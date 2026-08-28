#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lauburu Red/Blue Adversarial Arena: AI Debate Tournament & Leaderboard Package
"""

from .leaderboard_connector import (
    LeaderboardConnector,
    CrownStatus,
    LeaderboardUpdateResult,
    compute_dynamic_k,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    ABILITERATED_LLAMA_PROFILE
)

from .red_blue_debate_tournament import (
    RedBlueDebateTournament,
    DebateTurn,
    ConsensusVector,
    DebateOutcome,
    compute_merkle_state_root,
    ACCORD_DIMENSION_WEIGHTS
)

__all__ = [
    "LeaderboardConnector",
    "CrownStatus",
    "LeaderboardUpdateResult",
    "compute_dynamic_k",
    "compute_eta_size",
    "compute_eta_token",
    "compute_eta_consensus",
    "compute_eta_compute",
    "compute_eta_truth",
    "ABILITERATED_LLAMA_PROFILE",
    "RedBlueDebateTournament",
    "DebateTurn",
    "ConsensusVector",
    "DebateOutcome",
    "compute_merkle_state_root",
    "ACCORD_DIMENSION_WEIGHTS"
]
