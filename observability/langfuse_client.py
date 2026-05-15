"""
Langfuse 客户端集成模块

提供与 Langfuse 平台的连接、认证和基础操作能力。
支持自托管和云端两种部署模式。
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

from langfuse import Langfuse
try:
    from langfuse import observe, langfuse_context
except ImportError:
    observe = None
    langfuse_context = None

from config import llm_config

logger = logging.getLogger(__name__)


class LangfuseClient:
    """
    Langfuse 客户端封装类

    封装 Langfuse SDK 的核心功能，提供：
    - 连接管理（自动重连、健康检查）
    - Trace/Span/Generation 创建
    - 评分记录
    - 批量数据上报
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
        release: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY", "")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        self.release = release or os.getenv("LANGFUSE_RELEASE", "v1.0.0")
        self.environment = environment or os.getenv("LANGFUSE_ENVIRONMENT", "production")

        self._client: Optional[Langfuse] = None
        self._connected = False

    def connect(self) -> bool:
        """建立与 Langfuse 服务的连接"""
        try:
            if not self.public_key or not self.secret_key:
                logger.warning("Langfuse API keys not configured, observability disabled")
                return False

            self._client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
                release=self.release,
                environment=self.environment,
                flush_at=10,
                flush_interval=5,
            )
            self._connected = True
            logger.info(f"Langfuse client connected to {self.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Langfuse: {e}")
            self._connected = False
            return False

    @property
    def client(self) -> Optional[Langfuse]:
        """获取底层 Langfuse 客户端实例"""
        if not self._connected or not self._client:
            self.connect()
        return self._client

    def health_check(self) -> bool:
        """检查 Langfuse 服务健康状态"""
        if not self.client:
            return False
        try:
            self.client.auth_check()
            return True
        except Exception as e:
            logger.warning(f"Langfuse health check failed: {e}")
            return False

    def create_trace(
        self,
        name: str,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
    ) -> Optional[Any]:
        """创建一个新的 Trace"""
        if not self.client:
            return None

        try:
            trace = self.client.trace(
                id=trace_id,
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {},
                tags=tags or [],
            )
            return trace
        except Exception as e:
            logger.error(f"Failed to create trace: {e}")
            return None

    def create_span(
        self,
        trace_id: str,
        name: str,
        parent_observation_id: Optional[str] = None,
        start_time: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """在指定 Trace 下创建 Span"""
        if not self.client:
            return None

        try:
            span = self.client.span(
                trace_id=trace_id,
                name=name,
                parent_observation_id=parent_observation_id,
                start_time=start_time,
                metadata=metadata or {},
            )
            return span
        except Exception as e:
            logger.error(f"Failed to create span: {e}")
            return None

    def create_generation(
        self,
        trace_id: str,
        name: str,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        completion: Optional[str] = None,
        usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_observation_id: Optional[str] = None,
    ) -> Optional[Any]:
        """记录 LLM Generation 事件"""
        if not self.client:
            return None

        try:
            generation = self.client.generation(
                trace_id=trace_id,
                name=name,
                model=model or llm_config.model,
                input=prompt,
                output=completion,
                usage=usage,
                metadata=metadata or {},
                parent_observation_id=parent_observation_id,
            )
            return generation
        except Exception as e:
            logger.error(f"Failed to create generation: {e}")
            return None

    def create_event(
        self,
        trace_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_observation_id: Optional[str] = None,
    ) -> Optional[Any]:
        """创建普通事件（如工具调用、决策点等）"""
        if not self.client:
            return None

        try:
            event = self.client.event(
                trace_id=trace_id,
                name=name,
                metadata=metadata or {},
                parent_observation_id=parent_observation_id,
            )
            return event
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return None

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: Optional[str] = None,
        observation_id: Optional[str] = None,
    ) -> bool:
        """为 Trace 或 Observation 添加评分"""
        if not self.client:
            return False

        try:
            self.client.score(
                trace_id=trace_id,
                observation_id=observation_id,
                name=name,
                value=value,
                comment=comment,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to score trace: {e}")
            return False

    def flush(self) -> None:
        """强制刷新所有待发送数据"""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                logger.error(f"Failed to flush Langfuse client: {e}")


@lru_cache()
def get_langfuse_client() -> LangfuseClient:
    """获取 Langfuse 客户端单例"""
    client = LangfuseClient()
    client.connect()
    return client