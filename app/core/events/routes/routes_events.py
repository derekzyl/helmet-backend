from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.events.services.service_event import SafetyEventService
from app.core.events.types.type_event import SafetyEventCreate, SafetyEventResponse

event_router = APIRouter()


@event_router.post("/", response_model=SafetyEventResponse, status_code=201)
async def create_safety_event(
    data: SafetyEventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Log an immediate safety incident (accident, alcohol lockout, SOS button)."""
    event = await SafetyEventService(db=db).create_event(data=data)
    return event


@event_router.get("/", response_model=List[SafetyEventResponse])
async def list_safety_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: Optional[str] = Query(None, description="Filter by device ID or serial"),
    severity: Optional[str] = Query(None, description="Filter: INFO, WARNING, CRITICAL"),
    event_type: Optional[str] = Query(None, description="Filter: COLLISION, ALCOHOL_LOCKOUT, etc."),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged state"),
    limit: int = Query(50, ge=1, le=500),
):
    """Query recent safety alerts and incidents."""
    events = await SafetyEventService(db=db).list_events(
        device_id=device_id,
        severity=severity,
        event_type=event_type,
        acknowledged=acknowledged,
        limit=limit,
    )
    return events


@event_router.post("/acknowledge/{event_id}", response_model=SafetyEventResponse)
async def acknowledge_safety_event(
    event_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    acknowledged_by: str = Query("Fleet Operator", description="Name/role of acknowledging party"),
):
    """Acknowledge a safety alarm."""
    event = await SafetyEventService(db=db).acknowledge_event(event_id=event_id, acknowledged_by=acknowledged_by)
    return event
