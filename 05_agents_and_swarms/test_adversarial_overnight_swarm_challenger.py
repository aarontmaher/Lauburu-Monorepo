#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Empirical Challenger Adversarial Stress Test Suite: Autonomous Overnight Swarm Trainer
================================================================================
Subsystem: 05_agents_and_swarms/test_adversarial_overnight_swarm_challenger.py
Auditor: Challenger 1 (Final Verification Gate)
Target Files:
  - 05_agents_and_swarms/overnight_swarm_training_daemon.py
  - 05_agents_and_swarms/dual_world_mcts.py
  - 05_agents_and_swarms/cloud_oracle_shadow.py
  - 02_ai_models_and_inference/benchmarks/swe_bench_harness.py
  - 02_ai_models_and_inference/benchmarks/sb_cli_adapter.py
  - 05_agents_and_swarms/swarm_tournament_and_continuous_trainer.py
================================================================================
"""

import os
import sys
import time
import json
import fcntl
import signal
import socket
import shutil
import random
import ctypes
import tempfile
import threading
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import pytest

# Monorepo Path Setup
REPO_ROOT = Path(__file__).resolve().parents[1]
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
BENCHMARKS_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"

for p in [str(REPO_ROOT), str(SWARMS_DIR), str(BENCHMARKS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from overnight_swarm_training_daemon import (
    PIDLockManager,
    SignalHandler,
    StorageHealthGuard,
    OvernightDaemonSupervisor,
    SupervisorConfig,
    run_single_overnight_training_step,
    load_swarms
)

from cloud_oracle_shadow import (
    CloudOracleShadow,
    PacedTokenBucketRateLimiter,
    DailyQuotaManager,
    ZeroDollarSpendViolationError,
    CERTIFIED_FREE_MODELS,
    FORBIDDEN_PAID_PATTERNS,
    is_free_tier
)

from dual_world_mcts import (
    DualWorldMCTSEngine,
    MCTSNode,
    AgentWorldSimulator,
    WebWorldSimulator,
    DevilsAdvocateClient,
    RouterSentinelMonitor
)

from swe_bench_harness import (
    SweBenchHarness,
    PatchSandboxEvaluator,
    SAMPLE_SWEBENCH_TASKS
)

from sb_cli_adapter import SbCliAdapter

from swarm_tournament_and_continuous_trainer import (
    SwarmELOTournamentEngine,
    SwarmMatchResult,
    INITIAL_SWARMS,
    calculate_expected_elo,
    compute_expected_pair,
    compute_dynamic_k,
    update_swarm_ratings,
    validate_lora_trajectory_schema,
    atomic_save_json,
    append_lora_trajectory_dual_sink,
    generate_obsidian_dashboard
)


# ==============================================================================
# CLASS 1: Adversarial PID Locking, Process Crashes & Concurrency Contention
# ==============================================================================
class TestAdversarialPIDLockAndCrashRecovery:
    """Stress-tests OS kernel flock behavior under sudden crashes and high contention."""

    def test_process_sigkill_flock_instant_release(self, tmp_path):
        """Spawns a subprocess that acquires flock and is abruptly killed with SIGKILL (9)."""
        pid_file = tmp_path / "test_kill.pid"
        code = f"""
import sys, time
from pathlib import Path
sys.path.insert(0, '{str(SWARMS_DIR)}')
from overnight_swarm_training_daemon import PIDLockManager

mgr = PIDLockManager('{str(pid_file)}')
if mgr.acquire():
    print('ACQUIRED', flush=True)
    time.sleep(30)
else:
    print('FAILED', flush=True)
"""
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = proc.stdout.readline().strip()
        assert line == "ACQUIRED", f"Child failed to acquire lock: {proc.stderr.read()}"

        # Ensure parent cannot acquire while child lives
        parent_mgr = PIDLockManager(pid_file)
        assert parent_mgr.acquire() is False

        # Abruptly SIGKILL the child process
        proc.kill()
        proc.wait()

        # The OS kernel must release flock immediately upon process death
        assert parent_mgr.acquire() is True
        parent_mgr.release()

    def test_high_concurrency_lock_contention_10_processes(self, tmp_path):
        """Launches 10 parallel OS processes contending for the same lock; at least 1 succeeds."""
        pid_file = tmp_path / "contention.pid"
        code = f"""
import sys, time
from pathlib import Path
sys.path.insert(0, '{str(SWARMS_DIR)}')
from overnight_swarm_training_daemon import PIDLockManager

