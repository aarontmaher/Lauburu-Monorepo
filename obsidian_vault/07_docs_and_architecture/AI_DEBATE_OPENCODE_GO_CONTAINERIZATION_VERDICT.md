---
title: "AI Debate: OpenCode Go Project Foundation & Containerization Verdict"
date: "2026-09-11"
tags: [ai_debate, opencode, go, containerization, docker, bluetooth, host_sanctuary, zero_mock]
consensus_score: 1.00
lead_orchestrator: "Gemini 3.8 Flash / Claude Fable 5.1 / GPT-6 Astra / Qwen 3.8 Max"
---

# 🧠 Live AI Debate: Should OpenCode Go Be Containerised?

- [[Index]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
- [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- [[OPENCODE_GO_BLUETOOTH_TERMINAL_UPDATE]]
- [[AI_DEBATE_OPENCODE_BLUETOOTH_TERMINAL_AND_QWEN_REDTEAM]]

---

## 🏛️ 1. The Core Architectural Question

> **Question:** *"Review the OpenCode Go project foundation. Should we containerise it so it contains all project dependencies?"*

---

## ⚖️ 2. Unanimous AI Debate Verdict

### **VERDICT: NO (100% Unanimous Consensus across All Orchestrators)**

OpenCode Go should **NOT** be containerised as its primary distribution or development form. 

The primary artifact MUST remain a set of **statically compiled native binaries** (`darwin/arm64`, `darwin/amd64`, `android/arm64-pie`, `linux/amd64`). An OCI container image is approved **strictly as an optional, secondary artifact scoped solely to headless server/bridge deployments on L3 (Linux Head Node)**.

---

## 🔬 3. Deep Architectural Analysis & Disqualifying Constraints

Containerising OpenCode Go violates three independent physical system invariants:

```
┌────────────────────────────────────────────────────────────────────────┐
│               WHY CONTAINERIZATION FAILS FOR OPENCODE GO               │
├────────────────────────────────────────────────────────────────────────┤
│ 1. HARDWARE SEVERANCE (macOS VM Boundary)                              │
│    • CoreBluetooth, /dev/tty.Bluetooth-Incoming-Port, and Mach vm_stat │
│      CANNOT pass through Docker Desktop's Linux VM on Darwin.          │
├────────────────────────────────────────────────────────────────────────┤
│ 2. HOST RAM SANCTUARY VIOLATION (Rule 3)                               │
│    • Docker Desktop VM consumes 4.0 - 8.0 GB wired RAM.                │
│    • Mac Mini Host (24 GB) MUST preserve >= 4.8 GB physical headroom. │
│    • Native Go binary consumes only 20 - 45 MB RAM (99.5% savings).    │
├────────────────────────────────────────────────────────────────────────┤
│ 3. TARGET INFEASIBILITY (Android L6 & L7)                              │
│    • Stock unrooted Android 15 (Pixel 10 Pro XL & Samsung Galaxy S20)  │
│      lacks cgroups/namespaces. Standard Docker cannot run.             │
│    • Native static PIE binary runs natively on Android Bionic libc.    │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Hardware Access is the Core Product
1. **CoreBluetooth on macOS Darwin (L1 & L2):**
   - CoreBluetooth is a Darwin userspace framework communicating via XPC/Mach IPC with `bluetoothd`.
   - Docker Desktop on macOS runs containers inside an Apple Virtualization Linux VM. Inside that VM, there is no Darwin kernel, no IOKit, no `bluetoothd`, and no XPC.
   - Docker Desktop **does not support USB/HCI Bluetooth passthrough**. The Linux backend of `tinygo.org/x/bluetooth` (BlueZ) finds no Bluetooth controller in the container.
   - **Result:** BLE NUS (Nordic UART Service) is completely unreachable from a macOS container.
2. **Serial & RFCOMM SPP (`/dev/tty.Bluetooth-Incoming-Port`):**
   - These device nodes are created by Darwin IOKit on the host. Bind-mounting `--device` in Docker Desktop operates on the *VM's* `/dev`, which does not see macOS serial ports.
3. **Darwin Kernel Profiling (`vm_stat`, Mach Memory, Battery):**
   - OpenCode Go monitors host health to enforce Rule 3. Inside a container, `vm_stat` or `/proc/meminfo` queries the *Linux VM guest*, not the Mac Mini host, rendering the telemetry false and violating Rule 0.

### 3.2 Memory Footprint vs. Host Sanctuary Invariant (Rule 3)
- **Docker Desktop on Mac:** Allocates a wired, resident Linux VM taking **4,096 MB to 8,192 MB** of host RAM.
- **Mac Mini Host Budget:** 24 GB Unified Memory. With local models, IDE, and OS, running Docker Desktop pushes free RAM below the mandatory **4.8 GB** sanctuary threshold.
- **Native Go Binary:** Consumes **20 to 45 MB RSS**.
- **Conclusion:** Native Go is **$100\times$ more memory-efficient** and preserves the Host Sanctuary Invariant.

### 3.3 Android Edge Target Infeasibility (L6 Pixel 10 Pro XL & L7 Samsung S20)
- Android 15 disables or restricts unprivileged cgroups v2, overlayfs, and network namespaces. Docker cannot run in Termux on stock Android without rooting.
- Native Go compiles with `CGO_ENABLED=0 GOOS=android GOARCH=arm64 -buildmode=pie` into a self-contained PIE binary that runs with zero dependencies on Android Bionic.

### 3.4 The Go Static Compilation Advantage
Containers were invented to solve "dependency hell" in interpreted or dynamically-linked ecosystems (Python, Node, Ruby, complex C++ shared objects).
Go already solves this at compile time:
- **Zero Runtime Dependencies:** Go packages all code, standard library, and vendored dependencies into a single static Mach-O / ELF binary.
- **Sub-10ms Startup:** Native Go boots in $<10\text{ ms}$; a container boots in $1.5 - 3.5\text{ s}$.
- **Direct Terminal Integration:** Native Go binds directly to terminal raw mode, ANSI escape code streams, and window resize signals (`SIGWINCH`) without PTY bridging shims.

---

## 🏗️ 4. Recommended Architectural Foundation

```
┌────────────────────────────────────────────────────────────────────────┐
│               CANONICAL OPENCODE ARTIFACT DISTRIBUTION                 │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 1: PRIMARY ARTIFACTS (Native Static Multi-Arch Binaries)          │
│ • darwin/arm64:  Mac Mini M4 Pro (L1) & MacBook Pro (Node L2) (L5)            │
│ • darwin/amd64:  MacBook Pro Intel (L2)                                │
│ • android/arm64: Pixel 10 Pro XL (L6) & Samsung Galaxy S20 (L7)        │
│ • linux/amd64:   Linux Mini (L3) & Linux Tablet (L4)                   │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 2: SECONDARY ARTIFACT (Headless OCI Microservice Container)       │
│ • Target: L3 Linux Mini (Docker Hub & Apache Ray Cluster)              │
│ • Role: Headless background daemon (`lauburu --bt-daemon` or `serve`)  │
│ • Base: `FROM scratch` or `FROM alpine:latest` (Static binary copy)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ 5. AI Debate Consensus Agreement

- **Cloud Frontier Architect (Gemini 3.8 Flash):** Agreed (1.0). Preserves zero-dependency static Go simplicity.
- **Anthropic Claude Fable 5.1:** Agreed (1.0). Proved hardware severance on macOS VM boundary.
- **OpenAI GPT-6 Astra:** Agreed (1.0). Confirmed containerization boundary opposes host integration.
- **Sovereign Master Local Orchestrator (Qwen 3.8 Max):** Agreed (1.0). Enforced Mac Mini Host RAM Sanctuary veto.
- **Devil's Advocate / Red Team:** Agreed (1.0). Scoped containerization strictly to L3 headless Linux worker.
- **Consensus Score:** **`1.00 (Unanimous)`**
