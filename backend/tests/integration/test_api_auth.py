"""
认证 API 集成测试

测试范围：
- 健康检查端点
- 登录（成功/失败/不存在用户）
- 令牌保护端点（无令牌/有效令牌/过期令牌）
- 刷新令牌（有效/无效）
- 登录接口速率限制
"""
import pytest


@pytest.mark.integration
class TestAPIAuth:
    """认证 API 端点集成测试"""

    def test_health_check_ok(self, client):
        """健康检查端点返回 ok 状态"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'message' in data

    def test_login_valid_credentials(self, client, mock_users):
        """使用有效凭证登录应返回令牌"""
        response = client.post('/api/login', json={
            'username': 'admin',
            'password': 'Test@123456'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'token' in data
        assert 'refresh_token' in data
        assert data['user']['username'] == 'admin'
        assert data['user']['role'] == 'admin'

    def test_login_wrong_password(self, client, mock_users):
        """错误密码登录应返回 401"""
        response = client.post('/api/login', json={
            'username': 'admin',
            'password': 'WrongPassword123!'
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'

    def test_login_nonexistent_user(self, client, mock_users):
        """不存在的用户登录应返回 401"""
        response = client.post('/api/login', json={
            'username': 'nonexistent_user_xyz',
            'password': 'Test@123456'
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'

    def test_protected_endpoint_without_token(self, client, mock_users):
        """无令牌访问受保护端点应返回 401"""
        response = client.get('/api/users')
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'

    def test_protected_endpoint_with_valid_token(self, client, mock_users, admin_headers):
        """使用有效令牌访问受保护端点应成功"""
        response = client.get('/api/users', headers=admin_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_protected_endpoint_with_expired_token(self, client, mock_users, expired_token):
        """过期令牌访问受保护端点应返回 401"""
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = client.get('/api/users', headers=headers)
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'

    def test_refresh_token_valid(self, client, mock_users):
        """有效刷新令牌应获取新的访问令牌"""
        # 先登录获取刷新令牌
        login_resp = client.post('/api/login', json={
            'username': 'admin',
            'password': 'Test@123456'
        })
        assert login_resp.status_code == 200
        refresh_tok = login_resp.get_json()['refresh_token']

        # 使用刷新令牌获取新令牌
        response = client.post('/api/refresh-token', json={
            'refresh_token': refresh_tok
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'token' in data
        assert data['token'] != login_resp.get_json()['token']

    def test_refresh_token_invalid(self, client, mock_users):
        """无效刷新令牌应返回 401"""
        response = client.post('/api/refresh-token', json={
            'refresh_token': 'this-is-not-a-valid-jwt-token'
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'

    def test_login_rate_limiting(self, client, mock_users):
        """登录接口速率限制：每分钟超过 5 次请求返回 429"""
        from app import login_limiter
        # 清除速率限制器状态，确保测试隔离
        login_limiter.requests.clear()
        try:
            # 发送 5 次请求（应全部通过速率限制）
            for i in range(5):
                resp = client.post('/api/login', json={
                    'username': f'rate_test_user_{i}',
                    'password': 'Test@123456'
                })
                # 这些请求可能返回 401（用户不存在），但不应被速率限制
                assert resp.status_code in (401, 200)

            # 第 6 次请求应被速率限制
            response = client.post('/api/login', json={
                'username': 'rate_test_user_6',
                'password': 'Test@123456'
            })
            assert response.status_code == 429
            data = response.get_json()
            assert data['status'] == 'error'
        finally:
            # 清理速率限制器状态，避免影响后续测试
            login_limiter.requests.clear()
