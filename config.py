import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


class LLMConfig:
    api_key: str = os.getenv("LLM_API_KEY", "")
    base_url: str = os.getenv("LLM_BASE_URL", "")
    model: str = os.getenv("LLM_MODEL", "")
    provider: str = os.getenv("LLM_PROVIDER", "")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    timeout: int = int(os.getenv("LLM_TIMEOUT", "300"))
    request_timeout: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "120"))

    @classmethod
    def get_crewai_llm(cls):
        from crewai import LLM

        if not cls.provider:
            if cls.base_url and "localhost" in cls.base_url:
                cls.provider = "openai"
            else:
                cls.provider = "deepseek"

        if not cls.model:
            cls.model = "deepseek-chat"

        if cls.provider == "openai":
            model_name = f"openai/{cls.model}"
        elif cls.provider == "deepseek":
            model_name = f"deepseek/{cls.model}"
        else:
            model_name = f"{cls.provider}/{cls.model}"

        if not cls.base_url:
            if cls.provider == "deepseek":
                cls.base_url = "https://api.deepseek.com/v1"
            else:
                cls.base_url = "http://localhost:1234/v1"

        llm_kwargs = {
            "model": model_name,
            "base_url": cls.base_url,
            "api_key": cls.api_key,
            "temperature": cls.temperature,
            "max_tokens": cls.max_tokens,
            "timeout": cls.timeout,
            "request_timeout": cls.request_timeout,
        }

        if cls.provider == "openai":
            llm_kwargs["api_version"] = "2024-01-01"

        return LLM(**llm_kwargs)

    @classmethod
    def get_langchain_llm(cls):
        from langchain_openai import ChatOpenAI

        if not cls.model:
            cls.model = "deepseek-chat"

        if not cls.base_url:
            if cls.provider == "deepseek":
                cls.base_url = "https://api.deepseek.com/v1"
            else:
                cls.base_url = "http://localhost:1234/v1"

        return ChatOpenAI(
            base_url=cls.base_url,
            api_key=cls.api_key,
            model_name=cls.model,
            temperature=cls.temperature,
            max_tokens=cls.max_tokens,
            request_timeout=cls.request_timeout,
        )


class SearchConfig:
    tool: str = os.getenv("SEARCH_TOOL", "duckduckgo")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    max_results: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
    search_depth: str = os.getenv("SEARCH_DEPTH", "basic")


class ContextConfig:
    max_tokens: int = int(os.getenv("CONTEXT_MAX_TOKENS", "8000"))
    warning_threshold: float = float(os.getenv("CONTEXT_WARNING_THRESHOLD", "0.75"))
    critical_threshold: float = float(os.getenv("CONTEXT_CRITICAL_THRESHOLD", "0.9"))


class AppConfig:
    port: int = int(os.getenv("APP_PORT", "8000"))
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'tasks.db'}")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


llm_config = LLMConfig()
search_config = SearchConfig
context_config = ContextConfig()
app_config = AppConfig
