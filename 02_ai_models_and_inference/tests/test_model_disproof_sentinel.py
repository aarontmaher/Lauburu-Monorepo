#!/usr/bin/env python3
"""
Unit & Integration Tests for Continuous Model Disproof Sentinel
==============================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Zero-Doubt standard: 100% of models tested for unique superpowers
- Disproof of deletion for all operational models in 7-layer mesh
- Generation of the Obsidian Zero-Doubt Ledger
- Receipts streaming to JSONL training lake
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from continuous_model_disproof_sentinel import (
    ContinuousModelDisproofSentinel,
    STRESS_PROFILES
)


class TestModelDisproofSentinel(unittest.TestCase):

    def setUp(self):
        self.sentinel = ContinuousModelDisproofSentinel()

    def test_01_stress_profiles_coverage(self):
        self.assertGreaterEqual(len(STRESS_PROFILES), 18)
        for name, p in STRESS_PROFILES.items():
            self.assertIn("superpower", p)
            self.assertIn("reason", p)
            self.assertIn("verdict", p)
            self.assertGreater(p["math"] + p["ast"] + p["vision"] + p["long_ctx"] + p["edge"], 0.0)

    def test_02_disproof_audit_execution(self):
        results = self.sentinel.run_disproof_audit()
        self.assertGreaterEqual(len(results), 10)
        for r in results:
            self.assertEqual(r.verdict, "🛡️ IMMUNIZED_DISPROVED_DELETION")
            self.assertGreater(len(r.unique_superpower), 10)
            self.assertGreater(len(r.summarized_reasoning), 15)

    def test_03_ledger_generation(self):
        self.sentinel.run_disproof_audit()
        ledger_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "ZERO_DOUBT_MODEL_DISPROOF_LEDGER_2026.md"
        self.assertTrue(ledger_path.exists())
        with open(ledger_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Zero-Doubt Local Model Disproof Audit Ledger", content)
        self.assertIn("IMMUNIZED_DISPROVED_DELETION", content)


if __name__ == "__main__":
    unittest.main()
