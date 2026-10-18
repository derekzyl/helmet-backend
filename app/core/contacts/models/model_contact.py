from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database.db import BaseModelClass


class EmergencyContactModel(BaseModelClass):
    __tablename__: str = "EMERGENCY_CONTACTS"

    user_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("USER.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("DEVICES.id", ondelete="CASCADE"), nullable=True, index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    relationship: Mapped[str] = mapped_column(String(100), default="Next of Kin")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_sms: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_call: Mapped[bool] = mapped_column(Boolean, default=False)
