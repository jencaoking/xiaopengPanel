"""
AI 对话助手

多轮对话管理，集成 Agent 引擎实现：
- 会话存储（内存，按 session_id）
- 同步/流式对话
- 上下文管理（保留最近 N 轮）
- 会话列表/删除/清空
"""

import time
import uuid
import logging
import threading
from typing import Dict, List, Any, Optional, Generator

from modules.ai_agent import get_agent_engine
from modules.ai_llm_client import get_llm_client
from modules.log_manager import log_system

logger = logging.getLogger(__name__)

# 最大会话数（防止内存溢出）
MAX_SESSIONS = 100
# 每个会话最大消息数
MAX_MESSAGES_PER_SESSION = 50

# 会话存储
_sessions: Dict[str, Dict] = {}
_sessions_lock = threading.Lock()


def _cleanup_old_sessions():
    """清理过期会话（超过最大数量时删除最旧的）"""
    if len(_sessions) <= MAX_SESSIONS:
        return
    # 按 last_active 排序，删除最旧的
    sorted_ids = sorted(
        _sessions.keys(),
        key=lambda sid: _sessions[sid].get('last_active', 0)
    )
    while len(_sessions) > MAX_SESSIONS and sorted_ids:
        _sessions.pop(sorted_ids.pop(0), None)


def create_session(operator: str, title: str = '新对话') -> Dict:
    """
    创建新会话

    :return: {"session_id": str, "title": str, "created_at": float}
    """
    session_id = uuid.uuid4().hex[:16]
    now = time.time()

    session = {
        'session_id': session_id,
        'operator': operator,
        'title': title,
        'messages': [],  # 对话历史（不含 system prompt）
        'created_at': now,
        'last_active': now,
        'message_count': 0,
    }

    with _sessions_lock:
        _sessions[session_id] = session
        _cleanup_old_sessions()

    log_system(f'AI 会话创建: {session_id} by {operator}', 'INFO', 'ai')
    return {
        'session_id': session_id,
        'title': title,
        'created_at': now,
    }


def get_session(session_id: str) -> Optional[Dict]:
    """获取会话"""
    return _sessions.get(session_id)


