from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles.models import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserRoleModel,
)
from app.utils.logger.log import logs


class RolePermissionService:
    """Minimal RBAC helpers for the starter template."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_roles(self, user_id: str) -> List[RoleModel]:
        result = await self.db.execute(
            select(RoleModel)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(UserRoleModel.user_id == user_id)
        )
        return list(result.scalars().all())

    async def assign_role(self, user_id: str, role_id: str) -> UserRoleModel:
        existing = await self.db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row

        assignment = UserRoleModel(user_id=user_id, role_id=role_id)
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def create_role(
        self, name: str, description: Optional[str] = None
    ) -> RoleModel:
        role = RoleModel(name=name, description=description)
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def check_user_permission(
        self,
        user_id: str,
        permission_name: str,
        resource: str,
        action: str,
    ) -> bool:
        query = (
            select(PermissionModel)
            .join(
                RolePermissionModel,
                PermissionModel.id == RolePermissionModel.permission_id,
            )
            .join(RoleModel, RolePermissionModel.role_id == RoleModel.id)
            .join(UserRoleModel, RoleModel.id == UserRoleModel.role_id)
            .where(
                UserRoleModel.user_id == user_id,
                PermissionModel.name == permission_name,
                PermissionModel.resource == resource,
                PermissionModel.action == action,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_user_permissions(self, user_id: str) -> List[PermissionModel]:
        query = (
            select(PermissionModel)
            .join(
                RolePermissionModel,
                PermissionModel.id == RolePermissionModel.permission_id,
            )
            .join(RoleModel, RolePermissionModel.role_id == RoleModel.id)
            .join(UserRoleModel, RoleModel.id == UserRoleModel.role_id)
            .where(UserRoleModel.user_id == user_id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def seed_permissions(self, permissions: list[dict]) -> int:
        """Create missing permissions from a flat catalog. Returns created count."""
        created = 0
        for item in permissions:
            existing = await self.db.execute(
                select(PermissionModel).where(
                    PermissionModel.name == item["name"],
                    PermissionModel.resource == item["resource"],
                    PermissionModel.action == item["action"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            self.db.add(
                PermissionModel(
                    name=item["name"],
                    resource=item["resource"],
                    action=item["action"],
                    description=item.get("description"),
                    permission_level=item.get("permission_level", "user"),
                )
            )
            created += 1
        if created:
            await self.db.commit()
            logs.info(f"Seeded {created} permissions")
        return created
