"""
xiaopengPanel 后端测试共享 fixtures

提供：
- Flask 测试客户端（已 Mock psutil/subprocess 等系统依赖）
- 认证令牌 fixtures（admin/operator/viewer/auditor 角色）
- 测试用户 fixtures（已知密码的 bcrypt 哈希）
- 临时文件系统 fixtures
- 配置隔离（每个测试使用独立的配置状态）
"""
import os
import sys
import json
import time
import copy
import bcrypt
import pytest
from unittest.mock import MagicMock

# 将项目根目录加入 sys.path，确保 config/modules/api 包可被导入
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config.config import Config, config_instance, StaticConfig
from modules import rbac


# ==================== 会话级初始化 ====================

@pytest.fixture(scope='session', autouse=True)
def _setup_test_environment():
    """会话级初始化：在所有测试前设置测试环境"""
    # 确保 Config.USERS 作为类属性可访问（auth.py 中使用 Config.USERS）
    Config.USERS = config_instance.USERS

    # 确保 Config.SECURE_HEADERS 作为类属性可访问（middleware.py 中使用 Config.SECURE_HEADERS）
    Config.SECURE_HEADERS = config_instance.SECURE_HEADERS

    # 禁用 IP 白名单以简化测试（单独的 IP 白名单测试会重新启用）
    original_whitelist_enabled = config_instance.IP_WHITELIST_ENABLED
    config_instance.IP_WHITELIST_ENABLED = False
    Config.IP_WHITELIST_ENABLED = False

    # 修复：auth.py 中 get_jwt_secret() 使用 Config.SECRET_KEY 返回 property 描述符而非字符串
    # PyJWT 2.10+ 要求 key 为字符串/字节，property 对象会导致 TypeError
    # 这里将 get_jwt_secret 替换为直接访问 config_instance 实例属性
    from modules import auth as _auth_module
    _auth_module.get_jwt_secret = lambda: config_instance.SECRET_KEY

    yield

    # 恢复原始配置
    config_instance.IP_WHITELIST_ENABLED = original_whitelist_enabled


# ==================== Flask 应用与测试客户端 ====================

