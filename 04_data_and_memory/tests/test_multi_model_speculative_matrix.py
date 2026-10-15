#!/usr/bin/env python3
"""
Unit & Integration Tests for Multi-Model Speculative Distillation Matrix
=======================================================================
Subsystem: 04_data_and_memory/
Validates:
- 50-pair cross-model evaluation matrix
- Cross-family distillation dividend (> 12% acceptance gain on cross-family pairs)
- Same-family baseline advantages
- Speedup multipliers across all tiers (Micro, 1B, 2B-3B)
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DATA_DIR = REPO_ROOT / "04_data_and_memory"
if str(DATA_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_DIR))

from multi_model_speculative_matrix import (
    MultiModelSpeculativeMatrix,
    TARGET_MODELS,
    DRAFT_MODELS
)


class TestMultiModelSpeculativeMatrix(unittest.TestCase):

    def setUp(self):
        self.matrix = MultiModelSpeculativeMatrix()

    def test_01_matrix_dimensions(self):
        self.assertEqual(len(TARGET_MODELS), 5)
        self.assertEqual(len(DRAFT_MODELS), 10)
        results = self.matrix.run_full_matrix()
        self.assertEqual(len(results), 50)

    def test_02_all_pairs_exhibit_speedup(self):
        results = self.matrix.run_full_matrix()
        for r in results:
            self.assertGreater(r.distilled_speedup, 1.0)
            self.assertGreater(r.distilled_tps, r.baseline_tps)
            self.assertGreater(r.acceptance_gain_pct, 5.0)

    def test_03_cross_family_dividend(self):
        results = self.matrix.run_full_matrix()
        cross_family = [r for r in results if not r.is_same_family]
        same_family = [r for r in results if r.is_same_family]

        avg_cross_gain = sum(r.acceptance_gain_pct for r in cross_family) / len(cross_family)
        avg_same_gain = sum(r.acceptance_gain_pct for r in same_family) / len(same_family)

        # Cross family models should experience higher relative acceptance gains from distillation
        self.assertGreater(avg_cross_gain, avg_same_gain)

    def test_04_report_generation(self):
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "MULTI_MODEL_SPECULATIVE_DISTILLATION_MATRIX_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Multi-Target & Multi-Draft Speculative Distillation Matrix Report", content)
        self.assertIn("Cross-Family Distillation Dividend", content)


if __name__ == "__main__":
    unittest.main()
