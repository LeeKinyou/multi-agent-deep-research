"""
前端通用组件和消息流展示

提供欢迎消息、进度条、状态显示等通用UI组件
"""

import chainlit as cl
from typing import Optional, Dict, Any


async def show_welcome_message():
    """显示欢迎消息"""
    welcome_md = """# 🎯 MultiAgentDeepResearch

欢迎使用多智能体深度研究系统！

## 系统功能

- 📝 **智能规划**: 主编Agent自动制定研究计划
- 🔍 **信息采集**: 情报采集Agent实时搜索网络信息
- 📊 **多维度分析**: 商业分析Agent进行SWOT、竞品分析
- 📄 **报告生成**: 自动生成结构化研究报告

## 使用方式

1. 输入您的研究主题
2. 系统自动生成研究计划
3. 确认计划后开始执行
4. 查看分析报告

## 示例主题

- 人工智能在医疗领域的应用
- 新能源汽车市场发展趋势
- 云计算行业竞争格局分析

---

**请输入您的研究主题开始研究** 🚀
"""
    
    actions = [
        cl.Action(
            name="view_history",
            value="history",
            label="📚 查看历史记录",
            payload={"action": "history"},
        ),
    ]
    
    await cl.Message(content=welcome_md, actions=actions).send()


async def create_progress_bar(initial_text: str = "处理中..."):
    """
    创建进度条
    
    Args:
        initial_text: 初始显示文本
        
    Returns:
        进度条消息对象
    """
    progress = cl.Message(content=initial_text)
    await progress.send()
    return progress


async def update_progress(progress: cl.Message, percent: int, text: str):
    """
    更新进度条
    
    Args:
        progress: 进度条消息对象
        percent: 进度百分比 (0-100)
        text: 显示文本
    """
    progress_bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    progress.content = f"{text}\n\n`{progress_bar}` {percent}%"
    await progress.update()


async def show_task_status(status: str, details: Optional[str] = None):
    """
    显示任务状态
    
    Args:
        status: 状态文本
        details: 详细信息
    """
    status_emojis = {
        "planning": "📝",
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "⛔",
    }
    
    emoji = status_emojis.get(status, "❓")
    content = f"{emoji} **任务状态**: {status}"
    
    if details:
        content += f"\n\n{details}"
    
    await cl.Message(content=content).send()


async def show_agent_message(agent_name: str, message: str, icon: str = "🤖"):
    """
    显示Agent消息
    
    Args:
        agent_name: Agent名称
        message: 消息内容
        icon: 图标
    """
    content = f"{icon} **{agent_name}**: {message}"
    await cl.Message(content=content).send()


async def show_step_completion(step_name: str, result: str):
    """
    显示步骤完成信息
    
    Args:
        step_name: 步骤名称
        result: 结果描述
    """
    content = f"✅ **{step_name}** 已完成\n\n{result}"
    await cl.Message(content=content).send()


async def show_error(error_message: str, suggestion: Optional[str] = None):
    """
    显示错误信息
    
    Args:
        error_message: 错误消息
        suggestion: 建议操作
    """
    content = f"❌ **错误**: {error_message}"
    
    if suggestion:
        content += f"\n\n💡 **建议**: {suggestion}"
    
    await cl.Message(content=content).send()


async def show_info(title: str, content: str):
    """
    显示信息提示
    
    Args:
        title: 标题
        content: 内容
    """
    message = f"ℹ️ **{title}**\n\n{content}"
    await cl.Message(content=message).send()


async def show_execution_log(logs: list):
    """
    显示执行日志
    
    Args:
        logs: 日志列表
    """
    if not logs:
        await show_info("日志", "暂无执行日志")
        return
    
    log_md = "## 📋 执行日志\n\n"
    
    for log in logs[-20:]:
        level = log.get("log_level", "info")
        message = log.get("message", "")
        agent = log.get("agent_name", "")
        timestamp = log.get("timestamp", "")
        
        level_icon = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
        }.get(level, "ℹ️")
        
        log_md += f"{level_icon} `{timestamp}` "
        if agent:
            log_md += f"**{agent}**: "
        log_md += f"{message}\n\n"
    
    await cl.Message(content=log_md).send()


def format_task_progress(task_info: Dict[str, Any]) -> str:
    """
    格式化任务进度信息
    
    Args:
        task_info: 任务信息字典
        
    Returns:
        格式化的进度文本
    """
    current = task_info.get("current_step", 0)
    total = task_info.get("total_steps", 0)
    step_name = task_info.get("step_name", "处理中")
    
    if total > 0:
        percent = int((current / total) * 100)
    else:
        percent = 0
    
    progress_bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    
    return (
        f"**当前步骤**: {step_name}\n"
        f"**进度**: `{progress_bar}` {percent}%\n"
        f"**步骤**: {current}/{total}"
    )
