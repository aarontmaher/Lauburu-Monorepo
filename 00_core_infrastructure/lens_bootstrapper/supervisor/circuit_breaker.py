"""
00_core_infrastructure/lens_bootstrapper/supervisor/circuit_breaker.py
======================================================================
Local Leaky-Bucket Circuit Breaker (Feature F10).

Rate-limits daemon and network recovery actions (max 3 restarts per 5 minutes
per service) to prevent crash loops and port flapping across the mesh.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional


class CircuitBreaker:
    """
    Sliding-window / leaky-bucket circuit breaker for service recovery actions.

    Default policy:
    - Max 3 restarts within a 300-second (5-minute) rolling window.
    - If exceeded, service is placed in a TRIPPED cooldown state for 300 seconds.
    - Tracks each service independently so one flapping service does not
      cascade into throttling other healthy services.
    """

    def __init__(
        self,
        max_restarts: int = 3,
        window_seconds: float = 300.0,
        cooldown_seconds: float = 300.0,
    ) -> None:
        self.max_restarts = max(1, max_restarts)
        self.window_seconds = max(1.0, float(window_seconds))
        self.cooldown_seconds = max(1.0, float(cooldown_seconds))

        self._lock = threading.Lock()
        # service_name -> list of restart timestamps (float)
        self._history: Dict[str, List[float]] = {}
        # service_name -> cooldown expiration timestamp (float)
        self._cooldown_until: Dict[str, float] = {}

    def _prune(self, service_name: str, now: float) -> List[float]:
        """Prunes timestamps older than window_seconds from history."""
        cutoff = now - self.window_seconds
        records = self._history.get(service_name, [])
        valid_records = [t for t in records if t >= cutoff]
        self._history[service_name] = valid_records
        return valid_records

    def can_restart(self, service_name: str, now: Optional[float] = None) -> bool:
        """
        Determines whether a restart attempt is permitted for service_name.

        Returns True if the service has fewer than max_restarts within the
        current window and is not currently in a cooldown state.
        """
        if not service_name:
            return False

        current_time = time.time() if now is None else float(now)

        with self._lock:
            # Check cooldown
            cooldown_exp = self._cooldown_until.get(service_name, 0.0)
            if current_time < cooldown_exp:
                return False

            records = self._prune(service_name, current_time)
            if len(records) >= self.max_restarts:
                # Trip breaker and trigger cooldown
                self._cooldown_until[service_name] = current_time + self.cooldown_seconds
                return False

            return True

    def record_restart(self, service_name: str, now: Optional[float] = None) -> bool:
        """
        Attempts to record a restart action.

        If permitted, logs the timestamp and returns True.
        If blocked by the circuit breaker, returns False without recording.
        """
        if not service_name:
            return False

        current_time = time.time() if now is None else float(now)

        with self._lock:
            # Check cooldown
            cooldown_exp = self._cooldown_until.get(service_name, 0.0)
            if current_time < cooldown_exp:
                return False

            records = self._prune(service_name, current_time)
            if len(records) >= self.max_restarts:
                self._cooldown_until[service_name] = current_time + self.cooldown_seconds
                return False

            # Allowed: record timestamp
            records.append(current_time)
            self._history[service_name] = records
            return True

    def get_service_status(
        self, service_name: str, now: Optional[float] = None
    ) -> Dict[str, Any]:
        """Returns the current circuit breaker status for service_name."""
        current_time = time.time() if now is None else float(now)

        with self._lock:
            cooldown_exp = self._cooldown_until.get(service_name, 0.0)
            is_in_cooldown = current_time < cooldown_exp
            cooldown_remaining = max(0.0, cooldown_exp - current_time) if is_in_cooldown else 0.0

            records = self._prune(service_name, current_time)
            count = len(records)
            is_tripped = is_in_cooldown or (count >= self.max_restarts)
            remaining_allowance = max(0, self.max_restarts - count) if not is_in_cooldown else 0
            last_restart = records[-1] if records else None

            return {
                "service": service_name,
                "is_tripped": is_tripped,
                "in_cooldown": is_in_cooldown,
                "restart_count_in_window": count,
                "max_restarts": self.max_restarts,
                "window_seconds": self.window_seconds,
                "remaining_allowance": remaining_allowance,
                "cooldown_remaining_sec": round(cooldown_remaining, 2),
                "last_restart_timestamp": last_restart,
            }

    def reset(self, service_name: Optional[str] = None) -> None:
        """Resets the circuit breaker for a specific service or all services."""
        with self._lock:
            if service_name:
                self._history.pop(service_name, None)
                self._cooldown_until.pop(service_name, None)
            else:
                self._history.clear()
                self._cooldown_until.clear()

    def get_all_statuses(self, now: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Returns the status of all currently tracked services."""
        current_time = time.time() if now is None else float(now)
        with self._lock:
            services = set(self._history.keys()) | set(self._cooldown_until.keys())

        return {svc: self.get_service_status(svc, current_time) for svc in sorted(services)}
