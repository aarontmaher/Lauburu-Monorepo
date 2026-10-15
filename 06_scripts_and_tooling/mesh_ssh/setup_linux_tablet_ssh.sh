#!/usr/bin/env bash
# ==============================================================================
# 📱 Lauburu Sovereign Mesh — Linux Tablet (Node L4 / DESKTOP-Q4SI00P)
# Physical / Bluetooth Setup & Network Healing Script
# Target: DESKTOP-Q4SI00P (MAC: 98:fc:84:e6:e2:12 / 00:03:7f:c2:00:43)
# ==============================================================================

set -e

echo "======================================================================"
echo "🚀 LAUBURU LINUX TABLET SETUP: SSH KEYS & NETWORK HEALING"
echo "======================================================================"

# 1. Setup SSH directory and permissions
echo "[1/4] Configuring OpenSSH directories and authorized keys..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. Append all mesh public keys (MacBook Air/Pro + Mac Mini)
cat >> ~/.ssh/authorized_keys << 'EOF'
# MacBook Air M4 Host
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIONTPyqCKyEEBZCLliqTxdBSXOQ3m3E0lONi6VxjgZsj aaronmaher@mac.local
# Mac Mini M4 Pro
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHBCVTl2xI3jRLUFvbasxL8BAao8waCSO8rE1Z5cl9lp aaron@Aarons-Mac-mini.local
# Mac Mini M4 Pro RSA Fallback
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDvB3Y52dG5QFSnAGf14j3koametoDXuWGteogpIqvXFoJ7KDmx7odnLFEBPVYxxUqMRSiNqAtgeSHPzJR2BOZC0N5qqY5C2E2CLs1OerYghMxX+rtCuxdyslLBx0YsIpPkA1LeZGGhzjNQMVsaAv8pOzLnENVaBT8cO4bXUPFftOJE9cNN4fWBjm2RMRVgjhrpOjo4MdzIjVxPpzUsHc6E1vnraAfCV3QHZfA7KoSbkPMiAfndabOma7kZUlhTQgUHL6HVHGg4tNSjQTioUdSao21zjCSHAduvfvWPiEo13Ulv8sd2b+NzTZ9AkQlUVnrMerkaJjei+dT/1cu8wrYhpn2RjDPG+xLAzCSFGvG5PMMA79AuSQHIvXUmFSXSzix+sjZkeZ/MdBJ+EGUhnftMRD6B8uG8NEs0cxQqlXXJzTd9tUIhpJptdAdHKP5+VqWtfJ6RQhgiJQb3QNzkqAecFtNf5xxvlx6xDRXam9NyyYTuK3xBOZqYg0dViykCbmM= aaronmaher@mac-2.local
EOF

# Ensure clean permissions and deduplicate keys
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo "✅ SSH Authorized Keys successfully configured and hardened."

# 3. Ensure OpenSSH Server is running and enabled
echo "[2/4] Ensuring OpenSSH daemon is active..."
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl enable ssh 2>/dev/null || sudo systemctl enable sshd 2>/dev/null || true
    sudo systemctl restart ssh 2>/dev/null || sudo systemctl restart sshd 2>/dev/null || true
elif command -v service >/dev/null 2>&1; then
    sudo service ssh restart 2>/dev/null || true
else
    sshd 2>/dev/null || true
fi
echo "✅ SSH daemon restarted."

# 4. Heal Network & Refresh DHCP Leases
echo "[3/4] Healing Wi-Fi, Ethernet, and Bluetooth interfaces..."
if command -v dhclient >/dev/null 2>&1; then
    sudo dhclient -r 2>/dev/null || true
    sudo dhclient -v 2>/dev/null || true
elif command -v nmcli >/dev/null 2>&1; then
    sudo nmcli networking off 2>/dev/null && sudo nmcli networking on 2>/dev/null || true
fi

# 5. Summary & Active IP Display
echo "[4/4] Active Network Interfaces:"
ip -br a 2>/dev/null || ip a 2>/dev/null || ifconfig

echo "======================================================================"
echo "🎉 Tablet Connectivity & SSH Keys Configured Successfully!"
echo "======================================================================"
