# Project: Canonical Mesh Fallback Terminal (`bluetooth_terminal_ide`)

## Architecture
The Canonical Mesh Fallback Terminal evolves the existing Python Textual Bluetooth Terminal into an autonomous, fault-tolerant, 3-stage mesh recovery system for the 7-Layer Lauburu Mesh Ecosystem. When high-bandwidth networks (Tailscale, Nebula, Wi-Fi 7) collapse, the system provides an autonomous escalation ladder to preserve out-of-band control and restore high-throughput communication.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CANONICAL MESH FALLBACK ESCALATION LADDER                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ STAGE 1: Layer 0 IP-Less Raw Serial Lifeline (BLE GATT NUS)                 │
│ • Transport: Nordic UART Service (6E400001-B5A3-F393-E0A9-E50E24DCCA9E)     │
│ • RX Ch: 6E400002 (Write/WriteNoResp), TX Ch: 6E400003 (Notify)             │
│ • MTU-Aware Paced Chunking (min(MTU-3, 240)B, 18ms pacing delay)            │
│ • NusStreamDeframer (\n delimited JSON-L framing, 64KB bounded buffer)      │
│ • Scope: Strictly OOB text payloads (WOL, RESTART_DAEMON, CYCLE_NET, PING)  │
│ • Anti-Tunneling Guard: Rejects interactive PTY/bulk data on Layer 0        │
├─────────────────────────────────────────────────────────────────────────────┤
│ STAGE 2: Layer 1 Autonomous Bluetooth PAN Escalation                        │
│ • Trigger: Outage Prober detects 3 consecutive failed cycles on Overlays    │
│ • Dual-Mode Execution:                                                      │
│   Vector A: OOB Magic Packet (/nexus ENABLE_PAN) over Stage 1 BLE NUS       │
│   Vector B: Android Edge Shizuku SDK Bridge (UID 2000) forcing BNEP         │
│     (rish -c 'cmd tethering start-tethering bluetooth' / binder / adb)      │
│ • Result: Android Edge spawns bnep0 & DHCP server on 192.168.44.1/24        │
├─────────────────────────────────────────────────────────────────────────────┤
│ STAGE 3: Layer 3 SSH / Mosh High-Throughput Handoff                         │
│ • Detection: Async TCP socket probe on 192.168.44.1:8022 (fallback :22)     │
│ • Debounce Gate: 2 consecutive successful probes confirm daemon readiness   │
│ • Non-Blocking Spawner:                                                     │
│   Mode A (Tmux): tmux split-window -h (zero TUI disruption)                 │
│   Mode B (Standalone): Textual app.suspend() interactive context            │
│   Mode C (Background): Async headless tunnel for Screen Lens Port 4003      │
│ • Adaptive Binary: mosh --ssh='ssh -p 8022' -> fallback to /usr/bin/ssh     │
│ • Watchdog & Demotion: 3s check; 3 misses demotes to Stage 1 + OOB recovery │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
Every feature identified during the Survey phase is mapped to a milestone below:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Textual App Event Loop Fix | Patch un-guarded `while True:` in `watch_stream_pipe` to `while self.is_running:`, preventing thread hangs during teardown | M1 | Survey (Exp 1, Exp 3) |
| 2 | Stage 1 BLE GATT NUS Protocol | Nordic UART Service client, dynamic MTU calculation, 18ms paced chunking, line-delimited JSON-L serialization | M1 | Survey (Exp 1, Exp 2) |
| 3 | Stage 1 Stream Deframer & Anti-Tunneling Guard | `NusStreamDeframer` stream buffer handling multi-chunk notifications without tearing; Anti-Tunneling guard barring bulk payloads | M1 | Survey (Exp 2) |
| 4 | Stage 1 OOB Payload Catalog | Structured command set: `WOL`, `RESTART_DAEMON`, `CYCLE_NET`, `TELEMETRY_REQ`, `ENABLE_PAN`, `PING/PONG` with execution validation | M1 | Survey (Exp 2) |
| 5 | Stage 2 Async Outage Prober | Non-blocking concurrent prober testing Tailscale (100.x.x.x) and Nebula (10.255.x.x) endpoints with 3-cycle sliding window debounce | M2 | Survey (Exp 2) |
| 6 | Stage 2 Dual-Mode Escalation | OOB magic packet dispatch (`ENABLE_PAN`) over BLE NUS, paired with Android Edge Shizuku SDK Bridge (`rish`/binder/adb) forcing BNEP tethering | M2 | Survey (Exp 2) |
| 7 | Stage 3 Subnet Reachability Prober | Non-blocking async TCP connect probe to `192.168.44.1:8022` (fallback `:22`) with 2-probe debounce gate | M3 | Survey (Exp 3) |
| 8 | Stage 3 Session Spawner | Async non-blocking spawner supporting tmux split-window, `app.suspend()`, and background tunnels with adaptive `mosh` -> `ssh` fallback | M3 | Survey (Exp 3) |
| 9 | Stage 3 Watchdog & Demotion Ladder | 3s heartbeat watchdog, 3-miss failure trigger, clean subprocess termination, demotion to Stage 1, and automated OOB resurrection | M3 | Survey (Exp 3) |
| 10 | Textual TUI Stage Integration | Live status badge (`STAGE 1 / 2 / 3`), `/nexus` command routing, unblocked RichLog rendering, zero-freeze async coroutines | M3 | Survey (Exp 1, 2, 3) |
| 11 | E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box test suite under `tests/e2e_mesh_fallback/` covering Feature Coverage, Boundaries, Pairwise, Real-World | M4 / E2E Track | Survey (Exp 3) |
| 12 | Acceptance Criteria Verification (AC1-AC3) | Automated deterministic verification of AC1 (Shizuku logged on `/nexus ENABLE_PAN`), AC2 (Simulated outage triggers 1->2), AC3 (Subnet triggers SSH/Mosh) | M4 / E2E Track | Survey (Exp 3) |
| 13 | Rule 0 AST Zero-Mock Audit | Static AST analysis verifying 0 imports of `unittest.mock`, `MagicMock`, `patch`, or `monkeypatch` in test and production files | M4 / E2E Track | Survey (Exp 3) |
| 14 | Phase 2 Adversarial Coverage Hardening | White-box stress testing, chaos fault injection, and coverage boundary exploration | M5 | Survey (Exp 3) |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Test Suite Infrastructure & Cases | Design and implement 4-Tier test suite (`tests/e2e_mesh_fallback/`), authentic test fixtures, runner, and publish `TEST_READY.md` | none | IN_PROGRESS |
| M1 | Stage 1 Raw Serial Lifeline via NUS | Fix Textual thread loop hang; implement `src/mesh_healer/protocol.py`, `nus_transport.py`, `deframer.py`, OOB command catalog, and anti-tunneling guards | none | PLANNED |
| M2 | Stage 2 Autonomous BT PAN Escalation | Implement `src/mesh_healer/outage_detector.py`, `shizuku_bridge.py`, dual-mode `/nexus ENABLE_PAN` dispatch and Shizuku BNEP activation | M1 | PLANNED |
| M3 | Stage 3 SSH/Mosh Handoff & TUI Integration | Implement `src/mesh_healer/session_spawner.py`, `healer_engine.py`, integrate with `src/bluetooth_terminal_app.py` for TUI event loop safety | M2 | PLANNED |
| M4 | Final Integration & 100% E2E Test Pass | Run master test runner `run_mesh_fallback_e2e_suite.py` verifying 100% pass across Tiers 1-4, AC1, AC2, AC3, and Zero-Mock AST audit | M3, E2E | PLANNED |
| M5 | Phase 2 Adversarial Hardening (Tier 5) | White-box adversarial testing, RF packet loss injection, rapid link flapping, edge error recovery | M4 | PLANNED |

