#!/usr/bin/env python3
"""
06_scripts_and_tooling/mesh/wol_manager.py
=========================================
Lauburu Wake-on-LAN (WoL) Fleet Engine, Web API & Obsidian Dashboard
-------------------------------------------------------------------
1. Transmits RFC 792 / UDP Magic Packets (UDP port 9 / 7) to wake sleeping nodes.
2. Manages real hardware MAC address registry across all 7 mesh devices.
3. Automatically syncs an interactive Obsidian Dashboard in DFS_UNIFIED.
4. Exposes REST API on port 18802 (and localhost:3000 proxy).
"""

import os
import sys
import json
import time
import socket
import logging
import argparse
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WoLManager]: %(message)s"
)
logger = logging.getLogger("WoLManager")

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OBSIDIAN_VAULT = Path("/Users/aaron/DFS_UNIFIED/00_SYSTEM_DASHBOARDS")
DASHBOARD_FILE = OBSIDIAN_VAULT / "WAKE_ON_LAN_CLUSTER.md"
STATUS_FILE = REPO_ROOT / "data/mesh/wol_status.json"

DEVICES = {
    "macbook_pro_vault": {
        "name": "MacBook Pro Vault",
        "mac": "a4:83:e7:d1:7c:82",
        "alt_mac": "82:e6:6d:c0:a4:01",
        "ip": "192.168.8.127",
        "tailscale": "100.103.212.21",
        "role": "Storage & Compute Vault (16 GB Unified RAM)",
        "icon": "💻"
    },
    "linux_head_node": {
        "name": "Linux Head Node (AMD Ryzen 7)",
        "mac": "00:41:0e:14:28:43",
        "ip": "192.168.8.224",
        "tailscale": "100.101.39.98",
        "role": "Continuous AI Training & LoRA Harvest (16 Threads)",
        "icon": "🐧"
    },
    "macbook_air": {
        "name": "MacBook Air M2 Node",
        "mac": "66:74:75:d8:16:fb",
        "ip": "192.168.8.222",
        "tailscale": "100.93.158.96",
        "role": "Mobile AI Agent Worker (8 Cores)",
        "icon": "🍏"
    },
    "mac_mini_host": {
        "name": "Host Mac Mini M4",
        "mac": "1c:f6:4c:7d:d7:0a",
        "alt_mac": "1c:f6:4c:7c:dc:5f",
        "ip": "192.168.8.230",
        "tailscale": "100.119.199.76",
        "role": "Master Orchestrator & Neural Engine Hub",
        "icon": "🖥️"
    },
    "gl_travel_router": {
        "name": "GL.iNet Travel Router (GL-MT3600BE)",
        "mac": "94:83:c4:d3:4a:10",
        "ip": "192.168.8.1",
        "tailscale": "100.122.185.123",
        "role": "Wi-Fi 7 Multi-WAN Gateway & TP-Link Bridge",
        "icon": "🛰️"
    }
}

class WoLEngine:
    def __init__(self):
        OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    def send_magic_packet(self, mac_address: str, broadcast_ip: str = "192.168.8.255", port: int = 9) -> bool:
        """Constructs and transmits an RFC standard Wake-on-LAN magic packet."""
        clean_mac = mac_address.replace(":", "").replace("-", "").replace(".", "")
        if len(clean_mac) != 12:
            logger.error(f"Invalid MAC address format: {mac_address}")
            return False

        mac_bytes = bytes.fromhex(clean_mac)
        magic_packet = b"\xff" * 6 + mac_bytes * 16

        # Broadcast targets to ensure reachability across subnets & Thunderbolt bridges
        targets = [broadcast_ip, "255.255.255.255", "169.254.255.255"]

        success = False
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for target in targets:
                try:
                    sock.sendto(magic_packet, (target, port))
                    sock.sendto(magic_packet, (target, 7))
                    success = True
                except Exception as e:
                    logger.debug(f"Broadcast to {target} failed: {e}")

        if success:
            logger.info(f"⚡ [WoL] Magic Packet dispatched to MAC: {mac_address} ({broadcast_ip}:{port})")
        return success

    def wake_device(self, key: str) -> Dict[str, Any]:
        """Wakes a specific device by key."""
        key = key.lower().strip()
        if key not in DEVICES:
            # Check partial match
            match = [k for k in DEVICES if key in k]
            if match:
                key = match[0]
            else:
                return {"success": False, "error": f"Device '{key}' not found in registry"}

        dev = DEVICES[key]
        mac = dev["mac"]
        ok = self.send_magic_packet(mac)
        if "alt_mac" in dev:
            self.send_magic_packet(dev["alt_mac"])

        result = {
            "success": ok,
            "device_key": key,
            "device_name": dev["name"],
            "mac_address": mac,
            "ip_address": dev["ip"],
            "tailscale_ip": dev["tailscale"],
            "timestamp_utc": datetime.utcnow().isoformat() + "Z"
        }
        
        self.generate_obsidian_dashboard(last_woken=dev["name"])
        return result

    def wake_all(self) -> Dict[str, Any]:
        """Broadcasts magic packets to all devices in the registry."""
        results = {}
        for k in DEVICES:
            results[k] = self.wake_device(k)
        return {"action": "WAKE_ALL", "results": results}

    def generate_obsidian_dashboard(self, last_woken: Optional[str] = None):
        """Generates an interactive Obsidian Dashboard with live status and triggers."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        md = f"""# ⚡ Lauburu Fleet Wake-on-LAN & Distributed Compute Dashboard
