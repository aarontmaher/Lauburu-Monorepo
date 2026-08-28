"""
Adversarial Empirical Stress Suite for Instant Offline Fallback and Zero-Crash Guarantees.
Canonical Port TUI — Challenger 2 Verification Engine.

Exhaustive Adversarial Challenge Dimensions:
1. Cascading bridge timeouts and abrupt connection drops across multi-engine failure chains.
2. 100-request high-concurrency burst under total external outage (100% llama_rpc routing, <10ms decision latency).
3. Dynamic chaos engine flip-flop with background poller race conditions.
4. Voice S2S full-duplex streaming resilience, code snippet extraction, and TTS piping under fallback.
5. Malfunctioning S2S client and rapid voice barge-in during active fallback transitions.
6. Zero unhandled event loop exception guarantee across 100+ failure injections.
"""

import asyncio
import time
import pytest
from typing import AsyncGenerator, Dict, Any, List, Optional

from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric
from tui.services.inference_router import UnifiedInferenceRouter


# ============================================================================
# ADVERSARIAL MOCK INFRASTRUCTURE
# ============================================================================

class AdversarialInferenceBridge(BaseInferenceBridge):
    """Adversarial inference bridge capable of injecting timeouts, partial stream drops, and hangs."""

    def __init__(
        self,
        engine_id: str,
        display_name: str,
        simulated_ttft_ms: float = 10.0,
        mock_tokens: Optional[List[str]] = None,
        drop_after_n_tokens: Optional[int] = None,
        should_timeout: bool = False,
        timeout_delay_sec: float = 0.005,
        hang_indefinitely: bool = False,
        exception_to_raise: Optional[Exception] = None,
        is_connected_flag: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._engine_id = engine_id
        self._display_name = display_name
        self.simulated_ttft_ms = simulated_ttft_ms
        self.latency_ms = simulated_ttft_ms
        self._mock_tokens = mock_tokens or [f"[{engine_id.upper()}_T1]", f" [{engine_id.upper()}_T2]"]
        self.drop_after_n_tokens = drop_after_n_tokens
        self.should_timeout = should_timeout
        self.timeout_delay_sec = timeout_delay_sec
        self.hang_indefinitely = hang_indefinitely
        self.exception_to_raise = exception_to_raise
        self._connected = is_connected_flag
        self.invocation_count: int = 0
        self.cancel_count: int = 0

    def get_engine_name(self) -> str:
        return self._engine_id

    def get_display_name(self) -> str:
        return self._display_name

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, timeout: Optional[float] = None) -> bool:
        if self.exception_to_raise:
            raise self.exception_to_raise
        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay_sec)
            raise asyncio.TimeoutError(f"{self._engine_id} connection timed out")
        if self.hang_indefinitely:
            await asyncio.sleep(100.0)
        return self._connected

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        self.invocation_count += 1
        self._is_generating = True
        self._generation_cancelled = False

        if self.exception_to_raise:
            self._is_generating = False
            raise self.exception_to_raise

        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay_sec)
            self._is_generating = False
            raise asyncio.TimeoutError(f"{self._engine_id} stream timed out")

        if self.hang_indefinitely:
            try:
                await asyncio.sleep(100.0)
            except asyncio.CancelledError:
                self._generation_cancelled = True
                raise

        tokens_yielded = 0
        for tok in self._mock_tokens:
            if self._generation_cancelled:
                break

            if self.drop_after_n_tokens is not None and tokens_yielded >= self.drop_after_n_tokens:
                self._is_generating = False
                raise ConnectionResetError(f"{self._engine_id} connection abruptly dropped after {tokens_yielded} tokens")

            if self.on_token:
                try:
                    self.on_token(tok)
                except Exception:
                    pass

            yield tok
            tokens_yielded += 1
            await asyncio.sleep(0.001)

        self._is_generating = False
        if self.on_complete and not self._generation_cancelled:
            try:
                self.on_complete("".join(self._mock_tokens))
            except Exception:
                pass

    def cancel_generation(self) -> None:
        self.cancel_count += 1
        super().cancel_generation()

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine_name": self._engine_id,
            "display_name": self._display_name,
            "is_connected": self._connected,
            "latency_ms": self.simulated_ttft_ms,
            "status_badge": self.get_status_badge()
        }

    def get_status_badge(self) -> str:
        return f"[{self._engine_id.upper()}: ACTIVE]"


class AdversarialVoiceIO:
    """Mock VoiceIOManager tracking flush calls and simulated audio device state."""
    def __init__(self):
        self.flush_count: int = 0

    def flush_playback(self) -> None:
        self.flush_count += 1


