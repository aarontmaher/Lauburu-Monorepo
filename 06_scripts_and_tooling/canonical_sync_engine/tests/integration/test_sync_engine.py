"""
tests/integration/test_sync_engine.py
Integration tests for CanonicalSyncEngine coordinator, multi-vault synchronization,
atomic rollback, degradation tracking, batch execution, and telemetry audit logging.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import pytest

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.engine.coordinator import CanonicalSyncEngine
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.sync_result import QuadVaultSyncResult, VaultSyncResult
from canonical_sync_engine.sync.base import BaseVaultSyncer
from canonical_sync_engine.verification.self_healer import CANONICAL_INDEX_MD_CONTENT


def test_sync_truth_artifact_e2e_all_vaults_succeed(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Asserts end-to-end synchronization of a single TruthArtifact across all four canonical vaults:
    1. PySpark JSONL Lakehouse
    2. Obsidian Vault Markdown with Wikilinks
    3. Git Monorepo JSON working tree
    4. Google Drive Cloud Mirror / Fallback VFS Cache
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    result: QuadVaultSyncResult = engine.sync_truth_artifact(
        artifact=sample_truth_artifact,
        verify_first=True,
    )

    assert result.success is True
    assert result.all_vaults_succeeded is True
    assert result.artifact_id == sample_truth_artifact.artifact_id
    assert result.sha256_hash == sample_truth_artifact.sha256_hash
    assert result.total_bytes_written > 0
    assert len(result.errors) == 0

    expected_vaults = {"pyspark", "obsidian", "git", "gdrive"}
    assert set(result.succeeded_vaults) == expected_vaults
    assert len(result.failed_vaults) == 0

    # 1. Assert PySpark output
    pyspark_res = result.vault_results["pyspark"]
    assert pyspark_res.success is True
    assert Path(pyspark_res.target_path).exists()
    # Check that master JSONL contains the record
    master_jsonl = mock_vault_sandbox["pyspark"] / "truth_audit_master.jsonl"
    assert master_jsonl.exists()
    lines = master_jsonl.read_text(encoding="utf-8").strip().split("\n")
    pyspark_records = [json.loads(line) for line in lines if line.strip()]
    assert any(r["artifact_id"] == sample_truth_artifact.artifact_id for r in pyspark_records)

    # 2. Assert Obsidian output
    obsidian_res = result.vault_results["obsidian"]
    assert obsidian_res.success is True
    obsidian_file = Path(obsidian_res.target_path)
    assert obsidian_file.exists()
    obs_content = obsidian_file.read_text(encoding="utf-8")
    assert f'artifact_id: "{sample_truth_artifact.artifact_id}"' in obs_content
    assert "[[Index]]" in obs_content
    assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in obs_content

    # 3. Assert Git output
    git_res = result.vault_results["git"]
    assert git_res.success is True
    git_file = Path(git_res.target_path)
    assert git_file.exists()
    git_json = json.loads(git_file.read_text(encoding="utf-8"))
    assert git_json["artifact_id"] == sample_truth_artifact.artifact_id
    assert git_json["sha256_hash"] == sample_truth_artifact.sha256_hash

    # 4. Assert Google Drive output
    gdrive_res = result.vault_results["gdrive"]
    assert gdrive_res.success is True
    gdrive_file = Path(gdrive_res.target_path)
    assert gdrive_file.exists()
    gdrive_json = json.loads(gdrive_file.read_text(encoding="utf-8"))
    assert gdrive_json["artifact_id"] == sample_truth_artifact.artifact_id
    assert gdrive_json["sha256_hash"] == sample_truth_artifact.sha256_hash


def test_sync_truth_artifact_sequential_vs_parallel(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Verifies that sequential and parallel sync execution modes both complete
    with identical cryptographic SHA-256 parity and identical target files.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    # Sequential Sync
    res_seq = engine.sync_truth_artifact(
        artifact=sample_truth_artifact,
        verify_first=False,
        parallel=False,
    )
    assert res_seq.success is True
    assert res_seq.all_vaults_succeeded is True

    # Construct second artifact for parallel sync
    parallel_art = TruthArtifact(
        artifact_id="art-parallel-test",
        artifact_type=ArtifactType.ARCHITECTURAL_DECISION,
        title="Parallel Execution Validation",
        payload={"strategy": "ThreadPoolExecutor", "workers": 4},
    )

    # Parallel Sync
    res_par = engine.sync_truth_artifact(
        artifact=parallel_art,
        verify_first=False,
        parallel=True,
    )
    assert res_par.success is True
    assert res_par.all_vaults_succeeded is True
    assert res_par.sha256_hash == parallel_art.sha256_hash


def test_sync_truth_artifact_with_pre_flight_healing(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Simulates degraded storage:
    - Missing Obsidian Index.md
    - Stale .git/index.lock file (>10m old)
    Asserts pre-flight self-healing restores invariants and sync completes successfully.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config, auto_heal=True)

    # Induce corruption
    index_md = mock_vault_sandbox["obsidian"] / "Index.md"
    if index_md.exists():
        index_md.unlink()

    stale_lock = mock_vault_sandbox["git"] / ".git" / "index.lock"
    stale_lock.write_text("dummy lock content", encoding="utf-8")
    # Backdate mtime by 15 minutes
    old_time = os.path.getmtime(mock_vault_sandbox["base"]) - 900
    os.utime(stale_lock, (old_time, old_time))

    # Sync with verify_first=True
    result = engine.sync_truth_artifact(
        artifact=sample_truth_artifact,
        verify_first=True,
    )

    assert result.success is True
    assert result.all_vaults_succeeded is True
    # Verify Index.md was healed
    assert index_md.exists()
    assert "[[Index]]" in index_md.read_text(encoding="utf-8")
    # Verify stale lock was removed
    assert not stale_lock.exists()


def test_sync_batch_multiple_artifacts(
    mock_vault_sandbox: Dict[str, Path],
):
    """
    Tests batch synchronization of multiple heterogeneous TruthArtifact types.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    artifacts = [
        TruthArtifact(
            artifact_id=f"batch-art-{i}",
            artifact_type=art_type,
            title=f"Batch Artifact {i} - {art_type.value}",
            payload={"item_index": i, "data": f"value_{i}"},
            tags=["batch", art_type.value],
        )
        for i, art_type in enumerate([
            ArtifactType.TRUTH_AUDIT,
            ArtifactType.AI_DEBATE_CONSENSUS,
            ArtifactType.ARCHITECTURAL_DECISION,
            ArtifactType.TELEMETRY_RECORD,
            ArtifactType.LORA_PAIR,
            ArtifactType.BENCHMARK_RESULT,
        ])
    ]

    results = engine.sync_batch(artifacts=artifacts, verify_first=True)

    assert len(results) == len(artifacts)
    for i, res in enumerate(results):
        assert res.success is True
        assert res.all_vaults_succeeded is True
        assert res.artifact_id == artifacts[i].artifact_id
        assert res.sha256_hash == artifacts[i].sha256_hash

        # Verify read from all vaults
        reconstructed = engine.read_from_all_vaults(artifacts[i].artifact_id)
        for v_name in ["pyspark", "obsidian", "git", "gdrive"]:
            art_v = reconstructed[v_name]
            assert art_v is not None
            assert art_v.artifact_id == artifacts[i].artifact_id
            assert art_v.sha256_hash == artifacts[i].sha256_hash


