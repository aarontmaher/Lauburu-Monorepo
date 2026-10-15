#!/bin/bash
# ==============================================================================
# 🛰️ Lauburu Pixel 10 Pro XL AVF Debian 13 (Trixie) Sovereign Bootstrap
# Optimized for Tensor G5 AVF crosvm microVM (Debian 13 aarch64 + Python 3.14)
# Governed by Rule 0, Rule 1 (Zero-Mock Truth) & Rule 3 (Host Sanctuary)
# ==============================================================================

set -euo pipefail

echo "===================================================================="
echo "🚀 Initializing Lauburu Edge Workstation on Pixel 10 Pro XL"
echo "Target OS: Debian 13 (Trixie) aarch64 / AVF Terminal"
echo "===================================================================="

# 1. Update APT and install essential networking, wireguard, and dev tools
echo "📦 [1/5] Updating APT packages and installing core utilities..."
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    wireguard-tools \
    iproute2 \
    iptables \
    curl \
    wget \
    git \
    rsync \
    openssh-client \
    openssh-server \
    tmux \
    procps \
    net-tools \
    ca-certificates \
    libglib2.0-0 \
    bluetooth \
    bluez

# 2. Install Astral uv and Python 3.14
echo "⚡ [2/5] Installing Astral uv and Python 3.14 (Parity with L1 & L8)..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv python install 3.14
uv venv --python 3.14 ~/.lauburu_venv
source ~/.lauburu_venv/bin/activate

# 3. Install core lightweight project dependencies
echo "📚 [3/5] Installing verified monorepo edge dependencies into Python 3.14..."
uv pip install \
    fastapi \
    uvicorn \
    httpx \
    aiohttp \
    websockets \
    numpy \
    cryptography \
    pyyaml \
    rich \
    google-genai

# 4. WireGuard Mesh Client Configuration (Peer 10.42.0.7)
echo "🔒 [4/5] Configuring WireGuard Mesh Client (IP: 10.42.0.7)..."
sudo mkdir -p /etc/wireguard
sudo tee /etc/wireguard/wg0.conf > /dev/null << 'EOF'
[Interface]
Address = 10.42.0.7/24
PrivateKey = CGLARZWCVvapKuOuU/ZhrzKXloxif0i6Q33Mk15jPXM=

[Peer]
PublicKey = NIQVFgRxRpg4ba65qrw9PYM5wjpsJ6wOJWOgX9ZnmWE=
PresharedKey = wYM4deOfHa+3sJ+7EVeZBbzehmEEPbO0OgclagBG+OE=
Endpoint = 100.121.247.8:51820
AllowedIPs = 10.42.0.0/24
PersistentKeepalive = 25
EOF

sudo chmod 600 /etc/wireguard/wg0.conf

# 5. SSH Client Config for instant access to L1 Mac Mini and L8 Linux Hub
echo "🔑 [5/5] Configuring SSH host mappings for the 10.42.0.0/24 mesh..."
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat >> ~/.ssh/config << 'EOF'
# Lauburu WireGuard Mesh Hosts
Host hub l8 lauburu-hub
    HostName 10.42.0.1
    Port 2222
    User root
    StrictHostKeyChecking no

Host mac-mini l1
    HostName 10.42.0.2
    User aaron
    StrictHostKeyChecking no
EOF
chmod 600 ~/.ssh/config

echo "===================================================================="
echo "✅ Pixel 10 AVF Debian 13 Edge Workstation Setup Complete!"
echo "To bring up the WireGuard tunnel: sudo wg-quick up wg0"
echo "To verify connectivity to L8: ping 10.42.0.1"
echo "To verify connectivity to L1 Mac Mini: ping 10.42.0.2"
echo "Python 3.14 environment: source ~/.lauburu_venv/bin/activate"
echo "===================================================================="
