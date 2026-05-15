# 混合计算架构技术文档

## 1. 架构概述

混合计算架构（Hybrid Computing Architecture）为企业级多模态交互系统提供云/本地协同处理能力，在保障数据隐私的同时实现高性能响应。

### 1.1 设计目标

| 目标 | 指标 | 说明 |
|------|------|------|
| 数据隐私 | 敏感数据 100% 本地处理 | 核心流程、内部数据不上云 |
| 本地延迟 | < 200ms | 高频敏感查询快速响应 |
| 云端延迟 | < 500ms | 通用交互合理响应时间 |
| 路由准确率 | > 99.9% | 意图分类与路由决策准确 |
| 无缝切换 | 用户无感知 | 云/本地模式平滑切换 |

### 1.2 架构全景图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户请求                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HybridRouter (混合路由器)                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐ │
│  │ IntentClassifier│→│ SecurityFilter   │→│  Routing Decision  │ │
│  │ (意图识别)       │  │ (安全检查)       │  │  (路由决策)        │ │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
┌──────────────────┐  ┌───────────────┐  ┌──────────────────┐
│  LocalProcessor  │  │ Cache Layer   │  │ CloudProcessor   │
│  (本地处理层)     │  │ (缓存层)      │  │ (云端处理层)      │
│                  │  │               │  │                  │
│ • 本地 LLM       │  │ • 5min TTL    │  │ • OpenAI API     │
│ • RAG 知识库     │  │ • 10x 加速    │  │ • DeepSeek API   │
│ • 敏感数据处理   │  │               │  │ • 通用交互       │
└────────┬─────────┘  └───────────────┘  └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  LocalKnowledgeBase (本地知识库)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ 文档存储     │  │ 向量检索     │  │ 版本管理 & 完整性校验    │  │
│  │ (JSON文件)   │  │ (ChromaDB)   │  │ (SHA-256 校验)           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 核心模块

### 2.1 意图识别与动态路由 (`intent_classifier.py`)

**分类策略**：规则匹配 + LLM 分类 + 综合决策

```
用户查询
    │
    ├──→ 规则匹配（快速识别敏感关键词）
    │       ├── 命中 → 置信度 0.85 → 直接路由
    │       └── 未命中 → 进入 LLM 分类
    │
    ├──→ LLM 分类（复杂意图识别）
    │       ├── 返回 JSON 格式分类结果
    │       └── 包含意图类型、敏感度、置信度
    │
    └──→ 综合决策
            ├── 规则判定敏感 → 优先规则结果
            ├── LLM 置信度更高 → 采用 LLM 结果
            └── 默认 → 规则结果
```

**意图类型**：
- `GENERAL_CHAT`: 通用闲聊
- `CREATIVE_WRITING`: 创意内容生成
- `GENERAL_QUERY`: 通用问题查询
- `SENSITIVE_DATA`: 敏感数据处理
- `INTERNAL_METRICS`: 内部业务指标
- `MARKETING_DATA`: 营销数据
- `AMBIGUOUS`: 模糊查询（需人工干预）

**敏感度级别**：
- `PUBLIC`: 公开数据，可上云
- `INTERNAL`: 内部数据，本地处理
- `CONFIDENTIAL`: 机密数据，严格本地处理
- `RESTRICTED`: 受限数据，禁止处理

### 2.2 安全过滤器 (`security_filter.py`)

**数据分类**：
```python
SENSITIVE_DATA_PATTERNS = {
    DataType.CONFIDENTIAL: [
        "银行卡号", "身份证号", "密码/密钥", "API密钥", "加密哈希",
    ],
    DataType.INTERNAL: [
        "财务数据", "客户数据", "销售数据", "运营指标", "薪酬数据",
        "内部业务数据", "营销数据",
    ],
}
```

**脱敏处理**：自动替换敏感信息为 `[REDACTED]`

**传输检查**：验证数据是否可以安全发送到云端

**审计日志**：记录所有安全相关操作，支持查询和导出

### 2.3 混合路由器 (`router.py`)

**处理流程**：
1. 缓存检查（5min TTL）
2. 意图分类（除非强制模式）
3. 安全检查（拦截敏感数据上云）
4. 路由到对应处理层
5. 降级容错（失败时自动降级到本地）

**处理模式**：
- `CLOUD`: 云端处理
- `LOCAL`: 本地处理
- `HYBRID`: 混合处理
- `FALLBACK`: 降级处理

**统计追踪**：
- 总请求数、本地/云端请求数
- 本地/云端比例
- 缓存大小和 TTL

### 2.4 本地处理器 (`local_processor.py`)

**支持**：
- 本地 LLM 推理（Ollama、LM Studio 等）
- RAG 增强生成
- 降级策略（模型不可用时回退）

**配置**：
```python
LocalProcessor(
    model_url="http://localhost:1234/v1",
    model_name="qwen2.5-7b-instruct",
    knowledge_base=LocalKnowledgeBase(),
)
```

### 2.5 云端处理器 (`cloud_processor.py`)

