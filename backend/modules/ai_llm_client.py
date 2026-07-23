"""
AI LLM 统一客户端

支持 OpenAI 兼容格式的云端 API（DeepSeek / 通义千问 / Moonshot / OpenAI 等）。
提供：
- 普通对话补全
- 流式对话补全（SSE）
- 函数/工具调用（Function Calling）
- 嵌入向量（可选）

所有 API Key 从 config.json 的 ai 段读取，支持运行时热更新。
"""

import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Generator

logger = logging.getLogger(__name__)

# 尝试导入 requests（优先），回退到 urllib
try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False
    import urllib.request
    import urllib.error

# 默认供应商配置（OpenAI 兼容端点）
_DEFAULT_PROVIDERS = {
    'deepseek': {
        'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat',
        'models': ['deepseek-chat', 'deepseek-reasoner'],
    },
    'openai': {
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    },
    'qwen': {
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-plus',
        'models': ['qwen-plus', 'qwen-turbo', 'qwen-max'],
    },
    'moonshot': {
        'base_url': 'https://api.moonshot.cn/v1',
        'model': 'moonshot-v1-8k',
        'models': ['moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k'],
    },
    'custom': {
        'base_url': '',
        'model': '',
        'models': [],
    },
}


class LLMClient:
    """
    统一 LLM 客户端（单例）

    通过 get_instance() 获取，配置从 config_instance 动态读取。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def _get_ai_config(self) -> Dict[str, Any]:
        """从全局配置读取 AI 段"""
        try:
            from config.config import config_instance
            cfg = config_instance.get_config()
            return cfg.get('ai', {})
        except Exception:
            return {}

    def is_available(self) -> bool:
        """检查 AI 服务是否可用（已配置 API Key）"""
        cfg = self._get_ai_config()
        return bool(cfg.get('enabled', False) and cfg.get('api_key'))

    def get_provider_info(self) -> Dict[str, Any]:
        """获取当前供应商信息"""
        cfg = self._get_ai_config()
        provider = cfg.get('provider', 'deepseek')
        base_url = cfg.get('base_url') or _DEFAULT_PROVIDERS.get(provider, {}).get('base_url', '')
        model = cfg.get('model') or _DEFAULT_PROVIDERS.get(provider, {}).get('model', '')
        return {
            'provider': provider,
            'base_url': base_url,
            'model': model,
            'available': self.is_available(),
        }

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        cfg = self._get_ai_config()
        api_key = cfg.get('api_key', '')
        return {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

    def _build_payload(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """构建请求体"""
        cfg = self._get_ai_config()
        provider = cfg.get('provider', 'deepseek')
        default_model = model or cfg.get('model') or _DEFAULT_PROVIDERS.get(provider, {}).get('model', 'deepseek-chat')

        payload = {
            'model': default_model,
            'messages': messages,
            'temperature': cfg.get('temperature', 0.3) if temperature is None else temperature,
            'max_tokens': cfg.get('max_tokens', 4096) if max_tokens is None else max_tokens,
            'stream': stream,
        }

        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = tool_choice or 'auto'

        return payload

    def chat(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        retry: int = 2,
    ) -> Dict[str, Any]:
        """
        同步对话补全

        :param messages: 消息列表 [{"role": "system/user/assistant/tool", "content": "..."}]
        :param tools: 工具定义列表（Function Calling）
        :return: {"content": str, "tool_calls": list, "usage": dict, "raw": dict}
        """
        cfg = self._get_ai_config()
        if not self.is_available():
            return {
                'content': 'AI 服务未配置或未启用。请在系统配置中设置 API Key。',
                'tool_calls': [],
                'usage': {},
                'error': 'not_configured',
            }

        provider = cfg.get('provider', 'deepseek')
        base_url = cfg.get('base_url') or _DEFAULT_PROVIDERS.get(provider, {}).get('base_url', '')
        url = f"{base_url.rstrip('/')}/chat/completions"

        payload = self._build_payload(
            messages, model, temperature, max_tokens, tools, tool_choice, stream=False
        )
        headers = self._build_headers()

        last_error = None
        for attempt in range(retry + 1):
            try:
                if _HAS_REQUESTS:
                    resp = _requests.post(url, json=payload, headers=headers, timeout=120)
                    if resp.status_code != 200:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                        if resp.status_code in (429, 500, 502, 503) and attempt < retry:
                            time.sleep(2 ** attempt)
                            continue
                        return {'content': '', 'tool_calls': [], 'usage': {}, 'error': last_error}
                    data = resp.json()
                else:
                    req = urllib.request.Request(
                        url, data=json.dumps(payload).encode('utf-8'),
                        headers=headers, method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        data = json.loads(resp.read().decode('utf-8'))

                choice = data.get('choices', [{}])[0]
                message = choice.get('message', {})
                return {
                    'content': message.get('content', ''),
                    'tool_calls': message.get('tool_calls', []),
                    'usage': data.get('usage', {}),
                    'finish_reason': choice.get('finish_reason', ''),
                    'raw': data,
                }
            except Exception as e:
                last_error = str(e)
                if attempt < retry:
                    time.sleep(2 ** attempt)
                    continue

        return {'content': '', 'tool_calls': [], 'usage': {}, 'error': last_error}

    def chat_stream(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式对话补全（SSE）

        :yield: {"type": "content/tool_call/done/error", "content": str, ...}
        """
        cfg = self._get_ai_config()
        if not self.is_available():
            yield {'type': 'error', 'content': 'AI 服务未配置或未启用'}
            return

        provider = cfg.get('provider', 'deepseek')
        base_url = cfg.get('base_url') or _DEFAULT_PROVIDERS.get(provider, {}).get('base_url', '')
        url = f"{base_url.rstrip('/')}/chat/completions"

        payload = self._build_payload(
            messages, model, temperature, max_tokens, tools, stream=True
        )
        headers = self._build_headers()

        try:
            if _HAS_REQUESTS:
                resp = _requests.post(url, json=payload, headers=headers, timeout=180, stream=True)
                if resp.status_code != 200:
                    yield {'type': 'error', 'content': f"HTTP {resp.status_code}: {resp.text[:200]}"}
                    return
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith('data: '):
                        line = line[6:]
                    if line.strip() == '[DONE]':
                        yield {'type': 'done'}
                        return
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get('choices', [{}])[0].get('delta', {})
                        if delta.get('content'):
                            yield {'type': 'content', 'content': delta['content']}
                        if delta.get('tool_calls'):
                            yield {'type': 'tool_call', 'tool_calls': delta['tool_calls']}
                    except json.JSONDecodeError:
                        continue
            else:
                # urllib 流式读取
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode('utf-8'),
                    headers=headers, method='POST'
                )
                with urllib.request.urlopen(req, timeout=180) as resp:
                    buffer = b''
                    for chunk in iter(lambda: resp.read(1024), b''):
                        buffer += chunk
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            line = line.decode('utf-8', errors='ignore').strip()
                            if not line:
                                continue
                            if line.startswith('data: '):
                                line = line[6:]
                            if line == '[DONE]':
                                yield {'type': 'done'}
                                return
                            try:
                                data = json.loads(line)
                                delta = data.get('choices', [{}])[0].get('delta', {})
                                if delta.get('content'):
                                    yield {'type': 'content', 'content': delta['content']}
                                if delta.get('tool_calls'):
                                    yield {'type': 'tool_call', 'tool_calls': delta['tool_calls']}
                            except json.JSONDecodeError:
                                continue
            yield {'type': 'done'}
        except Exception as e:
            yield {'type': 'error', 'content': str(e)}


