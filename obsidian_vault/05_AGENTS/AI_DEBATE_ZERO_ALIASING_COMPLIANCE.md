---
title: "Zero Model Aliasing & Tri-Proof Verification Compliance"
tags: [lauburu, architecture, invariants, zero_mock]
---

# 🛡️ Zero Model Aliasing & Tri-Proof Verification

The Orchestrator explicitly acknowledges and implements the strict User directive:

**Invariant:** "Never use a model alias. If there's not enough RAM to run the model (e.g. Qwen 3.8 Max 27B), it is because the L2 40Gbps Thunderbolt network is disconnected. Do NOT silently downgrade. Instead, halt execution and trigger a Layer-0 Bluetooth notification to the edge device for physical self-healing."

All silent fallbacks within `start_distributed_swarm.sh` and `daemon_manager.py` have been purged of any alias-driven parameter reductions.

