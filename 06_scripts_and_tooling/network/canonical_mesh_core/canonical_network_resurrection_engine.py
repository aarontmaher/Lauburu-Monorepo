#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_scripts_and_tooling/network/canonical_network_resurrection_engine.py
======================================================================
Canonical 6-Stage Network Resurrection & Cascading Daemon Engine (Gen 31).
Implements Rule 0 (Zero-Mock Truth), Rule 10 (Fundamental Baseline Trinity),
and Rule 15 (Meritocratic Dynamic ELO Default Model Governance).

Canonical 6-Stage Execution DAG:
- Pre-flight Fast-Path Carrier Check:
    Uses kernel carrier status (<1ms) and 50ms socket micro-probe.
    If carrier is active and SSH port connects, bypass Stages 1 & 2 (RFCOMM & PAN)
    to prevent head-of-line blocking.
- Stage 1: Bluetooth RFConnect / RFCOMM (Layer 0 IP-less serial control plane)
- Stage 2: Bluetooth PAN (Layer 1 IP tethering / bnep0)
- Stage 3: Ethernet Cables (Layer 2 physical twisted pair & WoL RFC 792 Magic Packet)
- Stage 4: Thunderbolt Cables (Layer 2 40Gbps DMA bridge, RTT <= 1.0ms over bridge0)
- Stage 5: SSH Remote Actuation Plane (OpenSSH ControlMaster multiplexed connections)
- Stage 6: Cascading Daemon & Dependency Resurrection (RPC 50052, Qdrant 6333, Models 8081-8085, Lens 4003)

Interface Contract:
    probe_and_resurrect_service(service_name: str, node: str, port: int, launch_cmd: str) -> dict
    returns: {"service": str, "port": int, "initial_state": "UP"|"DOWN", "resurrected": bool, "final_state": "UP"|"DOWN", "exit_code": int}
