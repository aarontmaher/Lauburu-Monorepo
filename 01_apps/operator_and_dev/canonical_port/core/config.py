"""
Canonical Port Configuration.
=============================
Subsystem: 01_apps/operator_and_dev/canonical_port/core/config.py
"""

from dataclasses import dataclass
from typing import Dict

@dataclass
class CanonicalPortConfig:
    port: int = 8088
    total_mesh_nodes: int = 7
    total_physical_ram_gb: float = 108.0
    total_usable_vram_gb: float = 82.8
    host_node: str = "Mac_Node"
    storage_obsidian_path: str = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
    storage_lora_path: str = "/Users/aaron/DFS_UNIFIED/lora_datasets"
