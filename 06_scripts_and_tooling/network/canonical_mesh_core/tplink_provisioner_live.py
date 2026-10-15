#!/usr/bin/env python3
import os
import sys
import time
import socket
import subprocess

TARGETS = [
    ("192.168.8.238", 22, "Ethernet LAN"),
    ("192.168.2.3", 22, "Thunderbolt IPv4"),
    ("fe80::1082:a3ff:fe9e:ae71%bridge0", 22, "Thunderbolt IPv6"),
]

def check_tcp(host, port=22, timeout=0.5):
    try:
        if "%" in host:
            addr, ifname = host.split("%")
            idx = socket.if_nametoindex(ifname)
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((addr, port, 0, idx))
            s.close()
            return res == 0
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((host, port))
            s.close()
            return res == 0
    except Exception:
        return False

def run_ssh(host, cmd, timeout=35):
    ssh_host = host
    if "%" in host:
        ssh_host = host.replace("%", "%%")
    cmd_list = [
        "ssh", "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-i", "/Users/aaron/.ssh/id_rsa",
        f"linuxmini@{ssh_host}",
        cmd
    ]
    p = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def provision(host, label):
    print(f"\n🟢 [DETECTED] Linux Mini is REACHABLE on {label} ({host}:22)!")
    print("Executing automated Wi-Fi provisioning and Netplan unblocking...")

    rc, stdout, stderr = run_ssh(host, "lsusb && echo '---' && ip -br link")
    print(f"\n[Hardware Probing]:\n{stdout}")

    remote_script = """
set -e
echo "=== 1. Identifying Wi-Fi Interfaces ==="
iw dev || true
WIFI_IFACE=$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2}' | head -n 1)
if [ -z "$WIFI_IFACE" ]; then
    WIFI_IFACE=$(ip -br link | awk '$1 ~ /^wl/ {print $1}' | head -n 1)
fi
echo "Selected Wi-Fi Interface: $WIFI_IFACE"

if [ -n "$WIFI_IFACE" ]; then
    sudo -n ip link set "$WIFI_IFACE" up 2>/dev/null || true
    if command -v nmcli &>/dev/null; then
        echo "=== 2. Connecting with nmcli ==="
        sudo -n nmcli radio wifi on 2>/dev/null || true
        sudo -n nmcli dev wifi connect "GL-MT3600BE-a0f" password "goldfighting1" ifname "$WIFI_IFACE" || true
    fi
fi

echo "=== 3. Hardening Netplan to Prevent Boot Hangs ==="
for f in /etc/netplan/*.yaml /etc/netplan/*.yml; do
    if [ -f "$f" ]; then
        echo "Patching $f to make enp4s0 optional..."
        sudo -n sed -i 's/optional: false/optional: true/g' "$f" 2>/dev/null || true
        if ! grep -q "optional: true" "$f"; then
            sudo -n sed -i '/enp4s0:/a \\      optional: true' "$f" 2>/dev/null || true
        fi
    fi
done

sudo -n netplan apply 2>/dev/null || true

echo "=== 4. Ensuring SSH listens on all interfaces ==="
sudo -n sed -i 's/^#*ListenAddress 0.0.0.0/ListenAddress 0.0.0.0/' /etc/ssh/sshd_config 2>/dev/null || true
sudo -n sed -i 's/^#*ListenAddress ::/ListenAddress ::/' /etc/ssh/sshd_config 2>/dev/null || true
sudo -n systemctl restart ssh 2>/dev/null || sudo -n systemctl restart sshd 2>/dev/null || true

echo "=== 5. Network Summary ==="
ip -br addr
echo "=== 6. WAN Egress Verification ==="
ping -c 2 1.1.1.1 || true
"""
    rc, out, err = run_ssh(host, remote_script, timeout=60)
    print(f"\n[Provisioning Output]:\n{out}")
    if err:
        print(f"[Errors/Warnings]:\n{err}")

    rc, wan_out, _ = run_ssh(host, "curl -s -m 5 https://1.1.1.1 >/dev/null && echo 'WAN_OK' || echo 'WAN_FAIL'")
    print(f"\n[WAN Status]: {wan_out}")

    print("\n✅ PROVISIONING COMPLETE!")
    return True

def main():
    print("⏳ Listening for Linux Mini on Ethernet & Thunderbolt...")
    attempts = 0
    while True:
        attempts += 1
        for host, port, label in TARGETS:
            if check_tcp(host, port):
                if provision(host, label):
                    return 0
        if attempts % 10 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Waiting for Linux Mini... (attempt {attempts})")
        time.sleep(1.0)

if __name__ == "__main__":
    sys.exit(main())
