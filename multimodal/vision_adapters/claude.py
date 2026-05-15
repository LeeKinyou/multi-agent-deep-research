"""
Anthropic Claude 视觉模型适配器

支持：
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307
- claude-3-5-sonnet-20241022
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from multimodal.vision_adapters.base import BaseVisionAdapter, ChartAnalysisResult

logger = logging.getLogger(__name__)


class ClaudeVisionAdapter(BaseVisionAdapter):
    """
    Anthropic Claude 视觉模型适配器

    通过 Anthropic API 调用 Claude 3 系列模型进行图表分析。
    """

    SUPPORTED_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        model = model_name or os.getenv("VISION_MODEL_NAME", "claude-3-5-sonnet-20241022")
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        url = base_url or os.getenv("VISION_BASE_URL", "https://api.anthropic.com")

        super().__init__(
            model_name=model,
            api_key=key,
            base_url=url,
        )
        self._client = None

    def initialize(self) -> bool:
        """初始化 Claude 客户端"""
        try:
            from anthropic import Anthropic

            self._client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url != "https://api.anthropic.com" else None,
            )

            # 简单验证
            self._client.models.list()
            self._initialized = True
            logger.info(f"Claude adapter initialized: {self.model_name}")
            return True

        except Exception as e:
            logger.warning(f"Claude adapter initialization failed: {e}")
            self._initialized = False
            return False

    def analyze_image(
        self,
        image_data: bytes,
        image_format: str = "PNG",
        context: str = "",
    ) -> ChartAnalysisResult:
        """分析图像"""
        if not self._initialized:
            if not self.initialize():
                return self._fallback_analysis(image_data, context)

        base64_image = base64.b64encode(image_data).decode("utf-8")

        # 映射 MIME 类型
        mime_map = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "WEBP": "image/webp",
            "GIF": "image/gif",
        }
        media_type = mime_map.get(image_format.upper(), "image/png")

        prompt = self._build_chart_analysis_prompt(context)

        try:
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            content = response.content[0].text
            return self._parse_analysis_response(content)

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return self._fallback_analysis(image_data, context)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "anthropic",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "initialized": self._initialized,
            "supported_models": self.SUPPORTED_MODELS,
        }
