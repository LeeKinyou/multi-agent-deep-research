"""
多模态视觉模型适配层 - 支持灵活集成多种视觉大模型

架构设计：
- BaseVisionAdapter: 抽象基类，定义统一接口
- QwenVLAdapter: Qwen-VL 系列模型适配器
- GPT4VAdapter: OpenAI GPT-4V / GPT-4o 适配器
- ClaudeVisionAdapter: Anthropic Claude 视觉适配器
- GeminiVisionAdapter: Google Gemini 视觉适配器
- VisionModelFactory: 模型工厂，根据配置创建对应适配器
"""

from multimodal.vision_adapters.base import BaseVisionAdapter
from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
from multimodal.vision_adapters.gpt4v import GPT4VAdapter
from multimodal.vision_adapters.claude import ClaudeVisionAdapter
from multimodal.vision_adapters.gemini import GeminiVisionAdapter
from multimodal.vision_adapters.factory import VisionModelFactory

__all__ = [
    "BaseVisionAdapter",
    "QwenVLAdapter",
    "GPT4VAdapter",
    "ClaudeVisionAdapter",
    "GeminiVisionAdapter",
    "VisionModelFactory",
]
