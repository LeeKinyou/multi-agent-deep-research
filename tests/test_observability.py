"""
可观测性模块测试

测试覆盖：
1. TraceCollector 基础功能
2. LLMJudgeEvaluator 评测逻辑
3. AlertService 告警规则
4. DashboardService 数据导出
"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from observability.trace_collector import (
    TraceCollector, ToolCallRecord, TokenUsageRecord,
    PromptRecord, DecisionRecord, TraceData,
    trace_span, trace_tool_call,
)
from observability.evaluator import (
    LLMJudgeEvaluator, EvaluationResult, DimensionScore,
    EvaluationDimension,
)
from observability.alert_service import (
    AlertService, AlertRule, AlertLevel, AlertChannel, AlertEvent,
)
from observability.dashboard import DashboardService


class TestTraceCollector:
    """Trace 采集器测试"""

    def setup_method(self):
        self.collector = TraceCollector()
        self.collector._traces.clear()

    def test_start_trace(self):
        trace_id = self.collector.start_trace(
            name="test_trace",
            task_id="task_001",
            agent_type="TestAgent",
        )
        assert trace_id is not None
        assert len(trace_id) > 0
        assert trace_id in self.collector._traces

    def test_end_trace(self):
        trace_id = self.collector.start_trace("test_trace")
        result = self.collector.end_trace(trace_id, status="completed")

        assert result is not None
        assert result.status == "completed"
        assert result.end_time is not None

    def test_record_tool_call(self):
        trace_id = self.collector.start_trace("test_trace")
        record = self.collector.record_tool_call(
            tool_name="test_tool",
            input_params={"query": "test"},
            output_result="result",
        )

        assert record.tool_name == "test_tool"
        assert record.success is True
        assert len(self.collector._traces[trace_id].tool_calls) == 1

    def test_record_token_usage(self):
        trace_id = self.collector.start_trace("test_trace")
        record = self.collector.record_token_usage(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
        )

        assert record.model == "gpt-4"
        assert record.total_tokens == 1500
        assert len(self.collector._traces[trace_id].token_usage) == 1

    def test_record_prompt(self):
        trace_id = self.collector.start_trace("test_trace")
        record = self.collector.record_prompt(
            prompt_text="Test prompt",
            role="system",
            version=1,
        )

        assert record.prompt_text == "Test prompt"
        assert record.version == 1
        assert len(self.collector._traces[trace_id].prompts) == 1

    def test_record_decision(self):
        trace_id = self.collector.start_trace("test_trace")
        record = self.collector.record_decision(
            decision_type="test_decision",
            context={"key": "value"},
            options=["a", "b"],
            selected_option="a",
            confidence=0.9,
        )

        assert record.decision_type == "test_decision"
        assert record.selected_option == "a"
        assert len(self.collector._traces[trace_id].decisions) == 1

    def test_get_traces_by_task(self):
        trace_id = self.collector.start_trace("test", task_id="task_001")
        self.collector.end_trace(trace_id)

        traces = self.collector.get_traces_by_task("task_001")
        assert len(traces) == 1
        assert traces[0].task_id == "task_001"

    def test_get_traces_by_time_range(self):
        trace_id = self.collector.start_trace("test")
        self.collector.end_trace(trace_id)

        now = datetime.now(timezone.utc)
        traces = self.collector.get_traces_by_time_range(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        assert len(traces) >= 1

    def test_trace_to_dict(self):
        trace_id = self.collector.start_trace("test")
        self.collector.record_tool_call("tool", {})
        self.collector.end_trace(trace_id)

        trace = self.collector._traces[trace_id]
        data = trace.to_dict()

        assert "trace_id" in data
        assert "tool_calls" in data
        assert "token_usage" in data


class TestLLMJudgeEvaluator:
    """LLM 评测器测试"""

    def setup_method(self):
        self.evaluator = LLMJudgeEvaluator()

    def test_evaluate_structure(self):
        """测试评测结果结构"""
        result = self.evaluator.evaluate(
            report_content="这是一个测试报告。",
            source_data="这是原始数据。",
            task_id="task_001",
        )

        assert isinstance(result, EvaluationResult)
        assert result.evaluation_id is not None
        assert result.task_id == "task_001"
        assert 0 <= result.overall_score <= 10
        assert len(result.dimensions) > 0

    def test_dimension_scores(self):
        """测试各维度评分"""
        result = self.evaluator.evaluate(
            report_content="测试报告内容。",
            task_id="task_002",
        )

        for dim in result.dimensions:
            assert isinstance(dim, DimensionScore)
            assert 0 <= dim.score <= 10
            assert dim.weight > 0
            assert dim.dimension in [d.value for d in EvaluationDimension]

    def test_add_dimension(self):
        """测试添加自定义维度"""
        # 使用现有维度测试添加/覆盖配置
        self.evaluator.add_dimension(
            dimension=EvaluationDimension.ACCURACY,
            weight=0.5,
            prompt_template="测试模板\n{report_content}",
        )

        assert EvaluationDimension.ACCURACY in self.evaluator.dimensions
        assert self.evaluator.dimensions[EvaluationDimension.ACCURACY]["weight"] == 0.5

    def test_batch_evaluate(self):
        """测试批量评测"""
        reports = [
            {"report_content": "报告1", "task_id": "task_001"},
            {"report_content": "报告2", "task_id": "task_002"},
        ]

        results = self.evaluator.batch_evaluate(reports)
        assert len(results) == 2

    def test_parse_json_response(self):
        """测试 JSON 解析"""
        # 标准 JSON
        result = self.evaluator._parse_json_response(
            '{"score": 8.5, "reasoning": "good", "deductions": [], "suggestions": []}'
        )
        assert result["score"] == 8.5

        # Markdown 代码块
        result = self.evaluator._parse_json_response(
            '```json\n{"score": 7.0, "reasoning": "ok", "deductions": [], "suggestions": []}\n```'
        )
        assert result["score"] == 7.0

        # 无效 JSON
        result = self.evaluator._parse_json_response("invalid")
        assert result["score"] == 0


class TestAlertService:
    """告警服务测试"""

    def setup_method(self):
        self.service = AlertService()
        # 清空历史、规则和触发记录
        self.service._rules.clear()
        self.service._alert_history.clear()
        self.service._triggered_rules.clear()

    def test_add_rule(self):
        rule = AlertRule(
            rule_id="test_rule",
            name="测试规则",
            metric="test_metric",
            condition=">",
            threshold=100,
            level=AlertLevel.WARNING,
        )
        self.service.add_rule(rule)

        assert "test_rule" in self.service._rules

    def test_remove_rule(self):
        rule = AlertRule(
            rule_id="test_rule",
            name="测试规则",
            metric="test_metric",
            condition=">",
            threshold=100,
            level=AlertLevel.WARNING,
        )
        self.service.add_rule(rule)
        result = self.service.remove_rule("test_rule")

        assert result is True
        assert "test_rule" not in self.service._rules

    def test_check_metric(self):
        rule = AlertRule(
            rule_id="high_value",
            name="高值告警",
            metric="value",
            condition=">",
            threshold=100,
            level=AlertLevel.WARNING,
            cooldown_seconds=0,
        )
        self.service.add_rule(rule)

        alerts = self.service.check_metric("value", 150)
        assert len(alerts) == 1
        assert alerts[0].current_value == 150

    def test_check_metric_no_alert(self):
        rule = AlertRule(
            rule_id="high_value",
            name="高值告警",
            metric="value",
            condition=">",
            threshold=100,
            level=AlertLevel.WARNING,
        )
        self.service.add_rule(rule)

        alerts = self.service.check_metric("value", 50)
        assert len(alerts) == 0

    def test_cooldown(self):
        rule = AlertRule(
            rule_id="cooldown_test",
            name="冷却测试",
            metric="value",
            condition=">",
            threshold=100,
            level=AlertLevel.WARNING,
            cooldown_seconds=3600,
        )
        self.service.add_rule(rule)

        # 第一次触发
        alerts1 = self.service.check_metric("value", 150)
        assert len(alerts1) == 1

        # 冷却期内不触发
        alerts2 = self.service.check_metric("value", 150)
        assert len(alerts2) == 0

    def test_get_alert_history(self):
        rule = AlertRule(
            rule_id="test",
            name="测试",
            metric="value",
            condition=">",
            threshold=0,
            level=AlertLevel.WARNING,
            cooldown_seconds=0,
        )
        self.service.add_rule(rule)
        self.service.check_metric("value", 1)

        history = self.service.get_alert_history(limit=10)
        assert len(history) == 1

    def test_enable_disable(self):
        self.service.disable()
        assert self.service._enabled is False

        self.service.enable()
        assert self.service._enabled is True


class TestDashboardService:
    """仪表盘服务测试"""

    def setup_method(self):
        self.dashboard = DashboardService()
        # 清空数据
        self.dashboard.trace_collector._traces.clear()

    def test_get_overview_metrics(self):
        metrics = self.dashboard.get_overview_metrics(hours=24)

        assert "total_tasks" in metrics
        assert "success_rate" in metrics
        assert "avg_duration_ms" in metrics

    def test_export_to_json(self):
        # 创建测试数据
        trace_id = self.dashboard.trace_collector.start_trace("test")
        self.dashboard.trace_collector.end_trace(trace_id)

        json_data = self.dashboard.export_to_json(hours=24)
        assert len(json_data) > 0
        assert "export_time" in json_data

    def test_export_to_csv(self):
        trace_id = self.dashboard.trace_collector.start_trace("test")
        self.dashboard.trace_collector.end_trace(trace_id)

        csv_data = self.dashboard.export_to_csv(hours=24)
        assert len(csv_data) > 0
        assert "trace_id" in csv_data

    def test_generate_report(self):
        report = self.dashboard.generate_report(hours=24, format="markdown")
        assert "Agent 系统运行报告" in report
        assert "任务概览" in report

    def test_get_time_series(self):
        trace_id = self.dashboard.trace_collector.start_trace("test")
        self.dashboard.trace_collector.end_trace(trace_id)

        points = self.dashboard.get_time_series("task_count", hours=24)
        assert isinstance(points, list)

    def test_get_realtime_stats(self):
        stats = self.dashboard.get_realtime_stats()
        assert "timestamp" in stats
        assert "active_traces" in stats