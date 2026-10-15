---
title: "Canonical 8-Node Mesh Device Role Matrix"
tags: [lauburu, infrastructure, roles, ai, swarm, hardware_matrix]
last_updated: "2026-10-12T10:10:00+11:00"
canonical_source: true
---

# 🏛️ Canonical Mesh Device Role Matrix (Probed 2026-10-12)

Governed by Rule 0 (Canonical Hardware Matrix), Rule 1 (Zero-Mock), Rule 3 (Host Sanctuary), Rule 8 (Pre-flight Gate), and Rule 10 (Linux Mini First-Offload).

---

## L1: Mac Mini M4 Pro (Primary Host — Mac_Node)
- **Local IPs**: `192.168.8.143` (Wi-Fi `en1`) / `192.168.8.230` (Ethernet `en0`) | **Tailscale**: `100.119.199.76` | **TB4 Bridge**: `bridge0` `10.0.0.2`
- **Hardware**: Apple M4 Pro (8P+4E CPU, 16-Core GPU, 16-Core ANE), 24.0 GB Unified Memory
- **RAM Sanctuary (Rule 3)**: Hard Cap: 80% (19.2 GB AI VRAM max), strictly preserving $\ge 4.8\text{ GB}$ free physical RAM at all times.
- **Roles**: Master Prompt Ingestion, Screen Lens Sovereign Core (:3035/:4003), Host Memory Governor, Swarm Coordinator.
- **Inference Runtime Reality**: 
  - Port 8082: `decentralized_prima_daemon.py` proxy forwarding to Port 8090 (`llama-server` Hermes-3 8B).
  - Port 8081: `mesh_multiport_bridge.py` proxy returning `Qwen2.5-VL-7B-Instruct-Q4_K_M`.
  - Port 8083: `mesh_multiport_bridge.py` proxy advertising `qwen_38_max_abliterated` (pointing to GGUF on L8).

## L8: Linux Mini Hub (lauburu — Tier 0 Thunderbolt 4 Co-Processor)
- **TB4 IP**: `10.0.0.8` (`bridge0` Receptacle 1, **40 Gb/s PCIe DMA, 0.38 ms avg RTT**)
- **Local LAN**: `192.168.8.242` | **Tailscale**: `100.121.247.8` (3.5 ms RTT)
- **Hardware**: Intel Core i7-8700B (12 threads), 32.0 GB RAM, Ubuntu 24.04 LTS (Linux 6.8 x86_64)
- **RAM Cap**: 80% (25.6 GB AI VRAM max)
- **Roles**: 
  - Primary GGUF Model Vault Hub (`/home/linuxmini/model_vault_gguf/` containing `Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf`)
  - 40 Gbps TB4 DMA Bridge Anchor to L1 Mac Mini
  - Glances v4 System Telemetry (:61208), KDE Connect active

## L1b: Mac Mini M2 Pro (MacMini_M2 — Secondary Mac & Compute Worker)
- **TB4 IP**: `10.0.0.3` (`bridge0` Receptacle 2, **40 Gb/s PCIe DMA, 0.43 ms avg RTT**)
- **Local LAN**: `192.168.8.114` | **Tailscale**: `100.104.128.34`
- **Hardware**: Apple M2 Pro, Mac14,12 (10-Core CPU, 16-Core GPU), 16.0 GB Unified Memory
- **RAM Cap**: 85% (13.6 GB AI VRAM max)
- **Roles**: Secondary inference node, AST validation, TB4 cluster compute worker.

## L2 / L1c: MacBook Pro Intel (MacBook_Pro — Automation Worker & Teacher Target)
- **TB4 IP**: `10.0.0.4` (`bridge0` Receptacle 3, **40 Gb/s PCIe DMA, MTU 9000**)
- **Local LAN**: `192.168.8.127` (Probed RTT: 4.67 ms) | **Tailscale**: `100.103.212.21` (RTT ~9-38 ms)
- **Hardware**: Intel Core i7-9750H (6C/12T), 16.0 GB RAM, 285 GB SSD Model Vault
- **RAM Cap**: 90% (14.0 GB AI VRAM max)
- **Roles**: 
  - Screen Lens Sovereign Teacher Target: Authorized execution node for macOS desktop automation (`osascript` / AppleScript) under Lens Teacher supervision
  - Secondary x86_64 Worker & Glances v4 (:61208)

## L3: Linux Head Node (Linux_Head_Node — Compute Hub & First-Offload Target)
- **Local LAN**: `192.168.8.225` | **Tailscale**: `100.101.39.98` (RTT ~6.4 ms)
- **Hardware**: AMD Ryzen 7 5700U (8C/16T), 15.0 GB RAM, Ubuntu Linux x86_64
- **Bluetooth Link**: Connected to L1 (-28 dBm)
- **RAM Cap**: 80% (12.0 GB AI VRAM max)
- **Roles**: 
  - **Rule 10 First-Offload Invariant**: Absorbs background servers (Docker Hub, Ray Head, SeaweedFS DFS, Qdrant vector DB)
  - Glances v3 System Telemetry (:61208)

## L4: Linux Tablet (Linux_Tablet — Bedside Mobile Compute & Touch DSP)
- **Local LAN**: `192.168.8.176` (Wired Port 2 on GL-BE14000, 0.95 ms RTT) | **Tailscale**: `100.99.210.89`
- **Hardware**: Debian Linux Touch Tablet (`debian-1`), 8.0 GB RAM
- **RAM Cap**: 75% (6.0 GB AI VRAM max)
- **Roles**: Bedside Interactive TUI Terminal, Touch DSP Digitizer, Lightweight Telemetry Collector

