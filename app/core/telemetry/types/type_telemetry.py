from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TelemetryIngestItem(BaseModel):
    device_id: str = Field(..., description="Device ID or serial number")
    timestamp: Optional[int] = Field(None, description="Unix timestamp in seconds")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    altitude_m: Optional[float] = None
    speed_kmh: Optional[float] = Field(default=0.0, ge=0.0)
    battery_pct: int = Field(default=100, ge=0, le=100)
    battery_mv: Optional[int] = Field(default=4000)
    alcohol_level_mg_l: float = Field(default=0.0, ge=0.0)
    helmet_worn: bool = Field(default=False)
    ignition_state: str = Field(default="LOCKED")
    link_state: str = Field(default="CONNECTED")
    hdop: Optional[float] = None
    satellites: Optional[int] = 0


class TelemetryBatchIngestRequest(BaseModel):
    items: List[TelemetryIngestItem] = Field(..., max_length=100)


class TelemetryResponse(BaseModel):
    id: str
    device_id: str
    recorded_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    speed_kmh: Optional[float] = 0.0
    battery_pct: int
    battery_mv: int
    alcohol_level_mg_l: float
    helmet_worn: bool
    ignition_state: str
    link_state: str
    hdop: Optional[float] = None
    satellites: Optional[int] = 0

    class Config:
        from_attributes = True


class TelemetryIngestResponse(BaseModel):
    status: str = "INGESTED"
    ingested_count: int = 1
    server_time: datetime
