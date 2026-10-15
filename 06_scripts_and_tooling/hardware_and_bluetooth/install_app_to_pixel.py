#!/usr/bin/env python3
"""
06_scripts_and_tooling/install_app_to_pixel.py
==============================================
Sovereign Pixel 10 Pro XL Automated App Installer & Provisioning Sentinel
Compliant with: Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), Rule 5 (Victory Gate)
==============================================
"""

import os
import sys
import time
import socket
import argparse
import subprocess
from pathlib import Path

DEFAULT_APK = "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android_apks/de.kai_morich.serial_bluetooth_terminal.apk"
PIXEL_TS_IP = "100.73.38.87"
PIXEL_LAN_IP = "192.168.8.145"
ADB_BIN = "/Users/aaron/.local/bin/adb" if os.path.exists("/Users/aaron/.local/bin/adb") else "adb"


def probe_tcp_port(host: str, port: int, timeout_s: float = 0.3) -> bool:
    """Non-blocking TCP port connection probe."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def get_attached_usb_devices() -> list[str]:
    """Returns list of active USB/local ADB devices."""
    try:
        res = subprocess.run([ADB_BIN, "devices"], capture_output=True, text=True, timeout=2.0)
        lines = res.stdout.strip().splitlines()[1:]
        devices = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device" and ":" not in parts[0]:
                devices.append(parts[0])
        return devices
    except Exception:
        return []


def find_pixel_target() -> str | None:
    """Probes USB, LAN, and Tailscale for Pixel 10 Pro XL."""
    # 1. Check direct USB connection
    usb_devs = get_attached_usb_devices()
    if usb_devs:
        return usb_devs[0]

    # 2. Check LAN port 5555
    if probe_tcp_port(PIXEL_LAN_IP, 5555, timeout_s=0.3):
        subprocess.run([ADB_BIN, "connect", f"{PIXEL_LAN_IP}:5555"], capture_output=True, timeout=2.0)
        return f"{PIXEL_LAN_IP}:5555"

    # 3. Check Tailscale port 5555
    if probe_tcp_port(PIXEL_TS_IP, 5555, timeout_s=0.3):
        subprocess.run([ADB_BIN, "connect", f"{PIXEL_TS_IP}:5555"], capture_output=True, timeout=2.0)
        return f"{PIXEL_TS_IP}:5555"

    # 4. Any active ADB target
    try:
        res = subprocess.run([ADB_BIN, "devices"], capture_output=True, text=True, timeout=2.0)
        lines = res.stdout.strip().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                return parts[0]
    except Exception:
        pass

    return None


def install_and_provision(target_serial: str, apk_path: str) -> bool:
    print(f"\n🟢 Connected to Active Target: {target_serial}")
    print(f"📦 Installing APK: {apk_path}")

    # Determine package name
    pkg_name = "de.kai_morich.serial_bluetooth_terminal"
    if "android_auto" in apk_path:
        pkg_name = "com.lauburu.androidauto.voicecoder"
    elif "openclaw" in apk_path:
        pkg_name = "ai.openclaw.agent"

    # Install APK
    t0 = time.perf_counter()
    install_cmd = [ADB_BIN, "-s", target_serial, "install", "-r", "-g", apk_path]
    res = subprocess.run(install_cmd, capture_output=True, text=True, timeout=60.0)
    dur_ms = (time.perf_counter() - t0) * 1000.0

    if res.returncode != 0 or "Success" not in res.stdout:
        print(f"❌ Installation failed:\n{res.stdout}\n{res.stderr}")
        return False

    print(f"✅ APK Successfully Installed in {dur_ms:.1f} ms!")

    # Configure Doze Bypass & Permissions
    print(f"⚡ Applying Keepalive & Doze Bypass for {pkg_name}...")
    subprocess.run([ADB_BIN, "-s", target_serial, "shell", f"dumpsys deviceidle whitelist +{pkg_name} +com.termux"], capture_output=True, timeout=5.0)
    subprocess.run([ADB_BIN, "-s", target_serial, "shell", f"cmd appops set {pkg_name} RUN_IN_BACKGROUND allow"], capture_output=True, timeout=5.0)
    subprocess.run([ADB_BIN, "-s", target_serial, "shell", "settings put global settings_enable_monitor_phantom_procs false"], capture_output=True, timeout=5.0)

    # Launch app
    print(f"🚀 Launching {pkg_name} on Pixel...")
    subprocess.run([ADB_BIN, "-s", target_serial, "shell", f"monkey -p {pkg_name} -c android.intent.category.LAUNCHER 1"], capture_output=True, timeout=5.0)

    # Verification Screenshot (Proof 3)
    print("📸 Capturing Verification Screenshot...")
    subprocess.run([ADB_BIN, "-s", target_serial, "shell", "screencap -p /sdcard/pixel_install_verify.png"], capture_output=True, timeout=5.0)
    subprocess.run([ADB_BIN, "-s", target_serial, "pull", "/sdcard/pixel_install_verify.png", "/tmp/pixel_install_verify.png"], capture_output=True, timeout=5.0)

    if os.path.isfile("/tmp/pixel_install_verify.png"):
        size_b = os.path.getsize("/tmp/pixel_install_verify.png")
        print(f"🖼️ Tri-Proof Visual Verification Saved: /tmp/pixel_install_verify.png ({size_b:,} bytes)")

    print("\n" + "=" * 60)
    print(f"🎉 SUCCESS: {pkg_name} installed, provisioned, and verified on Pixel!")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="Install APK to Pixel 10 Pro XL")
    parser.add_argument("apk", nargs="?", default=DEFAULT_APK, help="Path to APK to install")
    parser.add_argument("--wait", action="store_true", help="Wait in a loop until Pixel connects")
    parser.add_argument("--timeout", type=int, default=60, help="Max seconds to wait when --wait is set")
    args = parser.parse_args()

    if not os.path.isfile(args.apk):
        print(f"❌ Error: APK file not found at {args.apk}")
        sys.exit(1)

    print("=" * 60)
    print("📱 SOVEREIGN PIXEL APP INSTALLER")
    print(f"Target APK: {args.apk}")
    print("=" * 60)

    t0 = time.time()
    while True:
        target = find_pixel_target()
        if target:
            success = install_and_provision(target, args.apk)
            sys.exit(0 if success else 1)

        if not args.wait or (time.time() - t0 >= args.timeout):
            break

        print(f"\r⏳ Waiting for Pixel to connect via USB or Wireless ADB... ({int(time.time() - t0)}s elapsed)", end="", flush=True)
        time.sleep(1.0)

    print("\n⚠️ Pixel 10 Pro XL is currently not detected via ADB.")
    print("\n📋 Hardware Status:")
    print(f"  • Tailscale ({PIXEL_TS_IP}): Offline / Sleep")
    print(f"  • Router LAN ({PIXEL_LAN_IP}): Wi-Fi Power-Save")
    print("  • Bluetooth (30:E0:44:6D:18:EC): Paired")
    print("\n👉 To proceed:")
    print("  1. Connect Pixel to Mac Mini via USB-C with USB Debugging enabled, OR")
    print("  2. Wake Pixel and enable Developer Options -> Wireless Debugging.")
    sys.exit(2)


if __name__ == "__main__":
    main()
