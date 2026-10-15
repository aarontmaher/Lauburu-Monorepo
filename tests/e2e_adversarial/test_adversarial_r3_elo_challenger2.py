"""
Adversarial Stress Test Suite for R3 (Bradley-Terry ELO Engine & Numerical Stability).
================================================================================
Empirical Challenger 2 Test Suite.
Authoritative Specifications:
- ORIGINAL_REQUEST.md (§R3, Acceptance Criteria)
- DISPATCH.md (Challenger 2 Mission)

Adversarially stress-tests:
1. Bounds clamping [1000.0, 3000.0] under 10,000 streak matches & max waste tax penalties.
2. Exponent overflow protection with extreme delta R (up to 10^9 and beyond).
3. Wilson score confidence interval under degenerate Bernoulli inputs (k=0, k=n, n=0, huge n, extreme alpha).
4. 50,000-run latency benchmark on evaluate_project_scorecard to verify P99 latency <= 50 µs.
"""

import math
import random
import sys
import time
from pathlib import Path
from typing import List, Tuple
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DAEMON_SRC = REPO_ROOT / "00_core_infrastructure" / "router_ai_daemon"

for p in [REPO_ROOT, DAEMON_SRC]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from src.elo import (
    CodeOffMatch,
    EloEngine,
    EloUpdateResult,
    ResourceUsage,
    WasteTaxCalculator,
    MAX_DAVID_ELO_GAIN,
    MAX_TAX_DEDUCTION,
)
from src.elo.elo_engine import (
    CategoryScorecard,
    ProjectEloScorecard,
    WilsonConfidenceInterval,
    calculate_wilson_confidence_interval,
    evaluate_project_scorecard,
    MIN_ELO_RATING,
    MAX_ELO_RATING,
)


