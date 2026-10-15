#!/usr/bin/env python3
"""
Unit & Integration Tests for Model Utility Lifecycle Governor
============================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Immutable anchor whitelist protections (Pinned models never marked dominated)
- 6-pillar capability profiling and scoring
- Pareto dominance computation across all vault models
- Qwen-Math formal accuracy verification score integration
- Audit ledger generation in Obsidian Vault
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from model_utility_lifecycle_governor import (
    ModelUtilityLifecycleGovernor,
    PINNED_IMMUTABLE_PATTERNS
)


class TestModelUtilityLifecycleGovernor(unittest.TestCase):

    def setUp(self):
        self.governor = ModelUtilityLifecycleGovernor()

    def test_01_pinned_whitelist_integrity(self):
        # Master weights must always be pinned
        self.assertTrue(self.governor.is_model_pinned("Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf"))
        self.assertTrue(self.governor.is_model_pinned("Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf"))
        self.assertTrue(self.governor.is_model_pinned("Llama-4-Scout-17B-16E-Instruct-Q4_K_M-00001-of-00002.gguf"))
        self.assertTrue(self.governor.is_model_pinned("smollm2-135m-instruct-q4_k_m.gguf"))

    def test_02_model_scanning_and_evaluation(self):
        models = self.governor.scan_local_models()
        self.assertGreater(len(models), 0)
        for m in models:
            self.assertGreater(m.file_size_gb, 0.0)
            self.assertGreaterEqual(m.math_proof_score, 0.0)
            self.assertLessEqual(m.math_proof_score, 100.0)

    def test_03_pareto_dominance_safeguards(self):
        models = self.governor.scan_local_models()
        audited = self.governor.compute_pareto_dominance(models)
        
        for m in audited:
            if m.is_pinned:
                self.assertEqual(m.pareto_status, "PINNED_CORE")
                self.assertEqual(m.qwen_math_verdict, "IMMUTABLE_CORE_ANCHOR")

    def test_04_ledger_generation(self):
        models = self.governor.scan_local_models()
        self.governor.compute_pareto_dominance(models)
        ledger_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "LOCAL_AI_MODEL_UTILITY_AUDIT_LEDGER_2026.md"
        self.assertTrue(ledger_path.exists())
        with open(ledger_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Local AI Model Utility & Pareto Lifecycle Governance Ledger", content)
        self.assertIn("Qwen-Math", content)


if __name__ == "__main__":
    unittest.main()
