"""
研究计划展示组件

负责将研究计划以清晰、结构化的方式展示给用户
"""

import chainlit as cl
from typing import Dict, Any, List


async def render_plan(plan_data: Dict[str, Any]):
    """
    渲染研究计划
    
    Args:
        plan_data: 包含计划信息的字典，包括tasks、topic等
    """
    topic = plan_data.get("topic", "未指定主题")
    tasks = plan_data.get("tasks", [])
    total_tasks = plan_data.get("total_tasks", len(tasks))
    estimated_time = plan_data.get("estimated_time", "未知")
    
    plan_md = f"""## 📋 研究计划

**研究主题**: {topic}

**任务总数**: {total_tasks} 个

**预计耗时**: {estimated_time}

---

### 任务详情

"""
    
    for i, task in enumerate(tasks, 1):
        task_id = task.get("task_id", str(i))
        description = task.get("description", "无描述")
        agent = task.get("agent", "未指定")
        expected_output = task.get("expected_output", "标准输出")
        search_queries = task.get("search_queries", [])
        
        plan_md += f"""#### 任务 {i}: {description}

- **执行Agent**: {agent}
- **预期输出**: {expected_output}
"""
        
        if search_queries:
            plan_md += "- **搜索关键词**:\n"
            for query in search_queries:
                plan_md += f"  - `{query}`\n"
        
        plan_md += "\n---\n\n"
    
    plan_md += """
### 执行流程

```
主编Agent (规划) 
    ↓
情报采集Agent (搜索) 
    ↓
商业分析Agent (分析) 
    ↓
报告生成Agent (撰写)
```

---

**请确认是否执行此计划？**

- 输入 **y** 或 **确认** 开始执行
- 输入 **n** 或 **取消** 取消计划
"""
    
    await cl.Message(content=plan_md).send()


def format_plan_summary(plan_data: Dict[str, Any]) -> str:
    """
    生成计划摘要
    
    Args:
        plan_data: 计划数据字典
        
    Returns:
        格式化的计划摘要文本
    """
    topic = plan_data.get("topic", "未指定")
    tasks = plan_data.get("tasks", [])
    
    summary = f"研究主题：{topic}\n"
    summary += f"任务数量：{len(tasks)}\n"
    summary += "任务列表：\n"
    
    for i, task in enumerate(tasks, 1):
        desc = task.get("description", "无描述")
        agent = task.get("agent", "未知")
        summary += f"  {i}. {desc} ({agent})\n"
    
    return summary


def validate_plan(plan_data: Dict[str, Any]) -> List[str]:
    """
    验证计划完整性
    
    Args:
        plan_data: 计划数据字典
        
    Returns:
        验证错误列表，空列表表示验证通过
    """
    errors = []
    
    if not plan_data.get("topic"):
        errors.append("缺少研究主题")
    
    tasks = plan_data.get("tasks", [])
    if not tasks:
        errors.append("没有研究任务")
    
    for i, task in enumerate(tasks, 1):
        if not task.get("description"):
            errors.append(f"任务 {i} 缺少描述")
        if not task.get("agent"):
            errors.append(f"任务 {i} 缺少执行Agent")
    
    return errors
