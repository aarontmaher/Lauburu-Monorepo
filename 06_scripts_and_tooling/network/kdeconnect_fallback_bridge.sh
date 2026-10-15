#!/usr/bin/env bash
# ==============================================================================
# KDE Connect Fallback Bridge & SSH Resurrection (Rule 14)
# ==============================================================================
# When ADB and Shizuku are unavailable, KDE Connect serves as the primary 
# out-of-band fallback bridge to resurrect edge nodes (L6, L7).
# ==============================================================================

set -euo pipefail

# Resolve dynamic KDE Connect D-Bus session socket on macOS
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    DBUS_SOCK=$(ls -t /tmp/dbus-* 2>/dev/null | head -n 1)
    if [ -n "$DBUS_SOCK" ]; then
        export DBUS_SESSION_BUS_ADDRESS="unix:path=$DBUS_SOCK"
    fi
fi
export PATH="/Users/aaron/.local/bin:/Applications/KDE Connect.app/Contents/MacOS:$PATH"

echo "========================================================================"
echo "🔌 INITIATING KDE CONNECT FALLBACK BRIDGE (RULE 14)"
echo "========================================================================"

# 1. List all paired KDE Connect devices
echo "[*] Querying paired KDE Connect devices across the mesh..."
kdeconnect-cli -l

# Extract device IDs (assuming standard naming, or we broadcast to all reachable)
# We will send a ping to awaken the device radios and prompt Termux/ADB to restart.
DEVICE_IDS=$(kdeconnect-cli -l --id-only)

if [ -z "$DEVICE_IDS" ]; then
    echo "[!] No KDE Connect devices found. Ensure the Mac/Linux host is paired."
    exit 1
fi

for DEVICE in $DEVICE_IDS; do
    echo "[>] Sending Silent Wake Ping to Device: $DEVICE"
    kdeconnect-cli -d "$DEVICE" --ping || echo "[!] Notice: Ping to $DEVICE unacknowledged (device may be in standby)"

    # Beam a clipboard payload to execute in Moonshine / Termux terminal
    echo "[>] Beaming Shizuku/ADB recovery shell payload via clipboard..."
    kdeconnect-cli -d "$DEVICE" --share-text "su -c 'setprop service.adb.tcp.port 5555 && stop adbd && start adbd' && termux-wake-lock" || echo "[!] Notice: Payload transfer to $DEVICE skipped"
done

echo "[✔] KDE Connect payloads transmitted. Radios should be waking up."
echo "    -> Please paste the beamed clipboard payload into the edge node's terminal."
echo "========================================================================"
