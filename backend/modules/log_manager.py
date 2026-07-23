import os
import re
import gzip
import shutil
import platform
import datetime
import json
import logging
import logging.handlers
import uuid
from contextvars import ContextVar
from typing import List, Dict, Any, Optional

try:
    import chardet
except ImportError:
    chardet = None

# 配置实例（可选依赖，缺失时回退默认值）
try:
    from config.config import config_instance
except Exception:
    config_instance = None

# ===== 日志目录与文件路径 =====
def _resolve_log_dir():
    """优先从配置读取日志目录，回退到项目根 logs 目录"""
    if config_instance is not None:
        try:
            d = config_instance.LOG_DIR
            if d:
                return d
        except Exception:
            pass
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')

# 面板日志目录
PANEL_LOG_DIR = _resolve_log_dir()

# 确保日志目录存在
os.makedirs(PANEL_LOG_DIR, exist_ok=True)

# 面板操作日志文件路径
PANEL_OPERATIONS_LOG = os.path.join(PANEL_LOG_DIR, 'panel_operations.log')
PANEL_SYSTEM_LOG = os.path.join(PANEL_LOG_DIR, 'panel_system.log')

# ===== request_id 链路追踪上下文 =====
_request_id_var: ContextVar[str] = ContextVar('panel_request_id', default='-')

def set_request_id(rid: Optional[str] = None) -> str:
    """设置当前请求的 request_id；不提供则自动生成。返回设置的 id。"""
    rid = rid or uuid.uuid4().hex[:12]
    _request_id_var.set(rid)
    return rid

def get_request_id() -> str:
    """获取当前上下文的 request_id"""
    return _request_id_var.get()

def clear_request_id():
    """清除 request_id（请求结束时调用）"""
    _request_id_var.set('-')

# ===== 级别映射 =====
_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.CRITICAL,
}

def _level_value(level):
    """将级别名称或数字转为 logging 级别常量"""
    if isinstance(level, int):
        return level
    return _LEVEL_MAP.get(str(level).upper(), logging.INFO)

def _config_level(default='INFO'):
    """读取配置的日志级别"""
    if config_instance is not None:
        try:
            return _level_value(config_instance.LOG_LEVEL)
        except Exception:
            pass
    return _level_value(default)

# ===== 自定义 Formatter =====
class _ContextFormatter(logging.Formatter):
    """注入 request_id 等上下文信息的格式器基类"""

    def format(self, record):
        if not hasattr(record, 'request_id') or not record.request_id:
            record.request_id = get_request_id()
        return super().format(record)

# 操作日志默认文本格式（保持与旧版完全一致，严格兼容前端解析）
_OPERATION_FMT = '%(asctime)s - %(levelname)s - %(user)s - %(action)s - %(ip)s - %(message)s'
# 系统日志文本格式（新增 request_id 字段，解析器已兼容旧格式）
_SYSTEM_FMT = '%(asctime)s - %(levelname)s - %(name)s - [%(request_id)s] - %(filename)s:%(lineno)d - %(message)s'


class _JsonFormatter(_ContextFormatter):
    """结构化 JSON 日志格式器"""

    def format(self, record):
        record.request_id = get_request_id()
        log_obj = {
            'timestamp': datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'logger': record.name,
            'request_id': record.request_id,
            'message': record.getMessage(),
        }
        # 操作日志特有字段
        for f in ('user', 'action', 'ip'):
            if hasattr(record, f):
                log_obj[f] = getattr(record, f)
        # 系统日志特有字段
        log_obj['source'] = f'{record.filename}:{record.lineno}'
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)


# ===== 控制台彩色格式器 =====
_CONSOLE_COLORS = {
    'DEBUG': '\033[36m',     # cyan
    'INFO': '\033[32m',      # green
    'WARNING': '\033[33m',   # yellow
    'ERROR': '\033[31m',     # red
    'CRITICAL': '\033[35m',  # magenta
}
_RESET = '\033[0m'


