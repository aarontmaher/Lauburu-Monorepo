---
title: "Movesense Biometrics Pipeline - AI Debate Routing Consensus"
tags: [lauburu, ai-debate, biometrics, movesense, architecture]
date: "2026-10-01"
---

# 🧠 Movesense TinyML Routing Consensus
**Generated via `/ai-debate` Protocol (Tri-Orchestrator Consensus)**

## 1. The Debate Participants
- **Cloud Shadow Orchestrator:** Advocated for an Edge-heavy DSP pipeline with 70B medical models sharded across L1 and L2 via Thunderbolt 4.
- **Devil's Advocate (Qwen 3.8 Max 27B Abliterated):** Intercepted and ruthlessly dismantled the proposal based on strict hardware invariants, VRAM limits, and BLE physics.
- **Master Local Orchestrator:** Synthesizing the final architectural ruling.

## 2. The Final Consensus Architecture

The following architecture has been mathematically verified to pass the >0.98 consensus threshold without violating Lauburu Ecosystem Invariants:

### Tier A: Sensor Layer (Movesense nRF52)
* **Role:** Pure "Dumb Pipe" Acquisition.
* **Workload:** Raw 512Hz ECG and 9-axis IMU transmission over BLE GATT.
* **Critique/Ruling:** TinyML inference on the nRF52 while simultaneously streaming 512Hz data is strictly prohibited. It saturates BLE throughput, decimates the CR2025 coin-cell battery in under two hours, and destroys the high-fidelity QRS complex morphologies required for downstream BP and DFA-alpha1 DSP.

### Tier B: Edge Compute (Pixel 10 Tensor G5 AVF)
* **Role:** Feature Extraction & Buffer.
* **Workload:** Runs C++/Numpy-based DSP filters (Pan-Tompkins, DFA-alpha1 extraction).
* **Critique/Ruling:** Android Virtualization Framework (AVF) Linux microVM is strictly capped at **$\le 3.5$ GB** memory residency (Rule 9). Running a 7B model (e.g., BioMistral) requires $>7.5$ GB VRAM and will instantly trigger catastrophic swapping and thermal throttling, dropping BLE packets. 
* **Edge ML Exception:** If mesh connectivity is lost, only ultra-lightweight models that natively fit the 3.5GB constraint (e.g., SmolLM2 or quantized Qwen 2.5 Coder 1.5B/3B) are permitted to evaluate the lightweight feature arrays locally.

### Tier C: Sovereign Medical AI (Mesh & Host)
* **Role:** Deep Diagnostic Reasoning on anomalous 10-second windows.
* **Workload:** Semantic analysis of irregular HRV drops or premature ventricular contractions.
* **Critique/Ruling:** A 70B Medical Model (requiring ~41GB VRAM at Q4_K_M) is a **physical impossibility** and explicitly banned. It violates the Rule 3 Host Sanctuary (4.8GB headroom) and exceeds the total 35.6GB pooled AI capacity across L1 (Mac Mini) and L2 (MacBook Pro).
* **Final Routing:** Diagnostic requests must either be routed to the **Sovereign Duo (Qwen 3.8 Max, 1734 ELO)** running on L1/L2 via the 40Gbps TB4 Bridge, or offloaded completely to the **L3 Linux Head Node** (Rule 10 First-Offload Invariant) over 1GbE/Tailscale.

## 3. Disconnect Resilience Matrix (Rule 9 Fallback)
When transmitting feature arrays from the Edge to the Host:
1. **Primary Transport:** Wi-Fi 7 (6GHz MLO) $\rightarrow$ Tailscale Mesh.
2. **Secondary Transport:** Wi-Fi 5/LTE $\rightarrow$ Nebula Overlay.
3. **Tertiary Fallback:** Bluetooth PAN Tethering (Layer 0).
4. **Behavior on Failure:** The AVF container buffers the vectors locally using VirtioFS (`/mnt/shared`) and pauses transmission until the link recovers, ensuring no data loss.

## 4. Priority Injections
- **[APPROVED]** Eliminate all TinyML / embedded ML routines on the nRF52 codebase.
- **[APPROVED]** Restrict Pixel 10 AVF to Numpy/DSP processing and ban 7B+ parameter models from the guest VM.
- **[APPROVED]** Route semantic medical evaluation tasks to the existing Qwen 3.8 Max Sovereign engine rather than attempting to load a 70B model.
