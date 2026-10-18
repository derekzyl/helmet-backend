from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database.db import Base, TimeStamp
from app.utils.uuid_generator import id_gen


class SafetyEventModel(Base, TimeStamp):
    __tablename__: str = "SAFETY_EVENTS"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=id_gen, unique=True)
    device_id: Mapped[str] = mapped_column(String(255), ForeignKey("DEVICES.id", ondelete="CASCADE"), index=True, nullable=False)
    
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    # Types: "COLLISION", "ALCOHOL_LOCKOUT", "HELMET_REMOVED", "LINK_LOST", "SOS_TRIGGERED", "MANUAL_OVERRIDE"
    
    severity: Mapped[str] = mapped_column(String(20), default="WARNING")
    # Severity: "INFO", "WARNING", "CRITICAL"

    message: Mapped[str] = mapped_column(String(500), nullable=False)
    
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Acknowledgement status
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
