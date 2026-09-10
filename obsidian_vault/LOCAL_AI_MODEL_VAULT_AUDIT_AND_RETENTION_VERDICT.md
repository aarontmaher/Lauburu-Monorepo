---
title: "Lauburu Mesh Local AI Vault Audit, Testing & Model Retention Verdict"
tags: [local_ai, model_vault, thunderbolt4, sharding, lora, zero_mock, host_sanctuary]
timestamp: "2026-09-04T13:56:39.914572+00:00"
---

# 🧠 Lauburu Mesh Local AI Vault Audit, Testing & Model Retention Verdict

**Governed by:** [[CANONICAL_PROJECT_AND_STORAGE_RULE]], [[Rule_1_Zero_Mock]], [[Rule_2_Tri_Vault_Storage]], and [[Rule_3_Host_Sanctuary]].

---

## 🌐 1. Multi-Node Storage & Memory Headroom Status

| Node | Physical RAM | Available RAM | Total Disk | Free Disk | Storage Pressure | Live Inference Services |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mac Mini M4 Pro (L1 Host)** | 24.0 GB | 12.1 GB | 460 GiB | **12.0 GiB** | 98% (Host Sanctuary Target $\ge 10$ GB) | `:8083` Qwen 3.8 Max Abliterated (Devil's Advocate) |
| **MacBook Pro M4 (L2 Vault)** | 16.0 GB | 6.7 GB inactive | 466 GiB | **9.3 GiB** | 98% (Critical Storage Limit) | `:8081` Qwen2.5-VL-7B, `:50052` ggml-rpc-server |
| **Linux Head Node (L3 Compute)** | 16.0 GB | 13.1 GB | 468 GiB | **14.0 GiB** | 97% (Storage Constrained) | `:50052` ggml-rpc-server, `:8080` Qwen3-VL, Exo P2P |

---

## ⚡ 2. Model Roles, Purposes & Retention Matrix

### 2.1 Vision-Language Models (VLM)
- **`Qwen2.5-VL-32B-Instruct.Q4_K_M.gguf` (18 GB - MacBook Pro):** Flagship Sovereign VLA Copilot. Provides high-resolution Set-of-Marks visual UI grounding, multi-window layout tree parsing, and zero-cloud desktop DOM analysis. **[KEEP]**
- **`Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` (4.4 GB - Mac Mini & MacBook Pro :8081):** Real-time UI/UX Truth Auditor. Drives continuous 10–15 FPS screen monitoring, sequential click-through auditing, and visual graph verification on edge testbeds. **[KEEP]**
- **`Kimi-VL-A3B-Thinking-2506-Q4_K_M.gguf` (9.8 GB - MacBook Pro):** Multimodal Chain-of-Thought Visual Reasoner. Interprets ECG/PPG sensor waveforms and complex multi-panel diagrams. **[KEEP]**
- **`SmolVLM-Instruct-Q4_K_M.gguf` (1.0 GB - Mac Mini):** Sub-100ms ultra-low-latency edge OCR. **[KEEP]**

### 2.2 70B+ Frontier Weights & Heavy Reasoning
- **`DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf` (40 GB - MacBook Pro):** Canonical 70B Reasoning Teacher. Sharded over the 10Gbps Thunderbolt 4 bridge (0.54ms RTT) for whole-monorepo AST analysis, deep mathematical proofs, and synthetic LoRA distillation. **[KEEP]**
- **`DeepSeek-R1-Distill-Llama-70B-IQ2_XXS.gguf` (18 GB - MacBook Pro):** Single-node emergency fallback for running 70B reasoning within a single 16GB–24GB node memory envelope. **[KEEP]**
- **`Llama-3.3-70B-Instruct-abliterated-Q4_K_M.gguf` (40 GB - MacBook Pro):** Heavy Frontier Devil's Advocate for AI Debate and security boundary probing. **[KEEP]**
- **`dbrx-instruct.Q3_K_M.gguf` (37 GB - MacBook Pro):** 16x MoE Engine (36B active out of 132B). Ultra-fast coding and multi-turn refactoring. **[KEEP]**
- **`gemma-4-31B-it-Q4_K_M.gguf` (17 GB - MacBook Pro):** Dense instruction and zero-error structured JSON function caller. **[KEEP]**
- **`Meta-Llama-3.1-70B-Instruct-IQ2_M.gguf` (21 GB - MacBook Pro):** Redundant baseline. **[RECOMMEND ARCHIVE/REMOVE: Frees 21 GB]**

### 2.3 Mathematical Models & Critical Storage Cleanup
- **`Qwen2.5-Math-72B-Instruct-Q4_K_M.gguf` (45 GB - Linux Node):** Canonical Math Engine for Pan-Tompkins QRS DSP, DFA-alpha1, and PTT blood pressure algorithms. **[KEEP]**
- **`math_rm_72b` Safetensors Shards (133 GB - Linux Node `/home/linux/math_rm_72b`):** Raw unquantized FP16 source files. The quantized GGUFs already exist in `gguf_vault`. **[URGENT PURGE: Immediately recovers 133 GB on Linux NVMe, dropping usage from 97% to 68%!]**
- **`Qwen2.5-Math-72B-Instruct-IQ2_XS.gguf` (26 GB - Linux Node):** Redundant on Linux where Q4_K_M is present. **[RECOMMEND PURGE: Frees 26 GB]**

### 2.4 Corrupted / Broken Download Shards
- `Mixtral-8x22B-Instruct-v0.1.Q3_K_M-00001-of-00002.gguf` (43 MB) — **[PURGE]**
- `Mixtral-8x22B-Instruct-v0.1.Q3_K_M-00002-of-00002.gguf` (96 MB) — **[PURGE]**
- `command-r-plus-IQ3_S.gguf` (302 MB) — **[PURGE]**
- `Hermes-3-Llama-3.1-8B-Q5_K_M.gguf` (420 MB) — **[PURGE]**

---

## 🛠️ 3. Empirical Test Proofs

1. **Local Devil's Advocate (Port 8083):**
   - Model: `Qwen-3.8-Max-Abliterated` (Q4_K_M, 7.6B params)
   - Prompt Evaluation: 323.8 tok/s
   - Generation Speed: 25.7 tok/s
   - Status: Active and responsive
2. **MacBook Pro VLM Inference (Port 8081 over 10Gbps TB4 Bridge):**
   - Target: `169.254.215.118:8081`
   - Latency: 0.54 ms RTT link latency
   - Model: `Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`
   - Host Memory Impact: 0.0 MB added to Mac Mini Host RAM
3. **Linux Head Node Distributed RPC (Port 50052):**
   - Active daemon: `ggml-rpc-server -H 0.0.0.0 -p 50052`
   - Available System RAM: 13,072 MB
   - CPU: AMD Ryzen 7 5700U (16 threads active)

---

## 💾 4. Total Recoverable Headroom
By executing the recommended cleanup:
- **Linux Head Node:** Reclaim **159 GB** (`math_rm_72b` 133 GB + `IQ2_XS` 26 GB) $	o$ Free space increases from 14 GB to **173 GB**.
- **MacBook Pro:** Reclaim **21.8 GB** (`Meta-Llama-3.1-70B-IQ2_M` 21 GB + broken shards 861 MB) $	o$ Free space increases from 9.3 GB to **31.1 GB**.
- **Mac Mini Host:** Preserves $\ge 12.0$ GiB without downloading duplicate 70B weights.
