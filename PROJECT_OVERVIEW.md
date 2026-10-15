# 🧠 Lauburu AI Ecosystem - Canonical Project Overview

**MANDATORY BOOTSTRAP DOCUMENT FOR ALL NEW AI AGENTS**
Any new AI agent joining the Lauburu Ecosystem MUST parse this file to understand the physical hardware constraints, strict operational laws, storage architecture, and the established sovereign hierarchy before executing any commands or making code modifications.

---

## 1. 🌐 The 7-Layer Physical Mesh Network Topology & Hardware Matrix

The Lauburu Mesh pools **108.0 GB RAM (82.8 GB Usable AI VRAM)** across 7 physical layers to enable multi-agent inference, live VLA (Vision-Language-Action), and continuous LoRA training without cloud reliance.

| Layer | Node Name | Network Role | Local IP | Tailscale IP | RAM / AI Cap | Key Roles & Protocols |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Primary Host & Memory Governor | `192.168.8.230` | `100.119.199.76` | 24.0 GB (21.6 GB) | Apple M4 Pro Mac Mini. Prompt Ingestion & Memory Governor. |
| **L2** | `MacBook_Pro` | Metal GPU RPC & Storage Vault | `192.168.8.127` | `100.103.212.21` | 16.0 GB (14.0 GB) | Intel MacBook Pro. 40Gbps Thunderbolt 4 Bridge (`bridge0`). |
| **L3** | `Linux_Mini` | Gateway Ingress & Compute Hub | `192.168.8.224` | `100.101.39.98` | 16.0 GB (13.8 GB) | AMD Ryzen 7 5700U Docker Hub & Petals DHT Hub. |
| **L4** | `Linux_Tablet` | Mobile Linux Compute | DHCP | `100.81.92.125` | 8.0 GB (6.5 GB) | Debian Tablet, secondary Petals worker. |
| **L5** | `MacBook_Air` | Secondary High-Speed Worker | `192.168.8.222` | `100.93.158.96` | 16.0 GB (14.0 GB) | Apple M4 MacBook Air, Metal Performance Shaders. |
| **L6** | `Pixel_10_Pro_XL` | 8K Vision Stream & Edge TPU | DHCP | `100.73.38.87` | 16.0 GB (12.5 GB) | Tensor G5, Edge TPU, UWB 3D. |
| **L7** | `Samsung_S20` | Dedicated Automated UI Tester | DHCP | `100.84.40.95` | 12.0 GB (9.0 GB) | Exynos 990, ADB Target. |

**Pre-Flight Invariant:** Model sharding between L1 and L2 uses the 40Gbps Thunderbolt 4 Bridge (`bridge0`) yielding 0.544ms RTT. Slower mesh layers mandate `llama.cpp` pipeline parallelism over Tensor Parallelism. Any VRAM tasks that can be spared MUST be offloaded to **L3 Linux Head Node** to preserve L1 Mac Mini Sanctuary Headroom (always maintain >=4.8GB free).

---

## 2. 🏛️ Canonical Tri-Vault Storage Architecture

All knowledge, telemetry, and source code are strictly synchronized across three foundational storage tiers:

1. **Obsidian Vault (Human & Semantic Core)**
   - **Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/`
   - Stores architecture whitepapers, AI debate consensus, graph-linked rules, and continuous audit logs.
2. **PySpark & Big Data Lake (High-Throughput)**
   - **Path:** `/Users/aaron/DFS_UNIFIED/lora_datasets/` & `04_data_and_memory/`
   - Stores 24/7 LoRA pairs, 435K+ LOC indexes, vector DBs, and 512Hz ECG streams.
3. **GitHub Repository & Worktrees (Version Control)**
   - **Path:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`
   - Canonical application code, microservices, and Docker Compose manifests.

**Pre-Flight Storage Gate:** AI agents must execute the self-healing storage script to ensure all directories exist, disk space is >= 5.0 GB, and `.git/index.lock` is clear before any execution.

