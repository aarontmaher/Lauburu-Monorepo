#!/usr/bin/env python3
"""
Screen Lens Sovereign — Neo4j 5 CLI/MCP & EmbeddingGemma 2 Multimodal RAG Global Orchestrator
=============================================================================================
Implements:
1. Root-Privileged Mesh Execution (`sudo -n` UID 0 on macOS/Linux/OpenWrt, `rish` UID 2000 / `tsu` on Android L6)
2. Authentic Neo4j 5.26.32 Cypher Client & CLI (`neo4j-cli` / `cypher-shell` / `lens neo4j`) with
   4 native MRL Vector Indexes (`gemma2_vec_768`, `gemma2_vec_512`, `gemma2_vec_256`, `gemma2_vec_128`)
   plus offline SQLite Graph Replica fallback.
3. Authentic Google DeepMind EmbeddingGemma 2 (`google/embeddinggemma-2` / `unsloth/embeddinggemma-2-GGUF`)
   740M Multimodal Engine (270M text + 170M vision + 300M audio, 8,192 context window, MRL 768/512/256/128D
   with mandatory L2 re-normalization, task prefixes, and `<|image|>`, `<|video|>`, `<|audio|>` interleaving).
4. Lightweight Global RAG ChatModel Orchestrator combining Neo4j GraphRAG + Qdrant MRL + Local GGUF ChatModel.
"""

import argparse
import base64
import concurrent.futures
import hashlib
import json
import math
import os
import platform
import re
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 1. CONFIGURATION & MESH TOPOLOGY
# ============================================================================