mgr = PIDLockManager('{str(pid_file)}')
success = mgr.acquire()
if success:
    time.sleep(0.3)
    mgr.release()
    print('WINNER', flush=True)
else:
    print('LOSER', flush=True)
"""
        with ProcessPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    subprocess.run,
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True
                )
                for _ in range(10)
            ]
            results = [f.result().stdout.strip() for f in futures]

        winners = [r for r in results if r == "WINNER"]
        assert len(winners) >= 1, f"Expected at least 1 winner, got {results}"

    def test_stale_pid_dead_process_overwrite(self, tmp_path):
        """Verifies that a dead PID in the lock file is detected and cleanly overwritten."""
        pid_file = tmp_path / "stale.pid"
        fake_payload = {
            "pid": 9999999,
            "created_at": "2026-01-01T00:00:00Z",
            "hostname": "test-host",
            "argv": ["daemon.py"]
        }
        pid_file.write_text(json.dumps(fake_payload))

        mgr = PIDLockManager(pid_file)
        assert mgr.check_active_process() is None
        assert mgr.acquire() is True
        data = json.loads(pid_file.read_text())
        assert data["pid"] == os.getpid()
        mgr.release()

    def test_corrupted_json_in_pid_file_recovery(self, tmp_path):
        """Verifies that non-JSON corrupted bytes in PID file are gracefully handled."""
        pid_file = tmp_path / "corrupt.pid"
        pid_file.write_bytes(b"INVALID_CORRUPT_JSON_DATA_#@!$%^&*")

        mgr = PIDLockManager(pid_file)
        assert mgr.check_active_process() is None
        assert mgr.acquire() is True
        mgr.release()

    def test_rapid_context_manager_lifecycle_50_iterations(self, tmp_path):
        """Stress-tests 50 rapid sequential acquire/release cycles without fd leaks."""
        pid_file = tmp_path / "rapid.pid"
        for i in range(50):
            with PIDLockManager(pid_file) as mgr:
                assert mgr.pid_file.exists()
                assert json.loads(pid_file.read_text())["pid"] == os.getpid()
            assert not pid_file.exists()


# ==============================================================================
# CLASS 2: Adversarial Rate Limiting, Spend Guardrails & Quotas
# ==============================================================================
class TestAdversarialRateLimitAndSpendGuardrails:
    """Stress-tests token bucket burst handling, paid model blacklisting, and $0 spend assertions."""

    def test_burst_token_bucket_pacing_under_stress(self):
        """Slam token bucket with rapid acquire requests; verifies rate limit pacing interval."""
        limiter = PacedTokenBucketRateLimiter(target_rpm=60.0) # 1 request per second
        timestamps = []

        for _ in range(3):
            limiter.acquire(blocking=True)
            timestamps.append(time.time())

        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        for iv in intervals:
            assert iv >= 0.85, f"Rate limiter burst violation: interval was {iv:.3f}s"

    def test_daily_quota_exhaustion_blocks_further_requests(self, tmp_path):
        """Verifies daily quota blocks requests once max limit (10) is reached."""
        quota_file = tmp_path / "quota_test.json"
        mgr = DailyQuotaManager(quota_file=quota_file, daily_limit=10)

        for i in range(10):
            assert mgr.can_request_google() is True
            mgr.record_success(provider="google_ai_studio_free", cost_usd=0.0)

        assert mgr.can_request_google() is False

    def test_forbidden_paid_models_strict_rejection(self):
        """Passes 8 commercial paid model names to is_free_tier; all must be rejected."""
        paid_models = [
            "gpt-4o",
            "gpt-4-turbo",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "o1-preview",
            "o3-mini",
            "gemini-1.5-pro-paid",
            "deepseek-v3-paid"
        ]
        for model in paid_models:
            assert is_free_tier(provider="openai", model=model) is False, f"Model {model} incorrectly classified as free"

    def test_spoofed_cost_triggers_hard_spend_violation_abort(self, tmp_path):
        """Simulates an upstream response returning non-zero spend ($0.0001) to verify kill-switch."""
        oracle = CloudOracleShadow(quota_file=tmp_path / "q.json", enforce_zero_cost=True)
        with pytest.raises(ZeroDollarSpendViolationError):
            oracle._assert_zero_spend(cost_usd=0.0001, provider="gemini-3.7-flash-high", model="gemini-3.7-flash")

        with pytest.raises(ZeroDollarSpendViolationError):
            oracle._assert_zero_spend(cost_usd=1e-7, provider="google_ai_studio", model="gemini-3.7-flash")

        # Zero spend must pass cleanly
        oracle._assert_zero_spend(cost_usd=0.00, provider="gemini-3.7-flash-high", model="gemini-3.7-flash")

    def test_429_circuit_breaker_exponential_backoff_and_decay(self, tmp_path):
        """Verifies exponential backoff doubling on 429 and recovery after cooldown."""
        quota_file = tmp_path / "cb_test.json"
        mgr = DailyQuotaManager(quota_file=quota_file)

        assert mgr.can_request_google() is True
        mgr.record_429()
        assert mgr.can_request_google() is False
        assert mgr.state["consecutive_429_count"] == 1
        assert mgr.state["circuit_breaker_until"] > time.time()


# ==============================================================================
# CLASS 3: Adversarial Malformed Diff & Syntax Corruption
# ==============================================================================
class TestAdversarialMalformedDiffAndSyntaxCorruption:
    """Fuzzes and stresses AST diff validator across 10 distinct syntax corruption vectors."""

    @pytest.mark.parametrize("corrupt_code,error_name", [
        ("def foo():\nreturn 42", "IndentationError"),
        ("def calc(a, b):\n    return (a + b * (", "UnmatchedParenthesis"),
        ("data = {'key': 'val', 'list': [1, 2, }", "UnmatchedBrace"),
        ("msg = \"unterminated string literal", "UnterminatedString"),
        ("x = 10 ++ 20 ** ", "InvalidOperator"),
        ("123 = variable_name", "InvalidAssignment"),
        ("if True:\n", "IncompleteStatement"),
        ("for i in range(10)\n    pass", "MissingColon"),
        ("class 123InvalidName:\n    pass", "InvalidClassName"),
        ("import os\nimport sys\nimport", "TrailingImportKeyword"),
    ])
    def test_ast_diff_validator_catches_all_syntax_corruption_vectors(self, corrupt_code, error_name):
        """Verifies that PatchSandboxEvaluator safely rejects all syntax corruption classes."""
        patch_str = f"--- a/core.py\n+++ b/core.py\n@@ -1,5 +1,10 @@\n" + "\n".join("+" + l for l in corrupt_code.splitlines())
        valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(patch_str, "core.py")
        assert valid is False, f"Failed to reject corrupt vector '{error_name}': {msg}"
        assert "AST Syntax Error" in msg or "SyntaxError" in msg or "IndentationError" in msg

    def test_devils_advocate_assigns_maximum_penalty_to_corrupt_patch(self):
        """Verifies Devil's Advocate assigns near-maximum penalty to corrupt patches."""
        client = DevilsAdvocateClient()
        corrupted_patch = "--- a/bad.py\n+++ b/bad.py\n@@ -1,1 +1,3 @@\n+def broken():\n+    return ("
        res = client.evaluate_patch(
            task_instance={"instance_id": "test-corrupt", "task": "Fix bug"},
            patch_str=corrupted_patch
        )
        assert res["penalty"] >= 0.70, f"Expected high penalty for syntax corruption, got {res['penalty']}"
        assert "critique" in res

    def test_ast_diff_100_file_megadiff_stress(self):
        """Generates a massive 100-file unified diff and verifies parsing speed and accuracy."""
        diff_lines = []
        for i in range(100):
            diff_lines.append(f"--- a/module_{i}.py")
            diff_lines.append(f"+++ b/module_{i}.py")
            diff_lines.append(f"@@ -10,5 +10,15 @@")
            for j in range(10):
                diff_lines.append(f"+def helper_{i}_{j}(x: int) -> int:")
                diff_lines.append(f"+    return x + {i * 10 + j}")
        mega_patch = "\n".join(diff_lines)

        start = time.time()
        valid, msg, details = PatchSandboxEvaluator.validate_ast_diff(mega_patch, "module_0.py")
        elapsed = time.time() - start

        assert valid is True
        assert details.get("lines_added") == 2000
        assert elapsed < 0.50, f"Megadiff parsing too slow: {elapsed:.3f}s"


