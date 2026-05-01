import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3

from .log_manager import log_system

# Monitoring configurations and data files
MONITOR_CONFIGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor_configs.json')
MONITOR_DATA_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor_data.db')

class DBMonitor:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.monitor_configs = self._load_monitor_configs()
        self.metrics_history = {}
        self.alert_thresholds = {}
        self.running_monitors = {}
        
        # Initialize monitoring database
        self._init_monitor_db()
    
    def _load_monitor_configs(self) -> Dict:
        """Load monitoring configurations from file"""
        if not os.path.exists(MONITOR_CONFIGS_FILE):
            # Ensure data directory exists
            os.makedirs(os.path.dirname(MONITOR_CONFIGS_FILE), exist_ok=True)
            with open(MONITOR_CONFIGS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        
        with open(MONITOR_CONFIGS_FILE, 'r') as f:
            return json.load(f)
    
    def _save_monitor_configs(self) -> None:
        """Save monitoring configurations to file"""
        with open(MONITOR_CONFIGS_FILE, 'w') as f:
            json.dump(self.monitor_configs, f, indent=2)
    
    def _init_monitor_db(self) -> None:
        """Initialize SQLite database for storing monitoring data"""
        conn = sqlite3.connect(MONITOR_DATA_DB)
        cursor = conn.cursor()
        
        # Create tables for metrics history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                db_config_id TEXT NOT NULL,
                db_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT
            )
        ''')
        
        # Create table for slow queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS slow_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                db_config_id TEXT NOT NULL,
                db_name TEXT NOT NULL,
                query_text TEXT NOT NULL,
                execution_time REAL NOT NULL,
                rows_affected INTEGER,
                lock_time REAL,
                index_usage TEXT
            )
        ''')
        
        # Create table for alerts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                db_config_id TEXT NOT NULL,
                db_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                current_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                status TEXT DEFAULT 'active',
                resolved_at DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_monitor_config(self, config_id: str, db_config_id: str, db_name: str, metrics: List[str], 
                          collection_interval: int = 60, alert_enabled: bool = True, description: str = '') -> Dict:
        """Add a new monitoring configuration"""
        if config_id in self.monitor_configs:
            log_system(f"Failed to add monitor config {config_id}: Configuration already exists", level='ERROR', name='db_monitor')
            return {'status': 'error', 'message': f'Monitoring configuration {config_id} already exists'}
        
        # Validate metrics
        valid_metrics = self._get_valid_metrics()
        for metric in metrics:
            if metric not in valid_metrics:
                log_system(f"Failed to add monitor config {config_id}: Invalid metric {metric}", level='ERROR', name='db_monitor')
                return {'status': 'error', 'message': f'Invalid metric: {metric}'}
        
        self.monitor_configs[config_id] = {
            'db_config_id': db_config_id,
            'db_name': db_name,
            'metrics': metrics,
            'collection_interval': collection_interval,
            'alert_enabled': alert_enabled,
            'description': description,
            'enabled': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self._save_monitor_configs()
        log_system(f"Added monitor config {config_id}: Monitoring {db_name} with metrics {', '.join(metrics)}", level='INFO', name='db_monitor')
        return {'status': 'success', 'message': f'Monitoring configuration {config_id} added successfully'}
    
    def _get_valid_metrics(self) -> List[str]:
        """Get list of valid metrics that can be monitored"""
        return [
            'query_execution_time',
            'connection_count',
            'cpu_usage',
            'memory_usage',
            'disk_io',
            'lock_contention',
            'slow_queries_count',
            'buffer_pool_hit_rate',
            'index_usage',
            'query_count',
            'table_scans',
            'deadlocks',
            'open_files',
            'threads_running',
            'buffer_pool_usage',
            'cache_hit_rate',
            'network_traffic'
        ]
    
    def update_monitor_config(self, config_id: str, updates: Dict) -> Dict:
        """Update an existing monitoring configuration"""
        if config_id not in self.monitor_configs:
            log_system(f"Failed to update monitor config: {config_id} not found", level='ERROR', name='db_monitor')
            return {'status': 'error', 'message': f'Monitoring configuration {config_id} not found'}
        
        # Only allow updating certain fields
        allowed_fields = ['metrics', 'collection_interval', 'alert_enabled', 'description', 'enabled']
        updated_fields = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                updated_fields.append(field)
                if field == 'metrics':
                    # Validate metrics
                    valid_metrics = self._get_valid_metrics()
                    for metric in value:
                        if metric not in valid_metrics:
                            log_system(f"Failed to update monitor config {config_id}: Invalid metric {metric}", level='ERROR', name='db_monitor')
                            return {'status': 'error', 'message': f'Invalid metric: {metric}'}
                self.monitor_configs[config_id][field] = value
        
        self.monitor_configs[config_id]['updated_at'] = datetime.now().isoformat()
        self._save_monitor_configs()
        log_system(f"Updated monitor config {config_id} (Fields: {', '.join(updated_fields)})", level='INFO', name='db_monitor')
        return {'status': 'success', 'message': f'Monitoring configuration {config_id} updated successfully'}
    
    def delete_monitor_config(self, config_id: str) -> Dict:
        """Delete a monitoring configuration"""
        if config_id not in self.monitor_configs:
            log_system(f"Failed to delete monitor config: {config_id} not found", level='ERROR', name='db_monitor')
            return {'status': 'error', 'message': f'Monitoring configuration {config_id} not found'}
        
        # Stop monitoring if it's running
        if config_id in self.running_monitors:
            self.stop_monitoring(config_id)
        
        del self.monitor_configs[config_id]
        self._save_monitor_configs()
        log_system(f"Deleted monitor config {config_id}", level='INFO', name='db_monitor')
        return {'status': 'success', 'message': f'Monitoring configuration {config_id} deleted successfully'}
    
    def get_monitor_configs(self) -> Dict:
        """Get all monitoring configurations"""
        return {'status': 'success', 'configs': self.monitor_configs}
    
    def get_monitor_config(self, config_id: str) -> Dict:
        """Get a specific monitoring configuration"""
        if config_id not in self.monitor_configs:
            return {'status': 'error', 'message': f'Monitoring configuration {config_id} not found'}
        
        return {'status': 'success', 'config': self.monitor_configs[config_id]}
    
    def start_monitoring(self, config_id: str) -> Dict:
        """Start monitoring for a configuration"""
        if config_id not in self.monitor_configs:
            log_system(f"Failed to start monitoring: {config_id} not found", level='ERROR', name='db_monitor')
            return {'status': 'error', 'message': f'Monitoring configuration {config_id} not found'}
        
        if config_id in self.running_monitors:
            log_system(f"Failed to start monitoring: {config_id} is already running", level='ERROR', name='db_monitor')
            return {'status': 'error', 'message': f'Monitoring for {config_id} is already running'}
        
        # Create and start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(config_id,),
            daemon=True
        )
        
        self.running_monitors[config_id] = {
            'thread': monitor_thread,
            'stop_event': threading.Event()
        }
        
        monitor_thread.start()
        log_system(f"Started monitoring for {config_id}", level='INFO', name='db_monitor')
        return {'status': 'success', 'message': f'Monitoring started for {config_id}'}
    
    def stop_monitoring(self, config_id: str) -> Dict:
        """Stop monitoring for a configuration"""
        if config_id not in self.running_monitors:
            log_system(f"Failed to stop monitoring: {config_id} is not running", level='ERROR', name='db_monitor')
            return {'status': 'error', 'message': f'Monitoring for {config_id} is not running'}
        
        # Signal thread to stop
        self.running_monitors[config_id]['stop_event'].set()
        
        # Wait for thread to finish (with timeout)
        self.running_monitors[config_id]['thread'].join(timeout=5.0)
        
        # Remove from running monitors
        del self.running_monitors[config_id]
        
        log_system(f"Stopped monitoring for {config_id}", level='INFO', name='db_monitor')
        return {'status': 'success', 'message': f'Monitoring stopped for {config_id}'}
    
    def _monitoring_loop(self, config_id: str) -> None:
        """Main monitoring loop"""
        config = self.monitor_configs[config_id]
        stop_event = self.running_monitors[config_id]['stop_event']
        
        log_system(f"Entering monitoring loop for {config_id}", level='DEBUG', name='db_monitor')
        
        while not stop_event.is_set() and config.get('enabled', True):
            try:
                # Collect metrics
                metrics_data = self._collect_metrics(config)
                
                # Store metrics
                self._store_metrics(config_id, metrics_data)
                
                # Check alerts
                if config.get('alert_enabled', True):
                    self._check_alerts(config_id, metrics_data)
                
                # Sleep for collection interval
                stop_event.wait(config['collection_interval'])
            except Exception as e:
                # Log error but continue monitoring
                self._log_monitor_error(config_id, str(e))
                time.sleep(10)  # Short sleep before retrying
        
        log_system(f"Exiting monitoring loop for {config_id}", level='DEBUG', name='db_monitor')
    
    def _collect_metrics(self, config: Dict) -> Dict:
        """Collect metrics for a specific database"""
        db_config_id = config['db_config_id']
        db_name = config['db_name']
        metrics = config['metrics']
        
        # Get database configuration
        db_config_result = self.db_manager.get_db_config(db_config_id)
        if db_config_result['status'] != 'success':
            log_system(f"Failed to get DB config {db_config_id} for metrics collection", level='ERROR', name='db_monitor')
            return {}
        
        db_config = db_config_result['config']
        db_type = db_config['db_type']
        
        collected_metrics = {
            'timestamp': datetime.now().isoformat(),
            'db_config_id': db_config_id,
            'db_name': db_name,
            'metrics': {}
        }
        
        try:
            if db_type == 'mysql':
                collected_metrics['metrics'] = self._collect_mysql_metrics(db_config, db_name, metrics)
            elif db_type == 'postgresql':
                collected_metrics['metrics'] = self._collect_postgresql_metrics(db_config, db_name, metrics)
            else:
                log_system(f"Unsupported DB type {db_type} for metrics collection", level='ERROR', name='db_monitor')
        except Exception as e:
            log_system(f"Error collecting metrics for {db_name}: {str(e)}", level='ERROR', name='db_monitor')
        
        # Also collect slow queries if enabled
        if 'slow_queries_count' in metrics:
            try:
                slow_queries = self._collect_slow_queries(db_config, db_name, db_type)
                collected_metrics['slow_queries'] = slow_queries
                if slow_queries:
                    log_system(f"Collected {len(slow_queries)} slow queries for {db_name}", level='INFO', name='db_monitor')
            except Exception as e:
                log_system(f"Error collecting slow queries for {db_name}: {str(e)}", level='ERROR', name='db_monitor')
        
        log_system(f"Collected metrics for {db_name}: {list(collected_metrics['metrics'].keys())}", level='DEBUG', name='db_monitor')
        return collected_metrics
    
    def _collect_mysql_metrics(self, db_config: Dict, db_name: str, metrics: List[str]) -> Dict:
        """Collect MySQL specific metrics"""
        result = {}
        
        # Get database connection
        db_config_id = db_config['db_config_id'] if 'db_config_id' in db_config else 'unknown'
        
        # Collect metrics based on requested list
        if any(m in metrics for m in ['query_execution_time', 'slow_queries_count']):
            # Get slow query statistics
            slow_query_result = self.db_manager.execute_query(
                db_config_id,
                "SHOW GLOBAL STATUS LIKE 'Slow_queries'",
                None
            )
            if slow_query_result['status'] == 'success':
                result['slow_queries_count'] = int(slow_query_result['results'][0]['Value'])
        
        if 'connection_count' in metrics:
            # Get current connections
            connections_result = self.db_manager.execute_query(
                db_config_id,
                "SHOW GLOBAL STATUS LIKE 'Threads_connected'",
                None
            )
            if connections_result['status'] == 'success':
                result['connection_count'] = int(connections_result['results'][0]['Value'])
        
        if any(m in metrics for m in ['cpu_usage', 'memory_usage']):
            # Get server status for resource usage
            status_result = self.db_manager.execute_query(
                db_config_id,
                "SHOW GLOBAL STATUS LIKE '%%cpu%%' OR SHOW GLOBAL STATUS LIKE '%%memory%%'",
                None
            )
            if status_result['status'] == 'success':
                for row in status_result['results']:
                    if row['Variable_name'] == 'Innodb_row_lock_current_waits':
                        result['lock_contention'] = int(row['Value'])
        
        if 'buffer_pool_hit_rate' in metrics:
            # Calculate buffer pool hit rate
            buffer_result = self.db_manager.execute_query(
                db_config_id,
                "SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read_%'",
                None
            )
            if buffer_result['status'] == 'success':
                read_requests = 0
                read_physical = 0
                for row in buffer_result['results']:
                    if row['Variable_name'] == 'Innodb_buffer_pool_read_requests':
                        read_requests = int(row['Value'])
                    elif row['Variable_name'] == 'Innodb_buffer_pool_reads':
                        read_physical = int(row['Value'])
                
                if read_requests > 0:
                    hit_rate = 100 - (read_physical / read_requests * 100)
                    result['buffer_pool_hit_rate'] = round(hit_rate, 2)
        
        return result
    
    def _collect_postgresql_metrics(self, db_config: Dict, db_name: str, metrics: List[str]) -> Dict:
        """Collect PostgreSQL specific metrics"""
        result = {}
        
        # Get database connection
        db_config_id = db_config['db_config_id'] if 'db_config_id' in db_config else 'unknown'
        
        if 'connection_count' in metrics:
            # Get current connections
            connections_result = self.db_manager.execute_query(
                db_config_id,
                "SELECT count(*) as connection_count FROM pg_stat_activity",
                db_name
            )
            if connections_result['status'] == 'success':
                result['connection_count'] = connections_result['results'][0]['connection_count']
        
        if 'query_execution_time' in metrics:
            # Get average query time
            query_time_result = self.db_manager.execute_query(
                db_config_id,
                "SELECT avg(query_exec_time) as avg_query_time FROM pg_stat_statements",
                db_name
            )
            if query_time_result['status'] == 'success' and query_time_result['results']:
                result['query_execution_time'] = query_time_result['results'][0]['avg_query_time'] or 0
        
        if 'lock_contention' in metrics:
            # Get lock statistics
            lock_result = self.db_manager.execute_query(
                db_config_id,
                "SELECT count(*) as lock_count FROM pg_locks WHERE granted = false",
                db_name
            )
            if lock_result['status'] == 'success':
                result['lock_contention'] = lock_result['results'][0]['lock_count']
        
        if 'index_usage' in metrics:
            # Get index usage statistics
            index_result = self.db_manager.execute_query(
                db_config_id,
                "SELECT sum(idx_scan) as index_scans, sum(seq_scan) as seq_scans FROM pg_stat_user_tables",
                db_name
            )
            if index_result['status'] == 'success' and index_result['results']:
                row = index_result['results'][0]
                index_scans = row['index_scans'] or 0
                seq_scans = row['seq_scans'] or 0
                total_scans = index_scans + seq_scans
                if total_scans > 0:
                    result['index_usage'] = round((index_scans / total_scans) * 100, 2)
        
        return result
    
    def _collect_slow_queries(self, db_config: Dict, db_name: str, db_type: str) -> List[Dict]:
        """Collect slow queries"""
        slow_queries = []
        db_config_id = db_config['db_config_id'] if 'db_config_id' in db_config else 'unknown'
        
        try:
            if db_type == 'mysql':
                # Get slow queries from MySQL
                slow_result = self.db_manager.execute_query(
                    db_config_id,
                    "SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10",
                    None
                )
                if slow_result['status'] == 'success':
                    for row in slow_result['results']:
                        slow_queries.append({
                            'query_text': row['sql_text'],
                            'execution_time': row['query_time'],
                            'lock_time': row['lock_time'],
                            'rows_affected': row['rows_affected']
                        })
            elif db_type == 'postgresql':
                # Get slow queries from PostgreSQL
                slow_result = self.db_manager.execute_query(
                    db_config_id,
                    "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10",
                    db_name
                )
                if slow_result['status'] == 'success':
                    for row in slow_result['results']:
                        slow_queries.append({
                            'query_text': row['query'],
                            'execution_time': row['mean_exec_time'],
                            'calls': row['calls']
                        })
        except Exception:
            # Ignore errors when collecting slow queries
            pass
        
        return slow_queries
    
    def _store_metrics(self, config_id: str, metrics_data: Dict) -> None:
        """Store metrics in SQLite database"""
        conn = sqlite3.connect(MONITOR_DATA_DB)
        cursor = conn.cursor()
        
        timestamp = metrics_data['timestamp']
        db_config_id = metrics_data['db_config_id']
        db_name = metrics_data['db_name']
        
        # Store metrics
        for metric_name, metric_value in metrics_data['metrics'].items():
            if metric_value is not None:
                cursor.execute(
                    "INSERT INTO metrics (timestamp, db_config_id, db_name, metric_name, metric_value) VALUES (?, ?, ?, ?, ?)",
                    (timestamp, db_config_id, db_name, metric_name, metric_value)
                )
        
        # Store slow queries if any
        if 'slow_queries' in metrics_data:
            for query in metrics_data['slow_queries']:
                cursor.execute(
                    "INSERT INTO slow_queries (timestamp, db_config_id, db_name, query_text, execution_time, rows_affected, lock_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, db_config_id, db_name, query['query_text'], query['execution_time'], 
                     query.get('rows_affected'), query.get('lock_time'))
                )
        
        conn.commit()
        conn.close()
    
    def _check_alerts(self, config_id: str, metrics_data: Dict) -> None:
        """Check if metrics exceed alert thresholds"""
        # This would check against configured thresholds and create alerts
        # For now, we'll just log the metrics
        pass
    
    def _log_monitor_error(self, config_id: str, error_msg: str) -> None:
        """Log monitoring errors"""
        error_log = {
            'timestamp': datetime.now().isoformat(),
            'config_id': config_id,
            'error': error_msg
        }
        
        # Log to both file and system logger
        log_system(f"Monitoring error for {config_id}: {error_msg}", level='ERROR', name='db_monitor')
        
        # Simple logging to a file
        error_log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'monitor_errors.log')
        with open(error_log_file, 'a') as f:
            f.write(json.dumps(error_log) + '\n')
    
    def get_realtime_metrics(self, config_id: str, metrics: Optional[List[str]] = None) -> Dict:
        """Get real-time metrics for a configuration"""
        if config_id not in self.monitor_configs:
            return {'status': 'error', 'message': f'Monitoring configuration {config_id} not found'}
        
        config = self.monitor_configs[config_id]
        
        # Collect current metrics
        metrics_data = self._collect_metrics(config)
        
        # Filter metrics if requested
        if metrics:
            filtered_metrics = {k: v for k, v in metrics_data['metrics'].items() if k in metrics}
            metrics_data['metrics'] = filtered_metrics
        
        return {'status': 'success', 'metrics': metrics_data}
    
    def get_historical_metrics(self, db_config_id: str, db_name: str, metric_name: str, 
                              time_range: str = '1h', interval: str = '1m') -> Dict:
        """Get historical metrics data"""
        conn = sqlite3.connect(MONITOR_DATA_DB)
        cursor = conn.cursor()
        
        # Calculate time range
        end_time = datetime.now()
        if time_range == '1h':
            start_time = end_time - timedelta(hours=1)
        elif time_range == '24h':
            start_time = end_time - timedelta(days=1)
        elif time_range == '7d':
            start_time = end_time - timedelta(days=7)
        elif time_range == '30d':
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=1)
        
        # Query historical metrics
        cursor.execute(
            "SELECT timestamp, metric_value FROM metrics WHERE db_config_id = ? AND db_name = ? AND metric_name = ? AND timestamp >= ? ORDER BY timestamp",
            (db_config_id, db_name, metric_name, start_time.isoformat())
        )
        
        results = cursor.fetchall()
        conn.close()
        
        # Format results
        formatted_results = [
            {
                'timestamp': row[0],
                'value': row[1]
            }
            for row in results
        ]
        
        return {
            'status': 'success',
            'metric_name': metric_name,
            'time_range': time_range,
            'data': formatted_results
        }
    
    def get_slow_queries(self, db_config_id: str, db_name: str, limit: int = 20, time_range: str = '24h') -> Dict:
        """Get slow queries for a database"""
        conn = sqlite3.connect(MONITOR_DATA_DB)
        cursor = conn.cursor()
        
        # Calculate time range
        end_time = datetime.now()
        if time_range == '1h':
            start_time = end_time - timedelta(hours=1)
        elif time_range == '24h':
            start_time = end_time - timedelta(days=1)
        elif time_range == '7d':
            start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(days=1)
        
        # Query slow queries
        cursor.execute(
            "SELECT timestamp, query_text, execution_time, rows_affected, lock_time FROM slow_queries WHERE db_config_id = ? AND db_name = ? AND timestamp >= ? ORDER BY execution_time DESC LIMIT ?",
            (db_config_id, db_name, start_time.isoformat(), limit)
        )
        
        results = cursor.fetchall()
        conn.close()
        
        # Format results
        formatted_results = [
            {
                'timestamp': row[0],
                'query_text': row[1],
                'execution_time': row[2],
                'rows_affected': row[3],
                'lock_time': row[4]
            }
            for row in results
        ]
        
        return {
            'status': 'success',
            'slow_queries': formatted_results,
            'count': len(formatted_results)
        }
    
    def get_optimization_recommendations(self, db_config_id: str, db_name: str) -> Dict:
        """Get optimization recommendations based on metrics"""
        recommendations = []
        
        # Get database configuration
        db_config_result = self.db_manager.get_db_config(db_config_id)
        if db_config_result['status'] != 'success':
            return {'status': 'error', 'message': 'Database configuration not found'}
        
        db_config = db_config_result['config']
        db_type = db_config['db_type']
        
        # Get recent slow queries
        slow_queries_result = self.get_slow_queries(db_config_id, db_name, limit=10)
        if slow_queries_result['status'] == 'success' and slow_queries_result['slow_queries']:
            recommendations.append({
                'type': 'slow_queries',
                'severity': 'medium',
                'message': f'Found {len(slow_queries_result["slow_queries"])} slow queries in the last 24 hours',
                'recommendation': 'Analyze and optimize the slowest queries using EXPLAIN',
                'details': {
                    'slow_query_count': len(slow_queries_result['slow_queries']),
                    'slowest_query_time': max(q['execution_time'] for q in slow_queries_result['slow_queries'])
                }
            })
        
        # Get connection count metrics
        conn = sqlite3.connect(MONITOR_DATA_DB)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT avg(metric_value) as avg_connections, max(metric_value) as max_connections FROM metrics WHERE db_config_id = ? AND db_name = ? AND metric_name = 'connection_count' AND timestamp >= ?",
            (db_config_id, db_name, (datetime.now() - timedelta(hours=24)).isoformat())
        )
        
        conn_result = cursor.fetchone()
        if conn_result and conn_result[1] is not None and conn_result[1] > 100:
            recommendations.append({
                'type': 'high_connections',
                'severity': 'warning',
                'message': f'High connection count detected: {conn_result[1]} connections at peak',
                'recommendation': 'Consider optimizing connection pooling or increasing max_connections setting',
                'details': {
                    'average_connections': conn_result[0],
                    'peak_connections': conn_result[1]
                }
            })
        
        conn.close()
        
        return {
            'status': 'success',
            'recommendations': recommendations,
            'db_type': db_type
        }
    
    def add_alert_threshold(self, db_config_id: str, db_name: str, metric_name: str, 
                          threshold_type: str, threshold_value: float, 
                          alert_message: str = '') -> Dict:
        """Add alert threshold for a metric"""
        # This would add alert thresholds to be checked during monitoring
        # For now, we'll just store it in memory
        
        key = f"{db_config_id}_{db_name}_{metric_name}"
        self.alert_thresholds[key] = {
            'threshold_type': threshold_type,  # 'above' or 'below'
            'threshold_value': threshold_value,
            'alert_message': alert_message
        }
        
        return {'status': 'success', 'message': f'Alert threshold added for {metric_name}'}
    
    def get_alerts(self, db_config_id: Optional[str] = None, db_name: Optional[str] = None, 
                  status: Optional[str] = None) -> Dict:
        """Get alerts"""
        conn = sqlite3.connect(MONITOR_DATA_DB)
        cursor = conn.cursor()
        
        query = "SELECT id, timestamp, db_config_id, db_name, metric_name, alert_type, current_value, threshold_value, status, resolved_at FROM alerts"
        params = []
        
        # Build WHERE clause
        where_clauses = []
        if db_config_id:
            where_clauses.append("db_config_id = ?")
            params.append(db_config_id)
        if db_name:
            where_clauses.append("db_name = ?")
            params.append(db_name)
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        # Format results
        alerts = [
            {
                'id': row[0],
                'timestamp': row[1],
                'db_config_id': row[2],
                'db_name': row[3],
                'metric_name': row[4],
                'alert_type': row[5],
                'current_value': row[6],
                'threshold_value': row[7],
                'status': row[8],
                'resolved_at': row[9]
            }
            for row in results
        ]
        
        return {'status': 'success', 'alerts': alerts}

