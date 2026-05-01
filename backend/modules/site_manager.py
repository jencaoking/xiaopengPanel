import os
import json
from datetime import datetime
from typing import Dict, List, Optional

class SiteManager:
    def __init__(self, config):
        self.config = config
        self.sites_file = os.path.join(self.config.BASE_DIR, 'config', 'sites.json')
        self.domains_file = os.path.join(self.config.BASE_DIR, 'config', 'domains.json')
        self._sites = self._load_sites()
        self._domains = self._load_domains()
    
    def _load_sites(self) -> Dict:
        """从JSON文件加载站点数据"""
        if os.path.exists(self.sites_file):
            try:
                with open(self.sites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading sites: {e}")
        return {}
    
    def _save_sites(self):
        """保存站点数据到JSON文件"""
        try:
            with open(self.sites_file, 'w', encoding='utf-8') as f:
                json.dump(self._sites, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving sites: {e}")
            return False
    
    def _load_domains(self) -> Dict:
        """从JSON文件加载域名数据"""
        if os.path.exists(self.domains_file):
            try:
                with open(self.domains_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading domains: {e}")
        return {}
    
    def _save_domains(self):
        """保存域名数据到JSON文件"""
        try:
            with open(self.domains_file, 'w', encoding='utf-8') as f:
                json.dump(self._domains, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving domains: {e}")
            return False
    
    # 站点管理方法
    def get_sites(self) -> List[Dict]:
        """获取所有站点"""
        return list(self._sites.values())
    
    def get_site(self, site_id: str) -> Optional[Dict]:
        """根据ID获取站点"""
        return self._sites.get(site_id)
    
    def add_site(self, site_data: Dict) -> Dict:
        """添加新站点"""
        # 生成唯一站点ID
        site_id = f"site_{len(self._sites) + 1}"
        
        # 构建站点数据
        site = {
            'id': site_id,
            'name': site_data.get('name'),
            'status': 'stopped',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'root_dir': site_data.get('root_dir'),
            'web_server': site_data.get('web_server', 'nginx'),
            'php_version': site_data.get('php_version', '7.4'),
            'database': site_data.get('database', None),
            'notes': site_data.get('notes', '')
        }
        
        # 添加到站点列表
        self._sites[site_id] = site
        
        # 保存到文件
        if self._save_sites():
            return {'status': 'success', 'message': 'Site added successfully', 'site': site}
        else:
            return {'status': 'error', 'message': 'Failed to add site'}
    
    def update_site(self, site_id: str, site_data: Dict) -> Dict:
        """更新站点信息"""
        if site_id not in self._sites:
            return {'status': 'error', 'message': 'Site not found'}
        
        # 更新站点数据
        site = self._sites[site_id]
        for key, value in site_data.items():
            if key in site and key != 'id' and key != 'created_at':
                site[key] = value
        
        site['updated_at'] = datetime.now().isoformat()
        
        # 保存到文件
        if self._save_sites():
            return {'status': 'success', 'message': 'Site updated successfully', 'site': site}
        else:
            return {'status': 'error', 'message': 'Failed to update site'}
    
    def delete_site(self, site_id: str) -> Dict:
        """删除站点"""
        if site_id not in self._sites:
            return {'status': 'error', 'message': 'Site not found'}
        
        # 删除相关域名绑定
        domains_to_delete = []
        for domain_id, domain in self._domains.items():
            if domain['site_id'] == site_id:
                domains_to_delete.append(domain_id)
        
        for domain_id in domains_to_delete:
            del self._domains[domain_id]
        self._save_domains()
        
        # 删除站点
        del self._sites[site_id]
        
        # 保存到文件
        if self._save_sites():
            return {'status': 'success', 'message': 'Site deleted successfully'}
        else:
            return {'status': 'error', 'message': 'Failed to delete site'}
    
    def update_site_status(self, site_id: str, status: str) -> Dict:
        """更新站点状态"""
        if site_id not in self._sites:
            return {'status': 'error', 'message': 'Site not found'}
        
        self._sites[site_id]['status'] = status
        self._sites[site_id]['updated_at'] = datetime.now().isoformat()
        
        if self._save_sites():
            return {'status': 'success', 'message': 'Site status updated', 'status': status}
        else:
            return {'status': 'error', 'message': 'Failed to update site status'}
    
    # 域名管理方法
    def get_domains(self) -> List[Dict]:
        """获取所有域名"""
        return list(self._domains.values())
    
    def get_site_domains(self, site_id: str) -> List[Dict]:
        """获取指定站点的所有域名"""
        return [domain for domain in self._domains.values() if domain['site_id'] == site_id]
    
    def add_domain(self, domain_data: Dict) -> Dict:
        """添加域名绑定"""
        # 检查站点是否存在
        if domain_data['site_id'] not in self._sites:
            return {'status': 'error', 'message': 'Site not found'}
        
        # 生成唯一域名ID
        domain_id = f"domain_{len(self._domains) + 1}"
        
        # 构建域名数据
        domain = {
            'id': domain_id,
            'site_id': domain_data['site_id'],
            'domain': domain_data['domain'],
            'status': 'pending',  # pending, active, error
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'ssl_status': domain_data.get('ssl_status', 'disabled'),
            'ssl_cert': domain_data.get('ssl_cert', None),
            'ssl_key': domain_data.get('ssl_key', None)
        }
        
        # 添加到域名列表
        self._domains[domain_id] = domain
        
        # 保存到文件
        if self._save_domains():
            return {'status': 'success', 'message': 'Domain added successfully', 'domain': domain}
        else:
            return {'status': 'error', 'message': 'Failed to add domain'}
    
    def update_domain(self, domain_id: str, domain_data: Dict) -> Dict:
        """更新域名信息"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': 'Domain not found'}
        
        # 更新域名数据
        domain = self._domains[domain_id]
        for key, value in domain_data.items():
            if key in domain and key != 'id' and key != 'created_at':
                domain[key] = value
        
        domain['updated_at'] = datetime.now().isoformat()
        
        # 保存到文件
        if self._save_domains():
            return {'status': 'success', 'message': 'Domain updated successfully', 'domain': domain}
        else:
            return {'status': 'error', 'message': 'Failed to update domain'}
    
    def delete_domain(self, domain_id: str) -> Dict:
        """删除域名绑定"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': 'Domain not found'}
        
        # 删除域名
        del self._domains[domain_id]
        
        # 保存到文件
        if self._save_domains():
            return {'status': 'success', 'message': 'Domain deleted successfully'}
        else:
            return {'status': 'error', 'message': 'Failed to delete domain'}
    
    def check_domain_status(self, domain_id: str) -> Dict:
        """检查域名解析状态"""
        if domain_id not in self._domains:
            return {'status': 'error', 'message': 'Domain not found'}
        
        # 这里可以添加实际的域名解析检查逻辑
        # 暂时返回模拟数据
        domain = self._domains[domain_id]
        domain['status'] = 'active'
        domain['updated_at'] = datetime.now().isoformat()
        
        self._save_domains()
        return {'status': 'success', 'message': 'Domain status checked', 'domain': domain}
    
    # 批量操作
    def batch_delete_sites(self, site_ids: List[str]) -> Dict:
        """批量删除站点"""
        success_count = 0
        error_count = 0
        
        for site_id in site_ids:
            if site_id in self._sites:
                # 删除相关域名
                domains_to_delete = []
                for domain_id, domain in self._domains.items():
                    if domain['site_id'] == site_id:
                        domains_to_delete.append(domain_id)
                
                for domain_id in domains_to_delete:
                    del self._domains[domain_id]
                
                # 删除站点
                del self._sites[site_id]
                success_count += 1
            else:
                error_count += 1
        
        # 保存到文件
        if self._save_sites() and self._save_domains():
            return {
                'status': 'success', 
                'message': f'Batch delete completed: {success_count} sites deleted, {error_count} sites not found'
            }
        else:
            return {'status': 'error', 'message': 'Failed to complete batch delete'}
    
    def batch_delete_domains(self, domain_ids: List[str]) -> Dict:
        """批量删除域名"""
        success_count = 0
        error_count = 0
        
        for domain_id in domain_ids:
            if domain_id in self._domains:
                del self._domains[domain_id]
                success_count += 1
            else:
                error_count += 1
        
        # 保存到文件
        if self._save_domains():
            return {
                'status': 'success', 
                'message': f'Batch delete completed: {success_count} domains deleted, {error_count} domains not found'
            }
        else:
            return {'status': 'error', 'message': 'Failed to complete batch delete'}
    
    # 搜索和筛选
    def search_sites(self, keyword: str) -> List[Dict]:
        """根据关键词搜索站点"""
        results = []
        keyword = keyword.lower()
        
        for site in self._sites.values():
            if (
                keyword in site['name'].lower() or
                keyword in site['root_dir'].lower() or
                keyword in site['notes'].lower()
            ):
                results.append(site)
        
        return results
    
    def filter_sites(self, filters: Dict) -> List[Dict]:
        """根据条件筛选站点"""
        results = list(self._sites.values())
        
        if 'status' in filters:
            results = [site for site in results if site['status'] == filters['status']]
        
        if 'web_server' in filters:
            results = [site for site in results if site['web_server'] == filters['web_server']]
        
        if 'php_version' in filters:
            results = [site for site in results if site['php_version'] == filters['php_version']]
        
        return results
