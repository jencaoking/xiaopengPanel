"""
定时任务管理 API 集成测试

测试范围：
- 列出定时任务
- 校验 Cron 表达式（合法/非法）
- 创建/获取/删除任务
- 启用/禁用任务（toggle）
- 手动触发任务执行
- 获取任务执行历史
"""
import pytest


@pytest.mark.integration
class TestAPICron:
    """定时任务管理 API 端点集成测试"""

    def test_list_cron_tasks(self, admin_client, mock_users):
        """管理员可以列出所有定时任务"""
        response = admin_client.get('/api/cron/tasks')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'tasks' in data

    def test_validate_cron_valid(self, admin_client, mock_users):
        """校验合法的 Cron 表达式"""
        response = admin_client.post('/api/cron/validate', json={
            'cron_expr': '*/5 * * * *'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['valid'] is True

    def test_validate_cron_invalid(self, admin_client, mock_users):
        """校验非法的 Cron 表达式"""
        response = admin_client.post('/api/cron/validate', json={
            'cron_expr': 'not-a-cron'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['valid'] is False

    def test_create_cron_task(self, admin_client, mock_users):
        """创建定时任务"""
        response = admin_client.post('/api/cron/tasks', json={
            'name': 'integration_test_task',
            'command': 'echo hello',
            'cron_expr': '*/5 * * * *',
            'description': '集成测试任务'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'task_id' in data
        # 清理：删除创建的任务
        task_id = data['task_id']
        admin_client.delete(f'/api/cron/tasks/{task_id}')

    def test_get_nonexistent_task_404(self, admin_client, mock_users):
        """获取不存在的任务应返回 404"""
        response = admin_client.get('/api/cron/tasks/nonexistent_task_id')
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'

    def test_delete_task(self, admin_client, mock_users):
        """删除定时任务"""
        # 先创建一个任务
        create_resp = admin_client.post('/api/cron/tasks', json={
            'name': 'delete_test_task',
            'command': 'echo delete',
            'cron_expr': '*/10 * * * *'
        })
        assert create_resp.status_code == 200
        task_id = create_resp.get_json()['task_id']

        # 删除该任务
        response = admin_client.delete(f'/api/cron/tasks/{task_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_toggle_task(self, admin_client, mock_users):
        """启用/禁用定时任务"""
        # 先创建一个任务（默认启用）
        create_resp = admin_client.post('/api/cron/tasks', json={
            'name': 'toggle_test_task',
            'command': 'echo toggle',
            'cron_expr': '*/15 * * * *',
            'enabled': True
        })
        assert create_resp.status_code == 200
        task_id = create_resp.get_json()['task_id']

        try:
            # 切换任务状态（禁用）
            response = admin_client.post(f'/api/cron/tasks/{task_id}/toggle')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
        finally:
            # 清理
            admin_client.delete(f'/api/cron/tasks/{task_id}')

    def test_run_task(self, admin_client, mock_users):
        """手动触发定时任务执行"""
        # 先创建一个任务
        create_resp = admin_client.post('/api/cron/tasks', json={
            'name': 'run_test_task',
            'command': 'echo run',
            'cron_expr': '*/30 * * * *'
        })
        assert create_resp.status_code == 200
        task_id = create_resp.get_json()['task_id']

        try:
            # 手动触发执行
            response = admin_client.post(f'/api/cron/tasks/{task_id}/run')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
        finally:
            # 清理
            admin_client.delete(f'/api/cron/tasks/{task_id}')

    def test_get_task_history(self, admin_client, mock_users):
        """获取任务执行历史"""
        # 先创建一个任务
        create_resp = admin_client.post('/api/cron/tasks', json={
            'name': 'history_test_task',
            'command': 'echo history',
            'cron_expr': '0 * * * *'
        })
        assert create_resp.status_code == 200
        task_id = create_resp.get_json()['task_id']

        try:
            # 获取执行历史
            response = admin_client.get(f'/api/cron/tasks/{task_id}/history')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            assert 'history' in data
        finally:
            # 清理
            admin_client.delete(f'/api/cron/tasks/{task_id}')
