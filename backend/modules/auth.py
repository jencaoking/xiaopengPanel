import jwt
import time
import bcrypt
import re
import threading
from functools import wraps
from flask import request, jsonify, g
from config.config import Config, config_instance
from modules.log_manager import log_operation, log_system
from modules import rbac


def get_current_user_permissions(role):
    """获取指定角色用户的权限列表（供其他模块使用）"""
    return rbac.get_user_permissions(role)

# 密码强度检测
PASSWORD_PATTERN = {
    'min_length': 8,
    'max_length': 32,
    'require_lowercase': True,
    'require_uppercase': True,
    'require_digit': True,
    'require_special': True
}

def check_password_strength(password):
    """检查密码强度"""
    # 检查长度
    if len(password) < PASSWORD_PATTERN['min_length']:
        return False, f"密码长度至少为{PASSWORD_PATTERN['min_length']}个字符"
    if len(password) > PASSWORD_PATTERN['max_length']:
        return False, f"密码长度不能超过{PASSWORD_PATTERN['max_length']}个字符"
    
    # 检查是否包含小写字母
    if PASSWORD_PATTERN['require_lowercase'] and not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"
    
    # 检查是否包含大写字母
    if PASSWORD_PATTERN['require_uppercase'] and not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"
    
    # 检查是否包含数字
    if PASSWORD_PATTERN['require_digit'] and not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"
    
    # 检查是否包含特殊字符
    special_chars = '!@#$%^&*(),.?":{}|<>'
    if PASSWORD_PATTERN['require_special'] and not any(c in special_chars for c in password):
        return False, f"密码必须包含至少一个特殊字符({special_chars})"
    
    return True, "密码强度符合要求"

# 修改密码函数
def change_password(username, old_password, new_password):
    """修改用户密码"""
    # 验证用户是否存在
    if username not in Config.USERS:
        return {'status': 'error', 'message': '用户不存在'}, 404
    
    # 验证原密码
    if not old_password or not Config.USERS[username].get('password'):
        return {'status': 'error', 'message': '密码不能为空'}, 400
    
    try:
        if not bcrypt.checkpw(old_password.encode('utf-8'), Config.USERS[username]['password'].encode('utf-8')):
            return {'status': 'error', 'message': '原密码错误'}, 401
    except Exception as e:
        return {'status': 'error', 'message': '密码验证失败'}, 500
    
    # 检查新密码强度
    is_valid, message = check_password_strength(new_password)
    if not is_valid:
        return {'status': 'error', 'message': message}, 400
    
    # 生成新密码的哈希值
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    # 更新密码
    if config_instance.update_user_password(username, hashed_password.decode('utf-8')):
        # 记录密码修改成功日志
        log_operation(username, 'change_password', request.remote_addr, 'Password changed successfully')
        log_system(f'User {username} changed password from {request.remote_addr}', 'INFO', 'auth')
        return {'status': 'success', 'message': '密码修改成功'}, 200
    else:
        # 记录密码修改失败日志
        log_operation(username, 'change_password', request.remote_addr, 'Password change failed', 'ERROR')
        log_system(f'User {username} failed to change password from {request.remote_addr}', 'ERROR', 'auth')
        return {'status': 'error', 'message': '密码修改失败'}, 500

# JWT过期时间
JWT_EXPIRE_TIME = 3600  # 1小时
REFRESH_TOKEN_EXPIRE_TIME = 7 * 24 * 3600  # 7天

# 获取JWT密钥的函数（动态获取，确保配置更新后生效）
def get_jwt_secret():
    return Config.SECRET_KEY

# 登录尝试记录
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5分钟


def _cleanup_old_login_attempts():
    """清理过期的登录尝试记录，防止内存泄漏"""
    now = time.time()
    expired_users = []
    for username, (attempts, last_attempt) in login_attempts.items():
        if now - last_attempt > LOCKOUT_TIME * 2:
            expired_users.append(username)
    for username in expired_users:
        del login_attempts[username]


def _schedule_cleanup():
    """定期清理登录尝试记录"""
    _cleanup_old_login_attempts()
    # 每5分钟清理一次
    timer = threading.Timer(300, _schedule_cleanup)
    timer.daemon = True
    timer.start()


# 启动定期清理
_schedule_cleanup()

