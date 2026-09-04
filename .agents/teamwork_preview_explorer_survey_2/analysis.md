# Comprehensive Codebase Survey & Gap Analysis: RAM Governor, 7-Layer Mesh Sharding & Edge Hardware Offloading

**Agent:** Explorer 2 (RAM Governor & Mesh Specialist)  
**Date:** 2026-08-31T03:46:00Z  
**Monorepo Root:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_2`  
**Parent Agent:** `f0584c86-8cae-46d4-9172-b35bcf84eb11`  
**Requirements Addressed:** R3 (Real-Time Dynamic RAM & VRAM Governor), R5 (7-Layer Mesh Sharding & Hardware Offloading), E3 (Edge-Accelerated Dataset Tokenization)

---

## 1. Executive Summary

An exhaustive empirical survey was conducted across the `Lauburu-Monorepo` codebase (specifically inspecting `00_core_infrastructure`, `02_ai_models_and_inference`, `04_data_and_memory`, `06_scripts_and_tooling`, and network routing layers).

The monorepo contains a mature foundation for distributed heterogeneous compute spanning 108.0 GB Physical RAM and 82.8 GB Pooled Usable AI VRAM across 7 physical hardware layers and the OpenWrt router gateway. However, critical gaps exist in real-time cross-framework coordination:
1. **R3 (RAM Governor):** Memory monitoring scripts are currently fragmented across multiple daemons with disparate threshold configs (e.g., 88% in `dynamic_ram_governor.py` vs 85% in `ram_autoscaler_governor.py`). VRAM / Metal MPS cache purging (`torch.mps.empty_cache()`), active background training process throttling (SIGSTOP/SIGCONT / Ray task pausing), and dynamic layer-offloading triggers over the 10Gbps Thunderbolt 4 bridge are not yet wired into a unified closed-loop governor.
2. **R5 (7-Layer Mesh Sharding):** The 4 sharding adapters (`LlamaCppAdapter`, `PetalsAdapter`, `ExoAdapter`, `AccelerateAdapter`) and `prima.cpp` PRP proxy (`prima_ring_adapter.py`) exist with test coverage, but live dynamic re-sharding (migrating transformer layers on-the-fly when host RAM approaches 85%) and multi-node Ray auto-clustering (L3 Linux + L5 MacBook Air) require automated runtime binding.
3. **E3 (Edge-Accelerated Tokenization):** While non-root Termux execution, wake-locks (`termux-wake-lock`), and thermal monitoring exist on Pixel 10 Pro XL (`pixel_termux_node.py`) and Samsung S20+ (`s20_watchdog.py`), dataset tokenization and synthetic question generation are still executed on the Host Mac CPU rather than being distributed to Tensor G5 TPU / Exynos edge workers.

---

## 2. Deep-Dive Subsystem Architecture & Catalog

### 2.1 RAM & VRAM Governance Subsystem (R3)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DYNAMIC RAM & VRAM GOVERNOR                              │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Host (L1 Mac Mini M4 Pro - 24GB)                                                         │
│  ├─ Tier 1: SAFE (<65%)         → 100% throughput, full 4096 context                     │
│  ├─ Tier 2: CAUTION (65-75%)    → 80% throttle factor, proactive gc.collect()            │
│  ├─ Tier 3: PROTECTIVE (75-85%) → 50% throttle factor, context reduced to 2048,           │
│  │                                torch.mps.empty_cache(), am trim-caches (Android)      │
│  └─ Tier 4: CRITICAL (>85.0%)   → 0% throttle factor (pause training), drop_caches (Linux)│
│                                    sudo -n purge, offload top layers to L2 over TB4 DMA   │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Peripheral Ceilings & Buffers:                                                           │
│  • L2 MacBook Pro: 90% ceiling (14.0 GB usable / 1.6 GB reserve)                         │
│  • L3 Linux Head Node: 80% ceiling (12.8 GB usable / 3.2 GB reserve)                     │
│  • L4 Linux Tablet: 75% ceiling (6.0 GB usable / 2.0 GB reserve)                         │
│  • L5 MacBook Air: 90% ceiling (14.0 GB usable / 1.6 GB reserve)                         │
│  • L6 Pixel 10 Pro XL: 85% ceiling (12.5 GB usable / 2.4 GB reserve, 41°C cutoff)       │
│  • L7 Samsung S20+: 75% ceiling (9.0 GB usable / 3.0 GB reserve)                         │
│  • GW GL.iNet Router: MemAvailable >= 35MB (drop_caches trigger at 45MB)                 │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Existing Implementations:
1. `06_scripts_and_tooling/automation/dynamic_ram_governor.py`:
   - Inspects `psutil.virtual_memory()`.
   - `warn_pct = 80.0`, `crit_pct = 88.0` (needs realignment to 85.0%).
   - Reclaims memory via `gc.collect()` and `sudo -n purge`.
   - Writes state to `04_data_and_memory/session_logs/ram_governor_status.json`.
2. `00_core_infrastructure/self_healing_hub/src/ram_autoscaler_governor.py`:
   - Comprehensive multi-node evaluation across `Mac_Node`, `MacBook_Pro`, `Linux_Head_Node`, `Linux_Tablet`, `MacBook_Air`, `Pixel_10_Pro_XL`, `Samsung_S20`.
   - Implements 4-tier scaling (`SAFE`, `CAUTION`, `PROTECTIVE`, `CRITICAL`).
   - Implements pre-flight node cache trimming (`am trim-caches 2048M`, `pkill -f proot`, `sync && echo 3 | sudo tee /proc/sys/vm/drop_caches`).
   - Computes Kimi-Dev-72B sharding split `[28, 28, 24]` across Linux Node, MacBook Pro, and Mac Host.
3. `06_scripts_and_tooling/network/real_hardware_router_ram_governor.py`:
   - SSH `/proc/meminfo` sampling on `192.168.8.1` (GL-MT3600BE).
   - Auto-flushes kernel buffer cache via `sync; echo 3 > /proc/sys/vm/drop_caches` when `MemAvailable < 45MB`.
   - Optimizes SQM `fq_codel` queue discipline and TCP BBR/cubic congestion.
4. `06_scripts_and_tooling/mcp/mesh_governor_mcp_server.py`:
   - Exposes MCP tools: `audit_ram_and_hardware`, `audit_and_heal_daemons`, `audit_and_heal_storage`, `optimize_mesh_network`.

---

### 2.2 7-Layer Physical Mesh Sharding Subsystem (R5)

#### Hardware Cluster Matrix:
| Layer | Node ID | Hostname / Description | RAM | Cap % | Usable VRAM | Primary Interconnect | Preferred IP | Roles & Protocols |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | `mac_host` | Apple Mac Mini M4 Pro | 24.0 GB | 90.0% | 21.6 GB | TB4 PCIe DMA | `100.119.199.76` / `192.168.8.230` / TB4 `169.254.80.69` | Master DHT Bootstrap, Prompt Ingestion, `llama-server` Master, RAM Governor |
| **L2** | `macbook_pro` | Apple MacBook Pro M1 Max | 16.0 GB | 90.0% | 14.0 GB | TB4 PCIe DMA | TB4 `169.254.114.190` / `100.103.212.21` / `192.168.8.127` | Metal GPU RPC Worker (`ggml-rpc-server`), 285 GB SSD Model Vault |
| **L3** | `linux_node` | AMD Ryzen 7 5700U | 16.0 GB | 80.0% | 13.8 GB | TP-Link 1GbE | `192.168.8.224` / `100.101.39.98` | Gateway Ingress, Docker Hub, Petals DHT Bootstrap & Apache Ray Cluster |
| **L4** | `linux_tablet` | Debian Linux Touch Tablet | 8.0 GB | 75.0% | 6.0 GB | Tailscale Direct | `100.81.92.125` | Mobile Linux Compute, Secondary Petals Worker, Biometrics DSP |
| **L5** | `macbook_air` | Apple M4 MacBook Air | 16.0 GB | 90.0% | 14.0 GB | TB4 PCIe DMA / Wi-Fi 7 | TB4 `169.254.95.19` / `100.93.158.96` / `192.168.8.222` | Secondary Metal Worker, Continuous LoRA Distillation (`accelerate`) |
| **L6** | `pixel_10` | Google Pixel 10 Pro XL | 16.0 GB | 85.0% | 12.5 GB | Multipath Bond / USB | `100.73.38.87` / USB `169.254.60.151` (SSH 8022) | Tensor G5 TPU Worker, Vision Stream Projector, Mobile DHT Node |
| **L7** | `samsung_s20` | Samsung Galaxy S20+ | 12.0 GB | 75.0% | 9.0 GB | Router USB / Tailscale | `100.84.40.95` / Router USB (ADB 5555) | Dedicated Automated UI Tester, OpenClaw Agent, Low-Layer Telemetry Shard |
| **GW** | `router_gw` | GL.iNet GL-MT3600BE | 512 MB | 50.0% | 0.0 GB | LAN 1GbE / Wi-Fi 7 | `192.168.8.1` / `100.122.185.123` | Core Gateway, Subnet Router, Hardware USB Hub, Micro-SLM Sentinel |
| **SUM** | **8 Nodes** | **Pooled Cluster Capacity** | **108.0 GB** | — | **82.8 GB** | — | — | **100% Zero-Mock Hardware Cluster** |

#### Distributed Sharding Frameworks & Modules:
1. `02_ai_models_and_inference/sharding_daemon/`:
   - `config.py`: Hardware specs, dynamic RAM ceilings, transport tier profiles, model catalogs (Kimi-Dev-72B, Qwen2.5-72B, Llama-3-70B, BLOOM-560M).
   - `router.py`: Network-Aware Dynamic Dijkstra DP Router optimizing communication + compute latency with circuit breaker.
   - `network_awareness.py`: UNAL probing live RTT, jitter, loss, and bandwidth across all interfaces.
   - `dht_ring.py`: Libp2p/Kademlia-style DHT topology ring with multiaddr ranking.
   - `prima_ring_adapter.py`: Port 8083 OpenAI proxy with automated health checking and sub-second failover from `prima.cpp` PRP (Port 8082) to legacy `llama.cpp` RPC (Port 8081).
2. Adapters:
   - `adapters/llamacpp_adapter.py`: Metal GPU RPC socket framing (Port 50052) and `-ts` calculation.
   - `adapters/petals_adapter.py`: Petals DHT transformer block forward execution (Port 31330).
   - `adapters/exo_adapter.py`: Exo Zenoh P2P peer ring sharding (Port 52415).
   - `adapters/accelerate_adapter.py`: Hugging Face `accelerate` dynamic device mapping, LoRA parameter offloading, and continuous training hooks (Port 29500).
3. `02_ai_models_and_inference/prima_cpp/`: High-throughput C++ pipelined-ring parallelism implementation.
4. `04_data_and_memory/distributed_model_scanner_ray_pyspark.py`: Apache Ray worker parallelism for distributed filesystem model discovery and AST parsing.

---

### 2.3 Edge-Accelerated Tokenization & Processing Subsystem (E3)

#### Existing Implementations:
1. `02_ai_models_and_inference/sharding_daemon/edge/pixel_termux_node.py`:
   - `PixelThermalSentinel`: Real-time temperature querying (`termux-battery-status` / sysfs) enforcing 41.0°C cutoff.
   - `PixelMemoryGovernor`: Enforces 12.5 GB Usable AI VRAM ceiling (85% of 16GB).
   - `PixelKeepaliveManager`: Acquires `PARTIAL_WAKE_LOCK` via `termux-wake-lock`, sets `settings_enable_monitor_phantom_procs false`, and whitelists Termux/Tailscale from Doze.
   - `PixelEdgeComputeEngine`: Authentic transformer block compute (RMSNorm, MHA, SwiGLU) in pure Python / NumPy.
   - `PixelTermuxServer`: Lightweight HTTP/JSON/Binary REST endpoint for edge requests.
2. `06_scripts_and_tooling/device_watchdog/s20_watchdog.py`:
   - 3-path automated recovery for Samsung S20+ (Direct Tailscale, Router USB ADB TCP/IP bounce via `adb tcpip 5555`, and KEYCODE_WAKEUP).
   - Pre-failure logcat capture and LoRA failure instruction logging.
3. `06_scripts_and_tooling/scripts/adb_wireless_manager.py`:
   - Wi-Fi ADB pairing and connection manager for Android 11+ wireless debugging.
4. `00_core_infrastructure/self_healing_hub/src/npu_training_harvesting_engine.py`:
   - Catalogs on-device NPU power (Apple ANE 38 TOPS, Tensor G5 TPU 22 TOPS, Snapdragon Hexagon 45 TOPS, AMD XDNA 16 TOPS).

---

### 2.4 Canonical Port Matrix

| Port | Service Name | Subsystem / File | Protocol | Role |
| :--- | :--- | :--- | :--- | :--- |
| **8080** | Unified AI Proxy | `02_ai_models_and_inference/lauburu_ai_proxy.py` | HTTP / OpenAI | Central local API gateway & cloud fallback router |
| **8081** | `llama-server` Master | `llama.cpp` / `dynamic_agi_fallback_router.py` | HTTP / GGML-RPC | Primary local inference master (Qwen-3.8Max / GPT-OSS 20B) |
| **8082** | `prima.cpp` PRP Master | `02_ai_models_and_inference/prima_cpp/` | HTTP / PRP | High-throughput Pipelined-Ring Parallelism Master |
| **8083** | `prima.cpp` Ring Adapter | `sharding_daemon/prima_ring_adapter.py` | HTTP / OpenAI | Proxy with health checking & failover to Port 8081 |
| **8084** | Conversational RAG / Edge Server | `lauburu_ai_proxy.py` / `sharding_daemon/config.py` | HTTP / JSON | Sub-50ms Edge RAG & Nemotron RPC |
| **8085** | Vision Server / Abliterated | `lauburu_ai_proxy.py` / `sharding_daemon/config.py` | HTTP / OpenAI | Multimodal Vision & Qwen-Abliterated |
| **8086** | Qwen 2.5 Math Specialist | `lauburu_ai_proxy.py` / `sharding_daemon/config.py` | HTTP / OpenAI | Deterministic algorithmic & mathematical reasoning |
| **8087** | Pixel Edge AI Server | `lauburu_ai_proxy.py` / `pixel_termux_node.py` | HTTP / Tailscale | Tensor G5 on-device inference & tokenization |
| **8088** | Web-TUI Portal & Cockpit | `01_apps/canonical_port/tui/serve_web_tui.py` | HTTP / WebSocket | Interactive live telemetry and swarm dashboard |
| **18802** | Self-Healing Hub / WoL API | `00_core_infrastructure/self_healing_hub/` | HTTP / REST | Infrastructure resurrection, WoL packets, metric poller |
| **29500** | PyTorch Accelerate / Torchrun | `sharding_daemon/adapters/accelerate_adapter.py` | TCP Rendezvous | Multi-GPU / multi-node LoRA training rendezvous |
| **31330** | Petals DHT Bootstrap Port | `sharding_daemon/adapters/petals_adapter.py` | Libp2p / TCP | Decentralized peer discovery & block routing |
| **50052** | `llama.cpp` GGML-RPC Sharding | `06_scripts_and_tooling/network/llama_rpc_shard_daemon.py` | GGML Binary RPC | Sub-millisecond tensor exchange over TB4 DMA |
| **50053** | `prima.cpp` PRP Worker Socket | `02_ai_models_and_inference/prima_cpp/` | Raw TCP Binary | PRP worker socket on MacBook Pro & Linux Node |
| **52415** | Exo Zenoh P2P Port | `sharding_daemon/adapters/exo_adapter.py` | Zenoh / UDP/TCP | Ring memory topology & dynamic pipeline routing |

---

## 3. Concrete Code Inventory & File Mapping

| Subsystem | Exact File Path | Line Range | Status | Key Class / Functions | Current Gaps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R3** | `06_scripts_and_tooling/automation/dynamic_ram_governor.py` | 1–105 | Production | `DynamicRamGovernor`, `check_and_govern` | Hardcoded 88% crit threshold; no MPS purge; no worker throttle; no TB4 layer offload |
| **R3** | `00_core_infrastructure/self_healing_hub/src/ram_autoscaler_governor.py` | 1–502 | Production | `MeshRAMAutoScalerSentinel`, `evaluate_and_scale`, `trim_node_caches` | Evaluates multi-node headroom, but scaling actions (throttle/context) are not propagated to active PyTorch / Ray workers |
| **R3** | `06_scripts_and_tooling/network/real_hardware_router_ram_governor.py` | 1–290 | Production | `RealHardwareRAMGovernor`, `TriVaultStorageGuardian` | Router drop_caches works, but is isolated from the host governor event loop |
| **R3** | `06_scripts_and_tooling/mcp/mesh_governor_mcp_server.py` | 1–96 | Production | `handle_request`, `HybridMeshGovernor` | Provides MCP query tools, but lacks active webhook/push notification when threshold is breached |
| **R5** | `02_ai_models_and_inference/sharding_daemon/config.py` | 1–446 | Production | `CLUSTER_NODES`, `MODEL_CATALOG`, `TRANSPORT_TIER_PROFILES` | Configures 8 nodes (82.8 GB VRAM), but static DHCP link-local IP changes need resilient dynamic interface probing |
| **R5** | `02_ai_models_and_inference/sharding_daemon/router.py` | 1–784 | Production | `RoutingPlan`, `RouteStep`, `DijkstraRouter` | Dijkstra DP works on static link estimates; lacks runtime dynamic layer migration message dispatch |
| **R5** | `02_ai_models_and_inference/sharding_daemon/prima_ring_adapter.py` | 1–201 | Production | `FastAPI`, `probe_endpoint`, `_proxy_stream` | Excellent failover proxy on 8083, but does not coordinate with the RAM governor for load shedding |
| **R5** | `02_ai_models_and_inference/sharding_daemon/adapters/llamacpp_adapter.py` | 1–325 | Production | `LlamaCppAdapter`, `compute_tensor_split` | Split is computed once at initialization; dynamic re-splitting requires restarting the worker process |
| **R5** | `02_ai_models_and_inference/sharding_daemon/adapters/accelerate_adapter.py` | 1–400 | Production | `AccelerateAdapter`, `compute_auto_device_map` | Offloads MPS -> CPU -> Disk, but does not listen for dynamic throttle signals from RAM Governor |
| **E3** | `02_ai_models_and_inference/sharding_daemon/edge/pixel_termux_node.py` | 1–1073 | Production | `PixelThermalSentinel`, `PixelMemoryGovernor`, `PixelKeepaliveManager`, `PixelTermuxServer` | Edge server handles block execution, but does not expose a batch tokenization RPC endpoint |
| **E3** | `06_scripts_and_tooling/device_watchdog/s20_watchdog.py` | 1–192 | Production | `S20DeviceWatchdog`, `attempt_recovery` | Excellent 3-path ADB bounce; does not have an active batch worker daemon for dataset tokenization |
| **E3** | `00_core_infrastructure/self_healing_hub/src/npu_training_harvesting_engine.py` | 1–291 | Production | `MultiStreamDataHarvester`, `NPUHardwareGovernor` | Harvests 4 real streams to JSONL, but tokenization occurs on host rather than edge NPU |

---

## 4. Concrete Implementation Gaps & Technical Action Plan

### 4.1 R3: Real-Time Dynamic RAM & VRAM Governor (<85% Safety Ceiling)

#### Identified Deficiencies:
1. **Critical Threshold Alignment:** `dynamic_ram_governor.py` triggers emergency action at 88.0%. Requirement R3 strictly mandates maintaining Host RAM below the **85.0% safety ceiling** with progressive multi-tier throttling starting at 75.0% and 80.0%.
2. **Apple Metal MPS & CUDA Cache Purging:** Active PyTorch/TRL fine-tuning retains cached Metal allocations. When RAM exceeds 80%, the governor must execute:
   ```python
   import gc
   gc.collect()
   if hasattr(torch, "mps") and torch.mps.is_available():
       torch.mps.empty_cache()
   if hasattr(torch, "cuda") and torch.cuda.is_available():
       torch.cuda.empty_cache()
   ```
3. **Active Worker Throttling & Process Control:** When memory load exceeds 80%:
   - Send throttle signal (e.g. reduce batch size from 4 to 1, insert `time.sleep` pause cycles, or reduce Ray parallelism).
   - When memory load exceeds 85%, send `SIGSTOP` to non-critical background training workers, purge OS caches (`sudo -n purge` on macOS, `sync && echo 3 | sudo tee /proc/sys/vm/drop_caches` on Linux), and wait for memory to drop below 75% before sending `SIGCONT`.
4. **Dynamic Tensor Layer Offload over TB4 DMA Bridge:** When Host RAM exceeds 85%, dynamically shed top model layers (e.g., layers 56..79 of Kimi-72B) to MacBook Pro L2 (`169.254.114.190:50052`) via RPC.

---

### 4.2 R5: 7-Layer Mesh Sharding & Edge Hardware Offloading

#### Identified Deficiencies:
1. **Thunderbolt 4 DMA IP Resolution Resilience:** The TB4 link-local IP on MacBook Pro can vary across macOS DHCP handshakes (`169.254.187.138` vs `169.254.114.190`). A dynamic interface probe (`ifconfig bridge0 | grep 'inet 169.254'`) is needed during initialization to auto-bind the exact live IP.
2. **Ray Cluster Multi-Node Auto-Bootstrap:** L3 (Linux Head Node) and L5 (MacBook Air) must be automatically connected to the Ray head cluster on `mac_host` via a dedicated cluster initialization daemon (`ray start --address='100.119.199.76:6379'`).
3. **Dynamic Re-sharding Runtime Protocol:** When the RAM Governor signals high load, `sharding_daemon` must update the tensor split across `llamacpp_adapter` and `prima_ring_adapter` without dropping in-flight inference requests.

---

### 4.3 E3: Edge-Accelerated Dataset Tokenization

#### Identified Deficiencies:
1. **Dedicated Edge Tokenizer Daemon on Termux:** Deploy an ultra-lightweight FastAPI / JSON-RPC daemon on the Pixel 10 Pro (Tensor G5) and Samsung S20+ listening on Port 8087 / 8089 in Termux that accepts batches of text strings and returns HuggingFace-compatible tokenized ID tensors (`input_ids`, `attention_mask`, `labels`) using `tokenizers` Rust bindings compiled for ARM64 Android.
2. **Night-Cycle Synthetic Question Generator:** Integrate SmolLM2-135M / Qwen-0.5B running on Android Termux into `free_tier_ai_continuous_cron.py` during overnight off-peak windows (00:00 - 06:00 UTC) to generate high-quality synthetic instruction pairs from monorepo AST diffs without burdening Host CPU/GPU.

---

## 5. Architectural Blueprint for Implementation

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED MESH ARCHITECTURAL TOPOLOGY                              │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│    ┌───────────────────────────┐    10Gbps TB4 DMA (0.27ms)   ┌────────────────────────┐ │
│    │    L1: Mac Mini M4 Pro    │◄════════════════════════════►│  L2: MacBook Pro M1 Max│ │
│    │ • Memory Governor (<85%)  │                              │ • ggml-rpc-server      │ │
│    │ • llama-server / prima PRP│                              │ • 285 GB Model Vault   │ │
│    │ • Ray Cluster Head        │                              │ • Port 50052 / 50053   │ │
│    └─────────────┬─────────────┘                              └────────────────────────┘ │
│                  │                                                                       │
│                  │ 1GbE LAN (0.90ms) / Wi-Fi 7 MLO (2.10ms)                              │
│                  ▼                                                                       │
│    ┌───────────────────────────┐                              ┌────────────────────────┐ │
│    │    L3: Linux Head Node    │◄────────────────────────────►│   L5: MacBook Air M4   │ │
│    │ • Docker Hub & Ray Worker │      Tailscale Direct        │ • Continuous LoRA Dist.│ │
│    │ • Petals DHT Bootstrap    │         (3.50ms)             │ • Metal Shaders (MPS)  │ │
│    └─────────────┬─────────────┘                              └────────────────────────┘ │
│                  │                                                                       │
│                  │ Wireless ADB / USB ADB / Tailscale WireGuard                          │
│                  ▼                                                                       │
│    ┌───────────────────────────┐                              ┌────────────────────────┐ │
│    │   L6: Pixel 10 Pro XL     │                              │   L7: Samsung S20+     │ │
│    │ • Tensor G5 Edge TPU      │                              │ • Exynos 990           │ │
│    │ • Batch Tokenizer Daemon  │                              │ • UI Automation        │ │
│    │ • Thermal Guard (41.0°C)  │                              │ • Synthetic QA Gen     │ │
│    └───────────────────────────┘                              └────────────────────────┘ │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Verification and Test Strategy

### 6.1 Unit & Integration Test Targets
1. **Dynamic RAM Governor Invariant:**
   - Execute: `pytest 02_ai_models_and_inference/tests/test_m3_sharding_and_governor.py -v`
   - Verify all 7 layer ceilings: `mac_host` (90%), `macbook_pro` (90%), `linux_node` (80%), `linux_tablet` (75%), `macbook_air` (90%), `pixel_10` (85%), `samsung_s20` (75%).
2. **TB4 Interconnect & Port Verification:**
   - Verify Port 50052 RPC handshake: `nc -zv 127.0.0.1 50052` and `nc -zv 169.254.114.190 50052`.
   - Verify Port 8083 Prima proxy: `curl -s http://127.0.0.1:8083/prima/status`.
3. **Edge Node & Keepalive Verification:**
   - Execute: `pytest 02_ai_models_and_inference/tests/test_pixel_termux_edge.py -v`
   - Verify `PixelThermalSentinel` 41.0°C cutoff and `PixelMemoryGovernor` 12.5 GB ceiling.

### 6.2 Zero-Mock Rule #0 Compliance
All metrics in `ram_governor_status.json`, `router_governor_telemetry.json`, and `prima_sharding_manifest.json` must be derived from genuine `/proc/meminfo`, `psutil`, `vm_stat`, and socket probes with clean fallback waiting states (`--`).
