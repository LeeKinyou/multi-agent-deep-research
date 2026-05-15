# MultiAgent Deep Research

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Chainlit](https://img.shields.io/badge/Chainlit-1.0%2B-orange.svg)](https://docs.chainlit.io/)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.165%2B-purple.svg)](https://docs.crewai.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**MultiAgent Deep Research** 是一个基于多智能体协作的深度研究系统。用户只需输入研究主题，系统即可自动制定研究计划、调度各专业 Agent 执行信息采集、多维度分析、交叉验证，最终输出结构化的专业研究报告。系统内置企业级链路可观测性与 LLM-as-a-Judge 评测体系，支持全流程可视化监控和自动化质量评估。

---

## ✨ 核心功能

### 多智能体协作
- 📝 **智能计划制定**：主编 Agent 自动生成结构化研究计划
- 🔍 **自动化信息采集**：支持实时网络搜索和网页内容抓取，RAG 工具支持信息持久化存储
- 📊 **多维度分析能力**：覆盖商业、技术、竞品等维度，支持交叉验证
- 🤖 **4 个核心 Agent 协同**：主编规划、情报采集、商业分析、报告生成

### 企业级可观测性
- 🔗 **Langfuse 链路追踪**：Agent 执行全流程可视化监控
- ⏱️ **Trace 数据采集**：Tool Call 耗时（毫秒级）、Token 消耗统计、Prompt 演变记录、决策节点追踪
- 📈 **异常检测与告警**：超时检测、Token 消耗异常、工具调用失败自动告警
- 📊 **可视化仪表盘**：实时指标、历史趋势分析、数据导出（JSON/CSV/Markdown）

### 自动化评测体系
- 🎯 **LLM-as-a-Judge**：多维度自动化评分（信源一致性、逻辑严密性、准确性、完整性、引用质量）
- 📋 **详细评分报告**：分数、扣分点、改进建议
- � **历史数据对比**：支持趋势分析和质量追踪

### 用户体验
- �💬 **交互式 Web 界面**：Chainlit 驱动的对话式用户体验，支持计划确认
- 📄 **结构化报告输出**：支持 Markdown 格式导出
- 🔄 **异步任务管理**：支持异步任务执行和状态追踪
- 📚 **历史记录管理**：查看过往分析任务和报告

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端层                                  │
│                      Chainlit (Web UI)                          │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                        API 服务层                                │
│                    FastAPI + Uvicorn                            │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      多智能体引擎层                              │
│                CrewAI 多智能体编排引擎                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 主编规划 │→│ 情报采集 │→│ 商业分析 │→│ 报告生成 │       │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌──────────────────────────┬──────────────────────────────────────┐
│         工具层           │          可观测性层                   │
│  ┌─────────────┐        │  ┌──────────────────────────────┐   │
│  │ Tavily API  │        │  │ Langfuse 链路追踪             │   │
│  └─────────────┘        │  ├──────────────────────────────┤   │
│  ┌─────────────┐        │  │ Trace 数据采集器              │   │
│  │ Web Loader  │        │  ├──────────────────────────────┤   │
│  └─────────────┘        │  │ LLM-as-a-Judge 评测器        │   │
│  ┌─────────────┐        │  ├──────────────────────────────┤   │
│  │ RAG Tools   │        │  │ 异常检测与告警服务            │   │
│  └─────────────┘        │  ├──────────────────────────────┤   │
│  ┌─────────────┐        │  │ 可视化仪表盘 & 数据导出       │   │
│  │ Vector DB   │        │  └──────────────────────────────┘   │
│  └─────────────┘        │                                      │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端 | Chainlit | 对话式 Web 界面 |
| API 框架 | FastAPI | RESTful API 服务 |
| 服务器 | Uvicorn | ASGI 服务器 |
| 多智能体框架 | CrewAI | Agent 编排与协作 |
| LLM 集成 | LangChain | LLM 工具链 |
| 数据库 | SQLAlchemy | ORM 与数据持久化 |
| 搜索工具 | Tavily API | 网络搜索 |
| 网页抓取 | BeautifulSoup4 | 网页内容提取 |
| 链路追踪 | Langfuse | 可观测性平台 |
| 测试框架 | Pytest | 单元测试与集成测试 |

---

## 📋 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows / macOS / Linux
- **内存**: 至少 4GB RAM
- **网络**: 需要访问外部 API（LLM、搜索服务）

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/LeeKinyou/multi-agent-deep-research.git
cd multi-agent-deep-research
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，配置必要的 API 密钥
```

**.env 文件配置示例**：

```env
# OpenAI API 配置（必需）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 搜索 API 配置（可选）
TAVILY_API_KEY=your_tavily_api_key_here

# Langfuse 可观测性配置（可选）
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com

# 数据库配置（可选，默认使用 SQLite）
DATABASE_URL=sqlite:///./research.db
```

### 5. 启动服务

```bash
# Windows
scripts\start.bat all

# 或使用 Python 脚本
python cli/start_services.py all
```

### 6. 访问应用

- **前端界面**: http://localhost:8001
- **API 文档**: http://localhost:8000/api/docs
- **健康检查**: http://localhost:8000/health

---

## 📖 使用指南

### 基本使用流程

1. **输入研究主题**：在对话界面输入您想要研究的主题
2. **查看研究计划**：系统自动生成结构化的研究计划
3. **确认或修改计划**：
   - 点击「确认执行」开始研究
   - 点击「修改计划」提出调整意见
   - 点击「取消研究」放弃当前任务
4. **等待执行完成**：系统按计划调度各 Agent 执行
5. **查看和下载报告**：在线预览或下载 Markdown 格式报告

### CLI 模式

```bash
# 交互式 CLI 模式
python cli/main_cli.py -i

# 直接运行研究
python cli/main_cli.py -t "人工智能在医疗领域的应用"
```

### API 使用示例

```bash
# 创建研究任务
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"topic": "新能源汽车市场发展趋势", "depth": "standard"}'

