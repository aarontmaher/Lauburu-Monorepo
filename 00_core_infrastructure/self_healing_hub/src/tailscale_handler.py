import logging
from adb_helper import AdbHelper

logger = logging.getLogger(__name__)

class TailscaleHandler:
    def __init__(self, adb_helper: AdbHelper):
        self.adb = adb_helper
        self.package_name = "com.tailscale.ipn"

    def is_installed(self):
        result = self.adb.run_shell(f"pm list packages | grep {self.package_name}")
        return result and result.returncode == 0 and self.package_name in result.stdout

    def start_tailscale(self):
        """
        Attempts to start the Tailscale VPN service via intent.
        """
        logger.info("Attempting to start Tailscale via ADB intent...")
        # Start the main activity
        result = self.adb.run_shell(f"am start -n {self.package_name}/.ui.MainActivity")
        if result and result.returncode == 0:
            logger.info("Tailscale UI launched.")
            return True
        logger.error("Failed to launch Tailscale.")
        return False

    def stop_tailscale(self):
        """
        Force stops the Tailscale app to drop the VPN.
        """
        logger.info("Stopping Tailscale...")
        result = self.adb.run_shell(f"am force-stop {self.package_name}")
        return result and result.returncode == 0
