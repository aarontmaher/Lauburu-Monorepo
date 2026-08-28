#!/usr/bin/env python3
"""
Samsung S20+ Dedicated Router Gateway Auto-Revert Watchdog Daemon
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Primary ADB path  : Tailscale TCP  → 100.84.40.95:5555
• Fallback ADB path : GL.iNet Router → SSH 192.168.8.1 (USB serial usb:1-1)
• When Tailscale VPN drops the fallback breaks Doze and revives it.
• NEVER force-stops com.tailscale.ipn or com.termux — always protects them.
"""

import subprocess
import time
import sys
import os
import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
TARGET_TAILSCALE   = os.environ.get("S20_ADB_TARGET", "100.84.40.95:5555")
ROUTER_SSH_HOST    = "192.168.8.1"
ROUTER_ADB_SERIAL  = "usb:1-1"
ADB_BIN            = "/Users/aaron/.local/bin/adb" if os.path.isfile("/Users/aaron/.local/bin/adb") else "adb"
CHECK_INTERVAL     = 30
OVERRIDE_TIMEOUT   = 900
TAILSCALE_MISS_MAX = 3

_active_target  = TARGET_TAILSCALE
_tailscale_miss = 0

def _ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_adb(cmd, timeout=12):
    try:
        res = subprocess.run(
            [ADB_BIN, "-s", _active_target, "shell", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return res.stdout.strip()
    except Exception:
        return None

def _ssh_adb(cmd, timeout=15):
    try:
        res = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             ROUTER_SSH_HOST, f"adb -s {ROUTER_ADB_SERIAL} shell '{cmd}'"],
            capture_output=True, text=True, timeout=timeout
        )
        return res.stdout.strip()
    except Exception:
        return None

def _router_adb_available():
    try:
        # Start ADB server first (idempotent), then query devices
        subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             ROUTER_SSH_HOST, "adb start-server >/dev/null 2>&1; sleep 1; adb devices"],
            capture_output=True, text=True, timeout=12
        )
        # Second call — guaranteed daemon is up now
        out = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
             ROUTER_SSH_HOST, "adb devices"],
            capture_output=True, text=True, timeout=8
        ).stdout
        return "R3CN40CJJ1R" in out or "SM_G986B" in out or "y2s" in out
    except Exception:
        return False

def _revive_via_router():
    global _active_target, _tailscale_miss
    if not _router_adb_available():
        print(f"[{_ts()}] ❌ Router ADB bridge unavailable. Will retry.", flush=True)
        return
    print(f"[{_ts()}] 🔧 Reviving S20 via router USB bridge…", flush=True)
    _ssh_adb("tcpip 5555", timeout=8)
    time.sleep(2)
    _ssh_adb("input keyevent 26; sleep 1; input keyevent 26", timeout=6)
    time.sleep(3)
    revival = (
        "dumpsys deviceidle whitelist +com.tailscale.ipn +com.termux +com.termux.boot; "
        "cmd appops set com.tailscale.ipn RUN_IN_BACKGROUND allow; "
        "cmd appops set com.tailscale.ipn RUN_ANY_IN_BACKGROUND allow; "
        "cmd appops set com.termux RUN_IN_BACKGROUND allow; "
        # Android 14+: startservice requires foreground permission; use monkey or direct am start
        "monkey -p com.tailscale.ipn -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; "
        "am broadcast --user 0 -a com.termux.RUN_COMMAND "
        "--es com.termux.RUN_COMMAND_PATH /data/data/com.termux/files/usr/bin/bash "
        "--esa com.termux.RUN_COMMAND_ARGUMENTS '-c,termux-wake-lock' "
        "--ez com.termux.RUN_COMMAND_BACKGROUND true "
        "-n com.termux/com.termux.app.RunCommandService; "
        "echo REVIVAL_DONE"
    )
    out = _ssh_adb(revival, timeout=20)
    print(f"[{_ts()}] 🔧 Revival: {out}", flush=True)
    for i in range(6):
        time.sleep(5)
        # Use grep with escaped dot to match literal "inet 100." prefix
        tun = _ssh_adb("ip addr show tun0 2>/dev/null | grep -F 'inet 100.'", timeout=8)
        if tun:
            print(f"[{_ts()}] ✅ Tailscale tun0 back: {tun}", flush=True)
            subprocess.run([ADB_BIN, "connect", TARGET_TAILSCALE],
                           capture_output=True, text=True, timeout=6)
            _active_target  = TARGET_TAILSCALE
            _tailscale_miss = 0
            return
        print(f"[{_ts()}] ⏳ Waiting for tun0… ({(i+1)*5}s)", flush=True)
    print(f"[{_ts()}] ⚠️  tun0 not yet up. Will keep retrying each cycle.", flush=True)

