"""
canonical_sync_engine.config
Central configuration for vault paths, mesh topology, timeouts, and storage thresholds.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union


@dataclass(frozen=True)
class MeshNodeConfig:
    """Configuration and network identity for a physical node in the Lauburu Mesh."""
    node_id: str
    name: str
    layer: str  # "L1", "L2", "L3", "L4", "L5", "L6", "L7", "GW"
    local_ip: str
    tailscale_ip: str
    tb4_ip: Optional[str] = None
    ssh_port: int = 22
    ssh_user: str = "aaron"
    ssh_key_path: Optional[str] = None
    adb_port: Optional[int] = None
    http_port: Optional[int] = None
    probe_timeout_sec: float = 2.0
    is_critical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "layer": self.layer,
            "local_ip": self.local_ip,
            "tailscale_ip": self.tailscale_ip,
            "tb4_ip": self.tb4_ip,
            "ssh_port": self.ssh_port,
            "ssh_user": self.ssh_user,
            "ssh_key_path": self.ssh_key_path,
            "adb_port": self.adb_port,
            "http_port": self.http_port,
            "probe_timeout_sec": self.probe_timeout_sec,
            "is_critical": self.is_critical,
        }


# Canonical 7-Layer Mesh Topology Matrix per Rule 2
DEFAULT_MESH_TOPOLOGY: Dict[str, MeshNodeConfig] = {
    "L1": MeshNodeConfig(
        node_id="L1",
        name="Mac_Node",
        layer="L1",
        local_ip="192.168.8.230",
        tailscale_ip="100.119.199.76",
        ssh_port=22,
        ssh_user="aaron",
        ssh_key_path="/Users/aaron/.ssh/id_ed25519",
        http_port=18802,
        probe_timeout_sec=1.5,
        is_critical=True,
    ),
    "L2": MeshNodeConfig(
        node_id="L2",
        name="MacBook_Pro",
        layer="L2",
        local_ip="192.168.8.127",
        tailscale_ip="100.103.212.21",
        tb4_ip="169.254.187.138",
        ssh_port=22,
        ssh_user="aaron",
        ssh_key_path="/Users/aaron/.ssh/id_ed25519_monorepo",
        probe_timeout_sec=2.0,
        is_critical=False,
    ),
    "L3": MeshNodeConfig(
        node_id="L3",
        name="Linux_Head_Node",
        layer="L3",
        local_ip="192.168.8.224",
        tailscale_ip="100.101.39.98",
        ssh_port=22,
        ssh_user="aaron",
        ssh_key_path="/Users/aaron/.ssh/id_ed25519_monorepo",
        http_port=6333,
        probe_timeout_sec=2.0,
        is_critical=False,
    ),
    "L4": MeshNodeConfig(
        node_id="L4",
        name="Linux_Tablet",
        layer="L4",
        local_ip="DHCP",
        tailscale_ip="100.81.92.125",
        ssh_port=22,
        ssh_user="aaron",
        ssh_key_path="/Users/aaron/.ssh/id_ed25519_monorepo",
        probe_timeout_sec=2.5,
        is_critical=False,
    ),
    "L5": MeshNodeConfig(
        node_id="L5",
        name="MacBook_Air",
        layer="L5",
        local_ip="192.168.8.222",
        tailscale_ip="100.93.158.96",
        ssh_port=22,
        ssh_user="aaron",
        ssh_key_path="/Users/aaron/.ssh/id_ed25519",
        probe_timeout_sec=2.0,
        is_critical=False,
    ),
    "L6": MeshNodeConfig(
        node_id="L6",
        name="Pixel_10_Pro_XL",
        layer="L6",
        local_ip="DHCP",
        tailscale_ip="100.73.38.87",
        ssh_port=8022,
        ssh_user="u0_a363",
        ssh_key_path="/Users/aaron/.ssh/id_ed25519_monorepo",
        probe_timeout_sec=3.0,
        is_critical=False,
    ),
    "L7": MeshNodeConfig(
        node_id="L7",
        name="Samsung_S20",
        layer="L7",
        local_ip="DHCP",
        tailscale_ip="100.84.40.95",
        adb_port=5555,
        probe_timeout_sec=3.0,
        is_critical=False,
    ),
    "GW": MeshNodeConfig(
        node_id="GW",
        name="GL.iNet Router",
        layer="GW",
        local_ip="192.168.8.1",
        tailscale_ip="100.122.185.123",
        ssh_port=22,
        ssh_user="root",
        probe_timeout_sec=1.5,
        is_critical=False,
    ),
}


@dataclass
class SyncConfig:
    """Master configuration for canonical synchronization and storage verification."""
    # Vault Paths
    obsidian_vault_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
        )).expanduser().resolve()
    )
    pyspark_dataset_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "PYSPARK_DATASET_PATH",
            "/Users/aaron/DFS_UNIFIED/lora_datasets"
        )).expanduser().resolve()
    )
    pyspark_memory_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "PYSPARK_MEMORY_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
        )).expanduser().resolve()
    )
    git_repo_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "GIT_REPO_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
        )).expanduser().resolve()
    )
    gdrive_mount_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "GDRIVE_MOUNT_PATH",
            "/Volumes/Google Drive/My Drive/Lauburu_AI_Memory"
        )).expanduser().resolve()
    )
    gdrive_fallback_cache_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "GDRIVE_FALLBACK_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache"
        )).expanduser().resolve()
    )

    # Thresholds & Timeouts
    min_disk_headroom_gb: float = field(
        default_factory=lambda: float(os.environ.get("CANONICAL_SYNC_MIN_HEADROOM_GB", "10.0"))
    )
    fast_path_min_disk_headroom_gb: float = 5.0
    fast_path_max_duration_ms: float = 3.0
    network_timeout_sec: float = 3.0

    # Mesh Node Topology
    mesh_nodes: Dict[str, MeshNodeConfig] = field(
        default_factory=lambda: dict(DEFAULT_MESH_TOPOLOGY)
    )

    # Operating Environment
    env: str = field(
        default_factory=lambda: os.environ.get("CANONICAL_SYNC_ENV", "production").lower()
    )
    auto_heal: bool = True

    @classmethod
    def from_env(cls) -> SyncConfig:
        """Instantiates configuration loading values from environment variables."""
        return cls()

    @classmethod
    def for_testing(cls, base_dir: Union[str, Path]) -> SyncConfig:
        """
        Creates an isolated, hermetic testing configuration with all vaults located
        inside subdirectories of the provided base_dir.
        """
        base = Path(base_dir).resolve()
        obsidian_dir = base / "obsidian_vault"
        pyspark_dir = base / "lora_datasets"
        memory_dir = base / "04_data_and_memory"
        git_dir = base / "git_repo"
        gdrive_dir = base / "gdrive_mount"
        gdrive_cache = base / "data" / "gdrive_cache"

        for d in [obsidian_dir, pyspark_dir, memory_dir, git_dir, gdrive_dir, gdrive_cache]:
            d.mkdir(parents=True, exist_ok=True)

        return cls(
            obsidian_vault_path=obsidian_dir,
            pyspark_dataset_path=pyspark_dir,
            pyspark_memory_path=memory_dir,
            git_repo_path=git_dir,
            gdrive_mount_path=gdrive_dir,
            gdrive_fallback_cache_path=gdrive_cache,
            min_disk_headroom_gb=1.0,  # Lower threshold for temp test mounts
            fast_path_min_disk_headroom_gb=0.5,
            env="test",
            auto_heal=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obsidian_vault_path": str(self.obsidian_vault_path),
            "pyspark_dataset_path": str(self.pyspark_dataset_path),
            "pyspark_memory_path": str(self.pyspark_memory_path),
            "git_repo_path": str(self.git_repo_path),
            "gdrive_mount_path": str(self.gdrive_mount_path),
            "gdrive_fallback_cache_path": str(self.gdrive_fallback_cache_path),
            "min_disk_headroom_gb": self.min_disk_headroom_gb,
            "fast_path_min_disk_headroom_gb": self.fast_path_min_disk_headroom_gb,
            "fast_path_max_duration_ms": self.fast_path_max_duration_ms,
            "network_timeout_sec": self.network_timeout_sec,
            "mesh_nodes": {k: v.to_dict() for k, v in self.mesh_nodes.items()},
            "env": self.env,
            "auto_heal": self.auto_heal,
        }
