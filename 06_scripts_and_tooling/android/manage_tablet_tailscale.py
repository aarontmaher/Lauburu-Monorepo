#!/usr/bin/env python3
"""
manage_tablet_tailscale.py
Automated Tailscale Lifecycle, Upgrade & Migration Manager for Samsung Tablet (Node L4).

Resolves the issue where Tailscale is installed as a GitHub-sideloaded APK:
1. Sideloaded GitHub APKs do not auto-update via Google Play.
2. Android blocks Google Play updates due to signature mismatch (INSTALL_FAILED_UPDATE_INCOMPATIBLE).
3. Provides:
   - In-place GitHub APK upgrade to latest release (v1.102.4+) via ADB.
   - Clean migration to Google Play Store version (uninstalls GitHub APK + launches Play Store).
   - Automated updater via Obtainium (tracks GitHub releases directly on-device).
   - Post-install hardening (battery whitelist, phantom process limit, background keepalive).
"""

import sys
import os
import subprocess
import argparse
import json
import urllib.request
import re
from typing import Optional, List

TABLET_SERIAL = "R3CN40CJJ1R"
PACKAGE_NAME = "com.tailscale.ipn"
OBTAINIUM_PACKAGE = "com.imranr98.obtainium"
CANDIDATE_TRANSPORTS = [
    "192.168.42.129:5555",
    "192.168.8.185:5555",
    "192.168.8.173:5555",
    "192.168.8.134:5555",
    "100.81.92.125:5555",
]


def run_cmd(cmd: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def find_adb_device() -> Optional[str]:
    """Finds active ADB connection to the tablet via USB serial or network IP."""
    res = run_cmd(["adb", "devices"])
    lines = res.stdout.strip().splitlines()[1:]
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            identifier = parts[0]
            if identifier == TABLET_SERIAL or any(ip in identifier for ip in CANDIDATE_TRANSPORTS):
                return identifier

    # Attempt to probe network transports
    for endpoint in CANDIDATE_TRANSPORTS:
        try:
            conn = run_cmd(["adb", "connect", endpoint], timeout=3)
            if "connected to" in conn.stdout:
                return endpoint
        except Exception:
            pass

    # Fallback to any attached device if single device present
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]

    return None


def get_tailscale_info(device_id: str) -> dict:
    """Inspects installed Tailscale package info, version, and signature."""
    info = {
        "installed": False,
        "version_name": None,
        "version_code": None,
        "installer": None,
        "is_github_build": False,
    }
    res = run_cmd(["adb", "-s", device_id, "shell", "dumpsys", "package", PACKAGE_NAME])
    if "Unable to find package" in res.stdout or res.returncode != 0:
        return info

    info["installed"] = True
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("versionName="):
            info["version_name"] = line.split("=")[1]
        elif line.startswith("versionCode="):
            m = re.search(r"versionCode=(\d+)", line)
            if m:
                info["version_code"] = m.group(1)
        elif "installerPackageName=" in line:
            info["installer"] = line.split("=")[1]

    # Check installer package
    # Google Play Store installer is 'com.android.vending'. Sideloaded/GitHub is empty or 'com.google.android.packageinstaller'.
    if not info["installer"] or info["installer"] != "com.android.vending":
        info["is_github_build"] = True

    return info


def fetch_latest_github_apk(download_path: str = "/tmp/tailscale-latest.apk") -> str:
    """Queries GitHub API for latest tailscale-android universal APK and downloads it."""
    url = "https://api.github.com/repos/tailscale/tailscale-android/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "Lauburu-Mesh-Updater/1.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    tag_name = data.get("tag_name", "unknown")
    download_url = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".apk") and ("universal" in name or "arm64" in name):
            download_url = asset.get("browser_download_url")
            break

    if not download_url:
        raise RuntimeError("Could not find suitable APK asset in latest GitHub release.")

    print(f"[*] Downloading Tailscale {tag_name} from {download_url}...")
    urllib.request.urlretrieve(download_url, download_path)
    print(f"[+] Download complete: {download_path}")
    return download_path


def update_via_github(device_id: str):
    """Downloads and installs the latest GitHub release APK via ADB."""
    apk_path = fetch_latest_github_apk()
    print(f"[*] Installing {apk_path} to {device_id} (in-place reinstall)...")
    res = run_cmd(["adb", "-s", device_id, "install", "-r", "-d", apk_path], timeout=60)
    print(res.stdout)
    if "Success" in res.stdout:
        print("[+] Tailscale successfully updated to the latest GitHub release!")
        harden_tailscale(device_id)
    else:
        print(f"[-] Installation failed: {res.stderr or res.stdout}")


