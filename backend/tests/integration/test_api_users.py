"""
用户管理 API 集成测试

测试范围：
- 列出用户（管理员/权限不足）
- 创建用户（成功/重复/权限不足）
- 删除用户（成功/最后一个管理员）
- 更新用户角色与密码
- 修改自身密码
"""
import pytest


@pytest.mark.integration
class TestAPIUsers:
    """用户管理 API 端点集成测试"""

    def test_admin_can_list_users(self, admin_client, mock_users):
        """管理员可以列出所有用户"""
        response = admin_client.get('/api/users')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'users' in data
        usernames = [u['username'] for u in data['users']]
        assert 'admin' in usernames
        assert 'viewer' in usernames

    def test_operator_cannot_list_users(self, operator_client, mock_users):
        """运维人员无 user:view 权限，不能列出用户（403）"""
        response = operator_client.get('/api/users')
        assert response.status_code == 403
        data = response.get_json()
        assert data['status'] == 'error'

    def test_admin_can_create_user(self, admin_client, mock_users):
        """管理员可以创建新用户"""
        response = admin_client.post('/api/users', json={
            'username': 'new_test_user',
            'password': 'NewP@ss123',
            'role': 'viewer'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_admin_can_delete_user(self, admin_client, mock_users):
        """管理员可以删除用户"""
        # 先创建一个用户
        create_resp = admin_client.post('/api/users', json={
            'username': 'delete_me_user',
            'password': 'DelP@ss123',
            'role': 'viewer'
        })
        assert create_resp.status_code == 200

        # 删除该用户
        response = admin_client.delete('/api/users/delete_me_user')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_admin_can_update_user_role(self, admin_client, mock_users):
        """管理员可以更新用户角色"""
        # 先创建一个用户
        admin_client.post('/api/users', json={
            'username': 'role_test_user',
            'password': 'RoleP@ss123',
            'role': 'viewer'
        })

        # 更新角色
        response = admin_client.put('/api/users/role_test_user/role', json={
            'new_role': 'operator'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_admin_can_update_user_password(self, admin_client, mock_users):
        """管理员可以更新用户密码"""
        # 先创建一个用户
        admin_client.post('/api/users', json={
            'username': 'pwd_test_user',
            'password': 'OldP@ss123',
            'role': 'viewer'
        })

        # 更新密码
        response = admin_client.put('/api/users/pwd_test_user/password', json={
            'new_password': 'NewP@ss456'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_user_can_change_own_password(self, admin_client, mock_users):
        """用户可以修改自身密码"""
        response = admin_client.put('/api/users/password', json={
            'old_password': 'Test@123456',
            'new_password': 'ChangedP@ss1',
            'confirm_password': 'ChangedP@ss1'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_cannot_create_duplicate_user(self, admin_client, mock_users):
        """不能创建已存在的用户"""
        response = admin_client.post('/api/users', json={
            'username': 'admin',
            'password': 'DupP@ss123',
            'role': 'viewer'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'already exists' in data['message']

    def test_cannot_delete_last_admin(self, admin_client, mock_users):
        """不能删除最后一个启用的管理员账户"""
        # mock_users 中只有一个 admin，尝试删除应失败
        response = admin_client.delete('/api/users/admin')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'error'

    def test_viewer_cannot_create_user(self, viewer_client, mock_users):
        """只读用户无 user:create 权限，不能创建用户（403）"""
        response = viewer_client.post('/api/users', json={
            'username': 'unauthorized_user',
            'password': 'SomeP@ss123',
            'role': 'viewer'
        })
        assert response.status_code == 403
        data = response.get_json()
        assert data['status'] == 'error'
