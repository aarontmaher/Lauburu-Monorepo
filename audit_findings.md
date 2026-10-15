# 🔍 Comprehensive Project-Wide Audit Report: Lauburu 7-Layer Mesh & Canonical TUI Ecosystem

```
========================================================================================
AUDIT REPORT: LAUBURU MONOREPO DOCUMENTATION, CANONICAL TUI & INFRASTRUCTURE MATRIX
Generated: 2026-09-15 | Working Group: worker_tui_harden_1
Auditing Standards: Canonical Hardware Matrix (Rule 0), Zero-Mock Truth (Rule 1),
                    Tri-Vault Storage (Rule 2), Host Sanctuary (Rule 3),
                    Sovereign Local AI Hierarchy (Rule 7), Pre-Flight Sharding (Rule 8),
                    Fundamental Baseline Trinity (Rule 10), Linux Mini First-Offload (Rule 10)
Status: COMPREHENSIVE MULTI-SURVEY SYNTHESIS (38+ DISCREPANCIES CATALOGED)
========================================================================================
```

---

## 1. Executive Summary

A project-wide architectural audit and code-level investigation was conducted across the **Lauburu Monorepo**, encompassing:
- `01_apps/canonical_port/tui/` (The Canonical Textual Terminal User Interface Command Center)
- `06_scripts_and_tooling/network/` (Mesh IP matrix, network daemons, self-healers)
- `07_docs_and_architecture/` (Master architecture guides, hardware guides, context maps)
- `obsidian_vault/` (Knowledge graph topology notes, device matrices)
- `00_core_infrastructure/` & `05_agents_and_swarms/` (Incident auto-healers, tournament engines)

This synthesis consolidates findings from three independent survey reports (`spec_miner_survey_3`, `explorer_survey_2`, and `explorer_survey_1`). Across the codebase, **38+ distinct high-impact discrepancies, architectural hallucinations, Rule 1 (Zero-Mock) violations, and hardware configuration drift** have been cataloged.

### Primary Root Causes
1. **Silicon Architecture Hallucination:** Presumption that all Apple devices in the cluster are Apple Silicon M-series unified memory chips, falsely labeling the L2 MacBook Pro (an **Intel Core i7** x86_64 system) as M1 Pro, M3 Pro, or M4 Pro.
2. **Destructive Global Find-and-Replace:** Automated replacements corrupted hardware documentation, swapping `Ryzen 7` and `RyzenAdj` with `Intel 2018 Mac Mini (Linux)` and `Intel 2018 Mac MiniAdj`.
3. **Ghost Hardware & Retired Router Persistence:** The TP-Link VX230v AX1800 gateway, which was retired due to a 1Gbps bottleneck, remains provisioned and polled in multiple automation scripts and network views.
4. **Sovereign Local AI Hierarchy Drift:** Fragmentation of port roles, where Port 8081, 8082, and 8083 were interchangeably assigned to obsolete models (Llama 3.3 70B, Kimi 72B, Mistral Nemo 12B) in direct violation of the **Qwen 3.8 Max Mandate** and **`prima.cpp` PRP Invariant**.
5. **Zero-Mock Violations & Missing Authentic Waiting States:** Widespread emission of pseudo-random data (`random.randint`, `random.randbytes`), hardcoded telemetry rows in views, and fallback constants (e.g., 482.0 Mbps, 12.4 ms, 18.5ms TTFT, 92.4 readiness) instead of clean waiting states (`--`).

---

## 2. Canonical Truth vs. Monorepo Deviations

### 2.1 7-Layer Physical Mesh Hardware Matrix (Core Rule 0 & user_global)

The Lauburu Mesh pools **108.0 GB System RAM (82.8 GB Usable AI VRAM)** across 7 physical layers plus 1 core gateway:

