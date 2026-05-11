# 前端界面开发文档

## 概述

MultiAgentDeepResearch 前端界面基于 Chainlit 框架构建，提供对话式Web交互体验。

## 目录结构

```
frontend/
├── __init__.py
├── app.py                    # Chainlit主应用
├── plan_display.py           # 计划展示组件
├── plan_confirmation.py      # 计划确认交互
├── components.py             # 通用组件和消息流
└── display.py                # 报告展示组件
```

## 技术栈

- **Chainlit**: 对话式Web界面框架
- **Requests**: HTTP客户端，与后端API通信
- **Markdown**: 内容渲染和展示

## 功能模块

### 1. 主应用 (app.py)

**功能**:
- 会话管理
- 用户消息处理
- 研究任务创建
- 计划生成与展示
- 任务执行控制

**核心函数**:
- `on_chat_start()`: 会话初始化
- `on_message()`: 处理用户输入
- `create_new_research_task()`: 创建研究任务
- `generate_and_display_plan()`: 生成并展示计划
- `execute_research()`: 执行研究任务

### 2. 计划展示组件 (plan_display.py)

**功能**:
- 结构化展示研究计划
- 任务详情展示
- 计划摘要生成
- 计划完整性验证

**核心函数**:
- `render_plan()`: 渲染计划界面
- `format_plan_summary()`: 生成计划摘要
- `validate_plan()`: 验证计划完整性

### 3. 计划确认交互 (plan_confirmation.py)

**功能**:
- 计划确认/修改/取消操作
- 按钮交互处理
- 计划修改处理
- 计划重新生成

**核心函数**:
- `handle_plan_confirmation()`: 处理计划确认
- `on_confirm()`: 确认计划回调
- `on_modify()`: 修改计划回调
- `on_cancel()`: 取消计划回调
- `execute_confirmed_plan()`: 执行已确认计划

### 4. 通用组件 (components.py)

**功能**:
- 欢迎消息展示
- 进度条组件
- 任务状态显示
- Agent消息展示
- 错误信息展示
- 执行日志展示

**核心函数**:
- `show_welcome_message()`: 显示欢迎消息
- `create_progress_bar()`: 创建进度条
- `update_progress()`: 更新进度
- `show_task_status()`: 显示任务状态
- `show_agent_message()`: 显示Agent消息
- `show_error()`: 显示错误信息

### 5. 报告展示组件 (display.py)

**功能**:
- Markdown报告渲染
- 报告下载功能
- 报告预览
- 报告摘要提取

**核心函数**:
- `render_report()`: 渲染完整报告
- `render_report_from_api()`: 从API获取并渲染报告
- `show_report_preview()`: 显示报告预览
- `extract_report_summary()`: 提取报告摘要
- `show_report_summary()`: 显示报告摘要

## 用户交互流程

```
用户输入研究主题
    ↓
创建研究任务 (API)
    ↓
生成研究计划
    ↓
展示计划详情
    ↓
用户确认/修改/取消
    ↓
[确认] 执行研究任务
    ↓
展示执行进度
    ↓
生成研究报告
    ↓
展示报告 + 下载选项
```

## API集成

前端通过HTTP请求与后端API通信：

```python
API_BASE_URL = "http://localhost:8000"

# 创建任务
POST /api/v1/tasks/

# 确认计划
POST /api/v1/tasks/{task_id}/plan/confirm

# 取消任务
POST /api/v1/tasks/{task_id}/cancel

# 获取结果
GET /api/v1/tasks/{task_id}/result

# 获取任务列表
GET /api/v1/tasks/
```

## 启动方式

```bash
# 启动前端服务
chainlit run frontend/app.py --watch --port 8001

# 访问界面
# http://localhost:8001
```

## 测试

运行前端测试：

```bash
pytest tests/test_frontend.py -v
```

测试覆盖：
- 计划展示组件测试 (6个测试)
- 报告展示组件测试 (2个测试)
- 通用组件测试 (4个测试)
- 计划确认数据结构测试 (1个测试)

## 开发规范

遵循项目文档中的前端开发规范：

1. **代码规范**:
   - 遵循PEP 8 Python编码规范
   - 使用类型注解提高代码可读性
   - 函数和类必须包含docstring
   - 关键逻辑添加注释说明

2. **组件设计**:
   - 单一职责原则
   - 组件可复用
   - 清晰的接口定义

3. **错误处理**:
   - 友好的错误提示
   - 异常捕获和日志记录
   - 优雅降级

## 响应式设计

Chainlit框架自动适配不同屏幕尺寸：
- 桌面端：完整功能展示
- 平板端：优化布局
- 移动端：简化展示

## 性能优化

1. **懒加载**: 按需加载组件
2. **缓存**: 避免重复API请求
3. **异步处理**: 使用async/await提高响应速度
4. **进度反馈**: 实时显示操作进度

## 浏览器兼容性

支持主流现代浏览器：
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 后续优化建议

1. **国际化**: 支持多语言切换
2. **主题定制**: 支持亮色/暗色主题
3. **历史记录**: 增强历史记录查看功能
4. **实时通知**: WebSocket实时推送
5. **数据分析**: 用户行为分析

---

**最后更新**: 2026-05-11  
**版本**: v1.0.0