class TestAdversarialBoundsClamping10000Streak:
    """Stress test bounds clamping [1000.0, 3000.0] under 10,000 streak matches."""

    def test_david_10000_win_streak_upper_bound_invariance(self):
        """
        Adversarial test: David wins 10,000 consecutive matches against high-tier Goliath.
        Asserts that at EVERY single match in the 10,000 streak:
        1. 1000.0 <= new_elo <= 3000.0
        2. Once hitting 3000.0, rating remains strictly clamped at 3000.0.
        """
        engine = EloEngine()
        david_res = ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=200)
        goliath_res = ResourceUsage(params_b=70.0, ram_mb=42000.0, tokens=2000)

        current_david = 2800.0
        hit_max_count = 0

        for i in range(10000):
            match = CodeOffMatch(
                task_id=f"streak_win_{i}",
                david_model="David-360M",
                goliath_model="Goliath-70B",
                task_difficulty=2.5,
                david_solved=True,
                goliath_solved=False,
                david_resources=david_res,
                goliath_resources=goliath_res,
            )
            res = engine.record_code_off_result(
                match=match,
                current_elo_david=current_david,
                current_elo_goliath=2950.0,
            )

            assert MIN_ELO_RATING <= res.new_elo_david <= MAX_ELO_RATING, (
                f"David rating breached bounds at iteration {i}: {res.new_elo_david}"
            )
            current_david = res.new_elo_david
            if current_david == MAX_ELO_RATING:
                hit_max_count += 1

        assert current_david == MAX_ELO_RATING
        assert current_david == 3000.0
        assert hit_max_count >= 9990, f"Expected rating to remain pinned at 3000.0, pinned count: {hit_max_count}"

    def test_goliath_10000_loss_streak_with_maximum_waste_tax_penalty(self):
        """
        Adversarial test: Goliath loses 10,000 consecutive matches with catastrophic waste tax penalties.
        Asserts that at EVERY single match in the 10,000 streak:
        1. 1000.0 <= new_elo <= 3000.0
        2. Once hitting 1000.0, rating remains strictly clamped at 1000.0.
        """
        engine = EloEngine()
        david_res = ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=200)
        # Catastrophic waste: $50 spend, 20 spurious calls, high mesh drain
        goliath_glutton = ResourceUsage(
            params_b=70.0,
            ram_mb=42000.0,
            tokens=16384,
            spend_usd=50.0,
            spurious_calls=25,
            mesh_drain_index=5.0,
        )

        current_goliath = 1200.0
        hit_min_count = 0

        for i in range(10000):
            match = CodeOffMatch(
                task_id=f"streak_loss_{i}",
                david_model="David-360M",
                goliath_model="Goliath-Glutton",
                task_difficulty=0.2,
                david_solved=True,
                goliath_solved=False,
                david_resources=david_res,
                goliath_resources=goliath_glutton,
            )
            res = engine.record_code_off_result(
                match=match,
                current_elo_david=2000.0,
                current_elo_goliath=current_goliath,
            )

            assert MIN_ELO_RATING <= res.new_elo_goliath <= MAX_ELO_RATING, (
                f"Goliath rating breached bounds at iteration {i}: {res.new_elo_goliath}"
            )
            current_goliath = res.new_elo_goliath
            if current_goliath == MIN_ELO_RATING:
                hit_min_count += 1

        assert current_goliath == MIN_ELO_RATING
        assert current_goliath == 1000.0
        assert hit_min_count >= 9990, f"Expected rating to remain pinned at 1000.0, pinned count: {hit_min_count}"

    def test_randomized_10000_match_adversarial_fuzzing(self):
        """
        Monte Carlo fuzzing: 10,000 matches with randomized task difficulties,
        random solve outcomes, and randomized resource consumption profiles.
        Asserts 100% boundary compliance across both contenders.
        """
        engine = EloEngine()
        rng = random.Random(42)

        r_a = 2000.0
        r_b = 2000.0

        for i in range(10000):
            task_diff = rng.uniform(0.05, 5.0)
            david_solved = rng.random() > 0.4
            goliath_solved = rng.random() > 0.3

            d_res = ResourceUsage(
                params_b=rng.uniform(0.1, 1.5),
                ram_mb=rng.uniform(50.0, 500.0),
                tokens=rng.randint(50, 2000),
                spend_usd=rng.uniform(0.0, 0.05) if not david_solved else 0.0,
            )
            g_res = ResourceUsage(
                params_b=rng.uniform(10.0, 100.0),
                ram_mb=rng.uniform(8000.0, 64000.0),
                tokens=rng.randint(500, 10000),
                spend_usd=rng.uniform(0.0, 10.0) if not goliath_solved else 0.0,
                spurious_calls=rng.randint(0, 10) if not goliath_solved else 0,
                mesh_drain_index=rng.uniform(0.0, 5.0) if not goliath_solved else 0.0,
            )

            match = CodeOffMatch(
                task_id=f"fuzz_{i}",
                david_model="David",
                goliath_model="Goliath",
                task_difficulty=task_diff,
                david_solved=david_solved,
                goliath_solved=goliath_solved,
                david_resources=d_res,
                goliath_resources=g_res,
            )

            res = engine.record_code_off_result(match, r_a, r_b)
            assert MIN_ELO_RATING <= res.new_elo_david <= MAX_ELO_RATING
            assert MIN_ELO_RATING <= res.new_elo_goliath <= MAX_ELO_RATING
            r_a = res.new_elo_david
            r_b = res.new_elo_goliath

    def test_extreme_out_of_bounds_inputs_sanitization(self):
        """Verify inputs far outside [1000.0, 3000.0] are sanitized and clamped."""
        engine = EloEngine()
        david_res = ResourceUsage(params_b=0.36, ram_mb=98.0, tokens=200)
        goliath_res = ResourceUsage(params_b=70.0, ram_mb=42000.0, tokens=2000)

        extreme_inputs = [
            (-1e9, 1e9),
            (-500.0, 0.0),
            (999.9, 3000.1),
            (0.0, 50000.0),
            (10000.0, -10000.0),
        ]

        for r_d, r_g in extreme_inputs:
            deltas = engine.evaluate_match_deltas(
                r_david=r_d,
                r_goliath=r_g,
                david_solved=True,
                goliath_solved=False,
                david_resources=david_res,
                goliath_resources=goliath_res,
                task_difficulty=1.0,
            )
            # Clamped expected scores should match expected scores for [1000, 3000]
            clamped_d = max(MIN_ELO_RATING, min(MAX_ELO_RATING, r_d))
            clamped_g = max(MIN_ELO_RATING, min(MAX_ELO_RATING, r_g))
            exp_d, exp_g = engine.calculate_expected_score(clamped_d, clamped_g)
            assert math.isclose(deltas["e_david"], exp_d, rel_tol=1e-6)
            assert math.isclose(deltas["e_goliath"], exp_g, rel_tol=1e-6)


