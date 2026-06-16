import logging
from typing import cast

from redis import Redis

from src.config import Settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, settings: Settings):
        self._client = Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
            decode_responses=settings.redis.decode_responses,
            retry_on_timeout=True,
        )
        self._ttl_hours = settings.redis.ttl_hours

    def get(self, key: str) -> str | None:
        return cast(str | None, self._client.get(key))

    def set(self, key: str, value: str, ttl_hours: int | None = None) -> None:
        ttl = (ttl_hours or self._ttl_hours) * 3600
        self._client.set(key, value, ex=ttl)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def health_check(self) -> bool:
        try:
            self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
