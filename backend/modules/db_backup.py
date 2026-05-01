import json
import os
import subprocess
import time
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from croniter import croniter

from .log_manager import log_system

# Backup configurations and data files
BACKUP_CONFIGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backup_configs.json')
BACKUP_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backup_history.json')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backups')

class BackupManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.backup_configs = self._load_backup_configs()
        self.backup_history = self._load_backup_history()
        self.supported_backup_types = ['full', 'incremental', 'differential']
        self.supported_schedules = ['daily', 'weekly', 'monthly']
        
        # Ensure backup directory exists
        os.makedirs(BACKUP_DIR, exist_ok=True)
    
    def _load_backup_configs(self) -> Dict:
        """Load backup configurations from file"""
        if not os.path.exists(BACKUP_CONFIGS_FILE):
            # Ensure data directory exists
            os.makedirs(os.path.dirname(BACKUP_CONFIGS_FILE), exist_ok=True)
            with open(BACKUP_CONFIGS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        
        with open(BACKUP_CONFIGS_FILE, 'r') as f:
            return json.load(f)
    
    def _save_backup_configs(self) -> None:
        """Save backup configurations to file"""
        with open(BACKUP_CONFIGS_FILE, 'w') as f:
            json.dump(self.backup_configs, f, indent=2)
    
    def _load_backup_history(self) -> Dict:
        """Load backup history from file"""
        if not os.path.exists(BACKUP_HISTORY_FILE):
            with open(BACKUP_HISTORY_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        
        with open(BACKUP_HISTORY_FILE, 'r') as f:
            return json.load(f)
    
    def _save_backup_history(self) -> None:
        """Save backup history to file"""
        with open(BACKUP_HISTORY_FILE, 'w') as f:
            json.dump(self.backup_history, f, indent=2)
    
    def add_backup_config(self, config_id: str, db_config_id: str, db_name: str, backup_type: str, schedule: str, 
                          retention_days: int, compression: bool = True, description: str = '') -> Dict:
        """Add a new backup configuration"""
        if backup_type not in self.supported_backup_types:
            log_system(f"Failed to add backup config {config_id}: Unsupported backup type {backup_type}", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Unsupported backup type: {backup_type}'}
        
        if schedule not in self.supported_schedules:
            log_system(f"Failed to add backup config {config_id}: Unsupported schedule {schedule}", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Unsupported schedule: {schedule}'}
        
        if config_id in self.backup_configs:
            log_system(f"Failed to add backup config {config_id}: Configuration already exists", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup configuration {config_id} already exists'}
        
        # Generate cron expression based on schedule
        cron_expr = self._generate_cron_expression(schedule)
        
        self.backup_configs[config_id] = {
            'db_config_id': db_config_id,
            'db_name': db_name,
            'backup_type': backup_type,
            'schedule': schedule,
            'cron_expr': cron_expr,
            'retention_days': retention_days,
            'compression': compression,
            'description': description,
            'enabled': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self._save_backup_configs()
        log_system(f"Added backup config {config_id}: {db_name} ({backup_type}, {schedule})", level='INFO', name='db_backup')
        return {'status': 'success', 'message': f'Backup configuration {config_id} added successfully'}
    
    def _generate_cron_expression(self, schedule: str) -> str:
        """Generate cron expression based on schedule type"""
        if schedule == 'daily':
            return '0 2 * * *'  # Daily at 2 AM
        elif schedule == 'weekly':
            return '0 2 * * 0'  # Weekly on Sunday at 2 AM
        elif schedule == 'monthly':
            return '0 2 1 * *'  # Monthly on 1st at 2 AM
        return '0 2 * * *'  # Default to daily
    
    def update_backup_config(self, config_id: str, updates: Dict) -> Dict:
        """Update an existing backup configuration"""
        if config_id not in self.backup_configs:
            log_system(f"Failed to update backup config: {config_id} not found", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup configuration {config_id} not found'}
        
        # Only allow updating certain fields
        allowed_fields = ['backup_type', 'schedule', 'retention_days', 'compression', 'description', 'enabled']
        updated_fields = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                updated_fields.append(field)
                if field == 'schedule':
                    # Update cron expression when schedule changes
                    self.backup_configs[config_id]['cron_expr'] = self._generate_cron_expression(value)
                self.backup_configs[config_id][field] = value
        
        self.backup_configs[config_id]['updated_at'] = datetime.now().isoformat()
        self._save_backup_configs()
        log_system(f"Updated backup config {config_id} (Fields: {', '.join(updated_fields)})", level='INFO', name='db_backup')
        return {'status': 'success', 'message': f'Backup configuration {config_id} updated successfully'}
    
    def delete_backup_config(self, config_id: str) -> Dict:
        """Delete a backup configuration"""
        if config_id not in self.backup_configs:
            log_system(f"Failed to delete backup config: {config_id} not found", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup configuration {config_id} not found'}
        
        config = self.backup_configs[config_id]
        del self.backup_configs[config_id]
        self._save_backup_configs()
        log_system(f"Deleted backup config {config_id}: {config['db_name']} ({config['backup_type']})", level='INFO', name='db_backup')
        return {'status': 'success', 'message': f'Backup configuration {config_id} deleted successfully'}
    
    def get_backup_configs(self) -> Dict:
        """Get all backup configurations"""
        return {'status': 'success', 'configs': self.backup_configs}
    
    def get_backup_config(self, config_id: str) -> Dict:
        """Get a specific backup configuration"""
        if config_id not in self.backup_configs:
            return {'status': 'error', 'message': f'Backup configuration {config_id} not found'}
        
        return {'status': 'success', 'config': self.backup_configs[config_id]}
    
    def trigger_backup(self, config_id: str, backup_type: Optional[str] = None) -> Dict:
        """Trigger manual backup for a configuration"""
        if config_id not in self.backup_configs:
            log_system(f"Failed to trigger backup: {config_id} not found", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup configuration {config_id} not found'}
        
        config = self.backup_configs[config_id]
        actual_backup_type = backup_type or config['backup_type']
        
        # Validate backup type
        if actual_backup_type not in self.supported_backup_types:
            log_system(f"Failed to trigger backup for {config_id}: Unsupported backup type {actual_backup_type}", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Unsupported backup type: {actual_backup_type}'}
        
        log_system(f"Triggering manual backup for {config_id}: {config['db_name']} ({actual_backup_type})")
        try:
            backup_result = self._perform_backup(config, actual_backup_type)
            return backup_result
        except Exception as e:
            log_system(f"Manual backup failed for {config_id}: {str(e)}", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup failed: {str(e)}'}
    
    def _perform_backup(self, config: Dict, backup_type: str) -> Dict:
        """Perform actual backup operation"""
        db_config_id = config['db_config_id']
        db_name = config['db_name']
        compression = config['compression']
        
        # Get database configuration
        db_config_result = self.db_manager.get_db_config(db_config_id)
        if db_config_result['status'] != 'success':
            return db_config_result
        
        db_config = db_config_result['config']
        db_type = db_config['db_type']
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{db_type}_{db_name}_{backup_type}_{timestamp}"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        start_time = datetime.now()
        log_system(f"Starting backup for {db_name} ({db_type}, {backup_type}) at {start_time.isoformat()}", level='INFO', name='db_backup')
        
        try:
            if db_type == 'mysql':
                backup_file = self._backup_mysql(db_config, db_name, backup_path, compression, backup_type)
            elif db_type == 'postgresql':
                backup_file = self._backup_postgresql(db_config, db_name, backup_path, compression, backup_type)
            else:
                log_system(f"Unsupported database type {db_type} for backup", level='ERROR', name='db_backup')
                return {'status': 'error', 'message': f'Unsupported database type: {db_type}'}
            
            # Calculate backup size
            backup_size = os.path.getsize(backup_file)
            
            # Calculate checksum for integrity verification
            checksum = self._calculate_checksum(backup_file)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Record backup in history
            backup_id = f"backup_{timestamp}_{hashlib.md5(backup_file.encode()).hexdigest()[:8]}"
            self.backup_history[backup_id] = {
                'backup_id': backup_id,
                'db_config_id': db_config_id,
                'db_name': db_name,
                'db_type': db_type,
                'backup_type': backup_type,
                'filename': os.path.basename(backup_file),
                'path': backup_file,
                'size': backup_size,
                'checksum': checksum,
                'compression': compression,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': round(duration, 2),
                'status': 'success'
            }
            
            self._save_backup_history()
            
            # Apply retention policy
            self._apply_retention_policy(config)
            
            log_system(f"Backup completed successfully for {db_name} ({db_type}, {backup_type}): {backup_id}, Size: {backup_size} bytes, Duration: {round(duration, 2)}s", level='INFO', name='db_backup')
            return {
                'status': 'success',
                'message': f'Backup completed successfully',
                'backup_id': backup_id,
                'filename': os.path.basename(backup_file),
                'size': backup_size,
                'duration': round(duration, 2)
            }
        except Exception as e:
            # Record failed backup in history
            backup_id = f"backup_{timestamp}_{hashlib.md5(str(e).encode()).hexdigest()[:8]}"
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.backup_history[backup_id] = {
                'backup_id': backup_id,
                'db_config_id': db_config_id,
                'db_name': db_name,
                'db_type': db_type,
                'backup_type': backup_type,
                'filename': backup_filename,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': round(duration, 2),
                'status': 'failed',
                'error': str(e)
            }
            
            self._save_backup_history()
            log_system(f"Backup failed for {db_name} ({db_type}, {backup_type}): {str(e)}", level='ERROR', name='db_backup')
            raise
    
    def _backup_mysql(self, config: Dict, db_name: str, backup_path: str, compression: bool, backup_type: str) -> str:
        """Perform MySQL backup"""
        # For MySQL, incremental and differential backups require binary logging
        # For simplicity, we'll use mysqldump for full backups
        # In production, you'd use mysqlbinlog for incremental backups
        
        backup_file = f"{backup_path}.sql"
        if compression:
            backup_file = f"{backup_file}.gz"
        
        # Build mysqldump command
        cmd = [
            'mysqldump',
            '--host', config['host'],
            '--port', str(config['port']),
            '--user', config['username'],
            '--password=' + config['password'],
            '--single-transaction',
            '--quick',
            '--lock-tables=false'
        ]
        
        if backup_type == 'full':
            cmd.append(db_name)
        else:
            # For incremental/differential, we'd need to handle binary logs
            # This is a simplified implementation
            cmd.append(db_name)
        
        if compression:
            cmd.extend(['|', 'gzip', '>', backup_file])
            full_cmd = ' '.join(cmd)
            subprocess.run(full_cmd, shell=True, check=True)
        else:
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
        
        return backup_file
    
    def _backup_postgresql(self, config: Dict, db_name: str, backup_path: str, compression: bool, backup_type: str) -> str:
        """Perform PostgreSQL backup"""
        backup_file = f"{backup_path}.sql"
        if compression:
            backup_file = f"{backup_file}.gz"
        
        # Set PGPASSWORD environment variable for authentication
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--host', config['host'],
            '--port', str(config['port']),
            '--username', config['username'],
            '--dbname', db_name,
            '--format', 'plain'
        ]
        
        if backup_type == 'full':
            pass  # Full backup by default
        elif backup_type == 'incremental':
            # PostgreSQL incremental backup requires wal_level = replica or higher
            cmd.extend(['--no-create-db', '--no-create-info'])
        elif backup_type == 'differential':
            # Differential backup implementation
            cmd.extend(['--no-create-db'])
        
        if compression:
            cmd.extend(['|', 'gzip', '>', backup_file])
            full_cmd = ' '.join(cmd)
            subprocess.run(full_cmd, shell=True, env=env, check=True)
        else:
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, env=env, check=True)
        
        return backup_file
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum for a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def verify_backup(self, backup_id: str) -> Dict:
        """Verify backup integrity by checking checksum"""
        if backup_id not in self.backup_history:
            log_system(f"Failed to verify backup: {backup_id} not found", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup {backup_id} not found'}
        
        backup = self.backup_history[backup_id]
        backup_file = backup['path']
        
        if not os.path.exists(backup_file):
            log_system(f"Backup file {backup_file} not found for verification", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup file {backup_file} not found'}
        
        log_system(f"Verifying backup integrity for {backup_id}", level='INFO', name='db_backup')
        try:
            calculated_checksum = self._calculate_checksum(backup_file)
            if calculated_checksum == backup['checksum']:
                log_system(f"Backup {backup_id} integrity verification passed", level='INFO', name='db_backup')
                return {
                    'status': 'success',
                    'message': 'Backup integrity verified successfully',
                    'backup_id': backup_id,
                    'expected_checksum': backup['checksum'],
                    'calculated_checksum': calculated_checksum,
                    'verified': True
                }
            else:
                log_system(f"Backup {backup_id} integrity verification failed: checksum mismatch", level='ERROR', name='db_backup')
                return {
                    'status': 'error',
                    'message': 'Backup integrity verification failed - checksum mismatch',
                    'backup_id': backup_id,
                    'expected_checksum': backup['checksum'],
                    'calculated_checksum': calculated_checksum,
                    'verified': False
                }
        except Exception as e:
            log_system(f"Backup verification failed for {backup_id}: {str(e)}", level='ERROR', name='db_backup')
            return {
                'status': 'error',
                'message': f'Backup verification failed: {str(e)}',
                'backup_id': backup_id
            }
    
    def restore_backup(self, backup_id: str, target_config_id: Optional[str] = None, target_db_name: Optional[str] = None) -> Dict:
        """Restore backup to original or alternate database"""
        if backup_id not in self.backup_history:
            log_system(f"Failed to restore backup: {backup_id} not found", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup {backup_id} not found'}
        
        backup = self.backup_history[backup_id]
        if backup['status'] != 'success':
            log_system(f"Cannot restore failed backup {backup_id}", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Cannot restore failed backup {backup_id}'}
        
        backup_file = backup['path']
        if not os.path.exists(backup_file):
            log_system(f"Backup file {backup_file} not found for restore", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup file {backup_file} not found'}
        
        # Determine target database configuration
        if target_config_id:
            # Restore to alternate database
            target_db_config_result = self.db_manager.get_db_config(target_config_id)
            if target_db_config_result['status'] != 'success':
                return target_db_config_result
            target_db_config = target_db_config_result['config']
            actual_db_name = target_db_name or backup['db_name']
        else:
            # Restore to original database
            target_db_config_result = self.db_manager.get_db_config(backup['db_config_id'])
            if target_db_config_result['status'] != 'success':
                return target_db_config_result
            target_db_config = target_db_config_result['config']
            actual_db_name = backup['db_name']
        
        log_system(f"Starting restore of backup {backup_id} to {actual_db_name} at {datetime.now().isoformat()}", level='INFO', name='db_backup')
        try:
            start_time = datetime.now()
            
            if backup['db_type'] == 'mysql':
                self._restore_mysql(target_db_config, actual_db_name, backup_file, backup['compression'])
            elif backup['db_type'] == 'postgresql':
                self._restore_postgresql(target_db_config, actual_db_name, backup_file, backup['compression'])
            else:
                log_system(f"Unsupported database type {backup['db_type']} for restore", level='ERROR', name='db_backup')
                return {'status': 'error', 'message': f'Unsupported database type: {backup["db_type"]}'}
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_system(f"Restore completed successfully for backup {backup_id} to {actual_db_name} in {round(duration, 2)}s", level='INFO', name='db_backup')
            return {
                'status': 'success',
                'message': f'Backup {backup_id} restored successfully',
                'backup_id': backup_id,
                'target_config_id': target_config_id or backup['db_config_id'],
                'target_db_name': actual_db_name,
                'duration': round(duration, 2)
            }
        except Exception as e:
            log_system(f"Restore failed for backup {backup_id}: {str(e)}", level='ERROR', name='db_backup')
            return {
                'status': 'error',
                'message': f'Restore failed: {str(e)}',
                'backup_id': backup_id
            }
    
    def _restore_mysql(self, db_config: Dict, db_name: str, backup_file: str, compressed: bool) -> None:
        """Restore MySQL backup"""
        # Create database if it doesn't exist
        create_db_cmd = [
            'mysqladmin',
            '--host', db_config['host'],
            '--port', str(db_config['port']),
            '--user', db_config['username'],
            '--password=' + db_config['password'],
            'create', db_name
        ]
        try:
            subprocess.run(create_db_cmd, check=True)
        except subprocess.CalledProcessError:
            # Database might already exist, continue
            pass
        
        # Restore backup
        restore_cmd = [
            'mysql',
            '--host', db_config['host'],
            '--port', str(db_config['port']),
            '--user', db_config['username'],
            '--password=' + db_config['password'],
            db_name
        ]
        
        if compressed:
            with open(backup_file, 'rb') as f:
                gunzip_cmd = ['gzip', '-d', '-c']
                gunzip_proc = subprocess.Popen(gunzip_cmd, stdin=f, stdout=subprocess.PIPE)
                subprocess.run(restore_cmd, stdin=gunzip_proc.stdout, check=True)
        else:
            with open(backup_file, 'r') as f:
                subprocess.run(restore_cmd, stdin=f, check=True)
    
    def _restore_postgresql(self, db_config: Dict, db_name: str, backup_file: str, compressed: bool) -> None:
        """Restore PostgreSQL backup"""
        # Set PGPASSWORD environment variable for authentication
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']
        
        # Create database if it doesn't exist
        create_db_cmd = [
            'createdb',
            '--host', db_config['host'],
            '--port', str(db_config['port']),
            '--username', db_config['username'],
            db_name
        ]
        try:
            subprocess.run(create_db_cmd, env=env, check=True)
        except subprocess.CalledProcessError:
            # Database might already exist, continue
            pass
        
        # Restore backup
        restore_cmd = [
            'psql',
            '--host', db_config['host'],
            '--port', str(db_config['port']),
            '--username', db_config['username'],
            '--dbname', db_name
        ]
        
        if compressed:
            with open(backup_file, 'rb') as f:
                gunzip_cmd = ['gzip', '-d', '-c']
                gunzip_proc = subprocess.Popen(gunzip_cmd, stdin=f, stdout=subprocess.PIPE, env=env)
                subprocess.run(restore_cmd, stdin=gunzip_proc.stdout, env=env, check=True)
        else:
            with open(backup_file, 'r') as f:
                subprocess.run(restore_cmd, stdin=f, env=env, check=True)
    
    def _apply_retention_policy(self, config: Dict) -> None:
        """Apply retention policy to remove old backups"""
        db_config_id = config['db_config_id']
        db_name = config['db_name']
        retention_days = config['retention_days']
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Find backups to delete
        backups_to_delete = []
        for backup_id, backup in self.backup_history.items():
            if (backup['db_config_id'] == db_config_id and 
                backup['db_name'] == db_name and 
                datetime.fromisoformat(backup['start_time']) < cutoff_date):
                backups_to_delete.append(backup_id)
        
        if backups_to_delete:
            log_system(f"Applying retention policy: deleting {len(backups_to_delete)} old backups for {db_name}", level='INFO', name='db_backup')
            # Delete old backups
            for backup_id in backups_to_delete:
                backup = self.backup_history[backup_id]
                if os.path.exists(backup['path']):
                    os.remove(backup['path'])
                del self.backup_history[backup_id]
            
            self._save_backup_history()
    
    def get_backup_history(self, db_config_id: Optional[str] = None, db_name: Optional[str] = None) -> Dict:
        """Get backup history, optionally filtered by database"""
        if not db_config_id and not db_name:
            return {'status': 'success', 'history': list(self.backup_history.values())}
        
        filtered_history = []
        for backup in self.backup_history.values():
            if ((not db_config_id or backup['db_config_id'] == db_config_id) and 
                (not db_name or backup['db_name'] == db_name)):
                filtered_history.append(backup)
        
        return {'status': 'success', 'history': filtered_history}
    
    def get_backup_info(self, backup_id: str) -> Dict:
        """Get detailed information about a specific backup"""
        if backup_id not in self.backup_history:
            return {'status': 'error', 'message': f'Backup {backup_id} not found'}
        
        return {'status': 'success', 'backup': self.backup_history[backup_id]}
    
    def delete_backup(self, backup_id: str) -> Dict:
        """Delete a specific backup"""
        if backup_id not in self.backup_history:
            log_system(f"Failed to delete backup: {backup_id} not found", level='ERROR', name='db_backup')
            return {'status': 'error', 'message': f'Backup {backup_id} not found'}
        
        backup = self.backup_history[backup_id]
        if os.path.exists(backup['path']):
            os.remove(backup['path'])
        
        del self.backup_history[backup_id]
        self._save_backup_history()
        
        log_system(f"Deleted backup {backup_id}: {backup['filename']}", level='INFO', name='db_backup')
        return {'status': 'success', 'message': f'Backup {backup_id} deleted successfully'}
    
    def get_scheduled_backups(self) -> Dict:
        """Get list of scheduled backups that need to be run"""
        now = datetime.now()
        scheduled_backups = []
        
        for config_id, config in self.backup_configs.items():
            if not config['enabled']:
                continue
            
            cron = croniter(config['cron_expr'], now)
            next_run = cron.get_prev(datetime)
            
            # Check if backup should have run in the last 5 minutes
            if (now - next_run).total_seconds() < 300:
                scheduled_backups.append({
                    'config_id': config_id,
                    'backup_config': config,
                    'scheduled_time': next_run.isoformat()
                })
        
        return {'status': 'success', 'scheduled_backups': scheduled_backups}

