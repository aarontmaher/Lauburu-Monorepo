#!/usr/bin/env python3
"""
shizuku_luci_sentinel.py
========================
Continuous LuCI & WireGuard Mesh Sentinel

Monitors the GL.iNet router via SSH and the Samsung S20 Shizuku bridge,
tracking WireGuard peer handshake freshness, LuCI health, device status,
and logging all state changes to the Obsidian vault.

Run as a background daemon on L1 Mac Mini:
    python3 shizuku_luci_sentinel.py [--interval 60] [--once]
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Volumes/Lauburu-Monorepo")
VAULT = REPO / "obsidian_vault/05_Hardware_Mesh"
STATUS_JSON = REPO / "data/network/shizuku_luci_sentinel_status.json"
LOG_FILE = VAULT / "Routing_Logs" / f"{datetime.now().strftime('%Y-%m-%d')}_sentinel.md"

ROUTER_IP = "192.168.8.1"
S20_ADB = "192.168.8.131:5555"
PIXEL_SERIAL = "5B080DLCQ001LQ"

WG_PEER_MAP = {
    "peer_1": {"name": "Pixel 10 Pro XL", "ip": "10.1.0.2"},
    "peer_2": {"name": "Mac Mini M4 Pro", "ip": "10.1.0.3"},
    "peer_3": {"name": "Linux Workstation", "ip": "10.1.0.4"},
    "peer_4": {"name": "MacBook Air", "ip": "10.1.0.5"},
    "peer_5": {"name": "Samsung Galaxy S20+", "ip": "10.1.0.6"},
}


def run_cmd(cmd: str, timeout: int = 8) -> str:
    """Run a shell command and return stdout."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, Exception) as e:
        return f"ERROR: {e}"


def ssh_router(cmd: str) -> str:
    """Execute command on router via SSH."""
    return run_cmd(
        f'ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -o BatchMode=yes '
        f'root@{ROUTER_IP} "{cmd}"'
    )


def rish_s20(cmd: str) -> str:
    """Execute command on S20 via Shizuku rish."""
    return run_cmd(
        f"adb -s {S20_ADB} shell \"export RISH_DEX=/data/local/tmp/rish_shizuku.dex; "
        f"sh /data/local/tmp/rish -c '{cmd}'\"",
        timeout=12,
    )


def pixel_usb(cmd: str) -> str:
    """Execute command on Pixel via router USB ADB."""
    return ssh_router(f"adb -s {PIXEL_SERIAL} shell '{cmd}'")


def check_router_health() -> dict:
    """Audit router RAM, load, kernel stability."""
    data = {}
    
    # Uptime and load
    raw = ssh_router("cat /proc/loadavg")
    if "ERROR" not in raw:
        parts = raw.split()
        data["load_1m"] = float(parts[0]) if parts else 0
        data["load_5m"] = float(parts[1]) if len(parts) > 1 else 0
    
    # RAM
    raw = ssh_router("free -m | awk '/Mem:/{print $3,$2}'")
    if "ERROR" not in raw:
        parts = raw.split()
        if len(parts) >= 2:
            data["ram_used_mb"] = int(parts[0])
            data["ram_total_mb"] = int(parts[1])
            data["ram_pct"] = round(int(parts[0]) / int(parts[1]) * 100, 1)
    
    # SWAP
    raw = ssh_router("free -m | awk '/Swap:/{print $3,$2}'")
    if "ERROR" not in raw:
        parts = raw.split()
        if len(parts) >= 2:
            data["swap_used_mb"] = int(parts[0])
            data["swap_total_mb"] = int(parts[1])
    
    # Kernel timer migration
    raw = ssh_router("sysctl -n kernel.timer_migration 2>/dev/null")
    data["timer_migration"] = raw.strip() if "ERROR" not in raw else "unknown"
    
    # Connection tracking
    raw = ssh_router("conntrack -L 2>/dev/null | wc -l")
    data["conntrack_entries"] = int(raw) if raw.isdigit() else 0
    
    data["healthy"] = data.get("ram_pct", 100) < 90 and data.get("timer_migration") == "0"
    return data


