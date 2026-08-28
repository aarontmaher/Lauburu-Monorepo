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
