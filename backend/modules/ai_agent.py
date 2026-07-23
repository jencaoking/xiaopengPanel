"""
L3 Agent 引擎

实现 ReAct (Reasoning + Acting) 循环：
1. 接收用户输入 + 会话历史
2. LLM 决定调用工具或直接回复
3. L1/L2 工具自动执行 → 结果回传 LLM
4. L3/L4 工具暂停 → 返回确认请求给用户
5. 用户确认后继续执行
6. 达到最大迭代或 LLM 不再调用工具时结束

L3 安全机制：
- 自动执行边界：仅 L1/L2 工具
- 人工确认：L3/L4 工具需用户显式确认
- 审计追踪：所有工具调用记录到日志
- 迭代限制：防止无限循环
"""

import json
import time
import uuid
import logging
import threading
from typing import Dict, List, Any, Optional, Generator

from modules.ai_llm_client import get_llm_client, build_system_prompt, get_system_context_snapshot
from modules.ai_tools import (
    TOOL_REGISTRY, get_tool_schemas, execute_tool, get_tool_info,
    SAFETY_LEVELS,
)
from modules.log_manager import log_system, log_operation

logger = logging.getLogger(__name__)

# 最大 Agent 迭代轮数
MAX_ITERATIONS = 10

# 待确认操作的缓存（token -> 操作详情）
# 生产环境应使用 Redis 或数据库，这里使用内存缓存 + TTL
_pending_confirmations: Dict[str, Dict] = {}
_confirmation_lock = threading.Lock()
_CONFIRMATION_TTL = 300  # 5分钟过期


def _cleanup_expired_confirmations():
    """清理过期的确认请求"""
    now = time.time()
    expired = [
        token for token, data in _pending_confirmations.items()
        if now - data.get('created_at', 0) > _CONFIRMATION_TTL
    ]
    for token in expired:
        _pending_confirmations.pop(token, None)


def create_confirmation(operator: str, tool_name: str, params: Dict,
                         messages: List[Dict], iteration: int) -> Dict:
    """
    创建待确认操作

    :return: {"confirmation_token": str, "tool": str, "params": dict, "level": str, "description": str}
    """
    _cleanup_expired_confirmations()
    token = uuid.uuid4().hex
    info = get_tool_info(tool_name)

    confirmation = {
        'token': token,
        'operator': operator,
        'tool_name': tool_name,
        'params': params,
        'messages': messages,  # 保存当前对话状态，确认后继续
        'iteration': iteration,
        'level': info['level'] if info else 'L3',
        'description': info['description'] if info else '',
        'created_at': time.time(),
    }

    with _confirmation_lock:
        _pending_confirmations[token] = confirmation

    log_system(
        f'AI Agent 创建确认请求: operator={operator}, tool={tool_name}, level={info["level"] if info else "L3"}',
        'INFO', 'ai'
    )

    return {
        'confirmation_token': token,
        'tool': tool_name,
        'params': params,
        'level': info['level'] if info else 'L3',
        'description': info['description'] if info else '',
        'safety': SAFETY_LEVELS.get(info['level'] if info else 'L3', ''),
        'expires_in': _CONFIRMATION_TTL,
    }


def get_confirmation(token: str) -> Optional[Dict]:
    """获取待确认操作详情"""
    _cleanup_expired_confirmations()
    return _pending_confirmations.get(token)


def revoke_confirmation(token: str) -> bool:
    """撤销确认请求"""
    with _confirmation_lock:
        if token in _pending_confirmations:
            _pending_confirmations.pop(token)
            return True
    return False


def execute_confirmed(token: str) -> Dict:
    """
    执行已确认的操作

    :return: {"status": "success/error", "result": dict, "messages": list}
    """
    confirmation = _pending_confirmations.get(token)
    if not confirmation:
        return {'status': 'error', 'message': '确认令牌无效或已过期'}

    tool_name = confirmation['tool_name']
    params = confirmation['params']
    operator = confirmation['operator']
    messages = confirmation['messages']
    iteration = confirmation['iteration']

    # 执行工具
    result = execute_tool(tool_name, params, operator=operator)

    # 移除确认记录
    with _confirmation_lock:
        _pending_confirmations.pop(token, None)

    log_operation(
        operator, f'ai_confirmed_{tool_name}', '',
        f'AI 确认执行工具: {tool_name}, 参数: {json.dumps(params, ensure_ascii=False)}',
    )

    return {
        'status': result.get('status', 'success'),
        'result': result,
        'tool_name': tool_name,
        'messages': messages,
        'iteration': iteration,
    }


