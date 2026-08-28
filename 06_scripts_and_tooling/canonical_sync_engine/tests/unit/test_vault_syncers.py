"""
tests/unit/test_vault_syncers.py
Comprehensive unit tests for the 4 Quad-Vault synchronization adapters:
BaseVaultSyncer, PySparkVaultSyncer, ObsidianVaultSyncer, GitVaultSyncer, GDriveVaultSyncer.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List
import pytest

from canonical_sync_engine.config import SyncConfig
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.sync_result import VaultSyncResult
from canonical_sync_engine.sync import (
    BaseVaultSyncer,
    PySparkVaultSyncer,
    ObsidianVaultSyncer,
    GitVaultSyncer,
    GDriveVaultSyncer,
)


# ==============================================================================
# 1. BaseVaultSyncer Abstract Class & Utility Tests
# ==============================================================================


def test_base_vault_syncer_cannot_be_instantiated_directly():
    """Asserts that BaseVaultSyncer is abstract and cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseVaultSyncer()  # type: ignore


def test_base_vault_syncer_atomic_write_utilities(tmp_path: Path):
    """Tests _atomic_write_text and _atomic_write_json utility methods."""
    class DummySyncer(BaseVaultSyncer):
        @property
        def vault_name(self) -> str:
            return "dummy"
        def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
            return VaultSyncResult.create_success("dummy", "", "", 0)
        def verify(self, artifact: TruthArtifact) -> bool:
            return True
        def read(self, artifact_id: str):
            return None

    syncer = DummySyncer()
    target_file = tmp_path / "subdir" / "test.txt"
    bytes_written = syncer._atomic_write_text(target_file, "Hello Atomic World!")
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "Hello Atomic World!"
    assert bytes_written > 0

    json_file = tmp_path / "subdir" / "data.json"
    data = {"b": 2, "a": 1}
    syncer._atomic_write_json(json_file, data)
    assert json_file.exists()
    parsed = json.loads(json_file.read_text(encoding="utf-8"))
    assert parsed == {"a": 1, "b": 2}


def test_timer_utility():
    """Tests the latency timer context manager."""
    class DummySyncer(BaseVaultSyncer):
        @property
        def vault_name(self) -> str:
            return "dummy"
        def sync(self, artifact: TruthArtifact) -> VaultSyncResult:
            return VaultSyncResult.create_success("dummy", "", "", 0)
        def verify(self, artifact: TruthArtifact) -> bool:
            return True
        def read(self, artifact_id: str):
            return None

    syncer = DummySyncer()
    with syncer._measure_time() as timer:
        time.sleep(0.01)
    assert timer.elapsed_ms >= 5.0


# ==============================================================================
# 2. PySparkVaultSyncer Tests
# ==============================================================================


