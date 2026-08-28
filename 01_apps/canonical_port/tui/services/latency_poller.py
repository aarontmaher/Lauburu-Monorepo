"""
Dynamic Latency Poller (TTFT)
Version: 1.0.0-CANONICAL

Asynchronous, non-blocking background poller that periodically pings the 4 inference bridges:
- llama_rpc (GGML-RPC / HTTP SSE)
- exo (Zenoh Ring P2P)
- accelerate (MPS Metal / Multi-GPU DDP)
- petals (BitTorrent DHT Swarm)

Calculates Time-To-First-Token (TTFT) and availability status with:
- Single-token fast probe and instant stream cancellation
- Concurrent execution via asyncio.gather(return_exceptions=True)
- Safe lifecycle management (start/stop)
- Exception safety (never crashes the event loop)
"""

import time
import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable

try:
    from services.inference_bridges.base_bridge import BaseInferenceBridge
except ImportError:
    from tui.services.inference_bridges.base_bridge import BaseInferenceBridge

logger = logging.getLogger("DynamicLatencyPoller")


CLOUD_ENGINES = {"gemini", "cloudflare", "julien"}


@dataclass
class EngineLatencyMetric:
    """Telemetry data point for engine latency and availability."""
    engine_name: str
    is_available: bool = True
    ttft_ms: float = 0.0
    last_polled: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine_name,
            "engine_name": self.engine_name,
            "is_available": self.is_available,
            "ttft_ms": self.ttft_ms,
            "latency_ms": self.ttft_ms,
            "last_polled": self.last_polled,
            "error": self.error,
        }


