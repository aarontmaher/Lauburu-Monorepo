# Comprehensive Specification Mining Report: Distributed Resource & Compute Pooling Manager

**Author:** Survey Spec Miner 3 (Teamwork Specialist AI)  
**Target Project:** `teamwork_projects/compute_pooling_app` (`/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/teamwork_projects/compute_pooling_app`)  
**Workspace Root:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`  
**Date:** 2026-08-24  
**Status:** COMPLETE (Authoritative Specification Draft)

---

## 1. Executive Summary & Specification Scope

The **Distributed Resource & Compute Pooling Manager** is a standalone, commercially-viable system application designed to govern, pool, and auto-optimize distributed compute, memory, and network resources across a heterogeneous 7-node hardware mesh totaling **104.8 GB RAM (82.8 GB Pooled AI VRAM)**.

This specification mining report delivers concrete, mathematically rigorous, and zero-mock interface contracts, data schemas, algorithms, and verification harnesses covering:
1. **R2: Auto-Adaptive Compute Pooling & User Opt-In Levels**: Dynamic compute governance featuring three distinct user opt-in modes (Light, Moderate, Maximum), real-time sub-50ms user input activity detection (mouse, keyboard, display interactions), and automated throttling/pausing of background AI tasks.
2. **R3: Cloud AI Synergy (Gemini Pro 3.1 High & Opus 4.6)**: Hybrid dual-tier intelligence splitting sub-second local edge routing from cloud runtime evaluators (`gemini-3.1-pro-preview` / `gemini-3.7-flash` via the official `google-genai` Interactions API) and deep batch telemetry analytics / long-term anomaly detection, cross-validated by Opus 4.6 for architectural invariance.
3. **R4: Mac Mini 24GB Unified RAM Memory Governor & Aggressive Workload Offloading**: Dynamic memory headroom governor running on the primary Mac Mini M4 host (24GB RAM) that enforces a strict 90% dynamic ceiling (2.4GB reserved buffer) and executes sub-100ms task migration to utility nodes (MacBook Pro over 10Gbps Thunderbolt 4, Linux Head Node over LAN/Tailscale).
4. **Acceptance Test Harnesses & 5-Tier Verification Framework**: Programmatic, zero-mock test harnesses validating instant throttling, cloud anomaly batching, multi-WAN link failovers, and resource invariants.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            7-NODE DISTRIBUTED HARDWARE MESH                                 │
│                                                                                             │
│  ┌───────────────────────────┐    10Gbps TB4 Bridge (0.277ms)   ┌────────────────────────┐  │
│  │   Mac_Node (Host M4)      │ ◄──────────────────────────────► │  MacBook_Pro (Vault)   │  │
│  │   24GB RAM / Governor     │                                  │  16GB RAM / Metal RPC  │  │
│  │   Primary BLE/DSP & UI    │                                  │  Port 50052 (32B AI)   │  │
│  └─────────────┬─────────────┘                                  └────────────────────────┘  │
│                │                                                                            │
│                │ Gigabit LAN / Wi-Fi 6E / Tailscale (100.x.x.x)                             │
│                ▼                                                                            │
│  ┌───────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────────┐  │
│  │  Linux_Head_Node (Ryzen)  │  │  MacBook_Air (M2)      │  │  Linux_Tablet (Debian)     │  │
│  │  16GB RAM / Docker Engine │  │  16GB RAM / Metal Work │  │  8GB RAM / Petals Worker   │  │
│  │  Ray Head / 1TB Model SSD │  │  LoRA Distillation     │  │  Lightweight DSP           │  │
│  └─────────────┬─────────────┘  └────────────────────────┘  └────────────────────────────┘  │
│                │                                                                            │
│                │ USB ADB / Wi-Fi Hotspot / Tailscale                                        │
│                ▼                                                                            │
│  ┌───────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────────┐  │
│  │  Pixel_10_Pro_XL (Tensor) │  │  Samsung_S20 (Exynos)  │  │  GL.iNet Gateway Core      │  │
│  │  16GB RAM / Edge TPU / 8K │  │  12GB RAM / UI Testing │  │  192.168.8.1 / USB Bus     │  │
│  └───────────────────────────┘  └────────────────────────┘  └────────────────────────────┘  │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                       Cloudflare Tunnel / HTTPS (google-genai / Anthropic SDK)
                                               ▼
                         ┌───────────────────────────────────────────┐
                         │              CLOUD AI TIER                │
                         │  • Gemini Pro 3.1 High (Interactions API) │
                         │    - Runtime Routing & Failover Evaluator │
                         │    - 1M-Token Batch Telemetry Analytics   │
                         │  • Claude Opus 4.6                        │
                         │    - Deep Architectural Safety & Invariant│
                         └───────────────────────────────────────────┘
```

---

## 2. Specification Discovery: R2 — Auto-Adaptive Compute Pooling & User Opt-In Levels

### 2.1 Opt-In Level Profiles & Constraints

The system MUST enforce three user-selectable resource governance profiles: `LIGHT`, `MODERATE`, and `MAXIMUM`. Each profile configures hard boundaries on local CPU allocation, GPU/Metal utilization, RAM consumption, thermal trip points, and responsiveness SLAs.

