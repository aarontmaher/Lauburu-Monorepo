# Comprehensive E2E Testbed & Infrastructure Survey Report
**Project:** Lauburu Monorepo — Marionette MCP, Shizuku Network Healing & AI Debate  
**Agent:** `survey_explorer_e2e_infra_1`  
**Date:** 2026-08-26  
**Integrity Mode:** Benchmark / Zero-Mock Empirical Verification  

---

## 1. Host Environment & Tooling Assessment

An exhaustive empirical audit of the host environment was performed on macOS Darwin 25.6.0 (Apple Silicon M4 Host, arm64).

### 1.1 Toolchain & Runtime Inventory

| Tool / Runtime | Binary Path | Version | Status & Capability |
|---|---|---|---|
| **Node.js** | `/Users/aaron/.nvm/versions/node/v20.20.2/bin/node` | `v20.20.2` | ✅ Operational. Ready for Node.js stdio MCP servers and frontend test tooling. |
| **npm** | `/Users/aaron/.nvm/versions/node/v20.20.2/bin/npm` | `10.8.2` | ✅ Operational. Ready for package dependencies (`@modelcontextprotocol/sdk`, etc.). |
| **Python 3** | `/usr/bin/python3` | `3.9.6` | ✅ Operational. Core host Python runtime. |
| **uv** | `/Users/aaron/.local/bin/uv` | `0.12.5` | ✅ Operational. Ultra-fast Python package/project manager. |
| **Pytest** | Python `pytest` | `8.4.2` | ✅ Operational (`pytest-asyncio 1.2.0` installed). Primary test runner for multi-tier suites. |
| **ADB** | `/Users/aaron/.local/bin/adb` | `1.0.41` (v37.0.1) | ✅ Operational. Standard Android Debug Bridge daemon host (`127.0.0.1:5037`). |
| **Tailscale** | `/Applications/Tailscale.app/Contents/MacOS/Tailscale` | `1.102.1` | ✅ Operational. Active WireGuard mesh interface (`utun4` @ `100.119.199.76`). |
| **Firefox** | Not found in `/Applications` or on PATH | Missing | ⚠️ Requires installation or download for live headless GeckoDriver sessions. |
| **Geckodriver** | Not found on standard system PATH | Missing | ⚠️ Requires Homebrew install (`brew install geckodriver`) or npm `geckodriver` wrapper. |
| **Homebrew** | `/Users/aaron/.local/bin/brew` | `6.0.19` | ✅ Operational. Available for host binary provisioning if needed. |

### 1.2 Mesh Network Topology & Device Reachability

```
                       ┌────────────────────────────────────────────────────────┐
                       │          Host Mac Mini M4 (100.119.199.76)             │
                       │     Local Subnet: 192.168.8.230 | TB4 DMA: en5         │
                       └───────────────┬────────────────────────┬───────────────┘
                                       │                        │
                     Tailscale Mesh / LAN Subnet           Direct / Standby Links
                                       │                        │
       ┌───────────────────────────────┼────────────────────────┼──────────────────────────────┐
       ▼                               ▼                        ▼                              ▼
┌──────────────┐              ┌─────────────────┐       ┌────────────────┐             ┌──────────────┐
│ Pixel 10 Pro │              │ Samsung Galaxy  │       │ MacBook Pro M1 │             │ GL-MT3600BE  │
│ 100.73.38.87 │              │     S20+        │       │ 100.103.212.21 │             │ Router Gate  │
│ (Active/Relay)│             │ 100.84.40.95    │       │ 169.254.122.166│             │100.122.185.123│
│ Port 5555 TCP│              │ (Idle Standby)  │       │ (Layer 2 Vault)│             │192.168.8.1   │
└──────────────┘              └─────────────────┘       └────────────────┘             └──────────────┘
```

- **Physical USB Connection (`adb devices -l`):** 0 devices currently connected via direct physical USB cable.
- **Wireless ADB TCP/IP (`100.73.38.87:5555` & `100.84.40.95:5555`):** Connection refused on port 5555 (daemons in standby / require wake-lock or pairing).
- **Testbed Strategy:**
  - **Mode A (Synthetic / Mock / Dry-Run):** 100% deterministic test execution using mock ADB subprocess streams, mock MCP stdio pipes, and synthetic debate transcripts. Guaranteed to run in CI/CD environments without external physical hardware.
  - **Mode B (Live Hardware Testbed):** Auto-detects connected ADB devices (`adb get-state`) and live Tailscale endpoints to execute live on-device APK/shell operations when hardware is connected.

