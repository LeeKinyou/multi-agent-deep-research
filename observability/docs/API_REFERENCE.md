# 可观测性模块 API 参考

## TraceCollector

### 方法

#### `start_trace(name, task_id=None, agent_type="", metadata=None)`

开始一个新的 Trace。

**参数**：
- `name` (str): Trace 名称
- `task_id` (str, optional): 关联的任务ID
- `agent_type` (str): Agent 类型
- `metadata` (dict): 附加元数据

**返回**：
- `str`: Trace ID

**示例**：
```python
trace_id = collector.start_trace(
    name="research_execution",
    task_id="task_001",
    agent_type="ResearchCrew",
)
```

#### `end_trace(trace_id=None, status="completed", metadata=None)`

结束 Trace 并计算汇总指标。

**参数**：
- `trace_id` (str, optional): Trace ID，默认使用当前上下文
- `status` (str): 状态 (completed/failed/running)
- `metadata` (dict): 附加元数据

**返回**：
- `TraceData`: Trace 数据对象

#### `record_tool_call(tool_name, input_params, output_result=None, error=None, duration_ms=None)`

记录 Tool Call。

**参数**：
- `tool_name` (str): 工具名称
- `input_params` (dict): 输入参数
- `output_result`: 输出结果
- `error` (str, optional): 错误信息
- `duration_ms` (float, optional): 耗时（毫秒）

**返回**：
- `ToolCallRecord`: 工具调用记录

#### `record_token_usage(model, input_tokens, output_tokens, cost_usd=None)`

记录 Token 消耗。

**参数**：
- `model` (str): 模型名称
- `input_tokens` (int): 输入 Token 数
- `output_tokens` (int): 输出 Token 数
- `cost_usd` (float, optional): 成本（美元）

**返回**：
- `TokenUsageRecord`: Token 使用记录

#### `record_prompt(prompt_text, role="system", version=None, metadata=None)`

记录 Prompt 演变。

**参数**：
- `prompt_text` (str): Prompt 内容
- `role` (str): 角色 (system/user/assistant)
- `version` (int, optional): 版本号
- `metadata` (dict): 附加元数据

**返回**：
- `PromptRecord`: Prompt 记录

#### `record_decision(decision_type, context, options, selected_option, reasoning="", confidence=0.0)`

记录决策节点。

**参数**：
- `decision_type` (str): 决策类型
- `context` (dict): 决策上下文
- `options` (list): 可选选项
- `selected_option` (str): 选中的选项
- `reasoning` (str): 决策理由
- `confidence` (float): 置信度 (0-1)

**返回**：
- `DecisionRecord`: 决策记录

#### `get_trace(trace_id)`

获取指定 Trace。

**返回**：
- `TraceData` 或 `None`

#### `get_traces_by_task(task_id)`

按任务ID查询 Trace。

**返回**：
- `List[TraceData]`

#### `get_traces_by_time_range(start, end, agent_type=None)`

按时间范围查询 Trace。

**返回**：
- `List[TraceData]`

## LLMJudgeEvaluator

### 方法

#### `evaluate(report_content, source_data=None, task_id=None, dimensions=None)`

执行完整评测。

**参数**：
- `report_content` (str): 待评测报告
- `source_data` (str, optional): 原始数据源
- `task_id` (str, optional): 任务ID
- `dimensions` (list, optional): 指定评测维度

**返回**：
- `EvaluationResult`: 评测结果

**示例**：
```python
result = evaluator.evaluate(
    report_content=report,
    source_data=source,
    task_id="task_001",
    dimensions=[
        EvaluationDimension.SOURCE_CONSISTENCY,
        EvaluationDimension.LOGICAL_RIGOR,
    ],
)
```

#### `add_dimension(dimension, weight, prompt_template, requires_source=False)`

添加自定义评测维度。

**参数**：
- `dimension` (EvaluationDimension): 维度枚举
- `weight` (float): 权重
- `prompt_template` (str): Prompt 模板
- `requires_source` (bool): 是否需要源数据

#### `batch_evaluate(reports)`

批量评测。

**参数**：
- `reports` (list): 报告列表，每项为 dict 包含 report_content, source_data, task_id

**返回**：
- `List[EvaluationResult]`

## AlertService

### 方法

#### `add_rule(rule)`

添加告警规则。

**参数**：
- `rule` (AlertRule): 规则对象

#### `check_trace(trace)`

检查 Trace 是否触发告警。

**返回**：
- `List[AlertEvent]`

#### `check_metric(metric_name, value, trace_id=None, task_id=None)`

检查单个指标。

**返回**：
- `List[AlertEvent]`

#### `get_alert_history(level=None, rule_id=None, limit=100)`

获取告警历史。

**返回**：
- `List[AlertEvent]`

#### `register_handler(channel, handler)`

注册自定义告警处理器。

**参数**：
- `channel` (AlertChannel): 渠道枚举
- `handler` (callable): 处理函数 `(AlertEvent) -> None`

## DashboardService

### 方法

#### `get_overview_metrics(hours=24)`

获取概览指标。

**返回**：
```python
{
    "period_hours": 24,
    "total_tasks": 100,
    "completed_tasks": 95,
    "failed_tasks": 3,
    "success_rate": 95.0,
    "avg_duration_ms": 15000.5,
}
```

#### `get_task_performance(task_id)`

获取任务性能数据。

#### `get_time_series(metric, hours=24, interval_minutes=60)`

获取时间序列数据。

**支持的指标**：
- `task_count`
- `avg_duration_ms`
- `total_tokens`
- `total_cost_usd`
- `success_rate`
- `tool_call_count`
- `avg_tool_duration_ms`

#### `export_to_json(task_id=None, hours=24)`

导出 JSON 数据。

#### `export_to_csv(task_id=None, hours=24)`

导出 CSV 数据。

#### `generate_report(hours=24, format="markdown")`

生成统计报告。

**格式**：
- `markdown`: Markdown 格式
- `html`: HTML 格式

## 装饰器

### `trace_span(span_name, agent_type="")`

函数装饰器，自动追踪函数执行。

```python
from observability import trace_span

@trace_span("plan_generation", agent_type="PlanningAgent")
def generate_plan(topic):
    ...
```

### `trace_tool_call(tool_name, input_params=None)`

上下文管理器，追踪 Tool Call。

```python
from observability import trace_tool_call

with trace_tool_call("search", {"query": "AI"}):
    result = search_tool("AI")
```