---
title: "AI Debate Consensus: Canonical Global Single-Word CLI Command Interface (`lauburu`, `tui`, `arena`)"
date: "2026-08-29T17:50:00Z"
tags: [lauburu, ai_debate, cli, global_command, tui_launcher, dev_mode]
---

# 🌐 Tri-Orchestrator AI Debate: Canonical Global Single-Word CLI Interface

**Debate Question:** How to architect an idempotent, zero-friction global CLI interface so the user can type a single word (`lauburu`, `tui`, or `arena`) anywhere in their terminal to launch the full Canonical TUI or the Live `--dev` Cockpit?

---

## 👥 1. Orchestrator Deliberations

### 🔵 Local AI Orchestrator (Qwen 3.8 Max / Coder 7B)
> *"By placing a clean, self-contained executable entrypoint `lauburu` directly into `/Users/aaron/.local/bin/` (which is already in `$PATH`), the user can execute `lauburu` or `tui` or `arena` from any directory or tmux window with zero environment setup or directory hopping."*

### 🔴 Devil's Advocate (Qwen 2.5 Abliterated / Mistral Nemo)
> *"The CLI must support subcommands and arguments (`lauburu dev`, `lauburu arena`, `lauburu map`, `lauburu movesense`, `lauburu stop`), pass through all flags (`--dev`), and provide symlinked single-word aliases (`tui` and `arena`) for maximum developer velocity."*

### 🟣 Cloud Shadow Orchestrator (Gemini 2.5 Flash / High Reasoning)
> *"The CLI wrapper must also:
> 1. Ensure the background physical Movesense BLE daemon is alive.
> 2. Auto-heal any stale Python / TUI processes.
> 3. Provide rich colored help and instant execution (<10ms overhead)."*

---

## 🏛️ 2. Mathematical Consensus Accord (>0.98 Threshold)

### Invariant 1: Single-Word Executable Mappings
- `lauburu` $\to$ Full 9-screen Canonical TUI Command Center.
- `tui` $\to$ Fast alias for `lauburu`.
- `arena` / `lauburu dev` $\to$ Live Side-by-Side Dual Graphical Arena with hot-reloading.
- `lauburu map` $\to$ Unified 3D Spatial Fusion Engine.
