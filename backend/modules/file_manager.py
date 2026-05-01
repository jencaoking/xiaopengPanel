import os
import stat
import time
import shutil
import json
from datetime import datetime
from config.config import config_instance

# 确保临时目录存在
temp_dir = os.path.join(config_instance.LOG_DIR, config_instance.FILE_MANAGER_UPLOAD_TEMP_DIR)
os.makedirs(temp_dir, exist_ok=True)

# 确保版本控制目录存在
version_dir = os.path.join(config_instance.LOG_DIR, 'file_versions')
os.makedirs(version_dir, exist_ok=True)

# 确保操作日志目录存在
operation_log_dir = os.path.join(config_instance.LOG_DIR, 'file_operations')
os.makedirs(operation_log_dir, exist_ok=True)


def is_path_in_whitelist(path):
    """验证路径是否在白名单中"""
    # 规范化路径
    normalized_path = os.path.normpath(path)
    
    # 检查是否在白名单目录中
    for whitelist_dir in config_instance.FILE_MANAGER_WHITELIST_DIRS:
        whitelist_path = os.path.normpath(whitelist_dir['path'])
        if normalized_path.startswith(whitelist_path):
            return True
    return False


def get_whitelist_dirs():
    """获取白名单目录列表"""
    return config_instance.FILE_MANAGER_WHITELIST_DIRS


def get_file_info(file_path):
    """获取文件详细信息"""
    try:
        stat_info = os.stat(file_path)
        is_dir = os.path.isdir(file_path)
        
        # 获取文件权限
        permissions = {
            'user': {
                'read': bool(stat_info.st_mode & stat.S_IRUSR),
                'write': bool(stat_info.st_mode & stat.S_IWUSR),
                'execute': bool(stat_info.st_mode & stat.S_IXUSR)
            },
            'group': {
                'read': bool(stat_info.st_mode & stat.S_IRGRP),
                'write': bool(stat_info.st_mode & stat.S_IWGRP),
                'execute': bool(stat_info.st_mode & stat.S_IXGRP)
            },
            'other': {
                'read': bool(stat_info.st_mode & stat.S_IROTH),
                'write': bool(stat_info.st_mode & stat.S_IWOTH),
                'execute': bool(stat_info.st_mode & stat.S_IXOTH)
            }
        }
        
        # 转换为权限字符串（如：rwxr-xr-x）
        perm_str = f"{'r' if permissions['user']['read'] else '-'}{'w' if permissions['user']['write'] else '-'}{'x' if permissions['user']['execute'] else '-'}"\
                  f"{'r' if permissions['group']['read'] else '-'}{'w' if permissions['group']['write'] else '-'}{'x' if permissions['group']['execute'] else '-'}"\
                  f"{'r' if permissions['other']['read'] else '-'}{'w' if permissions['other']['write'] else '-'}{'x' if permissions['other']['execute'] else '-'}"
        
        file_info = {
            'name': os.path.basename(file_path),
            'path': file_path,
            'is_dir': is_dir,
            'size': stat_info.st_size,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_ctime)),
            'modified_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_mtime)),
            'accessed_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_atime)),
            'permissions': perm_str,
            'permissions_detail': permissions,
            'owner': stat_info.st_uid,
            'group': stat_info.st_gid,
            'inode': stat_info.st_ino
        }
        
        return file_info
    except Exception as e:
        return {'error': str(e)}