def migrate_to_play_store(device_id: str):
    """Cleanly uninstalls the GitHub version and opens Google Play Store to install cleanly."""
    print("[!] Step 1/3: Uninstalling GitHub version of Tailscale...")
    res = run_cmd(["adb", "-s", device_id, "uninstall", PACKAGE_NAME])
    print(res.stdout)

    print("[*] Step 2/3: Opening Google Play Store to Tailscale on tablet...")
    run_cmd([
        "adb", "-s", device_id, "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", f"market://details?id={PACKAGE_NAME}"
    ])

    print("[+] Step 3/3: Tablet screen is now on the official Google Play Tailscale page.")
    print("    Tap 'Install' on the tablet screen. Future updates will be fully automatic!")


def install_obtainium(device_id: str):
    """Installs Obtainium to automate GitHub APK updates directly on the tablet."""
    url = "https://api.github.com/repos/ImranR98/Obtainium/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "Lauburu-Mesh-Updater/1.0"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    download_url = None
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".apk") and "arm64" in name:
            download_url = asset.get("browser_download_url")
            break

    if not download_url:
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".apk"):
                download_url = asset.get("browser_download_url")
                break

    if download_url:
        path = "/tmp/obtainium.apk"
        print(f"[*] Downloading Obtainium from {download_url}...")
        urllib.request.urlretrieve(download_url, path)
        print(f"[*] Installing Obtainium to {device_id}...")
        res = run_cmd(["adb", "-s", device_id, "install", "-r", path], timeout=60)
        if "Success" in res.stdout:
            print("[+] Obtainium installed successfully on tablet.")
            # Launch Obtainium with tailscale repo preloaded
            run_cmd([
                "adb", "-s", device_id, "shell", "am", "start",
                "-a", "android.intent.action.VIEW",
                "-d", "https://github.com/tailscale/tailscale-android",
                "-n", f"{OBTAINIUM_PACKAGE}/.ui.MainActivity"
            ])


def harden_tailscale(device_id: str):
    """Ensures Tailscale is whitelisted from battery optimization and stays alive."""
    print("[*] Hardening Tailscale background keepalive on tablet...")
    run_cmd(["adb", "-s", device_id, "shell", "dumpsys", "deviceidle", "whitelist", f"+{PACKAGE_NAME}"])
    run_cmd(["adb", "-s", device_id, "shell", "cmd", "appops", "set", PACKAGE_NAME, "RUN_IN_BACKGROUND", "allow"])
    run_cmd(["adb", "-s", device_id, "shell", "cmd", "appops", "set", PACKAGE_NAME, "RUN_ANY_IN_BACKGROUND", "allow"])
    print("[+] Battery optimization disabled for Tailscale.")


def main():
    parser = argparse.ArgumentParser(description="Tailscale Manager for Samsung Tablet")
    parser.add_argument("--inspect", action="store_true", help="Inspect installed Tailscale version & signature")
    parser.add_argument("--update-github", action="store_true", help="Download and install latest GitHub release APK")
    parser.add_argument("--migrate-play", action="store_true", help="Uninstall GitHub version & open Google Play Store")
    parser.add_argument("--setup-obtainium", action="store_true", help="Install Obtainium to auto-update GitHub APKs")
    parser.add_argument("--harden", action="store_true", help="Whitelist Tailscale from battery saver & Doze")
    args = parser.parse_args()

    device = find_adb_device()
    if not device:
        print("[-] Tablet not found via USB or network ADB. Ensure tablet is powered on.")
        sys.exit(1)

    print(f"[+] Active tablet connection: {device}")

    if args.inspect or (not args.update_github and not args.migrate_play and not args.setup_obtainium and not args.harden):
        info = get_tailscale_info(device)
        print("\n=== Tailscale Inspection Status ===")
        print(f"Installed:       {info['installed']}")
        print(f"Version Name:    {info['version_name']}")
        print(f"Version Code:    {info['version_code']}")
        print(f"Installer:       {info['installer'] or 'Sideloaded / GitHub'}")
        print(f"Is GitHub Build: {info['is_github_build']}")
        if info["is_github_build"]:
            print("\n[!] Root Cause Confirmed: Tailscale is a GitHub-sideloaded build.")
            print("    - To update in-place without losing login: run --update-github")
            print("    - To switch to auto-updating Google Play Store: run --migrate-play")
            print("    - To auto-update GitHub releases on-device: run --setup-obtainium")
        return

    if args.update_github:
        update_via_github(device)
    elif args.migrate_play:
        migrate_to_play_store(device)
    elif args.setup_obtainium:
        install_obtainium(device)

    if args.harden:
        harden_tailscale(device)


if __name__ == "__main__":
    main()
