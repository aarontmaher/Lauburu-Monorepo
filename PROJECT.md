# Project: Master 6-Pillar Local AI Arena Training & Interactive Cockpit

## Architecture
- **Target Notebook**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/notebooks/00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb`
- **Exported Visual Asset**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/notebooks/6_pillar_dark_cockpit.png`
- **UI Engine**: Tailwind Cyberpunk Glassmorphism + HTML5 Canvas + Dual-Mode Standalone JS / IPyWidgets.
- **7-Layer Mesh Endpoints**: 108.0 GB Pooled RAM / 82.8 GB Usable AI VRAM across L1 Mac Host, L2 MacBook Pro (TB4 Bridge), L3 Linux Head Node (`100.101.39.98:4005`), L4 Linux Tablet, L5 MacBook Air (`100.93.158.96:8889`), L6 Pixel 10 Pro XL, L7 Samsung S20, and Devil's Advocate RPC (`100.119.199.76:8083`).
- **Tri-Vault Storage**: Obsidian Vault (`obsidian_vault/`), PySpark Data Lake (`lora_datasets/continuous_lora_dataset.jsonl`), and GitHub Monorepo (`04_data_and_memory/`).
- **Headless Invariant**: Strict `matplotlib.use('Agg')` in Cell 1; zero local GUI popups.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| F1 | Glassmorphic CSS & 4K Typography | Cyberpunk design tokens (#06b6d4, #3b82f6, #8b5cf6, #10b981, #f59e0b), Inter/JetBrains Mono fonts | M1 | Survey | DONE |
| F2 | High-DPI 3-Panel Dark Visualizations | 160+ DPI figure (Horizontal ELO, Polar Radar, Token Velocity vs TTFT) exported to disk | M1 | Survey | DONE |
| F3 | Zero-JSON HTML Cards & Invariants | Styled HTML cards/tables for system invariants and telemetry; zero raw JSON dumps | M1 | Survey | DONE |
| F4 | Dynamic Status/Layer Filter Pills | Status (All, Active, Ready, Syncing, Ingested) & Layer pills with dynamic match counter and empty state card | M2 | Survey | DONE |
| F5 | Interactive Model Selector Dropdown | Dropdown with 9 canonical models updating dynamic metadata cards on change | M2 | Survey | DONE |
| F6 | Live ELO Recalculation & Canvas | Bradley-Terry ELO slider with dynamic HTML5 `<canvas id="win-curve-canvas">` sigmoid curve | M2 | Survey | DONE |
| F7 | 6-Pillar Dataset Ingestion Engine | Multi-path resolution across 6 pillars with memory-safe streaming generator (>=2.5GB headroom) | M3 | Survey | DONE |
| F8 | DPO Formatter & Split-View Viewer | Standardized HuggingFace TRL DPO schema and 3-panel split view (Cyan prompt, Emerald chosen, Amber rejected) | M3 | Survey | DONE |
| F9 | Tri-Vault Sync & One-Click Lake Export | POSIX flock atomic append to `continuous_lora_dataset.jsonl`, Obsidian Wikilinks sync, export toast card | M3 | Survey | DONE |
| F10 | Zero-Mock Live Mesh Sockets | Non-blocking TCP socket probes (200ms timeout) across 6 endpoints and Rule #0 fallback states | M4 | Survey | DONE |
| F11 | Live Debate Stream Inspector | Stream ingestion from `truth_audit_debate.jsonl`, glowing role badges, consensus bar, unified diff viewer | M4 | Survey | DONE |
| F12 | Cross-Runtime & Standalone Packaging | Standalone client-side JS (`window.meshCockpitEngine`), IPyWidgets fallback, Marimo DAG compatibility | M4 | Survey | DONE |
| F13 | Full Opaque-Box E2E Test Suite | 4-tier opaque-box test suite (Tiers 1-4) in `tests/e2e_arena_notebook/` with JUnit/JSON runner | E2E | Survey | DONE |
| F14 | White-Box Adversarial Hardening (Tier 5) | Comprehensive white-box adversarial stress tests, edge case fuzzing, and victory sign-off | M5 | Survey | IN_PROGRESS |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Design test harness and implement Tiers 1-4 test suites -> TEST_READY.md | none | DONE |
| M1 | Glassmorphic High-DPI UI/UX & Tailwind Theme | CSS styles, 4K Retina typography, 3-panel 160+ DPI dark charts, zero raw JSON | none | DONE |
| M2 | Interactive Controls & Live ELO Recalculation | Model dropdown, filter pills, ELO sliders, canvas win curves | M1 | DONE |
| M3 | 6-Pillar Dataset & Tri-Vault Integration | 6-pillar loader, DPO sample viewer, TRL formatter, Tri-Vault sync | M1, M2 | DONE |
| M4 | Zero-Mock Live Mesh Sync & Multi-Runtime | Live mesh probes (:4005, :8889, :8083), debate stream, Marimo/standalone compatibility | M1, M2, M3 | DONE |
| M5 | Final Milestone: 100% E2E Pass & Adversarial Hardening | Pass 100% of Tiers 1-4 test suite, execute Tier 5 adversarial hardening | M4, E2E (TEST_READY.md) | IN_PROGRESS |

## Code Layout
- `obsidian_vault/notebooks/00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb` — Master arena notebook
- `obsidian_vault/notebooks/6_pillar_dark_cockpit.png` — 160+ DPI 3-panel exported dark figure
- `tests/e2e_arena_notebook/test_tier1_feature_coverage.py` — Tier 1 isolated feature tests (F1-F12)
- `tests/e2e_arena_notebook/test_tier2_boundary_corner.py` — Tier 2 boundary and corner case tests
- `tests/e2e_arena_notebook/test_tier3_pairwise_combinations.py` — Tier 3 cross-feature interaction tests
- `tests/e2e_arena_notebook/test_tier4_real_world_workloads.py` — Tier 4 real-world user workload tests
- `tests/e2e_arena_notebook/run_e2e_tests.py` — Master test runner
