#!/usr/bin/env python3
"""
Adversarial Stress-Test Suite for Continuous AI Arena (Milestone 4 Independent Review)
======================================================================================
Reviewer: reviewer_m4_2 (Role: Grading, ELO & Tri-Vault Reviewer)

Stress-tests:
1. Blind Anonymization & Header Stripping
2. 3-Judge Panel & 5-Pillar Multi-Dimensional Scoring
3. Dynamic 6-Factor K-Factor & Logistic ELO Formula Invariants
4. Dynamic Champion Promotion & Leaderboard Re-Indexing
5. Tri-Vault Harvesting, Multi-Threaded Concurrency, and Rule #0 Quarantine
6. Challenger Pool Cycler Edge Cases & Vault Scanning
"""

import os
import sys
import time
import math
import json
import uuid
import shutil
import tempfile
import threading
import pytest
from pathlib import Path
from typing import Dict, Any, List

# Setup Monorepo paths
MONOREPO_ROOT = Path(__file__).resolve().parents[1]
if str(MONOREPO_ROOT) not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT))
if str(MONOREPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src") not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"))
if str(MONOREPO_ROOT / "02_ai_models_and_inference") not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT / "02_ai_models_and_inference"))
if str(MONOREPO_ROOT / "04_data_and_memory") not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT / "04_data_and_memory"))
if str(MONOREPO_ROOT / "05_agents_and_swarms" / "tri_orchestrator") not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT / "05_agents_and_swarms" / "tri_orchestrator"))

from challenger_pool_cycler import ChallengerPoolCycler, DEFAULT_CHALLENGER_POOL
from continuous_arena_grader import TriOrchestratorBlindGrader, ContinuousArenaGrader, BLIND_ALIASES
from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    compute_expected_outcome,
    calculate_expected_elo,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k_factor,
    compute_elo_delta,
    compute_skill_delta,
    validate_ledger_schema,
    atomic_save_canonical_ledger,
)
from tri_vault_sink import TriVaultSink, verify_zero_mock_compliance, check_storage_health


# ===========================================================================
# 1. BLIND ANONYMIZATION & HEADER STRIPPING TESTS
# ===========================================================================
class TestBlindAnonymization:
    def test_header_stripping_various_patterns(self, tmp_path):
        grader = TriOrchestratorBlindGrader(
            leaderboard_path=tmp_path / "ledger.json",
            lora_sink_path=tmp_path / "lora.jsonl",
            obsidian_sink_path=tmp_path / "obsidian",
        )
        champ = {
            "model_id": "kimi_tandem_titan",
            "name": "Kimi Tandem Titan",
            "status": "SUCCESS",
            "latency_ms": 50.0,
            "text": "[Kimi Tandem Titan] def solve_problem(): return 42",
        }
        c1 = {
            "model_id": "command_r_plus_104b",
            "name": "Command-R+ 104B",
            "status": "SUCCESS",
            "latency_ms": 60.0,
            "text": "[Cohere Command-R+] def solve_problem() -> int: return 42",
        }
        c2 = {
            "model_id": "gemini_3_1_pro",
            "name": "Gemini 3.1 Pro",
            "status": "SUCCESS",
            "latency_ms": 40.0,
            "text": "def solve_problem():\n    return 42",
        }

        alias_map, payloads = grader._anonymize_participants(champ, [c1, c2])

        # Verify 3 distinct aliases
        assert len(alias_map) == 3
        assert set(alias_map.values()) == {"kimi_tandem_titan", "command_r_plus_104b", "gemini_3_1_pro"}

        # Verify headers stripped
        for alias, payload in payloads.items():
            assert not payload["text"].startswith("[Kimi")
            assert not payload["text"].startswith("[Cohere")
            assert "def solve_problem" in payload["text"]

    def test_alias_entropy_distribution(self, tmp_path):
        """Verify randomization doesn't bias alias assignment."""
        grader = TriOrchestratorBlindGrader(
            leaderboard_path=tmp_path / "ledger.json",
            lora_sink_path=tmp_path / "lora.jsonl",
            obsidian_sink_path=tmp_path / "obsidian",
            randomize_alias_order=True
        )
        champ = {"model_id": "champ", "text": "champ output", "status": "SUCCESS"}
        c1 = {"model_id": "c1", "text": "c1 output", "status": "SUCCESS"}
        c2 = {"model_id": "c2", "text": "c2 output", "status": "SUCCESS"}

        counts = {"alpha": 0, "beta": 0, "gamma": 0}
        trials = 300
        for _ in range(trials):
            alias_map, _ = grader._anonymize_participants(champ, [c1, c2])
            # Find which alias champ got
            for a, mid in alias_map.items():
                if mid == "champ":
                    counts[a] += 1

        # Each alias should receive roughly 1/3 (~100) of the assignments (within 35-165 range)
        for a in ["alpha", "beta", "gamma"]:
            assert 35 <= counts[a] <= 165, f"Alias {a} had biased count: {counts[a]}/{trials}"


