import pytest
from unittest.mock import patch, MagicMock


class TestGetSearchTools:
    @patch("tools.search_tool.search_config")
    def test_returns_tavily_when_configured(self, mock_config):
        mock_config.tool = "tavily"
        mock_config.tavily_api_key = "test-key"
        from tools.search_tool import get_search_tools
        tools = get_search_tools()
        tool_names = [t.name for t in tools]
        assert any("Tavily" in name for name in tool_names)
        assert any("Scraper" in name for name in tool_names)

    @patch("tools.search_tool.search_config")
    def test_returns_duckduckgo_by_default(self, mock_config):
        mock_config.tool = "duckduckgo"
        mock_config.tavily_api_key = ""
        from tools.search_tool import get_search_tools
        tools = get_search_tools()
        tool_names = [t.name for t in tools]
        assert any("DuckDuckGo" in name for name in tool_names)
        assert any("Scraper" in name for name in tool_names)

    @patch("tools.search_tool.search_config")
    def test_fallback_to_duckduckgo_without_tavily_key(self, mock_config):
        mock_config.tool = "tavily"
        mock_config.tavily_api_key = ""
        from tools.search_tool import get_search_tools
        tools = get_search_tools()
        tool_names = [t.name for t in tools]
        assert any("DuckDuckGo" in name for name in tool_names)


class TestDuckDuckGoSearch:
    def test_search_returns_formatted_results(self):
        from tools.search_tool import duckduckgo_search
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = [
                {"title": "Test", "link": "http://test.com", "snippet": "Test snippet"}
            ]
            mock_cls.return_value = mock_instance
            result = duckduckgo_search.run("test query")
            assert "Test" in result
            assert "http://test.com" in result

    def test_search_handles_empty_results(self):
        from tools.search_tool import duckduckgo_search
        with patch("langchain_community.tools.DuckDuckGoSearchResults") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = []
            mock_cls.return_value = mock_instance
            result = duckduckgo_search.run("nonexistent query")
            assert isinstance(result, str)


class TestScrapeWebpage:
    def test_scrape_extracts_text(self):
        from tools.search_tool import scrape_webpage
        with patch("tools.search_tool.requests") as mock_requests, \
             patch("tools.search_tool.BeautifulSoup") as mock_bs:
            mock_response = MagicMock()
            mock_response.text = "<html><body><p>Test</p></body></html>"
            mock_response.raise_for_status = MagicMock()
            mock_requests.get.return_value = mock_response

            mock_soup = MagicMock()
            mock_soup.get_text.return_value = "Test content"
            mock_bs.return_value = mock_soup

            result = scrape_webpage.run("http://example.com")
            assert isinstance(result, str)

    def test_scrape_handles_request_error(self):
        from tools.search_tool import scrape_webpage
        with patch("tools.search_tool.requests") as mock_requests:
            mock_requests.get.side_effect = Exception("Connection error")
            result = scrape_webpage.run("http://invalid-url.com")
            assert "失败" in result or "错误" in result
