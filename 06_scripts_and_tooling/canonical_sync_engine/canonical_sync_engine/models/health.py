"""
canonical_sync_engine.models.health
Data models for mesh node storage metrics, mesh summary, and composite storage health reports.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class NodeProbeMethod(str, Enum):
    """Network transport and probe method for mesh nodes."""
    LOCAL = "local"
    SSH = "ssh"
    ADB = "adb"
    SOCKET = "socket"

    @classmethod
    def from_string(cls, value: Union[str, NodeProbeMethod]) -> NodeProbeMethod:
        if isinstance(value, cls):
            return value
        val_str = str(value).strip().lower()
        for member in cls:
            if member.value.lower() == val_str:
                return member
        return cls.LOCAL


@dataclass
class NodeStorageHealth:
    """Storage health and probe telemetry for a single mesh node."""
    node_id: str
    node_name: str = ""
    is_reachable: bool = True
    layer: int = 1
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_free_percent: float = 0.0
    inode_state: str = "OK"  # "OK", "DEGRADED", "EXHAUSTED", "UNKNOWN"
    latency_ms: float = 0.0
    headroom_ok: bool = True
    probe_method: NodeProbeMethod = NodeProbeMethod.LOCAL
    endpoint: str = "127.0.0.1"
    mount_point: str = "/"
    error_message: Optional[str] = None
    checked_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    # Aliases for explorer compatibility
    @property
    def name(self) -> str:
        return self.node_name or self.node_id

    @property
    def is_online(self) -> bool:
        return self.is_reachable

    @property
    def storage_healthy(self) -> bool:
        return self.headroom_ok and self.is_reachable

    @property
    def free_disk_gb(self) -> float:
        return self.disk_free_gb

    @property
    def total_disk_gb(self) -> float:
        return self.disk_total_gb

    @property
    def error(self) -> Optional[str]:
        return self.error_message

    @property
    def last_checked(self) -> str:
        return self.checked_at

    def __post_init__(self):
        if not self.node_name:
            self.node_name = self.node_id
        if not isinstance(self.probe_method, NodeProbeMethod):
            self.probe_method = NodeProbeMethod.from_string(self.probe_method)

    @classmethod
    def create_unreachable(
        cls, node_id: str, node_name: str, error_message: str, latency_ms: float = 0.0, layer: int = 0
    ) -> NodeStorageHealth:
        """Factory for an unreachable or timed-out mesh node."""
        return cls(
            node_id=node_id,
            node_name=node_name,
            layer=layer,
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
            "name": self.name,
            "layer": self.layer,
            "is_reachable": self.is_reachable,
            "is_online": self.is_online,
            "storage_healthy": self.storage_healthy,
            "disk_total_gb": round(self.disk_total_gb, 2),
            "disk_used_gb": round(self.disk_used_gb, 2),
            "disk_free_gb": round(self.disk_free_gb, 2),
            "total_disk_gb": round(self.disk_total_gb, 2),
            "free_disk_gb": round(self.disk_free_gb, 2),
            "disk_free_percent": round(self.disk_free_percent, 2),
            "inode_state": self.inode_state,
            "latency_ms": round(self.latency_ms, 2),
            "headroom_ok": self.headroom_ok,
            "probe_method": self.probe_method.value,
            "endpoint": self.endpoint,
            "mount_point": self.mount_point,
            "error_message": self.error_message,
            "error": self.error,
            "checked_at": self.checked_at,
            "last_checked": self.last_checked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeStorageHealth:
        node_id = data["node_id"]
        name = data.get("node_name") or data.get("name", node_id)
        is_reach = bool(data.get("is_reachable", data.get("is_online", True)))
        disk_tot = float(data.get("disk_total_gb", data.get("total_disk_gb", 0.0)))
        disk_fr = float(data.get("disk_free_gb", data.get("free_disk_gb", 0.0)))
        disk_used = float(data.get("disk_used_gb", disk_tot - disk_fr if disk_tot >= disk_fr else 0.0))
        pct_fr = float(data.get("disk_free_percent", (disk_fr / disk_tot * 100.0) if disk_tot > 0 else 0.0))
        head_ok = bool(data.get("headroom_ok", data.get("storage_healthy", True)))
        err = data.get("error_message") or data.get("error")
        probe_meth = NodeProbeMethod.from_string(data.get("probe_method", "local"))
        
        return cls(
            node_id=node_id,
            node_name=name,
            layer=int(data.get("layer", 1)),
            is_reachable=is_reach,
            disk_total_gb=disk_tot,
            disk_used_gb=disk_used,
            disk_free_gb=disk_fr,
            disk_free_percent=pct_fr,
            inode_state=data.get("inode_state", "OK"),
            latency_ms=float(data.get("latency_ms", 0.0)),
            headroom_ok=head_ok,
            probe_method=probe_meth,
            endpoint=data.get("endpoint", "127.0.0.1"),
            mount_point=data.get("mount_point", "/"),
            error_message=err,
            checked_at=data.get("checked_at", data.get("last_checked", datetime.datetime.now(datetime.timezone.utc).isoformat())),
        )


@dataclass
class MeshSummaryReport:
    """Aggregated summary of storage health across the physical mesh."""
    total_nodes: int
    online_nodes: int
    offline_nodes: int
    total_mesh_free_gb: float
    total_mesh_capacity_gb: float
    scan_duration_ms: float
    nodes: Dict[str, NodeStorageHealth] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "online_nodes": self.online_nodes,
            "offline_nodes": self.offline_nodes,
            "total_mesh_free_gb": round(self.total_mesh_free_gb, 2),
            "total_mesh_capacity_gb": round(self.total_mesh_capacity_gb, 2),
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MeshSummaryReport:
        node_reps = {
            k: NodeStorageHealth.from_dict(v)
            for k, v in data.get("nodes", {}).items()
        }
        return cls(
            total_nodes=int(data.get("total_nodes", len(node_reps))),
            online_nodes=int(data.get("online_nodes", sum(1 for n in node_reps.values() if n.is_reachable))),
            offline_nodes=int(data.get("offline_nodes", sum(1 for n in node_reps.values() if not n.is_reachable))),
            total_mesh_free_gb=float(data.get("total_mesh_free_gb", sum(n.disk_free_gb for n in node_reps.values() if n.is_reachable))),
            total_mesh_capacity_gb=float(data.get("total_mesh_capacity_gb", sum(n.disk_total_gb for n in node_reps.values() if n.is_reachable))),
            scan_duration_ms=float(data.get("scan_duration_ms", 0.0)),
            nodes=node_reps,
            timestamp=data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
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
    vault_details: Dict[str, Any] = field(default_factory=dict)
    node_reports: Dict[str, NodeStorageHealth] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    healed_actions: List[str] = field(default_factory=list)
    scan_duration_ms: float = 0.0
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
            "vault_details": self.vault_details,
            "node_reports": {k: v.to_dict() for k, v in self.node_reports.items()},
            "violations": list(self.violations),
            "healed_actions": list(self.healed_actions),
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StorageHealthReport:
        node_reps = {}
        for k, v in data.get("node_reports", {}).items():
            if isinstance(v, dict):
                node_reps[k] = NodeStorageHealth.from_dict(v)
            elif isinstance(v, NodeStorageHealth):
                node_reps[k] = v

        return cls(
            is_healthy=bool(data["is_healthy"]),
            disk_free_gb=float(data.get("disk_free_gb", 0.0)),
            headroom_satisfied=bool(data.get("headroom_satisfied", True)),
            obsidian_healthy=bool(data.get("obsidian_healthy", False)),
            pyspark_healthy=bool(data.get("pyspark_healthy", False)),
            git_healthy=bool(data.get("git_healthy", False)),
            gdrive_healthy=bool(data.get("gdrive_healthy", False)),
            vault_details=dict(data.get("vault_details", {})),
            node_reports=node_reps,
            violations=list(data.get("violations", [])),
            healed_actions=list(data.get("healed_actions", [])),
            scan_duration_ms=float(data.get("scan_duration_ms", 0.0)),
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
