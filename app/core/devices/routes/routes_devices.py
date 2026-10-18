from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.devices.services.service_device import DeviceService
from app.core.devices.types.type_device import (
    DeviceConfigResponse,
    DeviceConfigUpdate,
    DevicePairRequest,
    DevicePairResponse,
    DeviceRegisterRequest,
    DeviceResponse,
)

device_router = APIRouter()


@device_router.post("/register", response_model=DeviceResponse, status_code=201)
@device_router.post("/system", response_model=DeviceResponse, status_code=201)
@device_router.post("/register-system", response_model=DeviceResponse, status_code=201)
async def register_device(
    data: DeviceRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a Smart Helmet and Motorcycle Ignition together as 1 cohesive system device."""
    device = await DeviceService(db=db).register_device(data=data)
    return device


@device_router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    db: Annotated[AsyncSession, Depends(get_db)],
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    all_components: bool = Query(False, description="If True, returns raw underlying hardware components separately"),
):
    """List registered devices in the fleet (presents 1 device per paired Smart Helmet System by default)."""
    devices = await DeviceService(db=db).list_devices(device_type=device_type, all_components=all_components)
    return devices


@device_router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve details for a specific device by ID or serial number."""
    device = await DeviceService(db=db).get_device(device_id_or_serial=device_id)
    return device


@device_router.post("/pair", response_model=DevicePairResponse)
async def pair_devices(
    data: DevicePairRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Explicitly pair a helmet unit with an ignition unit and generate the 256-bit PSK."""
    pair_res = await DeviceService(db=db).pair_devices(data=data)
    return pair_res


@device_router.put("/{device_id}/config", response_model=DeviceConfigResponse)
async def update_device_config(
    device_id: Annotated[str, Path()],
    data: DeviceConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update configuration thresholds (BAC limit, collision sensitivity, countdowns)."""
    config = await DeviceService(db=db).update_device_config(device_id=device_id, update_data=data)
    return config