def list_sessions(operator: Optional[str] = None) -> List[Dict]:
    """
    列出会话

    :param operator: 按操作者过滤（None 表示全部）
    """
    sessions = []
    for sid, s in _sessions.items():
        if operator and s.get('operator') != operator:
            continue
        sessions.append({
            'session_id': sid,
            'title': s.get('title', '新对话'),
            'operator': s.get('operator'),
            'created_at': s.get('created_at'),
            'last_active': s.get('last_active'),
            'message_count': s.get('message_count', 0),
        })
    # 按最后活跃时间倒序
    sessions.sort(key=lambda x: x.get('last_active', 0), reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """删除会话"""
    with _sessions_lock:
        if session_id in _sessions:
            _sessions.pop(session_id)
            return True
    return False


def clear_sessions(operator: Optional[str] = None) -> int:
    """清空会话"""
    count = 0
    with _sessions_lock:
        if operator:
            # 只清空指定用户的
            to_delete = [sid for sid, s in _sessions.items() if s.get('operator') == operator]
            for sid in to_delete:
                _sessions.pop(sid)
                count += 1
        else:
            count = len(_sessions)
            _sessions.clear()
    return count


def _update_session(session_id: str, messages: List[Dict], title: Optional[str] = None):
    """更新会话消息"""
    with _sessions_lock:
        if session_id not in _sessions:
            return
        session = _sessions[session_id]
        # 限制消息数量
        if len(messages) > MAX_MESSAGES_PER_SESSION:
            messages = messages[-MAX_MESSAGES_PER_SESSION:]
        session['messages'] = messages
        session['last_active'] = time.time()
        session['message_count'] = len(messages)
        if title:
            session['title'] = title


def chat(
    session_id: str,
    user_message: str,
    operator: str = 'ai_user',
) -> Dict[str, Any]:
    """
    同步对话

    :return: {
        "reply": str,
        "session_id": str,
        "tool_calls": list,
        "pending_confirmation": dict,
        "messages": list,  # 更新后的消息历史
    }
    """
    # 获取或创建会话
    session = _sessions.get(session_id)
    if not session:
        create_result = create_session(operator)
        session_id = create_result['session_id']
        session = _sessions.get(session_id)

    history = session.get('messages', [])

    # 自动生成标题（首次对话）
    title = session.get('title', '新对话')
    if title == '新对话' and user_message:
        title = user_message[:30] + ('...' if len(user_message) > 30 else '')

    # 调用 Agent 引擎
    engine = get_agent_engine()
    result = engine.run(
        user_message=user_message,
        messages=history,
        operator=operator,
        scenario='assistant',
    )

    # 更新会话
    updated_messages = result.get('messages', [])
    # 移除 system 消息后存储（system 由 agent 动态构建）
    stored_messages = [m for m in updated_messages if m.get('role') != 'system']
    _update_session(session_id, stored_messages, title)

    return {
        'reply': result.get('reply', ''),
        'session_id': session_id,
        'tool_calls': result.get('tool_calls', []),
        'pending_confirmation': result.get('pending_confirmation'),
        'iterations': result.get('iterations', 0),
        'error': result.get('error'),
    }


def chat_stream(
    session_id: str,
    user_message: str,
    operator: str = 'ai_user',
) -> Generator[Dict[str, Any], None, None]:
    """
    流式对话

    :yield: 事件流
        {"type": "content", "content": str}
        {"type": "tool_start", ...}
        {"type": "tool_result", ...}
        {"type": "confirmation", ...}
        {"type": "done", "reply": str, "session_id": str}
        {"type": "error", "content": str}
    """
    session = _sessions.get(session_id)
    if not session:
        create_result = create_session(operator)
        session_id = create_result['session_id']
        session = _sessions.get(session_id)

    history = session.get('messages', [])
    title = session.get('title', '新对话')
    if title == '新对话' and user_message:
        title = user_message[:30] + ('...' if len(user_message) > 30 else '')

    engine = get_agent_engine()

    final_messages = []
    final_reply = ''

    for event in engine.run_stream(
        user_message=user_message,
        messages=history,
        operator=operator,
        scenario='assistant',
    ):
        if event['type'] == 'done':
            final_messages = event.get('messages', [])
            final_reply = event.get('reply', '')
        yield event

    # 更新会话
    if final_messages:
        stored_messages = [m for m in final_messages if m.get('role') != 'system']
        _update_session(session_id, stored_messages, title)

    yield {'type': 'session_update', 'session_id': session_id, 'title': title}


def continue_after_confirmation(token: str, operator: str = 'ai_user') -> Dict:
    """
    确认操作后继续 Agent 循环

    :param token: 确认令牌
    :return: 继续执行的结果
    """
    from modules.ai_agent import execute_confirmed, get_agent_engine

    confirmed = execute_confirmed(token)
    if confirmed.get('status') != 'success':
        return confirmed

    messages = confirmed.get('messages', [])
    tool_name = confirmed.get('tool_name', '')
    result = confirmed.get('result', {})

    # 将工具执行结果加入消息
    messages.append({
        'role': 'tool',
        'tool_call_id': f'confirmed_{token[:8]}',
        'name': tool_name,
        'content': json.dumps(result, ensure_ascii=False, default=str),
    })

    # 继续运行 Agent
    engine = get_agent_engine()

    # 构造一个空的用户消息让 Agent 继续
    # 实际上 Agent 会基于 tool 结果继续推理
    # 这里我们直接调用 LLM 继续推理
    from modules.ai_llm_client import get_llm_client, build_system_prompt, get_system_context_snapshot
    from modules.ai_tools import get_tool_schemas

    llm = get_llm_client()
    context = get_system_context_snapshot()
    system_prompt = build_system_prompt('assistant', context)

    # 确保 system 消息在前
    if not messages or messages[0].get('role') != 'system':
        messages = [{'role': 'system', 'content': system_prompt}] + messages
    else:
        messages[0] = {'role': 'system', 'content': system_prompt}

    tools = get_tool_schemas()
    llm_result = llm.chat(messages, tools=tools, tool_choice='auto')

    reply = llm_result.get('content', '')
    if reply:
        messages.append({'role': 'assistant', 'content': reply})

    return {
        'status': 'success',
        'reply': reply or '操作已完成。',
        'messages': messages,
        'tool_result': result,
        'tool_name': tool_name,
    }


# 导入 json（continue_after_confirmation 中使用）
import json
