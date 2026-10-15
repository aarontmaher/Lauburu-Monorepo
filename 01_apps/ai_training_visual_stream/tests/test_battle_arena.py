#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Canonical Watchable AI Battle Arena and Training Stream on Port 4004.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
SRC_DIR = REPO_ROOT / "01_apps/ai_training_visual_stream/src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms/ai_training_games"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms/ai_training_games/tracks"))

from battle_engine import BattleEngine, TRACK_METADATA
from post_game_reviewer import PostGameReviewEngine
from ui_ux_learning_engine import UIUXLearningEngine


class TestBattleArena(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.broadcast_mock = lambda ev, data: self.events.append((ev, data))
        self.engine = BattleEngine(broadcast_fn=self.broadcast_mock)
        self.reviewer = PostGameReviewEngine()
        self.ui_engine = UIUXLearningEngine(broadcast_fn=self.broadcast_mock)

    def test_track_metadata_exists(self):
        """Verifies that all 5 tracks are properly registered."""
        for track_id in range(1, 6):
            self.assertIn(track_id, TRACK_METADATA)
            self.assertTrue(len(TRACK_METADATA[track_id]["name"]) > 0)
            self.assertTrue(len(TRACK_METADATA[track_id]["icon"]) > 0)

    def test_battle_engine_status(self):
        """Verifies initial state structure of BattleEngine."""
        status = self.engine.get_status()
        self.assertIn("active_track", status)
        self.assertIn("current_match", status)
        self.assertIn("leaderboard", status)
        self.assertEqual(status["current_match"]["blue_team_hp"], 100)
        self.assertEqual(status["current_match"]["red_team_hp"], 100)

    def test_set_active_track(self):
        """Verifies switching active tracks."""
        self.engine.set_active_track(2)
        self.assertEqual(self.engine.active_track, 2)
        self.assertEqual(self.engine.current_match["track_id"], 2)

    def test_post_game_reviewer_evaluation(self):
        """Verifies post-game review execution and contrastive DPO pair synthesis."""
        mock_summary = {
            "match_id": "TEST-MATCH-001",
            "track_id": 5,
            "track_name": "Track 5: Capture The Flag (CTF) CyberGym & Bluetooth Mesh",
            "winner": "LOCAL SOVEREIGN SWARM",
            "blue_team_hp": 95,
            "red_team_hp": 12,
            "recent_actions": []
        }
        mock_local = {"composite_score": 98.5, "avg_latency_ms": 3.8}
        mock_cloud = {"composite_score": 75.0, "avg_latency_ms": 490.0}

        review = self.reviewer.evaluate_match(mock_summary, mock_local, mock_cloud)
        self.assertIn("review_id", review)
        self.assertIn("scores", review)
        self.assertIn("gemini_flash_review", review)
        self.assertIn("ultra_plan_review", review)
        self.assertIn("dpo_pair_harvested", review)

        dpo = review["dpo_pair_harvested"]
        self.assertIsNotNone(dpo)
        self.assertIn("instruction", dpo)
        self.assertIn("chosen", dpo)
        self.assertIn("rejected", dpo)
        self.assertIn("consensus_score", dpo)
        self.assertTrue(dpo["consensus_score"] >= 0.98)

    def test_ui_ux_learning_metrics(self):
        """Verifies UI/UX learning engine metrics."""
        status = self.ui_engine.get_status()
        self.assertIn("metrics", status)
        self.assertIn("latest_lessons", status)
        self.assertGreaterEqual(status["metrics"]["render_fps"], 50.0)


if __name__ == "__main__":
    unittest.main()
