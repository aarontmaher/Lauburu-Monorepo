---
title: "Lauburu Monorepo — Applications Organizational Structure TUI & 6-Domain Architecture"
tags: [lauburu, apps, tui, architecture, ratatui, zero_mock, process_governor]
date: "2026-09-11"
---

# 🌌 Lauburu Monorepo — Applications Organizational Structure TUI (`lauburu-apps`)

Following the Tri-Orchestrator debate consensus in [[05_SWARMS/debates/AI_DEBATE_FRONTIER_SWARM_AND_COST_ANALYSIS]], running continuous background TUI loops in every individual sub-application causes severe thermal drift and host RAM starvation on Apple Silicon.

To provide unified observability without background rendering overhead, the **Master Applications Organizational Structure TUI** (`lauburu-apps`) catalogs all 24+ applications and core services into **6 Canonical Domains**, delivering real-time zero-mock process telemetry, non-blocking TCP socket health, and on-demand interactive lifecycle management.

---

## 🏛️ The 6 Canonical Application Domains

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               LAUBURU MONOREPO APPLICATIONS ORGANIZATIONAL TREE             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🚀 DOMAIN 1: CLIENT HUBS & USER-FACING PORTALS                              │
│    • port_4000_flutter_rust   (Port 4000/4001: Flutter UI + Axum Backend)   │
│    • canonical_port           (Port 9-Screen Operations Console)            │
│    • zone2_endurance          (Port 3000: Next.js 14 Cardio Coaching Web)   │
│    • web_tui_portal           (Port 8088: WebGL 120 FPS Terminal Streamer)  │
│    • unified_portal           (Gateway & Multi-App Router)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🩺 DOMAIN 2: BIOMETRICS DSP & SPATIAL KINEMATICS                            │
│    • movesense_hub            (Port 4000: 512Hz ECG, Pan-Tompkins QRS, BLE) │
│    • movesense_readiness_hub  (Overnight Sleep Staging, PTT BP, DFA-alpha1) │
│    • spatial_grappling_3d     (Port 8090: Three.js / WebGPU 3D Tatami Grid) │
│    • automotive               (Android Auto Voice Coder & HUD Telemetry)    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🧠 DOMAIN 3: AI INFERENCE, PRP RING & TRAINING ENGINES                      │
│    • prima_tui                (Port 8082: Prima.cpp PRP Ring Master)        │
│    • rust_arena_tui           (Bradley-Terry AI Combat Arena & ELO Radar)   │
│    • edge_compute_and_ai      (Port 8081/8083: GGUF Sharding & llama.cpp)   │
│    • lora_synthesizer_worker  (24/7 Continuous LoRA SFT/DPO Synthesizer)    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🖥️ DOMAIN 4: TERMINAL TUIS, OBSERVABILITY & WORKBENCHES                     │
│    • rust_project_monitor     (lauburu-monitor: Ports, Mesh, Monorepo AST)  │
│    • rust_swarm_training_tui  (lauburu_health_tui: 7-Layer Mesh Health/RAM) │
│    • rust_network_analyzer    (lauburu_network_lens: 40Gbps TB4 DMA Prober) │
│    • notebooks                (Port 8888/8889 JupyterLab, 2718 Marimo, 8890)│
│    • canonical_tui_prototypes (Polyglot TUI Engines: Go, Python, Rust, C)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🛍️ DOMAIN 5: COMMERCE, SUBSCRIPTIONS & MONETIZATION                         │
│    • commerce_and_business    (Shopify Storefront GraphQL & Subscriptions)  │
│    • shopify_ai               (Autonomous Store Manager & Compute Token)    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 📱 DOMAIN 6: EDGE MOBILE, VISION & REVERSE ENGINEERING                      │
│    • screen_lens              (Port 4003: ScreenCaptureKit VLA & OCR)       │
│    • pixel_app_reverse_engineer (APK Decompilation & Protocol Rebuilder)    │
│    • network_cable_analyzer   (Physical TB4/Ethernet/Wi-Fi Link Prober)     │
│    • self_healing_hub         (Port 18802: FastAPI Self-Healing & ADB)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Unified Binary Specifications

### 1. Standalone Application Orchestrator (`lauburu-apps`)
- **Location:** `/Users/aaron/.local/bin/lauburu-apps`
- **Source:** `01_apps/rust_apps_orchestrator/`
- **SHA256:** `d6d877ee85933e2bef68586641c8a2d0a9c43a898aea60067aefdb1f452f839b`
- **Controls:**
  - `[Tab] / [1-6]`: Domain navigation.
  - `[↑/↓] / [j/p]`: Application selection.
  - `[Enter] / [o]`: Launch in default browser (for web-facing portals).
  - `[s]`: Background process start with log piping to `01_apps/.logs/<app_id>.log`.
  - `[k]`: Graceful process kill (`SIGTERM` $\to$ `SIGKILL`).
  - `[t]`: Automated test command execution.
  - `[r]`: Telemetry refresh.
  - `[q]`: Quit.
- **Headless Modes:** `--tree`, `--test`, `--json`.

### 2. Master Project Monitor Integration (`lauburu-monitor`)
- **Location:** `/Users/aaron/.local/bin/lauburu-monitor`
- **Source:** `01_apps/rust_project_monitor/`
- **SHA256:** `c0c0d75027662ab313055a618f66919ef71fd42dc3d482aff078b0d9015c01cc`
- **Tab 4 (`📱 Apps Ecosystem`):** Embeds live status for all 24 apps alongside Monorepo AST, 7-Layer Mesh Nodes, Port Matrix, Subsystems, and Tri-Vault Storage.

---

## 🛡️ Empirical Tri-Proof Verification

1. **Proof 1 (Actuation):** `lauburu-apps --test` and `lauburu-monitor --test` both exit with code 0 in $< 1.0$s.
2. **Proof 2 (Line-by-Line):** Clean Rust codebase, zero warnings, genuine TCP socket polling and `lsof`/`ps` process metrics.
3. **Proof 3 (Visual):** Clear ANSI tree hierarchy and Ratatui 120 FPS split layout.
