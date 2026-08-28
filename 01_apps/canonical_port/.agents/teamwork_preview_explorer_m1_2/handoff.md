# Handoff Report — Explorer 2: 4-Way Debate Governance (check_vram_and_lock)

**Date**: 2026-08-29T03:25:00+10:00 (UTC: 2026-08-28T17:25:00Z)  
**Agent**: `teamwork_preview_explorer_m1_2` (Explorer 2 — Milestone 1)  
**Working Directory**: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_2`  
**Target File under Investigation**: `01_apps/canonical_port/backend/devils_lock_governor.py`  
**Status**: Investigation & Design Complete  

---

## 1. Observation

### 1.1 Authoritative Governance Invariants & Interface Contracts
- **`ORIGINAL_REQUEST.md:25-30`**:
  ```markdown
  ### R2. 4-Way Debate Governance (The Devil's Lock)
  The orchestrator must strictly enforce the following gating mechanisms before spawning an agent:
  1. **Resource Cap:** Only 1 active subagent is allowed at a time.
  2. **VRAM Check:** Do not spawn if global VRAM headroom is under 15% (e.g. `check_vram_and_lock()` explicitly blocks execution if free VRAM < 15%).
  3. **Genetic ELO Mandate:** It must read the `canonical_ai_leaderboard.json` and select the model with the highest domain ELO for UI tasks.
  ```
- **`ORIGINAL_REQUEST.md:36`**:
  ```markdown
  - [ ] The VRAM lock logic is programmatically verifiable (e.g. `check_vram_and_lock()` explicitly blocks execution if free VRAM < 15%).
  ```
- **`PROJECT.md:35-40`**:
  ```markdown
  ### `backend.devils_lock_governor.DevilsLockGovernor` ↔ `backend.tui_specialist_daemon.TuiSpecialistDaemon`
  - `check_resource_cap() -> bool`: Returns `True` if no active subagent is running, `False` otherwise.
  - `check_vram_and_lock(override_free_pct: Optional[float] = None) -> Tuple[bool, float, float]`: Returns `(is_allowed, free_vram_gb, free_pct)`. Blocks (`is_allowed = False`) when `free_pct < 15.0`.
  - `select_highest_elo_model_for_ui(leaderboard_path: Optional[str] = None) -> Dict[str, Any]`: Returns dict of top model selected from `canonical_ai_leaderboard.json`.
  - `validate_preflight_locks() -> Dict[str, Any]`: Runs all 3 gates in sequence, raising `DevilsLockError` if any check fails.
  ```

### 1.2 Hardware Telemetry & Memory Inspection Mechanics
1. **Live Host Hardware Query (`psutil.virtual_memory()`)**:
   - Command: `python3 -c "import psutil; vm = psutil.virtual_memory(); print(f'Total: {vm.total/(1024**3):.2f} GB, Available: {vm.available/(1024**3):.2f} GB, Used: {vm.used/(1024**3):.2f} GB, Free Pct: {(vm.available/vm.total)*100:.2f}%')"`
   - Output: `Total: 24.00 GB, Available: 4.27 GB, Used: 7.19 GB, Free Pct: 17.80%`
   - Observation: On the Apple M4 Pro Mac Mini Host, RAM and VRAM share unified LPDDR5X memory. `psutil.virtual_memory()` directly queries Darwin kernel registers (`mach_vm` / `vm_stat`), providing 100% authentic, fluctuating physical metrics without mock/simulated data.
2. **Mesh Telemetry Query (`blackboard_store.get_snapshot().layer_1_hardware`)**:
   - Command: `python3 -c "import sys; sys.path.insert(0, '.'); from tui.services.blackboard_store import blackboard_store; s = blackboard_store.get_snapshot(); print('Layer 1 HW:', s.layer_1_hardware.total_vram_gb, s.layer_1_hardware.pooled_vram_used_gb)"`
   - Output: `Layer 1 HW: 82.8 39.0`
   - Observation: In `tui/models/blackboard_models.py:367-377`, `Layer1HardwareState` defines `total_vram_gb = 82.8` and `pooled_vram_used_gb = 39.0`, giving $82.8 - 39.0 = 43.8$ GB free ($52.90\%$ free headroom across the 7-node pool).
3. **Canonical AI Leaderboard (`canonical_ai_leaderboard.json`)**:
   - File Path: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json`
   - Top UI domain candidate: `kimi_tandem_titan` (Base ELO: 3089.0, UI Domain ELO: 3070.5).

