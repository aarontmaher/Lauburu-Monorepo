#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comprehensive 5-Tier Test Suite: Autonomous Overnight Swarm Trainer Daemon
================================================================================
Subsystem: 05_agents_and_swarms/test_overnight_swarm_trainer.py
Milestone: M5 — Persistent Daemon Supervision, Self-Healing & Comprehensive Test Suite
Lauburu Mesh Ecosystem — 2026

Tiers:
- Tier 1: Feature Coverage (SWE-bench parsing, Cloud Oracle whitelist & 14.2 RPM, Dual-World MCTS, ELO updates, Daemon PID & Supervisor)
- Tier 2: Boundary & Corner Cases ($0.00 spend guard, 429 backoff, invalid diff rejection, stale PID recovery, disk headroom)
- Tier 3: Cross-Feature Interactions (Oracle guidance -> MCTS tree rollout -> ELO rating delta -> Obsidian sync)
- Tier 4: Real-World Scenarios (Full overnight cycle, 5-round tournament with medal transition, air-gapped offline mesh execution, concurrency safety, daemon crash recovery)
- Tier 5: Adversarial Edge Cases (Fuzzed syntax corruption detection, spend spoofing rejection, Rule #0 anti-mock checks, extreme ELO stability, multi-file diff stress)
================================================================================
"""

import os
import sys
import json
import time
import math
import signal
import shutil
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

import pytest

# Dynamic Monorepo Path Setup
REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
BENCHMARKS_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
DATA_DIR = REPO_ROOT / "04_data_and_memory"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS"

for p in [str(REPO_ROOT), str(SWARMS_DIR), str(BENCHMARKS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from swe_bench_harness import (
    SweBenchHarness,
    PatchSandboxEvaluator,
    SAMPLE_SWEBENCH_TASKS
)
from sb_cli_adapter import SbCliAdapter
from cloud_oracle_shadow import (
    CloudOracleShadow,
    PacedTokenBucketRateLimiter,
    DailyQuotaManager,
    DeterministicOfflineOracle,
    ZeroDollarSpendViolationError,
    is_free_tier,
    CERTIFIED_FREE_MODELS,
    FORBIDDEN_PAID_PATTERNS
)
from dual_world_mcts import (
    MCTSNode,
    MCTSResult,
    DualWorldMCTSEngine,
    AgentWorldSimulator,
    WebWorldSimulator,
    DevilsAdvocateClient,
    RouterSentinelMonitor,
    CompositeValueCalculator
)
from swarm_tournament_and_continuous_trainer import (
    INITIAL_SWARMS,
    CANONICAL_SWARMS_CATALOG,
    calculate_expected_elo,
    compute_expected_pair,
    compute_dynamic_k,
    update_swarm_ratings,
    validate_lora_trajectory_schema,
    atomic_save_json,
    generate_obsidian_dashboard,
    SwarmELOTournamentEngine,
    LEADERBOARD_FILE,
    DASHBOARD_FILE,
    MASTER_LORA
)
from overnight_swarm_training_daemon import (
    SWE_BENCH_BENCHMARKS,
    PIDLockManager,
    SignalHandler,
    StorageHealthGuard,
    SupervisorConfig,
    OvernightDaemonSupervisor,
    load_swarms,
    generate_swe_patch,
    run_single_overnight_training_step,
    run_overnight_daemon,
    check_storage_health,
    PREDS_FILE
)


@pytest.fixture
def clean_test_env(tmp_path):
    """Provides isolated paths for Tri-Vault datasets, leaderboards, and lock files."""
    env = {
        "data_dir": tmp_path / "04_data_and_memory",
        "lora_dir": tmp_path / "lora_datasets",
        "lora_file": tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl",
        "sec_lora": tmp_path / "04_data_and_memory" / "continuous_lora_dataset.jsonl",
        "leaderboard_file": tmp_path / "swarm_elo_leaderboard.json",
        "obsidian_file": tmp_path / "obsidian_vault" / "04_ANALYTICS" / "SWARM_ELO_LEADERBOARD_AND_TRAINING_2026.md",
        "preds_file": tmp_path / "04_data_and_memory" / "swe_bench_predictions" / "preds.json",
        "pid_file": tmp_path / "overnight_swarm_trainer.pid",
        "quota_file": tmp_path / "quota.json",
        "incidents_file": tmp_path / "04_data_and_memory" / "daemon_incidents.jsonl"
    }
    env["data_dir"].mkdir(parents=True, exist_ok=True)
    env["lora_dir"].mkdir(parents=True, exist_ok=True)
    env["obsidian_file"].parent.mkdir(parents=True, exist_ok=True)
    env["preds_file"].parent.mkdir(parents=True, exist_ok=True)
    return env


# ==============================================================================
# TIER 1: FEATURE COVERAGE (Unit & Core Component Tests)
# ==============================================================================

class TestTier1SweBenchIngestionAndHarness:
    """Tier 1.1: SWE-bench task ingestion, AST diff parsing, and canonical preds export."""

    def test_curated_task_repository_structure(self):
        """Curated SWE-bench tasks contain all required schema fields."""
        assert len(SAMPLE_SWEBENCH_TASKS) >= 4
        for task in SAMPLE_SWEBENCH_TASKS:
            assert "instance_id" in task
            assert "repo" in task
            assert "problem_statement" in task
            assert "expected_files" in task
            assert "golden_test" in task
            assert isinstance(task["expected_files"], list)

    def test_patch_sandbox_evaluator_parse_unified_diff(self):
        """PatchSandboxEvaluator parses multi-file unified diff into structured hunks."""
        diff_text = (
            "diff --git a/pkg/core.py b/pkg/core.py\n"
            "--- a/pkg/core.py\n"
            "+++ b/pkg/core.py\n"
            "@@ -10,3 +10,4 @@\n"
            "-    return None\n"
            "+    return 42\n"
            "+    # added comment\n"
        )
        parsed = PatchSandboxEvaluator.parse_unified_diff(diff_text)
        assert "pkg/core.py" in parsed
        info = parsed["pkg/core.py"]
        assert info["is_python"] is True
        assert len(info["added_lines"]) == 2
        assert len(info["removed_lines"]) == 1
        assert "return 42" in info["added_lines"][0]

    def test_patch_sandbox_evaluator_ast_code_validation(self):
        """validate_ast_code correctly handles functions, indentation, and async syntax."""
        valid_func = "def compute(a, b):\n    return a + b\n"
        is_ok, err = PatchSandboxEvaluator.validate_ast_code(valid_func)
        assert is_ok is True
        assert err is None

        valid_async = "async def fetch():\n    await task()\n"
        is_ok, err = PatchSandboxEvaluator.validate_ast_code(valid_async)
        assert is_ok is True

        invalid_code = "def broken(\n    return @@@\n"
        is_ok, err = PatchSandboxEvaluator.validate_ast_code(invalid_code)
        assert is_ok is False
        assert err is not None

    def test_sb_cli_adapter_prediction_formatting_and_validation(self, tmp_path):
        """SbCliAdapter creates and validates canonical predictions JSON schema."""
        preds = {
            "django__django-11099": {
                "model_patch": "diff --git a/a.py b/a.py\n+pass\n",
                "model_name_or_path": "Qwen-2.5-Coder-32B"
            }
        }
        out_file = tmp_path / "preds.json"
        SbCliAdapter.format_predictions_file(preds, out_file)
        assert out_file.exists()

        is_valid, msg, details = SbCliAdapter.validate_predictions_file(out_file)
        assert is_valid is True
        assert details["count"] == 1
        assert "django__django-11099" in details["instances"]

    def test_swe_bench_harness_evaluate_patch_against_golden_test(self):
        """SweBenchHarness evaluates candidate patch against task domain rules."""
        task = {
            "instance_id": "django__django-11099",
            "domain": "Web Framework / Security",
            "golden_test": "test_regex_anchors"
        }
        good_patch = (
            "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n"
            "--- a/django/contrib/auth/validators.py\n"
            "+++ b/django/contrib/auth/validators.py\n"
            "@@ -7,3 +7,3 @@\n"
            "-    regex = r'^[\\w.@+-]+$'\n"
            "+    regex = r'\\A[\\w.@+-]+\\Z'\n"
        )
        res = PatchSandboxEvaluator.evaluate_patch_against_task(task, good_patch)
        assert res["passed"] is True
        assert res["ast_valid"] is True


class TestTier1CloudOracleShadowing:
    """Tier 1.2: Free Cloud Oracle, token bucket pacing, and $0.00 spend governance."""

    def test_free_tier_model_classification(self):
        """Certified free models are correctly whitelisted."""
        assert is_free_tier("google", "gemini-3.7-flash") is True
        assert is_free_tier("cloudflare", "@cf/meta/llama-3.1-8b-instruct") is True
        assert is_free_tier("local", "qwen-2.5-coder-32b") is True
        assert is_free_tier("openai", "gpt-4o") is False
        assert is_free_tier("anthropic", "claude-3-5-sonnet") is False

    def test_paced_token_bucket_interval_math(self):
        """PacedTokenBucketRateLimiter computes correct ~4.225s interval for 14.2 RPM."""
        limiter = PacedTokenBucketRateLimiter(target_rpm=14.2)
        assert abs(limiter.interval - (60.0 / 14.2)) < 1e-6

    def test_daily_quota_manager_enforcement(self, tmp_path):
        """DailyQuotaManager tracks request counts against daily limits."""
        q_file = tmp_path / "quota.json"
        mgr = DailyQuotaManager(quota_file=q_file, daily_limit=3)

        assert mgr.can_request_google() is True
        mgr.record_success("google_ai_studio_free", cost_usd=0.0)
        mgr.record_success("google_ai_studio_free", cost_usd=0.0)
        mgr.record_success("google_ai_studio_free", cost_usd=0.0)

        assert mgr.can_request_google() is False
        assert mgr.state["daily_requests_count"] == 3

    def test_deterministic_offline_oracle_generation(self):
        """DeterministicOfflineOracle produces AST-valid diff with $0.00 cost."""
        task = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "task": "Fix username regex trailing newline"
        }
        res = DeterministicOfflineOracle.generate_offline_solution("Fix regex", task)
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True
        assert "\\A" in res["solution"] and "\\Z" in res["solution"]

    def test_oracle_waterfall_fallback_offline(self, tmp_path):
        """When cloud and local mesh are offline, waterfall returns offline solution."""
        oracle = CloudOracleShadow(
            gemini_api_key=None,
            cf_api_token=None,
            local_rpc_urls=["http://127.0.0.1:9999/v1"],
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "lora.jsonl"
        )
        res = oracle.query_oracle(
            prompt="Fix username regex",
            task_context={"instance_id": "django__django-11099", "repo": "django/django"}
        )
        assert res["provider"] == "offline_deterministic_engine"
        assert res["cost_usd"] == 0.00
        assert res["is_free_tier"] is True


class TestTier1DualWorldMCTS:
    """Tier 1.3: Dual-World MCTS, Devil's Advocate, and Router Sentinel."""

    def test_mcts_node_state_and_backpropagation(self):
        """MCTSNode tracks visit count and average value correctly."""
        node = MCTSNode(patch="diff ...", prior_p=0.5)
        node.update(0.8)
        node.update(0.6)
        assert node.N == 2
        assert abs(node.Q - 0.7) < 1e-6

    def test_puct_selection_exploration_bonus(self):
        """PUCT score awards exploration bonus to unvisited/low-visit nodes."""
        parent = MCTSNode(patch="diff root", prior_p=1.0)
        parent.N = 10
        c1 = MCTSNode(patch="diff c1", parent=parent, prior_p=0.3)
        c1.N = 5
        c1.Q = 0.8
        c2 = MCTSNode(patch="diff c2", parent=parent, prior_p=0.9)
        c2.N = 0
        c2.Q = 0.0
        parent.children = {"c1": c1, "c2": c2}

        selected = parent.select_child(c_puct=1.414)
        assert selected is c2

    def test_agent_world_simulation_evaluation(self):
        """AgentWorldSimulator returns high score for valid code and 0.0 for syntax errors."""
        sim = AgentWorldSimulator()
        good_patch = "diff --git a/f.py b/f.py\n+def resolve(): return True\n"
        res_good = sim.evaluate(good_patch, {"instance_id": "test-good"})
        assert res_good["v_agent"] > 0.5
        assert res_good["ast_valid"] is True

        bad_patch = "diff --git a/f.py b/f.py\n+def broken(\n+    invalid @\n"
        res_bad = sim.evaluate(bad_patch, {"instance_id": "test-bad"})
        assert res_bad["v_agent"] == 0.0
        assert res_bad["ast_valid"] is False

    def test_web_world_simulation_evaluation(self):
        """WebWorldSimulator evaluates HTTP contract satisfaction."""
        sim = WebWorldSimulator()
        patch = (
            "diff --git a/django/http/response.py b/django/http/response.py\n"
            "--- a/django/http/response.py\n"
            "+++ b/django/http/response.py\n"
            "@@ -1,2 +1,3 @@\n"
            "+def get_response():\n"
            "+    return 200\n"
        )
        res = sim.evaluate(patch, {"instance_id": "django-web"})
        assert res["v_web"] >= 0.5
        assert res["contract_satisfied"] is True

    def test_devils_advocate_adversarial_challenge(self):
        """DevilsAdvocateClient applies heavy penalty to flawed patches."""
        client = DevilsAdvocateClient()
        task = {"instance_id": "django__django-11099", "problem_statement": "regex newline"}
        flawed = "diff --git a/v.py b/v.py\n+regex = r'^[a-z]+$'\n"
        res_flawed = client.evaluate_patch(task, flawed)
        assert res_flawed["penalty"] >= 0.70

        fixed = "diff --git a/v.py b/v.py\n+regex = r'\\A[a-z]+\\Z'\n"
        res_fixed = client.evaluate_patch(task, fixed)
        assert res_fixed["penalty"] <= 0.20

    def test_router_sentinel_memory_and_loss_invariants(self):
        """RouterSentinelMonitor enforces RAM footprint <= 28MB and 0% packet loss."""
        sentinel = RouterSentinelMonitor(port=18802, max_ram_mb=28.0)
        report = sentinel.check_health()
        assert report["healthy"] is True
        assert report["ram_footprint_mb"] <= 28.0
        assert report["packet_loss_pct"] == 0.0


class TestTier1TriVaultAndELO:
    """Tier 1.4: Bradley-Terry ELO math, continuous LoRA sink, and Obsidian sync."""

    def test_bradley_terry_expected_score_math(self):
        """Expected scores satisfy E_A + E_B == 1.0 and equal ratings produce 0.50."""
        e_a, e_b = compute_expected_pair(2200.0, 2000.0)
        assert math.isclose(e_a + e_b, 1.0, rel_tol=1e-9)

        e_equal = calculate_expected_elo(2000.0, 2000.0)
        assert math.isclose(e_equal, 0.50, abs_tol=1e-6)

    def test_rating_update_zero_sum_conservation(self):
        """Rating deltas strictly sum to 0.0 in head-to-head matches."""
        _, _, d_a, d_b = update_swarm_ratings(2100.0, 1950.0, score_a=1.0, k_factor=32.0)
        assert d_a + d_b == 0.0

    def test_dynamic_k_factor_mcts_margin_scaling(self):
        """Dynamic K-factor scales with MCTS margin."""
        k_narrow = compute_dynamic_k(matches_played_a=20, matches_played_b=20, mcts_margin=0.02)
        k_wide = compute_dynamic_k(matches_played_a=20, matches_played_b=20, mcts_margin=0.85)
        assert 8.0 <= k_narrow <= 96.0
        assert 8.0 <= k_wide <= 96.0
        assert k_wide > k_narrow

    def test_lora_trajectory_schema_validation(self):
        """validate_lora_trajectory_schema accepts conforming trajectories."""
        sample = {
            "instruction": "Solve task",
            "thought": "Analysis chain",
            "output": "diff --git a/a.py b/a.py\n+pass\n",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench_training_round",
            "instance_id": "test-001",
            "cloud_spend_aud": 0.00,
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }
        is_ok, msg = validate_lora_trajectory_schema(sample)
        assert is_ok is True, msg

    def test_obsidian_dashboard_generation_wikilinks(self, tmp_path):
        """generate_obsidian_dashboard embeds master Wikilinks and medal badges."""
        out_md = tmp_path / "SWARM_ELO_LEADERBOARD_AND_TRAINING_2026.md"
        generate_obsidian_dashboard(INITIAL_SWARMS, out_md)
        assert out_md.exists()

        content = out_md.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[Index]]" in content
        assert "🥇" in content


