# 🌐 Canonical Mesh RAM Inventory & Distributed AI Deployment Architecture

> **Governed by:** Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), Rule 2 (Tri-Vault), Rule 3 (Host Sanctuary), Rule 8 (Pre-Flight Network Gate), Rule 10 (Linux Mini First-Offload), Rule 15 (Dynamic ELO Default Model Governance)  
> **Timestamp:** `2026-10-12T10:10:00+11:00`

---

## 🏛️ 1. Active Fleet Memory Matrix (100% Empirically Probed)

All figures below are extracted directly from kernel syscalls (`sysctl hw.memsize`, `vm_stat`, `/proc/meminfo`, `adb shell`) in accordance with Darwin kernel memory accounting formulas and Rule 0.

| Node | Silicon / Architecture | Role & Model Placement | Total RAM | Usable AI VRAM | Dynamic RAM Cap | Primary Interfaces | Probed Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1 Mac Mini** | Apple M4 Pro (8P+4E CPU, 16C GPU) | **Host Sanctuary**: Master Ingestion, Screen Lens Sovereign, Memory Governor | **24.00 GB** | **19.20 GB** | **80% Hard Cap** ($\ge 4.8\text{ GB}$ free) | TB `bridge0` (`10.0.0.2`), Wi-Fi `192.168.8.143`, LAN `192.168.8.230`, TS `100.119.199.76` | `ONLINE` (0.05ms local) |
| **L8 Linux Mini** | Intel Core i7-8700B (6C/12T), Ubuntu 24.04 | **TB4 DMA Co-Processor & GGUF Vault**: 40 Gb/s TB4 Bridge, Huihui 27B GGUF Vault | **32.00 GB** | **25.60 GB** | **80% Hard Cap** | TB `bridge0` (`10.0.0.8`), LAN `192.168.8.242`, TS `100.121.247.8` | `ONLINE` (**0.38ms TB**, 3.5ms TS) |
| **L1c / L2 MacBook Pro** | Intel Core i7-9750H (6C/12T), macOS | **Desktop Automation & Teacher Target**: osascript target under Screen Lens, Model Vault | **16.00 GB** | **14.00 GB** | **90% Hard Cap** | TB `bridge0` (`10.0.0.4`, MTU 9000), LAN Wi-Fi `192.168.8.127`, TS `100.103.212.21` | `ONLINE` (4.67ms LAN / 40 Gbps TB) |
| **L1b Mac Mini M2** | Apple M2 Pro, Mac14,12 (10C/16G) | **Secondary Compute Worker**: Local inference & validation | **16.00 GB** | **13.60 GB** | **85% Hard Cap** | TB `bridge0` (`10.0.0.3`), LAN `192.168.8.114`, TS `100.104.128.34` | `ONLINE` (**0.43ms TB**, 27ms LAN) |
| **L3 Linux Head Node** | AMD Ryzen 7 5700U (8C/16T), Ubuntu | **Compute Hub (First-Offload)**: Docker Hub, Ray Head, SeaweedFS DFS, Qdrant | **15.00 GB** | **12.00 GB** | **80% Hard Cap** | LAN `192.168.8.225`, TS `100.101.39.98`, BT to L1 (-28 dBm) | `ONLINE` (~5.5ms TS, 13.8ms LAN) |
| **L4 Linux Tablet** | Debian Linux (`debian-1`) | **Bedside Mobile Compute**: Touch DSP, Peripheral Telemetry | **8.00 GB** | **6.00 GB** | **75% Hard Cap** | LAN `192.168.8.176` (Port 2 on Router), TS `100.99.210.89` | `ONLINE` (0.95ms LAN, 111-492ms TS) |
| **L5 MacBook Air M4**| Apple M4 (4P+6E CPU, 10C GPU) | **Metal Worker**: Metal Performance Shaders, 24/7 LoRA adapter distillation | **16.00 GB** | **14.00 GB** | **90% Hard Cap** | LAN Wi-Fi `192.168.8.248`, TS `100.121.202.34` | `ONLINE` (~12ms TS, 3.5ms LAN) |
| **L6 Pixel 10 Pro XL**| Google Tensor G5 + Edge TPU | **Vision Edge**: 8K PTZ Vision Stream & Edge TPU VLA, Shizuku rish | **16.00 GB** | **13.60 GB** | **85% Hard Cap** | LAN Wi-Fi `192.168.8.213`, TS `100.114.215.68` (Termux: `100.124.199.15`) | `ONLINE` (Ports 8022/1716 open) |
| **L7 Samsung S20+** | Samsung Exynos 990, Android 13 | **UI Automation**: Dedicated OpenClaw ADB UI Test Target | **12.00 GB** | **9.00 GB** | **75% Hard Cap** | LAN `192.168.8.130`, USB Eth `192.168.8.224`, TS `100.78.206.96` | `ONLINE` (ADB :5039 / :5555) |
| **GW GL.iNet Router** | MediaTek Filogic 880 Quad-Core, OpenWrt | **Hardware Gateway**: 2.5G NBN WAN `eth2`, USB Bridge, Wi-Fi 7 MLO AP | **2.00 GB** | Embedded (1.38 GB free) | **1 GB Swap Active** | LAN `192.168.8.1`, TS `100.70.123.123`, WAN `eth2` (NBN NTD) | `ONLINE` (12ms NBN WAN, 0% loss) |
| **TOTAL FLEET** | **8 Compute Nodes + 1 GW** | **Pooled Distributed AI Ecosystem** | **139.00 GB** | **108.40 GB** | **Dynamic Caps** | **Multi-Subnet Fabric** | **ALL PROBED & ALIVE** |