# ===========================================================================
# 2. 3-JUDGE PANEL & 5-PILLAR SCORING TESTS
# ===========================================================================
class TestJudicialPanelAndScoring:
    def test_5_pillar_mathematical_weights(self, tmp_path):
        grader = TriOrchestratorBlindGrader(
            leaderboard_path=tmp_path / "ledger.json",
            lora_sink_path=tmp_path / "lora.jsonl",
            obsidian_sink_path=tmp_path / "obsidian",
        )
        payloads = {
            "alpha": {
                "text": "def calculate_matrix():\n    return [[1, 2], [3, 4]]",
                "status": "SUCCESS",
                "latency_ms": 80.0,
                "tokens_generated": 64,
                "params_b": 70.0
            }
        }
        scores, totals, breakdowns = grader._evaluate_judicial_council("Compute matrix", payloads)

        sc = scores["alpha"]
        expected_total = round(
            sc["syntax"] * 0.25 +
            sc["depth"] * 0.25 +
            sc["economy"] * 0.20 +
            sc["safety"] * 0.15 +
            sc["truth"] * 0.15,
            2
        )
        assert abs(totals["alpha"] - expected_total) < 1e-3
        assert sc["safety"] == 100.0
        assert sc["truth"] == 100.0

    def test_disqualification_on_failure(self, tmp_path):
        grader = TriOrchestratorBlindGrader(
            leaderboard_path=tmp_path / "ledger.json",
            lora_sink_path=tmp_path / "lora.jsonl",
            obsidian_sink_path=tmp_path / "obsidian",
        )
        payloads = {
            "alpha": {
                "text": "",
                "status": "ERROR",
                "error": "Connection timed out",
                "latency_ms": 15000.0,
                "tokens_generated": 0,
            },
            "beta": {
                "text": "def healthy_func(): return True",
                "status": "SUCCESS",
                "latency_ms": 50.0,
                "tokens_generated": 32,
            }
        }
        scores, totals, breakdowns = grader._evaluate_judicial_council("Test", payloads)

        assert totals["alpha"] == 0.0
        assert scores["alpha"]["syntax"] == 0.0
        assert scores["alpha"]["safety"] == 0.0
        assert breakdowns["alpha"]["devils_advocate"]["score"] == 0.0
        assert totals["beta"] > 80.0


