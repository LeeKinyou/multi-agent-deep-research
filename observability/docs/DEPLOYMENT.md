# 可观测性模块部署指南

## 环境要求

- Python 3.10+
- 已安装项目依赖
- Langfuse 账号（可选，用于云端追踪）

## 安装步骤

### 1. 安装 Langfuse SDK

```bash
pip install langfuse
```

### 2. 配置环境变量

在项目根目录 `.env` 文件中添加：

```bash
# Langfuse 配置（云端）
LANGFUSE_PUBLIC_KEY=pk-your-public-key
LANGFUSE_SECRET_KEY=sk-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_RELEASE=v1.0.0
LANGFUSE_ENVIRONMENT=production

# 或自托管配置
# LANGFUSE_HOST=http://localhost:3000
```

### 3. 验证安装

```python
from observability import get_langfuse_client

client = get_langfuse_client()
if client.health_check():
    print("Langfuse 连接成功")
else:
    print("Langfuse 连接失败，将以本地模式运行")
```

## Langfuse 自托管部署（可选）

### Docker Compose 部署

```yaml
# docker-compose.langfuse.yml
version: "3"
services:
  langfuse:
    image: ghcr.io/langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langfuse
      - NEXTAUTH_SECRET=your-secret
      - SALT=your-salt
      - ENCRYPTION_KEY=your-encryption-key
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: langfuse
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

启动命令：
```bash
docker-compose -f docker-compose.langfuse.yml up -d
```

访问地址：`http://localhost:3000`

## 集成到现有 Agent

### 1. 在 Crew 执行中集成

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
            # 记录 Prompt
            collector.record_prompt(
                prompt_text=f"研究主题: {topic}",
                role="user",
                metadata={"depth": depth},
            )
            
            plan = self.create_plan(topic, depth)
            crew = self.build_crew(topic, plan)
            
            # 记录决策
            collector.record_decision(
                decision_type="plan_confirmation",
                context={"plan": plan.to_dict()},
                options=["execute", "modify", "cancel"],
                selected_option="execute",
                confidence=0.95,
            )
            
            result = crew.kickoff()
            
            collector.end_trace(trace_id, status="completed")
            return result
            
        except Exception as e:
            collector.end_trace(trace_id, status="failed")
            raise
```

### 2. 在工具调用中集成

修改 `tools/search_tool.py`：

```python
from observability import trace_tool_call

@tool("Tavily Web Search")
def tavily_search(query, max_results=5):
    with trace_tool_call(
        tool_name="tavily_search",
        input_params={"query": query, "max_results": max_results},
    ):
        # 原有逻辑
        results = tavily_tool.invoke({"query": query})
        return results
```

### 3. 在任务执行后集成评测

修改 `app/services/task_service.py`：

```python
from observability import LLMJudgeEvaluator

class TaskService:
    async def execute_task(self, task_id, execution_func, *args, **kwargs):
        # 执行任务
        result = await loop.run_in_executor(None, lambda: execution_func(*args, **kwargs))
        
        # 自动评测
        try:
            evaluator = LLMJudgeEvaluator()
            eval_result = evaluator.evaluate(
                report_content=str(result),
                task_id=task_id,
            )
            
            # 记录评测结果
            logger.info(f"Task {task_id} evaluation: {eval_result.overall_score}/10")
            
            # 保存到数据库（可选）
            # self.save_evaluation(task_id, eval_result.to_dict())
            
        except Exception as e:
            logger.error(f"Evaluation failed for task {task_id}: {e}")
        
        return result
```

## 性能优化

### 1. 批量上报

Langfuse 客户端默认配置：
- `flush_at=10`: 每10条记录批量上报
- `flush_interval=5`: 每5秒强制刷新

可根据场景调整：
```python
client = Langfuse(
    flush_at=50,        # 高并发场景增大批量
    flush_interval=10,  # 降低上报频率
)
```

### 2. 异步采集

Trace 数据采集使用上下文变量，无锁开销：
```python
from contextvars import ContextVar
_current_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
```

### 3. 本地缓存

当 Langfuse 不可用时，数据保存在内存中：
```python
self._local_buffer: List[Dict[str, Any]] = []
self._buffer_size = 100
```

## 监控与维护

### 查看 Langfuse 仪表盘

1. 登录 Langfuse 控制台
2. 查看 Trace 列表
3. 分析性能指标
4. 查看评分趋势

### 告警检查

```python
from observability import AlertService

alert_service = AlertService()

# 查看最近告警
alerts = alert_service.get_alert_history(limit=20)
for alert in alerts:
    print(f"[{alert.level}] {alert.message}")
```

### 数据清理

定期清理过期 Trace 数据：
```python
from datetime import datetime, timedelta

collector = TraceCollector()
cutoff = datetime.now() - timedelta(days=7)

# 清理7天前的数据
to_remove = [
    tid for tid, trace in collector._traces.items()
    if datetime.fromisoformat(trace.start_time) < cutoff
]
for tid in to_remove:
    del collector._traces[tid]
```