## L5 / L1a: MacBook Air M4 (MacBook_Air — Metal Worker & LoRA Distillation)
- **Local LAN**: `192.168.8.248` (Wi-Fi) | **Tailscale**: `100.121.202.34` (RTT ~12 ms)
- **Hardware**: Apple M4 (4P+6E CPU, 10-Core GPU, 16-Core ANE), 16.0 GB Unified RAM
- **RAM Cap**: 90% (14.0 GB AI VRAM max)
- **Roles**: Secondary Metal Performance Shaders worker, 24/7 continuous LoRA adapter distillation, Glances v4 (:61208)

## L6: Google Pixel 10 Pro XL (Pixel_10_Pro_XL — Edge TPU & 8K Video Stream)
- **Local LAN**: `192.168.8.213` (Wi-Fi 7) | **Tailscale**: `100.114.215.68` (Termux: `100.124.199.15`)
- **Hardware**: Google Tensor G5 silicon + Edge TPU, 16.0 GB RAM, Android 15
- **Ports**: 8022 (Termux SSH) & 1716 (KDE Connect) OPEN
- **RAM Cap**: 85% (13.6 GB AI VRAM max, requires `termux-wake-lock`)
- **Roles**: Edge TPU VLA inference, 8K Digital PTZ camera stream, Shizuku rish privileged execution

## L7: Samsung Galaxy S20+ (Samsung_S20 — Dedicated Automated UI Tester)
- **Local LAN**: `192.168.8.130` (Wi-Fi) / `192.168.8.224` (USB Eth adapter) | **Tailscale**: `100.78.206.96`
- **Hardware**: Samsung Exynos 990, 12.0 GB RAM, Android 13
- **Bluetooth**: Paired BT (`5c-cb-99-05-81-41`)
- **RAM Cap**: 75% (9.0 GB AI VRAM max)
- **Roles**: Dedicated OpenClaw mobile UI automation tester, ADB target (:5039 / :5555)

## GW: GL.iNet GL-BE14000 (Router — Core Gateway & Hardware USB Bridge)
- **Local LAN**: `192.168.8.1` | **Tailscale**: `100.70.123.123` (RTT 3.5 ms)
- **WAN**: 2.5GbE Port (`eth2`) connected to NBN NTD (12 ms RTT to 1.1.1.1, 0% loss)
- **Hardware**: MediaTek Filogic 880 Quad-Core, 2.0 GB RAM (1.38 GB free, 1 GB overlay swap active)
- **Roles**: Sovereign Gateway, 2.5G NBN WAN Uplink, Hardware USB ADB Daemon, Port 18802 C Sentinel

---

## 🔌 Master Port Allocation Matrix (Probed Reality)
| Port | Process | Function & Reality | Status |
|---|---|---|---|
| **3035** | `lauburu-lens` | Screen Lens Core Daemon | PROBED |
| **3036** | `screen_life_companion.py` | Screen Life Companion Daemon | PROBED |
| **3037** | `lens_global_orchestrator.py` | Lens Global Orchestrator | PROBED |
| **4000** | `lauburu-s` | Sovereign Biometrics / Console Service | PROBED |
| **4001** | `omniterminal_production_supervisor.py` | Omni Terminal Supervisor & SSH tunnel | PROBED |
| **4003** | `core.stream_service` | Screen MJPEG Stream Service (10–15 FPS) | PROBED |
| **4005** | `bluetooth_serial_terminal_daemon.py`| Bluetooth Serial Terminal Daemon | PROBED |
| **4006** | `sovereign_remote_desktop_server.py` | Sovereign Remote Desktop Server | PROBED |
| **4007** | `network_cable_analyzer` | Network Cable & Mesh Analyzer | PROBED |
| **8080** | `python3` | Local Web Service | PROBED |
| **8081** | `mesh_multiport_bridge.py` | Proxy returning `Qwen2.5-VL-7B-Instruct-Q4_K_M` | PROBED |
| **8082** | `decentralized_prima_daemon.py` | Proxy forwarding to :8090 Hermes-3 8B (Target: Qwen 3.8 Max) | PROBED |
| **8083** | `mesh_multiport_bridge.py` | Proxy advertising `qwen_38_max_abliterated` (pointing to GGUF on L8) | PROBED |
| **8085 / 8087** | `weed` (SeaweedFS) | SeaweedFS Distributed Storage Endpoints | PROBED |
| **8088** | `canonical_port/tui/serve_web_*` | Universal Web-TUI Bridge | PROBED |
| **8090** | `llama-server` b10545 | `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf`, Metal, ctx 16384 | PROBED |
| **8095** | `neo-mcp-launcher` | Neo MCP Launcher | PROBED |
| **8890** | `voila` | Voilà Notebooks Master Cyber Studio | PROBED |
| **9119** | `hermes_mesh_daemon.py` | Hermes Mesh Daemon | PROBED |
| **9999** | `lauburu_project_mcp.py` | Project MCP Server | PROBED |
| **18802** | `self_healing_hub.py` | Self-Healing Hub | PROBED |
| **50052** | `llama_rpc_shard_daemon.py` | Tensor RPC Socket Server | PROBED |
| **61208** | `glances` | Glances System Telemetry Server | PROBED |
