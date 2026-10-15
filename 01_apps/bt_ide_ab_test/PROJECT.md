# Project: IDE Intelligence Architecture
**Codebase Root**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/bt_ide_ab_test`  
**Reference Document**: `.agents/ORIGINAL_REQUEST.md`  
**Status**: Active — Decomposition Phase  

---

## 1. Architecture Overview

The **IDE Intelligence Architecture** implements a Strict Local-First IDE Mesh Gateway operating across the 7-Layer Lauburu Physical Mesh Network (108.0 GB RAM / 82.8 GB usable AI VRAM). It provides dynamic RAM governance, dual-engine tool routing, physical storage affinity through SeaweedFS, a manual cloud escalation gate, and continuous local distillation.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 IDE INTELLIGENCE ARCHITECTURE                                    │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│   [ IDE Client / Textual TUI / Continue.dev Extension ] (Port 8085 / OpenAI Compatible API)     │
│                                           │                                                      │
│                                           ▼                                                      │
│              ┌────────────────────────────────────────────────────────┐                          │
│              │        UNIFIED IDE GATEWAY (Port 8085 FastAPI)         │                          │
│              └────────────────────────────┬───────────────────────────┘                          │
│                                           │                                                      │
│           ┌───────────────────────────────┼───────────────────────────────┐                      │
│           ▼                               ▼                               ▼                      │
│   ┌────────────────────┐      ┌───────────────────────┐      ┌────────────────────────┐          │
│   │ Dynamic Global RAM │      │ Dual-Engine Classifier│      │ Manual Cloud Escalation│          │
│   │ Governor (R1)      │      │ & Router Engine (R2)  │      │ Gate (R4)              │          │
│   │ • 7-Layer Polling  │      │ • Hermes 3 Tool Router│      │ • Context Overflow     │          │
│   │ • Global Pool VRAM │      │   (Port 8082)         │      │   Detection (> 8192)   │          │
│   │ • Backpressure     │      │ • Qwen 2.5 Coder      │      │ • Dual-Mode Block:     │          │
│   │   Suspension       │      │   (Port 8081)         │      │   TTY & HTTP Ticket    │          │
│   │   (SIGSTOP/CONT)   │      │ • Vector DB Paging    │      │ • Zero Auto-Cloud Leak │          │
│   └────────────────────┘      └───────────────────────┘      └───────────┬────────────┘          │
│                                                                          │ (If Authorized)       │
│                                                                          ▼                       │
│                                                              ┌────────────────────────┐          │
│                                                              │ Continuous Local       │          │
│                                                              │ Distillation (/loop)   │          │
│                                                              │ • Silent Trace Capture │          │
│                                                              │ • Funnel to L3 Hub     │          │
│                                                              │ • Nightly LoRA Daemon  │          │
│                                                              └───────────┬────────────┘          │
│                                                                          │                       │
│                                  ┌───────────────────────────────────────┴────────────┐          │
│                                  │ Tri-Vault Storage Specialist & SeaweedFS (R3)      │          │
│                                  │ • Heavy Datasets -> L3 Linux Hub                   │          │
│                                  │ • Vector Context  -> L4/L6 Edge NPUs               │          │
│                                  │ • Git Source Code -> L1 Mac Mini Host              │          │
│                                  └────────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Port Assignments & Model Hierarchy
- **Port 8085**: Unified IDE Gateway & Mesh RAM Governor (`gateway/server.py`).
- **Port 8082**: Sovereign Master Local Orchestrator (`Qwen 3.8 Max 27B Abliterated` via `prima.cpp` PRP / Hermes 3 tool routing). ELO: 1734.
- **Port 8081**: Subordinate Syntax Worker (`Qwen 2.5 Coder 7B Instruct` via `llama-server`).
- **Port 8083**: Canonical Adversarial Red Team / Dialectic (`Qwen 3.8 Max` standard).
- **Port 9333 / 8888 / 8080**: SeaweedFS Master, Filer, and Volume Daemons.
- **Port 18802**: Self-Healing Hub on L3 Linux Hub (`100.101.39.98`).

---

## 2. Feature Inventory

Every feature from user requirements and the survey phase is enumerated below with its assigned milestone.

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1: Multi-Node Telemetry Polling | Async OS telemetry collection (`sysctl`, `/proc/meminfo`, HTTP JSON) across all 7 layers | M1 | Survey 1, Survey 3 |
| 2 | F2: Global RAM Pool Metric | Aggregate 108GB RAM pool, calculate dynamic safety thresholds (L1 >= 4.8GB sanctuary, L3 <= 80%, L6 <= 85%) | M1 | Survey 1, Survey 3 |
| 3 | F3: Backpressure Suspension | Task priority registry; pause low-priority background subagents (LoRA harvesting, AST crawling) under memory pressure | M1 | Survey 1, Survey 3 |
| 4 | F4: Hermes 3 Tool Routing Engine | Decoupled tool router on Port 8082; tool discovery, XML schema parsing, skill management | M2 | Survey 1, Survey 3 |
| 5 | F5: Qwen 2.5 Coder Code Engine | Dedicated syntax generation endpoint on Port 8081 with SSE streaming | M2 | Survey 1, Survey 3 |
| 6 | F6: Vector DB Context Paging | Qdrant / KV-cache vector page retrieval, top-k ranking, context injection | M2 | Survey 1, Survey 3 |
| 7 | F7: SeaweedFS Hardware Affinity | Path-to-hardware affinity rules (L3 datasets, L4/L6 vector context, L1 git source), `filer.toml` placement rules | M3 | Survey 2, Survey 3 |
| 8 | F8: SeaweedFS Volume Logic | Transparent VFS namespace preservation, Master `/dir/assign` parameter synthesis | M3 | Survey 2, Survey 3 |
| 9 | F9: Context Overflow Detection | Local context ceiling (8,192 tokens), fast local token estimation | M4 | Survey 2, Survey 3 |
| 10 | F10: Manual Cloud Escalation Gate | Dual-mode halt & block (Interactive TTY + HTTP ticket polling), zero auto-routing to cloud | M4 | Survey 2, Survey 3 |
| 11 | F11: Silent Trace Capture | Non-blocking capture of authorized cloud responses without latency penalty | M5 | Survey 2, Survey 3 |
| 12 | F12: L3 Overnight Fine-Tuning Loop | Funnel traces to L3 Linux Hub, ChatML formatting, overnight PEFT/LoRA daemon | M5 | Survey 2, Survey 3 |
| 13 | F13: Unified IDE Gateway Server | FastAPI / Uvicorn server on Port 8085 integrating all modules with OpenAI compatibility | M6 | Survey 1, Survey 2, Survey 3 |
| 14 | F14: 4-Tier E2E Test Suite | 25 Tier 1 + 25 Tier 2 + Tier 3 + Tier 4 tests, master runner `run_all_tiers.py`, Tri-Proof verification | M7 | Survey 3 |

---

## 3. Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Dynamic Global Mesh RAM Governance | F1, F2, F3: Multi-node telemetry collector, global pool metric, backpressure suspension engine | none | DONE |
| M2 | Dual-Engine Tool Routing & Vector Paging | F4, F5, F6: Hermes 3 tool routing, Qwen 2.5 Coder delegation, Vector DB KV-cache pager | M1 | DONE |
| M3 | Tri-Vault Storage Specialist & SeaweedFS Affinity | F7, F8: Hardware affinity rules, `filer.toml` logic, SeaweedFS volume assignment | none | DONE |
| M4 | Manual Cloud Escalation Gate | F9, F10: Context overflow detection (> 8192 tokens), dual-mode blocking (TTY + HTTP ticket) | M1 | DONE |
| M5 | Continuous Local Distillation Loop (/loop) | F11, F12: Silent trace capture, ChatML formatting, L3 overnight fine-tuning queue | M3, M4 | DONE |
| M6 | Unified Gateway Integration & CLI Entry Points | F13: Integrate all components into Port 8085 server, refactor CLI stubs, OpenAI API compatibility | M1, M2, M3, M4, M5 | DONE |
| M7 | E2E Testing Suite & Multi-Tier Verification | F14: Complete 4-tier test harness (Tiers 1-4: 50+ tests), `run_all_tiers.py`, Tri-Proof report | M6 | DONE |
| M8 | Final Milestone: 100% E2E Pass & Adversarial Hardening | Phase 1 (Tiers 1-4 pass 100%), Phase 2 (Tier 5 adversarial hardening with Challenger), Forensic Integrity Audit | M7 | DONE |

---

## 4. Interface Contracts

### 4.1 RAM Telemetry & Governance Contract (`core/ram_governor.py`)
```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class SubagentPriority(int, Enum):
    LOW = 1          # LoRA Harvester, AST Crawler
    MEDIUM = 2       # Continuous Benchmarker
    HIGH = 3         # Multi-Agent Debate
    IDE_CRITICAL = 4 # Active user IDE session

