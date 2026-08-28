# Milestone 1 (M1.1) Exploration Report: Core Models & Configuration

**Project:** `canonical_sync_engine`  
**Milestone:** M1.1 — Core Data Models & Central Configuration  
**Agent:** Explorer Agent (`teamwork_preview_explorer_m1_1`)  
**Date:** 2026-08-27T07:18:00+10:00  
**Working Directory:** `/Users/aaron/teamwork_projects/canonical_sync_engine/.agents/teamwork_preview_explorer_m1_1`

---

## 1. Executive Summary

This exploration report delivers the complete architectural and implementation specification for **Milestone 1.1 (M1.1: Core Models & Configuration)** of the `canonical_sync_engine`.

The `canonical_sync_engine` coordinates the verification of active mesh nodes and synchronizes canonical truth artifacts across four distinct storage vaults:
1. **PySpark Data Lake** (`/Users/aaron/DFS_UNIFIED/lora_datasets` and `04_data_and_memory`)
2. **Obsidian Knowledge Graph** (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault`)
3. **GitHub Monorepo Working Tree** (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`)
4. **Google Drive Cloud Mirror** (`/Volumes/Google Drive/My Drive` with local VFS fallback `data/gdrive_cache`)

This document defines:
1. **`canonical_sync_engine/config.py`**: Centralized configuration management supporting canonical paths, 7-layer mesh network topology, environment variable overrides, and testing sandbox factories.
2. **`canonical_sync_engine/models/artifact.py`**: `TruthArtifact` data contract, `ArtifactType` enum, deterministic canonical SHA-256 hashing over normalized JSON payloads, full dict/JSON roundtrips, and Obsidian Markdown frontmatter generation with bidirectional Wikilinks.
3. **`canonical_sync_engine/models/health.py`**: `NodeStorageHealth` and `StorageHealthReport` models tracking per-node metrics, headroom thresholds, inode states, and invariant violation reports.
4. **`canonical_sync_engine/models/sync_result.py`**: `VaultSyncResult` and `QuadVaultSyncResult` tracking atomic cross-vault sync execution, latency, bytes written, and granular failure diagnostics.
5. **Exact Test Specification for `tests/unit/test_models.py`**: 20 comprehensive Tier 1 (Unit) and Tier 2 (Boundary/Adversarial) test cases.

---

## 2. Component Design & Source Code Specifications

### 2.1 Central Configuration: `canonical_sync_engine/config.py`

#### Responsibilities
- Define canonical default paths matching the **Lauburu Mesh Ecosystem Rule 1 & Rule 6**.
- Maintain the **7-Layer Physical Mesh Topology Matrix** (L1 through L7 plus Gateway router).
- Support dynamic configuration via environment variables (`OBSIDIAN_VAULT_PATH`, `PYSPARK_DATASET_PATH`, `GIT_REPO_PATH`, `GDRIVE_MOUNT_PATH`, `CANONICAL_SYNC_MIN_HEADROOM_GB`, `CANONICAL_SYNC_ENV`).
- Provide an isolated `SyncConfig.for_testing(base_dir)` factory to enable hermetic, sandboxed testing without touching live production vaults.

#### Proposed Implementation Code

```python
"""
canonical_sync_engine.config
Central configuration for vault paths, mesh topology, timeouts, and storage thresholds.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any, Union


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
```

---

### 2.2 Truth Artifact Data Model: `canonical_sync_engine/models/artifact.py`

#### Responsibilities
- Define standard `ArtifactType` enum matching the core categories: `TRUTH_AUDIT`, `AI_DEBATE_CONSENSUS`, `ARCHITECTURAL_DECISION`, `TELEMETRY_RECORD`, `LORA_PAIR`, `BENCHMARK_RESULT`.
- Implement canonical deterministic SHA-256 computation over payload and envelope keys, ensuring that key insertion ordering never alters the computed hash.
- Provide lossless conversion methods: `to_dict()`, `from_dict()`, `to_json()`, `from_json()`.
- Generate valid Obsidian-compatible Markdown with YAML frontmatter, headers, formatted JSON payloads, and bidirectional Wikilinks (`[[Index]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`, `[[{artifact_type}]]`).

#### Proposed Implementation Code

