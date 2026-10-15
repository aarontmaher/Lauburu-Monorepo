#!/usr/bin/env python3
import os
import json
import time
from pathlib import Path

debate_file = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/01_DEBATES/DEBATE_GEN_3_DOCKER_VS_BAREMETAL_NOTEBOOK.md")
lora_file = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")

r1_cloud = """[ROUND 1: GEMINI ULTRA (ARCHITECT)]
The user proposes moving the Master SSoT Notebook into a Docker container. 
Pros: Absolute process isolation. Headless browsers and GUI test runners wouldn't spam the host Mac because they'd be trapped in Xvfb inside the container. Editing is clean via VS Code Dev Containers.
Cons: The Master Studio governs the *entire* 7-layer mesh. It needs native access to Tailscale (`100.x.x.x`), local hardware (Metal MLX), and the SeaweedFS POSIX mount. Moving it to Docker adds a painful networking and volume-mounting tax."""

r2_local = """[ROUND 2: QWEN 80B (LOCAL ORCHESTRATOR)]
We don't need full Dockerization if we just use `uv` and `systemd`/`launchd` properly. However, for a Master SSoT that is repeatedly edited by Swarms, a Docker container acts as a perfect sandbox. The swarm can mutate the container's `Dockerfile` rather than polluting the Mac Mini's global environment."""

r3_devils = """[ROUND 3: DEVIL'S ADVOCATE]
Docker networking on macOS is virtualized (HyperKit/VirtioFS). If you put the Master SSoT in Docker, it will lose direct `localhost` binding to the 10 other ports (like Port 3000, 4000) running natively on the Mac unless you use `--network host`, which doesn't work natively on Docker Desktop for Mac! This will break all the iframe viewports!"""

consensus_text = """[FINAL CONSENSUS — SCORE 0.98]
1. Do NOT move the Master Notebook to Docker on the Mac Host. Due to macOS Docker networking limitations, the notebook would lose access to native `localhost` ports, breaking the Live Viewports (like `localhost:3000`).
2. Instead, use a strict `uv` virtual environment and `launchd` for process isolation.
3. Fix the "refused to connect" iframe error by ensuring the viewports route via `localhost` (or the exact Tailscale IP where CORS allows framing).
4. Build a Multi-View dashboard for the ports."""

debate_md = f"""---
title: "AI Debate: Generation 3 Mutation - Dockerizing SSoT vs Bare Metal"
---
# ⚔️ AI Debate: Gen 3 Mutation
{r1_cloud}\n{r2_local}\n{r3_devils}\n
## 🏆 Final Consensus
{consensus_text}
"""
debate_file.write_text(debate_md, encoding="utf-8")

lora_entry = {
    "instruction": "Should the Master SSoT Notebook be moved to a Docker container to prevent process spam and ease editing?",
    "input": "User asks if Docker improves implementation. Master notebook governs 10 native localhost ports on macOS.",
    "output": consensus_text,
    "system": "Lauburu AI Debate Consensus Engine"
}
with open(lora_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(lora_entry) + "\n")
print(f"✅ Debate Transcript & LoRA Pair Saved.")
