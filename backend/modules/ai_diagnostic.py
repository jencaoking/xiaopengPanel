"""
AI 故障诊断引擎

主动收集系统状态，进行根因分析（RCA），生成结构化诊断报告。
工作流程：
1. 收集系统指标（CPU/内存/磁盘/网络/进程/服务）
2. 检测异常（高负载、失败服务、错误日志）
3. 关联分析，定位根因
4. 调用 LLM 生成诊断报告
5. 给出修复建议
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional

from modules.ai_llm_client import get_llm_client, build_system_prompt, get_system_context_snapshot
from modules.ai_tools import (
    tool_get_system_status, tool_get_processes, tool_get_services,
    tool_get_alerts, tool_analyze_process_anomaly, tool_correlate_metrics,
    tool_get_system_logs, tool_search_logs, _truncate, _safe_str,
)
from modules.log_manager import log_system

logger = logging.getLogger(__name__)

# 诊断历史存储（内存）
_diagnostic_history: List[Dict] = []
_MAX_HISTORY = 50


def collect_system_snapshot() -> Dict[str, Any]:
    """收集系统状态快照（用于诊断）"""
    snapshot = {
        'timestamp': time.time(),
        'system': {},
        'processes': {},
        'services': {},
        'alerts': {},
        'anomalies': {},
        'correlations': {},
    }

    try:
        snapshot['system'] = tool_get_system_status({}).get('data', {})
    except Exception as e:
        snapshot['system'] = {'error': str(e)}

    try:
        snapshot['processes'] = tool_get_processes({'sort_by': 'cpu', 'sort_order': 'desc'}).get('data', {})
    except Exception as e:
        snapshot['processes'] = {'error': str(e)}

    try:
        snapshot['services'] = tool_get_services({}).get('data', {})
    except Exception as e:
        snapshot['services'] = {'error': str(e)}

    try:
        snapshot['alerts'] = tool_get_alerts({'status': 'active'}).get('data', [])
    except Exception as e:
        snapshot['alerts'] = {'error': str(e)}

    try:
        snapshot['anomalies'] = tool_analyze_process_anomaly({}).get('data', {})
    except Exception as e:
        snapshot['anomalies'] = {'error': str(e)}

    try:
        snapshot['correlations'] = tool_correlate_metrics({}).get('data', {})
    except Exception as e:
        snapshot['correlations'] = {'error': str(e)}

    return snapshot


def detect_issues(snapshot: Dict) -> List[Dict]:
    """从快照中检测问题"""
    issues = []

    # CPU 高负载
    system = snapshot.get('system', {})
    cpu = float(system.get('cpu_usage', 0))
    if cpu > 85:
        issues.append({
            'category': 'cpu',
            'severity': 'critical' if cpu > 95 else 'warning',
            'message': f'CPU 使用率过高: {cpu}%',
            'value': cpu,
        })

    # 内存高占用
    mem = float(system.get('memory_usage', 0))
    if mem > 85:
        issues.append({
            'category': 'memory',
            'severity': 'critical' if mem > 95 else 'warning',
            'message': f'内存使用率过高: {mem}%',
            'value': mem,
        })

    # 磁盘高占用
    disk = float(system.get('disk_usage', 0))
    if disk > 85:
        issues.append({
            'category': 'disk',
            'severity': 'critical' if disk > 95 else 'warning',
            'message': f'磁盘使用率过高: {disk}%',
            'value': disk,
        })

    # 异常进程
    anomalies = snapshot.get('anomalies', {})
    for anomaly in anomalies.get('anomalies', []):
        issues.append({
            'category': 'process',
            'severity': anomaly.get('severity', 'warning'),
            'message': f"进程 {anomaly.get('name', 'unknown')} (PID:{anomaly.get('pid')}) {anomaly.get('issue')}",
            'value': anomaly,
        })

    # 失败服务
    services = snapshot.get('services', {})
    for svc in services.get('services', []):
        if svc.get('status') == 'failed':
            issues.append({
                'category': 'service',
                'severity': 'critical',
                'message': f"服务 {svc.get('name')} 状态为 failed",
                'value': svc,
            })

    # 活跃告警
    alerts = snapshot.get('alerts', [])
    if isinstance(alerts, list):
        for alert in alerts[:10]:
            issues.append({
                'category': 'alert',
                'severity': 'warning',
                'message': f"告警: {alert.get('message', 'unknown')}",
                'value': alert,
            })

    # 关联分析
    correlations = snapshot.get('correlations', {}).get('correlations', [])
    for corr in correlations:
        issues.append({
            'category': 'correlation',
            'severity': 'warning',
            'message': corr,
            'value': corr,
        })

    return issues


def diagnose(operator: str = 'ai_user', target: str = 'system') -> Dict[str, Any]:
    """
    执行故障诊断

    :param operator: 操作者
    :param target: 诊断目标 system/service_name/process_pid
    :return: 诊断报告
    """
    llm = get_llm_client()
    if not llm.is_available():
        return {
            'status': 'error',
            'message': 'AI 服务未配置，无法执行智能诊断',
            'snapshot': None,
            'issues': [],
            'report': '',
        }

    log_system(f'AI 诊断开始: operator={operator}, target={target}', 'INFO', 'ai')

    # 1. 收集系统快照
    snapshot = collect_system_snapshot()

    # 2. 检测问题
    issues = detect_issues(snapshot)

    # 如果没有问题，快速返回
    if not issues:
        report = '## 诊断报告\n\n### 系统状态\n✅ 系统运行正常，未发现异常。\n\n### 建议\n继续保持当前配置，定期监控。'
        _save_diagnostic_history(operator, target, snapshot, issues, report)
        return {
            'status': 'success',
            'message': '系统运行正常',
            'snapshot': snapshot,
            'issues': [],
            'report': report,
            'issue_count': 0,
        }

    # 3. 构建诊断上下文
    context_parts = [
        '## 系统快照',
        json.dumps(snapshot, ensure_ascii=False, default=str)[:4000],
        '',
        '## 检测到的问题',
    ]
    for i, issue in enumerate(issues, 1):
        context_parts.append(f"{i}. [{issue['severity'].upper()}] {issue['message']}")

    context = '\n'.join(context_parts)

    # 4. 调用 LLM 生成诊断报告
    system_prompt = build_system_prompt('diagnostic', context)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f'请对以下问题进行诊断分析并生成诊断报告。诊断目标: {target}'},
    ]

    result = llm.chat(messages, temperature=0.2, max_tokens=4096)

    report = result.get('content', '诊断报告生成失败')

    # 5. 保存诊断历史
    _save_diagnostic_history(operator, target, snapshot, issues, report)

    log_system(
        f'AI 诊断完成: operator={operator}, issues={len(issues)}',
        'INFO', 'ai'
    )

    return {
        'status': 'success',
        'message': f'诊断完成，发现 {len(issues)} 个问题',
        'snapshot': snapshot,
        'issues': issues,
        'report': report,
        'issue_count': len(issues),
        'critical_count': sum(1 for i in issues if i.get('severity') == 'critical'),
        'warning_count': sum(1 for i in issues if i.get('severity') == 'warning'),
    }


def diagnose_service(service_name: str, operator: str = 'ai_user') -> Dict:
    """诊断特定服务"""
    from modules.ai_tools import tool_diagnose_service

    llm = get_llm_client()
    if not llm.is_available():
        return {'status': 'error', 'message': 'AI 服务未配置'}

    # 收集服务诊断信息
    diag_data = tool_diagnose_service({'service_name': service_name})

    context = f"## 服务诊断数据\n{json.dumps(diag_data, ensure_ascii=False, default=str)[:4000]}"
    system_prompt = build_system_prompt('diagnostic', context)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f'请诊断服务 "{service_name}" 的问题并给出修复建议'},
    ]

    result = llm.chat(messages, temperature=0.2, max_tokens=3000)
    return {
        'status': 'success',
        'service': service_name,
        'diagnostic_data': diag_data,
        'report': result.get('content', ''),
    }


def get_diagnostic_history(limit: int = 20) -> List[Dict]:
    """获取诊断历史"""
    return _diagnostic_history[:limit]


def _save_diagnostic_history(operator: str, target: str, snapshot: Dict,
                              issues: List, report: str):
    """保存诊断记录"""
    _diagnostic_history.insert(0, {
        'timestamp': time.time(),
        'operator': operator,
        'target': target,
        'issue_count': len(issues),
        'critical_count': sum(1 for i in issues if i.get('severity') == 'critical'),
        'warning_count': sum(1 for i in issues if i.get('severity') == 'warning'),
        'issues': issues,
        'report': report,
        # 不保存完整 snapshot 避免内存过大
        'snapshot_summary': {
            'cpu': snapshot.get('system', {}).get('cpu_usage'),
            'memory': snapshot.get('system', {}).get('memory_usage'),
            'disk': snapshot.get('system', {}).get('disk_usage'),
        },
    })
    # 限制历史数量
    if len(_diagnostic_history) > _MAX_HISTORY:
        _diagnostic_history = _diagnostic_history[:_MAX_HISTORY]