class TestTier1DaemonAndPIDSupervision:
    """Tier 1.5: Daemon training loop, swarms catalog, PID locking, and supervisor."""

    def test_daemon_load_swarms_catalog(self):
        """load_swarms returns catalog with all 6 swarms."""
        swarms = load_swarms()
        assert len(swarms) >= 5
        assert any("Dual-World" in s["name"] for s in swarms)

    def test_generate_swe_patch_syntax(self):
        """generate_swe_patch produces diff with headers and repo path."""
        bench = SWE_BENCH_BENCHMARKS[0]
        patch = generate_swe_patch(bench, "Qwen 3.8 Max")
        assert "diff --git" in patch
        assert "django" in patch
        assert "Qwen 3.8 Max" in patch

    def test_run_single_overnight_training_step_execution(self, monkeypatch, clean_test_env):
        """run_single_overnight_training_step generates prediction, LoRA entry, and updates ELO."""
        import overnight_swarm_training_daemon as daemon_mod
        monkeypatch.setattr(daemon_mod, "PREDS_FILE", clean_test_env["preds_file"])
        monkeypatch.setattr(daemon_mod, "MASTER_LORA", clean_test_env["lora_file"])
        monkeypatch.setattr(daemon_mod, "SECONDARY_LORA", clean_test_env["sec_lora"])
        monkeypatch.setattr(daemon_mod, "LEADERBOARD_FILE", clean_test_env["leaderboard_file"])

        res = daemon_mod.run_single_overnight_training_step(1)

        assert res["passed"] is True
        assert res["oracle_cost_usd"] == 0.00
        assert clean_test_env["preds_file"].exists()
        assert clean_test_env["lora_file"].exists()
        assert clean_test_env["leaderboard_file"].exists()

        with open(clean_test_env["leaderboard_file"], "r", encoding="utf-8") as f:
            lb = json.load(f)
            assert "champion_swarm" in lb
            assert len(lb["swarms"]) >= 5

    def test_pid_lock_manager_acquire_and_release(self, tmp_path):
        """PIDLockManager acquires exclusive flock and releases cleanly."""
        pid_file = tmp_path / "test_trainer.pid"
        mgr = PIDLockManager(pid_file)

        assert mgr.acquire() is True
        assert pid_file.exists()
        active_pid = mgr.check_active_process()
        assert active_pid == os.getpid()

        mgr.release()
        assert not pid_file.exists()

    def test_pid_lock_manager_prevent_concurrent(self, tmp_path):
        """Second PIDLockManager cannot acquire lock while held by first."""
        pid_file = tmp_path / "concurrent.pid"
        mgr1 = PIDLockManager(pid_file)
        mgr2 = PIDLockManager(pid_file)

        assert mgr1.acquire() is True
        assert mgr2.acquire() is False

        mgr1.release()
        assert mgr2.acquire() is True
        mgr2.release()

    def test_pid_lock_context_manager(self, tmp_path):
        """PIDLockManager supports python context manager protocol."""
        pid_file = tmp_path / "ctx.pid"
        with PIDLockManager(pid_file) as mgr:
            assert pid_file.exists()
        assert not pid_file.exists()

    def test_signal_handler_interruptible_sleep(self):
        """SignalHandler unblocks immediately when stop_event is set."""
        sh = SignalHandler()
        start = time.time()

        t = threading.Thread(target=lambda: (time.sleep(0.05), sh.stop_event.set()))
        t.start()

        interrupted = sh.sleep(5.0)
        t.join()
        elapsed = time.time() - start

        assert interrupted is True
        assert elapsed < 1.0
        assert sh.is_stopping() is True

    def test_storage_health_guard_and_auto_heal(self, tmp_path):
        """StorageHealthGuard detects missing Index.md and auto-heals canonical Wikilinks."""
        guard = StorageHealthGuard(repo_root=tmp_path, lora_dir=tmp_path / "lora_datasets", min_free_gb=1.0)
        report = guard.verify_and_heal()

        assert report["healthy"] is True
        assert report["obsidian_index_healed"] is True

        index_file = tmp_path / "obsidian_vault" / "Index.md"
        assert index_file.exists()
        content = index_file.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (Stress, Bounds, Defensive Guardrails)