def check_wireguard_peers() -> dict:
    """Audit WireGuard server peer handshakes."""
    peers = {}
    raw = ssh_router("wg show wgserver dump 2>/dev/null | tail -n +2")
    
    if "ERROR" in raw or not raw.strip():
        return {"error": "Cannot read WG server", "peers": {}}
    
    now = int(time.time())
    for line in raw.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        pubkey = parts[0]
        endpoint = parts[2] if len(parts) > 2 else "(none)"
        allowed_ips = parts[3] if len(parts) > 3 else ""
        handshake_ts = int(parts[4]) if len(parts) > 4 and parts[4] != "0" else 0
        rx_bytes = int(parts[5]) if len(parts) > 5 else 0
        tx_bytes = int(parts[6]) if len(parts) > 6 else 0
        
        # Find peer name from map
        name = "unknown"
        for pid, pdata in WG_PEER_MAP.items():
            ip_prefix = pdata["ip"]
            if ip_prefix in allowed_ips:
                name = pdata["name"]
                break
        
        if handshake_ts > 0:
            age_s = now - handshake_ts
            status = "active" if age_s < 180 else "stale"
        else:
            age_s = -1
            status = "dormant"
        
        peers[allowed_ips] = {
            "name": name,
            "pubkey_short": pubkey[:12] + "...",
            "endpoint": endpoint,
            "handshake_age_s": age_s,
            "status": status,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
        }
    
    return {"peers": peers, "total": len(peers)}


def check_dhcp_leases() -> list:
    """Get current DHCP leases from router."""
    raw = ssh_router("cat /tmp/dhcp.leases")
    leases = []
    if "ERROR" not in raw:
        for line in raw.strip().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                leases.append({
                    "ip": parts[2],
                    "hostname": parts[3],
                    "mac": parts[1],
                })
    return leases


def check_s20_status() -> dict:
    """Check S20 via rish."""
    data = {"reachable": False}
    
    # Check ADB connectivity
    raw = run_cmd(f"adb -s {S20_ADB} shell echo ADB_OK", timeout=5)
    if "ADB_OK" not in raw:
        return data
    
    data["reachable"] = True
    
    # Battery
    raw = run_cmd(f"adb -s {S20_ADB} shell dumpsys battery | grep level", timeout=5)
    if "level" in raw:
        try:
            data["battery"] = int(raw.split(":")[-1].strip())
        except ValueError:
            pass
    
    # Shizuku running?
    raw = run_cmd(f"adb -s {S20_ADB} shell 'ps -A | grep -c shizuku_server'", timeout=5)
    data["shizuku_running"] = raw.strip() != "0"
    
    # WG tunnel
    raw = rish_s20("ip addr show | grep 10.1.0")
    data["wg_tunnel_active"] = "10.1.0" in raw
    
    # Tailscale
    raw = rish_s20("ip addr show tun1 2>/dev/null | grep inet")
    data["tailscale_active"] = "100." in raw
    
    return data


def check_pixel_status() -> dict:
    """Check Pixel 10 via router USB ADB."""
    data = {"reachable": False}
    raw = pixel_usb("echo PIXEL_OK")
    if "PIXEL_OK" in raw:
        data["reachable"] = True
        bat_raw = pixel_usb("dumpsys battery | grep level")
        if "level" in bat_raw:
            try:
                data["battery"] = int(bat_raw.split(":")[-1].strip())
            except ValueError:
                pass
        wg_raw = pixel_usb("ip addr show | grep 10.1.0")
        data["wg_tunnel_active"] = "10.1.0" in wg_raw
    return data


def check_luci() -> dict:
    """Check LuCI web UI accessibility."""
    raw = run_cmd(
        f'curl -s -o /dev/null -w "%{{http_code}}" --connect-timeout 3 '
        f'"http://{ROUTER_IP}/cgi-bin/luci/"',
        timeout=5,
    )
    code = raw.strip()
    return {
        "http_code": code,
        "accessible": code in ("200", "302", "403"),
    }


