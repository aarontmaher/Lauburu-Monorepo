"""
canonical_sync_engine.engine.coordinator
CanonicalSyncEngine orchestrating storage health checks, pre-flight self-healing,
and parallel or sequential Quad-Vault synchronization with cryptographic parity.
"""
from __future__ import annotations

import concurrent.futures
import datetime
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.health import StorageHealthReport
from canonical_sync_engine.models.sync_result import (
    QuadVaultSyncResult,
    VaultSyncResult,
)
from canonical_sync_engine.sync.base import BaseVaultSyncer
from canonical_sync_engine.sync.gdrive_syncer import GDriveVaultSyncer
from canonical_sync_engine.sync.git_syncer import GitVaultSyncer
from canonical_sync_engine.sync.obsidian_syncer import ObsidianVaultSyncer
from canonical_sync_engine.sync.pyspark_syncer import PySparkVaultSyncer
from canonical_sync_engine.verification import StorageVerifier

logger = logging.getLogger(__name__)


class CanonicalSyncEngine:
    """
    Master Quad-Vault Synchronization Engine.
    Orchestrates:
      1. Pre-flight self-healing (Rule 6.2) and storage health verification (Rule 6.1/6.3).
      2. Concurrent or sequential propagation across PySpark, Obsidian, Git, and Google Drive.
      3. Cryptographic parity assertion (exact SHA-256 hash match on all destinations).
      4. Degraded vault tracking, atomic rollback capability, and batch sync operations.
      5. Structured telemetry recording and audit log emission.
    """

    def __init__(
        self,
        config: Optional[SyncConfig] = None,
        verifier: Optional[StorageVerifier] = None,
        syncers: Optional[Dict[str, BaseVaultSyncer]] = None,
        max_workers: int = 4,
        auto_heal: bool = True,
        parallel_sync: bool = True,
    ) -> None:
        self.config = config or SyncConfig.from_env()
        self.auto_heal = auto_heal if auto_heal is not None else self.config.auto_heal
        self.parallel_sync = parallel_sync
        self.max_workers = max(1, max_workers)

        # Storage Verifier
        self.verifier = verifier or StorageVerifier(
            obsidian_vault_path=self.config.obsidian_vault_path,
            pyspark_dataset_path=self.config.pyspark_dataset_path,
            pyspark_memory_path=self.config.pyspark_memory_path,
            git_working_tree_path=self.config.git_repo_path,
            gdrive_mount_path=self.config.gdrive_mount_path,
            gdrive_fallback_cache_path=self.config.gdrive_fallback_cache_path,
            min_headroom_gb=self.config.min_disk_headroom_gb,
        )

        # Quad-Vault Sync Adapters
        if syncers is not None:
            self.syncers = dict(syncers)
        else:
            self.syncers = {
                "pyspark": PySparkVaultSyncer(config=self.config),
                "obsidian": ObsidianVaultSyncer(config=self.config),
                "git": GitVaultSyncer(config=self.config),
                "gdrive": GDriveVaultSyncer(config=self.config),
            }

        # Telemetry and audit tracking
        self._telemetry_records: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Health Verification & Self-Healing
    # -------------------------------------------------------------------------

    def fast_path_check(self) -> bool:
        """
        Executes ultra-fast (< 3ms) inode & status verification per Rule 6.3.
        """
        return self.verifier.fast_path_check()

    def pre_flight_self_heal(self) -> List[str]:
        """
        Executes idempotent pre-flight self-healing per Rule 6.2:
        - Auto-creates missing vault directories
        - Clears stale .git/index.lock files (> 10 mins old)
        - Recreates missing or corrupt Obsidian master Index.md
        """
        return self.verifier.pre_flight_self_heal()

    def verify_storage_health(
        self,
        scan_remote_nodes: bool = False,
        auto_heal: Optional[bool] = None,
    ) -> StorageHealthReport:
        """
        Runs comprehensive storage health assessment across all vaults and mesh nodes.
        """
        should_heal = self.auto_heal if auto_heal is None else auto_heal
        return self.verifier.full_verification(
            scan_remote_nodes=scan_remote_nodes,
            auto_heal=should_heal,
        )

    # -------------------------------------------------------------------------
    # Synchronization Pipeline
    # -------------------------------------------------------------------------

    def sync_truth_artifact(
        self,
        artifact: TruthArtifact,
        verify_first: bool = True,
        parallel: Optional[bool] = None,
        rollback_on_failure: bool = False,
    ) -> QuadVaultSyncResult:
        """
        Synchronizes a single TruthArtifact across all four canonical vaults.

        Parameters:
            artifact: The canonical TruthArtifact to synchronize.
            verify_first: If True, executes health check and self-healing prior to sync.
            parallel: If True, uses thread pool for concurrent sync; if False, syncs sequentially.
            rollback_on_failure: If True, attempts to roll back partially written files on failure.

        Returns:
            QuadVaultSyncResult containing per-vault statuses, cryptographic hashes,
            latency, and overall success flag.
        """
        t0 = time.perf_counter()
        errors: List[str] = []
        health_report: Optional[StorageHealthReport] = None

        # 1. Validate artifact integrity and deterministic hash
        if not isinstance(artifact, TruthArtifact):
            raise TypeError(f"Expected TruthArtifact, got {type(artifact).__name__}")

        if not artifact.sha256_hash:
            artifact.sha256_hash = artifact.compute_hash()
        elif not artifact.verify_hash():
            err_msg = (
                f"Artifact hash verification failed for '{artifact.artifact_id}'. "
                f"Provided: {artifact.sha256_hash}, Computed: {artifact.compute_hash()}"
            )
            logger.error(err_msg)
            return QuadVaultSyncResult(
                artifact_id=artifact.artifact_id,
                sha256_hash=artifact.sha256_hash,
                success=False,
                vault_results={},
                health_report=None,
                errors=[err_msg],
                total_bytes_written=0,
                total_duration_ms=(time.perf_counter() - t0) * 1000.0,
            )

        # 2. Pre-flight verification & self-healing
        if verify_first:
            if self.auto_heal:
                healed_actions = self.pre_flight_self_heal()
                if healed_actions:
                    logger.info("Pre-flight self-healing executed: %s", healed_actions)

            health_report = self.verify_storage_health(
                scan_remote_nodes=False,
                auto_heal=False,
            )
            if not health_report.is_healthy:
                logger.warning(
                    "Storage health check reported violations: %s",
                    health_report.violations,
                )
                for v in health_report.violations:
                    errors.append(f"Storage warning: {v}")

        # 3. Determine execution strategy (Parallel vs Sequential)
        use_parallel = self.parallel_sync if parallel is None else parallel
        vault_results: Dict[str, VaultSyncResult] = {}

        if use_parallel and len(self.syncers) > 1:
            vault_results = self._sync_parallel(artifact)
        else:
            vault_results = self._sync_sequential(artifact)

        # 4. Post-Sync Verification & Cryptographic Hash Parity Assertion
        total_bytes = 0
        all_succeeded = True

        for vault_name, syncer in self.syncers.items():
            result = vault_results.get(vault_name)
            if result is None:
                err_str = f"Missing sync result for vault '{vault_name}'."
                errors.append(err_str)
                vault_results[vault_name] = VaultSyncResult.create_failure(
                    vault_name=vault_name,
                    target_path="",
                    error=err_str,
                )
                all_succeeded = False
                continue

            if not result.success:
                all_succeeded = False
                if result.error and result.error not in errors:
                    errors.append(f"[{vault_name}] {result.error}")
                continue

            total_bytes += result.bytes_written

            # Verify cryptographic SHA-256 parity
            if result.sha256_hash.lower() != artifact.sha256_hash.lower():
                err_str = (
                    f"[{vault_name}] SHA-256 hash mismatch. "
                    f"Vault: {result.sha256_hash}, Expected: {artifact.sha256_hash}"
                )
                errors.append(err_str)
                vault_results[vault_name] = VaultSyncResult.create_failure(
                    vault_name=vault_name,
                    target_path=result.target_path,
                    error=err_str,
                    latency_ms=result.latency_ms,
                )
                all_succeeded = False
                continue

            # Secondary direct verification via syncer.verify()
            try:
                if not syncer.verify(artifact):
                    err_str = f"[{vault_name}] Direct verification assertion failed on disk."
                    errors.append(err_str)
                    vault_results[vault_name] = VaultSyncResult.create_failure(
                        vault_name=vault_name,
                        target_path=result.target_path,
                        error=err_str,
                        latency_ms=result.latency_ms,
                    )
                    all_succeeded = False
            except Exception as e:
                err_str = f"[{vault_name}] Verification exception: {str(e)}"
                errors.append(err_str)
                all_succeeded = False

        # 5. Rollback Handling (if requested and partial failure occurred)
        if rollback_on_failure and not all_succeeded:
            self._attempt_rollback(artifact, vault_results)

        total_duration_ms = (time.perf_counter() - t0) * 1000.0

        quad_result = QuadVaultSyncResult(
            artifact_id=artifact.artifact_id,
            sha256_hash=artifact.sha256_hash,
            success=all_succeeded,
            vault_results=vault_results,
            health_report=health_report,
            errors=errors,
            total_bytes_written=total_bytes,
            total_duration_ms=round(total_duration_ms, 2),
        )

        # 6. Audit & Telemetry Emission
        self._record_telemetry(artifact, quad_result)

        return quad_result

    def sync_batch(
        self,
        artifacts: List[TruthArtifact],
        verify_first: bool = True,
        parallel: Optional[bool] = None,
        rollback_on_failure: bool = False,
    ) -> List[QuadVaultSyncResult]:
        """
        Synchronizes a collection of TruthArtifacts in batch.
        Executes pre-flight verification and healing once before processing.
        """
        if not artifacts:
            return []

        # One-time pre-flight check for the entire batch
        if verify_first:
            if self.auto_heal:
                self.pre_flight_self_heal()
            self.verify_storage_health(scan_remote_nodes=False, auto_heal=False)

        results: List[QuadVaultSyncResult] = []
        for artifact in artifacts:
            res = self.sync_truth_artifact(
                artifact=artifact,
                verify_first=False,  # Already verified for batch
                parallel=parallel,
                rollback_on_failure=rollback_on_failure,
            )
            results.append(res)

        return results

    # -------------------------------------------------------------------------
    # Internal Sync Execution Strategies
    # -------------------------------------------------------------------------

    def _sync_single_vault(
        self,
        vault_name: str,
        syncer: BaseVaultSyncer,
        artifact: TruthArtifact,
    ) -> Tuple[str, VaultSyncResult]:
        """Invokes a single vault syncer, catching and wrapping any unexpected error."""
        t_start = time.perf_counter()
        try:
            res = syncer.sync(artifact)
            return vault_name, res
        except Exception as exc:
            lat = (time.perf_counter() - t_start) * 1000.0
            fail_res = VaultSyncResult.create_failure(
                vault_name=vault_name,
                target_path="",
                error=f"Unhandled sync exception: {type(exc).__name__}: {str(exc)}",
                latency_ms=lat,
            )
            return vault_name, fail_res

    def _sync_parallel(self, artifact: TruthArtifact) -> Dict[str, VaultSyncResult]:
        """Concurrently synchronizes across all registered vaults using ThreadPoolExecutor."""
        results: Dict[str, VaultSyncResult] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._sync_single_vault, name, syncer, artifact): name
                for name, syncer in self.syncers.items()
            }
            for fut in concurrent.futures.as_completed(futures):
                try:
                    v_name, v_res = fut.result()
                    results[v_name] = v_res
                except Exception as exc:
                    v_name = futures[fut]
                    results[v_name] = VaultSyncResult.create_failure(
                        vault_name=v_name,
                        target_path="",
                        error=f"Thread execution error: {str(exc)}",
                    )
        return results

    def _sync_sequential(self, artifact: TruthArtifact) -> Dict[str, VaultSyncResult]:
        """Synchronizes across all registered vaults in deterministic sequential order."""
        results: Dict[str, VaultSyncResult] = {}
        # Deterministic order: pyspark -> obsidian -> git -> gdrive
        order = ["pyspark", "obsidian", "git", "gdrive"]
        ordered_keys = [k for k in order if k in self.syncers] + [
            k for k in self.syncers if k not in order
        ]

        for name in ordered_keys:
            syncer = self.syncers[name]
            _, v_res = self._sync_single_vault(name, syncer, artifact)
            results[name] = v_res
        return results

    # -------------------------------------------------------------------------
    # Rollback & Degradation Tracking
    # -------------------------------------------------------------------------

    def _attempt_rollback(
        self,
        artifact: TruthArtifact,
        vault_results: Dict[str, VaultSyncResult],
    ) -> None:
        """
        Attempts best-effort cleanup of artifacts written to vaults that succeeded
        when another critical vault failed.
        """
        logger.warning("Initiating rollback for artifact '%s'", artifact.artifact_id)
        for vault_name, res in vault_results.items():
            if res.success and res.target_path:
                try:
                    target_file = Path(res.target_path)
                    # For individual files (Obsidian, Git, GDrive, PySpark standalone)
                    if target_file.is_file() and not target_file.name.endswith(".jsonl"):
                        target_file.unlink(missing_ok=True)
                        logger.info("Rolled back file: %s", res.target_path)
                except Exception as e:
                    logger.error("Rollback failed for %s: %s", vault_name, e)

    # -------------------------------------------------------------------------
    # Inspection & Read Operations
    # -------------------------------------------------------------------------

    def verify_all_vaults(self, artifact: TruthArtifact) -> Dict[str, bool]:
        """
        Directly checks whether the given artifact exists and is valid across all vaults.
        """
        return {
            name: syncer.verify(artifact)
            for name, syncer in self.syncers.items()
        }

    def read_from_all_vaults(self, artifact_id: str) -> Dict[str, Optional[TruthArtifact]]:
        """
        Reads and reconstructs the artifact from all 4 vaults.
        """
        return {
            name: syncer.read(artifact_id)
            for name, syncer in self.syncers.items()
        }

    def get_vault_status(self) -> Dict[str, Any]:
        """
        Returns an overview of the status, paths, and writeability of each vault.
        """
        status: Dict[str, Any] = {}
        for name, syncer in self.syncers.items():
            info: Dict[str, Any] = {"vault_name": name}
            if name == "pyspark" and isinstance(syncer, PySparkVaultSyncer):
                info["dataset_path"] = str(self.config.pyspark_dataset_path)
                info["master_jsonl"] = str(syncer.master_jsonl_path)
                info["exists"] = self.config.pyspark_dataset_path.exists()
                info["writable"] = os.access(str(self.config.pyspark_dataset_path), os.W_OK) if self.config.pyspark_dataset_path.exists() else False
            elif name == "obsidian" and isinstance(syncer, ObsidianVaultSyncer):
                info["vault_path"] = str(self.config.obsidian_vault_path)
                info["notes_dir"] = str(syncer.notes_dir)
                info["exists"] = self.config.obsidian_vault_path.exists()
                info["writable"] = os.access(str(self.config.obsidian_vault_path), os.W_OK) if self.config.obsidian_vault_path.exists() else False
            elif name == "git" and isinstance(syncer, GitVaultSyncer):
                info["repo_path"] = str(self.config.git_repo_path)
                info["target_dir"] = str(syncer.target_dir)
                info["exists"] = self.config.git_repo_path.exists()
                info["writable"] = os.access(str(self.config.git_repo_path), os.W_OK) if self.config.git_repo_path.exists() else False
            elif name == "gdrive" and isinstance(syncer, GDriveVaultSyncer):
                dest_dir, tier = syncer.resolve_destination()
                dest_dir_check = dest_dir if dest_dir.exists() else dest_dir.parent
                info["mount_path"] = str(self.config.gdrive_mount_path)
                info["fallback_path"] = str(self.config.gdrive_fallback_cache_path)
                info["active_tier"] = tier
                info["active_destination"] = str(dest_dir)
                info["exists"] = dest_dir.exists() or dest_dir.parent.exists()
                info["writable"] = os.access(str(dest_dir_check), os.W_OK) if dest_dir_check.exists() else False
            status[name] = info
        return status

    # -------------------------------------------------------------------------
    # Telemetry & Audit Event Logging
    # -------------------------------------------------------------------------

    def _record_telemetry(
        self,
        artifact: TruthArtifact,
        result: QuadVaultSyncResult,
    ) -> None:
        """
        Emits and stores a structured telemetry and audit record.
        """
        telemetry_entry = {
            "event_type": "quad_vault_sync",
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type.value,
            "title": artifact.title,
            "sha256_hash": artifact.sha256_hash,
            "source_node": artifact.source_node,
            "success": result.success,
            "all_vaults_succeeded": result.all_vaults_succeeded,
            "succeeded_vaults": result.succeeded_vaults,
            "failed_vaults": result.failed_vaults,
            "total_bytes_written": result.total_bytes_written,
            "total_duration_ms": result.total_duration_ms,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        self._telemetry_records.append(telemetry_entry)

        # Write to audit log file in pyspark dataset or memory path
        audit_file = self.config.pyspark_dataset_path / "sync_audit_log.jsonl"
        try:
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            log_line = json.dumps(telemetry_entry, sort_keys=True) + "\n"
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()
        except Exception:
            pass  # Non-fatal telemetry write

    @property
    def telemetry_records(self) -> List[Dict[str, Any]]:
        """Returns the in-memory log of telemetry events."""
        return list(self._telemetry_records)


__all__ = [
    "CanonicalSyncEngine",
    "QuadVaultSyncResult",
    "VaultSyncResult",
]