# 模块级单例
def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    return LLMClient()


# 系统提示词模板
SYSTEM_PROMPTS = {
    'assistant': """你是一个专业的服务器运维 AI 助手，集成在 xiaopengPanel 管理面板中。
你的职责：
1. 回答运维相关问题，提供专业建议
2. 分析系统状态，识别潜在问题
3. 诊断故障根因，给出修复方案
4. 在用户授权下执行修复操作

工作原则：
- 回答简洁准确，使用中文
- 涉及执行操作时，必须先说明将做什么、有什么影响，等待用户确认
- 对危险操作保持谨慎，明确提示风险
- 如果信息不足，主动调用工具获取系统状态
- 不要编造数据，基于工具返回的真实数据进行分析
""",

    'diagnostic': """你是一个服务器故障诊断专家。你的任务是：
1. 收集系统指标（CPU、内存、磁盘、网络、进程、服务状态）
2. 分析日志，识别异常模式
3. 关联指标与日志，定位根因
4. 给出结构化诊断报告：问题现象、根因分析、影响评估、修复建议

输出格式：
## 诊断报告
### 问题现象
（描述观察到的异常）
### 根因分析
（分析可能的原因，按可能性排序）
### 影响评估
（对系统的影响范围和严重程度）
### 修复建议
（具体可操作的修复步骤）
""",

    'alert': """你是服务器告警分析专家。对每条告警进行智能分级：
- critical: 需立即处理，系统功能受损
- warning: 需关注，可能恶化
- info: 正常波动，无需处理

输出 JSON 格式：
{"severity": "critical|warning|info", "analysis": "原因分析", "suggestion": "处理建议", "confidence": 0-1}
""",

    'repair': """你是服务器自动修复引擎。你的任务是：
1. 根据诊断结果选择合适的修复脚本
2. 说明修复步骤和预期效果
3. 提示回滚方案
4. 执行前必须获得用户确认

安全原则：
- 不执行任何破坏性操作（如 rm -rf、dd、mkfs）
- 不修改系统关键文件（/etc/passwd, /etc/shadow 等）
- 所有执行操作记录审计日志
- 优先选择可逆的修复方案
""",
}


def build_system_prompt(scenario: str = 'assistant', extra_context: str = '') -> str:
    """
    构建系统提示词

    :param scenario: 场景 assistant/diagnostic/alert/repair
    :param extra_context: 额外上下文（如系统状态摘要）
    """
    prompt = SYSTEM_PROMPTS.get(scenario, SYSTEM_PROMPTS['assistant'])
    if extra_context:
        prompt += f"\n\n## 当前系统上下文\n{extra_context}"
    return prompt


def get_system_context_snapshot() -> str:
    """获取系统状态快照，作为 AI 上下文"""
    try:
        from modules.system_info import get_real_time_status, get_system_info
        status = get_real_time_status()
        info = get_system_info()

        lines = [
            f"主机名: {info.get('hostname', 'unknown')}",
            f"操作系统: {info.get('os', 'unknown')} {info.get('os_version', '')}",
            f"运行时间: {info.get('uptime', 'unknown')}",
            f"CPU 使用率: {status.get('cpu_usage', 'N/A')}%",
            f"内存使用率: {status.get('memory_usage', 'N/A')}%",
            f"磁盘使用率: {status.get('disk_usage', 'N/A')}%",
            f"负载均衡: {status.get('load_average', 'N/A')}",
        ]

        # 网络状态
        net = status.get('network', {})
        if net:
            lines.append(f"网络上传: {net.get('sent_speed', 'N/A')} | 下载: {net.get('recv_speed', 'N/A')}")

        return '\n'.join(lines)
    except Exception as e:
        return f"（系统状态获取失败: {e}）"
