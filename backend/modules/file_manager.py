import os
import stat
import time
import shutil
import json
import hashlib
import zipfile
import tarfile
import threading
import difflib
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

# 文件读取大小限制 (10MB)
MAX_FILE_READ_SIZE = 10 * 1024 * 1024

# 搜索结果最大数量
MAX_SEARCH_RESULTS = 200

# 搜索最大深度
MAX_SEARCH_DEPTH = 10

# 压缩操作单文件大小上限 (512MB)，防止资源耗尽
ARCHIVE_MAX_SIZE = 512 * 1024 * 1024

# 允许的压缩包类型
ALLOWED_ARCHIVE_TYPES = {'zip', 'tar', 'gz', 'tgz', 'bz2'}

# 文件锁：按规范化路径加锁，防止同一文件的并发写入冲突
_file_locks = {}
_file_locks_guard = threading.Lock()


def _get_file_lock(file_path):
    """获取指定文件路径对应的锁（线程安全）"""
    key = os.path.normpath(os.path.abspath(file_path))
    with _file_locks_guard:
        lock = _file_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _file_locks[key] = lock
        return lock


def _resolve_real_path(path):
    """规范化并解析真实绝对路径（解析符号链接与 ..）"""
    return os.path.realpath(os.path.normpath(os.path.abspath(path)))


def is_path_in_whitelist(path):
    """
    验证路径是否在白名单中（安全实现）。
    - 使用 realpath 解析符号链接，防止通过软链接逃逸出白名单
    - 使用 commonpath 做边界匹配，避免 /var/www2 误匹配 /var/www 这类前缀漏洞
    """
    try:
        normalized_path = _resolve_real_path(path)
        for whitelist_dir in config_instance.FILE_MANAGER_WHITELIST_DIRS:
            whitelist_path = _resolve_real_path(whitelist_dir['path'])
            try:
                common = os.path.commonpath([normalized_path, whitelist_path])
            except ValueError:
                # 跨驱动器等无法比较的情况
                continue
            if common == whitelist_path:
                return True
        return False
    except Exception:
        return False


def get_whitelist_dirs():
    """获取白名单目录列表"""
    return config_instance.FILE_MANAGER_WHITELIST_DIRS


def _permission_detail(stat_info):
    """从 stat 信息提取权限详情与权限字符串（DRY：消除重复逻辑）"""
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
    perm_str = (
        f"{'r' if permissions['user']['read'] else '-'}{'w' if permissions['user']['write'] else '-'}{'x' if permissions['user']['execute'] else '-'}"
        f"{'r' if permissions['group']['read'] else '-'}{'w' if permissions['group']['write'] else '-'}{'x' if permissions['group']['execute'] else '-'}"
        f"{'r' if permissions['other']['read'] else '-'}{'w' if permissions['other']['write'] else '-'}{'x' if permissions['other']['execute'] else '-'}"
    )
    return permissions, perm_str