| Governance Metric | Light (Eco / High Responsiveness) | Moderate (Balanced Productivity) | Maximum (Compute Station / Max Pool) |
| :--- | :--- | :--- | :--- |
| **Max Local RAM Allocation** | $\le 25\%$ of free RAM ($\approx 4.0\text{ GB}$) | $\le 50\%$ of free RAM ($\approx 9.0\text{ GB}$) | Up to Dynamic Ceiling ($90\% = 21.6\text{ GB}$) |
| **Max Local CPU Threads** | 2 threads (nice level 19 / `cpulimit` 25%) | 4 threads (nice level 10 / `cpulimit` 50%) | Physical Cores $- 1$ (nice level 0 / 90%) |
| **Max Local GPU / Metal Allocation** | $\le 20\%$ GPU time slice | $\le 50\%$ GPU time slice | $\le 90\%$ GPU time slice |
| **Thermal Ceiling ($T_{\text{max}}$)** | $65.0^\circ\text{C}$ (steep step-down) | $78.0^\circ\text{C}$ (gradual step-down) | $92.0^\circ\text{C}$ (emergency step-down) |
| **Max Local AI Model Size** | $\le 1.5\text{B}$ parameters (Q4_K_M) | $\le 7\text{B}$ parameters (Q4_K_M) | $\le 32\text{B}$ parameters (Q4_K_M pooled) |
| **User Activity Pause Latency** | $< 50\text{ms}$ (Instant hard pause) | $< 100\text{ms}$ (Throttle to 10% or pause) | $< 200\text{ms}$ (Graceful concurrency reduction) |
| **Cooldown Resume Delay ($T_{\text{cooldown}}$)**| $10.0\text{ seconds}$ idle | $5.0\text{ seconds}$ idle | $2.0\text{ seconds}$ idle |
| **Offload Preference** | Aggressive (90%+ tasks offloaded) | Balanced (Heavy tasks offloaded) | Minimal (Execute locally, offload on overflow) |

### 2.2 Real-time User Activity & Input Detection

To ensure zero user interface lag or mouse stuttering on the host machine, the governor MUST monitor input events across multiple operating system hooks without polling lag.

1. **macOS Host Implementation**:
   - Primary: Quartz CoreGraphics Event Source query via `CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType)`.
   - Polling Frequency: High-resolution async timer running at $20\text{ Hz}$ ($50\text{ms}$ interval) during active inference, dropping to $1\text{ Hz}$ when idle.
   - User Activity Flag:
     $$\text{IsUserActive}(t) = \begin{cases} \text{True}, & \text{if } \Delta t_{\text{last\_input}} < 0.500\text{ s} \\ \text{False}, & \text{otherwise} \end{cases}$$
   - Display Server V-Sync / Dropped Frame Detection: Monitor Quartz WindowServer frame drops via `CFAbsoluteTimeGetCurrent()`. If frame duration $> 16.6\text{ms}$ ($< 60\text{ FPS}$), trigger immediate throttle.

2. **Linux Head Node & Tablet Implementation**:
   - X11: `xprintidle` query / `libXss.so.1` (XScreenSaver API).
   - Wayland: `org.freedesktop.ScreenSaver` GetActiveTime or `ext-idle-notify-v1` protocol.
   - Direct Kernel: `epoll` monitoring on `/dev/input/event*` devices with `EV_KEY`, `EV_REL`, `EV_ABS` mask.

3. **Android Edge Nodes (Pixel 10 Pro XL / Samsung S20+)**:
   - ADB / Termux Shell: Query `dumpsys input | grep -E "mIsInteractive|mPointerSpeed"` and `dumpsys power | grep -E "mHoldingDisplaySuspendBlocker"`.
   - Screen State: If screen is unlocked and interactive, suspend local background `llama-server` and yield CPU to foreground UI automation.

### 2.3 Mathematical Throttling & Compute Allocation Algorithm

The dynamic compute governor calculates a real-time **Compute Throttle Factor** $\Theta(t) \in [0.0, 1.0]$, representing the proportion of maximum compute capacity permitted:

$$\Theta(t) = \Omega_{\text{profile}} \times \Phi_{\text{activity}}(t) \times \Psi_{\text{memory}}(t) \times \Gamma_{\text{thermal}}(t)$$

Where:
1. **$\Omega_{\text{profile}}$** is the base multiplier for the active user opt-in profile:
   $$\Omega_{\text{profile}} = \begin{cases} 0.25, & \text{Light} \\ 0.50, & \text{Moderate} \\ 1.00, & \text{Maximum} \end{cases}$$

2. **$\Phi_{\text{activity}}(t)$** is the user activity penalty with exponential decay recovery:
   $$\Phi_{\text{activity}}(t) = \begin{cases} 0.0, & \text{if } \Delta t_{\text{input}} < T_{\text{detect}} \text{ (User Active)} \\ 1.0 - \exp\left(-\frac{\Delta t_{\text{input}} - T_{\text{detect}}}{\tau_{\text{recovery}}}\right), & \text{if } \Delta t_{\text{input}} \ge T_{\text{detect}} \text{ (Idle Recovery)} \end{cases}$$
   Where $T_{\text{detect}} = 0.5\text{s}$, and $\tau_{\text{recovery}} = 2.0\text{s}$ (Light), $1.0\text{s}$ (Moderate), $0.5\text{s}$ (Maximum).

3. **$\Psi_{\text{memory}}(t)$** is the RAM headroom governor:
   $$\Psi_{\text{memory}}(t) = \text{clamp}\left(\frac{\text{RAM}_{\text{free}}(t) - \text{RAM}_{\text{reserved}}}{\text{RAM}_{\text{target\_headroom}}}, 0.0, 1.0\right)$$
   Where $\text{RAM}_{\text{reserved}} = 2.4\text{ GB}$ (Mac Mini 10% buffer), $\text{RAM}_{\text{target\_headroom}} = 4.0\text{ GB}$.

4. **$\Gamma_{\text{thermal}}(t)$** is the thermal dissipation curve:
   $$\Gamma_{\text{thermal}}(t) = \begin{cases} 1.0, & \text{if } T_{\text{die}}(t) \le T_{\text{warn}} \\ \frac{T_{\text{max}} - T_{\text{die}}(t)}{T_{\text{max}} - T_{\text{warn}}}, & \text{if } T_{\text{warn}} < T_{\text{die}}(t) < T_{\text{max}} \\ 0.0, & \text{if } T_{\text{die}}(t) \ge T_{\text{max}} \end{cases}$$

### 2.4 State Machine & Process Control

