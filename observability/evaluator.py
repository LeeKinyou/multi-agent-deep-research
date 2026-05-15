"""
LLM-as-a-Judge 评测体系

采用 LLM 作为评判者，对 Agent 生成的报告进行多维度自动化评测。
支持信源一致性、逻辑严密性等核心指标，可扩展更多评测维度。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from config import llm_config
from observability.langfuse_client import get_langfuse_client

logger = logging.getLogger(__name__)


class EvaluationDimension(str, Enum):
    """评测维度枚举"""
    SOURCE_CONSISTENCY = "source_consistency"      # 信源一致性
    LOGICAL_RIGOR = "logical_rigor"                # 逻辑严密性
    ACCURACY = "accuracy"                          # 准确性
    COMPLETENESS = "completeness"                  # 完整性
    COMPLIANCE = "compliance"                      # 合规性
    CLARITY = "clarity"                            # 清晰度
    CITATION_QUALITY = "citation_quality"          # 引用质量
    STRUCTURE_QUALITY = "structure_quality"        # 结构质量


@dataclass
class DimensionScore:
    """单个维度的评分结果"""
    dimension: str
    score: float                                  # 0-10 分
    weight: float = 1.0
    reasoning: str = ""
    deductions: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class EvaluationResult:
    """完整评测结果"""
    evaluation_id: str
    task_id: Optional[str]
    report_content: str
    source_data: Optional[str]
    dimensions: List[DimensionScore] = field(default_factory=list)
    overall_score: float = 0.0
    summary: str = ""
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "task_id": self.task_id,
            "overall_score": round(self.overall_score, 2),
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "score": d.score,
                    "weight": d.weight,
                    "weighted_score": round(d.weighted_score, 2),
                    "reasoning": d.reasoning,
                    "deductions": d.deductions,
                    "suggestions": d.suggestions,
                }
                for d in self.dimensions
            ],
            "summary": self.summary,
            "evaluated_at": self.evaluated_at,
            "metadata": self.metadata,
        }


class EvaluationPrompts:
    """评测 Prompt 模板库"""

    SOURCE_CONSISTENCY = """你是一位专业的信息验证专家。请评估以下研究报告与其原始数据源的一致性。

## 评分标准（0-10分）：
- 10分：报告中的所有事实、数据、引用均与原始数据源完全一致，无任何偏差
- 7-9分：大部分信息与数据源一致，存在少量不重要的偏差或遗漏
- 4-6分：部分信息与数据源不一致，存在明显的事实错误或数据偏差
- 1-3分：大量信息与数据源不符，存在严重的事实扭曲或虚构
- 0分：报告内容与数据源完全不符

## 扣分项：
- 数据与原始来源不一致（-2分/处）
- 引用不存在于原始数据中（-1.5分/处）
- 事实陈述与数据源矛盾（-2分/处）
- 遗漏关键数据点（-1分/处）
- 数据解读错误（-1分/处）

## 原始数据源：
{source_data}

## 研究报告：
{report_content}