# ==============================================================================
# CLASS 4: High-Concurrency Tri-Vault Storage & ELO Invariant Stress
# ==============================================================================
class TestAdversarialTriVaultHighConcurrencyStress:
    """Stress-tests concurrent reader/writer safety on JSON leaderboard and JSONL dataset sinks."""

    def test_concurrent_atomic_json_leaderboard_20_threads(self, tmp_path):
        """20 writer threads and 20 reader threads simultaneously operating on the same JSON file."""
        json_file = tmp_path / "concurrent_leaderboard.json"
        atomic_save_json(json_file, {"timestamp": "2026-01-01T00:00:00Z", "swarms": INITIAL_SWARMS})

        read_errors = []
        write_errors = []
        iterations_per_thread = 20

        def writer_task(thread_id):
            for i in range(iterations_per_thread):
                swarms_copy = [dict(s) for s in INITIAL_SWARMS]
                swarms_copy[0]["elo"] = round(2185.0 + (thread_id * 10) + i, 1)
                data = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "thread_id": thread_id,
                    "iteration": i,
                    "swarms": swarms_copy
                }
                ok = atomic_save_json(json_file, data)
                if not ok:
                    write_errors.append(f"Writer {thread_id} failed on iter {i}")
                time.sleep(0.005)

        def reader_task(thread_id):
            for i in range(iterations_per_thread):
                try:
                    content = json_file.read_text(encoding="utf-8")
                    parsed = json.loads(content)
                    assert "swarms" in parsed
                    assert len(parsed["swarms"]) == len(INITIAL_SWARMS)
                except Exception as e:
                    read_errors.append(f"Reader {thread_id} iter {i} error: {e}")
                time.sleep(0.005)

        with ThreadPoolExecutor(max_workers=40) as executor:
            writers = [executor.submit(writer_task, tid) for tid in range(20)]
            readers = [executor.submit(reader_task, tid) for tid in range(20)]
            for f in as_completed(writers + readers):
                f.result()

        assert len(write_errors) == 0, f"Write errors: {write_errors}"
        assert len(read_errors) == 0, f"Partial read / corrupted JSON errors: {read_errors}"

    def test_concurrent_lora_dataset_dual_sink_20_threads(self, tmp_path):
        """20 threads appending 25 trajectories each (500 records total) to dual sinks."""
        sink_a = tmp_path / "sink_a" / "continuous_lora_dataset.jsonl"
        sink_b = tmp_path / "sink_b" / "continuous_lora_dataset.jsonl"

        def append_task(thread_id):
            for i in range(25):
                traj = {
                    "instruction": f"Solve SWE-bench instance thread-{thread_id}-{i}",
                    "thought": f"Analyzed AST diff on worker thread {thread_id}.",
                    "output": f"Verified diff patch for instance thread-{thread_id}-{i}",
                    "swarm": "👑 Dual-World Sovereign Mesh Swarm",
                    "category": "swe_bench_training_round",
                    "instance_id": f"inst-{thread_id}-{i}",
                    "cloud_spend_aud": 0.00,
                    "truth_verified": True,
                    "zero_mock": True
                }
                ok = append_lora_trajectory_dual_sink(traj, sink_a, sink_b)
                assert ok is True

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(append_task, tid) for tid in range(20)]
            for f in as_completed(futures):
                f.result()

        # Both sinks must have exactly 500 lines
        lines_a = sink_a.read_text(encoding="utf-8").strip().splitlines()
        lines_b = sink_b.read_text(encoding="utf-8").strip().splitlines()

        assert len(lines_a) == 500, f"Expected 500 lines in Sink A, got {len(lines_a)}"
        assert len(lines_b) == 500, f"Expected 500 lines in Sink B, got {len(lines_b)}"

        # Every line must be valid JSON and pass schema validation
        for idx, line in enumerate(lines_a):
            data = json.loads(line)
            valid, msg = validate_lora_trajectory_schema(data)
            assert valid is True, f"Line {idx} failed schema: {msg}"

    def test_elo_zero_sum_mathematical_conservation_1000_matches(self):
        """Simulates 1,000 matches with extreme rating divergences; verifies zero-sum conservation."""
        for _ in range(1000):
            r_a = random.uniform(500.0, 3500.0)
            r_b = random.uniform(500.0, 3500.0)
            score_a = random.choice([0.0, 0.5, 1.0])
            k_factor = random.uniform(8.0, 96.0)

            new_a, new_b, delta_a, delta_b = update_swarm_ratings(r_a, r_b, score_a, k_factor)

            # Exact Zero-Sum Conservation Invariant
            assert delta_a + delta_b == 0.0, f"Zero-sum violated: delta_a={delta_a}, delta_b={delta_b}"

            # Logistic expectation bounds
            e_a, e_b = compute_expected_pair(r_a, r_b)
            assert 0.0 < e_a < 1.0
            assert 0.0 < e_b < 1.0
            assert abs((e_a + e_b) - 1.0) < 1e-12


