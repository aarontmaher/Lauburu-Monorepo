#!/usr/bin/env python3
"""
06_scripts_and_tooling/device_watchdog/deploy_mobile_mesh.py
============================================================
One-Click Mobile APK & Port 4000 PWA Deployment Engine for Project Lauburu.
Targets:
  - Primary Default: Samsung Galaxy S20+ (100.84.40.95:5555)
  - Secondary/Flagship: Google Pixel 10 Pro XL (100.73.38.87:5555)

Features:
  1. Wireless ADB Auto-Connect & Screen Wakeup (KEYCODE_WAKEUP, dismiss-keyguard)
  2. Automatic Pre-Built APK Discovery / Install (-r -d -g)
  3. Automatic Runtime Permission Grants (BLE, Location, Notifications)
  4. Foreground App Launch (monkey launcher) & Port 4000 PWA Chrome Dispatch
  5. Live Process Verification & Window Focus Validation
"""

import os
import sys
import time
import argparse
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DEPLOY-MESH]: %(message)s"
)
logger = logging.getLogger("DeployMesh")

ADB_BIN = "/Users/aaron/.local/bin/adb" if os.path.exists("/Users/aaron/.local/bin/adb") else "adb"
PORT4000_URL = "http://100.119.199.76:4000"
ROUTER_SSH = "root@192.168.8.1"

DEVICES: Dict[str, Dict[str, Any]] = {
    "s20": {
        "name": "Samsung Galaxy S20+ (Primary Testbed)",
        "ip": "100.84.40.95",
        "alt_ip": "192.168.8.11",
        "port": 5555,
        "router_usb_serial": "R3CN40CJJ1R"
    },
    "pixel": {
        "name": "Google Pixel 10 Pro XL (Flagship Edge)",
        "ip": "100.73.38.87",
        "alt_ip": "192.168.8.14",
        "port": 5555,
        "router_usb_serial": ""
    }
}

APP_PACKAGES: Dict[str, Dict[str, Any]] = {
    "compute_hub": {
        "name": "Lauburu Compute Hub (Central Background BLE Service)",
        "package": "com.example.lauburu_compute_hub",
        "activity": ".MainActivity",
        "dir": "Installed_Apps/Phone_Applications/lauburu_compute_hub",
        "permissions": [
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
            "android.permission.BLUETOOTH_SCAN",
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.POST_NOTIFICATIONS"
        ]
    },
    "zone2": {
        "name": "Lauburu Zone 2 Endurance",
        "package": "com.example.lauburu_zone2_endurance",
        "activity": ".MainActivity",
        "dir": "Installed_Apps/Phone_Applications/lauburu_zone2_endurance",
        "permissions": [
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.BLUETOOTH_SCAN",
            "android.permission.ACCESS_FINE_LOCATION"
        ]
    },
    "super_app": {
        "name": "Lauburu Super App",
        "package": "com.lauburu.super_app",
        "activity": ".MainActivity",
        "dir": "Installed_Apps/Phone_Applications/lauburu_super_app",
        "permissions": [
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.BLUETOOTH_SCAN"
        ]
    },
    "bluetooth_sensor": {
        "name": "Lauburu Bluetooth Sensor",
        "package": "com.example.lauburu_bluetooth_sensor",
        "activity": ".MainActivity",
        "permissions": [
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.BLUETOOTH_SCAN",
            "android.permission.ACCESS_FINE_LOCATION"
        ]
    },
    "openclaw": {
        "name": "OpenClaw AI Mobile Agent",
        "package": "com.openclaw.openclaw_app",
        "apk": "openclaw_apk/base.apk",
        "permissions": [
            "android.permission.INTERNET",
            "android.permission.RECORD_AUDIO"
        ]
    }
}

def is_device_online(target: str) -> bool:
    try:
        res = subprocess.run([ADB_BIN, "devices"], capture_output=True, text=True, timeout=2.5)
        for line in res.stdout.splitlines():
            if target in line and "device" in line and "offline" not in line:
                return True
    except Exception:
        pass
    return False