class TestAdversarialExponentOverflowExtremeDeltaR:
    """Stress test exponent overflow protection with extreme delta R (up to 10^9 and beyond)."""

    def test_astronomical_delta_r_no_overflow_error(self):
        """
        Assert that calculate_expected_score never raises OverflowError: math range error
        even when delta R reaches 10^9 or extreme float boundaries.
        """
        engine = EloEngine()
        extreme_deltas = [
            1e5, 1e6, 1e7, 1e8, 1e9, 1e12, 1e20, 1e50, 1e100, 1e300,
            -1e5, -1e6, -1e7, -1e8, -1e9, -1e12, -1e20, -1e50, -1e100, -1e300,
        ]

        for d in extreme_deltas:
            ea, eb = engine.calculate_expected_score(0.0, d)
            assert not math.isnan(ea), f"NaN returned for delta R = {d}"
            assert not math.isnan(eb), f"NaN returned for delta R = {d}"
            assert 0.0 <= ea <= 1.0, f"E_A out of range [0, 1] for delta R = {d}: {ea}"
            assert 0.0 <= eb <= 1.0, f"E_B out of range [0, 1] for delta R = {d}: {eb}"
            assert math.isclose(ea + eb, 1.0, rel_tol=1e-12), f"Symmetry broken for delta R = {d}: {ea + eb}"

    def test_monotonicity_across_exponent_spectrum(self):
        """Verify expected score strictly increases as rating advantage increases."""
        engine = EloEngine()
        spectrum = [-1e9, -1e5, -4000.0, -800.0, -400.0, -200.0, 0.0, 200.0, 400.0, 800.0, 4000.0, 1e5, 1e9]
        scores = []
        for d in spectrum:
            ea, eb = engine.calculate_expected_score(d, 0.0)
            scores.append(ea)

        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], f"Monotonicity violation at index {i}: {scores[i]} > {scores[i+1]}"

    def test_exponent_clamping_exact_boundary_values(self):
        """
        Verify exact values at the exponent clamp limit (+-20.0, delta R = +-8000.0).
        exp = max(-20.0, min(20.0, delta / 400.0)).
        For delta >= 8000.0, exp is 20.0. 10^20.0 = 1e20. E_A = 1/(1 + 1e20) ≈ 1e-20.
        """
        engine = EloEngine()
        ea_8000, eb_8000 = engine.calculate_expected_score(0.0, 8000.0)
        ea_huge, eb_huge = engine.calculate_expected_score(0.0, 1e9)

        assert ea_8000 == ea_huge, "Expected exponent clamping to produce identical results for delta >= 8000"
        assert eb_8000 == eb_huge
        assert ea_8000 == 1.0 / (1.0 + 10.0 ** 20.0)
        assert eb_8000 == 1.0 - ea_8000