| Layer | Node Name | Canonical Hardware Truth | Canonical Network Truth | Monorepo Hallucinations & Inaccuracies Found |
| :---: | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` | Apple M4 Pro Mac Mini (24GB Unified RAM, 12C CPU/16C GPU) | Local: `192.168.8.230`<br>TS: `100.119.199.76`<br>Wi-Fi 7 (802.11be), 10GbE | • Dynamic RAM cap set to 90.0% instead of Rule 3's 80.0% (4.8 GB free buffer).<br>• Outdated IP `192.168.8.155` hardcoded in telemetry models. |
| **L2** | `MacBook_Pro` | **Intel Core i7** (6C x86_64, AMD Radeon GPU, **Wi-Fi 5 802.11ac**, No Unified Memory) | Local: `192.168.8.127`<br>TB4 Bridge: **`169.254.187.138`**<br>TS: `100.103.212.21` | • **Pervasively hallucinated as Apple M1 Pro, M3 Pro, or M4** in docs, TUI views, and scripts.<br>• Claims Wi-Fi 7 MLO 6GHz capability.<br>• TB4 bridge IP wrongly recorded as `169.254.44.77` or `169.254.215.118`. |
| **L3** | `Linux_Mini` | **AMD Ryzen 7 5700U** (Dell Inspiron 15 3525, 8C/16T, Realtek RTL8821CE **Wi-Fi 5**, 1GbE/2.5GbE) | Local: `192.168.8.224`<br>TS: `100.101.39.98`<br>Wi-Fi 5 ONLY (No 6GHz) | • **Pervasively documented as "Intel 2018 Mac Mini (Linux)"** with 16 cores.<br>• Global find-and-replace corrupted `RyzenAdj` to `FlyGoat/Intel 2018 Mac MiniAdj`. |
| **L4** | `Linux_Tablet` | Debian Linux Tablet (ARM64 Quad-Core, 8GB RAM / 6.5GB AI, Wi-Fi 5/6) | TS: `100.81.92.125`<br>DHCP LAN, Wi-Fi 5/6 ONLY | • Falsely attributed Wi-Fi 7 MLO in router consensus documentation.<br>• Layer inverted with L5 in storage context map. |
| **L5** | `MacBook_Air` | Apple M4 MacBook Air (16GB Unified RAM, 8C CPU/10C GPU, Wi-Fi 7 MLO) | Local: `192.168.8.222`<br>TS: **`100.93.158.96`**<br>Wi-Fi 7 (802.11be) | • **Tailscale IP wrongly recorded as `100.121.202.34`** in `mesh_ip_matrix.json` and `nomad_courier_self_healer.py`.<br>• Triggers 125% CPU socket spin loop per Rule 8. |
| **L6** | `Pixel_10_Pro_XL` | Google Tensor G5 (Edge TPU, 16GB RAM / 12.5GB AI, Android 15 Termux) | TS: `100.73.38.87`<br>Port 8022 (Non-root)<br>Wi-Fi 7 (802.11be) | • Wi-Fi IP inconsistencies (`192.168.8.145` vs `192.168.8.160` vs `192.168.8.189`). |
| **L7** | `Samsung_S20` | Samsung Exynos 990 (12GB RAM / 9.0GB AI, Wi-Fi 5/6, USB ADB target) | TS: `100.84.40.95`<br>Alt TS: `100.99.123.58`<br>Port 8022 (Non-root) | • Local IP variations (`192.168.8.105` vs `192.168.8.118` vs `192.168.8.214`). |
| **GW** | `GL.iNet Router` | MediaTek MT7988A/MT7986 ARM64, Wi-Fi 7 MLO (GL-MT3600BE) | LAN: `192.168.8.1`<br>TS: `100.122.185.123`<br>**TP-Link AX1800 is RETIRED** | • **TP-Link VX230v AX1800 actively provisioned and probed** across daemons and TUI probers. |

---

### 2.2 Sovereign Local AI Hierarchy & Port Governance (Rules 7, 8, 10)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 CANONICAL LOCAL AI MODEL ROSTER & HIERARCHY                              │
├──────┬──────────────────────────────┬──────────────────┬─────────────────┬──────────────────────────────┤
│ Port │ Canonical Model Designation  │ Model ID         │ Host / Route    │ Canonical Role & Invariants  │
├──────┼──────────────────────────────┼──────────────────┼─────────────────┼──────────────────────────────┤
│ 8082 │ Qwen 3.8 Max                 │ qwen_38_max      │ 127.0.0.1 (L1)  │ SOVEREIGN MASTER ORCHESTRATOR│
│      │                              │                  │                 │ via prima.cpp PRP over TB4   │
├──────┼──────────────────────────────┼──────────────────┼─────────────────┼──────────────────────────────┤
│ 8083 │ Qwen 3.8 Max 27B Abliterated │ qwen_38_max_abli │ 100.101.39.98/L3│ CANONICAL DEVIL'S ADVOCATE   │
│      │                              │                  │                 │ Adversarial Red Team         │
├──────┼──────────────────────────────┼──────────────────┼─────────────────┼──────────────────────────────┤
│ 8081 │ Qwen 2.5 Coder 7B            │ qwen2.5-coder-7b │ 100.101.39.98/L3│ SUBORDINATE SYNTAX WORKER    │
│      │                              │                  │                 │ Fast single-file code only   │
├──────┼──────────────────────────────┼──────────────────┼─────────────────┼──────────────────────────────┤
│ 8084 │ Screen Lens VLA / Vision     │ screen_lens_vla  │ 100.101.39.98/L3│ Multimodal Vision Compute    │
├──────┼──────────────────────────────┼──────────────────┼─────────────────┼──────────────────────────────┤
│ 8085 │ Kimi VL / Multimodal Context │ kimi_vl_context  │ 127.0.0.1 (L1)  │ Context Specialist           │
├──────┼──────────────────────────────┼──────────────────┼─────────────────┼──────────────────────────────┤
│50052 │ Distributed GGML-RPC Matrix  │ llama.cpp RPC    │ 169.254.187.138 │ TB4 Distributed Tensor Shard │
└──────┴──────────────────────────────┴──────────────────┴─────────────────┴──────────────────────────────┘
```

