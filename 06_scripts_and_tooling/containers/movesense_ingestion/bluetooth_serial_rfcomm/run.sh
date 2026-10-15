#!/usr/bin/env bash
# Runs Bluetooth Serial / RFCOMM Ingestion container via Podman
set -e

CONTAINER_NAME="movesense-bluetooth-serial-rfcomm"
IMAGE_NAME="localhost/movesense-bluetooth-serial-rfcomm:latest"
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
    -v /dev:/dev \
    -e PORT=8089 \
    -e RFCOMM_DEV=/dev/rfcomm0 \
    "$IMAGE_NAME"

echo "✓ Container $CONTAINER_NAME launched successfully."
echo "  RFCOMM Browser UI: http://localhost:8089"