请输出JSON格式：
{{
    "score": float,
    "reasoning": "详细评分理由",
    "deductions": ["扣分点1", "扣分点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}"""

    LOGICAL_RIGOR = """你是一位逻辑学教授。请评估以下研究报告的论证逻辑严密性。

## 评分标准（0-10分）：
- 10分：论证结构完美，前提充分，推理无懈可击，结论必然成立
- 7-9分：论证基本合理，逻辑链条完整，存在少量可改进之处
- 4-6分：论证存在明显逻辑漏洞，推理过程不够严谨
- 1-3分：逻辑混乱，存在大量逻辑谬误，结论缺乏支撑
- 0分：完全无逻辑可言

## 评估维度：
1. 论证结构：是否有清晰的前提-推理-结论结构
2. 因果推理：因果关系是否成立，是否存在虚假因果
3. 归纳演绎：归纳是否充分，演绎是否有效
4. 一致性：全文论证是否自相矛盾
5. 证据支撑：论点是否有充分证据支持
6. 排除他因：是否考虑了其他可能的解释

## 扣分项：
- 逻辑谬误（如滑坡谬误、稻草人、虚假两难等）（-2分/处）
- 因果关系不成立（-1.5分/处）
- 证据不足以支撑论点（-1分/处）
- 论证自相矛盾（-2分/处）
- 遗漏关键前提（-1分/处）

## 研究报告：
{report_content}

请输出JSON格式：
{{
    "score": float,
    "reasoning": "详细评分理由",
    "deductions": ["扣分点1", "扣分点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}"""

    ACCURACY = """你是一位领域专家。请评估以下研究报告的事实准确性。

## 评分标准（0-10分）：
- 10分：所有事实陈述均准确无误
- 7-9分：存在少量不重要的错误
- 4-6分：存在若干明显的事实错误
- 1-3分：大量事实错误，可信度低
- 0分：完全不可信

## 扣分项：
- 事实性错误（-2分/处）
- 数据错误（-1.5分/处）
- 日期/时间错误（-1分/处）
- 人名/机构名错误（-1分/处）
- 概念混淆（-1.5分/处）

## 研究报告：
{report_content}

请输出JSON格式：
{{
    "score": float,
    "reasoning": "详细评分理由",
    "deductions": ["扣分点1", "扣分点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}"""

    COMPLETENESS = """你是一位内容审核专家。请评估以下研究报告的完整性。

## 评分标准（0-10分）：
- 10分：内容全面，覆盖了主题的所有关键方面
- 7-9分：覆盖了大部分关键方面，存在少量遗漏
- 4-6分：遗漏了若干重要方面
- 1-3分：大量关键内容缺失
- 0分：内容极度不完整

## 评估维度：
1. 主题覆盖：是否覆盖了研究主题的所有关键维度
2. 深度：每个维度的分析是否充分
3. 背景：是否提供了足够的背景信息
4. 结论：结论是否基于完整分析得出
5. 建议：是否提供了可行的建议

## 研究报告：
{report_content}

请输出JSON格式：
{{
    "score": float,
    "reasoning": "详细评分理由",
    "deductions": ["扣分点1", "扣分点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}"""

    CITATION_QUALITY = """你是一位学术规范专家。请评估以下研究报告的引用质量。

## 评分标准（0-10分）：
- 10分：引用规范、来源可靠、标注完整
- 7-9分：引用基本规范，存在少量问题
- 4-6分：引用存在明显问题
- 1-3分：引用质量差
- 0分：无引用或引用完全不规范

## 评估维度：
1. 引用完整性：是否有完整的来源信息
2. 来源可靠性：引用来源是否权威可靠
3. 引用准确性：引用内容是否与原文一致
4. 引用格式：引用格式是否规范统一
5. 引用密度：关键论点是否有引用支撑

## 扣分项：
- 引用信息不完整（-1分/处）
- 来源不可靠（-1.5分/处）
- 引用与原文不符（-2分/处）
- 格式不规范（-0.5分/处）
- 关键论点无引用（-1分/处）

## 研究报告：
{report_content}

请输出JSON格式：
{{
    "score": float,
    "reasoning": "详细评分理由",
    "deductions": ["扣分点1", "扣分点2"],
    "suggestions": ["改进建议1", "改进建议2"]
}}"""


class LLMJudgeEvaluator:
    """
    LLM-as-a-Judge 评测器

    使用 LLM 对 Agent 生成的报告进行多维度自动化评测。
    """

    # 默认维度配置
    DEFAULT_DIMENSIONS = {
        EvaluationDimension.SOURCE_CONSISTENCY: {
            "weight": 0.25,
            "prompt": EvaluationPrompts.SOURCE_CONSISTENCY,
            "requires_source": True,
        },
        EvaluationDimension.LOGICAL_RIGOR: {
            "weight": 0.25,
            "prompt": EvaluationPrompts.LOGICAL_RIGOR,
            "requires_source": False,
        },
        EvaluationDimension.ACCURACY: {
            "weight": 0.15,
            "prompt": EvaluationPrompts.ACCURACY,
            "requires_source": False,
        },
        EvaluationDimension.COMPLETENESS: {
            "weight": 0.15,
            "prompt": EvaluationPrompts.COMPLETENESS,
            "requires_source": False,
        },
        EvaluationDimension.CITATION_QUALITY: {
            "weight": 0.20,
            "prompt": EvaluationPrompts.CITATION_QUALITY,
            "requires_source": False,
        },
    }

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        dimensions: Optional[Dict[EvaluationDimension, Dict[str, Any]]] = None,
    ):
        self.model = model or llm_config.model or "deepseek-chat"
        self.temperature = temperature
        self.dimensions = dimensions or self.DEFAULT_DIMENSIONS.copy()

        self._llm = ChatOpenAI(
            model=self.model,
            base_url=llm_config.base_url,
            api_key=llm_config.api_key,
            temperature=temperature,
            max_tokens=4096,
        )

    def evaluate(
        self,
        report_content: str,
        source_data: Optional[str] = None,
        task_id: Optional[str] = None,
        dimensions: Optional[List[EvaluationDimension]] = None,
    ) -> EvaluationResult:
        """
        执行完整评测

        Args:
            report_content: 待评测的研究报告内容
            source_data: 原始数据源（用于信源一致性评测）
            task_id: 关联的任务ID
            dimensions: 指定评测维度，None则评测所有配置维度

        Returns:
            EvaluationResult: 完整评测结果
        """
        import uuid

        evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"
        eval_dimensions = dimensions or list(self.dimensions.keys())

        result = EvaluationResult(
            evaluation_id=evaluation_id,
            task_id=task_id,
            report_content=report_content[:5000],  # 限制长度
            source_data=source_data,
        )

        logger.info(f"Starting evaluation {evaluation_id} for task {task_id}")

        for dim in eval_dimensions:
            if dim not in self.dimensions:
                logger.warning(f"Dimension {dim} not configured, skipping")
                continue

            config = self.dimensions[dim]

            # 检查是否需要源数据
            if config.get("requires_source") and not source_data:
                logger.warning(f"Dimension {dim} requires source data but none provided, skipping")
                continue

            try:
                dim_score = self._evaluate_dimension(
                    dimension=dim,
                    report_content=report_content,
                    source_data=source_data,
                    config=config,
                )
                result.dimensions.append(dim_score)
                logger.info(f"Dimension {dim.value}: score={dim_score.score}")

            except Exception as e:
                logger.error(f"Failed to evaluate dimension {dim.value}: {e}")
                result.dimensions.append(DimensionScore(
                    dimension=dim.value,
                    score=0.0,
                    weight=config.get("weight", 1.0),
                    reasoning=f"评测失败: {str(e)}",
                ))

        # 计算总分
        total_weight = sum(d.weight for d in result.dimensions)
        if total_weight > 0:
            result.overall_score = sum(d.weighted_score for d in result.dimensions) / total_weight

        # 生成总结
        result.summary = self._generate_summary(result)

        # 上报 Langfuse
        self._report_to_langfuse(result)

        logger.info(f"Evaluation {evaluation_id} completed: overall_score={result.overall_score:.2f}")
        return result

    def _evaluate_dimension(
        self,
        dimension: EvaluationDimension,
        report_content: str,
        source_data: Optional[str],
        config: Dict[str, Any],
    ) -> DimensionScore:
        """评测单个维度"""
        prompt_template = config["prompt"]

        # 填充模板
        prompt_text = prompt_template.format(
            report_content=report_content[:8000],
            source_data=source_data[:8000] if source_data else "未提供原始数据源",
        )

        messages = [
            SystemMessage(content="你是一位专业的评测专家。请严格按照评分标准进行评估，只输出JSON格式结果。"),
            HumanMessage(content=prompt_text),
        ]

        response = self._llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)

        # 解析 JSON
        parsed = self._parse_json_response(content)

        return DimensionScore(
            dimension=dimension.value,
            score=float(parsed.get("score", 0)),
            weight=config.get("weight", 1.0),
            reasoning=parsed.get("reasoning", ""),
            deductions=parsed.get("deductions", []),
            suggestions=parsed.get("suggestions", []),
        )

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 代码块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取花括号内容
        brace_match = re.search(r'\{[\s\S]*\}', content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse JSON from response: {content[:200]}")
        return {"score": 0, "reasoning": "解析失败", "deductions": [], "suggestions": []}

    def _generate_summary(self, result: EvaluationResult) -> str:
        """生成评测总结"""
        lines = [
            f"## 评测总结",
            f"",
            f"**综合得分**: {result.overall_score:.2f}/10",
            f"",
            f"### 各维度得分",
        ]

        for dim in result.dimensions:
            lines.append(f"- **{dim.dimension}**: {dim.score:.2f}/10 (权重: {dim.weight})")

        lines.extend(["", "### 主要问题"])
        all_deductions = []
        for dim in result.dimensions:
            all_deductions.extend([f"[{dim.dimension}] {d}" for d in dim.deductions])

        if all_deductions:
            for d in all_deductions[:10]:
                lines.append(f"- {d}")
        else:
            lines.append("- 未发现明显问题")

        lines.extend(["", "### 改进建议"])
        all_suggestions = []
        for dim in result.dimensions:
            all_suggestions.extend([f"[{dim.dimension}] {s}" for s in dim.suggestions])

        if all_suggestions:
            for s in all_suggestions[:10]:
                lines.append(f"- {s}")
        else:
            lines.append("- 无特别建议")

        return "\n".join(lines)

    def _report_to_langfuse(self, result: EvaluationResult) -> None:
        """将评测结果上报 Langfuse"""
        try:
            langfuse = get_langfuse_client()
            if not langfuse or not langfuse.client:
                return

            # 为每个维度创建评分
            for dim in result.dimensions:
                langfuse.score_trace(
                    trace_id=result.task_id or result.evaluation_id,
                    name=f"eval_{dim.dimension}",
                    value=dim.score,
                    comment=dim.reasoning[:500],
                )

            # 总评分
            langfuse.score_trace(
                trace_id=result.task_id or result.evaluation_id,
                name="eval_overall",
                value=result.overall_score,
                comment=result.summary[:500],
            )

        except Exception as e:
            logger.error(f"Failed to report evaluation to Langfuse: {e}")

    def add_dimension(
        self,
        dimension: EvaluationDimension,
        weight: float,
        prompt_template: str,
        requires_source: bool = False,
    ) -> None:
        """添加自定义评测维度"""
        self.dimensions[dimension] = {
            "weight": weight,
            "prompt": prompt_template,
            "requires_source": requires_source,
        }
        logger.info(f"Added evaluation dimension: {dimension.value} (weight={weight})")

    def batch_evaluate(
        self,
        reports: List[Dict[str, Any]],
    ) -> List[EvaluationResult]:
        """
        批量评测

        Args:
            reports: 报告列表，每项包含 report_content, source_data, task_id

        Returns:
            List[EvaluationResult]: 评测结果列表
        """
        results = []
        for i, report in enumerate(reports):
            logger.info(f"Batch evaluating {i+1}/{len(reports)}")
            try:
                result = self.evaluate(
                    report_content=report["report_content"],
                    source_data=report.get("source_data"),
                    task_id=report.get("task_id"),
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate report {i+1}: {e}")
                results.append(EvaluationResult(
                    evaluation_id=f"eval_error_{i}",
                    task_id=report.get("task_id"),
                    report_content=report.get("report_content", "")[:100],
                    overall_score=0.0,
                    summary=f"评测失败: {str(e)}",
                ))

        return results