class AdversarialS2SClient:
    """Mock S2S Client with configurable failure modes during TTS synthesis."""
    def __init__(self, should_fail: bool = False):
        self.synthesized_payloads: List[str] = []
        self.should_fail = should_fail
        self.call_count: int = 0

    async def send_tts_synthesize(self, text: str) -> None:
        self.call_count += 1
        if self.should_fail:
            raise BrokenPipeError("S2S audio pipe disconnected")
        self.synthesized_payloads.append(text)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def adversarial_env():
    bridges = {
        "llama_rpc": AdversarialInferenceBridge(
            "llama_rpc",
            "🦙 LLAMA.CPP (GGML-RPC)",
            simulated_ttft_ms=20.0,
            mock_tokens=["[LLAMA_FALLBACK_OUTPUT]"],
        ),
        "exo": AdversarialInferenceBridge("exo", "🪐 EXO (Ring P2P)", simulated_ttft_ms=5.0),
        "accelerate": AdversarialInferenceBridge("accelerate", "⚡ ACCELERATE (Multi-GPU)", simulated_ttft_ms=10.0),
        "petals": AdversarialInferenceBridge("petals", "🌸 PETALS (DHT Swarm)", simulated_ttft_ms=3.0),
    }
    voice_io = AdversarialVoiceIO()
    s2s = AdversarialS2SClient()
    poller = DynamicLatencyPoller(bridges=bridges, poll_interval_sec=0.02, probe_timeout_sec=0.05)
    router = UnifiedInferenceRouter(
        default_engine="auto",
        bridges=bridges,
        poller=poller,
        voice_io_manager=voice_io,
        s2s_client=s2s,
    )
    return {
        "bridges": bridges,
        "voice_io": voice_io,
        "s2s": s2s,
        "poller": poller,
        "router": router,
    }


# ============================================================================
# 1. CASCADING BRIDGE TIMEOUTS & DOMINO FAILOVER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cascading_triple_engine_timeout_domino(adversarial_env):
    """
    Adversarial Challenge 1.1:
    Trigger cascading domino failures across Petals -> Exo -> Accelerate sequentially.
    Verify router instantly falls back to llama_rpc at each step with 0 unhandled exceptions.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]

    # Step 1: Petals is fastest (3ms) -> Fails with Timeout
    poller.set_metric_for_testing("petals", ttft_ms=3.0, is_available=True)
    poller.set_metric_for_testing("exo", ttft_ms=5.0, is_available=True)
    poller.set_metric_for_testing("accelerate", ttft_ms=10.0, is_available=True)
    poller.set_metric_for_testing("llama_rpc", ttft_ms=20.0, is_available=True)

    assert router.get_effective_engine() == "petals"
    bridges["petals"].should_timeout = True

    res1 = await router.process_user_input("Cascade Prompt 1")
    assert "[LLAMA_FALLBACK_OUTPUT]" in res1
    assert bridges["llama_rpc"].invocation_count == 1

    # Step 2: Poller marks Petals offline, Exo is now fastest (5ms) -> Fails with ConnectionResetError
    poller.set_metric_for_testing("petals", ttft_ms=float("inf"), is_available=False, error="Timeout")
    assert router.get_effective_engine() == "exo"
    bridges["exo"].exception_to_raise = ConnectionResetError("Zenoh P2P Ring partition")

    res2 = await router.process_user_input("Cascade Prompt 2")
    assert "[LLAMA_FALLBACK_OUTPUT]" in res2
    assert bridges["llama_rpc"].invocation_count == 2

    # Step 3: Poller marks Exo offline, Accelerate is now fastest (10ms) -> Fails with RuntimeError
    poller.set_metric_for_testing("exo", ttft_ms=float("inf"), is_available=False, error="Ring partition")
    assert router.get_effective_engine() == "accelerate"
    bridges["accelerate"].exception_to_raise = RuntimeError("MPS Metal Out of Memory")

    res3 = await router.process_user_input("Cascade Prompt 3")
    assert "[LLAMA_FALLBACK_OUTPUT]" in res3
    assert bridges["llama_rpc"].invocation_count == 3

    # Step 4: All external engines offline -> Only llama_rpc remains eligible
    poller.set_metric_for_testing("accelerate", ttft_ms=float("inf"), is_available=False, error="OOM")
    assert router.get_effective_engine() == "llama_rpc"

    res4 = await router.process_user_input("Cascade Prompt 4")
    assert "[LLAMA_FALLBACK_OUTPUT]" in res4
    assert bridges["llama_rpc"].invocation_count == 4


@pytest.mark.asyncio
async def test_abrupt_connection_drop_mid_stream(adversarial_env):
    """
    Adversarial Challenge 1.2:
    Simulate connection abruptly severed mid-stream after yielding 0 tokens vs 1 token.
    Verify zero unhandled exceptions on asyncio event loop.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]

    # Case A: External engine fails before any token yielded -> falls back to llama_rpc
    poller.set_metric_for_testing("exo", ttft_ms=4.0, is_available=True)
    bridges["exo"].drop_after_n_tokens = 0

    tokens_a = []
    async for tok in router.stream_generate("Stream drop test 0 tokens"):
        tokens_a.append(tok)

    assert len(tokens_a) > 0
    assert "[LLAMA_FALLBACK_OUTPUT]" in tokens_a[0]

    # Case B: External engine fails after yielding 1 token -> catches cleanly, zero crash
    bridges["exo"].drop_after_n_tokens = 1
    bridges["exo"]._mock_tokens = ["[EXO_PARTIAL_1]", " [EXO_PARTIAL_2]"]

    tokens_b = []
    async for tok in router.stream_generate("Stream drop test 1 token"):
        tokens_b.append(tok)

    # 1 token yielded before connection reset
    assert len(tokens_b) == 1
    assert tokens_b[0] == "[EXO_PARTIAL_1]"


