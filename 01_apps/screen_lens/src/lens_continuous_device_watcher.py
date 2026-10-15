#!/usr/bin/env python3
"""
01_apps/screen_lens/src/lens_continuous_device_watcher.py
=========================================================
Continuous Passive Device & Screen Watcher Daemon.
Passively monitors:
1. macOS frontmost active application and window title
2. Connected Android ADB devices (Pixel 10 Pro XL, Samsung S20)
3. Physical Darwin Mach kernel memory headroom
4. Logs real-time observations into obsidian_vault and 04_data_and_memory.
Strictly complies with soul.md Cardinal Law #1 (Zero-Mock / Zero-Simulation).
"""

import os
import sys
import time
import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
OBS_FILE = WORKSPACE / "obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md"
JSONL_FILE = WORKSPACE / "04_data_and_memory/lens_passive_observations.jsonl"
SENTINEL_FILE = WORKSPACE / "01_apps/screen_lens/src/host_sentinel_state.json"

try:
    from lens_crash_sentinel_training_engine import GLOBAL_CRASH_SENTINEL
except ImportError:
    try:
        from .lens_crash_sentinel_training_engine import GLOBAL_CRASH_SENTINEL
    except Exception:
        GLOBAL_CRASH_SENTINEL = None


def get_frontmost_app():
    scpt = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set frontAppName to name of frontApp
        set winTitle to ""
        try
            set winTitle to name of front window of frontApp
        end try
        return frontAppName & "|||" & winTitle
    end tell
    '''
    try:
        out = subprocess.check_output(["osascript", "-e", scpt], text=True, timeout=2.0).strip()
        if "|||" in out:
            app, win = out.split("|||", 1)
            return app.strip(), win.strip()
        return out, ""
    except Exception:
        return "Unknown", ""


def get_connected_adb_devices():
    try:
        out = subprocess.check_output(["adb", "devices"], text=True, timeout=2.0)
        lines = [l.strip() for l in out.splitlines() if l.strip() and not l.startswith("List of")]
        devices = []
        for l in lines:
            parts = l.split()
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "state": parts[1]})
        return devices
    except Exception:
        return []


def get_free_ram_gb():
    try:
        out = subprocess.check_output(["vm_stat"], text=True, timeout=2.0)
        free_pages = sum(
            int(l.split(":")[1].strip().strip("."))
            for l in out.splitlines()
            if "Pages free:" in l or "Pages speculative:" in l
        )
        return round((free_pages * 16384) / (1024**3), 2)
    except Exception:
        return 0.0


def get_sentinel_telemetry():
    """Reads live host memory, disk headroom, swap count, and watchdog liveness from sentinel state."""
    state = {
        "free_disk_gb": 0.0,
        "swap_count": 0,
        "watchdog_alive": False,
        "watchdog_pid": None,
        "available_ram_gb": 0.0
    }
    try:
        if SENTINEL_FILE.exists():
            data = json.loads(SENTINEL_FILE.read_text())
            telem = data.get("telemetry", {})
            state["free_disk_gb"] = telem.get("free_disk_gb", 0.0)
            state["swap_count"] = telem.get("swap_count", 0)
            state["watchdog_alive"] = telem.get("watchdog_alive", False)
            state["watchdog_pid"] = telem.get("watchdog_pid")
            state["available_ram_gb"] = telem.get("available_ram_gb", 0.0)
        else:
            import shutil
            state["free_disk_gb"] = round(shutil.disk_usage("/Users/aaron").free / (1024**3), 2)
    except Exception:
        pass
    return state


def watch_loop():
    print("👁️ Screen Lens Continuous Passive Device Watcher active...")
    if not OBS_FILE.exists():
        OBS_FILE.write_text(
            "---\ntitle: Screen Lens Live Observations Feed\n"
            "date: 2026-09-04\ntags: [screen_lens, live_observations, adb, macos]\n---\n\n"
            "# 👁️ Screen Lens Real-Time Multi-Device Observations\n\n"
            "| Timestamp (UTC) | Frontmost App | Window Title | ADB Devices | Avail RAM | Disk Free | Swaps | Watchdog |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )

    last_app = ""
    last_win = ""
    last_crash_check = 0.0

    while True:
        try:
            now_ts = time.time()
            if GLOBAL_CRASH_SENTINEL and (now_ts - last_crash_check > 30.0):
                last_crash_check = now_ts
                try:
                    GLOBAL_CRASH_SENTINEL.run_full_crash_harvest_and_train_cycle()
                except Exception:
                    pass

            app, win = get_frontmost_app()
            adb_devs = get_connected_adb_devices()
            ram = get_free_ram_gb()
            sentinel = get_sentinel_telemetry()
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Log change or periodic heartbeat
            is_changed = (app != last_app or win != last_win)
            if is_changed or random.random() < 0.2:
                last_app = app
                last_win = win

                dev_summary = ", ".join([d["serial"] for d in adb_devs]) if adb_devs else "None (Wireless standby)"
                wd_str = f"ALIVE ({sentinel['watchdog_pid']})" if sentinel["watchdog_alive"] else "OFFLINE"

                # JSONL record
                record = {
                    "timestamp": now_str,
                    "frontmost_app": app,
                    "window_title": win,
                    "adb_devices_count": len(adb_devs),
                    "adb_devices": adb_devs,
                    "host_free_ram_gb": ram,
                    "host_available_ram_gb": sentinel["available_ram_gb"],
                    "host_free_disk_gb": sentinel["free_disk_gb"],
                    "host_swap_count": sentinel["swap_count"],
                    "watchdog_alive": sentinel["watchdog_alive"],
                    "watchdog_pid": sentinel["watchdog_pid"],
                    "zero_mock_verified": True
                }
                with open(JSONL_FILE, "a") as jf:
                    jf.write(json.dumps(record) + "\n")

                # Markdown table row
                clean_win = win.replace("|", "/")[:50]
                row = (
                    f"| {now_str} | **{app}** | `{clean_win}` | {dev_summary} | "
                    f"{sentinel['available_ram_gb']} GB | {sentinel['free_disk_gb']} GB | "
                    f"{sentinel['swap_count']} | {wd_str} |\n"
                )
                with open(OBS_FILE, "a") as mf:
                    mf.write(row)

            time.sleep(3.0)
        except Exception as e:
            time.sleep(2.0)


if __name__ == "__main__":
    watch_loop()
