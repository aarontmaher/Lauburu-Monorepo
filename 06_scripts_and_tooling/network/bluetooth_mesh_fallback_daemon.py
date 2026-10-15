#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bluetooth Mesh Fallback & Resurrection Daemon
============================================
Autonomous background daemon maintaining Layer 0 Bluetooth presence,
IP-less fallback, and out-of-band node resurrection.
"""

import os
import sys
import time
import json
import socket
import datetime
import subprocess
from pathlib import Path

# Setup paths
REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
OBSIDIAN_AUDIT = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "BLUETOOTH_MESH_SELF_HEALING_AUDIT.md"
BLUEUTIL_PATH = "/Users/aaron/.local/bin/blueutil"

OBSIDIAN_AUDIT.parent.mkdir(parents=True, exist_ok=True)

# Hardware Registry
BT_DEVICES = {
    "GW_GLiNet_Router": {"mac": "8c-86-dd-00-26-41", "name": "Lauburu-Mesh-Gateway (GW)", "is_nap": True},
    "L3_Linux_Hub": {"mac": "00-41-0e-14-28-44", "name": "Linux Head Node (L3)"},
    "L4_Linux_Tablet": {"mac": "00-03-7f-c2-00-43", "name": "Linux Tablet (L4)"},
    "L6_Pixel_10": {"mac": "30-e0-44-6d-18-ec", "name": "Pixel 10 Pro XL (L6)"},
    "L7_Samsung_S20": {"mac": "5c-cb-99-05-81-41", "name": "Samsung Galaxy S20+ (L7)"},
    "L5_MacBook_Air": {"mac": "2c-ca-16-08-c0-27", "name": "MacBook Air M4 (L5)"},
    "L2_MacBook_Pro": {"mac": "dc-29-55-d6-fc-0b", "name": "MacBook Pro Intel (L2)"},
    "L9_iPhone_16_Pro": {"mac": "74-cc-40-20-8e-10", "name": "iPhone 16 Pro Node (L9)"}
}

def log_event(entry: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OBSIDIAN_AUDIT, "a") as f:
        f.write(f"- `[{timestamp}]` {entry}\n")

def check_bt_connected(mac: str) -> bool:
    if not os.path.exists(BLUEUTIL_PATH):
        return False
    try:
        res = subprocess.run([BLUEUTIL_PATH, "--is-connected", mac], capture_output=True, text=True, timeout=2)
        return res.returncode == 0 and res.stdout.strip() == "1"
    except Exception:
        return False

def reconnect_bt(mac: str) -> bool:
    if not os.path.exists(BLUEUTIL_PATH):
        return False
    try:
        subprocess.run([BLUEUTIL_PATH, "--pair", mac], capture_output=True, timeout=4)
        res = subprocess.run([BLUEUTIL_PATH, "--connect", mac], capture_output=True, text=True, timeout=4)
        return res.returncode == 0
    except Exception:
        return False

def audit_cycle():
    statuses = {}
    for dev_id, info in BT_DEVICES.items():
        mac = info["mac"]
        is_conn = check_bt_connected(mac)
        
        # If not connected, attempt gentle Layer-0 Bluetooth handshake
        if not is_conn:
            reconnect_bt(mac)
            is_conn = check_bt_connected(mac)
            
        statuses[dev_id] = {
            "name": info["name"],
            "mac": mac,
            "connected": is_conn
        }
        
    log_event(f"Audit Cycle: {sum(1 for s in statuses.values() if s.get('connected'))}/{len(statuses)} BT nodes active.")
    return statuses

def main():
    print("[DAEMON] Starting Bluetooth Mesh Fallback & Resurrection Daemon...")
    res = audit_cycle()
    print("[DAEMON] Initial audit complete:", json.dumps(res, indent=2))
    if "--once" in sys.argv:
        return
    while True:
        try:
            audit_cycle()
        except Exception as e:
            pass
        time.sleep(300)

if __name__ == "__main__":
    main()
