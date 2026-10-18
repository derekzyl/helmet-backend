from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.contacts.services.service_contact import EmergencyContactService
from app.core.contacts.types.type_contact import (
    EmergencyContactCreate,
    EmergencyContactResponse,
    EmergencyContactUpdate,
)

contact_router = APIRouter()


@contact_router.post("/", response_model=EmergencyContactResponse, status_code=201)
async def create_emergency_contact(
    data: EmergencyContactCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a new emergency contact for SMS/voice notifications."""
    contact = await EmergencyContactService(db=db).create_contact(data=data)
    return contact


@contact_router.get("/", response_model=List[EmergencyContactResponse])
async def list_emergency_contacts(
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: Optional[str] = Query(None, description="Filter contacts by device"),
):
    """List registered emergency contacts."""
    contacts = await EmergencyContactService(db=db).list_contacts(device_id=device_id)
    return contacts


@contact_router.put("/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(
    contact_id: Annotated[str, Path()],
    data: EmergencyContactUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update contact details or notification preferences."""
    contact = await EmergencyContactService(db=db).update_contact(contact_id=contact_id, data=data)
    return contact


@contact_router.delete("/{contact_id}", status_code=204)
async def delete_emergency_contact(
    contact_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove an emergency contact."""
    await EmergencyContactService(db=db).delete_contact(contact_id=contact_id)
    return None
