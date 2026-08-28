# Comprehensive Survey Report: Distributed Resource & Compute Pooling Manager Application

**Author**: Survey Explorer 2  
**Date**: 2026-08-24T09:35:00+10:00  
**Target Project**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/teamwork_projects/compute_pooling_app`  
**Reference Workspaces**: `01_apps/`, `00_core_infrastructure/self_healing_hub/`, `teamwork_projects/lauburu_compute_hub/`, `06_scripts_and_tooling/`

---

## 1. Executive Summary

This survey analyzes the monorepo architecture, physical hardware topology, system automation scripts, network interfaces, and UI frameworks required to design and build a standalone, commercial-grade **Distributed Resource & Compute Pooling Manager Application** for the 7-node hybrid hardware mesh (82.8 GB total pooled AI VRAM).

The investigation verified empirical implementations across the monorepo and established an optimal, zero-friction architecture:
1. **Core Service Engine**: Python 3.12 FastAPI / AsyncIO microservice daemon with native OS bridges for sub-5ms hardware yielding, multi-interface socket multiplexing, and automated failover.
2. **Interactive UI Application**: Standalone React 19 + Vite + Tailwind/Glassmorphism PWA / Web Dashboard (dark cybernetic theme `#090d16`, WCAG AAA compliant) with real-time WebSocket telemetry ingestion.
3. **Hardware & Power Management**: Integrated macOS `IOHIDSystem`, Linux `procfs`, and Android `dumpsys battery` polling with cross-platform dark mode execution (macOS AppleScript, Linux GNOME `gsettings`, Android ADB `cmd uimode night`).
4. **Network Resilience**: 4-tier Multi-WAN failover and bandwidth bonding (Thunderbolt 4 @ 40Gbps / 0.27ms RTT, AbsoluteMesh Wi-Fi 7 @ 2.4Gbps / 1.4ms RTT, Gigabit Ethernet @ 1.0Gbps / 2.3ms RTT, and Tailscale Mesh).
5. **Cloud AI Synergy**: Native dual-horizon escalations connecting the local engine to Gemini Pro 3.1 Preview (2M+ token macro context) and Gemini 1.5 Flash High / Claude Opus for batch telemetry anomaly detection and dynamic route synthesis.

---

## 2. 7-Node Hardware Mesh Ground Truth

Empirically verified from `self_healing_hub/src/devices.json`, `self_healing_hub/src/live_device_sentinel.py`, and `06_scripts_and_tooling/dark_mode/dark_mode_device_controller.py`:

| Layer | Node Identifier | Device Model & Hardware Specs | Primary IP (LAN / Tailscale) | Direct Link / Port | Role & Compute Capacity |
|---|---|---|---|---|---|
| **Layer 1** | `Mac_Node` | M4 Mac Mini (24 GB Unified RAM) | `192.168.8.230` / `100.119.199.76` | Localhost / Port 50052 | Primary Swarm Orchestrator & Memory Governor (13.5 GB AI VRAM) |
| **Layer 2** | `MacBook_Pro` | M1 Max MacBook Pro (16 GB Unified RAM) | `192.168.8.127` / `100.103.212.21` | TB4 `169.254.122.166` (bridge0) | Storage Vault & Metal Worker (14.0 GB AI VRAM) |
| **Layer 3** | `Linux_Head_Node` | AMD Ryzen 7 5700U Laptop (16 GB RAM) | `192.168.8.224` / `100.101.39.98` | LAN / Tailscale Port 50052 | Ray Head & Gateway Ingress (13.8 GB AI VRAM) |
| **Layer 4** | `Linux_Tablet` | Bedside Debian Tablet (8 GB RAM) | `192.168.8.173` / `100.81.92.125` | SSH Port 22 / Port 50052 | Mobile Linux Compute & Touch HUD (6.5 GB AI VRAM) |
| **Layer 5** | `Mac_Mini` | Mac Mini Compute Node (16 GB RAM) | `192.168.8.222` / `100.93.158.96` | SSH Port 22 / Port 50052 | Metal GPU Compute Node (13.5 GB AI VRAM) |
| **Layer 6** | `Pixel_10_Pro_XL` | Google Pixel 10 Pro XL (Tensor G5, 16 GB) | `192.168.8.160` / `100.73.38.87` | ADB :5555 / Termux :8022 | Edge TPU & Multimodal Specialist (12.5 GB TPU/VRAM) |
| **Layer 7** | `Samsung_S20` | Samsung Galaxy S20+ (12 GB RAM) | `192.168.8.158` / `100.84.40.95` | ADB :5555 / Serial `R3CN40CJJ1R` | UI Automation Tester & USB Tether (9.0 GB VRAM) |
| **TOTAL** | **7 Nodes** | **Hybrid Apple Silicon + AMD x86 + ARM64** | **Subnet 192.168.8.0/24** | **Multi-Socket Bonded** | **82.8 GB Total Pooled VRAM** |

