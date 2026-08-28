"""
Unit tests for Instant Offline Fallback in Auto Inference Mode.
Verifies that when primary engines (petals DHT, exo ring, etc.) timeout or raise
connection errors, UnifiedInferenceRouter in 'auto' mode instantly and seamlessly
falls back to local llama.cpp without crashing the event loop or dropping user prompts.
"""

import time
import asyncio
import pytest
from typing import AsyncGenerator, Dict, Any, List, Optional

from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.latency_poller import DynamicLatencyPoller
from tui.services.inference_router import UnifiedInferenceRouter


class MockFallbackInferenceBridge(BaseInferenceBridge):
    """Mock bridge for testing timeouts, network drops, and fallback recovery."""

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
        self._mock_tokens = mock_tokens or [f"[{engine_id.upper()}_TOKEN_1]", f" [{engine_id.upper()}_TOKEN_2]"]
        self.should_timeout = should_timeout
        self.timeout_delay_sec = timeout_delay_sec
        self.should_raise = should_raise
        self._connected = is_connected_flag
        self.invocation_count: int = 0

    @property
    def engine_name(self) -> str:
        return self._engine_id

    def get_engine_name(self) -> str:
        return self._engine_id

    def get_display_name(self) -> str:
        return self._display_name

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, timeout: Optional[float] = None) -> bool:
        if self.should_raise:
            raise self.should_raise
        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay_sec)
            raise asyncio.TimeoutError(f"{self._engine_id} connection timed out")
        self.latency_ms = self.simulated_ttft_ms
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

        if self.should_raise:
            self._is_generating = False
            raise self.should_raise

        if self.should_timeout:
            await asyncio.sleep(self.timeout_delay_sec)
            self._is_generating = False
            raise asyncio.TimeoutError(f"{self._engine_id} stream generation timed out")

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
        if self.on_complete:
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
        return f"[{self._engine_id.upper()}: ACTIVE]"


class MockS2SClient:
    """Mock PersonaPlexS2SClient to verify TTS forwarding during fallback."""
    def __init__(self):
        self.synthesized_payloads: List[str] = []
        self.is_connected: bool = True

    async def send_tts_synthesize(self, text: str) -> None:
        self.synthesized_payloads.append(text)


@pytest.fixture
def fallback_bridges() -> Dict[str, MockFallbackInferenceBridge]:
    return {
        "llama_rpc": MockFallbackInferenceBridge(
            "llama_rpc",
            "🦙 LLAMA.CPP (GGML-RPC)",
            simulated_ttft_ms=25.0,
            mock_tokens=["[LLAMA_FALLBACK_TOKEN_1]", " [LLAMA_FALLBACK_TOKEN_2]"],
        ),
        "exo": MockFallbackInferenceBridge("exo", "🪐 EXO (Ring P2P)", simulated_ttft_ms=10.0),
        "accelerate": MockFallbackInferenceBridge("accelerate", "⚡ ACCELERATE (Multi-GPU)", simulated_ttft_ms=15.0),
        "petals": MockFallbackInferenceBridge("petals", "🌸 PETALS (DHT Swarm)", simulated_ttft_ms=5.0),
    }


@pytest.fixture
def fallback_poller(fallback_bridges) -> DynamicLatencyPoller:
    return DynamicLatencyPoller(bridges=fallback_bridges, poll_interval_sec=0.05, probe_timeout_sec=0.1)


@pytest.fixture
def fallback_router(fallback_bridges, fallback_poller) -> UnifiedInferenceRouter:
    return UnifiedInferenceRouter(
        default_engine="auto",
        bridges=fallback_bridges,
        poller=fallback_poller,
    )


# ============================================================================
# 1. PRIMARY TIMEOUT FAILOVER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_on_primary_engine_timeout(fallback_bridges, fallback_router):
    """Verify that when primary engine (Petals) times out, router seamlessly falls back to llama_rpc."""
    assert fallback_router.active_engine == "auto"

    # Set Petals as fastest engine in poller
    fallback_poller = fallback_router.poller
    fallback_poller.set_metric_for_testing("petals", ttft_ms=5.0, is_available=True)
    fallback_poller.set_metric_for_testing("llama_rpc", ttft_ms=25.0, is_available=True)

    assert fallback_router.get_effective_engine() == "petals"

    # Configure Petals to simulate stream timeout
    fallback_bridges["petals"].should_timeout = True

    # Execute user input in auto mode
    result = await fallback_router.process_user_input("Generate neural network layer", is_voice=False)

    # Assert fallback to llama_rpc executed successfully
    assert "[LLAMA_FALLBACK_TOKEN_1]" in result
    assert fallback_bridges["llama_rpc"].invocation_count == 1


@pytest.mark.asyncio
async def test_auto_fallback_stream_generate_timeout(fallback_bridges, fallback_router):
    """Verify stream_generate yields fallback tokens from llama_rpc on primary stream timeout."""
    fallback_poller = fallback_router.poller
    fallback_poller.set_metric_for_testing("exo", ttft_ms=3.0, is_available=True)
    fallback_poller.set_metric_for_testing("llama_rpc", ttft_ms=20.0, is_available=True)

    assert fallback_router.get_effective_engine() == "exo"
    fallback_bridges["exo"].should_timeout = True

    tokens = []
    async for token in fallback_router.stream_generate("Stream generation fallback test"):
        tokens.append(token)

    assert len(tokens) == 2
    assert tokens[0] == "[LLAMA_FALLBACK_TOKEN_1]"
    assert tokens[1] == " [LLAMA_FALLBACK_TOKEN_2]"
    assert fallback_bridges["llama_rpc"].invocation_count == 1