def get_file_info(file_path):
    """获取文件详细信息"""
    try:
        stat_info = os.stat(file_path)
        is_dir = os.path.isdir(file_path)
        permissions, perm_str = _permission_detail(stat_info)

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

    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception:
        # 日志失败不应影响主流程，但记录到 stderr 便于排查
        import sys
        print(f"[file_manager] 写入操作日志失败: {log_file}", file=sys.stderr)


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
        with _get_file_lock(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        save_file_operation_log('create', file_path, username, True)
        return {'status': 'success', 'message': '文件创建成功'}
    except Exception as e:
        save_file_operation_log('create', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def create_directory(file_path, username=''):
    """创建目录（支持递归创建）"""
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('mkdir', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    try:
        os.makedirs(file_path, exist_ok=True)
        save_file_operation_log('mkdir', file_path, username, True)
        return {'status': 'success', 'message': '目录创建成功'}
    except Exception as e:
        save_file_operation_log('mkdir', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def delete_file(file_path, username=''):
    """删除文件"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('delete', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    try:
        with _get_file_lock(file_path):
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)

        save_file_operation_log('delete', file_path, username, True)
        return {'status': 'success', 'message': '文件删除成功'}
    except Exception as e:
        save_file_operation_log('delete', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def batch_delete(paths, username=''):
    """批量删除文件/目录"""
    if not isinstance(paths, list) or not paths:
        return {'status': 'error', 'message': '缺少文件路径列表'}

    results = []
    success_count = 0
    for p in paths:
        result = delete_file(p, username)
        ok = result.get('status') == 'success'
        if ok:
            success_count += 1
        results.append({'path': p, 'status': result.get('status'), 'message': result.get('message')})

    save_file_operation_log('batch_delete', '; '.join(paths), username,
                           success=(success_count == len(paths)),
                           details={'total': len(paths), 'success': success_count})
    return {
        'status': 'success' if success_count == len(paths) else 'partial' if success_count else 'error',
        'message': f'批量删除完成：成功 {success_count}/{len(paths)}',
        'results': results
    }


def read_file(file_path, username=''):
    """读取文件内容"""
    # 验证路径是否在白名单中
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('read', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    try:
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_READ_SIZE:
            save_file_operation_log('read', file_path, username, False,
                                    {'error': '文件过大', 'size': file_size})
            return {
                'status': 'error',
                'message': f'文件过大 ({file_size} 字节)，超过限制 ({MAX_FILE_READ_SIZE} 字节)'
            }

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        save_file_operation_log('read', file_path, username, True)
        return {'status': 'success', 'content': content}
    except Exception as e:
        save_file_operation_log('read', file_path, username, False, {'error': str(e)})
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
        with _get_file_lock(file_path):
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


def rename_file(file_path, new_name, username=''):
    """重命名文件/目录（new_name 仅文件名，不含路径）"""
    if not is_path_in_whitelist(file_path):
        save_file_operation_log('rename', file_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    # 防止 new_name 包含路径分隔符导致越权移动
    if os.path.sep in new_name or '/' in new_name or '\\' in new_name:
        save_file_operation_log('rename', file_path, username, False, {'error': '非法的新文件名'})
        return {'status': 'error', 'message': '新文件名不能包含路径分隔符'}

    new_path = os.path.join(os.path.dirname(file_path), new_name)
    if not is_path_in_whitelist(new_path):
        save_file_operation_log('rename', file_path, username, False, {'error': '目标路径未授权'})
        return {'status': 'error', 'message': '目标路径未授权'}

    try:
        with _get_file_lock(file_path):
            os.rename(file_path, new_path)
        save_file_operation_log('rename', file_path, username, True, {'new_path': new_path})
        return {'status': 'success', 'message': '重命名成功', 'new_path': new_path}
    except Exception as e:
        save_file_operation_log('rename', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def move_file(src_path, dst_dir, username=''):
    """移动文件/目录到目标目录"""
    if not is_path_in_whitelist(src_path) or not is_path_in_whitelist(dst_dir):
        save_file_operation_log('move', src_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    if not os.path.isdir(dst_dir):
        return {'status': 'error', 'message': '目标路径不是目录'}

    dst_path = os.path.join(dst_dir, os.path.basename(src_path))
    if not is_path_in_whitelist(dst_path):
        save_file_operation_log('move', src_path, username, False, {'error': '目标路径未授权'})
        return {'status': 'error', 'message': '目标路径未授权'}

    if os.path.exists(dst_path):
        return {'status': 'error', 'message': '目标路径已存在同名文件'}

    try:
        with _get_file_lock(src_path):
            shutil.move(src_path, dst_path)
        save_file_operation_log('move', src_path, username, True, {'dst_path': dst_path})
        return {'status': 'success', 'message': '移动成功', 'new_path': dst_path}
    except Exception as e:
        save_file_operation_log('move', src_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def copy_file(src_path, dst_dir, username=''):
    """复制文件/目录到目标目录"""
    if not is_path_in_whitelist(src_path) or not is_path_in_whitelist(dst_dir):
        save_file_operation_log('copy', src_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    if not os.path.isdir(dst_dir):
        return {'status': 'error', 'message': '目标路径不是目录'}

    dst_path = os.path.join(dst_dir, os.path.basename(src_path))
    if not is_path_in_whitelist(dst_path):
        save_file_operation_log('copy', src_path, username, False, {'error': '目标路径未授权'})
        return {'status': 'error', 'message': '目标路径未授权'}

    if os.path.exists(dst_path):
        return {'status': 'error', 'message': '目标路径已存在同名文件'}

    try:
        with _get_file_lock(src_path):
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
        save_file_operation_log('copy', src_path, username, True, {'dst_path': dst_path})
        return {'status': 'success', 'message': '复制成功', 'new_path': dst_path}
    except Exception as e:
        save_file_operation_log('copy', src_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def get_directory_size(path):
    """递归计算目录大小"""
    if not is_path_in_whitelist(path):
        return {'status': 'error', 'message': '访问未授权路径'}

    try:
        total = 0
        file_count = 0
        dir_count = 0
        for root, dirs, files in os.walk(path):
            dir_count += len(dirs)
            for name in files:
                fp = os.path.join(root, name)
                try:
                    total += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    continue
        return {
            'status': 'success',
            'path': path,
            'size': total,
            'file_count': file_count,
            'dir_count': dir_count
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_file_hash(file_path, algorithm='sha256'):
    """计算文件校验和（支持 md5/sha1/sha256）"""
    if not is_path_in_whitelist(file_path):
        return {'status': 'error', 'message': '访问未授权路径'}

    algorithm = (algorithm or 'sha256').lower()
    if algorithm not in ('md5', 'sha1', 'sha256'):
        return {'status': 'error', 'message': '不支持的哈希算法'}

    try:
        h = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return {
            'status': 'success',
            'file_path': file_path,
            'algorithm': algorithm,
            'hash': h.hexdigest()
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def search_files(path, query, max_results=MAX_SEARCH_RESULTS, max_depth=MAX_SEARCH_DEPTH):
    """
    在指定目录下递归搜索文件/目录名。
    - 限制最大结果数与递归深度，防止资源耗尽
    - 仅在白名单内搜索
    """
    if not is_path_in_whitelist(path):
        return {'status': 'error', 'message': '访问未授权路径'}

    if not query or not query.strip():
        return {'status': 'error', 'message': '搜索关键字不能为空'}

    query_lower = query.lower().strip()
    results = []

    def _walk(current_path, depth):
        if depth > max_depth or len(results) >= max_results:
            return
        try:
            entries = os.listdir(current_path)
        except OSError:
            return
        for entry in entries:
            if len(results) >= max_results:
                return
            entry_path = os.path.join(current_path, entry)
            # 二次校验白名单（防止符号链接逃逸）
            if not is_path_in_whitelist(entry_path):
                continue
            if query_lower in entry.lower():
                info = get_file_info(entry_path)
                if 'error' not in info:
                    results.append({
                        'name': info['name'],
                        'path': info['path'],
                        'is_dir': info['is_dir'],
                        'size': info['size'],
                        'modified_at': info['modified_at']
                    })
            # 递归进入子目录
            try:
                if os.path.isdir(entry_path) and not os.path.islink(entry_path):
                    _walk(entry_path, depth + 1)
            except OSError:
                continue

    try:
        _walk(path, 0)
        return {
            'status': 'success',
            'path': path,
            'query': query,
            'total': len(results),
            'truncated': len(results) >= max_results,
            'results': results
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def _safe_archive_path(base_dir, member):
    """防止压缩包内路径穿越（Zip Slip / Tar Slip）"""
    member_path = os.path.normpath(os.path.join(base_dir, member))
    base = os.path.normpath(base_dir)
    if os.path.commonpath([member_path, base]) != base:
        return None
    return member_path


def create_archive(src_paths, archive_path, username=''):
    """将多个文件/目录打包为压缩包"""
    if not isinstance(src_paths, list) or not src_paths:
        return {'status': 'error', 'message': '缺少源路径列表'}

    # 校验所有源路径与目标路径均在白名单
    for p in src_paths:
        if not is_path_in_whitelist(p):
            save_file_operation_log('archive_create', archive_path, username, False, {'error': '访问未授权路径'})
            return {'status': 'error', 'message': '访问未授权路径'}

    if not is_path_in_whitelist(archive_path):
        save_file_operation_log('archive_create', archive_path, username, False, {'error': '目标路径未授权'})
        return {'status': 'error', 'message': '目标路径未授权'}

    ext = os.path.splitext(archive_path)[1].lower()[1:]
    if ext not in ALLOWED_ARCHIVE_TYPES:
        return {'status': 'error', 'message': f'不支持的压缩格式，允许: {", ".join(sorted(ALLOWED_ARCHIVE_TYPES))}'}

    # 校验源大小，防止资源耗尽
    total_size = 0
    for p in src_paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for name in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        continue
        else:
            try:
                total_size += os.path.getsize(p)
            except OSError:
                continue
        if total_size > ARCHIVE_MAX_SIZE:
            return {'status': 'error', 'message': f'待压缩内容过大，超过限制 ({ARCHIVE_MAX_SIZE // 1024 // 1024}MB)'}

    try:
        with _get_file_lock(archive_path):
            if ext == 'zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for src in src_paths:
                        if os.path.isdir(src):
                            for root, _, files in os.walk(src):
                                for name in files:
                                    full = os.path.join(root, name)
                                    arc = os.path.relpath(full, os.path.dirname(src))
                                    zf.write(full, arc)
                        else:
                            zf.write(src, os.path.basename(src))
            else:
                # tar / gz / bz2 / tgz 统一交由 tarfile 处理
                mode = 'w'
                if ext == 'gz' or ext == 'tgz':
                    mode = 'w:gz'
                elif ext == 'bz2':
                    mode = 'w:bz2'
                with tarfile.open(archive_path, mode) as tf:
                    for src in src_paths:
                        tf.add(src, arcname=os.path.basename(src))

        save_file_operation_log('archive_create', archive_path, username, True,
                                {'sources': src_paths, 'size': total_size})
        return {'status': 'success', 'message': '压缩成功', 'archive_path': archive_path}
    except Exception as e:
        save_file_operation_log('archive_create', archive_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def extract_archive(archive_path, target_dir, username=''):
    """解压压缩包到目标目录"""
    if not is_path_in_whitelist(archive_path) or not is_path_in_whitelist(target_dir):
        save_file_operation_log('archive_extract', archive_path, username, False, {'error': '访问未授权路径'})
        return {'status': 'error', 'message': '访问未授权路径'}

    ext = os.path.splitext(archive_path)[1].lower()[1:]
    if ext not in ALLOWED_ARCHIVE_TYPES:
        return {'status': 'error', 'message': f'不支持的压缩格式，允许: {", ".join(sorted(ALLOWED_ARCHIVE_TYPES))}'}

    os.makedirs(target_dir, exist_ok=True)

    try:
        if ext == 'zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for member in zf.namelist():
                    # 防止 Zip Slip
                    if _safe_archive_path(target_dir, member) is None:
                        continue
                zf.extractall(target_dir)
        else:
            mode = 'r'
            if ext == 'gz' or ext == 'tgz':
                mode = 'r:gz'
            elif ext == 'bz2':
                mode = 'r:bz2'
            with tarfile.open(archive_path, mode) as tf:
                for member in tf.getmembers():
                    # 防止 Tar Slip
                    if _safe_archive_path(target_dir, member.name) is None:
                        continue
                tf.extractall(target_dir)

        save_file_operation_log('archive_extract', archive_path, username, True, {'target': target_dir})
        return {'status': 'success', 'message': '解压成功', 'target_dir': target_dir}
    except Exception as e:
        save_file_operation_log('archive_extract', archive_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


def save_file_version(file_path, username=''):
    """
    保存文件版本。
    - 失败时记录日志而非静默吞掉异常
    - 返回 (success: bool, error: str|None)
    """
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

        return True, None
    except Exception as e:
        save_file_operation_log('save_version', file_path, username, False, {'error': str(e)})
        return False, str(e)


def get_file_versions(file_path):
    """
    获取文件版本列表。
    - 失败时记录日志而非静默返回空列表
    """
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
        save_file_operation_log('get_versions', file_path, '', False, {'error': str(e)})
        return []


def get_file_version_diff(file_path, version_num, username=''):
    """对比当前文件内容与指定版本内容的差异（unified diff）"""
    if not is_path_in_whitelist(file_path):
        return {'status': 'error', 'message': '访问未授权路径'}

    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        rel_path = os.path.relpath(file_path, base_dir)
        file_version_dir = os.path.join(version_dir, rel_path)
        version_file = os.path.join(file_version_dir, f"{version_num}.bak")

        if not os.path.exists(version_file):
            return {'status': 'error', 'message': '版本不存在'}

        # 读取版本内容
        with open(version_file, 'r', encoding='utf-8', errors='replace') as f:
            old_lines = f.readlines()

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                new_lines = f.readlines()
        else:
            new_lines = []

        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f'version:{version_num}',
            tofile='current',
            lineterm=''
        ))

        save_file_operation_log('version_diff', file_path, username, True, {'version': version_num})
        return {
            'status': 'success',
            'file_path': file_path,
            'version': version_num,
            'diff': '\n'.join(diff)
        }
    except Exception as e:
        save_file_operation_log('version_diff', file_path, username, False, {'error': str(e)})
        return {'status': 'error', 'message': str(e)}


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

        with _get_file_lock(file_path):
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
        permissions, perm_str = _permission_detail(stat_info)

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

        # 计算总分块数
        chunk_size = config_instance.FILE_MANAGER_UPLOAD_CHUNK_SIZE
        total_chunks = (total_size + chunk_size - 1) // chunk_size if chunk_size > 0 else 0

        # 生成唯一上传 ID
        upload_id = f"{int(time.time())}_{os.urandom(8).hex()}"

        # 保存上传信息（含已接收分块索引，支持断点续传）
        upload_info = {
            'upload_id': upload_id,
            'filename': filename,
            'total_size': total_size,
            'total_chunks': total_chunks,
            'chunk_size': chunk_size,
            'target_path': target_path,
            'received_size': 0,
            'received_chunks': [],
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
            'chunk_size': chunk_size,
            'total_chunks': total_chunks
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def upload_chunk(upload_id, chunk_index, chunk_data, username=''):
    """
    上传文件块（支持断点续传）。
    - 同一分块重复上传会覆盖旧分块，但 received_size 不会重复累加
    """
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

        # 断点续传：若该分块已存在，先扣除其旧大小
        is_reupload = chunk_index in upload_info['received_chunks']
        old_chunk_size = 0
        if is_reupload and os.path.exists(chunk_file):
            old_chunk_size = os.path.getsize(chunk_file)

        with open(chunk_file, 'wb') as f:
            f.write(chunk_data)

        # 更新已接收大小与分块索引
        chunk_size = os.path.getsize(chunk_file)
        upload_info['received_size'] = upload_info['received_size'] - old_chunk_size + chunk_size
        if not is_reupload:
            upload_info['received_chunks'].append(chunk_index)

        with open(upload_info_path, 'w', encoding='utf-8') as f:
            json.dump(upload_info, f, ensure_ascii=False, indent=2)

        progress = 0
        if upload_info['total_size'] > 0:
            progress = round(upload_info['received_size'] / upload_info['total_size'] * 100, 2)

        return {
            'status': 'success',
            'message': '文件块上传成功',
            'received_size': upload_info['received_size'],
            'total_size': upload_info['total_size'],
            'progress': min(progress, 100),
            'received_chunks': len(upload_info['received_chunks']),
            'total_chunks': upload_info.get('total_chunks', 0)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_upload_status(upload_id):
    """查询上传状态（用于断点续传判断缺失分块）"""
    try:
        upload_info_path = os.path.join(temp_dir, f"{upload_id}.json")
        if not os.path.exists(upload_info_path):
            return {'status': 'error', 'message': '上传ID不存在'}

        with open(upload_info_path, 'r', encoding='utf-8') as f:
            upload_info = json.load(f)

        total_chunks = upload_info.get('total_chunks', 0)
        received = set(upload_info.get('received_chunks', []))
        missing = [i for i in range(total_chunks) if i not in received]

        progress = 0
        if upload_info['total_size'] > 0:
            progress = round(upload_info['received_size'] / upload_info['total_size'] * 100, 2)

        return {
            'status': 'success',
            'upload_id': upload_id,
            'filename': upload_info['filename'],
            'received_size': upload_info['received_size'],
            'total_size': upload_info['total_size'],
            'progress': min(progress, 100),
            'total_chunks': total_chunks,
            'received_chunks': sorted(received),
            'missing_chunks': missing
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

        # 目标路径二次校验
        if not is_path_in_whitelist(target_file):
            return {'status': 'error', 'message': '目标路径未授权'}

        with _get_file_lock(target_file):
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
