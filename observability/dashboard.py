"""
可视化仪表盘服务

提供 Agent 运行状态、性能指标及评测分数的可视化展示。
支持数据导出功能，可生成用于汇报的统计报告。

技术选型：
- 使用项目已有的 StreamService 进行实时数据推送
- 使用 SQLAlchemy 进行数据查询
- 支持 JSON/CSV/PDF 导出
"""

import json
import logging
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from app.models.database import Task, TaskStatus, ExecutionLog, get_db
from observability.trace_collector import TraceCollector, TraceData
from observability.evaluator import EvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Agent 运行指标"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    avg_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_score: float = 0.0
    tool_call_success_rate: float = 0.0
    active_tasks: int = 0


@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    timestamp: str
    value: float
    metric: str


class DashboardService:
    """
    仪表盘服务

    提供：
    - 实时指标查询
    - 历史趋势分析
    - 评测结果展示
    - 数据导出功能
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.trace_collector = TraceCollector()

    def get_overview_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取概览指标

        Args:
            hours: 时间范围（小时）

        Returns:
            Dict: 概览指标数据
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        if not self.db:
            return self._get_metrics_from_trace_collector(since)

        try:
            # 任务统计
            total = self.db.query(Task).filter(Task.created_at >= since).count()
            completed = self.db.query(Task).filter(
                and_(Task.created_at >= since, Task.status == TaskStatus.completed)
            ).count()
            failed = self.db.query(Task).filter(
                and_(Task.created_at >= since, Task.status == TaskStatus.failed)
            ).count()
            cancelled = self.db.query(Task).filter(
                and_(Task.created_at >= since, Task.status == TaskStatus.cancelled)
            ).count()
            running = self.db.query(Task).filter(
                and_(Task.created_at >= since, Task.status == TaskStatus.running)
            ).count()

            # 平均耗时（从 ExecutionLog 计算）
            avg_duration = self.db.query(func.avg(ExecutionLog.duration_ms)).filter(
                ExecutionLog.timestamp >= since
            ).scalar() or 0

            return {
                "period_hours": hours,
                "total_tasks": total,
                "completed_tasks": completed,
                "failed_tasks": failed,
                "cancelled_tasks": cancelled,
                "running_tasks": running,
                "success_rate": round(completed / total * 100, 2) if total > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get overview metrics: {e}")
            return self._get_metrics_from_trace_collector(since)

    def _get_metrics_from_trace_collector(self, since: datetime) -> Dict[str, Any]:
        """从 TraceCollector 获取指标（数据库不可用时）"""
        traces = [
            t for t in self.trace_collector._traces.values()
            if datetime.fromisoformat(t.start_time) >= since
        ]

        total = len(traces)
        completed = sum(1 for t in traces if t.status == "completed")
        failed = sum(1 for t in traces if t.status == "failed")

        avg_duration = sum(t.total_duration_ms for t in traces) / total if total > 0 else 0

        return {
            "period_hours": 24,
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "cancelled_tasks": 0,
            "running_tasks": sum(1 for t in traces if t.status == "running"),
            "success_rate": round(completed / total * 100, 2) if total > 0 else 0,
            "avg_duration_ms": round(avg_duration, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_task_performance(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取单个任务的性能数据"""
        traces = self.trace_collector.get_traces_by_task(task_id)
        if not traces:
            return None

        trace = traces[0]
        return {
            "task_id": task_id,
            "trace_id": trace.trace_id,
            "status": trace.status,
            "duration_ms": trace.total_duration_ms,
            "input_tokens": trace.total_input_tokens,
            "output_tokens": trace.total_output_tokens,
            "total_tokens": trace.total_input_tokens + trace.total_output_tokens,
            "cost_usd": trace.total_cost_usd,
            "tool_calls": len(trace.tool_calls),
            "tool_call_success_rate": (
                sum(1 for tc in trace.tool_calls if tc.success) / len(trace.tool_calls)
                if trace.tool_calls else 1.0
            ),
            "decisions": len(trace.decisions),
            "start_time": trace.start_time,
            "end_time": trace.end_time,
        }

    def get_evaluation_summary(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """获取评测结果汇总"""
        # 从本地缓存获取评测结果
        # 实际实现中应该从数据库查询
        return {
            "task_id": task_id,
            "evaluations_count": 0,
            "avg_overall_score": 0.0,
            "dimensions": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_time_series(
        self,
        metric: str,
        hours: int = 24,
        interval_minutes: int = 60,
    ) -> List[TimeSeriesPoint]:
        """
        获取时间序列数据

        Args:
            metric: 指标名称
            hours: 时间范围
            interval_minutes: 聚合间隔

        Returns:
            List[TimeSeriesPoint]: 时间序列数据点
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        traces = [
            t for t in self.trace_collector._traces.values()
            if datetime.fromisoformat(t.start_time) >= since
        ]

        # 按时间间隔聚合
        points = []
        current = since
        interval = timedelta(minutes=interval_minutes)

        while current <= datetime.now(timezone.utc):
            end = current + interval
            bucket_traces = [
                t for t in traces
                if current <= datetime.fromisoformat(t.start_time) < end
            ]

            if bucket_traces:
                value = self._calculate_metric(metric, bucket_traces)
                points.append(TimeSeriesPoint(
                    timestamp=current.isoformat(),
                    value=value,
                    metric=metric,
                ))

            current = end

        return points

    def _calculate_metric(self, metric: str, traces: List[TraceData]) -> float:
        """计算聚合指标"""
        if not traces:
            return 0.0

        if metric == "task_count":
            return len(traces)
        elif metric == "avg_duration_ms":
            return sum(t.total_duration_ms for t in traces) / len(traces)
        elif metric == "total_tokens":
            return sum(t.total_input_tokens + t.total_output_tokens for t in traces)
        elif metric == "total_cost_usd":
            return sum(t.total_cost_usd for t in traces)
        elif metric == "success_rate":
            completed = sum(1 for t in traces if t.status == "completed")
            return completed / len(traces) * 100
        elif metric == "tool_call_count":
            return sum(len(t.tool_calls) for t in traces)
        elif metric == "avg_tool_duration_ms":
            all_durations = [
                tc.duration_ms for t in traces for tc in t.tool_calls
            ]
            return sum(all_durations) / len(all_durations) if all_durations else 0

        return 0.0

    def export_to_json(
        self,
        task_id: Optional[str] = None,
        hours: int = 24,
    ) -> str:
        """导出数据为 JSON"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        traces = [
            t for t in self.trace_collector._traces.values()
            if datetime.fromisoformat(t.start_time) >= since
        ]

        if task_id:
            traces = [t for t in traces if t.task_id == task_id]

        data = {
            "export_time": datetime.now(timezone.utc).isoformat(),
            "period_hours": hours,
            "task_id": task_id,
            "trace_count": len(traces),
            "traces": [t.to_dict() for t in traces],
            "summary": self.get_overview_metrics(hours),
        }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def export_to_csv(
        self,
        task_id: Optional[str] = None,
        hours: int = 24,
    ) -> str:
        """导出数据为 CSV"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        traces = [
            t for t in self.trace_collector._traces.values()
            if datetime.fromisoformat(t.start_time) >= since
        ]

        if task_id:
            traces = [t for t in traces if t.task_id == task_id]

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow([
            "trace_id", "task_id", "name", "agent_type", "status",
            "start_time", "end_time", "duration_ms",
            "input_tokens", "output_tokens", "total_tokens", "cost_usd",
            "tool_calls", "decisions",
        ])

        # 写入数据
        for trace in traces:
            writer.writerow([
                trace.trace_id,
                trace.task_id or "",
                trace.name,
                trace.agent_type,
                trace.status,
                trace.start_time,
                trace.end_time or "",
                trace.total_duration_ms,
                trace.total_input_tokens,
                trace.total_output_tokens,
                trace.total_input_tokens + trace.total_output_tokens,
                trace.total_cost_usd,
                len(trace.tool_calls),
                len(trace.decisions),
            ])

        return output.getvalue()

    def generate_report(
        self,
        hours: int = 24,
        format: str = "markdown",
    ) -> str:
        """
        生成统计报告

        Args:
            hours: 时间范围
            format: 输出格式 (markdown, html)

        Returns:
            str: 报告内容
        """
        metrics = self.get_overview_metrics(hours)

        if format == "markdown":
            return self._generate_markdown_report(metrics, hours)
        elif format == "html":
            return self._generate_html_report(metrics, hours)
        else:
            return self._generate_markdown_report(metrics, hours)

    def _generate_markdown_report(self, metrics: Dict[str, Any], hours: int) -> str:
        """生成 Markdown 报告"""
        lines = [
            f"# Agent 系统运行报告",
            f"",
            f"**生成时间**: {datetime.now(timezone.utc).isoformat()}",
            f"**统计周期**: 过去 {hours} 小时",
            f"",
            f"## 任务概览",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总任务数 | {metrics['total_tasks']} |",
            f"| 已完成 | {metrics['completed_tasks']} |",
            f"| 失败 | {metrics['failed_tasks']} |",
            f"| 已取消 | {metrics['cancelled_tasks']} |",
            f"| 运行中 | {metrics['running_tasks']} |",
            f"| 成功率 | {metrics['success_rate']}% |",
            f"| 平均耗时 | {metrics['avg_duration_ms']:.2f} ms |",
            f"",
            f"## 性能指标",
            f"",
            f"- 总 Token 消耗: {metrics.get('total_tokens', 'N/A')}",
            f"- 总成本: ${metrics.get('total_cost_usd', 'N/A')}",
            f"- 工具调用成功率: {metrics.get('tool_call_success_rate', 'N/A')}%",
            f"",
            f"---",
            f"*报告由 MultiAgentDeepResearch 可观测性系统自动生成*",
        ]

        return "\n".join(lines)

    def _generate_html_report(self, metrics: Dict[str, Any], hours: int) -> str:
        """生成 HTML 报告"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Agent 系统运行报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
    </style>
</head>
<body>
    <h1>Agent 系统运行报告</h1>
    <p><strong>生成时间:</strong> {datetime.now(timezone.utc).isoformat()}</p>
    <p><strong>统计周期:</strong> 过去 {hours} 小时</p>

    <h2>任务概览</h2>
    <table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>总任务数</td><td>{metrics['total_tasks']}</td></tr>
        <tr><td>已完成</td><td>{metrics['completed_tasks']}</td></tr>
        <tr><td>失败</td><td>{metrics['failed_tasks']}</td></tr>
        <tr><td>已取消</td><td>{metrics['cancelled_tasks']}</td></tr>
        <tr><td>运行中</td><td>{metrics['running_tasks']}</td></tr>
        <tr><td>成功率</td><td>{metrics['success_rate']}%</td></tr>
        <tr><td>平均耗时</td><td>{metrics['avg_duration_ms']:.2f} ms</td></tr>
    </table>

    <p><em>报告由 MultiAgentDeepResearch 可观测性系统自动生成</em></p>
</body>
</html>
        """.strip()

    def get_realtime_stats(self) -> Dict[str, Any]:
        """获取实时统计"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_traces": len([t for t in self.trace_collector._traces.values() if t.status == "running"]),
            "total_traces_in_memory": len(self.trace_collector._traces),
            "buffer_size": len(self.trace_collector._local_buffer),
        }