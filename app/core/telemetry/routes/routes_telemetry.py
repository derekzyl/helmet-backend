from datetime import datetime, timezone
import json
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.telemetry.services.service_telemetry import TelemetryService
from app.core.telemetry.types.type_telemetry import (
    TelemetryBatchIngestRequest,
    TelemetryIngestItem,
    TelemetryIngestResponse,
    TelemetryResponse,
)
from app.core.telemetry.websocket_hub import telemetry_ws_hub
from app.utils.logger.log import logs

telemetry_router = APIRouter()


@telemetry_router.post("/ingest", response_model=TelemetryIngestResponse)
async def ingest_telemetry(
    item: TelemetryIngestItem,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Ingest a single telemetry frame from a helmet or ignition unit."""
    await TelemetryService(db=db).ingest_single(item=item)
    return TelemetryIngestResponse(
        status="INGESTED",
        ingested_count=1,
        server_time=datetime.now(timezone.utc),
    )


@telemetry_router.post("/batch", response_model=TelemetryIngestResponse)
async def ingest_batch_telemetry(
    data: TelemetryBatchIngestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Ingest a batch of offline-buffered telemetry frames."""
    count = await TelemetryService(db=db).ingest_batch(items=data.items)
    return TelemetryIngestResponse(
        status="INGESTED",
        ingested_count=count,
        server_time=datetime.now(timezone.utc),
    )


@telemetry_router.get("/latest/{device_id}", response_model=Optional[TelemetryResponse])
async def get_latest_telemetry(
    device_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the most recent telemetry point for a given device."""
    telemetry = await TelemetryService(db=db).get_latest_telemetry(device_id_or_serial=device_id)
    return telemetry


@telemetry_router.get("/history/{device_id}", response_model=List[TelemetryResponse])
async def get_telemetry_history(
    device_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=1000),
):
    """Get historical telemetry records for GPS track mapping and analytics."""
    history = await TelemetryService(db=db).get_history(device_id_or_serial=device_id, limit=limit)
    return history


@telemetry_router.websocket("/ws")
async def telemetry_websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket feed for cockpit gauges and live fleet maps."""
    await telemetry_ws_hub.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                if msg.get("action") == "SUBSCRIBE":
                    device_ids = msg.get("device_ids", [])
                    await telemetry_ws_hub.subscribe(websocket, device_ids)
                elif msg.get("action") == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG", "time": datetime.now(timezone.utc).isoformat()}))
            except Exception as e:
                logs.warning(f"Error parsing WebSocket message: {e}")
    except WebSocketDisconnect:
        await telemetry_ws_hub.disconnect(websocket)
    except Exception as e:
        logs.error(f"WebSocket unexpected error: {e}")
        await telemetry_ws_hub.disconnect(websocket)
