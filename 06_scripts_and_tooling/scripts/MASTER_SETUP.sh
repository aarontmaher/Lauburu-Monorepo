#!/usr/bin/env bash

# --- 1. SYSTEM PRIVILEGES & INTERNAL STORAGE PREP ---
STORAGE_PATH="${STORAGE_PATH:-/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data}"
echo "Checking internal storage at $STORAGE_PATH..."
mkdir -p "$STORAGE_PATH"

# --- 2. DATA MIGRATION (Move Everything to Internal Storage) ---
echo "--- 2. Moving AI Models & Caches to Internal Storage ---"
FOLDERS=( ".exo" ".cache" ".local" "exo_mac" )

for folder in "${FOLDERS[@]}"; do
    SRC="$HOME/$folder"
    DST="$STORAGE_PATH/$folder"

    if [ -d "$SRC" ] && [ ! -L "$SRC" ]; then
        echo "Moving $folder to internal storage..."
        mkdir -p "$STORAGE_PATH"
        cp -RPp "$SRC" "$STORAGE_PATH/" && rm -rf "$SRC" && ln -s "$DST" "$SRC"
    else
        echo "$folder already on internal storage or missing."
    fi
done

# --- 3. FIXING NETWORK ROUTING & INTERFACE ---
echo "--- 3. Optimizing Network for Adapter ---"
# Find the Ethernet adapter interface (usually the highest 'en' number)
ETH_IFACE=$(networksetup -listallhardwareports | awk '/Ethernet|LAN/ {getline; print $2}' | head -n 1)
if [ ! -z "$ETH_IFACE" ]; then
    echo "Found Ethernet Adapter at $ETH_IFACE. Prioritizing..."
    sudo networksetup -setv4off "$ETH_IFACE" && sudo networksetup -setdhcp "$ETH_IFACE"
fi

sudo route delete -net 192.168.8.0/24 -interface utun5 2>/dev/null || echo "VPN route clear."

# --- 4. INSTALLING KDE CONNECT & TOOLS ---
echo "--- 4. Installing KDE Connect (Pixel Controller) ---"
if ! which kdeconnect-cli > /dev/null; then
    # Fix Homebrew permissions first
    sudo chown -R $(whoami) /opt/homebrew "$HOME/Library/Caches/Homebrew" 2>/dev/null
    brew install --cask kde-connect
else
    echo "KDE Connect is ready."
fi

# --- 5. SSH CONNECTIVITY (Pixel & Router) ---
echo "--- 5. Synchronizing SSH Keys ---"
mkdir -p ~/.ssh
cat <<EOF > ~/.ssh/config
Host pixel
    HostName 127.0.0.1
    Port 18022
    User u0_a497
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking ask

Host router
    HostName 192.168.8.1
    User root
    IdentityFile ~/.ssh/id_rsa
EOF
chmod 600 ~/.ssh/config

# --- 6. RESTARTING AI CLUSTER (EXO) ---
echo "--- 6. Restarting EXO Cluster ---"
killall exo EXO 2>/dev/null || true
sleep 2
export EXO_ZENOH_NAMESPACE="lauburu"
export UV_CACHE_DIR="$HOME/.cache/uv"
cd ~/exo_mac
uv run exo > ~/exo_mac/exo_node_live.log 2>&1 &
echo "EXO Cluster active. Logs at: tail -f ~/exo_mac/exo_node_live.log"

# --- 7. DOCKER & GL.iNET APP ---
echo "--- 7. Re-initializing Backend Services ---"
open -a Docker
echo "If GL.iNet site fails, refresh http://192.168.8.1 now."

echo "--- SWARM SYNC COMPLETE ---"
