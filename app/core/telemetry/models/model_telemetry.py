from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database.db import Base, TimeStamp
from app.utils.uuid_generator import id_gen


class TelemetryModel(Base, TimeStamp):
    __tablename__: str = "TELEMETRY"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=id_gen, unique=True)
    device_id: Mapped[str] = mapped_column(String(255), ForeignKey("DEVICES.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Telemetry point timestamp (Unix timestamp or datetime)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # GPS Position & Dynamics
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speed_kmh: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    hdop: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    satellites: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    # Helmet Sensor Telemetry
    battery_pct: Mapped[int] = mapped_column(Integer, default=100)
    battery_mv: Mapped[int] = mapped_column(Integer, default=4000)
    alcohol_level_mg_l: Mapped[float] = mapped_column(Float, default=0.0)
    helmet_worn: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # System States
    ignition_state: Mapped[str] = mapped_column(String(50), default="LOCKED")  # LOCKED, UNLOCKED, RUNNING_LATCHED, FAULT
    link_state: Mapped[str] = mapped_column(String(50), default="CONNECTED")   # CONNECTED, DISCONNECTED, SOFTAP
    
    # Raw JSON payload for diagnostic logs
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
