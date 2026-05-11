import json
import logging
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from config import llm_config

logger = logging.getLogger(__name__)


class ResearchSubTask(BaseModel):
    task_id: str = Field(description="任务唯一标识，如T1, T2")
    name: str = Field(description="任务名称")
    agent: str = Field(description="执行该任务的Agent名称")
    description: str = Field(description="任务详细描述")
    search_queries: list[str] = Field(default_factory=list, description="搜索关键词列表")
    depends_on: list[str] = Field(default_factory=list, description="依赖的前置任务ID列表")
    expected_output: str = Field(default="", description="预期输出描述")


class ResearchPlan(BaseModel):
    topic: str = Field(description="研究主题")
    objectives: list[str] = Field(default_factory=list, description="研究目标列表")
    scope_included: list[str] = Field(default_factory=list, description="研究包含范围")
    scope_excluded: list[str] = Field(default_factory=list, description="研究排除范围")
    tasks: list[ResearchSubTask] = Field(default_factory=list, description="研究子任务列表")
    estimated_duration: int = Field(default=300, description="预估执行时间(秒)")
    validation_points: list[str] = Field(default_factory=list, description="验证检查点")


PLANNING_SYSTEM_PROMPT = """你是一位资深研究主编与项目规划专家，拥有15年跨领域研究经验。你的任务是根据用户给出的研究主题，制定一份全面、结构化的研究计划。

## 研究计划必须包含以下内容：

1. **研究目标**：明确本次研究要回答的核心问题（3-5个）
2. **研究范围**：包含和排除的范围
3. **子任务列表**：每个任务包含：
   - task_id: 唯一标识（T1, T2, T3...）
   - name: 任务名称
   - agent: 执行Agent（ResearchAgent / BusinessAnalyst / WriterAgent）
   - description: 任务详细描述
   - search_queries: 搜索关键词（仅ResearchAgent任务需要）
   - depends_on: 依赖的前置任务ID
   - expected_output: 预期输出
4. **预估时间**：总预估执行时间（秒）
5. **验证点**：需要交叉验证的关键信息点

## 任务编排规则：

根据研究主题灵活调整任务结构，但通常遵循以下流程：

- **信息采集阶段**（ResearchAgent）：
  - T1: 基础信息采集 → 收集主题相关的基础数据、现状、背景信息
  - T2: 深度信息采集 → 收集更专业的数据、案例、观点（依赖T1）

- **分析阶段**（BusinessAnalyst）：
  - T3: 综合分析 → 基于采集的信息进行多维度分析（依赖T1, T2）

- **撰写阶段**（WriterAgent）：
  - T4: 报告撰写 → 整合所有分析结果，撰写结构化报告（依赖T3）

## 搜索关键词设计原则：

- 覆盖中英文搜索（如适用）
- 包含核心概念、相关术语、同义词
- 关注最新数据（近1-2年）
- 包含权威来源关键词

## 输出格式：

请严格按照以下JSON格式输出，不要输出任何其他内容：

```json
{
  "topic": "研究主题",
  "objectives": ["目标1", "目标2", "目标3"],
  "scope_included": ["包含范围1", "包含范围2"],
  "scope_excluded": ["排除范围1"],
  "tasks": [
    {
      "task_id": "T1",
      "name": "任务名称",
      "agent": "ResearchAgent",
      "description": "任务描述",
      "search_queries": ["搜索词1", "搜索词2"],
      "depends_on": [],
      "expected_output": "预期输出"
    }
  ],
  "estimated_duration": 300,
  "validation_points": ["验证点1"]
}
```"""


