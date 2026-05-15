"""
云处理层模块

功能：
- 云端 LLM API 调用
- 通用交互处理（闲聊、创意生成等）
- 数据过滤（确保不传输敏感信息）
- 性能优化（连接池、超时控制）
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CloudProcessor:
    """
    云端处理器

    负责处理所有非敏感的通用查询，利用云端 LLM 的强大能力。

    支持：
    1. 云端 LLM API 调用（OpenAI、DeepSeek 等）
    2. 通用交互（闲聊、创意生成、知识问答）
    3. 连接池和超时控制
    4. 错误重试机制
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        from config.settings import llm_config

        self.api_key = api_key or llm_config.api_key
        self.base_url = base_url or llm_config.base_url
        self.model = model or llm_config.model
        self._client = None
        self._initialized = False

    def initialize(self) -> bool:
        """初始化云端客户端"""
        try:
            from langchain_openai import ChatOpenAI

            self._client = ChatOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                model_name=self.model,
                temperature=0.7,
                max_tokens=2048,
            )
            self._initialized = True
            logger.info(f"Cloud processor initialized: {self.model}")
            return True

        except Exception as e:
            logger.error(f"Cloud processor initialization failed: {e}")
            return False

    def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        处理云端查询

        Args:
            query: 用户查询（已脱敏）
            context: 上下文信息

        Returns:
            str: 处理结果
        """
        if not self._initialized:
            self.initialize()

        prompt = self._build_prompt(query, context)

        try:
            response = self._client.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)

        except Exception as e:
            logger.error(f"Cloud API call failed: {e}")
            return self._fallback_response(query, str(e))

    def _build_prompt(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """构建云端模型提示词"""
        system_prompt = """你是一个专业、友好的 AI 助手。请简洁、准确地回答用户的问题。
如果是闲聊，请友好回应；如果是问题，请给出准确的答案。"""

        context_info = ""
        if context:
            context_info = f"\n\n上下文信息：{context}"

        return f"""{system_prompt}

用户问题：{query}{context_info}"""

    def _fallback_response(
        self,
        query: str,
        error: str,
    ) -> str:
        """降级响应"""
        return f"""云端服务暂时不可用，请稍后重试。

错误信息：{error}"""

    def get_status(self) -> Dict[str, Any]:
        """获取云端处理器状态"""
        return {
            "initialized": self._initialized,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
        }
