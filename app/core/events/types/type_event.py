from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SafetyEventCreate(BaseModel):
    device_id: str = Field(..., description="Device ID or serial number")
    event_type: str = Field(..., example="COLLISION")
    severity: str = Field(default="WARNING", example="CRITICAL")
    message: str = Field(..., example="Crash detected! Peak 4.8G, tilt 75°")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None


class SafetyEventResponse(BaseModel):
    id: str
    device_id: str
    event_type: str
    severity: str
    message: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    payload_json: Optional[str] = None
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
