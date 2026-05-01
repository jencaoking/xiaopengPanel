import os
import platform
import re
import chardet
import datetime
import json
import logging
import logging.handlers
from typing import List, Dict, Any

# 面板日志目录
PANEL_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')

# 确保日志目录存在
os.makedirs(PANEL_LOG_DIR, exist_ok=True)

# 面板操作日志文件路径
PANEL_OPERATIONS_LOG = os.path.join(PANEL_LOG_DIR, 'panel_operations.log')
PANEL_SYSTEM_LOG = os.path.join(PANEL_LOG_DIR, 'panel_system.log')

# 配置日志记录器
def setup_logging():
    """配置日志记录器"""
    # 操作日志记录器
    operation_logger = logging.getLogger('panel_operations')
    operation_logger.setLevel(logging.INFO)
    
    # 系统日志记录器
    system_logger = logging.getLogger('panel_system')
    system_logger.setLevel(logging.DEBUG)
    
    # 移除现有的处理器
    operation_logger.handlers.clear()
    system_logger.handlers.clear()
    
    # 创建文件处理器
    operation_handler = logging.handlers.RotatingFileHandler(
        PANEL_OPERATIONS_LOG,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    
    system_handler = logging.handlers.RotatingFileHandler(
        PANEL_SYSTEM_LOG,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    
    # 创建日志格式
    operation_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(user)s - %(action)s - %(ip)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    system_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置格式器
    operation_handler.setFormatter(operation_formatter)
    system_handler.setFormatter(system_formatter)
    
    # 添加处理器
    operation_logger.addHandler(operation_handler)
    system_logger.addHandler(system_handler)
    
    return operation_logger, system_logger

# 获取日志记录器
operation_logger, system_logger = setup_logging()

# 记录面板操作日志
def log_operation(user: str, action: str, ip: str, message: str = '', level: str = 'INFO'):
    """记录面板操作日志"""
    extra = {
        'user': user,
        'action': action,
        'ip': ip
    }
    
    if level == 'INFO':
        operation_logger.info(message, extra=extra)
    elif level == 'WARN':
        operation_logger.warning(message, extra=extra)
    elif level == 'ERROR':
        operation_logger.error(message, extra=extra)

# 记录系统日志
def log_system(message: str, level: str = 'INFO', name: str = 'system'):
    """记录系统日志"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 如果没有处理器，添加一个
    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            PANEL_SYSTEM_LOG,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    if level == 'INFO':
        logger.info(message)
    elif level == 'WARN':
        logger.warning(message)
    elif level == 'ERROR':
        logger.error(message)
    elif level == 'DEBUG':
        logger.debug(message)

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
    os.path.join(os.environ.get('SystemRoot', 'C:\Windows'), 'Logs'),
    os.path.join(os.environ.get('ProgramData', 'C:\ProgramData'), 'Microsoft', 'Windows', 'EventLog'),
    os.path.join(os.environ.get('SystemRoot', 'C:\Windows'), 'System32', 'winevt', 'Logs')
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
    """解析日志行"""
    if log_type == 'panel_operations':
        # 解析面板操作日志格式: 2023-01-01 12:00:00 - INFO - admin - login - 127.0.0.1 - Login successful
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (INFO|WARN|ERROR) - (\w+) - ([\w_]+) - ([\d\.]+) - (.+)'
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
        # 解析面板系统日志格式: 2023-01-01 12:00:00 - INFO - system - app.py:123 - System started
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (INFO|WARN|ERROR|DEBUG) - ([\w\.]+) - ([\w\.]+:\d+) - (.+)'
        match = re.match(pattern, log_line)
        if match:
            return {
                'timestamp': match.group(1),
                'level': match.group(2),
                'logger': match.group(3),
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
