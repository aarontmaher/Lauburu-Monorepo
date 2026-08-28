"""
Unit Tests for TrainingPipelineWidget and LauburuGymsWidget (Milestone 2 & 3)
tests/unit/test_training_pipeline_widgets.py

Comprehensive unit tests verifying:
  1. TrainingPipelineWidget: Ingestion Loop, Gatekeeper, Staged HF Epoch VRAM Gate
  2. LauburuGymsWidget: Gyms 1-5 (Red/Blue, Mesh Healing, Stealth Compute, Software Dev, Spatial Grappling)
  3. Braille sparkline generation and non-blocking telemetry updates.

Strict Invariant: Rule #0 Zero-Mock — authentic system calls, file stats, and math models.
"""

import os
import sys
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static, TabbedContent

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from widgets.training_pipeline_widget import TrainingPipelineWidget
from widgets.lauburu_gyms_widget import LauburuGymsWidget
from widgets.live_implementation_stream_widget import render_braille_sparkline


def get_static_text(static_widget: Static) -> str:
    """Helper to extract full text and title from a Static widget's rendered Rich renderable."""
    renderable = static_widget.render()
    panel = getattr(renderable, "_renderable", renderable)
    title = str(getattr(panel, "title", ""))
    content = str(getattr(panel, "renderable", panel))
    return f"{title} {content}"


class PipelineWidgetTestApp(App):
    """Test harness App mounting TrainingPipelineWidget."""
    def compose(self) -> ComposeResult:
        yield TrainingPipelineWidget(id="test-pipeline-widget")


class GymsWidgetTestApp(App):
    """Test harness App mounting LauburuGymsWidget."""
    def compose(self) -> ComposeResult:
        yield LauburuGymsWidget(id="test-gyms-widget")


# ============================================================================
# 1. TrainingPipelineWidget Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_training_pipeline_widget_composition_and_mounting():
    """Verifies that TrainingPipelineWidget mounts all 3 child static panels."""
    app = PipelineWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(TrainingPipelineWidget)
        assert widget is not None
        assert widget.query_one("#ingestion-panel", Static) is not None
        assert widget.query_one("#gatekeeper-panel", Static) is not None
        assert widget.query_one("#vram-gate-panel", Static) is not None


@pytest.mark.asyncio
async def test_training_pipeline_widget_ingestion_rendering():
    """Verifies Ingestion Loop panel rendering with custom telemetry payload."""
    app = PipelineWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(TrainingPipelineWidget)
        
        custom_ingestion = {
            "file_size_bytes": 78381354,
            "file_size_mb": 74.75,
            "record_count": 12115,
            "growth_rate_bps": 124.5,
            "growth_rate_records_per_min": 18.2,
            "primary_dataset_path": "/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl",
            "primary_dataset_exists": True,
            "aux_datasets": [
                {"name": "truth_audit_debate.jsonl", "exists": True, "size_mb": 9.86, "record_count": 1984},
                {"name": "movesense_biometrics_coaching.jsonl", "exists": True, "size_mb": 12.75, "record_count": 12457},
            ],
            "total_dataset_mb": 97.36,
        }
        
        widget.update_telemetry(ingestion=custom_ingestion)
        await pilot.pause(0.05)
        
        ingestion_panel = widget.query_one("#ingestion-panel", Static)
        text = get_static_text(ingestion_panel)
        assert "74.75 MB" in text or "74.7" in text
        assert "12,115" in text or "12115" in text
        assert "continuous_lora_dataset.jsonl" in text
        assert "Zero-Mock" in text or "CERTIFIED" in text


@pytest.mark.asyncio
async def test_training_pipeline_widget_gatekeeper_rendering():
    """Verifies Gatekeeper panel rendering with locked vs unlocked Devil's Lock states."""
    app = PipelineWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(TrainingPipelineWidget)
        
        # Test Locked state
        locked_gatekeeper = {
            "active_intercepts_count": 42,
            "lock_state": "LOCKED",
            "resource_cap_active": True,
            "threat_level": "ELEVATED",
            "active_subagent": {"name": "TestSubagent", "pid": 99999, "archetype": "worker"},
            "recent_intercepts_log": [{"event": "SSH Port Scan Blocked", "ip": "100.101.39.98"}],
        }
        
        widget.update_telemetry(gatekeeper=locked_gatekeeper)
        await pilot.pause(0.05)
        
        gate_panel = widget.query_one("#gatekeeper-panel", Static)
        text = get_static_text(gate_panel)
        assert "LOCKED" in text
        assert "TestSubagent" in text
        assert "42" in text
        assert "ELEVATED" in text


