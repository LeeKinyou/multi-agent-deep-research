"""
视觉模型适配器模块单元测试
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBaseVisionAdapter:
    def setup_method(self):
        from multimodal.vision_adapters.base import BaseVisionAdapter, ChartAnalysisResult, DataPoint
        self.DataPoint = DataPoint
        self.ChartAnalysisResult = ChartAnalysisResult

    def test_data_point_creation(self):
        dp = self.DataPoint(label="Q1", value=100.5, unit="万元")
        assert dp.label == "Q1"
        assert dp.value == 100.5
        assert dp.unit == "万元"

    def test_chart_analysis_result_creation(self):
        result = self.ChartAnalysisResult(
            chart_type="bar",
            title="Revenue Chart",
            description="Quarterly revenue",
            data_points=[
                self.DataPoint(label="Q1", value=100, unit="万元"),
                self.DataPoint(label="Q2", value=150, unit="万元"),
            ],
            trends=["Growth trend"],
            key_insights=["Q2 outperformed Q1"],
            confidence=0.9,
        )
        assert result.chart_type == "bar"
        assert len(result.data_points) == 2
        assert result.confidence == 0.9

    def test_build_chart_analysis_prompt(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        prompt = adapter._build_chart_analysis_prompt("This is a revenue chart")
        assert "你是一个专业的数据图表分析专家" in prompt
        assert "This is a revenue chart" in prompt
        assert "chart_type" in prompt

    def test_parse_analysis_response_valid_json(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        response = """
        {
            "chart_type": "line",
            "title": "Sales Trend",
            "description": "Monthly sales data",
            "data_points": [
                {"label": "Jan", "value": 500, "unit": "units"},
                {"label": "Feb", "value": 600, "unit": "units"}
            ],
            "trends": ["Upward trend"],
            "key_insights": ["February sales increased"],
            "confidence": 0.85
        }
        """
        result = adapter._parse_analysis_response(response)
        assert result.chart_type == "line"
        assert result.title == "Sales Trend"
        assert len(result.data_points) == 2
        assert result.data_points[0].label == "Jan"
        assert result.data_points[0].value == 500
        assert result.confidence == 0.85

    def test_parse_analysis_response_invalid_json(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        response = "This is not valid JSON"
        result = adapter._parse_analysis_response(response)
        assert result.chart_type == "unknown"
        assert result.confidence == 0.0

    def test_parse_analysis_response_partial_json(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        response = """
        Here is the analysis:
        {
            "chart_type": "pie",
            "title": "Market Share",
            "description": "Company market share",
            "data_points": [],
            "trends": [],
            "key_insights": [],
            "confidence": 0.7
        }
        End of analysis.
        """
        result = adapter._parse_analysis_response(response)
        assert result.chart_type == "pie"
        assert result.title == "Market Share"

    def test_fallback_analysis(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        result = adapter._fallback_analysis(b"fake_image", "test context")
        assert result.chart_type == "unknown"
        assert result.confidence == 0.0
        assert "视觉模型不可用" in result.title


class TestQwenVLAdapter:
    def setup_method(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        self.adapter = QwenVLAdapter()

    def test_init_default_values(self):
        assert "qwen" in self.adapter.model_name.lower()
        assert "localhost" in self.adapter.base_url

    def test_init_custom_values(self):
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter(
            model_name="qwen-vl-max",
            api_key="test-key",
            base_url="https://custom.api/v1",
        )
        assert adapter.model_name == "qwen-vl-max"
        assert adapter.api_key == "test-key"
        assert adapter.base_url == "https://custom.api/v1"

    def test_get_model_info(self):
        info = self.adapter.get_model_info()
        assert info["provider"] == "qwen-vl"
        assert "qwen" in info["model_name"].lower()
        assert info["initialized"] is False

    @patch("openai.OpenAI")
    def test_initialize_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.return_value = []

        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        result = adapter.initialize()

        assert result is True
        assert adapter._initialized is True

    @patch("openai.OpenAI")
    def test_initialize_failure(self, mock_openai_class):
        mock_openai_class.side_effect = Exception("Connection failed")

        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        adapter = QwenVLAdapter()
        result = adapter.initialize()

        assert result is False
        assert adapter._initialized is False

    def test_analyze_image_not_initialized(self):
        result = self.adapter.analyze_image(b"fake_image", "PNG", "context")
        assert result.chart_type == "unknown"
        assert result.confidence == 0.0


class TestGPT4VAdapter:
    def setup_method(self):
        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        self.adapter = GPT4VAdapter()

    def test_init_default_values(self):
        assert "gpt-4o" in self.adapter.model_name.lower()
        assert "openai" in self.adapter.base_url.lower()

    def test_init_custom_values(self):
        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        adapter = GPT4VAdapter(
            model_name="gpt-4-turbo",
            api_key="sk-test-key",
            base_url="https://custom.openai/v1",
        )
        assert adapter.model_name == "gpt-4-turbo"
        assert adapter.api_key == "sk-test-key"

    def test_get_model_info(self):
        info = self.adapter.get_model_info()
        assert info["provider"] == "openai"
        assert "gpt-4" in info["model_name"].lower()
        assert info["initialized"] is False

    @patch("openai.OpenAI")
    def test_initialize_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.models.list.return_value = []

        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        adapter = GPT4VAdapter(api_key="sk-test")
        result = adapter.initialize()

        assert result is True
        assert adapter._initialized is True

    @patch("openai.OpenAI")
    def test_initialize_failure(self, mock_openai_class):
        mock_openai_class.side_effect = Exception("API error")

        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        adapter = GPT4VAdapter(api_key="invalid")
        result = adapter.initialize()

        assert result is False


class TestClaudeVisionAdapter:
    def setup_method(self):
        from multimodal.vision_adapters.claude import ClaudeVisionAdapter
        self.adapter = ClaudeVisionAdapter()

    def test_init_default_values(self):
        assert "claude" in self.adapter.model_name.lower()
        assert "anthropic" in self.adapter.base_url.lower()

    def test_init_custom_values(self):
        from multimodal.vision_adapters.claude import ClaudeVisionAdapter
        adapter = ClaudeVisionAdapter(
            model_name="claude-3-opus-20240229",
            api_key="sk-ant-test",
            base_url="https://custom.anthropic.com",
        )
        assert adapter.model_name == "claude-3-opus-20240229"
        assert adapter.api_key == "sk-ant-test"

    def test_get_model_info(self):
        info = self.adapter.get_model_info()
        assert info["provider"] == "anthropic"
        assert "claude" in info["model_name"].lower()
        assert info["initialized"] is False

    @pytest.mark.skip(reason="Requires anthropic SDK (pip install anthropic)")
    @patch("anthropic.Anthropic")
    def test_initialize_success(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.models.list.return_value = []

        from multimodal.vision_adapters.claude import ClaudeVisionAdapter
        adapter = ClaudeVisionAdapter(api_key="sk-ant-test")
        result = adapter.initialize()

        assert result is True
        assert adapter._initialized is True

    @pytest.mark.skip(reason="Requires anthropic SDK (pip install anthropic)")
    @patch("anthropic.Anthropic")
    def test_initialize_failure(self, mock_anthropic_class):
        mock_anthropic_class.side_effect = Exception("Auth failed")

        from multimodal.vision_adapters.claude import ClaudeVisionAdapter
        adapter = ClaudeVisionAdapter(api_key="invalid")
        result = adapter.initialize()

        assert result is False


class TestGeminiVisionAdapter:
    def setup_method(self):
        from multimodal.vision_adapters.gemini import GeminiVisionAdapter
        self.adapter = GeminiVisionAdapter()

    def test_init_default_values(self):
        assert "gemini" in self.adapter.model_name.lower()

    def test_init_custom_values(self):
        from multimodal.vision_adapters.gemini import GeminiVisionAdapter
        adapter = GeminiVisionAdapter(
            model_name="gemini-1.5-pro",
            api_key="google-api-key",
        )
        assert adapter.model_name == "gemini-1.5-pro"
        assert adapter.api_key == "google-api-key"

    def test_get_model_info(self):
        info = self.adapter.get_model_info()
        assert info["provider"] == "google"
        assert "gemini" in info["model_name"].lower()
        assert info["initialized"] is False

    @pytest.mark.skip(reason="Requires google-generativeai SDK (pip install google-generativeai)")
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_initialize_success(self, mock_model_class, mock_configure):
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.count_tokens.return_value = MagicMock()

        from multimodal.vision_adapters.gemini import GeminiVisionAdapter
        adapter = GeminiVisionAdapter(api_key="google-key")
        result = adapter.initialize()

        assert result is True
        assert adapter._initialized is True

    @pytest.mark.skip(reason="Requires google-generativeai SDK (pip install google-generativeai)")
    @patch("google.generativeai.configure")
    def test_initialize_failure(self, mock_configure):
        mock_configure.side_effect = Exception("Invalid API key")

        from multimodal.vision_adapters.gemini import GeminiVisionAdapter
        adapter = GeminiVisionAdapter(api_key="invalid")
        result = adapter.initialize()

        assert result is False


class TestVisionModelFactory:
    def setup_method(self):
        from multimodal.vision_adapters.factory import VisionModelFactory
        self.factory = VisionModelFactory

    def test_get_supported_providers(self):
        providers = self.factory.get_supported_providers()
        assert "qwen-vl" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers

    def test_get_default_model_qwen(self):
        model = self.factory.get_default_model("qwen-vl")
        assert "qwen" in model.lower()

    def test_get_default_model_openai(self):
        model = self.factory.get_default_model("openai")
        assert "gpt-4" in model.lower()

    def test_get_default_model_anthropic(self):
        model = self.factory.get_default_model("anthropic")
        assert "claude" in model.lower()

    def test_get_default_model_google(self):
        model = self.factory.get_default_model("google")
        assert "gemini" in model.lower()

    def test_get_default_model_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            self.factory.get_default_model("unsupported")

    def test_create_adapter_qwen_vl(self):
        adapter = self.factory.create_adapter(
            provider="qwen-vl",
            model_name="qwen2.5-vl-7b-instruct",
            api_key="not-needed",
            base_url="http://localhost:1234/v1",
        )
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        assert isinstance(adapter, QwenVLAdapter)
        assert adapter.model_name == "qwen2.5-vl-7b-instruct"

    def test_create_adapter_openai(self):
        adapter = self.factory.create_adapter(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )
        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        assert isinstance(adapter, GPT4VAdapter)
        assert adapter.model_name == "gpt-4o"

    def test_create_adapter_anthropic(self):
        adapter = self.factory.create_adapter(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            api_key="sk-ant-test",
            base_url="https://api.anthropic.com",
        )
        from multimodal.vision_adapters.claude import ClaudeVisionAdapter
        assert isinstance(adapter, ClaudeVisionAdapter)
        assert adapter.model_name == "claude-3-5-sonnet-20241022"

    def test_create_adapter_google(self):
        adapter = self.factory.create_adapter(
            provider="google",
            model_name="gemini-2.0-flash",
            api_key="google-key",
        )
        from multimodal.vision_adapters.gemini import GeminiVisionAdapter
        assert isinstance(adapter, GeminiVisionAdapter)
        assert adapter.model_name == "gemini-2.0-flash"

    def test_create_adapter_unsupported_provider(self):
        with pytest.raises(ValueError, match="Unsupported vision provider"):
            self.factory.create_adapter(provider="unsupported")

    def test_create_adapter_from_env(self, monkeypatch):
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        monkeypatch.setenv("VISION_MODEL_NAME", "gpt-4o-mini")
        monkeypatch.setenv("VISION_API_KEY", "sk-env-test")
        monkeypatch.setenv("VISION_BASE_URL", "https://api.openai.com/v1")

        adapter = self.factory.create_adapter()
        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        assert isinstance(adapter, GPT4VAdapter)
        assert adapter.model_name == "gpt-4o-mini"

    def test_create_adapter_case_insensitive(self):
        adapter = self.factory.create_adapter(
            provider="OPENAI",
            model_name="gpt-4o",
            api_key="sk-test",
        )
        from multimodal.vision_adapters.gpt4v import GPT4VAdapter
        assert isinstance(adapter, GPT4VAdapter)

    def test_create_adapter_default_provider(self):
        adapter = self.factory.create_adapter(
            model_name="qwen2.5-vl-7b-instruct",
            api_key="not-needed",
            base_url="http://localhost:1234/v1",
        )
        from multimodal.vision_adapters.qwen_vl import QwenVLAdapter
        assert isinstance(adapter, QwenVLAdapter)


class TestVisionAnalyzerWithAdapters:
    def setup_method(self):
        from multimodal.vision_analyzer import VisionAnalyzer
        self.VisionAnalyzer = VisionAnalyzer

    def test_vision_analyzer_uses_qwen_by_default(self):
        analyzer = self.VisionAnalyzer(
            provider="qwen-vl",
            model_name="qwen2.5-vl-7b-instruct",
            api_key="not-needed",
            base_url="http://localhost:1234/v1",
        )
        assert "qwen" in analyzer.provider.lower()

    def test_vision_analyzer_uses_openai(self):
        analyzer = self.VisionAnalyzer(
            provider="openai",
            model_name="gpt-4o",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
        )
        assert "openai" in analyzer.provider.lower()

    def test_vision_analyzer_get_status(self):
        analyzer = self.VisionAnalyzer(
            provider="qwen-vl",
            model_name="qwen2.5-vl-7b-instruct",
            api_key="not-needed",
            base_url="http://localhost:1234/v1",
        )
        status = analyzer.get_status()
        assert "provider" in status
        assert "model_name" in status
        assert "initialized" in status
