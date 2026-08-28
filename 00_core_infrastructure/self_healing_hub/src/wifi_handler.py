import logging
from adb_helper import AdbHelper

logger = logging.getLogger(__name__)

class WifiHandler:
    def __init__(self, adb_helper: AdbHelper):
        self.adb = adb_helper

    def enable_wifi(self):
        """Enables Wi-Fi via ADB."""
        logger.info("Enabling Wi-Fi...")
        result = self.adb.run_shell("svc wifi enable", as_root=True)
        return result and result.returncode == 0

    def disable_wifi(self):
        """Disables Wi-Fi via ADB."""
        logger.info("Disabling Wi-Fi...")
        result = self.adb.run_shell("svc wifi disable", as_root=True)
        return result and result.returncode == 0

    def get_wifi_state(self):
        """Checks if Wi-Fi is enabled."""
        result = self.adb.run_shell("dumpsys wifi | grep 'Wi-Fi is'")
        if result and result.returncode == 0:
            return "enabled" in result.stdout.lower()
        return False
