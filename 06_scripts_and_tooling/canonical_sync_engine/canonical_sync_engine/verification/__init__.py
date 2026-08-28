"""
canonical_sync_engine.verification
Storage verification and pre-flight validation module.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from canonical_sync_engine.models.health import (
    MeshSummaryReport,
    NodeProbeMethod,
    NodeStorageHealth,
    StorageHealthReport,
)
from canonical_sync_engine.verification.fast_path import (
    FastPathChecker,
    FastPathResult,
    fast_path_check,
    is_storage_healthy,
)
from canonical_sync_engine.verification.headroom import (
    HeadroomStatus,
    HeadroomValidator,
    check_disk_headroom,
    check_multi_mount_headroom,
)
from canonical_sync_engine.verification.invariants import (
    REQUIRED_OBSIDIAN_WIKILINKS,
    StorageInvariantValidator,
    VaultInvariantResult,
)
from canonical_sync_engine.verification.mesh_scanner import (
    DEFAULT_MESH_TOPOLOGY,
    MeshNodeScanner,
)
from canonical_sync_engine.verification.self_healer import (
    CANONICAL_INDEX_MD_CONTENT,
    PreFlightSelfHealer,
    StorageSelfHealer,
)

logger = logging.getLogger(__name__)


class StorageVerifier:
    """
    Composite verification engine orchestrating fast-path, headroom,
    invariant, self-healing, and mesh node scanning routines.
    """

    def __init__(
        self,
        obsidian_vault_path: Optional[Union[str, Path]] = None,
        pyspark_dataset_path: Optional[Union[str, Path]] = None,
        pyspark_memory_path: Optional[Union[str, Path]] = None,
        git_working_tree_path: Optional[Union[str, Path]] = None,
        gdrive_mount_path: Optional[Union[str, Path]] = None,
        gdrive_fallback_cache_path: Optional[Union[str, Path]] = None,
        min_headroom_gb: float = 10.0,
        mesh_scanner: Optional[MeshNodeScanner] = None,
    ):
        self.obsidian_path = str(Path(obsidian_vault_path or os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"
        )).expanduser().resolve())

        self.pyspark_path = str(Path(pyspark_dataset_path or os.environ.get(
            "PYSPARK_DATASET_PATH",
            "/Users/aaron/DFS_UNIFIED/lora_datasets"
        )).expanduser().resolve())

        self.pyspark_memory_path = str(Path(pyspark_memory_path or os.environ.get(
            "PYSPARK_MEMORY_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory"
        )).expanduser().resolve())

        self.git_path = str(Path(git_working_tree_path or os.environ.get(
            "GIT_REPO_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
        )).expanduser().resolve())

        self.gdrive_path = str(Path(gdrive_mount_path or os.environ.get(
            "GDRIVE_MOUNT_PATH",
            "/Volumes/Google Drive/My Drive/Lauburu_AI_Memory"
        )).expanduser().resolve())

        self.gdrive_cache = str(Path(gdrive_fallback_cache_path or os.environ.get(
            "GDRIVE_FALLBACK_PATH",
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/gdrive_cache"
        )).expanduser().resolve())

        self.min_headroom_gb = min_headroom_gb

        # Sub-validators
        self.fast_checker = FastPathChecker(
            obsidian_path=self.obsidian_path,
            pyspark_path=self.pyspark_path,
            git_path=self.git_path,
            min_free_gb=5.0,
        )
        self.headroom_validator = HeadroomValidator(
            min_headroom_gb=self.min_headroom_gb,
            paths=[self.obsidian_path, self.pyspark_path, self.git_path],
        )
        self.invariant_validator = StorageInvariantValidator(
            obsidian_path=self.obsidian_path,
            pyspark_path=self.pyspark_path,
            pyspark_memory_path=self.pyspark_memory_path,
            git_path=self.git_path,
            gdrive_path=self.gdrive_path,
            gdrive_cache_path=self.gdrive_cache,
            min_headroom_gb=self.min_headroom_gb,
        )
        self.self_healer = StorageSelfHealer(
            obsidian_path=self.obsidian_path,
            pyspark_lora_path=self.pyspark_path,
            pyspark_memory_path=self.pyspark_memory_path,
            git_repo_path=self.git_path,
            gdrive_fallback_path=self.gdrive_cache,
        )
        self.mesh_scanner = mesh_scanner or MeshNodeScanner(min_headroom_gb=self.min_headroom_gb)

    def fast_path_check(self) -> bool:
        """Executes fast-path verification in < 3ms per Rule 6.3."""
        return self.fast_checker.is_healthy()

    def fast_path(self) -> bool:
        """Convenience alias for fast_path_check."""
        return self.fast_path_check()

    def validate_headroom(self) -> Tuple[bool, float, List[str]]:
        """Validates host & target storage headroom (>= min_headroom_gb)."""
        return self.headroom_validator.check()

    def validate_invariants(self) -> Tuple[bool, List[str], Dict[str, bool]]:
        """Validates Rule 6 storage invariants across vaults."""
        return self.invariant_validator.check()

    def pre_flight_self_heal(self) -> List[str]:
        """Executes idempotent pre-flight self-healing per Rule 6.2."""
        return self.self_healer.heal()

    def scan_mesh(self, parallel: bool = True) -> Dict[str, NodeStorageHealth]:
        """Scans active mesh nodes across L1-L7 and Gateway."""
        return self.mesh_scanner.scan_all_nodes(parallel=parallel)

    def full_verification(
        self,
        scan_remote_nodes: bool = True,
        auto_heal: bool = True,
    ) -> StorageHealthReport:
        """
        Performs comprehensive storage health verification.
        """
        t0 = time.time()
        healed_actions: List[str] = []

        if auto_heal:
            healed_actions = self.pre_flight_self_heal()

        # Check Headroom
        headroom_ok, disk_free_gb, headroom_violations = self.headroom_validator.check()

        # Check Invariants
        invariants_ok, invariant_violations, vault_statuses = self.invariant_validator.check()

        # Scan Mesh Nodes
        node_reports: Dict[str, NodeStorageHealth] = {}
        if scan_remote_nodes:
            node_reports = self.scan_mesh(parallel=True)
        else:
            # Local node only
            local_spec = self.mesh_scanner.topology[0] if self.mesh_scanner.topology else {
                "node_id": "L1", "name": "Mac_Node", "probe_method": NodeProbeMethod.LOCAL, "mount_point": "/"
            }
            local_report = self.mesh_scanner.scan_node_by_spec(local_spec)
            node_reports[local_report.node_id] = local_report

        all_violations = headroom_violations + invariant_violations
        overall_healthy = headroom_ok and invariants_ok

        duration_ms = (time.time() - t0) * 1000.0

        return StorageHealthReport(
            is_healthy=overall_healthy,
            disk_free_gb=disk_free_gb,
            headroom_satisfied=headroom_ok,
            obsidian_healthy=vault_statuses.get("obsidian", False),
            pyspark_healthy=vault_statuses.get("pyspark", False),
            git_healthy=vault_statuses.get("git", False),
            gdrive_healthy=vault_statuses.get("gdrive", False),
            vault_details={
                "obsidian": self.invariant_validator.validate_obsidian().to_dict(),
                "pyspark": self.invariant_validator.validate_pyspark().to_dict(),
                "git": self.invariant_validator.validate_git().to_dict(),
                "gdrive": self.invariant_validator.validate_gdrive().to_dict(),
            },
            node_reports=node_reports,
            violations=all_violations,
            healed_actions=healed_actions,
            scan_duration_ms=round(duration_ms, 2),
        )


__all__ = [
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
    "DEFAULT_MESH_TOPOLOGY",
    "MeshNodeScanner",
    "StorageVerifier",
]