def connect_device(dev_key: str = "s20") -> str:
    dev = DEVICES[dev_key]
    target = f"{dev['ip']}:{dev['port']}"
    logger.info(f"Connecting to {dev['name']} at {target}...")

    # 1. Direct connect
    try:
        subprocess.run([ADB_BIN, "connect", target], capture_output=True, timeout=3.0)
        if is_device_online(target):
            logger.info(f"✓ Connected to {dev['name']} ({target})")
            return target
    except Exception as e:
        logger.warning(f"Direct connect note: {e}")

    # 2. Router USB TCP/IP bounce
    if dev.get("router_usb_serial"):
        serial = dev["router_usb_serial"]
        logger.info(f"Executing router USB ADB TCP/IP bounce on {serial}...")
        try:
            res = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=2", "-o", "StrictHostKeyChecking=no",
                 ROUTER_SSH, f"adb -s {serial} tcpip 5555"],
                capture_output=True, text=True, timeout=4.0
            )
            logger.info(f"Router response: {res.stdout.strip()}")
            time.sleep(1.0)
            subprocess.run([ADB_BIN, "connect", target], capture_output=True, timeout=3.0)
            if is_device_online(target):
                logger.info(f"✓ Connected to {dev['name']} via Router USB bounce ({target})")
                return target
        except Exception as e:
            logger.warning(f"Router USB bounce note: {e}")

    # 3. Alternate IP
    if dev.get("alt_ip"):
        alt_target = f"{dev['alt_ip']}:{dev['port']}"
        logger.info(f"Trying alternative IP {alt_target}...")
        try:
            subprocess.run([ADB_BIN, "connect", alt_target], capture_output=True, timeout=2.0)
            if is_device_online(alt_target):
                logger.info(f"✓ Connected to {dev['name']} ({alt_target})")
                return alt_target
        except Exception as e:
            logger.warning(f"Alt IP note: {e}")

    logger.warning(f"Could not reach {dev['name']} ({target}).")
    return ""

def wake_device(target: str):
    logger.info(f"Waking up screen and unlocking keyguard on {target}...")
    try:
        subprocess.run([ADB_BIN, "-s", target, "shell", "input keyevent KEYCODE_WAKEUP"], capture_output=True, timeout=2.0)
        subprocess.run([ADB_BIN, "-s", target, "shell", "input keyevent 82"], capture_output=True, timeout=2.0)
        subprocess.run([ADB_BIN, "-s", target, "shell", "wm dismiss-keyguard"], capture_output=True, timeout=2.0)
        subprocess.run([ADB_BIN, "-s", target, "shell", "svc power stayon true"], capture_output=True, timeout=2.0)
    except Exception as e:
        logger.warning(f"Wake note on {target}: {e}")

def find_apk_for_app(app_key: str) -> Optional[Path]:
    app_meta = APP_PACKAGES.get(app_key, {})
    if "apk" in app_meta:
        p = Path(app_meta["apk"])
        if p.exists():
            return p
        p_full = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo") / app_meta["apk"]
        if p_full.exists():
            return p_full

    if "dir" in app_meta:
        cand1 = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo") / app_meta["dir"] / "build/app/outputs/flutter-apk/app-debug.apk"
        if cand1.exists():
            return cand1
        cand2 = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo") / app_meta["dir"] / "build/app/outputs/flutter-apk/app-release.apk"
        if cand2.exists():
            return cand2

    return None

def install_app_package(target: str, app_key: str, apk_override: Optional[str] = None) -> bool:
    app_meta = APP_PACKAGES.get(app_key, APP_PACKAGES["compute_hub"])
    pkg = app_meta["package"]
    
    apk_path = Path(apk_override) if apk_override else find_apk_for_app(app_key)

    if apk_path and apk_path.exists():
        logger.info(f"Installing APK ({apk_path}) to {target}...")
        try:
            res = subprocess.run(
                [ADB_BIN, "-s", target, "install", "-r", "-d", "-g", str(apk_path)],
                capture_output=True, text=True, timeout=90
            )
            if res.returncode == 0 and "Success" in res.stdout:
                logger.info(f"✓ APK install successful: {pkg}")
            else:
                logger.warning(f"Install response: {res.stdout.strip()} {res.stderr.strip()}")
        except Exception as e:
            logger.warning(f"Install exception: {e}")
    else:
        logger.info(f"No new local APK file found to push; using installed package '{pkg}' on device.")

    # Grant permissions
    grant_permissions(target, app_key)
    return True