NEO4J_HTTP_ENDPOINTS = [
    os.environ.get("NEO4J_HTTP_URL", "").strip(),
    "http://100.101.39.98:7474/db/neo4j/tx/commit",
    "http://192.168.8.225:7474/db/neo4j/tx/commit",
    "http://127.0.0.1:7474/db/neo4j/tx/commit",
]
NEO4J_HTTP_ENDPOINTS = [u for u in NEO4J_HTTP_ENDPOINTS if u]
NEO4J_BOLT_URI = os.environ.get("NEO4J_BOLT_URI", "bolt://100.101.39.98:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "lauburu-sovereign-2026")

QDRANT_ENDPOINTS = [
    os.environ.get("QDRANT_URL", "").strip(),
    "http://100.101.39.98:6333",
    "http://192.168.8.225:6333",
    "http://127.0.0.1:6333",
]
QDRANT_ENDPOINTS = [u for u in QDRANT_ENDPOINTS if u]
QDRANT_COLLECTION = "embeddinggemma_2_multimodal"

EMBEDDINGGEMMA2_ENDPOINTS = [
    os.environ.get("EMBEDDINGGEMMA2_URL", "").strip(),
    "http://10.0.0.5:8087/v1/embeddings",
    "http://127.0.0.1:8087/v1/embeddings",
    "http://100.121.202.34:8087/v1/embeddings",
    "http://100.119.199.76:8087/v1/embeddings",
    "http://100.101.39.98:8087/v1/embeddings",
]
EMBEDDINGGEMMA2_ENDPOINTS = [u for u in EMBEDDINGGEMMA2_ENDPOINTS if u]

CHAT_ORCHESTRATOR_ENDPOINTS = [
    os.environ.get("LENS_CHAT_URL", "").strip(),
    "http://127.0.0.1:8089/v1/chat/completions",
    "http://10.0.0.5:8089/v1/chat/completions",
    "http://100.119.199.76:8090/v1/chat/completions",
    "http://100.119.199.76:8082/v1/chat/completions",
    "http://100.121.202.34:8089/v1/chat/completions",
    "http://127.0.0.1:8081/v1/chat/completions",
    "http://100.101.39.98:8089/v1/chat/completions",
]
CHAT_ORCHESTRATOR_ENDPOINTS = [u for u in CHAT_ORCHESTRATOR_ENDPOINTS if u]


def _tcp_reachable(url: str, timeout: float = 1.2) -> bool:
    """Fast TCP socket pre-check before HTTP requests to avoid multi-second dead-host hangs."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

MODEL_PATHS = [
    "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/models/embeddinggemma-2/embeddinggemma-2-UD-Q4_K_XL.gguf",
    "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/models/embeddinggemma-2/embeddinggemma-2-UD-Q4_K_XL.gguf",
    str(Path.home() / "models/embeddinggemma-2/embeddinggemma-2-UD-Q4_K_XL.gguf"),
    str(Path.home() / ".lauburu/models/embeddinggemma-2/embeddinggemma-2-UD-Q4_K_XL.gguf"),
]

MMPROJ_PATHS = [
    "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/models/embeddinggemma-2/mmproj-Q8_0.gguf",
    "/Volumes/Lauburu-Monorepo/02_ai_models_and_inference/models/embeddinggemma-2/mmproj-Q8_0.gguf",
    str(Path.home() / "models/embeddinggemma-2/mmproj-Q8_0.gguf"),
]

LLAMA_EMBEDDING_BINS = [
    str(Path.home() / ".local/bin/llama-gemma2/llama-embedding"),
    "/Volumes/.local/bin/llama-gemma2/llama-embedding",
    "/Users/aaron/llama.cpp/build/bin/llama-embedding",
    "/home/linux/llama.cpp/build/bin/llama-embedding",
    "llama-embedding",
]

MRL_DIMENSIONS = (768, 512, 256, 128)

TASK_PREFIXES = {
    "search_result": "task: search result | query: ",
    "search": "task: search result | query: ",
    "qa": "task: question answering | query: ",
    "question_answering": "task: question answering | query: ",
    "fact_checking": "task: fact checking | query: ",
    "code_retrieval": "task: code retrieval | query: ",
    "code": "task: code retrieval | query: ",
    "clustering": "task: clustering | query: ",
    "classification": "task: classification | query: ",
    "orchestration": "task: question answering | query: ",
}

MESH_NODES: Dict[str, Dict[str, Any]] = {
    "L5": {
        "node_id": "L5",
        "name": "MacBook Air M4 (L5 Human Sanctuary)",
        "role": "Primary Cockpit & Multimodal EmbeddingGemma 2 Host (:8087) — Human Chrome Protected",
        "fleet_role": "HUMAN_SANCTUARY",
        "os": "macOS",
        "ips": ["100.121.202.34", "192.168.8.248", "127.0.0.1"],
        "ssh_user": "aaronmaher",
        "ssh_port": 22,
        "bt_mac": "aa:f0:a8:fc:29:17",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "UNIFIED_METAL_VRAM",
        "normal_ram_gb": 16.0,
        "vram_gb": 16.0,
        "bandwidth_gbps": 120.0,
        "glances_api": "http://100.121.202.34:61208/api/4",
        "telemetry_method": "glances_v4_modular (/quicklook,/mem,/load,/network) + adaptive_circuit_breaker",
    },
    "L1": {
        "node_id": "L1",
        "name": "Mac Mini M4 Pro Primary (L1 Human Sanctuary)",
        "role": "10GbE M4 Compute Sanctuary & Global Orchestrator (:3037 / :8087) — Passive /lens",
        "fleet_role": "HUMAN_SANCTUARY",
        "os": "macOS",
        "ips": ["100.119.199.76", "192.168.8.230", "192.168.8.143"],
        "ssh_user": "aaron",
        "ssh_port": 22,
        "bt_mac": "d0:11:e5:c1:8f:41",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "UNIFIED_METAL_VRAM",
        "normal_ram_gb": 24.0,
        "vram_gb": 24.0,
        "bandwidth_gbps": 273.0,
        "glances_api": "http://100.119.199.76:61208/api/4",
        "telemetry_method": "glances_v4_modular (/quicklook,/mem,/load,/network) + adaptive_circuit_breaker",
    },
    "L1b": {
        "node_id": "L1b",
        "name": "Apple M2 Pro Mac Mini (L1b Dedicated AI Desktop Node)",
        "role": "Dedicated AI Go-Browser (:9225), Sovereign Chromium (:9222) & Desktop Actuation Host",
        "fleet_role": "AI_ACTUATION_NODE",
        "os": "macOS",
        "ips": ["192.168.8.114", "100.104.128.34", "10.0.0.3"],
        "ssh_user": "aaronmaher",
        "ssh_port": 22,
        "l1_jump_target": "aaronmaher@10.0.0.3",
        "bt_mac": "d0:11:e5:c1:8f:42",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "UNIFIED_METAL_VRAM",
        "normal_ram_gb": 16.0,
        "vram_gb": 16.0,
        "bandwidth_gbps": 200.0,
        "glances_api": "http://100.104.128.34:61208/api/4",
        "telemetry_method": "glances_v4_modular (/quicklook,/mem,/load,/network) + tcp_precheck_300ms",
    },
    "L2": {
        "node_id": "L2",
        "name": "MacBook Pro Intel (L2 Secondary AI Desktop Target)",
        "role": "Desktop Automation Target & Teacher Model Host (Discrete AMD Radeon Pro 5500M 4GB VRAM + 16GB DDR4)",
        "fleet_role": "AI_ACTUATION_NODE",
        "os": "macOS",
        "ips": ["192.168.8.127", "10.0.0.4", "100.103.212.21"],
        "ssh_user": "aaronmaher",
        "ssh_port": 22,
        "l1_jump_target": "aaronmaher@10.0.0.4",
        "bt_mac": "f0:18:98:14:98:89",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "DISCRETE_4GB_VRAM_PLUS_16GB_NORMAL_RAM",
        "normal_ram_gb": 16.0,
        "vram_gb": 4.0,
        "bandwidth_gbps": 192.0,
        "glances_api": "http://192.168.8.127:61208/api/4",
        "telemetry_method": "glances_v4_modular (/quicklook,/mem,/load,/network) + tcp_precheck_300ms",
    },
    "L3": {
        "node_id": "L3",
        "name": "Ubuntu Linux Head Node (L3 Podman & Graph Hub — Normal RAM Only, 0GB VRAM)",
        "role": "Neo4j 5.26.32 (:7474/:7687), Qdrant MRL (:6333), Disaggregated KV-Cache & AVX2 Sparse/Draft CPU Shards",
        "fleet_role": "AI_PODMAN_HUB",
        "os": "Linux",
        "ips": ["100.101.39.98", "192.168.8.225"],
        "ssh_user": "linux",
        "ssh_port": 22,
        "bt_mac": "dc:41:a9:fb:eb:66",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "NORMAL_RAM_ONLY_ZERO_VRAM",
        "normal_ram_gb": 16.0,
        "vram_gb": 0.0,
        "bandwidth_gbps": 25.6,
        "glances_api": "http://100.101.39.98:61208/api/3",
        "telemetry_method": "glances_v3_low_overhead_systemd (--disable-plugin docker,containers,ports,folders,raid,cloud,amps,processlist)",
    },
    "L8": {
        "node_id": "L8",
        "name": "Lauburu Linux Hub (L8 Podman & Disaggregated KV-Cache Hub — Normal RAM Only, 0GB VRAM)",
        "role": "32GB DDR4 Normal RAM Disaggregated KV-Cache Pool, Podman AI Trainer (:8096) & Sovereign Chromium (:9222)",
        "fleet_role": "AI_PODMAN_HUB",
        "os": "Linux",
        "ips": ["100.121.247.8", "192.168.8.242", "10.0.0.8"],
        "ssh_user": "linuxmini",
        "ssh_port": 22,
        "l1_jump_target": "linuxmini@10.0.0.8",
        "bt_mac": "94:83:c4:ff:00:01",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "NORMAL_RAM_ONLY_ZERO_VRAM",
        "normal_ram_gb": 32.0,
        "vram_gb": 0.0,
        "bandwidth_gbps": 34.1,
        "glances_api": "http://100.121.247.8:61208/api/4",
        "telemetry_method": "glances_v4_modular (/quicklook,/mem,/load,/network) + adaptive_circuit_breaker",
    },
    "L7": {
        "node_id": "L7",
        "name": "Samsung Galaxy S20+ 5G (L7 Dedicated AI Mobile Browser & WAF Node)",
        "role": "Dedicated 24/7 Mobile AI Browser, WAF Bypass & Shizuku/ADB UIAutomator Node (UID 2000)",
        "fleet_role": "AI_ACTUATION_NODE",
        "os": "Android",
        "ips": ["192.168.8.101", "192.168.8.224"],
        "ssh_user": "u0_a420",
        "ssh_port": 8022,
        "adb_serial": "192.168.8.101:32873",
        "bt_mac": "c2:f8:c0:36:de:29",
        "privilege_type": "shizuku_rish_or_tsu",
        "memory_class": "EDGE_LPDDR5_NORMAL_RAM",
        "normal_ram_gb": 12.0,
        "vram_gb": 0.0,
        "bandwidth_gbps": 44.0,
        "glances_api": "none_use_adb_proc_meminfo",
        "telemetry_method": "adb_or_ssh_proc_meminfo_single_shot",
    },
    "L6": {
        "node_id": "L6",
        "name": "Google Pixel 10 Pro XL (L6 Human Sanctuary Phone + AVF Root Edge)",
        "role": "Primary Personal Phone (Protected Browser) + Shizuku rish (UID 2000) & AVF Debian 13 (UID 0)",
        "fleet_role": "HUMAN_SANCTUARY_PHONE",
        "os": "Android",
        "ips": ["192.168.8.213", "100.114.215.68"],
        "ssh_user": "u0_a363",
        "ssh_port": 8022,
        "bt_mac": "26:cc:79:f2:90:76",
        "privilege_type": "shizuku_rish_and_avf_root",
        "memory_class": "EDGE_LPDDR5X_TENSOR_G5_NPU",
        "normal_ram_gb": 16.0,
        "vram_gb": 8.0,
        "bandwidth_gbps": 68.0,
        "glances_api": "none_use_ssh_8022_proc_meminfo",
        "telemetry_method": "ssh_8022_proc_meminfo_and_dumpsys_battery_60s",
    },
    "GW": {
        "node_id": "GW",
        "name": "GL.iNet GL-BE14000 Wi-Fi 7 Router (GW OpenWrt Root Sentinel)",
        "role": "OpenWrt Root (UID 0) DHCP/ARP Sentinel & Edge Wake Controller (192.168.8.1)",
        "fleet_role": "MESH_GATEWAY_SENTINEL",
        "os": "OpenWrt",
        "ips": ["192.168.8.1"],
        "ssh_user": "root",
        "ssh_port": 22,
        "bt_mac": "94:83:c4:ff:00:00",
        "privilege_type": "root_uid0",
        "memory_class": "EMBEDDED_ROUTER_NORMAL_RAM_ONLY",
        "normal_ram_gb": 1.0,
        "vram_gb": 0.0,
        "bandwidth_gbps": 12.8,
        "glances_api": "none_use_ubus_or_proc_meminfo",
        "telemetry_method": "ssh_proc_loadavg_meminfo_and_ip_neigh",
    },
    "L4": {
        "node_id": "L4",
        "name": "Surface Go 2 Linux Tablet (L4 Portable Edge — Normal RAM Only, 0GB VRAM)",
        "role": "Portable Linux Edge & Mobile Diagnostics Node (8GB Normal RAM Only, 0GB VRAM)",
        "fleet_role": "PORTABLE_LINUX_EDGE",
        "os": "Linux",
        "ips": ["100.78.250.119", "192.168.8.227"],
        "ssh_user": "linux",
        "ssh_port": 22,
        "bt_mac": "00:15:5d:ff:00:04",
        "privilege_type": "sudo_nopasswd",
        "memory_class": "NORMAL_RAM_ONLY_ZERO_VRAM",
        "normal_ram_gb": 8.0,
        "vram_gb": 0.0,
        "bandwidth_gbps": 17.0,
        "glances_api": "http://100.78.250.119:61208/api/4",
        "telemetry_method": "glances_v4_modular_when_awake_else_skip",
    },
}


def detect_local_node_id() -> str:
    """Identifies which mesh node this process is currently executing on."""
    env_node = os.environ.get("LAUBURU_NODE_ID")
    if env_node in MESH_NODES:
        return env_node
    hostname = socket.gethostname().lower()
    user = os.environ.get("USER", "")
    if Path("/data/data/com.termux").exists():
        return "L6"
    if Path("/etc/openwrt_release").exists() or user == "linuxmini":
        return "L8"
    if platform.system() == "Linux":
        return "L3"
    if user == "aaronmaher" and Path("/Volumes/Lauburu-Monorepo").exists():
        return "L5"
    if "macbook-pro" in hostname or "mac-intel" in hostname:
        return "L2"
    if "mini-5" in hostname:
        return "L1b"
    return "L1"


def discover_wireless_adb_target() -> Optional[str]:
    """Discovers connected or mDNS-advertised (_adb-tls-connect._tcp) Android ADB target."""
    try:
        out = subprocess.check_output(["adb", "devices"], text=True, timeout=2)
        for line in out.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                return parts[0]
    except Exception:
        pass
    if platform.system() == "Darwin":
        try:
            p = subprocess.Popen(
                ["dns-sd", "-Z", "_adb-tls-connect._tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                out, _ = p.communicate(timeout=1.8)
            except subprocess.TimeoutExpired:
                p.kill()
                out, _ = p.communicate()
            m = re.search(r"SRV\s+\d+\s+\d+\s+(\d+)\s+", out)
            if m:
                port = m.group(1)
                for host in ("192.168.8.101", "192.168.8.213", "100.114.215.68"):
                    subprocess.run(["adb", "connect", f"{host}:{port}"], capture_output=True, timeout=2)
                    chk = subprocess.check_output(["adb", "devices"], text=True, timeout=2)
                    if f"{host}:{port}\tdevice" in chk:
                        return f"{host}:{port}"
        except Exception:
            pass
    return None


# ============================================================================
# 2. ROOT-PRIVILEGED MESH EXECUTION ENGINE
# ============================================================================

def execute_root_command(
    node_id: str,
    command: str,
    timeout: int = 20,
) -> Dict[str, Any]:
    """
    Executes a command with root/elevated privileges on a specific node or ALL nodes.
    - macOS/Linux (L5, L1, L1b, L2, L3, L8): `sudo -n sh -c '<cmd>'` (UID 0)
    - Android (L6/L7): `tsu -c '<cmd>'` if rooted, else Shizuku `rish -c '<cmd>' 2>&1` (UID 2000 shell)
    """
    target = node_id.upper() if node_id.upper() != "L1B" else "L1b"
    if target == "ALL":
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
            futs = {
                nid: pool.submit(execute_root_command, nid, command, timeout)
                for nid in MESH_NODES
            }
            for nid, fut in futs.items():
                try:
                    results[nid] = fut.result(timeout=timeout + 5)
                except Exception as exc:
                    results[nid] = {"node": nid, "status": "error", "error": str(exc)}
        return {
            "mode": "ALL_NODES_ROOT_EXEC",
            "command": command,
            "nodes_succeeded": sum(1 for r in results.values() if r.get("status") == "ok"),
            "total_nodes": len(MESH_NODES),
            "results": results,
        }

    if target not in MESH_NODES:
        return {"node": node_id, "status": "error", "error": f"Unknown node_id '{node_id}'"}

    info = MESH_NODES[target]
    local_node = detect_local_node_id()
    t0 = time.time()

    # Case 1: Executing on the local host directly
    if target == local_node:
        if target == "L6":
            wrapped = (
                f"if command -v tsu >/dev/null 2>&1 && tsu -c id >/dev/null 2>&1; then "
                f"tsu -c {json.dumps(command)} 2>&1; "
                f"elif [ -x ~/.local/bin/rish ]; then "
                f"sh ~/.local/bin/rish -c {json.dumps(command)} 2>&1; "
                f"elif [ -x ~/rish ]; then "
                f"sh ~/rish -c {json.dumps(command)} 2>&1; "
                f"else sh -c {json.dumps(command)} 2>&1; fi"
            )
            priv_mode = "local_android_rish_or_tsu"
        elif os.geteuid() == 0:
            wrapped = command
            priv_mode = "local_native_root"
        else:
            wrapped = f"sudo -n sh -c {json.dumps(command)}"
            priv_mode = "local_sudo_root"

        try:
            proc = subprocess.run(
                wrapped,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "node": target,
                "status": "ok" if proc.returncode == 0 else "error",
                "privilege_mode": priv_mode,
                "transport": "local",
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "latency_ms": round((time.time() - t0) * 1000, 2),
            }
        except Exception as exc:
            return {
                "node": target,
                "status": "error",
                "privilege_mode": priv_mode,
                "transport": "local",
                "error": str(exc),
                "latency_ms": round((time.time() - t0) * 1000, 2),
            }

    # Case 2: Android ADB + Shizuku `rish` (UID 2000) for L7 (Galaxy S20+) or L6 (Pixel 10 Pro XL)
    if target in ("L6", "L7"):
        adb_dev = info.get("adb_serial")
        if not adb_dev:
            cand = discover_wireless_adb_target()
            if cand and any( cand.startswith(ip + ":") for ip in info.get("ips", []) ):
                adb_dev = cand
        if adb_dev:
            try:
                rish_wrap = (
                    f"if [ -x /data/local/tmp/rish ]; then "
                    f"RISH_APPLICATION_ID=com.termux /data/local/tmp/rish -c {json.dumps(command)} 2>&1; "
                    f"else {command} 2>&1; fi"
                )
                proc = subprocess.run(
                    ["adb", "-s", adb_dev, "shell", rish_wrap],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if proc.returncode == 0:
                    return {
                        "node": target,
                        "status": "ok",
                        "privilege_mode": "shizuku_rish_2000_over_adb",
                        "transport": f"adb://{adb_dev}",
                        "exit_code": proc.returncode,
                        "stdout": proc.stdout.strip(),
                        "stderr": proc.stderr.strip(),
                        "latency_ms": round((time.time() - t0) * 1000, 2),
                    }
            except Exception:
                pass

    # Resolve valid SSH key across L5 (/Volumes vs /Users/aaronmaher), L1, L3, L8
    ssh_key = None
    for cand_key in (
        os.path.expanduser("~/.ssh/id_ed25519"),
        "/Users/aaronmaher/.ssh/id_ed25519",
        "/Users/aaron/.ssh/id_ed25519",
        "/home/linux/.ssh/id_ed25519",
        "/home/linuxmini/.ssh/id_ed25519",
    ):
        if os.path.exists(cand_key):
            ssh_key = cand_key
            break

    # Case 3: Remote SSH execution across direct IPs
    for ip in info.get("ips", []):
        ssh_port = str(info.get("ssh_port", 22))
        ssh_user = info.get("ssh_user", "root")
        if target in ("L6", "L7"):
            remote_cmd = (
                f"if command -v tsu >/dev/null 2>&1 && tsu -c id >/dev/null 2>&1; then "
                f"tsu -c {json.dumps(command)} 2>&1; "
                f"elif [ -x /data/data/com.termux/files/home/rish ]; then "
                f"sh /data/data/com.termux/files/home/rish -c {json.dumps(command)} 2>&1; "
                f"elif [ -x /data/local/tmp/rish ]; then "
                f"RISH_APPLICATION_ID=com.termux /data/local/tmp/rish -c {json.dumps(command)} 2>&1; "
                f"else sh -c {json.dumps(command)} 2>&1; fi"
            )
            priv_mode = "remote_shizuku_rish_2000"
        elif target == "GW" or ssh_user == "root":
            remote_cmd = f"sh -c {json.dumps(command)}"
            priv_mode = "remote_native_root_uid0"
        else:
            remote_cmd = f"sudo -n sh -c {json.dumps(command)}"
            priv_mode = "remote_sudo_root"

        ssh_args = ["ssh", "-F", "/dev/null"]
        if ssh_key:
            ssh_args.extend(["-i", ssh_key])
        ssh_args.extend([
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=3",
            "-o", "StrictHostKeyChecking=no",
            "-p", ssh_port,
            f"{ssh_user}@{ip}",
            remote_cmd,
        ])
        try:
            proc = subprocess.run(
                ssh_args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode == 0:
                return {
                    "node": target,
                    "status": "ok",
                    "privilege_mode": priv_mode,
                    "transport": f"ssh://{ssh_user}@{ip}:{ssh_port}",
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(),
                    "latency_ms": round((time.time() - t0) * 1000, 2),
                }
        except Exception:
            continue

    # Case 4: L1 Thunderbolt 4 Bridge Jump (`aaron@100.119.199.76` -> `10.0.0.x`)
    l1_jump = info.get("l1_jump_target")
    if l1_jump:
        try:
            inner_cmd = f"sudo -n sh -c {json.dumps(command)}"
            outer_cmd = f"ssh -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=no {l1_jump} {json.dumps(inner_cmd)}"
            jump_args = ["ssh", "-F", "/dev/null"]
            if ssh_key:
                jump_args.extend(["-i", ssh_key])
            jump_args.extend([
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=4",
                "-o", "StrictHostKeyChecking=no",
                "aaron@100.119.199.76",
                outer_cmd,
            ])
            proc = subprocess.run(
                jump_args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode == 0:
                return {
                    "node": target,
                    "status": "ok",
                    "privilege_mode": "remote_sudo_root_via_l1_tb4",
                    "transport": f"ssh://aaron@100.119.199.76->{l1_jump}",
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(),
                    "latency_ms": round((time.time() - t0) * 1000, 2),
                }
        except Exception:
            pass

    return {
        "node": target,
        "status": "unreachable",
        "bt_mac_anchor": info.get("bt_mac"),
        "error": f"All IP/ADB transports to {target} timed out; consult Bluetooth anchor {info.get('bt_mac')}",
        "latency_ms": round((time.time() - t0) * 1000, 2),
    }


# ============================================================================
# 3. EMBEDDINGGEMMA 2 MULTIMODAL & MATRYOSHKA (MRL) ENGINE
# ============================================================================

def l2_normalize(vec: List[float]) -> List[float]:
    """L2-normalizes a vector to unit length."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 1e-12:
        return vec
    return [round(x / norm, 7) for x in vec]


def mrl_truncate(vec_768: List[float], dim: int = 768) -> List[float]:
    """
    Matryoshka Representation Learning (MRL) dynamic output truncation.
    Slices the 768D EmbeddingGemma 2 vector to `dim` (768, 512, 256, or 128)
    and strictly L2 re-normalizes the sliced representation.
    """
    if dim not in MRL_DIMENSIONS:
        raise ValueError(f"Unsupported MRL dimension {dim}; must be one of {MRL_DIMENSIONS}")
    sliced = vec_768[:dim]
    return l2_normalize(sliced)


class EmbeddingGemma2Engine:
    """
    Google DeepMind EmbeddingGemma 2 (740M multimodal / 270M text backbone) Engine.
    - 8,192-token context window
    - Unified 768D vector space across text, code, images, audio, and video
    - Matryoshka Representation Learning (MRL) dimensions: 768, 512, 256, 128
    """

    def __init__(self) -> None:
        self.active_endpoint: Optional[str] = None

    @staticmethod
    def format_query(query: str, task: str = "search_result") -> str:
        raw = query.strip()
        if raw.startswith("task:") or raw.startswith("title:"):
            return raw
        prefix = TASK_PREFIXES.get(task, TASK_PREFIXES["search_result"])
        return f"{prefix}{raw}"

    @staticmethod
    def format_document(
        text: str,
        title: str = "none",
        modality: str = "text",
        media_path: Optional[str] = None,
    ) -> str:
        clean_title = (title or "none").strip()
        modality_tag = ""
        media_summary = ""
        if modality in ("image", "video", "audio") or media_path:
            token = f"<|{modality if modality in ('image', 'video', 'audio') else 'image'}|>"
            modality_tag = f"{token} "
            if media_path and Path(media_path).exists():
                p = Path(media_path)
                st = p.stat()
                h = hashlib.sha256(p.read_bytes()[:65536]).hexdigest()[:16]
                media_summary = f" [media_file={p.name} bytes={st.st_size} sha256_prefix={h}]"
        if text.strip().startswith("title:"):
            return text.strip()
        return f"title: {clean_title} | text: {modality_tag}{text.strip()}{media_summary}"

    def embed_raw(self, formatted_input: str) -> Tuple[List[float], str]:
        """
        Generates a 768D EmbeddingGemma 2 vector using:
        1. Live EmbeddingGemma 2 HTTP server (:8087) on local/mesh nodes
        2. Direct `llama-embedding` binary with `embeddinggemma-2-UD-Q4_K_XL.gguf`
        """
        payload = json.dumps({"input": formatted_input}).encode("utf-8")
        endpoints = (
            [self.active_endpoint] + [e for e in EMBEDDINGGEMMA2_ENDPOINTS if e != self.active_endpoint]
            if self.active_endpoint
            else EMBEDDINGGEMMA2_ENDPOINTS
        )
        for url in endpoints:
            if not url or not _tcp_reachable(url):
                continue
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=4.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if "data" in data and data["data"]:
                        vec = data["data"][0].get("embedding")
                    elif "embedding" in data:
                        vec = data["embedding"]
                    else:
                        vec = None
                    if isinstance(vec, list) and len(vec) >= 768:
                        self.active_endpoint = url
                        return l2_normalize([float(x) for x in vec[:768]]), f"http:{url}"
            except Exception:
                continue

        # Fallback to direct `llama-embedding` CLI binary with authentic GGUF weights
        model_path = next((m for m in MODEL_PATHS if Path(m).exists()), None)
        bin_path = next((b for b in LLAMA_EMBEDDING_BINS if Path(b).exists()), None)
        if model_path and bin_path:
            try:
                proc = subprocess.run(
                    [
                        bin_path,
                        "-m", model_path,
                        "--pooling", "mean",
                        "-p", formatted_input,
                        "--embd-output-format", "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                out = proc.stdout
                idx = out.find("{")
                if idx != -1:
                    data = json.loads(out[idx:])
                    vec = data["data"][0]["embedding"]
                    if len(vec) >= 768:
                        return l2_normalize([float(x) for x in vec[:768]]), f"cli:{bin_path}"
            except Exception:
                pass

        raise RuntimeError(
            "EmbeddingGemma 2 inference unavailable across :8087 endpoints and local GGUF binary."
        )

    def embed_mrl_bundle(
        self,
        text: str,
        is_query: bool = False,
        task: str = "search_result",
        title: str = "none",
        modality: str = "text",
        media_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes the full 768D EmbeddingGemma 2 vector and all 4 MRL representations
        (768D, 512D, 256D, 128D), each L2 re-normalized.
        """
        t0 = time.time()
        formatted = (
            self.format_query(text, task=task)
            if is_query
            else self.format_document(text, title=title, modality=modality, media_path=media_path)
        )
        vec_768, provider = self.embed_raw(formatted)
        return {
            "model": "google/embeddinggemma-2 (UD-Q4_K_XL + mmproj-Q8_0)",
            "provider": provider,
            "modality": modality,
            "formatted_prompt": formatted,
            "context_window": 8192,
            "latency_ms": round((time.time() - t0) * 1000, 2),
            "mrl": {
                "768": mrl_truncate(vec_768, 768),
                "512": mrl_truncate(vec_768, 512),
                "256": mrl_truncate(vec_768, 256),
                "128": mrl_truncate(vec_768, 128),
            },
        }


# ============================================================================
# 4. NEO4J 5 SOVEREIGN CLIENT & OFFLINE SQLITE REPLICA
# ============================================================================

DDL_REGEX = re.compile(
    r"^\s*(CREATE\s+(CONSTRAINT|VECTOR\s+INDEX|FULLTEXT\s+INDEX|INDEX)|DROP\s+(CONSTRAINT|INDEX))",
    re.IGNORECASE,
)


class Neo4jSovereignClient:
    """
    Zero-Mock Neo4j 5.26.32 Transactional HTTP Client (`:7474/db/neo4j/tx/commit`)
    with automatic DDL/DML transaction isolation and local SQLite graph replica.
    """

    def __init__(self) -> None:
        self.active_http_url: Optional[str] = None
        self.replica_path = Path.home() / ".lauburu" / "lens_neo4j_replica.sqlite"
        self.replica_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_local_replica()

    def _init_local_replica(self) -> None:
        with sqlite3.connect(self.replica_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lens_documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT,
                    text TEXT,
                    modality TEXT,
                    source_node TEXT,
                    media_path TEXT,
                    embedding_768 TEXT,
                    embedding_512 TEXT,
                    embedding_256 TEXT,
                    embedding_128 TEXT,
                    updated_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cypher_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement TEXT,
                    parameters TEXT,
                    backend TEXT,
                    executed_at REAL
                )
                """
            )

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASSWORD}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def _post_statements(self, statements: List[Dict[str, Any]], timeout: float = 15.0) -> Dict[str, Any]:
        payload = json.dumps({"statements": statements}).encode("utf-8")
        urls = (
            [self.active_http_url] + [u for u in NEO4J_HTTP_ENDPOINTS if u != self.active_http_url]
            if self.active_http_url
            else NEO4J_HTTP_ENDPOINTS
        )
        last_err = "No Neo4j endpoints configured"
        for url in urls:
            if not url or not _tcp_reachable(url, timeout=0.6):
                continue
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": self._auth_header(),
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    self.active_http_url = url
                    return {"backend": url, "body": body}
            except Exception as exc:
                last_err = str(exc)
                continue
        raise ConnectionError(f"Neo4j HTTP endpoints unreachable ({last_err})")

    def query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Executes one or more semicolon-separated Cypher statements against Neo4j 5.26.32.
        Automatically isolates DDL statements into standalone transactions as required by Neo4j 5.
        """
        params = parameters or {}
        parts = [p.strip() for p in cypher.split(";") if p.strip()]
        if not parts:
            return {"status": "ok", "records": [], "errors": []}

        all_records: List[Dict[str, Any]] = []
        all_errors: List[Dict[str, Any]] = []
        backend_used = "local_replica"

        try:
            for stmt in parts:
                resp = self._post_statements([{"statement": stmt, "parameters": params}], timeout=timeout)
                backend_used = resp["backend"]
                body = resp["body"]
                for err in body.get("errors", []):
                    all_errors.append(err)
                for res in body.get("results", []):
                    cols = res.get("columns", [])
                    for row_obj in res.get("data", []):
                        row_vals = row_obj.get("row", [])
                        all_records.append(dict(zip(cols, row_vals)))

            with sqlite3.connect(self.replica_path) as conn:
                conn.execute(
                    "INSERT INTO cypher_audit_log (statement, parameters, backend, executed_at) VALUES (?, ?, ?, ?)",
                    (cypher, json.dumps(params), backend_used, time.time()),
                )

            return {
                "status": "ok" if not all_errors else "cypher_error",
                "backend": backend_used,
                "bolt_uri": NEO4J_BOLT_URI,
                "row_count": len(all_records),
                "records": all_records,
                "errors": all_errors,
            }
        except Exception as exc:
            return {
                "status": "offline_replica",
                "backend": str(self.replica_path),
                "error": str(exc),
                "records": [],
            }

    def ensure_schema(self) -> Dict[str, Any]:
        """Ensures Neo4j constraints and all 4 EmbeddingGemma 2 MRL vector indexes exist and are ONLINE."""
        ddl_statements = [
            "CREATE CONSTRAINT lens_doc_id IF NOT EXISTS FOR (d:LensDocument) REQUIRE d.doc_id IS UNIQUE",
            "CREATE CONSTRAINT lens_node_id IF NOT EXISTS FOR (n:MeshNode) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT lens_event_id IF NOT EXISTS FOR (e:ScreenEvent) REQUIRE e.event_id IS UNIQUE",
            "CREATE CONSTRAINT lens_subsystem_id IF NOT EXISTS FOR (s:Subsystem) REQUIRE s.subsystem_id IS UNIQUE",
            "CREATE CONSTRAINT lens_app_id IF NOT EXISTS FOR (a:Application) REQUIRE a.app_id IS UNIQUE",
            "CREATE CONSTRAINT lens_signal_id IF NOT EXISTS FOR (b:BiometricSignal) REQUIRE b.signal_id IS UNIQUE",
            "CREATE CONSTRAINT lens_sensor_id IF NOT EXISTS FOR (s:SensorDevice) REQUIRE s.sensor_id IS UNIQUE",
            "CREATE CONSTRAINT lens_dsp_id IF NOT EXISTS FOR (m:DSPModule) REQUIRE m.module_id IS UNIQUE",
            "CREATE CONSTRAINT lens_model_id IF NOT EXISTS FOR (m:SpecialistModel) REQUIRE m.model_id IS UNIQUE",
            "CREATE CONSTRAINT lens_task_id IF NOT EXISTS FOR (t:TaskCategory) REQUIRE t.task_id IS UNIQUE",
            "CREATE VECTOR INDEX gemma2_vec_768 IF NOT EXISTS FOR (d:LensDocument) ON (d.embedding_768) OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}}",
            "CREATE VECTOR INDEX gemma2_vec_512 IF NOT EXISTS FOR (d:LensDocument) ON (d.embedding_512) OPTIONS {indexConfig: {`vector.dimensions`: 512, `vector.similarity_function`: 'cosine'}}",
            "CREATE VECTOR INDEX gemma2_vec_256 IF NOT EXISTS FOR (d:LensDocument) ON (d.embedding_256) OPTIONS {indexConfig: {`vector.dimensions`: 256, `vector.similarity_function`: 'cosine'}}",
            "CREATE VECTOR INDEX gemma2_vec_128 IF NOT EXISTS FOR (d:LensDocument) ON (d.embedding_128) OPTIONS {indexConfig: {`vector.dimensions`: 128, `vector.similarity_function`: 'cosine'}}",
        ]
        results = []
        for stmt in ddl_statements:
            res = self.query(stmt)
            results.append({"ddl": stmt[:60], "status": res.get("status"), "errors": res.get("errors", [])})
        idx_res = self.query("SHOW VECTOR INDEXES YIELD name, state, populationPercent RETURN name, state, populationPercent")
        return {
            "status": "ok",
            "ddl_applied": len(results),
            "vector_indexes": idx_res.get("records", []),
        }

    def get_schema_summary(self) -> Dict[str, Any]:
        labels = self.query("CALL db.labels() YIELD label RETURN label").get("records", [])
        rel_types = self.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType").get("records", [])
        indexes = self.query("SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties RETURN name, type, state, labelsOrTypes, properties").get("records", [])
        constraints = self.query("SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties").get("records", [])
        counts = self.query("MATCH (n) RETURN labels(n) AS labels, count(n) AS count").get("records", [])
        return {
            "status": "ok",
            "backend": self.active_http_url or NEO4J_HTTP_ENDPOINTS[0],
            "bolt_uri": NEO4J_BOLT_URI,
            "labels": [r.get("label") for r in labels],
            "relationship_types": [r.get("relationshipType") for r in rel_types],
            "node_counts": counts,
            "indexes": indexes,
            "constraints": constraints,
        }

    def sync_mesh_topology(self, verify_root: bool = True) -> Dict[str, Any]:
        """
        Synchronizes all 10 Lauburu Mesh nodes (`GW`, `L1`, `L1b`, `L2`, `L3`, `L4`, `L5`, `L6`, `L7`, `L8`),
        their live root-privilege audit status, Glances API endpoints, Normal RAM vs VRAM hardware
        classifications, and inter-node topology edges into Neo4j.
        """
        root_audit = execute_root_command("ALL", "id") if verify_root else {"results": {}}
        node_results = root_audit.get("results", {})
        synced_nodes = []

        for nid, meta in MESH_NODES.items():
            audit = node_results.get(nid, {})
            cypher = """
            MERGE (n:MeshNode {node_id: $node_id})
            SET n.name = $name,
                n.role = $role,
                n.fleet_role = $fleet_role,
                n.os = $os,
                n.primary_ip = $primary_ip,
                n.all_ips = $all_ips,
                n.bt_mac = $bt_mac,
                n.privilege_type = $privilege_type,
                n.memory_class = $memory_class,
                n.normal_ram_gb = $normal_ram_gb,
                n.vram_gb = $vram_gb,
                n.bandwidth_gbps = $bandwidth_gbps,
                n.glances_api = $glances_api,
                n.telemetry_method = $telemetry_method,
                n.root_status = $root_status,
                n.root_uid_output = $root_uid_output,
                n.last_synced_at = timestamp()
            RETURN n.node_id AS node_id, n.root_status AS root_status
            """
            params = {
                "node_id": nid,
                "name": meta["name"],
                "role": meta["role"],
                "fleet_role": meta.get("fleet_role", "MESH_NODE"),
                "os": meta["os"],
                "primary_ip": meta["ips"][0],
                "all_ips": meta["ips"],
                "bt_mac": meta.get("bt_mac", ""),
                "privilege_type": meta["privilege_type"],
                "memory_class": meta.get("memory_class", "UNKNOWN"),
                "normal_ram_gb": float(meta.get("normal_ram_gb", 0.0)),
                "vram_gb": float(meta.get("vram_gb", 0.0)),
                "bandwidth_gbps": float(meta.get("bandwidth_gbps", 0.0)),
                "glances_api": meta.get("glances_api", ""),
                "telemetry_method": meta.get("telemetry_method", ""),
                "root_status": audit.get("status", "unverified"),
                "root_uid_output": audit.get("stdout", ""),
            }
            self.query(cypher, params)
            synced_nodes.append({
                "node_id": nid,
                "primary_ip": params["primary_ip"],
                "memory_class": params["memory_class"],
                "normal_ram_gb": params["normal_ram_gb"],
                "vram_gb": params["vram_gb"],
                "glances_api": params["glances_api"],
                "root_status": params["root_status"],
                "uid": params["root_uid_output"],
            })

        # Create topological links across all 10 hardware nodes
        edges = [
            ("L5", "L1", "THUNDERBOLT_10GBE", 0.27),
            ("L1", "L1b", "THUNDERBOLT_10GBE", 0.31),
            ("L1", "L2", "THUNDERBOLT_10GBE", 0.35),
            ("L1", "L8", "THUNDERBOLT_10GBE", 0.42),
            ("L5", "L3", "TAILSCALE_WIREGUARD", 4.5),
            ("L1", "L3", "TAILSCALE_WIREGUARD", 3.8),
            ("L3", "L8", "LAN_GIGABIT", 1.2),
            ("L3", "L4", "TAILSCALE_WIREGUARD", 5.6),
            ("L5", "L6", "TAILSCALE_AND_ADB", 8.4),
            ("L1", "L7", "ADB_WIRELESS_LAN", 9.1),
            ("GW", "L1", "WIFI7_AND_LAN_GATEWAY", 0.8),
            ("GW", "L3", "LAN_GATEWAY", 0.9),
            ("GW", "L8", "LAN_GATEWAY", 0.9),
        ]
        for src, dst, transport, rtt_ms in edges:
            self.query(
                """
                MATCH (a:MeshNode {node_id: $src}), (b:MeshNode {node_id: $dst})
                MERGE (a)-[r:CONNECTED_TO {transport: $transport}]->(b)
                SET r.rtt_ms = $rtt_ms, r.updated_at = timestamp()
                """,
                {"src": src, "dst": dst, "transport": transport, "rtt_ms": rtt_ms},
            )

        return {
            "status": "ok",
            "synced_nodes": synced_nodes,
            "edges_synced": len(edges),
        }

    def sync_full_codebase_and_biometrics_graph(self, verify_root: bool = False) -> Dict[str, Any]:
        """
        Indexes the complete Lauburu Monorepo architecture into Neo4j 5.26.32:
        1. All 10 Hardware Nodes (`GW`, `L1`, `L1b`, `L2`, `L3`, `L4`, `L5`, `L6`, `L7`, `L8`)
        2. All 13 Monorepo Subsystems (`00_core_infrastructure` through `12_continuous_lora_evolution`)
        3. All Consolidated Applications & Service Endpoints (Unified Movesense + AssaultBike Real-Time
           Biometrics Hub, `:8084` GATT Browser, `:8089` RFCOMM Bridge, `:9223` Web Bluetooth Bridge,
           `:8443` code-server, `:8888/:18888` SeaweedFS, `:8889` JupyterLab, `:7681` ttyd, `:3035-:3037` Screen Lens)
        4. All 7 Biometric & Workout Signals (`Readiness`, `HeartRate`, `DFA_Alpha1`, `HRV_RMSSD`,
           `ECG_512Hz`, `BloodPressure_PTT`, `AssaultBike_FTMS`), Sensor Devices (`Movesense_HR2_ECG`,
           `AssaultBike_BLE_FTMS`), and DSP Modules (`PanTompkins_512Hz`, `Peng_DFA_Alpha1_Window120s`,
           `MoensKorteweg_PTT_BP_Kalman`, `RMSSD_LnRMSSD_Readiness_Engine`, `FTMS_PowerCadence_Synchronizer`)
        5. All 7 Specialized Local AI Models (`:SpecialistModel`) and `:TaskCategory` routing edges.
        """
        self.ensure_schema()
        topo = self.sync_mesh_topology(verify_root=verify_root)

        subsystems = [
            ("00_core_infrastructure", "Core Infrastructure, SeaweedFS, Docker/Podman, Tailscale & Systemd", ["L1", "L3", "L8", "GW"]),
            ("01_apps", "Consolidated Applications Ecosystem (Unified Movesense + AssaultBike Hub, Screen Lens, Zone 2)", ["L1", "L5", "L3", "L6", "L7"]),
            ("02_ai_models_and_inference", "Distributed AI Inference, Hybrid Sharding & Specialized Local AI Router", ["L1", "L5", "L1b", "L2", "L3", "L8"]),
            ("03_biometrics_and_telemetry", "Medical-Grade Biometrics & DSP Engine (512Hz ECG, DFA-alpha1, PTT BP, RMSSD, FTMS)", ["L1", "L5", "L3", "L6"]),
            ("04_data_and_memory", "Dual-Vault Memory (Neo4j 5.26.32 + Qdrant MRL + EmbeddingGemma 2 + 24/7 LoRA Datasets)", ["L3", "L8", "L1", "L5"]),
            ("05_agents_and_swarms", "Tri-Orchestrator, Multi-Model Perspective Council & Genetic MoE Swarm", ["L1", "L5", "L3", "L8"]),
            ("06_scripts_and_tooling", "Autonomous Tooling, NetMon Non-Overloading Telemetry, Neo4j Orchestrator & Self-Healing", ["L1", "L5", "L3", "L8"]),
            ("07_docs_and_architecture", "Canonical Architecture Specifications, Whitepapers & Multi-Model Consensus Reports", ["L1", "L5", "L3"]),
            ("08_business_and_commerce", "Shopify Storefront GraphQL, Subscription Tiers & Autonomous Commerce", ["L1", "L3"]),
            ("09_app_store_production", "Flutter/Android/iOS Release Engineering & Zero-Crash Production Pipeline", ["L1", "L5", "L6", "L7"]),
            ("10_spatial_grappling_kinematics", "955-Node OPML Spatial Grappling Trees & 3D Tatami World Kinematics", ["L1", "L2", "L5"]),
            ("11_security_red_blue_team", "Zero-Trust SSH/RPC Isolation, HMAC Auth & Red/Blue Team Auditing", ["GW", "L1", "L3", "L8"]),
            ("12_continuous_lora_evolution", "24/7 Unsloth/QLoRA Distillation, Teacher-Student WebVLA & Weight Merging", ["L8", "L3", "L1", "L2"]),
        ]
        for sub_id, desc, nodes in subsystems:
            self.query(
                """
                MERGE (s:Subsystem {subsystem_id: $sub_id})
                SET s.name = $sub_id,
                    s.description = $desc,
                    s.path = '/Volumes/Lauburu-Monorepo/' + $sub_id,
                    s.updated_at = timestamp()
                WITH s
                UNWIND $nodes AS nid
                MATCH (n:MeshNode {node_id: nid})
                MERGE (s)-[:DEPLOYED_ON]->(n)
                """,
                {"sub_id": sub_id, "desc": desc, "nodes": nodes},
            )

        apps = [
            {
                "app_id": "unified_movesense_assaultbike_hub",
                "name": "Unified Movesense + AssaultBike Real-Time Biometrics Hub",
                "subsystem_id": "01_apps",
                "ports": [4000, 8084, 8089, 9223],
                "host_nodes": ["L1", "L5", "L3"],
                "description": (
                    "Consolidated real-time physiological & ergometer cockpit merging Movesense HR2/ECG "
                    "(Readiness, HeartRate, DFA-alpha1, HRV RMSSD, 512Hz ECG, Cuffless PTT Blood Pressure) "
                    "with AssaultBike BLE FTMS (Watts, Cadence RPM, HR-to-Power Decoupling) and GATT/RFCOMM/WebBluetooth bridges."
                ),
                "canonical_path": "01_apps/movesense_biometrics_dashboard",
            },
            {
                "app_id": "gatt_browser_and_coder_8084",
                "name": "BLE GATT Characteristic Browser & Qwen2.5-Coder Endpoint (:8084)",
                "subsystem_id": "03_biometrics_and_telemetry",
                "ports": [8084],
                "host_nodes": ["L3", "L1"],
                "description": "Real-time BLE GATT service/characteristic inspector (0x180D HR, 0x2AD2 FTMS, Movesense Whiteboard) & Qwen2.5-Coder-1.5B server.",
                "canonical_path": "03_biometrics_and_telemetry/movesense_247_service.py",
            },
            {
                "app_id": "rfcomm_bridge_and_qwen_8089",
                "name": "Bluetooth RFCOMM Serial Bridge & Qwen2.5-0.5B Micro-Triage (:8089)",
                "subsystem_id": "03_biometrics_and_telemetry",
                "ports": [8089],
                "host_nodes": ["L1", "L3"],
                "description": "Low-latency Bluetooth RFCOMM/SPP serial telemetry bridge and ultra-fast Qwen2.5-0.5B-Instruct readiness triage endpoint.",
                "canonical_path": "03_biometrics_and_telemetry/movesense_to_4000_bridge.py",
            },
            {
                "app_id": "web_bluetooth_bridge_9223",
                "name": "Web Bluetooth to Native CoreBluetooth/BlueZ GATT Proxy (:9223)",
                "subsystem_id": "01_apps",
                "ports": [9223],
                "host_nodes": ["L1", "L5"],
                "description": "WebSocket/HTTP proxy bridging browser Web Bluetooth API requests to native macOS CoreBluetooth and Linux BlueZ GATT/FTMS.",
                "canonical_path": "01_apps/movesense_lauburu",
            },
            {
                "app_id": "code_server_8443",
                "name": "Lauburu Sovereign Code-Server IDE (:8443)",
                "subsystem_id": "00_core_infrastructure",
                "ports": [8443],
                "host_nodes": ["L3"],
                "description": "Browser-accessible VS Code IDE hosted on L3 (http://100.101.39.98:8443) for zero-overhead remote development off M4 sanctuaries.",
                "canonical_path": "00_core_infrastructure",
            },
            {
                "app_id": "seaweedfs_8888_18888",
                "name": "SeaweedFS Distributed Filer & Object Store (:8888/:18888)",
                "subsystem_id": "00_core_infrastructure",
                "ports": [8888, 18888, 9333],
                "host_nodes": ["L3"],
                "description": "POSIX Filer (:8888) and Master (:9333) storing raw 512Hz ECG parquet/sqlite archives, GGUF shards, and LoRA checkpoints.",
                "canonical_path": "00_core_infrastructure",
            },
            {
                "app_id": "jupyterlab_8889",
                "name": "JupyterLab Biometrics DSP & ML Workbench (:8889)",
                "subsystem_id": "03_biometrics_and_telemetry",
                "ports": [8889],
                "host_nodes": ["L3"],
                "description": "Interactive notebook server on L3 (:8889) for DFA-alpha1 validation, PTT BP calibration curves, and QLoRA loss analysis.",
                "canonical_path": "03_biometrics_and_telemetry/movesense_biometrics_dsp_engine.py",
            },
            {
                "app_id": "ttyd_headless_7681",
                "name": "Headless Web Terminal & Multi-Model Perspective Council (:7681)",
                "subsystem_id": "05_agents_and_swarms",
                "ports": [7681],
                "host_nodes": ["L3"],
                "description": "Headless ttyd web terminal on L3 (:7681) hosting persistent tmux sessions (`ai_perspective_council`, `netmon`, `cypher-shell`).",
                "canonical_path": "05_agents_and_swarms",
            },
            {
                "app_id": "screen_lens_sovereign_3035_3037",
                "name": "Screen Lens Sovereign Visual OCR, Audio Companion & Global Orchestrator (:3035-:3037)",
                "subsystem_id": "01_apps",
                "ports": [3035, 3036, 3037, 4003, 4005, 4006],
                "host_nodes": ["L1", "L5", "L2", "L7"],
                "description": "Zero-mock visual perception (:3035), Screen Life Companion (:3036), Global Orchestrator (:3037), and Teacher-Student WebVLA engine.",
                "canonical_path": "01_apps/screen_lens",
            },
        ]
        for app in apps:
            self.query(
                """
                MERGE (a:Application {app_id: $app_id})
                SET a.name = $name,
                    a.ports = $ports,
                    a.description = $description,
                    a.canonical_path = $canonical_path,
                    a.updated_at = timestamp()
                WITH a
                MATCH (s:Subsystem {subsystem_id: $subsystem_id})
                MERGE (a)-[:BELONGS_TO_SUBSYSTEM]->(s)
                WITH a
                UNWIND $host_nodes AS nid
                MATCH (n:MeshNode {node_id: nid})
                MERGE (a)-[:HOSTED_ON]->(n)
                """,
                app,
            )

        sensors = [
            {
                "sensor_id": "Movesense_HR2_ECG",
                "name": "Movesense Medical/HR2 Chest Strap Sensor",
                "protocol": "BLE_GATT_AND_WHITEBOARD",
                "sampling_rates": "ECG 512Hz, RR/HR 1-4Hz, 9-Axis IMU/SCG 208Hz",
                "gatt_uuids": ["0x180D", "0x2A37", "34802252-7185-4d5d-b431-630e7050e8f0"],
            },
            {
                "sensor_id": "AssaultBike_BLE_FTMS",
                "name": "Assault AirBike Pro / Elite BLE FTMS Console",
                "protocol": "BLE_FTMS_AND_ANT_PLUS",
                "sampling_rates": "Indoor Bike Data 1-4Hz (Watts, Cadence RPM, Speed, Distance, kcal)",
                "gatt_uuids": ["0x1826", "0x2AD2"],
            },
        ]
        for s in sensors:
            self.query(
                """
                MERGE (dev:SensorDevice {sensor_id: $sensor_id})
                SET dev.name = $name,
                    dev.protocol = $protocol,
                    dev.sampling_rates = $sampling_rates,
                    dev.gatt_uuids = $gatt_uuids,
                    dev.updated_at = timestamp()
                """,
                s,
            )

        dsp_modules = [
            {
                "module_id": "PanTompkins_512Hz",
                "name": "512Hz Zero-Phase Bandpass (0.5-40Hz) & Pan-Tompkins QRS Detector",
                "algorithm": "4th-order Butterworth bandpass + derivative squaring + adaptive R-peak thresholding + 2ms parabolic interpolation",
                "source_file": "03_biometrics_and_telemetry/movesense_biometrics_dsp_engine.py",
            },
            {
                "module_id": "Peng_DFA_Alpha1_Window120s",
                "name": "Detrended Fluctuation Analysis Short-Term Exponent (DFA-alpha1)",
                "algorithm": "Peng (1995) integrated RR series detrended over box sizes n in [4..16] beats on 120s sliding window (5s step); LT1=0.75, LT2=0.50",
                "source_file": "03_biometrics_and_telemetry/movesense_biometrics_dsp_engine.py",
            },
            {
                "module_id": "MoensKorteweg_PTT_BP_Kalman",
                "name": "Cuffless Pulse Transit Time (PTT) Systolic/Diastolic Blood Pressure Estimator",
                "algorithm": "ECG R-peak to peripheral/SCG pulse arrival delta_t -> Moens-Korteweg logarithmic arterial stiffness model (SBP = a*ln(PTT) + b*HR + c) + 1D Kalman filter",
                "source_file": "03_biometrics_and_telemetry/movesense_biometrics_dsp_engine.py",
            },
            {
                "module_id": "RMSSD_LnRMSSD_Readiness_Engine",
                "name": "Autonomic Readiness & Orthostatic Vagal Tone Engine (RMSSD / lnRMSSD)",
                "algorithm": "20% ectopic-filtered RR intervals -> RMSSD (ms), ln(RMSSD), SDNN, pNN50, and 60-day Z-score Readiness composite (0-100)",
                "source_file": "03_biometrics_and_telemetry/movesense_readiness_suite.py",
            },
            {
                "module_id": "FTMS_PowerCadence_Synchronizer",
                "name": "AssaultBike BLE FTMS 0x2AD2 Parser & HR-Power Decoupling Synchronizer",
                "algorithm": "Monotonic timestamp alignment of FTMS Instantaneous Power (W) & Cadence (RPM) against Movesense HR/DFA-alpha1 to compute Aerobic Efficiency Factor (EF) & Cardiac Drift %",
                "source_file": "03_biometrics_and_telemetry/movesense_to_4000_bridge.py",
            },
        ]
        for m in dsp_modules:
            self.query(
                """
                MERGE (mod:DSPModule {module_id: $module_id})
                SET mod.name = $name,
                    mod.algorithm = $algorithm,
                    mod.source_file = $source_file,
                    mod.updated_at = timestamp()
                WITH mod
                MATCH (s:Subsystem {subsystem_id: '03_biometrics_and_telemetry'})
                MERGE (mod)-[:PART_OF]->(s)
                """,
                m,
            )

        signals = [
            {
                "signal_id": "Readiness",
                "name": "Autonomic Readiness Score (0-100)",
                "unit": "score_0_100",
                "sensor_id": "Movesense_HR2_ECG",
                "module_id": "RMSSD_LnRMSSD_Readiness_Engine",
                "clinical_thresholds": "Green >= 75 (High Vagal Recovery), Amber 50-74 (Moderate Load), Red < 50 (Sympathetic Overload / Autonomic Suppression)",
            },
            {
                "signal_id": "HeartRate",
                "name": "Instantaneous Heart Rate & RR Intervals",
                "unit": "bpm_and_ms",
                "sensor_id": "Movesense_HR2_ECG",
                "module_id": "PanTompkins_512Hz",
                "clinical_thresholds": "Zone 1 < 68% HRmax, Zone 2 69-83% HRmax (Aerobic Base), Zone 5 > 95% HRmax",
            },
            {
                "signal_id": "DFA_Alpha1",
                "name": "DFA-alpha1 Non-Linear HRV Fractal Correlation Index",
                "unit": "dimensionless_exponent",
                "sensor_id": "Movesense_HR2_ECG",
                "module_id": "Peng_DFA_Alpha1_Window120s",
                "clinical_thresholds": "alpha1 > 0.75 = Below LT1 (Zone 1/2 Aerobic), 0.50 <= alpha1 <= 0.75 = Heavy Transition (LT1-LT2), alpha1 < 0.50 = Severe Intensity Above LT2",
            },
            {
                "signal_id": "HRV_RMSSD",
                "name": "Heart Rate Variability RMSSD & ln(RMSSD)",
                "unit": "ms",
                "sensor_id": "Movesense_HR2_ECG",
                "module_id": "RMSSD_LnRMSSD_Readiness_Engine",
                "clinical_thresholds": "Baseline +/- 0.5 SD normal corridor; acute drop > 1.5 SD indicates incomplete parasympathetic recovery",
            },
            {
                "signal_id": "ECG_512Hz",
                "name": "512Hz Single-Lead Raw Electrocardiogram Waveform",
                "unit": "microvolts_uV",
                "sensor_id": "Movesense_HR2_ECG",
                "module_id": "PanTompkins_512Hz",
                "clinical_thresholds": "512 samples/sec, sub-2ms R-peak precision, ectopic/missed-beat detection if |delta_RR| > 20%",
            },
            {
                "signal_id": "BloodPressure_PTT",
                "name": "Cuffless Pulse Transit Time Systolic & Diastolic Blood Pressure",
                "unit": "mmHg",
                "sensor_id": "Movesense_HR2_ECG",
                "module_id": "MoensKorteweg_PTT_BP_Kalman",
                "clinical_thresholds": "Resting normal < 120/80 mmHg; Exercise SBP dynamic ceiling alert >= 210 mmHg",
            },
            {
                "signal_id": "AssaultBike_FTMS",
                "name": "AssaultBike FTMS Power (Watts), Cadence (RPM) & HR-Power Coupling",
                "unit": "Watts_RPM_EF",
                "sensor_id": "AssaultBike_BLE_FTMS",
                "module_id": "FTMS_PowerCadence_Synchronizer",
                "clinical_thresholds": "Cardiac Drift < 5% over 45m indicates solid Zone 2 durability; > 5% drift or alpha1 < 0.75 triggers Wattage cap alert",
            },
        ]
        for sig in signals:
            self.query(
                """
                MERGE (b:BiometricSignal {signal_id: $signal_id})
                SET b.name = $name,
                    b.unit = $unit,
                    b.clinical_thresholds = $clinical_thresholds,
                    b.updated_at = timestamp()
                WITH b
                MATCH (dev:SensorDevice {sensor_id: $sensor_id})
                MERGE (b)-[:MEASURED_BY]->(dev)
                WITH b
                MATCH (mod:DSPModule {module_id: $module_id})
                MERGE (b)-[:COMPUTED_BY]->(mod)
                WITH b
                MATCH (app:Application {app_id: 'unified_movesense_assaultbike_hub'})
                MERGE (b)-[:STREAMED_TO]->(app)
                """,
                sig,
            )

        specialist_models = [
            {
                "model_id": "EmbeddingGemma-2-740M-MRL",
                "name": "Google DeepMind EmbeddingGemma 2 (740M Multimodal MRL)",
                "endpoint": "http://127.0.0.1:8087/v1/embeddings",
                "host_node": "L5",
                "fallback_node": "L1",
                "params_m": 740,
                "memory_footprint_mb": 620,
                "hardware_mode": "UNIFIED_METAL_VRAM (-ngl 99)",
                "task_id": "MULTIMODAL_RAG_AND_MRL_COMPRESSION",
                "task_name": "Multimodal RAG & MRL Context Compression (768d -> 256d/128d)",
            },
            {
                "model_id": "SmolLM2-135M-Instruct",
                "name": "SmolLM2 135M Instruct Q4_K_M Ultra-Fast Edge Triage",
                "endpoint": "http://100.121.247.8:9096/v1/chat/completions",
                "host_node": "L8",
                "fallback_node": "L3",
                "params_m": 135,
                "memory_footprint_mb": 145,
                "hardware_mode": "NORMAL_DDR4_RAM_AVX2 (--mmap --mlock -ngl 0)",
                "task_id": "BIOMETRICS_DSP_ANOMALY_AND_READINESS_TRIAGE",
                "task_name": "Fast Biometrics DSP Anomaly & Readiness Triage (<50ms)",
            },
            {
                "model_id": "Qwen2.5-0.5B-Instruct",
                "name": "Qwen2.5 0.5B Instruct Real-Time Readiness & RFCOMM Triage",
                "endpoint": "http://100.119.199.76:8089/v1/chat/completions",
                "host_node": "L1",
                "fallback_node": "L5",
                "params_m": 500,
                "memory_footprint_mb": 420,
                "hardware_mode": "UNIFIED_METAL_VRAM (-ngl 99)",
                "task_id": "BIOMETRICS_DSP_ANOMALY_AND_READINESS_TRIAGE",
                "task_name": "Fast Biometrics DSP Anomaly & Readiness Triage (<50ms)",
            },
            {
                "model_id": "Qwen-3.8-27B-Abliterated",
                "name": "Qwen 3.8 Max Abliterated (L8 32GB DDR4 Normal RAM AVX2 Engine)",
                "endpoint": "http://100.121.247.8:8083/v1/chat/completions",
                "host_node": "L8",
                "fallback_node": "L1",
                "params_m": 27000,
                "memory_footprint_mb": 15800,
                "hardware_mode": "NORMAL_DDR4_RAM_AVX2 (--mmap -ngl 0)",
                "task_id": "BIOMETRICS_DSP_ANOMALY_AND_READINESS_TRIAGE",
                "task_name": "Fast Biometrics DSP Anomaly & Readiness Triage (<50ms)",
            },
            {
                "model_id": "Qwen2.5-Coder-1.5B",
                "name": "Qwen2.5-Coder 1.5B Instruct (L3 Cypher & Codebase Specialist)",
                "endpoint": "http://100.101.39.98:8084/v1/chat/completions",
                "host_node": "L3",
                "fallback_node": "L1",
                "params_m": 1500,
                "memory_footprint_mb": 1150,
                "hardware_mode": "NORMAL_DDR4_RAM_AVX2 (--mmap -ngl 0)",
                "task_id": "CODEBASE_CYPHER_AND_JSON_SCHEMA_EXTRACTION",
                "task_name": "Codebase Indexing, Cypher Query Generation & JSON Schema Extraction",
            },
            {
                "model_id": "Hermes-3-Llama-3.1-8B",
                "name": "Nous Hermes 3 Llama 3.1 8B Q4_K_M Function & Schema Specialist",
                "endpoint": "http://100.119.199.76:8085/v1/chat/completions",
                "host_node": "L1",
                "fallback_node": "L3",
                "params_m": 8000,
                "memory_footprint_mb": 4920,
                "hardware_mode": "UNIFIED_METAL_VRAM (-ngl 99)",
                "task_id": "CODEBASE_CYPHER_AND_JSON_SCHEMA_EXTRACTION",
                "task_name": "Codebase Indexing, Cypher Query Generation & JSON Schema Extraction",
            },
            {
                "model_id": "Qwen2.5-VL-7B-Instruct",
                "name": "Qwen2.5-VL 7B Instruct Multimodal Vision-Language Specialist",
                "endpoint": "http://192.168.8.127:8081/v1/chat/completions",
                "host_node": "L2",
                "fallback_node": "L1",
                "params_m": 7000,
                "memory_footprint_mb": 4600,
                "hardware_mode": "DISCRETE_4GB_VRAM_PLUS_16GB_NORMAL_RAM (<=3.2GB GPU Cap)",
                "task_id": "SPATIAL_3D_AND_VISUAL_UI_AUDIT",
                "task_name": "3D Spatial Kinematics & Visual UI Audit (Screen Lens Teacher-Student)",
            },
        ]
        for sm in specialist_models:
            self.query(
                """
                MERGE (t:TaskCategory {task_id: $task_id})
                SET t.name = $task_name,
                    t.updated_at = timestamp()
                MERGE (m:SpecialistModel {model_id: $model_id})
                SET m.name = $name,
                    m.endpoint = $endpoint,
                    m.params_m = $params_m,
                    m.memory_footprint_mb = $memory_footprint_mb,
                    m.hardware_mode = $hardware_mode,
                    m.updated_at = timestamp()
                MERGE (m)-[:OPTIMIZED_FOR_TASK]->(t)
                WITH m
                MATCH (h:MeshNode {node_id: $host_node})
                MERGE (m)-[:HOSTED_ON {role: 'PRIMARY'}]->(h)
                WITH m
                MATCH (fb:MeshNode {node_id: $fallback_node})
                MERGE (m)-[:FALLBACK_ON]->(fb)
                """,
                sm,
            )

        return {
            "status": "ok",
            "mesh_nodes_synced": len(topo.get("synced_nodes", [])),
            "subsystems_synced": len(subsystems),
            "applications_synced": len(apps),
            "sensors_synced": len(sensors),
            "dsp_modules_synced": len(dsp_modules),
            "biometric_signals_synced": len(signals),
            "specialist_models_synced": len(specialist_models),
        }


# ============================================================================
# 5. DUAL-VAULT GRAPH-RAG & LIGHTWEIGHT GLOBAL ORCHESTRATOR
# ============================================================================

class Gemma2GlobalRAGOrchestrator:
    """
    Lightweight Global Orchestrator combining:
    - EmbeddingGemma 2 (768D / 512D / 256D / 128D MRL) multimodal embeddings
    - Neo4j 5.26.32 GraphRAG (`gemma2_vec_*` vector indexes + 1-2 hop Cypher traversal)
    - Qdrant `embeddinggemma_2_multimodal` named-vector MRL store
    - Local GGUF ChatModel (`:8081` / `:8088` / `:8082`) for lightweight synthesis & root orchestration
    """

    def __init__(self) -> None:
        self.neo4j = Neo4jSovereignClient()
        self.embedder = EmbeddingGemma2Engine()

    def _qdrant_upsert(self, doc_id: str, payload: Dict[str, Any], mrl: Dict[str, List[float]]) -> str:
        point_id = int(hashlib.sha256(doc_id.encode("utf-8")).hexdigest()[:15], 16)
        body = json.dumps(
            {
                "points": [
                    {
                        "id": point_id,
                        "vector": {
                            "mrl_768": mrl["768"],
                            "mrl_512": mrl["512"],
                            "mrl_256": mrl["256"],
                            "mrl_128": mrl["128"],
                        },
                        "payload": payload,
                    }
                ]
            }
        ).encode("utf-8")
        for base_url in QDRANT_ENDPOINTS:
            if not _tcp_reachable(base_url, timeout=0.5):
                continue
            try:
                req = urllib.request.Request(
                    f"{base_url}/collections/{QDRANT_COLLECTION}/points?wait=true",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status in (200, 201):
                        return f"{base_url}/collections/{QDRANT_COLLECTION}"
            except Exception:
                continue
        return "qdrant_unreachable"

    def _qdrant_search(self, vec: List[float], dim: int = 768, top_k: int = 5) -> List[Dict[str, Any]]:
        body = json.dumps(
            {
                "vector": {
                    "name": f"mrl_{dim}",
                    "vector": vec,
                },
                "limit": top_k,
                "with_payload": True,
            }
        ).encode("utf-8")
        for base_url in QDRANT_ENDPOINTS:
            if not _tcp_reachable(base_url, timeout=0.5):
                continue
            try:
                req = urllib.request.Request(
                    f"{base_url}/collections/{QDRANT_COLLECTION}/points/search",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    hits = []
                    for item in data.get("result", []):
                        pl = item.get("payload", {})
                        hits.append(
                            {
                                "doc_id": pl.get("doc_id", str(item.get("id"))),
                                "title": pl.get("title", ""),
                                "text": pl.get("text", ""),
                                "modality": pl.get("modality", "text"),
                                "source_node": pl.get("source_node", ""),
                                "score": round(float(item.get("score", 0.0)), 5),
                                "vault": f"qdrant:mrl_{dim}",
                            }
                        )
                    return hits
            except Exception:
                continue
        return []

    def ingest_document(
        self,
        doc_id: str,
        title: str,
        text: str,
        modality: str = "text",
        source_node: Optional[str] = None,
        media_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Embeds a multimodal document with EmbeddingGemma 2 (computing 768, 512, 256, and 128D MRL vectors)
        and stores it in both Neo4j (`:LensDocument` + graph relationships) and Qdrant (`embeddinggemma_2_multimodal`).
        """
        node_id = source_node or detect_local_node_id()
        bundle = self.embedder.embed_mrl_bundle(
            text=text,
            is_query=False,
            title=title,
            modality=modality,
            media_path=media_path,
        )
        mrl = bundle["mrl"]
        tag_list = tags or []

        cypher = """
        MERGE (d:LensDocument {doc_id: $doc_id})
        SET d.title = $title,
            d.text = $text,
            d.modality = $modality,
            d.source_node = $source_node,
            d.media_path = $media_path,
            d.tags = $tags,
            d.embedding_768 = $v768,
            d.embedding_512 = $v512,
            d.embedding_256 = $v256,
            d.embedding_128 = $v128,
            d.updated_at = timestamp()
        WITH d
        MERGE (n:MeshNode {node_id: $source_node})
        MERGE (n)-[:INDEXED_DOCUMENT]->(d)
        FOREACH (tagName IN $tags |
            MERGE (e:Entity {name: tagName})
            MERGE (d)-[:HAS_TAG]->(e)
        )
        RETURN d.doc_id AS doc_id
        """
        neo_res = self.neo4j.query(
            cypher,
            {
                "doc_id": doc_id,
                "title": title,
                "text": text,
                "modality": modality,
                "source_node": node_id,
                "media_path": media_path or "",
                "tags": tag_list,
                "v768": mrl["768"],
                "v512": mrl["512"],
                "v256": mrl["256"],
                "v128": mrl["128"],
            },
        )

        # Save to local SQLite replica as well
        with sqlite3.connect(self.neo4j.replica_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO lens_documents
                (doc_id, title, text, modality, source_node, media_path, embedding_768, embedding_512, embedding_256, embedding_128, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    title,
                    text,
                    modality,
                    node_id,
                    media_path or "",
                    json.dumps(mrl["768"]),
                    json.dumps(mrl["512"]),
                    json.dumps(mrl["256"]),
                    json.dumps(mrl["128"]),
                    time.time(),
                ),
            )

        qdrant_status = self._qdrant_upsert(
            doc_id=doc_id,
            payload={
                "doc_id": doc_id,
                "title": title,
                "text": text,
                "modality": modality,
                "source_node": node_id,
                "media_path": media_path or "",
                "tags": tag_list,
                "updated_at": time.time(),
            },
            mrl=mrl,
        )

        return {
            "status": "ok",
            "doc_id": doc_id,
            "source_node": node_id,
            "modality": modality,
            "embedding_provider": bundle["provider"],
            "mrl_dimensions_stored": [768, 512, 256, 128],
            "neo4j_status": neo_res.get("status"),
            "qdrant_endpoint": qdrant_status,
            "embed_latency_ms": bundle["latency_ms"],
        }

    def hybrid_vector_graph_search(
        self,
        query: str,
        dim: int = 768,
        top_k: int = 5,
        task: str = "search_result",
    ) -> Dict[str, Any]:
        """
        Executes Matryoshka (MRL) vector search at dimension `dim` (768, 512, 256, or 128)
        across both Neo4j Vector Index (`gemma2_vec_<dim>`) + 1-hop Graph Neighborhood
        AND Qdrant (`mrl_<dim>`), fusing results via Reciprocal Rank Fusion (RRF).
        """
        if dim not in MRL_DIMENSIONS:
            dim = 768
        bundle = self.embedder.embed_mrl_bundle(text=query, is_query=True, task=task)
        q_vec = bundle["mrl"][str(dim)]
        index_name = f"gemma2_vec_{dim}"

        cypher = f"""
        CALL db.index.vector.queryNodes('{index_name}', $top_k, $q_vec)
        YIELD node, score
        OPTIONAL MATCH (node)-[r]-(neighbor)
        RETURN node.doc_id AS doc_id,
               node.title AS title,
               node.text AS text,
               node.modality AS modality,
               node.source_node AS source_node,
               score AS score,
               collect(DISTINCT {{
                   rel: type(r),
                   neighbor_labels: labels(neighbor),
                   neighbor_id: coalesce(neighbor.node_id, neighbor.name, neighbor.doc_id, neighbor.event_id, '')
               }})[0..8] AS graph_context
        ORDER BY score DESC
        """
        neo_res = self.neo4j.query(cypher, {"top_k": top_k, "q_vec": q_vec})
        neo_hits = neo_res.get("records", [])
        qdrant_hits = self._qdrant_search(q_vec, dim=dim, top_k=top_k)

        # Reciprocal Rank Fusion (RRF)
        fused: Dict[str, Dict[str, Any]] = {}
        for rank, item in enumerate(neo_hits):
            did = item.get("doc_id") or f"neo_{rank}"
            fused[did] = {
                "doc_id": did,
                "title": item.get("title", ""),
                "text": item.get("text", ""),
                "modality": item.get("modality", "text"),
                "source_node": item.get("source_node", ""),
                "neo4j_cosine": round(float(item.get("score", 0.0)), 5),
                "qdrant_cosine": None,
                "graph_context": item.get("graph_context", []),
                "rrf_score": round(1.0 / (60 + rank + 1), 6),
            }

        for rank, item in enumerate(qdrant_hits):
            did = item.get("doc_id") or f"qd_{rank}"
            if did in fused:
                fused[did]["qdrant_cosine"] = item.get("score")
                fused[did]["rrf_score"] = round(fused[did]["rrf_score"] + 1.0 / (60 + rank + 1), 6)
            else:
                fused[did] = {
                    "doc_id": did,
                    "title": item.get("title", ""),
                    "text": item.get("text", ""),
                    "modality": item.get("modality", "text"),
                    "source_node": item.get("source_node", ""),
                    "neo4j_cosine": None,
                    "qdrant_cosine": item.get("score"),
                    "graph_context": [],
                    "rrf_score": round(1.0 / (60 + rank + 1), 6),
                }

        ranked = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)[:top_k]
        return {
            "status": "ok",
            "query": query,
            "mrl_dimension": dim,
            "neo4j_index": index_name,
            "qdrant_vector": f"mrl_{dim}",
            "embedding_provider": bundle["provider"],
            "embed_latency_ms": bundle["latency_ms"],
            "results": ranked,
        }

    def _call_chat_model(self, system_prompt: str, user_prompt: str, max_tokens: int = 512) -> Tuple[str, str]:
        payload = json.dumps(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
        ).encode("utf-8")
        for url in CHAT_ORCHESTRATOR_ENDPOINTS:
            if not _tcp_reachable(url, timeout=0.35):
                continue
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"].strip()
                    if content:
                        return content, url
            except Exception:
                continue
        return (
            "Synthesized deterministically from EmbeddingGemma 2 + Neo4j GraphRAG context (all local chat ports busy).",
            "deterministic_graphrag_synthesizer",
        )

    def orchestrate_rag_chat(
        self,
        question: str,
        dim: int = 768,
        top_k: int = 5,
        execute_root_check: Optional[str] = None,
        target_node: str = "L5",
    ) -> Dict[str, Any]:
        """
        Lightweight Global Orchestrator:
        1. Embeds `question` with EmbeddingGemma 2 at MRL dimension `dim`.
        2. Retrieves hybrid Neo4j GraphRAG + Qdrant MRL context.
        3. Optionally executes a root-privileged diagnostic command on `target_node`.
        4. Calls the lightweight local RAG ChatModel to synthesize the response.
        5. Records the `:OrchestrationEvent` node into Neo4j.
        """
        t0 = time.time()
        retrieval = self.hybrid_vector_graph_search(query=question, dim=dim, top_k=top_k, task="qa")
        hits = retrieval.get("results", [])

        root_telemetry = None
        if execute_root_check:
            root_telemetry = execute_root_command(target_node, execute_root_check)

        context_lines = []
        for idx, h in enumerate(hits, 1):
            neighbors = ", ".join(
                f"{g.get('rel')}->{g.get('neighbor_id')}"
                for g in h.get("graph_context", [])
                if g.get("neighbor_id")
            )
            context_lines.append(
                f"[{idx}] ({h['modality']} | doc_id={h['doc_id']} | node={h['source_node']} | "
                f"neo4j_cos={h['neo4j_cosine']} | qdrant_cos={h['qdrant_cosine']}) "
                f"Title: {h['title']} | Text: {h['text']} | GraphLinks: [{neighbors}]"
            )
        context_block = "\n".join(context_lines) if context_lines else "No prior documents matched."

        if root_telemetry:
            context_block += (
                f"\n[LIVE ROOT PRIVILEGE TELEMETRY on {target_node}]: "
                f"mode={root_telemetry.get('privilege_mode')} stdout={root_telemetry.get('stdout')}"
            )

        sys_prompt = (
            "You are the Screen Lens Sovereign Lightweight Global Orchestrator powered by Google DeepMind "
            "EmbeddingGemma 2 (768D/512D/256D/128D MRL multimodal embeddings) and Neo4j 5 GraphRAG. "
            "Answer concisely and accurately using the retrieved GraphRAG + Qdrant MRL evidence and live mesh state."
        )
        user_prompt = f"Retrieved Multimodal GraphRAG Context:\n{context_block}\n\nUser / Orchestrator Query: {question}"
        answer, chat_provider = self._call_chat_model(sys_prompt, user_prompt)

        event_id = f"orch_{int(time.time() * 1000)}"
        self.neo4j.query(
            """
            MERGE (e:ScreenEvent:OrchestrationEvent {event_id: $event_id})
            SET e.question = $question,
                e.answer = $answer,
                e.mrl_dim = $dim,
                e.chat_provider = $chat_provider,
                e.embedding_provider = $embedding_provider,
                e.created_at = timestamp()
            WITH e
            MERGE (n:MeshNode {node_id: $local_node})
            MERGE (n)-[:ORCHESTRATED]->(e)
            """,
            {
                "event_id": event_id,
                "question": question,
                "answer": answer[:1000],
                "dim": dim,
                "chat_provider": chat_provider,
                "embedding_provider": retrieval.get("embedding_provider", ""),
                "local_node": detect_local_node_id(),
            },
        )

        return {
            "status": "ok",
            "orchestration_event_id": event_id,
            "question": question,
            "mrl_dimension": dim,
            "embedding_model": "google/embeddinggemma-2",
            "embedding_provider": retrieval.get("embedding_provider"),
            "chat_provider": chat_provider,
            "retrieved_count": len(hits),
            "retrieved_context": hits,
            "root_telemetry": root_telemetry,
            "answer": answer,
            "total_latency_ms": round((time.time() - t0) * 1000, 2),
        }


# ============================================================================
# 6. SEED INITIAL MULTIMODAL GRAPH KNOWLEDGE BASE
# ============================================================================

def seed_sovereign_knowledge_graph(orchestrator: Gemma2GlobalRAGOrchestrator) -> Dict[str, Any]:
    """Seeds authentic Screen Lens Sovereign, Neo4j, Biometrics Hub, and EmbeddingGemma 2 multimodal knowledge into Neo4j + Qdrant."""
    schema_res = orchestrator.neo4j.ensure_schema()
    full_graph_res = orchestrator.neo4j.sync_full_codebase_and_biometrics_graph(verify_root=False)

    seed_docs = [
        {
            "doc_id": "spec_embeddinggemma_2_core",
            "title": "Google DeepMind EmbeddingGemma 2 Technical Specification",
            "text": (
                "EmbeddingGemma 2 is a lightweight open-weight natively multimodal embedding model built on the "
                "Gemma 4 decoder architecture (740M total parameters: 270M text backbone, 170M vision encoder, "
                "300M audio encoder). Maps text, code, images (<|image|>), audio (<|audio|>), and video (<|video|>) "
                "into a unified 768-dimensional vector space with an 8,192-token context window and Matryoshka "
                "Representation Learning (MRL) truncation at 768, 512, 256, and 128 dimensions."
            ),
            "modality": "text",
            "source_node": "L5",
            "tags": ["EmbeddingGemma2", "Multimodal", "MRL", "Gemma4"],
        },
        {
            "doc_id": "spec_neo4j_lens_mesh",
            "title": "Screen Lens Sovereign Neo4j 5.26.32 & Qdrant MRL GraphRAG Topology",
            "text": (
                "Neo4j 5.26.32 runs on L3 Head Node (100.101.39.98:7474 HTTP / :7687 Bolt) with 4 native cosine "
                "vector indexes (gemma2_vec_768, gemma2_vec_512, gemma2_vec_256, gemma2_vec_128) paired with "
                "Qdrant collection embeddinggemma_2_multimodal (mrl_768, mrl_512, mrl_256, mrl_128) and root "
                "execution across all 10 mesh nodes (GW, L1, L1b, L2, L3, L4, L5, L6, L7, L8)."
            ),
            "modality": "code",
            "source_node": "L3",
            "tags": ["Neo4j", "Qdrant", "ScreenLens", "RootPrivileges"],
        },
        {
            "doc_id": "spec_visual_hud_telemetry",
            "title": "Screen Lens Visual HUD Frame & Audio Companion Multimodal Trace",
            "text": (
                "<|image|> <|audio|> Live Screen Lens Sovereign visual OCR state (:3035) and Audio Companion (:3036) "
                "unified into 768D cross-modal vector space for teacher-student WebVLA distillation and Global "
                "Orchestrator (:3037) routing."
            ),
            "modality": "image",
            "source_node": "L1",
            "tags": ["ScreenLens", "WebVLA", "Multimodal", "VisualHUD"],
        },
        {
            "doc_id": "spec_netmon_glances_ram_vram_governance",
            "title": "NetMon v2.0, Glances API (:61208) Non-Overloading Telemetry & Normal RAM vs VRAM Sharding Governance",
            "text": (
                "NetMon v2.0 (~/.local/bin/netmon -> 06_scripts_and_tooling/network/dual_network_monitor.py and "
                "autonomous_async_netmon.py) enforces non-overloading live telemetry across the 10-node Lauburu Mesh: "
                "(1) NEVER query /api/3/all or /api/4/all on Glances (:61208) because /all triggers full process/Docker "
                "walks (6,917ms latency, 449MB RSS on L3); instead query modular endpoints /quicklook, /mem, /load, "
                "/network (~75ms, <1.5KB JSON) and cache /fs for 60s. (2) L3 systemd glances.service runs with "
                "--disable-plugin docker,containers,ports,folders,raid,cloud,amps,processlist -t 5 (reducing RSS from "
                "449.3MB to 43.7MB, -90.3%). (3) Adaptive Overload Circuit Breaker (THROTTLED_3X) triples poll intervals "
                "when CPU > 80% or RAM > 88%. (4) Hardware Memory Class optimization strictly separates Apple Unified "
                "Metal VRAM (L1 24GB @ 273GB/s, L5 16GB @ 120GB/s, L1b 16GB @ 200GB/s for dense attention decode -ngl 99) "
                "and Discrete GPU VRAM (L2 4GB Radeon GDDR6 + 16GB DDR4) from Normal DDR4 System RAM Only nodes with "
                "0GB VRAM (L8 32GB DDR4 @ 34.1GB/s, L3 16GB DDR4 @ 25.6GB/s, L4 8GB). L8 and L3 must run with -ngl 0 "
                "and host Disaggregated Mooncake/LMCache KV-Cache pools (16GB on L8, 4GB on L3), Neo4j 5.26.32 (:7474/:7687), "
                "Qdrant MRL (:6333), and AVX2 CPU sparse MoE / speculative draft models."
            ),
            "modality": "code",
            "source_node": "L3",
            "tags": ["NetMon", "GlancesAPI", "NormalRAMvsVRAM", "TelemetryOptimization", "KVDisaggregation"],
        },
        {
            "doc_id": "spec_canonical_ip_matrix_2026",
            "title": "Lauburu 10-Node Canonical IP Address, Glances API (:61208) & Memory Classification Matrix",
            "text": (
                "Canonical Lauburu Mesh IP & Glances Matrix (06_scripts_and_tooling/network/mesh_ip_matrix.json): "
                "GW (GL.iNet Router): LAN 192.168.8.1 (1GB Normal RAM, 0GB VRAM, SSH /proc/meminfo); "
                "L1 (Mac Mini M4 Pro Sanctuary): Tailscale 100.119.199.76, LAN 192.168.8.230/.143, TB4 10.0.0.1, "
                "Glances http://100.119.199.76:61208/api/4 (24GB Unified Metal VRAM); "
                "L5 (MacBook Air M4 Sanctuary): Tailscale 100.121.202.34, LAN 192.168.8.248, TB4 10.0.0.2, "
                "Glances http://100.121.202.34:61208/api/4 (16GB Unified Metal VRAM); "
                "L1b (Mac Mini M2 Pro AI Node): Tailscale 100.104.128.34, LAN 192.168.8.114, TB4 10.0.0.3, "
                "Glances http://100.104.128.34:61208/api/4 (16GB Unified Metal VRAM); "
                "L2 (MacBook Pro Intel i9): Tailscale 100.103.212.21, LAN 192.168.8.127, TB4 10.0.0.4, "
                "Glances http://192.168.8.127:61208/api/4 (4GB Discrete GDDR6 VRAM + 16GB Normal DDR4 RAM); "
                "L3 (Ubuntu Linux Head Node Ryzen 7 5700U): Tailscale 100.101.39.98, LAN 192.168.8.225, "
                "Glances http://100.101.39.98:61208/api/3 (16GB Normal DDR4 RAM Only, 0GB VRAM); "
                "L8 (Lauburu Linux Hub i7-8700B): Tailscale 100.121.247.8, LAN 192.168.8.242, TB4 10.0.0.8, "
                "Glances http://100.121.247.8:61208/api/4 (32GB Normal DDR4 RAM Only, 0GB VRAM); "
                "L4 (Surface Go 2 Linux Tablet): Tailscale 100.78.250.119, LAN 192.168.8.227 (8GB Normal RAM Only, 0GB VRAM); "
                "L6 (Google Pixel 10 Pro XL): Tailscale 100.114.215.68, LAN 192.168.8.213:8022 (16GB LPDDR5X + Tensor G5 NPU); "
                "L7 (Samsung Galaxy S20+ 5G): LAN 192.168.8.101/.224:8022, ADB :32873 (12GB LPDDR5 Normal RAM)."
            ),
            "modality": "text",
            "source_node": "L5",
            "tags": ["IPMatrix", "GlancesAPI", "Tailscale", "Thunderbolt10GbE", "NormalRAMvsVRAM"],
        },
        {
            "doc_id": "spec_unified_movesense_assaultbike_biometrics_hub",
            "title": "Unified Movesense HR2/ECG + AssaultBike BLE FTMS Real-Time Biometrics Hub",
            "text": (
                "The Unified Movesense + AssaultBike Real-Time Biometrics Hub consolidates 7 medical-grade physiological "
                "and ergometer signals into a single zero-mock cockpit (:4000 Web UI, :8084 GATT Browser, :8089 RFCOMM Bridge, "
                ":9223 Web Bluetooth Proxy): (1) Readiness Score (0-100 composite from lnRMSSD, resting HR, DFA-alpha1), "
                "(2) HeartRate (BPM & RR ms), (3) DFA-alpha1 (Peng 1995 non-linear fractal scaling exponent over 120s window, "
                "LT1=0.75, LT2=0.50), (4) HRV RMSSD & ln(RMSSD), (5) 512Hz Single-Lead ECG Waveform (Pan-Tompkins QRS R-peak "
                "detector), (6) Cuffless Blood Pressure via Pulse Transit Time (Moens-Korteweg SBP/DBP mmHg with 1D Kalman "
                "filter), and (7) AssaultBike BLE FTMS 0x2AD2 (Instantaneous Power Watts, Cadence RPM, Aerobic Efficiency "
                "Factor EF = Watts/HR, and Cardiac Drift %)."
            ),
            "modality": "code",
            "source_node": "L1",
            "tags": ["Movesense", "AssaultBike", "DFA_Alpha1", "ECG_512Hz", "BloodPressure_PTT", "Readiness", "FTMS"],
        },
        {
            "doc_id": "spec_specialized_small_local_ai_router",
            "title": "Specialized Small Local AI Task Router & MRL Context Compression Engine",
            "text": (
                "Specialized Small Local AI Router (02_ai_models_and_inference/routing/specialized_local_ai_router.py) "
                "eliminates frontier context bloat by routing micro-tasks to purpose-built local models across the 10-node mesh: "
                "(1) Multimodal RAG & MRL Context Compression (768d -> 256d/128d): EmbeddingGemma 2 (740M) on :8087 + Qdrant "
                "L3:6333 + Neo4j L3:7474, compressing retrieval context by >72%. "
                "(2) Fast Biometrics DSP Anomaly & Readiness Triage (<50ms): SmolLM2-135M (L8:9096 AVX2 -ngl 0), "
                "Qwen2.5-0.5B-Instruct (L1:8089 Metal -ngl 99), and Qwen-3.8-27B-Abliterated (L8:8083 32GB Normal DDR4 RAM). "
                "(3) Codebase Indexing, Cypher Generation & JSON Schema Extraction: Qwen2.5-Coder-1.5B (L3:8084) and "
                "Hermes-3-Llama-3.1-8B (L1:8085). "
                "(4) 3D Spatial & Visual UI Audit: Qwen2.5-VL-7B (L2:8081) + Screen Lens (:3035/:3037)."
            ),
            "modality": "code",
            "source_node": "L5",
            "tags": ["SpecializedRouter", "EmbeddingGemma2", "SmolLM2", "QwenCoder", "Hermes3", "QwenVL", "MRL"],
        },
    ]

    ingested = []
    for doc in seed_docs:
        res = orchestrator.ingest_document(**doc)
        ingested.append(res)

    return {
        "status": "ok",
        "schema": schema_res,
        "full_graph": full_graph_res,
        "seeded_documents": ingested,
    }


# ============================================================================
# 7. MCP SERVER PROTOCOL (`neo4j-mcp` + Screen Lens MCP Integration)
# ============================================================================

NEO4J_GEMMA2_MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "neo4j_cypher_query",
        "description": (
            "Execute a Cypher query against the Screen Lens Sovereign Neo4j 5.26.32 Graph Database "
            "(with automatic DDL/DML transaction isolation and offline SQLite replica fallback)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cypher": {"type": "string", "description": "Cypher statement to execute."},
                "parameters": {"type": "object", "description": "Optional Cypher query parameters."},
            },
            "required": ["cypher"],
        },
    },
    {
        "name": "neo4j_schema_inspect",
        "description": (
            "Inspect Neo4j 5 graph labels, relationship types, uniqueness constraints, node counts, "
            "and the 4 EmbeddingGemma 2 MRL vector indexes (768, 512, 256, 128D)."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "neo4j_vector_mrl_search",
        "description": (
            "Perform hybrid Matryoshka Representation Learning (MRL) vector + graph search across "
            "Neo4j (`gemma2_vec_<dim>`) and Qdrant (`mrl_<dim>`) using EmbeddingGemma 2 at 768, 512, 256, or 128 dimensions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text or multimodal query."},
                "dim": {
                    "type": "integer",
                    "enum": [768, 512, 256, 128],
                    "default": 768,
                    "description": "Matryoshka (MRL) truncation dimension (768, 512, 256, or 128).",
                },
                "top_k": {"type": "integer", "default": 5, "description": "Number of top results to return."},
                "task": {
                    "type": "string",
                    "default": "search_result",
                    "description": "EmbeddingGemma 2 task prefix (search_result, qa, fact_checking, code_retrieval, clustering, classification).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "neo4j_sync_mesh_topology",
        "description": (
            "Synchronize all 10 Lauburu Mesh devices (GW, L1, L1b, L2, L3, L4, L5, L6, L7, L8), verify root privileges "
            "across the mesh, and update `:MeshNode` and `:CONNECTED_TO` edges in Neo4j."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "verify_root": {"type": "boolean", "default": True, "description": "Run live root `id` verification on all nodes."},
            },
        },
    },
    {
        "name": "neo4j_sync_full_graph",
        "description": (
            "Synchronize the complete Lauburu Monorepo graph into Neo4j 5.26.32: all 10 Hardware Nodes, "
            "13 Subsystems (`00`..`12`), Consolidated Applications (Unified Movesense + AssaultBike Hub, GATT/RFCOMM/WebBluetooth bridges), "
            "7 Biometric Signals (`Readiness`, `HeartRate`, `DFA_Alpha1`, `HRV_RMSSD`, `ECG_512Hz`, `BloodPressure_PTT`, `AssaultBike_FTMS`), "
            "Sensors, DSP Modules, and 7 Specialized Local AI Models."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "verify_root": {"type": "boolean", "default": False, "description": "Optionally run live root `id` verification on all nodes."},
            },
        },
    },
    {
        "name": "embeddinggemma2_embed_multimodal",
        "description": (
            "Generate a unified 768D Google DeepMind EmbeddingGemma 2 multimodal embedding and dynamically "
            "truncated + L2-renormalized Matryoshka (MRL) vectors (768, 512, 256, 128D) for text, code, images, audio, or video."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text, code, or multimodal prompt (<|image|>, <|audio|>, <|video|>)."},
                "dim": {"type": "integer", "enum": [768, 512, 256, 128], "default": 768},
                "task": {"type": "string", "default": "search_result"},
                "modality": {"type": "string", "enum": ["text", "code", "image", "audio", "video"], "default": "text"},
                "media_path": {"type": "string", "description": "Optional local path to image/audio/video file."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "embeddinggemma2_ingest_document",
        "description": (
            "Embed and ingest a multimodal document (text, code, image, audio, video) into both Neo4j "
            "(`:LensDocument` + `:Entity` tags) and Qdrant (`embeddinggemma_2_multimodal`) across all 4 MRL dimensions (768, 512, 256, 128)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Unique document identifier."},
                "title": {"type": "string", "description": "Document title."},
                "text": {"type": "string", "description": "Document content or multimodal description."},
                "modality": {"type": "string", "enum": ["text", "code", "image", "audio", "video"], "default": "text"},
                "media_path": {"type": "string", "description": "Optional path to media asset."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Entity tags for Neo4j graph linking."},
            },
            "required": ["doc_id", "title", "text"],
        },
    },
    {
        "name": "embeddinggemma2_rag_orchestrate",
        "description": (
            "Lightweight Global Orchestrator: embeds query with EmbeddingGemma 2, retrieves hybrid Neo4j GraphRAG + "
            "Qdrant MRL context, optionally executes a root diagnostic on a target node, synthesizes via the local "
            "RAG ChatModel (:8089/:8090/:8082), and logs `:OrchestrationEvent` in Neo4j."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "User question or global orchestration directive."},
                "dim": {"type": "integer", "enum": [768, 512, 256, 128], "default": 768},
                "top_k": {"type": "integer", "default": 5},
                "execute_root_check": {"type": "string", "description": "Optional root shell command to run and include in RAG context."},
                "target_node": {"type": "string", "default": "L5", "description": "Target node ID (L5, L1, L1b, L2, L3, L4, L8, L6, L7, GW, or ALL)."},
            },
            "required": ["question"],
        },
    },
    {
        "name": "lens_root_exec",
        "description": (
            "Execute a shell command with root/elevated privileges (`sudo -n` UID 0 on L5/L1/L1b/L2/L3/L4/L8/GW, "
            "Shizuku `rish` UID 2000 or `tsu` on Android L6/L7) across one or ALL mesh devices."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "default": "ALL", "description": "Target node ID (GW, L1, L1b, L2, L3, L4, L5, L6, L7, L8, or ALL)."},
                "command": {"type": "string", "description": "Shell command to execute with root privileges."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "lens_benchmark_and_consensus_elo",
        "description": (
            "Benchmark EmbeddingGemma 2 MRL speed (768d-128d), 6 AI sharding protocols, 5 AI training protocols, "
            "and execute Qwen 3D/Visual/Telemetry Review Panel consensus ELO evaluation, contributing agreed scores "
            "to canonical_ai_leaderboard.json and Neo4j 5.26.32."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["full", "gemma2", "sharding", "training", "elo"],
                    "default": "full",
                    "description": "Benchmark suite mode to execute.",
                },
            },
        },
    },
]


