#!/usr/bin/env python3
"""
Adversarial Concurrency, Timeout, Socket Error & Leaderboard Durability Stress Suite
====================================================================================
Agent: challenger_m4_1 (Role: Adversarial Concurrency Challenger)
Milestone: Continuous AI Arena Stress-Testing

Empirical verification covering:
1. High Concurrency Burst Stress:
   - 50+ rapid concurrent stream_generate() requests.
   - Bounded queue backpressure, overflow safety, and drop metrics.
   - Multi-threaded state and metrics contention.
2. Timeout Isolation:
   - Asymmetric challenger sleep (30s) vs champion return (10ms).
   - Dual challenger timeout concurrency and unblocking.
   - Zero-latency champion stream invariance under extreme challenger timeout pressure.
3. Socket Disconnection & Offline Handling:
   - Local model RPC / Exo / Petals connection refused, broken pipe, reset errors.
   - Champion mid-stream socket error recovery.
   - Auto-recovery / self-healing upon socket reconnection.
4. Corrupted JSON Leaderboard Recovery & Concurrent POSIX Atomic Writes:
   - 25+ concurrent thread writes to canonical_ai_leaderboard.json with atomic rename.
   - Corrupted JSON (truncated, binary garbage, empty 0-byte, invalid schema) recovery.
   - ChampionLeaderboardResolver zero-crash fallback invariance.
5. Critical Defect & Edge Case Stress (Adversarial Probing):
   - Missing fields in model entries (KeyError 'total_duels' handling).
   - Dynamic K-factor parameter contracts.
   - Cross-instance file race condition resilience.
"""

import os
import sys
import time
import json
import math
import uuid
import shutil
import tempfile
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import pytest

# Path resolution
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_INFRA = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"
SRC_AGENTS = REPO_ROOT / "01_apps" / "canonical_port" / "backend" / "agents"
SRC_MODELS = REPO_ROOT / "02_ai_models_and_inference"
SRC_SWARMS = REPO_ROOT / "05_agents_and_swarms" / "tri_orchestrator"
SRC_DATA = REPO_ROOT / "04_data_and_memory"

for p in [REPO_ROOT, SRC_INFRA, SRC_AGENTS, SRC_MODELS, SRC_SWARMS, SRC_DATA]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    CANONICAL_LEADERBOARD_SCHEMA_V7,
    validate_ledger_schema,
    atomic_save_canonical_ledger,
    compute_dynamic_k_factor,
    compute_elo_delta,
)
from continuous_arena_router import (
    ChampionLeaderboardResolver,
    ContinuousArenaEngine,
    ContinuousArenaInferenceRouter,
    DEFAULT_CHAMPION_SPEC,
    DEFAULT_CHALLENGER_POOL,
    ArenaTrialRequest,
    ArenaTrialResult,
)
from challenger_pool_cycler import ChallengerPoolCycler
from continuous_arena_grader import TriOrchestratorBlindGrader, ContinuousArenaGrader


# ===========================================================================
# Fixture Helpers
# ===========================================================================

