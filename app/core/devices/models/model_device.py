from datetime import datetime, timezone
from typing import Optional
import secrets

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database.db import BaseModelClass


class DeviceModel(BaseModelClass):
    __tablename__: str = "DEVICES"

    serial_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "HELMET" or "IGNITION"
    hardware_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    firmware_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_token: Mapped[str] = mapped_column(String(255), unique=True, default=lambda: f"tok_{secrets.token_hex(24)}")
    
    # State tracking
    status: Mapped[str] = mapped_column(String(50), default="UNPAIRED")  # UNPAIRED, ONLINE, OFFLINE
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_battery_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Pairing: binds a helmet to an ignition unit
    paired_device_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("DEVICES.id", ondelete="SET NULL"), nullable=True)
    pairing_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 256-bit hex PSK for HMAC
    
    # Ownership
    owner_id: Mapped[Optional[str]] = mapped_column(String(255), ForeignKey("USER.id", ondelete="SET NULL"), nullable=True)

    # Relationship to configuration
    config: Mapped[Optional["DeviceConfigModel"]] = relationship(
        "DeviceConfigModel", back_populates="device", cascade="all, delete-orphan", uselist=False, lazy="joined"
    )


class DeviceConfigModel(BaseModelClass):
    __tablename__: str = "DEVICE_CONFIGS"

    device_id: Mapped[str] = mapped_column(String(255), ForeignKey("DEVICES.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    alcohol_threshold_mg_l: Mapped[float] = mapped_column(Float, default=0.05)
    collision_accel_g: Mapped[float] = mapped_column(Float, default=3.5)
    collision_tilt_deg: Mapped[float] = mapped_column(Float, default=60.0)
    heartbeat_timeout_ms: Mapped[int] = mapped_column(Integer, default=2000)
    telemetry_interval_sec: Mapped[int] = mapped_column(Integer, default=5)
    emergency_countdown_sec: Mapped[int] = mapped_column(Integer, default=20)
    cutoff_on_accident: Mapped[bool] = mapped_column(Boolean, default=False)  # Safety cutoff policy

    device: Mapped["DeviceModel"] = relationship("DeviceModel", back_populates="config")
