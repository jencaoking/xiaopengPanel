"""
AI API 路由蓝图

提供 AI 助手、故障诊断、智能告警、自动修复的 REST API。
所有路由复用现有的 @authenticate + @ip_whitelist_required + @require_permission 装饰器。
"""

import json
import time
from flask import Blueprint, jsonify, request, Response, stream_with_context

from modules.auth import authenticate
from modules.middleware import ip_whitelist_required, require_permission
from modules.log_manager import log_operation, log_system

# 创建 AI 蓝图
ai_api = Blueprint('ai_api', __name__)


# ==================== AI 健康检查 ====================

@ai_api.route('/ai/health', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def ai_health_route():
    """AI 服务健康检查"""
    from modules.ai_llm_client import get_llm_client
    client = get_llm_client()
    info = client.get_provider_info()

    return jsonify({
        'status': 'ok' if info['available'] else 'not_configured',
        'available': info['available'],
        'provider': info['provider'],
        'model': info['model'],
        'timestamp': time.time(),
    })


# ==================== AI 配置管理 ====================

@ai_api.route('/ai/config', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:manage')
def get_ai_config_route():
    """获取 AI 配置"""
    from config.config import config_instance
    cfg = config_instance.get_config().get('ai', {})
    # 脱敏：不返回完整 API Key
    safe_cfg = dict(cfg)
    if safe_cfg.get('api_key'):
        safe_cfg['api_key'] = safe_cfg['api_key'][:8] + '****' if len(safe_cfg['api_key']) > 8 else '****'
        safe_cfg['api_key_configured'] = True
    else:
        safe_cfg['api_key_configured'] = False
    return jsonify({'status': 'success', 'config': safe_cfg})


@ai_api.route('/ai/config', methods=['PUT'])
@authenticate
@ip_whitelist_required
@require_permission('ai:manage')
def update_ai_config_route():
    """更新 AI 配置"""
    from config.config import config_instance
    data = request.json or {}

    # 构建 AI 配置更新
    ai_config = {}
    for key in ['enabled', 'provider', 'model', 'base_url', 'temperature',
                'max_tokens', 'max_iterations', 'auto_repair_enabled',
                'confirmation_required']:
        if key in data:
            ai_config[key] = data[key]

    # API Key 特殊处理（非空才更新）
    if 'api_key' in data and data['api_key']:
        ai_config['api_key'] = data['api_key']

    if ai_config:
        config_instance.update_config({'ai': ai_config})
        log_operation(
            request.user['username'], 'update_ai_config', request.remote_addr,
            f'更新 AI 配置: {", ".join(ai_config.keys())}'
        )

    return jsonify({'status': 'success', 'message': 'AI 配置已更新'})


# ==================== 对话助手 ====================

@ai_api.route('/ai/sessions', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def list_sessions_route():
    """获取会话列表"""
    from modules.ai_assistant import list_sessions
    operator = request.user.get('username')
    sessions = list_sessions(operator=operator)
    return jsonify({'status': 'success', 'sessions': sessions})


@ai_api.route('/ai/sessions', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def create_session_route():
    """创建新会话"""
    from modules.ai_assistant import create_session
    data = request.json or {}
    operator = request.user.get('username')
    result = create_session(operator, title=data.get('title', '新对话'))
    return jsonify({'status': 'success', **result})


@ai_api.route('/ai/sessions/<session_id>', methods=['DELETE'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def delete_session_route(session_id):
    """删除会话"""
    from modules.ai_assistant import delete_session
    if delete_session(session_id):
        return jsonify({'status': 'success', 'message': '会话已删除'})
    return jsonify({'status': 'error', 'message': '会话不存在'}), 404


@ai_api.route('/ai/chat', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def ai_chat_route():
    """AI 对话（同步模式）"""
    from modules.ai_assistant import chat
    data = request.json or {}
    session_id = data.get('session_id', '')
    message = data.get('message', '')

    if not message:
        return jsonify({'status': 'error', 'message': '消息不能为空'}), 400

    operator = request.user.get('username')

    try:
        result = chat(session_id, message, operator=operator)
        return jsonify({'status': 'success', **result})
    except Exception as e:
        log_system(f'AI 对话异常: {e}', 'ERROR', 'ai')
        return jsonify({'status': 'error', 'message': f'对话失败: {e}'}), 500


@ai_api.route('/ai/chat/stream', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def ai_chat_stream_route():
    """AI 对话（流式 SSE 模式）"""
    from modules.ai_assistant import chat_stream

    data = request.json or {}
    session_id = data.get('session_id', '')
    message = data.get('message', '')

    if not message:
        return jsonify({'status': 'error', 'message': '消息不能为空'}), 400

    operator = request.user.get('username')

    def event_stream():
        try:
            for event in chat_stream(session_id, message, operator=operator):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


@ai_api.route('/ai/confirm', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:execute')
def ai_confirm_route():
    """确认执行 AI 提出的操作"""
    from modules.ai_assistant import continue_after_confirmation

    data = request.json or {}
    token = data.get('confirmation_token', '')
    action = data.get('action', '')  # confirm / cancel

    if not token:
        return jsonify({'status': 'error', 'message': '缺少确认令牌'}), 400

    operator = request.user.get('username')

    if action == 'cancel':
        from modules.ai_agent import revoke_confirmation
        if revoke_confirmation(token):
            log_operation(operator, 'ai_cancel_action', request.remote_addr, '取消 AI 操作')
            return jsonify({'status': 'success', 'message': '操作已取消'})
        return jsonify({'status': 'error', 'message': '令牌无效或已过期'}), 404

    # 确认执行
    try:
        result = continue_after_confirmation(token, operator=operator)
        log_operation(operator, 'ai_confirm_action', request.remote_addr, '确认执行 AI 操作')
        return jsonify({'status': 'success', **result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'执行失败: {e}'}), 500


# ==================== 故障诊断 ====================

@ai_api.route('/ai/diagnose', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def ai_diagnose_route():
    """故障诊断"""
    from modules.ai_diagnostic import diagnose
    data = request.json or {}
    target = data.get('target', 'system')
    operator = request.user.get('username')

    try:
        result = diagnose(operator=operator, target=target)
        log_operation(operator, 'ai_diagnose', request.remote_addr, f'AI 诊断: {target}')
        return jsonify(result)
    except Exception as e:
        log_system(f'AI 诊断异常: {e}', 'ERROR', 'ai')
        return jsonify({'status': 'error', 'message': f'诊断失败: {e}'}), 500


@ai_api.route('/ai/diagnose/service/<service_name>', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def ai_diagnose_service_route(service_name):
    """诊断特定服务"""
    from modules.ai_diagnostic import diagnose_service
    operator = request.user.get('username')

    try:
        result = diagnose_service(service_name, operator=operator)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'服务诊断失败: {e}'}), 500


@ai_api.route('/ai/diagnostics/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def diagnostic_history_route():
    """诊断历史"""
    from modules.ai_diagnostic import get_diagnostic_history
    limit = int(request.args.get('limit', 20))
    history = get_diagnostic_history(limit=limit)
    return jsonify({'status': 'success', 'history': history})


# ==================== 智能告警 ====================

@ai_api.route('/ai/alerts/smart', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def smart_alerts_route():
    """智能告警仪表盘"""
    from modules.ai_alert import get_smart_alert_dashboard
    try:
        result = get_smart_alert_dashboard()
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'获取智能告警失败: {e}'}), 500


@ai_api.route('/ai/alerts/analyze', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def analyze_alert_route():
    """分析单条告警"""
    from modules.ai_alert import analyze_alert
    data = request.json or {}
    alert = data.get('alert', {})
    if not alert:
        return jsonify({'status': 'error', 'message': '缺少告警数据'}), 400

    try:
        result = analyze_alert(alert)
        return jsonify({'status': 'success', 'analysis': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'分析失败: {e}'}), 500


# ==================== 自动修复 ====================

@ai_api.route('/ai/repair/propose', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def repair_propose_route():
    """提出修复方案"""
    from modules.ai_repair import propose_repair
    data = request.json or {}
    issue = data.get('issue', '')
    diagnostic_data = data.get('diagnostic_data')
    operator = request.user.get('username')

    if not issue:
        return jsonify({'status': 'error', 'message': '缺少问题描述'}), 400

    try:
        result = propose_repair(issue, operator=operator, diagnostic_data=diagnostic_data)
        log_operation(operator, 'ai_repair_propose', request.remote_addr, f'AI 修复方案: {issue[:100]}')
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'生成修复方案失败: {e}'}), 500


@ai_api.route('/ai/repair/execute', methods=['POST'])
@authenticate
@ip_whitelist_required
@require_permission('ai:execute')
def repair_execute_route():
    """执行修复操作（L3/L4 需确认）"""
    from modules.ai_repair import execute_repair_action
    data = request.json or {}
    tool_name = data.get('tool', '')
    params = data.get('params', {})
    operator = request.user.get('username')

    if not tool_name:
        return jsonify({'status': 'error', 'message': '缺少工具名称'}), 400

    try:
        result = execute_repair_action(tool_name, params, operator=operator)
        log_operation(
            operator, 'ai_repair_execute', request.remote_addr,
            f'AI 修复执行: {tool_name}'
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'执行失败: {e}'}), 500


@ai_api.route('/ai/repair/playbooks', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def repair_playbooks_route():
    """获取修复方案库"""
    from modules.ai_repair import get_repair_playbooks
    return jsonify({'status': 'success', 'playbooks': get_repair_playbooks()})


@ai_api.route('/ai/repair/history', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def repair_history_route():
    """修复历史"""
    from modules.ai_repair import get_repair_history
    limit = int(request.args.get('limit', 20))
    return jsonify({'status': 'success', 'history': get_repair_history(limit=limit)})


# ==================== 工具列表 ====================

@ai_api.route('/ai/tools', methods=['GET'])
@authenticate
@ip_whitelist_required
@require_permission('ai:view')
def ai_tools_route():
    """获取可用工具列表"""
    from modules.ai_tools import list_all_tools, SAFETY_LEVELS
    return jsonify({
        'status': 'success',
        'tools': list_all_tools(),
        'safety_levels': SAFETY_LEVELS,
    })
