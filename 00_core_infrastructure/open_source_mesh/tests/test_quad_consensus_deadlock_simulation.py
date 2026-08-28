#!/usr/bin/env python3
"""
Adversarial Stress Test: Multi-Agent Quad-Consensus Debate & Dynamic ELO Engine
File: 00_core_infrastructure/open_source_mesh/tests/test_quad_consensus_deadlock_simulation.py

Tests:
1. Mathematical consensus thresholds for 6 candidate models (demonstrates that 90% requires 100% unanimity)
2. Strategic veto and deadlock vulnerability under competitive tournament dynamics
3. Dynamic ELO K-factor gaming (token conciseness vs deep reasoning chain penalty)
"""

import math
import numpy as np

def compute_dynamic_k(
    k0: float = 32.0,
    params_b: float = 14.0,
    tokens: int = 256,
    score_agree: float = 0.95,
    rtt_ms: float = 50.0,
    is_authentic: bool = True
) -> dict:
    eta_type = 1.0 # Standard tournament match
    
    # eta_size = max(0.50, min(2.50, log2(71.0) / log2(params_b + 1.0)))
    log2_71 = math.log2(71.0)
    eta_size = max(0.50, min(2.50, log2_71 / math.log2(params_b + 1.0)))
    
    # eta_token = min(1.50, max(0.50, 2048.0 / max(1.0, float(tokens))))
    eta_token = min(1.50, max(0.50, 2048.0 / max(1.0, float(tokens))))
    
    # eta_consensus = min(1.00, max(0.50, 0.50 + 0.50 * score_agree))
    eta_consensus = min(1.00, max(0.50, 0.50 + 0.50 * score_agree))
    
    # eta_compute = min(1.30, max(0.70, 100.0 / (rtt_ms + 30.0)))
    eta_compute = min(1.30, max(0.70, 100.0 / (rtt_ms + 30.0)))
    
    # eta_truth = 1.0 if authentic else 0.0
    eta_truth = 1.0 if is_authentic else 0.0
    
    k_dyn = k0 * eta_type * eta_size * eta_token * eta_consensus * eta_compute * eta_truth
    
    return {
        "k_dyn": k_dyn,
        "eta_size": eta_size,
        "eta_token": eta_token,
        "eta_consensus": eta_consensus,
        "eta_compute": eta_compute,
        "eta_truth": eta_truth
    }

def simulate_voting_scenarios():
    print("================================================================================")
    print("EMPIRICAL ADVERSARIAL TEST: Quad-Consensus Debate Engine & ELO Stress Testing")
    print("================================================================================")

    # 1. CONSENSUS THRESHOLD PROOF
    print("\n--- TEST 1: Voting Pool Threshold Analysis (N = 6 Models) ---")
    n_models = 6
    for votes_for in range(n_models, -1, -1):
        pct = (votes_for / n_models) * 100.0
        passes_90 = (pct >= 90.0)
        status = "PASSED" if passes_90 else "DEADLOCKED (<90%)"
        print(f"Votes For: {votes_for}/{n_models} ({pct:5.1f}%) -> Status: {status}")
    print("Vulnerability Confirmed: In a 6-member council, a 90% threshold requires 100% UNANIMITY (6/6). A single dissenting vote (5/6 = 83.3%) causes complete deadlock.")

    # 2. TOURNAMENT STRATEGIC VETO SIMULATION
    print("\n--- TEST 2: Strategic Veto Simulation in Competitive Tournaments ---")
    # Simulate 100 debate rounds where each model has an 80% natural agreement rate, but a 20% strategic veto probability
    np.random.seed(42)
    num_rounds = 1000
    deadlocks = 0
    vetoes_triggered = 0

    for _ in range(num_rounds):
        # 6 models voting independently
        votes = np.random.choice([1, 0], size=6, p=[0.85, 0.15]) # 85% agree, 15% disagree/veto
        if np.sum(votes) < 6: # Even 1 no vote deadlocks
            deadlocks += 1
        if 0 in votes:
            vetoes_triggered += 1

    deadlock_rate = (deadlocks / num_rounds) * 100.0
    print(f"Simulated {num_rounds} debate rounds with 85% individual model concurrence.")
    print(f"Resulting Tournament Deadlock Rate: {deadlock_rate:.1f}%!")
    print("Flaw Confirmed: Unanimous consensus requirements in competitive settings produce >60% deadlock rates.")

    # 3. DYNAMIC ELO GAMING: TOKEN FRUGALITY VS DEEP REASONING
    print("\n--- TEST 3: Dynamic ELO K-Factor Exploitation ---")
    
    # Model A: DeepSeek-R1 (32B, deep chain-of-thought 3500 tokens, 60ms RTT)
    k_deep = compute_dynamic_k(params_b=32.0, tokens=3500, score_agree=0.95, rtt_ms=60.0)
    
    # Model B: Shallow MoE / Quantized SLM (14B, terse unverified 50 tokens, 15ms RTT)
    k_shallow = compute_dynamic_k(params_b=14.0, tokens=50, score_agree=0.95, rtt_ms=15.0)

    print(f"Model A (Deep Reasoning, 3500 tokens, 32B): K_dyn = {k_deep['k_dyn']:.2f} (eta_token = {k_deep['eta_token']:.3f})")
    print(f"Model B (Shallow Response, 50 tokens, 14B): K_dyn = {k_shallow['k_dyn']:.2f} (eta_token = {k_shallow['eta_token']:.3f})")
    print(f"K-Factor Disparity Ratio: {k_shallow['k_dyn'] / k_deep['k_dyn']:.2f}x advantage for shallow model!")
    print("Exploit Confirmed: The ELO engine heavily punishes thorough chain-of-thought verification in favor of superficial low-token responses.")

if __name__ == "__main__":
    simulate_voting_scenarios()
