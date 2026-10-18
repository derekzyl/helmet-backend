from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database.db import BaseModelClass


class SystemSettingModel(BaseModelClass):
    """Application settings (system-wide or scoped)."""

    __tablename__ = "SYSTEM_SETTING"

    setting_key: Mapped[str] = mapped_column(String(100), nullable=False)
    setting_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    setting_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_system_wide: Mapped[bool] = mapped_column(Boolean, default=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self):
        return (
            f"<SystemSettingModel(id={self.id}, "
            f"setting_key='{self.setting_key}', scope_id='{self.scope_id}')>"
        )

    def to_dict(self):
        return {
            "id": str(self.id),
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "setting_type": self.setting_type,
            "description": self.description,
            "is_system_wide": self.is_system_wide,
            "scope_id": self.scope_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by_id": str(self.created_by_id)
            if hasattr(self, "created_by_id") and self.created_by_id
            else None,
            "updated_by_id": str(self.updated_by_id)
            if hasattr(self, "updated_by_id") and self.updated_by_id
            else None,
        }
