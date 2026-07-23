"""
中间件模块单元测试

测试范围：
- IP 白名单装饰器 ip_whitelist_required（启用/禁用、命中/未命中、角色未配置）
- 权限校验装饰器 require_permission（充足/不足/未认证）
- 安全响应头中间件 secure_headers

注意：不使用 conftest 的 `app` fixture（该 fixture 在当前环境因 Python 3.14
的 patch 解析机制差异而无法正常加载 app 模块），改用最小 Flask 应用上下文。
"""
import pytest
from flask import Flask, jsonify, request

from config.config import Config, StaticConfig, config_instance
from modules.middleware import (
    ip_whitelist_required,
    require_permission,
    secure_headers,
)

# 中间件在类级别访问 Config.SECURE_HEADERS，但该属性仅在 config_instance 实例上设置。
# 这里在类级别补齐，使中间件在测试环境中可正常工作（与生产环境行为一致）。
if not hasattr(Config, 'SECURE_HEADERS'):
    Config.SECURE_HEADERS = config_instance.SECURE_HEADERS


@pytest.fixture
def flask_app():
    """最小 Flask 测试应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


# ==================== IP 白名单装饰器 ====================

class TestIpWhitelistRequired:
    """ip_whitelist_required 装饰器测试"""

    @pytest.mark.unit
    def test_whitelist_disabled_allows_all(self, flask_app, monkeypatch):
        """白名单未启用时应放行所有请求"""
        # 直接 patch config_instance（中间件实际读取的对象），避免被残留实例属性遮蔽
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', False)

        with flask_app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.100'}):
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_whitelist_enabled_ip_in_whitelist(self, flask_app, monkeypatch):
        """白名单启用且 IP 在白名单内时应放行"""
        whitelist = {'admin': ['127.0.0.1', '::1']}
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', whitelist)

        with flask_app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_whitelist_enabled_ip_not_in_whitelist(self, flask_app, monkeypatch):
        """白名单启用且 IP 不在白名单内时应返回 403"""
        whitelist = {'admin': ['127.0.0.1', '::1']}
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', whitelist)

        with flask_app.test_request_context('/', environ_base={'REMOTE_ADDR': '10.0.0.99'}):
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'IP address not allowed' in resp[0].get_data()

    @pytest.mark.unit
    def test_whitelist_enabled_role_not_configured(self, flask_app, monkeypatch):
        """白名单启用但角色不在白名单配置中时应返回 403"""
        whitelist = {'operator': ['127.0.0.1'], 'viewer': ['127.0.0.1']}
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', whitelist)

        with flask_app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'not configured' in resp[0].get_data()

    @pytest.mark.unit
    def test_whitelist_enabled_no_user_passes_through(self, flask_app, monkeypatch):
        """白名单启用但用户未认证时应放行（认证由其他中间件处理）"""
        whitelist = {'admin': ['127.0.0.1']}
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', whitelist)

        with flask_app.test_request_context('/', environ_base={'REMOTE_ADDR': '10.0.0.5'}):
            # 不设置 request.user，模拟未认证用户
            if hasattr(request, 'user'):
                del request.user

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_whitelist_ipv6_address(self, flask_app, monkeypatch):
        """白名单应支持 IPv6 地址"""
        whitelist = {'admin': ['::1']}
        monkeypatch.setattr(config_instance, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(config_instance, 'IP_WHITELIST', whitelist)

        with flask_app.test_request_context('/', environ_base={'REMOTE_ADDR': '::1'}):
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200


# ==================== 权限校验装饰器 ====================

class TestRequirePermission:
    """require_permission 装饰器测试"""

    @pytest.mark.unit
    def test_permission_sufficient_allows(self, flask_app):
        """拥有所需权限时应放行（admin 拥有 *:manage 通配权限）"""
        with flask_app.test_request_context('/'):
            request.user = {'username': 'admin', 'role': 'admin'}

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_permission_insufficient_blocks(self, flask_app):
        """权限不足时应返回 403"""
        import json as _json
        with flask_app.test_request_context('/'):
            # viewer 仅有 *:view 权限
            request.user = {'username': 'viewer', 'role': 'viewer'}

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            body = _json.loads(resp[0].get_data(as_text=True))
            assert 'message' in body
            assert '权限不足' in body['message']

    @pytest.mark.unit
    def test_permission_without_auth_returns_401(self, flask_app):
        """未认证（无 request.user）时应返回 401"""
        with flask_app.test_request_context('/'):
            if hasattr(request, 'user'):
                del request.user

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 401
            assert b'Authentication required' in resp[0].get_data()

    @pytest.mark.unit
    def test_permission_missing_role_blocks(self, flask_app):
        """用户数据中缺少 role 字段时应返回 403"""
        with flask_app.test_request_context('/'):
            request.user = {'username': 'unknown'}

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'User role not found' in resp[0].get_data()

    @pytest.mark.unit
    def test_operator_with_matching_permission_allows(self, flask_app):
        """operator 拥有的特定权限应放行"""
        with flask_app.test_request_context('/'):
            request.user = {'username': 'operator', 'role': 'operator'}

            # operator 拥有 process:manage 权限
            @require_permission('process:manage')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_operator_without_permission_blocks(self, flask_app):
        """operator 没有的权限应被拒绝"""
        with flask_app.test_request_context('/'):
            request.user = {'username': 'operator', 'role': 'operator'}

            # operator 不持有 user:create 权限
            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403

    @pytest.mark.unit
    def test_auditor_view_permission_allows(self, flask_app):
        """auditor 拥有的 view 权限应放行"""
        with flask_app.test_request_context('/'):
            request.user = {'username': 'auditor', 'role': 'auditor'}

            @require_permission('log:view')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_permission_response_includes_required_permission(self, flask_app):
        """403 响应应包含 required_permission 字段"""
        with flask_app.test_request_context('/'):
            request.user = {'username': 'viewer', 'role': 'viewer'}

            @require_permission('user:delete')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'required_permission' in resp[0].get_data()
            assert b'user:delete' in resp[0].get_data()


# ==================== 安全响应头 ====================

class TestSecureHeaders:
    """secure_headers 中间件测试"""

    @pytest.mark.unit
    def test_secure_headers_adds_all_configured_headers(self, flask_app):
        """应添加 Config.SECURE_HEADERS 中配置的所有响应头"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)

            for header, value in Config.SECURE_HEADERS.items():
                assert result.headers[header] == value

    @pytest.mark.unit
    def test_secure_headers_returns_same_response(self, flask_app):
        """应返回传入的响应对象"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result is resp

    @pytest.mark.unit
    def test_secure_headers_includes_x_frame_options(self, flask_app):
        """应包含 X-Frame-Options: DENY"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result.headers.get('X-Frame-Options') == 'DENY'

    @pytest.mark.unit
    def test_secure_headers_includes_csp(self, flask_app):
        """应包含 Content-Security-Policy 头"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert 'Content-Security-Policy' in result.headers
            assert "default-src 'self'" in result.headers['Content-Security-Policy']

    @pytest.mark.unit
    def test_secure_headers_includes_nosniff(self, flask_app):
        """应包含 X-Content-Type-Options: nosniff"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result.headers.get('X-Content-Type-Options') == 'nosniff'

    @pytest.mark.unit
    def test_secure_headers_count(self, flask_app):
        """应至少添加 5 个安全响应头"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            added = sum(1 for h in Config.SECURE_HEADERS if h in result.headers)
            assert added >= 5

    @pytest.mark.unit
    def test_secure_headers_includes_referrer_policy(self, flask_app):
        """应包含 Referrer-Policy 头"""
        with flask_app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
