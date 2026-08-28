# Scope & Architecture: Milestone 2 (Auto-Adaptive Compute Governor & Opt-In Engine)

## Objective
Deliver a production-ready Auto-Adaptive Compute Governor and User Opt-In Engine for the Distributed Resource & Compute Pooling Manager.

## Features Breakdown

### 1. `src/governor/models.py`
- `OptInLevel`: `LIGHT` ("Light", 30% max compute), `MODERATE` ("Moderate", 60% max compute), `MAXIMUM` ("Maximum", 90% max compute).
- `GovernorMode`: `AUTONOMOUS_SURGE` ("AUTONOMOUS_MAX_SURGE_MODE"), `HUMAN_INTERACTIVE` ("HUMAN_INTERACTIVE_MODE"), `THROTTLED` ("THROTTLED_USER_ACTIVE"), `DRAINING_OFFLOAD` ("DRAINING_FOR_OFFLOAD"), `PAUSED` ("PAUSED_HARD_STOP").
- `WorkloadTask`: `task_id`, `name`, `pid`, `priority`, `ram_required_gb`, `cpu_target_percent`, `is_paused`, `is_offloaded`, `target_node`, `created_at`.
- `OffloadTarget`: `node_id`, `hostname`, `transport`, `rtt_ms`, `available_ram_gb`, `is_eligible`.
- `ThrottleStatus`: `opt_in_level`, `governor_mode`, `is_user_active`, `user_idle_seconds`, `computed_throttle_factor`, `active_local_workloads`, `offloaded_workloads`.

### 2. `src/governor/activity_detector.py`
- Sub-50ms human activity detection.
- CoreGraphics / Quartz ctypes integration (`CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType)`).
- macOS IOHIDSystem fallback if Quartz unavailable.
- `psutil` process scanner for active foreground interactive applications (cursor, code, antigravity, terminal, chrome).
- Synthetic event injection API (`inject_user_activity(event_type, timestamp)`, `reset_activity()`) for deterministic testing without external mocks.
- Background asynchronous polling loop with configurable poll intervals (10ms - 100ms) and subscriber callbacks.

### 3. `src/governor/throttle_controller.py`
- Real-time throttle factor calculation:
  - When user active: throttle factor = 0.0 (PAUSED / fully throttled) or scaled by OptInLevel ceiling.
  - When user idle: computed throttle factor scales up to OptInLevel maximum (Light: 0.30, Moderate: 0.60, Maximum: 0.90).
- Process signal dispatcher: sends `SIGSTOP` / `SIGCONT` to registered workload processes with POSIX error handling.
- Async cooperative yield engine (`async def cooperative_yield()`): throttles async coroutines via event loop sleep proportionally to throttle factor.
- Thread-safe registry of active workloads and process handles.

### 4. `src/governor/workload_offloader.py`
- Mac Mini 24GB memory ceiling enforcement:
  - Total RAM: 24.0 GB
  - Kernel buffer reserve: 2.4 GB hard limit
  - Usable ceiling: 21.6 GB
- Offload decision engine:
  - Monitored RAM usage >= 21.6 GB triggers immediate draining and offload.
  - Priority-based offload routing:
    1. `MacBook_Pro` (node_2) via 10Gbps TB4 (0.27ms RTT)
    2. `Linux_Head_Node` (node_3) via Gigabit LAN / Tailscale
  - Reclaim mechanism: when memory pressure subsides (< 18.0 GB), offloaded workloads can be safely rebalanced back to Mac Mini.

### 5. `src/server/routes.py` & `src/server/governor_routes.py`
- Integrate REST endpoints with FastAPI:
  - `POST /api/governor/opt-in`: Set opt-in profile (Light, Moderate, Maximum).
  - `GET /api/governor/status`: Return current `ThrottleStatus`.
  - `GET /api/governor/workloads`: List registered local and offloaded workloads.
  - `POST /api/governor/workloads/register`: Register new background compute task.
  - `POST /api/governor/offload`: Manually trigger or execute automated offload.
  - `POST /api/governor/reclaim`: Reclaim offloaded workload.
  - `POST /api/governor/activity/inject`: Inject synthetic activity for testing.

### 6. Test Suite
- `tests/test_m2_governor.py`: Comprehensive unit tests for all M2 components.
- `tests/tier1_features/test_governor.py`: Feature validation tests.
- `tests/tier2_boundaries/test_throttle_limits.py`: Boundary and latency tests (<50ms transition).
- `tests/tier2_boundaries/test_memory_ceilings.py`: Memory ceiling boundary tests.
- `tests/tier3_pairwise/test_activity_with_offload.py`: Integration and pairwise tests.
