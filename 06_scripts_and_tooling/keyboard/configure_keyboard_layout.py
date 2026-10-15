#!/usr/bin/env python3
"""
06_scripts_and_tooling/keyboard/configure_keyboard_layout.py
============================================================
Configures keyboard modifier mappings via macOS hidutil.
Specifically targets the 2.4G Wireless Receiver (VendorID 0x32c2, ProductID 0x18)
to swap physical Alt and Command (Win) keys for native Mac layout, or restore standard mapping.
"""

import sys
import json
import argparse
import subprocess

TARGET_VENDOR = 0x32c2  # 12994
TARGET_PRODUCT = 0x18   # 24

# HID Usage Page 0x07 (Keyboard)
# 0x7000000E2: Keyboard Left Alt / Option
# 0x7000000E3: Keyboard Left GUI / Command
# 0x7000000E6: Keyboard Right Alt / Option
# 0x7000000E7: Keyboard Right GUI / Command

SWAP_ALT_CMD_MAP = [
    {"HIDKeyboardModifierMappingSrc": 0x7000000E2, "HIDKeyboardModifierMappingDst": 0x7000000E3},
    {"HIDKeyboardModifierMappingSrc": 0x7000000E3, "HIDKeyboardModifierMappingDst": 0x7000000E2},
    {"HIDKeyboardModifierMappingSrc": 0x7000000E6, "HIDKeyboardModifierMappingDst": 0x7000000E7},
    {"HIDKeyboardModifierMappingSrc": 0x7000000E7, "HIDKeyboardModifierMappingDst": 0x7000000E6},
]

def get_mapping(matching_dict=None):
    cmd = ["hidutil", "property"]
    if matching_dict:
        cmd += ["--matching", json.dumps(matching_dict)]
    cmd += ["--get", "UserKeyMapping"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout.strip()

def set_mapping(mapping_list, matching_dict=None):
    payload = {"UserKeyMapping": mapping_list}
    cmd = ["hidutil", "property"]
    if matching_dict:
        cmd += ["--matching", json.dumps(matching_dict)]
    cmd += ["--set", json.dumps(payload)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout.strip() + res.stderr.strip()

def main():
    parser = argparse.ArgumentParser(description="Mac Mini Keyboard Modifier Configuration")
    parser.add_argument("--swap-alt-cmd", action="store_true", help="Swap Alt and Cmd on 2.4G PC Keyboard for native Mac layout")
    parser.add_argument("--restore-standard", action="store_true", help="Restore default 1:1 modifier mapping")
    parser.add_argument("--global-scope", action="store_true", help="Apply to all connected keyboards instead of targeted 2.4G dongle")
    parser.add_argument("--status", action="store_true", help="Show current modifier mapping state")

    args = parser.parse_args()

    matching = None if args.global_scope else {"VendorID": TARGET_VENDOR, "ProductID": TARGET_PRODUCT}

    if args.status or (not args.swap_alt_cmd and not args.restore_standard):
        print("=== CURRENT KEYBOARD MAPPING STATUS ===")
        print("Target Device (2.4G Receiver 0x32c2:0x18):")
        print(get_mapping({"VendorID": TARGET_VENDOR, "ProductID": TARGET_PRODUCT}))
        print("\nGlobal Scope:")
        print(get_mapping(None))
        return 0

    if args.swap_alt_cmd:
        scope_name = "Global" if args.global_scope else "2.4G Receiver 0x32c2:0x18"
        print(f"Applying Alt <-> Command swap (Target: {scope_name})...")
        ok, out = set_mapping(SWAP_ALT_CMD_MAP, matching)
        if ok:
            print("Successfully configured Alt <-> Command swap!")
            print("Physical Alt is now Command (Cmd+C, Cmd+V works naturally next to spacebar).")
            print("Physical Win key is now Option (Alt).")
        else:
            print(f"Failed to set mapping: {out}")
            return 1

    elif args.restore_standard:
        scope_name = "Global" if args.global_scope else "2.4G Receiver 0x32c2:0x18"
        print(f"Restoring standard 1:1 modifier mapping (Target: {scope_name})...")
        ok, out = set_mapping([], matching)
        if ok:
            print("Successfully restored default 1:1 mapping.")
        else:
            print(f"Failed to reset mapping: {out}")
            return 1

    print("\nUpdated State:")
    print(get_mapping(matching))
    return 0

if __name__ == "__main__":
    sys.exit(main())
