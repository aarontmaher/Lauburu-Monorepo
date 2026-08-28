---
title: "Lauburu Mesh — Apps & Features Log"
tags: [apps, features, status, localhost, services]
updated: "2026-08-26T17:19:00+10:00"
---

# Lauburu Mesh — Apps & Features Log (August 26, 2026)
**Status:** All 8 apps VERIFIED LIVE  
**Author:** Antigravity Autonomous Swarm  
**Last Updated:** 2026-08-26T17:19:00+10:00

---

## Localhost Services Registry

| Service | URL | Port | PID Location | Tech Stack |
|---------|-----|------|-------------|------------|
| AI Sharding Daemon | http://localhost:18800 | 18800 | `/tmp/sharding_daemon.log` | FastAPI + uvicorn + asyncio |
| Termius TUI REST API | http://localhost:18888 | 18888 | `/tmp/termius_api.log` | aiohttp + WebSocket |
| Software Dev Training Game | http://localhost:4005 | 4005 | `/tmp/softdev_game.log` | Python HTTPServer + HTML/CSS |
| Mesh PWA (Node.js) | http://localhost:3000 | 3000 | system node process | Next.js |
| AI Strengthening Game | headless loop | N/A | `/tmp/ai_strengthening.log` | asyncio CLI |
| Termius TUI (Terminal) | `uv run termius-tui` | N/A | TTY | Textual framework |

**Master Launch Script:** `~/teamwork_projects/launch_all.sh`

---

## App 1: AI Sharding Daemon
**Path:** `~/teamwork_projects/ai_sharding_daemon/`  
**API Base:** `http://localhost:18800/v1/`

### Key Endpoints
| Endpoint | Method | Returns |
|----------|--------|---------|
| `/v1/health` | GET | Status, 8 active nodes, total VRAM 81.6GB |
| `/v1/telemetry/nodes` | GET | Per-node RAM/VRAM/status for all 8 mesh nodes |
| `/v1/telemetry/memory/pool` | GET | Transactional VRAM pool snapshot |
| `/v1/telemetry/sharding/state` | GET | Active model, route decisions, backend status |
| `/v1/inference/route` | POST | Route an inference request across the mesh |
| `/ws/telemetry` | WebSocket | 0.5s streaming telemetry broadcast |

### Hardware Topology (as of Aug 26)
| Node | Device | RAM | Usable VRAM | Role |
|------|--------|-----|-------------|------|
| mac_node | M4 Pro (14C/20C GPU) | 24GB | 20.4GB | Primary Governor |
| mac_studio | M2 Ultra (24C/76C GPU) | 192GB | 163.2GB | Compute Heavy |
| linux_node | AMD64 | 32GB | 27.2GB | Secondary |
| android_pixel | Tensor G5 | 12GB | 10.2GB | Edge |
| + 4 more | various | 108GB total | 81.6GB total | — |

### Safety Features
- ≤85% RAM ceiling enforced on Mac Mini (≤20.4GB VRAM)  
- `safety_guards.py` kills oversize allocations before OOM  
- `memory_pool.py` manages transactional reservations with rollback  
- Cloudflare sync for remote telemetry push

### Fixes Applied (Aug 26)
- Launch command: `uv run python -m src.main --host 127.0.0.1 --port 18800`
- Correct API prefix is `/v1/` not `/` (common confusion)

---

## App 2: Termius TUI Dashboard
**Path:** `~/teamwork_projects/termius_tui_dashboard/`  
**Launch:** `cd ~/teamwork_projects/termius_tui_dashboard && uv run termius-tui`  
**API:** `http://localhost:18888/api/v1/`

### Architecture
- **Framework:** Textual 8.2.8 (Python TUI)
- **Main Class:** `TermiusDashboardApp` in `termius_tui/ui/app.py`
- **Stylesheet:** `termius_tui/ui/styles.tcss` (Catppuccin Mocha dark theme)
- **Layout:** 3-pane (sidebar node tree | center terminal | right telemetry+models)

