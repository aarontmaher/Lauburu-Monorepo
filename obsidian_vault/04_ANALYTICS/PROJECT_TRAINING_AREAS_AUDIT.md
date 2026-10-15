# 🎯 Lauburu Mesh Ecosystem: Comprehensive Project Training Areas Audit & Specialist Roadmap

## 📌 Executive Overview

An exhaustive empirical audit of the **3,100+ code files**, **435K+ LOC**, and `/Volumes/Lauburu-Monorepo/04_data_and_memory/data/` across the monorepo was conducted. 

While the existing continuous 24/7 training pipelines excel at **Screen Lens Visual VLA + CTF CyberGym**, **10M Speculative Drafting**, **Generational Shadow Coder evolution**, and **Shopify E-Commerce**, there are **8 major high-yield domains** and **24 dedicated specialist roles** with rich production codebases that currently have **minimal or near-zero training coverage** (`<= 7 lines` in `lora_datasets/specialists/`).

---

## 🗺️ Master Training Gap & Priority Matrix

| Domain # | Subsystem & Codebase Area | Code Base Breadth | Existing Dataset Size | Training Criticality | Recommended Local AI Specialist | Target Mesh Node & Placement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Biometrics & DSP** | `03_biometrics_and_telemetry/` & `01_apps/biometrics/` | 52 files (25 source code) | `8.1 KB` (5 lines) | 🚨 **TIER 1 CRITICAL** | **BioMistral 7B (Q8_0)** | L4 (Linux Tablet) / L6 (Pixel 10 TPU) |
| **2. Spatial Kinematics** | `01_apps/spatial_and_3d/` (WebGPU Tatami) | 1,174 files (18 source code) | `5.0 KB` (3 lines) | 🚨 **TIER 1 CRITICAL** | **Qwen 2.5 Coder 32B (Q4_K_M)** | L2 (MBP TB4 Vault) / L5 (MBA Metal) |
| **3. Mesh Transports & OOB** | `00_core_infrastructure/multi_wan/` & Layer 0 | 58 files (33 source code) | `4.6 KB` (3 lines) | 🚨 **TIER 1 CRITICAL** | **SmolLM2 135M / 360M (IQ2_XXS)** | GW (GL.iNet) / L1/L3 (Mac/Linux Mini) |
| **4. Polyglot Terminal UIs** | `01_apps/canonical_port/` (Go / Rust / Python) | 13,635 files (6,844 source code) | `4.8 KB` (3 lines) | ⚡ **TIER 2 HIGH** | **Qwen 2.5 Coder 7B (Q4_K_M)** | L1 (Mac Mini MPS) / L3 (Linux Node) |
| **5. Reactive Notebooks** | `01_apps/notebooks/` (Marimo / IPykernel) | 17,258 files (9,708 source code) | `5.1 KB` (3 lines) | ⚡ **TIER 2 HIGH** | **Notebook Specialist 7B (Q4_K_M)** | L1 (Mac Mini) / L5 (MacBook Air) |
| **6. Edge Android & ADB** | `06_scripts_and_tooling/android/` | Android 15 / Tensor G5 | `5.0 KB` (3 lines) | ⚡ **TIER 2 HIGH** | **SmolLM2 1.7B / NanoVision 10M** | L6 (Pixel 10) / L7 (Samsung S20) |
| **7. App Store Packaging** | `01_apps/` Native Release Manifests | Flutter, Swift, Kotlin | `90 KB` (evals only) | 📋 **TIER 3 MEDIUM** | **Qwen 2.5 Coder 15B (Q4_K_M)** | L3 (Linux Node Docker Hub) |
| **8. SWE-Bench AST Repair** | `04_data_and_memory/swe_bench_datasets/` | Multi-file git AST diffs | `5.0 KB` (3 lines) | 📋 **TIER 3 MEDIUM** | **DeepSeek Coder V2 Lite / Qwen 32B** | L2/L3 (MBP TB4 + Linux Node RPC) |

---

## 🔬 Deep-Dive: The 8 Identified Training Domains

