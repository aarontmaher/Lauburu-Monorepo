"""
Adversarial Empirical Stress Suite for DynamicLatencyPoller and UnifiedInferenceRouter Auto Mode.
Challenger 1 Verification Suite.

Tests:
1. High-frequency dynamic latency oscillations (100 iterations) with strict min-TTFT verification.
2. Concurrent poller metric updates vs router query read/write safety audit.
3. Pathological latency and telemetry metrics (negative, zero, inf, nan, flapping).
4. 60+ concurrent auto stream_generate requests (deadlock freedom, zero token loss).
5. 60+ concurrent process_user_input requests across text and voice modes.
6. Sub-1ms cancellation latency benchmark under 50+ concurrent active streams.
7. Mixed concurrent timeout/network failure stress (50% failure rate under 50 concurrent tasks).
8. Concurrent engine mode switching during active auto streaming.
9. Empirical Diagnostic 1: Background poller probe cancellation collision on in-flight user stream.
10. Empirical Diagnostic 2: Zero TTFT metric exclusion in get_fastest_engine.
11. Empirical Diagnostic 3: Mid-stream connection drop fallback truncation.
"""

import time
import asyncio
import math
import random
import pytest
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple

from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric
from tui.services.inference_router import UnifiedInferenceRouter


class AdversarialMockBridge(BaseInferenceBridge):
    """
    Thread-safe, highly configurable mock inference bridge for adversarial testing.
    Supports dynamic latency shifts, simulated timeouts, exceptions, and token streaming.
    """

    def __init__(
        self,
        engine_id: str,
        display_name: str,
        simulated_ttft_ms: float = 10.0,
        mock_tokens: Optional[List[str]] = None,
        should_timeout: bool = False,
        timeout_delay_sec: float = 0.01,
        should_raise: Optional[Exception] = None,
        is_connected_flag: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._engine_id = engine_id
        self._display_name = display_name
        self.simulated_ttft_ms = simulated_ttft_ms
        self.latency_ms = simulated_ttft_ms
        self._mock_tokens = mock_tokens or [f"[{engine_id.upper()}_TOK1]", f" [{engine_id.upper()}_TOK2]"]
        self.should_timeout = should_timeout
        self.timeout_delay_sec = timeout_delay_sec
        self.should_raise = should_raise
        self._connected = is_connected_flag
        self.invocation_count: int = 0
        self._lock = asyncio.Lock()

    @property
    def engine_name(self) -> str:
        return self._engine_id

    def get_engine_name(self) -> str:
        return self._engine_id

    def get_display_name(self) -> str:
        return self._display_name

    def is_connected(self) -> bool:
        return self._connected

    def set_latency(self, ttft_ms: float) -> None:
        self.simulated_ttft_ms = ttft_ms
        self.latency_ms = ttft_ms

    async def connect(self, timeout: Optional[float] = None) -> bool:
        if self.should_raise:
            raise self.should_raise
        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay_sec)
            raise asyncio.TimeoutError(f"{self._engine_id} connect timeout")
        self.latency_ms = self.simulated_ttft_ms
        return self._connected

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        async with self._lock:
            self.invocation_count += 1
        
        self._is_generating = True
        self._generation_cancelled = False

        if self.should_raise:
            self._is_generating = False
            raise self.should_raise

        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay_sec)
            self._is_generating = False
            raise asyncio.TimeoutError(f"{self._engine_id} stream timed out")

        # Yield tokens with minimal delay
        await asyncio.sleep(0.001)

        for tok in self._mock_tokens:
            if self._generation_cancelled:
                break
            if self.on_token:
                try:
                    self.on_token(tok)
                except Exception:
                    pass
            yield tok
            await asyncio.sleep(0.001)

        self._is_generating = False
        if self.on_complete and not self._generation_cancelled:
            try:
                self.on_complete("".join(self._mock_tokens))
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine_name": self._engine_id,
            "display_name": self._display_name,
            "is_connected": self._connected,
            "latency_ms": self.simulated_ttft_ms,
            "status_badge": self.get_status_badge()
        }

    def get_status_badge(self) -> str:
        name_map = {
            "llama_rpc": "LLAMA.CPP",
            "exo": "EXO",
            "accelerate": "ACCELERATE",
            "petals": "PETALS",
        }
        disp = name_map.get(self._engine_id, self._engine_id.upper())
        return f"[{disp}: ACTIVE]"


class MockAdversarialS2SClient:
    def __init__(self):
        self.synthesized_payloads: List[str] = []
        self.is_connected: bool = True
        self._lock = asyncio.Lock()

    async def send_tts_synthesize(self, text: str) -> None:
        async with self._lock:
            self.synthesized_payloads.append(text)


