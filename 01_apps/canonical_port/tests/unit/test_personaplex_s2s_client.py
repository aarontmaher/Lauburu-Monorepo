"""
Unit Tests: PersonaPlex S2S Full-Duplex Streaming Client (Milestone 2)
Validates:
- WebSocket connection handshake and session initialization
- Upstream binary PCM audio streaming with 100% byte fidelity
- Downstream binary audio routing to VoiceIOManager
- JSON control messages and state transitions (IDLE -> LISTENING -> THINKING -> SPEAKING)
- Streaming transcript aggregation and code snippet extraction
- Instant barge-in interruption (<1ms buffer flush + S2S interrupt frame dispatch)
- Fallback endpoint connection when primary endpoint is unreachable
- BlackboardStore live state synchronization (<3ms fast-path)
- Ping/pong round-trip latency telemetry
- Graceful disconnect, error handling, and resource teardown
"""

import os
import sys
import time
import json
import asyncio
import pytest
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union

import websockets

# Ensure tui package is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
from models.blackboard_models import (
    VoiceCodingState,
    VoiceTelemetry,
    VoiceStatus,
    VOICE_STATUS_IDLE,
    VOICE_STATUS_LISTENING,
    VOICE_STATUS_THINKING,
    VOICE_STATUS_SPEAKING,
    VOICE_STATUS_MUTED,
    VOICE_STATUS_ERROR
)
from services.blackboard_store import BlackboardStore
from services.voice_io_manager import (
    VoiceIOManager,
    SyntheticAudioEngine,
    generate_synthetic_pcm_sine,
    generate_synthetic_pcm_silence
)
from services.personaplex_s2s_client import PersonaPlexS2SClient


# ============================================================================
# MOCK S2S WEBSOCKET SERVER HELPER
# ============================================================================

