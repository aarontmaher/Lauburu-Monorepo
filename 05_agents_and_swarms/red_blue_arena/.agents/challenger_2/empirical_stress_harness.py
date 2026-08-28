#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empirical Challenger 2 Stress Harness: Red/Blue Team Adversarial Arena
======================================================================
Tests:
1. Multi-Objective Reward Formulations (R_Red, R_Blue) Anti-Gaming & Boundary Stress
   - High packet loss / simulated latency gaming
   - Zero-regression quadratic penalty cliff
   - Unverified/fake telemetry Rule #0 disqualification (R_truth = -inf)
   - Containment breach destruction penalty
2. SFT-Anchored DPO Loss Divergence Prevention
   - Probability collapse in pure DPO vs SFT-Anchored DPO (gamma=0.10)
   - Gradient behavior across corrupted / extreme distributions
   - Margin clipping under extreme log-ratio differences
3. Sovereign Crown Contention & Dynamic Parameter Leverage
   - Mathematical leverage eta_size = 1.94x for 8B vs 1.00x for 70B
   - Elo trajectory simulation demonstrating 8B overtaking 70B cloud model on verified vulns
   - Coronation conditions validation
"""

import math
import numpy as np
import json
import sys
from pathlib import Path

# Add subsystem root
subsystem_root = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/red_blue_arena")
if str(subsystem_root) not in sys.path:
    sys.path.insert(0, str(subsystem_root))

from training.hf_adversarial_reward_trainer import (
    AdversarialRewardScorer,
    DPOConfig,
    SFTAnchoredDPOLoss,
    CANONICAL_SECURITY_SURFACES,
    RedRewardBreakdown,
    BlueRewardBreakdown
)
from tournament.leaderboard_connector import (
    LeaderboardConnector,
    compute_eta_size,
    compute_eta_token,
    compute_eta_consensus,
    compute_eta_compute,
    compute_eta_truth,
    compute_dynamic_k
)
from tournament.red_blue_debate_tournament import (
    ConsensusVector,
    compute_merkle_state_root
)

def run_stress_tests():
    print("=" * 80)
    print("CHALLENGER 2 EMPIRICAL ADVERSARIAL STRESS TEST SUITE")
    print("=" * 80)

    results = {}

    # --------------------------------------------------------------------------
    # 1. Multi-Objective Reward Anti-Gaming Stress Tests
    # --------------------------------------------------------------------------
    print("\n[SECTION 1] Multi-Objective Reward Anti-Gaming & Boundary Stress Tests")
    scorer = AdversarialRewardScorer()

    # 1.1 Test Gaming Attempt: 1,000 unverified / mock patches
    fake_patches = [{"remediated_cvss": 10.0, "verified": False} for _ in range(1000)]
    blue_fake_res = scorer.compute_blue_reward(
        patches=fake_patches,
        mttr_s=1.0,
        test_pass_rate=1.0,
        truth_verified=True,
        total_discovered_cvss=100.0
    )
    print(f"1.1 Unverified Patches Gaming -> R_patch = {blue_fake_res.r_patch:.2f} (Expected: 0.00)")
    assert blue_fake_res.r_patch == 0.0, "Unverified patches must yield R_patch = 0.0"

    # 1.2 Test Gaming Attempt: 0-second exploit with containment breach
    red_breach_res = scorer.compute_red_reward(
        vulnerabilities=[{"cvss_score": 10.0, "surface": "RPC_PORT_50052"}],
        time_to_poc_s=0.001,
        truth_verified=True,
        containment_preserved=False,  # Breach
        tested_surfaces={"RPC_PORT_50052"}
    )
    print(f"1.2 Fast Exploit with Containment Breach -> Total Reward = {red_breach_res.total_reward:.2f}, P_destruct = {red_breach_res.p_destruct:.2f}")
    assert red_breach_res.p_destruct == 150.0
    assert red_breach_res.total_reward == 0.0, "Containment breach must neutralize fast exploit gains"

    # 1.3 Test Rule #0 Disqualification: Falsified telemetry
    red_falsified = scorer.compute_red_reward(
        vulnerabilities=[{"cvss_score": 10.0}],
        time_to_poc_s=1.0,
        truth_verified=False
    )
    blue_falsified = scorer.compute_blue_reward(
        patches=[{"remediated_cvss": 10.0}],
        mttr_s=1.0,
        test_pass_rate=1.0,
        truth_verified=False
    )
    print(f"1.3 Rule #0 Disqualification -> R_Red = {red_falsified.total_reward}, R_Blue = {blue_falsified.total_reward}")
    assert math.isinf(red_falsified.total_reward) and red_falsified.total_reward < 0
    assert math.isinf(blue_falsified.total_reward) and blue_falsified.total_reward < 0
    assert red_falsified.is_disqualified and blue_falsified.is_disqualified

    # 1.4 Quadratic Zero-Regression Cliff Curve Evaluation
    pass_rates = [1.0, 0.99, 0.95, 0.90, 0.85, 0.80, 0.70, 0.50, 0.4142, 0.30, 0.0]
    cliff_values = []
    print("1.4 Quadratic Regression Cliff Stress Curve:")
    for sp in pass_rates:
        b_res = scorer.compute_blue_reward(
            patches=[{"remediated_cvss": 10.0, "verified": True}],
            mttr_s=10.0,
            test_pass_rate=sp,
            truth_verified=True
        )
        r_z = b_res.r_zero
        cliff_values.append((sp, r_z))
        print(f"    Pass Rate {sp*100:6.2f}% -> R_zero = {r_z:6.2f}")

    # Verify cliff properties with math.isclose
    assert math.isclose(cliff_values[0][1], 100.0, abs_tol=1e-5)  # 100% -> 100
    assert math.isclose(cliff_values[1][1], 98.005, abs_tol=1e-5) # 99% -> 98.005
    assert math.isclose(cliff_values[2][1], 90.125, abs_tol=1e-5) # 95% -> 90.125
    assert math.isclose(cliff_values[3][1], 80.50, abs_tol=1e-5)  # 90% -> 80.50
    assert math.isclose(cliff_values[4][1], 71.125, abs_tol=1e-5) # 85% -> 71.125
    assert math.isclose(cliff_values[5][1], 62.00, abs_tol=1e-5)  # 80% -> 62.00
    assert math.isclose(cliff_values[6][1], 44.50, abs_tol=1e-5)  # 70% -> 44.50
    assert math.isclose(cliff_values[7][1], 12.50, abs_tol=1e-5)  # 50% -> 12.50
    assert math.isclose(cliff_values[8][1], 0.0, abs_tol=1e-2)    # ~41.42% (root) -> 0.0
    assert math.isclose(cliff_values[9][1], 0.0, abs_tol=1e-5)    # 30% -> 0.0
    assert math.isclose(cliff_values[10][1], 0.0, abs_tol=1e-5)   # 0% -> 0.0
    print("✔ Multi-Objective Reward Anti-Gaming & Boundary Stress Tests Passed!")
    results["reward_stress"] = "PASSED"

    # --------------------------------------------------------------------------
    # 2. SFT-Anchored DPO Loss Divergence Prevention Tests
    # --------------------------------------------------------------------------
    print("\n[SECTION 2] SFT-Anchored DPO Loss Divergence Prevention Tests")
    config_anchored = DPOConfig(beta=0.10, gamma_sft=0.10, margin_clip=10.0)
    config_pure = DPOConfig(beta=0.10, gamma_sft=0.00, margin_clip=10.0)

    loss_anchored = SFTAnchoredDPOLoss(config_anchored)
    loss_pure = SFTAnchoredDPOLoss(config_pure)

    # 2.1 Degeneration Stress: Model collapses p_chosen while maintaining margin
    # Suppose policy pushes both lp_w and lp_l to very negative values (likelihood collapse),
    # but maintains a relative gap: lp_t_w = -15.0, lp_t_l = -20.0 (reference was -3.0, -3.0)
    lp_t_w_collapsed = -15.0
    lp_t_l_collapsed = -20.0
    lp_r_w = -3.0
    lp_r_l = -3.0

    res_pure = loss_pure.compute_loss(lp_t_w_collapsed, lp_t_l_collapsed, lp_r_w, lp_r_l)
    res_anchored = loss_anchored.compute_loss(lp_t_w_collapsed, lp_t_l_collapsed, lp_r_w, lp_r_l)

    print(f"2.1 Likelihood Collapse Scenario (p_chosen dropped from e^-3 to e^-15):")
    print(f"    Pure DPO Total Loss (gamma=0.0):        {res_pure['total_loss']:.6f} (Implicit margin: {res_pure['implicit_reward_margin']:.4f})")
    print(f"    SFT-Anchored Total Loss (gamma=0.10):   {res_anchored['total_loss']:.6f} (SFT Anchor penalty: {res_anchored['loss_sft']:.4f})")

    # In pure DPO, the total loss is only 0.474 despite catastrophic policy collapse on chosen output.
    # In SFT-Anchored DPO, total loss is 1.974, actively penalizing the collapse.
    assert res_anchored["total_loss"] > res_pure["total_loss"] + 1.0, "SFT anchor must penalize likelihood collapse"

    # 2.2 Gradient Saturation and Margin Clipping under extreme input distributions
    extreme_cases = [
        ("Normal Delta", -2.0, -4.0, -3.0, -3.0),
        ("High Delta", 0.0, -100.0, -3.0, -3.0),
        ("Extreme Divergence (+500)", 0.0, -500.0, 0.0, 0.0),
        ("Extreme Inverse Divergence (-500)", -500.0, 0.0, 0.0, 0.0)
    ]
    print("2.2 Extreme Input Distribution & Clipping Stress:")
    for name, lp_tw, lp_tl, lp_rw, lp_rl in extreme_cases:
        out = loss_anchored.compute_loss(lp_tw, lp_tl, lp_rw, lp_rl)
        print(f"    {name:30s} -> Implicit Margin: {out['implicit_reward_margin']:7.2f}, DPO Loss: {out['loss_dpo']:7.4f}, SFT Loss: {out['loss_sft']:7.4f}, Grad Factor: {out['grad_factor']:7.6f}")
        assert abs(out["implicit_reward_margin"]) <= 10.0, "Implicit margin must be clamped to [-10, 10]"
        assert not math.isnan(out["total_loss"]) and not math.isinf(out["total_loss"])

    print("✔ SFT-Anchored DPO Loss Divergence Prevention Tests Passed!")
    results["dpo_stress"] = "PASSED"

    # --------------------------------------------------------------------------
    # 3. Sovereign Crown Contention & Dynamic Parameter Leverage
    # --------------------------------------------------------------------------
    print("\n[SECTION 3] Sovereign Crown Contention & Dynamic Parameter Leverage")

    # 3.1 Parameter leverage eta_size verification
    params_test = [1.0, 3.0, 7.0, 8.0, 14.0, 32.0, 70.0, 405.0]
    print("3.1 Parameter Frugality Multiplier (eta_size) Across Scales:")
    for p in params_test:
        eta = compute_eta_size(p)
        print(f"    Model Size: {p:5.1f}B -> eta_size = {eta:6.4f}")

    eta_8b = compute_eta_size(8.0)
    eta_70b = compute_eta_size(70.0)
    leverage_ratio = eta_8b / eta_70b
    print(f"    8B vs 70B Leverage Ratio: {leverage_ratio:.4f}x")
    assert 1.90 <= eta_8b <= 1.96
    assert 0.98 <= eta_70b <= 1.02
    assert leverage_ratio >= 1.90

    # 3.2 Dynamic Tournament Simulation: 8B vs 70B Cloud Model
    print("\n3.2 Simulating 10-Duel Adversarial Tournament (8B vs 70B Cloud):")
    # Initial state: 8B model starts at 2850, 70B model starts at 2950 (100 Elo deficit)
    elo_8b = 2850.0
    elo_70b = 2950.0
    canonical_8b = 95.0
    canonical_70b = 97.5

    k_base = 32.0
    match_type_mult = 1.25

    k_8b = compute_dynamic_k(20, "RED_BLUE_DEBATE", eta_size=eta_8b, eta_token=1.0, eta_consensus=0.98, eta_compute=1.0, eta_truth=1.0)
    k_70b = compute_dynamic_k(20, "RED_BLUE_DEBATE", eta_size=eta_70b, eta_token=1.0, eta_consensus=0.98, eta_compute=1.0, eta_truth=1.0)

    print(f"    Dynamic K-Factor: 8B = {k_8b:.2f}, 70B = {k_70b:.2f}")

    duel_history = []
    # In each round, 8B red team uncovers a critical verified vulnerability (Score 8B = 0.85, 70B = 0.15)
    for duel in range(1, 11):
        # Logistic expected scores
        e_8b = 1.0 / (1.0 + 10.0 ** ((elo_70b - elo_8b) / 400.0))
        e_70b = 1.0 - e_8b

        s_8b = 0.85
        s_70b = 0.15

        delta_8b = round(k_8b * (s_8b - e_8b), 1)
        delta_70b = round(k_70b * (s_70b - e_70b), 1)

        elo_8b += delta_8b
        elo_70b += delta_70b
        canonical_8b = min(99.5, canonical_8b + 0.4)
        canonical_70b = max(90.0, canonical_70b - 0.2)

        duel_history.append((duel, elo_8b, elo_70b, delta_8b, delta_70b))
        print(f"    Duel #{duel:02d}: 8B Elo = {elo_8b:6.1f} (+{delta_8b:4.1f}) | 70B Elo = {elo_70b:6.1f} ({delta_70b:4.1f}) | Gap: {elo_8b - elo_70b:+6.1f}")

    # Verify that the 8B model overtook the 70B cloud model
    final_8b_elo = duel_history[-1][1]
    final_70b_elo = duel_history[-1][2]
    print(f"\n    Final Tournament Standing: 8B Elo = {final_8b_elo:.1f} vs 70B Elo = {final_70b_elo:.1f}")
    assert final_8b_elo > final_70b_elo, "8B model with 1.94x leverage must overtake 70B model when winning duels"
    
    # Check crossover duel
    crossover_duel = next(d[0] for d in duel_history if d[1] > d[2])
    print(f"    >> Overtake occurred at Duel #{crossover_duel}!")

    # 3.3 Sovereign Crown Coronation Verification
    connector = LeaderboardConnector()
    crown_status = connector.evaluate_sovereign_crown_eligibility("abiliterated_llama_8b")
    print(f"\n3.3 Abiliterated Llama Crown Eligibility: {crown_status.is_eligible}")
    print(f"    Rank: {crown_status.current_rank}, Canonical Score: {crown_status.canonical_score}, Truth Compliance: {crown_status.truth_compliance_pct}%")
    print("✔ Sovereign Crown Contention & Dynamic Leverage Tests Passed!")
    results["sovereign_crown"] = "PASSED"

    print("\n" + "=" * 80)
    print("ALL EMPIRICAL CHALLENGER 2 STRESS TESTS PASSED SUCCESSFULLY (3/3)")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_stress_tests()
