from datetime import datetime, timezone
import json
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.devices.models.model_device import DeviceModel
from app.core.events.models.model_event import SafetyEventModel
from app.core.events.types.type_event import SafetyEventCreate
from app.core.telemetry.websocket_hub import telemetry_ws_hub
from app.utils.logger.log import logs


class SafetyEventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(self, data: SafetyEventCreate) -> SafetyEventModel:
        # Resolve device
        stmt_dev = select(DeviceModel).where(
            (DeviceModel.id == data.device_id) | (DeviceModel.serial_number == data.device_id)
        )
        res_dev = await self.db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()
        device_db_id = device.id if device else data.device_id

        event = SafetyEventModel(
            device_id=device_db_id,
            event_type=data.event_type.upper(),
            severity=data.severity.upper(),
            message=data.message,
            latitude=data.latitude,
            longitude=data.longitude,
            payload_json=json.dumps(data.payload) if data.payload else None,
            acknowledged=False,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logs.warning(f"🚨 Safety Alert [{event.severity}] {event.event_type} on device {data.device_id}: {event.message}")

        # Broadcast via WebSocket hub immediately to all connected cockpit dashboards and apps
        await telemetry_ws_hub.broadcast_alert(
            device_id=device.serial_number if device else data.device_id,
            event_data={
                "id": event.id,
                "device_id": device.serial_number if device else data.device_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "message": event.message,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "created_at": event.created_at.isoformat(),
            },
        )

        return event

    async def list_events(
        self,
        device_id: Optional[str] = None,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50,
    ) -> List[SafetyEventModel]:
        stmt = select(SafetyEventModel).order_by(desc(SafetyEventModel.created_at)).limit(limit)

        if device_id:
            stmt_dev = select(DeviceModel).where(
                (DeviceModel.id == device_id) | (DeviceModel.serial_number == device_id)
            )
            res_dev = await self.db.execute(stmt_dev)
            device = res_dev.scalar_one_or_none()
            resolved_id = device.id if device else device_id
            stmt = stmt.where(SafetyEventModel.device_id == resolved_id)

        if severity:
            stmt = stmt.where(SafetyEventModel.severity == severity.upper())
        if event_type:
            stmt = stmt.where(SafetyEventModel.event_type == event_type.upper())
        if acknowledged is not None:
            stmt = stmt.where(SafetyEventModel.acknowledged == acknowledged)

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def acknowledge_event(self, event_id: str, acknowledged_by: str = "Operator") -> SafetyEventModel:
        stmt = select(SafetyEventModel).where(SafetyEventModel.id == event_id)
        res = await self.db.execute(stmt)
        event = res.scalar_one_or_none()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Safety event '{event_id}' not found."
            )
        event.acknowledged = True
        event.acknowledged_at = datetime.now(timezone.utc)
        event.acknowledged_by = acknowledged_by
        await self.db.commit()
        await self.db.refresh(event)
        return event
