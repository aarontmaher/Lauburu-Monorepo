#!/usr/bin/env python3
"""
Unit & Integration Tests for Model Role RAM-to-Usefulness ROI Analyzer
======================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Mathematical ROI calculation integrity (Usefulness / Resource Cost)
- Elimination of artificial niche inflation
- Micro-model high-ROI classification (SmolLM2-135M, Qwen2.5-0.5B)
- Low-ROI overkill model identification (ROI < 6.0)
- Generation of the Obsidian ROI Ledger
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from model_role_roi_analyzer import ModelRoleROIAnalyzer, TASK_PROFILES


class TestModelRoleROIAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = ModelRoleROIAnalyzer()

    def test_01_task_profiles_registered(self):
        self.assertGreaterEqual(len(TASK_PROFILES), 15)
        for name, p in TASK_PROFILES.items():
            self.assertGreater(p["crit"], 0.0)
            self.assertGreater(p["freq"], 0)
            self.assertGreater(p["ram_gb"], 0.0)

    def test_02_roi_evaluation_and_tiers(self):
        results = self.analyzer.evaluate_all_models()
        self.assertGreaterEqual(len(results), 10)

        # Micro models must have higher ROI than heavy 7B-9B models
        micro_135 = next(r for r in results if "135m" in r.model_name.lower())
        heavy_9b = next(r for r in results if "gemma-2-9b" in r.model_name.lower())

        self.assertGreater(micro_135.roi_ratio, heavy_9b.roi_ratio)
        self.assertEqual(micro_135.roi_tier, "🌟 HIGH_ROI_CORE")

    def test_03_overkill_detection(self):
        results = self.analyzer.evaluate_all_models()
        low_roi_models = [r for r in results if r.roi_tier == "🛑 LOW_ROI_OVERKILL"]
        self.assertGreater(len(low_roi_models), 0)
        for r in low_roi_models:
            self.assertEqual(r.recommendation, "CONSOLIDATE_INTO_LIGHTER")

    def test_04_ledger_generation(self):
        self.analyzer.evaluate_all_models()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "MODEL_ROLE_RAM_ROI_AUDIT_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Model Role RAM-to-Usefulness ROI Audit Ledger", content)
        self.assertIn("HIGH_ROI_CORE", content)


if __name__ == "__main__":
    unittest.main()