**支持**：
- OpenAI/DeepSeek 等云端 API
- 连接池和超时控制
- 错误重试机制

### 2.6 本地知识库 (`local_knowledge_base.py`)

**功能**：
- 企业私有数据安全本地存储
- 文档分块与索引
- 向量相似度检索（ChromaDB）
- 文本检索（降级方案）
- 版本管理与完整性校验

## 3. 使用指南

### 3.1 基本使用

```python
from hybrid_computing import HybridRouter

router = HybridRouter()

# 处理查询（自动路由）
result = router.process_query("核心流程参数是什么？")
print(f"模式: {result.mode.value}")
print(f"延迟: {result.latency_ms:.0f}ms")
print(f"响应: {result.response}")

# 强制模式
result = router.process_query("测试", force_mode=ProcessingMode.CLOUD)
```

### 3.2 安全过滤

```python
from hybrid_computing import SecurityFilter

filter = SecurityFilter(strict_mode=True)

# 数据分类
classification = filter.classify_data("本月营收 500 万元")
print(f"类型: {classification.data_type.value}")
print(f"风险: {classification.risk_level}")

# 数据脱敏
result = filter.sanitize_data("密码：secret123")
print(f"脱敏后: {result.sanitized_text}")

# 传输检查
can_send, reason = filter.can_send_to_cloud("内部销售数据")
print(f"可上云: {can_send}, 原因: {reason}")
```

### 3.3 知识库管理

```python
from hybrid_computing import LocalKnowledgeBase

kb = LocalKnowledgeBase()

# 添加文档
doc_id = kb.add_document(
    title="2024年Q1销售报告",
    content="本季度销售额达到 500 万元...",
    metadata={"quarter": "Q1", "year": 2024},
)

# 检索
results = kb.search("销售额", n_results=3)

# 删除
kb.delete_document(doc_id)
```

## 4. 性能指标

### 4.1 延迟目标

| 场景 | 目标 | 实际 |
|------|------|------|
| 本地处理 | < 200ms | 待验证 |
| 云端处理 | < 500ms | 待验证 |
| 路由切换 | < 100ms | 待验证 |
| 缓存命中 | < 10ms | 待验证 |

### 4.2 准确率目标

| 指标 | 目标 | 实际 |
|------|------|------|
| 意图分类 | > 99.9% | 规则匹配 85%+ |
| 安全检测 | 100% | 待验证 |
| 路由决策 | > 99.9% | 待验证 |

## 5. 安全边界

### 5.1 数据分类规则

| 级别 | 处理方式 | 示例 |
|------|---------|------|
| PUBLIC | 可上云 | 天气、知识问答、闲聊 |
| INTERNAL | 本地处理 | 内部数据、销售数据、客户信息 |
| CONFIDENTIAL | 严格本地 | 银行卡号、密码、API密钥 |
| RESTRICTED | 禁止处理 | 国家机密、核心源代码 |

### 5.2 传输安全

- 敏感数据 **绝不** 传输到云端
- 云端传输前必须进行脱敏检查
- 严格模式下内部数据禁止上云
- 所有安全操作记录审计日志

## 6. 部署指南

### 6.1 环境要求

- Python 3.10+
- 本地 LLM 服务（可选，如 Ollama、LM Studio）
- ChromaDB（向量存储）

### 6.2 安装

```bash
pip install -r requirements.txt
```

### 6.3 配置

```python
# .env 文件
LOCAL_MODEL_URL=http://localhost:1234/v1
LOCAL_MODEL_NAME=qwen2.5-7b-instruct
KNOWLEDGE_BASE_PATH=./data/knowledge_base
SECURITY_STRICT_MODE=true
```

## 7. 测试

### 7.1 单元测试

```bash
pytest tests/test_hybrid_computing.py -v
```

### 7.2 性能测试

```bash
python tests/test_hybrid_computing_performance.py
```

### 7.3 安全验证

```bash
python tests/test_hybrid_computing_security.py
```

## 8. 与现有系统集成

### 8.1 集成到 CrewAI

```python
from hybrid_computing import HybridRouter

router = HybridRouter()

# 在 Agent 工具中使用
def smart_query(query: str) -> str:
    result = router.process_query(query)
    return result.response
```

### 8.2 集成到 FastAPI

```python
from fastapi import FastAPI
from hybrid_computing import HybridRouter

app = FastAPI()
router = HybridRouter()

@app.post("/api/v1/query")
async def handle_query(query: str):
    result = router.process_query(query)
    return {
        "response": result.response,
        "mode": result.mode.value,
        "latency_ms": result.latency_ms,
    }
```

### 8.3 集成到可观测性

```python
from observability import TraceCollector
from hybrid_computing import HybridRouter

collector = TraceCollector()
router = HybridRouter()

# 记录路由决策
collector.record_tool_call(
    tool_name="hybrid_router",
    input_params={"query": query},
    output_result=result.response,
    metadata={
        "mode": result.mode.value,
        "latency_ms": result.latency_ms,
        "intent_type": result.intent_type.value,
    },
)
```
