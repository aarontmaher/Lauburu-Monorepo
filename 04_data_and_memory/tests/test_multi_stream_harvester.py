#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E & Unit Test Suite: Multi-Stream LoRA Harvester & Rule #0 Zero-Mock Sanitizer
================================================================================
Test Target: 04_data_and_memory/multi_stream_harvester.py & tri_vault_sink.py
Covers:
- Feature 1: Multi-Stream Dataset Harvesting (Tier 1 & Tier 2)
- Feature 2: Rule #0 Zero-Mock Sanitization (Tier 1 & Tier 2)
- Feature 3: Dual-Tier Storage Sync (Tier 1 & Tier 2)
Test Framework: pytest
Zero-Mock Compliance: 100% genuine inputs, deterministic verification, zero facade mocks.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, List

import pytest

# Ensure module path is accessible
MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from multi_stream_harvester import (
    MultiStreamHarvester,
    DEBATE_STREAM_TOPICS,
    CODE_DIFF_STREAM_TOPICS,
    MATH_PROOF_STREAM_TOPICS,
    RECOVERY_ACTION_STREAM_TOPICS,
    TRAINING_GAME_STREAM_TOPICS,
)
from tri_vault_sink import (
    TriVaultSink,
    verify_zero_mock_compliance,
    check_storage_health,
    get_daily_verified_count,
    append_verified_pair,
)