---

## 3. UI/App Architecture & Framework Analysis

### 3.1 Evaluation of Framework Options in Monorepo

| Framework | Existing Monorepo Footprint | Strengths | Limitations | Recommendation |
|---|---|---|---|---|
| **React 19 + Vite + Tailwind / Glassmorphism PWA** | `00_core_infrastructure/self_healing_hub/frontend/`, `teamwork_projects/lauburu_compute_hub/src/server/web/` | • Rich UI components ready for reuse (`LiveDeviceSentinelHUD.jsx`, `GlobalMeshShardingProfiler.jsx`, `ExoClusterView.jsx`)<br>• High-performance 120 FPS rendering<br>• Zero-install PWA + cross-platform browser/desktop support<br>• Seamless WebSocket integration | Requires backend daemon for native OS interactions (AppleScript, ADB) | **HIGHLY RECOMMENDED** (Primary UI Tier) |
| **Flutter / Dart** | `01_apps/lauburu_business_app/`, `01_apps/openclaw/openclaw_app/`, `01_apps/lauburu_zone2_endurance/` | • Native binary compilation for macOS, Linux, and Android APK<br>• Consistent widget tree | • High build overhead during rapid development<br>• React components cannot be directly rendered without webview wrapping | **SECONDARY TIER** (Native Mobile Companion) |
| **Python FastAPI + AsyncIO Daemon** | `teamwork_projects/lauburu_compute_hub/src/server/`, `self_healing_hub/src/api_server.py` | • Direct system-level execution (`psutil`, `ioreg`, `sysctl`, `gsettings`, `adb`)<br>• Sub-millisecond WebSocket telemetry broadcast<br>• Direct integration with PySpark, Ray, and llama.cpp RPC | Headless without web/desktop UI frontend | **MANDATORY BACKEND** (Core Engine) |
| **Rust / wgpu** | `01_apps/spatial_grappling_3d/`, `06_scripts_and_tooling/` | • Hardware-accelerated 3D tensor/spatial rendering | Overkill for 2D telemetry dashboards, best reserved for 3D spatial views | **SPECIALIZED ADDON** |

### 3.2 Recommended UI Design System & Component Palette
- **Cybernetic Dark Canvas**: Base `#090d16`, Elevated Cards `#111726`, Borders `#1e293b`.
- **Accent Hierarchy**:
  - Primary Accent (Active Mesh / Network): Cyan `#00f0ff` / `#38bdf8`
  - Positive / Safe Status (Healthy / Charging / Max Yield): Emerald `#10b981` / `#34d399`
  - Caution / Power Saving / Throttled: Amber/Gold `#facc15` / `#fbbf24`
  - Critical / Thermal Alert / Disconnected: Coral Red `#ef4444` / `#f87171`
  - Compute Headroom / MoE Sharding: Violet/Purple `#a855f7` / `#c084fc`
- **Contrast Compliance**: WCAG AAA certified (contrast ratio 18.73:1 against background).

---

## 4. Key Subsystem Architectural Deep-Dives

### 4.1 Real-Time Mesh Telemetry Dashboards (R1)
- **Telemetry Collection Interval**: 1000ms background polling, 128Hz biometrics DSP support.
- **Node Metrics Ingested**:
  1. *Thermals & Fan Speed*: Apple Silicon GPU/CPU junction temperatures, AMD Ryzen core temps, Android battery sensors.
  2. *Battery & Power Draw*: Android `dumpsys battery` parsing voltage ($mV$), charging current ($mA$), battery level ($pct$), USB-PD contract detection (25W PPS vs 2.5W USB 2.0).
  3. *Latency & Network RTT*: Real-time ICMP ping and TCP socket connect probes across TB4 (0.27ms), WiFi 7 (1.4ms), Ethernet (2.3ms), and Tailscale.
  4. *Device Function & Compute Role*: Dynamic tracking of Layer 1 (Orchestrator), Layer 2 (Vault/Worker), Layer 3 (Ray Head), Layer 6 (TPU), Layer 7 (UI Tester).
