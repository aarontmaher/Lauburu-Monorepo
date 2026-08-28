# Canonical Port — Lauburu Unified Command Center (Web & TUI)

Canonical Port is the authoritative operational interface and command center for the **Lauburu Mesh Ecosystem**. It provides a high-density, cyberpunk aerospace Web Dashboard (React 18 / Vite) and a headless Terminal UI (Python Textual / Rich).

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL PORT UNIFIED ARCHITECTURE                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Master AGI Governance Layer (R1)                                                    │
│    • Kimi 88B Tandem Titan (Port 8085 + Port 50052/8081, -ts 28,28,24)                 │
│    • Qwen 3.8 Max / Qwen 2.5-VL Edge (Port 8084, 48.3 tok/s)                          │
│    • 82.8 GB Pooled VRAM Sharding & Dynamic Memory Ceilings (90%, 80%, 85%, 75%)       │
│    • Tri-Orchestrator Debate Console (>0.98 Accord) & Stagnation Failsafe Modal        │
│    • 1-Click Swarm Action Dispatcher (/audit, /duel, /cron, /storage, /ping, /revive)  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. 4 Optimization Modules Aggregation Layer (R2)                                       │
│    • Hardware Optimization: LiveDeviceSentinelHUD + ComputeHubWebView + Bleak 128Hz    │
│    • Software Optimization: MetaTrainingGame AST Dispatcher + Clang ASan Sandbox       │
│    • Internet Optimization: FutureNetworkSimulationHub + MultiWAN 10-Route Accelerator │
│    • Storage Optimization: StorageAnalysisHub + StorageDeepAnalysis + NAS DFS Sync     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Local AI Training & Games Multi-Tab Layer (R3)                                      │
│    • Tab 1: LoRA Training & Distillation Monitor (SFTTrainer, 22+ datasets, Truth Gate)│
│    • Tab 2: Implemented Games & Benchmark Environments (FFA Arena, Chaos SLMs, 3D Kin)│
│    • Tab 3: Structural & Dataset Metrics (10.2k files AST index, 3.29M LOC, 7 Nodes)   │
│    • Tab 4: Execution Traces & Action Logs (Debate logs, Action Ledger, Smolagent)     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Unified Dual Interfaces                                                             │
│    • Web Dashboard: React 18 / Vite / Aerospace Dark Theme                             │
│    • Terminal UI (TUI): Python Textual / Rich Headless Command Center                  │
│    • Unified API & WebSocket Client: Connects to Ports 5001, 4000, 8000, 18888, 18802  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Web Dashboard (Vite / React)
```bash
cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
npm install
npm run dev
# Dashboard opens on http://localhost:3000
```

To create a production build:
```bash
npm run build
```

### 2. Terminal UI (Python Textual)
```bash
cd /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/tui
uv run --with textual --with rich --with httpx python3 canonical_tui.py
```

#### TUI Keyboard Shortcuts:
* `g` — Switch to Master AGI Governance Screen
* `o` — Switch to 4 Optimization Modules Screen
* `t` — Switch to Local AI Training & Games Multi-Tab Screen
* `r` — Refresh live telemetry
* `q` — Quit TUI

---

## 🧩 Interface Contracts

### 1. Navigation State Machine
```typescript
type ViewRoute = 
  | 'governance'
  | 'optimization-hardware'
  | 'optimization-software'
  | 'optimization-internet'
  | 'optimization-storage'
  | 'training-lora'
  | 'training-games'
  | 'training-metrics'
  | 'training-traces'
  | 'leaderboard';
```

### 2. Optimization Mounting Contract
```typescript
interface OptimizationModuleMountProps {
  apiBaseUrl: string;
  telemetryStream: any;
  onActionTrigger: (actionName: string, payload: any) => Promise<any>;
}
```

---

## 🔒 Mandatory Integrity Invariants
* **Rule #0 (Zero-Mock & Zero-Simulated Data):** All gauges represent authentic physical hardware parameters, live sensor streams, or organic telemetry fallbacks.
* **Dynamic Memory Ceilings:** Host Mac (≤90%), Linux Head Node (≤80%), Android (≤85%).
* **Rule #6 Storage Health:** Inode paths verified for Obsidian Knowledge Vault, PySpark Data Lake, and GitHub Monorepo.
