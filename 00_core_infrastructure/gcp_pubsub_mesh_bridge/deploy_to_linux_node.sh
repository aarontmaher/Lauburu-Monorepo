#!/bin/bash
set -e

echo "🚀 Deploying Local Subscriber to L3 Linux Head Node (100.101.39.98)..."

TARGET="linux"
REMOTE_DIR="/opt/lauburu/gcp_pubsub_mesh_bridge"
LOCAL_DIR="/Volumes/Lauburu-Monorepo/00_core_infrastructure/gcp_pubsub_mesh_bridge"
SYSTEMD_FILE="/Volumes/Lauburu-Monorepo/00_core_infrastructure/systemd/lauburu-pubsub-subscriber.service"

echo "Creating remote directory..."
ssh -o ConnectTimeout=5 "$TARGET" "sudo mkdir -p $REMOTE_DIR && sudo chown -R linux:linux /opt/lauburu"

echo "Copying subscriber files..."
rsync -avz --exclude 'venv' --exclude '__pycache__' "$LOCAL_DIR/local_subscriber" "$TARGET:$REMOTE_DIR/"

echo "Copying systemd service..."
scp "$SYSTEMD_FILE" "$TARGET:/tmp/lauburu-pubsub-subscriber.service"
ssh "$TARGET" "sudo mv /tmp/lauburu-pubsub-subscriber.service /etc/systemd/system/lauburu-pubsub-subscriber.service"

echo "Setting up Python venv and installing requirements on remote..."
ssh "$TARGET" "cd $REMOTE_DIR/local_subscriber && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"

echo "Reloading systemd and enabling service..."
ssh "$TARGET" "sudo systemctl daemon-reload && sudo systemctl enable lauburu-pubsub-subscriber.service && sudo systemctl restart lauburu-pubsub-subscriber.service"

echo "✅ Deployment complete. Service 'lauburu-pubsub-subscriber' is now running on the L3 Linux Head Node."
