from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EmergencyContactCreate(BaseModel):
    name: str = Field(..., example="Jane Doe")
    phone_number: str = Field(..., example="+2348012345678")
    relationship: str = Field(default="Family", example="Spouse")
    device_id: Optional[str] = None
    is_primary: bool = Field(default=False)
    notify_sms: bool = Field(default=True)
    notify_call: bool = Field(default=False)


class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    relationship: Optional[str] = None
    is_primary: Optional[bool] = None
    notify_sms: Optional[bool] = None
    notify_call: Optional[bool] = None


class EmergencyContactResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    name: str
    phone_number: str
    relationship: str
    is_primary: bool
    notify_sms: bool
    notify_call: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
