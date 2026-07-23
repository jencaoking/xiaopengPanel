import os
from flask import Blueprint, jsonify, request, send_file
from modules.system_info import get_system_info
from modules.process_manager import get_processes, manage_process, get_process_detail, manage_processes
from modules.service_manager import get_services, manage_service, get_service_status, get_service_logs, get_service_unit_file, get_service_dependencies
from modules.log_manager import get_logs, read_log_file, search_logs, log_operation
from modules.system_config import get_system_config, update_system_config
from modules.auth import login, authenticate, refresh_token, verify_2fa_login
from modules.middleware import ip_whitelist_required, require_permission
from modules import rbac
from modules.file_manager import (
    get_whitelist_dirs, list_directory, create_file, create_directory, delete_file,
    batch_delete, read_file, write_file, get_file_permissions, init_upload,
    upload_chunk, get_upload_status, complete_upload, cancel_upload, download_file,
    get_file_versions, restore_file_version, get_file_version_diff,
    rename_file, move_file, copy_file, get_directory_size, get_file_hash,
    search_files, create_archive, extract_archive
)
from modules.site_manager import SiteManager
from modules.db_manager import db_manager
from config.config import config_instance

# 初始化站点管理器
site_manager = SiteManager(config_instance)

# 创建API蓝图
api = Blueprint('api', __name__)