@dataclass
class NodeMemoryTelemetry:
    node_id: str
    ip: str
    total_ram_mb: float
    free_ram_mb: float
    available_ram_mb: float
    utilization_pct: float
    dynamic_safety_threshold_mb: float
    is_saturated: bool
    is_reachable: bool
    rtt_ms: float

@dataclass
class GlobalRAMPoolMetric:
    total_mesh_ram_gb: float          # ~108.0 GB nominal
    available_mesh_ram_gb: float
    usable_ai_vram_gb: float          # ~82.8 GB nominal
    pool_utilization_pct: float
    nodes_reporting: int
    nodes_total: int
    backpressure_triggered: bool
    saturated_nodes: List[str]
```

### 4.2 Tool Router vs Code Generator Contract (`core/hermes_router.py`)
```python
@dataclass
class RoutingDecision:
    engine: str                       # "HERMES_TOOL_ROUTER" or "QWEN_CODE_GENERATOR"
    target_endpoint: str              # Port 8082 or Port 8081
    model_id: str                     # "qwen_38_max_abliterated" or "qwen2.5-coder-7b-instruct"
    tools_to_invoke: List[dict]
    vector_pages_paged: int
    loop_triggered: bool
    reasoning: str
```

### 4.3 Escalation Gate Contract (`core/escalation_gate.py`)
```python
@dataclass
class EscalationTicket:
    ticket_id: str
    token_count: int
    context_limit: int
    target_cloud_model: str
    status: str                       # "PENDING", "APPROVED", "REJECTED", "TIMED_OUT"
    created_at: float
    expires_at: float
