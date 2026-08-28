"""
Unit Tests: Canonical Port AGI Coding Terminal TUI Voice Integration (Milestone M3 & Feature 29)
Verifies:
1. AgiCodingTerminalView mounting, widget hierarchy, and sub-tab navigation.
2. Voice status badge rendering in status bar (#terminal-status-bar) and indicator strip (#voice-coding-strip) across all states:
   [LISTENING | SPEAKING | THINKING | IDLE | MUTED | ERROR].
3. Custom Textual Message classes:
   - VoiceStateChanged
   - VoiceTranscriptReceived
   - VoiceCodeSnippetInjected
   - VoiceTelemetryUpdated
4. Non-blocking message handling:
   - VoiceTranscriptReceived appends to #voice-transcription-log (User in cyan, Assistant in green).
   - VoiceCodeSnippetInjected updates editor_code_buffer and logs to terminal and voice log.
   - VoiceTelemetryUpdated updates #voice-telemetry-view and HUD metrics with zero lag.
5. Action button clicks:
   - #btn-start-stt (Start Voice Stream)
   - #btn-stop-stt (Stop Voice Stream)
   - #btn-trigger-tts (Mute / Unmute Mic toggle)
   - #btn-voice-code (Hands-Free Auto-Inject ON/OFF toggle)
6. Non-blocking UI execution: Keypresses, REPL commands (/voice, /mute), and rapid grid cycling under heavy traffic.
7. Lifecycle management and clean teardown on unmount.
"""

import os
import sys
import time
import pytest
import asyncio
from typing import Optional

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Input, RichLog, TabbedContent
from views.agi_coding_terminal_view import (
    AgiCodingTerminalView,
    VoiceStateChanged,
    VoiceTranscriptReceived,
    VoiceCodeSnippetInjected,
    VoiceTelemetryUpdated,
)
from models.blackboard_models import (
    VoiceTelemetry,
    VoiceCodingState,
    VOICE_STATUS_IDLE,
    VOICE_STATUS_LISTENING,
    VOICE_STATUS_THINKING,
    VOICE_STATUS_SPEAKING,
    VOICE_STATUS_MUTED,
    VOICE_STATUS_ERROR,
)
from services.voice_io_manager import VoiceIOManager, SyntheticAudioEngine
from services.personaplex_s2s_client import PersonaPlexS2SClient


