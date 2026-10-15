#!/usr/bin/env bash
# Runs Chromium Web Bluetooth Ingestion container via Podman
set -e

CONTAINER_NAME="movesense-chromium-web-bluetooth"
IMAGE_NAME="localhost/movesense-chromium-web-bluetooth:latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Building $IMAGE_NAME with Podman ==="
podman build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"

echo "=== Stopping existing container if running ==="
podman rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Determine D-Bus socket path on host
DBUS_SOCK="/run/dbus/system_bus_socket"
if [ ! -e "$DBUS_SOCK" ]; then
    DBUS_SOCK="/var/run/dbus/system_bus_socket"
fi

echo "=== Starting $CONTAINER_NAME ==="
podman run -d \
    --name "$CONTAINER_NAME" \
    --net=host \
    --privileged \
    -v "$DBUS_SOCK:$DBUS_SOCK:ro" \
    -v /sys/class/bluetooth:/sys/class/bluetooth:ro \
    -v /dev:/dev \
    -v /tmp/movesense_data:/data \
    "$IMAGE_NAME"

echo "✓ Container $CONTAINER_NAME launched successfully."
echo "  Web UI: http://localhost:9223"
echo "  Chrome Remote Debugging (CDP): http://localhost:9222"
