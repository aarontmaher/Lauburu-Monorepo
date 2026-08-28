# Comprehensive Codebase & Design History Survey Report
**Focus Domains**: `00_core_infrastructure`, `06_scripts_and_tooling`, `07_docs_and_architecture`, Hardware Sentinel, Mesh Healer, Mac Air Sync Orchestrator  
**Auditor**: `survey_explorer_1_gen2`  
**Timestamp**: 2026-08-26T01:15:00Z  
**Monorepo Root**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`

---

## Executive Summary

This comprehensive audit surveys the core infrastructure, operational tooling, architectural specifications, and edge daemon ecosystems across the Lauburu Monorepo. All observations are verified directly against source code files, Docker Compose definitions, systemd service units, shell scripts, Python daemons, and architectural markdown documents.

---

## 1. 00_core_infrastructure: Core Mesh Infrastructure & Containerization

### 1.1 SeaweedFS Distributed File System Cluster
- **Manifest Reference**: `00_core_infrastructure/README.md:7-18`
- **Topology Spec**: `07_docs_and_architecture/mesh_storage_topology.md:1-54`
- **Total Namespace Capacity**: 1.701 TB aggregated into mount point `/mnt/dfs_unified`
- **Network Ports & Protocol Allocations**:
  - SeaweedFS Master: `100.101.39.98:9333` (gRPC: `19333`)
  - SeaweedFS Filer: `100.101.39.98:8888` (gRPC: `18888`)
  - SeaweedFS Volume Server: `100.101.39.98:8080` (gRPC: `18080`)
  - Samba SMB3 Gateway: `100.101.39.98:445` & `139` (`dperson/samba` container with Apple VFS Fruit extensions)
- **Kernel FUSE Mount Unit (`00_core_infrastructure/systemd/dfs-fuse-mount.service`)**:
  ```ini
  [Unit]
  Description=Lauburu Unified Distributed File System (DFS) Kernel FUSE Mount
  After=network-online.target tailscaled.service docker.service
  Wants=network-online.target
  Requires=docker.service

  [Service]
  Type=simple
  User=root
  Group=root
  ExecStartPre=/bin/mkdir -p /mnt/dfs_unified
  ExecStartPre=/bin/sh -c "grep -q 'user_allow_other' /etc/fuse.conf || echo 'user_allow_other' >> /etc/fuse.conf"
  ExecStart=/usr/local/bin/weed mount \
      -filer=100.101.39.98:8888 \
      -dir=/mnt/dfs_unified \
      -filer.path=/ \
      -allowOthers=true \
      -umask=000 \
      -cacheCapacityMB=128 \
      -chunkSizeLimitMB=16 \
      -concurrentWriters=32 \
      -readOnly=false
  ExecStop=/bin/fusermount3 -u -z /mnt/dfs_unified
  Restart=always
  RestartSec=5
  ```
- **Datacenter Sharding Architecture**:
  - `[DataCenter: Thunderbolt]`: Mac Mini M4 Pro internal NVMe. Hosts physical GGUF models, Exo weights, Champion Vault, and Qdrant Vector DBs. Accessed by MacBooks over 40 Gbps Thunderbolt 4 (3.6 GB/s DMA).
  - `[DataCenter: WiFi]`: Linux Hub internal NVMe. Dedicated to archival logs, scrapers, and datasets. Docker containers utilize native local `ext4` to prevent SQLite network-lock corruption.

---

### 1.2 4-Node Core Syncthing P2P Cluster
- **Configuration File**: `00_core_infrastructure/docker/docker-compose.syncthing.yml`
- **Architecture**: Peer-to-peer encrypted Block Exchange Protocol (BEP) over TLS with hard 256MB memory ceilings per container to preserve the 75% host RAM safety margin.
- **Node Allocation Table**:

| Container Name | Target Node | Role | Tailscale IP / Port | Sync Port (TCP/UDP) | Mem Limit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `syncthing_mac_node` | M4 Mac Mini (Host) | Layer 1 Orchestrator | `100.84.87.3:8384` | `22000` | 256 MB |
| `syncthing_macbook_pro` | Headless MacBook Pro | Layer 2 Storage Vault | `100.103.212.21:8384` | `22001` | 256 MB |
| `syncthing_linux_head_node`| Linux Head Node | Layer 3 P2P Hub | `100.101.39.98:8384` | `22002` | 256 MB |
| `syncthing_mac_mini` | MacBook Air Compute | Layer 5 GPU Worker | `100.93.158.96:8384` | `22003` | 256 MB |

---

### 1.3 Canonical 7/8-Node Hardware Mesh Topology & Tailscale Overlay
- **Source of Truth**: `00_core_infrastructure/self_healing_hub/src/devices.json` & `~/.gemini/config/skills/mesh-universal-ssh/SKILL.md`
- **Topology Breakdown**:

```
                                  ┌────────────────────────────────┐
                                  │   Layer 1: Host Mac Mini M4    │
                                  │ 100.119.199.76 / 192.168.8.230 │
                                  │  21.6 GB VRAM (Port 22 / 50052)│
                                  └───────────────┬────────────────┘
                                                  │
                 ┌────────────────────────────────┼────────────────────────────────┐
                 │                                │                                │
