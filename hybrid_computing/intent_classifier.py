"""
意图识别与动态路由模块

功能：
- 基于规则 + LLM 的意图分类
- 敏感度级别判定
- 动态路由决策
- 模糊查询人工干预机制
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型"""
    GENERAL_CHAT = "general_chat"           # 通用闲聊
    CREATIVE_WRITING = "creative_writing"    # 创意内容生成
    GENERAL_QUERY = "general_query"          # 通用问题查询
    SENSITIVE_DATA = "sensitive_data"        # 敏感数据处理
    INTERNAL_METRICS = "internal_metrics"    # 内部业务指标
    CORE_PROCESS = "core_process"            # 核心流程参数
    MARKETING_DATA = "marketing_data"        # 营销数据
    AMBIGUOUS = "ambiguous"                  # 模糊查询（需人工干预）


class SensitivityLevel(Enum):
    """敏感度级别"""
    PUBLIC = "public"               # 公开数据，可上云
    INTERNAL = "internal"           # 内部数据，本地处理
    CONFIDENTIAL = "confidential"   # 机密数据，严格本地处理
    RESTRICTED = "restricted"       # 受限数据，禁止处理


@dataclass
class RoutingDecision:
    """路由决策结果"""
    intent_type: IntentType
    sensitivity: SensitivityLevel
    route_to_local: bool
    confidence: float               # 0.0 - 1.0
    reasoning: str
    requires_human_review: bool = False
    original_query: str = ""
    sanitized_query: str = ""       # 脱敏后的查询（用于云端）


# 敏感关键词模式（用于快速规则匹配）
SENSITIVE_PATTERNS = {
    SensitivityLevel.CONFIDENTIAL: [
        r"核心流程", r"工艺参数", r"生产配方", r"源代码", r"密钥",
        r"密码", r"token", r"api.key", r"私钥", r"证书",
        r"财务数据", r"营收", r"利润", r"成本结构",
        r"客户名单", r"供应商", r"合同金额",
    ],
    SensitivityLevel.INTERNAL: [
        r"内部", r"机密", r"保密", r"策略", r"计划",
        r"营销方案", r"推广计划", r"销售数据",
        r"用户画像", r"转化率", r"留存率",
        r"组织架构", r"人事", r"薪酬",
    ],
}

# 通用意图关键词模式
GENERAL_PATTERNS = [
    r"你好", r"hello", r"hi", r"在吗", r"帮忙", r"请问",
    r"写一[篇首个]", r"创作", r"生成", r"翻译",
    r"天气", r"时间", r"日期", r"计算",
    r"什么是", r"如何", r"怎么", r"介绍一下",
]