def ensure_connected():
    global _active_target, _tailscale_miss
    try:
        subprocess.run([ADB_BIN, "connect", TARGET_TAILSCALE],
                       capture_output=True, text=True, timeout=6)
        test = subprocess.run(
            [ADB_BIN, "-s", TARGET_TAILSCALE, "shell", "echo ping"],
            capture_output=True, text=True, timeout=6
        )
        if "ping" in test.stdout:
            _active_target  = TARGET_TAILSCALE
            _tailscale_miss = 0
            return True
    except Exception:
        pass
    _tailscale_miss += 1
    print(f"[{_ts()}] ⚠️  Tailscale ADB miss #{_tailscale_miss}/{TAILSCALE_MISS_MAX}", flush=True)
    if _tailscale_miss >= TAILSCALE_MISS_MAX:
        _revive_via_router()
    return False

BASELINE_CMDS = """
    # 0. DISABLE DOZE — this is a dedicated router gateway, never needs deep idle
    dumpsys deviceidle disable >/dev/null 2>&1 || true
    settings put global app_standby_enabled 0
    settings put global adaptive_battery_management_enabled 0

    settings put global protect_battery 1
    settings put global stay_on_while_plugged_in 0
    settings put system screen_brightness 1
    settings put system screen_brightness_mode 0
    settings put system screen_off_timeout 15000
    settings put system aod_mode 0
    settings put secure doze_always_on 0
    settings put system refresh_rate_mode 0
    settings put system high_refresh_rate_mode 0
    settings put secure wake_gesture_enabled 0
    settings put global window_animation_scale 0.0
    settings put global transition_animation_scale 0.0
    settings put global animator_duration_scale 0.0
    settings put global mobile_data_always_on 1
    settings put global wifi_scan_throttle_enabled 1
    settings put global wifi_verbose_logging_enabled 0
    settings put global tether_dun_required 0
    settings put global tether_offload_subvention 1
    settings put global cached_apps_freezer enabled
    settings put global settings_enable_monitor_phantom_procs false
    settings put global app_standby_enabled 1
    settings put global send_action_app_error 0
    settings put global bugreport_in_power_menu 0
    settings put secure usb_audio_automatic_routing_disabled 1
    media volume --stream 1 --set 0 2>/dev/null || true
    media volume --stream 2 --set 0 2>/dev/null || true
    media volume --stream 3 --set 0 2>/dev/null || true
    media volume --stream 5 --set 0 2>/dev/null || true
    settings put system sound_effects_enabled 0
    settings put system vibrate_when_ringing 0
    settings put system haptic_feedback_enabled 0
    settings put system lockscreen_minimizing_notification 1
    pkill -f termux-wifi-enable 2>/dev/null || true
    for pkg in com.duckduckgo.mobile.android com.android.vending \\
               de.axelspringer.yana.zeropage com.sec.android.app.shealth \\
               com.microsoft.appmanager com.samsung.android.oneconnect \\
               com.samsung.android.rubin.app com.google.android.apps.tachyon \\
               com.spotify.music com.google.android.apps.youtube.music \\
               com.google.android.apps.photos com.google.android.apps.docs \\
               com.telstra.mobile.android.mytelstra com.lycamobile.au \\
               com.firsty.app com.redbull.android.esim \\
               travel.eskimo.esim com.roamless.roamless; do
        am force-stop "$pkg" 2>/dev/null || true
    done
    dumpsys deviceidle whitelist +com.tailscale.ipn +com.termux +com.termux.boot >/dev/null 2>&1 || true
    cmd appops set com.tailscale.ipn RUN_IN_BACKGROUND allow >/dev/null 2>&1 || true
    cmd appops set com.tailscale.ipn RUN_ANY_IN_BACKGROUND allow >/dev/null 2>&1 || true
    cmd appops set com.termux RUN_IN_BACKGROUND allow >/dev/null 2>&1 || true
    cmd appops set com.termux RUN_ANY_IN_BACKGROUND allow >/dev/null 2>&1 || true
    if ! dumpsys activity services 2>/dev/null | grep -q 'com.tailscale.ipn/.IPNService'; then
        am startservice -n com.tailscale.ipn/.IPNService >/dev/null 2>&1 || true
    fi
    am startservice -n com.termux/.app.TermuxService >/dev/null 2>&1 || true
"""

