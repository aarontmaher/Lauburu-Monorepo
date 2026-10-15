#!/usr/bin/env bash
# Deploy Movesense Ingestion Suites with Podman on Linux or macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_CONFIG="${1:-all}" # chromium, go, rfcomm, or all

echo "================================================================="
echo "Movesense Podman Multi-Configuration Launcher"
echo "Target Configuration: $TARGET_CONFIG"
echo "================================================================="

case "$TARGET_CONFIG" in
    chromium)
        echo "Launching Headless Chromium Web Bluetooth Ingestion..."
        bash "$SCRIPT_DIR/chromium_web_bluetooth/run.sh"
        ;;
    go)
        echo "Launching Go GATT Browser Ingestion..."
        bash "$SCRIPT_DIR/go_gatt_browser/run.sh"
        ;;
    rfcomm)
        echo "Launching Bluetooth Serial / RFCOMM Browser Ingestion..."
        bash "$SCRIPT_DIR/bluetooth_serial_rfcomm/run.sh"
        ;;
    all)
        echo "Launching all configurations via podman-compose..."
        if command -v podman-compose >/dev/null 2>&1; then
            podman-compose -f "$SCRIPT_DIR/podman-compose.movesense.yml" up -d --build
        else
            echo "podman-compose not found, running individual run.sh scripts..."
            bash "$SCRIPT_DIR/chromium_web_bluetooth/run.sh"
            bash "$SCRIPT_DIR/go_gatt_browser/run.sh"
            bash "$SCRIPT_DIR/bluetooth_serial_rfcomm/run.sh"
        fi
        ;;
    *)
        echo "Usage: $0 [chromium | go | rfcomm | all]"
        exit 1
        ;;
esac

echo "================================================================="
echo "Endpoints Available:"
echo "  - Chromium Web Bluetooth: http://localhost:9223 (CDP :9222)"
echo "  - Go GATT Browser:        http://localhost:8084"
echo "  - Bluetooth Serial RFCOMM:http://localhost:8089"
echo "================================================================="
