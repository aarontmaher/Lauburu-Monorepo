"""
01_apps/canonical_port/tui/models/network_optimizer_models.py
============================================================
Pydantic v2 Models for Network System Settings Optimization & Real-Time Effect Tracking.
Governs all 6 categories: Kernel Sysctls, Interface MTUs, Sockets/BDP, DNS/Routing,
Mesh/Tailscale, and Remote Linux/Termux Mesh Nodes.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class NetworkSettingCategory(str, Enum):
    KERNEL_SYSCTL = "Kernel Sysctl (Darwin/XNU)"
    INTERFACE_MTU = "Interface & MTU Layer"
    SOCKET_BDP = "Socket Buffers & BDP Engine"
    DNS_ROUTING = "DNS, Routing & Multi-Homing"
    MESH_TAILSCALE = "Mesh, Tailscale & Speedify"
    REMOTE_NODES = "Remote Linux & Termux Nodes"


class SettingImpactMetric(str, Enum):
    RTT_LATENCY = "RTT Latency (ms)"
    THROUGHPUT = "Throughput (Mbps / Gbps)"
    JITTER = "Jitter & Packet Loss"
    QUEUE_DELAY = "Queue Delay / Bufferbloat"
    HANDSHAKE_TIME = "SYN/ACK Handshake Time"
    SYSTEM_RESOURCES = "Kernel Memory / Mbufs"


class SettingValueType(str, Enum):
    INTEGER = "int"
    BOOLEAN = "bool"
    STRING = "str"
    ENUM = "enum"


class NetworkSettingDefinition(BaseModel):
    """Canonical model for a single changeable/modifiable network system setting."""
    key: str = Field(..., description="Canonical sysctl or configuration key (e.g. net.inet.tcp.sendspace)")
    category: NetworkSettingCategory = Field(..., description="High-level architectural domain")
    name: str = Field(..., description="Human-friendly setting name")
    value_type: SettingValueType = Field(default=SettingValueType.INTEGER, description="Data type")
    current_value: Union[int, bool, str] = Field(..., description="Live value queried from the operating system")
    default_value: Union[int, bool, str] = Field(..., description="Standard OS default baseline value")
    min_value: Optional[Union[int, float]] = Field(default=None, description="Safe minimum value")
    max_value: Optional[Union[int, float]] = Field(default=None, description="Safe maximum value")
    step: Optional[Union[int, float]] = Field(default=None, description="Increment step for adjustments")
    unit: str = Field(default="", description="Measurement unit (bytes, ms, packets, etc.)")
    options: Optional[List[str]] = Field(default=None, description="Selectable options if enum")
    is_mutable: bool = Field(default=True, description="Whether the setting can be modified at runtime")
    requires_root: bool = Field(default=True, description="Whether root/sudo is required to modify")
    target_metric: SettingImpactMetric = Field(..., description="Primary network performance metric impacted")
    description: str = Field(..., description="Clear explanation of the parameter behavior")
    mathematical_formula: Optional[str] = Field(default=None, description="Underlying mathematical equation or principle")
    recommended_presets: Dict[str, Union[int, bool, str]] = Field(
        default_factory=dict,
        description="Recommended value for each profile: ai_tensor_sharding, high_throughput_tb4, resilient_mesh, stock_balanced"
    )
    line_by_line_analysis: str = Field(
        default="",
        description="Exhaustive scientific analysis of the kernel behavior and implications"
    )


class NetworkBenchmarkMetrics(BaseModel):
    """Empirical live performance metrics measured across real interfaces."""
    timestamp: float = Field(..., description="Epoch timestamp of measurement")
    gateway_rtt_ms: Optional[float] = Field(default=None, description="Live RTT to GL.iNet Router (192.168.8.1)")
    head_node_rtt_ms: Optional[float] = Field(default=None, description="Live RTT to Linux Head Node (192.168.8.224)")
    dns_cloudflare_rtt_ms: Optional[float] = Field(default=None, description="Live RTT to 1.1.1.1 Cloudflare DNS")
    avg_rtt_ms: float = Field(default=0.0, description="Composite average RTT")
    jitter_ms: float = Field(default=0.0, description="Measured RTT variance / jitter")
    handshake_latency_ms: float = Field(default=0.0, description="TCP SYN/ACK socket connection time to local RPC/Hub")
    loopback_throughput_mbps: float = Field(default=0.0, description="Local socket loopback transfer speed")
    queue_delay_index_ms: float = Field(default=0.0, description="Estimated bufferbloat / queue delay delta")
    packet_loss_pct: float = Field(default=0.0, description="Empirical packet loss percentage")
    dns_query_time_ms: float = Field(default=0.0, description="UDP 53 DNS query resolution time")


class OptimizationDeltaReport(BaseModel):
    """Tracks real-time Before vs After performance delta for setting changes."""
    baseline_metrics: NetworkBenchmarkMetrics
    current_metrics: NetworkBenchmarkMetrics
    delta_rtt_pct: float = Field(default=0.0, description="Percentage change in RTT (negative is better)")
    delta_jitter_pct: float = Field(default=0.0, description="Percentage change in Jitter (negative is better)")
    delta_handshake_pct: float = Field(default=0.0, description="Percentage change in Handshake time (negative is better)")
    delta_throughput_pct: float = Field(default=0.0, description="Percentage change in Throughput (positive is better)")
    delta_queue_delay_pct: float = Field(default=0.0, description="Percentage change in Queue Delay (negative is better)")
    overall_score: float = Field(default=50.0, description="Network Optimization Index Score (0-100)")
    active_profile: str = Field(default="stock_balanced", description="Currently applied optimization preset")


class BDPCalculation(BaseModel):
    """Bandwidth-Delay Product (BDP) analysis for a specific network link."""
    link_name: str
    bandwidth_mbps: float
    rtt_ms: float
    bdp_bytes: int
    bdp_formatted: str
    recommended_sendspace: int
    recommended_recvspace: int
    recommended_maxsockbuf: int
