from functools import wraps
from flask import request, jsonify
from config.config import Config, config_instance
from modules import rbac
from modules.log_manager import log_system


# IP白名单验证中间件
def ip_whitelist_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 如果IP白名单未启用，直接通过
        # IP_WHITELIST_ENABLED 为 @property，须通过实例访问
        if not config_instance.IP_WHITELIST_ENABLED:
            return f(*args, **kwargs)

        # 获取客户端IP
        client_ip = request.remote_addr

        # 从请求中获取用户信息
        user = getattr(request, 'user', None)

        # 如果用户未认证，允许访问（认证由其他中间件处理）
        if not user:
            return f(*args, **kwargs)

        username = user.get('username')
        role = user.get('role')

        # 检查用户角色是否在白名单配置中
        if role not in config_instance.IP_WHITELIST:
            return jsonify({
                'status': 'error',
                'message': 'IP whitelist not configured by this role'
            }), 403

        # 检查客户端IP是否在白名单中
        if client_ip not in config_instance.IP_WHITELIST[role]:
            return jsonify({
                'status': 'error',
                'message': 'IP address not allowed'
            }), 403

        return f(*args, **kwargs)

    return decorated


def require_permission(permission):
    """
    细粒度权限校验装饰器。

    必须在 @authenticate 之后使用（依赖 request.user）。
    用法:
        @api.route('/users', methods=['POST'])
        @authenticate
        @require_permission('user:create')
        def add_user_route():
            ...

    :param permission: 所需权限，格式 "资源:操作"，例如 "user:create"
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, 'user', None)
            if not user:
                # 未认证（理论上 authenticate 已拦截），兜底处理
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required'
                }), 401

            role = user.get('role')
            if not role:
                return jsonify({
                    'status': 'error',
                    'message': 'User role not found'
                }), 403

            # 通过 RBAC 引擎校验权限
            if not rbac.check_user_permission(role, permission):
                username = user.get('username', 'unknown')
                log_system(
                    f'Permission denied: user={username} role={role} '
                    f'required={permission} path={request.path}',
                    'WARN', 'rbac'
                )
                return jsonify({
                    'status': 'error',
                    'message': '权限不足，无法执行此操作',
                    'required_permission': permission
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# 安全响应头中间件
def secure_headers(response):
    # 添加安全响应头
    for header, value in Config.SECURE_HEADERS.items():
        response.headers[header] = value

    return response
