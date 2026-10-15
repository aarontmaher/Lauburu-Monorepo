# 🌐 Dual-World Simulator E-Commerce Architecture Plan: AgentWorld-35B + WebWorld-32B

## Executive Summary
This blueprint integrates **`AgentWorld-35B`** (Operating System & Syscall Simulator) and **`WebWorld-32B`** (Web DOM & Shopify Store Simulator) into the Lauburu 24/7 E-Commerce Training Engine. By adding a predictive world-modeling layer, the local and cloud AI models shift from reactive, error-prone execution to forward-simulating, regret-minimizing Monte Carlo Tree Search (MCTS) planning.

---

## 1. Problem Statement & Root Cause
Recent system penalties—unplayable notebook environments (-500 ELO), missing outline navigation (-150 ELO), and runaway browser tab sprawl (-300 ELO)—originated from **blind actuation**:
* Agents generated bash commands (`marimo edit ...`, `open http://...`) and executed them directly on macOS without anticipating OS side effects.
* A single missing `--headless` flag spawned 8 duplicate WebSocket connections, exhausting Chrome's GPU memory pool and crashing the Shopify Admin webview.

---

## 2. Dual-World Modeling Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DUAL-WORLD SIMULATION INVARIANT                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. AgentWorld-35B (OS & Syscall Simulator | Port 8086 on L3 Linux Mini)    │
│    • Simulates OS process trees, memory deltas, port binds, and GUI spawns. │
│    • Evaluates shell commands BEFORE execution: predicts if a command will   │
│      spawn tabs, consume >1 GB RAM, or leak file descriptors.              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. WebWorld-32B (Web DOM & Shopify Store Simulator | Port 8088 on L2 MBP)   │
│    • Simulates DOM trees, GraphQL mutations, cart checkouts, and customer   │
│      email counter-offers.                                                  │
│    • Predicts customer churn and margin impact without spending API tokens. │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Sovereign Master Orchestrator (Qwen 3.8 Max | Port 8082 on L1/L2 TB4)    │
│    • Dispatches MCTS rollouts across the two simulators.                    │
│    • Prunes low-reward branches; only actuates proven, clean paths.         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware Deployment Topology & Host Sanctuary (Rule 3 & Rule 10)

* **Combined VRAM Required:** ~28.5 GB (AgentWorld: 14.5 GB, WebWorld: 14.0 GB in Q4_K_M).
* **Mac Mini Host (L1) RAM Sanctuary:** Mac Mini available RAM is currently **4.09 GB (82.9% utilized)**. Under Rule 3, loading either model locally on L1 is **STRICTLY FORBIDDEN**.
* **Offloaded Routing:**
  * **`AgentWorld-35B` Endpoint:** `http://100.101.39.98:8086` (L3 Linux Head Node: AMD Ryzen 7 5700U with **12.0 GB free RAM and 26.0 GB swap**).
  * **`WebWorld-32B` Endpoint:** `http://100.103.212.21:8088` (L2 MacBook Pro with 285 GB SSD Vault over Tailscale/TB4).
* **Host Impact:** **0 MB VRAM load on the Mac Mini**. Rollouts execute via lightweight JSON over LAN.

---

## 4. Financial & Training Lake ROI

1. **$0 Cloud Spend Offline Training:** Replaces continuous cloud API grading (Gemini Pro / Claude Opus) with local self-play simulation on L2/L3 hardware.
2. **DPO Trajectory Generation:** Automatically harvests winning ($y_w$) vs. losing ($y_l$) negotiation and code execution pairs into `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`.
3. **Milestone Value:** Unlocks milestone `DUAL_WORLD_ECOMMERCE_SIMULATOR`: **+$1,200.00 AUD** capital and **+350 ELO**.
