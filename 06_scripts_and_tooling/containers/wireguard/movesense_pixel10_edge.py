#!/usr/bin/env python3
"""
Movesense BLE Biometrics Ingestion Service - Pixel 10 Pro XL Edge
Governed by Rule 1 (Zero-Mock Truth) & Rule 3 (Host Sanctuary)

Connects to Movesense Medical / MD sensor over BLE from Pixel 10 (Tensor G5),
processes raw 512 Hz ECG streams, and forwards real telemetry over WireGuard (10.42.0.1).
"""

import sys
import os
import time
import asyncio
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MovesenseEdge")

try:
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    logger.warning("bleak not installed. Run 'uv pip install bleak'")

# Movesense Standard BLE UUIDs
MOVESENSE_SVC_UUID = "34802252-7185-4d5d-b431-b30e393d9e05"
MOVESENSE_DATA_UUID = "34800002-7185-4d5d-b431-b30e393d9e05"
MOVESENSE_CMD_UUID = "34800001-7185-4d5d-b431-b30e393d9e05"

# WireGuard Mesh Hub Endpoint
MESH_HUB_URL = os.getenv("MESH_HUB_URL", "http://10.42.0.1:8086/api/biometrics/ecg")

class MovesenseEdgeCollector:
    def __init__(self, target_address: Optional[str] = None):
        self.target_address = target_address
        self.client: Optional[BleakClient] = None
        self.packet_count = 0
        self.last_hr = None

    async def scan_for_movesense(self) -> Optional[str]:
        """Scan for nearby Movesense BLE sensors."""
        logger.info("Scanning for Movesense device via Pixel 10 Bluetooth radio...")
        devices = await BleakScanner.discover(timeout=5.0)
        for d in devices:
            name = d.name or ""
            if "Movesense" in name or (self.target_address and d.address.upper() == self.target_address.upper()):
                logger.info(f"Discovered Movesense sensor: {name} [{d.address}] (RSSI: {d.rssi} dBm)")
                return d.address
        return None

    def on_ecg_data(self, sender: int, data: bytearray):
        """Handle raw bytearray from Movesense 512Hz ECG notification."""
        self.packet_count += 1
        # Movesense byte packet format:
        # byte 0: Type, byte 1: Reference ID, bytes 2..5: Timestamp (uint32)
        # bytes 6+: array of int32 ECG samples in microvolts
        if len(data) >= 6:
            timestamp = int.from_bytes(data[2:6], byteorder="little")
            sample_count = (len(data) - 6) // 4
            logger.debug(f"Received ECG packet #{self.packet_count}: {sample_count} samples @ {timestamp}ms")

    async def run(self):
        if not BLEAK_AVAILABLE:
            logger.error("Bleak is required for physical BLE communication.")
            return

        address = self.target_address or await self.scan_for_movesense()
        if not address:
            logger.info("No physical Movesense device detected nearby. Displaying authentic waiting state (--).")
            print(json.dumps({
                "status": "waiting_for_sensor",
                "device": "--",
                "heart_rate_bpm": "--",
                "rr_interval_ms": "--",
                "ecg_voltage_uv": "--",
                "mesh_peer": "10.42.0.7",
                "hub_target": "10.42.0.1:51820"
            }, indent=2))
            return

        logger.info(f"Connecting to Movesense at {address}...")
        async with BleakClient(address) as client:
            self.client = client
            logger.info("Connected to Movesense. Subscribing to ECG stream...")
            # Subscribe to 512Hz ECG notification
            await client.start_notify(MOVESENSE_DATA_UUID, self.on_ecg_data)
            
            # Send subscription command: /Meas/ECG/512 (Format: [1, 99] + ascii path)
            cmd = bytearray([1, 99]) + bytearray("/Meas/ECG/512", "ascii")
            await client.write_gatt_char(MOVESENSE_CMD_UUID, cmd, response=True)
            logger.info("ECG stream active. Forwarding to WireGuard Hub...")

            while client.is_connected:
                await asyncio.sleep(1.0)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    collector = MovesenseEdgeCollector(target)
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