class _ColorFormatter(_ContextFormatter):
    """控制台彩色输出格式器"""

    def __init__(self, fmt=None, datefmt=None, color=True):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.color = color

    def format(self, record):
        record.request_id = get_request_id()
        msg = super().format(record)
        if self.color:
            color = _CONSOLE_COLORS.get(record.levelname, '')
            if color:
                msg = f'{color}{msg}{_RESET}'
        return msg


# ===== 支持压缩的轮转处理器 =====
class _CompressorMixin:
    """轮转后压缩旧日志文件的混入，gzip 压缩非 .gz 的轮转文件"""

    compress = True

    def _compress_rotated_files(self):
        dir_name, base_name = os.path.split(self.baseFilename)
        try:
            files = os.listdir(dir_name)
        except Exception:
            return
        for fn in files:
            # 只处理当前日志文件的轮转产物
            if not fn.startswith(base_name + '.'):
                continue
            if fn.endswith('.gz'):
                continue
            full_path = os.path.join(dir_name, fn)
            if not os.path.isfile(full_path):
                continue
            gz_path = full_path + '.gz'
            try:
                with open(full_path, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(full_path)
            except Exception:
                # 压缩失败保留原文件，避免日志丢失
                pass


class _CompressingTimedHandler(_CompressorMixin, logging.handlers.TimedRotatingFileHandler):
    """按时间轮转 + 可选 gzip 压缩"""

    def __init__(self, filename, when='midnight', interval=1, backupCount=7,
                 compress=True, encoding='utf-8'):
        super().__init__(filename, when=when, interval=interval,
                         backupCount=backupCount, encoding=encoding)
        self.compress = compress

    def doRollover(self):
        super().doRollover()
        if self.compress:
            self._compress_rotated_files()


class _CompressingSizeHandler(_CompressorMixin, logging.handlers.RotatingFileHandler):
    """按大小轮转 + 可选 gzip 压缩"""

    def __init__(self, filename, maxBytes=0, backupCount=0, compress=True, encoding='utf-8'):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding)
        self.compress = compress

    def doRollover(self):
        super().doRollover()
        if self.compress:
            self._compress_rotated_files()


def _cleanup_old_logs(retention_days: int):
    """清理超过保留天数的旧日志文件"""
    if not retention_days or retention_days <= 0:
        return
    try:
        now = datetime.datetime.now()
        for fn in os.listdir(PANEL_LOG_DIR):
            full_path = os.path.join(PANEL_LOG_DIR, fn)
            if not os.path.isfile(full_path):
                continue
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
            except Exception:
                continue
            if (now - mtime).days > retention_days:
                try:
                    os.remove(full_path)
                except Exception:
                    pass
    except Exception:
        pass


def _make_file_handler(filename):
    """根据配置创建文件处理器：when='size' 按大小轮转，其他按时间轮转"""
    when = 'midnight'
    interval = 1
    backup_count = 5
    compress = True
    max_bytes = 10 * 1024 * 1024
    if config_instance is not None:
        try:
            when = config_instance.LOG_WHEN or 'midnight'
            interval = config_instance.LOG_INTERVAL or 1
            backup_count = config_instance.LOG_BACKUP_COUNT or 5
            compress = bool(config_instance.LOG_COMPRESS)
            max_bytes = config_instance.LOG_MAX_BYTES or (10 * 1024 * 1024)
        except Exception:
            pass
    if str(when).lower() == 'size':
        return _CompressingSizeHandler(
            filename, maxBytes=max_bytes, backupCount=backup_count,
            compress=compress, encoding='utf-8'
        )
    return _CompressingTimedHandler(
        filename, when=when, interval=interval,
        backupCount=backup_count, compress=compress
    )


def _make_formatter(is_operation: bool):
    """根据配置创建格式器（JSON 或文本）"""
    json_fmt = False
    if config_instance is not None:
        try:
            json_fmt = bool(config_instance.LOG_JSON_FORMAT)
        except Exception:
            json_fmt = False
    if json_fmt:
        return _JsonFormatter()
    fmt = _OPERATION_FMT if is_operation else _SYSTEM_FMT
    return _ContextFormatter(fmt, datefmt='%Y-%m-%d %H:%M:%S')