# 登录函数
def login(data):
    username = data.get('username')
    password = data.get('password')
    client_ip = request.remote_addr
    
    # 检查登录尝试次数
    if username in login_attempts:
        attempts, last_attempt = login_attempts[username]
        if attempts >= MAX_LOGIN_ATTEMPTS:
            # 检查是否还在锁定时间内
            if time.time() - last_attempt < LOCKOUT_TIME:
                return {
                    'status': 'error',
                    'message': f'登录尝试次数过多，请{int((LOCKOUT_TIME - (time.time() - last_attempt)) / 60)}分钟后再试'
                }, 403
            else:
                # 重置登录尝试次数
                login_attempts[username] = [0, time.time()]
    else:
        login_attempts[username] = [0, time.time()]
    
    # 验证用户
    if username in Config.USERS:
        # 使用bcrypt验证密码
        if bcrypt.checkpw(password.encode('utf-8'), Config.USERS[username]['password'].encode('utf-8')):
            # 重置登录尝试次数
            login_attempts[username] = [0, time.time()]

            # 检查用户是否被禁用
            from modules.user_manager import is_user_disabled
            if is_user_disabled(username):
                log_system(f'Disabled user {username} attempted login from {client_ip}', 'WARN', 'auth')
                return {
                    'status': 'error',
                    'message': '该账户已被禁用，请联系管理员'
                }, 403

            # 检查是否启用了2FA
            from modules.totp_manager import get_2fa_status
            totp_status = get_2fa_status(username)
            if totp_status.get('enabled'):
                # 2FA已启用，生成临时令牌供二次验证使用
                temp_token = jwt.encode(
                    {
                        'username': username,
                        'role': Config.USERS[username]['role'],
                        'exp': time.time() + 300,  # 5分钟有效期
                        'iat': time.time(),
                        'type': '2fa_pending'
                    },
                    get_jwt_secret(),
                    algorithm='HS256'
                )

                log_system(f'User {username} requires 2FA verification from {client_ip}', 'INFO', 'auth')

                return {
                    'status': '2fa_required',
                    'message': '请输入双因素认证验证码',
                    'temp_token': temp_token
                }, 200

            # 2FA未启用，直接生成JWT令牌
            user_role = Config.USERS[username]['role']
            user_permissions = rbac.get_user_permissions(user_role)
            token = jwt.encode(
                {
                    'username': username,
                    'role': user_role,
                    'permissions': user_permissions,
                    'exp': time.time() + JWT_EXPIRE_TIME,
                    'iat': time.time()
                },
                get_jwt_secret(),
                algorithm='HS256'
            )

            # 生成刷新令牌
            refresh_token = jwt.encode(
                {
                    'username': username,
                    'exp': time.time() + REFRESH_TOKEN_EXPIRE_TIME,
                    'iat': time.time(),
                    'type': 'refresh'
                },
                get_jwt_secret(),
                algorithm='HS256'
            )

            # 记录登录成功日志
            log_operation(username, 'login', client_ip, 'Login successful')
            log_system(f'User {username} logged in from {client_ip}', 'INFO', 'auth')

            return {
                'status': 'success',
                'message': 'Login successful',
                'token': token,
                'refresh_token': refresh_token,
                'token_expires_in': JWT_EXPIRE_TIME,
                'user': {
                    'username': username,
                    'role': user_role,
                    'permissions': user_permissions
                }
            }
        else:
            # 增加登录尝试次数
            login_attempts[username][0] += 1
            login_attempts[username][1] = time.time()
            remaining_attempts = MAX_LOGIN_ATTEMPTS - login_attempts[username][0]
            return {
                'status': 'error',
                'message': f'用户名或密码错误，还有{remaining_attempts}次尝试机会'
            }, 401
    else:
        return {
            'status': 'error',
            'message': 'Invalid username or password'
        }, 401

