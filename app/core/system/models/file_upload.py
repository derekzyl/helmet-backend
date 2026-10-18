from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database.db import BaseModelClass

if TYPE_CHECKING:
    from app.core.users.models.model_user import UserModel


class FileUploadModel(BaseModelClass):
    """File uploads and attachments"""

    __tablename__ = "FILE_UPLOAD"

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # prescription, profile_picture, document
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # document, image, user
    entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Foreign Keys
    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("USER.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    file_upload__uploaded_by: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[uploaded_by_id] )

    def __repr__(self):
        return f"<FileUploadModel(id={self.id}, original_filename='{self.original_filename}', uploaded_by_id='{self.uploaded_by_id}')>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "file_type": self.file_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "uploaded_by_id": str(self.uploaded_by_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by_id": str(self.created_by_id) if hasattr(self, 'created_by_id') and self.created_by_id else None,
            "updated_by_id": str(self.updated_by_id) if hasattr(self, 'updated_by_id') and self.updated_by_id else None
        }