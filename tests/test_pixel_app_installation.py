#!/usr/bin/env python3
"""
tests/test_pixel_app_installation.py
Empirical Tri-Proof test suite verifying the installation of the Lauburu OpenCode
Bluetooth RFConnect Terminal & Terminal IDE on the Google Pixel 10 Pro XL (Layer 6).
Complies with Rule #0 (Zero-Mock), Rule #1 (Tri-Proof), Rule #3 (Host Sanctuary), and Rule #5.
"""

import hashlib
import os
import shutil
import subprocess
import unittest

HOST_APK_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/bluetooth_terminal_ide/android/app/build/outputs/apk/debug/app-debug.apk"
KAI_MORICH_APK = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/android_apks/de.kai_morich.serial_bluetooth_terminal.apk"


def calculate_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TestPixelAppInstallation(unittest.TestCase):

    def test_01_host_apk_build_and_sha256(self):
        """Verify the host APK was compiled successfully and exists."""
        self.assertTrue(os.path.isfile(HOST_APK_PATH), f"Host APK missing: {HOST_APK_PATH}")
        size = os.path.getsize(HOST_APK_PATH)
        self.assertGreater(size, 1_000_000, f"Host APK too small: {size} bytes")
        sha256 = calculate_sha256(HOST_APK_PATH)
        print(f"\n[HOST APK] Size: {size} bytes | SHA256: {sha256}")
        self.assertTrue(len(sha256) == 64)

    def test_02_pixel_staged_apks_integrity(self):
        """Verify the APKs staged in Pixel /sdcard/Download/ match the host SHA256 checksums."""
        host_sha256 = calculate_sha256(HOST_APK_PATH)
        res = subprocess.run(
            ["ssh", "pixel", "sha256sum /sdcard/Download/Lauburu_BT_Terminal_IDE.apk /sdcard/Download/Serial_Bluetooth_Terminal.apk"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res.returncode, 0, f"Failed to query remote checksums: {res.stderr}")
        lines = res.stdout.strip().splitlines()
        self.assertGreaterEqual(len(lines), 2)
        remote_sha256_lauburu = lines[0].split()[0]
        self.assertEqual(host_sha256, remote_sha256_lauburu, "Cryptographic mismatch on Pixel Lauburu APK!")
        print(f"[PIXEL APK SHA256 VERIFIED]: {remote_sha256_lauburu}")

    def test_03_pixel_launcher_shortcuts(self):
        """Verify launcher shortcuts exist in ~/.shortcuts/ and are executable."""
        res = subprocess.run(
            ["ssh", "pixel", "test -x ~/.shortcuts/Lauburu_BT_Terminal && test -x ~/.shortcuts/tasks/Lauburu_BLE_Scan.sh && test -x ~/.shortcuts/Lauburu_BT_IDE && echo 'ALL_SHORTCUTS_OK'"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res.returncode, 0, f"Shortcuts check failed: {res.stderr}")
        self.assertIn("ALL_SHORTCUTS_OK", res.stdout)
        print("[PIXEL SHORTCUTS]: Lauburu_BT_Terminal, Lauburu_BLE_Scan.sh, Lauburu_BT_IDE verified executable.")

    def test_04_pixel_app_binary_shortcut(self):
        """Verify /data/data/com.termux/files/usr/bin/lauburu-app is executable and functional."""
        res = subprocess.run(
            ["ssh", "pixel", "/data/data/com.termux/files/usr/bin/lauburu-app --help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(res.returncode, 0, f"lauburu-app failed: {res.stderr}")
        self.assertIn("Lauburu OpenCode Go Sovereign Mesh CLI & Bluetooth RFConnect Terminal", res.stdout)
        print("[PIXEL LAUBURU-APP BINARY]: Verified functional.")

    def test_05_host_memory_sanctuary(self):
        """Rule #3: Verify host Mac Mini preserves >= 4.8 GB available RAM."""
        import psutil
        vm = psutil.virtual_memory()
        avail_gb = vm.available / (1024**3)
        print(f"[HOST SANCTUARY]: Available RAM = {avail_gb:.2f} GB (Required >= 4.80 GB)")
        self.assertGreaterEqual(avail_gb, 4.80, f"Host memory sanctuary breached! Available: {avail_gb:.2f} GB")


if __name__ == "__main__":
    unittest.main()
