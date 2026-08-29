"""
7-Layer Physical Mesh Node Registry.
====================================
Subsystem: 01_apps/operator_and_dev/canonical_port/nodes/mesh_nodes.py
"""

from typing import List
from ..core.models import MeshNodeInfo

MESH_NODES: List[MeshNodeInfo] = [
    MeshNodeInfo(
        layer="L1",
        node_name="Mac_Node",
        network_role="Primary Host & Memory Governor (Apple M4 Pro)",
        local_ip="192.168.8.230",
        tailscale_ip="100.119.199.76",
        physical_ram_gb=24.0,
        usable_ai_vram_gb=21.6,
        dynamic_cap_pct=0.90,
        active_models=["Qwen-7B-Math", "Hermes-3-8B"]
    ),
    MeshNodeInfo(
        layer="L2",
        node_name="MacBook_Pro",
        network_role="Metal GPU RPC & Storage Vault (10Gbps TB4 Bridge: 0.27ms RTT)",
        local_ip="192.168.8.127",
        tailscale_ip="100.103.212.21",
        physical_ram_gb=16.0,
        usable_ai_vram_gb=14.0,
        dynamic_cap_pct=0.90,
        active_models=["llama.cpp-RPC-Metal"]
    ),
    MeshNodeInfo(
        layer="L3",
        node_name="Linux_Head_Node",
        network_role="Gateway Ingress & Compute Hub (AMD Ryzen 7 5700U)",
        local_ip="192.168.8.224",
        tailscale_ip="100.101.39.98",
        physical_ram_gb=16.0,
        usable_ai_vram_gb=13.8,
        dynamic_cap_pct=0.80,
        active_models=["Petals-DHT-Bootstrap", "Apache-Ray"]
    ),
    MeshNodeInfo(
        layer="L4",
        node_name="Linux_Tablet",
        network_role="Mobile Linux Compute & Touch DSP (Debian)",
        local_ip="DHCP",
        tailscale_ip="100.81.92.125",
        physical_ram_gb=8.0,
        usable_ai_vram_gb=6.5,
        dynamic_cap_pct=0.75,
        active_models=["Petals-Worker"]
    ),
    MeshNodeInfo(
        layer="L5",
        node_name="MacBook_Air",
        network_role="Secondary High-Speed Metal Worker (Apple M4)",
        local_ip="192.168.8.222",
        tailscale_ip="100.93.158.96",
        physical_ram_gb=16.0,
        usable_ai_vram_gb=14.0,
        dynamic_cap_pct=0.90,
        active_models=["LoRA-Distillation-Worker"]
    ),
    MeshNodeInfo(
        layer="L6",
        node_name="Pixel_10_Pro_XL",
        network_role="8K Vision Stream & Edge TPU (Google Tensor G5)",
        local_ip="DHCP",
        tailscale_ip="100.73.38.87",
        physical_ram_gb=16.0,
        usable_ai_vram_gb=12.5,
        dynamic_cap_pct=0.85,
        active_models=["Edge-TPU-Pose"]
    ),
    MeshNodeInfo(
        layer="L7",
        node_name="Samsung_S20",
        network_role="Dedicated Automated UI Tester (Samsung Exynos 990)",
        local_ip="DHCP",
        tailscale_ip="100.84.40.95",
        physical_ram_gb=12.0,
        usable_ai_vram_gb=9.0,
        dynamic_cap_pct=0.75,
        active_models=["OpenClaw-Automator"]
    ),
]
