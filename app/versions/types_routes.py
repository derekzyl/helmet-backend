from enum import Enum
from typing import NotRequired, TypedDict

from fastapi import APIRouter


class AccessLevel(str, Enum):
    """Access levels for API routes"""

    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ADMIN = "admin"
    SYSTEM = "system"


class RouterData(TypedDict):
    path: str
    tags: list[str | Enum]
    api_route: APIRouter
    access_level: AccessLevel
    description: str
    responses: NotRequired[dict[int | str, dict[str, str]] | None]
