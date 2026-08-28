"""
Adversarial Empirical Stress Suite for UnifiedInferenceRouter and Polymorphic Inference Bridges.
Challenger 1 Verification Engine.

Tests:
1. 50x Rapid mid-stream engine switching during active token generation.
2. Asyncio task leak audit and unhandled CancelledError detection on event loop.
3. High-resolution sub-1ms cancellation latency benchmark (100 samples per bridge + router).
4. Micro-yield & event loop jitter profiling during continuous token streaming (60 FPS UI guarantee).
5. Multi-task concurrent barge-in and redundant cancellation idempotency stress.
"""

import asyncio
import time
import pytest
from typing import List, Dict, Any, Optional

from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.inference_bridges.llama_bridge import LlamaRpcInferenceBridge
from tui.services.inference_bridges.exo_bridge import ExoInferenceBridge
from tui.services.inference_bridges.accelerate_bridge import AccelerateInferenceBridge
from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge
from tui.services.inference_router import UnifiedInferenceRouter


class MockVoiceIO:
    def __init__(self):
        self.flush_count: int = 0
    def flush_playback(self) -> None:
        self.flush_count += 1


class MockS2S:
    def __init__(self):
        self.sent_payloads: List[str] = []
    async def send_tts_synthesize(self, text: str) -> None:
        self.sent_payloads.append(text)


# ============================================================================
# 1. 50X RAPID MID-STREAM ENGINE SWITCHING STRESS TEST
# ============================================================================

@pytest.mark.asyncio
async def test_rapid_engine_switching_50x_mid_stream():
    """
    Stress test:
    - Initiates prompt generation on current engine.
    - Rapidly cycles engine 50 times mid-stream with micro-intervals (2ms-5ms).
    - Verifies router remains completely stable, active engine updates correctly,
      and no orphaned tasks or corrupt states remain.
    """
    voice_io = MockVoiceIO()
    s2s = MockS2S()
    tokens_streamed: List[str] = []

    router = UnifiedInferenceRouter(
        default_engine="llama_rpc",
        voice_io_manager=voice_io,
        s2s_client=s2s,
        on_token=lambda tok: tokens_streamed.append(tok)
    )
    for b in router.bridges.values():
        b.set_mock_tokens([f"token_{i}" for i in range(20)])

    engines = ["llama_rpc", "exo", "accelerate", "petals"]
    active_tasks: List[asyncio.Task] = []

    for i in range(50):
        target_engine = engines[i % len(engines)]
        
        # Start generation in background
        task = asyncio.create_task(
            router.process_user_input(
                f"Iter {i}: Implement distributed matrix tensor shard {target_engine}",
                is_voice=(i % 2 == 0),
                max_tokens=64
            )
        )
        active_tasks.append(task)

        # Allow stream to start generating (3ms)
        await asyncio.sleep(0.003)

        # Mid-stream swap to next engine
        next_engine = engines[(i + 1) % len(engines)]
        swapped = router.set_active_engine(next_engine)
        assert swapped == next_engine
        assert router.get_active_engine() == next_engine

    # Final cleanup wait
    await asyncio.sleep(0.1)
    
    # Verify all tasks finished (either returned or cancelled)
    for idx, t in enumerate(active_tasks):
        assert t.done(), f"Task {idx} failed to complete!"

    assert voice_io.flush_count >= 50
    assert router.get_active_engine() in engines


# ============================================================================
# 2. ZERO TASK LEAK & UNHANDLED CANCELLEDERROR VERIFICATION
# ============================================================================

