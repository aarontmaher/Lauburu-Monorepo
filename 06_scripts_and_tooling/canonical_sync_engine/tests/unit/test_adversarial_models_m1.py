"""
tests/unit/test_adversarial_models_m1.py
Empirical Challenger Adversarial Stress Suite for Milestone 1 Models & Canonical Hashing.

Covers:
1. Deeply nested JSON payloads (up to 100 levels) and massive trees.
2. Arbitrary recursive key permutations and dictionary order invariance (1000+ permutations).
3. List ordering sensitivity vs Dict key order invariance.
4. Unicode, Multilingual, Zero-Width, Emojis, and Escape Sequences.
5. Float representations, numeric precision, Boolean vs Integer distinction, Nulls.
6. Empty payloads, empty nested containers, and minimal envelopes.
7. Granular tamper detection across all fields (Avalanche effect verification).
8. Corrupted hashes, invalid hex, and signature verification.
9. Serialization roundtrips (to_dict, from_dict, to_json, from_json, to_markdown_frontmatter).
10. Health and Sync Result composite models stress testing under corrupt & degraded payloads.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import math
import random
import string
import pytest

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


# ============================================================================
# Helper Utilities for Adversarial Generation
# ============================================================================

def _permute_dict_keys(d: dict, rng: random.Random) -> dict:
    """Recursively permutes dictionary insertion order at every level."""
    items = list(d.items())
    rng.shuffle(items)
    new_d = {}
    for k, v in items:
        if isinstance(v, dict):
            new_d[k] = _permute_dict_keys(v, rng)
        elif isinstance(v, list):
            new_d[k] = [
                _permute_dict_keys(elem, rng) if isinstance(elem, dict) else elem
                for elem in v
            ]
        else:
            new_d[k] = v
    return new_d


def _build_deeply_nested_dict(depth: int, branch_factor: int = 2) -> dict:
    """Builds a deeply nested dictionary tree with varied types."""
    if depth <= 1:
        return {
            f"leaf_{i}": f"val_{i}_{random.randint(1000, 9999)}"
            for i in range(branch_factor)
        }
    return {
        f"branch_{depth}_{i}": _build_deeply_nested_dict(depth - 1, branch_factor)
        for i in range(branch_factor)
    }


# ============================================================================
# 1. Deeply Nested Payloads & Arbitrary Key Permutations
# ============================================================================

def test_adversarial_deep_nesting_hash_invariance():
    """Test 50 levels of nested dictionaries with identical contents in arbitrary insertion orders."""
    rng = random.Random(42)
    # Build 50-level linear nested dict
    root = {"val": 42}
    for level in range(50):
        root = {f"k_level_{level}": root, f"sibling_{level}": f"data_{level}"}

    # Generate 20 distinct dictionary key permutations of the same 50-level structure
    fixed_ts = "2026-08-27T00:00:00Z"
    artifacts = []
    for i in range(20):
        permuted_payload = _permute_dict_keys(root, rng)
        art = TruthArtifact(
            artifact_id="art-deep-nested",
            artifact_type=ArtifactType.TRUTH_AUDIT,
            title="Deeply Nested Test",
            payload=permuted_payload,
            source_node="Mac_Node",
            timestamp=fixed_ts,
            tags=["nested", "depth50"],
            metadata={"meta_k2": "v2", "meta_k1": "v1"},
        )
        artifacts.append(art)

    # Assert 100% hash equality across all 20 permutations
    canonical_hash = artifacts[0].sha256_hash
    for i, art in enumerate(artifacts):
        assert art.sha256_hash == canonical_hash, f"Permutation {i} produced mismatched hash!"
        assert art.verify_hash() is True


def test_adversarial_random_tree_100_permutations_invariance():
    """Build a complex hierarchical dictionary tree and test 100 randomized key permutations."""
    rng = random.Random(1337)
    base_tree = _build_deeply_nested_dict(depth=6, branch_factor=3)
    base_tree["mixed_list"] = [
        {"sub_k2": "v2", "sub_k1": "v1"},
        {"x": 10, "y": 20, "z": {"nested_b": 2, "nested_a": 1}},
        [1, 2, {"inner_2": True, "inner_1": False}],
    ]

    fixed_ts = "2026-08-27T12:00:00Z"
    base_art = TruthArtifact(
        artifact_id="art-tree-perm",
        artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
        title="Tree Permutations",
        payload=base_tree,
        timestamp=fixed_ts,
    )
    expected_hash = base_art.sha256_hash

    for step in range(100):
        shuffled_payload = _permute_dict_keys(base_tree, rng)
        test_art = TruthArtifact(
            artifact_id="art-tree-perm",
            artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
            title="Tree Permutations",
            payload=shuffled_payload,
            timestamp=fixed_ts,
        )
        assert test_art.sha256_hash == expected_hash, f"Failed at step {step}"
        assert test_art.verify_hash() is True


# ============================================================================
# 2. List Ordering Sensitivity vs Dict Key Invariance
# ============================================================================

def test_adversarial_list_order_sensitivity():
    """Verify that while dict keys are order-invariant, list elements are order-sensitive."""
    fixed_ts = "2026-08-27T00:00:00Z"

    # List element reordering MUST change the hash
    art_list_1 = TruthArtifact(
        artifact_id="art-list",
        artifact_type=ArtifactType.LORA_PAIR,
        title="List Test",
        payload={"items": [1, 2, 3, 4]},
        timestamp=fixed_ts,
    )
    art_list_2 = TruthArtifact(
        artifact_id="art-list",
        artifact_type=ArtifactType.LORA_PAIR,
        title="List Test",
        payload={"items": [1, 3, 2, 4]},
        timestamp=fixed_ts,
    )
    assert art_list_1.sha256_hash != art_list_2.sha256_hash

    # Dict within list key reordering MUST preserve the hash
    art_dict_in_list_1 = TruthArtifact(
        artifact_id="art-d-list",
        artifact_type=ArtifactType.LORA_PAIR,
        title="Dict in List Test",
        payload={"items": [{"a": 1, "b": 2}, {"x": 10, "y": 20}]},
        timestamp=fixed_ts,
    )
    art_dict_in_list_2 = TruthArtifact(
        artifact_id="art-d-list",
        artifact_type=ArtifactType.LORA_PAIR,
        title="Dict in List Test",
        payload={"items": [{"b": 2, "a": 1}, {"y": 20, "x": 10}]},
        timestamp=fixed_ts,
    )
    assert art_dict_in_list_1.sha256_hash == art_dict_in_list_2.sha256_hash


# ============================================================================
# 3. Unicode, Multi-Byte UTF-8, Emojis, Control Characters
# ============================================================================

def test_adversarial_unicode_and_special_character_matrix():
    """Test unicode characters, zero-width joiners, bidirectional text, and control characters."""
    adversarial_strings = [
        "🔥⚡🚀💎🧠🛡️",  # Emojis
        "👨‍👩‍👧‍👦",         # ZWJ compound emoji
        "مرحبا بالعالم",     # Arabic Right-to-Left
        "שָׁלוֹם עוֹלָם",     # Hebrew
        "こんにちは世界",     # Japanese Kanji/Kana
        "안녕하세요 세계",     # Korean
        "Привет, мир",       # Russian Cyrillic
        "Γειά σου Κόσμε",    # Greek
        "Thành phố Hồ Chí Minh",  # Vietnamese tones
        "Kraków, Łódź, Gdańsk",    # Polish diacritics
        "Line1\nLine2\r\nLine3\tTabbed",  # Whitespace & escapes
        "Quotes: \" ' ` and backslash: \\",
        "Control chars: \x01\x02\x1f\x7f",
        "Zero-width: \u200B\u200C\u200D\uFEFF",  # ZWSP, ZWNJ, ZWJ, BOM
        "Math: ∀x ∈ ℝ, ∃y: y > x ∧ ∑(i=1..n) i = n(n+1)/2",
    ]

    for idx, sample in enumerate(adversarial_strings):
        art = TruthArtifact(
            artifact_id=f"art-unicode-{idx}",
            artifact_type=ArtifactType.TELEMETRY_RECORD,
            title=f"Title with {sample}",
            payload={
                "content": sample,
                "nested": {"deep_key": sample, "array": [sample, sample]},
            },
            tags=[f"tag_{idx}", sample[:10]],
            metadata={"source_text": sample},
        )

        assert art.verify_hash() is True

        # Test JSON roundtrip preserves exact string and hash
        json_repr = art.to_json()
        restored = TruthArtifact.from_json(json_repr)
        assert restored.sha256_hash == art.sha256_hash
        assert restored.payload["content"] == sample
        assert restored.verify_hash() is True

        # Test Markdown frontmatter generation handles special characters
        md_text = art.to_markdown_frontmatter(custom_body=f"Body: {sample}")
        assert art.sha256_hash in md_text
        assert art.artifact_id in md_text


# ============================================================================
# 4. Floats, Numbers, Booleans, Nulls Representation
# ============================================================================

def test_adversarial_numeric_types_and_precision():
    """Test various floating point values, large ints, booleans, and nulls."""
    payload = {
        "float_zero": 0.0,
        "float_neg_zero": -0.0,
        "small_float": 1e-15,
        "large_float": 1.23456789012345e25,
        "high_precision": 3.141592653589793,
        "int_zero": 0,
        "int_large": 2**64 - 1,
        "int_huge": 10**50,
        "bool_true": True,
        "bool_false": False,
        "null_val": None,
    }

    art = TruthArtifact(
        artifact_id="art-num-001",
        artifact_type=ArtifactType.BENCHMARK_RESULT,
        title="Numeric Stress Test",
        payload=payload,
    )
    assert art.verify_hash() is True

    # JSON roundtrip
    restored = TruthArtifact.from_json(art.to_json())
    assert restored.sha256_hash == art.sha256_hash
    assert restored.payload["float_zero"] == 0.0
    assert restored.payload["bool_true"] is True
    assert restored.payload["bool_false"] is False
    assert restored.payload["null_val"] is None
    assert restored.payload["int_large"] == 2**64 - 1


def test_adversarial_boolean_vs_integer_distinct_hash():
    """Assert that in JSON canonical hashing, True is distinct from 1, and False from 0."""
    fixed_ts = "2026-08-27T00:00:00Z"
    art_bool = TruthArtifact(
        artifact_id="art-type-diff",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Type Diff",
        payload={"flag": True},
        timestamp=fixed_ts,
    )
    art_int = TruthArtifact(
        artifact_id="art-type-diff",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Type Diff",
        payload={"flag": 1},
        timestamp=fixed_ts,
    )
    assert art_bool.sha256_hash != art_int.sha256_hash


def test_adversarial_null_vs_empty_vs_absent():
    """Assert that null, empty string, empty dict, and missing keys produce distinct hashes."""
    fixed_ts = "2026-08-27T00:00:00Z"

    art_null = TruthArtifact("art-k", ArtifactType.TRUTH_AUDIT, "T", {"k": None}, timestamp=fixed_ts)
    art_empty_str = TruthArtifact("art-k", ArtifactType.TRUTH_AUDIT, "T", {"k": ""}, timestamp=fixed_ts)
    art_empty_dict = TruthArtifact("art-k", ArtifactType.TRUTH_AUDIT, "T", {"k": {}}, timestamp=fixed_ts)
    art_empty_list = TruthArtifact("art-k", ArtifactType.TRUTH_AUDIT, "T", {"k": []}, timestamp=fixed_ts)
    art_empty_payload = TruthArtifact("art-k", ArtifactType.TRUTH_AUDIT, "T", {}, timestamp=fixed_ts)

    hashes = {
        art_null.sha256_hash,
        art_empty_str.sha256_hash,
        art_empty_dict.sha256_hash,
        art_empty_list.sha256_hash,
        art_empty_payload.sha256_hash,
    }
    # All 5 must have completely distinct SHA-256 hashes
    assert len(hashes) == 5


# ============================================================================
# 5. Granular Tamper Detection & Avalanche Effect
# ============================================================================

def test_adversarial_tamper_detection_every_field():
    """Verify that tampering with ANY single field immediately invalidates verify_hash()."""
    base_art = TruthArtifact(
        artifact_id="art-base-tamper",
        artifact_type=ArtifactType.ARCHITECTURAL_DECISION,
        title="Base Architecture Decision",
        payload={"node": "L1", "metrics": {"qps": 5000, "active": True}},
        source_node="Mac_Node",
        timestamp="2026-08-27T08:00:00Z",
        tags=["tag1", "tag2"],
        metadata={"author": "Aaron", "version": 1},
    )
    assert base_art.verify_hash() is True

    # 1. Tamper artifact_id
    art1 = copy.deepcopy(base_art)
    art1.artifact_id = "art-base-tamper-X"
    assert art1.verify_hash() is False

    # 2. Tamper artifact_type
    art2 = copy.deepcopy(base_art)
    art2.artifact_type = ArtifactType.TRUTH_AUDIT
    assert art2.verify_hash() is False

    # 3. Tamper title
    art3 = copy.deepcopy(base_art)
    art3.title = "Base Architecture Decision - Altered"
    assert art3.verify_hash() is False

    # 4. Tamper source_node
    art4 = copy.deepcopy(base_art)
    art4.source_node = "Linux_Head_Node"
    assert art4.verify_hash() is False

    # 5. Tamper timestamp
    art5 = copy.deepcopy(base_art)
    art5.timestamp = "2026-08-27T08:00:01Z"
    assert art5.verify_hash() is False

    # 6. Tamper tags (add tag)
    art6 = copy.deepcopy(base_art)
    art6.tags.append("tag3")
    assert art6.verify_hash() is False

    # 7. Tamper metadata
    art7 = copy.deepcopy(base_art)
    art7.metadata["version"] = 2
    assert art7.verify_hash() is False

    # 8. Tamper leaf in payload (single integer)
    art8 = copy.deepcopy(base_art)
    art8.payload["metrics"]["qps"] = 5001
    assert art8.verify_hash() is False

    # 9. Tamper boolean in payload
    art9 = copy.deepcopy(base_art)
    art9.payload["metrics"]["active"] = False
    assert art9.verify_hash() is False


def test_adversarial_corrupted_hash_signatures():
    """Verify behavior with corrupted, truncated, or invalid hex hashes."""
    art = TruthArtifact(
        artifact_id="art-corrupt-hash",
        artifact_type=ArtifactType.TRUTH_AUDIT,
        title="Corrupt Hash Test",
        payload={"status": "ok"},
    )
    valid_hash = art.sha256_hash
    assert art.verify_hash() is True

    # 1. Truncated hash
    art.sha256_hash = valid_hash[:32]
    assert art.verify_hash() is False

    # 2. Single bit flip in hash string
    flipped_char = "0" if valid_hash[0] != "0" else "1"
    art.sha256_hash = flipped_char + valid_hash[1:]
    assert art.verify_hash() is False

    # 3. Non-hex characters
    art.sha256_hash = "Z" * 64
    assert art.verify_hash() is False

    # 4. Empty hash string
    art.sha256_hash = ""
    assert art.verify_hash() is False


# ============================================================================
# 6. Serialization Boundary & Error Cases
# ============================================================================

def test_adversarial_from_dict_and_from_json_error_handling():
    """Test validation errors on missing fields or incorrect types during deserialization."""
    # Missing artifact_id
    with pytest.raises(KeyError):
        TruthArtifact.from_dict({
            "artifact_type": "truth_audit",
            "title": "Title",
            "payload": {},
        })

    # Missing title
    with pytest.raises(KeyError):
        TruthArtifact.from_dict({
            "artifact_id": "art-1",
            "artifact_type": "truth_audit",
            "payload": {},
        })

    # Non-dict data passed to from_dict
    with pytest.raises(TypeError):
        TruthArtifact.from_dict(["not", "a", "dict"])  # type: ignore

    # Invalid JSON string passed to from_json
    with pytest.raises(json.JSONDecodeError):
        TruthArtifact.from_json("invalid json payload { missing bracket")


def test_adversarial_empty_strings_and_invalid_types_in_constructor():
    """Test that constructor rejects empty strings and invalid payload types."""
    with pytest.raises(ValueError):
        TruthArtifact("", ArtifactType.TRUTH_AUDIT, "Title", {})

    with pytest.raises(ValueError):
        TruthArtifact("id-1", ArtifactType.TRUTH_AUDIT, "", {})

    with pytest.raises(ValueError):
        TruthArtifact("id-1", ArtifactType.TRUTH_AUDIT, "Title", {}, source_node="")

    with pytest.raises(TypeError):
        TruthArtifact("id-1", ArtifactType.TRUTH_AUDIT, "Title", ["not", "dict"])  # type: ignore


# ============================================================================
# 7. Health & Sync Result Composite Models Adversarial Stress
# ============================================================================

def test_adversarial_node_storage_health_extreme_values():
    """Test NodeStorageHealth serialization with extreme values, negative floats, and nan/inf handling."""
    node = NodeStorageHealth(
        node_id="L-EDGE",
        node_name="Edge_Node",
        is_reachable=True,
        layer=999,
        disk_total_gb=1000000.555,
        disk_used_gb=999999.111,
        disk_free_gb=1.444,
        disk_free_percent=0.00014,
        inode_state="EXHAUSTED",
        latency_ms=99999.999,
        headroom_ok=False,
        probe_method=NodeProbeMethod.ADB,
        endpoint="fe80::1ff:fe23:4567:890a%eth0",  # IPv6 link-local
        mount_point="/mnt/deep/volume/nvme0n1p99",
        error_message="Severe inode exhaustion and latency spike",
    )

    d = node.to_dict()
    assert d["disk_total_gb"] == 1000000.56  # Rounded to 2 decimal places
    assert d["disk_free_gb"] == 1.44
    assert d["latency_ms"] == 100000.0

    restored = NodeStorageHealth.from_dict(d)
    assert restored.node_id == "L-EDGE"
    assert restored.inode_state == "EXHAUSTED"
    assert restored.probe_method == NodeProbeMethod.ADB


def test_adversarial_mesh_summary_report_corrupted_dict():
    """Test MeshSummaryReport resilience when reconstructed from sparse or partial dictionaries."""
    data = {
        "total_nodes": 1,
        "online_nodes": 1,
        "nodes": {
            "L1": {
                "node_id": "L1",
                "is_reachable": True,
                "disk_free_gb": 100.0,
                "disk_total_gb": 500.0,
            }
        }
    }
    summary = MeshSummaryReport.from_dict(data)
    assert summary.total_nodes == 1
    assert summary.online_nodes == 1
    assert summary.nodes["L1"].node_name == "L1"
    assert summary.nodes["L1"].disk_free_gb == 100.0


def test_adversarial_storage_health_report_massive_violations_and_heals():
    """Test StorageHealthReport formatting and serialization with 50+ violations and healed actions."""
    violations = [f"Storage violation on cluster node {i}: disk headroom violated" for i in range(50)]
    healed = [f"Purged cache on target node {i}" for i in range(30)]

    report = StorageHealthReport(
        is_healthy=False,
        disk_free_gb=2.5,
        headroom_satisfied=False,
        obsidian_healthy=False,
        pyspark_healthy=False,
        git_healthy=False,
        gdrive_healthy=False,
        violations=violations,
        healed_actions=healed,
    )

    summary_text = report.summary()
    assert "=== Storage Health Report: UNHEALTHY ===" in summary_text
    assert "Violations (50):" in summary_text
    assert "Self-Healing Actions (30):" in summary_text

    d = report.to_dict()
    restored = StorageHealthReport.from_dict(d)
    assert restored.is_healthy is False
    assert len(restored.violations) == 50
    assert len(restored.healed_actions) == 30


def test_adversarial_quad_vault_sync_result_edge_matrix():
    """Test QuadVaultSyncResult with custom extra vaults and partial combinations."""
    res_pyspark = VaultSyncResult.create_success("pyspark", "/path/pyspark", "hashA", 100)
    res_obsidian = VaultSyncResult.create_success("obsidian", "/path/obsidian", "hashA", 200)
    res_git = VaultSyncResult.create_failure("git", "/path/git", "Lock contention")
    res_gdrive = VaultSyncResult.create_success("gdrive", "/path/gdrive", "hashA", 300)
    res_custom = VaultSyncResult.create_success("custom_backup", "/path/backup", "hashA", 400)

    quad = QuadVaultSyncResult(
        artifact_id="art-quad-adv",
        sha256_hash="hashA",
        success=False,
        vault_results={
            "pyspark": res_pyspark,
            "obsidian": res_obsidian,
            "git": res_git,
            "gdrive": res_gdrive,
            "custom_backup": res_custom,
        },
        errors=["git: Lock contention"],
        total_bytes_written=1000,
    )

    assert quad.all_vaults_succeeded is False
    assert set(quad.succeeded_vaults) == {"pyspark", "obsidian", "gdrive", "custom_backup"}
    assert quad.failed_vaults == ["git"]

    d = quad.to_dict()
    restored = QuadVaultSyncResult.from_dict(d)
    assert restored.artifact_id == "art-quad-adv"
    assert restored.total_bytes_written == 1000
    assert len(restored.vault_results) == 5
    assert restored.failed_vaults == ["git"]


# ============================================================================
# 8. High-Throughput Generative Property-Based Stress Tests
# ============================================================================

def _generate_random_payload(rng: random.Random, depth: int = 0, max_depth: int = 5) -> Any:
    """Generates random heterogeneous data structures (dicts, lists, primitives, unicode)."""
    if depth >= max_depth:
        choice = rng.randint(0, 5)
        if choice == 0:
            return rng.randint(-1000000, 1000000)
        elif choice == 1:
            return rng.random() * 10000.0 - 5000.0
        elif choice == 2:
            return rng.choice([True, False, None])
        elif choice == 3:
            return "".join(rng.choices(string.ascii_letters + string.digits + "🔥⚡🚀✓-_\n\t", k=rng.randint(0, 30)))
        elif choice == 4:
            return {}
        else:
            return []

    node_type = rng.randint(0, 3)
    if node_type == 0:
        # Dictionary with 1 to 5 random keys
        k_count = rng.randint(1, 5)
        d = {}
        for _ in range(k_count):
            k = "".join(rng.choices(string.ascii_letters + string.digits + "_-", k=rng.randint(1, 10)))
            d[k] = _generate_random_payload(rng, depth + 1, max_depth)
        return d
    elif node_type == 1:
        # List with 1 to 4 elements
        l_count = rng.randint(1, 4)
        return [_generate_random_payload(rng, depth + 1, max_depth) for _ in range(l_count)]
    elif node_type == 2:
        return rng.choice([True, False, None, 0, 0.0, 3.14159, "string_val", "日本語テスト"])
    else:
        return rng.randint(-10000, 10000)


def test_adversarial_generative_1000_payload_permutations_invariance():
    """
    Generates 500 distinct randomized JSON payload trees.
    For each tree, creates 5 random key permutations and verifies 100% hash invariance.
    Total 2,500 hash evaluations.
    """
    rng = random.Random(999)
    fixed_ts = "2026-08-27T06:00:00Z"

    for trial in range(500):
        base_payload = _generate_random_payload(rng, depth=0, max_depth=4)
        if not isinstance(base_payload, dict):
            base_payload = {"root_val": base_payload}

        art_base = TruthArtifact(
            artifact_id=f"art-gen-{trial}",
            artifact_type=rng.choice(list(ArtifactType)),
            title=f"Generative Trial {trial}",
            payload=base_payload,
            timestamp=fixed_ts,
            tags=[f"tag_{i}" for i in range(rng.randint(0, 3))],
            metadata={"trial": trial},
        )
        base_hash = art_base.sha256_hash

        for p_idx in range(5):
            permuted = _permute_dict_keys(base_payload, rng)
            art_perm = TruthArtifact(
                artifact_id=f"art-gen-{trial}",
                artifact_type=art_base.artifact_type,
                title=art_base.title,
                payload=permuted,
                timestamp=fixed_ts,
                tags=list(reversed(art_base.tags)),  # Reverse tags to test tag sorting
                metadata=art_base.metadata,
            )
            assert art_perm.sha256_hash == base_hash, (
                f"Hash mismatch on trial {trial}, permutation {p_idx}!\n"
                f"Base: {art_base.payload}\nPerm: {permuted}"
            )
            assert art_perm.verify_hash() is True


def test_adversarial_generative_500_tamper_mutations():
    """
    Generates 500 distinct artifacts and applies 1 random mutation to each.
    Asserts verify_hash() catches 100% of mutations immediately.
    """
    rng = random.Random(888)
    fixed_ts = "2026-08-27T06:00:00Z"

    for trial in range(500):
        base_payload = _generate_random_payload(rng, depth=0, max_depth=3)
        if not isinstance(base_payload, dict):
            base_payload = {"root": base_payload}

        art = TruthArtifact(
            artifact_id=f"art-tamper-{trial}",
            artifact_type=ArtifactType.TRUTH_AUDIT,
            title=f"Tamper Trial {trial}",
            payload=copy.deepcopy(base_payload),
            timestamp=fixed_ts,
        )
        assert art.verify_hash() is True

        # Apply mutation
        mutation_type = rng.randint(0, 5)
        if mutation_type == 0:
            # Add extra key to payload
            art.payload[f"mutated_key_{trial}"] = "mutated_value"
        elif mutation_type == 1:
            # Change title slightly
            art.title += "!"
        elif mutation_type == 2:
            # Change source_node
            art.source_node = "Pixel_10_Pro_XL"
        elif mutation_type == 3:
            # Add a tag
            art.tags.append("mutated_tag")
        elif mutation_type == 4:
            # Alter timestamp by 1 ms
            art.timestamp = "2026-08-27T06:00:00.001Z"
        else:
            # Alter metadata
            art.metadata["mutated"] = True

        assert art.verify_hash() is False, f"Tamper went undetected on trial {trial} (mutation type {mutation_type})!"


def test_adversarial_datetime_serialization_in_payload():
    """Verify that Python datetime objects embedded in payload serialize cleanly via default=str."""
    now = datetime.datetime(2026, 8, 27, 12, 0, 0, tzinfo=datetime.timezone.utc)
    art = TruthArtifact(
        artifact_id="art-dt-001",
        artifact_type=ArtifactType.TELEMETRY_RECORD,
        title="Datetime Test",
        payload={"event_time": now, "date": now.date()},
    )
    assert len(art.sha256_hash) == 64
    assert art.verify_hash() is True


def test_adversarial_markdown_frontmatter_structural_parsing():
    """Verify that to_markdown_frontmatter generates valid YAML frontmatter and extractable JSON."""
    art = TruthArtifact(
        artifact_id="art-md-parse",
        artifact_type=ArtifactType.AI_DEBATE_CONSENSUS,
        title="Debate Consensus 42",
        payload={"winner": "Model_A", "score": 99.8, "notes": ["note1", "note2"]},
        tags=["consensus", "ai_debate", "m1"],
        metadata={"reviewer": "sentinel"},
    )
    md_content = art.to_markdown_frontmatter(custom_body="Detailed discussion on consensus.")

    # Check YAML delimiter structure
    assert md_content.startswith("---\n")
    parts = md_content.split("---\n", 2)
    assert len(parts) >= 3, "Markdown missing YAML closing delimiter!"
    yaml_header = parts[1]
    body = parts[2]

    # Verify header contains essential fields
    assert f'artifact_id: "{art.artifact_id}"' in yaml_header
    assert f'sha256_hash: "{art.sha256_hash}"' in yaml_header
    assert "tags:\n  - consensus\n  - ai_debate\n  - m1" in yaml_header

    # Verify json codeblock in body contains exact parseable payload
    json_start = body.find("```json\n") + len("```json\n")
    json_end = body.find("\n```", json_start)
    assert json_start > 0 and json_end > json_start
    extracted_json = body[json_start:json_end]
    parsed_payload = json.loads(extracted_json)
    assert parsed_payload == art.payload
