"""
canonical_sync_engine
Distributed storage verification and quad-vault synchronization engine.
"""
from __future__ import annotations

__version__ = "1.0.0"

from canonical_sync_engine.config import (
    DEFAULT_MESH_TOPOLOGY,
    MeshNodeConfig,
    SyncConfig,
)
from canonical_sync_engine.models import (
    ArtifactType,
    MeshSummaryReport,
    NodeProbeMethod,
    NodeStorageHealth,
    QuadVaultSyncResult,
    StorageHealthReport,
    TruthArtifact,
    VaultSyncResult,
)
from canonical_sync_engine.verification import (
    CANONICAL_INDEX_MD_CONTENT,
    FastPathChecker,
    FastPathResult,
    HeadroomStatus,
    HeadroomValidator,
    MeshNodeScanner,
    PreFlightSelfHealer,
    REQUIRED_OBSIDIAN_WIKILINKS,
    StorageInvariantValidator,
    StorageSelfHealer,
    StorageVerifier,
    VaultInvariantResult,
    check_disk_headroom,
    check_multi_mount_headroom,
    fast_path_check,
    is_storage_healthy,
)

__all__ = [
    "__version__",
    "MeshNodeConfig",
    "DEFAULT_MESH_TOPOLOGY",
    "SyncConfig",
    "ArtifactType",
    "TruthArtifact",
    "NodeProbeMethod",
    "NodeStorageHealth",
    "MeshSummaryReport",
    "StorageHealthReport",
    "VaultSyncResult",
    "QuadVaultSyncResult",
    "FastPathResult",
    "FastPathChecker",
    "fast_path_check",
    "is_storage_healthy",
    "HeadroomStatus",
    "HeadroomValidator",
    "check_disk_headroom",
    "check_multi_mount_headroom",
    "REQUIRED_OBSIDIAN_WIKILINKS",
    "VaultInvariantResult",
    "StorageInvariantValidator",
    "CANONICAL_INDEX_MD_CONTENT",
    "StorageSelfHealer",
    "PreFlightSelfHealer",
    "MeshNodeScanner",
    "StorageVerifier",
]