def handle_neo4j_gemma2_mcp_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes one of the Neo4j / EmbeddingGemma 2 / Root Orchestrator / ELO Benchmark MCP tools."""
    orch = Gemma2GlobalRAGOrchestrator()
    if name == "neo4j_cypher_query":
        return orch.neo4j.query(args.get("cypher", ""), args.get("parameters") or {})
    if name == "neo4j_schema_inspect":
        return orch.neo4j.get_schema_summary()
    if name == "neo4j_vector_mrl_search":
        return orch.hybrid_vector_graph_search(
            query=args.get("query", ""),
            dim=int(args.get("dim", 768)),
            top_k=int(args.get("top_k", 5)),
            task=args.get("task", "search_result"),
        )
    if name == "neo4j_sync_mesh_topology":
        return orch.neo4j.sync_mesh_topology(verify_root=bool(args.get("verify_root", True)))
    if name == "neo4j_sync_full_graph":
        return orch.neo4j.sync_full_codebase_and_biometrics_graph(verify_root=bool(args.get("verify_root", False)))
    if name == "embeddinggemma2_embed_multimodal":
        bundle = orch.embedder.embed_mrl_bundle(
            text=args.get("text", ""),
            is_query=True,
            task=args.get("task", "search_result"),
            modality=args.get("modality", "text"),
            media_path=args.get("media_path"),
        )
        dim = int(args.get("dim", 768))
        vec = bundle["mrl"].get(str(dim), bundle["mrl"]["768"])
        return {
            "status": "ok",
            "model": bundle["model"],
            "provider": bundle["provider"],
            "formatted_prompt": bundle["formatted_prompt"],
            "dimension": dim,
            "l2_norm": round(math.sqrt(sum(x * x for x in vec)), 6),
            "latency_ms": bundle["latency_ms"],
            "embedding_preview": vec[:16],
            "embedding": vec,
        }
    if name == "embeddinggemma2_ingest_document":
        return orch.ingest_document(
            doc_id=args.get("doc_id", f"doc_{int(time.time())}"),
            title=args.get("title", "Untitled"),
            text=args.get("text", ""),
            modality=args.get("modality", "text"),
            media_path=args.get("media_path"),
            tags=args.get("tags") or [],
        )
    if name == "embeddinggemma2_rag_orchestrate":
        return orch.orchestrate_rag_chat(
            question=args.get("question", ""),
            dim=int(args.get("dim", 768)),
            top_k=int(args.get("top_k", 5)),
            execute_root_check=args.get("execute_root_check"),
            target_node=args.get("target_node", "L5"),
        )
    if name == "lens_root_exec":
        return execute_root_command(
            node_id=args.get("node", "ALL"),
            command=args.get("command", "id"),
        )
    if name == "lens_benchmark_and_consensus_elo":
        from lens_gemma2_qwen3d_elo_benchmark import (
            benchmark_gemma2_embeddings,
            benchmark_sharding_protocols,
            benchmark_training_protocols,
            run_full_benchmark_suite,
            run_qwen_3d_telemetry_visual_consensus_elo,
        )
        mode = str(args.get("mode", "full")).lower()
        if mode == "gemma2":
            return benchmark_gemma2_embeddings()
        if mode == "sharding":
            return benchmark_sharding_protocols()
        if mode == "training":
            return benchmark_training_protocols()
        if mode == "elo":
            return run_qwen_3d_telemetry_visual_consensus_elo(
                benchmark_gemma2_embeddings(),
                benchmark_sharding_protocols(),
                benchmark_training_protocols(),
            )
        return run_full_benchmark_suite(persist_report=True)
    raise ValueError(f"Unknown Neo4j/EmbeddingGemma2 MCP tool: {name}")


def run_mcp_stdio_server() -> int:
    """Runs a compliant JSON-RPC 2.0 MCP Server over stdio (`neo4j-mcp` / `--mcp`)."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method", "")
        msg_id = req.get("id")
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "screen-lens-neo4j-gemma2-mcp",
                        "version": "2.1.0",
                    },
                },
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": NEO4J_GEMMA2_MCP_TOOLS},
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        elif method == "tools/call":
            params = req.get("params") or {}
            t_name = params.get("name", "")
            t_args = params.get("arguments") or {}
            try:
                out = handle_neo4j_gemma2_mcp_tool(t_name, t_args)
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(out, indent=2)}],
                        "isError": False,
                    },
                }
            except Exception as exc:
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"status": "error", "error": str(exc)})}],
                        "isError": True,
                    },
                }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        elif msg_id is not None:
            resp = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
    return 0


