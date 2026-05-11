# MultiAgentDeepResearch

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Chainlit](https://img.shields.io/badge/Chainlit-1.0%2B-orange.svg)](https://docs.chainlit.io/)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.165%2B-purple.svg)](https://docs.crewai.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**MultiAgentDeepResearch** 是一个基于多智能体协作的深度研究系统。用户只需输入研究主题，系统即可自动制定研究计划、调度各专业Agent执行信息采集、多维度分析、交叉验证，最终输出结构化的专业研究报告。

---

## ✨ 核心功能

- 📝 **智能计划制定**：主编Agent自动生成结构化研究计划
- 🔍 **自动化信息采集**：支持实时网络搜索和网页内容抓取
- 📊 **多维度分析能力**：覆盖商业、技术、竞品等维度，支持交叉验证
- 🤖 **多Agent协作**：4个核心Agent协同工作（主编、采集、分析、撰写）
- 💬 **交互式Web界面**：友好的对话式用户体验，支持计划确认
- 📄 **结构化报告输出**：支持Markdown格式导出
- 🔄 **异步任务管理**：支持异步任务执行和状态追踪
- 📚 **历史记录管理**：查看过往分析任务和报告

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│                    Chainlit (Web UI)                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      API服务层                               │
│                  FastAPI + Uvicorn                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    多智能体引擎层                            │
│              CrewAI 多智能体编排引擎                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 主编规划 │→│ 情报采集 │→│ 商业分析 │→│ 报告生成 │   │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       工具层                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Tavily API  │  │ Web Loader  │  │ DuckDuckGo Search   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端 | Chainlit | >=1.0.8 | 对话式Web界面 |
| API框架 | FastAPI | >=0.135.0 | RESTful API服务 |
| 服务器 | Uvicorn | >=0.29.0 | ASGI服务器 |
| 多智能体框架 | CrewAI | >=0.165.1 | Agent编排与协作 |
| LLM集成 | LangChain | >=0.3.0 | LLM工具链 |
| 数据库 | SQLAlchemy | >=2.0.29 | ORM与数据持久化 |
| 搜索工具 | Tavily API | >=0.7.0 | 网络搜索 |
| 网页抓取 | BeautifulSoup4 | >=4.12.3 | 网页内容提取 |
| 测试框架 | Pytest | >=8.1.0 | 单元测试与集成测试 |

---

## 📋 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows / macOS / Linux
- **内存**: 至少 4GB RAM
- **网络**: 需要访问外部API（LLM、搜索服务）

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/MultiAgentDeepResearch.git
cd MultiAgentDeepResearch
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

# 编辑 .env 文件，配置必要的API密钥
```

**.env 文件配置示例**：

```env
# OpenAI API配置（必需）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 搜索API配置（可选）
TAVILY_API_KEY=your_tavily_api_key_here

# 数据库配置（可选，默认使用SQLite）
DATABASE_URL=sqlite:///./research.db
```

### 5. 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
# Windows
start.bat all

# 或使用Python脚本
python start_services.py all
```

#### 方式二：手动启动

```bash
# 启动API服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端服务（新终端）
chainlit run frontend/app.py --watch --port 8001 --host 0.0.0.0
```

#### 方式三：使用Docker

```bash
docker-compose up -d
```

### 6. 访问应用

- **前端界面**: http://localhost:8001
- **API文档**: http://localhost:8000/api/docs
- **健康检查**: http://localhost:8000/health

---

## 📖 使用指南

### 基本使用流程

1. **输入研究主题**：在对话界面输入您想要研究的主题
2. **查看研究计划**：系统自动生成结构化的研究计划
3. **确认或修改计划**：
   - 点击"确认执行"开始研究
   - 点击"修改计划"提出调整意见
   - 点击"取消研究"放弃当前任务
4. **等待执行完成**：系统按计划调度各Agent执行
5. **查看和下载报告**：在线预览或下载Markdown格式报告

### CLI模式

```bash
# 交互式CLI模式
python main_cli.py -i

# 直接运行研究
python main_cli.py -t "人工智能在医疗领域的应用"
```

### API使用示例

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

## 📁 项目结构

```
MultiAgentDeepResearch/
├── agents/                     # Agent实现
│   ├── business_agent.py      # 商业分析Agent
│   ├── editor_agent.py        # 主编规划Agent
│   ├── research_agent.py      # 情报采集Agent
│   └── writer_agent.py        # 报告生成Agent
├── app/                       # 后端服务
│   ├── main.py               # FastAPI应用入口
│   ├── models/               # 数据库模型
│   ├── routers/              # API路由
│   ├── services/             # 业务服务
│   ├── middleware/           # 中间件
│   └── utils/                # 工具函数
├── frontend/                  # 前端界面
│   ├── app.py                # Chainlit主应用
│   ├── components.py         # 通用组件
│   ├── display.py            # 报告展示
│   ├── plan_confirmation.py  # 计划确认交互
│   └── plan_display.py       # 计划展示
├── services/                  # 辅助服务
├── tasks/                     # 任务定义
├── tools/                     # 工具集成
├── tests/                     # 测试文件
├── docs/                      # 文档
├── crew.py                    # CrewAI编排
├── config.py                  # 配置管理
├── main_cli.py               # CLI入口
├── requirements.txt          # 依赖列表
├── Dockerfile                # Docker配置
├── docker-compose.yml        # Docker编排
└── start_services.py         # 服务启动脚本
```

---

## 📚 API文档

完整的API文档请参考：

- **在线文档**: 启动服务后访问 http://localhost:8000/api/docs
- **文档文件**: [docs/API.md](docs/API.md)

### 核心API端点

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
# API测试
pytest tests/test_api.py -v

# 前端测试
pytest tests/test_frontend.py -v

# Crew测试
pytest tests/test_crew.py -v
```

### 生成测试覆盖率报告

```bash
pytest tests/ --cov=. --cov-report=html
```

---

## 🐳 Docker部署

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
```

---

## 🤝 贡献规范

我们欢迎所有形式的贡献！请遵循以下步骤：

### 1. Fork项目

在GitHub上Fork本项目到您的账户。

### 2. 创建特性分支

```bash
git checkout -b feature/your-feature-name
```

### 3. 代码规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) Python编码规范
- 使用类型注解提高代码可读性
- 所有函数和类必须包含docstring
- 关键逻辑添加注释说明
- 保持代码简洁，避免冗余

### 4. 测试要求

- 为新功能编写单元测试
- 确保所有测试通过：`pytest tests/ -v`
- 测试覆盖率不低于80%

### 5. 提交规范

提交信息格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Type类型**：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

**示例**：
```
feat(api): 添加任务取消功能

- 实现任务取消API端点
- 添加任务状态管理逻辑
- 编写相关单元测试

Closes #123
```

### 6. 提交Pull Request

- 在PR描述中清晰说明改动内容
- 关联相关的Issue
- 等待代码审查并合并

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 👥 作者与维护者

- **项目创建者**: MultiAgentDeepResearch Team
- **主要维护者**: 社区贡献者

---

## 🙏 致谢

感谢以下开源项目：

- [CrewAI](https://github.com/crewAIInc/crewAI) - 多智能体编排框架
- [Chainlit](https://github.com/Chainlit/chainlit) - 对话式Web界面框架
- [FastAPI](https://github.com/tiangolo/fastapi) - 高性能API框架
- [LangChain](https://github.com/langchain-ai/langchain) - LLM应用开发框架

---

## 📞 联系方式

- **Issue反馈**: [GitHub Issues](https://github.com/LeeKinyou/multi-agent-deep-research/issues)
- **讨论区**: [GitHub Discussions](https://github.com/LeeKinyou/multi-agent-deep-research/discussions)

---

**⭐ 如果这个项目对您有帮助，请给个Star！**
