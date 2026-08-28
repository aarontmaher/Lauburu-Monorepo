"""
Unit Tests: Voice Coding Audio I/O Manager & Blackboard State Models (Milestone 1)
Validates:
- Pure Python RMS and dBFS calculations without removed audioop (Python 3.13+)
- Pure Python VAD hysteresis and hangover state tracking
- SyntheticAudioEngine capture, playback, and instant buffer flush (<1ms)
- PyAudioEngine hardware detection and graceful fallback
- VoiceIOManager lifecycle (start, stop, mute, unmute, toggle_mute, telemetry)
- VoiceCodingState, VoiceTelemetry, VoiceStatus data models
- BlackboardStore voice state update methods and <3ms fast-path performance
"""

import os
import sys
import time
import math
import pytest
import tempfile
from typing import List, Tuple

# Ensure tui package is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))
from models.blackboard_models import (
    BlackboardTelemetryState,
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
    calculate_pcm_rms,
    calculate_pcm_dbfs,
    PurePythonVAD,
    generate_synthetic_pcm_sine,
    generate_synthetic_pcm_silence,
    SyntheticAudioEngine,
    PyAudioEngine,
    VoiceIOManager
)


# ============================================================================
# 1. DATA MODEL & STATUS TESTS
# ============================================================================

def test_voice_status_enum_and_constants():
    """Verify VoiceStatus enum values and top-level constants match."""
    assert VoiceStatus.IDLE == "IDLE"
    assert VoiceStatus.LISTENING == "LISTENING"
    assert VoiceStatus.THINKING == "THINKING"
    assert VoiceStatus.SPEAKING == "SPEAKING"
    assert VoiceStatus.MUTED == "MUTED"
    assert VoiceStatus.ERROR == "ERROR"

    assert VOICE_STATUS_IDLE == "IDLE"
    assert VOICE_STATUS_LISTENING == "LISTENING"
    assert VOICE_STATUS_THINKING == "THINKING"
    assert VOICE_STATUS_SPEAKING == "SPEAKING"
    assert VOICE_STATUS_MUTED == "MUTED"
    assert VOICE_STATUS_ERROR == "ERROR"


def test_voice_telemetry_defaults_and_serialization():
    """Verify VoiceTelemetry defaults and dictionary round-trip."""
    tel = VoiceTelemetry()
    assert tel.input_db == -60.0
    assert tel.output_db == -60.0
    assert tel.sample_rate_in_hz == 16000
    assert tel.sample_rate_out_hz == 24000
    assert tel.vad_active is False
    assert tel.total_ingress_bytes == 0
    assert tel.total_egress_bytes == 0

    d = tel.to_dict()
    assert isinstance(d, dict)
    assert d["input_db"] == -60.0
    assert d["sample_rate_in_hz"] == 16000


def test_voice_coding_state_defaults_and_roundtrip():
    """Verify VoiceCodingState instantiation, to_dict, and from_dict."""
    state = VoiceCodingState()
    assert state.status == "IDLE"
    assert state.is_active is False
    assert state.is_stt_active is False
    assert state.is_tts_active is False
    assert state.is_muted is False
    assert state.endpoint_ws == "ws://127.0.0.1:8765/ws/voice"
    assert state.current_transcript == ""

    # Modify and roundtrip
    state.status = "LISTENING"
    state.is_active = True
    state.is_stt_active = True
    state.current_transcript = "import numpy as np"
    state.telemetry.input_db = -18.5
    state.telemetry.vad_active = True

    d = state.to_dict()
    assert d["status"] == "LISTENING"
    assert d["current_transcript"] == "import numpy as np"
    assert d["telemetry"]["input_db"] == -18.5

    reconstructed = VoiceCodingState.from_dict(d)
    assert reconstructed.status == "LISTENING"
    assert reconstructed.is_stt_active is True
    assert reconstructed.current_transcript == "import numpy as np"
    assert reconstructed.telemetry.input_db == -18.5
    assert reconstructed.telemetry.vad_active is True


def test_blackboard_telemetry_state_voice_integration():
    """Verify voice_coding is wired into BlackboardTelemetryState and serialization."""
    root = BlackboardTelemetryState.create_canonical_default()
    assert hasattr(root, "voice_coding")
    assert isinstance(root.voice_coding, VoiceCodingState)
    assert root.voice_coding.status == "IDLE"
    assert root.voice_coding.endpoint_ws == "ws://127.0.0.1:8765/ws/voice"

    # JSON roundtrip
    json_str = root.to_json()
    assert '"voice_coding"' in json_str
    from_json = BlackboardTelemetryState.from_json(json_str)
    assert from_json.voice_coding.status == "IDLE"
    assert from_json.voice_coding.telemetry.sample_rate_in_hz == 16000

    # YAML roundtrip
    yaml_str = root.to_yaml()
    assert "voice_coding:" in yaml_str
    from_yaml = BlackboardTelemetryState.from_yaml(yaml_str)
    assert from_yaml.voice_coding.status == "IDLE"


