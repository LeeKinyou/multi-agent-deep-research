"""
本地处理层模块

功能：
- 本地模型推理（支持多种本地 LLM）
- 本地 RAG 知识库检索增强
- 敏感数据本地处理
- 性能优化（缓存、批处理）
"""

import logging
from typing import Optional, Dict, Any, List

from hybrid_computing.local_knowledge_base import LocalKnowledgeBase

logger = logging.getLogger(__name__)


class LocalProcessor:
    """
    本地处理器

    负责处理所有敏感数据查询，确保数据不离开本地环境。

    支持：
    1. 本地 LLM 推理（Ollama、LM Studio 等）
    2. RAG 增强生成（结合本地知识库）
    3. 快速响应（< 200ms 目标）
    4. 降级策略（模型不可用时的回退方案）
    """

    def __init__(
        self,
        model_url: Optional[str] = None,
        model_name: Optional[str] = None,
        knowledge_base: Optional[LocalKnowledgeBase] = None,
    ):
        self.model_url = model_url or "http://localhost:1234/v1"
        self.model_name = model_name or "qwen2.5-7b-instruct"
        self.knowledge_base = knowledge_base or LocalKnowledgeBase()
        self._initialized = False
        self._model_available = False

    def initialize(self) -> bool:
        """初始化本地模型"""
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.model_url,
                api_key="not-needed",
            )

            # 健康检查
            models = self._client.models.list()
            self._model_available = True
            self._initialized = True
            logger.info(f"Local model initialized: {self.model_name} at {self.model_url}")
            return True

        except Exception as e:
            logger.warning(f"Local model initialization failed: {e}")
            self._model_available = False
            return False

    def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        处理本地查询

        Args:
            query: 用户查询
            context: 上下文信息

        Returns:
            str: 处理结果
        """
        if not self._initialized:
            self.initialize()

        # Step 1: 检索本地知识库
        rag_context = self._retrieve_context(query)

        # Step 2: 构建提示词
        prompt = self._build_prompt(query, rag_context, context)

        # Step 3: 调用本地模型
        if self._model_available:
            try:
                return self._call_local_model(prompt)
            except Exception as e:
                logger.error(f"Local model call failed: {e}")

        # Step 4: 降级方案
        return self._fallback_response(query, rag_context)

    def _retrieve_context(self, query: str) -> str:
        """检索本地知识库上下文"""
        try:
            results = self.knowledge_base.search(query, n_results=3)
            if results:
                context_parts = []
                for i, result in enumerate(results, 1):
                    context_parts.append(f"[{i}] {result}")
                return "\n\n".join(context_parts)
        except Exception as e:
            logger.warning(f"Knowledge base retrieval failed: {e}")
        return ""

    def _build_prompt(
        self,
        query: str,
        rag_context: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """构建本地模型提示词"""
        system_prompt = """你是一个专业的企业级助手，负责处理敏感数据查询。
所有数据处理都在本地完成，确保数据安全。
请基于以下提供的上下文信息回答问题。
如果上下文中没有相关信息，请明确告知用户。"""

        context_section = ""
        if rag_context:
            context_section = f"""

## 参考信息
{rag_context}"""

        context_info = ""
        if context:
            context_info = f"\n\n## 上下文信息\n{context}"

        return f"""{system_prompt}

## 用户问题
{query}{context_section}{context_info}

## 回答
"""

    def _call_local_model(self, prompt: str) -> str:
        """调用本地 LLM"""
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def _fallback_response(
        self,
        query: str,
        rag_context: str,
    ) -> str:
        """降级响应（当本地模型不可用时）"""
        if rag_context:
            return f"""本地模型暂时不可用，以下是从本地知识库检索到的相关信息：

{rag_context}

请稍后重试以获取 AI 生成的完整回答。"""

        return "本地模型暂时不可用，无法处理此查询。请确保本地 LLM 服务已启动。"

    def get_status(self) -> Dict[str, Any]:
        """获取本地处理器状态"""
        return {
            "initialized": self._initialized,
            "model_available": self._model_available,
            "model_url": self.model_url,
            "model_name": self.model_name,
            "knowledge_base_docs": self.knowledge_base.get_document_count(),
        }