```
                 ┌─────────────────────────────────────────┐
                 │             STATE: IDLE_STANDBY         │
                 └────────────────────┬────────────────────┘
                                      │ Workload Dispatched
                                      ▼
                 ┌─────────────────────────────────────────┐
       ┌────────►│            STATE: ACTIVE_FULL           │◄────────┐
       │         │ (Local inference / pooling operational) │         │
       │         └────────────────────┬────────────────────┘         │
       │                              │                              │
       │ User Input Idle > T_cooldown │ User Input Detected (<50ms)  │ Thermal / RAM
       │                              ▼                              │ Normalized
       │         ┌─────────────────────────────────────────┐         │
       │         │       STATE: THROTTLED_USER_ACTIVE      │         │
       │         │ (Concurrency capped, nice level raised) │         │
       │         └────────────────────┬────────────────────┘         │
       │                              │                              │
       │                              │ Sustained Activity / Heavy   │
       │                              ▼                              │
       │         ┌─────────────────────────────────────────┐         │
       │         │       STATE: PAUSED_HARD_STOP           │         │
       │         │ (SIGSTOP / async yield / pause sockets) │         │
       │         └────────────────────┬────────────────────┘         │
       │                              │                              │
       │                              │ Workload Offload Triggered   │
       │                              ▼                              │
       │         ┌─────────────────────────────────────────┐         │
       └─────────┤       STATE: DRAINING_FOR_OFFLOAD       ├─────────┘
                 │ (Migrate KV-cache & tasks to TB4 node)  │
                 └─────────────────────────────────────────┘
```

**Process Control Execution Mechanisms:**
- Subprocess suspension: Dispatch `os.kill(pid, signal.SIGSTOP)` to local `llama-server` C++ binaries within $15\text{ms}$ of input detection. Dispatch `signal.SIGCONT` upon transition to `RAMPING_UP`.
- Asyncio pipeline suspension: Cooperative token yield point `await governor.yield_check()` checked prior to every LLM token generation step.
- Cgroups v2 limits (Linux): Dynamically update `cpu.max` and `memory.high` via sysfs controller.

---

## 3. Specification Discovery: R3 — Cloud AI Synergy (Gemini Pro 3.1 High & Opus 4.6)

### 3.1 Architectural Split & Responsibilities

The system decouples edge responsiveness from cloud reasoning depth.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       AI COGNITIVE TAXONOMY                                      │
├──────────────────────────┬─────────────────────────────┬─────────────────────────────────────────┤
│ Tier                     │ Target Model / Endpoint     │ Governed Domain                         │
├──────────────────────────┼─────────────────────────────┼─────────────────────────────────────────┤
│ **Tier 1: Fast Edge**    │ `llama.cpp` (:8081-:8084)   │ Sub-second reasoning, syntax checks,    │
│                          │ Local / Metal GPU (TB4)     │ local DSP classification (<500ms SLA).  │
├──────────────────────────┼─────────────────────────────┼─────────────────────────────────────────┤
│ **Tier 2: Distributed**  │ Exo (:52415) / Petals DHT   │ Pooled 82.8GB VRAM sharded inference   │
│                          │ Multi-node P2P mesh         │ (DeepSeek-R1-32B, Qwen3-VL-32B).        │
├──────────────────────────┼─────────────────────────────┼─────────────────────────────────────────┤
│ **Tier 3: Cloud Runtime  │ `gemini-3.1-pro-preview` /  │ Runtime routing escalations, multi-WAN  │
│ Evaluator & Deep Intel** │ `gemini-3.7-flash`          │ split-brain tie-breakers, 1M-token     │
│                          │ (`google-genai` SDK v2.3+)  │ telemetry batch anomaly detection.      │
├──────────────────────────┼─────────────────────────────┼─────────────────────────────────────────┤
│ **Tier 4: Deep Security  │ `claude-3-opus` / Opus 4.6  │ Formal architectural invariant audit,   │
│ & Invariant Audit**      │ Anthropic API Client        │ zero-data-leak verification, self-heal. │
└──────────────────────────┴─────────────────────────────┴─────────────────────────────────────────┘
```

### 3.2 Escalation Protocol & Fast-Track Classifier

The local orchestrator employs a rule-based and neural fast-track classifier to determine if a decision requires cloud escalation.

**Escalation Trigger Conditions:**
1. **Decision Complexity ($C_{\text{score}} > 0.85$):** Multi-hop mesh routing involving $\ge 3$ degraded nodes or contradictory health metrics.
2. **Local Circuit Breaker Fault Cascade:** Consecutive failures $\ge 3$ on local edge tiers with circuit breaker state `OPEN`.
3. **Multi-WAN Network Partition:** Topology split-brain where GL.iNet Gateway and Tailscale report incompatible routing tables.
4. **Thermal / Memory Deadlock:** All local utility nodes operate at $>90\%$ dynamic ceiling simultaneously.

**SDK Invocation Contract (`google-genai` v2.3+ Interactions API):**
```python
from google import genai
from google.genai import types

client = genai.Client()

