"""
MultiAgentDeepResearch - Chainlit前端应用

提供对话式Web界面，支持：
- 研究主题输入
- 研究计划展示与确认
- 实时进度查看
- 报告预览与下载
- 历史记录查看
"""

import chainlit as cl
import requests
import json
from typing import Optional, Dict, Any
from frontend.plan_display import render_plan
from frontend.plan_confirmation import handle_plan_confirmation
from frontend.display import render_report
from frontend.components import (
    show_welcome_message,
    show_task_status,
    create_progress_bar,
    update_progress,
)

API_BASE_URL = "http://localhost:8000"


@cl.on_chat_start
async def on_chat_start():
    """聊天会话开始时执行"""
    cl.user_session.set("current_task_id", None)
    cl.user_session.set("current_plan", None)
    await show_welcome_message()


@cl.on_message
async def on_message(message: cl.Message):
    """处理用户消息"""
    user_input = message.content.strip()
    
    if not user_input:
        await cl.Message(content="请输入研究主题，不能为空。").send()
        return
    
    current_task_id = cl.user_session.get("current_task_id")
    
    if current_task_id:
        await handle_existing_task(user_input)
    else:
        await create_new_research_task(user_input)


async def create_new_research_task(topic: str):
    """创建新的研究任务"""
    progress_bar = await create_progress_bar("正在创建研究任务...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/",
            json={"topic": topic, "depth": "standard"},
            timeout=10
        )
        
        if response.status_code != 201:
            await cl.Message(
                content=f"创建任务失败，请稍后重试。错误码：{response.status_code}"
            ).send()
            return
        
        task_data = response.json()
        task_id = task_data["task_id"]
        cl.user_session.set("current_task_id", task_id)
        cl.user_session.set("current_topic", topic)
        
        await update_progress(progress_bar, 100, "任务创建成功")
        
        await cl.Message(
            content=f"研究任务已创建，任务ID：`{task_id}`\n\n"
                    f"研究主题：{topic}\n\n"
                    f"正在生成研究计划，请稍候..."
        ).send()
        
        await generate_and_display_plan(task_id, topic)
        
    except requests.ConnectionError:
        await cl.Message(
            content="无法连接到API服务，请确保后端服务已启动。\n\n"
                    "启动命令：`python -m uvicorn app.main:app --reload`"
        ).send()
    except Exception as e:
        await cl.Message(content=f"发生错误：{str(e)}").send()


async def generate_and_display_plan(task_id: str, topic: str):
    """生成并展示研究计划"""
    try:
        from crew import ResearchCrew
        from app.services.plan_service import PlanService
        from app.models.database import get_db, SessionLocal
        
        crew = ResearchCrew()
        plan = crew.create_plan(topic, depth="standard")
        
        plan_dict = {
            "topic": topic,
            "tasks": [
                {
                    "task_id": str(i),
                    "description": task.description,
                    "agent": task.agent,
                    "expected_output": task.expected_output,
                }
                for i, task in enumerate(plan.tasks, 1)
            ],
            "total_tasks": len(plan.tasks),
            "estimated_time": "3-5分钟",
        }
        
        db = SessionLocal()
        try:
            plan_service = PlanService(db)
            plan_service.create_plan(task_id, plan_dict)
        finally:
            db.close()
        
        cl.user_session.set("current_plan", plan_dict)
        
        await render_plan(plan_dict)
        await handle_plan_confirmation(task_id, plan_dict)
        
    except Exception as e:
        await cl.Message(content=f"生成研究计划失败：{str(e)}").send()


async def handle_existing_task(user_input: str):
    """处理已有任务的用户输入"""
    current_task_id = cl.user_session.get("current_task_id")
    current_plan = cl.user_session.get("current_plan")
    
    if current_plan and user_input.lower() in ["y", "yes", "确认", "是", "ok"]:
        await confirm_plan_and_execute(current_task_id, current_plan)
    elif current_plan and user_input.lower() in ["n", "no", "取消", "否"]:
        await cl.Message(content="研究计划已取消。请输入新的研究主题开始新的研究。").send()
        cl.user_session.set("current_task_id", None)
        cl.user_session.set("current_plan", None)
    elif current_plan:
        await cl.Message(
            content="请确认研究计划：\n\n"
                    "输入 **y** 或 **确认** 开始执行\n"
                    "输入 **n** 或 **取消** 取消计划\n"
                    "输入新的研究主题开始新的研究"
        ).send()
    else:
        await create_new_research_task(user_input)


async def confirm_plan_and_execute(task_id: str, plan: Dict[str, Any]):
    """确认计划并开始执行"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/plan/confirm",
            json={"confirmed": True},
            timeout=10
        )
        
        if response.status_code == 200:
            await cl.Message(
                content="研究计划已确认，正在执行研究任务，请稍候..."
            ).send()
            
            await execute_research(task_id)
        else:
            await cl.Message(content="确认计划失败，请重试。").send()
            
    except Exception as e:
        await cl.Message(content=f"确认计划时发生错误：{str(e)}").send()


async def execute_research(task_id: str):
    """执行研究任务"""
    topic = cl.user_session.get("current_topic", "研究")
    
    try:
        from crew import ResearchCrew
        
        crew = ResearchCrew()
        result = crew.run(topic, depth="standard", auto_confirm=True)
        
        await render_report(result, task_id)
        
        cl.user_session.set("current_task_id", None)
        cl.user_session.set("current_plan", None)
        
    except Exception as e:
        await cl.Message(content=f"执行研究任务失败：{str(e)}").send()


@cl.action_callback("view_history")
async def view_history(action):
    """查看历史记录"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tasks/",
            params={"limit": 10},
            timeout=10
        )
        
        if response.status_code == 200:
            tasks = response.json()["tasks"]
            
            if not tasks:
                await cl.Message(content="暂无历史记录。").send()
                return
            
            history_text = "## 历史研究任务\n\n"
            for task in tasks:
                status_emoji = {
                    "completed": "✅",
                    "running": "🔄",
                    "failed": "❌",
                    "cancelled": "⛔",
                    "planning": "📝",
                    "pending": "⏳",
                }.get(task["status"], "❓")
                
                history_text += (
                    f"{status_emoji} **{task['topic']}**\n"
                    f"   - 状态：{task['status']}\n"
                    f"   - 创建时间：{task['created_at']}\n\n"
                )
            
            await cl.Message(content=history_text).send()
        else:
            await cl.Message(content="获取历史记录失败。").send()
            
    except Exception as e:
        await cl.Message(content=f"获取历史记录时发生错误：{str(e)}").send()


@cl.action_callback("download_report")
async def download_report(action):
    """下载报告"""
    task_id = cl.user_session.get("current_task_id")
    
    if not task_id:
        await cl.Message(content="没有可下载的报告。").send()
        return
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/result",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            report_content = result["report_content"]
            
            elements = [
                cl.File(
                    name=f"report_{task_id}.md",
                    content=report_content.encode("utf-8"),
                    mime="text/markdown",
                )
            ]
            
            await cl.Message(
                content="报告已准备好下载：",
                elements=elements,
            ).send()
        else:
            await cl.Message(content="下载报告失败。").send()
            
    except Exception as e:
        await cl.Message(content=f"下载报告时发生错误：{str(e)}").send()