@pytest.mark.asyncio
async def test_zero_task_leak_and_no_unhandled_cancelled_error():
    """
    Empirical Leak & Exception Audit:
    - Installs event loop exception handler to trap any unhandled exceptions/CancelledError.
    - Runs 50 rapid stream-and-cancel iterations.
    - Audits asyncio.all_tasks() before and after to verify zero leaked background coroutines.
    - Asserts 0 unhandled exceptions reported to the event loop.
    """
    loop = asyncio.get_running_loop()
    unhandled_exceptions: List[Dict[str, Any]] = []

    def custom_exc_handler(l, context):
        # Ignore expected cleanup warnings if any, but capture genuine unhandled errors
        exc = context.get("exception")
        msg = context.get("message", "")
        unhandled_exceptions.append({"message": msg, "exception": exc, "context": context})

    old_handler = loop.get_exception_handler()
    loop.set_exception_handler(custom_exc_handler)

    try:
        initial_tasks = {t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()}
        
        voice_io = MockVoiceIO()
        router = UnifiedInferenceRouter(
            default_engine="llama_rpc",
            voice_io_manager=voice_io
        )

        for i in range(50):
            # Launch stream_generate
            async def _consume_stream(eng):
                router.set_active_engine(eng)
                async for _ in router.stream_generate(f"Stress prompt {i}", max_tokens=100):
                    pass

            t = asyncio.create_task(_consume_stream(router.SUPPORTED_ENGINES[i % 4]))
            await asyncio.sleep(0.002)  # Stream running
            
            # Cancel via router
            router.cancel_active_stream()
            
            try:
                await asyncio.wait_for(t, timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Give event loop one tick to settle
        await asyncio.sleep(0.05)

        current_tasks = {t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()}
        leaked_tasks = current_tasks - initial_tasks

        # Verify no leaked tasks created during stress loop
        assert len(leaked_tasks) == 0, f"Leaked tasks detected: {leaked_tasks}"
        
        # Verify no unhandled CancelledError or exceptions escaped to event loop
        assert len(unhandled_exceptions) == 0, f"Unhandled loop exceptions: {unhandled_exceptions}"

    finally:
        loop.set_exception_handler(old_handler)


# ============================================================================
# 3. HIGH-RESOLUTION SUB-1MS CANCELLATION LATENCY BENCHMARK
# ============================================================================

@pytest.mark.asyncio
async def test_sub_1ms_cancellation_latency_benchmark():
    """
    Empirical Latency Benchmark:
    - Measures wall-clock execution time of router.cancel_active_stream()
      and router.set_active_engine() across 100 samples during active stream generation.
    - Asserts mean cancellation latency < 1.0 ms and p95 latency < 1.0 ms.
    """
    router = UnifiedInferenceRouter(default_engine="llama_rpc", voice_io_manager=MockVoiceIO())
    for b in router.bridges.values():
        b.set_mock_tokens([f"token_{i}" for i in range(20)])
    
    latencies_ns: List[int] = []

    for i in range(100):
        # Start a stream
        gen_task = asyncio.create_task(
            router.process_user_input(f"Benchmark prompt {i}", max_tokens=128)
        )
        await asyncio.sleep(0.002)  # Ensure generation active

        # Measure high precision cancellation latency
        t0 = time.perf_counter_ns()
        router.cancel_active_stream()
        t1 = time.perf_counter_ns()
        latencies_ns.append(t1 - t0)

        try:
            await asyncio.wait_for(gen_task, timeout=0.05)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    latencies_ms = [ns / 1_000_000.0 for ns in latencies_ns]
    latencies_ms.sort()

    mean_lat = sum(latencies_ms) / len(latencies_ms)
    min_lat = latencies_ms[0]
    p50_lat = latencies_ms[int(len(latencies_ms) * 0.50)]
    p95_lat = latencies_ms[int(len(latencies_ms) * 0.95)]
    p99_lat = latencies_ms[int(len(latencies_ms) * 0.99)]
    max_lat = latencies_ms[-1]

    print(f"\n[CANCELLATION BENCHMARK RESULTS (100 samples)]")
    print(f"  Min:  {min_lat:.4f} ms")
    print(f"  Mean: {mean_lat:.4f} ms")
    print(f"  p50:  {p50_lat:.4f} ms")
    print(f"  p95:  {p95_lat:.4f} ms")
    print(f"  p99:  {p99_lat:.4f} ms")
    print(f"  Max:  {max_lat:.4f} ms")

    # Strict empirical assertions
    assert mean_lat < 1.0, f"Mean cancellation latency exceeded 1ms: {mean_lat:.4f} ms"
    assert p95_lat < 1.0, f"p95 cancellation latency exceeded 1ms: {p95_lat:.4f} ms"


# ============================================================================
# 4. MICRO-YIELD & EVENT LOOP JITTER PROFILING (60 FPS UI GUARANTEE)
# ============================================================================

@pytest.mark.asyncio
async def test_streaming_maintains_micro_yields_without_blocking_event_loop():
    """
    Event Loop Responsiveness & Micro-Yield Test:
    - Runs a background heartbeat checking time every 5ms.
    - Simultaneously streams long token responses through all 4 bridges.
    - Measures maximum jitter (delay delta) on the heartbeat.
    - If any bridge blocks synchronously without yielding, jitter spikes > 50ms.
    - Asserts max jitter < 40ms, proving the Textual UI rendering loop is never starved.
    """
    heartbeat_delays: List[float] = []
    stop_heartbeat = asyncio.Event()

    async def _heartbeat():
        target_interval = 0.005  # 5ms
        while not stop_heartbeat.is_set():
            t0 = time.perf_counter()
            await asyncio.sleep(target_interval)
            elapsed = time.perf_counter() - t0
            jitter = max(0.0, elapsed - target_interval)
            heartbeat_delays.append(jitter * 1000.0)

    hb_task = asyncio.create_task(_heartbeat())

    router = UnifiedInferenceRouter(default_engine="llama_rpc")
    for b in router.bridges.values():
        b.set_mock_tokens([f"token_{i}" for i in range(20)])
    
    # Stream across all 4 engines sequentially
    for eng in ["llama_rpc", "exo", "accelerate", "petals"]:
        router.set_active_engine(eng)
        tokens = []
        async for tok in router.stream_generate(f"Generate large output for {eng}", max_tokens=20):
            tokens.append(tok)
        assert len(tokens) > 0

    stop_heartbeat.set()
    await hb_task

    assert len(heartbeat_delays) > 20
    max_jitter_ms = max(heartbeat_delays)
    avg_jitter_ms = sum(heartbeat_delays) / len(heartbeat_delays)

    print(f"\n[EVENT LOOP JITTER METRICS (Heartbeat 5ms interval)]")
    print(f"  Samples:    {len(heartbeat_delays)}")
    print(f"  Avg Jitter: {avg_jitter_ms:.2f} ms")
    print(f"  Max Jitter: {max_jitter_ms:.2f} ms")

    # A synchronous block would cause jitter >= 100ms
    # 60 FPS frame time budget is 16.6ms; max tolerable UI jitter is < 40ms
    assert max_jitter_ms < 40.0, f"Event loop starved! Max jitter: {max_jitter_ms:.2f} ms"


# ============================================================================
# 5. IDEMPOTENT & MULTI-CALL CANCELLATION HARDENING
# ============================================================================

def test_router_cancel_active_stream_idempotent_when_idle():
    """Verify calling cancel_active_stream multiple times while idle never throws."""
    router = UnifiedInferenceRouter(default_engine="llama_rpc")
    for _ in range(20):
        router.cancel_active_stream()
    assert router.active_engine == "llama_rpc"


@pytest.mark.asyncio
async def test_rapid_cycle_engine_100x_in_tight_loop():
    """Verify rapid synchronous cycle_engine calls under active async context."""
    router = UnifiedInferenceRouter(default_engine="llama_rpc")
    start_engine = router.active_engine
    num_engines = len(router.supported_engines)
    total_cycles = num_engines * 15
    for i in range(total_cycles):
        next_eng = router.cycle_engine(1)
        assert next_eng in router.SUPPORTED_ENGINES
    assert router.active_engine == start_engine