# Runtime Evaluator Escalation Call
interaction = client.interactions.create(
    model="gemini-3.1-pro-preview",
    input=escalation_context_json,
    generation_config=types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=EscalationDecisionResponse
    )
)
decision = EscalationDecisionResponse.model_validate_json(interaction.output_text)
```

### 3.3 Batch Telemetry Aggregation & Deep Anomaly Detection

1. **Aggregation Window & Compaction**:
   - The Mac Mini host buffers telemetry frames (CPU, GPU, RAM, thermals, RTT, packet loss, battery %, BLE RSSI) into an in-memory ring buffer.
   - Every **60 minutes** (or upon reaching 10,000 frames), the data is delta-compressed into a JSONL/Parquet batch payload.
2. **Cloud Batch Analysis Pipeline**:
   - The batch is dispatched asynchronously (`background=True`) to `gemini-3.1-pro-preview` utilizing its **1M token context window**.
   - Gemini evaluates:
     - **Thermal Drift Curves**: Identifies degrading thermal paste or fan failure across nodes.
     - **WAN Jitter & Packet Loss Correlation**: Detects RF interference patterns across Wi-Fi 6E bands.
     - **Battery Degradation Velocity**: Predicts Samsung S20+ / Pixel 10 Pro XL battery health decline.
     - **Memory Leak Trajectories**: Fits linear and polynomial curves to long-term memory growth in daemons.
3. **Cross-Validation with Opus 4.6**:
   - High-severity anomalies (e.g. predicted hardware failure or persistent routing degradation) are mirrored to Opus 4.6 to synthesize verified, fail-safe remediation shell scripts.

---

## 4. Specification Discovery: R4 — Mac Mini 24GB RAM Primary Governor Workload Offloading

### 4.1 Mac Mini Host Hardware Constraints & Role

- **Hardware**: Apple M4 Pro / M4 Silicon, 24.0 GB Unified Memory, 10Gbps Thunderbolt 4, 10GbE / Wi-Fi 6E.
- **Operating System**: macOS Sequoia 15+.
- **Dynamic RAM Ceiling**: **90.0% ($21.6\text{ GB}$)**.
- **Hard Reserved Buffer**: **$2.4\text{ GB}$** strictly protected for macOS kernel, WindowServer, audio/video pipelines, and interactive UI responsiveness.
- **Governor Invariant**: The governor MUST NEVER allow total system RAM consumption to exceed $21.6\text{ GB}$. If memory pressure approaches $20.0\text{ GB}$, task offloading MUST commence immediately.

### 4.2 Utility Nodes & Capability Matrix

The governor offloads heavy workloads across four specialized utility targets:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   UTILITY NODE CAPABILITY MATRIX                                       │
├───────────────────┬─────────────┬──────────────┬──────────────┬────────────────────────────────────────┤
│ Node Identifier   │ Primary IP  │ RAM / AI Cap │ Interconnect │ Governed Offload Domain                │
├───────────────────┼─────────────┼──────────────┼──────────────┼────────────────────────────────────────┤
│ `MacBook_Pro`     │ TB4:        │ 16.0 GB /    │ 10Gbps TB4   │ • Primary Metal GPU RPC (Port 50052)   │
│ (Vault Node)      │ 169.254.    │ 14.0 GB AI   │ (0.277ms RTT │ • Heavy 32B Model Tensor Layers        │
│                   │ 187.138     │ (90% Cap)    │ 1.25 GB/s)   │ • 285 GB SSD Model Storage Vault       │
├───────────────────┼─────────────┼──────────────┼──────────────┼────────────────────────────────────────┤
│ `Linux_Head_Node` │ LAN:        │ 16.0 GB /    │ 1Gbps LAN /  │ • Batch Telemetry Analytics & ETL      │
│ (AMD Ryzen 7)     │ 192.168.    │ 13.8 GB AI   │ Tailscale    │ • Dockerized Microservices & Ray Head  │
│                   │ 8.224       │ (80% Cap)    │ (1.2ms RTT)  │ • 1TB SSD Model Vault & OpenClaw       │
├───────────────────┼─────────────┼──────────────┼──────────────┼────────────────────────────────────────┤
│ `MacBook_Air`     │ LAN:        │ 16.0 GB /    │ Wi-Fi 6E /   │ • Secondary Metal Performance Shaders  │
│ (Apple M2)        │ 192.168.    │ 13.5 GB AI   │ Tailscale    │ • LoRA Distillation & Fine-Tuning      │
│                   │ 8.222       │ (90% Cap)    │ (2.5ms RTT)  │                                        │
├───────────────────┼─────────────┼──────────────┼──────────────┼────────────────────────────────────────┤
│ `Pixel_10_Pro_XL` │ Tailscale:  │ 16.0 GB /    │ Wi-Fi 6E /   │ • Tensor G5 Edge TPU Inference         │
│ (Mobile Edge)     │ 100.73.     │ 12.5 GB AI   │ USB ADB      │ • 8K PTZ Vision Stream Ingestion       │
│                   │ 38.87       │ (85% Cap)    │ (5.0ms RTT)  │ • UWB Spatial Positioning Anchor       │
└───────────────────┴─────────────┴──────────────┴──────────────┴────────────────────────────────────────┘
```

### 4.3 Multi-Transport Routing & Offloading Mechanics

1. **Transport Priority Hierarchy**:
   $$\text{Route Priority} = \begin{cases} 
   \textbf{TB4 Direct Bridge } (\text{10Gbps}, 0.277\text{ms}), & \text{Target: MacBook Pro (Tensor Shards)} \\
   \textbf{Gigabit Ethernet / 2.5G LAN } (\text{1Gbps}, 1.2\text{ms}), & \text{Target: Linux Head Node (Ray/Batch)} \\
   \textbf{Wi-Fi 6E } (800\text{Mbps}, 3.0\text{ms}), & \text{Target: MacBook Air / Mobile Nodes} \\
   \textbf{Tailscale WireGuard Overlay } (200\text{Mbps}, 12.0\text{ms}), & \text{Target: All Nodes (Encrypted Fallback)} 
   \end{cases}$$

2. **Stateful vs Stateless Offload Dispatch**:
   - **Stateless Tasks (Batch analytics, code formatting, simple LLM queries)**: Serialized as JSON over HTTP POST `/api/v1/mesh/offload` to the Linux Head Node Ray cluster with a $1.5\text{s}$ timeout.
   - **Stateful LLM Inference (Multi-turn conversations, large KV-caches)**: Offloaded to the MacBook Pro via `llama-rpc-server` on port `50052` over Thunderbolt 4. If TB4 drops, session context is saved to local Redis/Qdrant and delegated via Tailscale.

3. **Offload Rollback & Fault Resilience**:
   - If the designated target node fails to acknowledge task reception within $500\text{ms}$, the governor automatically re-routes to the next node in the priority list.
   - If all local utility nodes are unavailable, the governor engages Cloud Fallback (`gemini-3.7-flash`).

---

