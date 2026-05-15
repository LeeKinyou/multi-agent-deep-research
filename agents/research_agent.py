"""
情报采集Agent - 支持RAG存储

增强功能：
- 采集到的信息自动分块存储到向量数据库
- 支持按任务ID隔离的长期记忆
- 为后续分析Agent提供RAG检索能力
"""

from crewai import Agent

from config import llm_config
from tools.search_tool import get_search_tools
from tools.rag_tools import create_rag_tools


def create_research_agent(task_id: str = None) -> Agent:
    tools = get_search_tools()
    
    if task_id:
        rag_tools = create_rag_tools(task_id)
        tools.extend(rag_tools)
    
    backstory = (
        "你是一位经验丰富的情报分析师，擅长使用各种搜索工具快速定位关键信息，"
        "能够从海量数据中筛选出最有价值的内容。你注重信息的来源可靠性，"
        "会对搜索结果进行初步筛选和验证，确保采集的信息具有参考价值。"
        "你善于从不同角度搜索同一主题，以获得全面的信息覆盖。"
    )
    
    if task_id:
        backstory += (
            f"\n\n当前任务ID: {task_id}。"
            "你可以使用 store_research_info 工具将采集到的重要信息存储到向量数据库中，"
            "这样后续的分析Agent可以通过RAG检索获取完整的研究数据。"
            "建议在每次搜索完成后，将整理好的信息调用 store_research_info 存储起来。"
        )

    return Agent(
        role="专业情报采集员",
        goal=(
            "根据主编制定的研究计划，全面收集与研究主题相关的网络信息，"
            "确保信息的准确性、时效性和来源多样性"
        ),
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools,
        llm=llm_config.get_crewai_llm(),
    )