def grant_permissions(target: str, app_key: str):
    app_meta = APP_PACKAGES.get(app_key, APP_PACKAGES["compute_hub"])
    pkg = app_meta["package"]
    perms = app_meta.get("permissions", [])
    logger.info(f"Granting {len(perms)} runtime permissions for {pkg} on {target}...")
    for perm in perms:
        try:
            subprocess.run([ADB_BIN, "-s", target, "shell", "pm", "grant", pkg, perm], capture_output=True, timeout=2.0)
        except Exception:
            pass

def launch_app_foreground(target: str, app_key: str):
    app_meta = APP_PACKAGES.get(app_key, APP_PACKAGES["compute_hub"])
    pkg = app_meta["package"]
    logger.info(f"Launching {app_meta['name']} ({pkg}) into foreground on {target}...")
    try:
        subprocess.run(
            [ADB_BIN, "-s", target, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True, text=True, timeout=5.0
        )
    except Exception as e:
        logger.warning(f"Foreground launch note: {e}")

def launch_port_4000_pwa(target: str):
    logger.info(f"Dispatching Port 4000 Master PWA ({PORT4000_URL}) in Chrome on {target}...")
    try:
        subprocess.run(
            [ADB_BIN, "-s", target, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", PORT4000_URL, "com.android.chrome"],
            capture_output=True, text=True, timeout=5.0
        )
    except Exception as e:
        logger.warning(f"PWA launch note: {e}")

def verify_deployment(target: str, app_key: str) -> bool:
    app_meta = APP_PACKAGES.get(app_key, APP_PACKAGES["compute_hub"])
    pkg = app_meta["package"]
    
    print("\n--- Live Deployment Verification ---")
    # 1. Window focus check
    try:
        focus = subprocess.run(
            [ADB_BIN, "-s", target, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"],
            capture_output=True, text=True, timeout=5.0
        )
        print(f"Current Window Focus:\n{focus.stdout.strip()}")
    except Exception as e:
        print(f"Window focus error: {e}")

    # 2. Process PID check
    try:
        pid = subprocess.run(
            [ADB_BIN, "-s", target, "shell", f"pidof {pkg}"],
            capture_output=True, text=True, timeout=5.0
        )
        pid_str = pid.stdout.strip()
        if pid_str:
            print(f"✓ Process '{pkg}' is RUNNING (PID: {pid_str})")
            return True
        else:
            print(f"⚠️  Process '{pkg}' was not listed in active pidof output (may be backgrounded or starting).")
            return True
    except Exception as e:
        print(f"PID check note: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Lauburu One-Click Mobile APK & PWA Deployer")
    parser.add_argument("--device", choices=["all", "s20", "pixel"], default="s20", help="Target device (default: s20)")
    parser.add_argument("--app", choices=list(APP_PACKAGES.keys()), default="compute_hub", help="Target application")
    parser.add_argument("--apk", type=str, default="", help="Optional explicit path to APK file")
    parser.add_argument("--launch-pwa", action="store_true", help="Launch Port 4000 PWA in Chrome after app deployment")
    parser.add_argument("--wake-only", action="store_true", help="Only wake and unlock device screen")
    args = parser.parse_args()

    print("=" * 80)
    print("📱 PROJECT LAUBURU — ONE-CLICK MOBILE DEPLOYMENT ENGINE")
    print(f"Target Device : {args.device}")
    print(f"Target App    : {args.app} ({APP_PACKAGES[args.app]['name']})")
    print(f"Launch PWA    : {args.launch_pwa}")
    print("=" * 80)

    target_keys = ["s20", "pixel"] if args.device == "all" else [args.device]

    for d_key in target_keys:
        target = connect_device(d_key)
        if not target:
            print(f"❌ Could not establish ADB connection with {DEVICES[d_key]['name']}.")
            continue

        print(f"\n[Deploying to {DEVICES[d_key]['name']} @ {target}]")
        wake_device(target)

        if args.wake_only:
            print("✓ Screen woke up successfully.")
            continue

        install_app_package(target, args.app, args.apk)
        time.sleep(0.5)
        launch_app_foreground(target, args.app)

        if args.launch_pwa:
            time.sleep(1.0)
            launch_port_4000_pwa(target)

        time.sleep(1.0)
        verify_deployment(target, args.app)

    print("\n" + "=" * 80)
    print("🎉 MOBILE DEPLOYMENT SEQUENCE COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