## Interface Contracts

### `MeshHealer` ↔ `BluetoothTerminalApp`
- **Class**: `MeshHealer(app: Optional[BluetoothTerminalApp] = None, ...)`
- **Methods**:
  - `async start_monitoring() -> None`: Starts the background outage detection and reachability watchdogs.
  - `async stop_monitoring() -> None`: Cancels background tasks cleanly during app teardown.
  - `async handle_command(cmd_text: str) -> Optional[str]`: Intercepts `/nexus` and OOB commands. Returns response message or None.
  - `async trigger_pan_escalation(source: str = "manual") -> bool`: Executes dual-mode Stage 2 escalation.
  - `async trigger_stage3_handoff(target_ip: str, port: int) -> bool`: Executes non-blocking SSH/Mosh handoff.
  - `get_state() -> HealerState`: Returns current state (`STAGE_0_NORMAL`, `STAGE_1_RAW_SERIAL`, `STAGE_2_PAN_ESCALATING`, `STAGE_2_PAN_CONNECTED`, `STAGE_3_SSH_MOSH`).
- **Events / Callbacks**:
  - `on_stage_changed(old_stage: HealerState, new_stage: HealerState) -> None`: Dispatches to Textual thread-safe UI updater `call_from_thread`.
  - `on_log_message(level: str, message: str) -> None`: Posts styled status updates directly to Textual `RichLog`.

