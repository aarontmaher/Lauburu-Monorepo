#!/usr/bin/env python3
"""
BetterDisplay Sovereign Controller for Lauburu Mesh Ecosystem
=============================================================
Provides deterministic programmatic control over BetterDisplay via `betterdisplaycli`:
- Display enumeration and telemetry (physical & virtual screens, brightness, resolution, refresh rate).
- Headless virtual dummy display lifecycle management (create, connect, disconnect, discard).
- Screen Lens Sovereign headless canvas provisioning (isolated virtual screen for test runs).
- Zero-mock execution, native JSON parsing, and graceful error handling.

Usage:
  python3 betterdisplay_controller.py status
  python3 betterdisplay_controller.py create-dummy --name "ScreenLensDummy" --aspect 16:9 --connect
  python3 betterdisplay_controller.py discard-dummy --name "ScreenLensDummy"
  python3 betterdisplay_controller.py set-brightness --name "MP245 E14VL" --level 0.8
"""

import sys
import os
import json
import subprocess
import argparse
from typing import Dict, List, Any, Optional

CLI_PATH = "/Users/aaron/.local/bin/betterdisplaycli"
APP_BUNDLE_CLI = "/Applications/BetterDisplay.app/Contents/MacOS/BetterDisplay"

def get_cli_bin() -> str:
    """Resolve active BetterDisplay CLI binary."""
    if os.path.isfile(CLI_PATH) and os.access(CLI_PATH, os.X_OK):
        return CLI_PATH
    if os.path.isfile(APP_BUNDLE_CLI) and os.access(APP_BUNDLE_CLI, os.X_OK):
        return APP_BUNDLE_CLI
    # Fallback to which
    res = subprocess.run(["which", "betterdisplaycli"], capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    raise FileNotFoundError("BetterDisplay CLI binary not found. Verify BetterDisplay is installed.")

def run_cli(*args: str, timeout: float = 5.0) -> subprocess.CompletedProcess:
    """Execute betterdisplaycli command with timeout and strict error handling."""
    bin_path = get_cli_bin()
    cmd = [bin_path] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

def get_identifiers() -> List[Dict[str, Any]]:
    """Retrieve all display and group identifiers as structured JSON."""
    res = run_cli("get", "-identifiers")
    if res.returncode != 0:
        return []
    
    raw = res.stdout.strip()
    # The output format is comma-separated JSON objects: {...},{...}
    # Wrap in array brackets if not already wrapped
    if not raw.startswith("["):
        wrapped = f"[{raw}]"
    else:
        wrapped = raw
    
    try:
        return json.loads(wrapped)
    except Exception:
        # Parse line by line or fallback
        items = []
        chunks = raw.split("},{")
        for i, chunk in enumerate(chunks):
            c = chunk
            if not c.startswith("{"):
                c = "{" + c
            if not c.endswith("}"):
                c = c + "}"
            try:
                items.append(json.loads(c))
            except Exception:
                pass
        return items

def get_display_telemetry(name: str) -> Dict[str, Any]:
    """Query brightness, resolution, and refresh rate for a named display."""
    data = {"name": name}
    
    # Brightness
    res = run_cli("get", f"-name={name}", "-brightness")
    if res.returncode == 0 and res.stdout.strip():
        try:
            data["brightness"] = float(res.stdout.strip())
        except ValueError:
            data["brightness"] = res.stdout.strip()
    
    # Resolution
    res = run_cli("get", f"-name={name}", "-resolution")
    if res.returncode == 0 and res.stdout.strip():
        data["resolution"] = res.stdout.strip()
        
    # Refresh Rate
    res = run_cli("get", f"-name={name}", "-refreshRate")
    if res.returncode == 0 and res.stdout.strip():
        data["refreshRate"] = res.stdout.strip()
        
    # Connected
    res = run_cli("get", f"-name={name}", "-connected")
    if res.returncode == 0 and res.stdout.strip():
        data["connected"] = res.stdout.strip()
        
    return data

def get_pro_status() -> bool:
    """Check if Pro features are unlocked."""
    res = run_cli("get", "-proAvailable")
    return res.returncode == 0 and res.stdout.strip().lower() in ("on", "true", "1", "yes")

def get_full_status() -> Dict[str, Any]:
    """Compile comprehensive system display status."""
    identifiers = get_identifiers()
    pro_active = get_pro_status()
    
    displays = []
    virtual_screens = []
    groups = []
    
    for item in identifiers:
        dev_type = item.get("deviceType")
        name = item.get("name", "")
        if dev_type == "Display":
            telem = get_display_telemetry(name)
            item.update(telem)
            displays.append(item)
        elif dev_type == "VirtualScreen":
            telem = get_display_telemetry(name)
            item.update(telem)
            virtual_screens.append(item)
        elif dev_type == "DisplayGroup":
            groups.append(item)
            
    return {
        "status": "ok",
        "cli_path": get_cli_bin(),
        "pro_available": pro_active,
        "physical_displays": displays,
        "virtual_screens": virtual_screens,
        "display_groups": groups,
    }

def create_virtual_screen(name: str = "ScreenLensDummy", aspect: str = "16:9", connect: bool = True) -> Dict[str, Any]:
    """Create a virtual dummy screen with specified aspect ratio and optionally connect it."""
    parts = aspect.split(":")
    w = parts[0] if len(parts) > 0 else "16"
    h = parts[1] if len(parts) > 1 else "9"
    
    args = [
        "create",
        "-type=VirtualScreen",
        f"-virtualScreenName={name}",
        f"-aspectWidth={w}",
        f"-aspectHeight={h}"
    ]
    
    res = run_cli(*args)
    if res.returncode != 0:
        return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}
        
    if connect:
        conn_res = run_cli("set", f"-name={name}", "-connected=on")
        if conn_res.returncode != 0:
            return {"success": True, "created": True, "connected": False, "conn_error": conn_res.stderr.strip()}
            
    # Verify creation
    identifiers = get_identifiers()
    created_item = next((d for d in identifiers if d.get("name") == name), None)
    return {
        "success": True,
        "name": name,
        "connected": connect,
        "details": created_item
    }