#### Major Governance Invariants:
1. **Qwen 3.8 Max Supremacy:** Port 8082 is the sole, exclusive Master Local Orchestrator. Assigning Llama 3.3 70B, Mistral Nemo 12B, or Kimi 88B to Port 8082 violates user_global §7.
2. **Qwen 2.5 Coder 7B Invariant:** Port 8081 is strictly a subordinate syntax worker. It is prohibited from acting as orchestrator or leading debates. Naming it `qwen38_standard_orchestrator` in `nomad_courier_self_healer.py` is a direct violation.
3. **Pillar I (`prima.cpp`) Inclusion:** `prima.cpp` is the canonical Sovereign Engine for Local Orchestration over the 40Gbps TB4 DMA Bridge. It must be exposed in all engine selector dropdowns and headers.
4. **Linux Mini First-Offload (Rule 10):** Port 8083 (Devil's Advocate), Port 8081 (Syntax Worker), and Port 8084 (Screen Lens) default to L3 Linux Mini (`100.101.39.98`) to spare Mac Mini host VRAM.

---

### 2.3 Host RAM Sanctuary & Dynamic Headroom (Rule 3)

- **Canonical Limit:** Mac Mini M4 Pro (24 GB) host MUST strictly preserve $\ge 4.8\text{ GB}$ free physical RAM (utilization $\le 80\%$).
- **Observed Deviations:**
  - `hardware_screen.py` checked `Rule 3: >= 9.6GB` (an outdated 40% threshold).
  - `blackboard_models.py` configured `dynamic_cap_pct = 90.0` for L1.
  - `daemon_manager.py` and `nomad_courier_self_healer.py` used disk headroom check of `free_gb >= 5.0` instead of canonical $\ge 10.0\text{ GB}$.

---

## 3. Comprehensive Catalog of 38+ Identified Discrepancies

| Item # | Target File & Line(s) | Category | Description of Hallucination / Defect | Canonical Ground Truth | Severity |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **D01** | `01_apps/canonical_port/tui/models/blackboard_models.py:1457` | Hardware Matrix | L2 model string set to `"Apple Silicon TB4 Bridge Node"` while arch is `"x86_64"`. | L2 is **Intel Core i7** MacBook Pro (x86_64, Wi-Fi 5). | **CRITICAL** |
| **D02** | `01_apps/canonical_port/tui/models/blackboard_models.py:363, 403-404` | Hardware Matrix | `from_dict` explicitly overwrites `"Intel"` with `"Apple Silicon"`. | Remove the overwrite logic; preserve Intel Core i7 identity. | **CRITICAL** |
| **D03** | `01_apps/canonical_port/tui/models/blackboard_models.py:1465` | Hardware Matrix | L3 labeled `"Intel 2018 Mac Mini (Linux)"` with 16 cores. | L3 is **AMD Ryzen 7 5700U** (8C/16T, Realtek Wi-Fi 5). | **CRITICAL** |
| **D04** | `01_apps/canonical_port/tui/models/blackboard_models.py:1443` | RAM Governance | L1 `dynamic_cap_pct = 90.0`. | Set to `80.0%` (Host Sanctuary $\ge 4.8\text{ GB}$ free RAM). | **HIGH** |
| **D05** | `01_apps/canonical_port/tui/models/blackboard_models.py:1541-1604` | Model Roster | Port 8081 mapped to Kimi 72B; Port 8082 mapped to Meta Llama 3.3 70B; Port 8083 mapped to Genetic MoE. | Port 8082: Qwen 3.8 Max; Port 8083: Qwen 3.8 Max 27B Abliterated; Port 8081: Qwen 2.5 Coder 7B. | **CRITICAL** |
| **D06** | `01_apps/canonical_port/tui/models/blackboard_models.py:1649` | Zero-Mock | Generates synthetic LoRA dataset count: `pairs_count = 3650 + (i * 120)`. | Remove arithmetic formula; report authentic count or `--`. | **HIGH** |
| **D07** | `01_apps/canonical_port/tui/models/blackboard_models.py:1397` | Network Matrix | L2 Tailscale peer OS set to `"macOS Darwin ARM64"`. | Must be `macOS Darwin x86_64`. | **MEDIUM** |
| **D08** | `01_apps/canonical_port/tui/models/network_telemetry.py:321` | Network Matrix | L2 peer node claims ARM64 architecture. | Update to `x86_64`. | **MEDIUM** |
| **D09** | `01_apps/canonical_port/tui/models/network_telemetry.py:375` | Network Matrix | Hardcodes L1 Mac Mini local IP as `192.168.8.155`. | Update canonical IP to `192.168.8.230`. | **MEDIUM** |
| **D10** | `01_apps/canonical_port/tui/services/blackboard_store.py:283-329` | Zero-Mock | `probe_internet_speed()` falls back to `482.0 Mbps`, `48.0 Mbps`, `1420 RPM`, `12.4 ms` if networkQuality fails. | Default to `None` and display authentic waiting state (`--`). | **CRITICAL** |
| **D11** | `01_apps/canonical_port/tui/services/blackboard_store.py:701-839` | Zero-Mock | L2-L7 nodes default to ONLINE with static thermals rather than reflecting unreachable state. | Mark unreachable nodes as OFFLINE / STANDBY with `"--"` metrics. | **HIGH** |
| **D12** | `01_apps/canonical_port/tui/services/lauburu_dht_daemon.py:17-24` | Zero-Mock | Emits fake DHT gossip with `random.randint(-2, 3)`, `random.randint(1000, 5000)`, and `random.randbytes(4)`. | Eliminate pseudo-random generators; use authentic DHT state. | **CRITICAL** |
| **D13** | `01_apps/canonical_port/tui/views/network_view.py:196-202` | Zero-Mock / HW | Hardcoded Wi-Fi client rows assert L2 is `MacBook_Pro (M1 Pro)` on `Wi-Fi 7 MLO (6GHz) Ch 37 / 320 MHz 2400 Mbps`. | Remove hardcoded rows; L2 is Intel Core i7 Wi-Fi 5; use live telemetry or waiting rows. | **CRITICAL** |
| **D14** | `01_apps/canonical_port/tui/views/hardware_noc_view.py:86-88` | Zero-Mock | Hardcoded GW fallback row: `12% (0.4)`, `38°C NOM`, `0.18ms`. | Display authentic waiting state (`--`) for unprobed GW. | **HIGH** |
| **D15** | `01_apps/canonical_port/tui/views/hardware_noc_view.py:139-140` | Zero-Mock | Hardcoded fallback readiness score (`92.4`) and CNS strain (`2.1`). | Display clean waiting state (`--`) when sensor is disconnected. | **HIGH** |
| **D16** | `01_apps/canonical_port/tui/views/biometrics_view.py:160-184` | Zero-Mock | When `ms.connected` is False, displays `512 Hz`, `Battery: 94%`, `NOMINAL`, and Kamath rejection `1.42%`. | Display clean disconnected waiting panel (`[bold red]● DISCONNECTED[/bold red]`, `--`). | **CRITICAL** |
| **D17** | `01_apps/canonical_port/tui/views/biometrics_view.py:120-140` | Zero-Mock | Displays nominal autonomic recovery (92.4%) without physical sensor stream. | Render waiting state (`--`). | **HIGH** |
| **D18** | `01_apps/canonical_port/tui/widgets/canonical_header_bar.py:157-158` | Zero-Mock | Reactive defaults set to `ttft_ms = 18.5`, `tok_per_sec = 64.2`. | Initialize reactive defaults to `0.0` or `None` and render `"--"`. | **HIGH** |
| **D19** | `01_apps/canonical_port/tui/widgets/canonical_header_bar.py:281` | Zero-Mock | TB4 RTT fallback hardcoded to `"0.28ms"`. | Render `"--"` or `STANDBY` when TB4 link is unlinked. | **HIGH** |
| **D20** | `01_apps/canonical_port/tui/widgets/canonical_header_bar.py:134-154` | Model / Engine | `prima` engine missing from engine selector options. | Add `("⚡ PRIMA.CPP (Pipelined-Ring TB4 DMA)", "prima")`. | **HIGH** |
| **D21** | `01_apps/canonical_port/tui/widgets/live_speedtest_card.py:58-64` | Zero-Mock | Initializes with fake speed metrics (`482.5 Mbps ⬇`, `48.0 Mbps ⬆`, `1420 RPM`). | Default metrics to `None` and render `"--"`. | **HIGH** |
| **D22** | `01_apps/canonical_port/tui/widgets/engine_selector.py:78-98` | Model / Engine | `prima` missing from engine options list. | Add `("⚡ PRIMA.CPP (Pipelined-Ring TB4 DMA)", "prima")`. | **HIGH** |
| **D23** | `01_apps/canonical_port/tui/screens/hardware_screen.py:92` | RAM Governance | Condition checks `Rule 3: >= 9.6GB`. | Update to canonical `Rule 3: >= 4.8GB` (utilization $\le 80\%$). | **MEDIUM** |
| **D24** | `06_scripts_and_tooling/network/mesh_ip_matrix.json:12` | Network Matrix | L2 `tb4_bridge` IP set to `"169.254.44.77"`. | Update to canonical **`169.254.187.138`**. | **CRITICAL** |
| **D25** | `06_scripts_and_tooling/network/mesh_ip_matrix.json:37` | Network Matrix | L5 `tailscale` IP set to `"100.121.202.34"`. | Update to canonical **`100.93.158.96`**. | **CRITICAL** |
| **D26** | `06_scripts_and_tooling/network/mesh_ip_matrix.json` | Retired Hardware | TP-Link AX1800 listed as active node. | Mark TP-Link AX1800 as `RETIRED`. | **HIGH** |
| **D27** | `06_scripts_and_tooling/network/nomad_courier_self_healer.py:73, 238` | Network Matrix | L5 Tailscale IP configured as `100.121.202.34:50052`. | Update to **`100.93.158.96:50052`** to avoid socket hang. | **CRITICAL** |
| **D28** | `06_scripts_and_tooling/network/nomad_courier_self_healer.py:51-56` | Model Hierarchy | Port 8081 named `"qwen38_standard_orchestrator"` while loading `qwen2.5-coder-7b`. | Rename to `"qwen25_coder_syntax_worker"`. | **CRITICAL** |
| **D29** | `06_scripts_and_tooling/network/nomad_courier_self_healer.py:57-62` | Model Hierarchy | Port 8082 loading Mistral Nemo 12B. | Update to Qwen 3.8 Max (prima.cpp PRP). | **HIGH** |
| **D30** | `07_docs_and_architecture/08_hardware_guides/DELL_INSPIRON_3525_BATTERY_AND_CHARGING_GUIDE.md` | Doc Corruption | Corrupted find-replace tokens: `FlyGoat/Intel 2018 Mac MiniAdj`, `Intel 2018 Mac Mini (Linux)`, `Intel 2018 Mac Mini 5700U`. | Restore `FlyGoat/RyzenAdj` and `AMD Ryzen 7 5700U`. | **CRITICAL** |
| **D31** | `07_docs_and_architecture/CANONICAL_PROJECT_OVERVIEW.md:38` | Hardware Matrix | L2 listed as `Apple M4 Pro TB4`. | L2 is **Intel Core i7** (x86_64). | **CRITICAL** |
| **D32** | `07_docs_and_architecture/CANONICAL_PROJECT_OVERVIEW.md:39` | Hardware Matrix | L3 listed as `Intel 2018 Mac Mini (Linux)`. | L3 is **AMD Ryzen 7 5700U**. | **CRITICAL** |
| **D33** | `07_docs_and_architecture/CANONICAL_PROJECT_OVERVIEW.md:25` | RAM Governance | Host Sanctuary cited as $\ge 8.0\text{ GB}$, $\le 90\%$. | Rule 3 canonical: $\ge 4.8\text{ GB}$ free RAM, utilization $\le 80\%$. | **MEDIUM** |
| **D34** | `07_docs_and_architecture/CANONICAL_PROJECT_OVERVIEW.md:7, 20` | Memory Pool | Cites `85.02 GB` pooled AI VRAM. | Canonical pool is **82.8 GB Usable AI VRAM** (108.0 GB RAM). | **MEDIUM** |
| **D35** | `07_docs_and_architecture/STORAGE_ARCHITECTURE_CONTEXT_MAP.md:21-25` | Topology Drift | Layer inversion: L3 listed as MacBook Air, L4 as Linux Mini, L5 as Linux Tablet. | Restore canonical sequence: L3 Linux Mini, L4 Linux Tablet, L5 MacBook Air. | **HIGH** |
| **D36** | `07_docs_and_architecture/ROUTER_ORCHESTRATOR_CONSENSUS.md:109` | RF Physics | Falsely attributes `Wi-Fi 7 MLO` to L4 Linux Tablet. | L4 is Wi-Fi 5/6 only. Only L1, L5, L6, GW support Wi-Fi 7. | **MEDIUM** |
| **D37** | `06_scripts_and_tooling/network/daemon_manager.py:64-78` | Model Hierarchy | Port 8082 allocated to Mistral Nemo; Port 8083 to Qwen Coder. | Port 8082 is Qwen 3.8 Max; Port 8083 is Qwen 3.8 Max Abliterated. | **HIGH** |
| **D38** | `00_core_infrastructure/mesh_incident_auto_healer.py:57, 176` | Model Hierarchy | Designates Port 8085 as Primary inference router instead of Port 8082. | Port 8082 is Master Orchestrator; Port 8085 is Context Specialist. | **HIGH** |
| **D39** | `01_apps/canonical_port/backend/training_telemetry_collector.py:848` | Zero-Mock | Vulnerability rate calculated via arithmetic modulo formula. | Remove synthetic formula; report authentic collector data. | **MEDIUM** |
| **D40** | `01_apps/canonical_port/tui/services/mesh_optimization_algorithms.py:36, 65` | Zero-Mock | Routing weights and fitness generated using `random.random()`. | Replace pseudo-random fitness with kernel RTT probing. | **MEDIUM** |

---

## 4. Remediation Architecture & Implementation Plan

The remediation plan executes across three functional phases:

### Phase 1: Canonical TUI Hardening (`01_apps/canonical_port/tui`)
1. **Model Synchronization (`models/blackboard_models.py`, `models/network_telemetry.py`):**
   - Correct L2 definition: Intel Core i7, Wi-Fi 5 (802.11ac), x86_64, TB4 bridge `169.254.187.138`. Strip out the `from_dict` overwrite.
   - Correct L3 definition: AMD Ryzen 7 5700U, Realtek RTL8821CE Wi-Fi 5.
   - Set L1 dynamic cap to 80.0% (Host Sanctuary $\ge 4.8\text{ GB}$).
   - Rebind Local AI Model Roster: Port 8082 = `Qwen 3.8 Max`, Port 8083 = `Qwen 3.8 Max 27B Abliterated`, Port 8081 = `Qwen 2.5 Coder 7B`. Prune Kimi on 8081 and Llama 3.3 on 8082.
   - Prune synthetic LoRA dataset formula (`pairs_count = 3650 + (i*120)`).
2. **Telemetry & Service Hardening (`services/blackboard_store.py`, `services/lauburu_dht_daemon.py`):**
   - Eliminate hardcoded `482.0 / 48.0 Mbps` and `12.4 ms` fallbacks in `probe_internet_speed()`. Default to `None` / `"--"`.
   - Update node status mapping so unreachable nodes report `OFFLINE` / `STANDBY` rather than false `ONLINE` states with synthetic thermals.
   - Remove pseudo-random gossip generation from `lauburu_dht_daemon.py`.
3. **View & Widget Rectification (`views/`, `widgets/`, `screens/`):**
   - `network_view.py`: Remove static Wi-Fi client rows asserting L2 has Wi-Fi 7 MLO 6GHz.
   - `hardware_noc_view.py`: Replace hardcoded GW row (`12% (0.4)`, `38°C NOM`) and synthetic readiness (`92.4`) / CNS (`2.1`) with authentic data or `"--"`.
   - `biometrics_view.py`: Reinstate clean disconnected waiting state (`[bold red]● DISCONNECTED[/bold red]`, `"--"`) when `ms.connected` is False.
   - `canonical_header_bar.py` & `live_speedtest_card.py`: Default reactive throughput fields to `"--"`; add `prima.cpp` to engine selector options.
   - `screens/hardware_screen.py`: Update Rule 3 threshold check to `>= 4.8GB`.

### Phase 2: Network Configurations & Hardware Guide Corrections
1. `06_scripts_and_tooling/network/mesh_ip_matrix.json`:
   - Set L2 TB4 bridge IP to `169.254.187.138`.
   - Set L5 Tailscale IP to `100.93.158.96`.
   - Mark TP-Link AX1800 as `RETIRED`.
2. `06_scripts_and_tooling/network/nomad_courier_self_healer.py`:
   - Set L5 RPC endpoint to `100.93.158.96:50052`.
   - Rename Port 8081 to `qwen25_coder_syntax_worker`.
3. `07_docs_and_architecture/08_hardware_guides/DELL_INSPIRON_3525_BATTERY_AND_CHARGING_GUIDE.md`:
   - Revert corrupted tokens `FlyGoat/Intel 2018 Mac MiniAdj` and `Intel 2018 Mac Mini (Linux)` back to `FlyGoat/RyzenAdj` and `AMD Ryzen 7 5700U`.

### Phase 3: Verification & Integrity Testing
- Run `python3 -m py_compile` across all modified Python modules in `01_apps/canonical_port/tui`.
- Execute headless Textual auto-pilot test to verify app initialization, reactive properties, and screen transitions across all 14 screens without runtime exceptions.
- Run existing unit test suite in `01_apps/canonical_port/tests/`.
- Compile final `handoff.md` with full execution proofs, byte counts, and SHA256 hashes.

---
*Report certified by `worker_tui_harden_1` under strict Zero-Mock and Canonical Hardware Matrix rules.*