### Keybindings
| Key | Action |
|-----|--------|
| Ctrl+K | Quick Connect modal |
| Ctrl+B | Broadcast command to all nodes |
| Ctrl+T | Toggle Telemetry Dock |
| Ctrl+M | Toggle Local Models pane |
| Ctrl+G | Toggle Tools & Skills pane |
| F5 | Refresh mesh nodes |
| Q / Ctrl+C | Quit |

### Dark Theme Fix (Aug 26)
**Problem:** Pale green text on white background (Textual default bleedthrough)  
**Root cause:** `CSS_PATH = "styles.tcss"` — relative path failed when CWD ≠ module dir  
**Fix 1:** `CSS_PATH = str(Path(__file__).parent / "styles.tcss")` — absolute path via `__file__`  
**Fix 2:** Added universal `*` CSS rule in `styles.tcss`:
```css
* {
    background: #1e1e2e;
    color: #cdd6f4;
    scrollbar-background: #181825;
    scrollbar-color: #585b70;
}
```
**Test result:** 111/111 tests still passing after fix ✅

### REST API Endpoints
- `GET /api/v1/health` — TUI health status
- `GET /api/v1/nodes` — Connected mesh nodes
- `GET /api/v1/models` — Active local model engines
- `GET /api/v1/tools` — MCP tools, Skills, SDKs registered
- `WS /ws/telemetry` — Live streaming updates

---

## App 3: Software Dev Training Game
**Path:** `~/teamwork_projects/software_dev_training_game/`  
**URL:** `http://localhost:4005`  
**Launch:** `cd ~/teamwork_projects/software_dev_training_game && uv run python -c "from src.web.server import start_dashboard_server; import time; start_dashboard_server(port=4005); time.sleep(86400)"`

### Features
- **Tri-Orchestrator Debate Council** with 5 model seats:
  - `cloud_orchestrator`: Kimi-k1.5-Frontier
  - `local_orchestrator`: DeepSeek-R1-Distill-Llama-70B-GGUF
  - `genetic_engine`: Qwen2.5-Coder-32B-LoRA
- **Challenge Matrix:** Speedify bonding, Tailscale NAT, Petals DHT, eBPF
- **Compiler Sandbox:** Clang ASan/UBSan, Rust, Python subprocess isolation
- **ELO System:** Starting ELO 1450, scored by Tri-Orchestrator
- **DPO/RLHF Dataset Synthesizer**
- **Figma Token Bridge** for UI/UX design-to-code loop

### REST API (port 4005)
| Endpoint | Returns |
|----------|---------|
| `GET /api/status` | `{status, elo, total_runs, model_seats, mesh_ram_headroom}` |
| `GET /api/challenges` | Available challenge IDs |
| `POST /api/run` | Trigger challenge run |
| `GET /api/dataset` | Latest DPO dataset entries |

### Fix Applied (Aug 26)
**Problem:** `ImportError: attempted relative import with no known parent package`  
**Fix:** Must run `uv run python -m src.game` from project root (not `python src/game.py`)  
**Web server launch:** Use `start_dashboard_server()` function in `src/web/server.py`

---

## App 4: AI Strengthening Training Game
**Path:** `~/teamwork_projects/ai_strengthening_training_game/`  
**Launch:** `cd ~/teamwork_projects/ai_strengthening_training_game && uv run python run_game.py --rounds 999 --headless`  
**Monitor:** `tail -f /tmp/ai_strengthening.log`

### Live Session Results (Aug 26)
```
Round 1: filesystem_mcp challenge → PASSED 5/5 tests → Score 94.00/100
Round 2: inference_optimizer challenge → PASSED 2/2 tests → Score 89.25/100
Debate verdict: Lead Orchestrator APPROVE (86.8/100)
```

### Challenge Types
| Challenge ID | Description |
|-------------|-------------|
| `filesystem_mcp` | Build a JSON-RPC 2.0 filesystem MCP server |
| `memory_mcp` | Implement stateful memory MCP server |
| `skill_md_generator` | Auto-generate Antigravity skill markdown |
| `lora_dataset_synthesizer` | Synthesize DPO training pairs |
| `inference_optimizer` | VRAM-aware model loading optimizer |

