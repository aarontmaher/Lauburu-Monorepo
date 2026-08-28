"""
4-Way Debate Governance — The Devil's Lock Governor
Authoritative implementation design for backend/devils_lock_governor.py
Version: 1.0.0-M1

Governs autonomous subagent spawning by enforcing:
1. Resource Cap: Maximum 1 active subagent simultaneously.
2. VRAM Headroom Check: check_vram_and_lock() strictly blocking execution when free VRAM < 15.0%.
3. Genetic ELO Mandate: Selects the model with highest domain ELO for UI/UX tasks from canonical_ai_leaderboard.json.
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

# Blackboard state store integration
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
    """
    Authoritative Gating Governor for Subagent Spawning.
    Implements 4-Way Debate Devil's Lock rules.
    """

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
        """Resolve path to canonical_ai_leaderboard.json across monorepo locations."""
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

    # =========================================================================
    # GATE 1: RESOURCE CAP (Max 1 Active Subagent)
    # =========================================================================

    def check_resource_cap(self) -> bool:
        """
        Check if spawning is permitted under the 1-subagent resource cap.
        Returns True if no subagent is currently active, False otherwise.
        Automatically heals stale locks from dead processes.
        """
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
                    # Check if PID is actively running
                    try:
                        os.kill(int(pid), 0)
                        # Process is alive -> Lock is valid and active
                        return False
                    except (ProcessLookupError, ValueError):
                        # Process is dead -> Stale lock, can heal
                        logger.warning(f"[DEVIL'S LOCK] Auto-healing stale subagent lock for dead PID {pid}")
                        try:
                            os.remove(self.lock_file_path)
                        except OSError:
                            pass
                        return True
                    except PermissionError:
                        # Process exists but owned by another user
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

    # =========================================================================
    # GATE 2: VRAM HEADROOM CHECK (check_vram_and_lock)
    # =========================================================================

    def check_vram_and_lock(
        self,
        override_free_pct: Optional[float] = None
    ) -> Tuple[bool, float, float]:
        """
        Check VRAM / Unified Memory headroom and block execution if < 15.0%.

        Parameters:
            override_free_pct (Optional[float]):
                If provided (e.g. 14.9, 15.0, 15.1 in unit tests), overrides
                the live OS query for deterministic test verification.

        Returns:
            Tuple[bool, float, float]:
                (is_allowed, free_vram_gb, free_pct)
                - is_allowed: True if free_pct >= 15.0, False if free_pct < 15.0
                - free_vram_gb: Absolute available VRAM / memory in Gigabytes
                - free_pct: Percentage of free headroom (0.0 - 100.0)

        Strict Gating Invariant:
            free_pct < 15.0  -> is_allowed = False (BLOCKED)
            free_pct >= 15.0 -> is_allowed = True  (ALLOWED)
        """
        # 1. Test Override Path (Unit Testing & Boundary Verification)
        if override_free_pct is not None:
            free_pct = float(override_free_pct)
            # Default reference total memory (host Mac Mini 24.0 GB or mesh 82.8 GB)
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
                logger.info(
                    f"[DEVIL'S LOCK] VRAM Headroom Check PASSED (override): "
                    f"{free_pct:.2f}% free ({free_vram_gb:.2f} GB) >= {self.min_vram_pct:.1f}%"
                )
            else:
                logger.warning(
                    f"[DEVIL'S LOCK ENGAGED] VRAM Headroom Check FAILED (override): "
                    f"{free_pct:.2f}% free ({free_vram_gb:.2f} GB) < {self.min_vram_pct:.1f}%. Spawning locked."
                )
            return (is_allowed, free_vram_gb, round(free_pct, 2))

        # 2. Live Hardware Telemetry Inspection (Rule #0 Zero-Mock Compliant)
        # Primary Source: psutil.virtual_memory() (Apple Silicon Host Unified Memory)
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                total_bytes = vm.total
                available_bytes = vm.available
                free_pct = round((available_bytes / total_bytes) * 100.0, 2)
                free_vram_gb = round(available_bytes / (1024**3), 2)
                is_allowed = bool(free_pct >= self.min_vram_pct)

                if is_allowed:
                    logger.info(
                        f"[DEVIL'S LOCK] VRAM Headroom Check PASSED (psutil): "
                        f"{free_pct:.2f}% free ({free_vram_gb:.2f} GB) >= {self.min_vram_pct:.1f}%"
                    )
                else:
                    logger.warning(
                        f"[DEVIL'S LOCK ENGAGED] VRAM Headroom Check FAILED (psutil): "
                        f"{free_pct:.2f}% free ({free_vram_gb:.2f} GB) < {self.min_vram_pct:.1f}%. Spawning locked."
                    )
                return (is_allowed, free_vram_gb, free_pct)
            except Exception as e:
                logger.error(f"[DEVIL'S LOCK] Error querying psutil.virtual_memory: {e}")

        # Secondary Source: blackboard_store.get_snapshot().layer_1_hardware
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
                    logger.info(
                        f"[DEVIL'S LOCK] VRAM Headroom Check PASSED (blackboard): "
                        f"{free_pct:.2f}% free ({free_vram_gb:.2f} GB) >= {self.min_vram_pct:.1f}%"
                    )
                else:
                    logger.warning(
                        f"[DEVIL'S LOCK ENGAGED] VRAM Headroom Check FAILED (blackboard): "
                        f"{free_pct:.2f}% free ({free_vram_gb:.2f} GB) < {self.min_vram_pct:.1f}%. Spawning locked."
                    )
                return (is_allowed, free_vram_gb, free_pct)
            except Exception as e:
                logger.error(f"[DEVIL'S LOCK] Error querying blackboard_store: {e}")

        # Fail-Closed: Rule #0 forbids hallucinated or fake fallback metrics
        raise VRAMTelemetryError(
            "Unable to extract authentic hardware VRAM telemetry from psutil or blackboard_store (Rule #0 Fail-Closed)."
        )

    def get_vram_telemetry(
        self,
        override_free_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """Return comprehensive VRAM telemetry snapshot."""
        is_allowed, free_gb, free_pct = self.check_vram_and_lock(override_free_pct=override_free_pct)
        return {
            "is_allowed": is_allowed,
            "free_vram_gb": free_gb,
            "free_pct": free_pct,
            "min_required_pct": self.min_vram_pct,
            "is_locked": not is_allowed,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # =========================================================================
    # GATE 3: GENETIC ELO MANDATE (select_highest_elo_model_for_ui)
    # =========================================================================

    def select_highest_elo_model_for_ui(
        self,
        leaderboard_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read canonical_ai_leaderboard.json and select the top model for UI tasks.
        Computes domain UI fitness from vision, 3D UI, and client architecture skills.
        """
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
        champion_score = score_ui_model(champion)

        return {
            "model_id": champion.get("id"),
            "display_name": champion.get("name", champion.get("id")),
            "base_elo": champion.get("elo"),
            "ui_domain_elo": round(champion_score, 1),
            "engine": champion.get("engine", "llama_rpc"),
            "specialist_skills": champion.get("specialist_skills", {}),
            "tier": champion.get("tier", "Production"),
        }

    # =========================================================================
    # PRE-FLIGHT VALIDATION (All 3 Gates)
    # =========================================================================

    def validate_preflight_locks(
        self,
        override_free_pct: Optional[float] = None,
        override_resource_cap: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Validate all 3 Devil's Lock gates in sequence before spawning a subagent.
        Raises specific DevilsLockError exceptions if any gate fails.
        """
        # Gate 1: Resource Cap
        resource_cap_ok = self.check_resource_cap() if override_resource_cap is None else bool(override_resource_cap)
        if not resource_cap_ok:
            raise ResourceCapExceededError(
                f"[DEVIL'S LOCK] Resource cap exceeded: 1 active subagent is already running."
            )

        # Gate 2: VRAM Headroom Check
        is_allowed, free_gb, free_pct = self.check_vram_and_lock(override_free_pct=override_free_pct)
        if not is_allowed:
            raise VRAMLockBlockedError(
                f"[DEVIL'S LOCK ENGAGED] Free VRAM headroom {free_pct:.2f}% is below mandatory {self.min_vram_pct:.1f}% threshold (Free: {free_gb:.2f} GB)."
            )

        # Gate 3: Genetic ELO Selection
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