> **Last Synced:** `{now_str}`  
> **Active Subnet:** `192.168.8.0/24` | **Tailscale Mesh:** `100.x.x.x` | **Magic Port:** `UDP 9 / 7`

---

## 🎯 Device Registry & Instant Wake Controls

| Device | Role | Hardware MAC | Local LAN IP | Tailscale IP | Quick Wake Command |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for k, d in DEVICES.items():
            md += f"| {d['icon']} **{d['name']}** | `{d['role']}` | `{d['mac']}` | `{d['ip']}` | `{d['tailscale']}` | `wol wake {k}` |\n"

        md += f"""
---

## 🚀 Quick Execution Triggers

- **Wake All Sleeping Nodes:**
  ```bash
  python3 /Users/aaron/06_scripts_and_tooling/mesh/wol_manager.py --wake-all
  ```
- **Wake MacBook Pro Vault:**
  ```bash
  python3 /Users/aaron/06_scripts_and_tooling/mesh/wol_manager.py --wake macbook_pro_vault
  ```
- **Wake Linux Head Node:**
  ```bash
  python3 /Users/aaron/06_scripts_and_tooling/mesh/wol_manager.py --wake linux_head_node
  ```

---

## 🌐 Web API & Localhost 3000 Integration

The WoL service exposes an HTTP API for the Localhost 3000 Web UI:
- **Endpoint:** `GET /api/wol/wake?device=<device_key>`
- **Endpoint:** `GET /api/wol/wake-all`
- **Status:** `GET /api/wol/status`

> [!NOTE]
> Last Woken Device: **{last_woken if last_woken else "None"}**
"""
        with open(DASHBOARD_FILE, "w") as f:
            f.write(md)
        logger.info(f"📑 Obsidian WoL Dashboard updated -> {DASHBOARD_FILE}")

class WoLHTTPHandler(BaseHTTPRequestHandler):
    engine = WoLEngine()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path == "/api/wol/wake":
            dev = params.get("device", [""])[0]
            res = self.engine.wake_device(dev)
            self.wfile.write(json.dumps(res).encode())
        elif path == "/api/wol/wake-all":
            res = self.engine.wake_all()
            self.wfile.write(json.dumps(res).encode())
        elif path == "/api/wol/status":
            res = {"status": "ONLINE", "registered_devices": DEVICES}
            self.wfile.write(json.dumps(res).encode())
        else:
            self.wfile.write(json.dumps({"service": "Lauburu WoL API v2.1", "endpoints": ["/api/wol/wake?device=...", "/api/wol/wake-all", "/api/wol/status"]}).encode())

    def log_message(self, format, *args):
        pass  # Quiet logging

def run_server(port: int = 18802):
    server = HTTPServer(("0.0.0.0", port), WoLHTTPHandler)
    logger.info(f"🌐 WoL REST API listening on port {port} (http://localhost:{port}/api/wol/status)...")
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Lauburu Wake-on-LAN Fleet Manager")
    parser.add_argument("--wake", type=str, help="Device key to wake (e.g. macbook_pro_vault, linux_head_node)")
    parser.add_argument("--wake-all", action="store_true", help="Broadcast magic packet to all devices")
    parser.add_argument("--serve-api", action="store_true", help="Start WoL HTTP API on port 18802")
    parser.add_argument("--sync-dashboard", action="store_true", help="Sync Obsidian dashboard only")
    args = parser.parse_args()

    engine = WoLEngine()

    if args.wake:
        res = engine.wake_device(args.wake)
        print(json.dumps(res, indent=2))
        return

    if args.wake_all:
        res = engine.wake_all()
        print(json.dumps(res, indent=2))
        return

    if args.sync_dashboard:
        engine.generate_obsidian_dashboard()
        print("✅ Obsidian Dashboard Synced.")
        return

    if args.serve_api:
        engine.generate_obsidian_dashboard()
        run_server()
        return

    # Default: sync dashboard and display status
    engine.generate_obsidian_dashboard()
    print(json.dumps({"status": "WoL Engine Ready", "registered_devices": DEVICES}, indent=2))

if __name__ == "__main__":
    main()
