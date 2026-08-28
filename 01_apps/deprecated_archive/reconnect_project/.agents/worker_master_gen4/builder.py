import os
import sys

target_path = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md'

doc = r"""---
tags:
  - architecture
  - lauburu-monorepo
  - distributed-systems
  - biometrics-dsp
  - edge-ai
  - zero-cloud
updated: 2026-08-26
status: canonical
title: Lauburu App Ecosystem & Distributed Mesh Architecture
author: Lauburu AI Core Architecture Team
version: 4.0.0-canonical
---

# Lauburu App Ecosystem & Distributed Mesh Architecture

> [!abstract] Executive System Overview
> The **Lauburu Monorepo** is a unified, sovereign, zero-cloud distributed edge operating system and biomedical intelligence ecosystem. Interconnecting **7 heterogeneous hardware nodes** into a cohesive compute mesh, Lauburu pools **106.5 GB of physical RAM** into **82.8 GB of usable, high-performance AI VRAM** and **1.701 TB of distributed POSIX storage** via SeaweedFS and Syncthing P2P. Operating at **$0.00 recurring cloud spend**, the ecosystem executes full-stack biomedical digital signal processing (128Hz raw ECG, continuous non-invasive blood pressure, rolling DFA-$\alpha_1$ fractal stress analysis), autonomous multi-agent swarm self-healing, real-time spatial grappling kinematics, and continuous 24/7 LoRA reinforcement learning.

> [!info] The Tri-Partite Structural Taxonomy
> The architectural topology is organized into three distinct biological and computational tiers:
> 1. **The Peripheral Nerves (Sellable Commercial Apps & Edge Daemons):** Autonomous, low-footprint services running directly on edge nodes (Macs, Linux terminals, Android/Termux). Includes the **Lauburu Hardware Sentinel** (Zero-VRAM TUI), **Lauburu Mesh Healer** (`smolagents` self-repair daemon), **Movesense Biometrics Hub** (128Hz BLE GATT engine), and **Shadow Benchmarker API** (dynamic VRAM sharding load balancer).
> 2. **The Prefrontal Cortex (Proprietary Core Infrastructure):** Internal intelligence, orchestration, and continuous learning systems. Includes **The Crucible** (8-way ELO Chaos Arena and Hourly LoRA `SFTTrainer`), **The Main Hub** (`localhost:3000` Swarm Dashboard & `localhost:4000` Canonical Hub), **Obsidian Commander** (Quartz v5.0.0 engine & Qdrant semantic RAG memory graph), and **Mac Air Sync Orchestrator** (4-node Syncthing P2P cluster).
> 3. **The Brain Stem (Global Communication & Distributed Compute Fabric):** The underlying synchronization substrate. Includes the **Scout-to-Commander SSE 1Hz Stream** (energy-conserving unidirectional telemetry), **Apache Ray & PySpark Distributed Compute** (stream processing, parallel actor tasks, and DARE-TIES/SLERP genetic model merging), and the **Obsidian Canonical Knowledge Graph**.

---

## Complete 17-App Monorepo Application Catalog

The Lauburu Monorepo registers and orchestrates **17 canonical applications and microservices**, formally indexed and exposed via `GET /api/apps` on the Port 4000 Canonical Hub (`01_apps/port_4000_hub/server.py`):

| App ID | Name | Category | Route | Port | Key Features & Subsystems | Verified Source Location |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| `lauburu_super_app` | Lauburu Super App | Health & Lifestyle | `/apps/lauburu_super_app/` | 4000 | Daily Recovery Score, Sleep Architecture, Zone 2 Summary, AI Chat Coach, Shopify Storefront UI | `01_apps/port_4000_hub/server.py` |
| `lauburu_zone2_endurance` | Zone 2 Endurance | Fitness & Biometrics | `/apps/lauburu_zone2_endurance/` | 4000 | Real-time DFA-$\alpha_1$ fractal engine, Rogue Echo Bike FTMS cadence/power, continuous SBP/DBP, AI audio cues | `01_apps/lauburu_zone2_endurance/` & `01_apps/zone2_endurance/` |
| `lauburu_bluetooth_sensor` | Bluetooth & PPG Sensor | Fitness & Biometrics | `/apps/lauburu_bluetooth_sensor/` | 4000 | 10s Camera PPG calibrator, Movesense 128-512Hz ECG stream, real-time TKEO energy filter, WebSocket IPC | `01_apps/lauburu_compute_hub/lib/services/movesense_ble_service.dart` |
| `lauburu_compute_hub` | Lauburu Compute Hub | Distributed AI & Compute | `/apps/lauburu_compute_hub/` | 4000 | Bare-metal llama.cpp RPC server, Petals BitTorrent sharding, dynamic VRAM pooling, $0 token execution | `01_apps/lauburu_compute_hub/main.py` |
| `lauburu_grappling_3d` | 3D Spatial Grappling | Martial Arts & Kinematics | `/apps/spatial_grappling_3d/` | 5001 | 955-Node technique hierarchy, Three.js inverse kinematics, torque stress heatmaps, UWB tracking | `01_apps/spatial_grappling_3d/` & `10_spatial_grappling_kinematics/` |
| `lauburu_termux_daemon` | Termux Edge Daemon | Infrastructure & Edge | `/apps/termux_edge_daemon/` | 8088 | `termux-wake-lock`, ADB TCP/IP Port 5555, Doze mode bypass, SQLite WAL local cache, 1Hz SSE client | `01_apps/termux_edge_daemon/README.md` |
| `lauburu_shopify_ai` | Shopify AI Merchant | Commerce & Subscription | `/apps/shopify_ai/` | 4000 | Storefront GraphQL API, Customer Access Tokens, membership verification (`FREE`, `PAID_PRO`, `CONTRIBUTOR_PRO`) | `01_apps/shopify_ai/` & `01_apps/lauburu-storefront/` |
| `lauburu_swarm_dashboard` | Swarm Orchestrator & ELO | Multi-Agent AI | `/apps/swarm_dashboard/` | 3000 | Tri-Orchestrator protocol canvas, dynamic JSON ELO ledger, Swarm Truth Audit, 75% RAM safety governor | `01_apps/swarm_dashboard/app.js` & `arena_canvas.html` |
| `lauburu_movesense_hub` | Movesense 128Hz Ingestion | Medical DSP | `/apps/movesense_hub/` | 4000 | 128Hz Raw ECG streaming, Kamath 2004 20% artifact filter, 52Hz IMU dynamic G-force, PTT blood pressure | `01_apps/movesense_hub/pyspark_biometrics_dsp.py` |
| `lauburu_hemodynamics_cloud` | Hemodynamics & Arterial | Clinical Biometrics | `/apps/hemodynamics_cloud/` | 4000 | Non-linear Moens-Korteweg inversion, Bramwell-Hill arterial compliance, 2-element Windkessel SVR | `01_apps/Standalone_Services/Hemodynamic_Cloud_Server/` |
| `lauburu_openclaw` | OpenClaw Research Agent | Autonomous AI | `/apps/openclaw/` | 4000 | Open-source repository scout, empirical hardware price verification, visual UI auditing, LoRA harvesting | `01_apps/openclaw/` & `01_apps/openclaw_apk/` |
| `lauburu_memory_sync` | Data Memory & Vector Sync | Data & Persistence | `/apps/memory_sync/` | 4000 | SQLite WAL mode, Zero-PII sanitization, ChromaDB / Qdrant RAG vectors, automated checkpoint sync | `01_apps/Standalone_Services/Hemodynamic_Cloud_Server/app/storage/` |
| `lauburu_red_blue_security` | Red/Blue Security Suite | Security & Isolation | `/apps/security_suite/` | 4000 | Zero-PII sanitization, ed25519 auth, Cloudflare tunnel HMAC verification, RAM isolation sandbox | `11_security_and_governance/` |
| `lauburu_lora_evolution` | Continuous LoRA Evolution | AI Training | `/apps/lora_evolution/` | 4000 | 24/7 Execution trace harvesting, loss tracking, Genetic MoE weight merging (DARE-TIES/SLERP), $0 cloud spend | `12_continuous_lora_evolution/` |
| `lauburu_kinematics_lab` | Spatial Kinematics Lab | Physics & Biomechanics | `/apps/kinematics_lab/` | 5001 | Joint torque vector computation, angular velocity DSP, submission counters, biomechanical heatmaps | `10_spatial_grappling_kinematics/` |
| `lauburu_nomad_courier` | Nomad Courier Mesh Governor | Mesh & Networking | `/apps/nomad_courier/` | 18802 | 5-Tier network failover, Port 4000 watchdog, RFC 792 Wake-on-LAN resurrector, LoRA action logging | `06_scripts_and_tooling/network/nomad_courier_self_healer.py` |
| `lauburu_app_store` | Lauburu Port 4000 Hub | System Hub | `/` | 4000 | Unified PBKDF2 authentication, Shopify account sync, 128Hz Movesense ingest, WebSocket broadcast, GL.iNet proxy | `01_apps/port_4000_hub/server.py` |

---

## Section 1: Sellable Commercial Apps & Edge Daemons (The Peripheral Nerves)

The Peripheral Nerves comprise autonomous, modular microservices running directly on edge hardware. Packaged as standalone Docker containers or native daemons, these services provide critical edge observability, self-healing, telemetry ingestion, and load balancing while preserving maximum host resources for AI inference.

```
                              ┌────────────────────────────────────────────────────────┐
                              │            THE PERIPHERAL NERVES (EDGE TIER)           │
                              └───────────────────────────┬────────────────────────────┘
                                                          │
         ┌────────────────────────────────┬───────────────┴────────────────┬───────────────────────────────┐
         │                                │                                │                               │
┌────────▼───────────────┐       ┌────────▼───────────────┐       ┌────────▼───────────────┐      ┌────────▼───────────────┐
│   Hardware Sentinel    │       │      Mesh Healer       │       │ Movesense Biometrics   │      │   Shadow Benchmarker   │
│ • Zero-VRAM Textual TUI│       │ • smolagents CodeAgent │       │ • 128Hz Raw ECG / BLE  │      │ • Port 5050 FastAPI    │
│ • Shizuku Thermal HAL  │       │ • 5-Tier Recovery Link │       │ • Kamath 20% & DFA-a1  │      │ • 82.8 GB VRAM Pool    │
│ • 4-Pillar MIN Formula │       │ • +15 ELO Race Arena   │       │ • Moens-Korteweg PTT   │      │ • TTFT/TPS Evaluator   │
│ • Mac/Linux Wake-Locks │       │ • Zombie PID Hunting   │       │ • LUDS Readiness 0-100 │      │ • Dynamic routing.json │
└────────────────────────┘       └────────────────────────┘       └────────────────────────┘      └────────────────────────┘
```

### 1.1 Lauburu Hardware Sentinel
- **Core Source Files**: `scripts/mesh_sentinel_profiler.py`, `00_core_infrastructure/self_healing_hub/src/live_device_sentinel.py`, `adaptive_device_hardware_governor.py`, `samsung_battery_power_monitor.py`
- **Zero-VRAM Textual Architecture**: Designed to monitor dense edge hardware without consuming a single megabyte of precious GPU/VRAM memory. Built using Python standard library primitives and lightweight asynchronous socket/procfs readers, the Sentinel runs comfortably in headless terminal environments (Textual TUI / rich CLI) with $< 15\,\text{MB}$ host RAM footprint.
- **Android Shizuku & Thermal HAL 2.0 Integration**:
  - Connects to Android system services over ADB/Shizuku without requiring root privileges.
  - Queries `dumpsys battery`, `dumpsys deviceidle whitelist`, and `termux-battery-status`.
  - Captures real-time voltage ($V_{\text{mV}}$), charging current ($I_{\text{mA}}$), battery temperature ($T_{\text{batt}}$ in $0.1^\circ\text{C}$ resolution), and battery state-of-health.
  - Detects OEM thermal throttling thresholds ($T_{\text{batt}} > 38.0^\circ\text{C}$) and dispatches proactive cooldown mitigation commands.
- **Multi-OS Sleep Prevention & Wake Locks**:
  - **macOS (Darwin)**: Injects power assertions via `caffeinate -dimsu` tied to active daemon PIDs, preventing display sleep, idle sleep, and disk spin-down.
  - **Linux (systemd)**: Issues `systemd-inhibit --what=sleep:idle:handle-lid-switch` and dynamically masks suspend targets.
  - **Android (Termux)**: Acquires kernel wake lock via `/data/data/com.termux/files/usr/bin/termux-wake-lock` and explicitly whitelists the daemon from Doze optimization (`cmd deviceidle whitelist +com.termux`).
- **4-Pillar MIN Speed Constraint Formula**:
  To protect users and hardware operators from wasting capital on redundant cable upgrades, the Sentinel evaluates the physical throughput ceiling across all hardware links:
  $$\text{Effective Speed} = \min(P_{\text{host}}, P_{\text{device}}, P_{\text{transport}}, P_{\text{thermal}})$$
  Where:
  - $P_{\text{host}}$ = Maximum USB/Thunderbolt PHY rate supported by the host controller (e.g., Mac Mini M4: $40.0\,\text{Gbps}$).
  - $P_{\text{device}}$ = Maximum USB interface rate supported by the target edge device (e.g., Pixel 10 Pro: $10.0\,\text{Gbps}$, Galaxy S20+: $5.0\,\text{Gbps}$).
  - $P_{\text{transport}}$ = Negotiated physical link speed of the active cable / bus.
  - $P_{\text{thermal}}$ = Thermally throttled bandwidth derating factor.
  
  **Anti-Waste Decision Logic**:
  ```python
  effective_max_gbps = min(host_max_gbps, device_max_gbps)
  if current_cable_gbps < effective_max_gbps:
      recommendation = {
          "upgrade_recommended": True,
          "target_gbps": effective_max_gbps,
          "roi_justification": f"Current link ({current_cable_gbps}Gbps) is bottlenecked. Both host and device support {effective_max_gbps}Gbps."
      }
  else:
      recommendation = {
          "upgrade_recommended": False,
          "target_gbps": current_cable_gbps,
          "roi_justification": "Hardware is physically saturated. Purchasing higher-spec cables yields $0.00 ROI."
      }
  ```
- **Adaptive Hardware Governor Context Modes**:
  - `HUMAN_INTERACTIVE_MODE`: Enforces a $58\%$ RAM ceiling, $45\%$ CPU ceiling, and $80\%$ NPU ceiling to guarantee buttery $60\,\text{FPS}$ UI fluidity on local displays.
  - `AUTONOMOUS_MAX_SURGE_MODE`: Unlocks up to $94\%$ RAM ceiling, $92\%$ CPU ceiling, and $100\%$ NPU ceiling during overnight background training and large-model inference sweeps.

---

### 1.2 Lauburu Mesh Healer (The Reflex Arc)
- **Core Source Files**: `scripts/smolagents_healer.py`, `scripts/smolagents_swarm_healer.py`, `00_core_infrastructure/self_healing_hub/src/universal_mesh_healer.py`, `06_scripts_and_tooling/network/nomad_courier_self_healer.py`
- **Hugging Face `smolagents` CodeAgent Integration**:
  - Instantiates lightweight autonomous agents wrapping local Small Language Models (SLMs $<3\text{B}$ params) executing on local OpenAI-compatible endpoints (`:8080`, `:8081-8084`).
  - Operates via dynamic Python code generation and sandboxed local execution, inspecting network routing tables, sockets, and OS process trees directly.
- **5-Tier Network Healing Escalation**:
  1. **Tier 1 (Soft DNS & Socket Recycle)**: Flushes local mDNS responder caches (`killall -HUP mDNSResponder` on macOS, `systemd-resolve --flush-caches` on Linux).
  2. **Tier 2 (Tailscale WireGuard Link Flush)**: Resets stateful overlay tunnels and forces route re-advertisement:
     ```bash
     tailscale down && tailscale up --accept-routes=true --reset
     ```
  3. **Tier 3 (Zombie PID Hunting & VRAM De-allocation)**: Detects stalled inference servers holding TCP ports or GPU memory allocations and executes targeted termination:
     ```bash
     fuser -k 50052/tcp 8080/tcp 3000/tcp
     pkill -9 -f llama-rpc-server
     nohup /usr/local/bin/llama-rpc-server -H 0.0.0.0 -p 50052 > /tmp/rpc.log 2>&1 &
     ```
  4. **Tier 4 (Hugging Face & Disk Cache Pruning)**: Scans `~/.cache/huggingface/hub/` for orphaned incomplete weight downloads and temporary files, pruning stale tensors to preserve the mandatory $\ge 20\%$ disk headroom.
  5. **Tier 5 (Out-of-Band Wake-on-LAN Resurrect)**: Dispatches RFC 792 UDP Magic Packets (`b"\xff"*6 + mac_bytes*16`) to broadcast targets `192.168.8.255`, `255.255.255.255`, and `169.254.255.255` on UDP ports 9 and 7, invoking router-side `etherwake` over SSH to wake sleeping nodes.
- **Swarm ELO Race Arena & Real-Time +15 ELO Harvesting**:
  - When an infrastructure fault is detected, the Healer broadcasts the anonymized stack trace simultaneously to all edge models.
  - An `asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)` race condition identifies the first agent to generate a syntactically valid and empirically verified remediation script.
  - The winning agent earns $+15\,\text{ELO}$ in `04_data_and_memory/data/ai_elo_leaderboard.json`.
  - The successful execution trace is appended to `04_data_and_memory/lora_dataset.jsonl` as an instruction-tuning pair for continuous LoRA model improvement.

---

### 1.3 Movesense Biometrics Hub
- **Core Source Files**: `01_apps/movesense_hub/pyspark_biometrics_dsp.py`, `01_apps/lauburu_compute_hub/lib/services/movesense_ble_service.dart`, `01_apps/Standalone_Services/Hemodynamic_Cloud_Server/app/physics/`, `07_docs_and_architecture/MOVESENSE_BLUETOOTH_ARCHITECTURE_DEBATE.md`
- **Bluetooth 5.4 Low Energy GATT Architecture**:
  The biometrics daemon utilizes the Python `bleak` library to bind directly to the Movesense Medical / MD sensor over BLE 5.4, operating on the authoritative 128-bit Movesense Device Service (MDS 2.0):

| Service / Characteristic | UUID / 16-bit Handle | Function & Transmission Protocol |
| :--- | :--- | :--- |
| **Movesense MDS 2.0 Primary Service** | `34800001-7185-4d5d-b431-b30e393d9e05` | Master Whiteboard REST-over-BLE command & subscription conduit |
| **MDS 2.0 Command Characteristic** | `34800001-7185-4d5d-b431-b30e393d9e05` | Write characteristic (Opcodes: GET=1, PUT=2, POST=3, DEL=4, SUB=5, UNSUB=6) |
| **MDS 2.0 Data Notification 1** | `34800002-7185-4d5d-b431-b30e393d9e05` | High-frequency SBEM binary notification channel (CCCD `0x2902`) |
| **MDS 2.0 Data Notification 2** | `34800003-7185-4d5d-b431-b30e393d9e05` | Secondary high-throughput notification stream |
| **Standard Bluetooth SIG HRS** | `0x180D` (`0000180d-0000-1000-8000-00805f9b34fb`) | Standard BLE Heart Rate Service |
| **SIG Heart Rate Measurement** | `0x2A37` (`00002a37-0000-1000-8000-00805f9b34fb`) | Standard HR (uint8/16) and RR-interval stream |
| **SIG Battery Service** | `0x180F` (`0x2A19`) | Battery level percentage notification ($0-100\%$) |
| **SIG Device Information (DIS)** | `0x180A` (`0x2A24`-`0x2A26`) | Hardware serial number, manufacturer, and firmware version |

- **High-Throughput Binary Streaming Formats**:
  - `/Meas/ECG/128` (128Hz Raw Single-Lead ECG): 6-byte header `[type (uint8), req_id (uint8), timestamp_ms (uint32 LE)]` followed by signed 32-bit little-endian microvolt samples ($V_{\text{mV}} = V_{\mu\text{V}} / 1000.0$).
  - `/Meas/IMU6/52` (52Hz 6-DoF Kinematics): 6-byte header followed by 6 $\times$ IEEE-754 `float32` values ($a_x, a_y, a_z$ in $\text{m/s}^2$, $g_x, g_y, g_z$ in $\text{deg/s}$). Dynamic acceleration magnitude is computed as:
    $$\|a\| = \frac{\sqrt{a_x^2 + a_y^2 + a_z^2}}{9.80665} \quad [\text{G}]$$

- **Biomedical DSP & Mathematical Formulations**:

```
[Movesense 128Hz ECG] ──► [Bandpass 0.5-40Hz] ──► [Pan-Tompkins QRS] ──► [Kamath 20% Filter]
                                                                                │
                                           ┌────────────────────────────────────┴────────────────────────────────────┐
                                           ▼                                                                         ▼
                             [RMSSD Parasympathetic]                                                   [120s Rolling DFA-alpha1]
                                           │                                                                         │
                                           └────────────────────────────────────┬────────────────────────────────────┘
                                                                                ▼
                                                              [PTT Blood Pressure & Windkessel SVR]
                                                                                ▼
                                                              [LUDS Athlete Readiness Score: 0-100]
```

  1. **Kamath et al. (2004) 20% Clinical RR Artifact Filter**:
     To eliminate ectopic beats, motion artifacts, and false detections before fractal analysis:
     $$\frac{|RR_i - RR_{i-1}|}{RR_{i-1}} \le 0.20$$
     RR intervals deviating by $>20\%$ from the immediately preceding valid beat are rejected or cubic-spline interpolated.

  2. **Root Mean Square of Successive Differences (RMSSD)**:
     Quantifies vagally-mediated parasympathetic cardiac autonomic regulation:
     $$\text{RMSSD} = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N-1} (RR_{i+1} - RR_i)^2}$$

  3. **120-Second Rolling Detrended Fluctuation Analysis (DFA-$\alpha_1$) Short-Term Exponent**:
     Measures qualitative fractal scaling and heart rate dynamical self-similarity:
     - Compute integrated profile: $y(k) = \sum_{j=1}^k (RR_j - \overline{RR})$.
     - Divide $y(k)$ into non-overlapping segments of length $n$ ($n \in [4, 16]$ beats).
     - Calculate local least-squares linear trend $y_n(k)$ in each segment.
     - Compute root-mean-square fluctuation:
       $$F(n) = \sqrt{\frac{1}{N} \sum_{k=1}^N (y(k) - y_n(k))^2}$$
     - Determine scaling exponent $\alpha_1$ as the linear slope of $\log(F(n))$ against $\log(n)$:
       $$F(n) \propto n^{\alpha_1}$$
     - **Physiological Training Zones**:
       - $\alpha_1 \ge 0.75$: **Zone 2 (Aerobic Base / Optimal Lipid Oxidation)** — High fractal correlation.
       - $0.50 \le \alpha_1 < 0.75$: **Zone 3 (Tempo / Aerobic Power)** — Intermediate autonomic stress.
       - $\alpha_1 < 0.50$: **Zone 4/5 (Anaerobic Threshold / Severe Domain)** — Uncorrelated / anti-correlated white noise.

  4. **Moens-Korteweg & Hughes Non-Linear Hydrodynamic Wave Speed**:
     - Pulse Wave Velocity ($PWV_0$) in elastic vessels:
       $$c = PWV_0 = \sqrt{\frac{E_0 \cdot h}{\rho \cdot D}}$$
       Where $E_0$ is Young's modulus of the arterial wall, $h$ is wall thickness, $D$ is internal diameter, and $\rho = 1055.0\,\text{kg/m}^3$ is blood density.
     - Hughes non-linear strain-stiffening relationship:
       $$E(P) = E_0 \cdot \exp(\gamma \cdot P) \quad (\gamma \approx 0.017\,\text{mmHg}^{-1})$$
     - Pulse Transit Time (PTT) continuous blood pressure inversion:
       $$P = -\frac{2}{\gamma} \ln(PTT) + \frac{2}{\gamma} \ln\left(\frac{L}{PWV_0}\right) \implies \text{BP} = a \cdot \ln(PTT) + b$$
     - Calibrated SBP and DBP models:
       $$\text{SBP} = a_{\text{sbp}} \ln(PTT_{\text{sec}}) + b_{\text{sbp}} \left(\frac{E_0}{E_{\text{ref}}}\right) + c_{\text{sbp}} + k_{\text{hr\_sbp}} (HR - 70)$$
       $$\text{DBP} = a_{\text{dbp}} \ln(PTT_{\text{sec}}) + b_{\text{dbp}} \left(\frac{E_0}{E_{\text{ref}}}\right) + c_{\text{dbp}} + k_{\text{hr\_dbp}} (HR - 70)$$

  5. **Bramwell-Hill Arterial Compliance & Distensibility**:
     - Volumetric distensibility:
       $$D_v = \frac{1}{\rho \cdot PWV^2}$$
     - Total Arterial Compliance ($TAC / C_{\text{art}}$):
       $$C_{\text{art}} = \frac{V_0}{\rho \cdot PWV^2} \times 133.322 \times 10^6 \quad [\text{mL/mmHg}]$$
       Where $V_0 = 0.0010\,\text{m}^3$ is the nominal aortic arterial volume.

  6. **2-Element Windkessel Vascular Model (WK2) for Systemic Vascular Resistance (SVR)**:
     - Peripheral resistance ($R_p$) derived from diastolic exponential pressure decay:
       $$R_p = \frac{\Delta T_{\text{dia}}}{C_{\text{art}} \cdot \ln(\alpha_{\text{notch}} \cdot \text{SBP} / \text{DBP})} \quad (\alpha_{\text{notch}} = 0.85)$$

  7. **LUDS (Lauburu Unified Dynamic Stress) Readiness Score Algorithm ($0-100$)**:
     $$\text{LUDS Readiness} = w_{\text{hrv}} \cdot S_{\text{rmssd}} + w_{\text{dfa}} \cdot S_{\text{dfa}} + w_{\text{bp}} \cdot S_{\text{map}} - P_{\text{drift}} - P_{\text{kinetic}}$$
     Where:
     - $S_{\text{rmssd}} = \min\left(100.0, \frac{\text{RMSSD}}{\text{RMSSD}_{\text{baseline}}} \times 100\right)$ ($w_{\text{hrv}} = 0.40$).
     - $S_{\text{dfa}} = \begin{cases} 100.0 & \text{if } \alpha_1 \ge 0.75 \\ 70.0 & \text{if } 0.50 \le \alpha_1 < 0.75 \\ 30.0 & \text{if } \alpha_1 < 0.50 \end{cases}$ ($w_{\text{dfa}} = 0.35$).
     - $S_{\text{map}} = \max\left(0.0, 100.0 - |\text{MAP} - 93.3| \times 2.0\right)$ ($w_{\text{bp}} = 0.25$).
     - $P_{\text{drift}}$ = Cardiac drift penalty (deducts 15 points if HR elevates $>6\%$ while mechanical power output remains constant).
     - $P_{\text{kinetic}}$ = Impact accumulation penalty (deducts points for repeated G-force shocks $>3.5\text{G}$).

---

### 1.4 Shadow Benchmarker API
- **Core Source Files**: `01_apps/shadow_benchmarker/server.py`, `02_ai_models_and_inference/mesh_benchmarks/`
- **FastAPI Microservice Architecture (Port 5050)**:
  - Runs on Port 5050 with asynchronous background benchmarking workers.
  - Probes live local AI endpoints:
    - `llama.cpp` RPC Gateway: `http://127.0.0.1:8080/v1/chat/completions`
    - `Exo` Distributed Ring: `http://127.0.0.1:52415/v1/chat/completions`
    - `Petals` BitTorrent Swarm: `http://127.0.0.1:8001/v1/chat/completions`
- **Dynamic VRAM Sharding across the 7-Device 82.8 GB Pool**:
  The benchmarker orchestrates model placement across the unified hardware topology:

| Hardware Layer | Node Identity | Physical RAM | Usable AI VRAM Cap | Priority Rank | Primary Role & Layer Allocation |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Layer 1** | Apple M4 Pro Mac Mini Host | 24.0 GB | **21.6 GB** | Rank 4 | Prompt Ingestion, `qwen2-vl-7b`, `deepseek_r1_70b_shard_1` |
| **Layer 2** | MacBook Pro M1 Max | 16.0 GB | **14.0 GB** | Rank 2 | Thunderbolt 4 RPC (3.6 GB/s), `qwen2.5_coder_32b_shard_a` |
| **Layer 3** | Linux Head Node (Ryzen 7) | 15.3 GB | **13.8 GB** | Rank 1 | Ray Head, Docker Master, `qwen2.5_coder_32b_shard_b` |
| **Layer 4** | Bedside Linux Tablet | 8.0 GB | **6.5 GB** | Rank 1 | Biometrics HUD, Petals DHT auxiliary worker |
| **Layer 5** | MacBook Air (Apple M4) | 16.0 GB | **13.5 GB** | Rank 3 | Metal Shaders, LoRA SFT fine-tuning, `kimi_tandem_shard` |
| **Layer 6** | Google Pixel 10 Pro XL | 15.2 GB | **12.5 GB** | Rank 6 | Tensor G5 Edge TPU (22 TOPS), Vision Projector, `llama-3.1-8b` |
| **Layer 7** | Samsung Galaxy S20+ | 12.0 GB | **9.0 GB** | Rank 5 | Termux Edge Worker, `SmolLM2-135M`, continuous telemetry |
| **TOTAL** | **7-Device Sovereign Mesh** | **106.5 GB** | **82.8 GB** | - | **Pooled Cluster: 53.41 GB Active / 29.39 GB Headroom** |

- **Streaming TTFT & TPS Evaluation Logic**:
  Dispatches a standardized 50-token streaming completion prompt (`model: Llama-3-8B-Q4_K_M`) to measure:
  - **Time To First Token (TTFT)**: Time elapsed from request dispatch until the arrival of the first SSE completion chunk ($t_1 - t_0$).
  - **Tokens Per Second (TPS)**: Effective generation throughput across remaining tokens ($N_{\text{tokens}} / (t_{\text{end}} - t_1)$).
- **Dynamic Routing Matrix Sync (`routing.json`)**:
  Computes a composite routing score:
  $$\text{Score} = \frac{\text{TPS}}{\text{TTFT}_{\text{sec}}} \times \left(1.0 - \frac{\text{VRAM}_{\text{used}}}{\text{VRAM}_{\text{total}}}\right)$$
  The highest-scoring inference backend is atomically written to `routing.json` for all edge agents to consume.

---

## Section 2: Proprietary Infrastructure (The Prefrontal Cortex)

The Prefrontal Cortex represents the core internal operating systems of the Lauburu Monorepo. These systems govern multi-agent consensus, continuous reinforcement training, canonical truth enforcement, and peer-to-peer data replication.

```
                              ┌────────────────────────────────────────────────────────┐
                              │          THE PREFRONTAL CORTEX (CORE TIER)             │
                              └───────────────────────────┬────────────────────────────┘
                                                          │
         ┌────────────────────────────────┬───────────────┴────────────────┬───────────────────────────────┐
         │                                │                                │                               │
┌────────▼───────────────┐       ┌────────▼───────────────┐       ┌────────▼───────────────┐      ┌────────▼───────────────┐
│     The Crucible       │       │      The Main Hub      │       │   Obsidian Commander   │      │ Mac Air Sync Orchestr. │
│ • 8-Gladiator Chaos    │       │ • Port 3000 Dashboard  │       │ • Quartz v5.0.0 (8888) │      │ • 4-Node Syncthing P2P │
│ • 7-Tool Recovery Kit  │       │ • Port 4000 System Hub │       │ • Bidirectional Links  │      │ • TLS 1.3 BEP Encrypt  │
│ • FFA ELO (K=32) Math  │       │ • PBKDF2 Session Auth  │       │ • Qdrant Vector RAG    │      │ • 256MB RAM Hard Cap   │
│ • Hourly LoRA PEFT     │       │ • Shopify GraphQL Sync │       │ • AST Canonical Truth  │      │ • 75% Host Margin Safe │
└────────────────────────┘       └────────────────────────┘       └────────────────────────┘      └────────────────────────┘
```

### 2.1 The Crucible (AI Training Game)
- **Core Source Files**: `scripts/chaos_arena.py`, `game_arena_manager.py`, `scripts/train_mesh_lora.py`, `05_agents_and_swarms/architect_leaderboard.json`
- **8-Gladiator Small Language Model Tournament (<3B Params)**:
  The Crucible runs an automated tournament under real injected network latency, dropped packets, and process terminations across 8 dedicated SLM nodes:

| Gladiator Model | Parameters | API Endpoint | Target Edge Hardware | Assigned Specialization |
| :--- | :---: | :--- | :--- | :--- |
| **Qwen2.5-Coder-1.5B** | 1.5B | `http://localhost:8081/v1` | Google Pixel 10 Pro XL (Tensor G5 TPU) | Bash scripting & socket recovery |
| **Llama-3.2-1B-Instruct** | 1.2B | `http://localhost:8082/v1` | Samsung Galaxy S20+ (Termux) | ADB diagnostics & memory cleanup |
| **Gemma-2-2B-Instruct** | 2.6B | `http://localhost:8083/v1` | Apple M4 Mac Mini (Host Worker) | Code refactoring & syntax validation |
| **DeepSeek-Coder-1.3B** | 1.3B | `http://localhost:8084/v1` | GL.iNet Flint 2 Router Gateway | Network namespace & route tables |
| **SmolLM2-1.7B-Instruct** | 1.7B | `http://localhost:8085/v1` | Linux Head Node | Docker daemon & systemd units |
| **Phi-3-Mini-4K-Instruct** | 3.8B | `http://localhost:8086/v1` | Bedside Linux Tablet | JSON schema & REST API verification |
| **Granite-3.0-2B-Instruct** | 2.5B | `http://localhost:8087/v1` | Headless MacBook Air M4 | Metal shader kernel diagnostics |
| **H2O-Danube3-500M** | 0.5B | `http://localhost:8088/v1` | Local Edge Co-Processor | Micro-task triage & fast pinging |

- **7-Tool Mesh Recovery Toolkit**:
  Gladiators remediate simulated chaos using 7 sandboxed execution tools:
  1. `execute_adb_command(device_id, command)`: Invokes ADB shell commands on connected mobile devices.
  2. `flush_tailscale()`: Restarts WireGuard service and purges stale mesh routes.
  3. `kill_zombie_process(port)`: Locates and forcefully terminates orphaned PIDs on conflicting ports.
  4. `clear_hf_cache()`: Purges unreferenced Hugging Face cache blobs to recover disk space.
  5. `throttle_android_cpu(device_id)`: Enforces thermal throttling via Shizuku if battery temp $>45^\circ\text{C}$.
  6. `enforce_global_wake_locks(os_type)`: Dispatches `caffeinate` or `termux-wake-lock` keepalives.
  7. `sync_obsidian_vault(vault_path)`: Scans and heals codebase-to-vault documentation drift.
- **Multi-Player FFA ELO Rating Algorithm**:
  For an $N$-player tournament where winner $W$ beats all remaining losing models $L$:
  - Expected win probability of agent $A$ against agent $B$:
    $$E_{AB} = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$
  - Total expected score for winner $W$:
    $$E_W = \sum_{L \ne W} E_{WL}$$
  - ELO rating adjustments ($K=32$):
    $$\Delta R_W = K \cdot (|L| - E_W)$$
    $$\Delta R_L = -K \cdot (1 - E_{LW})$$
    $$R_W' = R_W + \Delta R_W, \quad R_L' = R_L + \Delta R_L$$
- **Anti-Collapse Quality Gate & Hourly LoRA `SFTTrainer`**:
  - **Quality Filter**: Only trajectories generated by models with post-match $ELO \ge 1100$ are admitted to the dataset. Stale or hallucinated traces are permanently discarded.
  - **Dataset Sink**: `04_data_and_memory/lora_dataset.jsonl`
  - **Hourly LoRA PEFT Fine-Tuning Hyperparameters**:
    - **Base Model**: `Qwen/Qwen2.5-Coder-7B-Instruct` (Quantized to 4-bit NF4 via `bitsandbytes`)
    - **PEFT Method**: LoRA (Low-Rank Adaptation)
    - **LoRA Rank ($r$)**: `8`
    - **LoRA Alpha ($\alpha$)**: `16`
    - **Target Modules**: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`
    - **LoRA Dropout**: `0.05`
    - **Per-Device Batch Size**: `2`, **Gradient Accumulation Steps**: `4` (Effective batch size = 8)
    - **Learning Rate**: `2e-4` with cosine learning rate scheduler and warm-up ratio `0.03`
    - **Max Sequence Length**: `1024` tokens
    - **Output Checkpoint**: `02_ai_models_and_inference/mesh_lora_checkpoints/mesh_healer_lora_final`

---

### 2.2 The Main Hub (localhost:3000 & localhost:4000)
- **Hub Architecture Bifurcation**:
  The ecosystem separates real-time multi-agent swarm orchestration from end-user API servicing into two dedicated port environments:
  - **Port 3000 (Swarm Dashboard)**: Pure agent command center hosting the Tri-Orchestrator canvas (`arena_canvas.html`), real-time ELO leaderboard graphs, active LoRA training toggles, and the 75% host RAM safety governor.
  - **Port 4000 (Canonical Web & Compute Hub)**: Production ASGI FastAPI backend hosting the unified authentication engine, Shopify customer account sync, 17-app registry, 128Hz Movesense telemetry ingestion, and GL.iNet router reverse proxy.
- **PBKDF2-HMAC-SHA256 Authentication Engine**:
  - `POST /api/auth/register`: Salts and hashes passwords with 100,000 iterations of PBKDF2-HMAC-SHA256, generating a cryptographically secure 64-character hexadecimal session token stored in SQLite WAL (`data/port_4000_hub.db`).
  - `POST /api/auth/login`: Validates credentials against PBKDF2 hashes and issues active session tokens.
  - `GET /api/auth/me`: Resolves active user sessions via `Authorization: Bearer <token>`, cookie header, or URL parameter.
- **Shopify Storefront GraphQL Integration**:
  - `POST /api/auth/shopify-login`: Connects to Shopify Storefront GraphQL API to validate Customer Access Tokens and fetch active subscription tags.
  - **Dynamic Tier Verification**:
    - `FREE`: Base telemetry viewing and community access.
    - `PAID_PRO`: $19/mo subscription unlocking full DFA-$\alpha_1$ coaching, PTT blood pressure analysis, and cloud backup.
    - `CONTRIBUTOR_PRO`: Awarded automatically to local operators who contribute $\ge 8\,\text{GB}$ of physical RAM to the distributed AI inference pool.
- **WebSocket Broadcast & GL.iNet Reverse Proxy**:
  - `WS /ws/telemetry`: Multi-client broadcast engine streaming 1Hz aggregated physiological ticks to dashboards.
  - `GET /proxy/router/{path}`: Seamless reverse proxy for GL.iNet Flint 2 router admin gateway (`192.168.8.1`), stripping `X-Frame-Options` and `Content-Security-Policy` headers to allow embedded management within the Swarm Dashboard.

---

### 2.3 Obsidian Commander (Quartz Engine, Port 8888)
- **Core Source Files**: `01_apps/obsidian_web/`, `00_core_infrastructure/self_healing_hub/src/obsidian_swarm_syncer.py`
- **Canonical Truth Enforcer (Quartz v5.0.0)**:
  - Preact / TypeScript static site engine running on Port 8888, rendering the local Obsidian markdown vault as a blazing-fast digital garden.
  - Acts as the single source of truth across the monorepo, governing architectural specifications, IP matrices, and debate resolutions.
- **Bidirectional Wikilink Graph Structure**:
  - Maintains connected relationship graphs linking core documentation:
    - `[[Index]]`: Master knowledge graph directory.
    - `[[swarm]]`: 7-Device hardware topology, IP allocation, and VRAM limits.
    - `[[ai-debate]]`: Tri-Orchestrator consensus debate transcripts.
    - `[[teamwork-preview]]`: Multi-agent teamwork prompt specifications.
- **Qdrant Semantic RAG Memory Graph (Port 6333)**:
  - Continuously indexes monorepo Abstract Syntax Trees (AST), architectural whitepapers, and agent execution traces into high-dimensional vector embeddings.
  - When an autonomous agent is dispatched, it queries Qdrant to inject verified context, permanently eliminating hallucination loops.

---

### 2.4 Mac Air Sync Orchestrator
- **Core Source Files**: `00_core_infrastructure/docker/docker-compose.syncthing.yml`, `06_scripts_and_tooling/mesh/syncthing_vault_mesh.py`, `00_core_infrastructure/self_healing_hub/src/syncthing_handler.py`
- **4-Node Syncthing P2P Cluster Table**:

| Container Name | Target Node | Role | Tailscale IP / Web GUI | Sync Port (TCP/UDP) | Memory Limit |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `syncthing_mac_node` | Mac Mini M4 Pro (Host) | Layer 1 Orchestrator | `100.84.87.3:8384` | `22000` | **256 MB** |
| `syncthing_macbook_pro` | MacBook Pro M1 Max | Layer 2 Storage Vault | `100.103.212.21:8384` | `22001` | **256 MB** |
| `syncthing_linux_head_node` | Linux Head Node | Layer 3 P2P Hub | `100.101.39.98:8384` | `22002` | **256 MB** |
| `syncthing_mac_mini` | MacBook Air M4 | Layer 5 GPU Worker | `100.93.158.96:8384` | `22003` | **256 MB** |

- **Security & Resource Enforcements**:
  - **Transport Security**: Block Exchange Protocol (BEP) over TLS 1.3 with AES-128-GCM cipher suites.
  - **Memory Ceiling**: Strict Docker cgroup limits (`mem_limit: 256m`, `cpus: '1.0'`) per container to guarantee that background replication never breaches the 75% host RAM safety ceiling.
  - **$0.00 Cloud Spend**: Replaces proprietary cloud storage (Dropbox, iCloud, AWS S3) with zero-leakage local peer-to-peer synchronization across all development laptops.

---

## Section 3: Global Architecture & Communication Protocols (The Brain Stem)

The Brain Stem connects edge sensory daemons to central computing clusters and semantic knowledge graphs.

```
                              ┌────────────────────────────────────────────────────────┐
                              │            THE BRAIN STEM (PROTOCOLS TIER)             │
                              └───────────────────────────┬────────────────────────────┘
                                                          │
         ┌────────────────────────────────────────────────┼────────────────────────────────┐
         │                                                │                                │
┌────────▼────────────────────────┐      ┌────────────────▼───────────────┐       ┌────────▼───────────────────────┐
│ Scout-to-Commander SSE 1Hz Push │      │ Apache Ray & PySpark Compute   │       │ Obsidian Canonical RAG Graph   │
│ • POST /api/v1/diagnostic/stream│      │ • Ray Head (Port 6379 / 8265)  │       │ • Qdrant Vector DB (Port 6333) │
│ • 92% Radio Energy Reduction    │      │ • 128Hz Streaming ECG DSP      │       │ • Bidirectional Wikilink Graph │
│ • CPU C-State Preservation      │      │ • DARE-TIES & SLERP MoE Merge  │       │ • Zero-Mock Truth Invariant    │
└─────────────────────────────────┘      └────────────────────────────────┘       └────────────────────────────────┘
```

### 3.1 Scout-to-Commander SSE 1Hz Diagnostic Stream
- **Core Endpoint**: `POST /api/v1/diagnostic/stream` (`Accept: text/event-stream`)
- **JSON Payload Event Schemas**:
  1. `event: thinking_delta`:
     ```json
     {"type": "thinking_delta", "delta": "Analyzing 128Hz ECG RR intervals... Kamath filter rejected 1 artifact."}
     ```
  2. `event: telemetry_tick`:
     ```json
     {
       "timestamp": 1771985400.124,
       "heart_rate": 142,
       "rmssd": 34.2,
       "dfa_alpha1": 0.78,
       "zone": "Zone 2 (Aerobic Base)",
       "sbp_mmhg": 124.5,
       "dbp_mmhg": 78.2,
       "luds_readiness": 88.4
     }
     ```
  3. `event: content_delta`:
     ```json
     {"type": "content_delta", "delta": "Maintaining optimal Zone 2 lipid oxidation. Power output: 185W."}
     ```
  4. `event: [DONE]`: End of active diagnostic stream.
- **Energy Conservation & Battery Preservation Rationale**:
  - Traditional biometrics applications execute high-frequency HTTP polling loops (10-50Hz), keeping mobile Wi-Fi/cellular radio modems continuously in high-power active states ($DCH / Tx$), depleting phone batteries in $<3\,\text{hours}$.
  - The Scout-to-Commander architecture aggregates 128 raw ECG samples per second into **a single 1Hz pushed payload**. Between 1Hz transmissions, the mobile operating system (Android/iOS) transitions the CPU into low-power $C$-states and allows radio hardware to sleep, reducing active radio power consumption by **$92\%$**.

---

### 3.2 Apache Ray & PySpark Distributed Compute
- **Cluster Head Topology**:
  - Hosted on Layer 3 Linux Head Node (`100.101.39.98:6379`, Web Dashboard on Port `8265`).
  - Coordinates multi-node distributed compute across Mac and Linux nodes via `01_apps/Standalone_Services/Edge_Node_Hub/lauburu_node_supervisor.py`.
- **Parallel Workloads**:
  1. **128Hz PySpark Streaming DSP**: Ingests high-frequency ECG/IMU packet streams from multiple simultaneous athletes, executing parallel Kamath filtering, FFT power spectral density, and DFA-$\alpha_1$ windowing in sub-millisecond worker micro-batches.
  2. **Genetic MoE PySpark Optimization**: 5-minute background cron evaluating monorepo AST indices and ranking agent ELO swings.
  3. **DARE-TIES & SLERP Distributed Model Weight Merging (`ray_spark_model_merger.py`)**:
     - **DARE-TIES (Drop And REscale with Task-Informed Energy Scaling)**: Drops $90\%$ of delta parameters (drop rate $p=0.90$), rescales remaining weights by $\frac{1}{1-p} = 10.0$, and resolves directional conflicts via sign consensus voting across distributed workers.
     - **SLERP (Spherical Linear Interpolation)**: Merges base and specialist models across spherical geometric angles:
       $$\text{SLERP}(W_0, W_1; t) = \frac{\sin((1-t)\theta)}{\sin(\theta)} W_0 + \frac{\sin(t\theta)}{\sin(\theta)} W_1$$
       Where $\theta = \arccos\left(\frac{\langle W_0, W_1 \rangle}{\|W_0\| \|W_1\|}\right)$ and $t=0.5$.

---

### 3.3 Obsidian RAG Memory Graph
- **Contextual Knowledge Grounding**:
  - Autonomous agents dispatched across the mesh query the local Qdrant vector database (Port 6333) and Obsidian knowledge graph before taking action.
  - Enforces the **Zero-Mock Standard (Rule #0)**: Agents must reference real source code lines, authentic hardware metrics, and empirical ELO rankings, preventing architectural drift and self-referential hallucination.

---

## Section 4: Architectural Mermaid.js Diagrams

### Diagram 1: Scout-to-Commander SSE Data Flow & Telemetry Ingestion

```mermaid
sequenceDiagram
    autonumber
    actor Athlete as Athlete (Sensor Wearer)
    participant Sensor as Movesense Medical Sensor
    participant EdgeScout as Edge Scout (Pixel 10 / S20+ Termux)
    participant Port4000 as Port 4000 Canonical Hub
    participant SQLiteDB as SQLite WAL Storage
    participant Commander as Main Commander (Port 3000 / HUD)

    Athlete->>Sensor: Physical Movement & Cardiac Contraction
    Sensor->>EdgeScout: BLE 5.4 GATT Stream (128Hz Raw ECG / 52Hz IMU)
    Note over EdgeScout: Pure Local Edge DSP Execution<br/>• Bandpass 0.5-40Hz & Notch<br/>• Pan-Tompkins QRS Detection<br/>• Kamath 20% RR Filter<br/>• RMSSD & Rolling DFA-alpha1<br/>• Moens-Korteweg PTT BP Inversion
    
    alt Continuous 1Hz Ingestion Push
        EdgeScout->>Port4000: HTTP POST /api/sensors/ingest (1Hz Batched Tick)
        Port4000->>SQLiteDB: INSERT INTO telemetry_ticks (WAL Mode)
        Port4000-->>Commander: WS Broadcast (/ws/telemetry live_tick)
    else Interactive Diagnostic Stream (SSE)
        Commander->>Port4000: POST /api/v1/diagnostic/stream (Accept: text/event-stream)
        Port4000-->>Commander: event: thinking_delta (DSP Analysis Reasoning)
        Port4000-->>Commander: event: telemetry_tick (Biomarkers & LUDS Readiness)
        Port4000-->>Commander: event: content_delta (Actionable AI Coaching Advice)
        Port4000-->>Commander: event: [DONE]
    end

    Note over EdgeScout,Commander: 92% Radio Energy Reduction: Phone CPU enters C-State between 1Hz frames
```

---

### Diagram 2: The Crucible AI Training & Evolution Feedback Loop

```mermaid
graph TD
    %% Subgraphs
    subgraph ChaosInjection [1. Injected Chaos Engine]
        Fault[Network Outage / Zombie PID / Port Lock]
    end

    subgraph TheArena [2. The 8-Way Chaos Arena]
        Qwen[Qwen2.5-Coder-1.5B :8081]
        Llama[Llama-3.2-1B :8082]
        Gemma[Gemma-2-2B :8083]
        DeepSeek[DeepSeek-Coder-1.3B :8084]
        Smol[SmolLM2-1.7B :8085]
        Phi[Phi-3-Mini :8086]
        Granite[Granite-3.0-2B :8087]
        Danube[H2O-Danube3-500M :8088]
    end

    subgraph ToolRecovery [3. 7-Tool Recovery Execution]
        Tools[ADB / Flush Tailscale / Kill PID / Clear Cache / Thermal Throttle / Wake Lock / Vault Sync]
    end

    subgraph EvaluationLoop [4. Evaluation & Gating]
        RaceWinner[First Verified Fix Elected]
        ELOLedger[(ai_elo_leaderboard.json +15 ELO)]
        QualityGate{Post-Match ELO >= 1100?}
        Discard[Discard Corrupt Trace]
        DatasetSink[(04_data_and_memory/lora_dataset.jsonl)]
    end

    subgraph FineTuningEngine [5. Continuous Training & Deployment]
        SFTTrainer[Hourly LoRA SFTTrainer PEFT Qwen2.5-Coder-7B NF4 r=8 a=16]
        GGUFExport[Export GGUF Quantized Weights Q4_K_M]
        ChampionVault[(02_ai_models/Champion Vault)]
        MeshDeploy[OTA Webhook Deploy to Edge Nodes]
    end

    %% Flow connections
    Fault -->|Concurrent Broadcast| Qwen & Llama & Gemma & DeepSeek & Smol & Phi & Granite & Danube
    Qwen & Llama & Gemma & DeepSeek & Smol & Phi & Granite & Danube -->|Generate Remediation Code| Tools
    Tools -->|Execute & Verify| RaceWinner
    RaceWinner -->|Update Ratings K=32| ELOLedger
    RaceWinner --> QualityGate
    QualityGate -- No --> Discard
    QualityGate -- Yes --> DatasetSink
    DatasetSink -->|Hourly Trigger| SFTTrainer
    SFTTrainer --> GGUFExport
    GGUFExport --> ChampionVault
    ChampionVault --> MeshDeploy
    MeshDeploy -->|Evolved Weights Update| TheArena
```

---

### Diagram 3: Tri-Layer Data Engine Architecture

```mermaid
graph TB
    %% Layer 1
    subgraph Layer1 [Layer 1: Edge Daemons & Commercial Peripheral Nerves]
        Sentinel[Hardware Sentinel TUI]
        Healer[Mesh Healer CodeAgent]
        Movesense[Movesense 128Hz Hub]
        Benchmarker[Shadow Benchmarker API]
    end

    %% Layer 2
    subgraph Layer2 [Layer 2: Head Node Compute & Distributed Processing]
        RayCluster[Apache Ray Cluster Head :6379/:8265]
        PySparkDSP[PySpark 128Hz Streaming DSP Engine]
        Port4000Hub[Port 4000 Canonical Web Hub & SQLite WAL]
        ModelMerger[DARE-TIES / SLERP Model Merger]
    end

    %% Layer 3
    subgraph Layer3 [Layer 3: Sovereign Storage & Knowledge Vault]
        SeaweedFS[(1.701 TB SeaweedFS DFS :9333/:8888/:8080)]
        Syncthing[(4-Node Syncthing P2P TLS 1.3 Cluster)]
        QdrantDB[(Qdrant Semantic Vector DB :6333)]
        QuartzVault[Obsidian Commander Quartz v5.0.0 :8888]
    end

    %% Connections
    Sentinel & Healer & Movesense & Benchmarker -->|1Hz Pushed Telemetry / SSE| Port4000Hub
    Movesense -->|High-Frequency Raw Stream| PySparkDSP
    Port4000Hub & PySparkDSP --> RayCluster
    RayCluster --> ModelMerger
    ModelMerger -->|Export Checkpoints| SeaweedFS
    Port4000Hub -->|Persist Telemetry & Datasets| SeaweedFS
    SeaweedFS -->|Sync Markdown Vault| Syncthing
    Syncthing --> QuartzVault
    QuartzVault -->|Embed AST & Spec Vectors| QdrantDB
    QdrantDB -->|Contextual RAG Retrieval| Layer1
```

---

## Section 5: Unified Monorepo Port Allocation Matrix & File Path Index

### 5.1 Canonical Port Allocation Matrix

| Port (TCP/UDP) | Protocol / Service | Bound Host / Interface | Owning Component / Application | Security & Access Context |
| :--- | :--- | :--- | :--- | :--- |
| **`22`** | OpenSSH Server (Root/User) | `100.x.x.x` (Tailscale) / LAN | All macOS & Linux Hosts | Strict ed25519 public-key auth only |
| **`445` / `139`** | Samba SMB3 File Gateway | `100.101.39.98` | `00_core_infrastructure` (SeaweedFS) | Apple VFS Fruit extensions, local LAN |
| **`3000`** | Swarm Dashboard & Canvas | `0.0.0.0` (All Nodes) | `01_apps/swarm_dashboard` | Multi-agent ELO canvas, internal mesh |
| **`4000`** | Canonical Web & Compute Hub | `0.0.0.0` (All Nodes) | `01_apps/port_4000_hub` | PBKDF2 auth, 17-app API, Shopify sync |
| **`5001`** | 3D Spatial Kinematics Lab | `0.0.0.0` (Mac/Linux) | `01_apps/spatial_grappling_3d` | Three.js WebGPU tatami arena |
| **`5050`** | Shadow Benchmarker API | `0.0.0.0` (Host Node) | `01_apps/shadow_benchmarker` | Dynamic VRAM sharding load balancer |
| **`5555`** | Android Debug Bridge (ADB) | `127.0.0.1` / Termux USB | `06_scripts_and_tooling` (ADB) | Shizuku & termux keepalive bridge |
| **`6333`** | Qdrant Vector Database | `127.0.0.1` / `100.101.39.98` | `04_data_and_memory` (Qdrant) | Semantic RAG embeddings store |
| **`6379`** | Apache Ray / Redis Cluster | `100.101.39.98` (Linux Head) | `00_core_infrastructure` (Ray) | Distributed compute cluster bus |
| **`8022`** | Termux OpenSSH Server | `100.73.38.87` / `100.84.40.95` | Pixel 10 Pro & Galaxy S20+ | Unprivileged mobile edge shell |
| **`8080`** | llama.cpp OpenAI API Gateway | `127.0.0.1` (Mac Mini Host) | `02_ai_models_and_inference` | Local AI inference endpoint |
| **`8081-8088`** | Crucible SLM Gladiator APIs | `127.0.0.1` (Edge Nodes) | `scripts/chaos_arena.py` | 8-way chaos arena inference ports |
| **`8085` / `31337`** | Petals DHT Layer Swarm | `0.0.0.0` (P2P Mesh) | `02_ai_models_and_inference` | Decentralized model sharding |
| **`8086`** | Edge Sensor Daemon | `0.0.0.0` (Edge Nodes) | `01_apps/Standalone_Services` | 15s rolling telemetry window |
| **`8087`** | LoRA Harvest Cron Service | `127.0.0.1` (Linux Head) | `lauburu_node_supervisor.py` | 15m dataset harvest trigger |
| **`8088`** | SeaweedFS Filer / Quartz SSG | `100.101.39.98` / `127.0.0.1` | `00_core_infra` & `01_apps/obsidian_web` | Distributed file system & digital garden |
| **`8265`** | Apache Ray Web Dashboard | `100.101.39.98` (Linux Head) | `00_core_infrastructure` (Ray) | Cluster resource & actor dashboard |
| **`8384`** | Syncthing Web Management | `127.0.0.1` / `100.x.x.x` | `00_core_infrastructure` (Syncthing) | P2P cluster GUI (256MB memory cap) |
| **`9333` / `19333`**| SeaweedFS Master & gRPC | `100.101.39.98` (Linux Head) | `00_core_infrastructure` (SeaweedFS) | 1.701 TB distributed storage master |
| **`18802`** | Nomad Courier WoL REST API | `0.0.0.0` (All Nodes) | `06_scripts_and_tooling` (Nomad) | Remote hardware wake-on-LAN daemon |
| **`22000-22003`** | Syncthing BEP Sync (TCP/UDP)| `0.0.0.0` (P2P Cluster) | `00_core_infrastructure` (Syncthing) | Encrypted TLS 1.3 block sync |
| **`50052`** | llama.cpp Metal/CPU RPC Server | `0.0.0.0` (6 Mesh Endpoints) | `02_ai_models_and_inference` | Low-latency (0.27ms) tensor sharding |
| **`52415`** | Exo Distributed Ring Pipeline | `0.0.0.0` (All Nodes) | `02_ai_models_and_inference` (Exo) | P2P ring memory layer splitting |

---

### 5.2 Comprehensive File Path & Subsystem Index

| Architectural Subsystem | Directory / File Path in Monorepo | Primary Language / Stack | Core Responsibility |
| :--- | :--- | :--- | :--- |
| **Port 4000 Canonical Hub** | `01_apps/port_4000_hub/server.py` | Python / FastAPI / Uvicorn | Master API, PBKDF2 auth, Shopify sync, 17-app catalog |
| **Zone 2 Endurance App** | `01_apps/lauburu_zone2_endurance/` & `01_apps/zone2_endurance/` | Dart / Flutter | Cross-platform athlete UI, live DFA-$\alpha_1$ audio coach |
| **Movesense 128Hz Hub** | `01_apps/movesense_hub/pyspark_biometrics_dsp.py` | Python / PySpark / Bleak | 128Hz raw ECG ingestion, Kamath filter, RMSSD, PTT BP |
| **3D Spatial Grappling** | `01_apps/spatial_grappling_3d/` & `10_spatial_grappling_kinematics/` | JavaScript / Three.js / WebGPU | 955-Node kinematic tree, joint torque, UWB tracking |
| **Swarm Dashboard** | `01_apps/swarm_dashboard/app.js` & `arena_canvas.html` | JavaScript / HTML5 Canvas | Tri-Orchestrator visualizer, live ELO arena, RAM governor |
| **Hemodynamic Cloud Server** | `01_apps/Standalone_Services/Hemodynamic_Cloud_Server/` | Python / FastAPI / NumPy | Moens-Korteweg, Bramwell-Hill, and Windkessel physics |
| **Shadow Benchmarker API** | `01_apps/shadow_benchmarker/server.py` | Python / FastAPI | Real-time TTFT/TPS testing, dynamic `routing.json` sync |
| **Hardware Sentinel** | `scripts/mesh_sentinel_profiler.py` & `live_device_sentinel.py` | Python / Textual TUI | Zero-VRAM profiler, Shizuku thermals, 4-pillar MIN speed |
| **Mesh Healer Daemon** | `scripts/smolagents_healer.py` & `smolagents_swarm_healer.py` | Python / `smolagents` | CodeAgent auto-repair, Tailscale flush, +15 ELO harvesting |
| **The Crucible Chaos Arena**| `scripts/chaos_arena.py` & `game_arena_manager.py` | Python / AsyncIO | 8-Gladiator SLM tournament, 7-tool recovery race, FFA ELO |
| **Hourly LoRA SFTTrainer** | `scripts/train_mesh_lora.py` | Python / Hugging Face TRL & PEFT | Continuous Qwen2.5-Coder-7B LoRA fine-tuning (NF4, $r=8$) |
| **Champion Vault Sync** | `06_scripts_and_tooling/champion_vault_sync.py` | Python / OS Symlinks | Symlinks highest-ranked ELO GGUF models to champion paths |
| **Nomad Mesh Governor** | `06_scripts_and_tooling/network/nomad_courier_self_healer.py` | Python / Subprocess | 14-Module self-healer, WoL API (Port 18802), autostart daemons |
| **SeaweedFS Distributed FS** | `00_core_infrastructure/systemd/dfs-fuse-mount.service` | Systemd / FUSE (`weed mount`) | 1.701 TB unified storage mount point (`/mnt/dfs_unified`) |
| **Syncthing 4-Node Cluster**| `00_core_infrastructure/docker/docker-compose.syncthing.yml` | Docker Compose / Syncthing | 4-Node P2P TLS 1.3 sync, 256MB memory cap per container |
| **Obsidian Commander Web** | `01_apps/obsidian_web/` | TypeScript / Preact / Quartz v5 | Canonical truth publisher, bidirectional wikilink graph |
| **Ray & Model Merger** | `00_core_infrastructure/multi_wan/ray_spark_model_merger.py` | Python / Ray / PyTorch | Distributed DARE-TIES & SLERP genetic weight merging |
| **24/7 LoRA Datasets** | `12_continuous_lora_evolution/lora_datasets/` | JSONL Data Files | 164.3MB `truth_audit_debate.jsonl`, Google Drive hourly sync |
"""

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(doc.strip() + '\n')

print(f"Successfully generated {target_path} (length: {len(doc)} chars, {len(doc.splitlines())} lines)")
