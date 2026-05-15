"""
上下文管理器 - 工作记忆 + RAG长期记忆架构

架构设计：
- 工作记忆(State Context)：保存大纲、核心指标和Agent互动摘要
- 长期记忆(Vector Store)：通过ChromaDB存储完整文档，按任务ID隔离
- 检索增强分析(RAG)：Agent按需检索，避免Token爆炸

解决的问题：
- 物理截断导致的信息丢失
- Token爆炸和OOM问题
- 深度研究中的上下文容量限制
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from services.vector_store import VectorStoreService, SearchResult, vector_store
from services.document_chunker import DocumentChunker, DocumentChunk, document_chunker

logger = logging.getLogger(__name__)


@dataclass
class MemorySegment:
    content: str
    importance: float = 0.5
    token_estimate: int = 0
    is_summary: bool = False
    source: str = ""
    segment_type: str = "working_memory"


class ContextManager:
    def __init__(
        self,
        max_tokens: int = 8000,
        warning_threshold: float = 0.75,
        critical_threshold: float = 0.9,
        task_id: Optional[str] = None,
        vector_store_service: Optional[VectorStoreService] = None,
        chunker_service: Optional[DocumentChunker] = None,
    ):
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.task_id = task_id
        
        self._vector_store = vector_store_service or vector_store
        self._chunker = chunker_service or document_chunker
        
        self._segments: List[MemorySegment] = []
        self._total_tokens: int = 0
        self._cleanup_count: int = 0
        
        logger.info(f"ContextManager initialized with RAG architecture (task: {task_id})")

    def add_segment(self, content: str, importance: float = 0.5, source: str = "", segment_type: str = "working_memory"):
        token_count = self._estimate_tokens(content)
        segment = MemorySegment(
            content=content,
            importance=importance,
            token_estimate=token_count,
            source=source,
            segment_type=segment_type,
        )
        self._segments.append(segment)
        self._total_tokens += token_count

        if self.get_usage_ratio() >= self.warning_threshold:
            logger.info(f"上下文使用率 {self.get_usage_ratio():.1%}，触发自动整理")
            self.auto_cleanup()

    def add_document_to_vector_store(
        self,
        content: str,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if not self.task_id:
            raise ValueError("task_id is required for vector store operations")
        
        chunks = self._chunker.chunk_document(content, source, metadata)
        
        if not chunks:
            logger.warning(f"No chunks created from document: {source}")
            return
        
        chunk_texts = [chunk.content for chunk in chunks]
        chunk_metadatas = [chunk.metadata for chunk in chunks]
        chunk_ids = [f"{self.task_id}_{source}_{chunk.chunk_index}" for chunk in chunks]
        
        self._vector_store.add_document(
            task_id=self.task_id,
            chunks=chunk_texts,
            metadatas=chunk_metadatas,
            ids=chunk_ids,
        )
        
        logger.info(f"Added document to vector store: {source} ({len(chunks)} chunks)")

    def search_memory(
        self,
        query: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        if not self.task_id:
            raise ValueError("task_id is required for memory search")
        
        results = self._vector_store.search(
            task_id=self.task_id,
            query=query,
            n_results=n_results,
            where_filter=where_filter,
        )
        
        logger.info(f"RAG search returned {len(results)} results for query: {query[:50]}...")
        return results

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
                    summary_seg = MemorySegment(
                        content=summary,
                        importance=seg.importance,
                        token_estimate=self._estimate_tokens(summary),
                        is_summary=True,
                        source=seg.source,
                        segment_type="summary",
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
                    summary_seg = MemorySegment(
                        content=summary,
                        importance=seg.importance,
                        token_estimate=self._estimate_tokens(summary),
                        is_summary=True,
                        source=seg.source,
                        segment_type="summary",
                    )
                    kept_segments.append(summary_seg)
                    current_tokens += summary_seg.token_estimate

        self._segments = kept_segments
        self._total_tokens = current_tokens
        self._cleanup_count += 1

        logger.warning(f"紧急整理完成: 保留 {len(self._segments)} 段, 使用率 {self.get_usage_ratio():.1%}")

    def add_summary(self, summary: str, importance: float = 0.9):
        token_count = self._estimate_tokens(summary)
        segment = MemorySegment(
            content=summary,
            importance=importance,
            token_estimate=token_count,
            is_summary=True,
            source="system",
            segment_type="summary",
        )
        self._segments.append(segment)
        self._total_tokens += token_count

    def reset(self):
        self._segments.clear()
        self._total_tokens = 0
        self._cleanup_count = 0
        
        if self.task_id:
            try:
                self._vector_store.delete_task_collection(self.task_id)
                logger.info(f"Cleared vector store for task {self.task_id}")
            except Exception as e:
                logger.warning(f"Failed to clear vector store: {e}")

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    @property
    def cleanup_count(self) -> int:
        return self._cleanup_count

    def get_vector_store_stats(self) -> Dict[str, Any]:
        if not self.task_id:
            return {"document_count": 0}
        
        try:
            count = self._vector_store.get_document_count(self.task_id)
            return {"document_count": count}
        except Exception as e:
            logger.warning(f"Failed to get vector store stats: {e}")
            return {"document_count": 0}

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
            "vector_store": self.get_vector_store_stats(),
        }
