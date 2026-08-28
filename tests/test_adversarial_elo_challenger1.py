"""
Adversarial Stress Test Suite for Milestone 1: Canonical ELO Ledger & Math Engine.
================================================================================
Empirical Challenger 1 Test Suite.

Adversarially stress-tests:
1. Rating Extremes & Disparities (R_A=10000, R_B=10, floating-point precision, logistic limits)
2. Mathematical Invariance & Symmetry (Logistic E_A + E_B == 1.0, precision limits)
3. Parameter Efficiency Multiplier Bounds (eta_size from 0.0001B to 100,000B, exact thresholds)
4. Multi-Factor Dynamic Multipliers (eta_token, eta_consensus, eta_compute, eta_truth)
5. Asymmetric K-Factors & Expected Value Zero-Drift under Logistic Distribution
6. Specialist Skill Asymptotic Progression & Hard Boundary Clamping [50.0, 100.0]
7. High-Concurrency Stress Test (20 threads, 200 matches, POSIX atomic file integrity)
8. Long-Horizon Monte Carlo Simulation (500 matches, Schema v7 invariance, ranking order)
9. Adversarial Schema Corruption Injection & Detection
10. State Persistence & Read/Write Synchronization between record_match_victory and get_canonical_leaderboard
"""

import os
import sys
import json
import math
import time
import random
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, List
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"

