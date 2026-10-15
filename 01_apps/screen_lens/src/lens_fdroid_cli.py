#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
lens_fdroid_cli.py
================================================================================
Screen Lens Sovereign — F-Droid & Headless Package Manager CLI
Wraps fdroidcl and ADB streaming installation channels across the Lauburu mesh:
- L6: Google Pixel 10 Pro XL (192.168.8.213:5555 / 100.73.38.87:5555)
- L7: Samsung Galaxy S20+ (192.168.8.131:5555 / 100.84.40.95:5555 / R3CN40CJJ1R)

Governed by:
- Rule #0: Zero-Mock Empirical Truth
- Rule #10: Screen Lens Sovereign Automation Invariant
================================================================================
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

ADB_BIN = "/Users/aaron/.local/bin/adb"
FDROIDCL_BIN = shutil.which("fdroidcl") or "/Users/aaron/.local/bin/fdroidcl"
LOCAL_FDROID_APK = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/F-Droid.apk")

KNOWN_DEVICES = {
    "s20": {
        "name": "Samsung Galaxy S20+ (L7)",
        "candidates": ["192.168.8.131:5555", "100.84.40.95:5555", "R3CN40CJJ1R"]
    },
    "pixel": {
        "name": "Google Pixel 10 Pro XL (L6)",
        "candidates": ["192.168.8.213:5555", "192.168.8.114:5555", "100.73.38.87:5555", "5B080DLCQ001LQ"]
    }
}


def get_online_devices() -> Dict[str, Dict[str, Any]]:
    """Discovers which devices are online in ADB."""
    active = {}
    try:
        res = subprocess.run([ADB_BIN, "devices", "-l"], capture_output=True, text=True, timeout=3.0)
        lines = res.stdout.strip().splitlines()[1:]
    except Exception as e:
        lines = []

    online_serials = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            online_serials.append(parts[0])

    for key, info in KNOWN_DEVICES.items():
        matched = None
        for cand in info["candidates"]:
            if cand in online_serials:
                matched = cand
                break
        active[key] = {
            "name": info["name"],
            "online": matched is not None,
            "serial": matched or info["candidates"][0]
        }
    return active


def check_fdroid_installed(serial: str) -> Dict[str, Any]:
    """Checks if F-Droid is installed on a specific device."""
    try:
        res = subprocess.run(
            [ADB_BIN, "-s", serial, "shell", "pm list packages -f org.fdroid.fdroid"],
            capture_output=True, text=True, timeout=5.0
        )
        out = res.stdout.strip()
        is_installed = "org.fdroid.fdroid" in out
        version = None
        if is_installed:
            dumpsys = subprocess.run(
                [ADB_BIN, "-s", serial, "shell", "dumpsys package org.fdroid.fdroid | grep versionName | head -n 1"],
                capture_output=True, text=True, timeout=5.0
            )
            version = dumpsys.stdout.strip().replace("versionName=", "").strip()

        return {
            "installed": is_installed,
            "package_line": out,
            "version": version
        }
    except Exception as e:
        return {"installed": False, "error": str(e)}


def install_fdroid_apk(serial: str, apk_path: Path = LOCAL_FDROID_APK) -> Dict[str, Any]:
    """Installs or upgrades F-Droid APK on target device via ADB streaming install."""
    if not apk_path.exists():
        return {"status": "error", "message": f"APK not found at {apk_path}"}

    try:
        cmd = [ADB_BIN, "-s", serial, "install", "-r", "-d", str(apk_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
        success = "Success" in res.stdout
        return {
            "status": "success" if success else "failed",
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_fdroidcl(args: List[str]) -> Dict[str, Any]:
    """Executes a command via fdroidcl."""
    if not os.path.exists(FDROIDCL_BIN):
        return {"status": "error", "message": f"fdroidcl binary not found at {FDROIDCL_BIN}"}

    try:
        res = subprocess.run([FDROIDCL_BIN] + args, capture_output=True, text=True, timeout=60.0)
        return {
            "status": "success" if res.returncode == 0 else "failed",
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Screen Lens F-Droid CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    subparsers.add_parser("devices", help="List detected Android edge nodes and their ADB status")

    status_parser = subparsers.add_parser("status", help="Check F-Droid status across edge nodes")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    install_parser = subparsers.add_parser("install-fdroid", help="Install F-Droid client on device")
    install_parser.add_argument("--target", choices=["s20", "pixel", "all"], default="all", help="Target device")

    search_parser = subparsers.add_parser("search", help="Search F-Droid repository via fdroidcl")
    search_parser.add_argument("query", help="Search query")

    subparsers.add_parser("update", help="Update F-Droid repository index")

    audit_parser = subparsers.add_parser("audit", help="Perform comprehensive F-Droid ecosystem audit")

    args = parser.parse_args()

    if not args.command or args.command == "devices":
        devs = get_online_devices()
        print("=== Android Edge Node ADB Registry ===")
        for key, d in devs.items():
            state = "ONLINE" if d["online"] else "OFFLINE"
            print(f"[{key.upper()}] {d['name']} -> {d['serial']} ({state})")

    elif args.command == "status":
        devs = get_online_devices()
        results = {}
        for key, d in devs.items():
            if d["online"]:
                st = check_fdroid_installed(d["serial"])
            else:
                st = {"installed": False, "status": "device_offline"}
            results[key] = {
                "name": d["name"],
                "serial": d["serial"],
                "online": d["online"],
                "fdroid": st
            }
        if getattr(args, "json", False):
            print(json.dumps(results, indent=2))
        else:
            print("=== F-Droid Edge Node Status ===")
            for key, r in results.items():
                print(f"Device: {r['name']} ({r['serial']})")
                print(f"  Online: {r['online']}")
                fd = r["fdroid"]
                if fd.get("installed"):
                    print(f"  F-Droid Installed: YES (version: {fd.get('version')})")
                    print(f"  Package path: {fd.get('package_line')}")
                else:
                    print(f"  F-Droid Installed: NO / Offline ({fd.get('status', fd.get('error', 'unknown'))})")

    elif args.command == "install-fdroid":
        devs = get_online_devices()
        targets = [args.target] if args.target != "all" else ["s20", "pixel"]
        for t in targets:
            d = devs.get(t)
            if not d or not d["online"]:
                print(f"Skipping {t}: device is offline in ADB.")
                continue
            print(f"Installing F-Droid on {d['name']} ({d['serial']})...")
            res = install_fdroid_apk(d["serial"])
            print(json.dumps(res, indent=2))

    elif args.command == "search":
        res = run_fdroidcl(["search", args.query])
        if res["status"] == "success":
            print(res["stdout"])
        else:
            print(f"Error searching F-Droid: {res.get('stderr') or res.get('message')}")

    elif args.command == "update":
        print("Updating F-Droid index via fdroidcl...")
        res = run_fdroidcl(["update"])
        print(res["stdout"] if res["status"] == "success" else res.get("stderr"))

    elif args.command == "audit":
        devs = get_online_devices()
        print("=== Zero-Mock F-Droid Ecosystem Audit ===")
        for key, d in devs.items():
            print(f"\n--- Node: {d['name']} [{key}] ---")
            print(f"Serial: {d['serial']} | Status: {'ONLINE' if d['online'] else 'OFFLINE'}")
            if d["online"]:
                fd = check_fdroid_installed(d["serial"])
                print(f"F-Droid Package Present: {fd['installed']}")
                if fd.get("version"):
                    print(f"F-Droid Version: {fd['version']}")
                print(f"Package Line: {fd.get('package_line')}")
            else:
                print("Device currently offline from ADB.")


if __name__ == "__main__":
    main()
