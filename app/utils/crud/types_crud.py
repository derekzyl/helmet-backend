
from typing import Any, Optional, TypedDict


class ResponseMessage(TypedDict):
    success_status: bool
    message: str
    error: Any
    data: Any
    doc_length: Optional[int]


def response_message(
    success_status: bool,
    message: str,
    error: Any | None = None,
    data: Any | None = None,
    doc_length: int | None = None,
) -> ResponseMessage:
    if success_status:
        return {
            "success_status": success_status,
            "message": message,
            "data": data,
            "doc_length": doc_length,
            "error": None,
        }
    else:
        return {
            "success_status": success_status,
            "message": message,
            "error": str(error) if error else None,
            "doc_length": doc_length,
            "data": None,
        }
