#!/usr/bin/env python3
"""
Lauburu Self-Healing Hub - Wi-Fi & Cellular Radio Interface Handler
===================================================================
Manages privileged cycling of wireless radio hardware (Wi-Fi, Mobile Data)
to recover from MTU black holes, AP disassociations, and DNS deadlocks.
"""

import logging
import time
from typing import Dict, Any, Optional
from adb_helper import AdbHelper

logger = logging.getLogger(__name__)


class WifiHandler:
    def __init__(self, adb_helper: AdbHelper):
        self.adb = adb_helper

    def enable_wifi(self) -> bool:
        """Enables Wi-Fi radio interface via privileged svc."""
        logger.info("Enabling Wi-Fi radio...")
        result = self.adb.run_privileged("svc wifi enable")
        return bool(result and result.returncode == 0)

    def disable_wifi(self) -> bool:
        """Disables Wi-Fi radio interface via privileged svc."""
        logger.info("Disabling Wi-Fi radio...")
        result = self.adb.run_privileged("svc wifi disable")
        return bool(result and result.returncode == 0)

    def bounce_wifi(self, delay_sec: float = 2.0) -> bool:
        """Executes full atomic Wi-Fi radio bounce (disable -> wait -> enable)."""
        logger.info("Bouncing Wi-Fi interface...")
        if not self.disable_wifi():
            return False
        if not self.adb.mock_mode and delay_sec > 0:
            time.sleep(delay_sec)
        return self.enable_wifi()

    def enable_cellular(self) -> bool:
        """Enables Cellular mobile data radio."""
        logger.info("Enabling Cellular data interface...")
        result = self.adb.run_privileged("svc data enable")
        return bool(result and result.returncode == 0)

    def disable_cellular(self) -> bool:
        """Disables Cellular mobile data radio."""
        logger.info("Disabling Cellular data interface...")
        result = self.adb.run_privileged("svc data disable")
        return bool(result and result.returncode == 0)

    def bounce_cellular(self, delay_sec: float = 1.0) -> bool:
        """Executes full atomic Cellular data radio bounce."""
        logger.info("Bouncing Cellular data interface...")
        if not self.disable_cellular():
            return False
        if not self.adb.mock_mode and delay_sec > 0:
            time.sleep(delay_sec)
        return self.enable_cellular()

    def get_wifi_state(self) -> bool:
        """Checks if Wi-Fi is currently enabled."""
        result = self.adb.run_privileged("dumpsys wifi")
        if result and result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Wi-Fi is" in line:
                    return "enabled" in line.lower()
        return False

    def get_wifi_details(self) -> Dict[str, Any]:
        """Queries Wi-Fi connection metadata (state, SSID, link speed)."""
        details = {"enabled": self.get_wifi_state(), "connected": False, "ssid": None, "rssi": None}
        result = self.adb.run_privileged("dumpsys wifi")
        if result and result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if "mWifiInfo" in line or "mNetworkInfo" in line:
                    if "CONNECTED" in line:
                        details["connected"] = True
                if "SSID:" in line:
                    parts = line.split("SSID:")
                    if len(parts) > 1:
                        details["ssid"] = parts[1].split(",")[0].strip().strip('"')
                if "RSSI:" in line:
                    parts = line.split("RSSI:")
                    if len(parts) > 1:
                        try:
                            details["rssi"] = int(parts[1].split()[0].replace(",", ""))
                        except ValueError:
                            pass
        return details
