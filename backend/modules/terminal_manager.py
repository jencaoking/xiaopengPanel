import os
import json
import time
import threading
import subprocess
import select
import socket
import struct
import termios
import pty
import fcntl
import errno
import signal
from datetime import datetime
from flask import request, jsonify
from flask_socketio import SocketIO, emit

TERMINAL_SESSIONS = {}
COMMAND_HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'command_history.json')

socketio = None

def init_socketio(app):
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    @socketio.on('connect', namespace='/terminal')
    def handle_connect():
        from flask_login import current_user
        print(f"Client connected: {request.sid}")
    
    @socketio.on('disconnect', namespace='/terminal')
    def handle_disconnect():
        session_id = request.sid
        if session_id in TERMINAL_SESSIONS:
            session = TERMINAL_SESSIONS[session_id]
            if session.get('process'):
                try:
                    os.killpg(os.getpgid(session['process'].pid), signal.SIGTERM)
                except:
                    pass
            del TERMINAL_SESSIONS[session_id]
        print(f"Client disconnected: {session_id}")
    
    @socketio.on('terminal_input', namespace='/terminal')
    def handle_terminal_input(data):
        session_id = request.sid
        if session_id in TERMINAL_SESSIONS:
            session = TERMINAL_SESSIONS[session_id]
            if session.get('fd') is not None:
                try:
                    os.write(session['fd'], data.get('data', '').encode())
                except OSError as e:
                    if e.errno != errno.EIO:
                        raise
    
    @socketio.on('terminal_resize', namespace='/terminal')
    def handle_terminal_resize(data):
        session_id = request.sid
        if session_id in TERMINAL_SESSIONS:
            session = TERMINAL_SESSIONS[session_id]
            if session.get('fd') is not None:
                winsize = struct.pack('HHHH', data.get('rows', 24), data.get('cols', 80), 0, 0)
                fcntl.ioctl(session['fd'], termios.TIOCSWINSZ, winsize)
    
    @socketio.on('create_session', namespace='/terminal')
    def handle_create_session(data):
        session_id = request.sid
        rows = data.get('rows', 24)
        cols = data.get('cols', 80)
        shell = data.get('shell', '/bin/bash')
        
        pid, fd = pty.fork()
        
        if pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.environ['COLORTERM'] = 'truecolor'
            os.execvp(shell, [shell])
        else:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
            
            TERMINAL_SESSIONS[session_id] = {
                'fd': fd,
                'process': None,
                'pid': pid,
                'created_at': datetime.now().isoformat(),
                'shell': shell
            }
            
            def read_output():
                while session_id in TERMINAL_SESSIONS:
                    try:
                        data = os.read(fd, 65536)
                        if data:
                            emit('terminal_output', {'data': data.decode('utf-8', errors='replace')}, namespace='/terminal')
                        else:
                            break
                    except OSError:
                        break
                    except Exception as e:
                        print(f"Read error: {e}")
                        break
                
                emit('session_closed', {}, namespace='/terminal')
            
            thread = threading.Thread(target=read_output, daemon=True)
            thread.start()
            
            emit('session_created', {'session_id': session_id}, namespace='/terminal')
    
    return socketio

def get_socketio():
    return socketio

class TerminalSession:
    def __init__(self, session_id, shell='/bin/bash', rows=24, cols=80):
        self.session_id = session_id
        self.shell = shell
        self.rows = rows
        self.cols = cols
        self.fd = None
        self.pid = None
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.history = []
    
    def create(self):
        pid, fd = pty.fork()
        
        if pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.environ['COLORTERM'] = 'truecolor'
            os.execvp(self.shell, [self.shell])
        else:
            self.pid = pid
            self.fd = fd
            self.resize(self.rows, self.cols)
            return True
        return False
    
    def resize(self, rows, cols):
        if self.fd is not None:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
            self.rows = rows
            self.cols = cols
    
    def write(self, data):
        if self.fd is not None:
            try:
                os.write(self.fd, data.encode() if isinstance(data, str) else data)
                self.last_activity = datetime.now()
                return True
            except OSError:
                return False
        return False
    
    def read(self):
        if self.fd is not None:
            try:
                return os.read(self.fd, 65536)
            except OSError:
                return None
        return None
    
    def close(self):
        if self.pid:
            try:
                os.killpg(os.getpgid(self.pid), signal.SIGTERM)
            except:
                pass
        if self.fd is not None:
            try:
                os.close(self.fd)
            except:
                pass

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
        
        if len(history[username]) > 1000:
            history[username] = history[username][-1000:]
        
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
    except:
        pass
    
    return shells

def check_ssh_available():
    try:
        result = subprocess.run(['which', 'ssh'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False