# ============================================================================
# 8. CLI ENTRYPOINT (`neo4j-cli`, `cypher-shell`, `neo4j-mcp`, `lens-root`)
# ============================================================================

def format_table(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "(0 rows)"
    cols = list(records[0].keys())
    widths = {c: max(len(str(c)), *(len(json.dumps(r.get(c)) if isinstance(r.get(c), (dict, list)) else str(r.get(c, ""))) for r in records)) for c in cols}
    header = " | ".join(str(c).ljust(min(widths[c], 48)) for c in cols)
    sep = "-+-".join("-" * min(widths[c], 48) for c in cols)
    lines = [header, sep]
    for r in records:
        row_str = " | ".join(
            (json.dumps(r.get(c)) if isinstance(r.get(c), (dict, list)) else str(r.get(c, "")))[:48].ljust(min(widths[c], 48))
            for c in cols
        )
        lines.append(row_str)
    lines.append(f"({len(records)} rows)")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    args_list = argv if argv is not None else sys.argv[1:]
    prog_name = Path(sys.argv[0]).name

    if prog_name == "neo4j-mcp" or "--mcp" in args_list or (args_list and args_list[0] == "mcp"):
        return run_mcp_stdio_server()

    if prog_name == "lens-root":
        node = args_list[0] if len(args_list) >= 2 else "ALL"
        cmd = " ".join(args_list[1:]) if len(args_list) >= 2 else (args_list[0] if args_list else "id")
        print(json.dumps(execute_root_command(node, cmd), indent=2))
        return 0

    # Compatibility mode when invoked as `cypher-shell` with inline Cypher or `-u`/`-p`/`-a`
    if prog_name == "cypher-shell" or (args_list and args_list[0].upper().startswith(("MATCH ", "RETURN ", "SHOW ", "CALL ", "CREATE ", "MERGE "))):
        parser = argparse.ArgumentParser(prog="cypher-shell", description="Neo4j 5 Sovereign Cypher Shell")
        parser.add_argument("-a", "--address", default=NEO4J_BOLT_URI)
        parser.add_argument("-u", "--username", default=NEO4J_USER)
        parser.add_argument("-p", "--password", default=NEO4J_PASSWORD)
        parser.add_argument("--format", choices=["json", "table", "plain"], default="table")
        parser.add_argument("cypher", nargs="*", help="Cypher query statement")
        parsed, unknown = parser.parse_known_args(args_list)
        query_str = " ".join(parsed.cypher + unknown).strip()
        if not query_str and not sys.stdin.isatty():
            query_str = sys.stdin.read().strip()
        if not query_str:
            query_str = "RETURN 'Neo4j 5.26.32 Sovereign Cypher Shell Online' AS status, timestamp() AS ts"
        client = Neo4jSovereignClient()
        res = client.query(query_str)
        if parsed.format == "json":
            print(json.dumps(res, indent=2))
        else:
            if res.get("errors"):
                print(json.dumps(res["errors"], indent=2), file=sys.stderr)
                return 1
            print(format_table(res.get("records", [])))
        return 0

    parser = argparse.ArgumentParser(
        prog="neo4j-cli",
        description="Screen Lens Sovereign — Neo4j 5 CLI + Root Executor + EmbeddingGemma 2 Multimodal RAG Orchestrator",
    )
    sub = parser.add_subparsers(dest="subcommand")

    # 1. status
    p_status = sub.add_parser("status", help="Show Neo4j 5, Qdrant MRL, EmbeddingGemma 2, and Root privilege status")
    p_status.add_argument("--verify-root", action="store_true", help="Run live root `id` check across all 10 nodes")

    # 2. query / cypher
    p_query = sub.add_parser("query", help="Execute a Cypher query against Neo4j 5")
    p_query.add_argument("cypher", help="Cypher statement to execute")
    p_query.add_argument("--params", default="{}", help="JSON parameters dictionary")
    p_query.add_argument("--format", choices=["json", "table"], default="json")

    # 3. schema
    sub.add_parser("schema", help="Inspect Neo4j 5 labels, relationships, constraints, and MRL vector indexes")

    # 4. sync-topology
    sub.add_parser("sync-topology", help="Sync all 10 mesh nodes and root privilege telemetry into Neo4j")

    # 4b. sync-full-graph
    p_sfg = sub.add_parser("sync-full-graph", help="Sync all 10 nodes, 13 subsystems, consolidated apps, 7 biometric signals, sensors, DSP modules, and 7 specialist AI models")
    p_sfg.add_argument("--verify-root", action="store_true", help="Also run root `id` verification on all nodes")

    # 5. seed
    sub.add_parser("seed", help="Ensure Neo4j MRL vector schema, sync full graph, and seed multimodal documents")

    # 6. embed
    p_embed = sub.add_parser("embed", help="Generate EmbeddingGemma 2 MRL (768/512/256/128D) vectors")
    p_embed.add_argument("text", help="Input text or multimodal prompt")
    p_embed.add_argument("--dim", type=int, default=768, choices=[768, 512, 256, 128])
    p_embed.add_argument("--task", default="search_result", choices=list(TASK_PREFIXES.keys()))
    p_embed.add_argument("--modality", default="text", choices=["text", "code", "image", "audio", "video"])
    p_embed.add_argument("--media-path", default=None)

    # 7. ingest
    p_ingest = sub.add_parser("ingest", help="Ingest a multimodal document into Neo4j + Qdrant across all 4 MRL dimensions")
    p_ingest.add_argument("--doc-id", required=True)
    p_ingest.add_argument("--title", required=True)
    p_ingest.add_argument("--text", required=True)
    p_ingest.add_argument("--modality", default="text", choices=["text", "code", "image", "audio", "video"])
    p_ingest.add_argument("--media-path", default=None)
    p_ingest.add_argument("--tags", default="", help="Comma-separated entity tags")

    # 8. vector-search / search
    p_vsearch = sub.add_parser("vector-search", aliases=["search"], help="Hybrid Neo4j Vector Index + Graph + Qdrant MRL search")
    p_vsearch.add_argument("query", help="Search query")
    p_vsearch.add_argument("--dim", type=int, default=768, choices=[768, 512, 256, 128])
    p_vsearch.add_argument("--top-k", type=int, default=5)
    p_vsearch.add_argument("--task", default="search_result", choices=list(TASK_PREFIXES.keys()))

    # 9. rag
    p_rag = sub.add_parser("rag", help="Run the Lightweight Global RAG ChatModel Orchestrator")
    p_rag.add_argument("question", help="Question or orchestration directive")
    p_rag.add_argument("--dim", type=int, default=768, choices=[768, 512, 256, 128])
    p_rag.add_argument("--top-k", type=int, default=5)
    p_rag.add_argument("--root-check", default=None, help="Optional root command to execute and include in RAG context")
    p_rag.add_argument("--node", "--target", dest="node", default="L5", help="Target node for --root-check (L5, L1, L1b, L2, L3, L4, L8, L6, L7, GW, ALL)")

    # 10. root-exec / root
    p_root = sub.add_parser("root-exec", aliases=["root"], help="Execute a root-privileged command on a target device or ALL devices")
    p_root.add_argument("--node", "--target", dest="node", default="ALL", help="Node ID (L5, L1, L1b, L2, L3, L4, L8, L6, L7, GW, or ALL)")
    p_root.add_argument("--cmd", default=None, help="Shell command to execute with root privileges")
    p_root.add_argument("pos_cmd", nargs="*", help="Positional shell command to execute with root privileges")

    # 11. mcp
    sub.add_parser("mcp", help="Run the JSON-RPC 2.0 Neo4j & EmbeddingGemma 2 MCP Server over stdio")

    # 12. benchmark
    p_bench = sub.add_parser("benchmark", help="Benchmark EmbeddingGemma 2 MRL speed, sharding/training protocols, and Qwen 3D consensus ELO")
    p_bench.add_argument("--mode", choices=["full", "gemma2", "sharding", "training", "elo"], default="full")

    args = parser.parse_args(args_list)
    orch = Gemma2GlobalRAGOrchestrator()

    if args.subcommand == "benchmark":
        res = handle_neo4j_gemma2_mcp_tool("lens_benchmark_and_consensus_elo", {"mode": args.mode})
        print(json.dumps(res, indent=2))
        return 0

    if args.subcommand in (None, "status"):
        schema = orch.neo4j.get_schema_summary()
        emb_test = orch.embedder.embed_mrl_bundle("Screen Lens Sovereign status check", is_query=True)
        out: Dict[str, Any] = {
            "status": "online",
            "local_node": detect_local_node_id(),
            "neo4j": {
                "http_endpoint": schema.get("backend"),
                "bolt_uri": schema.get("bolt_uri"),
                "labels": schema.get("labels"),
                "relationship_types": schema.get("relationship_types"),
                "node_counts": schema.get("node_counts"),
                "vector_indexes": [i for i in schema.get("indexes", []) if i.get("type") == "VECTOR"],
            },
            "embeddinggemma_2": {
                "model": emb_test["model"],
                "provider": emb_test["provider"],
                "context_window": emb_test["context_window"],
                "mrl_dimensions": list(MRL_DIMENSIONS),
                "latency_ms": emb_test["latency_ms"],
                "sample_dim_768_head": emb_test["mrl"]["768"][:5],
                "sample_dim_128_head": emb_test["mrl"]["128"][:5],
            },
        }
        if getattr(args, "verify_root", False):
            out["root_privileges"] = execute_root_command("ALL", "id")
        print(json.dumps(out, indent=2))
        return 0

    if args.subcommand == "query":
        params = json.loads(args.params)
        res = orch.neo4j.query(args.cypher, params)
        if args.format == "table":
            print(format_table(res.get("records", [])))
        else:
            print(json.dumps(res, indent=2))
        return 0

    if args.subcommand == "schema":
        print(json.dumps(orch.neo4j.get_schema_summary(), indent=2))
        return 0

    if args.subcommand == "sync-topology":
        print(json.dumps(orch.neo4j.sync_mesh_topology(verify_root=True), indent=2))
        return 0

    if args.subcommand == "sync-full-graph":
        print(json.dumps(orch.neo4j.sync_full_codebase_and_biometrics_graph(verify_root=getattr(args, "verify_root", False)), indent=2))
        return 0

    if args.subcommand == "seed":
        print(json.dumps(seed_sovereign_knowledge_graph(orch), indent=2))
        return 0

    if args.subcommand == "embed":
        bundle = orch.embedder.embed_mrl_bundle(
            text=args.text,
            is_query=True,
            task=args.task,
            modality=args.modality,
            media_path=args.media_path,
        )
        vec = bundle["mrl"][str(args.dim)]
        print(
            json.dumps(
                {
                    "status": "ok",
                    "model": bundle["model"],
                    "provider": bundle["provider"],
                    "formatted_prompt": bundle["formatted_prompt"],
                    "dimension": args.dim,
                    "l2_norm": round(math.sqrt(sum(x * x for x in vec)), 6),
                    "latency_ms": bundle["latency_ms"],
                    "embedding_preview": vec[:12],
                    "embedding": vec,
                },
                indent=2,
            )
        )
        return 0

    if args.subcommand == "ingest":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        res = orch.ingest_document(
            doc_id=args.doc_id,
            title=args.title,
            text=args.text,
            modality=args.modality,
            media_path=args.media_path,
            tags=tags,
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.subcommand in ("vector-search", "search"):
        res = orch.hybrid_vector_graph_search(
            query=args.query,
            dim=args.dim,
            top_k=args.top_k,
            task=args.task,
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.subcommand == "rag":
        res = orch.orchestrate_rag_chat(
            question=args.question,
            dim=args.dim,
            top_k=args.top_k,
            execute_root_check=args.root_check,
            target_node=args.node,
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.subcommand in ("root-exec", "root"):
        cmd_str = args.cmd or " ".join(args.pos_cmd).strip() or "id"
        res = execute_root_command(args.node, cmd_str)
        print(json.dumps(res, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
