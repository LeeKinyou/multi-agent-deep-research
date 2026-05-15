"""
OpenAI GPT-4V / GPT-4o 视觉模型适配器

支持：
- gpt-4-vision-preview
- gpt-4o
- gpt-4o-mini
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from multimodal.vision_adapters.base import BaseVisionAdapter, ChartAnalysisResult

logger = logging.getLogger(__name__)


class GPT4VAdapter(BaseVisionAdapter):
    """
    OpenAI GPT-4V / GPT-4o 视觉模型适配器

    通过 OpenAI API 调用 GPT-4 视觉模型进行图表分析。
    """

    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4-vision-preview",
    ]

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        model = model_name or os.getenv("VISION_MODEL_NAME", "gpt-4o")
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        url = base_url or os.getenv("VISION_BASE_URL", "https://api.openai.com/v1")

        super().__init__(
            model_name=model,
            api_key=key,
            base_url=url,
        )
        self._client = None

    def initialize(self) -> bool:
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )

            # 健康检查
            self._client.models.list()
            self._initialized = True
            logger.info(f"GPT-4V adapter initialized: {self.model_name}")
            return True

        except Exception as e:
            logger.warning(f"GPT-4V adapter initialization failed: {e}")
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
        data_uri = f"data:image/{image_format.lower()};base64,{base64_image}"

        prompt = self._build_chart_analysis_prompt(context)

        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_uri,
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            content = response.choices[0].message.content
            return self._parse_analysis_response(content)

        except Exception as e:
            logger.error(f"GPT-4V analysis failed: {e}")
            return self._fallback_analysis(image_data, context)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "openai",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "initialized": self._initialized,
            "supported_models": self.SUPPORTED_MODELS,
        }