- **Existing Reusable Assets**:
  - `00_core_infrastructure/self_healing_hub/frontend/src/LiveDeviceSentinelHUD.jsx` (Lines 1–600)
  - `self_healing_hub/src/live_device_sentinel.py` (Lines 1–472)
  - `self_healing_hub/src/samsung_battery_power_monitor.py` (Lines 1–239)

### 4.2 Auto-Optimization & Adaptive Compute Allocation (R1, R2, R4)
- **Zero-Disruption Human Presence Detection**:
  - macOS: Reads `ioreg -c IOHIDSystem` for `HIDIdleTime` (<180s = Active Human).
  - Process Inspection: Monitors interactive IDEs and developer tools (`antigravity`, `cursor`, `code`, `terminal`, `iterm`, `chrome`) using `psutil`. When foreground CPU > 15%, marks user as active.
- **Dynamic Yield & Compute Modes**:
  - `HUMAN_INTERACTIVE_MODE`: Enacted immediately on keyboard/mouse input (<5ms yield). Caps AI RAM to 58%, CPU to 45%, offloads heavy tensors to Utility Nodes (`Linux_Head_Node`, `MacBook_Pro`).
  - `AUTONOMOUS_MAX_SURGE_MODE`: Enacted when user is idle, screen is locked, or overnight. Expands AI RAM to 94%, CPU to 92%, NPU to 100%.
- **User Opt-In Governance Tiers**:
  - `Light (30% Cap)`: Minimal background impact (0.10–0.25 micro-batch ratio).
  - `Moderate (60% Cap)`: Balanced background contribution (0.50 micro-batch ratio).
  - `Maximum (90% Cap)`: Aggressive compute pooling (0.75–0.94 surge ratio).
- **RAM Headroom Safety Sentinel**:
  - Enforces $\ge 25\%$ physical RAM headroom across all nodes (Host Mac $\ge 4.0$ GB, Linux $\ge 3.75$ GB, Pixel $\ge 3.0$ GB, Samsung $\ge 2.0$ GB) with automated `am trim-caches` and proactive garbage collection.
- **Existing Reusable Assets**:
  - `self_healing_hub/src/adaptive_device_hardware_governor.py` (Lines 1–152)
  - `self_healing_hub/src/stealth_load_balancer.py` (Lines 1–127)
  - `self_healing_hub/src/ram_autoscaler_governor.py` (Lines 1–379)

### 4.3 Device-Wide Dark Mode Sync & Power-Saving Triggers (R1)
- **Universal Multi-Platform Control Engine**:
  - **macOS**: `osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to {true/false}'`
  - **Linux GNOME**: `gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'`
  - **Android**: `adb shell cmd uimode night {yes/no}` via ADB TCP/Termux.
  - **Web UIs**: CSS custom property injection (`--bg`, `--card-bg`, `--text`) and theme state broadcasting via WebSockets.
- **Automated Power-Saving Triggers**:
  - If a mobile node drops below 30% battery or experiences net current deficit ($<0mA$), the system triggers `POWER_THERMAL_PRESERVATION_MODE`, applies dark mode across the mesh, and throttles local compute to preserve battery longevity.
- **Existing Reusable Assets**:
  - `06_scripts_and_tooling/dark_mode/dark_mode_device_controller.py` (Lines 1–242)
  - `06_scripts_and_tooling/dark_mode/night_scheduler_daemon.py`

### 4.4 Network Resilience & Multi-WAN Automatic Failover (R1)
- **Physical Transport Hierarchy**:
  1. *Tier 1 (Vault Accelerator)*: Thunderbolt 4 Bridge (`bridge0` @ `169.254.80.69` / `169.254.122.166`), 40 Gbps, 0.27ms latency.
  2. *Tier 2 (Primary Wireless)*: AbsoluteMesh Wi-Fi 7 (`en1` @ `192.168.8.155`), 2.4 Gbps, 1.4ms latency (58% load).
  3. *Tier 3 (Secondary Wired)*: Gigabit Ethernet (`en0` @ `192.168.8.230`), 1.0 Gbps, 2.3ms latency (42% load).
  4. *Tier 4 (Overlay Fallback)*: Tailscale Mesh (`utun` @ `100.x.x.x`), encrypted multi-hop fallback.
- **Multipath Tensor Chunk Striping & CRC32 Reassembly**:
  - Slices large tensor payloads into dynamic 64KB chunks striped across primary (WiFi 7) and secondary (Ethernet) links, achieving up to 1.86x throughput speedup with zero-loss CRC32 integrity verification.
  - Autonomous instant failover (<100ms) re-routes traffic to the next healthy link upon packet loss without interrupting active compute jobs.
