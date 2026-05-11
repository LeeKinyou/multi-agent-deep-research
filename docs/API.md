# MultiAgentDeepResearch API 文档

## 概述

MultiAgentDeepResearch API 提供了一套完整的RESTful接口,用于管理多智能体深度研究系统的任务、计划和结果。

**基础URL**: `http://localhost:8000`

**API文档**: 
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## 认证

API支持可选的API Key认证。在请求头中添加 `X-API-Key` 即可。

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/tasks/
```

## API端点

### 1. 健康检查

**GET** `/api/v1/health/`

检查服务健康状态。

**响应示例**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-05-11T12:00:00",
  "database": "connected"
}
```

### 2. 创建任务

**POST** `/api/v1/tasks/`

创建一个新的研究任务。

**请求体**:
```json
{
  "topic": "人工智能发展趋势",
  "depth": "standard"
}
```

**参数说明**:
- `topic` (string, 必填): 研究主题,1-500字符
- `depth` (string, 可选): 研究深度,可选值 `standard` 或 `deep`,默认 `standard`

**响应示例** (201 Created):
```json
{
  "task_id": "task_abc123",
  "topic": "人工智能发展趋势",
  "status": "planning",
  "depth": "standard",
  "created_at": "2026-05-11T12:00:00",
  "updated_at": "2026-05-11T12:00:00",
  "completed_at": null,
  "error_message": null
}
```

### 3. 获取任务列表

**GET** `/api/v1/tasks/`

获取所有任务列表,支持分页。

**查询参数**:
- `skip` (integer, 可选): 跳过记录数,默认 0
- `limit` (integer, 可选): 返回记录数,默认 50,最大 100

**响应示例**:
```json
{
  "tasks": [
    {
      "task_id": "task_abc123",
      "topic": "人工智能发展趋势",
      "status": "planning",
      "depth": "standard",
      "created_at": "2026-05-11T12:00:00",
      "updated_at": "2026-05-11T12:00:00",
      "completed_at": null,
      "error_message": null
    }
  ],
  "total": 1
}
```

### 4. 获取任务详情

**GET** `/api/v1/tasks/{task_id}`

获取指定任务的详细信息。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**响应示例**:
```json
{
  "task_id": "task_abc123",
  "topic": "人工智能发展趋势",
  "status": "planning",
  "depth": "standard",
  "created_at": "2026-05-11T12:00:00",
  "updated_at": "2026-05-11T12:00:00",
  "completed_at": null,
  "error_message": null
}
```

### 5. 获取任务结果

**GET** `/api/v1/tasks/{task_id}/result`

获取已完成任务的研究报告。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**响应示例** (200 OK):
```json
{
  "task_id": "task_abc123",
  "report_content": "# 研究报告内容...\n\n...",
  "report_format": "markdown",
  "sources_count": 10,
  "word_count": 5000,
  "created_at": "2026-05-11T12:30:00"
}
```

**错误响应** (400 Bad Request):
```json
{
  "detail": "Task is not completed. Current status: planning"
}
```

### 6. 获取任务日志

**GET** `/api/v1/tasks/{task_id}/logs`

获取任务的执行日志。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**查询参数**:
- `limit` (integer, 可选): 返回日志数,默认 100,最大 500

**响应示例**:
```json
[
  {
    "id": 1,
    "task_id": "task_abc123",
    "agent_name": "ResearchAgent",
    "step_name": "search",
    "log_level": "info",
    "message": "搜索完成",
    "validation_event": false,
    "timestamp": "2026-05-11T12:10:00"
  }
]
```

### 7. 取消任务

**POST** `/api/v1/tasks/{task_id}/cancel`

取消正在执行的任务。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**响应示例**:
```json
{
  "message": "Task task_abc123 cancelled successfully"
}
```

### 8. 获取研究计划

**GET** `/api/v1/tasks/{task_id}/plan/`

获取任务的研究计划。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**响应示例**:
```json
{
  "id": 1,
  "task_id": "task_abc123",
  "plan_content": {
    "tasks": [
      {
        "task_id": "1",
        "description": "搜索相关信息",
        "agent": "ResearchAgent",
        "search_queries": ["query1", "query2"]
      }
    ]
  },
  "version": 1,
  "status": "draft",
  "created_at": "2026-05-11T12:00:00",
  "confirmed_at": null
}
```

### 9. 创建研究计划

**POST** `/api/v1/tasks/{task_id}/plan/`

为任务创建研究计划。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**请求体**:
```json
{
  "task_id": "task_abc123",
  "plan_content": {
    "tasks": [
      {
        "task_id": "1",
        "description": "搜索相关信息",
        "agent": "ResearchAgent"
      }
    ]
  },
  "version": 1
}
```

### 10. 确认研究计划

**POST** `/api/v1/tasks/{task_id}/plan/confirm`

确认或修改研究计划。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**请求体**:
```json
{
  "confirmed": true,
  "modifications": null
}
```

**参数说明**:
- `confirmed` (boolean, 必填): 是否确认计划
- `modifications` (string, 可选): 修改意见

**响应示例**:
```json
{
  "id": 1,
  "task_id": "task_abc123",
  "plan_content": {...},
  "version": 1,
  "status": "confirmed",
  "created_at": "2026-05-11T12:00:00",
  "confirmed_at": "2026-05-11T12:05:00"
}
```

### 11. 更新研究计划

**PUT** `/api/v1/tasks/{task_id}/plan/`

更新研究计划内容。

**路径参数**:
- `task_id` (string, 必填): 任务ID

**请求体**:
```json
{
  "tasks": [
    {
      "task_id": "1",
      "description": "更新后的任务描述",
      "agent": "ResearchAgent"
    }
  ]
}
```

## 数据模型

### 任务状态 (TaskStatus)

- `planning`: 计划生成中
- `pending`: 等待执行
- `running`: 正在执行
- `completed`: 已完成
- `failed`: 执行失败
- `cancelled`: 已取消

### 计划状态 (PlanStatus)

- `draft`: 草稿
- `confirmed`: 已确认
- `modified`: 已修改

## 错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求错误 |
| 404 | 资源不存在 |
| 422 | 请求参数验证失败 |
| 500 | 服务器内部错误 |

## 使用示例

### 1. 创建研究任务

```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "人工智能在医疗领域的应用",
    "depth": "standard"
  }'
```

### 2. 查看任务状态

```bash
curl http://localhost:8000/api/v1/tasks/task_abc123
```

### 3. 查看研究计划

```bash
curl http://localhost:8000/api/v1/tasks/task_abc123/plan/
```

### 4. 确认计划

```bash
curl -X POST http://localhost:8000/api/v1/tasks/task_abc123/plan/confirm \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'
```

### 5. 获取研究结果

```bash
curl http://localhost:8000/api/v1/tasks/task_abc123/result
```

### 6. 查看执行日志

```bash
curl http://localhost:8000/api/v1/tasks/task_abc123/logs
```

## 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 性能指标

- API响应时间: P95 < 500ms
- 创建任务响应时间: < 2秒
- 并发任务数: 支持3个任务并行

## 版本历史

- v1.0.0 (2026-05-11): 初始版本,包含任务管理、计划管理、结果获取等核心功能
