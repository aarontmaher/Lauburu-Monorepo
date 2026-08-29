"""
108GB Distributed Hardware & VRAM Pooling Governor.
===================================================
Subsystem: 01_apps/operator_and_dev/canonical_port/nodes/hardware_pool.py
"""

from typing import Dict, Any
from .mesh_nodes import MESH_NODES

def get_hardware_pool_summary() -> Dict[str, Any]:
    """Computes total physical RAM and pooled AI VRAM capacity across all 7 layers."""
    total_ram = sum(n.physical_ram_gb for n in MESH_NODES)
    total_ai_vram = sum(n.usable_ai_vram_gb for n in MESH_NODES)
    online_count = sum(1 for n in MESH_NODES if n.is_online)

    return {
        "total_nodes": len(MESH_NODES),
        "online_nodes": online_count,
        "total_physical_ram_gb": round(total_ram, 1),
        "total_usable_ai_vram_gb": round(total_ai_vram, 1),
        "tb4_bandwidth_gbps": 10.0,
        "tb4_rtt_ms": 0.27,
        "storage_tri_vault_healthy": True
    }
