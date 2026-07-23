import os
import json
import uuid
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict
from croniter import croniter

from .log_manager import log_system

# 定时任务数据文件路径
CRON_TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cron_tasks.json')
CRON_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cron_history.json')

# 历史记录最大保留条数（每个任务）
MAX_HISTORY_PER_TASK = 50
# 调度器轮询间隔（秒）
SCHEDULER_INTERVAL = 30
# 命令执行超时（秒）
COMMAND_TIMEOUT = 3600


class CronTaskManager:
    """定时任务管理器，支持 Cron 表达式调度与执行历史记录"""

    def __init__(self):
        self.tasks = self._load_tasks()
        self.history = self._load_history()
        self._lock = threading.RLock()
        self._scheduler_thread = None
        self._running = False
        # 记录每个任务下一次触发时间
        self._next_run = {}
        # 正在执行的任务ID集合，防止并发执行同一任务
        self._running_tasks = set()

    # -------------------- 数据持久化 --------------------

    def _load_tasks(self) -> Dict:
        """从 JSON 文件加载任务配置"""
        if not os.path.exists(CRON_TASKS_FILE):
            os.makedirs(os.path.dirname(CRON_TASKS_FILE), exist_ok=True)
            with open(CRON_TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}
        try:
            with open(CRON_TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log_system(f'Failed to load cron tasks: {e}', 'ERROR', 'cron_manager')
            return {}

    def _save_tasks(self) -> None:
        """保存任务配置到 JSON 文件"""
        try:
            os.makedirs(os.path.dirname(CRON_TASKS_FILE), exist_ok=True)
            with open(CRON_TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
        except IOError as e:
            log_system(f'Failed to save cron tasks: {e}', 'ERROR', 'cron_manager')

    def _load_history(self) -> Dict:
        """从 JSON 文件加载执行历史"""
        if not os.path.exists(CRON_HISTORY_FILE):
            os.makedirs(os.path.dirname(CRON_HISTORY_FILE), exist_ok=True)
            with open(CRON_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {}
        try:
            with open(CRON_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log_system(f'Failed to load cron history: {e}', 'ERROR', 'cron_manager')
            return {}

    def _save_history(self) -> None:
        """保存执行历史到 JSON 文件"""
        try:
            os.makedirs(os.path.dirname(CRON_HISTORY_FILE), exist_ok=True)
            with open(CRON_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            log_system(f'Failed to save cron history: {e}', 'ERROR', 'cron_manager')

    # -------------------- 校验工具 --------------------

    @staticmethod
    def validate_cron(cron_expr: str) -> bool:
        """校验 Cron 表达式是否合法"""
        try:
            croniter(cron_expr, datetime.now())
            return True
        except (ValueError, KeyError):
            return False

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """清理任务名称，去除首尾空白"""
        return (name or '').strip()

    # -------------------- 任务 CRUD --------------------

    def get_all_tasks(self) -> Dict:
        """获取所有任务"""
        with self._lock:
            tasks_list = []
            for task_id, task in self.tasks.items():
                item = dict(task)
                item['task_id'] = task_id
                # 附加下次运行时间
                item['next_run'] = self._next_run.get(task_id)
                tasks_list.append(item)
            return {'status': 'success', 'tasks': tasks_list}

    def get_task(self, task_id: str) -> Dict:
        """获取单个任务详情"""
        with self._lock:
            if task_id not in self.tasks:
                return {'status': 'error', 'message': f'Task {task_id} not found'}
            item = dict(self.tasks[task_id])
            item['task_id'] = task_id
            item['next_run'] = self._next_run.get(task_id)
            return {'status': 'success', 'task': item}

    def add_task(self, name: str, command: str, cron_expr: str,
                 description: str = '', enabled: bool = True,
                 timeout: int = COMMAND_TIMEOUT) -> Dict:
        """添加新的定时任务"""
        name = self._sanitize_name(name)
        if not name:
            return {'status': 'error', 'message': 'Task name is required'}
        if not command or not command.strip():
            return {'status': 'error', 'message': 'Command is required'}
        if not self.validate_cron(cron_expr):
            return {'status': 'error', 'message': f'Invalid cron expression: {cron_expr}'}

        try:
            timeout = int(timeout)
            if timeout <= 0:
                timeout = COMMAND_TIMEOUT
        except (ValueError, TypeError):
            timeout = COMMAND_TIMEOUT

        with self._lock:
            task_id = uuid.uuid4().hex[:12]
            now = datetime.now().isoformat()
            self.tasks[task_id] = {
                'name': name,
                'command': command.strip(),
                'cron_expr': cron_expr.strip(),
                'description': description.strip(),
                'enabled': bool(enabled),
                'timeout': timeout,
                'created_at': now,
                'updated_at': now,
                'last_run': None,
                'last_status': None,
                'run_count': 0
            }
            self._save_tasks()
            self._update_next_run(task_id)
            log_system(f'Added cron task {task_id}: {name}', 'INFO', 'cron_manager')
            return {'status': 'success', 'message': 'Task added successfully', 'task_id': task_id}

    def update_task(self, task_id: str, updates: Dict) -> Dict:
        """更新任务配置"""
        with self._lock:
            if task_id not in self.tasks:
                return {'status': 'error', 'message': f'Task {task_id} not found'}

            task = self.tasks[task_id]

            if 'name' in updates:
                name = self._sanitize_name(updates['name'])
                if not name:
                    return {'status': 'error', 'message': 'Task name cannot be empty'}
                task['name'] = name

            if 'command' in updates:
                command = updates['command']
                if not command or not str(command).strip():
                    return {'status': 'error', 'message': 'Command cannot be empty'}
                task['command'] = str(command).strip()

            if 'cron_expr' in updates:
                cron_expr = updates['cron_expr']
                if not self.validate_cron(cron_expr):
                    return {'status': 'error', 'message': f'Invalid cron expression: {cron_expr}'}
                task['cron_expr'] = cron_expr.strip()

            if 'description' in updates:
                task['description'] = str(updates['description']).strip()

            if 'enabled' in updates:
                task['enabled'] = bool(updates['enabled'])

            if 'timeout' in updates:
                try:
                    timeout = int(updates['timeout'])
                    task['timeout'] = timeout if timeout > 0 else COMMAND_TIMEOUT
                except (ValueError, TypeError):
                    pass

            task['updated_at'] = datetime.now().isoformat()
            self._save_tasks()
            self._update_next_run(task_id)
            log_system(f'Updated cron task {task_id}', 'INFO', 'cron_manager')
            return {'status': 'success', 'message': 'Task updated successfully'}

    def delete_task(self, task_id: str) -> Dict:
        """删除任务"""
        with self._lock:
            if task_id not in self.tasks:
                return {'status': 'error', 'message': f'Task {task_id} not found'}
            name = self.tasks[task_id].get('name', '')
            del self.tasks[task_id]
            self._save_tasks()
            # 同时清理历史记录
            if task_id in self.history:
                del self.history[task_id]
                self._save_history()
            self._next_run.pop(task_id, None)
            log_system(f'Deleted cron task {task_id}: {name}', 'INFO', 'cron_manager')
            return {'status': 'success', 'message': 'Task deleted successfully'}

    def toggle_task(self, task_id: str) -> Dict:
        """启用/禁用任务"""
        with self._lock:
            if task_id not in self.tasks:
                return {'status': 'error', 'message': f'Task {task_id} not found'}
            self.tasks[task_id]['enabled'] = not self.tasks[task_id]['enabled']
            self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
            self._save_tasks()
            if self.tasks[task_id]['enabled']:
                self._update_next_run(task_id)
            else:
                self._next_run.pop(task_id, None)
            state = 'enabled' if self.tasks[task_id]['enabled'] else 'disabled'
            log_system(f'Task {task_id} {state}', 'INFO', 'cron_manager')
            return {'status': 'success', 'message': f'Task {state}', 'enabled': self.tasks[task_id]['enabled']}

    # -------------------- 执行与历史 --------------------

    def _execute_task(self, task_id: str, trigger_type: str = 'scheduled') -> None:
        """执行任务命令并记录历史（在子线程中运行）"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            # 防止同一任务并发执行
            if task_id in self._running_tasks:
                log_system(f'Cron task {task_id} is already running, skip this trigger',
                           'WARNING', 'cron_manager')
                return
            self._running_tasks.add(task_id)
            command = task['command']
            timeout = task.get('timeout', COMMAND_TIMEOUT)
            name = task['name']

        try:
            run_id = uuid.uuid4().hex[:16]
            start_time = datetime.now()
            log_system(f'Executing cron task {task_id} ({name}) via {trigger_type}: {command[:200]}',
                       'INFO', 'cron_manager')

            exit_code = -1
            stdout = ''
            stderr = ''
            try:
                # 使用 shell 执行，捕获输出
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                exit_code = result.returncode
                stdout = result.stdout or ''
                stderr = result.stderr or ''
            except subprocess.TimeoutExpired:
                exit_code = -2
                stderr = f'Command timed out after {timeout} seconds'
            except Exception as e:
                exit_code = -3
                stderr = str(e)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            status = 'success' if exit_code == 0 else 'failed'

            # 截断输出避免历史文件膨胀
            if len(stdout) > 8192:
                stdout = stdout[:8192] + '\n... [truncated]'
            if len(stderr) > 8192:
                stderr = stderr[:8192] + '\n... [truncated]'

            record = {
                'run_id': run_id,
                'task_id': task_id,
                'task_name': name,
                'command': command,
                'trigger_type': trigger_type,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': round(duration, 3),
                'exit_code': exit_code,
                'status': status,
                'stdout': stdout,
                'stderr': stderr
            }

            with self._lock:
                # 更新任务统计
                if task_id in self.tasks:
                    self.tasks[task_id]['last_run'] = start_time.isoformat()
                    self.tasks[task_id]['last_status'] = status
                    self.tasks[task_id]['run_count'] = self.tasks[task_id].get('run_count', 0) + 1
                    self._save_tasks()

                # 写入历史
                if task_id not in self.history:
                    self.history[task_id] = []
                self.history[task_id].insert(0, record)
                # 限制每个任务的历史条数
                if len(self.history[task_id]) > MAX_HISTORY_PER_TASK:
                    self.history[task_id] = self.history[task_id][:MAX_HISTORY_PER_TASK]
                self._save_history()

            log_system(f'Cron task {task_id} ({name}) finished: {status}, exit={exit_code}, '
                       f'duration={duration:.3f}s', 'INFO' if status == 'success' else 'ERROR', 'cron_manager')
        finally:
            with self._lock:
                self._running_tasks.discard(task_id)

    def run_task_now(self, task_id: str) -> Dict:
        """手动触发任务执行"""
        with self._lock:
            if task_id not in self.tasks:
                return {'status': 'error', 'message': f'Task {task_id} not found'}
            if task_id in self._running_tasks:
                return {'status': 'error', 'message': 'Task is already running'}

        # 在独立线程执行避免阻塞请求
        thread = threading.Thread(
            target=self._execute_task,
            args=(task_id, 'manual'),
            daemon=True
        )
        thread.start()
        log_system(f'Manually triggered cron task {task_id}', 'INFO', 'cron_manager')
        return {'status': 'success', 'message': 'Task triggered successfully'}

    def get_task_history(self, task_id: str, limit: int = 20) -> Dict:
        """获取任务执行历史"""
        with self._lock:
            if task_id not in self.history:
                return {'status': 'success', 'history': []}
            records = self.history[task_id][:limit]
            return {'status': 'success', 'history': records}

    def get_all_history(self, limit: int = 100) -> Dict:
        """获取所有任务的执行历史"""
        with self._lock:
            all_records = []
            for task_id, records in self.history.items():
                all_records.extend(records)
            # 按开始时间倒序
            all_records.sort(key=lambda r: r.get('start_time', ''), reverse=True)
            return {'status': 'success', 'history': all_records[:limit]}

    def clear_task_history(self, task_id: str) -> Dict:
        """清空指定任务的执行历史"""
        with self._lock:
            if task_id in self.history:
                del self.history[task_id]
                self._save_history()
            return {'status': 'success', 'message': 'History cleared'}

    # -------------------- 调度器 --------------------

    def _update_next_run(self, task_id: str) -> None:
        """计算并更新任务的下次运行时间"""
        task = self.tasks.get(task_id)
        if not task or not task['enabled']:
            self._next_run.pop(task_id, None)
            return
        try:
            cron = croniter(task['cron_expr'], datetime.now())
            self._next_run[task_id] = cron.get_next(datetime).isoformat()
        except Exception as e:
            log_system(f'Failed to compute next run for task {task_id}: {e}', 'ERROR', 'cron_manager')
            self._next_run.pop(task_id, None)

    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        log_system('Cron scheduler started', 'INFO', 'cron_manager')
        while self._running:
            try:
                now = datetime.now()
                with self._lock:
                    due_tasks = []
                    for task_id, task in self.tasks.items():
                        if not task['enabled']:
                            continue
                        next_run_str = self._next_run.get(task_id)
                        if not next_run_str:
                            continue
                        try:
                            next_run = datetime.fromisoformat(next_run_str)
                            if next_run <= now:
                                due_tasks.append(task_id)
                        except (ValueError, TypeError):
                            continue

                # 在锁外执行任务，避免长时间持锁
                for task_id in due_tasks:
                    # 启动子线程执行，不阻塞调度循环
                    thread = threading.Thread(
                        target=self._execute_task,
                        args=(task_id, 'scheduled'),
                        daemon=True
                    )
                    thread.start()
                    # 更新下次运行时间
                    with self._lock:
                        self._update_next_run(task_id)

            except Exception as e:
                log_system(f'Scheduler loop error: {e}', 'ERROR', 'cron_manager')

            # 等待下一轮
            time.sleep(SCHEDULER_INTERVAL)

        log_system('Cron scheduler stopped', 'INFO', 'cron_manager')

    def start_scheduler(self) -> None:
        """启动调度器线程"""
        if self._running:
            return
        # 初始化所有启用任务的下次运行时间
        with self._lock:
            for task_id in self.tasks:
                self._update_next_run(task_id)
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name='cron-scheduler'
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """停止调度器线程"""
        self._running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)


# 创建全局管理器实例
cron_manager = CronTaskManager()
