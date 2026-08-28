"""
Tier 1 PersonaPlex S2S Full-Duplex Streaming WebSocket Client
Version: 1.0.0-CANONICAL

Provides ultra-low latency, bidirectional speech-to-speech (S2S) streaming between
the Canonical Port TUI and the Tier 1 PersonaPlex / Voice Bridge server:
- Dual-plane framing: Binary PCM audio (Opcode 0x02) + JSON control messages (Opcode 0x01)
- Async WebSocket connection lifecycle with automatic fallback and auto-reconnect
- Upstream audio streaming from VoiceIOManager with bounded queues
- Downstream audio chunk routing directly to speaker playback
- Instant barge-in interruption (<1ms buffer flush + S2S interrupt frame dispatch)
- Real-time state synchronization across IDLE, LISTENING, THINKING, SPEAKING, MUTED, ERROR
- Streaming transcript aggregation and hands-free code snippet extraction
- Round-trip ping/pong latency telemetry calculation
- Zero-mock / Zero-simulated data compliance (Rule #0)
"""

import os
import sys
import time
import json
import uuid
import logging
import asyncio
import threading
from typing import Optional, Dict, Any, Callable, List, Tuple, Union

try:
    import websockets
    # websockets protocol
except ImportError:
    websockets = None
    WebSocketClientProtocol = Any

# Ensure models can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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

logger = logging.getLogger("PersonaPlexS2SClient")


