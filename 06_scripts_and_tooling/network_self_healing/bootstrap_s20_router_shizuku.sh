#!/usr/bin/env bash
# ==============================================================================
# LAUBURU MESH - SAMSUNG S20 SHIZUKU & ROUTER USB BOOTSTRAPPER
# Subsystem: 06_scripts_and_tooling/network_self_healing
# Target: GL.iNet Router (100.122.185.123) -> Samsung S20 (SM-G986B)
# ==============================================================================
set -euo pipefail

ROUTER_IP="${ROUTER_IP:-100.122.185.123}"
echo "========================================================"
echo "Connecting to GL.iNet Router at $ROUTER_IP..."
echo "========================================================"

ssh -o StrictHostKeyChecking=no "root@${ROUTER_IP}" "
echo '=== 1. Checking USB ADB Devices on Router ==='
adb start-server
adb devices -l

echo '=== 2. Starting Shizuku Service ==='
adb shell 'sh /sdcard/Android/data/moe.shizuku.privileged.api/start.sh || sh /storage/emulated/0/Android/data/moe.shizuku.privileged.api/start.sh'

echo '=== 3. Whitelisting Mesh Daemons (Doze Mode Bypass) ==='
adb shell dumpsys deviceidle whitelist +com.termux
adb shell dumpsys deviceidle whitelist +com.termux.boot
adb shell dumpsys deviceidle whitelist +com.tailscale.ipn
adb shell dumpsys deviceidle whitelist +moe.shizuku.privileged.api

echo '=== 4. Enabling TCP/IP ADB (Port 5555) ==='
adb tcpip 5555

echo '=== 5. Reading Live Battery Telemetry ==='
adb shell dumpsys battery | grep -iE 'level|temperature|USB powered|status'

echo '========================================================'
echo 'SAMSUNG S20 SHIZUKU & MESH HEALER BOOTSTRAP COMPLETE!'
echo '========================================================'
"
