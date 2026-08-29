---
title: "System 2 Mac Host Daemon — Autonomous Memory & Task Governor"
updated: "2026-08-29T12:00:00Z"
tags: [system2, daemon, mac_host, memory_governor, tri_vault, zero_mock]
---

# 🖥️ System 2 Mac Host Daemon

The **System 2 Mac Host Daemon** executes on the primary host node (Apple Silicon M4 Pro Mac Mini, `192.168.8.230` / `100.119.199.76`), governing high-level deliberation, dynamic RAM constraints (<=90% ceiling / 21.6GB AI cap), background batch processing, and Tri-Vault storage integrity.

## 🏛️ Core Responsibilities
1. **Dynamic RAM & Compute Governance:** Enforces that host memory remains within safe operating envelopes.
2. **Tri-Vault Knowledge Core Sync:** Guarantees Obsidian notes, PySpark Lake, and Git worktree synchronization.
3. **Daemon Supervised Matrix:** Oversees continuous operations across Ports 8080-8086, 18802, 50052, and 8088.
4. **Autonomous Reflex Healing:** Reacts sub-second to network drops, stale locks, and memory pressure.

## 🔗 Related Notes
- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[TRI_ORCHESTRATOR_AI_DEBATE]]