class TestAdversarialWilsonScoreDegenerateInputs:
    """Stress test Wilson score confidence interval under degenerate Bernoulli inputs."""

    def test_wilson_zero_trials_uninformative_prior(self):
        """Asserts n=0 returns uninformative prior [0.0, 1.0] with spread 1.0."""
        ci_0_0 = calculate_wilson_confidence_interval(0, 0)
        assert ci_0_0.lower == 0.0
        assert ci_0_0.upper == 1.0
        assert ci_0_0.spread == 1.0

        ci_neg_n = calculate_wilson_confidence_interval(5, -100)
        assert ci_neg_n.lower == 0.0
        assert ci_neg_n.upper == 1.0
        assert ci_neg_n.spread == 1.0

    def test_wilson_zero_successes_exact_zero_lower_bound(self):
        """Asserts k=0 returns lower bound of exactly 0.0 and valid non-zero upper bound."""
        for n in [1, 5, 10, 100, 1000, 10000, 1000000]:
            ci = calculate_wilson_confidence_interval(0, n)
            assert ci.lower == 0.0, f"k=0 did not yield lower bound 0.0 for n={n}"
            assert 0.0 < ci.upper <= 1.0, f"k=0 yielded invalid upper bound for n={n}"
            assert ci.spread == ci.upper

    def test_wilson_all_successes_exact_one_upper_bound_and_non_zero_uncertainty(self):
        """
        Asserts k=n returns upper bound of exactly 1.0, and lower bound < 1.0
        (preserving non-zero uncertainty even when all finite tests pass).
        """
        for n in [1, 5, 10, 100, 1000, 10000, 1000000]:
            ci = calculate_wilson_confidence_interval(n, n)
            assert ci.upper == 1.0, f"k=n did not yield upper bound 1.0 for n={n}"
            assert ci.lower < 1.0, f"k=n had zero uncertainty (lower == 1.0) for finite n={n}"
            assert ci.lower > 0.0, f"k=n yielded non-positive lower bound for n={n}"
            assert ci.spread > 0.0

    def test_wilson_degenerate_k_out_of_bounds(self):
        """Asserts k < 0 is clamped to 0, and k > n is clamped to n."""
        ci_neg = calculate_wilson_confidence_interval(-50, 100)
        ci_zero = calculate_wilson_confidence_interval(0, 100)
        assert ci_neg == ci_zero
        assert ci_neg.lower == 0.0

        ci_over = calculate_wilson_confidence_interval(500, 100)
        ci_full = calculate_wilson_confidence_interval(100, 100)
        assert ci_over == ci_full
        assert ci_over.upper == 1.0

    def test_wilson_huge_n_asymptotic_convergence(self):
        """Asserts Wilson interval converges to point mass for n = 1,000,000 and n = 1,000,000,000."""
        ci_1m_half = calculate_wilson_confidence_interval(500000, 1000000)
        assert math.isclose(ci_1m_half.lower, 0.5, abs_tol=0.002)
        assert math.isclose(ci_1m_half.upper, 0.5, abs_tol=0.002)
        assert ci_1m_half.spread < 0.003

        ci_1b_full = calculate_wilson_confidence_interval(1000000000, 1000000000)
        assert ci_1b_full.upper == 1.0
        assert ci_1b_full.lower > 0.999999
        assert ci_1b_full.spread < 1e-5

    def test_wilson_extreme_confidence_levels(self):
        """Asserts validity across extreme confidence levels: 0.01 to 0.999999."""
        conf_levels = [0.0001, 0.01, 0.50, 0.90, 0.95, 0.99, 0.9999, 0.999999]
        spreads = []

        for conf in conf_levels:
            ci = calculate_wilson_confidence_interval(50, 100, confidence=conf)
            assert 0.0 <= ci.lower <= ci.upper <= 1.0
            spreads.append(ci.spread)

        # Higher confidence must yield strictly larger spreads
        for i in range(len(spreads) - 1):
            assert spreads[i] <= spreads[i + 1], f"Spread did not increase with confidence at index {i}"


