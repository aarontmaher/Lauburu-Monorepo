#!/usr/bin/env python3
"""
AI Project Benchmarking Leaderboard Engine (Canonical Wrapper)
==============================================================
Provides backward-compatible access to the unified Canonical AI Leaderboard Engine.
"""
import sys
from pathlib import Path

# Ensure self_healing_hub/src is on path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from canonical_ai_leaderboard import CanonicalAILeaderboardEngine

class AIBenchmarkLeaderboardEngine(CanonicalAILeaderboardEngine):
    def get_leaderboard_data(self):
        """Returns the unified canonical leaderboard data."""
        return self.get_canonical_leaderboard()

if __name__ == "__main__":
    import json
    engine = AIBenchmarkLeaderboardEngine()
    print(json.dumps(engine.get_leaderboard_data(), indent=2))
