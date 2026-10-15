#!/usr/bin/env bash
# Runs Go GATT Browser Ingestion container via Podman
set -e

CONTAINER_NAME="movesense-go-gatt-browser"
IMAGE_NAME="localhost/movesense-go-gatt-browser:latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Building $IMAGE_NAME with Podman ==="
podman build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Containerfile" "$SCRIPT_DIR"

echo "=== Stopping existing container if running ==="
podman rm -f "$CONTAINER_NAME" 2>/dev/null || true

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
    -e PORT=8084 \
    "$IMAGE_NAME"

echo "✓ Container $CONTAINER_NAME launched successfully."
echo "  Go Browser UI: http://localhost:8084"
