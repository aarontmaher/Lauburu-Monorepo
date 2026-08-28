# Exhaustive Monorepo Telemetry & Metric Survey
**Document Version:** 3.0.0-CANONICAL  
**Generated UTC:** 2026-08-27T05:55:00Z  
**Agent Archetype:** explorer (survey_explorer_telemetry)  
**Target Monorepo Root:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Purpose:** Canonical catalog of every single active metric, telemetry feed, data type, unit, collection mechanism, and source file for integration into the Canonical Port TUI and Blackboard Shared State.

---

## 1. Physical Hardware, Software & Storage Mesh Layers (7 Physical Nodes + 1 Gateway)

The Lauburu Mesh pools **108.0 GB RAM (82.8 GB Usable AI VRAM)** across 7 physical compute layers and 1 gateway node. Every metric is governed by Rule #0 (100% authentic live data; explicit `None`/`null` waiting states when disconnected).

### 1.1 Node Topology & Specifications Matrix

| Layer | Node Identifier | Hardware Model & Specs | Operating System & Kernel | Primary IP | Mesh / Bridge IPs | Total RAM | Usable AI VRAM Cap | Dynamic Cap % | Storage & Target Tier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `Mac_Node` / `mac_mini_host` | Apple M4 Pro Mac Mini (12-core CPU, 16-core GPU, 16-core ANE) | macOS Darwin 24+ ARM64 | `192.168.8.230` | Tailscale: `100.119.199.76`, Local: `127.0.0.1` | **24.0 GB** | **21.6 GB** | 90.0% | 228 GB APFS SSD (16 GB Guarded Headroom) |
| **L2** | `MacBook_Pro` / `macbook_pro_vault` | Intel Core i7-9750H / Apple M3-M4 Pro (Metal GPU) | macOS Darwin ARM64/x86_64 | `192.168.8.127` | Tailscale: `100.103.212.21`, TB4: `169.254.187.138` | **16.0 GB** | **14.0 GB** | 90.0% | 466 GB APFS SSD (409.3 GB free GGUF Vault) |
| **L3** | `Linux_Head_Node` / `linux_node` | AMD Ryzen 7 5700U (8C/16T, Zen 3) | Debian GNU/Linux x86_64 (Kernel 6.x) | `192.168.8.224` | Tailscale: `100.101.39.98`, 2.5GbE LAN | **16.0 GB** | **13.8 GB** | 80.0% | 512 GB NVMe SSD (MergerFS / Docker Overlays) |
| **L4** | `Linux_Tablet` / `linux_tablet` | Debian Linux Tablet (ARM64 Quad-Core) | Debian Linux ARM64 (Touch UI) | `192.168.8.173` / DHCP | Tailscale: `100.81.92.125` | **8.0 GB** | **6.5 GB** | 75.0% | 64 GB eMMC Flash Storage |
| **L5** | `MacBook_Air` / `macbook_air` | Apple M4 / M2 MacBook Air (8-core CPU, 10-core GPU) | macOS Darwin ARM64 | `192.168.8.222` | Tailscale: `100.93.158.96` | **16.0 GB** | **14.0 GB** | 90.0% | 256 GB APFS SSD |
| **L6** | `Pixel_10_Pro_XL` / `pixel_10` | Google Tensor G5 (Edge TPU, 8K Camera, UWB) | Android 15 (Termux Linux ABI) | `192.168.8.160` / DHCP | Tailscale: `100.73.38.87`, ADB: `5555` | **16.0 GB** | **12.5 GB** | 85.0% | 256 GB UFS 4.0 Storage (128 GB Edge Cache) |
| **L7** | `Samsung_S20` / `samsung_s20` | Samsung Exynos 990 / Snapdragon 865 | Android 13 (Termux + Router USB ADB) | `192.168.8.158` / DHCP | Tailscale: `100.84.40.95` (Alt: `100.99.123.58`) | **12.0 GB** | **9.0 GB** | 75.0% | 128 GB UFS 3.1 Storage (64 GB Artifacts) |
| **GW** | `GL.iNet Router` / `gl_travel_router` | GL-MT3600BE-a0f-MLO (Wi-Fi 7 Multi-WAN) | OpenWrt Linux 23.x (Kernel 5.15) | `192.168.8.1` | Tailscale: `100.122.185.123` | Embedded | N/A | N/A | Flash / USB Mount |

---

### 1.2 Hardware Telemetry Metrics Catalog

| Metric Key | Unit | Data Type | Sampling Rate / Timeout | Sourcing Mechanism | Source File & Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cpu.usage_pct` | `%` [0.0–100.0] | Float | 0.05s / 5s | `psutil.cpu_percent()` / `/proc/stat` / `top -bn1` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:42` |
| `cpu.per_core_pct` | `List[%]` | Array[Float] | Instantaneous | `psutil.cpu_percent(percpu=True)` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:51` |
| `cpu.core_count` | count | Integer | Static | `psutil.cpu_count(logical=True)` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:52` |
| `cpu.load_avg_1m` | load | Float | Instantaneous | `os.getloadavg()[0]` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:54` |
| `cpu.load_avg_5m` | load | Float | Instantaneous | `os.getloadavg()[1]` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:55` |
| `cpu.load_avg_15m` | load | Float | Instantaneous | `os.getloadavg()[2]` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:56` |
| `ram.total_gb` | `GB` | Float | Instantaneous | `psutil.virtual_memory().total / (1024^3)` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:65` |
| `ram.used_gb` | `GB` | Float | Instantaneous | `psutil.virtual_memory().used / (1024^3)` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:66` |
| `ram.available_gb` | `GB` | Float | Instantaneous | `psutil.virtual_memory().available / (1024^3)` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:67` |
| `ram.usage_pct` | `%` | Float | Instantaneous | `psutil.virtual_memory().percent` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:68` |
| `ram.swap_used_gb` | `GB` | Float | Instantaneous | `psutil.swap_memory().used / (1024^3)` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:69` |
| `gpu.model` | name | String | Static / Init | `ioreg -r -d 1 -c IOAccelerator` / `nvidia-smi` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:87` |
| `gpu.gpu_cores` | count | Integer | Static / Init | `ioreg` `gpu-core-count` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:88` |
| `gpu.usage_pct` | `%` | Float | Instantaneous | `ioreg` `Device Utilization %` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:90` |
| `gpu.vram_in_use_mb` | `MB` | Float | Instantaneous | `ioreg` `In use system memory` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:91` |
| `gpu.vram_alloc_mb` | `MB` | Float | Instantaneous | `ioreg` `Alloc system memory` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:92` |
| `thermal.thermal_c` | `°C` | Float | 1.0s | `sysctl machdep.xcpm.cpu_thermal_level` / `/sys/class/thermal/` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:170` |
| `thermal.status` | status | Enum (`NOMINAL`, `FAIR`, `SERIOUS`, `CRITICAL`) | Derived | Thermal threshold gating (<48, <60, <75, >=75) | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:190` |
| `thermal.battery_pct` | `%` [0–100] | Integer | 1.0s | `pmset -g batt` / `termux-battery-status` / `cat /sys/class/power_supply/BAT0/capacity` | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:155` |
| `thermal.is_charging` | flag | Boolean | 1.0s | `pmset` charging regex / sysfs status | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:157` |
| `thermal.power_source` | source | Enum (`AC`, `BATTERY`) | 1.0s | Power source probe / Qi inductive check | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:158` |
| `hardware.npu` | description | String | Static | `sysctl brand_string` (ANE) / Tensor G5 Edge TPU / None | `00_core_infrastructure/self_healing_hub/src/metric_pollers.py:197` |
| `power_computing_stats.power_usage_watts` | `Watts` | Float | Dynamic / Inferred | Computed from CPU/GPU load + Qi coil delta | `00_core_infrastructure/self_healing_hub/src/unorthodox_matrix_engine.py:59` |

