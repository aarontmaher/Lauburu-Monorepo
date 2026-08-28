#!/usr/bin/env python3
"""
Samsung S20+ Dedicated Router Gateway Auto-Revert Watchdog Daemon
Monitors S20+ over ADB. If user temporarily wakes device or changes brightness,
automatically defaults back to optimized gateway state after 15 min or on screen-off.
"""

import subprocess
import time
import sys
import os
import datetime

TARGET_DEVICE = os.environ.get("S20_ADB_TARGET", "100.84.40.95:5555")
ADB_BIN = "/Users/aaron/.local/bin/adb" if os.path.isfile("/Users/aaron/.local/bin/adb") else "adb"
CHECK_INTERVAL = 30 # seconds
OVERRIDE_TIMEOUT = 900 # 15 minutes in seconds

def run_adb(cmd, timeout=10):
    try:
        full_cmd = [ADB_BIN, "-s", TARGET_DEVICE, "shell", cmd]
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip()
    except Exception as e:
        return None

def ensure_connected():
    try:
        res = subprocess.run([ADB_BIN, "devices"], capture_output=True, text=True, timeout=5)
        if TARGET_DEVICE not in res.stdout:
            subprocess.run([ADB_BIN, "connect", TARGET_DEVICE], capture_output=True, text=True, timeout=5)
    except Exception:
        pass

def restore_golden_baseline():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] 🔄 Restoring Samsung S20+ Golden Gateway Baseline...", flush=True)
    
    cmds = """
    # 1. Protect Battery (85% Charge Limit)
    settings put global protect_battery 1

    # 2. Display & Power Minimization
    settings put global stay_on_while_plugged_in 0
    settings put system screen_brightness 1
    settings put system screen_brightness_mode 0
    settings put system screen_off_timeout 15000
    settings put system aod_mode 0
    settings put secure doze_always_on 0
    settings put system refresh_rate_mode 0
    settings put system high_refresh_rate_mode 0
    settings put secure wake_gesture_enabled 0

    # 3. Developer Settings Optimization
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

    # 4. Audio & Notification Muting
    media volume --stream 1 --set 0 2>/dev/null || true
    media volume --stream 2 --set 0 2>/dev/null || true
    media volume --stream 3 --set 0 2>/dev/null || true
    media volume --stream 5 --set 0 2>/dev/null || true
    settings put system sound_effects_enabled 0
    settings put system vibrate_when_ringing 0
    settings put system haptic_feedback_enabled 0
    settings put system notification_sound ''
    settings put system lockscreen_minimizing_notification 1

    # 5. Background Bloat & Subshells
    pkill -f termux-wifi-enable 2>/dev/null || true
    for pkg in com.duckduckgo.mobile.android \
               com.android.vending \
               de.axelspringer.yana.zeropage \
               com.sec.android.app.shealth \
               com.microsoft.appmanager \
               com.samsung.android.oneconnect \
               com.samsung.android.rubin.app \
               com.google.android.apps.tachyon \
               com.spotify.music \
               com.google.android.apps.youtube.music \
               com.google.android.apps.photos \
               com.google.android.apps.docs \
               com.telstra.mobile.android.mytelstra \
               com.lycamobile.au \
               com.firsty.app \
               com.redbull.android.esim \
               travel.eskimo.esim \
               com.roamless.roamless; do
        am force-stop "$pkg" 2>/dev/null || true
    done
    """
    run_adb(cmds, timeout=15)
    print(f"[{now_str}] ✅ Golden Gateway Baseline Enforced.", flush=True)

def main():
    print(f"🚀 Samsung S20+ Auto-Revert Watchdog Daemon Initialized.", flush=True)
    print(f"Target: {TARGET_DEVICE} | Poll Interval: {CHECK_INTERVAL}s | Override Timeout: {OVERRIDE_TIMEOUT}s (15 min)", flush=True)
    
    ensure_connected()
    restore_golden_baseline()
    
    awake_seconds = 0
    
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            ensure_connected()
            
            wake_out = run_adb("dumpsys power | grep -m1 mWakefulness=")
            bright_out = run_adb("settings get system screen_brightness")
            stay_out = run_adb("settings get global stay_on_while_plugged_in")
            bat_out = run_adb("settings get global protect_battery")
            
            if not wake_out:
                continue
                
            is_awake = "Awake" in wake_out
            brightness = int(bright_out) if bright_out and bright_out.isdigit() else 1
            stay_on = int(stay_out) if stay_out and stay_out.isdigit() else 0
            protect_bat = int(bat_out) if bat_out and bat_out.isdigit() else 1
            
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if is_awake:
                awake_seconds += CHECK_INTERVAL
                print(f"[{now_str}] 📱 S20 Screen Active (Awake for {awake_seconds}s / {OVERRIDE_TIMEOUT}s, Brightness: {brightness})", flush=True)
                
                if awake_seconds >= OVERRIDE_TIMEOUT:
                    print(f"[{now_str}] ⏳ 15-minute override timeout reached. Turning off display and restoring baseline...", flush=True)
                    run_adb("input keyevent 26") # Sleep screen
                    restore_golden_baseline()
                    awake_seconds = 0
            else:
                awake_seconds = 0
                # If screen is asleep but settings are dirty, restore immediately
                if brightness != 1 or stay_on != 0 or protect_bat != 1:
                    print(f"[{now_str}] 💤 S20 Screen Asleep with dirty settings (Brightness: {brightness}, StayOn: {stay_on}, ProtectBat: {protect_bat}). Reverting...", flush=True)
                    restore_golden_baseline()
                    
        except KeyboardInterrupt:
            print("\nWatchdog terminated by user.", flush=True)
            sys.exit(0)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
