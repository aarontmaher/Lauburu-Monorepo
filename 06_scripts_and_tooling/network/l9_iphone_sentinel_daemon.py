#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lauburu Mesh - L9 iPhone 16 Pro Node Sentinel Daemon
====================================================
Subsystem: 06_scripts_and_tooling/network/l9_iphone_sentinel_daemon.py
Maintains continuous discovery, telemetry, and status tracking for L9 (iPhone 16 Pro, A18 Pro).
Monitors:
  - Tailscale Layer 3 WireGuard overlay (100.122.52.89)
  - CoreDevice Pairing & USB Physical Link (xcrun devicectl)
  - Bluetooth Layer 0 Proximity Link (74:cc:40:20:8e:10)
  - Interactive iSH SSH Listener (Port 2222)
Governed by Rule #0 (Zero-Mock) and Rule #1 (Tri-Proof Empirical Telemetry).
"""

import os
import sys
import json
import time
import socket
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "00_MASTER_INFRASTRUCTURE_TOPOLOGY"
STATUS_FILE = OBSIDIAN_DIR / "IPHONE_16_PRO_NODE_STATUS.md"
TELEMETRY_LOG = REPO_ROOT / "obsidian_vault" / "APPS_AND_FEATURES" / "MESH_TELEMETRY_LOG.md"

UDID = "00008140-00015D5E3EFA801C"
COREDEVICE_ID = "AE1D33CE-4249-5E2C-B866-FE3BD627D575"
TAILSCALE_IP = "100.122.52.89"
LOCAL_IP = "192.168.8.102"
BT_MAC = "74:cc:40:20:8e:10"
SSH_PORT = 2222
RPC_PORT = 50052

def test_socket(host: str, port: int, timeout_sec: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def check_ping(ip: str, timeout_ms: int = 500) -> tuple[bool, str]:
    try:
        res = subprocess.run(["ping", "-c", "1", "-W", str(timeout_ms), ip], capture_output=True, text=True, timeout=1.0)
        if res.returncode == 0:
            time_ms = res.stdout.split("time=")[1].split(" ")[0] if "time=" in res.stdout else "<1"
            return True, f"{time_ms} ms"
    except Exception:
        pass
    return False, "TIMEOUT"

def check_coredevice() -> tuple[bool, str]:
    try:
        res = subprocess.run(["xcrun", "devicectl", "list", "devices"], capture_output=True, text=True, timeout=3.0)
        if res.returncode == 0 and COREDEVICE_ID in res.stdout:
            state = "paired (available)" if "available" in res.stdout else "paired (standby)"
            return True, state
    except Exception:
        pass
    return False, "UNPAIRED"

def check_bluetooth() -> bool:
    blueutil = "/Users/aaron/.local/bin/blueutil"
    if os.path.exists(blueutil):
        try:
            res = subprocess.run([blueutil, "--paired"], capture_output=True, text=True, timeout=1.5)
            clean_mac = BT_MAC.replace(":", "-").lower()
            return clean_mac in res.stdout.lower() or BT_MAC.lower() in res.stdout.lower()
        except Exception:
            pass
    return False

def probe_l9_status() -> dict:
    ts_ok, ts_rtt = check_ping(TAILSCALE_IP)
    cd_ok, cd_state = check_coredevice()
    bt_ok = check_bluetooth()
    ssh_ok = test_socket(TAILSCALE_IP, SSH_PORT) if ts_ok else False
    rpc_ok = test_socket(TAILSCALE_IP, RPC_PORT) if ts_ok else False

    is_online = ts_ok or cd_ok

    status_data = {
        "node_id": "l9_iphone_16",
        "name": "iPhone 16 Pro (L9)",
        "marketing_name": "iPhone 16 Pro",
        "product_type": "iPhone17,1",
        "silicon": "Apple A18 Pro (6C CPU / 6C GPU / 16C Neural Engine)",
        "npu_tops": 35.0,
        "ram_gb": 8.0,
        "tailscale_ip": TAILSCALE_IP,
        "tailscale_online": ts_ok,
        "tailscale_rtt": ts_rtt,
        "coredevice_paired": cd_ok,
        "coredevice_state": cd_state,
        "bluetooth_mac": BT_MAC,
        "bluetooth_paired": bt_ok,
        "ssh_listener_2222": ssh_ok,
        "rpc_listener_50052": rpc_ok,
        "online": is_online,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Write Markdown Status
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    report = f"""---
title: "iPhone 16 Pro (L9 Active Mesh Node) Status"
tags: [mesh, iphone16pro, l9, edge_node, a18_pro, tailscale, coredevice]
---

# 🍎 iPhone 16 Pro Node Status (L9)
> **Last Checked:** `{status_data['timestamp']}`  
> **Silicon:** `Apple A18 Pro (6-Core CPU / 6-Core GPU / 16-Core Neural Engine 35 TOPS)`  
> **Unified Memory:** `8.0 GB LPDDR5X`  
> **Role:** `Primary iOS Testing Node & Screen Lens Commerce Target`

## 🌐 Connectivity Matrix
- **Tailscale Layer 3 (`{TAILSCALE_IP}`):** {"🟢 ACTIVE (" + ts_rtt + ")" if ts_ok else "🟡 SLEEP / STANDBY"}
- **CoreDevice Bridge (`{COREDEVICE_ID}`):** {"🟢 " + cd_state.upper() if cd_ok else "🔴 UNPAIRED"}
- **Bluetooth Layer 0 (`{BT_MAC}`):** {"🟢 PAIRED / VERIFIED" if bt_ok else "🟡 STANDBY"}
- **iSH SSH Daemon (:2222):** {"🟢 LISTENING" if ssh_ok else "⚪ INACTIVE (Install iSH on iOS for full SSH)"}
- **prima.cpp RPC Worker (:50052):** {"🟢 LISTENING" if rpc_ok else "⚪ STANDBY"}

## 📱 Hardware & Identifiers
- **Apple Identifier:** `iPhone17,1` (Model: `D93AP`)
- **UDID:** `{UDID}`
- **CoreDevice ID:** `{COREDEVICE_ID}`
- **Overall Node Status:** {"🟢 ACTIVE MESH NODE" if is_online else "🟡 STANDBY"}
"""
    with open(STATUS_FILE, "w") as f:
        f.write(report)

    return status_data

def run_daemon(poll_interval: int = 15):
    print(f"[L9_SENTINEL] Started background watcher for iPhone 16 Pro (poll: {poll_interval}s)...")
    while True:
        try:
            res = probe_l9_status()
            ts_str = "ONLINE" if res["tailscale_online"] else "SLEEP"
            cd_str = res["coredevice_state"]
            print(f"[L9_SENTINEL] Telemetry updated: TS={ts_str} | CoreDevice={cd_str} | Overall={'ACTIVE' if res['online'] else 'STANDBY'}")
        except Exception as e:
            print(f"[L9_SENTINEL] Probe error: {e}")
        time.sleep(poll_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="L9 iPhone 16 Pro Node Sentinel")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a background daemon")
    parser.add_argument("--interval", type=int, default=15, help="Poll interval in seconds")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.interval)
    else:
        result = probe_l9_status()
        print(json.dumps(result, indent=2))
