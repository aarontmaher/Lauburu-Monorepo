# Comprehensive Reconnaissance & Data Contract Report: Cloud API Quotas & TUI Frameworks

- **Author**: Survey Explorer 1 (Codebase Reconnaissance & Data Contracts)
- **Target Workspace**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo`
- **Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/explorer_survey_1`
- **Date**: 2026-08-27
- **Status**: Completed Reconnaissance

---

## Executive Summary

This report establishes the complete architectural reconnaissance and exact data contracts required for building high-performance, cross-platform Terminal User Interfaces (TUIs) in Python (`Textual`), Go (`Bubble Tea`), and Rust (`Ratatui`), integrated with the Lauburu Sovereign Cloud API Quota Manager daemon and Termux edge deployment.

Key Discoveries:
1. **Quota Architecture**: `cloud_api_quota_manager.py` implements an atomic state persistence store using `fcntl.flock` on `.lock` files, UTC midnight resets, and a 5-factor composite heuristic scoring formula:
   $$\text{Score} = 0.40 \cdot Q_{\text{rem\_pct}} + 0.25 \cdot \text{Speed}_{\text{norm}} + 0.25 \cdot \text{Token}_{\text{fit}} + 0.10 \cdot \text{Health}_{\text{score}} - \text{Penalty}_{\text{failures}}$$
2. **State Store Contract**: `cloud_api_quota_state.json` tracks per-provider daily quotas, token ceilings, latency EWMA, consecutive failure penalties, cooldown timestamps, and aggregate metrics.
3. **Monorepo TUI Conventions**: `01_apps/canonical_port` establishes the canonical Lauburu visual design: deep obsidian `#070b12`/`#0b111c` background, slate-200 `#e2e8f0` text, vibrant neon accents (Cyan `#00ffcc`, Sky Blue `#38bdf8`, Magenta `#e879f9`, Green `#4ade80`, Yellow `#facc15`), pinned top navigation tabs (`PinnedTabNavBar`), top-bar dropdowns (`EngineSelectorWidget`), and decoupled async event loops.
4. **Prototypes Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes` is currently clean and empty, ready for structured tri-framework prototyping (`python_textual/`, `go_bubbletea/`, `rust_ratatui/`, and deployment tooling).

---

## 1. Deep Inspection: `cloud_api_quota_manager.py`

### 1.1 Architecture & Core Components

File: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/cloud_api_quota_manager.py` (1,408 LOC)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            CLOUD API QUOTA MANAGER ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   [ CLI / Cron Trigger ]                                                             │
│             │                                                                        │
│             ▼                                                                        │
│   ┌────────────────────────┐         Reads State (fcntl.flock SH)                   │
│   │ WorkloadRouter         │ ─────────────────────────────────┐                      │
│   └────────┬───────────────┘                                  │                      │
│            │                                                  ▼                      │
│            ▼                                      ┌───────────────────────┐          │
│   ┌────────────────────────┐                      │ QuotaStateStore       │          │
│   │ HeuristicRoutingEngine │                      │ (State & Lockfile)    │          │
│   └────────┬───────────────┘                      └───────────┬───────────┘          │
│            │ Multi-Factor Composite Score                     │                      │
│            ▼                                                  │                      │
│   ┌─────────────────────────────────────────────────┐         │ Consumes / Updates   │
│   │ Provider Adapters (Ranked Execution Cascade)    │ ◄───────┘ (fcntl.flock EX)     │
│   │ 1. gemini_free (1500 RPD, 32K context)          │                                │
│   │ 2. cloudflare_ai (1000 RPD, 4K context)         │                                │
│   │ 3. julien_ai (300 RPD, 8K context)              │                                │
│   │ 4. local_mesh (∞ RPD, 16K context fallback)     │                                │
│   └────────┬────────────────────────────────────────┘                                │
│            │ Succeeded / Synthesized Output                                          │
│            ▼                                                                         │
│   ┌────────────────────────┐                                                         │
│   │ LoRADatasetWriter      │ ──► Writes Alpaca/ChatML jsonl to:                      │
│   │ (Dataset & Mirror)     │     1. /Users/aaron/DFS_UNIFIED/lora_datasets/          │
│   └────────────────────────┘     2. 04_data_and_memory/lora_datasets/               │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Mathematical Heuristic Scoring Engine

