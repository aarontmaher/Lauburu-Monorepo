#!/usr/bin/env python3
"""
06_scripts_and_tooling/network/configure_mesh_router_topology.py
================================================================
Canonical Router & Subnet Configuration Governor for the Lauburu Mesh Ecosystem.
Manages OpenWrt GL.iNet (192.168.8.1) static DHCP leases, TP-Link VX230v AP settings,
multi-WAN carrier status, and zero-mock physical mesh connectivity.
"""

import os
import sys
import json
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

ROUTER_IP = "192.168.8.1"
ROUTER_USER = "root"

# Canonical Mesh Node Matrix
CANONICAL_STATIC_LEASES = [
    {
        "id": "mac_mini_eth",
        "name": "aarons-mac-mini-eth",
        "mac": "1c:f6:4c:7d:d7:0a",
        "ip": "192.168.8.230",
        "layer": "L1",
        "role": "Mac Mini M4 Pro Host & Governor"
    },
    {
        "id": "mac_mini_wifi",
        "name": "aarons-mac-mini-wifi",
        "mac": "1c:f6:4c:7c:dc:5f",
        "ip": "192.168.8.155",
        "layer": "L1-Alt",
        "role": "Mac Mini Wi-Fi Interface"
    },
    {
        "id": "macbook_pro",
        "name": "aarons-macbook-pro",
        "mac": "36:7e:4d:07:b2:c0",
        "ip": "192.168.8.127",
        "layer": "L2",
        "role": "MacBook Pro M4 Metal GPU & Storage Vault"
    },
    {
        "id": "linux_head_node",
        "name": "linux-head-node",
        "mac": "00:e0:4c:68:03:c8",
        "ip": "192.168.8.224",
        "layer": "L3",
        "role": "Linux Head Node Compute Hub"
    },
    {
        "id": "linux_head_node_wol",
        "name": "linux-head-node-wol",
        "mac": "00:41:0e:14:28:43",
        "ip": "192.168.8.225",
        "layer": "L3-WOL",
        "role": "Linux Head Node Wake-on-LAN MAC"
    },
    {
        "id": "macbook_air",
        "name": "aarons-macbook-air",
        "mac": "66:74:75:d8:16:fb",
        "ip": "192.168.8.222",
        "layer": "L5",
        "role": "MacBook Air M4 Manual AI & UI/UX Specialist"
    },
    {
        "id": "pixel_10_pro",
        "name": "pixel-10-pro-xl",
        "mac": "66:00:88:ca:e8:3b",
        "ip": "192.168.8.145",
        "layer": "L6",
        "role": "Pixel 10 Pro XL Vision & Edge TPU"
    },
    {
        "id": "samsung_s20",
        "name": "samsung-s20",
        "mac": "0a:8f:1b:f1:c8:17",
        "ip": "192.168.8.214",
        "layer": "L7",
        "role": "Samsung S20 Automated UI/UX Tester"
    },
    {
        "id": "pixel_10_pro_xl_eth",
        "name": "l6-pixel-10-pro-xl-usb-eth",
        "mac": "98:fc:84:e6:e2:12",
        "ip": "192.168.8.176",
        "layer": "L6",
        "role": "Pixel 10 Pro XL Wired USB-C Gigabit Ethernet"
    }
]


def run_ssh_router(cmd: str) -> subprocess.CompletedProcess:
    """Execute command on GL.iNet OpenWrt router via SSH with timeout & error trapping."""
    full_cmd = [
        "ssh",
        "-o", "ConnectTimeout=3",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        f"{ROUTER_USER}@{ROUTER_IP}",
        cmd
    ]
    try:
        return subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
    except Exception as e:
        return subprocess.CompletedProcess(args=full_cmd, returncode=255, stdout="", stderr=str(e))