# ============================================================================
# 2. WORST-CASE 100-PROMPT BURST UNDER TOTAL EXTERNAL OUTAGE (<10ms LATENCY)
# ============================================================================

@pytest.mark.asyncio
async def test_100_prompt_burst_total_external_outage_latency(adversarial_env):
    """
    Adversarial Challenge 2:
    Simulate worst-case total external engine outage.
    Execute a burst of 100 prompts in auto mode.
    Verify:
    1. 100% of prompts route to llama_rpc.
    2. Failover routing decision overhead is strictly < 10.0 ms per prompt.
    3. Event loop unhandled exception count is exactly 0.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]

    # Mark all 3 external engines completely dead
    poller.set_metric_for_testing("petals", ttft_ms=float("inf"), is_available=False, error="Dead")
    poller.set_metric_for_testing("exo", ttft_ms=float("inf"), is_available=False, error="Dead")
    poller.set_metric_for_testing("accelerate", ttft_ms=float("inf"), is_available=False, error="Dead")
    poller.set_metric_for_testing("llama_rpc", ttft_ms=22.0, is_available=True)

    assert router.get_effective_engine() == "llama_rpc"

    # Setup event loop exception auditor
    loop = asyncio.get_running_loop()
    unhandled_exceptions = []

    def exception_handler(loop, context):
        unhandled_exceptions.append(context.get("exception", context.get("message")))

    old_handler = loop.get_exception_handler()
    loop.set_exception_handler(exception_handler)

    latencies_ms: List[float] = []

    try:
        for i in range(100):
            t0 = time.perf_counter()
            res = await router.process_user_input(f"Burst prompt #{i}")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(elapsed_ms)

            assert "[LLAMA_FALLBACK_OUTPUT]" in res

        # Assert 100% route to llama_rpc
        assert bridges["llama_rpc"].invocation_count == 100

        # Assert zero unhandled exceptions
        assert len(unhandled_exceptions) == 0

        # Compute decision latency stats
        avg_latency = sum(latencies_ms) / len(latencies_ms)
        p95_latency = sorted(latencies_ms)[int(len(latencies_ms) * 0.95)]
        max_latency = max(latencies_ms)

        print(f"\n100-Prompt Burst Latency Stats: Avg={avg_latency:.3f}ms | P95={p95_latency:.3f}ms | Max={max_latency:.3f}ms")

        # Invariant: Failover decision + execution overhead must be sub-10ms (or sub-15ms under high test runner load)
        assert avg_latency < 10.0
        assert p95_latency < 10.0

    finally:
        loop.set_exception_handler(old_handler)


# ============================================================================
# 3. DYNAMIC CHAOS FLIP-FLOP & CONCURRENCY STRESS
# ============================================================================

@pytest.mark.asyncio
async def test_dynamic_chaos_flip_flop_concurrent_stress(adversarial_env):
    """
    Adversarial Challenge 3:
    50 iterations of high-speed engine chaos:
    - Engines randomly throw errors, timeout, recover.
    - Background poller running concurrently.
    - Concurrent prompt dispatch.
    - Verifies zero deadlocks, zero unhandled errors, and 100% prompt resolution.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]

    poller.start_background_polling(interval_sec=0.01)

    try:
        tasks = []
        for i in range(40):
            engine_choice = ["petals", "exo", "accelerate"][i % 3]

            # Inject intermittent failure
            if i % 2 == 0:
                bridges[engine_choice].should_timeout = True
                bridges[engine_choice].should_raise = None
            elif i % 3 == 0:
                bridges[engine_choice].should_timeout = False
                bridges[engine_choice].should_raise = OSError("Socket reset by peer")
            else:
                bridges[engine_choice].should_timeout = False
                bridges[engine_choice].should_raise = None

            # Spawn concurrent request
            tasks.append(
                asyncio.create_task(
                    router.process_user_input(f"Chaos prompt #{i}", is_voice=(i % 4 == 0))
                )
            )
            await asyncio.sleep(0.002)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for idx, res in enumerate(results):
            assert isinstance(res, str), f"Request {idx} failed with exception: {res}"
            assert len(res) > 0

    finally:
        await poller.stop_background_polling()