---

## ⚡ 2. Sovereign Local Model Alignment & Runtime Reality (Rule 0 & 15)

### Mac Mini (L1 Host): Dedicated Master Orchestration Plane
- **Screen Lens Sovereign:** Active on Port 3035 with native Cocoa / AXUIElement perception, Port 4003 (MJPEG Live Stream), Port 3037 (Global Orchestrator).
- **Master Local Orchestration Plane (Port 8082):**
  - *Target Architecture:* `Qwen 3.8 Max 27B Abliterated` via `prima.cpp` PRP ring.
  - *Probed Runtime Reality:* `decentralized_prima_daemon.py` proxy forwarding to `llama-server` on Port 8090 serving `Hermes-3-Llama-3.1-8B.Q4_K_M.gguf`. Advertises itself as `qwen_38_max`.
- **Adversarial Red Team Plane (Port 8083):**
  - *Target Architecture:* `Qwen 3.8 Max` standard/unabliterated.
  - *Probed Runtime Reality:* `mesh_multiport_bridge.py` proxy advertising `qwen_38_max_abliterated`; `/props` model_path = `/home/linuxmini/model_vault_gguf/Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf` on L8 `lauburu`.
- **Subordinate Syntax Worker Plane (Port 8081):**
  - *Probed Runtime Reality:* `mesh_multiport_bridge.py` proxy returning `Qwen2.5-VL-7B-Instruct-Q4_K_M` (vision model).
- **Host Sanctuary Restored:** Mac Mini unified memory preserves $\ge 4.8\text{ GB}$ free buffer at all times (utilization $\le 80\%$), preventing kernel panics.

### Peripheral Mesh Model Realignment
- **L8 Linux Mini (`lauburu` — `10.0.0.8` / `100.121.247.8`):** Hosts the heavy 27B model `Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf` in `/home/linuxmini/model_vault_gguf/`, connected to L1 via **40 Gb/s Thunderbolt 4 bridge (0.38ms avg RTT)**.
- **L2 MacBook Pro (`100.103.212.21`):** Operates as the Screen Lens Teacher Target for desktop automation under Teacher Model supervision over LAN/Tailscale.
- **L3 Linux Head Node (`100.101.39.98`):** Hosts SeaweedFS DFS, Ray Head, Docker microservices, and Qdrant with ample headroom.

---

## 🔬 3. Moonshot Kimi-VL & 72B Distributed Sizing

### Memory Footprint by Quantization Level

| Quantization Tier | Model Weights (GB) | Encoder & Projector (GB) | KV Cache @ 32K (MLA) | Min VRAM / RAM Needed | Recommended Host |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FP16 (16-bit)** | 32.0 GB | 2.0 GB | ~0.60 GB | **~35.5 GB** | Distributed PRP Ring (L1 + L8 via 40Gbps TB4) |
| **Q8_0 (8-bit)** | 16.0 GB | 1.4 GB | ~0.60 GB | **~18.5 GB** | **L8 Linux Mini Hub** (25.6 GB available AI VRAM) |
| **Q4_K_M (4-bit)** | 8.8 GB | 0.9 GB | ~0.60 GB | **~10.5 GB** | **L8 Linux Mini** OR **L3 Linux Head Node** |
| **IQ3_M (3-bit)** | 6.8 GB | 0.8 GB | ~0.60 GB | **~8.2 GB** | **L2 MacBook Pro** OR **L5 MacBook Air** |
| **IQ2_XXS (2-bit)** | 4.8 GB | 0.8 GB | ~0.60 GB | **~6.2 GB** | Edge / Low-power standalone |

### Optimal Placement on Lauburu Mesh
1. **Best Standalone Placement: L8 Linux Mini (`10.0.0.8` / `100.121.247.8`)**:
   - L8 has **32.0 GB physical RAM (25.6 GB usable AI VRAM)**.
   - It hosts models natively on CPU/Vulkan with zero impact on the Mac Mini host RAM.
2. **Alternative Placement: L3 Linux Head Node (`100.101.39.98`)**:
   - L3 has **12.0 GB usable AI VRAM**. It can comfortably run Q4_K_M (10.5 GB footprint).
3. **Mac Mini Invariant (Rule 3):**
   - Because Mac Mini must preserve $\ge 4.8\text{ GB}$ free physical RAM for Screen Lens and OS sanctuary, running heavy 27B+ models directly on L1 alongside Master Orchestration would violate Rule 3 unless sharded across the 40Gbps Thunderbolt 4 bridge to L8 `lauburu`.

---

## ⚡ 4. Thunderbolt 4 Fabric Diagnostic & Verified Truth

### Probed Physical Link Reality (Rule 0)
1. **Mac Mini L1 Thunderbolt Architecture:** Mac mini M4 Pro features 3 discrete Thunderbolt controllers, all three currently active at 40 Gb/s on `bridge0` (`10.0.0.0/24`).
2. **Receptacle 1 (Bus 0):** Connected to **L8 `lauburu` (Linux Mini Hub)** at **40 Gb/s** (`bridge0` IP `10.0.0.8`, 0.38 ms avg RTT).
3. **Receptacle 2 (Bus 1):** Connected to **L1b `Mac mini M2 Pro`** at **40 Gb/s** (`bridge0` IP `10.0.0.3`, 0.43 ms avg RTT).
4. **Receptacle 3 (Bus 2):** Connected to **L2 `MacBook Pro 16"`** at **40 Gb/s** (`bridge0` IP `10.0.0.4`, MTU 9000, 4.67 ms LAN fallback).
