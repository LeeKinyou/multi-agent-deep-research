"""
混合计算架构模块 - 云/本地协同处理

提供企业级多模态交互系统的核心能力：
- 意图识别与动态路由
- 云处理层（通用交互）
- 本地处理层（敏感数据处理）
- 无缝路由切换
- 本地 RAG 知识库
- 安全边界控制
"""

from hybrid_computing.intent_classifier import IntentClassifier, IntentType, RoutingDecision
from hybrid_computing.router import HybridRouter
from hybrid_computing.local_processor import LocalProcessor
from hybrid_computing.cloud_processor import CloudProcessor
from hybrid_computing.local_knowledge_base import LocalKnowledgeBase
from hybrid_computing.security_filter import SecurityFilter, DataClassifier

__all__ = [
    "IntentClassifier",
    "IntentType",
    "RoutingDecision",
    "HybridRouter",
    "LocalProcessor",
    "CloudProcessor",
    "LocalKnowledgeBase",
    "SecurityFilter",
    "DataClassifier",
]
