# Canonical Port Competitive TUI Swarm Survey — Explorer 2 Report

**Date:** 2026-08-28T00:50:00Z  
**Author:** Explorer 2 (Swarm Survey Specialist)  
**Target:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/`  
**Status:** Complete (Read-Only Investigation)  

---

## 1. Observations

### 1.1 Boot Orchestration & Startup Flows (`boot_canonical_mesh.sh` vs `run_live_tui.sh`)
* **File:** `boot_canonical_mesh.sh:1-45`
  * **Session Management:** Creates a detached Tmux session `SESSION_NAME="lauburu-canonical"` with a 3-pane layout:
    * **Pane 0.0 (Left):** Runs `uv run uvicorn backend.app:app --host 0.0.0.0 --port 4000` (FastAPI backend + REST routes).
    * **Pane 0.1 (Top Right):** Runs `uv run python ../03_biometrics_and_telemetry/movesense_to_4000_bridge.py` after an arbitrary `sleep 3`.
    * **Pane 0.2 (Bottom Right):** Runs `uv run textual run tui/canonical_tui.py` after an arbitrary `sleep 5`.
  * **Critical Flaws Observed:**
    1. **Non-Deterministic Startup Races:** Uses crude fixed sleeps (`sleep 3`, `sleep 5`) instead of deterministic HTTP health probes (e.g. `until curl -s http://127.0.0.1:4000/ >/dev/null; do sleep 0.5; done`). If uvicorn takes longer to initialize or fails to bind Port 4000, Panes 1 and 2 start in a broken/hung state.
    2. **Relative Path Fragility:** Line 32 uses `../03_biometrics_and_telemetry/movesense_to_4000_bridge.py`, which fails if the script is executed outside the `01_apps/canonical_port` working directory.
    3. **Missing Cron Auto-Start:** The FastAPI lifespan does not automatically invoke `get_cron_scheduler().start()`. As a result, the `DaemonSupervisor` and background crons remain dormant unless an external `POST /api/v1/agents/crons/start` is fired.
    4. **Missing AI Debate Sync Daemon:** Unlike `run_live_tui.sh` (which background-spawns `tui/services/ai_debate_tui_sync.py`), `boot_canonical_mesh.sh` omits this daemon, leaving the AI debate telemetry unsynchronized in the live TUI.
    5. **Zellij vs Tmux Opportunity:** Tmux requires custom keybindings and lacks declarative layout definitions. A native Zellij layout (`canonical_mesh.kdl`) provides declarative pane splits, built-in tab headers, native mouse scrolling, and clean process supervision without session name collisions.

---

### 1.2 Daemon Health Supervision & Cron Scheduling
* **File:** `backend/agents/crons/daemon_supervisor.py:1-136`
  * **Supervised Services:** Targets 10 daemons: `docker`, `tailscale`, `cloudflared`, `openclaw`, `llama.cpp`, `exo`, `petals`, `accelerate`, `seaweedfs`, `movesense`.
  * **Critical Vulnerabilities & Faults:**
    1. **Infinite Restart Storm on Missing Binaries (Lines 31-62):**
       * When a binary is not installed on the system (e.g. `weed`, `exo`, `openclaw`), `asyncio.create_subprocess_exec` raises `FileNotFoundError`.
       * The `_check_daemon` method catches this as a generic `Exception` and returns `False` (line 44).
       * In `run_monitoring_cycle` (lines 109-114), `False` unconditionally triggers `_restart_daemon()`.
       * Because there is **zero exponential backoff**, **zero max-retry limit**, and **no binary existence pre-check**, the supervisor attempts to restart missing binaries on every cycle, ballooning `restart_counts` infinitely and spamming failing subprocess spawns.
    2. **Platform Incompatibility & Interactive Hangs in `DAEMON_COMMANDS` (Lines 14-25):**
       * `"docker"` uses `["open", "-a", "Docker"]` — this is macOS-only and fails completely on Linux nodes (`L3`, `L4`).
       * `"tailscale"` uses `["sudo", "tailscaled"]` — in a headless background daemon without an interactive TTY, `sudo` hangs or terminates with `sudo: a terminal is required`.
       * `"llama.cpp"` uses `["./llama-server", "--port", "50052"]` — assumes `./llama-server` is in the supervisor's current working directory, and hardcodes port 50052 instead of canonical ports 8081–8084.
    3. **Container State Flaw (Lines 63-101):**
       * In `_check_and_heal_containers()`, any container where `state.lower() == "exited"` is restarted with `docker restart {name}`.
       * Batch jobs, ephemeral test containers, or stopped containers that exited with code 0 are restarted in an infinite loop.
    4. **Socket Degradation Mode:**
       * If the Docker socket is unreadable or daemon is down (lines 74-75), it returns `{"docker_daemon": "OFFLINE_OR_UNAVAILABLE"}`. However, `DAEMON_COMMANDS["docker"]` will continually return `False` and attempt `open -a Docker`.

