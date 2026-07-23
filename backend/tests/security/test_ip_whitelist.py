"""
IP 白名单安全测试

测试范围：
- IP 白名单启用/禁用
- 白名单内 IP 允许访问
- 白名单外 IP 被拒绝
- 不同角色的白名单配置
"""
import pytest
from config.config import Config, config_instance


@pytest.mark.security
class TestIPWhitelist:
    """IP 白名单安全测试"""

    def test_whitelist_disabled_allows_all(self, client, mock_users, disable_ip_whitelist, admin_token):
        """白名单禁用时允许所有 IP"""
        resp = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                         environ_base={'REMOTE_ADDR': '192.168.1.100'})
        assert resp.status_code == 200

    def test_whitelist_enabled_allows_localhost(self, client, mock_users, enable_ip_whitelist, admin_token):
        """白名单启用时允许 localhost"""
        resp = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                         environ_base={'REMOTE_ADDR': '127.0.0.1'})
        assert resp.status_code == 200

    def test_whitelist_enabled_blocks_unknown_ip(self, client, mock_users, enable_ip_whitelist, admin_token):
        """白名单启用时拒绝未知 IP"""
        resp = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                         environ_base={'REMOTE_ADDR': '192.168.1.100'})
        assert resp.status_code == 403
        data = resp.get_json()
        assert 'not allowed' in data['message'].lower() or 'IP' in data.get('message', '')

    def test_whitelist_ipv6_localhost(self, client, mock_users, enable_ip_whitelist, admin_token):
        """白名单支持 IPv6 localhost"""
        resp = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                         environ_base={'REMOTE_ADDR': '::1'})
        assert resp.status_code == 200

    def test_whitelist_per_role_configuration(self, client, mock_users, monkeypatch):
        """不同角色有不同的白名单配置"""
        # 设置 admin 只允许 10.0.0.1
        test_whitelist = {
            'admin': ['10.0.0.1'],
            'viewer': ['127.0.0.1'],
        }
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', test_whitelist)
        monkeypatch.setattr(Config, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(Config, 'IP_WHITELIST', test_whitelist)

        # admin 从 10.0.0.1 访问
        from modules.auth import get_jwt_secret
        import jwt, time
        from modules import rbac
        admin_token = jwt.encode(
            {'username': 'admin', 'role': 'admin', 'permissions': rbac.get_user_permissions('admin'),
             'exp': time.time() + 3600, 'iat': time.time()},
            config_instance.SECRET_KEY, algorithm='HS256'
        )
        resp = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                         environ_base={'REMOTE_ADDR': '10.0.0.1'})
        assert resp.status_code == 200

        # admin 从 127.0.0.1 访问（不在 admin 白名单中）
        resp = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                         environ_base={'REMOTE_ADDR': '127.0.0.1'})
        assert resp.status_code == 403

    def test_whitelist_blocks_after_enable(self, client, mock_users, admin_token, monkeypatch):
        """启用白名单后立即生效"""
        # 通过 setter 修改实例配置（不触碰 Config 类属性，保留 @property 描述符）
        # 使用 monkeypatch 确保自动恢复
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', False)

        resp1 = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                           environ_base={'REMOTE_ADDR': '192.168.1.1'})
        assert resp1.status_code == 200

        # 启用白名单
        test_whitelist = {'admin': ['127.0.0.1']}
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', test_whitelist)

        resp2 = client.get('/api/system/info', headers={'Authorization': f'Bearer {admin_token}'},
                           environ_base={'REMOTE_ADDR': '192.168.1.1'})
        assert resp2.status_code == 403


@pytest.mark.security
class TestSecureHeaders:
    """安全响应头测试"""

    def test_response_has_security_headers(self, client, mock_users):
        """响应包含安全响应头"""
        resp = client.get('/api/health')
        headers = dict(resp.headers)

        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'

        assert 'X-Frame-Options' in headers
        assert headers['X-Frame-Options'] == 'DENY'

        assert 'X-XSS-Protection' in headers

    def test_response_has_csp_header(self, client, mock_users):
        """响应包含 CSP 头"""
        resp = client.get('/api/health')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "default-src 'self'" in csp

    def test_response_has_referrer_policy(self, client, mock_users):
        """响应包含 Referrer-Policy 头"""
        resp = client.get('/api/health')
        referrer_policy = resp.headers.get('Referrer-Policy', '')
        assert referrer_policy == 'strict-origin-when-cross-origin'

    def test_cors_configured(self, client, mock_users):
        """CORS 正确配置"""
        # OPTIONS 请求测试 CORS
        resp = client.options('/api/health', headers={
            'Origin': 'http://localhost:8000',
            'Access-Control-Request-Method': 'GET'
        })
        # Flask-CORS 应处理预检请求
        assert resp.status_code in (200, 204)
