---
title: "Lauburu Known Incidents, Root Cause & Autonomous Healing Knowledge Base 2026"
tags: [incidents, self_healing, knowledge_base, lora, root_cause, mesh_health]
---

# 🛡️ Lauburu Known Incidents & Autonomous Self-Healing Knowledge Base (2026)

> **Autonomous Learning Invariant:** Every network, memory, or GPU contention event ever discovered is permanently cataloged, converted into a high-density LoRA instruction pair, and equipped with an automated self-healing remediation daemon.

## 1. 📋 Master Incident & Remediation Catalog

### ⚠️ `INC-001-RAM-GPU-CONTENTION`: Apple Silicon Unified Memory & WindowServer GPU Contention
* **Symptoms:** Multiple duplicate llama-server instances (≥4) and runaway TUI loops causing Wired RAM to spike >14GB, free RAM <200MB, WindowServer 60Hz stutter, and terminal UI lag.
* **Root Cause:** Uncoordinated parallel model spawning without dynamic VRAM lock checks, exhausting macOS WindowServer render compositor buffers.
* **Automated Self-Healing Actions:**
  1. Run `ps aux | grep llama-server` and count active processes.
  2. If active llama-server instances > 3 or wired RAM > 12GB, kill orphaned and non-primary instances.
  3. Enforce maximum 2 active concurrent inference ports on Mac Mini (Primary: 8085, Sharded: 8081).
  4. Prune runaway Python textual TUI event loops pegging CPU >80%.
* **LoRA Distillation Instruction:**
  > **Prompt:** *"Diagnose and resolve macOS WindowServer UI stuttering, mouse lag, and high Wired RAM on an Apple Silicon M4 Pro Mac Mini hosting local LLMs."*
  > **Learned Protocol:** *"1. Execute `ps aux | grep llama-server` to inspect active inference servers.
2. Terminate orphaned instances with `pkill -f '<model_name>'`.
3. Verify..."*

---

### ⚠️ `INC-002-ROUTER-512MB-OOM`: OpenWrt 512MB Router Kernel OOM Crash on Heavy GGUF Load
* **Symptoms:** GL.iNet travel router stops routing Wi-Fi packets, drops SSH, and triggers kernel panic when running local AI.
* **Root Cause:** Attempting to load a standard Q4_K_M 1B model (770MB) onto a router with only 512MB physical RAM.
* **Automated Self-Healing Actions:**
  1. Restrict on-router native SLM weights to <=240MB RAM (SmolLM2 360M Q4_K_M or Qwen 0.5B IQ3_XXS).
  2. Enable OpenWrt `zram-swap` kernel compression.
  3. Offload all models >=1B to L3 Linux Node or L1 Mac Mini via GGML-RPC socket.
* **LoRA Distillation Instruction:**
  > **Prompt:** *"Configure local AI inference on an OpenWrt router with only 512MB total RAM without crashing the network stack."*
  > **Learned Protocol:** *"1. Deploy SmolLM2 360M Instruct (220 MB RAM footprint) with `-c 512`.
2. Install `zram-swap` via `opkg install zram-swap` to provide virtual compresse..."*

---

### ⚠️ `INC-003-TB4-DMA-SOCKET-HANG`: Thunderbolt 4 10Gbps Bridge Socket Stale Lock
* **Symptoms:** Inter-node RPC tensor latency spikes from 0.204ms to >50ms or drops connection between Mac Mini and MacBook Pro.
* **Root Cause:** Thunderbolt DMA IP interface `169.254.187.138` stale ARP cache or sleeping display sleep state on target MacBook Pro.
* **Automated Self-Healing Actions:**
  1. Pulse Line 1 Bluetooth Proximity Wake (`blueutil --connect 2c-ca-16-08-c0-27`, zero IP dependency) to awaken sleeping MacBook Pro radio hardware.
  2. Send Line 2 Out-of-Band UDP Wake-on-LAN Magic Packet via Port 18802.
  3. Ping 169.254.187.138 with 1-second timeout; trigger `arp -d 169.254.187.138` if packet loss > 0%.
  4. Restart `llama-rpc-server` on MacBook Pro via SSH.
* **LoRA Distillation Instruction:**
  > **Prompt:** *"Troubleshoot and restore sub-millisecond tensor latency on a 10Gbps Thunderbolt 4 bridge between macOS nodes."*
  > **Learned Protocol:** *"1. Pulse Line 1 Bluetooth Proximity Wake: `blueutil --connect 2c-ca-16-08-c0-27`.
2. Dispatch Line 2 Wake-on-LAN magic packet to MacBook Pro MAC addre..."*

---