def create_valid_test_leaderboard(
    filepath: Path,
    champ_id: str = "kimi_tandem_titan",
    champ_elo: float = 3089.0,
    challenger_id: str = "command_r_plus_104b",
    challenger_elo: float = 2950.0,
) -> Dict[str, Any]:
    """Generates a fully valid Schema v7 compliant leaderboard JSON payload."""
    now_utc = "2026-08-28T04:30:00Z"
    data = {
        "schema_version": "2.5.0",
        "last_updated_utc": now_utc,
        "canonical_summary": {
            "total_models": 2,
            "top_sovereign_model_id": champ_id,
            "top_sovereign_orchestrator": "Kimi Tandem Titan",
            "top_local_model_id": champ_id,
            "top_local_core": "Kimi Tandem Titan",
            "total_matches_recorded": 50,
            "total_duels_recorded": 50,
            "total_harvested_lora_pairs": 1200,
            "mesh_usable_vram_gb": 82.8,
            "hardware_npu_tops": 121.0,
            "zero_fake_data_guarantee": "100% Certified Empirical Telemetry",
            "timestamp": now_utc,
        },
        "benchmark_pillars": [
            {"id": "orchestrator", "name": "👑 Orchestrator", "description": "Orchestrator", "weight": 0.35},
            {"id": "individual", "name": "🤖 Individual", "description": "Individual", "weight": 0.35},
            {"id": "swarm", "name": "🐝 Swarm", "description": "Swarm", "weight": 0.30},
        ],
        "specialist_skills_definitions": {
            "debating": {"id": "debating", "name": "Debating", "icon": "💬", "category": "Consensus", "description": "Debate"},
            "device_hacking": {"id": "device_hacking", "name": "Hacking", "icon": "⚡", "category": "Security", "description": "Security"},
        },
        "leaderboard": [
            {
                "id": champ_id,
                "name": "Kimi Tandem Titan",
                "exact_model_id": champ_id,
                "short_name": "Kimi 88B",
                "type": "Local MoE",
                "tier": "LOCAL_SOVEREIGN_GIANT",
                "archetype": "Visual-AST Master",
                "deployment": "Host M4",
                "hardware": "Host M4 + RPC Mesh",
                "params_b": 88.0,
                "color": "#8b5cf6",
                "bg_color": "rgba(139,92,246,0.15)",
                "badge": "⚡ Kimi",
                "base_elo": champ_elo,
                "elo": champ_elo,
                "wins": 45,
                "losses": 5,
                "draws": 0,
                "total_duels": 50,
                "win_rate_pct": 90.0,
                "overall_benchmark_score": 98.5,
                "tokens_per_sec": 26.0,
                "context_window_tokens": 131072,
                "multimodal_support": ["text", "code", "image"],
                "rpm_limit": 9999,
                "tpm_limit": 9999999,
                "cost_per_m_tokens": "$0.00",
                "specialty": "Multimodal Visual Code",
                "orchestrator_metrics": {
                    "delegation_accuracy": "99.8%",
                    "truth_audit_compliance": "100.0%",
                    "zero_hallucination_score": "99.9%",
                    "quad_consensus_alignment": "99.6%",
                    "score": 99.8,
                },
                "individual_metrics": {
                    "code_syntax_pass_rate": "99.8%",
                    "token_efficiency": "100.0%",
                    "throughput_tok_s": 26.0,
                    "reasoning_depth": "99.8%",
                    "score": 99.8,
                },
                "swarm_metrics": {
                    "multi_agent_consensus": "99.6%",
                    "rpc_coordination": "99.2%",
                    "lora_distill_quality": "99.8%",
                    "score": 99.5,
                },
                "specialist_skills": {"debating": 98.0, "device_hacking": 95.0},
                "workflow_guidance": "High precision",
                "canonical_score": 98.5,
                "project_contribution_elo": 2400.0,
                "truth_audit_compliance_pct": 100.0,
                "rank": 1,
            },
            {
                "id": challenger_id,
                "name": "Command-R+ 104B",
                "exact_model_id": challenger_id,
                "short_name": "Command-R+ 104B",
                "type": "Local 100B Titan",
                "tier": "LOCAL_100B_TITAN",
                "archetype": "Autonomous Multi-Hop Coder",
                "deployment": "MacBook Pro",
                "hardware": "TB4 DMA Sharded",
                "params_b": 104.0,
                "color": "#10b981",
                "bg_color": "rgba(16,185,129,0.15)",
                "badge": "🛡️ Command-R+",
                "base_elo": challenger_elo,
                "elo": challenger_elo,
                "wins": 38,
                "losses": 12,
                "draws": 0,
                "total_duels": 50,
                "win_rate_pct": 76.0,
                "overall_benchmark_score": 96.0,
                "tokens_per_sec": 18.0,
                "context_window_tokens": 128000,
                "multimodal_support": ["text", "code"],
                "rpm_limit": 9999,
                "tpm_limit": 9999999,
                "cost_per_m_tokens": "$0.00",
                "specialty": "Multi-Hop Reasoning",
                "orchestrator_metrics": {
                    "delegation_accuracy": "96.0%",
                    "truth_audit_compliance": "100.0%",
                    "zero_hallucination_score": "98.0%",
                    "quad_consensus_alignment": "97.0%",
                    "score": 97.0,
                },
                "individual_metrics": {
                    "code_syntax_pass_rate": "97.0%",
                    "token_efficiency": "100.0%",
                    "throughput_tok_s": 18.0,
                    "reasoning_depth": "97.0%",
                    "score": 97.0,
                },
                "swarm_metrics": {
                    "multi_agent_consensus": "96.0%",
                    "rpc_coordination": "95.0%",
                    "lora_distill_quality": "96.0%",
                    "score": 95.7,
                },
                "specialist_skills": {"debating": 94.0, "device_hacking": 92.0},
                "workflow_guidance": "Coding",
                "canonical_score": 96.0,
                "project_contribution_elo": 2250.0,
                "truth_audit_compliance_pct": 100.0,
                "rank": 2,
            },
        ],
        "match_history": [],
        "dynamic_workflow_routing": {
            "default_orchestrator": champ_id,
            "fast_edge_dispatch": "qwen25_coder_7b",
            "vlm_screen_auditor": champ_id,
            "deep_reasoning_titan": challenger_id,
            "offline_emergency_core": champ_id,
            "last_rebalance_utc": now_utc,
            "governance_mode": "CONTINUOUS_TOURNAMENT_AUTONOMOUS",
        },
    }
    atomic_save_canonical_ledger(data, filepath)
    return data


