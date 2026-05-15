"""
网页复杂可视化内容提取模块

功能：
- 从网页中提取图像和图表
- 识别数据可视化元素
- 提取 SVG/Canvas 渲染的图表
- 图像上下文关联
"""

import os
import re
import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WebImageData:
    """网页图像数据"""
    image_id: str
    url: str
    src: str
    alt_text: str
    width: int
    height: int
    image_type: str = "unknown"
    surrounding_text: str = ""
    caption: str = ""
    image_data: bytes = b""


class WebVisualExtractor:
    """
    网页可视化内容提取器

    从网页中提取数据可视化元素，包括：
    - 静态图片（PNG, JPEG, SVG）
    - 图表元素
    - 数据表格
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        min_width: int = 200,
        min_height: int = 150,
    ):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "..", "data", "multimodal", "web_images"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.min_width = min_width
        self.min_height = min_height
        self._extracted: List[WebImageData] = []

    def extract_from_html(
        self,
        html_content: str,
        base_url: str = "",
    ) -> List[WebImageData]:
        """
        从 HTML 内容中提取可视化元素

        Args:
            html_content: HTML 内容
            base_url: 基础 URL（用于解析相对路径）

        Returns:
            List[WebImageData]: 提取的图像数据列表
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("BeautifulSoup not installed")
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        images = []

        # 提取 img 标签
        for img_tag in soup.find_all("img"):
            image_data = self._process_img_tag(img_tag, base_url, html_content)
            if image_data:
                images.append(image_data)

        # 提取 SVG 元素
        for svg_tag in soup.find_all("svg"):
            svg_data = self._process_svg_tag(svg_tag, base_url, html_content)
            if svg_data:
                images.append(svg_data)

        # 提取 canvas 元素
        for canvas_tag in soup.find_all("canvas"):
            canvas_data = self._process_canvas_tag(canvas_tag, base_url, html_content)
            if canvas_data:
                images.append(canvas_data)

        self._extracted.extend(images)
        logger.info(f"Extracted {len(images)} visual elements from HTML")
        return images

    def extract_from_url(
        self,
        url: str,
    ) -> List[WebImageData]:
        """
        从 URL 提取可视化元素

        Args:
            url: 网页 URL

        Returns:
            List[WebImageData]: 提取的图像数据列表
        """
        import requests

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            return self.extract_from_html(response.text, base_url=url)

        except Exception as e:
            logger.error(f"Failed to extract from URL {url}: {e}")
            return []

    def _process_img_tag(
        self,
        img_tag,
        base_url: str,
        html_content: str,
    ) -> Optional[WebImageData]:
        """处理 img 标签"""
        src = img_tag.get("src", "")
        if not src:
            return None

        # 解析相对 URL
        if base_url and not src.startswith(("http://", "https://", "data:")):
            from urllib.parse import urljoin
            src = urljoin(base_url, src)

        # 获取尺寸
        width = self._parse_dimension(img_tag.get("width", 0))
        height = self._parse_dimension(img_tag.get("height", 0))

        # 过滤太小的图片
        if width < self.min_width or height < self.min_height:
            return None

        # 过滤图标和装饰性图片
        src_lower = src.lower()
        if any(
            keyword in src_lower
            for keyword in ["icon", "logo", "avatar", "favicon", "spacer", "pixel"]
        ):
            return None

        alt_text = img_tag.get("alt", "")
        image_id = hashlib.md5(src.encode()).hexdigest()[:12]

        # 分类
        image_type = self._classify_web_image(src, alt_text, width, height)

        # 提取上下文
        context = self._extract_context(img_tag, html_content)

        # 提取标题
        caption = self._extract_caption_from_html(img_tag)

        image_data = WebImageData(
            image_id=image_id,
            url=base_url,
            src=src,
            alt_text=alt_text,
            width=width,
            height=height,
            image_type=image_type,
            surrounding_text=context,
            caption=caption,
        )

        # 下载图像数据
        self._download_image(image_data)

        return image_data

    def _process_svg_tag(
        self,
        svg_tag,
        base_url: str,
        html_content: str,
    ) -> Optional[WebImageData]:
        """处理 SVG 元素"""
        svg_content = str(svg_tag)
        image_id = hashlib.md5(svg_content.encode()).hexdigest()[:12]

        width = self._parse_dimension(svg_tag.get("width", 0))
        height = self._parse_dimension(svg_tag.get("height", 0))

        if width < self.min_width or height < self.min_height:
            return None

        context = self._extract_context(svg_tag, html_content)

        return WebImageData(
            image_id=image_id,
            url=base_url,
            src="inline_svg",
            alt_text=svg_tag.get("aria-label", ""),
            width=width,
            height=height,
            image_type="chart",
            surrounding_text=context,
            image_data=svg_content.encode("utf-8"),
        )

    def _process_canvas_tag(
        self,
        canvas_tag,
        base_url: str,
        html_content: str,
    ) -> Optional[WebImageData]:
        """处理 Canvas 元素"""
        canvas_id = canvas_tag.get("id", "")
        image_id = hashlib.md5(f"canvas_{canvas_id}".encode()).hexdigest()[:12]

        width = self._parse_dimension(canvas_tag.get("width", 0))
        height = self._parse_dimension(canvas_tag.get("height", 0))

        if width < self.min_width or height < self.min_height:
            return None

        context = self._extract_context(canvas_tag, html_content)

        return WebImageData(
            image_id=image_id,
            url=base_url,
            src=f"canvas:{canvas_id}",
            alt_text="",
            width=width,
            height=height,
            image_type="chart",
            surrounding_text=context,
        )

    def _classify_web_image(
        self,
        src: str,
        alt_text: str,
        width: int,
        height: int,
    ) -> str:
        """分类网页图像类型"""
        text_to_check = (src + " " + alt_text).lower()

        # 图表关键词
        chart_keywords = ["chart", "graph", "plot", "diagram", "visualization",
                         "图表", "统计", "趋势", "数据"]
        if any(kw in text_to_check for kw in chart_keywords):
            return "chart"

        # 表格关键词
        table_keywords = ["table", "表格", "数据表"]
        if any(kw in text_to_check for kw in table_keywords):
            return "table"

        # 截图关键词
        screenshot_keywords = ["screenshot", "截图", "界面"]
        if any(kw in text_to_check for kw in screenshot_keywords):
            return "screenshot"

        # 宽幅图像可能是图表
        aspect_ratio = width / max(height, 1)
        if aspect_ratio > 1.5 and width > 400:
            return "chart"

        return "figure"

    def _extract_context(self, tag, html_content: str) -> str:
        """提取元素周围的文本"""
        # 获取父元素的文本
        parent = tag.parent
        if parent:
            text = parent.get_text(separator=" ", strip=True)
            return text[:500]
        return ""

    def _extract_caption_from_html(self, tag) -> str:
        """从 HTML 中提取标题"""
        # 检查 figcaption
        parent = tag.parent
        if parent and parent.name == "figure":
            figcaption = parent.find("figcaption")
            if figcaption:
                return figcaption.get_text(strip=True)

        # 检查 alt 属性
        alt = tag.get("alt", "")
        if alt:
            return alt

        # 检查 title 属性
        title = tag.get("title", "")
        if title:
            return title

        return ""

    def _download_image(self, image_data: WebImageData) -> bool:
        """下载图像数据"""
        import requests

        if image_data.src.startswith("data:"):
            # Base64 数据
            import base64
            try:
                header, encoded = image_data.src.split(",", 1)
                image_data.image_data = base64.b64decode(encoded)
                return True
            except Exception:
                return False

        if image_data.src.startswith(("http://", "https://")):
            try:
                response = requests.get(image_data.src, timeout=15)
                response.raise_for_status()
                image_data.image_data = response.content

                # 保存到文件
                filepath = os.path.join(
                    self.output_dir,
                    f"{image_data.image_id}.png",
                )
                with open(filepath, "wb") as f:
                    f.write(image_data.image_data)

                return True
            except Exception as e:
                logger.warning(f"Failed to download image: {e}")
                return False

        return False

    def _parse_dimension(self, value: Any) -> int:
        """解析尺寸值"""
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.match(r"(\d+)", value)
            return int(match.group(1)) if match else 0
        return 0

    def get_charts_only(self) -> List[WebImageData]:
        """只获取图表类型的图像"""
        return [img for img in self._extracted if img.image_type == "chart"]

    def get_stats(self) -> Dict[str, Any]:
        """获取提取统计"""
        return {
            "total_images": len(self._extracted),
            "charts": sum(1 for img in self._extracted if img.image_type == "chart"),
            "tables": sum(1 for img in self._extracted if img.image_type == "table"),
            "figures": sum(1 for img in self._extracted if img.image_type == "figure"),
        }
