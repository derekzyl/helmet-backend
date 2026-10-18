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
        device_type_upper = (data.device_type or "SMART_HELMET_SYSTEM").upper()

        # If registering a unified Smart Helmet & Ignition Kit (1 device)
        if device_type_upper in ("SMART_HELMET_SYSTEM", "SYSTEM", "HELMET_IGNITION_KIT") or (
            device_type_upper == "HELMET" and data.ignition_serial
        ):
            return await self.register_system_kit(
                helmet_serial=data.serial_number,
                ignition_serial=data.ignition_serial,
                label=data.label,
                hardware_version=data.hardware_version,
                firmware_version=data.firmware_version,
                alcohol_threshold_mg_l=data.alcohol_threshold_mg_l or 0.05,
                collision_accel_g=data.collision_accel_g or 3.5,
                owner_id=owner_id,
            )

        # Standalone individual device registration
        stmt = select(DeviceModel).where(DeviceModel.serial_number == data.serial_number)
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device with serial number '{data.serial_number}' is already registered.",
            )

        device = DeviceModel(
            serial_number=data.serial_number,
            device_type=device_type_upper,
            hardware_version=data.hardware_version,
            firmware_version=data.firmware_version,
            label=data.label,
            owner_id=owner_id,
            status="UNPAIRED",
            is_active=True,
        )
        self.db.add(device)
        await self.db.flush()

        config = DeviceConfigModel(
            device_id=device.id,
            alcohol_threshold_mg_l=data.alcohol_threshold_mg_l or 0.05,
            collision_accel_g=data.collision_accel_g or 3.5,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(device)
        logs.info(f"Registered device {device.serial_number} ({device.device_type})")
        return device

    async def register_system_kit(
        self,
        helmet_serial: str,
        ignition_serial: Optional[str] = None,
        label: Optional[str] = None,
        hardware_version: str = "v1.0",
        firmware_version: str = "1.0.0",
        alcohol_threshold_mg_l: float = 0.05,
        collision_accel_g: float = 3.5,
        owner_id: Optional[str] = None,
    ) -> DeviceModel:
        """Register Smart Helmet and Motorcycle Ignition together as 1 cohesive device."""
        helmet_sn = helmet_serial.strip()
        if not ignition_serial:
            if helmet_sn.startswith("HLM-"):
                ignition_sn = "IGN-" + helmet_sn[4:]
            elif helmet_sn.startswith("HLM"):
                ignition_sn = "IGN" + helmet_sn[3:]
            else:
                ignition_sn = f"{helmet_sn}-IGN"
        else:
            ignition_sn = ignition_serial.strip()

        # Check if either already registered
        stmt = select(DeviceModel).where(
            or_(
                DeviceModel.serial_number == helmet_sn,
                DeviceModel.serial_number == ignition_sn,
            )
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().all()
        if existing:
            sns = [d.serial_number for d in existing]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device(s) with serial number(s) {sns} are already registered in the system.",
            )

        psk = secrets.token_hex(32)
        system_label = label or f"Smart Helmet System ({helmet_sn})"

        # 1. Primary Helmet Unit
        helmet = DeviceModel(
            serial_number=helmet_sn,
            device_type="SMART_HELMET_SYSTEM",
            hardware_version=hardware_version,
            firmware_version=firmware_version,
            label=system_label,
            owner_id=owner_id,
            status="ONLINE",
            is_active=True,
            pairing_secret=psk,
        )
        self.db.add(helmet)
        await self.db.flush()

        # 2. Paired Ignition Relay Unit
        ignition = DeviceModel(
            serial_number=ignition_sn,
            device_type="IGNITION",
            hardware_version=hardware_version,
            firmware_version=firmware_version,
            label=f"{system_label} - Ignition Relay",
            owner_id=owner_id,
            status="ONLINE",
            is_active=True,
            paired_device_id=helmet.id,
            pairing_secret=psk,
        )
        self.db.add(ignition)
        await self.db.flush()

        helmet.paired_device_id = ignition.id

        # 3. Default Safety Threshold Configurations
        helmet_config = DeviceConfigModel(
            device_id=helmet.id,
            alcohol_threshold_mg_l=alcohol_threshold_mg_l,
            collision_accel_g=collision_accel_g,
        )
        ignition_config = DeviceConfigModel(device_id=ignition.id)
        self.db.add(helmet_config)
        self.db.add(ignition_config)

        await self.db.commit()
        await self.db.refresh(helmet)

        # Attach helper attributes for response serialization
        setattr(helmet, "paired_serial_number", ignition_sn)
        setattr(helmet, "ignition_serial", ignition_sn)

        logs.info(f"Registered unified Smart Helmet System: {helmet_sn} <===> {ignition_sn} as 1 device.")
        return helmet

    async def list_devices(
        self,
        owner_id: Optional[str] = None,
        device_type: Optional[str] = None,
        all_components: bool = False,
    ) -> List[DeviceModel]:
        stmt = select(DeviceModel).options(selectinload(DeviceModel.config))
        if owner_id:
            stmt = stmt.where(DeviceModel.owner_id == owner_id)

        if device_type:
            stmt = stmt.where(DeviceModel.device_type == device_type.upper())
        elif not all_components:
            # Paired helmet & ignition units go together as 1 device.
            # Unpaired ignitions remain visible until paired.
            from sqlalchemy import and_
            stmt = stmt.where(
                or_(
                    DeviceModel.device_type.in_(["SMART_HELMET_SYSTEM", "HELMET"]),
                    and_(DeviceModel.device_type == "IGNITION", DeviceModel.paired_device_id.is_(None)),
                )
            )

        res = await self.db.execute(stmt)
        devices = list(res.scalars().all())

        # Resolve paired ignition serial numbers
        paired_ids = [d.paired_device_id for d in devices if d.paired_device_id]
        if paired_ids:
            p_stmt = select(DeviceModel.id, DeviceModel.serial_number).where(DeviceModel.id.in_(paired_ids))
            p_res = await self.db.execute(p_stmt)
            id_to_sn = {row[0]: row[1] for row in p_res.all()}
            for d in devices:
                if d.paired_device_id and d.paired_device_id in id_to_sn:
                    setattr(d, "paired_serial_number", id_to_sn[d.paired_device_id])
                    setattr(d, "ignition_serial", id_to_sn[d.paired_device_id])

        return devices

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
                detail=f"Device '{device_id_or_serial}' not found.",
            )

        if device.paired_device_id:
            p_stmt = select(DeviceModel.serial_number).where(DeviceModel.id == device.paired_device_id)
            p_res = await self.db.execute(p_stmt)
            p_sn = p_res.scalar_one_or_none()
            if p_sn:
                setattr(device, "paired_serial_number", p_sn)
                setattr(device, "ignition_serial", p_sn)

        return device

    async def pair_devices(self, data: DevicePairRequest) -> DevicePairResponse:
        helmet = await self.get_device(data.helmet_device_id)
        ignition = await self.get_device(data.ignition_device_id)

        # Generate a shared 256-bit cryptographically secure key (64 hex characters)
        psk = secrets.token_hex(32)
        now = datetime.now(timezone.utc)

        helmet.paired_device_id = ignition.id
        helmet.pairing_secret = psk
        helmet.status = "ONLINE"
        helmet.device_type = "SMART_HELMET_SYSTEM"

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
