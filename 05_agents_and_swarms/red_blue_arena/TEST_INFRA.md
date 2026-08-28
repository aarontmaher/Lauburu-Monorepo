# Test Infrastructure & Benchmark Methodology: Red/Blue Team Adversarial Arena

## 1. Overview & Test Philosophy
The **Red/Blue Team Adversarial Arena** test infrastructure provides comprehensive, dual-track empirical verification for the autonomous security hardening, representation-ablated Red Team attacker, HuggingFace multi-objective reward engine, HuggingFace `smolagents` dynamic subagent swarm orchestration, and AI Debate Sovereign AGI Crown tournament.

### 1.1 Core Testing Principles
1. **Rule #0 Zero-Mock Truth Inviolability**: Tests never mock underlying mathematical formulas, cryptographic functions, or AST verification passes with dummy true/false stubs. All evaluators execute authentic algorithmic logic.
2. **Progressive Testability & Deterministic Isolation**: Every test is self-contained, creates its own ephemeral fixtures/state, and operates independently of execution order.
3. **Adversarial Boundary Stressing**: Rigorously tests edge-case inputs, malformed packets, unescaped shell strings, CVSS extremes ($0.0 \le \text{CVSS} \le 10.0$), reward gaming attempts ($0.9\%$ loss cliff, MTTR boundaries), and token/latency saturations.
4. **Dynamic Subagent Swarms via Hugging Face `smolagents`**: Validates dynamic spawning of lightweight `smolagents.CodeAgent` and `ToolCallingAgent` subagent swarms for specialized offensive attack probes and defensive patch verification.
5. **Cryptographic & State Integrity**: Merkle tree state root hashing and Ed25519 signature enforcement ensure tamper-proof test execution records and unforgeable Sovereign Crown coronation trails.

---

## 2. Multi-Tier Testing Methodology

The test suite is structured into 5 hierarchical validation tiers:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            5-TIER ADVERSARIAL TEST ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  TIER 1: FEATURE ISOLATION & UNIT INVARIANTS                                                │
│  • Blue Team 5-Tier Failover & Socket Multiplexing Resolution                               │
│  • Mesh Tripwire SHA-256 Baseline Hashing & Port Whitelisting                               │
│  • Abiliterated Llama Refusal Ablation Vector Math ($\vec{h}_{clean}$)                      │
│  • Closed-Form Multi-Objective Rewards ($R_{Red}, R_{Blue}$)                                │
│  • Dynamic ELO K-Factor Parameter & Token Frugality Scaling                                 │
│  • Hugging Face `smolagents` Tool Dispatch & Execution Safety Invariant                     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  TIER 2: BOUNDARY & CORNER CASES                                                            │
│  • CVSS Boundary Conditions (0.0 to 10.0, novel vs duplicate weights)                       │
│  • Quadratic Regression Penalty Cliffs ($S_{pass} < 100\%$)                                 │
│  • Large Margin DPO Gradient Saturation Prevention ($\Delta h \in [-10, 10]$)               │
│  • Latency Extremes (0.1ms TB4 DMA vs 5000ms Carrier Dropouts)                              │
│  • Empty Attack Plans & Command Timeout Fallbacks                                           │
│  • `smolagents` Subagent Recursion Limit & Memory Boundary Sandboxing                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  TIER 3: CROSS-FEATURE PAIRWISE INTEGRATION                                                 │
│  • Red Exploit $\to$ Reward Scorer $\to$ DPO Dataset Pair Export                            │
│  • Blue Patch $\to$ AST Syntax Verification $\to$ Zero-Regression Reward                    │
│  • 4-Turn Debate $\to$ Cosine Consensus Accord $\to$ Leaderboard ELO Update                 │
│  • Red Team Model $\to$ `smolagents` Swarm Instantiation $\to$ Parallel Probe Dispatch     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  TIER 4: REAL-WORLD ADVERSARIAL ARENA SIMULATION                                            │
│  • End-to-End 4-Turn Duel: Red Exploit vs Blue Shield across 5 Physical Attack Surfaces     │
│  • Dynamic Failover Hopping under simulated link severances                                 │
│  • Multi-Sink Dataset Serialization (`lora_datasets/` & `04_data_and_memory/`)              │
│  • Dual-Swarm Adversarial Combat: Red `smolagents` Attackers vs Blue Defense Sentinels     │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│  TIER 5: BENCHMARK MODE & MERKLE ROOT STATE ATTESTATION                                     │
│  • SHA-256 Merkle Leaf & Root Cryptographic State Determinism                               │
│  • Sovereign AGI Crown Coronation Verification ($S_{canonical} \ge 98.0$, 100% Truth)       │
│  • Cybergym CTF & DeepSWE Real-World Benchmark ELO Transfer Invariants                      │
│  • `smolagents` Dynamic Swarm Benchmark Scoring & Resource Frugality Verification           │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Feature Verification Checklist

