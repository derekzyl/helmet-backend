"""
Ultra-Optimized CRUD Service for maximum performance.
Optimizations applied:
1. Minimal logging overhead with conditional execution
2. Reduced time.time() calls
3. Optimized dictionary conversions with caching
4. Compiled query caching
5. Better memory management
6. Batch processing improvements
"""

import json
from typing import Any, Dict, List, Optional, Type, TypedDict

from fastapi import HTTPException, status
from sqlalchemy import delete, func, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as sa_select
from sqlalchemy.orm import DeclarativeBase, joinedload, selectinload
from sqlalchemy.sql import insert

from app.config.env import env
from app.utils.crud.super_optimised_query import UltraOptimizedQueries
from app.utils.crud.types_crud import ResponseMessage, response_message
from app.utils.logger import log

# Performance logging flag - disable in production
ENABLE_PERF_LOGS = env.get("enable_perf_logs", False)  # Set to False in production


class PopulateField(TypedDict, total=False):
    path: str
    fields: Optional[List[str]]
    second_layer: Optional[List["PopulateField"]]


def perf_log(message: str, level: str = "info"):
    """Conditional performance logging to reduce overhead."""
    if ENABLE_PERF_LOGS:
        getattr(log.logs, level)(message)


class UltraOptimizedCrudService:
    """
    Ultra high-performance CRUD service with minimal overhead.
    """

    # Class-level caches shared across instances
    _model_fields_cache: Dict[str, tuple] = {}
    _model_relationships_cache: Dict[str, tuple] = {}
    _populate_options_cache: Dict[str, Any] = {}

    def __init__(
        self,
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None,
    ):
        self.model = model
        self.db = db
        self.current_user_id = current_user_id
        self._model_name = model.__name__

    def _get_model_fields(self) -> tuple:
        """Cache model field names at class level."""
        if self._model_name not in self._model_fields_cache:
            self._model_fields_cache[self._model_name] = tuple(
                self.model.__table__.columns.keys()
            )
        return self._model_fields_cache[self._model_name]

    def _get_model_relationships(self) -> tuple:
        """Cache model relationship names at class level."""
        if self._model_name not in self._model_relationships_cache:
            relationships = []
            for attr_name in dir(self.model):
                if not attr_name.startswith("_"):
                    attr = getattr(self.model, attr_name, None)
                    if (
                        attr
                        and hasattr(attr, "property")
                        and hasattr(attr.property, "mapper")
                    ):
                        relationships.append(attr_name)
            self._model_relationships_cache[self._model_name] = tuple(relationships)
        return self._model_relationships_cache[self._model_name]

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

        # Batch field checks
        if is_create and "created_by_id" in model_fields:
            audit_data["created_by_id"] = self.current_user_id

        if "updated_by_id" in model_fields:
            audit_data["updated_by_id"] = self.current_user_id

        return audit_data

    def _build_populate_options(self, populate: List[PopulateField]) -> List[Any]:
        """
        Highly optimized populate options builder with aggressive caching.
        """
        perf_log(f"📊 Building populate options for {len(populate)} relationships")

        options = []
        relationships = self._get_model_relationships()

        for pop_config in populate:
            path = pop_config.get("path")
            second_layer = pop_config.get("second_layer", [])

            if not path or path not in relationships:
                perf_log(f"⚠️ Invalid populate path: {path}", "warning")
                continue

            # Generate cache key
            cache_key = (
                f"{self._model_name}:{path}:{json.dumps(second_layer, sort_keys=True)}"
            )

            # Check class-level cache
            if cache_key in self._populate_options_cache:
                options.append(self._populate_options_cache[cache_key])
                continue

            # Build load option
            relationship_attr = getattr(self.model, path)

            # Use selectinload for collections, joinedload for single relationships
            if hasattr(relationship_attr.property, "collection_class"):
                load_option = selectinload(relationship_attr)
            else:
                load_option = joinedload(relationship_attr)

            # Handle second layer population (nested relationships)
            if second_layer:
                for nested_config in second_layer:
                    nested_path = nested_config.get("path")
                    if nested_path:
                        nested_attr = getattr(
                            relationship_attr.property.mapper.class_, nested_path
                        )

                        if hasattr(nested_attr.property, "collection_class"):
                            load_option = load_option.selectinload(nested_attr)
                        else:
                            load_option = load_option.joinedload(nested_attr)

            # Cache the built option
            self._populate_options_cache[cache_key] = load_option
            options.append(load_option)

        perf_log(f"✅ Built {len(options)} populate options")
        return options

    async def get_many(
        self,
        query: Dict[str, Any],
        filter: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
    ) -> ResponseMessage:
        """
        Ultra-optimized get_many with minimal overhead.
        """
        try:
            # Build query
            query_model = sa_select(self.model)

            # Apply populate options if provided
            if populate:
                populate_options = self._build_populate_options(populate)
                for option in populate_options:
                    query_model = query_model.options(option)

            # Apply additional filters efficiently
            if filter:
                model_fields = self._get_model_fields()
                # Build all filter conditions in one pass
                filter_conditions = [
                    getattr(self.model, key) == value
                    for key, value in filter.items()
                    if key in model_fields
                ]
                if filter_conditions:
                    query_model = query_model.where(*filter_conditions)

            # Use optimized queries
            optimized_query = UltraOptimizedQueries(query_model, query, self.model)
            optimized_query.filter().limit_fields().paginate().sort()

            # Execute query
            result = await self.db.execute(optimized_query.model)
            results = result.scalars().all()

            if not results:
                return response_message(
                    data=[],
                    error=None,
                    message="No data found",
                    success_status=True,
                    doc_length=0,
                )

            # Post-process results efficiently
            if populate:
                # Filter and convert in single pass
                results = [
                    self._fast_convert_to_dict(result, populate) for result in results
                ]

            perf_log(f"✅ Retrieved {len(results)} records")

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

    async def get_one(
        self,
        data: Dict[str, Any],
        select: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
    ) -> ResponseMessage:
        """
        Ultra-optimized get_one.
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

            # Build query efficiently
            query = sa_select(self.model)

            # Apply populate options
            if populate:
                populate_options = self._build_populate_options(populate)
                for option in populate_options:
                    query = query.options(option)

            # Apply filters
            model_fields = self._get_model_fields()
            for key, value in data.items():
                if key in model_fields:
                    column = getattr(self.model, key)

                    # Handle boolean columns
                    if (
                        hasattr(column.type, "python_type")
                        and column.type.python_type is bool
                    ):
                        if isinstance(value, str):
                            value = value.lower() in ("true", "1", "yes", "on")
                        query = query.where(column.is_(value))
                    else:
                        query = query.where(column == value)

            # Handle field selection
            if select and not populate:
                include_fields = [
                    field for field in select if not field.startswith("-")
                ]

                if include_fields:
                    valid_fields = [
                        getattr(self.model, field)
                        for field in include_fields
                        if field in model_fields
                    ]

                    if valid_fields:
                        where_conditions = [
                            getattr(self.model, k) == v
                            for k, v in data.items()
                            if k in model_fields
                        ]
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

            # Convert result efficiently
            if populate:
                db_item_selected = self._fast_convert_to_dict(
                    db_item_selected, populate
                )

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

    def _fast_convert_to_dict(
        self, obj: Any, populate: List[PopulateField]
    ) -> Dict[str, Any]:
        """
        Fast conversion to dictionary with minimal overhead.
        """
        if obj is None:
            return {}

        # Quick conversion using to_dict if available
        if hasattr(obj, "to_dict"):
            data = obj.to_dict()

            # Add populated relationships efficiently
            for pop_config in populate:
                path = pop_config.get("path")
                if not path or not hasattr(obj, path):
                    continue

                related_obj = getattr(obj, path)
                if related_obj is None:
                    continue

                relationship_name = path.split("__")[-1] if "__" in path else path

                if isinstance(related_obj, list):
                    # Handle collections
                    data[relationship_name] = [
                        item.to_dict()
                        if hasattr(item, "to_dict")
                        else {"id": str(item.id)}
                        for item in related_obj
                    ]
                else:
                    # Handle single relationships
                    data[relationship_name] = (
                        related_obj.to_dict()
                        if hasattr(related_obj, "to_dict")
                        else {"id": str(related_obj.id)}
                    )

            return data

        # Fallback
        return {"id": str(obj.id) if hasattr(obj, "id") else str(obj)}

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
                model_fields = self._get_model_fields()
                query = sa_select(self.model)
                for key, value in check.items():
                    if key in model_fields:
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
                model_fields = self._get_model_fields()
                include_fields = [
                    field for field in select if not field.startswith("-")
                ]
                exclude_fields = [
                    field[1:] for field in select if field.startswith("-")
                ]

                if include_fields:
                    valid_fields = [
                        getattr(self.model, field)
                        for field in include_fields
                        if field in model_fields
                    ]
                elif exclude_fields:
                    included_fields = set(model_fields) - set(exclude_fields)
                    valid_fields = [
                        getattr(self.model, field) for field in included_fields
                    ]
                else:
                    valid_fields = []

                if valid_fields:
                    pk_column = list(self.model.__table__.primary_key)[0]
                    pk_value = getattr(db_item, pk_column.name)
                    query = sa_select(*valid_fields).where(pk_column == pk_value)

                    result = await self.db.execute(query)
                    response_data = result.fetchone()

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

            # Add audit fields
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
        Optimized delete operation.
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
        Ultra-optimized bulk create with efficient batch processing.
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
                model_fields = self._get_model_fields()
                for condition in check:
                    query = sa_select(self.model)
                    for key, value in condition.items():
                        if key in model_fields:
                            query = query.where(getattr(self.model, key) == value)

                    result = await self.db.execute(query)
                    if result.scalars().first():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Record with {', '.join(condition.keys())} already exists",
                        )

            # Process in batches efficiently
            total_created = 0
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]

                # Add audit fields to batch in one pass
                audit_batch = [
                    self._add_audit_fields(item, is_create=True) for item in batch
                ]

                query = insert(self.model).values(audit_batch)
                await self.db.execute(query)
                total_created += len(batch)

            await self.db.commit()

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
