"""
配置模块单元测试

测试范围：
- Config 属性读取（SECRET_KEY/DEBUG/HOST/PORT/LOG_LEVEL 等）
- Config 属性写入并持久化
- 用户管理操作（增删/改密码/改角色/改状态）
- count_admins 仅统计 active 管理员
- 配置文件缺失时使用默认配置创建
"""
import os
import json
import pytest
from unittest.mock import patch

from config.config import Config, StaticConfig, config_instance

# 在会话级 autouse fixture 修改 Config 类属性前，捕获原始的属性描述符。
# conftest._setup_test_environment 会执行 Config.IP_WHITELIST_ENABLED = False，
# 这会用普通值覆盖 @property 描述符，导致 setter 不再被调用。
# 这里保存原始描述符以便在测试中临时恢复。
_ORIG_IP_WHITELIST_ENABLED = Config.__dict__.get('IP_WHITELIST_ENABLED')
_ORIG_IP_WHITELIST = Config.__dict__.get('IP_WHITELIST')


# ==================== 配置属性读取 ====================

class TestConfigProperties:
    """Config 属性读取测试"""

    @pytest.mark.unit
    def test_secret_key_returns_string(self):
        """SECRET_KEY 应返回非空字符串"""
        value = config_instance.SECRET_KEY
        assert isinstance(value, str)
        assert len(value) > 0

    @pytest.mark.unit
    def test_host_returns_string(self):
        """HOST 应返回字符串"""
        value = config_instance.HOST
        assert isinstance(value, str)
        assert len(value) > 0

    @pytest.mark.unit
    def test_port_returns_int(self):
        """PORT 应返回整数"""
        value = config_instance.PORT
        assert isinstance(value, int)
        assert 1 <= value <= 65535

    @pytest.mark.unit
    def test_debug_returns_bool(self):
        """DEBUG 应返回布尔值"""
        value = config_instance.DEBUG
        assert isinstance(value, bool)

    @pytest.mark.unit
    def test_log_level_returns_string(self):
        """LOG_LEVEL 应返回字符串"""
        value = config_instance.LOG_LEVEL
        assert isinstance(value, str)
        assert value in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NOTSET')

    @pytest.mark.unit
    def test_ip_whitelist_enabled_returns_bool(self):
        """IP_WHITELIST_ENABLED 应返回布尔值"""
        value = config_instance.IP_WHITELIST_ENABLED
        assert isinstance(value, bool)

    @pytest.mark.unit
    def test_ip_whitelist_returns_dict(self):
        """IP_WHITELIST 应返回字典"""
        value = config_instance.IP_WHITELIST
        assert isinstance(value, dict)

    @pytest.mark.unit
    def test_log_dir_returns_absolute_path(self):
        """LOG_DIR 应返回绝对路径字符串"""
        value = config_instance.LOG_DIR
        assert isinstance(value, str)
        assert os.path.isabs(value)

    @pytest.mark.unit
    def test_secure_headers_present(self):
        """SECURE_HEADERS 应包含安全响应头"""
        headers = config_instance.SECURE_HEADERS
        assert 'X-Frame-Options' in headers
        assert 'X-Content-Type-Options' in headers
        assert 'Content-Security-Policy' in headers

    @pytest.mark.unit
    def test_get_config_returns_dict(self):
        """get_config 应返回完整配置字典"""
        cfg = config_instance.get_config()
        assert isinstance(cfg, dict)
        assert 'server' in cfg
        assert 'security' in cfg
        assert 'logging' in cfg


# ==================== 属性写入并持久化 ====================

