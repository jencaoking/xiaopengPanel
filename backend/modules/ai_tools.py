"""
AI 工具集

定义 Agent 可调用的工具，按安全级别分级：
- L1 只读：自动执行，无副作用
- L2 诊断：自动执行，仅分析不修改
- L3 执行：需人工确认，修改系统状态
- L4 危险：双重确认 + 审计，执行命令/脚本

每个工具包含：
- OpenAI Function Calling 格式的 schema
- 执行函数
- 安全级别
- 审计标记
"""

import json
import time
import logging
import subprocess
import shlex
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

# 安全级别
SAFETY_LEVELS = {
    'L1': '只读，自动执行',
    'L2': '诊断，自动执行',
    'L3': '执行，需确认',
    'L4': '危险，双重确认',
}

# 危险命令黑名单
DANGEROUS_PATTERNS = [
    'rm -rf /', 'rm -rf ~', 'rm -rf *', 'mkfs', 'dd if=', 'shutdown',
    'reboot', 'halt', 'init 0', 'init 6', ':(){:|:&};:',
    'chmod -R 777 /', 'chown -R', '>/dev/sda', 'mv / ',
]

# 允许执行的命令白名单前缀（L3 级别）
ALLOWED_COMMAND_PREFIXES = [
    'systemctl', 'service', 'journalctl', 'top', 'ps', 'df', 'du',
    'free', 'uptime', 'cat /var/log', 'tail', 'head', 'grep',
    'netstat', 'ss', 'lsof', 'iostat', 'vmstat', 'sar',
    'nginx -t', 'mysqladmin', 'redis-cli', 'psql',
    'find /var/log', 'find /tmp',
]


def _truncate(text: str, max_len: int = 4000) -> str:
    """截断文本到指定长度"""
    if not text:
        return ''
    if len(text) <= max_len:
        return text
    return text[:max_len] + f'\n... (已截断，共 {len(text)} 字符)'


def _safe_str(data: Any) -> str:
    """安全转换为字符串"""
    try:
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


# ==================== L1 只读工具 ====================

def tool_get_system_status(params: Dict) -> Dict:
    """获取系统实时状态"""
    from modules.system_info import get_real_time_status, get_system_info
    status = get_real_time_status()
    info = get_system_info()
    return {
        'status': 'success',
        'data': {
            'hostname': info.get('hostname'),
            'os': info.get('os'),
            'uptime': info.get('uptime'),
            'cpu_usage': status.get('cpu_usage'),
            'memory_usage': status.get('memory_usage'),
            'disk_usage': status.get('disk_usage'),
            'load_average': status.get('load_average'),
            'network': status.get('network', {}),
        }
    }


def tool_get_processes(params: Dict) -> Dict:
    """获取进程列表（可排序/搜索）"""
    from modules.process_manager import get_processes
    sort_by = params.get('sort_by', 'cpu')
    sort_order = params.get('sort_order', 'desc')
    search = params.get('search')
    result = get_processes(sort_by=sort_by, sort_order=sort_order, search_term=search)
    # 只返回 Top 20 进程避免过长
    processes = result.get('processes', [])[:20]
    return {
        'status': 'success',
        'data': {
            'total': result.get('total', len(processes)),
            'processes': processes,
        }
    }


def tool_get_services(params: Dict) -> Dict:
    """获取服务列表"""
    from modules.service_manager import get_services
    result = get_services()
    services = result.get('services', [])
    # 可按状态过滤
    filter_status = params.get('filter')
    if filter_status:
        services = [s for s in services if s.get('status') == filter_status]
    return {
        'status': 'success',
        'data': {
            'total': len(services),
            'services': services[:30],
        }
    }


def tool_get_service_logs(params: Dict) -> Dict:
    """获取服务日志"""
    from modules.service_manager import get_service_logs
    service_name = params.get('service_name')
    if not service_name:
        return {'status': 'error', 'message': 'service_name 必填'}
    result = get_service_logs(
        service_name=service_name,
        time_range=params.get('time_range', 'today'),
        keyword=params.get('keyword'),
        limit=int(params.get('limit', 50)),
    )
    logs = result.get('logs', '')
    return {
        'status': 'success',
        'data': _truncate(_safe_str(logs), 6000),
    }


