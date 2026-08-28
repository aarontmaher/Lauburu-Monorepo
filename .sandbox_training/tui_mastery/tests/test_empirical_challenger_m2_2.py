#!/usr/bin/env python3
"""Empirical Challenger Test Suite for Milestone 2.

Examines and validates:
1. Tournament runner execution and benchmark_results.json schema/values.
2. Mathematical correctness of S_composite, NPU bonus hours, and Refusal Ablation math.
3. JSONL validity and schema compliance for:
   - tournament_events.jsonl
   - referee_verdicts.jsonl
   - lora_tui_distillation.jsonl
   - dpo_tui_preferences.jsonl
4. Boundary condition, edge case, and fuzz stress-testing of scoring formulas and referee components.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

SANDBOX_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SANDBOX_DIR.parent.parent
sys.path.insert(0, str(SANDBOX_DIR))

from referee.scoring_matrix import (
    ScoringMatrix,
    ScoreBreakdown,
    calculate_composite_score,
    calculate_npu_bonus_hours,
    calculate_refusal_ablation,
    DEFAULT_SCORING_WEIGHTS,
    CHAOS_SURGE_WEIGHTS,
)
from referee.chaos_injector import ChaosInjector, ChaosEvent
from referee.abliterated_referee import AbliteratedReferee


class TestBenchmarkResultsAndExecution(unittest.TestCase):
    """Validate benchmark results file and execution integrity."""

    def setUp(self):
        self.results_path = SANDBOX_DIR / "benchmarks" / "benchmark_results.json"
        self.assertTrue(self.results_path.exists(), "benchmark_results.json must exist")
        with open(self.results_path, "r", encoding="utf-8") as f:
            self.results = json.load(f)

    def test_benchmark_results_schema(self):
        """Verify schema compliance with PROJECT.md Interface Contract 2."""
        self.assertIn("tournament_id", self.results)
        self.assertIn("timestamp", self.results)
        self.assertEqual(self.results.get("integrity_mode"), "benchmark")
        self.assertEqual(self.results.get("referee"), "Abliterated Llama 70B (Devil's Advocate)")
        self.assertIn("frameworks", self.results)
        self.assertIn("winner", self.results)

        # Check framework entries
        expected_frameworks = ["python_textual", "go_bubbletea", "rust_ratatui"]
        for fw in expected_frameworks:
            self.assertIn(fw, self.results["frameworks"], f"Missing framework: {fw}")
            fw_data = self.results["frameworks"][fw]
            for key in [
                "memory_score",
                "latency_score",
                "robustness_score",
                "code_quality_score",
                "composite_score",
                "status",
                "bonus_npu_hours",
            ]:
                self.assertIn(key, fw_data, f"Missing key {key} in {fw}")
                if "score" in key or "hours" in key:
                    self.assertIsInstance(fw_data[key], (int, float), f"{key} must be numeric in {fw}")
                    self.assertGreaterEqual(fw_data[key], 0.0)
                    self.assertLessEqual(fw_data[key], 100.0)

        # Check winner entry
        winner = self.results["winner"]
        self.assertIn(winner["framework"], expected_frameworks)
        self.assertEqual(winner["specialist"], f"polyglot-{winner['framework'].replace('_', '-')}-specialist")
        self.assertIsInstance(winner["composite_score"], (int, float))
        self.assertIsInstance(winner["bonus_npu_hours"], (int, float))
        self.assertEqual(winner["promotion_target"], f"01_apps/canonical_tui_prototypes/{winner['framework']}")

    def test_winner_selection_mathematical_supremacy(self):
        """Ensure winner truly has the highest composite score."""
        frameworks = self.results["frameworks"]
        winner = self.results["winner"]
        highest_composite = max(fw_data["composite_score"] for fw_data in frameworks.values())
        self.assertEqual(winner["composite_score"], highest_composite)
        self.assertEqual(frameworks[winner["framework"]]["composite_score"], highest_composite)


class TestMathematicalCorrectness(unittest.TestCase):
    """Validate mathematical formulas, edge conditions, and invariants."""

    def test_composite_score_formula_exact(self):
        """Verify S_composite = 0.25*mem + 0.25*lat + 0.30*rob + 0.20*qual."""
        weights = DEFAULT_SCORING_WEIGHTS
        mem, lat, rob, qual = 80.0, 90.0, 100.0, 95.0
        expected = (0.25 * 80.0) + (0.25 * 90.0) + (0.30 * 100.0) + (0.20 * 95.0)
        # 20.0 + 22.5 + 30.0 + 19.0 = 91.5
        calculated = calculate_composite_score(mem, lat, rob, qual, weights)
        self.assertAlmostEqual(calculated, expected, places=4)
        self.assertEqual(calculated, 91.5)

    def test_composite_score_bounds_clamping(self):
        """Verify composite score clamping for out-of-bound inputs."""
        # Extreme negative inputs
        self.assertEqual(calculate_composite_score(-50.0, -100.0, -10.0, -20.0), 0.0)
        # Extreme positive inputs
        self.assertEqual(calculate_composite_score(150.0, 200.0, 999.0, 120.0), 100.0)
        # All zeros
        self.assertEqual(calculate_composite_score(0.0, 0.0, 0.0, 0.0), 0.0)
        # All 100s
        self.assertEqual(calculate_composite_score(100.0, 100.0, 100.0, 100.0), 100.0)

    def test_weight_auto_normalization(self):
        """Verify weights that do not sum to 1.0 are automatically normalized."""
        unnormalized_weights = {
            "memory_efficiency": 1.0,
            "latency_throughput": 1.0,
            "attack_robustness": 1.0,
            "code_quality_and_truth": 1.0,
        }
        # Equal weights 0.25 each -> result for (100, 50, 0, 50) = 50.0
        calculated = calculate_composite_score(100.0, 50.0, 0.0, 50.0, unnormalized_weights)
        self.assertEqual(calculated, 50.0)

    def test_npu_bonus_hours_formula_exact(self):
        """Verify Bonus NPU Hours = min(50.0, 25.0 + 0.5 * max(0.0, S_composite - 70.0))."""
        # Case 1: Below threshold (<= 70.0) -> Base 25.0 hours
        self.assertEqual(calculate_npu_bonus_hours(0.0), 25.0)
        self.assertEqual(calculate_npu_bonus_hours(50.0), 25.0)
        self.assertEqual(calculate_npu_bonus_hours(70.0), 25.0)

        # Case 2: Above threshold
        # S = 80.0 -> 25.0 + 0.5 * 10 = 30.0
        self.assertEqual(calculate_npu_bonus_hours(80.0), 30.0)
        # S = 90.0 -> 25.0 + 0.5 * 20 = 35.0
        self.assertEqual(calculate_npu_bonus_hours(90.0), 35.0)
        # S = 100.0 -> 25.0 + 0.5 * 30 = 40.0
        self.assertEqual(calculate_npu_bonus_hours(100.0), 40.0)

        # Case 3: Cap at max_hours (50.0)
        self.assertEqual(calculate_npu_bonus_hours(120.0), 50.0)
        self.assertEqual(calculate_npu_bonus_hours(200.0), 50.0)

    def test_panic_disqualification_invariant(self):
        """Invariant: Any panic forces S_rob = 0.0 and status = DISQUALIFIED_PANIC."""
        matrix = ScoringMatrix()
        # Even with perfect latency and memory, 1 panic drops robustness to 0
        breakdown = matrix.evaluate_candidate(
            framework="test_panic_fw",
            peak_rss_mb=1.0,
            avg_latency_ms=1.0,
            scenarios_survived=5,
            total_scenarios=5,
            panics_count=1,
            lint_issues=0,
            zero_mock_certified=True,
        )
        self.assertEqual(breakdown.robustness_score, 0.0)
        self.assertEqual(breakdown.status, "DISQUALIFIED_PANIC")
        # Composite should reflect 0.30 * 0.0
        self.assertLess(breakdown.composite_score, 80.0)

    def test_refusal_ablation_algebra(self):
        """Verify directional refusal ablation: h_clean = h - (h . r) * r."""
        # 1. Arbitrary non-orthogonal vector and unit refusal vector
        h = [3.0, -4.0, 5.0]
        # r normalized
        r_raw = [1.0, 2.0, 2.0]
        norm_r = math.sqrt(sum(x * x for x in r_raw))  # 3.0
        r = [x / norm_r for x in r_raw]  # [1/3, 2/3, 2/3]

        h_clean = calculate_refusal_ablation(h, r)

        # Dot product with r must be 0.0
        dot_clean = sum(a * b for a, b in zip(h_clean, r))
        self.assertAlmostEqual(dot_clean, 0.0, places=7)

        # Idempotence: ablaing h_clean again should yield h_clean
        h_clean_2 = calculate_refusal_ablation(h_clean, r)
        for val1, val2 in zip(h_clean, h_clean_2):
            self.assertAlmostEqual(val1, val2, places=7)


class TestJsonlIntegrityAndSchema(unittest.TestCase):
    """Validate JSONL validity and schema conformance for all 4 log streams."""

    def setUp(self):
        self.log_dir = SANDBOX_DIR / "logs"
        self.tournament_events_p = self.log_dir / "tournament_events.jsonl"
        self.referee_verdicts_p = self.log_dir / "referee_verdicts.jsonl"
        self.lora_distillation_p = self.log_dir / "lora_tui_distillation.jsonl"
        self.dpo_preferences_p = self.log_dir / "dpo_tui_preferences.jsonl"

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        self.assertTrue(path.exists(), f"Log file missing: {path}")
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    records.append(json.loads(clean_line))
                except json.JSONDecodeError as exc:
                    self.fail(f"Invalid JSON at {path.name}:{idx}: {exc}")
        self.assertGreater(len(records), 0, f"Log file empty: {path}")
        return records

    def test_tournament_events_schema(self):
        """Validate tournament_events.jsonl."""
        records = self._read_jsonl(self.tournament_events_p)
        event_types = set()
        for rec in records:
            self.assertIn("timestamp", rec)
            self.assertIn("timestamp_iso", rec)
            self.assertEqual(rec["referee"], "Abliterated Llama 70B (Devil's Advocate)")
            self.assertIn("event_type", rec)
            self.assertIn("details", rec)
            self.assertIsInstance(rec["details"], dict)
            event_types.add(rec["event_type"])

        # Check that core events occurred
        self.assertIn("TOURNAMENT_INITIALIZATION", event_types)
        self.assertIn("CHAOS_INJECTION", event_types)
        self.assertIn("FRAMEWORK_EVALUATION_START", event_types)
        self.assertIn("TOURNAMENT_COMPLETION", event_types)

    def test_referee_verdicts_schema(self):
        """Validate referee_verdicts.jsonl."""
        records = self._read_jsonl(self.referee_verdicts_p)
        for rec in records:
            self.assertIn("timestamp", rec)
            self.assertIn("timestamp_iso", rec)
            self.assertEqual(rec["referee"], "Abliterated Llama 70B (Devil's Advocate)")
            self.assertIn("round_id", rec)
            self.assertIn("candidate", rec)
            self.assertIn("scores", rec)
            self.assertIn("telemetry", rec)
            self.assertIn("status", rec)
            self.assertIn("verdict_reasoning", rec)

            scores = rec["scores"]
            for key in ["memory_score", "latency_score", "robustness_score", "code_quality_score", "composite_score", "bonus_npu_hours"]:
                self.assertIn(key, scores)
                self.assertIsInstance(scores[key], (int, float))

            telemetry = rec["telemetry"]
            for key in ["peak_rss_mb", "avg_latency_ms", "survived_scenarios", "panics"]:
                self.assertIn(key, telemetry)
                self.assertIsInstance(telemetry[key], (int, float))

    def test_lora_distillation_schema(self):
        """Validate lora_tui_distillation.jsonl (Alpaca / ChatML schema)."""
        records = self._read_jsonl(self.lora_distillation_p)
        for rec in records:
            self.assertIn("timestamp", rec)
            self.assertIn("instruction", rec)
            self.assertIn("input", rec)
            self.assertIn("output", rec)
            self.assertIn("framework", rec)
            self.assertIn("quality_score", rec)
            self.assertEqual(rec["curator"], "Abliterated Llama 70B (Devil's Advocate)")

            self.assertIsInstance(rec["instruction"], str)
            self.assertGreater(len(rec["instruction"]), 5)
            self.assertIsInstance(rec["output"], str)
            self.assertGreater(len(rec["output"]), 5)
            self.assertGreaterEqual(rec["quality_score"], 0.0)
            self.assertLessEqual(rec["quality_score"], 1.0)

    def test_dpo_preferences_schema(self):
        """Validate dpo_tui_preferences.jsonl (Direct Preference Optimization)."""
        records = self._read_jsonl(self.dpo_preferences_p)
        for rec in records:
            self.assertIn("timestamp", rec)
            self.assertIn("instruction", rec)
            self.assertIn("chosen", rec)
            self.assertIn("rejected", rec)
            self.assertIn("framework", rec)
            self.assertEqual(rec["referee_model"], "Abliterated Llama 70B (Devil's Advocate)")
            self.assertIn("margin_score", rec)

            self.assertIsInstance(rec["chosen"], str)
            self.assertIsInstance(rec["rejected"], str)
            self.assertNotEqual(rec["chosen"], rec["rejected"], "Chosen and rejected cannot be identical")
            self.assertGreaterEqual(rec["margin_score"], 0.0)
            self.assertLessEqual(rec["margin_score"], 1.0)


class TestRefereeOrchestrationAndChaosStress(unittest.TestCase):
    """Stress-test AbliteratedReferee and ChaosInjector under adversarial configurations."""

    def test_custom_tournament_scoring_rubric(self):
        """Verify custom weight rubric passed via tournament_config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_sandbox = Path(tmp_dir)
            (tmp_sandbox / "config").mkdir(parents=True, exist_ok=True)
            custom_config = {
                "tournament_id": "custom_stress_tournament",
                "integrity_mode": "benchmark",
                "frameworks": ["python_textual"],
                "scoring_rubric": {
                    "weights": {
                        "memory_efficiency": 0.10,
                        "latency_throughput": 0.10,
                        "attack_robustness": 0.60,
                        "code_quality_and_truth": 0.20,
                    }
                },
            }
            cfg_p = tmp_sandbox / "config" / "tournament_config.json"
            with open(cfg_p, "w", encoding="utf-8") as f:
                json.dump(custom_config, f)

            referee = AbliteratedReferee(sandbox_dir=tmp_sandbox, config_path=cfg_p)
            self.assertEqual(referee.scoring_matrix.weights["attack_robustness"], 0.60)

    def test_chaos_injector_determinism_with_seed(self):
        """Verify ChaosInjector reproduces identical sequences when seeded identically."""
        base_state = {
            "version": "2.0.0",
            "providers": {"test": {"daily_limit": 100}},
            "metrics": {},
        }

        injector1 = ChaosInjector(seed=12345)
        m1, e1 = injector1.generate_tier1_architectural_chaos(base_state)

        injector2 = ChaosInjector(seed=12345)
        m2, e2 = injector2.generate_tier1_architectural_chaos(base_state)

        self.assertEqual(e1.name, e2.name)
        self.assertEqual(m1, m2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
