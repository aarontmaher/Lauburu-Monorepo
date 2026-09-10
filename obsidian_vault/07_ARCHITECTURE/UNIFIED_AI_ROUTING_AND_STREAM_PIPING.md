---
title: "Unified Local AI Routing, POSIX Stream Piping & IDE Integration"
date: "2026-09-02"
tags: [architecture, router, mods, jupyterlab, vscode, antigravity, bilateral_swarm]
---

# ⚡ Unified Local AI Routing, POSIX Stream Piping & IDE Integration

## 🏛️ 1. Multi-Tier AI Execution Hierarchy

The Lauburu Mesh provides three tiers of AI intelligence for maximum speed and decision quality:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAUBURU MULTI-TIER AI EXECUTION STACK                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: SUB-SECOND STREAM PIPING (`mods` / Port :8083 / ~0.5s / $0)        │
│ • Runs directly in terminal, scripts, and VS Code tasks.                    │
│ • Ingests stdin -> fast local Qwen 3.8 Max -> stdout.                       │
│ • Use for: Instant build error triage, git diff commit messages, log filter.│
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: LOCAL ORCHESTRATOR & DEVIL'S ADVOCATE (`router debate` / :8083)    │
│ • 4-Agent Bilateral Swarm AI Debate (Proposal vs Abliterated Red Team).     │
│ • High-stakes architectural consensus (>0.98 threshold).                    │
│ • Use for: System design decisions, sharding strategy, protocol selection.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: MULTIMODAL CLOUD FRONTIER AGENTS (Antigravity / Gemini 3.7 Flash)   │
│ • Long-context pair programming, whole-codebase AST refactors.              │
│ • Governs living visual cortex (Screen Lens) and interactive JupyterLab.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🛠️ 2. IDE & Antigravity Integration for `mods`

1. **Inside VS Code & Code-Server:**
   - Run tasks directly via `Terminal -> Run Task -> AI: Explain Selection / AI: Generate Commit Message`.
   - Pipe terminal output in the integrated terminal: `cargo build 2>&1 | mods "diagnose"`.
2. **Inside Antigravity Agent Sessions:**
   - Antigravity agents execute `mods` via `run_command` for 0.4s pre-filtering of massive logs before context ingestion.

## 🚀 3. Quick Reference Commands

- `router notebook` — Launches Master Dashboard in dedicated Standalone JupyterLab.
- `router vscode` — Launches Full Embedded VS Code on Port 8090.
- `router debate "<topic>"` — Runs Bilateral Swarm Crucible.
- `router free "<query>"` — Free keyless query via `tgpt`.
- `router voice "<prompt>"` — Local AI voice code synthesizer.