def tool_get_system_logs(params: Dict) -> Dict:
    """获取系统日志"""
    from modules.log_manager import get_logs
    result = get_logs(
        log_type=params.get('log_type', 'system'),
        limit=int(params.get('limit', 50)),
        level=params.get('level', 'INFO'),
    )
    return {
        'status': 'success',
        'data': _truncate(_safe_str(result), 6000),
    }


def tool_search_logs(params: Dict) -> Dict:
    """搜索日志"""
    from modules.log_manager import search_logs
    keyword = params.get('keyword', '')
    if not keyword:
        return {'status': 'error', 'message': 'keyword 必填'}
    result = search_logs(keyword=keyword, limit=int(params.get('limit', 50)))
    return {
        'status': 'success',
        'data': _truncate(_safe_str(result), 6000),
    }


def tool_get_alerts(params: Dict) -> Dict:
    """获取系统告警"""
    from modules.system_monitor import metrics_collector
    status = params.get('status', 'active')
    result = metrics_collector.get_alerts(status=status, limit=int(params.get('limit', 50)))
    return {
        'status': 'success',
        'data': result.get('alerts', []),
    }


def tool_get_metrics_history(params: Dict) -> Dict:
    """获取指标历史"""
    from modules.system_monitor import metrics_collector
    metric = params.get('metric', 'cpu')
    hours = int(params.get('hours', 1))
    try:
        realtime = metrics_collector.get_realtime_metrics()
        return {
            'status': 'success',
            'data': {
                'realtime': realtime,
                'metric': metric,
                'hours': hours,
            }
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def tool_get_disk_info(params: Dict) -> Dict:
    """获取磁盘信息"""
    from modules.system_info import get_disk_info
    result = get_disk_info()
    return {'status': 'success', 'data': result}


def tool_get_network_info(params: Dict) -> Dict:
    """获取网络信息"""
    from modules.system_info import get_network_info
    result = get_network_info()
    return {'status': 'success', 'data': result}


def tool_read_file(params: Dict) -> Dict:
    """读取文件内容（受白名单限制）"""
    from modules.file_manager import read_file
    from config.config import config_instance
    path = params.get('path', '')
    if not path:
        return {'status': 'error', 'message': 'path 必填'}

    # 检查是否在白名单目录
    whitelist = config_instance.FILE_MANAGER_WHITELIST_DIRS
    allowed = any(path.startswith(wd['path']) for wd in whitelist)
    if not allowed:
        return {'status': 'error', 'message': '文件不在允许的目录范围内'}

    result = read_file(path)
    return {
        'status': result.get('status', 'success'),
        'data': _truncate(result.get('content', ''), 6000),
    }


# ==================== L2 诊断工具 ====================

def tool_analyze_process_anomaly(params: Dict) -> Dict:
    """分析进程异常（高CPU/内存占用）"""
    from modules.process_manager import get_processes
    result = get_processes(sort_by='cpu', sort_order='desc')
    processes = result.get('processes', [])[:10]

    anomalies = []
    for p in processes:
        cpu = float(p.get('cpu', 0))
        mem = float(p.get('memory', 0))
        if cpu > 80:
            anomalies.append({
                'pid': p.get('pid'),
                'name': p.get('name'),
                'cpu': cpu,
                'memory': mem,
                'issue': 'CPU 占用过高',
                'severity': 'critical' if cpu > 95 else 'warning',
            })
        if mem > 50:
            anomalies.append({
                'pid': p.get('pid'),
                'name': p.get('name'),
                'cpu': cpu,
                'memory': mem,
                'issue': '内存占用过高',
                'severity': 'critical' if mem > 80 else 'warning',
            })

    return {
        'status': 'success',
        'data': {
            'top_processes': processes,
            'anomalies': anomalies,
            'analysis': f'发现 {len(anomalies)} 个异常进程' if anomalies else '未发现异常进程',
        }
    }


def tool_diagnose_service(params: Dict) -> Dict:
    """诊断服务状态"""
    from modules.service_manager import get_service_status, get_service_logs
    service_name = params.get('service_name')
    if not service_name:
        return {'status': 'error', 'message': 'service_name 必填'}

    status = get_service_status(service_name)
    logs_result = get_service_logs(service_name=service_name, time_range='today', limit=30)
    logs = logs_result.get('logs', '')

    issues = []
    if status.get('status') != 'active':
        issues.append(f"服务状态异常: {status.get('status')}")
    if 'error' in _safe_str(logs).lower():
        issues.append('日志中存在错误信息')
    if 'failed' in _safe_str(logs).lower():
        issues.append('日志中存在失败记录')

    return {
        'status': 'success',
        'data': {
            'service': service_name,
            'current_status': status,
            'recent_logs': _truncate(_safe_str(logs), 4000),
            'issues': issues,
        }
    }


def tool_correlate_metrics(params: Dict) -> Dict:
    """关联分析系统指标"""
    from modules.system_info import get_real_time_status
    from modules.system_monitor import metrics_collector

    status = get_real_time_status()
    realtime = {}
    try:
        realtime = metrics_collector.get_realtime_metrics()
    except Exception:
        pass

    correlations = []
    cpu = float(status.get('cpu_usage', 0))
    mem = float(status.get('memory_usage', 0))
    disk = float(status.get('disk_usage', 0))
    load = status.get('load_average', {})

    if isinstance(load, dict):
        load_1 = float(load.get('1min', 0))
    else:
        load_1 = 0

    if cpu > 80 and load_1 > 2:
        correlations.append('CPU 高负载且系统负载偏高，可能存在计算密集型任务')
    if mem > 85 and disk > 90:
        correlations.append('内存和磁盘均高占用，可能导致系统性能严重下降')
    if cpu > 90:
        correlations.append('CPU 严重过载，建议检查高占用进程')

    return {
        'status': 'success',
        'data': {
            'metrics': {
                'cpu': cpu,
                'memory': mem,
                'disk': disk,
                'load': load,
                'realtime': realtime,
            },
            'correlations': correlations,
        }
    }


# ==================== L3 执行工具（需确认） ====================

def tool_restart_service(params: Dict, operator: str = 'ai_agent') -> Dict:
    """重启服务"""
    from modules.service_manager import manage_service
    from modules.log_manager import log_operation
    service_name = params.get('service_name')
    if not service_name:
        return {'status': 'error', 'message': 'service_name 必填'}

    log_operation(operator, 'ai_restart_service', '', f'AI 重启服务: {service_name}')
    result = manage_service(service_name, 'restart')
    return {
        'status': result.get('status', 'success'),
        'data': result,
        'message': f'服务 {service_name} 重启结果: {result.get("message", "")}',
    }


def tool_manage_service(params: Dict, operator: str = 'ai_agent') -> Dict:
    """管理服务（start/stop/restart/reload）"""
    from modules.service_manager import manage_service
    from modules.log_manager import log_operation
    service_name = params.get('service_name')
    action = params.get('action', 'restart')
    if not service_name:
        return {'status': 'error', 'message': 'service_name 必填'}

    if action not in ('start', 'stop', 'restart', 'reload'):
        return {'status': 'error', 'message': f'不支持的操作: {action}'}

    log_operation(operator, f'ai_service_{action}', '', f'AI {action} 服务: {service_name}')
    result = manage_service(service_name, action)
    return {
        'status': result.get('status', 'success'),
        'data': result,
        'message': f'服务 {service_name} {action} 结果: {result.get("message", "")}',
    }


def tool_kill_process(params: Dict, operator: str = 'ai_agent') -> Dict:
    """终止进程"""
    from modules.process_manager import manage_process
    from modules.log_manager import log_operation
    pid = params.get('pid')
    if not pid:
        return {'status': 'error', 'message': 'pid 必填'}

    log_operation(operator, 'ai_kill_process', '', f'AI 终止进程: PID={pid}')
    result = manage_process(int(pid), 'kill')
    return {
        'status': result.get('status', 'success'),
        'data': result,
        'message': f'进程 {pid} 终止结果: {result.get("message", "")}',
    }


def tool_clean_cache(params: Dict, operator: str = 'ai_agent') -> Dict:
    """清理缓存（内存/日志/临时文件）"""
    import os
    import glob
    from modules.log_manager import log_operation

    cache_type = params.get('cache_type', 'memory')
    results = []

    if cache_type in ('memory', 'all'):
        try:
            # 同步缓存到磁盘
            with open('/proc/sys/vm/drop_caches', 'w') as f:
                f.write('3')
            results.append('内存缓存已清理')
        except Exception as e:
            results.append(f'内存缓存清理失败: {e}')

    if cache_type in ('tmp', 'all'):
        try:
            tmp_dir = '/tmp'
            cleaned = 0
            for item in glob.glob(os.path.join(tmp_dir, '*')):
                # 只清理7天前的临时文件
                if os.path.isfile(item):
                    mtime = os.path.getmtime(item)
                    if time.time() - mtime > 7 * 24 * 3600:
                        os.remove(item)
                        cleaned += 1
            results.append(f'清理 {cleaned} 个临时文件')
        except Exception as e:
            results.append(f'临时文件清理失败: {e}')

    log_operation(operator, 'ai_clean_cache', '', f'AI 清理缓存: {cache_type}')

    return {
        'status': 'success',
        'data': {'results': results, 'cache_type': cache_type},
        'message': '; '.join(results),
    }


# ==================== L4 危险工具（双重确认） ====================

def tool_execute_command(params: Dict, operator: str = 'ai_agent') -> Dict:
    """执行系统命令（严格白名单限制）"""
    from modules.log_manager import log_operation, log_system

    command = params.get('command', '').strip()
    if not command:
        return {'status': 'error', 'message': 'command 必填'}

    # 危险命令检查
    cmd_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            log_system(f'AI 拒绝执行危险命令: {command}', 'WARNING', 'ai')
            return {'status': 'error', 'message': f'命令包含危险模式 "{pattern}"，已拒绝执行'}

    # 白名单检查
    allowed = False
    for prefix in ALLOWED_COMMAND_PREFIXES:
        if cmd_lower.startswith(prefix):
            allowed = True
            break

    if not allowed:
        return {'status': 'error', 'message': f'命令 "{command}" 不在允许的白名单中'}

    log_operation(operator, 'ai_execute_command', '', f'AI 执行命令: {command}')
    log_system(f'AI 执行命令: {command}', 'INFO', 'ai')

    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout or result.stderr or ''
        return {
            'status': 'success' if result.returncode == 0 else 'error',
            'data': {
                'command': command,
                'returncode': result.returncode,
                'output': _truncate(output, 4000),
            },
            'message': f'命令执行完成，返回码: {result.returncode}',
        }
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': '命令执行超时（30秒）'}
    except Exception as e:
        return {'status': 'error', 'message': f'命令执行失败: {e}'}


# ==================== 工具注册表 ====================

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # L1 只读
    'get_system_status': {
        'level': 'L1',
        'func': tool_get_system_status,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_system_status',
                'description': '获取系统实时状态，包括CPU、内存、磁盘使用率、负载、网络等',
                'parameters': {'type': 'object', 'properties': {}, 'required': []},
            }
        }
    },
    'get_processes': {
        'level': 'L1',
        'func': tool_get_processes,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_processes',
                'description': '获取进程列表（按CPU或内存排序，Top 20）',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'sort_by': {'type': 'string', 'enum': ['cpu', 'memory', 'pid'], 'default': 'cpu'},
                        'sort_order': {'type': 'string', 'enum': ['asc', 'desc'], 'default': 'desc'},
                        'search': {'type': 'string', 'description': '搜索关键词'},
                    },
                    'required': [],
                },
            }
        }
    },
    'get_services': {
        'level': 'L1',
        'func': tool_get_services,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_services',
                'description': '获取系统服务列表及状态',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'filter': {'type': 'string', 'enum': ['active', 'inactive', 'failed'], 'description': '按状态过滤'},
                    },
                    'required': [],
                },
            }
        }
    },
    'get_service_logs': {
        'level': 'L1',
        'func': tool_get_service_logs,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_service_logs',
                'description': '获取指定服务的日志',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'service_name': {'type': 'string', 'description': '服务名称'},
                        'time_range': {'type': 'string', 'default': 'today'},
                        'keyword': {'type': 'string', 'description': '关键词过滤'},
                        'limit': {'type': 'integer', 'default': 50},
                    },
                    'required': ['service_name'],
                },
            }
        }
    },
    'get_system_logs': {
        'level': 'L1',
        'func': tool_get_system_logs,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_system_logs',
                'description': '获取系统日志',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'log_type': {'type': 'string', 'default': 'system'},
                        'level': {'type': 'string', 'default': 'INFO'},
                        'limit': {'type': 'integer', 'default': 50},
                    },
                    'required': [],
                },
            }
        }
    },
    'search_logs': {
        'level': 'L1',
        'func': tool_search_logs,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'search_logs',
                'description': '搜索日志关键词',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'keyword': {'type': 'string'},
                        'limit': {'type': 'integer', 'default': 50},
                    },
                    'required': ['keyword'],
                },
            }
        }
    },
    'get_alerts': {
        'level': 'L1',
        'func': tool_get_alerts,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_alerts',
                'description': '获取系统告警列表',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string', 'enum': ['active', 'resolved'], 'default': 'active'},
                        'limit': {'type': 'integer', 'default': 50},
                    },
                    'required': [],
                },
            }
        }
    },
    'get_metrics_history': {
        'level': 'L1',
        'func': tool_get_metrics_history,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_metrics_history',
                'description': '获取监控指标历史数据',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'metric': {'type': 'string', 'default': 'cpu'},
                        'hours': {'type': 'integer', 'default': 1},
                    },
                    'required': [],
                },
            }
        }
    },
    'get_disk_info': {
        'level': 'L1',
        'func': tool_get_disk_info,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_disk_info',
                'description': '获取磁盘分区使用情况',
                'parameters': {'type': 'object', 'properties': {}, 'required': []},
            }
        }
    },
    'get_network_info': {
        'level': 'L1',
        'func': tool_get_network_info,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'get_network_info',
                'description': '获取网络接口和连接信息',
                'parameters': {'type': 'object', 'properties': {}, 'required': []},
            }
        }
    },
    'read_file': {
        'level': 'L1',
        'func': tool_read_file,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'read_file',
                'description': '读取白名单目录内的文件内容',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': '文件绝对路径'},
                    },
                    'required': ['path'],
                },
            }
        }
    },
    # L2 诊断
    'analyze_process_anomaly': {
        'level': 'L2',
        'func': tool_analyze_process_anomaly,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'analyze_process_anomaly',
                'description': '分析进程异常（高CPU/内存占用），返回异常进程列表',
                'parameters': {'type': 'object', 'properties': {}, 'required': []},
            }
        }
    },
    'diagnose_service': {
        'level': 'L2',
        'func': tool_diagnose_service,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'diagnose_service',
                'description': '诊断指定服务的状态和日志，识别问题',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'service_name': {'type': 'string', 'description': '服务名称'},
                    },
                    'required': ['service_name'],
                },
            }
        }
    },
    'correlate_metrics': {
        'level': 'L2',
        'func': tool_correlate_metrics,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'correlate_metrics',
                'description': '关联分析系统指标，发现潜在问题关联',
                'parameters': {'type': 'object', 'properties': {}, 'required': []},
            }
        }
    },
    # L3 执行（需确认）
    'restart_service': {
        'level': 'L3',
        'func': tool_restart_service,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'restart_service',
                'description': '重启指定服务（需用户确认）',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'service_name': {'type': 'string', 'description': '服务名称'},
                    },
                    'required': ['service_name'],
                },
            }
        }
    },
    'manage_service': {
        'level': 'L3',
        'func': tool_manage_service,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'manage_service',
                'description': '管理服务：start/stop/restart/reload（需用户确认）',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'service_name': {'type': 'string'},
                        'action': {'type': 'string', 'enum': ['start', 'stop', 'restart', 'reload']},
                    },
                    'required': ['service_name', 'action'],
                },
            }
        }
    },
    'kill_process': {
        'level': 'L3',
        'func': tool_kill_process,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'kill_process',
                'description': '终止指定进程（需用户确认）',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'pid': {'type': 'integer', 'description': '进程ID'},
                    },
                    'required': ['pid'],
                },
            }
        }
    },
    'clean_cache': {
        'level': 'L3',
        'func': tool_clean_cache,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'clean_cache',
                'description': '清理系统缓存（内存/临时文件，需用户确认）',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'cache_type': {'type': 'string', 'enum': ['memory', 'tmp', 'all'], 'default': 'memory'},
                    },
                    'required': [],
                },
            }
        }
    },
    # L4 危险（双重确认）
    'execute_command': {
        'level': 'L4',
        'func': tool_execute_command,
        'schema': {
            'type': 'function',
            'function': {
                'name': 'execute_command',
                'description': '执行系统命令（严格白名单限制，需双重确认）',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'command': {'type': 'string', 'description': '要执行的命令'},
                    },
                    'required': ['command'],
                },
            }
        }
    },
}