┌────────────────▼───────────────┐ ┌──────────────▼───────────────┐ ┌──────────────▼───────────────┐
│ Layer 2: MacBook Pro M1 Max    │ │ Layer 3: Linux Head Node     │ │ Layer 5: MacBook Air M2/M4    │
│ 100.103.212.21 / 192.168.8.127 │ │ 100.101.39.98 / 192.168.8.224│ │ 100.93.158.96 / 192.168.8.222│
│ TB4: 169.254.187.138 (Port 22) │ │ Ray Head / Docker (Port 22)  │ │ Metal Shaders (Port 22)       │
│ 14.0 GB VRAM / 285GB NVMe Vault│ │ 13.8 GB VRAM / Ryzen 7       │ │ 13.5 GB VRAM                  │
└────────────────────────────────┘ └──────────────┬───────────────┘ └───────────────────────────────┘
                                                  │
                 ┌────────────────────────────────┼────────────────────────────────┐
                 │                                │                                │
┌────────────────▼───────────────┐ ┌──────────────▼───────────────┐ ┌──────────────▼───────────────┐
│ Layer 4: Bedside Linux Tablet  │ │ Layer 6: Pixel 10 Pro XL     │ │ Layer 7: Samsung Galaxy S20+  │
│ 100.81.92.125 / 192.168.8.173  │ │ 100.73.38.87 (Port 8022)     │ │ 100.84.40.95 (Port 8022)     │
│ 6.5 GB VRAM / Touch HUD        │ │ 12.5 GB VRAM / Edge TPU G5   │ │ 9.0 GB ARM / OpenClaw UI Test │
└────────────────────────────────┘ └──────────────────────────────┘ └──────────────────────────────┘
```

---

## 2. 06_scripts_and_tooling: Network Healing, Automation & Daemons

### 2.1 Multi-WAN Nomad Courier Autonomous Self-Healer
- **Source File**: `06_scripts_and_tooling/network/nomad_courier_self_healer.py`
- **Daemon Version**: v3.0
- **Operational Cadence**: 30-second continuous loop (`--daemon`) or single-pass (`--once`)
- **Key Modules**:
  1. `heal_localhost_3000`: Audits Web Hub UI availability on port 3000.
  2. `heal_wol_api_18802`: Restores Wake-on-LAN REST API daemon on port 18802.
  3. `heal_tplink_extender_mesh`: Audits Ethernet interface (`enx98fc84e6e212`, `eth0`), checks router gateway (`192.168.8.1`), and asserts policy routing table 200 (`ip rule add lookup 200`).
  4. `heal_ai_compute`: Probes llama.cpp RPC Server on port 50052 across 6 mesh endpoints.
  5. `heal_antigravity_skills`: Immunizes 39 Antigravity skills by syncing to `~/.gemini/config/skills/` and `/Users/aaron/DFS_UNIFIED/.agents/skills/`.
  6. `heal_mcp_health`: Reconciles `~/.gemini/settings.json` and `~/.gemini/config/mcp_config.json` to purge dead `/Volumes` paths and assert `/Users/aaron/DFS_UNIFIED`.
  7. `document_to_obsidian`: Refreshes `00_SYSTEM_DASHBOARDS/NOMAD_AUTONOMOUS_MESH_DASHBOARD.md`.
  8. `enforce_dark_shield`: Executes AppleScript `tell appearance preferences to set dark mode to true`.
  9. `heal_genetic_storage`: Supervises `nomad_genetic_storage_self_improving_cron.py`.
  10. `heal_autostart_daemons`: Deploys `ai.lauburu.nomad_courier.plist` (macOS), `lauburu_nomad.service` (Linux), or `99_lauburu_nomad.sh` (Termux).

### 2.2 Champion Vault AI Sync Engine
- **Source File**: `06_scripts_and_tooling/champion_vault_sync.py`
- **Function**: Reads ELO leaderboard data from `04_data_and_memory/data/ai_elo_leaderboard.json`, filters by non-cloud specialist tiers, finds physical `.gguf` binaries in `/Volumes/localhost/AI_Models/gguf`, `/Volumes/localhost/AI_Models/exo`, `/Users/aaron/models`, and symlinks the champion model into `/Volumes/localhost/AI_Models/champions/<role>/`. If missing, creates `<model>.gguf.pending` placeholder.

### 2.3 WoL Manager & Multi-Interface Broadcast
- **Source File**: `06_scripts_and_tooling/mesh/wol_manager.py` & `00_core_infrastructure/self_healing_hub/src/universal_mesh_healer.py:38-58`
- **Protocol**: Transmits RFC 792 UDP Magic Packets (`b"\xff"*6 + mac_bytes*16`) across broadcast addresses `192.168.8.255`, `255.255.255.255`, and `169.254.255.255` on UDP ports 9 and 7. Dispatches router-side `etherwake` over SSH to GL.iNet router (`192.168.8.1`).

---

## 3. 07_docs_and_architecture: Specifications & Security Models

### 3.1 Architectural Whitepapers Catalog
1. `ios_edge_compute_architecture_whitepaper.md`: CoreBluetooth State Restoration, background execution audio/VoIP entitlement bypass, and Tailscale `NetworkExtension` bridging.
2. `edge_compute_token_tracker_specification.md`: Cryptographic HMAC-SHA256 ledger tracking compute contributions and subscription credits.
3. `local_rag_core_agi_bridge_specification.md`: Multi-tier streaming protocol linking Edge RAG agents to 7-Device Mesh AGI.
4. `7_device_hardware_topology.md`: Canonical IP matrix, RAM limits, dynamic ceilings, and failover pathways.
5. `browser_automation_vlm_audit_spec.md`: Multi-frame sequential vision verification for UI testing.
6. `MOVESENSE_BLUETOOTH_ARCHITECTURE_DEBATE.md`: Direct BLE GATT streaming vs intermediary hub comparison for biometrics.

### 3.2 Security & Isolation Architecture
- **Passwordless SSH**: Strict ed25519 authentication (`~/.ssh/id_ed25519_monorepo`, `~/.ssh/id_ed25519`).
- **Port Isolation**: Strict bifurcation between root/user OpenSSH (Port 22) and unprivileged Android Termux OpenSSH (Port 8022).
- **Zero Cloud Leakage**: Local AI models process code and telemetry locally; all inference is routed to local llama.cpp RPC ports (`:50052`) or local API gateways (`:8080`, `:5001`).

---

## 4. Key Specific Applications & Edge Daemons

### 4.1 Lauburu Hardware Sentinel
- **Core Files**: `scripts/mesh_sentinel_profiler.py`, `00_core_infrastructure/self_healing_hub/src/live_device_sentinel.py`, `adaptive_device_hardware_governor.py`, `samsung_battery_power_monitor.py`
- **Zero-VRAM Textual Architecture**: Runs purely in Python standard library and lightweight psutil/socket interfaces. Consumes 0 MB GPU/VRAM memory, ensuring zero interference with 82.8 GB inference pool.
- **Shizuku & Android Thermal Integration**:
  - Queries `dumpsys battery`, `dumpsys deviceidle whitelist`, and `termux-battery-status`.
  - Measures live voltage (`voltage_mv`), charging current (`current_now_ma`), temperature in 0.1°C units, and battery health.
  - Detects OEM thermal charging cutoffs (>38.0°C) and dispatches screen stay-awake keepalives.
- **Mac & Linux Wake Locks**:
  - macOS: `caffeinate -dimsu` power assertions via SSH.
  - Linux: `systemd-inhibit --what=sleep:idle:handle-lid-switch` and systemd target masking.
  - Android: `/data/data/com.termux/files/usr/bin/termux-wake-lock` and Doze whitelisting (`cmd deviceidle whitelist +com.termux`).
- **4-Pillar Constraint Math Formula**:
  $$\text{Effective Speed} = \min(\text{Host}_{\max\_usb\_gbps}, \text{Device}_{\max\_usb\_gbps})$$
  - Hardware Specs:
    - `MacMini_M4`: 40.0 Gbps (Host Max)
    - `MacBookPro`: 40.0 Gbps (Device/Host Max)
    - `Pixel_10_Pro`: 10.0 Gbps (Device Max)
    - `Samsung_S20_Plus`: 5.0 Gbps (Device Max)
  - Anti-Waste Decision Logic:
    ```python
    effective_max = min(host_max, dev_max)
    if current_speed_gbps < effective_max:
        return {"upgrade_recommended": True, "target_gbps": effective_max, "reason": f"Current cable ({current_speed_gbps}Gbps) is bottlenecking. Both host and device support {effective_max}Gbps."}
    else:
        return {"upgrade_recommended": False, "target_gbps": current_speed_gbps, "reason": "Hardware physically capped. Upgrading cable will yield $0 ROI."}
    ```
- **Adaptive Hardware Governor Context Modes**:
  - `HUMAN_INTERACTIVE_MODE`: 58% RAM cap, 45% CPU cap, 80% NPU cap (protects 60 FPS UI fluidity).
  - `AUTONOMOUS_MAX_SURGE_MODE`: 94% RAM cap, 92% CPU cap, 100% NPU cap (overnight/idle maximum throughput).

---

### 4.2 Lauburu Mesh Healer
- **Core Files**: `scripts/smolagents_healer.py`, `scripts/smolagents_swarm_healer.py`, `00_core_infrastructure/self_healing_hub/src/universal_mesh_healer.py`
- **HuggingFace `smolagents` Autonomous CodeAgent**:
  - Wraps local models (`qwen2.5-coder-7b` on port 8080 or SLM Swarm <3B: `Qwen2.5-Coder-1.5B` on :8081, `Llama-3.2-1B` on :8082, `Gemma-2-2B` on :8083, `DeepSeek-Coder-1.3B` on :8084).
  - Autonomous Code Execution: Generates and runs Python code in real-time to inspect network interfaces, execute ADB commands, or rebind sockets.
- **Swarm ELO Race Arena**:
  - Broadcasts crash logs simultaneously across all edge models.
  - `asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)` enforces a real-time race condition.
  - Fastest model with a verified working fix earns +15 ELO in `04_data_and_memory/elo_scores.json`.
  - Fixes are harvested as JSONL training pairs to `04_data_and_memory/lora_dataset.jsonl` for continuous SFTTrainer fine-tuning.
- **Multi-Stage Network & Process Remediation**:
  - Tailscale flush: `killall -HUP mDNSResponder; Tailscale up --accept-routes=true`.
  - Zombie PID hunting: `pkill -f llama-rpc-server; nohup /usr/local/bin/llama-rpc-server -H 0.0.0.0 -p 50052 > /tmp/rpc.log 2>&1 &`.
  - Android Keepalive: `dumpsys deviceidle whitelist +com.termux; termux-wake-lock; nohup sh -c "while true; do ping -c 1 -W 2 100.119.199.76; sleep 15; done" &`.

---

### 4.3 Mac Air Sync Orchestrator
- **Core Files**: `06_scripts_and_tooling/mesh/syncthing_vault_mesh.py`, `00_core_infrastructure/docker/docker-compose.syncthing.yml`, `00_core_infrastructure/self_healing_hub/src/syncthing_handler.py`
- **Decentralized Vault Synchronization**:
  - Synchronizes master Obsidian vault (`/Users/aaron/DFS_UNIFIED`) and monorepo datasets across 4 core peers (Mac Mini Host, MacBook Pro Vault, Linux Head Node, MacBook Air M2/M4).
  - Protocol: Block Exchange Protocol (BEP) over TLS 1.3 with AES-128-GCM encryption.
  - $0.00 recurring cloud spend with continuous zero-cloud replication.
- **Resource & Security Constraints**:
  - Hard memory cap of 256MB per node (`mem_limit: 256m`, `cpus: '1.0'`).
  - Isolated configuration paths per device (`/Volumes/Lauburu-Monorepo/data/syncthing_config/<node_name>`).
  - Health checks: `nc -z 127.0.0.1 8384 || curl -fk http://127.0.0.1:8384/rest/system/ping`.

