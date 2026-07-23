import psutil
import time
import json
import os
import sqlite3
import platform
import threading
from datetime import datetime, timedelta
from collections import deque

HISTORY_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'metrics_history.db')
WIDGET_LAYOUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'widget_layouts.json')

# 数据保留策略：分钟级 7 天，小时级 90 天，天级永久
RETENTION_MINUTE_DAYS = 7
RETENTION_HOUR_DAYS = 90
RETENTION_DAY_DAYS = 3650

# 采集与推送间隔（秒）
COLLECT_INTERVAL = 60
PUSH_INTERVAL = 3

# 可监控的指标白名单（用于告警阈值校验）
MONITORED_METRICS = {
    'cpu', 'memory', 'swap', 'load', 'disk_read', 'disk_write',
    'network_sent', 'network_recv', 'disk_response_time',
    'temperature', 'gpu'
}

# SocketIO 实例引用（由 app.py 注入），用于实时推送
_socketio_ref = None


def set_socketio_reference(sio):
    """由 app.py 注入 socketio 实例，供监控推送使用"""
    global _socketio_ref
    _socketio_ref = sio


def _verify_monitor_token(token):
    """验证监控 WebSocket 连接的 JWT 令牌"""
    if not token:
        return None
    try:
        import jwt
        from config.config import config_instance
        payload = jwt.decode(token, config_instance.SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception:
        return None


def init_monitor_namespace(sio):
    """注册 /monitor WebSocket 命名空间事件处理（带 JWT 鉴权）"""
    from flask import request
    from flask_socketio import join_room, leave_room

    @sio.on('connect', namespace='/monitor')
    def handle_monitor_connect():
        # 连接时通过 auth 查询参数校验 JWT
        token = None
        auth = request.args.get('auth')
        if auth:
            token = auth
        elif request.headers.get('Authorization', '').startswith('Bearer '):
            token = request.headers['Authorization'][7:]
        payload = _verify_monitor_token(token)
        if not payload:
            # 拒绝未认证连接
            from flask_socketio import ConnectionRefusedError
            raise ConnectionRefusedError('Unauthorized')
        request.monitor_user = payload.get('username', 'unknown')

    @sio.on('disconnect', namespace='/monitor')
    def handle_monitor_disconnect():
        pass

    @sio.on('subscribe', namespace='/monitor')
    def handle_subscribe(data):
        # 订阅特定指标频道（realtime / alerts），实现按需推送的扩展点
        channel = (data or {}).get('channel', 'realtime')
        join_room(f"monitor_{channel}")

    @sio.on('unsubscribe', namespace='/monitor')
    def handle_unsubscribe(data):
        channel = (data or {}).get('channel', 'realtime')
        leave_room(f"monitor_{channel}")


def _emit_monitor_event(event, data):
    """安全地向 /monitor 命名空间推送事件"""
    if _socketio_ref is None:
        return
    try:
        _socketio_ref.emit(event, data, namespace='/monitor')
    except Exception as e:
        print(f"Monitor push error ({event}): {e}")


class GpuCollector:
    """GPU 指标采集器，基于 pynvml；不可用时优雅降级"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._nvml = None
        self._device_count = 0
        self._available = False
        self._init_nvml()

    def _init_nvml(self):
        try:
            import pynvml
            pynvml.nvmlInit()
            self._device_count = pynvml.nvmlDeviceGetCount()
            self._nvml = pynvml
            self._available = True
        except Exception:
            # pynvml 未安装或无 NVIDIA GPU
            self._available = False

    @property
    def available(self):
        return self._available

    def get_metrics(self):
        """返回 GPU 指标列表；不可用时返回空列表"""
        if not self._available or self._nvml is None:
            return []
        metrics = []
        for i in range(self._device_count):
            try:
                handle = self._nvml.nvmlDeviceGetHandleByIndex(i)
                util = self._nvml.nvmlDeviceGetUtilizationRates(handle)
                mem = self._nvml.nvmlDeviceGetMemoryInfo(handle)
                temp = self._nvml.nvmlDeviceGetTemperature(handle, self._nvml.NVML_TEMPERATURE_GPU)
                name = self._nvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8', errors='replace')
                power = self._nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW -> W
                metrics.append({
                    'index': i,
                    'name': name,
                    'gpu_utilization': util.gpu,
                    'memory_utilization': util.memory,
                    'memory_total': mem.total,
                    'memory_used': mem.used,
                    'memory_free': mem.free,
                    'temperature': temp,
                    'power_draw': power
                })
            except Exception as e:
                print(f"GPU metric error (device {i}): {e}")
        return metrics


def get_temperature_sensors():
    """获取温度传感器信息（仅 Linux 可用），其他平台返回空列表"""
    if platform.system() != 'Linux':
        return []
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, Exception):
        return []
    if not temps:
        return []
    result = []
    for name, entries in temps.items():
        for entry in entries:
            result.append({
                'label': entry.label or name,
                'sensor': name,
                'current': entry.current,
                'high': getattr(entry, 'high', None),
                'critical': getattr(entry, 'critical', None)
            })
    return result


class MetricsCollector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # 内存环形缓冲：10080 = 7 天的分钟级数据
        self._history_buffer = {
            'cpu': deque(maxlen=10080),
            'memory': deque(maxlen=10080),
            'swap': deque(maxlen=10080),
            'load': deque(maxlen=10080),
            'disk_read': deque(maxlen=10080),
            'disk_write': deque(maxlen=10080),
            'network_sent': deque(maxlen=10080),
            'network_recv': deque(maxlen=10080),
            'disk_io_read_bytes': deque(maxlen=10080),
            'disk_io_write_bytes': deque(maxlen=10080),
            'disk_iops_read': deque(maxlen=10080),
            'disk_iops_write': deque(maxlen=10080),
            'disk_response_time': deque(maxlen=10080),
            'temperature': deque(maxlen=10080),
            'gpu': deque(maxlen=10080)
        }
        self._last_disk_io = None
        self._last_net_io = None
        self._last_collect_time = None
        # 已触发的活跃告警缓存，避免重复触发 (metric_key -> alert_id)
        self._active_alerts_cache = {}
        self._gpu_collector = GpuCollector()
        self._init_db()
        self._start_collector()
        self._start_pusher()
        self._start_retention_cleaner()

    def _init_db(self):
        os.makedirs(os.path.dirname(HISTORY_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(HISTORY_DB_PATH)
        cursor = conn.cursor()
        # 原始分钟级数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                granularity TEXT DEFAULT 'minute'
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON metrics_history(timestamp, metric_type)
        ''')
        # 告警阈值配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL UNIQUE,
                threshold_type TEXT NOT NULL,
                threshold_value REAL NOT NULL,
                alert_message TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 告警记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                metric_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                current_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                message TEXT,
                status TEXT DEFAULT 'active',
                resolved_at DATETIME
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_system_alerts_status
            ON system_alerts(status, timestamp)
        ''')
        conn.commit()
        conn.close()

    def _start_collector(self):
        def collect_loop():
            while True:
                try:
                    self._collect_metrics()
                except Exception as e:
                    print(f"Metrics collection error: {e}")
                time.sleep(COLLECT_INTERVAL)

        thread = threading.Thread(target=collect_loop, daemon=True)
        thread.start()

    def _start_pusher(self):
        """独立线程通过 SocketIO 推送实时指标，替代前端轮询"""
        def push_loop():
            while True:
                try:
                    metrics = self.get_realtime_metrics()
                    _emit_monitor_event('realtime_metrics', metrics)
                    # 推送活跃告警计数
                    alerts = self.get_alerts(status='active').get('alerts', [])
                    _emit_monitor_event('alerts_update', {
                        'active_count': len(alerts),
                        'alerts': alerts[:20]
                    })
                except Exception as e:
                    print(f"Metrics push error: {e}")
                time.sleep(PUSH_INTERVAL)

        thread = threading.Thread(target=push_loop, daemon=True)
        thread.start()

    def _start_retention_cleaner(self):
        """每小时执行一次数据保留清理 + 降采样"""
        def cleanup_loop():
            while True:
                try:
                    self._downsample_and_cleanup()
                except Exception as e:
                    print(f"Retention cleanup error: {e}")
                time.sleep(3600)

        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()

    def _downsample_and_cleanup(self):
        """将过期的分钟级数据聚合为小时级，并按保留策略清理"""
        now = datetime.now()
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                # 1) 分钟级超过 7 天 -> 聚合为小时级
                minute_cutoff = now - timedelta(days=RETENTION_MINUTE_DAYS)
                cursor.execute('''
                    SELECT metric_type,
                           strftime('%Y-%m-%d %H:00:00', timestamp) AS hour_bucket,
                           AVG(metric_value) AS avg_val
                    FROM metrics_history
                    WHERE granularity = 'minute' AND timestamp < ?
                    GROUP BY metric_type, hour_bucket
                ''', (minute_cutoff.isoformat(),))
                rows = cursor.fetchall()
                if rows:
                    cursor.executemany('''
                        INSERT INTO metrics_history (timestamp, metric_type, metric_value, granularity)
                        VALUES (?, ?, ?, 'hour')
                    ''', [(hour_bucket, mt, avg_val, ) for mt, hour_bucket, avg_val in rows])
                cursor.execute('''
                    DELETE FROM metrics_history
                    WHERE granularity = 'minute' AND timestamp < ?
                ''', (minute_cutoff.isoformat(),))

                # 2) 小时级超过 90 天 -> 聚合为天级
                hour_cutoff = now - timedelta(days=RETENTION_HOUR_DAYS)
                cursor.execute('''
                    SELECT metric_type,
                           strftime('%Y-%m-%d 00:00:00', timestamp) AS day_bucket,
                           AVG(metric_value) AS avg_val
                    FROM metrics_history
                    WHERE granularity = 'hour' AND timestamp < ?
                    GROUP BY metric_type, day_bucket
                ''', (hour_cutoff.isoformat(),))
                rows = cursor.fetchall()
                if rows:
                    cursor.executemany('''
                        INSERT INTO metrics_history (timestamp, metric_type, metric_value, granularity)
                        VALUES (?, ?, ?, 'day')
                    ''', [(day_bucket, mt, avg_val) for mt, day_bucket, avg_val in rows])
                cursor.execute('''
                    DELETE FROM metrics_history
                    WHERE granularity = 'hour' AND timestamp < ?
                ''', (hour_cutoff.isoformat(),))

                # 3) 天级超过保留期 -> 删除
                day_cutoff = now - timedelta(days=RETENTION_DAY_DAYS)
                cursor.execute('''
                    DELETE FROM metrics_history
                    WHERE granularity = 'day' AND timestamp < ?
                ''', (day_cutoff.isoformat(),))

                conn.commit()
        except Exception as e:
            print(f"Downsample/cleanup failed: {e}")

    def _collect_metrics(self):
        now = time.time()
        timestamp = datetime.now().isoformat()

        # 单次采集 CPU，避免重复调用阻塞
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        swap_percent = psutil.swap_memory().percent
        load_avg = self._get_load_average_scalar()

        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        disk_read_speed = 0
        disk_write_speed = 0
        disk_iops_read = 0
        disk_iops_write = 0
        disk_response_time = 0
        net_sent_speed = 0
        net_recv_speed = 0

        if self._last_disk_io and self._last_collect_time:
            time_delta = now - self._last_collect_time
            if time_delta > 0:
                disk_read_speed = (disk_io.read_bytes - self._last_disk_io.read_bytes) / time_delta
                disk_write_speed = (disk_io.write_bytes - self._last_disk_io.write_bytes) / time_delta
                disk_iops_read = (disk_io.read_count - self._last_disk_io.read_count) / time_delta
                disk_iops_write = (disk_io.write_count - self._last_disk_io.write_count) / time_delta

                read_time_delta = disk_io.read_time - self._last_disk_io.read_time
                write_time_delta = disk_io.write_time - self._last_disk_io.write_time
                total_ops = disk_iops_read + disk_iops_write
                if total_ops > 0:
                    disk_response_time = (read_time_delta + write_time_delta) / total_ops

                net_sent_speed = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
                net_recv_speed = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta

        self._last_disk_io = disk_io
        self._last_net_io = net_io
        self._last_collect_time = now

        # 温度指标（取第一个 CPU/核心温度作为代表值，便于趋势记录）
        temps = get_temperature_sensors()
        temp_value = 0
        for t in temps:
            if t['current'] is not None:
                temp_value = t['current']
                break

        # GPU 利用率（取首个设备，便于趋势记录）
        gpu_value = 0
        gpu_metrics = self._gpu_collector.get_metrics()
        if gpu_metrics:
            gpu_value = gpu_metrics[0].get('gpu_utilization', 0)

        metrics = {
            'cpu': cpu_percent,
            'memory': memory_percent,
            'swap': swap_percent,
            'load': load_avg,
            'disk_read': disk_read_speed,
            'disk_write': disk_write_speed,
            'network_sent': net_sent_speed,
            'network_recv': net_recv_speed,
            'disk_io_read_bytes': disk_io.read_bytes,
            'disk_io_write_bytes': disk_io.write_bytes,
            'disk_iops_read': disk_iops_read,
            'disk_iops_write': disk_iops_write,
            'disk_response_time': disk_response_time,
            'temperature': temp_value,
            'gpu': gpu_value
        }

        for key, value in metrics.items():
            self._history_buffer[key].append({
                'timestamp': timestamp,
                'value': value
            })

        self._save_to_db(metrics, timestamp)

        # 采集后检查告警阈值
        self._check_alerts(metrics, timestamp)

    def _get_load_average_scalar(self):
        if platform.system() == 'Linux':
            try:
                return os.getloadavg()[0]
            except Exception:
                return 0
        return 0

    def _save_to_db(self, metrics, timestamp):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                for metric_type, metric_value in metrics.items():
                    cursor.execute('''
                        INSERT INTO metrics_history (timestamp, metric_type, metric_value, granularity)
                        VALUES (?, ?, ?, 'minute')
                    ''', (timestamp, metric_type, metric_value))
                conn.commit()
        except Exception as e:
            print(f"Failed to save metrics to DB: {e}")

    def get_realtime_metrics(self):
        """获取实时系统指标（单次 cpu_percent 调用，避免重复阻塞）"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cores = psutil.cpu_percent(interval=0, percpu=True)
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        now = time.time()
        disk_read_speed = 0
        disk_write_speed = 0
        net_sent_speed = 0
        net_recv_speed = 0
        disk_iops_read = 0
        disk_iops_write = 0
        disk_response_time = 0

        if self._last_disk_io and self._last_collect_time:
            time_delta = now - self._last_collect_time
            if time_delta > 0:
                disk_read_speed = (disk_io.read_bytes - self._last_disk_io.read_bytes) / time_delta
                disk_write_speed = (disk_io.write_bytes - self._last_disk_io.write_bytes) / time_delta
                disk_iops_read = (disk_io.read_count - self._last_disk_io.read_count) / time_delta
                disk_iops_write = (disk_io.write_count - self._last_disk_io.write_count) / time_delta

                read_time_delta = disk_io.read_time - self._last_disk_io.read_time
                write_time_delta = disk_io.write_time - self._last_disk_io.write_time
                total_ops = disk_iops_read + disk_iops_write
                if total_ops > 0:
                    disk_response_time = (read_time_delta + write_time_delta) / total_ops

                net_sent_speed = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
                net_recv_speed = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta

        return {
            'cpu': {
                'usage': cpu_percent,
                'cores': cores,
                'times': self._get_cpu_times()
            },
            'memory': {
                'total': memory.total,
                'used': memory.used,
                'available': memory.available,
                'percent': memory.percent,
                'cached': getattr(memory, 'cached', 0),
                'buffers': getattr(memory, 'buffers', 0)
            },
            'swap': {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent
            },
            'disk_io': {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_speed': disk_read_speed,
                'write_speed': disk_write_speed,
                'iops_read': disk_iops_read,
                'iops_write': disk_iops_write,
                'response_time': disk_response_time
            },
            'network': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'sent_speed': net_sent_speed,
                'recv_speed': net_recv_speed,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            },
            'load_average': self._get_load_average(),
            'temperature': get_temperature_sensors(),
            'gpu': self._gpu_collector.get_metrics(),
            'timestamp': datetime.now().isoformat()
        }

    def _get_cpu_times(self):
        try:
            t = psutil.cpu_times_percent(interval=0)
            return {'user': t.user, 'system': t.system, 'idle': t.idle}
        except Exception:
            return {'user': 0, 'system': 0, 'idle': 0}

    def _get_load_average(self):
        if platform.system() == 'Linux':
            try:
                loads = list(os.getloadavg())
            except Exception:
                loads = [0, 0, 0]
        else:
            loads = [0, 0, 0]
        return {
            '1min': loads[0],
            '5min': loads[1],
            '15min': loads[2]
        }

    def get_historical_metrics(self, metric_type, time_range='1h', granularity='minute'):
        now = datetime.now()
        time_map = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30)
        }
        start_time = now - time_map.get(time_range, timedelta(hours=1))

        # 短时间范围优先走内存缓冲，避免 DB 查询
        if granularity == 'minute' and time_range in ('1h', '6h', '24h'):
            buffer_data = list(self._history_buffer.get(metric_type, []))
            if buffer_data:
                filtered_data = [
                    item for item in buffer_data
                    if datetime.fromisoformat(item['timestamp']) >= start_time
                ]
                if filtered_data:
                    return filtered_data

        # 长时间范围 / 指定 granularity 走 DB（利用已降采样数据）
        # 当请求分钟级但跨度超过 7 天时，自动升级到小时级
        effective_granularity = granularity
        if granularity == 'minute' and time_range in ('30d',):
            effective_granularity = 'hour'

        try:
            conn = sqlite3.connect(HISTORY_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, metric_value FROM metrics_history
                WHERE metric_type = ? AND granularity = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            ''', (metric_type, effective_granularity, start_time.isoformat()))
            rows = cursor.fetchall()
            conn.close()
            return [{'timestamp': row[0], 'value': row[1]} for row in rows]
        except Exception as e:
            print(f"Failed to get historical metrics: {e}")
            return []

    # ============== 告警阈值引擎 ==============

    def _check_alerts(self, metrics, timestamp):
        """每次采集后根据阈值检查是否触发/解除告警"""
        try:
            thresholds = self.get_alert_thresholds()
            for th in thresholds:
                if not th.get('enabled'):
                    continue
                metric_name = th['metric_name']
                if metric_name not in metrics:
                    continue
                current_value = metrics[metric_name]
                threshold_value = th['threshold_value']
                threshold_type = th['threshold_type']
                triggered = False
                if threshold_type == 'above' and current_value > threshold_value:
                    triggered = True
                elif threshold_type == 'below' and current_value < threshold_value:
                    triggered = True

                cache_key = metric_name
                if triggered and cache_key not in self._active_alerts_cache:
                    alert_id = self._create_alert(
                        metric_name, threshold_type, current_value,
                        threshold_value, th.get('alert_message', ''), timestamp
                    )
                    if alert_id:
                        self._active_alerts_cache[cache_key] = alert_id
                        _emit_monitor_event('alert_triggered', {
                            'id': alert_id,
                            'metric_name': metric_name,
                            'alert_type': threshold_type,
                            'current_value': current_value,
                            'threshold_value': threshold_value,
                            'message': th.get('alert_message', ''),
                            'timestamp': timestamp
                        })
                elif not triggered and cache_key in self._active_alerts_cache:
                    alert_id = self._active_alerts_cache.pop(cache_key)
                    self._resolve_alert(alert_id)
                    _emit_monitor_event('alert_resolved', {
                        'id': alert_id,
                        'metric_name': metric_name,
                        'timestamp': timestamp
                    })
        except Exception as e:
            print(f"Alert check error: {e}")

    def _create_alert(self, metric_name, alert_type, current_value, threshold_value, message, timestamp):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_alerts
                        (timestamp, metric_name, alert_type, current_value, threshold_value, message, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                ''', (timestamp, metric_name, alert_type, current_value, threshold_value, message))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Failed to create alert: {e}")
            return None

    def _resolve_alert(self, alert_id):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE system_alerts SET status = 'resolved', resolved_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), alert_id))
                conn.commit()
        except Exception as e:
            print(f"Failed to resolve alert: {e}")

    def get_alert_thresholds(self):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, metric_name, threshold_type, threshold_value, alert_message, enabled, created_at
                    FROM alert_thresholds ORDER BY created_at DESC
                ''')
                rows = cursor.fetchall()
                return [
                    {
                        'id': row[0], 'metric_name': row[1], 'threshold_type': row[2],
                        'threshold_value': row[3], 'alert_message': row[4],
                        'enabled': bool(row[5]), 'created_at': row[6]
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"Failed to get alert thresholds: {e}")
            return []

    def add_alert_threshold(self, metric_name, threshold_type, threshold_value, alert_message=''):
        if metric_name not in MONITORED_METRICS:
            return {'status': 'error', 'message': f'Invalid metric: {metric_name}'}
        if threshold_type not in ('above', 'below'):
            return {'status': 'error', 'message': 'threshold_type must be above or below'}
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alert_thresholds (metric_name, threshold_type, threshold_value, alert_message, enabled)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(metric_name) DO UPDATE SET
                        threshold_type = excluded.threshold_type,
                        threshold_value = excluded.threshold_value,
                        alert_message = excluded.alert_message,
                        enabled = 1
                ''', (metric_name, threshold_type, threshold_value, alert_message))
                conn.commit()
                return {'status': 'success', 'message': f'Alert threshold saved for {metric_name}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_alert_threshold(self, threshold_id, data):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                for field in ('metric_name', 'threshold_type', 'threshold_value', 'alert_message', 'enabled'):
                    if field in data:
                        val = data[field]
                        if field == 'enabled':
                            val = 1 if val else 0
                        updates.append(f"{field} = ?")
                        params.append(val)
                if not updates:
                    return {'status': 'error', 'message': 'No fields to update'}
                params.append(threshold_id)
                cursor.execute(
                    f"UPDATE alert_thresholds SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()
                return {'status': 'success', 'message': 'Alert threshold updated'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_alert_threshold(self, threshold_id):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM alert_thresholds WHERE id = ?', (threshold_id,))
                conn.commit()
                return {'status': 'success', 'message': 'Alert threshold deleted'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_alerts(self, status=None, limit=100):
        try:
            with sqlite3.connect(HISTORY_DB_PATH) as conn:
                cursor = conn.cursor()
                query = '''SELECT id, timestamp, metric_name, alert_type, current_value,
                                  threshold_value, message, status, resolved_at
                           FROM system_alerts'''
                params = []
                if status:
                    query += ' WHERE status = ?'
                    params.append(status)
                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return {'status': 'success', 'alerts': [
                    {
                        'id': row[0], 'timestamp': row[1], 'metric_name': row[2],
                        'alert_type': row[3], 'current_value': row[4],
                        'threshold_value': row[5], 'message': row[6],
                        'status': row[7], 'resolved_at': row[8]
                    }
                    for row in rows
                ]}
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'alerts': []}

    def resolve_alert(self, alert_id):
        self._resolve_alert(alert_id)
        # 同步清理缓存
        for k, v in list(self._active_alerts_cache.items()):
            if v == alert_id:
                self._active_alerts_cache.pop(k, None)
        return {'status': 'success', 'message': 'Alert resolved'}


metrics_collector = MetricsCollector()

# ============== 兼容旧 API 的模块级函数 ==============

def get_network_traffic():
    net_io = psutil.net_io_counters()
    realtime = metrics_collector.get_realtime_metrics()

    return {
        'current': {
            'upload_speed': realtime['network']['sent_speed'],
            'download_speed': realtime['network']['recv_speed']
        },
        'total': {
            'upload': net_io.bytes_sent,
            'download': net_io.bytes_recv
        },
        'packets': {
            'sent': net_io.packets_sent,
            'recv': net_io.packets_recv
        },
        'errors': {
            'in': net_io.errin,
            'out': net_io.errout
        },
        'dropped': {
            'in': net_io.dropin,
            'out': net_io.dropout
        },
        'per_interface': get_per_network_interface_traffic()
    }

def get_per_network_interface_traffic():
    """获取每网卡流量统计"""
    result = []
    try:
        per_nic = psutil.net_io_counters(pernic=True)
        for iface, stats in per_nic.items():
            result.append({
                'interface': iface,
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'errin': stats.errin,
                'errout': stats.errout,
                'dropin': stats.dropin,
                'dropout': stats.dropout
            })
    except Exception:
        pass
    return result

def get_per_disk_io():
    """获取每磁盘 IO 统计"""
    result = []
    try:
        per_disk = psutil.disk_io_counters(perdisk=True)
        for disk, stats in per_disk.items():
            result.append({
                'disk': disk,
                'read_bytes': stats.read_bytes,
                'write_bytes': stats.write_bytes,
                'read_count': stats.read_count,
                'write_count': stats.write_count,
                'read_time': stats.read_time,
                'write_time': stats.write_time
            })
    except Exception:
        pass
    return result

def get_network_traffic_history(time_range='1h'):
    sent_data = metrics_collector.get_historical_metrics('network_sent', time_range)
    recv_data = metrics_collector.get_historical_metrics('network_recv', time_range)

    return {
        'upload': sent_data,
        'download': recv_data
    }

def get_disk_io():
    disk_io = psutil.disk_io_counters()
    realtime = metrics_collector.get_realtime_metrics()

    return {
        'current': {
            'read_speed': realtime['disk_io']['read_speed'],
            'write_speed': realtime['disk_io']['write_speed'],
            'iops_read': realtime['disk_io']['iops_read'],
            'iops_write': realtime['disk_io']['iops_write'],
            'response_time': realtime['disk_io']['response_time']
        },
        'total': {
            'read_bytes': disk_io.read_bytes,
            'write_bytes': disk_io.write_bytes,
            'read_count': disk_io.read_count,
            'write_count': disk_io.write_count,
            'read_time': disk_io.read_time,
            'write_time': disk_io.write_time
        },
        'per_disk': get_per_disk_io()
    }

def get_disk_io_history(time_range='1h'):
    read_data = metrics_collector.get_historical_metrics('disk_read', time_range)
    write_data = metrics_collector.get_historical_metrics('disk_write', time_range)
    iops_read = metrics_collector.get_historical_metrics('disk_iops_read', time_range)
    iops_write = metrics_collector.get_historical_metrics('disk_iops_write', time_range)
    response_time = metrics_collector.get_historical_metrics('disk_response_time', time_range)

    return {
        'read_speed': read_data,
        'write_speed': write_data,
        'iops_read': iops_read,
        'iops_write': iops_write,
        'response_time': response_time
    }

def get_gpu_info():
    """获取 GPU 监控信息"""
    return {
        'available': GpuCollector().available,
        'devices': GpuCollector().get_metrics()
    }

def get_temperature_info():
    """获取温度传感器信息"""
    return {
        'available': platform.system() == 'Linux',
        'sensors': get_temperature_sensors()
    }

def get_top_processes(sort_by='cpu', limit=10):
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'io_counters', 'create_time', 'username', 'cmdline']):
        try:
            pinfo = proc.info
            io_counters = proc.io_counters() if hasattr(proc, 'io_counters') else None

            process_data = {
                'pid': pinfo['pid'],
                'name': pinfo['name'],
                'cpu_percent': pinfo['cpu_percent'] or 0,
                'memory_percent': pinfo['memory_percent'] or 0,
                'username': pinfo['username'] or '',
                'cmdline': ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else '',
                'create_time': datetime.fromtimestamp(pinfo['create_time']).isoformat() if pinfo['create_time'] else '',
                'io_read_bytes': io_counters.read_bytes if io_counters else 0,
                'io_write_bytes': io_counters.write_bytes if io_counters else 0
            }
            processes.append(process_data)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if sort_by == 'cpu':
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
    elif sort_by == 'memory':
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
    elif sort_by == 'io':
        processes.sort(key=lambda x: x['io_read_bytes'] + x['io_write_bytes'], reverse=True)

    return processes[:limit]

def get_process_detail(pid):
    try:
        proc = psutil.Process(pid)

        with proc.oneshot():
            cpu_times = proc.cpu_times()
            memory_info = proc.memory_info()
            io_counters = proc.io_counters() if hasattr(proc, 'io_counters') else None

            return {
                'pid': pid,
                'name': proc.name(),
                'status': proc.status(),
                'username': proc.username(),
                'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else '',
                'exe': proc.exe(),
                'cwd': proc.cwd(),
                'create_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                'cpu': {
                    'percent': proc.cpu_percent(interval=0.1),
                    'times': {
                        'user': cpu_times.user,
                        'system': cpu_times.system
                    },
                    'num_threads': proc.num_threads()
                },
                'memory': {
                    'percent': proc.memory_percent(),
                    'rss': memory_info.rss,
                    'vms': memory_info.vms,
                    'shared': getattr(memory_info, 'shared', 0),
                    'text': getattr(memory_info, 'text', 0),
                    'data': getattr(memory_info, 'data', 0)
                },
                'io': {
                    'read_bytes': io_counters.read_bytes if io_counters else 0,
                    'write_bytes': io_counters.write_bytes if io_counters else 0,
                    'read_count': io_counters.read_count if io_counters else 0,
                    'write_count': io_counters.write_count if io_counters else 0
                } if io_counters else None,
                'connections': len(proc.connections()) if hasattr(proc, 'connections') else 0,
                'open_files': len(proc.open_files()) if hasattr(proc, 'open_files') else 0
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        return {'error': str(e)}

def get_widget_layout(username):
    try:
        if os.path.exists(WIDGET_LAYOUT_FILE):
            with open(WIDGET_LAYOUT_FILE, 'r', encoding='utf-8') as f:
                layouts = json.load(f)
                return layouts.get(username, get_default_layout())
    except Exception as e:
        print(f"Failed to get widget layout: {e}")
    return get_default_layout()

def save_widget_layout(username, layout):
    try:
        layouts = {}
        if os.path.exists(WIDGET_LAYOUT_FILE):
            with open(WIDGET_LAYOUT_FILE, 'r', encoding='utf-8') as f:
                layouts = json.load(f)

        layouts[username] = layout

        with open(WIDGET_LAYOUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(layouts, f, indent=2, ensure_ascii=False)

        return {'status': 'success', 'message': 'Layout saved successfully'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_default_layout():
    return {
        'widgets': [
            {'id': 'cpu', 'x': 0, 'y': 0, 'w': 6, 'h': 4, 'visible': True},
            {'id': 'memory', 'x': 6, 'y': 0, 'w': 6, 'h': 4, 'visible': True},
            {'id': 'disk', 'x': 0, 'y': 4, 'w': 6, 'h': 4, 'visible': True},
            {'id': 'network', 'x': 6, 'y': 4, 'w': 6, 'h': 4, 'visible': True},
            {'id': 'alerts', 'x': 0, 'y': 8, 'w': 12, 'h': 4, 'visible': True},
            {'id': 'top_processes', 'x': 0, 'y': 12, 'w': 12, 'h': 6, 'visible': True},
            {'id': 'network_chart', 'x': 0, 'y': 18, 'w': 6, 'h': 5, 'visible': True},
            {'id': 'disk_io_chart', 'x': 6, 'y': 18, 'w': 6, 'h': 5, 'visible': True}
        ],
        'columns': 12
    }

def export_metrics_data(metric_types, time_range='24h', format='json'):
    data = {}
    for metric_type in metric_types:
        data[metric_type] = metrics_collector.get_historical_metrics(metric_type, time_range)

    if format == 'csv':
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['timestamp'] + metric_types)

        all_timestamps = set()
        for metric_data in data.values():
            for item in metric_data:
                all_timestamps.add(item['timestamp'])

        for timestamp in sorted(all_timestamps):
            row = [timestamp]
            for metric_type in metric_types:
                value = next((item['value'] for item in data[metric_type] if item['timestamp'] == timestamp), '')
                row.append(value)
            writer.writerow(row)

        return {'format': 'csv', 'data': output.getvalue()}

    return {'format': 'json', 'data': data}