def get_tool_schemas(levels: Optional[List[str]] = None) -> List[Dict]:
    """
    获取工具的 OpenAI schema 列表

    :param levels: 安全级别过滤 ['L1','L2','L3','L4']，None 表示全部
    """
    schemas = []
    for name, info in TOOL_REGISTRY.items():
        if levels is None or info['level'] in levels:
            schemas.append(info['schema'])
    return schemas


def get_tool_names(levels: Optional[List[str]] = None) -> List[str]:
    """获取工具名称列表"""
    names = []
    for name, info in TOOL_REGISTRY.items():
        if levels is None or info['level'] in levels:
            names.append(name)
    return names


def execute_tool(tool_name: str, params: Dict, operator: str = 'ai_agent') -> Dict:
    """
    执行指定工具

    :param tool_name: 工具名称
    :param params: 参数
    :param operator: 操作者（用于审计）
    :return: 执行结果
    """
    if tool_name not in TOOL_REGISTRY:
        return {'status': 'error', 'message': f'未知工具: {tool_name}'}

    info = TOOL_REGISTRY[tool_name]
    func: Callable = info['func']

    try:
        # L3/L4 工具需要 operator 参数
        if info['level'] in ('L3', 'L4'):
            return func(params, operator=operator)
        else:
            return func(params)
    except Exception as e:
        logger.exception(f'工具执行异常: {tool_name}')
        return {'status': 'error', 'message': f'工具执行失败: {e}'}


def get_tool_info(tool_name: str) -> Optional[Dict]:
    """获取工具信息（级别、描述）"""
    if tool_name not in TOOL_REGISTRY:
        return None
    info = TOOL_REGISTRY[tool_name]
    return {
        'name': tool_name,
        'level': info['level'],
        'description': info['schema']['function']['description'],
        'safety': SAFETY_LEVELS.get(info['level'], ''),
    }


def list_all_tools() -> List[Dict]:
    """列出所有工具信息"""
    tools = []
    for name, info in TOOL_REGISTRY.items():
        tools.append({
            'name': name,
            'level': info['level'],
            'description': info['schema']['function']['description'],
            'safety': SAFETY_LEVELS.get(info['level'], ''),
            'parameters': info['schema']['function']['parameters'],
        })
    return tools
