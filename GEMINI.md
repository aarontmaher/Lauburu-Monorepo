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

* **Mac Mini M4 Pro (Host / Governor):** `192.168.8.230` / `100.119.199.76` | RAM Cap: 90%
* **MacBook Pro (Metal GPU RPC & Model Vault):** `192.168.8.127` / `100.103.212.21` (TB4: `169.254.187.138`) | RAM Cap: 90%
* **Linux Head Node (Docker Hub & Compute):** `192.168.8.224` / `100.101.39.98` | RAM Cap: 80%
* **Linux Tablet (Debian Compute & Touch DSP):** `100.81.92.125` | RAM Cap: 75%
* **MacBook Air (Metal LoRA Distillation):** `192.168.8.222` / `100.93.158.96` | RAM Cap: 90%
* **Pixel 10 Pro XL (Tensor G5 Edge TPU):** `100.73.38.87` | RAM Cap: 85% (Requires `termux-wake-lock`)
* **Samsung S20+ (OpenClaw UI Tester):** `100.84.40.95` | RAM Cap: 75%
* **GL.iNet Router (Core Gateway & USB ADB):** `192.168.8.1` / `100.122.185.123`

---

## 🛑 Rule #0: Zero-Mock Truth Mandate
Never generate or use fake telemetry arrays or mock data. All data must originate from live sensors or authentic log replays.