```

### 4.4 SeaweedFS Storage Specialist Contract (`core/storage_specialist.py`)
```python
@dataclass
class StorageAffinityRoute:
    path: str
    category: str                     # "heavy_datasets", "vector_context", "git_source"
    target_node: str                  # "L3_Linux", "L6_Edge", "L1_Mac"
    target_ip: str
    collection: str
    seaweed_assign_params: Dict[str, str]
```

---

## 5. Code Layout

The project follows a clean modular layout under `01_apps/bt_ide_ab_test/`:

```
01_apps/bt_ide_ab_test/
├── PROJECT.md                        # Master Project Architecture & Status (Living Document)
├── mesh_ram_governor.py              # Canonical CLI entry point for RAM Governor
├── lens_ide_router_gateway.py        # Canonical CLI entry point for IDE Gateway
├── seaweed_affinity_specialist.py    # Canonical CLI entry point for Storage Specialist
├── core/
│   ├── __init__.py
│   ├── config.py                     # Mesh IP matrix, ports, thresholds, ELO routing table
│   ├── telemetry.py                  # OS telemetry collector (sysctl, /proc/meminfo, multi-IP)
│   ├── ram_governor.py               # Global RAM pool calculator & backpressure suspension
│   ├── hermes_router.py              # Hermes 3 tool-calling & /loop detector
│   ├── vector_pager.py               # Qdrant REST / KV-cache vector context pager
│   ├── code_generator.py             # Qwen 2.5 Coder client with streaming SSE
│   ├── escalation_gate.py            # Manual Cloud Escalation Gate (TTY + HTTP ticket)
│   ├── storage_specialist.py         # SeaweedFS node hardware affinity router
│   └── distillation.py               # Silent trace capture & L3 fine-tuning queue
├── gateway/
│   ├── __init__.py
│   └── server.py                     # Unified FastAPI / Uvicorn Port 8085 server
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures, mock HTTP loopback nodes
│   ├── run_all_tiers.py              # Master multi-tier CLI test runner with Tri-Proof output
│   ├── test_tier1_features.py        # 25 Tier 1 Feature Coverage tests
│   ├── test_tier2_boundaries.py      # 25 Tier 2 Boundary & Corner case tests
│   ├── test_tier3_combinations.py    # Pairwise cross-feature interaction tests
│   └── test_tier4_real_world.py      # 4 Real-world application workload simulations
└── .agents/                          # Agent coordination metadata only
```

---

## 6. Rule Compliance & Invariants

1. **Rule 1 & Rule 5 (Zero-Mock & Tri-Proof Interceptor)**:  
   No simulated arrays, fake latencies, or dummy strings in production code. All test results require Exit Code 0, line-by-line checksums, and telemetry logs.
2. **Rule 3 (Host Sanctuary & Dynamic RAM Governance)**:  
   Mac Mini host preserves $\ge 4.8\text{ GB}$ free physical RAM.
3. **Rule 7 & Rule 15 (Sovereign Local AI Hierarchy & Dynamic ELO)**:  
   Qwen 3.8 Max 27B Abliterated (Port 8082, 1734 ELO) is Master Orchestrator. Qwen 2.5 Coder 7B (Port 8081) is Subordinate Syntax Worker.
4. **Rule 10 (Linux Mini First-Offload Invariant)**:  
   All heavy datasets and overnight LoRA training are offloaded to L3 Linux Hub (`100.101.39.98`).