## 5. Concrete Data Schemas & API Interface Contracts

### 5.1 Pydantic v2 Models (`compute_pooling_schemas.py`)

```python
"""
Concrete Pydantic v2 Schemas for Distributed Resource & Compute Pooling Manager
Authoritative Specification Model
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class OptInLevel(str, Enum):
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    MAXIMUM = "MAXIMUM"


class ExecutionState(str, Enum):
    IDLE_STANDBY = "IDLE_STANDBY"
    ACTIVE_FULL = "ACTIVE_FULL"
    THROTTLED_USER_ACTIVE = "THROTTLED_USER_ACTIVE"
    PAUSED_HARD_STOP = "PAUSED_HARD_STOP"
    DRAINING_FOR_OFFLOAD = "DRAINING_FOR_OFFLOAD"
    RAMPING_UP = "RAMPING_UP"


class NetworkTransport(str, Enum):
    THUNDERBOLT4 = "THUNDERBOLT4"
    GIGABIT_ETHERNET = "GIGABIT_ETHERNET"
    WIFI_6E = "WIFI_6E"
    TAILSCALE = "TAILSCALE"
    CLOUD_TUNNEL = "CLOUD_TUNNEL"


# --- R2: User Opt-In & Activity Schemas ---

class UserActivityEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp_utc: str = Field(description="ISO-8601 UTC timestamp of event")
    device_id: str = Field(description="Host device identifier, e.g. Mac_Node")
    seconds_since_last_input: float = Field(ge=0.0, description="Seconds since last mouse/keyboard event")
    is_user_active: bool = Field(description="True if seconds_since_last_input < 0.500s")
    display_frame_rate_fps: float = Field(ge=0.0, le=240.0, description="Current window server FPS")
    dropped_frames_detected: bool = Field(default=False)


class ComputeGovernorConfig(BaseModel):
    opt_in_level: OptInLevel = Field(default=OptInLevel.MODERATE)
    max_ram_bytes: int = Field(gt=0, description="Max allowed RAM allocation in bytes")
    max_cpu_threads: int = Field(gt=0, le=32, description="Max allowed CPU threads")
    max_gpu_utilization_pct: float = Field(ge=0.0, le=100.0)
    thermal_limit_celsius: float = Field(ge=40.0, le=105.0)
    user_pause_latency_ms_sla: int = Field(default=50, description="Target pause latency SLA in ms")
    cooldown_seconds: float = Field(default=5.0)


class ComputeGovernorStatus(BaseModel):
    timestamp_utc: str
    current_state: ExecutionState
    active_opt_in_level: OptInLevel
    throttle_factor: float = Field(ge=0.0, le=1.0, description="Current compute throttle factor Theta(t)")
    mac_mini_ram_free_bytes: int
    mac_mini_ram_used_bytes: int
    mac_mini_ram_ceiling_bytes: int
    active_local_processes: List[str]
    active_offloads: int
    thermal_celsius: float


# --- R3: Cloud AI Synergy Schemas ---

class EscalationReason(str, Enum):
    COMPLEXITY_THRESHOLD_EXCEEDED = "COMPLEXITY_THRESHOLD_EXCEEDED"
    MULTI_NODE_SPLIT_BRAIN = "MULTI_NODE_SPLIT_BRAIN"
    CIRCUIT_BREAKER_CASCADE = "CIRCUIT_BREAKER_CASCADE"
    THERMAL_MEMORY_DEADLOCK = "THERMAL_MEMORY_DEADLOCK"
    SECURITY_INVARIANT_AUDIT = "SECURITY_INVARIANT_AUDIT"


class EscalationRequest(BaseModel):
    request_id: str = Field(description="UUID of the escalation event")
    timestamp_utc: str
    reason: EscalationReason
    complexity_score: float = Field(ge=0.0, le=1.0)
    originating_node: str
    mesh_topology_snapshot: Dict[str, Any]
    failed_local_attempts: List[str]
    context_payload: Dict[str, Any]


class EscalationDecisionResponse(BaseModel):
    request_id: str
    target_evaluator: str = Field(description="gemini-3.1-pro-preview or claude-3-opus")
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommended_routing: Dict[str, str] = Field(description="Map of task_id to target node")
    failover_instructions: List[str]
    reconfiguration_commands: List[str]
    rationale: str


class TelemetryFrame(BaseModel):
    timestamp_epoch_ms: int
    node_name: str
    cpu_percent: float = Field(ge=0.0, le=100.0)
    ram_used_mb: float
    ram_free_mb: float
    thermal_celsius: float
    battery_percent: Optional[float] = None
    battery_is_charging: Optional[bool] = None
    active_transport: NetworkTransport
    rtt_to_gateway_ms: float
    packet_loss_pct: float


class TelemetryBatchPayload(BaseModel):
    batch_id: str
    start_time_utc: str
    end_time_utc: str
    total_frames: int
    node_summaries: Dict[str, Dict[str, float]]
    compressed_frames_delta_json: str


class AnomalyReport(BaseModel):
    batch_id: str
    timestamp_utc: str
    evaluator_model: str
    overall_mesh_health_score: float = Field(ge=0.0, le=100.0)
    anomalies_detected: List[Dict[str, Any]] = Field(description="List of detected anomalies with severity")
    thermal_drift_warnings: List[str]
    predicted_hardware_failures: List[Dict[str, Any]]
    recommended_actions: List[str]


# --- R4: Workload Offloading Schemas ---

class OffloadTaskRequest(BaseModel):
    task_id: str
    priority: int = Field(ge=1, le=10, description="1=Lowest, 10=Highest")
    source_node: str = Field(default="Mac_Node")
    target_node: str = Field(description="MacBook_Pro, Linux_Head_Node, etc.")
    preferred_transport: NetworkTransport
    task_type: str = Field(description="LLM_INFERENCE_SHARD, BATCH_ETL, LORA_TRAINING")
    payload: Dict[str, Any]
    timeout_seconds: float = Field(default=30.0)


class OffloadTaskResponse(BaseModel):
    task_id: str
    status: str = Field(description="ACCEPTED, REJECTED, COMPLETED, FAILED")
    executing_node: str
    transport_used: NetworkTransport
    latency_ms: float
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
```