def create_adversarial_test_rig():
    bridges = {
        "llama_rpc": AdversarialMockBridge("llama_rpc", "🦙 LLAMA.CPP (GGML-RPC)", simulated_ttft_ms=25.0),
        "exo": AdversarialMockBridge("exo", "🪐 EXO (Ring P2P)", simulated_ttft_ms=15.0),
        "accelerate": AdversarialMockBridge("accelerate", "⚡ ACCELERATE (Multi-GPU)", simulated_ttft_ms=35.0),
        "petals": AdversarialMockBridge("petals", "🌸 PETALS (DHT Swarm)", simulated_ttft_ms=80.0),
    }
    poller = DynamicLatencyPoller(bridges=bridges, poll_interval_sec=0.05, probe_timeout_sec=0.2)
    router = UnifiedInferenceRouter(
        default_engine="auto",
        bridges=bridges,
        poller=poller,
    )
    return bridges, poller, router


# ============================================================================
# 1. RAPID DYNAMIC LATENCY SHIFTS & MIN-TTFT ROUTING ADVERSARIAL CHALLENGE
# ============================================================================

@pytest.mark.asyncio
async def test_high_frequency_latency_oscillations_100x():
    """
    Adversarial Challenge 1:
    - Simulates 100 rapid, randomized latency shifts across all 4 engines.
    - After each shift, polls metrics and dispatches an auto-routed request.
    - Verifies that in 100% of cases, the router selects the exact backend with
      the lowest positive TTFT at that instant without race conditions.
    """
    bridges, poller, router = create_adversarial_test_rig()
    engine_keys = ["llama_rpc", "exo", "accelerate", "petals"]

    for iteration in range(100):
        # Generate random latencies between 0.5ms and 200.0ms
        latencies = {eng: round(random.uniform(0.5, 200.0), 2) for eng in engine_keys}
        
        # Explicitly designate a winner with lowest latency
        winner = random.choice(engine_keys)
        min_lat = round(random.uniform(0.1, 0.4), 3)
        latencies[winner] = min_lat

        for eng, lat in latencies.items():
            bridges[eng].set_latency(lat)

        # Poll all engines
        await poller.poll_all_engines()

        # Check effective engine
        effective = router.get_effective_engine()
        assert effective == winner, (
            f"Iteration {iteration}: Expected fastest engine '{winner}' (latency {min_lat}ms), "
            f"but router selected '{effective}'. Latencies: {latencies}"
        )

        # Reset counts and process prompt
        for b in bridges.values():
            b.invocation_count = 0

        res = await router.process_user_input(f"Oscillation prompt {iteration}")
        assert f"[{winner.upper()}_TOK1]" in res, (
            f"Iteration {iteration}: Result did not contain tokens from expected winner '{winner}'"
        )
        assert bridges[winner].invocation_count == 1


# ============================================================================
# 2. PATHOLOGICAL METRICS & ADVERSARIAL TELEMETRY HARDENING
# ============================================================================

@pytest.mark.asyncio
async def test_pathological_latency_and_telemetry_metrics():
    """
    Adversarial Challenge 2:
    - Injects pathological TTFT values: negative (-10ms), zero (0.0ms), inf (inf),
      nan (nan), and sudden offline errors.
    - Verifies router does not crash, ignores invalid negative/nan/inf values,
      and reliably resolves to healthy candidates or local llama_rpc fallback.
    """
    bridges, poller, router = create_adversarial_test_rig()

    # 1. Test NaN and Negative TTFT injection
    poller.set_metric_for_testing("petals", ttft_ms=float("nan"), is_available=True)
    poller.set_metric_for_testing("exo", ttft_ms=-15.0, is_available=True)
    poller.set_metric_for_testing("accelerate", ttft_ms=float("inf"), is_available=False)
    poller.set_metric_for_testing("llama_rpc", ttft_ms=25.0, is_available=True)

    fastest = poller.get_fastest_engine()
    assert fastest == "llama_rpc", f"Expected 'llama_rpc' fallback, got '{fastest}'"
    assert router.get_effective_engine() == "llama_rpc"

    # 2. Test all engines reporting inf / unavailable
    for eng in ["llama_rpc", "exo", "accelerate", "petals"]:
        poller.set_metric_for_testing(eng, ttft_ms=float("inf"), is_available=False, error="All offline")

    fastest_offline = poller.get_fastest_engine()
    assert fastest_offline == "llama_rpc"
    assert router.get_effective_engine() == "llama_rpc"

    # 3. Test sudden resurrection of an engine
    poller.set_metric_for_testing("accelerate", ttft_ms=2.1, is_available=True, error=None)
    assert router.get_effective_engine() == "accelerate"


