# 🎬 Lauburu Showrunner: Autonomous Multi-Agent Simulation & Broadcast Engine

## Overview
**Lauburu Showrunner** is the real-time autonomous multi-agent simulation, emergent narrative generation, and interactive broadcast engine of the Lauburu 7-layer mesh ecosystem. It orchestrates autonomous AI personas, ingests live Darwin host telemetry, queries persistent Qdrant vector memory, and streams real-time narrative events and dynamic glassmorphic cyberpunk UI transitions across WebSockets to Flutter (desktop/mobile/web) and standalone web browsers.

---

## 🏛️ Canonical Architecture & Multi-Model Inference Mesh

Showrunner strictly complies with `[[CANONICAL_PROJECT_AND_STORAGE_RULE]]`, `[[01_zero_mock_truth_rule]]`, `[[02_tri_vault_storage_rule]]`, `[[03_host_sanctuary_and_ram_governance]]`, and `[[08_preflight_network_telemetry_model_launch_gate]]`.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         LAUBURU SHOWRUNNER TOPOLOGY                              │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1. MULTI-TIER AI ROUTER (prima.cpp PRP Ring over 10Gbps TB4 DMA Bridge):         │
│    • Port 8082: Qwen 3.8 Max (Sovereign Master Local Orchestrator)               │
│    • Port 8083: Qwen 3.8 Max 27B Abliterated (Adversarial Red Team)             │
│    • Port 8081: Qwen 2.5 Coder 7B (Subordinate Syntax Fallback)                  │
│    • Cloud Tier: Google Gemini 2.5 Flash / OpenRouter (GPT-4o / DeepSeek-V3)     │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 2. PERSISTENT VECTOR MEMORY & TELEMETRY:                                         │
│    • Qdrant Vector Engine: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data...  │
│    • Embedder: sentence-transformers/all-MiniLM-L6-v2 (384-dim cosine)           │
│    • Rule #3 RAM Governor: Darwin Mach kernel memory monitoring (>= 9.6 GB safe) │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 3. MULTI-SURFACE CLIENTS:                                                        │
│    • Web Dashboard (Port 8101 /): Glassmorphic Cyberpunk HTML5/Tailwind/WS       │
│    • Flutter Client (mobile_app): macOS Desktop, iOS, Android, and Web builds    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start & CLI Management

Use the unified master CLI daemon script:

```bash
# Check pre-flight storage health and model endpoints
./run_showrunner.py check

# Start the background daemon on Port 8101
./run_showrunner.py start

# Check status, PID, and active endpoints
./run_showrunner.py status

# Stop the daemon
./run_showrunner.py stop
```

---

## 🌐 Endpoints & WebSockets

- **Web Dashboard:** `http://127.0.0.1:8101/`
- **Real-Time WebSocket Feed:** `ws://127.0.0.1:8101/ws/sim_stream`
- **Status & Telemetry API:** `GET /api/status`
- **Active Personas (NPCs):** `GET /api/npcs`
- **Director Event Injection:** `POST /api/director/event` (JSON: `{"event": "..."}`)
- **Simulation Cadence / Speed:** `POST /api/director/speed` (JSON: `{"interval_seconds": 8.0}`)
- **Simulation Pause / Resume:** `POST /api/director/pause` (JSON: `{"paused": true}`)

---

## 🧪 Empirical Verification Suite

```bash
# Backend & Mesh Integration PyTest Suite (7/7 Passed)
backend/venv/bin/pytest tests/test_lauburu_showrunner_mesh_integrations.py -v

# Flutter Static Analysis & Widget Tests (0 issues, 100% Passed)
cd mobile_app && flutter analyze && flutter test
```

---

## 🔗 Knowledge Graph Linkages
- [[Index]]
- [[CANONICAL_APP_UI_AND_STRUCTURE_RULE]]
- [[E2E_PRIMA_AND_PAN_INTEGRATION_REPORT]]
- [[E2E_APP_SPECULATIVE_VERIFICATION_MATRIX]]

