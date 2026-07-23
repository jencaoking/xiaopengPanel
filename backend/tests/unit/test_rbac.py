"""
RBAC 权限引擎单元测试

测试范围：
- 权限展开与匹配
- 通配符处理
- 操作隐含关系
- 角色管理（创建/更新/删除）
- 内置角色定义
"""
import pytest
import os
import json
from unittest.mock import patch

from modules import rbac
from modules.rbac import (
    RESOURCES,
    ACTIONS,
    _expand_permissions,
    has_permission,
    get_role_permissions,
    get_user_permissions,
    check_user_permission,
    list_roles,
    get_role,
    create_role,
    update_role,
    delete_role,
    get_all_permissions,
    is_valid_role,
    get_valid_role_keys,
    _validate_permissions,
)


# ==================== 权限展开 ====================

class TestPermissionExpansion:
    """权限展开测试"""

    def test_expand_simple_permission(self):
        """展开简单权限"""
        result = _expand_permissions(['file:view'])
        assert ('file', 'view') in result

    def test_expand_wildcard_resource(self):
        """通配符资源"""
        result = _expand_permissions(['*:view'])
        for resource in RESOURCES:
            assert (resource, 'view') in result

    def test_expand_wildcard_action(self):
        """通配符操作"""
        result = _expand_permissions(['file:*'])
        for action in ACTIONS:
            assert ('file', action) in result

    def test_expand_manage_implies_all(self):
        """manage 隐含所有操作"""
        result = _expand_permissions(['file:manage'])
        assert ('file', 'view') in result
        assert ('file', 'create') in result
        assert ('file', 'update') in result
        assert ('file', 'delete') in result
        assert ('file', 'execute') in result
        assert ('file', 'manage') in result

    def test_expand_execute_implies_view(self):
        """execute 隐含 view"""
        result = _expand_permissions(['terminal:execute'])
        assert ('terminal', 'view') in result
        assert ('terminal', 'execute') in result

    def test_expand_create_implies_view(self):
        """create 隐含 view"""
        result = _expand_permissions(['user:create'])
        assert ('user', 'view') in result
        assert ('user', 'create') in result

    def test_expand_empty_list(self):
        """空权限列表"""
        result = _expand_permissions([])
        assert len(result) == 0

    def test_expand_none(self):
        """None 权限"""
        result = _expand_permissions(None)
        assert len(result) == 0

    def test_expand_invalid_format(self):
        """无效格式的权限被忽略"""
        result = _expand_permissions(['invalid', 'no_colon', ''])
        assert len(result) == 0

    def test_expand_unknown_resource(self):
        """未知资源被忽略"""
        result = _expand_permissions(['unknown_resource:view'])
        assert len(result) == 0

    def test_expand_all_manage(self):
        """*:manage 展开为所有资源所有操作"""
        result = _expand_permissions(['*:manage'])
        for resource in RESOURCES:
            for action in ACTIONS:
                assert (resource, action) in result


# ==================== 权限匹配 ====================

class TestPermissionMatching:
    """权限匹配测试"""

    def test_exact_match(self):
        """精确匹配"""
        assert has_permission(['file:view'], 'file:view') is True

    def test_no_match(self):
        """不匹配"""
        assert has_permission(['file:view'], 'file:delete') is False

    def test_wildcard_resource_match(self):
        """通配符资源匹配"""
        assert has_permission(['*:view'], 'file:view') is True
        assert has_permission(['*:view'], 'system:view') is True

    def test_wildcard_action_match(self):
        """通配符操作匹配"""
        assert has_permission(['file:*'], 'file:view') is True
        assert has_permission(['file:*'], 'file:delete') is True

    def test_super_permission_manage(self):
        """超级权限 *:manage"""
        assert has_permission(['*:manage'], 'file:view') is True
        assert has_permission(['*:manage'], 'user:delete') is True
        assert has_permission(['*:manage'], 'system:manage') is True

    def test_super_permission_all(self):
        """超级权限 *:*"""
        assert has_permission(['*:*'], 'anything:anything') is True

    def test_manage_implies_view(self):
        """manage 隐含 view"""
        assert has_permission(['file:manage'], 'file:view') is True

    def test_manage_implies_create_update_delete(self):
        """manage 隐含 create/update/delete"""
        perms = ['file:manage']
        assert has_permission(perms, 'file:create') is True
        assert has_permission(perms, 'file:update') is True
        assert has_permission(perms, 'file:delete') is True

    def test_execute_implies_view(self):
        """execute 隐含 view"""
        assert has_permission(['terminal:execute'], 'terminal:view') is True

    def test_create_implies_view(self):
        """create 隐含 view"""
        assert has_permission(['user:create'], 'user:view') is True

    def test_view_does_not_imply_create(self):
        """view 不隐含 create"""
        assert has_permission(['file:view'], 'file:create') is False

    def test_empty_permissions(self):
        """空权限列表"""
        assert has_permission([], 'file:view') is False

    def test_none_permissions_raises(self):
        """None 权限应抛出 TypeError（已知问题：缺少 None 检查）"""
        with pytest.raises(TypeError):
            has_permission(None, 'file:view')

    def test_invalid_required_permission(self):
        """无效的所需权限格式"""
        assert has_permission(['*:manage'], 'invalid') is False
        assert has_permission(['*:manage'], '') is False
        assert has_permission(['*:manage'], 'no_colon') is False