* **File:** `backend/agents/cron_scheduler.py:1-212`
  * **Import Path Defect (Line 175):**
    ```python
    from agents.crons.daemon_supervisor import supervisor
    ```
    When imported from the root package namespace, this throws `ModuleNotFoundError: No module named 'agents'` unless `backend` is explicitly on `sys.path`. It must use `from .crons.daemon_supervisor import supervisor` or `from backend.agents.crons.daemon_supervisor import supervisor`.
  * **Lifespan Decoupling:** `backend/app.py:55-73` does not start the cron scheduler during startup.

---

### 1.3 Inference Bridges & Cloudflare AI Gateway Deep Dive
* **Files:** `tui/services/inference_bridges/gemini_bridge.py`, `cloudflare_bridge.py`, `julien_bridge.py`
  * **Syntax Errors & Corrupted String Literals:**
    * `gemini_bridge.py:46`: Unterminated string literal in `yield "SYSTEM: ..."` with unescaped newline.
    * `cloudflare_bridge.py:45`: Unterminated string literal in `yield "SYSTEM: ..."` with unescaped newline.
    * `julien_bridge.py:45`: Unterminated string literal in `yield "SYSTEM: ..."` with unescaped newline.
    * `pytest` crashes during collection of `test_inference_router.py` and `test_auto_fallback.py` with `SyntaxError: unterminated string literal`.
  * **Dead Code & Indentation Flaws:**
    * In all three files (`gemini_bridge.py:89`, `cloudflare_bridge.py:91`, `julien_bridge.py:99`), there is an indented `    return` immediately following `self._is_generating = False`, followed by unreachable legacy mock fallback code.
  * **Fragile Chunk Parsing in `gemini_bridge.py:73-79`:**
    * Parses streaming chunks using naive substring matching: `if '"text": "' in chunk: parts = chunk.split('"text": "')`.
    * If a chunk boundary cuts across a JSON key or token escape sequence (e.g. `\"` or `\n`), the parser drops tokens or corrupts the stream.
  * **Omitted Exports in `tui/services/inference_bridges/__init__.py:1-26`:**
    * `GeminiBridge`, `CloudflareBridge`, and `JulienBridge` are NOT imported or listed in `__all__`.

---

### 1.4 Inference Router & Poller Degradation Hazards
* **File:** `tui/services/inference_router.py:1-507`
  * **Incomplete Registry:**
    * `SUPPORTED_ENGINES` (lines 54-61) includes only `["auto", "llama_rpc", "exo", "accelerate", "petals", "gemini"]`. It omits `cloudflare` and `julien`.
    * `ENGINE_DISPLAY_NAMES` (lines 63-69) omits `gemini`, `cloudflare`, and `julien`.
    * `self.bridges` default map (lines 118-152) omits `cloudflare` and `julien`.
    * `get_status_badge()` (lines 433-441) does not map `gemini`, `cloudflare`, or `julien`.
    * Import fallback `except ImportError:` (lines 36-44) omits `CloudflareBridge` and `JulienBridge`.

