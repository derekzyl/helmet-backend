from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.auth.services.service_auth import get_current_user
from app.core.roles.services.roles import RolePermissionService
from app.utils.crud.types_crud import response_message

role_permission_router = APIRouter()


class CreateRoleRequest(BaseModel):
    name: str
    description: Optional[str] = None


class AssignRoleToUserRequest(BaseModel):
    user_id: str


class CheckPermissionRequest(BaseModel):
    user_id: str
    permission_name: str
    resource: str
    action: str


@role_permission_router.post("/roles", response_model=dict)
async def create_role(
    data: CreateRoleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    service = RolePermissionService(db=db)
    role = await service.create_role(name=data.name, description=data.description)
    return JSONResponse(status_code=201, content=role.to_dict())


@role_permission_router.get("/users/{user_id}/roles", response_model=dict)
async def get_user_roles(
    user_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    service = RolePermissionService(db=db)
    roles = await service.get_user_roles(user_id=user_id)
    return JSONResponse(
        status_code=200,
        content=response_message(
            data=[r.to_dict() for r in roles],
            success_status=True,
            message="Roles retrieved",
        ),
    )


@role_permission_router.post("/roles/{role_id}/users", response_model=dict)
async def assign_role_to_user(
    role_id: Annotated[str, Path()],
    data: AssignRoleToUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    service = RolePermissionService(db=db)
    assignment = await service.assign_role(user_id=data.user_id, role_id=role_id)
    return JSONResponse(
        status_code=201,
        content=response_message(
            data=assignment.to_dict(),
            success_status=True,
            message="Role assigned",
        ),
    )


@role_permission_router.post("/check-permission", response_model=dict)
async def check_permission_endpoint(
    data: CheckPermissionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    service = RolePermissionService(db=db)
    allowed = await service.check_user_permission(
        user_id=data.user_id,
        permission_name=data.permission_name,
        resource=data.resource,
        action=data.action,
    )
    return JSONResponse(
        status_code=200,
        content=response_message(
            data={"allowed": allowed},
            success_status=True,
            message="Permission checked",
        ),
    )


@role_permission_router.get("/users/{user_id}/permissions", response_model=dict)
async def get_user_permissions(
    user_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    service = RolePermissionService(db=db)
    permissions = await service.get_user_permissions(user_id=user_id)
    return JSONResponse(
        status_code=200,
        content=response_message(
            data=[p.to_dict() for p in permissions],
            success_status=True,
            message="Permissions retrieved",
        ),
    )
