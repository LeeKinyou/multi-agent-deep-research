"""
研究任务 - 使用结构化JSON输出

ResearchAgent采集信息后返回ResearchOutput JSON格式，而非大段文本
大幅减少Token消耗，避免信息在传递过程中丢失
"""

from crewai import Task

from agents.research_agent import create_research_agent
from models.structured_output import ResearchOutput


def create_research_task(topic: str, search_queries: list[str] = None) -> Task:
    agent = create_research_agent(task_id=None)
    queries = search_queries or [
        f"{topic}市场规模 发展趋势",
        f"{topic}行业报告 现状分析",
        f"{topic}主要公司 竞争格局",
        f"{topic}商业模式 盈利模式",
    ]
    queries_str = "\n".join(f"  - {q}" for q in queries)

    return Task(
        description=(
            "作为专业情报采集员，请针对以下研究主题进行全面的信息采集：\n\n"
            "主题：{topic}\n\n"
            "搜索方向：\n{queries}\n\n"
            "请完成以下工作：\n"
            "1. 按照搜索方向逐一搜索，收集相关信息\n"
            "2. 对搜索结果进行初步筛选，去除无关和低质量信息\n"
            "3. 验证关键数据的来源可靠性\n"
            "4. 整理信息，按主题分类归纳\n"
            "5. 标注信息来源URL，确保可追溯\n"
            "6. 识别信息缺口，必要时进行补充搜索\n\n"
            "注意事项：\n"
            "- 优先采集近两年的最新数据\n"
            "- 关注权威来源（政府报告、行业白皮书、知名咨询公司报告）\n"
            "- 对同一数据尽量找到多个来源进行交叉验证\n"
            "- 记录数据的具体数值和来源\n"
            "- 输出必须为严格的JSON格式，不要包含任何额外文本"
        ).format(topic=topic, queries=queries_str),
        expected_output=(
            "返回ResearchOutput JSON格式，包含：\n"
            "- market_overview: 市场概况（规模、增长率、趋势）\n"
            "- key_players: 主要参与者列表\n"
            "- key_events: 关键事件和政策\n"
            "- technology_trends: 技术发展动态\n"
            "- data_points: 关键数据点\n"
            "- sources: 信息来源列表\n"
            "- information_gaps: 信息缺口\n"
            "- summary: 研究摘要（500字以内）"
        ),
        agent=agent,
        output_pydantic=ResearchOutput,
    )
