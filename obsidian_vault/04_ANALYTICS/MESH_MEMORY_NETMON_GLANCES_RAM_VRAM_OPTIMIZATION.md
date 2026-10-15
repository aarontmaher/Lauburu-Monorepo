# 🧠 Sovereign Mesh Memory Note: `netmon` v2.0, Glances API (`:61208`), Canonical IP Matrix & Normal RAM vs VRAM Optimization

**Updated:** 2026-10-14  
**Status:** Production-Active & Persisted Across Neo4j 5.26.32 (`L3:7474` / `:7687`), Qdrant MRL (`L3:6333`), EmbeddingGemma 2 (`L5:8087` / `L1:8087`), Antigravity Skills, and LoRA Distillation Lake.

---

## 1. Executive Summary & Empirical Impact

To prevent live telemetry polling from overloading mesh nodes and to ensure distributed AI sharding respects the physical boundary between **Unified Metal VRAM**, **Discrete GPU VRAM + Normal RAM**, and **Normal DDR4 System RAM Only (`0 GB` VRAM)**, the following empirical upgrades have been permanently deployed and persisted:

| Optimization Target | Before (v1.0 Unoptimized) | After (v2.0 Sovereign Governance) | Measured Improvement |
|---|---|---|---|
| **`L3` (`100.101.39.98`) `glances.service` RSS** | `449.3 MB` peak (`404.5 MB` active RSS) + `160.9 MB` swap | **`43.7 MB` RSS** (`0 MB` swap) via `--disable-plugin docker,containers,ports,folders,raid,cloud,amps,processlist -t 5` | **`-90.3%` daemon RAM overhead** (`~830 MB` system RAM freed on `L3`: `39.7%` -> `34.5%`) |
| **`L3` Glances API Latency** | `6,917.4 ms` (`/api/3/all` full system & container walk) | **`73.23 ms`** (`/api/3/load`), **`78.78 ms`** (`/api/3/mem`), **`82.94 ms`** (`/api/3/network`) | **`-98.8%` HTTP telemetry latency** |
| **`netmon --once` Total Mesh Poll Time** | `~26,000 ms` (sequential `/all` timeouts + sleeping node stalls) | **`2,570 ms`** (300ms async TCP precheck + modular endpoints + 60s `/fs` cache) | **`10.1x` faster full-mesh snapshot** |
| **Normal RAM (`0 GB` VRAM) vs VRAM Routing** | Treated `L3` (16GB) & `L8` (32GB) as generic GPU-capable RAM | Explicitly classifies `L8` (32GB DDR4) & `L3` (16GB DDR4) as `NORMAL_RAM_ONLY_ZERO_VRAM` (`-ngl 0`), dedicating them to **20 GB Disaggregated Mooncake/LMCache KV-Cache**, **Neo4j 5.26.32**, **Qdrant**, and **AVX2 Sparse/Draft shards** | Eliminates CPU/PCIe thrashing while freeing Unified Metal VRAM on `L1` (24GB) & `L5` (16GB) |

---

## 2. Canonical 10-Node IP Address, Glances API (`:61208`) & Memory Class Matrix

Machine-readable source of truth: [`mesh_ip_matrix.json`](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_ip_matrix.json)

