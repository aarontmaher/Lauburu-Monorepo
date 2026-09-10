---
title: "Pixel 10 Pro XL Screen Lens Sovereign Hardware & Agent Audit"
date: 2026-09-05
tags: [pixel10proxl, screen_lens, audit, tensor_g5, termux, proot, agy, zero_mock]
---

# 📱 Pixel 10 Pro XL Screen Lens Sovereign Hardware & Agent Audit

**Device Node:** Layer 6 Mobile Edge Worker (`100.73.38.87` / `Pixel_10_Pro_XL`)  
**Audit Protocol:** Screen Lens Live Perception + Authentic Kernel Syscalls + Termux OpenSSH  
**Verification Level:** Rule #0 Strict Zero-Mock & Truth Verification  

---

## 🏛️ 1. Empirical Hardware Architecture & Micro-Topography

| Component | Verified Kernel Specification | Notes |
| :--- | :--- | :--- |
| **Model / Codename** | `Pixel 10 Pro XL` / `mustang` | Google Flagship Reference Device |
| **SoC / Silicon** | **Google Tensor G5** (`laguna`) | 3nm TSMC Architecture |
| **CPU Cluster** | **8 Physical Cores (Tri-Cluster)**<br>• 1x Cortex-X4 Prime Core @ **3,782 MHz** (3.78 GHz)<br>• 5x Cortex-A725 Mid Cores @ **3,052 MHz** (3.05 GHz)<br>• 2x Cortex-A520 Efficiency Cores @ **2,246 MHz** (2.25 GHz) | Hardware scaling: 23% - 72% active load |
| **ISA Extensions** | `armv9.2-a`, `sve`, `sve2`, `i8mm`, `svei8mm`, `bf16`, `svebf16`, `asimddp`, `sha3`, `sha512` | Native INT8 matrix multiplication (`i8mm`) and Bfloat16 support |
| **Security Module** | **Titan-M2** Hardware StrongBox Keymaster | `ro.strongbox.model: Titan-M2` |
| **Memory (RAM)** | **15.0 GiB LPDDR5X Unified Memory**<br>• Used: 11.0 GiB (System + PRoot + LLM)<br>• Buffer/Cache: 3.3 GiB<br>• Available Headroom: ~4.0 GiB | Dynamic memory governor active |
| **ZRAM / Swap** | **7.6 GiB ZRAM Pool** (5.2 GiB active swap) | In-RAM compressed block device |
| **Storage (UFS)** | **467 GiB UFS 4.0** (`3c400000.ufs`)<br>• Free Headroom: **188 GiB** available | High-speed model weights storage |

---

## ⚡ 2. Battery Health & Thermal Telemetry

Authentic readings captured via `termux-battery-status` and Darwin/Linux sysfs:

```json
{
  "present": true,
  "technology": "Li-ion",
  "health": "GOOD",
  "plugged": "UNPLUGGED",
  "status": "DISCHARGING",
  "temperature_celsius": 27.7,
  "voltage_mv": 4108,
  "current_ua": -2202343,
  "percentage": 77,
  "charge_cycle": 94
}
```

- **Operating Temperature:** **27.7°C** — Thermal state is nominal and ice-cool. Zero thermal throttling observed across Cortex-X4 and A725 clusters.
- **Battery Headroom:** **77% (4.11 V)** with only **94 lifetime charge cycles**.
- **Discharge Current:** ~2.2 A during active PRoot container execution and multi-agent coordination.

---

## 🌐 3. Multi-Interface Network Mesh Topology

Captured via authentic link-layer socket inspection:

| Interface | IP Address | Subnet Mask | Protocol Role |
| :--- | :--- | :--- | :--- |
| **`tun0`** | `100.73.38.87` | `255.255.255.255` | **Tailscale WireGuard Mesh** (0% loss, ~52ms peer latency) |
| **`ap_br_wlan2`** | `172.20.132.154` | `255.255.255.0` | **Wi-Fi Hotspot Bridge** (Local mesh tethering ingress) |
| **`avf_tap_fixed`** | `172.23.74.95` | `255.255.255.0` | **Android Virtualization Framework** tap device |
| **`v4-rmnet16`** | `192.0.0.4` | `255.255.255.255` | **Cellular WAN Data Link** (Emergency ISP failover) |
| **`lo`** | `127.0.0.1` | `255.0.0.0` | Localhost loopback |

---

## 🧠 4. Active Daemons & Sovereign Multi-Agent Subsystem

1. **Termux Service Supervisor (`runsvdir`):**
   - Supervising `sshd` (Port 8022, PID 15562)
   - Supervising `ssh-agent`
   - Supervising `dockerd` (Daemon ready)

2. **Distributed llama.cpp Tensor Worker:**
   - Command: `/data/data/com.termux/files/home/llama.cpp/build/bin/ggml-rpc-server -H 0.0.0.0 -p 50052 -t 8` (PID 31041)
   - Dedicated Port: `50052`
   - Tensor Sharding Target: 8 CPU threads utilizing ARMv9.2 `i8mm` acceleration.

3. **Autonomous Antigravity Subagent (`agy`) in PRoot Ubuntu:**
   - Command: `/root/.local/bin/agy --dangerously-skip-permissions -c` (PID 1139)
   - RSS Memory: 1.6 GB (10% of physical RAM)
   - Model Orchestrator: Gemini 3.8 Flash (High reasoning)
   - **Screen Lens Active Intervention:**
     Screen Lens visual audit detected the subagent was blocked at an interactive CLI feedback modal (`How's the CLI experience so far? [1] Good [2] Fine [3] Bad [0] Skip`).
     Screen Lens dispatched automated keypress `0` (Skip), unblocking the subagent. The subagent immediately resumed running network discovery probes (`ssh mac whoami`, `ip route show`) across the Lauburu mesh.

---

## 🔗 5. Inter-Device Linkage & Tri-Vault Synchronization

- **Obsidian Vault Index:** Linked in `[[Index]]` and `[[APPS_AND_FEATURES]]`.
- **Screen Lens Live Stream:** Continuously broadcasting on `http://localhost:4003/stream.mjpg`.
- **VLA Training Dataset:** Continuous observation records appended to `lora_datasets/proven_accuracy_vla_dataset.jsonl`.
