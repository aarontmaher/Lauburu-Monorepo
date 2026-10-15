#!/usr/bin/env python3
"""
Lauburu Sovereign Mesh — Non-Overloading Live Network & Hardware Monitor (`netmon`)
===================================================================================
Canonical CLI (`~/.local/bin/netmon` -> `06_scripts_and_tooling/network/dual_network_monitor.py`)

Key Architectural & Memory Governance Invariants:
1. NON-OVERLOADING GLANCES API POLLING:
   - Strictly FORBIDS `/api/3/all` and `/api/4/all` (which walk all PIDs in `/proc` and
     caused 6.91s latency + 449.3 MB RAM bloat on L3).
   - Queries lightweight modular endpoints ONLY: `/quicklook`, `/mem`, `/load`, `/network`
     (plus `/fs` cached on a 60s TTL).
   - Enforces a 1.5s connect/read timeout with Tailscale (`100.x.y.z`) and TB4 (`10.0.0.x`)
     prioritized ahead of subnet-dependent LAN (`192.168.8.x`) IPs.
   - Implements an Adaptive Overload Circuit Breaker: when `cpu_pct > 80%` or `mem_pct > 88%`,
     marks `overload_guard: THROTTLED_3X` and backs off secondary probes.
2. NORMAL SYSTEM RAM vs UNIFIED METAL VRAM vs DISCRETE GPU VRAM:
   - Explicitly tracks `memory_class`, `normal_ram_gb`, `vram_gb`, and `bandwidth_gbps` per node
     so CPU-only DDR4 nodes (`L3` 16GB, `L8` 32GB, `L4` 8GB, `L7` 12GB — 0 GB dedicated VRAM)
     are never misclassified as GPU VRAM pools.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def _detect_local_ips() -> set[str]:
    ips = {"127.0.0.1", "::1"}
    try:
        out = subprocess.check_output(["ifconfig"], text=True, stderr=subprocess.DEVNULL, timeout=1.5)
        for m in re.findall(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out):
            ips.add(m)
    except Exception:
        pass
    try:
        out = subprocess.check_output(["ip", "-4", "addr"], text=True, stderr=subprocess.DEVNULL, timeout=1.5)
        for m in re.findall(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out):
            ips.add(m)
    except Exception:
        pass
    return ips


LOCAL_IPS = _detect_local_ips()
HOSTNAME = socket.gethostname().lower()


@dataclass
class NodeSpec:
    layer: str
    name: str
    role: str
    tailscale_ip: Optional[str]
    lan_ip: Optional[str]
    tb4_ip: Optional[str]
    wg_ip: Optional[str]
    bt_mac: str
    glances_api_ver: Optional[int]  # 4 for L1/L5/L8, 3 for L3, None if no Glances daemon
    memory_class: str               # UNIFIED_METAL_VRAM | DISCRETE_VRAM_PLUS_RAM | NORMAL_RAM_ONLY_ZERO_VRAM | EDGE_LPDDR5X_NPU | ROUTER_EMBEDDED
    normal_ram_gb: float
    vram_gb: float                  # Dedicated or Unified Metal/NPU VRAM usable for GPU/NPU kernels
    bandwidth_gbps: float
    cpu_threads_cap: int            # Max threads allowed for GGML_BACKEND_CPU to prevent overload
    preferred_sharding_role: str
    extra_ports: List[int] = field(default_factory=list)


CANONICAL_NODES: List[NodeSpec] = [
    NodeSpec(
        layer="GW",
        name="GL.iNet Flint 2 (OpenWrt)",
        role="Multi-WAN Router & DNS/WireGuard Anchor",
        tailscale_ip=None,
        lan_ip="192.168.8.1",
        tb4_ip=None,
        wg_ip="10.1.0.1",
        bt_mac="94:83:c4:00:00:01",
        glances_api_ver=None,
        memory_class="ROUTER_EMBEDDED (0 VRAM)",
        normal_ram_gb=2.0,
        vram_gb=0.0,
        bandwidth_gbps=12.8,
        cpu_threads_cap=2,
        preferred_sharding_role="Network Routing Only (No LLM Shards)",
        extra_ports=[80, 22, 53],
    ),
    NodeSpec(
        layer="L1",
        name="Mac Mini M4 Pro (24GB)",
        role="Primary Metal Sanctuary & Prefill Master",
        tailscale_ip="100.119.199.76",
        lan_ip="192.168.8.132",
        tb4_ip="10.0.0.1",
        wg_ip="10.1.0.2",
        bt_mac="d0:11:e5:5e:fc:c7",
        glances_api_ver=4,
        memory_class="UNIFIED_METAL_VRAM (24GB)",
        normal_ram_gb=24.0,
        vram_gb=20.0,
        bandwidth_gbps=273.0,
        cpu_threads_cap=10,
        preferred_sharding_role="Disaggregated Prefill Master + Dense Metal Decode",
        extra_ports=[61208, 8080, 8081, 8087, 50052],
    ),
    NodeSpec(
        layer="L1b",
        name="Mac Mini M2 Pro (16GB)",
        role="Secondary Metal Compute Node",
        tailscale_ip="100.87.131.34",
        lan_ip=None,
        tb4_ip=None,
        wg_ip=None,
        bt_mac="00:00:00:00:01:0b",
        glances_api_ver=4,
        memory_class="UNIFIED_METAL_VRAM (16GB)",
        normal_ram_gb=16.0,
        vram_gb=12.0,
        bandwidth_gbps=200.0,
        cpu_threads_cap=8,
        preferred_sharding_role="Auxiliary Metal Ring Shard",
        extra_ports=[61208, 22],
    ),
    NodeSpec(
        layer="L2",
        name="MacBook Pro Intel i7 (16GB+4GB)",
        role="Desktop Automation Target & TB4 Bridge",
        tailscale_ip="100.88.85.69",
        lan_ip="192.168.8.149",
        tb4_ip="10.0.0.2",
        wg_ip="10.1.0.5",
        bt_mac="ac:de:48:00:11:22",
        glances_api_ver=4,
        memory_class="DISCRETE_4GB_VRAM+16GB_RAM",
        normal_ram_gb=16.0,
        vram_gb=4.0,
        bandwidth_gbps=192.0,
        cpu_threads_cap=6,
        preferred_sharding_role="4GB Metal GPU Layers + 8GB DDR4 CPU Assist",
        extra_ports=[61208, 50052, 22],
    ),
    NodeSpec(
        layer="L3",
        name="Linux Ubuntu Ryzen 7 5700U (16GB)",
        role="Neo4j 5.26.32 Graph Master & Container Host",
        tailscale_ip="100.101.39.98",
        lan_ip="192.168.8.225",
        tb4_ip=None,
        wg_ip="10.1.0.3",
        bt_mac="dc:41:a9:fb:eb:66",
        glances_api_ver=3,
        memory_class="NORMAL_RAM_ONLY (0 VRAM)",
        normal_ram_gb=16.0,
        vram_gb=0.0,
        bandwidth_gbps=25.6,
        cpu_threads_cap=7,
        preferred_sharding_role="Neo4j Graph + Qdrant + AVX2 Sparse MoE / Draft Only",
        extra_ports=[61208, 7474, 7687, 6333, 50052, 22],
    ),
    NodeSpec(
        layer="L4",
        name="Lenovo TB351FU Tablet (8GB)",
        role="Tatami Kiosk & Biometric HUD",
        tailscale_ip="100.99.210.89",
        lan_ip="192.168.8.176",
        tb4_ip=None,
        wg_ip="10.1.0.7",
        bt_mac="b4:f1:da:5f:c9:dd",
        glances_api_ver=None,
        memory_class="NORMAL_RAM_ONLY (0 VRAM)",
        normal_ram_gb=8.0,
        vram_gb=0.0,
        bandwidth_gbps=17.0,
        cpu_threads_cap=4,
        preferred_sharding_role="Visual Kiosk Consumer Only (0 LLM Layers)",
        extra_ports=[5555, 8022],
    ),
    NodeSpec(
        layer="L5",
        name="MacBook Air M4 (16GB)",
        role="Zero-Fan Metal Sanctuary & EmbeddingGemma 2 MRL",
        tailscale_ip="100.121.202.34",
        lan_ip="192.168.8.198",
        tb4_ip="10.0.0.5",
        wg_ip="10.1.0.6",
        bt_mac="80:65:7c:37:52:4c",
        glances_api_ver=4,
        memory_class="UNIFIED_METAL_VRAM (16GB)",
        normal_ram_gb=16.0,
        vram_gb=11.0,
        bandwidth_gbps=120.0,
        cpu_threads_cap=8,
        preferred_sharding_role="EmbeddingGemma 2 (:8087) + Metal Decode Ring Shard",
        extra_ports=[61208, 8087, 3035, 50052],
    ),
    NodeSpec(
        layer="L6",
        name="Pixel 10 Pro XL Tensor G5 (16GB)",
        role="Pocket Nomad Courier & AVF Debian VM",
        tailscale_ip="100.114.215.68",
        lan_ip="192.168.8.213",
        tb4_ip=None,
        wg_ip="10.1.0.8",
        bt_mac="30:e0:44:6d:18:ec",
        glances_api_ver=None,
        memory_class="EDGE_LPDDR5X_NPU (16GB)",
        normal_ram_gb=16.0,
        vram_gb=6.5,
        bandwidth_gbps=68.0,
        cpu_threads_cap=6,
        preferred_sharding_role="LiteRT/MediaPipe EmbeddingGemma 2 + Speculative Draft",
        extra_ports=[8022, 22, 5555, 50052],
    ),
    NodeSpec(
        layer="L7",
        name="Samsung Galaxy S20+ (12GB)",
        role="Always-On USB/ADB Sensor & Shizuku Bridge",
        tailscale_ip="100.78.206.96",
        lan_ip="192.168.8.130",
        tb4_ip=None,
        wg_ip="10.1.0.4",
        bt_mac="e0:cb:bc:91:df:c7",
        glances_api_ver=None,
        memory_class="NORMAL_RAM_ONLY (0 VRAM)",
        normal_ram_gb=12.0,
        vram_gb=0.0,
        bandwidth_gbps=44.0,
        cpu_threads_cap=4,
        preferred_sharding_role="ADB/Screen Lens Sensor & EmbeddingGemma 2 128d-256d",
        extra_ports=[8022, 5555],
    ),
    NodeSpec(
        layer="L8",
        name="Intel i7-8700B Mac Mini (32GB)",
        role="High-Capacity DDR4 Context & AVX2 CPU Worker",
        tailscale_ip="100.121.247.8",
        lan_ip="192.168.8.180",
        tb4_ip="10.0.0.8",
        wg_ip="10.1.0.9",
        bt_mac="f0:18:98:aa:bb:cc",
        glances_api_ver=4,
        memory_class="NORMAL_RAM_ONLY (0 VRAM)",
        normal_ram_gb=32.0,
        vram_gb=0.0,
        bandwidth_gbps=34.1,
        cpu_threads_cap=10,
        preferred_sharding_role="24GB DDR4 KV-Cache Store + AVX2 Q4_K_M Sparse/CPU Shards",
        extra_ports=[61208, 50052, 22],
    ),
]


# In-memory TTL cache for disk `/fs` and adaptive overload backoff state
_FS_TTL_CACHE: Dict[str, Tuple[float, Optional[float]]] = {}
_OVERLOAD_BACKOFF_STATE: Dict[str, int] = {}


def _is_node_local(spec: NodeSpec) -> bool:
    for ip in (spec.tailscale_ip, spec.lan_ip, spec.tb4_ip, spec.wg_ip):
        if ip and ip in LOCAL_IPS:
            return True
    if spec.layer == "L6" and (
        "100.80.64.5" in LOCAL_IPS
        or "10.85.23.53" in LOCAL_IPS
        or os.path.exists("/data/data/com.termux")
    ):
        return True
    if spec.layer == "L5" and ("air" in HOSTNAME or "100.121.202.34" in LOCAL_IPS):
        return True
    if spec.layer == "L1" and ("mini" in HOSTNAME and "100.119.199.76" in LOCAL_IPS):
        return True
    return False


def _tcp_fast_check(host: str, port: int, timeout: float = 0.30) -> Optional[float]:
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return round((time.perf_counter() - t0) * 1000.0, 2)
    except Exception:
        return None


def _glances_base_urls(spec: NodeSpec) -> List[Tuple[str, int, str]]:
    """Returns list of (host, port, base_url) ordered by fastest reachable transport."""
    if not spec.glances_api_ver:
        return []
    ver = spec.glances_api_ver
    candidates: List[Tuple[str, int, str]] = []
    if _is_node_local(spec):
        candidates.append(("127.0.0.1", 61208, f"http://127.0.0.1:61208/api/{ver}"))
    if spec.tailscale_ip:
        candidates.append((spec.tailscale_ip, 61208, f"http://{spec.tailscale_ip}:61208/api/{ver}"))
    if spec.tb4_ip:
        candidates.append((spec.tb4_ip, 61208, f"http://{spec.tb4_ip}:61208/api/{ver}"))
    if spec.lan_ip:
        candidates.append((spec.lan_ip, 61208, f"http://{spec.lan_ip}:61208/api/{ver}"))
    return candidates


def _fetch_json(url: str, timeout: float = 1.1) -> Optional[Any]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Lauburu-NetMon/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None


def _poll_glances_lightweight(spec: NodeSpec) -> Optional[Dict[str, Any]]:
    """
    Polls Glances using ONLY lightweight modular endpoints (`/quicklook`, `/mem`, `/load`, `/network`)
    and caches `/fs` for 60s. Never calls `/all` or `/processlist`.
    """
    candidates = _glances_base_urls(spec)
    if not candidates:
        return None

    skip_count = _OVERLOAD_BACKOFF_STATE.get(spec.layer, 0)
    if skip_count > 0:
        _OVERLOAD_BACKOFF_STATE[spec.layer] = skip_count - 1

    for host, port, base in candidates:
        if host != "127.0.0.1" and _tcp_fast_check(host, port, timeout=0.30) is None:
            continue
        t0 = time.perf_counter()
        ql = _fetch_json(f"{base}/quicklook", timeout=1.1)
        if not isinstance(ql, dict) or ("cpu" not in ql and "mem" not in ql):
            continue
        rtt_ms = (time.perf_counter() - t0) * 1000.0

        cpu_pct = float(ql.get("cpu", 0.0))
        mem_pct = float(ql.get("mem", 0.0))
        swap_pct = float(ql.get("swap", 0.0))
        cpu_name = ql.get("cpu_name")

        overloaded = cpu_pct > 80.0 or mem_pct > 88.0
        if overloaded:
            _OVERLOAD_BACKOFF_STATE[spec.layer] = 2

        mem_data = _fetch_json(f"{base}/mem", timeout=0.9) if not overloaded else None
        load_data = _fetch_json(f"{base}/load", timeout=0.9) if not overloaded else None
        net_data = _fetch_json(f"{base}/network", timeout=0.9) if not overloaded else None

        now = time.time()
        cached_fs = _FS_TTL_CACHE.get(spec.layer)
        if cached_fs and (now - cached_fs[0] < 60.0):
            disk_pct = cached_fs[1]
        elif not overloaded:
            fs_data = _fetch_json(f"{base}/fs", timeout=0.9)
            disk_pct = None
            if isinstance(fs_data, list) and fs_data:
                root_fs = next((f for f in fs_data if f.get("mnt_point") in ("/", "/System/Volumes/Data")), fs_data[0])
                if isinstance(root_fs, dict) and root_fs.get("percent") is not None:
                    disk_pct = float(root_fs["percent"])
            _FS_TTL_CACHE[spec.layer] = (now, disk_pct)
        else:
            disk_pct = cached_fs[1] if cached_fs else None

        mem_used_gb = None
        mem_total_gb = spec.normal_ram_gb
        mem_avail_gb = None
        if isinstance(mem_data, dict) and mem_data.get("total"):
            mem_total_gb = round(float(mem_data["total"]) / (1024**3), 2)
            mem_used_gb = round(float(mem_data.get("used", 0)) / (1024**3), 2)
            mem_avail_gb = round(float(mem_data.get("available", mem_data.get("free", 0))) / (1024**3), 2)
        else:
            mem_used_gb = round(spec.normal_ram_gb * (mem_pct / 100.0), 2)
            mem_avail_gb = round(spec.normal_ram_gb - mem_used_gb, 2)

        load_1m = None
        if isinstance(load_data, dict) and load_data.get("min1") is not None:
            load_1m = round(float(load_data["min1"]), 2)
        elif ql.get("load") is not None:
            load_1m = float(ql["load"]) if isinstance(ql["load"], (int, float)) else None

        rx_kbps = 0.0
        tx_kbps = 0.0
        if isinstance(net_data, list):
            for iface in net_data:
                if not isinstance(iface, dict):
                    continue
                name = str(iface.get("interface_name", ""))
                if name.startswith(("lo", "utun", "llw", "awdl", "veth", "docker", "br-")):
                    continue
                t_upd = float(iface.get("time_since_update") or 1.0)
                rx_rate = iface.get("bytes_recv_rate_per_sec", (iface.get("rx", 0) or 0) / max(t_upd, 0.1))
                tx_rate = iface.get("bytes_sent_rate_per_sec", (iface.get("tx", 0) or 0) / max(t_upd, 0.1))
                rx_kbps += float(rx_rate or 0.0) / 1024.0
                tx_kbps += float(tx_rate or 0.0) / 1024.0

        return {
            "endpoint": f"{base}/quicklook",
            "rtt_ms": round(rtt_ms, 2),
            "cpu_pct": round(cpu_pct, 1),
            "cpu_name": cpu_name,
            "mem_pct": round(mem_pct, 1),
            "mem_used_gb": mem_used_gb,
            "mem_avail_gb": mem_avail_gb,
            "mem_total_gb": mem_total_gb,
            "swap_pct": round(swap_pct, 1),
            "load_1m": load_1m,
            "disk_pct": disk_pct,
            "rx_kbps": round(rx_kbps, 1),
            "tx_kbps": round(tx_kbps, 1),
            "overload_guard": "THROTTLED_3X" if overloaded else "OK_MODULAR",
        }
    return None


def _tcp_probe(ip: Optional[str], ports: List[int], timeout: float = 0.25) -> Tuple[bool, Optional[float], List[int]]:
    if not ip:
        return False, None, []
    open_ports: List[int] = []
    best_rtt: Optional[float] = None
    for port in ports[:2]:
        rtt = _tcp_fast_check(ip, port, timeout=timeout)
        if rtt is not None:
            open_ports.append(port)
            if best_rtt is None or rtt < best_rtt:
                best_rtt = rtt
            break
    return (len(open_ports) > 0), best_rtt, open_ports


def collect_node_snapshot(spec: NodeSpec) -> Dict[str, Any]:
    is_local = _is_node_local(spec)
    glances_info = _poll_glances_lightweight(spec)

    probe_ports = spec.extra_ports or [22, 80, 61208]
    ts_ok, ts_rtt, _ = _tcp_probe(spec.tailscale_ip, probe_ports)
    if spec.layer == "L6" and not ts_ok:
        ts_ok, ts_rtt, _ = _tcp_probe("100.80.64.5", [22])
    lan_ok, lan_rtt, _ = _tcp_probe(spec.lan_ip, probe_ports)
    tb4_ok, tb4_rtt, _ = _tcp_probe(spec.tb4_ip, [61208, 22])

    online = bool(is_local or glances_info is not None or ts_ok or lan_ok or tb4_ok)

    active_transports: List[str] = []
    if is_local:
        active_transports.append("LOCAL")
    if tb4_ok:
        active_transports.append(f"TB4({spec.tb4_ip})")
    if ts_ok or (glances_info and spec.tailscale_ip and spec.tailscale_ip in glances_info["endpoint"]):
        active_transports.append(f"TS({spec.tailscale_ip})")
    if lan_ok or (glances_info and spec.lan_ip and spec.lan_ip in glances_info["endpoint"]):
        active_transports.append(f"LAN({spec.lan_ip})")

    best_rtt = None
    for candidate in (
        tb4_rtt,
        ts_rtt,
        lan_rtt,
        glances_info["rtt_ms"] if glances_info else None,
    ):
        if candidate is not None and (best_rtt is None or candidate < best_rtt):
            best_rtt = candidate

    mem_avail_gb = glances_info["mem_avail_gb"] if glances_info else None
    if spec.vram_gb > 0:
        if mem_avail_gb is not None:
            usable_vram_gb = round(min(spec.vram_gb, max(0.0, mem_avail_gb - 2.5)), 2)
        else:
            usable_vram_gb = spec.vram_gb
        usable_cpu_ram_gb = round(max(0.0, (mem_avail_gb or spec.normal_ram_gb) - 3.0), 2)
    else:
        usable_vram_gb = 0.0
        usable_cpu_ram_gb = round(max(0.0, (mem_avail_gb or (spec.normal_ram_gb * 0.6)) - 2.5), 2)

    return {
        "layer": spec.layer,
        "name": spec.name,
        "role": spec.role,
        "online": online,
        "is_local": is_local,
        "transports": active_transports,
        "tailscale_ip": spec.tailscale_ip,
        "lan_ip": spec.lan_ip,
        "tb4_ip": spec.tb4_ip,
        "wg_ip": spec.wg_ip,
        "bt_mac": spec.bt_mac,
        "best_rtt_ms": best_rtt,
        "memory_architecture": {
            "memory_class": spec.memory_class,
            "normal_ram_gb": spec.normal_ram_gb,
            "dedicated_or_unified_vram_gb": spec.vram_gb,
            "usable_vram_now_gb": usable_vram_gb,
            "usable_normal_ram_now_gb": usable_cpu_ram_gb,
            "bandwidth_gbps": spec.bandwidth_gbps,
            "cpu_threads_cap": spec.cpu_threads_cap,
            "preferred_sharding_role": spec.preferred_sharding_role,
        },
        "telemetry": glances_info or {
            "endpoint": "tcp-probe-only",
            "rtt_ms": best_rtt,
            "cpu_pct": None,
            "mem_pct": None,
            "mem_used_gb": None,
            "mem_avail_gb": None,
            "mem_total_gb": spec.normal_ram_gb,
            "swap_pct": None,
            "load_1m": None,
            "disk_pct": None,
            "rx_kbps": None,
            "tx_kbps": None,
            "overload_guard": "PASSIVE_TCP_ONLY",
        },
    }


def collect_mesh_snapshot() -> Dict[str, Any]:
    t0 = time.perf_counter()
    results_by_layer: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(CANONICAL_NODES)) as pool:
        futs = {pool.submit(collect_node_snapshot, spec): spec.layer for spec in CANONICAL_NODES}
        for fut in as_completed(futs):
            layer = futs[fut]
            try:
                results_by_layer[layer] = fut.result()
            except Exception as exc:
                results_by_layer[layer] = {"layer": layer, "online": False, "error": str(exc)}

    ordered = [results_by_layer[s.layer] for s in CANONICAL_NODES if s.layer in results_by_layer]
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    total_normal_ram = sum(s.normal_ram_gb for s in CANONICAL_NODES if s.layer != "GW")
    total_vram = sum(s.vram_gb for s in CANONICAL_NODES if s.layer != "GW")
    online_nodes = [n for n in ordered if n.get("online")]
    online_vram = sum(n["memory_architecture"]["dedicated_or_unified_vram_gb"] for n in online_nodes)
    online_normal_ram = sum(n["memory_architecture"]["normal_ram_gb"] for n in online_nodes)

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": HOSTNAME,
        "local_ips": sorted(LOCAL_IPS),
        "poll_duration_ms": elapsed_ms,
        "polling_policy": "NON_OVERLOADING_MODULAR_GLANCES (quicklook+mem+load+network; /all FORBIDDEN)",
        "summary": {
            "nodes_online": len(online_nodes),
            "nodes_total": len(ordered),
            "fleet_physical_ram_gb": total_normal_ram,
            "fleet_true_vram_gb": total_vram,
            "online_normal_ram_gb": online_normal_ram,
            "online_true_vram_gb": online_vram,
        },
        "nodes": ordered,
    }


def render_table(snapshot: Dict[str, Any]) -> Table:
    s = snapshot["summary"]
    title = (
        f"LAUBURU SOVEREIGN NETMON v2.0 | Host: {snapshot['host']} | "
        f"Online: {s['nodes_online']}/{s['nodes_total']} | "
        f"Online Normal RAM: {s['online_normal_ram_gb']:.0f}GB | "
        f"Online True VRAM: {s['online_true_vram_gb']:.1f}GB | "
        f"Poll: {snapshot['poll_duration_ms']:.0f}ms"
    )
    table = Table(title=title, box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Layer", style="bold cyan", no_wrap=True)
    table.add_column("Node", style="white", no_wrap=True)
    table.add_column("State", no_wrap=True)
    table.add_column("Active Transports", style="magenta", no_wrap=True)
    table.add_column("RTT", justify="right", no_wrap=True)
    table.add_column("CPU%", justify="right", no_wrap=True)
    table.add_column("RAM Used/Tot", justify="right", no_wrap=True)
    table.add_column("Memory Class (RAM vs VRAM)", style="yellow", no_wrap=True)
    table.add_column("VRAM Usable", justify="right", style="green", no_wrap=True)
    table.add_column("Guard / API", style="dim", no_wrap=True)

    for n in snapshot["nodes"]:
        tel = n.get("telemetry", {})
        mem_arch = n.get("memory_architecture", {})
        state = "[bold green]ONLINE[/]" if n.get("online") else "[dim red]OFFLINE[/]"
        transports = ", ".join(n.get("transports", [])) or f"BT:{n.get('bt_mac', '-')}"
        rtt = f"{n['best_rtt_ms']:.1f}ms" if n.get("best_rtt_ms") is not None else "-"
        cpu = f"{tel['cpu_pct']:.1f}%" if tel.get("cpu_pct") is not None else "-"
        if tel.get("mem_used_gb") is not None:
            ram_str = f"{tel['mem_used_gb']:.1f}/{tel['mem_total_gb']:.0f}GB ({tel['mem_pct']:.0f}%)"
        else:
            ram_str = f"-/{mem_arch.get('normal_ram_gb', 0):.0f}GB"
        vram_usable = f"{mem_arch.get('usable_vram_now_gb', 0.0):.1f}GB" if mem_arch.get("dedicated_or_unified_vram_gb", 0) > 0 else "0GB (CPU-RAM)"
        guard = tel.get("overload_guard", "-")
        table.add_row(
            n["layer"],
            n["name"],
            state,
            transports,
            rtt,
            cpu,
            ram_str,
            mem_arch.get("memory_class", "-"),
            vram_usable,
            guard,
        )
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description="Lauburu Non-Overloading Multi-Transport & RAM/VRAM Monitor (netmon)")
    parser.add_argument("--once", action="store_true", help="Run a single non-overloading poll and exit")
    parser.add_argument("--json", action="store_true", help="Output structured JSON telemetry")
    parser.add_argument("--interval", type=float, default=5.0, help="Refresh interval in seconds (min 2.0s to prevent overload)")
    args = parser.parse_args()

    interval = max(2.0, args.interval)

    if args.once or args.json:
        snap = collect_mesh_snapshot()
        if args.json:
            print(json.dumps(snap, indent=2))
            return 0
        if HAS_RICH:
            Console(width=165).print(render_table(snap))
        else:
            print(json.dumps(snap, indent=2))
        return 0

    if not HAS_RICH:
        snap = collect_mesh_snapshot()
        print(json.dumps(snap, indent=2))
        return 0

    console = Console()
    with Live(render_table(collect_mesh_snapshot()), console=console, refresh_per_second=1) as live:
        try:
            while True:
                time.sleep(interval)
                live.update(render_table(collect_mesh_snapshot()))
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    sys.exit(main())
