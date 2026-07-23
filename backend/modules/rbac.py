"""
细粒度基于角色的访问控制（RBAC）引擎

权限模型：
- 权限格式: "资源:操作"，例如 "user:create"、"file:delete"
- 通配符:
  - "*:action" 表示对所有资源拥有该操作权限
  - "resource:*" 表示对该资源拥有全部操作权限
  - "*:*" 或 "*:manage" 表示超级权限
- 操作层级（隐式包含关系）:
  - manage 隐含 view/create/update/delete/execute 全部权限
  - execute 隐含 view
  - create/update/delete 隐含 view

资源定义对应各功能模块；内置角色（admin/operator/viewer/auditor）不可删除，
自定义角色可由管理员创建并分配任意权限集合。
"""
import os
import json
import threading
from modules.log_manager import log_system

# RBAC 数据文件路径
RBAC_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'roles.json')

# 文件锁，保证多线程下读写一致性
_data_lock = threading.RLock()

# -------------------- 资源与操作定义 --------------------

# 所有受控资源（与功能模块对应）
RESOURCES = {
    'dashboard':   '仪表盘',
    'system':      '系统信息',
    'process':     '进程管理',
    'service':     '服务管理',
    'file':        '文件管理',
    'site':        '站点管理',
    'database':    '数据库管理',
    'log':         '日志管理',
    'user':        '用户管理',
    'role':        '角色管理',
    'config':      '系统配置',
    'terminal':    '终端访问',
    'editor':      '代码编辑器',
    'firewall':    '防火墙管理',
    'web_service': 'Web服务管理',
    'monitor':     '系统监控',
    'cron':        '定时任务',
    'ai':          'AI 助手',
}

# 所有受控操作
ACTIONS = {
    'view':    '查看',
    'create':  '创建',
    'update':  '更新',
    'delete':  '删除',
    'execute': '执行',
    'manage':  '管理（全部操作）',
}

# 操作包含关系：manage 包含所有操作；execute/create/update/delete 隐含 view
_ACTION_IMPLICATIONS = {
    'manage':  ['view', 'create', 'update', 'delete', 'execute'],
    'execute': ['view'],
    'create':  ['view'],
    'update':  ['view'],
    'delete':  ['view'],
}

# -------------------- 内置角色定义 --------------------

def _builtin_roles():
    """构造内置角色定义"""
    all_perms = ['*:manage']
    viewer_perms = ['*:view']
    operator_perms = [
        'dashboard:view',
        'system:view',
        'monitor:view',
        'process:manage',
        'service:manage',
        'file:manage',
        'site:manage',
        'database:manage',
        'log:view',
        'web_service:manage',
        'terminal:execute',
        'editor:view',
        'cron:manage',
        'ai:view',
        'ai:execute',
    ]
    auditor_perms = [
        'dashboard:view',
        'system:view',
        'monitor:view',
        'log:view',
    ]
    return {
        'admin': {
            'name': '管理员',
            'description': '系统超级管理员，拥有全部权限',
            'permissions': all_perms,
            'is_system': True,
        },
        'operator': {
            'name': '运维人员',
            'description': '负责日常运维操作，可管理系统资源、服务、站点和文件',
            'permissions': operator_perms,
            'is_system': True,
        },
        'viewer': {
            'name': '只读用户',
            'description': '仅可查看各项系统信息，不可执行修改操作',
            'permissions': viewer_perms,
            'is_system': True,
        },
        'auditor': {
            'name': '审计人员',
            'description': '仅可查看日志与监控数据，用于安全审计',
            'permissions': auditor_perms,
            'is_system': True,
        },
    }


# -------------------- 持久化层 --------------------

