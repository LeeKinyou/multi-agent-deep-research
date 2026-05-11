"""
报告展示组件

负责渲染和展示研究报告，支持Markdown渲染和下载功能
"""

import chainlit as cl
from typing import Optional, Dict, Any
import requests

API_BASE_URL = "http://localhost:8000"
HTTP_TIMEOUT = 120


async def render_report(report_content: str, task_id: str, agent_thoughts: list = None):
    elements = [
        cl.File(
            name=f"report_{task_id}.md",
            content=report_content.encode("utf-8"),
            mime="text/markdown",
            description="下载完整报告",
        )
    ]
    
    actions = [
        cl.Action(
            name="download_report",
            value="download",
            label="下载",
            payload={"task_id": task_id},
        ),
        cl.Action(
            name="show_thinking_process",
            value="show",
            label="查看思考过程",
            payload={"task_id": task_id},
        ),
        cl.Action(
            name="new_research",
            value="new",
            label="新的研究",
            payload={"action": "new"},
        ),
    ]
    
    success_md = f"""# 研究完成

**任务ID**: `{task_id}`

---

{report_content}

---

## 下载报告

点击下方按钮下载完整报告，或输入新的研究主题开始新的研究。
"""
    
    await cl.Message(
        content=success_md,
        elements=elements,
        actions=actions,
    ).send()


async def render_report_from_api(task_id: str):
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/tasks/{task_id}/result",
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            report_content = result.get("report_content", "")
            word_count = result.get("word_count", 0)
            sources_count = result.get("sources_count", 0)
            
            report_md = f"""# 研究报告

**任务ID**: `{task_id}`

**字数**: {word_count} 字

**信息来源**: {sources_count} 个

---

{report_content}

---

## 下载报告

点击下方按钮下载完整报告。
"""
            
            elements = [
                cl.File(
                    name=f"report_{task_id}.md",
                    content=report_content.encode("utf-8"),
                    mime="text/markdown",
                    description="下载报告",
                )
            ]
            
            await cl.Message(
                content=report_md,
                elements=elements,
            ).send()
        else:
            await cl.Message(
                content=f"获取报告失败，状态码：{response.status_code}"
            ).send()
            
    except requests.ConnectionError:
        await cl.Message(
            content="无法连接到API服务，请确保后端服务已启动"
        ).send()
    except Exception as e:
        await cl.Message(content=f"发生错误：{str(e)}").send()


async def show_report_preview(report_content: str, max_lines: int = 50):
    """
    显示报告预览
    
    Args:
        report_content: 报告内容
        max_lines: 最大显示行数
    """
    lines = report_content.split("\n")
    
    if len(lines) > max_lines:
        preview = "\n".join(lines[:max_lines])
        preview += f"\n\n... (共 {len(lines)} 行，请下载完整报告查看)"
    else:
        preview = report_content
    
    await cl.Message(
        content=f"## 📖 报告预览\n\n{preview}",
    ).send()


def extract_report_summary(report_content: str) -> Dict[str, Any]:
    """
    提取报告摘要信息
    
    Args:
        report_content: 报告内容
        
    Returns:
        摘要信息字典
    """
    lines = report_content.split("\n")
    
    summary = {
        "title": "",
        "sections": [],
        "word_count": len(report_content),
        "line_count": len(lines),
    }
    
    for line in lines:
        if line.startswith("# ") and not summary["title"]:
            summary["title"] = line[2:].strip()
        elif line.startswith("## "):
            summary["sections"].append(line[3:].strip())
    
    return summary


async def show_report_summary(report_content: str):
    """
    显示报告摘要
    
    Args:
        report_content: 报告内容
    """
    summary = extract_report_summary(report_content)
    
    summary_md = f"""## 📊 报告摘要

**标题**: {summary.get('title', '未指定')}

**字数**: {summary['word_count']} 字

**章节数**: {len(summary['sections'])}

### 章节列表

"""
    
    for i, section in enumerate(summary['sections'], 1):
        summary_md += f"{i}. {section}\n"
    
    await cl.Message(content=summary_md).send()