# 认证路由
@api.route('/login', methods=['POST'])
def login_route():
    # 应用速率限制
    from app import login_limiter
    client_ip = request.remote_addr or 'unknown'
    if not login_limiter.is_allowed(client_ip):
        return jsonify({
            'status': 'error',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429
    return login(request.json)

# 刷新令牌路由
@api.route('/refresh-token', methods=['POST'])
def refresh_token_route():
    return refresh_token(request.json)

# 2FA登录验证路由
@api.route('/login/2fa', methods=['POST'])
def verify_2fa_login_route():
    """2FA登录验证"""
    return verify_2fa_login(request.json)

# 系统信息路由
@api.route('/system/info', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('system:view')
def system_info_route():
    return jsonify(get_system_info())

# 实时系统状态路由（适合频繁调用）
@api.route('/system/status', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('system:view')
def system_status_route():
    from modules.system_info import get_real_time_status
    return jsonify(get_real_time_status())

# 进程管理路由
@api.route('/processes', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('process:view')
def get_processes_route():
    sort_by = request.args.get('sort_by')
    sort_order = request.args.get('sort_order', 'asc')
    search_term = request.args.get('search')
    return jsonify(get_processes(sort_by=sort_by, sort_order=sort_order, search_term=search_term))

@api.route('/processes/<int:pid>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('process:view')
def get_process_detail_route(pid):
    detail = get_process_detail(pid)
    if detail is None:
        return jsonify({'status': 'error', 'message': f'Process {pid} not found'}), 404
    return jsonify(detail)

@api.route('/processes/<int:pid>/<action>', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('process:manage')
def manage_process_route(pid, action):
    return jsonify(manage_process(pid, action))

@api.route('/processes/batch/<action>', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('process:manage')
def batch_manage_processes_route(action):
    data = request.json
    pids = data.get('pids', [])
    if not pids:
        return jsonify({'status': 'error', 'message': 'No process IDs provided'}), 400
    return jsonify(manage_processes(pids, action))

# 服务管理路由
@api.route('/services', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('service:view')
def get_services_route():
    # Get query parameters for filtering and sorting
    filter_status = request.args.get('filter')
    sort_by = request.args.get('sort')
    return jsonify(get_services(filter_status=filter_status, sort_by=sort_by))

@api.route('/services/<service_name>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('service:view')
def get_service_status_route(service_name):
    return jsonify(get_service_status(service_name))

@api.route('/services/<service_name>/<action>', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('service:manage')
def manage_service_route(service_name, action):
    return jsonify(manage_service(service_name, action))

@api.route('/services/<service_name>/logs', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('service:view')
def get_service_logs_route(service_name):
    # Get query parameters for log filtering
    time_range = request.args.get('time_range', 'today')
    keyword = request.args.get('keyword')
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid limit or offset parameter'}), 400
    verbosity = request.args.get('verbosity', 'info')
    return jsonify(get_service_logs(
        service_name=service_name,
        time_range=time_range,
        keyword=keyword,
        limit=limit,
        offset=offset,
        verbosity=verbosity
    ))

@api.route('/services/<service_name>/unit', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('service:view')
def get_service_unit_route(service_name):
    return jsonify(get_service_unit_file(service_name))

@api.route('/services/<service_name>/dependencies', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('service:view')
def get_service_dependencies_route(service_name):
    reverse = request.args.get('reverse', 'false').lower() == 'true'
    return jsonify(get_service_dependencies(service_name, reverse=reverse))

# 日志管理路由
@api.route('/logs', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('log:view')
def get_logs_route():
    return jsonify(get_logs())

@api.route('/logs/read', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('log:view')
def read_logs_route():
    return jsonify(read_log_file(request.json.get('file_path'), request.json.get('lines', 100), request.json.get('offset', 0)))

@api.route('/logs/search', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('log:view')
def search_logs_route():
    return jsonify(search_logs(request.json))

# 增强的日志读取路由（支持筛选）
@api.route('/logs/read/filtered', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('log:view')
def read_logs_filtered_route():
    from modules.log_manager import read_logs_with_filter
    data = request.json
    return jsonify(read_logs_with_filter(
        file_path=data.get('file_path'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        log_levels=data.get('log_levels'),
        keyword=data.get('keyword'),
        case_sensitive=data.get('case_sensitive', False),
        limit=data.get('limit', 100),
        offset=data.get('offset', 0)
    ))

# 日志导出路由
@api.route('/logs/export', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('log:view')
def export_logs_route():
    from modules.log_manager import export_logs
    data = request.json
    return jsonify(export_logs(
        file_path=data.get('file_path'),
        export_format=data.get('export_format', 'json'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        log_levels=data.get('log_levels'),
        keyword=data.get('keyword'),
        case_sensitive=data.get('case_sensitive', False),
        limit=data.get('limit', 10000)  # 导出时默认返回更多行
    ))

# 下载导出的日志文件
@api.route('/logs/download/<filename>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('log:view')
def download_log_route(filename):
    from flask import send_file
    from modules.log_manager import PANEL_LOG_DIR
    import os
    
    file_path = os.path.join(PANEL_LOG_DIR, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

# 系统配置路由
@api.route('/config', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('config:view')
def get_config_route():
    return jsonify(get_system_config())

@api.route('/config', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('config:update')
def update_config_route():
    return jsonify(update_system_config(request.json))

# 用户管理路由
@api.route('/users', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('user:view')
def get_users_route():
    from modules.user_manager import get_all_users
    users_dict = get_all_users()
    # 转换为前端期望的数组格式，包含用户名
    users_list = [
        {
            'username': uname,
            'role': info.get('role', 'viewer'),
            'status': info.get('status', 'active')
        }
        for uname, info in users_dict.items()
    ]
    return jsonify({'status': 'success', 'users': users_list})

@api.route('/users', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('user:create')
def add_user_route():
    from modules.user_manager import add_user
    data = request.json
    return jsonify(add_user(data.get('username'), data.get('password'), data.get('role', 'user')))

@api.route('/users/<username>/password', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def update_user_password_route(username):
    from modules.user_manager import update_user_password
    data = request.json
    return jsonify(update_user_password(username, data.get('new_password')))

@api.route('/users/<username>/role', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def update_user_role_route(username):
    from modules.user_manager import update_user_role
    data = request.json
    return jsonify(update_user_role(username, data.get('new_role')))

@api.route('/users/<username>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('user:delete')
def delete_user_route(username):
    from modules.user_manager import delete_user
    result = delete_user(username)
    # 兼容 delete_user 返回 (dict, status_code) 元组的情况
    if isinstance(result, tuple):
        result, status_code = result
        return jsonify(result), status_code
    return jsonify(result)

@api.route('/users/<username>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('user:view')
def get_user_route(username):
    from modules.user_manager import get_user
    result = get_user(username)
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

@api.route('/users/<username>/status', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def update_user_status_route(username):
    from modules.user_manager import update_user_status
    data = request.json or {}
    result = update_user_status(username, data.get('status'))
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 修改密码路由
@api.route('/users/password', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def change_password_route():
    from modules.auth import change_password
    data = request.json
    username = request.user['username']  # 从JWT令牌中获取当前用户名
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    # 验证密码确认
    if new_password != confirm_password:
        return jsonify({'status': 'error', 'message': '新密码与确认密码不一致'}), 400
    
    return change_password(username, old_password, new_password)


# -------------------- 文件管理API --------------------

# 获取白名单目录列表
@api.route('/file-manager/whitelist-dirs', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def get_whitelist_dirs_route():
    """获取白名单目录列表"""
    return jsonify({'status': 'success', 'dirs': get_whitelist_dirs()})

# 浏览目录内容
@api.route('/file-manager/directory', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def list_directory_route():
    """浏览目录内容"""
    path = request.args.get('path')
    if not path:
        return jsonify({'status': 'error', 'message': '缺少路径参数'}), 400
    
    result = list_directory(path)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 创建文件
@api.route('/file-manager/file', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def create_file_route():
    """创建文件"""
    data = request.json
    file_path = data.get('file_path')
    content = data.get('content', '')
    
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    username = request.user['username']
    result = create_file(file_path, content, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 删除文件
@api.route('/file-manager/file', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('file:delete')
def delete_file_route():
    """删除文件"""
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    username = request.user['username']
    result = delete_file(file_path, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 读取文件内容
@api.route('/file-manager/file/read', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def read_file_route():
    """读取文件内容"""
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400

    username = request.user['username']
    result = read_file(file_path, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 写入文件内容（在线编辑）
@api.route('/file-manager/file/write', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('file:update')
def write_file_route():
    """写入文件内容"""
    data = request.json
    file_path = data.get('file_path')
    content = data.get('content')
    
    if not file_path or content is None:
        return jsonify({'status': 'error', 'message': '缺少文件路径或内容参数'}), 400
    
    username = request.user['username']
    result = write_file(file_path, content, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 获取文件权限信息
@api.route('/file-manager/file/permissions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def get_file_permissions_route():
    """获取文件权限信息"""
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    result = get_file_permissions(file_path)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 初始化文件上传
@api.route('/file-manager/upload/init', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def init_upload_route():
    """初始化文件上传"""
    data = request.json
    username = request.user['username']
    
    result = init_upload(data, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 上传文件块
@api.route('/file-manager/upload/chunk', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def upload_chunk_route():
    """上传文件块"""
    upload_id = request.form.get('upload_id')
    chunk_index = int(request.form.get('chunk_index', 0))
    chunk_data = request.files['chunk'].read()
    username = request.user['username']
    
    if not upload_id:
        return jsonify({'status': 'error', 'message': '缺少上传ID参数'}), 400
    
    result = upload_chunk(upload_id, chunk_index, chunk_data, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 完成文件上传
@api.route('/file-manager/upload/complete', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def complete_upload_route():
    """完成文件上传"""
    data = request.json
    upload_id = data.get('upload_id')
    username = request.user['username']
    
    if not upload_id:
        return jsonify({'status': 'error', 'message': '缺少上传ID参数'}), 400
    
    result = complete_upload(upload_id, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 取消文件上传
@api.route('/file-manager/upload/cancel', methods=['POST'])
@authenticate
@ip_whitelist_required
def cancel_upload_route():
    """取消文件上传"""
    data = request.json
    upload_id = data.get('upload_id')
    
    if not upload_id:
        return jsonify({'status': 'error', 'message': '缺少上传ID参数'}), 400
    
    result = cancel_upload(upload_id)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 下载文件
@api.route('/file-manager/download', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def download_file_route():
    """下载文件"""
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    result = download_file(file_path)
    if result['status'] == 'error':
        return jsonify(result), 400
    
    return send_file(result['file_path'], as_attachment=True, download_name=result['filename'])

# 获取文件版本列表
@api.route('/file-manager/file/versions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def get_file_versions_route():
    """获取文件版本列表"""
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    versions = get_file_versions(file_path)
    return jsonify({'status': 'success', 'versions': versions})

# 恢复文件版本
@api.route('/file-manager/file/restore-version', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:update')
def restore_file_version_route():
    """恢复文件到指定版本"""
    data = request.json
    file_path = data.get('file_path')
    version_num = data.get('version')
    
    if not file_path or not version_num:
        return jsonify({'status': 'error', 'message': '缺少文件路径或版本号参数'}), 400
    
    username = request.user['username']
    result = restore_file_version(file_path, version_num, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 版本差异对比
@api.route('/file-manager/file/version-diff', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def get_file_version_diff_route():
    """对比当前文件与指定版本的内容差异"""
    file_path = request.args.get('path')
    version_num = request.args.get('version')
    if not file_path or not version_num:
        return jsonify({'status': 'error', 'message': '缺少文件路径或版本号参数'}), 400

    username = request.user['username']
    result = get_file_version_diff(file_path, int(version_num), username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 创建目录
@api.route('/file-manager/directory', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def create_directory_route():
    """创建目录"""
    data = request.json
    dir_path = data.get('file_path')
    if not dir_path:
        return jsonify({'status': 'error', 'message': '缺少目录路径参数'}), 400

    username = request.user['username']
    result = create_directory(dir_path, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 重命名文件/目录
@api.route('/file-manager/rename', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:update')
def rename_file_route():
    """重命名文件/目录"""
    data = request.json
    file_path = data.get('file_path')
    new_name = data.get('new_name')
    if not file_path or not new_name:
        return jsonify({'status': 'error', 'message': '缺少文件路径或新名称参数'}), 400

    username = request.user['username']
    result = rename_file(file_path, new_name, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 移动文件/目录
@api.route('/file-manager/move', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:update')
def move_file_route():
    """移动文件/目录"""
    data = request.json
    src_path = data.get('src_path')
    dst_dir = data.get('dst_dir')
    if not src_path or not dst_dir:
        return jsonify({'status': 'error', 'message': '缺少源路径或目标目录参数'}), 400

    username = request.user['username']
    result = move_file(src_path, dst_dir, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 复制文件/目录
@api.route('/file-manager/copy', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def copy_file_route():
    """复制文件/目录"""
    data = request.json
    src_path = data.get('src_path')
    dst_dir = data.get('dst_dir')
    if not src_path or not dst_dir:
        return jsonify({'status': 'error', 'message': '缺少源路径或目标目录参数'}), 400

    username = request.user['username']
    result = copy_file(src_path, dst_dir, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 批量删除
@api.route('/file-manager/batch-delete', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:delete')
def batch_delete_route():
    """批量删除文件/目录"""
    data = request.json
    paths = data.get('paths')
    if not isinstance(paths, list) or not paths:
        return jsonify({'status': 'error', 'message': '缺少文件路径列表参数'}), 400

    username = request.user['username']
    result = batch_delete(paths, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 递归获取目录大小
@api.route('/file-manager/directory-size', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def get_directory_size_route():
    """递归计算目录大小"""
    path = request.args.get('path')
    if not path:
        return jsonify({'status': 'error', 'message': '缺少路径参数'}), 400

    result = get_directory_size(path)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 文件校验和
@api.route('/file-manager/file/hash', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def get_file_hash_route():
    """计算文件校验和"""
    file_path = request.args.get('path')
    algorithm = request.args.get('algorithm', 'sha256')
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400

    result = get_file_hash(file_path, algorithm)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 搜索文件
@api.route('/file-manager/search', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:view')
def search_files_route():
    """搜索文件/目录"""
    path = request.args.get('path')
    query = request.args.get('query')
    if not path or not query:
        return jsonify({'status': 'error', 'message': '缺少路径或搜索关键字参数'}), 400

    result = search_files(path, query)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 创建压缩包
@api.route('/file-manager/archive/create', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def create_archive_route():
    """创建压缩包"""
    data = request.json
    src_paths = data.get('src_paths')
    archive_path = data.get('archive_path')
    if not src_paths or not archive_path:
        return jsonify({'status': 'error', 'message': '缺少源路径列表或压缩包路径参数'}), 400

    username = request.user['username']
    result = create_archive(src_paths, archive_path, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 解压压缩包
@api.route('/file-manager/archive/extract', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def extract_archive_route():
    """解压压缩包"""
    data = request.json
    archive_path = data.get('archive_path')
    target_dir = data.get('target_dir')
    if not archive_path or not target_dir:
        return jsonify({'status': 'error', 'message': '缺少压缩包路径或目标目录参数'}), 400

    username = request.user['username']
    result = extract_archive(archive_path, target_dir, username)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 查询上传状态（断点续传）
@api.route('/file-manager/upload/status', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('file:create')
def get_upload_status_route():
    """查询上传状态"""
    upload_id = request.args.get('upload_id')
    if not upload_id:
        return jsonify({'status': 'error', 'message': '缺少上传ID参数'}), 400

    result = get_upload_status(upload_id)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# -------------------- 站点管理API --------------------

# 获取站点统计信息
@api.route('/sites/stats', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def get_sites_stats_route():
    """获取站点统计信息"""
    return jsonify(site_manager.get_stats())

# 获取站点列表
@api.route('/sites', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def get_sites_route():
    """获取站点列表，支持搜索和筛选"""
    keyword = request.args.get('keyword')
    status = request.args.get('status')
    web_server = request.args.get('web_server')
    php_version = request.args.get('php_version')

    if keyword:
        sites = site_manager.search_sites(keyword)
    else:
        sites = site_manager.get_sites()

    filters = {}
    if status:
        filters['status'] = status
    if web_server:
        filters['web_server'] = web_server
    if php_version:
        filters['php_version'] = php_version
    if filters:
        sites = site_manager.filter_sites(filters)

    return jsonify({'status': 'success', 'sites': sites})

# 获取单个站点详情
@api.route('/sites/<site_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def get_site_route(site_id):
    """获取单个站点详情（含域名列表与配置文件路径）"""
    site = site_manager.get_site(site_id)
    if not site:
        return jsonify({'status': 'error', 'message': 'Site not found'}), 404
    return jsonify({'status': 'success', 'site': site})

# 添加站点
@api.route('/sites', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:create')
def add_site_route():
    """添加新站点，并自动生成 Web 服务器配置文件"""
    data = request.json or {}
    username = request.user['username']
    result = site_manager.add_site(data, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 更新站点信息
@api.route('/sites/<site_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('site:update')
def update_site_route(site_id):
    """更新站点信息"""
    data = request.json or {}
    username = request.user['username']
    result = site_manager.update_site(site_id, data, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 删除站点
@api.route('/sites/<site_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('site:delete')
def delete_site_route(site_id):
    """删除站点及其配置文件、域名绑定"""
    username = request.user['username']
    remove_files = (request.args.get('remove_files', 'false').lower() == 'true')
    result = site_manager.delete_site(site_id, user=username, ip=request.remote_addr,
                                       remove_files=remove_files)
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 批量删除站点
@api.route('/sites/batch/delete', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:delete')
def batch_delete_sites_route():
    """批量删除站点"""
    data = request.json or {}
    site_ids = data.get('site_ids', [])
    if not site_ids:
        return jsonify({'status': 'error', 'message': 'No site IDs provided'}), 400
    username = request.user['username']
    return jsonify(site_manager.batch_delete_sites(site_ids, user=username, ip=request.remote_addr))

# 更新站点状态（仅元数据）
@api.route('/sites/<site_id>/status', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('site:update')
def update_site_status_route(site_id):
    """更新站点状态（仅元数据，不触发服务操作）"""
    data = request.json or {}
    status = data.get('status')
    if not status:
        return jsonify({'status': 'error', 'message': 'Status is required'}), 400
    return jsonify(site_manager.update_site_status(site_id, status))

# 启动站点（重载 Web 服务器使配置生效）
@api.route('/sites/<site_id>/start', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def start_site_route(site_id):
    """启动站点"""
    username = request.user['username']
    result = site_manager.start_site(site_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 停止站点
@api.route('/sites/<site_id>/stop', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def stop_site_route(site_id):
    """停止站点"""
    username = request.user['username']
    result = site_manager.stop_site(site_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 重载站点配置
@api.route('/sites/<site_id>/reload', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def reload_site_route(site_id):
    """重载站点配置"""
    username = request.user['username']
    result = site_manager.reload_site(site_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# -------------------- 站点配置文件管理API --------------------

# 获取站点配置文件内容
@api.route('/sites/<site_id>/config', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def get_site_config_route(site_id):
    """获取站点配置文件内容"""
    result = site_manager.get_site_config(site_id)
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 保存站点配置文件内容
@api.route('/sites/<site_id>/config', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('site:update')
def save_site_config_route(site_id):
    """保存站点配置文件内容（在线编辑）"""
    data = request.json or {}
    content = data.get('content')
    if content is None:
        return jsonify({'status': 'error', 'message': 'Content is required'}), 400
    username = request.user['username']
    result = site_manager.save_site_config(site_id, content,
                                            user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 校验站点配置文件语法
@api.route('/sites/<site_id>/config/validate', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def validate_site_config_route(site_id):
    """校验站点配置文件语法"""
    return jsonify(site_manager.validate_site_config(site_id))

# -------------------- 域名绑定API --------------------

# 获取所有域名
@api.route('/domains', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def get_domains_route():
    """获取所有域名"""
    return jsonify({'status': 'success', 'domains': site_manager.get_domains()})

# 获取站点域名
@api.route('/sites/<site_id>/domains', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def get_site_domains_route(site_id):
    """获取站点域名"""
    return jsonify({'status': 'success', 'domains': site_manager.get_site_domains(site_id)})

# 添加域名绑定
@api.route('/domains', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:create')
def add_domain_route():
    """添加域名绑定"""
    data = request.json or {}
    username = request.user['username']
    result = site_manager.add_domain(data, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 更新域名信息
@api.route('/domains/<domain_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('site:update')
def update_domain_route(domain_id):
    """更新域名信息"""
    data = request.json or {}
    username = request.user['username']
    result = site_manager.update_domain(domain_id, data, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 删除域名绑定
@api.route('/domains/<domain_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('site:delete')
def delete_domain_route(domain_id):
    """删除域名绑定"""
    username = request.user['username']
    result = site_manager.delete_domain(domain_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 批量删除域名
@api.route('/domains/batch/delete', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:delete')
def batch_delete_domains_route():
    """批量删除域名"""
    data = request.json or {}
    domain_ids = data.get('domain_ids', [])
    if not domain_ids:
        return jsonify({'status': 'error', 'message': 'No domain IDs provided'}), 400
    username = request.user['username']
    return jsonify(site_manager.batch_delete_domains(domain_ids, user=username, ip=request.remote_addr))

# 检查域名 DNS 解析状态
@api.route('/domains/<domain_id>/check', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def check_domain_status_route(domain_id):
    """检查域名 DNS 解析状态"""
    username = request.user['username']
    return jsonify(site_manager.check_domain_status(domain_id, user=username, ip=request.remote_addr))

# -------------------- SSL 证书管理API --------------------

# 申请 SSL 证书（Let's Encrypt via certbot）
@api.route('/domains/<domain_id>/ssl/issue', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def issue_ssl_route(domain_id):
    """申请 SSL 证书"""
    data = request.json or {}
    email = data.get('email')
    username = request.user['username']
    result = site_manager.issue_ssl_certificate(domain_id, user=username,
                                                 ip=request.remote_addr, email=email)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 续期 SSL 证书
@api.route('/domains/<domain_id>/ssl/renew', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def renew_ssl_route(domain_id):
    """续期 SSL 证书"""
    username = request.user['username']
    result = site_manager.renew_ssl_certificate(domain_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 撤销 SSL 证书
@api.route('/domains/<domain_id>/ssl/revoke', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def revoke_ssl_route(domain_id):
    """撤销 SSL 证书"""
    username = request.user['username']
    result = site_manager.revoke_ssl_certificate(domain_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 检查 SSL 证书状态
@api.route('/domains/<domain_id>/ssl/status', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def check_ssl_status_route(domain_id):
    """检查 SSL 证书状态"""
    return jsonify(site_manager.check_ssl_status(domain_id))

# -------------------- 站点备份API --------------------

# 备份站点
@api.route('/sites/<site_id>/backup', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('site:manage')
def backup_site_route(site_id):
    """备份站点配置"""
    username = request.user['username']
    result = site_manager.backup_site(site_id, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 列出站点备份
@api.route('/sites/backups', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def list_site_backups_route():
    """列出所有站点备份"""
    site_id = request.args.get('site_id')
    return jsonify(site_manager.list_backups(site_id))

# 删除站点备份
@api.route('/sites/backups/<backup_name>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('site:delete')
def delete_site_backup_route(backup_name):
    """删除站点备份"""
    username = request.user['username']
    result = site_manager.delete_backup(backup_name, user=username, ip=request.remote_addr)
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 下载站点备份
@api.route('/sites/backups/<backup_name>/download', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('site:view')
def download_site_backup_route(backup_name):
    """下载站点备份文件"""
    # 防止路径穿越
    if not backup_name.endswith('.zip') or '/' in backup_name or '\\' in backup_name:
        return jsonify({'status': 'error', 'message': 'Invalid backup name'}), 400
    backup_path = os.path.join(site_manager.backup_dir, backup_name)
    if not os.path.exists(backup_path):
        return jsonify({'status': 'error', 'message': 'Backup not found'}), 404
    return send_file(backup_path, as_attachment=True, download_name=backup_name)

# -------------------- Web服务管理API --------------------

# 重载Web服务
@api.route('/web-service/reload', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('web_service:manage')
def reload_web_service_route():
    """重载Web服务"""
    data = request.json
    web_server = data.get('web_server', 'nginx')
    
    try:
        import subprocess
        
        if web_server == 'nginx':
            # 执行nginx重载命令
            result = subprocess.run(['nginx', '-s', 'reload'], 
                                   capture_output=True, text=True, check=True)
            return jsonify({
                'status': 'success', 
                'message': f'{web_server} service reloaded successfully',
                'output': result.stdout
            })
        elif web_server == 'apache':
            # 执行apache重载命令
            result = subprocess.run(['apachectl', 'graceful'], 
                                   capture_output=True, text=True, check=True)
            return jsonify({
                'status': 'success', 
                'message': f'{web_server} service reloaded successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': f'Unsupported web server: {web_server}'
            })
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error', 
            'message': f'Failed to reload {web_server} service',
            'error': e.stderr
        })
    except FileNotFoundError:
        return jsonify({
            'status': 'error', 
            'message': f'{web_server} is not installed or not in PATH'
        })
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Error occurred while reloading {web_server} service',
            'error': str(e)
        })

# 获取Web服务状态
@api.route('/web-service/status', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('web_service:view')
def get_web_service_status_route():
    """获取Web服务状态"""
    web_server = request.args.get('web_server', 'nginx')
    
    try:
        import subprocess
        
        if web_server == 'nginx':
            # 检查nginx状态
            result = subprocess.run(['nginx', '-t'], 
                                   capture_output=True, text=True, check=True)
            return jsonify({
                'status': 'success', 
                'message': f'{web_server} service is running properly',
                'output': result.stdout
            })
        elif web_server == 'apache':
            # 检查apache状态
            result = subprocess.run(['apachectl', 'status'], 
                                   capture_output=True, text=True, check=True)
            return jsonify({
                'status': 'success', 
                'message': f'{web_server} service is running properly',
                'output': result.stdout
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': f'Unsupported web server: {web_server}'
            })
    except subprocess.CalledProcessError as e:
        return jsonify({
            'status': 'error', 
            'message': f'{web_server} service has issues',
            'error': e.stderr
        })
    except FileNotFoundError:
        return jsonify({
            'status': 'error', 
            'message': f'{web_server} is not installed or not in PATH'
        })
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Error occurred while checking {web_server} service',
            'error': str(e)
        })


# -------------------- 数据库管理API --------------------

# 获取数据库配置列表
@api.route('/databases/configs', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_db_configs_route():
    """获取数据库配置列表"""
    log_operation(request.user['username'], 'get_db_configs', request.remote_addr, 'Retrieved database configurations')
    return jsonify(db_manager.get_db_configs())

# -------------------- 数据库用户权限管理API --------------------

# 获取数据库用户列表
@api.route('/databases/configs/<config_id>/users', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_db_users_route(config_id):
    """获取数据库用户列表"""
    return jsonify(db_manager.get_users(config_id))

# 创建数据库用户
@api.route('/databases/configs/<config_id>/users', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:manage')
def create_db_user_route(config_id):
    """创建数据库用户"""
    data = request.json
    return jsonify(db_manager.create_user(
        config_id=config_id,
        username=data.get('username'),
        password=data.get('password'),
        db_name=data.get('db_name')
    ))

# 修改用户密码
@api.route('/databases/configs/<config_id>/users/<username>/password', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('database:manage')
def change_db_user_password_route(config_id, username):
    """修改数据库用户密码"""
    data = request.json
    return jsonify(db_manager.change_user_password(
        config_id=config_id,
        username=username,
        new_password=data.get('new_password')
    ))

# 删除数据库用户
@api.route('/databases/configs/<config_id>/users/<username>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('database:manage')
def delete_db_user_route(config_id, username):
    """删除数据库用户"""
    return jsonify(db_manager.delete_user(config_id, username))

# 授予用户权限
@api.route('/databases/configs/<config_id>/users/<username>/permissions', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:manage')
def grant_db_permissions_route(config_id, username):
    """授予数据库用户权限"""
    data = request.json
    return jsonify(db_manager.grant_permissions(
        config_id=config_id,
        username=username,
        db_name=data.get('db_name'),
        permissions=data.get('permissions', []),
        table_name=data.get('table_name')
    ))

# 撤销用户权限
@api.route('/databases/configs/<config_id>/users/<username>/permissions', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('database:manage')
def revoke_db_permissions_route(config_id, username):
    """撤销数据库用户权限"""
    data = request.json
    return jsonify(db_manager.revoke_permissions(
        config_id=config_id,
        username=username,
        db_name=data.get('db_name'),
        permissions=data.get('permissions', []),
        table_name=data.get('table_name')
    ))

# 获取用户权限
@api.route('/databases/configs/<config_id>/users/<username>/permissions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_db_user_permissions_route(config_id, username):
    """获取数据库用户权限"""
    db_name = request.args.get('db_name')
    if not db_name:
        return jsonify({'status': 'error', 'message': 'Database name is required'}), 400
    return jsonify(db_manager.get_user_permissions(config_id, username, db_name))

# 获取单个数据库配置
@api.route('/databases/configs/<config_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_db_config_route(config_id):
    """获取单个数据库配置"""
    log_operation(request.user['username'], 'get_db_config', request.remote_addr, f'Retrieved database configuration {config_id}')
    return jsonify(db_manager.get_db_config(config_id))

# 添加数据库配置
@api.route('/databases/configs', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:create')
def add_db_config_route():
    """添加数据库配置"""
    data = request.json
    result = db_manager.add_db_config(
        config_id=data.get('config_id'),
        db_type=data.get('db_type'),
        host=data.get('host'),
        port=data.get('port'),
        username=data.get('username'),
        password=data.get('password'),
        description=data.get('description', '')
    )
    log_operation(request.user['username'], 'add_db_config', request.remote_addr, f'Added database configuration {data.get("config_id")}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 更新数据库配置
@api.route('/databases/configs/<config_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('database:update')
def update_db_config_route(config_id):
    """更新数据库配置"""
    data = request.json
    result = db_manager.update_db_config(config_id, data)
    log_operation(request.user['username'], 'update_db_config', request.remote_addr, f'Updated database configuration {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 删除数据库配置
@api.route('/databases/configs/<config_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('database:delete')
def delete_db_config_route(config_id):
    """删除数据库配置"""
    result = db_manager.delete_db_config(config_id)
    log_operation(request.user['username'], 'delete_db_config', request.remote_addr, f'Deleted database configuration {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 测试数据库连接
@api.route('/databases/configs/<config_id>/test', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def test_db_connection_route(config_id):
    """测试数据库连接"""
    result = db_manager.test_connection(config_id)
    log_operation(request.user['username'], 'test_db_connection', request.remote_addr, f'Tested connection for database configuration {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 获取数据库列表
@api.route('/databases/configs/<config_id>/databases', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_databases_route(config_id):
    """获取数据库列表"""
    return jsonify(db_manager.get_databases(config_id))

# 获取数据库表列表
@api.route('/databases/configs/<config_id>/databases/<db_name>/tables', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_tables_route(config_id, db_name):
    """获取数据库表列表"""
    return jsonify(db_manager.get_tables(config_id, db_name))

# 执行SQL查询
@api.route('/databases/configs/<config_id>/query', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:execute')
def execute_query_route(config_id):
    """执行SQL查询"""
    data = request.json
    query = data.get('query', '')
    query_log = query[:100] + '...' if len(query) > 100 else query
    result = db_manager.execute_query(
        config_id=config_id,
        query=query,
        db_name=data.get('db_name')
    )
    log_operation(request.user['username'], 'execute_sql_query', request.remote_addr, f'Executed query on {config_id}: {query_log}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)


# -------------------- 数据库备份API --------------------

# 获取备份配置列表
@api.route('/databases/backups/configs', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_backup_configs_route():
    """获取备份配置列表"""
    from modules.db_manager import backup_manager
    log_operation(request.user['username'], 'get_backup_configs', request.remote_addr, 'Retrieved backup configurations')
    return jsonify(backup_manager.get_backup_configs())

# 获取单个备份配置
@api.route('/databases/backups/configs/<config_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_backup_config_route(config_id):
    """获取单个备份配置"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.get_backup_config(config_id))

# 添加备份配置
@api.route('/databases/backups/configs', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:create')
def add_backup_config_route():
    """添加备份配置"""
    from modules.db_manager import backup_manager
    data = request.json
    result = backup_manager.add_backup_config(
        config_id=data.get('config_id'),
        db_config_id=data.get('db_config_id'),
        db_name=data.get('db_name'),
        backup_type=data.get('backup_type'),
        schedule=data.get('schedule'),
        retention_days=data.get('retention_days'),
        compression=data.get('compression', True),
        description=data.get('description', '')
    )
    log_operation(request.user['username'], 'add_backup_config', request.remote_addr, f'Added backup configuration {data.get("config_id")}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 更新备份配置
@api.route('/databases/backups/configs/<config_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('database:update')
def update_backup_config_route(config_id):
    """更新备份配置"""
    from modules.db_manager import backup_manager
    data = request.json
    return jsonify(backup_manager.update_backup_config(config_id, data))

# 删除备份配置
@api.route('/databases/backups/configs/<config_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('database:delete')
def delete_backup_config_route(config_id):
    """删除备份配置"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.delete_backup_config(config_id))

# 触发手动备份
@api.route('/databases/backups/configs/<config_id>/trigger', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:execute')
def trigger_backup_route(config_id):
    """触发手动备份"""
    from modules.db_manager import backup_manager
    data = request.json or {}
    backup_type = data.get('backup_type')
    result = backup_manager.trigger_backup(config_id, backup_type)
    log_operation(request.user['username'], 'trigger_backup', request.remote_addr, f'Triggered manual backup for {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 获取备份历史
@api.route('/databases/backups/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_backup_history_route():
    """获取备份历史"""
    from modules.db_manager import backup_manager
    db_config_id = request.args.get('db_config_id')
    db_name = request.args.get('db_name')
    return jsonify(backup_manager.get_backup_history(db_config_id, db_name))

# 获取备份详情
@api.route('/databases/backups/<backup_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_backup_info_route(backup_id):
    """获取备份详情"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.get_backup_info(backup_id))

# 验证备份完整性
@api.route('/databases/backups/<backup_id>/verify', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def verify_backup_route(backup_id):
    """验证备份完整性"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.verify_backup(backup_id))

# 恢复备份
@api.route('/databases/backups/<backup_id>/restore', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:execute')
def restore_backup_route(backup_id):
    """恢复备份"""
    from modules.db_manager import backup_manager
    data = request.json or {}
    result = backup_manager.restore_backup(
        backup_id=backup_id,
        target_config_id=data.get('target_config_id'),
        target_db_name=data.get('target_db_name')
    )
    log_operation(request.user['username'], 'restore_backup', request.remote_addr, f'Restored backup {backup_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 删除备份
@api.route('/databases/backups/<backup_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('database:delete')
def delete_backup_route(backup_id):
    """删除备份"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.delete_backup(backup_id))

# 获取待执行的备份任务
@api.route('/databases/backups/scheduled', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_scheduled_backups_route():
    """获取待执行的备份任务"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.get_scheduled_backups())


# -------------------- 数据库监控API --------------------

# 获取监控配置列表
@api.route('/databases/monitor/configs', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_monitor_configs_route():
    """获取监控配置列表"""
    from modules.db_manager import db_monitor
    log_operation(request.user['username'], 'get_monitor_configs', request.remote_addr, 'Retrieved monitoring configurations')
    return jsonify(db_monitor.get_monitor_configs())

# 获取单个监控配置
@api.route('/databases/monitor/configs/<config_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_monitor_config_route(config_id):
    """获取单个监控配置"""
    from modules.db_manager import db_monitor
    return jsonify(db_monitor.get_monitor_config(config_id))

# 添加监控配置
@api.route('/databases/monitor/configs', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:create')
def add_monitor_config_route():
    """添加监控配置"""
    from modules.db_manager import db_monitor
    data = request.json
    result = db_monitor.add_monitor_config(
        config_id=data.get('config_id'),
        db_config_id=data.get('db_config_id'),
        db_name=data.get('db_name'),
        metrics=data.get('metrics', []),
        collection_interval=data.get('collection_interval', 60),
        alert_enabled=data.get('alert_enabled', True),
        description=data.get('description', '')
    )
    log_operation(request.user['username'], 'add_monitor_config', request.remote_addr, f'Added monitoring configuration {data.get("config_id")}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 更新监控配置
@api.route('/databases/monitor/configs/<config_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('database:update')
def update_monitor_config_route(config_id):
    """更新监控配置"""
    from modules.db_manager import db_monitor
    data = request.json
    return jsonify(db_monitor.update_monitor_config(config_id, data))

# 删除监控配置
@api.route('/databases/monitor/configs/<config_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('database:delete')
def delete_monitor_config_route(config_id):
    """删除监控配置"""
    from modules.db_manager import db_monitor
    return jsonify(db_monitor.delete_monitor_config(config_id))

# 开始监控
@api.route('/databases/monitor/configs/<config_id>/start', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:execute')
def start_monitoring_route(config_id):
    """开始监控"""
    from modules.db_manager import db_monitor
    result = db_monitor.start_monitoring(config_id)
    log_operation(request.user['username'], 'start_monitoring', request.remote_addr, f'Started monitoring for {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 停止监控
@api.route('/databases/monitor/configs/<config_id>/stop', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:execute')
def stop_monitoring_route(config_id):
    """停止监控"""
    from modules.db_manager import db_monitor
    result = db_monitor.stop_monitoring(config_id)
    log_operation(request.user['username'], 'stop_monitoring', request.remote_addr, f'Stopped monitoring for {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 获取实时指标
@api.route('/databases/monitor/configs/<config_id>/metrics', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_db_realtime_metrics_route(config_id):
    """获取数据库实时指标"""
    from modules.db_manager import db_monitor
    metrics_param = request.args.get('metrics')
    metrics = metrics_param.split(',') if metrics_param else None
    return jsonify(db_monitor.get_realtime_metrics(config_id, metrics))

# 获取历史指标
@api.route('/databases/monitor/metrics/historical', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_db_historical_metrics_route():
    """获取数据库历史指标"""
    from modules.db_manager import db_monitor
    db_config_id = request.args.get('db_config_id')
    db_name = request.args.get('db_name')
    metric_name = request.args.get('metric_name')
    time_range = request.args.get('time_range', '1h')
    
    if not all([db_config_id, db_name, metric_name]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400
    
    return jsonify(db_monitor.get_historical_metrics(db_config_id, db_name, metric_name, time_range))

# 获取慢查询
@api.route('/databases/monitor/slow-queries', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_slow_queries_route():
    """获取慢查询"""
    from modules.db_manager import db_monitor
    db_config_id = request.args.get('db_config_id')
    db_name = request.args.get('db_name')
    limit = int(request.args.get('limit', 20))
    time_range = request.args.get('time_range', '24h')
    
    if not all([db_config_id, db_name]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400
    
    return jsonify(db_monitor.get_slow_queries(db_config_id, db_name, limit, time_range))

# 获取优化建议
@api.route('/databases/monitor/optimization', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_optimization_recommendations_route():
    """获取优化建议"""
    from modules.db_manager import db_monitor
    db_config_id = request.args.get('db_config_id')
    db_name = request.args.get('db_name')
    
    if not all([db_config_id, db_name]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400
    
    return jsonify(db_monitor.get_optimization_recommendations(db_config_id, db_name))

# 添加告警阈值
@api.route('/databases/monitor/alerts/thresholds', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('database:create')
def add_alert_threshold_route():
    """添加告警阈值"""
    from modules.db_manager import db_monitor
    data = request.json
    return jsonify(db_monitor.add_alert_threshold(
        db_config_id=data.get('db_config_id'),
        db_name=data.get('db_name'),
        metric_name=data.get('metric_name'),
        threshold_type=data.get('threshold_type'),
        threshold_value=data.get('threshold_value'),
        alert_message=data.get('alert_message', '')
    ))

# 获取告警列表
@api.route('/databases/monitor/alerts', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('database:view')
def get_alerts_route():
    """获取告警列表"""
    from modules.db_manager import db_monitor
    db_config_id = request.args.get('db_config_id')
    db_name = request.args.get('db_name')
    status = request.args.get('status')
    return jsonify(db_monitor.get_alerts(db_config_id, db_name, status))


# -------------------- 系统监控增强API --------------------

@api.route('/monitor/realtime', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_realtime_metrics_route():
    """获取实时系统指标"""
    from modules.system_monitor import metrics_collector
    return jsonify(metrics_collector.get_realtime_metrics())

@api.route('/monitor/network/traffic', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_network_traffic_route():
    """获取网络流量信息"""
    from modules.system_monitor import get_network_traffic
    return jsonify(get_network_traffic())

@api.route('/monitor/network/traffic/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_network_traffic_history_route():
    """获取网络流量历史"""
    from modules.system_monitor import get_network_traffic_history
    time_range = request.args.get('time_range', '1h')
    return jsonify(get_network_traffic_history(time_range))

@api.route('/monitor/disk-io', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_disk_io_route():
    """获取磁盘IO信息"""
    from modules.system_monitor import get_disk_io
    return jsonify(get_disk_io())

@api.route('/monitor/disk-io/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_disk_io_history_route():
    """获取磁盘IO历史"""
    from modules.system_monitor import get_disk_io_history
    time_range = request.args.get('time_range', '1h')
    return jsonify(get_disk_io_history(time_range))

@api.route('/monitor/history/<metric_type>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_historical_metrics_route(metric_type):
    """获取历史指标数据"""
    from modules.system_monitor import metrics_collector
    time_range = request.args.get('time_range', '1h')
    granularity = request.args.get('granularity', 'minute')
    return jsonify(metrics_collector.get_historical_metrics(metric_type, time_range, granularity))

@api.route('/monitor/top-processes', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_top_processes_route():
    """获取资源占用最高的进程"""
    from modules.system_monitor import get_top_processes
    sort_by = request.args.get('sort_by', 'cpu')
    limit = int(request.args.get('limit', 10))
    return jsonify(get_top_processes(sort_by, limit))

@api.route('/monitor/process/<int:pid>/detail', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_process_detail_monitor_route(pid):
    """获取进程详细信息"""
    from modules.system_monitor import get_process_detail
    return jsonify(get_process_detail(pid))

@api.route('/monitor/export', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def export_metrics_route():
    """导出指标数据"""
    from modules.system_monitor import export_metrics_data
    data = request.json
    return jsonify(export_metrics_data(
        metric_types=data.get('metric_types', []),
        time_range=data.get('time_range', '24h'),
        format=data.get('format', 'json')
    ))

@api.route('/monitor/gpu', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_gpu_route():
    """获取 GPU 监控信息"""
    from modules.system_monitor import get_gpu_info
    return jsonify(get_gpu_info())

@api.route('/monitor/temperature', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_temperature_route():
    """获取温度传感器信息"""
    from modules.system_monitor import get_temperature_info
    return jsonify(get_temperature_info())

@api.route('/monitor/disk-io/per-disk', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_per_disk_io_route():
    """获取每磁盘 IO 统计"""
    from modules.system_monitor import get_per_disk_io
    return jsonify({'disks': get_per_disk_io()})

@api.route('/monitor/network/interfaces', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_per_network_interface_route():
    """获取每网卡流量统计"""
    from modules.system_monitor import get_per_network_interface_traffic
    return jsonify({'interfaces': get_per_network_interface_traffic()})

@api.route('/monitor/load-average', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_load_average_route():
    """获取系统负载平均值"""
    from modules.system_monitor import metrics_collector
    return jsonify(metrics_collector.get_realtime_metrics().get('load_average', {}))

@api.route('/monitor/swap', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_swap_route():
    """获取 swap 交换分区信息"""
    import psutil
    swap = psutil.swap_memory()
    return jsonify({
        'total': swap.total,
        'used': swap.used,
        'free': swap.free,
        'percent': swap.percent,
        'sin': swap.sin,
        'sout': swap.sout
    })

# -------------------- 系统告警阈值API --------------------

@api.route('/monitor/alerts/thresholds', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_alert_thresholds_route():
    """获取告警阈值列表"""
    from modules.system_monitor import metrics_collector
    return jsonify({'status': 'success', 'thresholds': metrics_collector.get_alert_thresholds()})

@api.route('/monitor/alerts/thresholds', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:manage')
def add_alert_threshold_route():
    """新增告警阈值"""
    from modules.system_monitor import metrics_collector
    data = request.json or {}
    result = metrics_collector.add_alert_threshold(
        metric_name=data.get('metric_name'),
        threshold_type=data.get('threshold_type'),
        threshold_value=data.get('threshold_value'),
        alert_message=data.get('alert_message', '')
    )
    log_operation(request.user['username'], 'add_alert_threshold', request.remote_addr,
                  f"Added alert threshold for {data.get('metric_name')}",
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

@api.route('/monitor/alerts/thresholds/<int:threshold_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:manage')
def update_alert_threshold_route(threshold_id):
    """更新告警阈值"""
    from modules.system_monitor import metrics_collector
    data = request.json or {}
    return jsonify(metrics_collector.update_alert_threshold(threshold_id, data))

@api.route('/monitor/alerts/thresholds/<int:threshold_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:manage')
def delete_alert_threshold_route(threshold_id):
    """删除告警阈值"""
    from modules.system_monitor import metrics_collector
    result = metrics_collector.delete_alert_threshold(threshold_id)
    log_operation(request.user['username'], 'delete_alert_threshold', request.remote_addr,
                  f"Deleted alert threshold {threshold_id}",
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

@api.route('/monitor/alerts', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:view')
def get_system_alerts_route():
    """获取系统告警列表"""
    from modules.system_monitor import metrics_collector
    status = request.args.get('status')
    limit = int(request.args.get('limit', 100))
    return jsonify(metrics_collector.get_alerts(status=status, limit=limit))

@api.route('/monitor/alerts/<int:alert_id>/resolve', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('monitor:manage')
def resolve_system_alert_route(alert_id):
    """手动解除告警"""
    from modules.system_monitor import metrics_collector
    result = metrics_collector.resolve_alert(alert_id)
    log_operation(request.user['username'], 'resolve_alert', request.remote_addr,
                  f"Resolved alert {alert_id}",
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)


# -------------------- Widget布局API --------------------

@api.route('/dashboard/widgets/layout', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('dashboard:view')
def get_widget_layout_route():
    """获取用户Widget布局"""
    from modules.system_monitor import get_widget_layout
    username = request.user['username']
    return jsonify(get_widget_layout(username))

@api.route('/dashboard/widgets/layout', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('dashboard:update')
def save_widget_layout_route():
    """保存用户Widget布局"""
    from modules.system_monitor import save_widget_layout
    username = request.user['username']
    layout = request.json
    return jsonify(save_widget_layout(username, layout))

@api.route('/dashboard/widgets/default', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('dashboard:view')
def get_default_widget_layout_route():
    """获取默认Widget布局"""
    from modules.system_monitor import get_default_layout
    return jsonify(get_default_layout())


# -------------------- 终端模拟器API --------------------

@api.route('/terminal/shells', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('terminal:view')
def get_available_shells_route():
    """获取可用的Shell列表"""
    from modules.terminal_manager import get_available_shells
    return jsonify(get_available_shells())

@api.route('/terminal/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('terminal:view')
def get_command_history_route():
    """获取命令历史"""
    from modules.terminal_manager import get_command_history
    username = request.user['username']
    limit = int(request.args.get('limit', 100))
    return jsonify(get_command_history(username, limit))

@api.route('/terminal/history', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('terminal:execute')
def save_command_history_route():
    """保存单条命令历史"""
    from modules.terminal_manager import save_command_history
    data = request.json or {}
    command = (data.get('command') or '').strip()
    if not command:
        return jsonify({'status': 'error', 'message': 'Empty command'}), 400
    # 限制单条命令长度，避免历史文件膨胀
    if len(command) > 4096:
        command = command[:4096]
    username = request.user['username']
    ok = save_command_history(username, command)
    return jsonify({'status': 'success' if ok else 'error'})

@api.route('/terminal/history/search', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('terminal:view')
def search_command_history_route():
    """搜索命令历史"""
    from modules.terminal_manager import search_command_history
    username = request.user['username']
    query = request.args.get('query', '')
    return jsonify(search_command_history(username, query))

@api.route('/terminal/suggestions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('terminal:view')
def get_command_suggestions_route():
    """获取命令建议"""
    from modules.terminal_manager import get_command_suggestions
    username = request.user['username']
    partial = request.args.get('partial', '')
    return jsonify(get_command_suggestions(username, partial))

@api.route('/terminal/history/clear', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('terminal:execute')
def clear_command_history_route():
    """清空命令历史"""
    from modules.terminal_manager import clear_command_history
    username = request.user['username']
    return jsonify(clear_command_history(username))


# -------------------- 代码编辑器API --------------------

@api.route('/editor/languages', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def get_editor_languages_route():
    """获取支持的语言列表"""
    from modules.code_editor import get_all_languages
    return jsonify(get_all_languages())

@api.route('/editor/language/<filename>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def detect_language_route(filename):
    """检测文件语言"""
    from modules.code_editor import get_language_from_extension
    return jsonify({'language': get_language_from_extension(filename)})

@api.route('/editor/tokenize', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def tokenize_code_route():
    """代码分词"""
    from modules.code_editor import tokenize_code, get_language_from_extension
    data = request.json
    code = data.get('code', '')
    filename = data.get('filename', '')
    language = data.get('language') or get_language_from_extension(filename)
    return jsonify(tokenize_code(code, language))

@api.route('/editor/completions', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def get_completions_route():
    """获取代码补全建议"""
    from modules.code_editor import get_code_completions, get_language_from_extension
    data = request.json
    code = data.get('code', '')
    filename = data.get('filename', '')
    cursor_position = data.get('cursor_position', 0)
    language = data.get('language') or get_language_from_extension(filename)
    return jsonify(get_code_completions(code, language, cursor_position))

@api.route('/editor/search', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def search_in_file_route():
    """在文件中搜索"""
    from modules.code_editor import search_in_file
    data = request.json
    return jsonify(search_in_file(
        content=data.get('content', ''),
        query=data.get('query', ''),
        case_sensitive=data.get('case_sensitive', False),
        whole_word=data.get('whole_word', False),
        regex=data.get('regex', False)
    ))

@api.route('/editor/replace', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:update')
def replace_in_file_route():
    """在文件中替换"""
    from modules.code_editor import replace_in_file
    data = request.json
    return jsonify(replace_in_file(
        content=data.get('content', ''),
        search=data.get('search', ''),
        replace=data.get('replace', ''),
        case_sensitive=data.get('case_sensitive', False),
        whole_word=data.get('whole_word', False),
        regex=data.get('regex', False)
    ))

@api.route('/editor/search-files', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def search_in_files_route():
    """在多个文件中搜索"""
    from modules.code_editor import search_in_files
    data = request.json
    return jsonify(search_in_files(
        base_path=data.get('base_path', '/'),
        query=data.get('query', ''),
        file_patterns=data.get('file_patterns'),
        case_sensitive=data.get('case_sensitive', False),
        whole_word=data.get('whole_word', False),
        regex=data.get('regex', False)
    ))

@api.route('/editor/settings', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def get_editor_settings_route():
    """获取编辑器设置"""
    from modules.code_editor import get_editor_settings
    username = request.user['username']
    return jsonify(get_editor_settings(username))

@api.route('/editor/settings', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:update')
def save_editor_settings_route():
    """保存编辑器设置"""
    from modules.code_editor import save_editor_settings
    username = request.user['username']
    settings = request.json
    return jsonify(save_editor_settings(username, settings))

@api.route('/editor/sessions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def get_file_sessions_route():
    """获取文件会话"""
    from modules.code_editor import get_file_sessions
    username = request.user['username']
    return jsonify(get_file_sessions(username))

@api.route('/editor/sessions', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:update')
def save_file_session_route():
    """保存文件会话"""
    from modules.code_editor import save_file_session
    username = request.user['username']
    session_data = request.json
    return jsonify(save_file_session(username, session_data))

@api.route('/editor/sessions/<path:file_path>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('editor:update')
def close_file_session_route(file_path):
    """关闭文件会话"""
    from modules.code_editor import close_file_session
    username = request.user['username']
    return jsonify(close_file_session(username, file_path))

@api.route('/editor/outline', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('editor:view')
def get_file_outline_route():
    """获取文件大纲"""
    from modules.code_editor import get_file_outline, get_language_from_extension
    data = request.json
    content = data.get('content', '')
    filename = data.get('filename', '')
    language = data.get('language') or get_language_from_extension(filename)
    return jsonify(get_file_outline(content, language))


# -------------------- 双因素认证(2FA)管理API --------------------

# 获取2FA状态
@api.route('/2fa/status', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('user:view')
def get_2fa_status_route():
    """获取当前用户的2FA状态"""
    from modules.totp_manager import get_2fa_status
    username = request.user['username']
    return jsonify(get_2fa_status(username))

# 初始化2FA设置（生成密钥和QR码）
@api.route('/2fa/setup', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def setup_2fa_route():
    """初始化2FA设置，生成密钥和二维码"""
    from modules.totp_manager import setup_2fa
    username = request.user['username']
    result = setup_2fa(username)
    return jsonify(result)

# 启用2FA（验证验证码后正式启用）
@api.route('/2fa/enable', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def enable_2fa_route():
    """验证验证码并启用2FA"""
    from modules.totp_manager import enable_2fa
    username = request.user['username']
    data = request.json
    secret = data.get('secret')
    verification_code = data.get('verification_code')

    if not secret or not verification_code:
        return jsonify({'status': 'error', 'message': '密钥和验证码不能为空'}), 400

    result, status_code = enable_2fa(username, secret, verification_code)
    log_operation(username, 'enable_2fa', request.remote_addr, '2FA enabled', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result), status_code

# 禁用2FA
@api.route('/2fa/disable', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def disable_2fa_route():
    """禁用2FA"""
    from modules.totp_manager import disable_2fa
    username = request.user['username']
    data = request.json
    verification_code = data.get('verification_code')

    result, status_code = disable_2fa(username, verification_code)
    log_operation(username, 'disable_2fa', request.remote_addr, '2FA disabled', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result), status_code

# 重新生成备用验证码
@api.route('/2fa/backup-codes/regenerate', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('user:update')
def regenerate_backup_codes_route():
    """重新生成备用验证码"""
    from modules.totp_manager import regenerate_backup_codes
    username = request.user['username']
    data = request.json
    verification_code = data.get('verification_code')

    if not verification_code:
        return jsonify({'status': 'error', 'message': '验证码不能为空'}), 400

    result, status_code = regenerate_backup_codes(username, verification_code)
    log_operation(username, 'regenerate_backup_codes', request.remote_addr, 'Backup codes regenerated', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result), status_code


# -------------------- 防火墙管理API --------------------

# 获取防火墙状态
@api.route('/firewall/status', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:view')
def get_firewall_status_route():
    """获取防火墙状态、后端类型、规则列表"""
    from modules.firewall_manager import get_firewall_status
    return jsonify(get_firewall_status())

# 启用防火墙
@api.route('/firewall/enable', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:manage')
def enable_firewall_route():
    """启用防火墙"""
    from modules.firewall_manager import enable_firewall
    result = enable_firewall()
    log_operation(request.user['username'], 'enable_firewall', request.remote_addr,
                  'Firewall enabled', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 禁用防火墙
@api.route('/firewall/disable', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:manage')
def disable_firewall_route():
    """禁用防火墙"""
    from modules.firewall_manager import disable_firewall
    result = disable_firewall()
    log_operation(request.user['username'], 'disable_firewall', request.remote_addr,
                  'Firewall disabled', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 重载防火墙规则
@api.route('/firewall/reload', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:manage')
def reload_firewall_route():
    """重载防火墙规则"""
    from modules.firewall_manager import reload_firewall
    result = reload_firewall()
    log_operation(request.user['username'], 'reload_firewall', request.remote_addr,
                  'Firewall reloaded', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 添加防火墙规则
@api.route('/firewall/rules', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:create')
def add_firewall_rule_route():
    """添加防火墙规则
    请求体参数：
    - port: 端口号或端口范围（必填，如 80 或 8000:8100）
    - protocol: 协议 tcp/udp（默认 tcp）
    - action: allow/deny/reject（默认 allow）
    - source_ip: 来源 IP（可选）
    - direction: in/out（默认 in）
    - name: 规则名称（Windows 可选）
    - permanent: 是否永久生效（默认 true）
    """
    from modules.firewall_manager import add_firewall_rule
    data = request.json or {}
    result = add_firewall_rule(data)
    log_operation(request.user['username'], 'add_firewall_rule', request.remote_addr,
                  f'Added firewall rule: {data.get("port")}/{data.get("protocol", "tcp")} {data.get("action", "allow")}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 删除防火墙规则
@api.route('/firewall/rules', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:delete')
def delete_firewall_rule_route():
    """删除防火墙规则
    请求体参数：port, protocol, action, source_ip, direction, name(Windows)
    """
    from modules.firewall_manager import delete_firewall_rule
    data = request.json or {}
    result = delete_firewall_rule(data)
    log_operation(request.user['username'], 'delete_firewall_rule', request.remote_addr,
                  f'Deleted firewall rule: {data.get("port") or data.get("name")}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 快速放行端口
@api.route('/firewall/quick-allow', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:create')
def quick_allow_port_route():
    """快速放行端口
    请求体参数：port, protocol(默认 tcp)
    """
    from modules.firewall_manager import quick_allow_port
    data = request.json or {}
    port = data.get('port')
    protocol = data.get('protocol', 'tcp')
    if port is None:
        return jsonify({'status': 'error', 'message': 'Port is required'}), 400
    try:
        port = int(port)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Invalid port'}), 400
    result = quick_allow_port(port, protocol)
    log_operation(request.user['username'], 'quick_allow_port', request.remote_addr,
                  f'Quick allow port: {port}/{protocol}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 快速封禁端口
@api.route('/firewall/quick-block', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:create')
def quick_block_port_route():
    """快速封禁端口
    请求体参数：port, protocol(默认 tcp)
    """
    from modules.firewall_manager import quick_block_port
    data = request.json or {}
    port = data.get('port')
    protocol = data.get('protocol', 'tcp')
    if port is None:
        return jsonify({'status': 'error', 'message': 'Port is required'}), 400
    try:
        port = int(port)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Invalid port'}), 400
    result = quick_block_port(port, protocol)
    log_operation(request.user['username'], 'quick_block_port', request.remote_addr,
                  f'Quick block port: {port}/{protocol}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 设置默认策略
@api.route('/firewall/default-policy', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:manage')
def set_default_policy_route():
    """设置防火墙默认策略（仅 ufw 支持）
    请求体参数：direction(incoming/outgoing/forward), policy(allow/deny/reject)
    """
    from modules.firewall_manager import set_default_policy
    data = request.json or {}
    result = set_default_policy(data)
    log_operation(request.user['username'], 'set_default_policy', request.remote_addr,
                  f'Set default policy: {data.get("direction")} -> {data.get("policy")}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 获取可用服务列表（仅 firewalld）
@api.route('/firewall/services', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('firewall:view')
def get_firewall_services_route():
    """获取防火墙可用服务列表"""
    from modules.firewall_manager import get_available_services
    return jsonify(get_available_services())


# -------------------- 定时任务管理API --------------------

# 获取所有定时任务
@api.route('/cron/tasks', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('cron:view')
def get_cron_tasks_route():
    """获取所有定时任务"""
    from modules.cron_manager import cron_manager
    return jsonify(cron_manager.get_all_tasks())

# 获取单个定时任务详情
@api.route('/cron/tasks/<task_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('cron:view')
def get_cron_task_route(task_id):
    """获取单个定时任务详情"""
    from modules.cron_manager import cron_manager
    result = cron_manager.get_task(task_id)
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 创建定时任务
@api.route('/cron/tasks', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('cron:create')
def add_cron_task_route():
    """创建定时任务
    请求体参数：
    - name: 任务名称（必填）
    - command: 执行命令（必填）
    - cron_expr: Cron 表达式（必填，5段式）
    - description: 描述（可选）
    - enabled: 是否启用（可选，默认 true）
    - timeout: 超时秒数（可选，默认 3600）
    """
    from modules.cron_manager import cron_manager
    data = request.json or {}
    result = cron_manager.add_task(
        name=data.get('name', ''),
        command=data.get('command', ''),
        cron_expr=data.get('cron_expr', ''),
        description=data.get('description', ''),
        enabled=data.get('enabled', True),
        timeout=data.get('timeout', 3600)
    )
    log_operation(request.user['username'], 'add_cron_task', request.remote_addr,
                  f'Added cron task: {data.get("name")}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 更新定时任务
@api.route('/cron/tasks/<task_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('cron:update')
def update_cron_task_route(task_id):
    """更新定时任务"""
    from modules.cron_manager import cron_manager
    data = request.json or {}
    result = cron_manager.update_task(task_id, data)
    log_operation(request.user['username'], 'update_cron_task', request.remote_addr,
                  f'Updated cron task: {task_id}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 删除定时任务
@api.route('/cron/tasks/<task_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('cron:delete')
def delete_cron_task_route(task_id):
    """删除定时任务"""
    from modules.cron_manager import cron_manager
    result = cron_manager.delete_task(task_id)
    log_operation(request.user['username'], 'delete_cron_task', request.remote_addr,
                  f'Deleted cron task: {task_id}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 启用/禁用定时任务
@api.route('/cron/tasks/<task_id>/toggle', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('cron:update')
def toggle_cron_task_route(task_id):
    """启用/禁用定时任务"""
    from modules.cron_manager import cron_manager
    result = cron_manager.toggle_task(task_id)
    log_operation(request.user['username'], 'toggle_cron_task', request.remote_addr,
                  f'Toggled cron task: {task_id} -> {"enabled" if result.get("enabled") else "disabled"}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        return jsonify(result), 404
    return jsonify(result)

# 手动执行定时任务
@api.route('/cron/tasks/<task_id>/run', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('cron:execute')
def run_cron_task_route(task_id):
    """手动触发定时任务执行"""
    from modules.cron_manager import cron_manager
    result = cron_manager.run_task_now(task_id)
    log_operation(request.user['username'], 'run_cron_task', request.remote_addr,
                  f'Manually triggered cron task: {task_id}',
                  level='INFO' if result['status'] == 'success' else 'ERROR')
    if result['status'] == 'error':
        # 任务不存在返回 404，任务正在运行返回 409
        if 'already running' in result.get('message', '').lower():
            return jsonify(result), 409
        return jsonify(result), 404
    return jsonify(result)

# 获取任务执行历史
@api.route('/cron/tasks/<task_id>/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('cron:view')
def get_cron_task_history_route(task_id):
    """获取任务执行历史"""
    from modules.cron_manager import cron_manager
    try:
        limit = int(request.args.get('limit', 20))
    except ValueError:
        limit = 20
    return jsonify(cron_manager.get_task_history(task_id, limit))

# 获取所有任务执行历史
@api.route('/cron/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('cron:view')
def get_cron_history_route():
    """获取所有任务执行历史"""
    from modules.cron_manager import cron_manager
    try:
        limit = int(request.args.get('limit', 100))
    except ValueError:
        limit = 100
    return jsonify(cron_manager.get_all_history(limit))

# 清空任务执行历史
@api.route('/cron/tasks/<task_id>/history', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('cron:delete')
def clear_cron_task_history_route(task_id):
    """清空任务执行历史"""
    from modules.cron_manager import cron_manager
    result = cron_manager.clear_task_history(task_id)
    log_operation(request.user['username'], 'clear_cron_history', request.remote_addr,
                  f'Cleared history for cron task: {task_id}')
    return jsonify(result)

# 校验 Cron 表达式
@api.route('/cron/validate', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('cron:view')
def validate_cron_route():
    """校验 Cron 表达式"""
    from modules.cron_manager import cron_manager
    data = request.json or {}
    cron_expr = data.get('cron_expr', '')
    is_valid = cron_manager.validate_cron(cron_expr)
    return jsonify({'status': 'success', 'valid': is_valid})


# -------------------- 角色与权限管理API --------------------

# 获取所有角色列表
@api.route('/roles', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('role:view')
def get_roles_route():
    """获取所有角色列表"""
    return jsonify({'status': 'success', 'roles': rbac.list_roles()})

# 获取单个角色详情
@api.route('/roles/<role_key>', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('role:view')
def get_role_route(role_key):
    """获取单个角色详情"""
    role = rbac.get_role(role_key)
    if not role:
        return jsonify({'status': 'error', 'message': f'Role {role_key} not found'}), 404
    return jsonify({'status': 'success', 'role': role})

# 创建自定义角色
@api.route('/roles', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('role:create')
def create_role_route():
    """创建自定义角色"""
    data = request.json or {}
    role_key = data.get('key')
    name = data.get('name')
    description = data.get('description', '')
    permissions = data.get('permissions', [])
    result, status_code = rbac.create_role(role_key, name, description, permissions)
    if result['status'] == 'success':
        log_operation(request.user['username'], 'create_role', request.remote_addr,
                      f'Created role: {role_key}', level='INFO')
    return jsonify(result), status_code

# 更新角色定义
@api.route('/roles/<role_key>', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('role:update')
def update_role_route(role_key):
    """更新角色定义（内置角色不可改权限）"""
    data = request.json or {}
    result, status_code = rbac.update_role(
        role_key,
        name=data.get('name'),
        description=data.get('description'),
        permissions=data.get('permissions')
    )
    if result['status'] == 'success':
        log_operation(request.user['username'], 'update_role', request.remote_addr,
                      f'Updated role: {role_key}', level='INFO')
    return jsonify(result), status_code

# 删除自定义角色
@api.route('/roles/<role_key>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('role:delete')
def delete_role_route(role_key):
    """删除自定义角色（内置角色不可删；被用户引用时不可删）"""
    from config.config import Config
    result, status_code = rbac.delete_role(role_key, Config.USERS)
    if result['status'] == 'success':
        log_operation(request.user['username'], 'delete_role', request.remote_addr,
                      f'Deleted role: {role_key}', level='INFO')
    return jsonify(result), status_code

# 获取所有可用权限定义（资源与操作）
@api.route('/permissions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('role:view')
def get_permissions_route():
    """获取所有可用的资源与操作定义，供前端构建权限选择器"""
    return jsonify({'status': 'success', 'permissions': rbac.get_all_permissions()})

# 获取当前登录用户的权限信息
@api.route('/me/permissions', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_my_permissions_route():
    """获取当前登录用户的角色与权限（用于前端按权限渲染UI）"""
    user = request.user
    return jsonify({
        'status': 'success',
        'user': {
            'username': user.get('username'),
            'role': user.get('role'),
            'permissions': user.get('permissions', [])
        }
    })