def test_sync_batch_empty_list(mock_vault_sandbox: Dict[str, Path]):
    """Asserts that syncing an empty list returns an empty list without error."""
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)
    results = engine.sync_batch([])
    assert results == []


def test_sync_tampered_artifact_hash_fails_immediately(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Tampering with the artifact's canonical SHA-256 hash must immediately reject
    the sync operation before any storage modification occurs.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    # Tamper with the hash
    sample_truth_artifact.sha256_hash = "bad000000000000000000000000000000000000000000000000000000000dead"

    result = engine.sync_truth_artifact(sample_truth_artifact, verify_first=False)

    assert result.success is False
    assert len(result.errors) > 0
    assert "verification failed" in result.errors[0]
    assert result.total_bytes_written == 0


def test_sync_invalid_artifact_type_error(mock_vault_sandbox: Dict[str, Path]):
    """Asserts TypeError is raised if an invalid artifact object is passed."""
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    with pytest.raises(TypeError, match="Expected TruthArtifact"):
        engine.sync_truth_artifact({"invalid": "dict"})  # type: ignore


class _FailingVaultSyncer(BaseVaultSyncer):
    """Mock syncer that deliberately raises or returns failure for test coverage."""

    def __init__(self, name: str, should_raise: bool = False, config: Optional[SyncConfig] = None):
        super().__init__(config=config)
        self._name = name
        self._should_raise = should_raise

    @property
    def vault_name(self) -> str:
        return self._name

    def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
        if self._should_raise:
            raise PermissionError(f"Simulated permission denied in {self._name}")
        return VaultSyncResult.create_failure(
            vault_name=self._name,
            target_path="/dev/null",
            error=f"Simulated write failure in {self._name}",
        )

    def verify(self, artifact: TruthArtifact) -> bool:
        return False

    def read(self, artifact_id: str) -> Optional[TruthArtifact]:
        return None


def test_degraded_single_vault_failure_and_error_isolation(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Verifies that failure in one vault is isolated, reported in failed_vaults,
    and other healthy vaults are accurately tracked in succeeded_vaults.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    # Replace 'git' syncer with failing mock
    engine.syncers["git"] = _FailingVaultSyncer("git", should_raise=False, config=config)

    result = engine.sync_truth_artifact(sample_truth_artifact, verify_first=False)

    assert result.success is False
    assert result.all_vaults_succeeded is False
    assert "git" in result.failed_vaults
    assert "pyspark" in result.succeeded_vaults
    assert "obsidian" in result.succeeded_vaults
    assert "gdrive" in result.succeeded_vaults
    assert any("[git]" in err for err in result.errors)


def test_degraded_vault_with_exception_in_sync(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Verifies that unhandled exceptions thrown by a vault syncer are cleanly caught
    and converted to a failed VaultSyncResult rather than crashing the engine.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    # Replace 'obsidian' syncer with throwing mock
    engine.syncers["obsidian"] = _FailingVaultSyncer("obsidian", should_raise=True, config=config)

    result = engine.sync_truth_artifact(sample_truth_artifact, verify_first=False)

    assert result.success is False
    assert "obsidian" in result.failed_vaults
    assert "pyspark" in result.succeeded_vaults
    assert any("PermissionError" in err or "permission denied" in err for err in result.errors)


def test_atomic_rollback_on_failure(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Tests that with rollback_on_failure=True, newly written individual files in
    succeeded vaults (e.g. Obsidian markdown, Git JSON) are removed if a critical failure occurs.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    # Make gdrive fail
    engine.syncers["gdrive"] = _FailingVaultSyncer("gdrive", should_raise=False, config=config)

    result = engine.sync_truth_artifact(
        sample_truth_artifact,
        verify_first=False,
        parallel=False,  # Sequential to control write order
        rollback_on_failure=True,
    )

    assert result.success is False
    # Verify rollback was attempted on individual files
    obsidian_note = mock_vault_sandbox["obsidian"] / "notes" / f"{sample_truth_artifact.artifact_id}.md"
    assert not obsidian_note.exists()


def test_verify_all_vaults_and_read_from_all_vaults(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Tests engine.verify_all_vaults() and engine.read_from_all_vaults().
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    # Before sync, verification must be False and read returns None
    v_status_before = engine.verify_all_vaults(sample_truth_artifact)
    assert all(status is False for status in v_status_before.values())

    read_before = engine.read_from_all_vaults(sample_truth_artifact.artifact_id)
    assert all(art is None for art in read_before.values())

    # Perform Sync
    res = engine.sync_truth_artifact(sample_truth_artifact, verify_first=False)
    assert res.success is True

    # After sync, verification must be True
    v_status_after = engine.verify_all_vaults(sample_truth_artifact)
    assert all(status is True for status in v_status_after.values())

    # Read back and assert equality
    read_after = engine.read_from_all_vaults(sample_truth_artifact.artifact_id)
    for v_name, read_art in read_after.items():
        assert read_art is not None, f"Vault '{v_name}' returned None on read."
        assert read_art.artifact_id == sample_truth_artifact.artifact_id
        assert read_art.title == sample_truth_artifact.title
        assert read_art.sha256_hash == sample_truth_artifact.sha256_hash


def test_telemetry_emission_and_audit_log_jsonl(
    mock_vault_sandbox: Dict[str, Path],
    sample_truth_artifact: TruthArtifact,
):
    """
    Asserts telemetry records are captured in-memory and appended to sync_audit_log.jsonl on disk.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    initial_count = len(engine.telemetry_records)
    engine.sync_truth_artifact(sample_truth_artifact, verify_first=False)

    assert len(engine.telemetry_records) == initial_count + 1
    last_event = engine.telemetry_records[-1]
    assert last_event["artifact_id"] == sample_truth_artifact.artifact_id
    assert last_event["success"] is True
    assert last_event["event_type"] == "quad_vault_sync"

    audit_log = config.pyspark_dataset_path / "sync_audit_log.jsonl"
    assert audit_log.exists()
    lines = audit_log.read_text(encoding="utf-8").strip().split("\n")
    logged_records = [json.loads(line) for line in lines if line.strip()]
    assert any(r["artifact_id"] == sample_truth_artifact.artifact_id for r in logged_records)


def test_get_vault_status_reporting(mock_vault_sandbox: Dict[str, Path]):
    """
    Asserts get_vault_status returns valid metadata and path access info for each vault.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    status = engine.get_vault_status()
    assert "pyspark" in status
    assert "obsidian" in status
    assert "git" in status
    assert "gdrive" in status

    assert status["pyspark"]["exists"] is True
    assert status["pyspark"]["writable"] is True
    assert status["obsidian"]["exists"] is True
    assert status["obsidian"]["writable"] is True
    assert status["git"]["exists"] is True
    assert status["git"]["writable"] is True
    assert status["gdrive"]["writable"] is True


def test_fast_path_check_and_verify_storage_health(mock_vault_sandbox: Dict[str, Path]):
    """
    Verifies fast_path_check() and verify_storage_health() on a healthy test environment.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config)

    assert engine.fast_path_check() is True

    health = engine.verify_storage_health(scan_remote_nodes=False, auto_heal=False)
    assert health.is_healthy is True
    assert health.obsidian_healthy is True
    assert health.pyspark_healthy is True
    assert health.git_healthy is True
    assert health.gdrive_healthy is True
    assert health.headroom_satisfied is True


def test_high_concurrency_multi_thread_engine_sync(
    mock_vault_sandbox: Dict[str, Path],
):
    """
    Executes multiple concurrent worker threads synchronizing unique artifacts
    simultaneously through a single shared CanonicalSyncEngine instance.
    """
    config = SyncConfig.for_testing(mock_vault_sandbox["base"])
    engine = CanonicalSyncEngine(config=config, max_workers=4)

    num_threads = 10
    artifacts = [
        TruthArtifact(
            artifact_id=f"art-concurrent-{i}",
            artifact_type=ArtifactType.TRUTH_AUDIT,
            title=f"Concurrent Stress Test Artifact {i}",
            payload={"thread_id": i, "timestamp_ms": i * 100},
        )
        for i in range(num_threads)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(engine.sync_truth_artifact, art, False, True, False)
            for art in artifacts
        ]
        results = [fut.result() for fut in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads
    assert all(res.success is True for res in results)
    assert all(res.all_vaults_succeeded is True for res in results)