def discard_virtual_screen(name: str) -> Dict[str, Any]:
    """Cleanly discard a virtual screen by name."""
    res = run_cli("discard", f"-name={name}")
    if res.returncode != 0:
        return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}
    return {"success": True, "discarded": name}

def set_brightness(name: str, level: float) -> Dict[str, Any]:
    """Set display brightness level (0.0 to 1.0)."""
    val = max(0.0, min(1.0, level))
    res = run_cli("set", f"-name={name}", f"-brightness={val}")
    if res.returncode != 0:
        return {"success": False, "error": res.stderr.strip() or res.stdout.strip()}
    return {"success": True, "name": name, "brightness": val}

def main():
    parser = argparse.ArgumentParser(description="BetterDisplay Sovereign Controller")
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    # Status
    subparsers.add_parser("status", help="Get comprehensive display telemetry")
    
    # Create Dummy
    create_p = subparsers.add_parser("create-dummy", help="Create a virtual dummy display")
    create_p.add_argument("--name", default="ScreenLensDummy", help="Name of virtual screen")
    create_p.add_argument("--aspect", default="16:9", help="Aspect ratio (e.g., 16:9, 16:10, 20:9)")
    create_p.add_argument("--connect", action="store_true", default=True, help="Immediately connect the virtual screen")
    
    # Discard Dummy
    discard_p = subparsers.add_parser("discard-dummy", help="Discard a virtual dummy display")
    discard_p.add_argument("--name", required=True, help="Name of virtual screen to discard")
    
    # Set Brightness
    bright_p = subparsers.add_parser("set-brightness", help="Set brightness of a display")
    bright_p.add_argument("--name", required=True, help="Display name")
    bright_p.add_argument("--level", type=float, required=True, help="Brightness level (0.0 - 1.0)")
    
    args = parser.parse_args()
    
    if args.action == "status":
        st = get_full_status()
        print(json.dumps(st, indent=2))
    elif args.action == "create-dummy":
        out = create_virtual_screen(args.name, args.aspect, args.connect)
        print(json.dumps(out, indent=2))
    elif args.action == "discard-dummy":
        out = discard_virtual_screen(args.name)
        print(json.dumps(out, indent=2))
    elif args.action == "set-brightness":
        out = set_brightness(args.name, args.level)
        print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
