from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import relationship

from app.config.database.db import BaseModelClass, Mapped, mapped_column

if TYPE_CHECKING:
    from app.core.users.models.model_user import UserModel


class ProfileModel(BaseModelClass):
    __tablename__: str = "PROFILE"
    user_id: Mapped[str] = mapped_column(ForeignKey("USER.id", ondelete="CASCADE"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
  
    language:Mapped[str]= mapped_column(String(255), unique=True, nullable=True)
    country:Mapped[str]= mapped_column(String(255), nullable=True)
    region:Mapped[str]= mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)

    profile__user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="user__profile", foreign_keys=[user_id]
    )

    def __repr__(self):
        return f"<ProfileModel(id={self.id}, user_id='{self.user_id}', first_name='{self.first_name}', last_name='{self.last_name}')>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "language": self.language,
            "country": self.country,
            "region": self.region,
            "phone": self.phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by_id": str(self.created_by_id) if hasattr(self, 'created_by_id') and self.created_by_id else None,
            "updated_by_id": str(self.updated_by_id) if hasattr(self, 'updated_by_id') and self.updated_by_id else None
        }