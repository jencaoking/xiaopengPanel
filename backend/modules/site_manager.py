import os
import json
import uuid
import socket
import shutil
import subprocess
import platform
from datetime import datetime
from typing import Dict, List, Optional


class SiteManager:
    """站点管理器：管理 Web 站点、域名绑定、SSL 证书与 Web 服务器配置文件。

    升级要点：
    - 使用 UUID 作为站点/域名 ID，避免删除后 ID 冲突
    - 自动生成 Nginx/Apache 配置文件，启用/禁用站点时通过 systemctl 重载
    - 通过 socket.gethostbyname 进行域名 DNS 解析验证
    - 集成 certbot 申请/续期/撤销 Let's Encrypt 证书
    - 支持站点配置文件在线编辑（读取/保存/校验）
    - 关键操作记录到面板操作日志（log_operation）
    - 原子写入 JSON 文件，避免并发损坏
    - 跨平台：Linux 上执行真实命令，其他平台优雅降级并返回明确错误
    """

    # 允许的 Web 服务器类型
    SUPPORTED_WEB_SERVERS = ('nginx', 'apache')

    # 站点状态枚举
    VALID_STATUSES = ('running', 'stopped', 'error', 'pending')

    # 域名状态枚举
    VALID_DOMAIN_STATUSES = ('active', 'pending', 'error')

    # SSL 状态枚举
    VALID_SSL_STATUSES = ('disabled', 'pending', 'active', 'expired', 'error')

    def __init__(self, config):
        self.config = config
        self.sites_file = os.path.join(self.config.BASE_DIR, 'config', 'sites.json')
        self.domains_file = os.path.join(self.config.BASE_DIR, 'config', 'domains.json')
        # 站点配置文件目录（Nginx/Apache conf）
        self.sites_config_dir = os.path.join(self.config.BASE_DIR, 'config', 'web_servers')
        self.nginx_conf_dir = os.path.join(self.sites_config_dir, 'nginx')
        self.apache_conf_dir = os.path.join(self.sites_config_dir, 'apache')
        # 站点备份目录
        self.backup_dir = os.path.join(self.config.BASE_DIR, 'config', 'site_backups')
        # 证书存储目录
        self.ssl_cert_dir = os.path.join(self.config.BASE_DIR, 'config', 'ssl')

        # 确保目录存在
        for d in (self.sites_config_dir, self.nginx_conf_dir,
                  self.apache_conf_dir, self.backup_dir, self.ssl_cert_dir):
            os.makedirs(d, exist_ok=True)

        self._sites = self._load_sites()
        self._domains = self._load_domains()

    # -------------------- 通用工具 --------------------

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat()

    @staticmethod
    def _gen_id(prefix: str) -> str:
        """生成 12 位十六进制 ID，避免与现有数据冲突"""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _atomic_write_json(file_path: str, data) -> bool:
        """原子写入 JSON 文件，先写临时文件再重命名，避免写入期间损坏"""
        tmp_path = f"{file_path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            os.replace(tmp_path, file_path)
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return False

    @staticmethod
    def _is_linux() -> bool:
        return platform.system().lower() == 'linux'

    @staticmethod
    def _run_command(cmd: List[str], timeout: int = 30) -> Dict:
        """安全执行子进程命令，返回统一结构"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return {
                'returncode': result.returncode,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip()
            }
        except FileNotFoundError:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command not found: {cmd[0]}'
            }
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {timeout}s'
            }
        except Exception as e:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }

    def _log(self, user: Optional[str], action: str, ip: Optional[str],
             message: str, level: str = 'INFO'):
        """记录操作日志，避免在 log_manager 未就绪时崩溃"""
        try:
            from modules.log_manager import log_operation
            log_operation(user or 'system', action, ip or 'unknown', message, level)
        except Exception:
            pass

    # -------------------- 数据加载/保存 --------------------

    def _load_sites(self) -> Dict:
        if os.path.exists(self.sites_file):
            try:
                with open(self.sites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading sites: {e}")
        return {}

    def _save_sites(self) -> bool:
        return self._atomic_write_json(self.sites_file, self._sites)

    def _load_domains(self) -> Dict:
        if os.path.exists(self.domains_file):
            try:
                with open(self.domains_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading domains: {e}")
        return {}

    def _save_domains(self) -> bool:
        return self._atomic_write_json(self.domains_file, self._domains)

    # -------------------- 站点 CRUD --------------------

    def get_sites(self) -> List[Dict]:
        """获取所有站点（附带域名统计）"""
        sites = list(self._sites.values())
        for site in sites:
            site_domains = self.get_site_domains(site['id'])
            site['domain_count'] = len(site_domains)
            site['ssl_enabled'] = any(d.get('ssl_status') == 'active' for d in site_domains)
        return sites

    def get_site(self, site_id: str) -> Optional[Dict]:
        site = self._sites.get(site_id)
        if not site:
            return None
        # 附带完整域名信息
        site = dict(site)
        site['domains'] = self.get_site_domains(site_id)
        site['config_file'] = self._get_config_file_path(site)
        return site

    def add_site(self, site_data: Dict,
                 user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """添加新站点，并生成对应的 Web 服务器配置文件"""
        # 参数校验
        name = (site_data.get('name') or '').strip()
        root_dir = (site_data.get('root_dir') or '').strip()
        if not name or not root_dir:
            return {'status': 'error', 'message': '站点名称和根目录不能为空'}

        # 检查名称唯一性
        for s in self._sites.values():
            if s.get('name') == name:
                return {'status': 'error', 'message': f'站点名称已存在: {name}'}

        web_server = site_data.get('web_server', 'nginx').lower()
        if web_server not in self.SUPPORTED_WEB_SERVERS:
            return {'status': 'error', 'message': f'不支持的 Web 服务器: {web_server}'}

        site_id = self._gen_id('site')
        now = self._now()
        site = {
            'id': site_id,
            'name': name,
            'status': 'stopped',
            'created_at': now,
            'updated_at': now,
            'root_dir': root_dir,
            'web_server': web_server,
            'php_version': site_data.get('php_version', '7.4'),
            'database': site_data.get('database', None),
            'notes': site_data.get('notes', ''),
            'listen_port': int(site_data.get('listen_port', 80)),
            'ssl_port': int(site_data.get('ssl_port', 443)) if site_data.get('ssl_port') else None,
            'index_files': site_data.get('index_files', 'index.html index.htm index.php'),
            'error_log': site_data.get('error_log', ''),
            'access_log': site_data.get('access_log', ''),
            'auto_redirect_http': bool(site_data.get('auto_redirect_http', False)),
        }

        self._sites[site_id] = site
        if not self._save_sites():
            del self._sites[site_id]
            return {'status': 'error', 'message': '保存站点数据失败'}

        # 创建根目录（若不存在）
        try:
            os.makedirs(root_dir, exist_ok=True)
        except Exception as e:
            self._log(user, 'add_site', ip,
                      f'Created site {name} but failed to create root_dir: {e}',
                      level='WARN')

        # 生成配置文件
        config_result = self._write_config_file(site)
        site['config_file'] = self._get_config_file_path(site)

        self._log(user, 'add_site', ip,
                  f'Added site {name} ({site_id}), config: {config_result.get("message", "")}',
                  level='INFO' if config_result['status'] == 'success' else 'ERROR')

        return {'status': 'success', 'message': '站点添加成功', 'site': site,
                'config': config_result}

    def update_site(self, site_id: str, site_data: Dict,
                    user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """更新站点信息"""
        if site_id not in self._sites:
            return {'status': 'error', 'message': '站点不存在'}

        site = self._sites[site_id]
        old_web_server = site.get('web_server')
        old_root_dir = site.get('root_dir')

        # 受保护字段
        protected = {'id', 'created_at'}
        for key, value in site_data.items():
            if key in protected:
                continue
            if key in site:
                site[key] = value

        # 校验 web_server
        if site.get('web_server', '').lower() not in self.SUPPORTED_WEB_SERVERS:
            site['web_server'] = old_web_server
            return {'status': 'error', 'message': '不支持的 Web 服务器类型'}

        site['updated_at'] = self._now()

        if not self._save_sites():
            return {'status': 'error', 'message': '保存站点数据失败'}

        # 如果 web_server 或 root_dir 变化，重新生成配置文件
        if (site.get('web_server') != old_web_server or
                site.get('root_dir') != old_root_dir):
            # 删除旧配置文件
            self._delete_config_file({'id': site_id, 'web_server': old_web_server,
                                       'name': site.get('name')})
            self._write_config_file(site)

        self._log(user, 'update_site', ip,
                  f'Updated site {site.get("name")} ({site_id})', level='INFO')

        return {'status': 'success', 'message': '站点更新成功', 'site': site}

    def delete_site(self, site_id: str,
                    user: Optional[str] = None, ip: Optional[str] = None,
                    remove_files: bool = False) -> Dict:
        """删除站点及其配置文件、域名绑定"""
        if site_id not in self._sites:
            return {'status': 'error', 'message': '站点不存在'}

        site = self._sites[site_id]
        site_name = site.get('name')

        # 删除相关域名绑定
        domains_to_delete = [d_id for d_id, d in self._domains.items()
                             if d.get('site_id') == site_id]
        for d_id in domains_to_delete:
            del self._domains[d_id]
        self._save_domains()

        # 删除配置文件
        self._delete_config_file(site)

        # 可选：删除站点根目录
        root_dir = site.get('root_dir', '')
        if remove_files and root_dir and os.path.isdir(root_dir):
            try:
                shutil.rmtree(root_dir)
            except Exception as e:
                self._log(user, 'delete_site', ip,
                          f'Failed to remove root_dir {root_dir}: {e}',
                          level='WARN')

        del self._sites[site_id]
        if not self._save_sites():
            return {'status': 'error', 'message': '保存站点数据失败'}

        self._log(user, 'delete_site', ip,
                  f'Deleted site {site_name} ({site_id}), '
                  f'removed {len(domains_to_delete)} domains, '
                  f'remove_files={remove_files}', level='INFO')

        return {'status': 'success',
                'message': f'站点已删除，关联域名 {len(domains_to_delete)} 个已解绑'}

    def update_site_status(self, site_id: str, status: str,
                           user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """更新站点状态（仅更新元数据，不触发服务操作；启停服务请用 start/stop）"""
        if site_id not in self._sites:
            return {'status': 'error', 'message': '站点不存在'}
        if status not in self.VALID_STATUSES:
            return {'status': 'error', 'message': f'无效状态: {status}'}

        self._sites[site_id]['status'] = status
        self._sites[site_id]['updated_at'] = self._now()
        self._save_sites()
        return {'status': 'success', 'message': '站点状态已更新', 'status': status}

    # -------------------- 站点启停/重载 --------------------

    def start_site(self, site_id: str,
                   user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """启动站点：重载 Web 服务器配置使站点生效"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}

        # 确保配置文件存在
        if not os.path.exists(self._get_config_file_path(site)):
            self._write_config_file(site)

        result = self._reload_web_server(site['web_server'])
        if result['status'] == 'success':
            site['status'] = 'running'
            site['updated_at'] = self._now()
            self._save_sites()
            self._log(user, 'start_site', ip,
                      f'Started site {site["name"]} ({site_id})', level='INFO')
        else:
            site['status'] = 'error'
            site['updated_at'] = self._now()
            self._save_sites()
            self._log(user, 'start_site', ip,
                      f'Failed to start site {site["name"]}: {result.get("message")}',
                      level='ERROR')
        return result

    def stop_site(self, site_id: str,
                  user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """停止站点：移除配置文件并重载 Web 服务器"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}

        # 移除配置文件（标记为禁用）
        self._delete_config_file(site)
        # 写入禁用标记文件，便于排查
        disabled_marker = os.path.join(self.sites_config_dir, f"{site_id}.disabled")
        try:
            with open(disabled_marker, 'w', encoding='utf-8') as f:
                f.write(f"Site {site.get('name')} disabled at {self._now()}\n")
        except Exception:
            pass

        result = self._reload_web_server(site['web_server'])
        if result['status'] == 'success':
            site['status'] = 'stopped'
            site['updated_at'] = self._now()
            self._save_sites()
            self._log(user, 'stop_site', ip,
                      f'Stopped site {site["name"]} ({site_id})', level='INFO')
        else:
            site['status'] = 'error'
            site['updated_at'] = self._now()
            self._save_sites()
            self._log(user, 'stop_site', ip,
                      f'Failed to stop site {site["name"]}: {result.get("message")}',
                      level='ERROR')
        return result

    def reload_site(self, site_id: str,
                    user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """重载站点配置"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}

        # 重新生成配置文件
        self._write_config_file(site)
        result = self._reload_web_server(site['web_server'])
        self._log(user, 'reload_site', ip,
                  f'Reloaded site {site["name"]} ({site_id})', level='INFO')
        return result

    def _reload_web_server(self, web_server: str) -> Dict:
        """重载 Web 服务器配置"""
        if not self._is_linux():
            return {'status': 'error',
                    'message': f'当前系统不支持直接操作 {web_server}（仅 Linux）'}

        if web_server == 'nginx':
            # 先测试配置语法
            test = self._run_command(['nginx', '-t'])
            if test['returncode'] != 0:
                return {'status': 'error',
                        'message': 'Nginx 配置语法检查失败',
                        'error': test['stderr'] or test['stdout']}
            # 重载
            r = self._run_command(['nginx', '-s', 'reload'])
            if r['returncode'] == 0:
                return {'status': 'success', 'message': 'Nginx 已重载'}
            return {'status': 'error',
                    'message': 'Nginx 重载失败',
                    'error': r['stderr'] or r['stdout']}
        elif web_server == 'apache':
            test = self._run_command(['apachectl', 'configtest'])
            if test['returncode'] != 0:
                return {'status': 'error',
                        'message': 'Apache 配置语法检查失败',
                        'error': test['stderr'] or test['stdout']}
            r = self._run_command(['apachectl', 'graceful'])
            if r['returncode'] == 0:
                return {'status': 'success', 'message': 'Apache 已重载'}
            return {'status': 'error',
                    'message': 'Apache 重载失败',
                    'error': r['stderr'] or r['stdout']}
        return {'status': 'error', 'message': f'不支持的 Web 服务器: {web_server}'}

    # -------------------- 配置文件生成/编辑 --------------------

    def _get_config_file_path(self, site: Dict) -> str:
        """获取站点配置文件路径"""
        web_server = site.get('web_server', 'nginx')
        safe_name = self._sanitize_filename(site.get('name', site.get('id', 'site')))
        if web_server == 'apache':
            return os.path.join(self.apache_conf_dir, f"{safe_name}.conf")
        return os.path.join(self.nginx_conf_dir, f"{safe_name}.conf")

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """将站点名转换为安全的文件名"""
        import re
        safe = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
        return safe or 'site'

    def _generate_nginx_config(self, site: Dict, domains: List[Dict]) -> str:
        """生成 Nginx 配置文件内容"""
        root_dir = site.get('root_dir', '/var/www/html')
        index_files = site.get('index_files', 'index.html index.htm index.php')
        listen_port = site.get('listen_port', 80)
        php_version = site.get('php_version', '7.4')
        auto_redirect = site.get('auto_redirect_http', False)
        error_log = site.get('error_log', '')
        access_log = site.get('access_log', '')

        # 主域名列表
        server_names = ' '.join(d['domain'] for d in domains) if domains else site.get('name', '_')

        lines = [
            f"# Nginx configuration for site: {site.get('name')} ({site.get('id')})",
            f"# Generated by xiaopengPanel at {self._now()}",
            "",
        ]

        # 是否有 SSL 域名
        ssl_domains = [d for d in domains if d.get('ssl_status') == 'active' and d.get('ssl_cert')]
        ssl_port = site.get('ssl_port') or 443

        if ssl_domains:
            # 使用第一个 SSL 域名的证书
            cert = ssl_domains[0]['ssl_cert']
            key = ssl_domains[0]['ssl_key']
            lines.append(f"server {{")
            lines.append(f"    listen {ssl_port} ssl http2;")
            lines.append(f"    server_name {server_names};")
            lines.append(f"    root {root_dir};")
            lines.append(f"    index {index_files};")
            lines.append("")
            lines.append(f"    ssl_certificate {cert};")
            lines.append(f"    ssl_certificate_key {key};")
            lines.append(f"    ssl_protocols TLSv1.2 TLSv1.3;")
            lines.append(f"    ssl_ciphers HIGH:!aNULL:!MD5;")
            lines.append(f"    ssl_prefer_server_ciphers on;")
            lines.append("")
            if access_log:
                lines.append(f"    access_log {access_log};")
            if error_log:
                lines.append(f"    error_log {error_log};")
            lines.append("")
            lines.append(f"    location / {{")
            lines.append(f"        try_files $uri $uri/ =404;")
            lines.append(f"    }}")
            lines.append("")
            # PHP 支持
            if php_version:
                php_socket = f"/run/php/php{php_version}-fpm.sock"
                lines.append(f"    location ~ \\.php$ {{")
                lines.append(f"        fastcgi_pass unix:{php_socket};")
                lines.append(f"        fastcgi_index index.php;")
                lines.append(f"        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;")
                lines.append(f"        include fastcgi_params;")
                lines.append(f"    }}")
                lines.append("")
            # 禁止访问隐藏文件
            lines.append(f"    location ~ /\\. {{")
            lines.append(f"        deny all;")
            lines.append(f"    }}")
            lines.append(f"}}")
            lines.append("")

            # HTTP 跳转
            if auto_redirect:
                lines.append(f"server {{")
                lines.append(f"    listen {listen_port};")
                lines.append(f"    server_name {server_names};")
                lines.append(f"    return 301 https://$host$request_uri;")
                lines.append(f"}}")
            else:
                lines.append(f"server {{")
                lines.append(f"    listen {listen_port};")
                lines.append(f"    server_name {server_names};")
                lines.append(f"    root {root_dir};")
                lines.append(f"    index {index_files};")
                lines.append("")
                lines.append(f"    location / {{")
                lines.append(f"        try_files $uri $uri/ =404;")
                lines.append(f"    }}")
                lines.append(f"}}")
        else:
            # 纯 HTTP
            lines.append(f"server {{")
            lines.append(f"    listen {listen_port};")
            lines.append(f"    server_name {server_names};")
            lines.append(f"    root {root_dir};")
            lines.append(f"    index {index_files};")
            lines.append("")
            if access_log:
                lines.append(f"    access_log {access_log};")
            if error_log:
                lines.append(f"    error_log {error_log};")
            lines.append("")
            lines.append(f"    location / {{")
            lines.append(f"        try_files $uri $uri/ =404;")
            lines.append(f"    }}")
            lines.append("")
            if php_version:
                php_socket = f"/run/php/php{php_version}-fpm.sock"
                lines.append(f"    location ~ \\.php$ {{")
                lines.append(f"        fastcgi_pass unix:{php_socket};")
                lines.append(f"        fastcgi_index index.php;")
                lines.append(f"        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;")
                lines.append(f"        include fastcgi_params;")
                lines.append(f"    }}")
                lines.append("")
            lines.append(f"    location ~ /\\. {{")
            lines.append(f"        deny all;")
            lines.append(f"    }}")
            lines.append(f"}}")

        return '\n'.join(lines) + '\n'

    def _generate_apache_config(self, site: Dict, domains: List[Dict]) -> str:
        """生成 Apache 配置文件内容"""
        root_dir = site.get('root_dir', '/var/www/html')
        index_files = site.get('index_files', 'index.html index.php')
        listen_port = site.get('listen_port', 80)
        server_names = ' '.join(d['domain'] for d in domains) if domains else site.get('name', '_')
        php_version = site.get('php_version', '7.4')
        error_log = site.get('error_log', '')
        access_log = site.get('access_log', '')

        lines = [
            f"# Apache configuration for site: {site.get('name')} ({site.get('id')})",
            f"# Generated by xiaopengPanel at {self._now()}",
            "",
            f"<VirtualHost *:{listen_port}>",
            f"    ServerName {(server_names.split() or ['_'])[0]}",
        ]
        if len(server_names.split()) > 1:
            lines.append(f"    ServerAlias {' '.join(server_names.split()[1:])}")
        lines.append(f"    DocumentRoot {root_dir}")
        lines.append(f"    DirectoryIndex {index_files}")
        lines.append("")
        lines.append(f"    <Directory {root_dir}>")
        lines.append(f"        Options -Indexes +FollowSymLinks")
        lines.append(f"        AllowOverride All")
        lines.append(f"        Require all granted")
        lines.append(f"    </Directory>")
        lines.append("")
        if access_log:
            lines.append(f"    CustomLog {access_log} combined")
        if error_log:
            lines.append(f"    ErrorLog {error_log}")
        lines.append("")
        if php_version:
            lines.append(f"    <FilesMatch \\.php$>")
            lines.append(f"        SetHandler \"proxy:unix:/run/php/php{php_version}-fpm.sock|fcgi://localhost\"")
            lines.append(f"    </FilesMatch>")
            lines.append("")
        lines.append(f"</VirtualHost>")
        return '\n'.join(lines) + '\n'

    def _write_config_file(self, site: Dict) -> Dict:
        """根据站点数据生成 Web 服务器配置文件"""
        try:
            domains = self.get_site_domains(site['id'])
            web_server = site.get('web_server', 'nginx')
            content = self._generate_nginx_config(site, domains) if web_server == 'nginx' \
                else self._generate_apache_config(site, domains)
            config_path = self._get_config_file_path(site)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {'status': 'success',
                    'message': '配置文件已生成',
                    'config_file': config_path,
                    'content': content}
        except Exception as e:
            return {'status': 'error',
                    'message': f'生成配置文件失败: {e}'}

    def _delete_config_file(self, site: Dict) -> bool:
        """删除站点配置文件"""
        config_path = self._get_config_file_path(site)
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            return True
        except Exception:
            return False

    def get_site_config(self, site_id: str) -> Dict:
        """获取站点配置文件内容"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}

        config_path = self._get_config_file_path(site)
        if not os.path.exists(config_path):
            # 自动生成
            result = self._write_config_file(site)
            if result['status'] != 'success':
                return result
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {'status': 'success',
                    'config_file': config_path,
                    'content': content}
        except Exception as e:
            return {'status': 'error', 'message': f'读取配置文件失败: {e}'}

    def save_site_config(self, site_id: str, content: str,
                         user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """保存站点配置文件内容（在线编辑）"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}
        if not isinstance(content, str):
            return {'status': 'error', 'message': '配置内容必须为字符串'}

        config_path = self._get_config_file_path(site)

        # 备份原配置
        if os.path.exists(config_path):
            backup_path = f"{config_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                shutil.copy2(config_path, backup_path)
            except Exception:
                pass

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return {'status': 'error', 'message': f'保存配置文件失败: {e}'}

        # Linux 下自动校验语法
        validation = None
        if self._is_linux():
            validation = self._validate_config_syntax(site['web_server'])

        self._log(user, 'save_site_config', ip,
                  f'Saved config for site {site.get("name")} ({site_id})',
                  level='INFO')
        return {'status': 'success',
                'message': '配置文件已保存',
                'config_file': config_path,
                'validation': validation}

    def validate_site_config(self, site_id: str) -> Dict:
        """校验站点配置文件语法"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}
        return self._validate_config_syntax(site['web_server'])

    def _validate_config_syntax(self, web_server: str) -> Dict:
        """校验 Web 服务器配置语法"""
        if not self._is_linux():
            return {'status': 'success', 'message': '非 Linux 系统，跳过语法校验'}

        if web_server == 'nginx':
            r = self._run_command(['nginx', '-t'])
            if r['returncode'] == 0:
                return {'status': 'success', 'message': 'Nginx 配置语法正确',
                        'output': r['stderr'] or r['stdout']}
            return {'status': 'error', 'message': 'Nginx 配置语法错误',
                    'error': r['stderr'] or r['stdout']}
        elif web_server == 'apache':
            r = self._run_command(['apachectl', 'configtest'])
            if r['returncode'] == 0:
                return {'status': 'success', 'message': 'Apache 配置语法正确',
                        'output': r['stderr'] or r['stdout']}
            return {'status': 'error', 'message': 'Apache 配置语法错误',
                    'error': r['stderr'] or r['stdout']}
        return {'status': 'error', 'message': f'不支持的 Web 服务器: {web_server}'}

    # -------------------- 域名管理 --------------------

    def get_domains(self) -> List[Dict]:
        return list(self._domains.values())

    def get_site_domains(self, site_id: str) -> List[Dict]:
        return [d for d in self._domains.values() if d.get('site_id') == site_id]

    def add_domain(self, domain_data: Dict,
                   user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """添加域名绑定"""
        site_id = domain_data.get('site_id')
        if site_id not in self._sites:
            return {'status': 'error', 'message': '站点不存在'}

        domain_name = (domain_data.get('domain') or '').strip().lower()
        if not domain_name:
            return {'status': 'error', 'message': '域名不能为空'}

        # 检查域名唯一性
        for d in self._domains.values():
            if d.get('domain') == domain_name:
                return {'status': 'error', 'message': f'域名已绑定: {domain_name}'}

        domain_id = self._gen_id('domain')
        now = self._now()
        domain = {
            'id': domain_id,
            'site_id': site_id,
            'domain': domain_name,
            'status': 'pending',
            'created_at': now,
            'updated_at': now,
            'ssl_status': domain_data.get('ssl_status', 'disabled'),
            'ssl_cert': domain_data.get('ssl_cert', None),
            'ssl_key': domain_data.get('ssl_key', None),
            'ssl_expiry': domain_data.get('ssl_expiry', None),
            'ssl_issuer': domain_data.get('ssl_issuer', None),
            'force_https': bool(domain_data.get('force_https', False)),
        }

        self._domains[domain_id] = domain
        if not self._save_domains():
            del self._domains[domain_id]
            return {'status': 'error', 'message': '保存域名数据失败'}

        # 重新生成站点配置文件
        self._write_config_file(self._sites[site_id])

        self._log(user, 'add_domain', ip,
                  f'Added domain {domain_name} to site {site_id}', level='INFO')

        return {'status': 'success', 'message': '域名绑定成功', 'domain': domain}

    def update_domain(self, domain_id: str, domain_data: Dict,
                      user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """更新域名信息"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        protected = {'id', 'created_at', 'site_id'}
        for key, value in domain_data.items():
            if key in protected:
                continue
            if key in domain:
                domain[key] = value

        domain['updated_at'] = self._now()
        if not self._save_domains():
            return {'status': 'error', 'message': '保存域名数据失败'}

        # 重新生成站点配置文件
        site_id = domain.get('site_id')
        if site_id in self._sites:
            self._write_config_file(self._sites[site_id])

        self._log(user, 'update_domain', ip,
                  f'Updated domain {domain.get("domain")} ({domain_id})', level='INFO')
        return {'status': 'success', 'message': '域名更新成功', 'domain': domain}

    def delete_domain(self, domain_id: str,
                      user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """删除域名绑定"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        site_id = domain.get('site_id')
        domain_name = domain.get('domain')

        del self._domains[domain_id]
        if not self._save_domains():
            return {'status': 'error', 'message': '保存域名数据失败'}

        # 重新生成站点配置文件
        if site_id in self._sites:
            self._write_config_file(self._sites[site_id])

        self._log(user, 'delete_domain', ip,
                  f'Deleted domain {domain_name} ({domain_id})', level='INFO')
        return {'status': 'success', 'message': '域名绑定已删除'}

    def check_domain_status(self, domain_id: str,
                            user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """检查域名 DNS 解析状态"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        domain_name = domain.get('domain', '')

        # 通过 socket 进行 DNS 解析
        try:
            resolved_ip = socket.gethostbyname(domain_name)
            domain['status'] = 'active'
            domain['resolved_ip'] = resolved_ip
            message = f'域名 {domain_name} 解析正常，IP: {resolved_ip}'
            level = 'INFO'
        except socket.gaierror as e:
            domain['status'] = 'error'
            domain['resolved_ip'] = None
            message = f'域名 {domain_name} DNS 解析失败: {e}'
            level = 'WARN'
        except Exception as e:
            domain['status'] = 'error'
            domain['resolved_ip'] = None
            message = f'域名 {domain_name} 检查异常: {e}'
            level = 'ERROR'

        domain['updated_at'] = self._now()
        self._save_domains()
        self._log(user, 'check_domain_status', ip, message, level=level)

        return {'status': 'success', 'message': message, 'domain': domain}

    # -------------------- SSL 证书管理 --------------------

    def issue_ssl_certificate(self, domain_id: str,
                              user: Optional[str] = None, ip: Optional[str] = None,
                              email: Optional[str] = None) -> Dict:
        """通过 certbot 申请 Let's Encrypt 证书"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        domain_name = domain.get('domain', '')
        if not domain_name:
            return {'status': 'error', 'message': '域名为空'}

        if not self._is_linux():
            return {'status': 'error',
                    'message': '证书签发仅支持 Linux 系统（需 certbot）'}

        # 标记为 pending
        domain['ssl_status'] = 'pending'
        domain['updated_at'] = self._now()
        self._save_domains()

        cert_dir = os.path.join(self.ssl_cert_dir, domain_name)
        os.makedirs(cert_dir, exist_ok=True)

        cmd = [
            'certbot', 'certonly',
            '--non-interactive',
            '--agree-tos',
            '--webroot',
            '--webroot-path', domain.get('webroot', '/var/www/html'),
            '-d', domain_name,
            '--cert-path', os.path.join(cert_dir, 'cert.pem'),
            '--key-path', os.path.join(cert_dir, 'privkey.pem'),
            '--fullchain-path', os.path.join(cert_dir, 'fullchain.pem'),
        ]
        if email:
            cmd.extend(['--email', email])

        result = self._run_command(cmd, timeout=120)
        if result['returncode'] == 0:
            cert_path = os.path.join(cert_dir, 'fullchain.pem')
            key_path = os.path.join(cert_dir, 'privkey.pem')
            domain['ssl_status'] = 'active'
            domain['ssl_cert'] = cert_path
            domain['ssl_key'] = key_path
            domain['ssl_issuer'] = "Let's Encrypt"
            domain['ssl_expiry'] = self._get_cert_expiry(cert_path)
            domain['updated_at'] = self._now()
            self._save_domains()
            # 重新生成站点配置文件（启用 SSL）
            site_id = domain.get('site_id')
            if site_id in self._sites:
                self._write_config_file(self._sites[site_id])
            self._log(user, 'issue_ssl', ip,
                      f'Issued SSL cert for {domain_name}', level='INFO')
            return {'status': 'success',
                    'message': f'证书签发成功: {domain_name}',
                    'domain': domain}
        else:
            domain['ssl_status'] = 'error'
            domain['updated_at'] = self._now()
            self._save_domains()
            self._log(user, 'issue_ssl', ip,
                      f'Failed to issue SSL for {domain_name}: {result["stderr"]}',
                      level='ERROR')
            return {'status': 'error',
                    'message': '证书签发失败',
                    'error': result['stderr'] or result['stdout']}

    def renew_ssl_certificate(self, domain_id: str,
                              user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """续期 SSL 证书"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        domain_name = domain.get('domain', '')

        if not self._is_linux():
            return {'status': 'error', 'message': '证书续期仅支持 Linux 系统'}

        cmd = ['certbot', 'renew', '--cert-name', domain_name, '--non-interactive']
        result = self._run_command(cmd, timeout=120)
        if result['returncode'] == 0:
            if domain.get('ssl_cert'):
                domain['ssl_expiry'] = self._get_cert_expiry(domain['ssl_cert'])
            domain['ssl_status'] = 'active'
            domain['updated_at'] = self._now()
            self._save_domains()
            self._log(user, 'renew_ssl', ip,
                      f'Renewed SSL for {domain_name}', level='INFO')
            return {'status': 'success', 'message': f'证书续期成功: {domain_name}'}
        else:
            self._log(user, 'renew_ssl', ip,
                      f'Failed to renew SSL for {domain_name}: {result["stderr"]}',
                      level='ERROR')
            return {'status': 'error', 'message': '证书续期失败',
                    'error': result['stderr'] or result['stdout']}

    def revoke_ssl_certificate(self, domain_id: str,
                               user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """撤销 SSL 证书"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        domain_name = domain.get('domain', '')

        if not self._is_linux():
            return {'status': 'error', 'message': '证书撤销仅支持 Linux 系统'}

        cmd = ['certbot', 'delete', '--cert-name', domain_name, '--non-interactive']
        result = self._run_command(cmd, timeout=60)

        domain['ssl_status'] = 'disabled'
        domain['ssl_cert'] = None
        domain['ssl_key'] = None
        domain['ssl_expiry'] = None
        domain['ssl_issuer'] = None
        domain['updated_at'] = self._now()
        self._save_domains()

        # 重新生成站点配置文件（移除 SSL）
        site_id = domain.get('site_id')
        if site_id in self._sites:
            self._write_config_file(self._sites[site_id])

        self._log(user, 'revoke_ssl', ip,
                  f'Revoked SSL for {domain_name}', level='INFO')
        return {'status': 'success',
                'message': f'证书已撤销: {domain_name}',
                'output': result.get('stderr') or result.get('stdout')}

    @staticmethod
    def _get_cert_expiry(cert_path: str) -> Optional[str]:
        """读取证书过期时间（通过 openssl）"""
        if not os.path.exists(cert_path):
            return None
        try:
            r = SiteManager._run_command(
                ['openssl', 'x509', '-enddate', '-noout', '-in', cert_path])
            if r['returncode'] == 0:
                # 输出格式: notAfter=Aug 23 12:34:56 2026 GMT
                return r['stdout'].split('=', 1)[-1].strip()
        except Exception:
            pass
        return None

    def check_ssl_status(self, domain_id: str) -> Dict:
        """检查 SSL 证书状态"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': '域名不存在'}

        domain = self._domains[domain_id]
        cert_path = domain.get('ssl_cert')
        if not cert_path or not os.path.exists(cert_path):
            domain['ssl_status'] = 'disabled'
            self._save_domains()
            return {'status': 'success', 'message': '未配置证书', 'domain': domain}

        expiry = self._get_cert_expiry(cert_path)
        domain['ssl_expiry'] = expiry

        # 检查是否过期
        if expiry:
            try:
                from datetime import datetime as dt
                # 解析 "Aug 23 12:34:56 2026 GMT"
                exp_dt = dt.strptime(expiry, '%b %d %H:%M:%S %Y %Z')
                now = dt.now()
                days_left = (exp_dt - now).days
                domain['days_until_expiry'] = days_left
                if days_left < 0:
                    domain['ssl_status'] = 'expired'
                elif days_left < 30:
                    domain['ssl_status'] = 'pending'  # 即将过期
                else:
                    domain['ssl_status'] = 'active'
            except Exception:
                pass

        domain['updated_at'] = self._now()
        self._save_domains()
        return {'status': 'success', 'domain': domain}

    # -------------------- 站点备份/恢复 --------------------

    def backup_site(self, site_id: str,
                    user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """备份站点配置（站点 JSON + 域名 JSON + Web 服务器配置文件）"""
        site = self._sites.get(site_id)
        if not site:
            return {'status': 'error', 'message': '站点不存在'}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        safe_name = self._sanitize_filename(site.get('name', site_id))
        backup_name = f"{safe_name}_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            import zipfile
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 写入站点元数据
                zf.writestr('site.json', json.dumps(site, ensure_ascii=False, indent=4))
                # 写入关联域名
                domains = self.get_site_domains(site_id)
                zf.writestr('domains.json', json.dumps(domains, ensure_ascii=False, indent=4))
                # 写入 Web 服务器配置文件
                config_path = self._get_config_file_path(site)
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        zf.writestr(os.path.basename(config_path), f.read())

            self._log(user, 'backup_site', ip,
                      f'Backed up site {site.get("name")} to {backup_name}', level='INFO')
            return {'status': 'success',
                    'message': '备份成功',
                    'backup_file': backup_path,
                    'backup_name': backup_name}
        except Exception as e:
            return {'status': 'error', 'message': f'备份失败: {e}'}

    def list_backups(self, site_id: Optional[str] = None) -> Dict:
        """列出站点备份"""
        backups = []
        try:
            for fname in sorted(os.listdir(self.backup_dir), reverse=True):
                if not fname.endswith('.zip'):
                    continue
                fpath = os.path.join(self.backup_dir, fname)
                stat = os.stat(fpath)
                backups.append({
                    'name': fname,
                    'path': fpath,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        except Exception:
            pass
        return {'status': 'success', 'backups': backups}

    def delete_backup(self, backup_name: str,
                      user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """删除备份文件"""
        # 防止路径穿越
        if not backup_name.endswith('.zip') or '/' in backup_name or '\\' in backup_name:
            return {'status': 'error', 'message': '无效的备份文件名'}
        backup_path = os.path.join(self.backup_dir, backup_name)
        if not os.path.exists(backup_path):
            return {'status': 'error', 'message': '备份文件不存在'}
        try:
            os.remove(backup_path)
            self._log(user, 'delete_backup', ip,
                      f'Deleted backup {backup_name}', level='INFO')
            return {'status': 'success', 'message': '备份已删除'}
        except Exception as e:
            return {'status': 'error', 'message': f'删除失败: {e}'}

    # -------------------- 统计信息 --------------------

    def get_stats(self) -> Dict:
        """获取站点统计信息"""
        total = len(self._sites)
        by_status = {'running': 0, 'stopped': 0, 'error': 0, 'pending': 0}
        by_web_server = {}
        for site in self._sites.values():
            status = site.get('status', 'stopped')
            if status in by_status:
                by_status[status] += 1
            ws = site.get('web_server', 'nginx')
            by_web_server[ws] = by_web_server.get(ws, 0) + 1

        total_domains = len(self._domains)
        ssl_active = sum(1 for d in self._domains.values()
                         if d.get('ssl_status') == 'active')
        ssl_expiring = sum(1 for d in self._domains.values()
                           if d.get('ssl_status') == 'pending'
                           and d.get('ssl_expiry'))

        return {
            'status': 'success',
            'total_sites': total,
            'by_status': by_status,
            'by_web_server': by_web_server,
            'total_domains': total_domains,
            'ssl_active': ssl_active,
            'ssl_expiring': ssl_expiring
        }

    # -------------------- 批量操作 --------------------

    def batch_delete_sites(self, site_ids: List[str],
                           user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """批量删除站点"""
        success_count = 0
        error_count = 0
        for site_id in site_ids:
            result = self.delete_site(site_id, user=user, ip=ip)
            if result['status'] == 'success':
                success_count += 1
            else:
                error_count += 1
        return {
            'status': 'success',
            'message': f'批量删除完成: 成功 {success_count} 个, 失败 {error_count} 个',
            'success_count': success_count,
            'error_count': error_count
        }

    def batch_delete_domains(self, domain_ids: List[str],
                             user: Optional[str] = None, ip: Optional[str] = None) -> Dict:
        """批量删除域名"""
        success_count = 0
        error_count = 0
        for domain_id in domain_ids:
            result = self.delete_domain(domain_id, user=user, ip=ip)
            if result['status'] == 'success':
                success_count += 1
            else:
                error_count += 1
        return {
            'status': 'success',
            'message': f'批量删除完成: 成功 {success_count} 个, 失败 {error_count} 个',
            'success_count': success_count,
            'error_count': error_count
        }

    # -------------------- 搜索和筛选 --------------------

    def search_sites(self, keyword: str) -> List[Dict]:
        """根据关键词搜索站点"""
        results = []
        kw = (keyword or '').lower()
        for site in self._sites.values():
            if (kw in (site.get('name') or '').lower() or
                kw in (site.get('root_dir') or '').lower() or
                kw in (site.get('notes') or '').lower()):
                results.append(site)
        return results

    def filter_sites(self, filters: Dict) -> List[Dict]:
        """根据条件筛选站点"""
        results = list(self._sites.values())
        if 'status' in filters and filters['status']:
            results = [s for s in results if s.get('status') == filters['status']]
        if 'web_server' in filters and filters['web_server']:
            results = [s for s in results if s.get('web_server') == filters['web_server']]
        if 'php_version' in filters and filters['php_version']:
            results = [s for s in results if s.get('php_version') == filters['php_version']]
        return results
