import json
import logging

import requests
from bs4 import BeautifulSoup
from crewai.tools import tool
from config import search_config
from services.data_cleaner import ContentCleaner, ContentCache

logger = logging.getLogger(__name__)

content_cleaner = ContentCleaner(max_chars=2000, min_word_count=50)
content_cache = ContentCache(max_size=100, max_memory_mb=50)


@tool("Tavily Web Search")
def tavily_search(query: str, max_results: int = 5, search_depth: str = "basic") -> str:
    """使用Tavily搜索引擎搜索网络信息。输入搜索关键词，返回相关搜索结果。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数，默认使用配置值
        search_depth: 搜索深度 (basic/advanced)，默认使用配置值
    """
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        tavily_tool = TavilySearchResults(
            max_results=max_results,
            search_depth=search_depth,
            tavily_api_key=search_config.tavily_api_key,
        )
        results = tavily_tool.invoke({"query": query})

        if isinstance(results, list):
            formatted = []
            for i, r in enumerate(results, 1):
                if isinstance(r, dict):
                    formatted.append(
                        f"[{i}] {r.get('title', 'No Title')}\n"
                        f"URL: {r.get('url', 'N/A')}\n"
                        f"内容: {r.get('content', 'N/A')}"
                    )
                else:
                    formatted.append(f"[{i}] {str(r)}")
            return "\n\n".join(formatted)
        return str(results)

    except ImportError:
        return "错误: tavily-python 未安装，请运行 pip install tavily-python"
    except Exception as e:
        logger.error(f"Tavily搜索失败: {e}")
        return f"搜索失败: {str(e)}"


@tool("DuckDuckGo Web Search")
def duckduckgo_search(query: str, max_results: int = 5) -> str:
    """使用DuckDuckGo搜索引擎搜索网络信息。输入搜索关键词，返回相关搜索结果。无需API密钥。

    Args:
        query: 搜索关键词
        max_results: 最大返回结果数，默认使用配置值
    """
    try:
        from langchain_community.tools import DuckDuckGoSearchResults

        search = DuckDuckGoSearchResults(max_results=max_results)
        results = search.invoke(query)

        if isinstance(results, list):
            formatted = []
            for i, r in enumerate(results, 1):
                if isinstance(r, dict):
                    formatted.append(
                        f"[{i}] {r.get('title', 'No Title')}\n"
                        f"URL: {r.get('link', r.get('url', 'N/A'))}\n"
                        f"内容: {r.get('snippet', r.get('content', 'N/A'))}"
                    )
                else:
                    formatted.append(f"[{i}] {str(r)}")
            return "\n\n".join(formatted)
        return str(results)

    except ImportError:
        return "错误: duckduckgo-search 未安装，请运行 pip install duckduckgo-search"
    except Exception as e:
        logger.error(f"DuckDuckGo搜索失败: {e}")
        return f"搜索失败: {str(e)}"


@tool("Web Content Scraper")
def scrape_webpage(url: str) -> str:
    """抓取指定URL网页的正文内容。输入完整的URL地址，返回网页正文文本。

    Args:
        url: 要抓取的网页URL
    """
    try:
        cached = content_cache.get(url)
        if cached:
            logger.info(f"使用缓存内容: {url}")
            return cached.text

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        raw_text = soup.get_text(separator="\n", strip=True)

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        cleaned = content_cleaner.clean(raw_text, url=url, title=title)

        if not cleaned.text:
            return f"网页内容不符合要求: {url}"

        content_cache.put(url, cleaned)

        return cleaned.text

    except Exception as e:
        logger.error(f"网页抓取失败 [{url}]: {e}")
        return f"网页抓取失败: {str(e)}"


def get_search_tools():
    """根据配置返回搜索工具列表"""
    tools = []
    if search_config.tool == "tavily" and search_config.tavily_api_key:
        tools.append(tavily_search)
    else:
        tools.append(duckduckgo_search)
    tools.append(scrape_webpage)
    return tools