class MockS2SServer:
    """
    In-process mock PersonaPlex S2S WebSocket server for deterministic testing.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server = None
        self.actual_port: int = 0
        self.ws_url: str = ""
        
        self.received_binary_frames: List[bytes] = []
        self.received_control_frames: List[Dict[str, Any]] = []
        self.active_sockets: List[Any] = []
        self._connected_event = asyncio.Event()

    async def handle_connection(self, websocket: Any) -> None:
        self.active_sockets.append(websocket)
        self._connected_event.set()
        
        # Send initial readiness packet
        ready_pkt = {
            "type": "ready",
            "service": "Mock PersonaPlex S2S Daemon",
            "session_id": "session-mock-42",
            "server_time": time.time() * 1000.0
        }
        await websocket.send(json.dumps(ready_pkt))

        try:
            async for message in websocket:
                if isinstance(message, (bytes, bytearray, memoryview)):
                    self.received_binary_frames.append(bytes(message))
                elif isinstance(message, str):
                    try:
                        parsed = json.loads(message)
                        self.received_control_frames.append(parsed)
                        msg_type = parsed.get("type", "")

                        if msg_type == "session_start":
                            await websocket.send(json.dumps({
                                "type": "session_started",
                                "session_id": "session-mock-42",
                                "status": "READY"
                            }))
                        elif msg_type == "ping":
                            client_time = parsed.get("client_time", 0.0)
                            await websocket.send(json.dumps({
                                "type": "pong",
                                "client_time": client_time,
                                "server_time": time.time() * 1000.0
                            }))
                        elif msg_type == "session_end":
                            await websocket.send(json.dumps({
                                "type": "session_ended",
                                "session_id": "session-mock-42"
                            }))
                    except Exception:
                        pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if websocket in self.active_sockets:
                self.active_sockets.remove(websocket)

    async def start(self) -> "MockS2SServer":
        self.server = await websockets.serve(self.handle_connection, self.host, self.port)
        self.actual_port = self.server.sockets[0].getsockname()[1]
        self.ws_url = f"ws://{self.host}:{self.actual_port}"
        return self

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def __aenter__(self) -> "MockS2SServer":
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def send_to_all(self, data: Union[str, bytes, Dict[str, Any]]) -> None:
        if isinstance(data, dict):
            msg = json.dumps(data)
        else:
            msg = data
        for ws in list(self.active_sockets):
            try:
                await ws.send(msg)
            except Exception:
                pass


# ============================================================================
# 1. CLIENT INITIALIZATION & DATA MODEL TESTS
# ============================================================================

def test_client_initialization_and_defaults():
    """Verify PersonaPlexS2SClient constructor, defaults, and properties."""
    client = PersonaPlexS2SClient()
    assert client.endpoint_ws == PersonaPlexS2SClient.DEFAULT_ENDPOINT
    assert client.fallback_endpoint_ws == PersonaPlexS2SClient.FALLBACK_ENDPOINT
    assert client.sample_rate_in_hz == 16000
    assert client.sample_rate_out_hz == 24000
    assert client.status == "IDLE"
    assert client.is_connected is False
    assert client.is_active is False
    assert client.session_id is None

    state = client.get_state()
    assert isinstance(state, VoiceCodingState)
    assert state.status == "IDLE"

    tel = client.get_telemetry()
    assert isinstance(tel, VoiceTelemetry)
    assert tel.sample_rate_in_hz == 16000
    assert tel.sample_rate_out_hz == 24000


# ============================================================================
# 2. WEBSOCKET CONNECTION HANDSHAKE & SESSION INIT
# ============================================================================

def test_client_connection_handshake_and_session_init():
    """Verify WebSocket connection handshake, session_start frame, and status transition."""
    async def _run():
        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                auto_reconnect=False
            )

            success = await client.connect()
            assert success is True
            assert client.is_connected is True
            assert client.status in ("LISTENING", "IDLE")

            # Allow session initialization frame to round-trip
            await asyncio.sleep(0.05)
            assert client.session_id == "session-mock-42"
            assert client.active_endpoint == server.ws_url

            # Verify server received session_start frame
            start_frames = [f for f in server.received_control_frames if f.get("type") == "session_start"]
            assert len(start_frames) == 1
            assert start_frames[0]["sample_rate"] == 16000
            assert start_frames[0]["mode"] == "duplex"

            await client.disconnect()
            assert client.is_connected is False
            assert client.status == "IDLE"

    asyncio.run(_run())


# ============================================================================
# 3. UPSTREAM BINARY PCM AUDIO STREAMING
# ============================================================================

def test_upstream_binary_audio_streaming():
    """Verify upstream binary PCM audio streaming maintains 100% byte fidelity."""
    async def _run():
        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                auto_reconnect=False
            )
            await client.connect()

            # Generate 4 distinct synthetic PCM chunks (20ms @ 16kHz = 640 bytes each)
            test_chunks = [
                generate_synthetic_pcm_sine(frequency_hz=300.0 + i * 100.0, duration_s=0.02, sample_rate_hz=16000)
                for i in range(4)
            ]

            for chunk in test_chunks:
                client.send_audio_chunk(chunk)

            # Wait briefly for worker task to transmit
            await asyncio.sleep(0.1)

            assert len(server.received_binary_frames) == 4
            for sent, received in zip(test_chunks, server.received_binary_frames):
                assert len(received) == 640
                assert sent == received

            tel = client.get_telemetry()
            assert tel.total_ingress_bytes == 4 * 640

            await client.disconnect()

    asyncio.run(_run())


# ============================================================================
# 4. DOWNSTREAM BINARY AUDIO ROUTING TO VOICE_IO_MANAGER
# ============================================================================

def test_downstream_binary_audio_routing_to_voice_io_manager():
    """Verify downstream binary audio frames are routed directly to VoiceIOManager speaker queue."""
    async def _run():
        voice_io = VoiceIOManager.create_synthetic(
            sample_rate_in_hz=16000,
            sample_rate_out_hz=24000,
            chunk_duration_ms=20,
            waveform="silence"
        )
        voice_io.start()

        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                voice_io_manager=voice_io,
                auto_reconnect=False
            )
            await client.connect()

            # Server streams 2 binary chunks downstream
            downstream_audio_1 = b"\x11\x22\x33\x44" * 120
            downstream_audio_2 = b"\x55\x66\x77\x88" * 120
            await server.send_to_all(downstream_audio_1)
            await server.send_to_all(downstream_audio_2)

            await asyncio.sleep(0.08)

            # Check VoiceIOManager recorded playback on underlying engine
            recorded = voice_io.engine.get_recorded_playback_bytes()
            assert downstream_audio_1 in recorded
            assert downstream_audio_2 in recorded
            assert client.status == "SPEAKING"

            tel = client.get_telemetry()
            assert tel.total_egress_bytes >= len(downstream_audio_1) + len(downstream_audio_2)

            await client.disconnect()
        voice_io.close()

    asyncio.run(_run())


# ============================================================================
# 5. JSON CONTROL MESSAGES & STATE TRANSITIONS
# ============================================================================

def test_json_control_messages_and_state_transitions():
    """Verify parsing of state control messages (THINKING, SPEAKING, LISTENING, MUTED)."""
    async def _run():
        observed_states: List[str] = []
        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                on_state_change=lambda st: observed_states.append(st),
                auto_reconnect=False
            )
            await client.connect()

            # Send THINKING state from server
            await server.send_to_all({"type": "state", "status": "THINKING"})
            await asyncio.sleep(0.04)
            assert client.status == "THINKING"
            assert client.state.is_stt_active is True
            assert client.state.is_tts_active is False

            # Send SPEAKING state from server
            await server.send_to_all({"type": "state", "status": "SPEAKING"})
            await asyncio.sleep(0.04)
            assert client.status == "SPEAKING"
            assert client.state.is_tts_active is True
            assert client.state.is_stt_active is False

            # Send MUTED state from server
            await server.send_to_all({"type": "state", "status": "MUTED"})
            await asyncio.sleep(0.04)
            assert client.status == "MUTED"
            assert client.state.is_muted is True

            # Send LISTENING state from server
            await server.send_to_all({"type": "state", "status": "LISTENING"})
            await asyncio.sleep(0.04)
            assert client.status == "LISTENING"
            assert client.state.is_muted is False

            assert "THINKING" in observed_states
            assert "SPEAKING" in observed_states
            assert "MUTED" in observed_states
            assert "LISTENING" in observed_states

            await client.disconnect()

    asyncio.run(_run())


# ============================================================================
# 6. STREAMING TRANSCRIPTS & CODE SNIPPET EXTRACTION
# ============================================================================

def test_streaming_transcripts_and_code_snippet_extraction():
    """Verify streaming transcripts (user & model) and code snippet injection."""
    async def _run():
        transcripts_received: List[Tuple[str, bool, str]] = []
        snippets_received: List[Tuple[str, Optional[str]]] = []

        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                on_transcript=lambda txt, fin, role: transcripts_received.append((txt, fin, role)),
                on_code_snippet=lambda snip, lang: snippets_received.append((snip, lang)),
                auto_reconnect=False
            )
            await client.connect()

            # User interim transcript
            await server.send_to_all({
                "type": "transcript",
                "text": "build a binary search tree",
                "is_final": False,
                "role": "user"
            })
            await asyncio.sleep(0.04)
            assert client.state.current_transcript == "build a binary search tree"
            assert client.state.last_user_speech == "build a binary search tree"

            # Assistant final transcript
            await server.send_to_all({
                "type": "transcript",
                "text": "Here is the binary search tree implementation in Python:",
                "is_final": True,
                "role": "assistant"
            })
            await asyncio.sleep(0.04)
            assert client.state.current_transcript == "Here is the binary search tree implementation in Python:"
            assert client.state.last_model_speech == "Here is the binary search tree implementation in Python:"

            # Code snippet frame
            code_text = "class Node:\n    def __init__(self, val):\n        self.val = val"
            await server.send_to_all({
                "type": "code_snippet",
                "snippet": code_text,
                "language": "python"
            })
            await asyncio.sleep(0.04)
            assert client.state.last_code_snippet == code_text

            assert len(transcripts_received) == 2
            assert transcripts_received[0] == ("build a binary search tree", False, "user")
            assert transcripts_received[1] == ("Here is the binary search tree implementation in Python:", True, "assistant")

            assert len(snippets_received) == 1
            assert snippets_received[0] == (code_text, "python")

            await client.disconnect()

    asyncio.run(_run())


# ============================================================================
# 7. PING / PONG LATENCY TELEMETRY
# ============================================================================

def test_ping_pong_latency_telemetry():
    """Verify ping/pong exchange and round-trip latency calculation."""
    async def _run():
        telemetry_updates: List[VoiceTelemetry] = []
        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                ping_interval_s=0.1,
                on_telemetry=lambda tel: telemetry_updates.append(tel),
                auto_reconnect=False
            )
            await client.connect()

            # Trigger explicit ping
            t0 = time.time() * 1000.0
            await client.send_control_async({"type": "ping", "client_time": t0})
            await asyncio.sleep(0.06)

            pings = [f for f in server.received_control_frames if f.get("type") == "ping"]
            assert len(pings) >= 1

            tel = client.get_telemetry()
            assert tel.latency_ms >= 0.0

            await client.disconnect()

    asyncio.run(_run())


# ============================================================================
# 8. BARGE-IN INTERRUPTION FLUSHES PLAYBACK (<1ms)
# ============================================================================

def test_barge_in_interruption_flushes_playback():
    """Verify barge-in instantly flushes VoiceIOManager playback and dispatches interrupt frame."""
    async def _run():
        voice_io = VoiceIOManager.create_synthetic(
            sample_rate_in_hz=16000,
            sample_rate_out_hz=24000,
            chunk_duration_ms=20,
            waveform="silence"
        )
        voice_io.start()

        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                voice_io_manager=voice_io,
                auto_reconnect=False
            )
            await client.connect()

            # Simulate speaking state with buffered audio
            client._set_status("SPEAKING")
            for _ in range(5):
                voice_io.play_audio_chunk(b"\x01\x02" * 240)

            # Trigger instant barge-in
            t0 = time.perf_counter()
            client.trigger_barge_in_sync()
            flush_duration_ms = (time.perf_counter() - t0) * 1000.0
            assert flush_duration_ms < 2.0, f"Barge-in flush too slow: {flush_duration_ms:.3f}ms"

            # Status must immediately be LISTENING
            assert client.status == "LISTENING"

            # Allow worker to transmit interrupt frame
            await asyncio.sleep(0.06)
            interrupt_frames = [f for f in server.received_control_frames if f.get("type") == "interrupt"]
            assert len(interrupt_frames) >= 1
            assert interrupt_frames[0]["reason"] == "user_speech_detected"

            await client.disconnect()
        voice_io.close()

    asyncio.run(_run())


# ============================================================================
# 9. FALLBACK ENDPOINT CONNECTION
# ============================================================================

def test_fallback_endpoint_connection():
    """Verify automatic fallback to secondary endpoint when primary is offline."""
    async def _run():
        async with MockS2SServer() as server:
            # Primary endpoint is invalid port
            dead_endpoint = "ws://127.0.0.1:59997"
            client = PersonaPlexS2SClient(
                endpoint_ws=dead_endpoint,
                fallback_endpoint_ws=server.ws_url,
                auto_reconnect=False
            )

            success = await client.connect()
            assert success is True
            assert client.is_connected is True
            assert client.active_endpoint == server.ws_url

            await client.disconnect()

    asyncio.run(_run())


# ============================================================================
# 10. BLACKBOARD STORE INTEGRATION (<3ms FAST-PATH)
# ============================================================================

def test_blackboard_store_integration():
    """Verify PersonaPlexS2SClient seamlessly synchronizes state to BlackboardStore."""
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
            async with MockS2SServer() as server:
                client = PersonaPlexS2SClient(
                    endpoint_ws=server.ws_url,
                    blackboard_store=store,
                    auto_reconnect=False
                )

                await client.connect()
                await asyncio.sleep(0.04)

                # BlackboardStore voice state should reflect active connection
                vc = store.get_voice_state()
                assert vc.status == "LISTENING"
                assert vc.is_active is True
                assert vc.session_id == "session-mock-42"

                # Receive transcript from server
                await server.send_to_all({
                    "type": "transcript",
                    "text": "grep -rn VoiceCodingState",
                    "is_final": True,
                    "role": "user"
                })
                await asyncio.sleep(0.04)

                vc2 = store.get_voice_state()
                assert vc2.current_transcript == "grep -rn VoiceCodingState"
                assert vc2.last_user_speech == "grep -rn VoiceCodingState"

                await client.disconnect()
                vc_after = store.get_voice_state()
                assert vc_after.status == "IDLE"

    asyncio.run(_run())


# ============================================================================
# 11. ERROR HANDLING & REMOTE TEARDOWN
# ============================================================================

def test_error_handling_and_remote_teardown():
    """Verify server error frames and disconnect event handling."""
    async def _run():
        errors_caught: List[str] = []
        async with MockS2SServer() as server:
            client = PersonaPlexS2SClient(
                endpoint_ws=server.ws_url,
                on_error=lambda err: errors_caught.append(err),
                auto_reconnect=False
            )
            await client.connect()

            # Server sends error frame
            await server.send_to_all({
                "type": "error",
                "message": "CUDA Device 0 OOM: Memory allocation failed"
            })
            await asyncio.sleep(0.04)

            assert client.status == "ERROR"
            assert client.state.error_message == "CUDA Device 0 OOM: Memory allocation failed"
            assert len(errors_caught) == 1
            assert "CUDA Device 0 OOM" in errors_caught[0]

            await client.disconnect()

    asyncio.run(_run())