def _load_roles():
    """从 JSON 文件加载角色定义，文件不存在时初始化内置角色"""
    with _data_lock:
        try:
            if os.path.exists(RBAC_DATA_FILE):
                with open(RBAC_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 合并内置角色（保证内置角色定义始终为最新，防止被覆盖）
                for role_key, role_def in _builtin_roles().items():
                    data[role_key] = role_def
                return data
        except Exception as e:
            log_system(f'Failed to load RBAC roles: {e}', 'ERROR', 'rbac')

        # 初始化内置角色并保存
        roles = _builtin_roles()
        _save_roles(roles)
        return roles


def _save_roles(roles):
    """保存角色定义到 JSON 文件"""
    try:
        os.makedirs(os.path.dirname(RBAC_DATA_FILE), exist_ok=True)
        with open(RBAC_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(roles, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_system(f'Failed to save RBAC roles: {e}', 'ERROR', 'rbac')
        return False


# 全局角色缓存（启动时加载，写操作时刷新）
_roles_cache = _load_roles()


def _refresh_cache():
    """刷新角色缓存"""
    global _roles_cache
    _roles_cache = _load_roles()


# -------------------- 权限解析与匹配 --------------------

def _expand_permissions(permissions):
    """
    将权限规则展开为具体的 (资源, 操作) 集合。
    处理通配符并应用操作隐含关系。
    返回 set of (resource, action) 元组。
    """
    expanded = set()
    for perm in permissions or []:
        if not perm or ':' not in perm:
            continue
        resource, action = perm.split(':', 1)
        resource = resource.strip()
        action = action.strip()

        # 确定资源集合
        if resource == '*':
            target_resources = list(RESOURCES.keys())
        else:
            target_resources = [resource] if resource in RESOURCES else []

        # 确定操作集合（应用隐含关系）
        if action == '*':
            target_actions = list(ACTIONS.keys())
        else:
            implied = set([action])
            implied.update(_ACTION_IMPLICATIONS.get(action, []))
            target_actions = implied

        for res in target_resources:
            for act in target_actions:
                expanded.add((res, act))
    return expanded


def has_permission(user_permissions, required_permission):
    """
    检查权限集合是否满足所需权限。
    支持通配符匹配。

    :param user_permissions: list[str] 用户拥有的权限规则
    :param required_permission: str 形如 "resource:action" 的所需权限
    :return: bool
    """
    if not required_permission or ':' not in required_permission:
        return False

    # 超级权限快速路径
    if '*:manage' in user_permissions or '*:*' in user_permissions:
        return True

    req_resource, req_action = required_permission.split(':', 1)

    for perm in user_permissions or []:
        if not perm or ':' not in perm:
            continue
        res, act = perm.split(':', 1)

        # 资源匹配：通配符或精确匹配
        if res != '*' and res != req_resource:
            continue

        # 操作匹配：通配符或精确匹配
        if act == '*':
            return True
        if act == req_action:
            return True
        # 操作隐含关系：manage 包含其他操作
        implied = _ACTION_IMPLICATIONS.get(act, [])
        if req_action in implied:
            return True

    return False


def get_role_permissions(role_key):
    """
    获取指定角色的全部权限（已展开为具体规则，不包含隐含项）。
    若角色不存在返回空列表。
    """
    role = _roles_cache.get(role_key)
    if not role:
        return []
    return list(role.get('permissions', []))


def get_user_permissions(role_key):
    """
    获取指定角色用户的完整权限规则列表（原始规则，含通配符）。
    用于嵌入 JWT 或返回给前端。
    """
    return get_role_permissions(role_key)


def check_user_permission(role_key, required_permission):
    """
    检查指定角色的用户是否拥有某项权限。

    :param role_key: 角色标识
    :param required_permission: 所需权限 "resource:action"
    :return: bool
    """
    permissions = get_role_permissions(role_key)
    return has_permission(permissions, required_permission)


# -------------------- 角色管理 API --------------------

def list_roles(include_system=True):
    """
    列出全部角色定义。
    返回结构: { role_key: {name, description, permissions, is_system} }
    """
    result = {}
    for role_key, role_def in _roles_cache.items():
        if not include_system and role_def.get('is_system'):
            continue
        result[role_key] = {
            'key': role_key,
            'name': role_def.get('name', role_key),
            'description': role_def.get('description', ''),
            'permissions': list(role_def.get('permissions', [])),
            'is_system': role_def.get('is_system', False),
        }
    return result


def get_role(role_key):
    """获取单个角色定义"""
    role_def = _roles_cache.get(role_key)
    if not role_def:
        return None
    return {
        'key': role_key,
        'name': role_def.get('name', role_key),
        'description': role_def.get('description', ''),
        'permissions': list(role_def.get('permissions', [])),
        'is_system': role_def.get('is_system', False),
    }


def _validate_permissions(permissions):
    """
    校验权限列表合法性，返回 (is_valid, error_message)
    允许使用通配符，但非通配资源/操作必须存在。
    """
    if not isinstance(permissions, list):
        return False, '权限必须为列表'

    valid_actions = set(ACTIONS.keys()) | {'*'}
    valid_resources = set(RESOURCES.keys()) | {'*'}

    for perm in permissions:
        if not isinstance(perm, str) or ':' not in perm:
            return False, f'权限格式无效: {perm}（应为 "资源:操作"）'
        res, act = perm.split(':', 1)
        res, act = res.strip(), act.strip()
        if res not in valid_resources:
            return False, f'未知资源: {res}'
        if act not in valid_actions:
            return False, f'未知操作: {act}'
    return True, ''


def create_role(role_key, name, description, permissions):
    """
    创建自定义角色。

    :return: (result_dict, status_code)
    """
    if not role_key or not name:
        return {'status': 'error', 'message': '角色标识和名称不能为空'}, 400

    # 角色标识只能包含字母、数字、下划线
    if not role_key.replace('_', '').isalnum():
        return {'status': 'error', 'message': '角色标识只能包含字母、数字和下划线'}, 400

    with _data_lock:
        if role_key in _roles_cache:
            return {'status': 'error', 'message': f'角色 {role_key} 已存在'}, 409

        is_valid, err = _validate_permissions(permissions)
        if not is_valid:
            return {'status': 'error', 'message': err}, 400

        _roles_cache[role_key] = {
            'name': name,
            'description': description or '',
            'permissions': list(permissions),
            'is_system': False,
        }

        if _save_roles(_roles_cache):
            log_system(f'Role created: {role_key} ({name})', 'INFO', 'rbac')
            return {
                'status': 'success',
                'message': f'角色 {name} 创建成功',
                'role': get_role(role_key),
            }, 201
        return {'status': 'error', 'message': '角色保存失败'}, 500


def update_role(role_key, name=None, description=None, permissions=None):
    """
    更新角色定义。内置角色不允许修改权限，但允许更新名称和描述。
    """
    with _data_lock:
        role_def = _roles_cache.get(role_key)
        if not role_def:
            return {'status': 'error', 'message': f'角色 {role_key} 不存在'}, 404

        is_system = role_def.get('is_system', False)

        # 内置角色不允许修改权限
        if permissions is not None and is_system:
            return {'status': 'error', 'message': '内置角色不允许修改权限'}, 403

        if permissions is not None:
            is_valid, err = _validate_permissions(permissions)
            if not is_valid:
                return {'status': 'error', 'message': err}, 400
            role_def['permissions'] = list(permissions)

        if name is not None:
            role_def['name'] = name
        if description is not None:
            role_def['description'] = description

        if _save_roles(_roles_cache):
            log_system(f'Role updated: {role_key}', 'INFO', 'rbac')
            return {
                'status': 'success',
                'message': f'角色 {role_key} 更新成功',
                'role': get_role(role_key),
            }, 200
        return {'status': 'error', 'message': '角色保存失败'}, 500


def delete_role(role_key, current_users):
    """
    删除自定义角色。
    :param current_users: 当前 users.json 中的用户映射，用于检查是否有用户仍使用该角色
    """
    with _data_lock:
        role_def = _roles_cache.get(role_key)
        if not role_def:
            return {'status': 'error', 'message': f'角色 {role_key} 不存在'}, 404

        if role_def.get('is_system'):
            return {'status': 'error', 'message': '内置角色不允许删除'}, 403

        # 检查是否有用户仍使用该角色
        in_use = [u for u, info in current_users.items() if info.get('role') == role_key]
        if in_use:
            return {
                'status': 'error',
                'message': f'角色正在被以下用户使用，无法删除: {", ".join(in_use)}'
            }, 409

        del _roles_cache[role_key]
        if _save_roles(_roles_cache):
            log_system(f'Role deleted: {role_key}', 'INFO', 'rbac')
            return {'status': 'success', 'message': f'角色 {role_key} 已删除'}, 200
        return {'status': 'error', 'message': '角色删除失败'}, 500


def get_all_permissions():
    """
    返回所有可用的资源和操作定义，供前端构建权限选择器。
    """
    return {
        'resources': RESOURCES,
        'actions': ACTIONS,
        'implications': _ACTION_IMPLICATIONS,
    }


def get_valid_role_keys():
    """返回全部有效的角色标识列表（供用户管理校验使用）"""
    return list(_roles_cache.keys())


def is_valid_role(role_key):
    """检查角色标识是否有效"""
    return role_key in _roles_cache