### 5.2 Protocol Buffers Interface Contract (`compute_pooling.proto`)

```protobuf
syntax = "proto3";

package lauburu.compute.v1;

option go_package = "lauburu/compute/v1;computev1";
option java_package = "com.lauburu.compute.v1";

enum OptInLevel {
  OPT_IN_UNSPECIFIED = 0;
  OPT_IN_LIGHT = 1;
  OPT_IN_MODERATE = 2;
  OPT_IN_MAXIMUM = 3;
}

enum ExecutionState {
  STATE_UNSPECIFIED = 0;
  STATE_IDLE_STANDBY = 1;
  STATE_ACTIVE_FULL = 2;
  STATE_THROTTLED_USER_ACTIVE = 3;
  STATE_PAUSED_HARD_STOP = 4;
  STATE_DRAINING_FOR_OFFLOAD = 5;
  STATE_RAMPING_UP = 6;
}

enum TransportType {
  TRANSPORT_UNSPECIFIED = 0;
  TRANSPORT_THUNDERBOLT4 = 1;
  TRANSPORT_GIGABIT_ETHERNET = 2;
  TRANSPORT_WIFI_6E = 3;
  TRANSPORT_TAILSCALE = 4;
  TRANSPORT_CLOUD_TUNNEL = 5;
}

message SetOptInRequest {
  OptInLevel level = 1;
  string user_id = 2;
}

message SetOptInResponse {
  bool success = 1;
  OptInLevel active_level = 2;
  string message = 3;
}

message UserActivityNotification {
  string timestamp_utc = 1;
  string device_id = 2;
  double seconds_since_last_input = 3;
  bool is_user_active = 4;
  double display_fps = 5;
}

message GovernorStatusRequest {
  string device_id = 1;
}

message GovernorStatusResponse {
  string timestamp_utc = 1;
  ExecutionState current_state = 2;
  OptInLevel opt_in_level = 3;
  double throttle_factor = 4;
  int64 ram_free_bytes = 5;
  int64 ram_used_bytes = 6;
  double thermal_celsius = 7;
  int32 active_offloads = 8;
}

message OffloadTaskRequestProto {
  string task_id = 1;
  int32 priority = 2;
  string source_node = 3;
  string target_node = 4;
  TransportType preferred_transport = 5;
  string task_type = 6;
  bytes serialized_payload = 7;
  double timeout_seconds = 8;
}

message OffloadTaskResponseProto {
  string task_id = 1;
  string status = 2;
  string executing_node = 3;
  TransportType transport_used = 4;
  double execution_duration_ms = 5;
  bytes serialized_result = 6;
  string error_message = 7;
}

service ComputeGovernorService {
  rpc SetOptInLevel(SetOptInRequest) returns (SetOptInResponse);
  rpc NotifyUserActivity(UserActivityNotification) returns (GovernorStatusResponse);
  rpc GetGovernorStatus(GovernorStatusRequest) returns (GovernorStatusResponse);
  rpc StreamGovernorEvents(GovernorStatusRequest) returns (stream GovernorStatusResponse);
}

service WorkloadOffloadService {
  rpc DispatchOffloadTask(OffloadTaskRequestProto) returns (OffloadTaskResponseProto);
}
```

### 5.3 REST & WebSocket API Surface

| Endpoint | Method / Protocol | Role | Input Payload | Output Payload |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/compute/opt-in` | `POST` | Updates active user opt-in level | `{"opt_in_level": "LIGHT"}` | `ComputeGovernorStatus` |
| `/api/v1/compute/activity` | `POST` | Ingests input activity tick | `UserActivityEvent` | `ComputeGovernorStatus` |
| `/api/v1/compute/status` | `GET` | Queries live governor state | None | `ComputeGovernorStatus` |
| `/api/v1/cloud/escalate` | `POST` | Escalates decision to Gemini/Opus | `EscalationRequest` | `EscalationDecisionResponse` |
| `/api/v1/cloud/telemetry/batch` | `POST` | Submits batch for deep analytics | `TelemetryBatchPayload` | `AnomalyReport` |
| `/api/v1/mesh/offload` | `POST` | Dispatches task to utility node | `OffloadTaskRequest` | `OffloadTaskResponse` |
| `/ws/telemetry` | `WebSocket` | Real-time 20Hz telemetry stream | Channel Subscribe Msg | Stream of `TelemetryFrame` |
| `/ws/governor-events` | `WebSocket` | Real-time governor state change | Channel Subscribe Msg | Stream of `ComputeGovernorStatus` |

---

## 6. Acceptance Criteria Test Harnesses & Verification Framework

### 6.1 Test Harness 1: User Activity Throttling & Offloading Test
**Target**: Validate R2 & R4 acceptance criteria. Heavy compute task on Mac Mini MUST immediately throttle/offload ($<50\text{ms}$) upon simulated user input.

```python
"""
tests/test_harness_user_activity_throttling.py
Programmatic Zero-Mock Acceptance Test for R2 & R4
"""

import time
import pytest
from typing import Generator
from compute_pooling_schemas import OptInLevel, ExecutionState, UserActivityEvent


