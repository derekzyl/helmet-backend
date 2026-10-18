"""Generic response helpers with optional cache."""

from typing import Any, Callable, Optional

from app.utils.cache.redis_cache import cache_manager
from app.utils.logger.log import logs


class OptimizedResponseService:
    def __init__(self) -> None:
        self.cache = cache_manager
        self.response_cache_ttl = {
            "user_data": 300,
            "dashboard_stats": 120,
        }

    async def get_or_set(
        self,
        cache_key: str,
        fallback_func: Callable,
        cache_ttl: int = 300,
    ) -> Any:
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        data = await fallback_func()
        if data is not None:
            await self.cache.set(cache_key, data, expire=cache_ttl)
        return data

    async def invalidate(self, pattern: str) -> None:
        try:
            await self.cache.delete_pattern(pattern)
        except Exception as e:
            logs.error(f"Failed to invalidate cache {pattern}: {e}")


optimized_response = OptimizedResponseService()
