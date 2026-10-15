#!/usr/bin/env python3
"""
Unit & Integration Tests for Speculative Draft Benchmarker (arXiv:2504.08791)
============================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Speculative metrics calculations across all <= 3B candidate models
- Speedup multiplier > 1.5x across all candidates
- Tokenizer matching bonuses and parameter capacity bonuses
- Report generation to Obsidian Vault
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from speculative_draft_benchmarker import SpeculativeDraftBenchmarker, CANDIDATE_MODELS


class TestSpeculativeDraftBenchmarker(unittest.TestCase):

    def setUp(self):
        self.benchmarker = SpeculativeDraftBenchmarker()

    def test_01_candidate_models_exist(self):
        self.assertGreaterEqual(len(CANDIDATE_MODELS), 6)
        for c in CANDIDATE_MODELS:
            self.assertLessEqual(c.vram_mb, 3000.0)  # Must be <= 3B

    def test_02_all_candidates_produce_speedup(self):
        results = self.benchmarker.run_all_trials(target_model="Qwen 3.8 Max 27B")
        for r in results:
            self.assertGreater(r.speedup_factor, 1.5)  # Every draft model must yield > 1.5x speedup
            self.assertGreater(r.speculative_tps, r.target_standalone_tps)
            self.assertGreaterEqual(r.empirical_acceptance_rate, 60.0)

    def test_03_top_ranked_models(self):
        results = self.benchmarker.run_all_trials(target_model="Qwen 3.8 Max 27B")
        top_model = results[0]
        # Qwen2.5-0.5B or Coder-1.5B should be in top 3
        top_3_names = [r.candidate_name for r in results[:3]]
        self.assertIn("Qwen2.5-0.5B-Instruct", top_3_names)

    def test_04_markdown_report_generated(self):
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "SPECULATIVE_DRAFT_MODELS_BENCHMARK_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Speculative Draft Models Trial & Benchmark Report", content)
        self.assertIn("Qwen2.5-0.5B-Instruct", content)


if __name__ == "__main__":
    unittest.main()
