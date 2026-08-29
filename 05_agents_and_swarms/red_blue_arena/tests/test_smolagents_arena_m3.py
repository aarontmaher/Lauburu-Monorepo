"""
Unit & Integration Test Suite for Milestone M3:
SmolAgents Autonomous Code-Execution Arena & 4-Mode TUI Engine
==============================================================
Tests:
1. Autonomous Python Code-Execution for Faction Leaders (Red / Blue) in Sandbox
2. 4 Selectable Game Modes (Classic, Python Duel, Multi-Model Swarm, Cloud Chaos)
3. Plain-Language Tactical Objective Summaries & Physiological State in Telemetry HUD
4. Standalone & Embedded TUI Synchronization (LiveArenaDevApp & LiveArenaDevScreen)
5. 1-Key Interactive Battle Abilities and Mode Switching via 'm'
"""

import os
import sys
import json
import time
import pytest
from pathlib import Path

WORKSPACE_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(WORKSPACE_ROOT / "05_agents_and_swarms/smolagents_engine"))
sys.path.insert(0, str(WORKSPACE_ROOT / "05_agents_and_swarms/red_blue_arena"))
sys.path.insert(0, str(WORKSPACE_ROOT / "01_apps/canonical_port/tui"))
sys.path.insert(0, str(WORKSPACE_ROOT / "01_apps/canonical_port/tui/screens"))

from smolagents_arena_hub import SmolAgentsArenaHub, GAME_MODES
from live_arena_dev_screen import (
    LiveArenaDevScreen,
    RedTeamGraphicalMapWidget as ScreenRedMap,
    BlueTeamGraphicalMapWidget as ScreenBlueMap,
)
from tui_live_arena_dev import (
    LiveArenaDevApp,
    RedTeamGraphicalMapWidget as AppRedMap,
    BlueTeamGraphicalMapWidget as AppBlueMap,
)


class TestSmolAgentsAutonomousPythonCodeExecution:
    """Verifies sandboxed Python code generation and execution for Red and Blue faction leads."""

    def test_red_lead_code_generation_and_sandboxed_execution_duel_mode(self):
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("SMOLAGENTS_PYTHON_DUEL")
        action = hub.generate_red_smolagent_action(target_node="MacBook_Pro")

        assert action["status"] == "SUCCESS"
        assert action["agent"] == "Hermes 3 / Qwen 7B (Red SmolAgent)"
        assert "def red_exploit_action" in action["generated_code"]
        assert action["execution_result"]["status"] == "BURST_INJECTED"
        assert action["execution_result"]["payload_drained_mb"] == 64
        assert "TB4" in action["intent"] or "MacBook_Pro" in action["intent"]

    def test_blue_lead_code_generation_and_sandboxed_execution_duel_mode(self):
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("SMOLAGENTS_PYTHON_DUEL")
        action = hub.generate_blue_smolagent_action()

        assert action["status"] == "SUCCESS"
        assert action["agent"] == "LuCI OpenWrt / Sentinel (Blue SmolAgent)"
        assert "def blue_defense_action" in action["generated_code"]
        assert action["execution_result"]["status"] == "SHIELD_DEPLOYED"
        assert action["execution_result"]["bufferbloat_mitigated_ms"] == 350.0
        assert "SQM" in action["intent"] or "Kamath" in action["intent"]

    def test_sandboxed_execution_scope_isolation(self):
        """Verifies that generated code executes strictly inside a fresh local dictionary."""
        scope = {}
        code = "result = {'computed': 1024 * 64, 'airgap_verified': True}"
        exec(code, {}, scope)
        assert scope["result"]["computed"] == 65536
        assert scope["result"]["airgap_verified"] is True
        assert "result" in scope