# ===========================================================================
# 3. DYNAMIC K-FACTOR & LOGISTIC ELO FORMULA INVARIANTS
# ===========================================================================
class TestEloMathematicalInvariants:
    def test_logistic_expected_outcome_invariants(self):
        """E_A + E_B == 1.0 across any rating differences."""
        ratings = [500.0, 1000.0, 1500.0, 2000.0, 2800.0, 3089.0, 3500.0, 4500.0, 5000.0]
        for r_a in ratings:
            for r_b in ratings:
                e_a, e_b = compute_expected_outcome(r_a, r_b)
                assert abs((e_a + e_b) - 1.0) < 1e-9
                assert 0.0 < e_a < 1.0
                assert 0.0 < e_b < 1.0
                if r_a > r_b:
                    assert e_a > 0.5 and e_b < 0.5
                elif r_a < r_b:
                    assert e_a < 0.5 and e_b > 0.5
                else:
                    assert abs(e_a - 0.5) < 1e-9

    def test_all_6_dynamic_k_factor_multipliers(self):
        # 1. eta_size bounds
        assert compute_eta_size(0.1) == 2.50  # Clamped max
        assert compute_eta_size(1000.0) == 0.617  # Larger model -> smaller multiplier
        assert compute_eta_size(70.0) == 1.00  # Baseline 70B -> exactly 1.0
        assert compute_eta_size(7.0) > 1.00   # Smaller model -> > 1.0

        # 2. eta_token bounds
        assert compute_eta_token(2048) == 1.00
        assert compute_eta_token(1024) == 1.50  # Clamped max
        assert compute_eta_token(10000) == 0.50 # Clamped min

        # 3. eta_consensus bounds
        assert compute_eta_consensus(1.0) == 1.00
        assert compute_eta_consensus(0.0) == 0.50
        assert compute_eta_consensus(0.5) == 0.75

        # 4. eta_compute bounds
        assert compute_eta_compute(70.0) == 1.00
        assert compute_eta_compute(0.0) == 1.30  # Sub-millisecond -> clamped max
        assert compute_eta_compute(500.0) == 0.70 # Slow -> clamped min

        # 5. eta_truth zero-mock enforcement
        assert compute_eta_truth(True, 100.0) == 1.00
        assert compute_eta_truth(False, 100.0) == 0.00
        assert compute_eta_truth(True, 99.9) == 0.00

        # 6. Composite K-Factor computation
        k_dyn = compute_dynamic_k_factor(
            matches_played=5,
            match_type="TRI_ORCHESTRATOR_DEBATE",
            eta_size=1.2,
            eta_token=1.1,
            eta_consensus=0.9,
            eta_compute=1.05,
            eta_truth=1.0
        )
        assert k_dyn > 0.0
        # If eta_truth is 0, K MUST be 0.0
        k_unverified = compute_dynamic_k_factor(
            matches_played=5,
            eta_truth=0.0
        )
        assert k_unverified == 0.0


# ===========================================================================
# 4. DYNAMIC CHAMPION PROMOTION & LEADERBOARD RE-INDEXING
# ===========================================================================
class TestChampionPromotionDynamics:
    def test_dynamic_champion_promotion_upon_elo_overtake(self, tmp_path):
        ledger_path = tmp_path / "canonical_ai_leaderboard.json"
        engine = CanonicalAILeaderboardEngine(ledger_path=ledger_path)
        
        # Initialize ledger
        initial_data = engine.get_canonical_leaderboard(persist=True)
        assert len(initial_data["leaderboard"]) > 0

        # Set up a match where challenger beats champion with high ELO deltas
        rankings = engine.get_rankings()
        champion = rankings[0]
        challenger_id = "command_r_plus_104b"

        # Boost challenger or simulate consecutive wins
        for i in range(10):
            match_payload = {
                "match_id": f"TEST_PROMOTION_{i}",
                "model_a_id": challenger_id,
                "model_b_id": champion["id"],
                "score_a": 1.0,
                "score_b": 0.0,
                "match_type": "BENCHMARK_CHALLENGE",
                "truth_verified": True,
                "truth_compliance_pct": 100.0,
                "consumed_tokens_a": 1024,
                "consumed_tokens_b": 2048,
                "rtt_ms": 30.0,
            }
            res = engine.record_match_victory(match_payload)
            new_ranks = engine.get_rankings()
            if new_ranks[0]["id"] == challenger_id:
                break

        final_ranks = engine.get_rankings()
        # Verify rank 1 is updated
        assert final_ranks[0]["rank"] == 1
        for idx, m in enumerate(final_ranks):
            assert m["rank"] == idx + 1
            if idx > 0:
                assert (final_ranks[idx-1]["elo"], final_ranks[idx-1]["canonical_score"]) >= (m["elo"], m["canonical_score"])