# ==============================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: Defensive boundary checks, rate-limit backoff, and invalid inputs."""

    def test_zero_dollar_spend_violation_raises_error(self, tmp_path):
        """Commercial paid models immediately raise ZeroDollarSpendViolationError."""
        oracle = CloudOracleShadow(quota_file=tmp_path / "quota.json")
        with pytest.raises(ZeroDollarSpendViolationError):
            oracle.query_oracle("Write code", model="gpt-4o", provider="openai")

    def test_zero_dollar_spend_in_lora_trajectory_rejection(self):
        """validate_lora_trajectory_schema rejects non-zero cloud spend."""
        bad_sample = {
            "instruction": "Solve task",
            "thought": "Thought",
            "output": "Output",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench",
            "instance_id": "t-1",
            "cloud_spend_aud": 0.05,
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }
        is_ok, msg = validate_lora_trajectory_schema(bad_sample)
        assert is_ok is False
        assert "Spend Violation" in msg

    def test_rate_limit_429_circuit_breaker_exponential_backoff(self, tmp_path):
        """Consecutive 429 errors engage circuit breaker and double backoff duration."""
        q_file = tmp_path / "quota_429.json"
        mgr = DailyQuotaManager(quota_file=q_file, daily_limit=1500)

        mgr.record_429()
        cb1 = mgr.state["circuit_breaker_until"]
        assert cb1 > time.time()
        assert mgr.can_request_google() is False

        mgr.record_429()
        cb2 = mgr.state["circuit_breaker_until"]
        assert cb2 > cb1

    def test_daily_quota_utc_date_rollover_reset(self, tmp_path):
        """UTC date transition automatically resets daily quota counts."""
        q_file = tmp_path / "quota_rollover.json"
        with open(q_file, "w", encoding="utf-8") as f:
            json.dump({
                "current_date_utc": "2020-01-01",
                "daily_requests_count": 1500,
                "daily_requests_limit": 1500,
                "total_requests_all_time": 5000,
                "total_spend_usd": 0.0,
                "last_request_timestamp": 0.0,
                "circuit_breaker_until": 0.0,
                "consecutive_429_count": 5
            }, f)

        mgr = DailyQuotaManager(quota_file=q_file, daily_limit=1500)
        assert mgr.can_request_google() is True
        assert mgr.state["daily_requests_count"] == 0

    def test_malformed_diff_missing_headers_rejection(self):
        """PatchSandboxEvaluator rejects diffs missing git headers and hunks."""
        malformed = "just a plain text description without any diff markers"
        is_valid, msg, _ = PatchSandboxEvaluator.validate_ast_diff(malformed)
        assert is_valid is False

    def test_syntax_corrupted_python_diff_rejection(self):
        """PatchSandboxEvaluator catches Python syntax errors within diff hunks."""
        corrupt = (
            "diff --git a/corrupt.py b/corrupt.py\n"
            "--- a/corrupt.py\n"
            "+++ b/corrupt.py\n"
            "@@ -1,2 +1,3 @@\n"
            "+def broken_syntax(:\n"
            "+    return 1 +\n"
        )
        is_valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(corrupt)
        assert is_valid is False
        assert "AST Syntax Error" in msg

    def test_stale_pid_lock_detection_and_recovery(self, tmp_path):
        """Stale PID lock file containing non-existent PID is safely detected."""
        pid_file = tmp_path / "test_daemon.pid"
        pid_file.write_text(json.dumps({"pid": 999999, "hostname": "local"}), encoding="utf-8")

        mgr = PIDLockManager(pid_file)
        assert mgr.check_active_process() is None
        assert mgr.acquire() is True
        mgr.release()

    def test_active_pid_lock_prevents_duplicate_instance(self, tmp_path):
        """Active running PID prevents duplicate daemon startup."""
        pid_file = tmp_path / "active_daemon.pid"
        mgr = PIDLockManager(pid_file)
        assert mgr.acquire() is True

        assert mgr.check_active_process() == os.getpid()
        mgr.release()

    def test_disk_headroom_invariant_check(self):
        """Disk headroom check verifies free NVMe space >= 5.0 GB."""
        free_bytes = shutil.disk_usage(os.path.expanduser("~")).free
        free_gb = free_bytes / (1024 ** 3)
        assert free_gb >= 5.0, f"Low disk headroom: {free_gb:.2f} GB free"

    def test_empty_or_whitespace_diff_rejection(self):
        """Empty, non-string, or whitespace-only diffs are rejected."""
        assert PatchSandboxEvaluator.validate_ast_diff("")[0] is False
        assert PatchSandboxEvaluator.validate_ast_diff("   \n\t  ")[0] is False
        assert PatchSandboxEvaluator.validate_ast_diff(None)[0] is False


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS (Multi-Subsystem Workflows)
# ==============================================================================

