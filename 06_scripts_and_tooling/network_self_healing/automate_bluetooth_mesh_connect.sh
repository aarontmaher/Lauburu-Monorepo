#!/usr/bin/env bash
echo "============================================================"
echo "⚡ AUTOMATING BLUETOOTH MESH CONNECTIONS (LAYER 0 WAKE)"
echo "============================================================"

# Get all paired devices
PAIRED=$(blueutil --paired | grep -v "Magic Keyboard" | grep -v "Polar")

echo "$PAIRED" | while read -r line; do
    MAC=$(echo "$line" | grep -oE "([0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}")
    NAME=$(echo "$line" | grep -oE 'name: "[^"]+"' | cut -d '"' -f 2)
    
    if [ -n "$MAC" ]; then
        echo "Attempting to bridge/wake: $NAME ($MAC) ..."
        blueutil --connect "$MAC" &
    fi
done

wait
echo "✅ All Bluetooth connection bridging packets dispatched."