def sync_static_dhcp_leases() -> bool:
    """Idempotently configure deduplicated static DHCP leases on GL.iNet router."""
    print("🔄 Synchronizing Static DHCP Leases on GL.iNet OpenWrt...")
    uci_commands = [
        "while uci -q delete dhcp.@host[0]; do :; done"
    ]
    seen_ips = set()
    seen_macs = set()
    for lease in CANONICAL_STATIC_LEASES:
        lid = lease["id"]
        ip = lease["ip"].strip()
        mac = lease["mac"].strip().lower()
        if ip in seen_ips or mac in seen_macs:
            continue
        seen_ips.add(ip)
        seen_macs.add(mac)
        uci_commands.append(f"uci -q delete dhcp.{lid}")
        uci_commands.append(f"uci set dhcp.{lid}=host")
        uci_commands.append(f"uci set dhcp.{lid}.name='{lease['name']}'")
        uci_commands.append(f"uci set dhcp.{lid}.mac='{mac}'")
        uci_commands.append(f"uci set dhcp.{lid}.ip='{ip}'")
    
    uci_commands.append("uci set firewall.@defaults[0].flow_offloading_hw='0'")
    uci_commands.append("uci set firewall.@defaults[0].flow_offloading='0'")
    uci_commands.append("uci commit dhcp")
    uci_commands.append("uci commit firewall")
    uci_commands.append("echo 0 > /sys/kernel/debug/hnat/hook_toggle 2>/dev/null || true")
    uci_commands.append("/etc/init.d/dnsmasq restart")
    
    script = "\n".join(uci_commands)
    res = run_ssh_router(script)
    if res.returncode == 0:
        print("✔ Static DHCP leases successfully applied and dnsmasq reloaded.")
        return True
    else:
        print(f"❌ Failed to apply DHCP leases: {res.stderr}")
        return False


def get_live_router_dhcp_leases() -> Dict[str, str]:
    """Fetch live DHCP leases from router to map MAC addresses and hostnames to real dynamic IPs."""
    res = run_ssh_router("cat /tmp/dhcp.leases 2>/dev/null")
    leases = {}
    if res.returncode == 0:
        for line in res.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                mac, ip, name = parts[1].lower(), parts[2], parts[3].lower()
                leases[mac] = ip
                leases[name] = ip
    return leases


def ping_ip(ip: str, timeout_ms: int = 500) -> Tuple[bool, Optional[float]]:
    """Empirical sub-second ping probe."""
    ping_bin = shutil.which("ping") or "/sbin/ping"
    try:
        p = subprocess.run([ping_bin, "-c", "2", "-W", str(timeout_ms), ip], capture_output=True, text=True, timeout=4)
        if p.returncode == 0:
            for line in p.stdout.splitlines():
                if "round-trip" in line or "rtt" in line:
                    try:
                        return True, float(line.split("=")[1].strip().split("/")[1])
                    except Exception:
                        pass
            for line in p.stdout.splitlines():
                if "time=" in line:
                    try:
                        return True, float(line.split("time=")[1].split()[0])
                    except Exception:
                        return True, 1.0
        return False, None
    except Exception:
        return False, None