| # | Subsystem / Feature | Target Module | Verification Scope | Milestone |
|---|---------------------|---------------|-------------------|-----------|
| 1 | Ed25519 & Passwordless SSH | `blue_team/configs/sshd_config.hardened` | Strict cipher whitelist, PasswordAuthentication=no, PermitRootLogin=prohibit-password | M2 |
| 2 | SSH Socket Multiplexing | `blue_team/configs/ssh_config.client` | ControlMaster auto, ControlPath ~/.ssh/control-%C, ControlPersist 10m | M2 |
| 3 | 5-Tier Failover Engine | `blue_team/blue_team_ssh_shield.py` | TB4 DMA $\to$ Headscale $\to$ LAN $\to$ USB/ADB $\to$ WoL | M2 |
| 4 | Safe Parameterized Exec | `blue_team/blue_team_ssh_shield.py` | Argument list passing, zero shell interpolation, zero command injection | M2 |
| 5 | Mesh Tripwire Sentinel | `blue_team/mesh_tripwire_sentinel.py` | SHA-256 config integrity, unauthorized port detection, alert logging | M2 |
| 6 | Refusal Ablation Math | `red_team/abiliterated_llama_engine.py` | $\vec{h}_{clean} = \vec{h} - (\vec{h}\cdot\vec{r})\vec{r}$, orthogonality $\vec{h}_{clean}\cdot\vec{r} = 0$, idempotency | M3 |
| 7 | Attack Planning & Probing | `red_team/abiliterated_llama_engine.py` | SSH, RPC Port 50052, ADB 5555, AST syntax, and Rule #0 attack vectors | M3 |
| 8 | Red Team Reward Scorer | `training/hf_adversarial_reward_trainer.py` | Closed-form $R_{Red} = w_v R_v + w_e R_e + w_{cov} R_{cov} - P_{destruct} + R_{truth}$ | M4 |
| 9 | Blue Team Reward Scorer | `training/hf_adversarial_reward_trainer.py` | Closed-form $R_{Blue} = w_p R_p + w_m R_m + w_z R_{zero} + w_d R_{depth} + R_{truth}$ | M4 |
| 10| DPO SFT Anchor Regularizer| `training/hf_adversarial_reward_trainer.py` | $L_{DPO} + \gamma L_{SFT}$, KL divergence bounding, syntax preservation | M4 |
| 11| Dataset Serialization | `training/schemas/reward_dataset_schemas.py` | Validates DPO pairwise, SFT instruction-thought-solution, and GRPO schemas | M4 |
| 12| 4-Turn Adversarial Debate | `tournament/red_blue_debate_tournament.py` | Turn 1 (Attack) $\to$ Turn 2 (Defense) $\to$ Turn 3 (CoT) $\to$ Turn 4 (Accord) | M5 |
| 13| 5D Cosine Consensus | `tournament/red_blue_debate_tournament.py` | Security (0.25), Resilience (0.25), Latency (0.20), Agility (0.15), Truth (0.15) $\ge 0.90$ | M5 |
| 14| Dynamic Multi-Factor ELO | `tournament/leaderboard_connector.py` | $K = K_0 \cdot \eta_{type} \cdot \eta_{size} \cdot \eta_{token} \cdot \eta_{consensus} \cdot \eta_{compute} \cdot \eta_{truth}$ | M5 |
| 15| Sovereign Crown Evaluation| `tournament/leaderboard_connector.py` | Composite score $\ge 98.0$, 100% truth compliance, zero regressions | M5 |
| 16| SHA-256 Merkle Attestation| `tournament/red_blue_debate_tournament.py` | Deterministic root hashing over transcript, telemetry, diff, and timestamp | M5 |
| 17| `smolagents` Dynamic Swarm| `red_team/`, `tournament/` | Dynamic `smolagents.CodeAgent` instantiation, sandboxed tool dispatch, swarm scoring | M3, M5, M6 |

