# PLAN — Canonical Port Competitive TUI Swarm

## Objective
Develop, optimize, and debate multiple distinct TUI paradigms for the Canonical Port (`01_apps/canonical_port`), evaluate them via Tri-Orchestrator AI Debate, declare a mathematically justified winner, integrate the winner with all mesh components (llama.cpp, biometrics, DaemonSupervisor, Cloudflare AI Gateway), and verify with zero-mock forensic integrity.

## Swarm Roadmap

### Milestone 0: Survey & Infrastructure Reconnaissance
- Spawn 3 Explorers:
  - `explorer_tui_survey_1`: Inspect existing TUI architecture, screens, widgets, `tui/services/`, and `tui/screens/`.
  - `explorer_tui_survey_2`: Inspect backend daemons (`DaemonSupervisor`, `cron_scheduler.py`, `boot_canonical_mesh.sh`, Zellij/Tmux configurations).
  - `explorer_tui_survey_3`: Inspect test harnesses, mocks vs authentic providers, `llama.cpp` router, and biometrics telemetry pipelines.
- Synthesize findings into `PROJECT.md`.

### Milestone 1: Bootstrapping & Mesh Layout Automation (R1)
- Refine and finalize `boot_canonical_mesh.sh` (supporting Tmux/Zellij multiplexing, daemon auto-restart, health probes, Cloudflare AI Gateway pre-flight checks).
- Verify integration between `DaemonSupervisor` and TUI status event bus.

### Milestone 2: Competitive Swarm Deployment (R2)
- Deploy 3 competitive implementation tracks in parallel:
  - **TUI-Alpha (Dashboard/Telemetry Paradigm)**: High-density real-time grid, live system stats, daemon cards, biometrics gauges, sparklines.
  - **TUI-Beta (Chat/Multi-Model Inference Paradigm)**: Dynamic prompt canvas, streaming multi-model comparison (Cloudflare vs llama.cpp local vs Julien), token telemetry, context inspectors.
  - **TUI-Gamma (Graph/Architecture Paradigm)**: Dual-layout tree + ASCII graph, live dependency traversal, Obsidian Wikilink graph, component drilldowns.
- Each track implements a standalone runnable entry point with test pilots.

### Milestone 3: Tri-Orchestrator Live AI Debate Evaluation (R3)
- Execute the Tri-Orchestrator Live Agent Debate Protocol:
  - Cloud Orchestrator (Gemini 3.1 Pro / 3.7 Flash)
  - Local AI Orchestrator (Kimi / Qwen on Mesh)
  - Training Engine (HuggingFace / TRL / PEFT)
  - Devil's Advocate (Abliterated Llama 70B)
- Score each candidate on Performance, Stability, UI/UX Ergonomics, Mesh Integration, and Extensibility.
- Produce `canonical_tui_verdict.md` with mathematical consensus (>0.98).

### Milestone 4: Victor Harmonization & Seamless Integration
- Integrate the winning paradigm (and top features from candidates) into the canonical TUI entrypoint (`app.py` / `main.py`).
- Connect live `llama.cpp` router, Biometrics dashboard, DaemonSupervisor, and Cloudflare AI Gateway without blocking event loops.

### Milestone 5: Verification, Adversarial Hardening & Forensic Zero-Mock Audit
- Run Reviewers, Challengers, and Forensic Auditor to ensure:
  - All E2E / pilot tests pass.
  - Zero synthetic mock data (Rule #0 compliant).
  - Terminal resizing (SIGWINCH), error states, and disconnects handled gracefully.
