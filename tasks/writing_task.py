"""
写作任务 - 接收JSON并渲染为Markdown报告

WriterAgent接收ResearchOutput和AnalysisOutput JSON数据
将其渲染为优美的Markdown格式研究报告
"""

from crewai import Task

from agents.writer_agent import create_writer_agent
from models.structured_output import ReportOutput


REPORT_TEMPLATE = """# {topic} 研究报告

## 1. 执行摘要
- 研究背景
- 核心发现
- 关键建议

## 2. 研究方法与数据来源
- 研究范围
- 数据来源
- 分析方法

## 3. 市场分析
- 市场规模与趋势
- 目标用户群体
- 竞争格局

## 4. 竞品分析
- 主要竞品列表
- 竞品功能对比
- 竞品优劣势分析

## 5. SWOT分析
- 优势 (Strengths)
- 劣势 (Weaknesses)
- 机会 (Opportunities)
- 威胁 (Threats)

## 6. 结论与建议
- 核心结论
- 行动建议
- 风险提示

## 7. 参考来源
- 信息来源列表
"""


def create_writing_task(topic: str, analysis_context: str = "") -> Task:
    agent = create_writer_agent()
    context_section = ""
    if analysis_context:
        context_section = f"\n\n以下是各阶段的分析结果：\n{analysis_context}\n"

    return Task(
        description=(
            "作为专业研究报告撰写专家，请整合所有分析结果，撰写一份结构化的研究报告：\n\n"
            "主题：{topic}\n"
            "{context}"
            "\n\n报告结构要求：\n"
            "{template}\n"
            "撰写要求：\n"
            "1. 执行摘要应简洁有力，突出核心发现和关键建议\n"
            "2. 数据引用必须标注来源\n"
            "3. 分析结论要有逻辑论证链条\n"
            "4. 建议部分要具体可执行\n"
            "5. 全文使用Markdown格式\n"
            "6. 报告总字数不少于2000字\n"
            "7. 参考来源需列出所有引用的信息来源URL"
        ).format(topic=topic, context=context_section, template=REPORT_TEMPLATE),
        expected_output=(
            "一份完整的Markdown格式研究报告，包含：\n"
            "- 执行摘要（核心发现和关键建议）\n"
            "- 研究方法与数据来源\n"
            "- 市场分析\n"
            "- 竞品分析\n"
            "- SWOT分析\n"
            "- 结论与建议\n"
            "- 参考来源列表\n"
            "报告字数不少于2000字，逻辑清晰，数据有据"
        ),
        agent=agent,
        output_pydantic=ReportOutput,
    )