# 查询任务状态
curl http://localhost:8000/api/v1/tasks/{task_id}

# 确认研究计划
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/plan/confirm \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'

# 获取研究结果
curl http://localhost:8000/api/v1/tasks/{task_id}/result
```

---

## 🔍 可观测性使用

### 启用链路追踪

在 `.env` 中配置 Langfuse 密钥后，系统自动启用链路追踪：

```python
from observability import TraceCollector, get_langfuse_client

# 初始化
client = get_langfuse_client()
collector = TraceCollector()
collector.initialize(client)

# 开始追踪
trace_id = collector.start_trace(
    name="research_task",
    task_id="task_123",
    agent_type="ResearchAgent"
)

# 记录工具调用
collector.record_tool_call(
    tool_name="tavily_search",
    input_params={"query": "AI market trends"},
    output_result={"results": [...]},
    duration_ms=1250
)

# 记录 Token 消耗
collector.record_token_usage(
    model="gpt-4",
    input_tokens=1500,
    output_tokens=800
)

# 结束追踪
collector.end_trace(trace_id, status="completed")
```

### 使用 LLM-as-a-Judge 评测

```python
from observability import LLMJudgeEvaluator

evaluator = LLMJudgeEvaluator()

result = evaluator.evaluate(
    report_content="...",       # 研究报告内容
    source_data="...",          # 原始数据源
    task_id="task_123"
)

print(f"综合得分: {result.overall_score:.2f}/10")
for dim in result.dimensions:
    print(f"  {dim.dimension}: {dim.score}/10")
```

### 查看告警

```python
from observability import AlertService

alerts = AlertService()
# 检查指标
alerts.check_metric("tool_call_duration_ms", 35000)
# 查看历史
history = alerts.get_history()
```

### 数据导出

```python
from observability import DashboardService

dashboard = DashboardService()

# 导出 JSON
json_data = dashboard.export_to_json(hours=24)

# 导出 CSV
csv_data = dashboard.export_to_csv(hours=24)

