import os
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.app import init_app
from app.config.database.db import session_manager

TEST_DB_FILE = "test_smart_helmet.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def test_db_setup():
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    session_manager.init(TEST_DB_URL, echo=False)
    async with session_manager.connect() as conn:
        await session_manager.create_all(conn)
    yield
    await session_manager.close()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.fixture
async def client():
    app = init_app(init_db=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_device_registration_and_listing(client: AsyncClient):
    # 1. Register Helmet
    res_hlm = await client.post(
        "/api/v1/devices/register",
        json={
            "serial_number": "HLM-TEST-0001",
            "device_type": "HELMET",
            "hardware_version": "v1.2",
            "firmware_version": "1.0.0",
            "label": "Test Helmet Unit",
        },
    )
    assert res_hlm.status_code == 201
    hlm_data = res_hlm.json()
    assert hlm_data["serial_number"] == "HLM-TEST-0001"
    assert hlm_data["status"] == "UNPAIRED"

    # 2. Register Ignition
    res_ign = await client.post(
        "/api/v1/devices/register",
        json={
            "serial_number": "IGN-TEST-0001",
            "device_type": "IGNITION",
            "hardware_version": "v1.0",
            "firmware_version": "1.0.0",
            "label": "Test Ignition Unit",
        },
    )
    assert res_ign.status_code == 201

    # 3. List devices
    res_list = await client.get("/api/v1/devices/")
    assert res_list.status_code == 200
    devices = res_list.json()
    assert len(devices) >= 2


@pytest.mark.asyncio
async def test_device_pairing(client: AsyncClient):
    res_pair = await client.post(
        "/api/v1/devices/pair",
        json={
            "helmet_device_id": "HLM-TEST-0001",
            "ignition_device_id": "IGN-TEST-0001",
        },
    )
    assert res_pair.status_code == 200
    data = res_pair.json()
    assert data["status"] == "PAIRED"
    assert len(data["pairing_secret"]) == 64  # 256-bit hex


@pytest.mark.asyncio
async def test_device_config_update(client: AsyncClient):
    res_cfg = await client.put(
        "/api/v1/devices/HLM-TEST-0001/config",
        json={
            "alcohol_threshold_mg_l": 0.04,
            "collision_accel_g": 4.0,
            "emergency_countdown_sec": 15,
        },
    )
    assert res_cfg.status_code == 200
    cfg = res_cfg.json()
    assert cfg["alcohol_threshold_mg_l"] == 0.04
    assert cfg["collision_accel_g"] == 4.0
    assert cfg["emergency_countdown_sec"] == 15


@pytest.mark.asyncio
async def test_telemetry_ingest_and_query(client: AsyncClient):
    # Ingest single
    res_ingest = await client.post(
        "/api/v1/telemetry/ingest",
        json={
            "device_id": "HLM-TEST-0001",
            "latitude": 6.5244,
            "longitude": 3.3792,
            "speed_kmh": 32.5,
            "battery_pct": 91,
            "alcohol_level_mg_l": 0.015,
            "helmet_worn": True,
            "ignition_state": "RUNNING_LATCHED",
            "link_state": "CONNECTED",
        },
    )
    assert res_ingest.status_code == 200
    assert res_ingest.json()["status"] == "INGESTED"

    # Query latest
    res_latest = await client.get("/api/v1/telemetry/latest/HLM-TEST-0001")
    assert res_latest.status_code == 200
    latest = res_latest.json()
    assert latest["speed_kmh"] == 32.5
    assert latest["helmet_worn"] is True
    assert latest["ignition_state"] == "RUNNING_LATCHED"

    # Batch ingest
    res_batch = await client.post(
        "/api/v1/telemetry/batch",
        json={
            "items": [
                {
                    "device_id": "HLM-TEST-0001",
                    "latitude": 6.5245,
                    "longitude": 3.3793,
                    "speed_kmh": 35.0,
                    "battery_pct": 90,
                    "alcohol_level_mg_l": 0.014,
                    "helmet_worn": True,
                    "ignition_state": "RUNNING_LATCHED",
                },
                {
                    "device_id": "HLM-TEST-0001",
                    "latitude": 6.5246,
                    "longitude": 3.3794,
                    "speed_kmh": 38.0,
                    "battery_pct": 89,
                    "alcohol_level_mg_l": 0.013,
                    "helmet_worn": True,
                    "ignition_state": "RUNNING_LATCHED",
                },
            ]
        },
    )
    assert res_batch.status_code == 200
    assert res_batch.json()["ingested_count"] == 2


@pytest.mark.asyncio
async def test_safety_events(client: AsyncClient):
    # Log event
    res_ev = await client.post(
        "/api/v1/events/",
        json={
            "device_id": "HLM-TEST-0001",
            "event_type": "COLLISION",
            "severity": "CRITICAL",
            "message": "Crash detected! Peak 4.5G impact.",
            "latitude": 6.5244,
            "longitude": 3.3792,
            "payload": {"peak_g": 4.5, "tilt_deg": 68.0},
        },
    )
    assert res_ev.status_code == 201
    event = res_ev.json()
    assert event["event_type"] == "COLLISION"
    assert event["severity"] == "CRITICAL"
    event_id = event["id"]

    # List events
    res_list = await client.get("/api/v1/events/?severity=CRITICAL")
    assert res_list.status_code == 200
    events = res_list.json()
    assert any(e["id"] == event_id for e in events)

    # Acknowledge event
    res_ack = await client.post(f"/api/v1/events/acknowledge/{event_id}")
    assert res_ack.status_code == 200
    assert res_ack.json()["acknowledged"] is True


@pytest.mark.asyncio
async def test_emergency_contacts(client: AsyncClient):
    res_c = await client.post(
        "/api/v1/contacts/",
        json={
            "name": "Jane Doe",
            "phone_number": "+2348012345678",
            "relationship": "Spouse",
            "device_id": "HLM-TEST-0001",
            "is_primary": True,
            "notify_sms": True,
        },
    )
    assert res_c.status_code == 201
    contact = res_c.json()
    assert contact["name"] == "Jane Doe"
    contact_id = contact["id"]

    # List
    res_list = await client.get("/api/v1/contacts/?device_id=HLM-TEST-0001")
    assert res_list.status_code == 200
    contacts = res_list.json()
    assert any(c["id"] == contact_id for c in contacts)

    # Delete
    res_del = await client.delete(f"/api/v1/contacts/{contact_id}")
    assert res_del.status_code == 204
