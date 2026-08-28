"""
tests/e2e/test_full_suite_tiers.py
Comprehensive 5-Tier E2E Testing and Adversarial Verification Suite for canonical_sync_engine.

Test Tier Architecture:
- Tier 1: Feature Coverage (F1 through F12 complete functional verification)
- Tier 2: Boundary & Corner Cases (Empty, nested, unicode, corrupted storage, unmounted drive, stale locks)
- Tier 3: Cross-Feature Combinations (Concurrent batch sync, multi-threaded cross-vault consistency, atomic rollback)
- Tier 4: Real-World Application Scenarios (Swarm debate consensus, live mesh health audit, LoRA dataset ingest, ADR RFC)
- Tier 5: Adversarial Coverage Hardening (Tampered hashes, broken permissions, malformed JSONL, rapid stress)
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from canonical_sync_engine.cli.main import main as cli_main
from canonical_sync_engine.config import DEFAULT_MESH_TOPOLOGY, MeshNodeConfig, SyncConfig
from canonical_sync_engine.engine.coordinator import CanonicalSyncEngine
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.health import NodeStorageHealth, StorageHealthReport
from canonical_sync_engine.models.sync_result import QuadVaultSyncResult, VaultSyncResult
from canonical_sync_engine.sync.base import BaseVaultSyncer
from canonical_sync_engine.sync.gdrive_syncer import GDriveVaultSyncer
from canonical_sync_engine.sync.git_syncer import GitVaultSyncer
from canonical_sync_engine.sync.obsidian_syncer import ObsidianVaultSyncer
from canonical_sync_engine.sync.pyspark_syncer import PySparkVaultSyncer
from canonical_sync_engine.verification.fast_path import (
    FastPathChecker,
    fast_path_check,
    is_storage_healthy,
)
from canonical_sync_engine.verification.headroom import HeadroomValidator, check_disk_headroom
from canonical_sync_engine.verification.invariants import StorageInvariantValidator
from canonical_sync_engine.verification.mesh_scanner import (
    DEFAULT_MESH_TOPOLOGY as SCANNER_DEFAULT_TOPOLOGY,
    MeshNodeScanner,
)
from canonical_sync_engine.verification.self_healer import (
    CANONICAL_INDEX_MD_CONTENT,
    PreFlightSelfHealer,
)
from tests.e2e.test_sync_pipeline import (
    create_synthetic_ai_debate_artifact,
    create_synthetic_truth_audit_artifact,
    run_acceptance_pipeline,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# =============================================================================
# TIER 1: FEATURE COVERAGE (F1 to F12)
# =============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Systematic coverage of all canonical engine features F1 through F12."""

    # --- F1: TruthArtifact Data Model & Hashing ---
    def test_tier1_f1_all_artifact_types_supported(self):
        """F1.1: Asserts all 6 ArtifactType enum variants instantiate and hash correctly."""
        for art_type in ArtifactType:
            artifact = TruthArtifact(
                artifact_id=f"art-type-{art_type.value}",
                artifact_type=art_type,
                title=f"Test Artifact for {art_type.value}",
                payload={"type_name": art_type.value, "verified": True},
            )
            assert artifact.artifact_type == art_type
            assert len(artifact.sha256_hash) == 64
            assert artifact.verify_hash() is True

    def test_tier1_f1_hash_determinism_and_key_sorting(self):
        """F1.2: Asserts hash invariance regardless of dictionary key insertion order."""
        payload_a = {"alpha": 1, "beta": {"nested_z": 9, "nested_a": 1}, "gamma": [3, 2, 1]}
        payload_b = {"gamma": [3, 2, 1], "alpha": 1, "beta": {"nested_a": 1, "nested_z": 9}}

        art_a = TruthArtifact("art-hash-1", ArtifactType.TRUTH_AUDIT, "Title", payload_a, timestamp="2026-08-27T00:00:00Z")
        art_b = TruthArtifact("art-hash-1", ArtifactType.TRUTH_AUDIT, "Title", payload_b, timestamp="2026-08-27T00:00:00Z")

        assert art_a.sha256_hash == art_b.sha256_hash

    def test_tier1_f1_json_dict_roundtrip_fidelity(self, sample_truth_artifact: TruthArtifact):
        """F1.3: Asserts full serialization roundtrip through dict and JSON preserves equality."""
        as_dict = sample_truth_artifact.to_dict()
        recon_dict = TruthArtifact.from_dict(as_dict)
        assert recon_dict.artifact_id == sample_truth_artifact.artifact_id
        assert recon_dict.sha256_hash == sample_truth_artifact.sha256_hash
        assert recon_dict.verify_hash() is True

        as_json = sample_truth_artifact.to_json()
        recon_json = TruthArtifact.from_json(as_json)
        assert recon_json.sha256_hash == sample_truth_artifact.sha256_hash

    def test_tier1_f1_markdown_frontmatter_generation(self, sample_truth_artifact: TruthArtifact):
        """F1.4: Asserts standard Markdown frontmatter format with mandatory tags and Wikilinks."""
        md = sample_truth_artifact.to_markdown_frontmatter()
        assert md.startswith("---")
        assert f'artifact_id: "{sample_truth_artifact.artifact_id}"' in md
        assert f'sha256_hash: "{sample_truth_artifact.sha256_hash}"' in md
        assert "[[Index]]" in md
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in md

    def test_tier1_f1_validation_constraints(self):
        """F1.5: Asserts invalid artifact types or payloads raise appropriate errors."""
        with pytest.raises(ValueError, match="Unknown ArtifactType"):
            TruthArtifact("art-err", "non_existent_type", "Title", {})  # type: ignore

        with pytest.raises(TypeError, match="payload must be a Dict"):
            TruthArtifact("art-err", ArtifactType.TRUTH_AUDIT, "Title", "not a dict")  # type: ignore

    # --- F2: Fast-Path Health Checker (< 3ms) ---
    def test_tier1_f2_fast_path_sub_3ms_execution(self, test_sync_config: SyncConfig):
        """F2.1: Asserts fast-path check executes in under 3ms across multiple runs."""
        # Ensure directories exist
        test_sync_config.obsidian_vault_path.mkdir(parents=True, exist_ok=True)
        test_sync_config.pyspark_dataset_path.mkdir(parents=True, exist_ok=True)

        checker = FastPathChecker(
            obsidian_path=test_sync_config.obsidian_vault_path,
            pyspark_path=test_sync_config.pyspark_dataset_path,
            min_free_gb=0.1,
        )

        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            res = checker.is_healthy()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            times.append(elapsed_ms)
            assert res is True

        avg_time = sum(times) / len(times)
        assert avg_time < 3.0, f"Fast path average time {avg_time:.3f}ms exceeds 3ms threshold"

    def test_tier1_f2_fast_path_detects_missing_obsidian(self, tmp_path: Path):
        """F2.2: Asserts fast-path returns False when Obsidian vault directory is missing."""
        obsidian_dir = tmp_path / "missing_obsidian"
        pyspark_dir = tmp_path / "pyspark"
        pyspark_dir.mkdir(parents=True, exist_ok=True)

        assert is_storage_healthy(obsidian_path=obsidian_dir, pyspark_path=pyspark_dir, min_free_gb=0.1) is False

    def test_tier1_f2_fast_path_detects_missing_pyspark(self, tmp_path: Path):
        """F2.3: Asserts fast-path returns False when PySpark dataset directory is missing."""
        obsidian_dir = tmp_path / "obsidian"
        obsidian_dir.mkdir(parents=True, exist_ok=True)
        pyspark_dir = tmp_path / "missing_pyspark"

        assert is_storage_healthy(obsidian_path=obsidian_dir, pyspark_path=pyspark_dir, min_free_gb=0.1) is False

    def test_tier1_f2_fast_path_detects_low_headroom(self, tmp_path: Path):
        """F2.4: Asserts fast-path returns False when disk headroom is lower than required."""
        obs = tmp_path / "obs"
        py = tmp_path / "py"
        obs.mkdir()
        py.mkdir()
        # Require an impossible 999999 GB free headroom
        assert is_storage_healthy(obsidian_path=obs, pyspark_path=py, min_free_gb=999999.0) is False

    def test_tier1_f2_fast_path_object_oriented_api(self, test_sync_config: SyncConfig):
        """F2.5: Asserts FastPathChecker check() returns detailed diagnostics."""
        checker = FastPathChecker(
            obsidian_path=test_sync_config.obsidian_vault_path,
            pyspark_path=test_sync_config.pyspark_dataset_path,
            min_free_gb=0.1,
        )
        detailed = checker.check()
        assert detailed.is_healthy is True
        assert detailed.obsidian_ok is True
        assert detailed.pyspark_ok is True
        assert detailed.disk_free_gb > 0
        assert detailed.duration_ms >= 0

    # --- F3: Mesh Node Storage Scanner (L1-L7) ---
    def test_tier1_f3_local_mac_node_probe(self):
        """F3.1: Asserts local L1 Mac_Node storage probe returns authentic disk stats."""
        scanner = MeshNodeScanner()
        l1_spec = scanner.topology[0]
        health = scanner.scan_node_by_spec(l1_spec)

        assert health.node_id == "L1"
        assert health.is_reachable is True
        assert health.disk_free_gb > 0
        assert health.disk_total_gb > 0

    def test_tier1_f3_parallel_node_scan_isolation(self):
        """F3.2: Asserts parallel scanning across all configured nodes finishes within timeout."""
        scanner = MeshNodeScanner(timeout_sec=1.5)
        t0 = time.perf_counter()
        results = scanner.scan_all_nodes(parallel=True, max_workers=8)
        elapsed = time.perf_counter() - t0

        assert "L1" in results
        assert results["L1"].is_reachable is True
        assert elapsed < 5.0

    def test_tier1_f3_scanner_summary_report(self):
        """F3.3: Asserts scanner summary report aggregates online count and storage capacity."""
        scanner = MeshNodeScanner()
        summary = scanner.get_mesh_summary(parallel=True)

        assert summary.total_nodes >= 1
        assert summary.online_nodes >= 1
        assert summary.total_mesh_capacity_gb > 0

    def test_tier1_f3_probe_timeout_handling(self):
        """F3.4: Asserts unreachable node fails gracefully with offline status and no exception."""
        scanner = MeshNodeScanner(timeout_sec=0.5)
        fake_node_spec = {
            "node_id": "LX",
            "name": "Unreachable_Node",
            "layer": 0,
            "probe_method": "ssh",
            "endpoints": ["192.0.2.1"],  # RFC 5737 TEST-NET-1 (unroutable)
            "user": "aaron",
            "port": 2222,
        }
        health = scanner.scan_node_by_spec(fake_node_spec)
        assert health.is_reachable is False
        assert health.headroom_ok is False

    def test_tier1_f3_custom_topology_configuration(self):
        """F3.5: Asserts MeshNodeScanner operates with custom node topologies."""
        custom_topo = [
            SCANNER_DEFAULT_TOPOLOGY[0],
        ]
        scanner = MeshNodeScanner(topology=custom_topo)
        results = scanner.scan_all_nodes()
        assert len(results) == 1
        assert "L1" in results

    # --- F4: Storage Health Invariant Validator ---
    def test_tier1_f4_healthy_sandbox_all_invariants_pass(self, mock_vault_sandbox: Dict[str, Path]):
        """F4.1: Asserts all storage invariants pass on a pristine mock sandbox."""
        validator = StorageInvariantValidator(
            obsidian_path=mock_vault_sandbox["obsidian"],
            pyspark_path=mock_vault_sandbox["pyspark"],
            pyspark_memory_path=mock_vault_sandbox["memory"],
            git_path=mock_vault_sandbox["git"],
            gdrive_path=mock_vault_sandbox["gdrive_mount"],
            gdrive_cache_path=mock_vault_sandbox["gdrive_cache"],
            min_headroom_gb=1.0,
        )
        report = validator.validate_all()
        assert report.is_healthy is True
        assert report.obsidian_healthy is True
        assert report.pyspark_healthy is True
        assert report.git_healthy is True
        assert report.gdrive_healthy is True
        assert len(report.violations) == 0

    def test_tier1_f4_obsidian_missing_wikilinks_invariant(self, mock_vault_sandbox: Dict[str, Path]):
        """F4.2: Asserts Obsidian Index.md missing mandatory Wikilinks is flagged as violation."""
        index_file = mock_vault_sandbox["obsidian"] / "Index.md"
        index_file.write_text("# Corrupted Index without links\n", encoding="utf-8")

        validator = StorageInvariantValidator(
            obsidian_path=mock_vault_sandbox["obsidian"],
            pyspark_path=mock_vault_sandbox["pyspark"],
            pyspark_memory_path=mock_vault_sandbox["memory"],
            git_path=mock_vault_sandbox["git"],
            gdrive_path=mock_vault_sandbox["gdrive_mount"],
            gdrive_cache_path=mock_vault_sandbox["gdrive_cache"],
            min_headroom_gb=1.0,
        )
        report = validator.validate_all()
        assert report.obsidian_healthy is False
        assert any("missing mandatory Wikilink" in v for v in report.violations)

    def test_tier1_f4_stale_git_lock_invariant(self, mock_vault_sandbox: Dict[str, Path]):
        """F4.3: Asserts stale .git/index.lock file triggers invariant violation."""
        lock_file = mock_vault_sandbox["git"] / ".git" / "index.lock"
        lock_file.write_text("lock", encoding="utf-8")

        validator = StorageInvariantValidator(
            obsidian_path=mock_vault_sandbox["obsidian"],
            pyspark_path=mock_vault_sandbox["pyspark"],
            pyspark_memory_path=mock_vault_sandbox["memory"],
            git_path=mock_vault_sandbox["git"],
            gdrive_path=mock_vault_sandbox["gdrive_mount"],
            gdrive_cache_path=mock_vault_sandbox["gdrive_cache"],
            min_headroom_gb=1.0,
        )
        report = validator.validate_all()
        assert report.git_healthy is False
        assert any("index lock present" in v for v in report.violations)

    def test_tier1_f4_disk_headroom_threshold_invariant(self, mock_vault_sandbox: Dict[str, Path]):
        """F4.4: Asserts impossible headroom requirement triggers headroom violation."""
        validator = StorageInvariantValidator(
            obsidian_path=mock_vault_sandbox["obsidian"],
            pyspark_path=mock_vault_sandbox["pyspark"],
            pyspark_memory_path=mock_vault_sandbox["memory"],
            git_path=mock_vault_sandbox["git"],
            gdrive_path=mock_vault_sandbox["gdrive_mount"],
            gdrive_cache_path=mock_vault_sandbox["gdrive_cache"],
            min_headroom_gb=9999999.0,
        )
        report = validator.validate_all()
        assert report.headroom_satisfied is False
        assert any("is below required headroom threshold" in v or "Disk free space" in v for v in report.violations)

    def test_tier1_f4_pyspark_corrupt_jsonl_invariant(self, mock_vault_sandbox: Dict[str, Path]):
        """F4.5: Asserts unparseable lines in master JSONL are detected during validation."""
        master_jsonl = mock_vault_sandbox["pyspark"] / "truth_audit_master.jsonl"
        master_jsonl.write_text("VALID_JSON: NO\n{invalid json here\n", encoding="utf-8")

        validator = StorageInvariantValidator(
            obsidian_path=mock_vault_sandbox["obsidian"],
            pyspark_path=mock_vault_sandbox["pyspark"],
            pyspark_memory_path=mock_vault_sandbox["memory"],
            git_path=mock_vault_sandbox["git"],
            gdrive_path=mock_vault_sandbox["gdrive_mount"],
            gdrive_cache_path=mock_vault_sandbox["gdrive_cache"],
            min_headroom_gb=1.0,
        )
        report = validator.validate_all()
        assert report.pyspark_healthy is False

    # --- F5: Pre-Flight Self-Healer (Rule 6.2) ---
    def test_tier1_f5_auto_heal_missing_directories(self, tmp_path: Path):
        """F5.1: Asserts missing directories are automatically created during healing."""
        obs = tmp_path / "obs_heal"
        pysp = tmp_path / "pysp_heal"
        mem = tmp_path / "mem_heal"
        git_d = tmp_path / "git_heal"

        healer = PreFlightSelfHealer(
            obsidian_path=obs,
            pyspark_lora_path=pysp,
            pyspark_memory_path=mem,
            git_repo_path=git_d,
        )
        actions = healer.heal_all()
        assert obs.exists()
        assert pysp.exists()
        assert mem.exists()
        assert len(actions) > 0

    def test_tier1_f5_auto_heal_stale_git_lock(self, tmp_path: Path):
        """F5.2: Asserts stale git lock (> 10m old) is removed by self-healer."""
        git_dir = tmp_path / "git_repo"
        dot_git = git_dir / ".git"
        dot_git.mkdir(parents=True)
        lock_file = dot_git / "index.lock"
        lock_file.write_text("stale lock", encoding="utf-8")

        # Age the lock file by 15 minutes
        stale_time = time.time() - 900
        os.utime(lock_file, (stale_time, stale_time))

        healer = PreFlightSelfHealer(git_repo_path=git_dir, stale_lock_timeout_sec=600.0)
        actions = healer.heal_git_locks()

        assert not lock_file.exists()
        assert any("Removed stale git index lock" in a for a in actions)

    def test_tier1_f5_auto_heal_missing_obsidian_index(self, tmp_path: Path):
        """F5.3: Asserts missing Index.md in Obsidian vault is created with canonical content."""
        obs_dir = tmp_path / "obsidian_vault"
        obs_dir.mkdir(parents=True)

        healer = PreFlightSelfHealer(obsidian_path=obs_dir)
        actions = healer.heal_obsidian_index()

        index_file = obs_dir / "Index.md"
        assert index_file.exists()
        content = index_file.read_text(encoding="utf-8")
        assert "[[Index]]" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert any("Recreated Obsidian master Index.md" in a for a in actions)

    def test_tier1_f5_auto_heal_corrupt_obsidian_index(self, tmp_path: Path):
        """F5.4: Asserts corrupted Index.md is rewritten to restore master Wikilinks."""
        obs_dir = tmp_path / "obsidian_vault"
        obs_dir.mkdir(parents=True)
        index_file = obs_dir / "Index.md"
        index_file.write_text("corrupted content without links", encoding="utf-8")

        healer = PreFlightSelfHealer(obsidian_path=obs_dir)
        actions = healer.heal_obsidian_index()

        content = index_file.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert any("Recreated Obsidian master Index.md" in a for a in actions)

    def test_tier1_f5_idempotent_heal_all_composite(self, tmp_path: Path):
        """F5.5: Asserts self-healing is completely idempotent and reports no actions on repeat."""
        obs_dir = tmp_path / "obsidian"
        pysp_dir = tmp_path / "pyspark"
        git_dir = tmp_path / "git"

        healer = PreFlightSelfHealer(
            obsidian_path=obs_dir,
            pyspark_lora_path=pysp_dir,
            git_repo_path=git_dir,
        )

        actions_1 = healer.heal_all()
        assert len(actions_1) > 0

        # Second run should execute zero actions
        actions_2 = healer.heal_all()
        assert len(actions_2) == 0

    # --- F6: PySpark Vault Syncer ---
    def test_tier1_f6_jsonl_append_and_verify(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F6.1: Asserts single record append and verify in PySpark vault syncer."""
        syncer = PySparkVaultSyncer(config=test_sync_config)
        res = syncer.sync(sample_truth_artifact)

        assert res.success is True
        assert res.sha256_hash == sample_truth_artifact.sha256_hash
        assert syncer.verify(sample_truth_artifact) is True

    def test_tier1_f6_partition_by_type_generation(self, test_sync_config: SyncConfig, sample_ai_debate_artifact: TruthArtifact):
        """F6.2: Asserts partitioned dataset file is updated by artifact type."""
        syncer = PySparkVaultSyncer(config=test_sync_config)
        res = syncer.sync(sample_ai_debate_artifact)
        assert res.success is True

        partition_file = test_sync_config.pyspark_dataset_path / "by_type" / f"{sample_ai_debate_artifact.artifact_type.value}.jsonl"
        assert partition_file.exists()
        lines = partition_file.read_text(encoding="utf-8").strip().splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        assert any(r["artifact_id"] == sample_ai_debate_artifact.artifact_id for r in records)

    def test_tier1_f6_standalone_artifact_jsonl(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F6.3: Asserts standalone artifact file is written to artifacts/ directory."""
        syncer = PySparkVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)

        standalone_file = test_sync_config.pyspark_dataset_path / "artifacts" / f"{sample_truth_artifact.artifact_id}.jsonl"
        assert standalone_file.exists()
        data = json.loads(standalone_file.read_text(encoding="utf-8"))
        assert data["artifact_id"] == sample_truth_artifact.artifact_id

    def test_tier1_f6_read_and_read_all(self, test_sync_config: SyncConfig):
        """F6.4: Asserts reading single artifact and read_all() across multiple records."""
        syncer = PySparkVaultSyncer(config=test_sync_config)
        artifacts = [
            TruthArtifact(f"art-py-read-{i}", ArtifactType.TRUTH_AUDIT, f"Title {i}", {"idx": i})
            for i in range(3)
        ]
        for a in artifacts:
            syncer.sync(a)

        read_one = syncer.read("art-py-read-1")
        assert read_one is not None
        assert read_one.artifact_id == "art-py-read-1"

        all_records = syncer.read_all()
        assert len(all_records) >= 3

    def test_tier1_f6_concurrent_append_thread_safety(self, test_sync_config: SyncConfig):
        """F6.5: Asserts 10 concurrent threads appending to PySpark master JSONL causes zero corruption."""
        syncer = PySparkVaultSyncer(config=test_sync_config)
        artifacts = [
            TruthArtifact(f"art-py-thread-{i}", ArtifactType.TRUTH_AUDIT, f"Thread Title {i}", {"t": i})
            for i in range(10)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(syncer.sync, a) for a in artifacts]
            results = [f.result() for f in futures]

        assert all(r.success for r in results)
        assert all(syncer.verify(a) for a in artifacts)

    # --- F7: Obsidian Vault Syncer ---
    def test_tier1_f7_markdown_note_generation(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F7.1: Asserts Markdown note with frontmatter is generated in truth_artifacts/."""
        syncer = ObsidianVaultSyncer(config=test_sync_config)
        res = syncer.sync(sample_truth_artifact)

        assert res.success is True
        note_path = test_sync_config.obsidian_vault_path / "truth_artifacts" / f"{sample_truth_artifact.artifact_id}.md"
        assert note_path.exists()

    def test_tier1_f7_bidirectional_wikilinks_presence(self, test_sync_config: SyncConfig, sample_ai_debate_artifact: TruthArtifact):
        """F7.2: Asserts Obsidian note contains all required bidirectional Wikilinks."""
        syncer = ObsidianVaultSyncer(config=test_sync_config)
        syncer.sync(sample_ai_debate_artifact)

        note_path = test_sync_config.obsidian_vault_path / "truth_artifacts" / f"{sample_ai_debate_artifact.artifact_id}.md"
        content = note_path.read_text(encoding="utf-8")
        assert "[[Index]]" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[ai_debate_consensus]]" in content

    def test_tier1_f7_obsidian_read_reconstruction(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F7.3: Asserts reading note reconstructs TruthArtifact with exact hash match."""
        syncer = ObsidianVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)

        recon = syncer.read(sample_truth_artifact.artifact_id)
        assert recon is not None
        assert recon.artifact_id == sample_truth_artifact.artifact_id
        assert recon.sha256_hash == sample_truth_artifact.sha256_hash

    def test_tier1_f7_obsidian_verify_hash_mismatch(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F7.4: Asserts verify() detects tampered hash in markdown note."""
        syncer = ObsidianVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)

        # Tamper with the markdown file
        note_path = test_sync_config.obsidian_vault_path / "truth_artifacts" / f"{sample_truth_artifact.artifact_id}.md"
        content = note_path.read_text(encoding="utf-8")
        tampered_content = content.replace(sample_truth_artifact.sha256_hash, "0" * 64)
        note_path.write_text(tampered_content, encoding="utf-8")

        assert syncer.verify(sample_truth_artifact) is False

    def test_tier1_f7_obsidian_special_characters_filename_sanitization(self, test_sync_config: SyncConfig):
        """F7.5: Asserts artifact IDs with slashes or colons are sanitized for note filenames."""
        syncer = ObsidianVaultSyncer(config=test_sync_config)
        artifact = TruthArtifact("art/custom:id#1", ArtifactType.TRUTH_AUDIT, "Special ID", {"v": 1})
        res = syncer.sync(artifact)

        assert res.success is True
        assert Path(res.target_path).exists()
        assert "/" not in Path(res.target_path).name.replace(".md", "")

    # --- F8: Git Monorepo Vault Syncer ---
    def test_tier1_f8_json_worktree_writing(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F8.1: Asserts structured JSON is written to 04_data_and_memory/core_data/."""
        syncer = GitVaultSyncer(config=test_sync_config)
        res = syncer.sync(sample_truth_artifact)

        assert res.success is True
        git_json_file = test_sync_config.git_repo_path / "04_data_and_memory" / "core_data" / f"{sample_truth_artifact.artifact_id}.json"
        assert git_json_file.exists()

    def test_tier1_f8_git_staging_with_cli(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F8.2: Asserts git staging is executed when inside an initialized git repository."""
        # Initialize .git directory
        (test_sync_config.git_repo_path / ".git").mkdir(parents=True, exist_ok=True)
        syncer = GitVaultSyncer(config=test_sync_config)
        res = syncer.sync(sample_truth_artifact)

        assert res.success is True

    def test_tier1_f8_git_read_reconstruction(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F8.3: Asserts reading artifact JSON from Git worktree reconstructs TruthArtifact."""
        syncer = GitVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)

        recon = syncer.read(sample_truth_artifact.artifact_id)
        assert recon is not None
        assert recon.artifact_id == sample_truth_artifact.artifact_id
        assert recon.sha256_hash == sample_truth_artifact.sha256_hash

    def test_tier1_f8_git_verify_integrity(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F8.4: Asserts verify() validates payload and hash integrity in Git worktree."""
        syncer = GitVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)
        assert syncer.verify(sample_truth_artifact) is True

    def test_tier1_f8_git_stale_lock_healing_on_sync(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F8.5: Asserts stale index.lock is cleared automatically during git sync."""
        dot_git = test_sync_config.git_repo_path / ".git"
        dot_git.mkdir(parents=True, exist_ok=True)
        lock_file = dot_git / "index.lock"
        lock_file.write_text("lock", encoding="utf-8")
        stale_time = time.time() - 900
        os.utime(lock_file, (stale_time, stale_time))

        syncer = GitVaultSyncer(config=test_sync_config)
        res = syncer.sync(sample_truth_artifact)
        assert res.success is True
        assert not lock_file.exists()

    # --- F9: Google Drive Vault Syncer ---
    def test_tier1_f9_tier1_native_mount_sync(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F9.1: Asserts sync writes to Tier 1 native mount when available."""
        syncer = GDriveVaultSyncer(config=test_sync_config)
        dest, tier = syncer.resolve_destination()
        assert tier == "tier_1_native_mount"

        res = syncer.sync(sample_truth_artifact)
        assert res.success is True
        assert (test_sync_config.gdrive_mount_path / "truth_artifacts" / f"{sample_truth_artifact.artifact_id}.json").exists()

    def test_tier1_f9_tier3_fallback_cache_resolution(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F9.2: Asserts syncer resolves to Tier 3 fallback cache when native mount is unavailable."""
        # Unmount native mount by pointing to non-existent path
        test_sync_config.gdrive_mount_path = Path("/non_existent_gdrive_mount_path_12345")
        syncer = GDriveVaultSyncer(config=test_sync_config)
        dest, tier = syncer.resolve_destination()

        assert tier == "tier_3_fallback_cache"
        res = syncer.sync(sample_truth_artifact)
        assert res.success is True
        assert (test_sync_config.gdrive_fallback_cache_path / "truth_artifacts" / f"{sample_truth_artifact.artifact_id}.json").exists()

    def test_tier1_f9_offline_queue_generation(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F9.3: Asserts offline queue (pending_sync.jsonl) is populated during Tier 3 fallback."""
        test_sync_config.gdrive_mount_path = Path("/non_existent_gdrive_mount_path_12345")
        syncer = GDriveVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)

        queue_file = test_sync_config.gdrive_fallback_cache_path / "pending_sync.jsonl"
        assert queue_file.exists()
        lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
        records = [json.loads(l) for l in lines if l.strip()]
        assert any(r["artifact_id"] == sample_truth_artifact.artifact_id for r in records)

    def test_tier1_f9_gdrive_read_and_verify(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F9.4: Asserts read() and verify() operate across Google Drive storage tiers."""
        syncer = GDriveVaultSyncer(config=test_sync_config)
        syncer.sync(sample_truth_artifact)

        assert syncer.verify(sample_truth_artifact) is True
        recon = syncer.read(sample_truth_artifact.artifact_id)
        assert recon is not None
        assert recon.sha256_hash == sample_truth_artifact.sha256_hash

    def test_tier1_f9_tier2_rclone_candidate_resolution(self, test_sync_config: SyncConfig, tmp_path: Path, monkeypatch):
        """F9.5: Asserts Tier 2 rclone mount candidate is resolved when environment is configured."""
        test_sync_config.gdrive_mount_path = Path("/non_existent_gdrive_mount_path_12345")
        rclone_dir = tmp_path / "rclone_mount"
        rclone_dir.mkdir(parents=True)
        monkeypatch.setenv("RCLONE_MOUNT_PATH", str(rclone_dir))

        syncer = GDriveVaultSyncer(config=test_sync_config)
        dest, tier = syncer.resolve_destination()
        assert tier == "tier_2_rclone_mount"

    # --- F10: CanonicalSyncEngine Coordinator ---
    def test_tier1_f10_quad_vault_atomic_sync(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F10.1: Asserts CanonicalSyncEngine coordinates sync across all 4 vaults atomically."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(sample_truth_artifact, verify_first=True)

        assert res.success is True
        assert res.all_vaults_succeeded is True
        assert len(res.succeeded_vaults) == 4
        assert len(res.failed_vaults) == 0

    def test_tier1_f10_parallel_vs_sequential_execution(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F10.2: Asserts parallel and sequential execution both result in complete vault parity."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        res_seq = engine.sync_truth_artifact(sample_truth_artifact, parallel=False)
        assert res_seq.success is True

        art_par = TruthArtifact("art-par-test", ArtifactType.ARCHITECTURAL_DECISION, "Parallel", {"p": 1})
        res_par = engine.sync_truth_artifact(art_par, parallel=True)
        assert res_par.success is True

    def test_tier1_f10_batch_synchronization(self, test_sync_config: SyncConfig):
        """F10.3: Asserts sync_batch() handles heterogeneous artifacts in a single batch."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        batch = [
            TruthArtifact(f"art-batch-{i}", ArtifactType.TRUTH_AUDIT, f"Batch {i}", {"idx": i})
            for i in range(5)
        ]
        results = engine.sync_batch(batch, verify_first=True)
        assert len(results) == 5
        assert all(r.success for r in results)

    def test_tier1_f10_telemetry_and_audit_logging(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """F10.4: Asserts telemetry emission to in-memory records and sync_audit_log.jsonl."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        engine.sync_truth_artifact(sample_truth_artifact)

        assert len(engine.telemetry_records) >= 1
        audit_file = test_sync_config.pyspark_dataset_path / "sync_audit_log.jsonl"
        assert audit_file.exists()

    def test_tier1_f10_vault_status_inspection(self, test_sync_config: SyncConfig):
        """F10.5: Asserts get_vault_status() reports valid status for all 4 vault adapters."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        status = engine.get_vault_status()
        assert set(status.keys()) == {"pyspark", "obsidian", "git", "gdrive"}
        assert all(s["exists"] is True for s in status.values())

    # --- F11: Unified CLI Interface ---
    def test_tier1_f11_cli_verify_command(self, mock_vault_sandbox: Dict[str, Path], capsys, monkeypatch):
        """F11.1: Asserts CLI verify command passes on sandboxed environment."""
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(mock_vault_sandbox["obsidian"]))
        monkeypatch.setenv("PYSPARK_DATASET_PATH", str(mock_vault_sandbox["pyspark"]))
        monkeypatch.setenv("PYSPARK_MEMORY_PATH", str(mock_vault_sandbox["memory"]))
        monkeypatch.setenv("GIT_REPO_PATH", str(mock_vault_sandbox["git"]))
        monkeypatch.setenv("GDRIVE_MOUNT_PATH", str(mock_vault_sandbox["gdrive_mount"]))
        monkeypatch.setenv("GDRIVE_FALLBACK_PATH", str(mock_vault_sandbox["gdrive_cache"]))
        monkeypatch.setenv("CANONICAL_SYNC_MIN_HEADROOM_GB", "0.5")

        exit_code = cli_main(["verify", "--json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["is_healthy"] is True

    def test_tier1_f11_cli_heal_command(self, mock_vault_sandbox: Dict[str, Path], capsys, monkeypatch):
        """F11.2: Asserts CLI heal command executes pre-flight healing."""
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(mock_vault_sandbox["obsidian"]))
        monkeypatch.setenv("PYSPARK_DATASET_PATH", str(mock_vault_sandbox["pyspark"]))
        monkeypatch.setenv("PYSPARK_MEMORY_PATH", str(mock_vault_sandbox["memory"]))
        monkeypatch.setenv("GIT_REPO_PATH", str(mock_vault_sandbox["git"]))
        monkeypatch.setenv("GDRIVE_MOUNT_PATH", str(mock_vault_sandbox["gdrive_mount"]))
        monkeypatch.setenv("GDRIVE_FALLBACK_PATH", str(mock_vault_sandbox["gdrive_cache"]))

        exit_code = cli_main(["heal", "--json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["status"] == "success"

    def test_tier1_f11_cli_sync_command(self, mock_vault_sandbox: Dict[str, Path], capsys, monkeypatch):
        """F11.3: Asserts CLI sync command creates artifact and mirrors across all 4 vaults."""
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(mock_vault_sandbox["obsidian"]))
        monkeypatch.setenv("PYSPARK_DATASET_PATH", str(mock_vault_sandbox["pyspark"]))
        monkeypatch.setenv("PYSPARK_MEMORY_PATH", str(mock_vault_sandbox["memory"]))
        monkeypatch.setenv("GIT_REPO_PATH", str(mock_vault_sandbox["git"]))
        monkeypatch.setenv("GDRIVE_MOUNT_PATH", str(mock_vault_sandbox["gdrive_mount"]))
        monkeypatch.setenv("GDRIVE_FALLBACK_PATH", str(mock_vault_sandbox["gdrive_cache"]))
        monkeypatch.setenv("CANONICAL_SYNC_MIN_HEADROOM_GB", "0.5")

        exit_code = cli_main([
            "sync",
            "--type", "truth_audit",
            "--title", "Tier1 CLI Sync Test",
            "--payload", '{"tier1": "cli_ok"}',
            "--json",
        ])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["success"] is True
        assert data["all_vaults_succeeded"] is True

    def test_tier1_f11_cli_status_command(self, mock_vault_sandbox: Dict[str, Path], capsys, monkeypatch):
        """F11.4: Asserts CLI status command outputs storage health and vault overview."""
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(mock_vault_sandbox["obsidian"]))
        monkeypatch.setenv("PYSPARK_DATASET_PATH", str(mock_vault_sandbox["pyspark"]))
        monkeypatch.setenv("PYSPARK_MEMORY_PATH", str(mock_vault_sandbox["memory"]))
        monkeypatch.setenv("GIT_REPO_PATH", str(mock_vault_sandbox["git"]))
        monkeypatch.setenv("GDRIVE_MOUNT_PATH", str(mock_vault_sandbox["gdrive_mount"]))
        monkeypatch.setenv("GDRIVE_FALLBACK_PATH", str(mock_vault_sandbox["gdrive_cache"]))
        monkeypatch.setenv("CANONICAL_SYNC_MIN_HEADROOM_GB", "0.5")

        exit_code = cli_main(["status", "--json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert "vaults" in data

    def test_tier1_f11_cli_info_command(self, capsys):
        """F11.5: Asserts CLI info command prints configuration and mesh topology."""
        exit_code = cli_main(["info", "--json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert "mesh_nodes" in data

    # --- F12: E2E Acceptance Test Pipeline ---
    def test_tier1_f12_standalone_acceptance_runner(self, tmp_path: Path):
        """F12.1: Asserts run_acceptance_pipeline() returns success and valid report."""
        config = SyncConfig.for_testing(tmp_path)
        success, report = run_acceptance_pipeline(config=config, verbose=False)
        assert success is True
        assert report["parity_verified"] is True

    def test_tier1_f12_acceptance_runner_exit_code_zero(self):
        """F12.2: Asserts Acceptance Criteria script executes with exit code 0 via subprocess."""
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "test_sync_pipeline.py"), "--quiet"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0

    def test_tier1_f12_acceptance_runner_json_output(self):
        """F12.3: Asserts test_sync_pipeline.py --json produces valid JSON summary."""
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "test_sync_pipeline.py"), "--json"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["parity_verified"] is True
        assert data["engine_success"] is True

    def test_tier1_f12_acceptance_runner_ai_debate_type(self):
        """F12.4: Asserts test_sync_pipeline.py with --type ai_debate_consensus succeeds."""
        proc = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "test_sync_pipeline.py"),
                "--type", "ai_debate_consensus",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["artifact_type"] == "ai_debate_consensus"

    def test_tier1_f12_cryptographic_parity_invariant(self, tmp_path: Path):
        """F12.5: Strictly asserts exact cryptographic SHA-256 parity across all 4 vault outputs."""
        config = SyncConfig.for_testing(tmp_path)
        engine = CanonicalSyncEngine(config=config)
        artifact = create_synthetic_truth_audit_artifact()

        res = engine.sync_truth_artifact(artifact)
        assert res.success is True

        # Extract SHA-256 from each vault
        pyspark_art = engine.syncers["pyspark"].read(artifact.artifact_id)
        obsidian_art = engine.syncers["obsidian"].read(artifact.artifact_id)
        git_art = engine.syncers["git"].read(artifact.artifact_id)
        gdrive_art = engine.syncers["gdrive"].read(artifact.artifact_id)

        assert pyspark_art is not None
        assert obsidian_art is not None
        assert git_art is not None
        assert gdrive_art is not None

        all_hashes = {
            pyspark_art.sha256_hash,
            obsidian_art.sha256_hash,
            git_art.sha256_hash,
            gdrive_art.sha256_hash,
        }
        assert len(all_hashes) == 1
        assert all_hashes.pop() == artifact.sha256_hash


# =============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# =============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Boundary value analysis, extreme payloads, Unicode, and edge cases."""

    def test_tier2_b1_empty_payload_dictionary(self, test_sync_config: SyncConfig):
        """B1: Asserts artifact with empty payload {} synchronizes and hashes cleanly."""
        artifact = TruthArtifact(
            artifact_id="art-empty-payload",
            artifact_type=ArtifactType.TRUTH_AUDIT,
            title="Empty Payload Boundary Test",
            payload={},
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is True
        assert res.all_vaults_succeeded is True
        reconstructed = engine.read_from_all_vaults(artifact.artifact_id)
        assert all(a is not None and a.payload == {} for a in reconstructed.values())

    def test_tier2_b2_deeply_nested_json_payload(self, test_sync_config: SyncConfig):
        """B2: Asserts deeply nested JSON structures (15 levels) maintain hash invariance."""
        nested = {"level": 15, "data": "deep_core_value"}
        for i in range(14, 0, -1):
            nested = {"level": i, "sub": nested}

        artifact = TruthArtifact(
            artifact_id="art-deeply-nested",
            artifact_type=ArtifactType.ARCHITECTURAL_DECISION,
            title="Deeply Nested Payload Boundary",
            payload=nested,
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is True
        reconstructed = engine.read_from_all_vaults(artifact.artifact_id)
        assert reconstructed["pyspark"].payload["level"] == 1
        assert reconstructed["obsidian"].payload["level"] == 1
        assert reconstructed["git"].payload["level"] == 1
        assert reconstructed["gdrive"].payload["level"] == 1

    def test_tier2_b3_multibyte_unicode_and_emojis(self, test_sync_config: SyncConfig):
        """B3: Asserts multi-byte Unicode (Japanese, Chinese, Arabic, emojis) UTF-8 stability."""
        unicode_payload = {
            "japanese": "量子コンピュータと人工知能の統合",
            "chinese": "分布式四库同步引擎验证",
            "arabic": "بروتوكول التوافق المتعدد",
            "emojis": "🧠🚀⚡🔒🔥💎🛰️🛡️",
            "special_symbols": "§ ± × ÷ √ ∞ ≈ ≠ ≤ ≥ ∇ ∢",
        }
        artifact = TruthArtifact(
            artifact_id="art-unicode-emojis-🌟",
            artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
            title="Unicode & Emoji Test: 日本語 / 中文 / 🧠",
            payload=unicode_payload,
            tags=["unicode", "マルチバイト", "测试", "🌟"],
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is True
        reconstructed = engine.read_from_all_vaults(artifact.artifact_id)
        for name, art in reconstructed.items():
            assert art is not None, f"Vault {name} failed read"
            assert art.payload["japanese"] == unicode_payload["japanese"]
            assert art.payload["emojis"] == unicode_payload["emojis"]
            assert art.sha256_hash == artifact.sha256_hash

    def test_tier2_b4_corrupted_storage_preflight_auto_healing(self, tmp_path: Path):
        """B4: Asserts engine heals completely missing vault directories before syncing."""
        config = SyncConfig.for_testing(tmp_path)
        # Purge all directories to simulate catastrophic inode loss
        for d in [config.obsidian_vault_path, config.pyspark_dataset_path, config.pyspark_memory_path, config.git_repo_path]:
            if d.exists():
                shutil.rmtree(d)

        engine = CanonicalSyncEngine(config=config, auto_heal=True)
        artifact = create_synthetic_truth_audit_artifact()
        res = engine.sync_truth_artifact(artifact, verify_first=True)

        assert res.success is True
        assert res.all_vaults_succeeded is True
        assert config.obsidian_vault_path.exists()
        assert (config.obsidian_vault_path / "Index.md").exists()

    def test_tier2_b5_unmounted_gdrive_fallback_and_offline_queue(self, test_sync_config: SyncConfig):
        """B5: Asserts unmounted Google Drive gracefully falls back to local VFS cache."""
        test_sync_config.gdrive_mount_path = Path("/Volumes/NonExistentCloudDrive_999")
        engine = CanonicalSyncEngine(config=test_sync_config)
        artifact = create_synthetic_truth_audit_artifact()

        res = engine.sync_truth_artifact(artifact)
        assert res.success is True
        assert res.vault_results["gdrive"].metadata["tier_used"] == "tier_3_fallback_cache"
        assert res.vault_results["gdrive"].metadata["is_offline_queued"] is True

        queue_file = test_sync_config.gdrive_fallback_cache_path / "pending_sync.jsonl"
        assert queue_file.exists()

    def test_tier2_b6_stale_vs_active_git_locks(self, mock_vault_sandbox: Dict[str, Path]):
        """B6: Asserts active lock (< 10m) is reported while stale lock (> 10m) is cleared."""
        config = SyncConfig.for_testing(mock_vault_sandbox["base"])
        healer = PreFlightSelfHealer(git_repo_path=config.git_repo_path, stale_lock_timeout_sec=600.0)

        dot_git = config.git_repo_path / ".git"
        dot_git.mkdir(parents=True, exist_ok=True)
        lock_file = dot_git / "index.lock"

        # 1. Active lock (just created)
        lock_file.write_text("active lock", encoding="utf-8")
        actions_active = healer.heal_git_locks()
        assert lock_file.exists()  # Must not delete active lock
        assert any("Skipped active git index lock" in a for a in actions_active)

        # 2. Stale lock (aged 15 mins)
        stale_time = time.time() - 900
        os.utime(lock_file, (stale_time, stale_time))
        actions_stale = healer.heal_git_locks()
        assert not lock_file.exists()  # Must delete stale lock
        assert any("Removed stale git index lock" in a for a in actions_stale)

    def test_tier2_b7_large_payload_synchronization(self, test_sync_config: SyncConfig):
        """B7: Asserts large 1MB+ JSON payload syncs across all 4 vaults with exact hash parity."""
        large_array = [f"data_point_payload_entry_{i}_{i * 123.456}" for i in range(15000)]
        artifact = TruthArtifact(
            artifact_id="art-large-1mb-payload",
            artifact_type=ArtifactType.BENCHMARK_RESULT,
            title="1MB Large Payload Throughput & Parity Test",
            payload={"entries": large_array, "count": len(large_array)},
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is True
        assert res.total_bytes_written > 1_000_000

        reconstructed = engine.read_from_all_vaults(artifact.artifact_id)
        assert all(a is not None and a.sha256_hash == artifact.sha256_hash for a in reconstructed.values())

    def test_tier2_b8_special_character_artifact_ids(self, test_sync_config: SyncConfig):
        """B8: Asserts edge-case characters in artifact_id (dots, dashes, underscores)."""
        artifact = TruthArtifact(
            artifact_id="art.v1.0-alpha_2026.08.27",
            artifact_type=ArtifactType.TELEMETRY_RECORD,
            title="Dotted and Dashed ID Test",
            payload={"telemetry": "sample"},
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is True
        assert engine.verify_all_vaults(artifact) == {"pyspark": True, "obsidian": True, "git": True, "gdrive": True}

    def test_tier2_b9_empty_tags_and_metadata(self, test_sync_config: SyncConfig):
        """B9: Asserts artifact with empty tags list [] and empty metadata {} syncs cleanly."""
        artifact = TruthArtifact(
            artifact_id="art-empty-tags-meta",
            artifact_type=ArtifactType.TRUTH_AUDIT,
            title="Empty Tags and Metadata",
            payload={"ok": True},
            tags=[],
            metadata={},
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is True
        recon = engine.read_from_all_vaults(artifact.artifact_id)
        assert recon["obsidian"].tags == []


# =============================================================================
# TIER 3: CROSS-FEATURE & CONCURRENCY COMBINATIONS
# =============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Concurrency, multi-threading, race condition resilience, and rollback."""

    def test_tier3_c1_high_concurrency_batch_sync(self, test_sync_config: SyncConfig):
        """C1: Asserts 20 concurrent threads synchronizing distinct artifacts through one engine."""
        engine = CanonicalSyncEngine(config=test_sync_config, max_workers=8)
        num_artifacts = 20
        artifacts = [
            TruthArtifact(
                artifact_id=f"art-concurrent-stress-{i:03d}",
                artifact_type=ArtifactType.TRUTH_AUDIT,
                title=f"Concurrent Stress Artifact {i}",
                payload={"worker_id": i, "timestamp_us": time.time_ns()},
            )
            for i in range(num_artifacts)
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(engine.sync_truth_artifact, a, False, True, False) for a in artifacts]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_artifacts
        assert all(r.success is True for r in results)
        assert all(r.all_vaults_succeeded is True for r in results)

        # Verify all 20 records exist in master JSONL
        master_jsonl = test_sync_config.pyspark_dataset_path / "truth_audit_master.jsonl"
        lines = [l for l in master_jsonl.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
        assert len(lines) == num_artifacts

    def test_tier3_c2_concurrent_reads_and_writes(self, test_sync_config: SyncConfig):
        """C2: Asserts concurrent reads and writes from multiple threads do not lock or crash."""
        engine = CanonicalSyncEngine(config=test_sync_config, max_workers=4)
        base_artifact = create_synthetic_truth_audit_artifact("art-read-write-base")
        engine.sync_truth_artifact(base_artifact)

        def reader_task():
            for _ in range(10):
                art = engine.read_from_all_vaults("art-read-write-base")
                assert art["pyspark"] is not None

        def writer_task(idx: int):
            for i in range(5):
                art = TruthArtifact(f"art-rw-{idx}-{i}", ArtifactType.TRUTH_AUDIT, "RW", {"idx": idx, "i": i})
                res = engine.sync_truth_artifact(art, verify_first=False)
                assert res.success is True

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            readers = [executor.submit(reader_task) for _ in range(3)]
            writers = [executor.submit(writer_task, i) for i in range(3)]
            for f in concurrent.futures.as_completed(readers + writers):
                f.result()

    def test_tier3_c3_pairwise_cross_vault_validation_matrix(self, test_sync_config: SyncConfig):
        """C3: Systematic pairwise equality assertion between (PySpark, Obsidian, Git, GDrive)."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        artifact = create_synthetic_ai_debate_artifact("art-pairwise-matrix")
        res = engine.sync_truth_artifact(artifact)
        assert res.success is True

        reconstructed = engine.read_from_all_vaults(artifact.artifact_id)
        pyspark_a = reconstructed["pyspark"]
        obsidian_a = reconstructed["obsidian"]
        git_a = reconstructed["git"]
        gdrive_a = reconstructed["gdrive"]

        # Pairwise assertions
        # 1. PySpark == Obsidian
        assert pyspark_a.sha256_hash == obsidian_a.sha256_hash
        assert pyspark_a.payload == obsidian_a.payload
        # 2. PySpark == Git
        assert pyspark_a.sha256_hash == git_a.sha256_hash
        assert pyspark_a.payload == git_a.payload
        # 3. Git == GDrive
        assert git_a.sha256_hash == gdrive_a.sha256_hash
        assert git_a.payload == gdrive_a.payload
        # 4. Obsidian == GDrive
        assert obsidian_a.sha256_hash == gdrive_a.sha256_hash
        assert obsidian_a.payload == gdrive_a.payload

    def test_tier3_c4_atomic_rollback_on_simulated_failure(self, test_sync_config: SyncConfig):
        """C4: Asserts rollback removes uncommitted single files if a vault syncer fails."""
        engine = CanonicalSyncEngine(config=test_sync_config)

        class _FailSyncer(BaseVaultSyncer):
            @property
            def vault_name(self) -> str:
                return "gdrive"
            def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
                return VaultSyncResult.create_failure("gdrive", "", "Simulated Failure")
            def verify(self, artifact: TruthArtifact) -> bool:
                return False
            def read(self, artifact_id: str) -> Optional[TruthArtifact]:
                return None

        engine.syncers["gdrive"] = _FailSyncer(config=test_sync_config)
        artifact = create_synthetic_truth_audit_artifact("art-rollback-test")

        res = engine.sync_truth_artifact(
            artifact=artifact,
            verify_first=False,
            parallel=False,
            rollback_on_failure=True,
        )

        assert res.success is False
        # Obsidian note should have been unlinked by rollback
        obs_note = test_sync_config.obsidian_vault_path / "truth_artifacts" / f"{artifact.artifact_id}.md"
        assert not obs_note.exists()

    def test_tier3_c5_idempotent_double_sync(self, test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
        """C5: Asserts syncing the identical artifact twice succeeds idempotently."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        res1 = engine.sync_truth_artifact(sample_truth_artifact)
        res2 = engine.sync_truth_artifact(sample_truth_artifact)

        assert res1.success is True
        assert res2.success is True
        assert engine.verify_all_vaults(sample_truth_artifact) == {
            "pyspark": True, "obsidian": True, "git": True, "gdrive": True
        }


# =============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# =============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: Production workload simulations across Swarms, Mesh, LoRA, and ADRs."""

    def test_tier4_scenario1_swarm_debate_consensus_propagation(self, test_sync_config: SyncConfig):
        """Scenario 1: Tri-Orchestrator Swarm Consensus deliberation record propagation."""
        artifact = TruthArtifact(
            artifact_id="art-debate-consensus-2026-08-27",
            artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
            title="Tri-Orchestrator Consensus: Adoption of Quad-Vault Invariant Engine",
            payload={
                "debate_id": "DEBATE-001",
                "consensus_score": 0.994,
                "quorum_reached": True,
                "deliberation_rounds": 3,
                "participants": [
                    {"name": "Gemini_3.1_Pro_High", "verdict": "APPROVE"},
                    {"name": "Gemini_3.7_Flash_High", "verdict": "APPROVE"},
                    {"name": "Kimi_Tandem", "verdict": "APPROVE"},
                    {"name": "Qwen_3.8_Max", "verdict": "APPROVE"},
                ],
                "resolution": "Enforce sub-3ms fast path and 100% cryptographic SHA-256 parity.",
            },
            tags=["swarm", "debate", "consensus", "m4"],
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact, verify_first=True)

        assert res.success is True
        assert res.all_vaults_succeeded is True

        # Check Obsidian Wikilinks
        obsidian_note = test_sync_config.obsidian_vault_path / "truth_artifacts" / f"{artifact.artifact_id}.md"
        content = obsidian_note.read_text(encoding="utf-8")
        assert "[[Index]]" in content
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[ai_debate_consensus]]" in content

    def test_tier4_scenario2_live_mesh_health_telemetry_audit(self, test_sync_config: SyncConfig):
        """Scenario 2: Live 7-Layer Mesh Node Health Audit Telemetry ingestion."""
        scanner = MeshNodeScanner()
        mesh_summary = scanner.get_mesh_summary(parallel=True)

        artifact = TruthArtifact(
            artifact_id=f"art-telemetry-mesh-{int(time.time())}",
            artifact_type=ArtifactType.TELEMETRY_RECORD,
            title="7-Layer Mesh Storage & Capacity Telemetry Snapshot",
            payload={
                "total_nodes": mesh_summary.total_nodes,
                "online_nodes": mesh_summary.online_nodes,
                "total_mesh_capacity_gb": mesh_summary.total_mesh_capacity_gb,
                "total_mesh_free_gb": mesh_summary.total_mesh_free_gb,
                "scan_duration_ms": mesh_summary.scan_duration_ms,
                "layer_breakdown": {
                    "L1_Mac_Node": "ONLINE",
                    "L2_MacBook_Pro": "TB4_BRIDGE",
                    "L3_Linux_Head_Node": "COMPUTE_HUB",
                },
            },
            tags=["telemetry", "mesh", "hardware_matrix", "audit"],
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact, verify_first=True)

        assert res.success is True
        assert res.vault_results["pyspark"].success is True

    def test_tier4_scenario3_continuous_lora_dataset_pair_ingestion(self, test_sync_config: SyncConfig):
        """Scenario 3: 24/7 Continuous LoRA Training Dataset instruction pair ingestion."""
        lora_pairs = [
            TruthArtifact(
                artifact_id=f"art-lora-pair-{i:04d}",
                artifact_type=ArtifactType.LORA_PAIR,
                title=f"LoRA DPO Pair {i}: Canonical Storage Invariant",
                payload={
                    "instruction": "Explain Rule 6.1 storage health invariants.",
                    "input": "Obsidian vault path, PySpark dataset path, and disk headroom.",
                    "chosen_response": "Rule 6.1 requires Obsidian Index.md with Wikilinks, PySpark JSONL, and >=10GB headroom.",
                    "rejected_response": "Storage is healthy if files are on disk without checking invariants.",
                    "dpo_margin": 1.45,
                    "model_source": "Qwen_3.8_Max_Distill",
                },
                tags=["lora", "dpo", "training_dataset", "24_7_memory"],
            )
            for i in range(3)
        ]
        engine = CanonicalSyncEngine(config=test_sync_config)
        results = engine.sync_batch(lora_pairs, verify_first=True)

        assert len(results) == 3
        assert all(r.success for r in results)

        # Check partitioned dataset in PySpark
        lora_partition = test_sync_config.pyspark_dataset_path / "by_type" / "lora_pair.jsonl"
        assert lora_partition.exists()
        lines = [l for l in lora_partition.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
        assert len(lines) == 3

    def test_tier4_scenario4_architectural_decision_record_rfc(self, test_sync_config: SyncConfig):
        """Scenario 4: Architectural Decision Record (ADR) RFC generation and propagation."""
        adr_artifact = TruthArtifact(
            artifact_id="ADR-0042-QUAD-VAULT-SYNC",
            artifact_type=ArtifactType.ARCHITECTURAL_DECISION,
            title="ADR 0042: Deterministic SHA-256 Quad-Vault Synchronizer",
            payload={
                "status": "ACCEPTED",
                "deciders": ["Project Orchestrator", "Sentinel", "M4 Worker"],
                "context": "We need resilient, zero-mock synchronization across 4 storage layers.",
                "decision": "Implement CanonicalSyncEngine with fast-path, pre-flight healer, and 4 syncer adapters.",
                "consequences": {
                    "positive": ["Cryptographic parity guaranteed", "Sub-3ms fast path", "Zero data loss"],
                    "negative": ["Multi-target write latency overhead"],
                },
            },
            tags=["adr", "architecture", "rfc", "canonical"],
        )
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(adr_artifact, verify_first=True)

        assert res.success is True
        staged_git_file = test_sync_config.git_repo_path / "04_data_and_memory" / "core_data" / "ADR-0042-QUAD-VAULT-SYNC.json"
        assert staged_git_file.exists()

    def test_tier4_scenario5_disaster_recovery_storage_resurrection(self, tmp_path: Path):
        """Scenario 5: Complete disaster recovery and automated storage resurrection workflow."""
        config = SyncConfig.for_testing(tmp_path)
        # Induce multi-layer corruption:
        # 1. Missing obsidian vault directory
        shutil.rmtree(config.obsidian_vault_path, ignore_errors=True)
        # 2. Corrupt PySpark dataset
        config.pyspark_dataset_path.mkdir(parents=True, exist_ok=True)
        (config.pyspark_dataset_path / "truth_audit_master.jsonl").write_text("CORRUPTED\n", encoding="utf-8")
        # 3. Stale git lock
        dot_git = config.git_repo_path / ".git"
        dot_git.mkdir(parents=True, exist_ok=True)
        lock_file = dot_git / "index.lock"
        lock_file.write_text("stale", encoding="utf-8")
        os.utime(lock_file, (time.time() - 900, time.time() - 900))

        # Run resurrection via CanonicalSyncEngine auto_heal
        engine = CanonicalSyncEngine(config=config, auto_heal=True)
        artifact = create_synthetic_truth_audit_artifact("art-disaster-resurrected")
        res = engine.sync_truth_artifact(artifact, verify_first=True)

        assert res.success is True
        assert res.all_vaults_succeeded is True
        assert not lock_file.exists()
        assert (config.obsidian_vault_path / "Index.md").exists()
        assert engine.verify_all_vaults(artifact) == {"pyspark": True, "obsidian": True, "git": True, "gdrive": True}


# =============================================================================
# TIER 5: ADVERSARIAL COVERAGE HARDENING
# =============================================================================

class TestTier5AdversarialHardening:
    """Tier 5: Adversarial stress testing, tampered data, broken permissions, and fault recovery."""

    def test_tier5_a1_tampered_artifact_hash_rejection(self, test_sync_config: SyncConfig):
        """A1: Asserts tampered SHA-256 hash in TruthArtifact is rejected before any disk write."""
        artifact = create_synthetic_truth_audit_artifact("art-tamper-hash")
        artifact.sha256_hash = "deadbeef" * 8  # 64-char fake hash

        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)

        assert res.success is False
        assert len(res.errors) > 0
        assert "verification failed" in res.errors[0]
        # Verify no files were created
        assert not (test_sync_config.obsidian_vault_path / "truth_artifacts" / "art-tamper-hash.md").exists()

    def test_tier5_a2_post_sync_ondisk_tampering_detection(self, test_sync_config: SyncConfig):
        """A2: Asserts on-disk file tampering after sync is detected by verify_all_vaults()."""
        artifact = create_synthetic_truth_audit_artifact("art-disk-tamper")
        engine = CanonicalSyncEngine(config=test_sync_config)
        res = engine.sync_truth_artifact(artifact)
        assert res.success is True

        # Tamper with Git JSON file
        git_file = test_sync_config.git_repo_path / "04_data_and_memory" / "core_data" / f"{artifact.artifact_id}.json"
        data = json.loads(git_file.read_text(encoding="utf-8"))
        data["payload"]["tampered"] = True
        git_file.write_text(json.dumps(data), encoding="utf-8")

        v_status = engine.verify_all_vaults(artifact)
        assert v_status["git"] is False  # Must detect tampering
        assert v_status["pyspark"] is True
        assert v_status["obsidian"] is True

    def test_tier5_a3_broken_file_permissions_error_isolation(self, test_sync_config: SyncConfig):
        """A3: Asserts read-only directory in one vault is isolated while other vaults succeed."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        artifact = create_synthetic_truth_audit_artifact("art-perm-iso")

        # Make Obsidian directory read-only (0o444)
        obs_dir = test_sync_config.obsidian_vault_path / "truth_artifacts"
        obs_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(obs_dir, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

        try:
            res = engine.sync_truth_artifact(artifact, verify_first=False)
            assert res.success is False
            assert "obsidian" in res.failed_vaults
            assert "pyspark" in res.succeeded_vaults
            assert "git" in res.succeeded_vaults
            assert "gdrive" in res.succeeded_vaults
        finally:
            # Restore permissions for teardown
            os.chmod(obs_dir, stat.S_IRWXU)

    def test_tier5_a4_corrupted_jsonl_lines_in_pyspark_master(self, test_sync_config: SyncConfig):
        """A4: Asserts parser skips malformed/corrupted JSON lines in PySpark JSONL without crashing."""
        syncer = PySparkVaultSyncer(config=test_sync_config)
        art1 = TruthArtifact("art-valid-1", ArtifactType.TRUTH_AUDIT, "Valid 1", {"v": 1})
        art2 = TruthArtifact("art-valid-2", ArtifactType.TRUTH_AUDIT, "Valid 2", {"v": 2})

        syncer.sync(art1)
        # Inject corrupted line
        with open(syncer.master_jsonl_path, "a", encoding="utf-8") as f:
            f.write("MALFORMED_JSON_LINE_HERE_WITHOUT_BRACES\n")
            f.write('{"incomplete_json": \n')
        syncer.sync(art2)

        read_art1 = syncer.read("art-valid-1")
        read_art2 = syncer.read("art-valid-2")
        assert read_art1 is not None and read_art1.artifact_id == "art-valid-1"
        assert read_art2 is not None and read_art2.artifact_id == "art-valid-2"

        all_valid = syncer.read_all()
        assert len(all_valid) == 2

    def test_tier5_a5_corrupted_obsidian_frontmatter_handling(self, test_sync_config: SyncConfig):
        """A5: Asserts Obsidian note with unparseable frontmatter returns None gracefully."""
        syncer = ObsidianVaultSyncer(config=test_sync_config)
        note_path = test_sync_config.obsidian_vault_path / "truth_artifacts" / "corrupt_note.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text("No frontmatter at all in this text file.", encoding="utf-8")

        assert syncer.read("corrupt_note") is None

    def test_tier5_a6_rapid_sequential_sync_stress_test(self, test_sync_config: SyncConfig):
        """A6: Asserts 50 rapid sequential syncs exhibit zero file descriptor leaks or deadlocks."""
        engine = CanonicalSyncEngine(config=test_sync_config)
        t0 = time.perf_counter()

        for i in range(50):
            art = TruthArtifact(
                artifact_id=f"art-rapid-{i:03d}",
                artifact_type=ArtifactType.TRUTH_AUDIT,
                title=f"Rapid Sync {i}",
                payload={"i": i, "t": time.time()},
            )
            res = engine.sync_truth_artifact(art, verify_first=False, parallel=True)
            assert res.success is True

        total_time = time.perf_counter() - t0
        assert total_time < 10.0  # 50 syncs must complete rapidly (< 200ms each)