---

## 3. 👑 The Dynamic ELO Meritocracy & Sovereign Model Governance

Model selection is strictly meritocratic based on empirical performance (Bradley-Terry Swarm Leaderboard). Hardcoded assumptions of supremacy are forbidden.

*   **Sovereign Master Local Orchestrator:** **`Qwen 3.8 Max 27B Abliterated`** (1734 ELO).
    *   Endpoint: `http://127.0.0.1:8082` (Port 8082).
    *   Engine: `prima.cpp` Pipelined-Ring Parallelism over the TB4 DMA Bridge.
    *   Mandate: Leads all architectural consensus and multi-agent coordination. Exclusively bound to the `/screen-lens-sovereign` capability for Vision-Language-Action execution.
*   **Adversarial Red Team (Devil's Advocate):** **`Qwen 3.8 Max`** (Standard)
    *   Endpoint: `http://127.0.0.1:8083` (Port 8083).
    *   Mandate: Relentless red-team stress testing. Zero prompts to external APIs.
*   **Subordinate Syntax Worker:** **`Qwen 2.5 Coder 7B`** (Port 8081).
    *   Mandate: Strictly acts as a fast micro-linter and single-file syntax parser. NEVER acts as the Master Orchestrator.

---

## 4. 🛡️ Fundamental Baseline Trinity

Agents MUST NOT attempt to deprecate, replace, or overwrite these three highly-tested foundational pillars:
1. **`prima.cpp` Engine:** The sovereign engine for all local orchestration.
2. **Network Healer Daemons:** Native shell scripts running as background daemons (`mesh_unhealable_notifier_daemon.py`, etc) managing IP routing and Tailscale self-recovery. NEVER schedule via cloud-agent crons.
3. **Bluetooth PAN Full-Mesh (Layer 0):** The omnipresent IP-less control plane to recover dead Wi-Fi/Tailscale links.

---

## 5. 🛑 Core Project Directives & Truth Verification

1. **Rule 1: Zero-Mock & Truth Verification:** Absolutely NO simulated data, mocked arrays, or synthetic telemetry. All outputs must stem from physical processes.
2. **The Tri-Proof Interceptor Gate:** Any claim of task completion (e.g., "success", "fixed") automatically triggers a mandatory gate requiring empirical proof: (1) Exit Code 0, (2) SHA256/Byte Counts, (3) Visual Screen/Diff Proof. Unverified claims result in token slashing.
3. **Untouched Baseline Sandbox:** Production code (`01_apps/`, `00_core_infrastructure/`) is 100% UNTOUCHED during autonomous experiments. All tests must run in `01_apps/screen_lens/sandbox_evolution/`.
4. **Specialist Delegation ("No Generalist" Mandate):** Agents must assume specific personas (e.g., polyglot-bash-posix-specialist) or delegate via subagents when crossing domains.

---

## 6. 👁️ Autonomous Self-Evolution & Document Maintenance

This `PROJECT_OVERVIEW.md` is a living entity, autonomously managed by the **Screen Lens VLA & Abliterated Duo**.

*   **Continuous VLA Monitoring:** Screen Lens Sovereign continuously monitors device telemetry, background daemons, and developer workflows using `/screen-lens-sovereign`.
*   **The AI Debate Synchronization:** When network topography shifts, a new default ELO leader emerges, or new hardware is added, the Qwen 3.8 Max Sovereign Duo engages in an `/ai-debate`.
    *   The *Master Orchestrator* proposes updates to this `PROJECT_OVERVIEW.md`.
    *   The *Adversarial Red Team* challenges the updates, ensuring no core invariants (e.g., L1 Mac Sanctuary Headroom) are violated.
*   **Tri-Vault Crystalization:** Upon reaching consensus, the changes are written directly to this file, indexed in `obsidian_vault`, and exported to `lora_datasets/` for 24/7 background conditioning of future models. This ensures zero human intervention is required to maintain complete project context.
