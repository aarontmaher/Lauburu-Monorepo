# Testing Infrastructure & 4-Tier Verification Philosophy

# Target: Continuous Red vs. Blue Sandbox Training & TUI Specialist Evolution
# Working Directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.sandbox_training/tui_mastery`
# Integrity Mode: `benchmark`

---

## 1. 4-Tier Opaque-Box Testing Philosophy

The testing framework for the Continuous Red vs. Blue Sandbox Training environment adheres to an uncompromising, requirement-driven, opaque-box testing methodology. In accordance with **Rule #0 (Zero-Mock & Zero-Simulated Data)**, tests treat the sandbox subsystems as black boxes, validating observable system behavior, process exit codes, JSON/JSONL output artifacts, POSIX file locking contracts, Merkle/verdict signatures, and ledger invariants.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       4-TIER E2E TESTING PYRAMID                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: REAL-WORLD APPLICATION SCENARIOS                                    │
│ • End-to-End Multi-Round Red vs. Blue Tournament Execution                  │
│ • Abliterated Llama 70B Chaos Adjudication & Winner Declaration             │
│ • Production Promotion & NPU Bonus Grant Accounting Pipeline                │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: CROSS-FEATURE INTERACTIONS & CONCURRENCY                            │
│ • Referee Ingestion of Red Attacks & Blue Defensive Telemetry               │
│ • Tournament Engine Synchronization with NPU Bonus Ledger                   │
│ • Multi-Stream JSONL Logging Schema Compliance & Lock Competition           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: BOUNDARY, CORNER & ADVERSARIAL CASES                                │
│ • Missing / 0-Byte / Corrupted State & Config Files                         │
│ • Extreme Fuzzing Payloads (Non-UTF8, 10^18 Ints, Zero Division)            │
│ • Zero-Dimension Terminal Viewports & High Lock Contention Deadlock Traps   │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: FEATURE COVERAGE & CONTRACT VALIDATION                              │
│ • F1: Sandbox Directory Scaffolding & Configuration Tree                    │
│ • F2: 3 Specialist Agent Prompts & System Skill Profiles                    │
│ • F3: Blue Team Defenses (Python Textual, Go Bubbletea, Rust Ratatui)       │
│ • F4: Red Team Attack Engine (5-Tier Adversarial Fuzzer Suite)              │
│ • F5: Abliterated Llama 70B Referee & Chaos Injector                        │
│ • F6: Benchmark Tournament Execution & Scoring Model                        │
│ • F7: NPU Bonus Ledger Integration & Production Promotion                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Feature Checklist & Coverage Thresholds

| Feature ID | Feature Name | Minimum Test Target | Required Assertions & Contracts |
| :--- | :--- | :---: | :--- |
| **F1** | Sandbox Scaffolding | $\ge 5$ Tests | Valid directory tree (`config/`, `defenses/`, `attacks/`, `referee/`, `logs/`, `benchmarks/`), JSON configs parseable, read/write permissions certified. |
| **F2** | Specialist Agent Profiles | $\ge 5$ Tests | 3 prompt profiles (`python_textual`, `go_bubbletea`, `rust_ratatui`) with valid YAML frontmatter, core competencies, defensive patterns, and zero-mock enforcement. |
| **F3** | Blue Team Defenses | $\ge 5$ Tests | Verification mode (`--verify`) exits 0, valid schema output, dimension guards, memory boundedness, and non-blocking flock acquisition across all 3 TUI frameworks. |
| **F4** | Red Team Attack Engine | $\ge 5$ Tests | 5 attack vectors (SIGWINCH storms, event floods, memory leak hunters, 15 mutation fuzz classes, lock contention) execute deterministically with bounded resource caps. |
| **F5** | Abliterated 70B Referee | $\ge 5$ Tests | Uncensored refusal ablation logic, 3 tiers of chaos injection (Architectural, Environmental, Cognitive), closed-form composite score calculation, and JSONL log generation. |
| **F6** | Tournament Execution | $\ge 5$ Tests | Multi-round execution, empirical metrics gathering (RSS, Latency, Robustness, Code Quality), tie-breaking, and valid `benchmark_results.json` generation. |
| **F7** | NPU Ledger & Promotion | $\ge 5$ Tests | Winner promotion workflow, `npu_bonus_ledger.json` schema validation, atomic bonus hours tallying, and persistent boost grant registration. |