---

## 2. 4-Tier E2E Test Suite Design

The E2E test architecture follows the Lauburu Monorepo 4-Tier Hierarchy:
- **Tier 1:** Feature Coverage (Unit & Fundamental Execution)
- **Tier 2:** Boundary & Corner Cases (Extreme payloads, timeouts, fault injection)
- **Tier 3:** Cross-Feature Combinations (Multi-component state machines, concurrency, pipeline chaining)
- **Tier 4:** Real-World Application Scenarios (Full workflows, visual audits, untethered self-healing)

---

### 2.1 Subsystem 1: `marionette-mcp` Programmatic Tool Execution

Controls headless Firefox via GeckoDriver / Marionette JSON-RPC protocol to expose standardized Model Context Protocol (MCP) tools matching Chrome DevTools MCP schemas.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MARIONETTE MCP ARCHITECTURE                                   │
│                                                                                                 │
│   Client (AI / Test Harness)  ◄──[ JSON-RPC 2.0 stdio ]──►  marionette-mcp (Node.js)           │
│                                                                        │                        │
│                                                                        ▼                        │
│                                                          GeckoDriver (HTTP/Marionette)          │
│                                                                        │                        │
│                                                                        ▼                        │
│                                                          Headless Firefox Engine                │
│                                                          (DOM, Canvas, WebGPU, AX Tree)         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Tier 1: Feature Coverage
- **`TC_MAR_T1_01_MCP_HANDSHAKE`**: Verify standard MCP protocol initialization (`initialize`, `tools/list`) over stdio; assert all exposed tools (`navigate`, `take_screenshot`, `get_ax_tree`, `evaluate_script`, `click`, `type_text`) conform to JSON Schema v7.
- **`TC_MAR_T1_02_BROWSER_LIFECYCLE`**: Verify browser launch, session establishment, and clean shutdown without orphan GeckoDriver or Firefox processes.
- **`TC_MAR_T1_03_NAVIGATE_BASIC`**: Execute `navigate` to a local HTTP endpoint (`http://localhost:3000` / `http://localhost:4000` or `data:text/html,...`); verify return confirmation and HTTP 200 status.
- **`TC_MAR_T1_04_SCREENSHOT_BASE64`**: Execute `take_screenshot`; verify output is a valid base64-encoded string, byte length > 10KB, and decoded binary starts with standard PNG magic bytes (`\x89PNG\r\n\x1a\n`).
- **`TC_MAR_T1_05_AX_TREE_STRUCTURE`**: Execute `get_ax_tree`; verify output returns a structured JSON tree containing accessibility roles (`button`, `heading`, `link`, `region`), element names, coordinates, and child hierarchies.
- **`TC_MAR_T1_06_EVALUATE_SCRIPT`**: Execute `evaluate_script` with arithmetic/DOM queries (`window.location.href`, `document.title`); verify exact serializable return values.

#### Tier 2: Boundary & Corner Cases
- **`TC_MAR_T2_01_NAVIGATE_INVALID_URL`**: Attempt navigation to unreachable endpoints (`http://127.0.0.1:99999/down`, `invalid://proto`); verify structured error response (`isError: true`, descriptive message) without server crash or stdio hang.
- **`TC_MAR_T2_02_SCREENSHOT_BLANK_PAGE`**: Capture screenshot on `about:blank` and unrendered DOM; verify valid base64 PNG generation without null pointer exception.
- **`TC_MAR_T2_03_AX_TREE_DEEP_DOM`**: Parse DOM tree nested > 100 levels deep; verify recursive AX parser completes without stack overflow.
- **`TC_MAR_T2_04_LARGE_SCRIPT_PAYLOAD`**: Execute `evaluate_script` returning 5MB serialized array and circular structure; verify safe string truncation or structured circular error.
- **`TC_MAR_T2_05_GECKODRIVER_CRASH_RECOVERY`**: Simulate abrupt GeckoDriver termination (SIGKILL); verify MCP server detects socket closure, cleans up state, and rejects subsequent tool calls with clean error code.
- **`TC_MAR_T2_06_STDIO_BURST_FRAMING`**: Transmit 20 rapid chunked JSON-RPC requests over stdin buffer; verify stdio framing correctly parses all requests without desynchronization.

