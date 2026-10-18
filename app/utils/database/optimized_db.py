"""Generic optimized DB helpers for the starter template."""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.cache.redis_cache import cache_manager
from app.utils.logger.log import logs


class OptimizedDB:
    def __init__(self) -> None:
        self.cache = cache_manager

    async def get_cached(
        self, cache_key: str, fallback=None, expire: int = 300
    ) -> Any:
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        if fallback is None:
            return None
        data = await fallback()
        if data is not None:
            await self.cache.set(cache_key, data, expire=expire)
        return data

    async def clear_cache_pattern(self, pattern: str) -> int:
        try:
            return await self.cache.delete_pattern(pattern)
        except Exception as e:
            logs.error(f"Failed to clear cache pattern {pattern}: {e}")
            return 0


optimized_db = OptimizedDB()


async def get_user_summary(
    db: AsyncSession, user_id: str, *, use_cache: bool = True
) -> Optional[dict]:
    cache_key = f"user_summary:{user_id}"

    async def fetch():
        from sqlalchemy import select

        from app.core.users.models.model_user import UserModel

        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        data = user.to_dict()
        data.pop("password", None)
        return data

    if use_cache:
        return await optimized_db.get_cached(cache_key, fallback=fetch, expire=300)
    return await fetch()
