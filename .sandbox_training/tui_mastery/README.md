# Continuous Red vs. Blue Sandbox Training — TUI Mastery & Specialist Evolution

Welcome to the **TUI Mastery Sandboxed Agent Arena**, a high-velocity Red vs. Blue evolutionary training environment governed by the **Abliterated Llama 70B (Devil's Advocate)**.

This sandbox operates in `benchmark` integrity mode to develop, stress-test, benchmark, and distill three polyglot Terminal User Interface (TUI) specialist AI agents:
1. **Python Textual Specialist** (`polyglot-python-textual-specialist`)
2. **Go Bubble Tea Specialist** (`polyglot-go-bubbletea-specialist`)
3. **Rust Ratatui Specialist** (`polyglot-rust-ratatui-specialist`)

---

## 🏛️ Architectural Pillars

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ABLITERATED LLAMA 70B DEVIL'S ADVOCATE                      │
│       • Uncensored Rules of Engagement  • Dynamic Chaos Spec Injection      │
│       • Multi-Factor Fitness Scoring    • Structured JSONL Audit Logging    │
└──────────────────────┬───────────────────────────────┬──────────────────────┘
                       │                               │
                       ▼                               ▼
       ┌───────────────────────────────┐ ┌───────────────────────────────┐
       │       BLUE TEAM DEFENSES      │ │       RED TEAM FUZZERS        │
       │ • Python Textual (TCSS/Async) │ │ • SIGWINCH Storms (1,000 res) │
       │ • Go Bubble Tea (Elm/Bubbles) │ │ • Telemetry Torrents (100k)   │
       │ • Rust Ratatui (Tokio/Cross)  │ │ • Memory Pressure & ANSI Fuzz │
       │ • Zero-Mock Telemetry Binding │ │ • Socket Hangs & Spec Shifts  │
       └───────────────────────────────┘ └───────────────────────────────┘
                       │                               │
                       └───────────────┬───────────────┘
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │             EVALUATION, PROMOTION & NPU LEDGER                │
       │ • Composite Scoring S_composite = 0.25Mem+0.25Lat+0.30Rob+0.20│
       │ • Production Skill Deployment to ~/.gemini/config/skills/     │
       │ • Automated NPU Bonus Grant to npu_bonus_ledger.json          │
       └───────────────────────────────────────────────────────────────┘
```

1. **Blue Team Defenses**: Builds modular, robust, non-blocking TUI dashboards across Python (Textual), Go (Bubble Tea), and Rust (Ratatui). Defenses incorporate bounded ring buffers, zero-allocation render passes, and fail-safe panic recovery.
2. **Red Team Attack Engine**: Executes a 10-tier adversarial stress suite including SIGWINCH resize storms, unthrottled event torrents, malformed UTF-8/ANSI byte sequences, PTY key spam, and socket disconnects.
3. **Abliterated Llama 70B Referee**: Operates with refusal ablation to ruthlessly challenge implementations, dynamically mutating requirements mid-tournament, and calculating empirical composite fitness scores.
4. **Production Promotion & NPU Accounting**: Automates the promotion of surviving framework implementations to `01_apps/` and awards NPU bonus grants in `02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json`.

---

## 📁 Directory Structure

```
.sandbox_training/tui_mastery/
├── config/
│   ├── tournament_config.json        # Master tournament parameters & scoring weights
│   └── specialists/
│       ├── python_textual.json       # Python Textual Specialist prompt profile
│       ├── go_bubbletea.json         # Go Bubble Tea Specialist prompt profile
│       └── rust_ratatui.json         # Rust Ratatui Specialist prompt profile
├── defenses/
│   ├── python_textual/               # Blue team Python Textual defense component
│   ├── go_bubbletea/                 # Blue team Go Bubble Tea defense component
│   └── rust_ratatui/                 # Blue team Rust Ratatui defense component
├── attacks/
│   ├── sigwinch_storm.py             # 1,000 rapid resize cycles fuzzer
│   ├── event_flood.py                # 100,000 events/sec socket stream fuzzer
│   ├── memory_stressor.py            # Memory pressure & heap allocation stressor
│   ├── schema_fuzzer.py              # Malformed ANSI / UTF-8 mutation corpus
│   └── lock_contention.py            # Multi-threaded mutex/state contention fuzzer
├── referee/
│   ├── abliterated_referee.py        # Devil's Advocate referee logic
│   ├── scoring_matrix.py             # Multi-factor S_composite scoring calculator
│   └── chaos_injector.py             # Dynamic requirement & spec mutator
├── logs/
│   ├── tournament_events.jsonl       # High-frequency tournament telemetry log
│   ├── referee_verdicts.jsonl        # Abliterated 70B round verdicts & decisions
│   ├── lora_tui_distillation.jsonl   # Continuous LoRA instruction training dataset
│   └── dpo_tui_preferences.jsonl     # DPO preference pairs (chosen vs rejected)
├── benchmarks/
│   ├── run_tournament.py             # Main tournament execution script
│   └── benchmark_results.json        # Canonical tournament output artifact
└── README.md
```

---

## 📊 Benchmark Evaluation Metrics ($S_{\text{composite}}$)

The benchmark harness calculates a composite score $S_{\text{composite}} \in [0, 100]$:

$$S_{\text{composite}} = (0.25 \times S_{\text{mem}}) + (0.25 \times S_{\text{lat}}) + (0.30 \times S_{\text{rob}}) + (0.20 \times S_{\text{qual}})$$

- **$S_{\text{mem}}$ (Memory Efficiency, 25%)**: Evaluates baseline RSS, peak RSS under load, and residual memory leak delta after garbage collection.
- **$S_{\text{lat}}$ (Latency & Throughput, 25%)**: Evaluates frame rendering time ($\le 16.6\text{ ms}$ for 60 FPS), P99 event-to-draw turnaround, and sustained frame rate.
- **$S_{\text{rob}}$ (Attack Robustness, 30%)**: Measures survival rate across all 10 Red Team attack scenarios, penalizing any unhandled panics or terminal corruptions.
- **$S_{\text{qual}}$ (Code Quality & Zero-Mock, 20%)**: Enforces clean static analysis (`ruff`, `golangci-lint`, `clippy`), complete error handling, and strict adherence to Rule #0 (zero synthetic mocks).

---

## ⚡ 10-Tier Adversarial Attack Suite

1. `SIGWINCH_STORM`: 1,000 rapid terminal resize events (10x5 to 300x100) within 2 seconds.
2. `EVENT_FLOOD`: 100,000 JSON telemetry events streamed over local socket at unthrottled line rate.
3. `ANSI_INJECTION`: Fuzz payload containing corrupted byte sequences, truncated CSI codes, and OSC title exploits.
4. `KEY_SPAM_FLOOD`: 10,000 keystrokes/sec injected via PTY input buffer.
5. `SLOW_CONSUMER_HANG`: Abruptly severed TCP/Unix socket testing connection retry without UI freeze.
6. `ZERO_DIM_VIEWPORT`: Terminal resized to $0\times0$ and $1\times1$ boundary conditions.
7. `HIGH_CONCURRENCY_MUTATION`: 10 background worker threads writing simultaneous telemetry updates.
8. `MEMORY_PRESSURE`: Artificial host memory throttling inducing emergency GC cycles.
9. `ABRUPT_TERMINATION`: Verification of zero orphaned background threads and clean terminal restoration on SIGTERM/SIGINT.
10. `CHAOS_SPEC_SHIFT`: Abliterated 70B dynamic layout and telemetry schema mutation injection mid-flight.

---

## 🏆 NPU Bonus Grant Accounting

Upon tournament completion, the surviving TUI framework and its specialist agent author receive an NPU Bonus Grant logged to `02_ai_models_and_inference/mesh_benchmarks/npu_bonus_ledger.json`:

$$\text{Bonus NPU Hours} = 25.0 + 0.5 \times \max\left(0, S_{\text{composite}} - 70.0\right)$$

- Elite scores ($S_{\text{composite}} \ge 90.0$) are awarded up to **50.0 NPU Hours** with `ACTIVE_GRANT` status.
