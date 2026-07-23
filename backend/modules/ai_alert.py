"""
AI 智能告警

基于 LLM 对告警进行智能分级与分析：
- 告警分级（critical/warning/info）
- 原因分析
- 处理建议
- 批量分析活跃告警
- 智能去重与聚合
"""

import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional

from modules.ai_llm_client import get_llm_client, build_system_prompt
from modules.log_manager import log_system

logger = logging.getLogger(__name__)

# 告警分析结果缓存（alert_id -> 分析结果）
_alert_analysis_cache: Dict[int, Dict] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 3600  # 1小时


def _cleanup_cache():
    """清理过期缓存"""
    now = time.time()
    expired = [
        aid for aid, data in _alert_analysis_cache.items()
        if now - data.get('analyzed_at', 0) > _CACHE_TTL
    ]
    for aid in expired:
        _alert_analysis_cache.pop(aid, None)


def analyze_alert(alert: Dict) -> Dict[str, Any]:
    """
    分析单条告警

    :param alert: 告警数据
    :return: {
        "severity": "critical|warning|info",
        "analysis": "原因分析",
        "suggestion": "处理建议",
        "confidence": 0-1,
    }
    """
    llm = get_llm_client()
    if not llm.is_available():
        # AI 不可用时，使用规则降级
        return _rule_based_analysis(alert)

    alert_id = alert.get('id')
    if alert_id:
        with _cache_lock:
            _cleanup_cache()
            if alert_id in _alert_analysis_cache:
                return _alert_analysis_cache[alert_id]

    # 构建告警上下文
    alert_context = json.dumps(alert, ensure_ascii=False, default=str)

    system_prompt = build_system_prompt('alert')
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f'请分析以下告警:\n{alert_context}'},
    ]

    result = llm.chat(messages, temperature=0.1, max_tokens=1000)
    content = result.get('content', '')

    # 尝试解析 JSON
    analysis = _parse_alert_response(content, alert)

    # 缓存结果
    if alert_id:
        with _cache_lock:
            _alert_analysis_cache[alert_id] = analysis

    return analysis


def analyze_active_alerts(limit: int = 20) -> Dict[str, Any]:
    """
    批量分析活跃告警

    :return: {
        "status": "success",
        "total": int,
        "analyzed": int,
        "summary": {"critical": int, "warning": int, "info": int},
        "alerts": list,
    }
    """
    from modules.system_monitor import metrics_collector

    # 获取活跃告警
    result = metrics_collector.get_alerts(status='active', limit=limit)
    alerts = result.get('alerts', [])

    if not alerts:
        return {
            'status': 'success',
            'total': 0,
            'analyzed': 0,
            'summary': {'critical': 0, 'warning': 0, 'info': 0},
            'alerts': [],
            'message': '当前无活跃告警',
        }

    analyzed_alerts = []
    summary = {'critical': 0, 'warning': 0, 'info': 0}

    for alert in alerts:
        analysis = analyze_alert(alert)
        severity = analysis.get('severity', 'info')
        summary[severity] = summary.get(severity, 0) + 1

        analyzed_alerts.append({
            'alert': alert,
            'analysis': analysis,
        })

    return {
        'status': 'success',
        'total': len(alerts),
        'analyzed': len(analyzed_alerts),
        'summary': summary,
        'alerts': analyzed_alerts,
    }


def get_smart_alert_dashboard() -> Dict[str, Any]:
    """
    获取智能告警仪表盘

    汇总告警状态 + AI 分析结果
    """
    from modules.system_monitor import metrics_collector

    # 活跃告警
    active_result = metrics_collector.get_alerts(status='active', limit=50)
    active_alerts = active_result.get('alerts', [])

    # 最近告警（含已解决）
    recent_result = metrics_collector.get_alerts(status=None, limit=20)
    recent_alerts = recent_result.get('alerts', [])

    # 批量分析活跃告警
    ai_analysis = analyze_active_alerts(limit=20) if active_alerts else {
        'summary': {'critical': 0, 'warning': 0, 'info': 0},
        'alerts': [],
    }

    return {
        'status': 'success',
        'active_count': len(active_alerts),
        'recent_count': len(recent_alerts),
        'ai_summary': ai_analysis.get('summary', {}),
        'active_alerts': ai_analysis.get('alerts', []),
        'recent_alerts': recent_alerts[:10],
    }


def _parse_alert_response(content: str, alert: Dict) -> Dict:
    """解析 LLM 告警分析响应"""
    # 尝试提取 JSON
    try:
        # 查找 JSON 块
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            data = json.loads(json_str)
            return {
                'severity': data.get('severity', 'info'),
                'analysis': data.get('analysis', ''),
                'suggestion': data.get('suggestion', ''),
                'confidence': float(data.get('confidence', 0.5)),
                'analyzed_at': time.time(),
            }
    except (json.JSONDecodeError, ValueError):
        pass

    # 解析失败，使用规则降级
    return _rule_based_analysis(alert, fallback_text=content)


def _rule_based_analysis(alert: Dict, fallback_text: str = '') -> Dict:
    """基于规则的告警分析（AI 不可用时的降级方案）"""
    metric = alert.get('metric_name', '')
    current = float(alert.get('current_value', 0))
    threshold = float(alert.get('threshold_value', 0))
    alert_type = alert.get('alert_type', 'gt')

    severity = 'warning'
    analysis = f'指标 {metric} 当前值 {current} 超过阈值 {threshold}'
    suggestion = '请检查相关服务状态'
    confidence = 0.6

    # 根据指标和严重程度分级
    if current > threshold * 1.5:
        severity = 'critical'
        confidence = 0.8

    if metric in ('cpu', 'memory') and current > 95:
        severity = 'critical'
        analysis = f'{metric.upper()} 使用率严重过高 ({current}%)，可能影响系统稳定性'
        suggestion = f'1. 检查高占用进程\n2. 考虑重启相关服务\n3. 评估是否需要扩容'
    elif metric == 'disk' and current > 90:
        severity = 'critical'
        analysis = f'磁盘使用率过高 ({current}%)，可能导致服务异常'
        suggestion = '1. 清理大文件和日志\n2. 检查临时文件\n3. 考虑扩容磁盘'
    elif metric == 'disk_response_time':
        severity = 'warning'
        analysis = f'磁盘响应时间过长 ({current}ms)'
        suggestion = '1. 检查磁盘 I/O\n2. 排查 IO 密集进程'
    elif 'network' in metric:
        severity = 'warning'
        analysis = f'网络指标异常: {metric} = {current}'
        suggestion = '检查网络连接和带宽使用'

    return {
        'severity': severity,
        'analysis': analysis,
        'suggestion': suggestion,
        'confidence': confidence,
        'analyzed_at': time.time(),
        'rule_based': True,
        'ai_fallback': fallback_text[:200] if fallback_text else '',
    }