```python
"""
canonical_sync_engine.models.artifact
Defines TruthArtifact, ArtifactType, deterministic SHA-256 hashing, and Obsidian Markdown formatting.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ArtifactType(str, Enum):
    """Canonical artifact types supported across the Quad-Vault ecosystem."""
    TRUTH_AUDIT = "truth_audit"
    AI_DEBATE_CONSENSUS = "ai_debate_consensus"
    ARCHITECTURAL_DECISION = "architectural_decision"
    TELEMETRY_RECORD = "telemetry_record"
    LORA_PAIR = "lora_pair"
    BENCHMARK_RESULT = "benchmark_result"

    @classmethod
    def from_string(cls, value: Union[str, ArtifactType]) -> ArtifactType:
        """Case-insensitive parser for ArtifactType."""
        if isinstance(value, cls):
            return value
        val_str = str(value).strip().lower()
        for member in cls:
            if member.value.lower() == val_str:
                return member
        # Fallback support for uppercase / enum name strings
        val_upper = str(value).strip().upper()
        if val_upper in cls.__members__:
            return cls[val_upper]
        raise ValueError(
            f"Unknown ArtifactType '{value}'. Valid types: {[m.value for m in cls]}"
        )


@dataclass
class TruthArtifact:
    """
    Canonical representation of a verified truth artifact.
    Guarantees deterministic SHA-256 hashing and cross-target format generation.
    """
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    payload: Dict[str, Any]
    source_node: str = "Mac_Node"
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    sha256_hash: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate and coerce artifact_type
        if not isinstance(self.artifact_type, ArtifactType):
            self.artifact_type = ArtifactType.from_string(self.artifact_type)

        # Validate mandatory string fields
        if not self.artifact_id or not isinstance(self.artifact_id, str):
            raise ValueError("artifact_id must be a non-empty string.")
        if not self.title or not isinstance(self.title, str):
            raise ValueError("title must be a non-empty string.")
        if not self.source_node or not isinstance(self.source_node, str):
            raise ValueError("source_node must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise TypeError(f"payload must be a Dict[str, Any], got {type(self.payload).__name__}.")

        # Auto-compute SHA-256 hash if absent
        if not self.sha256_hash:
            self.sha256_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """
        Computes a deterministic, canonical SHA-256 hash over the normalized JSON representation.
        Sorts all dictionary keys recursively to guarantee hash invariance across platforms.
        """
        canonical_envelope = {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "title": self.title,
            "payload": self.payload,
            "source_node": self.source_node,
            "timestamp": self.timestamp,
            "tags": sorted(self.tags) if self.tags else [],
            "metadata": self.metadata,
        }
        # Compact canonical JSON with sorted keys
        canonical_bytes = json.dumps(
            canonical_envelope,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_hash(self) -> bool:
        """Asserts whether the current sha256_hash matches the computed canonical hash."""
        return self.sha256_hash == self.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the artifact to a standard dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type.value,
            "title": self.title,
            "payload": self.payload,
            "source_node": self.source_node,
            "timestamp": self.timestamp,
            "sha256_hash": self.sha256_hash,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TruthArtifact:
        """Reconstructs a TruthArtifact from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        
        required_fields = ["artifact_id", "artifact_type", "title", "payload"]
        for req in required_fields:
            if req not in data:
                raise KeyError(f"Missing required field '{req}' in artifact data.")

        return cls(
            artifact_id=data["artifact_id"],
            artifact_type=ArtifactType.from_string(data["artifact_type"]),
            title=data["title"],
            payload=data["payload"],
            source_node=data.get("source_node", "Mac_Node"),
            timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            sha256_hash=data.get("sha256_hash", ""),
            tags=list(data.get("tags", [])),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializes the artifact to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> TruthArtifact:
        """Parses a TruthArtifact from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_markdown_frontmatter(self, custom_body: Optional[str] = None) -> str:
        """
        Generates standard Obsidian Markdown with YAML frontmatter and bidirectional Wikilinks.
        """
        # Format tags for YAML
        tags_yaml = ""
        if self.tags:
            tags_yaml = "tags:\n" + "\n".join(f"  - {t}" for t in self.tags)
        else:
            tags_yaml = "tags: []"

        formatted_payload = json.dumps(self.payload, indent=2, sort_keys=True, ensure_ascii=False)

        md_lines = [
            "---",
            f'title: "{self.title}"',
            f'artifact_id: "{self.artifact_id}"',
            f'artifact_type: "{self.artifact_type.value}"',
            f'source_node: "{self.source_node}"',
            f'timestamp: "{self.timestamp}"',
            f'sha256_hash: "{self.sha256_hash}"',
            tags_yaml,
            "---",
            "",
            f"# {self.title}",
            "",
            "## Metadata",
            f"- **Artifact ID**: `{self.artifact_id}`",
            f"- **Artifact Type**: `{self.artifact_type.value}`",
            f"- **Source Node**: `{self.source_node}`",
            f"- **Timestamp**: `{self.timestamp}`",
            f"- **Canonical Hash (SHA-256)**: `{self.sha256_hash}`",
            f"- **Knowledge Links**: [[Index]] | [[CANONICAL_PROJECT_AND_STORAGE_RULE]] | [[{self.artifact_type.value}]]",
            "",
            "## Payload Content",
            "```json",
            formatted_payload,
            "```",
        ]

        if custom_body:
            md_lines.extend(["", "## Discussion & Context", custom_body.strip()])

        return "\n".join(md_lines) + "\n"