# ===========================================================================
# 5. TRI-VAULT HARVESTING, MULTI-THREADED CONCURRENCY & RULE #0 QUARANTINE
# ===========================================================================
class TestTriVaultConcurrencyAndRuleZero:
    def test_rule_zero_quarantine_mock_data(self, tmp_path):
        sink = TriVaultSink(
            lora_dir=tmp_path / "lora",
            obsidian_dir=tmp_path / "obsidian",
            enforce_rule_zero=True
        )

        mock_trial = {
            "trial_id": "mock_trial_1",
            "prompt": "Test prompt",
            "winner_id": "model_x",
            "truth_verified": False,  # VIOLATION
            "truth_compliance_pct": 50.0,
        }

        with pytest.raises(ValueError, match="Rule #0 Violation"):
            sink.export_dpo_pair(mock_trial)

        assert sink.get_metrics()["rule_zero_violations_quarantined"] == 1

    def test_multithreaded_concurrent_writes_integrity(self, tmp_path):
        lora_dir = tmp_path / "lora"
        obsidian_dir = tmp_path / "obsidian"
        sink = TriVaultSink(
            lora_dir=lora_dir,
            obsidian_dir=obsidian_dir,
            enforce_rule_zero=True
        )

        num_threads = 10
        records_per_thread = 5
        errors = []

        def worker(thread_idx):
            try:
                for r in range(records_per_thread):
                    trial = {
                        "trial_id": f"trial_t{thread_idx}_r{r}",
                        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "prompt": f"Thread {thread_idx} Prompt {r}",
                        "winner_id": "kimi_tandem_titan",
                        "winner_alias": "alpha",
                        "judicial_rationale": f"Rationale for thread {thread_idx} record {r}",
                        "pairwise_matches": [
                            {"model_a_id": "kimi_tandem_titan", "model_b_id": "gemini_pro", "winner_id": "kimi_tandem_titan", "score_a": 95.0, "score_b": 90.0}
                        ],
                        "scores": {"alpha": {"syntax": 95.0, "depth": 95.0, "economy": 90.0, "safety": 100.0, "truth": 100.0}},
                        "total_scores": {"alpha": 94.5},
                        "truth_verified": True,
                        "truth_compliance_pct": 100.0,
                    }
                    res = sink.export_trial_to_trivault(trial)
                    if not res["dpo_exported"] or not res["obsidian_exported"]:
                        errors.append(f"Thread {thread_idx} write failed: {res}")
            except Exception as e:
                errors.append(f"Thread {thread_idx} exception: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent write errors: {errors}"

        # Verify JSONL lines
        dpo_file = lora_dir / "continuous_lora_dataset.jsonl"
        assert dpo_file.exists()
        with open(dpo_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == num_threads * records_per_thread

        # Verify Obsidian notes
        notes = list(obsidian_dir.glob("ARENA_TRIAL_*.md"))
        assert len(notes) == num_threads * records_per_thread


# ===========================================================================
# 6. CHALLENGER POOL CYCLER EDGE CASES & GGUF VAULT SCANNING
# ===========================================================================
class TestChallengerPoolCyclerEdgeCases:
    def test_strict_exclusion_of_champion(self):
        cycler = ChallengerPoolCycler()
        for champion_id in ["kimi_tandem_titan", "command_r_plus_104b", "gemini_3_1_pro"]:
            for _ in range(20):
                selected = cycler.select_challengers(exclude_model_id=champion_id, count=2)
                assert len(selected) == 2
                for model in selected:
                    assert model["model_id"] != champion_id

    def test_timeout_boundary_isolation(self):
        cycler = ChallengerPoolCycler()
        spec = cycler.pool[0]
        # Extremely small timeout <= 0.05 triggers instant TIMEOUT status
        res = cycler.execute_challenger(spec, "Test prompt", timeout=0.01)
        assert res["status"] == "TIMEOUT"
        assert "timeout" in res["error"].lower()
        assert res["tokens_generated"] == 0

    def test_vault_scanner_dynamic_registration(self, tmp_path):
        vault_dir = tmp_path / "gguf_vault"
        vault_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy GGUF files
        (vault_dir / "Command-R-Plus-104B-Q4_K_M.gguf").write_text("GGUF_HEADER")
        (vault_dir / "Qwen-2.5-Coder-7B-Instruct.gguf").write_text("GGUF_HEADER")

        cycler = ChallengerPoolCycler(vault_dir=vault_dir, auto_scan_vault=False)
        initial_count = len(cycler.pool)

        discovered = cycler.scan_gguf_vault()
        assert len(discovered) > 0
        assert len(cycler.pool) == initial_count + len(discovered)
