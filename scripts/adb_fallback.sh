#!/bin/bash
# adb_fallback.sh
# An overarching ADB fallback wrapper that ensures ADB commands never fail due to a single transport dropping.
# It probes Tailscale IP, KDE Connect, local Wi-Fi, and direct USB for a given device model (e.g. Pixel).

TARGET_MODEL=${1:-"Pixel"}
shift
COMMAND="$@"

if [ -z "$COMMAND" ]; then
    echo "Usage: adb_fallback.sh <Target_Model> <command>"
    echo "Example: adb_fallback.sh Pixel shell input tap 900 1100"
    exit 1
fi

echo "[adb_fallback] Searching for $TARGET_MODEL across all transports..."

# Get all connected devices
DEVICES=$(adb devices | grep -v "List of devices" | awk '{print $1}' | grep -v "^$")

for dev in $DEVICES; do
  MODEL=$(adb -s $dev shell getprop ro.product.model 2>/dev/null | tr -d '\r')
  
  if [[ "$MODEL" == *"$TARGET_MODEL"* ]]; then
    echo "[adb_fallback] Found $TARGET_MODEL at transport: $dev"
    echo "[adb_fallback] Executing command: $COMMAND"
    
    # Run the command and capture exit status
    adb -s $dev $COMMAND
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[adb_fallback] Command succeeded on transport $dev."
        exit 0
    else
        echo "[adb_fallback] Command failed with exit code $EXIT_CODE on transport $dev. Trying next transport..."
    fi
  fi
done

echo "[adb_fallback] ERROR: Could not successfully execute command. No matching devices found online or all transports failed."
exit 1