from flask import Blueprint, jsonify, request, send_file
from modules.system_info import get_system_info
from modules.process_manager import get_processes, manage_process, get_process_detail, manage_processes
from modules.service_manager import get_services, manage_service, get_service_status, get_service_logs, get_service_unit_file, get_service_dependencies
from modules.log_manager import get_logs, read_log_file, search_logs, log_operation
from modules.system_config import get_system_config, update_system_config
from modules.auth import login, authenticate, refresh_token
from modules.middleware import ip_whitelist_required
from modules.file_manager import (
    get_whitelist_dirs, list_directory, create_file, delete_file,
    read_file, write_file, get_file_permissions, init_upload,
    upload_chunk, complete_upload, cancel_upload, download_file,
    get_file_versions, restore_file_version
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
    return login(request.json)

# 刷新令牌路由
@api.route('/refresh-token', methods=['POST'])
def refresh_token_route():
    return refresh_token(request.json)

# 系统信息路由
@api.route('/system/info', methods=['GET'])
@authenticate
@ip_whitelist_required
def system_info_route():
    return jsonify(get_system_info())

# 实时系统状态路由（适合频繁调用）
@api.route('/system/status', methods=['GET'])
@authenticate
@ip_whitelist_required
def system_status_route():
    from modules.system_info import get_real_time_status
    return jsonify(get_real_time_status())

# 进程管理路由
@api.route('/processes', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_processes_route():
    sort_by = request.args.get('sort_by')
    sort_order = request.args.get('sort_order', 'asc')
    search_term = request.args.get('search')
    return jsonify(get_processes(sort_by=sort_by, sort_order=sort_order, search_term=search_term))

@api.route('/processes/<int:pid>', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_process_detail_route(pid):
    detail = get_process_detail(pid)
    if detail is None:
        return jsonify({'status': 'error', 'message': f'Process {pid} not found'}), 404
    return jsonify(detail)

@api.route('/processes/<int:pid>/<action>', methods=['POST'])
@authenticate
@ip_whitelist_required
def manage_process_route(pid, action):
    return jsonify(manage_process(pid, action))

@api.route('/processes/batch/<action>', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_services_route():
    # Get query parameters for filtering and sorting
    filter_status = request.args.get('filter')
    sort_by = request.args.get('sort')
    return jsonify(get_services(filter_status=filter_status, sort_by=sort_by))

@api.route('/services/<service_name>', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_service_status_route(service_name):
    return jsonify(get_service_status(service_name))

@api.route('/services/<service_name>/<action>', methods=['POST'])
@authenticate
@ip_whitelist_required
def manage_service_route(service_name, action):
    return jsonify(manage_service(service_name, action))

@api.route('/services/<service_name>/logs', methods=['GET'])
@authenticate
@ip_whitelist_required
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
def get_service_unit_route(service_name):
    return jsonify(get_service_unit_file(service_name))

@api.route('/services/<service_name>/dependencies', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_service_dependencies_route(service_name):
    reverse = request.args.get('reverse', 'false').lower() == 'true'
    return jsonify(get_service_dependencies(service_name, reverse=reverse))

# 日志管理路由
@api.route('/logs', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_logs_route():
    return jsonify(get_logs())

@api.route('/logs/read', methods=['POST'])
@authenticate
@ip_whitelist_required
def read_logs_route():
    return jsonify(read_log_file(request.json.get('file_path'), request.json.get('lines', 100), request.json.get('offset', 0)))

@api.route('/logs/search', methods=['POST'])
@authenticate
@ip_whitelist_required
def search_logs_route():
    return jsonify(search_logs(request.json))

# 增强的日志读取路由（支持筛选）
@api.route('/logs/read/filtered', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_config_route():
    return jsonify(get_system_config())

@api.route('/config', methods=['PUT'])
@authenticate
@ip_whitelist_required
def update_config_route():
    return jsonify(update_system_config(request.json))

# 用户管理路由
@api.route('/users', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_users_route():
    from modules.user_manager import get_all_users
    return jsonify(get_all_users())

@api.route('/users', methods=['POST'])
@authenticate
@ip_whitelist_required
def add_user_route():
    from modules.user_manager import add_user
    data = request.json
    return jsonify(add_user(data.get('username'), data.get('password'), data.get('role', 'user')))

@api.route('/users/<username>/password', methods=['PUT'])
@authenticate
@ip_whitelist_required
def update_user_password_route(username):
    from modules.user_manager import update_user_password
    data = request.json
    return jsonify(update_user_password(username, data.get('new_password')))

@api.route('/users/<username>/role', methods=['PUT'])
@authenticate
@ip_whitelist_required
def update_user_role_route(username):
    from modules.user_manager import update_user_role
    data = request.json
    return jsonify(update_user_role(username, data.get('new_role')))

@api.route('/users/<username>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
def delete_user_route(username):
    from modules.user_manager import delete_user
    return jsonify(delete_user(username))

# 修改密码路由
@api.route('/users/password', methods=['PUT'])
@authenticate
@ip_whitelist_required
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
def get_whitelist_dirs_route():
    """获取白名单目录列表"""
    return jsonify({'status': 'success', 'dirs': get_whitelist_dirs()})

# 浏览目录内容
@api.route('/file-manager/directory', methods=['GET'])
@authenticate
@ip_whitelist_required
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
def read_file_route():
    """读取文件内容"""
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'status': 'error', 'message': '缺少文件路径参数'}), 400
    
    result = read_file(file_path)
    if result['status'] == 'error':
        return jsonify(result), 400
    return jsonify(result)

# 写入文件内容（在线编辑）
@api.route('/file-manager/file/write', methods=['PUT'])
@authenticate
@ip_whitelist_required
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

# -------------------- 站点管理API --------------------

# 获取站点列表
@api.route('/sites', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_sites_route():
    """获取站点列表"""
    # 获取查询参数
    keyword = request.args.get('keyword')
    status = request.args.get('status')
    web_server = request.args.get('web_server')
    php_version = request.args.get('php_version')
    
    # 基础站点列表
    sites = site_manager.get_sites()
    
    # 搜索功能
    if keyword:
        sites = [site for site in sites if 
                 keyword.lower() in site['name'].lower() or 
                 keyword.lower() in site['root_dir'].lower() or 
                 keyword.lower() in site['notes'].lower()]
    
    # 筛选功能
    if status:
        sites = [site for site in sites if site['status'] == status]
    
    if web_server:
        sites = [site for site in sites if site['web_server'] == web_server]
    
    if php_version:
        sites = [site for site in sites if site['php_version'] == php_version]
    
    return jsonify({'status': 'success', 'sites': sites})

# 获取单个站点详情
@api.route('/sites/<site_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_site_route(site_id):
    """获取单个站点详情"""
    site = site_manager.get_site(site_id)
    if not site:
        return jsonify({'status': 'error', 'message': 'Site not found'}), 404
    return jsonify({'status': 'success', 'site': site})

# 添加站点
@api.route('/sites', methods=['POST'])
@authenticate
@ip_whitelist_required
def add_site_route():
    """添加新站点"""
    data = request.json
    return jsonify(site_manager.add_site(data))

# 更新站点信息
@api.route('/sites/<site_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
def update_site_route(site_id):
    """更新站点信息"""
    data = request.json
    return jsonify(site_manager.update_site(site_id, data))

# 删除站点
@api.route('/sites/<site_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
def delete_site_route(site_id):
    """删除站点"""
    return jsonify(site_manager.delete_site(site_id))

# 批量删除站点
@api.route('/sites/batch/delete', methods=['POST'])
@authenticate
@ip_whitelist_required
def batch_delete_sites_route():
    """批量删除站点"""
    data = request.json
    site_ids = data.get('site_ids', [])
    if not site_ids:
        return jsonify({'status': 'error', 'message': 'No site IDs provided'}), 400
    return jsonify(site_manager.batch_delete_sites(site_ids))

# 更新站点状态
@api.route('/sites/<site_id>/status', methods=['PUT'])
@authenticate
@ip_whitelist_required
def update_site_status_route(site_id):
    """更新站点状态"""
    data = request.json
    status = data.get('status')
    if not status:
        return jsonify({'status': 'error', 'message': 'Status is required'}), 400
    return jsonify(site_manager.update_site_status(site_id, status))

# -------------------- 域名绑定API --------------------

# 获取所有域名
@api.route('/domains', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_domains_route():
    """获取所有域名"""
    return jsonify({'status': 'success', 'domains': site_manager.get_domains()})

# 获取站点域名
@api.route('/sites/<site_id>/domains', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_site_domains_route(site_id):
    """获取站点域名"""
    return jsonify({'status': 'success', 'domains': site_manager.get_site_domains(site_id)})

# 添加域名绑定
@api.route('/domains', methods=['POST'])
@authenticate
@ip_whitelist_required
def add_domain_route():
    """添加域名绑定"""
    data = request.json
    return jsonify(site_manager.add_domain(data))

# 更新域名信息
@api.route('/domains/<domain_id>', methods=['PUT'])
@authenticate
@ip_whitelist_required
def update_domain_route(domain_id):
    """更新域名信息"""
    data = request.json
    return jsonify(site_manager.update_domain(domain_id, data))

# 删除域名绑定
@api.route('/domains/<domain_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
def delete_domain_route(domain_id):
    """删除域名绑定"""
    return jsonify(site_manager.delete_domain(domain_id))

# 批量删除域名
@api.route('/domains/batch/delete', methods=['POST'])
@authenticate
@ip_whitelist_required
def batch_delete_domains_route():
    """批量删除域名"""
    data = request.json
    domain_ids = data.get('domain_ids', [])
    if not domain_ids:
        return jsonify({'status': 'error', 'message': 'No domain IDs provided'}), 400
    return jsonify(site_manager.batch_delete_domains(domain_ids))

# 检查域名状态
@api.route('/domains/<domain_id>/check', methods=['POST'])
@authenticate
@ip_whitelist_required
def check_domain_status_route(domain_id):
    """检查域名状态"""
    return jsonify(site_manager.check_domain_status(domain_id))

# -------------------- Web服务管理API --------------------

# 重载Web服务
@api.route('/web-service/reload', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_db_configs_route():
    """获取数据库配置列表"""
    log_operation(request.user['username'], 'get_db_configs', request.remote_addr, 'Retrieved database configurations')
    return jsonify(db_manager.get_db_configs())

# -------------------- 数据库用户权限管理API --------------------

# 获取数据库用户列表
@api.route('/databases/configs/<config_id>/users', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_db_users_route(config_id):
    """获取数据库用户列表"""
    return jsonify(db_manager.get_users(config_id))

# 创建数据库用户
@api.route('/databases/configs/<config_id>/users', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def delete_db_user_route(config_id, username):
    """删除数据库用户"""
    return jsonify(db_manager.delete_user(config_id, username))

# 授予用户权限
@api.route('/databases/configs/<config_id>/users/<username>/permissions', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_db_config_route(config_id):
    """获取单个数据库配置"""
    log_operation(request.user['username'], 'get_db_config', request.remote_addr, f'Retrieved database configuration {config_id}')
    return jsonify(db_manager.get_db_config(config_id))

# 添加数据库配置
@api.route('/databases/configs', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def delete_db_config_route(config_id):
    """删除数据库配置"""
    result = db_manager.delete_db_config(config_id)
    log_operation(request.user['username'], 'delete_db_config', request.remote_addr, f'Deleted database configuration {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 测试数据库连接
@api.route('/databases/configs/<config_id>/test', methods=['POST'])
@authenticate
@ip_whitelist_required
def test_db_connection_route(config_id):
    """测试数据库连接"""
    result = db_manager.test_connection(config_id)
    log_operation(request.user['username'], 'test_db_connection', request.remote_addr, f'Tested connection for database configuration {config_id}', level='INFO' if result['status'] == 'success' else 'ERROR')
    return jsonify(result)

# 获取数据库列表
@api.route('/databases/configs/<config_id>/databases', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_databases_route(config_id):
    """获取数据库列表"""
    return jsonify(db_manager.get_databases(config_id))

# 获取数据库表列表
@api.route('/databases/configs/<config_id>/databases/<db_name>/tables', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_tables_route(config_id, db_name):
    """获取数据库表列表"""
    return jsonify(db_manager.get_tables(config_id, db_name))

# 执行SQL查询
@api.route('/databases/configs/<config_id>/query', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_backup_configs_route():
    """获取备份配置列表"""
    from modules.db_manager import backup_manager
    log_operation(request.user['username'], 'get_backup_configs', request.remote_addr, 'Retrieved backup configurations')
    return jsonify(backup_manager.get_backup_configs())

# 获取单个备份配置
@api.route('/databases/backups/configs/<config_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_backup_config_route(config_id):
    """获取单个备份配置"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.get_backup_config(config_id))

# 添加备份配置
@api.route('/databases/backups/configs', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def update_backup_config_route(config_id):
    """更新备份配置"""
    from modules.db_manager import backup_manager
    data = request.json
    return jsonify(backup_manager.update_backup_config(config_id, data))

# 删除备份配置
@api.route('/databases/backups/configs/<config_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
def delete_backup_config_route(config_id):
    """删除备份配置"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.delete_backup_config(config_id))

# 触发手动备份
@api.route('/databases/backups/configs/<config_id>/trigger', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_backup_info_route(backup_id):
    """获取备份详情"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.get_backup_info(backup_id))

# 验证备份完整性
@api.route('/databases/backups/<backup_id>/verify', methods=['POST'])
@authenticate
@ip_whitelist_required
def verify_backup_route(backup_id):
    """验证备份完整性"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.verify_backup(backup_id))

# 恢复备份
@api.route('/databases/backups/<backup_id>/restore', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def delete_backup_route(backup_id):
    """删除备份"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.delete_backup(backup_id))

# 获取待执行的备份任务
@api.route('/databases/backups/scheduled', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_scheduled_backups_route():
    """获取待执行的备份任务"""
    from modules.db_manager import backup_manager
    return jsonify(backup_manager.get_scheduled_backups())


# -------------------- 数据库监控API --------------------

# 获取监控配置列表
@api.route('/databases/monitor/configs', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_monitor_configs_route():
    """获取监控配置列表"""
    from modules.db_manager import db_monitor
    log_operation(request.user['username'], 'get_monitor_configs', request.remote_addr, 'Retrieved monitoring configurations')
    return jsonify(db_monitor.get_monitor_configs())

# 获取单个监控配置
@api.route('/databases/monitor/configs/<config_id>', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_monitor_config_route(config_id):
    """获取单个监控配置"""
    from modules.db_manager import db_monitor
    return jsonify(db_monitor.get_monitor_config(config_id))

# 添加监控配置
@api.route('/databases/monitor/configs', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def update_monitor_config_route(config_id):
    """更新监控配置"""
    from modules.db_manager import db_monitor
    data = request.json
    return jsonify(db_monitor.update_monitor_config(config_id, data))

# 删除监控配置
@api.route('/databases/monitor/configs/<config_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
def delete_monitor_config_route(config_id):
    """删除监控配置"""
    from modules.db_manager import db_monitor
    return jsonify(db_monitor.delete_monitor_config(config_id))

# 开始监控
@api.route('/databases/monitor/configs/<config_id>/start', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_realtime_metrics_route():
    """获取实时系统指标"""
    from modules.system_monitor import metrics_collector
    return jsonify(metrics_collector.get_realtime_metrics())

@api.route('/monitor/network/traffic', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_network_traffic_route():
    """获取网络流量信息"""
    from modules.system_monitor import get_network_traffic
    return jsonify(get_network_traffic())

@api.route('/monitor/network/traffic/history', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_network_traffic_history_route():
    """获取网络流量历史"""
    from modules.system_monitor import get_network_traffic_history
    time_range = request.args.get('time_range', '1h')
    return jsonify(get_network_traffic_history(time_range))

@api.route('/monitor/disk-io', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_disk_io_route():
    """获取磁盘IO信息"""
    from modules.system_monitor import get_disk_io
    return jsonify(get_disk_io())

@api.route('/monitor/disk-io/history', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_disk_io_history_route():
    """获取磁盘IO历史"""
    from modules.system_monitor import get_disk_io_history
    time_range = request.args.get('time_range', '1h')
    return jsonify(get_disk_io_history(time_range))

@api.route('/monitor/history/<metric_type>', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_historical_metrics_route(metric_type):
    """获取历史指标数据"""
    from modules.system_monitor import metrics_collector
    time_range = request.args.get('time_range', '1h')
    granularity = request.args.get('granularity', 'minute')
    return jsonify(metrics_collector.get_historical_metrics(metric_type, time_range, granularity))

@api.route('/monitor/top-processes', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_top_processes_route():
    """获取资源占用最高的进程"""
    from modules.system_monitor import get_top_processes
    sort_by = request.args.get('sort_by', 'cpu')
    limit = int(request.args.get('limit', 10))
    return jsonify(get_top_processes(sort_by, limit))

@api.route('/monitor/process/<int:pid>/detail', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_process_detail_monitor_route(pid):
    """获取进程详细信息"""
    from modules.system_monitor import get_process_detail
    return jsonify(get_process_detail(pid))

@api.route('/monitor/export', methods=['POST'])
@authenticate
@ip_whitelist_required
def export_metrics_route():
    """导出指标数据"""
    from modules.system_monitor import export_metrics_data
    data = request.json
    return jsonify(export_metrics_data(
        metric_types=data.get('metric_types', []),
        time_range=data.get('time_range', '24h'),
        format=data.get('format', 'json')
    ))


# -------------------- Widget布局API --------------------

@api.route('/dashboard/widgets/layout', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_widget_layout_route():
    """获取用户Widget布局"""
    from modules.system_monitor import get_widget_layout
    username = request.user['username']
    return jsonify(get_widget_layout(username))

@api.route('/dashboard/widgets/layout', methods=['POST'])
@authenticate
@ip_whitelist_required
def save_widget_layout_route():
    """保存用户Widget布局"""
    from modules.system_monitor import save_widget_layout
    username = request.user['username']
    layout = request.json
    return jsonify(save_widget_layout(username, layout))

@api.route('/dashboard/widgets/default', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_default_widget_layout_route():
    """获取默认Widget布局"""
    from modules.system_monitor import get_default_layout
    return jsonify(get_default_layout())


# -------------------- 终端模拟器API --------------------

@api.route('/terminal/shells', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_available_shells_route():
    """获取可用的Shell列表"""
    from modules.terminal_manager import get_available_shells
    return jsonify(get_available_shells())

@api.route('/terminal/history', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_command_history_route():
    """获取命令历史"""
    from modules.terminal_manager import get_command_history
    username = request.user['username']
    limit = int(request.args.get('limit', 100))
    return jsonify(get_command_history(username, limit))

@api.route('/terminal/history/search', methods=['GET'])
@authenticate
@ip_whitelist_required
def search_command_history_route():
    """搜索命令历史"""
    from modules.terminal_manager import search_command_history
    username = request.user['username']
    query = request.args.get('query', '')
    return jsonify(search_command_history(username, query))

@api.route('/terminal/suggestions', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_command_suggestions_route():
    """获取命令建议"""
    from modules.terminal_manager import get_command_suggestions
    username = request.user['username']
    partial = request.args.get('partial', '')
    return jsonify(get_command_suggestions(username, partial))

@api.route('/terminal/history/clear', methods=['POST'])
@authenticate
@ip_whitelist_required
def clear_command_history_route():
    """清空命令历史"""
    from modules.terminal_manager import clear_command_history
    username = request.user['username']
    return jsonify(clear_command_history(username))


# -------------------- 代码编辑器API --------------------

@api.route('/editor/languages', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_editor_languages_route():
    """获取支持的语言列表"""
    from modules.code_editor import get_all_languages
    return jsonify(get_all_languages())

@api.route('/editor/language/<filename>', methods=['GET'])
@authenticate
@ip_whitelist_required
def detect_language_route(filename):
    """检测文件语言"""
    from modules.code_editor import get_language_from_extension
    return jsonify({'language': get_language_from_extension(filename)})

@api.route('/editor/tokenize', methods=['POST'])
@authenticate
@ip_whitelist_required
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
def get_editor_settings_route():
    """获取编辑器设置"""
    from modules.code_editor import get_editor_settings
    username = request.user['username']
    return jsonify(get_editor_settings(username))

@api.route('/editor/settings', methods=['POST'])
@authenticate
@ip_whitelist_required
def save_editor_settings_route():
    """保存编辑器设置"""
    from modules.code_editor import save_editor_settings
    username = request.user['username']
    settings = request.json
    return jsonify(save_editor_settings(username, settings))

@api.route('/editor/sessions', methods=['GET'])
@authenticate
@ip_whitelist_required
def get_file_sessions_route():
    """获取文件会话"""
    from modules.code_editor import get_file_sessions
    username = request.user['username']
    return jsonify(get_file_sessions(username))

@api.route('/editor/sessions', methods=['POST'])
@authenticate
@ip_whitelist_required
def save_file_session_route():
    """保存文件会话"""
    from modules.code_editor import save_file_session
    username = request.user['username']
    session_data = request.json
    return jsonify(save_file_session(username, session_data))

@api.route('/editor/sessions/<path:file_path>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
def close_file_session_route(file_path):
    """关闭文件会话"""
    from modules.code_editor import close_file_session
    username = request.user['username']
    return jsonify(close_file_session(username, file_path))

@api.route('/editor/outline', methods=['POST'])
@authenticate
@ip_whitelist_required
def get_file_outline_route():
    """获取文件大纲"""
    from modules.code_editor import get_file_outline, get_language_from_extension
    data = request.json
    content = data.get('content', '')
    filename = data.get('filename', '')
    language = data.get('language') or get_language_from_extension(filename)
    return jsonify(get_file_outline(content, language))