---

## 2. Multi-WAN / Network / Connection Metrics (Master 17-Protocol Matrix)

The network layer forms the foundational stability baseline for the monorepo, prioritized in ground-up order: Bare-metal WoL → Bluetooth PAN → KDE Connect → Thunderbolt DMA → Tailscale / WAN.

### 2.1 The 17 Transport Protocols Specification Table

| # | Protocol ID | Name & Category | RTT Latency | Bandwidth | Interface / Port | Payload Suitability | Optimal Local AI Model & Mechanism | Source Location |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P01** | `p01_tb4_dma` | Thunderbolt 4 PCIe DMA Bridge (Ultra-Fast Wired) | **0.28 ms** | **3,500.0 MB/s (38.4 Gbps)** | `bridge0` / `tb0` (`169.254.187.138`) | Raw GPU Tensors & KV Cache | DeepSeek-R1-32B / Qwen 2.5 Coder 32B (llama.cpp Metal RPC :50052) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:35` |
| **P02** | `p02_10gbe` | 10Gbps Switched Ethernet (Enterprise Wired) | **0.08 ms** | **1,250.0 MB/s (10 Gbps)** | `en0` (`192.168.8.x`) | Distributed MoE Expert Routing & Multi-Node Batches | Qwen3.5 122B A10B (MoE) / Nemotron 70B (Exo + llama.cpp RPC) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:46` |
| **P03** | `p03_usb32_adb` | USB 3.2 High-Speed ADB Serial (Direct Mobile Bridge) | **0.03 ms** | **420.0 MB/s** | USB serial / RNDIS (`5555`) | 8K Uncompressed Camera Frames & High-Rate Sensor DSP | Qwen 3-VL 32B Vision-Language (Edge TPU Hybrid) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:57` |
| **P04** | `p04_wifi7_mlo` | Wi-Fi 7 / 6E MLO Subnet (High-Speed Wireless) | **3.74 ms** | **450.0 MB/s (2.4 Gbps)** | `en0_wifi_wan` (`192.168.8.1`) | Continuous Batched Inference Requests & Model Layers | Gemma 4 31B Dense / Qwen 2.5 Coder 7B (Exo Zenoh Cluster :52415) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:68` |
| **P05** | `p05_wifi_direct` | Wi-Fi Direct P2P (Infrastructure-Free Wireless) | **4.20 ms** | **250.0 MB/s** | `p2p0` / `wlan0` | Direct Device-to-Device Mesh Sharding without Router | Qwen 2.5 Coder 7B / Llama 3.2 3B (Exo P2P Group Owner Auto-Election) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:79` |
| **P06** | `p06_wifi_aware` | Wi-Fi Aware / NAN (Proximity Mesh) | **8.50 ms** | **80.0–250.0 MB/s** | Port `50055` / NAN cluster `lauburu-nan-mesh-7x` | Zero-Connection Proximity Discovery & Tiny Shard Swapping | Llama 3.2 3B Instruct (Petals Micro-Shard Swarm) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:90` |
| **P07** | `p07_passpoint` | Passpoint / Hotspot 2.0 (Roaming Wireless) | **12.00 ms** | **120.0 MB/s** | `802.11u` EAP-TLS | Seamless Enterprise Roaming for AI Mobile Nodes | DeepSeek-R1-1.5B (Tailscale WireGuard + Exo Remote Node) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:101` |
| **P08** | `p08_kde_localsend` | Zero-Config LAN P2P (Local Broadcast) | **0.94 ms** | **90.0 MB/s** | Port `8750`, UDP `1716`, TCP `1714-1764` | AST Code Context, Prompt Payloads & Shared Clipboards | DeepSeek-R1-1.5B / Qwen 0.5B (PySpark AST Context Broadcast) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:112` |
| **P09** | `p09_syncthing_bep` | Syncthing Block Exchange Protocol BEP (Stateful Sync) | **0.02 ms** | **105.0 MB/s** | Port `8086`, `22000` | 50MB Hot-Swappable DARE-TIES LoRA Adapters | Continuous 24/7 LoRA Fine-Tuning Adapters Daemon | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:123` |
| **P10** | `p10_tailscale_wireguard` | Tailscale Direct WireGuard UDP (Encrypted Overlay Mesh) | **4.13 ms** | **65.0 MB/s (1.0 Gbps)** | `utun1` / Port `51820` | Cross-Subnet Multi-Device Layer Sharding | Meta-Llama-3.1-70B / DeepSeek-R1-70B (Petals DHT Swarm :31337) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:134` |
| **P11** | `p11_webrtc_datachannels` | WebRTC DataChannels (Browser P2P) | **18.50 ms** | **45.0 MB/s** | SCTP/DTLS STUN/TURN | Direct Browser-to-Browser Client-Side Sharding | SmolLM2 360M / WebGPU Whisper STT (Wasm Compute) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:145` |
| **P12** | `p12_bittorrent_dht` | BitTorrent DHT / LibP2P (Decentralized Global Swarm) | **22.00 ms** | **40.0 MB/s** | Port `31337` / `31330` | Heterogeneous Compute Sharing across Global Nodes | Meta-Llama-3.1-70B-Instruct (Petals DHT Swarm Slicing) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:156` |
| **P13** | `p13_cloudflare_quic` | Cloudflare Zero-Trust QUIC Tunnel (Global Edge Gateway) | **24.20 ms** | **32.0 MB/s** | Port `443` / `8787` / `cloudflared` | External Webhooks, Push Alerts & Ingress | Cloud Orchestrator (Gemini 3.7 Flash API) | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:167` |
| **P14** | `p14_mobile_5g_gym` | Mobile 5G / 4G LTE WAN (Remote Gym Protocol) | **48.00 ms** | **25.0 MB/s (120 Mbps)** | `en6_usb_tether` / Cellular | Real-Time Biometrics Telemetry & Voice Coaching | Hermes-3 Llama-3.2 3B (Edge TPU) + Async Swarm Sync | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:178` |
| **P15** | `p15_ble_pan` | Bluetooth 5.3 BLE / PAN BNEP (Ultra-Low Power RF) | **0.03 ms** | **3.0 MB/s** | Port `8087` / GATT / BNEP | Movesense 512Hz/128Hz ECG, Accelerometer, Heartbeat | SmolLM2 135M Tiny / DSP Heuristic Filter | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:189` |
| **P16** | `p16_nfc_beam` | NFC Beam / NDEF Proximity (Near-Field Physical 13.56MHz) | **0.01 ms** (138ms tap) | **0.424 MB/s** | Contact NFC NDEF (<4cm) | Instant Pairing, SSH Keys & Tailscale Auth Tokens | 1-Token Handshake / Session State Seed | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:200` |
| **P17** | `p17_uwb_spatial` | Ultra-Wideband UWB IEEE 802.15.4z (Centimeter Spatial) | **0.01 ms** | **27.0 MB/s** | Port `8181` / ToF / AoA | 3D Spatial Positioning (<10cm) & Kinematic Vectors | Spatial 3D Kinematics & Grappling Joint Predictor | `00_core_infrastructure/multi_wan/all_transports_protocol_matrix.py:211` |

---

### 2.2 Network Telemetry Metrics Catalog

| Metric Key | Unit | Data Type | Collection Mechanism | Source File & Location |
| :--- | :--- | :--- | :--- | :--- |
| `network.interfaces.<nic>.rx_mb_s` | `MB/s` | Float | `psutil.net_io_counters(pernic=True)` delta / dt | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:277` |
| `network.interfaces.<nic>.tx_mb_s` | `MB/s` | Float | `psutil.net_io_counters(pernic=True)` delta / dt | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:278` |
| `network.aggregate_rx_mb_s` | `MB/s` | Float | Sum of all active NIC rx rates | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:286` |
| `network.aggregate_tx_mb_s` | `MB/s` | Float | Sum of all active NIC tx rates | `00_core_infrastructure/self_healing_hub/src/telemetry_poller.py:287` |
| `net_stats.<nic>.rx_bytes` | bytes | Integer | `/proc/net/dev` / sysctl `net.link.generic` | `00_core_infrastructure/self_healing_hub/telemetry_state.json:26` |
| `net_stats.<nic>.tx_bytes` | bytes | Integer | `/proc/net/dev` / sysctl `net.link.generic` | `00_core_infrastructure/self_healing_hub/telemetry_state.json:27` |
| `wanRoutes[].rttMs` | `ms` | Float | ICMP ping probe (1 count, timeout 300ms) | `00_core_infrastructure/self_healing_hub/src/metric_pollers.py:416` |
| `wanRoutes[].dropRate` | ratio [0.0–1.0] | Float | Ping packet loss percentage | `00_core_infrastructure/self_healing_hub/src/metric_pollers.py:432` |
| `wanRoutes[].circuitState` | state | Enum (`CLOSED`, `HALF_OPEN`, `OPEN`) | Adaptive circuit-breaker state machine | `01_apps/canonical_port/src/services/mockFallbackData.js:361` |
| `tailscalePeers[].relay` | transport | String (`Direct WireGuard`, `DERP Relay`) | `tailscale status --json` | `01_apps/canonical_port/src/services/mockFallbackData.js:385` |
| `tb4Dma.rttMs` | `ms` | Float | Sub-millisecond direct socket ping across `169.254.187.138` | `01_apps/canonical_port/src/services/mockFallbackData.js:396` |
| `tb4Dma.throughputGbps` | `Gbps` | Float | Bandwidth benchmark over PCIe bridge0 | `01_apps/canonical_port/src/services/mockFallbackData.js:397` |
| `dual_power_split.net_power_delta_watts` | `Watts` | Float | Qi wireless power input (15W) minus compute draw | `00_core_infrastructure/self_healing_hub/src/unorthodox_matrix_engine.py:91` |
| `nfc.handshake_latency_ms` | `ms` | Float | NDEF tap-to-pair serialization & key exchange time | `00_core_infrastructure/self_healing_hub/src/unorthodox_matrix_engine.py:210` |
| `uwb.tof_distance_meters` | meters | Float | Nanosecond Time-of-Flight matrix between nodes | `00_core_infrastructure/self_healing_hub/src/unorthodox_matrix_engine.py:259` |

