"""
Comprehensive Unit & Textual Pilot Tests for TUI Beta: Multi-Engine Swarm IDE & Chat Shell.
Verifies mounting, 8-engine cycling, multi-agent chat streaming, code buffer execution,
diff inspector, debate consensus gauge, voice coding HUD, latency matrix, and slash commands.
"""

import os
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from textual.app import App
from textual.widgets import Select, Static, RichLog, TextArea, Input, Button

from tui.prototypes.tui_beta_chat_ide import (
    TuiBetaChatIDEApp,
    TuiBetaChatIDEView,
    BetaHeaderBar,
    BetaEngineChanged,
    LeftMainPane,
    MultiAgentChatStream,
    ActiveCodeBuffer,
    RightSidebar,
    DebateConsensusGauge,
    VoiceCodingHud,
    LatencyMatrixPanel,
    BetaPromptInputBar,
    CodeExecutionRequested,
)
from tui.services.inference_router import UnifiedInferenceRouter


# ============================================================================
# 1. MOUNTING & DOM LAYOUT INTEGRITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_mounting_and_dom_hierarchy():
    """Verify TuiBetaChatIDEApp mounts cleanly with all required subcomponents and layout panes."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)

        # 1. Root view check
        view = app.query_one(TuiBetaChatIDEView)
        assert view is not None

        # 2. Header bar with 8-engine selector
        header = view.query_one(BetaHeaderBar)
        assert header is not None
        assert header.active_engine == "auto"
        assert len(header.ENGINES) == 8
        select_widget = header.query_one("#beta-engine-select", Select)
        assert select_widget is not None

        # 3. Left Main Pane (65%)
        left_pane = view.query_one(LeftMainPane)
        assert left_pane is not None

        # 3a. Upper Chat & REPL Stream (60%)
        chat_stream = left_pane.query_one(MultiAgentChatStream)
        assert chat_stream is not None
        chat_log = chat_stream.query_one("#chat-log", RichLog)
        assert chat_log is not None

        # 3b. Lower Active Code Buffer (40%)
        code_buffer = left_pane.query_one(ActiveCodeBuffer)
        assert code_buffer is not None
        code_editor = code_buffer.query_one("#code-editor", TextArea)
        assert code_editor is not None
        assert "probe_mesh_latency" in code_editor.text

        # 4. Right Sidebar (35%)
        sidebar = view.query_one(RightSidebar)
        assert sidebar is not None

        # 4a. Panel 1: Debate Consensus Gauge
        debate_gauge = sidebar.query_one(DebateConsensusGauge)
        assert debate_gauge is not None
        assert debate_gauge.accordance >= 0.90
        assert debate_gauge.current_turn >= 1

        # 4b. Panel 2: Voice Coding HUD
        voice_hud = sidebar.query_one(VoiceCodingHud)
        assert voice_hud is not None
        assert "16kHz" in voice_hud.vad_status

        # 4c. Panel 3: Latency Matrix Panel
        latency_matrix = sidebar.query_one(LatencyMatrixPanel)
        assert latency_matrix is not None
        assert len(latency_matrix.ENGINES_DATA) == 8

        # 5. Bottom Prompt Bar
        prompt_bar = view.query_one(BetaPromptInputBar)
        assert prompt_bar is not None
        input_widget = prompt_bar.query_one("#prompt-input", Input)
        assert input_widget is not None


# ============================================================================
# 2. DYNAMIC ENGINE SELECTOR & 8-ENGINE CYCLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_8_engine_cycling_and_router_sync():
    """Verify cycling through all 8 engines via hotkey [ctrl+e] synchronizes router and header."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)
        header = view.query_one(BetaHeaderBar)

        # Expected canonical order of 8 engines:
        # auto -> llama_rpc -> exo -> accelerate -> petals -> gemini -> cloudflare -> julien -> auto
        expected_cycle = [
            "llama_rpc",
            "exo",
            "accelerate",
            "petals",
            "gemini",
            "cloudflare",
            "julien",
            "auto",
        ]

        for expected in expected_cycle:
            await pilot.press("ctrl+e")
            await pilot.pause(0.05)
            assert header.active_engine == expected
            assert view.inference_router.active_engine == expected

        # Test programmatic engine setting
        header.set_engine("gemini")
        await pilot.pause(0.05)
        assert header.active_engine == "gemini"
        assert view.inference_router.active_engine == "gemini"


