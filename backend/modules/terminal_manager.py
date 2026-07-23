"""
终端模拟器后端 - 专业级实现

特性：
- 基于 pty.fork() 的真实 PTY，支持完整 ANSI/256色/truecolor
- Socket.IO 实时双向通信
- 心跳保活（ping/pong + last_activity 活跃度跟踪）
- 会话超时自动清理（守护线程，避免僵尸进程）
- 每用户并发会话上限
- 输入大小限制（防粘贴炸弹）
- 并发安全的 resize（窗口尺寸调整）
- 优雅关闭：SIGTERM → 2s 超时 → SIGKILL
- 子线程使用 socketio.emit(..., to=sid) 避免闭包 emit 在 threading 模式下的隐患
"""
import os
import json
import time
import threading
import subprocess
import struct
import signal
import re
import errno
from datetime import datetime
from flask import request
from flask_socketio import SocketIO

# ============== 常量配置 ==============

TERMINAL_SESSIONS = {}
COMMAND_HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'command_history.json')

# 允许的 shell 白名单
ALLOWED_SHELLS = {
    '/bin/bash', '/bin/sh', '/bin/zsh',
    '/usr/bin/bash', '/usr/bin/sh', '/usr/bin/zsh'
}

# 心跳与超时
HEARTBEAT_INTERVAL = 30          # Socket.IO ping 间隔（秒）
SESSION_TIMEOUT = 30 * 60        # 30 分钟无活动自动清理
SESSION_CLEANUP_INTERVAL = 60    # 守护线程扫描间隔

# 安全限制
MAX_INPUT_CHUNK_SIZE = 64 * 1024   # 单次输入最大 64KB
MAX_SESSIONS_PER_USER = 5          # 每用户最多并发会话
MAX_TERMINAL_COLS = 400
MAX_TERMINAL_ROWS = 200

socketio = None
_sessions_lock = threading.RLock()
_cleanup_thread = None


# ============== JWT 验证 ==============

