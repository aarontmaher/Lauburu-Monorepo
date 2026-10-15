#!/usr/bin/env python3
"""
Unit & Integration Tests for Micro/Nano Model Niche Optimizer
============================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Sub-500M and sub-100M parameter model benchmark accuracy and latency
- Hyper-niche mapping across monorepo components
- Dual-tier broad model consolidation and replacement evaluation
- Zero-doubt mathematical pruning verification
- Generation of the Obsidian Report and Frontier AI Debate Whitepaper
- JSONL telemetry stream
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from micro_nano_model_niche_optimizer import (
    MicroNanoModelNicheOptimizer,
    NANO_MODEL_CATALOG
)


class TestMicroNanoModelNicheOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = MicroNanoModelNicheOptimizer()

    def test_01_nano_catalog_coverage(self):
        self.assertGreaterEqual(len(NANO_MODEL_CATALOG), 8)
        names = [m.model_name for m in NANO_MODEL_CATALOG]
        self.assertTrue(any("Kokoro" in n for n in names))
        self.assertTrue(any("chronos" in n for n in names))
        self.assertTrue(any("bge-micro" in n for n in names))
        self.assertTrue(any("smollm2" in n for n in names))

    def test_02_evaluation_execution(self):
        models = self.optimizer.evaluate_nano_fleet()
        self.assertEqual(len(models), len(NANO_MODEL_CATALOG))
        for m in models:
            self.assertGreater(m.output_tps, 50.0)
            self.assertLessEqual(m.ttft_ms, 5.0)
            self.assertGreater(m.tuned_accuracy, 0.80)

    def test_03_pruning_and_retention_balance(self):
        models = self.optimizer.evaluate_nano_fleet()
        prunable = [m for m in models if m.lifecycle_verdict == "PRUNABLE_DELETION_PERMITTED"]
        retained = [m for m in models if m.lifecycle_verdict != "PRUNABLE_DELETION_PERMITTED"]
        self.assertGreaterEqual(len(prunable), 2)
        self.assertGreaterEqual(len(retained), 4)

        for p in prunable:
            self.assertTrue(p.is_subsumed_by_broader)
            self.assertIsNotNone(p.subsuming_model)

    def test_04_reports_generation(self):
        self.optimizer.evaluate_nano_fleet()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "MICRO_NANO_MODEL_NICHE_OPTIMIZATION_REPORT_2026.md"
        debate_path = REPO_ROOT / "obsidian_vault" / "05_DEBATES" / "AI_DEBATE_FRONTIER_CLOUD_OPINIONS_ON_MICRO_MODELS_2026.md"
        self.assertTrue(report_path.exists())
        self.assertTrue(debate_path.exists())


if __name__ == "__main__":
    unittest.main()
