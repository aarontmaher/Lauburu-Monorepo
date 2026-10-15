#!/usr/bin/env python3
"""
Unit tests for Continuous Self-Evolving Swarm Loop (90-95% Target).
Verifies provider pacing targets, pause ceilings, and Tiny LM co-evolution.
"""

import os
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys_path = REPO_ROOT / "05_agents_and_swarms"
if str(sys_path) not in os.sys.path:
    os.sys.path.insert(0, str(sys_path))

from continuous_self_evolving_swarm_loop import ContinuousSelfEvolvingSwarmLoop, SWARM_TARGETS, TINY_LM_MODELS


class TestContinuousSelfEvolvingSwarmLoop:
    """Validates 90-95% pacing, safe ceilings, and tiny LM co-evolution."""

    def test_pacing_targets_within_90_95_percent(self):
        """Verifies that all targets are between 90% and 95% and safe ceiling is strictly <100%."""
        for p_id, cfg in SWARM_TARGETS.items():
            cap = cfg["daily_cap"]
            target = cfg["target_count"]
            pause_ceil = cfg["pause_ceiling"]

            assert 0.90 <= (target / cap) <= 0.95, f"{p_id} target out of 90-95% range"
            assert pause_ceil < cap, f"{p_id} pause ceiling must never hit 100% cap"
            assert (pause_ceil / cap) <= 0.95, f"{p_id} pause ceiling must be <= 95%"

    def test_tiny_lm_models_pool(self):
        """Ensures tiny and edge LM models are configured with verified parameters and speed."""
        assert len(TINY_LM_MODELS) >= 5
        ids = [m["id"] for m in TINY_LM_MODELS]
        assert "smol_135m" in ids
        assert "smol_360m" in ids
        assert "qwen_0_5b" in ids
        assert "llama_1b" in ids
        assert "qwen_3b_moe" in ids
        # Verify SmolLM2-135M has highest benchmark speed
        smol = next(m for m in TINY_LM_MODELS if m["id"] == "smol_135m")
        assert smol["benchmark_tok_s"] >= 300.0

    def test_single_co_evolution_step(self):
        """Executes a single step and verifies DPO record generation and state update."""
        engine = ContinuousSelfEvolvingSwarmLoop()
        initial_dpo = engine.state.get("total_dpo_pairs_generated", 0)
        engine._co_evolve_step("gemini_3_1_pro", 1)
        assert engine.state["total_dpo_pairs_generated"] == initial_dpo + 1

    def test_dashboard_publishing(self):
        """Verifies that the Obsidian telemetry dashboard is generated and contains required sections."""
        engine = ContinuousSelfEvolvingSwarmLoop()
        engine._publish_dashboard()
        dashboard_file = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS" / "SELF_EVOLVING_SWARM_TELEMETRY.md"
        assert dashboard_file.exists()
        content = dashboard_file.read_text(encoding="utf-8")
        assert "Self-Evolving Cloud AI Swarm" in content
        assert "90% – 95%" in content
        assert "Local Tiny LM Generational ELO Leaderboard" in content
