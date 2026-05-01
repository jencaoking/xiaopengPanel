import psutil
import os
import platform
import time

# 获取进程列表
def get_processes(sort_by=None, sort_order='asc', search_term=None):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time', 'username', 'status', 'cmdline']):
        try:
            process_info = proc.info
            
            # 构建完整的命令行
            cmdline = process_info.get('cmdline', [])
            full_command = ' '.join(cmdline) if cmdline else ''
            
            # 搜索过滤
            if search_term:
                search_term_lower = search_term.lower()
                if (search_term_lower not in process_info['name'].lower() and
                    search_term_lower not in str(process_info['pid']) and
                    search_term_lower not in full_command.lower() and
                    search_term_lower not in process_info.get('username', '').lower()):
                    continue
            
            processes.append({
                'pid': process_info['pid'],
                'name': process_info['name'],
                'cpu_percent': process_info['cpu_percent'],
                'memory_percent': process_info['memory_percent'],
                'create_time': process_info['create_time'],
                'username': process_info['username'],
                'status': process_info['status'],
                'full_command': full_command
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # 排序处理
    if sort_by:
        reverse = (sort_order == 'desc')
        if sort_by == 'cpu_percent':
            processes.sort(key=lambda x: x['cpu_percent'], reverse=reverse)
        elif sort_by == 'memory_percent':
            processes.sort(key=lambda x: x['memory_percent'], reverse=reverse)
        elif sort_by == 'pid':
            processes.sort(key=lambda x: x['pid'], reverse=reverse)
        elif sort_by == 'name':
            processes.sort(key=lambda x: x['name'].lower(), reverse=reverse)
        elif sort_by == 'create_time':
            processes.sort(key=lambda x: x['create_time'], reverse=reverse)
    
    return processes

# 获取进程详情
def get_process_detail(pid):
    try:
        process = psutil.Process(pid)
        
        process_info = process.as_dict(attrs=[
            'pid', 'name', 'cpu_percent', 'memory_percent', 'create_time',
            'username', 'status', 'cmdline', 'cwd', 'exe', 'memory_info',
            'cpu_times', 'num_threads', 'num_handles', 'open_files'
        ])
        
        # 格式化数据
        return {
            'pid': process_info['pid'],
            'name': process_info['name'],
            'cpu_percent': process_info['cpu_percent'],
            'memory_percent': process_info['memory_percent'],
            'memory_used': process_info['memory_info'].rss,
            'create_time': process_info['create_time'],
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process_info['create_time'])),
            'username': process_info['username'],
            'status': process_info['status'],
            'cmdline': ' '.join(process_info['cmdline']) if process_info['cmdline'] else '',
            'cwd': process_info['cwd'],
            'exe': process_info['exe'],
            'cpu_times': {
                'user': process_info['cpu_times'].user,
                'system': process_info['cpu_times'].system
            },
            'num_threads': process_info['num_threads'],
            'num_handles': process_info.get('num_handles', 0),
            'open_files': [f.path for f in process_info.get('open_files', [])]
        }
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied:
        return {'error': 'Access denied'}
    except Exception as e:
        return {'error': str(e)}

# 管理单个进程
def manage_process(pid, action):
    try:
        process = psutil.Process(pid)
        
        if action == 'stop':
            process.terminate()
            process.wait(timeout=5)
            return {
                'status': 'success',
                'message': f'Process {pid} terminated successfully'
            }
        elif action == 'kill':
            process.kill()
            return {
                'status': 'success',
                'message': f'Process {pid} killed successfully'
            }
        elif action == 'restart':
            # 安全警告：通过API重启任意进程存在严重风险
            # 1. os.execvp 会替换当前进程内存空间（Flask主进程将被替换）
            # 2. cmdline 可能被恶意进程篡改，导致执行任意命令
            # 3. 进程终止超时后可能仍然存在
            # 因此，此功能已被禁用，请使用服务管理功能代替
            return {
                'status': 'error',
                'message': 'Process restart is not supported via API for security reasons. Please use service management instead.'
            }
        else:
            return {
                'status': 'error',
                'message': f'Invalid action: {action}'
            }
    except psutil.NoSuchProcess:
        return {
            'status': 'error',
            'message': f'Process {pid} not found'
        }
    except psutil.AccessDenied:
        return {
            'status': 'error',
            'message': f'Access denied to process {pid}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# 批量管理进程
def manage_processes(pids, action):
    results = []
    for pid in pids:
        result = manage_process(pid, action)
        results.append({
            'pid': pid,
            'status': result['status'],
            'message': result['message']
        })
    
    # 统计结果
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count
    
    return {
        'status': 'partial' if error_count > 0 else 'success',
        'total': len(results),
        'success': success_count,
        'error': error_count,
        'results': results
    }