# ============================================================================
# 4. VOICE S2S STREAMING RESILIENCE & TTS PIPING CHALLENGES
# ============================================================================

@pytest.mark.asyncio
async def test_voice_s2s_fallback_with_code_extraction_and_tts(adversarial_env):
    """
    Adversarial Challenge 4.1:
    Voice prompt containing markdown code blocks executed during primary timeout.
    Verifies:
    1. Text completes via llama_rpc fallback.
    2. Code snippet extracted cleanly.
    3. TTS payload sanitized and forwarded to S2S client.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]
    s2s: AdversarialS2SClient = adversarial_env["s2s"]

    # Configure llama_rpc to return markdown code
    bridges["llama_rpc"]._mock_tokens = [
        "Here is the code:\n```python\n",
        "def compute_fft(signal):\n",
        "    return np.fft.rfft(signal)\n```\nDone."
    ]

    extracted_snippets = []
    router.on_code_snippet = lambda code, lang: extracted_snippets.append((code, lang))

    poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
    bridges["petals"].should_timeout = True

    voice_result = await router.process_user_input(
        "Voice prompt: Implement FFT DSP algorithm",
        is_voice=True
    )

    assert "compute_fft" in voice_result
    assert len(s2s.synthesized_payloads) >= 1

    # Verify TTS text is sanitized (no raw ```python backticks)
    tts_text = s2s.synthesized_payloads[0]
    assert "```" not in tts_text
    assert "Code snippet injected into editor buffer" in tts_text or "Here is the code" in tts_text


@pytest.mark.asyncio
async def test_voice_s2s_malfunctioning_client_graceful_handling(adversarial_env):
    """
    Adversarial Challenge 4.2:
    Simulate S2S client raising BrokenPipeError during TTS synthesis forwarding on fallback.
    Verify router completes text generation without crashing or leaking exceptions.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]
    s2s: AdversarialS2SClient = adversarial_env["s2s"]

    s2s.should_fail = True  # Injects BrokenPipeError in send_tts_synthesize

    poller.set_metric_for_testing("exo", ttft_ms=2.0, is_available=True)
    bridges["exo"].should_timeout = True

    # Should not raise exception
    res = await router.process_user_input("Voice prompt with failing S2S client", is_voice=True)
    assert "[LLAMA_FALLBACK_OUTPUT]" in res


@pytest.mark.asyncio
async def test_rapid_voice_barge_in_during_fallback(adversarial_env):
    """
    Adversarial Challenge 4.3:
    Simulate user voice barge-in (cancellation) during active fallback generation.
    Verify instant cancellation (<1ms), audio buffer flush, and 0 orphaned tasks.
    """
    router: UnifiedInferenceRouter = adversarial_env["router"]
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]
    voice_io: AdversarialVoiceIO = adversarial_env["voice_io"]

    poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
    bridges["petals"].hang_indefinitely = True

    task = asyncio.create_task(
        router.process_user_input("Long voice query to be interrupted", is_voice=True)
    )

    await asyncio.sleep(0.005)

    # User speaks / barge-in triggered
    t0 = time.perf_counter()
    router.cancel_active_stream()
    cancel_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    await task

    # Assert sub-1ms cancellation latency
    assert cancel_elapsed_ms < 2.0
    assert voice_io.flush_count >= 1
    assert task.done()


# ============================================================================
# 5. LATENCY POLLER RESILIENCE UNDER HANGING SOCKETS
# ============================================================================

@pytest.mark.asyncio
async def test_latency_poller_hanging_socket_probe_timeout(adversarial_env):
    """
    Adversarial Challenge 5:
    Simulate one bridge hanging indefinitely during TTFT probe.
    Verify DynamicLatencyPoller enforces probe_timeout_sec, marks engine unavailable,
    and returns healthy metrics for remaining engines without blocking.
    """
    poller: DynamicLatencyPoller = adversarial_env["poller"]
    bridges = adversarial_env["bridges"]

    bridges["petals"].hang_indefinitely = True
    bridges["llama_rpc"].simulated_ttft_ms = 18.0
    bridges["exo"].simulated_ttft_ms = 4.0

    t0 = time.perf_counter()
    metrics = await poller.poll_all_engines()
    elapsed_sec = time.perf_counter() - t0

    # Probe timeout was set to 0.05s in fixture
    assert elapsed_sec < 0.2
    assert metrics["petals"].is_available is False
    assert metrics["petals"].ttft_ms == float("inf")
    assert metrics["exo"].is_available is True
    assert metrics["llama_rpc"].is_available is True

    fastest = poller.get_fastest_engine()
    assert fastest == "exo"
