# Project: lauburu-tui 5-Tab Architecture Expansion

## Architecture
`lauburu-tui` is a high-performance, native Rust terminal interface built on Ratatui 0.29, Tokio 1.0, and Crossterm 0.28. It provides real-time cluster monitoring, local and distributed AI inference streaming, dynamic sharding routing, cloud API spend optimization, and 24/7 continuous LoRA training oversight across the canonical 7-layer Lauburu Mesh Ecosystem (108.0 GB RAM / 82.8 GB Usable AI VRAM Pool).

### System Data Flow
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TOKIO ASYNC RUNTIME                              │
│                                                                             │
│   ┌────────────────────┐   ┌────────────────────┐   ┌───────────────────┐   │
│   │   EventHandler     │   │   NetworkWorker    │   │ PersistenceWorker │   │
│   │ (Crossterm & Tick) │   │  (SSE Streaming)   │   │  (GDrive/Fallback)│   │
│   └─────────┬──────────┘   └─────────┬──────────┘   └─────────┬─────────┘   │
│             │                        │                        │             │
│             └────────────────► mpsc::UnboundedSender ◄────────┘             │
│                                      │                                      │
│                                      ▼                                      │
│                         ┌────────────────────────┐                          │
│                         │   Central Event Loop   │ (60 FPS Render Loop)     │
│                         │   (App::handle_event)  │                          │
│                         └────────────┬───────────┘                          │
│                                      │                                      │
│                                      ▼                                      │
│                         ┌────────────────────────┐                          │
│                         │   Terminal Draw Frame  │                          │
│                         │    (ui::render(&app))  │                          │
│                         └────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| F1 | 5-Tab Navigation (`Tab` Enum) | Expand `Tab` to Topology, Chat, Sharding, API Scanner, Training with 1-5 keys, Tab/BackTab, arrows | M1 | R1 | DONE |
| F2 | 5-Tab Header & Footer | Render all 5 tabs in `header.rs` Tabs widget and contextual hotkeys in `footer.rs` | M1 | R1 | DONE |
| F3 | Unified AI Sharding Decision Tree | Visual flowchart for TB4 DMA -> Exo MLX Ring -> Petals DHT -> Local Solo | M2 | R2 | DONE |
| F4 | 7-Layer Node Sharding Matrix | Interactive table of 7 physical nodes (82.8 GB VRAM, dynamic caps, protocol roles) | M2 | R2 | DONE |
| F5 | Dynamic Model-to-Protocol Table | Quantization & size routing (≤8B/14B, 32B, 70B, 120B, 405B) to optimal sharding protocol | M2 | R2 | DONE |
| F6 | $0 Cloud Spend Velocity Dashboard | Gauges for baseline spend, current spend, savings, and $0 spend velocity % | M3 | R3 | DONE |
| F7 | Cloud API Endpoint Scanner | Table of detected cloud endpoints, token usage, and monthly costs | M3 | R3 | DONE |
| F8 | Local Model Swap Recommender | Match detected cloud APIs (GPT-4o, Claude 3.5, Gemini) to local GGUF/MLX replacements | M3 | R3 | DONE |
| F9 | Non-Blocking Scanner Poller | Background async poller scanning API usage via Tokio mpsc channels | M3 | R3 | DONE |
| F10 | 24/7 LoRA Distillation Dashboard | Live tracking of active model, teacher model, step progress, throughput, and loss history | M4 | R4 | DONE |
| F11 | Dynamic RAM Governor State Machine | Full (>85%), Medium (70-85%), Minimal (50-70%), Emergency Pause (<50%) with directives | M4 | R4 | DONE |
| F12 | Shadow Swarm Benchmark & NPU Ledger | ELO tournament table and NPU Bonus Ledger (Edge TPU / ANE token credits) | M4 | R4 | DONE |
| F13 | Dual-Path Persistence Manager | Primary `/Volumes/Google Drive/...` with graceful fallback to `config/memory_fallback.json` | M5 | R5 | DONE |
| F14 | Atomic Write & Zero-Panic Invariant | Atomic temporary file + intra-filesystem rename with no unhandled errors | M5 | R5 | DONE |
| F15 | Non-Blocking Persistence Worker | Debounced async persistence actor executing off UI thread via `spawn_blocking` | M5 | R5 | DONE |
| F16 | 4-Tier E2E Test Suite Pass | 100% passing tests across unit, integration, stress, fallback, and UI test backends | M6 | Acceptance Criteria | DONE |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Tab Navigation & App State Expansion | Expand `Tab` to 5 variants, update `app.rs`, `ui/mod.rs`, `header.rs`, `footer.rs` | none | DONE |
| M2 | Sharding Protocol View (`sharding.rs`) | Decision tree, 7-layer node matrix, dynamic model routing table, sharding state | M1 | DONE |
| M3 | API Scanner View & Async Poller (`api_scanner.rs`) | Spend velocity dashboard, endpoint table, local swap cards, background poller | M1 | DONE |
| M4 | Continuous Training View (`training.rs`) | LoRA job status, RAM Governor gauge, ELO tournament, NPU Bonus Ledger | M1 | DONE |
| M5 | Persistence Engine & Graceful Fallback (`persistence.rs`) | Dual-path `PersistenceManager`, atomic write, unmounted GDrive fallback, async worker | M1 | DONE |
| M6 | Full Test Suite Pass & Adversarial Hardening | Run full test suite, verify 100% passing cargo test, review, stress test, forensic audit | M1-M5 | DONE |

---

## Verification Summary
- **Unit & Integration Tests**: 100% Passing (210+ tests across all 16 test suites)
- **Reviewer Verdicts**: Reviewer 1 (APPROVE), Reviewer 2 (APPROVE)
- **Challenger Verdicts**: Challenger 1 (APPROVE: 40.5k tab switches/s, 182.9 FPS), Challenger 2 (APPROVE: unmounted fallback & zero panic)
- **Forensic Audit**: CLEAN (0 mock keywords, authentic math, POSIX atomic rename persistence)