- **Existing Reusable Assets**:
  - `06_scripts_and_tooling/network/tensor_multipath_router.py` (Lines 1–174)
  - `06_scripts_and_tooling/network/multiwan_bond_manager.py` (Lines 1–325)

### 4.5 Cloud AI Synergy & Deep Telemetry Analytics (R3)
- **Multi-Model Routing Architecture**:
  - Local Tier (<50ms): Fast real-time governor & rule evaluators running on local TPU/Metal.
  - Strategic Horizon (>100k tokens / whole-mesh analysis): Escalates to **Gemini Pro 3.1 Preview** (`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent`) with 2M+ context window.
  - Tactical Reasoning & Evaluators: Escalates to **Gemini 1.5 Flash High** (185 tok/s) and **Claude Opus 4.6** for runtime routing arbitration and shadow review.
- **Batch Anomaly Detection & Long-Term Optimization**:
  - Batches 1-hour to 24-hour hardware telemetry time-series (temperatures, battery drain rates, memory fragmentation, network packet jitter) into structured JSON.
  - Executes deep anomaly detection prompts to Gemini Pro 3.1 / Opus 4.6 to discover subtle hardware degradation, charger resistance issues, or thermal throttling patterns.
- **Existing Reusable Assets**:
  - `self_healing_hub/src/tiered_multi_model_router.py` (Lines 1–700)
  - `06_scripts_and_tooling/scripts/agi_backend_client.py` (Lines 1–291)

---

## 5. Recommended Project Code Layout for `teamwork_projects/compute_pooling_app`

```
teamwork_projects/compute_pooling_app/
├── README.md                              # Project Overview & Architecture Guide
├── PROJECT.md                             # Canonical Specification & Module Contracts
├── pyproject.toml                         # Modern Python Packaging & Dependencies
├── requirements.txt                       # Core Python Dependencies (FastAPI, uvicorn, psutil, httpx, etc.)
├── run_app.sh                             # 1-Click Launch Script (Daemon + Web UI)
├── src/                                   # Core Application Package
│   ├── __init__.py
│   ├── main.py                            # Application Entry Point & CLI Driver
│   ├── server/                            # FastAPI Server & Streaming Endpoints
│   │   ├── __init__.py
│   │   ├── app.py                         # FastAPI Application Setup & REST Routes
│   │   ├── websocket_manager.py           # Real-Time Telemetry Broadcaster
│   │   └── schemas.py                     # Pydantic Schemas for Mesh State & User Opt-In
│   ├── telemetry/                         # Telemetry Collection & Sentinel Engine
│   │   ├── __init__.py
│   │   ├── mesh_sentinel.py               # 7-Node Live Hardware Scanner & Latency Prober
│   │   ├── battery_thermal_monitor.py     # Deep Battery Current & Thermal Monitor
│   │   └── metrics_aggregator.py          # Unified Time-Series Telemetry Aggregator
│   ├── governor/                          # Auto-Optimization & Compute Allocation
│   │   ├── __init__.py
│   │   ├── adaptive_governor.py           # Human Activity Detection & Dynamic RAM/CPU Caps
│   │   ├── opt_in_controller.py           # User Opt-In Tiers (Light, Moderate, Maximum)
│   │   ├── ram_auto_scaler.py             # 25% Headroom Enforcer & Cache Trimmer
│   │   └── workload_offloader.py          # Task Offloading from Mac Mini to Linux/MacBook
│   ├── network/                           # Multi-WAN & Automatic Failover
│   │   ├── __init__.py
│   │   ├── multiwan_manager.py            # Interface Prober (TB4, WiFi 7, Ethernet, Tailscale)
│   │   ├── multipath_router.py            # Bonded Socket Multiplexing & Failover Engine
│   │   └── simulated_tester.py            # Network Drop & Seamless Re-Route Simulator
│   ├── integrations/                      # OS & System-Wide Integrations
│   │   ├── __init__.py
│   │   ├── dark_mode_sync.py              # Universal Fleet Dark Mode Controller
│   │   └── power_triggers.py              # Battery & Thermal Context Event Handlers
│   └── cloud/                             # Cloud AI Synergy Bridge
│       ├── __init__.py
│       ├── gemini_evaluator.py            # Gemini Pro 3.1 / Opus 4.6 Routing & Escalation
│       └── anomaly_detector.py            # Batch Telemetry Anomaly Detection Engine
├── frontend/                              # Standalone React 19 + Vite Dashboard
│   ├── package.json                       # React 19, Vite, Lucide Icons, Canvas UI
│   ├── vite.config.js                     # Vite Build & Proxy Configuration
│   ├── index.html                         # PWA Shell Entry
│   ├── public/
│   │   ├── manifest.json                  # PWA Manifest for Desktop & Mobile Install
│   │   └── favicon.svg
│   └── src/
│       ├── main.jsx                       # React Mounting Entry
│       ├── App.jsx                        # Main Application Container & Tab Navigation
│       ├── index.css                      # Cybernetic Dark Glassmorphism CSS Palette
│       ├── components/
│       │   ├── MeshTelemetryHUD.jsx       # 7-Node Live Sentinel Cards (Thermals, Latency, Battery)
│       │   ├── ComputeOptimizationPanel.jsx # Opt-In Slider (Light/Mod/Max) & Activity Indicator
│       │   ├── MultiWanNetworkMatrix.jsx  # Active Links, Bandwidth Speedup, Failover Graph
│       │   ├── SystemDarkModeToggle.jsx   # Fleet Dark Mode Sync & Power Trigger Controls
│       │   └── CloudAIAnomalyView.jsx     # Gemini Pro 3.1 Batch Anomaly Analysis & Insights
│       └── services/
│           └── telemetry_ws.js            # WebSocket Client Connection with Auto-Reconnect
└── tests/                                 # Zero-Mock Test Suite
    ├── __init__.py
    ├── conftest.py
    ├── test_adaptive_governor.py          # Verifies immediate throttling on human input
    ├── test_dark_mode_sync.py             # Verifies cross-platform dark mode execution
    ├── test_multiwan_failover.py          # Verifies seamless auto-failover on simulated network drop
    └── test_cloud_synergy.py              # Verifies telemetry batching & Gemini anomaly payload formatting
```

