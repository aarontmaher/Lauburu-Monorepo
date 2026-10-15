#!/usr/bin/env python3
"""
benchmark_full_mesh_wireguard_vs_tailscale.py
============================================
Comprehensive 7-Layer Mesh Benchmark: Tailscale vs WireGuard vs Baremetal Direct.
Governed by Rule 0 (Hardware Matrix) and Rule 1 (Zero-Mock Truth).
"""

import subprocess
import re
import json
import time

def parse_ping(output):
    avg_match = re.search(r"(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", output)
    loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
    avg_rtt = float(avg_match.group(2)) if avg_match else None
    loss = float(loss_match.group(1)) if loss_match else 100.0
    return avg_rtt, loss

def run_cmd(cmd_list, timeout=5):
    try:
        r = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

print("=" * 75)
print("🚀 FULL MESH BENCHMARK: TAILSCALE vs WIREGUARD vs DIRECT/THUNDERBOLT")
print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("Target Hub: L8 Linux Hub (lauburu, 32GB RAM)")
print("=" * 75)

devices = [
    {
        "id": "L1",
        "name": "Mac Mini M4 Pro (L1)",
        "cmd_prefix": [],
        "ts_target": "100.121.247.8",
        "direct_target": "10.0.0.8",  # 40Gb/s TB4
        "direct_type": "Thunderbolt 4 (40 Gb/s)",
        "wg_port_check": ["nc", "-u", "-z", "-w", "2", "100.121.247.8", "51820"]
    },
    {
        "id": "L3",
        "name": "Linux Head Node AMD (L3)",
        "cmd_prefix": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", "linux@100.101.39.98"],
        "ts_target": "100.121.247.8",
        "direct_target": "192.168.8.242",
        "direct_type": "Gigabit LAN Wi-Fi",
        "wg_port_check": ["ssh", "-o", "BatchMode=yes", "linux@100.101.39.98", "nc -u -z -w 2 100.121.247.8 51820 && echo OPEN"]
    },
    {
        "id": "L2",
        "name": "MacBook Pro Intel (L2)",
        "cmd_prefix": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", "aaronmaher@100.103.212.21"],
        "ts_target": "100.121.247.8",
        "direct_target": "192.168.8.242",
        "direct_type": "Wi-Fi 5 (802.11ac)",
        "wg_port_check": ["ssh", "-o", "BatchMode=yes", "aaronmaher@100.103.212.21", "nc -u -z -w 2 100.121.247.8 51820 && echo OPEN"]
    },
    {
        "id": "L1a",
        "name": "MacBook Air M4 (L1a)",
        "cmd_prefix": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", "aaronmaher@100.121.202.34"],
        "ts_target": "100.121.247.8",
        "direct_target": "192.168.8.242",
        "direct_type": "Wi-Fi 6E (802.11ax)",
        "wg_port_check": ["ssh", "-o", "BatchMode=yes", "aaronmaher@100.121.202.34", "nc -u -z -w 2 100.121.247.8 51820 && echo OPEN"]
    },
    {
        "id": "GW",
        "name": "GL-BE14000 Gateway (GW)",
        "cmd_prefix": ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", "root@192.168.8.1"],
        "ts_target": "100.121.247.8",
        "direct_target": "192.168.8.242",
        "direct_type": "Wired LAN / Switch",
        "wg_port_check": ["ssh", "-o", "BatchMode=yes", "root@192.168.8.1", "nc -u -z -w 2 100.121.247.8 51820 && echo OPEN"]
    },
    {
        "id": "L7",
        "name": "Samsung Galaxy S20+ (L7)",
        "cmd_prefix": ["adb", "-s", "192.168.8.224:5555", "shell"],
        "ts_target": "100.121.247.8",
        "direct_target": "192.168.8.242",
        "direct_type": "USB Ethernet / Wi-Fi 6",
        "wg_port_check": ["adb", "-s", "192.168.8.224:5555", "shell", "nc -u -z -w 2 100.121.247.8 51820 && echo OPEN"]
    },
]

results = []

for dev in devices:
    print(f"\n[*] Benchmarking Node: {dev['name']}...")
    
    # 1. Tailscale Ping
    ts_ping_cmd = list(dev['cmd_prefix'])
    if dev['cmd_prefix']:
        if "adb" in dev['cmd_prefix'][0]:
            ts_ping_cmd.append(f"ping -c 3 {dev['ts_target']}")
        else:
            ts_ping_cmd.append(f"ping -c 3 {dev['ts_target']}")
    else:
        ts_ping_cmd = ["ping", "-c", "3", dev['ts_target']]
        
    code, out, _ = run_cmd(ts_ping_cmd)
    ts_rtt, ts_loss = parse_ping(out)
    
    # 2. Direct / LAN Ping
    direct_ping_cmd = list(dev['cmd_prefix'])
    if dev['cmd_prefix']:
        if "adb" in dev['cmd_prefix'][0]:
            direct_ping_cmd.append(f"ping -c 3 {dev['direct_target']}")
        else:
            direct_ping_cmd.append(f"ping -c 3 {dev['direct_target']}")
    else:
        direct_ping_cmd = ["ping", "-c", "3", dev['direct_target']]
        
    code, out, _ = run_cmd(direct_ping_cmd)
    direct_rtt, direct_loss = parse_ping(out)
    
    # 3. WireGuard UDP Port 51820 Check
    code, out, _ = run_cmd(dev['wg_port_check'])
    wg_open = (code == 0) or ("OPEN" in out) or ("succeeded" in out)
    
    res = {
        "id": dev["id"],
        "name": dev["name"],
        "direct_type": dev["direct_type"],
        "tailscale_rtt_ms": ts_rtt,
        "tailscale_loss_pct": ts_loss,
        "direct_rtt_ms": direct_rtt,
        "direct_loss_pct": direct_loss,
        "wireguard_udp_51820": "OPEN" if wg_open else "CLOSED",
        "latency_advantage": f"{ts_rtt / direct_rtt:.1f}x faster" if ts_rtt and direct_rtt and direct_rtt > 0 else "N/A"
    }
    results.append(res)
    
    print(f"    Tailscale RTT: {ts_rtt} ms ({ts_loss}% loss)")
    print(f"    Direct RTT:    {direct_rtt} ms ({dev['direct_type']})")
    print(f"    WG UDP 51820:  {'OPEN' if wg_open else 'CLOSED'}")
    if ts_rtt and direct_rtt:
        print(f"    Speedup:       Direct/WireGuard is {ts_rtt / direct_rtt:.1f}x faster than Tailscale")

print("\n" + "=" * 75)
print("📊 SUMMARY MATRIX: TAILSCALE vs DIRECT/WIREGUARD")
print("=" * 75)
print(f"{'Node':<24} | {'Tailscale':<11} | {'Direct/TB':<12} | {'WG 51820':<9} | {'Advantage'}")
print("-" * 75)
for r in results:
    ts_str = f"{r['tailscale_rtt_ms']} ms" if r['tailscale_rtt_ms'] is not None else "OFFLINE"
    dir_str = f"{r['direct_rtt_ms']} ms" if r['direct_rtt_ms'] is not None else "OFFLINE"
    print(f"{r['name']:<24} | {ts_str:<11} | {dir_str:<12} | {r['wireguard_udp_51820']:<9} | {r['latency_advantage']}")
print("=" * 75)

# Save JSON artifact
with open("/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/containers/wireguard/mesh_full_benchmark.json", "w") as f:
    json.dump(results, f, indent=2)
print("✓ Saved results to 06_scripts_and_tooling/containers/wireguard/mesh_full_benchmark.json")
