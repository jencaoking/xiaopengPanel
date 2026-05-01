import platform
import subprocess
import datetime
import psutil

# 获取系统时间信息
def get_system_time():
    return {
        'current_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'timezone': datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo.__str__()
    }

# 设置系统时间（Windows）
def set_windows_time(new_time):
    try:
        # 将时间格式转换为Windows系统命令格式
        # 示例：2023-01-01 12:00:00 -> 2023-01-01,12:00:00
        time_str = new_time.replace(' ', ',')
        subprocess.run(['date', time_str.split(',')[0]], check=True, shell=True)
        subprocess.run(['time', time_str.split(',')[1]], check=True, shell=True)
        return {
            'status': 'success',
            'message': 'System time updated successfully'
        }
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f'Failed to update system time: {e.stderr.strip()}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# 设置系统时间（Linux）
def set_linux_time(new_time):
    try:
        subprocess.run(['date', '-s', new_time], check=True, shell=True)
        # 同步硬件时钟
        subprocess.run(['hwclock', '--systohc'], check=True, shell=True)
        return {
            'status': 'success',
            'message': 'System time updated successfully'
        }
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f'Failed to update system time: {e.stderr.strip()}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# 获取网络配置
def get_network_config():
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
    return networks

# 获取系统配置
def get_system_config():
    return {
        'time': get_system_time(),
        'network': get_network_config()
    }

# 更新系统配置
def update_system_config(config):
    if 'time' in config:
        new_time = config['time']
        if platform.system() == 'Windows':
            result = set_windows_time(new_time)
        elif platform.system() == 'Linux':
            result = set_linux_time(new_time)
        else:
            return {
                'status': 'error',
                'message': f'Unsupported OS: {platform.system()}'
            }
        return result
    
    # 其他配置项可以在这里添加
    return {
        'status': 'success',
        'message': 'System configuration updated successfully'
    }