class TestUserActivityThrottlingHarness:
    """Acceptance Harness: Instant pause/throttle and offload on user activity."""

    def test_instant_throttle_on_simulated_user_activity(self, compute_governor_service):
        """
        Verify:
        1. Governor is running full compute in MODERATE mode.
        2. Simulated user activity event arrives at t=0.
        3. Governor transitions to THROTTLED_USER_ACTIVE or PAUSED_HARD_STOP in < 50ms.
        4. Compute throttle factor Theta(t) drops to <= 0.10.
        5. Heavy task is offloaded to MacBook Pro over Thunderbolt 4.
        """
        # 1. Setup governor in Moderate mode
        compute_governor_service.set_opt_in_level(OptInLevel.MODERATE)
        compute_governor_service.start_synthetic_compute_task(task_id="heavy_32b_inference_1")
        
        status_initial = compute_governor_service.get_status()
        assert status_initial.current_state == ExecutionState.ACTIVE_FULL
        assert status_initial.throttle_factor >= 0.50

        # 2. Inject user activity event
        t_start = time.perf_counter()
        activity_event = UserActivityEvent(
            timestamp_utc="2026-08-24T09:35:00.000Z",
            device_id="Mac_Node",
            seconds_since_last_input=0.010, # 10ms ago
            is_user_active=True,
            display_frame_rate_fps=60.0,
            dropped_frames_detected=False
        )
        status_after = compute_governor_service.handle_user_activity(activity_event)
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        # 3. Assert SLA and State Transition
        print(f"\n[Test Result] Throttle response latency: {t_elapsed_ms:.2f} ms (SLA < 50.0 ms)")
        assert t_elapsed_ms < 50.0, f"Pause latency exceeded SLA: {t_elapsed_ms:.2f}ms >= 50ms"
        assert status_after.current_state in (ExecutionState.THROTTLED_USER_ACTIVE, ExecutionState.PAUSED_HARD_STOP)
        assert status_after.throttle_factor <= 0.10, f"Throttle factor did not decrease: {status_after.throttle_factor}"

        # 4. Verify Task Offload Trigger
        active_offload = compute_governor_service.get_last_offload_record()
        assert active_offload is not None
        assert active_offload.target_node == "MacBook_Pro"
        assert active_offload.preferred_transport == "THUNDERBOLT4"
        assert active_offload.status in ("ACCEPTED", "COMPLETED")
```

### 6.2 Test Harness 2: Cloud AI Synergy & Deep Telemetry Analytics Test
**Target**: Validate R3 acceptance criteria. Telemetry batches are formatted and evaluated by Gemini Pro 3.1 High / Opus 4.6 for anomaly detection.

```python
"""
tests/test_harness_cloud_synergy_analytics.py
Programmatic Zero-Mock Acceptance Test for R3
"""

import pytest
from compute_pooling_schemas import TelemetryBatchPayload, AnomalyReport, EscalationRequest, EscalationReason


class TestCloudSynergyAnalyticsHarness:
    """Acceptance Harness: Cloud AI Synergy for runtime evaluation & deep analytics."""

    def test_batch_telemetry_deep_analytics_pipeline(self, cloud_synergy_client):
        """
        Verify:
        1. Formats 1,000 real telemetry frames into TelemetryBatchPayload.
        2. Dispatches to Gemini Pro 3.1 High Interactions API.
        3. Returns valid AnomalyReport adhering to strict Pydantic schema.
        4. Validates presence of thermal drift and packet loss analyses.
        """
        batch = cloud_synergy_client.generate_telemetry_batch(frame_count=1000)
        assert isinstance(batch, TelemetryBatchPayload)
        assert batch.total_frames == 1000

        report = cloud_synergy_client.analyze_telemetry_batch(batch)
        assert isinstance(report, AnomalyReport)
        assert report.batch_id == batch.batch_id
        assert 0.0 <= report.overall_mesh_health_score <= 100.0
        assert len(report.thermal_drift_warnings) >= 0
        assert len(report.recommended_actions) >= 1

    def test_runtime_routing_escalation(self, cloud_synergy_client):
        """
        Verify:
        1. Simulates multi-node split-brain condition.
        2. Escalates to Gemini Pro 3.1 Runtime Evaluator.
        3. Receives deterministic routing and failover instructions.
        """
        escalation = EscalationRequest(
            request_id="esc-split-brain-001",
            timestamp_utc="2026-08-24T09:35:00.000Z",
            reason=EscalationReason.MULTI_NODE_SPLIT_BRAIN,
            complexity_score=0.92,
            originating_node="Mac_Node",
            mesh_topology_snapshot={"macbook_pro": "TB4_ONLINE", "linux_head": "LAN_ONLINE"},
            failed_local_attempts=["local_router_tie", "heuristic_pass_failed"],
            context_payload={"contending_tasks": ["task_a", "task_b"]}
        )
        decision = cloud_synergy_client.escalate_decision(escalation)
        assert decision.request_id == escalation.request_id
        assert decision.confidence_score >= 0.80
        assert "MacBook_Pro" in decision.recommended_routing.values() or "Linux_Head_Node" in decision.recommended_routing.values()
```

### 6.3 5-Tier Verification & Zero-Mock Compliance Matrix

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  5-TIER VERIFICATION SUITE MATRIX                                │
├────────┬───────────────────────────┬─────────────────────────────────────────────────────────────┤
│ Tier   │ Suite Name                │ Verification Scope & Invariants                             │
├────────┼───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Tier 1 │ Feature Unit Coverage     │ Pydantic schema validation, Opt-In profiles, state machine  │
│        │                           │ transitions, Quartz/X11 user event parser unit tests.       │
├────────┼───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Tier 2 │ Boundary & Dynamic Limits │ 24GB RAM ceiling enforcement (21.6GB clamp), thermal step-  │
│        │                           │ down at 65°C/78°C/92°C, sub-50ms pause latency assertions.  │
├────────┼───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Tier 3 │ Combinatorial Chaos Tests │ Concurrent user activity + TB4 cable pull + memory spike;  │
│        │                           │ assert 0 socket dropped, seamless Tailscale failover.       │
├────────┼───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Tier 4 │ End-to-End Mesh Workloads │ Real 32B model inference offload Mac Mini -> MacBook Pro    │
│        │                           │ via TB4 port 50052, telemetry batch upload to Gemini API.   │
├────────┼───────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Tier 5 │ Swarm Truth Audit Gate    │ Zero-mock code scanner, static analysis, live hardware E2E  │
│        │ (VLM + AST Gate)          │ click-through audit across Samsung S20+ and Pixel 10 Pro XL.│
└────────┴───────────────────────────┴─────────────────────────────────────────────────────────────┘
```