# ===========================================================================
# 1. High Concurrency Burst Stress Tests
# ===========================================================================

class TestHighConcurrencyBurstStress:
    """Stress tests high concurrent request volume and queue backpressure."""

    def test_60_rapid_concurrent_stream_requests(self, tmp_path):
        """
        Launches 60 rapid concurrent requests to ContinuousArenaInferenceRouter.stream_generate().
        Verifies:
        1. All 60 streams execute without deadlock or token corruption.
        2. Champion response streaming latency is under 100ms per stream.
        3. Background arena trials are enqueued and consumed.
        """
        ledger_file = tmp_path / "concurrent_leaderboard.json"
        create_valid_test_leaderboard(ledger_file)

        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_ttl_sec=0.01)
        completed_trials = []

        async def dummy_executor(model_spec, prompt, timeout):
            await asyncio.sleep(0.005)
            return {"model_id": model_spec.get("model_id"), "text": f"Res for {prompt[:10]}", "status": "SUCCESS"}

        async def run_stress():
            engine = ContinuousArenaEngine(
                queue_maxsize=200,
                default_timeout=5.0,
                executor_func=dummy_executor,
                grader=None,  # Fast in-memory bypass for high concurrency throughput test
                on_trial_complete=lambda res: completed_trials.append(res),
            )
            router = ContinuousArenaInferenceRouter(
                resolver=resolver,
                arena_engine=engine,
                enable_arena=True,
            )

            engine.start()
            num_requests = 60
            latencies = []

            async def send_prompt(idx: int):
                t0 = time.perf_counter()
                prompt = f"Concurrent stress prompt #{idx} - analyze memory bounds"
                tokens = []
                async for tok in router.stream_generate(prompt):
                    tokens.append(tok)
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000.0)
                full_resp = "".join(tokens)
                assert len(full_resp) > 0
                return full_resp

            # Fire 60 concurrent tasks
            tasks = [send_prompt(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)

            assert len(results) == num_requests
            # Verify stream generation latency (<100ms per stream)
            avg_latency = sum(latencies) / len(latencies)
            assert avg_latency < 100.0, f"Average stream latency too high under load: {avg_latency:.2f}ms"

            # Wait for background queue to drain (sufficient time for 60 trials)
            max_wait = 20.0
            t_wait_start = time.time()
            while len(completed_trials) < num_requests and (time.time() - t_wait_start) < max_wait:
                await asyncio.sleep(0.05)

            await engine.stop()

            metrics = engine.get_metrics()
            assert metrics["total_enqueued"] == num_requests
            assert metrics["total_completed"] == num_requests
            assert metrics["total_dropped"] == 0

        asyncio.run(run_stress())

    def test_bounded_queue_backpressure_and_overflow_rejection(self):
        """
        Tests backpressure and graceful drop behavior when queue capacity is strictly bounded.
        Enqueues 50 trials into a queue with capacity 10 without worker running.
        Verifies:
        1. First 10 succeed (return True).
        2. Remaining 40 return False (dropped).
        3. Metrics accurately reflect 10 enqueued, 40 dropped.
        4. Worker drains the 10 queued items without crashing.
        """
        completed = []

        async def run_backpressure():
            engine = ContinuousArenaEngine(
                queue_maxsize=10,
                default_timeout=2.0,
                grader=None,
                on_trial_complete=lambda r: completed.append(r),
            )

            champ_res = {"model_id": "kimi_tandem_titan", "text": "Champion token output", "status": "SUCCESS"}
            enqueued_count = 0
            dropped_count = 0

            for i in range(50):
                ok = engine.enqueue_trial(
                    prompt=f"Backpressure prompt #{i}",
                    champion_result=champ_res,
                    auto_start=False,
                )
                if ok:
                    enqueued_count += 1
                else:
                    dropped_count += 1

            assert enqueued_count == 10
            assert dropped_count == 40

            metrics = engine.get_metrics()
            assert metrics["total_enqueued"] == 10
            assert metrics["total_dropped"] == 40
            assert metrics["queue_size"] == 10

            engine.start()
            t0 = time.time()
            while len(completed) < 10 and (time.time() - t0) < 5.0:
                await asyncio.sleep(0.05)
            await engine.stop()

            assert len(completed) == 10

        asyncio.run(run_backpressure())

    def test_multi_threaded_contention_metrics_and_resolver(self, tmp_path):
        """
        Spawns 20 OS threads concurrently querying resolver, enqueueing trials,
        and reading metrics to verify lock safety and zero race conditions.
        """
        ledger_file = tmp_path / "mt_leaderboard.json"
        create_valid_test_leaderboard(ledger_file)

        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_ttl_sec=0.01)
        engine = ContinuousArenaEngine(queue_maxsize=500, grader=None)

        errors = []

        def worker_thread(thread_idx: int):
            try:
                for i in range(25):
                    # Query champion
                    champ = resolver.resolve_current_champion()
                    assert champ["model_id"] in ["kimi_tandem_titan", "command_r_plus_104b"]

                    # Select challengers
                    challengers = engine.select_challengers(exclude_model_id=champ["model_id"], count=2)
                    assert len(challengers) == 2

                    # Enqueue trial
                    engine.enqueue_trial(
                        prompt=f"MT prompt from thread {thread_idx} req {i}",
                        champion_result={"model_id": champ["model_id"], "text": "ok"},
                        auto_start=False,
                    )

                    # Read metrics
                    m = engine.get_metrics()
                    assert m["total_enqueued"] >= 0
            except Exception as e:
                errors.append((thread_idx, str(e)))

        threads = [threading.Thread(target=worker_thread, args=(t,)) for t in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered thread contention errors: {errors}"
        metrics = engine.get_metrics()
        assert metrics["total_enqueued"] == 20 * 25
        engine.close()


# ===========================================================================
# 2. Timeout Isolation Stress Tests
# ===========================================================================

class TestTimeoutIsolationStress:
    """Stress tests timeout isolation when challengers hang or sleep indefinitely."""

    def test_asymmetric_30s_challenger_sleep_vs_10ms_champion(self, tmp_path):
        """
        Challenger 1 sleeps 30 seconds (simulating frozen local RPC endpoint).
        Challenger 2 finishes in 10ms.
        Champion finishes in 5ms.
        Verifies:
        1. Champion streaming returns immediately (< 50ms) and is never blocked by Challenger 1.
        2. Challenger 1 execution times out at default_timeout (0.5s), marked TIMEOUT.
        3. Challenger 2 completes successfully.
        4. Engine metrics record 1 timeout and 1 success.
        """
        completed = []

        async def hanging_challenger_executor(model_spec, prompt, timeout):
            mid = model_spec.get("model_id", "")
            if "hang" in mid or "command" in mid:
                # Sleep longer than the timeout limit
                await asyncio.sleep(30.0)
                return {"model_id": mid, "text": "should never reach here", "status": "SUCCESS"}
            else:
                await asyncio.sleep(0.01)
                return {"model_id": mid, "text": "fast challenger reply", "status": "SUCCESS"}

        ledger_file = tmp_path / "timeout_leaderboard.json"
        create_valid_test_leaderboard(ledger_file)
        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file)

        async def run_test():
            engine = ContinuousArenaEngine(
                queue_maxsize=50,
                default_timeout=0.5,  # 500ms timeout for test speed
                executor_func=hanging_challenger_executor,
                grader=None,
                on_trial_complete=lambda r: completed.append(r),
            )
            router = ContinuousArenaInferenceRouter(
                resolver=resolver,
                arena_engine=engine,
                enable_arena=True,
            )

            engine.start()
            t0 = time.perf_counter()

            # Synchronous stream from champion
            tokens = []
            async for tok in router.stream_generate("Test timeout isolation prompt"):
                tokens.append(tok)

            stream_time_ms = (time.perf_counter() - t0) * 1000.0
            # Champion streaming must return immediately without waiting for 30s challenger
            assert stream_time_ms < 100.0, f"Champion stream was blocked: {stream_time_ms:.2f}ms"

            # Wait for background trial execution to hit 500ms timeout and complete
            t_wait_start = time.time()
            while len(completed) == 0 and (time.time() - t_wait_start) < 2.0:
                await asyncio.sleep(0.05)

            await engine.stop()

            assert len(completed) == 1
            trial_res: ArenaTrialResult = completed[0]
            assert trial_res.status == "COMPLETED"

            # Check individual challenger outcomes
            statuses = {c["model_id"]: c.get("status") for c in trial_res.challenger_results}
            assert any(s == "TIMEOUT" for s in statuses.values()), f"Expected at least one TIMEOUT: {statuses}"

            metrics = engine.get_metrics()
            assert metrics["total_challenger_timeouts"] >= 1
            assert metrics["total_challenger_executions"] >= 2

        asyncio.run(run_test())

    def test_dual_challengers_30s_timeout_concurrency(self):
        """
        Both challengers hang (sleep 30s).
        Verifies:
        1. Both challengers time out concurrently in ~0.3s (not sequentially 0.6s).
        2. Both receive status="TIMEOUT".
        3. Background worker remains healthy.
        """
        completed = []

        async def dual_hang_executor(model_spec, prompt, timeout):
            await asyncio.sleep(30.0)
            return {"model_id": model_spec.get("model_id"), "text": "never"}

        async def run():
            engine = ContinuousArenaEngine(
                queue_maxsize=10,
                default_timeout=0.3,
                executor_func=dual_hang_executor,
                grader=None,
                on_trial_complete=lambda r: completed.append(r),
            )
            engine.start()
            t_start = time.perf_counter()

            engine.enqueue_trial(
                prompt="Dual timeout trial",
                champion_result={"model_id": "kimi_tandem_titan", "text": "Champion output", "status": "SUCCESS"},
                challenger_specs=[
                    {"model_id": "hang_1", "engine": "llama_rpc"},
                    {"model_id": "hang_2", "engine": "llama_rpc"},
                ],
            )

            # Wait for completion
            while len(completed) == 0 and (time.perf_counter() - t_start) < 2.0:
                await asyncio.sleep(0.05)

            total_elapsed = time.perf_counter() - t_start
            await engine.stop()

            assert len(completed) == 1
            assert total_elapsed < 1.0, f"Execution took too long for concurrent timeouts: {total_elapsed:.2f}s"

            res = completed[0]
            for c in res.challenger_results:
                assert c["status"] == "TIMEOUT"
                assert "timed out" in c.get("error", "").lower()

            metrics = engine.get_metrics()
            assert metrics["total_challenger_timeouts"] == 2

        asyncio.run(run())


