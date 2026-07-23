"""
中间件模块单元测试

测试范围：
- IP 白名单装饰器 ip_whitelist_required（启用/禁用、命中/未命中、角色未配置）
- 权限校验装饰器 require_permission（充足/不足/未认证）
- 安全响应头中间件 secure_headers
"""
import pytest
from flask import Flask, jsonify

from config.config import Config, StaticConfig, config_instance
from modules.middleware import (
    ip_whitelist_required,
    require_permission,
    secure_headers,
)


# ==================== IP 白名单装饰器 ====================

class TestIpWhitelistRequired:
    """ip_whitelist_required 装饰器测试"""

    @pytest.mark.unit
    def test_whitelist_disabled_allows_all(self, app, disable_ip_whitelist):
        """白名单未启用时应放行所有请求"""
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '192.168.1.100'}):
            from flask import request
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_whitelist_enabled_ip_in_whitelist(self, app, enable_ip_whitelist):
        """白名单启用且 IP 在白名单内时应放行"""
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
            from flask import request
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_whitelist_enabled_ip_not_in_whitelist(self, app, enable_ip_whitelist):
        """白名单启用且 IP 不在白名单内时应返回 403"""
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '10.0.0.99'}):
            from flask import request
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'IP address not allowed' in resp[0].response[0].data

    @pytest.mark.unit
    def test_whitelist_enabled_role_not_configured(self, app, enable_ip_whitelist, monkeypatch):
        """白名单启用但角色不在白名单配置中时应返回 403"""
        # 构造一个不包含 admin 角色的白名单
        whitelist_without_admin = {
            'operator': ['127.0.0.1'],
            'viewer': ['127.0.0.1'],
        }
        monkeypatch.setattr(Config, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(Config, 'IP_WHITELIST', whitelist_without_admin)
        monkeypatch.setattr(StaticConfig, 'IP_WHITELIST_ENABLED', True)
        monkeypatch.setattr(StaticConfig, 'IP_WHITELIST', whitelist_without_admin)

        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
            from flask import request
            request.user = {'username': 'admin', 'role': 'admin'}

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'not configured for this role' in resp[0].response[0].data

    @pytest.mark.unit
    def test_whitelist_enabled_no_user_passes_through(self, app, enable_ip_whitelist):
        """白名单启用但用户未认证时应放行（认证由其他中间件处理）"""
        with app.test_request_context('/', environ_base={'REMOTE_ADDR': '10.0.0.5'}):
            from flask import request
            # 不设置 request.user，模拟未认证用户
            if hasattr(request, 'user'):
                del request.user

            @ip_whitelist_required
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200


# ==================== 权限校验装饰器 ====================

class TestRequirePermission:
    """require_permission 装饰器测试"""

    @pytest.mark.unit
    def test_permission_sufficient_allows(self, app):
        """拥有所需权限时应放行（admin 拥有 *:manage 通配权限）"""
        with app.test_request_context('/'):
            from flask import request
            request.user = {'username': 'admin', 'role': 'admin'}

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_permission_insufficient_blocks(self, app):
        """权限不足时应返回 403"""
        with app.test_request_context('/'):
            from flask import request
            # viewer 仅有 *:view 权限
            request.user = {'username': 'viewer', 'role': 'viewer'}

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'\xe6\x9d\x83\xe9\x99\x90\xe4\xb8\x8d\xe8\xb6\xb3' in resp[0].response[0].data  # "权限不足"

    @pytest.mark.unit
    def test_permission_without_auth_returns_401(self, app):
        """未认证（无 request.user）时应返回 401"""
        with app.test_request_context('/'):
            from flask import request
            if hasattr(request, 'user'):
                del request.user

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 401
            assert b'Authentication required' in resp[0].response[0].data

    @pytest.mark.unit
    def test_permission_missing_role_blocks(self, app):
        """用户数据中缺少 role 字段时应返回 403"""
        with app.test_request_context('/'):
            from flask import request
            request.user = {'username': 'unknown'}

            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403
            assert b'User role not found' in resp[0].response[0].data

    @pytest.mark.unit
    def test_operator_with_matching_permission_allows(self, app):
        """operator 拥有的特定权限应放行"""
        with app.test_request_context('/'):
            from flask import request
            request.user = {'username': 'operator', 'role': 'operator'}

            # operator 拥有 process:manage 权限
            @require_permission('process:manage')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 200

    @pytest.mark.unit
    def test_operator_without_permission_blocks(self, app):
        """operator 没有的权限应被拒绝"""
        with app.test_request_context('/'):
            from flask import request
            request.user = {'username': 'operator', 'role': 'operator'}

            # operator 不持有 user:create 权限
            @require_permission('user:create')
            def view():
                return jsonify({'status': 'ok'}), 200

            resp = view()
            assert resp[1] == 403


# ==================== 安全响应头 ====================

class TestSecureHeaders:
    """secure_headers 中间件测试"""

    @pytest.mark.unit
    def test_secure_headers_adds_all_configured_headers(self, app):
        """应添加 Config.SECURE_HEADERS 中配置的所有响应头"""
        with app.app_context():
            resp = jsonify({'status': 'ok'})
            # jsonify 会创建响应对象
            response = resp

            result = secure_headers(response)

            for header, value in Config.SECURE_HEADERS.items():
                assert result.headers[header] == value

    @pytest.mark.unit
    def test_secure_headers_returns_same_response(self, app):
        """应返回传入的响应对象"""
        with app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result is resp

    @pytest.mark.unit
    def test_secure_headers_includes_x_frame_options(self, app):
        """应包含 X-Frame-Options: DENY"""
        with app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result.headers.get('X-Frame-Options') == 'DENY'

    @pytest.mark.unit
    def test_secure_headers_includes_csp(self, app):
        """应包含 Content-Security-Policy 头"""
        with app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert 'Content-Security-Policy' in result.headers
            assert "default-src 'self'" in result.headers['Content-Security-Policy']

    @pytest.mark.unit
    def test_secure_headers_includes_nosniff(self, app):
        """应包含 X-Content-Type-Options: nosniff"""
        with app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            assert result.headers.get('X-Content-Type-Options') == 'nosniff'

    @pytest.mark.unit
    def test_secure_headers_count(self, app):
        """应至少添加 5 个安全响应头"""
        with app.app_context():
            resp = jsonify({'status': 'ok'})
            result = secure_headers(resp)
            added = sum(1 for h in Config.SECURE_HEADERS if h in result.headers)
            assert added >= 5
