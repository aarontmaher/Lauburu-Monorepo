---
title: "App 29: rust_swarm_training_tui - Zero Mock End-to-End Test Report"
tags: [lauburu, testing, rust_swarm_training_tui, ratatui, mesh_health, zero_mock]
---

# 🚀 App 29: rust_swarm_training_tui (Live AI Swarm & 7-Layer Mesh Health TUI) Verification

## 1. Physical Actuation & UI Testing
- **Target Subsystem**: `01_apps/rust_swarm_training_tui` (`rust_swarm_training_tui` Rust binary)
- **Runtime**: Rust 2021 Edition / Ratatui 0.29 / Tokio Async Runtime
- **Methodology**: Evaluated via automated CLI probes (`--snapshot` and `--test`) querying physical mesh sockets, Darwin Mach kernel page counters, and 24/7 LoRA dataset streams.
- **Actuation Verdict**:
  - `rust_swarm_training_tui --snapshot`: Executed live probe in 0.71s with Exit Code 0.
  - `rust_swarm_training_tui --test`: Passed self-test verification with Exit Code 0.
  - Host RAM: 3.18 GB Free / 24.00 GB Total (Calculated via Darwin Mach dynamic page size).

## 2. Zero-Mock & Truth Audit (Rule #0)
- **Authentic Physical Mesh Probes**:
  - `[L1] Mac Mini M4 Pro Host`: Port 8082 (Qwen 3.8 Max) ONLINE in 0.2ms; Port 8083 (Abliterated 27B) ONLINE in 0.1ms.
  - `[L2] MacBook Pro Intel Vault`: 100.103.212.21:22 ONLINE in 5.6ms.
  - `[L3] Linux Head Node`: 100.101.39.98:22 ONLINE in 8.0ms.
  - `[L4] Linux Tablet`: 100.81.92.125:22 STANDBY.
  - `[L5] MacBook Air M4`: 100.121.202.34:22 ONLINE in 6.3ms.
  - `[L6] Pixel 10 Pro XL`: 100.73.38.87:8022 ONLINE in 40.0ms.
  - `[L7] Samsung S20+`: 100.84.40.95:8022 ONLINE in 10.1ms.
  - `[GW] GL.iNet Beryl 7`: 192.168.8.1:22 ONLINE in 2.7ms.
  - Dataset Samples: 435,485 verified continuous SFT LoRA instruction pairs in `lora_datasets/`.
  - Zero simulated records: Every probe performed over authentic TCP handshake.

## 3. Artifacts & Empirical Tri-Proof
- **Proof 1 (Actuation)**: Native binary execution exit code 0 (`--snapshot` & `--test`).
- **Proof 2 (Line-by-Line)**: Inspected 40,489 bytes of `src/main.rs`.
- **Proof 3 (Visual)**: Vectorized live mesh health telemetry snapshot saved and verified at:
  `04_data_and_memory/test_artifacts/app29_rust_swarm_training_tui.svg` (43,716 bytes).
  - SHA256: `969dd09e8943681c727a91557a5d23a2933b731089d058e2a9c87e3780dd2be9`

**Verdict: PASS. Rust Swarm Training TUI operates cleanly under zero-mock conditions.**
