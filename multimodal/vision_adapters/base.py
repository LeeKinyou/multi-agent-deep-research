"""
视觉模型适配器基类

定义所有视觉模型适配器必须实现的统一接口。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    """数据点"""
    label: str
    value: float
    unit: str = ""


@dataclass
class ChartAnalysisResult:
    """图表分析结果"""
    chart_type: str
    title: str
    description: str
    data_points: List[DataPoint] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_analysis: str = ""
    model_name: str = ""


class BaseVisionAdapter(ABC):
    """
    视觉模型适配器基类

    所有具体的视觉模型适配器必须继承此类并实现抽象方法。
    """

    def __init__(
        self,
        model_name: str,
        api_key: str = "",
        base_url: str = "",
        **kwargs,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.extra_config = kwargs
        self._initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化模型客户端

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    def analyze_image(
        self,
        image_data: bytes,
        image_format: str = "PNG",
        context: str = "",
    ) -> ChartAnalysisResult:
        """
        分析图像

        Args:
            image_data: 图像数据（bytes）
            image_format: 图像格式（PNG, JPEG, WEBP等）
            context: 图像上下文文本

        Returns:
            ChartAnalysisResult: 分析结果
        """
        pass

    def analyze_image_file(
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
        import os

        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            format_map = {
                ".png": "PNG",
                ".jpg": "JPEG",
                ".jpeg": "JPEG",
                ".webp": "WEBP",
                ".gif": "GIF",
                ".bmp": "BMP",
            }
            ext = os.path.splitext(image_path)[1].lower()
            image_format = format_map.get(ext, "PNG")

            return self.analyze_image(image_data, image_format, context)

        except Exception as e:
            logger.error(f"Failed to analyze image {image_path}: {e}")
            return ChartAnalysisResult(
                chart_type="unknown",
                title="",
                description=f"分析失败: {str(e)}",
                confidence=0.0,
                model_name=self.model_name,
            )

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            Dict: 包含模型名称、提供商、状态等信息
        """
        pass

    def _build_chart_analysis_prompt(self, context: str) -> str:
        """构建标准的图表分析提示词"""
        context_section = f"\n上下文信息：{context}" if context else ""

        return f"""你是一个专业的数据图表分析专家。请仔细分析以下图表，并按要求提取信息。

请按照以下 JSON 格式返回分析结果：
{{
    "chart_type": "图表类型（bar/line/pie/scatter/table/other）",
    "title": "图表标题",
    "description": "图表的简要描述（2-3句话）",
    "data_points": [
        {{
            "label": "数据标签",
            "value": 数值（数字）,
            "unit": "单位（如百分比、万元等）"
        }}
    ],
    "trends": ["趋势描述1", "趋势描述2"],
    "key_insights": ["关键洞察1", "关键洞察2"],
    "confidence": 0.0-1.0
}}

要求：
1. 准确识别图表类型
2. 尽可能提取所有可见数据点的数值
3. 描述数据趋势和模式
4. 提供 2-3 个关键洞察
5. 评估分析的置信度{context_section}

请直接返回 JSON，不要包含其他文字。"""

    def _parse_analysis_response(self, content: str) -> ChartAnalysisResult:
        """解析模型的分析响应"""
        import json

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")

            data = json.loads(content[start:end])

            data_points = []
            for dp in data.get("data_points", []):
                data_points.append(DataPoint(
                    label=dp.get("label", ""),
                    value=float(dp.get("value", 0)),
                    unit=dp.get("unit", ""),
                ))

            return ChartAnalysisResult(
                chart_type=data.get("chart_type", "other"),
                title=data.get("title", ""),
                description=data.get("description", ""),
                data_points=data_points,
                trends=data.get("trends", []),
                key_insights=data.get("key_insights", []),
                confidence=float(data.get("confidence", 0.5)),
                raw_analysis=content,
                model_name=self.model_name,
            )

        except Exception as e:
            logger.warning(f"Failed to parse analysis response: {e}")
            return ChartAnalysisResult(
                chart_type="unknown",
                title="",
                description=f"解析失败: {str(e)}",
                confidence=0.0,
                raw_analysis=content,
                model_name=self.model_name,
            )

    def _fallback_analysis(
        self,
        image_data: bytes,
        context: str,
    ) -> ChartAnalysisResult:
        """降级分析（当模型不可用时）"""
        return ChartAnalysisResult(
            chart_type="unknown",
            title="视觉模型不可用",
            description=f"视觉大模型暂时不可用。{context[:200] if context else ''}",
            confidence=0.0,
            model_name=self.model_name,
        )
