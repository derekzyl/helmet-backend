#!/usr/bin/env python3
"""
Purge All Dummy & Seeded Fleet Data from the Smart Helmet Database
-----------------------------------------------------------------
Deletes:
- All Telemetry Records (GPS breadcrumbs, sensor readings)
- All Safety Events & Collision Logs
- All Emergency Contacts
- All Paired Helmet & Ignition Device records and configs
- Cleans User profiles to remove dummy rider identities while preserving admin credentials
"""

import asyncio
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import delete, select, update

from app.config.database.db import session_manager
from app.config.env import env
from app.core.contacts.models.model_contact import EmergencyContactModel
from app.core.devices.models.model_device import DeviceConfigModel, DeviceModel
from app.core.events.models.model_event import SafetyEventModel
from app.core.telemetry.models.model_telemetry import TelemetryModel
from app.core.users.models.model_user import UserModel


async def clear_data():
    db_url = env.get("database_url") or "sqlite+aiosqlite:///smart_helmet.db"
    print(f"[*] Connecting to database at: {db_url}")
    session_manager.init(db_url, echo=False)

    async with session_manager.session() as db:
        print("[*] Starting purge of all dummy data...")

        # 1. Delete all Telemetry records
        telem_del = await db.execute(delete(TelemetryModel))
        print(f"    -> Deleted {telem_del.rowcount} telemetry record(s).")

        # 2. Delete all Safety Events
        event_del = await db.execute(delete(SafetyEventModel))
        print(f"    -> Deleted {event_del.rowcount} safety event(s).")

        # 3. Delete all Emergency Contacts
        contact_del = await db.execute(delete(EmergencyContactModel))
        print(f"    -> Deleted {contact_del.rowcount} emergency contact(s).")

        # 4. Delete all Device Configurations
        config_del = await db.execute(delete(DeviceConfigModel))
        print(f"    -> Deleted {config_del.rowcount} device config(s).")

        # 5. Break pairing circular references before deleting devices
        await db.execute(update(DeviceModel).values(paired_device_id=None))
        await db.flush()

        # 6. Delete all Devices
        device_del = await db.execute(delete(DeviceModel))
        print(f"    -> Deleted {device_del.rowcount} device(s).")

        # 7. Clean up dummy rider names in User account
        stmt_user = select(UserModel).where(UserModel.email == "hello@cybergenii.com")
        res_user = await db.execute(stmt_user)
        admin_user = res_user.scalar_one_or_none()
        if admin_user:
            admin_user.first_name = "System"
            admin_user.last_name = "Admin"
            admin_user.name = "System Admin"
            admin_user.username = "admin"
            print(f"    -> Normalized admin user '{admin_user.email}' (retained login credentials).")

        await db.commit()
        print("[+] All dummy data successfully removed from database!")

    await session_manager.close()


if __name__ == "__main__":
    asyncio.run(clear_data())
