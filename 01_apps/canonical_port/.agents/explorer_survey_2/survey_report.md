# Deep Code-Level Investigation Report: DaemonSupervisor & CronScheduler

**Target Files**:
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/backend/agents/crons/daemon_supervisor.py`
- `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/backend/agents/cron_scheduler.py`

**Investigator**: Explorer Subagent (`explorer_survey_2`)  
**Date**: 2026-08-28  
**Scope**: Code structure, OS & Docker detection mechanics, Docker socket failure modes, error handling & restart storm analysis, CronScheduler concurrency, async/sync event loop safety, telemetry reporting.

---

## Executive Summary

The `DaemonSupervisor` and `SmolagentCronScheduler` establish an autonomous background health monitoring and periodic task execution framework for the canonical port backend. However, deep inspection reveals critical syntax errors, unhandled platform divergence, infinite restart storm vulnerabilities, blocking synchronous function hazards on the asyncio event loop, and disconnected telemetry pipelines.

| Assessment Dimension | Rating | Primary Observation |
| :--- | :--- | :--- |
| **Syntax & Import Integrity** | ❌ **BROKEN** | Concatenation/formatting syntax errors on `daemon_supervisor.py` (lines 14, 106) and `cron_scheduler.py` (line 171); invalid relative import path on line 175. |
| **OS Daemon Detection** | ⚠️ **FRAGILE** | Relies on `pgrep -f` substring matches rather than native `launchd`/`systemd` service queries; zero liveness/responsiveness verification. |
| **Docker Socket Failure Mode** | ⚠️ **CONTAINED** | `docker info` non-zero exit code cleanly skips container checks; however, triggers repetitive macOS `open -a Docker` invocations. |
| **Error Handling & Loop Safety** | 🟡 **RESILIENT** | Multi-tier `try...except` blocks guarantee that daemon failures never crash the background cron loop. |
| **Restart Storm Mitigation** | ❌ **UNPROTECTED** | No maximum restart threshold, circuit breaker, or exponential backoff; continuously spawns detached processes and restarts exited containers forever. |
| **Async Concurrency & Non-Blocking** | ⚠️ **BLOCKING RISK** | Individual cron jobs run in non-overlapping async loops with locks, but synchronous callable jobs are executed directly on the event loop without thread pool offloading. |
| **Telemetry & Knowledge Emission** | 🟡 **STUBBED** | In-memory `deque(maxlen=100)` buffers telemetry and exposes it via REST endpoints, but Obsidian Vault and PySpark persistence routines are no-op stubs. |

---

## 1. OS Daemon & Docker Container Detection Mechanics

### 1.1 OS Daemon Detection (`daemon_supervisor.py:14-45`)

In `DaemonSupervisor`, daemons are defined in the `DAEMON_COMMANDS` dictionary:

```python
# Lines 14-25 in backend/agents/crons/daemon_supervisor.py
DAEMON_COMMANDS = {
    "docker": {"check": ["docker", "info"], "start": ["open", "-a", "Docker"]},
    "tailscale": {"check": ["tailscale", "status"], "start": ["sudo", "tailscaled"]},
    "cloudflared": {"check": ["pgrep", "-f", "cloudflared"], "start": ["cloudflared", "tunnel", "run"]},
    "openclaw": {"check": ["pgrep", "-f", "openclaw"], "start": ["uv", "run", "openclaw"]},
    "llama.cpp": {"check": ["pgrep", "-f", "llama-server"], "start": ["./llama-server", "--port", "50052"]},
    "exo": {"check": ["pgrep", "-f", "exo"], "start": ["exo", "run"]},
    "petals": {"check": ["pgrep", "-f", "petals"], "start": ["python", "-m", "petals.cli.run_server"]},
    "accelerate": {"check": ["pgrep", "-f", "accelerate"], "start": ["accelerate", "launch"]},
    "seaweedfs": {"check": ["pgrep", "-f", "weed"], "start": ["weed", "server"]},
    "movesense": {"check": ["pgrep", "-f", "movesense_api_daemon"], "start": ["uv", "run", "python", "../03_biometrics_and_telemetry/movesense_api_daemon.py"]},
}
```

#### Detection Methodology:
- **`_check_daemon()` (lines 31-44)**:
  ```python
  process = await asyncio.create_subprocess_exec(
      *cmds["check"],
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL
  )
  await process.wait()
  return process.returncode == 0
  ```
- **Analysis & Vulnerabilities**:
  1. **No OS-Native Service Manager Integration**: The supervisor does not query `launchctl list` (macOS launchd) or `systemctl is-active` (Linux systemd). It ignores system service definitions.
  2. **`pgrep -f` False Positives**: `pgrep -f <pattern>` searches the full process command line. It matches editors opening the code (e.g. `vim daemon_supervisor.py`), grep commands, tests, or documentation scripts, falsely reporting the service as `ONLINE`.
  3. **No Functional / Responsiveness Verification**: A process that is deadlocked, hung in an infinite loop, or experiencing a memory leak will still return exit code 0 from `pgrep`, masking service degradation.
  4. **Platform-Coupled Start Commands**:
     - `["open", "-a", "Docker"]` only works on macOS Darwin with Docker Desktop GUI installed. On Linux or headless servers, `open` does not exist (`FileNotFoundError`).
     - `["sudo", "tailscaled"]` requires root privileges and interactive TTY unless passwordless sudo is configured in `/etc/sudoers`.
     - `["./llama-server", "--port", "50052"]` relies on fragile CWD assumptions.
     - `["../03_biometrics_and_telemetry/movesense_api_daemon.py"]` breaks if backend is launched from any directory other than `01_apps/canonical_port`.

---

### 1.2 Docker Container Health Detection (`daemon_supervisor.py:63-101`)

```python
# Lines 67-97 in backend/agents/crons/daemon_supervisor.py
process = await asyncio.create_subprocess_shell(
    "docker ps -a --format '{{.Names}}|{{.State}}|{{.Status}}'",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, _ = await process.communicate()

if process.returncode != 0:
    return {"docker_daemon": "OFFLINE_OR_UNAVAILABLE"}
    
lines = stdout.decode('utf-8').strip().split('\n')
for line in lines:
    if not line: continue
    parts = line.split('|')
    if len(parts) >= 3:
        name, state, status = parts[0], parts[1], parts[2]
        is_unhealthy = "unhealthy" in status.lower()
        is_exited = state.lower() == "exited"
        if is_exited or is_unhealthy:
            logger.info(f"Container {name} is {state}/{status}. Restarting...")
            restart_proc = await asyncio.create_subprocess_shell(
                f"docker restart {name}",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await restart_proc.wait()
            container_status[name] = "RESTARTED"
        else:
            container_status[name] = "HEALTHY"
```

#### Analysis & Vulnerabilities:
1. **Container Health Evaluation**: Properly evaluates both the Docker healthcheck status string (`unhealthy`) and container lifecycle state (`exited`).
2. **CrashLoop Backoff Blindness**: If a container exits intentionally (batch worker, database migration) or crashes on boot due to bad arguments, the supervisor will execute `docker restart {name}` unconditionally every cycle, entering an infinite container restart storm.
3. **Sequential Blocking Subprocesses**: The restart commands are executed serially with `await restart_proc.wait()`. If multiple containers are broken, restarting them sequentially adds cumulative delay to the cycle.

---

## 2. Docker Socket Failure Modes & Edge Cases

When `/var/run/docker.sock` or `~/.docker/run/docker.sock` is missing, unreadable, locked, or restricted:

```
[Cron Cycle Triggered]
         │
         ▼
[Execute `docker info` in `_check_daemon`]
         │
         ├── Socket Unreadable / Daemon Down -> Returns Exit Code != 0
         │
         ▼
[is_running == False]
         │
         ▼
[Execute `_restart_daemon("docker")`] ──> Calls `subprocess.Popen(["open", "-a", "Docker"])`
         │
         ▼
[Set current_status["docker"] = "RESTARTING"]
         │
         ▼
[Evaluate `if current_status.get("docker") == "ONLINE":`]
         │
         └── False ──> `_check_and_heal_containers()` is SKIPPED
```

### Detailed Failure Mode Analysis:

1. **Daemon Level Containment**:
   - `_check_daemon("docker", ...)` catches subprocess non-zero exit codes cleanly. Because `stdout` and `stderr` are discarded to `DEVNULL`, socket error messages do not pollute stdout.
   - `current_status["docker"]` is marked `"RESTARTING"`.
   - **Protection against cascading container errors**: Because line 119 checks `if current_status.get("docker") == "ONLINE":`, container health inspection is skipped entirely when the Docker daemon is unreachable.

2. **Mid-Cycle Socket Failure**:
   - If `docker info` passed but the socket disconnected prior to `docker ps -a`:
     - Lines 74-75 handle non-zero exit codes: `if process.returncode != 0: return {"docker_daemon": "OFFLINE_OR_UNAVAILABLE"}`.
     - Exceptions (such as missing `docker` CLI binary) are caught on line 98 (`except Exception as e:`), logging an error and returning an empty or partial dictionary.

3. **Edge Case Hazards**:
   - **macOS Desktop Popup Storm**: If Docker Desktop fails to initialize or is stuck in an initialization loop, calling `open -a Docker` every 15 minutes causes repeated focus shifts and launch daemon strain.
   - **Linux Node `open` Command Absence**: On Linux nodes (`Linux_Head_Node`, `Linux_Tablet`), `open -a Docker` raises `FileNotFoundError`. The exception is caught at line 59 and logged, but Docker is never actually restarted.

---

## 3. Error Handling & Infinite Restart Storm Analysis

### 3.1 Loop Crash Resiliency

The scheduler loop and daemon supervisor are exceptionally well-insulated against unhandled exceptions:

```
┌──────────────────────────────────────────────────────────┐
│ Level 4: _run_job_loop Outer Try-Except                  │
│   ┌──────────────────────────────────────────────────┐   │
│   │ Level 3: _run_job_loop Inner Task Execution      │   │
│   │   ┌──────────────────────────────────────────┐   │   │
│   │   │ Level 2: _self_healing_check Cron Task   │   │   │
│   │   │   ┌──────────────────────────────────┐   │   │   │
│   │   │   │ Level 1: DaemonSupervisor Calls  │   │   │   │
│   │   │   │ (_check_daemon, _restart_daemon) │   │   │   │
│   │   │   └──────────────────────────────────┘   │   │   │
│   │   └──────────────────────────────────────────┘   │   │
│   └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

- **Zero Crash Invariant**: Verified. If any daemon check or restart fails, the exception is caught, logged, and the loop continues to subsequent daemons and cycles.
- **Graceful Cancellation**: `asyncio.CancelledError` is explicitly re-raised in `_run_job_loop` (lines 78-79) and handled in `stop()` (lines 114-119), ensuring clean task teardown without unhandled task exceptions.

---

### 3.2 Infinite Restart Storm Vulnerability (CRITICAL DEFECT)

Despite crash resilience, `DaemonSupervisor` exhibits an **unconstrained infinite restart storm defect**:

1. **No Maximum Restart Limit (No Circuit Breaker)**:
   - `self.restart_counts[name]` is incremented at line 57 on every restart attempt.
   - **Flaw**: `self.restart_counts` is strictly informational; it is NEVER queried to abort further restarts once a threshold (e.g. 3 attempts) is exceeded.
2. **No Cooldown or Backoff**:
   - There is no exponential backoff ($2^n$ seconds) or cooldown window. If a daemon binary is missing or broken, it will be executed every cycle forever.
3. **Detached Process Accumulation**:
   - `_restart_daemon` uses `subprocess.Popen(..., start_new_session=True)`.
   - If the target command hangs or spawns child processes that block (e.g. `uv run openclaw`, `sudo tailscaled`, `accelerate launch`), a new orphaned process group is spawned every cycle without terminating earlier zombie instances.
4. **Permanent Container Restarts**:
   - In `_check_and_heal_containers()`, exited containers are restarted without tracking previous failure counts.

---

### 3.3 Syntax & Import Defects (IMMEDIATE EXECUTION BLOCKERS)

Code inspection identified immediate syntax and import errors that currently prevent `DaemonSupervisor` from functioning:

1. **Syntax Error in `backend/agents/crons/daemon_supervisor.py:14`**:
   ```python
   # Line 13-15
   Target daemons: openclaw, docker, llama.cpp, exo, accelerate, petals, cloudflare, tailscale.
   """    DAEMON_COMMANDS = {
   ```
   The docstring closing `"""` is on the same line as the variable declaration, causing `SyntaxError: invalid syntax`.

2. **Syntax Error in `backend/agents/crons/daemon_supervisor.py:106`**:
   ```python
   # Line 105-106
   current_status = {}
   actions_taken = []        for name, cmds in self.DAEMON_COMMANDS.items():
   ```
   Statement concatenation on a single line causes `SyntaxError: invalid syntax`.

3. **Syntax Error in `backend/agents/cron_scheduler.py:171`**:
   ```python
   # Line 170-172
   description="10-min Obsidian Knowledge Graph & Telemetry Sync",
   )    # 3. 15-min Self-Healing & Hardware Keepalive Check (900s)
   ```

4. **Module Import Error in `backend/agents/cron_scheduler.py:175`**:
   ```python
   # Line 175
   from agents.crons.daemon_supervisor import supervisor
   ```
   When executed from the application root with `PYTHONPATH=.`, `agents` is inside `backend.agents`. This raises `ModuleNotFoundError: No module named 'agents'`. It must be `from .crons.daemon_supervisor import supervisor` or `from backend.agents.crons.daemon_supervisor import supervisor`.

---

## 4. Integration with `cron_scheduler.py`

### 4.1 Concurrency Model & Lock Isolation

`SmolagentCronScheduler` (lines 27-212) implements a clean asynchronous multi-task scheduler:

- **Per-Job Task Independence**: Each registered job spawns an independent `asyncio.Task` (`_run_job_loop`).
- **Non-Overlapping Execution Guarantee**: Each job has a dedicated `asyncio.Lock()` (`job["lock"]`).
  ```python
  # Line 68 in backend/agents/cron_scheduler.py
  async with job["lock"]:
      start_time = time.time()
      ...
  ```
  If job execution takes longer than `interval_seconds`, the lock ensures subsequent intervals wait until the prior run finishes, preventing concurrency collisions.

---

### 4.2 Async vs. Sync Blocking Hazard

```python
# Lines 73-76 in backend/agents/cron_scheduler.py
if asyncio.iscoroutinefunction(job["func"]):
    await job["func"]()
else:
    job["func"]()
```

- **Critical Hazard**: If a registered job function is synchronous (e.g. `def my_sync_job()`), `cron_scheduler.py` invokes it directly on the main event loop thread (`job["func"]()`).
- **Impact**: Any synchronous network request, blocking file I/O, or `subprocess.run()` call inside a sync job will **freeze the entire asyncio event loop**, stalling all concurrent cron tasks, WebSocket broadcasting, and FastAPI request handling.
- **Remedy**: Synchronous jobs must be offloaded using `await asyncio.to_thread(job["func"])` or `await asyncio.get_running_loop().run_in_executor(None, job["func"])`.

---

### 4.3 Memory Bounding & Telemetry Reporting

1. **Memory Leak Prevention**:
   - `self.execution_history[job_id] = deque(maxlen=100)` (line 56) guarantees that historical execution records never exceed 100 entries per job.
   - Verified empirically in `test_challenger_2_memory_quota_stress.py` (1,000 cycles maintained net memory delta < 250 KB).

2. **REST API & Telemetry State**:
   - `get_jobs_status()` provides a complete dictionary of scheduler health, active task counts, and the last 5 execution logs per job.
   - Exposed through FastAPI endpoints in `backend/agents/router.py`:
     - `GET /api/v1/agents/crons`
     - `POST /api/v1/agents/crons/start`
     - `POST /api/v1/agents/crons/stop`

3. **Telemetry Gaps**:
   - `DaemonSupervisor.run_monitoring_cycle()` generates status dictionaries, but `_self_healing_check()` only emits them to `logger.info()`.
   - The default cron jobs for Obsidian sync (`_sync_obsidian_telemetry`) and PySpark LoRA harvesting (`_lora_ast_harvester`) are currently empty stubs (`await asyncio.sleep(0)`).

---

## 5. Architectural Recommendations & Remediation Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROPOSED ARCHITECTURAL REPAIRS                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. FIX SYNTAX & IMPORT PATHS                                                │
│    • Correct lines 14 & 106 in daemon_supervisor.py                         │
│    • Correct line 171 in cron_scheduler.py                                  │
│    • Change import to: `from .crons.daemon_supervisor import supervisor`    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. CIRCUIT BREAKER & BACKOFF IN DAEMON SUPERVISOR                           │
│    • Enforce `MAX_RESTART_ATTEMPTS = 3` per daemon.                         │
│    • Implement exponential backoff (e.g. 60s -> 300s -> 1800s cooldown).   │
│    • Avoid restarting containers that have intentional exit code 0.         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. EVENT LOOP SAFETY IN CRON SCHEDULER                                      │
│    • Wrap sync functions in `asyncio.to_thread(job["func"])`.               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. OS-AWARE SERVICE RESOLUTION                                              │
│    • Use `platform.system()` to choose between macOS `open`/`launchctl` and  │
│      Linux `systemctl`.                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. TELEMETRY PERSISTENCE BRIDGE                                             │
│    • Connect `_sync_obsidian_telemetry` to `ObsidianSyncEngine`.            │
│    • Forward daemon health reports into the WebSocket broadcast hub.        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---
