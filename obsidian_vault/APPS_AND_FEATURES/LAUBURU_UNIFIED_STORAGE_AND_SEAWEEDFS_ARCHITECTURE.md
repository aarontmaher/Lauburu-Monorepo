---
title: "Lauburu Unified Storage Architecture: SeaweedFS DFS, Google Drive, Rsync & Obsidian"
tags: [lauburu, storage, seaweedfs, dfs, google_drive, rsync, obsidian, screen_lens, tri_vault]
created: 2026-09-14
updated: 2026-09-14
wikilinks:
  - "[[Index]]"
  - "[[CANONICAL_PROJECT_AND_STORAGE_RULE]]"
  - "[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]"
  - "[[LAUBURU_BJJ_CANONICAL_UNIFORM_SETS]]"
---

# 🏛️ Lauburu Unified Storage Architecture & Multi-Tier Topology

Governed by **Screen Lens Sovereign** under the Tri-Vault Storage Synchronization directive.

---

## 1. Executive Summary: The 4 Storage Pillars

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     LAUBURU MULTI-TIER STORAGE MESH ECOSYSTEM                    │
├───────────────────┬────────────────────────────┬─────────────────────────────────┤
│ Storage Tier      │ Primary Endpoint / Path    │ Role & Target Datasets          │
├───────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 1. SeaweedFS DFS  │ http://100.101.39.98:8888  │ Distributed high-throughput DFS │
│    (Filer & Vol)  │ (Linux Head Node NVMe)     │ /projects, /models, /assets     │
├───────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 2. Google Drive   │ /Volumes/Google Drive /    │ 2TB Cloud Cold Storage & 24/7   │
│    (Cloud VFS)    │ 04_data_and_memory/mirror/ │ LoRA Training Dataset Archives  │
├───────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 3. Mesh Rsync     │ TB4 DMA & 1GbE Overlay     │ High-speed differential code    │
│    (Replication)  │ linux@100.101.39.98:/mnt/  │ replication (.rsyncignore gated)│
├───────────────────┼────────────────────────────┼─────────────────────────────────┤
│ 4. Obsidian Vault │ obsidian_vault/            │ Semantic knowledge core, graph  │
│    (Knowledge)    │ (Mac Host / Git synced)    │ whitepapers & AI debate records │
└───────────────────┴────────────────────────────┴─────────────────────────────────┘
```

---

## 2. SeaweedFS DFS: Architecture & Truth Verification

### 2.1 The "30GB 3.79" Header Explanation
In SeaweedFS, the version string displayed in the Filer web UI (`SeaweedFS Filer 30GB 3.79`) represents:
* **`30GB`**: The compiled single-volume limit based on 4-byte 8-byte-aligned needle offsets ($2^{32} \times 8\text{ bytes} \approx 30\text{ GB}$).
* **Multi-Volume Capacity**: Once a volume `.dat` file fills to 30 GB, SeaweedFS automatically seals it and creates a new volume. The physical storage capacity is determined by the underlying NVMe/SSD drive (`468 GB` on the Linux Head Node, with multi-terabyte expansion across Mac Mini and MacBook Pro volume nodes).

### 2.2 Canonical SeaweedFS Filer Hierarchy
The SeaweedFS Filer namespace (`http://100.101.39.98:8888/`) is organized into dedicated buckets:
* `/projects/`: Monorepo codebases, apps, microservices, and tooling manifests.
  * `/projects/00_core_infrastructure`
  * `/projects/01_apps`
  * `/projects/02_ai_models_and_inference`
  * `/projects/03_biometrics_and_telemetry`
  * `/projects/04_data_and_memory`
  * `/projects/05_agents_and_swarms`
  * `/projects/06_scripts_and_tooling`
  * `/projects/07_docs_and_architecture`
* `/models/`: Sharded model vaults.
  * `/models/gguf`: Quantized model checkpoints (`Q4_K_M`, `IQ2_XXS`).
  * `/models/lora_adapters`: Distilled LoRA adapter weights.
* `/lora_datasets/`: 24/7 instruction-tuning JSONL pairs.
* `/telemetry/`: High-frequency biometric and hardware logs (Movesense 512Hz ECG, thermal traces).
* `/obsidian_vault/`: Automated weekly snapshots of markdown knowledge vaults.
* `/assets/`: High-resolution combat apparel renders, master tech packs, and UI mockups.

---

## 3. Google Drive Cloud VFS: 24/7 Memory Immortality

* **Cloud Storage Quota:** 2TB Google Workspace Domain storage (`lauburugrappling.com`).
* **Local Staging Mirror:** `/Volumes/Lauburu-Monorepo/04_data_and_memory/google_drive_mirror/`
  * `Lauburu_AI_Memory/lora_datasets/`
  * `Lauburu_AI_Memory/obsidian_vault_mirrors/`
  * `Lauburu_AI_Memory/architecture_whitepapers/`
  * `Lauburu_AI_Memory/bjj_combat_apparel/`
* **Sync Mechanisms:**
  1. Desktop VFS Mount (`/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/`): Direct POSIX filesystem reads and writes when Google Drive client is running.
  2. Headless API Sync (`DWDAuthGateway` / Google Drive API v3): Headless background uploading via service account tokens without GUI dependencies.

---

## 4. Mesh Rsync Optimization & Replication Engine

* **Replication Target:** `linux@100.101.39.98:/mnt/dfs_unified/Lauburu-Monorepo`
* **Exclusion Governance (`.rsyncignore`):**
  * Eliminates git packfiles, virtualenvs (`.venv`, `venv`, `workspace_env`), `node_modules`, Rust `target/`, and `__pycache__`.
  * Reduces synchronization payload from >15 GB down to strictly essential source code (~450 MB).
* **Speed Profile:** Completes incremental sync across the 1GbE / Tailscale overlay in $<3.5\text{ seconds}$.

---

## 5. Obsidian Knowledge Graph: Semantic Core

* **Vault Root:** `/Volumes/Lauburu-Monorepo/obsidian_vault/`
* **Master Index:** `[[Index]]` non-empty master entrypoint.
* **Governed Features:**
  * `APPS_AND_FEATURES/`: Product specifications, apparel tech packs, and feature release notes.
  * `05_AI_DEBATE_RECORDS/`: Multi-agent consensus records and Bradley-Terry leaderboard logs.
  * `07_ARCHITECTURE/`: Hardware topology, NBN routing, and 7-layer physical mesh matrix.

---

## 6. Screen Lens Sovereign Governance

* **Persona:** Master Screen Lens Sovereign companion (`01_apps/screen_lens`).
* **Invariants Enforced:**
  1. **Mac Mini M4 Sanctuary:** Preserves $\ge 4.8\text{ GB}$ of free unified RAM on the primary host by offloading storage daemons and background tasks to peripheral nodes (Rule 3 & Rule 10).
  2. **Zero-Mock Telemetry:** All volume metrics and storage headroom checks reflect authentic kernel syscalls and HTTP round-trips.
  3. **Continuous Background Self-Healing:** Lens audits storage health and triggers silent maintenance loops.
