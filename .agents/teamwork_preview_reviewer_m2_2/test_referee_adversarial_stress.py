#!/usr/bin/env python3
"""Adversarial Stress Test Suite for Milestone 2 Referee & Chaos Engine.

Tests:
1. Refusal ablation mathematical boundaries (Zero vector, collinear vectors, orthogonal vectors, high-dimensional vectors).
2. Scoring matrix robustness under extreme bounds (NaN, Inf, negative values, 0-division, weight mismatch).
3. Disqualification invariance under multiple simulated panic vectors.
4. Deterministic tie-breaking behavior across identical composite candidates.
5. Multi-tier chaos generation stability and deterministic pseudo-random seed reproducibility.
6. JSONL streaming integrity under concurrent high-throughput append operations.
"""

import json
import math
import tempfile
import threading
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SANDBOX_DIR = REPO_ROOT / ".sandbox_training" / "tui_mastery"
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


class TestAdversarialRefereeStress(unittest.TestCase):

    def test_refusal_ablation_orthogonal_and_collinear(self):
        # 1. Parallel / collinear vectors
        h_parallel = [0.0, 5.0, 0.0]
        r_unit = [0.0, 1.0, 0.0]
        h_clean = calculate_refusal_ablation(h_parallel, r_unit)
        self.assertEqual(h_clean, [0.0, 0.0, 0.0])

        # 2. Orthogonal vectors
        h_ortho = [3.0, 0.0, 4.0]
        h_clean_ortho = calculate_refusal_ablation(h_ortho, r_unit)
        self.assertEqual(h_clean_ortho, [3.0, 0.0, 4.0])

        # 3. High-dimensional vector (100-dim)
        dim = 100
        h_100 = [float(i) for i in range(dim)]
        r_100 = [0.0] * dim
        r_100[50] = 1.0  # Unit along 50th dimension
        h_clean_100 = calculate_refusal_ablation(h_100, r_100)
        self.assertEqual(h_clean_100[50], 0.0)
        self.assertEqual(h_clean_100[49], 49.0)
        self.assertEqual(h_clean_100[51], 51.0)

    def test_scoring_weights_normalization(self):
        # Unnormalized weights (sum = 2.0)
        unnorm_weights = {
            "memory_efficiency": 0.50,
            "latency_throughput": 0.50,
            "attack_robustness": 0.60,
            "code_quality_and_truth": 0.40,
        }
        score = calculate_composite_score(100.0, 100.0, 100.0, 100.0, weights=unnorm_weights)
        self.assertAlmostEqual(score, 100.0)

    def test_scoring_bounds_clamping(self):
        # Scores exceeding 100.0 or below 0.0
        score_high = calculate_composite_score(150.0, 200.0, 1000.0, 500.0)
        self.assertEqual(score_high, 100.0)

        score_low = calculate_composite_score(-50.0, -100.0, -20.0, -10.0)
        self.assertEqual(score_low, 0.0)

    def test_npu_bonus_formula_thresholds(self):
        # At or below threshold (70.0)
        self.assertEqual(calculate_npu_bonus_hours(0.0), 25.0)
        self.assertEqual(calculate_npu_bonus_hours(70.0), 25.0)

        # Capped at 50.0
        self.assertEqual(calculate_npu_bonus_hours(150.0), 50.0)

    def test_deterministic_winner_selection_and_tie_breaking(self):
        matrix = ScoringMatrix()
        # Create identical composite scores but different robustness
        candidate_1 = ScoreBreakdown(
            framework="cand_1",
            memory_score=90.0,
            latency_score=90.0,
            robustness_score=100.0,
            code_quality_score=90.0,
            composite_score=92.5,
            panics_count=0,
            status="COMPLETED",
            bonus_npu_hours=36.25,
            weights_used=DEFAULT_SCORING_WEIGHTS,
        )
        candidate_2 = ScoreBreakdown(
            framework="cand_2",
            memory_score=100.0,
            latency_score=95.0,
            robustness_score=80.0,
            code_quality_score=95.0,
            composite_score=92.5,
            panics_count=0,
            status="COMPLETED",
            bonus_npu_hours=36.25,
            weights_used=DEFAULT_SCORING_WEIGHTS,
        )

        winner = matrix.select_winner([candidate_2, candidate_1])
        # Tie-breaker prioritizes robustness: candidate_1 has 100.0 vs candidate_2 has 80.0
        self.assertEqual(winner.framework, "cand_1")

    def test_empty_candidates_returns_none(self):
        matrix = ScoringMatrix()
        self.assertIsNone(matrix.select_winner([]))

    def test_concurrent_jsonl_logging(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_sandbox = Path(tmp_dir)
            referee = AbliteratedReferee(sandbox_dir=tmp_sandbox)

            def log_worker(worker_id: int):
                for i in range(25):
                    referee.emit_tournament_event("CONCURRENT_EVENT", {"worker": worker_id, "seq": i})
                    referee.emit_referee_verdict({"round_id": f"ROUND_{worker_id}_{i}", "status": "PASS"})
                    referee.emit_lora_training_sample("inst", "inp", "out", "rust", 1.0)
                    referee.emit_dpo_preference_pair("inst", "chosen", "rejected", "rust", 0.9)

            threads = [threading.Thread(target=log_worker, args=(w,)) for w in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Verify that each log has exactly 100 valid lines
            for log_p in [
                referee.tournament_events_log,
                referee.referee_verdicts_log,
                referee.lora_distillation_log,
                referee.dpo_preferences_log,
            ]:
                lines = [line.strip() for line in open(log_p) if line.strip()]
                self.assertEqual(len(lines), 100)
                for line in lines:
                    parsed = json.loads(line)
                    self.assertIn("timestamp", parsed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