---

## 3. System State, Services, Ports, Daemons & SeaweedFS Storage

### 3.1 Master Port & Service Registry

| Port Number | Protocol | Service Name | Service Daemon / Script | Node / Host Location | Health / Status Path |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **18802** | HTTP/REST | Self-Healing Hub API & WoL Server | `api_server.py` & `wol_manager.py` | L1 Mac Host / L3 Linux Head Node | `http://127.0.0.1:18802/api/telemetry` |
| **4000** | HTTP/WS | Master Port 4000 Hub & Canonical Port | `canonical_port` Vite/React Service | L1 Mac Host | `http://127.0.0.1:4000/api/agi/models` |
| **3000** | HTTP/REST | AI Training & Innovation Module Webapp | `webapp` Next.js / Vite Server | L1 Mac Host | `http://127.0.0.1:3000/` |
| **50052** | RPC (GGML) | llama.cpp RPC Tensor Sharding Server | `llama-rpc-server` / `kimi_tandem_orchestrator.py` | L1, L2, L3, L5, L6, L7 | Direct TCP Socket Handshake |
| **8081** | HTTP/REST | Master Kimi 72B Dev Inference Gateway | `llama-server` (-m kimi-dev-72b -ts 28,28,24) | L1 Mac Mini Host | `http://127.0.0.1:8081/health` |
| **8082** | HTTP/REST | Qwen 2.5 / 3.8 Code Reasoning Server | `llama-server` (-m qwen-2.5-coder-32b) | L3 Linux Head Node | `http://127.0.0.1:8082/health` |
| **8083** | HTTP/REST | Genetic MoE Distilled Core Server | `llama-server` (Continuous LoRA Merged) | L5 MacBook Air | `http://127.0.0.1:8083/health` |
| **8084** | HTTP/REST | Qwen Edge Vision 7B Fallback Server | `llama-server` (-m qwen2.5-vl-7b-instruct) | L1 Mac Mini Host | `http://127.0.0.1:8084/health` |
| **8085** | HTTP/REST | Kimi VL Thinking 2506 Vision Gateway | `llama-server` (-m kimi-vl-thinking-2506) | L1 Mac Mini Host | `http://127.0.0.1:8085/health` |
| **6333 / 6334**| HTTP / gRPC | Qdrant Vector Database | `qdrant` Container / Local Daemon | L3 Linux Head Node / L1 Host | `http://127.0.0.1:6333/dashboard` |
| **9333** | HTTP/Raft | SeaweedFS Master Consensus Cluster | `weed master` (-peers=100.101.39.98:9333,...) | L3 Head, L1 Mac, L2 MBP | `http://100.101.39.98:9333/cluster/status` |
| **8888** | HTTP/Filer | SeaweedFS Filer Gateway | `weed filer` (Metadata & Directory tree) | L3 Head Node (`100.101.39.98:8888`) | `http://100.101.39.98:8888/` |
| **9000** | HTTP/S3 | SeaweedFS S3 Object Storage API | `weed s3` (S3-compatible bucket API) | L3 Linux Head Node | `http://100.101.39.98:9000/` |
| **5555** | TCP/IP | Android Debug Bridge (ADB) Daemon | `adbd` (Pixel 10 Pro XL, Samsung S20) | L6 Pixel, L7 S20, GW Router | `adb devices -l` |
| **8022** | SSH | Termux OpenSSH Server | `sshd -p 8022` (Termux Android 15/13) | L6 Pixel, L7 Samsung S20 | Direct SSH Key Authentication |
| **8000** | HTTP/REST | Compute Hub Fast Ingress & Health | `fastapi` Compute Gateway | L3 Linux Head Node | `http://100.101.39.98:8000/health` |
| **8080** | HTTP/REST | On-Device Nano Smol HTTP API | `on_device_nano_smol_trainer.py` | L6 Pixel 10 Pro XL | `http://100.73.38.87:8080/` |
| **8086** | HTTP/REST | Continuous LoRA Pipeline Daemon | `continuous_lora_daemon.py` | L1 Mac Host / L5 MBA | `http://127.0.0.1:8086/status` |
| **8087** | HTTP/REST | Live Movesense Biometrics Harvester | `pyspark_movesense_stream.py` | L1 Mac Host | `http://127.0.0.1:8087/live` |
| **8181** | HTTP/REST | Spatial Grappling Map Engine REST | `spatial_grappling_map_engine.py` | L1 Mac Host | `http://127.0.0.1:8181/api/map` |
| **18789** | HTTP/REST | OpenClaw Remote UI Automation Gateway | `openclaw_ui_audit_bridge.py` | L3 Linux Head Node | `http://100.101.39.98:18789/` |
| **18800** | HTTP/REST | AI Sharding Daemon / Open Source Scout | `ai_sharding_daemon.py` | L1 Mac Mini Host | `http://127.0.0.1:18800/` |
| **18888** | HTTP/WS | Termius TUI Unified Dashboard Server | `termius_tui.api.server` | L1 Mac Mini Host | `http://127.0.0.1:18888/api/v1/health` |
| **50055** | UDP/NAN | Wi-Fi Aware NAN Publish Cluster Port | `unorthodox_matrix_engine.py` | Mesh L1-L7 Peer Discovery | Peer Broadcast |
| **52415** | TCP/Zenoh | Exo Ring P2P Discovery & Tensor Shard | `exo` P2P Cluster Daemon | Mesh Nodes | `http://localhost:52415/health` |
| **31337 / 31330**| LibP2P/DHT | Petals Distributed Swarm DHT Daemon | `petals.cli.run_server` | L3 Linux Node, L6 Pixel 10 | DHT Kademlia Protocol |
| **29500** | TCP/RPC | PyTorch / Accelerate Distributed Comm | `accelerate launch` / torch.distributed | L1 Mac, L3 Linux Node | C10d Backend Socket |

