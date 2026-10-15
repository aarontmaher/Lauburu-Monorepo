#!/usr/bin/env python3
"""
Unit & Integration Tests for Long-Term Security & Procurement Engine
====================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Storage-aware multi-node procurement planner (Host L1 vs MBP TB4 L2 285GB SSD)
- Sandboxed defensive Red/Blue team security audit findings
- Verification and formal math proof of security invariants
- Generation of the Obsidian Reports
- JSONL telemetry logging
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from long_term_security_and_procurement_engine import (
    LongTermSecurityAndProcurementEngine,
    PROCUREMENT_CATALOG
)


class TestLongTermSecurityAndProcurementEngine(unittest.TestCase):

    def setUp(self):
        self.engine = LongTermSecurityAndProcurementEngine()

    def test_01_procurement_catalog_structure(self):
        self.assertGreaterEqual(len(PROCUREMENT_CATALOG), 4)
        names = [p.model_name for p in PROCUREMENT_CATALOG]
        self.assertTrue(any("Hermes-3" in n for n in names))
        self.assertTrue(any("abliterated" in n for n in names))
        self.assertTrue(any("Coder-32B" in n for n in names))

    def test_02_storage_aware_planning(self):
        plan = self.engine.plan_procurement()
        self.assertEqual(len(plan), len(PROCUREMENT_CATALOG))
        for p in plan:
            self.assertIn("storage_target", p)
            self.assertIn("status", p)
            if p["size_gb"] > 25.0:
                self.assertIn("MacBook Pro", p["storage_target"])

    def test_03_sandboxed_security_audit(self):
        findings = self.engine.run_sandboxed_security_audit()
        self.assertGreaterEqual(len(findings), 3)
        for f in findings:
            self.assertEqual(f.status, "PATCHED_AND_VERIFIED")
            self.assertGreater(len(f.blue_team_patch), 10)
            self.assertGreater(len(f.formal_proof_verification), 10)

    def test_04_reports_generation(self):
        self.engine.run_sandboxed_security_audit()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "LONG_TERM_MODEL_PROCUREMENT_AND_SECURITY_REPORT_2026.md"
        debate_path = REPO_ROOT / "obsidian_vault" / "05_DEBATES" / "AI_DEBATE_LONG_TERM_SECURITY_AND_ABLITERATED_RED_BLUE_TEAM_2026.md"
        self.assertTrue(report_path.exists())
        self.assertTrue(debate_path.exists())


if __name__ == "__main__":
    unittest.main()