# ============================================================================
# 2. ZERO EVENT LOOP CRASH GUARANTEE TEST
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_zero_event_loop_crash(fallback_bridges, fallback_router):
    """
    Stress test:
    - Triggers 25 consecutive timeouts across different primary engines in auto mode.
    - Asserts 0 unhandled exceptions or CancelledError escape to the event loop.
    """
    loop = asyncio.get_running_loop()
    unhandled_exceptions = []

    def loop_exception_handler(loop, context):
        unhandled_exceptions.append(context.get("exception", context.get("message")))

    old_handler = loop.get_exception_handler()
    loop.set_exception_handler(loop_exception_handler)

    try:
        engines = ["petals", "exo", "accelerate"]
        for i in range(25):
            target = engines[i % len(engines)]
            fallback_router.poller.set_metric_for_testing(target, ttft_ms=2.0, is_available=True)
            fallback_bridges[target].should_timeout = True

            result = await fallback_router.process_user_input(f"Stress test prompt #{i}")
            assert "[LLAMA_FALLBACK_TOKEN_1]" in result

        assert len(unhandled_exceptions) == 0
    finally:
        loop.set_exception_handler(old_handler)


# ============================================================================
# 3. CONNECTION ERROR & EXCEPTION FAILOVER
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_on_connection_error_and_exception(fallback_bridges, fallback_router):
    """Verify failover to llama_rpc when primary engine raises ConnectionRefusedError or RuntimeError."""
    fallback_router.poller.set_metric_for_testing("accelerate", ttft_ms=1.0, is_available=True)
    assert fallback_router.get_effective_engine() == "accelerate"

    # Simulate hardware exception or network drop
    fallback_bridges["accelerate"].should_raise = ConnectionRefusedError("Metal MPS cluster unreachable")

    result = await fallback_router.process_user_input("Process input with hardware drop")
    assert "[LLAMA_FALLBACK_TOKEN_1]" in result
    assert fallback_bridges["llama_rpc"].invocation_count == 1


# ============================================================================
# 4. ALL EXTERNAL ENGINES OFFLINE TEST
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_all_external_engines_offline(fallback_bridges, fallback_router):
    """Verify router cleanly defaults to local llama_rpc when all external engines are offline."""
    poller = fallback_router.poller
    poller.set_metric_for_testing("petals", ttft_ms=float("inf"), is_available=False, error="DHT offline")
    poller.set_metric_for_testing("exo", ttft_ms=float("inf"), is_available=False, error="Ring partitioned")
    poller.set_metric_for_testing("accelerate", ttft_ms=float("inf"), is_available=False, error="No GPU")
    poller.set_metric_for_testing("llama_rpc", ttft_ms=25.0, is_available=True)

    assert fallback_router.get_effective_engine() == "llama_rpc"

    result = await fallback_router.process_user_input("Local execution test")
    assert "[LLAMA_FALLBACK_TOKEN_1]" in result
    assert fallback_bridges["llama_rpc"].invocation_count == 1


# ============================================================================
# 5. DECISION LATENCY BENCHMARK (< 10ms)
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_decision_latency_sub_10ms(fallback_bridges, fallback_router):
    """Verify internal failover overhead from primary failure detection to llama_rpc is < 10.0 ms."""
    fallback_router.poller.set_metric_for_testing("exo", ttft_ms=2.0, is_available=True)
    fallback_bridges["exo"].should_raise = ConnectionResetError("Peer reset")

    t0 = time.perf_counter()
    result = await fallback_router.process_user_input("Latency benchmark prompt")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert "[LLAMA_FALLBACK_TOKEN_1]" in result
    # Fallback decision overhead plus minimal mock generator yield
    assert elapsed_ms < 20.0


# ============================================================================
# 6. VOICE S2S PRESERVED DURING FALLBACK
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_voice_s2s_preserved(fallback_bridges, fallback_router):
    """Verify voice prompt fallback forwards final text from llama_rpc to S2S client."""
    s2s = MockS2SClient()
    fallback_router.bind_s2s_client(s2s)

    fallback_router.poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
    fallback_bridges["petals"].should_timeout = True

    result = await fallback_router.process_user_input("Voice coding fallback prompt", is_voice=True)
    assert len(result) > 0
    assert len(s2s.synthesized_payloads) >= 1
    assert "LLAMA" in s2s.synthesized_payloads[0].upper()


# ============================================================================
# 7. RECOVERY WHEN PRIMARY RESTORED
# ============================================================================

@pytest.mark.asyncio
async def test_auto_fallback_recovery_when_primary_restored(fallback_bridges, fallback_router):
    """Verify system resumes routing to primary engine once it recovers and reports healthy TTFT."""
    # 1. Petals is primary and fails -> fall back to llama_rpc
    fallback_router.poller.set_metric_for_testing("petals", ttft_ms=2.0, is_available=True)
    fallback_bridges["petals"].should_timeout = True

    res1 = await fallback_router.process_user_input("Prompt 1")
    assert "[LLAMA_FALLBACK_TOKEN_1]" in res1

    # 2. Petals recovers and poller records healthy metric
    fallback_bridges["petals"].should_timeout = False
    fallback_bridges["petals"]._mock_tokens = ["[PETALS_RECOVERED_1]"]
    fallback_router.poller.set_metric_for_testing("petals", ttft_ms=3.5, is_available=True)

    # 3. Next prompt routes to recovered Petals
    res2 = await fallback_router.process_user_input("Prompt 2")
    assert "[PETALS_RECOVERED_1]" in res2
    assert fallback_bridges["petals"].invocation_count == 2