def restore_golden_baseline():
    print(f"[{_ts()}] 🔄 Restoring Golden Gateway Baseline…", flush=True)
    run_adb(BASELINE_CMDS, timeout=20)
    print(f"[{_ts()}] ✅ Golden Gateway Baseline Enforced.", flush=True)

def main():
    print("🚀 Samsung S20+ Auto-Revert Watchdog Daemon Initialized.", flush=True)
    print(f"Primary: {TARGET_TAILSCALE} | Fallback: SSH {ROUTER_SSH_HOST} USB ADB ({ROUTER_ADB_SERIAL})", flush=True)
    print(f"Poll: {CHECK_INTERVAL}s | Screen Override Timeout: {OVERRIDE_TIMEOUT}s (15 min)", flush=True)
    ensure_connected()
    restore_golden_baseline()
    awake_seconds = 0
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            if not ensure_connected():
                continue
            wake_out   = run_adb("dumpsys power | grep -m1 mWakefulness=")
            bright_out = run_adb("settings get system screen_brightness")
            stay_out   = run_adb("settings get global stay_on_while_plugged_in")
            bat_out    = run_adb("settings get global protect_battery")
            if not wake_out:
                continue
            is_awake    = "Awake" in wake_out
            brightness  = int(bright_out) if bright_out  and bright_out.isdigit()  else 1
            stay_on     = int(stay_out)   if stay_out    and stay_out.isdigit()    else 0
            protect_bat = int(bat_out)    if bat_out     and bat_out.isdigit()     else 1
            if is_awake:
                awake_seconds += CHECK_INTERVAL
                print(f"[{_ts()}] 📱 S20 Awake ({awake_seconds}s/{OVERRIDE_TIMEOUT}s B:{brightness})", flush=True)
                if awake_seconds >= OVERRIDE_TIMEOUT:
                    print(f"[{_ts()}] ⏳ 15-min override. Sleeping + restoring…", flush=True)
                    run_adb("input keyevent 26")
                    restore_golden_baseline()
                    awake_seconds = 0
            else:
                awake_seconds = 0
                if brightness != 1 or stay_on != 0 or protect_bat != 1:
                    print(f"[{_ts()}] 💤 Dirty settings while asleep (B:{brightness} StayOn:{stay_on} Bat:{protect_bat}). Reverting…", flush=True)
                    restore_golden_baseline()
        except KeyboardInterrupt:
            print("\n🛑 Watchdog terminated by user.", flush=True)
            sys.exit(0)
        except Exception as e:
            print(f"[{_ts()}] ⚠️  Loop error: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