The routing engine calculates a composite fitness score for each candidate provider:
$$\text{Score} = (0.40 \cdot Q_{\text{rem\_pct}}) + (0.25 \cdot \text{Speed}_{\text{norm}}) + (0.25 \cdot \text{Token}_{\text{fit}}) + (0.10 \cdot \text{Health}_{\text{score}}) - \text{Penalty}_{\text{failures}}$$

Detailed Factor Invariants:
1. **Quota Remaining Percentage ($Q_{\text{rem\_pct}}$)**:
   - For cloud providers: $\max(0.0, \min(1.0, 1.0 - (\text{used\_today} / \text{daily\_limit})))$.
   - For `local_mesh`: Always $1.0$.
2. **Speed Normalization ($\text{Speed}_{\text{norm}}$)**:
   - Baseline speed scale: 200 TPS.
   - $\text{Speed}_{\text{norm}} = \max(0.0, \min(1.0, \text{default\_tps} / 200.0))$.
   - Cloudflare (120 TPS) $\rightarrow 0.60$; Gemini (185 TPS) $\rightarrow 0.925$; Julien (45 TPS) $\rightarrow 0.225$; Local Mesh (90 TPS) $\rightarrow 0.45$.
3. **Token Context Fit ($\text{Token}_{\text{fit}}$)**:
   - Base Fit: $1.0 - 0.2 \cdot (\text{estimated\_tokens} / \text{max\_tokens})$.
   - Domain Affinity Bonuses:
     - `distillation` / `reasoning`: Gemini (+0.15), Julien (+0.15), Local (+0.10).
     - `telemetry` / `summary`: Cloudflare (+0.20), Local (+0.10).
     - `code`: Julien (+0.15), Gemini (+0.15).
     - `prefer_local`: Local (+0.50), Cloud (-0.80).
4. **Health Score ($\text{Health}_{\text{score}}$)**:
   - In cooldown ($t < \text{cooldown\_until}$): $0.05$.
   - Status `degraded` ($\ge 3$ consecutive failures): $0.30$.
   - Consecutive failures $> 0$: $\max(0.1, 1.0 / (1.0 + 0.5 \cdot \text{failures}))$.
   - Healthy: $1.0$.
5. **Failure Penalty ($\text{Penalty}_{\text{failures}}$)**:
   - $0.15 \cdot \text{consecutive\_failures} + 0.50 \text{ (if in cooldown)} + 0.50 \text{ (if prefer\_local and provider is cloud)}$.
6. **Disqualification Invariants**:
   - `used_today >= daily_limit` (for cloud providers).
   - `estimated_tokens > max_tokens`.

### 1.3 Provider Configuration Matrix

| Provider ID | Daily Limit (RPD) | Max Tokens | Default TPS | RPM Limit | Is Local | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `julien_ai` | 300 | 8,192 | 45.0 | 10 | False | Julien AI / @google/jules CLI / REST |
| `cloudflare_ai` | 1,000 | 4,096 | 120.0 | 50 | False | Cloudflare Workers AI `@cf/meta/llama-3.1-8b-instruct` |
| `gemini_free` | 1,500 | 32,768 | 185.0 | 15 | False | Google Gemini `gemini-2.0-flash` Free Tier |
| `local_mesh` | 999,999 ($\infty$) | 16,384 | 90.0 | 1,000 | True | Lauburu 7-Layer Local Mesh (Ports 8081-8084) |

### 1.4 Execution Fallback Cascade
When a cloud provider fails (e.g. HTTP 429 Rate Limit, HTTP 500, Timeout, or Missing Credentials):
1. Router marks outcome as `success=False` with `error_type`.
2. If HTTP 429: sets `cooldown_until = now + 60.0` and status `in_cooldown`.
3. If $\ge 3$ failures: marks status `degraded`.
4. Attempts subsequent ranked candidates in descending order of fitness score.
5. If all cloud candidates fail or are exhausted, initiates Sovereign `local_mesh` fallback.
6. Execution always produces a valid result and appends a certified training pair to `continuous_lora_dataset.jsonl`.

---

## 2. Quota State Contract & Concurrency Invariants

