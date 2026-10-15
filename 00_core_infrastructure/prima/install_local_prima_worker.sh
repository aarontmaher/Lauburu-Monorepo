#!/usr/bin/env bash
# Local Installer for prima.cpp worker (run on each node after Syncthing syncs it)
# Enforces prima.cpp supremacy over exo (Rule 20)
# Honors Opus 5.5 architecture review & User directive: Excludes AVF Mobile due to lack of NPU passthrough.

set -e

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"
HOSTNAME="$(hostname)"

echo "Installing prima.cpp worker on $HOSTNAME ($OS $ARCH)..."

if [[ "$HOSTNAME" == *"pixel"* ]] || [[ "$HOSTNAME" == *"galaxy"* ]] || [[ "$HOSTNAME" == *"localhost"* && "$OS" == "Linux" && "$ARCH" == "aarch64" ]]; then
    echo "Aborting Prima.cpp install: Android AVF microVM does not have PCIe/MMIO passthrough to the Tensor G5 Edge TPU/NPU. Using CPU-only here would bottleneck the entire Thunderbolt Mac ring."
    exit 0
fi

# Coordinator IPs (L1 Mac Mini)
COORDINATOR_TB4_IP="169.254.186.211" # Mac Mini bridge0 IP
COORDINATOR_TS_IP="100.119.199.76"   # Mac Mini Tailscale IP

# Determine best IP to use based on ping
echo "Testing Thunderbolt 4 Data Plane to Coordinator ($COORDINATOR_TB4_IP)..."
if ping -c 1 -W 1 $COORDINATOR_TB4_IP >/dev/null 2>&1; then
    ACTIVE_COORDINATOR=$COORDINATOR_TB4_IP
    echo "Thunderbolt 4 link active. Latency < 1ms."
else
    ACTIVE_COORDINATOR=$COORDINATOR_TS_IP
    echo "Thunderbolt 4 unlinked. Falling back to Tailscale Control Plane ($ACTIVE_COORDINATOR)."
fi

# 1. Stop and disable legacy exo
echo "Disabling legacy Exo services..."
if [ "$OS" = "Darwin" ]; then
    launchctl unload /Library/LaunchDaemons/com.exo.worker.plist 2>/dev/null || true
    launchctl unload ~/Library/LaunchAgents/com.exo.worker.plist 2>/dev/null || true
elif [ "$OS" = "Linux" ]; then
    sudo systemctl disable --now exo-worker.service 2>/dev/null || true
fi

# 2. Determine Prima.cpp worker arguments
PRIMA_ARGS="--coordinator $ACTIVE_COORDINATOR"
if [ "$OS" = "Darwin" ]; then
    echo "Detected macOS. Enabling Metal backend."
    PRIMA_ARGS="$PRIMA_ARGS --gpu-layers 99"
fi

mkdir -p $HOME/.local/bin
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET_BIN=""
OS_LOWER="$(echo "$OS" | tr '[:upper:]' '[:lower:]')"
ARCH_LOWER="$ARCH"
if [ "$ARCH" = "x86_64" ]; then
    ARCH_LOWER="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH_LOWER="arm64"
fi

CANDIDATE="$DIR/../bin/prima-worker-${OS_LOWER}-${ARCH_LOWER}"
if [ -f "$CANDIDATE" ]; then
    TARGET_BIN="$CANDIDATE"
elif [ -f "$DIR/../bin/prima-worker" ]; then
    TARGET_BIN="$DIR/../bin/prima-worker"
fi

if [ -n "$TARGET_BIN" ]; then
    echo "Copying synced prima-worker binary from $TARGET_BIN..."
    rm -f $HOME/.local/bin/prima-worker
    cp "$TARGET_BIN" $HOME/.local/bin/prima-worker
    chmod +x $HOME/.local/bin/prima-worker
else
    echo "WARNING: prima-worker binary not found in 00_core_infrastructure/bin/."
    echo "Please build or drop prima-worker for your OS/Arch into the Syncthing bin folder."
fi

# 3. Create service files
if [ "$OS" = "Darwin" ]; then
    cat << PLIST_EOF > ~/Library/LaunchAgents/ai.lauburu.prima-worker.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.lauburu.prima-worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>sh</string>
        <string>-c</string>
        <string>$HOME/.local/bin/prima-worker $PRIMA_ARGS</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/prima-worker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/prima-worker.err</string>
</dict>
</plist>
PLIST_EOF
    launchctl unload ~/Library/LaunchAgents/ai.lauburu.prima-worker.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/ai.lauburu.prima-worker.plist
    echo "Started prima-worker via LaunchAgent."

elif [ "$OS" = "Linux" ]; then
    cat << SERVICE_EOF | sudo tee /etc/systemd/system/prima-worker.service
[Unit]
Description=prima.cpp Tensor Sharding Worker
After=network.target tailscaled.service

[Service]
ExecStart=$HOME/.local/bin/prima-worker $PRIMA_ARGS
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now prima-worker.service
    echo "Started prima-worker via systemd."
fi

echo "Prima.cpp local installation complete."