class TestConfigSetters:
    """Config 属性写入测试（mock 持久化避免污染真实配置文件）"""

    @pytest.mark.unit
    def test_set_secret_key_updates_config(self):
        """设置 SECRET_KEY 应更新内部配置"""
        with patch.object(config_instance, '_save_config') as mock_save:
            config_instance.SECRET_KEY = 'new-test-secret'
            assert config_instance._config['security']['secret_key'] == 'new-test-secret'
            assert mock_save.called

    @pytest.mark.unit
    def test_set_debug_updates_config(self):
        """设置 DEBUG 应更新内部配置"""
        original = config_instance.DEBUG
        try:
            with patch.object(config_instance, '_save_config') as mock_save:
                config_instance.DEBUG = True
                assert config_instance._config['security']['debug'] is True
                assert mock_save.called
        finally:
            config_instance._config['security']['debug'] = original

    @pytest.mark.unit
    def test_set_host_updates_config(self):
        """设置 HOST 应更新内部配置"""
        original = config_instance.HOST
        try:
            with patch.object(config_instance, '_save_config') as mock_save:
                config_instance.HOST = '127.0.0.1'
                assert config_instance._config['server']['host'] == '127.0.0.1'
                assert mock_save.called
        finally:
            config_instance._config['server']['host'] = original

    @pytest.mark.unit
    def test_set_port_updates_config(self):
        """设置 PORT 应更新内部配置"""
        original = config_instance.PORT
        try:
            with patch.object(config_instance, '_save_config') as mock_save:
                config_instance.PORT = 8080
                assert config_instance._config['server']['port'] == 8080
                assert mock_save.called
        finally:
            config_instance._config['server']['port'] = original

    @pytest.mark.unit
    def test_set_log_level_updates_config(self):
        """设置 LOG_LEVEL 应更新内部配置"""
        original = config_instance.LOG_LEVEL
        try:
            with patch.object(config_instance, '_save_config') as mock_save:
                config_instance.LOG_LEVEL = 'DEBUG'
                assert config_instance._config['logging']['level'] == 'DEBUG'
                assert mock_save.called
        finally:
            config_instance._config['logging']['level'] = original

    @pytest.mark.unit
    def test_set_ip_whitelist_enabled_updates_config(self):
        """设置 IP_WHITELIST_ENABLED 应更新内部配置"""
        # conftest 会用类属性覆盖 @property 描述符，这里临时恢复以测试真正的 setter
        shadowed = Config.__dict__.get('IP_WHITELIST_ENABLED')
        original_value = config_instance._config['security']['ip_whitelist_enabled']
        try:
            if _ORIG_IP_WHITELIST_ENABLED is not None:
                Config.IP_WHITELIST_ENABLED = _ORIG_IP_WHITELIST_ENABLED
            with patch.object(config_instance, '_save_config') as mock_save:
                config_instance.IP_WHITELIST_ENABLED = True
                assert config_instance._config['security']['ip_whitelist_enabled'] is True
                assert mock_save.called
        finally:
            config_instance._config['security']['ip_whitelist_enabled'] = original_value
            if not isinstance(shadowed, property):
                Config.IP_WHITELIST_ENABLED = shadowed

    @pytest.mark.unit
    def test_update_config_merges_nested(self):
        """update_config 应递归合并嵌套字典"""
        original_port = config_instance.PORT
        try:
            with patch.object(config_instance, '_save_config'):
                config_instance.update_config({'server': {'port': 9999}})
                assert config_instance.PORT == 9999
                # host 不应被覆盖
                assert 'host' in config_instance._config['server']
        finally:
            config_instance._config['server']['port'] = original_port


# ==================== 用户管理 ====================

class TestUserManagement:
    """用户管理操作测试"""

    @pytest.mark.unit
    def test_add_user_success(self):
        """添加新用户应成功并写入用户字典"""
        users = {'admin': {'password': 'h', 'role': 'admin', 'status': 'active'}}
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = users
            result = config_instance.add_user('newuser', {
                'password': 'hash',
                'role': 'viewer',
            })
            assert result is True
            assert 'newuser' in config_instance.USERS
            assert config_instance.USERS['newuser']['role'] == 'viewer'
            # 默认 status 应为 active
            assert config_instance.USERS['newuser']['status'] == 'active'
            assert mock_save.called

    @pytest.mark.unit
    def test_add_user_duplicate_fails(self):
        """添加已存在的用户应失败"""
        users = {'admin': {'password': 'h', 'role': 'admin'}}
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = users
            result = config_instance.add_user('admin', {
                'password': 'new',
                'role': 'viewer',
            })
            assert result is False
            assert not mock_save.called

    @pytest.mark.unit
    def test_delete_user_success(self):
        """删除用户应成功"""
        users = {
            'admin': {'password': 'h', 'role': 'admin'},
            'viewer1': {'password': 'h', 'role': 'viewer'},
        }
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = users
            result = config_instance.delete_user('viewer1')
            assert result is True
            assert 'viewer1' not in config_instance.USERS
            assert mock_save.called

    @pytest.mark.unit
    def test_delete_nonexistent_user_fails(self):
        """删除不存在的用户应失败"""
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = {'admin': {'password': 'h', 'role': 'admin'}}
            result = config_instance.delete_user('nonexistent')
            assert result is False
            assert not mock_save.called

    @pytest.mark.unit
    def test_update_user_password_success(self):
        """更新用户密码应成功并更新时间戳"""
        users = {'admin': {
            'password': 'old',
            'role': 'admin',
            'updated_at': '2025-01-01T00:00:00',
        }}
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = users
            result = config_instance.update_user_password('admin', 'new-hash')
            assert result is True
            assert config_instance.USERS['admin']['password'] == 'new-hash'
            assert config_instance.USERS['admin']['updated_at'] != '2025-01-01T00:00:00'
            assert mock_save.called

    @pytest.mark.unit
    def test_update_user_password_nonexistent_fails(self):
        """更新不存在用户的密码应失败"""
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = {'admin': {'password': 'h', 'role': 'admin'}}
            result = config_instance.update_user_password('nobody', 'new-hash')
            assert result is False
            assert not mock_save.called

    @pytest.mark.unit
    def test_update_user_role_success(self):
        """更新用户角色应成功"""
        users = {'u1': {'password': 'h', 'role': 'viewer', 'updated_at': 'old'}}
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = users
            result = config_instance.update_user_role('u1', 'operator')
            assert result is True
            assert config_instance.USERS['u1']['role'] == 'operator'
            assert mock_save.called

    @pytest.mark.unit
    def test_update_user_status_success(self):
        """更新用户状态应成功"""
        users = {'u1': {'password': 'h', 'role': 'viewer', 'status': 'active', 'updated_at': 'old'}}
        with patch.object(config_instance, '_save_users') as mock_save:
            config_instance.USERS = users
            result = config_instance.update_user_status('u1', 'disabled')
            assert result is True
            assert config_instance.USERS['u1']['status'] == 'disabled'
            assert mock_save.called


