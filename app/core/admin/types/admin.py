from typing import TypedDict, List

# Platform Role Management Types
class CreatePlatformRoleT(TypedDict):
    name: str
    description: str
    permissions: List[str]  # Permission IDs
    access_level: str
    department: str

class UpdatePlatformRoleT(TypedDict):
    name: str
    description: str
    permissions: List[str]  # Permission IDs
    access_level: str
    department: str

class AssignPlatformRoleT(TypedDict):
    role_id: str 