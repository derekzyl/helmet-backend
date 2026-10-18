from datetime import datetime, timezone
import secrets
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.devices.models.model_device import DeviceConfigModel, DeviceModel
from app.core.devices.types.type_device import (
    DeviceConfigUpdate,
    DevicePairRequest,
    DevicePairResponse,
    DeviceRegisterRequest,
)
from app.utils.logger.log import logs


class DeviceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(self, data: DeviceRegisterRequest, owner_id: Optional[str] = None) -> DeviceModel:
        # Check if serial number already exists
        stmt = select(DeviceModel).where(DeviceModel.serial_number == data.serial_number)
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device with serial number '{data.serial_number}' is already registered."
            )

        device = DeviceModel(
            serial_number=data.serial_number,
            device_type=data.device_type.upper(),
            hardware_version=data.hardware_version,
            firmware_version=data.firmware_version,
            label=data.label,
            owner_id=owner_id,
            status="UNPAIRED",
            is_active=True,
        )
        self.db.add(device)
        await self.db.flush()

        # Initialize default config for helmet or ignition
        config = DeviceConfigModel(device_id=device.id)
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(device)
        logs.info(f"Registered new device {device.serial_number} ({device.device_type})")
        return device

    async def list_devices(self, owner_id: Optional[str] = None, device_type: Optional[str] = None) -> List[DeviceModel]:
        stmt = select(DeviceModel).options(selectinload(DeviceModel.config))
        if owner_id:
            stmt = stmt.where(DeviceModel.owner_id == owner_id)
        if device_type:
            stmt = stmt.where(DeviceModel.device_type == device_type.upper())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_device(self, device_id_or_serial: str) -> DeviceModel:
        stmt = (
            select(DeviceModel)
            .options(selectinload(DeviceModel.config))
            .where(
                or_(
                    DeviceModel.id == device_id_or_serial,
                    DeviceModel.serial_number == device_id_or_serial,
                )
            )
        )
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device '{device_id_or_serial}' not found."
            )
        return device

    async def pair_devices(self, data: DevicePairRequest) -> DevicePairResponse:
        helmet = await self.get_device(data.helmet_device_id)
        ignition = await self.get_device(data.ignition_device_id)

        if helmet.device_type != "HELMET":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Device {helmet.serial_number} is not of type HELMET"
            )
        if ignition.device_type != "IGNITION":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Device {ignition.serial_number} is not of type IGNITION"
            )

        # Generate a shared 256-bit cryptographically secure key (64 hex characters)
        psk = secrets.token_hex(32)
        now = datetime.now(timezone.utc)

        helmet.paired_device_id = ignition.id
        helmet.pairing_secret = psk
        helmet.status = "ONLINE"

        ignition.paired_device_id = helmet.id
        ignition.pairing_secret = psk
        ignition.status = "ONLINE"

        await self.db.commit()
        logs.info(f"Successfully paired Helmet {helmet.serial_number} with Ignition {ignition.serial_number}")

        return DevicePairResponse(
            status="PAIRED",
            helmet_device_id=helmet.id,
            ignition_device_id=ignition.id,
            pairing_secret=psk,
            paired_at=now,
        )

    async def update_device_config(self, device_id: str, update_data: DeviceConfigUpdate) -> DeviceConfigModel:
        device = await self.get_device(device_id)
        stmt = select(DeviceConfigModel).where(DeviceConfigModel.device_id == device.id)
        res = await self.db.execute(stmt)
        config = res.scalar_one_or_none()
        if not config:
            config = DeviceConfigModel(device_id=device.id)
            self.db.add(config)

        for field, val in update_data.model_dump(exclude_unset=True).items():
            setattr(config, field, val)

        await self.db.commit()
        await self.db.refresh(config)
        logs.info(f"Updated configuration for device {device.serial_number}")
        return config
