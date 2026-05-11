"""
计划确认交互组件

处理用户对研究计划的确认、修改或取消操作
"""

import chainlit as cl
from typing import Dict, Any, Optional
import requests

API_BASE_URL = "http://localhost:8000"
HTTP_TIMEOUT = 120


async def handle_plan_confirmation(task_id: str, plan_data: Dict[str, Any]):
    actions = [
        cl.Action(
            name="confirm_plan",
            value="confirmed",
            label="确认执行",
            payload={"task_id": task_id, "action": "confirm"},
        ),
        cl.Action(
            name="modify_plan",
            value="modify",
            label="修改计划",
            payload={"task_id": task_id, "action": "modify"},
        ),
        cl.Action(
            name="cancel_plan",
            value="cancelled",
            label="取消研究",
            payload={"task_id": task_id, "action": "cancel"},
        ),
    ]
    
    await cl.Message(
        content="请选择操作：",
        actions=actions,
    ).send()


@cl.action_callback("confirm_plan")
async def on_confirm(action: cl.Action):
    task_id = action.payload.get("task_id")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/plan/confirm",
            json={"confirmed": True},
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            await cl.Message(
                content="研究计划已确认，正在开始执行..."
            ).send()
            
            cl.user_session.set("plan_confirmed", True)
            
            await execute_confirmed_plan(task_id)
        else:
            await cl.Message(
                content="确认计划失败，请重试"
            ).send()
            
    except requests.ConnectionError:
        await cl.Message(
            content="无法连接到API服务，请确保后端服务已启动"
        ).send()
    except Exception as e:
        await cl.Message(content=f"发生错误：{str(e)}").send()


@cl.action_callback("modify_plan")
async def on_modify(action: cl.Action):
    await cl.Message(
        content="请输入您的修改意见，例如：\n\n"
                "- 增加某个研究维度\n"
                "- 调整研究深度\n"
                "- 修改搜索方向\n\n"
                "输入您的修改要求："
    ).send()
    
    cl.user_session.set("waiting_for_modification", True)


@cl.action_callback("cancel_plan")
async def on_cancel(action: cl.Action):
    task_id = action.payload.get("task_id")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/cancel",
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            await cl.Message(
                content="研究计划已取消。\n\n"
                        "请输入新的研究主题开始新的研究。"
            ).send()
            
            cl.user_session.set("current_task_id", None)
            cl.user_session.set("current_plan", None)
        else:
            await cl.Message(content="取消计划失败，请重试").send()
            
    except Exception as e:
        await cl.Message(content=f"发生错误：{str(e)}").send()


async def execute_confirmed_plan(task_id: str):
    topic = cl.user_session.get("current_topic", "研究")
    
    try:
        from crew import ResearchCrew
        
        progress_msg = await cl.Message(content="正在执行研究计划...").send()
        
        crew = ResearchCrew()
        
        await cl.Message(
            content="执行步骤：\n\n"
                    "1. 情报采集Agent - 搜索相关信息\n"
                    "2. 商业分析Agent - 多维度分析\n"
                    "3. 报告生成Agent - 撰写研究报告\n\n"
                    "请稍候，这可能需要几分钟..."
        ).send()
        
        result = crew.run(topic, depth="standard", auto_confirm=True)
        
        from frontend.display import render_report
        await render_report(result, task_id)
        
        cl.user_session.set("current_task_id", None)
        cl.user_session.set("current_plan", None)
        cl.user_session.set("plan_confirmed", False)
        
    except Exception as e:
        await cl.Message(content=f"执行研究计划失败：{str(e)}").send()


async def handle_plan_modification(task_id: str, modifications: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/plan/confirm",
            json={
                "confirmed": False,
                "modifications": modifications,
            },
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            await cl.Message(
                content=f"修改意见已提交：{modifications}\n\n"
                        f"正在根据您的需求调整研究计划..."
            ).send()
            
            await regenerate_plan(task_id, modifications)
        else:
            await cl.Message(content="提交修改意见失败，请重试").send()
            
    except Exception as e:
        await cl.Message(content=f"发生错误：{str(e)}").send()


async def regenerate_plan(task_id: str, modifications: str):
    topic = cl.user_session.get("current_topic", "研究")
    
    try:
        from crew import ResearchCrew
        from app.services.plan_service import PlanService
        from app.models.database import SessionLocal
        
        crew = ResearchCrew()
        plan = crew.create_plan(topic, depth="standard")
        
        plan_dict = {
            "topic": topic,
            "modifications": modifications,
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
            existing_plan = plan_service.get_plan(task_id)
            
            if existing_plan:
                plan_service.update_plan(task_id, plan_dict)
            else:
                plan_service.create_plan(task_id, plan_dict)
        finally:
            db.close()
        
        cl.user_session.set("current_plan", plan_dict)
        
        from frontend.plan_display import render_plan
        await render_plan(plan_dict)
        await handle_plan_confirmation(task_id, plan_dict)
        
    except Exception as e:
        await cl.Message(content=f"重新生成计划失败：{str(e)}").send()