class DynamicLatencyPoller:
    """
    Non-blocking background worker that continuously benchmarks TTFT
    across all inference engines and ranks them for dynamic routing.
    """

    def __init__(
        self,
        bridges: Optional[Dict[str, BaseInferenceBridge]] = None,
        poll_interval: float = 3.0,
        poll_interval_sec: Optional[float] = None,
        probe_timeout: float = 1.5,
        probe_timeout_sec: Optional[float] = None,
        cloud_poll_interval_sec: float = 60.0,
        on_metric_update: Optional[Callable[[Dict[str, EngineLatencyMetric]], None]] = None,
    ):
        self.bridges: Dict[str, BaseInferenceBridge] = dict(bridges or {})
        self.poll_interval_sec: float = poll_interval_sec if poll_interval_sec is not None else poll_interval
        self.probe_timeout_sec: float = probe_timeout_sec if probe_timeout_sec is not None else probe_timeout
        self.cloud_poll_interval_sec: float = cloud_poll_interval_sec
        self.last_cloud_polled: Dict[str, float] = {}
        self._on_metric_update = on_metric_update

        self._metrics: Dict[str, EngineLatencyMetric] = {}
        self._running: bool = False
        self._poll_task: Optional[asyncio.Task] = None

        # Initialize default metrics for all known bridges
        now = time.time()
        for name, bridge in self.bridges.items():
            is_conn = bridge.is_connected() if hasattr(bridge, "is_connected") else True
            self._metrics[name] = EngineLatencyMetric(
                engine_name=name,
                is_available=is_conn,
                ttft_ms=50.0 if is_conn else float("inf"),
                last_polled=now,
                error=None if is_conn else "Bridge not configured or disconnected"
            )

    @property
    def metrics(self) -> Dict[str, EngineLatencyMetric]:
        return self._metrics

    @property
    def is_running(self) -> bool:
        return self._running

    def set_bridges(self, bridges: Dict[str, BaseInferenceBridge]) -> None:
        """Update or register inference bridge instances."""
        self.bridges = dict(bridges)
        now = time.time()
        for name, bridge in self.bridges.items():
            if name not in self._metrics:
                is_conn = bridge.is_connected() if hasattr(bridge, "is_connected") else True
                self._metrics[name] = EngineLatencyMetric(
                    engine_name=name,
                    is_available=is_conn,
                    ttft_ms=50.0 if is_conn else float("inf"),
                    last_polled=now,
                    error=None if is_conn else "Bridge not configured or disconnected"
                )

    async def measure_engine_ttft(
        self,
        engine_name: str,
        bridge: BaseInferenceBridge,
        test_prompt: str = "ping",
        timeout: Optional[float] = None,
    ) -> EngineLatencyMetric:
        """
        Probe a single engine with a single-token prompt to compute exact TTFT.
        Releases probe generator upon receiving token 1 without mutating shared bridge cancellation flags.
        """
        effective_timeout = timeout if timeout is not None else self.probe_timeout_sec
        t0 = time.perf_counter()

        try:
            # First check if the bridge exposes connect() probe or is_connected
            if hasattr(bridge, "is_connected") and not bridge.is_connected():
                # Try connecting with short timeout
                if hasattr(bridge, "connect"):
                    try:
                        connected = await asyncio.wait_for(
                            bridge.connect(timeout=min(0.5, effective_timeout)),
                            timeout=min(0.5, effective_timeout)
                        )
                        if not connected:
                            return EngineLatencyMetric(
                                engine_name=engine_name,
                                is_available=False,
                                ttft_ms=float("inf"),
                                last_polled=time.time(),
                                error="Bridge not connected"
                            )
                    except Exception as e:
                        return EngineLatencyMetric(
                            engine_name=engine_name,
                            is_available=False,
                            ttft_ms=float("inf"),
                            last_polled=time.time(),
                            error=str(e)
                        )
                else:
                    return EngineLatencyMetric(
                        engine_name=engine_name,
                        is_available=False,
                        ttft_ms=float("inf"),
                        last_polled=time.time(),
                        error="Bridge not connected"
                    )

            # Probe TTFT using single-token stream with timeout
            stream = bridge.stream_generate(prompt=test_prompt, max_tokens=1)
            token_received = False
            first_chunk = ""
            ttft_ms = 0.0

            async with asyncio.timeout(effective_timeout):
                async for chunk in stream:
                    ttft_ms = (time.perf_counter() - t0) * 1000.0
                    first_chunk = chunk
                    token_received = True
                    break

            if token_received:
                # Sanitize first chunk: check for SYSTEM: or ERROR: or [red] error strings
                clean_chunk = (first_chunk or "").strip().upper()
                if (
                    clean_chunk.startswith("SYSTEM:")
                    or clean_chunk.startswith("ERROR:")
                    or "[RED]" in clean_chunk
                    or "API ERROR" in clean_chunk
                ):
                    return EngineLatencyMetric(
                        engine_name=engine_name,
                        is_available=False,
                        ttft_ms=float("inf"),
                        last_polled=time.time(),
                        error=f"Unconfigured or error response: {first_chunk.strip()[:60]}"
                    )

                # If bridge has a reported simulated latency, allow it if explicitly set
                reported_lat = getattr(bridge, "simulated_ttft_ms", None) or getattr(bridge, "latency_ms", None)
                if reported_lat is not None and reported_lat >= 0:
                    ttft_ms = float(reported_lat)

                metric = EngineLatencyMetric(
                    engine_name=engine_name,
                    is_available=True,
                    ttft_ms=round(ttft_ms, 2),
                    last_polled=time.time(),
                    error=None
                )
                return metric
            else:
                return EngineLatencyMetric(
                    engine_name=engine_name,
                    is_available=False,
                    ttft_ms=float("inf"),
                    last_polled=time.time(),
                    error="No token yielded"
                )

        except (asyncio.TimeoutError, TimeoutError) as e:
            return EngineLatencyMetric(
                engine_name=engine_name,
                is_available=False,
                ttft_ms=float("inf"),
                last_polled=time.time(),
                error=f"Timeout after {effective_timeout}s: {e}"
            )
        except Exception as e:
            return EngineLatencyMetric(
                engine_name=engine_name,
                is_available=False,
                ttft_ms=float("inf"),
                last_polled=time.time(),
                error=str(e)
            )

    async def poll_once(self) -> Dict[str, EngineLatencyMetric]:
        """Alias for poll_all_engines()."""
        return await self.poll_all_engines()

    async def poll_all_engines(self, force_all: bool = False) -> Dict[str, EngineLatencyMetric]:
        """
        Concurrently probe registered inference bridges and update metrics.
        Decouples cloud engines (Gemini, Cloudflare, Julien) from aggressive 3-second loop.
        Guarantees zero-crash execution via asyncio.gather(return_exceptions=True).
        """
        if not self.bridges:
            return self._metrics

        now = time.time()
        engine_names_to_poll = []

        for name, bridge in self.bridges.items():
            if name in CLOUD_ENGINES and not force_all:
                # Fast credential check for cloud engines
                if hasattr(bridge, "is_connected") and not bridge.is_connected():
                    self._metrics[name] = EngineLatencyMetric(
                        engine_name=name,
                        is_available=False,
                        ttft_ms=float("inf"),
                        last_polled=now,
                        error="Credentials not configured"
                    )
                    continue

                # Throttle cloud inference probing
                last_p = self.last_cloud_polled.get(name, 0.0)
                if now - last_p < self.cloud_poll_interval_sec:
                    continue
                self.last_cloud_polled[name] = now

            engine_names_to_poll.append(name)

        if not engine_names_to_poll:
            return self._metrics

        tasks = [
            self.measure_engine_ttft(name, self.bridges[name])
            for name in engine_names_to_poll
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, res in zip(engine_names_to_poll, results):
            if isinstance(res, EngineLatencyMetric):
                self._metrics[name] = res
            elif isinstance(res, Exception):
                self._metrics[name] = EngineLatencyMetric(
                    engine_name=name,
                    is_available=False,
                    ttft_ms=float("inf"),
                    last_polled=time.time(),
                    error=str(res)
                )
            elif isinstance(res, dict):
                self._metrics[name] = EngineLatencyMetric(
                    engine_name=name,
                    is_available=res.get("is_available", False),
                    ttft_ms=res.get("ttft_ms", float("inf")),
                    last_polled=res.get("last_polled", time.time()),
                    error=res.get("error")
                )

        if self._on_metric_update:
            try:
                self._on_metric_update(self._metrics)
            except Exception as e:
                logger.debug(f"Error in on_metric_update callback: {e}")

        return self._metrics

    def get_latencies(self) -> Dict[str, float]:
        """Return mapping of engine names to current TTFT latencies in ms."""
        return {name: m.ttft_ms for name, m in self._metrics.items()}

    def get_metrics(self) -> Dict[str, EngineLatencyMetric]:
        """Return copy of current latency metrics dict."""
        return dict(self._metrics)

    def get_fastest_engine(
        self,
        available_only: bool = True,
        candidates: Optional[List[str]] = None
    ) -> str:
        """
        Return the engine name with the lowest valid TTFT.
        Defaults to 'llama_rpc' if no external engine is available.
        """
        valid_candidates = candidates if candidates is not None else list(self.bridges.keys())
        # Filter out 'auto' if present in candidates
        valid_candidates = [c for c in valid_candidates if c != "auto"]

        eligible: List[tuple[str, float]] = []
        for name in valid_candidates:
            metric = self._metrics.get(name)
            if not metric:
                continue
            if available_only:
                if (
                    metric.is_available
                    and metric.ttft_ms >= 0
                    and not math.isnan(metric.ttft_ms)
                    and metric.ttft_ms < float("inf")
                ):
                    eligible.append((name, metric.ttft_ms))
            else:
                if (
                    metric.ttft_ms >= 0
                    and not math.isnan(metric.ttft_ms)
                    and metric.ttft_ms < float("inf")
                ):
                    eligible.append((name, metric.ttft_ms))

        if not eligible:
            return "llama_rpc"

        # Sort ascending by TTFT
        eligible.sort(key=lambda x: x[1])
        return eligible[0][0]

    def set_metric_for_testing(
        self,
        engine_name: str,
        ttft_ms: float,
        is_available: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Programmatic helper to set latency metrics for deterministic unit testing."""
        self._metrics[engine_name] = EngineLatencyMetric(
            engine_name=engine_name,
            is_available=is_available,
            ttft_ms=ttft_ms,
            last_polled=time.time(),
            error=error
        )

    def start(self, interval_sec: Optional[float] = None) -> None:
        """Alias for start_background_polling()."""
        self.start_background_polling(interval_sec=interval_sec)

    def start_background_polling(self, interval_sec: Optional[float] = None) -> None:
        """Start non-blocking periodic TTFT polling background task."""
        if interval_sec is not None:
            self.poll_interval_sec = interval_sec
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._background_loop())

    def stop(self) -> None:
        """Synchronously request stopping the background loop."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()

    async def stop_background_polling(self) -> None:
        """Gracefully stop and await background poller task cancellation."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._poll_task = None

    async def _background_loop(self) -> None:
        """Background coroutine continuously executing TTFT benchmark sweeps."""
        while self._running:
            try:
                await self.poll_all_engines()
                await asyncio.sleep(self.poll_interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"DynamicLatencyPoller loop error: {e}")
                await asyncio.sleep(self.poll_interval_sec)