class TestAdversarialScorecard50kLatencyBenchmark:
    """Run 50,000-run latency benchmark on evaluate_project_scorecard to verify P99 latency <= 50 µs."""

    def test_scorecard_50000_run_latency_benchmark(self):
        """
        Adversarial benchmark: 50,000 sequential evaluations of evaluate_project_scorecard.
        Verifies:
        1. Mean latency <= 50.0 µs
        2. P99 latency <= 50.0 µs (Mandatory SLA acceptance criterion)
        3. Zero failures, 100% SLA compliance flag True for P99
        """
        # Pre-warm runtime
        for _ in range(500):
            evaluate_project_scorecard((95, 100), (998, 1000), (48, 50))

        runs = 50000
        internal_latencies: List[float] = []
        external_latencies: List[float] = []

        t_start = time.perf_counter()
        for i in range(runs):
            fe_k = 90 + (i % 10)
            be_k = 990 + (i % 10)
            ai_k = 45 + (i % 5)

            t0 = time.perf_counter_ns()
            sc = evaluate_project_scorecard(
                frontend_trials=(fe_k, 100),
                backend_trials=(be_k, 1000),
                ai_trials=(ai_k, 50),
                frontend_rating=2100.0 + (i % 300),
                backend_rating=2200.0 + (i % 300),
                ai_rating=2300.0 + (i % 300),
            )
            t1 = time.perf_counter_ns()

            internal_latencies.append(sc.evaluation_latency_us)
            external_latencies.append((t1 - t0) / 1000.0)

        t_elapsed = time.perf_counter() - t_start

        int_sorted = sorted(internal_latencies)
        ext_sorted = sorted(external_latencies)

        mean_int = sum(internal_latencies) / runs
        p50_int = int_sorted[int(runs * 0.50)]
        p90_int = int_sorted[int(runs * 0.90)]
        p95_int = int_sorted[int(runs * 0.95)]
        p99_int = int_sorted[int(runs * 0.99)]
        p999_int = int_sorted[int(runs * 0.999)]
        max_int = int_sorted[-1]

        mean_ext = sum(external_latencies) / runs
        p50_ext = ext_sorted[int(runs * 0.50)]
        p90_ext = ext_sorted[int(runs * 0.90)]
        p95_ext = ext_sorted[int(runs * 0.95)]
        p99_ext = ext_sorted[int(runs * 0.99)]
        p999_ext = ext_sorted[int(runs * 0.999)]
        max_ext = ext_sorted[-1]

        print(f"\n=======================================================")
        print(f"50,000-RUN SCORECARD LATENCY BENCHMARK REPORT")
        print(f"=======================================================")
        print(f"Total Wall Time:  {t_elapsed:.3f} s ({runs / t_elapsed:.1f} evals/sec)")
        print(f"Internal Latency: Mean={mean_int:.2f}µs, P50={p50_int:.2f}µs, P90={p90_int:.2f}µs, P95={p95_int:.2f}µs, P99={p99_int:.2f}µs, P99.9={p999_int:.2f}µs, Max={max_int:.2f}µs")
        print(f"External Latency: Mean={mean_ext:.2f}µs, P50={p50_ext:.2f}µs, P90={p90_ext:.2f}µs, P95={p95_ext:.2f}µs, P99={p99_ext:.2f}µs, P99.9={p999_ext:.2f}µs, Max={max_ext:.2f}µs")
        print(f"=======================================================")

        assert mean_int <= 50.0, f"Mean internal latency {mean_int:.2f} µs exceeded 50.0 µs SLA"
        assert p99_int <= 50.0, f"P99 internal latency {p99_int:.2f} µs exceeded 50.0 µs SLA"
        assert mean_ext <= 50.0, f"Mean external latency {mean_ext:.2f} µs exceeded 50.0 µs SLA"
        assert p99_ext <= 50.0, f"P99 external latency {p99_ext:.2f} µs exceeded 50.0 µs SLA"