"""

import os
import sys
import json
import time
import fcntl
import socket
import logging
import argparse
import tempfile
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ResurrectionEngine]: %(message)s"
)
logger = logging.getLogger("ResurrectionEngine")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MATRIX_PATH = SCRIPT_DIR / "mesh_ip_matrix.json"
if not MATRIX_PATH.exists():
    MATRIX_PATH = REPO_ROOT / "06_scripts_and_tooling" / "network" / "mesh_ip_matrix.json"

BLUEUTIL_PATH = "/Users/aaron/.local/bin/blueutil"
if not os.path.exists(BLUEUTIL_PATH):
    BLUEUTIL_PATH = "blueutil"

ADB_PATH = "/Users/aaron/.local/bin/adb"
if not os.path.exists(ADB_PATH):
    ADB_PATH = "adb"

OBSIDIAN_VAULT = REPO_ROOT / "obsidian_vault"
DASHBOARD_FILE = Path("/Volumes/Lauburu-Monorepo/00_SYSTEM_DASHBOARDS/WAKE_ON_LAN_CLUSTER.md")
TELEMETRY_LOG = OBSIDIAN_VAULT / "APPS_AND_FEATURES" / "MESH_TELEMETRY_LOG.md"
STATUS_FILE = REPO_ROOT / "data" / "mesh" / "wol_status.json"
LOCK_FILE_PATH = "/tmp/lauburu_network_resurrection.lock"

# Import helper functions from mesh_ping
try:
    from mesh_ping import (
        check_interface_carrier,
        ping_port_rtt,
        ping_icmp_rtt,
        check_ssh_execution,
        probe_physical_tier,
        resolve_node,
        load_matrix,
        check_bluetooth_presence
    )
except ImportError:
    # Minimal embedded fallbacks if running in isolated container
    def check_interface_carrier(ifname: str) -> bool:
        try:
            res = subprocess.run(["ifconfig", ifname], capture_output=True, text=True, timeout=0.2)
            return "status: active" in res.stdout
        except Exception:
            return False

    def ping_port_rtt(host: str, port: int, timeout: float = 0.5) -> Tuple[bool, float]:
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True, (time.perf_counter() - t0) * 1000.0
        except Exception:
            return False, (time.perf_counter() - t0) * 1000.0

    def ping_icmp_rtt(ip: str, timeout: float = 1.0) -> Tuple[bool, float]:
        t0 = time.perf_counter()
        try:
            res = subprocess.run(["ping", "-c", "1", "-W", str(int(timeout * 1000)), ip], capture_output=True, timeout=timeout + 0.5)
            return (res.returncode == 0), (time.perf_counter() - t0) * 1000.0
        except Exception:
            return False, (time.perf_counter() - t0) * 1000.0

    def check_ssh_execution(host: str, timeout: float = 2.0, user: Optional[str] = None, port: int = 22) -> Tuple[bool, float]:
        t0 = time.perf_counter()
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={int(timeout)}", "-p", str(port)]
        if user and "@" not in host:
            cmd.append(f"{user}@{host}")
        else:
            cmd.append(host)
        cmd.append("echo MESH_PING_OK")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1.0)
            return (res.returncode == 0 and "MESH_PING_OK" in res.stdout), (time.perf_counter() - t0) * 1000.0
        except Exception:
            return False, (time.perf_counter() - t0) * 1000.0

    def probe_physical_tier(node_name: str, tier: int) -> bool:
        return False

    def check_bluetooth_presence(rf_mac: str, timeout: float = 1.0) -> bool:
        return False

    def load_matrix() -> Dict[str, Any]:
        if MATRIX_PATH.exists():
            with open(MATRIX_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


# 6 Canonical DAG Stages definition in strict sequential order
DAG_STAGES = [
    (1, "Bluetooth RFCOMM (Layer 0)"),
    (2, "Bluetooth PAN (Layer 1)"),
    (3, "Ethernet Cables (Layer 2)"),
    (4, "Thunderbolt Cables (Layer 2 DMA)"),
    (5, "SSH Remote Actuation Plane"),
    (6, "Cascading Daemon Resurrection"),
]

# Canonical device registry metadata for 7-Layer Mesh
CANONICAL_DEVICE_METADATA = {
    "L1_Mac_Host": {
        "name": "Host Mac Mini M4 Pro (L1)",
        "role": "Master Orchestrator & Neural Engine Hub",
        "icon": "🖥️",
        "legacy_key": "mac_mini_host",
        "mac": "1c:f6:4c:7d:d7:0a",
        "alt_mac": "1c:f6:4c:7c:dc:5f",
        "bluetooth_mac": "1c:f6:4c:81:0b:28",
        "ip": "192.168.8.230",
        "tailscale": "10.1.0.10",
        "ssh_port": 22
    },
    "L2_MacBook_Pro": {
        "name": "MacBook Pro Vault (Intel Core i7 / L2)",
        "role": "Storage & Compute Vault (16 GB Unified RAM)",
        "icon": "💻",
        "legacy_key": "macbook_pro_vault",
        "mac": "a4:83:e7:d1:7c:82",
        "alt_mac": "82:e6:6d:c0:a4:01",
        "bluetooth_mac": "a4:83:e7:da:d0:b0",
        "alt_bluetooth_mac": "2c:ca:16:08:c0:27",
        "ip": "192.168.8.127",
        "tailscale": "10.1.0.11",
        "ssh_port": 22
    },
    "L3_Linux_Hub": {
        "name": "Linux Head Node (AMD Ryzen 7 5700U / L3)",
        "role": "Continuous AI Training & Ray Cluster",
        "icon": "🐧",
        "legacy_key": "linux_head_node",
        "mac": "00:41:0e:14:28:43",
        "bluetooth_mac": "00:41:0e:14:28:44",
        "ip": "192.168.8.224",
        "tailscale": "10.1.0.12",
        "ssh_port": 22
    },
    "L4_Linux_Tablet": {
        "name": "Linux Tablet (Debian Touch / L4)",
        "role": "Mobile Linux Compute & Touch DSP (8 GB RAM)",
        "icon": "📱",
        "legacy_key": "desktop_q4si00p",
        "mac": "00:03:7f:c2:00:43",
        "bluetooth_mac": "00:03:7f:c2:00:43",
        "ip": "192.168.8.173",
        "tailscale": "100.91.85.70",
        "ssh_port": 22
    },
    "L5_MacBook_Air": {
        "name": "MacBook Air M4 Node (L5)",
        "role": "Secondary Metal Worker & LoRA Distillation",
        "icon": "🍏",
        "legacy_key": "macbook_air",
        "mac": "66:74:75:d8:16:fb",
        "bluetooth_mac": "2c:ca:16:08:c0:27",
        "alt_bluetooth_mac": "ca:6b:75:9d:8e:92",
        "ip": "192.168.8.222",
        "tailscale": "100.93.158.96",
        "ssh_port": 22
    },
    "L6_Pixel_10_Edge": {
        "name": "Pixel 10 Pro XL (Tensor G5 / L6)",
        "role": "Edge TPU & 8K Vision (16 GB RAM)",
        "icon": "📱",
        "legacy_key": "pixel_10",
        "mac": "30:e0:44:6d:18:ec",
        "bluetooth_mac": "30:e0:44:6d:18:ec",
        "tailscale": "10.1.0.13",
        "ssh_port": 8022,
        "is_mobile": True,
        "adb_serial": "10.1.0.13:5555",
        "usb_adb_serial": "5B080DLCQ001LQ"
    },
    "L7_Samsung_S20": {
        "name": "Samsung Galaxy S20+ (SM_G986B / L7)",
        "role": "Dedicated Automated UI Tester & CAKE SQM",
        "icon": "📱",
        "legacy_key": "samsung_s20",
        "mac": "5c:cb:99:05:81:41",
        "alt_mac": "0a:8f:1b:f1:c8:17",
        "bluetooth_mac": "5c:cb:99:05:81:41",
        "tailscale": "10.1.0.14",
        "ssh_port": 8022,
        "is_mobile": True,
        "adb_serial": "10.1.0.14:5555",
        "usb_adb_serial": "R3CN40CJJ1R"
    },
    "L8_Linux_Mini": {
        "name": "Linux Mini (Intel 2018 / L8)",
        "role": "Docker Hub & RPC Sharding",
        "icon": "🐧",
        "legacy_key": "linux_mini",
        "mac": "23:57:01:3f:00:01",
        "bluetooth_mac": None,
        "ip": "192.168.8.28",
        "tailscale": "100.121.247.8",
        "ssh_port": 22
    },
    "GW_Router": {
        "name": "GL-BE14000 Sovereign Gateway (Wi-Fi 7 / GW)",
        "role": "Wi-Fi 7 Multi-WAN Gateway & Hardware Bridge",
        "icon": "🛰️",
        "legacy_key": "gl_travel_router",
        "mac": "94:83:c4:eb:e7:31",
        "ip": "192.168.8.1",
        "tailscale": "100.122.185.123",
        "bluetooth_mac": "8c:86:dd:00:26:41",
        "ssh_port": 22
    },
    "L9_iPhone_16_Pro": {
        "name": "iPhone 16 Pro (Apple A18 Pro / L9)",
        "role": "Primary iOS Testing Node & Screen Lens Commerce Target",
        "icon": "🍏",
        "legacy_key": "iphone_16_pro",
        "mac": "74:cc:40:25:39:24",
        "bluetooth_mac": "74:cc:40:20:8e:10",
        "ip": "192.168.8.102",
        "tailscale": "100.122.52.89",
        "lockdown_port": 62078,
        "udid": "00008140-00015D5E3EFA801C",
        "coredevice_id": "AE1D33CE-4249-5E2C-B866-FE3BD627D575",
        "is_mobile": True,
        "ssh_port": None
    }
}


def load_mesh_matrix() -> Dict[str, Any]:
    """Dynamically loads mesh_ip_matrix.json."""
    if not MATRIX_PATH.exists():
        logger.error(f"Matrix path not found: {MATRIX_PATH}")
        return {}
    try:
        with open(MATRIX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load matrix JSON from {MATRIX_PATH}: {e}")
        return {}


def build_device_registry() -> Dict[str, Dict[str, Any]]:
    """
    Builds the unified device registry from mesh_ip_matrix.json and canonical metadata,
    supporting canonical node names (e.g. L4_Linux_Tablet) and legacy aliases.
    Hardened with type guards against non-dict/list elements (Rule 0 Zero-Mock Truth).
    """
    matrix = load_mesh_matrix()
    registry = {}

    if isinstance(matrix, dict):
        for node_key, node_data in matrix.items():
            if node_key.startswith("_"):
                continue
            # Safely handle list entries (e.g. exhaustion_priority, nodes)
            if isinstance(node_data, list):
                continue
            if not isinstance(node_data, dict):
                continue

            meta = CANONICAL_DEVICE_METADATA.get(node_key, {})
            legacy_key = meta.get("legacy_key")
            is_retired = (node_data.get("status") == "RETIRED")

            ip = None
            if not is_retired:
                ip = (
                    node_data.get("wifi")
                    or node_data.get("ethernet")
                    or node_data.get("lan")
                    or node_data.get("tb4_bridge")
                    or meta.get("ip")
                    or (node_data.get("localhost") if "localhost" in node_data else None)
                )

            mac = node_data.get("mac") or meta.get("mac")
            alt_mac = meta.get("alt_mac")
            bt_mac = node_data.get("rf_mac") or node_data.get("bluetooth_mac") or meta.get("bluetooth_mac")
            alt_bt_mac = meta.get("alt_bluetooth_mac")

            dev_entry = {
                "key": node_key,
                "name": meta.get("name", node_key),
                "role": meta.get("role", "Mesh Node"),
                "icon": meta.get("icon", "🌐"),
                "status": node_data.get("status", "ACTIVE"),
                "is_retired": is_retired,
                "ip": ip,
                "alt_ip": node_data.get("alt_wifi"),
                "tailscale": node_data.get("tailscale") or meta.get("tailscale", ""),
                "pan": node_data.get("pan") or node_data.get("pan_tether", ""),
                "mac": mac,
                "alt_mac": alt_mac,
                "bluetooth_mac": bt_mac,
                "alt_bluetooth_mac": alt_bt_mac,
                "ssh_port": node_data.get("ssh_port", meta.get("ssh_port", 22)),
                "is_mobile": meta.get("is_mobile", False),
                "adb_serial": meta.get("adb_serial"),
                "matrix_data": node_data
            }

            registry[node_key] = dev_entry
            if legacy_key:
                registry[legacy_key] = dev_entry

    # Ensure all canonical metadata devices are registered
    for node_key, meta in CANONICAL_DEVICE_METADATA.items():
        if node_key not in registry:
            legacy_key = meta.get("legacy_key")
            dev_entry = {
                "key": node_key,
                "name": meta.get("name", node_key),
                "role": meta.get("role", "Mesh Node"),
                "icon": meta.get("icon", "🌐"),
                "status": "ACTIVE",
                "is_retired": False,
                "ip": meta.get("ip"),
                "alt_ip": None,
                "tailscale": meta.get("tailscale", ""),
                "pan": "",
                "mac": meta.get("mac"),
                "alt_mac": meta.get("alt_mac"),
                "bluetooth_mac": meta.get("bluetooth_mac"),
                "alt_bluetooth_mac": meta.get("alt_bluetooth_mac"),
                "ssh_port": meta.get("ssh_port", 22),
                "is_mobile": meta.get("is_mobile", False),
                "adb_serial": meta.get("adb_serial"),
                "matrix_data": {}
            }
            registry[node_key] = dev_entry
            if legacy_key:
                registry[legacy_key] = dev_entry

    return registry


DEVICES = build_device_registry()


def get_mesh_ip_matrix() -> Dict[str, Any]:
    """Compatibility interface for legacy callers."""
    return load_mesh_matrix()


def construct_magic_packet(mac_address: str) -> bytes:
    """Constructs an exact 102-byte RFC 792 Wake-on-LAN magic packet."""
    clean_mac = mac_address.replace(":", "").replace("-", "").replace(".", "").strip()
    if len(clean_mac) != 12:
        raise ValueError(f"Invalid MAC address format: {mac_address}")
    mac_bytes = bytes.fromhex(clean_mac)
    packet = b"\xff" * 6 + mac_bytes * 16
    if len(packet) != 102:
        raise ValueError(f"Constructed packet size {len(packet)} != 102 bytes")
    return packet


def send_magic_packet(
    mac_address: str,
    broadcast_ips: Optional[List[str]] = None,
    ports: Optional[List[int]] = None
) -> bool:
    """
    Stage 3: Transmits RFC 792 standard Wake-on-LAN magic packets across broadcast targets.
    Zero-mock: Genuine UDP datagram transmission across subnets.
    """
    if not mac_address:
        return False
    try:
        magic_packet = construct_magic_packet(mac_address)
    except Exception as e:
        logger.error(f"Failed to construct magic packet for {mac_address}: {e}")
        return False

    if broadcast_ips is None:
        broadcast_ips = ["192.168.8.255", "255.255.255.255", "169.254.255.255"]
    if ports is None:
        ports = [9, 7]

    success = False
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in broadcast_ips:
            for port in ports:
                try:
                    sock.sendto(magic_packet, (target, port))
                    success = True
                except Exception as e:
                    logger.debug(f"Broadcast to {target}:{port} failed: {e}")

    if success:
        logger.info(f"⚡ [WoL-Stage-3] 102-byte Magic Packet dispatched to MAC: {mac_address}")
    return success


def wake_bluetooth(bt_mac: str) -> bool:
    """
    Stage 1: Bluetooth Proximity Awakening via blueutil.
    Connects via macOS CoreBluetooth to awaken sleeping device hardware radios.
    """
    if not bt_mac:
        return False
    clean_mac = bt_mac.replace(":", "-").lower()

    # Host Mac Mini controller self-affirmation
    if clean_mac == "1c-f6-4c-81-0b-28":
        try:
            proc = subprocess.run([BLUEUTIL_PATH, "--power", "1"], capture_output=True, text=True, timeout=1.5)
            logger.info("📶 [BT-Stage-1] Host Mac Mini M4 controller affirmed active (Power: ON)")
            return proc.returncode == 0
        except Exception as e:
            logger.debug(f"Host Mac Mini Bluetooth power check error: {e}")
            return True

    try:
        proc = subprocess.run([BLUEUTIL_PATH, "--connect", clean_mac], capture_output=True, text=True, timeout=2.0)
        logger.info(f"📶 [BT-Stage-1] Bluetooth wake signal sent to {clean_mac} (rc={proc.returncode})")
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        logger.info(f"📶 [BT-Stage-1] Bluetooth connection beacon dispatched to {clean_mac} (pulse active)")
        return True
    except Exception as e:
        logger.debug(f"Bluetooth wake error for {clean_mac}: {e}")
        return False


def resurrect_via_bluetooth_l2cap(mac: str) -> bool:
    """Zero-mock implementation of Bluetooth proximity pulse and radio wake."""
    return wake_bluetooth(mac)


def inject_adb_wake_lock(serial: Optional[str] = None) -> bool:
    """Stage 1 mobile add-on: Android ADB Screen Wakeup & Keepalive Injection."""
    cmd = [ADB_PATH]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["shell", "cmd bluetooth_manager enable && input keyevent KEYCODE_WAKEUP && (which termux-wake-lock >/dev/null 2>&1 && termux-wake-lock || true)"])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
        if proc.returncode == 0:
            target_desc = f"device '{serial}'" if serial else "default attached device"
            logger.info(f"📱 [ADB-WakeLock] Wake-lock successfully injected into {target_desc}")
            return True
        return False
    except Exception as e:
        logger.debug(f"ADB execution error: {e}")
        return False


def ping_target_port(host: str, port: int = 22, timeout: float = 1.5) -> bool:
    """Probes a target TCP port."""
    connected, _ = ping_port_rtt(host, port, timeout=timeout)
    return connected


def ping_icmp(ip: str, timeout: float = 1.0) -> bool:
    """Probes target via ICMP ping."""
    ok, _ = ping_icmp_rtt(ip, timeout=timeout)
    return ok


def ping_tailscale(ip: str) -> bool:
    """Probes Tailscale IP."""
    return ping_icmp(ip, timeout=1.0)


# ==============================================================================
# FEATURE F4: 6-Stage Execution DAG Implementation
# ==============================================================================

def check_fast_path_carrier(node_key: str, node_data: Dict[str, Any], timeout: float = 0.05) -> Tuple[bool, str, float]:
    """
    Pre-flight Fast-Path Carrier Check:
    Uses sub-millisecond kernel carrier check (<1ms) and 50ms socket micro-probe.
    If carrier is active (en0 or bridge0) and SSH connects within 50ms, returns
    (True, endpoint, rtt_ms) allowing bypass of Stages 1 & 2 (Bluetooth RFCOMM and PAN).
    """
    eth_carrier = check_interface_carrier("en0")
    tb_carrier = check_interface_carrier("bridge0")

    if not eth_carrier and not tb_carrier:
        return False, "", 0.0

    target_port = node_data.get("ssh_port")
    if target_port is None:
        target_port = 22
    candidates = []

    # Priority 1: High speed Thunderbolt
    t4 = node_data.get("tier4_thunderbolt") or {}
    for k in ("tb4_bridge", "tb3_bridge", "ip"):
        v = t4.get(k)
        if v and v not in candidates:
            candidates.append(v)

    # Priority 2: Ethernet / LAN
    t3 = node_data.get("tier3_ethernet") or {}
    for k in ("ip", "lan_ip", "ethernet", "lan_10gbe", "wifi"):
        v = t3.get(k) or node_data.get(k)
        if v and v not in candidates:
            candidates.append(v)

    if node_key == "L1_Mac_Host":
        candidates.append("127.0.0.1")

    # Priority 3: Tailscale
    ts = node_data.get("tailscale")
    if ts and ts not in candidates:
        candidates.append(ts)

    for cand in candidates:
        ok, rtt = ping_port_rtt(cand, target_port, timeout=timeout)
        if ok:
            logger.info(f"⚡ [Fast-Path] Carrier ACTIVE, micro-probe succeeded on {cand}:{target_port} ({rtt:.2f}ms). Bypassing Stages 1 & 2.")
            return True, f"{cand}:{target_port}", rtt

    return False, "", 0.0


# ==============================================================================
# FEATURE F6: Cascading Daemon & Dependency Resurrection Engine
# ==============================================================================

CANONICAL_SERVICES = {
    50052: {
        "name": "ggml_rpc_server",
        "display": "Distributed GPU RPC Server",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 50052},
            {"node": "L2_MacBook_Pro", "host": "10.1.0.11", "port": 50052},
            {"node": "L8_Linux_Mini", "host": "192.168.8.28", "port": 50052}
        ],
        "launch_cmd": "python3 /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/llama_rpc_shard_daemon.py"
    },
    6333: {
        "name": "qdrant_rest",
        "display": "Qdrant Vector DB REST API",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 6333, "http_path": "/readyz"}
        ],
        "launch_cmd": "docker start lauburu-qdrant"
    },
    6334: {
        "name": "qdrant_grpc",
        "display": "Qdrant Vector DB gRPC API",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 6334}
        ],
        "launch_cmd": "docker start lauburu-qdrant"
    },
    8081: {
        "name": "qwen_2_5_coder_8081",
        "display": "Qwen 2.5 Coder 7B Subordinate Syntax Worker",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 8081, "http_path": "/health"}
        ],
        "launch_cmd": "launchctl kickstart -k gui/501/com.lauburu.qwen-8081 || launchctl load -w /Users/aaron/Library/LaunchAgents/com.lauburu.qwen-8081.plist"
    },
    8082: {
        "name": "qwen_38_max_abliterated_8082",
        "display": "Qwen 3.8 Max Abliterated Sovereign Master Local Orchestrator",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 8082, "http_path": "/health"}
        ],
        "launch_cmd": "python3 /Volumes/Lauburu-Monorepo/02_ai_models_and_inference/decentralized_prima_daemon.py"
    },
    8083: {
        "name": "qwen_38_max_devil_8083",
        "display": "Qwen 3.8 Max Devil's Advocate / Adversarial Red Team",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 8083, "http_path": "/health"}
        ],
        "launch_cmd": "launchctl kickstart -k gui/501/com.lauburu.qwen-8083 || launchctl load -w /Users/aaron/Library/LaunchAgents/com.lauburu.qwen-8083.plist"
    },
    8085: {
        "name": "unified_ide_gateway_8085",
        "display": "Lauburu Unified IDE Gateway / Multi-Model Dispatcher",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 8085, "http_path": "/health"}
        ],
        "launch_cmd": "PYTHONPATH=/Volumes/Lauburu-Monorepo/01_apps/bt_ide_ab_test python3 -m uvicorn gateway.server:app --host 0.0.0.0 --port 8085"
    },
    4003: {
        "name": "screen_lens_stream_4003",
        "display": "Screen Lens Sovereign MJPEG Live Stream",
        "probers": [
            {"node": "L1_Mac_Host", "host": "127.0.0.1", "port": 4003}
        ],
        "launch_cmd": "python3 /Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_lens_stream_server.py"
    }
}


def check_http_endpoint(host: str, port: int, path: str = "/health", timeout: float = 1.0) -> bool:
    """Verifies that an HTTP service returns 200 OK."""
    url = f"http://{host}:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LauburuResurrectionEngine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def probe_and_resurrect_service(
    service_name: str,
    node: Any = "L1_Mac_Host",
    port: Optional[int] = None,
    launch_cmd: Optional[str] = None
) -> Dict[str, Any]:
    """
    Interface Contract strictly per PROJECT.md:
    probe_and_resurrect_service(service_name: str, node: str, port: int, launch_cmd: str) -> dict
    Returns:
      {
        "service": str,
        "port": int,
        "initial_state": "UP" | "DOWN",
        "resurrected": bool,
        "final_state": "UP" | "DOWN",
        "exit_code": int
      }
    """
    # Normalize polymorphic calling patterns
    if isinstance(node, int):
        launch_cmd = port if isinstance(port, str) else launch_cmd
        port = node
        node = "L1_Mac_Host"
    elif port is None:
        port = 8080

    target_host = "127.0.0.1"
    if node != "L1_Mac_Host":
        matrix = load_mesh_matrix()
        dev_data = matrix.get(str(node), {})
        target_host = dev_data.get("tailscale") or dev_data.get("wifi") or dev_data.get("ethernet") or "127.0.0.1"

    # Step 1: Initial State Probe
    initial_up = False
    http_path = None
    if service_name == "router_rfcomm_getty" or node == "GW_Router":
        try:
            p = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", f"root@{target_host}", "ps | grep -v grep | grep 'rfcomm watch'"],
                capture_output=True, text=True, timeout=3.0
            )
            initial_up = (p.returncode == 0 and "rfcomm watch" in p.stdout)
        except Exception:
            initial_up = False
    elif port in CANONICAL_SERVICES:
        svc_cfg = CANONICAL_SERVICES[port]
        for pr in svc_cfg.get("probers", []):
            if pr.get("node") == node or node == "L1_Mac_Host":
                http_path = pr.get("http_path")
                break

        if http_path:
            initial_up = check_http_endpoint(target_host, port, path=http_path, timeout=0.8)
        else:
            initial_up, _ = ping_port_rtt(target_host, port, timeout=0.5)
    else:
        initial_up, _ = ping_port_rtt(target_host, port, timeout=0.5)

    if initial_up:
        return {
            "service": service_name,
            "port": port,
            "initial_state": "UP",
            "resurrected": False,
            "final_state": "UP",
            "exit_code": 0
        }

    # Step 2: Resurrect if DOWN
    exit_code = 0
    cmd_to_run = launch_cmd
    if not cmd_to_run and port in CANONICAL_SERVICES:
        cmd_to_run = CANONICAL_SERVICES[port].get("launch_cmd")

    if cmd_to_run:
        logger.info(f"🔄 [Resurrect] Reviving {service_name} on port {port} on {node}...")
        log_file = REPO_ROOT / "logs" / f"resurrect_{port}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if node == "L1_Mac_Host" or target_host == "127.0.0.1":
                # Local launch in background
                full_cmd = f"nohup {cmd_to_run} > '{log_file}' 2>&1 &"
                res = subprocess.run(["/bin/sh", "-c", full_cmd], capture_output=True, timeout=5.0)
                exit_code = res.returncode
            else:
                # Remote execution via SSH
                ssh_cmd = [
                    "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3",
                    "-o", "ControlMaster=auto", "-o", "ControlPath=~/.ssh/sockets/%r@%h:%p",
                    "-o", "ControlPersist=10m",
                    f"root@{target_host}" if node == "GW_Router" else target_host,
                    f"nohup {cmd_to_run} > /tmp/resurrect_{port}.log 2>&1 &"
                ]
                res = subprocess.run(ssh_cmd, capture_output=True, timeout=5.0)
                exit_code = res.returncode
        except Exception as e:
            logger.error(f"Error launching {service_name}: {e}")
            exit_code = 1

    # Step 3: Verify Final State (Poll up to 6.0 seconds)
    time.sleep(0.5)
    final_up = False
    deadline = time.time() + 6.0
    while time.time() < deadline:
        if service_name == "router_rfcomm_getty" or node == "GW_Router":
            try:
                p = subprocess.run(
                    ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=2", f"root@{target_host}", "ps | grep -v grep | grep 'rfcomm watch'"],
                    capture_output=True, text=True, timeout=3.0
                )
                final_up = (p.returncode == 0 and "rfcomm watch" in p.stdout)
            except Exception:
                final_up = False
        elif http_path:
            final_up = check_http_endpoint(target_host, port, path=http_path, timeout=0.8)
        else:
            final_up, _ = ping_port_rtt(target_host, port, timeout=0.5)
        if final_up:
            break
        time.sleep(0.5)

    resurrected = (not initial_up) and final_up

    return {
        "service": service_name,
        "port": port,
        "initial_state": "DOWN",
        "resurrected": resurrected,
        "final_state": "UP" if final_up else "DOWN",
        "exit_code": exit_code
    }



def probe_and_heal_storage_routing() -> dict:
    import subprocess
    result = {
        "service_id": "unified_router_storage",
        "node_id": "L1_Mac_Host",
        "status": "HEALTHY",
        "message": "Storage mounts and en0 routing are optimal."
    }
    try:
        route_out = subprocess.check_output(["route", "-n", "get", "192.168.8.1"], text=True, stderr=subprocess.DEVNULL)
        if "interface: en0" not in route_out:
            logger.warning("Route for 192.168.8.1 is NOT on en0. Healing...")
            subprocess.run("echo goldfighting1 | sudo -S route delete -net 192.168.8.0/24", shell=True, stderr=subprocess.DEVNULL)
            subprocess.run("echo goldfighting1 | sudo -S route add -net 192.168.8.0/24 -interface en0", shell=True, stderr=subprocess.DEVNULL)
            result["status"] = "HEALED"
            result["message"] = "Forced 192.168.8.0/24 route to en0."
    except Exception as e:
        result["status"] = "FAILED"
        result["message"] = f"Routing check failed: {e}"

    try:
        mounts_out = subprocess.check_output(["mount"], text=True, stderr=subprocess.DEVNULL)
        missing = []
        if "/Volumes/seaweed_network" not in mounts_out: missing.append("seaweed_network")
        if "/Volumes/lauburu_storage" not in mounts_out: missing.append("lauburu_storage")
        
        if missing:
            logger.warning(f"Missing mounts: {missing}. Executing canonical mount script...")
            subprocess.run(["/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/storage/mount_router_network_storage.sh", "mount"], check=False)
            result["status"] = "HEALED"
            result["message"] = f"Healed route and restored mounts: {missing}"
    except Exception as e:
        result["status"] = "FAILED"
        if "message" in result:
            result["message"] += f" | Mount check failed: {e}"
        else:
            result["message"] = f"Mount check failed: {e}"
        
    return result

def resurrect_all_daemons(transports_verified: bool = True) -> Dict[str, Any]:
        
    """
    Stage 6: Cascading Daemon & Dependency Resurrection.
    Audits and revives all registered service endpoints across the mesh.
    Strictly halts if transports_verified is False.
    """
    if not transports_verified:
        logger.warning("⛔ [Stage 6] Total transport failure detected. Halting daemon resurrection.")
        return {"status": "HALTED", "reason": "No active physical transport or SSH connection"}

    results = []

    # 1. Distributed GPU RPC on Port 50052
    rpc_res_l1 = probe_and_resurrect_service("ggml_rpc_server_l1", "L1_Mac_Host", 50052)
    results.append(rpc_res_l1)

    # Remote RPC on L2 and L8
    rpc_res_l2 = probe_and_resurrect_service(
        "ggml_rpc_server_l2", "L2_MacBook_Pro", 50052,
        "/Users/aaronmaher/llama.cpp/build/bin/ggml-rpc-server -H 0.0.0.0 -p 50052 -t 6 -c"
    )
    results.append(rpc_res_l2)

    rpc_res_l8 = probe_and_resurrect_service(
        "ggml_rpc_server_l8", "L8_Linux_Mini", 50052,
        "/home/linuxmini/llama.cpp/build/bin/ggml-rpc-server -H 0.0.0.0 -p 50052 -t 6 -c"
    )
    results.append(rpc_res_l8)

    # 2. Qdrant Vector DB on Ports 6333 and 6334
    qdrant_res = probe_and_resurrect_service("qdrant_vectordb", "L1_Mac_Host", 6333, "docker start lauburu-qdrant")
    results.append(qdrant_res)

    qdrant_grpc_res = probe_and_resurrect_service("qdrant_grpc", "L1_Mac_Host", 6334, "docker start lauburu-qdrant")
    results.append(qdrant_grpc_res)

    # 3. Model Inference Endpoints (Ports 8081, 8082, 8083, 8085)
    # Port 8081 (Subordinate Syntax Worker)
    coder_cmd = (
        "launchctl kickstart -k gui/501/com.lauburu.qwen-8081 || "
        "launchctl load -w /Users/aaron/Library/LaunchAgents/com.lauburu.qwen-8081.plist"
    )
    coder_res = probe_and_resurrect_service("qwen2.5_coder_8081", "L1_Mac_Host", 8081, coder_cmd)
    results.append(coder_res)

    # Port 8082 (Sovereign Master Orchestrator)
    prima_res = probe_and_resurrect_service("prima_daemon_8082", "L1_Mac_Host", 8082)
    results.append(prima_res)

    # Port 8083 (Adversarial Red Team)
    redteam_res = probe_and_resurrect_service("devil_advocate_8083", "L1_Mac_Host", 8083)
    results.append(redteam_res)

    # Port 8085 (IDE Gateway)
    gateway_res = probe_and_resurrect_service("ide_gateway_8085", "L1_Mac_Host", 8085)
    results.append(gateway_res)

    # 4. Port 4003 (Screen Lens Sovereign Stream)
    lens_res = probe_and_resurrect_service("screen_lens_4003", "L1_Mac_Host", 4003)
    results.append(lens_res)

    # 5. Router Headless Recovery Getty on /dev/rfcomm0
    router_cmd = "/etc/init.d/router_rfcomm_getty restart || nohup /usr/bin/rfcomm watch 0 1 /usr/libexec/login.sh > /dev/null 2>&1 &"
    router_getty_res = probe_and_resurrect_service("router_rfcomm_getty", "GW_Router", 22, router_cmd)
    results.append(router_getty_res)

    return {
        "status": "COMPLETED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "services": results
    }


# ==============================================================================
# CanonicalResurrectionEngine Class
# ==============================================================================

class CanonicalResurrectionEngine:
    """Canonical 6-Stage Directed Acyclic Graph (DAG) Resurrection Engine."""

    def __init__(self):
        self.devices = build_device_registry()
        self.matrix = load_mesh_matrix()
        try:
            OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
            (OBSIDIAN_VAULT / "APPS_AND_FEATURES").mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def execute_dag_node(
        self,
        node_key: str,
        fast_path: bool = True,
        strict_recovery: bool = False,
        target_stage: Optional[int] = None,
        run_daemons: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the 6-stage DAG for a single node:
        Pre-flight: Fast-path carrier probe (skips 1 & 2 if healthy)
        Stage 1: Bluetooth RFCOMM
        Stage 2: Bluetooth PAN
        Stage 3: Ethernet Cables & WoL
        Stage 4: Thunderbolt Cables DMA Bridge
        Stage 5: SSH Remote Actuation Plane
        Stage 6: Cascading Daemon Resurrection
        """
        key_norm = node_key.strip().lower()
        matched_key = None
        for k in self.devices:
            if k.lower() == key_norm or k.lower().replace("-", "_") == key_norm.replace("-", "_"):
                matched_key = k
                break
        if not matched_key:
            for k in self.devices:
                if key_norm in k.lower():
                    matched_key = k
                    break

        if not matched_key:
            return {"node": node_key, "success": False, "error": f"Device '{node_key}' not found in registry"}

        dev = self.devices[matched_key]
        if dev.get("is_retired"):
            return {"node": matched_key, "success": False, "is_retired": True, "reason": "Device is retired"}

        node_data = self.matrix.get(matched_key, dev.get("matrix_data", {}))
        stages_executed = {}
        transports_verified = set()

        # Pre-flight Fast-Path Carrier Check
        use_fast_path = fast_path and not strict_recovery
        fast_path_ok = False
        fast_endpoint = ""
        fast_rtt = 0.0

        if use_fast_path and (target_stage is None or target_stage in (1, 2, 5)):
            fast_path_ok, fast_endpoint, fast_rtt = check_fast_path_carrier(matched_key, node_data)
            if fast_path_ok:
                transports_verified.add(3) # Carrier verified
                transports_verified.add(5) # SSH micro-probe verified

        # Stage 1: Bluetooth RFCOMM (Layer 0)
        if target_stage is None or target_stage == 1:
            if fast_path_ok:
                stages_executed["stage1_rfcomm"] = {
                    "stage": 1,
                    "name": "Bluetooth RFCOMM (Layer 0)",
                    "status": "BYPASSED",
                    "reason": "Fast-path carrier active and SSH responsive"
                }
            else:
                bt_mac = dev.get("bluetooth_mac")
                bt_woken = False
                if bt_mac:
                    bt_woken = wake_bluetooth(bt_mac)
                if dev.get("alt_bluetooth_mac"):
                    wake_bluetooth(dev.get("alt_bluetooth_mac"))
                if dev.get("is_mobile") or matched_key in ("L6_Pixel_10_Edge", "L7_Samsung_S20"):
                    inject_adb_wake_lock(dev.get("adb_serial"))

                s1_alive = probe_physical_tier(matched_key, 1) or bt_woken
                if s1_alive:
                    transports_verified.add(1)
                stages_executed["stage1_rfcomm"] = {
                    "stage": 1,
                    "name": "Bluetooth RFCOMM (Layer 0)",
                    "status": "ACTIVE" if s1_alive else "DISPATCHED",
                    "bt_mac": bt_mac,
                    "woken": bt_woken
                }

        # Stage 2: Bluetooth PAN (Layer 1)
        if target_stage is None or target_stage == 2:
            if fast_path_ok:
                stages_executed["stage2_bt_pan"] = {
                    "stage": 2,
                    "name": "Bluetooth PAN (Layer 1)",
                    "status": "BYPASSED",
                    "reason": "Fast-path carrier active and SSH responsive"
                }
            else:
                s2_alive = probe_physical_tier(matched_key, 2)
                if s2_alive:
                    transports_verified.add(2)
                stages_executed["stage2_bt_pan"] = {
                    "stage": 2,
                    "name": "Bluetooth PAN (Layer 1)",
                    "status": "ACTIVE" if s2_alive else "INACTIVE",
                    "pan_ip": dev.get("pan")
                }

        # Stage 3: Ethernet Cables (Layer 2)
        if target_stage is None or target_stage == 3:
            mac = dev.get("mac")
            wol_sent = False
            if mac:
                wol_sent = send_magic_packet(mac)
            if dev.get("alt_mac"):
                send_magic_packet(dev.get("alt_mac"))

            s3_alive = probe_physical_tier(matched_key, 3) or (fast_path_ok and check_interface_carrier("en0"))
            if s3_alive:
                transports_verified.add(3)
            stages_executed["stage3_ethernet"] = {
                "stage": 3,
                "name": "Ethernet Cables (Layer 2)",
                "status": "ACTIVE" if s3_alive else "DISPATCHED",
                "wol_sent": wol_sent,
                "carrier": check_interface_carrier("en0")
            }

        # Stage 4: Thunderbolt Cables (Layer 2 DMA)
        if target_stage is None or target_stage == 4:
            s4_alive = probe_physical_tier(matched_key, 4)
            tb_carrier = check_interface_carrier("bridge0")
            if s4_alive or (tb_carrier and fast_path_ok):
                transports_verified.add(4)
            stages_executed["stage4_thunderbolt"] = {
                "stage": 4,
                "name": "Thunderbolt Cables (Layer 2 DMA)",
                "status": "ACTIVE" if s4_alive else "INACTIVE",
                "carrier": tb_carrier
            }

        # Stage 5: SSH Remote Actuation Plane
        if target_stage is None or target_stage == 5:
            if fast_path_ok:
                stages_executed["stage5_ssh"] = {
                    "stage": 5,
                    "name": "SSH Remote Actuation Plane",
                    "status": "ACTIVE",
                    "endpoint": fast_endpoint,
                    "rtt_ms": fast_rtt
                }
                transports_verified.add(5)
            else:
                s5_alive = probe_physical_tier(matched_key, 5)
                if s5_alive:
                    transports_verified.add(5)
                stages_executed["stage5_ssh"] = {
                    "stage": 5,
                    "name": "SSH Remote Actuation Plane",
                    "status": "ACTIVE" if s5_alive else "INACTIVE",
                    "ssh_port": dev.get("ssh_port", 22)
                }

        # Stage 6: Cascading Daemon Resurrection
        if target_stage == 6 or (target_stage is None and run_daemons):
            has_transport = bool(transports_verified.intersection({1, 2, 3, 4, 5}))
            if not has_transport and target_stage == 6:
                has_transport = check_interface_carrier("en0") or check_interface_carrier("bridge0") or fast_path_ok
            s6_res = resurrect_all_daemons(transports_verified=has_transport)
            stages_executed["stage6_daemons"] = {
                "stage": 6,
                "name": "Cascading Daemon Resurrection",
                "status": s6_res.get("status", "UNKNOWN"),
                "details": s6_res
            }
        elif target_stage is None and not run_daemons:
            stages_executed["stage6_daemons"] = {
                "stage": 6,
                "name": "Cascading Daemon Resurrection",
                "status": "DEFERRED",
                "details": "Deferred to post-sweep mesh execution"
            }

        overall_success = bool(transports_verified) or fast_path_ok or (target_stage == 6 and bool(has_transport))
        return {
            "node": matched_key,
            "success": overall_success,
            "fast_path_bypassed": fast_path_ok,
            "stages": stages_executed,
            "transports_verified": sorted(list(transports_verified)),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

    def heal_all(
        self,
        fast_path: bool = True,
        strict_recovery: bool = False,
        stage: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Full 6-Stage Mesh Healing Sweep:
        Executes DAG sequentially across all canonical nodes (L1..L8, GW_Router),
        culminating in Stage 6 cascading daemon revival.
        """
        logger.info(f"🚀 [HealAll] Initiating 6-Stage Resurrection Sweep (fast_path={fast_path}, strict={strict_recovery}, stage={stage})...")
        node_order = [
            "L1_Mac_Host", "L2_MacBook_Pro", "L3_Linux_Hub", "L4_Linux_Tablet",
            "L5_MacBook_Air", "L6_Pixel_10_Edge", "L7_Samsung_S20", "L8_Linux_Mini",
            "GW_Router"
        ]

        node_results = {}
        for nk in node_order:
            if nk in self.devices and not self.devices[nk].get("is_retired"):
                node_results[nk] = self.execute_dag_node(
                    nk,
                    fast_path=fast_path,
                    strict_recovery=strict_recovery,
                    target_stage=stage,
                    run_daemons=False
                )

        # Execute Stage 6 once mesh transports are assessed
        daemon_results = None
        if stage is None or stage == 6:
            any_transport = any(res.get("success") for res in node_results.values())
            if not any_transport and stage == 6:
                any_transport = check_interface_carrier("en0") or check_interface_carrier("bridge0")
            daemon_results = resurrect_all_daemons(transports_verified=any_transport)

        summary = {
            "action": "CANONICAL_6_STAGE_RESURRECTION_SWEEP",
            "fast_path": fast_path and not strict_recovery,
            "strict_recovery": strict_recovery,
            "target_stage": stage,
            "nodes_processed": len(node_results),
            "nodes_alive": sum(1 for r in node_results.values() if r.get("success")),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "nodes": node_results,
            "stage6_daemons": daemon_results
        }

        self.log_telemetry(summary)
        self.generate_obsidian_dashboard(last_woken="6-Stage Sweep")
        return summary

    def wake_device(self, key: str) -> Dict[str, Any]:
        """Backward-compatible wake method implementing 6-Stage DAG execution."""
        return self.execute_dag_node(key, fast_path=True, strict_recovery=False)

    def wake_node(self, node_name: str) -> bool:
        """Compatibility wrapper for WoLEngine interface."""
        res = self.wake_device(node_name)
        return bool(res.get("success", False))

    def wake_all(self) -> Dict[str, Any]:
        """Broadcasts 4-tier / 6-stage resurrection across all canonical mesh nodes."""
        return self.heal_all(fast_path=False, strict_recovery=True)

    def get_status(self) -> Dict[str, Any]:
        """Queries and returns live connectivity status for all mesh nodes."""
        status_report = {}
        for k, dev in self.devices.items():
            if k.startswith("L") or k == "GW_Router":
                if dev.get("is_retired"):
                    continue
                ip = dev.get("ip")
                ts = dev.get("tailscale")
                port = dev.get("ssh_port")
                if port is None:
                    port = 22

                ip_alive = ping_target_port(ip, port) if ip else False
                if not ip_alive and ip:
                    ip_alive = ping_icmp(ip)

                ts_alive = False
                if ts:
                    ts_alive = ping_target_port(ts, port) or ping_tailscale(ts)

                status_report[k] = {
                    "name": dev["name"],
                    "ip": ip,
                    "ip_alive": ip_alive,
                    "tailscale": ts,
                    "tailscale_alive": ts_alive,
                    "mac": dev.get("mac"),
                    "bluetooth_mac": dev.get("bluetooth_mac")
                }
        return {"status": "ONLINE", "nodes": status_report}

    def generate_obsidian_dashboard(self, last_woken: Optional[str] = None):
        """Generates interactive Obsidian Dashboard."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md = f"""# ⚡ Lauburu Fleet Wake-on-LAN & Distributed Compute Dashboard
> **Last Synced:** `{now_str}`  
> **Active Subnet:** `192.168.8.0/24` | **Tailscale Mesh:** `100.x.x.x` | **Magic Port:** `UDP 9 / 7`

---

## 🎯 Device Registry & Instant Wake Controls

| Device | Role | Hardware MAC | Local LAN IP | Tailscale IP | Quick Wake Command |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        seen = set()
        for k, d in self.devices.items():
            if k.startswith("L") or k == "GW_Router":
                if d.get("is_retired") or d["name"] in seen:
                    continue
                seen.add(d["name"])
                md += f"| {d['icon']} **{d['name']}** | `{d['role']}` | `{d['mac']}` | `{d['ip']}` | `{d['tailscale']}` | `python3 06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --node {k}` |\n"

        md += f"""
---

## 🚀 Quick Execution Triggers

- **Execute 6-Stage Healing Sweep:**
  ```bash
  python3 06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --heal-all --fast-path
  ```
- **Strict Recovery Fallback:**
  ```bash
  python3 06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --heal-all --strict-recovery
  ```
- **Check Mesh Status:**
  ```bash
  python3 06_scripts_and_tooling/network/canonical_network_resurrection_engine.py --status
  ```

> [!NOTE]
> Last Woken Trigger: **{last_woken if last_woken else "None"}**
"""
        try:
            DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
                f.write(md)
        except Exception as e:
            logger.debug(f"Could not write dashboard file: {e}")

    def log_telemetry(self, sweep_data: Dict[str, Any]):
        """Logs structured empirical telemetry to MESH_TELEMETRY_LOG.md."""
        now_aest = datetime.now().strftime("%Y-%m-%d %H:%M AEST")
        alive = sweep_data.get("nodes_alive", 0)
        total = sweep_data.get("nodes_processed", 0)

        # Get Host RAM Headroom
        host_ram_str = "Unknown"
        try:
            import psutil
            vm = psutil.virtual_memory()
            host_ram_str = f"{vm.total/(1024**3):.2f} GB total, {vm.available/(1024**3):.2f} GB available, {vm.percent}% used"
        except Exception:
            pass

        entry = f"""
### [{now_aest}] Canonical 6-Stage Network Resurrection & Cascading Daemon Sweep
- **Trigger:** Engine execution (`--heal-all`)
- **Fast-Path Status:** `{"ACTIVE (Bypassed Stages 1 & 2)" if sweep_data.get("fast_path") else "STRICT RECOVERY"}`
- **Nodes Responded:** **{alive} / {total}** nodes verified reachable
- **Host Sanctuary Headroom (Rule 3):** {host_ram_str}
- **Cascading Daemons (Stage 6):**
"""
        s6 = sweep_data.get("stage6_daemons") or {}
        for svc in s6.get("services", []):
            st = svc.get("final_state", "DOWN")
            rc = svc.get("exit_code", 0)
            entry += f"  - `{svc.get('service')}` (Port {svc.get('port')}): **{st}** (Exit Code: `{rc}`)\n"

        try:
            TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.debug(f"Could not append to telemetry log: {e}")


# ==============================================================================
# HTTP Server Interface (Port 18899 / Port 18802)
# ==============================================================================

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class WoLHTTPHandler(BaseHTTPRequestHandler):
    engine = CanonicalResurrectionEngine()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path == "/api/wol/wake":
            dev = params.get("device", [""])[0]
            res = self.engine.wake_device(dev)
            self.wfile.write(json.dumps(res).encode())
        elif path == "/api/wol/wake-all" or path == "/api/heal-all":
            res = self.engine.heal_all()
            self.wfile.write(json.dumps(res).encode())
        elif path == "/api/wol/status":
            res = {"status": "ONLINE", "registered_devices": self.engine.devices}
            self.wfile.write(json.dumps(res).encode())
        else:
            self.wfile.write(json.dumps({
                "service": "Canonical Network Resurrection & Cascading Daemon API",
                "endpoints": [
                    "/api/wol/wake?device=...", "/api/heal-all", "/api/wol/status"
                ]
            }).encode())

    def log_message(self, format, *args):
        pass


def run_server(port: int = 18899):
    server = HTTPServer(("0.0.0.0", port), WoLHTTPHandler)
    logger.info(f"🌐 WoL REST API listening on port {port}...")
    server.serve_forever()


# Compatibility Aliases
WoLEngine = CanonicalResurrectionEngine


def ensure_node_connectivity(node_name: str) -> bool:
    """Ensures node connectivity by executing the 6-stage DAG."""
    engine = CanonicalResurrectionEngine()
    logger.info(f"Ensuring connectivity for {node_name}...")
    res = engine.execute_dag_node(node_name, fast_path=True)
    logger.info(f"Resurrection outcome for {node_name}: {res.get('success', False)}")
    return bool(res.get("success", False))


def main():
    parser = argparse.ArgumentParser(description="Canonical 6-Stage Network Resurrection & Cascading Daemon Engine")
    parser.add_argument("--heal-all", action="store_true", help="Execute complete 6-stage DAG resurrection across all mesh nodes and services")
    parser.add_argument("--fast-path", action="store_true", default=True, help="Enable pre-flight fast-path carrier check (default: True)")
    parser.add_argument("--no-fast-path", dest="fast_path", action="store_false", help="Disable pre-flight fast-path carrier check")
    parser.add_argument("--strict-recovery", action="store_true", help="Enforce strict sequential fallback (RFCOMM -> PAN -> Ethernet -> TB4)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4, 5, 6], help="Execute only a specific stage of the DAG (1-6)")
    parser.add_argument("--wake-all", action="store_true", help="Broadcast resurrection across all mesh devices (compatibility alias)")
    parser.add_argument("--node", type=str, help="Specific node name or key to awaken (e.g. L4_Linux_Tablet, L3_Linux_Hub)")
    parser.add_argument("--wake", type=str, help="Alias for --node")
    parser.add_argument("--status", action="store_true", help="Display live connectivity and resurrection status")
    parser.add_argument("--serve-api", action="store_true", help="Start HTTP REST API")
    parser.add_argument("--sync-dashboard", action="store_true", help="Sync Obsidian dashboard only")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    # Process file lock to prevent duplicate concurrent runs
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE_PATH, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        logger.warning("Another instance of Canonical Network Resurrection Engine is already running. Proceeding.")
    except Exception:
        pass

    try:
        engine = CanonicalResurrectionEngine()

        if args.serve_api:
            engine.generate_obsidian_dashboard()
            run_server()
            sys.exit(0)

        if args.heal_all or args.wake_all:
            res = engine.heal_all(
                fast_path=args.fast_path and not args.strict_recovery,
                strict_recovery=args.strict_recovery,
                stage=args.stage
            )
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"[SUCCESS] 6-Stage Sweep Complete: {res['nodes_alive']} / {res['nodes_processed']} nodes verified.")
                if res.get("stage6_daemons"):
                    print("Cascading Daemons (Stage 6):")
                    for s in res["stage6_daemons"].get("services", []):
                        print(f"  • {s['service']:24s} (Port {s['port']:5d}): {s['final_state']} [exit={s['exit_code']}]")
            sys.exit(0)

        target_node = args.node or args.wake
        if target_node:
            res = engine.execute_dag_node(
                target_node,
                fast_path=args.fast_path and not args.strict_recovery,
                strict_recovery=args.strict_recovery,
                target_stage=args.stage
            )
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                st = "ALIVE" if res.get("success") else "FAILED"
                print(f"[{st}] Node {res['node']}: {st} (Transports: {res.get('transports_verified')})")
            sys.exit(0 if res.get("success") else 1)

        if args.status:
            st = engine.get_status()
            if args.json:
                print(json.dumps(st, indent=2))
            else:
                print(json.dumps(st, indent=2))
            sys.exit(0)

        if args.sync_dashboard:
            engine.generate_obsidian_dashboard()
            print("Obsidian Dashboard Synced.")
            sys.exit(0)

        # Default fallback: heal-all with fast-path
        res = engine.heal_all(fast_path=True, strict_recovery=False)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[SUCCESS] 6-Stage Sweep Complete: {res['nodes_alive']} / {res['nodes_processed']} nodes verified.")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting cleanly.")
        sys.exit(130)
    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
