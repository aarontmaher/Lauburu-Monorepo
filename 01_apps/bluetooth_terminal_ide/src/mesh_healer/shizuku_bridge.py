import subprocess
import json

class ShizukuBridge:
    def __init__(self):
        pass

    def verify_shizuku_active(self) -> bool:
        """Probes for active UID 2000 per Tier 1 Bootstrap Protocol."""
        try:
            res = subprocess.run(
                ["adb", "shell", "~/bin/rish", "-c", "'id'"],
                capture_output=True, text=True, timeout=5
            )
            if "uid=2000(shell)" in res.stdout:
                return True
            
            print("[SHIZUKU] UID 2000 not active. Auto-triggering wireless debugging start script...")
            subprocess.run(
                ["adb", "shell", "sh", "/sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh"],
                capture_output=True, text=True, timeout=5
            )
            return True
        except Exception:
            return False

    def enable_bt_pan(self, mac_address: str) -> bool:
        """Invokes Shizuku (rish) to force BNEP / BT Tethering."""
        if not self.verify_shizuku_active():
            print("[SHIZUKU BRIDGE] Fatal: Could not bootstrap Shizuku UID 2000.")
            return False

        print(f"[SHIZUKU BRIDGE] Forcing BT PAN tethering for {mac_address} via rish...")
        try:
            res = subprocess.run(
                ["adb", "shell", "~/bin/rish", "-c", "'cmd bluetooth_manager enable_tethering'"],
                capture_output=True, text=True, timeout=5
            )
            return res.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"[SHIZUKU BRIDGE] Error enabling PAN: {e}")
            return False
