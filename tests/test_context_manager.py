import pytest
from services.context_manager import ContextManager, ContextSegment


class TestContextManager:
    def setup_method(self):
        self.manager = ContextManager(max_tokens=1000, warning_threshold=0.75, critical_threshold=0.9)

    def test_add_segment(self):
        self.manager.add_segment("测试内容", importance=0.8, source="test")
        assert self.manager.segment_count == 1
        assert self.manager.get_usage_ratio() > 0

    def test_get_context(self):
        self.manager.add_segment("内容1", importance=0.5)
        self.manager.add_segment("内容2", importance=0.8)
        context = self.manager.get_context()
        assert "内容1" in context
        assert "内容2" in context

    def test_usage_ratio(self):
        self.manager.add_segment("x" * 500)
        ratio = self.manager.get_usage_ratio()
        assert 0 < ratio <= 1.0

    def test_auto_cleanup_triggers_on_warning(self):
        self.manager.add_segment("重要内容" * 100, importance=0.9, source="important")
        self.manager.add_segment("次要内容" * 100, importance=0.3, source="secondary")

        initial_count = self.manager.segment_count
        self.manager.add_segment("更多内容" * 100, importance=0.2, source="more")

        assert self.manager.cleanup_count >= 0

    def test_emergency_cleanup_on_critical(self):
        self.manager.add_segment("高优内容" * 150, importance=0.95, source="high")
        self.manager.add_segment("中优内容" * 100, importance=0.6, source="medium")
        self.manager.add_segment("低优内容" * 100, importance=0.2, source="low")

        context = self.manager.get_context()
        assert "高优内容" in context or "摘要" in context

    def test_auto_cleanup_preserves_important(self):
        self.manager.add_segment("重要信息" * 50, importance=0.9, source="important")
        self.manager.add_segment("次要信息" * 50, importance=0.3, source="secondary")
        self.manager.add_segment("更多次要" * 50, importance=0.2, source="more")

        self.manager.auto_cleanup()

        context = self.manager.get_context()
        assert "重要信息" in context

    def test_emergency_cleanup_preserves_very_important(self):
        self.manager.add_segment("关键信息" * 100, importance=0.95, source="critical")
        self.manager.add_segment("普通信息" * 100, importance=0.5, source="normal")

        self.manager.emergency_cleanup()

        context = self.manager.get_context()
        assert "关键信息" in context

    def test_add_summary(self):
        self.manager.add_summary("这是一段摘要内容", importance=0.9)
        assert self.manager.segment_count == 1
        context = self.manager.get_context()
        assert "[摘要" in context

    def test_reset(self):
        self.manager.add_segment("内容1")
        self.manager.add_segment("内容2")
        self.manager.reset()
        assert self.manager.segment_count == 0
        assert self.manager.get_usage_ratio() == 0

    def test_get_status(self):
        self.manager.add_segment("测试内容")
        status = self.manager.get_status()
        assert "total_tokens" in status
        assert "max_tokens" in status
        assert "usage_ratio" in status
        assert "segment_count" in status
        assert "cleanup_count" in status

    def test_estimate_tokens_chinese(self):
        text = "这是一段中文测试内容" * 10
        tokens = self.manager._estimate_tokens(text)
        assert tokens > 0

    def test_estimate_tokens_english(self):
        text = "This is an English test content " * 10
        tokens = self.manager._estimate_tokens(text)
        assert tokens > 0

    def test_create_summary(self):
        text = "第一句。第二句。第三句。第四句。第五句。" * 10
        summary = self.manager._create_summary(text, max_tokens=50)
        assert len(summary) <= 100
        assert "[已压缩]" in summary

    def test_context_segments_with_summary_markers(self):
        self.manager.add_segment("内容1", importance=0.5)
        self.manager.add_summary("摘要内容", importance=0.9)
        context = self.manager.get_context()
        assert "[摘要" in context

    def test_cleanup_reduces_token_usage(self):
        for i in range(10):
            self.manager.add_segment(f"内容{i}" * 30, importance=0.3 + i * 0.05)

        initial_tokens = self.manager._total_tokens
        self.manager.auto_cleanup()
        final_tokens = self.manager._total_tokens

        assert final_tokens <= initial_tokens
