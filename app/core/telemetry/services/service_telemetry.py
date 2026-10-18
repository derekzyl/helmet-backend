from datetime import datetime, timezone
import json
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.devices.models.model_device import DeviceModel
from app.core.telemetry.models.model_telemetry import TelemetryModel
from app.core.telemetry.types.type_telemetry import TelemetryIngestItem
from app.core.telemetry.websocket_hub import telemetry_ws_hub


class TelemetryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_single(self, item: TelemetryIngestItem) -> TelemetryModel:
        # Find device by ID or serial number
        stmt = select(DeviceModel).where(
            (DeviceModel.id == item.device_id) | (DeviceModel.serial_number == item.device_id)
        )
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()

        device_db_id = device.id if device else item.device_id

        recorded_dt = (
            datetime.fromtimestamp(item.timestamp, tz=timezone.utc)
            if item.timestamp
            else datetime.now(timezone.utc)
        )

        model = TelemetryModel(
            device_id=device_db_id,
            recorded_at=recorded_dt,
            latitude=item.latitude,
            longitude=item.longitude,
            altitude_m=item.altitude_m,
            speed_kmh=item.speed_kmh,
            battery_pct=item.battery_pct,
            battery_mv=item.battery_mv or 4000,
            alcohol_level_mg_l=item.alcohol_level_mg_l,
            helmet_worn=item.helmet_worn,
            ignition_state=item.ignition_state,
            link_state=item.link_state,
            hdop=item.hdop,
            satellites=item.satellites or 0,
            raw_payload=json.dumps(item.model_dump()),
        )
        self.db.add(model)

        # Update device quick-cache fields if device exists
        if device:
            device.last_seen_at = recorded_dt
            device.last_battery_pct = item.battery_pct
            if item.latitude is not None and item.longitude is not None:
                device.last_latitude = item.latitude
                device.last_longitude = item.longitude
            device.status = "ONLINE"

        await self.db.commit()
        await self.db.refresh(model)

        # Push to live WebSocket hub
        live_data = {
            "id": model.id,
            "device_id": device.serial_number if device else item.device_id,
            "recorded_at": recorded_dt.isoformat(),
            "latitude": item.latitude,
            "longitude": item.longitude,
            "speed_kmh": item.speed_kmh,
            "battery_pct": item.battery_pct,
            "alcohol_level_mg_l": item.alcohol_level_mg_l,
            "helmet_worn": item.helmet_worn,
            "ignition_state": item.ignition_state,
            "link_state": item.link_state,
            "satellites": item.satellites or 0,
        }
        await telemetry_ws_hub.broadcast_telemetry(
            device_id=device.serial_number if device else item.device_id,
            data=live_data,
        )

        return model

    async def ingest_batch(self, items: List[TelemetryIngestItem]) -> int:
        count = 0
        for item in items:
            await self.ingest_single(item)
            count += 1
        return count

    async def get_latest_telemetry(self, device_id_or_serial: str) -> Optional[TelemetryModel]:
        # Resolve device ID first
        stmt_dev = select(DeviceModel).where(
            (DeviceModel.id == device_id_or_serial) | (DeviceModel.serial_number == device_id_or_serial)
        )
        res_dev = await self.db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()
        resolved_id = device.id if device else device_id_or_serial

        stmt = (
            select(TelemetryModel)
            .where(TelemetryModel.device_id == resolved_id)
            .order_by(desc(TelemetryModel.recorded_at))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_history(self, device_id_or_serial: str, limit: int = 100) -> List[TelemetryModel]:
        stmt_dev = select(DeviceModel).where(
            (DeviceModel.id == device_id_or_serial) | (DeviceModel.serial_number == device_id_or_serial)
        )
        res_dev = await self.db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()
        resolved_id = device.id if device else device_id_or_serial

        stmt = (
            select(TelemetryModel)
            .where(TelemetryModel.device_id == resolved_id)
            .order_by(desc(TelemetryModel.recorded_at))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
