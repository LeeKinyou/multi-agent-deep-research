"""
MultiAgentDeepResearch - Chainlit前端应用（流式版本）

提供对话式Web界面，支持：
- 研究主题输入
- 研究计划展示与确认
- SSE流式实时进度查看
- Agent思考过程可视化展示
- 报告预览与下载
- 历史记录查看
"""

import chainlit as cl
import requests
import json
import time
import asyncio
from typing import Optional, Dict, Any, List
from frontend.plan_display import render_plan
from frontend.plan_confirmation import handle_plan_confirmation
from frontend.display import render_report
from frontend.components import (
    show_welcome_message,
    show_task_status,
    create_progress_bar,
    update_progress,
    show_agent_thinking,
)

API_BASE_URL = "http://localhost:8000"
HTTP_TIMEOUT = 120
SSE_TIMEOUT = 300


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("current_task_id", None)
    cl.user_session.set("current_plan", None)
    cl.user_session.set("agent_thoughts", [])
    cl.user_session.set("stream_messages", [])
    await show_welcome_message()


@cl.on_message
async def on_message(message: cl.Message):
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
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/",
            json={"topic": topic, "depth": "standard"},
            timeout=HTTP_TIMEOUT
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
        cl.user_session.set("agent_thoughts", [])
        cl.user_session.set("stream_messages", [])
        
        await cl.Message(
            content=f"研究任务已创建，任务ID：`{task_id}`\n\n"
                    f"研究主题：{topic}\n\n"
                    f"正在生成研究计划，请稍候..."
        ).send()
        
        await generate_and_display_plan(task_id, topic)
        
    except requests.exceptions.Timeout:
        await cl.Message(
            content="请求超时，后端服务处理时间过长。\n\n"
                    "请检查：\n"
                    "1. 后端服务是否正常运行\n"
                    "2. 数据库连接是否正常\n"
                    "3. 系统资源是否充足"
        ).send()
    except requests.ConnectionError:
        await cl.Message(
            content="无法连接到API服务，请确保后端服务已启动。\n\n"
                    "启动命令：`python -m uvicorn app.main:app --reload`"
        ).send()
    except Exception as e:
        await cl.Message(content=f"发生错误：{str(e)}").send()


async def generate_and_display_plan(task_id: str, topic: str):
    try:
        from crew import ResearchCrew
        from app.services.plan_service import PlanService
        from app.models.database import SessionLocal
        from app.services.stream_service import stream_manager
        
        thinking_msg = await cl.Message(content="主编Agent正在思考研究计划...").send()
        
        crew = ResearchCrew(task_id=task_id)
        plan = crew.create_plan(topic, depth="standard")
        
        await thinking_msg.remove()
        
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
    current_task_id = cl.user_session.get("current_task_id")
    current_plan = cl.user_session.get("current_plan")
    
    if current_plan and user_input.lower() in ["y", "yes", "确认", "是", "ok"]:
        await confirm_plan_and_execute_streaming(current_task_id, current_plan)
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


async def confirm_plan_and_execute_streaming(task_id: str, plan: Dict[str, Any]):
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/plan/confirm",
            json={"confirmed": True},
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            await cl.Message(
                content="研究计划已确认，正在执行研究任务...\n\n"
                        "**实时进度将在此展示**"
            ).send()
            
            await execute_research_streaming(task_id)
        else:
            await cl.Message(content="确认计划失败，请重试。").send()
            
    except requests.exceptions.Timeout:
        await cl.Message(content="请求超时，请检查后端服务状态。").send()
    except Exception as e:
        await cl.Message(content=f"确认计划时发生错误：{str(e)}").send()


