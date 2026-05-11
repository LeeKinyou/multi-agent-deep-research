# MultiAgentDeepResearch 项目启动指南

## 目录
1. [解决模块导入错误](#1-解决模块导入错误)
2. [环境配置要求](#2-环境配置要求)
3. [服务启动命令](#3-服务启动命令)
4. [服务启动顺序和依赖关系](#4-服务启动顺序和依赖关系)
5. [一键启动所有服务](#5-一键启动所有服务)
6. [验证服务启动](#6-验证服务启动)

---

## 1. 解决模块导入错误

### 问题原因
执行 `python ./app/main.py` 时出现 `ModuleNotFoundError: No module named 'app'` 错误，原因是：
- `main.py` 中使用了 `from app.models.database import init_db` 绝对导入
- 直接运行脚本时，Python 将 `app/` 目录作为脚本执行，而不是作为包
- `app` 包不在 `sys.path` 中

### 解决方案

**方法一：使用 uvicorn 模块运行（推荐）**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**方法二：使用启动脚本**
```bash
# Windows
start.bat api

# Linux/Mac
python start_services.py api
```

**方法三：修改 PYTHONPATH**
```bash
# Windows (PowerShell)
$env:PYTHONPATH="."; python ./app/main.py

# Linux/Mac
PYTHONPATH=. python ./app/main.py
```

---

## 2. 环境配置要求

### 2.1 系统要求
- **Python**: 3.10 或更高版本
- **操作系统**: Windows 10+/macOS/Linux
- **内存**: 至少 4GB RAM
- **磁盘空间**: 至少 1GB 可用空间

### 2.2 安装步骤

```bash
# 1. 克隆项目（如果还没有）
cd MultiAgentDeepResearch

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# 6. 编辑 .env 文件，填入 API 密钥
notepad .env  # Windows
nano .env     # Linux/Mac
```

### 2.3 .env 文件配置

```env
# LLM 配置
LLM_API_KEY=your_deepseek_api_key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_PROVIDER=deepseek
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# 搜索配置
TAVILY_API_KEY=your_tavily_api_key
SEARCH_TOOL=duckduckgo
SEARCH_MAX_RESULTS=5
SEARCH_DEPTH=basic

# 应用配置
APP_PORT=8000
DATABASE_URL=sqlite:///./data/tasks.db
DEBUG=false
LOG_LEVEL=INFO

# 上下文配置
CONTEXT_MAX_TOKENS=8000
CONTEXT_WARNING_THRESHOLD=0.75
CONTEXT_CRITICAL_THRESHOLD=0.9
```

---

## 3. 服务启动命令

### 3.1 API 服务（FastAPI）

```bash
# 开发模式（自动重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**访问地址**:
- API 根路径: http://localhost:8000
- Swagger 文档: http://localhost:8000/api/docs
- ReDoc 文档: http://localhost:8000/api/redoc

### 3.2 Chainlit 前端

```bash
chainlit run frontend/app.py --watch --port 8001
```

**访问地址**: http://localhost:8001

### 3.3 交互式 CLI

```bash
python main_cli.py -i
```

### 3.4 单次研究任务

```bash
python main_cli.py "人工智能发展趋势" --depth standard
```

---

## 4. 服务启动顺序和依赖关系

### 4.1 服务依赖图

```
┌─────────────────┐
│   外部 API 服务   │
│  (LLM, Search)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐     ┌─────────────────┐
│   API 服务       │────→│   数据库         │
│  (FastAPI)      │     │  (SQLite)       │
└────────┬────────┘     └─────────────────┘
         │
         ↓
┌─────────────────┐
│   Chainlit 前端  │
│   (Web UI)      │
└─────────────────┘
```

### 4.2 启动顺序

| 顺序 | 服务 | 说明 | 依赖 |
|------|------|------|------|
| 1 | 环境准备 | 激活虚拟环境，检查依赖 | 无 |
| 2 | API 服务 | FastAPI 后端服务 | 环境变量配置 |
| 3 | Chainlit 前端 | Web 用户界面 | API 服务运行中 |

### 4.3 Agent 服务说明

Agent 不是独立服务，而是作为 API 服务的一部分运行：
- 当 API 接收到任务执行请求时，会动态创建和运行 Agent
- Agent 运行在 API 服务的进程内，不需要单独启动
- Agent 依赖外部 LLM API 和搜索 API

---

## 5. 一键启动所有服务

### 5.1 使用启动脚本（推荐）

**Windows**:
```bash
# 仅启动 API 服务
start.bat api

# 启动 API + 前端
start.bat all

# 启动交互式 CLI
start.bat cli
```

**Linux/Mac**:
```bash
# 仅启动 API 服务
python start_services.py api

# 启动 API + 前端
python start_services.py all

# 启动交互式 CLI
python start_services.py cli
```

### 5.2 使用 Docker Compose

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 5.3 使用 Python 启动器

```bash
python start_services.py api   # 仅 API
python start_services.py all   # API + 前端
python start_services.py cli   # CLI
```

---

## 6. 验证服务启动

### 6.1 验证 API 服务

**方法一：浏览器访问**
打开 http://localhost:8000/api/docs，应该能看到 Swagger UI 界面

**方法二：curl 命令**
```bash
# 健康检查
curl http://localhost:8000/api/v1/health/

# 预期响应
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-05-11T12:00:00",
  "database": "connected"
}
```

**方法三：Python 脚本**
```python
import requests
response = requests.get("http://localhost:8000/api/v1/health/")
print(response.status_code)  # 应该是 200
print(response.json())
```

### 6.2 验证 Chainlit 前端

打开 http://localhost:8001，应该能看到对话式 Web 界面

### 6.3 验证 CLI

```bash
python main_cli.py -i
```

应该能看到交互式命令行界面

### 6.4 完整功能测试

```python
import requests

# 1. 创建任务
response = requests.post(
    "http://localhost:8000/api/v1/tasks/",
    json={"topic": "测试主题", "depth": "standard"}
)
print(f"创建任务: {response.status_code}")
task_id = response.json()["task_id"]

# 2. 查询任务
response = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
print(f"查询任务: {response.status_code}")

# 3. 创建计划
response = requests.post(
    f"http://localhost:8000/api/v1/tasks/{task_id}/plan/",
    json={
        "task_id": task_id,
        "plan_content": {"tasks": []},
        "version": 1
    }
)
print(f"创建计划: {response.status_code}")

# 4. 确认计划
response = requests.post(
    f"http://localhost:8000/api/v1/tasks/{task_id}/plan/confirm",
    json={"confirmed": True}
)
print(f"确认计划: {response.status_code}")

print("\n所有测试通过！")
```

---

## 7. 常见问题

### Q1: 端口被占用

**错误**: `Address already in use`

**解决**:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Q2: 虚拟环境未激活

**错误**: `ModuleNotFoundError`

**解决**:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Q3: 依赖包缺失

**错误**: `No module named 'xxx'`

**解决**:
```bash
pip install -r requirements.txt
```

### Q4: API 密钥未配置

**错误**: `LLM API 密钥未配置`

**解决**:
1. 复制 `.env.example` 为 `.env`
2. 编辑 `.env` 填入 API 密钥

---

## 8. 开发工作流

```bash
# 1. 激活虚拟环境
venv\Scripts\activate  # Windows

# 2. 启动 API 服务（开发模式）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 打开浏览器访问 API 文档
# http://localhost:8000/api/docs

# 4. 使用 Postman/curl 测试 API

# 5. 运行测试
pytest tests/ -v

# 6. 停止服务
# 按 Ctrl+C
```

---

## 9. 生产部署

### 使用 Docker Compose

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入生产环境配置

# 2. 构建并启动
docker-compose up -d

# 3. 验证服务
curl http://localhost:8000/api/v1/health/

# 4. 查看日志
docker-compose logs -f api
```

### 使用云服务器

1. 安装 Docker 和 Docker Compose
2. 克隆项目代码
3. 配置环境变量
4. 运行 `docker-compose up -d`
5. 配置域名和 HTTPS（使用 Nginx 反向代理）

---

## 10. 监控和维护

### 查看服务状态

```bash
# API 服务健康检查
curl http://localhost:8000/api/v1/health/

# 查看任务列表
curl http://localhost:8000/api/v1/tasks/

# 查看日志
tail -f logs/api.log  # 如果配置了日志文件
```

### 重启服务

```bash
# Docker Compose
docker-compose restart

# 手动重启
# 按 Ctrl+C 停止，然后重新启动
```

### 数据库备份

```bash
# 备份 SQLite 数据库
cp data/tasks.db data/tasks.db.backup.$(date +%Y%m%d)
```

---

**最后更新**: 2026-05-11  
**版本**: v1.0.0
