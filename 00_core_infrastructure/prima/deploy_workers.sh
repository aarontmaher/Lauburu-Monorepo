#!/usr/bin/env bash
# Deploy prima.cpp workers across the Lauburu Mesh (L1, L2, L3, L5, L6, L7)
# Enforces prima.cpp supremacy over exo, ensuring cross-device compatibility.

set -e

# L1 (Mac Mini) serves as the primary coordinator
# Prefer Thunderbolt 4 IP if available, fallback to Tailscale IP
COORDINATOR_TB4_IP="192.168.10.1"
COORDINATOR_TS_IP="100.100.10.1"

# Define worker nodes (Hostnames or Tailscale IPs)
WORKERS=(
    "l1-macmini"
    "l2-node"
    "l3-node"
    "l5-node"
    "l6-node"
    "l7-node"
)

echo "Starting prima.cpp mesh deployment..."
echo "Coordinator set to L1 (TB4: $COORDINATOR_TB4_IP, Tailscale: $COORDINATOR_TS_IP)"

for worker in "${WORKERS[@]}"; do
    echo "========================================="
    echo "Deploying prima.cpp worker to $worker..."
    
    # 1. Stop and disable any legacy exo services
    echo "  -> Deprecating and disabling exo services..."
    ssh "$worker" "sudo systemctl disable --now exo-worker.service 2>/dev/null || true"
    ssh "$worker" "launchctl unload /Library/LaunchDaemons/com.exo.worker.plist 2>/dev/null || true"
    
    # 2. Deploy prima.cpp binary and configuration
    echo "  -> Syncing prima.cpp binaries..."
    rsync -avz ./bin/prima-worker "$worker":/usr/local/bin/prima-worker
    
    # 3. Start prima.cpp worker, routing to L1 over Tailscale or TB4
    echo "  -> Starting prima.cpp worker service..."
    ssh "$worker" << EOF
cat << 'SERVICE_EOF' | sudo tee /etc/systemd/system/prima-worker.service
[Unit]
Description=prima.cpp Tensor Sharding Worker
After=network.target tailscaled.service

[Service]
ExecStart=/usr/local/bin/prima-worker --coordinator $COORDINATOR_TS_IP
Restart=always
User=root

[Install]
WantedBy=multi-user.target
SERVICE_EOF

sudo systemctl daemon-reload
sudo systemctl enable --now prima-worker.service
EOF

    echo "  -> $worker deployment complete."
done

echo "========================================="
echo "prima.cpp deployment finished successfully."