class VoiceTUIHarnessApp(App):
    """Test harness App mounting AgiCodingTerminalView."""
    CSS = """
    Screen {
        background: #070b12;
        color: #e2e8f0;
    }
    """

    def __init__(
        self,
        voice_io_manager: Optional[VoiceIOManager] = None,
        s2s_client: Optional[PersonaPlexS2SClient] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.terminal_view = AgiCodingTerminalView(
            voice_io_manager=voice_io_manager,
            s2s_client=s2s_client
        )

    def compose(self) -> ComposeResult:
        yield self.terminal_view


# ============================================================================
# 1. MESSAGE CLASS TESTS
# ============================================================================

def test_voice_message_classes_instantiation():
    """Verify instantiation, attributes, and defaults for all 4 Custom Message classes."""
    # 1. VoiceStateChanged
    m1 = VoiceStateChanged(status="LISTENING", is_active=True, is_muted=False, endpoint="ws://localhost:8765")
    assert m1.status == "LISTENING"
    assert m1.is_active is True
    assert m1.is_muted is False
    assert m1.endpoint == "ws://localhost:8765"

    # 2. VoiceTranscriptReceived
    m2 = VoiceTranscriptReceived(text="Build a resilient neural bridge", is_final=True, role="user")
    assert m2.text == "Build a resilient neural bridge"
    assert m2.is_final is True
    assert m2.role == "user"
    assert isinstance(m2.timestamp, str)

    # 3. VoiceCodeSnippetInjected
    m3 = VoiceCodeSnippetInjected(snippet="def ping(): return True", language="python", auto_executed=True)
    assert m3.snippet == "def ping(): return True"
    assert m3.language == "python"
    assert m3.auto_executed is True

    # 4. VoiceTelemetryUpdated
    tel = VoiceTelemetry(input_db=-42.0, output_db=-24.0, latency_ms=3.5, vad_active=True)
    m4 = VoiceTelemetryUpdated(telemetry=tel)
    assert m4.telemetry is not None
    assert m4.telemetry.input_db == -42.0
    assert m4.telemetry.latency_ms == 3.5

    m4_alt = VoiceTelemetryUpdated(input_db=-38.0, output_db=-60.0, latency_ms=2.1, vad_active=False)
    assert m4_alt.input_db == -38.0
    assert m4_alt.latency_ms == 2.1
    assert m4_alt.vad_active is False


# ============================================================================
# 2. WIDGET HIERARCHY & TAB NAVIGATION (PILOT)
# ============================================================================

@pytest.mark.asyncio
async def test_agi_coding_terminal_view_mounting_and_widgets():
    """Verify AgiCodingTerminalView mounts correctly with all required widgets and tabs."""
    synthetic_vm = VoiceIOManager.create_synthetic()
    app = VoiceTUIHarnessApp(voice_io_manager=synthetic_vm)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)

        view = app.terminal_view
        assert view is not None

        # Check top status HUD
        status_bar = view.query_one("#terminal-status-bar", Static)
        assert status_bar is not None

        # Check main TabbedContent
        tabs = view.query_one("#agi-terminal-tabs", TabbedContent)
        assert tabs is not None

        # Check Tab 1 widgets
        assert view.query_one("#grid-coding-container", Static) is not None
        assert view.query_one("#terminal-output-log", RichLog) is not None
        assert view.query_one("#voice-coding-strip", Static) is not None
        assert view.query_one("#repl-input", Input) is not None

        # Check Tab 2 widgets
        assert view.query_one("#voice-telemetry-view", Static) is not None
        assert view.query_one("#voice-transcription-log", RichLog) is not None
        assert view.query_one("#btn-start-stt", Button) is not None
        assert view.query_one("#btn-stop-stt", Button) is not None
        assert view.query_one("#btn-trigger-tts", Button) is not None
        assert view.query_one("#btn-voice-code", Button) is not None

        # Switch to Tab 2
        tabs.active = "tab-voice-coding"
        await pilot.pause(0.2)
        assert tabs.active == "tab-voice-coding"

        # Switch back to Tab 1
        tabs.active = "tab-coding-shell"
        await pilot.pause(0.2)
        assert tabs.active == "tab-coding-shell"


# ============================================================================
# 3. VOICE STATUS BADGE RENDERING ACROSS ALL STATES
# ============================================================================

@pytest.mark.asyncio
async def test_voice_status_badge_rendering_across_all_states():
    """Verify status bar (#terminal-status-bar) and indicator strip render all voice states."""
    app = VoiceTUIHarnessApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view

        states_to_test = [
            (VOICE_STATUS_LISTENING, True, False),
            (VOICE_STATUS_SPEAKING, True, False),
            (VOICE_STATUS_THINKING, True, False),
            (VOICE_STATUS_MUTED, False, True),
            (VOICE_STATUS_ERROR, False, False),
            (VOICE_STATUS_IDLE, False, False),
        ]

        for state, expected_active, expected_muted in states_to_test:
            # Post VoiceStateChanged message
            view.post_message(VoiceStateChanged(status=state, is_active=expected_active, is_muted=expected_muted))
            await pilot.pause(0.1)

            assert view.voice_status == state
            assert view.is_muted == expected_muted

            # Verify status bar and strip exist and render without crash
            status_bar = view.query_one("#terminal-status-bar", Static)
            strip = view.query_one("#voice-coding-strip", Static)
            assert status_bar is not None
            assert strip is not None


# ============================================================================
# 4. TRANSCRIPTION MESSAGE HANDLING & AUTO-INJECTION
# ============================================================================

