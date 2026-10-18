from typing import Any, Dict, List

from sqlalchemy import and_, func, not_, or_

from app.utils.logger import log


class Queries:
    def __init__(self, model_query, request_query: dict[str, Any], model_class):
        self.model = model_query
        self.request_query = request_query
        self.model_class = model_class

    def filter(self):
        query_obj = self.request_query.copy()
        excluded_fields = ["page", "sort", "limit", "fields"]
        for field in excluded_fields:
            query_obj.pop(field, None)

        for key, value in query_obj.items():
            try:
                # Handle MongoDB-style operators in field values
                if isinstance(value, dict) and any(
                    k.startswith("$") for k in value.keys()
                ):
                    self._apply_mongodb_operators(key, value)
                # Handle traditional Django-style filters
                elif key.endswith("__gte"):
                    field_name = key[:-5]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name) >= value
                        )
                elif key.endswith("__gt"):
                    field_name = key[:-4]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name) > value
                        )
                elif key.endswith("__lte"):
                    field_name = key[:-5]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name) <= value
                        )
                elif key.endswith("__lt"):
                    field_name = key[:-4]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name) < value
                        )
                elif key.endswith("__icontains"):
                    field_name = key[:-11]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name).icontains(value)
                        )
                elif key.endswith("__contains"):
                    field_name = key[:-10]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name).contains(value)
                        )
                elif key.endswith("__in"):
                    field_name = key[:-4]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            getattr(self.model_class, field_name).in_(value)
                        )
                elif key.endswith("__nin"):
                    field_name = key[:-5]
                    if hasattr(self.model_class, field_name):
                        self.model = self.model.where(
                            ~getattr(self.model_class, field_name).in_(value)
                        )
                # Handle top-level MongoDB operators like $or, $and, $nor
                elif key.startswith("$"):
                    log.logs.info(
                        f"Applying top-level MongoDB operator: {key}, {value}"
                    )
                    self._apply_top_level_mongodb_operators(key, value)
                else:
                    # Simple equality filter
                    if hasattr(self.model_class, key):
                        self.model = self.model.where(
                            getattr(self.model_class, key) == value
                        )
            except AttributeError:
                log.logs.warning(
                    f"Field '{key}' not found in model {self.model_class.__name__}"
                )
                continue
            except Exception as e:
                log.logs.error(f"Error applying filter for field '{key}': {e}")
                continue

        return self

    def _apply_mongodb_operators(self, field_name: str, operators_dict: Dict[str, Any]):
        """
        Apply MongoDB-style operators to a specific field.

        Supported operators:
        - $eq: Equal to
        - $ne: Not equal to
        - $gt: Greater than
        - $gte: Greater than or equal to
        - $lt: Less than
        - $lte: Less than or equal to
        - $in: In array
        - $nin: Not in array
        - $regex: Regular expression match
        - $exists: Field exists (not null)
        - $size: Array size (for JSON fields)
        - $all: All values in array (for JSON fields)
        """
        if not hasattr(self.model_class, field_name):
            log.logs.warning(
                f"Field '{field_name}' not found in model {self.model_class.__name__}"
            )
            return

        field = getattr(self.model_class, field_name)
        conditions = []

        for operator, value in operators_dict.items():
            try:
                if operator == "$eq":
                    conditions.append(field == value)
                elif operator == "$ne":
                    conditions.append(field != value)
                elif operator == "$gt":
                    conditions.append(field > value)
                elif operator == "$gte":
                    conditions.append(field >= value)
                elif operator == "$lt":
                    conditions.append(field < value)
                elif operator == "$lte":
                    conditions.append(field <= value)
                elif operator == "$in":
                    if isinstance(value, (list, tuple)):
                        conditions.append(field.in_(value))
                    else:
                        log.logs.warning(
                            f"$in operator requires a list/array, got {type(value)}"
                        )
                elif operator == "$nin":
                    if isinstance(value, (list, tuple)):
                        conditions.append(~field.in_(value))
                    else:
                        log.logs.warning(
                            f"$nin operator requires a list/array, got {type(value)}"
                        )
                elif operator == "$regex":
                    # Use ILIKE for case-insensitive regex-like matching
                    conditions.append(field.ilike(f"%{value}%"))
                elif operator == "$iregex":
                    # Case-insensitive regex
                    conditions.append(field.ilike(f"%{value}%"))
                elif operator == "$exists":
                    if value:
                        conditions.append(field.is_not(None))
                    else:
                        conditions.append(field.is_(None))
                elif operator == "$size":
                    # For JSON array fields - check array size
                    conditions.append(func.json_array_length(field) == value)
                elif operator == "$all":
                    # For JSON array fields - check if all values exist
                    if isinstance(value, (list, tuple)):
                        for item in value:
                            conditions.append(func.json_contains(field, f'"{item}"'))
                    else:
                        log.logs.warning(
                            f"$all operator requires a list/array, got {type(value)}"
                        )
                elif operator == "$elemMatch":
                    # For JSON array fields with object elements
                    log.logs.warning(
                        "$elemMatch operator not fully implemented for SQL"
                    )
                elif operator == "$type":
                    # Type checking - basic implementation
                    if value == "string":
                        conditions.append(field.is_not(None))
                    elif value == "number":
                        conditions.append(field.is_not(None))
                    # Add more type checks as needed
                else:
                    log.logs.warning(f"Unsupported MongoDB operator: {operator}")

            except Exception as e:
                log.logs.error(
                    f"Error applying operator '{operator}' to field '{field_name}': {e}"
                )
                continue

        # Apply all conditions for this field
        if conditions:
            if len(conditions) == 1:
                self.model = self.model.where(conditions[0])
            else:
                # Multiple conditions for same field are ANDed together
                self.model = self.model.where(and_(*conditions))

    def _apply_top_level_mongodb_operators(self, operator: str, value: Any):
        """
        Apply top-level MongoDB operators like $or, $and, $nor.

        Example usage:
        {
            "$or": [
                {"name": "John"},
                {"age": {"$gt": 25}}
            ]
        }
        """
        try:
            if operator == "$or":
                if isinstance(value, list):
                    or_conditions = []
                    for condition_dict in value:
                        field_conditions = self._parse_condition_dict(condition_dict)
                        if field_conditions:
                            or_conditions.extend(field_conditions)

                    if or_conditions:
                        self.model = self.model.where(or_(*or_conditions))
                else:
                    log.logs.warning("$or operator requires an array of conditions")

            elif operator == "$and":
                if isinstance(value, list):
                    and_conditions = []
                    for condition_dict in value:
                        field_conditions = self._parse_condition_dict(condition_dict)
                        if field_conditions:
                            and_conditions.extend(field_conditions)

                    if and_conditions:
                        self.model = self.model.where(and_(*and_conditions))
                else:
                    log.logs.warning("$and operator requires an array of conditions")

            elif operator == "$nor":
                if isinstance(value, list):
                    nor_conditions = []
                    for condition_dict in value:
                        field_conditions = self._parse_condition_dict(condition_dict)
                        if field_conditions:
                            nor_conditions.extend(field_conditions)

                    if nor_conditions:
                        # NOR is equivalent to NOT (condition1 OR condition2 OR ...)
                        self.model = self.model.where(not_(or_(*nor_conditions)))
                else:
                    log.logs.warning("$nor operator requires an array of conditions")

            elif operator == "$not":
                # $not operator for negating conditions
                if isinstance(value, dict):
                    not_conditions = self._parse_condition_dict(value)
                    if not_conditions:
                        if len(not_conditions) == 1:
                            self.model = self.model.where(not_(not_conditions[0]))
                        else:
                            self.model = self.model.where(not_(and_(*not_conditions)))
                else:
                    log.logs.warning("$not operator requires a condition object")

            else:
                log.logs.warning(f"Unsupported top-level MongoDB operator: {operator}")

        except Exception as e:
            log.logs.error(f"Error applying top-level operator '{operator}': {e}")

    def _parse_condition_dict(self, condition_dict: Dict[str, Any]) -> List[Any]:
        """
        Parse a condition dictionary and return SQLAlchemy conditions.

        Args:
            condition_dict: Dictionary like {"name": "John", "age": {"$gt": 25}}

        Returns:
            List of SQLAlchemy condition objects
        """
        conditions = []

        for field_name, field_value in condition_dict.items():
            if not hasattr(self.model_class, field_name):
                log.logs.warning(
                    f"Field '{field_name}' not found in model {self.model_class.__name__}"
                )
                continue

            field = getattr(self.model_class, field_name)

            try:
                if isinstance(field_value, dict) and any(
                    k.startswith("$") for k in field_value.keys()
                ):
                    # Handle operators like {"age": {"$gt": 25}}
                    for operator, value in field_value.items():
                        if operator == "$eq":
                            conditions.append(field == value)
                        elif operator == "$ne":
                            conditions.append(field != value)
                        elif operator == "$gt":
                            conditions.append(field > value)
                        elif operator == "$gte":
                            conditions.append(field >= value)
                        elif operator == "$lt":
                            conditions.append(field < value)
                        elif operator == "$lte":
                            conditions.append(field <= value)
                        elif operator == "$in":
                            if isinstance(value, (list, tuple)):
                                conditions.append(field.in_(value))
                        elif operator == "$nin":
                            if isinstance(value, (list, tuple)):
                                conditions.append(~field.in_(value))
                        elif operator == "$regex":
                            conditions.append(field.ilike(f"%{value}%"))
                        elif operator == "$exists":
                            if value:
                                conditions.append(field.is_not(None))
                            else:
                                conditions.append(field.is_(None))
                        # Add more operators as needed
                else:
                    # Simple equality: {"name": "John"}
                    conditions.append(field == field_value)

            except Exception as e:
                log.logs.error(f"Error parsing condition for field '{field_name}': {e}")
                continue

        return conditions

    def sort(self):
        if "sort" in self.request_query:
            sort_by = self.request_query["sort"].split(",")
            for field in sort_by:
                try:
                    if field.startswith("-"):
                        field_name = field[1:]
                        if hasattr(self.model_class, field_name):
                            self.model = self.model.order_by(
                                getattr(self.model_class, field_name).desc()
                            )
                    else:
                        if hasattr(self.model_class, field):
                            self.model = self.model.order_by(
                                getattr(self.model_class, field).asc()
                            )
                except AttributeError:
                    log.logs.warning(
                        f"Sort field '{field}' not found in model {self.model_class.__name__}"
                    )
                    continue
        else:
            # Default sort by created_at if it exists, otherwise by id
            if hasattr(self.model_class, "created_at"):
                self.model = self.model.order_by(
                    getattr(self.model_class, "created_at").desc()
                )
            elif hasattr(self.model_class, "id"):
                self.model = self.model.order_by(getattr(self.model_class, "id").desc())

        return self

    def limit_fields(self):
        if "fields" in self.request_query:
            fields = self.request_query["fields"].split(",")
            valid_fields = []
            for field in fields:
                if hasattr(self.model_class, field):
                    valid_fields.append(getattr(self.model_class, field))
                else:
                    log.logs.warning(
                        f"Field '{field}' not found in model {self.model_class.__name__}"
                    )

            if valid_fields:
                self.model = self.model.with_only_columns(*valid_fields)
        return self

    def paginate(self):
        try:
            page = max(1, int(self.request_query.get("page", 1)))
            limit = min(
                1000, max(1, int(self.request_query.get("limit", 100)))
            )  # Cap at 1000
            offset = (page - 1) * limit

            self.model = self.model.offset(offset).limit(limit)
        except (ValueError, TypeError):
            log.logs.warning("Invalid pagination parameters, using defaults")
            self.model = self.model.offset(0).limit(100)

        return self
