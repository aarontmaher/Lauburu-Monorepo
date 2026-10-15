#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wireguard_manager.py
====================
Sovereign WireGuard Mesh Profile Generator & Dual-Stack IPv6 Manager.
Bypasses carrier CGNAT by binding WireGuard client profiles directly to the
GL-BE14000 Sovereign Gateway's native Public IPv6 address: 2401:d006:c100::181.

Governed by:
- Rule #0 & #1: Zero-Mock Empirical Truth
- Rule #9: Multi-IP Fallback & Mesh Network Governance
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
PROFILES_DIR = REPO_ROOT / "06_scripts_and_tooling/network/wg_profiles"
ROUTER_HOST = "192.168.8.1"
ROUTER_USER = "root"

# Empirical hardware endpoints from WAN6 dhcpv6 status
WAN_IPV6 = "2401:d006:c100::181"
WG_PORT = 51820
ROUTER_PUBKEY = "SBY2Wf6XZho60QQ43/k+08WnqxTslo/ZJCbHa3R6Sx8="


def get_live_router_wg_config():
    """Queries active WireGuard server state on the GL-BE14000 router."""
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
        f"{ROUTER_USER}@{ROUTER_HOST}",
        "uci show wireguard_server; echo '---'; wg show wgserver; echo '---'; ubus call network.interface.wan6 status 2>/dev/null || true"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
        return res.stdout
    except Exception as e:
        return f"Error: {e}"


def generate_profiles():
    """Generates standard WireGuard client configuration profiles."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    client_matrix = [
        {"name": "l1_mac_mini_host", "ip": "10.1.0.2/32", "desc": "L1 Mac Mini M4 Pro Master Host"},
        {"name": "l6_pixel_10_pro_xl", "ip": "10.1.0.3/32", "desc": "L6 Pixel 10 Pro XL Tensor G5"},
        {"name": "l7_samsung_s20_plus", "ip": "10.1.0.4/32", "desc": "L7 Samsung Galaxy S20+ Router Control Center"},
        {"name": "l9_iphone_16_pro", "ip": "10.1.0.5/32", "desc": "L9 iPhone 16 Pro iOS Client"},
        {"name": "l5_macbook_air_m4", "ip": "10.1.0.6/32", "desc": "L5 MacBook Air M4 Worker"},
        {"name": "l8_linux_mini", "ip": "10.1.0.7/32", "desc": "L8 Linux Mini 32GB Neo Engine"}
    ]

    generated = []
    for client in client_matrix:
        conf_path = PROFILES_DIR / f"{client['name']}.conf"
        conf_content = f"""# ==============================================================================
# 🛰️ Lauburu Sovereign WireGuard Mesh Profile: {client['desc']}
# Native Public IPv6 Endpoint: [{WAN_IPV6}]:{WG_PORT} (Zero-CGNAT Bypass)
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
# ==============================================================================

[Interface]
# Replace PrivateKey with the client device's locally generated private key:
#   wg genkey > privatekey && wg pubkey < privatekey > publickey
# PrivateKey = <CLIENT_PRIVATE_KEY>
Address = {client['ip']}, fd00:9a75:96b1:cdbd::{client['ip'].split('.')[3]}/128
DNS = 10.1.0.1, 192.168.8.1

[Peer]
# Sovereign Gateway Router (GL-BE14000)
PublicKey = {ROUTER_PUBKEY}
Endpoint = [{WAN_IPV6}]:{WG_PORT}
AllowedIPs = 10.1.0.0/24, 192.168.8.0/24, fd00:9a75:96b1:cdbd::/64
PersistentKeepalive = 25
"""
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(conf_content)
        generated.append(str(conf_path))

    return generated


def main():
    print("🛰️ [WireGuard Sovereign Manager] Inspecting router and generating IPv6 profiles...")
    profiles = generate_profiles()
    print(f"✓ Generated {len(profiles)} WireGuard IPv6 client profiles in {PROFILES_DIR}:")
    for p in profiles:
        print(f"  - {os.path.basename(p)}")

    print("\n--- Live Router WireGuard Server Status ---")
    live_info = get_live_router_wg_config()
    lines = live_info.strip().split("\n")
    for line in lines[:20]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
