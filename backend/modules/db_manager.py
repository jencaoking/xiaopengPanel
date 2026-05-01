import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from .log_manager import log_system, log_operation

# Database connection configurations
DB_CONFIGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'db_configs.json')

class DatabaseManager:
    def __init__(self):
        self.db_configs = self._load_db_configs()
        self.supported_dbs = ['mysql', 'postgresql']
        
    def _load_db_configs(self) -> Dict:
        """Load database configurations from file"""
        if not os.path.exists(DB_CONFIGS_FILE):
            # Ensure data directory exists
            os.makedirs(os.path.dirname(DB_CONFIGS_FILE), exist_ok=True)
            with open(DB_CONFIGS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        
        with open(DB_CONFIGS_FILE, 'r') as f:
            return json.load(f)
    
    def _save_db_configs(self) -> None:
        """Save database configurations to file"""
        with open(DB_CONFIGS_FILE, 'w') as f:
            json.dump(self.db_configs, f, indent=2)
    
    def add_db_config(self, config_id: str, db_type: str, host: str, port: int, username: str, password: str, description: str = '') -> Dict:
        """Add a new database configuration"""
        if db_type not in self.supported_dbs:
            log_system(f"Failed to add DB config {config_id}: Unsupported database type {db_type}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        
        if config_id in self.db_configs:
            log_system(f"Failed to add DB config {config_id}: Configuration already exists", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} already exists'}
        
        self.db_configs[config_id] = {
            'db_type': db_type,
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self._save_db_configs()
        log_system(f"Added new DB config: {config_id} (Type: {db_type}, Host: {host})", level='INFO', name='db_manager')
        return {'status': 'success', 'message': f'Database configuration {config_id} added successfully'}
    
    def update_db_config(self, config_id: str, updates: Dict) -> Dict:
        """Update an existing database configuration"""
        if config_id not in self.db_configs:
            log_system(f"Failed to update DB config: {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        # Only allow updating certain fields
        allowed_fields = ['db_type', 'host', 'port', 'username', 'password', 'description']
        updated_fields = []
        for field, value in updates.items():
            if field in allowed_fields:
                self.db_configs[config_id][field] = value
                updated_fields.append(field)
        
        self.db_configs[config_id]['updated_at'] = datetime.now().isoformat()
        self._save_db_configs()
        log_system(f"Updated DB config: {config_id} (Fields: {', '.join(updated_fields)})", level='INFO', name='db_manager')
        return {'status': 'success', 'message': f'Database configuration {config_id} updated successfully'}
    
    def delete_db_config(self, config_id: str) -> Dict:
        """Delete a database configuration"""
        if config_id not in self.db_configs:
            log_system(f"Failed to delete DB config: {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        db_type = self.db_configs[config_id]['db_type']
        host = self.db_configs[config_id]['host']
        del self.db_configs[config_id]
        self._save_db_configs()
        log_system(f"Deleted DB config: {config_id} (Type: {db_type}, Host: {host})", level='INFO', name='db_manager')
        return {'status': 'success', 'message': f'Database configuration {config_id} deleted successfully'}
    
    def get_db_configs(self) -> Dict:
        """Get all database configurations"""
        return {'status': 'success', 'configs': self.db_configs}
    
    def get_db_config(self, config_id: str) -> Dict:
        """Get a specific database configuration"""
        if config_id not in self.db_configs:
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        return {'status': 'success', 'config': self.db_configs[config_id]}
    
    def test_connection(self, config_id: str) -> Dict:
        """Test database connection"""
        if config_id not in self.db_configs:
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                return self._test_mysql_connection(config)
            elif db_type == 'postgresql':
                return self._test_postgresql_connection(config)
            else:
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Connection test failed: {str(e)}'}
    
    def _test_mysql_connection(self, config: Dict) -> Dict:
        """Test MySQL connection"""
        try:
            import mysql.connector
            from mysql.connector import Error
            
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password']
            )
            
            if conn.is_connected():
                conn.close()
                return {'status': 'success', 'message': 'MySQL connection successful'}
            else:
                return {'status': 'error', 'message': 'MySQL connection failed'}
        except ImportError:
            return {'status': 'error', 'message': 'MySQL connector not installed'}
        except Error as e:
            return {'status': 'error', 'message': f'MySQL error: {str(e)}'}
    
    def _test_postgresql_connection(self, config: Dict) -> Dict:
        """Test PostgreSQL connection"""
        try:
            import psycopg2
            from psycopg2 import OperationalError
            
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password'],
                dbname='postgres'
            )
            
            conn.close()
            return {'status': 'success', 'message': 'PostgreSQL connection successful'}
        except ImportError:
            return {'status': 'error', 'message': 'PostgreSQL connector not installed'}
        except OperationalError as e:
            return {'status': 'error', 'message': f'PostgreSQL error: {str(e)}'}
    
    def execute_query(self, config_id: str, query: str, db_name: Optional[str] = None) -> Dict:
        """Execute SQL query on the specified database"""
        if config_id not in self.db_configs:
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                return self._execute_mysql_query(config, query, db_name)
            elif db_type == 'postgresql':
                return self._execute_postgresql_query(config, query, db_name)
            else:
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Query execution failed: {str(e)}'}
    
    def _execute_mysql_query(self, config: Dict, query: str, db_name: Optional[str]) -> Dict:
        """Execute MySQL query"""
        import mysql.connector
        from mysql.connector import Error
        
        conn = mysql.connector.connect(
            host=config['host'],
            port=config['port'],
            user=config['username'],
            password=config['password'],
            database=db_name
        )
        
        cursor = conn.cursor(dictionary=True)
        start_time = time.time()
        
        try:
            cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                conn.commit()
                return {
                    'status': 'success',
                    'query_type': 'select',
                    'results': results,
                    'columns': columns,
                    'row_count': len(results),
                    'execution_time': round(time.time() - start_time, 4)
                }
            else:
                affected_rows = cursor.rowcount
                conn.commit()
                return {
                    'status': 'success',
                    'query_type': 'modification',
                    'affected_rows': affected_rows,
                    'execution_time': round(time.time() - start_time, 4)
                }
        finally:
            cursor.close()
            conn.close()
    
    def _execute_postgresql_query(self, config: Dict, query: str, db_name: Optional[str]) -> Dict:
        """Execute PostgreSQL query"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            user=config['username'],
            password=config['password'],
            dbname=db_name or 'postgres'
        )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        start_time = time.time()
        
        try:
            cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                conn.commit()
                return {
                    'status': 'success',
                    'query_type': 'select',
                    'results': results,
                    'columns': columns,
                    'row_count': len(results),
                    'execution_time': round(time.time() - start_time, 4)
                }
            else:
                affected_rows = cursor.rowcount
                conn.commit()
                return {
                    'status': 'success',
                    'query_type': 'modification',
                    'affected_rows': affected_rows,
                    'execution_time': round(time.time() - start_time, 4)
                }
        finally:
            cursor.close()
            conn.close()
    
    def get_databases(self, config_id: str) -> Dict:
        """Get list of databases for the specified configuration"""
        if config_id not in self.db_configs:
            log_system(f"Failed to get databases: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._get_mysql_databases(config)
                if result['status'] == 'success':
                    log_system(f"Retrieved {len(result['databases'])} MySQL databases for {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._get_postgresql_databases(config)
                if result['status'] == 'success':
                    log_system(f"Retrieved {len(result['databases'])} PostgreSQL databases for {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to get databases: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to get databases for {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to get databases: {str(e)}'}
    
    def _get_mysql_databases(self, config: Dict) -> Dict:
        """Get MySQL databases"""
        query = "SHOW DATABASES"
        result = self._execute_mysql_query(config, query, None)
        if result['status'] == 'success':
            databases = [db['Database'] for db in result['results']]
            return {'status': 'success', 'databases': databases}
        return result
    
    def _get_postgresql_databases(self, config: Dict) -> Dict:
        """Get PostgreSQL databases"""
        query = "SELECT datname FROM pg_database WHERE datistemplate = false"
        result = self._execute_postgresql_query(config, query, 'postgres')
        if result['status'] == 'success':
            databases = [db['datname'] for db in result['results']]
            return {'status': 'success', 'databases': databases}
        return result
    
    def get_tables(self, config_id: str, db_name: str) -> Dict:
        """Get list of tables for a specific database"""
        if config_id not in self.db_configs:
            log_system(f"Failed to get tables: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._get_mysql_tables(config, db_name)
                if result['status'] == 'success':
                    log_system(f"Retrieved {len(result['tables'])} MySQL tables from {db_name} for {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._get_postgresql_tables(config, db_name)
                if result['status'] == 'success':
                    log_system(f"Retrieved {len(result['tables'])} PostgreSQL tables from {db_name} for {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to get tables: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to get tables from {db_name} for {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to get tables: {str(e)}'}
    
    def _get_mysql_tables(self, config: Dict, db_name: str) -> Dict:
        """Get MySQL tables"""
        query = "SHOW TABLES"
        result = self._execute_mysql_query(config, query, db_name)
        if result['status'] == 'success':
            tables = [list(db.values())[0] for db in result['results']]
            return {'status': 'success', 'tables': tables}
        return result
    
    def _get_postgresql_tables(self, config: Dict, db_name: str) -> Dict:
        """Get PostgreSQL tables"""
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        result = self._execute_postgresql_query(config, query, db_name)
        if result['status'] == 'success':
            tables = [db['table_name'] for db in result['results']]
            return {'status': 'success', 'tables': tables}
        return result
    
    # -------------------- User Permission Management --------------------
    def get_users(self, config_id: str) -> Dict:
        """Get list of users for the specified database configuration"""
        if config_id not in self.db_configs:
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                return self._get_mysql_users(config)
            elif db_type == 'postgresql':
                return self._get_postgresql_users(config)
            else:
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to get users: {str(e)}'}
    
    def _get_mysql_users(self, config: Dict) -> Dict:
        """Get MySQL users"""
        query = "SELECT user, host FROM mysql.user ORDER BY user"
        result = self._execute_mysql_query(config, query, None)
        if result['status'] == 'success':
            users = [f"{row['user']}@{row['host']}" for row in result['results']]
            return {'status': 'success', 'users': users}
        return result
    
    def _get_postgresql_users(self, config: Dict) -> Dict:
        """Get PostgreSQL users"""
        query = "SELECT usename FROM pg_user ORDER BY usename"
        result = self._execute_postgresql_query(config, query, 'postgres')
        if result['status'] == 'success':
            users = [row['usename'] for row in result['results']]
            return {'status': 'success', 'users': users}
        return result
    
    def create_user(self, config_id: str, username: str, password: str, db_name: Optional[str] = None) -> Dict:
        """Create a new database user"""
        if config_id not in self.db_configs:
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                return self._create_mysql_user(config, username, password)
            elif db_type == 'postgresql':
                return self._create_postgresql_user(config, username, password)
            else:
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to create user: {str(e)}'}
    
    def _create_mysql_user(self, config: Dict, username: str, password: str) -> Dict:
        """Create MySQL user"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password']
            )
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            query = "CREATE USER %s@'%%' IDENTIFIED BY %s"
            cursor.execute(query, (username, password))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'User {username} created successfully'}
        except Error as e:
            return {'status': 'error', 'message': f'MySQL error: {str(e)}'}
    
    def _create_postgresql_user(self, config: Dict, username: str, password: str) -> Dict:
        """Create PostgreSQL user"""
        import psycopg2
        from psycopg2 import OperationalError
        
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password'],
                dbname='postgres'
            )
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            query = "CREATE USER %s WITH PASSWORD %s"
            cursor.execute(query, (username, password))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'User {username} created successfully'}
        except OperationalError as e:
            return {'status': 'error', 'message': f'PostgreSQL error: {str(e)}'}
    
    def grant_permissions(self, config_id: str, username: str, db_name: str, permissions: List[str], table_name: Optional[str] = None) -> Dict:
        """Grant permissions to a user"""
        if config_id not in self.db_configs:
            log_system(f"Failed to grant permissions to {username}: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._grant_mysql_permissions(config, username, db_name, permissions, table_name)
                if result['status'] == 'success':
                    log_system(f"Granted permissions {', '.join(permissions)} to MySQL user {username} on {db_name}.{table_name or '*'} for {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._grant_postgresql_permissions(config, username, db_name, permissions, table_name)
                if result['status'] == 'success':
                    log_system(f"Granted permissions {', '.join(permissions)} to PostgreSQL user {username} on {db_name}.{table_name or '*'} for {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to grant permissions to {username}: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to grant permissions to {username} on {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to grant permissions: {str(e)}'}
    
    def _grant_mysql_permissions(self, config: Dict, username: str, db_name: str, permissions: List[str], table_name: Optional[str] = None) -> Dict:
        """Grant MySQL permissions"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password']
            )
            cursor = conn.cursor()
            # 验证权限名称，只允许特定的权限
            valid_permissions = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'INDEX', 'ALTER', 'ALL PRIVILEGES']
            safe_permissions = [p.upper() for p in permissions if p.upper() in valid_permissions]
            if not safe_permissions:
                return {'status': 'error', 'message': 'No valid permissions provided'}
            
            permissions_str = ', '.join(safe_permissions)
            # 对数据库名和表名进行转义处理
            safe_db_name = db_name.replace('`', '``')
            if table_name:
                safe_table_name = table_name.replace('`', '``')
                target = f"`{safe_db_name}`.`{safe_table_name}`"
            else:
                target = f"`{safe_db_name}`.*"
            
            query = f"GRANT {permissions_str} ON {target} TO %s@'%%'"
            cursor.execute(query, (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'Permissions granted successfully'}
        except Error as e:
            return {'status': 'error', 'message': f'MySQL error: {str(e)}'}
    
    def _grant_postgresql_permissions(self, config: Dict, username: str, db_name: str, permissions: List[str], table_name: Optional[str] = None) -> Dict:
        """Grant PostgreSQL permissions"""
        import psycopg2
        from psycopg2 import OperationalError
        
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password'],
                dbname=db_name
            )
            cursor = conn.cursor()
            # 验证权限名称
            valid_permissions = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER', 'ALL']
            safe_permissions = [p.upper() for p in permissions if p.upper() in valid_permissions]
            if not safe_permissions:
                return {'status': 'error', 'message': 'No valid permissions provided'}
            
            permissions_str = ', '.join(safe_permissions)
            
            if table_name:
                # 对表名进行转义
                safe_table_name = table_name.replace('"', '""')
                query = f'GRANT {permissions_str} ON "{safe_table_name}" TO %s'
            else:
                query = f'GRANT {permissions_str} ON ALL TABLES IN SCHEMA public TO %s'
            
            cursor.execute(query, (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'Permissions granted successfully'}
        except OperationalError as e:
            return {'status': 'error', 'message': f'PostgreSQL error: {str(e)}'}
    
    def revoke_permissions(self, config_id: str, username: str, db_name: str, permissions: List[str], table_name: Optional[str] = None) -> Dict:
        """Revoke permissions from a user"""
        if config_id not in self.db_configs:
            log_system(f"Failed to revoke permissions from {username}: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._revoke_mysql_permissions(config, username, db_name, permissions, table_name)
                if result['status'] == 'success':
                    log_system(f"Revoked permissions {', '.join(permissions)} from MySQL user {username} on {db_name}.{table_name or '*'} for {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._revoke_postgresql_permissions(config, username, db_name, permissions, table_name)
                if result['status'] == 'success':
                    log_system(f"Revoked permissions {', '.join(permissions)} from PostgreSQL user {username} on {db_name}.{table_name or '*'} for {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to revoke permissions from {username}: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to revoke permissions from {username} on {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to revoke permissions: {str(e)}'}
    
    def _revoke_mysql_permissions(self, config: Dict, username: str, db_name: str, permissions: List[str], table_name: Optional[str] = None) -> Dict:
        """Revoke MySQL permissions"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password']
            )
            cursor = conn.cursor()
            # 验证权限名称
            valid_permissions = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'INDEX', 'ALTER', 'ALL PRIVILEGES']
            safe_permissions = [p.upper() for p in permissions if p.upper() in valid_permissions]
            if not safe_permissions:
                return {'status': 'error', 'message': 'No valid permissions provided'}
            
            permissions_str = ', '.join(safe_permissions)
            # 对数据库名和表名进行转义处理
            safe_db_name = db_name.replace('`', '``')
            if table_name:
                safe_table_name = table_name.replace('`', '``')
                target = f"`{safe_db_name}`.`{safe_table_name}`"
            else:
                target = f"`{safe_db_name}`.*"
            
            query = f"REVOKE {permissions_str} ON {target} FROM %s@'%%'"
            cursor.execute(query, (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'Permissions revoked successfully'}
        except Error as e:
            return {'status': 'error', 'message': f'MySQL error: {str(e)}'}
    
    def _revoke_postgresql_permissions(self, config: Dict, username: str, db_name: str, permissions: List[str], table_name: Optional[str] = None) -> Dict:
        """Revoke PostgreSQL permissions"""
        import psycopg2
        from psycopg2 import OperationalError
        
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password'],
                dbname=db_name
            )
            cursor = conn.cursor()
            # 验证权限名称
            valid_permissions = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER', 'ALL']
            safe_permissions = [p.upper() for p in permissions if p.upper() in valid_permissions]
            if not safe_permissions:
                return {'status': 'error', 'message': 'No valid permissions provided'}
            
            permissions_str = ', '.join(safe_permissions)
            
            if table_name:
                # 对表名进行转义
                safe_table_name = table_name.replace('"', '""')
                query = f'REVOKE {permissions_str} ON "{safe_table_name}" FROM %s'
            else:
                query = f'REVOKE {permissions_str} ON ALL TABLES IN SCHEMA public FROM %s'
            
            cursor.execute(query, (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'Permissions revoked successfully'}
        except OperationalError as e:
            return {'status': 'error', 'message': f'PostgreSQL error: {str(e)}'}
    
    def get_user_permissions(self, config_id: str, username: str, db_name: str) -> Dict:
        """Get permissions for a user"""
        if config_id not in self.db_configs:
            log_system(f"Failed to get permissions for {username}: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._get_mysql_user_permissions(config, username, db_name)
                if result['status'] == 'success':
                    log_system(f"Retrieved permissions for MySQL user {username} on {db_name} for {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._get_postgresql_user_permissions(config, username, db_name)
                if result['status'] == 'success':
                    log_system(f"Retrieved permissions for PostgreSQL user {username} on {db_name} for {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to get permissions for {username}: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to get permissions for {username} on {db_name} for {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to get user permissions: {str(e)}'}
    
    def _validate_db_identifier(self, identifier: str) -> bool:
        """验证数据库标识符是否安全（只允许字母、数字、下划线）"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_]+$', identifier))

    def _get_mysql_user_permissions(self, config: Dict, username: str, db_name: str) -> Dict:
        """Get MySQL user permissions"""
        # 验证输入参数
        if not self._validate_db_identifier(username):
            return {'status': 'error', 'message': 'Invalid username format'}
        if not self._validate_db_identifier(db_name):
            return {'status': 'error', 'message': 'Invalid database name format'}

        query = f"SHOW GRANTS FOR '{username}'@'%' ON `{db_name}`.*"
        result = self._execute_mysql_query(config, query, None)
        if result['status'] == 'success':
            grants = [list(row.values())[0] for row in result['results']]
            return {'status': 'success', 'grants': grants}
        return result

    def _get_postgresql_user_permissions(self, config: Dict, username: str, db_name: str) -> Dict:
        """Get PostgreSQL user permissions"""
        # 验证输入参数
        if not self._validate_db_identifier(username):
            return {'status': 'error', 'message': 'Invalid username format'}

        # PostgreSQL: 使用参数化查询获取权限
        query = """
            SELECT table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = %s AND table_schema = 'public'
        """
        result = self._execute_postgresql_query(config, query, db_name, params=(username,))
        if result['status'] == 'success':
            permissions = []
            for row in result['results']:
                permissions.append(f"{row['privilege_type']} ON {row['table_name']}")
            return {'status': 'success', 'permissions': permissions}
        return result
    
    def delete_user(self, config_id: str, username: str) -> Dict:
        """Delete a database user"""
        if config_id not in self.db_configs:
            log_system(f"Failed to delete user {username}: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._delete_mysql_user(config, username)
                if result['status'] == 'success':
                    log_system(f"Deleted MySQL user {username} from {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._delete_postgresql_user(config, username)
                if result['status'] == 'success':
                    log_system(f"Deleted PostgreSQL user {username} from {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to delete user {username}: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to delete user {username} from {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to delete user: {str(e)}'}
    
    def _delete_mysql_user(self, config: Dict, username: str) -> Dict:
        """Delete MySQL user"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password']
            )
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            query = "DROP USER %s@'%%'"
            cursor.execute(query, (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'User {username} deleted successfully'}
        except Error as e:
            return {'status': 'error', 'message': f'MySQL error: {str(e)}'}
    
    def _delete_postgresql_user(self, config: Dict, username: str) -> Dict:
        """Delete PostgreSQL user"""
        import psycopg2
        from psycopg2 import OperationalError
        
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password'],
                dbname='postgres'
            )
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            query = "DROP USER %s"
            cursor.execute(query, (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'User {username} deleted successfully'}
        except OperationalError as e:
            return {'status': 'error', 'message': f'PostgreSQL error: {str(e)}'}
    
    def change_user_password(self, config_id: str, username: str, new_password: str) -> Dict:
        """Change user password"""
        if config_id not in self.db_configs:
            log_system(f"Failed to change password for {username}: DB config {config_id} not found", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Database configuration {config_id} not found'}
        
        config = self.db_configs[config_id]
        db_type = config['db_type']
        
        try:
            if db_type == 'mysql':
                result = self._change_mysql_user_password(config, username, new_password)
                if result['status'] == 'success':
                    log_system(f"Changed password for MySQL user {username} on {config_id}", level='INFO', name='db_manager')
                return result
            elif db_type == 'postgresql':
                result = self._change_postgresql_user_password(config, username, new_password)
                if result['status'] == 'success':
                    log_system(f"Changed password for PostgreSQL user {username} on {config_id}", level='INFO', name='db_manager')
                return result
            else:
                log_system(f"Failed to change password for {username}: Unsupported DB type {db_type}", level='ERROR', name='db_manager')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
        except Exception as e:
            log_system(f"Failed to change password for {username} on {config_id}: {str(e)}", level='ERROR', name='db_manager')
            return {'status': 'error', 'message': f'Failed to change password: {str(e)}'}
    
    def _change_mysql_user_password(self, config: Dict, username: str, new_password: str) -> Dict:
        """Change MySQL user password"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password']
            )
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            query = "ALTER USER %s@'%%' IDENTIFIED BY %s"
            cursor.execute(query, (username, new_password))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'Password changed successfully for user {username}'}
        except Error as e:
            return {'status': 'error', 'message': f'MySQL error: {str(e)}'}
    
    def _change_postgresql_user_password(self, config: Dict, username: str, new_password: str) -> Dict:
        """Change PostgreSQL user password"""
        import psycopg2
        from psycopg2 import OperationalError
        
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=config['password'],
                dbname='postgres'
            )
            cursor = conn.cursor()
            # 使用参数化查询防止SQL注入
            query = "ALTER USER %s WITH PASSWORD %s"
            cursor.execute(query, (username, new_password))
            conn.commit()
            cursor.close()
            conn.close()
            return {'status': 'success', 'message': f'Password changed successfully for user {username}'}
        except OperationalError as e:
            return {'status': 'error', 'message': f'PostgreSQL error: {str(e)}'}

# Singleton instance
db_manager = DatabaseManager()

# Initialize backup manager with the db_manager instance
from .db_backup import BackupManager
backup_manager = BackupManager(db_manager)

# Initialize database monitor with the db_manager instance
from .db_monitor import DBMonitor
db_monitor = DBMonitor(db_manager)