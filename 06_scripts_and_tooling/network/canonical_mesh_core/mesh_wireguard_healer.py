#!/usr/bin/env python3
"""
mesh_wireguard_healer.py
========================
Collaborative Multi-Node WireGuard & Tailscale Autonomous Network Healer
Lauburu Distributed AI Mesh

Coordinates all 8 compute layers to audit, revive, and optimize:
1. Tailscale WireGuard Overlay (100.64.0.0/10)
2. GL.iNet Native WireGuard Server (10.1.0.0/24 :51820)
3. Direct WireGuard Peer Pings (Port 41641 UDP)
4. Mobile ADB / Termux WireGuard Keepalives
5. Multi-Device agy Collaborative Orchestration
"""

import os
import sys
import json
import time
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Volumes/Lauburu-Monorepo")
DATA_DIR = REPO / "data/network"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATUS_JSON = DATA_DIR / "wireguard_mesh_healer_status.json"
ROUTING_LOG = REPO / "obsidian_vault/05_Hardware_Mesh/Routing_Logs/2026-09-20.md"

WIREGUARD_NODES = [
    {
        "alias": "GW_Router",
        "name": "GL.iNet BE14000 Sovereign Gateway",
        "wg_tailscale_ip": "100.103.212.34",
        "wg_native_ip": "10.1.0.1",
        "lan_ip": "192.168.8.1",
        "ssh_user": "root",
        "ssh_port": 22
    },
    {
        "alias": "L1_Mac_Host",
        "name": "Mac Mini M4 Pro Master Controller",
        "wg_tailscale_ip": "100.119.199.76",
        "lan_ip": "192.168.8.230",
        "direct_ip": "192.168.2.2",
        "ssh_user": "aaron",
        "ssh_port": 22
    },
    {
        "alias": "L2_MacBook_Pro",
        "name": "MacBook Pro M1 Max Storage Vault",
        "wg_tailscale_ip": "100.103.212.21",
        "lan_ip": "192.168.8.114",
        "ssh_user": "aaronmaher",
        "ssh_port": 22
    },
    {
        "alias": "L3_Linux_Hub",
        "name": "Linux Head Node (Ryzen 7)",
        "wg_tailscale_ip": "100.101.39.98",
        "lan_ip": "192.168.8.225",
        "ssh_user": "linux",
        "ssh_port": 22
    },
    {
        "alias": "L8_Linux_Mini",
        "name": "Linux Mini Hub (i7-8700B)",
        "wg_tailscale_ip": "100.121.247.8",
        "lan_ip": "192.168.8.238",
        "direct_ip": "192.168.2.3",
        "ssh_user": "linuxmini",
        "ssh_port": 22
    },
    {
        "alias": "L5_MacBook_Air",
        "name": "MacBook Air M4 Worker",
        "wg_tailscale_ip": "100.121.202.34",
        "lan_ip": "10.25.169.85",
        "direct_ip": "192.168.2.10",
        "ssh_user": "aaronmaher",
        "ssh_port": 22
    },
    {
        "alias": "L7_Samsung_S20",
        "name": "Samsung Galaxy S20+ Dedicated UI Tester",
        "wg_tailscale_ip": "100.78.206.96",
        "lan_ip": "192.168.8.131",
        "ssh_user": "u0_a420",
        "ssh_port": 8022,
        "adb_target": "192.168.8.131:5555"
    },
    {
        "alias": "L6_Pixel_10_Edge",
        "name": "Google Pixel 10 Pro XL",
        "wg_tailscale_ip": "100.73.38.87",
        "lan_ip": "192.168.8.213",
        "ssh_user": "u0_a363",
        "ssh_port": 8022,
        "adb_target": "100.73.38.87:5555"
    }
]

