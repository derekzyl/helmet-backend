from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database.db import BaseModelClass

if TYPE_CHECKING:
    from app.core.auth.services.middleware_auth import UserModel

    


class RoleModel(BaseModelClass):
    """Role model for role-based access control"""

    __tablename__: str = "ROLE"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    role__user_roles: Mapped[List["UserRoleModel"]] = relationship(
        "UserRoleModel", back_populates="user_role__role", cascade="all, delete-orphan"
    )
    role__role_permissions: Mapped[List["RolePermissionModel"]] = relationship(
        "RolePermissionModel",
        back_populates="role_permission__role",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert role model to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class AttributeModel(BaseModelClass):
    """Attribute model for storing attribute definitions"""

    __tablename__: str = "ATTRIBUTE"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    attribute_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    attribute__attribute_values: Mapped[List["AttributeValueModel"]] = relationship(
        "AttributeValueModel",
        back_populates="attribute_value__attribute",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert attribute model to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "attribute_type": self.attribute_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class AttributeValueModel(BaseModelClass):
    """Attribute value model for storing specific attribute values"""

    __tablename__: str = "ATTRIBUTE_VALUE"

    attribute_id: Mapped[str] = mapped_column(
        ForeignKey("ATTRIBUTE.id"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    attribute_value__attribute: Mapped["AttributeModel"] = relationship(
        "AttributeModel", back_populates="attribute__attribute_values"
    )
    attribute_value__user_attributes: Mapped[List["UserAttributeModel"]] = relationship(
        "UserAttributeModel",
        back_populates="user_attribute__attribute_value",
        cascade="all, delete-orphan",
    )
    attribute_value__attribute_permissions: Mapped[List["AttributePermissionModel"]] = (
        relationship(
            "AttributePermissionModel",
            back_populates="attribute_permission__attribute_value",
            cascade="all, delete-orphan",
        )
    )

    def to_dict(self) -> dict:
        """Convert attribute value model to dictionary"""
        return {
            "id": str(self.id),
            "attribute_id": str(self.attribute_id),
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class UserRoleModel(BaseModelClass):
    """Many-to-many relationship between User and Role"""

    __tablename__: str = "USER_ROLE"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(ForeignKey("ROLE.id"), nullable=False)

    # Relationships
    user_role__user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="user__user_roles", foreign_keys=[user_id]
    )
    user_role__role: Mapped["RoleModel"] = relationship(
        "RoleModel", back_populates="role__user_roles", foreign_keys=[role_id]
    )

    def to_dict(self) -> dict:
        """Convert user role model to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "role_id": str(self.role_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class UserAttributeModel(BaseModelClass):
    """Many-to-many relationship between User and AttributeValue"""

    __tablename__: str = "USER_ATTRIBUTE"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    attribute_value_id: Mapped[str] = mapped_column(
        ForeignKey("ATTRIBUTE_VALUE.id"), nullable=False
    )

    # Relationships
    user_attribute__user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="user__user_attributes", foreign_keys=[user_id]
    )
    user_attribute__attribute_value: Mapped["AttributeValueModel"] = relationship(
        "AttributeValueModel", back_populates="attribute_value__user_attributes", foreign_keys=[attribute_value_id]
    )

    def to_dict(self) -> dict:
        """Convert user attribute model to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "attribute_value_id": str(self.attribute_value_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class PermissionModel(BaseModelClass):
    """Permission model for defining system permissions"""

    __tablename__: str = "PERMISSION"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    permission_level: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Relationships
    permission__role_permissions: Mapped[List["RolePermissionModel"]] = relationship(
        "RolePermissionModel",
        back_populates="role_permission__permission",
        cascade="all, delete-orphan",
    )
    permission__attribute_permissions: Mapped[List["AttributePermissionModel"]] = (
        relationship(
            "AttributePermissionModel",
            back_populates="attribute_permission__permission",
            cascade="all, delete-orphan",
        )
    )
    permission__policy_rule_permissions: Mapped[List["PolicyRulePermissionModel"]] = (
        relationship(
            "PolicyRulePermissionModel",
            back_populates="policy_rule_permission__permission",
            cascade="all, delete-orphan",
        )
    )

    def to_dict(self) -> dict:
        """Convert permission model to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "resource": self.resource,
            "action": self.action,
            "description": self.description,
            "permission_level": self.permission_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class RolePermissionModel(BaseModelClass):
    """Many-to-many relationship between Role and Permission"""

    __tablename__: str = "ROLE_PERMISSION"

    role_id: Mapped[str] = mapped_column(ForeignKey("ROLE.id"), nullable=False)
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("PERMISSION.id"), nullable=False
    )

    # Relationships
    role_permission__role: Mapped["RoleModel"] = relationship(
        "RoleModel", back_populates="role__role_permissions"
    )
    role_permission__permission: Mapped["PermissionModel"] = relationship(
        "PermissionModel", back_populates="permission__role_permissions"
    )

    def to_dict(self) -> dict:
        """Convert role permission model to dictionary"""
        return {
            "id": str(self.id),
            "role_id": str(self.role_id),
            "permission_id": str(self.permission_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class AttributePermissionModel(BaseModelClass):
    """Many-to-many relationship between AttributeValue and Permission"""

    __tablename__: str = "ATTRIBUTE_PERMISSION"

    attribute_value_id: Mapped[str] = mapped_column(
        ForeignKey("ATTRIBUTE_VALUE.id"), nullable=False
    )
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("PERMISSION.id"), nullable=False
    )

    # Relationships
    attribute_permission__attribute_value: Mapped["AttributeValueModel"] = relationship(
        "AttributeValueModel", back_populates="attribute_value__attribute_permissions"
    )
    attribute_permission__permission: Mapped["PermissionModel"] = relationship(
        "PermissionModel", back_populates="permission__attribute_permissions"
    )

    def to_dict(self) -> dict:
        """Convert attribute permission model to dictionary"""
        return {
            "id": str(self.id),
            "attribute_value_id": str(self.attribute_value_id),
            "permission_id": str(self.permission_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class PolicyRuleModel(BaseModelClass):
    """Policy rule model for complex condition-based access control"""

    __tablename__: str = "POLICY_RULE"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    condition: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON or query expression
    effect: Mapped[str] = mapped_column(String(10), nullable=False)  # ALLOW or DENY

    # Relationships
    policy_rule__policy_rule_permissions: Mapped[List["PolicyRulePermissionModel"]] = (
        relationship(
            "PolicyRulePermissionModel",
            back_populates="policy_rule_permission__policy_rule",
            cascade="all, delete-orphan",
        )
    )

    def to_dict(self) -> dict:
        """Convert policy rule model to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "effect": self.effect,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class PolicyRulePermissionModel(BaseModelClass):
    """Many-to-many relationship between PolicyRule and Permission"""

    __tablename__: str = "POLICY_RULE_PERMISSION"

    policy_rule_id: Mapped[str] = mapped_column(
        ForeignKey("POLICY_RULE.id"), nullable=False
    )
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("PERMISSION.id"), nullable=False
    )

    # Relationships
    policy_rule_permission__policy_rule: Mapped["PolicyRuleModel"] = relationship(
        "PolicyRuleModel", back_populates="policy_rule__policy_rule_permissions"
    )
    policy_rule_permission__permission: Mapped["PermissionModel"] = relationship(
        "PermissionModel", back_populates="permission__policy_rule_permissions"
    )

    def to_dict(self) -> dict:
        """Convert policy rule permission model to dictionary"""
        return {
            "id": str(self.id),
            "policy_rule_id": str(self.policy_rule_id),
            "permission_id": str(self.permission_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
