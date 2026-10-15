---
title: "MCTS Test-Time Compute (TTC) Protocol"
tags: [mcts, ttc, lauburu, orchestration, ai_mesh, protocol]
---

# 🧠 MCTS Test-Time Compute Protocol (aka MTCP)

## Overview
The MCTS Test-Time Compute Protocol is the canonical reasoning framework implemented across the Lauburu AI Mesh. It enables smaller local edge models (e.g., 7B, 9B, 1.5B parameters) to achieve frontier-level reasoning by offloading deep thinking to a multi-step **Monte Carlo Tree Search**.

This protocol mitigates the weaknesses of single-shot autoregressive generation in small models. 

## Component Architecture
1. **Generator Nodes:** Edge devices (e.g., `L5_MacBook_Air`, `L3_Linux_Hub`) running fast coding or instruction models. These generate discrete reasoning steps (branches).
2. **Critic Nodes (PRM):** Adversarial models (e.g., `L2_MacBook_Pro`) acting as Process Reward Models. They evaluate the soundness of each reasoning branch and assign a score (0.0 to 1.0).
3. **Sovereign Master:** The final synthesis node (`L1_Mac_Host` running Qwen 3.8 Max) which takes the verified reasoning tree and outputs the definitive answer.

## Recent Continuous Development
- **True Tree Search:** Upgraded from a simple Best-of-N generator to a real depth-first/breadth-first iterative expansion `MCTSNode` tree.
- **Continuous LoRA Harvesting:** Implemented `mcts_lora_harvester.py` daemon to automatically sweep high-scoring MCTS traces into the PySpark Data Lake (`lora_datasets/continuous_mcts_traces.jsonl`). This fulfills the autonomous optimization rule, allowing smaller models to natively internalize Test-Time Compute strategies.

## Execution
* `06_scripts_and_tooling/automation/mesh_mcts_orchestrator.py`
* `06_scripts_and_tooling/automation/mcts_lora_harvester.py`
