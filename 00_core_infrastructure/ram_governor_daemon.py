#!/usr/bin/env python3
"""
00_core_infrastructure/ram_governor_daemon.py
==============================================
Production Mesh RAM & CPU Sanctuary Governor, Dynamic Offloader & Overflow Guard.
Governed by:
- Rule #0 (Canonical Hardware & Port Truth)
- Rule #1 (Zero-Mock Empirical Grounding & Darwin Kernel Memory Accounting Formulas)
- Rule #3 (Host Sanctuary Headroom >= 4.8 GB Free/Available RAM, <= 80% Used)

Monitors authentic physical RAM and CPU utilization across all 10 nodes of the Lauburu Mesh:
- L1: mac-mini-m4 (Local Host, 24 GB Unified Memory)
- L8 (L0_Linux_Mini): lauburu (Ubuntu 24.04, 32 GB RAM via 40Gbps TB4 10.0.0.8 / 100.121.247.8)
- L1b: mac-mini-m2 (Apple M2 Pro, 16 GB RAM via 40Gbps TB4 10.0.0.3 / 192.168.8.114)
- L2: macbook-intel (Intel Core i7, 16 GB RAM via 100.103.212.21 / 192.168.8.127)
- L5 (L1a): mac-air-m4 (Apple M4, 16 GB RAM via 100.121.202.34 / 192.168.8.248)
- L3: linux-amd-gpu (AMD Ryzen 7 5700U, 15 GB RAM via 192.168.8.225 / 100.101.39.98)
- L4: pixel-avf-debian (Debian 13 AVF VM, 10 GB RAM via 100.80.64.5 / L6 bridge 10.144.55.53)
- L6: pixel-10 (Tensor G5 Android 17, 15 GB RAM via Termux SSH :8022 192.168.8.213 / ADB)
- L7: galaxy-s20 (Exynos 990 Android 13, 12 GB RAM via 192.168.8.101 / 100.124.199.15)
- GW: router (GL-BE14000 OpenWrt, 2 GB RAM via 192.168.8.1 / 100.70.123.123)
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

os.environ["PATH"] = f"/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:{os.environ.get('PATH', '')}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RAM-Governor] %(levelname)s: %(message)s"
)
logger = logging.getLogger("RAMGovernor")

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
STATE_JSON = REPO_ROOT / "00_core_infrastructure/mesh_ram_matrix_live.json"
OBS_MD = REPO_ROOT / "obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md"
LORA_DATASET = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")

# Rule 3 Canonical Host Sanctuary Threshold: >= 4.8 GB available (<= 80% used on 24 GB host)
MIN_HOST_FREE_RAM_GB = 4.8

SSH_BASE_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=3",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Authentic Hardware Probing Helpers (Rule #0 & Rule #1 Zero-Mock)
# ─────────────────────────────────────────────────────────────────────────────

def ensure_thunderbolt_bridge_healthy() -> bool:
    """
    Ensures L1's Thunderbolt 4 `bridge0` retains its canonical `10.0.0.2/24` IP
    so 40 Gb/s links to L8 (`10.0.0.8`), L1b (`10.0.0.3`), and L2 (`10.0.0.4`)
    do not fall back to DHCP link-local (`169.254.x.x`).
    """
    try:
        out = subprocess.check_output(["ifconfig", "bridge0"], stderr=subprocess.DEVNULL, text=True, timeout=1.5)
        if "inet 10.0.0.2 " in out:
            return True
        subprocess.run(
            ["sudo", "-n", "ifconfig", "bridge0", "inet", "10.0.0.2", "netmask", "255.255.255.0", "alias"],
            capture_output=True,
            timeout=2.0,
        )
        out2 = subprocess.check_output(["ifconfig", "bridge0"], stderr=subprocess.DEVNULL, text=True, timeout=1.5)
        return "inet 10.0.0.2 " in out2
    except Exception:
        return False


def _parse_darwin_vm_and_cpu(out: str, default_total_gb: float = 16.0) -> Dict[str, Any]:
    """
    Parses Darwin `vm_stat`, `sysctl hw.memsize`, `sysctl hw.ncpu`, `sysctl vm.loadavg`,
    `kern.memorystatus_vm_pressure_level`, and instantaneous `ps -A -o %cpu` according to Rule 1 Section 6.
    """
    page_size = 16384
    vals: Dict[str, int] = {}
    total_bytes = int(default_total_gb * (1024 ** 3))
    ncpu = 8
    pressure = 1
    load_1m = load_5m = load_15m = 0.0
    ps_cpu_sum: Optional[float] = None

    for line in out.splitlines():
        s = line.strip()
        if "page size of" in s:
            m = re.search(r"page size of (\d+) bytes", s)
            if m:
                page_size = int(m.group(1))
        elif ":" in s and not s.startswith(("MEMSIZE:", "NCPU:", "LOADAVG:", "PRESSURE:", "PSCPU:")):
            k, v = s.split(":", 1)
            v_clean = v.strip().rstrip(".")
            if v_clean.isdigit():
                vals[k.strip()] = int(v_clean)
        elif s.startswith("MEMSIZE:"):
            total_bytes = int(s.split(":", 1)[1].strip())
        elif s.startswith("NCPU:"):
            ncpu = int(s.split(":", 1)[1].strip())
        elif s.startswith("PRESSURE:"):
            try:
                pressure = int(s.split(":", 1)[1].strip())
            except ValueError:
                pressure = 1
        elif s.startswith("LOADAVG:"):
            nums = re.findall(r"(\d+\.\d+)", s)
            if len(nums) >= 3:
                load_1m, load_5m, load_15m = float(nums[0]), float(nums[1]), float(nums[2])
        elif s.startswith("PSCPU:"):
            try:
                ps_cpu_sum = float(s.split(":", 1)[1].strip())
            except ValueError:
                ps_cpu_sum = None

    anon = vals.get("Anonymous pages", 0)
    purge = vals.get("Pages purgeable", 0)
    wired = vals.get("Pages wired down", 0)
    comp = vals.get("Pages occupied by compressor", 0)
    file_backed = vals.get("File-backed pages", 0)
    free_p = vals.get("Pages free", 0)
    spec_p = vals.get("Pages speculative", 0)
    inact_p = vals.get("Pages inactive", 0)

    total_gb = round(total_bytes / (1024 ** 3), 2)
    app_bytes = max(0, (anon - purge) * page_size)
    wired_bytes = wired * page_size
    comp_bytes = comp * page_size
    cached_bytes = (file_backed + purge) * page_size
    rule1_used_bytes = app_bytes + wired_bytes + comp_bytes
    rule1_avail_bytes = max(0, total_bytes - rule1_used_bytes)
    reclaimable_avail_bytes = (free_p + spec_p + inact_p + purge) * page_size

    # Strict Rule 1 Section 6 available_gb = Total - (App + Wired + Compressed)
    rule1_avail_gb = round(rule1_avail_bytes / (1024 ** 3), 2)
    avail_gb = rule1_avail_gb
    reclaimable_gb = round(reclaimable_avail_bytes / (1024 ** 3), 2)
    pure_free_gb = round((free_p + spec_p) * page_size / (1024 ** 3), 2)
    app_gb = round(app_bytes / (1024 ** 3), 2)
    wired_gb = round(wired_bytes / (1024 ** 3), 2)
    comp_gb = round(comp_bytes / (1024 ** 3), 2)
    cached_gb = round(cached_bytes / (1024 ** 3), 2)
    rule1_used_gb = round(rule1_used_bytes / (1024 ** 3), 2)
    used_pct = round((rule1_used_bytes / total_bytes) * 100.0, 1) if total_bytes else 0.0
    if ps_cpu_sum is not None:
        cpu_used_pct = round(min(100.0, ps_cpu_sum / max(1, ncpu)), 1)
    else:
        cpu_used_pct = round(min(100.0, (load_1m / max(1, ncpu)) * 100.0), 1)

    return {
        "total_gb": total_gb,
        "available_gb": avail_gb,
        "rule1_avail_gb": rule1_avail_gb,
        "reclaimable_gb": reclaimable_gb,
        "pure_free_gb": pure_free_gb,
        "app_gb": app_gb,
        "wired_gb": wired_gb,
        "compressed_gb": comp_gb,
        "cached_files_gb": cached_gb,
        "memory_used_gb": rule1_used_gb,
        "used_pct": used_pct,
        "memory_pressure": pressure,
        "cpu_cores": ncpu,
        "cpu_load_1m": load_1m,
        "cpu_load_5m": load_5m,
        "cpu_load_15m": load_15m,
        "cpu_used_pct": cpu_used_pct,
    }


def _parse_linux_mem_and_cpu(out: str, is_android: bool = False) -> Dict[str, Any]:
    """Parses Linux/Android `/proc/meminfo`, `/proc/loadavg`, `nproc`, and `ps -eo %cpu`."""
    total_kb = avail_kb = free_kb = buffers_kb = cached_kb = swap_total_kb = swap_free_kb = 0
    inactive_anon_kb = sreclaimable_kb = 0
    ncpu = 4
    load_1m = load_5m = load_15m = 0.0
    ps_cpu_sum: Optional[float] = None

    for line in out.splitlines():
        s = line.strip()
        if s.startswith("MemTotal:"):
            total_kb = int(s.split()[1])
        elif s.startswith("MemAvailable:"):
            avail_kb = int(s.split()[1])
        elif s.startswith("MemFree:"):
            free_kb = int(s.split()[1])
        elif s.startswith("Buffers:"):
            buffers_kb = int(s.split()[1])
        elif s.startswith("Cached:"):
            cached_kb = int(s.split()[1])
        elif s.startswith("Inactive(anon):"):
            inactive_anon_kb = int(s.split()[1])
        elif s.startswith("SReclaimable:"):
            sreclaimable_kb = int(s.split()[1])
        elif s.startswith("SwapTotal:"):
            swap_total_kb = int(s.split()[1])
        elif s.startswith("SwapFree:"):
            swap_free_kb = int(s.split()[1])
        elif s.startswith("NCPU:"):
            try:
                ncpu = int(s.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif s.startswith("LOADAVG:"):
            raw_la = s.split(":", 1)[1].strip()
            if "load average:" in raw_la:
                raw_la = raw_la.split("load average:", 1)[1].replace(",", " ")
            nums = re.findall(r"(\d+\.\d+)", raw_la)
            if len(nums) >= 3:
                try:
                    load_1m, load_5m, load_15m = float(nums[0]), float(nums[1]), float(nums[2])
                except ValueError:
                    pass
        elif s.startswith("PSCPU:"):
            try:
                val = float(s.split(":", 1)[1].strip())
                if val > 0.0:
                    ps_cpu_sum = val
            except ValueError:
                pass

    if avail_kb == 0 and free_kb > 0:
        avail_kb = free_kb + buffers_kb + cached_kb

    raw_linux_avail_kb = avail_kb
    if is_android and (inactive_anon_kb > 0 or sreclaimable_kb > 0):
        # Android lmkd reclaims cached background Zygote processes in Inactive(anon) + SReclaimable
        avail_kb = min(total_kb, raw_linux_avail_kb + inactive_anon_kb + sreclaimable_kb)

    total_gb = round(total_kb / (1024 ** 2), 2)
    avail_gb = round(avail_kb / (1024 ** 2), 2)
    pure_free_gb = round(free_kb / (1024 ** 2), 2)
    used_gb = round(max(0.0, total_gb - avail_gb), 2)
    swap_total_gb = round(swap_total_kb / (1024 ** 2), 2)
    swap_free_gb = round(swap_free_kb / (1024 ** 2), 2)
    used_pct = round(((total_kb - avail_kb) / total_kb) * 100.0, 1) if total_kb else 0.0
    if ps_cpu_sum is not None:
        cpu_used_pct = round(min(100.0, ps_cpu_sum / max(1, ncpu)), 1)
    else:
        cpu_used_pct = round(min(100.0, (load_1m / max(1, ncpu)) * 100.0), 1)

    res: Dict[str, Any] = {
        "total_gb": total_gb,
        "available_gb": avail_gb,
        "pure_free_gb": pure_free_gb,
        "memory_used_gb": used_gb,
        "swap_total_gb": swap_total_gb,
        "swap_free_gb": swap_free_gb,
        "used_pct": used_pct,
        "cpu_cores": ncpu,
        "cpu_load_1m": load_1m,
        "cpu_load_5m": load_5m,
        "cpu_load_15m": load_15m,
        "cpu_used_pct": cpu_used_pct,
    }
    if is_android:
        res["linux_memavailable_gb"] = round(raw_linux_avail_kb / (1024 ** 2), 2)
        res["android_reclaimable_cached_gb"] = round((inactive_anon_kb + sreclaimable_kb) / (1024 ** 2), 2)
    return res


def _warm_gguf_page_cache_and_compress_cold_anon() -> bool:
    """
    Streams local GGUF model files through the Darwin VFS buffer cache (`file_backed_pages`),
    which instructs the XNU VM pageout daemon to compress cold anonymous pages (`app_gb` ->
    `compressed_gb` at >2:1 ratio) and keeps local LLM weights resident in reclaimable file cache.
    """
    candidates = [
        Path("/Users/aaron/.local/share/models/Hermes-3-Llama-3.1-8B.Q4_K_M.gguf"),
        Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/qwen2.5-0.5b-instruct-q4_k_m.gguf"),
    ]
    warmed = False
    for path in candidates:
        if path.exists():
            try:
                with open(path, "rb") as f:
                    while f.read(16 * 1024 * 1024):
                        pass
                warmed = True
            except Exception:
                continue
    return warmed


def probe_l1_mac_mini() -> Dict[str, Any]:
    """Reads local Darwin kernel Mach VM and CPU statistics on L1 (`mac-mini-m4`)."""
    try:
        cmd = (
            "vm_stat; "
            "echo MEMSIZE:$(sysctl -n hw.memsize); "
            "echo NCPU:$(sysctl -n hw.ncpu); "
            "echo LOADAVG:$(sysctl -n vm.loadavg); "
            "echo PRESSURE:$(sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1); "
            "echo PSCPU:$(ps -A -o %cpu | awk 'NR>1 {s+=$1} END {printf \"%.1f\", s}')"
        )
        out = subprocess.check_output(["/bin/sh", "-c", cmd], text=True, timeout=4.0)
        stats = _parse_darwin_vm_and_cpu(out, default_total_gb=24.0)
        sanctuary_ok = (
            stats["rule1_avail_gb"] >= MIN_HOST_FREE_RAM_GB
            and stats["used_pct"] <= 80.0
        )
        return {
            "node_id": "L1",
            "name": "Apple M4 Pro Mac Mini (mac-mini-m4)",
            "ip": "10.0.0.2 / 192.168.8.143",
            "transport": "Local Host / TB4 Bridge0",
            "role": "Primary Host & Memory Sanctuary Governor",
            "status": "ONLINE",
            **stats,
            "sanctuary_healthy": sanctuary_ok,
            "can_receive_offload": False,
            "rtt_ms": 0.0,
        }
    except Exception as e:
        logger.error(f"Error probing L1 Mac Mini: {e}")
        return {"node_id": "L1", "name": "Apple M4 Pro Mac Mini", "status": "ERROR", "available_gb": 0.0}


def _probe_remote_darwin(
    node_id: str,
    name: str,
    role: str,
    targets: List[Tuple[str, str]],
    default_total_gb: float = 16.0,
    min_offload_gb: float = 2.5,
) -> Dict[str, Any]:
    """Probes a remote macOS node over TB4 / LAN / Tailscale SSH with 3-pass retry resilience."""
    remote_cmd = (
        "vm_stat; "
        "echo MEMSIZE:$(/usr/sbin/sysctl -n hw.memsize); "
        "echo NCPU:$(/usr/sbin/sysctl -n hw.ncpu); "
        "echo LOADAVG:$(/usr/sbin/sysctl -n vm.loadavg); "
        "echo PRESSURE:$(/usr/sbin/sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null || echo 1); "
        "echo PSCPU:$(ps -A -o %cpu | awk 'NR>1 {s+=$1} END {printf \"%.1f\", s}')"
    )
    for attempt, cmd_timeout in enumerate((3.5, 5.0, 6.5)):
        for ssh_target, transport_desc in targets:
            t0 = time.perf_counter()
            try:
                out = subprocess.check_output(
                    ["ssh", *SSH_BASE_OPTS, ssh_target, remote_cmd],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=cmd_timeout,
                )
                rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                stats = _parse_darwin_vm_and_cpu(out, default_total_gb=default_total_gb)
                host_ip = ssh_target.split("@")[-1]
                return {
                    "node_id": node_id,
                    "name": name,
                    "ip": host_ip,
                    "transport": transport_desc,
                    "role": role,
                    "status": "ONLINE",
                    **stats,
                    "can_receive_offload": stats["available_gb"] >= min_offload_gb and stats["cpu_used_pct"] < 85.0,
                    "rtt_ms": rtt_ms,
                }
            except Exception:
                continue
        if attempt < 2:
            time.sleep(0.2)

    return {
        "node_id": node_id,
        "name": name,
        "role": role,
        "status": "UNREACHABLE",
        "total_gb": default_total_gb,
        "available_gb": 0.0,
        "can_receive_offload": False,
    }


probe_remote_darwin_node = _probe_remote_darwin


def _probe_remote_linux(
    node_id: str,
    name: str,
    role: str,
    targets: List[Tuple[List[str], str, str]],
    default_total_gb: float = 16.0,
    min_offload_gb: float = 2.0,
    is_android: bool = False,
) -> Dict[str, Any]:
    """Probes a remote Linux/Android/OpenWrt node over SSH with 3-pass retry resilience."""
    remote_cmd = (
        "cat /proc/meminfo; "
        "echo NCPU:$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 4); "
        "echo LOADAVG:$(cat /proc/loadavg 2>/dev/null || uptime); "
        "echo PSCPU:$(ps -eo %cpu,comm 2>/dev/null | awk 'NR>1 && $2!=\"ps\" && $2!=\"awk\" && $2!=\"sh\" && $2!=\"bash\" {s+=$1} END {printf \"%.1f\", s}')"
    )
    for attempt, cmd_timeout in enumerate((3.5, 5.0, 6.5)):
        for cmd_prefix, host_ip, transport_desc in targets:
            t0 = time.perf_counter()
            try:
                out = subprocess.check_output(
                    [*cmd_prefix, remote_cmd],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=cmd_timeout,
                )
                rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                stats = _parse_linux_mem_and_cpu(out, is_android=is_android)
                return {
                    "node_id": node_id,
                    "name": name,
                    "ip": host_ip,
                    "transport": transport_desc,
                    "role": role,
                    "status": "ONLINE",
                    **stats,
                    "can_receive_offload": stats["available_gb"] >= min_offload_gb and stats["cpu_used_pct"] < 85.0,
                    "rtt_ms": rtt_ms,
                }
            except Exception:
                continue
        if attempt < 2:
            time.sleep(0.2)

    return {
        "node_id": node_id,
        "name": name,
        "role": role,
        "status": "UNREACHABLE",
        "total_gb": default_total_gb,
        "available_gb": 0.0,
        "can_receive_offload": False,
    }


probe_remote_linux_node = _probe_remote_linux


def probe_l0_linux_mini() -> Dict[str, Any]:
    """Probes L8 (`lauburu`, Ubuntu 24.04, 32 GB RAM) over 40Gbps TB4 `10.0.0.8` or Tailscale."""
    return _probe_remote_linux(
        node_id="L8",
        name="Ubuntu 24.04 Linux Mini Hub (lauburu)",
        role="Primary 40Gbps TB4 High-Capacity Offload & 27B Shard Host",
        targets=[
            (["ssh", *SSH_BASE_OPTS, "linuxmini@10.0.0.8"], "10.0.0.8", "Thunderbolt 4 (40 Gb/s bridge0)"),
            (["ssh", *SSH_BASE_OPTS, "linuxmini@100.121.247.8"], "100.121.247.8", "Tailscale Mesh"),
        ],
        default_total_gb=31.19,
        min_offload_gb=3.0,
    )


def probe_l1b_mac_mini_m2() -> Dict[str, Any]:
    """Probes L1b (`mac-mini-m2`, Apple M2 Pro, 16 GB RAM) over 40Gbps TB4 `10.0.0.3` or LAN."""
    return _probe_remote_darwin(
        node_id="L1b",
        name="Apple M2 Pro Mac Mini (mac-mini-m2)",
        role="Thunderbolt 4 Metal GPU Shard & Secondary Compute",
        targets=[
            ("aaronmaher@10.0.0.3", "Thunderbolt 4 (40 Gb/s bridge0)"),
            ("aaronmaher@192.168.8.114", "LAN Wi-Fi"),
            ("aaronmaher@100.104.128.34", "Tailscale Mesh"),
        ],
        default_total_gb=16.0,
        min_offload_gb=2.5,
    )


def probe_l2_macbook_pro() -> Dict[str, Any]:
    """Probes L2 (`macbook-intel`, Intel i7, 16 GB RAM) over 40Gbps TB4 `10.0.0.4` or Tailscale/LAN."""
    return _probe_remote_darwin(
        node_id="L2",
        name="MacBook Pro Intel i7 (macbook-intel)",
        role="Desktop Automation Target (Screen Lens Teacher) & Secondary Worker",
        targets=[
            ("aaronmaher@10.0.0.4", "Thunderbolt 4 (40 Gb/s bridge0)"),
            ("aaronmaher@100.103.212.21", "Tailscale Direct (192.168.8.127)"),
            ("aaronmaher@192.168.8.127", "LAN Wi-Fi"),
        ],
        default_total_gb=16.0,
        min_offload_gb=2.5,
    )


def probe_l5_macbook_air() -> Dict[str, Any]:
    """Probes L1a / L5 (`mac-air-m4`, Apple M4, 16 GB RAM) over 40Gbps TB4 (`10.0.0.5`), LAN, or Tailscale."""
    return _probe_remote_darwin(
        node_id="L1a",
        name="Apple M4 MacBook Air (mac-air-m4)",
        role="High-Efficiency M4 Metal Worker & ANE Node",
        targets=[
            ("aaronmaher@10.0.0.5", "Thunderbolt 4 (40 Gb/s bridge0)"),
            ("aaronmaher@169.254.190.217", "Thunderbolt 4 Link-Local (bridge0)"),
            ("aaronmaher@192.168.8.193", "LAN Wi-Fi"),
            ("aaronmaher@100.121.202.34", "Tailscale Direct"),
            ("aaronmaher@192.168.8.248", "LAN Wi-Fi (Secondary)"),
        ],
        default_total_gb=16.0,
        min_offload_gb=2.5,
    )


def probe_l3_linux_head_node() -> Dict[str, Any]:
    """Probes L3 (`linux-amd-gpu`, AMD Ryzen 7 5700U, 15 GB RAM) over LAN/Tailscale."""
    return _probe_remote_linux(
        node_id="L3",
        name="AMD Ryzen 7 5700U Linux Head Node (linux-amd-gpu)",
        role="SeaweedFS DFS (:8888), Docker Hub & Compute Offload Worker",
        targets=[
            (["ssh", *SSH_BASE_OPTS, "linux@192.168.8.225"], "192.168.8.225", "LAN Direct (4.2ms)"),
            (["ssh", *SSH_BASE_OPTS, "linux@100.101.39.98"], "100.101.39.98", "Tailscale Mesh"),
        ],
        default_total_gb=14.97,
        min_offload_gb=2.5,
    )


def probe_l4_linux_tablet() -> Dict[str, Any]:
    """Probes L4 (`pixel-avf-debian`, Debian 13 pKVM on Tensor G5, 10 GB RAM) via Tailscale or L6 tap bridge."""
    return _probe_remote_linux(
        node_id="L4",
        name="Debian 13 AVF MicroVM (pixel-avf-debian)",
        role="Isolated Linux MicroVM Sandbox, CDP & Edge Worker",
        targets=[
            (["ssh", *SSH_BASE_OPTS, "droid@100.80.64.5"], "100.80.64.5", "Tailscale Mesh"),
            (
                [
                    "ssh", *SSH_BASE_OPTS, "-p", "8022", "192.168.8.213",
                    "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 droid@10.144.55.53",
                ],
                "10.144.55.53 (via L6 192.168.8.213)",
                "AVF Hypervisor Tap Bridge (sub-ms)",
            ),
        ],
        default_total_gb=9.99,
        min_offload_gb=2.0,
    )


def probe_l6_pixel_10() -> Dict[str, Any]:
    """Probes L6 (`pixel-10`, Tensor G5 Android 17, 15 GB RAM) via Termux SSH :8022 or ADB."""
    res = _probe_remote_linux(
        node_id="L6",
        name="Google Pixel 10 Pro XL (pixel-10)",
        role="Tensor G5 Llama RPC (:50052), AVF Hypervisor Host & Screen Lens (:3035)",
        targets=[
            (["ssh", *SSH_BASE_OPTS, "-p", "8022", "192.168.8.213"], "192.168.8.213", "Termux SSH :8022 (LAN)"),
            (["ssh", *SSH_BASE_OPTS, "-p", "8022", "100.114.215.68"], "100.114.215.68", "Termux SSH :8022 (Tailscale)"),
        ],
        default_total_gb=14.73,
        min_offload_gb=2.0,
        is_android=True,
    )
    if res.get("status") == "ONLINE":
        return res

    # Fallback to ADB if Termux SSH is temporarily unreachable
    try:
        adb_devs = subprocess.check_output(["adb", "devices"], text=True, timeout=2.0)
        for line in adb_devs.splitlines():
            if "192.168.8.213" in line and "\tdevice" in line:
                serial = line.split()[0]
                out = subprocess.check_output(
                    ["adb", "-s", serial, "shell", "cat /proc/meminfo; echo NCPU:8; echo LOADAVG:$(cat /proc/loadavg)"],
                    text=True,
                    timeout=3.0,
                )
                stats = _parse_linux_mem_and_cpu(out, is_android=True)
                return {
                    "node_id": "L6",
                    "name": "Google Pixel 10 Pro XL (pixel-10)",
                    "ip": serial,
                    "transport": "ADB Wireless Bridge",
                    "role": "Tensor G5 Llama RPC (:50052) & Screen Lens",
                    "status": "ONLINE",
                    **stats,
                    "can_receive_offload": stats["available_gb"] >= 2.0,
                }
    except Exception:
        pass
    return res


def probe_l7_galaxy_s20() -> Dict[str, Any]:
    """
    Probes L7 (`galaxy-s20`, Exynos 990, 12 GB RAM).
    Checks Termux SSH (`192.168.8.224` USB Eth, `192.168.8.101` LAN, `100.124.199.15` Tailscale)
    and Wireless ADB (including mDNS `_adb-tls-connect._tcp` auto-discovery for `R3CN40CJJ1R`) first;
    if Android Doze protects inbound shell ports while L7 maintains active LAN/Tailscale ping,
    KDE Connect (`:1716`, device `46d2277e39eb41ae8471a739ad8371bb`), and outbound SSH sockets into L1,
    reports authentic connectivity without fabricating `/proc/meminfo` values (Rule 1 compliance).
    """
    res = _probe_remote_linux(
        node_id="L7",
        name="Samsung Galaxy S20+ 5G (galaxy-s20)",
        role="Mobile Edge Telemetry, KDE Connect & Outbound SSH Agent",
        targets=[
            (["ssh", *SSH_BASE_OPTS, "-p", "8022", "192.168.8.224"], "192.168.8.224", "Termux SSH :8022 (USB Eth)"),
            (["ssh", *SSH_BASE_OPTS, "-p", "8022", "192.168.8.101"], "192.168.8.101", "Termux SSH :8022 (LAN)"),
            (["ssh", *SSH_BASE_OPTS, "-p", "8022", "100.124.199.15"], "100.124.199.15", "Termux SSH :8022 (Tailscale)"),
        ],
        default_total_gb=12.0,
        min_offload_gb=1.5,
        is_android=True,
    )
    if res.get("status") == "ONLINE":
        return res

    # Try ADB Wireless Debugging (including mDNS discovery for R3CN40CJJ1R / 192.168.8.101 / 192.168.8.224)
    try:
        mdns_out = subprocess.check_output(["adb", "mdns", "services"], text=True, timeout=1.5)
        for line in mdns_out.splitlines():
            if any(k in line for k in ("R3CN40CJJ1R", "192.168.8.101", "192.168.8.224")):
                ep = line.split()[-1]
                subprocess.run(["adb", "connect", ep], capture_output=True, text=True, timeout=1.5)
        adb_devs = subprocess.check_output(["adb", "devices"], text=True, timeout=1.5)
        for line in adb_devs.splitlines():
            if any(k in line for k in ("R3CN40CJJ1R", "192.168.8.101", "192.168.8.224", "100.124.199.15")) and "\tdevice" in line:
                serial = line.split()[0]
                t0 = time.perf_counter()
                out = subprocess.check_output(
                    ["adb", "-s", serial, "shell", "cat /proc/meminfo; echo NCPU:8; echo LOADAVG:$(cat /proc/loadavg)"],
                    text=True,
                    timeout=2.5,
                )
                rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                stats = _parse_linux_mem_and_cpu(out, is_android=True)
                return {
                    "node_id": "L7",
                    "name": "Samsung Galaxy S20+ 5G (galaxy-s20)",
                    "ip": serial,
                    "transport": "ADB Wireless Bridge (mDNS)",
                    "role": "Mobile Edge Telemetry, KDE Connect & Outbound SSH Agent",
                    "status": "ONLINE",
                    **stats,
                    "can_receive_offload": stats["available_gb"] >= 1.5,
                    "rtt_ms": rtt_ms,
                }
    except Exception:
        pass

    # Verify live ICMP & KDE Connect (:1716) / established TCP sockets from 192.168.8.224 / 192.168.8.101 / 100.124.199.15
    for ip, transport in [
        ("192.168.8.224", "USB Eth + LAN Wi-Fi (.101) + KDE Connect (:1716) + Outbound SSH"),
        ("192.168.8.101", "LAN Wi-Fi + KDE Connect (:1716) + Outbound SSH"),
        ("100.124.199.15", "Tailscale Mesh (tailscale-termux)"),
    ]:
        t0 = time.perf_counter()
        ping = subprocess.run(["ping", "-c", "1", "-W", "400", ip], capture_output=True, text=True)
        if ping.returncode == 0:
            rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "node_id": "L7",
                "name": "Samsung Galaxy S20+ 5G (galaxy-s20)",
                "ip": ip,
                "lan_wifi_ip": "192.168.8.101",
                "tailscale_ip": "100.124.199.15",
                "kdeconnect_device_id": "46d2277e39eb41ae8471a739ad8371bb",
                "transport": transport,
                "role": "Mobile Edge Telemetry, KDE Connect & Outbound SSH Agent",
                "status": "ONLINE",
                "telemetry_mode": "LIVE_PING_KDECONNECT_AND_ESTABLISHED_SSH (Inbound Shell Doze-Protected)",
                "total_gb": 12.0,
                "available_gb": 0.0,
                "cpu_cores": 8,
                "kernel_ram_probed": "-- (Inbound SSH/ADB in Android Doze; Rule 1 Zero-Mock enforced)",
                "can_receive_offload": False,
                "rtt_ms": rtt_ms,
            }

    return res


def probe_gw_router() -> Dict[str, Any]:
    """Probes GW (`router`, GL-BE14000 OpenWrt Wi-Fi 7 Gateway, 2 GB RAM) via SSH."""
    res = _probe_remote_linux(
        node_id="GW",
        name="GL-BE14000 Wi-Fi 7 Gateway (router)",
        role="2.5GbE NBN WAN Router & Mesh Packet Switch",
        targets=[
            (["ssh", *SSH_BASE_OPTS, "root@192.168.8.1"], "192.168.8.1", "LAN Gateway"),
            (["ssh", *SSH_BASE_OPTS, "root@100.70.123.123"], "100.70.123.123", "Tailscale Gateway"),
        ],
        default_total_gb=1.94,
        min_offload_gb=10.0,  # Router never receives compute offload
    )
    res["can_receive_offload"] = False
    return res


def scan_full_mesh_ram() -> Dict[str, Dict[str, Any]]:
    """Concurrently gathers authentic physical RAM & CPU metrics across all 10 mesh nodes."""
    ensure_thunderbolt_bridge_healthy()
    probes = {
        "L1_Mac_Node": probe_l1_mac_mini,
        "L0_Linux_Mini": probe_l0_linux_mini,
        "L1b_Mac_Mini_M2": probe_l1b_mac_mini_m2,
        "L3_Linux_Head_Node": probe_l3_linux_head_node,
        "L2_MacBook_Pro": probe_l2_macbook_pro,
        "L5_MacBook_Air": probe_l5_macbook_air,
        "L4_Linux_Tablet": probe_l4_linux_tablet,
        "L6_Pixel_10_Pro_XL": probe_l6_pixel_10,
        "L7_Samsung_S20": probe_l7_galaxy_s20,
        "GW_Router": probe_gw_router,
    }
    matrix: Dict[str, Dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        future_map = {pool.submit(fn): key for key, fn in probes.items()}
        for fut in concurrent.futures.as_completed(future_map):
            key = future_map[fut]
            try:
                matrix[key] = fut.result()
            except Exception as e:
                matrix[key] = {"name": key, "status": f"ERROR: {e}", "available_gb": 0.0}

    # Preserve deterministic key ordering
    return {k: matrix[k] for k in probes.keys()}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Network Overflow Guard & Dynamic Offloading (Rule #3 & #10)
# ─────────────────────────────────────────────────────────────────────────────

def compute_network_overflow_guard(matrix: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes multi-device load distribution weights and backpressure thresholds
    so that no device's RAM/CPU or network link overflows.
    """
    base_multipliers = {
        "L0_Linux_Mini": 1.5,       # 40 Gb/s TB4 bridge0 (10.0.0.8)
        "L1b_Mac_Mini_M2": 1.5,     # 40 Gb/s TB4 bridge0 (10.0.0.3)
        "L2_MacBook_Pro": 1.35,     # 40 Gb/s TB4 bridge0 (10.0.0.4) & Screen Lens Teacher
        "L5_MacBook_Air": 1.35,     # 40 Gb/s TB4 bridge0 (10.0.0.5) & M4 ANE Worker
        "L3_Linux_Head_Node": 1.25, # Dedicated LAN Head Node
        "L4_Linux_Tablet": 1.15,    # Isolated Debian 13 AVF VM (90%+ free RAM)
        "L6_Pixel_10_Pro_XL": 1.0,  # Tensor G5 NPU / Llama RPC :50052
    }

    raw_scores: Dict[str, float] = {}
    overloaded_nodes: List[str] = []
    tb4_candidates = ("L0_Linux_Mini", "L1b_Mac_Mini_M2", "L2_MacBook_Pro", "L5_MacBook_Air")

    for key, info in matrix.items():
        if info.get("status") != "ONLINE":
            continue
        used_pct = float(info.get("used_pct", 0.0))
        cpu_pct = float(info.get("cpu_used_pct", 0.0))
        avail_gb = float(info.get("available_gb", 0.0))

        if used_pct > 88.0 or cpu_pct > 90.0:
            overloaded_nodes.append(key)

        if key in base_multipliers and info.get("can_receive_offload", False):
            cpu_headroom_factor = max(0.1, 1.0 - (cpu_pct / 100.0))
            mult = base_multipliers[key]
            ip_str = str(info.get("ip", ""))
            if key in tb4_candidates and not (ip_str.startswith("10.0.0.") or ip_str.startswith("169.254.")):
                mult = 1.0  # Downgrade multiplier if TB4 fell back to LAN/Tailscale
            raw_scores[key] = round(avail_gb * cpu_headroom_factor * mult, 3)

    total_score = sum(raw_scores.values())
    dispatch_weights = {
        k: round((score / total_score) * 100.0, 1) if total_score > 0 else 0.0
        for k, score in sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)
    }

    gw = matrix.get("GW_Router", {})
    gw_healthy = gw.get("status") == "ONLINE" and float(gw.get("available_gb", 0.0)) >= 0.5

    return {
        "overflow_guard_active": True,
        "backpressure_status": "NOMINAL_ZERO_OVERFLOW" if not overloaded_nodes else f"THROTTLING_OVERLOADED:{','.join(overloaded_nodes)}",
        "gateway_wan_healthy": gw_healthy,
        "gateway_free_ram_gb": gw.get("available_gb", 0.0),
        "thunderbolt_40gbps_nodes_online": [
            k for k in tb4_candidates
            if matrix.get(k, {}).get("status") == "ONLINE"
            and (str(matrix.get(k, {}).get("ip", "")).startswith("10.0.0.") or str(matrix.get(k, {}).get("ip", "")).startswith("169.254."))
        ],
        "recommended_dispatch_weights_pct": dispatch_weights,
        "overloaded_nodes_throttled": overloaded_nodes,
    }


