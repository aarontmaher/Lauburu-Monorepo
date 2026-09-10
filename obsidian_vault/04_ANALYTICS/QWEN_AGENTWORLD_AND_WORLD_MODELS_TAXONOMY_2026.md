---
title: "Qwen AgentWorld & World Models Ecosystem Taxonomy 2026"
tags: [world_models, agentworld, webworld, qwen, simulation, mcts, mesh]
---

# 🌐 Complete Qwen AgentWorld & World Models Ecosystem Taxonomy (2026)

## 1. Executive Overview: What are Language World Models (LWMs)?

**Language World Models (LWMs)** serve as the **"flight simulators"** of the Lauburu autonomous agent ecosystem. Instead of executing untested commands directly on physical hardware, live APIs, or production databases, autonomous subagents run **Monte Carlo Tree Search (MCTS) dual-world simulations** inside an in-memory World Model.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DUAL-WORLD SIMULATION & VERIFICATION LOOP                                    │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Subagent Formulates Action:                                                                               │
│    • Example: "Execute `nftables` flush on GL.iNet Router" OR "Modify React DOM bounds in Storefront".      │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Predictive Rollout in AgentWorld / WebWorld (0 ms Physical Overhead, Zero Risk):                         │
│    • World Model predicts the next 10-30 environment states, return codes, and error trajectories.           │
│    • MCTS lookahead evaluates whether the action causes packet drops, layout overflows, or API regressions. │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Consensus Verification Gate:                                                                              │
│    • If Lookahead Score ≥ 98% → Dispatch to Physical Node / Staging Web Server.                              │
│    • If Lookahead Fails → Autonomous backtracking & refactor before touching live hardware.                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Taxonomy of Qwen World Models for the Lauburu Mesh

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                QWEN WORLD MODEL TAXONOMY & MESH ALLOCATION                                   │
├──────────────────────────┬──────────┬──────────┬─────────────────────────────┬───────────────────────────────┤
│ Model Identifier         │ Size     │ Quant    │ Simulation Specialization   │ Optimal Mesh Hardware Target  │
├──────────────────────────┼──────────┼──────────┼─────────────────────────────┼───────────────────────────────┤
│ **Qwen-AgentWorld-35B**  │ 35B MoE  │ Q4_K_M   │ 7-Domain Master Simulator:  │ L1 Mac Mini M4 Pro (Metal)    │
│                          │ (20.6GB) │          │ MCP, Terminal, SWE, Android │ (Port :8086)                  │
├──────────────────────────┼──────────┼──────────┼─────────────────────────────┼───────────────────────────────┤
│ **Qwen-AgentWorld-7B/8B**│ 7B / 8B  │ Q4_K_M   │ Fast Edge Tool Simulator:   │ L5 MacBook Air / L3 Linux     │
│                          │ (4.7GB)  │          │ High-speed local rollouts   │ (Port :8083 - 74 tok/s)       │
├──────────────────────────┼──────────┼──────────┼─────────────────────────────┼───────────────────────────────┤
│ **WebWorld-32B**         │ 32B      │ Q4_K_M   │ Deep Browser Simulator:     │ L1 Mac Mini + L5 Air Shard    │
│                          │ (18.4GB) │          │ A11y Tree, DOM, CSS bounds  │ (Port :8088)                  │
├──────────────────────────┼──────────┼──────────┼─────────────────────────────┼───────────────────────────────┤
│ **WebWorld-8B**          │ 8B       │ Q4_K_M   │ Rapid Web Flight Simulator: │ L2 MacBook Pro (Metal)        │
│                          │ (4.7GB)  │          │ 30+ step browser navigation │ (Port :8089 - 68 tok/s)       │
├──────────────────────────┼──────────┼──────────┼─────────────────────────────┼───────────────────────────────┤
│ **Qwen2.5-VL AgentWorld**│ 7B / 32B │ Q4_K_M   │ Multimodal GUI Simulator:   │ L6 Pixel 10 Pro XL (TPU) + L1 │
│                          │ (4.8GB+) │          │ Frame-by-frame UI forecast  │ (Port :8084)                  │
├──────────────────────────┼──────────┼──────────┼─────────────────────────────┼───────────────────────────────┤
│ **Qwen-CodeWorld (SWE)** │ 14B/32B  │ Q4_K_M   │ Repository & AST Simulator: │ L3 Linux Head Node / Ray Hub  │
│                          │ (8.5GB+) │          │ pytest & compiler execution │ (Port :8082)                  │
└──────────────────────────┴──────────┴──────────┴─────────────────────────────┴───────────────────────────────┘
```

---

## 3. Detailed Breakdown of Each World Model Variant

### 3.1 🤖 Qwen-AgentWorld-35B-A3B (The Master Multi-Domain Simulator)
* **Architecture:** Mixture of Experts (MoE) based on Qwen 2.5 with 35B total parameters (active expert routing).
* **7 Core Simulation Domains:**
  1. **`MCP (Model Context Protocol)`**: Simulates tool execution returns, JSON-RPC schemas, and tool errors without calling external APIs.
  2. **`Terminal / Bash`**: Simulates POSIX shell commands, return codes, stdout/stderr, directory listings, and process states.
  3. **`SWE (Software Engineering)`**: Simulates git operations, unit test execution (`pytest`), patch application, and compilation outputs.
  4. **`Android`**: Simulates ADB commands, UIAutomator dumps, intent dispatching, and touchscreen coordinates.
  5. **`OS / Syscalls`**: Simulates file system reads/writes, permissions, process management, and socket states.
  6. **`Web`**: Simulates HTTP requests, REST/GraphQL endpoints, status codes, and server responses.
  7. **`Search`**: Simulates search engine queries, snippet extractions, and ranking.
* **Mesh Role:** Primary gatekeeper before destructive CLI/OS commands are executed across the 7 nodes.

### 3.2 🌐 WebWorld (8B / 14B / 32B) (The Web Flight Simulator)
* **Architecture:** Trained on over 1,000,000 real-world web interaction trajectories.
* **Capabilities:**
  - Simulates 30+ step long-horizon web browsing.
  - Generates realistic accessibility trees (A11y Tree), DOM snapshots, XML/HTML, CSS bounding boxes, and simulated click responses.
  - Prevents accidental real-world transactions, API rate-limit exhaustion, or destructive web mutations during agent exploration.
* **Mesh Role:** Autonomous testing and DOM validation for the **Shopify Storefront**, **Web-TUI Portal**, and **PWA Mobile Hub**.

### 3.3 👁️ Qwen2.5-VL / Qwen3-VL AgentWorld (Multimodal Visual Frame Predictor)
* **Capabilities:**
  - Given a screenshot of an Android screen or desktop window, plus an action `click(x=340, y=720)` or `type("search")`, predicts the next visual frame without waiting for physical UI rendering.
* **Mesh Role:** Deployed on **L6 Pixel 10 Pro XL (Tensor G5 Edge TPU)** and **L7 Samsung S20+** for zero-latency mobile UI automation testing.

---

## 4. 🚀 Autonomous Integration & Deployment Plan

1. **Active Storage Vault:**
   - Pre-downloaded models already in `02_ai_models_and_inference/model_vault_gguf/`:
     - `Qwen-AgentWorld-35B-A3B-UD-Q4_K_M.gguf` (21 GB)
     - `WebWorld-32B.Q4_K_M.gguf` (18 GB)
     - `WebWorld-8B.Q4_K_M.gguf` (4.7 GB)
2. **Auto-Procurement Queue:**
   - `autonomous_model_downloader_and_benchmarker.py` is configured to automatically download `Qwen-AgentWorld-7B` for fast edge rollouts on peripheral worker nodes.
3. **Continuous LoRA Distillation:**
   - Every simulated trajectory that correctly matches real-world execution is converted into a positive DPO pair and saved to:
     `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`
