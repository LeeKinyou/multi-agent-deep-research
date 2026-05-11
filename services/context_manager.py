import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextSegment:
    content: str
    importance: float = 0.5
    token_estimate: int = 0
    is_summary: bool = False
    source: str = ""


class ContextManager:
    def __init__(
        self,
        max_tokens: int = 8000,
        warning_threshold: float = 0.75,
        critical_threshold: float = 0.9,
    ):
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self._segments: list[ContextSegment] = []
        self._total_tokens: int = 0
        self._cleanup_count: int = 0

    def add_segment(self, content: str, importance: float = 0.5, source: str = ""):
        token_count = self._estimate_tokens(content)
        segment = ContextSegment(
            content=content,
            importance=importance,
            token_estimate=token_count,
            source=source,
        )
        self._segments.append(segment)
        self._total_tokens += token_count

        if self.get_usage_ratio() >= self.warning_threshold:
            logger.info(f"上下文使用率 {self.get_usage_ratio():.1%}，触发自动整理")
            self.auto_cleanup()

    def get_context(self) -> str:
        if self.get_usage_ratio() >= self.critical_threshold:
            logger.warning(f"上下文使用率 {self.get_usage_ratio():.1%}，执行紧急整理")
            self.emergency_cleanup()

        parts = []
        for i, seg in enumerate(self._segments, 1):
            if seg.is_summary:
                parts.append(f"[摘要{i}] {seg.content}")
            else:
                parts.append(seg.content)
        return "\n\n".join(parts)

    def get_usage_ratio(self) -> float:
        if self.max_tokens == 0:
            return 0.0
        return min(self._total_tokens / self.max_tokens, 1.0)

    def auto_cleanup(self):
        if self.get_usage_ratio() < self.warning_threshold:
            return

        self._segments.sort(key=lambda s: s.importance, reverse=True)

        kept_segments = []
        current_tokens = 0
        target_tokens = int(self.max_tokens * 0.6)

        for seg in self._segments:
            if current_tokens + seg.token_estimate <= target_tokens:
                kept_segments.append(seg)
                current_tokens += seg.token_estimate
            else:
                if seg.importance >= 0.7:
                    summary = self._create_summary(seg.content, max_tokens=200)
                    summary_seg = ContextSegment(
                        content=summary,
                        importance=seg.importance,
                        token_estimate=self._estimate_tokens(summary),
                        is_summary=True,
                        source=seg.source,
                    )
                    kept_segments.append(summary_seg)
                    current_tokens += summary_seg.token_estimate

        self._segments = kept_segments
        self._total_tokens = current_tokens
        self._cleanup_count += 1

        logger.info(f"自动整理完成: 保留 {len(self._segments)} 段, 使用率 {self.get_usage_ratio():.1%}")

    def emergency_cleanup(self):
        self._segments.sort(key=lambda s: s.importance, reverse=True)

        kept_segments = []
        current_tokens = 0
        target_tokens = int(self.max_tokens * 0.5)

        for seg in self._segments:
            if current_tokens + seg.token_estimate <= target_tokens:
                kept_segments.append(seg)
                current_tokens += seg.token_estimate
            else:
                if seg.importance >= 0.8:
                    summary = self._create_summary(seg.content, max_tokens=100)
                    summary_seg = ContextSegment(
                        content=summary,
                        importance=seg.importance,
                        token_estimate=self._estimate_tokens(summary),
                        is_summary=True,
                        source=seg.source,
                    )
                    kept_segments.append(summary_seg)
                    current_tokens += summary_seg.token_estimate

        self._segments = kept_segments
        self._total_tokens = current_tokens
        self._cleanup_count += 1

        logger.warning(f"紧急整理完成: 保留 {len(self._segments)} 段, 使用率 {self.get_usage_ratio():.1%}")

    def add_summary(self, summary: str, importance: float = 0.9):
        token_count = self._estimate_tokens(summary)
        segment = ContextSegment(
            content=summary,
            importance=importance,
            token_estimate=token_count,
            is_summary=True,
            source="system",
        )
        self._segments.append(segment)
        self._total_tokens += token_count

    def reset(self):
        self._segments.clear()
        self._total_tokens = 0
        self._cleanup_count = 0

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    @property
    def cleanup_count(self) -> int:
        return self._cleanup_count

    def _estimate_tokens(self, text: str) -> int:
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len(re.findall(r'\b\w+\b', text))
        return chinese_chars + english_words

    def _create_summary(self, content: str, max_tokens: int = 200) -> str:
        sentences = re.split(r'(?<=[.!?。！？])\s*', content)
        summary_parts = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            if current_tokens + sentence_tokens > max_tokens:
                break
            summary_parts.append(sentence)
            current_tokens += sentence_tokens

        result = ' '.join(summary_parts)
        if len(result) < len(content):
            result += " [已压缩]"

        return result

    def get_status(self) -> dict:
        return {
            "total_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "usage_ratio": self.get_usage_ratio(),
            "segment_count": self.segment_count,
            "cleanup_count": self.cleanup_count,
        }
