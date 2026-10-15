#!/usr/bin/env bash
# Local Installer for Nomad Client
# Honors Opus 5.5 architecture review: uses node.meta tags for aware scheduling.

set -e

OS="$(uname -s)"
HOSTNAME="$(hostname)"
ARCH="$(uname -m)"

echo "Installing Nomad Client on $HOSTNAME ($OS $ARCH)..."

mkdir -p $HOME/nomad_data
mkdir -p $HOME/nomad_config
mkdir -p $HOME/.local/bin

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR/../bin/nomad" ]; then
    echo "Copying synced nomad binary..."
    rm -f $HOME/.local/bin/nomad
    cp "$DIR/../bin/nomad" $HOME/.local/bin/nomad
    chmod +x $HOME/.local/bin/nomad
else
    echo "WARNING: nomad binary not found in 00_core_infrastructure/bin/."
    echo "Please download the nomad binary for your OS/Arch and place it in the Syncthing bin folder."
fi

# Determine meta tags
if [[ "$HOSTNAME" == *"mac-mini"* ]] || [[ "$HOSTNAME" == *"linux-mini"* ]]; then
    TIER="always_on"
else
    TIER="edge"
fi

if [[ "$OS" == "Darwin" ]]; then
    ACCEL="metal"
else
    ACCEL="cpu"
fi

cat << HCL_EOF > $HOME/nomad_config/client.hcl
data_dir = "$HOME/nomad_data"

client {
  enabled = true
  servers = ["100.101.39.98"]
  
  meta {
    tier = "$TIER"
    accel = "$ACCEL"
  }
}
HCL_EOF

if [ "$OS" = "Darwin" ]; then
    cat << PLIST_EOF > ~/Library/LaunchAgents/com.hashicorp.nomad.client.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hashicorp.nomad.client</string>
    <key>ProgramArguments</key>
    <array>
        <string>sh</string>
        <string>-c</string>
        <string>$HOME/.local/bin/nomad agent -config=$HOME/nomad_config/client.hcl</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/nomad-client.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/nomad-client.err</string>
</dict>
</plist>
PLIST_EOF
    launchctl unload ~/Library/LaunchAgents/com.hashicorp.nomad.client.plist 2>/dev/null || true
    launchctl load ~/Library/LaunchAgents/com.hashicorp.nomad.client.plist
    echo "Started Nomad Client via LaunchAgent."

elif [ "$OS" = "Linux" ]; then
    cat << SERVICE_EOF | sudo tee /etc/systemd/system/nomad-client.service
[Unit]
Description=Nomad Client
After=network.target tailscaled.service

[Service]
ExecStart=$HOME/.local/bin/nomad agent -config=%h/nomad_config/client.hcl
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    sudo systemctl daemon-reload
    sudo systemctl enable --now nomad-client.service
    echo "Started Nomad Client via systemd."
fi
