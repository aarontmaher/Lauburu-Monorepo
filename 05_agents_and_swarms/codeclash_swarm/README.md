# ⚔️ CodeClash Swarm: Sovereign Adversarial Coding & AST Decompiler Engine

The **CodeClash Swarm** is an autonomous multi-round software engineering tournament engine and polyglot AST analysis framework within the **Lauburu Mesh Ecosystem**. It pits adversarial AI agents against each other in real-world programming battles:

- **Red Team (Offense Core)**: Injects realistic, syntactically valid defects (off-by-one bounds, out-of-bounds index errors, concurrency race conditions, and catastrophic backtracking ReDoS patterns).
- **Blue Team (Defense Core)**: Utilizes AST/CFG inspection, static vulnerability analysis, and synthesized unified git diffs to repair code.
- **Judicial Sentinel**: Enforces syntactic validity, calculates AST structural distance $\Delta_{\text{AST}}$, executes an **Anti-Mock Scanner (Rule #0)**, and runs sandboxed subprocess test execution.
- **Bradley-Terry Dynamic ELO Engine**: Updates model ratings via dynamic 6-factor K-scaling based on model parameters, token efficiency, consensus, latency, and truth verification.
- **Continuous LoRA Training Stream**: Streams SFT instruction records and DPO pairwise preference records with atomic POSIX file locking (`fcntl.flock`) to `04_data_and_memory/lora_datasets/codeclash_swe_training.jsonl`.
- **Live Obsidian Leaderboard**: Dynamically synchronizes rankings, win rates, and AST pass percentages to `obsidian_vault/04_ANALYTICS/CODECLASH_LEADERBOARD_2026.md`.
- **Rule 6.3 Fast-Path Tri-Vault Invariant**: Validates storage health across Obsidian vault, PySpark data lake, and host disk headroom in $<3\text{ ms}$.

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CODECLASH ADVERSARIAL TOURNAMENT CYCLE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ CLEAN SOURCE CODE & BASE TEST SUITE ]                                   │
│                     │                                                       │
│                     ▼                                                       │
│   ┌───────────────────────────────────┐                                     │
│   │ PHASE 1: RED TEAM INJECTION       │                                     │
│   │ • Bug Injection (Off-by-one, OOB) │                                     │
│   │ • Concurrency Mutex Strip         │                                     │
│   │ • ReDoS Backtracking Injection    │                                     │
│   └─────────────────┬─────────────────┘                                     │
│                     │ (Poisoned AST / Corrupted Source)                     │
│                     ▼                                                       │
│   ┌───────────────────────────────────┐                                     │
│   │ PHASE 2: BLUE TEAM DEFENSE        │                                     │
│   │ • AST / CFG Decompilation         │                                     │
│   │ • Static Anomaly & Vulnerability  │                                     │
│   │ • Patch Synthesis & Diff Creation │                                     │
│   └─────────────────┬─────────────────┘                                     │
│                     │ (Synthesized Candidate Patch Diff)                    │
│                     ▼                                                       │
│   ┌───────────────────────────────────┐                                     │
│   │ PHASE 3: JUDICIAL AST VALIDATOR   │                                     │
│   │ • Python AST & Syntax Check       │                                     │
│   │ • CFG Structural Equivalence      │                                     │
│   │ • Zero-Mock Truth Audit Sentinel  │                                     │
│   └─────────────────┬─────────────────┘                                     │
│                     │ (Validated Clean Source)                              │
│                     ▼                                                       │
│   ┌───────────────────────────────────┐                                     │
│   │ PHASE 4: SANDBOXED TEST RUNNER    │                                     │
│   │ • Isolated Pytest Exec Subprocess │                                     │
│   │ • Exit Code, Latency, Assertions  │                                     │
│   │ • Regression Verification         │                                     │
│   └─────────────────┬─────────────────┘                                     │
│                     │ (Test Suite & Metric Payloads)                        │
│                     ▼                                                       │
│   ┌───────────────────────────────────┐                                     │
│   │ PHASE 5: ADJUDICATION & SCORING   │                                     │
│   │ • Bradley-Terry ELO Calculations  │                                     │
│   │ • Dynamic Multi-Factor K-Factor   │                                     │
│   │ • ELO Promotion & Degradation     │                                     │
│   └─────────────────┬─────────────────┘                                     │
│                     │                                                       │
│         ┌───────────┴───────────┐                                           │
│         ▼                       ▼                                           │
│ [ CONTINUOUS LORA SINK ]  [ TRI-VAULT LEADERBOARDS ]                        │
│ • SFT Instruction Record  • Obsidian CODECLASH_LEADERBOARD_2026.md          │
│ • DPO Pairwise Record     • TUI Tab 4 Structural AST Metrics                │
│ • Atomic POSIX flock      • Canonical JSON Ledger                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Mathematical Bradley-Terry ELO Formulations