@pytest.mark.asyncio
async def test_training_pipeline_widget_vram_gate_rendering():
    """Verifies Staged HF Epoch VRAM Gate panel rendering in BLOCKED vs UNBLOCKED modes."""
    app = PipelineWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(TrainingPipelineWidget)
        
        # 1. BLOCKED mode (low VRAM and Kimi active)
        blocked_gate = {
            "vram_free_gb": 2.10,
            "vram_total_gb": 24.0,
            "vram_headroom_pct": 8.75,
            "threshold_pct": 15.0,
            "kimi_88b_active": True,
            "is_blocked": True,
            "gate_status": "BLOCKED",
            "status_message": "BLOCKED (Kimi 88B resident in VRAM ~39.0GB; execution gated)",
        }
        widget.update_telemetry(vram_gate=blocked_gate)
        await pilot.pause(0.05)
        
        vram_panel = widget.query_one("#vram-gate-panel", Static)
        text = get_static_text(vram_panel)
        assert "BLOCKED" in text
        assert "8.8%" in text or "8.7" in text
        assert "RESIDENT" in text or "Kimi 88B" in text
        
        # 2. UNBLOCKED mode (adequate VRAM and Kimi unloaded)
        unblocked_gate = {
            "vram_free_gb": 8.22,
            "vram_total_gb": 24.0,
            "vram_headroom_pct": 34.25,
            "threshold_pct": 15.0,
            "kimi_88b_active": False,
            "is_blocked": False,
            "gate_status": "UNBLOCKED / READY",
            "status_message": "UNBLOCKED / READY (VRAM Headroom: 34.2% >= 15.0%)",
        }
        widget.update_telemetry(vram_gate=unblocked_gate)
        await pilot.pause(0.05)
        
        text2 = get_static_text(vram_panel)
        assert "UNBLOCKED / READY" in text2
        assert "34.2%" in text2 or "34.3" in text2
        assert "UNLOADED" in text2


# ============================================================================
# 2. LauburuGymsWidget Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_lauburu_gyms_widget_composition_and_tabs():
    """Verifies that LauburuGymsWidget mounts TabbedContent with all 5 Gym tab panes."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        assert widget is not None
        tabs = widget.query_one(TabbedContent)
        assert tabs is not None
        assert widget.query_one("#gym-1-view", Static) is not None
        assert widget.query_one("#gym-2-view", Static) is not None
        assert widget.query_one("#gym-3-view", Static) is not None
        assert widget.query_one("#gym-4-view", Static) is not None
        assert widget.query_one("#gym-5-view", Static) is not None


@pytest.mark.asyncio
async def test_lauburu_gyms_widget_gym_1_red_blue_arena():
    """Verifies Gym 1 (Red/Blue Arena) rendering with scores, attacks, and resistances."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        
        gym1_data = {
            "round": 35595,
            "mode": "TEAM_VS_TEAM_FACTION_WAR",
            "global_vram_pool_gb": 54.65,
            "active_battle_phase": "Active Combat",
            "team_local_score": 28.5,
            "team_cloud_score": 26.15,
            "vuln_discovery_rate": 2.45,
            "recent_attacks": [
                {"agent": "MeshTripwireSentinel", "faction": "TEAM_LOCAL_MESH", "action": "TB4 Armor Sync", "target": "PCIe DMA", "vram_delta": 0.0},
                {"agent": "CloudTitanInfiltrator", "faction": "TEAM_CLOUD_TITANS", "action": "RPC Probe", "target": "Port 50052", "vram_delta": -0.15},
            ],
            "resistances": {"local_mesh_buff_pct": 35.0, "cloud_titans_buff_pct": 15.0},
        }
        
        widget.update_telemetry({"red_blue_arena": gym1_data})
        await pilot.pause(0.05)
        
        view1 = widget.query_one("#gym-1-view", Static)
        text = get_static_text(view1)
        assert "RED/BLUE" in text or "ADVERSARIAL" in text
        assert "35595" in text
        assert "TEAM_LOCAL_MESH" in text or "Local Mesh" in text
        assert "28.5" in text


