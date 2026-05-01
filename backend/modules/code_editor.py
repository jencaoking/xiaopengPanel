import os
import re
import json
from datetime import datetime

EDITOR_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'editor_settings.json')
FILE_SESSIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'file_sessions.json')

LANGUAGE_CONFIGS = {
    'javascript': {
        'extensions': ['.js', '.jsx', '.mjs', '.cjs'],
        'keywords': ['async', 'await', 'break', 'case', 'catch', 'class', 'const', 'continue', 
                     'debugger', 'default', 'delete', 'do', 'else', 'export', 'extends', 'false',
                     'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new',
                     'null', 'return', 'super', 'switch', 'this', 'throw', 'true', 'try', 'typeof',
                     'undefined', 'var', 'void', 'while', 'with', 'yield'],
        'builtins': ['console', 'window', 'document', 'Array', 'Object', 'String', 'Number', 
                     'Boolean', 'Function', 'Symbol', 'Map', 'Set', 'Promise', 'JSON', 'Math',
                     'Date', 'RegExp', 'Error', 'setTimeout', 'setInterval', 'fetch', 'require'],
        'comment_start': '//',
        'comment_block_start': '/*',
        'comment_block_end': '*/'
    },
    'typescript': {
        'extensions': ['.ts', '.tsx'],
        'keywords': ['abstract', 'any', 'as', 'async', 'await', 'boolean', 'break', 'case', 'catch',
                     'class', 'const', 'constructor', 'continue', 'debugger', 'declare', 'default',
                     'delete', 'do', 'else', 'enum', 'export', 'extends', 'false', 'finally', 'for',
                     'from', 'function', 'get', 'if', 'implements', 'import', 'in', 'instanceof',
                     'interface', 'let', 'module', 'namespace', 'new', 'null', 'number', 'object',
                     'private', 'protected', 'public', 'readonly', 'return', 'set', 'static', 'string',
                     'super', 'switch', 'this', 'throw', 'true', 'try', 'type', 'typeof', 'undefined',
                     'var', 'void', 'while', 'with', 'yield'],
        'builtins': ['console', 'window', 'document', 'Array', 'Object', 'String', 'Number',
                     'Boolean', 'Function', 'Symbol', 'Map', 'Set', 'Promise', 'JSON', 'Math',
                     'Date', 'RegExp', 'Error', 'Partial', 'Required', 'Readonly', 'Record', 'Pick', 'Omit'],
        'comment_start': '//',
        'comment_block_start': '/*',
        'comment_block_end': '*/'
    },
    'python': {
        'extensions': ['.py', '.pyw', '.pyi'],
        'keywords': ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
                     'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
                     'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
                     'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'],
        'builtins': ['abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable', 'chr', 'dict',
                     'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter', 'float', 'format',
                     'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex', 'id',
                     'input', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list', 'locals',
                     'map', 'max', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow', 'print',
                     'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
                     'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'],
        'comment_start': '#',
        'comment_block_start': '"""',
        'comment_block_end': '"""'
    },
    'java': {
        'extensions': ['.java'],
        'keywords': ['abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char',
                     'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
                     'extends', 'final', 'finally', 'float', 'for', 'goto', 'if', 'implements',
                     'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new', 'package',
                     'private', 'protected', 'public', 'return', 'short', 'static', 'strictfp',
                     'super', 'switch', 'synchronized', 'this', 'throw', 'throws', 'transient',
                     'try', 'void', 'volatile', 'while'],
        'builtins': ['String', 'Integer', 'Long', 'Double', 'Float', 'Boolean', 'Character',
                     'Byte', 'Short', 'Object', 'Class', 'System', 'Math', 'ArrayList', 'HashMap',
                     'HashSet', 'List', 'Map', 'Set', 'Exception', 'RuntimeException'],
        'comment_start': '//',
        'comment_block_start': '/*',
        'comment_block_end': '*/'
    },
    'html': {
        'extensions': ['.html', '.htm', '.xhtml'],
        'keywords': ['html', 'head', 'body', 'div', 'span', 'p', 'a', 'img', 'ul', 'ol', 'li',
                     'table', 'tr', 'td', 'th', 'form', 'input', 'button', 'select', 'option',
                     'textarea', 'label', 'script', 'style', 'link', 'meta', 'title', 'header',
                     'footer', 'nav', 'section', 'article', 'aside', 'main', 'figure', 'figcaption'],
        'builtins': ['class', 'id', 'style', 'src', 'href', 'alt', 'title', 'type', 'name',
                     'value', 'placeholder', 'disabled', 'readonly', 'required', 'checked'],
        'comment_start': None,
        'comment_block_start': '<!--',
        'comment_block_end': '-->'
    },
    'css': {
        'extensions': ['.css', '.scss', '.sass', '.less'],
        'keywords': ['@import', '@media', '@keyframes', '@font-face', '@supports', '@page',
                     'important', 'inherit', 'initial', 'unset', 'revert', 'all'],
        'builtins': ['display', 'position', 'top', 'right', 'bottom', 'left', 'width', 'height',
                     'margin', 'padding', 'border', 'background', 'color', 'font', 'text-align',
                     'flex', 'grid', 'transform', 'transition', 'animation', 'opacity', 'z-index',
                     'overflow', 'visibility', 'cursor', 'box-shadow', 'border-radius'],
        'comment_start': None,
        'comment_block_start': '/*',
        'comment_block_end': '*/'
    },
    'json': {
        'extensions': ['.json', '.jsonc'],
        'keywords': ['true', 'false', 'null'],
        'builtins': [],
        'comment_start': '//',
        'comment_block_start': None,
        'comment_block_end': None
    },
    'yaml': {
        'extensions': ['.yaml', '.yml'],
        'keywords': ['true', 'false', 'null', 'yes', 'no', 'on', 'off'],
        'builtins': [],
        'comment_start': '#',
        'comment_block_start': None,
        'comment_block_end': None
    },
    'sql': {
        'extensions': ['.sql'],
        'keywords': ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
                     'ALTER', 'TABLE', 'INDEX', 'VIEW', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
                     'ON', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'AS', 'ORDER',
                     'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'UNION', 'DISTINCT', 'COUNT', 'SUM',
                     'AVG', 'MAX', 'MIN', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'CONSTRAINT',
                     'DEFAULT', 'AUTO_INCREMENT', 'INT', 'VARCHAR', 'TEXT', 'BOOLEAN', 'DATE', 'DATETIME'],
        'builtins': ['NOW', 'CURDATE', 'CURTIME', 'DATE_FORMAT', 'CONCAT', 'SUBSTRING', 'TRIM',
                     'UPPER', 'LOWER', 'LENGTH', 'COALESCE', 'IFNULL', 'NULLIF'],
        'comment_start': '--',
        'comment_block_start': '/*',
        'comment_block_end': '*/'
    },
    'shell': {
        'extensions': ['.sh', '.bash', '.zsh'],
        'keywords': ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done', 'case',
                     'esac', 'function', 'return', 'exit', 'break', 'continue', 'local', 'export',
                     'readonly', 'declare', 'unset', 'shift', 'source', 'eval', 'exec'],
        'builtins': ['echo', 'printf', 'read', 'cd', 'pwd', 'ls', 'cat', 'grep', 'sed', 'awk',
                     'find', 'mkdir', 'rm', 'cp', 'mv', 'touch', 'chmod', 'chown', 'ps', 'kill',
                     'top', 'htop', 'df', 'du', 'free', 'uptime', 'date', 'time', 'sleep', 'wait'],
        'comment_start': '#',
        'comment_block_start': None,
        'comment_block_end': None
    },
    'xml': {
        'extensions': ['.xml', '.xsl', '.xslt', '.svg'],
        'keywords': [],
        'builtins': [],
        'comment_start': None,
        'comment_block_start': '<!--',
        'comment_block_end': '-->'
    },
    'markdown': {
        'extensions': ['.md', '.markdown'],
        'keywords': [],
        'builtins': [],
        'comment_start': None,
        'comment_block_start': '<!--',
        'comment_block_end': '-->'
    }
}