def _reap_remote_tty_duplicate_mcp() -> int:
    """
    Reaps duplicate MCP child servers spawned by remote-TTY `agy --dangerously-skip-permissions`
    sessions (e.g., from L7 Termius auto-reconnect) and SIGSTOPs the remote `agy` CLI process
    so the SSH session stays open without respawning 20+ duplicate MCP servers on L1.
    """
    import signal
    reaped = 0
    try:
        out = subprocess.check_output(["ps", "-eo", "pid,ppid,tty,stat,command"], text=True, timeout=2.0)
        remote_agy_pids = set()
        rows = []
        for line in out.splitlines()[1:]:
            parts = line.split(None, 4)
            if len(parts) == 5:
                pid, ppid, tty, stat, cmd = int(parts[0]), int(parts[1]), parts[2], parts[3], parts[4]
                rows.append((pid, ppid, tty, stat, cmd))
                if tty.startswith("ttys") and "/agy" in cmd and "--dangerously-skip-permissions" in cmd:
                    remote_agy_pids.add(pid)
                elif ppid == 1 and stat.startswith("T") and "/agy" in cmd and "--hub" in cmd:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        reaped += 1
                    except Exception:
                        pass
        for pid, ppid, tty, stat, cmd in rows:
            if ppid in remote_agy_pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    reaped += 1
                except Exception:
                    pass
        for apid in remote_agy_pids:
            try:
                os.kill(apid, signal.SIGSTOP)
            except Exception:
                pass
    except Exception:
        pass
    return reaped