### 2.1 File Inode Paths
- **State File**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.json`
- **Lock File**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.lock`
- **Primary LoRA Dataset**: `/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl`
- **Mirror LoRA Dataset**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_datasets/continuous_lora_dataset.jsonl`
- **Session Log**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/session_logs/cloud_api_quota_manager.log`

### 2.2 Exact JSON Schema (`cloud_api_quota_state.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CloudApiQuotaState",
  "type": "object",
  "required": [
    "version",
    "last_reset",
    "last_reset_date",
    "last_updated",
    "providers",
    "metrics"
  ],
  "properties": {
    "version": { "type": "string", "example": "2.0.0" },
    "last_reset": { "type": "string", "format": "date-time", "example": "2026-08-27T06:38:56.235618+00:00" },
    "last_reset_date": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$", "example": "2026-08-27" },
    "last_updated": { "type": "string", "format": "date-time", "example": "2026-08-27T12:44:39.083683+00:00" },
    "providers": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": [
          "daily_limit",
          "used_today",
          "remaining_pct",
          "avg_latency_ms",
          "max_tokens",
          "consecutive_failures",
          "total_requests",
          "successful_requests",
          "status",
          "cooldown_until",
          "last_used_timestamp"
        ],
        "properties": {
          "daily_limit": { "type": "integer", "minimum": 0 },
          "used_today": { "type": "integer", "minimum": 0 },
          "remaining_pct": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
          "avg_latency_ms": { "type": "number", "minimum": 0.0 },
          "max_tokens": { "type": "integer", "minimum": 1 },
          "consecutive_failures": { "type": "integer", "minimum": 0 },
          "total_requests": { "type": "integer", "minimum": 0 },
          "successful_requests": { "type": "integer", "minimum": 0 },
          "status": { "type": "string", "enum": ["healthy", "in_cooldown", "degraded", "exhausted"] },
          "cooldown_until": { "type": "number", "description": "Unix timestamp in seconds" },
          "last_used_timestamp": { "type": "number", "description": "Unix timestamp in seconds" }
        }
      }
    },
    "metrics": {
      "type": "object",
      "required": [
        "total_tasks_routed",
        "cloud_tasks_succeeded",
        "local_mesh_fallback_count",
        "total_lora_samples_harvested"
      ],
      "properties": {
        "total_tasks_routed": { "type": "integer", "minimum": 0 },
        "cloud_tasks_succeeded": { "type": "integer", "minimum": 0 },
        "local_mesh_fallback_count": { "type": "integer", "minimum": 0 },
        "total_lora_samples_harvested": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

### 2.3 Concurrency & File Locking Rules Across Languages

To guarantee zero race conditions between Python background cron jobs, TUI polling processes, and multi-node Termux watchers:

1. **Lock File Discipline**: All readers and writers must acquire `fcntl.flock` on `cloud_api_quota_state.lock` (not the `.json` file itself).
   - **Shared Reads (SH)**: For read-only TUI refresh operations (`fcntl.LOCK_SH`).
   - **Exclusive Writes (EX)**: For mutating quota state or resetting daily counters (`fcntl.LOCK_EX`).
2. **Atomic Replacement Invariant**:
   - Write new payload to temporary file `cloud_api_quota_state.json.tmp`.
   - Call `flush()` and `fsync()`.
   - Execute atomic POSIX rename `os.replace(".tmp", ".json")`.
3. **Cross-Language Implementations**:
   - **Python**: `fcntl.flock(fd, fcntl.LOCK_SH)` / `fcntl.flock(fd, fcntl.LOCK_EX)`.
   - **Go**: `golang.org/x/sys/unix.Flock(int(f.Fd()), unix.LOCK_SH)` / `unix.LOCK_EX`.
   - **Rust**: `fs2::FileExt::lock_shared(&file)` / `lock_exclusive(&file)`.
4. **UTC Midnight Reset Algorithm**:
   - Evaluate `current_utc_date_str == "YYYY-MM-DD"`.
   - If `current_utc_date_str != state.last_reset_date`:
     - Set `state.last_reset = current_utc_iso`.
     - Set `state.last_reset_date = current_utc_date_str`.
     - For every provider: set `used_today = 0`, `remaining_pct = 1.0`, `consecutive_failures = 0`, `status = "healthy"`, `cooldown_until = 0.0`.

### 2.4 Extended Provider Matrix (Target Expansion)

For future-proofing the TUI monitors and quota managers, the following free-tier providers map directly into the schema:

| Provider | Free Limit (RPD) | Free RPM | Max Context | Default TPS | Suggested Model Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `gemini_free` | 1,500 | 15 | 32,768 | 185.0 | `gemini-2.0-flash` |
| `cloudflare_ai` | 1,000 | 50 | 4,096 | 120.0 | `@cf/meta/llama-3.1-8b-instruct` |
| `julien_ai` | 300 | 10 | 8,192 | 45.0 | `@google/jules` / `gemini-3.1-pro` |
| `groq_free` | 14,400 | 30 | 8,192 | 450.0 | `llama-3.1-8b-instant` |
| `cerebras_free`| 14,400 | 30 | 8,192 | 1,200.0 | `llama3.1-8b` |
| `openrouter_free` | 200 | 20 | 16,384 | 65.0 | `meta-llama/llama-3.1-8b-instruct:free` |
| `github_models` | 150 | 15 | 8,192 | 80.0 | `gpt-4o-mini` / `llama-3.3-70b` |
| `huggingface_free` | 1,000 | 20 | 8,192 | 50.0 | Serverless Inference Hub |
| `local_mesh` | $\infty$ | 1,000 | 16,384 | 90.0 | Ports 8081-8084 (Metal / RPC) |

---

## 3. Monorepo TUI Architecture & Visual Design Patterns

### 3.1 Framework & Core Design Tokens

The canonical TUI in `01_apps/canonical_port/tui` utilizes **Textual + Rich** with a unified visual language:

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [<] Prev │ [1] AGI Term │ [2] Network │ [3] Hardware │ [4] Biometrics │ ... │ [>] Next│
├──────────────────────────────────────────────────────────────────────────────────────┤
│ ⚙ Inference Engine [Ctrl+E]: [🦙 LLAMA.CPP (GGML-RPC)                          ▼]     │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─ CLOUD API QUOTAS & LOCAL MESH TELEMETRY ──────────────────────────────────────┐  │
│  │ PROVIDER       USED / LIMIT     REM %      AVG LAT    FAIL   STATUS            │  │
│  │ gemini_free    0 / 1500         100.0%     512.8ms    0      ● HEALTHY         │  │
│  │ cloudflare_ai  0 / 1000         100.0%     769.2ms    0      ● HEALTHY         │  │
│  │ julien_ai      0 / 300          100.0%    1818.2ms    0      ● HEALTHY         │  │
│  │ local_mesh     1 / ∞            100.0%     801.5ms    0      ● HEALTHY         │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ [Q] Quit  [D] Dark  [R] Refresh  [Ctrl+E] Engine  [< / >] Cycle Screen               │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Canonical Color Palette

| Token Name | Hex Code | Ansi / Terminal Equivalent | Purpose |
| :--- | :--- | :--- | :--- |
| `bg_canvas` | `#070b12` | Dark Navy/Black | Base screen background |
| `bg_surface` | `#0b111c` | Dark Slate/Obsidian | Panels, Header, Nav bar |
| `bg_input` | `#0f172a` | Deep Slate | Select dropdowns, text inputs |
| `border_subtle` | `#1e293b` | Slate 800 | Section dividers and panel borders |
| `text_primary` | `#e2e8f0` | Slate 200 | Body text, labels, active headers |
| `text_muted` | `#94a3b8` | Slate 400 | Subtitles, disabled tabs, table headers |
| `accent_cyan` | `#00ffcc` | Neon Bright Cyan | AGI Terminal, active values, highlights |
| `accent_blue` | `#38bdf8` | Sky Blue 400 | Hardware metrics, endpoints, optimization |
| `accent_green` | `#4ade80` | Neon Green 400 | Healthy status `● HEALTHY`, biometrics |
| `accent_magenta` | `#e879f9` | Fuchsia/Magenta | AI inference, RPC tensor layers |
| `accent_yellow` | `#facc15` | Amber/Yellow 400 | Training runs, ELO ratings, warnings |
| `accent_rose` | `#f43f5e` | Rose/Red 500 | Governance, critical alerts, degraded status |
| `accent_purple` | `#a78bfa` | Violet 400 | Tooling, scripts, daemons |

### 3.3 Key UI Components & Widgets

1. **`PinnedTabNavBar`**:
   - Fixed 1-row header widget.
   - Contains 9 canonical tabs: `[1] AGI Term`, `[2] Network`, `[3] Hardware`, `[4] Biometrics`, `[5] Inference`, `[6] Training`, `[7] Governance`, `[8] Tooling`, `[9] Optimization`.
   - Four responsive condensation tiers:
     - Standard: `[1] AGI Term │ [2] Network │ ...`
     - Compact: `[1] AGI │ [2] Net │ ...`
     - Tiny: `[1] AGI │ [2] Net │ [3] HW │ ...`
     - Micro: `[1] A │ [2] N │ [3] H │ ...`
2. **`EngineSelectorWidget`**:
   - Right-aligned dropdown / hotkey cycler (`[Ctrl+E]` / `[F2]`).
   - Supports 4 distributed inference backends: `llama_rpc`, `exo`, `accelerate`, `petals`.
3. **`DockedShortcutsLegend`**:
   - Fixed 1-row footer widget with keybindings and status tags.
4. **Data Tables & Metric Cards**:
   - High-contrast Rich tables with column styling, latency formatting (`ms`), quota percentages, and glowing status pills (`● HEALTHY`, `● DEGRADED`, `● COOLDOWN`).
5. **Decoupled Telemetry Polling**:
   - Background thread/task reads JSON/blackboard with non-blocking intervals (1 Hz).
   - UI redraw occurs via reactive events, guaranteeing 0 ms rendering stutter.

---

## 4. Current State of `01_apps/canonical_tui_prototypes`

- **Directory Path**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_tui_prototypes`
- **Current Content**: Empty directory (0 files, 0 subdirectories).
- **Target Prototypes to Implement**:
  1. **Python Prototype** (`python_textual/`):
     - Textual App reading `cloud_api_quota_state.json` via `QuotaStateStore`.
     - Live progress bars for quota consumption, sparklines for latency, and reactive provider status tables.
  2. **Go Prototype** (`go_bubbletea/`):
     - Charm `Bubble Tea` + `Lipgloss` styling + `Bubbles` table/progress.
     - POSIX file locking on `cloud_api_quota_state.lock`.
     - Static single-binary compilation for ARM64 Termux.
  3. **Rust Prototype** (`rust_ratatui/`):
     - `Ratatui` + `Crossterm`.
     - High-speed zero-allocation rendering (120+ FPS).
     - Static binary compilation (`cargo build --release`).
  4. **Termux Wireless Deployment & Tooling**:
     - `deploy_termux.sh`: Connects via ADB over TCP (`adb connect <IP>:5555`) or Universal SSH (`ssh termux@<IP> -p 8022`).
     - Provisions toolchains (`pkg update && pkg install -y python golang rust clang`).
     - Synchronizes source, compiles binaries on-device or cross-compiles for `aarch64-linux-android`.
     - `verify_termux_tuis.sh`: Runs headless verification and checks lockfile reading.

---

## 5. Comprehensive Data Contracts & Interfaces for TUI Prototypes

### 5.1 Common Data Model (Cross-Language Specification)

```
Struct QuotaState:
    version: String
    last_reset: DateTime (UTC)
    last_reset_date: String (YYYY-MM-DD)
    last_updated: DateTime (UTC)
    providers: Map<String, ProviderState>
    metrics: GlobalMetrics

Struct ProviderState:
    daily_limit: Integer
    used_today: Integer
    remaining_pct: Float (0.0 .. 1.0)
    avg_latency_ms: Float
    max_tokens: Integer
    consecutive_failures: Integer
    total_requests: Integer
    successful_requests: Integer
    status: String ("healthy" | "in_cooldown" | "degraded" | "exhausted")
    cooldown_until: Float (Epoch seconds)
    last_used_timestamp: Float (Epoch seconds)

Struct GlobalMetrics:
    total_tasks_routed: Integer
    cloud_tasks_succeeded: Integer
    local_mesh_fallback_count: Integer
    total_lora_samples_harvested: Integer
```

### 5.2 Required TUI Display Modules

Each of the three TUI prototypes must render these core visual modules:

1. **Header Banner**:
   - Title: `LAUBURU SOVEREIGN MESH — CLOUD API QUOTA & TELEMETRY HUB`
   - Clock: Live UTC ISO timestamp.
   - Node Target: Active host / Termux device badge.
2. **Provider Quotas Table**:
   - Columns: `Provider`, `Usage / Limit`, `Remaining Bar`, `Avg Latency`, `Failures`, `Status`.
   - Color coding:
     - Remaining $\ge 50\%$: Green (`#4ade80`).
     - Remaining $15\% - 49\%$: Yellow (`#facc15`).
     - Remaining $< 15\%$: Red/Rose (`#f43f5e`).
     - Status: `● HEALTHY` (Green), `⏱ COOLDOWN` (Yellow), `🔻 DEGRADED` (Red), `⛔ EXHAUSTED` (Gray).
3. **Global Metrics Panel**:
   - Total Routed, Cloud Succeeded, Local Fallbacks, Harvested LoRA Training Samples.
4. **Live Activity Feed / Daemon Stream**:
   - Rolling last 5-10 routing actions with timestamp, task ID, selected provider, latency, and $ spend ($0.00).
5. **Interactive Controls & Keybindings**:
   - `[Q]`: Clean exit.
   - `[R]`: Force refresh from state file.
   - `[T]`: Dispatch test task / simulate harvest.
   - `[C]`: Clear / Reset quotas.
   - `[TAB]`: Switch focus between panels.

---

## 6. Edge Deployment Strategy (Termux & Hardware Mesh)

### 6.1 Target Node Hardware
- **L6: Pixel 10 Pro XL** (`100.73.38.87` / `192.168.8.125` / ADB: `192.168.8.125:5555`)
- **L7: Samsung S20+** (`100.84.40.95` / `192.168.8.188` / ADB: `192.168.8.188:5555`)
- **GW: GL.iNet Router** (`192.168.8.1`) with ADB daemon bus.

### 6.2 Automated Provisioning Script Workflow
1. **Network Handshake**:
   - `adb connect <TARGET_IP>:5555`
   - Verify connection via `adb devices`.
2. **Termux Environment Setup**:
   - Wake lock: `adb shell "su -c termux-wake-lock || termux-wake-lock"`
   - Dependency installation:
     ```bash
     pkg update -y
     pkg install -y python python-pip golang rust git ncurses termux-api
     pip install textual rich
     ```
3. **Source Sync**:
   - `adb push 01_apps/canonical_tui_prototypes /data/data/com.termux/files/home/canonical_tui_prototypes`
   - `adb push 04_data_and_memory/data/cloud_api_quota_state.json /data/data/com.termux/files/home/data/cloud_api_quota_state.json`
4. **Compile & Run**:
   - Go: `cd go_bubbletea && go build -o quota_tui_go main.go`
   - Rust: `cd rust_ratatui && cargo build --release`
   - Python: `python3 python_textual/main.py`
5. **Remote Verification**:
   - Run in background with timeout or inspect exit codes to verify error-free launch.

---

## 7. Synthesis & Recommendations for Next Implementation Milestones

1. **Structure `01_apps/canonical_tui_prototypes` into 4 clear modules**:
   ```
   01_apps/canonical_tui_prototypes/
   ├── python_textual/
   │   ├── pyproject.toml
   │   ├── main.py
   │   └── app_styles.tcss
   ├── go_bubbletea/
   │   ├── go.mod
   │   ├── go.sum
   │   └── main.go
   ├── rust_ratatui/
   │   ├── Cargo.toml
   │   └── src/
   │       └── main.rs
   ├── deployment/
   │   ├── deploy_termux.sh
   │   ├── provision_termux_toolchains.sh
   │   └── verify_termux_tuis.py
   └── tests/
       ├── test_python_tui.py
       ├── test_go_tui.py
       └── test_rust_tui.py
   ```
2. **Strict Invariant Adherence**:
   - All three prototypes must strictly honor POSIX file locking on `cloud_api_quota_state.lock`.
   - All three prototypes must match the Canonical color scheme (`#070b12`, `#00ffcc`, `#38bdf8`, `#4ade80`, `#e879f9`, `#facc15`).
   - Zero mock data — read strictly from `04_data_and_memory/data/cloud_api_quota_state.json`.

---
*End of Report.*
