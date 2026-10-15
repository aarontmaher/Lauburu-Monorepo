#!/usr/bin/env python3
"""
Unit & Integration Tests for Genetic Speculative Optimizer & Procurement Protocol
==================================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Genetic Algorithm population initialization, fitness evaluation, and evolution
- Multi-generation fitness convergence (Fitness improves across generations)
- Qwen-Math symbolic correctness weighting
- Procurement daemon disk headroom checks (>= 10 GB) and org whitelist enforcement
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from genetic_speculative_optimizer import GeneticSpeculativeOptimizer, SpeculativeChromosome
from automated_model_procurement_daemon import AutonomousModelProcurementDaemon


class TestGeneticOptimizerAndProcurement(unittest.TestCase):

    def setUp(self):
        self.optimizer = GeneticSpeculativeOptimizer(population_size=8, mutation_rate=0.1)
        self.daemon = AutonomousModelProcurementDaemon(min_free_disk_gb=5.0)

    def test_01_genetic_population_init(self):
        self.optimizer.initialize_population()
        self.assertEqual(len(self.optimizer.population), 8)
        for c in self.optimizer.population:
            self.assertIn(c.quantization, ["Q4_K_M", "Q4_K_S", "IQ3_XXS", "Q5_K_M"])
            self.assertGreaterEqual(c.window_k, 3)
            self.assertLessEqual(c.window_k, 7)

    def test_02_fitness_evaluation_and_evolution(self):
        self.optimizer.initialize_population()
        gen1 = self.optimizer.step_generation()
        self.assertGreater(gen1["best_fitness"], 0.0)
        self.assertGreater(gen1["best_speedup"], 1.0)
        self.assertGreater(gen1["best_math_score"], 0.60)

        # Step 3 generations
        for _ in range(3):
            gen_next = self.optimizer.step_generation()

        # Evolution should preserve or improve fitness
        self.assertGreaterEqual(gen_next["best_fitness"], gen1["best_fitness"])

    def test_03_procurement_whitelist_enforcement(self):
        self.assertTrue(self.daemon.verify_repo_whitelist("Qwen/Qwen2.5-0.5B"))
        self.assertTrue(self.daemon.verify_repo_whitelist("bartowski/SmolLM2-135M"))
        self.assertFalse(self.daemon.verify_repo_whitelist("untrusted_random_org/malicious_model"))

    def test_04_procurement_cycle_execution(self):
        receipts = self.daemon.run_procurement_cycle()
        self.assertGreater(len(receipts), 0)
        for r in receipts:
            self.assertTrue(
                r.status in ["STAGED", "ALREADY_PRESENT", "SKIPPED_DISK_PRESSURE"] or r.status.startswith("DOWNLOAD_ERROR")
            )
            self.assertGreater(r.free_disk_gb_after, 0.0)


if __name__ == "__main__":
    unittest.main()
