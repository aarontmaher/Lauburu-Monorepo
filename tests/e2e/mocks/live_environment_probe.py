#!/usr/bin/env python3
"""
Live Environment Probe for Dual-Mode E2E Testbed
================================================
Empirically probes the host system to determine whether live physical hardware
(ADB devices, Tailscale peers) and live browser engines (Firefox, GeckoDriver)
are operational, or whether tests should execute in deterministic Synthetic Mode.
"""

import os
import shutil
import socket
import subprocess
from typing import Dict, Any, List


class LiveEnvironmentProbe:
    """Probes system for live hardware, network, and browser binaries."""

    @staticmethod
    def check_firefox() -> Dict[str, Any]:
        """Checks if Firefox and GeckoDriver are available."""
        firefox_bin = shutil.which("firefox") or shutil.which("/Applications/Firefox.app/Contents/MacOS/firefox")
        geckodriver_bin = shutil.which("geckodriver") or shutil.which("/usr/local/bin/geckodriver") or shutil.which("/opt/homebrew/bin/geckodriver")
        is_available = bool(firefox_bin and geckodriver_bin)
        return {
            "available": is_available,
            "firefox_path": str(firefox_bin) if firefox_bin else None,
            "geckodriver_path": str(geckodriver_bin) if geckodriver_bin else None,
        }

    @staticmethod
    def check_adb_devices() -> Dict[str, Any]:
        """Checks for live connected ADB devices (USB or TCP)."""
        adb_bin = shutil.which("adb") or shutil.which("/Users/aaron/.local/bin/adb")
        if not adb_bin:
            return {"available": False, "adb_path": None, "devices": []}

        try:
            res = subprocess.run([adb_bin, "devices", "-l"], capture_output=True, text=True, timeout=3)
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("List of devices")]
            devices = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return {
                "available": len(devices) > 0,
                "adb_path": str(adb_bin),
                "devices": devices,
            }
        except Exception:
            return {"available": False, "adb_path": str(adb_bin), "devices": []}

    @staticmethod
    def check_tailscale() -> Dict[str, Any]:
        """Checks if Tailscale mesh interface is active."""
        tailscale_bin = shutil.which("tailscale") or shutil.which("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
        if not tailscale_bin:
            return {"available": False, "tailscale_path": None, "ip": None, "status": "missing"}

        try:
            res = subprocess.run([tailscale_bin, "status", "--json"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                return {"available": True, "tailscale_path": str(tailscale_bin), "status": "active"}
        except Exception:
            pass

        return {"available": False, "tailscale_path": str(tailscale_bin), "status": "inactive"}

    @staticmethod
    def check_local_port(port: int, host: str = "127.0.0.1") -> bool:
        """Checks if a TCP port is currently listening."""
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except Exception:
            return False

    @classmethod
    def probe_all(cls) -> Dict[str, Any]:
        """Runs full audit of live environment capabilities."""
        ff_info = cls.check_firefox()
        adb_info = cls.check_adb_devices()
        ts_info = cls.check_tailscale()
        port_3000 = cls.check_local_port(3000)
        port_4000 = cls.check_local_port(4000)

        is_live_ready = bool(ff_info["available"] and adb_info["available"])

        return {
            "mode": "LIVE" if is_live_ready else "SYNTHETIC",
            "firefox": ff_info,
            "adb": adb_info,
            "tailscale": ts_info,
            "ports": {
                "port_3000": port_3000,
                "port_4000": port_4000,
            },
            "timestamp": "2026-08-26T01:00:00Z",
        }


if __name__ == "__main__":
    probe = LiveEnvironmentProbe.probe_all()
    import json
    print(json.dumps(probe, indent=2))