| Node | Hardware | Primary Tailscale IP | LAN IP (`192.168.8.x`) | TB4 10GbE IP | SSH Target | Glances API (`:61208`) | Memory Class | Normal RAM | Dedicated / Unified VRAM | Bandwidth |
|---|---|---|---|---|---|---|---|---|---|---|
| **GW** | GL.iNet GL-BE14000 Wi-Fi 7 | — | `192.168.8.1` | — | `root@192.168.8.1:22` | None (`/proc/meminfo` via SSH) | `EMBEDDED_ROUTER_NORMAL_RAM_ONLY` | `1.0 GB` | `0.0 GB` | `12.8 GB/s` |
| **L1** | Mac Mini M4 Pro (Sanctuary) | `100.119.199.76` | `192.168.8.230` / `.143` | `10.0.0.1` | `aaron@100.119.199.76:22` | `http://100.119.199.76:61208/api/4` | `UNIFIED_METAL_VRAM` | `24.0 GB` | **`24.0 GB` Unified** | `273.0 GB/s` |
| **L5** | MacBook Air M4 (Sanctuary) | `100.121.202.34` | `192.168.8.248` | `10.0.0.2` | `aaronmaher@100.121.202.34:22` | `http://100.121.202.34:61208/api/4` | `UNIFIED_METAL_VRAM` | `16.0 GB` | **`16.0 GB` Unified** | `120.0 GB/s` |
| **L1b** | Mac Mini M2 Pro (AI Node) | `100.104.128.34` | `192.168.8.114` | `10.0.0.3` | `aaronmaher@192.168.8.114:22` | `http://100.104.128.34:61208/api/4` | `UNIFIED_METAL_VRAM` | `16.0 GB` | **`16.0 GB` Unified** | `200.0 GB/s` |
| **L2** | MacBook Pro Intel i9 | `100.103.212.21` | `192.168.8.127` | `10.0.0.4` | `aaronmaher@192.168.8.127:22` | `http://192.168.8.127:61208/api/4` | `DISCRETE_4GB_VRAM_PLUS_16GB_NORMAL_RAM` | `16.0 GB` DDR4 | **`4.0 GB` GDDR6** | `192.0 GB/s` (GPU) / `42.6 GB/s` (RAM) |
| **L3** | Linux Head Node (Ryzen 7 5700U) | `100.101.39.98` | `192.168.8.225` | — | `linux@100.101.39.98:22` | `http://100.101.39.98:61208/api/3` | `NORMAL_RAM_ONLY_ZERO_VRAM` | **`16.0 GB` DDR4** | **`0.0 GB` VRAM** | `25.6 GB/s` |
| **L8** | Lauburu Linux Hub (i7-8700B) | `100.121.247.8` | `192.168.8.242` | `10.0.0.8` | `linuxmini@100.121.247.8:22` | `http://100.121.247.8:61208/api/4` | `NORMAL_RAM_ONLY_ZERO_VRAM` | **`32.0 GB` DDR4** | **`0.0 GB` VRAM** | `34.1 GB/s` |
| **L4** | Surface Go 2 Linux Tablet | `100.78.250.119` | `192.168.8.227` | — | `aaron@100.78.250.119:22` | None (`/proc/meminfo` via SSH) | `NORMAL_RAM_ONLY_ZERO_VRAM` | **`8.0 GB` LPDDR3** | **`0.0 GB` VRAM** | `14.9 GB/s` |
| **L6** | Google Pixel 10 Pro XL | `100.114.215.68` | `192.168.8.213` | — | `u0_a363@192.168.8.213:8022` | None (`ssh -p 8022 /proc/meminfo`) | `EDGE_LPDDR5X_TENSOR_G5_NPU` | `16.0 GB` LPDDR5X | `8.0 GB` Shared NPU | `68.0 GB/s` |
| **L7** | Samsung Galaxy S20+ 5G | — | `192.168.8.101` / `.224` | — | `u0_a420@192.168.8.101:8022` | None (`adb shell /proc/meminfo`) | `EDGE_LPDDR5_NORMAL_RAM` | `12.0 GB` LPDDR5 | `0.0 GB` | `44.0 GB/s` |

---

## 3. Non-Overloading Live Telemetry Architecture (`netmon` v2.0 & Glances API)

