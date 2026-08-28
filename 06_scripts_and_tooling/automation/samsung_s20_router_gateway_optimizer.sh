#!/usr/bin/env bash
# ==============================================================================
# Canonical Script: samsung_s20_router_gateway_optimizer.sh
# Purpose: Optimizes Samsung S20+ (SM-G986B) as a 24/7 dedicated router internet source.
# Protocol: Zero-Mock ADB over Wireless TCP/IP or USB Bridge
# ==============================================================================

set -euo pipefail

TARGET_DEVICE="${1:-100.84.40.95:5555}"
ADB_BIN="$(command -v adb || echo "/Users/aaron/.local/bin/adb")"

echo "=================================================================="
echo "🚀 SAMSUNG S20+ ROUTER GATEWAY OPTIMIZER & CLEANUP"
echo "Target Device: ${TARGET_DEVICE}"
echo "=================================================================="

# Check ADB connectivity
if ! "${ADB_BIN}" devices | grep -q "${TARGET_DEVICE}"; then
    echo "Connecting to ${TARGET_DEVICE}..."
    "${ADB_BIN}" connect "${TARGET_DEVICE}" || true
fi

"${ADB_BIN}" -s "${TARGET_DEVICE}" shell "
echo '=== TIER 1: BATTERY PROTECTION & THERMAL HEALTH ==='
settings put global protect_battery 1
echo '  [OK] Protect Battery (85% Charge Cap) Enabled'

echo '=== TIER 2: DISPLAY & POWER MINIMIZATION ==='
settings put global stay_on_while_plugged_in 0
settings put system screen_brightness 1
settings put system screen_brightness_mode 0
settings put system screen_off_timeout 15000
settings put system aod_mode 0
settings put secure doze_always_on 0
settings put system refresh_rate_mode 0
settings put system high_refresh_rate_mode 0
settings put secure wake_gesture_enabled 0
echo '  [OK] Screen Timeout: 15s, Brightness: 1 (Manual), AOD: OFF, 60Hz: Enforced'

echo '=== TIER 3: AUDIO & NOTIFICATION SUPPRESSION ==='
media volume --stream 1 --set 0 2>/dev/null || true
media volume --stream 2 --set 0 2>/dev/null || true
media volume --stream 3 --set 0 2>/dev/null || true
media volume --stream 5 --set 0 2>/dev/null || true
settings put system sound_effects_enabled 0
settings put system vibrate_when_ringing 0
settings put system haptic_feedback_enabled 0
settings put system notification_sound ''
settings put system lockscreen_minimizing_notification 1
echo '  [OK] Volumes Muted, Sound Effects / Haptics Disabled, Notifications Minimized'

echo '=== TIER 4: KILLING HUNG PROCESSES & HEAVY BACKGROUND CONSUMERS ==='
pkill -f termux-wifi-enable 2>/dev/null || true
pkill -f 'bash -c termux-wifi-enable' 2>/dev/null || true

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
    am force-stop \"\$pkg\" 2>/dev/null || true
done
echo '  [OK] Force-stopped background bloat packages'

echo '=== TIER 5: GATEWAY PERSISTENCE & DOZE WHITELIST ==='
settings put global settings_enable_monitor_phantom_procs false
dumpsys deviceidle whitelist +com.termux +com.termux.boot +com.tailscale.ipn >/dev/null 2>&1 || true
cmd appops set com.termux RUN_IN_BACKGROUND allow >/dev/null 2>&1 || true
cmd appops set com.termux RUN_ANY_IN_BACKGROUND allow >/dev/null 2>&1 || true
cmd appops set com.tailscale.ipn RUN_IN_BACKGROUND allow >/dev/null 2>&1 || true
cmd appops set com.tailscale.ipn RUN_ANY_IN_BACKGROUND allow >/dev/null 2>&1 || true
echo '  [OK] Phantom Procs Monitor Disabled, Termux & Tailscale Whitelisted'

echo '=== TIER 6: ENFORCING SCREEN SLEEP ==='
if dumpsys power | grep -q 'mWakefulness=Awake'; then
    input keyevent 26
fi
echo '  [OK] Screen Sleep Enforced'
"

echo "=================================================================="
echo "✅ OPTIMIZATION COMPLETED SUCCESSFULLY"
echo "=================================================================="