class IntentClassifier:
    """
    意图识别分类器

    采用规则 + LLM 的混合分类策略：
    1. 规则匹配：快速识别敏感关键词
    2. LLM 分类：处理复杂意图识别
    3. 置信度评估：决定是否需要人工干预
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        ambiguous_threshold: float = 0.5,
    ):
        self.confidence_threshold = confidence_threshold
        self.ambiguous_threshold = ambiguous_threshold
        self._pattern_cache: Dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """预编译正则表达式"""
        for level, patterns in SENSITIVE_PATTERNS.items():
            self._pattern_cache[level.value] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        self._pattern_cache["general"] = [
            re.compile(p, re.IGNORECASE) for p in GENERAL_PATTERNS
        ]

    def classify(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        对查询进行意图分类和路由决策

        Args:
            query: 用户输入查询
            context: 可选的上下文信息（用户角色、历史交互等）

        Returns:
            RoutingDecision: 路由决策结果
        """
        # Step 1: 规则匹配
        rule_result = self._rule_based_classification(query)

        if rule_result and rule_result.confidence >= self.confidence_threshold:
            logger.info(f"Rule-based classification: {rule_result.intent_type.value}")
            return rule_result

        # Step 2: LLM 分类（规则置信度不足时）
        llm_result = self._llm_based_classification(query, context)

        # Step 3: 综合决策
        return self._combine_decisions(rule_result, llm_result, query)

    def _rule_based_classification(
        self,
        query: str,
    ) -> Optional[RoutingDecision]:
        """基于规则的意图分类"""
        # 检查敏感关键词
        for level in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.INTERNAL]:
            patterns = self._pattern_cache.get(level.value, [])
            for pattern in patterns:
                if pattern.search(query):
                    intent_type = self._map_sensitivity_to_intent(level)
                    return RoutingDecision(
                        intent_type=intent_type,
                        sensitivity=level,
                        route_to_local=True,
                        confidence=0.85,
                        reasoning=f"匹配敏感关键词: {pattern.pattern}",
                    )

        # 检查通用意图
        for pattern in self._pattern_cache.get("general", []):
            if pattern.search(query):
                return RoutingDecision(
                    intent_type=IntentType.GENERAL_CHAT,
                    sensitivity=SensitivityLevel.PUBLIC,
                    route_to_local=False,
                    confidence=0.75,
                    reasoning=f"匹配通用意图关键词: {pattern.pattern}",
                )

        return None

    def _llm_based_classification(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """基于 LLM 的意图分类"""
        try:
            from config.settings import llm_config
            llm = llm_config.get_langchain_llm()

            prompt = self._build_classification_prompt(query, context)
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            return self._parse_llm_response(content, query)

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return RoutingDecision(
                intent_type=IntentType.AMBIGUOUS,
                sensitivity=SensitivityLevel.INTERNAL,
                route_to_local=True,
                confidence=0.0,
                reasoning=f"LLM 分类失败，降级为本地处理: {str(e)}",
                requires_human_review=True,
            )

    def _combine_decisions(
        self,
        rule_result: Optional[RoutingDecision],
        llm_result: RoutingDecision,
        query: str,
    ) -> RoutingDecision:
        """综合规则和 LLM 的决策结果"""
        if rule_result is None:
            return llm_result

        # 规则判定为敏感数据时，优先采用规则结果
        if rule_result.sensitivity in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.INTERNAL]:
            return rule_result

        # LLM 置信度更高时采用 LLM 结果
        if llm_result.confidence > rule_result.confidence:
            return llm_result

        # 默认采用规则结果
        return rule_result

    def _map_sensitivity_to_intent(
        self,
        level: SensitivityLevel,
    ) -> IntentType:
        """映射敏感度级别到意图类型"""
        mapping = {
            SensitivityLevel.CONFIDENTIAL: IntentType.SENSITIVE_DATA,
            SensitivityLevel.INTERNAL: IntentType.INTERNAL_METRICS,
        }
        return mapping.get(level, IntentType.AMBIGUOUS)

    def _build_classification_prompt(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建 LLM 分类提示词"""
        context_str = ""
        if context:
            context_str = f"\n上下文信息: {context}"

        return f"""你是一个意图分类器。请分析以下用户查询的意图和敏感度级别。

查询内容: {query}{context_str}

请按以下 JSON 格式返回结果:
{{
    "intent_type": "意图类型",
    "sensitivity_level": "敏感度级别",
    "confidence": 0.0-1.0,
    "reasoning": "分类理由"
}}

意图类型选项:
- general_chat: 通用闲聊（如问候、寒暄）
- creative_writing: 创意内容生成（如写文章、诗歌）
- general_query: 通用问题查询（如天气、知识问答）
- sensitive_data: 敏感数据处理（如核心流程、内部数据）
- internal_metrics: 内部业务指标（如销售数据、用户画像）
- ambiguous: 模糊查询（无法明确分类）

敏感度级别选项:
- public: 公开数据，可安全传输到云端
- internal: 内部数据，建议本地处理
- confidential: 机密数据，必须本地处理
- restricted: 受限数据，禁止处理

注意：
1. 如果查询包含企业核心流程、内部数据、财务信息等，必须判定为敏感数据
2. 如果查询是通用问题或闲聊，判定为公开数据
3. 如果无法明确分类，判定为 ambiguous
"""

    def _parse_llm_response(
        self,
        content: str,
        query: str,
    ) -> RoutingDecision:
        """解析 LLM 返回的分类结果"""
        import json

        try:
            # 尝试提取 JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")

            data = json.loads(content[start:end])

            intent_type = IntentType(data.get("intent_type", "ambiguous"))
            sensitivity = SensitivityLevel(data.get("sensitivity_level", "internal"))
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "")

            return RoutingDecision(
                intent_type=intent_type,
                sensitivity=sensitivity,
                route_to_local=sensitivity != SensitivityLevel.PUBLIC,
                confidence=confidence,
                reasoning=reasoning,
                requires_human_review=intent_type == IntentType.AMBIGUOUS,
            )

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return RoutingDecision(
                intent_type=IntentType.AMBIGUOUS,
                sensitivity=SensitivityLevel.INTERNAL,
                route_to_local=True,
                confidence=0.3,
                reasoning=f"LLM 响应解析失败: {str(e)}",
                requires_human_review=True,
            )

    def sanitize_query(self, query: str) -> str:
        """
        对查询进行脱敏处理（用于云端传输）

        移除可能的敏感信息，保留查询意图
        """
        sanitized = query

        # 移除常见的敏感模式
        sensitive_patterns = [
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # 卡号
            r"\b\d{18}\b",  # 身份证号
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # 邮箱
            r"(密码|密钥|token|key)[:\s]*\S+",  # 密码/密钥
        ]

        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        return sanitized
