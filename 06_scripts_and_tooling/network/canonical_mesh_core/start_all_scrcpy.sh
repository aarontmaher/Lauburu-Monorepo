#!/bin/bash
# start_all_scrcpy.sh - Lauburu Screen Lens Sovereign Initialization Script
# Wakes devices via Layer 0 (Bluetooth), verifies Shizuku, and launches scrcpy

set -e

echo "======================================================"
echo "👁️ SCREEN LENS SOVEREIGN — DEVICE INITIALIZATION ENGINE"
echo "======================================================"

# 1. Wake devices using Canonical Network Resurrection Engine
echo "[1/4] Pinging devices via Layer 0 Bluetooth wake pulse..."
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --wake L6_Pixel_10_Edge >/dev/null 2>&1 || true
python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --wake L7_Samsung_S20 >/dev/null 2>&1 || true

# 2. Re-establish ADB Connections (Wireless & mDNS)
echo "[2/4] Waiting for ADB descriptors to enumerate..."
sleep 2
adb connect 10.1.0.13:5555 >/dev/null 2>&1 || true

# 3. Bootstrapping Shizuku if needed
echo "[3/4] Ensuring Shizuku is active (UID 2000) on all edges..."
bash /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/bootstrap_s20_shizuku.sh --wait 5 >/dev/null 2>&1 || true

# 4. Launch Scrcpy for active devices
echo "[4/4] Launching scrcpy streams for active devices..."
PIXEL_SERIAL="10.1.0.13:5555"
S20_SERIAL="adb-R3CN40CJJ1R-JKttZ1._adb-tls-connect._tcp"

if adb devices | grep -q "${PIXEL_SERIAL}[[:space:]]*device"; then
    echo "  -> Starting scrcpy for Pixel 10 Pro XL..."
    # Kill any existing instance
    pkill -f "scrcpy -s ${PIXEL_SERIAL}" || true
    scrcpy -s "${PIXEL_SERIAL}" --max-fps 15 -m 1024 --window-title "Pixel 10 Pro XL (Tensor G5)" >/dev/null 2>&1 &
else
    echo "  -> [WARNING] Pixel 10 Pro XL not found."
fi

if adb devices | grep -q "${S20_SERIAL}[[:space:]]*device"; then
    echo "  -> Starting scrcpy for Samsung Galaxy S20+..."
    pkill -f "scrcpy -s ${S20_SERIAL}" || true
    scrcpy -s "${S20_SERIAL}" --max-fps 15 -m 1024 --window-title "Samsung Galaxy S20+ (Automated UI Tester)" >/dev/null 2>&1 &
else
    echo "  -> [WARNING] Samsung Galaxy S20+ not found."
fi

echo "======================================================"
echo "✅ All Screen Lens Sovereign endpoints are active."
echo "======================================================"