def execute_sanctuary_actuation(matrix: Dict[str, Dict[str, Any]], overflow_guard: Dict[str, Any]) -> List[str]:
    """
    Enforces Rule #3 Host Sanctuary (>= 4.8 GB available / <= 80% used on L1),
    proactively compresses cold anonymous memory on L1 when headroom dips below 6.8 GB,
    re-probes L1 after actuation to verify recovery, and ranks all online peripheral nodes.
    """
    actions: List[str] = []
    reaped_mcp = _reap_remote_tty_duplicate_mcp()
    if reaped_mcp > 0:
        actions.append(f"Reaped {reaped_mcp} duplicate remote-TTY MCP / orphaned processes on L1.")

    l1 = matrix.get("L1_Mac_Node", {})
    l1_avail = float(l1.get("available_gb", 0.0))
    l1_rule1_avail = float(l1.get("rule1_avail_gb", 0.0))
    l1_used_pct = float(l1.get("used_pct", 0.0))

    tier1_linux = []
    tier2_secondary = []
    tier3_edge = []

    for lid, info in matrix.items():
        if lid in ("L1_Mac_Node", "GW_Router") or not info.get("can_receive_offload", False):
            continue
        entry = (lid, info["name"], info["available_gb"], info.get("ip", "mesh"), info.get("cpu_used_pct", 0.0))
        if lid in ("L0_Linux_Mini", "L3_Linux_Head_Node", "L4_Linux_Tablet"):
            tier1_linux.append(entry)
        elif lid in ("L1b_Mac_Mini_M2", "L2_MacBook_Pro", "L5_MacBook_Air"):
            tier2_secondary.append(entry)
        else:
            tier3_edge.append(entry)

    tier1_linux.sort(key=lambda x: x[2], reverse=True)
    tier2_secondary.sort(key=lambda x: x[2], reverse=True)
    tier3_edge.sort(key=lambda x: x[2], reverse=True)
    offload_targets = tier1_linux + tier2_secondary + tier3_edge

    if offload_targets:
        actions.append(
            f"Active Multi-Device Offload Roster ({len(offload_targets)} nodes ready): "
            + ", ".join(f"{t[0]} ({t[2]} GB avail, CPU {t[4]}%)" for t in offload_targets)
        )

    # Proactive actuation threshold at 6.8 GB (2.0 GB cushion above 4.8 GB sanctuary floor)
    if l1_avail < 6.8 or l1_used_pct > 71.5 or not l1.get("sanctuary_healthy", False):
        pre_avail = l1_avail
        pre_pct = l1_used_pct
        for pattern in ("continuous_10m_genetic_drafter_trainer.py", "app_accuracy_functionality_and_ai_integration_loop.py"):
            try:
                res = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
                if res.returncode == 0 and res.stdout.strip():
                    pids = res.stdout.strip().split()
                    for pid in pids:
                        subprocess.run(["renice", "+19", pid], capture_output=True)
            except Exception:
                pass

        try:
            import gc
            gc.collect()
        except Exception:
            pass

        if _warm_gguf_page_cache_and_compress_cold_anon():
            actions.append("Triggered Darwin VFS GGUF cache warm & XNU cold-anonymous page compression.")

        # Re-probe L1 after actuation to verify Rule #3 sanctuary recovery
        l1_after = probe_l1_mac_mini()
        matrix["L1_Mac_Node"] = l1_after
        overflow_guard.update(compute_network_overflow_guard(matrix))
        l1 = l1_after
        l1_avail = float(l1.get("available_gb", 0.0))
        l1_rule1_avail = float(l1.get("rule1_avail_gb", 0.0))
        actions.append(
            f"Re-probed L1 after sanctuary actuation: {pre_avail} GB ({pre_pct}% used) -> "
            f"{l1_rule1_avail} GB ({l1.get('used_pct')}% used, sanctuary_healthy={l1.get('sanctuary_healthy')})."
        )

    if l1.get("sanctuary_healthy", False):
        logger.info(
            f"✔ Host Sanctuary Healthy: {l1_rule1_avail} GB Rule-1 free "
            f"(Threshold >= {MIN_HOST_FREE_RAM_GB} GB, Used={l1.get('used_pct')}%, Pressure={l1.get('memory_pressure', 1)})."
        )
        actions.append(
            f"Host RAM sanctuary verified healthy ({l1_rule1_avail} GB Rule-1 free, Used={l1.get('used_pct')}%, Pressure={l1.get('memory_pressure', 1)}). "
            f"Network overflow guard: {overflow_guard.get('backpressure_status')}."
        )
    else:
        logger.warning(
            f"🚨 Rule #3 Sanctuary Warning after actuation: Host RAM is {l1_rule1_avail} GB (Used={l1.get('used_pct')}%)."
        )

    return actions


