import bcrypt
from config.config import Config
import json
import os

# 获取所有用户
def get_all_users():
    # 返回用户信息，但不包含密码
    users = {}
    for username, user_data in Config.USERS.items():
        users[username] = {
            'role': user_data['role']
        }
    return users

# 添加用户
def add_user(username, password, role='user'):
    if username in Config.USERS:
        return {
            'status': 'error',
            'message': f'User {username} already exists'
        }
    
    # 使用bcrypt哈希密码
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    Config.USERS[username] = {
        'password': hashed_password.decode('utf-8'),
        'role': role
    }
    
    # 保存到配置文件（这里只是模拟，实际应该保存到数据库或文件）
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
    
    # 使用bcrypt哈希新密码
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    Config.USERS[username]['password'] = hashed_password.decode('utf-8')
    
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
    
    valid_roles = ['admin', 'user']
    if new_role not in valid_roles:
        return {
            'status': 'error',
            'message': f'Invalid role: {new_role}. Valid roles are: {', '.join(valid_roles)}'