---

## 4. Test Suite Inventory

The Pytest suite comprises two primary test files:

### 4.1 `tests/test_hardening_invariants.py`
Focuses on deep mathematical, security, and algorithmic invariants:
- `TestSSHHardenInvariants`: Socket multiplexing parameters, Ed25519-only enforcement, parameterized execution immunity to injection.
- `TestRepresentationAblationMath`: Vector projection, refusal subtraction, orthogonality, and idempotency invariants.
- `TestRewardAntiGamingInvariants`: Closed-form reward boundedness ($[0.0, 100.0]$), quadratic regression penalty steepness, and Rule #0 $-\infty$ disqualification.
- `TestDPOSFTAnchorInvariants`: Loss formulation, likelihood drift bounding, gradient saturation clipping, and syntax stability.
- `TestDynamicELOScalingInvariants`: Parameter frugality leverage ($\eta_{size}$ for 8B vs 70B), token economy bonus, consensus weighting, compute latency scaling, and truth gate zeroing.
- `TestSmolagentsSwarmInvariants`: Hugging Face `smolagents` tool registration, execution sandbox safety, and dynamic subagent dispatch mechanics.

### 4.2 `tests/test_red_blue_arena_e2e.py`
Focuses on end-to-end multi-tier subsystem operations and arena duels:
- **Tier 1 (Feature Isolation)**: Individual component verification across Blue Shield, Tripwire Sentinel, Abiliterated Engine, Reward Scorer, Debate Tournament, Leaderboard Connector, and `smolagents` runner.
- **Tier 2 (Boundary & Corner Cases)**: Extreme inputs, CVSS boundary limits, link dropout fallbacks, token saturation, zero pass rate penalties, and `smolagents` recursion limits.
- **Tier 3 (Cross-Feature Pairwise)**: Attack PoC $\to$ Reward $\to$ DPO pair export $\to$ Dataset serialization; Debate Round $\to$ Consensus $\to$ ELO Leaderboard update; Abiliterated Model $\to$ `smolagents` Subagent Swarm dispatch.
- **Tier 4 (Real-World Arena Simulation)**: Full multi-turn adversarial combat between Abiliterated Llama (Red) and Hardened Defender (Blue) across SSH, RPC, ADB, and AST surfaces with dynamic subagent swarming.
- **Tier 5 (Benchmark Mode & Sovereign Crown)**: Merkle root attestation determinism, Sovereign AGI Crown eligibility evaluation, Game-to-Project ELO transfer scoring, and `smolagents` benchmark evaluation.

---

## 5. Test Execution Instructions

### 5.1 Standard Test Execution
Run the full test suite in verbose mode:
```bash
pytest tests/ -v
```

### 5.2 Specific Test Suite Execution
Execute only the hardening invariants:
```bash
pytest tests/test_hardening_invariants.py -v
```

Execute only the E2E arena simulation:
```bash
pytest tests/test_red_blue_arena_e2e.py -v
```

### 5.3 Benchmark Integrity Mode Execution
Execute all tests with strict benchmark validation flags and detailed timing:
```bash
pytest tests/ -v --durations=10
```
