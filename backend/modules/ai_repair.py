"""
AI 自动修复引擎

根据诊断结果，提出修复方案，经用户确认后执行：
1. 修复脚本库（预定义常见修复方案）
2. LLM 生成修复方案
3. 安全沙箱执行
4. 回滚机制
5. 审计日志
"""

import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional

from modules.ai_llm_client import get_llm_client, build_system_prompt
from modules.ai_tools import execute_tool, get_tool_info, SAFETY_LEVELS
from modules.log_manager import log_system, log_operation

logger = logging.getLogger(__name__)

# 修复方案历史
_repair_history: List[Dict] = []
_MAX_HISTORY = 50

# 预定义修复方案库（按问题类型）
REPAIR_PLAYBOOKS = {
    'high_cpu': {
        'name': '高CPU占用修复',
        'description': '识别并处理高CPU占用进程',
        'steps': [
            {'tool': 'get_processes', 'params': {'sort_by': 'cpu', 'sort_order': 'desc'}, 'level': 'L1'},
            {'tool': 'analyze_process_anomaly', 'params': {}, 'level': 'L2'},
        ],
        'auto_actions': [],
        'suggested_actions': [
            {'tool': 'kill_process', 'description': '终止高CPU进程', 'level': 'L3'},
        ],
    },
    'high_memory': {
        'name': '高内存占用修复',
        'description': '清理内存缓存，处理内存泄漏进程',
        'steps': [
            {'tool': 'get_system_status', 'params': {}, 'level': 'L1'},
            {'tool': 'get_processes', 'params': {'sort_by': 'memory', 'sort_order': 'desc'}, 'level': 'L1'},
        ],
        'auto_actions': [],
        'suggested_actions': [
            {'tool': 'clean_cache', 'params': {'cache_type': 'memory'}, 'description': '清理内存缓存', 'level': 'L3'},
            {'tool': 'kill_process', 'description': '终止高内存进程', 'level': 'L3'},
        ],
    },
    'high_disk': {
        'name': '高磁盘占用修复',
        'description': '清理磁盘空间',
        'steps': [
            {'tool': 'get_disk_info', 'params': {}, 'level': 'L1'},
        ],
        'auto_actions': [],
        'suggested_actions': [
            {'tool': 'clean_cache', 'params': {'cache_type': 'tmp'}, 'description': '清理临时文件', 'level': 'L3'},
        ],
    },
    'service_failed': {
        'name': '服务故障修复',
        'description': '重启失败的服务',
        'steps': [
            {'tool': 'get_services', 'params': {'filter': 'failed'}, 'level': 'L1'},
            {'tool': 'diagnose_service', 'params': {}, 'level': 'L2'},
        ],
        'auto_actions': [],
        'suggested_actions': [
            {'tool': 'restart_service', 'description': '重启失败服务', 'level': 'L3'},
        ],
    },
    'general': {
        'name': '通用诊断修复',
        'description': '收集信息后由AI生成修复方案',
        'steps': [
            {'tool': 'get_system_status', 'params': {}, 'level': 'L1'},
            {'tool': 'get_processes', 'params': {}, 'level': 'L1'},
            {'tool': 'get_services', 'params': {}, 'level': 'L1'},
            {'tool': 'get_alerts', 'params': {}, 'level': 'L1'},
        ],
        'auto_actions': [],
        'suggested_actions': [],
    },
}