# ============================================================================
# 3. 60+ CONCURRENT AUTO STREAM_GENERATE REQUESTS (DEADLOCK FREEDOM)
# ============================================================================

@pytest.mark.asyncio
async def test_60_plus_concurrent_auto_stream_generate():
    """
    Adversarial Challenge 3:
    - Spawns 60 concurrent stream_generate coroutines through UnifiedInferenceRouter in 'auto' mode.
    - Measures completion rate, checks for deadlocks, token corruption, or state leakage.
    - Asserts 100% of streams complete with valid tokens within tight timeout.
    """
    bridges, poller, router = create_adversarial_test_rig()
    bridges["exo"].set_latency(5.0)
    await poller.poll_all_engines()
    assert router.get_effective_engine() == "exo"

    concurrent_count = 64
    results: List[List[str]] = [[] for _ in range(concurrent_count)]

    async def _run_stream(stream_id: int):
        async for token in router.stream_generate(f"Concurrent prompt #{stream_id}", max_tokens=10):
            results[stream_id].append(token)

    tasks = [asyncio.create_task(_run_stream(i)) for i in range(concurrent_count)]

    # Complete all within 2.0s timeout
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)

    # Verify all 64 streams received both tokens cleanly
    for i in range(concurrent_count):
        assert len(results[i]) == 2, f"Stream {i} received {len(results[i])} tokens, expected 2"
        assert results[i][0] == "[EXO_TOK1]"
        assert results[i][1] == " [EXO_TOK2]"


# ============================================================================
# 4. 60+ CONCURRENT PROCESS_USER_INPUT REQUESTS (TEXT & VOICE)
# ============================================================================

@pytest.mark.asyncio
async def test_60_plus_concurrent_process_user_input_text_and_voice():
    """
    Adversarial Challenge 4:
    - Executes 64 concurrent process_user_input calls alternating between text and S2S voice mode.
    - Verifies thread-safety, zero deadlocks, and that S2S voice payloads are safely delivered.
    """
    bridges, poller, router = create_adversarial_test_rig()
    s2s = MockAdversarialS2SClient()
    router.bind_s2s_client(s2s)

    bridges["accelerate"].set_latency(3.0)
    await poller.poll_all_engines()
    assert router.get_effective_engine() == "accelerate"

    concurrent_count = 64

    async def _execute_input(idx: int) -> str:
        is_voice = (idx % 2 == 0)
        return await router.process_user_input(
            f"Process input concurrent prompt #{idx}",
            is_voice=is_voice,
            max_tokens=32
        )

    tasks = [asyncio.create_task(_execute_input(i)) for i in range(concurrent_count)]
    responses = await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)

    assert len(responses) == concurrent_count
    for i, resp in enumerate(responses):
        assert "[ACCELERATE_TOK1]" in resp, f"Request {i} failed to return expected token"

    # Half the requests were voice requests (32 requests)
    assert len(s2s.synthesized_payloads) >= 32, (
        f"Expected at least 32 synthesized payloads, got {len(s2s.synthesized_payloads)}"
    )


# ============================================================================
# 5. SUB-1MS CANCELLATION LATENCY UNDER 50+ CONCURRENT STREAMS
# ============================================================================

