from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config.config import Config, config_instance
from modules.middleware import secure_headers

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}})

app.after_request(secure_headers)

# 简单的内存速率限制器
class RateLimiter:
    """基于内存的简单速率限制器"""
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, key):
        """检查请求是否允许"""
        import time
        now = time.time()

        if key not in self.requests:
            self.requests[key] = []

        # 清理过期的请求记录
        self.requests[key] = [t for t in self.requests[key] if now - t < self.window_seconds]

        if len(self.requests[key]) >= self.max_requests:
            return False

        self.requests[key].append(now)
        return True

    def cleanup(self):
        """清理过期的请求记录"""
        import time
        now = time.time()
        expired_keys = []
        for key, timestamps in self.requests.items():
            self.requests[key] = [t for t in timestamps if now - t < self.window_seconds]
            if not self.requests[key]:
                expired_keys.append(key)
        for key in expired_keys:
            del self.requests[key]


# 全局速率限制器实例
# 登录接口：5次/分钟
login_limiter = RateLimiter(max_requests=5, window_seconds=60)
# 通用API：100次/分钟
api_limiter = RateLimiter(max_requests=100, window_seconds=60)


def rate_limit(limiter):
    """速率限制装饰器"""
    from functools import wraps
    from flask import request

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr or 'unknown'
            if not limiter.is_allowed(client_ip):
                return jsonify({
                    'status': 'error',
                    'message': 'Rate limit exceeded. Please try again later.'
                }), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator

try:
    from modules.terminal_manager import init_socketio
    socketio = init_socketio(app)
except ImportError:
    socketio = None
except Exception as e:
    print(f"Warning: Could not initialize SocketIO: {e}")
    socketio = None

# 健康检查路由
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

# 导入API路由并注册蓝图
from api.routes import api
app.register_blueprint(api, url_prefix='/api')

# 添加获取和更新配置的API端点
@app.route('/api/config/panel', methods=['GET'])
def get_panel_config():
    """获取面板配置"""
    from modules.auth import authenticate
    from modules.middleware import ip_whitelist_required
    return authenticate(lambda: ip_whitelist_required(lambda: jsonify({
        'port': config_instance.PORT,
        'host': config_instance.HOST,
        'debug': config_instance.DEBUG
    })))()

@app.route('/api/config/panel', methods=['PUT'])
def update_panel_config():
    """更新面板配置"""
    from flask import request
    from modules.auth import authenticate
    from modules.middleware import ip_whitelist_required
    from modules.port_utils import validate_port
    
    def update_config():
        data = request.json
        
        # 验证端口
        if 'port' in data:
            is_valid, message = validate_port(data['port'])
            if not is_valid:
                return jsonify({'status': 'error', 'message': message})
            config_instance.PORT = data['port']
        
        if 'host' in data:
            config_instance.HOST = data['host']
        
        if 'debug' in data:
            config_instance.DEBUG = data['debug']
        
        return jsonify({'status': 'success', 'message': 'Panel configuration updated successfully. Please restart the service for changes to take effect.'})
    
    return authenticate(lambda: ip_whitelist_required(update_config))()

@app.route('/api/config/restart', methods=['POST'])
def restart_service_route():
    """重启服务"""
    from modules.auth import authenticate
    from modules.middleware import ip_whitelist_required
    from modules.port_utils import restart_service
    
    def restart():
        if restart_service():
            return jsonify({'status': 'success', 'message': 'Service is restarting...'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to restart service'})
    
    return authenticate(lambda: ip_whitelist_required(restart))()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    if socketio:
        socketio.run(app, host=config_instance.HOST, port=config_instance.PORT, debug=config_instance.DEBUG, allow_unsafe_werkzeug=True)
    else:
        app.run(host=config_instance.HOST, port=config_instance.PORT, debug=config_instance.DEBUG, use_reloader=False)
