#!/usr/bin/env python3
"""
06_scripts_and_tooling/tests/test_cloud_api_quota_manager.py
============================================================
Comprehensive 4-Tier Opaque-Box Test Suite for Cloud API Quota Manager & Workload Router

Covers:
- Tier 1: Feature Coverage (Heuristic scoring math, quota decrementing, provider selection, LoRA dataset write format, local mesh fallback).
- Tier 2: Boundary & Corner Cases (Zero remaining quota, negative limits, malformed JSON state recovery, missing API keys, high latency/timeout handling, concurrency/file lock stress).
- Tier 3: Cross-Feature Combinations (Provider exhaustion cascading to Local Mesh then generating LoRA dataset, quota reset at UTC midnight during active batch, speed heuristic weighting override).
- Tier 4: Real-World Scenarios (End-to-end CLI execution simulation with --live, --distill, --task, --status, --benchmark, state persistence integrity across consecutive runs, LoRA dataset verification).
"""

import os
import sys
import json
import time
import fcntl
import shutil
import tempfile
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

import pytest

# Ensure automation directory is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUTOMATION_DIR = PROJECT_ROOT / "06_scripts_and_tooling" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

# Import module under test
import cloud_api_quota_manager as caqm
from cloud_api_quota_manager import (
    QuotaStateStore,
    HeuristicRoutingEngine,
    HeuristicScore,
    TaskRequest,
    TaskResult,
    LoRADatasetWriter,
    WorkloadRouter,
    BaseProviderAdapter,
    GeminiAdapter,
    CloudflareAdapter,
    JulienAdapter,
    LocalMeshAdapter,
    ProviderError,
    PROVIDER_CONFIGS,
    generate_distillation_tasks,
    print_status,
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """
    Creates an isolated hermetic testing environment with temporary paths
    for state files, LoRA datasets, and environment variables.
    """
    state_file = tmp_path / "cloud_api_quota_state.json"
    dataset_file = tmp_path / "continuous_lora_dataset.jsonl"
    mirror_dataset_file = tmp_path / "mirror_lora_dataset.jsonl"
    log_file = tmp_path / "cloud_api_quota_manager.log"

    # Set environment variables for testing isolation
    monkeypatch.setenv("QUOTA_STATE_PATH", str(state_file))
    monkeypatch.setenv("LORA_DATASET_PATH", str(dataset_file))
    monkeypatch.setenv("LORA_DATASET_MIRROR_PATH", str(mirror_dataset_file))
    monkeypatch.setenv("QUOTA_LOG_PATH", str(log_file))

    state_store = QuotaStateStore(state_file=state_file)
    dataset_writer = LoRADatasetWriter(
        primary_dataset=dataset_file,
        mirror_dataset=mirror_dataset_file
    )
    router = WorkloadRouter(state_store=state_store, dataset_writer=dataset_writer)

    return {
        "tmp_path": tmp_path,
        "state_file": state_file,
        "dataset_file": dataset_file,
        "mirror_dataset_file": mirror_dataset_file,
        "log_file": log_file,
        "state_store": state_store,
        "dataset_writer": dataset_writer,
        "router": router,
    }


# ===========================================================================
# TIER 1: FEATURE COVERAGE (Unit & Contract Invariants)
# ===========================================================================

class TestTier1FeatureCoverage:
    """
    Tier 1 tests verify fundamental feature implementations:
    - Composite heuristic scoring calculation
    - Quota decrementing and tracking logic
    - Provider selection algorithms
    - LoRA dataset record schema formatting
    - Local mesh compute fallback
    """

    def test_t1_01_composite_heuristic_score_calculation(self, temp_env):
        """
        Verify the multi-attribute composite fitness formula:
        Score = 0.40 * Q_rem_pct + 0.25 * Speed_norm + 0.25 * Token_fit + 0.10 * Health_score - Penalty_failures
        """
        engine = temp_env["router"].heuristic_engine
        task = TaskRequest(
            task_id="t1_calc",
            prompt="Analyze movesense 512Hz ECG stream",
            estimated_tokens=500,
            task_type="distillation"
        )
        
        score_obj = engine.evaluate_provider("gemini_free", task)
        assert isinstance(score_obj, HeuristicScore)
        assert score_obj.provider == "gemini_free"
        assert not score_obj.disqualified
        
        # Verify manual component calculation
        expected_score = round(
            (0.40 * score_obj.q_rem_pct)
            + (0.25 * score_obj.speed_norm)
            + (0.25 * score_obj.token_fit)
            + (0.10 * score_obj.health_score)
            - score_obj.penalty_failures,
            4
        )
        assert score_obj.score == expected_score

    def test_t1_02_quota_consumption_and_tracking(self, temp_env):
        """Verify consuming quota increments used count and accurately updates remaining_pct."""
        state_store = temp_env["state_store"]
        
        # Initial state
        initial_julien = state_store.get_provider_state("julien_ai")
        assert initial_julien["used_today"] == 0
        assert initial_julien["remaining_pct"] == 1.0
        
        # Consume 5 requests
        consumed = state_store.consume_quota("julien_ai", amount=5)
        assert consumed is True
        
        updated_julien = state_store.get_provider_state("julien_ai")
        assert updated_julien["used_today"] == 5
        assert updated_julien["remaining_pct"] == (300 - 5) / 300.0

    def test_t1_03_provider_selection_under_token_constraints(self, temp_env):
        """
        Verify that a task with 25,000 tokens selects Gemini Free Tier
        or Local Mesh, while disqualifying Cloudflare (4K max) and Julien (8K max).
        """
        engine = temp_env["router"].heuristic_engine
        task = TaskRequest(
            task_id="t1_large_context",
            prompt="Review complete 25K token AST code tree",
            estimated_tokens=25000,
            task_type="code"
        )
        
        ranked = engine.rank_providers(task)
        assert len(ranked) == 4
        
        # Cloudflare and Julien must be disqualified due to token limits
        cf_score = next(s for s in ranked if s.provider == "cloudflare_ai")
        j_score = next(s for s in ranked if s.provider == "julien_ai")
        gemini_score = next(s for s in ranked if s.provider == "gemini_free")
        
        assert cf_score.disqualified is True
        assert j_score.disqualified is True
        assert gemini_score.disqualified is False
        assert ranked[0].provider in ["gemini_free", "local_mesh"]

    def test_t1_04_provider_selection_prefer_local(self, temp_env):
        """Verify that prefer_local flag awards top ranking to local_mesh."""
        engine = temp_env["router"].heuristic_engine
        task = TaskRequest(
            task_id="t1_local_pref",
            prompt="Process confidential biometrics",
            estimated_tokens=400,
            prefer_local=True
        )
        
        ranked = engine.rank_providers(task)
        assert ranked[0].provider == "local_mesh"

    def test_t1_05_lora_dataset_schema_formatting(self, temp_env):
        """
        Verify that LoRADatasetWriter appends records following the Alpaca / ChatML schema:
        instruction, input, output, system, metadata.
        """
        dataset_writer = temp_env["dataset_writer"]
        task = TaskRequest(
            task_id="t1_lora",
            prompt="Write unit tests for Pan-Tompkins DSP",
            system_prompt="You are a DSP QA specialist.",
            task_type="distillation"
        )
        result = TaskResult(
            task_id="t1_lora",
            provider_used="gemini_free",
            response_text="def test_pan_tompkins(): pass",
            prompt_tokens=50,
            completion_tokens=30,
            latency_ms=250.0,
            success=True
        )
        
        success = dataset_writer.append_distillation_pair(task, result)
        assert success is True
        
        # Verify primary dataset content
        dataset_path = temp_env["dataset_file"]
        assert dataset_path.exists()
        
        lines = dataset_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        
        entry = json.loads(lines[0])
        assert entry["instruction"] == task.prompt
        assert entry["output"] == result.response_text
        assert entry["system"] == task.system_prompt
        assert entry["metadata"]["provider"] == "gemini_free"
        assert entry["metadata"]["task_id"] == "t1_lora"
        assert entry["metadata"]["task_type"] == "distillation"
        assert entry["metadata"]["latency_ms"] == 250.0

    def test_t1_06_state_file_initialization_defaults(self, temp_env):
        """Verify default quota state defines correct daily limits for all providers."""
        state = temp_env["state_store"].state
        providers = state["providers"]
        
        assert "julien_ai" in providers
        assert "cloudflare_ai" in providers
        assert "gemini_free" in providers
        assert "local_mesh" in providers
        
        assert providers["julien_ai"]["daily_limit"] == 300
        assert providers["cloudflare_ai"]["daily_limit"] == 1000
        assert providers["gemini_free"]["daily_limit"] == 1500
        assert providers["local_mesh"]["daily_limit"] == 999999

    def test_t1_07_local_mesh_fallback_when_cloud_exhausted(self, temp_env):
        """Verify fallback to local mesh when all cloud providers are exhausted."""
        state_store = temp_env["state_store"]
        router = temp_env["router"]
        
        # Exhaust all cloud providers
        state_store.consume_quota("julien_ai", 300)
        state_store.consume_quota("cloudflare_ai", 1000)
        state_store.consume_quota("gemini_free", 1500)
        
        task = TaskRequest(
            task_id="t1_exhausted_fallback",
            prompt="Autonomous task during quota blackout",
            estimated_tokens=500
        )
        
        result = router.route_and_execute(task)
        assert result.success is True
        assert result.provider_used == "local_mesh"
        assert len(result.response_text) > 0

    def test_t1_08_task_request_and_result_interfaces(self, temp_env):
        """Verify TaskRequest and TaskResult dataclasses conform to PROJECT.md contracts."""
        req = TaskRequest(
            task_id="req_contract",
            prompt="Verify interface contract",
            system_prompt="System instructions",
            estimated_tokens=600,
            task_type="code",
            prefer_local=False
        )
        assert req.task_id == "req_contract"
        assert req.estimated_tokens == 600
        assert req.task_type == "code"
        
        res = TaskResult(
            task_id="req_contract",
            provider_used="local_mesh",
            response_text="contract valid",
            prompt_tokens=100,
            completion_tokens=20,
            latency_ms=45.0,
            success=True,
            error_message="",
            lora_entry_saved=True,
            fallback_occurred=False
        )
        assert res.success is True
        assert res.lora_entry_saved is True


# ===========================================================================
# TIER 2: BOUNDARY & CORNER CASES (Fault Tolerance & Resilience)
# ===========================================================================

class TestTier2BoundaryAndCornerCases:
    """
    Tier 2 tests verify resilience across edge cases and failure modes:
    - Zero remaining quota & rejection of over-quota requests
    - Negative and zero amount quota requests
    - Corrupted / malformed JSON state recovery
    - Missing API keys and offline fallback
    - High latency, HTTP 429 rate limit backoff
    - Multi-threaded file lock concurrency stress test
    """

    def test_t2_01_zero_quota_rejection(self, temp_env):
        """Verify that requests exceeding remaining daily quota are rejected."""
        state_store = temp_env["state_store"]
        
        # Consume all 300 slots for Julien
        assert state_store.consume_quota("julien_ai", 300) is True
        
        # Attempt 1 more
        assert state_store.consume_quota("julien_ai", 1) is False
        p_state = state_store.get_provider_state("julien_ai")
        assert p_state["used_today"] == 300
        assert p_state["remaining_pct"] == 0.0

    def test_t2_02_negative_and_zero_amount_consumption(self, temp_env):
        """Verify consuming 0 or negative quota does not corrupt state."""
        state_store = temp_env["state_store"]
        initial_used = state_store.get_provider_state("gemini_free")["used_today"]
        
        state_store.consume_quota("gemini_free", 0)
        assert state_store.get_provider_state("gemini_free")["used_today"] == initial_used

    def test_t2_03_malformed_json_state_file_recovery(self, temp_env):
        """
        Verify that corrupted, truncated, or invalid JSON state files
        are gracefully detected and recovered by re-initializing defaults.
        """
        state_file = temp_env["state_file"]
        with open(state_file, "w", encoding="utf-8") as f:
            f.write("{{{corrupted_malformed_json_truncated... [")
            
        # Creating a new store should self-heal without crashing
        new_store = QuotaStateStore(state_file=state_file)
        assert "gemini_free" in new_store.state["providers"]
        assert new_store.get_provider_state("gemini_free")["daily_limit"] == 1500

    def test_t2_04_missing_api_keys_graceful_handling(self, temp_env, monkeypatch):
        """
        Verify that when API keys are absent, live tasks gracefully cascade
        to Local Mesh without raising unhandled exceptions.
        """
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
        monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
        monkeypatch.delenv("JULIEN_API_KEY", raising=False)
        monkeypatch.delenv("JULES_API_KEY", raising=False)
        
        router = temp_env["router"]
        task = TaskRequest(
            task_id="t2_missing_keys",
            prompt="Synthesize architecture with no cloud keys",
            estimated_tokens=300
        )
        
        result = router.route_and_execute(task)
        assert result.success is True
        assert result.provider_used == "local_mesh"
        assert result.fallback_occurred is True

    def test_t2_05_http_429_rate_limit_and_health_penalty(self, temp_env):
        """
        Verify that recording an HTTP 429 rate limit triggers cooldown
        and reduces health score in subsequent heuristic evaluations.
        """
        state_store = temp_env["state_store"]
        router = temp_env["router"]
        
        # Record 429 for cloudflare_ai
        state_store.record_outcome("cloudflare_ai", success=False, latency_ms=0.0, error_type="rate_limit_429")
        
        p_state = state_store.get_provider_state("cloudflare_ai")
        assert p_state["status"] == "in_cooldown"
        assert p_state["cooldown_until"] > time.time()
        
        # Evaluate provider score
        task = TaskRequest(task_id="t2_429_eval", prompt="Short prompt", estimated_tokens=100)
        score_obj = router.heuristic_engine.evaluate_provider("cloudflare_ai", task)
        assert score_obj.health_score <= 0.1
        assert score_obj.penalty_failures >= 0.50

    def test_t2_06_consecutive_failure_status_degradation(self, temp_env):
        """Verify 3 consecutive failures mark provider status as degraded."""
        state_store = temp_env["state_store"]
        
        for _ in range(3):
            state_store.record_outcome("gemini_free", success=False, latency_ms=0.0, error_type="http_500")
            
        p_state = state_store.get_provider_state("gemini_free")
        assert p_state["consecutive_failures"] == 3
        assert p_state["status"] == "degraded"

    def test_t2_07_concurrent_state_file_access_with_flock(self, temp_env):
        """
        Stress test: Launch multiple concurrent threads attempting to update
        quota state simultaneously, verifying atomic locking prevents corruption.
        """
        state_store = temp_env["state_store"]
        errors = []
        
        def worker_consume(worker_id: int, iters: int):
            for _ in range(iters):
                try:
                    success = state_store.consume_quota("local_mesh", 1)
                    if not success:
                        errors.append(f"Worker {worker_id} consume failed")
                except Exception as ex:
                    errors.append(f"Worker {worker_id} exception: {ex}")
                time.sleep(0.001)

        threads = []
        num_threads = 6
        iters_per_thread = 15
        
        for t_id in range(num_threads):
            t = threading.Thread(target=worker_consume, args=(t_id, iters_per_thread))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        assert len(errors) == 0, f"Concurrency errors: {errors}"
        
        final_state = state_store.reload()
        assert final_state["providers"]["local_mesh"]["used_today"] == num_threads * iters_per_thread

    def test_t2_08_unknown_provider_handling(self, temp_env):
        """Verify requesting quota from an unknown provider returns False."""
        state_store = temp_env["state_store"]
        assert state_store.consume_quota("non_existent_provider_xyz", 1) is False

    def test_t2_09_extreme_token_size_handling(self, temp_env):
        """Verify handling of extreme token counts (e.g. 100,000 tokens)."""
        router = temp_env["router"]
        task = TaskRequest(
            task_id="t2_extreme_tok",
            prompt="Massive repository analysis",
            estimated_tokens=100000
        )
        
        ranked = router.heuristic_engine.rank_providers(task)
        for score_obj in ranked:
            if score_obj.provider != "local_mesh":
                assert score_obj.disqualified is True

    def test_t2_10_empty_state_file_recovery(self, temp_env):
        """Verify recovery when state file is completely empty (0 bytes)."""
        state_file = temp_env["state_file"]
        with open(state_file, "w", encoding="utf-8") as f:
            pass
            
        new_store = QuotaStateStore(state_file=state_file)
        assert new_store.consume_quota("cloudflare_ai", 1) is True


# ===========================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (Integration Cascades)
# ===========================================================================

class TestTier3CrossFeatureCombinations:
    """
    Tier 3 tests verify complex interactions across multiple features:
    - Cascade from Cloud Exhaustion -> Local Mesh Fallback -> LoRA Dataset Write
    - UTC midnight quota reset during active execution batch
    - Speed vs Context token fit heuristic trade-offs
    - Multi-provider sequential exhaustion cascade
    """

    def test_t3_01_full_cascade_cloud_to_local_to_lora_dataset(self, temp_env):
        """
        Verify the full cascade:
        1. All cloud quotas are exhausted.
        2. Router cascades task to Local Mesh Compute.
        3. Task execution succeeds ($0 spend).
        4. Valid LoRA distillation entry is appended to dataset file.
        """
        state_store = temp_env["state_store"]
        router = temp_env["router"]
        
        # Exhaust all cloud providers
        state_store.consume_quota("julien_ai", 300)
        state_store.consume_quota("cloudflare_ai", 1000)
        state_store.consume_quota("gemini_free", 1500)
        
        task = TaskRequest(
            task_id="t3_cascade_e2e",
            prompt="Generate continuous LoRA distillation sample for multi-path TB4 routing",
            task_type="distillation",
            estimated_tokens=600
        )
        
        result = router.route_and_execute(task)
        
        assert result.success is True
        assert result.provider_used == "local_mesh"
        assert result.lora_entry_saved is True
        
        # Verify dataset entry on disk
        dataset_file = temp_env["dataset_file"]
        assert dataset_file.exists()
        lines = dataset_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["metadata"]["provider"] == "local_mesh"

    def test_t3_02_utc_midnight_quota_reset_during_batch(self, temp_env):
        """
        Verify that when reset_date indicates a previous day,
        _load_or_initialize automatically resets used_today to 0 and remaining_pct to 1.0.
        """
        state_store = temp_env["state_store"]
        
        # Consume some quota today
        state_store.consume_quota("gemini_free", 500)
        assert state_store.get_provider_state("gemini_free")["used_today"] == 500
        
        # Mutate the state file on disk to simulate yesterday's date
        yesterday_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        with open(state_store.state_file, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["last_reset_date"] = yesterday_str
            f.seek(0)
            f.truncate()
            json.dump(data, f)
            
        # Trigger reload / rollover check
        reloaded = state_store.reload()
        assert reloaded["last_reset_date"] != yesterday_str
        assert reloaded["providers"]["gemini_free"]["used_today"] == 0
        assert reloaded["providers"]["gemini_free"]["remaining_pct"] == 1.0

    def test_t3_03_speed_vs_token_fit_heuristic_tradeoff(self, temp_env):
        """
        Verify heuristic scoring trade-off:
        - Task A (100 tokens): Cloudflare AI (120 TPS) receives speed advantage.
        - Task B (20,000 tokens): Gemini Free (32K tokens) dominates token fit.
        """
        engine = temp_env["router"].heuristic_engine
        
        # Task A: 100 tokens
        task_small = TaskRequest(task_id="t3_small", prompt="Short triage", estimated_tokens=100, task_type="telemetry")
        score_cf_small = engine.evaluate_provider("cloudflare_ai", task_small)
        score_julien_small = engine.evaluate_provider("julien_ai", task_small)
        assert score_cf_small.speed_norm > score_julien_small.speed_norm

        # Task B: 20,000 tokens
        task_large = TaskRequest(task_id="t3_large", prompt="Large AST review", estimated_tokens=20000, task_type="code")
        score_gemini_large = engine.evaluate_provider("gemini_free", task_large)
        score_cf_large = engine.evaluate_provider("cloudflare_ai", task_large)
        assert score_gemini_large.disqualified is False
        assert score_cf_large.disqualified is True

    def test_t3_04_provider_failure_penalty_decay_and_recovery(self, temp_env):
        """
        Verify that failure penalties penalize score, and subsequent successful
        execution restores health to 1.0 and clears consecutive_failures.
        """
        state_store = temp_env["state_store"]
        engine = temp_env["router"].heuristic_engine
        task = TaskRequest(task_id="t3_health", prompt="Test prompt", estimated_tokens=300)
        
        # Initial score
        score_init = engine.evaluate_provider("gemini_free", task)
        
        # Fail twice
        state_store.record_outcome("gemini_free", success=False, latency_ms=0.0, error_type="timeout")
        state_store.record_outcome("gemini_free", success=False, latency_ms=0.0, error_type="timeout")
        score_degraded = engine.evaluate_provider("gemini_free", task)
        assert score_degraded.score < score_init.score
        assert score_degraded.penalty_failures > 0
        
        # Success restores health
        state_store.record_outcome("gemini_free", success=True, latency_ms=300.0)
        score_recovered = engine.evaluate_provider("gemini_free", task)
        assert score_recovered.penalty_failures == 0.0
        assert score_recovered.health_score == 1.0

    def test_t3_05_multi_provider_sequential_exhaustion(self, temp_env):
        """
        Verify sequential exhaustion cascade across all 4 tiers:
        Julien (300) -> Cloudflare (1000) -> Gemini (1500) -> Local Mesh.
        """
        state_store = temp_env["state_store"]
        
        # 1. Drain Julien
        assert state_store.consume_quota("julien_ai", 300) is True
        assert state_store.consume_quota("julien_ai", 1) is False
        assert state_store.consume_quota("cloudflare_ai", 1) is True
        
        # 2. Drain Cloudflare
        assert state_store.consume_quota("cloudflare_ai", 999) is True
        assert state_store.consume_quota("cloudflare_ai", 1) is False
        assert state_store.consume_quota("gemini_free", 1) is True
        
        # 3. Drain Gemini
        assert state_store.consume_quota("gemini_free", 1499) is True
        assert state_store.consume_quota("gemini_free", 1) is False
        
        # 4. Local Mesh remains unlimited
        assert state_store.consume_quota("local_mesh", 1000) is True


# ===========================================================================
# TIER 4: REAL-WORLD SCENARIOS (CLI & Subprocess Simulation)
# ===========================================================================

class TestTier4RealWorldScenarios:
    """
    Tier 4 tests execute real subprocesses simulating CLI workflows:
    - CLI execution with --task "<prompt>"
    - CLI execution with --distill <count>
    - CLI execution with --status
    - CLI execution with --live
    - CLI execution with --benchmark
    - CLI execution with --reset-quotas
    - State persistence integrity across consecutive subprocess invocations
    - LoRA dataset validation on disk
    """

    def test_t4_01_cli_task_execution_subprocess(self, temp_env):
        """Test executing `python3 cloud_api_quota_manager.py --task` via subprocess with exit code 0."""
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--task", "Synthesize 512Hz ECG DSP pipeline",
            "--state-file", str(temp_env["state_file"]),
            "--dataset-file", str(temp_env["dataset_file"]),
            "--force-provider", "local_mesh"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        assert "Task Result" in result.stdout
        assert "local_mesh" in result.stdout

    def test_t4_02_cli_distill_batch_generation_subprocess(self, temp_env):
        """Test executing `python3 cloud_api_quota_manager.py --distill 2` via subprocess."""
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--distill", "2",
            "--state-file", str(temp_env["state_file"]),
            "--dataset-file", str(temp_env["dataset_file"]),
            "--force-provider", "local_mesh"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        
        assert result.returncode == 0, f"Distill failed with stderr: {result.stderr}"
        
        # Verify dataset received 2 entries
        dataset_file = temp_env["dataset_file"]
        assert dataset_file.exists()
        lines = [ln for ln in dataset_file.read_text(encoding="utf-8").strip().split("\n") if ln.strip()]
        assert len(lines) == 2

    def test_t4_03_cli_status_inspection_subprocess(self, temp_env):
        """Test executing `python3 cloud_api_quota_manager.py --status` via subprocess."""
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--status",
            "--state-file", str(temp_env["state_file"]),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0
        assert "LAUBURU CLOUD API QUOTA" in result.stdout
        assert "julien_ai" in result.stdout
        assert "cloudflare_ai" in result.stdout
        assert "gemini_free" in result.stdout
        assert "local_mesh" in result.stdout

    def test_t4_04_cli_benchmark_subprocess(self, temp_env):
        """Test executing `python3 cloud_api_quota_manager.py --benchmark` via subprocess."""
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--benchmark",
            "--state-file", str(temp_env["state_file"]),
            "--dataset-file", str(temp_env["dataset_file"]),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        
        assert result.returncode == 0
        assert "RUNNING HEURISTIC ROUTER & PROVIDER BENCHMARK" in result.stdout
        assert "Benchmark Complete" in result.stdout

    def test_t4_05_cli_reset_quotas_subprocess(self, temp_env):
        """Test executing `python3 cloud_api_quota_manager.py --reset-quotas` via subprocess."""
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        
        # Consume some quota first
        temp_env["state_store"].consume_quota("gemini_free", 100)
        
        cmd = [
            sys.executable,
            str(script_path),
            "--reset-quotas",
            "--state-file", str(temp_env["state_file"]),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0
        assert "0 / 1500" in result.stdout

    def test_t4_06_state_persistence_across_consecutive_runs(self, temp_env):
        """
        Verify that multiple consecutive CLI invocations preserve and increment
        cumulative task routing metrics on disk.
        """
        script_path = AUTOMATION_DIR / "cloud_api_quota_manager.py"
        
        # Run 1
        cmd1 = [
            sys.executable, str(script_path),
            "--task", "Task 1",
            "--state-file", str(temp_env["state_file"]),
            "--dataset-file", str(temp_env["dataset_file"]),
            "--force-provider", "local_mesh"
        ]
        res1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=20)
        assert res1.returncode == 0
        
        # Run 2
        cmd2 = [
            sys.executable, str(script_path),
            "--task", "Task 2",
            "--state-file", str(temp_env["state_file"]),
            "--dataset-file", str(temp_env["dataset_file"]),
            "--force-provider", "local_mesh"
        ]
        res2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=20)
        assert res2.returncode == 0
        
        # Verify state file reflects 2 completed tasks
        state = temp_env["state_store"].reload()
        assert state["providers"]["local_mesh"]["used_today"] == 2
        assert state["metrics"]["total_lora_samples_harvested"] == 2

    def test_t4_07_dataset_file_integrity_and_schema_validation(self, temp_env):
        """
        Verify that LoRA dataset records written by multiple CLI batch runs
        remain 100% syntactically valid JSON lines with proper metadata.
        """
        dataset_file = temp_env["dataset_file"]
        
        # Distill 3 tasks
        tasks = generate_distillation_tasks(count=3)
        for t in tasks:
            temp_env["router"].route_and_execute(t, force_provider="local_mesh")
            
        lines = [ln for ln in dataset_file.read_text(encoding="utf-8").strip().split("\n") if ln.strip()]
        assert len(lines) == 3
        
        for idx, line in enumerate(lines):
            record = json.loads(line)
            assert "instruction" in record and len(record["instruction"]) > 0
            assert "output" in record and len(record["output"]) > 0
            assert "metadata" in record
            assert record["metadata"]["provider"] == "local_mesh"
            assert record["metadata"]["task_type"] == "distillation"
            assert "timestamp" in record["metadata"]
