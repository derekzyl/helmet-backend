from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.admin.services.platform_staff import PlatformStaffService
from app.core.admin.types.admin import (
    AssignPlatformRoleT,
    CreatePlatformRoleT,
    UpdatePlatformRoleT,
)
from app.core.auth.services.service_auth import check_permission, get_current_user

platform_staff_router = APIRouter(
    prefix="/admin",
    tags=["Platform Staff Management"],
    responses={
        200: {"description": "Success"},
        201: {"description": "Created"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"}
    }
)


@platform_staff_router.get(
    "/platform-staff",
    response_model=dict,
    summary="Get Platform Staff",
    description="""
    Get all platform staff members.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Returns:**
    - List of platform staff with their roles and permissions
    """,
    tags=["Platform Staff Management"]
)
async def get_platform_staff(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        # Check platform admin permission
        await check_permission("read", "platform_staff", "manage", current_user=current_user, db=db)
        
        # Get platform staff
        service = PlatformStaffService(db=db)
        staff = await service.get_platform_staff()
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform staff retrieved successfully",
            "data": [member.to_dict() for member in staff]
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.post(
    "/platform-staff",
    response_model=dict,
    summary="Create Platform Staff",
    description="""
    Create a new platform staff member.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - staff_data: Platform staff details
    
    **Returns:**
    - Created platform staff information
    """,
    tags=["Platform Staff Management"]
)
async def create_platform_staff(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    staff_data: dict = Body(...),
):
    try:
        # Check platform admin permission
        await check_permission("create", "platform_staff", "manage", current_user=current_user, db=db)
        
        # Create platform staff
        service = PlatformStaffService(db=db)
        staff = await service.create_platform_staff(
            staff_data=staff_data,
            created_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=201, content={
            "success": True,
            "message": "Platform staff created successfully",
            "data": staff.to_dict()
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.put(
    "/platform-staff/{staff_id}",
    response_model=dict,
    summary="Update Platform Staff",
    description="""
    Update platform staff member details.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - staff_id: Platform staff ID
    - staff_data: Updated staff details
    
    **Returns:**
    - Updated platform staff information
    """,
    tags=["Platform Staff Management"]
)
async def update_platform_staff(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    staff_id: Annotated[str, Path()],
    staff_data: dict = Body(...),
):
    try:
        # Check platform admin permission
        await check_permission("update", "platform_staff", "manage", current_user=current_user, db=db)
        
        # Update platform staff
        service = PlatformStaffService(db=db)
        staff = await service.update_platform_staff(
            staff_id=staff_id,
            staff_data=staff_data,
            updated_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform staff updated successfully",
            "data": staff.to_dict()
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.delete(
    "/platform-staff/{staff_id}",
    response_model=dict,
    summary="Delete Platform Staff",
    description="""
    Delete a platform staff member.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - staff_id: Platform staff ID
    
    **Returns:**
    - Success message
    """,
    tags=["Platform Staff Management"]
)
async def delete_platform_staff(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    staff_id: Annotated[str, Path()],
):
    try:
        # Check platform admin permission
        await check_permission("delete", "platform_staff", "manage", current_user=current_user, db=db)
        
        # Delete platform staff
        service = PlatformStaffService(db=db)
        await service.delete_platform_staff(
            staff_id=staff_id,
            deleted_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform staff deleted successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.get(
    "/platform-roles",
    response_model=dict,
    summary="Get Platform Roles",
    description="""
    Get all platform roles.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Returns:**
    - List of platform roles with their permissions
    """,
    tags=["Platform Staff Management"]
)
async def get_platform_roles(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        # Check platform admin permission
        await check_permission("read", "platform_roles", "manage", current_user=current_user, db=db)
        
        # Get platform roles
        service = PlatformStaffService(db=db)
        roles = await service.get_platform_roles()
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform roles retrieved successfully",
            "data": [role.to_dict() for role in roles]
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.post(
    "/platform-roles",
    response_model=dict,
    summary="Create Platform Role",
    description="""
    Create a new platform role.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - role_data: Platform role details
    
    **Returns:**
    - Created platform role information
    """,
    tags=["Platform Staff Management"]
)
async def create_platform_role(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role_data: CreatePlatformRoleT = Body(...),
):
    try:
        # Check platform admin permission
        await check_permission("create", "platform_roles", "manage", current_user=current_user, db=db)
        
        # Create platform role
        service = PlatformStaffService(db=db)
        role = await service.create_platform_role(
            role_data=role_data,
            created_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=201, content={
            "success": True,
            "message": "Platform role created successfully",
            "data": role.to_dict()
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.put(
    "/platform-roles/{role_id}",
    response_model=dict,
    summary="Update Platform Role",
    description="""
    Update platform role details.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - role_id: Platform role ID
    - role_data: Updated role details
    
    **Returns:**
    - Updated platform role information
    """,
    tags=["Platform Staff Management"]
)
async def update_platform_role(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role_id: Annotated[str, Path()],
    role_data: UpdatePlatformRoleT = Body(...),
):
    try:
        # Check platform admin permission
        await check_permission("update", "platform_roles", "manage", current_user=current_user, db=db)
        
        # Update platform role
        service = PlatformStaffService(db=db)
        role = await service.update_platform_role(
            role_id=role_id,
            role_data=role_data,
            updated_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform role updated successfully",
            "data": role.to_dict()
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.delete(
    "/platform-roles/{role_id}",
    response_model=dict,
    summary="Delete Platform Role",
    description="""
    Delete a platform role.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - role_id: Platform role ID
    
    **Returns:**
    - Success message
    """,
    tags=["Platform Staff Management"]
)
async def delete_platform_role(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role_id: Annotated[str, Path()],
):
    try:
        # Check platform admin permission
        await check_permission("delete", "platform_roles", "manage", current_user=current_user, db=db)
        
        # Delete platform role
        service = PlatformStaffService(db=db)
        await service.delete_platform_role(
            role_id=role_id,
            deleted_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform role deleted successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.post(
    "/platform-staff/{staff_id}/assign-role",
    response_model=dict,
    summary="Assign Platform Role to Staff",
    description="""
    Assign a platform role to a staff member.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - staff_id: Platform staff ID
    - assignment_data: Role assignment details
    
    **Returns:**
    - Success message
    """,
    tags=["Platform Staff Management"]
)
async def assign_platform_role_to_staff(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    staff_id: Annotated[str, Path()],
    assignment_data: AssignPlatformRoleT = Body(...),
):
    try:
        # Check platform admin permission
        await check_permission("update", "platform_staff", "manage", current_user=current_user, db=db)
        
        # Assign platform role
        service = PlatformStaffService(db=db)
        await service.assign_platform_role_to_staff(
            staff_id=staff_id,
            role_id=assignment_data["role_id"],
            assigned_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform role assigned successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.get(
    "/platform-permissions",
    response_model=dict,
    summary="Get Platform Permissions",
    description="""
    Get all platform permissions.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Returns:**
    - List of all platform permissions
    """,
    tags=["Platform Staff Management"]
)
async def get_platform_permissions(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        # Check platform admin permission
        await check_permission("read", "platform_permissions", "manage", current_user=current_user, db=db)
        
        # Get platform permissions
        service = PlatformStaffService(db=db)
        permissions = await service.get_platform_permissions()
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform permissions retrieved successfully",
            "data": [perm.to_dict() for perm in permissions]
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.get(
    "/platform-roles/{role_id}/permissions",
    response_model=dict,
    summary="Get Platform Role Permissions",
    description="""
    Get permissions for a specific platform role.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - role_id: Platform role ID
    
    **Returns:**
    - List of permissions for the platform role
    """,
    tags=["Platform Staff Management"]
)
async def get_platform_role_permissions(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role_id: Annotated[str, Path()],
):
    try:
        # Check platform admin permission
        await check_permission("read", "platform_roles", "manage", current_user=current_user, db=db)
        
        # Get platform role permissions
        service = PlatformStaffService(db=db)
        permissions = await service.get_platform_role_permissions(role_id=role_id)
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Platform role permissions retrieved successfully",
            "data": [perm.to_dict() for perm in permissions]
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


@platform_staff_router.post(
    "/platform-roles/{role_id}/permissions",
    response_model=dict,
    summary="Assign Permissions to Platform Role",
    description="""
    Assign permissions to a platform role.
    
    **Access Level:** ADMIN (Platform Admin)
    
    **Parameters:**
    - role_id: Platform role ID
    - permission_data: Permission assignment details
    
    **Returns:**
    - Success message
    """,
    tags=["Platform Staff Management"]
)
async def assign_permissions_to_platform_role(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    role_id: Annotated[str, Path()],
    permission_data: dict = Body(...),
):
    try:
        # Check platform admin permission
        await check_permission("update", "platform_roles", "manage", current_user=current_user, db=db)
        
        # Assign permissions to platform role
        service = PlatformStaffService(db=db)
        await service.assign_permissions_to_platform_role(
            role_id=role_id,
            permission_ids=permission_data["permission_ids"],
            assigned_by_id=current_user['id']
        )
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "Permissions assigned to platform role successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        ) 