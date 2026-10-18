import asyncio
import json
from typing import Any, Dict, List, Set
from fastapi import WebSocket
from app.utils.logger.log import logs


class TelemetryWebSocketHub:
    """Manages active WebSocket connections from web dashboards and mobile apps."""

    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._subscriptions: Dict[WebSocket, Set[str]] = {}  # ws -> set of device_ids
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
            self._subscriptions[websocket] = set()
        logs.info(f"WebSocket client connected. Total active: {len(self._active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._active_connections.discard(websocket)
            self._subscriptions.pop(websocket, None)
        logs.info(f"WebSocket client disconnected. Total active: {len(self._active_connections)}")

    async def subscribe(self, websocket: WebSocket, device_ids: List[str]):
        async with self._lock:
            if websocket in self._subscriptions:
                self._subscriptions[websocket].update(device_ids)
        logs.info(f"WebSocket client subscribed to {len(device_ids)} devices")

    async def broadcast_telemetry(self, device_id: str, data: Dict[str, Any]):
        """Broadcasts telemetry frame to clients subscribed to device or global listeners."""
        payload = {
            "type": "TELEMETRY",
            "device_id": device_id,
            "data": data,
        }
        await self._broadcast_json(payload, target_device_id=device_id)

    async def broadcast_alert(self, device_id: str, event_data: Dict[str, Any]):
        """Broadcasts safety alert immediately to all active listeners."""
        payload = {
            "type": "ALERT",
            "device_id": device_id,
            "event": event_data,
        }
        await self._broadcast_json(payload, target_device_id=None)  # Alerts broadcast globally

    async def _broadcast_json(self, payload: Dict[str, Any], target_device_id: str | None = None):
        dead_sockets: List[WebSocket] = []
        msg_str = json.dumps(payload)

        async with self._lock:
            connections = list(self._active_connections)

        for ws in connections:
            try:
                subs = self._subscriptions.get(ws, set())
                # Send if subscriber is interested in this device or has no specific filter (wildcard)
                if target_device_id is None or not subs or target_device_id in subs:
                    await ws.send_text(msg_str)
            except Exception as e:
                logs.warning(f"Error sending to WebSocket client: {e}")
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self._active_connections.discard(ws)
                    self._subscriptions.pop(ws, None)


telemetry_ws_hub = TelemetryWebSocketHub()
