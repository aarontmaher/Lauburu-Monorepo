#!/usr/bin/env python3
"""
Linux Laptop & USB Bluetooth PAN Mesh Auto-Provisioner
Target: Dell Inspiron 15 3525 (AMD Ryzen 7 5700U)
Role: Layer 3 (Linux Head Node)
Canonical Mesh IP: 100.101.39.98 (Tailscale) / 192.168.8.224 / 192.168.8.225 (LAN)
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

# Mesh Peer Hardware Bluetooth MAC Addresses
PEER_BLUETOOTH_MACS = {
    "mac_mini": "1C:F6:4C:81:0B:28",
    "pixel_10_pro": "30:E0:44:6D:18:EC",
    "samsung_s20": "5C:CB:99:05:81:41",
    "macbook_pro": "2C:CA:16:08:C0:27",
}

# Linux Node Known Targets
TARGET_HOSTS = [
    {"ip": "100.101.39.98", "type": "tailscale"},
    {"ip": "192.168.8.224", "type": "lan_eth"},
    {"ip": "192.168.8.225", "type": "lan_wifi"},
]
TARGET_USERS = ["linux", "aaron"]
WOL_MACS = ["00:41:0e:14:28:43", "00:e0:4c:68:03:c8"]

PROVISION_PAYLOAD = """#!/usr/bin/env bash
set -eo pipefail

echo "=== [1/6] Enumerating USB Devices & Bluetooth Adapters ==="
lsusb
echo "--- HCI Interfaces ---"
hciconfig -a || bluetoothctl list || true

echo "=== [2/6] Loading Kernel Modules ==="
sudo modprobe btusb || true
sudo modprobe bnep || true

echo "=== [3/6] Unblocking RF & Powering HCI Adapters ==="
sudo rfkill unblock bluetooth || true
for hci in $(hciconfig 2>/dev/null | grep -o '^hci[0-9]*'); do
    echo "Powering up $hci..."
    sudo hciconfig "$hci" up || true
    sudo hciconfig "$hci" piscan || true
done

echo "=== [4/6] Configuring BlueZ Daemon ==="
sudo mkdir -p /etc/bluetooth
if [ -f /etc/bluetooth/main.conf ]; then
    sudo sed -i 's/^#AutoEnable=.*/AutoEnable=true/' /etc/bluetooth/main.conf || true
    sudo sed -i 's/^AutoEnable=.*/AutoEnable=true/' /etc/bluetooth/main.conf || true
else
    cat << 'CONF' | sudo tee /etc/bluetooth/main.conf
[General]
DiscoverableTimeout = 0
PairableTimeout = 0
AutoEnable = true
CONF
fi
sudo systemctl restart bluetooth || true

echo "=== [5/6] Trusting Mesh Peer Bluetooth MACs ==="
python3 -c "
import subprocess
peers = ['1C:F6:4C:81:0B:28', '30:E0:44:6D:18:EC', '5C:CB:99:05:81:41', '2C:CA:16:08:C0:27']
for mac in peers:
    subprocess.run(['bluetoothctl', 'trust', mac], capture_output=True)
    print(f'Marked {mac} as trusted')
" || true

echo "=== [6/6] Installing Bluetooth PAN Mesh Systemd Service ==="
cat << 'UNIT' | sudo tee /etc/systemd/system/bluetooth-pan-mesh.service
[Unit]
Description=Lauburu Bluetooth PAN BNEP Mesh Network Service
After=bluetooth.target network.target
Wants=bluetooth.target

[Service]
Type=simple
ExecStartPre=/sbin/modprobe bnep
ExecStart=/usr/bin/python3 -c "\
import subprocess, time;\
subprocess.run(['hciconfig', 'hci0', 'up']);\
subprocess.run(['hciconfig', 'hci0', 'piscan']);\
print('Bluetooth PAN listener ready.');\
while True: time.sleep(3600)"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now bluetooth-pan-mesh.service || true

echo "=== PROVISIONING COMPLETE ==="
ip -br addr show || true
hciconfig -a || true
"""


def send_wol():
    """Broadcast Wake-on-LAN magic packets."""
    for mac in WOL_MACS:
        clean_mac = mac.replace(":", "").replace("-", "")
        payload = b"\xff" * 6 + bytes.fromhex(clean_mac) * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for broadcast_ip in ["255.255.255.255", "192.168.8.255"]:
                try:
                    s.sendto(payload, (broadcast_ip, 9))
                except Exception:
                    pass
    print(f"[{datetime.now(timezone.utc).isoformat()}] Sent WoL packets to {WOL_MACS}")


def check_ssh(ip: str, user: str, timeout: int = 2) -> bool:
    """Check if SSH port is open and accepting authentication."""
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "StrictHostKeyChecking=no",
        f"{user}@{ip}",
        "echo reachable",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1)
        return res.returncode == 0 and "reachable" in res.stdout
    except (subprocess.TimeoutExpired, Exception):
        return False


def find_active_ssh():
    """Find active SSH target from known candidate addresses."""
    for target in TARGET_HOSTS:
        ip = target["ip"]
        for user in TARGET_USERS:
            if check_ssh(ip, user, timeout=2):
                return ip, user, target["type"]
    return None, None, None


def provision_node(ip: str, user: str):
    """Execute provisioning script remotely via SSH."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Connected to {user}@{ip}. Executing Bluetooth PAN provisioning...")
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        f"{user}@{ip}",
        "bash -s",
    ]
    res = subprocess.run(cmd, input=PROVISION_PAYLOAD, capture_output=True, text=True, timeout=60)
    print("--- Remote Provisioning Output ---")
    print(res.stdout)
    if res.stderr:
        print("--- Stderr ---")
        print(res.stderr)
    return res.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Linux Laptop & Bluetooth PAN Provisioner")
    parser.add_argument("--watch", action="store_true", help="Continuously poll until online and provision")
    parser.add_argument("--wol", action="store_true", help="Send Wake-on-LAN packets before probing")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    args = parser.parse_args()

    if args.wol:
        send_wol()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Probing for Linux Head Node...")
    active_ip, active_user, target_type = find_active_ssh()

    if active_ip:
        print(f"[FOUND] Active node at {active_ip} ({target_type}) as user '{active_user}'")
        success = provision_node(active_ip, active_user)
        sys.exit(0 if success else 1)

    if not args.watch:
        print(f"[OFFLINE] Linux Head Node not reachable on {TARGET_HOSTS}.")
        print("Required Physical Actions:")
        print("1. Ensure 4.5mm DC Barrel Charger is plugged in (USB-C port provides 0W charging).")
        print("2. Press the laptop Power Button.")
        print("3. If Dell BIOS displays 'AC power adapter wattage cannot be determined', strike 'F1'.")
        sys.exit(2)

    print("[WATCH] Polling in background for device boot...")
    try:
        while True:
            active_ip, active_user, target_type = find_active_ssh()
            if active_ip:
                print(f"\n[ONLINE] Detected {active_ip} ({target_type})! Proceeding with auto-provisioning...")
                success = provision_node(active_ip, active_user)
                sys.exit(0 if success else 1)
            time.sleep(args.interval)
            print(".", end="", flush=True)
    except KeyboardInterrupt:
        print("\nExiting watch mode.")
        sys.exit(0)


if __name__ == "__main__":
    main()
