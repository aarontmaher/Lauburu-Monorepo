#!/usr/bin/env python3
"""
Lauburu Self-Healing Hub - Tailscale VPN Daemon Controller
==========================================================
Manages privileged lifecycle, route flushing, and force restart of the
Tailscale Android daemon (com.tailscale.ipn) via elevated Shizuku / ADB IPC.
"""

import logging
import time
from typing import Optional
from adb_helper import AdbHelper

logger = logging.getLogger(__name__)


class TailscaleHandler:
    def __init__(self, adb_helper: AdbHelper):
        self.adb = adb_helper
        self.package_name = "com.tailscale.ipn"

    def is_installed(self) -> bool:
        """Verifies if Tailscale is installed on the target device."""
        result = self.adb.run_privileged(f"pm list packages")
        return bool(result and result.returncode == 0 and self.package_name in result.stdout)

    def is_running(self) -> bool:
        """Checks if Tailscale IPN process or service is active."""
        result = self.adb.run_privileged(f"pidof {self.package_name}")
        if result and result.returncode == 0 and result.stdout.strip():
            return True
        # Check dumpsys activity services
        result = self.adb.run_privileged(f"dumpsys activity services {self.package_name}")
        return bool(result and result.returncode == 0 and self.package_name in result.stdout)

    def start_tailscale(self) -> bool:
        """
        Attempts to start the Tailscale VPN service and main UI activity.
        """
        logger.info("Attempting to start Tailscale via privileged intent...")
        # 1. Start background service
        self.adb.run_privileged(f"am start-service {self.package_name}/.IPNService")
        # 2. Launch Main Activity (supports both modern and legacy component names)
        res1 = self.adb.run_privileged(f"am start -n {self.package_name}/com.tailscale.ipn.ui.MainActivity")
        if res1 and res1.returncode == 0:
            logger.info("Tailscale MainActivity launched successfully.")
            return True

        res2 = self.adb.run_privileged(f"am start -n {self.package_name}/.ui.MainActivity")
        if res2 and res2.returncode == 0:
            logger.info("Tailscale .ui.MainActivity launched successfully.")
            return True

        res3 = self.adb.run_privileged(f"am start -n {self.package_name}/.IPNActivity")
        return bool(res3 and res3.returncode == 0)

    def stop_tailscale(self) -> bool:
        """
        Force stops the Tailscale app to drop stuck VPN tunnels and clear socket buffers.
        """
        logger.info("Force-stopping Tailscale daemon...")
        result = self.adb.run_privileged(f"am force-stop {self.package_name}")
        return bool(result and result.returncode == 0)

    def restart_tailscale(self, delay_sec: float = 1.0) -> bool:
        """
        Executes an atomic force-stop and restart of the Tailscale daemon.
        """
        logger.info("Restarting Tailscale daemon...")
        stopped = self.stop_tailscale()
        if not self.adb.mock_mode and delay_sec > 0:
            time.sleep(delay_sec)
        started = self.start_tailscale()
        return stopped and started

    def get_tailscale_ip(self) -> Optional[str]:
        """Queries the assigned 100.x.y.z Tailscale CGNAT IP address."""
        res = self.adb.run_privileged("ip -f inet addr show tailscale0")
        if res and res.returncode == 0 and "inet " in res.stdout:
            for part in res.stdout.split():
                if part.startswith("100.") and "/" in part:
                    return part.split("/")[0]
        return None

    def ping_mesh_peer(self, peer_ip: str = "100.119.199.76", count: int = 1, timeout_sec: int = 3) -> bool:
        """Pings a Tailscale mesh peer (default: Host Mac Mini M4 Pro)."""
        res = self.adb.run_privileged(f"ping -c {count} -W {timeout_sec} {peer_ip}")
        return bool(res and res.returncode == 0)
