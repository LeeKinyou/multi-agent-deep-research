"""
增强版情报采集Agent - 支持多模态分析

在原有 ResearchAgent 基础上增加：
- PDF 文档解析能力
- 网页可视化提取能力
- 图表数据分析能力
- 可视化生成能力
"""

from crewai import Agent

from config import llm_config
from tools.search_tool import get_search_tools
from tools.rag_tools import create_rag_tools
from tools.multimodal_tools import get_multimodal_tools


def create_multimodal_research_agent(task_id: str = None) -> Agent:
    """创建支持多模态分析的研究Agent"""
    tools = get_search_tools()

    if task_id:
        rag_tools = create_rag_tools(task_id)
        tools.extend(rag_tools)

    # 添加多模态工具
    tools.extend(get_multimodal_tools())

    backstory = (
        "你是一位经验丰富的多模态情报分析师，擅长使用各种搜索工具快速定位关键信息，"
        "能够从海量数据中筛选出最有价值的内容。你注重信息的来源可靠性，"
        "会对搜索结果进行初步筛选和验证，确保采集的信息具有参考价值。"
        "你善于从不同角度搜索同一主题，以获得全面的信息覆盖。\n\n"
        "你具备强大的多模态分析能力：\n"
        "- 能够解析 PDF 行业报告，提取其中的文本和图表数据\n"
        "- 能够从网页中提取数据可视化元素并进行分析\n"
        "- 能够从图表图像中提取定量数据并进行趋势分析\n"
        "- 能够根据提取的数据生成标准化的可视化图表\n"
        "你善于将文本信息与视觉数据结合，形成全面的研究结论。"
    )

    if task_id:
        backstory += (
            f"\n\n当前任务ID: {task_id}。"
            "你可以使用 store_research_info 工具将采集到的重要信息存储到向量数据库中，"
            "这样后续的分析Agent可以通过RAG检索获取完整的研究数据。"
            "建议在每次搜索或分析完成后，将整理好的信息调用 store_research_info 存储起来。"
        )

    return Agent(
        role="多模态情报分析师",
        goal=(
            "根据主编制定的研究计划，全面收集与研究主题相关的网络信息和文档资料，"
            "通过多模态分析技术提取文本和视觉数据，确保信息的准确性、时效性和来源多样性"
        ),
        backstory=backstory,
        verbose=True,
        allow_delegation=False,
        tools=tools,
        llm=llm_config.get_crewai_llm(),
    )
