"""
Google Gemini 视觉模型适配器

支持：
- gemini-2.0-flash
- gemini-1.5-pro
- gemini-1.5-flash
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from multimodal.vision_adapters.base import BaseVisionAdapter, ChartAnalysisResult

logger = logging.getLogger(__name__)


class GeminiVisionAdapter(BaseVisionAdapter):
    """
    Google Gemini 视觉模型适配器

    通过 Google AI API 调用 Gemini 系列模型进行图表分析。
    """

    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro-vision",
    ]

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        model = model_name or os.getenv("VISION_MODEL_NAME", "gemini-2.0-flash")
        key = api_key or os.getenv("GOOGLE_API_KEY", "")
        url = base_url or os.getenv("VISION_BASE_URL", "")

        super().__init__(
            model_name=model,
            api_key=key,
            base_url=url,
        )
        self._client = None

    def initialize(self) -> bool:
        """初始化 Gemini 客户端"""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)

            # 简单验证
            self._client.count_tokens("test")
            self._initialized = True
            logger.info(f"Gemini adapter initialized: {self.model_name}")
            return True

        except Exception as e:
            logger.warning(f"Gemini adapter initialization failed: {e}")
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

        prompt = self._build_chart_analysis_prompt(context)

        try:
            import PIL.Image
            from io import BytesIO

            image = PIL.Image.open(BytesIO(image_data))

            response = self._client.generate_content([prompt, image])

            content = response.text
            return self._parse_analysis_response(content)

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return self._fallback_analysis(image_data, context)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "google",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "initialized": self._initialized,
            "supported_models": self.SUPPORTED_MODELS,
        }