def verify_mesh_connectivity() -> Dict[str, Any]:
    """Multi-transport empirical mesh connectivity probe (TB4 40Gbps -> LAN Static -> LAN Dynamic -> Tailscale)."""
    print("\n📡 Probing 7-Layer Physical & Multi-Transport Mesh Connectivity...")
    live_leases = get_live_router_dhcp_leases()
    results = {}
    
    mesh_nodes = [
        {
            "name": "GL.iNet Gateway (GW)",
            "layer": "GW",
            "candidates": [("LAN Gateway", "192.168.8.1"), ("Tailscale", "100.70.123.123"), ("Tailscale Alt", "100.103.212.34")],
            "mac": "94:83:c4:eb:e7:31"
        },
        {
            "name": "Mac Mini Host (L1)",
            "layer": "L1",
            "candidates": [("TB4 Bridge", "10.0.0.2"), ("LAN Wi-Fi", "192.168.8.143"), ("LAN Static (Eth)", "192.168.8.230"), ("Tailscale", "100.119.199.76"), ("Localhost", "127.0.0.1")],
            "mac": "1c:f6:4c:7d:d7:0a"
        },
        {
            "name": "Mac Mini M2 Pro (L1b)",
            "layer": "L1b",
            "candidates": [("TB3/TB4 Bridge", "10.0.0.3"), ("LAN Dynamic", live_leases.get("00:c5:85:05:6d:2c", "192.168.8.114")), ("Tailscale", "100.104.128.34")],
            "mac": "00:c5:85:05:6d:2c"
        },
        {
            "name": "MacBook Pro (L2)",
            "layer": "L2",
            "candidates": [("TB3/TB4 Bridge", "10.0.0.4"), ("LAN Static", "192.168.8.127"), ("LAN Dynamic", live_leases.get("a4:83:e7:d1:7c:82", "192.168.8.128")), ("Tailscale", "100.103.212.21")],
            "mac": "a4:83:e7:d1:7c:82"
        },
        {
            "name": "Linux Head Node (L3)",
            "layer": "L3",
            "candidates": [("LAN Dynamic", live_leases.get("00:41:0e:14:28:43", "192.168.8.225")), ("LAN Static", "192.168.8.225"), ("LAN Alt", "192.168.8.224"), ("Tailscale", "100.101.39.98")],
            "mac": "00:41:0e:14:28:43"
        },
        {
            "name": "Linux Mini Hub (L8)",
            "layer": "L8",
            "candidates": [("TB3/TB4 Bridge", "10.0.0.8"), ("LAN Static", "192.168.8.242"), ("LAN Dynamic", live_leases.get("3c:cd:36:68:29:e8", "192.168.8.242")), ("Tailscale", "100.121.247.8")],
            "mac": "3c:cd:36:68:29:e8"
        },
        {
            "name": "MacBook Air (L5)",
            "layer": "L5",
            "candidates": [("TB4 Bridge", "10.0.0.5"), ("LAN Dynamic", live_leases.get("6a:71:33:fe:61:29", "192.168.8.248")), ("LAN Alt", live_leases.get("66:74:75:d8:16:fb", "192.168.8.222")), ("Tailscale", "100.121.202.34")],
            "mac": "6a:71:33:fe:61:29"
        },
        {
            "name": "Pixel 10 Pro XL (L6)",
            "layer": "L6",
            "candidates": [("Wired USB-C Eth", "192.168.8.176"), ("LAN Dynamic", live_leases.get("26:cc:79:f2:90:76", live_leases.get("pixel-10-pro-xl", "192.168.8.213"))), ("LAN Static", "192.168.8.213"), ("Tailscale", "100.114.215.68")],
            "mac": "26:cc:79:f2:90:76"
        },
        {
            "name": "Samsung S20 (L7)",
            "layer": "L7",
            "candidates": [("LAN Dynamic", live_leases.get("c2:f8:c0:36:de:29", live_leases.get("galaxy-s20-5g", "192.168.8.101"))), ("LAN Static", "192.168.8.101"), ("LAN Alt", "192.168.8.130"), ("Tailscale", "100.78.206.96")],
            "mac": "c2:f8:c0:36:de:29"
        }
    ]
    
    for node in mesh_nodes:
        name = node["name"]
        active_ip = None
        active_path = None
        min_rtt = None
        is_online = False
        
        for path_label, ip in node["candidates"]:
            if not ip:
                continue
            t_ms = 1200 if ("Tailscale" in path_label or "Pixel" in name) else 500
            ok, rtt = ping_ip(ip, timeout_ms=t_ms)
            if ok:
                is_online = True
                active_ip = ip
                active_path = path_label
                min_rtt = rtt
                break
                
        results[name] = {
            "name": name,
            "layer": node["layer"],
            "online": is_online,
            "active_ip": active_ip,
            "active_path": active_path,
            "rtt_ms": min_rtt,
            "status": "🟢 ONLINE" if is_online else "⚪ STANDBY"
        }
        
        if is_online:
            rtt_str = f"{min_rtt:.2f} ms" if min_rtt is not None else "--"
            print(f"  🟢 ONLINE  {name:<26} ({active_path}: {active_ip:<15}) RTT: {rtt_str}")
        else:
            print(f"  ⚪ STANDBY {name:<26} (No active response across candidate IPs)")
            
    return results


def main():
    print("================================================================================")
    print("🌐  LAUBURU MESH — CANONICAL ROUTER & TOPOLOGY CONFIGURATOR")
    print("================================================================================")
    
    dhcp_ok = sync_static_dhcp_leases()
    mesh_status = verify_mesh_connectivity()
    
    online_count = sum(1 for v in mesh_status.values() if v["online"])
    print("\n================================================================================")
    print(f"✔ Router Sync Complete: {online_count}/{len(mesh_status)} Nodes Active on 192.168.8.0/24 Subnet")
    print("================================================================================")


if __name__ == "__main__":
    main()
