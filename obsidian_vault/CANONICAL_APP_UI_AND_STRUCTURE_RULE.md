---
title: "Canonical App UI & Structural Architecture Rule"
tags: [lauburu, apps, astra, vl_models, screen_lens, architecture]
---

# 🎨 Canonical App UI & Structural Architecture

This document governs the canonical directory structure, visual design language, and autonomous UI evolution pipeline across all applications within `/Volumes/Lauburu-Monorepo/01_apps/`.

## 1. Canonical Project Structure

Regardless of the framework (Flutter, Rust wgpu, Python Textual, Next.js), all apps MUST adhere to the following standard hierarchy to allow local AI agents to traverse and modify them predictably:

```text
01_apps/<app_name>/
├── src/                  # Core application logic
│   ├── ui/               # Visual components, widgets, styles
│   ├── state/            # State management (BLoC, Redux, Stores)
│   ├── ai_bindings/      # Edge AI SDK & MCP integrations
│   └── network/          # Mesh transport (ADB, Tailscale, gRPC)
├── assets/               # Images, fonts, icons
├── tests/                # Unit and integration tests
├── docs/                 # Local architecture decisions
├── pubspec.yaml / Cargo.toml / package.json / requirements.txt
└── README.md             # Standardized App Documentation
```

## 2. Autonomous UI Evolution Pipeline (Astra + Local VL)

The visual look of the Lauburu applications is not designed manually. It is dynamically evolved using a zero-mock, real-time multimodal pipeline:

### Step A: Speculative UI Drafting (Local VL Orchestrator)
The local orchestrator (`Qwen 3.8 Max` via `prima.cpp`) formulates speculative UI code drafts (e.g., a new Flutter Flexbox layout or a Ratatui widget).

### Step B: Screen Lens Extraction
The `screen_lens_mcp_server.py` captures the current application state or UI mockup, extracting the UI salience graph and bounding boxes.

### Step C: Project Astra Teacher Evaluation
The speculative draft and the visual context are passed to the `screen_lens_astra_teacher_critique` tool.
- **Teacher Model:** Project Astra (Gemini Multimodal Live API).
- **Critique:** Astra analyzes the visual context against the proposed code, enforcing color contrast, semantic layout, and accessibility rules.

### Step D: Generational Handoff & LoRA Distillation
- If Astra approves (`VERIFIED_APPROVE`), the code is committed.
- If Astra rejects (`REJECT_WITH_FEEDBACK`), the local model recursively refines the UI code.
- **ALL interactions** are appended to `lora_datasets/proven_accuracy_vla_dataset.jsonl` for continuous 24/7 background distillation.

## 3. Visual Design Language (The "Lauburu" Aesthetic)
- **Zero-Mock Telemetry Driven:** UIs must prioritize live data. If a sensor is disconnected, the UI must explicitly display `--` rather than a simulated 0.
- **Hardware Aware:** UI animations and frame rates scale dynamically based on the active mesh layer (e.g., 120Hz on Mac M4, degraded to static text on low-battery Termux nodes).
- **Accessibility First:** High contrast, large touch targets (minimum 44x44 dp), and semantic tagging for the `flutter_a11y_agent` to audit.

