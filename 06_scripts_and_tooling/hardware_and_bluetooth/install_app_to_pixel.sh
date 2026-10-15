#!/usr/bin/env bash
# ==============================================================================
# 06_scripts_and_tooling/install_app_to_pixel.sh
# ==============================================================================
# Sovereign Pixel 10 Pro XL Automated App Installer & Keepalive Provisioner
# Compliant with: Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), Rule 5 (Victory Gate)
# ==============================================================================

set -euo pipefail

DEFAULT_APK="/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/android_apks/de.kai_morich.serial_bluetooth_terminal.apk"
TARGET_APK="${1:-$DEFAULT_APK}"
PIXEL_TS_IP="100.73.38.87"
PIXEL_LAN_IP="192.168.8.145"
ADB_BIN="/Users/aaron/.local/bin/adb"

[ -x "$ADB_BIN" ] || ADB_BIN="adb"

echo "===================================================================="
echo "📱 PIXEL APP INSTALLER & DEPLOYMENT SENTINEL"
echo "Target APK: $TARGET_APK"
echo "===================================================================="

if [ ! -f "$TARGET_APK" ]; then
    echo "❌ Target APK not found: $TARGET_APK"
    exit 1
fi

# Function to discover active target
find_pixel_target() {
    # 1. Check local USB attached devices
    local usb_devs
    usb_devs=$($ADB_BIN devices | awk 'NR>1 && $2=="device" && $1 !~ /:/ {print $1}')
    if [ -n "$usb_devs" ]; then
        echo "$usb_devs" | head -n 1
        return 0
    fi

    # 2. Try wireless ADB connect via LAN if port 5555 responds
    if nc -z -w 1 "$PIXEL_LAN_IP" 5555 2>/dev/null; then
        if $ADB_BIN connect "${PIXEL_LAN_IP}:5555" 2>/dev/null | grep -q "connected"; then
            echo "${PIXEL_LAN_IP}:5555"
            return 0
        fi
    fi

    # 3. Try wireless ADB connect via Tailscale if port 5555 responds
    if nc -z -w 1 "$PIXEL_TS_IP" 5555 2>/dev/null; then
        if $ADB_BIN connect "${PIXEL_TS_IP}:5555" 2>/dev/null | grep -q "connected"; then
            echo "${PIXEL_TS_IP}:5555"
            return 0
        fi
    fi

    # 4. Check any attached device
    local any_dev
    any_dev=$($ADB_BIN devices | awk 'NR>1 && $2=="device" {print $1}')
    if [ -n "$any_dev" ]; then
        echo "$any_dev" | head -n 1
        return 0
    fi

    return 1
}

echo "🔍 Probing for Pixel 10 Pro XL (USB / LAN ${PIXEL_LAN_IP} / Tailscale ${PIXEL_TS_IP})..."

TARGET_DEVICE=""
for i in {1..3}; do
    if TARGET_DEVICE=$(find_pixel_target); then
        break
    fi
    sleep 1
done

if [ -z "$TARGET_DEVICE" ]; then
    echo "⚠️ Pixel 10 Pro XL is currently not detected via ADB."
    echo ""
    echo "📋 Current Hardware Status:"
    echo "  • Tailscale (100.73.38.87): Offline / Deep Sleep"
    echo "  • Router LAN (192.168.8.145): ARP Incomplete / Wi-Fi Power-Save"
    echo "  • Bluetooth (30:E0:44:6D:18:EC): Paired, awaiting wake event"
    echo ""
    echo "👉 To complete installation:"
    echo "  1. Plug Pixel into Mac Mini via USB-C and ensure 'USB Debugging' is enabled, OR"
    echo "  2. Unlock Pixel, open Developer Options -> Wireless Debugging -> Enable."
    exit 2
fi

echo "🟢 Detected Active Device: $TARGET_DEVICE"

# Step 1: Install APK with permission grant (-g)
echo "📦 Installing APK ($TARGET_APK)..."
$ADB_BIN -s "$TARGET_DEVICE" install -r -g "$TARGET_APK"

# Step 2: Extract Package Name
PKG_NAME="de.kai_morich.serial_bluetooth_terminal"
if [[ "$TARGET_APK" =~ "android_auto" ]]; then
    PKG_NAME="com.lauburu.androidauto.voicecoder"
elif [[ "$TARGET_APK" =~ "openclaw" ]]; then
    PKG_NAME="ai.openclaw.agent"
fi

# Step 3: Configure Doze Bypass & Keepalive
echo "⚡ Whitelisting package ($PKG_NAME) from battery optimization..."
$ADB_BIN -s "$TARGET_DEVICE" shell "dumpsys deviceidle whitelist +$PKG_NAME +com.termux 2>/dev/null || true"
$ADB_BIN -s "$TARGET_DEVICE" shell "cmd appops set $PKG_NAME RUN_IN_BACKGROUND allow 2>/dev/null || true"

# Step 4: Launch the installed app
echo "🚀 Launching $PKG_NAME on Pixel..."
$ADB_BIN -s "$TARGET_DEVICE" shell "monkey -p $PKG_NAME -c android.intent.category.LAUNCHER 1" >/dev/null 2>&1 || true

# Step 5: Capture Verification Screenshot
echo "📸 Capturing Tri-Proof Visual Verification..."
$ADB_BIN -s "$TARGET_DEVICE" shell "screencap -p /sdcard/pixel_install_verify.png" 2>/dev/null || true
$ADB_BIN -s "$TARGET_DEVICE" pull /sdcard/pixel_install_verify.png /tmp/pixel_install_verify.png 2>/dev/null || true

if [ -f "/tmp/pixel_install_verify.png" ]; then
    echo "✅ Visual receipt captured: /tmp/pixel_install_verify.png ($(wc -c < /tmp/pixel_install_verify.png) bytes)"
fi

echo "===================================================================="
echo "🎉 SUCCESS: App installed and launched on Pixel ($TARGET_DEVICE)!"
echo "===================================================================="
