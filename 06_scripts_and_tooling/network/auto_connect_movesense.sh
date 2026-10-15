#!/system/bin/sh
# Movesense Auto-Connect UI Automation via Shizuku
# This script waits for the user to finish using the device, then connects the BLE device.

echo "Waiting for device to be idle (screen off)..."
while true; do
    state=$(dumpsys power | grep 'mWakefulness=Asleep')
    if [ ! -z "$state" ]; then
        echo "Device is asleep. Starting UI automation."
        break
    fi
    sleep 5
done

# Wake device
input keyevent 224
sleep 1
# Swipe to unlock
input swipe 500 2000 500 500
sleep 1

# Launch the Serial Bluetooth Terminal
am start -n de.kai_morich.serial_bluetooth_terminal/.MainActivity
sleep 3

# Tap the 'Connect' icon in the Action Bar.
# The 'Connect' icon is typically at the top right, but uiautomator is safer.
uiautomator dump /data/local/tmp/ui.xml
# Find the connect button (usually a terminal plug icon with description "Connect")
# Or we can just tap the known coordinates (approx top right)
input tap 900 150

sleep 5

# Ensure TCP server is started if needed (or app auto-starts it)
# Go back to home
input keyevent 3

# Turn screen off
input keyevent 26
echo "Movesense automation complete."