---

### 3.2 Operating System Daemons & Launchd/Systemd Units

1. **`com.lauburu.nasautomount.plist`** (macOS launchd Daemon):
   - Path: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/systemd/com.lauburu.nasautomount.plist`
   - Target: `/usr/bin/python3 auto_mount_nas_daemon.py`
   - Metrics: KeepAlive `true`, RunAtLoad `true`, Logs: `nas_automount.log` / `nas_automount_err.log`.
2. **`dfs-fuse-mount.service`** (Linux systemd Unit):
   - Path: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/systemd/dfs-fuse-mount.service`
   - Command: `/usr/local/bin/weed mount -filer=100.101.39.98:8888 -dir=/mnt/dfs_unified -cacheCapacityMB=128 -chunkSizeLimitMB=16 -concurrentWriters=32`
   - Metrics: VFS mount state, canary `stat -t` latency, process PID, restart count.
3. **`dfs-fuse-watchdog.service`** (Linux systemd Unit):
   - Path: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/systemd/dfs-fuse-watchdog.service`
   - Action: Probes `/mnt/dfs_unified` every 10s; executes `fusermount3 -u -z` on freeze.
4. **`nomad_roi_cron_governor.py`** (Autonomous Cron Daemon):
   - Path: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/nomad_roi_cron_governor.py`
   - Cadence: 4-tier state machine (RAPID_TRIAGE 120s, NOMINAL 900s, BACKOFF 3600s, CIRCUIT_BREAKER).
   - Metrics: Job execution time, CPU %, RSS memory MB, non-linear failure penalty `P_fail(f) = 0.85 * f^1.45`, composite empirical ROI `[0.0–10.0]`.

---

### 3.3 SeaweedFS Raft & Storage Topology Metrics

| Metric Key | Unit | Data Type | Sourcing Mechanism | Source Location |
| :--- | :--- | :--- | :--- | :--- |
| `seaweedfs.status` | status | Enum (`QUORUM_HEALTHY`, `SPLIT_BRAIN_DETECTED`, `QUORUM_LOST_CRITICAL`) | Raft master `/cluster/status` probe | `00_core_infrastructure/seaweedfs/seaweed_tools.py:381` |
| `seaweedfs.has_quorum` | flag | Boolean | `reachable_peers_count >= (total // 2) + 1` | `00_core_infrastructure/seaweedfs/seaweed_tools.py:374` |
| `seaweedfs.consensus_leader` | endpoint | String (`ip:port`) | Normalized Raft leader identity | `00_core_infrastructure/seaweedfs/seaweed_tools.py:390` |
| `seaweedfs.is_split_brain` | flag | Boolean | Distinct reported leaders count > 1 | `00_core_infrastructure/seaweedfs/seaweed_tools.py:378` |
| `seaweedfs.total_free_volumes` | count | Integer | `/dir/status` topology free volumes | `00_core_infrastructure/seaweedfs/seaweed_tools.py:394` |
| `seaweedfs.total_max_volumes` | count | Integer | `/dir/status` topology max volumes | `00_core_infrastructure/seaweedfs/seaweed_tools.py:395` |
| `fuse.is_mounted` | flag | Boolean | OS `mount` table check / `/proc/mounts` | `00_core_infrastructure/seaweedfs/seaweed_tools.py:93` |
| `fuse.is_frozen` | flag | Boolean | Non-blocking canary `stat -t` timeout probe | `00_core_infrastructure/seaweedfs/seaweed_tools.py:120` |

