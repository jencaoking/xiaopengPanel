import psutil
import platform
import subprocess
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

# Constants for systemd states
SYSTEMD_STATES = {
    'active': {
        'status': 'running',
        'indicator': '🟢',
        'description': 'Service is running normally'
    },
    'inactive': {
        'status': 'stopped',
        'indicator': '⚫',
        'description': 'Service is not running'
    },
    'failed': {
        'status': 'failed',
        'indicator': '🔴',
        'description': 'Service has failed to start'
    },
    'activating': {
        'status': 'starting',
        'indicator': '🟡',
        'description': 'Service is starting up'
    },
    'deactivating': {
        'status': 'stopping',
        'indicator': '🟠',
        'description': 'Service is shutting down'
    }
}

# Get Windows services

def get_windows_services():
    services = []
    for service in psutil.win_service_iter():
        try:
            # Try to get service name first
            name = service.name()
            
            # Then get other service info with proper error handling
            display_name = service.display_name()
            status = service.status()
            start_type = service.start_type()
            
            # Handle case where description might not be available
            try:
                description = service.description()
            except FileNotFoundError:
                description = ""
            except Exception:
                description = ""
            
            services.append({
                'name': name,
                'display_name': display_name,
                'status': status,
                'start_type': start_type,
                'description': description,
                'indicator': '🟢' if status == 'running' else '⚫',
                'uptime': None,
                'exit_code': None
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError):
            continue
        except Exception as e:
            continue
    return services

# Get service uptime in seconds

def get_service_uptime(service_name: str) -> Optional[int]:
    """Get uptime for a running service"""
    try:
        result = subprocess.run([
            'systemctl', 'show', f'{service_name}.service', 
            '--property=ActiveEnterTimestamp'
        ], capture_output=True, text=True, check=True)
        
        timestamp_str = result.stdout.strip().split('=')[1]
        if timestamp_str:
            enter_time = datetime.strptime(timestamp_str, '%a %Y-%m-%d %H:%M:%S %Z')
            uptime = int((datetime.now() - enter_time).total_seconds())
            return uptime
    except Exception:
        pass
    return None

# Get service exit code

def get_service_exit_code(service_name: str) -> Optional[int]:
    """Get exit code for a failed service"""
    try:
        result = subprocess.run([
            'systemctl', 'show', f'{service_name}.service', 
            '--property=ExecMainStatus'
        ], capture_output=True, text=True, check=True)
        
        exit_code_str = result.stdout.strip().split('=')[1]
        if exit_code_str and exit_code_str.isdigit():
            return int(exit_code_str)
    except Exception:
        pass
    return None

# Get Linux service status

def get_linux_service_status(service_name: str) -> Dict[str, Any]:
    """Get detailed status for a Linux service"""
    status_info = {
        'name': service_name,
        'display_name': service_name,
        'status': 'unknown',
        'startup_type': 'unknown',
        'description': '',
        'indicator': '⚫',
        'uptime': None,
        'exit_code': None,
        'loaded': False,
        'active_state': 'unknown',
        'sub_state': 'unknown'
    }
    
    try:
        # Get service details
        result = subprocess.run([
            'systemctl', 'show', f'{service_name}.service',
            '--property=Description,Loaded,ActiveState,SubState,UnitFileState'
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                if key == 'Description':
                    status_info['description'] = value
                elif key == 'Loaded':
                    status_info['loaded'] = value.startswith('loaded')
                elif key == 'ActiveState':
                    status_info['active_state'] = value
                    status_info['status'] = SYSTEMD_STATES.get(value, {}).get('status', 'unknown')
                    status_info['indicator'] = SYSTEMD_STATES.get(value, {}).get('indicator', '⚫')
                elif key == 'SubState':
                    status_info['sub_state'] = value
                elif key == 'UnitFileState':
                    status_info['startup_type'] = value
        
        # Get uptime if service is active
        if status_info['active_state'] == 'active':
            status_info['uptime'] = get_service_uptime(service_name)
        
        # Get exit code if service has failed
        if status_info['active_state'] == 'failed':
            status_info['exit_code'] = get_service_exit_code(service_name)
            
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        pass
    
    return status_info

# Get all Linux services

def get_linux_services() -> List[Dict[str, Any]]:
    services = []
    try:
        # Get all service units
        result = subprocess.run([
            'systemctl', 'list-units', '--type=service', '--all', '--no-pager',
            '--output=json'
        ], capture_output=True, text=True, check=True)
        
        units = json.loads(result.stdout)
        for unit in units:
            if unit['unit_type'] == 'service':
                service_name = unit['unit_name'].replace('.service', '')
                service_info = get_linux_service_status(service_name)
                services.append(service_info)
    except subprocess.CalledProcessError:
        # Fallback to text output if JSON is not supported
        result = subprocess.run([
            'systemctl', 'list-units', '--type=service', '--all', '--no-pager'
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')[1:-3]  # Skip header and footer
        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                continue
            
            service_name = parts[0].replace('.service', '')
            service_info = get_linux_service_status(service_name)
            services.append(service_info)
    except Exception as e:
        print(f"Error getting Linux services: {e}")
    
    return services

# Get all services with filtering and sorting

def get_services(filter_status: Optional[str] = None, sort_by: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all system services with optional filtering and sorting
    
    Args:
        filter_status: Filter by service status (active, inactive, failed)
        sort_by: Sort by field (name, status, startup_type)
        
    Returns:
        Dict containing services and metadata
    """
    if platform.system() == 'Windows':
        services = get_windows_services()
    elif platform.system() == 'Linux':
        services = get_linux_services()
    else:
        return {
            'services': [],
            'total': 0,
            'filter_status': filter_status,
            'sort_by': sort_by,
            'os': platform.system()
        }
    
    # Apply filtering
    if filter_status:
        filtered_services = []
        for service in services:
            if 'active_state' in service:
                # Linux services use active_state
                if service['active_state'] == filter_status:
                    filtered_services.append(service)
            else:
                # Windows services use status directly
                if service['status'] == filter_status:
                    filtered_services.append(service)
        services = filtered_services
    
    # Apply sorting
    if sort_by:
        if sort_by == 'name':
            services.sort(key=lambda s: s['name'].lower())
        elif sort_by == 'status':
            services.sort(key=lambda s: s['status'].lower())
        elif sort_by == 'startup_type':
            services.sort(key=lambda s: s.get('startup_type', '').lower())
    
    return {
        'services': services,
        'total': len(services),
        'filter_status': filter_status,
        'sort_by': sort_by,
        'os': platform.system()
    }

# Get detailed service status

def get_service_status(service_name: str) -> Dict[str, Any]:
    """
    Get detailed status information for a specific service
    
    Args:
        service_name: Name of the service to check
        
    Returns:
        Dict containing detailed service information
    """
    if platform.system() == 'Linux':
        return get_linux_service_status(service_name)
    elif platform.system() == 'Windows':
        for service in psutil.win_service_iter():
            try:
                service_info = service.as_dict()
                if service_info['name'] == service_name:
                    return {
                        'name': service_info['name'],
                        'display_name': service_info['display_name'],
                        'status': service_info['status'],
                        'start_type': service_info['start_type'],
                        'description': service_info['description'],
                        'indicator': '🟢' if service_info['status'] == 'running' else '⚫',
                        'uptime': None,
                        'exit_code': None,
                        'os': 'Windows'
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    return {
        'error': f"Service {service_name} not found",
        'status': 'not_found',
        'indicator': '❌'
    }

# Manage Windows service

def manage_windows_service(service_name: str, action: str) -> Dict[str, Any]:
    try:
        service = psutil.win_service_get(service_name)
        
        if action == 'start':
            service.start()
            return {
                'status': 'success',
                'message': f'Service {service_name} started successfully'
            }
        elif action == 'stop':
            service.stop()
            return {
                'status': 'success',
                'message': f'Service {service_name} stopped successfully'
            }
        elif action == 'restart':
            service.restart()
            return {
                'status': 'success',
                'message': f'Service {service_name} restarted successfully'
            }
        elif action == 'enable':
            service.enable()
            return {
                'status': 'success',
                'message': f'Service {service_name} enabled successfully'
            }
        elif action == 'disable':
            service.disable()
            return {
                'status': 'success',
                'message': f'Service {service_name} disabled successfully'
            }
        else:
            return {
                'status': 'error',
                'message': f'Invalid action: {action}'
            }
    except psutil.NoSuchProcess:
        return {
            'status': 'error',
            'message': f'Service {service_name} not found'
        }
    except psutil.AccessDenied:
        return {
            'status': 'error',
            'message': f'Access denied to service {service_name}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# Manage Linux service with timeout handling

def manage_linux_service(service_name: str, action: str) -> Dict[str, Any]:
    try:
        timeout = 30  # 30 seconds timeout
        
        if action == 'start':
            subprocess.run(
                ['systemctl', 'start', f'{service_name}.service'], 
                check=True, timeout=timeout
            )
            # Verify service started successfully
            status = get_service_status(service_name)
            if status.get('active_state') == 'active':
                return {
                    'status': 'success',
                    'message': f'Service {service_name} started successfully',
                    'service_status': status
                }
            else:
                return {
                    'status': 'warning',
                    'message': f'Service {service_name} command executed, but status is {status.get("status")}',
                    'service_status': status
                }
                
        elif action == 'stop':
            subprocess.run(
                ['systemctl', 'stop', f'{service_name}.service'], 
                check=True, timeout=timeout
            )
            # Verify service stopped successfully
            status = get_service_status(service_name)
            if status.get('active_state') == 'inactive':
                return {
                    'status': 'success',
                    'message': f'Service {service_name} stopped successfully',
                    'service_status': status
                }
            else:
                return {
                    'status': 'warning',
                    'message': f'Service {service_name} command executed, but status is {status.get("status")}',
                    'service_status': status
                }
                
        elif action == 'restart':
            # Pre-check: ensure service exists
            status = get_service_status(service_name)
            if 'error' in status:
                return status
            
            subprocess.run(
                ['systemctl', 'restart', f'{service_name}.service'], 
                check=True, timeout=timeout
            )
            # Verify service restarted successfully
            status = get_service_status(service_name)
            if status.get('active_state') == 'active':
                return {
                    'status': 'success',
                    'message': f'Service {service_name} restarted successfully',
                    'service_status': status
                }
            else:
                return {
                    'status': 'warning',
                    'message': f'Service {service_name} command executed, but status is {status.get("status")}',
                    'service_status': status
                }
                
        elif action == 'enable':
            subprocess.run(
                ['systemctl', 'enable', f'{service_name}.service'], 
                check=True, timeout=timeout
            )
            return {
                'status': 'success',
                'message': f'Service {service_name} enabled successfully'
            }
            
        elif action == 'disable':
            subprocess.run(
                ['systemctl', 'disable', f'{service_name}.service'], 
                check=True, timeout=timeout
            )
            return {
                'status': 'success',
                'message': f'Service {service_name} disabled successfully'
            }
            
        else:
            return {
                'status': 'error',
                'message': f'Invalid action: {action}'
            }
            
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f'Failed to {action} service {service_name}: {e.stderr.strip() if e.stderr else str(e)}'
        }
    except subprocess.TimeoutExpired:
        return {
            'status': 'error',
            'message': f'Timeout exceeded ({timeout}s) while trying to {action} service {service_name}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An error occurred while trying to {action} service {service_name}: {str(e)}'
        }

# Manage service - main function

def manage_service(service_name: str, action: str) -> Dict[str, Any]:
    """
    Manage service operations with proper error handling
    
    Args:
        service_name: Name of the service to manage
        action: Action to perform (start, stop, restart, enable, disable)
        
    Returns:
        Dict containing operation result and service status
    """
    if platform.system() == 'Windows':
        return manage_windows_service(service_name, action)
    elif platform.system() == 'Linux':
        return manage_linux_service(service_name, action)
    else:
        return {
            'status': 'error',
            'message': f'Unsupported OS: {platform.system()}'
        }

# Get service logs using journalctl

def get_service_logs(
    service_name: str,
    time_range: str = 'today',
    keyword: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    verbosity: str = 'info'
) -> Dict[str, Any]:
    """
    Get service-specific logs using journalctl
    
    Args:
        service_name: Name of the service to get logs for
        time_range: Time range filter (today, yesterday, last_24h, custom)
        keyword: Keyword to search for in logs
        limit: Maximum number of log entries to return
        offset: Offset for pagination
        verbosity: Log verbosity level (debug, info, notice, warning, error, crit, alert, emerg)
        
    Returns:
        Dict containing log entries and metadata
    """
    if platform.system() != 'Linux':
        return {
            'status': 'error',
            'message': 'Service logs are only available on Linux systems',
            'logs': []
        }
    
    try:
        # Build journalctl command
        cmd = [
            'journalctl',
            f'--unit={service_name}.service',
            '--output=json',
            '--lines', str(limit),
            '--offset', str(offset)
        ]
        
        # Add time range filter
        if time_range == 'today':
            cmd.extend(['--since', 'today'])
        elif time_range == 'yesterday':
            cmd.extend(['--since', 'yesterday', '--until', 'today'])
        elif time_range == 'last_24h':
            cmd.extend(['--since', '24h ago'])
        
        # Add verbosity filter
        verbosity_map = {
            'debug': 7, 'info': 6, 'notice': 5, 'warning': 4,
            'error': 3, 'crit': 2, 'alert': 1, 'emerg': 0
        }
        if verbosity in verbosity_map:
            cmd.extend(['--priority', str(verbosity_map[verbosity])])
        
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse logs
        logs = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    log_entry = json.loads(line)
                    # Format log entry
                    formatted_entry = {
                        'timestamp': log_entry.get('_SOURCE_REALTIME_TIMESTAMP'),
                        'boot_id': log_entry.get('_BOOT_ID'),
                        'machine_id': log_entry.get('_MACHINE_ID'),
                        'priority': log_entry.get('PRIORITY'),
                        'message': log_entry.get('MESSAGE', ''),
                        'service': log_entry.get('SYSLOG_IDENTIFIER', ''),
                        'pid': log_entry.get('_PID'),
                        'uid': log_entry.get('_UID'),
                        'gid': log_entry.get('_GID'),
                        'process_name': log_entry.get('_COMM')
                    }
                    logs.append(formatted_entry)
                except json.JSONDecodeError:
                    continue
        
        # Apply keyword filtering if specified
        if keyword:
            filtered_logs = []
            for log in logs:
                if keyword.lower() in log['message'].lower():
                    # Add highlighting
                    highlighted_message = re.sub(
                        f'({re.escape(keyword)})',
                        r'**\1**',
                        log['message'],
                        flags=re.IGNORECASE
                    )
                    log['message'] = highlighted_message
                    filtered_logs.append(log)
            logs = filtered_logs
        
        return {
            'status': 'success',
            'message': f'Logs retrieved successfully for service {service_name}',
            'logs': logs,
            'total': len(logs),
            'service_name': service_name,
            'time_range': time_range,
            'keyword': keyword,
            'limit': limit,
            'offset': offset
        }
        
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f'Failed to retrieve logs: {e.stderr.strip() if e.stderr else str(e)}',
            'logs': []
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}',
            'logs': []
        }

# Get service unit file information

def get_service_unit_file(service_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a service's unit file
    
    Args:
        service_name: Name of the service to get unit file info for
        
    Returns:
        Dict containing unit file information
    """
    if platform.system() != 'Linux':
        return {
            'status': 'error',
            'message': 'Unit file information is only available on Linux systems'
        }
    
    try:
        result = subprocess.run([
            'systemctl', 'cat', f'{service_name}.service'
        ], capture_output=True, text=True, check=True)
        
        return {
            'status': 'success',
            'message': f'Unit file retrieved successfully for service {service_name}',
            'unit_file': result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f'Failed to retrieve unit file: {e.stderr.strip() if e.stderr else str(e)}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}'
        }

# Get service dependencies

def get_service_dependencies(service_name: str, reverse: bool = False) -> Dict[str, Any]:
    """
    Get service dependencies
    
    Args:
        service_name: Name of the service to get dependencies for
        reverse: If True, get reverse dependencies (services that depend on this service)
        
    Returns:
        Dict containing service dependencies
    """
    if platform.system() != 'Linux':
        return {
            'status': 'error',
            'message': 'Service dependencies are only available on Linux systems',
            'dependencies': []
        }
    
    try:
        cmd = [
            'systemctl',
            'list-dependencies' if not reverse else 'list-dependencies --reverse',
            f'{service_name}.service',
            '--all',
            '--no-pager'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse dependencies
        dependencies = []
        lines = result.stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            if line.strip():
                dep_name = line.strip().replace('.service', '')
                dependencies.append(dep_name)
        
        return {
            'status': 'success',
            'message': f'Dependencies retrieved successfully for service {service_name}',
            'dependencies': dependencies,
            'type': 'reverse' if reverse else 'normal'
        }
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'message': f'Failed to retrieve dependencies: {e.stderr.strip() if e.stderr else str(e)}',
            'dependencies': []
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}',
            'dependencies': []
        }