### 1. 🫀 Medical-Grade Biometrics, Pan-Tompkins DSP & Sleep Physiology
* **Subsystem:** `03_biometrics_and_telemetry/` & `01_apps/biometrics/movesense_hub` / `zone2`.
* **Current Gap:** `specialists/movesense_clinical_dsp.jsonl` (5 lines), `npu_ecg_signal_filter.jsonl` (3 lines), `autonomic_stress_hypnogram_coach.jsonl` (3 lines).
* **Specific Competencies to Train:**
  1. **Pan-Tompkins QRS Filtering:** Real-time 512Hz bandpass filtering ($5\text{–}15\text{ Hz}$), derivative squaring, and moving-window integration under high physical movement.
  2. **PTT Non-Invasive Blood Pressure:** Mapping R-peak to photoplethysmography pulse arrival time without cuff inflation.
  3. **Fractal DFA-$\alpha_1$ Scaling:** Detrended fluctuation analysis to identify exact Zone 1/Zone 2 aerobic threshold inflection ($\alpha_1 = 0.75$).
  4. **Nocturnal Polysomnography & Sleep Architecture:** Multimodal sleep hypnogram classification (Deep, Light, REM, Wake) and morning HRV readiness scoring.
* **Silicon Placement:** **BioMistral 7B (Q8_0)** on L4 (Linux Tablet) / L6 (Pixel 10 TPU).

---

### 2. 🥋 Spatial Grappling 3D Kinematics & WebGPU World Models
* **Subsystem:** `01_apps/spatial_and_3d/` & `spec-10-spatial-grappling-kinematics`.
* **Current Gap:** `specialists/spatial_grappling_kinematics.jsonl` (3 lines), `3d_spatial_instructional_map_lora.jsonl` (1.44 MB).
* **Specific Competencies to Train:**
  1. **955-Node OPML Spatial Tree Traversal:** Graph reasoning over full martial arts hierarchies (guard passes, sweeps, submissions, escapes).
  2. **Joint Torque & Biomechanical Safety:** Kinematic joint angle constraints, center-of-gravity vectors, and escape probability matrices.
  3. **120 FPS WebGPU WGSL Shaders:** Rust/wgpu shader synthesis for real-time 3D tatami coordinate rendering.
* **Silicon Placement:** **Qwen 2.5 Coder 32B (Q4_K_M)** on L2 (MBP TB4 Vault) / L5 (MacBook Air Metal).

---

### 3. 📡 5-Layer OSI-Inspired Mesh Transports & Layer 0 OOB Resurrection
* **Subsystem:** `00_core_infrastructure/multi_wan/`, `06_scripts_and_tooling/network/`, `canonical-mesh-transports`.
* **Current Gap:** `tb4_dma_tensor_streamer.jsonl` (3 lines), `router_uci_mesh_governor.jsonl` (3 lines), `wol_hardware_resurrector.jsonl` (3 lines).
* **Specific Competencies to Train:**
  1. **Layer 0 Bluetooth Serial PTY:** Raw RFCOMM/BLE UART (`/dev/rfcomm0`) transport without IP stacks for out-of-band terminal rescue.
  2. **10Gbps Thunderbolt 4 DMA Ring Sharding:** Zero-copy socket ring buffers across `bridge0` maintaining $<0.30\text{ ms}$ latency for `prima.cpp`.
  3. **OpenWrt UCI & mwan3 Dynamic Failover:** Automated route arbitration across Wi-Fi 7 MLO 6GHz, 1GbE LAN, and Tailscale WireGuard.
* **Silicon Placement:** **SmolLM2 135M / 360M (IQ2_XXS / Q4_K_M)** on GW (GL.iNet Router) & L1/L3.

---

### 4. 🖥️ Polyglot Terminal UI (TUI) & Elm Architecture
* **Subsystem:** `01_apps/canonical_port/` & `05_agents_and_swarms/tui_specialist_local_ai/`.
* **Current Gap:** `specialists/polyglot_tui_designer.jsonl` (3 lines).
* **Specific Competencies to Train:**
  1. **Elm Architecture State Loops:** Pure functional `Init`, `Update`, `View` in Go Bubble Tea, Python Textual, and Rust Ratatui.
  2. **Zero-Allocation Terminal Buffers:** Immediate-mode rendering at 120 FPS with zero memory allocation.
  3. **Dynamic Terminal Resizing (`SIGWINCH`):** Split-pane geometry management, ANSI styling, and headless tmux render buffers.
