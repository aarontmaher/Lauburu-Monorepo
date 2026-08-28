# Comprehensive Investigation Report: Tmux Boot Script & System Integration
**Subsystem**: `01_apps/canonical_port/boot_canonical_mesh.sh` & System Integration  
**Author**: Explorer Subagent (`explorer_survey_3`)  
**Date**: 2026-08-28  
**Scope**: Tmux session management, process lifecycle & startup dependencies, environment propagation, edge cases & failure recovery modes.

---

## Executive Summary

The script `boot_canonical_mesh.sh` serves as the primary multi-process orchestrator for the Canonical Port ecosystem, attempting to bring up the 3 core pillars:
1. **FastAPI Unified Backend** (`uvicorn backend.app:app --port 4000` with 12 Spec Modules & WebSocket Telemetry)
2. **Movesense BLE Telemetry Bridge** (`../03_biometrics_and_telemetry/movesense_to_4000_bridge.py`)
3. **Textual TUI Command Center** (`uv run textual run tui/canonical_tui.py` with 9-screen stability hierarchy)

While the script achieves basic bootstrapping in happy-path scenarios, deep code analysis reveals **critical architectural bottlenecks, lifecycle race conditions, environment isolation flaws, and missing daemon orchestrators** (e.g. `ai_debate_tui_sync.py` and `DaemonSupervisor` auto-start).

---

## 1. Tmux Session Management Analysis

### 1.1 Session Creation & Naming
- **Session Identifier**: `SESSION_NAME="lauburu-canonical"` (Line 4).
- **Creation Mode**: `tmux new-session -d -s $SESSION_NAME -n "Canonical Port"` (Line 22). Creates a detached session with a single window named `"Canonical Port"`.
- **Pre-flight Existence Check**:
  ```bash
  tmux has-session -t $SESSION_NAME 2>/dev/null
  if [ $? == 0 ]; then
      echo "Session $SESSION_NAME already exists. Attaching..."
      tmux attach-session -t $SESSION_NAME
      exit 0
  fi
  ```
  **Vulnerability**: If an earlier session crashed or contains dead/hung processes, the script simply attaches to the broken session without verifying pane health or offering a `--restart` / `--kill` / `--force` flag. Furthermore, `[ $? == 0 ]` uses bash-specific `==` instead of POSIX `=`.

### 1.2 Window and Pane Layout Geometry
The script establishes a 3-pane layout within a single window (Window 0):
1. **Pane 0.0 (Left, 50% width, 100% height)**:
   - Runs FastAPI Backend on Port 4000 (`uv run uvicorn backend.app:app --host 0.0.0.0 --port 4000`).
2. **Pane 0.1 (Top-Right, 50% width, 50% height)**:
   - Created via `tmux split-window -h -t $SESSION_NAME:0` (Line 29).
   - Runs Movesense BLE Telemetry Ingestion Bridge.
3. **Pane 0.2 (Bottom-Right, 50% width, 50% height)**:
   - Created via `tmux split-window -v -t $SESSION_NAME:0.1` (Line 35).
   - Runs Textual TUI Command Center.
   - Focused via `tmux select-pane -t $SESSION_NAME:0.2` (Line 41).

```
┌──────────────────────────────┬──────────────────────────────┐
│                              │ Pane 0.1 (Top-Right, 25% area)│
│ Pane 0.0 (Left, 50% width)   │ Movesense BLE Bridge         │
│ FastAPI Backend API          │ `movesense_to_4000_bridge.py`│
│ Port 4000 (12 Spec Modules)  ├──────────────────────────────┤
│                              │ Pane 0.2 (Bottom-Right, 25%) │
│                              │ Textual TUI (9-Screen Hub)   │
│                              │ [FOCUSED ON ATTACH]          │
└──────────────────────────────┴──────────────────────────────┘
```

### 1.3 Layout Ergonomics & Architectural Flaws
- **Severely Constrained TUI Viewport**: The Textual TUI contains 9 heavy screens (ASCII graph renderer, realtime ECG biometrics, hardware matrix, 12 spec modules, AGI coding terminal). Compressing the TUI into a 50%x50% quarter-pane causes extreme UI clipping, truncated tables, and degraded ASCII dependency trees.
- **Recommended Layout**: A 2-window architecture:
  - **Window 1 ("Command Center")**: Full-screen dedicated Textual TUI.
  - **Window 2 ("Daemons & Backend")**: Split panes for FastAPI, BLE Bridge, and AI Debate Sync Daemon.
  - *Or alternatively*, a 75/25 horizontal split where TUI occupies 75% height or width.

