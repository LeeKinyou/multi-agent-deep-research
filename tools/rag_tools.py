"""
RAG工具类 - 供Agent在任务中使用

提供：
- 存储采集到的信息到向量数据库
- 从向量数据库中检索相关信息
- 支持按任务ID和来源过滤
"""

import logging
from typing import List, Dict, Any, Optional

from langchain.tools import Tool

from services.vector_store import vector_store, SearchResult
from services.document_chunker import document_chunker

logger = logging.getLogger(__name__)


class RAGTools:
    @staticmethod
    def create_store_tool(task_id: str) -> Tool:
        def store_information(text: str, source: str = "agent_output") -> str:
            try:
                chunks = document_chunker.chunk_document(text, source)
                
                if not chunks:
                    return "存储失败：文本为空"
                
                chunk_texts = [chunk.content for chunk in chunks]
                chunk_metadatas = [chunk.metadata for chunk in chunks]
                chunk_ids = [f"{task_id}_{source}_{chunk.chunk_index}" for chunk in chunks]
                
                vector_store.add_document(
                    task_id=task_id,
                    chunks=chunk_texts,
                    metadatas=chunk_metadatas,
                    ids=chunk_ids,
                )
                
                return f"成功存储 {len(chunks)} 个文本块到向量数据库"
            except Exception as e:
                logger.error(f"Failed to store information: {e}")
                return f"存储失败：{str(e)}"

        return Tool(
            name="store_research_info",
            func=store_information,
            description="将采集到的研究信息存储到向量数据库中，供后续分析使用。输入参数：text(要存储的文本内容), source(来源标识，可选)"
        )

    @staticmethod
    def create_search_tool(task_id: str) -> Tool:
        def search_information(query: str, n_results: int = 5) -> str:
            try:
                results: List[SearchResult] = vector_store.search(
                    task_id=task_id,
                    query=query,
                    n_results=n_results,
                )
                
                if not results:
                    return f"未找到与'{query}'相关的信息"
                
                formatted_results = []
                for i, result in enumerate(results, 1):
                    formatted_results.append(
                        f"[{i}] {result.content}\n"
                        f"   来源: {result.source}\n"
                        f"   相关度: {1 - result.distance:.2f}"
                    )
                
                return "\n\n".join(formatted_results)
            except Exception as e:
                logger.error(f"Failed to search information: {e}")
                return f"检索失败：{str(e)}"

        return Tool(
            name="search_research_info",
            func=search_information,
            description="从向量数据库中检索与研究相关的信息。输入参数：query(检索查询), n_results(返回结果数量，默认5)"
        )

    @staticmethod
    def create_store_and_search_tools(task_id: str) -> List[Tool]:
        return [
            RAGTools.create_store_tool(task_id),
            RAGTools.create_search_tool(task_id),
        ]
