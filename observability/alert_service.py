"""
异常检测与告警服务

实现基于规则的异常检测：
- 超预期耗时检测
- 异常 Token 消耗检测
- 工具调用失败检测
- 自定义阈值告警

支持多种告警渠道：日志、Webhook、邮件（可扩展）。
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Set
from collections import deque

from observability.trace_collector import TraceCollector, TraceData

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(str, Enum):
    """告警渠道"""
    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    metric: str                          # 监控指标
    condition: str                       # 条件: >, <, >=, <=, ==, !=
    threshold: float                     # 阈值
    level: AlertLevel
    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG])
    cooldown_seconds: int = 300          # 冷却时间
    enabled: bool = True
    description: str = ""
    last_triggered: Optional[str] = None


@dataclass
class AlertEvent:
    """告警事件"""
    alert_id: str
    rule_id: str
    rule_name: str
    level: AlertLevel
    metric: str
    current_value: float
    threshold: float
    condition: str
    message: str
    trace_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertService:
    """
    异常检测与告警服务

    单例模式，负责：
    1. 管理告警规则
    2. 实时检测异常
    3. 触发告警通知
    4. 告警历史记录
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._rules: Dict[str, AlertRule] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._triggered_rules: Dict[str, float] = {}  # rule_id -> last_triggered_timestamp
        self._handlers: Dict[AlertChannel, Callable] = {}
        self._enabled = True

        # 注册默认告警处理器
        self._register_default_handlers()

        # 注册默认规则
        self._register_default_rules()

    def _register_default_handlers(self) -> None:
        """注册默认告警处理器"""
        self._handlers[AlertChannel.LOG] = self._handle_log_alert
        self._handlers[AlertChannel.WEBHOOK] = self._handle_webhook_alert

    def _register_default_rules(self) -> None:
        """注册默认告警规则"""
        default_rules = [
            AlertRule(
                rule_id="tool_call_timeout",
                name="Tool Call 超时",
                metric="tool_call_duration_ms",
                condition=">",
                threshold=30000,  # 30秒
                level=AlertLevel.WARNING,
                description="Tool Call 执行时间超过30秒",
            ),
            AlertRule(
                rule_id="tool_call_critical_timeout",
                name="Tool Call 严重超时",
                metric="tool_call_duration_ms",
                condition=">",
                threshold=60000,  # 60秒
                level=AlertLevel.CRITICAL,
                description="Tool Call 执行时间超过60秒",
            ),
            AlertRule(
                rule_id="high_token_usage",
                name="Token 消耗过高",
                metric="total_tokens",
                condition=">",
                threshold=10000,
                level=AlertLevel.WARNING,
                description="单次请求 Token 消耗超过10000",
            ),
            AlertRule(
                rule_id="critical_token_usage",
                name="Token 消耗严重超标",
                metric="total_tokens",
                condition=">",
                threshold=20000,
                level=AlertLevel.CRITICAL,
                description="单次请求 Token 消耗超过20000",
            ),
            AlertRule(
                rule_id="tool_call_failure",
                name="工具调用失败",
                metric="tool_call_success_rate",
                condition="<",
                threshold=0.8,
                level=AlertLevel.CRITICAL,
                description="工具调用成功率低于80%",
            ),
            AlertRule(
                rule_id="high_cost",
                name="调用成本过高",
                metric="total_cost_usd",
                condition=">",
                threshold=0.5,
                level=AlertLevel.WARNING,
                description="单次任务成本超过0.5美元",
            ),
            AlertRule(
                rule_id="trace_duration_long",
                name="Trace 执行时间过长",
                metric="trace_duration_ms",
                condition=">",
                threshold=300000,  # 5分钟
                level=AlertLevel.WARNING,
                description="完整 Trace 执行时间超过5分钟",
            ),
            AlertRule(
                rule_id="trace_duration_critical",
                name="Trace 执行时间严重超时",
                metric="trace_duration_ms",
                condition=">",
                threshold=600000,  # 10分钟
                level=AlertLevel.CRITICAL,
                description="完整 Trace 执行时间超过10分钟",
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self._rules[rule.rule_id] = rule
        logger.info(f"Alert rule added: {rule.rule_id} - {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除告警规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Alert rule removed: {rule_id}")
            return True
        return False

    def update_rule(self, rule_id: str, **kwargs) -> bool:
        """更新告警规则"""
        if rule_id not in self._rules:
            return False

        rule = self._rules[rule_id]
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        logger.info(f"Alert rule updated: {rule_id}")
        return True

    def enable_rule(self, rule_id: str) -> bool:
        """启用告警规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用告警规则"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def check_trace(self, trace: TraceData) -> List[AlertEvent]:
        """
        检查 Trace 数据是否触发告警

        Args:
            trace: Trace 数据

        Returns:
            List[AlertEvent]: 触发的告警事件列表
        """
        if not self._enabled:
            return []

        alerts = []
        metrics = self._extract_metrics(trace)

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            if rule.metric not in metrics:
                continue

            current_value = metrics[rule.metric]

            if self._evaluate_condition(current_value, rule.condition, rule.threshold):
                # 检查冷却时间
                if self._is_in_cooldown(rule.rule_id):
                    continue

                alert = self._create_alert(rule, current_value, trace)
                alerts.append(alert)
                self._dispatch_alert(alert, rule.channels)
                self._triggered_rules[rule.rule_id] = time.time()

        return alerts

    def check_metric(
        self,
        metric_name: str,
        value: float,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[AlertEvent]:
        """检查单个指标是否触发告警"""
        if not self._enabled:
            return []

        alerts = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.metric != metric_name:
                continue

            if self._evaluate_condition(value, rule.condition, rule.threshold):
                if self._is_in_cooldown(rule.rule_id):
                    continue

                alert = AlertEvent(
                    alert_id=f"alert_{int(time.time() * 1000)}",
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    level=rule.level,
                    metric=metric_name,
                    current_value=value,
                    threshold=rule.threshold,
                    condition=rule.condition,
                    message=self._format_alert_message(rule, value),
                    trace_id=trace_id,
                    task_id=task_id,
                )

                alerts.append(alert)
                self._dispatch_alert(alert, rule.channels)
                self._triggered_rules[rule.rule_id] = time.time()

        return alerts

    def _extract_metrics(self, trace: TraceData) -> Dict[str, float]:
        """从 Trace 中提取指标"""
        metrics = {
            "trace_duration_ms": trace.total_duration_ms,
            "total_tokens": trace.total_input_tokens + trace.total_output_tokens,
            "total_input_tokens": trace.total_input_tokens,
            "total_output_tokens": trace.total_output_tokens,
            "total_cost_usd": trace.total_cost_usd,
            "tool_call_count": len(trace.tool_calls),
        }

        # 工具调用指标
        if trace.tool_calls:
            durations = [tc.duration_ms for tc in trace.tool_calls]
            metrics["tool_call_duration_ms"] = max(durations) if durations else 0
            metrics["tool_call_avg_duration_ms"] = sum(durations) / len(durations) if durations else 0
            metrics["tool_call_success_rate"] = sum(1 for tc in trace.tool_calls if tc.success) / len(trace.tool_calls)
        else:
            metrics["tool_call_duration_ms"] = 0
            metrics["tool_call_avg_duration_ms"] = 0
            metrics["tool_call_success_rate"] = 1.0

        return metrics

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """评估条件"""
        if condition == ">":
            return value > threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        return False

    def _is_in_cooldown(self, rule_id: str) -> bool:
        """检查是否在冷却期"""
        if rule_id not in self._triggered_rules:
            return False

        rule = self._rules.get(rule_id)
        if not rule:
            return False

        elapsed = time.time() - self._triggered_rules[rule_id]
        return elapsed < rule.cooldown_seconds

    def _create_alert(self, rule: AlertRule, current_value: float, trace: TraceData) -> AlertEvent:
        """创建告警事件"""
        return AlertEvent(
            alert_id=f"alert_{int(time.time() * 1000)}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            level=rule.level,
            metric=rule.metric,
            current_value=current_value,
            threshold=rule.threshold,
            condition=rule.condition,
            message=self._format_alert_message(rule, current_value),
            trace_id=trace.trace_id,
            task_id=trace.task_id,
            metadata={
                "trace_name": trace.name,
                "agent_type": trace.agent_type,
                "tool_calls_count": len(trace.tool_calls),
            },
        )

    def _format_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """格式化告警消息"""
        return (
            f"[{rule.level.upper()}] {rule.name}: "
            f"当前值 {current_value:.2f} {rule.condition} 阈值 {rule.threshold:.2f}. "
            f"{rule.description}"
        )

    def _dispatch_alert(self, alert: AlertEvent, channels: List[AlertChannel]) -> None:
        """分发告警到各渠道"""
        self._alert_history.append(alert)

        for channel in channels:
            handler = self._handlers.get(channel)
            if handler:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Failed to dispatch alert to {channel}: {e}")

    def _handle_log_alert(self, alert: AlertEvent) -> None:
        """日志告警处理器"""
        if alert.level == AlertLevel.INFO:
            logger.info(alert.message)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(alert.message)
        elif alert.level == AlertLevel.CRITICAL:
            logger.error(alert.message)
        elif alert.level == AlertLevel.EMERGENCY:
            logger.critical(alert.message)

    def _handle_webhook_alert(self, alert: AlertEvent) -> None:
        """Webhook 告警处理器（占位）"""
        # TODO: 实现 Webhook 推送
        logger.info(f"Webhook alert would be sent: {alert.message}")

    def register_handler(self, channel: AlertChannel, handler: Callable[[AlertEvent], None]) -> None:
        """注册自定义告警处理器"""
        self._handlers[channel] = handler
        logger.info(f"Registered alert handler for channel: {channel.value}")

    def get_alert_history(
        self,
        level: Optional[AlertLevel] = None,
        rule_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AlertEvent]:
        """获取告警历史"""
        alerts = list(self._alert_history)

        if level:
            alerts = [a for a in alerts if a.level == level]
        if rule_id:
            alerts = [a for a in alerts if a.rule_id == rule_id]

        return alerts[-limit:]

    def get_rules(self) -> List[AlertRule]:
        """获取所有告警规则"""
        return list(self._rules.values())

    def enable(self) -> None:
        """启用告警服务"""
        self._enabled = True
        logger.info("Alert service enabled")

    def disable(self) -> None:
        """禁用告警服务"""
        self._enabled = False
        logger.info("Alert service disabled")