### 1.3 Proposed Implementation & Unit Test Execution
- Created proposed module: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_2/proposed_devils_lock_governor.py`
- Created unit test suite: `/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port/.agents/teamwork_preview_explorer_m1_2/test_proposed_vram_lock.py`
- Command: `uv run pytest .agents/teamwork_preview_explorer_m1_2/test_proposed_vram_lock.py -v`
- Result: `11 passed in 0.08s` (100% pass rate).

---

## 2. Logic Chain

1. **Premise 1 (Gating Mandate)**: The Devil's Lock requires that subagent execution is unconditionally halted when free VRAM headroom falls below 15.0%.
2. **Premise 2 (Zero-Mock Rule #0)**: Under Rule #0, production code must never generate fake numbers or mock arrays. Telemetry must originate from verified OS kernel APIs (`psutil.virtual_memory()`) or authentic state snapshots (`blackboard_store.get_snapshot().layer_1_hardware`).
3. **Premise 3 (Programmatic Verification via Parameter Overrides)**: To permit deterministic unit testing of the strict boundary conditions (14.9%, 15.0%, 15.1%) without injecting synthetic fake data into global runtime state or mutating OS memory, `check_vram_and_lock()` must accept an optional `override_free_pct: Optional[float] = None` argument.
4. **Premise 4 (Boundary Condition Rigor)**:
   - When $\text{free\_pct} < 15.0\%$ (e.g. 14.9%, 14.99%, 0.0%): `is_allowed` MUST be `False`.
   - When $\text{free\_pct} \ge 15.0\%$ (e.g. 15.0%, 15.01%, 15.1%, 100.0%): `is_allowed` MUST be `True`.
5. **Premise 5 (Multi-Tier Telemetry Resolution Hierarchy)**:
   - **Step 1 (Test Override)**: If `override_free_pct is not None`, compute `(free_pct >= min_vram_pct, ref_total_gb * (free_pct / 100.0), free_pct)`.
   - **Step 2 (Primary Live Hardware)**: Query `psutil.virtual_memory()`. Compute `free_pct = (vm.available / vm.total) * 100.0`, `free_vram_gb = vm.available / (1024**3)`.
   - **Step 3 (Secondary Blackboard Telemetry)**: If psutil is unimported/unavailable, query `blackboard_store.get_snapshot().layer_1_hardware`. Compute `free_vram_gb = max(0.0, l1.total_vram_gb - l1.pooled_vram_used_gb)` and `free_pct = (free_vram_gb / l1.total_vram_gb) * 100.0`.
   - **Step 4 (Fail-Closed Gate)**: If all authentic probes fail, DO NOT hallucinate a default percentage; raise `VRAMTelemetryError` to guarantee safety.
6. **Premise 6 (Exception Hierarchy & Composite Validation)**: `validate_preflight_locks()` evaluates Gate 1 (`check_resource_cap()`), Gate 2 (`check_vram_and_lock()`), and Gate 3 (`select_highest_elo_model_for_ui()`) sequentially, raising `ResourceCapExceededError` or `VRAMLockBlockedError` on any gate violation.
7. **Deduction**: The proposed architecture strictly fulfills R2 and the interface contracts in `PROJECT.md`, passes all boundary and live hardware tests, and provides an actionable blueprint for the implementer worker.

---

## 3. Caveats

1. **Unified Memory vs Dedicated VRAM**: On Apple Silicon Darwin hosts, CPU RAM and GPU VRAM are physically unified. `psutil.virtual_memory().available` measures the true instantaneous memory headroom available for both model weights and subagent execution. On discrete GPU nodes (e.g., Linux Head Node with dedicated VRAM), the secondary `blackboard_store` layer captures pooled VRAM.
2. **Read-Only Scope**: In compliance with the Teamwork Explorer protocol, no production source code files outside of `.agents/` were directly modified. The reference implementation is stored in `.agents/teamwork_preview_explorer_m1_2/proposed_devils_lock_governor.py`.

---

## 4. Conclusion & Implementation Recommendation

The design and verification of `check_vram_and_lock()` for `backend/devils_lock_governor.py` is complete and verified.

### 4.1 Target Code Specification for `backend/devils_lock_governor.py`

```python
"""
4-Way Debate Governance — The Devil's Lock Governor
backend/devils_lock_governor.py
Version: 1.0.0-CANONICAL
"""

