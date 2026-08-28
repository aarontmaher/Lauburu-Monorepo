#!/data/data/com.termux/files/usr/bin/bash
echo "=== Installing Termux Bluetooth Dependencies ==="
pkg update -y
pkg install -y python clang make libffi openssl termux-api
pip install --upgrade pip
pip install bleak

echo "=== Requesting Android Permissions ==="
# Use Termux API to request location/bluetooth permissions needed for BLE scanning
termux-setup-storage
# For Android 12+, Bluetooth permissions must be granted in Android settings, 
# but termux-location can sometimes trigger the prompt.
termux-location > /dev/null 2>&1

echo "Done! You can now run: python3 bt_telemetry_terminal.py"
