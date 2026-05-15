"""
Qwen-VL 系列模型适配器

支持：
- qwen2.5-vl-7b-instruct
- qwen2.5-vl-72b-instruct
- qwen-vl-max
- qwen-vl-plus
- 以及其他兼容 OpenAI API 格式的 Qwen-VL 模型
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from multimodal.vision_adapters.base import BaseVisionAdapter, ChartAnalysisResult

logger = logging.getLogger(__name__)


class QwenVLAdapter(BaseVisionAdapter):
    """
    Qwen-VL 视觉模型适配器

    支持通过 OpenAI 兼容 API 或 DashScope API 调用 Qwen-VL 系列模型。
    """

    SUPPORTED_MODELS = [
        "qwen2.5-vl-7b-instruct",
        "qwen2.5-vl-72b-instruct",
        "qwen-vl-max",
        "qwen-vl-plus",
        "qwen2-vl-7b-instruct",
    ]

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        model = model_name or os.getenv("VISION_MODEL_NAME", "qwen2.5-vl-7b-instruct")
        key = api_key or os.getenv("VISION_API_KEY", "not-needed")
        url = base_url or os.getenv("VISION_BASE_URL", "http://localhost:1234/v1")

        super().__init__(
            model_name=model,
            api_key=key,
            base_url=url,
        )
        self._client = None

    def initialize(self) -> bool:
        """初始化 Qwen-VL 客户端"""
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )

            # 健康检查
            self._client.models.list()
            self._initialized = True
            logger.info(f"Qwen-VL adapter initialized: {self.model_name}")
            return True

        except Exception as e:
            logger.warning(f"Qwen-VL adapter initialization failed: {e}")
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
                                "image_url": {"url": data_uri},
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
            logger.error(f"Qwen-VL analysis failed: {e}")
            return self._fallback_analysis(image_data, context)

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "qwen-vl",
            "model_name": self.model_name,
            "base_url": self.base_url,
            "initialized": self._initialized,
            "supported_models": self.SUPPORTED_MODELS,
        }
