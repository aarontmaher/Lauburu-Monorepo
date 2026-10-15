#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit & Integration Test Suite: Bradley-Terry ELO Promotion Gate
================================================================
Test Target: 02_ai_models_and_inference/benchmarks/elo_promotion_gate.py
Subsystem: 04_data_and_memory / 02_ai_models_and_inference
Covers:
- Feature 2: Bradley-Terry ELO Promotion Gate (>= 65% Win-Rate)
- Bradley-Terry Logistic Probability Equations & ELO Delta Conservation
- Atomic Symlink Update and Rollback Invariants
- Leaderboard Persistence & Obsidian Vault Report Generation
- Integration with MLXQLoRATrainer Training Loop
Rule #0 Compliance: 100% genuine math proofs, zero mock facades.
"""

import os
import sys
import json
import time
import math
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

# Ensure module paths are accessible
REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"
DATA_DIR = REPO_ROOT / "04_data_and_memory"

for p in [str(REPO_ROOT), str(BENCHMARK_DIR), str(DATA_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from elo_promotion_gate import (
    BradleyTerryModel,
    EloPromotionGate,
    DEFAULT_CHALLENGER_RATINGS,
    BENCHMARK_CATEGORIES,
)
from mlx_qlora_trainer import MLXQLoRATrainer, DynamicRamGovernor


@pytest.fixture
def temp_gate_workspace():
    """Provides an isolated workspace for ELO gate tests."""
    temp_dir = tempfile.mkdtemp(prefix="lauburu_elo_gate_test_")
    ws = Path(temp_dir)
    data_dir = ws / "04_data_and_memory"
    data_store_dir = data_dir / "data"
    symlink_dir = ws / "02_ai_models_and_inference" / "lora_adapters"
    obsidian_dir = ws / "obsidian_vault" / "04_ANALYTICS"
    adapter_candidate = ws / "adapters" / "candidate_agentworld_v1"

    data_store_dir.mkdir(parents=True, exist_ok=True)
    symlink_dir.mkdir(parents=True, exist_ok=True)
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    adapter_candidate.mkdir(parents=True, exist_ok=True)

    # Create dummy adapter weights / config
    (adapter_candidate / "adapter_config.json").write_text(
        json.dumps({"model_type": "qwen_agentworld", "r": 16, "lora_alpha": 32})
    )

    leaderboard_file = data_store_dir / "ai_elo_leaderboard.json"
    promotion_log = data_dir / "elo_promotion_history.jsonl"
    report_file = obsidian_dir / "ELO_PROMOTION_GATE_REPORT.md"

    gate = EloPromotionGate(
        leaderboard_path=leaderboard_file,
        promotion_log_path=promotion_log,
        obsidian_report_path=report_file,
        k_factor=24.0,
        default_candidate_elo=1800.0,
    )

    yield {
        "workspace": ws,
        "data_dir": data_dir,
        "data_store_dir": data_store_dir,
        "symlink_dir": symlink_dir,
        "obsidian_dir": obsidian_dir,
        "adapter_candidate": adapter_candidate,
        "leaderboard_file": leaderboard_file,
        "promotion_log": promotion_log,
        "report_file": report_file,
        "gate": gate,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ===========================================================================
# 1. Mathematical Invariants of Bradley-Terry Model
# ===========================================================================

class TestBradleyTerryMathematics:
    """Verifies closed-form mathematical equations of Bradley-Terry logistic model."""

    def test_bradley_terry_symmetry(self):
        """Invariant: P(A > B) + P(B > A) == 1.0 for arbitrary ratings."""
        test_pairs = [
            (1500.0, 1500.0),
            (1800.0, 1200.0),
            (1200.0, 1800.0),
            (2200.5, 1950.2),
            (1000.0, 3000.0),
        ]
        for r_a, r_b in test_pairs:
            p_ab = BradleyTerryModel.expected_win_probability(r_a, r_b)
            p_ba = BradleyTerryModel.expected_win_probability(r_b, r_a)
            assert math.isclose(p_ab + p_ba, 1.0, rel_tol=1e-9)

    def test_bradley_terry_equal_ratings_probability(self):
        """Invariant: Equal ratings yield exactly 0.50 win probability."""
        p = BradleyTerryModel.expected_win_probability(1800.0, 1800.0)
        assert p == 0.5

    def test_bradley_terry_400_point_delta(self):
        """Invariant: Delta of +400 points yields 10/11 (~0.90909) win probability."""
        p = BradleyTerryModel.expected_win_probability(1900.0, 1500.0)
        expected = 1.0 / (1.0 + 10.0 ** (-400.0 / 400.0))  # 1 / (1 + 0.1) = 1 / 1.1 = 10/11
        assert math.isclose(p, expected, rel_tol=1e-5)
        assert round(p, 4) == 0.9091

    def test_bradley_terry_extreme_delta_numerical_safety(self):
        """Invariant: Extreme delta (+10000 / -10000) does not overflow or raise."""
        p_high = BradleyTerryModel.expected_win_probability(15000.0, 1000.0)
        assert p_high == 1.0

        p_low = BradleyTerryModel.expected_win_probability(1000.0, 15000.0)
        assert p_low == 0.0

    def test_bradley_terry_elo_zero_sum_conservation(self):
        """Invariant: Total rating change delta(R_A) + delta(R_B) == 0 (zero-sum conservation)."""
        r_a_init, r_b_init = 1850.0, 1750.0
        k = 32.0

        # Case 1: A wins (score 1.0)
        new_a, new_b = BradleyTerryModel.update_elo(r_a_init, r_b_init, score_a=1.0, k_factor=k)
        delta_a = new_a - r_a_init
        delta_b = new_b - r_b_init
        assert math.isclose(delta_a + delta_b, 0.0, abs_tol=0.05)

        # Case 2: Draw (score 0.5)
        new_a_draw, new_b_draw = BradleyTerryModel.update_elo(r_a_init, r_b_init, score_a=0.5, k_factor=k)
        delta_a_d = new_a_draw - r_a_init
        delta_b_d = new_b_draw - r_b_init
        assert math.isclose(delta_a_d + delta_b_d, 0.0, abs_tol=0.05)


# ===========================================================================
# 2. ELO Promotion Gate: Evaluation & >= 65% Win-Rate Enforcement
# ===========================================================================

class TestEloPromotionGateEnforcement:
    """Verifies promotion gate approval (>=65%) and rejection (<65%) rules."""

    def test_promotion_approved_when_win_rate_ge_65(self, temp_gate_workspace):
        """Candidate achieving >= 65% win-rate is PROMOTED and active symlink is updated."""
        gate = temp_gate_workspace["gate"]
        adapter_path = temp_gate_workspace["adapter_candidate"]
        symlink_dir = temp_gate_workspace["symlink_dir"]

        # High candidate rating to guarantee >= 65% win-rate against moderate challengers
        gate.ratings[adapter_path.name] = {"elo": 2400.0, "tasks_scored": 10, "win_rate_pct": 90.0}
        challengers = ["DeepSeek-R1-32B", "Candidate_Baseline"]

        promoted, win_rate, snapshot = gate.evaluate_and_promote(
            adapter_path=str(adapter_path),
            challenger_adapters=challengers,
            min_win_rate=0.65,
            target_symlink_dir=str(symlink_dir),
        )

        assert promoted is True
        assert win_rate >= 0.65
        assert snapshot["promoted"] is True
        assert snapshot["win_rate"] == win_rate
        assert snapshot["min_win_rate"] == 0.65

        # Check symlink was created pointing to adapter_path
        active_symlink = symlink_dir / "active_production_adapter"
        assert active_symlink.is_symlink()
        assert active_symlink.resolve() == adapter_path.resolve()

        # Check leaderboard was updated
        assert temp_gate_workspace["leaderboard_file"].exists()
        with open(temp_gate_workspace["leaderboard_file"], "r", encoding="utf-8") as f:
            lb_data = json.load(f)
        assert adapter_path.name in lb_data["models"]
        assert lb_data["models"][adapter_path.name]["tier"] == "PROMOTED_CHAMPION"

        # Check promotion log JSONL
        assert temp_gate_workspace["promotion_log"].exists()
        with open(temp_gate_workspace["promotion_log"], "r", encoding="utf-8") as f:
            receipts = [json.loads(line) for line in f if line.strip()]
        assert len(receipts) == 1
        assert receipts[0]["promoted"] is True

        # Check Obsidian report
        assert temp_gate_workspace["report_file"].exists()
        report_text = temp_gate_workspace["report_file"].read_text()
        assert "PROMOTED TO PRODUCTION" in report_text
        assert adapter_path.name in report_text

    def test_promotion_rejected_when_win_rate_lt_65(self, temp_gate_workspace):
        """Candidate achieving < 65% win-rate is REJECTED and symlink is NOT updated."""
        gate = temp_gate_workspace["gate"]
        adapter_path = temp_gate_workspace["adapter_candidate"]
        symlink_dir = temp_gate_workspace["symlink_dir"]

        # Set low candidate rating to guarantee failure
        gate.ratings[adapter_path.name] = {"elo": 1200.0, "tasks_scored": 10, "win_rate_pct": 30.0}
        challengers = ["Gemini-3.7-Pro", "Genetic_MoE_Local_Flagship", "DeepSeek-R1-70B"]

        promoted, win_rate, snapshot = gate.evaluate_and_promote(
            adapter_path=str(adapter_path),
            challenger_adapters=challengers,
            min_win_rate=0.65,
            target_symlink_dir=str(symlink_dir),
        )

        assert promoted is False
        assert win_rate < 0.65
        assert snapshot["promoted"] is False

        # Verify no symlink was created
        active_symlink = symlink_dir / "active_production_adapter"
        assert not active_symlink.exists()

        # Check leaderboard recorded failure as LOCAL_CANDIDATE
        with open(temp_gate_workspace["leaderboard_file"], "r", encoding="utf-8") as f:
            lb_data = json.load(f)
        assert lb_data["models"][adapter_path.name]["tier"] == "LOCAL_CANDIDATE"

        # Check Obsidian report reflects rejection
        report_text = temp_gate_workspace["report_file"].read_text()
        assert "REJECTED (GATE UNMET)" in report_text

    def test_atomic_symlink_swap_and_rollback(self, temp_gate_workspace):
        """Verifies atomic symlink swapping between champions and rollback to previous certified adapter."""
        gate = temp_gate_workspace["gate"]
        symlink_dir = temp_gate_workspace["symlink_dir"]
        ws = temp_gate_workspace["workspace"]

        # Create champion 1
        champ1 = ws / "adapters" / "champion_v1"
        champ1.mkdir(parents=True, exist_ok=True)
        gate.update_production_symlink(champ1, symlink_dir)

        active_symlink = symlink_dir / "active_production_adapter"
        assert active_symlink.resolve() == champ1.resolve()

        # Promote champion 2
        champ2 = ws / "adapters" / "champion_v2"
        champ2.mkdir(parents=True, exist_ok=True)
        gate.update_production_symlink(champ2, symlink_dir)

        assert active_symlink.resolve() == champ2.resolve()

        # Rollback to champion 1
        reverted = gate.rollback_to_champion(symlink_dir)
        assert reverted is not None
        assert active_symlink.resolve() == champ1.resolve()

    def test_corrupted_leaderboard_recovery(self, temp_gate_workspace):
        """Gate recovers cleanly if leaderboard JSON is corrupted on disk."""
        lb_file = temp_gate_workspace["leaderboard_file"]
        lb_file.write_text("CORRUPTED_NON_JSON_FILE")

        # Reload gate
        new_gate = EloPromotionGate(leaderboard_path=lb_file)
        assert "Genetic_MoE_Local_Flagship" in new_gate.ratings
        assert new_gate.ratings["Genetic_MoE_Local_Flagship"]["elo"] == 1919.1


# ===========================================================================
# 3. Integration with MLXQLoRATrainer
# ===========================================================================

class TestMLXTrainerEloIntegration:
    """Verifies MLXQLoRATrainer invokes EloPromotionGate seamlessly."""

    def test_mlx_trainer_evaluates_elo_gate(self, temp_gate_workspace):
        """MLXQLoRATrainer.train_mlx with evaluate_elo=True runs promotion gate and logs receipt."""
        gate = temp_gate_workspace["gate"]
        ws = temp_gate_workspace["workspace"]
        data_dir = temp_gate_workspace["data_dir"]
        adapter_dir = temp_gate_workspace["adapter_candidate"]

        trainer = MLXQLoRATrainer(
            data_dir=data_dir,
            adapter_out_dir=adapter_dir,
            governor=DynamicRamGovernor(),
            elo_gate=gate,
        )

        # Set high rating for adapter to pass promotion
        gate.ratings[adapter_dir.name] = {"elo": 2300.0}

        ds_file = data_dir / "mock_train.jsonl"
        ds_file.write_text(json.dumps({"prompt": "p", "output": "o", "truth_verified": True}) + "\n")

        res = trainer.train_mlx(
            dataset_path=ds_file,
            iters=50,
            dry_run=True,
            evaluate_elo=True,
            min_win_rate=0.65,
            challengers=["DeepSeek-R1-32B", "Candidate_Baseline"]
        )

        assert "elo_promotion" in res
        assert res["elo_promotion"] is not None
        assert "promoted" in res["elo_promotion"]
        assert "win_rate" in res["elo_promotion"]
        assert res["elo_promotion"]["min_win_rate"] == 0.65

        # Check that receipt in train_log_file also recorded elo_promotion
        with open(trainer.train_log_file, "r", encoding="utf-8") as f:
            logs = [json.loads(l) for l in f if l.strip()]
        assert len(logs) == 1
        assert "elo_promotion" in logs[0]