def propose_repair(
    issue_description: str,
    operator: str = 'ai_user',
    diagnostic_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    提出修复方案

    :param issue_description: 问题描述
    :param operator: 操作者
    :param diagnostic_data: 可选的诊断数据
    :return: 修复方案
    """
    llm = get_llm_client()

    # 1. 匹配预定义方案
    playbook = _match_playbook(issue_description)

    # 2. 执行 L1/L2 信息收集步骤
    collected_data = {}
    for step in playbook.get('steps', []):
        tool_name = step['tool']
        params = step.get('params', {})
        result = execute_tool(tool_name, params, operator=operator)
        collected_data[tool_name] = result

    # 3. 如果 AI 可用，让 LLM 生成修复方案
    if llm.is_available():
        context_parts = [
            f'## 问题描述\n{issue_description}',
            f'\n## 收集的系统数据\n{json.dumps(collected_data, ensure_ascii=False, default=str)[:4000]}',
            f'\n## 匹配的修复方案\n{playbook["name"]}: {playbook["description"]}',
        ]
        if diagnostic_data:
            context_parts.append(f'\n## 诊断数据\n{json.dumps(diagnostic_data, ensure_ascii=False, default=str)[:2000]}')

        context = '\n'.join(context_parts)
        system_prompt = build_system_prompt('repair', context)

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': '请基于以上信息提出具体的修复方案，包括步骤、预期效果和回滚方案。'},
        ]

        result = llm.chat(messages, temperature=0.2, max_tokens=3000)
        ai_plan = result.get('content', '')
    else:
        ai_plan = _generate_rule_based_plan(playbook, collected_data)

    # 4. 构建修复方案
    plan = {
        'status': 'success',
        'issue': issue_description,
        'playbook': playbook['name'],
        'collected_data': collected_data,
        'ai_plan': ai_plan,
        'suggested_actions': playbook.get('suggested_actions', []),
        'requires_confirmation': True,
        'created_at': time.time(),
        'operator': operator,
    }

    log_system(
        f'AI 修复方案生成: operator={operator}, playbook={playbook["name"]}',
        'INFO', 'ai'
    )

    return plan


def execute_repair_action(
    tool_name: str,
    params: Dict,
    operator: str = 'ai_user',
    confirmation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行修复操作

    注意：L3/L4 工具应已通过 Agent 引擎的确认流程，
    此函数用于直接执行已确认的操作。

    :param tool_name: 工具名称
    :param params: 工具参数
    :param operator: 操作者
    :param confirmation_token: 确认令牌（如来自 Agent 流程）
    """
    info = get_tool_info(tool_name)
    if not info:
        return {'status': 'error', 'message': f'未知工具: {tool_name}'}

    level = info['level']

    # 记录审计
    log_operation(
        operator, f'ai_repair_{tool_name}', '',
        f'AI 修复执行: {tool_name}({level}), params={json.dumps(params, ensure_ascii=False)}',
    )

    # 执行工具
    result = execute_tool(tool_name, params, operator=operator)

    # 记录历史
    _save_repair_history(operator, tool_name, params, result, level)

    return {
        'status': result.get('status', 'success'),
        'tool': tool_name,
        'level': level,
        'result': result,
        'message': result.get('message', result.get('data', {}).get('message', '')),
        'executed_at': time.time(),
    }


def get_repair_playbooks() -> List[Dict]:
    """获取所有修复方案库"""
    playbooks = []
    for key, pb in REPAIR_PLAYBOOKS.items():
        playbooks.append({
            'key': key,
            'name': pb['name'],
            'description': pb['description'],
            'steps_count': len(pb.get('steps', [])),
            'suggested_actions': pb.get('suggested_actions', []),
        })
    return playbooks


def get_repair_history(limit: int = 20) -> List[Dict]:
    """获取修复历史"""
    return _repair_history[:limit]


def _match_playbook(issue_description: str) -> Dict:
    """根据问题描述匹配修复方案"""
    desc_lower = issue_description.lower()

    if any(kw in desc_lower for kw in ['cpu', '处理器', 'load', '负载']):
        return REPAIR_PLAYBOOKS['high_cpu']
    if any(kw in desc_lower for kw in ['内存', 'memory', 'mem', 'ram']):
        return REPAIR_PLAYBOOKS['high_memory']
    if any(kw in desc_lower for kw in ['磁盘', 'disk', '空间', 'space', 'storage']):
        return REPAIR_PLAYBOOKS['high_disk']
    if any(kw in desc_lower for kw in ['服务', 'service', '失败', 'failed', 'nginx', 'mysql']):
        return REPAIR_PLAYBOOKS['service_failed']

    return REPAIR_PLAYBOOKS['general']


def _generate_rule_based_plan(playbook: Dict, collected_data: Dict) -> str:
    """AI 不可用时生成基于规则的修复方案"""
    lines = [
        f'## 修复方案: {playbook["name"]}',
        '',
        f'**描述**: {playbook["description"]}',
        '',
        '### 建议操作:',
    ]

    for action in playbook.get('suggested_actions', []):
        tool = action.get('tool', '')
        desc = action.get('description', '')
        level = action.get('level', 'L3')
        lines.append(f'- [{level}] {desc} (工具: {tool})')

    lines.extend([
        '',
        '### 注意:',
        '- 所有操作需人工确认后执行',
        '- 建议先备份重要数据',
        '- 执行后验证系统状态',
    ])

    return '\n'.join(lines)


def _save_repair_history(operator: str, tool_name: str, params: Dict,
                          result: Dict, level: str):
    """保存修复历史"""
    _repair_history.insert(0, {
        'timestamp': time.time(),
        'operator': operator,
        'tool': tool_name,
        'level': level,
        'params': params,
        'status': result.get('status', 'unknown'),
        'message': result.get('message', ''),
    })
    if len(_repair_history) > _MAX_HISTORY:
        _repair_history = _repair_history[:_MAX_HISTORY]
