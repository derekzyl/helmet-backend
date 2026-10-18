#!/usr/bin/env python3
"""
Seed Initial Fleet Data into the Smart Helmet Database
------------------------------------------------------
Populates:
- Admin / Rider User (hello@cybergenii.com)
- 3 Helmet Units & 3 Bike Ignition Units (paired)
- 4 Emergency Contacts (Spouse, Doctor, Fleet Manager, Brother)
- 5 Historical Safety Events (Collision, Alcohol lockout, Warning, SOS)
- 50 Telemetry GPS Trail Points for fleet map visualization
- Sends fleet activation email notification via configured SMTP mailer
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import sys

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.config.database.db import session_manager
from app.config.env import env
from app.core.contacts.models.model_contact import EmergencyContactModel
from app.core.devices.models.model_device import DeviceConfigModel, DeviceModel
from app.core.events.models.model_event import SafetyEventModel
from app.core.telemetry.models.model_telemetry import TelemetryModel
from app.core.users.models.model_user import UserModel
from app.utils.mail.mailer import EmailTemplateTypesEnum, SMTPMailer
from app.utils.password_hash import PassHash


async def seed_data():
    db_url = env.get("database_url") or "sqlite+aiosqlite:///smart_helmet.db"
    print(f"[*] Initializing database session with: {db_url}")
    session_manager.init(db_url, echo=False)

    async with session_manager.connect() as conn:
        await session_manager.create_all(conn)

    async with session_manager.session() as db:
        now = datetime.now(timezone.utc)

        # 1. Seed User
        print("[*] Checking / Seeding Admin & Rider User...")
        stmt_user = select(UserModel).where(UserModel.email == "hello@cybergenii.com")
        res_user = await db.execute(stmt_user)
        admin_user = res_user.scalar_one_or_none()
        if not admin_user:
            admin_user = UserModel(
                first_name="Alex",
                last_name="Rider",
                name="Alex Rider",
                username="alex_rider",
                email="hello@cybergenii.com",
                password=PassHash().hash_me("Password123!"),
                email_verified=True,
                user_type="ADMIN",
                allow_login=True,
                privacy_policy_accepted=True,
            )
            db.add(admin_user)
            await db.flush()
            print("    -> Admin user 'hello@cybergenii.com' created (Password: Password123!)")
        else:
            print(f"    -> User 'hello@cybergenii.com' exists (ID: {admin_user.id})")

        # 2. Seed Fleet Devices
        print("[*] Seeding Fleet Devices...")
        fleet_pairs = [
            ("HLM-2026-0001", "IGN-2026-0001", "Alex Rider (Primary)", 6.5244, 3.3792, 88),
            ("HLM-2026-0002", "IGN-2026-0002", "Dispatch Courier #4", 6.5310, 3.3850, 72),
            ("HLM-2026-0003", "IGN-2026-0003", "Security Patrol Unit", 6.5180, 3.3640, 95),
        ]

        created_devices = {}

        for hlm_sn, ign_sn, label, lat, lng, batt in fleet_pairs:
            # Check if Helmet exists
            stmt_hlm = select(DeviceModel).where(DeviceModel.serial_number == hlm_sn)
            res_hlm = await db.execute(stmt_hlm)
            hlm = res_hlm.scalar_one_or_none()

            # Check if Ignition exists
            stmt_ign = select(DeviceModel).where(DeviceModel.serial_number == ign_sn)
            res_ign = await db.execute(stmt_ign)
            ign = res_ign.scalar_one_or_none()

            if not hlm:
                hlm = DeviceModel(
                    serial_number=hlm_sn,
                    device_type="HELMET",
                    hardware_version="v1.2-38pin",
                    firmware_version="1.0.0",
                    label=f"{label} - Helmet",
                    status="ONLINE",
                    last_seen_at=now,
                    last_battery_pct=batt,
                    last_latitude=lat,
                    last_longitude=lng,
                    pairing_secret="4f8a3c9b7e12d456f890123456789abcdef0123456789abcdef0123456789abc",
                )
                db.add(hlm)
                await db.flush()
                db.add(DeviceConfigModel(device_id=hlm.id, alcohol_threshold_mg_l=0.05, collision_accel_g=3.5))

            if not ign:
                ign = DeviceModel(
                    serial_number=ign_sn,
                    device_type="IGNITION",
                    hardware_version="v1.0",
                    firmware_version="1.0.0",
                    label=f"{label} - Ignition Box",
                    status="ONLINE",
                    last_seen_at=now,
                    last_battery_pct=100,
                    last_latitude=lat,
                    last_longitude=lng,
                    pairing_secret="4f8a3c9b7e12d456f890123456789abcdef0123456789abcdef0123456789abc",
                )
                db.add(ign)
                await db.flush()
                db.add(DeviceConfigModel(device_id=ign.id))

            # Ensure paired
            hlm.paired_device_id = ign.id
            ign.paired_device_id = hlm.id
            created_devices[hlm_sn] = hlm
            created_devices[ign_sn] = ign
            print(f"    -> Synced fleet pair: {hlm_sn} <===> {ign_sn}")

        # 3. Seed Emergency Contacts
        primary_hlm = created_devices["HLM-2026-0001"]
        print("[*] Checking / Seeding Emergency Contacts...")
        contacts = [
            ("Dr. Sarah Vance", "+2348031112233", "Family Physician", True, True),
            ("Marcus Vance", "+2348024445566", "Brother", False, True),
            ("Fleet Operations Command", "+2348009998877", "Fleet Dispatch", True, True),
            ("General Hospital Trauma Center", "+2348011223344", "Emergency Services", False, True),
        ]
        stmt_c = select(EmergencyContactModel).where(EmergencyContactModel.device_id == primary_hlm.id)
        existing_contacts = (await db.execute(stmt_c)).scalars().all()
        if not existing_contacts:
            for name, phone, rel, notify_call, notify_sms in contacts:
                c = EmergencyContactModel(
                    device_id=primary_hlm.id,
                    user_id=admin_user.id if admin_user else None,
                    name=name,
                    phone_number=phone,
                    relationship=rel,
                    is_primary=(rel == "Family Physician"),
                    notify_call=notify_call,
                    notify_sms=notify_sms,
                )
                db.add(c)
            print("    -> Emergency contacts seeded successfully.")
        else:
            print(f"    -> {len(existing_contacts)} emergency contacts already exist.")

        # 4. Seed Safety Events
        print("[*] Seeding Safety Incidents & Alerts...")
        stmt_ev = select(SafetyEventModel).where(SafetyEventModel.device_id == primary_hlm.id)
        existing_events = (await db.execute(stmt_ev)).scalars().all()
        if not existing_events:
            events = [
                ("COLLISION", "CRITICAL", "High-G impact (4.8G) at Victoria Island intersection. SOS SMS sent.", 6.5240, 3.3790),
                ("ALCOHOL_LOCKOUT", "WARNING", "Alcohol reading 0.12 mg/L detected during pre-ride sequence. Ignition locked.", 6.5210, 3.3750),
                ("HELMET_REMOVED", "INFO", "Helmet IR sensor unbuckled while engine idling.", 6.5280, 3.3810),
                ("LINK_LOST", "WARNING", "RF local link timeout (>2000ms). SoftAP failover active.", 6.5300, 3.3830),
                ("MANUAL_OVERRIDE", "INFO", "Authenticated maintenance override executed via Mobile App.", 6.5244, 3.3792),
            ]
            for ev_type, sev, msg, lat, lng in events:
                ev = SafetyEventModel(
                    device_id=primary_hlm.id,
                    event_type=ev_type,
                    severity=sev,
                    message=msg,
                    latitude=lat,
                    longitude=lng,
                    acknowledged=(sev == "INFO"),
                )
                db.add(ev)
            print("    -> Safety incidents seeded.")
        else:
            print(f"    -> {len(existing_events)} safety events already exist.")

        # 5. Seed Telemetry Breadcrumbs
        print("[*] Seeding GPS Telemetry Breadcrumbs...")
        stmt_telem = select(TelemetryModel).where(TelemetryModel.device_id == primary_hlm.id)
        existing_telem = (await db.execute(stmt_telem)).scalars().all()
        if len(existing_telem) < 20:
            base_lat = 6.5244
            base_lng = 3.3792
            for i in range(50):
                t_time = now - timedelta(minutes=(50 - i) * 2)
                cur_lat = base_lat + (i * 0.0003) + (random.uniform(-0.0001, 0.0001))
                cur_lng = base_lng + (i * 0.0004) + (random.uniform(-0.0001, 0.0001))
                spd = 25.0 + (i % 25) + random.uniform(-2, 3)
                telem = TelemetryModel(
                    device_id=primary_hlm.id,
                    recorded_at=t_time,
                    latitude=cur_lat,
                    longitude=cur_lng,
                    altitude_m=20.0 + (i * 0.2),
                    speed_kmh=spd,
                    battery_pct=max(60, 95 - int(i * 0.4)),
                    battery_mv=3900 - int(i * 3),
                    alcohol_level_mg_l=0.008,
                    helmet_worn=True,
                    ignition_state="RUNNING_LATCHED",
                    link_state="CONNECTED",
                    hdop=1.0,
                    satellites=10,
                )
                db.add(telem)
            print("    -> 50 GPS telemetry points seeded.")
        else:
            print(f"    -> {len(existing_telem)} telemetry breadcrumbs already present.")

        await db.commit()
        print("[+] Database seeding complete and committed!")

        # 6. Test Email Notification
        if env.get("mail", {}).get("use_mail_service") or env.get("mail", {}).get("use_credentials"):
            print("[*] Dispatching fleet activation email...")
            try:
                mailer = SMTPMailer(
                    receiver_emails=["hello@cybergenii.com", "info@cybergenii.com"],
                    template_name=EmailTemplateTypesEnum.EMERGENCY_ALERT,
                    subject="🚀 Smart Helmet Live Fleet Initialized on Koyeb",
                    template_data={
                        "event_type": "FLEET_ONLINE",
                        "severity": "INFO",
                        "device_id": "HLM-2026-0001",
                        "message": "Live Smart Helmet cloud fleet has been successfully connected to big-mariejeanne-cybergenii-b60e7032.koyeb.app. All safety telemetry channels are active.",
                        "google_maps_url": "https://maps.google.com/?q=6.5244,3.3792",
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    },
                    background=False,
                )
                await mailer.send_mail()
                print("[+] Fleet activation notification email sent to hello@cybergenii.com & info@cybergenii.com!")
            except Exception as e:
                print(f"[!] Email notification notice: {e}")

    await session_manager.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