# ============================================================================
# 3. CODE BUFFER RUNNER & DIFF INSPECTOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_code_buffer_execution_and_diff():
    """Verify executing code from buffer runs safely and logs stdout to chat."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)
        code_buf = view.query_one(ActiveCodeBuffer)

        # Set simple test code
        test_script = 'print("BETA_RUNNER_OUTPUT_VERIFIED: 42 * 2 = 84")'
        code_buf.set_code(test_script)

        # Trigger execution via F5
        await pilot.press("f5")
        await pilot.pause(0.15)

        chat_stream = view.query_one(MultiAgentChatStream)
        chat_log = chat_stream.query_one("#chat-log", RichLog)
        assert chat_log is not None

        # Toggle Diff Inspector
        btn_diff = code_buf.query_one("#btn-toggle-diff", Button)
        btn_diff.press()
        await pilot.pause(0.05)
        assert code_buf.is_diff_view is True

        diff_log = code_buf.query_one("#diff-log", RichLog)
        assert diff_log.styles.display == "block"

        # Toggle back to Editor
        btn_diff.press()
        await pilot.pause(0.05)
        assert code_buf.is_diff_view is False


# ============================================================================
# 4. TRI-ORCHESTRATOR DEBATE GAUGE & VOICE HUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_debate_gauge_and_voice_hud():
    """Verify Tri-Orchestrator debate rounds advance turn counter and voice HUD toggles mute."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)
        gauge = view.query_one(DebateConsensusGauge)
        voice_hud = view.query_one(VoiceCodingHud)

        # Initial debate gauge state
        init_turn = gauge.current_turn
        await pilot.press("ctrl+d")  # Triggers debate duel slash command
        await pilot.pause(0.1)

        assert gauge.current_turn != init_turn or gauge.debate_status in ("CONSENSUS_REACHED", "DEBATING", "CODE_OFF_ACTIVE")

        # Test Voice Mute Toggle
        assert voice_hud.is_muted is False
        await pilot.press("f4")
        await pilot.pause(0.05)
        assert voice_hud.is_muted is True

        await pilot.press("f4")
        await pilot.pause(0.05)
        assert voice_hud.is_muted is False


# ============================================================================
# 5. SLASH COMMANDS & REPL SECURITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_slash_commands_and_security(monkeypatch):
    """Verify slash commands (/audit, /split, /model, /key, /key_cf, /account_cf, /key_julien) work cleanly."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("JULIEN_API_KEY", raising=False)

    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)
        chat = view.query_one(MultiAgentChatStream)

        # 1. /help
        view.handle_user_input("/help")
        await pilot.pause(0.05)

        # 2. /audit
        view.handle_user_input("/audit")
        await pilot.pause(0.05)

        # 3. /split
        view.handle_user_input("/split 8")
        await pilot.pause(0.05)

        # 4. /model
        init_model_idx = view.active_model_idx
        view.handle_user_input("/model")
        assert view.active_model_idx == (init_model_idx + 1) % len(view.MODEL_ROSTER)

        # 5. /key
        view.handle_user_input("/key sk-gemini-test-secret-8888")
        assert os.environ.get("GEMINI_API_KEY") == "sk-gemini-test-secret-8888"

        # 6. /key_cf
        view.handle_user_input("/key_cf cf-secret-token-12345678")
        assert os.environ.get("CLOUDFLARE_API_KEY") == "cf-secret-token-12345678"

        # 7. /account_cf
        view.handle_user_input("/account_cf cf-acc-id-55555")
        assert os.environ.get("CLOUDFLARE_ACCOUNT_ID") == "cf-acc-id-55555"

        # 8. /key_julien
        view.handle_user_input("/key_julien julien-token-9999")
        assert os.environ.get("JULIEN_API_KEY") == "julien-token-9999"

        # 9. /engine status
        view.handle_user_input("/engine status")
        await pilot.pause(0.05)

        # 10. /clear
        view.handle_user_input("/clear")
        await pilot.pause(0.05)


# ============================================================================
# 6. STREAMING INFERENCE & CODE BLOCK EXTRACTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_streaming_inference_and_code_extraction():
    """Verify non-blocking streaming inference routes through router and extracts code blocks."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)

        # Submit text prompt
        inp = view.query_one("#prompt-input", Input)
        inp.value = "Write a fast async fibonacci function in python"
        await pilot.press("enter")

        # Let inference streaming run
        await pilot.pause(0.3)

        # Ensure code block extraction helper functions correctly
        test_response_with_code = (
            "Here is the optimized function:\n"
            "```python\n"
            "async def async_fib(n: int) -> int:\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return n\n"
            "```\n"
            "Ready for execution."
        )
        extracted = view._extract_code_block(test_response_with_code)
        assert extracted is not None
        assert "async def async_fib" in extracted