def _make_console_formatter():
    """控制台格式器"""
    color = True
    if config_instance is not None:
        try:
            color = bool(config_instance.LOG_CONSOLE_COLOR)
        except Exception:
            color = True
    return _ColorFormatter(
        fmt='%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s - %(message)s',
        datefmt='%H:%M:%S', color=color
    )


def _add_console_handler(logger):
    """为 logger 添加控制台处理器（若配置启用）"""
    enabled = True
    level = logging.INFO
    if config_instance is not None:
        try:
            enabled = bool(config_instance.LOG_CONSOLE_ENABLED)
            level = _level_value(config_instance.LOG_CONSOLE_LEVEL)
        except Exception:
            pass
    if not enabled:
        return
    # 避免重复添加控制台处理器
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            return
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(_make_console_formatter())
    logger.addHandler(handler)


# 配置日志记录器
def setup_logging():
    """配置日志记录器（操作日志 + 系统日志），统一从 config 读取配置。

    - 修复：不再为每个 name 创建独立 handler 写同一文件，所有系统日志统一通过
      panel_system logger 的 handler 输出，避免重复写入与文件锁竞争。
    - 支持 exc_info、CRITICAL 级别、JSON/文本格式、控制台输出、按时间/大小轮转与压缩。
    """
    # 操作日志记录器
    operation_logger = logging.getLogger('panel_operations')
    operation_logger.setLevel(_config_level('INFO'))
    operation_logger.propagate = False
    operation_logger.handlers.clear()

    # 系统日志记录器
    system_logger = logging.getLogger('panel_system')
    system_logger.setLevel(_config_level('DEBUG'))
    system_logger.propagate = False
    system_logger.handlers.clear()

    # 文件处理器
    operation_handler = _make_file_handler(PANEL_OPERATIONS_LOG)
    operation_handler.setFormatter(_make_formatter(is_operation=True))
    operation_logger.addHandler(operation_handler)

    system_handler = _make_file_handler(PANEL_SYSTEM_LOG)
    system_handler.setFormatter(_make_formatter(is_operation=False))
    system_logger.addHandler(system_handler)

    # 控制台处理器
    _add_console_handler(operation_logger)
    _add_console_handler(system_logger)

    # 清理过期日志
    retention = 30
    if config_instance is not None:
        try:
            retention = config_instance.LOG_RETENTION_DAYS or 30
        except Exception:
            pass
    _cleanup_old_logs(retention)

    return operation_logger, system_logger

# 获取日志记录器（模块级，导入即初始化）
operation_logger, system_logger = setup_logging()


def _emit(logger, message, level, exc_info=None, extra=None):
    """统一的日志发射函数，支持完整级别与异常堆栈"""
    level = str(level).upper() if level else 'INFO'
    lvl = _level_value(level)
    kwargs = {}
    if exc_info:
        kwargs['exc_info'] = exc_info
    if extra:
        kwargs['extra'] = extra
    logger.log(lvl, message, **kwargs)


# 记录面板操作日志
def log_operation(user: str, action: str, ip: str, message: str = '', level: str = 'INFO',
                  exc_info=None):
    """记录面板操作日志

    向后兼容：前 5 个参数与旧版完全一致，现有调用无需改动。
    新增 exc_info 关键字参数：传入 True 可记录完整异常堆栈。
    支持 INFO/WARN/ERROR/CRITICAL 等全部级别。
    """
    extra = {'user': user or '-', 'action': action or '-', 'ip': ip or '-'}
    _emit(operation_logger, message, level, exc_info=exc_info, extra=extra)


# 记录系统日志
def log_system(message: str, level: str = 'INFO', name: str = 'system', exc_info=None):
    """记录系统日志

    向后兼容：签名前 3 个参数与旧版完全一致，现有调用无需改动。
    新增 exc_info 关键字参数：传入 True 可记录完整异常堆栈。
    支持 DEBUG/INFO/WARN/ERROR/CRITICAL 全部级别。

    修复：name 不再创建独立 handler 写同一文件，而是通过 panel_system logger
    统一输出，避免重复写入与文件锁竞争。
    """
    if name and name != 'system':
        # 子 logger 通过传播由 panel_system 的 handler 统一处理，不重复添加 handler
        logger = logging.getLogger(f'panel_system.{name}')
    else:
        logger = system_logger
    _emit(logger, message, level, exc_info=exc_info)

