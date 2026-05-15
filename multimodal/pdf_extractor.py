"""
PDF 文档解析与图像提取模块

功能：
- PDF 文档解析（文本 + 图像）
- 按页面提取文本和图像
- 图像分类（图表、表格、装饰性图片）
- 图像上下文关联（提取图片周围的文本）
"""

import os
import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from io import BytesIO

logger = logging.getLogger(__name__)


@dataclass
class ExtractedImage:
    """提取的图像数据"""
    image_id: str
    page_number: int
    image_data: bytes
    width: int
    height: int
    format: str  # PNG, JPEG, etc.
    image_type: str = "unknown"  # chart, table, figure, decorative
    surrounding_text: str = ""
    caption: str = ""


@dataclass
class PDFPageData:
    """PDF 页面数据"""
    page_number: int
    text: str
    images: List[ExtractedImage] = field(default_factory=list)
    has_charts: bool = False
    has_tables: bool = False


class PDFExtractor:
    """
    PDF 文档解析器

    提取 PDF 文档中的文本和图像，并对图像进行分类。
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        dpi: int = 150,
    ):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "multimodal", "extracted"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.dpi = dpi
        self._extracted_images: List[ExtractedImage] = []

    def extract(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
    ) -> List[PDFPageData]:
        """
        提取 PDF 文档的文本和图像

        Args:
            pdf_path: PDF 文件路径
            pages: 要提取的页码列表，None 表示全部

        Returns:
            List[PDFPageData]: 页面数据列表
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
            return []

        doc = fitz.open(pdf_path)
        page_data_list = []

        page_range = pages if pages else range(len(doc))

        for page_num in page_range:
            if page_num >= len(doc):
                break

            page = doc[page_num]
            page_data = self._extract_page(page, page_num)
            page_data_list.append(page_data)

        doc.close()
        logger.info(f"Extracted {len(page_data_list)} pages from {pdf_path}")
        return page_data_list

    def extract_from_bytes(
        self,
        pdf_bytes: bytes,
        pages: Optional[List[int]] = None,
    ) -> List[PDFPageData]:
        """从 PDF 字节数据提取"""
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
            return []

        doc = fitz.open("pdf", pdf_bytes)
        page_data_list = []

        page_range = pages if pages else range(len(doc))

        for page_num in page_range:
            if page_num >= len(doc):
                break

            page = doc[page_num]
            page_data = self._extract_page(page, page_num)
            page_data_list.append(page_data)

        doc.close()
        return page_data_list

    def _extract_page(self, page, page_num: int) -> PDFPageData:
        """提取单个页面的文本和图像"""
        # 提取文本
        text = page.get_text("text")

        # 提取图像
        images = self._extract_images_from_page(page, page_num, text)

        # 检测是否包含图表和表格
        has_charts = any(img.image_type == "chart" for img in images)
        has_tables = any(img.image_type == "table" for img in images)

        return PDFPageData(
            page_number=page_num,
            text=text,
            images=images,
            has_charts=has_charts,
            has_tables=has_tables,
        )

    def _extract_images_from_page(
        self,
        page,
        page_num: int,
        surrounding_text: str,
    ) -> List[ExtractedImage]:
        """从页面提取图像"""
        images = []

        try:
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)

                if not base_image:
                    continue

                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_width = base_image["width"]
                image_height = base_image["height"]

                # 过滤太小的图片（可能是图标或装饰）
                if image_width < 100 or image_height < 100:
                    continue

                image_id = hashlib.md5(
                    f"{page_num}_{img_index}_{len(image_bytes)}".encode()
                ).hexdigest()[:12]

                # 分类图像
                image_type = self._classify_image(image_bytes, image_width, image_height)

                # 提取图像周围的文本
                context = self._extract_image_context(page, img_index, surrounding_text)

                # 提取标题（如果有）
                caption = self._extract_caption(page, img_index)

                extracted = ExtractedImage(
                    image_id=image_id,
                    page_number=page_num,
                    image_data=image_bytes,
                    width=image_width,
                    height=image_height,
                    format=image_ext.upper(),
                    image_type=image_type,
                    surrounding_text=context,
                    caption=caption,
                )

                images.append(extracted)
                self._extracted_images.append(extracted)

                # 保存图像到文件
                self._save_image(extracted)

        except Exception as e:
            logger.warning(f"Failed to extract images from page {page_num}: {e}")

        return images

    def _classify_image(
        self,
        image_bytes: bytes,
        width: int,
        height: int,
    ) -> str:
        """
        分类图像类型

        基于图像尺寸和简单启发式规则进行分类
        """
        aspect_ratio = width / max(height, 1)

        # 宽幅图像可能是图表
        if aspect_ratio > 1.5:
            return "chart"

        # 接近正方形且较大可能是图表或图形
        if width > 300 and height > 300:
            if 0.8 < aspect_ratio < 1.2:
                return "chart"

        # 长宽比接近表格
        if 0.5 < aspect_ratio < 2.0 and width > 200 and height > 150:
            return "table"

        return "figure"

    def _extract_image_context(self, page, img_index: int, full_text: str) -> str:
        """提取图像周围的文本上下文"""
        # 简单实现：返回页面文本的前 500 字符作为上下文
        return full_text[:500] if full_text else ""

    def _extract_caption(self, page, img_index: int) -> str:
        """提取图像标题"""
        # 简单实现：尝试从页面文本中提取包含"图"、"Figure"的行
        text = page.get_text("text")
        lines = text.split("\n")

        for line in lines:
            line_stripped = line.strip()
            if any(
                keyword in line_stripped
                for keyword in ["图", "Figure", "Fig.", "图表", "表"]
            ):
                return line_stripped

        return ""

    def _save_image(self, image: ExtractedImage) -> str:
        """保存图像到文件"""
        filepath = os.path.join(
            self.output_dir,
            f"{image.image_id}.{image.format.lower()}",
        )

        try:
            with open(filepath, "wb") as f:
                f.write(image.image_data)
            return filepath
        except Exception as e:
            logger.error(f"Failed to save image {image.image_id}: {e}")
            return ""

    def get_charts_only(self, page_data_list: List[PDFPageData]) -> List[ExtractedImage]:
        """只获取图表类型的图像"""
        charts = []
        for page_data in page_data_list:
            for img in page_data.images:
                if img.image_type in ("chart", "table"):
                    charts.append(img)
        return charts

    def get_stats(self) -> Dict[str, Any]:
        """获取提取统计信息"""
        return {
            "total_images": len(self._extracted_images),
            "charts": sum(1 for img in self._extracted_images if img.image_type == "chart"),
            "tables": sum(1 for img in self._extracted_images if img.image_type == "table"),
            "figures": sum(1 for img in self._extracted_images if img.image_type == "figure"),
        }
