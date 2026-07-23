import os
import json
import secrets
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')


def _generate_secret_key():
    """生成安全的随机密钥"""
    return secrets.token_hex(32)

class Config:
    def __init__(self):
        self._config = self._load_config()
        # 初始化配置属性
        self._init_properties()
        # 用户配置文件路径
        self._users_file = os.path.join(os.path.dirname(__file__), 'users.json')
        # 加载用户配置
        self._load_users()
    
    def _load_config(self):
        """从JSON文件加载配置"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 如果配置文件不存在，使用默认配置
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config
        except json.JSONDecodeError:
            # 配置文件格式错误，使用默认配置
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config
    
    def _get_default_config(self):
        """获取默认配置"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        # 优先从环境变量读取密钥，否则生成随机密钥
        env_secret = os.environ.get('XIAOPENG_SECRET_KEY')
        secret_key = env_secret if env_secret else _generate_secret_key()
        return {
            "server": {
                "port": 5000,
                "host": "0.0.0.0"
            },
            "security": {
                "secret_key": secret_key,
                "debug": True,
                "ip_whitelist_enabled": True,
                "ip_whitelist": {
                    "admin": ["127.0.0.1", "::1"],
                    "user": ["127.0.0.1", "::1"]
                }
            },
            "logging": {
                "level": "INFO",
                "dir": "logs",
                "max_bytes": 10485760,
                "backup_count": 5,
                "when": "midnight",
                "interval": 1,
                "retention_days": 30,
                "compress": True,
                "json_format": False,
                "console_enabled": True,
                "console_level": "INFO",
                "console_color": True
            },
            "file_manager": {
                "whitelist_dirs": [
                    {
                        "path": os.path.join(base_dir, "frontend"),
                        "name": "前端目录"
                    },
                    {
                        "path": os.path.join(base_dir, "backend"),
                        "name": "后端目录"
                    }
                ],
                "upload": {
                    "max_size": 10485760,
                    "allowed_types": ["txt", "md", "json", "js", "css", "html", "py", "csv", "xml"],
                    "chunk_size": 1048576,
                    "temp_dir": "temp_uploads"
                },
                "file_operations": {
                    "enabled": True,
                    "log_enabled": True
                },
                "online_edit": {
                    "enabled": True,
                    "allowed_extensions": ["txt", "md", "json", "js", "css", "html", "py", "csv", "xml"],
                    "version_control": {
                        "enabled": True,
                        "max_versions": 10
                    }
                }
            },
            "ai": {
                "enabled": False,
                "provider": "deepseek",
                "api_key": "",
                "model": "deepseek-chat",
                "base_url": "",
                "temperature": 0.3,
                "max_tokens": 4096,
                "max_iterations": 10,
                "auto_repair_enabled": False,
                "confirmation_required": True
            }
        }
    
    def _save_config(self, config):
        """保存配置到JSON文件"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _load_users(self):
        """从JSON文件加载用户配置"""
        try:
            with open(self._users_file, 'r', encoding='utf-8') as f:
                self.USERS = json.load(f)
            # 向后兼容：为旧用户数据补全状态与时间元数据字段
            self._migrate_users_fields()
        except FileNotFoundError:
            # 如果用户配置文件不存在，使用默认配置
            default_users = {
                'admin': {
                    'password': '$2b$12$iWo/NEU8cfu3Mjcvm8Us8.KTCHxNSIBodOhQwGSAM3eS/PSQRYbKC',
                    'role': 'admin'
                }
            }
            self._save_users(default_users)
            self.USERS = default_users
            self._migrate_users_fields()
        except json.JSONDecodeError:
            # 用户配置文件格式错误，使用默认配置
            default_users = {
                'admin': {
                    'password': '$2b$12$iWo/NEU8cfu3Mjcvm8Us8.KTCHxNSIBodOhQwGSAM3eS/PSQRYbKC',
                    'role': 'admin'
                }
            }
            self._save_users(default_users)
            self.USERS = default_users
            self._migrate_users_fields()

    def _migrate_users_fields(self):
        """为旧版本用户数据补全 status/created_at/updated_at 字段，并持久化"""
        now = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
        changed = False
        for username, user_data in self.USERS.items():
            if not isinstance(user_data, dict):
                continue
            if 'status' not in user_data:
                user_data['status'] = 'active'
                changed = True
            if 'created_at' not in user_data:
                user_data['created_at'] = now
                changed = True
            if 'updated_at' not in user_data:
                user_data['updated_at'] = now
                changed = True
        if changed:
            self._save_users(self.USERS)
    
    def _save_users(self, users):
        """保存用户配置到JSON文件"""
        with open(self._users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    
    def _init_properties(self):
        """初始化配置属性"""
        # 项目基础目录
        self.BASE_DIR = os.path.dirname(os.path.dirname(__file__))
        
        # CORS配置
        self.CORS_ORIGINS = [
            'http://localhost:8000', 'http://127.0.0.1:8000',
            'http://localhost:3000', 'http://127.0.0.1:3000'  # vite dev server
        ]
        
        # 安全响应头
        self.SECURE_HEADERS = {
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;",
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    def update_user_password(self, username, password):
        """更新用户密码"""
        if username in self.USERS:
            self.USERS[username]['password'] = password
            self.USERS[username]['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
            self._save_users(self.USERS)
            # 更新静态配置以保持一致性
            StaticConfig.USERS = self.USERS
            return True
        return False

    def verify_user_password(self, username, password):
        """验证用户密码"""
        if username in self.USERS:
            import bcrypt
            return bcrypt.checkpw(password.encode('utf-8'), self.USERS[username]['password'].encode('utf-8'))
        return False

    def add_user(self, username, user_data):
        """添加新用户并持久化"""
        if username in self.USERS:
            return False
        now = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
        user_data.setdefault('status', 'active')
        user_data.setdefault('created_at', now)
        user_data.setdefault('updated_at', now)
        self.USERS[username] = user_data
        self._save_users(self.USERS)
        StaticConfig.USERS = self.USERS
        return True

    def delete_user(self, username):
        """删除用户并持久化"""
        if username not in self.USERS:
            return False
        del self.USERS[username]
        self._save_users(self.USERS)
        StaticConfig.USERS = self.USERS
        return True

    def update_user_role(self, username, role):
        """更新用户角色并持久化"""
        if username not in self.USERS:
            return False
        self.USERS[username]['role'] = role
        self.USERS[username]['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
        self._save_users(self.USERS)
        StaticConfig.USERS = self.USERS
        return True

    def update_user_status(self, username, status):
        """更新用户状态并持久化"""
        if username not in self.USERS:
            return False
        self.USERS[username]['status'] = status
        self.USERS[username]['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
        self._save_users(self.USERS)
        StaticConfig.USERS = self.USERS
        return True

    def count_admins(self):
        """统计处于 active 状态的管理员数量"""
        return sum(
            1 for u in self.USERS.values()
            if isinstance(u, dict) and u.get('role') == 'admin' and u.get('status', 'active') == 'active'
        )
    
    @property
    def SECRET_KEY(self):
        return self._config['security']['secret_key']
    
    @SECRET_KEY.setter
    def SECRET_KEY(self, value):
        self._config['security']['secret_key'] = value
        self._save_config(self._config)
    
    @property
    def DEBUG(self):
        return self._config['security']['debug']
    
    @DEBUG.setter
    def DEBUG(self, value):
        self._config['security']['debug'] = value
        self._save_config(self._config)
    
    @property
    def HOST(self):
        return self._config['server']['host']
    
    @HOST.setter
    def HOST(self, value):
        self._config['server']['host'] = value
        self._save_config(self._config)
    
    @property
    def PORT(self):
        return self._config['server']['port']
    
    @PORT.setter
    def PORT(self, value):
        self._config['server']['port'] = value
        self._save_config(self._config)
    
    @property
    def LOG_LEVEL(self):
        return self._config['logging']['level']
    
    @LOG_LEVEL.setter
    def LOG_LEVEL(self, value):
        self._config['logging']['level'] = value
        self._save_config(self._config)
    
    @property
    def LOG_DIR(self):
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), self._config['logging']['dir'])

    @LOG_DIR.setter
    def LOG_DIR(self, value):
        self._config['logging']['dir'] = os.path.basename(value)
        self._save_config(self._config)

    def _log_cfg(self, key, default=None):
        """读取 logging 配置项，兼容旧版配置文件缺失字段"""
        return self._config.get('logging', {}).get(key, default)

    @property
    def LOG_MAX_BYTES(self):
        return self._log_cfg('max_bytes', 10 * 1024 * 1024)

    @property
    def LOG_BACKUP_COUNT(self):
        return self._log_cfg('backup_count', 5)

    @property
    def LOG_WHEN(self):
        return self._log_cfg('when', 'midnight')

    @property
    def LOG_INTERVAL(self):
        return self._log_cfg('interval', 1)

    @property
    def LOG_RETENTION_DAYS(self):
        return self._log_cfg('retention_days', 30)

    @property
    def LOG_COMPRESS(self):
        return self._log_cfg('compress', True)

    @property
    def LOG_JSON_FORMAT(self):
        return self._log_cfg('json_format', False)

    @property
    def LOG_CONSOLE_ENABLED(self):
        return self._log_cfg('console_enabled', True)

    @property
    def LOG_CONSOLE_LEVEL(self):
        return self._log_cfg('console_level', 'INFO')

    @property
    def LOG_CONSOLE_COLOR(self):
        return self._log_cfg('console_color', True)
    
    @property
    def IP_WHITELIST_ENABLED(self):
        return self._config['security']['ip_whitelist_enabled']
    
    @IP_WHITELIST_ENABLED.setter
    def IP_WHITELIST_ENABLED(self, value):
        self._config['security']['ip_whitelist_enabled'] = value
        self._save_config(self._config)
    
    @property
    def IP_WHITELIST(self):
        return self._config['security']['ip_whitelist']
    
    @IP_WHITELIST.setter
    def IP_WHITELIST(self, value):
        self._config['security']['ip_whitelist'] = value
        self._save_config(self._config)
    
    # 文件管理配置
    @property
    def FILE_MANAGER_WHITELIST_DIRS(self):
        return self._config.get('file_manager', {}).get('whitelist_dirs', [])
    
    @FILE_MANAGER_WHITELIST_DIRS.setter
    def FILE_MANAGER_WHITELIST_DIRS(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        self._config['file_manager']['whitelist_dirs'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_UPLOAD_MAX_SIZE(self):
        return self._config.get('file_manager', {}).get('upload', {}).get('max_size', 10485760)
    
    @FILE_MANAGER_UPLOAD_MAX_SIZE.setter
    def FILE_MANAGER_UPLOAD_MAX_SIZE(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'upload' not in self._config['file_manager']:
            self._config['file_manager']['upload'] = {}
        self._config['file_manager']['upload']['max_size'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_UPLOAD_ALLOWED_TYPES(self):
        return self._config.get('file_manager', {}).get('upload', {}).get('allowed_types', [])
    
    @FILE_MANAGER_UPLOAD_ALLOWED_TYPES.setter
    def FILE_MANAGER_UPLOAD_ALLOWED_TYPES(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'upload' not in self._config['file_manager']:
            self._config['file_manager']['upload'] = {}
        self._config['file_manager']['upload']['allowed_types'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_UPLOAD_CHUNK_SIZE(self):
        return self._config.get('file_manager', {}).get('upload', {}).get('chunk_size', 1048576)
    
    @FILE_MANAGER_UPLOAD_CHUNK_SIZE.setter
    def FILE_MANAGER_UPLOAD_CHUNK_SIZE(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'upload' not in self._config['file_manager']:
            self._config['file_manager']['upload'] = {}
        self._config['file_manager']['upload']['chunk_size'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_UPLOAD_TEMP_DIR(self):
        return self._config.get('file_manager', {}).get('upload', {}).get('temp_dir', 'temp_uploads')
    
    @FILE_MANAGER_UPLOAD_TEMP_DIR.setter
    def FILE_MANAGER_UPLOAD_TEMP_DIR(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'upload' not in self._config['file_manager']:
            self._config['file_manager']['upload'] = {}
        self._config['file_manager']['upload']['temp_dir'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_OPERATIONS_ENABLED(self):
        return self._config.get('file_manager', {}).get('file_operations', {}).get('enabled', True)
    
    @FILE_MANAGER_OPERATIONS_ENABLED.setter
    def FILE_MANAGER_OPERATIONS_ENABLED(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'file_operations' not in self._config['file_manager']:
            self._config['file_manager']['file_operations'] = {}
        self._config['file_manager']['file_operations']['enabled'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_OPERATIONS_LOG_ENABLED(self):
        return self._config.get('file_manager', {}).get('file_operations', {}).get('log_enabled', True)
    
    @FILE_MANAGER_OPERATIONS_LOG_ENABLED.setter
    def FILE_MANAGER_OPERATIONS_LOG_ENABLED(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'file_operations' not in self._config['file_manager']:
            self._config['file_manager']['file_operations'] = {}
        self._config['file_manager']['file_operations']['log_enabled'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_ONLINE_EDIT_ENABLED(self):
        return self._config.get('file_manager', {}).get('online_edit', {}).get('enabled', True)
    
    @FILE_MANAGER_ONLINE_EDIT_ENABLED.setter
    def FILE_MANAGER_ONLINE_EDIT_ENABLED(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'online_edit' not in self._config['file_manager']:
            self._config['file_manager']['online_edit'] = {}
        self._config['file_manager']['online_edit']['enabled'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_ONLINE_EDIT_ALLOWED_EXTENSIONS(self):
        return self._config.get('file_manager', {}).get('online_edit', {}).get('allowed_extensions', [])
    
    @FILE_MANAGER_ONLINE_EDIT_ALLOWED_EXTENSIONS.setter
    def FILE_MANAGER_ONLINE_EDIT_ALLOWED_EXTENSIONS(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'online_edit' not in self._config['file_manager']:
            self._config['file_manager']['online_edit'] = {}
        self._config['file_manager']['online_edit']['allowed_extensions'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_ENABLED(self):
        return self._config.get('file_manager', {}).get('online_edit', {}).get('version_control', {}).get('enabled', True)
    
    @FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_ENABLED.setter
    def FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_ENABLED(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'online_edit' not in self._config['file_manager']:
            self._config['file_manager']['online_edit'] = {}
        if 'version_control' not in self._config['file_manager']['online_edit']:
            self._config['file_manager']['online_edit']['version_control'] = {}
        self._config['file_manager']['online_edit']['version_control']['enabled'] = value
        self._save_config(self._config)
    
    @property
    def FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_MAX_VERSIONS(self):
        return self._config.get('file_manager', {}).get('online_edit', {}).get('version_control', {}).get('max_versions', 10)
    
    @FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_MAX_VERSIONS.setter
    def FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_MAX_VERSIONS(self, value):
        if 'file_manager' not in self._config:
            self._config['file_manager'] = {}
        if 'online_edit' not in self._config['file_manager']:
            self._config['file_manager']['online_edit'] = {}
        if 'version_control' not in self._config['file_manager']['online_edit']:
            self._config['file_manager']['online_edit']['version_control'] = {}
        self._config['file_manager']['online_edit']['version_control']['max_versions'] = value
        self._save_config(self._config)
    
    # 安全配置
    SECURE_HTTP_ONLY = True
    SECURE_SAMESITE = 'Strict'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    def update_config(self, config_dict):
        """更新配置"""
        def update_nested_dict(original, update):
            for key, value in update.items():
                if isinstance(value, dict) and key in original and isinstance(original[key], dict):
                    update_nested_dict(original[key], value)
                else:
                    original[key] = value
        
        update_nested_dict(self._config, config_dict)
        self._save_config(self._config)
        return True
    
    def get_config(self):
        """获取完整配置"""
        return self._config

# 创建全局配置实例
config_instance = Config()

# 同步【普通实例属性】为类属性，使 Config.XXX 类访问生效
# 注：USERS / BASE_DIR / CORS_ORIGINS / SECURE_HEADERS 在 __init__ 中以 self.X = ... 赋值（非 @property），
#     类访问默认会 AttributeError，此处显式暴露为类属性是安全的。
#     其余 SECRET_KEY / DEBUG / HOST / PORT / LOG_LEVEL / LOG_DIR / IP_WHITELIST* 为 @property，
#     覆盖类属性会破坏 setter（app.py 动态更新配置 / 测试用例依赖 setter），故不在此同步，
#     相关调用方应使用 config_instance.XXX 访问。
Config.USERS = config_instance.USERS
Config.BASE_DIR = os.path.dirname(os.path.dirname(__file__))
Config.CORS_ORIGINS = config_instance.CORS_ORIGINS
Config.SECURE_HEADERS = config_instance.SECURE_HEADERS

# 为了保持向后兼容，提供Config类的静态访问方式
class StaticConfig:
    SECRET_KEY = config_instance.SECRET_KEY
    DEBUG = config_instance.DEBUG
    HOST = config_instance.HOST
    PORT = config_instance.PORT
    LOG_LEVEL = config_instance.LOG_LEVEL
    LOG_DIR = config_instance.LOG_DIR
    USERS = config_instance.USERS
    IP_WHITELIST_ENABLED = config_instance.IP_WHITELIST_ENABLED
    IP_WHITELIST = config_instance.IP_WHITELIST
    SECURE_HTTP_ONLY = config_instance.SECURE_HTTP_ONLY
    SECURE_SAMESITE = config_instance.SECURE_SAMESITE
    SECURE_PROXY_SSL_HEADER = config_instance.SECURE_PROXY_SSL_HEADER
    CORS_ORIGINS = config_instance.CORS_ORIGINS
    SECURE_HEADERS = config_instance.SECURE_HEADERS
    
    # 文件管理配置
    FILE_MANAGER_WHITELIST_DIRS = config_instance.FILE_MANAGER_WHITELIST_DIRS
    FILE_MANAGER_UPLOAD_MAX_SIZE = config_instance.FILE_MANAGER_UPLOAD_MAX_SIZE
    FILE_MANAGER_UPLOAD_ALLOWED_TYPES = config_instance.FILE_MANAGER_UPLOAD_ALLOWED_TYPES
    FILE_MANAGER_UPLOAD_CHUNK_SIZE = config_instance.FILE_MANAGER_UPLOAD_CHUNK_SIZE
    FILE_MANAGER_UPLOAD_TEMP_DIR = config_instance.FILE_MANAGER_UPLOAD_TEMP_DIR
    FILE_MANAGER_OPERATIONS_ENABLED = config_instance.FILE_MANAGER_OPERATIONS_ENABLED
    FILE_MANAGER_OPERATIONS_LOG_ENABLED = config_instance.FILE_MANAGER_OPERATIONS_LOG_ENABLED
    FILE_MANAGER_ONLINE_EDIT_ENABLED = config_instance.FILE_MANAGER_ONLINE_EDIT_ENABLED
    FILE_MANAGER_ONLINE_EDIT_ALLOWED_EXTENSIONS = config_instance.FILE_MANAGER_ONLINE_EDIT_ALLOWED_EXTENSIONS
    FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_ENABLED = config_instance.FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_ENABLED
    FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_MAX_VERSIONS = config_instance.FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_MAX_VERSIONS

# 保持向后兼容 - 提供 AppConfig 别名指向 StaticConfig
# 注意：原始 Config 类仍然可以通过 type(config_instance) 获取
# 避免覆盖原始 Config 类，使用新的名称 AppConfig
AppConfig = StaticConfig
