#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh: Android Edge Node Deep Immunization Protocol
# Compatible with: Android 13 (One UI 5.1) & Android 15/16 (Pixel Tensor G5)
# Governed by Rule 0 (Hardware Matrix) & Rule 1 (Zero-Mock Truth)
# ==============================================================================
set -euo pipefail

TARGET_SERIAL="${1:-}"

if [ -z "${TARGET_SERIAL}" ]; then
    echo "Usage: $0 <adb_serial_or_ip_port>"
    echo "Example: $0 100.78.206.96:5555"
    echo "         $0 192.168.8.114:5555"
    exit 1
fi

echo "🛡️ Hardening Android Edge Node: [${TARGET_SERIAL}]..."

# 1. Annihilate the Phantom Process Killer (Android 12+)
adb -s "${TARGET_SERIAL}" shell "/system/bin/device_config put activity_manager max_phantom_processes 2147483647" 2>/dev/null || true
adb -s "${TARGET_SERIAL}" shell "settings put global settings_enable_monitor_phantom_procs false" 2>/dev/null || true

# 2. Disable Wi-Fi Sleep, Suspensions, and Radio Power Saving
adb -s "${TARGET_SERIAL}" shell "settings put global wifi_sleep_policy 2" 2>/dev/null || true              # 2 = NEVER sleep
adb -s "${TARGET_SERIAL}" shell "settings put global wifi_suspend_optimizations 0" 2>/dev/null || true    # Disable Wi-Fi sleep suspension
adb -s "${TARGET_SERIAL}" shell "settings put global wifi_power_save 0" 2>/dev/null || true
adb -s "${TARGET_SERIAL}" shell "settings put global wifi_scan_always_enabled 1" 2>/dev/null || true

# 3. Anchor Stay Awake on Power (Prevents Deep Doze while docked or connected to USB)
# 1=AC, 2=USB, 4=Wireless -> 7 = Always Stay Awake while on any power source
adb -s "${TARGET_SERIAL}" shell "settings put global stay_on_while_plugged_in 7" 2>/dev/null || true

# 4. Whitelist Core Daemons from Doze Mode
for pkg in com.termux com.termux.boot com.tailscale.ipn moe.shizuku.privileged.api com.wireguard.android ai.openclaw.app com.lauburu.omni_agent_flutter; do
    adb -s "${TARGET_SERIAL}" shell "dumpsys deviceidle whitelist +${pkg}" 2>/dev/null || true
    adb -s "${TARGET_SERIAL}" shell "cmd appops set ${pkg} RUN_IN_BACKGROUND allow" 2>/dev/null || true
    adb -s "${TARGET_SERIAL}" shell "cmd appops set ${pkg} WAKE_LOCK allow" 2>/dev/null || true
done

# 5. Device-Specific Optimizations
MODEL=$(adb -s "${TARGET_SERIAL}" shell "getprop ro.product.model" 2>/dev/null | tr -d '\r')
echo "Detected Hardware: ${MODEL}"

if [[ "${MODEL}" == *"SM-G986"* ]] || [[ "${MODEL}" == *"Samsung"* ]]; then
    echo "Applying Samsung One UI Specific Protections..."
    adb -s "${TARGET_SERIAL}" shell "settings put global adaptive_power_saving_setting 0" 2>/dev/null || true
    adb -s "${TARGET_SERIAL}" shell "settings put system power_saving_mode 0" 2>/dev/null || true
elif [[ "${MODEL}" == *"Pixel"* ]]; then
    echo "Applying Google Pixel / Tensor G5 Protections..."
    adb -s "${TARGET_SERIAL}" shell "settings put global adaptive_battery_management_enabled 0" 2>/dev/null || true
fi

echo "--- Current Immunization Verification ---"
echo "stay_on_while_plugged_in: $(adb -s "${TARGET_SERIAL}" shell "settings get global stay_on_while_plugged_in" 2>/dev/null | tr -d '\r')"
echo "wifi_sleep_policy: $(adb -s "${TARGET_SERIAL}" shell "settings get global wifi_sleep_policy" 2>/dev/null | tr -d '\r')"
echo "wifi_suspend_optimizations: $(adb -s "${TARGET_SERIAL}" shell "settings get global wifi_suspend_optimizations" 2>/dev/null | tr -d '\r')"
echo "max_phantom_processes: $(adb -s "${TARGET_SERIAL}" shell "device_config get activity_manager max_phantom_processes" 2>/dev/null | tr -d '\r')"
echo "✅ Node [${TARGET_SERIAL}] successfully immunized against Doze and process reaping."