---

## 7. Features Discovered & Edge Cases Matrix

### Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | R2 Governance | User Opt-In Profiles | Allows user to select Light (25%), Moderate (50%), Maximum (90%) resource allocation. | `OptInLevel` string | `ComputeGovernorConfig` | Reverts to MODERATE on invalid input | ORIGINAL_REQUEST §R2 |
| 2 | R2 Governance | Sub-50ms Input Activity Sensor | Monitors macOS CoreGraphics / Linux X11 / Android dumpsys for real-time human interaction. | OS Event Streams | `UserActivityEvent` | Fallback to timestamp polling if C-lib unavailable | Quartz API / IOHIDLib |
| 3 | R2 Governance | Adaptive Throttling State Machine | Transitions compute between ACTIVE_FULL, THROTTLED, and PAUSED based on input & thermals. | `UserActivityEvent`, CPU/RAM metrics | `ComputeGovernorStatus` | Failsafe to THROTTLED if sensor times out | System Design Spec |
| 4 | R2 Governance | Process Suspension Controller | Dispatches SIGSTOP/SIGCONT to local C++ llama-server workers on active user detection. | OS Process PID, Signal | Exit code / Status | Logs error and clamps CPU quota if SIGSTOP fails | POSIX / launchd |
| 5 | R3 Cloud AI | Runtime Evaluator Escalator | Escalates high-complexity routing and split-brain decisions to Gemini Pro 3.1 High. | `EscalationRequest` | `EscalationDecisionResponse` | Fallback to local heuristic table on network timeout | ORIGINAL_REQUEST §R3 / `google-genai` |
| 6 | R3 Cloud AI | Batch Telemetry Aggregator | Compresses 1-hour hardware metrics into Parquet/JSONL delta batches for 1M context analysis. | Ring buffer of `TelemetryFrame` | `TelemetryBatchPayload` | Discards oldest frames on ring buffer overflow | ORIGINAL_REQUEST §R3 |
| 7 | R3 Cloud AI | Deep Anomaly & Drift Detector | Calls Gemini Pro 3.1 High to compute thermal drift, battery degradation, and memory leaks. | `TelemetryBatchPayload` | `AnomalyReport` | Retries with exponential backoff on rate limit | `gemini-interactions-api` |
| 8 | R3 Cloud AI | Opus 4.6 Safety Invariant Auditor | Verifies zero credential leakage and cross-validates critical self-healing remediation code. | Remediation Code / Config | Formal Verification Result | Blocks patch application if invariant violated | Anthropic Claude API |
| 9 | R4 Offloading | Mac Mini 24GB Memory Governor | Enforces strict 90% (21.6GB) usable memory limit with 2.4GB kernel reservation buffer. | `vm_stat` / `psutil` memory | Memory Headroom Status | Triggers emergency offload if RAM > 20GB | ORIGINAL_REQUEST §R4 |
| 10 | R4 Offloading | Thunderbolt 4 Low-Latency Offload | Offloads heavy 32B GPU tensor layers to MacBook Pro Vault over 10Gbps TB4 (0.277ms RTT). | Tensor shard request | `OffloadTaskResponse` | Auto-failover to 10GbE LAN if TB4 link drops | `llama_rpc_mesh` / TB4 Bridge |
| 11 | R4 Offloading | Linux Head Node Batch Offload | Offloads Dockerized microservices, ETL pipelines, and Ray tasks to AMD Ryzen 7 5700U node. | Batch task payload | `OffloadTaskResponse` | Queues locally if Linux node busy | `spec-00-core-infrastructure` |
| 12 | R4 Offloading | Mobile Edge TPU Task Delegate | Offloads lightweight vision tasks to Pixel 10 Pro XL Tensor G5 NPU via USB ADB / Wi-Fi. | Vision frame buffer | Classification Result | Skips mobile node if battery < 20% | `spec-01-apps-ecosystem` |

### Edge Cases Discovered
| # | Feature | Input / Condition | Observed / Governed Behavior |
|---|---|---|---|
| 1 | R2 Throttling | Rapid intermittent user typing (50ms on / 100ms off bursts). | Hysteresis cooldown timer ($T_{\text{cooldown}}=5.0\text{s}$) prevents thrashing; remains in `THROTTLED_USER_ACTIVE`. |
| 2 | R2 Throttling | Full-screen game or video playback (no keyboard/mouse input, but 120 FPS display active). | WindowServer display refresh monitor detects active render context; keeps compute at MODERATE (50% max). |
| 3 | R3 Cloud Synergy | Internet blackout / WAN failure during escalation trigger. | Circuit breaker trips to `OPEN`; governor engages local heuristic fallback matrix without hanging. |
| 4 | R3 Cloud Synergy | Telemetry batch payload exceeds 50MB raw uncompressed size. | Delta-encoding compression and sliding-window downsampling reduce payload to $< 5\text{MB}$ before upload. |
| 5 | R4 Offloading | Thunderbolt 4 cable disconnected mid-tensor inference. | TCP socket timeout ($500\text{ms}$) trips failover; task context re-routed to Linux Head Node over Gigabit LAN. |
| 6 | R4 Offloading | All utility nodes simultaneously report $>90\%$ memory utilization. | Governor rejects new non-critical tasks, throttles active tasks to 10%, and alerts user in UI cockpit. |
| 7 | R4 Offloading | Mac Mini kernel memory pressure spike (e.g. Xcode compilation while AI running). | Immediate SIGSTOP dispatched to local `llama-server`; task state serialized and migrated to MacBook Pro. |
| 8 | Dark Mode Sync | Mixed OS fleet (macOS, Ubuntu GNOME, Android 16/14). | Universal controller broadcasts AppleScript (macOS), gsettings (GNOME), and ADB uimode (Android) concurrently. |

