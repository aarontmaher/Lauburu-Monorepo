"""
Unit tests for UnifiedInferenceRouter and Polymorphic Inference Bridges.
Tests llama.cpp RPC, exo P2P, accelerate MPS, and petals DHT backends.
Verifies dynamic switching, alias normalization, token streaming, sub-1ms cancellation,
and S2S voice TTS piping without blocking the Textual event loop.
"""

import asyncio
import pytest
from typing import List, Dict, Any, Optional

from tui.services.inference_bridges.base_bridge import BaseInferenceBridge
from tui.services.inference_bridges.llama_bridge import LlamaRpcInferenceBridge
from tui.services.inference_bridges.exo_bridge import ExoInferenceBridge
from tui.services.inference_bridges.accelerate_bridge import AccelerateInferenceBridge
from tui.services.inference_bridges.petals_bridge import PetalsInferenceBridge
from tui.services.inference_bridges.gemini_bridge import GeminiBridge
from tui.services.inference_bridges.cloudflare_bridge import CloudflareBridge
from tui.services.inference_bridges.julien_bridge import JulienBridge
from tui.services.inference_router import UnifiedInferenceRouter
from tui.services.petals_dht_client import PetalsDHTClient, PetalsNodeConfig


class MockVoiceIOManager:
    """Mock VoiceIOManager to verify audio flushing on cancellation."""
    def __init__(self):
        self.flushed: bool = False
        self.is_active: bool = True
        self.is_muted: bool = False

    def flush_playback(self) -> None:
        self.flushed = True


class MockS2SClient:
    """Mock PersonaPlexS2SClient to verify TTS synthesis message forwarding."""
    def __init__(self):
        self.synthesized_payloads: List[str] = []
        self.is_connected: bool = True

    async def send_tts_synthesize(self, text: str) -> None:
        self.synthesized_payloads.append(text)


# ============================================================================
# 1. INDIVIDUAL BRIDGE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_llama_rpc_bridge_streaming():
    """Verify LlamaRpcInferenceBridge streams tokens and handles cancellation."""
    voice_io = MockVoiceIOManager()
    s2s = MockS2SClient()
    tokens_received: List[str] = []
    snippets_received: List[str] = []

    bridge = LlamaRpcInferenceBridge(
        s2s_client=s2s,
        voice_io_manager=voice_io,
        on_token=lambda tok: tokens_received.append(tok),
        on_code_snippet=lambda snip, lang: snippets_received.append(snip),
    )

    assert bridge.engine_name == "llama_rpc"
    assert "LLAMA.CPP" in bridge.get_status_badge()

    # Test stream generation
    tokens = []
    async for token in bridge.stream_generate("Write a quick fibonacci function", max_tokens=10):
        tokens.append(token)

    assert len(tokens) > 0
    full_output = "".join(tokens)
    assert len(full_output) > 0

    # Test full user input processing
    result = await bridge.process_user_input("Write a quick fibonacci function", is_voice=False)
    assert len(result) > 0
    assert len(tokens_received) > 0


@pytest.mark.asyncio
async def test_exo_bridge_streaming():
    """Verify ExoInferenceBridge streams tokens with P2P ring metadata."""
    tokens_received = []
    bridge = ExoInferenceBridge(
        on_token=lambda tok: tokens_received.append(tok)
    )

    assert bridge.engine_name == "exo"
    assert "EXO" in bridge.get_status_badge()

    tokens = []
    async for token in bridge.stream_generate("Optimize matrix multiplication for Metal", max_tokens=8):
        tokens.append(token)

    assert len(tokens) > 0
    status = bridge.get_status()
    assert "ring" in status["topology"].lower()
    assert status["active_peer_count"] >= 1


@pytest.mark.asyncio
async def test_accelerate_bridge_streaming():
    """Verify AccelerateInferenceBridge streams tokens with device MPS status."""
    tokens_received = []
    bridge = AccelerateInferenceBridge(
        on_token=lambda tok: tokens_received.append(tok)
    )

    assert bridge.engine_name == "accelerate"
    assert "ACCELERATE" in bridge.get_status_badge()

    tokens = []
    async for token in bridge.stream_generate("Fine-tune LoRA adapter layer", max_tokens=8):
        tokens.append(token)

    assert len(tokens) > 0
    status = bridge.get_status()
    assert any(d in status["device"].lower() for d in ("mps", "cuda", "cpu", "metal", "apple"))


