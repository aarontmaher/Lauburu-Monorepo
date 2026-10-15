#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Screen Lens Sovereign — Real-Time Network & Hardware Health Terminal
================================================================================
Dedicated full-screen terminal TUI for headless Linux mesh nodes (L8, L3, etc.).
Runs persistently on DISPLAY=:99 inside xterm as the default screen display.

Governed by:
- Rule #0: Zero-Mock Empirical Truth (all metrics from /proc, kernel syscalls, authentic pings)
- Rule #1: Symmetrical Self-Auditing & Tri-Proof Verification Gate
- Rule #3: Host Sanctuary & Dynamic RAM Governance Invariant
- Rule #9: App-Wide Compact Output & Mesh Network Fallback
- Rule #10: Fundamental Baseline Trinity & Linux Mini First-Offload
================================================================================
"""

import os
import sys
import re
import time
import socket
import select
import datetime
import argparse
import threading
import subprocess
from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------------------------
# ANSI Color Codes & Styles
# ---------------------------------------------------------------------------
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_CYAN    = "\033[36m"
C_BCYAN   = "\033[1;36m"
C_GREEN   = "\033[32m"
C_BGREEN  = "\033[1;32m"
C_YELLOW  = "\033[33m"
C_BYELLOW = "\033[1;33m"
C_RED     = "\033[31m"
C_BRED    = "\033[1;31m"
C_WHITE   = "\033[37m"
C_BWHITE  = "\033[1;37m"
C_MAGENTA = "\033[35m"
C_BMAGENTA= "\033[1;35m"
C_BLUE    = "\033[34m"
C_BBLUE   = "\033[1;34m"
C_GRAY    = "\033[90m"

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def visible_len(s: str) -> int:
    """Calculates visible character length excluding ANSI escape sequences."""
    return len(ANSI_RE.sub('', s))

def pad_box_row(content: str, width: int) -> str:
    """Pads row content so the right border │ aligns exactly at column width."""
    vlen = visible_len(content)
    if vlen < width:
        return content + " " * (width - vlen)
    return content

# ---------------------------------------------------------------------------
# Mesh Target Definitions
# ---------------------------------------------------------------------------
PEER_TARGETS = [
    {
        "id": "L1",
        "name": "Mac Mini M4 Pro Host",
        "role": "Master Local Orchestrator",
        "ips": [("10.0.0.2", "TB4 DMA"), ("192.168.8.143", "Wi-Fi LAN"), ("192.168.8.230", "Eth LAN"), ("100.119.199.76", "Tailscale")],
        "ports": [22, 4003, 8082],
    },
    {
        "id": "GW",
        "name": "GL-BE14000 Router",
        "role": "Core Gateway & 2.5G NBN",
        "ips": [("192.168.8.1", "LAN Gateway"), ("100.70.123.123", "Tailscale")],
        "ports": [22, 53],
    },
    {
        "id": "WAN",
        "name": "WAN Uplink (DNS Path)",
        "role": "Internet DNS / Primary Gate",
        "ips": [("1.1.1.1", "Cloudflare DNS"), ("8.8.8.8", "Google DNS")],
        "ports": [53],
    },
    {
        "id": "L8",
        "name": "Linux Mini Central Hub",
        "role": "Central Ingress / Ray Head",
        "ips": [("10.0.0.8", "TB4 DMA"), ("192.168.8.242", "LAN Eth"), ("100.121.247.8", "Tailscale")],
        "ports": [22, 61208],
    },
    {
        "id": "L3",
        "name": "Linux Head Node",
        "role": "AMD Ryzen 5700U Compute",
        "ips": [("192.168.8.225", "LAN Wi-Fi"), ("100.101.39.98", "Tailscale")],
        "ports": [22, 61208],
    },
    {
        "id": "L2",
        "name": "MacBook Pro Vault",
        "role": "Intel Model Vault / MPS",
        "ips": [("10.0.0.4", "TB4 DMA"), ("192.168.8.127", "LAN Wi-Fi"), ("100.103.212.21", "Tailscale")],
        "ports": [22, 61208],
    },
    {
        "id": "L1b",
        "name": "Mac Mini M2 Pro",
        "role": "TB Ring Secondary",
        "ips": [("10.0.0.3", "TB4 DMA"), ("192.168.8.114", "LAN Wi-Fi"), ("100.104.128.34", "Tailscale")],
        "ports": [22],
    },
    {
        "id": "L6",
        "name": "Pixel 10 Pro XL",
        "role": "Tensor G5 Edge TPU",
        "ips": [("192.168.8.213", "LAN Wi-Fi 7"), ("100.114.215.68", "Tailscale")],
        "ports": [8022, 5555],
    },
    {
        "id": "L7",
        "name": "Galaxy S20+",
        "role": "Exynos UI Tester",
        "ips": [("192.168.8.157", "LAN Wi-Fi"), ("100.84.40.95", "Tailscale")],
        "ports": [5555],
    },
]

# ---------------------------------------------------------------------------
# Background Non-Blocking Ping Worker
# ---------------------------------------------------------------------------
_ping_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()

def _tcp_ping(host: str, port: int, timeout: float = 0.35) -> Tuple[bool, float]:
    """Measures TCP connect RTT in milliseconds."""
    t0 = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            err = s.connect_ex((host, port))
            dt = (time.perf_counter() - t0) * 1000.0
            return (err == 0, round(dt, 2))
    except Exception:
        return (False, 0.0)

def _icmp_ping(host: str, timeout_sec: float = 0.4) -> Tuple[bool, float]:
    """Executes single ICMP ping with millisecond RTT extraction."""
    try:
        t0 = time.perf_counter()
        res = subprocess.run(
            ["ping", "-c", "1", "-W", str(int(timeout_sec)), host],
            capture_output=True, text=True, timeout=timeout_sec + 0.2
        )
        dt = (time.perf_counter() - t0) * 1000.0
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "time=" in line:
                    try:
                        part = line.split("time=")[1].split()[0]
                        return (True, round(float(part), 2))
                    except Exception:
                        pass
            return (True, round(dt, 2))
    except Exception:
        pass
    return (False, 0.0)

def _get_local_ip_list() -> List[str]:
    """Harvests all local IPv4 addresses assigned to interfaces."""
    ips = ["127.0.0.1"]
    try:
        out = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True, timeout=1.0)
        if out.returncode == 0:
            for line in out.stdout.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    ip_part = line.split()[1].split("/")[0]
                    ips.append(ip_part)
    except Exception:
        pass
    return ips

def _ping_target(target: Dict[str, Any], local_ips: List[str]) -> Dict[str, Any]:
    """Tests connectivity to target using ICMP first, falling back to TCP."""
    res = {
        "id": target["id"],
        "name": target["name"],
        "role": target["role"],
        "status": "OFFLINE",
        "active_ip": "--",
        "transport": "--",
        "rtt_ms": 0.0,
        "last_seen": "--",
    }
    
    # Check if self
    for ip, _ in target["ips"]:
        if ip in local_ips:
            res["status"] = "LOCAL"
            res["active_ip"] = ip
            res["transport"] = "Internal Loopback"
            res["rtt_ms"] = 0.05
            res["last_seen"] = "Self"
            return res

    for ip, trans in target["ips"]:
        ok, rtt = _icmp_ping(ip, timeout_sec=0.35)
        if ok:
            res["status"] = "ONLINE"
            res["active_ip"] = ip
            res["transport"] = trans
            res["rtt_ms"] = rtt
            res["last_seen"] = time.strftime("%H:%M:%S")
            return res
        
        for port in target.get("ports", [22]):
            ok_tcp, rtt_tcp = _tcp_ping(ip, port, timeout=0.3)
            if ok_tcp:
                res["status"] = "ONLINE"
                res["active_ip"] = ip
                res["transport"] = f"{trans} (:{port})"
                res["rtt_ms"] = rtt_tcp
                res["last_seen"] = time.strftime("%H:%M:%S")
                return res

    return res

def _ping_worker_loop():
    """Perpetually updates target reachability cache in the background."""
    while True:
        local_ips = _get_local_ip_list()
        for target in PEER_TARGETS:
            probe = _ping_target(target, local_ips)
            with _cache_lock:
                _ping_cache[target["id"]] = probe
            time.sleep(0.04)
        time.sleep(0.8)

# ---------------------------------------------------------------------------
# Zero-Mock Hardware & Network Metric Harvesters
# ---------------------------------------------------------------------------
_prev_net_io: Dict[str, Tuple[int, int, float]] = {}

def harvest_network_interfaces() -> List[Dict[str, Any]]:
    """Harvests authentic network interface throughput & status from /proc/net/dev."""
    global _prev_net_io
    now = time.time()
    interfaces = []
    
    ip_map: Dict[str, str] = {}
    try:
        out = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True, timeout=1.0)
        if out.returncode == 0:
            current_dev = ""
            for line in out.stdout.splitlines():
                if line and not line.startswith(" "):
                    parts = line.split(":")
                    if len(parts) >= 2:
                        current_dev = parts[1].strip()
                elif "inet " in line and current_dev:
                    ip_map[current_dev] = line.strip().split()[1]
    except Exception:
        pass

    try:
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()
        for line in lines[2:]:
            if ":" not in line:
                continue
            name, data = line.split(":", 1)
            name = name.strip()
            # Filter out lo, veth, and auto-generated docker bridges for clean display
            if name == "lo" or name.startswith("veth") or name.startswith("br-"):
                continue

            fields = data.split()
            rx_bytes = int(fields[0])
            tx_bytes = int(fields[8])
            rx_errs = int(fields[2])
            tx_errs = int(fields[10])

            rx_rate_kb = 0.0
            tx_rate_kb = 0.0
            if name in _prev_net_io:
                prev_rx, prev_tx, prev_t = _prev_net_io[name]
                dt = max(0.1, now - prev_t)
                rx_rate_kb = max(0.0, (rx_bytes - prev_rx) / (1024.0 * dt))
                tx_rate_kb = max(0.0, (tx_bytes - prev_tx) / (1024.0 * dt))
            
            _prev_net_io[name] = (rx_bytes, tx_bytes, now)

            state = "DOWN"
            oper_path = f"/sys/class/net/{name}/operstate"
            if os.path.exists(oper_path):
                try:
                    with open(oper_path, "r") as sf:
                        state = sf.read().strip().upper()
                except Exception:
                    pass
            elif rx_bytes > 0:
                state = "UP"

            ip_str = ip_map.get(name, "--")
            interfaces.append({
                "name": name,
                "ip": ip_str,
                "state": state,
                "rx_rate_kb": rx_rate_kb,
                "tx_rate_kb": tx_rate_kb,
                "rx_total_mb": round(rx_bytes / (1024.0 * 1024.0), 1),
                "tx_total_mb": round(tx_bytes / (1024.0 * 1024.0), 1),
                "errors": rx_errs + tx_errs,
            })
    except Exception:
        pass

    def _iface_key(item):
        n = item["name"]
        if "thunderbolt" in n or "tb" in n: return 0
        if "enp" in n or "eth" in n: return 1
        if "wlp" in n or "wlan" in n: return 2
        if "tailscale" in n: return 3
        if "wg" in n: return 4
        if "docker" in n: return 5
        return 6

    interfaces.sort(key=_iface_key)
    return interfaces

def harvest_system_telemetry() -> Dict[str, Any]:
    """Gathers CPU, RAM, Disk, Thermal, and Uptime from Linux kernel."""
    telemetry = {
        "hostname": socket.gethostname(),
        "kernel": os.uname().release,
        "arch": os.uname().machine,
        "cpu_model": "Unknown CPU",
        "cpu_cores": os.cpu_count() or 1,
        "loadavg": "0.00, 0.00, 0.00",
        "uptime_str": "--",
        "thermal_c": "--",
        "ram_total_gb": 0.0,
        "ram_free_gb": 0.0,
        "ram_avail_gb": 0.0,
        "ram_used_gb": 0.0,
        "ram_used_pct": 0.0,
        "swap_total_gb": 0.0,
        "swap_used_gb": 0.0,
        "swap_used_pct": 0.0,
        "disk_total_gb": 0.0,
        "disk_free_gb": 0.0,
        "disk_used_pct": 0.0,
    }

    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    telemetry["cpu_model"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    try:
        load = os.getloadavg()
        telemetry["loadavg"] = f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
    except Exception:
        pass

    try:
        with open("/proc/uptime", "r") as f:
            up_sec = float(f.read().split()[0])
            days = int(up_sec // 86400)
            hours = int((up_sec % 86400) // 3600)
            mins = int((up_sec % 3600) // 60)
            telemetry["uptime_str"] = f"{days}d {hours}h {mins}m"
    except Exception:
        pass

    for zone in ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"]:
        if os.path.exists(zone):
            try:
                with open(zone, "r") as f:
                    temp_raw = f.read().strip()
                    if temp_raw.isdigit():
                        telemetry["thermal_c"] = f"{round(int(temp_raw) / 1000.0, 1)}°C"
                        break
            except Exception:
                pass

    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    if val.isdigit():
                        mem[k] = int(val) * 1024

        total = mem.get("MemTotal", 0)
        free = mem.get("MemFree", 0)
        avail = mem.get("MemAvailable", free)
        used = total - avail
        telemetry["ram_total_gb"] = round(total / (1024**3), 2)
        telemetry["ram_free_gb"] = round(free / (1024**3), 2)
        telemetry["ram_avail_gb"] = round(avail / (1024**3), 2)
        telemetry["ram_used_gb"] = round(used / (1024**3), 2)
        if total > 0:
            telemetry["ram_used_pct"] = round((used / total) * 100.0, 1)

        sw_total = mem.get("SwapTotal", 0)
        sw_free = mem.get("SwapFree", 0)
        sw_used = sw_total - sw_free
        telemetry["swap_total_gb"] = round(sw_total / (1024**3), 2)
        telemetry["swap_used_gb"] = round(sw_used / (1024**3), 2)
        if sw_total > 0:
            telemetry["swap_used_pct"] = round((sw_used / sw_total) * 100.0, 1)
    except Exception:
        pass

    try:
        st = os.statvfs("/")
        total_d = st.f_blocks * st.f_frsize
        free_d = st.f_bavail * st.f_frsize
        used_d = total_d - free_d
        telemetry["disk_total_gb"] = round(total_d / (1024**3), 1)
        telemetry["disk_free_gb"] = round(free_d / (1024**3), 1)
        if total_d > 0:
            telemetry["disk_used_pct"] = round((used_d / total_d) * 100.0, 1)
    except Exception:
        pass

    return telemetry

def harvest_active_daemons() -> List[Dict[str, Any]]:
    """Checks key mesh daemons and services running on this node."""
    target_procs = [
        ("Ray Head/Worker", ["raylet", "ray-dashboard", "ray_core"]),
        ("Glances Telemetry", ["glances"]),
        ("Tailscale Mesh", ["tailscaled"]),
        ("Xvfb Framebuffer", ["Xvfb"]),
        ("OpenSSH Server", ["sshd"]),
        ("Docker Engine", ["dockerd"]),
        ("Hermes Mesh Broker", ["mesh_broker", "hermes_mesh_daemon"]),
        ("Local AI Worker", ["prima-worker", "llama-server", "continuous_1m_router"]),
    ]
    results = []
    try:
        out = subprocess.run(["ps", "-eo", "pid,%cpu,%mem,args"], capture_output=True, text=True, timeout=1.0)
        lines = out.stdout.splitlines()[1:] if out.returncode == 0 else []
        for name, patterns in target_procs:
            matched = False
            for line in lines:
                parts = line.strip().split(None, 3)
                if len(parts) >= 4:
                    pid, cpu, mem, args = parts[0], parts[1], parts[2], parts[3]
                    if any(p in args for p in patterns) and "grep" not in args:
                        results.append({
                            "name": name,
                            "pid": pid,
                            "cpu": f"{cpu}%",
                            "mem": f"{mem}%",
                            "status": "RUNNING",
                        })
                        matched = True
                        break
            if not matched:
                results.append({
                    "name": name,
                    "pid": "--",
                    "cpu": "--",
                    "mem": "--",
                    "status": "INACTIVE",
                })
    except Exception:
        pass
    return results

# ---------------------------------------------------------------------------
# Terminal Rendering Engine (Double-Buffered ANSI)
# ---------------------------------------------------------------------------
def _format_bar(pct: float, width: int = 32) -> str:
    """Renders a high-resolution colored progress bar."""
    fill = int(round((pct / 100.0) * width))
    fill = max(0, min(width, fill))
    bar_str = "█" * fill + "░" * (width - fill)
    color = C_BGREEN if pct < 70.0 else (C_BYELLOW if pct < 85.0 else C_BRED)
    return f"{color}[{bar_str}]{C_RESET}"

def render_screen(frame_seq: int, start_time: float) -> str:
    """Builds the complete terminal screen string buffer with exact border alignment."""
    tele = harvest_system_telemetry()
    ifaces = harvest_network_interfaces()
    daemons = harvest_active_daemons()
    
    with _cache_lock:
        probes = list(_ping_cache.values())

    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
    node_id = "L8" if "lauburu" in tele["hostname"] else ("L3" if "linux" in tele["hostname"] else "LINUX")
    
    W = 100  # Total inner box width
    hbar = "─" * W
    lines = []

    def add_box_line(content: str):
        padded = pad_box_row(content, W)
        lines.append(f"{C_BCYAN}│{C_RESET}{padded}{C_BCYAN}│{C_RESET}")

    # Top Header
    lines.append("")
    lines.append(f"{C_BCYAN}┌{hbar}┐{C_RESET}")
    title = f" 🏛️  LAUBURU SOVEREIGN MESH — NETWORK & HARDWARE HEALTH TERMINAL  [{node_id}]"
    add_box_line(f"{C_BWHITE}{title}{C_RESET}")
    sub1 = f" Host: {tele['hostname']} ({tele['kernel']}) | Arch: {tele['arch']} | CPU: {tele['cpu_model'][:32]} | Temp: {tele['thermal_c']}"
    add_box_line(f"{C_WHITE}{sub1}{C_RESET}")
    sub2 = f" Uptime: {tele['uptime_str']} | Load: {tele['loadavg']} | Heartbeat: #{frame_seq} | Time: {now_str} AEST"
    add_box_line(f"{C_GRAY}{sub2}{C_RESET}")
    lines.append(f"{C_BCYAN}└{hbar}┘{C_RESET}")

    # Section 1: Live Mesh Connectivity
    tag1 = "── 🌐 LIVE MESH CONNECTIVITY & RTT LATENCY "
    hbar1 = "─" * max(0, W - len(tag1))
    lines.append(f"{C_BCYAN}┌{tag1}{hbar1}┐{C_RESET}")
    
    header_conn = f"  {'ID':<5} {'NODE NAME':<24} {'TARGET IP':<18} {'TRANSPORT':<18} {'STATUS':<10} {'RTT LATENCY':<12} {'LAST SEEN'}"
    add_box_line(f"{C_DIM}{header_conn}{C_RESET}")
    add_box_line(f"  {C_GRAY}{'─' * (W - 4)}{C_RESET}")

    for p in probes:
        stat = p.get("status", "OFFLINE")
        if stat == "ONLINE":
            stat_str = f"{C_BGREEN}ONLINE ●{C_RESET}"
            rtt_val = p.get("rtt_ms", 0.0)
            rtt_col = C_BGREEN if rtt_val < 5.0 else (C_BYELLOW if rtt_val < 30.0 else C_WHITE)
            rtt_str = f"{rtt_col}{rtt_val:6.2f} ms{C_RESET}"
        elif stat == "LOCAL":
            stat_str = f"{C_BCYAN}LOCAL  ●{C_RESET}"
            rtt_str = f"{C_BCYAN}  0.05 ms{C_RESET}"
        else:
            stat_str = f"{C_BRED}OFFLINE○{C_RESET}"
            rtt_str = f"{C_GRAY}   -- ms{C_RESET}"

        row_content = (
            f"  {C_BWHITE}{p.get('id', '--'):<5}{C_RESET} "
            f"{C_WHITE}{p.get('name', '--')[:23]:<24}{C_RESET} "
            f"{C_CYAN}{p.get('active_ip', '--'):<18}{C_RESET} "
            f"{C_GRAY}{p.get('transport', '--')[:17]:<18}{C_RESET} "
            f"{stat_str}  "
            f"{rtt_str:<12} "
            f"{C_DIM}{p.get('last_seen', '--')}{C_RESET}"
        )
        add_box_line(row_content)
    lines.append(f"{C_BCYAN}└{hbar}┘{C_RESET}")

    # Section 2: Physical & Virtual Network Interfaces
    tag2 = "── 📡 PHYSICAL & VIRTUAL NETWORK INTERFACES "
    hbar2 = "─" * max(0, W - len(tag2))
    lines.append(f"{C_BCYAN}┌{tag2}{hbar2}┐{C_RESET}")

    header_iface = f"  {'INTERFACE':<16} {'IPV4 ADDRESS':<20} {'STATE':<8} {'RX RATE':<14} {'TX RATE':<14} {'TOTAL RX/TX':<18} {'ERR'}"
    add_box_line(f"{C_DIM}{header_iface}{C_RESET}")
    add_box_line(f"  {C_GRAY}{'─' * (W - 4)}{C_RESET}")

    for iface in ifaces[:5]:
        st = iface["state"]
        st_col = C_BGREEN if st == "UP" else C_GRAY
        rx_rate = f"{iface['rx_rate_kb']:.1f} KB/s" if iface['rx_rate_kb'] < 1024.0 else f"{iface['rx_rate_kb']/1024.0:.2f} MB/s"
        tx_rate = f"{iface['tx_rate_kb']:.1f} KB/s" if iface['tx_rate_kb'] < 1024.0 else f"{iface['tx_rate_kb']/1024.0:.2f} MB/s"
        tot_str = f"{iface['rx_total_mb']:.0f}M / {iface['tx_total_mb']:.0f}M"
        err_str = f"{iface['errors']}" if iface['errors'] > 0 else "0"
        err_col = C_BRED if iface['errors'] > 0 else C_GRAY

        row_if = (
            f"  {C_BWHITE}{iface['name']:<16}{C_RESET} "
            f"{C_CYAN}{iface['ip']:<20}{C_RESET} "
            f"{st_col}{st:<8}{C_RESET} "
            f"{C_GREEN}{rx_rate:<14}{C_RESET} "
            f"{C_YELLOW}{tx_rate:<14}{C_RESET} "
            f"{C_WHITE}{tot_str:<18}{C_RESET} "
            f"{err_col}{err_str}{C_RESET}"
        )
        add_box_line(row_if)
    lines.append(f"{C_BCYAN}└{hbar}┘{C_RESET}")

    # Section 3: Hardware Sanctuary & RAM Governance (Rule 3)
    tag3 = "── 🛡️ HARDWARE SANCTUARY & MEMORY GOVERNANCE (RULE 3) "
    hbar3 = "─" * max(0, W - len(tag3))
    lines.append(f"{C_BCYAN}┌{tag3}{hbar3}┐{C_RESET}")

    sanctuary_ok = tele["ram_avail_gb"] >= 4.8
    sanc_status = f"{C_BGREEN}HEALTHY (>=4.8GB Free){C_RESET}" if sanctuary_ok else f"{C_BRED}PRESSURE (<4.8GB Free){C_RESET}"
    ram_bar = _format_bar(tele["ram_used_pct"], width=28)
    
    r1 = f"  RAM Total: {tele['ram_total_gb']} GB | Used: {tele['ram_used_gb']} GB ({tele['ram_used_pct']}%) | Avail: {tele['ram_avail_gb']} GB | Status: {sanc_status}"
    add_box_line(r1)
    r2 = f"  Usage: {ram_bar} {C_BWHITE}{tele['ram_used_pct']}%{C_RESET} | Swap: {tele['swap_used_gb']}/{tele['swap_total_gb']} GB ({tele['swap_used_pct']}%)"
    add_box_line(r2)
    r3 = f"  Storage (/): {tele['disk_free_gb']} GB Free / {tele['disk_total_gb']} GB Total ({tele['disk_used_pct']}% used)"
    add_box_line(f"{C_GRAY}{r3}{C_RESET}")
    lines.append(f"{C_BCYAN}└{hbar}┘{C_RESET}")

    # Section 4: Active Mesh Daemons
    tag4 = "── ⚙️ ACTIVE MESH DAEMONS & SUPERVISOR "
    hbar4 = "─" * max(0, W - len(tag4))
    lines.append(f"{C_BCYAN}┌{tag4}{hbar4}┐{C_RESET}")

    header_d = f"  {'SERVICE':<26} {'PID':<8} {'CPU %':<10} {'MEM %':<10} {'STATE':<12} {'ROLE'}"
    add_box_line(f"{C_DIM}{header_d}{C_RESET}")
    add_box_line(f"  {C_GRAY}{'─' * (W - 4)}{C_RESET}")

    for d in daemons[:5]:
        d_st = d["status"]
        st_col = C_BGREEN if d_st == "RUNNING" else C_GRAY
        row_d = (
            f"  {C_BWHITE}{d['name']:<26}{C_RESET} "
            f"{C_CYAN}{d['pid']:<8}{C_RESET} "
            f"{C_WHITE}{d['cpu']:<10}{C_RESET} "
            f"{C_WHITE}{d['mem']:<10}{C_RESET} "
            f"{st_col}{d_st:<12}{C_RESET} "
            f"{C_GRAY}Active Mesh Subsystem{C_RESET}"
        )
        add_box_line(row_d)
    lines.append(f"{C_BCYAN}└{hbar}┘{C_RESET}")

    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------------------
# Main Execution Loop
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Network & Hardware Health Terminal")
    parser.add_argument("--once", action="store_true", help="Print single frame and exit (for testing/CI)")
    args = parser.parse_args()

    local_ips = _get_local_ip_list()
    for target in PEER_TARGETS:
        probe = _ping_target(target, local_ips)
        with _cache_lock:
            _ping_cache[target["id"]] = probe

    if args.once:
        screen = render_screen(frame_seq=1, start_time=time.time())
        print(screen)
        return

    # Full-screen dynamic loop
    sys.stdout.write("\033[?25l")  # Hide cursor
    sys.stdout.write("\033[2J\033[H")  # Clear screen once
    sys.stdout.flush()

    t = threading.Thread(target=_ping_worker_loop, daemon=True)
    t.start()

    frame_seq = 0
    start_time = time.time()

    try:
        while True:
            frame_seq += 1
            screen = render_screen(frame_seq, start_time)
            sys.stdout.write("\033[H" + screen)
            sys.stdout.flush()
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        sys.stdout.write("\033[?25h\n")  # Restore cursor
        sys.stdout.flush()

if __name__ == "__main__":
    main()
