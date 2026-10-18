from typing import Any, Callable, Dict, Type, TypedDict, TypeVar

from pydantic import BaseModel, create_model


# The `PydanticUtil` class provides utility methods for working with Pydantic BaseModel classes, such
# as creating partial models, handling required fields, picking specific fields, and more.
class PydanticUtil:
    BaseModelType = type[BaseModel]
    Keys = TypeVar("Keys")
    Value = TypeVar("Value")
    Excluded = TypeVar("Excluded")
    Extracted = TypeVar("Extracted")
    Function = TypeVar("Function", bound=Callable)

    @staticmethod
    def partial_model(base_model: Type[BaseModel]) -> Type[BaseModel]:
        partial_fields = {f: (None, ...) for f in base_model.__annotations__.keys()}
        return create_model(
            base_model.__name__ + "Partial",
            field_definitions=partial_fields,
        )

    @staticmethod
    def required(obj: BaseModelType, keys: tuple[Keys, ...]) -> BaseModelType:
        missing_keys = [key for key in keys if key not in obj.__annotations__]

        if missing_keys:
            raise ValueError(
                f"Missing required keys: {', '.join(missing_keys.__str__())}"
            )
        return obj

    @staticmethod
    def readonly(obj: BaseModelType) -> BaseModelType:
        obj_dict = {key: obj.__annotations__[key] for key in obj.__annotations__}
        return create_model(
            obj.__name__ + "Readonly", __base__=BaseModel, field_definitions=obj_dict
        )

    @staticmethod
    def pick(obj: BaseModelType, keys: tuple[Keys, ...]) -> BaseModelType:
        picked_dict = {
            key: obj.__annotations__[key] for key in keys if key in obj.__annotations__ # type: ignore
        }
        return create_model(
            obj.__name__ + "Pick", __base__=BaseModel, field_definitions=picked_dict
        )

    @staticmethod
    def record(keys: tuple[Keys, ...], value: BaseModelType) -> BaseModelType:
        record_dict = {key: value for key in keys}
        return create_model(
            "RecordModel", __base__=BaseModel, field_definitions=record_dict
        )

    @staticmethod
    def omit(obj: BaseModelType, keys: tuple[Keys, ...]) -> BaseModelType:
        omitted_dict = {
            key: obj.__annotations__[key]
            for key in obj.__annotations__
            if key not in keys
        }
        return create_model(
            obj.__name__ + "Omit", __base__=BaseModel, field_definitions=omitted_dict
        )

    # Exclude<T, Excluded>
    @staticmethod
    def exclude(
        obj: type[BaseModel] | Excluded, excluded: Excluded
    ) -> type[BaseModel] | Excluded:
        if obj == excluded:
            raise ValueError(f"Excluded value {excluded} found")
        return obj

    # NonNullable<T>
    @staticmethod
    def non_nullable(obj: type[BaseModel] | None) -> type[BaseModel]:
        if obj is None:
            raise ValueError("Value is nullable")
        return obj

    # Extract<T, Extracted>
    @staticmethod
    def extract(obj: type[BaseModel] | Extracted, extracted: Extracted) -> Extracted:
        if obj != extracted:
            raise ValueError(f"Expected {extracted}, got {obj}")
        return extracted

    # Function types

    # Parameters<Function>


T = TypeVar("T", bound=TypeVar)


class TypeDict(TypedDict):
    pass


def pick(T: TypeDict, keys: list[str]) ->dict[str, Any]:
    new_dict = {key: T[key] for key in keys}
    return new_dict


# Awaited<T>
Awaited = TypeDict


# Object manipulation types
class ManipulatedObject(TypeDict):
    pass


# Partial<T>
def Partial(T: TypeDict) -> TypeDict:
    for key in T.keys():
        TypeDict.__annotations__[key] = Any
    return T


# Required<T>
def Required(T: TypeDict) -> TypeDict:
    for key in T.keys():
        if key not in TypeDict.__annotations__:
            TypeDict.__annotations__[key] = Any
    return T


# Readonly<T>
def Readonly(T: TypeDict) -> TypeDict:
    return T


# Record<Keys, Value>
def Record(keys: list, value: TypeDict) -> Dict[str, TypeDict]:
    return {k: value for k in keys}


# Omit<T, Keys>
def Omit(T: TypeDict, keys: list):
    omitted_keys = [key for key in T.keys() if key not in keys]
    return pick(T, omitted_keys)


# Union manipulation types
def Exclude(T: TypeDict, excluded: TypeDict) -> TypeDict:
    for key in excluded.keys():
        if key in T:
            del TypeDict.__annotations__[key]
    return T


# NonNullable<T>
NonNullable = TypeDict

# Extract<T, Extracted>
Extract = TypeDict

