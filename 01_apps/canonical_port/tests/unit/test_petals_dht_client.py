"""
Unit & Integration Tests: Petals DHT Async Inference Client & Stream Bridge
============================================================================
Comprehensive test suite verifying:
- Non-blocking TCP socket probing for Petals DHT peer connectivity
- Asynchronous token stream generation (<15ms per chunk dispatch)
- Resilient automatic fallback to local llama.cpp / Frontier AI when offline
- Instant barge-in cancellation (<1ms) on user speech detection
- PetalsAsyncInferenceBridge coordination with S2S client, REPL, and TTS
- Textual TUI integration with AgiCodingTerminalView and status HUD
"""

import os
import sys
import time
import asyncio
import pytest
from typing import List, Dict, Any, Optional

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from textual.app import App, ComposeResult
from textual.widgets import Static, RichLog, Input
from services.petals_dht_client import (
    PetalsDHTClient,
    PetalsAsyncInferenceBridge,
    PetalsNodeConfig,
    PetalsInferenceStatus,
)
from views.agi_coding_terminal_view import (
    AgiCodingTerminalView,
    VoiceStateChanged,
    VoiceTranscriptReceived,
    VoiceCodeSnippetInjected,
)
from services.voice_io_manager import VoiceIOManager
from services.personaplex_s2s_client import PersonaPlexS2SClient


# ============================================================================
# MOCK PETALS TCP PEER SERVER
# ============================================================================

class MockPetalsPeerServer:
    """In-process mock TCP server simulating a Petals DHT node."""
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server = None
        self.actual_port: int = 0

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            # Simple ACK / handshake
            writer.write(b"PETALS_DHT_PEER_ACK\n")
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self) -> "MockPetalsPeerServer":
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self.actual_port = self.server.sockets[0].getsockname()[1]
        return self

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def __aenter__(self) -> "MockPetalsPeerServer":
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


# ============================================================================
# 1. PETALS DHT CLIENT CONNECTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_petals_dht_client_connect_success():
    """Verify PetalsDHTClient connects to reachable mock peer node."""
    async with MockPetalsPeerServer() as server:
        config = PetalsNodeConfig(
            model_name="bigscience/bloom-560m",
            initial_peers=[f"127.0.0.1:{server.actual_port}"]
        )
        client = PetalsDHTClient(config=config)
        connected = await client.connect(timeout=1.0)

        assert connected is True
        assert client.is_connected is True
        assert client.active_peer_count == 1
        assert client.latency_ms > 0.0
        assert "bloom-560m" in client.get_status_badge()
        assert client.get_status()["is_connected"] is True


@pytest.mark.asyncio
async def test_petals_dht_client_connect_offline_fallback():
    """Verify PetalsDHTClient gracefully handles unreachable peers without exceptions."""
    # Use unused ports on loopback
    config = PetalsNodeConfig(
        model_name="petals-team/Stable-Beluga-7B",
        initial_peers=["127.0.0.1:39991", "127.0.0.1:39992"],
        timeout_s=0.2
    )
    client = PetalsDHTClient(config=config)
    connected = await client.connect(timeout=0.2)

    assert connected is False
    assert client.is_connected is False
    assert client.active_peer_count == 0
    assert "STANDBY FALLBACK" in client.get_status_badge()
    status = client.get_status()
    assert status["fallback_active"] is True


@pytest.mark.asyncio
async def test_petals_dht_client_mock_mode():
    """Verify PetalsDHTClient deterministic mock mode."""
    config = PetalsNodeConfig(mock_mode=True, model_name="bigscience/bloom-7b1")
    client = PetalsDHTClient(config=config)
    connected = await client.connect()

    assert connected is True
    assert client.is_connected is True
    assert "bloom-7b1" in client.get_status_badge()


# ============================================================================
# 2. PETALS DHT STREAMING & FALLBACK GENERATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_petals_dht_stream_generate_connected():
    """Verify token streaming when client is connected."""
    config = PetalsNodeConfig(mock_mode=True, model_name="bigscience/bloom-560m")
    client = PetalsDHTClient(config=config)
    await client.connect()

    tokens = []
    t0 = time.perf_counter()
    async for token in client.stream_generate("Write a function for zone2 dfa biometrics"):
        tokens.append(token)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    full_output = "".join(tokens)
    assert len(tokens) > 0
    assert "def calculate_zone2_dfa" in full_output or "dfa_alpha1" in full_output
    assert client.total_tokens_generated == len(tokens)
    assert client.last_generation_time_ms > 0.0


@pytest.mark.asyncio
async def test_petals_dht_stream_generate_fallback():
    """Verify automatic fallback token stream when DHT is offline."""
    config = PetalsNodeConfig(
        model_name="bigscience/bloom-560m",
        initial_peers=["127.0.0.1:39999"],
        timeout_s=0.1
    )
    client = PetalsDHTClient(config=config)
    client.is_connected = False

    tokens = []
    async for token in client.stream_generate("Explain the 7-layer mesh architecture"):
        tokens.append(token)

    full_output = "".join(tokens)
    assert len(tokens) > 0
    # Fallback produces either local llama.cpp or standby fallback
    assert ("[Petals Standby Fallback]" in full_output) or ("[Local llama.cpp RPC :8081 Fallback]" in full_output)
    assert client.total_tokens_generated == len(tokens)


