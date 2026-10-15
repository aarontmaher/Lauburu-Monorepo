#!/usr/bin/env bash
set -e

echo "=== [Chromium Web Bluetooth Ingestion Node] Starting ==="

# Check D-Bus socket existence
if [ ! -e /run/dbus/system_bus_socket ] && [ ! -e /var/run/dbus/system_bus_socket ]; then
    echo "WARNING: D-Bus socket not found in container! Web Bluetooth requires host D-Bus socket mount:"
    echo "  -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:ro"
fi

# Start telemetry web server
python3 /app/server.py &
SERVER_PID=$!

echo "Waiting for Telemetry Bridge Server to initialize..."
sleep 2

# Launch Headless Chromium with Web Bluetooth and Remote DevTools enabled
echo "Launching Headless Chromium with Web Bluetooth..."
chromium \
    --headless=new \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --enable-web-bluetooth \
    --enable-features=WebBluetooth,WebBluetoothScanning \
    --enable-experimental-web-platform-features \
    --remote-debugging-port=9222 \
    --remote-debugging-address=0.0.0.0 \
    --user-data-dir=/tmp/chromium-profile \
    "http://127.0.0.1:9223" &
CHROMIUM_PID=$!

echo "Chromium Web Bluetooth running (PID $CHROMIUM_PID)."
echo "DevTools CDP active on :9222 | Web UI active on :9223"

# Keep container alive and trap termination
trap "kill -TERM $SERVER_PID $CHROMIUM_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait
