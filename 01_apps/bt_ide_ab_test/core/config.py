"""
Mesh Configuration, 7-Layer Hardware Matrix & Dynamic Safety Thresholds
========================================================================
Subsystem: 01_apps/bt_ide_ab_test/core/config.py
Lauburu Mesh Ecosystem — 2026

Codifies the Canonical 7-Layer Hardware Topology, Multi-IP Fallback Matrix (Rule 9),
Dynamic Safety Thresholds (Rule 3, Rule 0), Standard Port Allocations,
and Subagent Priority Classes for Backpressure Suspension.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SubagentPriority(int, Enum):
    """Priority classifications for backpressure management."""
    LOW = 1          # LoRA Harvester, AST Crawler, Background Indexer
    MEDIUM = 2       # Continuous Benchmarker, Speculative Cache Preloader
    HIGH = 3         # Multi-Agent Debate Council, Red Team Challenger
    IDE_CRITICAL = 4 # Active user IDE session, interactive completion/typing


class NodeLayer(str, Enum):
    """Physical layers of the Lauburu 7-Layer Mesh Network."""
    L1 = "L1_Mac_Host"
    L2 = "L2_MacBook_Pro"
    L3 = "L3_Linux_Hub"
    L4 = "L4_Linux_Tablet"
    L5 = "L5_MacBook_Air"
    L6 = "L6_Pixel_10_Edge"
    L7 = "L7_Samsung_S20"
    GW = "GW_Router"


@dataclass
class NodeConfig:
    """Hardware specifications and multi-IP connectivity priority for a mesh node."""
    node_id: str
    name: str
    layer: NodeLayer
    os_type: str  # "darwin", "linux", "android", "openwrt"
    nominal_ram_gb: float
    nominal_ai_cap_gb: float
    max_utilization_pct: float
    min_sanctuary_free_mb: float
    ip_priority_list: List[str]
    telemetry_port: int = 8085
    is_local_host: bool = False
    notes: str = ""

    @property
    def nominal_ram_mb(self) -> float:
        return self.nominal_ram_gb * 1024.0

    @property
    def nominal_ai_cap_mb(self) -> float:
        return self.nominal_ai_cap_gb * 1024.0


# ---------------------------------------------------------------------------
# Standard Port Allocations
# ---------------------------------------------------------------------------
GATEWAY_PORT = 8085
RAM_GOVERNOR_PORT = 8085
LOCAL_TOOL_ROUTER_PORT = 8083     # Qwen 3.8 Max Master Reasoner / Hermes 3 tool routing (1734 ELO)
LOCAL_SYNTAX_WORKER_PORT = 8081   # Qwen 2.5 Coder 7B
LOCAL_RED_TEAM_PORT = 8083        # Qwen 3.8 Max Adversarial Red Team
EDGE_VISION_VLA_PORT = 8084       # Screen Lens Vision Encoders
SELF_HEALING_HUB_PORT = 18802     # Port on L3 Linux Hub
SEAWEEDFS_MASTER_PORT = 9333
SEAWEEDFS_FILER_PORT = 8888
SEAWEEDFS_VOLUME_PORT = 8080
QDRANT_PORT = 6333
SCREEN_LENS_STREAM_PORT = 4003

# ---------------------------------------------------------------------------
# Global RAM Pool & Safety Constants (Rule 0, Rule 3)
# ---------------------------------------------------------------------------
TOTAL_MESH_RAM_GB = 108.0
USABLE_AI_VRAM_GB = 82.8

# Rule 3: Mac Mini host preserves >= 4.8 GB free physical RAM and <= 80% RAM utilization
HOST_SANCTUARY_MIN_GB = 4.8
HOST_SANCTUARY_MIN_MB = 4.8 * 1024.0  # 4915.2 MB
HOST_MAX_UTILIZATION_PCT = 80.0
HOST_SANCTUARY_RECOVERY_HEADROOM_MB = 512.0  # +512 MB hysteresis recovery buffer
HOST_SANCTUARY_RECOVERY_MB = HOST_SANCTUARY_MIN_MB + HOST_SANCTUARY_RECOVERY_HEADROOM_MB  # 5427.2 MB

# Network-wide backpressure triggers when global pool utilization exceeds 85%
GLOBAL_POOL_SATURATION_PCT = 85.0
GLOBAL_CRITICAL_HEADROOM_GB = 10.0

# ---------------------------------------------------------------------------
# Canonical 7-Layer Mesh Node Configurations (Rule 0 & Rule 9 IP Matrix)
# ---------------------------------------------------------------------------
MESH_NODES: Dict[str, NodeConfig] = {
    NodeLayer.L1.value: NodeConfig(
        node_id=NodeLayer.L1.value,
        name="Mac Mini Host (M4 Pro)",
        layer=NodeLayer.L1,
        os_type="darwin",
        nominal_ram_gb=24.0,
        nominal_ai_cap_gb=21.6,
        max_utilization_pct=80.0,
        min_sanctuary_free_mb=HOST_SANCTUARY_MIN_MB,
        ip_priority_list=[
            "127.0.0.1",           # 1. Localhost
            "192.168.2.2",         # 2. TB4 Bridge
            "10.255.0.1",          # 3. Nebula Overlay
            "100.119.199.76",      # 4. Tailscale Overlay
            "192.168.8.230",       # 5. Local Ethernet (en0)
            "192.168.8.71",        # 6. Local Wi-Fi (en1)
        ],
        telemetry_port=8085,
        is_local_host=True,
        notes="Apple M4 Pro, 24GB Unified RAM. Host sanctuary required (>=4.8GB free, <=80% util).",
    ),
    NodeLayer.L2.value: NodeConfig(
        node_id=NodeLayer.L2.value,
        name="MacBook Pro (Intel Core i7)",
        layer=NodeLayer.L2,
        os_type="darwin",
        nominal_ram_gb=16.0,
        nominal_ai_cap_gb=14.0,
        max_utilization_pct=90.0,
        min_sanctuary_free_mb=1638.4,  # 10% min free
        ip_priority_list=[
            "192.168.2.3",         # 1. TB4 Bridge
            "169.254.187.138",     # 2. TB3/TB4 Direct IPv4
            "10.255.0.2",          # 3. Nebula Overlay
            "100.103.212.21",      # 4. Tailscale Overlay
            "192.168.8.116",       # 5. Local Wi-Fi
        ],
        telemetry_port=8085,
        is_local_host=False,
        notes="Intel Core i7, 16GB RAM. Model Vault & Metal GPU RPC via TB3/TB4.",
    ),
    NodeLayer.L3.value: NodeConfig(
        node_id=NodeLayer.L3.value,
        name="Linux Hub (Ryzen 7 5700U)",
        layer=NodeLayer.L3,
        os_type="linux",
        nominal_ram_gb=16.0,
        nominal_ai_cap_gb=13.8,
        max_utilization_pct=80.0,
        min_sanctuary_free_mb=3276.8,  # 20% min free
        ip_priority_list=[
            "10.255.0.3",          # 1. Nebula Overlay
            "100.101.39.98",       # 2. Tailscale Overlay
            "192.168.8.225",       # 3. Wired WoL LAN
            "192.168.8.183",       # 4. Wi-Fi LAN
        ],
        telemetry_port=18802,
        is_local_host=False,
        notes="AMD Ryzen 7 5700U, 16GB RAM. Docker Hub, Petals DHT, overnight fine-tuning queue.",
    ),
    NodeLayer.L4.value: NodeConfig(
        node_id=NodeLayer.L4.value,
        name="Linux Tablet (Debian)",
        layer=NodeLayer.L4,
        os_type="linux",
        nominal_ram_gb=8.0,
        nominal_ai_cap_gb=6.5,
        max_utilization_pct=75.0,
        min_sanctuary_free_mb=2048.0,  # 25% min free
        ip_priority_list=[
            "192.168.2.4",         # 1. Bluetooth PAN
            "10.255.0.4",          # 2. Nebula Overlay
            "100.81.92.125",       # 3. Tailscale Overlay
            "192.168.8.54",        # 4. Wi-Fi LAN
            "192.168.8.173",       # 5. Alt Wi-Fi LAN
        ],
        telemetry_port=8085,
        is_local_host=False,
        notes="Debian Tablet, 8GB RAM. Mobile Linux compute, touch DSP.",
    ),
    NodeLayer.L5.value: NodeConfig(
        node_id=NodeLayer.L5.value,
        name="MacBook Air (Apple M4)",
        layer=NodeLayer.L5,
        os_type="darwin",
        nominal_ram_gb=16.0,
        nominal_ai_cap_gb=14.0,
        max_utilization_pct=90.0,
        min_sanctuary_free_mb=1638.4,  # 10% min free
        ip_priority_list=[
            "192.168.2.5",         # 1. TB4 Bridge / PAN
            "10.255.0.5",          # 2. Nebula Overlay
            "100.121.202.34",      # 3. Tailscale Overlay
            "192.168.8.34",        # 4. Wi-Fi 7 (6GHz)
        ],
        telemetry_port=8085,
        is_local_host=False,
        notes="Apple M4, 16GB Unified RAM. Metal Performance Shaders, LoRA distillation.",
    ),
    NodeLayer.L6.value: NodeConfig(
        node_id=NodeLayer.L6.value,
        name="Pixel 10 Pro XL (Tensor G5)",
        layer=NodeLayer.L6,
        os_type="android",
        nominal_ram_gb=16.0,
        nominal_ai_cap_gb=12.5,
        max_utilization_pct=85.0,
        min_sanctuary_free_mb=2457.6,  # 15% min free
        ip_priority_list=[
            "192.168.44.1",        # 1. PAN / USB Tether
            "10.255.0.6",          # 2. Nebula Overlay
            "100.73.38.87",        # 3. Tailscale Overlay
            "192.168.8.33",        # 4. Wi-Fi 7 (6GHz)
        ],
        telemetry_port=8085,
        is_local_host=False,
        notes="Google Tensor G5, 16GB RAM. Edge TPU, 8K Vision Stream, Screen Lens VLA.",
    ),
    NodeLayer.L7.value: NodeConfig(
        node_id=NodeLayer.L7.value,
        name="Samsung S20 (Exynos 990)",
        layer=NodeLayer.L7,
        os_type="android",
        nominal_ram_gb=12.0,
        nominal_ai_cap_gb=9.0,
        max_utilization_pct=75.0,
        min_sanctuary_free_mb=3072.0,  # 25% min free
        ip_priority_list=[
            "192.168.44.2",        # 1. PAN Tether
            "10.200.110.217",      # 2. USB Tether
            "10.255.0.7",          # 3. Nebula Overlay
            "100.84.40.95",        # 4. Tailscale Overlay
            "100.99.123.58",       # 5. Alt Tailscale
            "192.168.8.10",        # 6. Wi-Fi LAN
        ],
        telemetry_port=8085,
        is_local_host=False,
        notes="Samsung Exynos 990, 12GB RAM. Automated UI tester via router USB ADB.",
    ),
    NodeLayer.GW.value: NodeConfig(
        node_id=NodeLayer.GW.value,
        name="GL.iNet Gateway (GL-MT3600BE)",
        layer=NodeLayer.GW,
        os_type="openwrt",
        nominal_ram_gb=0.5,
        nominal_ai_cap_gb=0.0,
        max_utilization_pct=90.0,
        min_sanctuary_free_mb=50.0,
        ip_priority_list=[
            "192.168.8.1",         # 1. Core LAN
            "10.255.0.254",        # 2. Nebula Gateway
            "100.112.203.121",     # 3. Tailscale
        ],
        telemetry_port=8085,
        is_local_host=False,
        notes="Embedded OpenWrt router, hardware USB bridge and gateway.",
    ),
}

# ---------------------------------------------------------------------------
# ELO Default Model Hierarchy (Rule 15)
# ---------------------------------------------------------------------------
DEFAULT_MODEL_ELO: Dict[str, Any] = {
    "master_orchestrator": {
        "model": "qwen_38_max_abliterated",
        "port": LOCAL_TOOL_ROUTER_PORT,
        "elo": 1734,
        "notes": "Sovereign Master Local Orchestrator & Hermes 3 tool router",
    },
    "syntax_worker": {
        "model": "qwen2.5-coder-7b-instruct",
        "port": LOCAL_SYNTAX_WORKER_PORT,
        "elo": 1650,
        "notes": "Subordinate Syntax Worker for fast code generation",
    },
    "red_team": {
        "model": "qwen_38_max",
        "port": LOCAL_RED_TEAM_PORT,
        "elo": 1700,
        "notes": "Canonical Adversarial Red Team / Dialectic Challenger",
    },
}


def load_mesh_ip_matrix(path: Optional[Path] = None) -> Dict[str, NodeConfig]:
    """
    Loads dynamic mesh IP matrix from disk if available, updating MESH_NODES.
    Defaults to canonical matrix when file is not present.
    """
    if path is None:
        path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_ip_matrix.json")

    if not path.exists():
        return MESH_NODES

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for node_id, ips in data.items():
            if node_id in MESH_NODES:
                priority_list = []
                # Prioritize: tb4/tb3 bridge -> pan -> nebula -> tailscale -> ethernet -> wifi
                key_order = ["tb4_bridge", "tb3_bridge", "tb3_ipv6", "pan", "pan_tether", "usb_tether", "nebula", "tailscale", "ethernet", "wifi", "alt_wifi", "lan", "localhost"]
                for k in key_order:
                    if k in ips and ips[k] not in priority_list:
                        priority_list.append(ips[k])
                # Add any remaining non-port/mac fields
                for k, v in ips.items():
                    if isinstance(v, str) and not k.startswith("rf_") and k not in ("ssh_port", "note", "status"):
                        if v not in priority_list and ":" not in v:
                            priority_list.append(v)
                if priority_list:
                    MESH_NODES[node_id].ip_priority_list = priority_list
    except Exception:
        pass

    return MESH_NODES
