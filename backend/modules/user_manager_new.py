import bcrypt
from flask import request, has_request_context
from config.config import Config, config_instance
from modules import rbac
from modules.auth import check_password_strength
from modules.log_manager import log_system


def _get_current_username():
    """安全获取当前登录用户名（供自禁用/自删除防护使用）。

    通过 authenticate 装饰器注入的 request.user 获取。
    在非请求上下文（如测试/脚本）中返回 None，不抛异常。
    """
    if not has_request_context():
        return None
    user = getattr(request, 'user', None)
    if not isinstance(user, dict):
        return None
    return user.get('username')


def _count_active_admins():
    """统计启用的管理员数量（仅 status == 'active'）。"""
    return sum(
        1 for info in Config.USERS.values()
        if info.get('role') == 'admin' and info.get('status', 'active') == 'active'
    )


# 获取所有用户
def get_all_users():
    # 返回用户信息，但不包含密码
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
        return {
            'status': 'error',
            'message': f'User {username} not found'
        }

    if new_status not in ('active', 'disabled'):
        return {
            'status': 'error',
            'message': 'Invalid status, must be "active" or "disabled"'
        }

    # 防止禁用当前登录用户自身
    current_user = _get_current_username()
    if new_status == 'disabled' and current_user is not None and username == current_user:
        return {
            'status': 'error',
            'message': 'MSG_DISABLE_SELF'
        }

    # 防止禁用最后一个启用的管理员
    if new_status == 'disabled' and Config.USERS[username].get('role') == 'admin':
        if _count_active_admins() <= 1:
            return {
                'status': 'error',
                'message': 'MSG_DISABLE_LAST_ADMIN'
            }

    Config.USERS[username]['status'] = new_status
    config_instance._save_users(Config.USERS)
    StaticConfigSync()

    log_system(f'User status updated: {username} -> {new_status}', 'INFO', 'user')
    return {
        'status': 'success',
        'message': f'Status for user {username} updated to {new_status}'
    }


def is_user_disabled(username):
    """检查用户是否被禁用（供登录流程使用）"""
    if username not in Config.USERS:
        return False
    return Config.USERS[username].get('status', 'active') == 'disabled'


# 添加用户
def add_user(username, password, role='viewer'):
    if username in Config.USERS:
        return {
            'status': 'error',
            'message': f'User {username} already exists'
        }

    # 校验角色合法性
    if not rbac.is_valid_role(role):
        return {
            'status': 'error',
            'message': f'Invalid role: {role}. Valid roles: {", ".join(rbac.get_valid_role_keys())}'
        }

    # 校验密码强度
    is_valid, msg = check_password_strength(password)
    if not is_valid:
        return {
            'status': 'error',
            'message': msg
        }

    # 使用bcrypt哈希密码
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    Config.USERS[username] = {
        'password': hashed_password.decode('utf-8'),
        'role': role,
        'status': 'active'
    }

    # 持久化到 users.json
    config_instance._save_users(Config.USERS)
    StaticConfigSync()

    log_system(f'User added: {username} (role={role})', 'INFO', 'user')
    return {
        'status': 'success',
        'message': f'User {username} added successfully'
    }


# 修改用户密码
def update_user_password(username, new_password):
    if username not in Config.USERS:
        return {
            'status': 'error',
            'message': f'User {username} not found'
        }

    # 校验密码强度
    is_valid, msg = check_password_strength(new_password)
    if not is_valid:
        return {
            'status': 'error',
            'message': msg
        }

    # 使用bcrypt哈希新密码
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    Config.USERS[username]['password'] = hashed_password.decode('utf-8')

    config_instance._save_users(Config.USERS)
    StaticConfigSync()

    log_system(f'User password updated: {username}', 'INFO', 'user')
    return {
        'status': 'success',
        'message': f'Password for user {username} updated successfully'
    }


# 修改用户角色
def update_user_role(username, new_role):
    if username not in Config.USERS:
        return {
            'status': 'error',
            'message': f'User {username} not found'
        }

    # 通过 RBAC 引擎校验角色合法性
    if not rbac.is_valid_role(new_role):
        return {
            'status': 'error',
            'message': f'Invalid role: {new_role}. Valid roles: {", ".join(rbac.get_valid_role_keys())}'
        }

    old_role = Config.USERS[username].get('role')

    # 防止降级最后一个启用的管理员
    if old_role == 'admin' and new_role != 'admin':
        if Config.USERS[username].get('status', 'active') == 'active' and _count_active_admins() <= 1:
            return {
                'status': 'error',
                'message': 'MSG_DOWNGRADE_LAST_ADMIN'
            }

    Config.USERS[username]['role'] = new_role

    config_instance._save_users(Config.USERS)
    StaticConfigSync()

    log_system(f'User role updated: {username} {old_role} -> {new_role}', 'INFO', 'user')
    return {
        'status': 'success',
        'message': f'Role for user {username} updated to {new_role}'
    }


# 删除用户
def delete_user(username):
    if username not in Config.USERS:
        return {
            'status': 'error',
            'message': f'User {username} not found'
        }

    # 防止删除当前登录用户自身
    current_user = _get_current_username()
    if current_user is not None and username == current_user:
        return {
            'status': 'error',
            'message': 'MSG_DELETE_SELF'
        }

    # 防止删除最后一个启用的管理员（仅统计 status == 'active' 的管理员）
    if Config.USERS[username].get('role') == 'admin' \
            and Config.USERS[username].get('status', 'active') == 'active' \
            and _count_active_admins() <= 1:
        return {
            'status': 'error',
            'message': 'MSG_DELETE_LAST_ADMIN'
        }

    del Config.USERS[username]
    config_instance._save_users(Config.USERS)
    StaticConfigSync()

    log_system(f'User deleted: {username}', 'INFO', 'user')
    return {
        'status': 'success',
        'message': f'User {username} deleted successfully'
    }


def StaticConfigSync():
    """同步 StaticConfig.USERS 以保持向后兼容"""
    try:
        from config.config import StaticConfig
        StaticConfig.USERS = config_instance.USERS
    except Exception as e:
        log_system(f'Failed to sync StaticConfig: {e}', 'WARN', 'user')
