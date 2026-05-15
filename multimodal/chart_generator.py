"""
标准化可视化生成模块

功能：
- 基于提取数据生成标准图表
- 支持多种图表类型（柱状图、折线图、饼图、散点图）
- 生成 Markdown 兼容的图像
- 代码驱动的可视化生成
"""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChartSpec:
    """图表规格"""
    chart_type: str  # bar, line, pie, scatter
    title: str
    data: List[Dict[str, Any]]  # [{"label": "A", "value": 100}, ...]
    x_label: str = ""
    y_label: str = ""
    width: int = 800
    height: int = 400
    colors: Optional[List[str]] = None


class ChartGenerator:
    """
    图表生成器

    基于提取的数据生成标准化的可视化图表，
    并输出为 Markdown 兼容格式。
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
    ):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "multimodal", "generated_charts"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self._generated_charts: List[Dict[str, Any]] = []

    def generate_chart(
        self,
        spec: ChartSpec,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成图表

        Args:
            spec: 图表规格
            filename: 输出文件名（可选）

        Returns:
            Dict: 包含图表路径、Markdown 引用等信息
        """
        try:
            import matplotlib
            matplotlib.use("Agg")  # 非交互式后端
            import matplotlib.pyplot as plt
            import matplotlib.ticker as mticker
        except ImportError:
            logger.error("Matplotlib not installed. Run: pip install matplotlib")
            return self._generate_fallback_chart(spec, filename)

        if filename is None:
            import hashlib
            filename = hashlib.md5(
                f"{spec.title}{len(spec.data)}".encode()
            ).hexdigest()[:12] + ".png"

        filepath = os.path.join(self.output_dir, filename)

        try:
            fig, ax = plt.subplots(figsize=(spec.width / 100, spec.height / 100))

            labels = [d.get("label", "") for d in spec.data]
            values = [d.get("value", 0) for d in spec.data]

            colors = spec.colors or self._get_default_colors(len(values))

            if spec.chart_type == "bar":
                bars = ax.bar(range(len(labels)), values, color=colors)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha="right")

                # 添加数值标签
                for bar, val in zip(bars, values):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(values) * 0.01,
                        f"{val:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

            elif spec.chart_type == "line":
                ax.plot(range(len(labels)), values, marker="o", color=colors[0], linewidth=2)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha="right")

                # 添加数值标签
                for i, val in enumerate(values):
                    ax.annotate(
                        f"{val:.1f}",
                        (i, val),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha="center",
                        fontsize=8,
                    )

            elif spec.chart_type == "pie":
                ax.pie(
                    values,
                    labels=labels,
                    colors=colors,
                    autopct="%1.1f%%",
                    startangle=90,
                    textprops={"fontsize": 8},
                )

            elif spec.chart_type == "scatter":
                x_values = [d.get("x", i) for i, d in enumerate(spec.data)]
                y_values = [d.get("y", d.get("value", 0)) for d in spec.data]
                ax.scatter(x_values, y_values, color=colors[0], s=50, alpha=0.7)

            else:
                # 默认柱状图
                ax.bar(range(len(labels)), values, color=colors)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha="right")

            ax.set_title(spec.title, fontsize=12, fontweight="bold", pad=15)

            if spec.x_label:
                ax.set_xlabel(spec.x_label, fontsize=9)
            if spec.y_label:
                ax.set_ylabel(spec.y_label, fontsize=9)

            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches="tight")
            plt.close()

            result = {
                "filepath": filepath,
                "filename": filename,
                "markdown_ref": f"![{spec.title}](./{filename})",
                "chart_type": spec.chart_type,
                "title": spec.title,
                "data_points": len(spec.data),
            }

            self._generated_charts.append(result)
            logger.info(f"Chart generated: {filepath}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate chart: {e}")
            return self._generate_fallback_chart(spec, filename)

    def generate_from_analysis(
        self,
        analysis,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        从分析结果生成图表

        Args:
            analysis: ChartAnalysisResult 对象
            filename: 输出文件名

        Returns:
            Dict: 图表信息
        """
        data = [
            {"label": dp.label, "value": dp.value}
            for dp in analysis.data_points
        ]

        spec = ChartSpec(
            chart_type=analysis.chart_type if analysis.chart_type != "other" else "bar",
            title=analysis.title or "数据图表",
            data=data,
            y_label=analysis.data_points[0].unit if analysis.data_points else "",
        )

        return self.generate_chart(spec, filename)

    def generate_markdown_section(
        self,
        analysis,
        chart_result: Dict[str, Any],
    ) -> str:
        """
        生成 Markdown 图表段落

        Args:
            analysis: ChartAnalysisResult
            chart_result: 图表生成结果

        Returns:
            str: Markdown 格式的图表段落
        """
        md = f"""### {analysis.title}

{chart_result['markdown_ref']}

**图表描述**: {analysis.description}

"""

        if analysis.trends:
            md += "**趋势分析**:\n"
            for trend in analysis.trends:
                md += f"- {trend}\n"
            md += "\n"

        if analysis.key_insights:
            md += "**关键洞察**:\n"
            for insight in analysis.key_insights:
                md += f"- {insight}\n"
            md += "\n"

        return md

    def _generate_fallback_chart(
        self,
        spec: ChartSpec,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """降级方案：生成文本格式的图表"""
        if filename is None:
            filename = "fallback_chart.txt"

        filepath = os.path.join(self.output_dir, filename)

        # 生成简单的文本图表
        lines = [f"## {spec.title}", ""]
        for item in spec.data:
            label = item.get("label", "")
            value = item.get("value", 0)
            bar = "█" * int(value / max(d.get("value", 1) for d in spec.data) * 30)
            lines.append(f"  {label:15s} | {bar} {value}")

        lines.append("")

        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "filepath": filepath,
            "filename": filename,
            "markdown_ref": f"```\n{content}\n```",
            "chart_type": spec.chart_type,
            "title": spec.title,
            "data_points": len(spec.data),
            "fallback": True,
        }

    def _get_default_colors(self, count: int) -> List[str]:
        """获取默认颜色列表"""
        default_colors = [
            "#4C72B0", "#55A868", "#C44E52", "#8172B2",
            "#CCB974", "#64B5CD", "#E377C2", "#7F7F7F",
            "#BCBD22", "#17BECF",
        ]
        return [default_colors[i % len(default_colors)] for i in range(count)]

    def get_generated_ch(self) -> List[Dict[str, Any]]:
        """获取所有已生成的图表"""
        return self._generated_charts

    def clear_generated(self) -> None:
        """清空已生成的图表"""
        self._generated_charts.clear()