@pytest.fixture
def temp_workspace():
    """Provides an isolated temporary workspace directory for test datasets."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_harvester_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def isolated_harvester(temp_workspace):
    """Provides a MultiStreamHarvester instance pointing to an isolated temp dataset."""
    target_file = temp_workspace / "test_ai_training_game_dataset.jsonl"
    sink = TriVaultSink(
        lora_dir=temp_workspace / "lora_datasets",
        obsidian_dir=temp_workspace / "obsidian_vault" / "01_DEBATES",
        secondary_lora_dir=temp_workspace / "secondary_lora",
        secondary_obsidian_dir=temp_workspace / "secondary_obsidian",
        enforce_rule_zero=True,
    )
    harvester = MultiStreamHarvester(
        workspace_root=temp_workspace,
        target_dataset=target_file,
        tri_vault_sink=sink,
    )
    return harvester


# ===========================================================================
# FEATURE 1: Multi-Stream Dataset Harvesting (Tiers 1 & 2)
# ===========================================================================

class TestFeature1MultiStreamHarvesting:
    """Tests 5 authentic stream harvesting functions and batch generation."""

    def test_harvest_debate_stream_valid_schema(self, isolated_harvester):
        """Tier 1.1: Verify Stream 1 (Tri-Orchestrator Debate) produces compliant structure."""
        record = isolated_harvester.harvest_debate_stream(idx=0)
        assert record is not None
        assert record["domain"] == "tri_orchestrator_debate"
        assert "Dynamic RAM Governor" in record["instruction"]
        assert "perspectives" in record["input"]
        assert record["truth_verified"] is True
        assert record["truth_compliance_pct"] == 100.0
        assert record["zero_mock"] is True
        assert isolated_harvester.target_dataset.exists()

    def test_harvest_code_diff_stream_valid_schema(self, isolated_harvester):
        """Tier 1.2: Verify Stream 2 (AST Code Diffs) produces compliant structure."""
        record = isolated_harvester.harvest_code_diff_stream(idx=0)
        assert record is not None
        assert record["domain"] == "code_refactor_ast_diff"
        assert "safe_append_jsonl" in record["output"] or "safe_append_jsonl" in record["chosen_response"]
        assert record["truth_verified"] is True
        assert record["reward"] >= 1.0

    def test_harvest_math_proof_stream_valid_schema(self, isolated_harvester):
        """Tier 1.3: Verify Stream 3 (Mathematical Proofs) produces verified inverse-variance proofs."""
        record = isolated_harvester.harvest_math_proof_stream(idx=0)
        assert record is not None
        assert record["domain"] == "mathematical_proof_derivation"
        assert "97.52%" in record["output"] or "Inverse variance" in record["output"] or "W_TB4" in record["output"]
        assert record["truth_verified"] is True
        assert record["reward"] >= 1.5

    def test_harvest_recovery_action_stream_valid_schema(self, isolated_harvester):
        """Tier 1.4: Verify Stream 4 (Autonomic Self-Healing) produces valid recovery commands."""
        record = isolated_harvester.harvest_recovery_action_stream(idx=0)
        assert record is not None
        assert record["domain"] == "autonomic_recovery_self_healing"
        assert "drop_caches" in record["output"] or "drop_caches" in record["chosen_response"]
        assert record["truth_verified"] is True

    def test_harvest_training_game_stream_valid_schema(self, isolated_harvester):
        """Tier 1.5: Verify Stream 5 (AI Training Game Duels) produces valid duel records."""
        record = isolated_harvester.harvest_training_game_stream(idx=0)
        assert record is not None
        assert record["game_mode"] in ["SMOLAGENTS_PYTHON_DUEL", "CANONICAL_PORT_4000_DEFENSE"]
        assert "chosen_response" in record
        assert record["zero_mock"] is True

    def test_harvest_all_5_streams_simultaneously(self, isolated_harvester):
        """Tier 2.1: Verify harvest_all_streams() gathers all 5 streams in a single call."""
        results = isolated_harvester.harvest_all_streams()
        expected_streams = {"debate", "code_diff", "math_proof", "recovery", "training_game"}
        assert set(results.keys()) == expected_streams
        for s_name, records in results.items():
            assert len(records) == 1
            assert records[0]["truth_verified"] is True

    def test_generate_batch_satisfies_daily_quota(self, isolated_harvester):
        """Tier 2.2: Verify generate_batch appends requested count cleanly across all streams."""
        batch_size = 25
        count = isolated_harvester.generate_batch(count=batch_size)
        assert count == batch_size

        # Verify dataset line count matches exactly
        with open(isolated_harvester.target_dataset, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == batch_size

    def test_harvest_from_file_with_limit_and_malformed_lines(self, isolated_harvester, temp_workspace):
        """Tier 2.3: Verify file ingestion filters invalid lines and enforces limit."""
        source_jsonl = temp_workspace / "source_input.jsonl"
        valid_rec1 = {
            "instruction": "Test instruction 1",
            "input": "context 1",
            "output": "solution 1",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        valid_rec2 = {
            "instruction": "Test instruction 2",
            "input": "context 2",
            "output": "solution 2",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }

        with open(source_jsonl, "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_rec1) + "\n")
            f.write("\n")  # Empty line
            f.write("MALFORMED JSON LINE\n")
            f.write(json.dumps(valid_rec2) + "\n")
            f.write(json.dumps({"prompt": "extra", "output": "extra", "truth_verified": True}) + "\n")

        ingested = isolated_harvester.harvest_from_file(source_jsonl, limit=2)
        assert ingested == 2

    def test_harvest_stream_invalid_type_fallback(self, isolated_harvester):
        """Tier 2.4: Verify passing unknown stream name safely defaults to debate stream."""
        rec = isolated_harvester.harvest_stream("unknown_arbitrary_stream")
        assert rec is not None
        assert rec["domain"] == "tri_orchestrator_debate"

    def test_get_dataset_stats_calculations(self, isolated_harvester):
        """Tier 2.5: Verify get_dataset_stats() accurately calculates statistics and quotas."""
        isolated_harvester.generate_batch(count=10)
        stats = isolated_harvester.get_dataset_stats()
        assert stats["total_pairs"] == 10
        assert stats["verified_24h_pairs"] == 10
        assert stats["file_size_bytes"] > 0
        assert stats["quota_target_daily"] == 500
        assert stats["quota_satisfied"] is False  # 10 < 500


# ===========================================================================
# FEATURE 2: Rule #0 Zero-Mock Sanitization (Tiers 1 & 2)
# ===========================================================================

class TestFeature2ZeroMockSanitization:
    """Tests strict Rule #0 Zero-Mock validator and sanitization filters."""

    def test_sanitize_record_valid_zero_mock_record(self, isolated_harvester):
        """Tier 1.1: Valid empirical record passes sanitization."""
        valid_record = {
            "instruction": "Derive TB4 inverse-variance weights",
            "input": "RTT 0.27ms vs 1.85ms",
            "output": "W_TB4 = 97.52%",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        sanitized = isolated_harvester.sanitize_record(valid_record)
        assert sanitized is not None
        assert sanitized["truth_verified"] is True
        assert sanitized["truth_compliance_pct"] == 100.0
        assert sanitized["zero_mock"] is True

    def test_sanitize_record_rejects_negative_latency(self, isolated_harvester):
        """Tier 1.2: Rule #0 rejects negative latency."""
        invalid_record = {
            "instruction": "Test latency",
            "output": "Result",
            "latency_ms": -15.5
        }
        sanitized = isolated_harvester.sanitize_record(invalid_record)
        assert sanitized is None

    def test_sanitize_record_rejects_negative_tokens(self, isolated_harvester):
        """Tier 1.3: Rule #0 rejects negative token counts."""
        invalid_record = {
            "instruction": "Test tokens",
            "output": "Result",
            "tokens_generated": -100
        }
        sanitized = isolated_harvester.sanitize_record(invalid_record)
        assert sanitized is None

    def test_sanitize_record_rejects_explicit_unverified_flag(self, isolated_harvester):
        """Tier 1.4: Rule #0 rejects explicitly unverified records."""
        rec = {
            "instruction": "Some task",
            "output": "Output",
            "meta": {"truth_verified": False}
        }
        is_valid, msg = verify_zero_mock_compliance(rec)
        assert is_valid is False
        assert "Rule #0 Violation" in msg

    def test_sanitize_record_rejects_dummy_zero_arrays(self, isolated_harvester):
        """Tier 1.5: Rule #0 rejects dummy zero arrays [0, 0, 0, ...]."""
        rec = {
            "instruction": "Check ECG stream",
            "output": "ECG array detected",
            "telemetry_stream": [0, 0, 0, 0, 0]
        }
        is_valid, msg = verify_zero_mock_compliance(rec)
        assert is_valid is False
        assert "Dummy zero array" in msg

    def test_sanitize_record_rejects_mock_placeholder_strings(self, isolated_harvester):
        """Tier 2.1: Rule #0 rejects strings containing mock/fake keywords."""
        rec = {
            "instruction": "Perform audit",
            "output": "Here is some fake_data for testing",
            "truth_verified": True
        }
        is_valid, msg = verify_zero_mock_compliance(rec)
        assert is_valid is False
        assert "Mock placeholder string detected" in msg

    def test_sanitize_record_rejects_empty_prompt_and_action(self, isolated_harvester):
        """Tier 2.2: Rule #0 rejects empty prompts/instructions."""
        rec = {
            "output": "Orphaned output without prompt",
            "truth_verified": True
        }
        is_valid, msg = verify_zero_mock_compliance(rec)
        assert is_valid is False
        assert "Empty or missing prompt" in msg

    def test_sanitize_record_rejects_non_dict_inputs(self, isolated_harvester):
        """Tier 2.3: verify_zero_mock_compliance gracefully handles non-dict types."""
        assert verify_zero_mock_compliance(["not", "a", "dict"])[0] is False
        assert verify_zero_mock_compliance("string_input")[0] is False
        assert verify_zero_mock_compliance(None)[0] is False
        assert isolated_harvester.sanitize_record(None) is None
        assert isolated_harvester.sanitize_record("raw_string") is None

    def test_sanitize_record_auto_injects_timestamps_if_missing(self, isolated_harvester):
        """Tier 2.4: Sanitizer auto-injects float and ISO-8601 timestamps if missing."""
        rec = {
            "instruction": "Task missing timestamps",
            "output": "Valid output response"
        }
        sanitized = isolated_harvester.sanitize_record(rec)
        assert sanitized is not None
        assert "timestamp" in sanitized
        assert isinstance(sanitized["timestamp"], float)
        assert "timestamp_utc" in sanitized
        assert sanitized["timestamp_utc"].endswith("Z")

    def test_sanitize_record_truth_compliance_pct_boundary(self, isolated_harvester):
        """Tier 2.5: Compliance percentage must be strictly 100.0%."""
        rec_99 = {
            "instruction": "Partial compliance test",
            "output": "Output",
            "truth_compliance_pct": 99.9
        }
        is_valid, msg = verify_zero_mock_compliance(rec_99)
        assert is_valid is False
        assert "Truth compliance is 99.9%" in msg

        rec_100 = {
            "instruction": "Full compliance test",
            "output": "Output",
            "truth_compliance_pct": 100.0
        }
        is_valid, msg = verify_zero_mock_compliance(rec_100)
        assert is_valid is True


# ===========================================================================
# FEATURE 3: Dual-Tier Storage Sync & Atomic Persistence (Tiers 1 & 2)
# ===========================================================================

class TestFeature3DualTierStorageSync:
    """Tests atomic POSIX file persistence, thread safety, and directory fallbacks."""

    def test_safe_append_jsonl_atomic_fsync(self, temp_workspace):
        """Tier 1.1: safe_append_jsonl appends valid JSON line and flushes to disk."""
        sink = TriVaultSink(lora_dir=temp_workspace)
        target = temp_workspace / "test_append.jsonl"
        data = {"key": "value_1", "step": 10}
        success = sink.safe_append_jsonl(target, data)
        assert success is True
        assert target.exists()

        with open(target, "r", encoding="utf-8") as f:
            read_data = json.loads(f.read().strip())
        assert read_data == data

    def test_append_verified_pair_updates_daily_count(self, temp_workspace):
        """Tier 1.2: append_verified_pair atomically increments daily count."""
        sink = TriVaultSink(lora_dir=temp_workspace)
        target = temp_workspace / "verified_pairs.jsonl"

        pair = {
            "instruction": "Test instruction",
            "input": "Test input",
            "output": "Test output",
            "timestamp": time.time(),
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        sink.append_verified_pair(target, pair)
        count = sink.get_daily_verified_count(target)
        assert count == 1

    def test_tri_vault_sink_resolve_active_lora_dir_fallback(self, temp_workspace):
        """Tier 1.3: Resolves active writable directory, falling back when unwritable."""
        unwritable_dir = Path("/nonexistent_root_dir_12345/lora")
        secondary_dir = temp_workspace / "secondary_lora"
        sink = TriVaultSink(lora_dir=unwritable_dir, secondary_lora_dir=secondary_dir)

        resolved = sink.resolve_active_lora_dir()
        assert resolved == secondary_dir
        assert resolved.exists()

    def test_tri_vault_sink_check_storage_health_metrics(self, temp_workspace):
        """Tier 1.4: Storage health check returns complete invariant diagnostics."""
        primary = temp_workspace / "primary"
        secondary = temp_workspace / "secondary"
        health = check_storage_health(primary, secondary, min_free_gb=1.0)

        assert health["is_healthy"] is True
        assert health["primary_accessible"] is True
        assert health["secondary_accessible"] is True
        assert health["free_disk_gb"] > 0.0
        assert health["active_target_dir"] == primary

    def test_export_dpo_pair_serialization_schema(self, temp_workspace):
        """Tier 1.5: export_dpo_pair serializes HuggingFace TRL DPO format."""
        sink = TriVaultSink(lora_dir=temp_workspace)
        trial = {
            "trial_id": "trial_dpo_001",
            "prompt": "Evaluate TB4 vs 1Gbps LAN tensor streaming",
            "winner_id": "qwen_25_coder",
            "winner_alias": "alpha",
            "judicial_rationale": "TB4 provides 0.277ms latency delivering 22.3x speedup.",
            "pairwise_matches": [
                {"model_a_id": "qwen_25_coder", "model_b_id": "naive_model", "winner_id": "qwen_25_coder"}
            ],
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }

        dpo_record = sink.export_dpo_pair(trial, target_filename="test_dpo.jsonl")
        assert dpo_record["prompt"] == trial["prompt"]
        assert "TB4 provides 0.277ms" in dpo_record["chosen"]
        assert "Sub-optimal reasoning solution" in dpo_record["rejected"]
        assert dpo_record["meta"]["winner"] == "qwen_25_coder"

    def test_concurrent_multi_threaded_appends(self, temp_workspace):
        """Tier 2.1: Concurrent multi-threaded appends maintain dataset integrity with 0 corruptions."""
        sink = TriVaultSink(lora_dir=temp_workspace)
        target = temp_workspace / "concurrent_test.jsonl"
        num_threads = 10
        appends_per_thread = 20
        total_expected = num_threads * appends_per_thread

        def worker_append(thread_id: int):
            for i in range(appends_per_thread):
                rec = {
                    "thread_id": thread_id,
                    "seq": i,
                    "timestamp": time.time(),
                    "instruction": f"Instruction from thread {thread_id} item {i}",
                    "output": f"Output from thread {thread_id} item {i}",
                    "truth_verified": True,
                    "truth_compliance_pct": 100.0,
                    "zero_mock": True
                }
                sink.safe_append_jsonl(target, rec)

        threads = [threading.Thread(target=worker_append, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Read back and verify exact line count and parseability
        with open(target, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == total_expected

    def test_atomic_write_file_replaces_cleanly(self, temp_workspace):
        """Tier 2.2: atomic_write_file writes via temp file and replaces without residue."""
        sink = TriVaultSink(lora_dir=temp_workspace)
        target = temp_workspace / "atomic_doc.md"
        content = "# Markdown Test\n[[CANONICAL_PROJECT_AND_STORAGE_RULE]]"

        success = sink.atomic_write_file(target, content)
        assert success is True
        assert target.read_text(encoding="utf-8") == content

        # Overwrite atomically
        new_content = "# Updated Markdown Test\n[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]"
        sink.atomic_write_file(target, new_content)
        assert target.read_text(encoding="utf-8") == new_content

    def test_gdrive_unmounted_fallback_directory_routing(self, temp_workspace):
        """Tier 2.3: Unmounted GDrive path falls back to secondary without unhandled errors."""
        unmounted_gdrive = Path("/Volumes/Google Drive Nonexistent/My Drive")
        local_fallback = temp_workspace / "gdrive_fallback"
        sink = TriVaultSink(lora_dir=unmounted_gdrive, secondary_lora_dir=local_fallback)

        trial = {
            "trial_id": "trial_fallback_test",
            "prompt": "Test GDrive fallback",
            "winner_id": "model_alpha",
            "judicial_rationale": "Fallback verified.",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        res = sink.export_dpo_pair(trial, target_filename="continuous_lora_dataset.jsonl")
        assert res is not None
        assert (local_fallback / "continuous_lora_dataset.jsonl").exists()

    def test_corrupted_dataset_recovery_in_get_daily_count(self, temp_workspace):
        """Tier 2.4: get_daily_verified_count ignores corrupt rows and ancient rows."""
        sink = TriVaultSink(lora_dir=temp_workspace)
        target = temp_workspace / "mixed_dataset.jsonl"

        now = time.time()
        valid_row = json.dumps({
            "instruction": "Valid item",
            "output": "Output",
            "timestamp": now,
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        })
        ancient_row = json.dumps({
            "instruction": "Ancient item",
            "output": "Output",
            "timestamp": 1000.0,  # Epoch 1970 (not recent era > 1700000000 and not within 24h)
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        })

        with open(target, "w", encoding="utf-8") as f:
            f.write(valid_row + "\n")
            f.write("CORRUPT_NOT_JSON\n")
            f.write(ancient_row + "\n")
            f.write(valid_row + "\n")

        count = sink.get_daily_verified_count(target)
        assert count == 2  # 2 valid recent rows

    def test_dataset_stats_with_nonexistent_file(self, temp_workspace):
        """Tier 2.5: Harvester get_dataset_stats returns clean zeros on non-existent dataset file."""
        nonexistent = temp_workspace / "does_not_exist.jsonl"
        harvester = MultiStreamHarvester(target_dataset=nonexistent)
        stats = harvester.get_dataset_stats()
        assert stats["total_pairs"] == 0
        assert stats["verified_24h_pairs"] == 0
        assert stats["file_size_bytes"] == 0
        assert stats["quota_satisfied"] is False