def run_sentinel(once: bool = False, interval: int = 60):
    """Main sentinel loop."""
    iteration = 0
    while True:
        iteration += 1
        ts = datetime.now(timezone.utc).isoformat()
        print(f"\n{'='*72}")
        print(f"  SHIZUKU LUCI SENTINEL — Iteration #{iteration} @ {ts}")
        print(f"{'='*72}")
        
        report = {"timestamp": ts, "iteration": iteration}
        
        # 1. Router health
        print("\n📡 Router Health...")
        report["router"] = check_router_health()
        rh = report["router"]
        print(f"  RAM: {rh.get('ram_used_mb', '?')}MB/{rh.get('ram_total_mb', '?')}MB "
              f"({rh.get('ram_pct', '?')}%) | Load: {rh.get('load_1m', '?')} | "
              f"Timer Migration: {rh.get('timer_migration', '?')}")
        
        # 2. WireGuard peers
        print("\n🔒 WireGuard Peers...")
        report["wireguard"] = check_wireguard_peers()
        for ip, peer in report["wireguard"].get("peers", {}).items():
            icon = {"active": "🟢", "stale": "🟡", "dormant": "⚪"}.get(peer["status"], "❓")
            age_str = f"{peer['handshake_age_s']}s ago" if peer["handshake_age_s"] >= 0 else "NEVER"
            print(f"  {icon} {peer['name']:<25} {ip:<18} Handshake: {age_str}")
        
        # 3. DHCP leases
        print("\n🏠 DHCP Leases...")
        report["dhcp"] = check_dhcp_leases()
        for lease in report["dhcp"]:
            print(f"  {lease['ip']:<18} {lease['hostname']}")
        
        # 4. S20 status
        print("\n📱 Samsung S20+...")
        report["s20"] = check_s20_status()
        s = report["s20"]
        if s["reachable"]:
            print(f"  Battery: {s.get('battery', '?')}% | Shizuku: {'✅' if s.get('shizuku_running') else '❌'} | "
                  f"WG: {'✅' if s.get('wg_tunnel_active') else '❌'} | TS: {'✅' if s.get('tailscale_active') else '❌'}")
        else:
            print("  ⚪ NOT reachable via ADB")
        
        # 5. Pixel 10
        print("\n📱 Pixel 10 Pro XL (USB)...")
        report["pixel"] = check_pixel_status()
        p = report["pixel"]
        if p["reachable"]:
            print(f"  Battery: {p.get('battery', '?')}% | WG: {'✅' if p.get('wg_tunnel_active') else '❌'}")
        else:
            print("  ⚪ NOT reachable via Router USB ADB")
        
        # 6. LuCI
        print("\n🌐 LuCI Web Admin...")
        report["luci"] = check_luci()
        print(f"  HTTP {report['luci']['http_code']} — {'✅ Accessible' if report['luci']['accessible'] else '❌ Down'}")
        
        # Save report
        try:
            STATUS_JSON.parent.mkdir(parents=True, exist_ok=True)
            with open(STATUS_JSON, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            print(f"  ⚠️ Could not save status JSON: {e}")
        
        # Append to Obsidian log
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a") as f:
                active_peers = sum(
                    1 for p in report["wireguard"].get("peers", {}).values()
                    if p["status"] == "active"
                )
                total_peers = report["wireguard"].get("total", 0)
                f.write(
                    f"\n## {ts}\n"
                    f"- Router RAM: {rh.get('ram_pct', '?')}% | Load: {rh.get('load_1m', '?')}\n"
                    f"- WG Peers: {active_peers}/{total_peers} active\n"
                    f"- S20: {'🟢' if s.get('reachable') else '⚪'} | "
                    f"Pixel: {'🟢' if p.get('reachable') else '⚪'}\n"
                    f"- LuCI: HTTP {report['luci']['http_code']}\n"
                )
        except Exception as e:
            print(f"  ⚠️ Could not append to Obsidian log: {e}")
        
        print(f"\n{'='*72}")
        print(f"  Sentinel complete. Next check in {interval}s...")
        print(f"{'='*72}")
        
        if once:
            break
        
        time.sleep(interval)


if __name__ == "__main__":
    once = "--once" in sys.argv
    interval = 60
    for i, arg in enumerate(sys.argv):
        if arg == "--interval" and i + 1 < len(sys.argv):
            interval = int(sys.argv[i + 1])
    run_sentinel(once=once, interval=interval)