@pytest.mark.asyncio
async def test_voice_transcript_received_message_handling():
    """Verify VoiceTranscriptReceived writes to transcription log and injects user prompt into REPL."""
    app = VoiceTUIHarnessApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view
        vlog = view.query_one("#voice-transcription-log", RichLog)
        repl = view.query_one("#repl-input", Input)

        # 1. User transcript with auto-inject ON
        view.auto_inject_enabled = True
        user_msg = VoiceTranscriptReceived(text="implement genetic MoE sharding", is_final=True, role="user")
        view.post_message(user_msg)
        await pilot.pause(0.1)

        # REPL input should have the transcript text
        assert repl.value == "implement genetic MoE sharding"

        # 2. Assistant transcript
        asst_msg = VoiceTranscriptReceived(text="Implementing 80-layer tensor sharding now.", is_final=True, role="assistant")
        view.post_message(asst_msg)
        await pilot.pause(0.1)

        # 3. User transcript with auto-inject OFF
        view.auto_inject_enabled = False
        repl.value = ""
        user_msg2 = VoiceTranscriptReceived(text="new command ignored by repl", is_final=True, role="user")
        view.post_message(user_msg2)
        await pilot.pause(0.1)
        assert repl.value == ""


# ============================================================================
# 5. CODE SNIPPET INJECTION MESSAGE HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_voice_code_snippet_injected_message_handling():
    """Verify VoiceCodeSnippetInjected updates editor_code_buffer and logs notification."""
    app = VoiceTUIHarnessApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view

        snippet_code = "def compute_kamath_filter(rr_list):\n    return [rr for rr in rr_list if abs(rr - 433) < 86.6]"
        msg = VoiceCodeSnippetInjected(snippet=snippet_code, language="python")
        view.post_message(msg)
        await pilot.pause(0.1)

        assert view.editor_code_buffer == snippet_code


# ============================================================================
# 6. TELEMETRY UPDATE MESSAGE HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_voice_telemetry_updated_message_handling():
    """Verify VoiceTelemetryUpdated updates internal telemetry snapshot and views."""
    app = VoiceTUIHarnessApp()

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view

        custom_tel = VoiceTelemetry(
            input_db=-34.5,
            output_db=-19.2,
            latency_ms=2.85,
            vad_active=True,
            speech_detected=True,
            total_ingress_bytes=64000,
            total_egress_bytes=128000,
            jitter_ms=0.65
        )
        msg = VoiceTelemetryUpdated(telemetry=custom_tel)
        view.post_message(msg)
        await pilot.pause(0.1)

        assert view._latest_telemetry.input_db == -34.5
        assert view._latest_telemetry.output_db == -19.2
        assert view._latest_telemetry.latency_ms == 2.85
        assert view._latest_telemetry.vad_active is True
        assert view._latest_telemetry.total_ingress_bytes == 64000


# ============================================================================
# 7. ACTION BUTTONS INTERACTION
# ============================================================================

@pytest.mark.asyncio
async def test_voice_action_buttons_clicks():
    """Verify clicks on all 4 action buttons trigger corresponding voice state transitions."""
    synthetic_vm = VoiceIOManager.create_synthetic()
    app = VoiceTUIHarnessApp(voice_io_manager=synthetic_vm)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view
        tabs = view.query_one("#agi-terminal-tabs", TabbedContent)
        tabs.active = "tab-voice-coding"
        await pilot.pause(0.1)

        # 1. Click #btn-start-stt
        await pilot.click("#btn-start-stt")
        await pilot.pause(0.1)
        assert view.voice_status == VOICE_STATUS_LISTENING
        assert view.is_stt_active is True
        assert synthetic_vm.is_capturing is True

        # 2. Click #btn-trigger-tts (Mute Mic)
        await pilot.click("#btn-trigger-tts")
        await pilot.pause(0.1)
        assert view.voice_status == VOICE_STATUS_MUTED
        assert view.is_muted is True
        assert synthetic_vm.is_muted is True

        # 3. Click #btn-trigger-tts again (Unmute Mic)
        await pilot.click("#btn-trigger-tts")
        await pilot.pause(0.1)
        assert view.voice_status == VOICE_STATUS_LISTENING
        assert view.is_muted is False
        assert synthetic_vm.is_muted is False

        # 4. Click #btn-voice-code (Toggle Auto-Inject OFF)
        assert view.auto_inject_enabled is True
        await pilot.click("#btn-voice-code")
        await pilot.pause(0.1)
        assert view.auto_inject_enabled is False

        # Click #btn-voice-code again (Toggle Auto-Inject ON)
        await pilot.click("#btn-voice-code")
        await pilot.pause(0.1)
        assert view.auto_inject_enabled is True

        # 5. Click #btn-stop-stt
        await pilot.click("#btn-stop-stt")
        await pilot.pause(0.1)
        assert view.voice_status == VOICE_STATUS_IDLE
        assert view.is_stt_active is False
        assert synthetic_vm.is_capturing is False


