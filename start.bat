@echo off
REM MultiAgentDeepResearch - Windows 服务启动脚本
REM 使用方法: start.bat [api|all|cli]

echo ============================================================
echo   MultiAgentDeepResearch - 服务启动器
echo ============================================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [信息] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用全局 Python
)

REM 检查依赖
echo [信息] 检查依赖...
python -c "import fastapi, uvicorn, sqlalchemy, pydantic" 2>nul
if errorlevel 1 (
    echo [警告] 缺少依赖包，正在安装...
    pip install -r requirements.txt
) else (
    echo [成功] 依赖检查通过
)

echo.

REM 解析参数
set MODE=%1
if "%MODE%"=="" set MODE=api

REM 启动服务
if "%MODE%"=="api" (
    echo [启动] API 服务器...
    echo [访问] http://localhost:8000
    echo [文档] http://localhost:8000/api/docs
    echo.
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) else if "%MODE%"=="all" (
    echo [启动] API 服务器 + Chainlit 前端...
    echo.
    start "API Server" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    timeout /t 3 /nobreak >nul
    start "Chainlit Frontend" cmd /k "chainlit run frontend/app.py --watch"
    echo [成功] 服务已启动
    echo   API 服务器: http://localhost:8000
    echo   Chainlit 前端: http://localhost:8001
    echo.
    echo 按任意键关闭此窗口（服务在后台运行）
    pause >nul
) else if "%MODE%"=="cli" (
    echo [启动] 交互式 CLI...
    echo.
    python main_cli.py -i
) else (
    echo [错误] 未知模式: %MODE%
    echo 可用模式: api, all, cli
    exit /b 1
)
