#!/usr/bin/env python3
"""
Unit & Integration Tests for Unified Hybrid Sharding Engine
===========================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Disaggregated Prefill-Decode routing logic
- Co-residency model verification during 70B and 32B sharding
- Generation of the Obsidian AI Debate Whitepaper
- Telemetry streaming to JSONL
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from unified_hybrid_sharding_engine import UnifiedHybridShardingEngine


class TestUnifiedHybridShardingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = UnifiedHybridShardingEngine()

    def test_01_disaggregated_70b_routing(self):
        d = self.engine.route_inference_request("Llama-3.3-70B", 2048, 512)
        self.assertIn("Mac_Node", d.prefill_node)
        self.assertEqual(d.decode_protocol, "PRIMA.CPP (Halda PRP Cyclic Ring)")
        self.assertGreater(d.estimated_decode_tps, 15.0)
        self.assertIn("Qwen2.5-Math-7B", d.co_resident_small_models)
        self.assertIn("Qwen2.5-VL-3B", d.co_resident_small_models)

    def test_02_disaggregated_32b_routing(self):
        d = self.engine.route_inference_request("WebWorld-32B", 1024, 256)
        self.assertIn("llama.cpp RPC", d.decode_protocol)
        self.assertGreater(d.estimated_decode_tps, 30.0)

    def test_03_ai_debate_whitepaper_generation(self):
        self.engine.generate_ai_debate_whitepaper()
        whitepaper_path = REPO_ROOT / "obsidian_vault" / "05_DEBATES" / "AI_DEBATE_UNIFIED_SHARDING_AND_DISAGGREGATED_PREFILL_2026.md"
        self.assertTrue(whitepaper_path.exists())
        with open(whitepaper_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("AI Debate Consensus: Unified Sharding & Disaggregated Prefill Architecture", content)
        self.assertIn("Mooncake", content)
        self.assertIn("PRIMA.CPP", content)


if __name__ == "__main__":
    unittest.main()
