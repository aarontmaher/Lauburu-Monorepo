#!/usr/bin/env python3
"""
setup_mesh_keys.py — Sovereign WireGuard Key & Configuration Generator
Generates cryptographic keypairs and configs for:
- L8 Hub Container (10.42.0.1)
- L1 Mac Mini Client (10.42.0.2)
- L6 Pixel 10 Termux (10.42.0.6)
- L6 Pixel 10 AVF Linux Terminal (10.42.0.7)
"""

import subprocess
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def gen_keypair():
    priv = subprocess.check_output(["wg", "genkey"]).decode().strip()
    pub = subprocess.check_output(["wg", "pubkey"], input=priv.encode()).decode().strip()
    psk = subprocess.check_output(["wg", "genpsk"]).decode().strip()
    return priv, pub, psk

def main():
    print("[*] Generating WireGuard Keys...")
    hub_priv, hub_pub, _ = gen_keypair()
    l1_priv, l1_pub, l1_psk = gen_keypair()
    pixel_priv, pixel_pub, pixel_psk = gen_keypair()
    avf_priv, avf_pub, avf_psk = gen_keypair()

    # Server config (for L8 WireGuard Container)
    server_conf = f"""[Interface]
Address = 10.42.0.1/24
ListenPort = 51820
PrivateKey = {hub_priv}
SaveConfig = false

# L1 Mac Mini
[Peer]
PublicKey = {l1_pub}
PresharedKey = {l1_psk}
AllowedIPs = 10.42.0.2/32

# L6 Pixel 10 Termux
[Peer]
PublicKey = {pixel_pub}
PresharedKey = {pixel_psk}
AllowedIPs = 10.42.0.6/32

# L6 Pixel 10 AVF Linux Terminal
[Peer]
PublicKey = {avf_pub}
PresharedKey = {avf_psk}
AllowedIPs = 10.42.0.7/32
"""

    # Client config for L1 Mac Mini
    # Endpoint can connect via Thunderbolt 10.0.0.8, Tailscale 100.121.247.8, or LAN 192.168.8.x
    client_l1_conf = f"""[Interface]
Address = 10.42.0.2/24
PrivateKey = {l1_priv}

[Peer]
PublicKey = {hub_pub}
PresharedKey = {l1_psk}
Endpoint = 100.121.247.8:51820
AllowedIPs = 10.42.0.0/24
PersistentKeepalive = 25
"""

    # Client config for Pixel 10 Termux
    client_pixel_conf = f"""[Interface]
Address = 10.42.0.6/24
PrivateKey = {pixel_priv}

[Peer]
PublicKey = {hub_pub}
PresharedKey = {pixel_psk}
Endpoint = 100.121.247.8:51820
AllowedIPs = 10.42.0.0/24
PersistentKeepalive = 25
"""

    # Client config for Pixel 10 AVF Linux Terminal
    client_avf_conf = f"""[Interface]
Address = 10.42.0.7/24
PrivateKey = {avf_priv}

[Peer]
PublicKey = {hub_pub}
PresharedKey = {avf_psk}
Endpoint = 100.121.247.8:51820
AllowedIPs = 10.42.0.0/24
PersistentKeepalive = 25
"""

    (CONFIG_DIR / "wg0.conf").write_text(server_conf)
    (CONFIG_DIR / "l1_mac.conf").write_text(client_l1_conf)
    (CONFIG_DIR / "pixel10_termux.conf").write_text(client_pixel_conf)
    (CONFIG_DIR / "pixel10_avf.conf").write_text(client_avf_conf)

    # Copy user's public key for container SSH
    id_pub = Path.home() / ".ssh" / "id_ed25519.pub"
    if id_pub.exists():
        (CONFIG_DIR / "authorized_keys").write_text(id_pub.read_text())

    print(f"[✓] Configurations generated successfully in {CONFIG_DIR}:")
    print("    - wg0.conf (Server Hub: 10.42.0.1)")
    print("    - l1_mac.conf (Mac Mini Client: 10.42.0.2)")
    print("    - pixel10_termux.conf (Pixel 10 Termux Client: 10.42.0.6)")
    print("    - pixel10_avf.conf (Pixel 10 AVF Client: 10.42.0.7)")

if __name__ == "__main__":
    main()