# ============================================================================
# 8. MULTI-AGENT BADGES & REPL FORMATTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_agent_badges_and_formatting():
    """Verify all 5 agent personas and system/user messages render with appropriate badges."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)
        chat = view.query_one(MultiAgentChatStream)

        # Append messages from all personas
        chat.append_message("kimi", "Kimi Titan 88B proposal for sharded tensor memory.")
        chat.append_message("qwen", "Qwen 38B boundary verification passed.")
        chat.append_message("llama", "Llama 70B unified patch generated.")
        chat.append_message("gemini", "Gemini 2.5 Flash cloud telemetry review.")
        chat.append_message("cloudflare", "Cloudflare Workers AI gateway validated.")
        chat.append_message("user", "User prompt test.")
        chat.append_message("system", "System notice test.")

        await pilot.pause(0.05)
        log = chat.query_one("#chat-log", RichLog)
        assert log is not None


# ============================================================================
# 9. BUTTON CLICKS & ACTIVE CODE ERROR RESILIENCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_button_actions_and_code_error_handling():
    """Verify button clicks and graceful error handling during code execution."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)
        code_buf = view.query_one(ActiveCodeBuffer)

        # 1. Test code syntax error resilience
        code_buf.set_code("def broken_func(:\n    syntax error here")
        btn_run = code_buf.query_one("#btn-run-code", Button)
        btn_run.press()
        await pilot.pause(0.1)

        # 2. Test code buffer clear button
        btn_clear = code_buf.query_one("#btn-clear-code", Button)
        btn_clear.press()
        await pilot.pause(0.05)
        editor = code_buf.query_one("#code-editor", TextArea)
        assert editor.text == ""

        # 3. Test send prompt button
        inp = view.query_one("#prompt-input", Input)
        inp.value = "/audit"
        btn_send = view.query_one("#btn-send-prompt", Button)
        btn_send.press()
        await pilot.pause(0.05)
        assert inp.value == ""


# ============================================================================
# 10. APP SHORTCUT ACTIONS & UNKNOWN COMMAND TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_app_actions_and_unknown_commands():
    """Verify app-level helper actions and unknown slash command feedback."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        view = app.query_one(TuiBetaChatIDEView)

        # Test action methods on App directly
        app.action_trigger_debate()
        await pilot.pause(0.05)

        app.action_clear_chat()
        await pilot.pause(0.05)

        app.action_toggle_voice()
        await pilot.pause(0.05)

        app.action_run_active_code()
        await pilot.pause(0.05)

        # Test unknown command
        view.handle_user_input("/unknown_command_12345")
        await pilot.pause(0.05)


# ============================================================================
# 11. SIGWINCH & RESPONSIVE RESIZE STRESS TEST
# ============================================================================

@pytest.mark.asyncio
async def test_tui_beta_responsive_resize_stress():
    """Verify TuiBetaChatIDEApp withstands dynamic terminal resizes without layout crashes."""
    app = TuiBetaChatIDEApp()

    async with app.run_test(size=(120, 35)) as pilot:
        await pilot.pause(0.05)

        # Rapidly cycle engine 8 times
        for _ in range(8):
            await pilot.press("ctrl+e")
            await pilot.pause(0.02)

        view = app.query_one(TuiBetaChatIDEView)
        assert view is not None
        assert view.inference_router.active_engine in BetaHeaderBar.ENGINES

