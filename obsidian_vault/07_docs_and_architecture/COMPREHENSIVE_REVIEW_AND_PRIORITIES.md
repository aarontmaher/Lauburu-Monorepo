---
title: "Tri-Orchestrator Review: LoRA, Lens, & Bluetooth"
tags: [architecture, lora, bluetooth, screen_lens, ai_debate]
---

# 🧠 Comprehensive Architectural Review & Injection

*Date: Sept 10, 2026*
*Trigger:* Manual `/ai-debate` command
*Scope:* LoRA Pipeline, Bluetooth Terminal, Screen Lens Companion, Project Overview

## 1. LoRA Training Pipeline Integration
**Current State:** The Multi-Cloud Harvester is actively dumping high-end reasoning traces from Astra, Fable, Gemini, etc., into `continuous_lora_dataset.jsonl`.
**Optimal Integration:**
*   **Event-Driven MLX Trigger:** Instead of a fixed cron job, the MLX LoRA training script should listen to the file size of `continuous_lora_dataset.jsonl`. Once it hits 1,000 new pairs, it triggers an isolated training run on the MacBook Air (L5 - Metal Performance Shaders worker).
*   **Sandbox Safety (Rule 4):** All weight merging (SLERP/TIES) must happen strictly within `01_apps/screen_lens/sandbox_evolution/`. The new weights must pass an automated ELO benchmark against the base model before replacing the active `qwen_38_max` weights.
*   **Danger:** Overfitting on "cloud synthetic style" (e.g., the model learns to talk like an AI). The dataset must heavily interleave your actual human code commits and terminal logs to maintain the raw developer persona.

## 2. Bluetooth Terminal Feedback
**Current State:** Provides critical local RF proximity routing when Wi-Fi/Tailscale fails.
**Vulnerabilities Identified:**
*   **Android Doze Mode:** The Android host will inevitably attempt to aggressively sleep the Bluetooth daemon, causing packet drops.
*   **Mac CoreBluetooth Resets:** The macOS stack occasionally drops PAN connections during high CPU load.
**Improvement Directives:**
*   **Local Queuing (Store-and-Forward):** The terminal must implement a local SQLite or append-only file buffer. If the BLE socket drops, it queues commands/telemetry and burst-transmits them upon reconnection.
*   **Keepalive Injection:** Force an aggressive `termux-wake-lock` and a 15-second BLE heartbeat ping to prevent the Android scheduler from suspending the terminal process.

## 3. Screen Lens Sovereign / Life Companion App
**Current State:** Continuous multimodal VLA monitoring user context.
**Vulnerabilities Identified:**
*   **Context Bloat / Token Hemorrhage:** Passing continuous UI frames into a 128K context window will cause an Out-Of-Memory (OOM) crash in minutes, destroying the Mac's 9.6GB RAM sanctuary (Rule 3).
*   **Privacy & Keylogging:** Unfiltered screen capture grabs passwords and sensitive auth tokens.
**Improvement Directives:**
*   **Speculative Token Reduction (Keyframing):** Stop sending continuous video/images. Implement a rapid structural diffing algorithm (e.g., SSIM). Only send a new frame to the AI when the screen structure changes by > 15%.
*   **DOM/Accessibility Tree Translation:** Instead of passing raw pixels, use macOS Accessibility APIs or Android UIAutomator to extract the screen as an XML tree. Text/XML consumes 99% less VRAM than image tensors.

## 4. Overall Project Trajectory
The Lauburu 7-Layer Mesh is a masterpiece of hardware leverage. You have successfully unified Apple Silicon, Linux, and Android into a single compute fabric, bypassing cloud costs via the Quota Harvester. 

**The Primary Threat:** *Daemon Sprawl.* 
With so many daemons running (Quota Harvester, Network Healer, Zombie Reaper, MLX trainer), the system is vulnerable to silent failures. 
**Next Step Priority:** Build a unified TUI (Terminal User Interface) Dashboard that tracks the PID and heartbeat of every daemon across the 7 layers. If a daemon hangs, the TUI must visually alert you so it can be restarted via the Network Resurrection Engine.

---

## 📌 Top 5 Verified Priorities (Injected via Debate)
1. **[LORA]** Implement file-size-triggered MLX training in the isolated sandbox, replacing dumb cron jobs.
2. **[BLUETOOTH]** Implement Store-and-Forward SQLite packet buffering for the Bluetooth Terminal to survive Doze mode drops.
3. **[LENS]** Switch Screen Lens from continuous video streaming to SSIM-based "Keyframing" to save VRAM.
4. **[LENS]** Route Screen Lens vision payloads through OCR/Accessibility XML translation rather than raw image tensors.
5. **[CORE]** Develop a unified `master_mesh_tui.py` Dashboard to track the heartbeat of all newly spawned background daemons.
