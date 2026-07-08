from functools import lru_cache

from src.config import Settings, get_settings
from src.services.llm.ollama_client import OllamaClient


@lru_cache(maxsize=1)
def make_llm_client(settings: Settings | None = None) -> OllamaClient:
    if settings is None:
        settings = get_settings()
    return OllamaClient(settings)