# ==================== 角色权限查询 ====================

class TestRolePermissions:
    """角色权限查询测试"""

    def test_admin_has_all_permissions(self):
        """管理员拥有所有权限"""
        perms = get_role_permissions('admin')
        assert '*:manage' in perms

    def test_viewer_has_view_only(self):
        """只读用户只有 view 权限"""
        perms = get_role_permissions('viewer')
        assert '*:view' in perms

    def test_operator_has_management(self):
        """运维人员有管理权限"""
        perms = get_role_permissions('operator')
        assert 'process:manage' in perms
        assert 'service:manage' in perms
        assert 'file:manage' in perms

    def test_auditor_has_audit_permissions(self):
        """审计人员只有日志和监控查看权限"""
        perms = get_role_permissions('auditor')
        assert 'log:view' in perms
        assert 'monitor:view' in perms
        assert 'system:view' in perms

    def test_nonexistent_role_returns_empty(self):
        """不存在的角色返回空列表"""
        assert get_role_permissions('nonexistent') == []

    def test_get_user_permissions_equals_role(self):
        """get_user_permissions 等同于 get_role_permissions"""
        assert get_user_permissions('admin') == get_role_permissions('admin')

    def test_check_user_permission_admin(self):
        """管理员通过所有权限检查"""
        assert check_user_permission('admin', 'file:view') is True
        assert check_user_permission('admin', 'user:delete') is True
        assert check_user_permission('admin', 'system:manage') is True

    def test_check_user_permission_viewer(self):
        """只读用户只能查看"""
        assert check_user_permission('viewer', 'file:view') is True
        assert check_user_permission('viewer', 'file:create') is False
        assert check_user_permission('viewer', 'file:delete') is False

    def test_check_user_permission_operator(self):
        """运维人员可以管理但不能查看用户"""
        assert check_user_permission('operator', 'process:manage') is True
        assert check_user_permission('operator', 'file:delete') is True
        assert check_user_permission('operator', 'user:create') is False

    def test_check_user_permission_nonexistent_role(self):
        """不存在的角色无权限"""
        assert check_user_permission('nobody', 'file:view') is False


# ==================== 内置角色 ====================

class TestBuiltinRoles:
    """内置角色定义测试"""

    def test_admin_is_system(self):
        """管理员是系统角色"""
        role = get_role('admin')
        assert role is not None
        assert role['is_system'] is True
        assert role['name'] == '管理员'

    def test_operator_is_system(self):
        """运维人员是系统角色"""
        role = get_role('operator')
        assert role is not None
        assert role['is_system'] is True

    def test_viewer_is_system(self):
        """只读用户是系统角色"""
        role = get_role('viewer')
        assert role is not None
        assert role['is_system'] is True

    def test_auditor_is_system(self):
        """审计人员是系统角色"""
        role = get_role('auditor')
        assert role is not None
        assert role['is_system'] is True

    def test_list_roles_includes_all_builtin(self):
        """列出角色包含所有内置角色"""
        roles = list_roles()
        assert 'admin' in roles
        assert 'operator' in roles
        assert 'viewer' in roles
        assert 'auditor' in roles

    def test_list_roles_exclude_system(self):
        """列出角色可排除系统角色"""
        roles = list_roles(include_system=False)
        assert 'admin' not in roles
        assert 'operator' not in roles

    def test_get_nonexistent_role(self):
        """获取不存在的角色返回 None"""
        assert get_role('nonexistent') is None

    def test_is_valid_role(self):
        """角色标识验证"""
        assert is_valid_role('admin') is True
        assert is_valid_role('operator') is True
        assert is_valid_role('nonexistent') is False

    def test_get_valid_role_keys(self):
        """获取有效角色标识列表"""
        keys = get_valid_role_keys()
        assert 'admin' in keys
        assert 'operator' in keys
        assert 'viewer' in keys
        assert 'auditor' in keys


# ==================== 权限校验 ====================

