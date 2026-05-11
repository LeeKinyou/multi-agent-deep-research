import hashlib
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CleanedContent:
    url: str
    title: str = ""
    text: str = ""
    word_count: int = 0
    char_count: int = 0
    relevance_score: float = 0.0
    content_hash: str = ""


class ContentCleaner:
    def __init__(
        self,
        max_chars: int = 2000,
        min_word_count: int = 50,
        max_duplicate_ratio: float = 0.8,
    ):
        self.max_chars = max_chars
        self.min_word_count = min_word_count
        self.max_duplicate_ratio = max_duplicate_ratio
        self._seen_hashes: set = set()

    def _count_words(self, text: str) -> int:
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len([w for w in text.split() if not any('\u4e00' <= c <= '\u9fff' for c in w)])
        return chinese_chars + english_words

    def clean(self, raw_text: str, url: str = "", title: str = "") -> CleanedContent:
        text = self._remove_noise(raw_text)
        text = self._normalize_whitespace(text)
        text = self._remove_duplicates(text)

        word_count = self._count_words(text)
        char_count = len(text)

        if word_count < self.min_word_count:
            logger.info(f"内容过短，跳过: {url} ({word_count}词)")
            return CleanedContent(
                url=url, title=title, text="", word_count=word_count, char_count=char_count
            )

        if self._is_duplicate(text):
            logger.info(f"重复内容，跳过: {url}")
            return CleanedContent(
                url=url, title=title, text="", word_count=word_count, char_count=char_count
            )

        if char_count > self.max_chars:
            text = self._truncate_smart(text, self.max_chars)

        content_hash = self._compute_hash(text)
        self._seen_hashes.add(content_hash)

        relevance = self._calculate_relevance(text, title)

        return CleanedContent(
            url=url,
            title=title,
            text=text,
            word_count=word_count,
            char_count=len(text),
            relevance_score=relevance,
            content_hash=content_hash,
        )

    def _remove_noise(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'【.*?】', '', text)
        return text.strip()

    def _normalize_whitespace(self, text: str) -> str:
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def _remove_duplicates(self, text: str) -> str:
        lines = text.split('\n')
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        return '\n'.join(unique_lines)

    def _is_duplicate(self, text: str) -> bool:
        content_hash = self._compute_hash(text)
        return content_hash in self._seen_hashes

    def _compute_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _truncate_smart(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text

        sentences = re.split(r'(?<=[.!?。！？])\s*', text)
        truncated = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_length + sentence_len + 1 > max_chars:
                break
            truncated.append(sentence)
            current_length += sentence_len + 1

        result = ' '.join(truncated)
        if len(result) < len(text):
            result += "\n\n[内容已截断...]"

        return result[:max_chars + len("\n\n[内容已截断...]")]

    def _calculate_relevance(self, text: str, title: str = "") -> float:
        score = 0.0

        word_count = self._count_words(text)
        if word_count > 200:
            score += 0.3
        elif word_count > 100:
            score += 0.2
        elif word_count > 50:
            score += 0.1

        if title:
            title_words = set(title.lower().split())
            text_words = set(text.lower().split())
            if title_words & text_words:
                score += 0.3

        if any(keyword in text.lower() for keyword in ['数据', '分析', '报告', '研究', '统计', '数据', 'data', 'analysis', 'report']):
            score += 0.2

        if re.search(r'\d{4}年', text):
            score += 0.1

        if len(text.split('\n')) > 5:
            score += 0.1

        return min(score, 1.0)

    def reset_seen(self):
        self._seen_hashes.clear()


class ContentCache:
    def __init__(
        self,
        max_size: int = 100,
        max_memory_mb: int = 50,
    ):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, CleanedContent] = OrderedDict()
        self._current_memory: int = 0

    def get(self, key: str) -> Optional[CleanedContent]:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, content: CleanedContent):
        if key in self._cache:
            self._cache.move_to_end(key)
            old_content = self._cache[key]
            self._current_memory -= len(old_content.text.encode('utf-8'))

        content_size = len(content.text.encode('utf-8'))

        while self._current_memory + content_size > self.max_memory_bytes and self._cache:
            self._cache.popitem(last=False)
            self._current_memory -= content_size

        while len(self._cache) >= self.max_size and self._cache:
            self._cache.popitem(last=False)

        self._cache[key] = content
        self._current_memory += content_size

    def clear(self):
        self._cache.clear()
        self._current_memory = 0

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    @property
    def memory_usage_mb(self) -> float:
        return self._current_memory / (1024 * 1024)

    @property
    def is_full(self) -> bool:
        return len(self._cache) >= self.max_size or self._current_memory >= self.max_memory_bytes
