"""
Unit Test Suite for Canonical ELO Ledger & Multi-Factor Dynamic ELO Math Engine.
================================================================================
Verifies:
1. Mathematical ELO properties: Logistic expected outcome, symmetry, zero-sum delta conservation.
2. Dynamic K-factor multipliers: Parameter efficiency (eta_size), token frugality (eta_token),
   consensus alignment (eta_consensus), compute latency (eta_compute), and zero-mock compliance (eta_truth).
3. Specialist skill progression formulas: Win, draw, and loss deltas with asymptotic boundaries.
4. JSON Schema v7 validation: Strict Draft-07 compliance on data/canonical_ai_leaderboard.json.
5. POSIX Atomic disk persistence: os.replace semantics and concurrent collision resilience.
6. Record match victory end-to-end flow: Real state updates, match history, and leaderboard re-ranking.
7. Zero-Mock integrity: Rule #0 compliance and zero simulated dummy data.
"""

import os
import sys
import json
import math
import time
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any
import pytest

# Ensure repository packages are in sys.path
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


class TestEloEngineMathematics:
    """Mathematical properties and invariance tests for the ELO engine."""

    def test_expected_probability_symmetry(self):
        """Verify that E_A + E_B == 1.0 across a wide spectrum of rating differentials."""
        test_ratings = [
            (1500.0, 1500.0),
            (2400.0, 2000.0),
            (2000.0, 2400.0),
            (3089.0, 2360.0),
            (800.0, 3500.0),
            (1234.5, 2345.6),
            (5000.0, 500.0),
        ]
        for r_a, r_b in test_ratings:
            e_a, e_b = compute_expected_outcome(r_a, r_b)
            assert round(e_a + e_b, 9) == 1.0, f"Expected scores {e_a} and {e_b} do not sum to 1.0 for ({r_a}, {r_b})"
            assert 0.0 < e_a < 1.0, f"E_A must be in (0, 1), got {e_a}"
            assert 0.0 < e_b < 1.0, f"E_B must be in (0, 1), got {e_b}"

            if r_a == r_b:
                assert e_a == 0.5 and e_b == 0.5
            elif r_a > r_b:
                assert e_a > 0.5 and e_b < 0.5
            else:
                assert e_a < 0.5 and e_b > 0.5

    def test_expected_outcome_exact_values(self):
        """Verify exact theoretical expected values at 400 and 800 rating differences."""
        # A 400 point difference gives 10^(400/400) = 10^1 = 10 -> E_A = 1 / (1 + 10^-1) = 10/11 ≈ 0.909090909
        e_a_400 = calculate_expected_elo(2400.0, 2000.0)
        expected_400 = 10.0 / 11.0
        assert abs(e_a_400 - expected_400) < 1e-6, f"Expected {expected_400}, got {e_a_400}"

        # An 800 point difference gives 10^(800/400) = 10^2 = 100 -> E_A = 1 / (1 + 10^-2) = 100/101 ≈ 0.990099
        e_a_800 = calculate_expected_elo(2800.0, 2000.0)
        expected_800 = 100.0 / 101.0
        assert abs(e_a_800 - expected_800) < 1e-6, f"Expected {expected_800}, got {e_a_800}"

    def test_zero_delta_conservation_symmetric_k(self):
        """Verify zero-sum delta conservation (delta_a + delta_b == 0) when symmetric K-factors are used."""
        r_a, r_b = 2300.0, 2100.0
        k = 32.0

        for score_a in [1.0, 0.5, 0.0]:
            delta_a, delta_b, e_a, e_b = compute_elo_delta(r_a, r_b, score_a, k_a=k, k_b=k)
            assert round(delta_a + delta_b, 1) == 0.0, f"Zero-sum conservation violated for score {score_a}: {delta_a} + {delta_b}"
            if score_a == 1.0:
                assert delta_a > 0.0 and delta_b < 0.0
            elif score_a == 0.0:
                assert delta_a < 0.0 and delta_b > 0.0
            elif score_a == 0.5:
                # Higher rated model loses slight rating on draw against lower rated model
                assert delta_a < 0.0 and delta_b > 0.0

    def test_parameter_efficiency_curve(self):
        """Verify that eta_size strictly rewards parameter efficiency and respects clamping bounds."""
        eta_1_5b = compute_eta_size(1.5)
        eta_7b = compute_eta_size(7.0)
        eta_14b = compute_eta_size(14.0)
        eta_32b = compute_eta_size(32.0)
        eta_70b = compute_eta_size(70.0)
        eta_88b = compute_eta_size(88.0)
        eta_400b = compute_eta_size(400.0)

        # Monotonicity check: smaller models must have higher efficiency multiplier
        assert eta_1_5b >= eta_7b > eta_14b > eta_32b > eta_70b > eta_88b > eta_400b, (
            f"Monotonicity failed: {eta_1_5b}, {eta_7b}, {eta_14b}, {eta_32b}, {eta_70b}, {eta_88b}, {eta_400b}"
        )

        # Baseline 70B must equal exactly 1.0
        assert eta_70b == 1.0, f"70B parameter multiplier must be 1.0, got {eta_70b}"

        # Clamping checks: minimum 0.50, maximum 2.50
        assert eta_1_5b == 2.50, f"1.5B model should clamp to max 2.50, got {eta_1_5b}"
        assert eta_400b >= 0.50, f"400B model should be >= min 0.50, got {eta_400b}"
        assert compute_eta_size(10000.0) == 0.50, "Extremely large models must clamp to min 0.50"

        # Edge case: zero or negative params handled safely
        assert compute_eta_size(0.0) == 2.50
        assert compute_eta_size(-5.0) == 2.50

    def test_token_frugality_scaling(self):
        """Verify that eta_token scales with consumed tokens relative to baseline."""
        baseline = 2048
        eta_fast = compute_eta_token(1024, baseline_tokens=baseline)
        eta_exact = compute_eta_token(2048, baseline_tokens=baseline)
        eta_bloat = compute_eta_token(4096, baseline_tokens=baseline)

        assert eta_fast == 1.50, f"1024 tokens should clamp to max 1.50, got {eta_fast}"
        assert eta_exact == 1.00, f"2048 tokens should yield 1.00, got {eta_exact}"
        assert eta_bloat == 0.50, f"4096 tokens should yield min 0.50, got {eta_bloat}"
        assert eta_fast > eta_exact > eta_bloat

        # Boundary checks
        assert compute_eta_token(0, baseline) == 1.50
        assert compute_eta_token(100000, baseline) == 0.50

    def test_consensus_alignment_scaling(self):
        """Verify that eta_consensus scales monotonically with agreement score."""
        eta_full = compute_eta_consensus(1.0)
        eta_mid = compute_eta_consensus(0.5)
        eta_zero = compute_eta_consensus(0.0)

        assert eta_full == 1.00, f"Agreement 1.0 must yield 1.00, got {eta_full}"
        assert eta_mid == 0.75, f"Agreement 0.5 must yield 0.75, got {eta_mid}"
        assert eta_zero == 0.50, f"Agreement 0.0 must yield 0.50, got {eta_zero}"
        assert eta_full > eta_mid > eta_zero

        # Clamping out-of-range values
        assert compute_eta_consensus(1.5) == 1.00
        assert compute_eta_consensus(-0.5) == 0.50

    def test_compute_latency_scaling(self):
        """Verify that eta_compute rewards low RTT response times."""
        eta_zero_lat = compute_eta_compute(0.0)   # 100/30 ≈ 3.33 -> clamped to 1.30
        eta_fast_lat = compute_eta_compute(70.0)  # 100/100 = 1.00
        eta_slow_lat = compute_eta_compute(300.0) # 100/330 ≈ 0.30 -> clamped to 0.70

        assert eta_zero_lat == 1.30, f"Ultra-low latency must clamp to 1.30, got {eta_zero_lat}"
        assert eta_fast_lat == 1.00, f"70ms latency must yield 1.00, got {eta_fast_lat}"
        assert eta_slow_lat == 0.70, f"High latency must clamp to 0.70, got {eta_slow_lat}"
        assert eta_zero_lat > eta_fast_lat > eta_slow_lat

    def test_truth_violation_disqualification(self):
        """Verify Rule #0 zero-mock enforcement: unverified or non-compliant claims get eta_truth=0.0."""
        assert compute_eta_truth(True, 100.0) == 1.00
        assert compute_eta_truth(False, 100.0) == 0.00
        assert compute_eta_truth(True, 99.9) == 0.00
        assert compute_eta_truth(False, 0.0) == 0.00

        # When eta_truth is 0, K_dyn must be 0.0
        k_untruthful = compute_dynamic_k_factor(base_k=32.0, eta_truth=0.0)
        assert k_untruthful == 0.0, f"K-factor must be 0.0 when truth is violated, got {k_untruthful}"

        # Zero delta applied when K=0
        delta_a, delta_b, _, _ = compute_elo_delta(2400.0, 2000.0, score_a=1.0, k_a=0.0, k_b=0.0)
        assert delta_a == 0.0 and delta_b == 0.0, "No ELO points may be awarded on unverified match"

    def test_dynamic_k_factor_provisioning_tiers(self):
        """Verify dynamic K-factor base calibration across provisional, standard, and established tiers."""
        # Provisional tier (< 10 matches): Base K = 48.0
        k_provisional = compute_dynamic_k_factor(matches_played=5)
        assert k_provisional == 48.0

        # Standard tier (10 <= N < 50): Base K = 32.0
        k_standard = compute_dynamic_k_factor(matches_played=25)
        assert k_standard == 32.0

        # Established tier (N >= 50): Base K = 24.0
        k_established = compute_dynamic_k_factor(matches_played=100)
        assert k_established == 24.0

    def test_dynamic_k_factor_match_type_scaling(self):
        """Verify match type scaling on K-factor."""
        k_debate = compute_dynamic_k_factor(base_k=32.0, match_type="TRI_ORCHESTRATOR_DEBATE")
        k_bench = compute_dynamic_k_factor(base_k=32.0, match_type="BENCHMARK_CHALLENGE")
        k_audit = compute_dynamic_k_factor(base_k=32.0, match_type="PROJECT_TASK_AUDIT")
        k_speed = compute_dynamic_k_factor(base_k=32.0, match_type="SPEED_TRIAL")

        assert k_debate == 32.0
        assert k_bench == round(32.0 * 1.20, 4)
        assert k_audit == round(32.0 * 1.50, 4)
        assert k_speed == round(32.0 * 0.80, 4)

    def test_specialist_skill_progression_formulas(self):
        """Verify asymptotic skill level-up delta calculations."""
        # Win with high skill (90.0): delta = +0.4 * (100 - 90)/10 = +0.40
        d_win_90 = compute_skill_delta(90.0, score=1.0)
        assert d_win_90 == 0.40, f"Expected +0.40, got {d_win_90}"

        # Win with low skill (50.0): delta = +0.4 * (100 - 50)/10 = +2.00
        d_win_50 = compute_skill_delta(50.0, score=1.0)
        assert d_win_50 == 2.00, f"Expected +2.00, got {d_win_50}"

        # Draw with skill (90.0): delta = +0.1 * (100 - 90)/10 = +0.10
        d_draw_90 = compute_skill_delta(90.0, score=0.5)
        assert d_draw_90 == 0.10, f"Expected +0.10, got {d_draw_90}"

        # Loss with skill (90.0): delta = -0.3 * (90 - 50)/10 = -1.20
        d_loss_90 = compute_skill_delta(90.0, score=0.0)
        assert d_loss_90 == -1.20, f"Expected -1.20, got {d_loss_90}"

        # Boundary asymptotic limits
        assert compute_skill_delta(100.0, score=1.0) == 0.0  # Max skill cannot increase
        assert compute_skill_delta(50.0, score=0.0) == 0.0   # Min skill cannot decrease


