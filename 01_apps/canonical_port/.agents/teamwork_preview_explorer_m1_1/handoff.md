# Handoff Report: Resource Cap (Max 1 Active Subagent) Locking Mechanism & Governor Architecture

**Agent:** `teamwork_preview_explorer_m1_1` (Explorer 1 — Milestone 1: 4-Way Debate Governance / The Devil's Lock)  
**Working Directory:** `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_1`  
**Timestamp:** 2026-08-29T03:24:30+10:00  
**Handoff Type:** Hard (Task Complete)

---

## 1. Observation

Direct inspection of `PROJECT.md`, `ORIGINAL_REQUEST.md`, `TEST_INFRA.md`, and existing monorepo concurrency implementations revealed the following concrete architectural constraints and requirements:

1. **Governance Interface Contract (`PROJECT.md` § Interface Contracts, lines 35-40):**
   - The gating layer must reside in `backend/devils_lock_governor.py` as class `DevilsLockGovernor`.
   - `check_resource_cap() -> bool`: Must return `True` when no active subagent is running (slot free), and `False` when a subagent is actively executing.
   - `validate_preflight_locks() -> Dict[str, Any]`: Must validate all three gates (Resource Cap, VRAM Headroom $\ge 15\%$, Genetic ELO selection), raising `DevilsLockError` if any check fails.

2. **Core Concurrency Requirements (`ORIGINAL_REQUEST.md` § R2.1):**
   - Resource Cap strictly enforces **maximum 1 active subagent** running simultaneously across the entire ecosystem.
   - The lock must be both **thread-safe** (preventing race conditions among worker threads in the daemon/FastAPI/TUI processes) and **process-safe** (preventing race conditions across independent CLI executions, background daemons, or separate pytest worker processes).

3. **Crash & Deadlock Vulnerabilities in Naive Implementations:**
   - **Naive In-Memory Lock (`threading.Lock` / `threading.RLock`)**: Fails completely across OS process boundaries (e.g., if a subagent runs as a separate process or if another CLI/daemon attempts spawning).
   - **Naive Lockfile (`open("lock.pid", "x")`)**: Vulnerable to permanent deadlocks if a process crashes (SIGKILL, segfault, power cut) without executing `os.remove()`, creating an unrecoverable "stale lock" state.
   - **Kernel Advisory Lock (`fcntl.flock`)**: Operating systems (macOS and Linux) automatically close open file descriptors and release `flock` locks when a process terminates, ensuring that the kernel cannot leave a stale kernel lock regardless of how violently the process died.

4. **Monorepo Persistence Conventions (`tui/services/blackboard_store.py` lines 934-968):**
   - Disk writes must be atomic using temporary files with unique PID/thread identifiers (`.tmp.{pid}.{tid}`) followed by `os.replace` to prevent partial reads or race corruption.

---

## 2. Logic Chain

From the observations above, we establish the step-by-step logic chain governing the design:

```
[Concurrent Invocations (Threads / Processes)]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Step 1: Thread Synchronization (threading.RLock)       │
│ Serializes threads within the current Python process.  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Step 2: Kernel Advisory Lock (fcntl.flock LOCK_EX)     │
│ Non-blocking attempt (LOCK_EX | LOCK_NB).              │
│ - If locked by another live process -> Blocked / False │
│ - If acquired -> Proceed to State Validation           │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Step 3: State Inspection & Dead PID Liveness Probe     │
│ Read active state file (devils_subagent_state.json).   │
│ - If state exists with PID: probe os.kill(pid, 0)      │
│   * If ProcessLookupError -> PID dead -> Auto-cleanup  │
│   * If alive & different subagent -> Lock Active       │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ Step 4: Atomic State Registration                      │
│ Write SubagentRegistration data atomically via         │
│ .tmp.{pid}.{tid} -> os.replace.                        │
│ Maintain open file descriptor until released.          │
└────────────────────────────────────────────────────────┘
```

1. **Dual-Layer Synchronization:**
   - **Layer 1 (Process-Internal):** A `threading.RLock` serializes multi-threaded calls within the same process, protecting in-memory caches, open file descriptors, and registration dicts.
   - **Layer 2 (Cross-Process):** `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)` acquires an exclusive kernel-level lock on `devils_subagent_resource.lock`. If another process holds the lock, the kernel immediately raises `BlockingIOError` / `OSError(EWOULDBLOCK)`, enabling instant non-blocking detection.

2. **Self-Healing Dead PID Recovery:**
   - When inspecting the lock state (`check_resource_cap()`, `get_active_subagent()`, or before `acquire()`):
     - The governor reads `devils_subagent_state.json`.
     - If a recorded PID exists, it executes `os.kill(pid, 0)`.
     - If `os.kill(pid, 0)` raises `ProcessLookupError` (or `OSError` with `errno.ESRCH`), the process has terminated.
     - Because `fcntl.flock` was already auto-released by the OS kernel upon process death, the governor safely removes the stale `devils_subagent_state.json` and in-memory references, self-healing the slot without manual user intervention.

3. **Reentrancy and Ownership Validation:**
   - If the *same* `subagent_id` requests lock verification while holding it, the governor acknowledges ownership.
   - If a *different* `subagent_id` or unregistered caller attempts acquisition while a live PID is active, the governor raises `ResourceCapExceededError` containing the active subagent's full diagnostic metadata (PID, task name, model, registered timestamp).

4. **Lifecycle Safety (Context Manager):**
   - Context manager `@contextlib.contextmanager` guarantees that upon exit (either clean termination or unhandled exception), `release_resource_lock()` is executed in a `finally:` block, closing the descriptor, releasing the `flock`, and atomically wiping the state file.

---

## 3. Caveats

1. **POSIX Scope:** `fcntl.flock` is native to POSIX systems (macOS and Linux). Since the Lauburu Monorepo environment exclusively runs on macOS (Darwin) and Debian Linux nodes, `fcntl` is universally available.
2. **PID Recycling:** In rare operating system conditions where a PID is rapidly recycled by the kernel to an unrelated process, the kernel `flock` provides the authoritative source of truth. If the original process died, its kernel `flock` was released even if another process was subsequently assigned the same PID.
3. **Lock Directory Permissions:** The lock directory (default `/tmp/lauburu_locks/`) must be writable by the running user. The governor must ensure `os.makedirs(lock_dir, exist_ok=True)` during initialization.
4. **Read-Only Explorer Mandate:** This report provides the architectural design, exact signatures, and test specifications. The actual code implementation will be performed by the Implementer agent.

---

## 4. Conclusion & Recommended Implementation

### 4.1 Error Class Hierarchy (`backend/devils_lock_governor.py`)

```python
class DevilsLockError(Exception):
    """Base exception for all 4-Way Debate Devil's Lock governance failures."""
    pass

class ResourceCapExceededError(DevilsLockError):
    """Raised when the resource cap (max 1 active subagent) is exceeded."""
    def __init__(self, message: str, active_subagent: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.active_subagent = active_subagent or {}

class VRAMHeadroomExceededError(DevilsLockError):
    """Raised when free VRAM headroom is below the 15% minimum threshold."""
    def __init__(self, message: str, free_pct: float, threshold_pct: float = 15.0):
        super().__init__(message)
        self.free_pct = free_pct
        self.threshold_pct = threshold_pct

class LeaderboardSelectionError(DevilsLockError):
    """Raised when genetic ELO model selection fails or leaderboard is unparseable."""
    pass
```

### 4.2 Data Model: `SubagentRegistration`

```python
from dataclasses import dataclass, field
import time
from typing import Optional, Dict, Any

@dataclass
class SubagentRegistration:
    subagent_id: str
    pid: int
    task_name: str
    model: str
    worktree_path: Optional[str] = None
    registered_at: float = field(default_factory=time.time)
    heartbeat_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subagent_id": self.subagent_id,
            "pid": self.pid,
            "task_name": self.task_name,
            "model": self.model,
            "worktree_path": self.worktree_path,
            "registered_at": self.registered_at,
            "heartbeat_at": self.heartbeat_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentRegistration":
        return cls(
            subagent_id=data["subagent_id"],
            pid=int(data["pid"]),
            task_name=data.get("task_name", ""),
            model=data.get("model", ""),
            worktree_path=data.get("worktree_path"),
            registered_at=float(data.get("registered_at", time.time())),
            heartbeat_at=float(data.get("heartbeat_at", time.time())),
            metadata=data.get("metadata", {}),
        )
```

### 4.3 `DevilsLockGovernor` Complete Architecture Specification

```python
import os
import sys
import fcntl
import json
import time
import errno
import threading
import contextlib
from typing import Optional, Tuple, Dict, Any

class DevilsLockGovernor:
    """
    4-Way Debate Devil's Lock Governor.
    Enforces:
      1. Resource Cap: Max 1 active subagent via thread & process flock.
      2. VRAM Headroom Check: check_vram_and_lock() blocking if free VRAM < 15.0%.
      3. Genetic ELO Mandate: select_highest_elo_model_for_ui() reading canonical_ai_leaderboard.json.
    """

    DEFAULT_LOCK_DIR = "/tmp/lauburu_locks"

    def __init__(
        self,
        lock_dir: Optional[str] = None,
        lock_file_name: str = "devils_subagent_resource.lock",
        state_file_name: str = "devils_subagent_state.json",
        min_free_vram_pct: float = 15.0,
        leaderboard_path: Optional[str] = None,
    ):
        self.lock_dir = lock_dir or self.DEFAULT_LOCK_DIR
        os.makedirs(self.lock_dir, exist_ok=True)

        self.lock_file_path = os.path.join(self.lock_dir, lock_file_name)
        self.state_file_path = os.path.join(self.lock_dir, state_file_name)
        self.min_free_vram_pct = min_free_vram_pct
        self.leaderboard_path = leaderboard_path

        self._thread_lock = threading.RLock()
        self._lock_fd: Optional[int] = None
        self._active_registration: Optional[SubagentRegistration] = None

    # ------------------------------------------------------------------
    # Helper: PID Liveness & Self-Healing
    # ------------------------------------------------------------------
    @staticmethod
    def is_pid_alive(pid: int) -> bool:
        """Probe if a PID is genuinely running using signal 0."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Process exists but owned by another user
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False
            return False

    def _read_persisted_state(self) -> Optional[SubagentRegistration]:
        """Read and parse the subagent state file if it exists."""
        if not os.path.isfile(self.state_file_path):
            return None
        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return SubagentRegistration.from_dict(data)
        except Exception:
            return None

    def _write_persisted_state(self, reg: SubagentRegistration) -> None:
        """Atomically persist subagent registration to disk."""
        tmp_path = f"{self.state_file_path}.tmp.{os.getpid()}.{threading.get_ident()}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(reg.to_dict(), f, indent=2)
            os.replace(tmp_path, self.state_file_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _clear_persisted_state(self) -> None:
        """Remove persisted state file cleanly."""
        if os.path.isfile(self.state_file_path):
            try:
                os.remove(self.state_file_path)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Gate 1: Resource Cap (Max 1 Active Subagent)
    # ------------------------------------------------------------------
    def check_resource_cap(self) -> bool:
        """
        Returns True if the resource slot is available (no active subagent).
        Returns False if an active subagent is currently running.
        Automatically cleans up stale locks if a recorded PID is dead.
        """
        with self._thread_lock:
            # 1. Check in-memory state
            if self._active_registration is not None:
                if not self.is_pid_alive(self._active_registration.pid):
                    self._cleanup_stale_lock("In-memory dead PID detected")
                else:
                    return False

            # 2. Check disk-persisted state
            persisted = self._read_persisted_state()
            if persisted is not None:
                if not self.is_pid_alive(persisted.pid):
                    self._cleanup_stale_lock("Disk-persisted dead PID detected")
                else:
                    self._active_registration = persisted
                    return False

            # 3. Test flock availability without holding it
            try:
                test_fd = os.open(self.lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
                try:
                    fcntl.flock(test_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(test_fd, fcntl.LOCK_UN)
                    return True
                except (BlockingIOError, OSError):
                    return False
                finally:
                    os.close(test_fd)
            except Exception:
                return True

    def acquire_resource_lock(
        self,
        subagent_id: str,
        pid: Optional[int] = None,
        task_name: str = "",
        model: str = "",
        worktree_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SubagentRegistration:
        """
        Acquire the exclusive resource lock for a subagent.
        Raises ResourceCapExceededError if another subagent is already active.
        """
        target_pid = pid or os.getpid()

        with self._thread_lock:
            # 1. If currently held by same subagent, update registration
            if (
                self._active_registration is not None
                and self._active_registration.subagent_id == subagent_id
                and self.is_pid_alive(self._active_registration.pid)
            ):
                self._active_registration.heartbeat_at = time.time()
                self._write_persisted_state(self._active_registration)
                return self._active_registration

            # 2. Ensure slot is available (performing dead PID cleanup if needed)
            if not self.check_resource_cap():
                active = self.get_active_subagent()
                active_dict = active.to_dict() if active else {}
                raise ResourceCapExceededError(
                    f"Resource Cap Exceeded: Max 1 active subagent allowed. Currently active: {active_dict.get('subagent_id', 'unknown')} (PID {active_dict.get('pid', 'unknown')})",
                    active_subagent=active_dict
                )

            # 3. Acquire OS kernel flock
            fd = os.open(self.lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (BlockingIOError, OSError) as e:
                os.close(fd)
                active = self.get_active_subagent()
                raise ResourceCapExceededError(
                    f"Resource Cap Exceeded: Kernel file lock held by active process.",
                    active_subagent=active.to_dict() if active else {}
                ) from e

            # 4. Record active file descriptor & registration
            self._lock_fd = fd
            registration = SubagentRegistration(
                subagent_id=subagent_id,
                pid=target_pid,
                task_name=task_name,
                model=model,
                worktree_path=worktree_path,
                registered_at=time.time(),
                heartbeat_at=time.time(),
                metadata=metadata or {},
            )
            self._active_registration = registration
            self._write_persisted_state(registration)
            return registration

    def release_resource_lock(
        self,
        subagent_id: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Release the active subagent resource lock and clear disk state.
        """
        with self._thread_lock:
            if not force and subagent_id and self._active_registration:
                if self._active_registration.subagent_id != subagent_id:
                    return False

            # Release flock and close fd
            if self._lock_fd is not None:
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                except Exception:
                    pass
                try:
                    os.close(self._lock_fd)
                except Exception:
                    pass
                self._lock_fd = None

            self._active_registration = None
            self._clear_persisted_state()
            return True

    def get_active_subagent(self) -> Optional[SubagentRegistration]:
        """Get active subagent registration if genuinely alive, else None."""
        with self._thread_lock:
            if self._active_registration is not None:
                if self.is_pid_alive(self._active_registration.pid):
                    return self._active_registration
                else:
                    self._cleanup_stale_lock("Dead PID in get_active_subagent")

            persisted = self._read_persisted_state()
            if persisted is not None:
                if self.is_pid_alive(persisted.pid):
                    self._active_registration = persisted
                    return persisted
                else:
                    self._cleanup_stale_lock("Dead PID in get_active_subagent persisted state")

            return None

    def _cleanup_stale_lock(self, reason: str = "") -> None:
        """Self-heal stale lock files and descriptors."""
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(self._lock_fd)
            except Exception:
                pass
            self._lock_fd = None
        self._active_registration = None
        self._clear_persisted_state()

    def heartbeat(self, subagent_id: str) -> bool:
        """Update heartbeat timestamp for the active subagent."""
        with self._thread_lock:
            if (
                self._active_registration is not None
                and self._active_registration.subagent_id == subagent_id
            ):
                self._active_registration.heartbeat_at = time.time()
                self._write_persisted_state(self._active_registration)
                return True
            return False

    @contextlib.contextmanager
    def subagent_lock_context(
        self,
        subagent_id: str,
        task_name: str = "",
        model: str = "",
        worktree_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager safely acquiring and releasing the resource lock."""
        reg = self.acquire_resource_lock(
            subagent_id=subagent_id,
            task_name=task_name,
            model=model,
            worktree_path=worktree_path,
            metadata=metadata,
        )
        try:
            yield reg
        finally:
            self.release_resource_lock(subagent_id=subagent_id, force=True)

    # ------------------------------------------------------------------
    # Preflight Validation Aggregator
    # ------------------------------------------------------------------
    def validate_preflight_locks(
        self,
        override_free_vram_pct: Optional[float] = None,
        leaderboard_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates all 3 Devil's Lock gates in sequence.
        Raises DevilsLockError (or specific subclass) if any gate fails.
        """
        # 1. Resource Cap Check
        if not self.check_resource_cap():
            active = self.get_active_subagent()
            active_dict = active.to_dict() if active else {}
            raise ResourceCapExceededError(
                f"Resource Cap Exceeded: Only 1 active subagent allowed. Active: {active_dict.get('subagent_id')}",
                active_subagent=active_dict
            )

        # 2. VRAM Check (Delegated to Explorer 2 design)
        vram_ok, free_gb, free_pct = self.check_vram_and_lock(override_free_pct=override_free_vram_pct)
        if not vram_ok:
            raise VRAMHeadroomExceededError(
                f"VRAM Lock Engaged: Free VRAM ({free_pct}%) is under the {self.min_free_vram_pct}% threshold ({free_gb} GB free).",
                free_pct=free_pct,
                threshold_pct=self.min_free_vram_pct,
            )

        # 3. Genetic ELO Model Selection (Delegated to Explorer 3 design)
        selected_model = self.select_highest_elo_model_for_ui(leaderboard_path=leaderboard_path)

        return {
            "resource_cap_passed": True,
            "vram_headroom_passed": True,
            "free_vram_gb": free_gb,
            "free_vram_pct": free_pct,
            "selected_model": selected_model,
            "status": "APPROVED",
            "timestamp": time.time(),
        }
```

---

## 5. Verification Method

### 5.1 Test Execution Command
```bash
uv run pytest tests/unit/test_devils_lock_governance.py -v
```

### 5.2 Recommended Unit Test Specifications (`tests/unit/test_devils_lock_governance.py`)

The test writer and implementer should implement the following 8 comprehensive test cases for the Resource Cap mechanism:

| Test Case | Method / Scenario | Expected Outcome |
|---|---|---|
| `test_resource_cap_initial_state_is_unlocked` | Instantiate `DevilsLockGovernor(lock_dir=tmp_path)` | `check_resource_cap() == True`, `get_active_subagent() is None` |
| `test_single_subagent_acquire_and_release` | Call `acquire_resource_lock('sub_1', task_name='Grid')` followed by `release_resource_lock('sub_1')` | Initial: `True`; After acquire: `check_resource_cap() == False`; After release: `check_resource_cap() == True` |
| `test_concurrent_subagent_collision_raises_error` | Subagent 1 acquires lock. Subagent 2 attempts `acquire_resource_lock('sub_2')` | Raises `ResourceCapExceededError`. `error.active_subagent['subagent_id'] == 'sub_1'` |
| `test_dead_pid_self_healing_recovery` | Manually write state file pointing to PID `999999` (non-existent). Call `check_resource_cap()` | Detects dead PID, removes stale state file, returns `True`. Subsequent `acquire_resource_lock` succeeds |
| `test_process_crash_kernel_flock_release` | Spawn a `multiprocessing.Process` or `subprocess` that acquires `DevilsLockGovernor` lock, then SIGKILLs itself | Parent process immediately checks `check_resource_cap() == True` and acquires lock without deadlock |
| `test_context_manager_lifecycle_safety` | Use `with governor.subagent_lock_context('sub_ctx'):` with normal block and with raised exception | Inside context: `check_resource_cap() == False`. Outside context (both normal and exception): `check_resource_cap() == True` |
| `test_multi_thread_high_concurrency_race` | Spawn 10 concurrent threads attempting `acquire_resource_lock()` on the same governor instance | Exactly 1 thread succeeds; exactly 9 threads catch `ResourceCapExceededError`. No crashes or corrupted files |
| `test_validate_preflight_locks_resource_cap_failure` | Lock active subagent, then call `validate_preflight_locks()` | Raises `ResourceCapExceededError` with `status != 'APPROVED'` and diagnostic metadata |

---
*Report certified by Explorer 1 (`teamwork_preview_explorer_m1_1`). Ready for handoff and synthesis.*