#### Tier 3: Cross-Feature Combinations & Concurrency
- **`TC_MAR_T3_01_NAV_SCREENSHOT_AX_SYNC`**: Execute pipeline: `navigate(pageA)` -> `take_screenshot` -> `navigate(pageB)` -> `get_ax_tree`; verify visual screenshot and accessibility tree correspond strictly to pageB state.
- **`TC_MAR_T3_02_SESSION_ISOLATION`**: Create successive browser sessions; verify cookies, localStorage, and cached credentials do not leak between isolated contexts.
- **`TC_MAR_T3_03_FRAME_DELTA_HASH_AUDIT`**: Navigate to animated WebGPU/Canvas interface; capture 5 successive screenshots over 2.5 seconds; verify MD5 hash delta between frames proves active rendering.
- **`TC_MAR_T3_04_HIGH_FREQ_SCREENSHOT_STREAM`**: Execute 10 screenshot requests in rapid succession (<100ms intervals); verify memory stability and latency SLA < 500ms per frame.

#### Tier 4: Real-World Application Scenarios
- **`TC_MAR_T4_01_PWA_FULL_VISUAL_AUDIT`**: Full end-to-end audit of Lauburu Frontend (`localhost:4000`): navigate root `/` -> inspect navigation buttons -> click tabs -> capture full-page screenshot -> verify zero layout overlap.
- **`TC_MAR_T4_02_TRI_LENS_CROSS_BROWSER_AUDIT`**: Concurrently audit the same application page via `chrome-devtools-mcp` (Chromium) and `marionette-mcp` (Firefox); cross-verify AX node names and element bounding box parity within 5% tolerance.
- **`TC_MAR_T4_03_TAILSCALE_REMOTE_AUDIT`**: Execute headless visual audit across the Tailscale mesh (`http://100.119.199.76:3000`) with simulated 50ms network latency; assert robust connection retry and timeout handling.

---

### 2.2 Subsystem 2: Shizuku Network Healing Privileged Payload Execution

Enables elevated ADB-level system execution on Android nodes (Pixel 10 Pro XL, Samsung Galaxy S20+) without physical USB tethering or PC connection, bypassing Android Doze mode.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                SHIZUKU SELF-HEALING ARCHITECTURE                                │
│                                                                                                 │
│   Swarm Healer Daemon  ──►  Shizuku Binder IPC / Termux Runner  ──►  Android Framework Privileges│
│                                                                            │                    │
│   • restart_tailscale   (am force-stop + am start com.tailscale.ipn) ◄─────┤                    │
│   • toggle_wifi         (svc wifi disable / enable)                  ◄─────┤                    │
│   • bypass_doze         (dumpsys deviceidle whitelist + termux-lock) ◄─────┤                    │
│   • zombie_pid_hunting  (pgrep uiautomator && kill -9)               ◄─────┘                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Tier 1: Feature Coverage
- **`TC_SHZ_T1_01_BINDER_PERMISSION_CHECK`**: Verify Shizuku service binding and permission query (`check_root_access()` or `shizuku-check` / IPC handshake); assert UID 2000 (Shell) or UID 0 (Root).
- **`TC_SHZ_T1_02_TAILSCALE_LIFECYCLE`**: Execute `start_tailscale()`, `stop_tailscale()`, and `is_installed()`; verify package manager check (`pm list packages | grep com.tailscale.ipn`) and intent dispatch (`am start -n com.tailscale.ipn/.ui.MainActivity`).
- **`TC_SHZ_T1_03_WIFI_TOGGLE`**: Execute `enable_wifi()`, `disable_wifi()`, and `get_wifi_state()`; verify privileged radio manipulation via `svc wifi` and status parsing from `dumpsys wifi`.
- **`TC_SHZ_T1_04_DOZE_WAKELOCK_INJECTION`**: Execute Termux CPU wake lock (`termux-wake-lock`) and battery optimization bypass (`dumpsys deviceidle whitelist +com.termux +com.tailscale.ipn`).
- **`TC_SHZ_T1_05_ZOMBIE_PROCESS_KILL`**: Execute process detection and SIGKILL (`pgrep -f uiautomator`, `kill -9 <PID>`) to eliminate hung ADB testing daemons.

