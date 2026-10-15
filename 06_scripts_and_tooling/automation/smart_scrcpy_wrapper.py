#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smart_scrcpy_wrapper.py
========================
Screen Lens Sovereign Smart Scrcpy Wrapper & Device Resolver.
Bypasses 'ERROR: Multiple (2) ADB devices' by automatically detecting
active devices, pruning stale endpoints, and selecting the optimal device.

Governed by:
- Rule #0: Zero-Mock Empirical Truth
- Rule #7: Live Screen Broadcasting & Continuous Telemetry
- Rule #10: Screen Lens Sovereign Automation Invariant
"""

import os
import sys
import time
import select
import subprocess
from typing import List, Dict, Optional

REAL_SCRCPY = next((
    p for p in [
        "/opt/homebrew/bin/scrcpy",
        "/usr/local/bin/scrcpy",
        "/Users/aaron/.homebrew/bin/scrcpy"
    ] if os.path.exists(p)
), "scrcpy")


def get_online_devices() -> List[Dict[str, str]]:
    """Discovers genuinely active ADB devices, ignoring offline/unauthorized."""
    try:
        res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=2.0)
        lines = res.stdout.strip().split("\n")[1:]
        devices = []
        for line in lines:
            line = line.strip()
            if not line or "offline" in line or "unauthorized" in line:
                continue
            parts = line.split()
            if len(parts) < 2 or parts[1] != "device":
                continue
            serial = parts[0]
            model = "Android Device"
            product = ""
            for p in parts:
                if p.startswith("model:"):
                    model = p.split(":", 1)[1]
                elif p.startswith("product:"):
                    product = p.split(":", 1)[1]
            
            display_name = model
            if "mustang" in product.lower() or "pixel" in model.lower():
                display_name = "Google Pixel 10 Pro XL (L6)"
            elif "y2s" in product.lower() or "sm_g986b" in model.lower() or "g986" in model.lower():
                display_name = "Samsung Galaxy S20+ (L7)"
            
            devices.append({
                "serial": serial,
                "model": model,
                "product": product,
                "display_name": display_name,
                "raw": line
            })
        return devices
    except Exception as e:
        return []


def prune_stale_connections():
    """Disconnects offline or duplicate adb tcpip endpoints."""
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2.0)
        for line in res.stdout.strip().split("\n")[1:]:
            if "offline" in line and ":" in line:
                endpoint = line.split()[0]
                subprocess.run(["adb", "disconnect", endpoint], capture_output=True, timeout=1.0)
    except Exception:
        pass


def pick_device_noninteractive(devices: List[Dict[str, str]]) -> Optional[str]:
    """Deterministic, non-blocking device selector for automated 24/7 pipelines."""
    if not devices:
        return None
    if len(devices) == 1:
        return devices[0]["serial"]

    env_target = os.environ.get("SCRCPY_DEVICE", "").strip().lower()
    if env_target:
        for d in devices:
            serial_str = str(d.get("serial", "")).lower()
            model_str = str(d.get("model", "")).lower()
            disp_str = str(d.get("display_name", d.get("info", ""))).lower()
            if env_target in serial_str or env_target in model_str or env_target in disp_str:
                return str(d.get("serial", ""))

    # Prefer Samsung Galaxy S20+ (L7 Active Actuator) over Sanctuary Phone (L6 Pixel)
    for d in devices:
        serial_str = str(d.get("serial", ""))
        disp_str = f"{d.get('display_name', '')} {d.get('model', '')} {d.get('info', '')}".lower()
        if "samsung" in disp_str or "s20" in disp_str or "g986" in disp_str or "192.168.8.101" in serial_str:
            return serial_str
    return str(devices[0].get("serial", ""))



def pick_device(devices: List[Dict[str, str]]) -> Optional[str]:
    """Selects target device based on env var, interactive prompt, or smart default."""
    if not devices:
        return None
    if len(devices) == 1:
        return devices[0]["serial"]

    # 1. Check environment variable override
    env_target = os.environ.get("SCRCPY_DEVICE", "").strip().lower()
    if env_target:
        for d in devices:
            if (env_target in d["serial"].lower() or 
                env_target in d["model"].lower() or 
                env_target in d["display_name"].lower()):
                return d["serial"]

    # 2. Interactive prompt if stdin is a terminal and not running in batch/automated mode
    if sys.stdin.isatty() and not os.environ.get("LENS_NONINTERACTIVE"):
        print("=" * 60)
        print("  👁️  Screen Lens Sovereign — Scrcpy Smart Device Selector")
        print("=" * 60)
        print("Multiple active ADB devices detected:")
        for idx, d in enumerate(devices, 1):
            print(f"  [{idx}] {d['display_name']} ({d['serial']})")
        print(f"  [Default: 1 - {devices[0]['display_name']}]")
        print("-" * 60)
        sys.stdout.write("Select device [1-{}]: ".format(len(devices)))
        sys.stdout.flush()

        try:
            # Wait up to 3 seconds for user input, then default to option 1
            rlist, _, _ = select.select([sys.stdin], [], [], 3.0)
            if rlist:
                choice = sys.stdin.readline().strip()
                if choice.isdigit() and 1 <= int(choice) <= len(devices):
                    selected = devices[int(choice) - 1]["serial"]
                    print(f"-> Launching on {devices[int(choice) - 1]['display_name']}...\n")
                    return selected
        except Exception:
            pass

        print(f"\n-> Auto-selecting default: {devices[0]['display_name']}...\n")
        return devices[0]["serial"]

    # 3. Non-interactive default (prefer Samsung S20+ if UI testbench, or first active)
    return pick_device_noninteractive(devices)


def get_physical_usb_android_device() -> Optional[str]:
    """Detects if an Android device is physically plugged into the Mac Mini via USB."""
    try:
        res = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=2.0)
        for line in res.stdout.strip().split("\n")[1:]:
            line = line.strip()
            if not line or "offline" in line or "unauthorized" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                if ":" not in serial and not serial.startswith("adb-"):
                    return serial
                for p in parts:
                    if p.startswith("usb:"):
                        return serial
    except Exception:
        pass
    return None


def log_scrcpy_session(serial: str, args: List[str]):
    """Logs scrcpy launch event to Obsidian vault."""
    obs_file = "/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_SCRCPY_ACTIVITY.md"
    try:
        os.makedirs(os.path.dirname(obs_file), exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"- `{timestamp}` | **Device:** `{serial}` | **Args:** `{' '.join(args)}`\n"
        with open(obs_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def get_device_sdk_version(serial: str) -> int:
    """Returns the Android SDK version (API level) for the device."""
    try:
        res = subprocess.run(["adb", "-s", serial, "shell", "getprop", "ro.build.version.sdk"],
                             capture_output=True, text=True, timeout=1.5)
        out = res.stdout.strip()
        if out.isdigit():
            return int(out)
    except Exception:
        pass
    return 33  # Default modern Android


def get_scrcpy_5_sovereign_profile(
    serial: Optional[str] = None,
    sdk_override: Optional[int] = None,
    devices_override: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, object]:
    """
    Returns the Scrcpy 5.0 Sovereign UHID + 60 FPS @ 16M bitrate + Shizuku rish
    capabilities profile and active ADB device matrix.
    """
    if devices_override is not None:
        devices = devices_override
    else:
        prune_stale_connections()
        devices = get_online_devices()
    chosen = serial or pick_device_noninteractive(devices) or "192.168.8.101:5555"
    online_serials = {d.get("serial") for d in devices}
    if sdk_override is not None:
        sdk_level = int(sdk_override)
    elif chosen in online_serials and devices_override is None:
        sdk_level = get_device_sdk_version(chosen)
    else:
        sdk_level = 34
    uhid_supported = sdk_level >= 30
    kb_mode_val = "uhid" if uhid_supported else "sdk"
    mouse_mode_val = "uhid" if uhid_supported else "sdk"
    kb_mode = f"--keyboard={kb_mode_val}"
    mouse_mode = f"--mouse={mouse_mode_val}"
    scrcpy_exists = os.path.exists(REAL_SCRCPY) or subprocess.run(["which", "scrcpy"], capture_output=True).returncode == 0
    rec_flags = [
        f"--serial={chosen}",
        "--max-fps=60",
        "--video-bit-rate=16M",
        kb_mode,
        mouse_mode,
        "--stay-awake",
    ]
    rish_tpl = f"adb -s {chosen} shell \"/data/local/tmp/rish -c '<cmd>' 2>&1\""
    return {
        "protocol": "Scrcpy 5.0 Sovereign UHID",
        "protocol_version": "5.0-SOVEREIGN-UHID",
        "scrcpy_binary": REAL_SCRCPY,
        "scrcpy_binary_installed": bool(scrcpy_exists),
        "online_adb_devices": devices,
        "online_devices_count": len(devices),
        "selected_serial": chosen,
        "target_serial": chosen,
        "android_sdk_level": sdk_level,
        "android_sdk": sdk_level,
        "uhid_hardware_hid_supported": uhid_supported,
        "keyboard_mode": kb_mode_val,
        "mouse_mode": mouse_mode_val,
        "max_fps": 60,
        "video_bit_rate": "16M",
        "recommended_flags": rec_flags,
        "command": f"{REAL_SCRCPY} " + " ".join(rec_flags),
        "otg_headless_hid_flags": [
            f"--serial={chosen}",
            kb_mode,
            mouse_mode,
            "--no-video",
            "--no-audio",
        ],
        "shizuku_rish_bridge": rish_tpl,
        "shizuku_rish_command_template": rish_tpl,
    }


def main():
    args = sys.argv[1:]

    if "--scrcpy-5-status" in args or "--status-json" in args:
        import json as _json
        print(_json.dumps(get_scrcpy_5_sovereign_profile(), indent=2))
        sys.exit(0)

    # Handle OTG mode and Scrcpy 5.0 Sovereign UHID mode translation
    has_otg = "--otg" in args
    has_scrcpy5 = "--scrcpy-5" in args
    if has_scrcpy5:
        args = [a for a in args if a != "--scrcpy-5"]
    physical_usb = get_physical_usb_android_device() if has_otg else None

    # Check if target device explicitly provided
    target_serial = None
    for i, a in enumerate(args):
        if a in ("-s", "--serial") and i + 1 < len(args):
            target_serial = args[i + 1]
            break
        elif a.startswith("-s="):
            target_serial = a.split("=", 1)[1]
            break
        elif a.startswith("--serial="):
            target_serial = a.split("=", 1)[1]
            break

    if has_otg:
        if physical_usb:
            # Physical USB Android device attached: explicitly target it so libusb doesn't collide with host hubs
            if not target_serial:
                args = ["-s", physical_usb] + args
                target_serial = physical_usb
        else:
            # No physical USB Android device attached to Mac: translate --otg to network HID mode
            if not target_serial:
                prune_stale_connections()
                devices = get_online_devices()
                target_serial = pick_device(devices)
                if target_serial:
                    args = ["-s", target_serial] + args

            # Inspect target SDK version: UHID supported on API 30+ (Android 11+)
            sdk_level = get_device_sdk_version(target_serial) if target_serial else 33
            kb_mode = "--keyboard=uhid" if sdk_level >= 30 else "--keyboard=sdk"
            mouse_mode = "--mouse=uhid" if sdk_level >= 30 else "--mouse=sdk"

            args = [a for a in args if a != "--otg"]
            for flag in (kb_mode, mouse_mode, "--no-video", "--no-audio"):
                if flag not in args:
                    args.append(flag)
            # Polish window title if generic
            for i, a in enumerate(args):
                if a == "--window-title=ScrcpyGui" or a == "--window-title=\"ScrcpyGui\"":
                    args[i] = "--window-title=ScrcpyGui (OTG Mode)"
            mode_name = "UHID hardware" if sdk_level >= 30 else "SDK API"
            print(f"[Screen Lens Sovereign] OTG Mode active via {mode_name} emulation (API {sdk_level}).", file=sys.stderr)
            print("[Screen Lens Sovereign] Keyboard & Mouse HID control enabled (zero video/audio stream).", file=sys.stderr)

    # If user explicitly specified device targeting flags or query flags, pass directly
    has_target = any(
        arg in ("-s", "--serial", "-d", "--select-usb", "-e", "--select-tcpip") or
        arg.startswith("-s=") or arg.startswith("--serial=") or
        arg in ("--version", "-v", "--help", "-h")
        for arg in args
    )

    if not has_target:
        prune_stale_connections()
        devices = get_online_devices()
        selected_serial = pick_device_noninteractive(devices) if has_scrcpy5 else pick_device(devices)
        if selected_serial:
            args = ["-s", selected_serial] + args
            target_serial = selected_serial
            log_scrcpy_session(selected_serial, args)

    if has_scrcpy5 and not has_otg:
        sdk_level = get_device_sdk_version(target_serial) if target_serial else 34
        kb_mode = "--keyboard=uhid" if sdk_level >= 30 else "--keyboard=sdk"
        mouse_mode = "--mouse=uhid" if sdk_level >= 30 else "--mouse=sdk"
        for flag in ("--max-fps=60", "--video-bit-rate=16M", kb_mode, mouse_mode, "--stay-awake"):
            if flag not in args:
                args.append(flag)

    if not os.path.exists(REAL_SCRCPY):
        print(f"Error: scrcpy binary not found at {REAL_SCRCPY}", file=sys.stderr)
        sys.exit(1)

    # Replace current process with real scrcpy
    os.execv(REAL_SCRCPY, [REAL_SCRCPY] + args)


if __name__ == "__main__":
    main()

