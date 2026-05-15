"""
向量存储服务 - 基于ChromaDB实现长期记忆

提供：
- 文档分块存储与向量嵌入
- 按任务ID隔离的集合管理
- 相似度检索(RAG)
- 元数据过滤查询
"""

import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    distance: float
    source: str = ""


class VectorStoreService:
    def __init__(self, persist_directory: str = "./data/vector_store"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self._collections: Dict[str, Any] = {}
        logger.info(f"VectorStore initialized at {persist_directory}")

    def _get_collection(self, task_id: str):
        if task_id not in self._collections:
            self._collections[task_id] = self.client.get_or_create_collection(
                name=f"task_{task_id}",
                metadata={"task_id": task_id, "hnsw:space": "cosine"}
            )
            logger.info(f"Created collection for task {task_id}")
        return self._collections[task_id]

    def add_document(
        self,
        task_id: str,
        chunks: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ):
        collection = self._get_collection(task_id)
        
        if ids is None:
            ids = [f"{task_id}_{i}" for i in range(len(chunks))]
        
        if metadatas is None:
            metadatas = [{"source": "unknown", "chunk_index": i} for i in range(len(chunks))]
        else:
            for i, meta in enumerate(metadatas):
                if "chunk_index" not in meta:
                    meta["chunk_index"] = i
        
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )
        
        logger.info(f"Added {len(chunks)} chunks to task {task_id}")

    def search(
        self,
        task_id: str,
        query: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        collection = self._get_collection(task_id)
        
        kwargs = {
            "query_texts": [query],
            "n_results": n_results,
        }
        
        if where_filter:
            kwargs["where"] = where_filter
        
        results = collection.query(**kwargs)
        
        search_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                
                search_results.append(SearchResult(
                    content=doc,
                    metadata=metadata,
                    distance=distance,
                    source=metadata.get("source", ""),
                ))
        
        logger.info(f"Search for task {task_id} returned {len(search_results)} results")
        return search_results

    def search_by_metadata(
        self,
        task_id: str,
        where_filter: Dict[str, Any],
        n_results: int = 10,
    ) -> List[SearchResult]:
        collection = self._get_collection(task_id)
        
        results = collection.get(
            where=where_filter,
            include=["documents", "metadatas"],
        )
        
        search_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                search_results.append(SearchResult(
                    content=doc,
                    metadata=metadata,
                    distance=0.0,
                    source=metadata.get("source", ""),
                ))
        
        return search_results[:n_results]

    def get_document_count(self, task_id: str) -> int:
        collection = self._get_collection(task_id)
        return collection.count()

    def delete_task_collection(self, task_id: str):
        if task_id in self._collections:
            del self._collections[task_id]
        
        try:
            self.client.delete_collection(name=f"task_{task_id}")
            logger.info(f"Deleted collection for task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to delete collection for task {task_id}: {e}")

    def list_collections(self) -> List[str]:
        return [name for name in self.client.list_collections()]

    def clear_all(self):
        for task_id in list(self._collections.keys()):
            self.delete_task_collection(task_id)
        self._collections.clear()
        logger.info("Cleared all vector store collections")


vector_store = VectorStoreService()