---

## 2. Process Startup Sequence, Dependencies & Port Bindings

### 2.1 Service Interaction & Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                   CANONICAL PORT ECOSYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│ 1. FastAPI Backend (0.0.0.0:4000)                           │
│    ├── Spec Modules 00-12 Lifespan Init                     │
│    ├── WebSockets: /ws/telemetry, /ws/network/telemetry     │
│    └── DaemonSupervisor (Inside CronScheduler)              │
│                           ▲                                 │
│        HTTP POST Ingest   │   HTTP / WebSocket Probes       │
│                           │                                 │
│ 2. Movesense BLE Bridge ──┘                                 │
│    └── polls GATT -> POSTs to :4000/api/v1/network/ingest   │
│                                                             │
│ 3. Textual TUI ─────────────────────────────────────────────┘
│    └── Direct in-process SpecModulesBridge & NetworkStore   │
│                                                             │
│ 4. [MISSING IN BOOT SCRIPT] AI Debate Sync Daemon           │
│    └── `tui/services/ai_debate_tui_sync.py` (5-min loop)    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Startup Timing & Fragile Heuristics
- **FastAPI Backend (Pane 0.0)**: Starts immediately.
- **Movesense BLE Bridge (Pane 0.1)**: Uses `sleep 3`. If Python package loading (e.g. `pyspark`, `torch`, `uvicorn`) takes >3.0s, the bridge executes its first connection attempts against a non-listening port (caught silently by `except Exception: pass`).
- **Textual TUI (Pane 0.2)**: Uses `sleep 5`.
- **Absence of Readiness Probing**: Neither Pane 0.1 nor Pane 0.2 polls `curl -s http://127.0.0.1:4000/docs` or uses socket probing before starting. On slower machines (e.g., Linux tablet or high load), 3s/5s delays will fail to synchronize.

### 2.3 The Cron Scheduler & Daemon Supervisor Gap
- In `backend/agents/cron_scheduler.py`, the `SmolagentCronScheduler` registers:
  1. `network_health_scan` (300s)
  2. `obsidian_telemetry_sync` (600s)
  3. `self_healing_keepalive` (900s) -> calls `DaemonSupervisor.run_monitoring_cycle()`
  4. `lora_dataset_harvester` (1800s)
- **Critical Discovery**: `cron_scheduler.start()` is **never called in `backend/app.py` lifespan**. It is only exposed via `POST /api/v1/agents/crons/start`. Consequently, booting the backend via `boot_canonical_mesh.sh` leaves `DaemonSupervisor` completely dormant unless an external actor triggers the REST endpoint.

### 2.4 Port Binding Catalog
| Service | Bound Port | Interface | Protocol | Consumer |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI Unified Backend** | `4000` | `0.0.0.0` | HTTP / WebSocket | BLE Bridge, Web UI, Mesh Nodes |
| **Self-Healing Hub (Infra)** | `18802` / `5000` | `127.0.0.1` | HTTP / REST | Hardware WoL, Keepalive |
| **llama.cpp RPC Shards** | `8081-8085` / `50052` | `0.0.0.0` | TCP / HTTP | Inference Router, Red/Blue Arena |
| **Qdrant Vector DB** | `6333` | `127.0.0.1` | HTTP / gRPC | LoRA Memory Engine |

---

## 3. Environment Variable Inheritance & Propagation

### 3.1 Tmux Environment Isolation Risks
When `tmux send-keys` launches commands inside pane subshells:
1. **Tmux Global Environment vs Shell Environment**: The tmux server retains the environment from when `tmux` was first spawned on the OS. Variables exported in the calling subshell of `boot_canonical_mesh.sh` do NOT automatically propagate to panes unless `tmux set-environment` or `-e` flags are used.
2. **Subshell RC Re-sourcing**: Each pane initializes a fresh interactive shell, executing `~/.zshrc` / `~/.bashrc`. If PATH configurations differ between non-interactive scripts and interactive login shells, unexpected binary mismatches occur.
3. **Absence of Monorepo Environment Variables**:
   Unlike `run_live_tui.sh`, which explicitly exports:
   ```bash
   export PYTHONPATH="${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${SCRIPT_DIR}/../../05_agents_and_swarms/red_blue_arena:${SCRIPT_DIR}/../../00_core_infrastructure/self_healing_hub/src:${PYTHONPATH:-}"
   export TERM="${TERM:-xterm-256color}"
   export COLORTERM="${COLORTERM:-truecolor}"
   ```
   `boot_canonical_mesh.sh` exports **zero environment variables**.
