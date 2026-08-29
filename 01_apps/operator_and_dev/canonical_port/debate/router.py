"""
AI Debate Router.
=================
Subsystem: 01_apps/operator_and_dev/canonical_port/debate/router.py
"""

from typing import Dict, Any
from .council import DebateCouncilEngine

class AIDebateRouter:
    """Routes architectural queries and system proposals to the AI Debate Council."""

    def __init__(self):
        self.engine = DebateCouncilEngine()

    def route_proposal(self, proposal: str) -> Dict[str, Any]:
        state = self.engine.conduct_debate_round(proposal)
        return {
            "topic": state.topic,
            "round": state.round_number,
            "consensus": state.consensus_summary,
            "consensus_reached": state.consensus_reached,
            "speakers_count": len(state.speakers)
        }