def ping_ip(ip: str, timeout_ms: int = 1500) -> tuple:
    if not ip:
        return False, None
    try:
        cmd = ["ping", "-c", "2", "-W", str(timeout_ms), ip]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        if p.returncode == 0:
            for line in p.stdout.splitlines():
                if "round-trip" in line or "rtt" in line:
                    rtt = float(line.split("=")[1].strip().split("/")[1])
                    return True, rtt
                if "time=" in line:
                    rtt = float(line.split("time=")[1].split()[0])
                    return True, rtt
            return True, 1.0
        return False, None
    except Exception:
        return False, None

def get_router_wg_status() -> dict:
    try:
        res = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes", "root@192.168.8.1", "wg show wgserver dump 2>/dev/null || true"],
            capture_output=True, text=True, timeout=5
        )
        peers = []
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 8:
                    peers.append({
                        "public_key": parts[0][:8] + "...",
                        "endpoint": parts[2],
                        "allowed_ips": parts[3],
                        "latest_handshake": int(parts[4]),
                        "rx_bytes": int(parts[5]),
                        "tx_bytes": int(parts[6])
                    })
        return {"server": "10.1.0.1:51820", "peers": peers, "healthy": len(peers) > 0}
    except Exception as e:
        return {"error": str(e), "healthy": False}

def heal_peer_wireguard(node: dict) -> list:
    actions = []
    alias = node["alias"]
    wg_ip = node["wg_tailscale_ip"]
    
    # 1. Probe WireGuard Tailscale IP
    ok, rtt = ping_ip(wg_ip)
    if ok:
        actions.append(f"WIREGUARD_ACTIVE_{alias} (RTT: {rtt:.2f}ms)")
        return actions

    # 2. If WireGuard ping failed, attempt healing via LAN fallback
    lan_ip = node.get("lan_ip") or node.get("direct_ip")
    if lan_ip:
        lan_ok, _ = ping_ip(lan_ip, timeout_ms=800)
        if lan_ok:
            actions.append(f"LAN_REACHABLE_{alias}")
            user = node.get("ssh_user", "root")
            port = str(node.get("ssh_port", 22))
            try:
                if "Linux" in node["name"]:
                    cmd = "sudo systemctl restart tailscaled 2>/dev/null || true; tailscale up --accept-routes 2>/dev/null || true"
                    subprocess.run(["ssh", "-p", port, "-o", "ConnectTimeout=3", f"{user}@{lan_ip}", cmd], timeout=6)
                    actions.append(f"RESTARTED_TAILSCALED_{alias}")
                elif "Mac" in node["name"]:
                    cmd = "/Applications/Tailscale.app/Contents/MacOS/Tailscale up --accept-routes 2>/dev/null || true"
                    subprocess.run(["ssh", "-p", port, "-o", "ConnectTimeout=3", f"{user}@{lan_ip}", cmd], timeout=6)
                    actions.append(f"KICKED_TAILSCALE_MAC_{alias}")
            except Exception as e:
                actions.append(f"SSH_HEAL_FAILED_{alias}: {e}")

    # 3. If Android, attempt ADB injection
    adb_target = node.get("adb_target")
    if adb_target:
        try:
            adb_cmd = f"adb connect {adb_target} 2>/dev/null; adb -s {adb_target} shell 'am start -n com.tailscale.ipn/.MainActivity 2>/dev/null || true'"
            subprocess.run(adb_cmd, shell=True, timeout=5)
            actions.append(f"ADB_REVIVED_TAILSCALE_{alias}")
        except Exception as e:
            actions.append(f"ADB_FAIL_{alias}: {e}")

    # 4. Shizuku rish fallback for S20 (when ADB-over-TCP fails)
    if adb_target and "S20" in alias:
        try:
            rish_cmd = (
                f"adb -s {adb_target} shell \""
                f"export RISH_DEX=/data/local/tmp/rish_shizuku.dex; "
                f"sh /data/local/tmp/rish -c 'svc wifi enable 2>/dev/null; "
                f"am start -n com.tailscale.ipn/.IPNActivity 2>/dev/null || true'\""
            )
            subprocess.run(rish_cmd, shell=True, timeout=8)
            actions.append(f"SHIZUKU_RISH_HEAL_{alias}")
        except Exception as e:
            actions.append(f"SHIZUKU_FAIL_{alias}: {e}")

    # 5. Pixel 10 USB-ADB wake through router's USB port
    if "Pixel" in alias:
        try:
            router_adb_cmd = (
                "ssh -o ConnectTimeout=3 -o BatchMode=yes root@192.168.8.1 "
                "\"adb -s 5B080DLCQ001LQ shell 'input keyevent KEYCODE_WAKEUP; "
                "am start -n com.wireguard.android/.activity.MainActivity 2>/dev/null || true'\""
            )
            subprocess.run(router_adb_cmd, shell=True, timeout=8)
            actions.append(f"ROUTER_USB_ADB_WAKE_{alias}")
        except Exception as e:
            actions.append(f"ROUTER_USB_FAIL_{alias}: {e}")

    return actions