def list_directory(path):
    """列出目录内容"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(path):
        return {'status': 'error', 'message': '访问未授权路径'}
    
    try:
        # 获取目录内容
        entries = os.listdir(path)
        files = []
        dirs = []
        
        for entry in entries:
            entry_path = os.path.join(path, entry)
            file_info = get_file_info(entry_path)
            if file_info.get('is_dir'):
                dirs.append(file_info)
            else:
                files.append(file_info)
        
        # 按名称排序
        dirs.sort(key=lambda x: x['name'])
        files.sort(key=lambda x: x['name'])
        
        return {
            'status': 'success',
            'path': path,
            'directories': dirs,
            'files': files
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def check_file_type(filename):
    """检查文件类型是否允许"""
    ext = os.path.splitext(filename)[1].lower()[1:]  # 去除点号
    return ext in config_instance.FILE_MANAGER_UPLOAD_ALLOWED_TYPES


def save_file_operation_log(action, file_path, username, success=True, details=None):
    """保存文件操作日志"""
    if not config_instance.FILE_MANAGER_OPERATIONS_LOG_ENABLED:
        return
    
    log_file = os.path.join(operation_log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'file_path': file_path,
        'username': username,
        'success': success,
        'details': details or {}
    }
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def create_file(file_path, content='', username=''):
    """创建文件"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('create', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}
    
    # 验证文件类型
    if not check_file_type(file_path):
        save_file_operation_log('create', file_path, username, False, {'error': '不允许的文件类型'})
        return {'status': 'error', 'message': '不允许的文件类型'}
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        save_file_operation_log('create', file_path, username, True)
        return {'status': 'success', 'message': '文件创建成功'}
    except Exception as e:
        save_file_operation_log('create', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def delete_file(file_path, username=''):
    """删除文件"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('delete', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}
    
    try:
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        
        save_file_operation_log('delete', file_path, username, True)
        return {'status': 'success', 'message': '文件删除成功'}
    except Exception as e:
        save_file_operation_log('delete', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def read_file(file_path):
    """读取文件内容"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        return {'status': 'error', 'message': '访问未授权路径'}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {'status': 'success', 'content': content}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def write_file(file_path, content, username=''):
    """写入文件内容，支持版本控制"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('write', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}
    
    # 验证文件类型
    ext = os.path.splitext(file_path)[1].lower()[1:]
    if ext not in config_instance.FILE_MANAGER_ONLINE_EDIT_ALLOWED_EXTENSIONS:
        save_file_operation_log('write', file_path, username, False, {'error': '不允许编辑的文件类型'})
        return {'status': 'error', 'message': '不允许编辑的文件类型'}
    
    try:
        # 如果启用版本控制，保存当前版本
        if config_instance.FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_ENABLED and os.path.exists(file_path):
            save_file_version(file_path, username)
        
        # 写入新内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        save_file_operation_log('write', file_path, username, True)
        return {'status': 'success', 'message': '文件写入成功'}
    except Exception as e:
        save_file_operation_log('write', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def save_file_version(file_path, username=''):
    """保存文件版本"""
    try:
        # 获取文件相对路径作为版本目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        rel_path = os.path.relpath(file_path, base_dir)
        file_version_dir = os.path.join(version_dir, rel_path)
        os.makedirs(file_version_dir, exist_ok=True)
        
        # 获取当前时间戳作为版本号
        timestamp = int(time.time())
        version_file = os.path.join(file_version_dir, f"{timestamp}.bak")
        
        # 复制文件到版本目录
        shutil.copy2(file_path, version_file)
        
        # 保存版本元数据
        version_meta = os.path.join(file_version_dir, f"{timestamp}.meta")
        with open(version_meta, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'username': username,
                'file_path': file_path,
                'created_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        # 清理旧版本，只保留最新的N个版本
        versions = sorted([f for f in os.listdir(file_version_dir) if f.endswith('.bak')],
                         key=lambda x: int(x.split('.')[0]), reverse=True)
        
        max_versions = config_instance.FILE_MANAGER_ONLINE_EDIT_VERSION_CONTROL_MAX_VERSIONS
        if len(versions) > max_versions:
            for old_version in versions[max_versions:]:
                old_version_bak = os.path.join(file_version_dir, old_version)
                old_version_meta = os.path.join(file_version_dir, f"{old_version.split('.')[0]}.meta")
                
                if os.path.exists(old_version_bak):
                    os.remove(old_version_bak)
                if os.path.exists(old_version_meta):
                    os.remove(old_version_meta)
        
        return True
    except Exception as e:
        return False


def get_file_versions(file_path):
    """获取文件版本列表"""
    try:
        # 获取文件相对路径作为版本目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        rel_path = os.path.relpath(file_path, base_dir)
        file_version_dir = os.path.join(version_dir, rel_path)
        
        if not os.path.exists(file_version_dir):
            return []
        
        versions = []
        # 获取所有版本文件
        for file in os.listdir(file_version_dir):
            if file.endswith('.meta'):
                meta_path = os.path.join(file_version_dir, file)
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                version_num = int(file.split('.')[0])
                versions.append({
                    'version': version_num,
                    'timestamp': meta['timestamp'],
                    'created_at': meta['created_at'],
                    'username': meta['username']
                })
        
        # 按版本号降序排序
        return sorted(versions, key=lambda x: x['version'], reverse=True)
    except Exception as e:
        return []


def restore_file_version(file_path, version_num, username=''):
    """恢复文件到指定版本"""
    try:
        # 验证路径是否在白名单中
        if not is_path_in_whitelist(file_path):
            save_file_operation_log('restore_version', file_path, username, False, {'error': '访问未授权路径'})
            return {'status': 'error', 'message': '访问未授权路径'}
        
        # 获取文件相对路径作为版本目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        rel_path = os.path.relpath(file_path, base_dir)
        file_version_dir = os.path.join(version_dir, rel_path)
        
        # 版本文件路径
        version_file = os.path.join(file_version_dir, f"{version_num}.bak")
        
        if not os.path.exists(version_file):
            save_file_operation_log('restore_version', file_path, username, False, {'error': '版本不存在'})
            return {'status': 'error', 'message': '版本不存在'}
        
        # 保存当前版本
        save_file_version(file_path, username)
        
        # 恢复指定版本
        shutil.copy2(version_file, file_path)
        
        save_file_operation_log('restore_version', file_path, username, True, {'version': version_num})
        return {'status': 'success', 'message': '文件版本恢复成功'}
    except Exception as e:
        save_file_operation_log('restore_version', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def get_file_permissions(file_path):
    """获取文件权限信息"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        return {'status': 'error', 'message': '访问未授权路径'}
    
    try:
        stat_info = os.stat(file_path)
        
        # 获取文件权限
        permissions = {
            'user': {
                'read': bool(stat_info.st_mode & stat.S_IRUSR),
                'write': bool(stat_info.st_mode & stat.S_IWUSR),
                'execute': bool(stat_info.st_mode & stat.S_IXUSR)
            },
            'group': {
                'read': bool(stat_info.st_mode & stat.S_IRGRP),
                'write': bool(stat_info.st_mode & stat.S_IWGRP),
                'execute': bool(stat_info.st_mode & stat.S_IXGRP)
            },
            'other': {
                'read': bool(stat_info.st_mode & stat.S_IROTH),
                'write': bool(stat_info.st_mode & stat.S_IWOTH),
                'execute': bool(stat_info.st_mode & stat.S_IXOTH)
            }
        }
        
        # 转换为权限字符串（如：rwxr-xr-x）
        perm_str = f"{'r' if permissions['user']['read'] else '-'}{'w' if permissions['user']['write'] else '-'}{'x' if permissions['user']['execute'] else '-'}"\
                  f"{'r' if permissions['group']['read'] else '-'}{'w' if permissions['group']['write'] else '-'}{'x' if permissions['group']['execute'] else '-'}"\
                  f"{'r' if permissions['other']['read'] else '-'}{'w' if permissions['other']['write'] else '-'}{'x' if permissions['other']['execute'] else '-'}"\
        
        return {
            'status': 'success',
            'file_path': file_path,
            'permissions': perm_str,
            'permissions_detail': permissions,
            'owner': stat_info.st_uid,
            'group': stat_info.st_gid,
            'inode': stat_info.st_ino
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def init_upload(file_info, username=''):
    """初始化文件上传"""
    try:
        filename = file_info.get('filename')
        total_size = file_info.get('total_size', 0)
        target_path = file_info.get('target_path')
        
        # 验证目标路径
        if not is_path_in_whitelist(target_path):
            return {'status': 'error', 'message': '访问未授权路径'}
        
        # 验证文件大小
        if total_size > config_instance.FILE_MANAGER_UPLOAD_MAX_SIZE:
            return {'status': 'error', 'message': f'文件大小超过限制（{config_instance.FILE_MANAGER_UPLOAD_MAX_SIZE / 1024 / 1024}MB）'}
        
        # 验证文件类型
        if not check_file_type(filename):
            return {'status': 'error', 'message': '不允许的文件类型'}
        
        # 生成唯一上传ID
        upload_id = f"{int(time.time())}_{os.urandom(8).hex()}"
        
        # 保存上传信息
        upload_info = {
            'upload_id': upload_id,
            'filename': filename,
            'total_size': total_size,
            'target_path': target_path,
            'received_size': 0,
            'created_at': datetime.now().isoformat(),
            'username': username
        }
        
        upload_info_path = os.path.join(temp_dir, f"{upload_id}.json")
        with open(upload_info_path, 'w', encoding='utf-8') as f:
            json.dump(upload_info, f, ensure_ascii=False, indent=2)
        
        return {
            'status': 'success',
            'upload_id': upload_id,
            'message': '上传初始化成功',
            'chunk_size': config_instance.FILE_MANAGER_UPLOAD_CHUNK_SIZE
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def upload_chunk(upload_id, chunk_index, chunk_data, username=''):
    """上传文件块"""
    try:
        # 获取上传信息
        upload_info_path = os.path.join(temp_dir, f"{upload_id}.json")
        if not os.path.exists(upload_info_path):
            return {'status': 'error', 'message': '上传ID不存在'}
        
        with open(upload_info_path, 'r', encoding='utf-8') as f:
            upload_info = json.load(f)
        
        # 保存文件块
        chunk_dir = os.path.join(temp_dir, upload_id)
        os.makedirs(chunk_dir, exist_ok=True)
        
        chunk_file = os.path.join(chunk_dir, f"chunk_{chunk_index}")
        with open(chunk_file, 'wb') as f:
            f.write(chunk_data)
        
        # 更新已接收大小
        chunk_size = os.path.getsize(chunk_file)
        upload_info['received_size'] += chunk_size
        
        with open(upload_info_path, 'w', encoding='utf-8') as f:
            json.dump(upload_info, f, ensure_ascii=False, indent=2)
        
        return {
            'status': 'success',
            'message': '文件块上传成功',
            'received_size': upload_info['received_size'],
            'total_size': upload_info['total_size']
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def complete_upload(upload_id, username=''):
    """完成文件上传，合并文件块"""
    try:
        # 获取上传信息
        upload_info_path = os.path.join(temp_dir, f"{upload_id}.json")
        if not os.path.exists(upload_info_path):
            return {'status': 'error', 'message': '上传ID不存在'}
        
        with open(upload_info_path, 'r', encoding='utf-8') as f:
            upload_info = json.load(f)
        
        # 验证是否接收完所有文件块
        if upload_info['received_size'] != upload_info['total_size']:
            return {'status': 'error', 'message': '文件块接收不完整'}
        
        # 合并文件块
        chunk_dir = os.path.join(temp_dir, upload_id)
        target_file = os.path.join(upload_info['target_path'], upload_info['filename'])
        
        with open(target_file, 'wb') as f:
            chunk_index = 0
            while True:
                chunk_file = os.path.join(chunk_dir, f"chunk_{chunk_index}")
                if not os.path.exists(chunk_file):
                    break
                
                with open(chunk_file, 'rb') as chunk:
                    f.write(chunk.read())
                
                chunk_index += 1
        
        # 清理临时文件
        shutil.rmtree(chunk_dir, ignore_errors=True)
        os.remove(upload_info_path)
        
        # 记录操作日志
        save_file_operation_log('upload', target_file, username, True)
        
        return {
            'status': 'success',
            'message': '文件上传成功',
            'file_path': target_file
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def cancel_upload(upload_id):
    """取消文件上传，清理临时文件"""
    try:
        # 获取上传信息
        upload_info_path = os.path.join(temp_dir, f"{upload_id}.json")
        if os.path.exists(upload_info_path):
            os.remove(upload_info_path)
        
        # 清理文件块
        chunk_dir = os.path.join(temp_dir, upload_id)
        if os.path.exists(chunk_dir):
            shutil.rmtree(chunk_dir, ignore_errors=True)
        
        return {'status': 'success', 'message': '上传已取消'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def download_file(file_path):
    """下载文件，返回文件路径和文件名"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        return {'status': 'error', 'message': '访问未授权路径'}
    
    try:
        if not os.path.exists(file_path):
            return {'status': 'error', 'message': '文件不存在'}
        
        return {
            'status': 'success',
            'file_path': file_path,
            'filename': os.path.basename(file_path)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
