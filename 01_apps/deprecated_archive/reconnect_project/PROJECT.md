# Project: Lauburu App Ecosystem Architectural Map

## Architecture Overview
The Lauburu App Ecosystem is a sovereign, self-healing, distributed AI and biometrics mesh combining:
- **Peripheral Nerves (Sellable Apps & Edge Daemons)**: Low-power edge agents, zero-VRAM text TUIs, Movesense BLE biometrics ingestion, Shizuku thermal governors, and continuous inference benchmarkers.
- **Prefrontal Cortex (Proprietary Infrastructure)**: Centralized orchestration, 8-way ELO chaos arenas, hourly LoRA distillation loops, Next.js / FastAPI command hubs, Quartz digital gardens, and 4-node Syncthing sync clusters.
- **The Brain Stem (Global Protocols & Compute Fabric)**: Unidirectional 1Hz SSE diagnostic streams, Apache Ray distributed actors, 82.8 GB pooled VRAM over 10Gbps TB4 / Wi-Fi 7, and the Obsidian Vault shared RAG knowledge graph.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Lauburu Hardware Sentinel | Zero-VRAM Textual TUI, Shizuku Android Thermal integration, Mac/Linux wake locks, 4-Pillar constraint math `MIN(Host, Device)` | M1 | survey_explorer_1_gen2 |
| F2 | Lauburu Mesh Healer | Autonomous `smolagents` daemon, network recovery (Tailscale flush, zombie PID hunting, cache clearing), +15 ELO harvesting | M1 | survey_explorer_1_gen2 |
| F3 | Movesense Biometrics Hub | Bluetooth daemon for 128Hz ECG, Heart Rate, Kamath 20% filter, DFA-alpha1, and LUDS Phone UI physical stress/readiness algorithm | M1 | survey_explorer_2_gen2 |
| F4 | Shadow Benchmarker API | Evaluates Llama.cpp/Exo/Petals TTFT/TPS for dynamic VRAM sharding across the 82.8GB pool (Port 5050 FastAPI) | M1 | survey_explorer_3 |
| F5 | The Crucible (AI Training Game) | 8-way ELO Chaos Arena, simulating network outages, harvesting high-ELO JSONL data (>1100 ELO), and Hourly LoRA `SFTTrainer` | M2 | survey_explorer_3 |
| F6 | The Main Hub (`localhost:3000` / `localhost:4000`) | Central commander UI consuming SSE telemetry from edge services, PBKDF2 auth, Shopify Customer Account verification | M2 | survey_explorer_2_gen2 |
| F7 | Obsidian Commander | Canonical truth enforcer, Quartz engine (Port 8888), RAG memory graph for cross-agent awareness | M2 | survey_explorer_3 |
| F8 | Mac Air Sync Orchestrator | Secure bidirectional Syncthing backup (TLS 1.3 BEP, 256MB RAM cap) across 4 peer nodes | M2 | survey_explorer_1_gen2 |
| F9 | Scout-to-Commander SSE Protocol | Unidirectional 1Hz push and Server-Sent Events (`POST /api/v1/diagnostic/stream`, `text/event-stream`) eliminating polling battery drain | M3 | survey_explorer_2_gen2 |
| F10 | Apache Ray Compute Orchestration | Distributed execution graph, 128Hz Movesense PySpark processing, DARE-TIES/SLERP genetic model weight merging | M3 | survey_explorer_3 |
| F11 | Obsidian Vault Shared Contextual Memory | Semantic RAG memory graph with Qdrant Vector DB (Port 6333), bidirectional links, and truth enforcement | M3 | survey_explorer_3 |
| F12 | Mermaid.js Data Flow & Training Feedback Diagrams | Visual architectural specifications for Scout-to-Commander SSE pipeline and Crucible training reinforcement loop | M3 | survey_explorer_1/2/3 |
| F13 | Complete Architectural Master Map Assembly | Production of `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md` | M4 | master synthesis |
| F14 | Multi-Stage Verification & Forensic Integrity Gate | Reviewer, Challenger stress-test, and Forensic Integrity Audit verification | M4 | quality gate |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Sellable Apps & Edge Daemons (Peripheral Nerves) | Draft detailed sections for Hardware Sentinel, Mesh Healer, Movesense Hub, Shadow Benchmarker with exact code citations, math, configs | Survey | DONE |
| M2 | Proprietary Infrastructure (Prefrontal Cortex) | Draft detailed sections for The Crucible, Main Hub (:3000/:4000), Obsidian Commander (:8888), Mac Air Sync Orchestrator | M1 | DONE |
| M3 | Global Architecture, Communication Protocols & Mermaid Diagrams | Draft SSE Brain Stem protocol, Apache Ray compute fabric, Obsidian RAG graph, and comprehensive Mermaid.js diagrams | M2 | DONE |
| M4 | Master Ecosystem Map Assembly & Forensic Verification | Compile complete `LAUBURU_APP_ECOSYSTEM.md`, execute Worker build, 2 Reviewers, 2 Challengers, and Forensic Auditor gate | M3 | IN_PROGRESS |

## Interface Contracts & Data Models
### Edge Scout $\to$ Main Hub Telemetry (SSE)
- Endpoint: `POST /api/v1/diagnostic/stream`
- Event Type: `text/event-stream`
- Frequency: 1Hz aggregated push
- Payload Schema: `{ device_id: str, battery_mv: int, thermal_c: float, ram_usage_pct: float, active_mesh_transport: str, status: str, timestamp: str }`

### Crucible Chaos Fix $\to$ Hourly SFTTrainer
- JSONL Schema: `{"prompt": "<incident_description>", "completion": "<verified_python_fix>", "elo": <int >= 1100>, "timestamp": "<iso_8601>"}`
- Storage Path: `04_data_and_memory/data/fine_tune_dataset.jsonl`
- LoRA Target: `Qwen/Qwen2.5-Coder-7B-Instruct` (NF4 4-bit, $r=8, \alpha=16$)

## Code Layout
- Target Artifact: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reconnect_project/LAUBURU_APP_ECOSYSTEM.md`
- Metadata: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reconnect_project/.agents/`
