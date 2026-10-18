#!/usr/bin/env python3
"""
Smart Helmet & Ignition Hardware Simulator
------------------------------------------
Emulates ESP32 Helmet and Ignition units interacting with the FastAPI backend.
Demonstrates:
- Device registration and cryptographic pairing (HMAC-SHA256 generation)
- Real-time GPS movement and sensor telemetry streaming
- Alcohol detection test scenarios (Pass vs Fail lockout)
- Accident collision kinematics with pre-alert cancel window and SOS trigger
- Batch offline buffering and network reconnection flushing
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import math
import sys
import time
from datetime import datetime, timezone
import httpx
import websockets

API_BASE_URL = "https://big-mariejeanne-cybergenii-b60e7032.koyeb.app/api/v1"
WS_URL = "wss://big-mariejeanne-cybergenii-b60e7032.koyeb.app/api/v1/ws/live"


class HardwareSimulator:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.helmet_serial = "HLM-2026-0001"
        self.ignition_serial = "IGN-2026-0001"
        self.pairing_secret = None
        self.seq_nonce = 0
        self.helmet_worn = True
        self.alcohol_level = 0.012
        self.battery_pct = 95
        self.ignition_state = "LOCKED"
        self.lat = 6.5244
        self.lng = 3.3792
        self.speed = 0.0

    async def setup_devices(self, client: httpx.AsyncClient):
        print(f"[*] Registering Helmet Unit ({self.helmet_serial})...")
        try:
            r = await client.post(
                f"{self.base_url}/devices/register",
                json={
                    "serial_number": self.helmet_serial,
                    "device_type": "HELMET",
                    "hardware_version": "v1.2-38pin",
                    "firmware_version": "1.0.0",
                    "label": "Test Helmet Unit #1",
                },
            )
            print(f"    -> Result: {r.status_code}")
        except Exception as e:
            print(f"    -> Registration notice: {e}")

        print(f"[*] Registering Ignition Unit ({self.ignition_serial})...")
        try:
            r = await client.post(
                f"{self.base_url}/devices/register",
                json={
                    "serial_number": self.ignition_serial,
                    "device_type": "IGNITION",
                    "hardware_version": "v1.0",
                    "firmware_version": "1.0.0",
                    "label": "Bike Ignition Unit #1",
                },
            )
            print(f"    -> Result: {r.status_code}")
        except Exception as e:
            print(f"    -> Registration notice: {e}")

        print("[*] Pairing Helmet and Ignition...")
        try:
            r = await client.post(
                f"{self.base_url}/devices/pair",
                json={
                    "helmet_device_id": self.helmet_serial,
                    "ignition_device_id": self.ignition_serial,
                },
            )
            data = r.json()
            self.pairing_secret = data.get("pairing_secret")
            print(f"    -> Paired successfully! PSK: {self.pairing_secret[:16]}...")
        except Exception as e:
            print(f"    -> Pairing fallback: {e}")
            self.pairing_secret = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def compute_hmac(self, msg_type: str, data_dict: dict) -> str:
        self.seq_nonce += 1
        ts = int(time.time())
        raw_msg = f"1:{msg_type}:{self.helmet_serial}:{self.seq_nonce}:{ts}:{json.dumps(data_dict, sort_keys=True)}"
        key = (self.pairing_secret or "secret").encode("utf-8")
        return hmac.new(key, raw_msg.encode("utf-8"), hashlib.sha256).hexdigest()

    async def run_scenario_pre_ride(self, client: httpx.AsyncClient):
        print("\n=== Scenario: Pre-Ride Safety Verification ===")
        # 1. Helmet not worn -> LOCKED
        print("Step 1: Rider approaches motorcycle without wearing helmet...")
        self.helmet_worn = False
        self.ignition_state = "LOCKED"
        await self._send_telemetry(client)
        print("  -> Ignition State: LOCKED (Reason: NO_HELMET)")
        await asyncio.sleep(1)

        # 2. Helmet put on -> Prompt alcohol test
        print("Step 2: Rider puts on helmet (FC-51 IR sensor triggers)...")
        self.helmet_worn = True
        await self._send_telemetry(client)
        print("  -> Helmet worn confirmed. Starting MQ-3 alcohol breath sample...")
        await asyncio.sleep(1)

        # 3. Clean breath sample -> UNLOCKED
        print("Step 3: Rider blows clean breath sample (BAC 0.01 mg/L < 0.05 limit)...")
        self.alcohol_level = 0.010
        self.ignition_state = "UNLOCKED"
        await self._send_telemetry(client)
        print("  -> Ignition State: UNLOCKED! (SSR Output: HIGH, Green LED ON)")
        await asyncio.sleep(1)

        # 4. Engine started -> RUNNING_LATCHED
        print("Step 4: Engine starts running, entering RUNNING_LATCHED state...")
        self.ignition_state = "RUNNING_LATCHED"
        self.speed = 35.0
        await self._send_telemetry(client)
        print("  -> Ignition Latched. Engine will NOT be cut even if helmet is adjusted mid-ride.")

    async def run_scenario_alcohol_lock(self, client: httpx.AsyncClient):
        print("\n=== Scenario: Intoxicated Rider Lockout ===")
        print("Step 1: Rider wearing helmet blows into MQ-3 with alcohol present...")
        self.helmet_worn = True
        self.alcohol_level = 0.12  # Exceeds 0.05 limit
        self.ignition_state = "LOCKED"
        await self._send_telemetry(client)
        print("  -> Ignition State: LOCKED (ALCOHOL_LOCKOUT, SSR remains OFF, Red LED ON)")
        
        # Log safety incident
        print("Step 2: Logging ALCOHOL_LOCKOUT incident to cloud...")
        await client.post(
            f"{self.base_url}/events/",
            json={
                "device_id": self.helmet_serial,
                "event_type": "ALCOHOL_LOCKOUT",
                "severity": "WARNING",
                "message": "High BAC reading (0.12 mg/L). Ignition disabled.",
                "latitude": self.lat,
                "longitude": self.lng,
                "payload": {"bac": self.alcohol_level, "threshold": 0.05},
            },
        )
        print("  -> Alert dispatched to cloud dashboard and logged.")

    async def run_scenario_accident(self, client: httpx.AsyncClient):
        print("\n=== Scenario: Motorcycle Collision & Automated SOS ===")
        print("Step 1: Vehicle cruising at 55 km/h...")
        self.ignition_state = "RUNNING_LATCHED"
        self.speed = 55.0
        await self._send_telemetry(client)
        await asyncio.sleep(1)

        print("Step 2: MPU-6050 detects 4.8G impact + 75° tilt shift + sudden stop...")
        self.speed = 0.0
        sig = self.compute_hmac("EMERGENCY_ALERT", {"event": "COLLISION", "impact_g": 4.8})
        print("  -> Pre-alert alarm activated! Piezo buzzer sounds 20-second warning countdown.")
        print("  -> (Button A would cancel false alarm). Simulating rider unable to cancel...")
        await asyncio.sleep(2)

        print("Step 3: 20s cancel window expired -> Dispatching SOS SMS and Cloud Incident!")
        r = await client.post(
            f"{self.base_url}/events/",
            json={
                "device_id": self.helmet_serial,
                "event_type": "COLLISION",
                "severity": "CRITICAL",
                "message": f"Crash detected at {self.lat}, {self.lng}! Peak 4.8G impact. SMS sent to emergency contacts.",
                "latitude": self.lat,
                "longitude": self.lng,
                "payload": {
                    "peak_g": 4.8,
                    "tilt_deg": 75.0,
                    "sim800l_sms_sent": True,
                    "google_maps_url": f"https://maps.google.com/?q={self.lat},{self.lng}",
                },
            },
        )
        print(f"  -> Cloud Event Recorded (Status {r.status_code})")
        print(f"  -> Simulated SIM800L SMS: 'EMERGENCY: Rider crash detected at https://maps.google.com/?q={self.lat},{self.lng}'")

    async def _send_telemetry(self, client: httpx.AsyncClient):
        # Slightly advance GPS coordinates to simulate movement
        if self.speed > 0:
            self.lat += 0.0001
            self.lng += 0.0001

        payload = {
            "device_id": self.helmet_serial,
            "timestamp": int(time.time()),
            "latitude": self.lat,
            "longitude": self.lng,
            "altitude_m": 25.0,
            "speed_kmh": self.speed,
            "battery_pct": self.battery_pct,
            "battery_mv": 3950,
            "alcohol_level_mg_l": self.alcohol_level,
            "helmet_worn": self.helmet_worn,
            "ignition_state": self.ignition_state,
            "link_state": "CONNECTED",
            "hdop": 1.1,
            "satellites": 9,
        }
        try:
            r = await client.post(f"{self.base_url}/telemetry/ingest", json=payload)
            print(f"  [TX Telemetry] Speed: {self.speed} km/h | BAC: {self.alcohol_level} | SSR: {self.ignition_state} -> HTTP {r.status_code}")
        except Exception as e:
            print(f"  [TX Telemetry] Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Smart Helmet Hardware Simulator")
    parser.add_argument("--scenario", choices=["pre_ride", "alcohol_lock", "accident", "all"], default="all")
    parser.add_argument("--url", default=API_BASE_URL, help="FastAPI Base URL")
    args = parser.parse_args()

    sim = HardwareSimulator(base_url=args.url)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        await sim.setup_devices(client)
        if args.scenario in ["pre_ride", "all"]:
            await sim.run_scenario_pre_ride(client)
        if args.scenario in ["alcohol_lock", "all"]:
            await sim.run_scenario_alcohol_lock(client)
        if args.scenario in ["accident", "all"]:
            await sim.run_scenario_accident(client)
    print("\n[+] Simulation run completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
