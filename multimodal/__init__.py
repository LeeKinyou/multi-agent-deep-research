"""
多模态处理模块 - ResearchAgent 视觉信息融合

提供：
- PDF 文档解析与图像提取
- 网页复杂可视化内容提取
- 多视觉大模型适配器（Qwen-VL、GPT-4V、Claude、Gemini）
- 图表解析与定量数据提取
- 图像分割识别核心数据可视化
- 标准化可视化生成
- 图文上下文关联
"""

from multimodal.pdf_extractor import PDFExtractor, PDFPageData
from multimodal.web_extractor import WebVisualExtractor
from multimodal.vision_analyzer import VisionAnalyzer
from multimodal.vision_adapters.base import BaseVisionAdapter, ChartAnalysisResult, DataPoint
from multimodal.vision_adapters.factory import VisionModelFactory
from multimodal.chart_generator import ChartGenerator
from multimodal.context_linker import ContextLinker, TextImageLink

__all__ = [
    "PDFExtractor",
    "PDFPageData",
    "WebVisualExtractor",
    "VisionAnalyzer",
    "BaseVisionAdapter",
    "ChartAnalysisResult",
    "DataPoint",
    "VisionModelFactory",
    "ChartGenerator",
    "ContextLinker",
    "TextImageLink",
]