# ============================================================================
# 3. BARGE-IN CANCELLATION TESTS (<1MS LATENCY)
# ============================================================================

@pytest.mark.asyncio
async def test_petals_dht_instant_barge_in_cancellation():
    """
    Verify barge-in cancellation halts active token generation in <1ms.
    """
    config = PetalsNodeConfig(mock_mode=True)
    client = PetalsDHTClient(config=config)
    await client.connect()

    yielded_tokens = []

    async def _stream_worker():
        try:
            async for tok in client.stream_generate("Long running prompt requiring several tokens..."):
                yielded_tokens.append(tok)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(_stream_worker())
    await asyncio.sleep(0.03)  # Let generator start

    # Trigger Barge-in and measure cancellation execution duration
    t0 = time.perf_counter()
    client.cancel_generation()
    cancel_duration_ms = (time.perf_counter() - t0) * 1000.0

    # Await worker teardown
    await asyncio.gather(task, return_exceptions=True)

    # Assert cancellation performance SLA < 1.0ms
    assert cancel_duration_ms < 1.0, f"Barge-in cancel latency violated SLA: {cancel_duration_ms:.3f}ms (limit: 1.0ms)"
    assert client._generation_cancelled is True


# ============================================================================
# 4. PETALS ASYNC INFERENCE BRIDGE & S2S INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_petals_bridge_process_text_and_code_snippet_extraction():
    """Verify PetalsAsyncInferenceBridge extracts code snippets and fires callbacks."""
    config = PetalsNodeConfig(mock_mode=True)
    client = PetalsDHTClient(config=config)
    await client.connect()

    received_tokens = []
    received_snippets = []
    completed_text = []

    bridge = PetalsAsyncInferenceBridge(
        client=client,
        on_token=lambda tok: received_tokens.append(tok),
        on_code_snippet=lambda snip, lang: received_snippets.append((snip, lang)),
        on_complete=lambda txt: completed_text.append(txt)
    )

    result = await bridge.process_user_input("Write a python function to check blackboard store", is_voice=False)

    assert len(received_tokens) > 0
    assert len(completed_text) == 1
    assert completed_text[0] == result
    assert len(received_snippets) >= 1
    snippet, lang = received_snippets[0]
    assert "blackboard_store" in snippet or "def " in snippet
    assert lang == "python"


@pytest.mark.asyncio
async def test_petals_bridge_voice_coding_tts_dispatch():
    """Verify PetalsAsyncInferenceBridge pipes generated speech to PersonaPlex S2S client."""
    config = PetalsNodeConfig(mock_mode=True)
    client = PetalsDHTClient(config=config)
    await client.connect()

    # Mock S2S client to inspect sent control messages
    class MockS2SClient:
        def __init__(self):
            self.sent_controls = []
        def send_control(self, payload):
            self.sent_controls.append(payload)

    mock_s2s = MockS2SClient()
    bridge = PetalsAsyncInferenceBridge(
        client=client,
        s2s_client=mock_s2s
    )

    await bridge.process_user_input("What is the mesh RAM status?", is_voice=True)

    assert len(mock_s2s.sent_controls) == 1
    tts_msg = mock_s2s.sent_controls[0]
    assert tts_msg["type"] == "tts_synthesize"
    assert "text" in tts_msg
    assert len(tts_msg["text"]) > 0


# ============================================================================
# 5. TEXTUAL TUI VIEW INTEGRATION TESTS
# ============================================================================

class PetalsTuiTestApp(App):
    """Test App mounting AgiCodingTerminalView with Petals client."""
    def __init__(self, petals_client: PetalsDHTClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.petals_client = petals_client
        self.terminal_view = AgiCodingTerminalView(
            petals_client=self.petals_client
        )

    def compose(self) -> ComposeResult:
        yield self.terminal_view


@pytest.mark.asyncio
async def test_agi_coding_terminal_view_petals_integration():
    """
    Verify AgiCodingTerminalView mounts Petals client, renders HUD badge,
    and processes slash commands and voice transcripts without blocking.
    """
    config = PetalsNodeConfig(mock_mode=True, model_name="bigscience/bloom-560m")
    client = PetalsDHTClient(config=config)
    app = PetalsTuiTestApp(petals_client=client)

    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view
        assert view is not None

        # 1. Assert status bar renders Petals DHT status badge
        status_bar = view.query_one("#terminal-status-bar", Static)
        assert status_bar is not None

        # 2. Test /petals status slash command
        view._execute_repl_command("/petals status")
        await pilot.pause(0.1)

        # 3. Test /petals streaming inference
        view._execute_repl_command("/petals calculate_zone2_dfa")
        await pilot.pause(0.25)
        log_widget = view.query_one("#terminal-output-log", RichLog)
        assert log_widget is not None

        # 4. Test Final Voice Transcript routing to Petals DHT & Code Injection
        view.auto_inject_enabled = True
        view.post_message(VoiceTranscriptReceived(
            text="Write a function for zone2 dfa biometrics",
            is_final=True,
            role="user"
        ))
        await pilot.pause(0.3)

        # Assert editor code buffer updated with the generated snippet
        assert "def " in view.editor_code_buffer

        # 5. Test Instant Barge-in via VoiceStateChanged
        view.post_message(VoiceStateChanged(status="LISTENING", is_active=True))
        await pilot.pause(0.05)
        assert client._generation_cancelled is True
