---
title: "Qwen 3.8 Max 27B Pinning Specification: Local Orchestrator & Devil's Advocate"
updated: "2026-08-29T04:55:00Z"
tags: [lauburu, qwen_3_8_max, ai_debate, local_orchestrator, devils_advocate, abliterated, unabliterated, swarm]
---

# 🧠 Qwen 3.8 Max 27B Pinning Specification

## 1. Executive Summary
This document establishes the canonical disk paths, memory allocations, and port assignments for pinning **Qwen 3.8 Max 27B / Qwen3.8-Flash-Next** as the **Master Local Orchestrator (Unabliterated)** and **Qwen 2.5 / 3.8 Abliterated** as the **Devil's Advocate** across the Lauburu AI Debate Protocol and persistent Swarm architecture.

---

## 📍 2. Identified Inodes & Model Vault Locations

### 2.1 Local Orchestrator (Unabliterated)
*   **Model Designation:** `Qwen 3.8 Max 27B / Qwen3.8-Flash-Next (Uncensored / Full CoT)`
*   **Local GGUF Shards:**
    *   `/Users/aaron/models/Qwen3.8-Flash-Next/Qwen3.8-Flash-Next-UD-Q2_K_XL-00001-of-00003.gguf`
    *   `/Users/aaron/models/Qwen3.8-Flash-Next/Qwen3.8-Flash-Next-UD-Q2_K_XL-00002-of-00003.gguf`
    *   `/Users/aaron/models/Qwen3.8-Flash-Next/Qwen3.8-Flash-Next-UD-Q2_K_XL-00003-of-00003.gguf`
*   **MLX Apple Silicon Shard:**
    *   `/Users/aaron/.exo/models/mlx-community--Qwen3.8-27B-4bit/`
*   **Active Inference Port:** Port `8081` (llama.cpp RPC mesh / Exo P2P)
*   **Role:** Master Local Orchestrator driving prompt execution, codebase AST analysis, and zero-cost high-context reasoning.

### 2.2 Devil's Advocate (Abliterated)
*   **Model Designation:** `Qwen 2.5 / 3.8 7B/32B Instruct Abliterated`
*   **Local GGUF Vault Path:**
    *   `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/model_vault_gguf/Qwen2.5-7B-Instruct-abliterated.Q4_K_M.gguf`
*   **Active Inference Port:** Port `8083` (with Mistral Nemo 12B on Port `8082` fallback)
*   **Role:** Uncensored, adversarial adversary ruthlessly challenging assumptions, exposing edge-case regressions, and testing mathematical consensus thresholds (>0.98).

---

## ⚙️ 3. Skill & Client Configuration Updates

1. **AI Debate Skill Definition:** [`/Users/aaron/.gemini/config/skills/ai-debate/SKILL.md`](file:///Users/aaron/.gemini/config/skills/ai-debate/SKILL.md)
   * Local AI Orchestrator pinned to `Qwen 3.8 Max 27B / Qwen3.8-Flash-Next` (Unabliterated).
   * Devil's Advocate pinned to `Qwen 3.8 / 2.5 Abliterated` at Port 8083.
2. **Devil's Advocate Client:** [`05_agents_and_swarms/ai_debate/devils_advocate_client.py`](file:///Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/ai_debate/devils_advocate_client.py)
   * Priority 1 server configured for `Qwen-Abliterated` on Port 8083.

---

## 🔗 Related Vault References
- [[Index]] — Master Knowledge Vault Core
- [[ai-debate]] — Tri-Orchestrator AI Debate Protocol
- [[AI_ROUTER_FREE_TIER_ARCHITECTURE]] — Multi-Tier AI Gateway Specification
- [[COMPREHENSIVE_FREE_AI_TIERS_RESEARCH_AND_DEBATE]] — Free AI Tiers Stacking Matrix
