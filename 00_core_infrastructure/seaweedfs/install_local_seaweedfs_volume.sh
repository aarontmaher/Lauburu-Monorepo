#!/usr/bin/env bash
# Local Installer for SeaweedFS volume server
# Honors Opus 5.5 architecture review: topology-aware replication and FUSE warnings.
# Per User Request (Oct 5): Exclude mobile devices (Pixel, Galaxy) to avoid "Churn Node" trapping.

set -e

OS="$(uname -s)"
HOSTNAME="$(hostname)"

echo "Installing SeaweedFS Volume Server on $HOSTNAME ($OS)..."

# Filter out mobile devices as requested by User
if [[ "$HOSTNAME" == *"pixel"* ]] || [[ "$HOSTNAME" == *"galaxy"* ]] || [[ "$HOSTNAME" == *"localhost"* && "$OS" == "Linux" && "$(uname -m)" == "aarch64" ]]; then
    echo "Aborting SeaweedFS volume install: Android Edge nodes are excluded from volume pooling to prevent data stranding when asleep."
    exit 0
fi

# Master is on Linux Mini (L3)
MASTER_TS_IP="100.101.39.98:9333"

mkdir -p $HOME/.local/bin
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR/../bin/weed" ]; then
    echo "Copying synced weed binary..."
    rm -f $HOME/.local/bin/weed
    cp "$DIR/../bin/weed" $HOME/.local/bin/weed
    chmod +x $HOME/.local/bin/weed
else
    echo "WARNING: weed binary not found in 00_core_infrastructure/bin/."
fi

# Determine Rack based on device
if [[ "$HOSTNAME" == *"mac-mini"* ]]; then
    RACK="always_on_mac"
    MAX_VOLUMES=40
elif [[ "$HOSTNAME" == *"linux-mini"* ]]; then
    RACK="always_on_linux"
    MAX_VOLUMES=40
else
    RACK="churn_laptop"
    MAX_VOLUMES=20
fi

if [ "$OS" = "Darwin" ]; then
    TS_IP="$(ipconfig getifaddr utun2 || ipconfig getifaddr utun3 || echo '127.0.0.1')"
    cat << PLIST_EOF > ~/Library/LaunchAgents/ai.lauburu.seaweedfs-volume.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.lauburu.seaweedfs-volume</string>
    <key>ProgramArguments</key>
    <array>
        <string>sh</string>
        <string>-c</string>
        <string>mkdir -p $HOME/seaweedfs_volume_data &amp;&amp; $HOME/.local/bin/weed volume -mserver=$MASTER_TS_IP -dir=$HOME/seaweedfs_volume_data -port=8086 -max=$MAX_VOLUMES -rack=$RACK -ip=$TS_IP</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/seaweedfs-volume.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/seaweedfs-volume.err</string>
</dict>
</plist>
PLIST_EOF
    launchctl unload ~/Library/LaunchAgents/ai.lauburu.seaweedfs-volume.plist 2>/dev/null || true
    
    launchctl load ~/Library/LaunchAgents/ai.lauburu.seaweedfs-volume.plist
    echo "Started SeaweedFS volume via LaunchAgent."

elif [ "$OS" = "Linux" ]; then
    TS_IP="$(ip -4 addr show tailscale0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo '127.0.0.1')"
    cat << SERVICE_EOF | sudo tee /etc/systemd/system/seaweedfs-volume.service
[Unit]
Description=SeaweedFS Volume Server
After=network.target tailscaled.service

[Service]
ExecStart=$HOME/.local/bin/weed volume -mserver=$MASTER_TS_IP -dir=%h/seaweedfs_volume_data -port=8086 -max=$MAX_VOLUMES -rack=$RACK -ip=$TS_IP
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now seaweedfs-volume.service
    echo "Started SeaweedFS volume via systemd."
fi
