from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contacts.models.model_contact import EmergencyContactModel
from app.core.contacts.types.type_contact import (
    EmergencyContactCreate,
    EmergencyContactUpdate,
)
from app.core.devices.models.model_device import DeviceModel
from app.utils.logger.log import logs


class EmergencyContactService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_contact(self, data: EmergencyContactCreate, user_id: Optional[str] = None) -> EmergencyContactModel:
        device_db_id = None
        if data.device_id:
            stmt_dev = select(DeviceModel).where(
                (DeviceModel.id == data.device_id) | (DeviceModel.serial_number == data.device_id)
            )
            res_dev = await self.db.execute(stmt_dev)
            dev = res_dev.scalar_one_or_none()
            device_db_id = dev.id if dev else data.device_id

        contact = EmergencyContactModel(
            user_id=user_id,
            device_id=device_db_id,
            name=data.name,
            phone_number=data.phone_number,
            relationship=data.relationship,
            is_primary=data.is_primary,
            notify_sms=data.notify_sms,
            notify_call=data.notify_call,
        )
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        logs.info(f"Added emergency contact '{contact.name}' ({contact.phone_number})")
        return contact

    async def list_contacts(self, user_id: Optional[str] = None, device_id: Optional[str] = None) -> List[EmergencyContactModel]:
        stmt = select(EmergencyContactModel)
        if user_id:
            stmt = stmt.where(EmergencyContactModel.user_id == user_id)
        if device_id:
            stmt_dev = select(DeviceModel).where(
                (DeviceModel.id == device_id) | (DeviceModel.serial_number == device_id)
            )
            res_dev = await self.db.execute(stmt_dev)
            dev = res_dev.scalar_one_or_none()
            resolved_id = dev.id if dev else device_id
            stmt = stmt.where(EmergencyContactModel.device_id == resolved_id)

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_contact(self, contact_id: str, data: EmergencyContactUpdate) -> EmergencyContactModel:
        stmt = select(EmergencyContactModel).where(EmergencyContactModel.id == contact_id)
        res = await self.db.execute(stmt)
        contact = res.scalar_one_or_none()
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Emergency contact '{contact_id}' not found."
            )
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(contact, field, val)

        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def delete_contact(self, contact_id: str) -> bool:
        stmt = select(EmergencyContactModel).where(EmergencyContactModel.id == contact_id)
        res = await self.db.execute(stmt)
        contact = res.scalar_one_or_none()
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Emergency contact '{contact_id}' not found."
            )
        await self.db.delete(contact)
        await self.db.commit()
        logs.info(f"Deleted emergency contact {contact_id}")
        return True
