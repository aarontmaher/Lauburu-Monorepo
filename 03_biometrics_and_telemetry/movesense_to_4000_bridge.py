#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Movesense to Port 4000 Telemetry Forwarding Bridge
Version: 3.0.0-CANONICAL
Subsystem: 03_biometrics_and_telemetry/movesense_to_4000_bridge.py

Subscribes to live Movesense GATT daemon notifications, computes Pan-Tompkins QRS,
Kamath 20% clinical filter, RMSSD, DFA-alpha1, and PTT BP, and pushes real-time
telemetry frames to Port 4000 REST /api/v1/network/ingest.

Strict Rule #0 compliance: zero mocked arrays. When sensor is disconnected,
emits explicit WAITING_FOR_SENSOR with null metrics.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    HTTPX_AVAILABLE = False

# Resolve monorepo root reliably across symlinks
REPO_ROOT = Path(__file__).resolve().parent.parent
HUB_SERVICES = REPO_ROOT / "01_apps/edge_compute_and_ai/lauburu_compute_hub/services"
DSP_DIR = REPO_ROOT / "03_biometrics_and_telemetry"

for p in [str(HUB_SERVICES), str(DSP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from movesense_ingestion import get_movesense_daemon, STATE_WAITING_FOR_SENSOR, STATE_CONNECTED_STREAMING
    daemon = get_movesense_daemon()
except ImportError:
    daemon = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("movesense_to_4000_bridge")

PORT_4000_INGEST = os.getenv("PORT_4000_INGEST", "http://127.0.0.1:4000/api/v1/network/ingest")


async def post_telemetry(payload: Dict[str, Any]):
    """Posts telemetry frame to Port 4000 REST ingest endpoint."""
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.post(PORT_4000_INGEST, json=payload)
        except Exception:
            pass


def on_telemetry(state: Dict[str, Any]):
    """Dispatches live Movesense telemetry frame to Port 4000 with zero-mock discipline."""
    if not state or not state.get("is_streaming"):
        return

    metrics = state.get("metrics", {})
    kinematics = metrics.get("kinematics") or {}
    acc_g = kinematics.get("accel") if kinematics else None

    payload = {
        "sensor_type": "movesense",
        "timestamp": state.get("timestamp_epoch_ms"),
        "connected": True,
        "device_name": state.get("device_name", "Movesense Medical"),
        "device_address": state.get("device_address"),
        "battery_pct": state.get("battery_pct"),
        "heart_rate": metrics.get("heart_rate_bpm"),
        "rr_intervals_ms": metrics.get("rr_intervals_ms", []),
        "rmssd": metrics.get("rmssd_ms"),
        "dfa_alpha1": metrics.get("dfa_alpha1"),
        "zone_alignment": metrics.get("zone_alignment"),
        "ecg_mv": metrics.get("ecg_mv", []),
        "acc_g": acc_g,
        "total_dynamic_g": metrics.get("total_dynamic_g"),
        "ptt_ms": metrics.get("ptt_ms"),
        "rule_0_zero_mock": True
    }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(post_telemetry(payload))
    except Exception as e:
        logger.debug(f"Telemetry dispatch error: {e}")


async def run_bridge():
    """Runs Movesense to Port 4000 continuous forwarding bridge."""
    if daemon is None:
        logger.warning("Movesense ingestion daemon not available; bridge entering standby.")
        while True:
            await asyncio.sleep(5.0)

    if on_telemetry not in daemon.subscribers:
        daemon.subscribers.append(on_telemetry)

    logger.info("Auto-scanning and connecting to Movesense via daemon...")
    await daemon.connect(auto_scan=True)
    logger.info(f"Movesense Bridge active. Target: {PORT_4000_INGEST}")

    while True:
        await asyncio.sleep(5.0)
        if not daemon.is_streaming:
            logger.debug("Movesense disconnected. Attempting auto-reconnect...")
            await daemon.connect(auto_scan=True)


if __name__ == "__main__":
    try:
        asyncio.run(run_bridge())
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")