class PlanningService:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or llm_config.get_langchain_llm()

    def generate_plan(self, topic: str, depth: str = "standard") -> ResearchPlan:
        logger.info(f"开始生成研究计划，主题: {topic}, 深度: {depth}")

        depth_instruction = ""
        if depth == "deep":
            depth_instruction = "\n\n注意：用户选择了深度研究模式，请制定更详细的研究计划，增加更多搜索维度和分析角度，子任务数量不少于6个。"

        messages = [
            SystemMessage(content=PLANNING_SYSTEM_PROMPT),
            HumanMessage(content=f"请为以下研究主题制定研究计划：{topic}{depth_instruction}"),
        ]

        try:
            response = self.llm.invoke(messages)
            plan = self._parse_plan_response(response.content, topic)
            logger.info(f"研究计划生成成功，共{len(plan.tasks)}个子任务")
            return plan
        except Exception as e:
            logger.error(f"研究计划生成失败: {e}")
            return self._get_fallback_plan(topic)

    def _parse_plan_response(self, response_content: str, topic: str) -> ResearchPlan:
        json_str = self._extract_json(response_content)
        if json_str:
            try:
                plan_data = json.loads(json_str)
                return ResearchPlan(
                    topic=plan_data.get("topic", topic),
                    objectives=plan_data.get("objectives", []),
                    scope_included=plan_data.get("scope_included", []),
                    scope_excluded=plan_data.get("scope_excluded", []),
                    tasks=[ResearchSubTask(**t) for t in plan_data.get("tasks", [])],
                    estimated_duration=plan_data.get("estimated_duration", 300),
                    validation_points=plan_data.get("validation_points", []),
                )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"JSON解析失败，使用降级方案: {e}")

        return self._get_fallback_plan(topic)

    def _extract_json(self, text: str) -> Optional[str]:
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"(\{[\s\S]*\})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _get_fallback_plan(self, topic: str) -> ResearchPlan:
        return ResearchPlan(
            topic=topic,
            objectives=[
                f"分析{topic}的现状与发展趋势",
                f"评估{topic}的关键参与者与相关格局",
                f"识别{topic}的机会与潜在风险",
            ],
            scope_included=[f"{topic}现状分析", "相关对比", "发展趋势"],
            scope_excluded=["无关领域"],
            tasks=[
                ResearchSubTask(
                    task_id="T1",
                    name="基础信息采集",
                    agent="ResearchAgent",
                    description=f"收集{topic}的基础数据、现状、背景信息等",
                    search_queries=[f"{topic}现状", f"{topic}发展", f"{topic}报告"],
                    depends_on=[],
                    expected_output="基础数据、现状信息、背景资料",
                ),
                ResearchSubTask(
                    task_id="T2",
                    name="深度信息采集",
                    agent="ResearchAgent",
                    description=f"收集{topic}的相关参与者、技术路线、案例等信息",
                    search_queries=[f"{topic}分析", f"{topic}主要参与者", f"{topic}案例"],
                    depends_on=["T1"],
                    expected_output="相关参与者信息、技术路线、案例分析",
                ),
                ResearchSubTask(
                    task_id="T3",
                    name="综合分析",
                    agent="BusinessAnalyst",
                    description=f"基于采集的信息进行多维度分析",
                    search_queries=[],
                    depends_on=["T1", "T2"],
                    expected_output="多维度分析结果",
                ),
                ResearchSubTask(
                    task_id="T4",
                    name="报告撰写",
                    agent="WriterAgent",
                    description=f"整合所有分析结果，撰写结构化的{topic}研究报告",
                    search_queries=[],
                    depends_on=["T3"],
                    expected_output="完整的结构化研究报告(Markdown格式)",
                ),
            ],
            estimated_duration=300,
            validation_points=[f"{topic}关键数据交叉验证"],
        )

    def format_plan_display(self, plan: ResearchPlan) -> str:
        lines = [
            "=" * 60,
            f"  研究计划: {plan.topic}",
            "=" * 60,
            "",
            "【研究目标】",
        ]
        for i, obj in enumerate(plan.objectives, 1):
            lines.append(f"  {i}. {obj}")

        lines.append("\n【研究范围】")
        lines.append(f"  包含: {', '.join(plan.scope_included)}")
        lines.append(f"  排除: {', '.join(plan.scope_excluded)}")

        lines.append("\n【任务列表】")
        for task in plan.tasks:
            deps = f" (依赖: {', '.join(task.depends_on)})" if task.depends_on else ""
            lines.append(f"  [{task.task_id}] {task.name} → {task.agent}{deps}")
            lines.append(f"      描述: {task.description}")
            if task.search_queries:
                lines.append(f"      搜索词: {', '.join(task.search_queries)}")

        lines.append(f"\n【预估时间】{plan.estimated_duration}秒")
        if plan.validation_points:
            lines.append("【验证点】")
            for vp in plan.validation_points:
                lines.append(f"  - {vp}")

        lines.append("=" * 60)
        return "\n".join(lines)