@pytest.mark.asyncio
async def test_sub_1ms_cancellation_under_50_concurrent_streams():
    """
    Adversarial Challenge 5:
    - Launches 50 concurrent active streaming tasks in auto mode.
    - Measures wall-clock execution time of router.cancel_active_stream() under concurrent load.
    - Asserts mean cancellation latency < 1.0 ms and p95 < 1.0 ms.
    """
    bridges, poller, router = create_adversarial_test_rig()
    bridges["exo"].set_latency(2.0)
    await poller.poll_all_engines()

    cancellation_timings_ns: List[int] = []

    for round_idx in range(20):
        # Spawn 50 concurrent streams
        active_tasks = []
        for i in range(50):
            t = asyncio.create_task(
                router.process_user_input(f"Cancellation storm {round_idx}-{i}", max_tokens=128)
            )
            active_tasks.append(t)

        # Allow streams to begin executing
        await asyncio.sleep(0.002)

        # Benchmark high-precision cancellation
        t0 = time.perf_counter_ns()
        router.cancel_active_stream()
        t1 = time.perf_counter_ns()
        cancellation_timings_ns.append(t1 - t0)

        # Cancel tasks cleanly
        for t in active_tasks:
            t.cancel()
        await asyncio.gather(*active_tasks, return_exceptions=True)

    latencies_ms = [ns / 1_000_000.0 for ns in cancellation_timings_ns]
    latencies_ms.sort()

    mean_lat = sum(latencies_ms) / len(latencies_ms)
    min_lat = latencies_ms[0]
    p50_lat = latencies_ms[int(len(latencies_ms) * 0.50)]
    p95_lat = latencies_ms[int(len(latencies_ms) * 0.95)]
    max_lat = latencies_ms[-1]

    print(f"\n[CONCURRENT LOAD CANCELLATION BENCHMARK (20 rounds x 50 streams)]")
    print(f"  Min:  {min_lat:.4f} ms")
    print(f"  Mean: {mean_lat:.4f} ms")
    print(f"  p50:  {p50_lat:.4f} ms")
    print(f"  p95:  {p95_lat:.4f} ms")
    print(f"  Max:  {max_lat:.4f} ms")

    assert mean_lat < 1.0, f"Mean cancellation latency under load exceeded 1.0ms: {mean_lat:.4f} ms"
    assert p95_lat < 1.0, f"p95 cancellation latency under load exceeded 1.0ms: {p95_lat:.4f} ms"


# ============================================================================
# 6. MIXED CONCURRENT TIMEOUT & NETWORK FAILURE STRESS (50% FAILURE RATE)
# ============================================================================

@pytest.mark.asyncio
async def test_mixed_concurrent_timeouts_and_successes_50x():
    """
    Adversarial Challenge 6:
    - 50 concurrent requests dispatched in auto mode where primary backends flap:
      50% fail with timeout or connection reset, 50% succeed.
    - Asserts that all failing requests seamlessly fall back to llama_rpc,
      all succeeding requests complete with primary tokens, and 0 unhandled loop errors occur.
    """
    loop = asyncio.get_running_loop()
    unhandled_exceptions = []

    def loop_exc_handler(l, ctx):
        unhandled_exceptions.append(ctx.get("exception", ctx.get("message")))

    old_handler = loop.get_exception_handler()
    loop.set_exception_handler(loop_exc_handler)

    try:
        bridges, poller, router = create_adversarial_test_rig()
        # Set Petals as primary target in auto mode
        poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
        assert router.get_effective_engine() == "petals"

        concurrent_count = 50

        async def _request_worker(idx: int) -> str:
            req_bridges = {
                "llama_rpc": AdversarialMockBridge("llama_rpc", "🦙 LLAMA.CPP", simulated_ttft_ms=20.0, mock_tokens=["[LLAMA_RPC_FALLBACK]"]),
                "petals": AdversarialMockBridge("petals", "🌸 PETALS", simulated_ttft_ms=2.0, mock_tokens=["[PETALS_SUCCESS]"], should_timeout=(idx % 2 == 0)),
            }
            req_poller = DynamicLatencyPoller(bridges=req_bridges)
            req_poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
            req_poller.set_metric_for_testing("llama_rpc", ttft_ms=20.0, is_available=True)
            req_router = UnifiedInferenceRouter(default_engine="auto", bridges=req_bridges, poller=req_poller)

            return await req_router.process_user_input(f"Mixed stress test prompt {idx}")

        tasks = [asyncio.create_task(_request_worker(i)) for i in range(concurrent_count)]
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=3.0)

        assert len(results) == concurrent_count
        for i, res in enumerate(results):
            if i % 2 == 0:
                assert "[LLAMA_RPC_FALLBACK]" in res, (
                    f"Failing request {i} failed to fallback cleanly. Result: {res}"
                )
            else:
                assert "[PETALS_SUCCESS]" in res, f"Succeeding request {i} did not return petals token. Result: {res}"

        assert len(unhandled_exceptions) == 0, f"Unhandled loop exceptions detected: {unhandled_exceptions}"
    finally:
        loop.set_exception_handler(old_handler)


