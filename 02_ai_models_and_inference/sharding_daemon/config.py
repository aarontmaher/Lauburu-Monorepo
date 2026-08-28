#!/usr/bin/env python3
"""
Canonical Configuration & Hardware Cluster Matrix for Lauburu AI Sharding Mesh
==============================================================================
Defines the 8-node physical hardware topology, OS-specific dynamic RAM ceilings,
usable AI VRAM allocations (82.8 GB total pooled usable VRAM across 108.0 GB RAM),
model catalogs, default ports, and transport tier interconnect performance metrics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class TransportTier(str, Enum):
    """Interconnect performance tiers across the heterogeneous physical mesh."""
    TB4_DMA = "TB4_DMA"                # Thunderbolt 4 PCIe DMA (0.27ms RTT, 40 Gbps, score 1.00)
    LAN_1GBE = "LAN_1GBE"              # TP-Link 1GbE Extender / Direct Ethernet (0.90ms RTT, 1 Gbps, score 0.85)
    MULTIPATH_BOND = "MULTIPATH_BOND"  # Bonded Multi-WAN (1.50ms RTT, 3.4 Gbps, score 0.80)
    WIFI7_MLO = "WIFI7_MLO"            # GL.iNet Wi-Fi 7 Multi-Link Operation (2.10ms RTT, 2.4 Gbps, score 0.70)
    TAILSCALE_DIRECT = "TAILSCALE_DIRECT" # Direct WireGuard Peer Routing (3.50ms RTT, 500 Mbps, score 0.50)
    TAILSCALE_DERP = "TAILSCALE_DERP"     # Encrypted DERP Relay Fallback (35.0ms RTT, 50 Mbps, score 0.15)


@dataclass(frozen=True)
class TransportMetrics:
    tier: TransportTier
    nominal_rtt_ms: float
    nominal_bandwidth_mbps: float
    reliability_score: float
    description: str


TRANSPORT_TIER_PROFILES: Dict[TransportTier, TransportMetrics] = {
    TransportTier.TB4_DMA: TransportMetrics(
        tier=TransportTier.TB4_DMA,
        nominal_rtt_ms=0.27,
        nominal_bandwidth_mbps=40000.0,
        reliability_score=1.00,
        description="High-Speed PCIe DMA Thunderbolt 4 bridge between Mac Mini and MacBook Pro"
    ),
    TransportTier.LAN_1GBE: TransportMetrics(
        tier=TransportTier.LAN_1GBE,
        nominal_rtt_ms=0.90,
        nominal_bandwidth_mbps=1000.0,
        reliability_score=0.85,
        description="TP-Link 1GbE low-latency copper interconnect to Linux Head Node"
    ),
    TransportTier.MULTIPATH_BOND: TransportMetrics(
        tier=TransportTier.MULTIPATH_BOND,
        nominal_rtt_ms=1.50,
        nominal_bandwidth_mbps=3400.0,
        reliability_score=0.80,
        description="Aggregated multipath channel bonding across Wi-Fi 7 + Ethernet + USB"
    ),
    TransportTier.WIFI7_MLO: TransportMetrics(
        tier=TransportTier.WIFI7_MLO,
        nominal_rtt_ms=2.10,
        nominal_bandwidth_mbps=2400.0,
        reliability_score=0.70,
        description="GL-MT3600BE-a0f-MLO Wi-Fi 7 6GHz/5GHz multi-link wireless transport"
    ),
    TransportTier.TAILSCALE_DIRECT: TransportMetrics(
        tier=TransportTier.TAILSCALE_DIRECT,
        nominal_rtt_ms=3.50,
        nominal_bandwidth_mbps=500.0,
        reliability_score=0.50,
        description="Direct peer-to-peer WireGuard tunnel with zero relay hop"
    ),
    TransportTier.TAILSCALE_DERP: TransportMetrics(
        tier=TransportTier.TAILSCALE_DERP,
        nominal_rtt_ms=35.0,
        nominal_bandwidth_mbps=50.0,
        reliability_score=0.15,
        description="Encrypted DERP relay fallback for NAT traversal when direct links fail"
    ),
}


# Standardized Port Allocations
RPC_PORT = 50052
LLAMA_SERVER_MASTER_PORT = 8081
PETALS_DHT_BOOTSTRAP_PORT = 31330
EXO_ZENOH_PORT = 52415
ACCELERATE_TORCHRUN_PORT = 29500
SHARDING_DAEMON_CONTROL_PORT = 18888
EDGE_SERVER_PORT = 8084
VISION_SERVER_PORT = 8085

DEFAULT_PORTS = {
    "rpc_port": RPC_PORT,
    "llama_master_port": LLAMA_SERVER_MASTER_PORT,
    "petals_dht_port": PETALS_DHT_BOOTSTRAP_PORT,
    "exo_zenoh_port": EXO_ZENOH_PORT,
    "accelerate_port": ACCELERATE_TORCHRUN_PORT,
    "sharding_daemon_control": SHARDING_DAEMON_CONTROL_PORT,
    "edge_server_port": EDGE_SERVER_PORT,
    "vision_server_port": VISION_SERVER_PORT,
}

# Dynamic Cluster Capacity Constants
CLUSTER_POOLED_VRAM_GB = 82.8
CLUSTER_POOLED_RAM_GB = 108.0
MOBILE_THERMAL_CUTOFF_CELSIUS = 41.0


@dataclass
class NodeSpec:
    """Hardware node specification in the 8-node physical mesh."""
    node_id: str
    name: str
    layer_level: str
    hardware_specs: str
    total_ram_gb: float
    ceiling_pct: float
    usable_vram_gb: float
    tailscale_ip: str
    local_ip: Optional[str] = None
    tb4_ip: Optional[str] = None
    usb_ip: Optional[str] = None
    ssh_port: int = 22
    ssh_user: str = "aaron"
    rpc_port: int = RPC_PORT
    dht_port: int = PETALS_DHT_BOOTSTRAP_PORT
    exo_port: int = EXO_ZENOH_PORT
    is_mobile: bool = False
    thermal_cutoff_c: float = 41.0
    primary_interconnect: TransportTier = TransportTier.TAILSCALE_DIRECT
    assigned_role: str = ""
    active_backends: List[str] = field(default_factory=lambda: ["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"])

    @property
    def max_usable_bytes(self) -> int:
        return int(self.usable_vram_gb * (1024 ** 3))


# Canonical 8-Node Physical Hardware Matrix
# Total Pooled Cluster RAM: 108.0 GB | Total Pooled Usable VRAM: 82.8 GB
CLUSTER_NODES: Dict[str, NodeSpec] = {
    "mac_host": NodeSpec(
        node_id="mac_host",
        name="Mac_Node (Primary Host)",
        layer_level="L1",
        hardware_specs="Apple M4 Pro (12C CPU / 16C GPU / 16-Core ANE)",
        total_ram_gb=24.0,
        ceiling_pct=90.0,
        usable_vram_gb=21.6,
        tailscale_ip="100.119.199.76",
        local_ip="192.168.8.230",
        ssh_port=22,
        ssh_user="aaron",
        primary_interconnect=TransportTier.TB4_DMA,
        assigned_role="Master DHT Bootstrap, Prompt Ingestion, llama-server Master, Memory Governor",
        active_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
    ),
    "macbook_pro": NodeSpec(
        node_id="macbook_pro",
        name="MacBook_Pro (M1 Max Vault)",
        layer_level="L2",
        hardware_specs="Apple M1 Max (10C CPU / 32C GPU / 400 GB/s Unified Memory)",
        total_ram_gb=16.0,
        ceiling_pct=90.0,
        usable_vram_gb=14.0,
        tailscale_ip="100.103.212.21",
        local_ip="192.168.8.127",
        tb4_ip="169.254.187.138",
        ssh_port=22,
        ssh_user="aaron",
        primary_interconnect=TransportTier.TB4_DMA,
        assigned_role="Metal GPU RPC Worker (ggml-rpc-server), 285 GB Model Vault",
        active_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
    ),
    "linux_node": NodeSpec(
        node_id="linux_node",
        name="Linux_Head_Node",
        layer_level="L3",
        hardware_specs="AMD Ryzen 7 5700U (8C / 16T / Radeon Vega 8 GPU)",
        total_ram_gb=16.0,
        ceiling_pct=80.0,
        usable_vram_gb=13.8,
        tailscale_ip="100.101.39.98",
        local_ip="192.168.8.224",
        ssh_port=22,
        ssh_user="aaron",
        primary_interconnect=TransportTier.LAN_1GBE,
        assigned_role="Gateway Ingress, Docker Hub, Petals DHT Bootstrap & Apache Ray Compute",
        active_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
    ),
    "macbook_air": NodeSpec(
        node_id="macbook_air",
        name="MacBook_Air (M4)",
        layer_level="L5",
        hardware_specs="Apple M4 MacBook Air (10C GPU / Metal Performance Shaders)",
        total_ram_gb=16.0,
        ceiling_pct=90.0,
        usable_vram_gb=14.0,
        tailscale_ip="100.93.158.96",
        local_ip="192.168.8.222",
        ssh_port=22,
        ssh_user="aaron",
        primary_interconnect=TransportTier.WIFI7_MLO,
        assigned_role="Secondary High-Speed Metal Worker, Continuous LoRA Distillation",
        active_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
    ),
    "pixel_10": NodeSpec(
        node_id="pixel_10",
        name="Pixel_10_Pro_XL",
        layer_level="L6",
        hardware_specs="Google Tensor G5 (Android 15 / Edge TPU / 8K Digital PTZ)",
        total_ram_gb=16.0,
        ceiling_pct=85.0,
        usable_vram_gb=12.5,
        tailscale_ip="100.73.38.87",
        usb_ip="169.254.60.151",
        ssh_port=8022,
        ssh_user="aaron",
        is_mobile=True,
        thermal_cutoff_c=41.0,
        primary_interconnect=TransportTier.MULTIPATH_BOND,
        assigned_role="Edge TPU Worker, Vision Stream Projector, Mobile DHT Node",
        active_backends=["llamacpp_rpc", "petals_dht", "exo_p2p"],
    ),
    "samsung_s20": NodeSpec(
        node_id="samsung_s20",
        name="Samsung_S20",
        layer_level="L7",
        hardware_specs="Samsung Exynos 990 (Android 13/14 / Router USB Bridge)",
        total_ram_gb=12.0,
        ceiling_pct=75.0,
        usable_vram_gb=9.0,
        tailscale_ip="100.84.40.95",
        ssh_port=8022,
        ssh_user="aaron",
        is_mobile=True,
        thermal_cutoff_c=41.0,
        primary_interconnect=TransportTier.TAILSCALE_DIRECT,
        assigned_role="Dedicated Automated UI Tester, OpenClaw Agent, Low-Layer Telemetry Shard",
        active_backends=["petals_dht", "exo_p2p"],
    ),
    "linux_tablet": NodeSpec(
        node_id="linux_tablet",
        name="Linux_Tablet",
        layer_level="L4",
        hardware_specs="Debian Linux Touch x86_64",
        total_ram_gb=8.0,
        ceiling_pct=75.0,
        usable_vram_gb=6.0,
        tailscale_ip="100.81.92.125",
        ssh_port=22,
        ssh_user="aaron",
        primary_interconnect=TransportTier.TAILSCALE_DIRECT,
        assigned_role="Mobile Linux Compute, Secondary Petals Worker, Biometrics DSP",
        active_backends=["petals_dht", "exo_p2p"],
    ),
    "router_gw": NodeSpec(
        node_id="router_gw",
        name="GL.iNet Router (GL-MT3600BE)",
        layer_level="GW",
        hardware_specs="OpenWrt Linux aarch64 Gateway",
        total_ram_gb=0.0,
        ceiling_pct=50.0,
        usable_vram_gb=0.0,
        tailscale_ip="100.122.185.123",
        local_ip="192.168.8.1",
        ssh_port=22,
        ssh_user="root",
        primary_interconnect=TransportTier.LAN_1GBE,
        assigned_role="Core Gateway, Subnet Router, Hardware USB Hub, OpenWrt Port Forwarder",
        active_backends=[],
    ),
}

# Core Compute Cluster (excluding standby tablet / gateway)
CORE_COMPUTE_NODES = ["mac_host", "macbook_pro", "linux_node", "macbook_air", "pixel_10", "samsung_s20"]


@dataclass
class ModelCatalogEntry:
    """Specification of an AI model supported for distributed execution."""
    model_id: str
    repo_id: str
    name: str
    params: str
    total_layers: int
    hidden_dim: int
    num_heads: int
    size_fp16_gb: float
    size_q4km_gb: float
    size_8bit_gb: float
    recommended_vram_gb: float
    default_tensor_split: Dict[str, int] = field(default_factory=dict)
    supported_backends: List[str] = field(default_factory=lambda: ["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"])
    description: str = ""


# Comprehensive Model Catalogs
MODEL_CATALOG: Dict[str, ModelCatalogEntry] = {
    "kimi-dev-72b": ModelCatalogEntry(
        model_id="kimi-dev-72b",
        repo_id="moonshotai/Kimi-Dev-72B",
        name="Kimi-Dev-72B (Distributed Reasoning & Code)",
        params="72B",
        total_layers=80,
        hidden_dim=8192,
        num_heads=64,
        size_fp16_gb=144.0,
        size_q4km_gb=39.0,
        size_8bit_gb=74.0,
        recommended_vram_gb=40.0,
        default_tensor_split={"linux_node": 28, "macbook_pro": 28, "mac_host": 24},
        supported_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
        description="Frontier 72B reasoning LLM sharded across Linux Head Node, MacBook Pro TB4, and Mac Mini Host."
    ),
    "bloom-560m": ModelCatalogEntry(
        model_id="bloom-560m",
        repo_id="bigscience/bloom-560m",
        name="BLOOM 560M (Bootstrap & Tensor Verification)",
        params="560M",
        total_layers=24,
        hidden_dim=1024,
        num_heads=16,
        size_fp16_gb=1.12,
        size_q4km_gb=0.45,
        size_8bit_gb=0.60,
        recommended_vram_gb=1.5,
        default_tensor_split={"mac_host": 24},
        supported_backends=["petals_dht", "llamacpp_rpc", "exo_p2p", "accelerate_lora"],
        description="Ultra-lightweight bootstrap model fitting 100% on any single node (Pixel, Samsung, Mac, Linux)."
    ),
    "stable-beluga-7b": ModelCatalogEntry(
        model_id="stable-beluga-7b",
        repo_id="petals-team/Stable-Beluga-7B",
        name="Stable Beluga 7B (Official Petals Swarm)",
        params="7.0B",
        total_layers=32,
        hidden_dim=4096,
        num_heads=32,
        size_fp16_gb=13.5,
        size_q4km_gb=3.8,
        size_8bit_gb=7.2,
        recommended_vram_gb=8.0,
        default_tensor_split={"mac_host": 16, "macbook_air": 16},
        supported_backends=["petals_dht", "llamacpp_rpc", "exo_p2p", "accelerate_lora"],
        description="Official Petals community model fine-tuned on Orca-style instruction datasets."
    ),
    "mistral-7b-instruct": ModelCatalogEntry(
        model_id="mistral-7b-instruct",
        repo_id="petals-team/Mistral-7B-Instruct-v0.1",
        name="Mistral 7B Instruct v0.1 (Sliding-Window Swarm)",
        params="7.2B",
        total_layers=32,
        hidden_dim=4096,
        num_heads=32,
        size_fp16_gb=14.5,
        size_q4km_gb=4.1,
        size_8bit_gb=7.5,
        recommended_vram_gb=8.5,
        default_tensor_split={"mac_host": 16, "macbook_air": 16},
        supported_backends=["petals_dht", "llamacpp_rpc", "exo_p2p", "accelerate_lora"],
        description="High-throughput sliding-window attention model adapted for collaborative generation."
    ),
    "qwen2.5-72b-instruct": ModelCatalogEntry(
        model_id="qwen2.5-72b-instruct",
        repo_id="Qwen/Qwen2.5-72B-Instruct",
        name="Qwen 2.5 72B Instruct (Full Cluster Swarm)",
        params="72.7B",
        total_layers=80,
        hidden_dim=8192,
        num_heads=64,
        size_fp16_gb=145.4,
        size_q4km_gb=42.0,
        size_8bit_gb=75.0,
        recommended_vram_gb=44.0,
        default_tensor_split={"mac_host": 24, "macbook_pro": 20, "macbook_air": 18, "linux_node": 18},
        supported_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
        description="Frontier instruction model pooled across 4-6 nodes over TB4 and 1GbE."
    ),
    "llama-3-70b-instruct": ModelCatalogEntry(
        model_id="llama-3-70b-instruct",
        repo_id="meta-llama/Meta-Llama-3-70B-Instruct",
        name="Llama 3 70B Instruct",
        params="70.6B",
        total_layers=80,
        hidden_dim=8192,
        num_heads=64,
        size_fp16_gb=141.2,
        size_q4km_gb=40.0,
        size_8bit_gb=73.0,
        recommended_vram_gb=42.0,
        default_tensor_split={"mac_host": 24, "macbook_pro": 20, "macbook_air": 18, "linux_node": 18},
        supported_backends=["llamacpp_rpc", "petals_dht", "exo_p2p", "accelerate_lora"],
        description="Llama-3 70B sharded across Mac Mini, MacBook Pro, MacBook Air, and Linux Head Node."
    ),
}


def get_cluster_total_usable_vram() -> float:
    """Returns total pooled usable AI VRAM across the primary cluster nodes in GB (82.8 GB)."""
    return sum(CLUSTER_NODES[nid].usable_vram_gb for nid in CORE_COMPUTE_NODES)


def get_cluster_total_physical_ram() -> float:
    """Returns total physical RAM across all cluster nodes in GB (108.0 GB)."""
    return sum(node.total_ram_gb for node in CLUSTER_NODES.values())


def get_node_spec(node_id: str) -> Optional[NodeSpec]:
    """Retrieve hardware node specification by ID or alias."""
    norm = node_id.lower().strip().replace("-", "_")
    return CLUSTER_NODES.get(norm)


def get_model_catalog(model_id: str) -> Optional[ModelCatalogEntry]:
    """Retrieve model catalog entry by model ID or key."""
    norm = model_id.lower().strip().replace("_", "-")
    return MODEL_CATALOG.get(norm)


def validate_cluster_vram_headroom(model_id: str, active_node_ids: Optional[List[str]] = None) -> Tuple[bool, float, float]:
    """
    Validates whether the cluster or active subset of nodes has sufficient usable VRAM for a model.
    Returns: (is_sufficient, total_available_gb, required_gb)
    """
    model = get_model_catalog(model_id)
    if not model:
        raise ValueError(f"Unknown model_id: '{model_id}'")
    
    if active_node_ids is None:
        nodes = [CLUSTER_NODES[nid] for nid in CORE_COMPUTE_NODES]
    else:
        nodes = [CLUSTER_NODES[nid] for nid in active_node_ids if nid in CLUSTER_NODES]
    
    available_gb = sum(n.usable_vram_gb for n in nodes)
    required_gb = model.size_q4km_gb
    return (available_gb >= required_gb, available_gb, required_gb)
