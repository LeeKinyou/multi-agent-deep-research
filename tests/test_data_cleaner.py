import pytest
from services.data_cleaner import ContentCleaner, ContentCache, CleanedContent


class TestContentCleaner:
    def setup_method(self):
        self.cleaner = ContentCleaner(max_chars=500, min_word_count=10)

    def test_clean_basic_text(self):
        text = "这是一段测试文本。" * 20
        result = self.cleaner.clean(text, url="http://test.com")
        assert result.text
        assert result.url == "http://test.com"
        assert result.word_count > 0
        assert result.char_count > 0

    def test_clean_removes_noise(self):
        text = """
        <!-- 注释内容 -->
        [广告]
        【推广】
        
        
        这是主要内容。
        """ * 5
        result = self.cleaner.clean(text)
        assert "<!--" not in result.text
        assert "[" not in result.text
        assert "【" not in result.text

    def test_clean_normalizes_whitespace(self):
        text = "line1\n\n\n\nline2\n\nline3"
        result = self.cleaner.clean(text)
        assert "\n\n\n" not in result.text

    def test_clean_removes_duplicate_lines(self):
        text = ("重复行\n" * 10) + ("不重复的内容行\n" * 10)
        result = self.cleaner.clean(text)
        assert result.text
        assert result.text.count("重复行") == 1

    def test_clean_detects_duplicates(self):
        text1 = "这是一段足够长的测试文本内容。" * 5
        text2 = "这是一段足够长的测试文本内容。" * 5
        
        result1 = self.cleaner.clean(text1)
        result2 = self.cleaner.clean(text2)
        
        assert result1.text
        assert not result2.text

    def test_clean_filters_short_content(self):
        text = "短文本"
        result = self.cleaner.clean(text)
        assert not result.text

    def test_clean_truncates_long_content(self):
        text = "这是一段很长的测试文本。" * 100
        result = self.cleaner.clean(text)
        assert result.text
        assert len(result.text) <= 500 + len("\n\n[内容已截断...]")
        assert "[内容已截断...]" in result.text

    def test_clean_calculates_relevance(self):
        text = "根据2024年数据分析报告，统计数据显示..." * 5
        result = self.cleaner.clean(text, title="数据分析")
        assert result.relevance_score > 0

    def test_clean_resets_seen_hashes(self):
        text = "这是一段足够长的测试文本内容。" * 5
        result1 = self.cleaner.clean(text)
        assert result1.text
        
        result2 = self.cleaner.clean(text)
        assert not result2.text
        
        self.cleaner.reset_seen()
        result3 = self.cleaner.clean(text)
        assert result3.text


class TestContentCache:
    def setup_method(self):
        self.cache = ContentCache(max_size=3, max_memory_mb=1)

    def test_cache_put_and_get(self):
        content = CleanedContent(url="http://test.com", text="测试内容", word_count=10, char_count=10)
        self.cache.put("key1", content)
        
        retrieved = self.cache.get("key1")
        assert retrieved is not None
        assert retrieved.text == "测试内容"

    def test_cache_returns_none_for_missing_key(self):
        result = self.cache.get("nonexistent")
        assert result is None

    def test_cache_evicts_oldest_when_full(self):
        for i in range(5):
            content = CleanedContent(url=f"http://test{i}.com", text=f"内容{i}" * 20, word_count=20, char_count=20)
            self.cache.put(f"key{i}", content)
        
        assert len(self.cache) <= 3
        assert self.cache.get("key0") is None

    def test_cache_evicts_when_memory_exceeded(self):
        self.cache = ContentCache(max_size=100, max_memory_mb=1)
        
        large_text = "x" * 600000
        content1 = CleanedContent(url="http://large1.com", text=large_text, word_count=100, char_count=600000)
        self.cache.put("large1", content1)
        
        content2 = CleanedContent(url="http://large2.com", text=large_text, word_count=100, char_count=600000)
        self.cache.put("large2", content2)
        
        assert len(self.cache) <= 1

    def test_cache_clear(self):
        content = CleanedContent(url="http://test.com", text="测试内容", word_count=10, char_count=10)
        self.cache.put("key1", content)
        self.cache.clear()
        
        assert len(self.cache) == 0
        assert self.cache.memory_usage_mb == 0

    def test_cache_contains(self):
        content = CleanedContent(url="http://test.com", text="测试内容", word_count=10, char_count=10)
        self.cache.put("key1", content)
        
        assert "key1" in self.cache
        assert "key2" not in self.cache

    def test_cache_memory_usage(self):
        content = CleanedContent(url="http://test.com", text="测试内容", word_count=10, char_count=10)
        self.cache.put("key1", content)
        
        assert self.cache.memory_usage_mb > 0

    def test_cache_is_full(self):
        for i in range(3):
            content = CleanedContent(url=f"http://test{i}.com", text=f"内容{i}" * 20, word_count=20, char_count=20)
            self.cache.put(f"key{i}", content)
        
        assert self.cache.is_full

    def test_cache_moves_accessed_to_end(self):
        content1 = CleanedContent(url="http://test1.com", text="内容1" * 20, word_count=20, char_count=20)
        content2 = CleanedContent(url="http://test2.com", text="内容2" * 20, word_count=20, char_count=20)
        content3 = CleanedContent(url="http://test3.com", text="内容3" * 20, word_count=20, char_count=20)
        
        self.cache.put("key1", content1)
        self.cache.put("key2", content2)
        self.cache.put("key3", content3)
        
        self.cache.get("key1")
        
        content4 = CleanedContent(url="http://test4.com", text="内容4" * 20, word_count=20, char_count=20)
        self.cache.put("key4", content4)
        
        assert self.cache.get("key1") is not None
        assert self.cache.get("key2") is None