def test_pyspark_syncer_sync_and_verify(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests single artifact synchronization to PySpark Data Lake JSONL."""
    syncer = PySparkVaultSyncer(test_sync_config)
    result = syncer.sync(sample_truth_artifact)

    assert result.success is True
    assert result.vault_name == "pyspark"
    assert result.sha256_hash == sample_truth_artifact.sha256_hash
    assert result.bytes_written > 0
    assert result.latency_ms > 0.0
    assert "master_jsonl" in result.metadata

    # Assert master file exists and contains record
    master_path = syncer.master_jsonl_path
    assert master_path.exists()
    content = master_path.read_text(encoding="utf-8")
    assert sample_truth_artifact.artifact_id in content

    # Assert verify and read
    assert syncer.verify(sample_truth_artifact) is True
    reconstructed = syncer.read(sample_truth_artifact.artifact_id)
    assert reconstructed is not None
    assert reconstructed.artifact_id == sample_truth_artifact.artifact_id
    assert reconstructed.sha256_hash == sample_truth_artifact.sha256_hash
    assert reconstructed.payload == sample_truth_artifact.payload
    assert reconstructed.verify_hash() is True


def test_pyspark_syncer_multiple_sequential_records(test_sync_config: SyncConfig):
    """Tests appending multiple distinct artifacts to PySpark JSONL."""
    syncer = PySparkVaultSyncer(test_sync_config)
    artifacts = []
    for i in range(5):
        art = TruthArtifact(
            artifact_id=f"art-multi-{i}",
            artifact_type=ArtifactType.LORA_PAIR if i % 2 == 0 else ArtifactType.TRUTH_AUDIT,
            title=f"Multi Test Artifact {i}",
            payload={"index": i, "data": f"value_{i}"},
            source_node="Mac_Node",
            tags=[f"tag_{i}"],
        )
        artifacts.append(art)
        res = syncer.sync(art)
        assert res.success is True

    all_records = syncer.read_all()
    assert len(all_records) == 5
    for art in artifacts:
        assert syncer.verify(art) is True
        read_art = syncer.read(art.artifact_id)
        assert read_art is not None
        assert read_art.payload == art.payload


def test_pyspark_syncer_concurrent_threads(test_sync_config: SyncConfig):
    """Tests thread-safety and race condition prevention during concurrent JSONL appends."""
    syncer = PySparkVaultSyncer(test_sync_config)
    num_threads = 20

    def sync_worker(idx: int) -> VaultSyncResult:
        art = TruthArtifact(
            artifact_id=f"art-concurrent-{idx:03d}",
            artifact_type=ArtifactType.TELEMETRY_RECORD,
            title=f"Concurrent Telemetry {idx}",
            payload={"sensor_id": f"s_{idx}", "value": idx * 1.5},
            source_node="Mac_Node",
        )
        return syncer.sync(art)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(sync_worker, i) for i in range(num_threads)]
        results = [f.result() for f in futures]

    assert all(r.success for r in results)
    all_read = syncer.read_all()
    assert len(all_read) == num_threads

    # Verify line integrity of master JSONL
    master_path = syncer.master_jsonl_path
    lines = master_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == num_threads
    for line in lines:
        data = json.loads(line)
        assert "artifact_id" in data


def test_pyspark_syncer_corrupt_line_handling_and_read(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests PySpark syncer robustness against corrupt/invalid JSON lines."""
    syncer = PySparkVaultSyncer(test_sync_config)
    syncer.sync(sample_truth_artifact)

    master_path = syncer.master_jsonl_path
    # Inject corrupt line
    with open(master_path, "a", encoding="utf-8") as f:
        f.write("CORRUPT_NOT_JSON_DATA_LINE_12345\n")

    # Sync another valid artifact
    art2 = TruthArtifact(
        artifact_id="art-valid-after-corrupt",
        artifact_type=ArtifactType.BENCHMARK_RESULT,
        title="Valid After Corrupt",
        payload={"score": 99.8},
    )
    syncer.sync(art2)

    # Both valid artifacts should still be readable
    assert syncer.verify(sample_truth_artifact) is True
    assert syncer.verify(art2) is True
    assert syncer.read(sample_truth_artifact.artifact_id) is not None
    assert syncer.read(art2.artifact_id) is not None

    all_valid = syncer.read_all()
    assert len(all_valid) == 2


def test_pyspark_syncer_verify_tamper_detection(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests that PySpark syncer detects tampered record content."""
    syncer = PySparkVaultSyncer(test_sync_config)
    syncer.sync(sample_truth_artifact)

    # Modify sample_truth_artifact sha256_hash or payload
    tampered_art = TruthArtifact(
        artifact_id=sample_truth_artifact.artifact_id,
        artifact_type=sample_truth_artifact.artifact_type,
        title="Tampered Title",
        payload={"tampered": True},
        source_node=sample_truth_artifact.source_node,
    )
    # Target file still holds original, so tampered_art verify fails
    assert syncer.verify(tampered_art) is False


def test_pyspark_syncer_non_existent_read(test_sync_config: SyncConfig):
    """Asserts that reading a non-existent artifact returns None."""
    syncer = PySparkVaultSyncer(test_sync_config)
    assert syncer.read("non-existent-artifact-999") is None


# ==============================================================================
# 3. ObsidianVaultSyncer Tests
# ==============================================================================


def test_obsidian_syncer_sync_and_verify(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests Markdown note generation with YAML frontmatter and Wikilinks in Obsidian."""
    syncer = ObsidianVaultSyncer(test_sync_config)
    result = syncer.sync(sample_truth_artifact)

    assert result.success is True
    assert result.vault_name == "obsidian"
    assert result.sha256_hash == sample_truth_artifact.sha256_hash
    assert result.bytes_written > 0

    note_path = syncer.get_note_path(sample_truth_artifact.artifact_id)
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")

    # Assert YAML frontmatter and Wikilinks
    assert "---" in content
    assert f'artifact_id: "{sample_truth_artifact.artifact_id}"' in content
    assert f'sha256_hash: "{sample_truth_artifact.sha256_hash}"' in content
    assert "[[Index]]" in content
    assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
    assert f"[[{sample_truth_artifact.artifact_type.value}]]" in content

    # Assert verify and read
    assert syncer.verify(sample_truth_artifact) is True
    reconstructed = syncer.read(sample_truth_artifact.artifact_id)
    assert reconstructed is not None
    assert reconstructed.artifact_id == sample_truth_artifact.artifact_id
    assert reconstructed.sha256_hash == sample_truth_artifact.sha256_hash
    assert reconstructed.title == sample_truth_artifact.title
    assert reconstructed.payload == sample_truth_artifact.payload
    assert reconstructed.tags == sample_truth_artifact.tags
    assert reconstructed.verify_hash() is True


def test_obsidian_syncer_ai_debate_artifact(test_sync_config: SyncConfig, sample_ai_debate_artifact: TruthArtifact):
    """Tests Obsidian note formatting for complex AI debate consensus artifact."""
    syncer = ObsidianVaultSyncer(test_sync_config)
    result = syncer.sync(sample_ai_debate_artifact)
    assert result.success is True

    note_path = syncer.get_note_path(sample_ai_debate_artifact.artifact_id)
    content = note_path.read_text(encoding="utf-8")
    assert "[[ai_debate_consensus]]" in content
    assert "consensus_score" in content

    assert syncer.verify(sample_ai_debate_artifact) is True
    recon = syncer.read(sample_ai_debate_artifact.artifact_id)
    assert recon is not None
    assert recon.payload["quorum_reached"] is True


def test_obsidian_syncer_tamper_detection_missing_wikilink(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests that verify fails if canonical Wikilinks are stripped from note."""
    syncer = ObsidianVaultSyncer(test_sync_config)
    syncer.sync(sample_truth_artifact)

    note_path = syncer.get_note_path(sample_truth_artifact.artifact_id)
    content = note_path.read_text(encoding="utf-8")
    # Remove mandatory Index link
    tampered_content = content.replace("[[Index]]", "")
    note_path.write_text(tampered_content, encoding="utf-8")

    assert syncer.verify(sample_truth_artifact) is False


def test_obsidian_syncer_tamper_detection_hash_mismatch(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests that verify fails if sha256_hash in frontmatter is mutated."""
    syncer = ObsidianVaultSyncer(test_sync_config)
    syncer.sync(sample_truth_artifact)

    note_path = syncer.get_note_path(sample_truth_artifact.artifact_id)
    content = note_path.read_text(encoding="utf-8")
    fake_hash = "0" * 64
    tampered_content = content.replace(sample_truth_artifact.sha256_hash, fake_hash)
    note_path.write_text(tampered_content, encoding="utf-8")

    assert syncer.verify(sample_truth_artifact) is False


def test_obsidian_syncer_non_existent_read(test_sync_config: SyncConfig):
    """Asserts reading a non-existent note returns None."""
    syncer = ObsidianVaultSyncer(test_sync_config)
    assert syncer.read("non_existent_note_999") is None


# ==============================================================================
# 4. GitVaultSyncer Tests
# ==============================================================================


def test_git_syncer_sync_and_verify(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests Git worktree JSON artifact persistence and hash verification."""
    syncer = GitVaultSyncer(test_sync_config)
    result = syncer.sync(sample_truth_artifact)

    assert result.success is True
    assert result.vault_name == "git"
    assert result.sha256_hash == sample_truth_artifact.sha256_hash
    assert result.bytes_written > 0

    target_path = syncer.get_artifact_path(sample_truth_artifact.artifact_id)
    assert target_path.exists()
    data = json.loads(target_path.read_text(encoding="utf-8"))
    assert data["artifact_id"] == sample_truth_artifact.artifact_id

    assert syncer.verify(sample_truth_artifact) is True
    reconstructed = syncer.read(sample_truth_artifact.artifact_id)
    assert reconstructed is not None
    assert reconstructed.sha256_hash == sample_truth_artifact.sha256_hash
    assert reconstructed.payload == sample_truth_artifact.payload


def test_git_syncer_with_real_git_repository(tmp_path: Path, sample_truth_artifact: TruthArtifact):
    """Tests Git staging integration when inside an initialized git repository."""
    git_dir = tmp_path / "git_sandbox"
    git_dir.mkdir(parents=True, exist_ok=True)

    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=str(git_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@lauburu.local"], cwd=str(git_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Lauburu Tester"], cwd=str(git_dir), capture_output=True, check=True)

    config = SyncConfig.for_testing(tmp_path)
    config.git_repo_path = git_dir

    syncer = GitVaultSyncer(config)
    result = syncer.sync(sample_truth_artifact)

    assert result.success is True
    assert result.metadata.get("staged") is True

    # Assert git status shows staged file
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(git_dir), capture_output=True, text=True, check=True)
    assert "A " in status.stdout or "M " in status.stdout or "04_data_and_memory" in status.stdout


def test_git_syncer_stale_lock_healing(tmp_path: Path, sample_truth_artifact: TruthArtifact):
    """Tests that GitVaultSyncer automatically clears stale .git/index.lock files."""
    git_dir = tmp_path / "git_locked_sandbox"
    git_dir.mkdir(parents=True, exist_ok=True)
    dot_git = git_dir / ".git"
    dot_git.mkdir(parents=True, exist_ok=True)

    lock_file = dot_git / "index.lock"
    lock_file.write_text("stale_lock", encoding="utf-8")
    # Make lock file 15 minutes old
    old_time = time.time() - 900
    os.utime(str(lock_file), (old_time, old_time))

    config = SyncConfig.for_testing(tmp_path)
    config.git_repo_path = git_dir

    syncer = GitVaultSyncer(config)
    cleared = syncer._check_and_heal_git_lock(git_dir)
    assert cleared is True
    assert not lock_file.exists()


def test_git_syncer_verify_tamper_detection(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests Git syncer tamper detection on mutated JSON content."""
    syncer = GitVaultSyncer(test_sync_config)
    syncer.sync(sample_truth_artifact)

    target_path = syncer.get_artifact_path(sample_truth_artifact.artifact_id)
    data = json.loads(target_path.read_text(encoding="utf-8"))
    data["payload"]["tampered"] = "yes"
    target_path.write_text(json.dumps(data), encoding="utf-8")

    assert syncer.verify(sample_truth_artifact) is False


def test_git_syncer_non_existent_read(test_sync_config: SyncConfig):
    """Asserts reading a non-existent git artifact returns None."""
    syncer = GitVaultSyncer(test_sync_config)
    assert syncer.read("non_existent_git_artifact") is None


# ==============================================================================
# 5. GDriveVaultSyncer Tests
# ==============================================================================


def test_gdrive_syncer_tier_1_native_mount(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests Tier 1 native mount resolution and synchronization."""
    syncer = GDriveVaultSyncer(test_sync_config)
    dest_dir, tier = syncer.resolve_destination()
    assert tier == "tier_1_native_mount"

    result = syncer.sync(sample_truth_artifact)
    assert result.success is True
    assert result.vault_name == "gdrive"
    assert result.metadata["tier_used"] == "tier_1_native_mount"
    assert result.metadata["is_offline_queued"] is False

    target_path = syncer.get_artifact_path(sample_truth_artifact.artifact_id, base_dir=dest_dir)
    assert target_path.exists()
    assert syncer.verify(sample_truth_artifact) is True

    recon = syncer.read(sample_truth_artifact.artifact_id)
    assert recon is not None
    assert recon.sha256_hash == sample_truth_artifact.sha256_hash


def test_gdrive_syncer_tier_3_fallback_cache_and_offline_queue(tmp_path: Path, sample_truth_artifact: TruthArtifact):
    """Tests Tier 3 fallback cache resolution and pending_sync.jsonl offline queuing."""
    config = SyncConfig.for_testing(tmp_path)
    # Point native mount to non-existent directory
    config.gdrive_mount_path = tmp_path / "unmounted_volume" / "Google Drive"

    syncer = GDriveVaultSyncer(config)
    dest_dir, tier = syncer.resolve_destination()
    assert tier == "tier_3_fallback_cache"

    result = syncer.sync(sample_truth_artifact)
    assert result.success is True
    assert result.metadata["tier_used"] == "tier_3_fallback_cache"
    assert result.metadata["is_offline_queued"] is True

    # Assert pending_sync.jsonl was written
    queue_file = config.gdrive_fallback_cache_path / "pending_sync.jsonl"
    assert queue_file.exists()
    queue_content = queue_file.read_text(encoding="utf-8")
    assert sample_truth_artifact.artifact_id in queue_content

    # Assert verify and read work from fallback cache
    assert syncer.verify(sample_truth_artifact) is True
    recon = syncer.read(sample_truth_artifact.artifact_id)
    assert recon is not None
    assert recon.sha256_hash == sample_truth_artifact.sha256_hash


def test_gdrive_syncer_tier_2_rclone_resolution(tmp_path: Path, sample_truth_artifact: TruthArtifact, monkeypatch: pytest.MonkeyPatch):
    """Tests Tier 2 rclone mount resolution via environment variable."""
    config = SyncConfig.for_testing(tmp_path)
    config.gdrive_mount_path = tmp_path / "unmounted_volume"

    rclone_dir = tmp_path / "rclone_gdrive_mount"
    rclone_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("RCLONE_MOUNT_PATH", str(rclone_dir))

    syncer = GDriveVaultSyncer(config)
    dest_dir, tier = syncer.resolve_destination()
    assert tier == "tier_2_rclone_mount"

    result = syncer.sync(sample_truth_artifact)
    assert result.success is True
    assert result.metadata["tier_used"] == "tier_2_rclone_mount"


def test_gdrive_syncer_verify_tamper_detection(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests Google Drive syncer tamper detection on mutated JSON content."""
    syncer = GDriveVaultSyncer(test_sync_config)
    syncer.sync(sample_truth_artifact)

    dest_dir, _ = syncer.resolve_destination()
    target_path = syncer.get_artifact_path(sample_truth_artifact.artifact_id, base_dir=dest_dir)
    data = json.loads(target_path.read_text(encoding="utf-8"))
    data["sha256_hash"] = "tampered_hash_value"
    target_path.write_text(json.dumps(data), encoding="utf-8")

    assert syncer.verify(sample_truth_artifact) is False


def test_gdrive_syncer_non_existent_read(test_sync_config: SyncConfig):
    """Asserts reading non-existent GDrive artifact returns None."""
    syncer = GDriveVaultSyncer(test_sync_config)
    assert syncer.read("non_existent_gdrive_art") is None


# ==============================================================================
# 6. Cross-Vault Uniformity & Hash Parity Matrix Tests
# ==============================================================================


@pytest.mark.parametrize("art_type", list(ArtifactType))
def test_cross_vault_hash_parity_across_all_artifact_types(test_sync_config: SyncConfig, art_type: ArtifactType):
    """
    Parametrized test asserting that every ArtifactType synchronizes across all 4 vaults
    with 100% SHA-256 cryptographic parity and reconstructs identical data.
    """
    artifact = TruthArtifact(
        artifact_id=f"art-matrix-{art_type.value}",
        artifact_type=art_type,
        title=f"Cross-Vault Certification: {art_type.value}",
        payload={
            "type": art_type.value,
            "certified": True,
            "nested": {"level": 2, "tags": ["cross_vault", art_type.value]},
        },
        source_node="Mac_Node",
        tags=["cross_vault", art_type.value],
        metadata={"spec_version": "2.0.0"},
    )

    syncers = [
        PySparkVaultSyncer(test_sync_config),
        ObsidianVaultSyncer(test_sync_config),
        GitVaultSyncer(test_sync_config),
        GDriveVaultSyncer(test_sync_config),
    ]

    for syncer in syncers:
        res = syncer.sync(artifact)
        assert res.success is True, f"Failed on {syncer.vault_name}: {res.error}"
        assert res.sha256_hash == artifact.sha256_hash
        assert syncer.verify(artifact) is True

        reconstructed = syncer.read(artifact.artifact_id)
        assert reconstructed is not None, f"Read failed on {syncer.vault_name}"
        assert reconstructed.artifact_id == artifact.artifact_id
        assert reconstructed.artifact_type == artifact.artifact_type
        assert reconstructed.sha256_hash == artifact.sha256_hash
        assert reconstructed.payload == artifact.payload
        assert reconstructed.verify_hash() is True


def test_cross_vault_error_isolation_on_broken_permissions(tmp_path: Path, sample_truth_artifact: TruthArtifact):
    """
    Tests that a filesystem error in one vault is isolated and reported as a clean failure
    result without crashing other vault syncers.
    """
    config = SyncConfig.for_testing(tmp_path)
    # Point PySpark to an invalid file path treated as directory
    invalid_file = tmp_path / "blocker.txt"
    invalid_file.write_text("i am a file not a dir", encoding="utf-8")
    config.pyspark_dataset_path = invalid_file / "sub_datasets"

    pyspark_syncer = PySparkVaultSyncer(config)
    obsidian_syncer = ObsidianVaultSyncer(config)

    # PySpark should return a clean failure result
    pyspark_res = pyspark_syncer.sync(sample_truth_artifact)
    assert pyspark_res.success is False
    assert pyspark_res.error is not None

    # Obsidian should succeed normally
    obsidian_res = obsidian_syncer.sync(sample_truth_artifact)
    assert obsidian_res.success is True


# ==============================================================================
# 7. Adversarial, Stress, & Boundary Matrix Tests for Vault Syncers
# ==============================================================================


def test_adversarial_large_payload_synchronization(test_sync_config: SyncConfig):
    """Tests syncing large (100KB+) deeply nested truth artifacts across all 4 syncers."""
    large_payload = {
        "depth_1": {
            "depth_2": {
                "records": [{"index": i, "vector": [float(i * 0.1)] * 50, "label": f"cluster_{i % 5}"} for i in range(100)],
                "description": "Large scale vector cluster benchmarking run",
            }
        },
        "stats": {"mean": 42.0, "variance": 1.2345},
    }
    artifact = TruthArtifact(
        artifact_id="art-adv-large-100k",
        artifact_type=ArtifactType.BENCHMARK_RESULT,
        title="Adversarial Large Payload Benchmark",
        payload=large_payload,
        source_node="Mac_Node",
        tags=["stress", "large_payload", "benchmark"],
        metadata={"size_tier": "100k", "depth": 4},
    )

    syncers = [
        PySparkVaultSyncer(test_sync_config),
        ObsidianVaultSyncer(test_sync_config),
        GitVaultSyncer(test_sync_config),
        GDriveVaultSyncer(test_sync_config),
    ]

    for syncer in syncers:
        res = syncer.sync(artifact)
        assert res.success is True
        assert res.bytes_written > 10000
        assert syncer.verify(artifact) is True

        read_art = syncer.read(artifact.artifact_id)
        assert read_art is not None
        assert read_art.sha256_hash == artifact.sha256_hash
        assert len(read_art.payload["depth_1"]["depth_2"]["records"]) == 100


def test_adversarial_unicode_and_special_characters_sync(test_sync_config: SyncConfig):
    """Tests synchronizing artifacts with multi-language Unicode, math symbols, and emojis."""
    unicode_payload = {
        "japanese": "コンニチハ 世界",
        "basque": "Euskara Lauburu Batasuna",
        "math": "∫_0^∞ e^{-x^2} dx = √π/2",
        "emojis": "🧠 ⚡ 🛡️ 🚀 💾 🌐",
        "special_chars": "<xml attr=\"val\"> & 'quotes' \n\t\r \\",
    }
    artifact = TruthArtifact(
        artifact_id="art-adv-unicode-✨",
        artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
        title="🌟 Unicode & Multi-Language Synthesis: 日本語 / Euskara / Math ∑",
        payload=unicode_payload,
        source_node="Mac_Node",
        tags=["unicode", "internationalization", "utf8_matrix", "🌐"],
        metadata={"charset": "UTF-8", "notes": "Special characters & <tags>"},
    )

    syncers = [
        PySparkVaultSyncer(test_sync_config),
        ObsidianVaultSyncer(test_sync_config),
        GitVaultSyncer(test_sync_config),
        GDriveVaultSyncer(test_sync_config),
    ]

    for syncer in syncers:
        res = syncer.sync(artifact)
        assert res.success is True
        assert syncer.verify(artifact) is True

        recon = syncer.read(artifact.artifact_id)
        assert recon is not None
        assert recon.sha256_hash == artifact.sha256_hash
        assert recon.payload["basque"] == "Euskara Lauburu Batasuna"
        assert recon.payload["emojis"] == "🧠 ⚡ 🛡️ 🚀 💾 🌐"


def test_adversarial_idempotency_double_sync(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests that syncing the exact same artifact multiple times is idempotent and safe."""
    syncers = [
        PySparkVaultSyncer(test_sync_config),
        ObsidianVaultSyncer(test_sync_config),
        GitVaultSyncer(test_sync_config),
        GDriveVaultSyncer(test_sync_config),
    ]

    for syncer in syncers:
        # First sync
        res1 = syncer.sync(sample_truth_artifact)
        assert res1.success is True

        # Second sync of identical artifact
        res2 = syncer.sync(sample_truth_artifact)
        assert res2.success is True

        # Should verify cleanly
        assert syncer.verify(sample_truth_artifact) is True
        read_art = syncer.read(sample_truth_artifact.artifact_id)
        assert read_art is not None
        assert read_art.sha256_hash == sample_truth_artifact.sha256_hash


def test_adversarial_corrupt_files_read_and_verify(test_sync_config: SyncConfig, sample_truth_artifact: TruthArtifact):
    """Tests that corrupt, truncated, or zero-byte files fail verify() cleanly without unhandled exceptions."""
    git_syncer = GitVaultSyncer(test_sync_config)
    gdrive_syncer = GDriveVaultSyncer(test_sync_config)
    obsidian_syncer = ObsidianVaultSyncer(test_sync_config)

    # 1. Test zero-byte file
    git_path = git_syncer.get_artifact_path(sample_truth_artifact.artifact_id)
    git_path.parent.mkdir(parents=True, exist_ok=True)
    git_path.write_text("", encoding="utf-8")
    assert git_syncer.verify(sample_truth_artifact) is False
    assert git_syncer.read(sample_truth_artifact.artifact_id) is None

    # 2. Test truncated JSON file
    dest_dir, _ = gdrive_syncer.resolve_destination()
    gdrive_path = gdrive_syncer.get_artifact_path(sample_truth_artifact.artifact_id, base_dir=dest_dir)
    gdrive_path.parent.mkdir(parents=True, exist_ok=True)
    gdrive_path.write_text('{"artifact_id": "art-test-001", "payloa', encoding="utf-8")
    assert gdrive_syncer.verify(sample_truth_artifact) is False
    assert gdrive_syncer.read(sample_truth_artifact.artifact_id) is None

    # 3. Test markdown file without YAML frontmatter
    obs_path = obsidian_syncer.get_note_path(sample_truth_artifact.artifact_id)
    obs_path.parent.mkdir(parents=True, exist_ok=True)
    obs_path.write_text("# Note without frontmatter\nSome body text", encoding="utf-8")
    assert obsidian_syncer.verify(sample_truth_artifact) is False
    assert obsidian_syncer.read(sample_truth_artifact.artifact_id) is None