#### Tier 2: Boundary & Corner Cases
- **`TC_SHZ_T2_01_SHIZUKU_SERVICE_UNAVAILABLE`**: Execute payload when Shizuku service is not running; verify graceful error interception, fallback logging, and alert dispatch without unhandled crash.
- **`TC_SHZ_T2_02_COMPLETE_NETWORK_BLACKOUT`**: Execute network recovery sequence when all interfaces (Wi-Fi, LTE, Tailscale) are down; verify execution completes locally via local binder/shell without network socket dependency.
- **`TC_SHZ_T2_03_COMMAND_INJECTION_DEFENSE`**: Submit shell arguments containing special characters (`'; rm -rf /; '`, `&&`, `$()`); verify strict argument sanitization and escaping.
- **`TC_SHZ_T2_04_RAPID_RADIO_FLAPPING`**: Dispatch 5 rapid Wi-Fi toggle commands within 2 seconds; verify debounce protection and deterministic final state.
- **`TC_SHZ_T2_05_CRITICAL_BATTERY_THROTTLE`**: Simulate device battery level < 10% / thermal level EMERGENCY; verify non-essential keepalive loops are paused while preserving core SSH/Tailscale link.

#### Tier 3: Cross-Feature Combinations & State Machine Resilience
- **`TC_SHZ_T3_01_AUTONOMOUS_HEALING_FLOW`**: Execute full self-healing pathway: Detect VPN drop -> Force-stop `com.tailscale.ipn` -> Cycle Wi-Fi radio (`svc wifi disable` -> `svc wifi enable`) -> Start Tailscale intent -> Verify ping connectivity re-established within 10 seconds.
- **`TC_SHZ_T3_02_DOZE_CLEANUP_INTEGRATION`**: Combine wake-lock refresh, phantom process killer bypass (`settings put global settings_enable_monitor_phantom_procs false`), and orphaned process reaping in a single atomic payload.
- **`TC_SHZ_T3_03_DUAL_DEVICE_CONCURRENT_DISPATCH`**: Concurrently dispatch self-healing payloads to Pixel 10 Pro XL and Samsung S20+ testbeds; assert thread isolation and zero race conditions.

#### Tier 4: Real-World Application Scenarios
- **`TC_SHZ_T4_01_UNTETHERED_VPN_HEALING_SIM`**: Simulate unexpected network gateway failure on remote Android node; verify autonomous Shizuku payload executes in background, restores Tailscale tunnel, and resumes SSE telemetry feed to `localhost:3000`.
- **`TC_SHZ_T4_02_COLD_BOOT_RESURRECTION`**: Simulate device reboot; verify companion foreground service auto-initializes upon boot (`BOOT_COMPLETED`), claims Shizuku binder, and relaunches background keepalive daemons without human intervention.

---

### 2.3 Subsystem 3: AI Debate Artifact Validation

Validates the Tri-Orchestrator deliberative debate engine (Cloud Frontier AI, Local Mesh AI, Genetic Evolution Engine) producing definitive architectural decisions, ELO updates, and continuous LoRA datasets.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AI DEBATE PROTOCOL FLOW                                      │
│                                                                                                 │
│   Turn 1: Opening Theses ──► Turn 2: Cross-Examination ──► Turn 3: Synthesis ──► Turn 4: Accord │
│                                                                                    │            │
│   • Consensus Accord (Agreement >= 90%, Unanimous Voting Ledger) ◄─────────────────┤            │
│   • Top 5 Non-Destructive Priorities (Injected into progress.md) ◄─────────────────┤            │
│   • 24/7 LoRA JSONL Dataset Record (instruction/input/thought/output) ◄────────────┤            │
│   • Canonical AI Leaderboard Update (record_match_victory & ELO Delta) ◄───────────┘            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Tier 1: Feature Coverage
- **`TC_DEB_T1_01_4_TURN_STATE_MACHINE`**: Execute full 4-turn deliberative state machine (Turn 1 Opening, Turn 2 Critique, Turn 3 Synthesis, Turn 4 Ratification); verify progression of turn states and speaker allocations.
- **`TC_DEB_T1_02_CONSENSUS_THRESHOLD`**: Calculate mathematical agreement score from voting ledger; assert consensus ratified if and only if agreement score >= 0.90 (90.0%).
- **`TC_DEB_T1_03_TOP5_PRIORITIES_EXTRACTION`**: Extract action priorities from synthesized accord; verify exactly 5 checkable, non-destructive markdown priority items are generated.
- **`TC_DEB_T1_04_LORA_JSONL_SERIALIZATION`**: Format debate transcript into LoRA fine-tuning record; assert valid JSONL conforming to schema `{instruction, input, thought, output, timestamp}`.
- **`TC_DEB_T1_05_ELO_LEADERBOARD_UPDATE`**: Call `CanonicalAILeaderboardEngine.record_match_victory()`; assert winner rating increases, loser rating updates, and ledger matches JSON Schema v7.

