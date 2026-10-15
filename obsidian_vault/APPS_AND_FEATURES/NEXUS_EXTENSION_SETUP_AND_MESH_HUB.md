---
title: "Nexus Terminal Extension Setup & Sovereign Nexus Server Architecture"
tags: [nexus, terminal, mesh, ssh, tunnels, extension, vs_code, antigravity_ide, sovereign_server]
created: 2026-09-18
updated: 2026-09-19
---

# 👑 Nexus Terminal Extension Setup & Sovereign Nexus Server Architecture

## 📋 System Overview
The **Nexus Terminal Extension (`sentriflow.vscode-nexterminal-2.8.218-universal`)** provides direct GUI and command integration within Antigravity IDE and VS Code for managing:
1. **👑 The Sovereign Nexus Host** (`127.0.0.1:22` / `192.168.8.230` Mac Mini M4 Pro).
2. **Local Shell Environments** (Monorepo root, Screen Lens console, interactive Single-Chat Nexus CLI).
3. **Port Forwarding Tunnels** (Single-Chat Nexus `:4050`, prima.cpp Master `:8082`, Qwen Red Team `:8083`, Syntax Worker `:8081`, Screen Lens Stream `:4003`, SeaweedFS `:8888`, Self-Healing Hub `:18802`).
4. **Local Daemon Management** (Auto-restarting Single-Chat Nexus Mother Ship daemon on Port 4050).
5. **Interactive Quick-Trigger Macros** (Mesh health, thread listings, Bluetooth PAN escalation, telemetry streaming).

---

## ❓ Architectural Clarification: "Why Did We Have 9 Servers?"

### 1. The 7-Layer Physical Mesh Topology Origin
The monorepo's canonical hardware matrix pools 139.0 GB RAM across 9 physical hardware nodes:
1. **L1:** Host Mac Mini M4 Pro (`127.0.0.1` / `192.168.8.230`) — Host Sanctuary, Prompt Ingestion, Memory Governor.
2. **L2:** MacBook Pro Intel (`100.103.212.21`, LAN `192.168.8.127`, Unlinked TB) — Metal GPU RPC & 285GB Model Vault.
3. **L3:** Linux Head Node AMD Ryzen 7 5700U (`100.101.39.98`, LAN `192.168.8.225`) — Docker Hub, AI Training & Ray Cluster.
4. **L4:** Linux Tablet Debian (`100.99.210.89`, LAN `192.168.8.176` Port 2 Router) — Mobile Linux Compute & Touch DSP.
5. **L5:** MacBook Air M4 (`100.121.202.34`, LAN `192.168.8.248`) — Metal Performance Shaders Worker.
6. **L6:** Pixel 10 Pro XL Tensor G5 (`100.114.215.68:8022`, LAN `192.168.8.213`) — 8K Vision Stream & Edge TPU.
7. **L7:** Samsung Galaxy S20+ (`100.78.206.96:8022`, LAN `192.168.8.130`) — Dedicated Automated UI Tester & OpenClaw Target.
8. **L8:** Linux Mini `lauburu` (`100.121.247.8`, TB4 `10.0.0.8`) — 40 Gb/s TB4 DMA Bridge & 32 GB Compute Hub.
9. **GW:** GL.iNet Sovereign Gateway Router GL-BE14000 (`100.70.123.123:22`, LAN `192.168.8.1:22`) — Core Gateway & 2.5G NBN WAN.

When `nexus_extension_provisioner.py` was originally scaffolded, it populated the entire 9-node hardware inventory into `nexus-config-shared.json` so every physical box could theoretically be reached via SSH.

### 2. Why 9 Servers Created Confusion & The Host Name Resolution Error
- **Dormant Edge Devices:** In day-to-day development, 7 of those 9 nodes are peripheral mobile devices (tablets, phones, auxiliary laptops) that roam or sleep, resulting in offline status indicators.
- **The DNS Resolution Error:** In Nexus Terminal, attempting to import `nexus-config-shared.json` via "Import Servers from List (CSV/Text)" caused the extension to treat the filename `nexus-config-shared.json` as a server host. This generated a bogus server entry (`Host: nexus-config-shared.json`) which triggered:
  `Host name could not be resolved: Nexus could not resolve the server host name to an IP address.`