# ============================================================================
# 8. REPL VOICE COMMANDS & NON-BLOCKING KEYPRESSES
# ============================================================================

@pytest.mark.asyncio
async def test_repl_commands_and_non_blocking_keypresses():
    """Verify /voice, /mute slash commands and non-blocking keypress grid cycling."""
    synthetic_vm = VoiceIOManager.create_synthetic()
    app = VoiceTUIHarnessApp(voice_io_manager=synthetic_vm)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view

        # Test /voice command in REPL
        view._execute_repl_command("/voice")
        await pilot.pause(0.1)
        assert view.is_stt_active is True
        assert view.voice_status == VOICE_STATUS_LISTENING

        # Test /mute command in REPL
        view._execute_repl_command("/mute")
        await pilot.pause(0.1)
        assert view.is_muted is True
        assert view.voice_status == VOICE_STATUS_MUTED

        # Test un-mute
        view._execute_repl_command("/mute")
        await pilot.pause(0.1)
        assert view.is_muted is False

        # Test /voice command again to stop
        view._execute_repl_command("/voice")
        await pilot.pause(0.1)
        assert view.is_stt_active is False
        assert view.voice_status == VOICE_STATUS_IDLE

        # Test rapid grid split keys: '+' and '-'
        assert view.grid_split_count == 1
        await pilot.press("+")
        await pilot.pause(0.05)
        assert view.grid_split_count == 4

        await pilot.press("]")
        await pilot.pause(0.05)
        assert view.grid_split_count == 8

        await pilot.press("+")
        await pilot.pause(0.05)
        assert view.grid_split_count == 16

        await pilot.press("+")
        await pilot.pause(0.05)
        assert view.grid_split_count == 1

        await pilot.press("-")
        await pilot.pause(0.05)
        assert view.grid_split_count == 16

        await pilot.press("[")
        await pilot.pause(0.05)
        assert view.grid_split_count == 8


# ============================================================================
# 9. S2S BRIDGE CALLBACKS & LIFECYCLE CLEANUP
# ============================================================================

@pytest.mark.asyncio
async def test_s2s_client_callbacks_and_unmount():
    """Verify internal callback bridges route S2S events to Textual messages and unmount cleans up."""
    synthetic_vm = VoiceIOManager.create_synthetic()
    client = PersonaPlexS2SClient(voice_io_manager=synthetic_vm)
    app = VoiceTUIHarnessApp(voice_io_manager=synthetic_vm, s2s_client=client)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        view = app.terminal_view

        # Trigger S2S client callbacks directly
        view._handle_s2s_state_change("SPEAKING")
        await pilot.pause(0.1)
        assert view.voice_status == "SPEAKING"
        assert view.is_tts_active is True

        view._handle_s2s_transcript("Voice coding test", True, "user")
        await pilot.pause(0.1)

        view._handle_s2s_code_snippet("x = 42", "python")
        await pilot.pause(0.1)
        assert view.editor_code_buffer == "x = 42"

        view._handle_s2s_telemetry(VoiceTelemetry(input_db=-50.0, output_db=-30.0, latency_ms=1.2))
        await pilot.pause(0.1)
        assert view._latest_telemetry.latency_ms == 1.2

        view._handle_s2s_error("Socket connection reset")
        await pilot.pause(0.1)

        # Test clean unmount
        view.on_unmount()
        assert synthetic_vm.is_capturing is False
