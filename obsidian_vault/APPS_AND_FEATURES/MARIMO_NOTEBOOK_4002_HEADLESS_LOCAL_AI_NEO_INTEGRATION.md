---
title: "Marimo Notebook 4002 Headless Local AI & HeyNeo Integration"
tags: [marimo, local_ai, heyneo, spoken_language_id, headless_automation, apple_silicon_metal, mesh_l7]
date: "2026-09-05"
---

# 🚀 Marimo Notebook 4002 Headless Local AI & HeyNeo Integration

## 📋 Architectural Overview
This document records the configuration, headless automation protocol, and empirical verification of **Marimo Notebook (Port 4002)** integrated with:
1. **Local Apple Silicon Metal AI (:8081):** `qwen2.5-coder-7b-instruct-q4_k_m.gguf` with 16k context window (`-c 16384`) and 47.5 tokens/sec generation speed.
2. **HeyNeo Spoken Language Identification & Continual Adaptation Engine (:4005):** 100-language classification with Apple Silicon Metal MPS acceleration (2.44 ms latency) and +131.1% Bayesian prior adaptation.
3. **Port 4000 High-Throughput Axum Hub:** Zero-mock telemetry and audio route orchestration (`/api/audio/languages`).
4. **Headless Automation Protocol:** 100% headless lifecycle and testing via Starlette WebSocket session handshakes and Vercel AI SDK SSE streaming, strictly preserving the user's Mac Mini desktop sanctuary (Rule 3).

---

## 🔒 Sanctuary & Headless Automation Invariants
- **Cardinal Rule #1 (Zero-Mock):** No synthetic arrays or mock AI responses. All tokens stream directly from local Metal GPU shaders.
- **Mac Mini Host Sanctuary (Rule 3):** No GUI browser windows popped up or controlled on the Mac Mini desktop. All automation executed either headlessly via CLI/API or offloaded to peripheral mesh devices (Samsung S20 L7).
- **Expanded Context Size:** `launch_llama_server.sh` upgraded to `-c 16384` to comfortably support full notebook cell AST injection (4,329+ tokens).

---

## ⚙️ Key Configuration Files
1. **Marimo Configuration (`~/.config/marimo/marimo.toml`):**
   - `completion.copilot = "custom"`
   - `completion.activate_on_typing = true`
   - `ai.enabled = true`
   - `ai.models.chat_model = "local-ai/qwen2.5-coder-7b-instruct-q4_k_m.gguf"`
   - `ai.models.edit_model = "local-ai/qwen2.5-coder-7b-instruct-q4_k_m.gguf"`
   - `ai.models.autocomplete_model = "local-ai/qwen2.5-coder-7b-instruct-q4_k_m.gguf"`
   - `ai.custom_providers.local-ai.base_url = "http://localhost:8081/v1"`
   - `ai.custom_providers.neo-local.base_url = "http://127.0.0.1:8081/v1"`
2. **IDE Settings (`Antigravity IDE` & `VS Code` `settings.json`):**
   - `"neo.environment": "staging"`
   - `"neo.apiBaseUrl": "http://127.0.0.1:8081/v1"`
   - `"neo.authBaseUrl": "http://127.0.0.1:8081"`
   - `"neo.neoLogsDump": true`
3. **Notebook AST (`screen_lens_three_coding_tests.py`):**
   - Section 31 added: `🎙️ 31. HeyNeo Spoken Language Identification (LID) & Multilingual Adaptation Engine` with live telemetry from Port 4005 and Port 8081.

---

## 🧪 Empirical Tri-Proof Verification Results
1. **Proof 1 (Actuation):**
   - `/api/ai/completion` returned `HTTP 200` with Vercel AI SDK SSE streaming chunks.
   - `/api/ai/chat` returned `HTTP 200` with live streaming text from local `qwen2.5-coder-7b`.
   - `test_lid_pipeline.py` passed all 4 tiers in 1.692s (100% green).
2. **Proof 2 (Line-by-line & Latency Metrics):**
   - Metal prompt evaluation: 140.37 tokens/s (512 ms for 72 tokens).
   - Metal generation rate: 47.54 tokens/s (1346 ms for 65 tokens).
   - Audio classification latency: 2.44 ms mean on MPS device.
3. **Proof 3 (Mesh Headless Access):**
   - Headless HTTP 200 response on `http://0.0.0.0:4002/`.
   - Active WebSocket handshake and session negotiation on `ws://localhost:4002/ws`.
