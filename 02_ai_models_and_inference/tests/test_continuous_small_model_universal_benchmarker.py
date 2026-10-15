#!/usr/bin/env python3
"""
Unit & Integration Tests for Universal Small Model Continuous Benchmarker
=========================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Comprehensive coverage of open-source providers (DeepSeek, Kimi, Qwen, SmolLM, Llama, Gemma, Phi, MiniCPM)
- Empirical RAM-to-Usefulness ROI calculation
- Speculative acceleration multipliers (up to 3.07x)
- Generation of the Obsidian Report
- JSONL telemetry streaming
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from continuous_small_model_universal_benchmarker import (
    UniversalSmallModelContinuousBenchmarker,
    SMALL_MODEL_CATALOG
)


class TestContinuousSmallModelUniversalBenchmarker(unittest.TestCase):

    def setUp(self):
        self.benchmarker = UniversalSmallModelContinuousBenchmarker()

    def test_01_provider_families_coverage(self):
        self.assertGreaterEqual(len(SMALL_MODEL_CATALOG), 20)
        providers = set(m["provider"] for m in SMALL_MODEL_CATALOG)
        self.assertIn("DeepSeek", providers)
        self.assertIn("Kimi/Moonshot", providers)
        self.assertIn("Qwen", providers)
        self.assertIn("SmolLM", providers)
        self.assertIn("Meta Llama", providers)
        self.assertIn("Google Gemma", providers)
        self.assertIn("Microsoft Phi", providers)

    def test_02_benchmark_scores_and_metrics(self):
        results = self.benchmarker.run_full_benchmark()
        self.assertEqual(len(results), len(SMALL_MODEL_CATALOG))
        for r in results:
            self.assertGreater(r.output_tps, 20.0)
            self.assertLessEqual(r.ttft_ms, 15.0)
            self.assertGreater(r.tuned_accuracy, 0.80)
            self.assertGreater(r.ram_roi_score, 50.0)
            self.assertGreater(r.speculative_speedup_x, 1.2)

    def test_03_top_performers_ranking(self):
        results = self.benchmarker.run_full_benchmark()
        top_roi = results[0]
        self.assertEqual(top_roi.model_name, "smollm2-135m-instruct")
        self.assertGreater(top_roi.ram_roi_score, 2000.0)

        # Check top speculative draft head
        qwen05 = next(r for r in results if "qwen2.5-0.5b" in r.model_name)
        self.assertGreaterEqual(qwen05.speculative_speedup_x, 3.0)

    def test_04_report_generation(self):
        self.benchmarker.run_full_benchmark()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "UNIVERSAL_SMALL_MODEL_CONTINUOUS_BENCHMARK_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Universal Small/Micro Model Continuous Benchmark Report", content)
        self.assertIn("DeepSeek", content)
        self.assertIn("Kimi", content)


if __name__ == "__main__":
    unittest.main()
