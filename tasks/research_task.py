from crewai import Task

from agents.research_agent import create_research_agent


def create_research_task(topic: str, search_queries: list[str] = None) -> Task:
    agent = create_research_agent()
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
            "- 记录数据的具体数值和来源"
        ).format(topic=topic, queries=queries_str),
        expected_output=(
            "一份结构化的信息采集报告，包含：\n"
            "- 市场概况数据（规模、增长率、趋势等）\n"
            "- 主要参与者信息\n"
            "- 关键事件和政策\n"
            "- 技术发展动态\n"
            "- 所有信息的来源URL列表\n"
            "- 信息缺口说明"
        ),
        agent=agent,
    )