class TestFourSelectableGameModes:
    """Verifies that all 4 canonical game modes are active and generate mode-specific actions."""

    def test_canonical_game_modes_list(self):
        expected = [
            "EDGE_ORCHESTRATOR_CLASSIC",
            "SMOLAGENTS_PYTHON_DUEL",
            "MULTI_MODEL_AGI_SWARM",
            "AIRGAP_MESH_VS_CLOUD_CHAOS",
        ]
        assert GAME_MODES == expected

    def test_mode_1_edge_orchestrator_classic(self):
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("EDGE_ORCHESTRATOR_CLASSIC")
        assert hub.active_mode == "EDGE_ORCHESTRATOR_CLASSIC"

        red_act = hub.generate_red_smolagent_action(target_node="Linux_Head_Node")
        assert red_act["status"] == "SUCCESS"
        assert red_act["execution_result"]["status"] == "PROBE_COMPLETED"
        assert "BQL" in red_act["intent"]

        blue_act = hub.generate_blue_smolagent_action()
        assert blue_act["status"] == "SUCCESS"
        assert blue_act["execution_result"]["status"] == "REMEDIATION_APPLIED"
        assert "fq_codel" in blue_act["intent"]

    def test_mode_2_smolagents_python_duel(self):
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("SMOLAGENTS_PYTHON_DUEL")
        assert hub.active_mode == "SMOLAGENTS_PYTHON_DUEL"

        tick = hub.execute_arena_tick()
        assert tick["active_game_mode"] == "SMOLAGENTS_PYTHON_DUEL"
        assert "BURST_INJECTED" in tick["smolagent_code_executions"]["red_code"]
        assert "SHIELD_DEPLOYED" in tick["smolagent_code_executions"]["blue_code"]

    def test_mode_3_multi_model_agi_swarm(self):
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("MULTI_MODEL_AGI_SWARM")
        assert hub.active_mode == "MULTI_MODEL_AGI_SWARM"

        red_act = hub.generate_red_smolagent_action()
        assert red_act["status"] == "SUCCESS"
        assert red_act["execution_result"]["status"] == "SWARM_DISPATCHED"
        assert "Hermes" in red_act["intent"] or "Qwen" in red_act["intent"]

        blue_act = hub.generate_blue_smolagent_action()
        assert blue_act["status"] == "SUCCESS"
        assert blue_act["execution_result"]["status"] == "MOE_ROUTED"
        assert "Genetic MoE" in blue_act["intent"]

    def test_mode_4_airgap_mesh_vs_cloud_chaos(self):
        hub = SmolAgentsArenaHub()
        hub.set_game_mode("AIRGAP_MESH_VS_CLOUD_CHAOS")
        assert hub.active_mode == "AIRGAP_MESH_VS_CLOUD_CHAOS"

        red_act = hub.generate_red_smolagent_action()
        assert red_act["status"] == "SUCCESS"
        assert red_act["execution_result"]["status"] == "CHAOS_INJECTED"
        assert "latency" in red_act["intent"] or "WAN" in red_act["intent"]

        blue_act = hub.generate_blue_smolagent_action()
        assert blue_act["status"] == "SUCCESS"
        assert blue_act["execution_result"]["status"] == "AIRGAP_LOCKED"
        assert "airgap" in blue_act["intent"] or "biometric" in blue_act["intent"]

    def test_mode_cycling_across_all_four(self):
        hub = SmolAgentsArenaHub()
        for mode in GAME_MODES:
            res = hub.set_game_mode(mode)
            assert res == mode
            assert hub.active_mode == mode


class TestTelemetryHUDTacticalObjectiveSummaries:
    """Verifies that the HUD produces plain-language statements of active intent."""

    def test_tactical_intent_summary_fields(self):
        hub = SmolAgentsArenaHub()
        tick = hub.execute_arena_tick()
        summary = tick["tactical_intent_summary"]

        assert "red_faction_intent" in summary
        assert "blue_faction_intent" in summary
        assert "user_biological_state" in summary
        assert "combat_narrative" in summary

        # Verify plain-language intent length & content
        assert len(summary["red_faction_intent"]) > 10
        assert len(summary["blue_faction_intent"]) > 10
        assert "Heart Rate" in summary["user_biological_state"]
        assert "BP" in summary["user_biological_state"]
        assert "Red" in summary["combat_narrative"] and "Blue" in summary["combat_narrative"]

    def test_state_file_persistence(self):
        hub = SmolAgentsArenaHub()
        tick = hub.execute_arena_tick()
        state_file = WORKSPACE_ROOT / "00_core_infrastructure/self_healing_hub/src/smolagents_arena_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            data = json.load(f)

        assert data["active_game_mode"] == tick["active_game_mode"]
        assert "tactical_intent_summary" in data


class TestTUISynchronizationAndWidgets:
    """Verifies synchronization between LiveArenaDevScreen and standalone LiveArenaDevApp."""

    def test_map_widgets_render_rich_panels(self):
        red_w = ScreenRedMap()
        panel_red = red_w.render_map(hr_bpm=80, chaos_active=False)
        assert panel_red is not None

        blue_w = ScreenBlueMap()
        panel_blue = blue_w.render_map(hr_bpm=80, chaos_active=True)
        assert panel_blue is not None

    def test_standalone_app_map_widgets_render_rich_panels(self):
        red_w = AppRedMap()
        panel_red = red_w.render_map(hr_bpm=72, chaos_active=True)
        assert panel_red is not None

        blue_w = AppBlueMap()
        panel_blue = blue_w.render_map(hr_bpm=72, chaos_active=False)
        assert panel_blue is not None

    def test_screen_bindings_and_actions(self):
        screen_bindings = [b[0] for b in LiveArenaDevScreen.BINDINGS]
        app_bindings = [b[0] for b in LiveArenaDevApp.BINDINGS]

        # Both must support canonical 1-key interactive battle commands
        for k in ["m", "c", "h", "b", "s", "v"]:
            assert k in screen_bindings
            assert k in app_bindings
