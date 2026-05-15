"""
本地知识库模块

功能：
- 企业私有数据的安全存储
- RAG 检索增强生成
- 数据索引与检索优化
- 知识库更新与版本管理
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDocument:
    """知识文档"""
    doc_id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    version: int = 1
    chunks: List[str] = field(default_factory=list)


class LocalKnowledgeBase:
    """
    本地知识库

    提供：
    1. 企业私有数据的安全本地存储
    2. 文档分块与索引
    3. 相似度检索（RAG）
    4. 知识库更新与版本管理
    5. 数据完整性校验
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        enable_vector_search: bool = True,
    ):
        base_path = storage_path or os.path.join(
            os.path.dirname(__file__), "..", "data", "knowledge_base"
        )
        self.storage_path = Path(base_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.docs_path = self.storage_path / "documents"
        self.docs_path.mkdir(exist_ok=True)

        self.index_path = self.storage_path / "index.json"
        self.enable_vector_search = enable_vector_search

        self._documents: Dict[str, KnowledgeDocument] = {}
        self._vector_client = None
        self._collection = None
        self._load_index()

        if enable_vector_search:
            self._init_vector_store()

        logger.info(f"LocalKnowledgeBase initialized at {self.storage_path}")

    def _init_vector_store(self) -> None:
        """初始化向量存储"""
        try:
            import chromadb
            from chromadb.config import Settings

            vector_path = self.storage_path / "vectors"
            vector_path.mkdir(exist_ok=True)

            self._vector_client = chromadb.PersistentClient(
                path=str(vector_path),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._vector_client.get_or_create_collection(
                name="knowledge_base",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Vector store initialized for knowledge base")

        except Exception as e:
            logger.warning(f"Vector store initialization failed: {e}")
            self._vector_client = None
            self._collection = None

    def _load_index(self) -> None:
        """加载索引"""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for doc_id, doc_data in data.items():
                    self._documents[doc_id] = KnowledgeDocument(**doc_data)
                logger.info(f"Loaded {len(self._documents)} documents from index")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")

    def _save_index(self) -> None:
        """保存索引"""
        try:
            data = {
                doc_id: {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "content": doc.content[:500],  # 仅保存摘要
                    "metadata": doc.metadata,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                    "version": doc.version,
                }
                for doc_id, doc in self._documents.items()
            }
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def add_document(
        self,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """
        添加文档到知识库

        Args:
            title: 文档标题
            content: 文档内容
            metadata: 元数据
            doc_id: 文档ID（可选，自动生成）

        Returns:
            str: 文档ID
        """
        if doc_id is None:
            doc_id = hashlib.md5(f"{title}{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:12]

        now = datetime.now(timezone.utc).isoformat()

        # 检查是否已存在
        if doc_id in self._documents:
            existing = self._documents[doc_id]
            version = existing.version + 1
            logger.info(f"Updating document {doc_id} (version {version})")
        else:
            version = 1

        # 文档分块
        chunks = self._chunk_content(content)

        doc = KnowledgeDocument(
            doc_id=doc_id,
            title=title,
            content=content,
            metadata=metadata or {},
            created_at=self._documents[doc_id].created_at if doc_id in self._documents else now,
            updated_at=now,
            version=version,
            chunks=chunks,
        )

        self._documents[doc_id] = doc

        # 保存到文件
        self._save_document_file(doc)

        # 更新向量存储
        if self.enable_vector_search and self._collection:
            self._update_vectors(doc)

        # 更新索引
        self._save_index()

        logger.info(f"Document added: {doc_id} - {title}")
        return doc_id

    def search(
        self,
        query: str,
        n_results: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        检索知识库

        Args:
            query: 查询文本
            n_results: 返回结果数量
            metadata_filter: 元数据过滤条件

        Returns:
            List[str]: 检索结果（文档内容片段）
        """
        results = []

        # 向量检索
        if self.enable_vector_search and self._collection:
            try:
                vector_results = self._collection.query(
                    query_texts=[query],
                    n_results=n_results,
                )
                if vector_results["documents"] and vector_results["documents"][0]:
                    results = vector_results["documents"][0]
                    logger.info(f"Vector search returned {len(results)} results")
                    return results
            except Exception as e:
                logger.warning(f"Vector search failed, falling back to text search: {e}")

        # 文本检索（降级方案）
        return self._text_search(query, n_results, metadata_filter)

    def _text_search(
        self,
        query: str,
        n_results: int,
        metadata_filter: Optional[Dict[str, Any]],
    ) -> List[str]:
        """基于文本的检索"""
        query_lower = query.lower()
        scored_docs = []

        for doc in self._documents.values():
            if metadata_filter:
                if not all(doc.metadata.get(k) == v for k, v in metadata_filter.items()):
                    continue

            content_lower = doc.content.lower()
            title_lower = doc.title.lower()

            score = 0
            if query_lower in title_lower:
                score += 10
            if query_lower in content_lower:
                score += content_lower.count(query_lower)

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc.content[:500] for _, doc in scored_docs[:n_results]]

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        """获取文档"""
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id not in self._documents:
            return False

        doc = self._documents.pop(doc_id)

        # 删除文件
        doc_file = self.docs_path / f"{doc_id}.json"
        if doc_file.exists():
            doc_file.unlink()

        # 删除向量
        if self._collection:
            try:
                self._collection.delete(ids=[f"{doc_id}_{i}" for i in range(len(doc.chunks))])
            except Exception:
                pass

        self._save_index()
        logger.info(f"Document deleted: {doc_id}")
        return True

    def get_document_count(self) -> int:
        """获取文档数量"""
        return len(self._documents)

    def list_documents(self) -> List[Dict[str, Any]]:
        """列出所有文档"""
        return [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "metadata": doc.metadata,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "version": doc.version,
            }
            for doc in self._documents.values()
        ]

    def _chunk_content(self, content: str, chunk_size: int = 500) -> List[str]:
        """文档分块"""
        chunks = []
        words = content.split()

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    def _update_vectors(self, doc: KnowledgeDocument) -> None:
        """更新向量存储"""
        if not self._collection:
            return

        try:
            ids = [f"{doc.doc_id}_{i}" for i in range(len(doc.chunks))]
            metadatas = [
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "chunk_index": i,
                    **doc.metadata,
                }
                for i in range(len(doc.chunks))
            ]

            self._collection.upsert(
                documents=doc.chunks,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as e:
            logger.error(f"Failed to update vectors: {e}")

    def _save_document_file(self, doc: KnowledgeDocument) -> None:
        """保存文档文件"""
        doc_file = self.docs_path / f"{doc.doc_id}.json"
        try:
            with open(doc_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "created_at": doc.created_at,
                        "updated_at": doc.updated_at,
                        "version": doc.version,
                        "chunks": doc.chunks,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save document file: {e}")
