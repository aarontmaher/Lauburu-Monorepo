#!/usr/bin/env bash
# ==============================================================================
# LAUBURU MESH - PIXEL 10 PRO XL SHIZUKU & WIRELESS MESH BOOTSTRAPPER
# Subsystem: 06_scripts_and_tooling/network_self_healing
# Target: Pixel 10 Pro XL (100.73.38.87 / 192.168.8.145)
# ==============================================================================
set -euo pipefail

PIXEL_IP="${PIXEL_IP:-100.73.38.87}"
PIXEL_PORT="${PIXEL_PORT:-5555}"

echo "========================================================"
echo "Connecting to Pixel 10 Pro XL at ${PIXEL_IP}:${PIXEL_PORT}..."
echo "========================================================"

adb connect "${PIXEL_IP}:${PIXEL_PORT}"

echo "=== 1. Starting Shizuku Service ==="
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell '
APK_PATH=$(pm path moe.shizuku.privileged.api | cut -d: -f2)
LIB_DIR=$(dirname $APK_PATH)/lib/arm64
if [ -f "$LIB_DIR/libshizuku.so" ]; then
    $LIB_DIR/libshizuku.so
elif [ -f /sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh ]; then
    sh /sdcard/Android/data/moe.shizuku.privileged.api/files/start.sh
else
    sh /storage/emulated/0/Android/data/moe.shizuku.privileged.api/start.sh
fi
'

echo "=== 2. Whitelisting Mesh Daemons (Doze Mode Bypass) ==="
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell dumpsys deviceidle whitelist +com.termux
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell dumpsys deviceidle whitelist +com.termux.boot
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell dumpsys deviceidle whitelist +com.tailscale.ipn
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell dumpsys deviceidle whitelist +moe.shizuku.privileged.api

echo "=== 3. Disabling Phantom Process Killer ==="
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell settings put global settings_enable_monitor_phantom_procs false

echo "=== 4. Setting AppOps ==="
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell cmd appops set moe.shizuku.privileged.api RUN_IN_BACKGROUND allow
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell cmd appops set com.termux RUN_IN_BACKGROUND allow

echo "=== 5. Reading Live Battery Telemetry ==="
adb -s "${PIXEL_IP}:${PIXEL_PORT}" shell dumpsys battery | grep -iE 'level|temperature|USB powered|status'

echo "========================================================"
echo "PIXEL 10 PRO XL SHIZUKU BOOTSTRAP COMPLETE!"
echo "========================================================"
