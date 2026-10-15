#!/usr/bin/env bash
# ==============================================================================
# Pixel AVF microVM — Code-Server Installer & Setup
# Target Silicon: Google Tensor G5 (ARM64) under Linux AVF microVM
# ==============================================================================
set -euo pipefail

echo "==> Installing code-server on Pixel AVF Debian..."

# Ensure curl is present
if ! command -v curl &>/dev/null; then
    apt-get update && apt-get install -y curl
fi

# Install standalone code-server release
if ! command -v code-server &>/dev/null; then
    curl -fsSL https://code-server.dev/install.sh | sh
fi

# Create configuration directory
CONFIG_DIR="$HOME/.config/code-server"
mkdir -p "$CONFIG_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/config.yaml" "$CONFIG_DIR/config.yaml"

# User settings for touch screen & low RAM
USER_DATA_DIR="$HOME/.local/share/code-server/User"
mkdir -p "$USER_DATA_DIR"
cp "$SCRIPT_DIR/settings.json" "$USER_DATA_DIR/settings.json"

# Deploy systemd service if running under systemd
if [ -d "/etc/systemd/system" ] && [ "$(id -u)" -eq 0 ]; then
    cp "$SCRIPT_DIR/code-server.service" /etc/systemd/system/code-server.service
    systemctl daemon-reload
    systemctl enable code-server.service
    systemctl restart code-server.service
    echo "==> code-server.service enabled and started on port 8443."
else
    echo "==> Non-root or non-systemd environment. Launch with:"
    echo "    code-server --config $CONFIG_DIR/config.yaml"
fi
