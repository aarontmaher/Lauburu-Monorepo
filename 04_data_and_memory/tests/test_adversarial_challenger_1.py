#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress-Test Suite: Challenger 1 for Lauburu Live Training Automation Engine
======================================================================================
Subsystem: 04_data_and_memory/tests/test_adversarial_challenger_1.py
Role: Empirical Challenger 1 (Adversarial Critic & Domain Specialist)

Comprehensive empirical stress-testing across 5 critical dimensions:
1. Malformed / Corrupted JSONL records & stream disruption
2. Simulated / Mock Data Injection Attempts & Rule #0 Reject Gate
3. Stagnation Trigger Conditions (ΔC < 0.02 over 3, 5, 10 rounds) & Dynamic Substitution
4. Low NVMe Disk Headroom (< 10.0 GB threshold) & Pre-Flight Cache Purging
5. RAM Governor Boundary Edge Cases & Over-Allocation near 21.6 GB Cap
"""

import os
import sys
import json
import time
import math
import shutil
import tempfile
import socket
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import pytest

# Ensure module path is accessible
MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from multi_stream_harvester import MultiStreamHarvester
from mlx_qlora_trainer import DynamicRamGovernor, MLXQLoRATrainer
from synthetic_debate_engine import SyntheticDebateEngine, DebateConsensusAccord
from telemetry_streamer import StorageSentinel, TelemetryStreamer
from live_training_automation_engine import LiveTrainingAutomationEngine
from tri_vault_sink import (
    TriVaultSink,
    verify_zero_mock_compliance,
    stream_loss_to_obsidian,
)


@pytest.fixture
def adversarial_env():
    """Creates an isolated temporary test workspace."""
    temp_dir = tempfile.mkdtemp(prefix="adv_challenger_test_")
    ws = Path(temp_dir)
    data_dir = ws / "04_data_and_memory"
    lora_dir = ws / "lora_datasets"
    obsidian_dir = ws / "obsidian_vault"
    tui_config = ws / "02_ai_models_and_inference" / "lauburu_tui" / "config"

    data_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    tui_config.mkdir(parents=True, exist_ok=True)

    sink = TriVaultSink(
        lora_dir=lora_dir,
        obsidian_dir=obsidian_dir / "01_DEBATES",
        enforce_rule_zero=True,
    )
    sentinel = StorageSentinel(monorepo_root=ws, min_free_gb=10.0)
    governor = DynamicRamGovernor(total_system_ram_gb=24.0, cap_pct=90.0, min_headroom_gb=2.50)
    harvester = MultiStreamHarvester(
        workspace_root=ws,
        target_dataset=data_dir / "ai_training_game_dataset.jsonl",
        tri_vault_sink=sink,
    )
    trainer = MLXQLoRATrainer(
        data_dir=data_dir,
        adapter_out_dir=ws / "adapters",
        governor=governor,
        tri_vault_sink=sink,
    )
    debate = SyntheticDebateEngine(tri_vault_sink=sink, stagnation_threshold=0.02, stagnation_turn_limit=3)
    streamer = TelemetryStreamer(monorepo_root=ws, sentinel=sentinel, tri_vault_sink=sink)

    yield {
        "workspace": ws,
        "data_dir": data_dir,
        "lora_dir": lora_dir,
        "obsidian_dir": obsidian_dir,
        "tui_config": tui_config,
        "sink": sink,
        "sentinel": sentinel,
        "governor": governor,
        "harvester": harvester,
        "trainer": trainer,
        "debate": debate,
        "streamer": streamer,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# DIMENSION 1: Malformed / Corrupted JSONL Records & Stream Disruption
# ===========================================================================

class TestAdversarialDimension1MalformedJSONL:
    """Stress-tests ingestion and recovery against corrupted and malformed inputs."""

    def test_harvester_ingests_severely_corrupted_jsonl(self, adversarial_env):
        """Feed file with truncated JSON, raw binary, non-object JSON, and valid lines."""
        harvester = adversarial_env["harvester"]
        src_file = adversarial_env["data_dir"] / "corrupted_stream.jsonl"

        corrupted_content = (
            "{\"valid\": 1, \"instruction\": \"Real task\", \"output\": \"Real output\"}\n"
            "{\"truncated\": \"bad json string without closing\n"
            "NOT_JSON_AT_ALL_JUST_RANDOM_TEXT_12345\n"
            "[1, 2, 3, 4, 5]\n"
            "\"just a raw json string\"\n"
            "null\n"
            "true\n"
            "{\"instruction\": \"Second valid task\", \"output\": \"Second valid result\"}\n"
            "{\"missing_quotes: 123\n"
        )
        src_file.write_text(corrupted_content, encoding="utf-8")

        ingested = harvester.harvest_from_file(src_file, limit=100)
        assert ingested == 2, f"Expected exactly 2 valid lines to be ingested, got {ingested}"

        # Verify output dataset contains only valid records
        target = harvester.target_dataset
        assert target.exists()
        with open(target, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 2
        assert lines[0]["instruction"] == "Real task"
        assert lines[1]["instruction"] == "Second valid task"

    def test_harvester_handles_empty_and_whitespace_files(self, adversarial_env):
        """Empty file, single newlines, and trailing spaces."""
        harvester = adversarial_env["harvester"]
        empty_file = adversarial_env["data_dir"] / "empty.jsonl"
        empty_file.write_text("   \n\n\t\n   ", encoding="utf-8")

        ingested = harvester.harvest_from_file(empty_file, limit=100)
        assert ingested == 0

    def test_harvester_handles_nonexistent_file(self, adversarial_env):
        """Gracefully returns 0 on missing file without raising exception."""
        harvester = adversarial_env["harvester"]
        missing_file = adversarial_env["data_dir"] / "does_not_exist.jsonl"
        ingested = harvester.harvest_from_file(missing_file, limit=100)
        assert ingested == 0

    def test_watermark_corruption_recovery(self, adversarial_env):
        """Corrupted watermark file recovers gracefully to 0."""
        trainer = adversarial_env["trainer"]
        wm_file = trainer.watermark_file

        # Write corrupted JSON to watermark
        wm_file.write_text("{CORRUPTED_JSON_DATA", encoding="utf-8")
        should_train, count, watermark = trainer.should_trigger_training(min_new_samples=100)
        assert watermark == 0

        # Write invalid types
        wm_file.write_text(json.dumps({"last_trained_sample_count": "NOT_AN_INTEGER"}), encoding="utf-8")
        trainer.update_watermark(500)
        assert wm_file.exists()
        with open(wm_file, "r") as f:
            data = json.load(f)
        assert data["last_trained_sample_count"] == 500

    def test_massive_payload_line_handling(self, adversarial_env):
        """Handle single record with large prompt without crashing."""
        harvester = adversarial_env["harvester"]
        src_file = adversarial_env["data_dir"] / "large_payload.jsonl"

        large_text = "A" * (1024 * 512)  # 512 KB string
        record = {
            "instruction": large_text,
            "output": "Processed large text",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "zero_mock": True
        }
        src_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

        ingested = harvester.harvest_from_file(src_file, limit=10)
        assert ingested == 1


# ===========================================================================
# DIMENSION 2: Simulated/Mock Data Injection Attempts & Rule #0 Gate
# ===========================================================================

class TestAdversarialDimension2MockInjectionGate:
    """Tests strict enforcement of Rule #0 Zero-Mock reject gate and surfaces laundering risks."""

    def test_direct_rule_zero_rejections(self):
        """Verify verify_zero_mock_compliance directly rejects all simulated patterns."""
        # Explicit mock flags
        assert verify_zero_mock_compliance({"truth_verified": False, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"zero_mock": False, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"truth_compliance_pct": 99.9, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"meta": {"truth_verified": False}, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"meta": {"truth_compliance_pct": 50.0}, "prompt": "a", "output": "b"})[0] is False

        # Negative metrics
        assert verify_zero_mock_compliance({"latency_ms": -1.0, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"tokens_generated": -10, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"meta": {"latency_ms": -0.5}, "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"latency_ms": "invalid", "prompt": "a", "output": "b"})[0] is False

        # Dummy zero arrays (length >= 3)
        assert verify_zero_mock_compliance({"weights": [0, 0, 0], "prompt": "a", "output": "b"})[0] is False
        assert verify_zero_mock_compliance({"scores": [0.0, 0.0, 0.0, 0.0], "prompt": "a", "output": "b"})[0] is False

        # Mock placeholder strings
        assert verify_zero_mock_compliance({"output": "This is a mock_dummy payload", "prompt": "a"})[0] is False
        assert verify_zero_mock_compliance({"response": "Some FAKE_DATA text", "prompt": "a"})[0] is False

        # Missing prompt or completion
        assert verify_zero_mock_compliance({"output": "only output, no prompt"})[0] is False
        assert verify_zero_mock_compliance({"prompt": "only prompt, no output"})[0] is False
        assert verify_zero_mock_compliance({})[0] is False
        assert verify_zero_mock_compliance("not a dict")[0] is False

    def test_mock_injection_with_placeholder_string_in_harvester(self, adversarial_env):
        """Attempt to ingest records containing mock_dummy string into harvester."""
        harvester = adversarial_env["harvester"]
        src = adversarial_env["data_dir"] / "injected_mocks.jsonl"

        mock_records = [
            {"instruction": "Legit task", "output": "mock_dummy_response", "truth_verified": True},
            {"instruction": "Another test", "output": "Contains FAKE_DATA_payload", "truth_verified": True},
            {"instruction": "Valid instruction", "output": "Authentic output string", "truth_verified": True},
        ]
        with open(src, "w", encoding="utf-8") as f:
            for r in mock_records:
                f.write(json.dumps(r) + "\n")

        ingested = harvester.harvest_from_file(src, limit=100)
        assert ingested == 1, f"Expected 1 valid record, got {ingested}"

    def test_mock_injection_with_zero_array_in_harvester(self, adversarial_env):
        """Attempt to ingest records containing [0, 0, 0] dummy arrays."""
        harvester = adversarial_env["harvester"]
        src = adversarial_env["data_dir"] / "injected_zero_arrays.jsonl"

        records = [
            {"instruction": "Task 1", "output": "Output 1", "dummy_array": [0, 0, 0, 0]},
            {"instruction": "Task 2", "output": "Output 2", "dummy_array": [1.0, 2.0, 3.0]},
        ]
        with open(src, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        ingested = harvester.harvest_from_file(src, limit=100)
        assert ingested == 1, f"Expected 1 valid record, got {ingested}"

    def test_sanitizer_with_negative_latency_injection(self, adversarial_env):
        """Attempt to inject negative latency record through sanitize_record."""
        harvester = adversarial_env["harvester"]
        bad_rec = {
            "instruction": "Benchmark query",
            "output": "Result",
            "latency_ms": -42.5,
        }
        sanitized = harvester.sanitize_record(bad_rec)
        assert sanitized is None, "Expected negative latency record to be rejected by sanitize_record"

    def test_remediation_sanitize_record_rejects_falsified_flags(self, adversarial_env):
        """Verify that sanitize_record rejects incoming records with false truth flags."""
        harvester = adversarial_env["harvester"]
        unverified_rec = {
            "instruction": "Unverified external prompt",
            "output": "Unverified external completion",
            "truth_verified": False,
            "zero_mock": False,
            "truth_compliance_pct": 20.0
        }
        # Direct verification rejects it
        is_valid, msg = verify_zero_mock_compliance(unverified_rec)
        assert is_valid is False

        # Harvester sanitize_record rejects and returns None
        sanitized = harvester.sanitize_record(unverified_rec)
        assert sanitized is None, "Expected unverified record to be rejected by sanitize_record"


# ===========================================================================
# DIMENSION 3: Stagnation Trigger Conditions & Dynamic Model Substitution
# ===========================================================================

class TestAdversarialDimension3StagnationDefense:
    """Stress-tests stagnation defense at ΔC < 0.02 over 3, 5, and 10 rounds."""

    def test_stagnation_detection_3_rounds_and_substitution(self, adversarial_env):
        """3 consecutive stagnant rounds (ΔC < 0.02) triggers substitution to math_72b."""
        debate = adversarial_env["debate"]
        assert debate.active_primary_model == "coder_architect"

        # Round 1: Baseline
        is_stag, _ = debate.detect_stagnation_and_substitute(0.950)
        assert is_stag is False
        assert debate.consecutive_stagnant_turns == 0

        # Round 2: Stagnant turn 1 (delta = 0.005 < 0.02)
        is_stag, _ = debate.detect_stagnation_and_substitute(0.955)
        assert is_stag is False
        assert debate.consecutive_stagnant_turns == 1

        # Round 3: Stagnant turn 2 (delta = 0.003 < 0.02)
        is_stag, _ = debate.detect_stagnation_and_substitute(0.958)
        assert is_stag is False
        assert debate.consecutive_stagnant_turns == 2

        # Round 4: Stagnant turn 3 (delta = 0.004 < 0.02) -> Triggers substitution!
        is_stag, msg = debate.detect_stagnation_and_substitute(0.962)
        assert is_stag is True
        assert "STAGNATION DEFENSE TRIGGERED" in msg
        assert debate.active_primary_model == "math_72b"
        assert debate.consecutive_stagnant_turns == 0  # Resets counter

    def test_stagnation_5_rounds_continuous_defense(self, adversarial_env):
        """5 continuous stagnant rounds triggers substitution and continues without crash."""
        debate = adversarial_env["debate"]
        assert debate.active_primary_model == "coder_architect"

        scores = [0.900, 0.905, 0.908, 0.910, 0.912, 0.915]
        substitutions = []

        for s in scores:
            is_stag, msg = debate.detect_stagnation_and_substitute(s)
            if is_stag:
                substitutions.append((s, msg, debate.active_primary_model))

        assert len(substitutions) == 1
        assert substitutions[0][2] == "math_72b"
        assert debate.consecutive_stagnant_turns == 2

    def test_stagnation_10_rounds_oscillating_substitutions(self, adversarial_env):
        """10 continuous stagnant rounds triggers multiple cyclic model substitutions."""
        debate = adversarial_env["debate"]
        scores = [0.800, 0.805, 0.808, 0.810, 0.812, 0.814, 0.816, 0.818, 0.820, 0.822, 0.824]
        substitutions = []

        for i, s in enumerate(scores):
            is_stag, msg = debate.detect_stagnation_and_substitute(s)
            if is_stag:
                substitutions.append((i, s, debate.active_primary_model))

        # At index 3 (round 4), index 6 (round 7), index 9 (round 10)
        assert len(substitutions) == 3
        assert substitutions[0][2] == "math_72b"
        assert substitutions[1][2] == "coder_architect"
        assert substitutions[2][2] == "math_72b"

    def test_stagnation_recovery_on_score_jump(self, adversarial_env):
        """Significant score change (ΔC >= 0.02) resets stagnant turn counter."""
        debate = adversarial_env["debate"]
        debate.detect_stagnation_and_substitute(0.850)
        debate.detect_stagnation_and_substitute(0.855)  # stagnant 1
        debate.detect_stagnation_and_substitute(0.860)  # stagnant 2
        assert debate.consecutive_stagnant_turns == 2

        # Significant jump (delta = 0.050 >= 0.02)
        is_stag, _ = debate.detect_stagnation_and_substitute(0.910)
        assert is_stag is False
        assert debate.consecutive_stagnant_turns == 0
        assert debate.active_primary_model == "coder_architect"

    def test_stagnation_zero_baseline_initialization(self, adversarial_env):
        """Verify None-based baseline initialization properly tracks subsequent 0.0 deltas."""
        debate = adversarial_env["debate"]
        # If consensus is 0.0, first call initializes baseline
        is_stag, msg1 = debate.detect_stagnation_and_substitute(0.0)
        assert is_stag is False
        assert msg1 == "Initial consensus baseline recorded"

        # Calling again with 0.0 computes delta (0.0 < 0.02) and tracks stagnant turn
        is_stag, msg2 = debate.detect_stagnation_and_substitute(0.0)
        assert is_stag is False
        assert msg2 == "Nominal debate progression"
        assert debate.consecutive_stagnant_turns == 1


# ===========================================================================
# DIMENSION 4: Low NVMe Disk Headroom (< 10.0 GB) & Cache Purging
# ===========================================================================

class TestAdversarialDimension4StorageSentinelAndPurging:
    """Stress-tests storage headroom checking and pre-flight cache purging."""

    def test_fast_path_latency_sub_3ms(self, adversarial_env):
        """Rule 6.3 Fast-Path check latency MUST be < 3.0 ms."""
        sentinel = adversarial_env["sentinel"]
        is_healthy, free_gb, latency_ms = sentinel.fast_path_check()
        assert latency_ms < 3.0, f"Fast-Path latency {latency_ms}ms exceeded 3.0ms requirement"
        assert isinstance(is_healthy, bool)

    def test_low_headroom_detected_and_reported_unhealthy(self, adversarial_env):
        """When disk free space is below threshold, fast_path returns False."""
        sentinel = adversarial_env["sentinel"]
        
        # Mock disk usage to return 4.5 GB free space (< 10.0 GB threshold)
        mock_stat = MagicMock()
        mock_stat.free = int(4.5 * (1024 ** 3))
        with patch("shutil.disk_usage", return_value=mock_stat):
            is_healthy, free_gb, latency_ms = sentinel.fast_path_check()
            assert is_healthy is False
            assert free_gb == 4.50
            assert latency_ms < 3.0

    def test_cache_purging_behavior_on_low_headroom(self, adversarial_env):
        """Verify purge of __pycache__, .pytest_cache, stale logs, and git locks."""
        ws = adversarial_env["workspace"]
        sentinel = adversarial_env["sentinel"]

        # Create dummy caches and stale files
        dummy_pycache = ws / "04_data_and_memory" / "__pycache__"
        dummy_pycache.mkdir(parents=True, exist_ok=True)
        (dummy_pycache / "test.cpython-313.pyc").write_text("bytecode")

        dummy_pytest_cache = ws / ".pytest_cache"
        dummy_pytest_cache.mkdir(parents=True, exist_ok=True)
        (dummy_pytest_cache / "v").write_text("cache")

        log_dir = ws / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        stale_log = log_dir / "stale_run.log"
        stale_log.write_text("stale logs")
        # Set mtime to 5 days ago
        old_time = time.time() - (5 * 86400)
        os.utime(stale_log, (old_time, old_time))

        active_log = log_dir / "active_run.log"
        active_log.write_text("fresh logs")

        git_dir = ws / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        stale_lock = git_dir / "index.lock"
        stale_lock.write_text("lock")
        os.utime(stale_lock, (time.time() - 30, time.time() - 30))

        # Execute heal_storage_headroom
        result = sentinel.heal_storage_headroom()
        assert result["rule_6_3_compliant"] is True

        # Assertions on purges
        assert not dummy_pycache.exists(), "__pycache__ should have been purged"
        assert not dummy_pytest_cache.exists(), ".pytest_cache should have been purged"
        assert not stale_log.exists(), "Stale log (>3 days) should have been purged"
        assert active_log.exists(), "Active fresh log should have been preserved"
        assert not stale_lock.exists(), "Stale git lock should have been removed"

    def test_master_engine_pauses_when_storage_constrained(self, adversarial_env):
        """Master daemon pauses cycle when disk headroom < 10.0 GB."""
        ws = adversarial_env["workspace"]
        engine = LiveTrainingAutomationEngine(monorepo_root=ws, dry_run=True)

        mock_stat = MagicMock()
        mock_stat.free = int(3.2 * (1024 ** 3))  # 3.2 GB < 10.0 GB
        with patch("shutil.disk_usage", return_value=mock_stat):
            res = engine.run_single_pass()
            assert res["status"] == "PAUSED_STORAGE_CONSTRAINED"
            assert res["free_disk_gb"] == 3.20
            assert "training_pass_executed" not in res or not res.get("training_pass_executed")

    def test_master_engine_pauses_when_ram_constrained(self, adversarial_env):
        """Master daemon pauses cycle when RAM headroom < 2.50 GB even after cache clearing."""
        ws = adversarial_env["workspace"]
        engine = LiveTrainingAutomationEngine(monorepo_root=ws, dry_run=True)

        unsafe_ram = {
            "is_safe": False,
            "status": "EXCEEDS_CAP",
            "ram_headroom_gb": 1.20,
            "min_headroom_required_gb": 2.50,
        }
        with patch.object(engine.governor, "check_headroom", return_value=unsafe_ram):
            res = engine.run_single_pass()
            assert res["status"] == "PAUSED_RAM_CONSTRAINED"
            assert res["reason"] == "RAM headroom breached"
            assert res["ram_headroom_gb"] == 1.20
            assert "training_pass_executed" not in res or not res.get("training_pass_executed")


# ===========================================================================
# DIMENSION 5: Dynamic RAM Governor Allocations near 21.6 GB
# ===========================================================================

class TestAdversarialDimension5RAMGovernorEdgeCases:
    """Stress-tests RAM Governor under edge-case allocations and overcommitments."""

    def test_nominal_allocation_safety(self, adversarial_env):
        """Nominal: Base=14.50, KV=2.10, Act=1.80 -> Allocated=18.40GB, Headroom=3.20GB >= 2.50GB."""
        gov = adversarial_env["governor"]
        status = gov.check_headroom(cap_gb=21.6, min_headroom_gb=2.50, base_model_gb=14.50, kv_cache_gb=2.10, activation_gb=1.80)
        assert status["is_safe"] is True
        assert status["status"] == "CERTIFIED_HEALTHY"
        assert status["ram_headroom_gb"] == 3.20

    def test_exact_headroom_boundary_at_2_50gb(self, adversarial_env):
        """Allocated=19.10GB -> Headroom = 21.60 - 19.10 = 2.50GB -> Exactly meets min headroom."""
        gov = adversarial_env["governor"]
        status = gov.check_headroom(cap_gb=21.6, min_headroom_gb=2.50, base_model_gb=15.00, kv_cache_gb=2.10, activation_gb=2.00)
        assert status["allocated_ai_ram_gb"] == 19.10
        assert status["ram_headroom_gb"] == 2.50
        assert status["is_safe"] is True
        assert status["status"] == "CERTIFIED_HEALTHY"

    def test_slight_headroom_breach_at_2_49gb(self, adversarial_env):
        """Allocated=19.11GB -> Headroom = 21.60 - 19.11 = 2.49GB < 2.50GB -> EXCEEDS_CAP."""
        gov = adversarial_env["governor"]
        status = gov.check_headroom(cap_gb=21.6, min_headroom_gb=2.50, base_model_gb=15.01, kv_cache_gb=2.10, activation_gb=2.00)
        assert status["ram_headroom_gb"] == 2.49
        assert status["is_safe"] is False
        assert status["status"] == "EXCEEDS_CAP"

    def test_complete_cap_exhaustion_at_21_60gb(self, adversarial_env):
        """Allocated=21.60GB -> Headroom = 0.00GB -> EXCEEDS_CAP."""
        gov = adversarial_env["governor"]
        status = gov.check_headroom(cap_gb=21.6, min_headroom_gb=2.50, base_model_gb=17.50, kv_cache_gb=2.10, activation_gb=2.00)
        assert status["allocated_ai_ram_gb"] == 21.60
        assert status["ram_headroom_gb"] == 0.00
        assert status["is_safe"] is False

    def test_overcommit_allocation_exceeding_total_ram(self, adversarial_env):
        """Allocated=26.00GB > 24.0GB Total -> Negative Headroom -> EXCEEDS_CAP."""
        gov = adversarial_env["governor"]
        status = gov.check_headroom(cap_gb=21.6, min_headroom_gb=2.50, base_model_gb=20.00, kv_cache_gb=3.00, activation_gb=3.00)
        assert status["allocated_ai_ram_gb"] == 26.00
        assert status["ram_headroom_gb"] < 0
        assert status["is_safe"] is False
        assert status["status"] == "EXCEEDS_CAP"

    def test_custom_cap_scaling_80_pct(self, adversarial_env):
        """Governor with 80% dynamic cap (19.20 GB on 24.0GB RAM)."""
        gov = DynamicRamGovernor(total_system_ram_gb=24.0, cap_pct=80.0, min_headroom_gb=2.50)
        assert gov.dynamic_cap_gb == 19.20

        # Allocated = 18.40 GB -> Headroom = 19.20 - 18.40 = 0.80 GB < 2.50 GB -> EXCEEDS_CAP
        status = gov.check_headroom()
        assert status["dynamic_cap_gb"] == 19.20
        assert status["ram_headroom_gb"] == 0.80
        assert status["is_safe"] is False
        assert status["status"] == "EXCEEDS_CAP"
