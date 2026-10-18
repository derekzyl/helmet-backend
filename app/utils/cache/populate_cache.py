"""
Specialized caching system for expensive populate operations.
This module provides intelligent caching for relationship data that is expensive to fetch.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as sa_select
from sqlalchemy.orm import DeclarativeBase

from app.utils.cache.redis_cache import cache_manager
from app.utils.logger import log


class PopulateCache:
    """Intelligent caching for populate operations"""
    
    def __init__(self, model_class: Type[DeclarativeBase], db: AsyncSession):
        self.model_class = model_class
        self.db = db
        self.cache_ttl = 300  # 5 minutes default
        self.relationship_cache = {}
    
    def _generate_cache_key(self, base_query: Dict[str, Any], populate_fields: List[Any]) -> str:
        """Generate a unique cache key for the query and populate combination"""
        # Create a deterministic key from query parameters and populate fields
        key_data = {
            "model": self.model_class.__name__,
            "query": base_query,
            "populate": populate_fields
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"populate_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def get_cached_populate_data(self, cache_key: str) -> Optional[List[Dict]]:
        """Retrieve cached populate data"""
        try:
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                log.logs.debug(f"💾 [POPULATE_CACHE] Cache hit for {cache_key[:20]}...")
                return json.loads(cached_data)
        except Exception as e:
            log.logs.debug(f"💾 [POPULATE_CACHE] Cache retrieval error: {e}")
        return None
    
    async def set_cached_populate_data(self, cache_key: str, data: List[Dict]) -> None:
        """Store populate data in cache"""
        try:
            await cache_manager.set(cache_key, json.dumps(data), expire=self.cache_ttl)
            log.logs.debug(f"💾 [POPULATE_CACHE] Cached data for {cache_key[:20]}...")
        except Exception as e:
            log.logs.debug(f"💾 [POPULATE_CACHE] Cache storage error: {e}")
    
    async def get_populate_data_with_cache(
        self, 
        base_query: Dict[str, Any], 
        populate_fields: List[Any],
        filter_params: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        Get populate data with intelligent caching.
        
        This method:
        1. Checks cache for existing data
        2. If cache miss, fetches from database
        3. Caches the result for future use
        4. Returns the data
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(base_query, populate_fields)
        
        # Try to get from cache first
        cached_data = await self.get_cached_populate_data(cache_key)
        if cached_data is not None:
            cache_time = (time.time() - start_time) * 1000
            log.logs.info(f"✅ [POPULATE_CACHE] Cache hit: {cache_time:.2f}ms")
            return cached_data
        
        # Cache miss - fetch from database
        log.logs.info("🔄 [POPULATE_CACHE] Cache miss, fetching from database...")
        
        # Build the query
        query = sa_select(self.model_class)
        
        # Apply filters
        if filter_params:
            for key, value in filter_params.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        
        # Execute query
        result = await self.db.execute(query)
        results = result.scalars().all()
        
        # Convert to dictionaries with relationships
        data = []
        for result_obj in results:
            if hasattr(result_obj, 'to_dict'):
                data.append(result_obj.to_dict())  # pyright: ignore[reportAttributeAccessIssue]
            else:
                # Fallback conversion
                data.append({
                    column.name: getattr(result_obj, column.name)
                    for column in result_obj.__table__.columns
                })
        
        # Cache the result
        await self.set_cached_populate_data(cache_key, data)
        
        total_time = (time.time() - start_time) * 1000
        log.logs.info(f"✅ [POPULATE_CACHE] Database fetch completed: {total_time:.2f}ms")
        
        return data
    
    def invalidate_cache_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching a pattern"""
        try:
            # This would need to be implemented based on your cache backend
            # For Redis, you could use SCAN with pattern matching
            log.logs.info(f"🗑️ [POPULATE_CACHE] Invalidating cache pattern: {pattern}")
        except Exception as e:
            log.logs.warning(f"🗑️ [POPULATE_CACHE] Cache invalidation error: {e}")
    
    def set_cache_ttl(self, ttl: int) -> None:
        """Set cache TTL for populate operations"""
        self.cache_ttl = ttl
        log.logs.info(f"⏰ [POPULATE_CACHE] Cache TTL set to {ttl} seconds")


class PopulateCacheManager:
    """Manager for multiple populate caches"""
    
    def __init__(self):
        self.caches = {}
    
    def get_cache(self, model_class: Type[DeclarativeBase], db: AsyncSession) -> PopulateCache:
        """Get or create a populate cache for a model"""
        cache_key = f"{model_class.__name__}"
        
        if cache_key not in self.caches:
            self.caches[cache_key] = PopulateCache(model_class, db)
            log.logs.debug(f"🆕 [POPULATE_CACHE] Created cache for {model_class.__name__}")
        
        return self.caches[cache_key]
    
    def clear_all_caches(self) -> None:
        """Clear all populate caches"""
        self.caches.clear()
        log.logs.info("🗑️ [POPULATE_CACHE] All caches cleared")


# Global cache manager instance
populate_cache_manager = PopulateCacheManager()