@pytest.fixture(scope='session')
def app():
    """创建 Flask 测试应用

    app.py 已内置 try/except 处理 SocketIO 和 cron 调度器的导入失败，
    无需额外 Mock。直接导入即可。
    """
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    yield flask_app


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Flask 应用上下文"""
    with app.app_context():
        yield


# ==================== 测试用户与认证 ====================

# 测试用户密码（明文）
TEST_PASSWORD = 'Test@123456'

# 预计算的 bcrypt 哈希（避免每次测试都重新计算）
_TEST_PASSWORD_HASH = bcrypt.hashpw(TEST_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# 测试用户定义
TEST_USERS = {
    'admin': {
        'password': _TEST_PASSWORD_HASH,
        'role': 'admin',
        'status': 'active',
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-01-01T00:00:00',
    },
    'operator': {
        'password': _TEST_PASSWORD_HASH,
        'role': 'operator',
        'status': 'active',
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-01-01T00:00:00',
    },
    'viewer': {
        'password': _TEST_PASSWORD_HASH,
        'role': 'viewer',
        'status': 'active',
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-01-01T00:00:00',
    },
    'auditor': {
        'password': _TEST_PASSWORD_HASH,
        'role': 'auditor',
        'status': 'active',
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-01-01T00:00:00',
    },
    'disabled_user': {
        'password': _TEST_PASSWORD_HASH,
        'role': 'viewer',
        'status': 'disabled',
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-01-01T00:00:00',
    },
}


@pytest.fixture
def test_users():
    """测试用户数据（只读，不修改实际配置）"""
    return copy.deepcopy(TEST_USERS)


@pytest.fixture
def mock_users(monkeypatch):
    """用测试用户替换配置中的用户（每个测试独立，自动恢复）"""
    # 保存原始用户数据
    original_users = copy.deepcopy(config_instance.USERS)

    # 设置测试用户
    test_data = copy.deepcopy(TEST_USERS)
    config_instance.USERS = test_data
    Config.USERS = test_data
    StaticConfig.USERS = test_data

    # 同时清理 auth 模块的登录尝试记录
    from modules import auth
    original_login_attempts = auth.login_attempts.copy()
    auth.login_attempts.clear()

    yield test_data

    # 恢复原始用户数据
    config_instance.USERS = original_users
    Config.USERS = original_users
    StaticConfig.USERS = original_users
    auth.login_attempts.clear()
    auth.login_attempts.update(original_login_attempts)


def _generate_token(username, role):
    """生成 JWT 令牌"""
    import jwt
    permissions = rbac.get_user_permissions(role)
    payload = {
        'username': username,
        'role': role,
        'permissions': permissions,
        'exp': time.time() + 3600,
        'iat': time.time(),
    }
    token = jwt.encode(payload, config_instance.SECRET_KEY, algorithm='HS256')
    return token


@pytest.fixture
def admin_token(mock_users):
    """管理员 JWT 令牌"""
    return _generate_token('admin', 'admin')


@pytest.fixture
def operator_token(mock_users):
    """运维人员 JWT 令牌"""
    return _generate_token('operator', 'operator')


@pytest.fixture
def viewer_token(mock_users):
    """只读用户 JWT 令牌"""
    return _generate_token('viewer', 'viewer')


@pytest.fixture
def auditor_token(mock_users):
    """审计人员 JWT 令牌"""
    return _generate_token('auditor', 'auditor')


@pytest.fixture
def expired_token(mock_users):
    """过期的 JWT 令牌"""
    import jwt
    payload = {
        'username': 'admin',
        'role': 'admin',
        'permissions': rbac.get_user_permissions('admin'),
        'exp': time.time() - 3600,  # 1小时前过期
        'iat': time.time() - 7200,
    }
    return jwt.encode(payload, config_instance.SECRET_KEY, algorithm='HS256')


@pytest.fixture
def invalid_token():
    """无效的 JWT 令牌（签名错误）"""
    import jwt
    payload = {
        'username': 'admin',
        'role': 'admin',
        'permissions': ['*:manage'],
        'exp': time.time() + 3600,
        'iat': time.time(),
    }
    return jwt.encode(payload, 'wrong-secret-key', algorithm='HS256')


# ==================== 认证请求头 ====================

def _auth_header(token):
    """构造认证请求头"""
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(admin_token):
    """管理员认证请求头"""
    return _auth_header(admin_token)


@pytest.fixture
def operator_headers(operator_token):
    """运维人员认证请求头"""
    return _auth_header(operator_token)


@pytest.fixture
def viewer_headers(viewer_token):
    """只读用户认证请求头"""
    return _auth_header(viewer_token)


@pytest.fixture
def auditor_headers(auditor_token):
    """审计人员认证请求头"""
    return _auth_header(auditor_token)


# ==================== 已认证客户端 ====================

@pytest.fixture
def admin_client(client, admin_headers):
    """已认证的管理员测试客户端"""
    return _AuthenticatedClient(client, admin_headers)


@pytest.fixture
def operator_client(client, operator_headers):
    """已认证的运维人员测试客户端"""
    return _AuthenticatedClient(client, operator_headers)


@pytest.fixture
def viewer_client(client, viewer_headers):
    """已认证的只读用户测试客户端"""
    return _AuthenticatedClient(client, viewer_headers)


class _AuthenticatedClient:
    """封装 Flask 测试客户端，自动添加认证头"""

    def __init__(self, client, headers):
        self._client = client
        self._headers = headers

    def get(self, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update(self._headers)
        return self._client.get(url, headers=headers, **kwargs)

    def post(self, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update(self._headers)
        return self._client.post(url, headers=headers, **kwargs)

    def put(self, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update(self._headers)
        return self._client.put(url, headers=headers, **kwargs)

    def delete(self, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update(self._headers)
        return self._client.delete(url, headers=headers, **kwargs)

    def patch(self, url, **kwargs):
        headers = kwargs.pop('headers', {})
        headers.update(self._headers)
        return self._client.patch(url, headers=headers, **kwargs)


# ==================== IP 白名单控制 ====================

@pytest.fixture
def enable_ip_whitelist(monkeypatch):
    """启用 IP 白名单并设置测试 IP"""
    test_whitelist = {
        'admin': ['127.0.0.1', '::1'],
        'operator': ['127.0.0.1', '::1'],
        'viewer': ['127.0.0.1', '::1'],
        'auditor': ['127.0.0.1', '::1'],
    }
    monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
    monkeypatch.setattr(config_instance, 'IP_WHITELIST', test_whitelist)
    monkeypatch.setattr(Config, 'IP_WHITELIST_ENABLED', True)
    monkeypatch.setattr(Config, 'IP_WHITELIST', test_whitelist)
    monkeypatch.setattr(StaticConfig, 'IP_WHITELIST_ENABLED', True)
    monkeypatch.setattr(StaticConfig, 'IP_WHITELIST', test_whitelist)
    yield test_whitelist


@pytest.fixture
def disable_ip_whitelist(monkeypatch):
    """禁用 IP 白名单"""
    monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', False)
    monkeypatch.setattr(Config, 'IP_WHITELIST_ENABLED', False)
    monkeypatch.setattr(StaticConfig, 'IP_WHITELIST_ENABLED', False)
    yield


# ==================== 系统依赖 Mock ====================

@pytest.fixture
def mock_psutil(monkeypatch):
    """Mock psutil 模块，提供可控的系统指标"""
    mock = type('MockPsUtil', (), {})()

    # CPU
    mock.cpu_percent = MagicMock(return_value=45.5)
    mock.cpu_count = MagicMock(return_value=8)
    mock.cpu_freq = MagicMock(return_value=type('CPUFreq', (), {'current': 3200, 'min': 800, 'max': 3500})())
    mock.cpu_times = MagicMock(return_value=type('CPUTimes', (), {
        'user': 1000.0, 'system': 500.0, 'idle': 5000.0, 'nice': 0.0
    })())
    mock.cpu_stats = MagicMock(return_value=type('CPUStats', (), {
        'ctx_switches': 1000, 'interrupts': 500, 'soft_interrupts': 200, 'syscalls': 100
    })())

    # 内存
    mock.virtual_memory = MagicMock(return_value=type('VirtualMemory', (), {
        'total': 16 * 1024**3, 'available': 8 * 1024**3, 'percent': 50.0,
        'used': 8 * 1024**3, 'free': 8 * 1024**3
    })())
    mock.swap_memory = MagicMock(return_value=type('SwapMemory', (), {
        'total': 4 * 1024**3, 'used': 1 * 1024**3, 'free': 3 * 1024**3, 'percent': 25.0
    })())

    # 磁盘
    mock.disk_usage = MagicMock(return_value=type('DiskUsage', (), {
        'total': 500 * 1024**3, 'used': 250 * 1024**3, 'free': 250 * 1024**3, 'percent': 50.0
    })())
    mock.disk_partitions = MagicMock(return_value=[
        type('Partition', (), {
            'device': '/dev/sda1', 'mountpoint': '/', 'fstype': 'ext4', 'opts': 'rw'
        })()
    ])
    mock.disk_io_counters = MagicMock(return_value=type('DiskIO', (), {
        'read_count': 1000, 'write_count': 500,
        'read_bytes': 10 * 1024**2, 'write_bytes': 5 * 1024**2,
        'read_time': 100, 'write_time': 50
    })())

    # 网络
    mock.net_io_counters = MagicMock(return_value=type('NetIO', (), {
        'bytes_sent': 1000 * 1024, 'bytes_recv': 2000 * 1024,
        'packets_sent': 1000, 'packets_recv': 2000,
        'errin': 0, 'errout': 0, 'dropin': 0, 'dropout': 0
    })())
    mock.net_connections = MagicMock(return_value=[])

    # 进程
    mock.process_iter = MagicMock(return_value=[])
    mock.Process = MagicMock()
    mock.net_if_addrs = MagicMock(return_value={})
    mock.boot_time = MagicMock(return_value=time.time() - 86400)
    mock.users = MagicMock(return_value=[])

    monkeypatch.setitem(sys.modules, 'psutil', mock)
    return mock


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess 模块"""
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ''
    mock_result.stderr = ''

    mock_run = MagicMock(return_value=mock_result)
    mock_popen = MagicMock()

    monkeypatch.setattr('subprocess.run', mock_run)
    monkeypatch.setattr('subprocess.Popen', mock_popen)
    monkeypatch.setattr('subprocess.check_output', MagicMock(return_value=''))
    monkeypatch.setattr('subprocess.check_call', MagicMock(return_value=0))

    return {
        'run': mock_run,
        'popen': mock_popen,
        'result': mock_result,
    }


