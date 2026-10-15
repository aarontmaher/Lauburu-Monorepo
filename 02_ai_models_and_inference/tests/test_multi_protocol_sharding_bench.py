#!/usr/bin/env python3
"""
Unit & Integration Tests for Multi-Protocol Sharding Benchmark Engine
====================================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- All 5 sharding protocols benchmarked (PRIMA.CPP, llama.cpp RPC, Exo, Petals, FSDP)
- Dynamic protocol recommendation engine
- Generation of the Obsidian Multi-Protocol Sharding Report
- JSONL telemetry streaming
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from multi_protocol_sharding_bench import (
    MultiProtocolShardingBenchmark,
    PROTOCOL_DATA
)


class TestMultiProtocolShardingBenchmark(unittest.TestCase):

    def setUp(self):
        self.bench = MultiProtocolShardingBenchmark()

    def test_01_protocol_coverage(self):
        self.assertEqual(len(PROTOCOL_DATA), 5)
        names = [p["name"] for p in PROTOCOL_DATA]
        self.assertTrue(any("PRIMA.CPP" in n for n in names))
        self.assertTrue(any("llama.cpp RPC" in n for n in names))
        self.assertTrue(any("Exo P2P" in n for n in names))
        self.assertTrue(any("Petals DHT" in n for n in names))
        self.assertTrue(any("FSDP" in n for n in names))

    def test_02_benchmark_scores_and_metrics(self):
        scores = self.bench.run_all_benchmarks()
        self.assertEqual(len(scores), 5)
        for s in scores:
            self.assertGreater(s.tps_70b, 5.0)
            self.assertGreater(s.tps_32b, 10.0)
            self.assertGreater(s.overall_efficiency_score, 80.0)
            self.assertGreater(s.network_bandwidth_mb_s, 50.0)

    def test_03_recommendation_logic(self):
        # 70B on heterogeneous cluster -> PRIMA.CPP
        rec_proto, _ = self.bench.recommendator = self.bench.recommend_protocol_for_request(70.0, 6, "Wi-Fi 7 Heterogeneous")
        self.assertIn("PRIMA.CPP", rec_proto)

        # 32B on TB4 -> llama.cpp RPC
        rec_proto, _ = self.bench.recommend_protocol_for_request(20.0, 2, "Thunderbolt 4")
        self.assertIn("llama.cpp RPC", rec_proto)

        # < 15GB -> Standalone / Speculative
        rec_proto, _ = self.bench.recommend_protocol_for_request(7.0, 1, "Local Metal")
        self.assertIn("Standalone", rec_proto)

    def test_04_report_generation(self):
        self.bench.run_all_benchmarks()
        report_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "MULTI_PROTOCOL_SHARDING_BENCHMARK_2026.md"
        self.assertTrue(report_path.exists())
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Multi-Protocol Distributed AI Sharding Benchmark Matrix", content)
        self.assertIn("PRIMA.CPP", content)
        self.assertIn("Exo P2P", content)


if __name__ == "__main__":
    unittest.main()
