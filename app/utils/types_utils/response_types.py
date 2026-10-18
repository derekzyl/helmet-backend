from typing import Any, Optional, TypedDict


# The above class is a type hint for a dictionary that specifies the structure of the dictionary.
class ResponseT(TypedDict):
    message: str
    data: dict[str, Any]
    success_status: bool


class ResponseMessageT(TypedDict, total=False):
    message: str
    data: dict[str, Any]
    error: dict[str, Any]
    success: bool