import os
import sys
import json
import time
import fcntl
import datetime
import logging
from typing import Dict, Any, Optional, Tuple, List, Union

try:
    import psutil
except ImportError:
    psutil = None

try:
    from tui.services.blackboard_store import blackboard_store, BlackboardStore
except ImportError:
    try:
        from services.blackboard_store import blackboard_store, BlackboardStore
    except ImportError:
        blackboard_store = None

logger = logging.getLogger("DevilsLockGovernor")


class DevilsLockError(Exception):
    """Base exception for all Devil's Lock governance violations."""
    pass


class ResourceCapExceededError(DevilsLockError):
    """Raised when an active subagent is already executing (concurrency cap = 1)."""
    pass


class VRAMLockBlockedError(DevilsLockError):
    """Raised when available VRAM headroom is below the mandatory 15.0% threshold."""
    pass


class VRAMTelemetryError(DevilsLockError):
    """Raised when hardware memory telemetry cannot be verified under Rule #0."""
    pass


class GeneticLeaderboardError(DevilsLockError):
    """Raised when canonical_ai_leaderboard.json is missing or corrupted."""
    pass


class DevilsLockGovernor:
    """Authoritative Gating Governor enforcing 4-Way Debate Devil's Lock rules."""

    DEFAULT_MIN_VRAM_PCT: float = 15.0
    DEFAULT_LOCK_FILE: str = "/tmp/tui_specialist_subagent.lock"
    DEFAULT_LEADERBOARD_PATH: str = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json"

    def __init__(
        self,
        leaderboard_path: Optional[str] = None,
        lock_file_path: Optional[str] = None,
        min_vram_pct: float = DEFAULT_MIN_VRAM_PCT,
    ):
        self.leaderboard_path = leaderboard_path or self._resolve_leaderboard_path()
        self.lock_file_path = lock_file_path or self.DEFAULT_LOCK_FILE
        self.min_vram_pct = float(min_vram_pct)
        self._active_lock_fd: Optional[int] = None
        self._active_task_id: Optional[str] = None

    def _resolve_leaderboard_path(self) -> str:
        candidates = [
            self.DEFAULT_LEADERBOARD_PATH,
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "04_data_and_memory", "data", "canonical_ai_leaderboard.json")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "canonical_ai_leaderboard.json")),
            "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/canonical_ai_leaderboard.json",
        ]
        for p in candidates:
            if os.path.isfile(p):
                return p
        return self.DEFAULT_LEADERBOARD_PATH

    def check_resource_cap(self) -> bool:
        """Returns True if no active subagent is running, False otherwise."""
        if not os.path.exists(self.lock_file_path):
            return True
        try:
            with open(self.lock_file_path, "r") as f:
                content = f.read().strip()
                if not content:
                    return True
                lock_data = json.loads(content)
                pid = lock_data.get("pid")
                if pid:
                    try:
                        os.kill(int(pid), 0)
                        return False  # Active process holding lock
                    except (ProcessLookupError, ValueError):
                        logger.warning(f"[DEVIL'S LOCK] Auto-healing stale lock for dead PID {pid}")
                        try:
                            os.remove(self.lock_file_path)
                        except OSError:
                            pass
                        return True
                    except PermissionError:
                        return False
            return False
        except (json.JSONDecodeError, OSError):
            return True

    def acquire_subagent_lock(self, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Acquire exclusive POSIX file lock for subagent execution."""
        if not self.check_resource_cap():
            return False
        payload = {
            "task_id": task_id,
            "pid": os.getpid(),
            "timestamp": time.time(),
            "utc_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        try:
            fd = os.open(self.lock_file_path, os.O_CREAT | os.O_RDWR | os.O_TRUNC)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(fd, json.dumps(payload, indent=2).encode("utf-8"))
            self._active_lock_fd = fd
            self._active_task_id = task_id
            return True
        except (OSError, BlockingIOError):
            return False

    def release_subagent_lock(self) -> bool:
        """Release subagent execution lock."""
        try:
            if self._active_lock_fd is not None:
                try:
                    fcntl.flock(self._active_lock_fd, fcntl.LOCK_UN)
                    os.close(self._active_lock_fd)
                except OSError:
                    pass
                self._active_lock_fd = None
            if os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)
            self._active_task_id = None
            return True
        except OSError:
            return False

    def check_vram_and_lock(
        self,
        override_free_pct: Optional[float] = None
    ) -> Tuple[bool, float, float]:
        """
        Check VRAM / Unified Memory headroom and block execution if < 15.0%.
        Returns (is_allowed, free_vram_gb, free_pct).
        """
        # 1. Test Override Path
        if override_free_pct is not None:
            free_pct = float(override_free_pct)
            ref_total_gb = 24.0
            if psutil is not None:
                try:
                    ref_total_gb = round(psutil.virtual_memory().total / (1024**3), 2)
                except Exception:
                    ref_total_gb = 24.0
            elif blackboard_store is not None:
                try:
                    ref_total_gb = blackboard_store.get_snapshot().layer_1_hardware.total_vram_gb
                except Exception:
                    ref_total_gb = 24.0

            free_vram_gb = round(ref_total_gb * (max(0.0, free_pct) / 100.0), 2)
            is_allowed = bool(free_pct >= self.min_vram_pct)

            if is_allowed:
                logger.info(f"[DEVIL'S LOCK] VRAM Headroom Check PASSED (override): {free_pct:.2f}% >= {self.min_vram_pct:.1f}%")
            else:
                logger.warning(f"[DEVIL'S LOCK ENGAGED] VRAM Headroom Check FAILED (override): {free_pct:.2f}% < {self.min_vram_pct:.1f}%. Locked.")
            return (is_allowed, free_vram_gb, round(free_pct, 2))

        # 2. Live Hardware Inspection (Rule #0 Zero-Mock)
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                total_bytes = vm.total
                available_bytes = vm.available
                free_pct = round((available_bytes / total_bytes) * 100.0, 2)
                free_vram_gb = round(available_bytes / (1024**3), 2)
                is_allowed = bool(free_pct >= self.min_vram_pct)

                if is_allowed:
                    logger.info(f"[DEVIL'S LOCK] VRAM Headroom Check PASSED (psutil): {free_pct:.2f}% >= {self.min_vram_pct:.1f}%")
                else:
                    logger.warning(f"[DEVIL'S LOCK ENGAGED] VRAM Headroom Check FAILED (psutil): {free_pct:.2f}% < {self.min_vram_pct:.1f}%. Locked.")
                return (is_allowed, free_vram_gb, free_pct)
            except Exception as e:
                logger.error(f"[DEVIL'S LOCK] Error querying psutil: {e}")

        # Secondary: blackboard_store Layer 1 Hardware
        if blackboard_store is not None:
            try:
                snapshot = blackboard_store.get_snapshot()
                l1 = snapshot.layer_1_hardware
                total_vram = l1.total_vram_gb
                used_vram = l1.pooled_vram_used_gb
                free_vram_gb = round(max(0.0, total_vram - used_vram), 2)
                free_pct = round((free_vram_gb / total_vram) * 100.0, 2) if total_vram > 0 else 0.0
                is_allowed = bool(free_pct >= self.min_vram_pct)

                if is_allowed:
                    logger.info(f"[DEVIL'S LOCK] VRAM Headroom Check PASSED (blackboard): {free_pct:.2f}% >= {self.min_vram_pct:.1f}%")
                else:
                    logger.warning(f"[DEVIL'S LOCK ENGAGED] VRAM Headroom Check FAILED (blackboard): {free_pct:.2f}% < {self.min_vram_pct:.1f}%. Locked.")
                return (is_allowed, free_vram_gb, free_pct)
            except Exception as e:
                logger.error(f"[DEVIL'S LOCK] Error querying blackboard_store: {e}")

        raise VRAMTelemetryError("Unable to extract authentic hardware VRAM telemetry (Rule #0 Fail-Closed).")

    def get_vram_telemetry(self, override_free_pct: Optional[float] = None) -> Dict[str, Any]:
        """Return structured dictionary of current VRAM telemetry."""
        is_allowed, free_gb, free_pct = self.check_vram_and_lock(override_free_pct=override_free_pct)
        return {
            "is_allowed": is_allowed,
            "free_vram_gb": free_gb,
            "free_pct": free_pct,
            "min_required_pct": self.min_vram_pct,
            "is_locked": not is_allowed,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    def select_highest_elo_model_for_ui(self, leaderboard_path: Optional[str] = None) -> Dict[str, Any]:
        """Selects the champion model for UI tasks based on domain ELO."""
        path = leaderboard_path or self.leaderboard_path
        if not os.path.isfile(path):
            raise GeneticLeaderboardError(f"Leaderboard file not found at {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise GeneticLeaderboardError(f"Failed to read leaderboard JSON: {e}")

        models = data.get("leaderboard", [])
        if not models:
            raise GeneticLeaderboardError("Leaderboard contains no models.")

        def score_ui_model(m: Dict[str, Any]) -> float:
            base_elo = float(m.get("elo", 1500.0))
            skills = m.get("specialist_skills", {})
            vlm = float(skills.get("vision_vlm_truth_auditing", 50.0))
            game_ui = float(skills.get("3d_ai_training_game", 50.0))
            mobile_ui = float(skills.get("flutter_dart_mobile_architecture", 50.0))
            openclaw = float(skills.get("openclaw_utilisation", 50.0))
            ui_fitness = (0.35 * vlm) + (0.30 * game_ui) + (0.20 * mobile_ui) + (0.15 * openclaw)
            return base_elo * (ui_fitness / 100.0)

        sorted_models = sorted(models, key=score_ui_model, reverse=True)
        champion = sorted_models[0]
        return {
            "model_id": champion.get("id"),
            "display_name": champion.get("name", champion.get("id")),
            "base_elo": champion.get("elo"),
            "ui_domain_elo": round(score_ui_model(champion), 1),
            "engine": champion.get("engine", "llama_rpc"),
            "specialist_skills": champion.get("specialist_skills", {}),
            "tier": champion.get("tier", "Production"),
        }

    def validate_preflight_locks(
        self,
        override_free_pct: Optional[float] = None,
        override_resource_cap: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Validate all 3 gates in sequence, raising DevilsLockError if any check fails."""
        resource_cap_ok = self.check_resource_cap() if override_resource_cap is None else bool(override_resource_cap)
        if not resource_cap_ok:
            raise ResourceCapExceededError("[DEVIL'S LOCK] Resource cap exceeded: 1 active subagent is already running.")

        is_allowed, free_gb, free_pct = self.check_vram_and_lock(override_free_pct=override_free_pct)
        if not is_allowed:
            raise VRAMLockBlockedError(
                f"[DEVIL'S LOCK ENGAGED] Free VRAM headroom {free_pct:.2f}% is below mandatory {self.min_vram_pct:.1f}% threshold (Free: {free_gb:.2f} GB)."
            )

        top_model = self.select_highest_elo_model_for_ui()
        return {
            "status": "APPROVED",
            "resource_cap_ok": True,
            "vram_lock_ok": True,
            "free_vram_gb": free_gb,
            "free_vram_pct": free_pct,
            "selected_model": top_model,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
```

---

## 5. Verification Method

### 5.1 Unit Test Execution Command
Execute the comprehensive unit test suite:
```bash
uv run pytest .agents/teamwork_preview_explorer_m1_2/test_proposed_vram_lock.py -v
```

**Expected Result**: All 11 tests collect and pass in < 0.2s with exit code 0:
- `test_vram_boundary_under_threshold` (14.9% -> `is_allowed=False`)
- `test_vram_boundary_exact_threshold` (15.0% -> `is_allowed=True`)
- `test_vram_boundary_above_threshold` (15.1% -> `is_allowed=True`)
- `test_vram_sub_decimal_precision` (14.99% vs 15.01%)
- `test_vram_extreme_boundaries` (0.0%, 100.0%, -5.0%)
- `test_vram_live_hardware_inspection` (Genuine `psutil` kernel metrics, `0.0 <= free_pct <= 100.0`)
- `test_get_vram_telemetry_schema` (Dictionary structure validation)
- `test_validate_preflight_locks_blocked_on_vram` (`VRAMLockBlockedError` raised on 14.9%)
- `test_validate_preflight_locks_approved` (`status: "APPROVED"` on 25.0%)
- `test_resource_cap_lifecycle` (Exclusive lock acquisition and release)
- `test_genetic_elo_model_selection` (Ranking by domain UI ELO)

### 5.2 Live Shell Verification Command
Verify live host memory telemetry extraction:
```bash
uv run python -c "from proposed_devils_lock_governor import DevilsLockGovernor; g = DevilsLockGovernor(); print('Live VRAM Check:', g.check_vram_and_lock())"
```

### 5.3 Invalidation Conditions
- If `check_vram_and_lock(override_free_pct=14.9)` returns `is_allowed=True`, the gating boundary is INVALID.
- If `check_vram_and_lock(override_free_pct=15.0)` returns `is_allowed=False`, the gating boundary is INVALID.
- If `check_vram_and_lock()` generates random/simulated numbers when `override_free_pct is None`, it violates Rule #0.