class PersonaPlexS2SClient:
    """
    Tier 1 PersonaPlex S2S WebSocket Client.
    Manages full-duplex binary audio streaming and JSON control messaging
    with Tier 1 Voice Bridge and inference daemons.
    """

    DEFAULT_ENDPOINT = "ws://127.0.0.1:8765/ws/voice"
    FALLBACK_ENDPOINT = "ws://127.0.0.1:8085/v1/audio/duplex"

    def __init__(
        self,
        endpoint_ws: str = DEFAULT_ENDPOINT,
        fallback_endpoint_ws: Optional[str] = FALLBACK_ENDPOINT,
        sample_rate_in_hz: int = 16000,
        sample_rate_out_hz: int = 24000,
        channels: int = 1,
        mime_type: str = "audio/pcm",
        time_slice_ms: int = 150,
        auto_reconnect: bool = True,
        reconnect_interval_s: float = 2.0,
        max_reconnect_attempts: int = 5,
        ping_interval_s: float = 10.0,
        blackboard_store: Optional[Any] = None,
        voice_io_manager: Optional[Any] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
        on_transcript: Optional[Callable[[str, bool, str], None]] = None,
        on_code_snippet: Optional[Callable[[str, Optional[str]], None]] = None,
        on_telemetry: Optional[Callable[[VoiceTelemetry], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.endpoint_ws = endpoint_ws
        self.fallback_endpoint_ws = fallback_endpoint_ws
        self.sample_rate_in_hz = sample_rate_in_hz
        self.sample_rate_out_hz = sample_rate_out_hz
        self.channels = channels
        self.mime_type = mime_type
        self.time_slice_ms = time_slice_ms
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval_s = reconnect_interval_s
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval_s = ping_interval_s

        self.blackboard_store = blackboard_store
        self.voice_io_manager = voice_io_manager

        # Event callbacks
        self.on_state_change = on_state_change
        self.on_transcript = on_transcript
        self.on_code_snippet = on_code_snippet
        self.on_telemetry = on_telemetry
        self.on_error = on_error

        # Internal state model
        self.state = VoiceCodingState(
            status=VOICE_STATUS_IDLE,
            is_active=False,
            endpoint_ws=endpoint_ws,
            telemetry=VoiceTelemetry(
                sample_rate_in_hz=sample_rate_in_hz,
                sample_rate_out_hz=sample_rate_out_hz
            )
        )

        # Connection & Concurrency primitives
        self._ws: Optional[Any] = None
        self._active_endpoint: Optional[str] = None
        self._session_id: Optional[str] = None
        self._is_connected: bool = False
        self._is_running: bool = False
        self._reconnect_attempts: int = 0

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: List[asyncio.Task] = []
        self._reconnect_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Bounded queues to prevent unbounded memory growth during latency spikes
        self._upstream_audio_queue: Optional[asyncio.Queue[bytes]] = None
        self._upstream_control_queue: Optional[asyncio.Queue[Dict[str, Any]]] = None

        # Bind VoiceIOManager if provided at initialization
        if self.voice_io_manager is not None:
            self.bind_voice_io_manager(self.voice_io_manager)

    # ------------------------------------------------------------------------
    # VoiceIOManager Binding & Intercepts
    # ------------------------------------------------------------------------

    def bind_voice_io_manager(self, voice_io_manager: Any) -> None:
        """
        Bind VoiceIOManager callbacks to stream ingress audio and detect VAD events.
        """
        self.voice_io_manager = voice_io_manager
        voice_io_manager.on_audio_chunk = self._on_voice_io_audio_chunk
        voice_io_manager.on_vad_state_changed = self._on_voice_io_vad_changed
        logger.info("VoiceIOManager bound to PersonaPlexS2SClient.")

    def _on_voice_io_audio_chunk(self, pcm_bytes: bytes, rms: float, is_speech: bool) -> None:
        """Callback invoked on background audio capture thread."""
        if not self._is_connected or not pcm_bytes:
            return

        # Check for barge-in while model is outputting audio
        if is_speech and self.state.status == VOICE_STATUS_SPEAKING:
            self.trigger_barge_in_sync()

        self.send_audio_chunk(pcm_bytes)

    def _on_voice_io_vad_changed(self, is_speech: bool) -> None:
        """Callback invoked on VAD state change."""
        if is_speech:
            if self.state.status == VOICE_STATUS_SPEAKING:
                self.trigger_barge_in_sync()
            elif self.state.status == VOICE_STATUS_IDLE and self._is_connected:
                self._set_status(VOICE_STATUS_LISTENING)
        else:
            # Silence detected
            pass

    # ------------------------------------------------------------------------
    # State & Status Management
    # ------------------------------------------------------------------------

    @property
    def status(self) -> str:
        """Current voice coding operational status string."""
        return self.state.status

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket connection is actively established."""
        return self._is_connected

    @property
    def is_active(self) -> bool:
        """Whether voice coding session is active."""
        return self.state.is_active

    @property
    def session_id(self) -> Optional[str]:
        """Active PersonaPlex session ID."""
        return self._session_id

    @property
    def active_endpoint(self) -> Optional[str]:
        """Currently connected WebSocket URI."""
        return self._active_endpoint

    def get_state(self) -> VoiceCodingState:
        """Return current VoiceCodingState snapshot."""
        return self.state

    def get_telemetry(self) -> VoiceTelemetry:
        """Return current VoiceTelemetry snapshot."""
        if self.voice_io_manager:
            mgr_tel = self.voice_io_manager.get_telemetry()
            self.state.telemetry.input_db = mgr_tel.input_db
            self.state.telemetry.output_db = mgr_tel.output_db
            self.state.telemetry.rms_energy = mgr_tel.rms_energy
            self.state.telemetry.vad_active = mgr_tel.vad_active
            self.state.telemetry.speech_detected = mgr_tel.speech_detected
            self.state.telemetry.total_ingress_bytes = mgr_tel.total_ingress_bytes
            self.state.telemetry.total_egress_bytes = mgr_tel.total_egress_bytes
            self.state.telemetry.jitter_ms = mgr_tel.jitter_ms
        return self.state.telemetry

    def _set_status(self, new_status: str) -> None:
        """Internal thread-safe status updater with callback and blackboard sync."""
        normalized = new_status.strip().upper()
        if self.state.status == normalized:
            return

        self.state.status = normalized
        self.state.is_stt_active = (normalized in (VOICE_STATUS_LISTENING, VOICE_STATUS_THINKING))
        self.state.is_tts_active = (normalized == VOICE_STATUS_SPEAKING)
        self.state.is_active = (normalized != VOICE_STATUS_IDLE and normalized != VOICE_STATUS_ERROR)

        if normalized == VOICE_STATUS_MUTED:
            self.state.is_muted = True
        elif normalized in (VOICE_STATUS_IDLE, VOICE_STATUS_LISTENING, VOICE_STATUS_SPEAKING, VOICE_STATUS_THINKING):
            self.state.is_muted = False

        # Sync with BlackboardStore if present
        if self.blackboard_store is not None:
            try:
                self.blackboard_store.update_voice_state(
                    self.state.status,
                    is_active=self.state.is_active,
                    is_stt_active=self.state.is_stt_active,
                    is_tts_active=self.state.is_tts_active,
                    is_muted=self.state.is_muted,
                    endpoint_ws=self._active_endpoint or self.endpoint_ws,
                    session_id=self._session_id,
                    current_transcript=self.state.current_transcript,
                    last_code_snippet=self.state.last_code_snippet,
                    last_user_speech=self.state.last_user_speech,
                    last_model_speech=self.state.last_model_speech,
                    error_message=self.state.error_message
                )
            except Exception as e:
                logger.debug(f"Error syncing with BlackboardStore: {e}")

        # Fire state change callback
        if self.on_state_change is not None:
            try:
                self.on_state_change(self.state.status)
            except Exception as e:
                logger.debug(f"on_state_change callback error: {e}")

    # ------------------------------------------------------------------------
    # WebSocket Lifecycle Management
    # ------------------------------------------------------------------------

    async def connect(self, endpoint: Optional[str] = None) -> bool:
        """
        Connect to the PersonaPlex S2S WebSocket server with automatic fallback.
        Starts background sender, receiver, and ping workers.
        """
        if websockets is None:
            err = "websockets library not installed in Python environment."
            logger.error(err)
            self._handle_error(err)
            return False

        async with self._lock:
            if self._is_connected:
                return True

            self._loop = asyncio.get_running_loop()
            self._upstream_audio_queue = asyncio.Queue(maxsize=1000)
            self._upstream_control_queue = asyncio.Queue(maxsize=200)

            endpoints_to_try = []
            if endpoint:
                endpoints_to_try.append(endpoint)
            else:
                endpoints_to_try.append(self.endpoint_ws)
                if self.fallback_endpoint_ws and self.fallback_endpoint_ws != self.endpoint_ws:
                    endpoints_to_try.append(self.fallback_endpoint_ws)

            connected = False
            last_conn_err: Optional[Exception] = None

            for ep in endpoints_to_try:
                try:
                    logger.info(f"Attempting PersonaPlex S2S connection to {ep}...")
                    self._ws = await websockets.connect(
                        ep,
                        ping_interval=None, # We govern custom application-level ping/pong
                        close_timeout=2.0
                    )
                    self._active_endpoint = ep
                    self.state.endpoint_ws = ep
                    connected = True
                    logger.info(f"Successfully connected to PersonaPlex S2S at {ep}")
                    break
                except Exception as e:
                    last_conn_err = e
                    logger.warning(f"Failed connection to {ep}: {e}")

            if not connected:
                err_msg = f"Failed to connect to any S2S endpoint ({endpoints_to_try}): {last_conn_err}"
                logger.error(err_msg)
                self._handle_error(err_msg)
                if self.auto_reconnect and self._is_running:
                    self._schedule_reconnect()
                return False

            self._is_connected = True
            self._is_running = True
            self._reconnect_attempts = 0
            self.state.error_message = None

            # Spawn background workers
            self._tasks = [
                asyncio.create_task(self._rx_worker(), name="PersonaPlex_RX"),
                asyncio.create_task(self._tx_audio_worker(), name="PersonaPlex_TX_Audio"),
                asyncio.create_task(self._tx_control_worker(), name="PersonaPlex_TX_Control"),
                asyncio.create_task(self._ping_worker(), name="PersonaPlex_Ping")
            ]

            # Send session_start handshake
            session_init_payload = {
                "type": "session_start",
                "sample_rate": self.sample_rate_in_hz,
                "sampleRate": self.sample_rate_in_hz,
                "channels": self.channels,
                "mime_type": self.mime_type,
                "mimeType": self.mime_type,
                "time_slice_ms": self.time_slice_ms,
                "timeSliceMs": self.time_slice_ms,
                "mode": "duplex"
            }
            await self.send_control_async(session_init_payload)

            self._set_status(VOICE_STATUS_LISTENING)
            return True

    async def disconnect(self) -> None:
        """
        Gracefully disconnect the WebSocket session and cancel all background tasks.
        """
        self._is_running = False

        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self._is_connected and self._ws is not None:
            try:
                # Send session_end frame
                end_frame = json.dumps({
                    "type": "session_end",
                    "session_id": self._session_id or ""
                })
                await asyncio.wait_for(self._ws.send(end_frame), timeout=0.5)
            except Exception:
                pass

            try:
                await asyncio.wait_for(self._ws.close(), timeout=1.0)
            except Exception:
                pass

        self._is_connected = False
        self._ws = None

        # Cancel all background worker tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._tasks.clear()

        # Clear remaining queues
        if self._upstream_audio_queue is not None:
            while not self._upstream_audio_queue.empty():
                try:
                    self._upstream_audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        if self._upstream_control_queue is not None:
            while not self._upstream_control_queue.empty():
                try:
                    self._upstream_control_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        self._set_status(VOICE_STATUS_IDLE)
        logger.info("PersonaPlex S2S client disconnected cleanly.")

    # ------------------------------------------------------------------------
    # Dual-Plane Transmission (Upstream)
    # ------------------------------------------------------------------------

    def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """
        Thread-safe non-blocking enqueue of raw PCM binary audio (Opcode 0x02).
        """
        if not self._is_connected or not pcm_bytes or self._upstream_audio_queue is None:
            return

        def _enqueue():
            if self._upstream_audio_queue is not None:
                try:
                    self._upstream_audio_queue.put_nowait(pcm_bytes)
                except asyncio.QueueFull:
                    # Drop oldest chunk to preserve real-time latency
                    try:
                        _ = self._upstream_audio_queue.get_nowait()
                        self._upstream_audio_queue.put_nowait(pcm_bytes)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        pass

        if self._loop and self._loop.is_running():
            if threading.current_thread() is threading.main_thread() and asyncio.get_event_loop() == self._loop:
                _enqueue()
            else:
                self._loop.call_soon_threadsafe(_enqueue)
        else:
            _enqueue()

    def send_control(self, payload: Dict[str, Any]) -> None:
        """
        Thread-safe enqueue of JSON control plane message (Opcode 0x01).
        """
        if not self._is_connected or self._upstream_control_queue is None:
            return

        def _enqueue():
            if self._upstream_control_queue is not None:
                try:
                    self._upstream_control_queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(_enqueue)
        else:
            _enqueue()

    async def send_control_async(self, payload: Dict[str, Any]) -> None:
        """Coroutine to enqueue a control message directly."""
        if self._upstream_control_queue is not None:
            await self._upstream_control_queue.put(payload)

    # ------------------------------------------------------------------------
    # Barge-In Interruption Handling (<1ms playback flush)
    # ------------------------------------------------------------------------

    def trigger_barge_in_sync(self) -> None:
        """
        Synchronous instant barge-in trigger:
        1. Instantly flushes speaker audio buffer (<1ms).
        2. Sends interrupt frame upstream.
        3. Updates status to LISTENING.
        """
        # 1. Flush local audio playback immediately
        if self.voice_io_manager is not None:
            try:
                self.voice_io_manager.flush_playback()
            except Exception as e:
                logger.debug(f"Error flushing playback in VoiceIOManager: {e}")

        # 2. Enqueue interrupt control frame
        interrupt_frame = {
            "type": "interrupt",
            "session_id": self._session_id or "",
            "timestamp": time.time() * 1000.0,
            "reason": "user_speech_detected"
        }
        self.send_control(interrupt_frame)

        # 3. Transition status
        self._set_status(VOICE_STATUS_LISTENING)

    async def trigger_barge_in(self) -> None:
        """Async wrapper for barge-in interruption."""
        self.trigger_barge_in_sync()

    # ------------------------------------------------------------------------
    # Background Coroutine Workers
    # ------------------------------------------------------------------------

    async def _tx_audio_worker(self) -> None:
        """Asynchronously streams binary PCM audio chunks upstream (Opcode 0x02)."""
        while self._is_running and self._is_connected and self._ws is not None:
            try:
                chunk = await self._upstream_audio_queue.get()
                if chunk is None:
                    break
                await self._ws.send(chunk)
                self.state.telemetry.total_ingress_bytes += len(chunk)
                self._upstream_audio_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"TX Audio worker error: {e}")
                self._handle_disconnect()
                break

    async def _tx_control_worker(self) -> None:
        """Asynchronously dispatches JSON control frames upstream (Opcode 0x01)."""
        while self._is_running and self._is_connected and self._ws is not None:
            try:
                payload = await self._upstream_control_queue.get()
                if payload is None:
                    break
                msg_str = json.dumps(payload)
                await self._ws.send(msg_str)
                self._upstream_control_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"TX Control worker error: {e}")
                self._handle_disconnect()
                break

    async def _rx_worker(self) -> None:
        """Asynchronously receives and multiplexes downstream binary audio & JSON control."""
        while self._is_running and self._is_connected and self._ws is not None:
            try:
                message = await self._ws.recv()
                if isinstance(message, (bytes, bytearray, memoryview)):
                    # Downstream Binary PCM Audio (Opcode 0x02)
                    pcm_bytes = bytes(message)
                    self.state.telemetry.total_egress_bytes += len(pcm_bytes)
                    if self.voice_io_manager is not None:
                        self.voice_io_manager.play_audio_chunk(pcm_bytes)

                    if self.state.status != VOICE_STATUS_SPEAKING and not self.state.is_muted:
                        self._set_status(VOICE_STATUS_SPEAKING)

                elif isinstance(message, str):
                    # Downstream JSON Control Plane (Opcode 0x01)
                    await self._handle_incoming_control(message)

            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed:
                logger.info("PersonaPlex S2S connection closed by remote server.")
                self._handle_disconnect()
                break
            except Exception as e:
                logger.debug(f"RX worker error: {e}")
                self._handle_disconnect()
                break

    async def _ping_worker(self) -> None:
        """Periodically dispatches ping frames to measure round-trip latency."""
        while self._is_running and self._is_connected:
            try:
                await asyncio.sleep(self.ping_interval_s)
                if not self._is_connected:
                    break
                ping_payload = {
                    "type": "ping",
                    "client_time": time.time() * 1000.0,
                    "session_id": self._session_id or ""
                }
                await self.send_control_async(ping_payload)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Ping worker error: {e}")
                break

    # ------------------------------------------------------------------------
    # Downstream JSON Control Frame Parsing
    # ------------------------------------------------------------------------

    async def _handle_incoming_control(self, raw_json: str) -> None:
        """Parse and dispatch downstream control frames."""
        try:
            msg = json.loads(raw_json)
        except Exception as e:
            logger.warning(f"Malformed JSON control frame received: {e}")
            return

        msg_type = msg.get("type", "").lower()

        if msg_type in ("ready", "session_started"):
            self._session_id = msg.get("session_id", self._session_id)
            self.state.session_id = self._session_id
            logger.info(f"PersonaPlex session initialized: session_id={self._session_id}")
            if self.blackboard_store is not None:
                try:
                    self.blackboard_store.update_voice_state(
                        self.state.status,
                        session_id=self._session_id
                    )
                except Exception:
                    pass
            if self.state.status == VOICE_STATUS_IDLE:
                self._set_status(VOICE_STATUS_LISTENING)

        elif msg_type in ("state", "state_change", "set_state"):
            new_state = msg.get("status", msg.get("state", "IDLE"))
            self._set_status(new_state)

        elif msg_type in ("transcript", "transcription"):
            text = msg.get("text", msg.get("transcript", ""))
            is_final = bool(msg.get("is_final", msg.get("isFinal", False)))
            role = msg.get("role", "assistant").lower()

            self.state.current_transcript = text
            if role in ("user", "human"):
                self.state.last_user_speech = text
            else:
                self.state.last_model_speech = text

            if self.blackboard_store is not None:
                try:
                    self.blackboard_store.update_voice_state(
                        self.state.status,
                        current_transcript=self.state.current_transcript,
                        last_user_speech=self.state.last_user_speech,
                        last_model_speech=self.state.last_model_speech
                    )
                except Exception:
                    pass

            if self.on_transcript is not None:
                try:
                    self.on_transcript(text, is_final, role)
                except Exception as e:
                    logger.debug(f"on_transcript callback error: {e}")

        elif msg_type in ("code_snippet", "code_injection", "code"):
            snippet = msg.get("snippet", msg.get("code", ""))
            language = msg.get("language", "python")

            self.state.last_code_snippet = snippet
            if self.blackboard_store is not None:
                try:
                    self.blackboard_store.update_voice_state(
                        self.state.status,
                        last_code_snippet=snippet
                    )
                except Exception:
                    pass

            if self.on_code_snippet is not None:
                try:
                    self.on_code_snippet(snippet, language)
                except Exception as e:
                    logger.debug(f"on_code_snippet callback error: {e}")

        elif msg_type == "pong":
            client_time = msg.get("client_time", 0.0)
            if client_time > 0:
                rtt_ms = max(0.0, time.time() * 1000.0 - float(client_time))
                self.state.telemetry.latency_ms = round(rtt_ms, 2)

                if self.blackboard_store is not None:
                    try:
                        self.blackboard_store.update_voice_telemetry(latency_ms=round(rtt_ms, 2))
                    except Exception:
                        pass

                if self.on_telemetry is not None:
                    try:
                        self.on_telemetry(self.get_telemetry())
                    except Exception as e:
                        logger.debug(f"on_telemetry callback error: {e}")

        elif msg_type == "error":
            err_msg = msg.get("message", "Unknown PersonaPlex error")
            self.state.error_message = err_msg
            self._set_status(VOICE_STATUS_ERROR)
            self._handle_error(err_msg)

        elif msg_type == "session_ended":
            self._session_id = None
            self.state.session_id = None
            self._set_status(VOICE_STATUS_IDLE)

    # ------------------------------------------------------------------------
    # Error & Reconnect Handling
    # ------------------------------------------------------------------------

    def _handle_error(self, message: str) -> None:
        """Trigger on_error callback and update state."""
        self.state.error_message = message
        if self.on_error is not None:
            try:
                self.on_error(message)
            except Exception as e:
                logger.debug(f"on_error callback error: {e}")

    def _handle_disconnect(self) -> None:
        """Internal handler for socket disconnection."""
        self._is_connected = False
        self._ws = None
        self._set_status(VOICE_STATUS_IDLE)

        if self.auto_reconnect and self._is_running:
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule background reconnect attempt."""
        if self._reconnect_task and not self._reconnect_task.done():
            return
        if self._loop and self._loop.is_running():
            self._reconnect_task = self._loop.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Exponential / interval backoff reconnect coroutine."""
        while self._is_running and not self._is_connected:
            self._reconnect_attempts += 1
            if self._reconnect_attempts > self.max_reconnect_attempts:
                logger.warning(f"PersonaPlex reconnect exceeded max attempts ({self.max_reconnect_attempts}). Stopping.")
                self._handle_error(f"Reconnect failed after {self.max_reconnect_attempts} attempts.")
                break

            logger.info(f"PersonaPlex reconnect attempt {self._reconnect_attempts}/{self.max_reconnect_attempts} in {self.reconnect_interval_s}s...")
            await asyncio.sleep(self.reconnect_interval_s)

            success = await self.connect()
            if success:
                logger.info("PersonaPlex S2S reconnected successfully.")
                break