def run_collaborative_wireguard_heal() -> dict:
    print("🚀 [Collaborative WireGuard Healer] Initiating multi-node network heal...")
    start_time = datetime.now(timezone.utc).isoformat()
    node_results = {}
    total_actions = []

    # 1. Verify host Mac Mini Tailscale state
    try:
        ts_status = subprocess.run(
            ["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        if ts_status.returncode != 0:
            print("⚠️ Tailscale local engine restarting...")
            subprocess.run(["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "up", "--accept-routes"], timeout=8)
            total_actions.append("RESTARTED_HOST_TAILSCALE")
    except Exception as e:
        total_actions.append(f"HOST_TS_ERR: {e}")

    # 2. Heal each peer in the WireGuard mesh
    online_count = 0
    for node in WIREGUARD_NODES:
        alias = node["alias"]
        wg_ip = node["wg_tailscale_ip"]
        actions = heal_peer_wireguard(node)
        total_actions.extend(actions)

        # Re-verify after healing action
        ok, rtt = ping_ip(wg_ip, timeout_ms=1200)
        if not ok and node.get("lan_ip"):
            ok_lan, rtt_lan = ping_ip(node.get("lan_ip"), timeout_ms=500)
            if ok_lan:
                node_results[alias] = {
                    "name": node["name"],
                    "wireguard_ip": wg_ip,
                    "lan_ip": node["lan_ip"],
                    "online": True,
                    "transport": "LAN/TB DMA",
                    "rtt_ms": rtt_lan
                }
                online_count += 1
                continue

        node_results[alias] = {
            "name": node["name"],
            "wireguard_ip": wg_ip,
            "lan_ip": node.get("lan_ip"),
            "online": ok,
            "transport": "WireGuard Overlay" if ok else "OFFLINE",
            "rtt_ms": rtt
        }
        if ok:
            online_count += 1

    # 3. Audit GL.iNet native WireGuard server
    wg_router = get_router_wg_status()

    report = {
        "timestamp": start_time,
        "overall_status": f"WIREGUARD_HEALTHY_{online_count}_OF_{len(WIREGUARD_NODES)}_NODES",
        "nodes": node_results,
        "router_native_wireguard": wg_router,
        "actions_taken": total_actions
    }

    # Save to status JSON
    try:
        with open(STATUS_JSON, "w") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        print(f"Could not save status json: {e}")

    # Print summary table
    print(f"\n================================================================================")
    print(f"✅ WIREGUARD COLLABORATIVE NETWORK HEAL COMPLETE ({online_count}/{len(WIREGUARD_NODES)} ONLINE)")
    print(f"================================================================================")
    for alias, data in node_results.items():
        st = "🟢 ONLINE " if data["online"] else "⚪ STANDBY"
        rtt_str = f"{data['rtt_ms']:.2f} ms" if data.get("rtt_ms") else "--"
        print(f"  {st} {data['name']:<38} [{data['transport']:<18}] WG: {data['wireguard_ip']:<15} RTT: {rtt_str}")
    print(f"================================================================================\n")

    return report

if __name__ == "__main__":
    run_collaborative_wireguard_heal()
