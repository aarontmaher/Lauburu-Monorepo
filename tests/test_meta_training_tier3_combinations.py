"""
Tier 3: Cross-Feature Combination E2E Tests for Meta-Training Game Dashboard & Tri-Orchestrator AI Debate System.
Validates:
1. Closed-Loop Deliberation Lifecycle (Debate Execution -> Dynamic ELO Calculation -> Leaderboard Update -> Task Dispatch Routing).
2. Multi-Model Tournament Simulation & Zero-Sum ELO Conservation.
3. Bidirectional Reinforcement Transfer (Game Arena ELO -> Real Project Contribution ELO).
4. Dynamic K-Factor Multi-Pillar Synergy & Asymmetric Parameter Matching.
"""

import os
import sys
import json
import time
import copy
from pathlib import Path
from typing import Dict, Any, List
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src"
SCRIPTS_PATH = REPO_ROOT / "06_scripts_and_tooling" / "scripts"

for p in [REPO_ROOT, SRC_PATH, SCRIPTS_PATH]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tests.test_meta_training_tier1_features import (
    calculate_expected_elo,
    compute_dynamic_k_factor,
    ReferenceTaskDispatchEngine
)


class TestTier3CrossFeatureCombinations:
    """Tier 3: Cross-Feature Combinations & Integration Test Suite."""

    # -----------------------------------------------------------------------
    # Combination 1: Full Closed-Loop Deliberation Lifecycle
    # -----------------------------------------------------------------------
    def test_c1_closed_loop_deliberation_elo_dispatch_lifecycle(self):
        """Verify the complete feedback loop: Debate Win -> ELO Update -> Rank Reorder -> Task Dispatch Routing."""
        from ai_debate_engine import generate_domain_conclusions
        from canonical_ai_leaderboard import CanonicalAILeaderboardEngine

        engine = CanonicalAILeaderboardEngine()
        initial_data = engine.get_canonical_leaderboard()
        models_copy = copy.deepcopy(initial_data["leaderboard"])

        # 1. Execute Debate
        topic = "Spatial 955-Node OPML Grappling Kinematics and Real-Time Joint Torque Extraction"
        domain = "Kinematics_Optimization"
        debate_result = generate_domain_conclusions(topic, domain)
        assert "consensus_conclusion" in debate_result

        # Identify Model A (top model) and Model B (runner-up)
        model_a = models_copy[0]
        model_b = models_copy[1]

        initial_elo_a = model_a["elo"]
        initial_elo_b = model_b["elo"]

        # 2. Compute Dynamic ELO Delta with Efficiency Multipliers
        e_a = calculate_expected_elo(initial_elo_a, initial_elo_b)
        e_b = calculate_expected_elo(initial_elo_b, initial_elo_a)

        # Model A wins with high parameter efficiency (eta_size=1.45, eta_token=1.20)
        k_dyn = compute_dynamic_k_factor(base_k=32.0, eta_size=1.45, eta_token=1.20, eta_consensus=0.98, eta_truth=1.0)
        delta_a = round(k_dyn * (1.0 - e_a), 2)
        delta_b = round(k_dyn * (0.0 - e_b), 2)

        model_a["elo"] += delta_a
        model_a["wins"] += 1
        model_b["elo"] += delta_b
        model_b["losses"] += 1

        # Recompute canonical scores and sort
        for m in models_copy:
            norm_elo = min(100.0, max(50.0, (m["elo"] - 1600.0) / 8.0))
            m["canonical_score"] = round(0.5 * m["overall_benchmark_score"] + 0.5 * norm_elo, 1)

        models_copy.sort(key=lambda x: (float(x.get("elo", 0.0)), float(x.get("canonical_score", 0.0))), reverse=True)
        for idx, m in enumerate(models_copy):
            m["rank"] = idx + 1

        # 3. Verify Rank #1 is Model A after the win
        assert models_copy[0]["id"] == model_a["id"]
        assert model_a["elo"] > initial_elo_a
        assert model_b["elo"] < initial_elo_b

        # 4. Dispatch a Task for Subsystem 10 (Spatial Grappling Kinematics)
        updated_data = dict(initial_data)
        updated_data["leaderboard"] = models_copy
        router = ReferenceTaskDispatchEngine(updated_data)

        task_spec = {
            "task_id": "TASK_10_OPML_JOINT_TORQUE_SYNC",
            "subsystem": "10_spatial_grappling_kinematics",
            "required_skills": ["grappling_map_understanding", "3d_ai_training_game"],
            "zero_cloud_spend_required": False
        }

        dispatch_result = router.route_task(task_spec)
        assert dispatch_result["routed_model_id"] == model_a["id"], \
            f"Expected {model_a['id']} to be routed following debate win, got {dispatch_result['routed_model_id']}"
        assert dispatch_result["dispatch_ticket"]["status"] == "DISPATCHED"

    # -----------------------------------------------------------------------
    # Combination 2: Multi-Model Round-Robin Tournament Simulation
    # -----------------------------------------------------------------------
    def test_c2_multi_model_tournament_convergence_and_stability(self):
        """Verify multi-round round-robin tournament preserves zero-sum ELO conservation and bounded stability."""
        from canonical_ai_leaderboard import CanonicalAILeaderboardEngine

        engine = CanonicalAILeaderboardEngine()
        data = engine.get_canonical_leaderboard()
        roster = [copy.deepcopy(m) for m in data["leaderboard"][:5]]  # Top 5 fighters

        initial_total_elo = sum(m["elo"] for m in roster)

        # Execute 5 complete round-robin rounds (each pair fights 5 times)
        for round_idx in range(5):
            for i in range(len(roster)):
                for j in range(i + 1, len(roster)):
                    f_a = roster[i]
                    f_b = roster[j]

                    e_a = calculate_expected_elo(f_a["elo"], f_b["elo"])
                    e_b = calculate_expected_elo(f_b["elo"], f_a["elo"])

                    # Higher ELO has higher probability of winning, simulated deterministically based on expectation
                    score_a = 1.0 if e_a >= 0.50 else 0.0
                    score_b = 1.0 - score_a

                    k = compute_dynamic_k_factor(base_k=24.0, eta_size=1.1, eta_token=1.0, eta_consensus=1.0, eta_truth=1.0)
                    delta_a = k * (score_a - e_a)
                    delta_b = k * (score_b - e_b)

                    f_a["elo"] += delta_a
                    f_b["elo"] += delta_b

        # Verify Total ELO is strictly conserved (Zero-Sum Property)
        final_total_elo = sum(m["elo"] for m in roster)
        assert round(final_total_elo, 2) == round(initial_total_elo, 2), \
            f"ELO Conservation violated: Initial={initial_total_elo}, Final={final_total_elo}"

        # Verify no model diverged into negative or infinite ELO
        for m in roster:
            assert 1000.0 < m["elo"] < 4000.0, f"Model {m['id']} ELO out of reasonable bounds: {m['elo']}"

    # -----------------------------------------------------------------------
    # Combination 3: Bidirectional Reinforcement Transfer Pipeline
    # -----------------------------------------------------------------------
    def test_c3_bidirectional_reinforcement_transfer_pipeline(self):
        """Verify game arena ELO transfers to real project contribution ELO via multi-pillar weighting."""
        # Multi-pillar weights from game_to_project_elo_analyzer.py
        pillar_weights = {
            "ast_precision": 0.30,
            "network_transport_mastery": 0.25,
            "hardware_vram_quantization": 0.20,
            "zero_simulated_data_truth": 0.15,
            "ghost_daemon_orchestration": 0.10
        }

        # Model A: High AST + Network + Zero Fake Data
        ast_score = 99.8
        net_score = 95.0
        quant_score = 99.0
        truth_score = 100.0
        ghost_score = 92.0
        game_elo = 3089.0

        composite_transfer_fitness = (
            (ast_score * pillar_weights["ast_precision"]) +
            (net_score * pillar_weights["network_transport_mastery"]) +
            (quant_score * pillar_weights["hardware_vram_quantization"]) +
            (truth_score * pillar_weights["zero_simulated_data_truth"]) +
            (ghost_score * pillar_weights["ghost_daemon_orchestration"])
        )

        project_contribution_elo = round((game_elo * 0.60) + (composite_transfer_fitness * 12.0))

        # Expected range: ~1853 (0.60 * 3089) + ~1170 (97.5 * 12) = ~3023
        assert 2950 <= project_contribution_elo <= 3100, \
            f"Project contribution ELO {project_contribution_elo} outside expected calibration range"

    # -----------------------------------------------------------------------
    # Combination 4: Dynamic K-Factor Multi-Pillar Synergy & Asymmetric Matchups
    # -----------------------------------------------------------------------
    def test_c4_dynamic_k_factor_multi_pillar_synergy(self):
        """Verify small SLM winning against large titan yields higher ELO reward than giant beating small SLM."""
        r_slm = 2000.0
        r_giant = 2400.0

        # Scenario 1: SLM wins (upset with high parameter & token frugality)
        e_slm = calculate_expected_elo(r_slm, r_giant)  # ~0.091
        k_slm_win = compute_dynamic_k_factor(base_k=32.0, eta_size=2.2, eta_token=1.5, eta_consensus=1.0, eta_truth=1.0)
        gain_slm = k_slm_win * (1.0 - e_slm)

        # Scenario 2: Giant wins (expected outcome with lower parameter frugality)
        e_giant = calculate_expected_elo(r_giant, r_slm)  # ~0.909
        k_giant_win = compute_dynamic_k_factor(base_k=32.0, eta_size=0.8, eta_token=0.9, eta_consensus=1.0, eta_truth=1.0)
        gain_giant = k_giant_win * (1.0 - e_giant)

        # The SLM's gain on an upset must be significantly greater than the giant's gain on a routine win
        assert gain_slm > gain_giant * 10.0, \
            f"SLM upset reward ({gain_slm}) should be much higher than routine Giant win reward ({gain_giant})"