def get_language_from_extension(filename):
    ext = os.path.splitext(filename)[1].lower()
    for lang, config in LANGUAGE_CONFIGS.items():
        if ext in config['extensions']:
            return lang
    return 'plaintext'

def get_language_config(language):
    return LANGUAGE_CONFIGS.get(language, {
        'keywords': [],
        'builtins': [],
        'comment_start': None,
        'comment_block_start': None,
        'comment_block_end': None
    })

def get_all_languages():
    return [
        {'id': lang, 'name': lang.capitalize(), 'extensions': config['extensions']}
        for lang, config in LANGUAGE_CONFIGS.items()
    ]

def tokenize_code(code, language):
    config = get_language_config(language)
    tokens = []
    
    patterns = [
        ('string_double', r'"(?:[^"\\]|\\.)*"'),
        ('string_single', r"'(?:[^'\\]|\\.)*'"),
        ('string_template', r'`(?:[^`\\]|\\.)*`'),
        ('number', r'\b\d+\.?\d*\b'),
        ('comment_line', r'//.*$' if config.get('comment_start') == '//' else r'#.*$' if config.get('comment_start') == '#' else None),
        ('comment_block', r'/\*[\s\S]*?\*/' if config.get('comment_block_start') == '/*' else None),
        ('keyword', r'\b(' + '|'.join(config['keywords']) + r')\b' if config['keywords'] else None),
        ('builtin', r'\b(' + '|'.join(config['builtins']) + r')\b' if config['builtins'] else None),
        ('function', r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()'),
        ('operator', r'[+\-*/%=<>!&|^~]+'),
        ('punctuation', r'[{}[\]();,.:]'),
        ('whitespace', r'\s+'),
        ('identifier', r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ]
    
    if language == 'html':
        patterns = [
            ('tag_open', r'</?[a-zA-Z][a-zA-Z0-9]*'),
            ('tag_close', r'/?>'),
            ('attribute', r'\s([a-zA-Z-]+)='),
            ('string_double', r'"(?:[^"\\]|\\.)*"'),
            ('string_single', r"'(?:[^'\\]|\\.)*'"),
            ('comment', r'<!--[\s\S]*?-->'),
            ('text', r'[^<]+'),
        ]
    elif language == 'css':
        patterns = [
            ('comment', r'/\*[\s\S]*?\*/'),
            ('property', r'([a-zA-Z-]+)\s*:'),
            ('value', r':\s*([^;{}]+)'),
            ('selector', r'([.#]?[a-zA-Z_][a-zA-Z0-9_-]*)'),
            ('at_rule', r'@[a-zA-Z-]+'),
            ('number', r'\b\d+\.?\d*(px|em|rem|%|vh|vw|s|ms)?\b'),
            ('punctuation', r'[{};:,]'),
            ('whitespace', r'\s+'),
        ]
    
    valid_patterns = [(name, pattern) for name, pattern in patterns if pattern]
    
    pos = 0
    while pos < len(code):
        match = None
        for token_type, pattern in valid_patterns:
            regex = re.compile(pattern, re.MULTILINE)
            match = regex.match(code, pos)
            if match:
                value = match.group(0)
                tokens.append({
                    'type': token_type,
                    'value': value,
                    'start': pos,
                    'end': pos + len(value)
                })
                pos = match.end()
                break
        
        if not match:
            tokens.append({
                'type': 'unknown',
                'value': code[pos],
                'start': pos,
                'end': pos + 1
            })
            pos += 1
    
    return tokens

def get_code_completions(code, language, cursor_position):
    config = get_language_config(language)
    
    line_start = code.rfind('\n', 0, cursor_position) + 1
    current_line = code[line_start:cursor_position]
    
    completions = []
    
    word_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)$', current_line)
    prefix = word_match.group(1) if word_match else ''
    
    if prefix:
        for keyword in config.get('keywords', []):
            if keyword.lower().startswith(prefix.lower()) and keyword not in [c['text'] for c in completions]:
                completions.append({
                    'text': keyword,
                    'type': 'keyword',
                    'display': keyword
                })
        
        for builtin in config.get('builtins', []):
            if builtin.lower().startswith(prefix.lower()) and builtin not in [c['text'] for c in completions]:
                completions.append({
                    'text': builtin,
                    'type': 'builtin',
                    'display': builtin
                })
        
        identifier_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        identifiers = set(re.findall(identifier_pattern, code))
        
        for identifier in identifiers:
            if identifier.lower().startswith(prefix.lower()) and identifier not in [c['text'] for c in completions]:
                if identifier not in config.get('keywords', []) and identifier not in config.get('builtins', []):
                    completions.append({
                        'text': identifier,
                        'type': 'variable',
                        'display': identifier
                    })
    
    if '.' in current_line:
        obj_match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\.$', current_line)
        if obj_match:
            obj_name = obj_match.group(1)
            method_completions = get_object_methods(obj_name, language)
            completions.extend(method_completions)
    
    return completions[:20]

def get_object_methods(obj_name, language):
    methods = []
    
    if language in ['javascript', 'typescript']:
        object_methods = {
            'Array': ['push', 'pop', 'shift', 'unshift', 'slice', 'splice', 'map', 'filter', 
                      'reduce', 'find', 'findIndex', 'forEach', 'includes', 'indexOf', 'join', 'sort', 'reverse'],
            'String': ['charAt', 'charCodeAt', 'concat', 'includes', 'endsWith', 'indexOf', 
                       'lastIndexOf', 'match', 'replace', 'search', 'slice', 'split', 'substring', 
                       'toLowerCase', 'toUpperCase', 'trim'],
            'Object': ['keys', 'values', 'entries', 'assign', 'freeze', 'seal', 'hasOwnProperty'],
            'Promise': ['then', 'catch', 'finally', 'all', 'race', 'resolve', 'reject'],
            'console': ['log', 'error', 'warn', 'info', 'debug', 'table', 'time', 'timeEnd']
        }
        
        if obj_name in object_methods:
            for method in object_methods[obj_name]:
                methods.append({
                    'text': method,
                    'type': 'method',
                    'display': f'{obj_name}.{method}'
                })
    
    elif language == 'python':
        object_methods = {
            'str': ['upper', 'lower', 'strip', 'split', 'join', 'replace', 'find', 'format', 
                    'startswith', 'endswith', 'isdigit', 'isalpha', 'isalnum'],
            'list': ['append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count',
                     'sort', 'reverse', 'copy'],
            'dict': ['keys', 'values', 'items', 'get', 'pop', 'update', 'clear', 'copy', 'setdefault'],
            'set': ['add', 'remove', 'discard', 'pop', 'clear', 'union', 'intersection', 'difference']
        }
        
        if obj_name in object_methods:
            for method in object_methods[obj_name]:
                methods.append({
                    'text': method,
                    'type': 'method',
                    'display': f'{obj_name}.{method}'
                })
    
    return methods

def search_in_file(content, query, case_sensitive=False, whole_word=False, regex=False):
    results = []
    lines = content.split('\n')
    
    flags = 0 if case_sensitive else re.IGNORECASE
    
    if regex:
        pattern = query
    else:
        pattern = re.escape(query)
        if whole_word:
            pattern = r'\b' + pattern + r'\b'
    
    try:
        compiled = re.compile(pattern, flags)
        
        for line_num, line in enumerate(lines, 1):
            matches = list(compiled.finditer(line))
            for match in matches:
                results.append({
                    'line': line_num,
                    'column': match.start() + 1,
                    'end_column': match.end() + 1,
                    'text': line,
                    'match': match.group()
                })
    except re.error as e:
        return {'error': str(e)}
    
    return results

def replace_in_file(content, search, replace, case_sensitive=False, whole_word=False, regex=False):
    flags = 0 if case_sensitive else re.IGNORECASE
    
    if regex:
        pattern = search
    else:
        pattern = re.escape(search)
        if whole_word:
            pattern = r'\b' + pattern + r'\b'
    
    try:
        compiled = re.compile(pattern, flags)
        new_content, count = compiled.subn(replace, content)
        return {
            'content': new_content,
            'replacements': count
        }
    except re.error as e:
        return {'error': str(e)}

def search_in_files(base_path, query, file_patterns=None, case_sensitive=False, whole_word=False, regex=False):
    if file_patterns is None:
        file_patterns = ['*.py', '*.js', '*.ts', '*.html', '*.css', '*.json', '*.yaml', '*.yml', '*.sh', '*.sql']
    
    results = []
    
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules' and d != '__pycache__']
        
        for file in files:
            if any(file.endswith(ext.replace('*', '')) for ext in file_patterns):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    file_results = search_in_file(content, query, case_sensitive, whole_word, regex)
                    
                    if 'error' not in file_results and file_results:
                        results.append({
                            'file': file_path,
                            'relative_path': os.path.relpath(file_path, base_path),
                            'matches': file_results,
                            'match_count': len(file_results)
                        })
                except Exception as e:
                    pass
    
    return results

def get_editor_settings(username):
    try:
        if os.path.exists(EDITOR_SETTINGS_FILE):
            with open(EDITOR_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get(username, get_default_editor_settings())
    except:
        pass
    return get_default_editor_settings()

def save_editor_settings(username, settings):
    try:
        all_settings = {}
        if os.path.exists(EDITOR_SETTINGS_FILE):
            with open(EDITOR_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                all_settings = json.load(f)
        
        all_settings[username] = settings
        
        with open(EDITOR_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_settings, f, indent=2, ensure_ascii=False)
        
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_default_editor_settings():
    return {
        'theme': 'vs-dark',
        'fontSize': 14,
        'fontFamily': 'Consolas, Monaco, monospace',
        'tabSize': 4,
        'insertSpaces': True,
        'wordWrap': 'on',
        'lineNumbers': 'on',
        'minimap': True,
        'autoSave': True,
        'autoSaveDelay': 1000,
        'formatOnSave': True,
        'bracketPairColorization': True,
        'highlightActiveLine': True,
        'showInvisibles': False,
        'scrollBeyondLastLine': False
    }

def save_file_session(username, session_data):
    try:
        sessions = {}
        if os.path.exists(FILE_SESSIONS_FILE):
            with open(FILE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
        
        if username not in sessions:
            sessions[username] = []
        
        existing = next((s for s in sessions[username] if s['path'] == session_data['path']), None)
        if existing:
            existing.update(session_data)
        else:
            sessions[username].append(session_data)
        
        if len(sessions[username]) > 20:
            sessions[username] = sessions[username][-20:]
        
        with open(FILE_SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
        
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_file_sessions(username):
    try:
        if os.path.exists(FILE_SESSIONS_FILE):
            with open(FILE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
                return sessions.get(username, [])
    except:
        pass
    return []

def close_file_session(username, file_path):
    try:
        sessions = {}
        if os.path.exists(FILE_SESSIONS_FILE):
            with open(FILE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
        
        if username in sessions:
            sessions[username] = [s for s in sessions[username] if s['path'] != file_path]
            
            with open(FILE_SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
        
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_file_outline(content, language):
    outline = []
    
    if language in ['javascript', 'typescript']:
        func_pattern = r'(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?\(.*?\)\s*=>|class\s+([a-zA-Z_][a-zA-Z0-9_]*))'
        for match in re.finditer(func_pattern, content):
            name = match.group(1) or match.group(2) or match.group(3)
            if name:
                line_num = content[:match.start()].count('\n') + 1
                outline.append({
                    'name': name,
                    'type': 'function' if match.group(1) or match.group(2) else 'class',
                    'line': line_num
                })
    
    elif language == 'python':
        func_pattern = r'(?:def\s+([a-zA-Z_][a-zA-Z0-9_]*)|class\s+([a-zA-Z_][a-zA-Z0-9_]*))'
        for match in re.finditer(func_pattern, content):
            name = match.group(1) or match.group(2)
            if name:
                line_num = content[:match.start()].count('\n') + 1
                outline.append({
                    'name': name,
                    'type': 'function' if match.group(1) else 'class',
                    'line': line_num
                })
    
    elif language == 'html':
        tag_pattern = r'<(h[1-6]|title|header|footer|nav|main|section|article|aside)[^>]*>(.*?)</\1>'
        for match in re.finditer(tag_pattern, content, re.IGNORECASE | re.DOTALL):
            tag = match.group(1).lower()
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()[:50]
            line_num = content[:match.start()].count('\n') + 1
            outline.append({
                'name': text or tag,
                'type': tag,
                'line': line_num
            })
    
    return outline
