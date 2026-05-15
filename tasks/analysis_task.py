"""
分析任务 - 使用结构化JSON输出

BusinessAnalyst接收ResearchOutput JSON，输出AnalysisOutput JSON格式
通过RAG检索获取完整数据，避免上下文截断
"""

from crewai import Task

from agents.business_agent import create_business_agent
from models.structured_output import AnalysisOutput


def create_analysis_task(topic: str, research_context: str = "") -> Task:
    agent = create_business_agent(task_id=None)
    context_section = ""
    if research_context:
        context_section = f"\n\n以下是情报采集阶段获取的信息：\n{research_context}\n"

    return Task(
        description=(
            "作为资深分析专家，请基于采集的信息进行深入的多维度分析：\n\n"
            "主题：{topic}\n"
            "{context}"
            "\n请完成以下分析：\n\n"
            "1. **现状分析**：\n"
            "   - 当前整体状况概述\n"
            "   - 关键特征与核心要素\n"
            "   - 主要参与者/相关方介绍\n\n"
            "2. **SWOT分析**：\n"
            "   - 优势(Strengths)：核心竞争力和有利因素\n"
            "   - 劣势(Weaknesses)：内在不足和短板\n"
            "   - 机会(Opportunities)：外部有利趋势和机遇\n"
            "   - 威胁(Threats)：外部风险和挑战\n\n"
            "3. **趋势研判**：\n"
            "   - 发展趋势与走向\n"
            "   - 关键驱动因素\n"
            "   - 潜在风险因素\n\n"
            "4. **专业建议**：\n"
            "   - 针对性建议\n"
            "   - 风险提示\n"
            "   - 行动优先级\n\n"
            "分析要求：\n"
            "- 每个结论都需要有数据或事实支撑\n"
            "- 分析框架完整，逻辑严密\n"
            "- 建议具体可执行，避免空泛\n"
            "- 输出必须为严格的JSON格式，不要包含任何额外文本"
        ).format(topic=topic, context=context_section),
        expected_output=(
            "返回AnalysisOutput JSON格式，包含：\n"
            "- current_status: 现状分析概述\n"
            "- key_characteristics: 关键特征列表\n"
            "- swot: SWOT分析（优势/劣势/机会/威胁列表）\n"
            "- trends: 趋势研判（方向/驱动因素/风险/预测）\n"
            "- recommendations: 针对性建议列表\n"
            "- risk_warnings: 风险提示列表\n"
            "- action_priorities: 行动优先级列表\n"
            "- conclusion: 分析结论\n"
            "- data_sources: 分析数据来源"
        ),
        agent=agent,
        output_pydantic=AnalysisOutput,
    )
