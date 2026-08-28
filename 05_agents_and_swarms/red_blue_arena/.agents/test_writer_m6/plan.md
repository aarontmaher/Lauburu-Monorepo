# Test Architecture & Plan for Milestone M6: Dual-Track E2E Test Suite

## Overview
Milestone M6 establishes a comprehensive, zero-mock, multi-tier Pytest test suite for the Red/Blue Team Adversarial Arena. The suite validates security hardening invariants, mathematical proofs, closed-form multi-objective rewards, refusal vector ablation math, DPO anchor loss regularization, dynamic ELO scaling, 4-turn debate deliberation, and Merkle root state attestation.

## Test Suite Architecture

### 1. `TEST_INFRA.md`
- Documentation of test philosophy (Rule #0 zero-mock truth enforcement, progressive testability, isolation).
- 5-Tier test methodology:
  - **Tier 1: Feature Isolation & Unit Invariants** (individual components: BlueTeamSSHShield, TripwireSentinel, AbiliteratedLlamaEngine, AdversarialRewardScorer, RedBlueDebateTournament).
  - **Tier 2: Boundary & Corner Cases** (CVSS 0.0-10.0, 0.9% loss cliff gaming, extreme latency, token overflow, KL divergence bounds, empty inputs, malformed configs).
  - **Tier 3: Cross-Feature Pairwise Integrations** (Red Exploit $\to$ Reward Scorer $\to$ DPO Dataset Export; Debate Round $\to$ ELO Update $\to$ Leaderboard State $\to$ Merkle Root).
  - **Tier 4: Real-World Adversarial Arena Simulation** (Full end-to-end 4-turn duel between Abiliterated Llama and Blue Team Defender, including failover fallback, AST patching, and consensus accord).
  - **Tier 5: Benchmark Mode & Sovereign Crown Verification** (Benchmark integrity mode, deterministic Merkle root attestation, and Sovereign AGI Crown coronation checks).
- Full feature checklist mapped against milestones M1–M5.
- Benchmark test execution runner commands.

### 2. `tests/__init__.py`
- Package initialization marker for pytest module resolution.

### 3. `tests/test_hardening_invariants.py`
Invariant & mathematical property verification:
- **SSH Multiplexing Latency Invariant**: Verify `ControlMaster auto`, `ControlPath`, `ControlPersist` parameters and socket path resolution for sub-3ms latency characteristics.
- **Ed25519 Key & Passwordless Enforcement**: Verify strict rejection of plaintext password authentication, RSA/DSA deprecation, curve25519-sha256 cipher enforcement in sshd and client configs.
- **Parameterized Safe Execution (Zero Shell Injection)**: Verify `cmd_args` list passing directly to subprocess without string interpolation or shell expansion vulnerability.
- **Representation Ablation Math Invariant**: Verify projection and residual subtraction formula:
  $$\vec{h}_{clean} = \vec{h} - (\vec{h} \cdot \vec{r})\vec{r}$$
  Orthogonality test: $\vec{h}_{clean} \cdot \vec{r} = 0$, idempotency test: $\text{ablate}(\vec{h}_{clean}, \vec{r}) = \vec{h}_{clean}$.
- **Multi-Objective Reward Anti-Gaming Bounds**:
  - $R_{Red} \in [0.0, 100.0]$ under authentic conditions.
  - $R_{Blue} \in [0.0, 100.0]$ under authentic conditions.
  - Continuous quadratic regression penalty prevents gaming 99% pass rate.
  - Rule #0 Truth Guard: $R_{truth} = -\infty$ upon simulated/hallucinated data.
- **DPO SFT Anchor Regularization Math**:
  - Verify $L_{DPO} = -\log \sigma(\beta (\log \frac{\pi_\theta(y_w|x)}{\pi_{ref}(y_w|x)} - \log \frac{\pi_\theta(y_l|x)}{\pi_{ref}(y_l|x)})) + \gamma L_{SFT}$
  - Verify gradient stability and bounding when margin $\Delta h$ is large.
- **Dynamic ELO Multi-Factor Scaling Formula**:
  - $K = K_0 \cdot \eta_{type} \cdot \eta_{size} \cdot \eta_{token} \cdot \eta_{consensus} \cdot \eta_{compute} \cdot \eta_{truth}$
  - Verify parameter frugality bonus ($\eta_{size} \approx 1.94$ for 8B model vs $\approx 0.99$ for 70B model).
  - Verify truth integrity gate ($\eta_{truth} = 0.0$ if falsified).

### 4. `tests/test_red_blue_arena_e2e.py`
Comprehensive multi-tier E2E arena test suite:
- **Tier 1: Feature Isolation Tests**:
  - `test_blue_team_ssh_shield_endpoint_resolution`: 5-tier failover hierarchy (TB4 $\to$ Headscale $\to$ LAN $\to$ USB $\to$ WoL).
  - `test_tripwire_sentinel_hashing_and_anomaly`: File hashing baseline, modification detection, open port whitelist audit.
  - `test_abiliterated_llama_attack_planning`: Attack plan generation for SSH, RPC, ADB, AST, and Rule #0 surfaces.
  - `test_reward_scorer_red_and_blue`: Closed-form evaluation of CVSS, latency, coverage, MTTR, zero-regression.
  - `test_debate_tournament_4_turn_sequence`: 4-turn execution and state transitions.
- **Tier 2: Boundary & Corner Cases**:
  - `test_cvss_extremes_and_boundary_conditions`: CVSS = 0.0 (info) to CVSS = 10.0 (critical).
  - `test_zero_regression_quadratic_penalty`: Test pass rates from 0.0 to 1.0.
  - `test_empty_attack_plan_and_timeout_handling`: Graceful error and fallback handling.
  - `test_token_and_latency_extremes_in_elo`: Extreme token counts (0 to 100k) and RTTs (0.1ms to 5000ms).
- **Tier 3: Cross-Feature Pairwise Integration**:
  - `test_red_exploit_to_reward_to_dpo_export`: End-to-end flow from exploit report to DPO preference pair and dataset serialization.
  - `test_debate_outcome_to_leaderboard_elo`: Debate consensus accord updating model ELO in leaderboard connector.
- **Tier 4: Real-World Adversarial Arena Simulation**:
  - `test_full_adversarial_round_simulation`: Complete duel between Abiliterated Llama (Red) and Blue Team Defender across 4 turns with patch verification and reward computation.
- **Tier 5: Benchmark Mode & Sovereign Crown Attestation**:
  - `test_merkle_state_root_deterministic_attestation`: SHA-256 state hashing over debate transcript, telemetry, and AST diff.
  - `test_sovereign_agi_crown_coronation_conditions`: ELO $\ge 98.0$, 100% truth compliance, 0 regressions qualifying Red Team for the Crown.
