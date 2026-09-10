---
title: "Lauburu 7-Layer Mesh Device Role & Student Model Optimization Matrix"
date: 2026-09-04
version: "2.4.0-CANONICAL"
tags: [mesh, device_roles, student_models, zero_mock, hardware_matrix, human_verification]
---

# 🌐 Lauburu 7-Layer Mesh Device Role & Student Model Optimization Matrix

> **Mandate:** Sub-1.5B edge student models (SmolLM, Tiny-LLM, StorySupra, Qwen2.5-0.5B, DeepSeek-R1-1.5B) are distributed across all physical layers of the mesh. Each device's operational role is either automatically evaluated or human-verified and optimized for that role.

## 📊 1. Master Hardware & Edge Student Model Distribution Matrix

| Layer | Node | RAM / Cap | Compute Arch | Assigned Student Model | Role & Purpose | Live Status | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1** | Mac Mini M4 Pro (Mac_Node) | 24.0GB / 21.6GB | Apple M4 Pro (12-core CPU, 16-... | 📦 `qwen2.5-0.5b-instruct-q4_k_m.gguf` | Primary Host, Memory Governor & Prompt Ingestion: Sub-10ms AST parsing, prompt triage, and memory go... | 🟢 0.01 ms | ✅ APPROVED |
| **L2** | MacBook Pro M4 (Metal RPC) | 16.0GB / 14.0GB | Apple M4 (10-core CPU, 10-core... | 📦 `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` | Metal GPU RPC Worker & 285 GB SSD Model Vault: High-throughput C11/Rust tensor compilation & 80B ... | 🟢 165.24 ms | ✅ APPROVED |
| **L3** | Linux Head Node (Ryzen 7) | 16.0GB / 13.8GB | AMD Ryzen 7 5700U (8C/16T, Doc... | 📦 `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` | Gateway Ingress, Petals DHT Bootstrap & PySpark Lakehouse: Continuous log summarization, Docker container tri... | ⚪ STANDBY | ✅ APPROVED |
| **L4** | Linux Tablet (Debian Touch) | 8.0GB / 6.5GB | ARM64 / x86 Low-Power Debian (... | 📦 `SmolLM2-360M-Instruct-Q4_K_M.gguf` | Mobile Linux Compute, Bedside Touch DSP & Polysomnography: Lightweight 512Hz Pan-Tompkins QRS anomaly explana... | ⚪ STANDBY | ⏳ PENDING |
| **L5** | MacBook Air M4 (Secondary Metal) | 16.0GB / 14.0GB | Apple M4 (Metal Performance Sh... | 📦 `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` | Secondary Metal Worker & Dedicated Continuous LoRA Distillation: Continuous MLX/TRL LoRA training pair backpropagat... | ⚪ STANDBY | ✅ APPROVED |
| **L6** | Pixel 10 Pro XL (Tensor G5 Edge TPU) | 16.0GB / 12.5GB | Google Tensor G5 (Edge TPU, UW... | 📦 `qwen2.5-0.5b-instruct-q4_k_m.gguf` | 8K Vision Stream, Spatial Grappling Kinematics & Edge Speech/VLA: Ultra-fast multimodal frame bounding-box predictio... | 🟢 78.70 ms | ✅ APPROVED |
| **L7** | Samsung Galaxy S20 (Automated UI Tester) | 12.0GB / 9.0GB | Samsung Exynos 990 (Dedicated ... | 📦 `smollm2-135m-instruct-q4_k_m.gguf` | Continuous UI Regression, ADB Monkey Testing & Screen Verification: Ultra-compact UI test step parser, crash dump summ... | 🟢 86.13 ms | ✅ APPROVED |
| **GW** | GL.iNet Beryl AX Router (GL-MT3600BE) | 0.5GB / 0.0GB | MediaTek MT7981B (OpenWrt Linu... | 📥 DL_QUEUE `StorySupra-10M / Tiny-LLM (Micro Rule Engine)` | Core Gateway, Hardware USB ADB Bridge & Wake-on-LAN Hub (Port 18802): Network ping anomaly triage, multi-WAN failover de... | 🟢 6.25 ms | ✅ APPROVED |

---

## 🛠️ 2. Detailed Per-Device Operational Profiles & Optimizations

### L1: Mac Mini M4 Pro (Mac_Node)
- **Physical RAM:** 24.0 GB (AI Cap: 21.6 GB)
- **Compute Engine:** Apple M4 Pro (12-core CPU, 16-core GPU, Metal MPS)
- **IP Configuration:** Local `192.168.8.230` | Tailscale `100.119.199.76`
- **Primary Network Role:** Primary Host, Memory Governor & Prompt Ingestion
- **Assigned Edge Student Model:** `qwen2.5-0.5b-instruct-q4_k_m.gguf`
- **Specialized Model Purpose:** Sub-10ms AST parsing, prompt triage, and memory governor auditing
- **Live Connectivity Probe:** `ONLINE (LOCAL HOST)` (RTT: 0.01 ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** Preserves >= 9.6 GB physical RAM host sanctuary under Rule 7.1

### L2: MacBook Pro M4 (Metal RPC)
- **Physical RAM:** 16.0 GB (AI Cap: 14.0 GB)
- **Compute Engine:** Apple M4 (10-core CPU, 10-core GPU, 10Gbps TB4 DMA)
- **IP Configuration:** Local `192.168.8.127` | Tailscale `100.103.212.21`
- **Primary Network Role:** Metal GPU RPC Worker & 285 GB SSD Model Vault
- **Assigned Edge Student Model:** `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`
- **Specialized Model Purpose:** High-throughput C11/Rust tensor compilation & 80B model sharding cache
- **Live Connectivity Probe:** `REACHABLE` (RTT: 165.236 ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** 0.277ms RTT over 10Gbps Thunderbolt 4 bridge

### L3: Linux Head Node (Ryzen 7)
- **Physical RAM:** 16.0 GB (AI Cap: 13.8 GB)
- **Compute Engine:** AMD Ryzen 7 5700U (8C/16T, Docker Hub, Apache Ray)
- **IP Configuration:** Local `192.168.8.224` | Tailscale `100.101.39.98`
- **Primary Network Role:** Gateway Ingress, Petals DHT Bootstrap & PySpark Lakehouse
- **Assigned Edge Student Model:** `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`
- **Specialized Model Purpose:** Continuous log summarization, Docker container triage & Petals block routing
- **Live Connectivity Probe:** `STANDBY / OFFLINE` (RTT: None ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** Dynamic RAM governor cap: 80% (13.8 GB)

### L4: Linux Tablet (Debian Touch)
- **Physical RAM:** 8.0 GB (AI Cap: 6.5 GB)
- **Compute Engine:** ARM64 / x86 Low-Power Debian (Touchscreen DSP)
- **IP Configuration:** Local `DHCP` | Tailscale `100.81.92.125`
- **Primary Network Role:** Mobile Linux Compute, Bedside Touch DSP & Polysomnography
- **Assigned Edge Student Model:** `SmolLM2-360M-Instruct-Q4_K_M.gguf`
- **Specialized Model Purpose:** Lightweight 512Hz Pan-Tompkins QRS anomaly explanation and bedside UI feedback
- **Live Connectivity Probe:** `STANDBY / OFFLINE` (RTT: None ms)
- **Human Sovereign Verification:** `PENDING_HUMAN_VERIFICATION`
- **Verification Notes:** Pending human touch test verification on bedside dock

### L5: MacBook Air M4 (Secondary Metal)
- **Physical RAM:** 16.0 GB (AI Cap: 14.0 GB)
- **Compute Engine:** Apple M4 (Metal Performance Shaders, JupyterLab Port 8889)
- **IP Configuration:** Local `192.168.8.222` | Tailscale `100.93.158.96`
- **Primary Network Role:** Secondary Metal Worker & Dedicated Continuous LoRA Distillation
- **Assigned Edge Student Model:** `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`
- **Specialized Model Purpose:** Continuous MLX/TRL LoRA training pair backpropagation & notebook execution
- **Live Connectivity Probe:** `STANDBY / OFFLINE` (RTT: None ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** Dynamic RAM governor cap: 90% (14.0 GB)

### L6: Pixel 10 Pro XL (Tensor G5 Edge TPU)
- **Physical RAM:** 16.0 GB (AI Cap: 12.5 GB)
- **Compute Engine:** Google Tensor G5 (Edge TPU, UWB 3D Positioning, 8K Video)
- **IP Configuration:** Local `DHCP (USB ADB 5B080DLCQ001LQ)` | Tailscale `100.73.38.87`
- **Primary Network Role:** 8K Vision Stream, Spatial Grappling Kinematics & Edge Speech/VLA
- **Assigned Edge Student Model:** `qwen2.5-0.5b-instruct-q4_k_m.gguf`
- **Specialized Model Purpose:** Ultra-fast multimodal frame bounding-box prediction and ShowUI execution
- **Live Connectivity Probe:** `REACHABLE` (RTT: 78.705 ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** USB ADB + Termux keepalive whitelist verified

### L7: Samsung Galaxy S20 (Automated UI Tester)
- **Physical RAM:** 12.0 GB (AI Cap: 9.0 GB)
- **Compute Engine:** Samsung Exynos 990 (Dedicated Automated Testing Target)
- **IP Configuration:** Local `DHCP (ADB 100.84.40.95:5555)` | Tailscale `100.84.40.95`
- **Primary Network Role:** Continuous UI Regression, ADB Monkey Testing & Screen Verification
- **Assigned Edge Student Model:** `smollm2-135m-instruct-q4_k_m.gguf`
- **Specialized Model Purpose:** Ultra-compact UI test step parser, crash dump summarizer, and test assertion generator
- **Live Connectivity Probe:** `REACHABLE` (RTT: 86.133 ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** Target of router USB ADB daemon and OpenClaw automated test suites

### GW: GL.iNet Beryl AX Router (GL-MT3600BE)
- **Physical RAM:** 0.5 GB (AI Cap: 0.0 GB)
- **Compute Engine:** MediaTek MT7981B (OpenWrt Linux, Hardware USB Bridge)
- **IP Configuration:** Local `192.168.8.1` | Tailscale `100.122.185.123`
- **Primary Network Role:** Core Gateway, Hardware USB ADB Bridge & Wake-on-LAN Hub (Port 18802)
- **Assigned Edge Student Model:** `StorySupra-10M / Tiny-LLM (Micro Rule Engine)`
- **Specialized Model Purpose:** Network ping anomaly triage, multi-WAN failover decision, and WoL packet generation
- **Live Connectivity Probe:** `REACHABLE` (RTT: 6.247 ms)
- **Human Sovereign Verification:** `APPROVED by Aaron`
- **Verification Notes:** Hardware USB daemon provides out-of-band recovery for Android layers

---

## 🛡️ 3. Continuous Self-Healing & Role Optimization Directives

1. **Autonomous Rebalancing (`continuous-mesh-self-optimizer`):** If any node experiences memory saturation or thermal throttling, its student model is scaled down (e.g. 1.5B -> 360M -> 135M -> 10M).
2. **Zero-Mock Verification Gate:** Ping RTTs and model SHA256 checksums must originate from live physical execution.
3. **Human Sovereign Override (`/grill-me`):** Aaron may set `human_verified: true` or reassign device roles via the Marimo Port 4002 Approval Banner.