def _verify_terminal_token(token):
    """验证终端连接的 JWT 令牌"""
    if not token:
        return None
    try:
        import jwt
        from config.config import config_instance
        payload = jwt.decode(token, config_instance.SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception:
        return None


# ============== PTY 会话管理 ==============

def _close_pty(session):
    """优雅关闭 PTY：先关 fd，再 SIGTERM，2s 后仍存活则 SIGKILL"""
    fd = session.get('fd')
    pid = session.get('pid')

    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass
        session['fd'] = None

    if pid:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            pass

        # 守护线程：2s 后强制 kill
        def _force_kill():
            time.sleep(2)
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass

        threading.Thread(target=_force_kill, daemon=True).start()


def _terminate_session(session_id, reason='closed'):
    """统一终止会话（线程安全）"""
    with _sessions_lock:
        session = TERMINAL_SESSIONS.pop(session_id, None)
    if not session:
        return
    _close_pty(session)
    # socketio 可能在初始化前被调用（极端情况），需 None 检查
    if socketio is None:
        return
    try:
        socketio.emit('session_closed', {'reason': reason},
                      namespace='/terminal', to=session_id)
    except Exception:
        pass


def _session_reaper():
    """守护线程：定期清理超时会话"""
    while True:
        time.sleep(SESSION_CLEANUP_INTERVAL)
        now = time.time()
        expired = []
        with _sessions_lock:
            for sid, sess in TERMINAL_SESSIONS.items():
                if now - sess.get('last_activity', now) > SESSION_TIMEOUT:
                    expired.append(sid)
        for sid in expired:
            print(f"[terminal] reaping expired session {sid}")
            _terminate_session(sid, reason='timeout')


def _start_reaper():
    """启动会话清理守护线程（仅一次）"""
    global _cleanup_thread
    if _cleanup_thread is None or not _cleanup_thread.is_alive():
        _cleanup_thread = threading.Thread(target=_session_reaper, daemon=True)
        _cleanup_thread.start()


def _count_user_sessions(username):
    with _sessions_lock:
        return sum(1 for s in TERMINAL_SESSIONS.values() if s.get('user') == username)


# ============== Socket.IO 初始化 ==============

def init_socketio(app):
    global socketio
    from config.config import Config
    socketio = SocketIO(
        app,
        cors_allowed_origins=Config.CORS_ORIGINS,
        async_mode='threading',
        ping_timeout=60,
        ping_interval=HEARTBEAT_INTERVAL,
    )

    @socketio.on('connect', namespace='/terminal')
    def handle_connect():
        # 不在此验证 token；由 create_session 显式校验
        print(f"[terminal] client connected: {request.sid}")

    @socketio.on('disconnect', namespace='/terminal')
    def handle_disconnect():
        _terminate_session(request.sid, reason='disconnect')

    @socketio.on('terminal_input', namespace='/terminal')
    def handle_terminal_input(data):
        session_id = request.sid
        with _sessions_lock:
            session = TERMINAL_SESSIONS.get(session_id)
            fd = session.get('fd') if session else None
            if session:
                session['last_activity'] = time.time()
        if fd is None:
            return

        text = data.get('data', '')
        if not isinstance(text, str):
            return
        # 防粘贴炸弹
        if len(text) > MAX_INPUT_CHUNK_SIZE:
            text = text[:MAX_INPUT_CHUNK_SIZE]

        try:
            os.write(fd, text.encode('utf-8', errors='replace'))
        except OSError as e:
            if e.errno != errno.EIO:
                # PTY 已关闭
                _terminate_session(session_id, reason='write_error')

    @socketio.on('terminal_resize', namespace='/terminal')
    def handle_terminal_resize(data):
        session_id = request.sid
        with _sessions_lock:
            session = TERMINAL_SESSIONS.get(session_id)
            fd = session.get('fd') if session else None
        if fd is None:
            return

        rows = max(1, min(int(data.get('rows', 24)), MAX_TERMINAL_ROWS))
        cols = max(1, min(int(data.get('cols', 80)), MAX_TERMINAL_COLS))
        try:
            import termios, fcntl
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            with _sessions_lock:
                if session_id in TERMINAL_SESSIONS:
                    TERMINAL_SESSIONS[session_id]['rows'] = rows
                    TERMINAL_SESSIONS[session_id]['cols'] = cols
        except OSError:
            pass

    @socketio.on('create_session', namespace='/terminal')
    def handle_create_session(data):
        session_id = request.sid

        # 验证 JWT
        user_payload = _verify_terminal_token(data.get('token'))
        if not user_payload:
            socketio.emit('terminal_error',
                          {'message': 'Unauthorized: Invalid or missing token'},
                          namespace='/terminal', to=session_id)
            return

        username = user_payload.get('username', 'unknown')

        # 每用户会话数上限
        if _count_user_sessions(username) >= MAX_SESSIONS_PER_USER:
            socketio.emit('terminal_error',
                          {'message': f'Too many active sessions (max {MAX_SESSIONS_PER_USER})'},
                          namespace='/terminal', to=session_id)
            return

        # 关闭同 sid 的前序会话（同 sid 复用）
        _terminate_session(session_id, reason='replaced')

        rows = max(1, min(int(data.get('rows', 24)), MAX_TERMINAL_ROWS))
        cols = max(1, min(int(data.get('cols', 80)), MAX_TERMINAL_COLS))
        shell = data.get('shell', '/bin/bash')

        # 白名单校验
        if shell not in ALLOWED_SHELLS:
            socketio.emit('terminal_error',
                          {'message': f'Unauthorized shell: {shell}'},
                          namespace='/terminal', to=session_id)
            return
        # 路径格式校验
        if not re.match(r'^/[a-zA-Z0-9_./-]+$', shell):
            socketio.emit('terminal_error',
                          {'message': 'Invalid shell path'},
                          namespace='/terminal', to=session_id)
            return

        # 创建 PTY
        import pty
        try:
            pid, fd = pty.fork()
        except Exception as e:
            socketio.emit('terminal_error',
                          {'message': f'Failed to create terminal session: {str(e)}'},
                          namespace='/terminal', to=session_id)
            return

        if pid == 0:
            # 子进程：执行 shell
            os.environ['TERM'] = 'xterm-256color'
            os.environ['COLORTERM'] = 'truecolor'
            os.environ.setdefault('LANG', 'en_US.UTF-8')
            os.environ.setdefault('LC_ALL', 'en_US.UTF-8')
            try:
                os.execvp(shell, [shell])
            except Exception:
                os._exit(127)
        else:
            # 父进程：设置窗口大小并注册会话
            try:
                import termios, fcntl
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            except OSError:
                pass

            with _sessions_lock:
                TERMINAL_SESSIONS[session_id] = {
                    'fd': fd,
                    'pid': pid,
                    'created_at': datetime.now().isoformat(),
                    'last_activity': time.time(),
                    'shell': shell,
                    'user': username,
                    'rows': rows,
                    'cols': cols,
                }

            # 输出读取线程：注意用 socketio.emit(..., to=sid) 而非闭包 emit
            def read_output():
                while True:
                    with _sessions_lock:
                        session = TERMINAL_SESSIONS.get(session_id)
                        if not session or session.get('fd') is None:
                            break
                        cur_fd = session['fd']
                    try:
                        data_bytes = os.read(cur_fd, 65536)
                        if not data_bytes:
                            break
                        socketio.emit(
                            'terminal_output',
                            {'data': data_bytes.decode('utf-8', errors='replace')},
                            namespace='/terminal', to=session_id
                        )
                    except OSError:
                        break
                _terminate_session(session_id, reason='process_exit')

            threading.Thread(target=read_output, daemon=True).start()
            _start_reaper()

            socketio.emit('session_created', {'session_id': session_id},
                          namespace='/terminal', to=session_id)

    @socketio.on('ping_session', namespace='/terminal')
    def handle_ping(data):
        """客户端应用层心跳：刷新活跃时间"""
        session_id = request.sid
        with _sessions_lock:
            if session_id in TERMINAL_SESSIONS:
                TERMINAL_SESSIONS[session_id]['last_activity'] = time.time()
        socketio.emit('pong_session', {'time': time.time()},
                      namespace='/terminal', to=session_id)

    return socketio


def get_socketio():
    return socketio


# ============== 命令历史 / Shell 列表（供 HTTP API 调用） ==============

def _ensure_history_dir():
    """确保命令历史文件目录存在"""
    dir_path = os.path.dirname(COMMAND_HISTORY_FILE)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def get_command_history(username, limit=100):
    try:
        if os.path.exists(COMMAND_HISTORY_FILE):
            with open(COMMAND_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                user_history = history.get(username, [])
                return user_history[-limit:]
    except Exception as e:
        print(f"Failed to get command history: {e}")
    return []


def save_command_history(username, command):
    try:
        history = {}
        if os.path.exists(COMMAND_HISTORY_FILE):
            with open(COMMAND_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)

        if username not in history:
            history[username] = []

        history[username].append({
            'command': command,
            'timestamp': datetime.now().isoformat()
        })

        # 上限 1000 条
        if len(history[username]) > 1000:
            history[username] = history[username][-1000:]

        _ensure_history_dir()
        with open(COMMAND_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Failed to save command history: {e}")
        return False


def search_command_history(username, query):
    history = get_command_history(username, limit=1000)
    if not query:
        return history
    query = query.lower()
    return [item for item in history if query in item['command'].lower()]


def get_command_suggestions(username, partial_command):
    history = get_command_history(username, limit=500)
    partial = partial_command.lower()

    suggestions = []
    seen = set()

    for item in reversed(history):
        cmd = item['command']
        if cmd.lower().startswith(partial) and cmd not in seen:
            suggestions.append({
                'command': cmd,
                'timestamp': item['timestamp']
            })
            seen.add(cmd)
            if len(suggestions) >= 10:
                break

    return suggestions


def clear_command_history(username):
    try:
        history = {}
        if os.path.exists(COMMAND_HISTORY_FILE):
            with open(COMMAND_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        history[username] = []
        _ensure_history_dir()
        with open(COMMAND_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return {'status': 'success', 'message': 'Command history cleared'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_available_shells():
    shells = []
    common_shells = ['/bin/bash', '/bin/sh', '/bin/zsh', '/bin/fish', '/bin/dash']

    for shell in common_shells:
        if os.path.exists(shell):
            shells.append({
                'path': shell,
                'name': os.path.basename(shell)
            })

    try:
        with open('/etc/shells', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and os.path.exists(line):
                    if not any(s['path'] == line for s in shells):
                        shells.append({
                            'path': line,
                            'name': os.path.basename(line)
                        })
    except Exception:
        pass

    return shells


def check_ssh_available():
    try:
        result = subprocess.run(['which', 'ssh'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False