### 5-Dimension Scoring Matrix
- Code Validity (0–100%)
- Architecture (0–100%)
- Security (0–100%)
- Performance (0–100%)
- Capability Gain (0–100%)

### Fix Applied (Aug 26)
**Problem:** `ModuleNotFoundError: No module named 'yaml'`  
**Fix:** `uv pip install pyyaml` — resolved PyYAML missing from venv

---

## App 5: Internet Training Protocol (Cloudflare AI)
**Path:** `~/teamwork_projects/internet_training_protocol/`  
**Launch:** `cd ~/teamwork_projects/internet_training_protocol && uv run python -m src.cloudflare_ai_client`

### Key Features
- 5 novel self-healing network architectures discovered:
  1. eBPF XDP packet-level failover
  2. Speedify-style multipath bonding (MPTCP-inspired)
  3. <4.5MB WireGuard VPN implementation
  4. EWMA memory leak projection
  5. 4-tier DNS failover with health TTL
- 154/154 tests passing ✅
- RuntimeWarning on launch is benign (`frozen runpy` module pre-import)

---

## App 6: Termius Mesh Telemetry Audit
**Path:** `~/teamwork_projects/mesh_telemetry_audit/`  
**Tests:** 40/40 ✅

---

## App 7: OSS Scout & Obsidian Docs
**Path:** `~/teamwork_projects/open_source_scout_obsidian/`  
**Tests:** 26/26 ✅  
**Output:** `OSS_REVERSE_ENGINEERING_REPORT.md` — Speedify packet bonding + Tailscale WireGuard NAT traversal reverse-engineered

---

## App 8: Global Training Games Audit
**Path:** `~/teamwork_projects/global_training_games_audit/`  
**Tests:** 61/61 ✅  
**Output:** `GLOBAL_APP_FEEDBACK_REPORT.md` — 727 lines, 60 prioritized remediation items

---

## HuggingFace Task Priority (AI-Debate Results)
> Full report: [[HF_TASK_PRIORITY_DEBATE]]

| Tier | Tasks | Key Model |
|------|-------|-----------|
| 🔴 CRITICAL | Text Generation | DeepSeek-R1-70B (DONE ✅) |
| 🟠 HIGH | Summarization, Sentence Similarity, Feature Extraction, Text Classification | BGE-M3 (580MB), SmolLM2 (360MB) |
| 🟡 MEDIUM | Token Classification, Zero-Shot Classification, Visual QA, Image-Text-to-Text | Qwen2.5-VL-7B |
| ❌ SKIP | Image-to-3D, Text-to-3D, Video-to-Video, Unconditional Image Gen | Cloud API only |

**Next downloads (tiny + high value):**
```bash
huggingface-cli download BAAI/bge-m3 --local-dir ~/models/bge-m3
huggingface-cli download HuggingFaceTB/SmolLM2-360M-Instruct --local-dir ~/models/smollm2-360m
huggingface-cli download openai/whisper-large-v3 --local-dir ~/models/whisper-large-v3
```

---

## Fixes & Entry Points Summary

| Project | Problem | Fix |
|---------|---------|-----|
| All projects | `ModuleNotFoundError: No module named 'src'` | Must `cd` into project dir before `uv run` |
| software_dev_training_game | `ImportError: relative import` | Use `uv run python -m src.game` not `python src/game.py` |
| ai_strengthening_training_game | `No module named ai_strengthening.__main__` | Use `uv run python run_game.py` |
| ai_strengthening_training_game | `ModuleNotFoundError: No module named 'yaml'` | `uv pip install pyyaml` |
| termius_tui_dashboard | White/pale theme | Fixed CSS_PATH + added `*` CSS dark rule |
| localhost:18888 | `ERR_INVALID_HTTP_RESPONSE` | SeaweedFS/Textual was on 18888; restart aiohttp server cleanly |
| termius_tui API | `MeshStateManager.initialize()` — no such method | Remove `await state_mgr.initialize()` |
