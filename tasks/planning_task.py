from crewai import Task

from agents.editor_agent import create_editor_agent


def create_planning_task(topic: str) -> Task:
    agent = create_editor_agent()
    return Task(
        description=(
            "作为研究主编，请为以下研究主题制定一份全面、结构化的研究计划：\n\n"
            "主题：{topic}\n\n"
            "请完成以下工作：\n"
            "1. 分析主题的核心问题和研究价值\n"
            "2. 明确研究目标（3-5个核心问题）\n"
            "3. 确定研究范围（包含和排除的领域）\n"
            "4. 设计信息采集策略（搜索关键词、信息来源类型）\n"
            "5. 规划分析维度与框架（SWOT、竞品对比等）\n"
            "6. 制定子任务列表，明确每个任务的执行Agent、搜索方向和预期输出\n"
            "7. 识别潜在风险与备选方案\n\n"
            "输出要求：\n"
            "- 研究目标清晰、可衡量\n"
            "- 子任务之间逻辑连贯，依赖关系明确\n"
            "- 搜索关键词覆盖中英文，确保信息全面性\n"
            "- 预估每个阶段的执行时间"
        ).format(topic=topic),
        expected_output=(
            "一份结构化的研究计划，包含：研究目标列表、研究范围、"
            "子任务列表（每个任务包含task_id、名称、执行Agent、描述、搜索关键词、依赖关系、预期输出）、"
            "预估时间和验证检查点"
        ),
        agent=agent,
    )