class TestPermissionValidation:
    """权限格式校验测试"""

    def test_valid_permissions(self):
        """合法权限"""
        is_valid, _ = _validate_permissions(['file:view', 'user:create', '*:manage'])
        assert is_valid is True

    def test_invalid_format(self):
        """无效格式"""
        is_valid, err = _validate_permissions(['invalid'])
        assert is_valid is False
        assert '格式无效' in err

    def test_unknown_resource(self):
        """未知资源"""
        is_valid, err = _validate_permissions(['unknown:view'])
        assert is_valid is False
        assert '未知资源' in err

    def test_unknown_action(self):
        """未知操作"""
        is_valid, err = _validate_permissions(['file:unknown'])
        assert is_valid is False
        assert '未知操作' in err

    def test_wildcard_allowed(self):
        """通配符被允许"""
        is_valid, _ = _validate_permissions(['*:view', 'file:*', '*:*'])
        assert is_valid is True

    def test_non_list_input(self):
        """非列表输入"""
        is_valid, _ = _validate_permissions('file:view')
        assert is_valid is False

    def test_empty_list(self):
        """空列表"""
        is_valid, _ = _validate_permissions([])
        assert is_valid is True


# ==================== 自定义角色管理 ====================

class TestCustomRoleManagement:
    """自定义角色管理测试"""

    def test_create_custom_role(self, tmp_path, monkeypatch):
        """创建自定义角色"""
        # 使用临时文件
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        result, status = create_role(
            role_key='developer',
            name='开发者',
            description='开发人员角色',
            permissions=['file:view', 'editor:view']
        )
        assert status == 201
        assert result['status'] == 'success'
        assert result['role']['key'] == 'developer'
        assert result['role']['name'] == '开发者'

    def test_create_duplicate_role(self, monkeypatch, tmp_path):
        """创建重复角色"""
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        create_role('dev1', 'Dev1', '', ['file:view'])
        result, status = create_role('dev1', 'Dev1', '', ['file:view'])
        assert status == 409
        assert result['status'] == 'error'

    def test_create_role_invalid_key(self, monkeypatch, tmp_path):
        """角色标识包含非法字符"""
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        result, status = create_role('dev-key!', 'Dev', '', ['file:view'])
        assert status == 400
        assert result['status'] == 'error'

    def test_create_role_empty_key(self):
        """角色标识为空"""
        result, status = create_role('', 'Dev', '', ['file:view'])
        assert status == 400

    def test_create_role_invalid_permission(self, monkeypatch, tmp_path):
        """权限格式无效"""
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        result, status = create_role('dev', 'Dev', '', ['invalid_permission'])
        assert status == 400

    def test_update_custom_role(self, monkeypatch, tmp_path):
        """更新自定义角色"""
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        create_role('dev', 'Dev', 'Old', ['file:view'])
        result, status = update_role('dev', name='Developer', description='New')
        assert status == 200
        assert result['role']['name'] == 'Developer'
        assert result['role']['description'] == 'New'

    def test_update_builtin_role_permissions_blocked(self):
        """内置角色不允许修改权限"""
        result, status = update_role('admin', permissions=['file:view'])
        assert status == 403
        assert '内置角色' in result['message']

    def test_update_nonexistent_role(self):
        """更新不存在的角色"""
        result, status = update_role('nobody', name='Nobody')
        assert status == 404

    def test_delete_custom_role(self, monkeypatch, tmp_path):
        """删除自定义角色"""
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        create_role('temp_role', 'Temp', '', ['file:view'])
        result, status = delete_role('temp_role', current_users={})
        assert result['status'] == 'success'

    def test_delete_builtin_role_blocked(self):
        """内置角色不允许删除"""
        result, status = delete_role('admin', current_users={})
        assert status == 403

    def test_delete_role_in_use(self, monkeypatch, tmp_path):
        """角色正在使用时不允许删除"""
        roles_file = tmp_path / 'roles.json'
        monkeypatch.setattr('modules.rbac.RBAC_DATA_FILE', str(roles_file))

        create_role('dev', 'Dev', '', ['file:view'])
        current_users = {'alice': {'role': 'dev'}}
        result, status = delete_role('dev', current_users=current_users)
        assert status == 409
        assert 'alice' in result['message']

    def test_delete_nonexistent_role(self):
        """删除不存在的角色"""
        result, status = delete_role('nobody', current_users={})
        assert status == 404


# ==================== 权限定义查询 ====================

class TestPermissionDefinitions:
    """权限定义查询测试"""

    def test_get_all_permissions(self):
        """获取所有权限定义"""
        result = get_all_permissions()
        assert 'resources' in result
        assert 'actions' in result
        assert 'implications' in result
        assert 'file' in result['resources']
        assert 'view' in result['actions']

    def test_resources_definition(self):
        """资源定义完整"""
        expected_resources = [
            'dashboard', 'system', 'process', 'service', 'file', 'site',
            'database', 'log', 'user', 'role', 'config', 'terminal',
            'editor', 'firewall', 'web_service', 'monitor'
        ]
        for res in expected_resources:
            assert res in RESOURCES

    def test_actions_definition(self):
        """操作定义完整"""
        expected_actions = ['view', 'create', 'update', 'delete', 'execute', 'manage']
        for act in expected_actions:
            assert act in ACTIONS
