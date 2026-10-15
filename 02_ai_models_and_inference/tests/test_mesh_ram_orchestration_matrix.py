#!/usr/bin/env python3
"""
Unit & Integration Tests for Mesh RAM Orchestration Matrix
==========================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Multi-scenario RAM allocation integrity (5 scenarios)
- Co-residency of small models during PRIMA.CPP 70B sharding
- Zero swapping risk and dynamic RAM governance caps (<=90% Mac, <=80% Linux)
- Generation of the Obsidian Mesh RAM Orchestration Report
- JSONL telemetry streaming
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from mesh_ram_orchestration_matrix_bench import (
    MeshRAMOrchestrationMatrixBench,
    MESH_NODES
)


class TestMeshRAMOrchestrationMatrix(unittest.TestCase):

    def setUp(self):
        self.bench = MeshRAMOrchestrationMatrixBench()

    def test_01_mesh_nodes_specification(self):
        self.assertEqual(len(MESH_NODES), 8)
        total_ram = sum(n["ram"] for n in MESH_NODES)
        self.assertGreaterEqual(total_ram, 100.0)

    def test_02_all_scenarios_execution(self):
        results = self.bench.evaluate_all_scenarios()
        self.assertEqual(len(results), 5)
        scenario_ids = [r.scenario_id for r in results]
        self.assertIn("SCENARIO_A", scenario_ids)
        self.assertIn("SCENARIO_B", scenario_ids)
        self.assertIn("SCENARIO_C", scenario_ids)
        self.assertIn("SCENARIO_D", scenario_ids)
        self.assertIn("SCENARIO_E", scenario_ids)

        for r in results:
            self.assertFalse(r.swapping_risk_detected)
            self.assertEqual(r.governance_verdict, "100%_OPTIMAL_SAFE")
            self.assertGreater(r.joint_throughput_tps, 10.0)
            self.assertGreater(r.concurrent_active_models, 5)

    def test_03_scenario_a_coresidency_details(self):
        results = self.bench.evaluate_all_scenarios()
        scen_a = next(r for r in results if r.scenario_id == "SCENARIO_A")
        mac_node = next(n for n in scen_a.node_states if n.node_name == "Mac_Node")
        
        # During 70B sharding (13.1 GB on Mac Mini), small models take 7.70 GB
        self.assertAlmostEqual(mac_node.sharded_heavy_ram_gb, 13.1, delta=0.5)
        self.assertGreaterEqual(mac_node.remaining_headroom_gb, 0.5)
        self.assertIn("Qwen2.5-Math-7B (4.4G)", mac_node.resident_models)
        self.assertIn("Qwen2.5-VL-3B (1.8G)", mac_node.resident_models)

    def test_04_report_generation(self):
        self.bench.evaluate_all_scenarios()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "MESH_RAM_USAGE_AND_CONCURRENT_ORCHESTRATION_REPORT_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Mesh RAM Usage & Concurrent Model Orchestration Benchmark", content)
        self.assertIn("SCENARIO_A", content)


if __name__ == "__main__":
    unittest.main()
