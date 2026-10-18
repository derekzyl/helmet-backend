"""
Enhanced caching service with automatic invalidation and performance monitoring.
"""

import hashlib
import inspect
from functools import wraps
from typing import Any, Callable, Dict, Optional

from app.utils.cache.redis_cache import cache_manager
from app.utils.logger.log import logs


class EnhancedCacheService:
    def __init__(self):
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
        self.cache_patterns = {
            "user_data": "user_data:{user_id}:*",
            "resource_data": "resource:{resource_id}:*",
        }

    async def get_with_fallback(
        self,
        cache_key: str,
        fallback_func: Callable,
        cache_ttl: int = 300,
        *args,
        **kwargs,
    ) -> Any:
        try:
            cached_data = await cache_manager.get(cache_key)
            if cached_data is not None:
                self.cache_stats["hits"] += 1
                return cached_data

            self.cache_stats["misses"] += 1
            data = await fallback_func(*args, **kwargs)
            if data is not None:
                await cache_manager.set(cache_key, data, expire=cache_ttl)
                self.cache_stats["sets"] += 1
            return data
        except Exception as e:
            logs.error(f"Error in get_with_fallback for key {cache_key}: {str(e)}")
            return await fallback_func(*args, **kwargs)

    async def invalidate_pattern(self, pattern: str) -> int:
        try:
            deleted = await cache_manager.delete_pattern(pattern)
            self.cache_stats["deletes"] += deleted
            return deleted
        except Exception as e:
            logs.error(f"Error invalidating cache pattern {pattern}: {str(e)}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        hit_rate = 0
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total > 0:
            hit_rate = self.cache_stats["hits"] / total
        return {
            **self.cache_stats,
            "hit_rate": round(hit_rate * 100, 2),
        }


enhanced_cache = EnhancedCacheService()


def cache_result(ttl: int = 300, key_prefix: str = "cache"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_src = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = f"{key_prefix}:{hashlib.md5(key_src.encode()).hexdigest()}"
            return await enhanced_cache.get_with_fallback(
                cache_key, lambda: func(*args, **kwargs), cache_ttl=ttl
            )

        return wrapper

    return decorator


def cache_invalidation_hook(resource_id_param: str = "id"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            resource_id = kwargs.get(resource_id_param)
            if resource_id is None:
                try:
                    bound = inspect.signature(func).bind_partial(*args, **kwargs)
                    resource_id = bound.arguments.get(resource_id_param)
                except Exception:
                    resource_id = None
            if resource_id:
                await enhanced_cache.invalidate_pattern(f"*{resource_id}*")
            return result

        return wrapper

    return decorator
