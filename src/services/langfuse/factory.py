from functools import lru_cache

from src.config import Settings, get_settings
from src.services.langfuse.client import LangfuseTracer


@lru_cache(maxsize=1)
def make_langfuse_tracer(settings: Settings | None = None) -> LangfuseTracer:
    if settings is None:
        settings = get_settings()
    return LangfuseTracer(settings)
