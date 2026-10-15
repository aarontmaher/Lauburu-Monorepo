"""
Asynchronous Non-Blocking Mesh Outage Detector
Part of Canonical Mesh Fallback Terminal (bluetooth_terminal_ide).

Monitors overlay networks (Tailscale 100.x.x.x and Nebula 10.255.x.x) concurrently.
Applies a 3-cycle sliding window debounce filter to eliminate roaming jitter flapping,
and triggers Stage 2 Bluetooth PAN escalation when 3 consecutive cycles fail.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("mesh_healer.outage_detector")

DEFAULT_MESH_TARGETS: Dict[str, Dict[str, str]] = {
    "L1_Mac_Host": {"tailscale": "100.119.199.76", "nebula": "10.255.0.1"},
    "L2_MacBook_Pro": {"tailscale": "100.103.212.21", "nebula": "10.255.0.2"},
    "L3_Linux_Hub": {"tailscale": "100.101.39.98", "nebula": "10.255.0.3"},
    "L6_Pixel_10_Edge": {"tailscale": "100.73.38.87", "nebula": "10.255.0.6"},
    "L7_Samsung_S20": {"tailscale": "100.84.40.95", "nebula": "10.255.0.7"},
}


class MeshOutageDetector:
    """
    Non-blocking concurrent prober for overlay mesh network health.
    Uses asyncio.open_connection and async ping across Tailscale & Nebula endpoints.
    """

    def __init__(
        self,
        targets: Optional[Dict[str, Dict[str, str]]] = None,
        failure_threshold: int = 3,
        probe_timeout: float = 1.0,
        probe_interval: float = 3.0,
        on_outage_detected: Optional[Callable[[], Any]] = None,
        on_outage_recovered: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.targets = targets if targets is not None else DEFAULT_MESH_TARGETS
        self.failure_threshold = max(1, failure_threshold)
        self.probe_timeout = probe_timeout
        self.probe_interval = probe_interval
        self.on_outage_detected = on_outage_detected
        self.on_outage_recovered = on_outage_recovered

        self.consecutive_failures: int = 0
        self.is_outage_detected: bool = False
        self.is_running: bool = False
        self._monitor_task: Optional[asyncio.Task] = None
        self.last_results: Dict[str, bool] = {}
        self._last_ping_proc: Optional[Any] = None

    async def probe_endpoint(
        self,
        ip: str,
        port: int = 8022,
        timeout: Optional[float] = None,
        check_ping: bool = True,
        ping_cmd: Optional[List[str]] = None,
    ) -> bool:
        """
        Asynchronously probes a single IP endpoint.
        1. Fast-path: non-blocking TCP socket connect check.
        2. Fallback: non-blocking async ICMP ping subprocess (if check_ping=True).
        """
        t = timeout or self.probe_timeout

        # 1. Fast path: TCP connect probe
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=t
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            pass

        if not check_ping:
            return False

        # 2. Secondary path: Async ICMP ping
        proc = None
        try:
            if ping_cmd:
                cmd = ping_cmd
            elif sys.platform == "darwin":
                # macOS ping: -W specifies milliseconds
                cmd = ["ping", "-c", "1", "-W", str(int(t * 1000)), ip]
            else:
                # Linux ping: -W specifies seconds
                cmd = ["ping", "-c", "1", "-W", str(max(1, int(t))), ip]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._last_ping_proc = proc
            await asyncio.wait_for(proc.wait(), timeout=t + 0.3)
            return proc.returncode == 0
        except (asyncio.TimeoutError, TimeoutError):
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                except (ProcessLookupError, OSError):
                    pass
                try:
                    await proc.wait()
                except Exception:
                    pass
            return False
        except Exception:
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                except (ProcessLookupError, OSError):
                    pass
                try:
                    await proc.wait()
                except Exception:
                    pass
            return False

    async def probe_cycle(self) -> bool:
        """
        Executes a single concurrent probe cycle across all target overlay endpoints.
        Returns True if at least one overlay endpoint is healthy, False if all fail.
        Applies a sliding-window debounce filter before updating outage state.
        """
        tasks: List[Tuple[str, asyncio.Task]] = []

        for node_name, ips in self.targets.items():
            if "tailscale" in ips and ips["tailscale"]:
                ip = ips["tailscale"]
                tasks.append((f"{node_name}_ts", asyncio.create_task(self.probe_endpoint(ip))))
            if "nebula" in ips and ips["nebula"]:
                ip = ips["nebula"]
                tasks.append((f"{node_name}_neb", asyncio.create_task(self.probe_endpoint(ip))))

        if not tasks:
            # No targets configured
            return True

        probe_coros = [task for _, task in tasks]
        results = await asyncio.gather(*probe_coros, return_exceptions=True)

        cycle_results: Dict[str, bool] = {}
        for (label, _), res in zip(tasks, results):
            is_alive = res is True
            cycle_results[label] = is_alive

        self.last_results = cycle_results
        any_alive = any(cycle_results.values())

        if any_alive:
            was_outage = self.is_outage_detected
            self.consecutive_failures = 0
            self.is_outage_detected = False
            if was_outage and self.on_outage_recovered:
                try:
                    res = self.on_outage_recovered()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    logger.error(f"Error in on_outage_recovered callback: {e}")
        else:
            self.consecutive_failures += 1
            logger.warning(
                f"Outage detector cycle failed ({self.consecutive_failures}/{self.failure_threshold})"
            )
            if self.consecutive_failures >= self.failure_threshold:
                if not self.is_outage_detected:
                    self.is_outage_detected = True
                    logger.error(
                        f"Mesh Outage Confirmed after {self.consecutive_failures} consecutive failed cycles!"
                    )
                    if self.on_outage_detected:
                        try:
                            res = self.on_outage_detected()
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception as e:
                            logger.error(f"Error in on_outage_detected callback: {e}")

        return any_alive

    async def run_loop(self) -> None:
        """Continuous background monitoring loop."""
        self.is_running = True
        try:
            while self.is_running:
                await self.probe_cycle()
                # Non-blocking sleep between cycles
                try:
                    await asyncio.sleep(self.probe_interval)
                except asyncio.CancelledError:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self.is_running = False

    def start(self) -> asyncio.Task:
        """Starts the outage monitor task in the current event loop."""
        if not self.is_running:
            self.is_running = True
            self._monitor_task = asyncio.create_task(self.run_loop())
        return self._monitor_task

    def stop(self) -> None:
        """Stops the outage monitor task cleanly."""
        self.is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            self._monitor_task = None
