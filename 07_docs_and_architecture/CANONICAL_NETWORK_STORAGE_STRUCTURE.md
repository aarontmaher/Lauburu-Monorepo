---
title: "Canonical Network Storage Structure & SeaweedFS Unification"
tags: [storage, architecture, seaweedfs, screen_lens, universal_namespace]
date: "2026-09-15"
status: "APPROVED_CONSENSUS"
---

# 🗄️ Canonical Network Storage Structure

**Problem Statement:** Local path definitions like `/Volumes/Android_DFS` (macOS), `/mnt/dfs_unified` (Linux), and `/sdcard/DFS` (Android) fragment the AI Swarm's context. When cloud agents or distributed subagents attempt to parse file paths, OS-specific roots cause hallucinated paths and failed executions.

**Consensus Solution:** Screen Lens Sovereign will enforce a **Universal SeaweedFS Namespace** across the entire 7-layer mesh. Local mounts will exist, but the Swarm will *only* communicate via the canonical Filer paths.

## 1. The Universal Filer Namespace (`seaweedfs://`)
All agents and swarms MUST reference files using the virtual SeaweedFS Filer URI (`seaweedfs://` or `http://100.101.39.98:8888/`). 

### Core Directory Tree
```text
seaweedfs://
├── /core_infrastructure/   (Docker Compose, Tailscale ACLs, Systemd Daemons)
├── /ai_models/             (GGUF Vault, LoRA Checkpoints, Exo P2P configs)
├── /biometrics/            (Raw ECG Streams, PTT Blood Pressure CSVs)
├── /lora_datasets/         (24/7 DPO Trajectories, Swarm Debate Transcripts)
├── /obsidian_vault/        (Master Knowledge Graph, SKILL_OUTPUTS, Markdown)
└── /edge_mounts/           (Dynamic FUSE mounts from Mobile Nodes)
    ├── /pixel_10_dcim/     (Live 8K Vision Stream Dumps)
    └── /samsung_s20_ui/    (OpenClaw uiautomator XML hierarchies)
```

## 2. Local OS Translation Map (For Native I/O)
While the AI context uses `seaweedfs://`, local Bash/Python scripts executed by Lens will map to these exact physical mount points:

| Layer / OS | Physical Mount Point | Daemon Responsible |
| :--- | :--- | :--- |
| **L1/L2 (macOS)** | `/Users/aaron/DFS_UNIFIED/` | `weed mount -filer=...` (macFUSE) |
| **L3 (Linux Hub)** | `/mnt/dfs_unified/` | `weed mount` (FUSE) |
| **L6/L7 (Android)** | `/data/local/tmp/dfs_unified/` | `rclone mount` / `adbfs` |

## 3. Screen Lens Sovereign's Governance Role
The `lens_canonical_storage_governor.py` daemon will continuously:
1. **Lint File Paths:** Scan prompt logs and Git commits to ensure agents are using the `seaweedfs://` namespace, not OS-specific paths.
2. **Auto-Mount Enforcement:** If a node loses its local mount (e.g., MacFUSE crashes), Lens will automatically restart the `weed mount` daemon.
3. **Data Deduplication:** Continuously run `weed shell` commands to compact volumes and enforce retention limits on `/lora_datasets/`.
