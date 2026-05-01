from flask import request, jsonify
from config.config import Config

# IP白名单验证中间件
def ip_whitelist_required(f):
    def decorated(*args, **kwargs):
        # 如果IP白名单未启用，直接通过
        if not Config.IP_WHITELIST_ENABLED:
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
        if role not in Config.IP_WHITELIST:
            return jsonify({
                'status': 'error',
                'message': 'IP whitelist not configured for this role'
            }), 403
        
        # 检查客户端IP是否在白名单中
        if client_ip not in Config.IP_WHITELIST[role]:
            return jsonify({
                'status': 'error',
                'message': 'IP address not allowed'
            }), 403
        
        return f(*args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

# 安全响应头中间件
def secure_headers(response):
    # 添加安全响应头
    for header, value in Config.SECURE_HEADERS.items():
        response.headers[header] = value
    
    return response