# 生成报告
report = dashboard.generate_report(hours=24, format="markdown")
```

---

## 📁 项目结构

```
MultiAgentDeepResearch/
├── agents/                     # Agent 实现
│   ├── business_agent.py       # 商业分析 Agent
│   ├── editor_agent.py         # 主编规划 Agent
│   ├── research_agent.py       # 情报采集 Agent
│   └── writer_agent.py         # 报告生成 Agent
├── app/                        # 后端服务
│   ├── main.py                 # FastAPI 应用入口
│   ├── models/                 # 数据库模型
│   ├── routers/                # API 路由
│   ├── services/               # 业务服务
│   ├── middleware/             # 中间件
│   └── utils/                  # 工具函数
├── cli/                        # 命令行工具
│   ├── main_cli.py             # CLI 入口
│   └── start_services.py       # 服务启动脚本
├── config/                     # 配置管理
├── core/                       # 核心编排
│   └── crew.py                 # CrewAI 编排逻辑
├── frontend/                   # 前端界面
│   ├── app.py                  # Chainlit 主应用
│   ├── components.py           # 通用组件
│   ├── display.py              # 报告展示
│   ├── plan_confirmation.py    # 计划确认交互
│   └── plan_display.py         # 计划展示
├── models/                     # 数据模型
│   └── structured_output.py    # 结构化输出模型
├── observability/              # 可观测性模块
│   ├── docs/                   # 可观测性文档
│   │   ├── ARCHITECTURE.md     # 架构设计
│   │   ├── API_REFERENCE.md    # API 参考
│   │   ├── DEPLOYMENT.md       # 部署指南
│   │   └── USAGE_GUIDE.md      # 使用手册
│   ├── __init__.py             # 模块入口
│   ├── alert_service.py        # 异常检测与告警
│   ├── dashboard.py            # 可视化仪表盘
│   ├── evaluator.py            # LLM-as-a-Judge 评测器
│   ├── langfuse_client.py      # Langfuse 客户端
│   └── trace_collector.py      # Trace 数据采集器
├── services/                   # 辅助服务
│   ├── context_manager.py      # 上下文管理
│   ├── data_cleaner.py         # 数据清洗
│   ├── document_chunker.py     # 文档分块
│   ├── planning_service.py     # 规划服务
│   └── vector_store.py         # 向量存储
├── tasks/                      # 任务定义
│   ├── analysis_task.py        # 分析任务
│   ├── planning_task.py        # 规划任务
│   ├── research_task.py        # 研究任务
│   └── writing_task.py         # 写作任务
├── tools/                      # 工具集成
│   ├── rag_tools.py            # RAG 工具
│   └── search_tool.py          # 搜索工具
├── tests/                      # 测试文件
├── docs/                       # 项目文档
├── scripts/                    # 脚本
├── requirements.txt            # 依赖列表
├── Dockerfile                  # Docker 配置
└── docker-compose.yml          # Docker 编排
```

---

## 📚 API 文档

完整的 API 文档请参考：

- **在线文档**: 启动服务后访问 http://localhost:8000/api/docs
- **文档文件**: [docs/API.md](docs/API.md)

### 核心 API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/tasks/` | 创建研究任务 |
| GET | `/api/v1/tasks/` | 获取任务列表 |
| GET | `/api/v1/tasks/{task_id}` | 获取任务详情 |
| POST | `/api/v1/tasks/{task_id}/plan/confirm` | 确认研究计划 |
| GET | `/api/v1/tasks/{task_id}/result` | 获取研究结果 |
| POST | `/api/v1/tasks/{task_id}/cancel` | 取消任务 |

---

## 🧪 测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试

```bash
# API 测试
pytest tests/test_api.py -v

# 可观测性测试
pytest tests/test_observability.py -v

# Crew 测试
pytest tests/test_crew.py -v
```

### 生成测试覆盖率报告

```bash
pytest tests/ --cov=. --cov-report=html
```

---

## 🐳 Docker 部署

### 构建镜像

```bash
docker build -t multiagent-deep-research .
```

### 运行容器

```bash
docker-compose up -d
```

### 环境变量配置

在 `docker-compose.yml` 中配置环境变量：

```yaml
environment:
  - OPENAI_API_KEY=your_key_here
  - TAVILY_API_KEY=your_tavily_key_here
  - LANGFUSE_PUBLIC_KEY=pk-...
  - LANGFUSE_SECRET_KEY=sk-...
```

---

## 🤝 贡献规范

我们欢迎所有形式的贡献！请遵循以下步骤：

### 1. Fork 项目

在 GitHub 上 Fork 本项目到您的账户。

### 2. 创建特性分支

```bash
git checkout -b feature/your-feature-name
```

### 3. 代码规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) Python 编码规范
- 使用类型注解提高代码可读性
- 所有函数和类必须包含 docstring
- 关键逻辑添加注释说明
- 保持代码简洁，避免冗余

### 4. 测试要求

- 为新功能编写单元测试
- 确保所有测试通过：`pytest tests/ -v`
- 测试覆盖率不低于 80%

### 5. 提交规范

提交信息格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Type 类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

**示例**：
```
feat(api): 添加任务取消功能

- 实现任务取消 API 端点
- 添加任务状态管理逻辑
- 编写相关单元测试

Closes #123
```

### 6. 提交 Pull Request

- 在 PR 描述中清晰说明改动内容
- 关联相关的 Issue
- 等待代码审查并合并

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 👥 作者与维护者

- **项目创建者**: MultiAgent Deep Research Team
- **主要维护者**: 社区贡献者

---

## 🙏 致谢

感谢以下开源项目：

- [CrewAI](https://github.com/crewAIInc/crewAI) - 多智能体编排框架
- [Chainlit](https://github.com/Chainlit/chainlit) - 对话式 Web 界面框架
- [FastAPI](https://github.com/tiangolo/fastapi) - 高性能 API 框架
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用开发框架
- [Langfuse](https://github.com/langfuse/langfuse) - LLM 可观测性平台

---

## 📞 联系方式

- **Issue 反馈**: [GitHub Issues](https://github.com/LeeKinyou/multi-agent-deep-research/issues)
- **讨论区**: [GitHub Discussions](https://github.com/LeeKinyou/multi-agent-deep-research/discussions)

---

**⭐ 如果这个项目对您有帮助，请给个 Star！**
