from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    serial_number: Optional[str] = Field(default=None, example="HLM-2026-0001", description="Serial number of the Smart Helmet unit (auto-generated if omitted)")
    ignition_serial: Optional[str] = Field(default=None, example="IGN-2026-0001", description="Optional serial number of the paired ignition relay (auto-generated if omitted)")
    device_type: Optional[str] = Field(default="SMART_HELMET_SYSTEM", example="SMART_HELMET_SYSTEM", description="SMART_HELMET_SYSTEM, HELMET, or IGNITION")
    hardware_version: str = Field(default="v1.0")
    firmware_version: str = Field(default="1.0.0")
    label: Optional[str] = Field(default=None, example="Primary Smart Helmet & Ignition Unit")
    alcohol_threshold_mg_l: Optional[float] = Field(default=0.05, ge=0.0, le=1.0)
    collision_accel_g: Optional[float] = Field(default=3.5, ge=1.5, le=16.0)


class EasyInstallRequest(BaseModel):
    short_code: Optional[str] = Field(default=None, description="Short 4-6 digit setup PIN or claim code e.g. '8492' or '729-104'")
    qr_payload: Optional[str] = Field(default=None, description="Scanned QR code payload string from device sticker")
    label: Optional[str] = Field(default=None, description="Friendly motorcycle or system nickname e.g. 'Cruiser Alpha'")
    vehicle_type: Optional[str] = Field(default="Motorcycle", description="Motorcycle, Cruiser, Sportbike, Scooter, Off-road")
    safety_preset: Optional[str] = Field(default="STANDARD", description="STANDARD, STRICT, or TRACK")
    serial_number: Optional[str] = Field(default=None, description="Optional manual serial number override")


class DiscoverableDeviceResponse(BaseModel):
    kit_code: str
    serial_number: str
    ignition_serial: str
    label: str
    rssi_dbm: int = -52
    ready_to_pair: bool = True


class SystemRegisterRequest(BaseModel):
    label: Optional[str] = Field(default=None, example="Primary Smart Helmet & Ignition Unit")
    helmet_serial: Optional[str] = Field(default=None, example="HLM-2026-0001", description="Serial number of the helmet unit (auto-generated if omitted)")
    ignition_serial: Optional[str] = Field(default=None, example="IGN-2026-0001", description="Serial number of paired ignition box (auto-generated if omitted)")
    hardware_version: str = Field(default="v1.0")
    firmware_version: str = Field(default="1.0.0")
    alcohol_threshold_mg_l: Optional[float] = Field(default=0.05, ge=0.0, le=1.0)
    collision_accel_g: Optional[float] = Field(default=3.5, ge=1.5, le=16.0)


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
    paired_serial_number: Optional[str] = None
    ignition_serial: Optional[str] = None
    pairing_secret: Optional[str] = None
    config: Optional[DeviceConfigResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
