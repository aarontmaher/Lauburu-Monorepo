# Project: Continuous Red vs. Blue Sandbox Training & TUI Specialist Evolution

## Architecture
A Continuous Red vs. Blue Sandbox Training environment overseen by Abliterated Llama 70B (Devil's Advocate) to rapidly evolve, benchmark, and distill three polyglot TUI specialist AI agents:
1. `polyglot-python-textual-specialist` (Python Textual / Rich)
2. `polyglot-go-bubbletea-specialist` (Go Bubble Tea / Lipgloss)
3. `polyglot-rust-ratatui-specialist` (Rust Ratatui / Crossterm)

Target Sandbox Directory: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.sandbox_training/tui_mastery`
Integrity Mode: `benchmark`

### Architectural Pillars:
1. **Blue Team Unbounded Creative Defenses**: Robust, memory-bounded, asynchronous, zero-mock TUI dashboards implementing lock-free backoff, SIGWINCH resilience, panic-recovery boundaries, and rich visualizations (live Sparklines, Real-Time Hardware Gauges, Multi-Screen Tabs, AST Visualizers, Mesh Telemetry).
2. **Red Team Attack Engine**: 5-tier adversarial stress fuzzer (SIGWINCH storms, event floods, memory exhaustion, schema mutations, lock contention).
3. **Abliterated Llama 70B Referee & Creative ELO Judge**: Uncensored Devil's Advocate referee enforcing Constructive Destruction, evaluating unbounded creative features, injecting dynamic chaos requirements, computing multi-factor composite scores ($S_{\text{composite}}$ + Creative Innovation ELO Boost), and generating structured JSONL logs (`tournament_events.jsonl`, `referee_verdicts.jsonl`, `lora_tui_distillation.jsonl`).
4. **Production Promotion & NPU Ledger Accounting**: Automated promotion of winning framework & specialist, with NPU Bonus Grant logged to `mesh_benchmarks/npu_bonus_ledger.json`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Sandbox Scaffolding | Initialize `.sandbox_training/tui_mastery` directory tree (`config/`, `attacks/`, `defenses/`, `referee/`, `logs/`, `benchmarks/`) | M1 | Survey |
| F2 | Specialist Agent Prompt Profiles | Develop and test prompt profiles & system messages for Textual, Bubble Tea, and Ratatui specialists in `.sandbox_training/tui_mastery/config/specialists/` and `/Users/aaron/.gemini/config/skills/` | M1 | Survey |
| F3 | Blue Team Creative Defenses | Build & optimize robust TUI components in Python Textual, Go Bubbletea, and Rust Ratatui with unbounded creative visualizations | M2 | User Directive |
| F4 | Red Team Attack Engine | Implement 5-tier adversarial fuzzer (SIGWINCH storms, 1k event/s flood, memory leak stressor, 15-class mutation corpus, flock contention) in `.sandbox_training/tui_mastery/attacks/` | M2 | Survey |
| F5 | Abliterated Llama 70B Referee & ELO Judge | Implement uncensored referee with refusal ablation, creative feature evaluation & ELO boost, 3-tier chaos injection, composite scoring, and JSONL logging | M2 | User Directive |
| F6 | Benchmark Tournament Execution | Run multi-round Red vs Blue tournament across all 3 frameworks, collecting empirical RSS, latency, robustness, creative ELO, and code quality metrics | M3 | User Directive |
| F7 | Production Promotion & NPU Ledger | Promote winning framework & specialist, grant NPU Bonus Hours and update `mesh_benchmarks/npu_bonus_ledger.json` | M3 | Survey |
| F8 | E2E Testing Track | Independent 4-tier opaque-box test suite verifying all acceptance criteria, log schemas, creative ELO grading, and ledger entries | M-E2E | Survey |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Sandbox Infrastructure & Specialist Profiles | F1 (Directory scaffolding), F2 (3 Specialist Agent Prompts & Skills) | None | DONE |
| M2 | Red vs Blue Arena & Abliterated 70B Referee | F3 (Creative Blue Defenses), F4 (Red Attack Engine), F5 (70B Referee & ELO Judge) | M1 | IN_PROGRESS |
| M3 | Tournament Execution, Promotion & NPU Ledger | F6 (Benchmark Tournament Run), F7 (Winner Promotion & Ledger Grant) | M2 | PLANNED |
| M-E2E | E2E Testing Track | F8 (4-Tier E2E Test Suite & Test Runner) | None | DONE |
| M-FINAL | Final Verification & Victory Audit | 100% E2E Pass, Forensic Integrity Audit CLEAN, Victory Report | M3, M-E2E | PLANNED |