```

---

### 2.3 Storage Health Models: `canonical_sync_engine/models/health.py`

#### Responsibilities
- `NodeStorageHealth`: Encapsulates individual node reachability, disk stats (total, used, free, percentage), inode state, latency, and headroom compliance.
- `StorageHealthReport`: Aggregates the overall health state, individual vault statuses, remote node reports, invariant violation messages, and self-healing logs.
- Provide clear `to_dict()`, `from_dict()`, and `summary()` methods for human and machine telemetry consumption.

#### Proposed Implementation Code

```python
"""
canonical_sync_engine.models.health
Data models for mesh node storage metrics and composite storage health reports.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NodeStorageHealth:
    """Storage health and probe telemetry for a single mesh node."""
    node_id: str
    node_name: str
    is_reachable: bool
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_free_percent: float = 0.0
    inode_state: str = "OK"  # "OK", "DEGRADED", "EXHAUSTED", "UNKNOWN"
    latency_ms: float = 0.0
    headroom_ok: bool = True
    error_message: Optional[str] = None
    checked_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    @classmethod
    def create_unreachable(
        cls, node_id: str, node_name: str, error_message: str, latency_ms: float = 0.0
    ) -> NodeStorageHealth:
        """Factory for an unreachable or timed-out mesh node."""
        return cls(
            node_id=node_id,
            node_name=node_name,
            is_reachable=False,
            headroom_ok=False,
            inode_state="UNKNOWN",
            latency_ms=latency_ms,
            error_message=error_message,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "is_reachable": self.is_reachable,
            "disk_total_gb": round(self.disk_total_gb, 2),
            "disk_used_gb": round(self.disk_used_gb, 2),
            "disk_free_gb": round(self.disk_free_gb, 2),
            "disk_free_percent": round(self.disk_free_percent, 2),
            "inode_state": self.inode_state,
            "latency_ms": round(self.latency_ms, 2),
            "headroom_ok": self.headroom_ok,
            "error_message": self.error_message,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeStorageHealth:
        return cls(
            node_id=data["node_id"],
            node_name=data["node_name"],
            is_reachable=bool(data["is_reachable"]),
            disk_total_gb=float(data.get("disk_total_gb", 0.0)),
            disk_used_gb=float(data.get("disk_used_gb", 0.0)),
            disk_free_gb=float(data.get("disk_free_gb", 0.0)),
            disk_free_percent=float(data.get("disk_free_percent", 0.0)),
            inode_state=data.get("inode_state", "OK"),
            latency_ms=float(data.get("latency_ms", 0.0)),
            headroom_ok=bool(data.get("headroom_ok", True)),
            error_message=data.get("error_message"),
            checked_at=data.get("checked_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )


@dataclass
class StorageHealthReport:
    """Comprehensive health assessment across local vaults and remote mesh nodes."""
    is_healthy: bool
    disk_free_gb: float
    headroom_satisfied: bool
    obsidian_healthy: bool
    pyspark_healthy: bool
    git_healthy: bool
    gdrive_healthy: bool
    node_reports: Dict[str, NodeStorageHealth] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    healed_actions: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_healthy": self.is_healthy,
            "disk_free_gb": round(self.disk_free_gb, 2),
            "headroom_satisfied": self.headroom_satisfied,
            "obsidian_healthy": self.obsidian_healthy,
            "pyspark_healthy": self.pyspark_healthy,
            "git_healthy": self.git_healthy,
            "gdrive_healthy": self.gdrive_healthy,
            "node_reports": {k: v.to_dict() for k, v in self.node_reports.items()},
            "violations": list(self.violations),
            "healed_actions": list(self.healed_actions),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StorageHealthReport:
        node_reps = {
            k: NodeStorageHealth.from_dict(v)
            for k, v in data.get("node_reports", {}).items()
        }
        return cls(
            is_healthy=bool(data["is_healthy"]),
            disk_free_gb=float(data.get("disk_free_gb", 0.0)),
            headroom_satisfied=bool(data.get("headroom_satisfied", True)),
            obsidian_healthy=bool(data.get("obsidian_healthy", False)),
            pyspark_healthy=bool(data.get("pyspark_healthy", False)),
            git_healthy=bool(data.get("git_healthy", False)),
            gdrive_healthy=bool(data.get("gdrive_healthy", False)),
            node_reports=node_reps,
            violations=list(data.get("violations", [])),
            healed_actions=list(data.get("healed_actions", [])),
            timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )

    def summary(self) -> str:
        """Formats a human-readable multi-line summary of storage health."""
        status_str = "HEALTHY" if self.is_healthy else "UNHEALTHY"
        headroom_str = "SATISFIED" if self.headroom_satisfied else "VIOLATED"
        lines = [
            f"=== Storage Health Report: {status_str} ===",
            f"Timestamp: {self.timestamp}",
            f"Host Disk Free: {self.disk_free_gb:.2f} GB (Headroom: {headroom_str})",
            "Vault Statuses:",
            f"  - Obsidian Vault: {'HEALTHY' if self.obsidian_healthy else 'DEGRADED'}",
            f"  - PySpark Lake:   {'HEALTHY' if self.pyspark_healthy else 'DEGRADED'}",
            f"  - Git Monorepo:   {'HEALTHY' if self.git_healthy else 'DEGRADED'}",
            f"  - Google Drive:   {'HEALTHY' if self.gdrive_healthy else 'DEGRADED'}",
        ]
        if self.node_reports:
            lines.append(f"Mesh Nodes Probed ({len(self.node_reports)} nodes):")
            for nid, nrep in self.node_reports.items():
                reach_str = "ONLINE" if nrep.is_reachable else "OFFLINE"
                lines.append(
                    f"  - [{nid}] {nrep.node_name}: {reach_str}, Free: {nrep.disk_free_gb:.1f}GB, Latency: {nrep.latency_ms:.1f}ms"
                )
        if self.violations:
            lines.append(f"Violations ({len(self.violations)}):")
            for v in self.violations:
                lines.append(f"  ! {v}")
        if self.healed_actions:
            lines.append(f"Self-Healing Actions ({len(self.healed_actions)}):")
            for h in self.healed_actions:
                lines.append(f"  ✓ {h}")
        return "\n".join(lines)
```

---

### 2.4 Synchronization Result Models: `canonical_sync_engine/models/sync_result.py`

#### Responsibilities
- `VaultSyncResult`: Captures the execution status, written file path, verified SHA-256 hash, byte count, latency, and error message for a single vault.
- `QuadVaultSyncResult`: Aggregates the synchronization results across all 4 targets, computes overall success, and provides properties (`all_vaults_succeeded`, `succeeded_vaults`, `failed_vaults`).

#### Proposed Implementation Code

```python
"""
canonical_sync_engine.models.sync_result
Data models for individual vault and composite quad-vault synchronization results.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from canonical_sync_engine.models.health import StorageHealthReport


