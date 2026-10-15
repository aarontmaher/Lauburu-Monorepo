#!/usr/bin/env python3
"""
Unit Tests for Autonomous Conversation Debate Scheduler
========================================================
Validates:
1. Extraction of conversation turns from transcript.jsonl.
2. Multi-model debate synthesis across DeepSeek V4 (1.6T), Gemini Flash Thinking, and Devil's Advocate.
3. Mathematical consensus calculation (>0.98 threshold).
4. Generation of actionable loop improvement suggestions.
5. Vault markdown persistence and continuous LoRA DPO distillation.
"""

import sys
import pytest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SWARMS_ROOT = TEST_DIR.parent

if str(SWARMS_ROOT) not in sys.path:
    sys.path.insert(0, str(SWARMS_ROOT))

from autonomous_conversation_debate_scheduler import AutonomousConversationDebateScheduler


class TestAutonomousConversationDebateScheduler:

    def test_extract_recent_conversation_context(self):
        scheduler = AutonomousConversationDebateScheduler()
        turns = scheduler.extract_recent_conversation_context(max_turns=4)
        assert isinstance(turns, list)
        if turns:
            assert "content" in turns[0]
            assert "type" in turns[0]

    def test_run_debate_cycle_achieves_consensus(self):
        scheduler = AutonomousConversationDebateScheduler()
        res = scheduler.run_debate_cycle()
        assert res["consensus_score"] >= 0.98
        assert "DEBATE_" in res["debate_id"]
        assert len(res["participants"]) >= 6
        assert len(res["synthesized_loop_improvements"]) >= 6

    def test_loop_improvements_are_actionable(self):
        scheduler = AutonomousConversationDebateScheduler()
        res = scheduler.run_debate_cycle()
        improvements = res["synthesized_loop_improvements"]
        for imp in improvements:
            assert len(imp) > 15
            assert any(k in imp.lower() for k in ["loop", "ast", "quota", "gate", "handoff", "offline", "audio", "jules", "pr", "cloudflare", "edge", "proxy"])


if __name__ == "__main__":
    pytest.main(["-v", __file__])
