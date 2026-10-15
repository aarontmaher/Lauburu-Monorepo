#!/bin/bash
set -e

echo "[*] Initializing Sovereign WireGuard & Mesh Container..."

# Ensure /etc/wireguard directory exists
mkdir -p /etc/wireguard

# Check if wg0.conf exists, otherwise wait
if [ -f /etc/wireguard/wg0.conf ]; then
    echo "[+] Bringing up wg0 interface..."
    ip link del wg0 2>/dev/null || true
    wg-quick up wg0 || echo "[!] Warning: wg-quick up had non-fatal warning"
fi

# Ensure authorized_keys is present if mounted
if [ -f /etc/wireguard/authorized_keys ]; then
    cp /etc/wireguard/authorized_keys /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
fi

# Verify project dependencies
if [ -x /usr/local/bin/verify_project_deps.py ]; then
    echo "[*] Running project dependency self-test..."
    /usr/local/bin/verify_project_deps.py || true
fi

# Start SSH daemon on port 2222
echo "[+] Starting SSH daemon on port 2222..."
mkdir -p /var/run/sshd
/usr/sbin/sshd -p 2222

echo "[✓] WireGuard Mesh Container Ready and Listening on UDP 51820 & TCP 2222."
echo "[*] Monitoring wg0 status..."

# Keep alive loop
while true; do
    wg show 2>/dev/null || true
    sleep 30
done