async def execute_research_streaming(task_id: str):
    topic = cl.user_session.get("current_topic", "研究")
    agent_thoughts = []
    
    try:
        from crew import ResearchCrew
        from app.services.stream_service import stream_manager
        import asyncio
        
        progress_msg = await cl.Message(content="正在启动研究任务...").send()
        
        async def stream_callback(event_type: str, data: Dict[str, Any]):
            nonlocal agent_thoughts
            
            if event_type == "agent_start":
                agent_name = data.get("agent_name", "未知Agent")
                task_desc = data.get("task_description", "")
                
                await cl.Message(
                    content=f"**{agent_name}** 开始工作\n\n{task_desc}"
                ).send()
                
            elif event_type == "agent_thinking":
                agent_name = data.get("agent_name", "未知Agent")
                thinking = data.get("thinking", "")
                step = data.get("step", "")
                
                agent_thoughts.append({
                    "agent": agent_name,
                    "content": thinking,
                    "step": step,
                    "timestamp": time.time(),
                })
                
                thinking_md = f"""
<details>
<summary>{agent_name} - 思考过程</summary>

{thinking}

</details>
"""
                await cl.Message(content=thinking_md).send()
                
            elif event_type == "agent_complete":
                agent_name = data.get("agent_name", "未知Agent")
                output = data.get("output", "")
                
                await cl.Message(
                    content=f"**{agent_name}** 完成工作\n\n{output}"
                ).send()
                
            elif event_type == "progress":
                current = data.get("current_step", 0)
                total = data.get("total_steps", 0)
                message = data.get("message", "")
                percent = data.get("percent", 0)
                
                progress_bar = "=" * (percent // 5) + "-" * (20 - percent // 5)
                progress_content = f"**进度**: [{progress_bar}] {percent}%\n\n{message}"
                
                await progress_msg.update(content=progress_content)
                
            elif event_type == "task_status":
                status = data.get("status", "")
                message = data.get("message", "")
                
                if status == "starting":
                    await progress_msg.update(content=message)
                    
            elif event_type == "complete":
                result = data.get("result", "")
                
                await progress_msg.remove()
                
                cl.user_session.set("agent_thoughts", agent_thoughts)
                
                await render_report(result, task_id, agent_thoughts)
                
                cl.user_session.set("current_task_id", None)
                cl.user_session.set("current_plan", None)
        
        crew = ResearchCrew(
            task_id=task_id,
            stream_callback=stream_callback,
        )
        
        result = await crew.arun_streaming(topic, depth="standard")
        
        cl.user_session.set("agent_thoughts", agent_thoughts)
        
        await progress_msg.remove()
        await render_report(result, task_id, agent_thoughts)
        
        cl.user_session.set("current_task_id", None)
        cl.user_session.set("current_plan", None)
        
    except asyncio.TimeoutError:
        await cl.Message(
            content="研究任务执行超时。\n\n"
                    "可能原因：\n"
                    "1. LLM API响应缓慢\n"
                    "2. 网络搜索耗时过长\n"
                    "3. 系统资源不足\n\n"
                    "建议：检查API密钥配置和网络连接"
        ).send()
    except Exception as e:
        await cl.Message(content=f"执行研究任务失败：{str(e)}").send()


@cl.action_callback("view_history")
async def view_history(action):
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tasks/",
            params={"limit": 10},
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            tasks = response.json()["tasks"]
            
            if not tasks:
                await cl.Message(content="暂无历史记录。").send()
                return
            
            history_text = "## 历史研究任务\n\n"
            for task in tasks:
                status_emoji = {
                    "completed": "completed",
                    "running": "running",
                    "failed": "failed",
                    "cancelled": "cancelled",
                    "planning": "planning",
                    "pending": "pending",
                }.get(task["status"], "unknown")
                
                history_text += (
                    f"- **{task['topic']}**\n"
                    f"  - 状态：{task['status']}\n"
                    f"  - 创建时间：{task['created_at']}\n\n"
                )
            
            await cl.Message(content=history_text).send()
        else:
            await cl.Message(content="获取历史记录失败。").send()
            
    except requests.exceptions.Timeout:
        await cl.Message(content="获取历史记录超时。").send()
    except Exception as e:
        await cl.Message(content=f"获取历史记录时发生错误：{str(e)}").send()


@cl.action_callback("download_report")
async def download_report(action):
    task_id = cl.user_session.get("current_task_id")
    
    if not task_id:
        await cl.Message(content="没有可下载的报告。").send()
        return
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/result",
            timeout=HTTP_TIMEOUT
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
            
    except requests.exceptions.Timeout:
        await cl.Message(content="下载报告超时。").send()
    except Exception as e:
        await cl.Message(content=f"下载报告时发生错误：{str(e)}").send()


@cl.action_callback("show_thinking_process")
async def show_thinking_process(action):
    agent_thoughts = cl.user_session.get("agent_thoughts", [])
    
    if not agent_thoughts:
        await cl.Message(content="暂无Agent思考过程记录。").send()
        return
    
    thinking_md = "## Agent 思考过程\n\n"
    
    for thought in agent_thoughts:
        thinking_md += f"<details>\n<summary>{thought['agent']}</summary>\n\n{thought['content']}\n\n</details>\n\n"
    
    thinking_md += "---\n\n_思考过程记录了每个Agent在执行任务时的分析思路和决策过程_"
    
    await cl.Message(content=thinking_md).send()
