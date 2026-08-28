"""
Unit tests for Dynamic TTFT Latency Poller and Auto-Inference Routing.
Verifies TTFT benchmarking, dynamic lowest-TTFT prompt routing, HUD badge formatting,
voice S2S forwarding in auto mode, and poller lifecycle safety.
"""

import time
import asyncio
import pytest
from typing import AsyncGenerator, Dict, Any, List, Optional

from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.latency_poller import DynamicLatencyPoller, EngineLatencyMetric
from tui.services.inference_router import UnifiedInferenceRouter
from tui.widgets.engine_selector import EngineSelectorWidget


class MockInferenceBridge(BaseInferenceBridge):
    """Configurable mock inference bridge for deterministic TTFT and routing tests."""

    def __init__(
        self,
        engine_id: str,
        display_name: str,
        simulated_ttft_ms: float = 10.0,
        mock_tokens: Optional[List[str]] = None,
        should_timeout: bool = False,
        timeout_delay_sec: float = 0.05,
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

        # Scaled simulated TTFT delay for high-speed deterministic testing
        await asyncio.sleep(max(0.001, self.simulated_ttft_ms / 10000.0))

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
        name_map = {
            "llama_rpc": "LLAMA.CPP",
            "exo": "EXO",
            "accelerate": "ACCELERATE",
            "petals": "PETALS",
        }
        disp = name_map.get(self._engine_id, self._engine_id.upper())
        return f"[{disp}: ACTIVE]"


class MockS2SClient:
    """Mock PersonaPlexS2SClient to verify TTS synthesis message forwarding."""
    def __init__(self):
        self.synthesized_payloads: List[str] = []
        self.is_connected: bool = True

    async def send_tts_synthesize(self, text: str) -> None:
        self.synthesized_payloads.append(text)


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_bridges() -> Dict[str, MockInferenceBridge]:
    return {
        "llama_rpc": MockInferenceBridge("llama_rpc", "🦙 LLAMA.CPP (GGML-RPC)", simulated_ttft_ms=28.0),
        "exo": MockInferenceBridge("exo", "🪐 EXO (Ring P2P)", simulated_ttft_ms=12.5),
        "accelerate": MockInferenceBridge("accelerate", "⚡ ACCELERATE (Multi-GPU)", simulated_ttft_ms=45.0),
        "petals": MockInferenceBridge("petals", "🌸 PETALS (DHT Swarm)", simulated_ttft_ms=110.0),
    }


@pytest.fixture
def dynamic_poller(mock_bridges) -> DynamicLatencyPoller:
    return DynamicLatencyPoller(bridges=mock_bridges, poll_interval_sec=0.05, probe_timeout_sec=0.5)


@pytest.fixture
def auto_router(mock_bridges, dynamic_poller) -> UnifiedInferenceRouter:
    router = UnifiedInferenceRouter(
        default_engine="auto",
        bridges=mock_bridges,
        poller=dynamic_poller,
    )
    return router


# ============================================================================
# 1. POLLER TTFT BENCHMARKING & RANKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_poller_ttft_calculation_and_ranking(mock_bridges, dynamic_poller):
    """Verify DynamicLatencyPoller polls all engines concurrently and ranks lowest TTFT."""
    metrics = await dynamic_poller.poll_all_engines()

    assert len(metrics) == 4
    assert metrics["exo"].is_available is True
    assert metrics["exo"].ttft_ms == 12.5
    assert metrics["llama_rpc"].ttft_ms == 28.0
    assert metrics["accelerate"].ttft_ms == 45.0
    assert metrics["petals"].ttft_ms == 110.0

    fastest = dynamic_poller.get_fastest_engine()
    assert fastest == "exo"

    latencies = dynamic_poller.get_latencies()
    assert latencies["exo"] == 12.5
    assert latencies["petals"] == 110.0


@pytest.mark.asyncio
async def test_poller_dynamic_ttft_update_and_reranking(mock_bridges, dynamic_poller):
    """Verify poller dynamically re-ranks engines as simulated latencies change."""
    # Initial poll: exo is fastest
    await dynamic_poller.poll_all_engines()
    assert dynamic_poller.get_fastest_engine() == "exo"

    # Simulate network shift: Petals DHT becomes fastest (6.2ms), Exo slows down (85.0ms)
    mock_bridges["petals"].simulated_ttft_ms = 6.2
    mock_bridges["petals"].latency_ms = 6.2
    mock_bridges["exo"].simulated_ttft_ms = 85.0
    mock_bridges["exo"].latency_ms = 85.0

    await dynamic_poller.poll_all_engines()
    assert dynamic_poller.get_fastest_engine() == "petals"

    # Simulate Accelerate MPS Metal becoming fastest (1.1ms)
    mock_bridges["accelerate"].simulated_ttft_ms = 1.1
    mock_bridges["accelerate"].latency_ms = 1.1

    await dynamic_poller.poll_all_engines()
    assert dynamic_poller.get_fastest_engine() == "accelerate"


# ============================================================================
# 2. AUTO MODE PROMPT ROUTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_auto_mode_prompt_routing_to_lowest_ttft(mock_bridges, auto_router):
    """Verify router in 'auto' mode intercepts prompts and routes to lowest TTFT backend."""
    assert auto_router.active_engine == "auto"

    # 1. Exo is fastest (12.5ms)
    await auto_router.poller.poll_all_engines()
    assert auto_router.get_effective_engine() == "exo"

    for b in mock_bridges.values():
        b.invocation_count = 0

    result = await auto_router.process_user_input("Write quicksort in Rust")
    assert "[EXO_TOKEN_1]" in result
    assert mock_bridges["exo"].invocation_count == 1
    assert mock_bridges["llama_rpc"].invocation_count == 0

    # 2. Switch fastest to Accelerate (1.5ms)
    mock_bridges["accelerate"].simulated_ttft_ms = 1.5
    mock_bridges["accelerate"].latency_ms = 1.5
    await auto_router.poller.poll_all_engines()
    assert auto_router.get_effective_engine() == "accelerate"

    for b in mock_bridges.values():
        b.invocation_count = 0

    result2 = await auto_router.process_user_input("Optimize Metal shader")
    assert "[ACCELERATE_TOKEN_1]" in result2
    assert mock_bridges["accelerate"].invocation_count == 1
    assert mock_bridges["exo"].invocation_count == 0


@pytest.mark.asyncio
async def test_auto_mode_stream_generate_token_dispatch(mock_bridges, auto_router):
    """Verify auto mode stream_generate yields tokens from fastest backend."""
    mock_bridges["exo"].simulated_ttft_ms = 5.0
    mock_bridges["exo"].latency_ms = 5.0
    await auto_router.poller.poll_all_engines()

    tokens = []
    async for token in auto_router.stream_generate("Stream generation test"):
        tokens.append(token)

    assert len(tokens) == 2
    assert tokens[0] == "[EXO_TOKEN_1]"
    assert tokens[1] == " [EXO_TOKEN_2]"


# ============================================================================
# 3. HUD STATUS BADGE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_auto_mode_hud_status_badge(mock_bridges, auto_router):
    """Verify get_status_badge format [AUTO (ENGINE): ACTIVE] across dynamic transitions."""
    assert auto_router.active_engine == "auto"

    # Exo fastest -> [AUTO (EXO): ACTIVE]
    mock_bridges["exo"].simulated_ttft_ms = 5.0
    mock_bridges["exo"].latency_ms = 5.0
    await auto_router.poller.poll_all_engines()
    assert auto_router.get_status_badge() == "[AUTO (EXO): ACTIVE]"

    # Llama.cpp fastest -> [AUTO (LLAMA.CPP): ACTIVE]
    mock_bridges["llama_rpc"].simulated_ttft_ms = 2.0
    mock_bridges["llama_rpc"].latency_ms = 2.0
    await auto_router.poller.poll_all_engines()
    assert auto_router.get_status_badge() == "[AUTO (LLAMA.CPP): ACTIVE]"

    # Accelerate fastest -> [AUTO (ACCELERATE): ACTIVE]
    mock_bridges["accelerate"].simulated_ttft_ms = 1.0
    mock_bridges["accelerate"].latency_ms = 1.0
    await auto_router.poller.poll_all_engines()
    assert auto_router.get_status_badge() == "[AUTO (ACCELERATE): ACTIVE]"

    # Petals fastest -> [AUTO (PETALS): ACTIVE]
    mock_bridges["petals"].simulated_ttft_ms = 0.5
    mock_bridges["petals"].latency_ms = 0.5
    await auto_router.poller.poll_all_engines()
    assert auto_router.get_status_badge() == "[AUTO (PETALS): ACTIVE]"


# ============================================================================
# 4. VOICE S2S FORWARDING IN AUTO MODE TEST
# ============================================================================

@pytest.mark.asyncio
async def test_auto_mode_voice_s2s_tts_forwarding(mock_bridges, auto_router):
    """Verify voice prompt routing in auto mode pipes spoken transcript to S2S client."""
    s2s = MockS2SClient()
    auto_router.bind_s2s_client(s2s)
    mock_bridges["exo"].simulated_ttft_ms = 10.0
    mock_bridges["exo"].latency_ms = 10.0
    await auto_router.poller.poll_all_engines()

    result = await auto_router.process_user_input("Explain async coroutines", is_voice=True)
    assert len(result) > 0
    assert len(s2s.synthesized_payloads) >= 1


# ============================================================================
# 5. BACKGROUND POLLER LIFECYCLE & SAFETY TEST
# ============================================================================

@pytest.mark.asyncio
async def test_background_poller_lifecycle_and_task_safety(mock_bridges, dynamic_poller):
    """Verify start and stop lifecycle of background poller without task leaks."""
    dynamic_poller.start_background_polling(interval_sec=0.01)
    assert dynamic_poller.is_running is True

    await asyncio.sleep(0.05)
    metrics = dynamic_poller.get_metrics()
    assert len(metrics) == 4

    await dynamic_poller.stop_background_polling()
    assert dynamic_poller.is_running is False
    assert dynamic_poller._poll_task is None


# ============================================================================
# 6. ENGINE SELECTOR WIDGET AUTO OPTION TEST
# ============================================================================

def test_engine_selector_widget_auto_option():
    """Verify EngineSelectorWidget contains 'auto' option and canonical cycle ordering."""
    assert "auto" in EngineSelectorWidget.ENGINES
    assert EngineSelectorWidget.ENGINES[0] == "auto"
    assert ("🤖 AUTO (Dynamic TTFT)", "auto") in EngineSelectorWidget.ENGINE_OPTIONS

    widget = EngineSelectorWidget(active_engine="auto")
    assert widget.active_engine == "auto"

    # Test cycling: auto -> llama_rpc -> exo -> accelerate -> petals -> gemini -> cloudflare -> julien -> auto
    assert widget.cycle_engine(1) == "llama_rpc"
    assert widget.cycle_engine(1) == "exo"
    assert widget.cycle_engine(1) == "accelerate"
    assert widget.cycle_engine(1) == "petals"
    assert widget.cycle_engine(1) == "gemini"
    assert widget.cycle_engine(1) == "cloudflare"
    assert widget.cycle_engine(1) == "julien"
    assert widget.cycle_engine(1) == "auto"
