# 可观测性与评测体系架构设计

## 1. 系统架构

```
+------------------+     +------------------+     +------------------+
|   Agent 执行层    | --> |  可观测性采集层   | --> |   数据存储层      |
|  (Crew/Tasks)    |     | (TraceCollector) |     | (Langfuse/Local) |
+------------------+     +------------------+     +------------------+
         |                       |                         |
         v                       v                         v
+------------------+     +------------------+     +------------------+
|   告警服务层      |     |   评测服务层      |     |   仪表盘展示层    |
| (AlertService)   |     | (LLMJudgeEvaluator)|    | (DashboardService)|
+------------------+     +------------------+     +------------------+
```

## 2. 模块说明

### 2.1 Langfuse 客户端 (`langfuse_client.py`)

封装 Langfuse SDK，提供：
- Trace/Span/Generation/Event 创建
- 评分记录
- 批量数据上报
- 连接健康检查

**配置方式**（环境变量）：
```bash
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # 或自托管地址
LANGFUSE_RELEASE=v1.0.0
LANGFUSE_ENVIRONMENT=production
```

### 2.2 Trace 采集器 (`trace_collector.py`)

核心采集模块，支持：

| 数据类型 | 采集内容 | 精度 |
|---------|---------|------|
| Tool Call | 工具名、参数、返回结果、耗时 | 毫秒级 |
| Token 消耗 | 输入/输出/总 Token、成本 | 精确计数 |
| Prompt 演变 | 版本、内容、角色、时间戳 | 完整记录 |
| 决策节点 | 类型、选项、选择、置信度 | 完整记录 |

**使用方式**：
```python
from observability import TraceCollector, trace_span, trace_tool_call

collector = TraceCollector()
collector.initialize()

# 方式1: 装饰器
trace_id = collector.start_trace("research_task", task_id="task_001")

# 方式2: 上下文管理器
with trace_tool_call("tavily_search", {"query": "AI trends"}) as record:
    result = tavily_search("AI trends")

# 方式3: 手动记录
collector.record_token_usage("gpt-4", input_tokens=1000, output_tokens=500)

collector.end_trace(trace_id, status="completed")
```

### 2.3 LLM-as-a-Judge 评测器 (`evaluator.py`)

多维度自动化评测体系：

| 维度 | 权重 | 说明 |
|------|------|------|
| 信源一致性 | 0.25 | 报告内容与原始数据源的一致性 |
| 逻辑严密性 | 0.25 | 论证过程的逻辑性和连贯性 |
| 准确性 | 0.15 | 事实陈述的准确程度 |
| 完整性 | 0.15 | 内容覆盖的全面程度 |
| 引用质量 | 0.20 | 引用的规范性和可靠性 |

**使用方式**：
```python
from observability import LLMJudgeEvaluator

evaluator = LLMJudgeEvaluator()

result = evaluator.evaluate(
    report_content=report,
    source_data=source_data,
    task_id="task_001",
)

print(f"综合得分: {result.overall_score}/10")
for dim in result.dimensions:
    print(f"{dim.dimension}: {dim.score}/10")
```

### 2.4 告警服务 (`alert_service.py`)

内置告警规则：

| 规则ID | 名称 | 阈值 | 级别 |
|--------|------|------|------|
| tool_call_timeout | Tool Call 超时 | > 30s | WARNING |
| tool_call_critical_timeout | Tool Call 严重超时 | > 60s | CRITICAL |
| high_token_usage | Token 消耗过高 | > 10000 | WARNING |
| critical_token_usage | Token 消耗严重超标 | > 20000 | CRITICAL |
| tool_call_failure | 工具调用失败 | 成功率 < 80% | CRITICAL |
| high_cost | 调用成本过高 | > $0.5 | WARNING |
| trace_duration_long | Trace 执行时间过长 | > 5min | WARNING |
| trace_duration_critical | Trace 执行时间严重超时 | > 10min | CRITICAL |

### 2.5 仪表盘服务 (`dashboard_service.py`)

提供数据导出：
- JSON 格式（完整数据）
- CSV 格式（表格数据）
- Markdown/HTML 报告（汇报用）

## 3. 集成指南

### 3.1 与 Crew 集成

修改 `core/crew.py`：

```python
from observability import TraceCollector, trace_span

class ResearchCrew:
    def run(self, topic, depth="standard"):
        collector = TraceCollector()
        trace_id = collector.start_trace(
            name="research_execution",
            task_id=self.task_id,
            agent_type="ResearchCrew",
        )
        
        try:
            plan = self.create_plan(topic, depth)
            crew = self.build_crew(topic, plan)
            result = crew.kickoff()
            
            collector.end_trace(trace_id, status="completed")
            return result
        except Exception as e:
            collector.end_trace(trace_id, status="failed")
            raise
```

### 3.2 与工具集成

修改 `tools/search_tool.py`：

```python
from observability import trace_tool_call

@tool("Tavily Web Search")
def tavily_search(query, max_results=5):
    with trace_tool_call("tavily_search", {"query": query, "max_results": max_results}):
        # 原有逻辑
        ...
```

### 3.3 与评测集成

修改 `app/services/task_service.py`：

```python
from observability import LLMJudgeEvaluator

class TaskService:
    async def execute_task(self, task_id, execution_func, *args, **kwargs):
        # 执行任务...
        result = await loop.run_in_executor(None, lambda: execution_func(*args, **kwargs))
        
        # 自动评测
        evaluator = LLMJudgeEvaluator()
        eval_result = evaluator.evaluate(
            report_content=str(result),
            task_id=task_id,
        )
        
        # 保存评测结果...
```

## 4. 部署指南

### 4.1 安装依赖

```bash
pip install langfuse
```

### 4.2 配置环境变量

```bash
# .env 文件
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4.3 启动服务

无需额外启动，随 Agent 系统自动运行。

## 5. API 接口

### 5.1 获取 Trace 数据

```python
from observability import TraceCollector

collector = TraceCollector()

# 按 Trace ID 查询
trace = collector.get_trace("trace_uuid")

# 按任务ID查询
traces = collector.get_traces_by_task("task_001")

# 按时间范围查询
from datetime import datetime, timedelta
traces = collector.get_traces_by_time_range(
    start=datetime.now() - timedelta(hours=24),
    end=datetime.now(),
    agent_type="ResearchAgent",
)
```

### 5.2 获取告警历史

```python
from observability import AlertService

alert_service = AlertService()

# 获取最近告警
alerts = alert_service.get_alert_history(limit=50)

# 按级别筛选
critical_alerts = alert_service.get_alert_history(level=AlertLevel.CRITICAL)
```

### 5.3 数据导出

```python
from observability import DashboardService

dashboard = DashboardService()

# JSON 导出
json_data = dashboard.export_to_json(hours=24)

# CSV 导出
csv_data = dashboard.export_to_csv(task_id="task_001")

# 生成报告
report = dashboard.generate_report(hours=24, format="markdown")
```