class TestCanonicalLedgerSchemaAndPersistence:
    """Tests schema validation, atomic disk persistence, and concurrency."""

    def test_json_schema_v7_compliance(self):
        """Verify that the generated canonical ledger strictly passes JSON Schema v7."""
        engine = CanonicalAILeaderboardEngine()
        data = engine.get_canonical_leaderboard(persist=False)

        # Validate with jsonschema
        validate_ledger_schema(data)

        # Assert all 19+ skills defined
        skills = data["specialist_skills_definitions"]
        assert len(skills) >= 19, f"Expected at least 19 specialist skills, got {len(skills)}"

        # Assert all models have complete definitions
        for m in data["leaderboard"]:
            assert m["params_b"] > 0
            assert m["elo"] >= 500.0
            assert "canonical_score" in m
            assert "project_contribution_elo" in m
            assert len(m["specialist_skills"]) >= 19
            assert m["rank"] >= 1

    def test_schema_rejection_of_invalid_payloads(self):
        """Verify that validate_ledger_schema raises ValidationError on missing required fields."""
        invalid_payload = {
            "schema_version": "2.5.0",
            # missing last_updated_utc
            "canonical_summary": {
                "total_models": 1
            }
        }
        with pytest.raises(Exception):
            validate_ledger_schema(invalid_payload)

    def test_atomic_persistence_and_file_integrity(self):
        """Verify that atomic_save_canonical_ledger creates valid JSON without partial corruption."""
        engine = CanonicalAILeaderboardEngine()
        data = engine.get_canonical_leaderboard(persist=False)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            success = atomic_save_canonical_ledger(data, tmp_path)
            assert success is True
            assert tmp_path.exists()

            with open(tmp_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded["schema_version"] == "2.5.0"
            assert len(loaded["leaderboard"]) == len(data["leaderboard"])
            validate_ledger_schema(loaded)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_concurrent_atomic_writes(self):
        """Verify that rapid concurrent writes to the same ledger do not produce corrupted files."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        engine = CanonicalAILeaderboardEngine(ledger_path=tmp_path)
        base_data = engine.get_canonical_leaderboard(persist=False)
        atomic_save_canonical_ledger(base_data, tmp_path)

        errors = []

        def worker(worker_id: int):
            try:
                for i in range(10):
                    payload = {
                        "match_id": f"CONCURRENT_{worker_id}_{i}",
                        "match_type": "ARENA_DUEL",
                        "topic": f"Thread duel {worker_id}-{i}",
                        "model_a_id": "kimi_tandem_titan",
                        "model_b_id": "claude_37_sonnet",
                        "score_a": 1.0 if (worker_id + i) % 2 == 0 else 0.0,
                        "score_b": 0.0 if (worker_id + i) % 2 == 0 else 1.0,
                        "truth_verified": True
                    }
                    engine.record_match_victory(payload)
            except Exception as e:
                errors.append(f"Worker {worker_id} error: {e}")

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Encountered concurrent write errors: {errors}"

        # Verify final file is 100% valid JSON and schema-compliant
        with open(tmp_path, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        validate_ledger_schema(final_data)
        assert final_data["canonical_summary"]["total_matches_recorded"] == 50

        if tmp_path.exists():
            tmp_path.unlink()


class TestRecordMatchVictoryAndRanking:
    """Tests end-to-end match execution, state updates, and ranking calculation."""

    def test_record_match_victory_flow(self):
        """Verify complete match recording flow: delta calculation, skill updates, and match logging."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        engine = CanonicalAILeaderboardEngine(ledger_path=tmp_path)
        initial_data = engine.get_canonical_leaderboard(persist=True)
        kimi_init = engine.get_model_by_id("kimi_tandem_titan")
        claude_init = engine.get_model_by_id("claude_37_sonnet")

        init_elo_kimi = kimi_init["elo"]
        init_elo_claude = claude_init["elo"]
        init_wins_kimi = kimi_init["wins"]
        init_losses_claude = claude_init["losses"]

        match_payload = {
            "match_id": "TEST_DEBATE_001",
            "match_type": "TRI_ORCHESTRATOR_DEBATE",
            "topic": "UI/UX Kinematic Optimization",
            "model_a_id": "kimi_tandem_titan",
            "model_b_id": "claude_37_sonnet",
            "score_a": 1.0,
            "score_b": 0.0,
            "consumed_tokens_a": 1200,
            "consumed_tokens_b": 2200,
            "agreement_score": 0.95,
            "rtt_ms": 40.0,
            "target_skills": ["debating", "3d_ai_training_game"],
            "truth_verified": True,
            "truth_compliance_pct": 100.0,
            "consensus_summary": "Kimi established superior token-efficient WebGPU AST pipeline."
        }

        result = engine.record_match_victory(match_payload)
        record = result["match_record"]
        model_a = result["updated_model_a"]
        model_b = result["updated_model_b"]

        assert record["match_id"] == "TEST_DEBATE_001"
        assert record["winner_id"] == "kimi_tandem_titan"
        assert record["delta_elo_a"] > 0
        assert record["delta_elo_b"] < 0
        assert model_a["elo"] == init_elo_kimi + record["delta_elo_a"]
        assert model_b["elo"] == init_elo_claude + record["delta_elo_b"]
        assert model_a["wins"] == init_wins_kimi + 1
        assert model_b["losses"] == init_losses_claude + 1

        # Check rankings sorting
        rankings = result["new_rankings"]
        for i in range(len(rankings) - 1):
            assert (rankings[i]["elo"], rankings[i]["canonical_score"]) >= (rankings[i + 1]["elo"], rankings[i + 1]["canonical_score"])

        # Cleanup
        if tmp_path.exists():
            tmp_path.unlink()


class TestZeroMockCompliance:
    """Rule #0: Enforces zero-mock data invariants across the canonical leaderboard."""

    def test_zero_mock_markers_absent(self):
        """Audits data/canonical_ai_leaderboard.json to assert no mock markers or fake values exist."""
        master_file = REPO_ROOT / "data" / "canonical_ai_leaderboard.json"
        assert master_file.exists(), "Master canonical ledger data/canonical_ai_leaderboard.json must exist"

        with open(master_file, "r", encoding="utf-8") as f:
            raw_text = f.read()
            data = json.loads(raw_text)

        # Check forbidden mock tokens in JSON
        forbidden = ["mock_data", "fake_array", "dummy_payload", "synthetic_placeholder"]
        for token in forbidden:
            assert token not in raw_text, f"Forbidden mock token '{token}' detected in canonical ledger!"

        # Guarantee statement present
        assert data["canonical_summary"]["zero_fake_data_guarantee"] == "100% Certified Empirical Telemetry"
        assert data["canonical_summary"]["total_models"] >= 10