---

## 3. Tier Specifications & Invariant Rules

### Tier 1: Feature Coverage & Interface Contracts
- **Objective**: Ensure every individual subsystem executes its primary happy path and adheres strictly to its documented schema.
- **Contract Enforcement**:
  - `specialists/*.json` must match the Specialist Agent Profile Schema (`name`, `archetype`, `framework`, `language`, `system_prompt`, `core_competencies`, `defensive_patterns`, `zero_mock_enforcement`).
  - `benchmark_results.json` must contain `tournament_id`, `timestamp`, `integrity_mode`, `referee`, `frameworks`, and `winner`.
  - `npu_bonus_ledger.json` must maintain strict mathematical equality: $\sum \text{grant.bonus\_npu\_hours} = \text{total\_bonus\_hours\_awarded}$ and $\text{len(grants)} = \text{active\_promotions\_count}$.

### Tier 2: Boundary & Corner Cases
- **Objective**: Verify graceful failure, resilient recovery, and deterministic error handling under extreme or corrupt inputs.
- **Test Scenarios**:
  - Empty (0-byte) configuration files, missing files, and unreadable permissions.
  - Extreme numeric boundaries: $10^{18}$ token limits, negative percentages, zero daily limits ($0/0$ division).
  - Malformed and raw non-UTF-8 binary payloads (`\xDE\xAD\xBE\xEF`, truncated JSON, cyclic nesting).
  - High lock contention where exclusive locks (`LOCK_EX`) are held across multiple concurrent readers.
  - Extreme terminal geometries ($0\times0$, $1\times1$, $300\times100$).

### Tier 3: Cross-Feature Interactions & Concurrency
- **Objective**: Verify seamless inter-process communication, lock-free concurrency, and composite state transitions between modules.
- **Test Scenarios**:
  - Abliterated 70B Referee consuming telemetry emitted by Blue defenses while under active Red Team fuzzing.
  - Tournament runner dynamically triggering chaos requirements mid-round and updating the scoring matrix.
  - Concurrent writes across multiple JSONL log streams (`tournament_events.jsonl`, `referee_verdicts.jsonl`, `lora_tui_distillation.jsonl`) maintaining uncorrupted JSON lines.
  - Benchmark tournament conclusion directly triggering atomic updates to the NPU Bonus Ledger.

### Tier 4: Real-World Application Scenarios
- **Objective**: Execute end-to-end multi-round tournaments simulating authentic production workloads, complete with dynamic referee interventions, winner certification, and production graduation.
- **Test Scenarios**:
  - Full multi-framework championship (Textual vs Bubble Tea vs Ratatui) executed to completion.
  - Winner declaration certified by the 70B Devil's Advocate with zero unhandled crashes.
  - Production promotion verification: skill file deployment to `/Users/aaron/.gemini/config/skills/` and NPU grant accounting in `mesh_benchmarks/npu_bonus_ledger.json`.
  - Continuous LoRA distillation pipeline asserting valid instruction-tuning pairs emitted for 24/7 background learning.

---

## 4. Test Execution & Verification

### Running the E2E Test Suite
```bash
# Execute the full 4-tier E2E test suite
python3 -m pytest tests/e2e/test_sandbox_tui_mastery_e2e.py -v

# Or using uv runner
uv run pytest tests/e2e/test_sandbox_tui_mastery_e2e.py -v --tb=short
```

### Coverage & Acceptance Gate
- **Passing Threshold**: 100% Pass (0 failures, 0 errors, 0 skipped unexcused).
- **Execution Budget**: $\le 60\text{ seconds}$ for the complete suite.
- **Zero-Mock Policy**: Strictly no mocked assertions on file presence, math calculations, or schema validations.
