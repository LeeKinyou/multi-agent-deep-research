"""
多模态处理工具 - 供 ResearchAgent 使用

提供：
- PDF 文档解析工具
- 网页可视化提取工具
- 图表分析工具
- 可视化生成工具
"""

import os
import logging
from typing import Optional

from crewai.tools import tool

logger = logging.getLogger(__name__)


@tool("PDF Document Analyzer")
def analyze_pdf(
    pdf_path: str,
    extract_charts: bool = True,
) -> str:
    """分析 PDF 文档，提取文本和图表数据。输入 PDF 文件路径，返回文档内容摘要和图表分析结果。

    Args:
        pdf_path: PDF 文件的绝对或相对路径
        extract_charts: 是否提取和分析图表，默认 True
    """
    try:
        from multimodal.pdf_extractor import PDFExtractor
        from multimodal.vision_analyzer import VisionAnalyzer
        from multimodal.context_linker import ContextLinker

        extractor = PDFExtractor()
        page_data_list = extractor.extract(pdf_path)

        if not page_data_list:
            return f"无法解析 PDF: {pdf_path}"

        # 提取文本内容
        full_text = "\n\n".join(
            f"[Page {p.page_number + 1}]\n{p.text}"
            for p in page_data_list
        )

        result_parts = [
            f"## PDF 文档分析结果",
            f"**文件**: {pdf_path}",
            f"**页数**: {len(page_data_list)}",
            f"**包含图表**: {any(p.has_charts for p in page_data_list)}",
            f"**包含表格**: {any(p.has_tables for p in page_data_list)}",
            "",
            "## 文档内容摘要",
            full_text[:3000],
        ]

        # 提取和分析图表
        if extract_charts:
            charts = extractor.get_charts_only(page_data_list)
            stats = extractor.get_stats()

            result_parts.append(f"\n## 图表统计")
            result_parts.append(f"- 总图像数: {stats['total_images']}")
            result_parts.append(f"- 图表: {stats['charts']}")
            result_parts.append(f"- 表格: {stats['tables']}")

            if charts:
                result_parts.append(f"\n## 图表分析")

                vision_analyzer = VisionAnalyzer()

                for i, chart in enumerate(charts[:5]):  # 最多分析5个图表
                    analysis = vision_analyzer.analyze_chart(
                        chart.image_data,
                        chart.format,
                        context=chart.surrounding_text[:500],
                    )

                    result_parts.append(f"\n### 图表 {i + 1} (Page {chart.page_number + 1})")
                    result_parts.append(f"**类型**: {analysis.chart_type}")
                    result_parts.append(f"**标题**: {analysis.title}")
                    result_parts.append(f"**描述**: {analysis.description}")

                    if analysis.data_points:
                        result_parts.append("**提取数据**:")
                        for dp in analysis.data_points:
                            result_parts.append(f"  - {dp.label}: {dp.value} {dp.unit}")

                    if analysis.key_insights:
                        result_parts.append("**关键洞察**:")
                        for insight in analysis.key_insights:
                            result_parts.append(f"  - {insight}")

        return "\n".join(result_parts)

    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
        return f"PDF 分析失败: {str(e)}"