# ==================== count_admins 测试 ====================

class TestCountAdmins:
    """count_admins 方法测试"""

    @pytest.mark.unit
    def test_count_admins_only_active(self):
        """应仅统计 active 状态的管理员"""
        users = {
            'admin1': {'password': 'h', 'role': 'admin', 'status': 'active'},
            'admin2': {'password': 'h', 'role': 'admin', 'status': 'active'},
            'admin3': {'password': 'h', 'role': 'admin', 'status': 'disabled'},
            'viewer1': {'password': 'h', 'role': 'viewer', 'status': 'active'},
            'operator1': {'password': 'h', 'role': 'operator', 'status': 'active'},
        }
        config_instance.USERS = users
        assert config_instance.count_admins() == 2

    @pytest.mark.unit
    def test_count_admins_default_active_when_missing(self):
        """status 缺失时应默认按 active 计数"""
        users = {
            'admin1': {'password': 'h', 'role': 'admin'},  # 无 status
        }
        config_instance.USERS = users
        assert config_instance.count_admins() == 1

    @pytest.mark.unit
    def test_count_admins_zero_when_no_admin(self):
        """没有管理员时应返回 0"""
        users = {
            'viewer1': {'password': 'h', 'role': 'viewer', 'status': 'active'},
        }
        config_instance.USERS = users
        assert config_instance.count_admins() == 0

    @pytest.mark.unit
    def test_count_admins_zero_when_all_disabled(self):
        """所有管理员都禁用时应返回 0"""
        users = {
            'admin1': {'password': 'h', 'role': 'admin', 'status': 'disabled'},
            'admin2': {'password': 'h', 'role': 'admin', 'status': 'disabled'},
        }
        config_instance.USERS = users
        assert config_instance.count_admins() == 0


# ==================== 默认配置创建 ====================

class TestDefaultConfigCreation:
    """配置文件缺失时使用默认配置创建的测试"""

    @pytest.mark.unit
    def test_get_default_config_structure(self):
        """_get_default_config 应返回结构完整的默认配置"""
        cfg = config_instance._get_default_config()
        assert 'server' in cfg
        assert 'security' in cfg
        assert 'logging' in cfg
        assert 'file_manager' in cfg
        assert cfg['server']['port'] == 5000
        assert cfg['server']['host'] == '0.0.0.0'
        assert 'secret_key' in cfg['security']
        assert cfg['security']['ip_whitelist_enabled'] is True

    @pytest.mark.unit
    def test_default_config_has_admin_whitelist(self):
        """默认配置应包含 admin 角色的 IP 白名单"""
        cfg = config_instance._get_default_config()
        assert 'admin' in cfg['security']['ip_whitelist']

    @pytest.mark.unit
    def test_load_config_creates_default_when_missing(self, tmp_path, monkeypatch):
        """配置文件不存在时应创建默认配置文件"""
        nonexistent = tmp_path / 'missing_config.json'
        monkeypatch.setattr('config.config.CONFIG_FILE', str(nonexistent))

        with patch.object(Config, '_save_config') as mock_save, \
             patch.object(Config, '_load_users'), \
             patch.object(Config, '_init_properties'):
            cfg = Config._load_config(Config.__new__(Config))
            assert isinstance(cfg, dict)
            assert cfg['server']['port'] == 5000
            assert mock_save.called

    @pytest.mark.unit
    def test_load_config_creates_default_on_decode_error(self, tmp_path, monkeypatch):
        """配置文件 JSON 格式错误时应使用默认配置"""
        bad_file = tmp_path / 'bad_config.json'
        bad_file.write_text('{invalid json content')
        monkeypatch.setattr('config.config.CONFIG_FILE', str(bad_file))

        with patch.object(Config, '_save_config') as mock_save, \
             patch.object(Config, '_load_users'), \
             patch.object(Config, '_init_properties'):
            cfg = Config._load_config(Config.__new__(Config))
            assert isinstance(cfg, dict)
            assert cfg['server']['port'] == 5000
            assert mock_save.called

    @pytest.mark.unit
    def test_default_config_log_settings(self):
        """默认配置应包含完整的 logging 字段"""
        cfg = config_instance._get_default_config()
        assert cfg['logging']['level'] == 'INFO'
        assert cfg['logging']['dir'] == 'logs'
        assert 'max_bytes' in cfg['logging']
        assert 'backup_count' in cfg['logging']

    @pytest.mark.unit
    def test_default_config_secret_key_is_string(self):
        """默认配置的 secret_key 应是非空字符串"""
        cfg = config_instance._get_default_config()
        assert isinstance(cfg['security']['secret_key'], str)
        assert len(cfg['security']['secret_key']) > 0