def run_governor_cycle() -> Dict[str, Any]:
    """Single complete concurrent scan, overflow guard computation, serialization, and actuation cycle."""
    t0 = time.time()
    matrix = scan_full_mesh_ram()
    overflow_guard = compute_network_overflow_guard(matrix)
    actions = execute_sanctuary_actuation(matrix, overflow_guard)
    duration_ms = round((time.time() - t0) * 1000, 2)

    total_mesh_ram = sum(float(info.get("total_gb", 0.0)) for info in matrix.values())
    total_mesh_avail = sum(float(info.get("available_gb", 0.0)) for info in matrix.values())
    peripheral_avail = total_mesh_avail - float(matrix.get("L1_Mac_Node", {}).get("available_gb", 0.0))
    total_mesh_cores = sum(int(info.get("cpu_cores", 0)) for info in matrix.values())
    online_nodes = sum(1 for info in matrix.values() if info.get("status") == "ONLINE")

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "epoch": time.time(),
        "cycle_duration_ms": duration_ms,
        "nodes_online": f"{online_nodes}/{len(matrix)}",
        "host_sanctuary_healthy": matrix.get("L1_Mac_Node", {}).get("sanctuary_healthy", False),
        "host_available_gb": matrix.get("L1_Mac_Node", {}).get("available_gb", 0.0),
        "host_rule1_avail_gb": matrix.get("L1_Mac_Node", {}).get("rule1_avail_gb", 0.0),
        "total_mesh_ram_gb": round(total_mesh_ram, 2),
        "total_mesh_available_gb": round(total_mesh_avail, 2),
        "peripheral_offload_headroom_gb": round(peripheral_avail, 2),
        "total_mesh_cpu_cores": total_mesh_cores,
        "network_overflow_guard": overflow_guard,
        "mesh_layers": matrix,
        "actions_taken": actions,
    }

    try:
        STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_JSON, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write state JSON: {e}")

    try:
        if OBS_MD.exists():
            l1 = matrix.get("L1_Mac_Node", {})
            obs_entry = (
                f"| {summary['timestamp']} | **RAM_Governor** | `10-Node Mesh Scan` | "
                f"L1: {l1.get('available_gb')}GB | L8: {matrix.get('L0_Linux_Mini', {}).get('available_gb')}GB | "
                f"L3: {matrix.get('L3_Linux_Head_Node', {}).get('available_gb')}GB | "
                f"Peripheral Headroom: {round(peripheral_avail, 1)}GB ({online_nodes}/{len(matrix)} Online) | "
                f"{'SANCTUARY_HEALTHY' if l1.get('sanctuary_healthy') else 'OFFLOAD_ACTIVE'} |\n"
            )
            with open(OBS_MD, "a", encoding="utf-8") as f:
                f.write(obs_entry)
    except Exception as e:
        logger.error(f"Failed to append to Obsidian: {e}")

    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lauburu Mesh RAM & CPU Sanctuary Governor Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a 24/7 background daemon")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds (default: 60)")
    parser.add_argument("--single-cycle", action="store_true", help="Execute single cycle and exit")
    args = parser.parse_args()

    if args.daemon:
        logger.info(f"Starting 24/7 Continuous RAM Sanctuary Governor Daemon (Interval: {args.interval}s)...")
        while True:
            try:
                summary = run_governor_cycle()
                l1_avail = summary.get("host_available_gb", 0.0)
                tot_mesh = summary.get("total_mesh_available_gb", 0.0)
                logger.info(f"Cycle completed: Host={l1_avail}GB, TotalMesh={tot_mesh}GB. Sleeping {args.interval}s.")
            except KeyboardInterrupt:
                logger.info("Governor daemon interrupted by user. Exiting.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in governor cycle: {e}")
            time.sleep(args.interval)
    else:
        res = run_governor_cycle()
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