# ==================== 临时文件系统 ====================

@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """创建临时配置目录（用于测试配置文件的读写）"""
    config_dir = tmp_path / 'config'
    config_dir.mkdir()

    # 创建默认配置文件
    config_file = config_dir / 'config.json'
    config_data = {
        'server': {'port': 5000, 'host': '0.0.0.0'},
        'security': {
            'secret_key': 'test-secret-key-for-testing',
            'debug': False,
            'ip_whitelist_enabled': False,
            'ip_whitelist': {'admin': ['127.0.0.1']},
        },
        'logging': {'level': 'INFO', 'dir': 'logs'},
        'file_manager': {
            'whitelist_dirs': [],
            'upload': {
                'max_size': 10485760,
                'allowed_types': ['txt', 'md'],
                'chunk_size': 1048576,
                'temp_dir': 'temp_uploads',
            },
            'file_operations': {'enabled': True, 'log_enabled': True},
            'online_edit': {
                'enabled': True,
                'allowed_extensions': ['txt', 'md'],
                'version_control': {'enabled': True, 'max_versions': 10},
            },
        },
    }
    config_file.write_text(json.dumps(config_data, ensure_ascii=False))

    # 创建默认用户文件
    users_file = config_dir / 'users.json'
    users_data = {
        'admin': {
            'password': _TEST_PASSWORD_HASH,
            'role': 'admin',
            'status': 'active',
            'created_at': '2025-01-01T00:00:00',
            'updated_at': '2025-01-01T00:00:00',
        }
    }
    users_file.write_text(json.dumps(users_data, ensure_ascii=False))

    return config_dir


@pytest.fixture
def temp_whitelist_dirs(tmp_path):
    """创建临时白名单目录"""
    dir1 = tmp_path / 'dir1'
    dir1.mkdir()
    dir2 = tmp_path / 'dir2'
    dir2.mkdir()
    return [str(dir1), str(dir2)]
