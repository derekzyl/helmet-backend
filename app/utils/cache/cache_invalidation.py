"""Generic cache invalidation helpers."""

from app.utils.cache.redis_cache import invalidate_cache_pattern


async def invalidate_user_cache(user_id: str) -> None:
    await invalidate_cache_pattern(f"user:{user_id}*")
    await invalidate_cache_pattern(f"auth_user:*")
    await invalidate_cache_pattern(f"user_summary:{user_id}*")


async def invalidate_resource_cache(resource: str, resource_id: str) -> None:
    await invalidate_cache_pattern(f"{resource}:{resource_id}*")