class AgentEngine:
    """
    L3 Agent 引擎

    执行 ReAct 循环，自动处理 L1/L2 工具，L3/L4 工具暂停等待确认。
    """

    def __init__(self):
        self.llm = get_llm_client()

    def run(
        self,
        user_message: str,
        messages: List[Dict],
        operator: str = 'ai_user',
        scenario: str = 'assistant',
        max_iterations: int = MAX_ITERATIONS,
    ) -> Dict[str, Any]:
        """
        运行 Agent（同步模式）

        :param user_message: 用户消息
        :param messages: 历史消息列表（会被修改）
        :param operator: 操作者
        :param scenario: 场景
        :param max_iterations: 最大迭代次数
        :return: {
            "reply": str,           # 最终回复
            "messages": list,       # 完整对话历史
            "tool_calls": list,     # 本次执行的工具调用记录
            "pending_confirmation": dict,  # 待确认操作（如有）
            "iterations": int,      # 实际迭代次数
        }
        """
        if not self.llm.is_available():
            return {
                'reply': 'AI 服务未配置。请在「系统配置 > AI 设置」中配置 API Key 后使用。',
                'messages': messages,
                'tool_calls': [],
                'pending_confirmation': None,
                'iterations': 0,
                'error': 'not_configured',
            }

        # 构建系统提示
        context = get_system_context_snapshot()
        system_prompt = build_system_prompt(scenario, context)

        # 确保消息以 system 开头
        full_messages = self._prepare_messages(messages, system_prompt, user_message)

        # 获取工具 schema
        tools = get_tool_schemas()

        tool_call_log = []
        iterations = 0

        for iteration in range(max_iterations):
            iterations = iteration + 1

            # 调用 LLM
            result = self.llm.chat(full_messages, tools=tools, tool_choice='auto')

            if result.get('error'):
                return {
                    'reply': f'AI 请求失败: {result["error"]}',
                    'messages': full_messages,
                    'tool_calls': tool_call_log,
                    'pending_confirmation': None,
                    'iterations': iterations,
                    'error': result['error'],
                }

            content = result.get('content', '')
            tool_calls = result.get('tool_calls', [])

            # 如果没有工具调用，返回最终回复
            if not tool_calls:
                full_messages.append({'role': 'assistant', 'content': content})
                return {
                    'reply': content,
                    'messages': full_messages,
                    'tool_calls': tool_call_log,
                    'pending_confirmation': None,
                    'iterations': iterations,
                }

            # 有工具调用，先记录 assistant 消息
            assistant_msg = {'role': 'assistant', 'content': content, 'tool_calls': tool_calls}
            full_messages.append(assistant_msg)

            # 处理每个工具调用
            pending = None
            for tc in tool_calls:
                tc_id = tc.get('id', '')
                func = tc.get('function', {})
                tool_name = func.get('name', '')
                try:
                    params = json.loads(func.get('arguments', '{}'))
                except json.JSONDecodeError:
                    params = {}

                info = get_tool_info(tool_name)
                level = info['level'] if info else 'L3'

                # L3/L4 工具：创建确认请求，暂停执行
                if level in ('L3', 'L4'):
                    pending = create_confirmation(
                        operator, tool_name, params, full_messages, iterations
                    )
                    # 告知用户需要确认
                    confirm_msg = (
                        f"⚠️ 需要确认操作\n\n"
                        f"**工具**: {tool_name}\n"
                        f"**操作**: {info['description'] if info else ''}\n"
                        f"**参数**: `{json.dumps(params, ensure_ascii=False)}`\n"
                        f"**安全级别**: {level} - {SAFETY_LEVELS.get(level, '')}\n\n"
                        f"请确认是否执行此操作。"
                    )
                    full_messages.append({'role': 'assistant', 'content': confirm_msg})

                    tool_call_log.append({
                        'tool': tool_name,
                        'params': params,
                        'level': level,
                        'status': 'pending_confirmation',
                        'token': pending['confirmation_token'],
                    })

                    return {
                        'reply': confirm_msg,
                        'messages': full_messages,
                        'tool_calls': tool_call_log,
                        'pending_confirmation': pending,
                        'iterations': iterations,
                    }

                # L1/L2 工具：自动执行
                tool_result = execute_tool(tool_name, params, operator=operator)
                result_str = json.dumps(tool_result, ensure_ascii=False, default=str)

                full_messages.append({
                    'role': 'tool',
                    'tool_call_id': tc_id,
                    'name': tool_name,
                    'content': result_str,
                })

                tool_call_log.append({
                    'tool': tool_name,
                    'params': params,
                    'level': level,
                    'status': tool_result.get('status', 'unknown'),
                    'result_preview': result_str[:500],
                })

                log_system(
                    f'AI Agent 执行工具: {tool_name}({level}), status={tool_result.get("status")}',
                    'INFO', 'ai'
                )

            # 继续下一轮迭代，让 LLM 基于工具结果继续推理

        # 达到最大迭代
        full_messages.append({
            'role': 'assistant',
            'content': '已达到最大推理轮数限制。如需继续，请提供更多信息或重新提问。'
        })

        return {
            'reply': '已达到最大推理轮数限制。如需继续，请提供更多信息或重新提问。',
            'messages': full_messages,
            'tool_calls': tool_call_log,
            'pending_confirmation': None,
            'iterations': iterations,
        }

    def run_stream(
        self,
        user_message: str,
        messages: List[Dict],
        operator: str = 'ai_user',
        scenario: str = 'assistant',
        max_iterations: int = MAX_ITERATIONS,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        运行 Agent（流式模式）

        :yield: 事件流
            {"type": "content", "content": str}      - 文本内容
            {"type": "tool_start", "tool": str, ...}  - 开始执行工具
            {"type": "tool_result", "result": dict}   - 工具执行结果
            {"type": "confirmation", ...}             - 需要确认
            {"type": "done", "reply": str}            - 完成
            {"type": "error", "content": str}         - 错误
        """
        if not self.llm.is_available():
            yield {'type': 'error', 'content': 'AI 服务未配置'}
            return

        context = get_system_context_snapshot()
        system_prompt = build_system_prompt(scenario, context)
        full_messages = self._prepare_messages(messages, system_prompt, user_message)
        tools = get_tool_schemas()

        tool_call_log = []

        for iteration in range(max_iterations):
            # 流式调用 LLM
            collected_content = ''
            collected_tool_calls = []

            for chunk in self.llm.chat_stream(full_messages, tools=tools):
                if chunk['type'] == 'content':
                    collected_content += chunk['content']
                    yield {'type': 'content', 'content': chunk['content']}
                elif chunk['type'] == 'tool_call':
                    collected_tool_calls.extend(chunk['tool_calls'])
                elif chunk['type'] == 'error':
                    yield {'type': 'error', 'content': chunk['content']}
                    return
                elif chunk['type'] == 'done':
                    break

            # 无工具调用，结束
            if not collected_tool_calls:
                full_messages.append({'role': 'assistant', 'content': collected_content})
                yield {
                    'type': 'done',
                    'reply': collected_content,
                    'messages': full_messages,
                    'tool_calls': tool_call_log,
                    'iterations': iteration + 1,
                }
                return

            # 记录 assistant 消息
            full_messages.append({
                'role': 'assistant',
                'content': collected_content,
                'tool_calls': collected_tool_calls,
            })

            # 处理工具调用
            for tc in collected_tool_calls:
                tc_id = tc.get('id', '')
                func = tc.get('function', {})
                tool_name = func.get('name', '')
                try:
                    params = json.loads(func.get('arguments', '{}'))
                except json.JSONDecodeError:
                    params = {}

                info = get_tool_info(tool_name)
                level = info['level'] if info else 'L3'

                yield {'type': 'tool_start', 'tool': tool_name, 'level': level, 'params': params}

                # L3/L4 需确认
                if level in ('L3', 'L4'):
                    pending = create_confirmation(
                        operator, tool_name, params, full_messages, iteration + 1
                    )
                    tool_call_log.append({
                        'tool': tool_name, 'params': params, 'level': level,
                        'status': 'pending_confirmation', 'token': pending['confirmation_token'],
                    })
                    yield {'type': 'confirmation', **pending, 'messages': full_messages}
                    return

                # L1/L2 自动执行
                tool_result = execute_tool(tool_name, params, operator=operator)
                result_str = json.dumps(tool_result, ensure_ascii=False, default=str)

                full_messages.append({
                    'role': 'tool', 'tool_call_id': tc_id,
                    'name': tool_name, 'content': result_str,
                })

                tool_call_log.append({
                    'tool': tool_name, 'params': params, 'level': level,
                    'status': tool_result.get('status', 'unknown'),
                })

                yield {'type': 'tool_result', 'tool': tool_name, 'result': tool_result}

        yield {
            'type': 'done',
            'reply': '已达到最大推理轮数限制。',
            'messages': full_messages,
            'tool_calls': tool_call_log,
            'iterations': max_iterations,
        }

    def _prepare_messages(
        self, messages: List[Dict], system_prompt: str, user_message: str
    ) -> List[Dict]:
        """准备完整消息列表"""
        full = []

        # system 消息（替换或添加）
        if messages and messages[0].get('role') == 'system':
            full.append({'role': 'system', 'content': system_prompt})
            full.extend(messages[1:])
        else:
            full.append({'role': 'system', 'content': system_prompt})
            full.extend(messages)

        # 追加当前用户消息
        full.append({'role': 'user', 'content': user_message})

        # 限制历史长度（保留最近 20 条 + system）
        if len(full) > 22:
            full = [full[0]] + full[-21:]

        return full


# 模块级单例
_agent_engine: Optional[AgentEngine] = None
_agent_lock = threading.Lock()


def get_agent_engine() -> AgentEngine:
    """获取 Agent 引擎单例"""
    global _agent_engine
    if _agent_engine is None:
        with _agent_lock:
            if _agent_engine is None:
                _agent_engine = AgentEngine()
    return _agent_engine
