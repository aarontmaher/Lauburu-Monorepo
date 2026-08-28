"""
Unit Tests for the 4 Finalized Architectural Paradigms (Screen 6 / Training Screen)
tests/unit/test_training_architectural_paradigms.py

Verifies:
  1. Native Async Integration: pure asyncio routines, async collector methods, reactive property updates.
  2. DSP Ecosystem (NumPy / SciPy): Vectorized kinematics tau = 120.0 * r * |sin(theta)| & scipy.signal.medfilt.
  3. Mesh Healing Gym (Tailscale Local IPC): aiohttp.UnixConnector (/var/run/tailscale/tailscaled.sock) with clean fallback (Rule #0).
  4. Subprocess Orchestration: asyncio.create_subprocess_exec non-blocking stdout/stderr stream capture.
"""

import os
import sys
import math
import asyncio
import tempfile
import pytest
import numpy as np
import scipy.signal
import aiohttp
from aiohttp import web
from textual.app import App, ComposeResult
from textual.widgets import Static

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from backend.training_telemetry_collector import (
    calculate_kinematic_torque,
    calculate_kinematic_torque_series,
    filter_biometrics_dsp_signal,
    fetch_tailscale_localapi_status,
    capture_subprocess_stream,
    stream_red_blue_arena_logs,
    stream_stealth_compute_traces,
    async_get_ingestion_loop_telemetry,
    async_get_gatekeeper_telemetry,
    async_get_hf_epoch_vram_gate,
    async_get_mesh_healing_telemetry,
    async_get_all_gyms_telemetry,
    get_spatial_grappling_telemetry,
    get_mesh_healing_telemetry,
    training_telemetry_collector,
)
from widgets.training_pipeline_widget import TrainingPipelineWidget
from widgets.lauburu_gyms_widget import LauburuGymsWidget


def get_static_text(static_widget: Static) -> str:
    """Helper to extract full text and title from a Static widget's rendered Rich renderable."""
    renderable = static_widget.render()
    panel = getattr(renderable, "_renderable", renderable)
    title = str(getattr(panel, "title", ""))
    content = str(getattr(panel, "renderable", panel))
    return f"{title} {content}"


# ============================================================================
# 1. DSP Ecosystem (NumPy & SciPy) Unit Tests
# ============================================================================

def test_numpy_kinematic_torque_scalar():
    """Verify NumPy-based torque calculation tau = 120 * r * |sin(theta)|."""
    # r = 0.5m, theta = 90 deg -> 120 * 0.5 * 1.0 = 60.0 Nm
    tau_90 = calculate_kinematic_torque(0.5, 90.0, force_n=120.0)
    assert tau_90 == 60.0

    # r = 0.35m, theta = 45 deg -> 120 * 0.35 * sin(45) = 29.7 Nm
    tau_45 = calculate_kinematic_torque(0.35, 45.0, force_n=120.0)
    assert pytest.approx(tau_45, 0.01) == 29.70

    # r = 0.40m, theta = 0 deg -> 0.0 Nm
    tau_0 = calculate_kinematic_torque(0.40, 0.0, force_n=120.0)
    assert tau_0 == 0.0


def test_numpy_kinematic_torque_series_vectorized():
    """Verify vectorized array torque calculation across angular position series."""
    lever_arms = np.array([0.35, 0.40, 0.50, 0.20], dtype=np.float64)
    angles_deg = np.array([45.0, 60.0, 75.0, 20.0], dtype=np.float64)

    torques = calculate_kinematic_torque_series(lever_arms, angles_deg, force_n=120.0)
    assert isinstance(torques, np.ndarray)
    assert len(torques) == 4

    # Check right elbow (0.35m, 45 deg): 120 * 0.35 * sin(45) = 29.70 Nm
    assert pytest.approx(torques[0], 0.01) == 29.70
    # Check left shoulder (0.40m, 60 deg): 120 * 0.40 * sin(60) = 41.57 Nm
    assert pytest.approx(torques[1], 0.01) == 41.57
    # Check right knee (0.50m, 75 deg): 120 * 0.50 * sin(75) = 57.96 Nm
    assert pytest.approx(torques[2], 0.01) == 57.96
    # Check cervical spine (0.20m, 20 deg): 120 * 0.20 * sin(20) = 8.21 Nm
    assert pytest.approx(torques[3], 0.01) == 8.21


def test_scipy_signal_medfilt_biometrics_filtering():
    """Verify SciPy median filter eliminates transient spike noise from IMU/ECG biometrics."""
    # Signal with single spike noise at index 3
    raw_signal = np.array([1.0, 1.0, 1.0, 99.0, 1.0, 1.0, 1.0], dtype=np.float64)
    filtered = filter_biometrics_dsp_signal(raw_signal, kernel_size=3)

    assert isinstance(filtered, np.ndarray)
    assert len(filtered) == 7
    # Spike at index 3 should be filtered down to 1.0
    assert filtered[3] == 1.0

    # Empty array handling
    assert len(filter_biometrics_dsp_signal([], kernel_size=3)) == 0


def test_spatial_grappling_telemetry_dsp_integration():
    """Verify Spatial Grappling collector outputs NumPy array torques and filtered biometrics."""
    res = get_spatial_grappling_telemetry()
    assert "torques_array" in res
    assert isinstance(res["torques_array"], list)
    assert "dsp_filtered_accel_g" in res
    assert res["dsp_filtered_accel_g"] > 0.0


# ============================================================================
# 2. Mesh Healing Gym (Tailscale Local IPC via aiohttp & UnixConnector)
# ============================================================================

