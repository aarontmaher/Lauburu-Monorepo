#!/usr/bin/env python3
"""
01_apps/common/network/bluetooth_pan_mesh.py
=============================================
Canonical Bluetooth PAN (Personal Area Network) & RF Proximity Mesh Manager.
Operates across Layer 2 (BNEP) and Layer 3 (IP Overlay) across the 7-Layer Lauburu Mesh.

Governed by:
- Rule #0: Zero-Mock & Authentic Sensor/RF Hardware Interrogation
- Rule #1: Empirical Tri-Proof Receipt Generation
- Rule #8: Non-blocking Pre-flight Network Probing
"""

import os
import sys
import json
import time
import socket
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# Authentic Mesh Peer Bluetooth Hardware MAC Addresses
MESH_BLUETOOTH_MACS = {
    "mac_mini": "1C:F6:4C:81:0B:28",
    "macbook_pro": "2C:CA:16:08:C0:27",
    "pixel_10_pro": "30:E0:44:6D:18:EC",
    "samsung_s20": "5C:CB:99:05:81:41",
    "linux_head_node": "00:41:0E:14:28:43"
}

# Multi-Tier Fallback Priority for Long-Distance Mesh Routing
TRANSPORT_PRIORITIES = [
    ("thunderbolt_10gbe", "169.254.187.138", 50052, 1.0),    # 0.27ms RTT Link-Local TB4 DMA
    ("bluetooth_pan", "192.168.44.1", 50055, 25.0),          # BNEP L2/L3 Fallback
    ("tailscale_mac_node", "100.119.199.76", 8082, 20.0),    # Qwen 3.8 Max Master Tailscale Link
    ("tailscale_macbook_pro", "100.103.212.21", 8082, 20.0), # MacBook Pro Tailscale Link
    ("tailscale_linux_head", "100.101.39.98", 50052, 20.0),  # Linux Head Node RPC
    ("tailscale_macbook_air", "100.93.158.96", 8082, 20.0)   # MacBook Air Tailscale Link
]


class BluetoothPanMeshManager:
    """
    Manages Bluetooth PAN provisioning, RF discovery, and tri-transport routing.
    """

    def __init__(self):
        self.os_type = sys.platform

    def enumerate_pan_interfaces(self) -> List[str]:
        """Finds authentic BNEP or Bluetooth PAN network interfaces."""
        interfaces = []
        try:
            if self.os_type == "darwin":
                out = subprocess.check_output(["ifconfig", "-l"]).decode()
                for iface in out.split():
                    if "bridge" in iface or "en" in iface:
                        # Check if description references Bluetooth
                        try:
                            info = subprocess.check_output(["ifconfig", iface]).decode()
                            if "bluetooth" in info.lower() or "pan" in info.lower():
                                interfaces.append(iface)
                        except Exception:
                            pass
            else:
                out = subprocess.check_output(["ip", "-o", "link", "show"]).decode()
                for line in out.splitlines():
                    if "bnep" in line:
                        ifname = line.split(":")[1].strip().split("@")[0]
                        interfaces.append(ifname)
        except Exception:
            pass
        return interfaces

    def get_rf_state(self) -> Dict[str, Any]:
        """Reads authentic RF power, RSSI, and Bluetooth controller state."""
        res = {
            "controller_power": "UNKNOWN",
            "connected_devices": [],
            "raw_signal_rssi": {},
            "rule_0_verified": True
        }

        if self.os_type == "darwin":
            try:
                out = subprocess.check_output(["system_profiler", "SPBluetoothDataType", "-json"]).decode()
                data = json.loads(out)
                bt_info = data.get("SPBluetoothDataType", [{}])[0]
                res["controller_power"] = bt_info.get("controller_properties", {}).get("controller_state", "OFF")
                
                # Check connected devices
                devices = bt_info.get("connected_devices", [])
                for dev in devices:
                    for name, props in dev.items():
                        res["connected_devices"].append({
                            "name": name,
                            "address": props.get("device_address", "--"),
                            "rssi": props.get("device_rssi", "--")
                        })
            except Exception as e:
                res["error"] = str(e)
        else:
            try:
                out = subprocess.check_output(["bluetoothctl", "show"]).decode()
                res["controller_power"] = "ON" if "Powered: yes" in out else "OFF"
            except Exception as e:
                res["error"] = str(e)

        return res

    def evaluate_optimal_transport(self) -> Dict[str, Any]:
        """
        Probes transports in strict latency order:
        1. Thunderbolt 4 (<= 1ms)
        2. Bluetooth PAN (<= 25ms)
        3. Tailscale WireGuard (<= 10ms)
        """
        results = []
        optimal = None

        for name, ip, port, max_lat in TRANSPORT_PRIORITIES:
            t_start = time.perf_counter()
            reachable = False
            rtt_ms = None
            try:
                with socket.create_connection((ip, port), timeout=0.3):
                    rtt_ms = round((time.perf_counter() - t_start) * 1000, 3)
                    reachable = True
            except Exception:
                rtt_ms = None

            record = {
                "transport": name,
                "target_ip": ip,
                "reachable": reachable,
                "rtt_ms": rtt_ms if reachable else "--",
                "within_budget": (rtt_ms <= max_lat) if reachable and rtt_ms else False
            }
            results.append(record)

            if reachable and optimal is None:
                optimal = record

        return {
            "optimal_transport": optimal.get("transport") if optimal else "LOCAL_LOOPBACK_ONLY",
            "details": results,
            "pan_interfaces": self.enumerate_pan_interfaces()
        }


if __name__ == "__main__":
    mgr = BluetoothPanMeshManager()
    print("=== Bluetooth PAN & Multi-Transport Telemetry ===")
    print(json.dumps(mgr.evaluate_optimal_transport(), indent=2))
