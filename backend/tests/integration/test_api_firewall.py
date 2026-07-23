"""
防火墙管理 API 集成测试

测试范围：
- 获取防火墙状态（mock subprocess）
- 启用防火墙（mock subprocess）
- 添加/删除防火墙规则（mock subprocess）
- 快速放行/封禁端口（mock subprocess）
- 端口参数校验（非法端口/缺失端口返回 400）
"""
import pytest


@pytest.mark.integration
class TestAPIFirewall:
    """防火墙管理 API 端点集成测试"""

    def test_get_firewall_status(self, admin_client, mock_users, mock_subprocess):
        """获取防火墙状态（使用 mock subprocess）"""
        response = admin_client.get('/api/firewall/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_enable_firewall(self, admin_client, mock_users, mock_subprocess):
        """启用防火墙（使用 mock subprocess）"""
        response = admin_client.post('/api/firewall/enable')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_add_firewall_rule(self, admin_client, mock_users, mock_subprocess):
        """添加防火墙规则（使用 mock subprocess）"""
        response = admin_client.post('/api/firewall/rules', json={
            'port': 8080,
            'protocol': 'tcp',
            'action': 'allow'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_delete_firewall_rule(self, admin_client, mock_users, mock_subprocess):
        """删除防火墙规则（使用 mock subprocess）"""
        response = admin_client.delete('/api/firewall/rules', json={
            'port': 8080,
            'protocol': 'tcp'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_quick_allow_port(self, admin_client, mock_users, mock_subprocess):
        """快速放行端口（使用 mock subprocess）"""
        response = admin_client.post('/api/firewall/quick-allow', json={
            'port': 9090,
            'protocol': 'tcp'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_quick_block_port(self, admin_client, mock_users, mock_subprocess):
        """快速封禁端口（使用 mock subprocess）"""
        response = admin_client.post('/api/firewall/quick-block', json={
            'port': 9091,
            'protocol': 'tcp'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_invalid_port_returns_400(self, admin_client, mock_users):
        """非法端口号应返回 400"""
        response = admin_client.post('/api/firewall/quick-allow', json={
            'port': 'not-a-number',
            'protocol': 'tcp'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'

    def test_missing_port_returns_400(self, admin_client, mock_users):
        """缺失端口参数应返回 400"""
        response = admin_client.post('/api/firewall/quick-allow', json={
            'protocol': 'tcp'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