# 刷新令牌函数
def refresh_token(data):
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return {
            'status': 'error',
            'message': 'Refresh token is missing'
        }, 400
    
    try:
        # 验证刷新令牌
        payload = jwt.decode(refresh_token, get_jwt_secret(), algorithms=['HS256'])
        
        # 检查令牌类型
        if payload.get('type') != 'refresh':
            return {
                'status': 'error',
                'message': 'Invalid refresh token type'
            }, 400
        
        username = payload.get('username')
        
        # 检查用户是否存在
        if username not in Config.USERS:
            return {
                'status': 'error',
                'message': 'User not found'
            }, 404
        
        # 生成新的访问令牌
        user_role = Config.USERS[username]['role']
        user_permissions = rbac.get_user_permissions(user_role)
        new_token = jwt.encode(
            {
                'username': username,
                'role': user_role,
                'permissions': user_permissions,
                'exp': time.time() + JWT_EXPIRE_TIME,
                'iat': time.time()
            },
            get_jwt_secret(),
            algorithm='HS256'
        )

        return {
            'status': 'success',
            'message': 'Token refreshed successfully',
            'token': new_token,
            'token_expires_in': JWT_EXPIRE_TIME,
            'user': {
                'username': username,
                'role': user_role,
                'permissions': user_permissions
            }
        }
    except jwt.ExpiredSignatureError:
        return {
            'status': 'error',
            'message': 'Refresh token has expired'
        }, 401
    except jwt.InvalidTokenError:
        return {
            'status': 'error',
            'message': 'Invalid refresh token'
        }, 401

# 认证装饰器
def authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Token is missing'
            }), 401
        
        # 移除Bearer前缀
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            # 验证JWT令牌
            payload = jwt.decode(token, get_jwt_secret(), algorithms=['HS256'])
            # 确保权限信息存在（兼容旧令牌：从角色实时加载）
            if 'permissions' not in payload:
                payload['permissions'] = rbac.get_user_permissions(payload.get('role'))
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({
                'status': 'error',
                'message': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid token'
            }), 401
        
        return f(*args, **kwargs)

    return decorated


# 2FA登录验证函数
def verify_2fa_login(data):
    """验证2FA登录验证码，完成登录"""
    temp_token = data.get('temp_token')
    verification_code = data.get('verification_code')
    client_ip = request.remote_addr

    if not temp_token or not verification_code:
        return {
            'status': 'error',
            'message': '临时令牌和验证码不能为空'
        }, 400

    try:
        # 验证临时令牌
        payload = jwt.decode(temp_token, get_jwt_secret(), algorithms=['HS256'])

        # 检查令牌类型
        if payload.get('type') != '2fa_pending':
            return {
                'status': 'error',
                'message': '无效的令牌类型'
            }, 400

        username = payload.get('username')

        # 检查用户是否存在
        if username not in Config.USERS:
            return {
                'status': 'error',
                'message': 'User not found'
            }, 404

        # 验证2FA验证码
        from modules.totp_manager import verify_2fa_login as verify_code
        if not verify_code(username, verification_code):
            log_system(f'User {username} failed 2FA verification from {client_ip}', 'WARN', 'auth')
            return {
                'status': 'error',
                'message': '验证码错误'
            }, 401

        # 2FA验证成功，生成正式JWT令牌
        user_role = Config.USERS[username]['role']
        user_permissions = rbac.get_user_permissions(user_role)
        token = jwt.encode(
            {
                'username': username,
                'role': user_role,
                'permissions': user_permissions,
                'exp': time.time() + JWT_EXPIRE_TIME,
                'iat': time.time()
            },
            get_jwt_secret(),
            algorithm='HS256'
        )

        # 生成刷新令牌
        refresh_token = jwt.encode(
            {
                'username': username,
                'exp': time.time() + REFRESH_TOKEN_EXPIRE_TIME,
                'iat': time.time(),
                'type': 'refresh'
            },
            get_jwt_secret(),
            algorithm='HS256'
        )

        # 记录登录成功日志
        log_operation(username, 'login_2fa', client_ip, 'Login successful with 2FA')
        log_system(f'User {username} logged in with 2FA from {client_ip}', 'INFO', 'auth')

        return {
            'status': 'success',
            'message': 'Login successful',
            'token': token,
            'refresh_token': refresh_token,
            'token_expires_in': JWT_EXPIRE_TIME,
            'user': {
                'username': username,
                'role': user_role,
                'permissions': user_permissions
            }
        }

    except jwt.ExpiredSignatureError:
        return {
            'status': 'error',
            'message': '临时令牌已过期，请重新登录'
        }, 401
    except jwt.InvalidTokenError:
        return {
            'status': 'error',
            'message': '无效的临时令牌'
        }, 401
