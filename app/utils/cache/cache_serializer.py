"""
Robust Cache Serializer for Mixed Data Types

Handles serialization/deserialization of:
- Pure model classes (with to_dict method)
- Pure dictionaries
- Mixed response formats: {message: str, data: dict|model_class}
- Lists containing models or dicts
- Nested structures

This ensures Redis caching works reliably regardless of data format.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from app.utils.logger.log import logs


class CacheSerializer:
    """
    Intelligent serializer for caching that handles model classes and dicts.
    """

    @staticmethod
    def _is_model_instance(obj: Any) -> bool:
        """Check if object is a SQLAlchemy model instance"""
        return (
            hasattr(obj, "__table__")  # SQLAlchemy models
            or hasattr(obj, "to_dict")  # Models with to_dict method
            or hasattr(obj, "model_dump")  # Pydantic models
            or (
                hasattr(obj, "__class__") and hasattr(obj.__class__, "__tablename__")
            )  # Alternative SQLAlchemy check
        )

    @staticmethod
    def _convert_value(value: Any) -> Any:
        """Convert a single value to JSON-serializable format"""
        if value is None:
            return None

        # Handle datetime objects
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        # Handle Decimal
        if isinstance(value, Decimal):
            return float(value)

        # Handle UUID
        if isinstance(value, UUID):
            return str(value)

        # Handle bytes
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")

        # Handle sets
        if isinstance(value, set):
            return list(value)

        # Basic types
        if isinstance(value, (str, int, float, bool)):
            return value

        # Lists
        if isinstance(value, list):
            return [CacheSerializer._convert_value(item) for item in value]

        # Dicts
        if isinstance(value, dict):
            return {k: CacheSerializer._convert_value(v) for k, v in value.items()}

        # Model instances
        if CacheSerializer._is_model_instance(value):
            return CacheSerializer._model_to_dict(value)

        # Fallback: convert to string
        try:
            return str(value)
        except Exception:
            return None

    @staticmethod
    def _model_to_dict(model: Any) -> Dict[str, Any]:
        """Convert a model instance to dictionary"""
        # Try Pydantic's model_dump
        if hasattr(model, "model_dump"):
            try:
                return model.model_dump()
            except Exception as e:
                logs.debug(f"model_dump failed: {e}")

        # Try custom to_dict method
        if hasattr(model, "to_dict"):
            try:
                result = model.to_dict()
                if isinstance(result, dict):
                    return result
            except Exception as e:
                logs.debug(f"to_dict failed: {e}")

        # Try SQLAlchemy's __dict__
        if hasattr(model, "__dict__"):
            try:
                result = {}
                for key, value in model.__dict__.items():
                    # Skip SQLAlchemy internal attributes
                    if key.startswith("_"):
                        continue
                    result[key] = CacheSerializer._convert_value(value)
                return result
            except Exception as e:
                logs.debug(f"__dict__ conversion failed: {e}")

        # Last resort: try to get table columns
        if hasattr(model, "__table__"):
            try:
                result = {}
                for column in model.__table__.columns:
                    value = getattr(model, column.name, None)
                    result[column.name] = CacheSerializer._convert_value(value)
                return result
            except Exception as e:
                logs.debug(f"Table column conversion failed: {e}")

        # Ultimate fallback
        return {"_error": "Could not serialize model", "_type": str(type(model))}

    @staticmethod
    def serialize(data: Any) -> str:
        """
        Serialize any data type to JSON string for Redis storage.

        Handles:
        - Model classes
        - Dictionaries
        - Mixed formats like {message: str, data: model_class|dict}
        - Lists of any of the above
        """
        try:
            # Handle None
            if data is None:
                return json.dumps(None)

            # Handle pure model instance
            if CacheSerializer._is_model_instance(data):
                serializable = CacheSerializer._model_to_dict(data)
                return json.dumps(serializable)

            # Handle dictionary (including response_message format)
            if isinstance(data, dict):
                serializable = {}
                for key, value in data.items():
                    if key == "data" and value is not None:
                        # Special handling for 'data' field
                        if isinstance(value, list):
                            # List of items (could be models or dicts)
                            serializable[key] = [
                                CacheSerializer._model_to_dict(item)
                                if CacheSerializer._is_model_instance(item)
                                else CacheSerializer._convert_value(item)
                                for item in value
                            ]
                        elif CacheSerializer._is_model_instance(value):
                            # Single model instance
                            serializable[key] = CacheSerializer._model_to_dict(value)
                        else:
                            # Already a dict or basic type
                            serializable[key] = CacheSerializer._convert_value(value)
                    else:
                        # Other fields
                        serializable[key] = CacheSerializer._convert_value(value)

                return json.dumps(serializable)

            # Handle list
            if isinstance(data, list):
                serializable = [
                    CacheSerializer._model_to_dict(item)
                    if CacheSerializer._is_model_instance(item)
                    else CacheSerializer._convert_value(item)
                    for item in data
                ]
                return json.dumps(serializable)

            # Handle basic types
            if isinstance(data, (str, int, float, bool)):
                return json.dumps(data)

            # Fallback: try to convert and serialize
            converted = CacheSerializer._convert_value(data)
            return json.dumps(converted)

        except Exception as e:
            logs.error(f"Serialization error: {e}")
            # Return a safe error representation
            return json.dumps({
                "_error": "Serialization failed",
                "_exception": str(e),
                "_type": str(type(data)),
            })

    @staticmethod
    def deserialize(json_str: str) -> Any:
        """
        Deserialize JSON string back to Python objects.

        Note: Model classes are returned as dictionaries since we can't
        reconstruct the original class without additional metadata.
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logs.error(f"Deserialization error: {e}")
            return None
        except Exception as e:
            logs.error(f"Unexpected deserialization error: {e}")
            return None


# Global serializer instance
cache_serializer = CacheSerializer()


# Convenience functions
def serialize_for_cache(data: Any) -> str:
    """Serialize data for Redis caching"""
    return cache_serializer.serialize(data)


def deserialize_from_cache(json_str: str) -> Any:
    """Deserialize data from Redis cache"""
    return cache_serializer.deserialize(json_str)


# Testing utility
def test_serialization():
    """Test serialization with various data types"""

    test_cases = [
        # Basic types
        None,
        "string",
        123,
        45.67,
        True,
        # Lists
        [1, 2, 3],
        ["a", "b", "c"],
        # Dicts
        {"key": "value"},
        {"nested": {"key": "value"}},
        # Response message format with dict data
        {
            "success_status": True,
            "message": "Data fetched successfully",
            "data": {"id": "123", "name": "Test"},
            "doc_length": 1,
            "error": None,
        },
        # Response message format with list data
        {
            "success_status": True,
            "message": "Data fetched successfully",
            "data": [{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}],
            "doc_length": 2,
            "error": None,
        },
    ]

    logs.info("🧪 Testing cache serialization...")

    for i, test_data in enumerate(test_cases):
        try:
            # Serialize
            serialized = serialize_for_cache(test_data)

            # Deserialize
            deserialized = deserialize_from_cache(serialized)

            # Compare
            if test_data == deserialized:
                logs.info(f"✅ Test case {i + 1}: PASSED")
            else:
                logs.warning(f"⚠️ Test case {i + 1}: Data mismatch")
                logs.debug(f"   Original: {test_data}")
                logs.debug(f"   Deserialized: {deserialized}")
        except Exception as e:
            logs.error(f"❌ Test case {i + 1}: FAILED - {e}")

    logs.info("🧪 Testing complete!")


if __name__ == "__main__":
    test_serialization()
