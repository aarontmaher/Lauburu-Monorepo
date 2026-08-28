"""
tests/unit/test_models.py
Unit and boundary tests for canonical_sync_engine models and configuration.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from canonical_sync_engine.config import (
    DEFAULT_MESH_TOPOLOGY,
    MeshNodeConfig,
    SyncConfig,
)
from canonical_sync_engine.models.artifact import ArtifactType, TruthArtifact
from canonical_sync_engine.models.health import (
    MeshSummaryReport,
    NodeProbeMethod,
    NodeStorageHealth,
    StorageHealthReport,
)
from canonical_sync_engine.models.sync_result import (
    QuadVaultSyncResult,
    VaultSyncResult,
)


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
    assert node_health.name == "Mac_Node"
    assert node_health.is_online is True
    assert node_health.storage_healthy is True
    assert node_health.free_disk_gb == 105.0

    d = node_health.to_dict()
    reconstructed = NodeStorageHealth.from_dict(d)
    assert reconstructed.node_id == "L1"
    assert reconstructed.disk_free_gb == 105.0

    unreachable = NodeStorageHealth.create_unreachable("L4", "Linux_Tablet", "Connection timed out", 2500.0)
    assert unreachable.is_reachable is False
    assert unreachable.headroom_ok is False
    assert unreachable.error_message == "Connection timed out"


def test_mesh_summary_report_and_roundtrip():
    n1 = NodeStorageHealth(node_id="L1", node_name="Mac_Node", is_reachable=True, disk_free_gb=100.0, disk_total_gb=500.0)
    n2 = NodeStorageHealth.create_unreachable("L4", "Linux_Tablet", "Offline")

    summary = MeshSummaryReport(
        total_nodes=2,
        online_nodes=1,
        offline_nodes=1,
        total_mesh_free_gb=100.0,
        total_mesh_capacity_gb=500.0,
        scan_duration_ms=45.0,
        nodes={"L1": n1, "L4": n2},
    )
    d = summary.to_dict()
    reconstructed = MeshSummaryReport.from_dict(d)
    assert reconstructed.total_nodes == 2
    assert reconstructed.online_nodes == 1
    assert reconstructed.offline_nodes == 1
    assert reconstructed.total_mesh_free_gb == 100.0


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
    custom_path = "/tmp/custom_obsidian"
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", custom_path)
    monkeypatch.setenv("CANONICAL_SYNC_MIN_HEADROOM_GB", "15.5")

    cfg = SyncConfig.from_env()
    assert cfg.obsidian_vault_path == Path(custom_path).resolve()
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


def test_truth_artifact_tags_order_hash_invariance():
    art1 = TruthArtifact(
        artifact_id="art-tags-1",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Tags Test",
        payload={"data": 1},
        tags=["zeta", "alpha", "beta"],
        timestamp="2026-08-27T00:00:00Z",
    )
    art2 = TruthArtifact(
        artifact_id="art-tags-1",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Tags Test",
        payload={"data": 1},
        tags=["alpha", "beta", "zeta"],
        timestamp="2026-08-27T00:00:00Z",
    )
    assert art1.sha256_hash == art2.sha256_hash


def test_truth_artifact_complex_types_payload():
    payload = {
        "is_active": True,
        "is_null": None,
        "count": 0,
        "ratio": 3.14159,
        "nested_arr": [1, "two", {"key": "val", "arr": [False, None]}],
    }
    art = TruthArtifact(
        artifact_id="art-complex",
        artifact_type=ArtifactType.TELEMETRY_RECORD,
        title="Complex Payload",
        payload=payload,
    )
    assert art.verify_hash() is True
    reconstructed = TruthArtifact.from_json(art.to_json())
    assert reconstructed.payload["is_active"] is True
    assert reconstructed.payload["is_null"] is None
    assert reconstructed.payload["ratio"] == 3.14159