### 3. The Streamlined Architecture: "The Nexus Server"
To eliminate clutter, confusion, and resolution errors, the active Nexus Terminal configuration is streamlined to **The Nexus Server**:
- **Active Configuration (`nexus-config-shared.json` & `state.vscdb`):** Exactly 1 sovereign server — `👑 Sovereign Nexus Host (Mac Mini M4 Pro)` on `127.0.0.1:22`, directly connected to the Single-Chat Nexus Mother Ship (`:4050`).
- **Archive Configuration (`nexus-mesh-full-topology.json`):** Retains all 9 nodes for multi-machine cluster orchestration when needed.

---

## 👑 Active Sovereign Nexus Configuration

### 1. Active Server Profile (`nexus.servers`)
- **Name:** `👑 Sovereign Nexus Host (Mac Mini M4 Pro)`
- **Host / Port:** `127.0.0.1:22` (Alt: `192.168.8.230`)
- **Protocol / User:** `ssh` / `aaron`
- **Auth Type:** `agent` (SSH Agent)
- **Group:** `Nexus Sovereign/Host`

### 2. Port Forwarding Tunnels (`nexus.tunnels`)
- **Port 4050:** Single-Chat Nexus Mother Ship (`127.0.0.1:4050`)
- **Port 8082:** prima.cpp Master Orchestrator PRP Ring (`127.0.0.1:8082`)
- **Port 8083:** Qwen 3.8 Max 27B Abliterated Red Team (`127.0.0.1:8083`)
- **Port 8081:** Qwen 2.5 Coder 7B Subordinate Syntax Worker (`127.0.0.1:8081`)
- **Port 4003:** Screen Lens Live MJPEG Stream (`127.0.0.1:4003`)
- **Port 8888:** SeaweedFS Distributed DFS Filer (`127.0.0.1:8888`)
- **Port 18802:** Self-Healing Hub Orchestrator (`127.0.0.1:18802`)

### 3. Local Shell Profiles (`nexus.localShellProfiles`)
- **⚡ Lauburu Monorepo Root Shell:** `/bin/zsh -l`, CWD: `/Volumes/Lauburu-Monorepo`
- **👁️ Screen Lens Sovereign Console:** `/bin/zsh -l`, CWD: `/Volumes/Lauburu-Monorepo/01_apps/screen_lens`
- **💬 Single-Chat Nexus Interactive CLI:** `/bin/zsh -l`, CWD: `/Volumes/Lauburu-Monorepo`, Startup: `nexus status`

### 4. Local Server Daemon (`nexus.localServers`)
- **💬 Single-Chat Nexus Mother Ship (:4050):** Executable: `/Users/aaron/.local/bin/nexus`, Args: `["chat"]`, AutoRestart: `True`

### 5. Interactive Macros (`nexus.macros`)
- `Nexus: Mesh Status` ➡️ `nexus status\n`
- `Nexus: Query Health` ➡️ `curl -s http://127.0.0.1:4050/api/health | jq .\n`
- `Nexus: List Chat Threads` ➡️ `curl -s http://127.0.0.1:4050/api/chat/nexus/threads | jq .\n`
- `Nexus: Trigger LoRA Sync` ➡️ `curl -s -X POST http://127.0.0.1:4050/api/chat/nexus/lora/sync | jq .\n`
- `Nexus: Escalate to Bluetooth PAN` ➡️ `nexus dispatch --target all --directive ENABLE_PAN\n`
- `Screen Lens: Stream Telemetry` ➡️ `tail -f /Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/SCREEN_LENS_LIVE_OBSERVATIONS.md\n`

---

## 📁 Artifacts & Verifications
- **Canonical Provisioner:** [`06_scripts_and_tooling/nexus/nexus_extension_provisioner.py`](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/nexus/nexus_extension_provisioner.py)
- **Sovereign Export Schema:** [`nexus-config-shared.json`](file:///Volumes/Lauburu-Monorepo/nexus-config-shared.json) (7,650 B)
- **Full Mesh Archive:** [`nexus-mesh-full-topology.json`](file:///Volumes/Lauburu-Monorepo/nexus-mesh-full-topology.json) (11,749 B)
- **SQLite State Database:** `~/Library/Application Support/Antigravity IDE/User/globalStorage/state.vscdb`