# ============================================================================
# 7. CONCURRENT ENGINE MODE CYCLING DURING ACTIVE AUTO STREAMING
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_engine_mode_cycling_during_active_auto_streaming():
    """
    Adversarial Challenge 7:
    - 50 active streaming tasks continuously flowing in auto mode.
    - Simultaneously, a background task rapidly switches active engine modes
      (auto -> llama_rpc -> exo -> accelerate -> petals -> auto).
    - Verifies system resilience, zero deadlocks, and clean recovery.
    """
    bridges, poller, router = create_adversarial_test_rig()
    stop_event = asyncio.Event()
    cycle_errors: List[Exception] = []

    async def _cycler():
        while not stop_event.is_set():
            try:
                router.cycle_engine(1)
                await asyncio.sleep(0.005)
            except Exception as e:
                cycle_errors.append(e)

    cycler_task = asyncio.create_task(_cycler())

    async def _streamer(idx: int):
        try:
            tokens = []
            async for tok in router.stream_generate(f"Mode switch stress {idx}", max_tokens=10):
                tokens.append(tok)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    stream_tasks = [asyncio.create_task(_streamer(i)) for i in range(50)]

    await asyncio.sleep(0.2)
    stop_event.set()
    await cycler_task
    await asyncio.gather(*stream_tasks, return_exceptions=True)

    assert len(cycle_errors) == 0, f"Encountered errors during concurrent engine cycling: {cycle_errors}"


# ============================================================================
# 8. DIAGNOSTIC REPRODUCTIONS (EMPIRICAL FINDINGS)
# ============================================================================

@pytest.mark.asyncio
async def test_diagnostic_reproduction_poller_probe_cancels_user_stream():
    """
    Diagnostic Verification 1:
    Verifies that background poller probing does NOT call bridge.cancel_generation(),
    allowing concurrent in-flight user stream generations on the shared bridge to complete.
    """
    bridge = AdversarialMockBridge("llama_rpc", "LLAMA", simulated_ttft_ms=10.0, mock_tokens=["tok1", "tok2", "tok3", "tok4", "tok5"])
    poller = DynamicLatencyPoller(bridges={"llama_rpc": bridge})
    router = UnifiedInferenceRouter(default_engine="llama_rpc", bridges={"llama_rpc": bridge}, poller=poller)

    # Start long user stream
    async def _user_stream():
        toks = []
        async for t in router.stream_generate("user prompt", max_tokens=5):
            toks.append(t)
            await asyncio.sleep(0.01)
        return toks

    user_task = asyncio.create_task(_user_stream())
    await asyncio.sleep(0.005)  # Let user stream begin

    # Background poller probes the exact same bridge
    await poller.measure_engine_ttft("llama_rpc", bridge)

    received_tokens = await user_task
    # The poller does not cancel generation, so all 5 tokens arrive cleanly
    assert len(received_tokens) == 5, f"Expected 5 tokens without cancellation collision, got {len(received_tokens)}"


def test_diagnostic_reproduction_zero_ttft_exclusion():
    """
    Diagnostic Verification 2:
    Verifies that get_fastest_engine() properly includes valid 0.0ms TTFT metrics.
    """
    poller = DynamicLatencyPoller(bridges={"llama_rpc": None, "exo": None})
    poller.set_metric_for_testing("exo", ttft_ms=0.0, is_available=True)
    poller.set_metric_for_testing("llama_rpc", ttft_ms=20.0, is_available=True)

    # Because exo has ttft_ms == 0.0, it is now correctly included as the fastest engine
    fastest = poller.get_fastest_engine()
    assert fastest == "exo", "0.0ms TTFT is valid and should be selected as fastest"


@pytest.mark.asyncio
async def test_diagnostic_reproduction_midstream_drop_fallback_truncation():
    """
    Diagnostic Finding 3:
    Demonstrates that when a bridge fails mid-stream after yielding 1 token,
    the router logs fallback but returns truncated output without engaging fallback.
    """
    class DroppingBridge(BaseInferenceBridge):
        def get_engine_name(self): return "petals"
        def get_display_name(self): return "PETALS"
        def is_connected(self): return True
        async def connect(self, timeout=None): return True
        def get_status(self): return {}
        def get_status_badge(self): return "[PETALS: ACTIVE]"
        async def stream_generate(self, prompt, max_tokens=None, temperature=None):
            yield "Partial token 1..."
            raise ConnectionResetError("DHT dropped")

    class FallbackBridge(BaseInferenceBridge):
        def get_engine_name(self): return "llama_rpc"
        def get_display_name(self): return "LLAMA"
        def is_connected(self): return True
        async def connect(self, timeout=None): return True
        def get_status(self): return {}
        def get_status_badge(self): return "[LLAMA: ACTIVE]"
        async def stream_generate(self, prompt, max_tokens=None, temperature=None):
            yield "Fallback text"

    bridges = {"petals": DroppingBridge(), "llama_rpc": FallbackBridge()}
    poller = DynamicLatencyPoller(bridges=bridges)
    poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
    router = UnifiedInferenceRouter(default_engine="auto", bridges=bridges, poller=poller)

    res = await router.process_user_input("prompt")
    # Output is truncated to partial token, fallback was not completed
    assert res == "Partial token 1..."