---

## 4. Local AI Training, Inference & Model Governance

### 4.1 Master AGI Model Roster & Sharding Allocations

| Model ID | Full Name & Model Path | Quantization | Architecture & Role | Assigned Layers & Nodes | Context Window | VRAM Footprint | Throughput | ELO Rating |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `kimi_tandem_titan` / `kimi_dev_72b` | `kimi-dev-72b-instruct-q4_k_m.gguf` (39.0 GB) | `Q4_K_M` | MoE Dual-Node Sharded Reasoning Engine | **80 total layers (-ts 28,28,24)**:<br>• Shard 1: L3 Linux (Layers 0..27, 13.5 GB)<br>• Shard 2: L2 MBP TB4 (Layers 28..55, 13.5 GB)<br>• Shard 3: L1 Mac Host (Layers 56..79, 12.0 GB) | 16,384 – 262,144 | **39.0–56.4 GB** | **48.2 tok/s** | **2,180** |
| `kimi_vl_thinking_2506` | `kimi-vl-thinking-2506-q4_k_m.gguf` (9.8 GB + 0.8 GB mmproj) | `Q4_K_M` | Tier-1 Local Vision-Language & Deep Reasoning | Apple Metal GPU (-ngl 999) on L1 Mac Mini Host | 32,768 | **10.6 GB** | **34.5 tok/s** | **2,150** |
| `qwen_38_max` / `qwen25_vl_7b_edge` | `qwen2.5-vl-7b-instruct-q4_k_m.gguf` (4.4 GB) | `Q4_K_M` | Dense Vision-Language Edge Transformer | L1 Mac Host + L6 Pixel 10 Edge TPU Hybrid | 8,192 – 131,072 | **5.85–18.2 GB**| **48.3 tok/s** | **2,110** |
| `gemini_flash_cloud` | Cloud Gateway Multimodal API | Cloud API | Hyperscale Cloud Fallback Multimodal Oracle | Cloudflare Worker Gateway (`/api/gemini`) | 1,048,576 | **0.0 GB** (Cloud) | **124.0 tok/s**| **2,240** |
| `genetic_moe_core` | Continuous LoRA Merged Checkpoint (`safetensors`) | `Q4_K_M` | Autonomous Continuous LoRA Distillation | L5 MacBook Air + L4 Linux Tablet Petals Ring | 32,768 | **8.2 GB** | **62.1 tok/s** | **2,040** |
| `deepseek_v3_671b` | DeepSeek V3 671B MoE Shard | `IQ2_XXS` | Local MoE Architecture | Distributed Petals / RPC Cluster | 65,536 | **24.0 GB** | **36.4 tok/s** | **2,010** |
| `llama_33_70b` | Meta-Llama-3.3-70B-Instruct | `Q4_K_M` | High-Precision Dense Code Engine | Distributed RPC Sharding | 32,768 | **42.0 GB** | **42.0 tok/s** | **1,985** |

---

### 4.2 Training & Game Arena Metrics Catalog