@pytest.mark.asyncio
async def test_tailscale_localapi_unmounted_socket_fallback():
    """Verify clean zero-mock fallback when /var/run/tailscale/tailscaled.sock is absent."""
    non_existent = "/tmp/non_existent_tailscale_socket.sock"
    res = await fetch_tailscale_localapi_status(socket_path=non_existent)

    assert isinstance(res, dict)
    assert res["connected"] is False
    assert res["backend_state"] == "OFFLINE_OR_UNMOUNTED"
    assert res["peers_count"] == 0
    assert res["self_hostname"] == "--"


@pytest.mark.asyncio
async def test_tailscale_localapi_unix_socket_mock_server():
    """Verify aiohttp.UnixConnector successfully communicates over a real Unix domain socket."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = os.path.join(tmpdir, "mock_tailscaled.sock")

        # Create mock Tailscale localapi aiohttp app
        app = web.Application()
        async def handle_status(request):
            return web.json_response({
                "BackendState": "Running",
                "Self": {
                    "HostName": "Mac_Node_M4",
                    "TailscaleIPs": ["100.119.199.76"],
                },
                "Peer": {
                    "node-1": {"HostName": "MacBook_Pro"},
                    "node-2": {"HostName": "Linux_Head_Node"},
                },
                "MagicDNSSuffix": "lauburu-mesh.ts.net",
            })
        app.router.add_get("/localapi/v0/status", handle_status)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.UnixSite(runner, sock_path)
        await site.start()

        try:
            res = await fetch_tailscale_localapi_status(socket_path=sock_path)
            assert res["connected"] is True
            assert res["backend_state"] == "Running"
            assert res["self_hostname"] == "Mac_Node_M4"
            assert res["peers_count"] == 2
            assert "100.119.199.76" in res["tailscale_ips"]
        finally:
            await runner.cleanup()


@pytest.mark.asyncio
async def test_mesh_healing_telemetry_with_tailscale_ipc():
    """Verify Mesh Healing collector incorporates Tailscale Local IPC status."""
    res = await async_get_mesh_healing_telemetry()
    assert "tailscale_ipc" in res
    assert "connected" in res["tailscale_ipc"]
    assert "backend_state" in res["tailscale_ipc"]


# ============================================================================
# 3. Subprocess Orchestration (asyncio.create_subprocess_exec)
# ============================================================================

@pytest.mark.asyncio
async def test_asyncio_create_subprocess_exec_capture():
    """Verify non-blocking stdout stream capture using asyncio.create_subprocess_exec."""
    cmd = [sys.executable, "-c", "import sys; print('LINE 1'); print('LINE 2'); sys.stdout.flush()"]
    lines = await capture_subprocess_stream(cmd, max_lines=5, timeout_sec=2.0)

    assert len(lines) == 2
    assert lines[0] == "LINE 1"
    assert lines[1] == "LINE 2"


@pytest.mark.asyncio
async def test_stream_red_blue_arena_logs():
    """Verify Red/Blue arena stream capture routine."""
    lines = await stream_red_blue_arena_logs(max_lines=5)
    assert isinstance(lines, list)
    assert len(lines) >= 1


@pytest.mark.asyncio
async def test_stream_stealth_compute_traces():
    """Verify Stealth Compute stream capture routine."""
    lines = await stream_stealth_compute_traces(max_lines=5)
    assert isinstance(lines, list)
    assert len(lines) >= 1


# ============================================================================
# 4. Native Async Integration & Reactive Properties
# ============================================================================

@pytest.mark.asyncio
async def test_async_collector_methods():
    """Verify pure asyncio collector methods return valid telemetry structures."""
    ingestion = await async_get_ingestion_loop_telemetry()
    assert isinstance(ingestion, dict)
    assert "file_size_bytes" in ingestion

    gatekeeper = await async_get_gatekeeper_telemetry()
    assert isinstance(gatekeeper, dict)
    assert "lock_state" in gatekeeper

    vram = await async_get_hf_epoch_vram_gate()
    assert isinstance(vram, dict)
    assert "is_blocked" in vram

    all_gyms = await async_get_all_gyms_telemetry()
    assert isinstance(all_gyms, dict)
    assert "spatial_grappling" in all_gyms


class ReactiveTestApp(App):
    def compose(self) -> ComposeResult:
        yield TrainingPipelineWidget(id="test-pipeline")
        yield LauburuGymsWidget(id="test-gyms")


@pytest.mark.asyncio
async def test_reactive_variable_dom_repainting():
    """Verify Textual reactive variable assignment triggers instant repaint without thread locks."""
    app = ReactiveTestApp()
    async with app.run_test(size=(140, 40)) as pilot:
        p_widget = app.query_one(TrainingPipelineWidget)
        g_widget = app.query_one(LauburuGymsWidget)

        # Update reactive property directly
        p_widget.ingestion_data = {
            "file_size_mb": 99.99,
            "record_count": 54321,
            "primary_dataset_path": "reactive_test.jsonl",
            "primary_dataset_exists": True,
            "growth_rate_bps": 50.0,
            "growth_rate_records_per_min": 10.0,
        }
        await pilot.pause(0.05)

        ingestion_panel = p_widget.query_one("#ingestion-panel", Static)
        text = get_static_text(ingestion_panel)
        assert "99.99 MB" in text or "99.9" in text
        assert "54,321" in text or "54321" in text

        # Update Gyms reactive property
        g_widget.gyms_data = {
            "spatial_grappling": {
                "opml_node_count": 955,
                "active_position": "Apex Back Control",
                "current_torque_nm": 78.5,
                "joint_torques": {"right_knee": 78.5},
            }
        }
        await pilot.pause(0.05)

        view5 = g_widget.query_one("#gym-5-view", Static)
        text5 = get_static_text(view5)
        assert "Apex Back Control" in text5
        assert "78.5" in text5
