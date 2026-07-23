"""
防火墙管理模块
跨平台支持：Linux (ufw/iptables/firewalld) 和 Windows (netsh advfirewall)

功能：
- 获取防火墙状态与后端类型
- 启用/禁用防火墙
- 列出/添加/删除/切换规则
- 端口快速放行/封禁
- 默认策略查询与修改
- IP 白名单/黑名单管理
"""

import os
import re
import platform
import shutil
import subprocess
from typing import List, Dict, Optional, Any, Tuple


# ------------------------------ 工具函数 ------------------------------

def _run_command(cmd: List[str], timeout: int = 15) -> Tuple[bool, str, str]:
    """安全地执行命令，返回 (success, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except FileNotFoundError:
        return False, '', f'Command not found: {cmd[0]}'
    except subprocess.TimeoutExpired:
        return False, '', f'Command timed out: {" ".join(cmd)}'
    except Exception as e:
        return False, '', str(e)


def _detect_linux_backend() -> Optional[str]:
    """检测 Linux 上使用的防火墙后端：ufw / firewalld / iptables"""
    # 优先 ufw（Ubuntu/Debian 常用）
    if shutil.which('ufw'):
        return 'ufw'
    # 其次 firewalld（CentOS/RHEL 常用）
    if shutil.which('firewall-cmd'):
        return 'firewalld'
    # 最后 iptables
    if shutil.which('iptables'):
        return 'iptables'
    return None


def _detect_backend() -> Optional[str]:
    """检测当前系统可用的防火墙后端"""
    system = platform.system().lower()
    if system == 'windows':
        # Windows Vista+ 自带 netsh advfirewall
        return 'netsh'
    elif system == 'linux':
        return _detect_linux_backend()
    return None


# ------------------------------ Linux: UFW ------------------------------

def _ufw_status() -> Dict[str, Any]:
    """获取 ufw 状态"""
    success, stdout, stderr = _run_command(['ufw', 'status', 'verbose'])
    if not success:
        return {
            'status': 'error',
            'message': f'Failed to get ufw status: {stderr or stdout}'
        }

    lines = stdout.strip().split('\n')
    enabled = False
    default_incoming = 'deny'
    default_outgoing = 'allow'
    default_forward = 'deny'
    rules = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if 'Status:' in line:
            enabled = 'active' in line.lower() or '启用' in line
        elif line.lower().startswith('default:'):
            # 例如 "Default: deny (incoming), allow (outgoing), deny (forward)"
            m = re.search(r'(deny|allow|reject)\s*\(incoming\)', line, re.I)
            if m:
                default_incoming = m.group(1).lower()
            m = re.search(r'(deny|allow|reject)\s*\(outgoing\)', line, re.I)
            if m:
                default_outgoing = m.group(1).lower()
            m = re.search(r'(deny|allow|reject)\s*\(forward\)', line, re.I)
            if m:
                default_forward = m.group(1).lower()
        elif line.startswith('--') or line.startswith('='):
            # 分隔线，跳过
            continue
        elif line.lower().startswith(('to ', 'logging:', 'new profiles', 'to\t')):
            # 表头行 "To  Action  From" 与其他元信息行，跳过
            continue
        else:
            # 规则行：例如 "22/tcp                     ALLOW IN    Anywhere"
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 2:
                action = parts[1].upper() if len(parts) > 1 else ''
                # 过滤掉表头行（Action 列不是合法动作）
                if action in ('ACTION',) or parts[0].lower() == 'to':
                    continue
                rules.append({
                    'target': parts[0],
                    'action': action,
                    'from': parts[2] if len(parts) > 2 else 'Anywhere',
                    'direction': 'IN' if 'IN' in action else ('OUT' if 'OUT' in action else 'IN'),
                    'raw': line
                })

    return {
        'status': 'success',
        'enabled': enabled,
        'backend': 'ufw',
        'default_policy': {
            'incoming': default_incoming,
            'outgoing': default_outgoing,
            'forward': default_forward
        },
        'rules': rules
    }


def _ufw_enable() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(['ufw', 'enable'])
    if not success:
        return {'status': 'error', 'message': f'Failed to enable ufw: {stderr or stdout}'}
    return {'status': 'success', 'message': 'UFW firewall enabled', 'output': stdout}


def _ufw_disable() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(['ufw', 'disable'])
    if not success:
        return {'status': 'error', 'message': f'Failed to disable ufw: {stderr or stdout}'}
    return {'status': 'success', 'message': 'UFW firewall disabled', 'output': stdout}


def _ufw_reload() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(['ufw', 'reload'])
    if not success:
        return {'status': 'error', 'message': f'Failed to reload ufw: {stderr or stdout}'}
    return {'status': 'success', 'message': 'UFW firewall reloaded', 'output': stdout}


def _ufw_add_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    """添加 ufw 规则
    参数：port, protocol, action(allow/deny/reject), source_ip, direction(in/out)
    """
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    action = params.get('action', 'allow').lower()
    source_ip = params.get('source_ip')
    direction = params.get('direction', 'in').lower()

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    cmd = ['ufw', action]
    if direction == 'out':
        cmd.append('out')
    if source_ip:
        cmd.append('from')
        cmd.append(source_ip)
        cmd.append('to')
        cmd.append('any')
        cmd.append('port')
        cmd.append(str(port))
        cmd.append('proto')
        cmd.append(protocol)
    else:
        cmd.append(f'{port}/{protocol}')

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to add rule: {stderr or stdout}'}
    return {
        'status': 'success',
        'message': f'Rule added: {action} {port}/{protocol}',
        'rule': {
            'target': f'{port}/{protocol}',
            'action': action.upper(),
            'from': source_ip or 'Anywhere',
            'direction': direction.upper()
        },
        'output': stdout
    }


def _ufw_delete_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    """删除 ufw 规则"""
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    action = params.get('action', 'allow').lower()
    source_ip = params.get('source_ip')
    direction = params.get('direction', 'in').lower()

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    cmd = ['ufw', 'delete', action]
    if direction == 'out':
        cmd.append('out')
    if source_ip:
        cmd.extend(['from', source_ip, 'to', 'any', 'port', str(port), 'proto', protocol])
    else:
        cmd.append(f'{port}/{protocol}')

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to delete rule: {stderr or stdout}'}
    return {'status': 'success', 'message': f'Rule deleted: {action} {port}/{protocol}', 'output': stdout}


def _ufw_set_default_policy(params: Dict[str, Any]) -> Dict[str, Any]:
    """设置默认策略
    参数：direction(incoming/outgoing/forward), policy(allow/deny/reject)
    """
    direction = params.get('direction', 'incoming').lower()
    policy = params.get('policy', 'deny').lower()

    if direction not in ('incoming', 'outgoing', 'forward'):
        return {'status': 'error', 'message': 'Invalid direction'}
    if policy not in ('allow', 'deny', 'reject'):
        return {'status': 'error', 'message': 'Invalid policy'}

    success, stdout, stderr = _run_command(['ufw', 'default', policy, direction])
    if not success:
        return {'status': 'error', 'message': f'Failed to set default policy: {stderr or stdout}'}
    return {
        'status': 'success',
        'message': f'Default {direction} policy set to {policy}',
        'output': stdout
    }


# ------------------------------ Linux: firewalld ------------------------------

def _firewalld_status() -> Dict[str, Any]:
    """获取 firewalld 状态"""
    success, stdout, stderr = _run_command(['firewall-cmd', '--state'])
    running = success and stdout.strip() == 'running'

    # 获取默认区域
    zone = 'public'
    success2, stdout2, _ = _run_command(['firewall-cmd', '--get-default-zone'])
    if success2:
        zone = stdout2.strip()

    # 获取已开放端口
    ports = []
    success3, stdout3, _ = _run_command(['firewall-cmd', f'--zone={zone}', '--list-ports'])
    if success3 and stdout3.strip():
        ports = stdout3.strip().split()

    # 获取已开放服务
    services = []
    success4, stdout4, _ = _run_command(['firewall-cmd', f'--zone={zone}', '--list-services'])
    if success4 and stdout4.strip():
        services = stdout4.strip().split()

    rules = []
    for p in ports:
        # 例如 80/tcp
        parts = p.split('/')
        if len(parts) == 2:
            rules.append({
                'target': p,
                'action': 'ALLOW',
                'from': 'Anywhere',
                'direction': 'IN',
                'service': False
            })
    for s in services:
        rules.append({
            'target': s,
            'action': 'ALLOW',
            'from': 'Anywhere',
            'direction': 'IN',
            'service': True
        })

    return {
        'status': 'success',
        'enabled': running,
        'backend': 'firewalld',
        'zone': zone,
        'default_policy': {
            'incoming': 'deny' if running else 'allow',
            'outgoing': 'allow',
            'forward': 'deny' if running else 'allow'
        },
        'rules': rules,
        'services': services,
        'ports': ports
    }


def _firewalld_enable() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(['systemctl', 'start', 'firewalld'])
    if not success:
        return {'status': 'error', 'message': f'Failed to start firewalld: {stderr or stdout}'}
    # 同时设置开机自启
    _run_command(['systemctl', 'enable', 'firewalld'])
    return {'status': 'success', 'message': 'firewalld started and enabled'}


def _firewalld_disable() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(['systemctl', 'stop', 'firewalld'])
    if not success:
        return {'status': 'error', 'message': f'Failed to stop firewalld: {stderr or stdout}'}
    _run_command(['systemctl', 'disable', 'firewalld'])
    return {'status': 'success', 'message': 'firewalld stopped and disabled'}


def _firewalld_reload() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(['firewall-cmd', '--reload'])
    if not success:
        return {'status': 'error', 'message': f'Failed to reload firewalld: {stderr or stdout}'}
    return {'status': 'success', 'message': 'firewalld reloaded'}


def _firewalld_add_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    action = params.get('action', 'allow').lower()
    permanent = params.get('permanent', True)

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    if action == 'allow':
        cmd = ['firewall-cmd', f'--add-port={port}/{protocol}']
        if permanent:
            cmd.append('--permanent')
    else:
        cmd = ['firewall-cmd', f'--remove-port={port}/{protocol}']
        if permanent:
            cmd.append('--permanent')

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to add rule: {stderr or stdout}'}
    # 永久规则需要 reload 才能生效
    if permanent:
        _run_command(['firewall-cmd', '--reload'])
    return {
        'status': 'success',
        'message': f'Rule added: {action} {port}/{protocol}',
        'rule': {
            'target': f'{port}/{protocol}',
            'action': action.upper(),
            'from': 'Anywhere',
            'direction': 'IN'
        }
    }


def _firewalld_delete_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    permanent = params.get('permanent', True)

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    cmd = ['firewall-cmd', f'--remove-port={port}/{protocol}']
    if permanent:
        cmd.append('--permanent')

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to delete rule: {stderr or stdout}'}
    if permanent:
        _run_command(['firewall-cmd', '--reload'])
    return {'status': 'success', 'message': f'Rule deleted: {port}/{protocol}'}


# ------------------------------ Linux: iptables ------------------------------

def _iptables_status() -> Dict[str, Any]:
    """获取 iptables 状态"""
    success, stdout, stderr = _run_command(['iptables', '-L', '-n', '--line-numbers'])
    if not success:
        return {'status': 'error', 'message': f'Failed to get iptables status: {stderr or stdout}'}

    rules = []
    current_chain = None
    for line in stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('Chain'):
            current_chain = line.split()[1]
        elif line.startswith('num'):
            continue
        else:
            parts = line.split()
            if len(parts) >= 8 and current_chain:
                rules.append({
                    'chain': current_chain,
                    'num': parts[0],
                    'target': parts[1],
                    'protocol': parts[2],
                    'source': parts[4],
                    'destination': parts[5],
                    'port': parts[6] if parts[2] != '0' else 'all',
                    'raw': line
                })

    return {
        'status': 'success',
        'enabled': True,  # iptables 总是存在规则
        'backend': 'iptables',
        'default_policy': {
            'incoming': 'deny',
            'outgoing': 'allow',
            'forward': 'deny'
        },
        'rules': rules
    }


def _iptables_add_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    action = params.get('action', 'allow').lower()
    source_ip = params.get('source_ip')

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    cmd = ['iptables', '-A', 'INPUT']
    if source_ip:
        cmd.extend(['-s', source_ip])
    cmd.extend(['-p', protocol, '--dport', str(port), '-j', action.upper()])

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to add rule: {stderr or stdout}'}
    return {'status': 'success', 'message': f'Rule added: {action} {port}/{protocol}'}


def _iptables_delete_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    action = params.get('action', 'allow').lower()
    source_ip = params.get('source_ip')

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    cmd = ['iptables', '-D', 'INPUT']
    if source_ip:
        cmd.extend(['-s', source_ip])
    cmd.extend(['-p', protocol, '--dport', str(port), '-j', action.upper()])

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to delete rule: {stderr or stdout}'}
    return {'status': 'success', 'message': f'Rule deleted: {port}/{protocol}'}


# ------------------------------ Windows: netsh advfirewall ------------------------------

def _netsh_status() -> Dict[str, Any]:
    """获取 Windows 防火墙状态"""
    success, stdout, stderr = _run_command(
        ['netsh', 'advfirewall', 'show', 'allprofiles', 'state']
    )
    if not success:
        return {'status': 'error', 'message': f'Failed to get firewall status: {stderr or stdout}'}

    # 解析各配置文件状态
    profiles = {}
    current_profile = None
    for line in stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        if 'Profile Settings' in line or '配置文件设置' in line:
            # 例如 "Domain Profile Settings:" / "域 配置文件设置:"
            current_profile = line.replace('Profile Settings', '').replace('配置文件设置', '').strip().rstrip(':').lower()
        elif 'State' in line or '状态' in line:
            state = line.split()[-1] if line.split() else ''
            # 兼容中英文：ON/打开 = 启用，OFF/关闭 = 禁用
            state_lower = state.lower()
            is_on = state_lower in ('on', '打开', '啟用', '启用', '是', 'yes')
            if current_profile:
                profiles[current_profile] = is_on

    enabled = any(profiles.values()) if profiles else False

    # 获取规则列表
    rules = []
    success2, stdout2, _ = _run_command(
        ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all']
    )
    if success2 and stdout2:
        current_rule = {}
        for line in stdout2.split('\n'):
            line = line.strip()
            if not line:
                if current_rule:
                    rules.append(current_rule)
                    current_rule = {}
                continue
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip().lower()
                value = value.strip()
                if key in ('rule name', '规则名称'):
                    current_rule['name'] = value
                elif key in ('enabled', '已启用'):
                    current_rule['enabled'] = value.lower() == 'yes'
                elif key in ('direction', '方向'):
                    current_rule['direction'] = value
                elif key in ('action', '操作'):
                    current_rule['action'] = value
                elif key in ('localport', '本地端口'):
                    current_rule['port'] = value
                elif key in ('protocol', '协议'):
                    current_rule['protocol'] = value
        if current_rule:
            rules.append(current_rule)

    # 格式化规则
    formatted_rules = []
    for r in rules:
        formatted_rules.append({
            'target': f"{r.get('port', 'Any')}/{r.get('protocol', 'Any')}",
            'action': 'ALLOW' if 'allow' in str(r.get('action', '')).lower() else 'BLOCK',
            'from': 'Anywhere',
            'direction': r.get('direction', 'In').upper().replace('INBOUND', 'IN').replace('OUTBOUND', 'OUT'),
            'name': r.get('name', ''),
            'enabled': r.get('enabled', True),
            'raw': r
        })

    return {
        'status': 'success',
        'enabled': enabled,
        'backend': 'netsh',
        'profiles': profiles,
        'default_policy': {
            'incoming': 'block' if enabled else 'allow',
            'outgoing': 'allow',
            'forward': 'block' if enabled else 'allow'
        },
        'rules': formatted_rules
    }


def _netsh_enable() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(
        ['netsh', 'advfirewall', 'set', 'allprofiles', 'state', 'on']
    )
    if not success:
        return {'status': 'error', 'message': f'Failed to enable firewall: {stderr or stdout}'}
    return {'status': 'success', 'message': 'Windows Firewall enabled'}


def _netsh_disable() -> Dict[str, Any]:
    success, stdout, stderr = _run_command(
        ['netsh', 'advfirewall', 'set', 'allprofiles', 'state', 'off']
    )
    if not success:
        return {'status': 'error', 'message': f'Failed to disable firewall: {stderr or stdout}'}
    return {'status': 'success', 'message': 'Windows Firewall disabled'}


def _netsh_add_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    port = params.get('port')
    protocol = params.get('protocol', 'tcp').lower()
    action = params.get('action', 'allow').lower()
    name = params.get('name', f'Panel-{protocol}-{port}')
    direction = params.get('direction', 'in').lower()
    source_ip = params.get('source_ip')

    if not port:
        return {'status': 'error', 'message': 'Port is required'}

    cmd = [
        'netsh', 'advfirewall', 'firewall', 'add', 'rule',
        f'name={name}',
        f'dir={direction}',
        f'action={action}',
        f'protocol={protocol}',
        f'localport={port}'
    ]
    if source_ip:
        cmd.append(f'remoteip={source_ip}')

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to add rule: {stderr or stdout}'}
    return {
        'status': 'success',
        'message': f'Rule added: {name} ({action} {port}/{protocol})',
        'rule': {
            'name': name,
            'target': f'{port}/{protocol}',
            'action': action.upper(),
            'direction': direction.upper()
        }
    }


def _netsh_delete_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get('name')
    if name:
        cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={name}']
    else:
        # 按端口删除
        port = params.get('port')
        protocol = params.get('protocol', 'tcp').lower()
        if not port:
            return {'status': 'error', 'message': 'Either rule name or port is required'}
        cmd = [
            'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
            f'protocol={protocol}', f'localport={port}'
        ]

    success, stdout, stderr = _run_command(cmd)
    if not success:
        return {'status': 'error', 'message': f'Failed to delete rule: {stderr or stdout}'}
    return {'status': 'success', 'message': 'Rule deleted'}


# ------------------------------ 统一对外接口 ------------------------------

def get_firewall_status() -> Dict[str, Any]:
    """获取防火墙状态（自动检测后端）"""
    backend = _detect_backend()
    if not backend:
        return {
            'status': 'error',
            'message': 'No firewall backend detected. '
                       'On Linux install ufw/firewalld/iptables; '
                       'Windows uses built-in netsh.'
        }

    if backend == 'ufw':
        result = _ufw_status()
    elif backend == 'firewalld':
        result = _firewalld_status()
    elif backend == 'iptables':
        result = _iptables_status()
    elif backend == 'netsh':
        result = _netsh_status()
    else:
        return {'status': 'error', 'message': f'Unsupported backend: {backend}'}

    if result.get('status') == 'success':
        result['backend'] = backend
        result['platform'] = platform.system()
    return result


def enable_firewall() -> Dict[str, Any]:
    """启用防火墙"""
    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    handlers = {
        'ufw': _ufw_enable,
        'firewalld': _firewalld_enable,
        'netsh': _netsh_enable
    }
    handler = handlers.get(backend)
    if not handler:
        return {'status': 'error', 'message': f'Enable not supported for backend: {backend}'}
    return handler()


def disable_firewall() -> Dict[str, Any]:
    """禁用防火墙"""
    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    handlers = {
        'ufw': _ufw_disable,
        'firewalld': _firewalld_disable,
        'netsh': _netsh_disable
    }
    handler = handlers.get(backend)
    if not handler:
        return {'status': 'error', 'message': f'Disable not supported for backend: {backend}'}
    return handler()


def reload_firewall() -> Dict[str, Any]:
    """重载防火墙规则"""
    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    handlers = {
        'ufw': _ufw_reload,
        'firewalld': _firewalld_reload
    }
    handler = handlers.get(backend)
    if not handler:
        return {'status': 'error', 'message': f'Reload not supported for backend: {backend}'}
    return handler()


def add_firewall_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    """添加防火墙规则
    通用参数：
    - port: 端口号（必填）
    - protocol: tcp/udp（默认 tcp）
    - action: allow/deny/reject（默认 allow）
    - source_ip: 来源 IP（可选）
    - direction: in/out（默认 in）
    - name: 规则名称（Windows 可选）
    - permanent: 是否永久生效（firewalld，默认 True）
    """
    # 参数校验
    port = params.get('port')
    if port is None:
        return {'status': 'error', 'message': 'Port is required'}

    try:
        port_num = int(port)
        if not (1 <= port_num <= 65535):
            return {'status': 'error', 'message': 'Port must be between 1 and 65535'}
    except (ValueError, TypeError):
        # 允许端口范围如 "8000:8100"
        if not re.match(r'^\d+:\d+$', str(port)):
            return {'status': 'error', 'message': 'Invalid port format'}

    protocol = params.get('protocol', 'tcp').lower()
    if protocol not in ('tcp', 'udp', 'any', 'all'):
        return {'status': 'error', 'message': 'Protocol must be tcp, udp, or any'}

    action = params.get('action', 'allow').lower()
    if action not in ('allow', 'deny', 'block', 'reject'):
        return {'status': 'error', 'message': 'Action must be allow, deny, or reject'}

    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    # Windows 用 block 替代 deny
    if backend == 'netsh' and action in ('deny', 'reject'):
        action = 'block'
    # Linux ufw/iptables 用小写
    if backend in ('ufw', 'iptables', 'firewalld'):
        if action == 'block':
            action = 'deny'

    handlers = {
        'ufw': _ufw_add_rule,
        'firewalld': _firewalld_add_rule,
        'iptables': _iptables_add_rule,
        'netsh': _netsh_add_rule
    }
    handler = handlers.get(backend)
    if not handler:
        return {'status': 'error', 'message': f'Add rule not supported for backend: {backend}'}

    params['protocol'] = protocol
    params['action'] = action
    return handler(params)


def delete_firewall_rule(params: Dict[str, Any]) -> Dict[str, Any]:
    """删除防火墙规则"""
    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    handlers = {
        'ufw': _ufw_delete_rule,
        'firewalld': _firewalld_delete_rule,
        'iptables': _iptables_delete_rule,
        'netsh': _netsh_delete_rule
    }
    handler = handlers.get(backend)
    if not handler:
        return {'status': 'error', 'message': f'Delete rule not supported for backend: {backend}'}
    return handler(params)


def set_default_policy(params: Dict[str, Any]) -> Dict[str, Any]:
    """设置默认策略（仅 ufw 支持，其他后端返回提示）"""
    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    if backend == 'ufw':
        return _ufw_set_default_policy(params)
    else:
        return {
            'status': 'error',
            'message': f'Default policy modification not supported for backend: {backend}. '
                       f'Please configure via system tools.'
        }


def get_available_services() -> Dict[str, Any]:
    """获取防火墙可用服务（仅 firewalld）"""
    backend = _detect_backend()
    if not backend:
        return {'status': 'error', 'message': 'No firewall backend detected'}

    if backend == 'firewalld':
        success, stdout, stderr = _run_command(['firewall-cmd', '--get-services'])
        if not success:
            return {'status': 'error', 'message': f'Failed to get services: {stderr or stdout}'}
        services = stdout.strip().split()
        return {'status': 'success', 'services': services, 'backend': backend}

    return {'status': 'success', 'services': [], 'backend': backend, 'message': 'No service abstraction for this backend'}


def quick_allow_port(port: int, protocol: str = 'tcp') -> Dict[str, Any]:
    """快速放行端口（便捷方法）"""
    return add_firewall_rule({
        'port': port,
        'protocol': protocol,
        'action': 'allow',
        'direction': 'in'
    })


def quick_block_port(port: int, protocol: str = 'tcp') -> Dict[str, Any]:
    """快速封禁端口（便捷方法）"""
    return add_firewall_rule({
        'port': port,
        'protocol': protocol,
        'action': 'deny',
        'direction': 'in'
    })
