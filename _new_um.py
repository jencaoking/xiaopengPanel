import bcrypt
from flask import request, has_request_context
from config.config import Config, config_instance
from modules import rbac
from modules.log_manager import log_system
from modules.auth import check_password_strength


def _get_current_username():
    """获取当前请求的登录用户名（用于安全防护），无请求上下文时返回 None"""
    if not has_request_context():
        return None
    user = getattr(request, 'user', None)
    if isinstance(user, dict):
        return user.get('username')
    return None


# 获取所有用户
def get_all_users():
    users = {}
    for username, user_data in Config.USERS.items():
        users[username] = {
            'role': user_data['role'],
            'status': user_data.get('status', 'active')
        }
    return users


# 获取单个用户信息（不含密码）
def get_user(username):
    if username not in Config.USERS:
        return {'status': 'error', 'message': f'User {username} not found'}
    user_data = Config.USERS[username]
    return {
        'status': 'success',
        'user': {
            'username': username,
            'role': user_data['role'],
            'status': user_data.get('status', 'active')
        }
    }


# 更新用户启用状态
def update_user_status(username, new_status):
    if username not in Config.USERS:
        return {'status': 'error', 'message': f'User {username} not found'}

    if new_status not in ('active', 'disabled'):
        return {'status': 'error', 'message': 'Invalid status, must be "active" or "disabled"'}

    if new_status == 'disabled':
        current = _get_current_username()
        if current == username:
            return {'status': 'error', 'message': '不能禁用当前登录用户'}

    if new_status == 'disabled' and Config.USERS[username].get('role') == 'admin':
        active_admins = sum(
            1 for u, info in Config.USERS.items()
            if info.get('role') == 'admin' and info.get('status', 'active') == 'active'
        )
        if active_admins <= 1:
            return {'status': 'error', 'message': '无法禁用最后一个启用的管理员账户'}

    Config.USERS[username]['status'] = new_status
    config_instance._save_users(Config.USERS)
    StaticConfigSync()
    log_system(f'User status updated: {username} -> {new_status}', 'INFO', 'user')
    return {'status': 'success', 'message': f'Status for user {username} updated to {new_status}'}


def is_user_disabled(username):
    if username not in Config.USERS:
        return False
    return Config.USERS[username].get('status', 'active') == 'disabled'


# 添加用户
def add_user(username, password, role='viewer'):
    if username in Config.USERS:
        return {'status': 'error', 'message': f'User {username} already exists'}

    if not rbac.is_valid_role(role):
        return {'status': 'error', 'message': f'Invalid role: {role}. Valid roles: {", ".join(rbac.get_valid_role_keys())}'}

    is_valid, msg = check_password_strength(password)
    if not is_valid:
        return {'status': 'error', 'message': msg}

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    Config.USERS[username] = {'password': hashed_password.decode('utf-8'), 'role': role}
    config_instance._save_users(Config.USERS)
    StaticConfigSync()
    log_system(f'User added: {username} (role={role})', 'INFO', 'user')
    return {'status': 'success', 'message': f'User {username} added successfully'}


# 修改用户密码
def update_user_password(username, new_password):
    if username not in Config.USERS:
        return {'status': 'error', 'message': f'User {username} not found'}

    is_valid, msg = check_password_strength(new_password)
    if not is_valid:
        return {'status': 'error', 'message': msg}

    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    Config.USERS[username]['password'] = hashed_password.decode('utf-8')
    config_instance._save_users(Config.USERS)
    StaticConfigSync()
    return {'status': 'success', 'message': f'Password for user {username} updated successfully'}


# 修改用户角色
def update_user_role(username, new_role):
    if username not in Config.USERS:
        return {'status': 'error', 'message': f'User {username} not found'}

    if not rbac.is_valid_role(new_role):
        return {'status': 'error', 'message': f'Invalid role: {new_role}. Valid roles: {", ".join(rbac.get_valid_role_keys())}'}

    old_role = Config.USERS[username].get('role')

    if old_role == 'admin' and new_role != 'admin':
        user_status = Config.USERS[username].get('status', 'active')
        if user_status == 'active':
            active_admins = sum(1 for info in Config.USERS.values() if info.get('role') == 'admin' and info.get('status', 'active') == 'active')
            if active_admins <= 1:
                return {'status': 'error', 'message': '无法降级最后一个启用的管理员账户'}

    Config.USERS[username]['role'] = new_role
    config_instance._save_users(Config.USERS)
    StaticConfigSync()
    log_system(f'User role updated: {username} {old_role} -> {new_role}', 'INFO', 'user')
    return {'status': 'success', 'message': f'Role for user {username} updated to {new_role}'}


# 删除用户
def delete_user(username):
    if username not in Config.USERS:
        return {'status': 'error', 'message': f'User {username} not found'}

    current = _get_current_username()
    if current == username:
        return {'status': 'error', 'message': '不能删除当前登录用户'}

    user_info = Config.USERS[username]
    if user_info.get('role') == 'admin' and user_info.get('status', 'active') == 'active':
        active_admins = sum(1 for info in Config.USERS.values() if info.get('role') == 'admin' and info.get('status', 'active') == 'active')
        if active_admins <= 1:
            return {'status': 'error', 'message': '无法删除最后一个启用的管理员账户'}

    del Config.USERS[username]
    config_instance._save_users(Config.USERS)
    StaticConfigSync()
    log_system(f'User deleted: {username}', 'INFO', 'user')
    return {'status': 'success', 'message': f'User {username} deleted successfully'}


def StaticConfigSync():
    try:
        from config.config import StaticConfig
        StaticConfig.USERS = config_instance.USERS
    except Exception as e:
        log_system(f'Failed to sync StaticConfig: {e}', 'WARN', 'user')