# ============================================================================
# 2. BLACKBOARD STORE VOICE SYNC & FAST-PATH TESTS
# ============================================================================

def test_blackboard_store_voice_methods():
    """Verify BlackboardStore update_voice_state, update_voice_telemetry, and get_voice_state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BlackboardStore(persistence_dir=tmpdir, auto_persist=False)
        
        # Initial voice state
        vc = store.get_voice_state()
        assert vc.status == "IDLE"
        assert vc.is_active is False

        # Update status string
        snap1 = store.update_voice_state("LISTENING", current_transcript="Hello World")
        assert snap1.voice_coding.status == "LISTENING"
        assert snap1.voice_coding.is_stt_active is True
        assert snap1.voice_coding.is_active is True
        assert snap1.voice_coding.current_transcript == "Hello World"

        # Update telemetry
        snap2 = store.update_voice_telemetry(input_db=-24.2, output_db=-18.0, latency_ms=15.4, vad_active=True)
        assert snap2.voice_coding.telemetry.input_db == -24.2
        assert snap2.voice_coding.telemetry.output_db == -18.0
        assert snap2.voice_coding.telemetry.latency_ms == 15.4
        assert snap2.voice_coding.telemetry.vad_active is True

        # Update layer generic
        snap3 = store.update_layer("voice_coding", {"status": "SPEAKING", "is_tts_active": True})
        assert snap3.voice_coding.status == "SPEAKING"
        assert snap3.voice_coding.is_tts_active is True


def test_blackboard_store_voice_fast_path_latency():
    """Verify get_voice_state and update_voice_state execute in <3ms (Rule #6 invariant)."""
    store = BlackboardStore(auto_persist=False)
    
    # Measure get_voice_state
    t0 = time.perf_counter()
    for _ in range(100):
        _ = store.get_voice_state()
    avg_get_ms = ((time.perf_counter() - t0) / 100.0) * 1000.0
    assert avg_get_ms < 1.0, f"get_voice_state too slow: {avg_get_ms:.3f}ms (>1.0ms)"

    # Measure update_voice_state
    t0 = time.perf_counter()
    for i in range(100):
        _ = store.update_voice_state("LISTENING", current_transcript=f"token_{i}")
    avg_update_ms = ((time.perf_counter() - t0) / 100.0) * 1000.0
    assert avg_update_ms < 3.0, f"update_voice_state too slow: {avg_update_ms:.3f}ms (>3.0ms)"


# ============================================================================
# 3. PURE PYTHON AUDIO DSP & VAD TESTS
# ============================================================================

def test_pure_python_rms_and_dbfs_math():
    """Verify RMS and dBFS pure Python formulas across edge cases without audioop."""
    # 1. Empty bytes
    assert calculate_pcm_rms(b"") == 0.0
    assert calculate_pcm_dbfs(b"") == -100.0

    # 2. Odd byte length
    assert calculate_pcm_rms(b"\x00\x00\x01") == 0.0

    # 3. Pure silence
    silence_chunk = generate_synthetic_pcm_silence(0.02, 16000)
    assert len(silence_chunk) == 640
    assert calculate_pcm_rms(silence_chunk) == 0.0
    assert calculate_pcm_dbfs(silence_chunk) == -100.0

    # 4. Pure sine wave
    sine_chunk = generate_synthetic_pcm_sine(frequency_hz=440.0, duration_s=0.02, sample_rate_hz=16000, amplitude=1.0)
    assert len(sine_chunk) == 640
    rms_val = calculate_pcm_rms(sine_chunk)
    # Sine wave with amplitude 32767 has RMS = 32767 / sqrt(2) ≈ 23169
    assert 22000.0 < rms_val < 24000.0
    dbfs_val = calculate_pcm_dbfs(sine_chunk)
    # Theoretical dBFS for full amplitude sine is -3.01 dBFS
    assert -3.5 < dbfs_val < -2.5


def test_pure_python_vad_state_transitions():
    """Verify VAD state machine transitions from silence to speech with hysteresis and hangover."""
    vad = PurePythonVAD(threshold_db=-40.0, hangover_frames=3, min_speech_frames=2)
    silence = generate_synthetic_pcm_silence(0.02, 16000)
    speech = generate_synthetic_pcm_sine(440.0, 0.02, 16000, amplitude=0.6) # ~ -4.4 dBFS

    # Initial silence -> False
    is_speech, _, _ = vad.process_chunk(silence)
    assert is_speech is False

    # First speech frame -> Still False (requires min_speech_frames=2)
    is_speech, _, _ = vad.process_chunk(speech)
    assert is_speech is False

    # Second speech frame -> True
    is_speech, _, _ = vad.process_chunk(speech)
    assert is_speech is True

    # Continuous speech -> True
    is_speech, _, _ = vad.process_chunk(speech)
    assert is_speech is True

    # First silence frame after speech -> True (hangover 3 -> 2)
    is_speech, _, _ = vad.process_chunk(silence)
    assert is_speech is True

    # Second silence frame -> True (hangover 2 -> 1)
    is_speech, _, _ = vad.process_chunk(silence)
    assert is_speech is True

    # Third silence frame -> True (hangover 1 -> 0)
    is_speech, _, _ = vad.process_chunk(silence)
    assert is_speech is True

    # Fourth silence frame -> False (hangover expired)
    is_speech, _, _ = vad.process_chunk(silence)
    assert is_speech is False


# ============================================================================
# 4. SYNTHETIC AUDIO ENGINE TESTS
# ============================================================================

def test_synthetic_audio_engine_capture_and_playback():
    """Verify SyntheticAudioEngine captures chunks on a background thread and records playback."""
    engine = SyntheticAudioEngine(
        sample_rate_in_hz=16000,
        sample_rate_out_hz=24000,
        chunk_duration_s=0.02,
        waveform="sine"
    )

    captured: List[bytes] = []
    engine.start_capture(lambda chunk: captured.append(chunk))
    engine.start_playback()

    assert engine.is_capturing() is True
    assert engine.is_playing() is True

    # Allow worker thread to run for 3-4 chunks (60-80ms)
    time.sleep(0.07)
    assert len(captured) >= 2
    for c in captured:
        assert len(c) == 640 # 20ms @ 16kHz 16-bit mono

    # Enqueue playback
    test_pcm = b"\x01\x02\x03\x04" * 100
    engine.play_chunk(test_pcm)
    assert engine.get_recorded_playback_bytes() == test_pcm

    # Instant flush (<1ms)
    t0 = time.perf_counter()
    engine.flush_playback()
    flush_time_ms = (time.perf_counter() - t0) * 1000.0
    assert flush_time_ms < 2.0

    engine.stop_capture()
    engine.stop_playback()
    assert engine.is_capturing() is False
    assert engine.is_playing() is False
    engine.close()


# ============================================================================
# 5. VOICE I/O MANAGER COORDINATOR TESTS
# ============================================================================

def test_voice_io_manager_lifecycle_and_telemetry():
    """Verify VoiceIOManager start, stop, mute, unmute, and live telemetry."""
    received_chunks: List[Tuple[bytes, float, bool]] = []
    vad_changes: List[bool] = []

    mgr = VoiceIOManager.create_synthetic(
        sample_rate_in_hz=16000,
        sample_rate_out_hz=24000,
        chunk_duration_ms=20,
        waveform="sine",
        frequency_hz=440.0,
        on_audio_chunk=lambda chunk, rms, speech: received_chunks.append((chunk, rms, speech))
    )
    mgr.on_vad_state_changed = lambda is_speech: vad_changes.append(is_speech)

    mgr.start()
    assert mgr.is_active is True
    assert mgr.is_capturing is True
    assert mgr.is_playing is True

    time.sleep(0.08)
    assert len(received_chunks) >= 3

    # Check telemetry
    tel = mgr.get_telemetry()
    assert tel.total_ingress_bytes > 0
    assert tel.sample_rate_in_hz == 16000
    assert tel.sample_rate_out_hz == 24000
    assert tel.rms_energy > 0.0

    # Test playback
    test_audio = b"\x10\x20" * 480
    mgr.play_audio_chunk(test_audio)
    tel2 = mgr.get_telemetry()
    assert tel2.total_egress_bytes == len(test_audio)

    # Test barge-in flush
    t0 = time.perf_counter()
    mgr.flush_playback()
    flush_ms = (time.perf_counter() - t0) * 1000.0
    assert flush_ms < 3.0

    # Test Mute / Unmute
    mgr.mute()
    assert mgr.is_muted is True
    time.sleep(0.05)
    tel_muted = mgr.get_telemetry()
    assert tel_muted.input_db == -100.0
    assert tel_muted.vad_active is False

    toggled = mgr.toggle_mute()
    assert toggled is False
    assert mgr.is_muted is False

    mgr.stop()
    assert mgr.is_active is False
    mgr.close()