#### Tier 2: Boundary & Corner Cases
- **`TC_DEB_T2_01_DEADLOCK_STAGNATION_ESCALATION`**: Simulate split vote (1-1-1) or agreement score < 0.90 across 3 consecutive rounds; verify `[STAGNATION DETECTED]` alert is emitted with structured multi-choice human escalation summary.
- **`TC_DEB_T2_02_CORRUPTED_LEDGER_RECOVERY`**: Pass missing, empty, or malformed JSON to leaderboard engine; verify automatic fallback to default canonical ledger with zero data loss.
- **`TC_DEB_T2_03_NON_DESTRUCTIVE_PROGRESS_INJECTION`**: Inject debate priorities into `progress.md`; verify all existing headings, logs, and historical content remain 100% intact while `## Active Priorities` is cleanly updated.
- **`TC_DEB_T2_04_THOUGHT_TRACE_ESCAPING`**: Serialize debate thought traces containing unescaped double quotes, backslashes, Unicode emojis, and markdown code blocks; verify 100% JSON round-trip fidelity.
- **`TC_DEB_T2_05_EXTREME_ELO_DELTA_BOUNDS`**: Submit debate outcome with extreme efficiency multipliers (eta > 5.0 or eta < 0.1); verify ELO delta clamp prevents rating explosion or negative ratings.

#### Tier 3: Cross-Feature Combinations & Pipeline Integration
- **`TC_DEB_T3_01_DEBATE_TO_EXECUTION_DISPATCH`**: End-to-end pipeline: Execute debate on Shizuku architecture -> ratify consensus on Native Kotlin + Termux fallback -> generate structured payload config -> dispatch to Shizuku testbed runner.
- **`TC_DEB_T3_02_MULTI_MODEL_TRI_LAYER_ROUTING`**: Verify heterogeneous model orchestration across Cloud (Gemini 3.7 Flash High), Local (DeepSeek-R1-32B / Kimi Tandem), and Genetic (MoE Router).
- **`TC_DEB_T3_03_CONCURRENT_DEBATE_SESSIONS`**: Run 3 independent debate topics simultaneously; verify session log and LoRA dataset isolation with zero file write collisions.

#### Tier 4: Real-World Application Scenarios
- **`TC_DEB_T4_01_SHIZUKU_ARCHITECTURE_DEBATE_VALIDATION`**: Execute production debate on "Native Kotlin Shizuku APK vs Termux Shizuku-Runner Daemon"; verify transcript is recorded in `truth_audit_nomad_mesh_debate.jsonl` with clear technical trade-offs evaluated.
- **`TC_DEB_T4_02_CONTINUOUS_TRAINING_HARVESTING`**: Verify that high-scoring debate accord outputs are immediately formatted and ingested into the `localhost:3000` training pipeline for Hourly LoRA `SFTTrainer` distillation.

---

## 3. Master E2E Test Suite Matrix

| # | Subsystem | Requirement Ref | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Real-World) | Total Tests |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| **1** | **Marionette MCP Server** | ORIGINAL_REQUEST §R1 | 6 | 6 | 4 | 3 | **19** |
| **2** | **Shizuku Network Healing** | ORIGINAL_REQUEST §R2 | 5 | 5 | 3 | 2 | **15** |
| **3** | **AI Debate Validation** | ORIGINAL_REQUEST §R3 | 5 | 5 | 3 | 2 | **15** |
| **Total** | **All 3 Subsystems** | **Full Monorepo Scope** | **16** | **16** | **10** | **7** | **49** |

---

## 4. Test Harness Architecture & Automated Runners

### 4.1 Test Suite File Layout

```
/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/
├── tests/
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── run_all_e2e.py                   # Master Unified CLI Runner
│   │   ├── test_marionette_mcp_e2e.py       # Marionette MCP 4-Tier Test Suite (Tiers 1-4)
│   │   ├── test_shizuku_healing_e2e.py      # Shizuku Self-Healing 4-Tier Test Suite (Tiers 1-4)
│   │   ├── test_ai_debate_e2e.py            # AI Debate & Consensus 4-Tier Test Suite (Tiers 1-4)
│   │   ├── mocks/
│   │   │   ├── mock_marionette_server.py    # Synthetic GeckoDriver/Marionette JSON-RPC Stub
│   │   │   ├── mock_shizuku_device.py       # Deterministic Android Binder/ADB Shell Mock
│   │   │   └── mock_debate_orchestrators.py # Synthetic Multi-Model Tri-Orchestrator Provider
│   │   └── fixtures/
│   │       ├── valid_ax_tree.json           # Reference Accessibility Tree Fixture
│   │       ├── sample_screenshot.png        # Reference 1080p Audit Screenshot
│   │       └── sample_lora_dataset.jsonl    # Reference LoRA Training Pair Fixture
```

