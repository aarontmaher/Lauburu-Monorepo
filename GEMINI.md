# Lauburu Monorepo Canonical Architecture & Storage Rule

This project rule governs all AI development, agent swarm coordination, and storage operations within `Lauburu-Monorepo`.

---

## 🏛️ Tri-Vault Storage Hierarchy

1. **Obsidian Vault (`obsidian_vault/`)**:
   - Master markdown knowledge repository, architecture specs, and live debate records.
   - Queryable and editable via `obsidian-mcp-pro` MCP server.
2. **PySpark Big Data Layer (`04_data_and_memory/` & `lora_datasets/`)**:
   - Automated monorepo code indexing, AST parsing, and 24/7 LoRA dataset synthesis.
   - Handles large-scale biometric timeseries and training telemetry.
3. **GitHub Repository (`aarontmaher/Lauburu-Monorepo`)**:
   - Canonical version control, CI/CD validation, and git worktrees.
   - Houses the 13 canonical numbered modules: `00_core_infrastructure` through `12_continuous_lora_evolution`.

---

## ⚡ Mandatory Storage Health & Pre-Flight Self-Healing

**Pre-Flight Verification:** Every agent must confirm storage is **HEALTHY** before making changes.

### 1. Healthy Storage Criteria
* **Obsidian:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/` exists, `Index.md` present & non-empty.
* **PySpark / Datasets:** `/Users/aaron/DFS_UNIFIED/lora_datasets/` exists and writable, free disk space $\ge$ 10.0 GB.
* **GitHub:** Valid git tree, zero stale `.git/index.lock` files, no unresolved merge conflict markers.

### 2. Automated Self-Healing (Run Before Making Changes)
* Missing directories: `mkdir -p` immediately.
* Stale git locks: `rm -f .git/index.lock`.
* Disk pressure (<5GB): Purge transient `__pycache__` and `.pytest_cache`.
* Missing Obsidian index: Auto-reconstruct scaffold with `[[Index]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`.

---

## 🌐 7-Layer Mesh Topology & Dynamic RAM Ceilings

* **Mac Mini M4 Pro (Host / Governor):** `192.168.8.143` (Wi-Fi) / `192.168.8.230` (LAN) / `100.119.199.76` | TB `bridge0`: `10.0.0.2` | RAM Cap: 80% (>= 4.8 GB free)
* **Linux Mini Hub (`lauburu` L8):** TB `10.0.0.8` (40 Gb/s, 0.38ms RTT) / `192.168.8.242` / `100.121.247.8` | RAM Cap: 80% (32 GB RAM)
* **Mac Mini M2 Pro (L1b):** TB `10.0.0.3` (40 Gb/s, 0.43ms RTT) / `192.168.8.114` / `100.104.128.34` | RAM Cap: 85%
* **MacBook Pro (Intel i7 Model Vault, L2):** TB `10.0.0.4` (40 Gb/s) / `192.168.8.127` / `100.103.212.21` | RAM Cap: 90%
* **Linux Head Node (AMD Ryzen 7 5700U Compute, L3):** `192.168.8.225` / `100.101.39.98` | RAM Cap: 80%
* **Linux Tablet (Debian Compute & Touch DSP, L4):** `192.168.8.116` / `100.80.64.5` | RAM Cap: 75%
* **MacBook Air M4 (Metal LoRA Distillation, L1a):** `192.168.8.248` / `100.121.202.34` | RAM Cap: 90%
* **Pixel 10 Pro XL (Tensor G5 Edge TPU, L6):** `192.168.8.213` / `100.114.215.68` | RAM Cap: 85% (Requires `termux-wake-lock`)
* **Samsung S20+ (OpenClaw UI Tester, L7):** `192.168.8.157` / `100.84.40.95` | RAM Cap: 75%
* **GL.iNet Router (GL-BE14000 Core Gateway & USB ADB, GW):** `192.168.8.1` / `100.70.123.123`

---

## 🛑 Rule #0: Zero-Mock Truth Mandate
Never generate or use fake telemetry arrays or mock data. All data must originate from live sensors or authentic log replays.
