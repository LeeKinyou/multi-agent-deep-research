"""
视觉大模型分析模块 - 多模型适配器集成

功能：
- 图表解析（柱状图、折线图、饼图、散点图等）
- 定量数据提取
- 图表描述生成
- 趋势分析
- 支持多种视觉大模型（Qwen-VL、GPT-4V、Claude、Gemini）
"""

import os
import logging
from typing import Optional, Dict, Any

from multimodal.vision_adapters.base import ChartAnalysisResult, DataPoint
from multimodal.vision_adapters.factory import VisionModelFactory

# Backward compatibility exports
__all__ = ["ChartAnalysisResult", "DataPoint"]

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """
    视觉分析器 - 多模型适配器

    使用适配器模式支持多种视觉大模型：
    - Qwen-VL 系列（本地部署或 DashScope）
    - OpenAI GPT-4V / GPT-4o
    - Anthropic Claude 3 系列
    - Google Gemini 系列
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider = provider or os.getenv("VISION_PROVIDER", "qwen-vl")
        self._adapter = VisionModelFactory.create_adapter(
            provider=self.provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )

    def initialize(self) -> bool:
        """初始化视觉模型"""
        return self._adapter.initialize()

    def analyze_chart(
        self,
        image_data: bytes,
        image_format: str = "PNG",
        context: str = "",
    ) -> ChartAnalysisResult:
        """
        分析图表

        Args:
            image_data: 图像数据（bytes）
            image_format: 图像格式
            context: 图像上下文文本

        Returns:
            ChartAnalysisResult: 分析结果
        """
        return self._adapter.analyze_image(image_data, image_format, context)

    def analyze_image(
        self,
        image_path: str,
        context: str = "",
    ) -> ChartAnalysisResult:
        """
        分析图像文件

        Args:
            image_path: 图像文件路径
            context: 上下文文本

        Returns:
            ChartAnalysisResult: 分析结果
        """
        return self._adapter.analyze_image_file(image_path, context)

    def get_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        return self._adapter.get_model_info()