### 4.2 Automated Runner CLI & Invocation

The master runner provides unified execution, tier filtering, machine-readable JSON reporting, and strict fail-fast semantics:

```bash
# Run full E2E suite across all 4 tiers
python3 tests/e2e/run_all_e2e.py --tier all --verbose

# Run specific tier for quick regression verification
python3 tests/e2e/run_all_e2e.py --tier 1 --fail-fast

# Run via Pytest with parallel execution
pytest tests/e2e/test_marionette_mcp_e2e.py tests/e2e/test_shizuku_healing_e2e.py tests/e2e/test_ai_debate_e2e.py -v

# Generate machine-readable JSON audit report
python3 tests/e2e/run_all_e2e.py --json-output /tmp/e2e_audit_report.json
```

### 4.3 Pass/Fail Semantics & SLA Thresholds

Every test execution is evaluated against strict empirical pass/fail criteria:
1. **Exit Codes:** Exit code `0` strictly requires 100% of assertions across all executed tiers to pass with zero errors, zero unhandled exceptions, and zero skipped core assertions. Exit code `1` is emitted on any assertion failure, timeout violation, or schema mismatch.
2. **Performance & Latency SLAs:**
   - Marionette MCP `take_screenshot`: response time < 3000ms.
   - Marionette MCP `get_ax_tree`: response time < 1500ms.
   - Shizuku privileged command execution: round-trip time < 5000ms.
   - AI Debate consensus agreement score: strictly >= 0.90 (90.0%).
3. **Fidelity & Data Integrity Assertions:**
   - Screenshots: Base64 decoded length > 10KB, first 8 bytes strictly equal `0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A`.
   - AX Trees: Valid JSON conforming to Chrome DevTools MCP AX schema.
   - Priority Injection: Exactly 5 items formatted as `- [ ] <Action>`, zero lines deleted from existing `progress.md`.
   - LoRA Datasets: 100% JSONL valid lines, each containing non-empty `instruction`, `input`, `thought`, and `output`.

---

## 5. Opaque-Box Test Verification Methodology

To enforce the monorepo's **Zero-Mock Truth Enforcement Rule**:
1. **Black-Box Verification:** Tests interact strictly through external public boundaries:
   - Stdio JSON-RPC 2.0 frames for `marionette-mcp`.
   - Subprocess CLI commands (`adb`, `ssh`) and exit status for Shizuku.
   - File artifacts (`.jsonl`, `.json`, `progress.md`) and API endpoints for AI Debate.
2. **Dual-Testbed Execution Mode:**
   - **Mode A (Synthetic / CI Harness):** In environments where external hardware or Firefox binaries are not provisioned, tests utilize synthetic process stubs that validate exact byte streams, JSON-RPC framing, regex parsers, and state machine transitions.
   - **Mode B (Live Hardware Harness):** When live devices or Firefox instances are present, tests automatically detect the active endpoints and execute live commands against real hardware and browser engines.
3. **Continuous Mutation Testing:**
   - Injected adversarial payloads (corrupted JSON, invalid URLs, SIGKILL signals, disconnected network states) verify that systems degrade gracefully and self-heal without cascading process failures.

---

## 6. Pre-Requisite & Host Remediation Recommendations

To enable live execution of all test suites on the host:
1. **Geckodriver Installation:** Run `brew install geckodriver` or install npm package `geckodriver` so `geckodriver` binary is accessible on PATH.
2. **Firefox Browser Installation:** Install Firefox to `/Applications/Firefox.app` (`brew install --cask firefox`).
3. **Android Device ADB TCP Re-Activation:**
   - Connect Pixel 10 Pro XL / Samsung S20+ via USB or execute Termux ADB activation script to enable `adb tcpip 5555`.
   - Ensure `termux-wake-lock` is active on Android nodes to prevent Wi-Fi sleep during background test execution.

---