* **Silicon Placement:** **Qwen 2.5 Coder 7B (Q4_K_M)** on L1 (Mac Mini Metal MPS) / L3 (Linux Node).

---

### 5. 📓 Reactive Notebooks & Interactive Data Science Pipelines
* **Subsystem:** `01_apps/notebooks/` & `04_data_and_memory/` (`notebook-specialist`).
* **Current Gap:** `specialists/notebook_visual_data_specialist.jsonl` (3 lines), `notebook_specialist_world_training.jsonl` (0.00 MB).
* **Specific Competencies to Train:**
  1. **Marimo Reactive DAGs:** Declarative cell dependency graphs eliminating hidden notebook states.
  2. **Bidirectional Notebook-to-Module Sync:** Distilling exploratory Jupyter cells directly into production monorepo Python modules.
  3. **Zero-Mock DSP Plotting:** Streaming numpy/scipy signal processing pipelines with real-time interactive UI widgets.
* **Silicon Placement:** **Local AI Notebook Specialist 7B (Q4_K_M)** on L1 (Mac Mini) / L5 (MacBook Air).

---

### 6. 📱 Multi-Device Edge Automation & ADB Accessibility Trees
* **Subsystem:** `06_scripts_and_tooling/android/`, `termux_edge_daemon`.
* **Current Gap:** `specialists/mobile_gesture_automator.jsonl` (3 lines).
* **Specific Competencies to Train:**
  1. **Accessibility Hierarchy Parsing:** Ingesting raw `uiautomator dump` XML trees and calculating exact tap/swipe coordinates.
  2. **Android 15 Doze & Foreground Services:** Enforcing `termux-wake-lock`, battery optimization exemptions, and persistent socket listening.
  3. **Edge TPU LiteRT FlatBuffer Quantization:** Compiling models to INT8 FlatBuffers for execution on Google Tensor G5.
* **Silicon Placement:** **SmolLM2 1.7B / NanoVision 10M** on L6 (Pixel 10 Pro XL) / L7 (Samsung S20).

---

### 7. 📦 App Store Production Readiness & Native Release Compliance
* **Subsystem:** `01_apps/` (Showrunner, Zone 2, Screen Lens) & `spec-09-app-store-production`.
* **Current Gap:** `app_ecosystem_evaluations.jsonl` is only 0.09 MB.
* **Specific Competencies to Train:**
  1. **App Store Guidelines Compliance:** Automated pre-flight auditing against Apple Human Interface Guidelines and Google Play policies.
  2. **Privacy Manifest (`PrivacyInfo.xcprivacy`):** API usage classification and zero-tracking certification.
  3. **ProGuard / R8 & Native Memory Safety:** Identifying unclosed Dart StreamControllers, native FFI leaks, and preventing ACIO2 panics.
* **Silicon Placement:** **Qwen 2.5 Coder 15B (Q4_K_M)** on L3 (Linux Head Node).

---

### 8. 🛠️ SWE-Bench Multi-File AST Issue Resolution & Mutant Testing
* **Subsystem:** `04_data_and_memory/swe_bench_datasets/`, `05_agents_and_swarms/codeclash_swarm/`.
* **Current Gap:** `specialists/swe_bench_mesh_sharder.jsonl` (3 lines), `swe_bench_solutions.jsonl` (0.31 MB).
* **Specific Competencies to Train:**
  1. **Cross-File Symbol Graph Navigation:** Tracing callers/callees across Python, Go, Dart, Rust, and C++.
  2. **Minimal Surgical Patching:** Generating clean unified diffs that resolve unit tests without touching production baselines.
  3. **Mutant Test Generation:** Synthesizing adversarial test cases to catch edge-case regressions.
* **Silicon Placement:** **Qwen 2.5 Coder 32B / DeepSeek Coder V2** on L2 (MBP TB4 Vault) + L3 (Linux Node).

---

## ⚡ Recommended Next Action: Multi-Role Specialist Training Daemon

The monorepo already possesses the canonical runner:
```bash
python3 05_agents_and_swarms/training_protocols/continuous_specialist_role_trainer.py --mode daemon --interval 120.0
```
Running this daemon alongside the existing daemons will harvest authentic DPO/SFT training pairs across all **24 specialist roles**, systematically expanding their datasets from 3 lines to thousands of verified domain pairs.
