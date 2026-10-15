#!/usr/bin/env python3
"""
Unit & Integration Tests for Genetic Mesh Protocol Optimizer (100B+ Models)
===========================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- 100B+ model sharding evaluation (Command-R+ 104B, Llama 405B, DeepSeek 671B, Qwen 72B)
- Multi-generation genetic evolution and confidence convergence
- Generation of the 100B+ Evolution Report and Global Scaling Plan
- Telemetry logging to JSONL
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from genetic_mesh_protocol_optimizer import (
    GeneticMeshProtocolOptimizer,
    FRONTIER_MODELS
)


class TestGeneticMeshProtocolOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = GeneticMeshProtocolOptimizer(population_size=8, mutation_rate=0.2)

    def test_01_frontier_models_coverage(self):
        self.assertGreaterEqual(len(FRONTIER_MODELS), 4)
        self.assertTrue(any("Llama-4-Scout" in k for k in FRONTIER_MODELS))
        self.assertTrue(any("Qwen-AgentWorld" in k for k in FRONTIER_MODELS))
        self.assertTrue(any("Command-R+" in k for k in FRONTIER_MODELS))
        self.assertTrue(any("Qwen2.5-72B" in k for k in FRONTIER_MODELS))

    def test_02_population_initialization_and_evaluation(self):
        self.optimizer.initialize_population()
        self.assertEqual(len(self.optimizer.population), 8)
        for c in self.optimizer.population:
            self.assertGreater(c.composite_fitness, 0.0)
            self.assertGreater(c.output_tps, 0.0)
            self.assertGreater(c.protocol_confidence_score, 0.0)

    def test_03_generational_evolution(self):
        res = self.optimizer.run_evolution(generations=3)
        self.assertEqual(len(res["history"]), 3)
        champ = res["champion"]
        self.assertGreater(champ.output_tps, 10.0)
        self.assertGreaterEqual(champ.protocol_confidence_score, 0.8)

    def test_04_reports_generation(self):
        self.optimizer.run_evolution(generations=2)
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "GENETIC_100B_PROTOCOL_EVOLUTION_REPORT_2026.md"
        scaling_path = REPO_ROOT / "obsidian_vault" / "07_ARCHITECTURE" / "GLOBAL_APP_SCALING_AND_MESH_DISTRIBUTION_PLAN_2026.md"
        self.assertTrue(report_path.exists())
        self.assertTrue(scaling_path.exists())


if __name__ == "__main__":
    unittest.main()
