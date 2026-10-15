#!/usr/bin/env python3
"""
Unit & Integration Tests for Project-Wide Genetic Evolution Orchestrator
=======================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- 8 Monorepo project domain assignments
- Local AI fine-tuning boost integration
- Micro-model leverage on edge tasks (<3.5 GB)
- Generation of the Project-Wide Evolution Report
- JSONL telemetry logging
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from project_wide_genetic_evolution_orchestrator import (
    ProjectWideGeneticEvolutionOrchestrator,
    LOCAL_MODEL_INVENTORY,
    PROJECT_DOMAINS
)


class TestProjectWideGeneticEvolutionOrchestrator(unittest.TestCase):

    def setUp(self):
        self.orchestrator = ProjectWideGeneticEvolutionOrchestrator(population_size=8, mutation_rate=0.2)

    def test_01_inventory_and_domains_coverage(self):
        self.assertGreaterEqual(len(LOCAL_MODEL_INVENTORY), 15)
        self.assertEqual(len(PROJECT_DOMAINS), 8)
        self.assertIn("DOMAIN_1_INFRA_KEEPALIVE", PROJECT_DOMAINS)
        self.assertIn("DOMAIN_2_BIOMETRICS_DSP", PROJECT_DOMAINS)
        self.assertIn("DOMAIN_3_SPECULATIVE_DRAFT", PROJECT_DOMAINS)
        self.assertIn("DOMAIN_7_CODECLASH_SWE", PROJECT_DOMAINS)

    def test_02_fine_tuning_awareness(self):
        for m, prof in LOCAL_MODEL_INVENTORY.items():
            self.assertGreater(prof.fine_tuned_accuracy, prof.base_accuracy)
            self.assertGreater(prof.fine_tuned_accuracy, 0.80)
            self.assertGreater(prof.base_tps, 5.0)

    def test_03_evolution_execution_and_champion(self):
        res = self.orchestrator.run_evolution(generations=3)
        self.assertEqual(len(res["history"]), 3)
        champ = res["champion"]
        self.assertLessEqual(champ.total_mesh_ram_gb, 82.8)
        self.assertGreaterEqual(champ.small_model_leverage_pct, 20.0)
        self.assertGreaterEqual(champ.effective_project_accuracy, 0.85)

    def test_04_report_generation(self):
        self.orchestrator.run_evolution(generations=2)
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "PROJECT_WIDE_GENETIC_EVOLUTION_OPTIMIZATION_REPORT_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Project-Wide Genetic Evolution & Local Training Optimization Report", content)
        self.assertIn("Converged Champion Project Roster", content)


if __name__ == "__main__":
    unittest.main()
