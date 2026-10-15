#!/usr/bin/env bash
# Deploy Chromium Mesh IDE to Linux Hub (L3)
# Rule 10: Linux Mini First-Offload Invariant

set -e

LINUX_HUB_IP="100.101.39.98"
LOCAL_PROJECT_DIR="/Users/aaron/teamwork_projects/chromium_mesh_ide"
REMOTE_PROJECT_DIR="/home/linux/teamwork_projects/chromium_mesh_ide"
SERVICE_FILE="/Volumes/Lauburu-Monorepo/00_core_infrastructure/systemd/chromium_mesh_ide.service"
SSH_USER="linux"
SUDO_PASS="goldfighting1"

echo "🚀 Deploying Chromium Mesh IDE to Linux Hub ($SSH_USER@$LINUX_HUB_IP)..."

# Ensure the remote parent directory exists
ssh "$SSH_USER@$LINUX_HUB_IP" "mkdir -p $REMOTE_PROJECT_DIR"

# 1. Sync the project directory (excluding node_modules so we install natively on Linux)
echo "📦 Syncing files..."
rsync -avz --exclude 'node_modules' --exclude '.git' "$LOCAL_PROJECT_DIR/" "$SSH_USER@$LINUX_HUB_IP:$REMOTE_PROJECT_DIR/"

# 2. Sync the systemd service file
echo "📄 Syncing systemd service..."
scp "$SERVICE_FILE" "$SSH_USER@$LINUX_HUB_IP:/tmp/chromium_mesh_ide.service"

# 3. Execute remote setup via SSH
echo "🔧 Configuring server and restarting daemon..."
ssh "$SSH_USER@$LINUX_HUB_IP" << EOF
    set -e
    cd $REMOTE_PROJECT_DIR
    
    # Install dependencies on the Linux architecture
    npm install
    
    # Move service file to systemd directory (requires sudo)
    echo "$SUDO_PASS" | sudo -S mv /tmp/chromium_mesh_ide.service /etc/systemd/system/chromium_mesh_ide.service
    
    # Reload and restart
    echo "$SUDO_PASS" | sudo -S systemctl daemon-reload
    echo "$SUDO_PASS" | sudo -S systemctl enable chromium_mesh_ide.service
    echo "$SUDO_PASS" | sudo -S systemctl restart chromium_mesh_ide.service
    
    echo "✅ Service Status:"
    echo "$SUDO_PASS" | sudo -S systemctl status chromium_mesh_ide.service --no-pager | head -n 15
EOF

echo "🎉 Deployment complete! The IDE backend is now running on the Linux Hub."
