#!/usr/bin/env bash
# ==============================================================================
# Pixel AVF microVM — JupyterLab Installer & Setup
# ==============================================================================
set -euo pipefail

echo "==> Installing JupyterLab on Pixel AVF Debian..."

# Ensure Python3 and venv are present
if ! command -v python3 &>/dev/null; then
    apt-get update && apt-get install -y python3 python3-pip python3-venv
fi

# Create dedicated virtual environment for Jupyter
JUPYTER_VENV="$HOME/.local/share/jupyter_venv"
if [ ! -d "$JUPYTER_VENV" ]; then
    python3 -m venv "$JUPYTER_VENV"
fi

"$JUPYTER_VENV/bin/pip" install --upgrade pip
"$JUPYTER_VENV/bin/pip" install jupyterlab ipykernel matplotlib numpy scipy

# Install config
CONFIG_DIR="$HOME/.jupyter"
mkdir -p "$CONFIG_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/jupyter_lab_config.py" "$CONFIG_DIR/jupyter_lab_config.py"

# Deploy systemd service if root
if [ -d "/etc/systemd/system" ] && [ "$(id -u)" -eq 0 ]; then
    cp "$SCRIPT_DIR/jupyterlab.service" /etc/systemd/system/jupyterlab.service
    systemctl daemon-reload
    systemctl enable jupyterlab.service
    systemctl restart jupyterlab.service
    echo "==> jupyterlab.service enabled and started on port 8888."
else
    echo "==> Launch manually with:"
    echo "    $JUPYTER_VENV/bin/jupyter lab --config $CONFIG_DIR/jupyter_lab_config.py"
fi
