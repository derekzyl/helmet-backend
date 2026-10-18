"""
Optimized CRUD Service for high-performance database operations.
This module provides enhanced CRUD operations with caching, connection pooling,
and query optimization techniques while maintaining the same return format.
"""

import hashlib
import json
import time
from functools import lru_cache, wraps
from typing import Any, Dict, List, Optional, Type, TypedDict

from fastapi import HTTPException, status
from sqlalchemy import delete, func, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as sa_select
from sqlalchemy.orm import DeclarativeBase, joinedload, selectinload
from sqlalchemy.sql import insert

from app.utils.cache.redis_cache import cache_manager
from app.utils.crud.optimized_queries import OptimizedQueries
from app.utils.crud.types_crud import ResponseMessage, response_message
from app.utils.logger import log


class PopulateField(TypedDict, total=False):
    path: str
    fields: Optional[List[str]]
    second_layer: Optional[List["PopulateField"]]


def cache_result(ttl: int = 300, key_prefix: str = "crud"):
    """Decorator to cache CRUD operation results."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{self.model.__name__}:{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"

            # Try to get from cache
            try:
                cached_result = await cache_manager.get(cache_key)
                if cached_result:
                    log.logs.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return json.loads(cached_result)
            except Exception as e:
                log.logs.warning(f"Cache retrieval error: {e}")

            # Execute function
            result = await func(self, *args, **kwargs)

            # Cache result - ensure it's JSON serializable
            try:
                serializable_result = result
                
                # Handle response_message format
                if isinstance(result, dict) and 'data' in result:
                    if hasattr(result['data'], '__iter__') and not isinstance(result['data'], (str, bytes)):
                        # Convert list of SQLAlchemy objects to list of dicts
                        serializable_data = []
                        for item in result['data']:
                            if hasattr(item, 'to_dict') and not isinstance(item, (dict, str, bytes, int, float, bool)):
                                serializable_data.append(item.to_dict())
                            elif isinstance(item, dict):
                                serializable_data.append(item)
                            else:
                                # Skip non-serializable items
                                continue
                        serializable_result = {**result, 'data': serializable_data}
                    elif hasattr(result['data'], 'to_dict') and not isinstance(result['data'], (dict, str, bytes, int, float, bool)):
                        # Single SQLAlchemy object
                        serializable_result = {**result, 'data': result['data'].to_dict()}
                elif hasattr(result, 'to_dict') and not isinstance(result, (dict, str, bytes, int, float, bool)):
                    # Direct SQLAlchemy object
                    serializable_result = result.to_dict()
                
                await cache_manager.set(cache_key, json.dumps(serializable_result), ttl)
                log.logs.debug(f"Cached result for {func.__name__}: {cache_key}")
            except Exception as e:
                log.logs.warning(f"Cache storage error: {e}")

            return result

        return wrapper

    return decorator


class OptimizedCrudService:
    """
    High-performance CRUD service with caching and optimization.
    Maintains the same interface as the original CrudService.
    """

    def __init__(
        self,
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None,
    ):
        self.model = model
        self.db = db
        self.current_user_id = current_user_id
        self._relationship_cache = {}
        self._field_cache = {}

    @lru_cache(maxsize=1000)
    def _get_model_fields(self) -> tuple:
        """Cache model field names."""
        return tuple(self.model.__table__.columns.keys())

    @lru_cache(maxsize=100)
    def _get_model_relationships(self) -> tuple:
        """Cache model relationship names."""
        relationships = []
        for attr_name in dir(self.model):
            if not attr_name.startswith("_"):
                attr = getattr(self.model, attr_name)
                if hasattr(attr, "property") and hasattr(attr.property, "mapper"):
                    relationships.append(attr_name)
        return tuple(relationships)

    def set_current_user(self, user_id: str):
        """Set the current user ID for audit fields"""
        self.current_user_id = user_id

    def _add_audit_fields(
        self, data: Dict[str, Any], is_create: bool = True
    ) -> Dict[str, Any]:
        """Add audit fields to data if model supports them"""
        if not self.current_user_id:
            return data

        audit_data = data.copy()
        model_fields = self._get_model_fields()

        # Check if model has audit fields
        if "created_by_id" in model_fields and is_create:
            audit_data["created_by_id"] = self.current_user_id

        if "updated_by_id" in model_fields:
            audit_data["updated_by_id"] = self.current_user_id

        return audit_data

    def _build_populate_options(self, populate: List[PopulateField]) -> List[Any]:
        """
        Optimized populate options builder with performance logging.
        """
        populate_start = time.time()
        log.logs.info(f"📊 [PERF] Building populate options for {len(populate)} relationships")
        
        options = []
        relationships = self._get_model_relationships()
        cache_hits = 0
        cache_misses = 0

        for i, pop_config in enumerate(populate):
            path = pop_config.get("path")
            second_layer = pop_config.get("second_layer", [])

            if not path or path not in relationships:
                log.logs.warning(f"⚠️ [PERF] Invalid populate path: {path}")
                continue

            # Use cached relationship info
            cache_key = f"{self.model.__name__}:{path}"
            if cache_key in self._relationship_cache:
                load_option = self._relationship_cache[cache_key]
                cache_hits += 1
                log.logs.debug(f"💾 [PERF] Cache hit for {path}")
            else:
                relationship_build_start = time.time()
                relationship_attr = getattr(self.model, path)

                # Use selectinload for collections, joinedload for single relationships
                if hasattr(relationship_attr.property, "collection_class"):
                    load_option = selectinload(relationship_attr)
                    load_type = "selectinload"
                else:
                    load_option = joinedload(relationship_attr)
                    load_type = "joinedload"

                # Cache the load option
                self._relationship_cache[cache_key] = load_option
                cache_misses += 1
                relationship_build_time = (time.time() - relationship_build_start) * 1000
                log.logs.debug(f"🔧 [PERF] Built {load_type} for {path}: {relationship_build_time:.2f}ms")

            # Handle second layer population (nested relationships)
            if second_layer:
                nested_start = time.time()
                log.logs.debug(f"🔄 [PERF] Processing {len(second_layer)} nested relationships for {path}")
                for nested_config in second_layer:
                    nested_path = nested_config.get("path")
                    if nested_path:
                        # Chain the loading options
                        relationship_attr = getattr(self.model, path)
                        nested_attr = getattr(
                            relationship_attr.property.mapper.class_, nested_path
                        )

                        if hasattr(nested_attr.property, "collection_class"):
                            load_option = load_option.selectinload(nested_attr)
                            nested_type = "selectinload"
                        else:
                            load_option = load_option.joinedload(nested_attr)
                            nested_type = "joinedload"
                        
                        log.logs.debug(f"🔗 [PERF] Chained {nested_type} for {path}.{nested_path}")
                
                nested_time = (time.time() - nested_start) * 1000
                log.logs.debug(f"⏱️ [PERF] Nested relationships for {path}: {nested_time:.2f}ms")

            options.append(load_option)

        total_populate_time = (time.time() - populate_start) * 1000
        log.logs.info("✅ [PERF] Populate options built:")
        log.logs.info(f"   📊 Total options: {len(options)}")
        log.logs.info(f"   💾 Cache hits: {cache_hits}")
        log.logs.info(f"   🔧 Cache misses: {cache_misses}")
        log.logs.info(f"   ⏱️ Total time: {total_populate_time:.2f}ms")

        return options

    # @cache_result(ttl=300, key_prefix="get_many")  # Caching disabled
    async def get_many(
        self,
        query: Dict[str, Any],
        filter: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
    ) -> ResponseMessage:
        """
        Optimized get_many with comprehensive performance logging.
        """
        start_time = time.time()
        log.logs.info(f"🚀 [PERF] get_many started for {self.model.__name__}")
        
        try:
            # Build optimized query
            query_build_start = time.time()
            query_model = sa_select(self.model)
            log.logs.info(f"⏱️ [PERF] Query model creation: {(time.time() - query_build_start)*1000:.2f}ms")

            # Apply populate options if provided
            populate_start = time.time()
            if populate:
                log.logs.info(f"📊 [PERF] Building populate options for {len(populate)} relationships")
                populate_options = self._build_populate_options(populate)
                for option in populate_options:
                    query_model = query_model.options(option)
                log.logs.info(f"⏱️ [PERF] Populate options built: {(time.time() - populate_start)*1000:.2f}ms")
            else:
                log.logs.info(f"⏱️ [PERF] No populate options: {(time.time() - populate_start)*1000:.2f}ms")

            # Apply additional filters
            filter_start = time.time()
            if filter:
                log.logs.info(f"🔍 [PERF] Applying {len(filter)} additional filters")
                for key, value in filter.items():
                    if key in self._get_model_fields():
                        query_model = query_model.where(
                            getattr(self.model, key) == value
                        )
                log.logs.info(f"⏱️ [PERF] Additional filters applied: {(time.time() - filter_start)*1000:.2f}ms")
            else:
                log.logs.info(f"⏱️ [PERF] No additional filters: {(time.time() - filter_start)*1000:.2f}ms")

            # Use optimized queries but execute directly like old service
            query_processing_start = time.time()
            optimized_query = OptimizedQueries(query_model, query, self.model)
            optimized_query.filter().limit_fields().paginate().sort()
            log.logs.info(f"⏱️ [PERF] Query processing (filter/paginate/sort): {(time.time() - query_processing_start)*1000:.2f}ms")

            # Execute directly like old service to avoid any caching issues
            db_execution_start = time.time()
            
            # Log the actual SQL query being executed
            try:
                compiled_query = str(optimized_query.model.compile(compile_kwargs={"literal_binds": True}))
                log.logs.info(f"🔍 [PERF] SQL Query: {compiled_query[:500]}{'...' if len(compiled_query) > 500 else ''}")
            except Exception as e:
                log.logs.debug(f"🔍 [PERF] Could not compile SQL query: {e}")
            
            result = await self.db.execute(optimized_query.model)
            results = result.scalars().all()
            db_execution_time = (time.time() - db_execution_start) * 1000
            
            # Log database connection pool status
            try:
                # Get engine from session's bind
                engine = self.db.get_bind()
                if hasattr(engine, 'pool'):
                    pool = engine.pool  # pyright: ignore[reportAttributeAccessIssue]
                    pool_size = getattr(pool, 'size', lambda: 0)()
                    checked_in = getattr(pool, 'checkedin', lambda: 0)()
                    checked_out = getattr(pool, 'checkedout', lambda: 0)()
                    overflow = getattr(pool, 'overflow', lambda: 0)()
                    log.logs.info(f"🔗 [PERF] DB Pool - Size: {pool_size}, CheckedIn: {checked_in}, CheckedOut: {checked_out}, Overflow: {overflow}")
                else:
                    log.logs.debug("🔗 [PERF] Pool information not available")
            except Exception as e:
                log.logs.debug(f"🔗 [PERF] Could not get pool status: {e}")
            
            log.logs.info(f"⏱️ [PERF] Database execution: {db_execution_time:.2f}ms")
            log.logs.info(f"📊 [PERF] Retrieved {len(results)} records from database")

            if not results:
                total_time = (time.time() - start_time) * 1000
                log.logs.info(f"✅ [PERF] get_many completed (no data): {total_time:.2f}ms")
                return response_message(
                    data=[],
                    error=None,
                    message="No data found",
                    success_status=True,
                    doc_length=0,
                )

            # Apply field filtering for populated relationships
            post_processing_start = time.time()
            if populate:
                log.logs.info(f"🔄 [PERF] Starting post-processing for {len(populate)} populate fields")
                
                # Field filtering
                field_filter_start = time.time()
                results = self._filter_populated_fields(results, populate)
                field_filter_time = (time.time() - field_filter_start) * 1000
                log.logs.info(f"⏱️ [PERF] Field filtering: {field_filter_time:.2f}ms")

                # Convert to dictionaries with relationships
                conversion_start = time.time()
                converted_results = []
                for i, result in enumerate(results):
                    result_start = time.time()
                    converted_result = self._convert_to_dict_with_relationships(
                        result, populate
                    )
                    converted_results.append(converted_result)
                    if i % 10 == 0:  # Log every 10th conversion
                        log.logs.debug(f"⏱️ [PERF] Converted item {i}: {(time.time() - result_start)*1000:.2f}ms")
                
                conversion_time = (time.time() - conversion_start) * 1000
                log.logs.info(f"⏱️ [PERF] Dictionary conversion: {conversion_time:.2f}ms")
                log.logs.info(f"📊 [PERF] Converted {len(converted_results)} items to dictionaries")
                results = converted_results
            else:
                log.logs.info(f"⏱️ [PERF] No post-processing needed: {(time.time() - post_processing_start)*1000:.2f}ms")

            post_processing_time = (time.time() - post_processing_start) * 1000
            total_time = (time.time() - start_time) * 1000
            
            log.logs.info("✅ [PERF] get_many completed successfully:")
            log.logs.info(f"   📊 Total records: {len(results)}")
            log.logs.info(f"   ⏱️ Total time: {total_time:.2f}ms")
            log.logs.info(f"   ⏱️ DB execution: {db_execution_time:.2f}ms ({db_execution_time/total_time*100:.1f}%)")
            log.logs.info(f"   ⏱️ Post-processing: {post_processing_time:.2f}ms ({post_processing_time/total_time*100:.1f}%)")
            if populate:
                log.logs.info(f"   🔄 With populate: {len(populate)} relationships")

            return response_message(
                success_status=True,
                message="Data fetched successfully",
                data=results,
                doc_length=len(results),
            )

        except SQLAlchemyError as e:
            log.logs.error(f"Database error fetching data: {e}")
            return response_message(
                data=None,
                doc_length=0,
                error=str(e),
                message="Database error occurred",
                success_status=False,
            )
        except Exception as e:
            log.logs.error(f"Error fetching data: {e}")
            return response_message(
                data=None,
                doc_length=0,
                error=str(e),
                message="Error fetching data",
                success_status=False,
            )

    # @cache_result(ttl=600, key_prefix="get_one")  # Caching disabled
    async def get_one(
        self,
        data: Dict[str, Any],
        select: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
    ) -> ResponseMessage:
        """
        Optimized get_one with caching.
        """
        try:
            if not data:
                return response_message(
                    data=None,
                    doc_length=0,
                    error="No filter criteria provided",
                    message="Filter criteria required",
                    success_status=False,
                )

            # Build optimized query
            query = sa_select(self.model)

            # Apply populate options if provided
            if populate:
                populate_options = self._build_populate_options(populate)
                for option in populate_options:
                    query = query.options(option)

            # Apply filters with optimization
            model_fields = self._get_model_fields()
            for key, value in data.items():
                if key in model_fields:
                    column = getattr(self.model, key)

                    # Handle boolean columns explicitly
                    if (
                        hasattr(column.type, "python_type")
                        and column.type.python_type is bool
                    ):
                        if isinstance(value, str):
                            value = value.lower() in ("true", "1", "yes", "on")
                        query = query.where(column.is_(value))
                    else:
                        query = query.where(column == value)

            # Handle field selection (only if not populating to avoid conflicts)
            if select and not populate:
                include_fields = [
                    field for field in select if not field.startswith("-")
                ]

                if include_fields:
                    valid_fields = []
                    for field in include_fields:
                        if field in model_fields:
                            valid_fields.append(getattr(self.model, field))

                    if valid_fields:
                        # Build WHERE conditions
                        where_conditions = []
                        for k, v in data.items():
                            if k in model_fields:
                                where_conditions.append(getattr(self.model, k) == v)

                        query = sa_select(*valid_fields).where(*where_conditions)

            result = await self.db.execute(query)
            db_item_selected = result.scalars().first()

            if db_item_selected is None:
                return response_message(
                    data=None,
                    doc_length=0,
                    error=None,
                    message="No data found",
                    success_status=True,
                )

            # Apply field filtering for populated relationships
            if populate:
                db_item_selected = self._filter_populated_fields(
                    db_item_selected, populate
                )

                # Convert to dictionary with relationships - use safe conversion
                if hasattr(db_item_selected, "model_dump"):
                    db_item_selected = db_item_selected.model_dump()
                elif hasattr(db_item_selected, "to_dict"):
                    db_item_selected = db_item_selected.to_dict()
                else:
                    # Fallback: convert manually to avoid greenlet issues
                    db_item_selected = {"id": str(db_item_selected.id)} if hasattr(db_item_selected, "id") else {}

            return response_message(
                data=db_item_selected,
                doc_length=1,
                error=None,
                message="Data fetched successfully",
                success_status=True,
            )

        except SQLAlchemyError as e:
            log.logs.error(f"Database error in get_one: {e}")
            return response_message(
                data=None,
                doc_length=0,
                error=str(e),
                message="Database error occurred",
                success_status=False,
            )
        except Exception as e:
            log.logs.error(f"Error in get_one: {e}")
            return response_message(
                data=None,
                doc_length=0,
                error=str(e),
                message="Error fetching data",
                success_status=False,
            )

    async def create(
        self,
        data: Dict[str, Any],
        check: Optional[Dict[str, Any]] = None,
        select: Optional[List[str]] = None,
    ) -> ResponseMessage:
        """
        Optimized create with batch validation.
        """
        try:
            if not data:
                return response_message(
                    data=None,
                    doc_length=0,
                    error="No data provided",
                    message="Data is required for creation",
                    success_status=False,
                )

            # Add audit fields
            audit_data = self._add_audit_fields(data, is_create=True)

            # Check for existing records if check criteria provided
            if check:
                query = sa_select(self.model)
                for key, value in check.items():
                    if key in self._get_model_fields():
                        query = query.where(getattr(self.model, key) == value)

                result = await self.db.execute(query)
                existing_item = result.scalars().first()

                if existing_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Record with {', '.join(check.keys())} already exists",
                    )

            # Create new record
            db_item = self.model(**audit_data)
            self.db.add(db_item)
            await self.db.commit()
            await self.db.refresh(db_item)

            # Handle field selection for response
            response_data = db_item
            if select:
                valid_fields = []
                model_fields = self._get_model_fields()

                include_fields = [
                    field for field in select if not field.startswith("-")
                ]
                exclude_fields = [
                    field[1:] for field in select if field.startswith("-")
                ]

                if include_fields:
                    for field in include_fields:
                        if field in model_fields:
                            valid_fields.append(getattr(self.model, field))
                elif exclude_fields:
                    included_fields = set(model_fields) - set(exclude_fields)
                    for field in included_fields:
                        valid_fields.append(getattr(self.model, field))

                if valid_fields:
                    # Query with selected fields
                    pk_column = list(self.model.__table__.primary_key)[0]
                    pk_value = getattr(db_item, pk_column.name)
                    query = sa_select(*valid_fields).where(pk_column == pk_value)

                    result = await self.db.execute(query)
                    response_data = result.fetchone()

            # Cache invalidation disabled
            # await self._invalidate_related_caches("create")

            return response_message(
                data=response_data,
                doc_length=1,
                error=None,
                message="Data created successfully",
                success_status=True,
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except IntegrityError as e:
            await self.db.rollback()
            log.logs.error(f"Integrity error in create: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity constraint violation",
            )
        except SQLAlchemyError as e:
            await self.db.rollback()
            log.logs.error(f"Database error in create: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )
        except Exception as e:
            await self.db.rollback()
            log.logs.error(f"Error in create: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred",
            )

    async def update(
        self, filter: Dict[str, Any], data: Dict[str, Any]
    ) -> ResponseMessage:
        """
        Optimized update with batch processing.
        """
        try:
            if not filter:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Filter criteria required for update",
                )

            if not data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Update data cannot be empty",
                )

            # Add audit fields and updated_at timestamp
            update_data = self._add_audit_fields(data, is_create=False)
            model_fields = self._get_model_fields()

            if "updated_at" in model_fields:
                update_data["updated_at"] = func.now()

            query = (
                update(self.model)
                .filter_by(**filter)
                .values(**update_data)
                .execution_options(synchronize_session="fetch")
            )

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount == 0:
                return response_message(
                    data=None,
                    doc_length=0,
                    error=None,
                    message="No records found to update",
                    success_status=True,
                )

            # Fetch updated record
            updated_item = await self.get_one(data=filter)

            # Cache invalidation disabled
            # await self._invalidate_related_caches("update")

            return response_message(
                data=updated_item.get("data")
                if updated_item.get("success_status")
                else None,
                doc_length=result.rowcount,
                error=None,
                message=f"Successfully updated {result.rowcount} record(s)",
                success_status=True,
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            log.logs.error(f"Database error in update: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during update",
            )
        except Exception as e:
            await self.db.rollback()
            log.logs.error(f"Error in update: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during update",
            )

    async def delete(self, filter: Dict[str, Any]) -> ResponseMessage:
        """
        Optimized delete with cache invalidation.
        """
        try:
            if not filter:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Filter criteria required for deletion",
                )

            query = (
                delete(self.model)
                .filter_by(**filter)
                .execution_options(synchronize_session="fetch")
            )

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount == 0:
                return response_message(
                    data=None,
                    doc_length=0,
                    error=None,
                    message="No records found to delete",
                    success_status=True,
                )

            # Cache invalidation disabled
            # await self._invalidate_related_caches("delete")

            return response_message(
                data=None,
                doc_length=result.rowcount,
                error=None,
                message=f"Successfully deleted {result.rowcount} record(s)",
                success_status=True,
            )

        except SQLAlchemyError as e:
            await self.db.rollback()
            log.logs.error(f"Database error in delete: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database error occurred during deletion",
            )
        except Exception as e:
            await self.db.rollback()
            log.logs.error(f"Error in delete: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during deletion",
            )

    async def create_many(
        self,
        data: List[Dict[str, Any]],
        check: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 1000,
    ) -> ResponseMessage:
        """
        Optimized bulk create with batch processing.
        """
        try:
            if not data:
                return response_message(
                    data=[],
                    doc_length=0,
                    error=None,
                    message="No data provided",
                    success_status=True,
                )

            # Validate data structure
            if not all(isinstance(item, dict) for item in data):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All items in data must be dictionaries",
                )

            # Check for duplicates if check criteria provided
            if check:
                for condition in check:
                    query = sa_select(self.model)
                    for key, value in condition.items():
                        if key in self._get_model_fields():
                            query = query.where(getattr(self.model, key) == value)

                    result = await self.db.execute(query)
                    if result.scalars().first():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Record with {', '.join(condition.keys())} already exists",
                        )

            # Process in batches for better performance
            total_created = 0
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]

                # Add audit fields to batch
                audit_batch = []
                for item in batch:
                    audit_item = self._add_audit_fields(item, is_create=True)
                    audit_batch.append(audit_item)

                query = insert(self.model).values(audit_batch)
                await self.db.execute(query)
                total_created += len(batch)

            await self.db.commit()

            # Cache invalidation disabled
            # await self._invalidate_related_caches("create_many")

            return response_message(
                data={"created_count": total_created},
                doc_length=total_created,
                error=None,
                message=f"Successfully created {total_created} records",
                success_status=True,
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except IntegrityError as e:
            await self.db.rollback()
            log.logs.error(f"IntegrityError during bulk insert: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity constraint violation during bulk insert",
            )
        except SQLAlchemyError as e:
            await self.db.rollback()
            log.logs.error(f"Database error during bulk insert: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred during bulk insert",
            )
        except Exception as e:
            await self.db.rollback()
            log.logs.error(f"Error creating bulk data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during bulk insert",
            )

    async def _invalidate_related_caches(self, operation: str):
        """Invalidate related caches after data modification."""
        try:
            # Invalidate model-specific caches
            cache_patterns = [
                f"get_many:{self.model.__name__}:*",
                f"get_one:{self.model.__name__}:*",
                f"crud:{self.model.__name__}:*",
            ]

            for pattern in cache_patterns:
                await cache_manager.delete_pattern(pattern)

            log.logs.debug(
                f"Invalidated caches for {operation} on {self.model.__name__}"
            )
        except Exception as e:
            log.logs.warning(f"Cache invalidation error: {e}")

    def _filter_populated_fields(
        self, result: Any, populate: List[PopulateField]
    ) -> Any:
        """
        Optimized field filtering with performance logging.
        """
        filter_start = time.time()
        log.logs.info(f"🔍 [PERF] Starting field filtering for {len(populate)} populate fields")
        
        if not result or not populate:
            log.logs.info(f"⏱️ [PERF] No filtering needed: {(time.time() - filter_start)*1000:.2f}ms")
            return result

        # Handle both single results and lists
        results = result if isinstance(result, list) else [result]
        log.logs.info(f"📊 [PERF] Filtering {len(results)} items")

        items_processed = 0
        fields_filtered = 0
        second_layers_processed = 0

        for item_idx, item in enumerate(results):
            for pop_config in populate:
                path = pop_config.get("path")
                fields = pop_config.get("fields")
                second_layer = pop_config.get("second_layer", [])

                if not path or not hasattr(item, path):
                    continue

                related_obj = getattr(item, path, None)
                if related_obj is None:
                    continue

                # If no fields specified, skip filtering but still handle second layer
                if not fields:
                    if second_layer:
                        self._process_second_layer(related_obj, second_layer)
                        second_layers_processed += 1
                    continue

                # Apply field filtering
                self._apply_field_filtering_to_object(related_obj, fields)
                fields_filtered += 1

                # Handle second layer
                if second_layer:
                    self._process_second_layer(related_obj, second_layer)
                    second_layers_processed += 1

            items_processed += 1

        total_filter_time = (time.time() - filter_start) * 1000
        log.logs.info("✅ [PERF] Field filtering completed:")
        log.logs.info(f"   📊 Items processed: {items_processed}")
        log.logs.info(f"   🔍 Fields filtered: {fields_filtered}")
        log.logs.info(f"   🔄 Second layers processed: {second_layers_processed}")
        log.logs.info(f"   ⏱️ Total time: {total_filter_time:.2f}ms")

        return result

    def _apply_field_filtering_to_object(self, obj: Any, fields: List[str]) -> None:
        """Apply field filtering to an object or list of objects"""
        if obj is None:
            return

        # Handle collections vs single objects
        objects_to_process = obj if isinstance(obj, list) else [obj]

        for single_obj in objects_to_process:
            if single_obj is None:
                continue

            try:
                # Handle both SQLAlchemy objects and cached dictionaries
                if isinstance(single_obj, dict):
                    # For cached dictionaries, use the keys as available columns
                    all_columns = set(single_obj.keys())
                else:
                    # For SQLAlchemy objects, use the table columns
                    try:
                        model_class = single_obj.__class__
                        all_columns = set(model_class.__table__.columns.keys())
                    except AttributeError:
                        # Fallback if __table__ is not available
                        all_columns = set(single_obj.__dict__.keys()) if hasattr(single_obj, '__dict__') else set()

                # Parse field specifications
                exclude_fields = [
                    field[1:] for field in fields if field.startswith("-")
                ]
                include_fields = [
                    field for field in fields if not field.startswith("-")
                ]

                # Validate no mixing
                if exclude_fields and include_fields:
                    exclude_fields = []

                # Determine which fields to remove
                if exclude_fields:
                    fields_to_remove = set(exclude_fields) & all_columns
                else:
                    fields_to_remove = all_columns - set(include_fields)

                # Set unwanted fields to None
                for field_name in fields_to_remove:
                    if isinstance(single_obj, dict):
                        # For dictionaries, set the key to None
                        if field_name in single_obj:
                            single_obj[field_name] = None
                    else:
                        # For SQLAlchemy objects, use setattr
                        if hasattr(single_obj, field_name):
                            try:
                                setattr(single_obj, field_name, None)
                            except (AttributeError, TypeError):
                                continue

            except Exception as e:
                log.logs.warning(f"Error applying field filtering: {e}")
                continue

    def _process_second_layer(
        self, parent_obj: Any, second_layer: List[PopulateField]
    ) -> None:
        """Process second layer relationships"""
        if parent_obj is None or not second_layer:
            return

        # Handle collections vs single objects
        parent_objects = parent_obj if isinstance(parent_obj, list) else [parent_obj]

        for parent in parent_objects:
            if parent is None:
                continue

            for nested_config in second_layer:
                nested_path = nested_config.get("path")
                nested_fields = nested_config.get("fields")

                if not nested_path or not hasattr(parent, nested_path):
                    continue

                nested_obj = getattr(parent, nested_path, None)
                if nested_obj is not None and nested_fields:
                    self._apply_field_filtering_to_object(nested_obj, nested_fields)

    # def _convert_to_dict_with_relationships(
    #     self, obj: Any, populate: List[PopulateField]
    # ) -> Dict[str, Any]:
    #     """
    #     Convert SQLAlchemy object to dictionary including populated relationships.
    #     """
    #     if obj is None:
    #         return {}

    #     # Convert to basic dict first
    #     if hasattr(obj, "to_dict"):
    #         data = obj.to_dict()

    #         # Add populated relationship objects
    #         for pop_config in populate:
    #             path = pop_config.get("path")

    #             if path and hasattr(obj, path):
    #                 related_obj = getattr(obj, path)

    #                 if related_obj is not None:
    #                     if isinstance(related_obj, list):
    #                         # Handle collections
    #                         relationship_name = (
    #                             path.split("__")[-1] if "__" in path else path
    #                         )
    #                         data[relationship_name] = []
    #                         for item in related_obj:
    #                             if hasattr(item, "to_dict"):
    #                                 data[relationship_name].append(item.to_dict())
    #                             else:
    #                                 data[relationship_name].append(str(item.id))
    #                     else:
    #                         # Handle single relationships
    #                         if hasattr(related_obj, "to_dict"):
    #                             relationship_name = (
    #                                 path.split("__")[-1] if "__" in path else path
    #                             )
    #                             data[relationship_name] = related_obj.to_dict()
    #                         else:
    #                             relationship_name = (
    #                                 path.split("__")[-1] if "__" in path else path
    #                             )
    #                             data[relationship_name] = str(related_obj.id)
    #     else:
    #         # Fallback: convert to dict manually
    #         data = {}
    #         try:
    #             for column in obj.__table__.columns:
    #                 value = getattr(obj, column.name)
    #                 if hasattr(value, "isoformat"):  # Handle datetime objects
    #                     data[column.name] = value.isoformat()
    #                 else:
    #                     data[column.name] = value
    #         except AttributeError:
    #             # If __table__ is not available, handle different object types
    #             if isinstance(obj, dict):
    #                 # If it's already a dictionary, use it directly
    #                 data = obj.copy()
    #             elif hasattr(obj, '__dict__'):
    #                 # If it has __dict__, use it
    #                 for key, value in obj.__dict__.items():
    #                     if not key.startswith('_'):  # Skip private attributes
    #                         if hasattr(value, "isoformat"):  # Handle datetime objects
    #                             data[key] = value.isoformat()
    #                         else:
    #                             data[key] = value
    #             else:
    #                 # Last resort: try to convert to string representation
    #                 data = {"id": str(obj) if hasattr(obj, 'id') else str(obj)}

    #         # Add populated relationships for fallback case
    #         for pop_config in populate:
    #             path = pop_config.get("path")
    #             if path and hasattr(obj, path):
    #                 related_obj = getattr(obj, path)
    #                 if related_obj is not None:
    #                     if isinstance(related_obj, list):
    #                         data[path] = [str(item.id) for item in related_obj]
    #                     else:
    #                         data[path] = str(related_obj.id)

    #     return data

    def _convert_to_dict_with_relationships(
        self, obj: Any, populate: List[PopulateField]
    ) -> Dict[str, Any]:
        """
        Convert SQLAlchemy object to dictionary including populated relationships with performance logging.
        """
        conversion_start = time.time()
        log.logs.debug(f"🔄 [PERF] Converting object to dict with {len(populate)} populate fields")
        
        if obj is None:
            return {}

        # Convert to basic dict first
        dict_conversion_start = time.time()
        if hasattr(obj, "to_dict"):
            data = obj.to_dict()
            dict_conversion_time = (time.time() - dict_conversion_start) * 1000
            log.logs.debug(f"⏱️ [PERF] to_dict() conversion: {dict_conversion_time:.2f}ms")

            # Now add the actual populated relationship objects (not just IDs)
            relationship_processing_start = time.time()
            for pop_config in populate:
                path = pop_config.get("path")
                log.logs.debug(f"🔄 [PERF] Processing populate path: {path}")

                # Directly access the relationship if it exists
                if path and hasattr(obj, path):
                    related_obj = getattr(obj, path)
                    log.logs.debug(f"🔄 [PERF] Related object for {path}: {type(related_obj)}")

                    if related_obj is not None:
                        if isinstance(related_obj, list):
                            # Handle collections
                            relationship_name = (
                                path.split("__")[-1] if "__" in path else path
                            )
                            data[relationship_name] = []
                            for item in related_obj:
                                if hasattr(item, "to_dict"):
                                    data[relationship_name].append(item.to_dict())
                                else:
                                    data[relationship_name].append(str(item.id))
                            log.logs.debug(f"🔄 [PERF] Converted collection {path} with {len(related_obj)} items")
                        else:
                            # Handle single relationships
                            if hasattr(related_obj, "to_dict"):
                                # Extract the relationship name from the path (e.g., "inventory__store" -> "store")
                                # Split by double underscore and take the last part
                                relationship_name = (
                                    path.split("__")[-1] if "__" in path else path
                                )
                                data[relationship_name] = related_obj.to_dict()
                                log.logs.debug(f"🔄 [PERF] Converted single relationship {path} to {relationship_name}")
                            else:
                                relationship_name = (
                                    path.split("__")[-1] if "__" in path else path
                                )
                                data[relationship_name] = str(related_obj.id)
                                log.logs.debug(f"🔄 [PERF] Used ID for {relationship_name}")
            
            relationship_processing_time = (time.time() - relationship_processing_start) * 1000
            log.logs.debug(f"⏱️ [PERF] Relationship processing: {relationship_processing_time:.2f}ms")
        else:
            # Fallback: convert to dict manually
            data: Dict[str, Any] = {}
            
            # Check if obj is already a dictionary (from cache)
            if isinstance(obj, dict):
                # If it's already a dictionary, use it directly
                data = obj.copy()
                log.logs.debug("🔄 [PERF] Object was already a dictionary")
            elif hasattr(obj, '__dict__'):
                # If it has __dict__, use it
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):  # Skip private attributes
                        if hasattr(value, "isoformat"):  # Handle datetime objects
                            data[key] = value.isoformat()
                        else:
                            data[key] = value
                log.logs.debug(f"🔄 [PERF] Converted using __dict__ with {len(data)} fields")
            else:
                # Last resort: try to convert to string representation
                data = {"id": str(obj) if hasattr(obj, 'id') else str(obj)}
                log.logs.debug("🔄 [PERF] Fallback conversion to string")

            # Add populated relationships for fallback case
            for pop_config in populate:
                path = pop_config.get("path")
                if path and hasattr(obj, path):
                    related_obj = getattr(obj, path)
                    if related_obj is not None:
                        if isinstance(related_obj, list):
                            data[path] = [str(item.id) for item in related_obj if hasattr(item, 'id')]
                        else:
                            data[path] = str(related_obj.id) if hasattr(related_obj, 'id') else str(related_obj)
            
            dict_conversion_time = (time.time() - dict_conversion_start) * 1000
            log.logs.debug(f"⏱️ [PERF] Manual dict conversion: {dict_conversion_time:.2f}ms")

        total_conversion_time = (time.time() - conversion_start) * 1000
        log.logs.debug(f"✅ [PERF] Object conversion completed: {total_conversion_time:.2f}ms ({len(data)} fields)")
        return data

    def get_available_relationships(self) -> List[str]:
        """Get all available relationship names on the model."""
        return list(self._get_model_relationships())

    def debug_populate_paths(self, populate: List[PopulateField]) -> None:
        """Debug helper to check populate paths against available relationships."""
        available_rels = self.get_available_relationships()
        log.logs.info(
            f"Available relationships in {self.model.__name__}: {available_rels}"
        )

        for pop_config in populate:
            path = pop_config.get("path")
            if path:
                if path in available_rels:
                    log.logs.info(f"✓ Populate path '{path}' is a valid relationship")
                else:
                    log.logs.warning(
                        f"✗ Populate path '{path}' is NOT a valid relationship"
                    )
                    log.logs.warning(f"  Available relationships: {available_rels}")