for p in [REPO_ROOT, SRC_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from canonical_ai_leaderboard import (
    CanonicalAILeaderboardEngine,
    CANONICAL_LEADERBOARD_SCHEMA_V7,
    validate_ledger_schema,
    atomic_save_canonical_ledger,
    calculate_expected_elo,
    compute_expected_outcome,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k_factor,
    compute_elo_delta,
    compute_skill_delta,
)


class TestAdversarialRatingExtremes:
    """Stress tests for extreme rating disparities and numerical stability."""

    def test_extreme_disparity_10000_vs_10(self):
        """Test massive rating disparity: R_A = 10000.0, R_B = 10.0 (|Delta R| = 9990.0)."""
        r_a = 10000.0
        r_b = 10.0

        e_a, e_b = compute_expected_outcome(r_a, r_b)
        assert round(e_a + e_b, 12) == 1.0, f"Expected sum 1.0, got {e_a + e_b}"
        assert e_a > 0.9999999999, f"E_A must be virtually 1.0, got {e_a}"
        assert 0.0 <= e_b < 1e-10, f"E_B must be virtually 0.0, got {e_b}"

        # If Titan (10000) wins against Novice (10):
        # Delta for A should be +0.0 (or negligible), Delta for B should be -0.0
        delta_a_win, delta_b_loss, _, _ = compute_elo_delta(r_a, r_b, score_a=1.0, k_a=32.0, k_b=32.0)
        assert delta_a_win == 0.0, f"Titan winning against Novice should get 0 delta, got {delta_a_win}"
        assert delta_b_loss == 0.0, f"Novice losing against Titan should lose 0 delta, got {delta_b_loss}"

        # If Novice (10) upsets Titan (10000):
        # Delta for A should be -32.0, Delta for B should be +32.0 (maximum possible K)
        delta_a_upset, delta_b_upset, _, _ = compute_elo_delta(r_a, r_b, score_a=0.0, k_a=32.0, k_b=32.0)
        assert delta_a_upset == -32.0, f"Titan losing to Novice should lose full K (-32.0), got {delta_a_upset}"
        assert delta_b_upset == 32.0, f"Novice beating Titan should gain full K (+32.0), got {delta_b_upset}"

    def test_extreme_disparity_inverted_10_vs_10000(self):
        """Test inverted disparity: R_A = 10.0, R_B = 10000.0."""
        r_a = 10.0
        r_b = 10000.0

        e_a, e_b = compute_expected_outcome(r_a, r_b)
        assert round(e_a + e_b, 12) == 1.0
        assert 0.0 <= e_a < 1e-10
        assert e_b > 0.9999999999

    def test_floating_point_extreme_limits(self):
        """Test floating-point inputs across multiple orders of magnitude."""
        test_pairs = [
            (5000.0, 500.0),      # Standard domain extremes
            (500.0, 5000.0),
            (25000.0, 100.0),     # Massive scale
            (100.0, 25000.0),
            (1500.0001, 1500.0002), # Micro-differentials
        ]
        for r_a, r_b in test_pairs:
            e_a, e_b = compute_expected_outcome(r_a, r_b)
            assert not math.isnan(e_a) and not math.isnan(e_b)
            assert not math.isinf(e_a) and not math.isinf(e_b)
            assert round(e_a + e_b, 10) == 1.0
            assert 0.0 <= e_a <= 1.0
            assert 0.0 <= e_b <= 1.0

    def test_leaderboard_elo_clamping_invariants(self):
        """Verify that record_match_victory enforces [500.0, 5000.0] ELO clamping."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=tmp_path)
            data = engine.get_canonical_leaderboard(persist=True)

            # Force model_b to 500.0 ELO
            for m in data["leaderboard"]:
                if m["id"] == "gemini_37_flash":
                    m["elo"] = 500.0

            atomic_save_canonical_ledger(data, tmp_path)

            # Gemini loses match with massive K
            match_payload = {
                "match_id": "TEST_CLAMP_LOW",
                "model_a_id": "kimi_tandem_titan",
                "model_b_id": "gemini_37_flash",
                "score_a": 1.0,
                "score_b": 0.0,
                "truth_verified": True
            }
            res = engine.record_match_victory(match_payload)
            updated_gemini = res["updated_model_b"]
            assert updated_gemini["elo"] == 500.0, f"ELO must not drop below 500.0, got {updated_gemini['elo']}"

            # Force model_a to 5000.0 ELO
            data = engine.get_canonical_leaderboard(persist=False)
            for m in data["leaderboard"]:
                if m["id"] == "kimi_tandem_titan":
                    m["elo"] = 5000.0
            atomic_save_canonical_ledger(data, tmp_path)

            # Kimi wins match
            match_payload = {
                "match_id": "TEST_CLAMP_HIGH",
                "model_a_id": "kimi_tandem_titan",
                "model_b_id": "gemini_37_flash",
                "score_a": 1.0,
                "score_b": 0.0,
                "truth_verified": True
            }
            res = engine.record_match_victory(match_payload)
            updated_kimi = res["updated_model_a"]
            assert updated_kimi["elo"] == 5000.0, f"ELO must not exceed 5000.0, got {updated_kimi['elo']}"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestAdversarialEfficiencyMultipliers:
    """Stress tests for parameter efficiency and dynamic K-factor multipliers."""

    def test_parameter_efficiency_exhaustive_spectrum(self):
        """Test eta_size from microscopic SLMs (0.0001B) to hyperscale LLMs (10,000B)."""
        # Micro SLMs should hit max ceiling (2.50)
        assert compute_eta_size(0.0001) == 2.50
        assert compute_eta_size(0.05) == 2.50
        assert compute_eta_size(0.5) == 2.50
        assert compute_eta_size(1.0) == 2.50
        assert compute_eta_size(1.5) == 2.50

        # Exact calculated values in transition zone
        # log2(71) = 6.149747
        # For 7B: log2(8) = 3.0 -> 6.149747 / 3 = 2.0499
        assert abs(compute_eta_size(7.0) - 2.0499) < 1e-3

        # For 14B: log2(15) = 3.90689 -> 6.149747 / 3.90689 = 1.5741
        assert abs(compute_eta_size(14.0) - 1.5741) < 1e-3

        # For 32B: log2(33) = 5.04439 -> 6.149747 / 5.04439 = 1.2191
        assert abs(compute_eta_size(32.0) - 1.2191) < 1e-3

        # For 70B: log2(71) / log2(71) = 1.0000
        assert compute_eta_size(70.0) == 1.0000

        # For 88B: log2(89) = 6.47573 -> 6.149747 / 6.47573 = 0.9497
        assert abs(compute_eta_size(88.0) - 0.9497) < 1e-3

        # For 400B: log2(401) = 8.64746 -> 6.149747 / 8.64746 = 0.7112
        assert abs(compute_eta_size(400.0) - 0.7112) < 1e-3

        # Hyperscale models should hit minimum floor (0.50)
        assert compute_eta_size(10000.0) == 0.50
        assert compute_eta_size(100000.0) == 0.50

        # Monotonicity test across 100 random sorted points
        sample_params = sorted([random.uniform(0.1, 1000.0) for _ in range(100)])
        etas = [compute_eta_size(p) for p in sample_params]
        for i in range(len(etas) - 1):
            assert etas[i] >= etas[i + 1], f"Monotonicity violated: eta({sample_params[i]})={etas[i]} < eta({sample_params[i+1]})={etas[i+1]}"

    def test_token_frugality_exhaustive_spectrum(self):
        """Test eta_token against zero, microscopic, exact, and bloat token consumption."""
        baseline = 2048
        # Ultra fast (<= 1365 tokens) hits 1.50 cap
        assert compute_eta_token(100, baseline) == 1.50
        assert compute_eta_token(500, baseline) == 1.50
        assert compute_eta_token(1365, baseline) == 1.50

        # Exact baseline
        assert compute_eta_token(2048, baseline) == 1.00

        # Bloated tokens (>= 4096 tokens) hits 0.50 floor
        assert compute_eta_token(4096, baseline) == 0.50
        assert compute_eta_token(10000, baseline) == 0.50
        assert compute_eta_token(500000, baseline) == 0.50

        # Negative and zero handling
        assert compute_eta_token(0, baseline) == 1.50
        assert compute_eta_token(-100, baseline) == 1.50

    def test_consensus_alignment_boundaries(self):
        """Test eta_consensus boundaries and out-of-range inputs."""
        assert compute_eta_consensus(1.0) == 1.00
        assert compute_eta_consensus(0.75) == 0.875
        assert compute_eta_consensus(0.50) == 0.75
        assert compute_eta_consensus(0.0) == 0.50

        # Out-of-bounds inputs clamped safely
        assert compute_eta_consensus(-5.0) == 0.50
        assert compute_eta_consensus(5.0) == 1.00

    def test_compute_latency_boundaries(self):
        """Test eta_compute boundaries across 0ms to 10,000ms."""
        # 0ms: 100/30 = 3.333 -> clamped to 1.30
        assert compute_eta_compute(0.0) == 1.30
        # 46.92ms: 100 / 76.92 = 1.300
        assert compute_eta_compute(46.92) == 1.30
        # 70ms: 100 / 100 = 1.000
        assert compute_eta_compute(70.0) == 1.00
        # 112.85ms: 100 / 142.85 = 0.700
        assert compute_eta_compute(112.85) == 0.70
        # High latency (> 113ms) clamped to 0.70
        assert compute_eta_compute(500.0) == 0.70
        assert compute_eta_compute(10000.0) == 0.70

        # Negative latency
        assert compute_eta_compute(-10.0) == 1.30

    def test_zero_mock_truth_annihilation(self):
        """Test that any truth violation completely zeroes the dynamic K-factor."""
        truth_failure_cases = [
            (False, 100.0),
            (True, 99.999),
            (False, 0.0),
            (False, 50.0),
            (True, 0.0)
        ]
        for verified, compliance in truth_failure_cases:
            eta_t = compute_eta_truth(verified, compliance)
            assert eta_t == 0.0, f"Truth factor should be 0.0 for ({verified}, {compliance}), got {eta_t}"

            k_dyn = compute_dynamic_k_factor(
                base_k=48.0,
                eta_size=2.5,
                eta_token=1.5,
                eta_consensus=1.0,
                eta_compute=1.3,
                eta_truth=eta_t
            )
            assert k_dyn == 0.0, f"K-factor must collapse to 0.0 on truth failure, got {k_dyn}"


class TestAdversarialAsymmetricKFactorsAndInvariance:
    """Tests mathematical invariance and expectation under asymmetric K-factors."""

    def test_asymmetric_k_expected_delta_zero(self):
        """
        Verify that under the true logistic outcome distribution,
        the expected ELO delta for any model is strictly zero:
        E[Delta_A] = P(A wins) * K_A * (1 - E_A) + P(A loses) * K_A * (0 - E_A)
                   = E_A * K_A * (1 - E_A) - (1 - E_A) * K_A * E_A
                   = 0.
        This holds for ANY K_A and ANY K_B independently!
        """
        test_pairs = [
            (2400.0, 2000.0, 48.0, 24.0),
            (3089.0, 2210.0, 18.0, 60.0),
            (1500.0, 1500.0, 32.0, 16.0),
            (1200.0, 2800.0, 72.0, 24.0),
        ]
        for r_a, r_b, k_a, k_b in test_pairs:
            e_a, e_b = compute_expected_outcome(r_a, r_b)

            # Win scenario: Score_A = 1.0, Score_B = 0.0
            delta_a_win = k_a * (1.0 - e_a)
            delta_b_loss = k_b * (0.0 - e_b)

            # Loss scenario: Score_A = 0.0, Score_B = 1.0
            delta_a_loss = k_a * (0.0 - e_a)
            delta_b_win = k_b * (1.0 - e_b)

            # Expected delta under logistic probability
            expected_delta_a = (e_a * delta_a_win) + (e_b * delta_a_loss)
            expected_delta_b = (e_a * delta_b_loss) + (e_b * delta_b_win)

            assert abs(expected_delta_a) < 1e-12, f"E[Delta_A] is not zero: {expected_delta_a}"
            assert abs(expected_delta_b) < 1e-12, f"E[Delta_B] is not zero: {expected_delta_b}"

    def test_asymmetric_k_bounded_variance_monte_carlo(self):
        """
        Run 1,000 simulated matches between two models with highly asymmetric K-factors (K_A=60, K_B=20).
        Verify that average ratings converge to their true theoretical equilibrium without unbounded drift.
        """
        r_a_true = 2200.0
        r_b_true = 2000.0
        k_a = 60.0
        k_b = 20.0

        r_a = r_a_true
        r_b = r_b_true

        p_a_win, _ = compute_expected_outcome(r_a_true, r_b_true)

        random.seed(42)
        history_a = []
        history_b = []

        for _ in range(1000):
            # Model with higher true capability wins with probability p_a_win
            outcome_a = 1.0 if random.random() < p_a_win else 0.0
            delta_a, delta_b, _, _ = compute_elo_delta(r_a, r_b, score_a=outcome_a, k_a=k_a, k_b=k_b)
            r_a += delta_a
            r_b += delta_b
            history_a.append(r_a)
            history_b.append(r_b)

        # Average rating over last 500 matches must remain stable and close to true ratings
        avg_a = sum(history_a[500:]) / 500.0
        avg_b = sum(history_b[500:]) / 500.0

        assert abs(avg_a - r_a_true) < 150.0, f"Model A drifted too far: avg={avg_a}, true={r_a_true}"
        assert abs(avg_b - r_b_true) < 150.0, f"Model B drifted too far: avg={avg_b}, true={r_b_true}"


class TestAdversarialSkillProgressionBounds:
    """Stress tests for specialist skill progression and boundaries."""

    def test_continuous_winning_asymptotic_approach_to_100(self):
        """Simulate 100 consecutive wins from base skill 50.0 to verify asymptotic approach to 100.0."""
        skill = 50.0
        for i in range(100):
            delta = compute_skill_delta(skill, score=1.0)
            skill += delta
            assert 50.0 <= skill <= 100.0, f"Skill escaped bounds on win {i}: {skill}"
            assert delta >= 0.0, f"Win delta cannot be negative: {delta}"

        # After 100 consecutive wins (decay factor 0.96 per win): skill = 100 - 50*(0.96)^100 ≈ 99.15
        assert 98.0 <= skill <= 100.0, f"Expected skill near 100.0, got {skill}"

    def test_continuous_losing_asymptotic_approach_to_50(self):
        """Simulate 150 consecutive losses from max skill 100.0 to verify asymptotic approach to 50.0."""
        skill = 100.0
        for i in range(150):
            delta = compute_skill_delta(skill, score=0.0)
            skill += delta
            assert 50.0 <= skill <= 100.0, f"Skill escaped bounds on loss {i}: {skill}"
            assert delta <= 0.0, f"Loss delta cannot be positive: {delta}"

        # After 150 consecutive losses (decay factor 0.97 per loss): skill = 50 + 50*(0.97)^150 ≈ 50.51
        assert 50.0 <= skill <= 51.0, f"Expected skill near 50.0, got {skill}"


class TestAdversarialHighConcurrencyAndFileIntegrity:
    """Stress tests for atomic persistence and concurrency under heavy parallel load."""

    def test_massive_concurrent_transactions_and_zero_corruption(self):
        """Execute 200 match transactions across 20 parallel threads on a single shared ledger."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        engine = CanonicalAILeaderboardEngine(ledger_path=tmp_path)
        base_data = engine.get_canonical_leaderboard(persist=True)

        num_threads = 20
        matches_per_thread = 10
        total_expected_matches = num_threads * matches_per_thread

        errors: List[str] = []
        models = [m["id"] for m in base_data["leaderboard"]]

        def worker(thread_idx: int):
            try:
                for i in range(matches_per_thread):
                    m_a, m_b = random.sample(models, 2)
                    score_a = random.choice([1.0, 0.5, 0.0])
                    payload = {
                        "match_id": f"CONCURRENT_T{thread_idx}_M{i}",
                        "match_type": "ARENA_DUEL",
                        "topic": f"Adversarial Concurrency Stress {thread_idx}-{i}",
                        "model_a_id": m_a,
                        "model_b_id": m_b,
                        "score_a": score_a,
                        "score_b": 1.0 - score_a,
                        "consumed_tokens_a": random.randint(500, 4000),
                        "consumed_tokens_b": random.randint(500, 4000),
                        "agreement_score": random.uniform(0.5, 1.0),
                        "rtt_ms": random.uniform(20.0, 200.0),
                        "truth_verified": True
                    }
                    engine.record_match_victory(payload)
            except Exception as e:
                errors.append(f"Thread {thread_idx} exception: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrency errors encountered: {errors}"

        # Verify final persisted ledger directly from disk
        with open(tmp_path, "r", encoding="utf-8") as f:
            final_data = json.load(f)

        # 1. Draft-07 Schema validation
        validate_ledger_schema(final_data)

        # 2. Total matches count matches
        assert final_data["canonical_summary"]["total_matches_recorded"] == total_expected_matches
        assert len(final_data["match_history"]) == total_expected_matches

        # 3. Ranks are contiguous 1..N
        ranks = [m["rank"] for m in final_data["leaderboard"]]
        assert ranks == list(range(1, len(final_data["leaderboard"]) + 1))

        # 4. Sorting invariant
        for i in range(len(final_data["leaderboard"]) - 1):
            cur = final_data["leaderboard"][i]
            nxt = final_data["leaderboard"][i + 1]
            assert (cur["elo"], cur["canonical_score"]) >= (nxt["elo"], nxt["canonical_score"])

        # 5. Check no temporary files leaked
        parent_dir = tmp_path.parent
        leaked_tmps = list(parent_dir.glob(f"{tmp_path.name}.tmp.*"))
        assert len(leaked_tmps) == 0, f"Found leaked temp files: {leaked_tmps}"

        if tmp_path.exists():
            tmp_path.unlink()


class TestAdversarialLongHorizonMonteCarloSimulation:
    """Long-horizon simulation verifying stability, ranking integrity, and schema compliance."""

    def test_500_match_tournament_simulation(self):
        """Execute a 500-match full tournament directly against persisted ledger and verify invariants."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            engine = CanonicalAILeaderboardEngine(ledger_path=tmp_path)
            data = engine.get_canonical_leaderboard(persist=True)
            models = [m["id"] for m in data["leaderboard"]]

            random.seed(1337)
            for i in range(500):
                m_a, m_b = random.sample(models, 2)

                # Read current state directly from disk to verify disk synchronization
                with open(tmp_path, "r", encoding="utf-8") as f:
                    current_disk = json.load(f)
                m_a_elo = [m["elo"] for m in current_disk["leaderboard"] if m["id"] == m_a][0]
                m_b_elo = [m["elo"] for m in current_disk["leaderboard"] if m["id"] == m_b][0]

                e_a, _ = compute_expected_outcome(m_a_elo, m_b_elo)
                score_a = 1.0 if random.random() < e_a else 0.0

                match_payload = {
                    "match_id": f"TOURNAMENT_MATCH_{i:04d}",
                    "match_type": random.choice(["TRI_ORCHESTRATOR_DEBATE", "BENCHMARK_CHALLENGE", "ARENA_DUEL", "PROJECT_TASK_AUDIT"]),
                    "topic": f"Round {i} Benchmark Topic",
                    "model_a_id": m_a,
                    "model_b_id": m_b,
                    "score_a": score_a,
                    "score_b": 1.0 - score_a,
                    "consumed_tokens_a": random.randint(1000, 3000),
                    "consumed_tokens_b": random.randint(1000, 3000),
                    "agreement_score": random.uniform(0.7, 1.0),
                    "rtt_ms": random.uniform(30.0, 150.0),
                    "target_skills": ["debating", "3d_ai_training_game", "lora_fine_tuning_distillation"],
                    "truth_verified": True
                }
                engine.record_match_victory(match_payload)

            # Final ledger validation directly from disk
            with open(tmp_path, "r", encoding="utf-8") as f:
                final_disk_data = json.load(f)

            validate_ledger_schema(final_disk_data)

            assert final_disk_data["canonical_summary"]["total_matches_recorded"] == 500
            assert len(final_disk_data["match_history"]) == 500

            for m in final_disk_data["leaderboard"]:
                assert 500.0 <= m["elo"] <= 5000.0
                assert 0.0 <= m["win_rate_pct"] <= 100.0
                assert 50.0 <= m["canonical_score"] <= 100.0
                assert 500.0 <= m["project_contribution_elo"] <= 5000.0
                for sk_val in m["specialist_skills"].values():
                    assert 50.0 <= sk_val <= 100.0

        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestAdversarialSchemaCorruptionRejection:
    """Tests schema rejection of corrupted and malicious payloads."""

    def test_schema_rejects_negative_elo(self):
        data = {
            "schema_version": "2.5.0",
            "last_updated_utc": "2026-08-24T19:00:00Z",
            "canonical_summary": {
                "total_models": 1,
                "top_sovereign_model_id": "test_m",
                "top_local_model_id": "test_m",
                "total_matches_recorded": 0,
                "total_harvested_lora_pairs": 0,
                "mesh_usable_vram_gb": 80.0,
                "zero_fake_data_guarantee": "100% Certified Empirical Telemetry"
            },
            "benchmark_pillars": [],
            "specialist_skills_definitions": {},
            "leaderboard": [{
                "id": "test_m",
                "name": "Test Model",
                "tier": "LOCAL",
                "archetype": "Test",
                "type": "Local",
                "hardware": "Mac",
                "elo": -100.0,  # Invalid: must be >= 500.0
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "total_duels": 0,
                "win_rate_pct": 0.0,
                "canonical_score": 50.0,
                "overall_benchmark_score": 90.0,
                "specialist_skills": {},
                "project_contribution_elo": 1000.0,
                "truth_audit_compliance_pct": 100.0,
                "rank": 1
            }],
            "match_history": [],
            "dynamic_workflow_routing": {}
        }
        with pytest.raises(Exception):
            validate_ledger_schema(data)

    def test_schema_rejects_zero_params(self):
        data = {
            "schema_version": "2.5.0",
            "last_updated_utc": "2026-08-24T19:00:00Z",
            "canonical_summary": {
                "total_models": 1,
                "top_sovereign_model_id": "test_m",
                "top_local_model_id": "test_m",
                "total_matches_recorded": 0,
                "total_harvested_lora_pairs": 0,
                "mesh_usable_vram_gb": 80.0,
                "zero_fake_data_guarantee": "100% Certified Empirical Telemetry"
            },
            "benchmark_pillars": [],
            "specialist_skills_definitions": {},
            "leaderboard": [{
                "id": "test_m",
                "name": "Test Model",
                "tier": "LOCAL",
                "archetype": "Test",
                "type": "Local",
                "hardware": "Mac",
                "params_b": 0.0, # Invalid: must be >= 0.1
                "elo": 1500.0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "total_duels": 0,
                "win_rate_pct": 0.0,
                "canonical_score": 50.0,
                "overall_benchmark_score": 90.0,
                "specialist_skills": {},
                "project_contribution_elo": 1000.0,
                "truth_audit_compliance_pct": 100.0,
                "rank": 1
            }],
            "match_history": [],
            "dynamic_workflow_routing": {}
        }
        with pytest.raises(Exception):
            validate_ledger_schema(data)