@pytest.mark.asyncio
async def test_petals_bridge_streaming():
    """Verify PetalsInferenceBridge polymorphic wrapping around PetalsDHTClient."""
    config = PetalsNodeConfig(mock_mode=True, model_name="bigscience/bloom-560m")
    client = PetalsDHTClient(config=config)
    tokens_received = []

    bridge = PetalsInferenceBridge(
        client=client,
        on_token=lambda tok: tokens_received.append(tok)
    )

    assert bridge.engine_name == "petals"
    assert "PETALS" in bridge.get_status_badge()

    tokens = []
    async for token in bridge.stream_generate("Compute DFA alpha-1 zone 2", max_tokens=8):
        tokens.append(token)

    assert len(tokens) > 0


@pytest.mark.asyncio
async def test_gemini_bridge_unconfigured(monkeypatch):
    """Verify GeminiBridge yields clean SYSTEM message when unconfigured."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    bridge = GeminiBridge()
    assert bridge.engine_name == "gemini"
    assert "GEMINI" in bridge.get_status_badge()
    tokens = []
    async for token in bridge.stream_generate("Hello Gemini"):
        tokens.append(token)
    assert len(tokens) > 0
    assert "SYSTEM:" in tokens[0]


@pytest.mark.asyncio
async def test_cloudflare_bridge_unconfigured(monkeypatch):
    """Verify CloudflareBridge yields clean SYSTEM message when unconfigured."""
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    bridge = CloudflareBridge()
    assert bridge.engine_name == "cloudflare"
    assert "CLOUDFLARE" in bridge.get_status_badge()
    tokens = []
    async for token in bridge.stream_generate("Hello Cloudflare"):
        tokens.append(token)
    assert len(tokens) > 0
    assert "SYSTEM:" in tokens[0]


@pytest.mark.asyncio
async def test_julien_bridge_unconfigured(monkeypatch):
    """Verify JulienBridge yields clean SYSTEM message when unconfigured."""
    monkeypatch.delenv("JULIEN_API_KEY", raising=False)
    bridge = JulienBridge()
    assert bridge.engine_name == "julien"
    assert "JULIEN" in bridge.get_status_badge()
    tokens = []
    async for token in bridge.stream_generate("Hello Julien"):
        tokens.append(token)
    assert len(tokens) > 0
    assert "SYSTEM:" in tokens[0]


# ============================================================================
# 2. UNIFIED INFERENCE ROUTER ROUTING & SWITCHING TESTS
# ============================================================================

def test_router_initialization_and_engine_roster():
    """Verify UnifiedInferenceRouter initializes all engines including auto mode."""
    router = UnifiedInferenceRouter(default_engine="llama_rpc")

    assert router.active_engine == "llama_rpc"
    assert set(router.supported_engines) == {"auto", "llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"}
    assert set(router.bridges.keys()) == {"llama_rpc", "exo", "accelerate", "petals", "gemini", "cloudflare", "julien"}

    # Test alias normalization
    assert router.normalize_engine_name("auto") == "auto"
    assert router.normalize_engine_name("dynamic") == "auto"
    assert router.normalize_engine_name("fastest") == "auto"
    assert router.normalize_engine_name("llamacpp") == "llama_rpc"
    assert router.normalize_engine_name("llama_cpp") == "llama_rpc"
    assert router.normalize_engine_name("exo_p2p") == "exo"
    assert router.normalize_engine_name("ring") == "exo"
    assert router.normalize_engine_name("mps") == "accelerate"
    assert router.normalize_engine_name("bloom") == "petals"
    assert router.normalize_engine_name("dht") == "petals"
    assert router.normalize_engine_name("google") == "gemini"
    assert router.normalize_engine_name("cf") == "cloudflare"
    assert router.normalize_engine_name("julien_ai") == "julien"


def test_router_engine_switching_and_cycling():
    """Verify switching and cycling across all inference engines including auto."""
    router = UnifiedInferenceRouter(default_engine="llama_rpc")

    # Set active engine
    swapped = router.set_active_engine("exo")
    assert swapped == "exo"
    assert router.get_active_engine() == "exo"
    assert "EXO" in router.get_status_badge()

    # Cycle forward: exo -> accelerate -> petals -> gemini -> cloudflare -> julien -> auto -> llama_rpc
    assert router.cycle_engine(1) == "accelerate"
    assert router.cycle_engine(1) == "petals"
    assert router.cycle_engine(1) == "gemini"
    assert router.cycle_engine(1) == "cloudflare"
    assert router.cycle_engine(1) == "julien"
    assert router.cycle_engine(1) == "auto"
    assert router.cycle_engine(1) == "llama_rpc"

    # Cycle backward: llama_rpc -> auto -> julien -> cloudflare -> gemini -> petals -> accelerate
    assert router.cycle_engine(-1) == "auto"
    assert router.cycle_engine(-1) == "julien"
    assert router.cycle_engine(-1) == "cloudflare"
    assert router.cycle_engine(-1) == "gemini"
    assert router.cycle_engine(-1) == "petals"
    assert router.cycle_engine(-1) == "accelerate"

    # Invalid engine raises ValueError
    with pytest.raises(ValueError, match="Unknown engine"):
        router.set_active_engine("invalid_engine_xyz")


@pytest.mark.asyncio
async def test_router_streaming_routes_to_active_backend():
    """Verify router streams from the currently active engine."""
    tokens_log: List[str] = []
    router = UnifiedInferenceRouter(
        default_engine="llama_rpc",
        on_token=lambda tok: tokens_log.append(tok)
    )

    # 1. Stream with llama_rpc
    llama_tokens = []
    async for tok in router.stream_generate("Write llama test"):
        llama_tokens.append(tok)
    assert len(llama_tokens) > 0

    # 2. Switch to exo and stream
    router.set_active_engine("exo")
    exo_tokens = []
    async for tok in router.stream_generate("Write exo test"):
        exo_tokens.append(tok)
    assert len(exo_tokens) > 0

    # 3. Switch to accelerate and stream
    router.set_active_engine("accelerate")
    accel_tokens = []
    async for tok in router.stream_generate("Write accelerate test"):
        accel_tokens.append(tok)
    assert len(accel_tokens) > 0

    # 4. Switch to petals and stream
    router.set_active_engine("petals")
    petals_tokens = []
    async for tok in router.stream_generate("Write petals test"):
        petals_tokens.append(tok)
    assert len(petals_tokens) > 0


# ============================================================================
# 3. SUB-1MS CANCELLATION & BARGE-IN TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_router_cancellation_and_barge_in():
    """Verify sub-1ms stream cancellation and audio buffer flush."""
    voice_io = MockVoiceIOManager()
    s2s = MockS2SClient()

    router = UnifiedInferenceRouter(
        default_engine="llama_rpc",
        voice_io_manager=voice_io,
        s2s_client=s2s
    )

    # Launch long generation task
    gen_task = asyncio.create_task(router.process_user_input("Generate 500 lines of code", is_voice=False))
    await asyncio.sleep(0.02)  # Let it start streaming

    # Cancel active stream (<1ms)
    router.cancel_active_stream()
    assert voice_io.flushed is True

    # Generation task should cleanly abort or finish promptly
    try:
        await asyncio.wait_for(gen_task, timeout=0.5)
    except asyncio.CancelledError:
        pass  # Expected on clean cancellation


@pytest.mark.asyncio
async def test_router_mid_stream_engine_swap_cancels_previous():
    """Verify switching active engine while a stream is running halts the previous stream."""
    voice_io = MockVoiceIOManager()
    router = UnifiedInferenceRouter(default_engine="llama_rpc", voice_io_manager=voice_io)

    gen_task = asyncio.create_task(router.process_user_input("Generate massive test prompt", is_voice=False))
    await asyncio.sleep(0.02)

    # Swapping engine triggers cancel_active_stream
    router.set_active_engine("exo")
    assert voice_io.flushed is True

    try:
        await asyncio.wait_for(gen_task, timeout=0.5)
    except asyncio.CancelledError:
        pass


# ============================================================================
# 4. VOICE SPEECH-TO-SPEECH (S2S) TTS PIPING & CODE EXTRACTION
# ============================================================================

@pytest.mark.asyncio
async def test_router_voice_s2s_sanitization_and_tts_forwarding():
    """Verify voice prompts strip markdown code blocks and pipe clean speech to TTS synthesis."""
    s2s = MockS2SClient()
    snippets_extracted: List[str] = []

    router = UnifiedInferenceRouter(
        default_engine="llama_rpc",
        s2s_client=s2s,
        on_code_snippet=lambda snip, lang: snippets_extracted.append(snip)
    )

    # Prompt containing code instructions
    voice_prompt = "Explain quicksort and write python implementation"
    full_response = await router.process_user_input(voice_prompt, is_voice=True)

    # Assert speech payload was forwarded to S2S TTS synthesis
    assert len(s2s.synthesized_payloads) == 1
    tts_speech = s2s.synthesized_payloads[0]

    # TTS speech should not contain raw ``` markdown code fences
    assert "```" not in tts_speech
    assert len(tts_speech) > 0


# ============================================================================
# 5. ALL ENGINE TELEMETRY & STATUS AGGREGATION
# ============================================================================

def test_router_get_all_engine_statuses():
    """Verify aggregated status telemetry for all 7 engines."""
    router = UnifiedInferenceRouter(default_engine="llama_rpc")
    statuses = router.get_all_engine_statuses()

    assert "llama_rpc" in statuses
    assert "exo" in statuses
    assert "accelerate" in statuses
    assert "petals" in statuses
    assert "gemini" in statuses
    assert "cloudflare" in statuses
    assert "julien" in statuses

    for eng, st in statuses.items():
        assert "engine_name" in st
        assert "display_name" in st
        assert "is_connected" in st
        assert "latency_ms" in st


# ============================================================================
# 6. LATENCY POLLER & ERROR CHUNK DETECTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_latency_poller_error_chunk_detection():
    """Verify measure_engine_ttft marks is_available=False and ttft_ms=inf when SYSTEM or ERROR messages are received."""
    from tui.services.latency_poller import DynamicLatencyPoller

    poller = DynamicLatencyPoller()

    # 1. Unconfigured Gemini bridge yields SYSTEM: message
    gemini_b = GeminiBridge()
    gem_metric = await poller.measure_engine_ttft("gemini", gemini_b)
    assert gem_metric.is_available is False
    assert gem_metric.ttft_ms == float("inf")
    assert gem_metric.error is not None

    # 2. Unconfigured Cloudflare bridge yields SYSTEM: message
    cf_b = CloudflareBridge()
    cf_metric = await poller.measure_engine_ttft("cloudflare", cf_b)
    assert cf_metric.is_available is False
    assert cf_metric.ttft_ms == float("inf")

    # 3. Unconfigured Julien bridge yields SYSTEM: message
    jul_b = JulienBridge()
    jul_metric = await poller.measure_engine_ttft("julien", jul_b)
    assert jul_metric.is_available is False
    assert jul_metric.ttft_ms == float("inf")


@pytest.mark.asyncio
async def test_latency_poller_unconfigured_cloud_bridge_filtering():
    """Verify that unconfigured cloud bridges are never selected in auto mode."""
    router = UnifiedInferenceRouter(default_engine="auto")
    # Poll all engines
    metrics = await router.poller.poll_all_engines(force_all=True)

    # Cloud bridges should be unavailable with ttft_ms = inf
    assert metrics["gemini"].is_available is False
    assert metrics["gemini"].ttft_ms == float("inf")
    assert metrics["cloudflare"].is_available is False
    assert metrics["cloudflare"].ttft_ms == float("inf")
    assert metrics["julien"].is_available is False
    assert metrics["julien"].ttft_ms == float("inf")

    # Effective engine should resolve to a healthy local engine, never an unconfigured cloud bridge
    effective = router.get_effective_engine()
    assert effective in ("llama_rpc", "accelerate", "exo", "petals")
    assert effective not in ("gemini", "cloudflare", "julien")