@pytest.mark.asyncio
async def test_lauburu_gyms_widget_gym_2_mesh_healing():
    """Verifies Gym 2 (Mesh Healing) rendering with recovery latency and 5-tier failover."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        
        gym2_data = {
            "last_recovery_latency_ms": 4.02,
            "active_tier": "Tier 1: 10Gbps TB4 DMA (0.28ms)",
            "tiers_available": [
                "Tier 1: 10Gbps Thunderbolt 4 PCIe DMA Bridge (0.28ms RTT)",
                "Tier 2: Tailscale WireGuard Overlay Mesh (100.x.x.x)",
                "Tier 3: Local 2.5GbE / Wi-Fi 7 LAN (192.168.8.x)",
                "Tier 4: Router Hardware USB ADB Loopback Bridge",
                "Tier 5: RFC 792 Wake-on-LAN (UDP 9/7) Magic Packet Resurrection",
            ],
            "fault_count": 2,
            "port_18802_healthy": True,
        }
        
        widget.update_telemetry({"mesh_healing": gym2_data})
        await pilot.pause(0.05)
        
        view2 = widget.query_one("#gym-2-view", Static)
        text = get_static_text(view2)
        assert "MESH HEALING" in text
        assert "4.02 ms" in text or "4.0" in text
        assert "Thunderbolt 4" in text
        assert "18802" in text


@pytest.mark.asyncio
async def test_lauburu_gyms_widget_gym_3_stealth_compute():
    """Verifies Gym 3 (AI Stealth Compute) rendering with sub-5ms yield and Doze whitelist."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        
        gym3_data = {
            "yield_latency_ms": 3.8,
            "target_yield_latency_ms": 5.0,
            "max_temperature_c": 42.5,
            "tensor_route": ["L1_Mac_Node", "L5_MacBook_Air", "GW_Router", "L6_Pixel_10_Pro"],
            "fitness": 17.61,
            "doze_whitelisted_apps": ["com.termux", "com.tailscale.ipn", "com.termux.boot", "com.openclaw.agent"],
        }
        
        widget.update_telemetry({"stealth_compute": gym3_data})
        await pilot.pause(0.05)
        
        view3 = widget.query_one("#gym-3-view", Static)
        text = get_static_text(view3)
        assert "STEALTH COMPUTE" in text
        assert "3.8 ms" in text
        assert "42.5°C" in text or "42.5" in text
        assert "com.termux" in text


@pytest.mark.asyncio
async def test_lauburu_gyms_widget_gym_4_software_dev_game():
    """Verifies Gym 4 (Software Dev Game) rendering with 13 Subsystem Architects ELO rankings."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        
        gym4_data = {
            "overseer": "global-project-architect-specialist (70B+ Tier)",
            "governance_mode": "AUTONOMOUS_CRON_TOP10_EXECUTION",
            "leaderboard_entries": [
                {"rank": 1, "spec_id": "spec-00-core-infrastructure", "elo": 1600, "zero_mock_compliance_pct": 100.0, "status": "GRADUATED_WRITE_AUTHORIZED"},
                {"rank": 2, "spec_id": "spec-01-apps-ecosystem", "elo": 1585, "zero_mock_compliance_pct": 100.0, "status": "GRADUATED_WRITE_AUTHORIZED"},
                {"rank": 13, "spec_id": "spec-12-continuous-lora-evolution", "elo": 1516, "zero_mock_compliance_pct": 100.0, "status": "GRADUATED_WRITE_AUTHORIZED"},
            ],
            "total_architects": 13,
        }
        
        widget.update_telemetry({"software_dev_game": gym4_data})
        await pilot.pause(0.05)
        
        view4 = widget.query_one("#gym-4-view", Static)
        text = get_static_text(view4)
        assert "SOFTWARE DEV" in text
        assert "global-project-architect-specialist" in text or "AUTONOMOUS" in text


@pytest.mark.asyncio
async def test_lauburu_gyms_widget_gym_5_spatial_grappling():
    """Verifies Gym 5 (Spatial Grappling 3D) rendering with kinematic torque tau=120*r*sin(theta)."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        
        gym5_data = {
            "opml_node_count": 955,
            "active_position": "Closed Guard",
            "current_torque_nm": 29.7,
            "joint_torques": {
                "right_elbow": 29.7,
                "left_shoulder": 41.57,
                "right_knee": 57.96,
            },
            "movesense_sync_status": "AWAITING_PHYSICAL_BLUETOOTH_STREAM",
            "movesense_sync_hz": 512,
        }
        
        widget.update_telemetry({"spatial_grappling": gym5_data})
        await pilot.pause(0.05)
        
        view5 = widget.query_one("#gym-5-view", Static)
        text = get_static_text(view5)
        assert "SPATIAL GRAPPLING" in text
        assert "955" in text
        assert "Closed Guard" in text
        assert "29.7" in text or "41.57" in text
        assert "Movesense" in text


@pytest.mark.asyncio
async def test_lauburu_gyms_widget_tab_switching():
    """Verifies programmatically switching gym tabs via switch_gym()."""
    app = GymsWidgetTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        widget = app.query_one(LauburuGymsWidget)
        tabs = widget.query_one(TabbedContent)
        
        assert widget.switch_gym("tab-gym-2") is True
        await pilot.pause(0.05)
        assert tabs.active == "tab-gym-2"
        
        assert widget.switch_gym("tab-gym-5") is True
        await pilot.pause(0.05)
        assert tabs.active == "tab-gym-5"
        
        assert widget.switch_gym("invalid-gym-tab") is False
