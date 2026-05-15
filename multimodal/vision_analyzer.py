"""
视觉大模型分析模块 - Qwen-VL 集成

功能：
- 图表解析（柱状图、折线图、饼图、散点图等）
- 定量数据提取
- 图表描述生成
- 趋势分析
"""

import os
import json
import logging
import base64
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from io import BytesIO

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
    chart_type: str  # bar, line, pie, scatter, table, other
    title: str
    description: str
    data_points: List[DataPoint] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_analysis: str = ""


class VisionAnalyzer:
    """
    视觉分析器 - 基于 Qwen-VL

    使用本地部署的 Qwen-VL 模型对图表进行解析，
    提取定量数据和上下文信息。
    """

    def __init__(
        self,
        model_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.model_url = model_url or os.getenv(
            "VISION_MODEL_URL", "http://localhost:1234/v1"
        )
        self.model_name = model_name or os.getenv(
            "VISION_MODEL_NAME", "qwen2.5-vl-7b-instruct"
        )
        self._client = None
        self._initialized = False

    def initialize(self) -> bool:
        """初始化视觉模型客户端"""
        try:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.model_url,
                api_key="not-needed",
            )

            # 健康检查
            self._client.models.list()
            self._initialized = True
            logger.info(f"Vision analyzer initialized: {self.model_name}")
            return True

        except Exception as e:
            logger.warning(f"Vision analyzer initialization failed: {e}")
            self._initialized = False
            return False

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
        if not self._initialized:
            if not self.initialize():
                return self._fallback_analysis(image_data, context)

        # 转换图像为 base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        data_uri = f"data:image/{image_format.lower()};base64,{base64_image}"

        prompt = self._build_analysis_prompt(context)

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
            logger.error(f"Vision analysis failed: {e}")
            return self._fallback_analysis(image_data, context)

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
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            format_map = {
                ".png": "PNG",
                ".jpg": "JPEG",
                ".jpeg": "JPEG",
                ".webp": "WEBP",
            }
            ext = os.path.splitext(image_path)[1].lower()
            image_format = format_map.get(ext, "PNG")

            return self.analyze_chart(image_data, image_format, context)

        except Exception as e:
            logger.error(f"Failed to analyze image {image_path}: {e}")
            return ChartAnalysisResult(
                chart_type="unknown",
                title="",
                description=f"分析失败: {str(e)}",
                confidence=0.0,
            )

    def _build_analysis_prompt(self, context: str) -> str:
        """构建图表分析提示词"""
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
        """解析分析响应"""
        try:
            # 提取 JSON
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
            )

        except Exception as e:
            logger.warning(f"Failed to parse analysis response: {e}")
            return ChartAnalysisResult(
                chart_type="unknown",
                title="",
                description=f"解析失败: {str(e)}",
                confidence=0.0,
                raw_analysis=content,
            )

    def _fallback_analysis(
        self,
        image_data: bytes,
        context: str,
    ) -> ChartAnalysisResult:
        """降级分析（当视觉模型不可用时）"""
        return ChartAnalysisResult(
            chart_type="unknown",
            title="视觉模型不可用",
            description=f"视觉大模型暂时不可用。{context[:200] if context else ''}",
            confidence=0.0,
        )

    def get_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        return {
            "initialized": self._initialized,
            "model_url": self.model_url,
            "model_name": self.model_name,
        }
