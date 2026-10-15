#!/usr/bin/env python3
"""
Unit & Integration Tests for Best Local AI Team Daemon
======================================================
Subsystem: 02_ai_models_and_inference/
Validates:
- Full 8 canonical team roles integrated and active
- Cooperative synergy and ELO rating tracking
- Peak speculative decoding speedup (>= 3.0x)
- Dynamic RAM governance compliance (Total RAM pooled across 82.8 GB VRAM)
- Obsidian dashboard and JSONL telemetry persistence
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
AI_DIR = REPO_ROOT / "02_ai_models_and_inference"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from autonomous_best_local_ai_team_daemon import (
    BestLocalAITeamDaemon,
    CANONICAL_TEAM_ROLES
)


class TestBestLocalAITeamDaemon(unittest.TestCase):

    def setUp(self):
        self.daemon = BestLocalAITeamDaemon()

    def test_01_canonical_roles_integrity(self):
        self.assertEqual(len(CANONICAL_TEAM_ROLES), 8)
        role_ids = {r["role_id"] for r in CANONICAL_TEAM_ROLES}
        self.assertIn("ROLE_01_SWARM_COMMANDER", role_ids)
        self.assertIn("ROLE_02_LEAD_ARCHITECT", role_ids)
        self.assertIn("ROLE_03_MATH_REFEREE", role_ids)
        self.assertIn("ROLE_04_POLYGLOT_CODER", role_ids)
        self.assertIn("ROLE_05_VISION_OCR", role_ids)
        self.assertIn("ROLE_06_SPECULATIVE_DRAFT", role_ids)
        self.assertIn("ROLE_07_BIOMETRICS_MOBILE", role_ids)
        self.assertIn("ROLE_08_ROUTER_EDGE_SENTINEL", role_ids)

    def test_02_team_assembly_and_metrics(self):
        members, metrics = self.daemon.assemble_team(epoch=1)
        self.assertEqual(len(members), 8)
        self.assertGreaterEqual(metrics["team_average_elo"], 90.0)
        self.assertGreaterEqual(metrics["team_cooperative_synergy"], 90.0)
        self.assertGreaterEqual(metrics["peak_speculative_speedup"], 3.0)
        self.assertTrue(metrics["host_mac_mini_ram_cap_compliance"])

    def test_03_dashboard_generation(self):
        self.daemon.assemble_team(epoch=1)
        dashboard_path = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "BEST_LOCAL_AI_TEAM_ORCHESTRATION_2026.md"
        self.assertTrue(dashboard_path.exists())
        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Best Local AI Team Orchestration & Optimization Dashboard", content)
        self.assertTrue("Swarm Commander" in content)

    def test_04_continuous_loop_execution(self):
        # Test 2 epochs in fast test mode
        self.daemon.run_continuous_loop(max_epochs=2, interval_sec=0.01)
        telemetry_file = REPO_ROOT / "04_data_and_memory" / "lora_datasets" / "best_local_ai_team_telemetry.jsonl"
        self.assertTrue(telemetry_file.exists())


if __name__ == "__main__":
    unittest.main()
