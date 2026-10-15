#!/usr/bin/env bash
# ==============================================================================
# Pixel AVF microVM — Chromium Browser & DevTools Setup
# ==============================================================================
set -euo pipefail

echo "==> Installing Chromium & X11/Wayland dependencies on Pixel AVF Debian..."

apt-get update
apt-get install -y \
    chromium \
    chromium-sandbox \
    fonts-liberation \
    libasound2t64 \
    libnspr4 \
    libnss3 \
    xdg-utils

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$SCRIPT_DIR/launch_chromium_ide.sh"

if [ -d "/etc/systemd/system" ] && [ "$(id -u)" -eq 0 ]; then
    cp "$SCRIPT_DIR/chromium_kiosk.service" /etc/systemd/system/chromium_kiosk.service
    systemctl daemon-reload
    echo "==> chromium_kiosk.service deployed."
fi