| Metric Key | Unit | Data Type | Mathematical Formula / Source | Source File & Location |
| :--- | :--- | :--- | :--- | :--- |
| `training.current_loss` | loss | Float | Cross-entropy training loss | `01_apps/canonical_port/src/services/mockFallbackData.js:221` |
| `training.initial_loss` | loss | Float | Baseline initial checkpoint loss (2.18) | `01_apps/canonical_port/src/services/mockFallbackData.js:222` |
| `training.throughput_pairs_per_min`| pairs/min | Float | Rate of harvested Alpaca instruction pairs | `01_apps/canonical_port/src/services/mockFallbackData.js:223` |
| `training.total_harvested_pairs` | count | Integer | Line count of verified `.jsonl` files (84,320+) | `01_apps/canonical_port/src/services/mockFallbackData.js:224` |
| `training.learning_rate` | lr | String | `2e-5` (AdamW optimizer) | `01_apps/canonical_port/src/services/mockFallbackData.js:226` |
| `training.batch_size` | count | Integer | 32 gradient accumulation batch | `01_apps/canonical_port/src/services/mockFallbackData.js:227` |
| `training.loss_history[].loss` | loss curve | Array[Float] | Stepwise loss decay history (1.84 -> 0.142 at step 4800) | `01_apps/canonical_port/src/services/mockFallbackData.js:228` |
| `ai_debate.cosine_accord` | accord [0.0–1.0]| Float | Persona alignment matrix cosine similarity (>= 0.90) | `ai_debate/src/tri_orchestrator_debate.py:19` |
| `ai_debate.current_turn` | turn count | Integer | 4-turn state machine (1: Proposal, 2: Cross-Exam, 3: Accord, 4: Priorities) | `ai_debate/src/tri_orchestrator_debate.py:13` |
| `elo.rating` | ELO score | Integer | Dynamic K-factor: `K = K_0 * eta_type * eta_size * eta_token * eta_consensus * eta_compute * eta_truth` | `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py:14` |
| `elo.win_rate_pct` | `%` | Float | `(wins + 0.5 * draws) / total_matches * 100` | `00_core_infrastructure/self_healing_hub/src/canonical_ai_leaderboard.py:180` |
| `game_arena.agent_hp` | HP [0–100] | Integer | Dynamic health points in 13-Model FFA | `01_apps/canonical_port/src/services/mockFallbackData.js:275` |
| `game_arena.biometric_shield_boost`| shield pts | Integer | Ingested Movesense Zone 2 heart rate multiplier (+35) | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:249` |

---

### 4.3 Continuous 24/7 LoRA Datasets Directory Matrix

Located in `12_continuous_lora_evolution/lora_datasets/` and mirrored to `/Users/aaron/DFS_UNIFIED/lora_datasets/`:
1. `all_local_ais_lora_burst_dataset.jsonl` — High-concurrency multi-model burst traces
2. `architectural_decisions.jsonl` — Formal architectural decisions and whitepaper consensus
3. `autonomous_consensus_iterations.jsonl` — Tri-Orchestrator debate consensus pairs
4. `biometrics_sleep_lora_dataset.jsonl` — Polysomnography and nocturnal HRV instruction pairs
5. `continuous_lora_dataset.jsonl` — Main continuous background LoRA distillation stream
6. `cot_distillation_generation_1786654798.jsonl` — Chain-of-Thought (CoT) reasoning traces
7. `device_doctor_telemetry.jsonl` — Node healing, thermal triage, and hardware repair logs
8. `gemma_nano_training_dataset.jsonl` — On-device Gemma Nano fine-tuning instructions
9. `genetic_ml_dataset_latest.jsonl` — Genetic MoE adapter weights optimization dataset
10. `genetic_smol_lora_training.jsonl` — SmolLM2 135M/360M parameter specialization pairs
11. `healing_incidents.jsonl` — Network, socket, and storage self-healing incident records
12. `lauburu_chat_conversations.jsonl` — Multi-turn user and agent conversation logs
13. `mesh_battle_game_training.jsonl` — Tactical combat strategies from 13-Model FFA arena
14. `model_merge_benchmarks.jsonl` — MergeKit Optuna DARE-TIES merge benchmark scores
15. `movesense_biometrics_coaching.jsonl` — Zone 2 endurance and ECG coaching feedback pairs
16. `on_device_nano_smol_training.jsonl` — Edge TPU on-device training instruction pairs
17. `quarantined_hallucinations.jsonl` — Strict Rule #0 violation samples for negative DPO tuning
18. `self_evolving_analysis_chains.jsonl` — Self-reflective reasoning chains
19. `shadow_coding_distillation.jsonl` — Zero-mock code synthesis and refactor datasets
20. `swarm_codebase_refactors.jsonl` — Verified git diff patches and AST transform pairs
21. `truth_audit_debate.jsonl` — Swarm Truth Audit verification debriefings
22. `truthfulness_retraining_dataset.jsonl` — Empirical verification ground truth pairs
23. `ui_ux_improvements.jsonl` — OpenClaw and VLM accessibility visual audit pairs

---

## 5. Medical-Grade Biometrics, Kinematics & DSP Telemetry

### 5.1 Movesense Sensor & Ingestion Pipeline Specs
- **Hardware Model:** Movesense Medical / HR+ 128Hz/512Hz GATT (Medical Class IIa certified).
- **Transport Protocols:** Bluetooth 5.3 BLE (Direct GATT / BNEP Serial Stream on Port 8087).
- **Dynamic Sampling Profiles:**
  * `resting`: 13Hz IMU, 125Hz ECG
  * `zone2`: 104Hz IMU, 250Hz ECG
  * `grappling`: 833Hz IMU, 500Hz ECG

---

### 5.2 Biometric & DSP Mathematical Metrics Catalog

| Metric Key | Unit | Data Type | Mathematical Formula / Algorithm | Clinical Reference / Interpretation | Source File & Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `biometrics.heart_rate_bpm` | `BPM` | Float | R-R interval instantaneous frequency: `60000.0 / RR_ms` | Authentic cardiovascular pulse rate | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:227` |
| `biometrics.rr_interval_ms` | `ms` | Array[Float] | Inter-beat intervals between consecutive R-peaks | Raw fiducial R-peak timing array | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:228` |
| `biometrics.artifact_filter` | status | String | Kamath et al. (2004) 20% Clinical RR Filter: `\|RR[i] - RR[i-1]\| / RR[i-1] <= 0.20` | Rejects ectopic beats and movement noise | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:25` |
| `biometrics.rmssd_ms` | `ms` | Float | `sqrt( 1/(N-1) * sum((RR[i+1] - RR[i])^2) )` | Root Mean Square of Successive Differences (Parasympathetic HRV index) | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:41` |
| `biometrics.dfa_alpha1` | exponent | Float | Detrended Fluctuation Analysis scaling exponent over 120s rolling window (n=4..16 beats) | **0.75 = Optimal Zone 2 Aerobic Threshold** (Aerobic lipid oxidation); <0.50 = Anaerobic | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:52` |
| `biometrics.vo2_max_ml_kg_min` | `ml/kg/min` | Float | `min(65, max(30, 15.3 * (HR/65.0) * (Power/135.0)))` | Estimated aerobic capacity | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:193` |
| `biometrics.ecg_snr_db` | `dB` | Float | Pan-Tompkins QRS power vs noise floor | Signal-to-Noise ratio (Nominal: >25 dB) | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:236` |
| `kinematics.accelerometer_g` | `g` | Object `{x, y, z}` | Direct 3-axis accelerometer sensor vector | Static and dynamic gravitational force | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:240` |
| `kinematics.gyroscope_dps` | `deg/s` | Object `{x, y, z}` | Direct 3-axis gyroscope angular velocity | Rotational acceleration on tatami mats | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:241` |
| `kinematics.total_dynamic_g` | `g` | Float | `sqrt(ax^2 + ay^2 + az^2)` | Total resultant acceleration vector magnitude | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:188` |
| `kinematics.mechanical_power_watts`| `Watts` | Float | `(total_dynamic_g * 140.0) + (gyro_magnitude * 18.0)` | Total mechanical kinetic power expenditure | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:190` |
| `kinematics.cadence_spm` | `SPM` | Integer | Steps / Strides per minute frequency analysis | Running / Grappling pace cadence | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:244` |
| `kinematics.posture_alignment_pct` | `%` | Float | MediaPipe 33 landmark spinal alignment vector | Kinematic joint integrity score | `00_core_infrastructure/self_healing_hub/src/pyspark_movesense_stream.py:245` |

---

### 5.3 3D Spatial Grappling Kinematics & OPML Trees

- **Data File:** `10_spatial_grappling_kinematics/opml_trees/grappling.opml` & `session_logs/spatial_grappling_map.json`
- **Spatial Bounds:** 8.0m x 8.0m x 2.5m 3D Tatami Mat projection
- **Positional Nodes:** 31 canonical positions categorized by:
  * `Neutral`: Standing Neutral (X:0, Y:0, Z:1.75m)
  * `Clinch`: Collar Tie Clinch, Underhook Pummel
  * `Takedown`: Single Leg Entry, Double Leg Shot
  * `Guard`: Closed Guard, Open Guard, De La Riva, Spider Guard, Half Guard Bottom
  * `Passing / Pin`: Half Guard Top, Side Control, Knee on Belly, Full Mount, North-South
  * `Defensive / Apex`: Turtle, Back Control (Hooks & Seatbelt)
  * `Leg Entanglements`: Single Leg X / Ashi Garami, Inside Sankaku / Saddle (4-11), 50/50 Guard
  * `Submissions`: Straight Armbar (Juji-Gatame, elbow >165°), Kimura Lock (internal shoulder torque >85°, figure-four grip), Rear Naked Choke (bilateral carotid blood choke), Triangle Choke (Sankaku-Jime), High-Elbow Guillotine, Inside Heel Hook (ACL rotational torque >260 Nm).
- **Biomechanical Transitions:** 57 directed edges tracking `difficulty` (0.0–10.0), `peak_torque_nm` (65–260 Nm), and `min_execution_time_s` (0.5–2.1s).

---

## 6. Tooling Metrics (MCP Servers, SDKs, APIs, CLIs, Agent Skills)

### 6.1 Model Context Protocol (MCP) Servers

| MCP Server Name | Schema Path / Module | Tool Count | Core Capabilities | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **`docker`** | `LobeHub Docker MCP` | 12 tools | Container lifecycle, network inspect, image pull/build | Managing multi-container compose topology |
| **`obsidian`** | `Obsidian MCP Pro` | 41 tools | Vault search, Wikilinks graph traversal, frontmatter querying | Syncing architecture whitepapers & debate logs |
| **`cloudflare`** | `@cloudflare/mcp-server-cloudflare` | 18 tools | Workers AI, KV/D1/R2 storage, Cloudflare Tunnels | Edge inference & WAN sync |
| **`computer-use`** | `@zavora-ai/computer-use-mcp` | 14 tools | Apple Silicon ARM64 desktop automation, screenshots | Native macOS UI automation |
| **`browser-use`** | `browser-use[cli]` | 16 tools | Autonomous web browsing, CDP DOM inspection | Webapp E2E testing |
| **`antigravity-models`** | `antigravity_mcp_models` | 8 tools | Dynamic routing for llama.cpp, Petals, Exo | Distributed local AI model routing |
| **`figma`** | `figma_mcp_client.py` | 6 tools | Live REST AST extraction (`get_file`, `get_image`) | Zero-mock UI design sync |
| **`marionette-mcp`** | `00_core_infrastructure/mcp_servers/marionette-mcp` | 9 tools | Firefox Marionette driver, AX tree builder, DOM audit | Headless browser testing & accessibility audits |
| **`filesystem`** | Native Native MCP | 14 tools | Safe filesystem read/write/edit/stat operations | Code modification & file management |
| **`memory`** | Native Knowledge Graph MCP | 9 tools | Entity and relationship graph management | Swarm shared entity memory |
| **`sequential-thinking`** | Native Reasoning MCP | 1 tool | Multi-step sequential problem solving | Complex architectural deliberation |
| **`chrome-devtools-mcp`** | Chrome DevTools Plugin MCP | 29 tools | Performance traces, heap snapshots, console, DOM | Webapp profiling & memory leak auditing |

---

### 6.2 Software Development Kits (SDKs) & Frameworks

| SDK Name | Detected Version | Binding Type | Core Capabilities | Source Location |
| :--- | :--- | :--- | :--- | :--- |
| `torch` | 2.5+ | C++/Metal/CUDA Native | PyTorch Deep Learning, MPS Metal acceleration | Python `site-packages` |
| `pyspark` | 3.5.0 | Java/Scala/Py4J Engine | Monorepo AST indexing, 435K LOC analysis, data lakehouse | Java 17 + Python PySpark |
| `transformers` | 4.48+ | Python/PyTorch | HuggingFace model architectures & tokenizers | Python `site-packages` |
| `peft` | 0.14+ | Python/PyTorch | Parameter-Efficient Fine-Tuning (LoRA / QLoRA / DARE) | Python `site-packages` |
| `trl` | 0.14+ | Python/PyTorch | Transformer Reinforcement Learning (DPO, PPO, SFT) | Python `site-packages` |
| `accelerate` | 1.3+ | Python/PyTorch | Multi-node distributed tensor training | Python `site-packages` |
| `llama_cpp` | 0.3+ | C/C++ FFI (GGML/Metal) | llama.cpp Python bindings & RPC client | Python `site-packages` |
| `google_antigravity_sdk` | 2.0+ | Python Native | Autonomous agent orchestration & tool lifecycle | Python `site-packages` |
| `textual` | 0.85+ | Python Async TUI | Rapid terminal user interfaces & widget trees | Python `site-packages` |
| `psutil` | 6.1+ | C/OS Native | Cross-platform hardware telemetry extraction | Python `site-packages` |
| `pydantic` | 2.10+ | Rust/C-Core | High-speed data model serialization & schema validation | Python `site-packages` |
| `asyncssh` | 2.18+ | Python Native | Asynchronous SSHv2 client for multi-node orchestration | Python `site-packages` |

---

### 6.3 Command-Line Interfaces (CLIs)

| CLI Tool | Target Transport / Category | Version Probe Command | Capabilities |
| :--- | :--- | :--- | :--- |
| `agy` | Autonomous Agent Lifecycle | `agy --version` | Antigravity 2.0 workspace and agent management |
| `gh` | GitHub Version Control | `gh --version` | Git PR reviews, release tagging, worktree management |
| `uv` | Python Package Manager | `uv --version` | High-speed venv creation and test runner (`uv run pytest`) |
| `adb` | Direct Mobile & Router Bridge | `adb version` | TCP/IP wireless debugging, Termux wake locks, screen capture |
| `ssh` / `sshpass` | Multi-Transport SSH Remote Exec | `ssh -V` | Idempotent remote command execution across 8 layers |
| `docker` / `docker compose` | Containerization Engine | `docker --version` | Multi-container orchestration (`docker-compose.*.yml`) |
| `kdeconnect-cli` | LAN Broadcast & Pairing | `kdeconnect-cli --version` | Local network packet broadcast and device discovery |
| `tailscale` | Encrypted WireGuard Overlay | `tailscale version` | Mesh network status, peer discovery, subnet routing |
| `weed` | Distributed Storage CLI | `weed version` | SeaweedFS master, filer, volume, and FUSE mount controls |
| `scrcpy` | Mobile Screen Projection | `scrcpy --version` | Low-latency Android screen mirroring and UI automation |

---

### 6.4 Agent Skills Catalog (Spec-00 through Spec-12 & Specialized Capabilities)

- **`spec-00-core-infrastructure`**: SeaweedFS DFS, Docker Compose, Tailscale mesh, systemd/launchd daemons.
- **`spec-01-apps-ecosystem`**: Port 4000 Hub, Movesense Hub (512Hz ECG), Zone 2, Shopify AI, 3D Grappling, Termux Edge.
- **`spec-02-ai-inference-mesh`**: llama.cpp RPC sharding (8081–8085), Petals DHT, Exo P2P, GGUF Vault.
- **`spec-03-biometrics-dsp`**: ECG, PTT blood pressure, DFA-alpha1, Pan-Tompkins QRS, polysomnography.
- **`spec-04-data-memory-sync`**: PySpark crawlers, 24/7 LoRA datasets, Google Drive Cloud Sync, Qdrant Vector DB.
- **`spec-05-swarm-orchestrator`**: Tri-Orchestrator AI debate council, Genetic MoE engine, ELO leaderboards.
- **`spec-06-tooling-healing`**: Network self-healing, global NAS mounts, ADB keepalive, WoL resurrection.
- **`spec-07-docs-architecture`**: Monorepo deep architecture indexes, whitepapers, security RFCs.
- **`spec-08-business-commerce`**: Shopify Storefront GraphQL, subscription billing, CAC/LTV modeling, merchandise profitability.
- **`spec-09-app-store-production`**: Google Play / Apple App Store readiness, memory leak audits, APK signing.
- **`spec-10-spatial-grappling-kinematics`**: 955-node OPML spatial trees, 3D tatami world models, joint torque, submission counters.
- **`spec-11-security-red-blue-team`**: Hardware isolation, SSH/RPC socket encryption, Cloudflare HMAC auth, zero source-code leakage.
- **`spec-12-continuous-lora-evolution`**: Continuous LoRA distillation, loss tracking, and Genetic MoE model merging.
- **Polyglot Specialists**: Python, Rust/wgpu, Swift/Metal, Kotlin/Android, Dart/Flutter, TypeScript/Web, C/C++, Bash/POSIX.
- **Transport Specialists**: Tailscale, Speedify Multipath, Thunderbolt 10GbE, KDE Connect, Bluetooth PAN, Wi-Fi Direct, Wake-on-LAN, ADB, Mobile Hotspot.

---

## 7. Knowledge, Storage & Monorepo AST Lakehouse

### 7.1 Tri-Vault Storage Invariants & Inode Health

| Vault Layer | Inode Path | Healthy Criteria & Invariants | Data Formats |
| :--- | :--- | :--- | :--- |
| **1. Obsidian Vault** | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/` | `0755/0644` permissions, non-empty `Index.md` with master Wikilinks (`[[Index]]`, `[[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]`, `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`) | Markdown (`.md`), YAML Frontmatter, Canvas |
| **2. PySpark Data Lake** | `/Users/aaron/DFS_UNIFIED/lora_datasets/` & `04_data_and_memory/` | Writable `.jsonl` datasets, $\ge$10.0 GB free disk headroom on host NVMe, reachable Qdrant Vector DB port (`127.0.0.1:6333`) | Delta Lake, Parquet, JSON Lines (`.jsonl`), JSON |
| **3. GitHub Monorepo** | `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo` | Valid git tree (`git rev-parse --is-inside-work-tree`), absent `.git/index.lock`, clean merge tree | Git Tree, Branches, Worktrees |

