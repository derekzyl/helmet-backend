from typing import TypedDict

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database.db import BaseModelClass
from app.core.auth.models.model_token import TokenModel
from app.core.roles.models import (
    AttributeValueModel,
    PermissionModel,
    RoleModel,
    UserAttributeModel,
    UserRoleModel,
)
from app.core.users.models.profile import ProfileModel


class UserModel(BaseModelClass):
    __tablename__: str = "USER"

    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_type: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str] = mapped_column(String(255), nullable=True)
    allow_login: Mapped[bool] = mapped_column(Boolean, default=True)
    privacy_policy_accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    privacy_policy_accepted_at: Mapped[str] = mapped_column(String(255), nullable=True)

    user__profile: Mapped["ProfileModel"] = relationship(
        "ProfileModel",
        back_populates="profile__user",
        cascade="all, delete-orphan",
        foreign_keys=[ProfileModel.user_id],
    )
    user__user_roles: Mapped[list["UserRoleModel"]] = relationship(
        "UserRoleModel",
        back_populates="user_role__user",
        cascade="all, delete-orphan",
        foreign_keys=[UserRoleModel.user_id],
    )
    user__tokens: Mapped[list["TokenModel"]] = relationship(
        "TokenModel",
        back_populates="token__user",
        cascade="all, delete-orphan",
        foreign_keys=[TokenModel.user_id],
    )
    user__user_attributes: Mapped[list["UserAttributeModel"]] = relationship(
        "UserAttributeModel",
        back_populates="user_attribute__user",
        cascade="all, delete-orphan",
        foreign_keys=[UserAttributeModel.user_id],
    )

    @property
    def roles(self) -> list["RoleModel"]:
        return [user_role.user_role__role for user_role in self.user__user_roles]

    @property
    def attributes(self) -> list["AttributeValueModel"]:
        return [
            user_attr.user_attribute__attribute_value
            for user_attr in self.user__user_attributes
        ]

    @property
    def permissions(self) -> list["PermissionModel"]:
        permissions: list[PermissionModel] = []
        for user_role in self.user__user_roles:
            for role_permission in user_role.user_role__role.role__role_permissions:
                permissions.append(role_permission.role_permission__permission)
        for user_attr in self.user__user_attributes:
            for attr_permission in (
                user_attr.user_attribute__attribute_value.attribute_value__attribute_permissions
            ):
                permissions.append(attr_permission.attribute_permission__permission)
        return list(set(permissions))

    def __repr__(self):
        return f"<UserModel(id={self.id}, username='{self.username}', email='{self.email}')>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "user_type": self.user_type,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "password": self.password,
            "email_verified": self.email_verified,
            "name": self.name,
            "gender": self.gender,
            "allow_login": self.allow_login,
            "privacy_policy_accepted": self.privacy_policy_accepted,
            "privacy_policy_accepted_at": self.privacy_policy_accepted_at,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by_id": str(self.created_by_id)
            if hasattr(self, "created_by_id") and self.created_by_id
            else None,
            "updated_by_id": str(self.updated_by_id)
            if hasattr(self, "updated_by_id") and self.updated_by_id
            else None,
        }


class UserModelType(TypedDict):
    id: str
    username: str
    email: str
    user_type: str
    first_name: str
    last_name: str
    password: str
    email_verified: bool
    name: str
    gender: str
    allow_login: bool
    privacy_policy_accepted: bool
    privacy_policy_accepted_at: str
    created_at: str
    updated_at: str
    created_by_id: str
    updated_by_id: str