# 日志路径白名单
LOG_PATH_WHITELIST = {
    # Linux系统日志路径
    '/var/log',
    '/var/log/syslog',
    '/var/log/messages',
    '/var/log/auth.log',
    '/var/log/kern.log',
    '/var/log/daemon.log',
    '/var/log/user.log',
    '/var/log/cron.log',
    '/var/log/apt',
    '/var/log/apache2',
    '/var/log/nginx',
    '/var/log/mysql',
    '/var/log/postgresql',
    
    # Windows系统日志路径
    os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'Logs'),
    os.path.join(os.environ.get('ProgramData', r'C:\ProgramData'), 'Microsoft', 'Windows', 'EventLog'),
    os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'winevt', 'Logs')
}

# 添加面板日志到白名单
LOG_PATH_WHITELIST.add(PANEL_LOG_DIR)

# 检查文件路径是否在白名单中
def is_path_allowed(file_path):
    # 规范化路径
    normalized_path = os.path.normpath(file_path)
    
    # 检查是否在白名单中
    for allowed_path in LOG_PATH_WHITELIST:
        allowed_path = os.path.normpath(allowed_path)
        if normalized_path.startswith(allowed_path):
            return True
    
    return False

# 自动检测文件编码
def detect_file_encoding(file_path, sample_size=1024*1024):
    if chardet is None:
        return 'utf-8'
    with open(file_path, 'rb') as f:
        # 读取文件前N个字节用于检测编码
        sample = f.read(sample_size)
        result = chardet.detect(sample)

    # 返回检测到的编码
    return result['encoding'] if result['confidence'] > 0.7 else 'utf-8'

# 获取Windows系统日志文件
def get_windows_logs():
    logs = []
    # Windows应用日志目录
    log_dirs = [
        os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Logs'),
        os.path.join(os.environ.get('ProgramData', 'C:\\ProgramData'), 'Microsoft', 'Windows', 'EventLog')
    ]
    
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    if file.endswith('.evtx') or file.endswith('.log'):
                        log_path = os.path.join(root, file)
                        logs.append({
                            'name': file,
                            'path': log_path,
                            'size': os.path.getsize(log_path)
                        })
    
    return logs

# 获取Linux系统日志文件
def get_linux_logs():
    logs = []
    # Linux日志目录
    log_dirs = ['/var/log', '/var/log/syslog']
    
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            if os.path.isdir(log_dir):
                for root, dirs, files in os.walk(log_dir):
                    for file in files:
                        log_path = os.path.join(root, file)
                        if os.path.isfile(log_path):
                            logs.append({
                                'name': file,
                                'path': log_path,
                                'size': os.path.getsize(log_path)
                            })
            else:
                # 单个日志文件
                logs.append({
                    'name': os.path.basename(log_dir),
                    'path': log_dir,
                    'size': os.path.getsize(log_dir)
                })
    
    return logs

