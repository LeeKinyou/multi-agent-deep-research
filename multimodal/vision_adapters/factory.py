"""
视觉模型工厂

根据配置自动创建对应的视觉模型适配器。
支持从环境变量或显式配置中选择模型提供商。
"""

import os
import logging
from typing import Optional, Dict, Any

from multimodal.vision_adapters.base import BaseVisionAdapter
from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
from multimodal.vision_adapters.gpt4v import GPT4VAdapter
from multimodal.vision_adapters.claude import ClaudeVisionAdapter
from multimodal.vision_adapters.gemini import GeminiVisionAdapter

logger = logging.getLogger(__name__)


class VisionModelFactory:
    """
    视觉模型工厂

    根据配置创建对应的视觉模型适配器。
    支持以下提供商：
    - qwen-vl: Qwen-VL 系列（本地或 DashScope）
    - openai: GPT-4V / GPT-4o
    - anthropic: Claude 3 系列
    - google: Gemini 系列
    """

    PROVIDER_MAP = {
        "qwen-vl": QwenVLAdapter,
        "qwen": QwenVLAdapter,
        "openai": GPT4VAdapter,
        "gpt-4v": GPT4VAdapter,
        "gpt4v": GPT4VAdapter,
        "gpt-4o": GPT4VAdapter,
        "gpt4o": GPT4VAdapter,
        "anthropic": ClaudeVisionAdapter,
        "claude": ClaudeVisionAdapter,
        "google": GeminiVisionAdapter,
        "gemini": GeminiVisionAdapter,
    }

    @classmethod
    def create_adapter(
        cls,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> BaseVisionAdapter:
        """
        创建视觉模型适配器

        Args:
            provider: 模型提供商（qwen-vl/openai/anthropic/google）
            model_name: 模型名称
            api_key: API 密钥
            base_url: API 基础 URL

        Returns:
            BaseVisionAdapter: 对应的适配器实例

        Raises:
            ValueError: 如果提供商不支持
        """
        # 从环境变量获取配置
        provider = provider or os.getenv("VISION_PROVIDER", "qwen-vl")
        model_name = model_name or os.getenv("VISION_MODEL_NAME", "")
        api_key = api_key or os.getenv("VISION_API_KEY", "")
        base_url = base_url or os.getenv("VISION_BASE_URL", "")

        provider_lower = provider.lower()

        if provider_lower not in cls.PROVIDER_MAP:
            supported = list(cls.PROVIDER_MAP.keys())
            raise ValueError(
                f"Unsupported vision provider: {provider}. "
                f"Supported providers: {supported}"
            )

        adapter_class = cls.PROVIDER_MAP[provider_lower]

        # 如果未指定模型名称，使用默认值
        if not model_name:
            model_name = adapter_class.SUPPORTED_MODELS[0]

        logger.info(f"Creating {provider} adapter with model: {model_name}")

        return adapter_class(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )

    @classmethod
    def get_supported_providers(cls) -> Dict[str, str]:
        """获取支持的提供商列表"""
        return {
            "qwen-vl": "Qwen-VL 系列（本地部署或 DashScope）",
            "openai": "OpenAI GPT-4V / GPT-4o",
            "anthropic": "Anthropic Claude 3 系列",
            "google": "Google Gemini 系列",
        }

    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """获取指定提供商的默认模型"""
        provider_lower = provider.lower()
        if provider_lower in cls.PROVIDER_MAP:
            return cls.PROVIDER_MAP[provider_lower].SUPPORTED_MODELS[0]
        raise ValueError(f"Unsupported provider: {provider}")