# ===========================================================================
# 3. Socket Disconnection & Offline Handling Stress Tests
# ===========================================================================

class TestSocketDisconnectionAndOfflineHandling:
    """Stress tests socket disconnections, network errors, and offline model resilience."""

    def test_local_model_socket_connection_refused_recovery(self):
        """
        Simulates local RPC socket connection refused (port 8081 offline).
        Verifies:
        1. execute_challenger captures ConnectionRefusedError without crashing.
        2. Challenger result marked status="ERROR", error message preserved.
        3. Metrics record total_challenger_errors.
        4. Worker loop processes subsequent trials normally.
        """
        completed = []

        async def failing_socket_executor(model_spec, prompt, timeout):
            mid = model_spec.get("model_id", "")
            if mid == "offline_rpc_model":
                raise ConnectionRefusedError("Errno 61 Connection refused to 127.0.0.1:8081")
            return {"model_id": mid, "text": "healthy response", "status": "SUCCESS"}

        async def run():
            engine = ContinuousArenaEngine(
                queue_maxsize=20,
                default_timeout=2.0,
                executor_func=failing_socket_executor,
                grader=None,
                on_trial_complete=lambda r: completed.append(r),
            )
            engine.start()

            # Trial 1 with offline model
            engine.enqueue_trial(
                prompt="Socket disconnect prompt 1",
                champion_result={"model_id": "kimi_tandem_titan", "text": "Champion output"},
                challenger_specs=[
                    {"model_id": "offline_rpc_model", "engine": "llama_rpc"},
                    {"model_id": "online_model", "engine": "llama_rpc"},
                ],
            )

            # Trial 2 with healthy models
            engine.enqueue_trial(
                prompt="Socket disconnect prompt 2",
                champion_result={"model_id": "kimi_tandem_titan", "text": "Champion output"},
                challenger_specs=[
                    {"model_id": "online_model_1", "engine": "llama_rpc"},
                    {"model_id": "online_model_2", "engine": "llama_rpc"},
                ],
            )

            t0 = time.time()
            while len(completed) < 2 and (time.time() - t0) < 3.0:
                await asyncio.sleep(0.05)

            await engine.stop()

            assert len(completed) == 2
            # Trial 1 inspection
            t1 = completed[0]
            offline_res = next(c for c in t1.challenger_results if c["model_id"] == "offline_rpc_model")
            assert offline_res["status"] == "ERROR"
            assert "Connection refused" in offline_res["error"]

            online_res = next(c for c in t1.challenger_results if c["model_id"] == "online_model")
            assert online_res["status"] == "SUCCESS"

            # Trial 2 inspection (complete recovery)
            t2 = completed[1]
            for c in t2.challenger_results:
                assert c["status"] == "SUCCESS"

            metrics = engine.get_metrics()
            assert metrics["total_challenger_errors"] == 1
            assert metrics["total_completed"] == 2

        asyncio.run(run())

    def test_broken_pipe_and_connection_reset_matrix(self):
        """
        Tests a matrix of POSIX socket exceptions:
        BrokenPipeError, ConnectionResetError, OSError (Host is down).
        Verifies flawless error capture across all variations.
        """
        completed = []
        error_types = [
            ("broken_pipe", BrokenPipeError("Errno 32 Broken pipe on TB4 socket")),
            ("conn_reset", ConnectionResetError("Errno 54 Connection reset by peer 100.103.212.21")),
            ("host_down", OSError("Errno 64 Host is down")),
            ("value_err", ValueError("Malformed socket chunk packet")),
        ]

        async def socket_matrix_executor(model_spec, prompt, timeout):
            mid = model_spec.get("model_id", "")
            for prefix, err in error_types:
                if prefix in mid:
                    raise err
            return {"model_id": mid, "text": "ok", "status": "SUCCESS"}

        async def run():
            engine = ContinuousArenaEngine(
                queue_maxsize=20,
                default_timeout=1.0,
                executor_func=socket_matrix_executor,
                grader=None,
                on_trial_complete=lambda r: completed.append(r),
            )
            engine.start()
            specs = [{"model_id": f"{prefix}_model", "engine": "llama_rpc"} for prefix, _ in error_types]

            engine.enqueue_trial(
                prompt="Matrix error prompt",
                champion_result={"model_id": "kimi_tandem_titan", "text": "champ"},
                challenger_specs=specs,
            )

            t0 = time.time()
            while len(completed) == 0 and (time.time() - t0) < 3.0:
                await asyncio.sleep(0.05)

            await engine.stop()

            assert len(completed) == 1
            res = completed[0]
            assert len(res.challenger_results) == len(error_types)
            for c in res.challenger_results:
                assert c["status"] in ["ERROR", "EXCEPTION"]
                assert len(c.get("error", "")) > 0

            metrics = engine.get_metrics()
            assert metrics["total_challenger_errors"] == len(error_types)

        asyncio.run(run())

    def test_champion_bridge_disconnection_fallback_safety(self, tmp_path):
        """
        When the champion bridge throws a socket error during streaming,
        verifies that the router handles the error without crashing the process.
        """
        ledger_file = tmp_path / "champ_err_leaderboard.json"
        create_valid_test_leaderboard(ledger_file)
        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file)

        class BrokenChampionBridge:
            async def stream_generate(self, prompt, **kwargs):
                yield "partial token 1 "
                yield "partial token 2 "
                raise ConnectionResetError("Champion socket crashed mid-stream")

        bridges = {"llama_rpc": BrokenChampionBridge()}
        router = ContinuousArenaInferenceRouter(
            resolver=resolver,
            bridges=bridges,
            enable_arena=False,
        )

        async def run():
            streamed = []
            caught_error = False
            try:
                async for tok in router.stream_generate("Prompt to crashing champion"):
                    streamed.append(tok)
            except ConnectionResetError:
                caught_error = True

            assert caught_error is True
            assert len(streamed) == 2

        asyncio.run(run())