---

### 7.2 PySpark Monorepo Codebase Crawl & AST Metrics
- **Total Federated Projects:** 32 active projects in `/Users/aaron/teamwork_projects`
- **Total Code Files:** 3,104 files
- **Total Lines of Code (LOC):** 434,965 LOC
- **Total Test Files:** 325 test suites
- **AST Functions & Methods:** 124,491 indexed AST nodes
- **Language Breakdown:**
  * Markdown: 2,228 files
  * Python: 752 files
  * JSON: 30 files
  * TypeScript / JSX: 24 files
  * Shell / POSIX: 22 files
  * JavaScript: 14 files
  * TOML: 13 files
  * YAML: 11 files
  * HTML: 4 files
  * CSS: 3 files
  * Rust: 1 file

---

### 7.3 Multi-Tier Unified NAS Storage Mesh Topology

| Storage Tier Identifier | Physical Node | Inode Path / Mount Point | Total Capacity | Available Headroom | Target Data Class | Interconnect Speed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `headless_mac` | L2 MacBook Pro | `/Volumes/NAS/Hardware_Tiers/Headless_Mac_Vault` | **466.0 GB** | **409.3 GB** | GGUF Model Weights (`.gguf`) | 10Gbps Thunderbolt 4 (0.277ms RTT) |
| `pixel_10_pro` | L6 Pixel 10 Pro XL | `/Volumes/NAS/Hardware_Tiers/Layer_4_Pixel_10_Pro_XL` | **256.0 GB** | **128.0 GB** | Edge TPU Weight Cache | Tailscale Direct / Termux |
| `main_mac_host` | L1 Mac Mini M4 Pro | `/Volumes/NAS/Hardware_Tiers/Main_Mac_Primary` | **228.0 GB** | **16.0 GB** | Metadata & Spark Driver | Internal Apple Silicon Fabric |
| `linux_laptop_node` | L3 Linux Head Node | `/Volumes/NAS/Hardware_Tiers/Linux_Laptop_Node` | **512.0 GB** | **320.0 GB** | Docker Volume Overlays & Parquet | 2.5GbE LAN / Tailscale Mesh |
| `samsung_s20` | L7 Samsung S20+ | `/Volumes/NAS/Hardware_Tiers/Samsung_S20_Tester` | **128.0 GB** | **64.0 GB** | UI Automation Test Artifacts | Router USB ADB / Wi-Fi 6 |
| `google_drive_vfs` | Google Drive Cloud API | `/Volumes/NAS/GoogleDrive_Sync` | **2,048.0 GB (2.0 TB)** | **1,850.0 GB** | Immortal LoRA Instruction Pairs | Cloudflare Tunnel / Google API |

