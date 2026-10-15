---
title: "Dual-Layer Canonical Control Plane Architecture"
tags: [architecture, tui, notebooks, bluetooth, marimo, rule_10]
date: "2026-09-15"
status: "APPROVED_SWARM_CONSENSUS_V2"
---

# 🛸 Dual-Layer Canonical Control Plane Architecture

This architecture dictates the separation, rendering, and offloading of the Lauburu Ecosystem's visual tracking planes, strictly enforcing **Rule 9 (Bluetooth Constraints)** and **Rule 10 (Linux Mini First-Offload)**.

## Executive Summary
The Lauburu Mesh is governed by a Dual-Layer control plane:
*   **Layer 1 (L0 Edge / TUI):** An omnipresent, IP-less, headless Terminal UI. The Pixel 10 natively bridges the BLE connection and broadcasts metrics to the entire mesh.
*   **Layer 2 (L3 Hub / Notebook):** A highly visual, stateful, browser-based Marimo DAG Notebook. Used for deep biometrics DSP (ECG/PTT), Qdrant metrics, and 8K vision tracking.

---

## 📡 Layer 1: The Headless TUI (Bluetooth L0 Edge)
The TUI is the baseline survival layer (Pillar III of the Fundamental Baseline Trinity). 

### 1. The Pixel Native BLE Gateway (User Override)
*   **The Constraint:** Android Termux CANNOT run Python `bleak` scripts.
*   **The Solution:** The Google Pixel 10 Pro XL (L6) acts as the **Native BLE Gateway**. A native Android Kotlin Foreground Service (or Flutter method channel) binds directly to the Movesense GATT NUS UUIDs (`6E400001-B5A3...`). 
*   **Mesh Broadcast:** The Pixel holds the physical Bluetooth connection and relays the raw serial string payloads out to the rest of the network (L1, L2, L3) via a ZeroMQ PUB/SUB socket or by appending to the SeaweedFS `seaweedfs://lora_datasets/tui_telemetry_stream.jsonl` mount via ADBFS.

### 2. UI Framework
*   **Mesh-Wide Rendering:** Because the Pixel broadcasts the raw metrics globally, ANY device on the network can spin up the `polyglot-go-bubbletea-specialist` or `textual` TUI client. The TUI simply subscribes to the Pixel's ZeroMQ broadcast, rendering the data headlessly over SSH or local terminal without needing its own Bluetooth hardware connection.

---

## 📊 Layer 2: The Stateful Notebook (Observation Plane)
The Notebook layer handles rich analytics without relying on heavy React/Node.js web frontends.

### 1. Technology Stack
*   **Framework:** Marimo (Reactive DAG Python Notebook).
*   **Execution:** `marimo run lens_dashboard.py` or `voila` serving `.ipynb`.

### 2. Constraint Enforcement (Rule 10: Host Sanctuary)
*   **L1 Kill-On-Sight Protocol:** Running Jupyter, Marimo, or IPykernel on the Mac Mini (L1) violates the 4.8 GB RAM host sanctuary and is **STRICTLY PROHIBITED**. Screen Lens Sovereign will continuously poll `ps aux` and auto-kill these PIDs on L1.
*   **L3 Pinning:** The notebook server is hard-pinned to the **L3 Linux Head Node** (`100.101.39.98:8890`). It will be managed natively as a Systemd service (`lauburu-notebook.service`).

### 3. Seamless Integration (TUI -> Notebook)
The Marimo Notebook on L3 reads the exact same SeaweedFS log file (or ZeroMQ stream) that the Pixel is broadcasting. Because Marimo uses a Directed Acyclic Graph (DAG), it instantly patches live `mo.ui.table` or `mo.ui.altair_chart` components via its background WebSockets—producing a 60 FPS dashboard atop the TUI layer.
