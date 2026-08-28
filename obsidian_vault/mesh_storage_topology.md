---
title: "mesh storage topology"
tags: [whitepaper, architecture, specification]
updated: "2026-08-27"
---

# 4-Device Lauburu Mesh: Storage & Compute Topology

This document outlines the official storage and compute architecture for the 4-device mesh, utilizing **SeaweedFS** as the unified global namespace, but strictly routing traffic to respect physical network constraints (Thunderbolt 4 vs. Wi-Fi).

---

## 1. The Unified SeaweedFS Namespace
To the user, there is only **one** single folder (e.g., `/Volumes/dfs_unified` or mounted via WebDAV). 
Under the hood, SeaweedFS splits this folder into two physical Datacenters:
- **`[DataCenter: Thunderbolt]`**: The Mac Mini's internal NVMe.
- **`[DataCenter: WiFi]`**: The Linux Hub's internal NVMe.

---

## 2. Device-by-Device Breakdown

### 🖥️ 1. Mac Mini (The Storage Core)
**Role:** Master Storage Orchestrator & High-Speed Volume
- **Compute Role:** SeaweedFS Master, SeaweedFS Filer, and WebDAV Gateway.
- **Storage Role (`Thunderbolt` Datacenter):** 
  - Physically stores all **Local AI Models** (`.gguf`, Exo checkpoints, HuggingFace caches).
  - **The Champion Vault:** Serves as the ultimate vault for models that emerge victorious from the local continuous training games (Genetic MoE / ELO Leaderboard). The best-performing AI for every specialist role is enshrined here.
  - Stores high-speed LoRA fine-tuning datasets and Qdrant Vector DBs.
- **Why:** The Mac Mini sits at the center of the Thunderbolt 4 bridge. When MacBooks need to load a 30GB AI model into VRAM, they fetch it from the Mac Mini at **40 Gbps (3.6 GB/s)**.

### 💻 2. MacBook Pro (Stateless Compute)
**Role:** Heavy AI Inference & UI Rendering
- **Compute Role:** Primary workstation for rendering, coding, and heavy AI execution (Metal Performance Shaders).
- **Storage Role (Stateless):** 
  - **ZERO** permanent AI models or massive datasets are stored here. 
  - It mounts the Mac Mini's SeaweedFS WebDAV over the physical Thunderbolt cable. It streams models directly into its VRAM on-demand.

### 💻 3. MacBook Air (Stateless Compute)
**Role:** Swarm Worker & LoRA Distillation
- **Compute Role:** Runs background agent swarms and LoRA training pipelines.
- **Storage Role (Stateless):** 
  - Like the Pro, it stores **ZERO** AI models locally. It reads/writes all its training data and model weights directly to the Mac Mini over the Thunderbolt cable.

### 🐧 4. Linux Hub (Edge & Archival)
**Role:** Background Scraper, Docker Engine, & Bulk Archive
- **Compute Role:** Runs Docker containers natively. Executes 24/7 background tasks like web scraping, Tailscale subnet routing, and Petals DHT bootstrapping.
- **Storage Role (`WiFi` Datacenter):**
  - **Docker Volumes:** Kept on its native `ext4` root drive (NOT in SeaweedFS) to prevent SQLite database locking issues over the Wi-Fi network.
  - **SeaweedFS Archival:** Stores raw logs, completed `.csv` scraping outputs, and obsolete data. 
- **Why:** Connected only via Wi-Fi (168 Mbps). If it stored AI models, loading a 30GB model would take 15-20 minutes. It handles the "dirty" internet/Docker work, completely offloading that burden from the Thunderbolt bridge.

---

## 3. Migration Action Plan
*As executed via the `/goal` mandate:*
1. **Model Rescue:** Move the 12GB `Qwen3vl_32b_h3` and 10GB of `exo` models from the Linux Hub's phantom mounts *into* the Mac Mini's SeaweedFS volume.
2. **Phantom Purge:** Safely delete the remaining 200GB+ of phantom data stuck in `/mnt/nas-primary` on the Linux Hub to free up space.
3. **Volume Activation:** Once space is freed, the Linux Hub's SeaweedFS Volume Server will automatically begin accepting archival data.