@dataclass
class VaultSyncResult:
    """Result of synchronizing an artifact to a single vault destination."""
    vault_name: str  # "pyspark", "obsidian", "git", "gdrive"
    success: bool
    target_path: str
    sha256_hash: str
    error: Optional[str] = None
    bytes_written: int = 0
    latency_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_success(
        cls,
        vault_name: str,
        target_path: str,
        sha256_hash: str,
        bytes_written: int,
        latency_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VaultSyncResult:
        """Factory for a successful vault sync operation."""
        return cls(
            vault_name=vault_name,
            success=True,
            target_path=target_path,
            sha256_hash=sha256_hash,
            bytes_written=bytes_written,
            latency_ms=latency_ms,
            metadata=metadata or {},
        )

    @classmethod
    def create_failure(
        cls,
        vault_name: str,
        target_path: str,
        error: str,
        latency_ms: float = 0.0,
    ) -> VaultSyncResult:
        """Factory for a failed vault sync operation."""
        return cls(
            vault_name=vault_name,
            success=False,
            target_path=target_path,
            sha256_hash="",
            error=error,
            bytes_written=0,
            latency_ms=latency_ms,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_name": self.vault_name,
            "success": self.success,
            "target_path": self.target_path,
            "sha256_hash": self.sha256_hash,
            "error": self.error,
            "bytes_written": self.bytes_written,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VaultSyncResult:
        return cls(
            vault_name=data["vault_name"],
            success=bool(data["success"]),
            target_path=data["target_path"],
            sha256_hash=data.get("sha256_hash", ""),
            error=data.get("error"),
            bytes_written=int(data.get("bytes_written", 0)),
            latency_ms=float(data.get("latency_ms", 0.0)),
            timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class QuadVaultSyncResult:
    """Composite result of synchronizing a TruthArtifact across all four canonical vaults."""
    artifact_id: str
    sha256_hash: str
    success: bool
    vault_results: Dict[str, VaultSyncResult] = field(default_factory=dict)
    health_report: Optional[StorageHealthReport] = None
    errors: List[str] = field(default_factory=list)
    total_bytes_written: int = 0
    total_duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    @property
    def all_vaults_succeeded(self) -> bool:
        """Returns True if all 4 canonical vaults succeeded."""
        expected_vaults = {"pyspark", "obsidian", "git", "gdrive"}
        return (
            expected_vaults.issubset(self.vault_results.keys())
            and all(res.success for res in self.vault_results.values())
        )

    @property
    def succeeded_vaults(self) -> List[str]:
        """List of vault names that synchronized successfully."""
        return [k for k, v in self.vault_results.items() if v.success]

    @property
    def failed_vaults(self) -> List[str]:
        """List of vault names that failed to synchronize."""
        return [k for k, v in self.vault_results.items() if not v.success]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "sha256_hash": self.sha256_hash,
            "success": self.success,
            "all_vaults_succeeded": self.all_vaults_succeeded,
            "succeeded_vaults": self.succeeded_vaults,
            "failed_vaults": self.failed_vaults,
            "vault_results": {k: v.to_dict() for k, v in self.vault_results.items()},
            "health_report": self.health_report.to_dict() if self.health_report else None,
            "errors": list(self.errors),
            "total_bytes_written": self.total_bytes_written,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuadVaultSyncResult:
        v_results = {
            k: VaultSyncResult.from_dict(v)
            for k, v in data.get("vault_results", {}).items()
        }
        h_rep = (
            StorageHealthReport.from_dict(data["health_report"])
            if data.get("health_report")
            else None
        )
        return cls(
            artifact_id=data["artifact_id"],
            sha256_hash=data["sha256_hash"],
            success=bool(data["success"]),
            vault_results=v_results,
            health_report=h_rep,
            errors=list(data.get("errors", [])),
            total_bytes_written=int(data.get("total_bytes_written", 0)),
            total_duration_ms=float(data.get("total_duration_ms", 0.0)),
            timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
```

---

## 3. Unit Test Suite Specification: `tests/unit/test_models.py`

### 3.1 Test Architecture & Methodology
- Framework: `pytest`
- Coverage Scope: 100% of methods, edge cases, deterministic hashing guarantees, format conversions, serialization roundtrips, and adversarial tampering.
- Layout: Co-located in `tests/unit/test_models.py`.

### 3.2 Test Case Specifications (20 Test Cases)

| # | Test Function Name | Tier | Description & Assertions |
|---|---|:---:|---|
| 1 | `test_artifact_type_enum_values` | 1 | Asserts all 6 enum values (`truth_audit`, `ai_debate_consensus`, `architectural_decision`, `telemetry_record`, `lora_pair`, `benchmark_result`) are strings and match exact names. |
| 2 | `test_artifact_type_from_string_coercion` | 1 | Tests case-insensitive resolution (`"TRUTH_AUDIT"`, `"ai_debate_consensus"`), invalid strings raising `ValueError`. |
| 3 | `test_truth_artifact_instantiation_defaults` | 1 | Verifies artifact creation with minimal required fields (`artifact_id`, `artifact_type`, `title`, `payload`), checks auto-computed SHA256 hash and default timestamp. |
| 4 | `test_deterministic_sha256_hash_key_order_invariance` | 1 | Creates two artifacts with identical payloads but randomized key insertion order. Asserts `hash1 == hash2`. |
| 5 | `test_deterministic_sha256_hash_nested_invariance` | 1 | Tests deeply nested dictionaries with different key orders producing identical SHA256 hashes. |
| 6 | `test_truth_artifact_dict_roundtrip` | 1 | Asserts `TruthArtifact.from_dict(artifact.to_dict()) == artifact` and hash parity. |
| 7 | `test_truth_artifact_json_roundtrip` | 1 | Asserts `TruthArtifact.from_json(artifact.to_json()) == artifact`. |
| 8 | `test_truth_artifact_verify_hash_success` | 1 | Validates that `artifact.verify_hash()` returns `True` for unmutated artifact. |
| 9 | `test_truth_artifact_verify_hash_tamper_detection` | 2 | Mutates payload directly without recalculating hash; asserts `artifact.verify_hash()` returns `False`. |
| 10 | `test_truth_artifact_markdown_frontmatter` | 1 | Generates Obsidian markdown; asserts YAML frontmatter tags, headers, payload block, and Wikilinks (`[[Index]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`). |
| 11 | `test_truth_artifact_empty_payload` | 2 | Asserts empty payload `{}` computes valid non-empty SHA256 and serializes cleanly. |
| 12 | `test_truth_artifact_unicode_and_special_chars` | 2 | Tests emojis, non-ASCII characters, math symbols in title, tags, and payload. |
| 13 | `test_truth_artifact_validation_errors` | 2 | Empty `artifact_id`, non-string `title`, or non-dict `payload` raises `ValueError` or `TypeError`. |
| 14 | `test_node_storage_health_factories_and_roundtrip` | 1 | Tests standard instantiation, `create_unreachable()` factory, `to_dict()`, and `from_dict()`. |
| 15 | `test_storage_health_report_summary_and_roundtrip` | 1 | Tests `StorageHealthReport` aggregation, violation logging, self-healing log, and `summary()` text generation. |
| 16 | `test_vault_sync_result_factories_and_roundtrip` | 1 | Tests `create_success()`, `create_failure()`, `to_dict()`, and `from_dict()`. |
| 17 | `test_quad_vault_sync_result_all_success` | 1 | When all 4 vaults succeed, `all_vaults_succeeded` is `True`, `failed_vaults` is `[]`. |
| 18 | `test_quad_vault_sync_result_partial_failure` | 2 | When 1 of 4 vaults fails, `all_vaults_succeeded` is `False`, `failed_vaults` returns `['gdrive']`. |
| 19 | `test_sync_config_defaults_and_env_loading` | 1 | Tests default paths, env variable overrides (`OBSIDIAN_VAULT_PATH`, etc.), and `to_dict()`. |
| 20 | `test_sync_config_for_testing_isolation` | 1 | Verifies that `SyncConfig.for_testing(tmp_path)` creates isolated sandbox directories and sets `env="test"`. |

### 3.3 Proposed Test Implementation Code (`tests/unit/test_models.py`)

```python
"""
tests/unit/test_models.py
Unit and boundary tests for canonical_sync_engine models and configuration.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from canonical_sync_engine.config import SyncConfig, MeshNodeConfig, DEFAULT_MESH_TOPOLOGY
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.health import NodeStorageHealth, StorageHealthReport
from canonical_sync_engine.models.sync_result import VaultSyncResult, QuadVaultSyncResult


# ---------------------------------------------------------------------------
# 1. ArtifactType Tests
# ---------------------------------------------------------------------------

def test_artifact_type_enum_values():
    assert ArtifactType.TRUTH_AUDIT == "truth_audit"
    assert ArtifactType.AI_DEBATE_CONSENSUS == "ai_debate_consensus"
    assert ArtifactType.ARCHITECTURAL_DECISION == "architectural_decision"
    assert ArtifactType.TELEMETRY_RECORD == "telemetry_record"
    assert ArtifactType.LORA_PAIR == "lora_pair"
    assert ArtifactType.BENCHMARK_RESULT == "benchmark_result"


def test_artifact_type_from_string_coercion():
    assert ArtifactType.from_string("truth_audit") == ArtifactType.TRUTH_AUDIT
    assert ArtifactType.from_string("TRUTH_AUDIT") == ArtifactType.TRUTH_AUDIT
    assert ArtifactType.from_string("AI_DEBATE_CONSENSUS") == ArtifactType.AI_DEBATE_CONSENSUS
    assert ArtifactType.from_string(ArtifactType.LORA_PAIR) == ArtifactType.LORA_PAIR

    with pytest.raises(ValueError):
        ArtifactType.from_string("non_existent_type")


# ---------------------------------------------------------------------------
# 2. TruthArtifact Model Tests
# ---------------------------------------------------------------------------

def test_truth_artifact_instantiation_defaults():
    artifact = TruthArtifact(
        artifact_id="art-001",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Test Audit Artifact",
        payload={"status": "verified", "count": 42},
    )
    assert artifact.artifact_id == "art-001"
    assert artifact.source_node == "Mac_Node"
    assert len(artifact.sha256_hash) == 64
    assert artifact.tags == []
    assert artifact.metadata == {}
    assert artifact.timestamp != ""


def test_deterministic_sha256_hash_key_order_invariance():
    payload_a = {"alpha": 1, "beta": 2, "gamma": {"x": 10, "y": 20}}
    payload_b = {"gamma": {"y": 20, "x": 10}, "beta": 2, "alpha": 1}

    art_a = TruthArtifact(
        artifact_id="art-same",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Same Title",
        payload=payload_a,
        source_node="Mac_Node",
        timestamp="2026-08-27T00:00:00Z",
    )
    art_b = TruthArtifact(
        artifact_id="art-same",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Same Title",
        payload=payload_b,
        source_node="Mac_Node",
        timestamp="2026-08-27T00:00:00Z",
    )
    assert art_a.sha256_hash == art_b.sha256_hash


def test_deterministic_sha256_hash_nested_invariance():
    payload_nested_1 = {"a": [1, 2, {"k1": "v1", "k2": "v2"}], "b": 3}
    payload_nested_2 = {"b": 3, "a": [1, 2, {"k2": "v2", "k1": "v1"}]}

    art1 = TruthArtifact("art-1", ArtifactType.LORA_PAIR, "Title", payload_nested_1, timestamp="2026-01-01T00:00:00Z")
    art2 = TruthArtifact("art-1", ArtifactType.LORA_PAIR, "Title", payload_nested_2, timestamp="2026-01-01T00:00:00Z")
    assert art1.sha256_hash == art2.sha256_hash


def test_truth_artifact_dict_roundtrip():
    original = TruthArtifact(
        artifact_id="art-roundtrip",
        artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
        title="Consensus Record",
        payload={"decision": "approved", "consensus_pct": 98.5},
        source_node="Linux_Head_Node",
        tags=["consensus", "debate"],
        metadata={"reviewer": "sentinel"},
    )
    data_dict = original.to_dict()
    reconstructed = TruthArtifact.from_dict(data_dict)

    assert reconstructed.artifact_id == original.artifact_id
    assert reconstructed.artifact_type == original.artifact_type
    assert reconstructed.title == original.title
    assert reconstructed.payload == original.payload
    assert reconstructed.sha256_hash == original.sha256_hash
    assert reconstructed.tags == original.tags
    assert reconstructed.metadata == original.metadata


def test_truth_artifact_json_roundtrip():
    original = TruthArtifact(
        artifact_id="art-json",
        artifact_type=ArtifactType.BENCHMARK_RESULT,
        title="Benchmark 100k",
        payload={"qps": 4500, "latency_p99": 2.1},
        tags=["benchmark"],
    )
    json_str = original.to_json()
    reconstructed = TruthArtifact.from_json(json_str)
    assert reconstructed.artifact_id == original.artifact_id
    assert reconstructed.sha256_hash == original.sha256_hash


def test_truth_artifact_verify_hash_success():
    artifact = TruthArtifact(
        artifact_id="art-verify",
        artifact_type=ArtifactType.TELEMETRY_RECORD,
        title="Telemetry",
        payload={"cpu": 12.5, "ram_gb": 18.2},
    )
    assert artifact.verify_hash() is True


def test_truth_artifact_verify_hash_tamper_detection():
    artifact = TruthArtifact(
        artifact_id="art-tamper",
        artifact_type=ArtifactType.TELEMETRY_RECORD,
        title="Telemetry",
        payload={"cpu": 12.5},
    )
    assert artifact.verify_hash() is True

    # Tamper with payload without updating sha256_hash
    artifact.payload["cpu"] = 99.9
    assert artifact.verify_hash() is False


def test_truth_artifact_markdown_frontmatter():
    artifact = TruthArtifact(
        artifact_id="art-md-001",
        artifact_type=ArtifactType.ARCHITECTURAL_DECISION,
        title="Quad Vault Synchronization Protocol",
        payload={"layer": "quad_vault", "approved": True},
        tags=["architecture", "lauburu"],
    )
    md = artifact.to_markdown_frontmatter(custom_body="Detailed design discussion.")

    assert "---" in md
    assert 'title: "Quad Vault Synchronization Protocol"' in md
    assert 'artifact_id: "art-md-001"' in md
    assert "- architecture" in md
    assert "[[Index]]" in md
    assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in md
    assert "Detailed design discussion." in md


def test_truth_artifact_empty_payload():
    artifact = TruthArtifact(
        artifact_id="art-empty",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Empty Payload Artifact",
        payload={},
    )
    assert len(artifact.sha256_hash) == 64
    assert artifact.verify_hash() is True


def test_truth_artifact_unicode_and_special_chars():
    artifact = TruthArtifact(
        artifact_id="art-unicode-🔥",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Unicode Test 🚀 - 日本語 / Ελληνικά",
        payload={"key_日本語": "値_🚀", "math": "∑(x_i) ≥ 10.0"},
        tags=["emoji_🎯", "tag_π"],
    )
    assert artifact.verify_hash() is True
    reconstructed = TruthArtifact.from_json(artifact.to_json())
    assert reconstructed.title == artifact.title
    assert reconstructed.payload["math"] == "∑(x_i) ≥ 10.0"


def test_truth_artifact_validation_errors():
    with pytest.raises(ValueError):
        TruthArtifact("", ArtifactType.TRUTH_AUDIT, "Title", {})

    with pytest.raises(ValueError):
        TruthArtifact("id-1", ArtifactType.TRUTH_AUDIT, "", {})

    with pytest.raises(TypeError):
        TruthArtifact("id-1", ArtifactType.TRUTH_AUDIT, "Title", "not-a-dict")  # type: ignore


# ---------------------------------------------------------------------------
# 3. Storage Health Model Tests
# ---------------------------------------------------------------------------

def test_node_storage_health_factories_and_roundtrip():
    node_health = NodeStorageHealth(
        node_id="L1",
        node_name="Mac_Node",
        is_reachable=True,
        disk_total_gb=460.0,
        disk_used_gb=355.0,
        disk_free_gb=105.0,
        disk_free_percent=22.8,
        inode_state="OK",
        latency_ms=0.25,
        headroom_ok=True,
    )
    assert node_health.headroom_ok is True
    d = node_health.to_dict()
    reconstructed = NodeStorageHealth.from_dict(d)
    assert reconstructed.node_id == "L1"
    assert reconstructed.disk_free_gb == 105.0

    unreachable = NodeStorageHealth.create_unreachable("L4", "Linux_Tablet", "Connection timed out", 2500.0)
    assert unreachable.is_reachable is False
    assert unreachable.headroom_ok is False
    assert unreachable.error_message == "Connection timed out"


def test_storage_health_report_summary_and_roundtrip():
    node1 = NodeStorageHealth(
        node_id="L1", node_name="Mac_Node", is_reachable=True, disk_free_gb=105.0
    )
    node2 = NodeStorageHealth.create_unreachable("L4", "Linux_Tablet", "Host offline")

    report = StorageHealthReport(
        is_healthy=True,
        disk_free_gb=105.0,
        headroom_satisfied=True,
        obsidian_healthy=True,
        pyspark_healthy=True,
        git_healthy=True,
        gdrive_healthy=True,
        node_reports={"L1": node1, "L4": node2},
        violations=[],
        healed_actions=["Removed stale .git/index.lock"],
    )

    summary = report.summary()
    assert "=== Storage Health Report: HEALTHY ===" in summary
    assert "Removed stale .git/index.lock" in summary
    assert "Mac_Node" in summary

    d = report.to_dict()
    reconstructed = StorageHealthReport.from_dict(d)
    assert reconstructed.is_healthy is True
    assert len(reconstructed.node_reports) == 2
    assert reconstructed.healed_actions == ["Removed stale .git/index.lock"]


# ---------------------------------------------------------------------------
# 4. Sync Result Model Tests
# ---------------------------------------------------------------------------

def test_vault_sync_result_factories_and_roundtrip():
    success_res = VaultSyncResult.create_success(
        vault_name="pyspark",
        target_path="/tmp/datasets/truth_audit.jsonl",
        sha256_hash="abcdef123456",
        bytes_written=1024,
        latency_ms=12.5,
    )
    assert success_res.success is True
    assert success_res.bytes_written == 1024

    d = success_res.to_dict()
    reconstructed = VaultSyncResult.from_dict(d)
    assert reconstructed.vault_name == "pyspark"
    assert reconstructed.success is True

    fail_res = VaultSyncResult.create_failure(
        vault_name="gdrive",
        target_path="/Volumes/Google Drive/My Drive",
        error="Drive volume unmounted",
        latency_ms=5.0,
    )
    assert fail_res.success is False
    assert fail_res.error == "Drive volume unmounted"


def test_quad_vault_sync_result_all_success():
    res_pyspark = VaultSyncResult.create_success("pyspark", "/path/pyspark", "hash1", 500)
    res_obsidian = VaultSyncResult.create_success("obsidian", "/path/obsidian", "hash1", 800)
    res_git = VaultSyncResult.create_success("git", "/path/git", "hash1", 500)
    res_gdrive = VaultSyncResult.create_success("gdrive", "/path/gdrive", "hash1", 500)

    quad_res = QuadVaultSyncResult(
        artifact_id="art-quad-1",
        sha256_hash="hash1",
        success=True,
        vault_results={
            "pyspark": res_pyspark,
            "obsidian": res_obsidian,
            "git": res_git,
            "gdrive": res_gdrive,
        },
        total_bytes_written=2300,
        total_duration_ms=45.2,
    )
    assert quad_res.all_vaults_succeeded is True
    assert set(quad_res.succeeded_vaults) == {"pyspark", "obsidian", "git", "gdrive"}
    assert quad_res.failed_vaults == []

    d = quad_res.to_dict()
    reconstructed = QuadVaultSyncResult.from_dict(d)
    assert reconstructed.all_vaults_succeeded is True
    assert reconstructed.total_bytes_written == 2300


def test_quad_vault_sync_result_partial_failure():
    res_pyspark = VaultSyncResult.create_success("pyspark", "/path/pyspark", "hash1", 500)
    res_obsidian = VaultSyncResult.create_success("obsidian", "/path/obsidian", "hash1", 800)
    res_git = VaultSyncResult.create_success("git", "/path/git", "hash1", 500)
    res_gdrive = VaultSyncResult.create_failure("gdrive", "/path/gdrive", "Permission denied")

    quad_res = QuadVaultSyncResult(
        artifact_id="art-quad-2",
        sha256_hash="hash1",
        success=False,
        vault_results={
            "pyspark": res_pyspark,
            "obsidian": res_obsidian,
            "git": res_git,
            "gdrive": res_gdrive,
        },
        errors=["gdrive: Permission denied"],
    )
    assert quad_res.all_vaults_succeeded is False
    assert quad_res.succeeded_vaults == ["pyspark", "obsidian", "git"]
    assert quad_res.failed_vaults == ["gdrive"]


# ---------------------------------------------------------------------------
# 5. Configuration Model Tests
# ---------------------------------------------------------------------------

def test_sync_config_defaults_and_env_loading(monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/custom_obsidian")
    monkeypatch.setenv("CANONICAL_SYNC_MIN_HEADROOM_GB", "15.5")

    cfg = SyncConfig.from_env()
    assert str(cfg.obsidian_vault_path) == "/tmp/custom_obsidian"
    assert cfg.min_disk_headroom_gb == 15.5
    assert "L1" in cfg.mesh_nodes
    assert cfg.mesh_nodes["L1"].name == "Mac_Node"


def test_sync_config_for_testing_isolation(tmp_path: Path):
    test_cfg = SyncConfig.for_testing(tmp_path)
    assert test_cfg.env == "test"
    assert test_cfg.obsidian_vault_path.is_dir()
    assert test_cfg.pyspark_dataset_path.is_dir()
    assert test_cfg.git_repo_path.is_dir()
    assert test_cfg.gdrive_mount_path.is_dir()
    assert test_cfg.gdrive_fallback_cache_path.is_dir()
    assert test_cfg.min_disk_headroom_gb == 1.0
```

---

## 4. Synthesis & Architectural Invariants

### 4.1 Invariant Table

| Invariant | Specification | Enforcement Mechanism |
|---|---|---|
| **Zero Simulation** | Real disk paths and authentic byte computations only. | `TruthArtifact.compute_hash()` and `tests/unit/test_models.py`. |
| **Deterministic Hashing** | SHA-256 hash must be identical across key permutations. | Recursive key sorting in `json.dumps(..., sort_keys=True)`. |
| **Headroom Threshold** | Disk free headroom must be $\ge 10.0\text{ GB}$ (warn if $< 5.0\text{ GB}$). | `SyncConfig.min_disk_headroom_gb` & `StorageHealthReport.headroom_satisfied`. |
| **Quad-Vault Parity** | Artifact hash in PySpark JSONL == Obsidian Frontmatter == Git JSON == Google Drive file. | `QuadVaultSyncResult.all_vaults_succeeded` and hash assertions. |
| **Hermetic Testing** | Unit/integration tests must never modify user's real Obsidian or Git repositories. | `SyncConfig.for_testing(tmp_path)` fixture. |

---

## 5. Implementer Checklist & Acceptance Criteria for Milestone 1.1

When the implementation agent takes over for M1.1, the following deliverables are ready to be enacted:

1. [ ] Create package layout `src/canonical_sync_engine/` and `src/canonical_sync_engine/models/`.
2. [ ] Implement `src/canonical_sync_engine/config.py` with `MeshNodeConfig` and `SyncConfig`.
3. [ ] Implement `src/canonical_sync_engine/models/artifact.py` with `ArtifactType` and `TruthArtifact`.
4. [ ] Implement `src/canonical_sync_engine/models/health.py` with `NodeStorageHealth` and `StorageHealthReport`.
5. [ ] Implement `src/canonical_sync_engine/models/sync_result.py` with `VaultSyncResult` and `QuadVaultSyncResult`.
6. [ ] Implement `tests/unit/test_models.py` with all 20 unit and boundary test cases.
7. [ ] Run `pytest tests/unit/test_models.py` and ensure 100% pass rate.

