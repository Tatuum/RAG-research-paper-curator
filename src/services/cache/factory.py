from functools import lru_cache

from src.config import Settings, get_settings
from src.services.cache.redis_client import RedisClient


@lru_cache(maxsize=1)
def make_redis_client(settings: Settings | None = None) -> RedisClient:
    if settings is None:
        settings = get_settings()
    return RedisClient(settings=settings)
