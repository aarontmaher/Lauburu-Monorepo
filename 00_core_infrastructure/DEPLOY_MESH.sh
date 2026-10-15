#!/usr/bin/env bash
# Global Mesh Deployment Script
# Run this script on ANY device in the Lauburu Mesh after Syncthing syncs this folder.
# It automatically detects the OS and sets up the 3-tier unification architecture.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting 3-Tier Mesh Unification Deployment on $(hostname)..."
echo "Following Opus 5.5 Architecture Review Rules..."

# 1. Install SeaweedFS Volume Server
echo "==> Deploying SeaweedFS Volume Server..."
bash "$DIR/seaweedfs/install_local_seaweedfs_volume.sh"

# 2. Install HashiCorp Nomad Client
echo "==> Deploying HashiCorp Nomad Client..."
bash "$DIR/nomad/install_local_nomad_client.sh"

# 3. Install Prima.cpp Worker
echo "==> Deploying Prima.cpp Worker (Replacing Exo)..."
bash "$DIR/prima/install_local_prima_worker.sh"

# 4. Enforce Docker Storage Hygiene (Anti-APFS Exhaustion)
echo "==> Running Docker Storage Hygiene Check..."
bash "$DIR/docker/docker_storage_hygiene_daemon.sh" --once || true

echo "========================================="
echo "Deployment Complete on $(hostname)!"
echo "Check statuses:"
if [ "$(uname -s)" = "Darwin" ]; then
    echo "  launchctl list | grep lauburu"
else
    echo "  sudo systemctl status seaweedfs-volume nomad-client prima-worker"
fi