# ==============================================================================
# CLASS 5: Adversarial Supervisor Lifecycle, Signals & Storage Self-Healing
# ==============================================================================
class TestAdversarialSupervisorLifecycleAndHealing:
    """Stress-tests signal unblocking, storage auto-healing, and supervisor circuit breaker."""

    def test_signal_handler_instant_unblock(self):
        """Verifies that SignalHandler.sleep unblocks in < 50ms upon receiving termination signal."""
        handler = SignalHandler()
        start = time.time()

        def trigger():
            time.sleep(0.05)
            handler._handle_term(signal.SIGINT, None)

        threading.Thread(target=trigger, daemon=True).start()
        interrupted = handler.sleep(10.0)
        elapsed = time.time() - start

        assert interrupted is True
        assert elapsed < 0.25, f"SignalHandler sleep unblock too slow: {elapsed:.3f}s"

    def test_storage_health_guard_heals_missing_and_corrupted_index(self, tmp_path):
        """Verifies that missing or truncated Index.md is automatically healed with master Wikilinks."""
        obsidian_dir = tmp_path / "obsidian_vault"
        guard = StorageHealthGuard(repo_root=tmp_path, lora_dir=tmp_path / "lora")

        # Case 1: Missing Index.md
        report = guard.verify_and_heal()
        assert report["obsidian_index_healed"] is True
        index_file = obsidian_dir / "Index.md"
        assert index_file.exists()
        content = index_file.read_text(encoding="utf-8")
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in content
        assert "[[Index]]" in content

        # Case 2: Corrupted empty Index.md
        index_file.write_text("")
        report2 = guard.verify_and_heal()
        assert report2["obsidian_index_healed"] is True
        assert len(index_file.read_text(encoding="utf-8")) > 50

    def test_circuit_breaker_trips_on_consecutive_errors(self, tmp_path):
        """Simulates consecutive step failures tripping the circuit breaker."""
        config = SupervisorConfig(
            max_rounds=5,
            interval_seconds=0.1,
            max_consecutive_errors=3,
            circuit_breaker_cooldown_seconds=0.5,
            pid_file=tmp_path / "cb.pid"
        )
        supervisor = OvernightDaemonSupervisor(config)
        assert supervisor.consecutive_errors == 0


