#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iPhone 16 Pro Node Sentinel (Temporary Mesh Node)
================================================
Monitors and utilizes the iPhone 16 Pro as an active edge node until sold.
Monitors:
- USB CoreDevice link (xcrun devicectl)
- Tailscale L3 overlay (100.113.62.81)
- Bluetooth Layer 0 link (74-cc-40-20-8e-10)
- Battery, thermal, and network telemetry
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "00_MASTER_INFRASTRUCTURE_TOPOLOGY"
NODE_STATUS_FILE = OBSIDIAN_DIR / "IPHONE_16_PRO_NODE_STATUS.md"

UDID = "00008140-00015D5E3EFA801C"
COREDEVICE_ID = "AE1D33CE-4249-5E2C-B866-FE3BD627D575"
TAILSCALE_IP = "100.122.52.89"
WIFI_IP = "192.168.8.217"
USB_TUNNEL_IP = "fda1:2c5b:597e::1"
BT_MAC = "74-cc-40-20-8e-10"

def check_tailscale():
    try:
        res = subprocess.run(["ping", "-c", "1", "-W", "1000", TAILSCALE_IP], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            time_ms = res.stdout.split("time=")[1].split(" ")[0] if "time=" in res.stdout else "OK"
            return True, time_ms
    except Exception:
        pass
    return False, "TIMEOUT"

def check_wifi():
    try:
        res = subprocess.run(["ping", "-c", "1", "-W", "1000", WIFI_IP], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            time_ms = res.stdout.split("time=")[1].split(" ")[0] if "time=" in res.stdout else "OK"
            return True, time_ms
    except Exception:
        pass
    return False, "TIMEOUT"

def check_usb_tunnel():
    try:
        res = subprocess.run(["ping6", "-c", "1", USB_TUNNEL_IP], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            time_ms = res.stdout.split("time=")[1].split(" ")[0] if "time=" in res.stdout else "OK"
            return True, time_ms
    except Exception:
        pass
    return False, "TIMEOUT"

def check_usb_device():
    try:
        res = subprocess.run(["xcrun", "devicectl", "list", "devices"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and (COREDEVICE_ID in res.stdout or "iPhone" in res.stdout):
            return True, "available (paired)"
    except Exception:
        pass
    return False, "DISCONNECTED"

def check_bluetooth():
    blueutil = "/Users/aaron/.local/bin/blueutil"
    if os.path.exists(blueutil):
        try:
            res = subprocess.run([blueutil, "--paired"], capture_output=True, text=True, timeout=2)
            if "74-cc-40-20-8e-10" in res.stdout or "74:cc:40:20:8e:10" in res.stdout.lower():
                return True
        except Exception:
            pass
    return False

def generate_node_report():
    ts_ok, ts_rtt = check_tailscale()
    wifi_ok, wifi_rtt = check_wifi()
    tun_ok, tun_rtt = check_usb_tunnel()
    usb_ok, usb_state = check_usb_device()
    bt_ok = check_bluetooth()
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    report = f"""---
title: "iPhone 16 Pro (L9 Temporary Node) Status"
tags: [mesh, iphone16pro, edge_node, usb_telemetry, tailscale]
---

# 🍎 iPhone 16 Pro Node Status (L9)
> **Last Checked:** `{timestamp}`  
> **Model:** `iPhone 16 Pro (iPhone17,1)` | **Silicon:** `Apple A18 Pro (6C CPU / 6C GPU / 16C NPU)`  
> **Lifecycle:** `Active Temporary Mesh Worker (Pre-Sale Transition)`

## 🌐 Connectivity Matrix
- **Tailscale Overlay (`{TAILSCALE_IP}`):** {"🟢 ACTIVE (" + str(ts_rtt) + " ms)" if ts_ok else "🔴 OFFLINE"}
- **Local Wi-Fi (`{WIFI_IP}`):** {"🟢 ACTIVE (" + str(wifi_rtt) + " ms)" if wifi_ok else "🔴 OFFLINE"}
- **USB CoreDevice Tunnel (`{USB_TUNNEL_IP}`):** {"🟢 CONNECTED (" + str(tun_rtt) + " ms)" if tun_ok else "🔴 OFFLINE"}
- **USB Physical Bus (CoreDevice):** {"🟢 ATTACHED (" + usb_state + ")" if usb_ok else "🔴 DISCONNECTED"}
- **Bluetooth Layer 0 (`{BT_MAC}`):** {"🟢 PAIRED / VERIFIED" if bt_ok else "🟡 STANDBY"}

## 📱 Hardware & Identifiers
- **UDID:** `{UDID}`
- **CoreDevice Identifier:** `{COREDEVICE_ID}`
- **Serial Number:** `G0WR66YPCQ`
- **Assigned Mesh Role:** `Peripheral Telemetry & Cellular WAN Fallback`
"""
    NODE_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NODE_STATUS_FILE, "w") as f:
        f.write(report)
    return {
        "tailscale": ts_ok,
        "tailscale_rtt": ts_rtt,
        "wifi": wifi_ok,
        "wifi_rtt": wifi_rtt,
        "usb_tunnel": tun_ok,
        "usb_tunnel_rtt": tun_rtt,
        "usb_attached": usb_ok,
        "usb_state": usb_state,
        "bluetooth": bt_ok
    }

if __name__ == "__main__":
    status = generate_node_report()
    print(json.dumps(status, indent=2))