### `ShizukuBridge` Interface
- **Class**: `ShizukuBridge(custom_rish_path: Optional[str] = None, target_serial: Optional[str] = None)`
- **Methods**:
  - `is_available() -> bool`: Returns True if local `rish` binary or remote ADB daemon is executable.
  - `async execute(cmd: str) -> Tuple[int, str, str]`: Executes privileged shell command returning `(returncode, stdout, stderr)`.
  - `async start_bluetooth_tethering() -> Tuple[bool, str]`: Runs `cmd tethering start-tethering bluetooth` with AIDL and ADB fallbacks.

### `OOBMessage` & `NusStreamDeframer`
- **Class**: `OOBMessage(id: str, cmd: str, params: Dict[str, Any], timestamp: float)`
  - `serialize() -> bytes`: Emits UTF-8 encoded JSON line ending in `\n`.
  - `deserialize(line: str) -> Optional[OOBMessage]`: Safely parses JSON line.
- **Class**: `NusStreamDeframer(max_buffer_size: int = 65536)`
  - `feed(chunk: bytes) -> List[str]`: Ingests chunk, maintains buffer, returns complete stripped lines.

## Code Layout
```
01_apps/bluetooth_terminal_ide/
├── PROJECT.md                               # Living Project Specification (this file)
├── TEST_INFRA.md                            # E2E Test Infrastructure Specification
├── TEST_READY.md                            # Published when E2E suite is fully verified
├── DEAD_ENDS.md                             # Log of invalidated approaches
├── GATE_STATUS.md                           # Iteration Gate Verdicts
├── src/
│   ├── bluetooth_terminal_app.py            # Primary Textual TUI Application (Patched event loop)
│   └── mesh_healer/                         # Core Mesh Fallback Escalation Package
│       ├── __init__.py                      # Package exports (MeshHealer, HealerState, OOBMessage)
│       ├── protocol.py                      # NUS UUIDs, OOBMessage, NusStreamDeframer, MTU chunker
│       ├── nus_transport.py                 # Async BleakClient session manager with paced writing
│       ├── outage_detector.py               # Non-blocking async multi-IP prober with debounce window
│       ├── shizuku_bridge.py                # Android Shizuku SDK / rish / ADB BNEP activation bridge
│       ├── session_spawner.py               # Non-blocking Stage 3 SSH/Mosh spawner (tmux/suspend/tunnel)
│       └── healer_engine.py                 # Master state machine orchestrating 1 -> 2 -> 3 escalation
└── tests/
    └── e2e_mesh_fallback/                   # 4-Tier Zero-Mock E2E Test Suite
        ├── __init__.py
        ├── fixtures/                        # Authentic executable script fixtures (rish, ssh, servers)
        ├── test_tier1_feature_coverage.py   # Tier 1: Isolated feature coverage (>=5 per feature)
        ├── test_tier2_boundary_corner.py    # Tier 2: Boundary & corner cases (MTU, timeouts, flapping)
        ├── test_tier3_cross_feature.py      # Tier 3: Pairwise combinations (TUI + workers + spawner)
        ├── test_tier4_real_world.py         # Tier 4: Real-world acceptance criteria (AC1, AC2, AC3)
        ├── test_zero_mock_compliance.py     # Tier 0: AST Rule 0 static audit
        └── run_mesh_fallback_e2e_suite.py   # Master test runner with exit code 0 enforcement
```