### 1. Expected Win Probability
$$P(A > B) = \frac{1}{1 + 10^{(R_B - R_A)/400.0}}, \quad P(B > A) = 1.0 - P(A > B)$$

### 2. Dynamic 6-Factor K-Scaling
$$K = K_0 \cdot \eta_{\text{type}} \cdot \eta_{\text{size}} \cdot \eta_{\text{token}} \cdot \eta_{\text{consensus}} \cdot \eta_{\text{compute}} \cdot \eta_{\text{truth}}$$

Where:
- **Base $K_0$**:
  $$K_0 = \begin{cases} 48.0 & \text{if } N_{\text{matches}} < 10 \\ 32.0 & \text{if } 10 \le N_{\text{matches}} < 50 \\ 24.0 & \text{if } N_{\text{matches}} \ge 50 \end{cases}$$
- **Match Type Multiplier $\eta_{\text{type}}$**:
  $$\eta_{\text{type}} = \begin{cases} 1.00 & \text{for standard Arena Duel} \\ 1.20 & \text{for Multi-Round Tournament} \\ 1.50 & \text{for SWE-bench Regression Challenge} \end{cases}$$
- **Parameter Efficiency $\eta_{\text{size}}$**:
  $$\eta_{\text{size}} = \max\left(0.50, \min\left(2.50, \frac{\log_2(70.0 + 1.0)}{\log_2(\text{params\_b} + 1.0)}\right)\right)$$
- **Token Economy $\eta_{\text{token}}$**:
  $$\eta_{\text{token}} = \max\left(0.50, \min\left(1.50, \frac{2048}{\max(1, \text{tokens\_used})}\right)\right)$$
- **Compute Latency Multiplier $\eta_{\text{compute}}$**:
  $$\eta_{\text{compute}} = \max\left(0.70, \min\left(1.30, \frac{100.0}{\text{rtt\_ms} + 30.0}\right)\right)$$
- **Rule #0 Truth Compliance Factor $\eta_{\text{truth}}$**:
  $$\eta_{\text{truth}} = \begin{cases} 1.00 & \text{if zero mock violations and 100\% verified} \\ 0.00 & \text{if mock/simulated data detected (match annulled)} \end{cases}$$

---

## ⚡ CLI Reference

### 1. Run Multi-Round Tournament
```bash
# Execute 3-match tournament and update rankings + LoRA stream + Obsidian leaderboard
python3 codeclash_arena_engine.py --tournament-rounds 3
```

### 2. Execute a Single Head-to-Head Duel
```bash
python3 codeclash_arena_engine.py --duel --red-model qwen2.5-7b-abliterated --blue-model qwen2.5-coder-32b --task swe_algo_001
```

### 3. Verify Tri-Vault Storage Invariant (<3ms)
```bash
python3 codeclash_arena_engine.py --verify-tri-vault
```

### 4. Display Current ELO Leaderboard
```bash
python3 codeclash_arena_engine.py --leaderboard
```

---

## 🧪 Testing & Verification

Run the comprehensive test suite:
```bash
pytest tests/test_codeclash_arena_engine.py -v
pytest tests/test_ast_analysis_specialist.py -v
pytest tests/test_codeclash_swarm_e2e.py -v
```

100% genuine execution, zero simulated or mock arrays (Rule #0 compliant).