Machine-readable governance policy: [`mesh_ram_governance_rules.json`](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_ram_governance_rules.json)  
Implementations: [`dual_network_monitor.py`](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/dual_network_monitor.py) (`~/.local/bin/netmon`) and [`autonomous_async_netmon.py`](file:///Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/autonomous_async_netmon.py)

1. **Strict Prohibition on `/api/3/all` and `/api/4/all`:**
   - Calling `/all` on Glances forces synchronous enumeration of every process, open socket, filesystem mount, and container daemon. On `L3`, `/api/3/all` took `6,917 ms` and bloated Glances to `449.3 MB` RSS.
2. **Modular Micro-Endpoints Only (`<1.5 KB` JSON, `~75 ms`):**
   - `GET /api/{3|4}/quicklook` — CPU% & RAM% summary.
   - `GET /api/{3|4}/mem` — Total, available, and used RAM bytes.
   - `GET /api/{3|4}/load` — 1m/5m/15m kernel load averages (`cpucore`).
   - `GET /api/{3|4}/network` — Per-interface RX/TX byte counters (`en0`, `eth0`, `tailscale0`, `bridge0`).
   - `GET /api/{3|4}/fs` — Cached with a **60-second TTL** so disk `statfs` syscalls are never repeated on every refresh.
3. **Low-Overhead Systemd Unit on `L3` (`/etc/systemd/system/glances.service`):**
   ```ini
   ExecStart=/usr/bin/glances -w -B 0.0.0.0 -p 61208 -t 5 --disable-plugin docker,containers,ports,folders,raid,cloud,amps,processlist
   ```
4. **300ms Async TCP Pre-Check & Adaptive Overload Circuit Breaker:**
   - Before issuing any HTTP or SSH request, `netmon` performs an async `0.30s` TCP connect check so offline/sleeping nodes never block the event loop.
   - When any node's `cpu_pct > 80.0%` or `mem_pct > 88.0%`, `netmon` trips its **Adaptive Overload Circuit Breaker (`THROTTLED_3X`)**, multiplying the poll interval by `3x` (`4.0s -> 12.0s`) and skipping secondary probes until pressure subsides.

---

## 4. Normal RAM (`0 GB` VRAM) vs Unified/Discrete VRAM Workload Optimization

Implemented in [`unified_hybrid_sharding_engine.py`](file:///Volumes/Lauburu-Monorepo/02_ai_models_and_inference/unified_hybrid_sharding_engine.py):

1. **Class 1 — Apple Silicon Unified Metal VRAM (`L1` 24GB, `L5` 16GB, `L1b` 16GB):**
   - **Hardware Physics:** `120–273 GB/s` zero-copy unified memory shared between CPU, Metal GPU, and ANE.
   - **Optimal Workload:** Dense transformer attention/FFN decode layers (`-ngl 99`), multimodal vision/audio encoders (`EmbeddingGemma 2 :8087`, `Qwen2-VL`), and low-TTFT primary token generation.
   - **Protection Floor:** Maintain at least `15%` free memory headroom (`>=3.0 GB` on `L1`, `>=2.2 GB` on `L5`). When Unified VRAM utilization exceeds `85%`, offload KV-cache prefixes to `L8` and `L3`.
2. **Class 2 — Hybrid Discrete GPU VRAM + Normal DDR4 System RAM (`L2` MacBook Pro Intel):**
   - **Hardware Physics:** `4.0 GB` Discrete AMD Radeon Pro 5500M GDDR6 (`192 GB/s`) + `16.0 GB` Normal DDR4 RAM (`42.6 GB/s`).
   - **Optimal Workload:** Cap GPU layer allocation strictly at `<=3.2 GB` so it never spills across PCIe into DDR4; use the `16.0 GB` Normal DDR4 RAM for desktop browser automation (`:9222`) and Teacher-Student dataset staging.
3. **Class 3 — Normal DDR4 System RAM Only, `0 GB` Dedicated VRAM (`L8` 32GB DDR4, `L3` 16GB DDR4, `L4` 8GB):**
   - **Hardware Physics:** `48.0 GB` combined DDR4 system RAM across `L8` + `L3` (`~27.2 GB` currently free), but **`0.0 GB` dedicated GPU VRAM** (`25.6–34.1 GB/s` dual-channel DDR4).
   - **Strict Anti-Pattern:** Never schedule dense FP16/Q8 GPU attention decode blocks or pass `-ngl > 0` on `L3` or `L8`.
   - **Optimal Workload:**
     - **Disaggregated Mooncake / LMCache KV-Cache Prefix Pools:** `16.0 GB` on `L8` + `4.0 GB` on `L3` (`20.0 GB` total) storing long-context KV states over Tailscale/LAN so `L1` and `L5` Unified Metal VRAM stays dedicated to active weight matrices.
     - **Graph & Vector Memory Stores:** Neo4j 5.26.32 (`L3:7474/:7687`), Qdrant MRL (`L3:6333`), and Podman AI Trainers (`L3:8096`, `L8:8096`).
     - **CPU-Friendly AVX2 Sparse MoE Experts & Speculative Draft Models (`SmolLM2-360M` / `Qwen2.5-0.5B`):** Run with `--mmap --mlock -ngl 0 -t 10` (`L8`) and `-t 7` (`L3`).