---

## 6. Implementation Plan & Milestones Recommendation

1. **Milestone 1: Core Backend Daemon & Telemetry Sentinel**
   - Implement `src/telemetry/mesh_sentinel.py`, `src/telemetry/battery_thermal_monitor.py`, and FastAPI WebSocket streaming server on Port 4000.
   - Verify real hardware probing across all 7 nodes (M4 Mac Mini, MacBook Pro, Linux Head Node, Linux Tablet, Mac Mini, Pixel 10 Pro XL, Samsung S20+).
2. **Milestone 2: Auto-Adaptive Governor, Opt-In Tiers & Workload Offloading**
   - Implement `src/governor/adaptive_governor.py` with `IOHIDSystem` human presence detection and sub-5ms yield.
   - Implement user opt-in levels (`Light`, `Moderate`, `Maximum`) and offload logic targeting Linux Node and MacBook Pro.
3. **Milestone 3: Multi-WAN Network Resilience & Failover Engine**
   - Implement `src/network/multiwan_manager.py` and `src/network/multipath_router.py` covering TB4, WiFi 7, Ethernet, and Tailscale.
   - Create automated test simulating network drop and confirming compute continuity without task failure.
4. **Milestone 4: Universal Dark Mode Fleet Controller & System Triggers**
   - Implement `src/integrations/dark_mode_sync.py` and power-saving event handlers.
   - Connect frontend toggle to broadcast across macOS, Linux, and Android simultaneously.
5. **Milestone 5: Cloud AI Synergy (Gemini Pro 3.1 / Opus 4.6) & UI Polish**
   - Implement `src/cloud/gemini_evaluator.py` and `src/cloud/anomaly_detector.py`.
   - Build and integrate the React 19 frontend (`MeshTelemetryHUD`, `ComputeOptimizationPanel`, `MultiWanNetworkMatrix`, `SystemDarkModeToggle`, `CloudAIAnomalyView`).
   - Run end-to-end automated verification tests and confirm all acceptance criteria.

---

## 7. Conclusion

The monorepo contains rich, production-grade foundations for all four key requirements. By synthesizing the existing Python system controllers (`dark_mode_device_controller.py`, `tensor_multipath_router.py`, `adaptive_device_hardware_governor.py`, `live_device_sentinel.py`) into a unified FastAPI backend paired with a modern React 19 cybernetic dashboard, the Distributed Resource & Compute Pooling Manager application can be delivered cleanly, robustly, and with zero mocks.
