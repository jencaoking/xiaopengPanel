import psutil
import platform
import socket
import os
import time
import datetime

# 面板启动时间
PANEL_START_TIME = time.time()

# 获取面板运行时长
def get_panel_uptime():
    """获取面板运行时长"""
    current_time = time.time()
    uptime_seconds = int(current_time - PANEL_START_TIME)
    
    days = uptime_seconds // (24 * 3600)
    hours = (uptime_seconds % (24 * 3600)) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    return {
        'seconds': uptime_seconds,
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds_remaining': seconds,
        'formatted': f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒",
        'start_time': datetime.datetime.fromtimestamp(PANEL_START_TIME).strftime('%Y-%m-%d %H:%M:%S')
    }

# 获取系统基本信息
def get_system_basic_info():
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'architecture': platform.machine(),
        'hostname': socket.gethostname(),
        'ip_address': socket.gethostbyname(socket.gethostname()),
        'distro': platform.platform(),
        'kernel_version': platform.uname().release
    }

# 获取CPU信息
def get_cpu_info():
    # 获取CPU时间信息，用于计算用户态/内核态比例
    cpu_times = psutil.cpu_times_percent(interval=0.1)
    
    return {
        'physical_cores': psutil.cpu_count(logical=False),
        'total_cores': psutil.cpu_count(logical=True),
        'cpu_usage': psutil.cpu_percent(interval=0.1, percpu=True),
        'cpu_usage_total': psutil.cpu_percent(interval=0.1),
        'user_mode': cpu_times.user,
        'system_mode': cpu_times.system,
        'idle_mode': cpu_times.idle
    }

# 获取内存信息
def get_memory_info():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        'total': mem.total,
        'available': mem.available,
        'used': mem.used,
        'free': mem.free,
        'cached': getattr(mem, 'cached', 0),
        'buffers': getattr(mem, 'buffers', 0),
        'shared': getattr(mem, 'shared', 0),
        'usage_percent': mem.percent,
        'swap_total': swap.total,
        'swap_used': swap.used,
        'swap_free': swap.free,
        'swap_percent': swap.percent
    }

# 获取磁盘信息
def get_disk_info():
    disks = []
    disk_io = psutil.disk_io_counters()
    
    for partition in psutil.disk_partitions():
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        disks.append({
            'device': partition.device,
            'mountpoint': partition.mountpoint,
            'file_system': partition.fstype,
            'total': partition_usage.total,
            'used': partition_usage.used,
            'free': partition_usage.free,
            'usage_percent': partition_usage.percent
        })
    
    return {
        'partitions': disks,
        'io_total_read_bytes': disk_io.read_bytes,
        'io_total_write_bytes': disk_io.write_bytes,
        'io_read_count': disk_io.read_count,
        'io_write_count': disk_io.write_count,
        'io_read_time': disk_io.read_time,
        'io_write_time': disk_io.write_time
    }

# 获取网络信息
def get_network_info():
    net_io = psutil.net_io_counters()
    networks = []
    
    for interface_name, interface_stats in psutil.net_if_addrs().items():
        addresses = []
        for address in interface_stats:
            if str(address.family) == 'AddressFamily.AF_INET':
                addresses.append({
                    'ip': address.address,
                    'netmask': address.netmask,
                    'broadcast': address.broadcast
                })
        networks.append({
            'interface': interface_name,
            'addresses': addresses
        })
    
    return {
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv,
        'packets_sent': net_io.packets_sent,
        'packets_recv': net_io.packets_recv,
        'errors_in': net_io.errin,
        'errors_out': net_io.errout,
        'dropped_in': net_io.dropin,
        'dropped_out': net_io.dropout,
        'networks': networks
    }

# 获取系统负载（仅Linux）
def get_load_average():
    if platform.system() == 'Linux':
        return list(os.getloadavg())
    return [0, 0, 0]

# 获取系统运行时间
def get_uptime():
    boot_time = psutil.boot_time()
    current_time = time.time()
    uptime_seconds = int(current_time - boot_time)
    
    days = uptime_seconds // (24 * 3600)
    hours = (uptime_seconds % (24 * 3600)) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    return {
        'seconds': uptime_seconds,
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds_remaining': seconds,
        'formatted': f"{days}天 {hours}小时 {minutes}分钟"
    }

# 主函数，获取所有系统信息
def get_system_info():
    return {
        'basic': get_system_basic_info(),
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'disk': get_disk_info(),
        'network': get_network_info(),
        'load_average': get_load_average(),
        'system_uptime': get_uptime(),
        'panel_uptime': get_panel_uptime()
    }

# 获取实时系统状态（简化版，适合频繁调用）
def get_real_time_status():
    """获取实时系统状态，适合频繁调用"""
    return {
        'cpu_usage': psutil.cpu_percent(interval=0.01),
        'memory_usage': psutil.virtual_memory().percent,
        'network_sent': psutil.net_io_counters().bytes_sent,
        'network_recv': psutil.net_io_counters().bytes_recv,
        'disk_read': psutil.disk_io_counters().read_bytes,
        'disk_write': psutil.disk_io_counters().write_bytes,
        'timestamp': time.time()
    }
