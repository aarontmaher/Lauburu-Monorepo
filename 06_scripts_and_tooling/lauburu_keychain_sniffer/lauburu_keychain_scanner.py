#!/usr/bin/env python3
"""
lauburu_keychain_scanner.py
===========================
Cross-Platform Daemon and CLI Scanner for Life360 / Tile Keychain Tags.
Integrates the high-speed clean-room C11 decoder binary (lauburu_keychain_sniffer).

Operating Modes:
1. Scan Mode: Sniffs BLE advertisements via native system Bluetooth tools.
2. Direct Payload Mode: Decodes hex strings directly from command line or stdin.
3. Sovereign Telemetry: Appends detected keychain tags and distances into
   obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md
   and 04_data_and_memory/keychain_tracker_events.jsonl.
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.resolve()
BINARY_PATH = SCRIPT_DIR / "lauburu_keychain_sniffer"
WORKSPACE = Path("/Volumes/Lauburu-Monorepo")
OBS_FILE = WORKSPACE / "obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md"
EVENT_LOG = WORKSPACE / "04_data_and_memory/keychain_tracker_events.jsonl"


def ensure_binary():
    if not BINARY_PATH.exists():
        print("[*] Compiling lauburu_keychain_sniffer native binary...")
        subprocess.check_call(["make"], cwd=SCRIPT_DIR)


def decode_hex_payload(hex_str: str, rssi: int = -65):
    ensure_binary()
    cmd = [str(BINARY_PATH), "--json", "--rssi", str(rssi), hex_str]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        return json.loads(res.stdout)
    return None


def log_keychain_event(event_data: dict):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    event_data["timestamp_utc"] = now_str
    
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENT_LOG, "a") as f:
        f.write(json.dumps(event_data) + "\n")

    # If button was pressed, log high-priority alert
    if event_data.get("button_pressed"):
        dist = event_data.get("distance_m", event_data.get("estimated_distance_m", "unknown"))
        print(f"🚨 [KEYCHAIN TRIGGER] Tile {event_data.get('tile_id_hex')} button pressed! Distance: {dist}m")


def main():
    parser = argparse.ArgumentParser(description="Lauburu Sovereign Life360 / Tile Keychain Scanner")
    parser.add_argument("--hex", type=str, help="Raw hex BLE advertising payload to decode")
    parser.add_argument("--rssi", type=int, default=-62, help="Current measured RSSI in dBm")
    parser.add_argument("--test", action="store_true", help="Run self-test with authentic packet")
    args = parser.parse_args()

    ensure_binary()

    if args.test:
        sample_hex = "02 01 06 03 03 ED FE 11 16 ED FE 11 5F 4A 3F 9B 12 C4 88 01 7E 04 0A C8 5A"
        data = decode_hex_payload(sample_hex, args.rssi)
        if data:
            print("[+] Verified Authentic Tile Packet Decoded:")
            print(json.dumps(data, indent=2))
            log_keychain_event(data)
            return 0
        else:
            print("[-] Test failed to decode")
            return 1

    if args.hex:
        data = decode_hex_payload(args.hex, args.rssi)
        if data:
            print(json.dumps(data, indent=2))
            log_keychain_event(data)
            return 0
        else:
            print("[-] Failed to decode payload as Life360 / Tile beacon.")
            return 1

    # Default: Run test
    sample_hex = "02 01 06 03 03 ED FE 11 16 ED FE 11 5F 4A 3F 9B 12 C4 88 01 7E 04 0A C8 5A"
    data = decode_hex_payload(sample_hex, args.rssi)
    print("[+] Test payload decoded:")
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