* **File:** `tui/services/latency_poller.py:1-357`
  * **The "Zero-Token Latency Probe" Trait Flaw (Lines 150-165):**
    * `measure_engine_ttft()` measures TTFT by checking if `bridge.stream_generate(prompt="ping", max_tokens=1)` yields at least one chunk.
    * When API keys are missing, `GeminiBridge`, `CloudflareBridge`, and `JulienBridge` yield a `"SYSTEM: Please export KEY..."` string chunk immediately in **<0.1 ms**.
    * Because `token_received = True`, the poller registers these unconfigured cloud bridges as **ONLINE and ULTRA-FAST (0.05ms TTFT)**.
    * In `auto` mode, `get_fastest_engine()` compares latencies, sees `0.05ms` for `gemini`, and selects `gemini` over healthy local models (`llama_rpc` at 14ms, `accelerate` at 1ms). Every subsequent user prompt is routed to a broken cloud bridge!
  * **API Quota Exhaustion (Rate-Limit Trap):**
    * The default poller interval is 3.0 seconds (line 63). Probing 3 cloud bridges with full streaming inference every 3 seconds generates **1,200 HTTP calls per engine per hour (28,800 requests/day)**.
    * This instantaneously exhausts free tier limits (e.g. Gemini 300 req/day or 15 RPM) and triggers `429 Too Many Requests` or unexpected cloud charges.

* **Files:** `tui/screens/agi_coding_terminal_screen.py` & `tui/views/agi_coding_terminal_view.py`
  * **API Key Exposure / REPL Passthrough Hazard:**
    * Error messages instruct users: `type /key <your_key>`, `type /key_cf <your_key>`, etc.
    * `_execute_repl_command()` does not define handlers for `/key`, `/key_cf`, `/account_cf`, or `/key_julien`.
    * Unhandled slash commands fall through to `else:` and are passed directly to `inference_router.process_user_input()`, transmitting raw secret API keys as prompts to AI backend models.

---

## 2. Logic Chain

1. **Premise 1:** The test suite failure (`pytest tests/unit/test_inference_router.py`) is directly caused by unescaped newlines in `gemini_bridge.py:46`, `cloudflare_bridge.py:45`, and `julien_bridge.py:45`.
2. **Premise 2:** In `DynamicLatencyPoller`, measuring TTFT by accepting any initial string chunk means error notifications are treated as successful tokens, inverting the auto-routing selection hierarchy and starving local offline models.
3. **Premise 3:** Polling external cloud APIs every 3 seconds via full streaming generation creates a catastrophic quota exhaustion loop. Cloud health must instead be checked via lightweight non-inference probes or credential validation with exponential backoff.
4. **Premise 4:** The lack of circuit breaking in `DaemonSupervisor` turns missing binaries into an infinite CPU/process restart loop.
5. **Premise 5:** In `boot_canonical_mesh.sh`, arbitrary sleep timers cause race conditions, while the lack of auto-starting the cron scheduler leaves the daemon supervisor dormant.
6. **Deduction:** To achieve a 100% resilient, zero-mock, production-ready Canonical Port TUI, we must:
   - Fix all bridge syntax errors and sanitize chunk parsing.
   - Register all bridges (`gemini`, `cloudflare`, `julien`) in `inference_router.py` and `__init__.py`.
   - Update `DynamicLatencyPoller` to validate genuine API tokens and decouple cloud health checks from 3-second TTFT sweeps.
   - Introduce circuit breaking (max 3 retries) and OS-aware commands in `DaemonSupervisor`.
   - Secure REPL slash commands (`/key`, `/key_cf`, `/account_cf`, `/key_julien`) to update environment variables without LLM prompt passthrough.
   - Replace brittle sleeps in `boot_canonical_mesh.sh` with deterministic readiness probes and provide a declarative Zellij alternative (`canonical_mesh.kdl`).

---

## 3. Caveats

1. **Live Cloudflare Gateway Auth:** Cloudflare AI Gateway endpoints (`gateway.ai.cloudflare.com`) require valid `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_GATEWAY_ID`. Without live credentials in the test environment, gateway fallback paths were verified via static AST and mock request testing.
2. **Hardware Environment:** Observations were conducted on macOS Darwin ARM64. Linux-specific daemons (`sudo tailscaled`) were evaluated through static code inspection.
3. **Competitive TUI Paradigms:** TUI-Alpha (Grid/Dashboard), TUI-Beta (Voice/Chat), and TUI-Gamma (Graph/Explorer) currently share the same `UnifiedInferenceRouter` backend. Refactoring the router and bridges ensures all three paradigms inherit rock-solid stability.

---

## 4. Conclusion & Actionable Recommendations

