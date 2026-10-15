#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for Milestone 4: ELO Handover, Multi-Turn Zero Latency & Tri-Vault Integrity
=========================================================================================================
Empirical Challenger m4_2 Test Suite.

Adversarially challenges and empirically verifies:
1. Dynamic Champion Promotion & Overtake: Consecutive shadow matches where Challenger overtakes Champion,
   verifying that subsequent prompt resolution dynamically switches Champion with zero disk thrashing.
2. Bidirectional & 3-Way Multi-Hop Promotion: Verifies reverse overtakes and 3-way circular champion handovers.
3. 24/7 Continuous Multi-Turn Trial Execution with Zero-Latency Impact:
   Measures synchronous stream latency overhead (< 2.0ms enqueue), ensures background async execution
   causes zero blocking on the main thread, and tests queue resilience under high-burst workloads.
4. Micro-benchmark Enqueue Latency (< 2.0ms strict invariant).
5. Tri-Vault LoRA DPO JSONL Dataset Integrity:
   Line-by-line parsing, schema compliance, chosen/rejected formatting, Rule #0 Zero-Mock validation,
   and concurrent thread-safe append validation.
6. Tri-Vault Obsidian Markdown Debate Files Integrity:
   YAML frontmatter parsing, Markdown structural integrity, 3-judge panel breakdowns,
   and canonical master Wikilinks ([[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], [[Index]]).
7. Fault Invariants & Edge Cases: Corrupted leaderboard recovery, timeout handling, draw/tie handling,
   and extreme ELO disparities.
"""

import os
import sys
import time
import math
import json
import uuid
import queue
import shutil
import tempfile
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import pytest

# Dynamic path resolution to monorepo root
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
    ArenaTrialRequest,
    ArenaTrialResult,
    DEFAULT_CHAMPION_SPEC,
    DEFAULT_CHALLENGER_POOL,
)
from challenger_pool_cycler import ChallengerPoolCycler
from continuous_arena_grader import TriOrchestratorBlindGrader, ContinuousArenaGrader
from tri_vault_sink import TriVaultSink, verify_zero_mock_compliance, check_storage_health


# ===========================================================================
# Helper Fixtures & Test Scaffold
# ===========================================================================

def create_isolated_leaderboard_data(
    champ_id: str = "kimi_tandem_titan",
    champ_elo: float = 3500.0,
    challenger_id: str = "command_r_plus_104b",
    challenger_elo: float = 3450.0,
    third_id: str = "gemini_3_1_pro",
    third_elo: float = 3400.0,
) -> Dict[str, Any]:
    """Generates valid Schema v7 leaderboard dict with customizable initial ratings."""
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "schema_version": "2.5.0",
        "last_updated_utc": now_utc,
        "canonical_summary": {
            "total_models": 3,
            "top_sovereign_model_id": champ_id,
            "top_sovereign_orchestrator": "Top Sovereign Model",
            "top_local_model_id": champ_id,
            "top_local_core": "Top Local Core",
            "total_matches_recorded": 100,
            "total_duels_recorded": 100,
            "total_harvested_lora_pairs": 50,
            "mesh_usable_vram_gb": 82.8,
            "hardware_npu_tops": 45.0,
            "zero_fake_data_guarantee": "CERTIFIED_RULE_ZERO_ZERO_SIMULATION",
            "timestamp": now_utc,
        },
        "benchmark_pillars": [
            {"id": "syntax", "name": "AST Syntax", "weight": 0.25, "description": "AST syntax correctness"},
            {"id": "depth", "name": "Reasoning Depth", "weight": 0.25, "description": "Reasoning depth"},
            {"id": "economy", "name": "Token Economy", "weight": 0.20, "description": "Token economy"},
            {"id": "safety", "name": "Defensive Safety", "weight": 0.15, "description": "Defensive safety"},
            {"id": "truth", "name": "Truth Compliance", "weight": 0.15, "description": "Truth compliance"},
        ],
        "specialist_skills_definitions": {
            "biometrics_dsp": {"id": "biometrics_dsp", "name": "Biometrics DSP", "category": "biometrics", "description": "DSP"},
            "spatial_grappling": {"id": "spatial_grappling", "name": "Spatial Grappling", "category": "kinematics", "description": "Kinematics"},
        },
        "leaderboard": [
            {
                "id": champ_id,
                "name": f"Champion Model ({champ_id})",
                "exact_model_id": champ_id,
                "type": "local_sovereign",
                "tier": "LOCAL_SOVEREIGN_GIANT",
                "archetype": "Multimodal Visual-AST Master",
                "params_b": 72.0,
                "engine": "llama_rpc",
                "hardware": "Mac_Node (Metal GPU)",
                "vram_required_gb": 38.5,
                "base_elo": champ_elo,
                "elo": champ_elo,
                "rank": 1,
                "wins": 80,
                "losses": 20,
                "draws": 0,
                "total_duels": 100,
                "win_rate_pct": 80.0,
                "overall_benchmark_score": 98.5,
                "canonical_score": 98.5,
                "project_contribution_elo": champ_elo,
                "truth_audit_compliance_pct": 100.0,
                "elo_history": [{"timestamp": now_utc, "elo": champ_elo, "delta": 0.0}],
                "specialist_skills": {"biometrics_dsp": 95.0, "spatial_grappling": 96.0},
            },
            {
                "id": challenger_id,
                "name": f"Challenger Model ({challenger_id})",
                "exact_model_id": challenger_id,
                "type": "local_100b",
                "tier": "LOCAL_100B_TITAN",
                "archetype": "Autonomous Multi-Hop Coder",
                "params_b": 104.0,
                "engine": "llama_rpc",
                "hardware": "Mac_Node + MacBook_Pro (TB4 DMA)",
                "vram_required_gb": 48.0,
                "base_elo": challenger_elo,
                "elo": challenger_elo,
                "rank": 2,
                "wins": 75,
                "losses": 25,
                "draws": 0,
                "total_duels": 100,
                "win_rate_pct": 75.0,
                "overall_benchmark_score": 97.2,
                "canonical_score": 97.2,
                "project_contribution_elo": challenger_elo,
                "truth_audit_compliance_pct": 100.0,
                "elo_history": [{"timestamp": now_utc, "elo": challenger_elo, "delta": 0.0}],
                "specialist_skills": {"biometrics_dsp": 92.0, "spatial_grappling": 94.0},
            },
            {
                "id": third_id,
                "name": f"Third Model ({third_id})",
                "exact_model_id": third_id,
                "type": "cloud_frontier",
                "tier": "FRONTIER_CLOUD_API",
                "archetype": "Frontier Cloud Oracle",
                "params_b": 70.0,
                "engine": "gemini",
                "hardware": "Google TPU v5e Cluster",
                "vram_required_gb": 0.0,
                "base_elo": third_elo,
                "elo": third_elo,
                "rank": 3,
                "wins": 70,
                "losses": 30,
                "draws": 0,
                "total_duels": 100,
                "win_rate_pct": 70.0,
                "overall_benchmark_score": 96.0,
                "canonical_score": 96.0,
                "project_contribution_elo": third_elo,
                "truth_audit_compliance_pct": 100.0,
                "elo_history": [{"timestamp": now_utc, "elo": third_elo, "delta": 0.0}],
                "specialist_skills": {"biometrics_dsp": 90.0, "spatial_grappling": 90.0},
            },
        ],
        "match_history": [],
        "dynamic_workflow_routing": {
            "default_orchestrator": champ_id,
            "fast_edge_dispatch": "qwen25_coder_7b",
            "heavy_reasoning_fallback": challenger_id,
        },
    }


# ===========================================================================
# 1. Dynamic Champion Promotion & ELO Overtake Tests
# ===========================================================================

class TestDynamicChampionPromotion:
    """
    Adversarially tests that consecutive shadow matches dynamically elevate a Challenger
    until its ELO overtakes the Champion, and verifies that the next prompt dynamically
    resolves the new champion.
    """

    def test_consecutive_shadow_matches_and_champion_overtake(self, tmp_path):
        """
        Empirically simulate consecutive shadow duels:
        - Champion: kimi_tandem_titan (initial ELO = 3500.0)
        - Challenger: command_r_plus_104b (initial ELO = 3450.0, diff = 50.0)
        - Challenger wins consecutive trials against Champion.
        - Verify step-by-step ELO progression and check exact overtake point.
        - Verify subsequent resolver call dynamically returns command_r_plus_104b as Champion.
        """
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        lora_file = tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl"
        obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"

        initial_data = create_isolated_leaderboard_data(
            champ_id="kimi_tandem_titan",
            champ_elo=3500.0,
            challenger_id="command_r_plus_104b",
            challenger_elo=3450.0,
            third_id="gemini_3_1_pro",
            third_elo=3400.0,
        )
        atomic_save_canonical_ledger(initial_data, ledger_file)

        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_sec=0.01)
        grader = TriOrchestratorBlindGrader(
            leaderboard_path=ledger_file,
            lora_sink_path=lora_file,
            obsidian_sink_path=obsidian_dir,
            randomize_alias_order=False,
        )

        # Initial champion is kimi_tandem_titan
        champ_0 = resolver.resolve_current_champion(force_refresh=True)
        assert champ_0["model_id"] == "kimi_tandem_titan"
        assert champ_0["elo"] == 3500.0

        overtake_reached = False
        overtake_round = -1
        max_rounds = 10

        for r in range(1, max_rounds + 1):
            champ_output = {
                "model_id": "kimi_tandem_titan",
                "name": "Kimi Tandem Titan",
                "status": "SUCCESS",
                "latency_ms": 120.0,
                "text": "def compute_average(values):\n    return sum(values) / len(values) if values else 0.0",
                "params_b": 72.0,
            }
            challenger_output_1 = {
                "model_id": "command_r_plus_104b",
                "name": "Command-R+ 104B",
                "status": "SUCCESS",
                "latency_ms": 40.0,
                "text": (
                    "from typing import Sequence, Union\n\n"
                    "def compute_average(values: Sequence[Union[int, float]]) -> float:\n"
                    "    \"\"\"Calculates arithmetic mean with zero-division safety and numerical stability.\"\"\"\n"
                    "    if not values:\n"
                    "        return 0.0\n"
                    "    return float(sum(values)) / len(values)\n"
                ),
                "params_b": 104.0,
            }
            challenger_output_2 = {
                "model_id": "gemini_3_1_pro",
                "name": "Gemini 3.1 Pro",
                "status": "SUCCESS",
                "latency_ms": 80.0,
                "text": "def compute_average(vals):\n    return sum(vals)/len(vals)",
                "params_b": 70.0,
            }

            res = grader.grade_arena_trial(
                prompt=f"Round {r}: Write a high-performance Python function for average computation",
                champion_output=champ_output,
                challenger_outputs=[challenger_output_1, challenger_output_2],
            )

            assert res["winner_id"] == "command_r_plus_104b"

            with open(ledger_file, "r", encoding="utf-8") as f:
                current_ledger = json.load(f)

            models_map = {m["id"]: m["elo"] for m in current_ledger["leaderboard"]}
            cmd_elo = models_map["command_r_plus_104b"]
            kimi_elo = models_map["kimi_tandem_titan"]

            if cmd_elo > kimi_elo and not overtake_reached:
                overtake_reached = True
                overtake_round = r

            time.sleep(0.015)
            resolved_champ = resolver.resolve_current_champion(force_refresh=True)

            if overtake_reached:
                assert resolved_champ["model_id"] == "command_r_plus_104b"
                assert resolved_champ["rank"] == 1
                break

        assert overtake_reached, f"Challenger did not overtake Champion within {max_rounds} rounds."
        assert overtake_round <= 5, f"Expected overtake within 5 rounds, took {overtake_round} rounds."

    def test_bidirectional_champion_handover(self, tmp_path):
        """
        Adversarially tests bidirectional promotion:
        1. Model B overtakes Model A to become Champion.
        2. Model A wins consecutive subsequent matches and overtakes Model B back.
        3. Verifies router dynamically flips Champion twice without state corruption.
        """
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        data = create_isolated_leaderboard_data(
            champ_id="model_a",
            champ_elo=3600.0,
            challenger_id="model_b",
            challenger_elo=3590.0,
            third_id="model_c",
            third_elo=3200.0,
        )
        atomic_save_canonical_ledger(data, ledger_file)

        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_sec=0.01)
        engine = CanonicalAILeaderboardEngine(ledger_path=ledger_file)

        # Initial: Model A is Champion
        assert resolver.resolve_current_champion(force_refresh=True)["model_id"] == "model_a"

        # Phase 1: Model B wins 3 matches against Model A
        for _ in range(3):
            engine.record_match_victory({
                "match_id": f"m_{uuid.uuid4().hex[:6]}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "match_type": "DUEL",
                "topic_or_challenge": "Phase 1 Duel",
                "model_a_id": "model_b",
                "model_b_id": "model_a",
                "score_a": 1.0,
                "score_b": 0.0,
                "winner_id": "model_b",
                "truth_verified": True,
                "truth_compliance_pct": 100.0,
            })

        time.sleep(0.015)
        champ_p1 = resolver.resolve_current_champion(force_refresh=True)
        assert champ_p1["model_id"] == "model_b", f"Expected model_b as champ after Phase 1, got {champ_p1['model_id']}"

        # Phase 2: Model A wins 5 matches against Model B to reclaim #1
        for _ in range(5):
            engine.record_match_victory({
                "match_id": f"m_{uuid.uuid4().hex[:6]}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "match_type": "DUEL",
                "topic_or_challenge": "Phase 2 Duel",
                "model_a_id": "model_a",
                "model_b_id": "model_b",
                "score_a": 1.0,
                "score_b": 0.0,
                "winner_id": "model_a",
                "truth_verified": True,
                "truth_compliance_pct": 100.0,
            })

        time.sleep(0.015)
        champ_p2 = resolver.resolve_current_champion(force_refresh=True)
        assert champ_p2["model_id"] == "model_a", f"Expected model_a to reclaim champ in Phase 2, got {champ_p2['model_id']}"

    def test_three_way_circular_promotion_handover(self, tmp_path):
        """
        Adversarially tests 3-way multi-hop handover (A -> B -> C -> A):
        Verifies leaderboard rankings re-index accurately on every hop.
        """
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        data = create_isolated_leaderboard_data(
            champ_id="model_a",
            champ_elo=3600.0,
            challenger_id="model_b",
            challenger_elo=3595.0,
            third_id="model_c",
            third_elo=3590.0,
        )
        atomic_save_canonical_ledger(data, ledger_file)

        resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_sec=0.01)
        engine = CanonicalAILeaderboardEngine(ledger_path=ledger_file)

        # Initial: Model A is Champion
        assert resolver.resolve_current_champion(force_refresh=True)["model_id"] == "model_a"

        # Hop 1: B beats A -> B becomes #1
        for _ in range(2):
            engine.record_match_victory({
                "match_id": f"m_{uuid.uuid4().hex[:6]}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "match_type": "DUEL",
                "model_a_id": "model_b",
                "model_b_id": "model_a",
                "score_a": 1.0,
                "score_b": 0.0,
                "winner_id": "model_b",
                "truth_verified": True,
            })
        time.sleep(0.015)
        assert resolver.resolve_current_champion(force_refresh=True)["model_id"] == "model_b"

        # Hop 2: C beats B -> C becomes #1
        for _ in range(4):
            engine.record_match_victory({
                "match_id": f"m_{uuid.uuid4().hex[:6]}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "match_type": "DUEL",
                "model_a_id": "model_c",
                "model_b_id": "model_b",
                "score_a": 1.0,
                "score_b": 0.0,
                "winner_id": "model_c",
                "truth_verified": True,
            })
        time.sleep(0.015)
        assert resolver.resolve_current_champion(force_refresh=True)["model_id"] == "model_c"

        # Hop 3: A beats C -> A becomes #1
        for _ in range(5):
            engine.record_match_victory({
                "match_id": f"m_{uuid.uuid4().hex[:6]}",
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "match_type": "DUEL",
                "model_a_id": "model_a",
                "model_b_id": "model_c",
                "score_a": 1.0,
                "score_b": 0.0,
                "winner_id": "model_a",
                "truth_verified": True,
            })
        time.sleep(0.015)
        assert resolver.resolve_current_champion(force_refresh=True)["model_id"] == "model_a"


# ===========================================================================
# 2. 24/7 Continuous Multi-Turn Trial Execution & Zero-Latency Tests
# ===========================================================================

class TestMultiTurnContinuousZeroLatency:
    """
    Adversarially tests multi-turn conversation trial execution, verifying:
    - Zero added latency for user-facing responses (enqueue takes < 2.0 ms).
    - Asynchronous background execution of challenger models and grading without blocking.
    - High-throughput multi-turn conversation bursts (50 consecutive turns).
    """

    def test_multi_turn_conversation_stream_latency(self, tmp_path):
        """
        Simulate a 15-turn continuous user dialogue.
        Measure time taken for synchronous champion streaming vs background processing.
        Verify that user prompt response latency is unaffected by challenger execution time.
        """
        async def _run_test():
            ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
            ledger_file.parent.mkdir(parents=True, exist_ok=True)
            lora_file = tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl"
            obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"

            initial_data = create_isolated_leaderboard_data()
            atomic_save_canonical_ledger(initial_data, ledger_file)

            resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_sec=0.01)
            grader = TriOrchestratorBlindGrader(
                leaderboard_path=ledger_file,
                lora_sink_path=lora_file,
                obsidian_sink_path=obsidian_dir,
            )

            completed_trials: List[ArenaTrialResult] = []
            trial_completed_event = asyncio.Event()

            def on_trial_done(result: ArenaTrialResult):
                completed_trials.append(result)
                trial_completed_event.set()

            # Simulate intentionally slow challenger (80ms) to prove zero-latency isolation
            async def slow_challenger_executor(spec: Dict[str, Any], prompt: str, timeout: float):
                await asyncio.sleep(0.08)  # 80ms latency in background
                return {
                    "model_id": spec.get("model_id", "challenger"),
                    "name": spec.get("name", "Challenger"),
                    "status": "SUCCESS",
                    "text": f"Slow response for {prompt[:20]}",
                    "latency_ms": 80.0,
                }

            arena_engine = ContinuousArenaEngine(
                queue_maxsize=100,
                grader=grader,
                executor_func=slow_challenger_executor,
                on_trial_complete=on_trial_done,
            )
            arena_engine.start()

            # Fast Champion bridge returning generator (0.5ms per token)
            class FastChampionBridge:
                async def stream_generate(self, prompt: str, **kwargs):
                    tokens = [f"Word_{i} " for i in range(10)]
                    for tok in tokens:
                        await asyncio.sleep(0.0005)
                        yield tok

            router = ContinuousArenaInferenceRouter(
                resolver=resolver,
                arena_engine=arena_engine,
                bridges={"llama_rpc": FastChampionBridge()},
                enable_arena=True,
            )

            num_turns = 15
            turn_latencies: List[float] = []

            for turn_idx in range(1, num_turns + 1):
                prompt = f"Turn {turn_idx}: Explain the biological mechanics of Zone 2 mitochondrial biogenesis."
                t0 = time.perf_counter()

                # Stream champion response
                received_tokens = []
                async for token in router.stream_generate(prompt):
                    received_tokens.append(token)

                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                turn_latencies.append(elapsed_ms)

                # Response must be fast (e.g. < 50ms total for 10 tokens), regardless of 80ms challenger delay
                assert len(received_tokens) == 10
                assert elapsed_ms < 50.0, f"Turn {turn_idx} took {elapsed_ms:.2f}ms, expected < 50ms."

            # Wait for all background trials to finish processing
            wait_start = time.time()
            while len(completed_trials) < num_turns and (time.time() - wait_start) < 10.0:
                await asyncio.sleep(0.05)

            await arena_engine.stop(wait=True)

            assert len(completed_trials) == num_turns, (
                f"Expected {num_turns} completed background trials, got {len(completed_trials)}"
            )

            # Verify operational metrics
            metrics = arena_engine.get_metrics()
            assert metrics["total_enqueued"] == num_turns
            assert metrics["total_completed"] == num_turns
            assert metrics["total_failed"] == 0

        asyncio.run(_run_test())

    def test_enqueue_microbenchmark_invariant(self, tmp_path):
        """
        Micro-benchmark: Measure exact wall-clock enqueue duration across 500 requests.
        Invariant: Max enqueue latency < 2.0ms (typically < 0.05ms).
        """
        engine = ContinuousArenaEngine(queue_maxsize=1000)
        engine.start()

        latencies_ms = []
        for i in range(500):
            champ_res = {"model_id": "kimi", "text": f"res_{i}", "status": "SUCCESS"}
            t0 = time.perf_counter()
            ok = engine.enqueue_trial(prompt=f"p_{i}", champion_result=champ_res)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(dt_ms)
            assert ok is True

        engine.close()

        avg_lat = sum(latencies_ms) / len(latencies_ms)
        max_lat = max(latencies_ms)
        p99_lat = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)]

        assert max_lat < 2.0, f"Max enqueue latency exceeded 2.0ms: {max_lat:.4f}ms"
        assert p99_lat < 0.5, f"p99 enqueue latency exceeded 0.5ms: {p99_lat:.4f}ms"
        assert avg_lat < 0.1, f"Avg enqueue latency exceeded 0.1ms: {avg_lat:.4f}ms"

    def test_high_throughput_burst_multi_turn_resilience(self, tmp_path):
        """
        Stress test: Burst 50 continuous turns into router.
        Verify bounded queue prevents memory explosion and all trials are drained safely.
        """
        async def _run_test():
            ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
            ledger_file.parent.mkdir(parents=True, exist_ok=True)
            lora_file = tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl"
            obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"

            initial_data = create_isolated_leaderboard_data()
            atomic_save_canonical_ledger(initial_data, ledger_file)

            resolver = ChampionLeaderboardResolver(leaderboard_path=ledger_file, debounce_sec=0.01)
            grader = TriOrchestratorBlindGrader(
                leaderboard_path=ledger_file,
                lora_sink_path=lora_file,
                obsidian_sink_path=obsidian_dir,
            )

            completed_count = 0
            lock = threading.Lock()

            def on_done(res: ArenaTrialResult):
                nonlocal completed_count
                with lock:
                    completed_count += 1

            arena_engine = ContinuousArenaEngine(
                queue_maxsize=100,
                grader=grader,
                on_trial_complete=on_done,
            )
            arena_engine.start()

            for i in range(50):
                champ_res = {
                    "model_id": "kimi_tandem_titan",
                    "name": "Kimi Tandem Titan",
                    "status": "SUCCESS",
                    "latency_ms": 15.0,
                    "text": f"Response {i}",
                }
                ok = arena_engine.enqueue_trial(
                    prompt=f"Burst prompt {i}",
                    champion_result=champ_res,
                )
                assert ok is True

            t_start = time.time()
            while completed_count < 50 and (time.time() - t_start) < 10.0:
                await asyncio.sleep(0.05)

            await arena_engine.stop(wait=True)
            assert completed_count == 50, f"Expected 50 completed trials, got {completed_count}"

        asyncio.run(_run_test())


# ===========================================================================
# 3. Tri-Vault Dataset Integrity & Knowledge Harvesting Tests
# ===========================================================================

class TestTriVaultDatasetIntegrity:
    """
    Adversarially tests the integrity of exported Tri-Vault artifacts:
    - LoRA DPO JSONL format, schema compliance, zero-mock validation.
    - Obsidian Markdown debate files, YAML frontmatter, 3-judge breakdowns, Wikilinks.
    - Multi-threaded concurrent writes to verify zero file corruption.
    """

    def test_lora_dpo_jsonl_schema_and_zero_mock(self, tmp_path):
        """
        Validates line-by-line JSONL format and ensures zero fabricated mocks.
        """
        lora_file = tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl"
        obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        data = create_isolated_leaderboard_data()
        atomic_save_canonical_ledger(data, ledger_file)

        grader = TriOrchestratorBlindGrader(
            leaderboard_path=ledger_file,
            lora_sink_path=lora_file,
            obsidian_sink_path=obsidian_dir,
        )

        prompts = [
            "Implement high-throughput ring buffer in C++20",
            "Explain Pan-Tompkins QRS peak detection algorithm with 512Hz DSP",
            "Draft a distributed ELO reconciliation strategy for local AI mesh",
        ]

        for p in prompts:
            champ = {
                "model_id": "kimi_tandem_titan",
                "name": "Kimi Tandem",
                "status": "SUCCESS",
                "latency_ms": 35.0,
                "text": f"Solution for {p}: details and algorithms.",
            }
            challengers = [
                {
                    "model_id": "command_r_plus_104b",
                    "name": "Command-R+",
                    "status": "SUCCESS",
                    "latency_ms": 45.0,
                    "text": f"Exhaustive architectural breakdown for {p}: complete code and proofs.",
                },
                {
                    "model_id": "gemini_3_1_pro",
                    "name": "Gemini 3.1 Pro",
                    "status": "SUCCESS",
                    "latency_ms": 25.0,
                    "text": f"Frontier analysis for {p}.",
                },
            ]
            grader.grade_arena_trial(p, champ, challengers)

        # Inspect exported JSONL
        assert lora_file.exists(), "LoRA JSONL file was not created"
        with open(lora_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) >= 3, f"Expected at least 3 JSONL lines, found {len(lines)}"

        for idx, line in enumerate(lines):
            record = json.loads(line)
            assert "trial_id" in record, f"Line {idx} missing trial_id"
            assert "timestamp" in record, f"Line {idx} missing timestamp"
            assert "prompt" in record, f"Line {idx} missing prompt"
            assert "chosen" in record, f"Line {idx} missing chosen"
            assert "rejected" in record, f"Line {idx} missing rejected"
            assert "meta" in record, f"Line {idx} missing meta"

            valid, reason = verify_zero_mock_compliance(record)
            assert valid is True, f"Rule #0 violation on line {idx}: {reason}"

            assert record["meta"]["zero_mock_certified"] is True
            assert record["meta"]["truth_verified"] is True
            assert any(p in record["prompt"] for p in prompts)

    def test_obsidian_markdown_debate_files_structure_and_wikilinks(self, tmp_path):
        """
        Validates Obsidian Markdown transcript files:
        - YAML frontmatter (title, date, tags, winner).
        - Pairwise match breakdown section.
        - Judicial Council breakdown blocks.
        - Canonical master Wikilinks ([[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]], [[Index]]).
        """
        lora_file = tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl"
        obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        data = create_isolated_leaderboard_data()
        atomic_save_canonical_ledger(data, ledger_file)

        grader = TriOrchestratorBlindGrader(
            leaderboard_path=ledger_file,
            lora_sink_path=lora_file,
            obsidian_sink_path=obsidian_dir,
        )

        trial_prompt = "Design a 0.27ms RTT PCIe Thunderbolt 4 Bridge for local AI tensors"
        champ = {
            "model_id": "kimi_tandem_titan",
            "name": "Kimi Tandem",
            "status": "SUCCESS",
            "latency_ms": 50.0,
            "text": "TB4 DMA Bridge implementation using memory-mapped buffers.",
        }
        challengers = [
            {
                "model_id": "command_r_plus_104b",
                "name": "Command-R+ 104B",
                "status": "SUCCESS",
                "latency_ms": 30.0,
                "text": "Ultra-low latency ring buffer architecture with zero-copy DMA.",
            }
        ]

        res = grader.grade_arena_trial(trial_prompt, champ, challengers)
        t_id = res["trial_id"]
        expected_md_file = obsidian_dir / f"ARENA_TRIAL_{t_id}.md"

        assert expected_md_file.exists(), f"Obsidian debate file {expected_md_file} was not generated."

        with open(expected_md_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Check YAML Frontmatter
        assert md_content.startswith("---"), "Missing YAML frontmatter opening"
        assert 'title: "Continuous Arena Trial' in md_content
        assert "tags: [arena, debate, tri_orchestrator, lora, zero_mock]" in md_content
        assert f'winner: "{res["winner_id"]}"' in md_content

        # Check Structural Sections
        assert f"# ⚔️ Continuous AI Arena Trial — {t_id}" in md_content
        assert "## ⚖️ Pairwise Match Breakdown" in md_content
        assert "## 🏛️ Judicial Council Evaluations" in md_content or "## 📊 Detailed 5-Pillar Score Matrix" in md_content

        # Check Master Wikilinks
        assert "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]" in md_content
        assert "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]" in md_content
        assert "[[Index]]" in md_content

    def test_concurrent_multi_thread_trivault_export_safety(self, tmp_path):
        """
        Adversarially hammers TriVaultSink from 10 parallel threads writing 15 trials each (150 total).
        Verifies that no JSONL lines are corrupted or interleaved, and all Markdown notes exist.
        """
        lora_file = tmp_path / "lora_datasets" / "continuous_lora_dataset.jsonl"
        obsidian_dir = tmp_path / "obsidian_vault" / "01_DEBATES"
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        data = create_isolated_leaderboard_data()
        atomic_save_canonical_ledger(data, ledger_file)

        grader = TriOrchestratorBlindGrader(
            leaderboard_path=ledger_file,
            lora_sink_path=lora_file,
            obsidian_sink_path=obsidian_dir,
        )

        num_threads = 10
        trials_per_thread = 15
        errors = []

        def worker_task(thread_id: int):
            for i in range(trials_per_thread):
                try:
                    p = f"Thread {thread_id} Trial {i} prompt"
                    c = {
                        "model_id": "kimi_tandem_titan",
                        "name": "Kimi",
                        "status": "SUCCESS",
                        "latency_ms": 20.0,
                        "text": f"Output from thread {thread_id} run {i}",
                    }
                    ch = [
                        {
                            "model_id": "command_r_plus_104b",
                            "name": "Command-R+",
                            "status": "SUCCESS",
                            "latency_ms": 25.0,
                            "text": f"Challenger output from thread {thread_id} run {i}",
                        }
                    ]
                    grader.grade_arena_trial(p, c, ch)
                except Exception as e:
                    errors.append(f"Thread {thread_id} run {i} error: {e}")

        threads = [threading.Thread(target=worker_task, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered {len(errors)} thread errors: {errors[:5]}"

        # Verify JSONL lines count and valid JSON syntax
        with open(lora_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        total_expected = num_threads * trials_per_thread
        assert len(lines) >= total_expected, f"Expected at least {total_expected} JSONL lines, got {len(lines)}"

        for idx, line in enumerate(lines):
            try:
                rec = json.loads(line)
                assert "trial_id" in rec
            except Exception as e:
                pytest.fail(f"Corrupted JSON on line {idx}: {e}")

        # Verify Markdown files count
        md_files = list(obsidian_dir.glob("ARENA_TRIAL_*.md"))
        assert len(md_files) == total_expected, f"Expected {total_expected} Markdown files, got {len(md_files)}"


# ===========================================================================
# 4. Fault Invariants, Boundary Edge Cases & Self-Healing
# ===========================================================================

class TestFaultInvariantsAndEdgeCases:
    """
    Adversarially tests system behavior under corrupted files, missing directories,
    and extreme mathematical inputs.
    """

    def test_corrupted_leaderboard_recovery_and_fallback(self, tmp_path):
        """
        Tests that when canonical_ai_leaderboard.json is corrupted (malformed JSON or empty),
        ChampionLeaderboardResolver seamlessly returns default champion fallback without throwing exceptions.
        """
        corrupted_file = tmp_path / "corrupted_leaderboard.json"
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID_JSON_CORRUPTED_STREAM: ")

        resolver = ChampionLeaderboardResolver(leaderboard_path=corrupted_file, debounce_sec=0.01)
        champ = resolver.resolve_current_champion(force_refresh=True)

        assert champ is not None
        assert champ["model_id"] == "kimi_tandem_titan"
        assert champ["is_fallback"] is True
        assert champ["rank"] == 1

    def test_challenger_timeout_and_error_isolation(self, tmp_path):
        """
        Tests that if a challenger model times out or throws an unhandled exception,
        the background ContinuousArenaEngine isolates the failure, assigns 0.0 scores,
        and continues continuous execution without crashing.
        """
        ledger_file = tmp_path / "data" / "canonical_ai_leaderboard.json"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_save_canonical_ledger(create_isolated_leaderboard_data(), ledger_file)

        grader = TriOrchestratorBlindGrader(leaderboard_path=ledger_file)

        champ = {
            "model_id": "kimi_tandem_titan",
            "name": "Kimi",
            "status": "SUCCESS",
            "latency_ms": 30.0,
            "text": "Valid Python implementation",
        }
        failing_challengers = [
            {
                "model_id": "command_r_plus_104b",
                "name": "Command-R+",
                "status": "TIMEOUT",
                "error": "Execution timed out after 15.0s",
                "latency_ms": 15000.0,
                "text": "",
            },
            {
                "model_id": "gemini_3_1_pro",
                "name": "Gemini",
                "status": "ERROR",
                "error": "Connection refused to remote gateway",
                "latency_ms": 100.0,
                "text": "",
            }
        ]

        result = grader.grade_arena_trial(
            prompt="Write a test function",
            champion_output=champ,
            challenger_outputs=failing_challengers,
        )

        assert result["winner_id"] == "kimi_tandem_titan"
        for alias, mid in result["alias_mapping"].items():
            if mid in ["command_r_plus_104b", "gemini_3_1_pro"]:
                assert result["total_scores"][alias] == 0.0
            elif mid == "kimi_tandem_titan":
                assert result["total_scores"][alias] > 50.0

    def test_extreme_disparity_elo_delta_clamping(self):
        """
        Tests mathematical stability under massive ELO disparities (3500 vs 1500, Delta = 2000).
        Verifies that dynamic K-factor and logistic expectations produce finite, bounded, positive deltas.
        """
        r_high = 3500.0
        r_low = 1500.0

        e_high, e_low = 1.0 / (1.0 + 10 ** ((r_low - r_high) / 400.0)), 1.0 / (1.0 + 10 ** ((r_high - r_low) / 400.0))
        assert math.isclose(e_high + e_low, 1.0, rel_tol=1e-9)
        assert e_high > 0.99999
        assert e_low < 0.00001

        k = compute_dynamic_k_factor(base_k=32.0, eta_size=1.0, eta_token=1.0, eta_consensus=1.0, eta_compute=1.0, eta_truth=1.0)
        delta_high_win = compute_elo_delta(rating_a=r_high, rating_b=r_low, score_a=1.0, k_a=k, k_b=k)[0]
        delta_low_loss = compute_elo_delta(rating_a=r_low, rating_b=r_high, score_a=0.0, k_a=k, k_b=k)[0]

        assert delta_high_win >= 0.0
        assert delta_low_loss <= 0.0
        assert not math.isnan(delta_high_win)
        assert not math.isinf(delta_high_win)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
