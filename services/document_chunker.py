"""
文档分块服务 - 智能文本分割

提供：
- 基于语义的文本分块（段落、句子级别）
- 重叠分块策略保持上下文连贯性
- 自动检测中英文混合内容
- 元数据提取（标题、来源、段落索引等）
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    token_count: int = 0


class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self,
        content: str,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        if not content or len(content.strip()) == 0:
            return []

        paragraphs = self._split_into_paragraphs(content)
        
        chunks = []
        current_chunk = ""
        current_index = 0
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunk = DocumentChunk(
                    content=current_chunk.strip(),
                    metadata={
                        **(metadata or {}),
                        "source": source,
                        "chunk_index": current_index,
                        "chunk_type": "paragraph_group",
                    },
                    chunk_index=current_index,
                    token_count=self._estimate_tokens(current_chunk),
                )
                chunks.append(chunk)
                current_index += 1
                
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text
            
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        
        if current_chunk.strip():
            chunk = DocumentChunk(
                content=current_chunk.strip(),
                metadata={
                    **(metadata or {}),
                    "source": source,
                    "chunk_index": current_index,
                    "chunk_type": "paragraph_group",
                },
                chunk_index=current_index,
                token_count=self._estimate_tokens(current_chunk),
            )
            chunks.append(chunk)
        
        if len(chunks) == 0 and len(content) > self.chunk_size:
            chunks = self._fallback_split(content, source, metadata)
        
        logger.info(f"Chunked document into {len(chunks)} chunks from source: {source}")
        return chunks

    def _split_into_paragraphs(self, content: str) -> List[str]:
        paragraphs = re.split(r'\n\s*\n', content)
        result = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(para) > self.chunk_size:
                sentences = self._split_into_sentences(para)
                result.extend(sentences)
            else:
                result.append(para)
        
        return result

    def _split_into_sentences(self, text: str) -> List[str]:
        sentence_endings = r'(?<=[.!?。！？\n])\s*'
        sentences = re.split(sentence_endings, text)
        
        result = []
        current = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current) + len(sentence) > self.chunk_size and current:
                result.append(current)
                current = sentence
            else:
                if current:
                    current += " " + sentence
                else:
                    current = sentence
        
        if current:
            result.append(current)
        
        return result

    def _get_overlap_text(self, chunk: str) -> str:
        if self.chunk_overlap <= 0:
            return ""
        
        sentences = re.split(r'(?<=[.!?。！？])\s*', chunk)
        
        overlap = ""
        for sentence in reversed(sentences):
            sentence = sentence.strip()
            if len(sentence) + len(overlap) > self.chunk_overlap:
                break
            if overlap:
                overlap = sentence + " " + overlap
            else:
                overlap = sentence
        
        return overlap.strip()

    def _fallback_split(self, content: str, source: str, metadata: Optional[Dict[str, Any]]) -> List[DocumentChunk]:
        chunks = []
        start = 0
        index = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            if end < len(content):
                break_point = content.rfind('\n', start, end)
                if break_point == -1 or break_point < start + self.min_chunk_size:
                    break_point = content.rfind(' ', start, end)
                if break_point == -1 or break_point < start + self.min_chunk_size:
                    break_point = end
                end = break_point
            
            chunk_content = content[start:end].strip()
            if chunk_content:
                chunk = DocumentChunk(
                    content=chunk_content,
                    metadata={
                        **(metadata or {}),
                        "source": source,
                        "chunk_index": index,
                        "chunk_type": "fallback",
                    },
                    chunk_index=index,
                    token_count=self._estimate_tokens(chunk_content),
                )
                chunks.append(chunk)
                index += 1
            
            start = end - self.chunk_overlap
        
        return chunks

    def _estimate_tokens(self, text: str) -> int:
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_words = len(re.findall(r'\b\w+\b', text))
        return chinese_chars + english_words


document_chunker = DocumentChunker()
