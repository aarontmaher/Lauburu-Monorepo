# Lauburu Mesh Storage Topology

## 1. Primary Host (Mac Mini M4 Pro - L1)
- **Role:** Primary host and memory governor for all project files and repositories (`/Users/Shared/aaron/DFS_UNIFIED/Lauburu-Monorepo`).
- **Hardware:** Apple M4 Pro (Mac16,11), 24 GB Unified RAM.
- **Sync Mechanism:** Syncthing and direct 40 Gb/s Thunderbolt 4 DMA access to L8 `lauburu`.
- **Purpose:** High-speed monorepo management, Screen Lens Sovereign Vision Core, and Tri-Vault storage synchronization.

## 2. Thunderbolt 4 Model Vault & Compute Hub (Linux Mini lauburu - L8)
- **Role:** Secondary high-RAM storage and primary GGUF Model Vault (`/home/linuxmini/model_vault_gguf/`).
- **Hardware:** Intel Core i7-8700B (12 cores), 32 GB RAM, Ubuntu 24.04 LTS.
- **Link:** 40 Gb/s Thunderbolt 4 (`bridge0` IP `10.0.0.8`, 0.36 ms avg RTT).
- **Purpose:** Storage offloading and Tier 0 high-bandwidth distributed AI inference.

## 3. SeaweedFS Unified Storage Layer
- **Role:** Dedicated unified distributed storage layer for large datasets, Parquet data lakes, and Screen Lens telemetry.
- **Exclusive Paths:** 
  - `lora_datasets`: Continuous LoRA training datasets.
  - `screen_lens_telemetry`: Screen Lens Sovereign visual data and frame captures.
- **Node Access:** L1, L8, L2, L3, L1a, L6, L7.
- **Active Endpoints:** Ports 8085, 8087, 8888, 9333.