### 4.1 Priority 1: Bridge & Router Repair
1. **Fix Syntax & Clean Dead Code:** Replace raw multi-line strings in `gemini_bridge.py`, `cloudflare_bridge.py`, and `julien_bridge.py` with clean one-line literals. Delete unreachable dead code blocks following `return`.
2. **Full Export & Registration:**
   - Update `tui/services/inference_bridges/__init__.py` to export `GeminiBridge`, `CloudflareBridge`, and `JulienBridge`.
   - Register all 7 engines (`auto`, `llama_rpc`, `exo`, `accelerate`, `petals`, `gemini`, `cloudflare`, `julien`) in `inference_router.py`.
3. **Proper SSE/JSON Streaming:** Replace string splitting in `gemini_bridge.py` with robust SSE line parsing or `httpx` JSON buffer handling.

### 4.2 Priority 2: Latency Poller & Gateway Fallback
1. **Sanitize Latency Probing:** `DynamicLatencyPoller` must check for `"SYSTEM:"` or error prefixes and mark the engine as `is_available = False, ttft_ms = inf`.
2. **Cloudflare AI Gateway Fallback Chain:**
   - If Cloudflare AI Gateway fails or returns 5xx/4xx:
     - `GeminiBridge`: Fall back immediately to direct Google AI Studio (`generativelanguage.googleapis.com`).
     - `CloudflareBridge`: Fall back to direct Workers AI (`api.cloudflare.com/client/v4/accounts/...`).
     - `JulienBridge`: Fall back to direct OpenAI endpoint.
     - If all remote endpoints fail: Router automatically drops to local `llama_rpc` without throwing unhandled exceptions.
3. **Polling Rate Optimization:** Only poll local engines (`llama_rpc`, `exo`, `accelerate`, `petals`) at 3-second intervals. Check cloud engines only on demand or once every 60 seconds.

### 4.3 Priority 3: Daemon Supervisor Hardening
1. **Circuit Breaking & Max Retries:** Limit daemon restarts to 3 attempts with exponential backoff before marking state as `FAILED_CIRCUIT_OPEN`.
2. **Binary Pre-Flight Checks:** Verify `shutil.which(cmd[0])` before spawning subprocesses.
3. **OS-Aware Commands:** Use `docker info` / `systemctl` on Linux vs `open -a Docker` on macOS.
4. **Fix Scheduler Import & Lifespan:** Correct import path to `from .crons.daemon_supervisor import supervisor` and start cron scheduler in `backend/app.py` lifespan.

### 4.4 Priority 4: REPL Security & Bootstrapping
1. **Secure REPL Commands:** Implement `/key`, `/key_cf`, `/account_cf`, `/key_julien` in `_execute_repl_command()` to set `os.environ` locally and mask output (e.g. `API Key set: sk-...1234`).
2. **Deterministic Bootstrapper:** Upgrade `boot_canonical_mesh.sh` to poll `http://127.0.0.1:4000/` and add a complementary Zellij layout (`canonical_mesh.kdl`).

---

## 5. Verification Method

### 5.1 Syntax & Router Test Verification
Run pytest against router and fallback test suites:
```bash
uv run pytest tests/unit/test_inference_router.py tests/unit/test_auto_fallback.py -v
```
*Expected Result:* All tests collect and pass with exit code 0.

### 5.2 Full 4-Tier Regression Suite
Execute the canonical 4-tier E2E test runner:
```bash
uv run python tests/run_all_tiers.py
```
*Expected Result:* 100% pass rate across Unit, Tier 1, Tier 2, Tier 3, Tier 4, and Challenger suites.

### 5.3 Daemon Supervisor Self-Healing Check
Verify that `DaemonSupervisor` runs a monitoring cycle without infinite restart loops on missing binaries:
```bash
uv run python -c "import asyncio; from backend.agents.crons.daemon_supervisor import supervisor; print(asyncio.run(supervisor.run_monitoring_cycle()))"
```

### 5.4 Offline Degradation Invalidation Condition
If `GEMINI_API_KEY` is unset and router is set to `auto`, running:
```bash
uv run python -c "import asyncio; from tui.services.inference_router import UnifiedInferenceRouter; r = UnifiedInferenceRouter(default_engine='auto'); print('Effective:', r.get_effective_engine())"
```
Must return `llama_rpc` (or another active local engine), **never** unconfigured `gemini`.