@tool("Web Visualization Extractor")
def extract_web_visualizations(url: str) -> str:
    """从网页中提取数据可视化元素（图表、统计图等）。输入完整的网页 URL，返回提取的可视化元素及其分析。

    Args:
        url: 要分析的网页 URL
    """
    try:
        from multimodal.web_extractor import WebVisualExtractor
        from multimodal.vision_analyzer import VisionAnalyzer

        extractor = WebVisualExtractor()
        images = extractor.extract_from_url(url)

        if not images:
            return f"未从网页 {url} 提取到可视化元素"

        result_parts = [
            f"## 网页可视化提取结果",
            f"**URL**: {url}",
            f"**提取元素数**: {len(images)}",
            "",
        ]

        stats = extractor.get_stats()
        result_parts.append(f"## 统计")
        result_parts.append(f"- 图表: {stats['charts']}")
        result_parts.append(f"- 表格: {stats['tables']}")
        result_parts.append(f"- 其他图像: {stats['figures']}")

        # 分析图表
        charts = extractor.get_charts_only()
        if charts:
            vision_analyzer = VisionAnalyzer()

            result_parts.append(f"\n## 图表分析")

            for i, chart in enumerate(charts[:5]):
                analysis = vision_analyzer.analyze_chart(
                    chart.image_data,
                    "PNG",
                    context=chart.surrounding_text[:500],
                )

                result_parts.append(f"\n### 图表 {i + 1}")
                result_parts.append(f"**类型**: {analysis.chart_type}")
                result_parts.append(f"**标题**: {analysis.title}")
                result_parts.append(f"**描述**: {analysis.description}")

                if analysis.data_points:
                    result_parts.append("**提取数据**:")
                    for dp in analysis.data_points:
                        result_parts.append(f"  - {dp.label}: {dp.value} {dp.unit}")

        return "\n".join(result_parts)

    except Exception as e:
        logger.error(f"Web visualization extraction failed: {e}")
        return f"网页可视化提取失败: {str(e)}"


@tool("Chart Data Extractor")
def extract_chart_data(image_path: str) -> str:
    """从图表图像中提取定量数据。输入图表图像文件路径，返回提取的数据点和趋势分析。

    Args:
        image_path: 图表图像文件路径
    """
    try:
        from multimodal.vision_analyzer import VisionAnalyzer

        analyzer = VisionAnalyzer()
        analysis = analyzer.analyze_image(image_path)

        result_parts = [
            f"## 图表数据分析",
            f"**图像**: {image_path}",
            f"**图表类型**: {analysis.chart_type}",
            f"**标题**: {analysis.title}",
            f"**置信度**: {analysis.confidence:.1%}",
            "",
            f"## 描述",
            analysis.description,
            "",
        ]

        if analysis.data_points:
            result_parts.append("## 提取数据")
            for dp in analysis.data_points:
                result_parts.append(f"- {dp.label}: {dp.value} {dp.unit}")
            result_parts.append("")

        if analysis.trends:
            result_parts.append("## 趋势")
            for trend in analysis.trends:
                result_parts.append(f"- {trend}")
            result_parts.append("")

        if analysis.key_insights:
            result_parts.append("## 关键洞察")
            for insight in analysis.key_insights:
                result_parts.append(f"- {insight}")

        return "\n".join(result_parts)

    except Exception as e:
        logger.error(f"Chart data extraction failed: {e}")
        return f"图表数据提取失败: {str(e)}"


@tool("Chart Generator")
def generate_chart(
    chart_type: str,
    title: str,
    data_json: str,
    x_label: str = "",
    y_label: str = "",
) -> str:
    """根据数据生成标准化图表。输入图表类型、标题和数据（JSON格式），返回生成的图表文件路径和Markdown引用。

    Args:
        chart_type: 图表类型（bar/line/pie/scatter）
        title: 图表标题
        data_json: JSON格式的数据，例如 [{"label": "Q1", "value": 100}, {"label": "Q2", "value": 150}]
        x_label: X轴标签
        y_label: Y轴标签
    """
    try:
        import json
        from multimodal.chart_generator import ChartGenerator, ChartSpec

        data = json.loads(data_json)

        spec = ChartSpec(
            chart_type=chart_type,
            title=title,
            data=data,
            x_label=x_label,
            y_label=y_label,
        )

        generator = ChartGenerator()
        result = generator.generate_chart(spec)

        return (
            f"## 图表生成成功\n\n"
            f"**类型**: {result['chart_type']}\n"
            f"**标题**: {result['title']}\n"
            f"**数据点数**: {result['data_points']}\n"
            f"**文件**: {result['filepath']}\n\n"
            f"{result['markdown_ref']}"
        )

    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return f"图表生成失败: {str(e)}"


def get_multimodal_tools():
    """获取多模态处理工具列表"""
    return [
        analyze_pdf,
        extract_web_visualizations,
        extract_chart_data,
        generate_chart,
    ]
