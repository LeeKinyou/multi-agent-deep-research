"""
商业分析Agent - 支持RAG检索

增强功能：
- 使用RAG从向量数据库中精准检索相关数据
- 避免被截断的上下文限制分析质量
- 按需检索，获取完整的原始数据片段
"""

from crewai import Agent

from config import llm_config
from tools.rag_tools import RAGTools


def create_business_agent(task_id: str = None) -> Agent:
    tools = []
    
    if task_id:
        rag_tools = RAGTools.create_store_and_search_tools(task_id)
        tools.extend(rag_tools)
    
    backstory = (
        "你拥有10年以上的跨领域研究分析经验，曾参与数百份深度研究报告的分析工作。"
        "你擅长从多个维度解读信息，能够将复杂的数据转化为清晰的洞察。"
        "你的分析框架包括SWOT分析、趋势分析、对比分析等，"
        "能够从多角度评估现状、机会和风险。你注重数据支撑，"
        "每个结论都有充分的事实依据。"
    )
    
    if task_id:
        backstory += (
            f"\n\n当前任务ID: {task_id}。"
            "你可以使用 search_research_info 工具从向量数据库中检索情报采集Agent存储的研究数据。"
            "在进行SWOT分析、趋势研判等分析工作时，先调用 search_research_info 检索相关数据，"
            "这样可以获取完整的原始信息，而不受上下文长度限制。"
            "例如：search_research_info(query='该公司的竞争劣势是什么', n_results=5)"
        )

    return Agent(
        role="资深分析专家",
        goal=(
            "基于收集的信息进行深入的多维度分析，包括现状分析、趋势研判、"
            "机会与风险评估，提供有洞察力的专业判断和建议"
        ),
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools if tools else None,
        llm=llm_config.get_crewai_llm(),
    )