4. **API Token & Secret Propagation**:
   - `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (Cloudflare AI Gateway)
   - `GEMINI_API_KEY` (Gemini Bridge)
   - `JULIEN_API_KEY` (Mistral/Julien Bridge)
   If these tokens are stored in `.env` or temporary session exports, the tmux panes will fail to inherit them unless explicitly loaded (`source .env` or python `dotenv`).
5. **Virtual Environment Invocation**:
   - `boot_canonical_mesh.sh` relies on `uv run <command>`. While `uv` resolves `.venv` within `01_apps/canonical_port`, if `uv` is not in standard system PATH (e.g. located in `~/.local/bin/uv` or `~/.cargo/bin/uv` not loaded in tmux pane), the command fails.

---

## 4. Edge Cases & Failure Recovery Analysis

### 4.1 Edge Case Matrix

| Edge Case | Manifestation in Current Script | Severity | Remediation |
| :--- | :--- | :--- | :--- |
| **Port 4000 Conflict** | `uvicorn` fails with `[Errno 48] Address already in use`. Pane 0.0 drops to shell. Panes 0.1 & 0.2 fail to connect. | **HIGH** | Pre-flight `lsof -i :4000` probe; kill stale PID or alert user before launch. |
| **Missing `tmux`** | Cleanly exits with `Error: tmux is not installed` (Lines 6-9). | **LOW** | Handled. |
| **Missing `uv`** | Panes output `zsh: command not found: uv`. All 3 services fail. | **HIGH** | Add pre-flight `command -v uv` validation. |
| **Stale / Zombie Session** | Script re-attaches to dead session containing idle shell prompts instead of running services. | **HIGH** | Add session health audit; implement `--restart` / `-r` to kill stale session and recreate. |
| **Unclean Shutdown (TUI Quit)** | User exits TUI (`q`). Backend & BLE bridge continue running indefinitely in detached tmux session. | **MEDIUM** | Hook TUI exit to trigger `tmux kill-session -t $SESSION_NAME` or provide shutdown script. |
| **Hardcoded Path Failures** | Commands hardcoded to `cd ~/DFS_UNIFIED/Lauburu-Monorepo/...`. Fails on other hosts/workspaces. | **HIGH** | Dynamic path resolution using `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`. |
| **Missing `ai_debate_tui_sync.py`** | `run_live_tui.sh` spawns the sync daemon, but `boot_canonical_mesh.sh` completely neglects it. | **MEDIUM** | Add Pane 3 / background daemon step for AI Debate live sync. |
| **Signal Handling (Ctrl+C during boot)** | If user interrupts during launch, leaves orphaned half-configured session. | **MEDIUM** | Add `trap cleanup INT TERM` in bootstrapper. |

---

## 5. Architectural Recommendations & Proposed Refactored Bootstrapper

### 5.1 Architecture Refactoring Plan
1. **Dynamic Path Resolution**: Resolve workspace root from `${BASH_SOURCE[0]}`.
2. **Pre-flight Invariant Checks**: Check `tmux`, `uv`, and Port 4000 availability before session creation.
3. **Environment Injection**: Explicitly inject `PYTHONPATH`, `COLORTERM=truecolor`, and propagate API tokens into the Tmux session via `tmux set-environment`.
4. **Polled Readiness Probes**: Replace arbitrary `sleep 3` and `sleep 5` with socket / HTTP polling (`wait_for_port 4000`).
5. **Multi-Window Command Layout**:
   - **Window 0 ("TUI-Hub")**: Full screen dedicated to `canonical_tui.py`.
   - **Window 1 ("Services")**: Split into Backend (Port 4000), BLE Bridge, and AI Debate Sync Daemon.
6. **Auto-Start Cron Scheduler**: Ensure FastAPI backend lifespan or bootstrapper activates `cron_scheduler.start()`.
7. **Session Lifecycle CLI**: Support flags `./boot_canonical_mesh.sh [--restart | --kill | --status | --detached]`.

---

## 6. Proposed Code Refactoring for `boot_canonical_mesh.sh`

```bash
#!/usr/bin/env bash
# ==============================================================================
# Lauburu Mesh - Canonical Port Resilient Multiplexer Bootstrapper
# Version: 4.1.0-CANONICAL
# Subsystem: 01_apps/canonical_port/boot_canonical_mesh.sh
# ==============================================================================
set -euo pipefail