# 获取面板日志文件
def get_panel_logs():
    """获取面板日志文件列表"""
    panel_logs = []
    
    # 遍历面板日志目录
    if os.path.exists(PANEL_LOG_DIR):
        for file in os.listdir(PANEL_LOG_DIR):
            file_path = os.path.join(PANEL_LOG_DIR, file)
            if os.path.isfile(file_path):
                panel_logs.append({
                    'name': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'type': 'panel',
                    'modified_time': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    return panel_logs

# 获取日志文件列表
def get_logs():
    """获取所有可用的日志文件，包括系统日志和面板日志"""
    logs = []
    
    if platform.system() == 'Windows':
        logs.extend(get_windows_logs())
    elif platform.system() == 'Linux':
        logs.extend(get_linux_logs())
    
    # 添加面板日志
    logs.extend(get_panel_logs())
    
    return logs

# 解析日志行
def parse_log_line(log_line: str, log_type: str = 'system') -> Dict[str, Any]:
    """解析日志行

    兼容旧版文本格式与新版（含 request_id、CRITICAL 级别）格式，同时支持 JSON 行。
    """
    if not log_line:
        return {'raw': log_line}

    # 优先尝试 JSON 格式（结构化日志）
    stripped = log_line.strip()
    if stripped.startswith('{') and stripped.endswith('}'):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                obj.setdefault('raw', log_line)
                return obj
        except Exception:
            pass

    if log_type == 'panel_operations':
        # 操作日志格式（保持不变，补充 CRITICAL）:
        # 2023-01-01 12:00:00 - INFO - admin - login - 127.0.0.1 - Login successful
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (DEBUG|INFO|WARN|ERROR|CRITICAL) - (\S+) - (\S+) - ([\d\.]+) - (.+)'
        match = re.match(pattern, log_line)
        if match:
            return {
                'timestamp': match.group(1),
                'level': match.group(2),
                'user': match.group(3),
                'action': match.group(4),
                'ip': match.group(5),
                'message': match.group(6),
                'raw': log_line
            }
    elif log_type == 'panel_system':
        # 新格式（含 request_id）:
        # 2023-01-01 12:00:00 - INFO - system - [a1b2c3d4e5f6] - app.py:123 - System started
        new_pattern = (r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - '
                       r'(DEBUG|INFO|WARN|ERROR|CRITICAL) - ([\w\.]+) - '
                       r'\[([^\]]*)\] - ([\w\.]+:\d+) - (.+)')
        match = re.match(new_pattern, log_line)
        if match:
            return {
                'timestamp': match.group(1),
                'level': match.group(2),
                'logger': match.group(3),
                'request_id': match.group(4),
                'source': match.group(5),
                'message': match.group(6),
                'raw': log_line
            }
        # 旧格式（无 request_id，向后兼容）:
        # 2023-01-01 12:00:00 - INFO - system - app.py:123 - System started
        old_pattern = (r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - '
                       r'(DEBUG|INFO|WARN|ERROR|CRITICAL) - ([\w\.]+) - '
                       r'([\w\.]+:\d+) - (.+)')
        match = re.match(old_pattern, log_line)
        if match:
            return {
                'timestamp': match.group(1),
                'level': match.group(2),
                'logger': match.group(3),
                'request_id': '-',
                'source': match.group(4),
                'message': match.group(5),
                'raw': log_line
            }

    # 默认返回原始日志行
    return {
        'raw': log_line
    }

# 读取日志文件并应用筛选
def read_logs_with_filter(file_path: str, 
                          start_time: str = None, 
                          end_time: str = None, 
                          log_levels: List[str] = None, 
                          keyword: str = None, 
                          case_sensitive: bool = False, 
                          limit: int = 100, 
                          offset: int = 0) -> Dict[str, Any]:
    """读取日志文件并应用筛选条件"""
    try:
        # 检查路径是否在白名单中
        if not is_path_allowed(file_path):
            return {
                'status': 'error',
                'message': f'访问被拒绝：{file_path}不在允许的日志路径列表中'
            }
        
        # 自动检测文件编码
        encoding = detect_file_encoding(file_path)
        
        # 确定日志类型
        log_type = 'system'
        if 'panel_operations' in file_path:
            log_type = 'panel_operations'
        elif 'panel_system' in file_path:
            log_type = 'panel_system'
        
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            all_lines = f.readlines()
        
        # 解析所有日志行
        parsed_lines = []
        for line in all_lines:
            parsed = parse_log_line(line.strip(), log_type)
            if parsed:
                parsed_lines.append(parsed)
        
        # 应用时间范围筛选
        if start_time or end_time:
            filtered_lines = []
            for line in parsed_lines:
                if 'timestamp' in line:
                    log_time = datetime.datetime.strptime(line['timestamp'], '%Y-%m-%d %H:%M:%S')
                    include = True
                    
                    if start_time:
                        start = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                        if log_time < start:
                            include = False
                    
                    if end_time:
                        end = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                        if log_time > end:
                            include = False
                    
                    if include:
                        filtered_lines.append(line)
            parsed_lines = filtered_lines
        
        # 应用日志级别筛选
        if log_levels:
            parsed_lines = [line for line in parsed_lines if 'level' in line and line['level'] in log_levels]
        
        # 应用关键词筛选
        if keyword:
            if case_sensitive:
                parsed_lines = [line for line in parsed_lines if keyword in line.get('raw', '')]
            else:
                parsed_lines = [line for line in parsed_lines if keyword.lower() in line.get('raw', '').lower()]
        
        # 计算分页
        total_lines = len(parsed_lines)
        start = max(0, total_lines - limit - offset)
        end = total_lines - offset
        paginated_lines = parsed_lines[start:end]
        
        return {
            'status': 'success',
            'content': paginated_lines,
            'total_lines': total_lines,
            'lines_returned': len(paginated_lines),
            'encoding': encoding,
            'log_type': log_type
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# 导出日志文件
def export_logs(file_path: str, export_format: str = 'json', **filter_params) -> Dict[str, Any]:
    """导出日志文件"""
    try:
        # 检查路径是否在白名单中
        if not is_path_allowed(file_path):
            return {
                'status': 'error',
                'message': f'访问被拒绝：{file_path}不在允许的日志路径列表中'
            }
        
        # 读取日志并应用筛选
        result = read_logs_with_filter(file_path, **filter_params)
        if result['status'] != 'success':
            return result
        
        # 生成导出文件路径
        base_name = os.path.basename(file_path)
        export_file = os.path.join(PANEL_LOG_DIR, f'export_{base_name}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.{export_format}')
        
        # 导出日志
        if export_format == 'json':
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(result['content'], f, ensure_ascii=False, indent=2, default=str)
        elif export_format == 'txt':
            with open(export_file, 'w', encoding='utf-8') as f:
                for line in result['content']:
                    f.write(line.get('raw', '') + '\n')
        else:
            return {
                'status': 'error',
                'message': f'Unsupported export format: {export_format}'
            }
        
        return {
            'status': 'success',
            'export_path': export_file,
            'file_name': os.path.basename(export_file),
            'lines_exported': result['lines_returned']
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# 读取日志文件内容
def read_log_file(file_path, lines=100, offset=0):
    try:
        # 检查路径是否在白名单中
        if not is_path_allowed(file_path):
            return {
                'status': 'error',
                'message': f'访问被拒绝：{file_path}不在允许的日志路径列表中'
            }
        
        # 自动检测文件编码
        encoding = detect_file_encoding(file_path)
        
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            # 读取所有行
            all_lines = f.readlines()
            
            # 计算起始和结束位置
            start = max(0, len(all_lines) - lines - offset)
            end = len(all_lines) - offset
            
            # 获取指定范围的行
            log_lines = all_lines[start:end]
            
            return {
                'status': 'success',
                'content': ''.join(log_lines),
                'total_lines': len(all_lines),
                'lines_returned': len(log_lines),
                'encoding': encoding
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# 搜索日志内容
def search_logs(data):
    file_path = data.get('file_path')
    keyword = data.get('keyword')
    case_sensitive = data.get('case_sensitive', False)
    lines = data.get('lines', 100)
    
    if not file_path or not keyword:
        return {
            'status': 'error',
            'message': 'file_path and keyword are required'
        }
    
    try:
        # 检查路径是否在白名单中
        if not is_path_allowed(file_path):
            return {
                'status': 'error',
                'message': f'访问被拒绝：{file_path}不在允许的日志路径列表中'
            }
        
        # 自动检测文件编码
        encoding = detect_file_encoding(file_path)
        
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            all_lines = f.readlines()
        
        # 搜索匹配的行
        matches = []
        for i, line in enumerate(all_lines):
            if case_sensitive:
                if keyword in line:
                    matches.append({'line': i + 1, 'content': line.strip()})
            else:
                if keyword.lower() in line.lower():
                    matches.append({'line': i + 1, 'content': line.strip()})
        
        # 返回最近的匹配结果
        recent_matches = matches[-lines:]
        
        return {
            'status': 'success',
            'matches': recent_matches,
            'total_matches': len(matches),
            'matches_returned': len(recent_matches),
            'encoding': encoding
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
