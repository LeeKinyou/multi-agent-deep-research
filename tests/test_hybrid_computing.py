"""
混合计算架构单元测试
"""

import pytest
from unittest.mock import Mock, patch

from hybrid_computing.intent_classifier import IntentClassifier, IntentType, RoutingDecision, SensitivityLevel
from hybrid_computing.security_filter import SecurityFilter, DataClassifier, DataType
from hybrid_computing.router import HybridRouter, ProcessingMode
from hybrid_computing.local_knowledge_base import LocalKnowledgeBase


class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_sensitive_data_detection(self):
        decision = self.classifier.classify("核心流程参数是什么？")
        assert decision.route_to_local is True
        assert decision.sensitivity in [SensitivityLevel.CONFIDENTIAL, SensitivityLevel.INTERNAL]

    def test_general_chat_detection(self):
        decision = self.classifier.classify("你好，在吗？")
        assert decision.route_to_local is False

    def test_creative_writing_detection(self):
        decision = self.classifier.classify("写一首关于春天的诗歌")
        assert decision.route_to_local is False

    def test_internal_metrics_detection(self):
        decision = self.classifier.classify("内部销售数据如何？")
        assert decision.route_to_local is True

    def test_marketing_data_detection(self):
        decision = self.classifier.classify("营销方案和推广计划")
        assert decision.route_to_local is True

    def test_sanitization(self):
        query = "我的密码是 abc123，请帮我查询"
        sanitized = self.classifier.sanitize_query(query)
        assert "密码" not in sanitized or "abc123" not in sanitized or "[REDACTED]" in sanitized

    def test_confidence_threshold(self):
        classifier = IntentClassifier(confidence_threshold=0.9)
        decision = classifier.classify("核心流程")
        assert decision.confidence >= 0.8

    def test_ambiguous_query(self):
        decision = self.classifier.classify("asdfghjkl")
        assert decision is not None

    def test_routing_decision_structure(self):
        decision = RoutingDecision(
            intent_type=IntentType.SENSITIVE_DATA,
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            route_to_local=True,
            confidence=0.9,
            reasoning="test",
        )
        assert decision.requires_human_review is False
        assert decision.route_to_local is True


class TestSecurityFilter:
    def setup_method(self):
        self.filter = SecurityFilter(strict_mode=True)

    def test_confidential_data_detection(self):
        result = self.filter.classify_data("银行卡号 6222021234567890")
        assert result.data_type == DataType.CONFIDENTIAL

    def test_id_card_detection(self):
        result = self.filter.classify_data("身份证号 110101199001011234")
        assert result.data_type == DataType.CONFIDENTIAL

    def test_api_key_detection(self):
        result = self.filter.classify_data("API密钥：sk-abc123def456ghi789jkl")
        assert result.data_type == DataType.CONFIDENTIAL

    def test_internal_data_detection(self):
        result = self.filter.classify_data("本月营收 500 万元")
        assert result.data_type == DataType.INTERNAL

    def test_public_data(self):
        result = self.filter.classify_data("今天天气很好")
        assert result.data_type == DataType.PUBLIC

    def test_sanitization_removes_sensitive(self):
        text = "密码：secret123，请帮我处理"
        result = self.filter.sanitize_data(text)
        assert "secret123" not in result.sanitized_text or "[REDACTED]" in result.sanitized_text

    def test_cloud_block_confidential(self):
        can_send, reason = self.filter.can_send_to_cloud("银行卡号 6222021234567890")
        assert can_send is False

    def test_cloud_block_internal_strict(self):
        can_send, reason = self.filter.can_send_to_cloud("内部营收数据")
        assert can_send is False

    def test_cloud_allow_public(self):
        can_send, reason = self.filter.can_send_to_cloud("今天天气怎么样")
        assert can_send is True

    def test_audit_log_records_actions(self):
        self.filter.classify_data("测试数据")
        self.filter.sanitize_data("密码：test")
        log = self.filter.get_audit_log()
        assert len(log) >= 2

    def test_data_classifier_singleton(self):
        c1 = DataClassifier()
        c2 = DataClassifier()
        assert c1 is c2


class TestHybridRouter:
    def setup_method(self):
        self.router = HybridRouter()

    def test_local_routing_for_sensitive(self):
        result = self.router.process_query("核心流程参数")
        assert result.mode in [ProcessingMode.LOCAL, ProcessingMode.FALLBACK]

    def test_force_cloud_mode(self):
        result = self.router.process_query("测试", force_mode=ProcessingMode.CLOUD)
        assert result.mode in [ProcessingMode.CLOUD, ProcessingMode.FALLBACK]

    def test_force_local_mode(self):
        result = self.router.process_query("测试", force_mode=ProcessingMode.LOCAL)
        assert result.mode in [ProcessingMode.LOCAL, ProcessingMode.FALLBACK]

    def test_cache_hit(self):
        query = "缓存测试查询"
        r1 = self.router.process_query(query, force_mode=ProcessingMode.LOCAL)
        r2 = self.router.process_query(query, force_mode=ProcessingMode.LOCAL)
        assert r1.response == r2.response

    def test_stats_tracking(self):
        self.router.process_query("测试1", force_mode=ProcessingMode.LOCAL)
        self.router.process_query("测试2", force_mode=ProcessingMode.CLOUD)
        stats = self.router.get_stats()
        assert stats["total_requests"] >= 2

    def test_cache_clear(self):
        self.router.process_query("清除缓存测试", force_mode=ProcessingMode.LOCAL)
        self.router.clear_cache()
        assert len(self.router._cache) == 0


class TestLocalKnowledgeBase:
    def setup_method(self):
        self.kb = LocalKnowledgeBase(enable_vector_search=False)

    def test_add_document(self):
        doc_id = self.kb.add_document(
            title="测试文档",
            content="这是测试内容",
            metadata={"category": "test"},
        )
        assert doc_id is not None
        assert self.kb.get_document_count() >= 1

    def test_search_text(self):
        self.kb.add_document(
            title="销售报告",
            content="本月销售额达到 100 万元，同比增长 20%",
        )
        results = self.kb.search("销售额")
        assert len(results) >= 1

    def test_delete_document(self):
        doc_id = self.kb.add_document(
            title="待删除文档",
            content="这是将要被删除的内容",
        )
        assert self.kb.delete_document(doc_id) is True
        assert self.kb.get_document(doc_id) is None

    def test_list_documents(self):
        self.kb.add_document(title="文档1", content="内容1")
        self.kb.add_document(title="文档2", content="内容2")
        docs = self.kb.list_documents()
        assert len(docs) >= 2

    def test_document_versioning(self):
        doc_id = self.kb.add_document(title="版本测试", content="版本1")
        self.kb.add_document(title="版本测试", content="版本2", doc_id=doc_id)
        doc = self.kb.get_document(doc_id)
        assert doc.version >= 2
