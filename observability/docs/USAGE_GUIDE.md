# 可观测性模块使用手册

## 快速开始

### 1. 初始化

```python
from observability import TraceCollector, LLMJudgeEvaluator, AlertService

# 初始化 Trace 采集器
collector = TraceCollector()
collector.initialize()

# 初始化告警服务
alert_service = AlertService()

# 初始化评测器
evaluator = LLMJudgeEvaluator()
```

### 2. 追踪 Agent 执行

```python
# 开始 Trace
trace_id = collector.start_trace(
    name="market_research",
    task_id="task_001",
    agent_type="ResearchCrew",
    metadata={"topic": "AI Market", "depth": "deep"},
)

# 记录 Token 消耗
collector.record_token_usage(
    model="gpt-4",
    input_tokens=1500,
    output_tokens=800,
)

# 记录 Prompt
collector.record_prompt(
    prompt_text="分析AI市场趋势...",
    role="system",
    version=1,
)

# 记录决策
collector.record_decision(
    decision_type="search_strategy",
    context={"topic": "AI Market"},
    options=["broad_search", "focused_search"],
    selected_option="focused_search",
    reasoning="主题明确，聚焦搜索更高效",
    confidence=0.85,
)

# 结束 Trace
collector.end_trace(trace_id, status="completed")
```

### 3. 评测报告

```python
report = """
# AI 市场趋势分析报告

## 执行摘要
AI 市场预计在2025年达到5000亿美元...

## 市场现状
...
"""

source_data = """
[1] Gartner Report 2024: AI Market Size...
[2] McKinsey: AI Adoption Survey...
"""

result = evaluator.evaluate(
    report_content=report,
    source_data=source_data,
    task_id="task_001",
)

print(f"综合得分: {result.overall_score}/10")
for dim in result.dimensions:
    print(f"  {dim.dimension}: {dim.score}/10")
    print(f"    扣分点: {dim.deductions}")
    print(f"    建议: {dim.suggestions}")
```

### 4. 查看告警

```python
# 检查最近告警
alerts = alert_service.get_alert_history(limit=10)
for alert in alerts:
    print(f"[{alert.level}] {alert.rule_name}: {alert.message}")
```

### 5. 导出数据

```python
from observability import DashboardService

dashboard = DashboardService()

# 导出 JSON
json_data = dashboard.export_to_json(hours=24)
with open("traces.json", "w") as f:
    f.write(json_data)

# 导出 CSV
csv_data = dashboard.export_to_csv(hours=24)
with open("traces.csv", "w") as f:
    f.write(csv_data)

# 生成报告
report = dashboard.generate_report(hours=24, format="markdown")
with open("report.md", "w") as f:
    f.write(report)
```

## 高级用法

### 自定义评测维度

```python
from observability.evaluator import EvaluationDimension

custom_prompt = """评估报告的创新性...

## 评分标准（0-10分）：
...

## 报告：
{report_content}

请输出JSON格式：
{{
    "score": float,
    "reasoning": "...",
    "deductions": [],
    "suggestions": []
}}"""

evaluator.add_dimension(
    dimension=EvaluationDimension("innovation"),
    weight=0.15,
    prompt_template=custom_prompt,
    requires_source=False,
)
```

### 自定义告警规则

```python
from observability.alert_service import AlertRule, AlertLevel, AlertChannel

rule = AlertRule(
    rule_id="custom_rule",
    name="自定义规则",
    metric="custom_metric",
    condition=">",
    threshold=100,
    level=AlertLevel.WARNING,
    channels=[AlertChannel.LOG, AlertChannel.WEBHOOK],
    cooldown_seconds=600,
    description="自定义指标超过阈值",
)

alert_service.add_rule(rule)
```

### 自定义告警处理器

```python
def send_slack_alert(alert):
    import requests
    requests.post(
        "https://hooks.slack.com/...",
        json={"text": alert.message},
    )

alert_service.register_handler(AlertChannel.SLACK, send_slack_alert)
```

## 常见问题

### Q: Langfuse 连接失败怎么办？

A: 系统会自动降级到本地模式，数据保存在内存中。检查环境变量配置或网络连接。

### Q: 如何关闭可观测性？

A: 不设置 Langfuse 环境变量即可，系统会以本地模式运行，不产生外部依赖。

### Q: 评测结果不准确怎么办？

A: 可以调整 Prompt 模板或权重配置，也可以添加人工校验环节。

### Q: 性能开销大吗？

A: Trace 采集使用上下文变量，开销极小。Langfuse 上报是异步的，不影响主流程。

## 最佳实践

1. **每个任务一个 Trace**: 便于追踪完整执行链路
2. **记录关键决策点**: 帮助分析 Agent 行为
3. **定期导出数据**: 避免内存占用过大
4. **设置合理阈值**: 避免告警风暴
5. **结合人工校验**: 确保评测标准准确