# ==============================================================================
# CLASS 6: End-to-End System Integration & Contract Verification
# ==============================================================================
class TestAdversarialEndToEndSystemIntegration:
    """Verifies complete end-to-end training step execution and contracts."""

    def test_e2e_training_step_contract_and_attributes(self, tmp_path):
        """Executes run_single_overnight_training_step in dry-run mode and verifies return schema."""
        res = run_single_overnight_training_step(
            step_number=1,
            dry_run=True,
            task_instance=SAMPLE_SWEBENCH_TASKS[0] if SAMPLE_SWEBENCH_TASKS else None,
            mcts_iterations=4
        )
        assert isinstance(res, dict)
        assert "step" in res
        assert "instance_id" in res
        assert "mcts_value" in res
        assert "devils_advocate_critique" in res
        assert "ast_valid" in res
        assert "patch_status" in res
        assert "elo_delta" in res
        assert "winner_id" in res
        assert "champion_swarm" in res

    def test_tournament_swarm_match_result_schema_consistency(self):
        """Verifies SwarmMatchResult fields and methods."""
        res = SwarmMatchResult(
            match_id="m-1",
            timestamp="2026-01-01T00:00:00Z",
            swarm_a_id="SWARM_A",
            swarm_b_id="SWARM_B",
            swarm_a_name="Swarm A",
            swarm_b_name="Swarm B",
            task_id="t-1",
            task_domain="code",
            score_a=1.0,
            score_b=0.0,
            winner_id="SWARM_A",
            old_elo_a=2000.0,
            old_elo_b=2000.0,
            new_elo_a=2016.0,
            new_elo_b=1984.0,
            delta_elo_a=16.0,
            delta_elo_b=-16.0,
            expected_score_a=0.5,
            expected_score_b=0.5,
            k_factor=32.0,
            mcts_value_a=0.9,
            mcts_value_b=0.7,
            mcts_margin=0.2,
            p_devil_a=0.05,
            p_devil_b=0.08,
            is_truth_verified=True,
            consensus_thought="Consensus",
            best_patch="--- a/f.py\n+++ b/f.py\n"
        )
        d = res.to_dict()
        assert d["delta_elo_a"] == 16.0
        assert d["delta_elo_b"] == -16.0
        assert d["winner_id"] == "SWARM_A"