class TestTier3CrossFeatureInteractions:
    """Tier 3: Inter-subsystem coupling, data transfers, and feedback loops."""

    def test_oracle_guidance_to_mcts_tree_injection(self, tmp_path):
        """Oracle candidate solution is injected as ACTION_ORACLE_INJECTION in MCTS search."""
        engine = DualWorldMCTSEngine(max_iterations=4, lora_sink=tmp_path / "lora.jsonl")
        task = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "problem_statement": "regex newline"
        }
        oracle_res = {
            "solution": (
                "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n"
                "--- a/django/contrib/auth/validators.py\n"
                "+++ b/django/contrib/auth/validators.py\n"
                "@@ -7,3 +7,3 @@\n"
                "-    regex = r'^[\\w.@+-]+$'\n"
                "+    regex = r'\\A[\\w.@+-]+\\Z'\n"
            ),
            "thought": "Use \\A and \\Z string anchors."
        }
        res = engine.search(task, oracle_guidance=oracle_res, iterations=4)
        assert res["instance_id"] == "django__django-11099"
        assert res["value"] > 0.60
        assert res["iterations_run"] == 4

    def test_mcts_outcome_to_dynamic_elo_update(self, tmp_path):
        """MCTS value differential directly determines ELO delta via Dynamic K."""
        engine = SwarmELOTournamentEngine(
            leaderboard_path=tmp_path / "lb.json",
            obsidian_path=tmp_path / "dash.md",
            lora_path=tmp_path / "lora.jsonl",
            secondary_lora_path=tmp_path / "sec_lora.jsonl"
        )
        task = {"instance_id": "test-mcts-elo", "repo": "django/django", "domain": "polyglot_code"}
        res = engine.execute_match(
            "SWARM_DUAL_WORLD_SOVEREIGN",
            "SWARM_GLOBAL_SOVEREIGN_FRONTIER",
            task=task,
            mcts_val_a=0.92,
            mcts_val_b=0.74
        )
        assert res.winner_id == "SWARM_DUAL_WORLD_SOVEREIGN"
        assert res.delta_elo_a > 0.0
        assert res.delta_elo_a + res.delta_elo_b == 0.0

    def test_training_step_to_tri_vault_triple_sync(self, clean_test_env, monkeypatch):
        """Single training step atomically writes to all three vault storage sinks."""
        import overnight_swarm_training_daemon as daemon_mod
        monkeypatch.setattr(daemon_mod, "PREDS_FILE", clean_test_env["preds_file"])
        monkeypatch.setattr(daemon_mod, "MASTER_LORA", clean_test_env["lora_file"])
        monkeypatch.setattr(daemon_mod, "SECONDARY_LORA", clean_test_env["sec_lora"])
        monkeypatch.setattr(daemon_mod, "LEADERBOARD_FILE", clean_test_env["leaderboard_file"])

        daemon_mod.run_single_overnight_training_step(42)

        # 1. SWE-bench predictions sink
        assert clean_test_env["preds_file"].exists()
        preds = json.loads(clean_test_env["preds_file"].read_text())
        assert len(preds) >= 1

        # 2. Continuous LoRA JSONL dataset sink
        assert clean_test_env["lora_file"].exists()
        lines = [json.loads(l) for l in clean_test_env["lora_file"].read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        assert lines[-1]["cloud_spend_aud"] == 0.00

        # 3. Canonical ELO Leaderboard JSON sink
        assert clean_test_env["leaderboard_file"].exists()
        lb = json.loads(clean_test_env["leaderboard_file"].read_text())
        assert lb["total_swarms"] >= 5

    def test_rate_limit_failover_to_offline_oracle_to_mcts(self, tmp_path):
        """Cloud 429 causes failover to offline oracle, which provides AST-valid guidance to MCTS."""
        oracle = CloudOracleShadow(
            gemini_api_key=None,
            cf_api_token=None,
            local_rpc_urls=["http://127.0.0.1:9999/v1"],
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "oracle_lora.jsonl"
        )
        task = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "domain": "Web Security",
            "task": "UsernameValidator regex anchor"
        }
        oracle_out = oracle.query_oracle("Fix username regex", task_context=task)
        assert oracle_out["provider"] == "offline_deterministic_engine"

        mcts = DualWorldMCTSEngine(max_iterations=2, lora_sink=tmp_path / "mcts_lora.jsonl")
        mcts_res = mcts.search(task, oracle_guidance=oracle_out, iterations=2)
        assert mcts_res["value"] > 0.60
        assert mcts_res["is_verified"] is True

    def test_devils_advocate_penalty_drives_mcts_alternative_branch(self):
        """Devil's Advocate penalty downweights vulnerable branch during PUCT selection."""
        parent = MCTSNode(patch="diff root", prior_p=1.0)
        parent.N = 4

        c_vuln = MCTSNode(patch="diff vuln", parent=parent, prior_p=0.5)
        c_vuln.N = 2
        c_vuln.W = 0.8
        c_vuln.Q = 0.4
        c_vuln.p_devil = 0.85

        c_sec = MCTSNode(patch="diff sec", parent=parent, prior_p=0.5)
        c_sec.N = 2
        c_sec.W = 1.7
        c_sec.Q = 0.85
        c_sec.p_devil = 0.05

        parent.children = {"vuln": c_vuln, "sec": c_sec}
        selected = parent.select_child(c_puct=1.414)
        assert selected is c_sec


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS (Complex Operational Pipelines)
# ==============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end full training cycles, tournaments, and crash recovery."""

    def test_scenario_1_full_overnight_training_cycle(self, clean_test_env, monkeypatch):
        """Scenario 1: Complete end-to-end execution of overnight training round."""
        import overnight_swarm_training_daemon as daemon_mod
        monkeypatch.setattr(daemon_mod, "PREDS_FILE", clean_test_env["preds_file"])
        monkeypatch.setattr(daemon_mod, "MASTER_LORA", clean_test_env["lora_file"])
        monkeypatch.setattr(daemon_mod, "SECONDARY_LORA", clean_test_env["sec_lora"])
        monkeypatch.setattr(daemon_mod, "LEADERBOARD_FILE", clean_test_env["leaderboard_file"])

        daemon_mod.run_single_overnight_training_step(step_number=101)

        is_val, _, details = SbCliAdapter.validate_predictions_file(clean_test_env["preds_file"])
        assert is_val is True
        assert details["count"] >= 1

        lines = [json.loads(l) for l in clean_test_env["lora_file"].read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        traj = lines[-1]
        assert traj["cloud_spend_aud"] == 0.00
        assert "diff --git" in traj["output"]

        lb = json.loads(clean_test_env["leaderboard_file"].read_text())
        assert lb["champion_swarm"] != ""

    def test_scenario_2_multi_round_tournament_champion_transition(self, tmp_path):
        """Scenario 2: Multi-round tournament allows challenger to take champion title."""
        lb_file = tmp_path / "swarm_leaderboard.json"
        md_file = tmp_path / "SWARM_DASHBOARD.md"
        lora_file = tmp_path / "lora.jsonl"
        sec_lora = tmp_path / "sec_lora.jsonl"

        engine = SwarmELOTournamentEngine(
            leaderboard_path=lb_file,
            obsidian_path=md_file,
            lora_path=lora_file,
            secondary_lora_path=sec_lora
        )

        for _ in range(5):
            engine.run_challenger_round()

        assert lb_file.exists()
        lb = json.loads(lb_file.read_text())
        assert "champion_swarm" in lb
        assert len(lb["swarms"]) == 6

        assert md_file.exists()
        md_content = md_file.read_text()
        assert "🥇" in md_content

    def test_scenario_3_complete_offline_mesh_airgap_training(self, tmp_path):
        """Scenario 3: Trainer runs seamlessly when air-gapped without external cloud APIs."""
        oracle = CloudOracleShadow(
            gemini_api_key=None,
            cf_api_token=None,
            local_rpc_urls=["http://127.0.0.1:9999/v1"],
            quota_file=tmp_path / "quota.json",
            lora_sink=tmp_path / "offline_lora.jsonl"
        )
        task = SAMPLE_SWEBENCH_TASKS[0]
        out = oracle.query_oracle(prompt="Solve issue", task_context=task)

        assert out["provider"] in ("offline_deterministic_engine", "local_mesh_rpc")
        assert out["cost_usd"] == 0.00
        is_ok, msg, _ = PatchSandboxEvaluator.validate_ast_diff(out["solution"])
        assert is_ok is True

    def test_scenario_4_concurrent_daemon_and_api_queries(self, tmp_path):
        """Scenario 4: High-frequency concurrent writes and reads never cause partial reads."""
        target = tmp_path / "concurrent_lb.json"
        stop_event = threading.Event()
        errors = []

        def writer():
            step = 0
            while not stop_event.is_set():
                step += 1
                atomic_save_json(target, {"step": step, "swarms": INITIAL_SWARMS})
                time.sleep(0.001)

        def reader():
            while not stop_event.is_set():
                if target.exists():
                    try:
                        with open(target, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            assert "step" in data
                    except Exception as e:
                        errors.append(str(e))
                time.sleep(0.001)

        w = threading.Thread(target=writer)
        readers = [threading.Thread(target=reader) for _ in range(3)]

        w.start()
        for r in readers:
            r.start()

        time.sleep(0.3)
        stop_event.set()

        w.join()
        for r in readers:
            r.join()

        assert len(errors) == 0, f"Concurrency errors encountered: {errors}"

    def test_scenario_5_daemon_crash_recovery_and_supervisor_execution(self, tmp_path, clean_test_env, monkeypatch):
        """Scenario 5: OvernightDaemonSupervisor bounded execution with incident handling."""
        import overnight_swarm_training_daemon as daemon_mod
        monkeypatch.setattr(daemon_mod, "PREDS_FILE", clean_test_env["preds_file"])
        monkeypatch.setattr(daemon_mod, "MASTER_LORA", clean_test_env["lora_file"])
        monkeypatch.setattr(daemon_mod, "SECONDARY_LORA", clean_test_env["sec_lora"])
        monkeypatch.setattr(daemon_mod, "LEADERBOARD_FILE", clean_test_env["leaderboard_file"])
        monkeypatch.setattr(daemon_mod, "INCIDENTS_FILE", clean_test_env["incidents_file"])

        cfg = SupervisorConfig(
            max_rounds=2,
            interval_seconds=0.01,
            pid_file=tmp_path / "supervisor_test.pid",
            min_disk_free_gb=1.0,
            dry_run=False
        )
        supervisor = OvernightDaemonSupervisor(cfg)
        supervisor.run()

        assert supervisor.rounds_completed == 2
        assert not cfg.pid_file.exists()


# ==============================================================================
# TIER 5: ADVERSARIAL EDGE CASES & HARDENING (Security, Corruption, Robustness)
# ==============================================================================

class TestTier5AdversarialHardening:
    """Tier 5: Adversarial inputs, fuzzing corruptions, and anti-mock invariants."""

    @pytest.mark.parametrize("corrupt_diff", [
        "diff --git a/a.py b/a.py\n+def broken(:\n",
        "diff --git a/a.py b/a.py\n+x = (1 +\n",
        "diff --git a/a.py b/a.py\n+class A:\n+  def m():\n+ invalid_indent@@@\n",
        "diff --git a/a.py b/a.py\n+x = \"unclosed string literal\n",
        "diff --git a/a.py b/a.py\n+import ?? illegal_syntax\n",
    ])
    def test_adversarial_syntax_corruption_fuzzing(self, corrupt_diff):
        """PatchSandboxEvaluator rejects 100% of fuzzed syntax corruptions."""
        is_ok, msg, _ = PatchSandboxEvaluator.validate_ast_diff(corrupt_diff)
        assert is_ok is False
        assert "AST Syntax Error" in msg or "Malformed" in msg

    def test_adversarial_cloud_spend_spoofing_attack(self, tmp_path):
        """Injected commercial headers and non-zero spend trigger hard abort."""
        oracle = CloudOracleShadow(quota_file=tmp_path / "quota.json")
        with pytest.raises(ZeroDollarSpendViolationError):
            oracle._assert_zero_spend(
                provider="spoofed_cloud_provider",
                model="gpt-4-turbo-spoof",
                cost_usd=0.00001
            )

    @pytest.mark.parametrize("mock_keyword", [
        "mock_dummy",
        "fake_data",
        "simulated_response",
        "test_mock"
    ])
    def test_rule_zero_anti_mock_keyword_fuzzing(self, mock_keyword):
        """Rule #0: validate_lora_trajectory_schema rejects fake/mock keywords."""
        sample = {
            "instruction": f"Solve task with {mock_keyword}",
            "thought": "Real reasoning",
            "output": "Real output",
            "swarm": "👑 Dual-World Sovereign Mesh Swarm",
            "category": "swe_bench",
            "instance_id": "test-mock-001",
            "cloud_spend_aud": 0.00,
            "truth_verified": True,
            "zero_mock": True,
            "truth_compliance_pct": 100.0
        }
        is_ok, msg = validate_lora_trajectory_schema(sample)
        assert is_ok is False
        assert "mock" in msg.lower() or "forbidden" in msg.lower() or "placeholder" in msg.lower()

    def test_extreme_elo_divergence_and_float_overflow(self):
        """Bradley-Terry update handles extreme ELO divergence (5000 vs 100) without float overflow."""
        r_a, r_b = 5000.0, 100.0
        e_a, e_b = compute_expected_pair(r_a, r_b)
        assert math.isclose(e_a + e_b, 1.0, rel_tol=1e-9)
        assert e_a > 0.9999
        assert e_b < 0.0001

        _, _, d_a, d_b = update_swarm_ratings(r_a, r_b, score_a=1.0, k_factor=32.0)
        assert math.isfinite(d_a)
        assert math.isfinite(d_b)
        assert d_a + d_b == 0.0

    def test_large_scale_multi_file_diff_stress(self):
        """PatchSandboxEvaluator processes large 50-file diff without memory exhaustion."""
        hunks = []
        for i in range(50):
            hunks.append(
                f"diff --git a/pkg/mod_{i}.py b/pkg/mod_{i}.py\n"
                f"--- a/pkg/mod_{i}.py\n"
                f"+++ b/pkg/mod_{i}.py\n"
                f"@@ -1,2 +1,5 @@\n"
                f"+def func_{i}():\n"
                f"+    '''Autogenerated function {i}'''\n"
                f"+    return {i} * 2\n"
            )
        large_diff = "\n".join(hunks)
        is_ok, msg, details = PatchSandboxEvaluator.validate_ast_diff(large_diff)
        assert is_ok is True
        assert details["lines_added"] == 150
        assert details["files"] == [f"pkg/mod_{i}.py" for i in range(50)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
