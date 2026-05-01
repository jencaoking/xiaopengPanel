import psutil
import time
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from collections import deque

HISTORY_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'metrics_history.db')
WIDGET_LAYOUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'widget_layouts.json')

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
        self._history_buffer = {
            'cpu': deque(maxlen=10080),
            'memory': deque(maxlen=10080),
            'disk_read': deque(maxlen=10080),
            'disk_write': deque(maxlen=10080),
            'network_sent': deque(maxlen=10080),
            'network_recv': deque(maxlen=10080),
            'disk_io_read_bytes': deque(maxlen=10080),
            'disk_io_write_bytes': deque(maxlen=10080),
            'disk_iops_read': deque(maxlen=10080),
            'disk_iops_write': deque(maxlen=10080),
            'disk_response_time': deque(maxlen=10080)
        }
        self._last_disk_io = None
        self._last_net_io = None
        self._last_collect_time = None
        self._init_db()
        self._start_collector()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(HISTORY_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(HISTORY_DB_PATH)
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()
    
    def _start_collector(self):
        def collect_loop():
            while True:
                try:
                    self._collect_metrics()
                except Exception as e:
                    print(f"Metrics collection error: {e}")
                time.sleep(60)
        
        thread = threading.Thread(target=collect_loop, daemon=True)
        thread.start()
    
    def _collect_metrics(self):
        now = time.time()
        timestamp = datetime.now().isoformat()
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
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
        
        metrics = {
            'cpu': cpu_percent,
            'memory': memory_percent,
            'disk_read': disk_read_speed,
            'disk_write': disk_write_speed,
            'network_sent': net_sent_speed,
            'network_recv': net_recv_speed,
            'disk_io_read_bytes': disk_io.read_bytes,
            'disk_io_write_bytes': disk_io.write_bytes,
            'disk_iops_read': disk_iops_read,
            'disk_iops_write': disk_iops_write,
            'disk_response_time': disk_response_time
        }
        
        for key, value in metrics.items():
            self._history_buffer[key].append({
                'timestamp': timestamp,
                'value': value
            })
        
        self._save_to_db(metrics, timestamp)
    
    def _save_to_db(self, metrics, timestamp):
        try:
            conn = sqlite3.connect(HISTORY_DB_PATH)
            cursor = conn.cursor()
            for metric_type, metric_value in metrics.items():
                cursor.execute('''
                    INSERT INTO metrics_history (timestamp, metric_type, metric_value, granularity)
                    VALUES (?, ?, ?, 'minute')
                ''', (timestamp, metric_type, metric_value))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to save metrics to DB: {e}")
    
    def get_realtime_metrics(self):
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
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
                'cores': psutil.cpu_percent(interval=0.1, percpu=True)
            },
            'memory': {
                'total': memory.total,
                'used': memory.used,
                'available': memory.available,
                'percent': memory.percent,
                'cached': getattr(memory, 'cached', 0),
                'buffers': getattr(memory, 'buffers', 0)
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
            'timestamp': datetime.now().isoformat()
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
        
        buffer_data = list(self._history_buffer.get(metric_type, []))
        
        if buffer_data:
            filtered_data = [
                item for item in buffer_data 
                if datetime.fromisoformat(item['timestamp']) >= start_time
            ]
            return filtered_data
        
        try:
            conn = sqlite3.connect(HISTORY_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, metric_value FROM metrics_history
                WHERE metric_type = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            ''', (metric_type, start_time.isoformat()))
            rows = cursor.fetchall()
            conn.close()
            
            return [{'timestamp': row[0], 'value': row[1]} for row in rows]
        except Exception as e:
            print(f"Failed to get historical metrics: {e}")
            return []

metrics_collector = MetricsCollector()

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
        }
    }

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
        }
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
            {'id': 'top_processes', 'x': 0, 'y': 8, 'w': 12, 'h': 6, 'visible': True},
            {'id': 'network_chart', 'x': 0, 'y': 14, 'w': 6, 'h': 5, 'visible': True},
            {'id': 'disk_io_chart', 'x': 6, 'y': 14, 'w': 6, 'h': 5, 'visible': True}
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
