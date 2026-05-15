"""
安全过滤器模块

功能：
- 数据分类（识别敏感数据类型）
- 数据脱敏（移除/替换敏感信息）
- 传输安全检查（确保敏感数据不上云）
- 安全审计日志
"""

import re
import logging
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class DataType(Enum):
    """数据类型"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class DataClassification:
    """数据分类结果"""
    data_type: DataType
    confidence: float
    detected_patterns: List[str]
    risk_level: str  # low, medium, high, critical


@dataclass
class SanitizationResult:
    """脱敏结果"""
    original_hash: str
    sanitized_text: str
    removed_items: List[str]
    risk_assessed: bool


# 敏感数据模式定义
SENSITIVE_DATA_PATTERNS = {
    DataType.CONFIDENTIAL: [
        (r"\b\d{15,19}\b", "银行卡号"),
        (r"\b\d{18}[\dXx]\b", "身份证号"),
        (r"(?:密码|密钥|password|secret|token|api[_\-]?key)\s*[:：\s]\s*\S+", "凭证信息"),
        (r"(?:sk|pk|rk)-[a-zA-Z0-9]{20,}", "API密钥"),
        (r"\b(?:0x)?[a-fA-F0-9]{40,}\b", "加密哈希/私钥"),
    ],
    DataType.INTERNAL: [
        (r"(?:营收|收入|利润|成本|毛利率|净利率)\s*[:：]?\s*\d+", "财务数据"),
        (r"(?:客户|用户)\s*(?:数量|列表|名单)\s*[:：]?\s*\d+", "客户数据"),
        (r"(?:销售|销量)\s*(?:额|量)\s*[:：]?\s*\d+", "销售数据"),
        (r"(?:转化率|留存率|复购率)\s*[:：]?\s*\d+\.?\d*%", "运营指标"),
        (r"(?:薪资|工资|奖金)\s*[:：]?\s*\d+", "薪酬数据"),
        (r"内部(?:营收|销售|客户|数据|指标|报告|计划|策略)", "内部业务数据"),
        (r"(?:营销|推广|策略|计划)\s*(?:方案|数据|计划)", "营销数据"),
    ],
}


class SecurityFilter:
    """
    安全过滤器

    提供：
    1. 数据分类：识别文本中的敏感数据类型
    2. 数据脱敏：移除或替换敏感信息
    3. 传输检查：验证数据是否可以安全传输到云端
    4. 审计日志：记录所有安全相关操作
    """

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._audit_log: List[Dict[str, Any]] = []
        self._compiled_patterns: Dict[DataType, List[Tuple[re.Pattern, str]]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """预编译正则表达式"""
        for data_type, patterns in SENSITIVE_DATA_PATTERNS.items():
            self._compiled_patterns[data_type] = [
                (re.compile(pattern, re.IGNORECASE), desc)
                for pattern, desc in patterns
            ]

    def classify_data(self, text: str) -> DataClassification:
        """
        对数据进行分类

        Args:
            text: 待分类的文本

        Returns:
            DataClassification: 分类结果
        """
        detected = []
        highest_type = DataType.PUBLIC
        max_confidence = 0.0

        for data_type, patterns in self._compiled_patterns.items():
            for pattern, desc in patterns:
                matches = pattern.findall(text)
                if matches:
                    detected.append(f"{desc}({len(matches)}处)")
                    confidence = min(0.95, 0.7 + len(matches) * 0.1)
                    if confidence > max_confidence:
                        max_confidence = confidence
                        highest_type = data_type

        risk_level = self._calculate_risk(highest_type, len(detected))

        result = DataClassification(
            data_type=highest_type,
            confidence=max_confidence if detected else 0.0,
            detected_patterns=detected,
            risk_level=risk_level,
        )

        self._log_audit("classify", text, result)
        return result

    def sanitize_data(self, text: str) -> SanitizationResult:
        """
        对数据进行脱敏处理

        Args:
            text: 待脱敏的文本

        Returns:
            SanitizationResult: 脱敏结果
        """
        original_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        sanitized = text
        removed = []

        for data_type, patterns in self._compiled_patterns.items():
            for pattern, desc in patterns:
                matches = pattern.findall(sanitized)
                if matches:
                    for match in matches:
                        removed.append(f"{desc}: {match[:20]}...")
                    sanitized = pattern.sub("[REDACTED]", sanitized)

        result = SanitizationResult(
            original_hash=original_hash,
            sanitized_text=sanitized,
            removed_items=removed,
            risk_assessed=len(removed) == 0,
        )

        self._log_audit("sanitize", text, result)
        return result

    def can_send_to_cloud(self, text: str) -> Tuple[bool, str]:
        """
        检查数据是否可以安全发送到云端

        Args:
            text: 待检查的文本

        Returns:
            Tuple[bool, str]: (是否安全, 原因说明)
        """
        classification = self.classify_data(text)

        if classification.data_type == DataType.PUBLIC:
            return True, "数据为公开类型，可安全传输"

        if classification.data_type == DataType.INTERNAL:
            if self.strict_mode:
                return False, f"严格模式下禁止内部数据上云 (检测到: {', '.join(classification.detected_patterns)})"
            sanitized = self.sanitize_data(text)
            if sanitized.risk_assessed:
                return True, "数据已脱敏，可安全传输"
            return False, f"脱敏后仍有风险 (检测到: {', '.join(classification.detected_patterns)})"

        return False, f"禁止{classification.data_type.value}级别数据上云"

    def _calculate_risk(self, data_type: DataType, pattern_count: int) -> str:
        """计算风险级别"""
        risk_matrix = {
            DataType.PUBLIC: "low",
            DataType.INTERNAL: "medium" if pattern_count <= 2 else "high",
            DataType.CONFIDENTIAL: "high" if pattern_count <= 1 else "critical",
            DataType.RESTRICTED: "critical",
        }
        return risk_matrix.get(data_type, "medium")

    def _log_audit(
        self,
        action: str,
        original_text: str,
        result: Any,
    ) -> None:
        """记录审计日志"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "text_preview": original_text[:100],
            "result": str(result),
        }
        self._audit_log.append(entry)

        if action == "classify" and hasattr(result, "data_type"):
            if result.data_type != DataType.PUBLIC:
                logger.warning(f"Security audit: {action} - {result}")
        elif action == "sanitize" and hasattr(result, "removed_items"):
            if result.removed_items:
                logger.warning(f"Security audit: {action} - removed {len(result.removed_items)} items")

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self._audit_log[-limit:]

    def clear_audit_log(self) -> None:
        """清空审计日志"""
        self._audit_log.clear()


class DataClassifier:
    """
    数据分类器（便捷封装）

    提供快速数据分类接口，供其他模块调用
    """

    _instance = None

    def __new__(cls, strict_mode: bool = True):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, strict_mode: bool = True):
        if self._initialized:
            return
        self._initialized = True
        self.filter = SecurityFilter(strict_mode=strict_mode)

    def classify(self, text: str) -> DataClassification:
        return self.filter.classify_data(text)

    def sanitize(self, text: str) -> SanitizationResult:
        return self.filter.sanitize_data(text)

    def is_safe_for_cloud(self, text: str) -> Tuple[bool, str]:
        return self.filter.can_send_to_cloud(text)
