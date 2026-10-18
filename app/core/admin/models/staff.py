import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String, Table
from sqlalchemy.orm import relationship

# Use the project's BaseModelClass
from app.config.database.db import BaseModelClass


class AccessLevelEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    support = "support"
    analyst = "analyst"

# Association table: platform_staff_roles
platform_staff_roles = Table(
    "PLATFORM_STAFF_ROLES",
    BaseModelClass.metadata,
    Column("staff_id", String(255), ForeignKey("PLATFORM_STAFF.id"), primary_key=True),
    Column("role_id", String(255), ForeignKey("PLATFORM_ROLES.id"), primary_key=True),
)

# Association table: platform_role_permissions
platform_role_permissions = Table(
    "PLATFORM_ROLE_PERMISSIONS",
    BaseModelClass.metadata,
    Column("role_id", String(255), ForeignKey("PLATFORM_ROLES.id"), primary_key=True),
    Column("permission_id", String(255), ForeignKey("PLATFORM_PERMISSIONS.id"), primary_key=True),
)

class PlatformStaffModel(BaseModelClass):
    __tablename__ = "PLATFORM_STAFF"
    user_id = Column(String(255), nullable=False, unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    position = Column(String, nullable=True)
    department = Column(String, nullable=True)
    access_level = Column(Enum(AccessLevelEnum), nullable=False, default=AccessLevelEnum.support)
    is_active = Column(Boolean, default=True)

    roles = relationship(
        "PlatformRoleModel",
        secondary=platform_staff_roles,
        back_populates="staff_members"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "position": self.position,
            "department": self.department,
            "access_level": self.access_level.value if self.access_level is not None else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "role_name": self.roles[0].name if self.roles else None
        }

class PlatformRoleModel(BaseModelClass):
    __tablename__ = "PLATFORM_ROLES"
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    access_level = Column(Enum(AccessLevelEnum), nullable=False, default=AccessLevelEnum.manager)
    department = Column(String, nullable=True)
    is_system_role = Column(Boolean, default=False)

    staff_members = relationship(
        "PlatformStaffModel",
        secondary=platform_staff_roles,
        back_populates="roles"
    )
    permissions = relationship(
        "PlatformPermissionModel",
        secondary=platform_role_permissions,
        back_populates="roles"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "access_level": self.access_level.value if self.access_level is not None else None,
            "department": self.department,
            "is_system_role": self.is_system_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "permissions": [perm.to_dict() for perm in self.permissions]
        }

class PlatformPermissionModel(BaseModelClass):
    __tablename__ = "PLATFORM_PERMISSIONS"
    name = Column(String, nullable=False, unique=True)
    resource = Column(String, nullable=False)
    action = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)

    roles = relationship(
        "PlatformRoleModel",
        secondary=platform_role_permissions,
        back_populates="permissions"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "resource": self.resource,
            "action": self.action,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