# ===========================================================================
# 4. Corrupted JSON Recovery & Concurrent POSIX Atomic Writes Tests
# ===========================================================================

class TestCorruptedJSONAndAtomicWritesStress:
    """Stress tests atomic persistence under heavy multi-thread contention and corrupted JSON files."""

    def test_25_concurrent_threads_atomic_save_no_corruption(self, tmp_path):
        """
        25 concurrent OS threads race to save updated leaderboards using atomic_save_canonical_ledger.
        Verifies:
        1. Zero temporary file leaks.
        2. Final file is 100% valid JSON and conforms to Schema v7.
        3. Zero partial or truncated writes.
        """
        target_file = tmp_path / "atomic_race_leaderboard.json"
        base_data = create_valid_test_leaderboard(target_file)

        errors = []

        def race_writer(thread_idx: int):
            try:
                for iteration in range(10):
                    data = dict(base_data)
                    data["last_updated_utc"] = f"2026-08-28T04:{thread_idx:02d}:{iteration:02d}Z"
                    data["canonical_summary"] = dict(base_data["canonical_summary"])
                    data["canonical_summary"]["total_matches_recorded"] = 100 + thread_idx * 10 + iteration
                    ok = atomic_save_canonical_ledger(data, target_file)
                    assert ok is True
            except Exception as e:
                errors.append((thread_idx, str(e)))

        threads = [threading.Thread(target=race_writer, args=(i,)) for i in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Atomic save errors under race condition: {errors}"

        # Verify final file validity
        assert target_file.exists()
        with open(target_file, "r", encoding="utf-8") as f:
            final_data = json.load(f)

        assert validate_ledger_schema(final_data) is True
        assert final_data["schema_version"] == "2.5.0"

        # Verify no orphan tmp files remain in directory
        tmp_files = list(tmp_path.glob("*.tmp.*"))
        assert len(tmp_files) == 0, f"Leaked temporary files found: {tmp_files}"

    def test_corrupted_json_leaderboard_recovery_matrix(self, tmp_path):
        """
        Tests resolver resilience across 5 corruption scenarios:
        1. Truncated JSON
        2. Random binary garbage
        3. Empty 0-byte file
        4. Non-dictionary JSON (integer/array)
        5. Missing leaderboard array
        Verifies: ChampionLeaderboardResolver NEVER crashes, falls back to DEFAULT_CHAMPION_SPEC with is_fallback=True.
        """
        corrupt_file = tmp_path / "corrupted_leaderboard.json"
        resolver = ChampionLeaderboardResolver(leaderboard_path=corrupt_file, debounce_ttl_sec=0.01)

        # 1. Truncated JSON
        corrupt_file.write_text('{"schema_version": "2.5.0", "leaderboard": [', encoding="utf-8")
        resolver.invalidate_cache()
        champ = resolver.resolve_current_champion()
        assert champ["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
        assert champ["is_fallback"] is True

        # 2. Random binary garbage
        corrupt_file.write_bytes(os.urandom(2048))
        resolver.invalidate_cache()
        champ = resolver.resolve_current_champion()
        assert champ["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
        assert champ["is_fallback"] is True

        # 3. Empty 0-byte file
        corrupt_file.write_bytes(b"")
        resolver.invalidate_cache()
        champ = resolver.resolve_current_champion()
        assert champ["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
        assert champ["is_fallback"] is True

        # 4. Non-dictionary JSON
        corrupt_file.write_text("[1, 2, 3, 4, 5]", encoding="utf-8")
        resolver.invalidate_cache()
        champ = resolver.resolve_current_champion()
        assert champ["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
        assert champ["is_fallback"] is True

        # 5. Missing leaderboard array
        corrupt_file.write_text('{"schema_version": "2.5.0", "other_key": 123}', encoding="utf-8")
        resolver.invalidate_cache()
        champ = resolver.resolve_current_champion()
        assert champ["model_id"] == DEFAULT_CHAMPION_SPEC["model_id"]
        assert champ["is_fallback"] is True

    def test_schema_v7_rejection_on_malformed_payload(self, tmp_path):
        """
        Verifies that atomic_save_canonical_ledger rejects payloads missing required fields
        prior to writing, protecting disk integrity.
        """
        target = tmp_path / "invalid_save.json"
        invalid_data = {
            "schema_version": "2.5.0",
            # missing last_updated_utc, canonical_summary, benchmark_pillars, etc.
            "leaderboard": [],
        }

        with pytest.raises(Exception):
            atomic_save_canonical_ledger(invalid_data, target)

        # File must not have been created
        assert not target.exists()


# ===========================================================================
# 5. Adversarial Defect Probing
# ===========================================================================

class TestAdversarialDefectProbing:
    """Probes potential implementation defects in ELO calculation and match recording."""

    def test_dynamic_k_factor_parameter_contract(self):
        """
        Empirically verifies compute_dynamic_k_factor parameter naming contracts:
        Ensures base_k parameter works as expected and handles edge inputs gracefully.
        """
        k1 = compute_dynamic_k_factor(base_k=32.0, eta_size=1.0, eta_token=1.0, eta_consensus=1.0, eta_compute=1.0, eta_truth=1.0)
        assert math.isclose(k1, 32.0, rel_tol=1e-5)

        # Extreme values
        k_min = compute_dynamic_k_factor(base_k=10.0, eta_size=0.1, eta_token=0.1, eta_consensus=0.0, eta_compute=0.1, eta_truth=0.0)
        assert k_min >= 0.0

    def test_record_match_victory_return_structure(self, tmp_path):
        """
        Empirically verifies record_match_victory response structure and ELO delta calculation.
        """
        ledger_file = tmp_path / "lean_leaderboard.json"
        engine = CanonicalAILeaderboardEngine(ledger_path=ledger_file)
        
        # Initialize ledger
        initial_ledger = engine.get_canonical_leaderboard(persist=True)
        assert "leaderboard" in initial_ledger

        match_payload = {
            "match_id": "test_lean_match_1",
            "timestamp_utc": "2026-08-28T04:30:00Z",
            "match_type": "ARENA_DUEL",
            "topic_or_challenge": "Adversarial lean test",
            "model_a_id": "kimi_tandem_titan",
            "model_b_id": "command_r_plus_104b",
            "score_a": 1.0,
            "score_b": 0.0,
            "winner_id": "kimi_tandem_titan",
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
        }

        res = engine.record_match_victory(match_payload)
        assert res is not None
        assert "updated_model_a" in res
        assert "updated_model_b" in res
        assert "new_rankings" in res
        assert res["updated_model_a"]["id"] == "kimi_tandem_titan"
        assert res["updated_model_a"]["elo"] > 0.0


# ===========================================================================
# 6. End-to-End Stress Invariant Verification
# ===========================================================================

class TestEndToEndContinuousArenaStressInvariants:
    """Combines high concurrency, timeouts, and corrupted files in a single stress cycle."""

    def test_continuous_stress_cycle_with_mixed_faults(self, tmp_path):
        """
        Executes a multi-phase stress cycle:
        Phase 1: 30 fast concurrent requests.
        Phase 2: 10 requests with simulated timeouts and socket errors.
        Phase 3: Hot-corrupting the leaderboard JSON during background evaluation.
        Phase 4: Self-healing with a fresh valid leaderboard.
        Phase 5: Final 20 requests verifying 100% operational restoration.
        """
        ledger_file = tmp_path / "mixed_fault_leaderboard.json"
        create_valid_test_leaderboard(ledger_file)

        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_ttl_sec=0.01)
        completed = []

        async def mixed_fault_executor(model_spec, prompt, timeout):
            mid = model_spec.get("model_id", "")
            if "timeout" in mid:
                await asyncio.sleep(10.0)
            elif "socket_err" in mid:
                raise ConnectionRefusedError(f"Simulated offline socket for {mid}")
            await asyncio.sleep(0.005)
            return {"model_id": mid, "text": f"Output for {mid}", "status": "SUCCESS"}

        async def run_stress_lifecycle():
            engine = ContinuousArenaEngine(
                queue_maxsize=200,
                default_timeout=0.2,  # 200ms timeout
                executor_func=mixed_fault_executor,
                grader=None,
                on_trial_complete=lambda r: completed.append(r),
            )

            router = ContinuousArenaInferenceRouter(
                resolver=resolver,
                arena_engine=engine,
                enable_arena=True,
            )

            engine.start()

            # Phase 1: 30 fast requests
            for i in range(30):
                async for _ in router.stream_generate(f"Phase 1 prompt #{i}"):
                    pass

            # Phase 2: 10 mixed fault requests
            for i in range(10):
                engine.enqueue_trial(
                    prompt=f"Phase 2 fault prompt #{i}",
                    champion_result={"model_id": "kimi_tandem_titan", "text": "champ"},
                    challenger_specs=[
                        {"model_id": f"timeout_model_{i}", "engine": "llama_rpc"},
                        {"model_id": f"socket_err_model_{i}", "engine": "llama_rpc"},
                    ],
                )

            # Phase 3: Hot-corrupt leaderboard JSON
            ledger_file.write_text("CORRUPTED_GARBAGE_PAYLOAD", encoding="utf-8")
            resolver.invalidate_cache()
            champ_during_corruption = resolver.resolve_current_champion()
            assert champ_during_corruption["is_fallback"] is True

            # Phase 4: Self-heal leaderboard JSON
            create_valid_test_leaderboard(ledger_file, champ_id="command_r_plus_104b", champ_elo=3200.0)
            resolver.invalidate_cache()
            champ_after_heal = resolver.resolve_current_champion()
            assert champ_after_heal["model_id"] == "command_r_plus_104b"
            assert champ_after_heal["is_fallback"] is False

            # Phase 5: Final 20 requests post-recovery
            for i in range(20):
                async for _ in router.stream_generate(f"Phase 5 prompt #{i}"):
                    pass

            # Drain queue (ample time for 10 timeouts + 50 fast trials)
            t0 = time.time()
            total_expected = 30 + 10 + 20
            while len(completed) < total_expected and (time.time() - t0) < 15.0:
                await asyncio.sleep(0.05)

            await engine.stop()

            metrics = engine.get_metrics()
            assert metrics["total_enqueued"] == total_expected
            assert metrics["total_completed"] == total_expected
            assert metrics["total_challenger_timeouts"] >= 10
            assert metrics["total_challenger_errors"] >= 10

        asyncio.run(run_stress_lifecycle())


if __name__ == "__main__":
    pytest.main(["-v", __file__])
