from typing import Any, Dict, List, Optional, Type, TypedDict

from fastapi import HTTPException, status
from sqlalchemy import delete, func, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as sa_select
from sqlalchemy.orm import DeclarativeBase, joinedload, selectinload
from sqlalchemy.sql import insert

from app.utils.crud.queries import Queries
from app.utils.crud.types_crud import ResponseMessage, response_message
from app.utils.logger import log


class PopulateField(TypedDict, total=False):
    path: str
    fields: Optional[List[str]]
    second_layer: Optional[List["PopulateField"]]


class CrudService:
    def __init__(
        self,
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None,
    ):
        self.model = model
        self.db = db
        self.current_user_id = current_user_id

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

        # Check if model has audit fields
        if hasattr(self.model, "created_by_id") and is_create:
            audit_data["created_by_id"] = self.current_user_id

        if hasattr(self.model, "updated_by_id"):
            audit_data["updated_by_id"] = self.current_user_id

        return audit_data

    def _build_populate_options(self, populate: List[PopulateField]) -> List[Any]:
        """
        Build SQLAlchemy relationship loading options from populate configuration.

        :param populate: List of populate field configurations
        :return: List of SQLAlchemy loading options
        """
        options = []

        for pop_config in populate:
            path = pop_config.get("path")
            fields = pop_config.get("fields")
            second_layer = pop_config.get("second_layer", [])

            if not path:
                continue

            # Check if path is a relationship (not a column)
            if not hasattr(self.model, path):
                log.logs.warning(
                    f"Populate path '{path}' not found in model {self.model.__name__}"
                )
                continue

            relationship_attr = getattr(self.model, path)
            
            # Verify this is actually a relationship, not a column
            if not hasattr(relationship_attr, 'property') or not hasattr(relationship_attr.property, 'mapper'):
                log.logs.warning(
                    f"Populate path '{path}' is not a relationship in model {self.model.__name__}"
                )
                continue

            log.logs.info(f"Building populate option for relationship: {path}")

            try:
                # Use selectinload for collections, joinedload for single relationships
                if hasattr(relationship_attr.property, "collection_class"):
                    load_option = selectinload(relationship_attr)
                    log.logs.info(f"Using selectinload for collection relationship: {path}")
                else:
                    load_option = joinedload(relationship_attr)
                    log.logs.info(f"Using joinedload for single relationship: {path}")

                # Handle second layer population (nested relationships)
                if second_layer:
                    for nested_config in second_layer:
                        nested_path = nested_config.get("path")
                        if nested_path and hasattr(
                            relationship_attr.property.mapper.class_, nested_path
                        ):
                            nested_attr = getattr(
                                relationship_attr.property.mapper.class_, nested_path
                            )

                            # Verify nested path is also a relationship
                            if hasattr(nested_attr, 'property') and hasattr(nested_attr.property, 'mapper'):
                                # Chain the loading options
                                if hasattr(nested_attr.property, "collection_class"):
                                    load_option = load_option.selectinload(nested_attr)
                                else:
                                    load_option = load_option.joinedload(nested_attr)
                                log.logs.info(f"Added nested populate: {path}.{nested_path}")
                            else:
                                log.logs.warning(f"Nested path '{nested_path}' is not a relationship")

                options.append(load_option)

            except AttributeError as e:
                log.logs.warning(f"Error building populate option for '{path}': {e}")
                continue

        return options

    # def _filter_populated_fields(
    #     self, result: Any, populate: List[PopulateField]
    # ) -> Any:
    #     """
    #     Filter fields in populated relationships based on the fields specification.
    #     This is a post-processing step since SQLAlchemy doesn't support field selection in relationships.

    #     :param result: The query result
    #     :param populate: List of populate field configurations
    #     :return: Result with filtered relationship fields
    #     """
    #     if not result or not populate:
    #         return result

    #     # Handle both single results and lists
    #     results = result if isinstance(result, list) else [result]

    #     for item in results:
    #         for pop_config in populate:
    #             path = pop_config.get("path")
    #             fields = pop_config.get("fields")

    #             if not path or not fields or not hasattr(item, path):
    #                 continue

    #             related_obj = getattr(item, path, None)
    #             if related_obj is None:
    #                 continue

    #             # Handle collections vs single objects
    #             related_objects = (
    #                 related_obj if isinstance(related_obj, list) else [related_obj]
    #             )

    #             for related in related_objects:
    #                 if related is None:
    #                     continue

    #                 # Get all attributes of the related object
    #                 all_attrs = [
    #                     attr
    #                     for attr in dir(related)
    #                     if not attr.startswith("_")
    #                     and not callable(getattr(related, attr))
    #                 ]

    #                 # Remove attributes not in the fields list
    #                 for attr in all_attrs:
    #                     if attr not in fields and hasattr(related, attr):
    #                         try:
    #                             # Set unwanted fields to None or remove them
    #                             # Note: This is a simplified approach, you might want to use a more sophisticated method
    #                             pass  # In practice, you might want to create a new object with only the desired fields
    #                         except:
    #                             pass

    #     return result






















    # def _filter_populated_fields(self, result: Any, populate: List[PopulateField]) -> Any:
    #     """
    #     Filter fields in populated relationships based on the fields specification.
    #     Field filtering rules:
    #     - Empty fields list: return all fields
    #     - Fields with '-' prefix (e.g., ['-name', '-email']): exclude those fields, keep everything else
    #     - Fields without '-' prefix (e.g., ['name', 'email']): include only those fields
    #     - Cannot mix include and exclude in the same list
        
    #     :param result: The query result
    #     :param populate: List of populate field configurations
    #     :return: Result with filtered relationship fields
    #     """
    #     if not result or not populate:
    #         return result
            
    #     # Handle both single results and lists
    #     results = result if isinstance(result, list) else [result]
        
    #     for item in results:
    #         for pop_config in populate:
    #             path = pop_config.get('path')
    #             fields = pop_config.get('fields')
    #             second_layer = pop_config.get('second_layer', [])
                
    #             if not path or not hasattr(item, path):
    #                 continue
                    
    #             # If fields is empty, skip filtering (return all fields)
    #             if not fields:
    #                 # Still process second layer if it exists
    #                 if second_layer:
    #                     self._filter_nested_fields(item, path, second_layer)
    #                 continue
                    
    #             related_obj = getattr(item, path, None)
    #             if related_obj is None:
    #                 continue
                    
    #             # Handle collections vs single objects
    #             related_objects = related_obj if isinstance(related_obj, list) else [related_obj]
                
    #             for related in related_objects:
    #                 if related is None:
    #                     continue
                        
    #                 try:
    #                     # Get the model class to access table columns
    #                     related_model = related.__class__
    #                     all_column_names = set(related_model.__table__.columns.keys())
                        
    #                     # Get all current attributes on the instance
    #                     current_attrs = set(attr for attr in dir(related) 
    #                                     if not attr.startswith('_') 
    #                                     and attr in all_column_names
    #                                     and hasattr(related, attr))
                        
    #                     # Determine filtering mode
    #                     exclude_fields = [field[1:] for field in fields if field.startswith('-')]
    #                     include_fields = [field for field in fields if not field.startswith('-')]
                        
    #                     # Validate that we don't have mixed modes
    #                     if exclude_fields and include_fields:
    #                         log.logs.warning(f"Mixed include/exclude fields in populate config for {path}. Using include mode.")
    #                         # Default to include mode if mixed
    #                         exclude_fields = []
                        
    #                     # Determine which attributes to remove
    #                     if exclude_fields:
    #                         # Exclude mode: remove specified fields
    #                         attrs_to_remove = set(exclude_fields) & current_attrs
    #                     else:
    #                         # Include mode: keep only specified fields
    #                         attrs_to_remove = current_attrs - set(include_fields)
                        
    #                     # Remove unwanted attributes
    #                     for attr in attrs_to_remove:
    #                         try:
    #                             if hasattr(related, attr):
    #                                 delattr(related, attr)
    #                         except (AttributeError, TypeError):
    #                             # If we can't delete the attribute, set it to None
    #                             try:
    #                                 setattr(related, attr, None)
    #                             except (AttributeError, TypeError):
    #                                 # If we can't modify it at all, skip it
    #                                 pass
                        
    #                 except Exception as e:
    #                     log.logs.warning(f"Error filtering populated fields for {path}: {e}")
    #                     continue
                
    #             # Handle second layer filtering (nested relationships)
    #             if second_layer:
    #                 self._filter_nested_fields(item, path, second_layer)
                        
    #     return result

    def _filter_nested_fields(self, parent_item: Any, parent_path: str, second_layer: List[PopulateField]) -> None:
        """
        Helper method to filter nested relationship fields.
        
        :param parent_item: The parent item containing the nested relationships
        :param parent_path: The path to the parent relationship
        :param second_layer: List of nested populate field configurations
        """
        if not hasattr(parent_item, parent_path):
            return
            
        parent_related_obj = getattr(parent_item, parent_path, None)
        if parent_related_obj is None:
            return
            
        # Handle collections vs single objects for parent relationship
        parent_related_objects = parent_related_obj if isinstance(parent_related_obj, list) else [parent_related_obj]
        
        for parent_related in parent_related_objects:
            if parent_related is None:
                continue
                
            for nested_config in second_layer:
                nested_path = nested_config.get('path')
                nested_fields = nested_config.get('fields')
                
                if not nested_path or not hasattr(parent_related, nested_path):
                    continue
                    
                # If nested fields is empty, skip filtering (return all fields)
                if not nested_fields:
                    continue
                    
                nested_obj = getattr(parent_related, nested_path, None)
                if nested_obj is None:
                    continue
                    
                # Handle collections vs single objects for nested relationships
                nested_objects = nested_obj if isinstance(nested_obj, list) else [nested_obj]
                
                for nested_item in nested_objects:
                    if nested_item is None:
                        continue
                        
                    try:
                        # Get nested model columns
                        nested_model = nested_item.__class__
                        nested_column_names = set(nested_model.__table__.columns.keys())
                        
                        # Get current nested attributes
                        nested_current_attrs = set(attr for attr in dir(nested_item) 
                                                if not attr.startswith('_') 
                                                and attr in nested_column_names
                                                and hasattr(nested_item, attr))
                        
                        # Determine filtering mode for nested fields
                        nested_exclude_fields = [field[1:] for field in nested_fields if field.startswith('-')]
                        nested_include_fields = [field for field in nested_fields if not field.startswith('-')]
                        
                        # Validate that we don't have mixed modes
                        if nested_exclude_fields and nested_include_fields:
                            log.logs.warning(f"Mixed include/exclude fields in nested populate config for {nested_path}. Using include mode.")
                            # Default to include mode if mixed
                            nested_exclude_fields = []
                        
                        # Determine which nested attributes to remove
                        if nested_exclude_fields:
                            # Exclude mode: remove specified fields
                            nested_attrs_to_remove = set(nested_exclude_fields) & nested_current_attrs
                        else:
                            # Include mode: keep only specified fields
                            nested_attrs_to_remove = nested_current_attrs - set(nested_include_fields)
                        
                        # Remove unwanted nested attributes
                        for attr in nested_attrs_to_remove:
                            try:
                                if hasattr(nested_item, attr):
                                    delattr(nested_item, attr)
                            except (AttributeError, TypeError):
                                try:
                                    setattr(nested_item, attr, None)
                                except (AttributeError, TypeError):
                                    pass
                                    
                    except Exception as e:
                        log.logs.warning(f"Error filtering nested fields for {nested_path}: {e}")
                        continue


    # Alternative implementation using a dictionary-based approach (more robust)
    def _filter_populated_fields_dict_approach(self, result: Any, populate: List[PopulateField]) -> Any:
        """
        Alternative implementation that converts objects to dictionaries for field filtering.
        Field filtering rules:
        - Empty fields list: return all fields
        - Fields with '-' prefix (e.g., ['-name', '-email']): exclude those fields, keep everything else
        - Fields without '-' prefix (e.g., ['name', 'email']): include only those fields
        - Cannot mix include and exclude in the same list
        
        :param result: The query result
        :param populate: List of populate field configurations
        :return: Result with filtered relationship fields
        """
        if not result or not populate:
            return result
            
        # Handle both single results and lists
        results = result if isinstance(result, list) else [result]
        
        for item in results:
            for pop_config in populate:
                path = pop_config.get('path')
                fields = pop_config.get('fields')
                second_layer = pop_config.get('second_layer', [])
                
                if not path or not hasattr(item, path):
                    continue
                    
                related_obj = getattr(item, path, None)
                if related_obj is None:
                    continue
                    
                # Handle collections vs single objects
                is_collection = isinstance(related_obj, list)
                related_objects = related_obj if is_collection else [related_obj]
                
                filtered_objects = []
                
                for related in related_objects:
                    if related is None:
                        filtered_objects.append(None)
                        continue
                        
                    try:
                        # Get all available fields from the model
                        related_model = related.__class__
                        all_column_names = set(related_model.__table__.columns.keys())
                        available_fields = set(attr for attr in all_column_names if hasattr(related, attr))
                        
                        # Determine which fields to include
                        if not fields:
                            # Empty fields list: include all fields
                            fields_to_include = available_fields
                        else:
                            # Parse include/exclude fields
                            exclude_fields = [field[1:] for field in fields if field.startswith('-')]
                            include_fields = [field for field in fields if not field.startswith('-')]
                            
                            # Validate that we don't have mixed modes
                            if exclude_fields and include_fields:
                                log.logs.warning(f"Mixed include/exclude fields in populate config for {path}. Using include mode.")
                                exclude_fields = []
                            
                            if exclude_fields:
                                # Exclude mode: keep all fields except specified ones
                                fields_to_include = available_fields - set(exclude_fields)
                            else:
                                # Include mode: keep only specified fields
                                fields_to_include = set(include_fields) & available_fields
                        
                        # Create filtered object with selected fields
                        filtered_obj = related.__class__()
                        for field in fields_to_include:
                            if hasattr(related, field):
                                value = getattr(related, field)
                                if hasattr(filtered_obj, field):
                                    setattr(filtered_obj, field, value)
                        
                        # Handle second layer filtering
                        if second_layer:
                            for nested_config in second_layer:
                                nested_path = nested_config.get('path')
                                nested_fields = nested_config.get('fields')
                                
                                if (nested_path and hasattr(related, nested_path) and 
                                    nested_path in fields_to_include):  # Only if nested path was included
                                    
                                    nested_obj = getattr(related, nested_path, None)
                                    if nested_obj is not None:
                                        # Apply same filtering logic to nested objects
                                        nested_is_collection = isinstance(nested_obj, list)
                                        nested_objects = nested_obj if nested_is_collection else [nested_obj]
                                        
                                        filtered_nested_objects = []
                                        for nested_item in nested_objects:
                                            if nested_item is None:
                                                filtered_nested_objects.append(None)
                                                continue
                                            
                                            # Get available nested fields
                                            nested_model = nested_item.__class__
                                            nested_all_columns = set(nested_model.__table__.columns.keys())
                                            nested_available_fields = set(attr for attr in nested_all_columns 
                                                                        if hasattr(nested_item, attr))
                                            
                                            # Determine which nested fields to include
                                            if not nested_fields:
                                                # Empty nested fields list: include all fields
                                                nested_fields_to_include = nested_available_fields
                                            else:
                                                # Parse nested include/exclude fields
                                                nested_exclude_fields = [field[1:] for field in nested_fields if field.startswith('-')]
                                                nested_include_fields = [field for field in nested_fields if not field.startswith('-')]
                                                
                                                # Validate mixed modes
                                                if nested_exclude_fields and nested_include_fields:
                                                    log.logs.warning(f"Mixed include/exclude fields in nested populate config for {nested_path}. Using include mode.")
                                                    nested_exclude_fields = []
                                                
                                                if nested_exclude_fields:
                                                    # Exclude mode: keep all except specified
                                                    nested_fields_to_include = nested_available_fields - set(nested_exclude_fields)
                                                else:
                                                    # Include mode: keep only specified
                                                    nested_fields_to_include = set(nested_include_fields) & nested_available_fields
                                            
                                            # Create filtered nested object
                                            nested_filtered_obj = nested_item.__class__()
                                            for nested_field in nested_fields_to_include:
                                                if hasattr(nested_item, nested_field):
                                                    nested_value = getattr(nested_item, nested_field)
                                                    if hasattr(nested_filtered_obj, nested_field):
                                                        setattr(nested_filtered_obj, nested_field, nested_value)
                                            
                                            filtered_nested_objects.append(nested_filtered_obj)
                                        
                                        # Set the filtered nested objects
                                        nested_result = filtered_nested_objects if nested_is_collection else (filtered_nested_objects[0] if filtered_nested_objects else None)
                                        setattr(filtered_obj, nested_path, nested_result)
                        
                        filtered_objects.append(filtered_obj)
                        
                    except Exception as e:
                        log.logs.warning(f"Error creating filtered object for {path}: {e}")
                        filtered_objects.append(related)  # Fall back to original object
                
                # Set the filtered objects back to the main item
                try:
                    filtered_result = filtered_objects if is_collection else (filtered_objects[0] if filtered_objects else None)
                    setattr(item, path, filtered_result)
                except Exception as e:
                    log.logs.warning(f"Error setting filtered relationship {path}: {e}")
                    
        return result






    async def get_many(
        self,
        query: Dict[str, Any],
        filter: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
    ) -> ResponseMessage:
        try:
            query_model = sa_select(self.model)

            # Apply populate options if provided
            if populate:
                # Debug populate paths
                self.debug_populate_paths(populate)
                
                populate_options = self._build_populate_options(populate)
                for option in populate_options:
                    query_model = query_model.options(option)

            # Apply additional filters
            if filter:
                for key, value in filter.items():
                    if hasattr(self.model, key):
                        query_model = query_model.where(
                            getattr(self.model, key) == value
                        )
                    else:
                        log.logs.warning(
                            f"Filter field '{key}' not found in model {self.model.__name__}"
                        )

            query_handler = Queries(query_model, query, self.model)

            # Apply select fields if provided
            if (
                select_fields and not populate
            ):  # Don't limit fields if we're populating relationships
                valid_fields = []
                for field in select_fields:
                    if hasattr(self.model, field):
                        valid_fields.append(getattr(self.model, field))
                    else:
                        log.logs.warning(
                            f"Select field '{field}' not found in model {self.model.__name__}"
                        )

                if valid_fields:
                    query_handler.model = query_handler.model.with_only_columns(
                        *valid_fields
                    )

            query_handler.filter().limit_fields().paginate().sort()

            result = await self.db.execute(query_handler.model)
            results = result.scalars().all()

            if not results:
                return response_message(
                    data=[],
                    error=None,
                    message="No data found",
                    success_status=True,
                    doc_length=0,
                )

            # Apply field filtering for populated relationships
            if populate:
                results = self._filter_populated_fields(results, populate)
                
                # Convert to dictionaries with relationships
                converted_results = []
                for result in results:
                    converted_result = self._convert_to_dict_with_relationships(result, populate)
                    converted_results.append(converted_result)
                results = converted_results

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
        Retrieve a single record based on the provided filter criteria.

        :param data: Dictionary containing filter criteria
        :param select: Optional list of fields to select (prefix with '-' to exclude)
        :param populate: Optional list of relationships to populate with field selection
        """
        try:
            # Validate filter data
            if not data:
                return response_message(
                    data=None,
                    doc_length=0,
                    error="No filter criteria provided",
                    message="Filter criteria required",
                    success_status=False,
                )

            # Build base query
            query = sa_select(self.model)

            # Apply populate options if provided
            if populate:
                populate_options = self._build_populate_options(populate)
                for option in populate_options:
                    query = query.options(option)

            # Apply filters
            valid_filters = {}
            for key, value in data.items():
                if hasattr(self.model, key):
                    valid_filters[key] = value
                    query = query.where(getattr(self.model, key) == value)
                else:
                    log.logs.warning(
                        f"Filter field '{key}' not found in model {self.model.__name__}"
                    )

            # Apply filters
            valid_filters = {}
            for key, value in data.items():
                if hasattr(self.model, key):
                    valid_filters[key] = value
                    column = getattr(self.model, key)
                    
                    # Handle boolean columns explicitly
                    if hasattr(column.type, 'python_type') and column.type.python_type is bool:
                        # Ensure boolean values are properly typed
                        if isinstance(value, str):
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        query = query.where(column.is_(value))
                    else:
                        query = query.where(column == value)
                else:
                    log.logs.warning(
                        f"Filter field '{key}' not found in model {self.model.__name__}"
                    )

            # Handle field selection (only if not populating to avoid conflicts)
            if select and not populate:
                include_fields = [
                    field for field in select if not field.startswith("-")
                ]
                exclude_fields = [
                    field[1:] for field in select if field.startswith("-")
                ]

                if include_fields:
                    # Include only specified fields
                    valid_fields = []
                    for field in include_fields:
                        if hasattr(self.model, field):
                            valid_fields.append(getattr(self.model, field))
                        else:
                            log.logs.warning(
                                f"Include field '{field}' not found in model {self.model.__name__}"
                            )

                    if valid_fields:
                        # Build WHERE conditions properly
                        where_conditions = []
                        for k, v in valid_filters.items():
                            where_conditions.append(getattr(self.model, k) == v)

                        query = sa_select(*valid_fields).where(*where_conditions)

                elif exclude_fields:
                    # Exclude specified fields
                    all_fields = set(self.model.__table__.columns.keys())
                    included_fields = all_fields - set(exclude_fields)
                    valid_fields = []
                    for field in included_fields:
                        if hasattr(self.model, field):
                            valid_fields.append(getattr(self.model, field))

                    if valid_fields:
                        # Build WHERE conditions properly
                        where_conditions = []
                        for k, v in valid_filters.items():
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
                
                # Convert to dictionary with relationships
                db_item_selected = self._convert_to_dict_with_relationships(db_item_selected, populate)

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

    # ... (rest of the methods remain the same: create, update, delete, create_many, etc.)

    async def create(
        self,
        data: Dict[str, Any],
        check: Optional[Dict[str, Any]] = None,
        select: Optional[List[str]] = None,
    ) -> ResponseMessage:
        """
        Create a new record with optional duplicate checking and field selection.

        :param data: Data to create the record
        :param check: Optional conditions to check for duplicates
        :param select: Optional fields to return (prefix with '-' to exclude)
        """
        try:
            # Validate input data
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
                    if hasattr(self.model, key):
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
            valid_fields = []
            if select:
                include_fields = [
                    field for field in select if not field.startswith("-")
                ]
                exclude_fields = [
                    field[1:] for field in select if field.startswith("-")
                ]

                if include_fields:
                    for field in include_fields:
                        if hasattr(self.model, field):
                            valid_fields.append(getattr(self.model, field))
                elif exclude_fields:
                    all_fields = set(self.model.__table__.columns.keys())
                    included_fields = all_fields - set(exclude_fields)
                    for field in included_fields:
                        if hasattr(self.model, field):
                            valid_fields.append(getattr(self.model, field))

                if valid_fields:
                    # Query with selected fields
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
        Update records matching the filter criteria.

        :param filter: Criteria to identify records to update
        :param data: New data values
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
            if hasattr(self.model, "updated_at"):
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
        Delete records matching the filter criteria.

        :param filter: Criteria to identify records to delete
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
        Create multiple records with optional duplicate checking and batch processing.

        :param data: List of data dictionaries to create records
        :param check: Optional list of conditions to check for duplicates
        :param batch_size: Number of records to process in each batch
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
                        if hasattr(self.model, key):
                            query = query.where(getattr(self.model, key) == value)

                    result = await self.db.execute(query)
                    if result.scalars().first():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Record with {', '.join(condition.keys())} already exists",
                        )

            # Process in batches to avoid memory issues
            total_created = 0
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                query = insert(self.model).values(batch)
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

    def _validate_field_exists(self, field_name: str) -> bool:
        """Helper method to validate if a field exists on the model."""
        return hasattr(self.model, field_name)

    def _get_model_fields(self) -> List[str]:
        """Helper method to get all available fields on the model."""
        return list(self.model.__table__.columns.keys())

    def get_available_relationships(self) -> List[str]:
        """Helper method to get all available relationship names on the model."""
        relationships = []
        for attr_name in dir(self.model):
            attr = getattr(self.model, attr_name)
            if (hasattr(attr, 'property') and 
                hasattr(attr.property, 'mapper') and 
                not attr_name.startswith('_')):
                relationships.append(attr_name)
        return relationships

    def debug_populate_paths(self, populate: List[PopulateField]) -> None:
        """Debug helper to check populate paths against available relationships."""
        available_rels = self.get_available_relationships()
        log.logs.info(f"Available relationships in {self.model.__name__}: {available_rels}")
        
        for pop_config in populate:
            path = pop_config.get("path")
            if path:
                if path in available_rels:
                    log.logs.info(f"✓ Populate path '{path}' is a valid relationship")
                else:
                    log.logs.warning(f"✗ Populate path '{path}' is NOT a valid relationship")
                    log.logs.warning(f"  Available relationships: {available_rels}")


    def _filter_populated_fields(self, result: Any, populate: List[PopulateField]) -> Any:
        """
        FIXED: Filter fields in populated relationships based on the fields specification.
        """
        if not result or not populate:
            return result

        # Handle both single results and lists
        results = result if isinstance(result, list) else [result]

        for item in results:
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
                    continue

                # Instead of creating new objects, modify existing ones
                self._apply_field_filtering_to_object(related_obj, fields)

                # Handle second layer
                if second_layer:
                    self._process_second_layer(related_obj, second_layer)

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
                # Get all available columns
                model_class = single_obj.__class__
                all_columns = set(model_class.__table__.columns.keys())

                # Parse field specifications
                exclude_fields = [field[1:] for field in fields if field.startswith("-")]
                include_fields = [field for field in fields if not field.startswith("-")]

                # Validate no mixing
                if exclude_fields and include_fields:
                    log.logs.warning("Mixed include/exclude fields. Using include mode.")
                    exclude_fields = []

                # Determine which fields to remove
                if exclude_fields:
                    # Remove specified fields
                    fields_to_remove = set(exclude_fields) & all_columns
                else:
                    # Keep only specified fields
                    fields_to_remove = all_columns - set(include_fields)

                # Instead of deleting attributes (which can cause issues),
                # set them to None or use a different approach
                for field_name in fields_to_remove:
                    if hasattr(single_obj, field_name):
                        try:
                            # Try to set to None instead of deleting
                            setattr(single_obj, field_name, None)
                        except (AttributeError, TypeError):
                            # If we can't set to None, try to delete
                            try:
                                delattr(single_obj, field_name)
                            except (AttributeError, TypeError):
                                # If we can't delete either, skip
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


    # Alternative: Use a serialization approach
    def _filter_populated_fields_serialization_approach(
        self, result: Any, populate: List[PopulateField]
    ) -> Any:
        """
        Alternative approach using serialization/dictionary conversion
        """
        if not result or not populate:
            return result

        # Convert to dict, filter, then convert back
        # This approach is more reliable but potentially slower

        def obj_to_dict(obj):
            """Convert SQLAlchemy object to dict"""
            if obj is None:
                return {}

            if isinstance(obj, list):
                return [obj_to_dict(item) for item in obj]

            # Get all column values
            result_dict = {}
            for column in obj.__table__.columns:
                result_dict[column.name] = getattr(obj, column.name, None)

            # Add relationship data
            for rel_name in obj.__mapper__.relationships.keys():
                if hasattr(obj, rel_name):
                    rel_value = getattr(obj, rel_name)
                    if rel_value is not None:
                        result_dict[rel_name] = obj_to_dict(rel_value)

            return result_dict

        # Convert result to dictionaries for easier manipulation
        results = result if isinstance(result, list) else [result]
        dict_results = [obj_to_dict(item) for item in results]

        # Apply filtering to the dictionaries
        for item_dict in dict_results:
            for pop_config in populate:
                path = pop_config.get("path")
                fields = pop_config.get("fields")

                if not path or not isinstance(item_dict, dict) or path not in item_dict or not fields:
                    continue

                related_data = item_dict.get(path)
                if related_data is None:
                    continue

                # Apply field filtering to the dictionary
                self._filter_dict_fields(related_data, fields)

        # For now, return the original objects since converting back is complex
        # You might want to implement a dict-to-object converter if needed
        return result


    def _filter_dict_fields(self, data: Any, fields: List[str]) -> None:
        """Filter fields in dictionary data"""
        if data is None:
            return

        data_items = data if isinstance(data, list) else [data]

        for item in data_items:
            if not isinstance(item, dict):
                continue

            # Parse field specifications
            exclude_fields = [field[1:] for field in fields if field.startswith("-")]
            include_fields = [field for field in fields if not field.startswith("-")]

            if exclude_fields and include_fields:
                exclude_fields = []

            if exclude_fields:
                # Remove excluded fields
                for field in exclude_fields:
                    item.pop(field, None)
            else:
                # Keep only included fields
                all_keys = list(item.keys())
                for key in all_keys:
                    if key not in include_fields:
                        item.pop(key, None)

    def _convert_to_dict_with_relationships(self, obj: Any, populate: List[PopulateField]) -> Dict[str, Any]:
        """
        Convert SQLAlchemy object to dictionary including populated relationships.
        """
        if obj is None:
            return {}
            
        # Convert to basic dict first
        if hasattr(obj, 'to_dict'):
            data = obj.to_dict()
            
            # Now add the actual populated relationship objects (not just IDs)
            for pop_config in populate:
                path = pop_config.get("path")
                log.logs.info(f"Processing populate path: {path}")
                
                # Directly access the relationship if it exists
                if path and hasattr(obj, path):
                    related_obj = getattr(obj, path)
                    log.logs.info(f"Related object for {path}: {related_obj}")
                    log.logs.info(f"Type of related object: {type(related_obj)}")
                    log.logs.info(f"Has to_dict method: {hasattr(related_obj, 'to_dict')}")
                    
                    if related_obj is not None:
                        if isinstance(related_obj, list):
                            # Handle collections
                            relationship_name = path.split('__')[-1] if '__' in path else path
                            data[relationship_name] = []
                            for item in related_obj:
                                if hasattr(item, 'to_dict'):
                                    data[relationship_name].append(item.to_dict())
                                else:
                                    data[relationship_name].append(str(item.id))
                        else:
                            # Handle single relationships
                            if hasattr(related_obj, 'to_dict'):
                                # Extract the relationship name from the path (e.g., "inventory__store" -> "store")
                                # Split by double underscore and take the last part
                                relationship_name = path.split('__')[-1] if '__' in path else path
                                data[relationship_name] = related_obj.to_dict()
                                log.logs.info(f"Converted {path} to {relationship_name}: {data[relationship_name]}")
                            else:
                                relationship_name = path.split('__')[-1] if '__' in path else path
                                data[relationship_name] = str(related_obj.id)
                                log.logs.info(f"Using ID for {relationship_name}: {data[relationship_name]}")
        else:
            # Fallback: convert to dict manually
            data = {}
            for column in obj.__table__.columns:
                value = getattr(obj, column.name)
                if hasattr(value, 'isoformat'):  # Handle datetime objects
                    data[column.name] = value.isoformat()
                else:
                    data[column.name] = value
            
            # Add populated relationships for fallback case
            for pop_config in populate:
                path = pop_config.get("path")
                if path and hasattr(obj, path):
                    related_obj = getattr(obj, path)
                    if related_obj is not None:
                        if isinstance(related_obj, list):
                            data[path] = [str(item.id) for item in related_obj]
                        else:
                            data[path] = str(related_obj.id)
        
        log.logs.info(f"Final converted data keys: {list(data.keys())}")
        return data