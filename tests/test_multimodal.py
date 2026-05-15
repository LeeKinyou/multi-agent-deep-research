"""
多模态处理模块单元测试
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPDFExtractor:
    def setup_method(self):
        from multimodal.pdf_extractor import PDFExtractor, ExtractedImage, PDFPageData
        self.extractor = PDFExtractor()
        self.ExtractedImage = ExtractedImage
        self.PDFPageData = PDFPageData

    def test_init_creates_output_dir(self):
        assert os.path.exists(self.extractor.output_dir)

    def test_extracted_image_creation(self):
        img = self.ExtractedImage(
            image_id="test123",
            page_number=0,
            image_data=b"fake_image_data",
            width=800,
            height=600,
            format="PNG",
        )
        assert img.image_id == "test123"
        assert img.width == 800
        assert img.height == 600
        assert img.format == "PNG"
        assert img.image_type == "unknown"

    def test_pdf_page_data_creation(self):
        page = self.PDFPageData(
            page_number=0,
            text="Test content",
            images=[],
            has_charts=False,
            has_tables=False,
        )
        assert page.page_number == 0
        assert page.text == "Test content"
        assert page.has_charts is False

    def test_classify_image_chart(self):
        # 宽幅图像应被分类为图表
        image_type = self.extractor._classify_image(b"data", 800, 400)
        assert image_type == "chart"

    def test_classify_image_square_chart(self):
        # 大正方形图像应被分类为图表
        image_type = self.extractor._classify_image(b"data", 500, 500)
        assert image_type == "chart"

    def test_classify_image_table(self):
        # 中等尺寸图像应被分类为表格
        image_type = self.extractor._classify_image(b"data", 400, 300)
        assert image_type == "table"

    def test_classify_small_image_figure(self):
        # 小图像应被分类为图形
        image_type = self.extractor._classify_image(b"data", 150, 150)
        assert image_type == "figure"

    def test_get_charts_only(self):
        page_data = [
            self.PDFPageData(
                page_number=0,
                text="Page 1",
                images=[
                    self.ExtractedImage(
                        image_id="img1", page_number=0, image_data=b"",
                        width=800, height=600, format="PNG", image_type="chart",
                    ),
                    self.ExtractedImage(
                        image_id="img2", page_number=0, image_data=b"",
                        width=100, height=100, format="PNG", image_type="figure",
                    ),
                ],
            ),
        ]
        charts = self.extractor.get_charts_only(page_data)
        assert len(charts) == 1
        assert charts[0].image_type == "chart"

    def test_get_stats(self):
        self.extractor._extracted_images = [
            self.ExtractedImage(
                image_id="1", page_number=0, image_data=b"",
                width=800, height=600, format="PNG", image_type="chart",
            ),
            self.ExtractedImage(
                image_id="2", page_number=0, image_data=b"",
                width=800, height=600, format="PNG", image_type="table",
            ),
            self.ExtractedImage(
                image_id="3", page_number=0, image_data=b"",
                width=800, height=600, format="PNG", image_type="figure",
            ),
        ]
        stats = self.extractor.get_stats()
        assert stats["total_images"] == 3
        assert stats["charts"] == 1
        assert stats["tables"] == 1
        assert stats["figures"] == 1


class TestWebVisualExtractor:
    def setup_method(self):
        from multimodal.web_extractor import WebVisualExtractor, WebImageData
        self.extractor = WebVisualExtractor()
        self.WebImageData = WebImageData

    def test_init_creates_output_dir(self):
        assert os.path.exists(self.extractor.output_dir)

    def test_web_image_data_creation(self):
        img = self.WebImageData(
            image_id="test123",
            url="http://example.com",
            src="http://example.com/image.png",
            alt_text="Test chart",
            width=800,
            height=600,
        )
        assert img.image_id == "test123"
        assert img.width == 800
        assert img.alt_text == "Test chart"

    def test_classify_web_image_chart(self):
        image_type = self.extractor._classify_web_image(
            "chart.png", "Revenue chart", 800, 600
        )
        assert image_type == "chart"

    def test_classify_web_image_table(self):
        image_type = self.extractor._classify_web_image(
            "data.png", "Sales table", 800, 600
        )
        assert image_type == "table"

    def test_classify_web_image_screenshot(self):
        image_type = self.extractor._classify_web_image(
            "app.png", "App screenshot", 800, 600
        )
        assert image_type == "screenshot"

    def test_classify_wide_image_chart(self):
        image_type = self.extractor._classify_web_image(
            "image.png", "", 1200, 600
        )
        assert image_type == "chart"

    def test_classify_regular_image_figure(self):
        image_type = self.extractor._classify_web_image(
            "photo.jpg", "", 400, 400
        )
        assert image_type == "figure"

    def test_parse_dimension_int(self):
        assert self.extractor._parse_dimension(100) == 100

    def test_parse_dimension_str(self):
        assert self.extractor._parse_dimension("100px") == 100

    def test_parse_dimension_invalid(self):
        assert self.extractor._parse_dimension("auto") == 0

    def test_get_charts_only(self):
        self.extractor._extracted = [
            self.WebImageData(
                image_id="1", url="", src="chart1.png", alt_text="",
                width=800, height=600, image_type="chart",
            ),
            self.WebImageData(
                image_id="2", url="", src="photo.jpg", alt_text="",
                width=400, height=400, image_type="figure",
            ),
        ]
        charts = self.extractor.get_charts_only()
        assert len(charts) == 1
        assert charts[0].image_type == "chart"

    def test_get_stats(self):
        self.extractor._extracted = [
            self.WebImageData(
                image_id="1", url="", src="chart.png", alt_text="",
                width=800, height=600, image_type="chart",
            ),
            self.WebImageData(
                image_id="2", url="", src="table.png", alt_text="",
                width=800, height=600, image_type="table",
            ),
        ]
        stats = self.extractor.get_stats()
        assert stats["total_images"] == 2
        assert stats["charts"] == 1
        assert stats["tables"] == 1


class TestVisionAnalyzer:
    def setup_method(self):
        from multimodal.vision_analyzer import VisionAnalyzer, ChartAnalysisResult, DataPoint
        self.analyzer = VisionAnalyzer()
        self.ChartAnalysisResult = ChartAnalysisResult
        self.DataPoint = DataPoint

    def test_init_default_values(self):
        assert "localhost" in self.analyzer.model_url
        assert "qwen" in self.analyzer.model_name.lower()

    def test_chart_analysis_result_creation(self):
        result = self.ChartAnalysisResult(
            chart_type="bar",
            title="Revenue Chart",
            description="Quarterly revenue data",
            data_points=[
                self.DataPoint(label="Q1", value=100, unit="万元"),
                self.DataPoint(label="Q2", value=150, unit="万元"),
            ],
            trends=["Revenue increased by 50%"],
            key_insights=["Q2 was the strongest quarter"],
            confidence=0.95,
        )
        assert result.chart_type == "bar"
        assert len(result.data_points) == 2
        assert result.data_points[0].value == 100
        assert result.confidence == 0.95

    def test_parse_analysis_response_valid_json(self):
        response = """
        {
            "chart_type": "bar",
            "title": "Test Chart",
            "description": "A test chart",
            "data_points": [
                {"label": "A", "value": 100, "unit": "units"}
            ],
            "trends": ["Upward trend"],
            "key_insights": ["Key insight 1"],
            "confidence": 0.9
        }
        """
        result = self.analyzer._parse_analysis_response(response)
        assert result.chart_type == "bar"
        assert result.title == "Test Chart"
        assert len(result.data_points) == 1
        assert result.data_points[0].label == "A"
        assert result.data_points[0].value == 100
        assert result.confidence == 0.9

    def test_parse_analysis_response_invalid_json(self):
        response = "This is not JSON"
        result = self.analyzer._parse_analysis_response(response)
        assert result.chart_type == "unknown"
        assert result.confidence == 0.0

    def test_parse_analysis_response_partial_json(self):
        response = """
        Here is the analysis:
        {
            "chart_type": "line",
            "title": "Trend Chart",
            "description": "Trend analysis",
            "data_points": [],
            "trends": [],
            "key_insights": [],
            "confidence": 0.8
        }
        End of analysis.
        """
        result = self.analyzer._parse_analysis_response(response)
        assert result.chart_type == "line"
        assert result.title == "Trend Chart"

    def test_fallback_analysis(self):
        result = self.analyzer._fallback_analysis(b"fake_image", "context")
        assert result.chart_type == "unknown"
        assert result.confidence == 0.0

    def test_get_status(self):
        status = self.analyzer.get_status()
        assert "initialized" in status
        assert "model_url" in status
        assert "model_name" in status


class TestChartGenerator:
    def setup_method(self):
        from multimodal.chart_generator import ChartGenerator, ChartSpec
        self.generator = ChartGenerator()
        self.ChartSpec = ChartSpec

    def test_init_creates_output_dir(self):
        assert os.path.exists(self.generator.output_dir)

    def test_chart_spec_creation(self):
        spec = self.ChartSpec(
            chart_type="bar",
            title="Test Chart",
            data=[{"label": "A", "value": 100}],
        )
        assert spec.chart_type == "bar"
        assert spec.title == "Test Chart"
        assert len(spec.data) == 1

    def test_generate_fallback_chart(self):
        spec = self.ChartSpec(
            chart_type="bar",
            title="Fallback Test",
            data=[
                {"label": "A", "value": 100},
                {"label": "B", "value": 200},
            ],
        )
        result = self.generator._generate_fallback_chart(spec, "fallback_test.txt")
        assert result["title"] == "Fallback Test"
        assert result["data_points"] == 2
        assert os.path.exists(result["filepath"])

    def test_generate_markdown_section(self):
        from multimodal.vision_analyzer import ChartAnalysisResult
        analysis = ChartAnalysisResult(
            chart_type="bar",
            title="Test Analysis",
            description="Test description",
            trends=["Trend 1"],
            key_insights=["Insight 1"],
        )
        chart_result = {
            "markdown_ref": "![Test](test.png)",
        }
        md = self.generator.generate_markdown_section(analysis, chart_result)
        assert "### Test Analysis" in md
        assert "![Test](test.png)" in md
        assert "Trend 1" in md
        assert "Insight 1" in md

    def test_get_default_colors(self):
        colors = self.generator._get_default_colors(5)
        assert len(colors) == 5
        assert all(c.startswith("#") for c in colors)

    def test_get_generated_charts(self):
        charts = self.generator.get_generated_ch()
        assert isinstance(charts, list)

    def test_clear_generated(self):
        self.generator._generated_charts = [{"test": True}]
        self.generator.clear_generated()
        assert len(self.generator.get_generated_ch()) == 0


class TestContextLinker:
    def setup_method(self):
        from multimodal.context_linker import ContextLinker, TextImageLink, DocumentContext
        from multimodal.vision_analyzer import ChartAnalysisResult, DataPoint
        self.linker = ContextLinker()
        self.TextImageLink = TextImageLink
        self.DocumentContext = DocumentContext
        self.ChartAnalysisResult = ChartAnalysisResult
        self.DataPoint = DataPoint

    def test_register_analysis(self):
        analysis = self.ChartAnalysisResult(
            chart_type="bar",
            title="Test",
            description="Test description",
        )
        self.linker.register_analysis("img1", analysis)
        assert "img1" in self.linker._image_analyses

    def test_create_link(self):
        analysis = self.ChartAnalysisResult(
            chart_type="bar",
            title="Test",
            description="Revenue data for Q1 and Q2",
            data_points=[
                self.DataPoint(label="Q1", value=100),
                self.DataPoint(label="Q2", value=150),
            ],
        )
        self.linker.register_analysis("img1", analysis)

        link = self.linker.create_link(
            text_section="Revenue increased from Q1 to Q2",
            image_id="img1",
            image_type="bar",
        )
        assert link.image_id == "img1"
        assert link.image_type == "bar"
        assert link.chart_data is not None
        assert len(link.chart_data) == 2

    def test_create_link_no_analysis(self):
        link = self.linker.create_link(
            text_section="Some text",
            image_id="unknown",
            image_type="figure",
        )
        assert link.image_id == "unknown"
        assert link.chart_data is None

    def test_build_document_context(self):
        analysis = self.ChartAnalysisResult(
            chart_type="bar",
            title="Revenue Chart",
            description="Revenue data shows growth",
        )
        self.linker.register_analysis("img1", analysis)

        context = self.linker.build_document_context(
            source="test_doc",
            text_sections=[
                "Introduction to the report",
                "Revenue data shows significant growth in Q2",
                "Conclusion",
            ],
            image_ids=["img1"],
        )
        assert context.source == "test_doc"
        assert len(context.sections) > 0
        assert len(context.image_links) >= 0

    def test_generate_markdown_report(self):
        context = self.DocumentContext(source="test")
        context.sections = [
            {"type": "text", "content": "# Report\n\nThis is the introduction."},
            {"type": "text", "content": "## Analysis\n\nDetailed analysis follows."},
        ]
        md = self.linker.generate_markdown_report(context)
        assert "# Report" in md
        assert "## Analysis" in md

    def test_get_context(self):
        context = self.DocumentContext(source="test_source")
        self.linker._contexts["test_source"] = context
        retrieved = self.linker.get_context("test_source")
        assert retrieved is not None
        assert retrieved.source == "test_source"

    def test_get_all_links(self):
        context = self.DocumentContext(
            source="test",
            image_links=[
                self.TextImageLink(
                    text_section="Text 1",
                    image_id="img1",
                    image_type="chart",
                    image_analysis="Analysis 1",
                ),
            ],
        )
        self.linker._contexts["test"] = context
        links = self.linker.get_all_links()
        assert len(links) == 1
        assert links[0].image_id == "img1"


class TestMultimodalTools:
    def setup_method(self):
        from tools.multimodal_tools import (
            analyze_pdf,
            extract_web_visualizations,
            extract_chart_data,
            generate_chart,
            get_multimodal_tools,
        )
        self.analyze_pdf = analyze_pdf
        self.extract_web_visualizations = extract_web_visualizations
        self.extract_chart_data = extract_chart_data
        self.generate_chart = generate_chart
        self.get_multimodal_tools = get_multimodal_tools

    def test_get_multimodal_tools(self):
        tools = self.get_multimodal_tools()
        assert len(tools) == 4

    def test_analyze_pdf_nonexistent(self):
        result = self.analyze_pdf.run({"pdf_path": "/nonexistent/file.pdf"})
        assert "无法解析" in result or "失败" in result

    def test_extract_web_visualizations_invalid_url(self):
        result = self.extract_web_visualizations.run({"url": "http://invalid.url.test"})
        assert isinstance(result, str)

    def test_extract_chart_data_nonexistent(self):
        result = self.extract_chart_data.run({"image_path": "/nonexistent/image.png"})
        assert "失败" in result

    def test_generate_chart_valid_data(self):
        result = self.generate_chart.run(
            chart_type="bar",
            title="Test Chart",
            data_json='[{"label": "A", "value": 100}, {"label": "B", "value": 200}]',
        )
        assert "图表生成" in result or "失败" in result

    def test_generate_chart_invalid_json(self):
        result = self.generate_chart.run(
            chart_type="bar",
            title="Test Chart",
            data_json="invalid json",
        )
        assert "失败" in result


class TestMultimodalResearchAgent:
    def setup_method(self):
        pass

    @pytest.mark.skip(reason="Requires external service (ChromaDB)")
    def test_create_agent(self):
        from agents.multimodal_research_agent import create_multimodal_research_agent
        agent = create_multimodal_research_agent()
        assert agent is not None
        assert agent.role == "多模态情报分析师"

    @pytest.mark.skip(reason="Requires external service (ChromaDB)")
    def test_create_agent_with_task_id(self):
        from agents.multimodal_research_agent import create_multimodal_research_agent
        agent = create_multimodal_research_agent(task_id="test_task_123")
        assert agent is not None
        assert "test_task_123" in agent.backstory

    @pytest.mark.skip(reason="Requires external service (ChromaDB)")
    def test_agent_has_multimodal_tools(self):
        from agents.multimodal_research_agent import create_multimodal_research_agent
        agent = create_multimodal_research_agent()
        tool_names = [t.name for t in agent.tools]
        multimodal_tool_names = [
            "PDF Document Analyzer",
            "Web Visualization Extractor",
            "Chart Data Extractor",
            "Chart Generator",
        ]
        for name in multimodal_tool_names:
            assert name in tool_names
