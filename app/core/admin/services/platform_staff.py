from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin.models.staff import (
    PlatformPermissionModel,
    PlatformRoleModel,
    PlatformStaffModel,
)
from app.utils.crud.types_crud import response_message


class PlatformStaffService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== PLATFORM STAFF MANAGEMENT ==========

    async def get_platform_staff(self) -> List[PlatformStaffModel]:
        """Get all platform staff members"""
        try:
            query = select(PlatformStaffModel).options(
                selectinload(PlatformStaffModel.roles)
            )
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform staff"
                )
            )

    async def get_platform_staff_by_id(self, staff_id: str) -> Optional[PlatformStaffModel]:
        """Get platform staff member by ID"""
        try:
            query = select(PlatformStaffModel).where(
                PlatformStaffModel.id == staff_id
            ).options(selectinload(PlatformStaffModel.roles))
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform staff member"
                )
            )

    async def create_platform_staff(self, staff_data: dict, created_by_id: str) -> PlatformStaffModel:
        """Create a new platform staff member"""
        try:
            # Check if user already exists as platform staff
            existing_staff = await self.get_platform_staff_by_user_id(staff_data["user_id"])
            if existing_staff:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="User already exists as platform staff",
                        success_status=False,
                        message="User is already registered as platform staff"
                    )
                )

            # Create new platform staff member
            platform_staff = PlatformStaffModel(
                user_id=staff_data["user_id"],
                first_name=staff_data["first_name"],
                last_name=staff_data["last_name"],
                email=staff_data["email"],
                position=staff_data.get("position"),
                department=staff_data.get("department"),
                access_level=staff_data.get("access_level", "support"),
                is_active=staff_data.get("is_active", True)
            )

            self.db.add(platform_staff)
            await self.db.commit()
            await self.db.refresh(platform_staff)

            # Assign role if provided
            if staff_data.get("role_id"):
                await self.assign_platform_role_to_staff(
                    str(platform_staff.id),
                    staff_data["role_id"],
                    created_by_id
                )

            return platform_staff
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to create platform staff member"
                )
            )

    async def update_platform_staff(self, staff_id: str, staff_data: dict, updated_by_id: str) -> PlatformStaffModel:
        """Update platform staff member"""
        try:
            staff = await self.get_platform_staff_by_id(staff_id)
            if not staff:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform staff not found",
                        success_status=False,
                        message="Platform staff member not found"
                    )
                )

            # Update fields
            for field, value in staff_data.items():
                if hasattr(staff, field):
                    setattr(staff, field, value)

            await self.db.commit()
            await self.db.refresh(staff)
            return staff
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to update platform staff member"
                )
            )

    async def delete_platform_staff(self, staff_id: str, deleted_by_id: str) -> bool:
        """Delete platform staff member"""
        try:
            staff = await self.get_platform_staff_by_id(staff_id)
            if not staff:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform staff not found",
                        success_status=False,
                        message="Platform staff member not found"
                    )
                )

            await self.db.delete(staff)
            await self.db.commit()
            return True
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to delete platform staff member"
                )
            )

    async def get_platform_staff_by_user_id(self, user_id: str) -> Optional[PlatformStaffModel]:
        """Get platform staff member by user ID"""
        try:
            query = select(PlatformStaffModel).where(
                PlatformStaffModel.user_id == user_id
            ).options(selectinload(PlatformStaffModel.roles))
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform staff member"
                )
            )

    # ========== PLATFORM ROLE MANAGEMENT ==========

    async def get_platform_roles(self) -> List[PlatformRoleModel]:
        """Get all platform roles"""
        try:
            query = select(PlatformRoleModel).options(
                selectinload(PlatformRoleModel.permissions),
                selectinload(PlatformRoleModel.staff_members)
            )
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform roles"
                )
            )

    async def get_platform_role_by_id(self, role_id: str) -> Optional[PlatformRoleModel]:
        """Get platform role by ID"""
        try:
            query = select(PlatformRoleModel).where(
                PlatformRoleModel.id == role_id
            ).options(
                selectinload(PlatformRoleModel.permissions),
                selectinload(PlatformRoleModel.staff_members)
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform role"
                )
            )

    async def create_platform_role(self, role_data, created_by_id: str) -> PlatformRoleModel:
        """Create a new platform role"""
        try:
            # Check if role name already exists
            existing_role = await self.get_platform_role_by_name(role_data["name"])
            if existing_role:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="Role name already exists",
                        success_status=False,
                        message="A role with this name already exists"
                    )
                )

            # Create new platform role
            platform_role = PlatformRoleModel(
                name=role_data["name"],
                description=role_data.get("description"),
                access_level=role_data.get("access_level", "manager"),
                department=role_data.get("department"),
                is_system_role=role_data.get("is_system_role", False)
            )

            self.db.add(platform_role)
            await self.db.commit()
            await self.db.refresh(platform_role)

            # Assign permissions if provided
            if role_data.get("permissions"):
                await self.assign_permissions_to_platform_role(
                    str(platform_role.id),
                    role_data["permissions"],
                    created_by_id
                )

            return platform_role
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to create platform role"
                )
            )

    async def update_platform_role(self, role_id: str, role_data, updated_by_id: str) -> PlatformRoleModel:
        """Update platform role"""
        try:
            role = await self.get_platform_role_by_id(role_id)
            if not role:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform role not found",
                        success_status=False,
                        message="Platform role not found"
                    )
                )

            # Check if role name already exists (if changing name)
            if role_data.get("name") and role_data["name"] != role.name:
                existing_role = await self.get_platform_role_by_name(role_data["name"])
                if existing_role:
                    raise HTTPException(
                        status_code=400,
                        detail=response_message(
                            error="Role name already exists",
                            success_status=False,
                            message="A role with this name already exists"
                        )
                    )

            # Update fields
            for field, value in role_data.items():
                if hasattr(role, field) and field != "permissions":
                    setattr(role, field, value)

            # Update permissions if provided
            if role_data.get("permissions") is not None:
                await self.assign_permissions_to_platform_role(
                    role_id,
                    role_data["permissions"],
                    updated_by_id
                )

            await self.db.commit()
            await self.db.refresh(role)
            return role
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to update platform role"
                )
            )

    async def delete_platform_role(self, role_id: str, deleted_by_id: str) -> bool:
        """Delete platform role"""
        try:
            role = await self.get_platform_role_by_id(role_id)
            if not role:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform role not found",
                        success_status=False,
                        message="Platform role not found"
                    )
                )

            # Check if role is assigned to any staff
            if role.staff_members:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="Cannot delete role with assigned staff",
                        success_status=False,
                        message="Cannot delete role that is assigned to staff members"
                    )
                )

            await self.db.delete(role)
            await self.db.commit()
            return True
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to delete platform role"
                )
            )

    async def get_platform_role_by_name(self, name: str) -> Optional[PlatformRoleModel]:
        """Get platform role by name"""
        try:
            query = select(PlatformRoleModel).where(
                PlatformRoleModel.name == name
            ).options(
                selectinload(PlatformRoleModel.permissions),
                selectinload(PlatformRoleModel.staff_members)
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform role"
                )
            )

    # ========== PLATFORM PERMISSION MANAGEMENT ==========

    async def get_platform_permissions(self) -> List[PlatformPermissionModel]:
        """Get all platform permissions"""
        try:
            query = select(PlatformPermissionModel).options(
                selectinload(PlatformPermissionModel.roles)
            )
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform permissions"
                )
            )

    async def get_platform_permission_by_id(self, permission_id: str) -> Optional[PlatformPermissionModel]:
        """Get platform permission by ID"""
        try:
            query = select(PlatformPermissionModel).where(
                PlatformPermissionModel.id == permission_id
            ).options(selectinload(PlatformPermissionModel.roles))
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform permission"
                )
            )

    async def create_platform_permission(self, permission_data: dict, created_by_id: str) -> PlatformPermissionModel:
        """Create a new platform permission"""
        try:
            # Check if permission already exists
            existing_permission = await self.get_platform_permission_by_name(permission_data["name"])
            if existing_permission:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="Permission already exists",
                        success_status=False,
                        message="A permission with this name already exists"
                    )
                )

            # Create new platform permission
            platform_permission = PlatformPermissionModel(
                name=permission_data["name"],
                resource=permission_data["resource"],
                action=permission_data["action"],
                description=permission_data.get("description"),
                category=permission_data.get("category")
            )

            self.db.add(platform_permission)
            await self.db.commit()
            await self.db.refresh(platform_permission)
            return platform_permission
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to create platform permission"
                )
            )

    async def get_platform_permission_by_name(self, name: str) -> Optional[PlatformPermissionModel]:
        """Get platform permission by name"""
        try:
            query = select(PlatformPermissionModel).where(
                PlatformPermissionModel.name == name
            ).options(selectinload(PlatformPermissionModel.roles))
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform permission"
                )
            )

    # ========== ROLE ASSIGNMENT ==========

    async def assign_platform_role_to_staff(self, staff_id: str, role_id: str, assigned_by_id: str) -> bool:
        """Assign platform role to staff member"""
        try:
            # Get staff and role
            staff = await self.get_platform_staff_by_id(staff_id)
            role = await self.get_platform_role_by_id(role_id)

            if not staff:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform staff not found",
                        success_status=False,
                        message="Platform staff member not found"
                    )
                )

            if not role:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform role not found",
                        success_status=False,
                        message="Platform role not found"
                    )
                )

            # Clear existing roles and assign new role
            staff.roles = [role]
            await self.db.commit()
            return True
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to assign platform role to staff"
                )
            )

    async def assign_permissions_to_platform_role(self, role_id: str, permission_ids: List[str], assigned_by_id: str) -> bool:
        """Assign permissions to platform role"""
        try:
            # Get role
            role = await self.get_platform_role_by_id(role_id)
            if not role:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform role not found",
                        success_status=False,
                        message="Platform role not found"
                    )
                )

            # Get permissions
            permissions = []
            for permission_id in permission_ids:
                permission = await self.get_platform_permission_by_id(permission_id)
                if permission:
                    permissions.append(permission)

            # Assign permissions
            role.permissions = permissions
            await self.db.commit()
            return True
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to assign permissions to platform role"
                )
            )

    async def get_platform_role_permissions(self, role_id: str) -> List[PlatformPermissionModel]:
        """Get permissions for a specific platform role"""
        try:
            role = await self.get_platform_role_by_id(role_id)
            if not role:
                raise HTTPException(
                    status_code=404,
                    detail=response_message(
                        error="Platform role not found",
                        success_status=False,
                        message="Platform role not found"
                    )
                )
            return role.permissions
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to retrieve platform role permissions"
                )
            )

    # ========== PERMISSION CHECKING ==========

    async def check_platform_staff_permission(self, user_id: str, permission_name: str, resource: str, action: str) -> bool:
        """Check if platform staff member has specific permission"""
        try:
            # Get platform staff member
            staff = await self.get_platform_staff_by_user_id(user_id)
            if not staff:
                return False

            # Check permissions through roles
            for role in staff.roles:
                for permission in role.permissions:
                    if (permission.name == permission_name and 
                        permission.resource == resource and 
                        permission.action == action):
                        return True

            return False
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Failed to check platform staff permission"
                )
            ) 