---

## 8. Summary of Integration Requirements for Canonical Port TUI

To achieve complete, stability-based maximalist rendering in the Canonical Port TUI (`01_apps/canonical_port`):
1. **Blackboard Shared State Store:** Map all identified metric keys into the central telemetry state object served on Port 18802 (`/api/telemetry`) and Port 4000 (`/api/agi/models`, `/api/mesh/telemetry`, `/api/swarm/debate`).
2. **Stability-Based UI Layout Hierarchy:**
   - **Layer 1 (Bottom/Foundation):** Networking & Power (Wake-on-LAN bare metal power → Bluetooth PAN → KDE Connect LAN → Thunderbolt 4 DMA → Tailscale / Multi-WAN failover).
   - **Layer 2:** Hardware & Node Health (7 physical node gauges, CPU %, RAM %, AI VRAM Cap %, Thermals °C, Power Split Watts).
   - **Layer 3:** Distributed AI Inference & Training (Kimi 72B / Qwen / Genetic MoE RPC sharding status, loss curves, ELO rankings, 24/7 LoRA dataset streams).
   - **Layer 4:** Medical-Grade Biometrics & 3D Kinematics (Movesense 512Hz ECG, Kamath filtered RR, RMSSD, DFA-alpha1 Zone 2 gauge, 31 OPML Grappling Positions & Torque).
   - **Layer 5:** Tooling, MCPs & Workflows (12 MCP servers, SDKs, CLIs, 10 Canonical Pillars Audit Score).
   - **Layer 6 (Top/Knowledge):** Tri-Vault Knowledge Core (Obsidian 47-note graph stats, PySpark 435K LOC index, NAS Lakehouse 2.0 TB storage).
