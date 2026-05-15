"""
混合路由器模块

功能：
- 根据意图分类结果动态路由到云或本地处理层
- 无缝切换处理模式
- 预加载和缓存策略
- 统一响应处理
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from enum import Enum

from hybrid_computing.intent_classifier import IntentClassifier, IntentType, RoutingDecision, SensitivityLevel
from hybrid_computing.local_processor import LocalProcessor
from hybrid_computing.cloud_processor import CloudProcessor
from hybrid_computing.security_filter import SecurityFilter

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """处理模式"""
    CLOUD = "cloud"
    LOCAL = "local"
    HYBRID = "hybrid"
    FALLBACK = "fallback"


@dataclass
class ProcessingResult:
    """处理结果"""
    response: str
    mode: ProcessingMode
    latency_ms: float
    intent_type: IntentType
    confidence: float
    metadata: Dict[str, Any]


class HybridRouter:
    """
    混合路由器

    核心功能：
    1. 意图识别与路由决策
    2. 动态选择处理层（云/本地）
    3. 无缝切换与缓存
    4. 统一响应格式
    5. 降级与容错机制
    """

    def __init__(
        self,
        local_processor: Optional[LocalProcessor] = None,
        cloud_processor: Optional[CloudProcessor] = None,
        intent_classifier: Optional[IntentClassifier] = None,
        security_filter: Optional[SecurityFilter] = None,
    ):
        self.local_processor = local_processor or LocalProcessor()
        self.cloud_processor = cloud_processor or CloudProcessor()
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.security_filter = security_filter or SecurityFilter()

        self._cache: Dict[str, ProcessingResult] = {}
        self._cache_ttl = 300  # 5分钟缓存
        self._cache_timestamps: Dict[str, float] = {}
        self._mode_switch_latency = 0.0
        self._total_requests = 0
        self._local_requests = 0
        self._cloud_requests = 0

    def process_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        force_mode: Optional[ProcessingMode] = None,
    ) -> ProcessingResult:
        """
        处理用户查询

        Args:
            query: 用户输入
            context: 上下文信息
            force_mode: 强制指定处理模式（用于测试或管理操作）

        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.perf_counter()
        self._total_requests += 1

        # Step 1: 检查缓存
        cache_key = self._generate_cache_key(query, context)
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return cached

        # Step 2: 意图分类（除非强制指定模式）
        if force_mode is None:
            decision = self.intent_classifier.classify(query, context)
        else:
            decision = self._create_decision_for_force_mode(force_mode, query)

        # Step 3: 安全检查
        if not decision.route_to_local:
            safe, reason = self.security_filter.can_send_to_cloud(query)
            if not safe:
                logger.warning(f"Cloud routing blocked: {reason}")
                decision.route_to_local = True
                decision.sensitivity = SensitivityLevel.INTERNAL
                decision.reasoning = f"安全检查拦截: {reason}"

        # Step 4: 路由到对应处理层
        try:
            if decision.route_to_local:
                result = self._process_local(query, decision, context)
                self._local_requests += 1
            else:
                result = self._process_cloud(query, decision, context)
                self._cloud_requests += 1

        except Exception as e:
            logger.error(f"Processing failed: {e}, falling back to local")
            result = self._process_fallback(query, decision, context, str(e))

        # Step 5: 计算延迟并缓存
        latency_ms = (time.perf_counter() - start_time) * 1000
        result.latency_ms = latency_ms

        self._set_cache(cache_key, result)

        logger.info(
            f"Query processed: mode={result.mode.value}, "
            f"latency={latency_ms:.0f}ms, intent={result.intent_type.value}"
        )

        return result

    def _process_local(
        self,
        query: str,
        decision: RoutingDecision,
        context: Optional[Dict[str, Any]],
    ) -> ProcessingResult:
        """本地处理"""
        response = self.local_processor.process(query, context)
        return ProcessingResult(
            response=response,
            mode=ProcessingMode.LOCAL,
            latency_ms=0.0,  # 将在调用方计算
            intent_type=decision.intent_type,
            confidence=decision.confidence,
            metadata={
                "sensitivity": decision.sensitivity.value,
                "reasoning": decision.reasoning,
            },
        )

    def _process_cloud(
        self,
        query: str,
        decision: RoutingDecision,
        context: Optional[Dict[str, Any]],
    ) -> ProcessingResult:
        """云端处理（带脱敏）"""
        sanitized = self.intent_classifier.sanitize_query(query)
        response = self.cloud_processor.process(sanitized, context)
        return ProcessingResult(
            response=response,
            mode=ProcessingMode.CLOUD,
            latency_ms=0.0,
            intent_type=decision.intent_type,
            confidence=decision.confidence,
            metadata={
                "original_query_sanitized": sanitized != query,
                "reasoning": decision.reasoning,
            },
        )

    def _process_fallback(
        self,
        query: str,
        decision: RoutingDecision,
        context: Optional[Dict[str, Any]],
        error: str,
    ) -> ProcessingResult:
        """降级处理（始终使用本地）"""
        response = self.local_processor.process(query, context)
        return ProcessingResult(
            response=response,
            mode=ProcessingMode.FALLBACK,
            latency_ms=0.0,
            intent_type=decision.intent_type,
            confidence=decision.confidence,
            metadata={
                "error": error,
                "fallback_reason": "处理失败，降级为本地处理",
            },
        )

    def _create_decision_for_force_mode(
        self,
        mode: ProcessingMode,
        query: str,
    ) -> RoutingDecision:
        """为强制模式创建路由决策"""
        return RoutingDecision(
            intent_type=IntentType.GENERAL_QUERY,
            sensitivity=SensitivityLevel.PUBLIC if mode == ProcessingMode.CLOUD else SensitivityLevel.INTERNAL,
            route_to_local=mode != ProcessingMode.CLOUD,
            confidence=1.0,
            reasoning=f"强制模式: {mode.value}",
        )

    def _generate_cache_key(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """生成缓存键"""
        import hashlib
        key_base = query.lower().strip()
        if context:
            key_base += str(sorted(context.items()))
        return hashlib.md5(key_base.encode()).hexdigest()

    def _get_cached(self, cache_key: str) -> Optional[ProcessingResult]:
        """获取缓存结果"""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self._cache_ttl:
                return self._cache[cache_key]
            else:
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: ProcessingResult) -> None:
        """设置缓存"""
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """获取路由器统计信息"""
        return {
            "total_requests": self._total_requests,
            "local_requests": self._local_requests,
            "cloud_requests": self._cloud_requests,
            "local_ratio": round(self._local_requests / max(self._total_requests, 1) * 100, 1),
            "cloud_ratio": round(self._cloud_requests / max(self._total_requests, 1) * 100, 1),
            "cache_size": len(self._cache),
            "cache_ttl_seconds": self._cache_ttl,
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()

    def update_cache_ttl(self, ttl_seconds: int) -> None:
        """更新缓存 TTL"""
        self._cache_ttl = ttl_seconds
