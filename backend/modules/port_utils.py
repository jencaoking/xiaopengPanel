import socket
import psutil
import os
import sys
import time
import subprocess

def is_port_available(port):
    """检查端口是否可用"""
    if not isinstance(port, int) or port < 1024 or port > 65535:
        return False
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.bind(('0.0.0.0', port))
            return True
        except socket.error:
            return False

def get_current_process_pid():
    """获取当前进程的PID"""
    return os.getpid()

def restart_service():
    """重启服务"""
    try:
        # 获取当前脚本的路径
        script_path = os.path.abspath(sys.argv[0])
        
        # 获取当前Python解释器的路径
        python_path = sys.executable
        
        # 启动新的进程
        subprocess.Popen([python_path, script_path], close_fds=True)
        
        # 退出当前进程
        sys.exit(0)
        return True
    except Exception as e:
        return False

def check_port_in_use(port):
    """检查端口是否被占用"""
    for conn in psutil.net_connections(kind='inet'):
        if conn.laddr.port == port and conn.status == 'LISTEN':
            return True
    return False

def validate_port(port):
    """验证端口是否有效"""
    # 检查端口是否为整数
    if not isinstance(port, int):
        try:
            port = int(port)
        except ValueError:
            return False, "端口必须是整数"
    
    # 检查端口范围
    if port < 1024 or port > 65535:
        return False, "端口必须在1024-65535之间"
    
    # 检查端口是否被占用
    if check_port_in_use(port):
        return False, "端口已被占用"
    
    return True, "端口有效"