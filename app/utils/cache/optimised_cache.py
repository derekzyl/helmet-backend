"""
Improved Redis Cache Manager with Robust Serialization

Key improvements:
1. Uses CacheSerializer to handle mixed data types
2. Better error handling for cache operations
3. Performance monitoring
4. Automatic retry logic
5. Connection health checks
"""

import asyncio
import hashlib
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from redis.asyncio import Redis

try:
    from redis.asyncio import Redis as RedisClient
    from redis.exceptions import ConnectionError, RedisError, TimeoutError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisClient = None
    ConnectionError = Exception
    TimeoutError = Exception
    RedisError = Exception

from app.utils.cache.cache_serializer import cache_serializer
from app.utils.logger.log import logs


class CacheManager:
    """
    Improved async Redis cache manager with robust serialization.
    """

    def __init__(self):
        self.redis: Optional["Redis"] = None
        self.enabled = False
        self._connection_retries = 0
        self._max_retries = 3

        # Performance stats
        self.stats = {"hits": 0, "misses": 0, "errors": 0, "sets": 0, "deletes": 0}

    async def init(
        self,
        redis_url: str,
        enabled: bool = True,
        max_retries: int = 3,
        retry_delay: int = 2,
    ):
        """
        Initialize Redis connection with retry logic

        Args:
            redis_url: Redis connection URL (e.g., redis://user:pass@host:port or host:port)
            enabled: Whether caching is enabled
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.enabled = enabled and REDIS_AVAILABLE
        self._max_retries = max_retries

        if not REDIS_AVAILABLE:
            logs.warning("⚠️ Redis library not installed. Caching will be disabled.")
            return

        if not enabled:
            logs.info("ℹ️ Caching is disabled by configuration")
            return

        # Parse Redis URL
        host, port, username, password, db, ssl = self._parse_redis_url(redis_url)

        # Retry connection logic
        for attempt in range(max_retries):
            try:
                logs.info(
                    f"🔌 Connecting to Redis at {host}:{port} (attempt {attempt + 1}/{max_retries})"
                )

                assert RedisClient is not None

                # Create Redis client with optimized settings
                self.redis = RedisClient(
                    host=host,
                    port=port,
                    db=db,
                    username=username if username else None,
                    password=password if password else None,
                    decode_responses=False,  # We handle encoding ourselves
                    encoding="utf-8",
                    socket_connect_timeout=10,
                    socket_timeout=10,
                    socket_keepalive=True,
                    socket_keepalive_options={
                        1: 60,  # TCP_KEEPIDLE
                        2: 10,  # TCP_KEEPINTVL
                        3: 3,  # TCP_KEEPCNT
                    },
                    max_connections=20,  # Reasonable pool size
                    health_check_interval=30,
                    ssl=ssl,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError, TimeoutError],
                )

                # Test connection
                await asyncio.wait_for(self.redis.ping(), timeout=10)

                logs.info("✅ Redis cache initialized successfully")
                self._connection_retries = 0
                return

            except asyncio.TimeoutError:
                logs.error(
                    f"⏱️ Redis connection timeout on attempt {attempt + 1}/{max_retries}"
                )
                await self._cleanup_redis_connection()

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue

            except ConnectionError as e:
                logs.error(
                    f"❌ Redis connection error on attempt {attempt + 1}/{max_retries}: {e}"
                )
                await self._cleanup_redis_connection()

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue

            except Exception as e:
                logs.error(
                    f"❌ Failed to initialize Redis cache on attempt {attempt + 1}/{max_retries}: {e}"
                )
                await self._cleanup_redis_connection()

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue

        # All retries failed
        logs.warning("⚠️ All Redis connection attempts failed. Running without cache.")
        self.enabled = False
        self.redis = None

    async def _cleanup_redis_connection(self):
        """Clean up Redis connection"""
        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass
            self.redis = None

    def _parse_redis_url(self, redis_url: str) -> tuple:
        """Parse Redis URL to extract components"""
        host = "localhost"
        port = 6379
        username = None
        password = None
        db = 0
        ssl = False

        try:
            if redis_url.startswith(("redis://", "rediss://")):
                ssl = redis_url.startswith("rediss://")
                url_without_scheme = redis_url.split("://", 1)[1]

                # Extract auth if present
                if "@" in url_without_scheme:
                    auth_part, host_part = url_without_scheme.split("@", 1)
                    if ":" in auth_part:
                        username, password = auth_part.split(":", 1)
                    else:
                        password = auth_part
                else:
                    host_part = url_without_scheme

                # Extract host, port, and db
                if "/" in host_part:
                    host_port, db_str = host_part.split("/", 1)
                    db = int(db_str) if db_str else 0
                else:
                    host_port = host_part

                if ":" in host_port:
                    host, port_str = host_port.rsplit(":", 1)
                    port = int(port_str)
                else:
                    host = host_port
            else:
                # Simple format: host:port
                if ":" in redis_url:
                    host, port_str = redis_url.rsplit(":", 1)
                    port = int(port_str)
                else:
                    host = redis_url
        except Exception as e:
            logs.error(f"Failed to parse Redis URL: {e}")

        return host, port, username, password, db, ssl

    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is alive"""
        if not self.enabled or not self.redis:
            return False

        try:
            await asyncio.wait_for(self.redis.ping(), timeout=2)
            return True
        except Exception as e:
            logs.warning(f"⚠️ Redis connection lost: {e}")
            self.enabled = False
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with robust deserialization

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled or not self.redis:
            return None

        try:
            # Check connection
            if not await self._ensure_connection():
                return None

            # Get from Redis
            value = await asyncio.wait_for(self.redis.get(key), timeout=5)

            if value is None:
                self.stats["misses"] += 1
                return None

            # Deserialize using robust serializer
            deserialized = cache_serializer.deserialize(value.decode("utf-8"))
            self.stats["hits"] += 1

            return deserialized

        except asyncio.TimeoutError:
            logs.warning(f"⏱️ Cache get timeout for key {key}")
            self.stats["errors"] += 1
            return None
        except Exception as e:
            logs.error(f"❌ Cache get error for key {key}: {e}")
            self.stats["errors"] += 1
            return None

    async def set(self, key: str, value: Any, expire: int = 300) -> bool:
        """
        Set value in cache with robust serialization

        Args:
            key: Cache key
            value: Value to cache (can be model, dict, list, or mixed format)
            expire: Expiration time in seconds (default: 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis:
            return False

        try:
            # Check connection
            if not await self._ensure_connection():
                return False

            # Serialize using robust serializer
            serialized = cache_serializer.serialize(value)

            # Set in Redis
            await asyncio.wait_for(
                self.redis.set(key, serialized.encode("utf-8"), ex=expire), timeout=5
            )

            self.stats["sets"] += 1
            return True

        except asyncio.TimeoutError:
            logs.warning(f"⏱️ Cache set timeout for key {key}")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logs.error(f"❌ Cache set error for key {key}: {e}")
            self.stats["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self.redis:
            return False

        try:
            await asyncio.wait_for(self.redis.delete(key), timeout=5)
            self.stats["deletes"] += 1
            return True
        except asyncio.TimeoutError:
            logs.warning(f"⏱️ Cache delete timeout for key {key}")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logs.error(f"❌ Cache delete error for key {key}: {e}")
            self.stats["errors"] += 1
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis:
            return 0

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                deleted = await asyncio.wait_for(self.redis.delete(*keys), timeout=10)
                self.stats["deletes"] += deleted
                return deleted
            return 0

        except asyncio.TimeoutError:
            logs.warning(f"⏱️ Cache delete pattern timeout for pattern {pattern}")
            self.stats["errors"] += 1
            return 0
        except Exception as e:
            logs.error(f"❌ Cache delete pattern error for pattern {pattern}: {e}")
            self.stats["errors"] += 1
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled or not self.redis:
            return False

        try:
            result = await asyncio.wait_for(self.redis.exists(key), timeout=5)
            return result > 0
        except asyncio.TimeoutError:
            logs.warning(f"⏱️ Cache exists timeout for key {key}")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logs.error(f"❌ Cache exists error for key {key}: {e}")
            self.stats["errors"] += 1
            return False

    async def clear_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        if not self.enabled or not self.redis:
            return False

        try:
            await asyncio.wait_for(self.redis.flushdb(), timeout=10)
            logs.info("🗑️ Cache cleared successfully")
            return True
        except asyncio.TimeoutError:
            logs.warning("⏱️ Cache clear timeout")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logs.error(f"❌ Cache clear error: {e}")
            self.stats["errors"] += 1
            return False

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_ops = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_ops * 100) if total_ops > 0 else 0

        return {
            **self.stats,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_operations": total_ops,
            "enabled": self.enabled,
        }

    def reset_stats(self):
        """Reset cache statistics"""
        self.stats = {"hits": 0, "misses": 0, "errors": 0, "sets": 0, "deletes": 0}

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            await self.redis.connection_pool.disconnect()
            logs.info("🔌 Redis cache connection closed")


# Global cache manager instance
cache_manager = CacheManager()


# Decorator for caching with improved serialization
def cached(
    key_prefix: str, expire: int = 300, key_builder: Optional[Callable] = None
):
    """
    Improved caching decorator with robust serialization

    Args:
        key_prefix: Prefix for cache key
        expire: Expiration time in seconds (default: 5 minutes)
        key_builder: Optional custom function to build cache key from args
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                try:
                    cache_key = key_builder(*args, **kwargs)
                except Exception as e:
                    logs.error(f"❌ Error building cache key: {e}")
                    key_parts = f"{key_prefix}:{args}:{sorted(kwargs.items())}"
                    cache_key = (
                        f"{key_prefix}:{hashlib.md5(key_parts.encode()).hexdigest()}"
                    )
            else:
                key_parts = f"{key_prefix}:{args}:{sorted(kwargs.items())}"
                cache_key = (
                    f"{key_prefix}:{hashlib.md5(key_parts.encode()).hexdigest()}"
                )

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logs.debug(f"💾 Cache HIT for key: {cache_key}")
                return cached_value

            logs.debug(f"🔍 Cache MISS for key: {cache_key}")

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache (non-blocking)
            asyncio.create_task(cache_manager.set(cache_key, result, expire))

            return result

        return wrapper

    return decorator


# Convenience function for invalidating cache patterns
async def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache keys matching pattern

    Example:
        await invalidate_cache_pattern("user:*")
        await invalidate_cache_pattern("analytics:example:*")
    """
    return await cache_manager.delete_pattern(pattern)
