from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database.db import BaseModelClass

if TYPE_CHECKING:
    from app.core.users.models.model_user import UserModel


class   TokenModel(BaseModelClass):
    __tablename__="TOKEN"
    
    type:Mapped[str] = mapped_column(String, nullable=False )
    expires:Mapped[str] = mapped_column(String, nullable=False)
    blacklisted:Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token:Mapped[str] = mapped_column(String, nullable=False)

    #foreign keys
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    
    
    #relationships
    token__user:Mapped["UserModel"] = relationship(
        back_populates="user__tokens",
        foreign_keys=[user_id]
    )
    
    def __repr__(self):
        return f"<TokenModel(id={self.id}, user_id='{self.user_id}', type='{self.type}')>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "type": self.type,
            "expires": self.expires,
            "blacklisted": self.blacklisted,
            "token": self.token,
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by_id": str(self.created_by_id) if hasattr(self, 'created_by_id') and self.created_by_id else None,
            "updated_by_id": str(self.updated_by_id) if hasattr(self, 'updated_by_id') and self.updated_by_id else None
        }
    