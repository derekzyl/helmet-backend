from dataclasses import dataclass
from typing import Optional, TypedDict


@dataclass
class Permission:
    id: int
    name: str
    guard_name: str
    created_at: str  # Consider using a proper datetime type if available in your Python environment
    updated_at: str  # Consider using a proper datetime type if available in your Python environment




class PermissionT(TypedDict):
    id: int
    name: str
    guard_name: str
    created_at: str  # Consider using a proper datetime type if available in your Python environment
    updated_at: str  # Consider using a proper datetime type if available in your Python environment




class SocialAuthStateT(TypedDict):
    state: str
    provider: str


class SocialCallbackT(TypedDict):
    code: str
    state: Optional[str]
    error: Optional[str]
    error_description: Optional[str]
