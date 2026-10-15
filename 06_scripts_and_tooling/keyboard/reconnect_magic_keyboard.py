#!/usr/bin/env python3
"""
06_scripts_and_tooling/keyboard/reconnect_magic_keyboard.py
==========================================================
Autonomous watchdog, auto-connector, and link monitor for Aaron's Magic Keyboard
(Address: 38-09-fb-38-ca-62) and Mac Mini Host keyboard subsystem.
Monitors Bluetooth link state, detects USB/Bluetooth waking events, auto-bonds,
and clears stuck modifiers via emergency_key_release.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

MAGIC_KEYBOARD_ADDR = "38-09-fb-38-ca-62"
BLUEUTIL_PATH = "/Users/aaron/.local/bin/blueutil"
AUDIT_LOG_PATH = Path("/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/MAC_MINI_KEYBOARD_HEALING_AUDIT.md")
RELEASE_SCRIPT = Path("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/keyboard/emergency_key_release.py")

def run_cmd(cmd: list[str], timeout: float = 10.0) -> tuple[int, str, str]:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def is_bt_connected() -> bool:
    if not os.path.exists(BLUEUTIL_PATH):
        return False
    rc, out, _ = run_cmd([BLUEUTIL_PATH, "--is-connected", MAGIC_KEYBOARD_ADDR], timeout=3.0)
    return out == "1"

def is_usb_connected() -> bool:
    rc, out, _ = run_cmd(["ioreg", "-r", "-c", "IOHIDDevice", "-l"], timeout=4.0)
    return "Magic Keyboard" in out and "USB" in out

def is_any_connected() -> tuple[bool, str]:
    if is_usb_connected():
        return True, "USB"
    if is_bt_connected():
        return True, "Bluetooth"
    return False, "Disconnected"

def try_connect() -> bool:
    if not os.path.exists(BLUEUTIL_PATH):
        return False
    print(f"[*] Attempting Bluetooth connection to Aaron's Magic Keyboard ({MAGIC_KEYBOARD_ADDR})...")
    rc, out, err = run_cmd([BLUEUTIL_PATH, "--connect", MAGIC_KEYBOARD_ADDR], timeout=8.0)
    connected = is_bt_connected()
    if connected:
        print("✅ Aaron's Magic Keyboard is CONNECTED via Bluetooth!")
        if RELEASE_SCRIPT.exists():
            subprocess.run([sys.executable, str(RELEASE_SCRIPT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    else:
        print(f"[-] Connection attempt returned: {out or err or 'Page Timeout (device sleeping or powered off)'}")
        return False

def update_audit_log(state: str, transport: str):
    if not AUDIT_LOG_PATH.exists():
        return
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n> **Telemetry Update [{ts}]:** Magic Keyboard link is `{state}` (Transport: `{transport}`).\n"
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass

def daemon_loop(interval_sec: float = 10.0):
    print(f"[*] Starting continuous Magic Keyboard Watchdog Daemon (interval={interval_sec}s)...")
    last_state = None
    while True:
        connected, transport = is_any_connected()
        curr_state = f"{'CONNECTED' if connected else 'DISCONNECTED'}:{transport}"
        if curr_state != last_state:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Keyboard link state change: {curr_state}")
            update_audit_log("CONNECTED" if connected else "DISCONNECTED", transport)
            last_state = curr_state

        if not connected:
            try_connect()
            time.sleep(interval_sec)
        else:
            time.sleep(30.0)

def watch_mode(max_wait_seconds: int = 30) -> int:
    print(f"[*] Starting Magic Keyboard Watchdog (Polling for up to {max_wait_seconds}s)...")
    print("    Tip: Verify physical switch on rear edge is ON (green showing), or plug in cable.")
    start = time.time()
    while time.time() - start < max_wait_seconds:
        connected, transport = is_any_connected()
        if connected:
            print(f"✅ Aaron's Magic Keyboard is actively connected via {transport}!")
            update_audit_log("CONNECTED", transport)
            return 0
        success = try_connect()
        if success:
            update_audit_log("CONNECTED", "Bluetooth")
            return 0
        time.sleep(3)

    print("\n⚠️ Magic Keyboard Watchdog Window Expired.")
    print("   The device did not respond within the timeout window.")
    print("   Empirical Root Cause:")
    print("   1. Physical Power Switch on rear edge of Magic Keyboard is switched OFF (red indicator).")
    print("   2. Battery is depleted (0%) - plug into Mac Mini USB port with Lightning/USB-C cable for 2-3 minutes.")
    print("   3. Once powered/plugged in, macOS auto-pairs immediately.")
    return 1

def main():
    parser = argparse.ArgumentParser(description="Aaron's Magic Keyboard Auto-Reconnector & Watchdog")
    parser.add_argument("--watch", type=int, default=15, help="Seconds to watch/poll for keyboard connection")
    parser.add_argument("--status", action="store_true", help="Check current connection status")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as silent background daemon")
    parser.add_argument("--interval", type=float, default=10.0, help="Polling interval in seconds")
    args = parser.parse_args()

    if args.status:
        connected, transport = is_any_connected()
        print(f"Aaron's Magic Keyboard ({MAGIC_KEYBOARD_ADDR}): {'CONNECTED via ' + transport if connected else 'NOT CONNECTED'}")
        if is_bt_connected():
            _, info, _ = run_cmd([BLUEUTIL_PATH, "--info", MAGIC_KEYBOARD_ADDR])
            print(info)
        return 0

    if args.daemon:
        daemon_loop(args.interval)
        return 0

    connected, transport = is_any_connected()
    if connected:
        print(f"✅ Aaron's Magic Keyboard is already connected via {transport}.")
        return 0

    return watch_mode(args.watch)

if __name__ == "__main__":
    sys.exit(main())

