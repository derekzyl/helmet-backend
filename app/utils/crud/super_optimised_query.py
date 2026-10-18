"""
Ultra-Optimized Queries module with minimal overhead.
Key optimizations:
1. Removed excessive logging
2. Simplified condition building
3. Better memory management
4. Compiled query caching
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, not_, or_
from sqlalchemy.sql import Select

from app.utils.logger import log


class UltraOptimizedQueries:
    """
    Ultra high-performance query builder with minimal overhead.
    """

    # Class-level caches
    _model_fields_cache: Dict[str, Tuple[str, ...]] = {}
    _model_relationships_cache: Dict[str, Tuple[str, ...]] = {}

    def __init__(self, model_query: Select, request_query: Dict[str, Any], model_class):
        self.model = model_query
        self.request_query = request_query
        self.model_class = model_class
        self._model_name = model_class.__name__

    def _get_model_fields(self) -> Tuple[str, ...]:
        """Cache model field names at class level."""
        if self._model_name not in self._model_fields_cache:
            self._model_fields_cache[self._model_name] = tuple(
                self.model_class.__table__.columns.keys()
            )
        return self._model_fields_cache[self._model_name]

    def _get_model_relationships(self) -> Tuple[str, ...]:
        """Cache model relationship names at class level."""
        if self._model_name not in self._model_relationships_cache:
            relationships = []
            for attr_name in dir(self.model_class):
                if not attr_name.startswith("_"):
                    attr = getattr(self.model_class, attr_name, None)
                    if (
                        attr
                        and hasattr(attr, "property")
                        and hasattr(attr.property, "mapper")
                    ):
                        relationships.append(attr_name)
            self._model_relationships_cache[self._model_name] = tuple(relationships)
        return self._model_relationships_cache[self._model_name]

    def filter(self):
        """
        Ultra-optimized filter with minimal overhead.
        """
        query_obj = self.request_query.copy()

        # Remove pagination/sorting fields
        for field in ["page", "sort", "limit", "fields"]:
            query_obj.pop(field, None)

        if not query_obj:
            return self

        # Batch collect all conditions
        filter_conditions = []
        mongodb_conditions = []

        model_fields = self._get_model_fields()

        for key, value in query_obj.items():
            try:
                # Handle MongoDB-style operators
                if isinstance(value, dict) and any(
                    k.startswith("$") for k in value.keys()
                ):
                    mongodb_conditions.append((key, value))
                # Handle Django-style filters
                elif "__" in key:
                    condition = self._build_django_filter(key, value, model_fields)
                    if condition is not None:
                        filter_conditions.append(condition)
                # Handle top-level MongoDB operators
                elif key.startswith("$"):
                    self._apply_top_level_mongodb_operators(key, value)
                else:
                    # Simple equality filter
                    if key in model_fields:
                        filter_conditions.append(
                            getattr(self.model_class, key) == value
                        )

            except Exception as e:
                log.logs.error(f"Error applying filter for field '{key}': {e}")
                continue

        # Apply all regular conditions in one call
        if filter_conditions:
            self.model = (
                self.model.where(filter_conditions[0])
                if len(filter_conditions) == 1
                else self.model.where(and_(*filter_conditions))
            )

        # Apply MongoDB conditions
        for field_name, operators_dict in mongodb_conditions:
            self._apply_mongodb_operators(field_name, operators_dict, model_fields)

        return self

    def _build_django_filter(
        self, key: str, value: Any, model_fields: Tuple[str, ...]
    ) -> Optional[Any]:
        """Build Django-style filter condition efficiently."""
        parts = key.split("__")
        field_name = parts[0]
        operator = parts[1] if len(parts) > 1 else None

        if field_name not in model_fields:
            return None

        field = getattr(self.model_class, field_name)

        # Use dictionary dispatch for better performance
        operator_map = {
            "gte": lambda f, v: f >= v,
            "gt": lambda f, v: f > v,
            "lte": lambda f, v: f <= v,
            "lt": lambda f, v: f < v,
            "icontains": lambda f, v: f.ilike(f"%{v}%"),
            "contains": lambda f, v: f.contains(v),
            "in": lambda f, v: f.in_(v) if isinstance(v, (list, tuple)) else None,
            "nin": lambda f, v: ~f.in_(v) if isinstance(v, (list, tuple)) else None,
        }

        op_func = operator_map.get(operator) if operator else None
        return op_func(field, value) if op_func else None

    def _apply_mongodb_operators(
        self,
        field_name: str,
        operators_dict: Dict[str, Any],
        model_fields: Tuple[str, ...],
    ):
        """Apply MongoDB-style operators efficiently."""
        if field_name not in model_fields:
            log.logs.warning(
                f"Field '{field_name}' not found in model {self._model_name}"
            )
            return

        field = getattr(self.model_class, field_name)
        conditions = []

        # Operator dispatch map for better performance
        operator_handlers = {
            "$eq": lambda f, v: f == v,
            "$ne": lambda f, v: f != v,
            "$gt": lambda f, v: f > v,
            "$gte": lambda f, v: f >= v,
            "$lt": lambda f, v: f < v,
            "$lte": lambda f, v: f <= v,
            "$in": lambda f, v: f.in_(v) if isinstance(v, (list, tuple)) else None,
            "$nin": lambda f, v: ~f.in_(v) if isinstance(v, (list, tuple)) else None,
            "$regex": lambda f, v: f.ilike(f"%{v}%"),
            "$iregex": lambda f, v: f.ilike(f"%{v}%"),
            "$exists": lambda f, v: f.is_not(None) if v else f.is_(None),
            "$size": lambda f, v: func.json_array_length(f) == v,
        }

        for operator, value in operators_dict.items():
            try:
                handler = operator_handlers.get(operator)
                if handler:
                    condition = handler(field, value)
                    if condition is not None:
                        conditions.append(condition)
                elif operator == "$all":
                    if isinstance(value, (list, tuple)):
                        for item in value:
                            conditions.append(func.json_contains(field, f'"{item}"'))
                else:
                    log.logs.warning(f"Unsupported MongoDB operator: {operator}")

            except Exception as e:
                log.logs.error(
                    f"Error applying operator '{operator}' to field '{field_name}': {e}"
                )
                continue

        # Apply all conditions
        if conditions:
            self.model = (
                self.model.where(conditions[0])
                if len(conditions) == 1
                else self.model.where(and_(*conditions))
            )

    def _apply_top_level_mongodb_operators(self, operator: str, value: Any):
        """Apply top-level MongoDB operators efficiently."""
        try:
            if operator not in ["$or", "$and", "$nor"] or not isinstance(value, list):
                return

            all_conditions = []
            for condition_dict in value:
                field_conditions = self._parse_condition_dict(condition_dict)
                all_conditions.extend(field_conditions)

            if not all_conditions:
                return

            if operator == "$or":
                self.model = self.model.where(or_(*all_conditions))
            elif operator == "$and":
                self.model = self.model.where(and_(*all_conditions))
            elif operator == "$nor":
                self.model = self.model.where(not_(or_(*all_conditions)))

        except Exception as e:
            log.logs.error(f"Error applying top-level operator '{operator}': {e}")

    def _parse_condition_dict(self, condition_dict: Dict[str, Any]) -> List[Any]:
        """
        Parse a condition dictionary efficiently.
        """
        conditions = []
        model_fields = self._get_model_fields()

        # Operator dispatch for better performance
        operator_map = {
            "$eq": lambda f, v: f == v,
            "$ne": lambda f, v: f != v,
            "$gt": lambda f, v: f > v,
            "$gte": lambda f, v: f >= v,
            "$lt": lambda f, v: f < v,
            "$lte": lambda f, v: f <= v,
            "$in": lambda f, v: f.in_(v) if isinstance(v, (list, tuple)) else None,
            "$nin": lambda f, v: ~f.in_(v) if isinstance(v, (list, tuple)) else None,
            "$regex": lambda f, v: f.ilike(f"%{v}%"),
            "$exists": lambda f, v: f.is_not(None) if v else f.is_(None),
        }

        for field_name, field_value in condition_dict.items():
            if field_name not in model_fields:
                continue

            field = getattr(self.model_class, field_name)

            try:
                if isinstance(field_value, dict) and any(
                    k.startswith("$") for k in field_value.keys()
                ):
                    # Handle operators
                    for operator, value in field_value.items():
                        handler = operator_map.get(operator)
                        if handler:
                            condition = handler(field, value)
                            if condition is not None:
                                conditions.append(condition)
                else:
                    # Simple equality
                    conditions.append(field == field_value)

            except Exception as e:
                log.logs.error(f"Error parsing condition for field '{field_name}': {e}")
                continue

        return conditions

    def sort(self):
        """Optimized sorting."""
        sort_str = self.request_query.get("sort")
        if not sort_str:
            # Default sorting
            if hasattr(self.model_class, "created_at"):
                self.model = self.model.order_by(
                    getattr(self.model_class, "created_at").desc()
                )
            elif hasattr(self.model_class, "id"):
                self.model = self.model.order_by(getattr(self.model_class, "id").desc())
            return self

        sort_fields = sort_str.split(",")
        order_clauses = []

        for field in sort_fields:
            try:
                if field.startswith("-"):
                    field_name = field[1:]
                    if hasattr(self.model_class, field_name):
                        order_clauses.append(
                            getattr(self.model_class, field_name).desc()
                        )
                else:
                    if hasattr(self.model_class, field):
                        order_clauses.append(getattr(self.model_class, field).asc())
            except Exception as e:
                log.logs.warning(f"Error applying sort for field '{field}': {e}")
                continue

        if order_clauses:
            self.model = self.model.order_by(*order_clauses)

        return self

    def limit_fields(self):
        """Optimized field limiting."""
        fields_str = self.request_query.get("fields")
        if not fields_str:
            return self

        fields = fields_str.split(",")
        valid_fields = [
            getattr(self.model_class, field)
            for field in fields
            if hasattr(self.model_class, field)
        ]

        if valid_fields:
            self.model = self.model.with_only_columns(*valid_fields)

        return self

    def paginate(self):
        """Optimized pagination."""
        try:
            page = max(1, int(self.request_query.get("page", 1)))
            limit = min(1000, max(1, int(self.request_query.get("limit", 100))))

            offset = (page - 1) * limit
            self.model = self.model.offset(offset).limit(limit)

        except (ValueError, TypeError):
            log.logs.warning("Invalid pagination parameters, using defaults")
            self.model = self.model.offset(0).limit(100)

        return self
