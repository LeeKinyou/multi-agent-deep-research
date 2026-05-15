"""
图文上下文关联模块

功能：
- 关联提取的视觉数据与对应文本内容
- 维护文档上下文结构
- 生成连贯的多模态报告
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TextImageLink:
    """图文关联数据"""
    text_section: str
    image_id: str
    image_type: str
    image_analysis: str
    chart_data: Optional[List[Dict[str, Any]]] = None
    relevance_score: float = 0.0
    position: int = 0


@dataclass
class DocumentContext:
    """文档上下文"""
    source: str
    sections: List[Dict[str, Any]] = field(default_factory=list)
    image_links: List[TextImageLink] = field(default_factory=list)


class ContextLinker:
    """
    上下文关联器

    将提取的视觉数据与文本内容进行关联，
    确保多模态报告的连贯性。
    """

    def __init__(self):
        self._contexts: Dict[str, DocumentContext] = {}
        self._image_analyses: Dict[str, Any] = {}

    def register_analysis(
        self,
        image_id: str,
        analysis,
    ) -> None:
        """
        注册图像分析结果

        Args:
            image_id: 图像 ID
            analysis: ChartAnalysisResult 对象
        """
        self._image_analyses[image_id] = analysis

    def create_link(
        self,
        text_section: str,
        image_id: str,
        image_type: str,
        position: int = 0,
    ) -> TextImageLink:
        """
        创建图文关联

        Args:
            text_section: 关联的文本段落
            image_id: 图像 ID
            image_type: 图像类型
            position: 在文档中的位置

        Returns:
            TextImageLink: 图文关联对象
        """
        analysis = self._image_analyses.get(image_id)
        analysis_text = analysis.description if analysis else ""
        chart_data = None

        if analysis and analysis.data_points:
            chart_data = [
                {"label": dp.label, "value": dp.value}
                for dp in analysis.data_points
            ]

        # 计算关联度
        relevance = self._calculate_relevance(text_section, analysis)

        link = TextImageLink(
            text_section=text_section,
            image_id=image_id,
            image_type=image_type,
            image_analysis=analysis_text,
            chart_data=chart_data,
            relevance_score=relevance,
            position=position,
        )

        return link

    def build_document_context(
        self,
        source: str,
        text_sections: List[str],
        image_ids: List[str],
    ) -> DocumentContext:
        """
        构建文档上下文

        Args:
            source: 文档来源
            text_sections: 文本段落列表
            image_ids: 图像 ID 列表

        Returns:
            DocumentContext: 文档上下文
        """
        context = DocumentContext(source=source)

        # 添加文本段落
        for i, section in enumerate(text_sections):
            context.sections.append({
                "type": "text",
                "content": section,
                "position": i,
            })

        # 关联图像
        for i, image_id in enumerate(image_ids):
            analysis = self._image_analyses.get(image_id)
            if not analysis:
                continue

            # 找到最相关的文本段落
            best_section_idx = self._find_best_section(
                analysis.description,
                text_sections,
            )

            if best_section_idx >= 0:
                link = self.create_link(
                    text_section=text_sections[best_section_idx],
                    image_id=image_id,
                    image_type=analysis.chart_type,
                    position=best_section_idx + 1,
                )
                context.image_links.append(link)

                # 在文档上下文中插入图像
                context.sections.insert(
                    best_section_idx + 1,
                    {
                        "type": "image",
                        "image_id": image_id,
                        "analysis": analysis,
                        "link": link,
                        "position": best_section_idx + 1,
                    },
                )

        self._contexts[source] = context
        return context

    def generate_markdown_report(
        self,
        context: DocumentContext,
        chart_generator=None,
    ) -> str:
        """
        生成 Markdown 格式的报告

        Args:
            context: 文档上下文
            chart_generator: 图表生成器（可选）

        Returns:
            str: Markdown 格式的报告
        """
        md_parts = []

        for section in context.sections:
            if section["type"] == "text":
                md_parts.append(section["content"])

            elif section["type"] == "image":
                analysis = section.get("analysis")
                if analysis:
                    if chart_generator:
                        chart_result = chart_generator.generate_from_analysis(
                            analysis,
                            filename=f"chart_{section['image_id']}.png",
                        )
                        md_parts.append(
                            chart_generator.generate_markdown_section(
                                analysis,
                                chart_result,
                            )
                        )
                    else:
                        md_parts.append(f"### {analysis.title}\n")
                        md_parts.append(f"{analysis.description}\n")

                        if analysis.trends:
                            md_parts.append("**趋势**:\n")
                            for trend in analysis.trends:
                                md_parts.append(f"- {trend}\n")
                            md_parts.append("\n")

                        if analysis.key_insights:
                            md_parts.append("**洞察**:\n")
                            for insight in analysis.key_insights:
                                md_parts.append(f"- {insight}\n")
                            md_parts.append("\n")

        return "\n\n".join(md_parts)

    def _calculate_relevance(
        self,
        text_section: str,
        analysis,
    ) -> float:
        """计算文本与图像的关联度"""
        if not analysis or not text_section:
            return 0.0

        # 简单关键词匹配
        text_lower = text_section.lower()
        analysis_lower = analysis.description.lower()

        # 提取关键词
        keywords = set()
        for word in analysis_lower.split():
            if len(word) > 3:
                keywords.add(word)

        if not keywords:
            return 0.5

        matches = sum(1 for kw in keywords if kw in text_lower)
        return matches / len(keywords)

    def _find_best_section(
        self,
        description: str,
        sections: List[str],
    ) -> int:
        """找到与描述最相关的文本段落"""
        if not sections or not description:
            return 0

        best_idx = 0
        best_score = 0

        desc_words = set(description.lower().split())

        for i, section in enumerate(sections):
            section_words = set(section.lower().split())
            common = desc_words & section_words
            score = len(common) / max(len(desc_words), 1)

            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx

    def get_context(self, source: str) -> Optional[DocumentContext]:
        """获取文档上下文"""
        return self._contexts.get(source)

    def get_all_links(self) -> List[TextImageLink]:
        """获取所有图文关联"""
        links = []
        for context in self._contexts.values():
            links.extend(context.image_links)
        return links
