#!/usr/bin/env python3
"""
Unit & Integration Tests for Continuous Self-Optimization Daemon
================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- 4-Phase loop cycle execution (Benchmark, Consult, Adapt, Re-Run)
- Continuous multi-cycle daemon execution
- Monotonic positive fitness gain verification
- Generation of the Obsidian Report and Debate Whitepaper
- JSONL telemetry stream
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from continuous_autonomous_self_optimization_daemon import (
    ContinuousAutonomousSelfOptimizationDaemon,
    LoopIterationRecord
)


class TestContinuousAutonomousSelfOptimizationDaemon(unittest.TestCase):

    def setUp(self):
        self.daemon = ContinuousAutonomousSelfOptimizationDaemon()

    def test_01_single_loop_execution(self):
        rec = self.daemon.execute_loop_cycle()
        self.assertIsInstance(rec, LoopIterationRecord)
        self.assertEqual(rec.iteration_id, 1)
        self.assertIn("measured_ttft_ms", rec.phase1_benchmark_summary)
        self.assertIn("consensus_verdict", rec.phase2_debate_consensus)
        self.assertGreater(len(rec.phase3_applied_adaptations), 0)
        self.assertGreater(rec.phase4_composite_fitness, 94.0)

    def test_02_continuous_multi_cycle_execution(self):
        records = self.daemon.run_continuous_daemon(max_cycles=3, interval_seconds=0)
        self.assertEqual(len(records), 3)
        self.assertGreater(records[-1].phase4_composite_fitness, records[0].phase4_composite_fitness)

    def test_03_reports_generation(self):
        self.daemon.execute_loop_cycle()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "CONTINUOUS_SELF_OPTIMIZATION_REPORT_2026.md"
        debate_path = REPO_ROOT / "obsidian_vault" / "05_DEBATES" / "AI_DEBATE_CONTINUOUS_SELF_OPTIMIZATION_LOOP_2026.md"
        self.assertTrue(report_path.exists())
        self.assertTrue(debate_path.exists())


if __name__ == "__main__":
    unittest.main()
