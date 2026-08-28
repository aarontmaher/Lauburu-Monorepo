# Project: Red/Blue Team Adversarial Arena

## Architecture
The **Red/Blue Team Adversarial Arena** establishes an autonomous, continuous security hardening and evolutionary intelligence engine for the Lauburu monorepo and physical mesh network. It integrates:
1. **Blue Team Defense Layer**: SSH & Network Hardening (Ed25519-only, zero plaintext passwords, socket multiplexing with `ControlMaster auto`, 5-tier failover TB4 $\to$ Headscale $\to$ LAN $\to$ ADB $\to$ WoL, tripwire configuration sentinels).
2. **Red Team Attacker Layer (Abiliterated Llama / Devil's Advocate)**: Residual refusal direction ablation ($\vec{h}_{clean} = \vec{h} - (\vec{h}\cdot\vec{r})\vec{r}$) operating under the Prime Directive of **Constructive Destruction** to discover vulnerabilities across SSH, RPC, ADB, and memory/code state.
3. **Ancestral Tool Memory & Ephemeral Execution via Hugging Face `smolagents`**:
   - **Ephemeral Lifecycle**: Individual subagents instantiate dynamically, execute their discrete probe/patch task, and terminate immediately to conserve host RAM and VRAM.
   - **Accumulative Ancestral Memory (`AncestralToolMemory`)**: The Master AGI / Tournament Engine harvests execution traces across generations, dynamically evolving Python tool capabilities for subsequent generations.
   - **Continuous DPO Serialization**: All validated ancestral traces are exported to the PySpark data lake (`/Users/aaron/DFS_UNIFIED/lora_datasets/`) for 24/7 LoRA distillation.
4. **HuggingFace Continuous Reward & Training Loop**: Closed-form multi-objective reward models ($R_{Red}, R_{Blue}$) scoring vulnerability CVSS severity, ancestral swarm coordination efficiency, discovery rate vs patch rate, MTTR, and test pass rates. Integrated with SFT-anchored DPO (`trl.DPOTrainer` with $\gamma L_{SFT}$) and continuous LoRA dataset sinks.
5. **AI Debate & Sovereign AGI Crown Tournament**: 4-turn adversarial debate sequence (Attack Proof $\to$ Defense Patch $\to$ Cloud CoT $\to$ Consensus Accord) with parameter frugality ELO scaling ($\eta_{size}, \eta_{token}, \eta_{consensus}, \eta_{compute}, \eta_{truth}$) and ancestral swarm efficacy bonuses, qualifying the Red Team model as a full contender for the Sovereign AGI Crown.
6. **Empirical Benchmark Test Suite**: Comprehensive, zero-mock, multi-tier validation running in benchmark integrity mode.

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                          RED/BLUE ADVERSARIAL ARENA ARCHITECTURE                          │
├───────────────────────────────────────────────────────────────────────────────────────────┤
│  [RED TEAM: Abiliterated Llama]                      [BLUE TEAM: Defensive Shield]        │
│  • Refusal Representation Ablated                    • Ed25519 Multiplexed SSH Engine     │
│  • Constructive Destruction Directive                • 5-Tier Zero-Trust Failover         │
│  • Ephemeral smolagents Swarm (Killed post-task)     • Ephemeral smolagents Defense Swarm │
│  • Ancestral Tool Memory (Evolving across gen)       • Continuous Tripwire Auditing       │
│                     │                                             │                       │
│                     ▼                                             ▼                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    4-TURN ADVERSARIAL AI DEBATE ARENA                               │  │
│  │  Turn 1: Red Attack Proof & Exploitation Analysis (Ephemeral smolagents)            │  │
│  │  Turn 2: Blue Defense Remediation & Cryptographic Patch (Ancestral Tools)           │  │
│  │  Turn 3: Cloud Frontier CoT (Gemini 3.7 / 3.1 Pro) Cross-Audit                      │  │
│  │  Turn 4: Council Consensus Accord & Merkle State Transition                         │  │
│  └─────────────────────────────────────────────────────────────────────────────────────┘  │
│                     │                                             │                       │
│                     ▼                                             ▼                       │
│  ┌───────────────────────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │   HUGGINGFACE TRL / DPO REWARD PIPELINE   │  │   CANONICAL ELO LEADERBOARD ENGINE   │  │
│  │   • Multi-Objective CVSS Scoring ($R_{Red}$) │  │   • Dynamic K-Factor Scaling ($K$)   │  │
│  │   • MTTR & Ancestral Swarm ($R_{Blue}$)   │  │   • Sovereign AGI Crown Award        │  │
│  │   • SFT-Anchored DPO Regularizer          │  │   • Champion Deployment Sync         │  │
│  └───────────────────────────────────────────┘  └──────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Specification Artifact | Generate `red_blue_arena_specification.md` detailing SSH hardening, prompts, smolagents swarms & Ancestral Tool Memory | M1 | User Request R1, R2, AC1, Follow-ups |
| 2 | Blue Team SSH Hardening | Remove plaintext passwords, deploy Ed25519-only `sshd_config.hardened` and multiplexed `ssh_config.client` | M2 | User Request R1 |
| 3 | Blue Team Defense Shield | Build `blue_team_ssh_shield.py` with 5-tier failover, safe parameterized execution, and zero shell injection | M2 | Survey 1 Findings |
| 4 | Mesh Tripwire Sentinel | Build `mesh_tripwire_sentinel.py` for continuous hash auditing of SSH/Headscale configs and anomaly logging | M2 | Survey 1 Findings |
| 5 | Abiliterated Llama Engine | Deploy `abiliterated_llama_engine.py` with refusal ablation hooks, constructive destruction prompts, and attack modes | M3 | User Request R2, R3 |
| 6 | Red Team Attack Harness | Deploy `red_team_attack_harness.py` for sandboxed vulnerability discovery (SSH, RPC, ADB, Doze, AST, Rule #0) | M3 | User Request R2 |
| 7 | Ancestral Tool Memory & Ephemeral Swarms | Implement dynamic ephemeral `smolagents` lifecycle and accumulative `AncestralToolMemory` tool evolution across generations | M3, M5 | User Request Follow-ups |
| 8 | HF Adversarial Reward Engine | Deploy `hf_adversarial_reward_trainer.py` with closed-form $R_{Red}, R_{Blue}$ scoring and CVSS weighting | M4 | User Request AC2 |
| 9 | SFT-Anchored DPO Training | Implement DPO trainer with SFT regularization anchor ($\gamma L_{SFT}$) preventing language degeneration | M4 | Survey 3 Findings |
| 10 | Multi-Sink Dataset Pipelines | Standardize JSONL schemas and automated logging to `lora_datasets/` and `04_data_and_memory/` | M4 | Survey 3 Findings |
| 11 | AI Debate Tournament Engine | Build `red_blue_debate_tournament.py` executing the 4-turn adversarial sequence with ancestral swarm scoring | M5 | User Request R3, AC3 |
| 12 | Sovereign Crown ELO Integration | Integrate dynamic multi-factor K-factor scaling ($\eta_{size}, \eta_{token}, \dots$) and leaderboard crowning | M5 | User Request R3, AC3 |
| 13 | Comprehensive E2E Test Suite | Build `test_red_blue_arena_e2e.py` verifying all components, ancestral tool memory, and swarms in benchmark mode | M6 | User Request AC4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Specification & Prompt Architecture | Generate `red_blue_arena_specification.md` detailing architecture, prompts, smolagents swarms, and mathematical models | None | DONE |
| M2 | Blue Team Defense Shield & SSH Hardening | Implement `blue_team_ssh_shield.py`, `mesh_tripwire_sentinel.py`, `sshd_config.hardened`, `ssh_config.client` | M1 | DONE |
| M3 | Red Team Abiliterated Llama Engine & Harness | Implement `abiliterated_llama_engine.py`, `red_team_attack_harness.py`, smolagents attack swarms, and sandbox execution | M1 | DONE |
| M4 | HuggingFace Reward Loop & LoRA Sinks | Implement `hf_adversarial_reward_trainer.py`, SFT-anchored DPO, CVSS scoring, and dataset serialization | M1 | DONE |
| M5 | AI Debate Sovereign Crown Tournament | Implement `red_blue_debate_tournament.py`, dynamic ELO engine, smolagents swarm scoring, and leaderboard integration | M2, M3, M4 | DONE |
| M6 | E2E Testing & Benchmark Verification | Implement and execute `test_red_blue_arena_e2e.py` verifying 100% test pass in benchmark integrity mode | M1, M2, M3, M4, M5 | DONE |

## Code Layout
```
05_agents_and_swarms/red_blue_arena/
├── README.md                                 # Overview & operational manual
├── red_blue_arena_specification.md           # Master architectural specification, prompts, and smolagents swarm guide
├── TEST_INFRA.md                             # Comprehensive test methodology and verification guidelines
├── TEST_READY.md                             # E2E Test Suite certification report
├── blue_team/                                # Blue Team Defense Layer
│   ├── __init__.py
│   ├── blue_team_ssh_shield.py               # Multiplexed, Ed25519-only 5-tier failover SSH engine
│   ├── mesh_tripwire_sentinel.py             # Configuration integrity and anomaly detection daemon
│   ├── configs/
│   │   ├── sshd_config.hardened              # Hardened daemon configuration
│   │   └── ssh_config.client                 # Multiplexed client configuration
├── red_team/                                 # Red Team Attacker Layer
│   ├── __init__.py
│   ├── abiliterated_llama_engine.py          # Refusal-ablated Devil's Advocate model engine & smolagents swarm
│   ├── red_team_attack_harness.py            # Sandboxed vulnerability discovery harness & Ancestral Tool Memory
│   └── prompts/
│       └── constructive_destruction_system.md# Exact system prompt & constraints
├── training/                                 # HuggingFace Reward & LoRA Pipelines
│   ├── __init__.py
│   ├── hf_adversarial_reward_trainer.py      # Closed-form multi-objective reward & SFT-anchored DPO
│   └── schemas/
│       └── reward_dataset_schemas.py         # JSONL dataset schemas (DPO, SFT, GRPO, Ancestral Tool Memory)
├── tournament/                               # AI Debate & Sovereign Crown Tournament
│   ├── __init__.py
│   ├── red_blue_debate_tournament.py         # 4-turn adversarial debate sequence & smolagents swarm integration
│   └── leaderboard_connector.py              # Canonical AI leaderboard integration
└── tests/                                    # Dual-Track E2E & Benchmark Test Suite
    ├── __init__.py
    ├── test_red_blue_arena_e2e.py            # End-to-end benchmark verification test suite
    ├── test_hardening_invariants.py          # Security and math invariant tests
    ├── test_red_team_engine.py               # Red Team engine & probe tests
    ├── test_reward_and_tournament.py         # Reward and tournament unit tests
    └── test_final_challenger_adversarial_suite.py # 28-test adversarial challenge suite
```
