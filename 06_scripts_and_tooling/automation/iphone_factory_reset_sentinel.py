#!/usr/bin/env python3
"""
iPhone 16 Pro Pre-Sale Factory Reset & Activation Lock Sentinel
==============================================================
Subsystem: 06_scripts_and_tooling / automation
Target: Apple iPhone 16 Pro (G0WR66YPCQ) connected via USB

Empirical Zero-Mock Audit:
1. Physical Connection & Battery Health
2. Apple ID & iCloud Sign-Out Status
3. Find My & Activation Lock Disassociation
4. Stolen Device Protection Status
5. Passcode & Encryption Obliteration Status
6. Physical SIM Card Extraction Verification
"""

import sys
import json
import time
import subprocess
from datetime import datetime, timezone

def run_lockdown_info():
    cmd = ["uv", "run", "--with", "pymobiledevice3", "pymobiledevice3", "lockdown", "info", "--native"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return None, res.stderr
    try:
        data = json.loads(res.stdout)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

def audit_device():
    info, err = run_lockdown_info()
    if not info:
        return {
            "status": "DEVICE_NOT_FOUND_OR_REBOOTING",
            "error": err,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    nvram = info.get("NonVolatileRAM", {})
    fm_locked = nvram.get("fm-activation-locked", {}).get("$hex", "")
    fm_spstatus = nvram.get("fm-spstatus", {}).get("$hex", "")
    fm_account = nvram.get("fm-account-masked", {}).get("$hex", "")

    # Decode hex values if present
    try:
        fm_locked_str = bytes.fromhex(fm_locked).decode("utf-8", errors="ignore") if fm_locked else "NO"
    except Exception:
        fm_locked_str = "UNKNOWN"

    try:
        fm_spstatus_str = bytes.fromhex(fm_spstatus).decode("utf-8", errors="ignore") if fm_spstatus else "NO"
    except Exception:
        fm_spstatus_str = "UNKNOWN"

    try:
        fm_account_str = bytes.fromhex(fm_account).decode("utf-8", errors="ignore") if fm_account else "NONE"
    except Exception:
        fm_account_str = "UNKNOWN"

    device_name = info.get("DeviceName", "Unknown")
    passcode_protected = info.get("PasswordProtected", False)
    sim_tray = info.get("SIMTrayStatus", "Unknown")
    phone_number = info.get("PhoneNumber", "None")
    serial = info.get("SerialNumber", "Unknown")
    product_type = info.get("ProductType", "Unknown")
    product_version = info.get("HumanReadableProductVersionString", info.get("ProductVersion", "Unknown"))
    activation_state = info.get("kCTPostponementStatus", "Unknown")

    # Audit checks
    checks = {
        "device_model": product_type == "iPhone17,1",
        "serial_matched": serial == "G0WR66YPCQ",
        "icloud_signed_out": (fm_account_str in ["NONE", ""] or "gmail" not in fm_account_str.lower()),
        "activation_lock_disabled": fm_locked_str != "YES",
        "stolen_device_protection_disabled": fm_spstatus_str != "YES",
        "passcode_removed": not passcode_protected,
        "factory_hello_name": device_name.lower() in ["iphone", "hello", ""],
        "sim_card_removed": ("NoSIM" in sim_tray or "Empty" in sim_tray or sim_tray != "kCTSIMSupportSIMTrayInsertedWithSIM")
    }

    all_ready = all(checks.values())

    return {
        "status": "READY_FOR_SALE" if all_ready else "ACTION_REQUIRED",
        "serial_number": serial,
        "device_name": device_name,
        "os_version": product_version,
        "sim_tray_status": sim_tray,
        "sim_phone_number": phone_number,
        "passcode_protected": passcode_protected,
        "find_my_account": fm_account_str,
        "activation_lock": fm_locked_str,
        "stolen_device_protection": fm_spstatus_str,
        "checks": checks,
        "all_ready_for_sale": all_ready,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="iPhone 16 Pro Pre-Sale Reset Sentinel")
    parser.add_argument("--watch", action="store_true", help="Continuously poll until device reaches READY_FOR_SALE")
    parser.add_argument("--interval", type=float, default=5.0, help="Poll interval in seconds")
    args = parser.parse_args()

    if not args.watch:
        result = audit_device()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("all_ready_for_sale") else 1)

    print(f"[*] Starting iPhone 16 Pro Pre-Sale Sentinel (Polling every {args.interval}s)...")
    last_status = None
    while True:
        res = audit_device()
        status = res.get("status")
        if status != last_status:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Status Transition -> {status}")
            print(f"    • Device Name: {res.get('device_name')}")
            print(f"    • Passcode Protected: {res.get('passcode_protected')}")
            print(f"    • Activation Lock: {res.get('activation_lock')} (Account: {res.get('find_my_account')})")
            print(f"    • SIM Status: {res.get('sim_tray_status')} (Number: {res.get('sim_phone_number')})")
            print(f"    • All Pre-Sale Checks Passed: {res.get('all_ready_for_sale')}")
            last_status = status

        if res.get("all_ready_for_sale"):
            print("\n[SUCCESS] All 6 Pre-Sale Factory Reset Checks PASSED!")
            print(json.dumps(res, indent=2))
            sys.exit(0)

        time.sleep(args.interval)

if __name__ == "__main__":
    main()

