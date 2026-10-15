#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
screen_lens_scrcpy_manager.py
=============================
Screen Lens Sovereign — Scrcpy GUI & Device Mirroring Integration Engine.
Coordinates low-latency Android screen mirroring for Pixel 10 Pro XL (L6)
and Samsung Galaxy S20+ (L7) under the Screen Lens Sovereign runtime.

Governed by:
- Rule #0: Zero-Mock Empirical Truth
- Rule #7: Live Screen Broadcasting & Continuous Telemetry
- Rule #10: Screen Lens Sovereign Automation Invariant
"""

import os
import sys
import json
import time
import signal
import subprocess
from typing import Dict, List, Any, Optional

SCRCPY_BIN = "/Users/aaron/.local/bin/scrcpy"
DEVICE_PROFILES = {
    "l6_pixel": {
        "name": "Google Pixel 10 Pro XL (L6)",
        "serial": "192.168.8.114:5555",
        "alt_serials": ["100.73.38.87:5555", "5B080DLCQ001LQ"],
        "role": "Tensor G5 Edge TPU & 8K Vision Stream",
        "default_codec": "h265",
        "max_size": 1920,
        "max_fps": 60
    },
    "l7_samsung": {
        "name": "Samsung Galaxy S20+ (L7)",
        "serial": "adb-R3CN40CJJ1R-JKttZ1._adb-tls-connect._tcp",
        "alt_serials": ["192.168.8.131:5555", "100.84.40.95:5555", "R3CN40CJJ1R"],
        "role": "Dedicated Automated UI Testbench",
        "default_codec": "h264",
        "max_size": 1920,
        "max_fps": 60
    }
}

ACTIVE_PROCESSES: Dict[str, subprocess.Popen] = {}


def list_active_devices() -> List[Dict[str, Any]]:
    """Returns detected devices with online status and scrcpy readiness."""
    try:
        res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=2.0)
        lines = res.stdout.strip().split("\n")[1:]
    except Exception:
        lines = []

    devices = []
    for node_id, prof in DEVICE_PROFILES.items():
        matched_serial = None
        is_online = False
        candidates = [prof["serial"]] + prof["alt_serials"]

        for line in lines:
            if not line.strip() or "offline" in line or "unauthorized" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                ser = parts[0]
                if ser in candidates or (node_id == "l6_pixel" and "mustang" in line.lower()) or (node_id == "l7_samsung" and "y2s" in line.lower()):
                    matched_serial = ser
                    is_online = True
                    break

        devices.append({
            "node_id": node_id,
            "name": prof["name"],
            "role": prof["role"],
            "active_serial": matched_serial or prof["serial"],
            "online": is_online,
            "running_mirror": node_id in ACTIVE_PROCESSES and ACTIVE_PROCESSES[node_id].poll() is None
        })
    return devices


def launch_mirror(node_id: str, turn_screen_off: bool = False, stay_awake: bool = True, otg_mode: bool = False) -> Dict[str, Any]:
    """Launches an optimized scrcpy session for the specified device (mirror or OTG mode)."""
    if node_id not in DEVICE_PROFILES:
        return {"status": "error", "message": f"Unknown node: {node_id}"}

    prof = DEVICE_PROFILES[node_id]
    devices = {d["node_id"]: d for d in list_active_devices()}
    dev_info = devices.get(node_id, {})
    if not dev_info.get("online"):
        return {"status": "error", "message": f"Device {prof['name']} is not online in ADB"}

    serial = dev_info["active_serial"]

    # Check if already running
    if node_id in ACTIVE_PROCESSES and ACTIVE_PROCESSES[node_id].poll() is None:
        return {"status": "running", "message": "Scrcpy session already active", "pid": ACTIVE_PROCESSES[node_id].pid}

    if otg_mode:
        cmd = [
            SCRCPY_BIN,
            "-s", serial,
            f"--window-title={prof['name']} (Screen Lens OTG Mode)",
            "--otg",
            "--pause-on-exit=if-error"
        ]
    else:
        cmd = [
            SCRCPY_BIN,
            "-s", serial,
            f"--window-title={prof['name']} (Screen Lens Sovereign)",
            f"--video-codec={prof['default_codec']}",
            f"--max-size={prof['max_size']}",
            f"--max-fps={prof['max_fps']}",
            "--no-audio"
        ]

        if turn_screen_off:
            cmd.append("--turn-screen-off")
        if stay_awake:
            cmd.append("--stay-awake")

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ACTIVE_PROCESSES[node_id] = proc
        mode_label = "OTG mode" if otg_mode else "mirror"
        return {
            "status": "success",
            "message": f"Launched scrcpy {mode_label} for {prof['name']}",
            "pid": proc.pid,
            "serial": serial,
            "otg_mode": otg_mode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def launch_otg(node_id: str) -> Dict[str, Any]:
    """Launches an optimized OTG (UHID hardware keyboard/mouse) session."""
    return launch_mirror(node_id, otg_mode=True)


def stop_mirror(node_id: str) -> Dict[str, Any]:
    """Stops the active scrcpy session for a given device."""
    if node_id in ACTIVE_PROCESSES:
        proc = ACTIVE_PROCESSES[node_id]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except Exception:
                proc.kill()
        del ACTIVE_PROCESSES[node_id]
        return {"status": "success", "message": f"Stopped mirror for {node_id}"}
    return {"status": "not_running", "message": f"No active mirror for {node_id}"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Screen Lens Sovereign Scrcpy Integration")
    parser.add_argument("--list", action="store_true", help="List active devices")
    parser.add_argument("--launch", choices=["l6_pixel", "l7_samsung"], help="Launch scrcpy mirror")
    parser.add_argument("--stop", choices=["l6_pixel", "l7_samsung"], help="Stop scrcpy mirror")
    parser.add_argument("--screen-off", action="store_true", help="Turn physical screen off while mirroring")
    parser.add_argument("--otg", action="store_true", help="Launch in OTG mode (UHID hardware keyboard/mouse emulation)")
    args = parser.parse_args()

    if args.list or len(sys.argv) == 1:
        devs = list_active_devices()
        print(json.dumps(devs, indent=2))
    elif args.launch:
        res = launch_mirror(args.launch, turn_screen_off=args.screen_off, otg_mode=args.otg)
        print(json.dumps(res, indent=2))
    elif args.stop:
        res = stop_mirror(args.stop)
        print(json.dumps(res, indent=2))
