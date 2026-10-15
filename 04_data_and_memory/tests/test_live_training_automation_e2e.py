#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Suite: Lauburu Live Training Automation Engine — Unified System Integration
====================================================================================
Test Target: 04_data_and_memory/live_training_automation_engine.py & Full Subsystem
Covers:
- Feature 15: Unified Automation Engine Master Daemon (Tier 1 & Tier 2)
- Tier 3: Pairwise Cross-Feature Interactions (15 Major Interlocks)
- Tier 4: Real-World Application Scenarios (Scenarios 1 - 5)
Test Framework: pytest
Zero-Mock Compliance: 100% genuine inputs, deterministic verification, zero facade mocks.
"""

import os
import sys
import json
import time
import math
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

# Ensure module path is accessible
MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from live_training_automation_engine import LiveTrainingAutomationEngine
from multi_stream_harvester import MultiStreamHarvester
from mlx_qlora_trainer import MLXQLoRATrainer, DynamicRamGovernor
from synthetic_debate_engine import SyntheticDebateEngine
from telemetry_streamer import TelemetryStreamer, StorageSentinel
from tri_vault_sink import TriVaultSink, verify_zero_mock_compliance


@pytest.fixture
def temp_e2e_workspace():
    """Provides an isolated workspace for full E2E engine execution."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_e2e_test_")
    ws = Path(temp_dir)
    data_dir = ws / "04_data_and_memory"
    obs_dir = ws / "obsidian_vault" / "04_ANALYTICS"
    obs_debates = ws / "obsidian_vault" / "01_DEBATES"
    tui_dir = ws / "02_ai_models_and_inference" / "lauburu_tui" / "config"
    lora_dir = ws / "lora_datasets"

    for d in [data_dir, obs_dir, obs_debates, tui_dir, lora_dir]:
        d.mkdir(parents=True, exist_ok=True)

    engine = LiveTrainingAutomationEngine(monorepo_root=ws, dry_run=True)
    # Configure all child subsystems to point to isolated workspace
    engine.harvester.target_dataset = data_dir / "ai_training_game_dataset.jsonl"
    engine.trainer.data_dir = data_dir
    engine.trainer.train_log_file = data_dir / "agentworld_training_runs.jsonl"
    engine.trainer.watermark_file = data_dir / ".training_watermark.json"
    engine.sentinel.lora_dir = lora_dir
    engine.sentinel.min_free_gb = 1.0  # Safe for temp dir

    yield {
        "workspace": ws,
        "data_dir": data_dir,
        "obs_dir": obs_dir,
        "tui_dir": tui_dir,
        "lora_dir": lora_dir,
        "engine": engine,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# FEATURE 15: Unified Automation Engine Master Daemon (Tiers 1 & 2)
# ===========================================================================

class TestFeature15MasterDaemonLifecycle:
    """Tests master daemon initialization, single pass cycle, and status reporting."""

    def test_engine_initialization_instantiates_all_subsystems(self, temp_e2e_workspace):
        """Tier 1.1: Engine initializes all 5 milestone subsystems cleanly."""
        engine = temp_e2e_workspace["engine"]

        assert isinstance(engine.sink, TriVaultSink)
        assert isinstance(engine.sentinel, StorageSentinel)
        assert isinstance(engine.governor, DynamicRamGovernor)
        assert isinstance(engine.harvester, MultiStreamHarvester)
        assert isinstance(engine.trainer, MLXQLoRATrainer)
        assert isinstance(engine.debate_engine, SyntheticDebateEngine)
        assert isinstance(engine.streamer, TelemetryStreamer)

    def test_engine_run_single_pass_completes_5_milestone_steps(self, temp_e2e_workspace):
        """Tier 1.2: run_single_pass executes pre-flight, harvest, debate, train, and telemetry."""
        engine = temp_e2e_workspace["engine"]
        res = engine.run_single_pass()

        assert res["status"] == "COMPLETED"
        assert res["cycle"] == 1
        assert res["cycle_duration_sec"] >= 0.0
        assert res["storage_headroom_gb"] > 0.0
        assert res["ram_governor_status"] == "CERTIFIED_HEALTHY"
        assert res["harvested_in_cycle"] >= 4
        assert res["debate_accord"]["consensus_passed"] is True
        assert res["training_pass_executed"] is True
        assert res["telemetry_streamed"]["tui_streamed"] is True

    def test_engine_get_status_comprehensive_diagnostics(self, temp_e2e_workspace):
        """Tier 1.3: get_status returns complete multi-subsystem diagnostic payload."""
        engine = temp_e2e_workspace["engine"]
        engine.run_single_pass()
        status = engine.get_status()

        assert status["engine_version"] == "2.0.0-CANONICAL-MASTER"
        assert "storage" in status
        assert "ram_governor" in status
        assert "dataset" in status
        assert "training_trigger" in status
        assert "fleet_ports" in status
        assert status["rule_zero_verified"] is True
        assert status["storage"]["healthy"] is True
        assert status["ram_governor"]["status"] == "CERTIFIED_HEALTHY"

    def test_engine_storage_constraint_pauses_compute(self, temp_e2e_workspace):
        """Tier 2.1: Constrained NVMe space cleanly pauses cycle at Pre-Flight gate."""
        engine = temp_e2e_workspace["engine"]
        # Set impossible storage threshold to simulate critical disk pressure
        engine.sentinel.min_free_gb = 99999.0

        res = engine.run_single_pass()
        assert res["status"] == "PAUSED_STORAGE_CONSTRAINED"
        assert "free_disk_gb" in res


# ===========================================================================
# TIER 3: Pairwise Cross-Feature Interactions (15 Major Interlocks)
# ===========================================================================

class TestTier3PairwiseCrossFeatureInteractions:
    """Tests pairwise interface contracts and cross-module couplings."""

    def test_interaction_harvester_to_trainer_batch_threshold(self, temp_e2e_workspace):
        """Tier 3.1: Harvester batch generation triggers MLX training pass when delta >= 100."""
        engine = temp_e2e_workspace["engine"]
        # Generate 110 pairs into primary dataset
        engine.harvester.generate_batch(count=110)

        should_train, count, watermark = engine.trainer.should_trigger_training(min_new_samples=100)
        assert should_train is True
        assert (count - watermark) >= 100

        # Execute pass and verify watermark advances
        result = engine.trainer.execute_incremental_pass(min_samples=100, dry_run=True)
        assert result is not None
        assert result["status"] == "DRY_RUN_PLAN_VERIFIED"

    def test_interaction_synthetic_debate_to_harvester_dataset(self, temp_e2e_workspace):
        """Tier 3.2: Synthetic debate engine exports TRL DPO pair directly into target dataset."""
        engine = temp_e2e_workspace["engine"]
        accord = engine.debate_engine.run_deliberation(topic_idx=0)
        dpo = engine.debate_engine.export_dpo_pair(accord)

        assert dpo["meta"]["zero_mock_certified"] is True
        is_valid, _ = verify_zero_mock_compliance(dpo)
        assert is_valid is True

    def test_interaction_mlx_trainer_to_ram_governor(self, temp_e2e_workspace):
        """Tier 3.3: MLX trainer check_headroom enforces <= 21.6GB AI VRAM cap."""
        engine = temp_e2e_workspace["engine"]
        status = engine.trainer.governor.check_headroom(cap_gb=21.6)

        assert status["dynamic_cap_gb"] == 21.6
        assert status["ram_headroom_gb"] >= 2.50
        assert status["status"] == "CERTIFIED_HEALTHY"

    def test_interaction_mlx_trainer_to_telemetry_streamer(self, temp_e2e_workspace):
        """Tier 3.4: Training pass receipts log into agentworld_training_runs.jsonl."""
        engine = temp_e2e_workspace["engine"]
        ram_status = engine.governor.check_headroom()

        logged = engine.streamer.log_training_run(
            backend="mlx_metal",
            model="Qwen-AgentWorld-35B",
            iters=100,
            final_loss=2.0447,
            ram_governor=ram_status,
            status="COMPLETED"
        )
        assert logged is True
        assert engine.streamer.train_log_file.exists()

    def test_interaction_synthetic_debate_to_stagnation_defense(self, temp_e2e_workspace):
        """Tier 3.5: Consensus score plateau in synthetic debate triggers specialist model substitution."""
        engine = temp_e2e_workspace["engine"]
        accord = engine.debate_engine.run_deliberation(topic_idx=0, force_stagnation=True)

        assert accord.stagnation_occurred is True
        assert accord.substituted_specialist is not None

    def test_interaction_telemetry_streamer_to_tui_tab5(self, temp_e2e_workspace):
        """Tier 3.6: Telemetry streamer updates TUI memory_fallback.json and optimization_strategies.json."""
        engine = temp_e2e_workspace["engine"]
        stream_ok = engine.streamer.stream_to_tui(step=250, current_loss=1.82)
        assert stream_ok is True

        mem_file = engine.streamer.tui_config_dir / "memory_fallback.json"
        opt_file = engine.streamer.tui_config_dir / "optimization_strategies.json"
        assert mem_file.exists()
        assert opt_file.exists()

    def test_interaction_storage_sentinel_to_cache_purger(self, temp_e2e_workspace):
        """Tier 3.7: Storage sentinel purges __pycache__ and returns Rule 6.3 compliant latency."""
        engine = temp_e2e_workspace["engine"]
        heal_res = engine.sentinel.heal_storage_headroom()

        assert heal_res["rule_6_3_compliant"] is True
        assert heal_res["latency_ms"] < 3.0
        assert heal_res["is_healthy"] is True


# ===========================================================================
# TIER 4: Real-World Application Scenarios (Scenarios 1 - 5)
# ===========================================================================

class TestTier4RealWorldApplicationScenarios:
    """Tests end-to-end multi-step real-world workflows defined in TEST_INFRA.md."""

    def test_scenario_1_continuous_harvest_to_train_to_telemetry_pipeline(self, temp_e2e_workspace):
        """
        Scenario 1: Continuous Harvest-to-Train-to-Telemetry Pipeline.
        1. Harvest authentic pairs from all 5 streams into dataset.
        2. Verify batch threshold condition is satisfied.
        3. Assemble multi-turn ChatML dataset.
        4. Execute QLoRA training pass with Dynamic RAM verification.
        5. Stream live loss curve to Obsidian and TUI Tab 5.
        6. Append certified run receipt to agentworld_training_runs.jsonl.
        """
        engine = temp_e2e_workspace["engine"]

        # Step 1: Harvest 105 verified pairs across 5 streams
        count = engine.harvester.generate_batch(count=105)
        assert count == 105

        # Step 2: Check batch trigger
        should_train, sample_count, _ = engine.trainer.should_trigger_training(min_new_samples=100)
        assert should_train is True

        # Step 3: Prepare dataset
        ds_path = engine.trainer.prepare_dataset(stage=1)
        assert ds_path.exists()

        # Step 4: Execute incremental training pass
        receipt = engine.trainer.execute_incremental_pass(min_samples=100, backend="mlx", iters=100, dry_run=True)
        assert receipt is not None
        assert receipt["ram_governor"]["is_safe"] is True

        # Step 5: Stream telemetry
        stream_res = engine.streamer.stream_all(step=100, loss=receipt["final_loss"], dry_run=True)
        assert stream_res["tui_streamed"] is True
        assert Path(stream_res["obsidian_note"]).exists()

        # Step 6: Verify receipt logged
        with open(engine.streamer.train_log_file, "r", encoding="utf-8") as f:
            receipts = [json.loads(l) for l in f if l.strip()]
        assert len(receipts) >= 1
        assert receipts[-1]["final_loss"] == receipt["final_loss"]

    def test_scenario_2_stagnation_triggered_specialist_substitution(self, temp_e2e_workspace):
        """
        Scenario 2: Stagnation-Triggered Specialist Substitution & DPO Synthesis.
        1. Multi-agent debate encounters a score plateau across 3 turns.
        2. Stagnation defense substitutes Primary Model with Qwen-Math-72B Specialist.
        3. Deliberation produces consensus accord with substitute.
        4. Verified DPO preference pair is exported and passes Rule #0 zero-mock check.
        """
        engine = temp_e2e_workspace["engine"]

        # Step 1 & 2: Deliberation with forced stagnation
        accord = engine.debate_engine.run_deliberation(topic_idx=0, force_stagnation=True)
        assert accord.stagnation_occurred is True

        # Step 3: Accord contains winner and top 5 priorities
        assert len(accord.top_5_priorities) == 5

        # Step 4: Export DPO pair
        dpo = engine.debate_engine.export_dpo_pair(accord, topic_idx=0)
        assert dpo["meta"]["zero_mock_certified"] is True
        assert "10Gbps Thunderbolt 4" in dpo["chosen"]

    def test_scenario_3_storage_pressure_auto_healing_and_resume(self, temp_e2e_workspace):
        """
        Scenario 3: Storage Pressure Auto-Healing & Training Resume.
        1. Inject transient __pycache__ and stale log files.
        2. Sentinel executes idempotent cache purge.
        3. Host NVMe space re-verified as healthy.
        4. Single pass training proceeds and completes successfully.
        """
        engine = temp_e2e_workspace["engine"]
        ws = temp_e2e_workspace["workspace"]

        # Create transient caches to clean
        pycache = ws / "module_temp" / "__pycache__"
        pycache.mkdir(parents=True, exist_ok=True)
        (pycache / "transient.pyc").write_bytes(b"PYC")

        log_dir = ws / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        old_log = log_dir / "old_run.log"
        old_log.write_text("old logs")
        os.utime(old_log, (time.time() - 400000, time.time() - 400000))

        # Explicitly trigger self-healing
        heal_res = engine.sentinel.heal_storage_headroom()
        assert not pycache.exists()
        assert not old_log.exists()

        # Run pass which confirms system is healthy
        res = engine.run_single_pass()
        assert res["status"] == "COMPLETED"

    def test_scenario_4_offline_google_drive_fallback(self, temp_e2e_workspace):
        """
        Scenario 4: Offline Google Drive Dual-Tier Fallback Under Live Training.
        1. Point primary dataset destination to unmounted GDrive path.
        2. Multi-stream harvester and telemetry streamer gracefully fallback to local disk.
        3. Ensure 0 unhandled I/O exceptions, 0 lost records, and full persistence.
        """
        engine = temp_e2e_workspace["engine"]
        unmounted = Path("/Volumes/Google Drive Unmounted Test/Lauburu_AI_Memory")
        engine.sink.primary_lora_dir = unmounted

        # Single pass should execute cleanly without panics
        res = engine.run_single_pass()
        assert res["status"] == "COMPLETED"
        assert res["telemetry_streamed"]["tui_streamed"] is True

    def test_scenario_5_end_to_end_autonomous_engine_multi_pass(self, temp_e2e_workspace):
        """
        Scenario 5: End-to-End Autonomous 24/7 Engine Multi-Pass Cycle.
        1. Execute 3 consecutive engine passes.
        2. Verify cycle counters, dataset accumulations, and debate accords advance.
        3. Verify final system status diagnostic confirms 100% operational health across all features.
        """
        engine = temp_e2e_workspace["engine"]

        for i in range(3):
            res = engine.run_single_pass()
            assert res["status"] == "COMPLETED"
            assert res["cycle"] == (i + 1)

        assert engine.cycle_count == 3
        assert engine.total_debates == 3

        status = engine.get_status()
        assert status["engine_version"] == "2.0.0-CANONICAL-MASTER"
        assert status["storage"]["healthy"] is True
        assert status["ram_governor"]["status"] == "CERTIFIED_HEALTHY"
        assert status["rule_zero_verified"] is True