---

## 5. Architectural Map & Cross-Subsystem Integration Matrix

| Subsystem | Primary Ports | Key Daemons / Scripts | Hardware Nodes Involved | Core Function |
| :--- | :--- | :--- | :--- | :--- |
| **00_core_infrastructure** | `9333`, `8888`, `8080`, `445`, `139`, `8384` | `dfs-fuse-mount.service`, `docker-compose.syncthing.yml` | Mac Mini, Linux Head, MBP, MBA | SeaweedFS DFS, SMB3 gateway, Syncthing P2P cluster |
| **06_scripts_and_tooling** | `18802`, `3005`, `50052` | `nomad_courier_self_healer.py`, `champion_vault_sync.py` | All 7 devices + GL.iNet Router | 14-module auto-healer, WoL API, ELO champion sync |
| **07_docs_and_architecture** | N/A | Whitepapers, IP matrices, topology specs | All 7 devices | Canonical architectural truth, HMAC token ledgers |
| **Hardware Sentinel** | `4000`, `8022`, `5555` | `live_device_sentinel.py`, `mesh_sentinel_profiler.py` | Pixel 10 Pro, Samsung S20+, Macs | Zero-VRAM TUI, Shizuku thermals, 4-pillar math |
| **Mesh Healer** | `8080-8084`, `50052` | `smolagents_healer.py`, `universal_mesh_healer.py` | Local models on Mac, Pixel, S20, Router | CodeAgent auto-repair, ELO arena, LoRA harvest |
| **Mac Air Sync** | `8384`, `22000-22003` | `syncthing_vault_mesh.py`, `syncthing_handler.py` | MacBook Air, Mac Mini, MBP, Linux | BEP TLS sync, 256MB memory ceiling, $0 cloud |

