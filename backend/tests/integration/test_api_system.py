"""
系统信息与监控 API 集成测试

测试范围：
- 系统信息（管理员/只读用户/审计人员）
- 实时系统状态
- 实时监控指标（CPU/内存/网络/磁盘/进程）
- 指标导出
- 权限控制（运维人员无法访问系统配置）
"""
import pytest


@pytest.mark.integration
class TestAPISystem:
    """系统信息与监控 API 端点集成测试"""

    def test_get_system_info_admin(self, admin_client, mock_users):
        """管理员可以获取系统信息"""
        response = admin_client.get('/api/system/info')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_viewer_can_access_system_info(self, viewer_client, mock_users):
        """只读用户拥有 system:view 权限（通过 *:view），可以访问系统信息"""
        response = viewer_client.get('/api/system/info')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_get_system_status(self, admin_client, mock_users):
        """获取实时系统状态"""
        response = admin_client.get('/api/system/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_get_realtime_metrics(self, admin_client, mock_users, mock_psutil):
        """获取实时监控指标（使用 mock psutil）"""
        response = admin_client.get('/api/monitor/realtime')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_get_network_traffic(self, admin_client, mock_users, mock_psutil):
        """获取网络流量信息（使用 mock psutil）"""
        response = admin_client.get('/api/monitor/network/traffic')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_get_disk_io(self, admin_client, mock_users, mock_psutil):
        """获取磁盘 IO 信息（使用 mock psutil）"""
        response = admin_client.get('/api/monitor/disk-io')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_get_top_processes(self, admin_client, mock_users, mock_psutil):
        """获取资源占用最高的进程（使用 mock psutil）"""
        response = admin_client.get('/api/monitor/top-processes')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_export_metrics(self, admin_client, mock_users, mock_psutil):
        """导出指标数据"""
        response = admin_client.post('/api/monitor/export', json={
            'metric_types': ['cpu', 'memory'],
            'time_range': '1h',
            'format': 'json'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_auditor_can_access_monitor(self, client, auditor_headers, mock_users, mock_psutil):
        """审计人员拥有 monitor:view 权限，可以访问监控端点"""
        response = client.get('/api/monitor/realtime', headers=auditor_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None

    def test_operator_cannot_access_system_config(self, operator_client, mock_users):
        """运维人员无 config:view 权限，不能访问系统配置（403）"""
        response = operator_client.get('/api/config')
        assert response.status_code == 403
        data = response.get_json()
        assert data['status'] == 'error'
