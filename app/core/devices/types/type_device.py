from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    serial_number: str = Field(..., example="HLM-2026-0001")
    device_type: str = Field(..., example="HELMET", description="HELMET or IGNITION")
    hardware_version: str = Field(default="v1.0")
    firmware_version: str = Field(default="1.0.0")
    label: Optional[str] = Field(default=None, example="Main Rider Helmet")


class DevicePairRequest(BaseModel):
    helmet_device_id: str = Field(..., description="ID or serial of helmet unit")
    ignition_device_id: str = Field(..., description="ID or serial of ignition unit")


class DevicePairResponse(BaseModel):
    status: str = "PAIRED"
    helmet_device_id: str
    ignition_device_id: str
    pairing_secret: str = Field(..., description="256-bit PSK for local HMAC-SHA256 protocol")
    paired_at: datetime


class DeviceConfigUpdate(BaseModel):
    alcohol_threshold_mg_l: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    collision_accel_g: Optional[float] = Field(default=None, ge=1.5, le=16.0)
    collision_tilt_deg: Optional[float] = Field(default=None, ge=20.0, le=90.0)
    heartbeat_timeout_ms: Optional[int] = Field(default=None, ge=500, le=10000)
    telemetry_interval_sec: Optional[int] = Field(default=None, ge=1, le=60)
    emergency_countdown_sec: Optional[int] = Field(default=None, ge=5, le=60)
    cutoff_on_accident: Optional[bool] = None


class DeviceConfigResponse(BaseModel):
    alcohol_threshold_mg_l: float
    collision_accel_g: float
    collision_tilt_deg: float
    heartbeat_timeout_ms: int
    telemetry_interval_sec: int
    emergency_countdown_sec: int
    cutoff_on_accident: bool


class DeviceResponse(BaseModel):
    id: str
    serial_number: str
    device_type: str
    hardware_version: str
    firmware_version: str
    label: Optional[str] = None
    status: str
    is_active: bool
    last_seen_at: Optional[datetime] = None
    last_battery_pct: Optional[int] = None
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    paired_device_id: Optional[str] = None
    config: Optional[DeviceConfigResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