SESSION_NAME="lauburu-canonical"

# 1. Dynamic Script & Monorepo Path Resolution
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
MONOREPO_ROOT="$(cd -P "${SCRIPT_DIR}/../.." && pwd)"

# 2. CLI Argument Handling
ACTION="${1:-boot}"
if [ "$ACTION" == "--kill" ] || [ "$ACTION" == "-k" ]; then
    echo "Stopping Tmux session: $SESSION_NAME..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || echo "No active session found."
    exit 0
elif [ "$ACTION" == "--restart" ] || [ "$ACTION" == "-r" ]; then
    echo "Restarting Tmux session: $SESSION_NAME..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
fi

# 3. Pre-flight Dependency Verification
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed. Please run: brew install tmux" >&2
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv package manager not found on PATH." >&2
    exit 1
fi

# 4. Check for Existing Active Session
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' is already active. Attaching..."
    tmux attach-session -t "$SESSION_NAME"
    exit 0
fi

# 5. Check Port 4000 Availability
if lsof -i :4000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Warning: Port 4000 is already in use by PID: $(lsof -ti :4000). Terminating stale instance..."
    kill -9 $(lsof -ti :4000) 2>/dev/null || true
    sleep 1
fi

echo "=============================================================================="
echo "⚡ BOOTING LAUBURU CANONICAL MESH ECOSYSTEM (TMUX MULTIPLEXER)"
echo "• Workspace: ${SCRIPT_DIR}"
echo "• Session:   ${SESSION_NAME}"
echo "=============================================================================="

# 6. Create Detached Tmux Session
tmux new-session -d -s "$SESSION_NAME" -n "Command Center"

# Export Environment into Tmux Global Context
tmux set-environment -t "$SESSION_NAME" PYTHONPATH "${SCRIPT_DIR}/tui:${SCRIPT_DIR}:${MONOREPO_ROOT}/05_agents_and_swarms/red_blue_arena:${MONOREPO_ROOT}/00_core_infrastructure/self_healing_hub/src"
tmux set-environment -t "$SESSION_NAME" COLORTERM "truecolor"
tmux set-environment -t "$SESSION_NAME" TERM "xterm-256color"

# ------------------------------------------------------------------------------
# WINDOW 1: Background Services & Daemons
# ------------------------------------------------------------------------------
tmux new-window -t "$SESSION_NAME:1" -n "Services"

# Pane 1.0 (Top-Left): FastAPI Backend (Port 4000)
tmux send-keys -t "$SESSION_NAME:1.0" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:1.0" "uv run uvicorn backend.app:app --host 0.0.0.0 --port 4000" C-m

# Pane 1.1 (Top-Right): Movesense BLE Bridge
tmux split-window -h -t "$SESSION_NAME:1"
tmux send-keys -t "$SESSION_NAME:1.1" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:1.1" "while ! nc -z 127.0.0.1 4000 2>/dev/null; do sleep 0.5; done; uv run python ../03_biometrics_and_telemetry/movesense_to_4000_bridge.py" C-m

# Pane 1.2 (Bottom-Right): AI Debate TUI Live Sync Daemon
tmux split-window -v -t "$SESSION_NAME:1.1"
tmux send-keys -t "$SESSION_NAME:1.2" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:1.2" "while ! nc -z 127.0.0.1 4000 2>/dev/null; do sleep 0.5; done; uv run python tui/services/ai_debate_tui_sync.py" C-m

# ------------------------------------------------------------------------------
# WINDOW 0: Dedicated Full-Screen Textual TUI Command Center
# ------------------------------------------------------------------------------
tmux select-window -t "$SESSION_NAME:0"
tmux send-keys -t "$SESSION_NAME:0.0" "cd '${SCRIPT_DIR}'" C-m
tmux send-keys -t "$SESSION_NAME:0.0" "echo 'Waiting for backend on :4000...' && while ! nc -z 127.0.0.1 4000 2>/dev/null; do sleep 0.5; done" C-m
tmux send-keys -t "$SESSION_NAME:0.0" "uv run python tui/canonical_tui.py" C-m

# Focus Window 0 (Command Center) and attach
tmux select-window -t "$SESSION_NAME:0"
if [ "${ACTION}" != "--detached" ] && [ "${ACTION}" != "-d" ]; then
    tmux attach-session -t "$SESSION_NAME"
fi
```
