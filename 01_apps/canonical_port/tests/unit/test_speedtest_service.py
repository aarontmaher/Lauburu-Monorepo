"""
Unit Tests for Speedtest Service & Network Tab Widgets
Version: 3.0.0-CANONICAL
Tests multi-engine speedtest execution, streaming progress callbacks,
cancellation token aborts, and TUI speedtest & router widgets.
"""

import pytest
import asyncio
import json
import threading
from unittest.mock import patch, MagicMock
from tui.services.speedtest_service import SpeedtestService, speedtest_service
from tui.models.network_telemetry import (
    InternetSpeedMetrics,
    SpeedtestState,
    RouterSystemInfo,
)
from tui.widgets.live_speedtest_card import LiveSpeedtestCard
from tui.widgets.router_control_card import RouterControlCard


class TestSpeedtestService:
    """Test suite for SpeedtestService."""

    def test_speedtest_service_initialization(self):
        st = SpeedtestService(default_duration_sec=3)
        assert st.default_duration_sec == 3
        state = st.get_current_state()
        assert state.stage == "IDLE"
        assert state.is_running is False

    def test_parse_network_quality_json_standard(self):
        sample = {
            "base_rtt": 12.45,
            "dl_throughput": 482500000,
            "ul_throughput": 48000000,
            "responsiveness": 1420,
        }
        metrics = SpeedtestService.parse_network_quality_json(sample)
        assert metrics.download_mbps == 482.5
        assert metrics.upload_mbps == 48.0
        assert metrics.responsiveness_rpm == 1420
        assert metrics.latency_ms == 12.45
        assert metrics.to_dict()["download_mbps"] == 482.5

    def test_parse_network_quality_json_bytes_fallback(self):
        sample = {
            "base_rtt": 15.0,
            "dl_bytes_transferred": 125000000,
            "dl_phase_duration": 2.0,
            "ul_bytes_transferred": 12500000,
            "ul_phase_duration": 2.0,
            "responsiveness": 950,
        }
        metrics = SpeedtestService.parse_network_quality_json(sample)
        # 125MB * 8 / 2s = 500 Mbps
        assert metrics.download_mbps == 500.0
        # 12.5MB * 8 / 2s = 50 Mbps
        assert metrics.upload_mbps == 50.0
        assert metrics.responsiveness_rpm == 950

    def test_run_speedtest_progress_callback(self):
        st = SpeedtestService()
        progress_events = []

        def _callback(stage, mbps, pct):
            progress_events.append((stage, mbps, pct))

        fake_metrics = InternetSpeedMetrics(
            download_mbps=450.0,
            upload_mbps=45.0,
            responsiveness_rpm=1300,
            latency_ms=10.5,
        )

        def _mock_exec(duration_sec=5, progress_callback=None, cancel_token=None):
            if progress_callback:
                progress_callback("INITIALIZING", 0.0, 10.0)
                progress_callback("DOWNLINK", 450.0, 50.0)
                progress_callback("COMPLETED", 450.0, 100.0)
            return fake_metrics

        with patch.object(st, "_execute_network_quality", side_effect=_mock_exec):
            res = st.run_speedtest(progress_callback=_callback, engine="networkQuality", duration_sec=2)
            assert res.download_mbps == 450.0
            assert len(progress_events) >= 1
            assert st.get_current_state().stage == "COMPLETED"

    def test_speedtest_cancellation_token(self):
        st = SpeedtestService()
        cancel_token = threading.Event()
        cancel_token.set()  # Pre-cancelled

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.kill = MagicMock()
        mock_proc.wait = MagicMock()

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(InterruptedError):
                st.run_speedtest(cancel_token=cancel_token, engine="networkQuality")

        assert st.get_current_state().stage == "CANCELLED"

    def test_cancel_active_speedtest_method(self):
        st = SpeedtestService()
        mock_proc = MagicMock()
        st._active_process = mock_proc
        res = st.cancel_active_speedtest()
        assert res is True
        mock_proc.kill.assert_called_once()
        assert st.get_current_state().stage == "CANCELLED"

    def test_speedtest_error_handling(self):
        st = SpeedtestService()
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = ("", "network interface down")

        with patch("subprocess.Popen", return_value=mock_proc):
            with pytest.raises(RuntimeError) as exc_info:
                st.run_speedtest(engine="networkQuality")
            assert "networkQuality failed" in str(exc_info.value)
            assert st.get_current_state().stage == "ERROR"

    @pytest.mark.asyncio
    async def test_async_run_speedtest(self):
        st = SpeedtestService()
        fake_metrics = InternetSpeedMetrics(
            download_mbps=500.0,
            upload_mbps=50.0,
            responsiveness_rpm=1500,
            latency_ms=8.0,
        )
        with patch.object(st, "run_speedtest", return_value=fake_metrics):
            res = await st.async_run_speedtest()
            assert res.download_mbps == 500.0
            assert res.responsiveness_rpm == 1500

    def test_run_lan_iperf3_success(self):
        st = SpeedtestService()
        sample_iperf_json = json.dumps({
            "end": {
                "sum_sent": {"bits_per_second": 940000000},
                "sum_received": {"bits_per_second": 935000000},
            }
        })
        with patch("shutil.which", return_value="/usr/local/bin/iperf3"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=sample_iperf_json, stderr="")
            res = st.run_lan_iperf3(router_ip="192.168.8.1", duration_sec=2)
            assert res["status"] == "SUCCESS"
            assert res["tx_mbps"] == 940.0
            assert res["rx_mbps"] == 935.0

    def test_run_lan_iperf3_missing_binary(self):
        st = SpeedtestService()
        with patch("shutil.which", return_value=None):
            res = st.run_lan_iperf3(router_ip="192.168.8.1")
            assert res["status"] == "UNAVAILABLE"


class TestNetworkWidgets:
    """Test suite for LiveSpeedtestCard and RouterControlCard."""

    def test_live_speedtest_card_render_and_update(self):
        card = LiveSpeedtestCard()
        assert card.state.stage == "IDLE"

        # Test progress update
        card.update_progress("DOWNLINK", 350.0, 45.0)
        assert card.state.stage == "DOWNLINK"
        assert card.state.percent == 45.0
        assert card.state.is_running is True

        # Test metrics update
        new_metrics = InternetSpeedMetrics(
            download_mbps=512.0,
            upload_mbps=52.4,
            responsiveness_rpm=1600,
            latency_ms=9.8,
        )
        card.update_metrics(new_metrics)
        assert card.state.stage == "COMPLETED"
        assert card.state.download_mbps == 512.0
        assert card.state.upload_mbps == 52.4
        assert card.state.responsiveness_rpm == 1600
        assert card.state.is_running is False

    def test_router_control_card_render_and_update(self):
        info = RouterSystemInfo(
            model="GL-MT3600BE",
            hostname="GL-MT3600BE",
            status="ONLINE",
            uptime=123456,
            uptime_formatted="1d 10h 17m 36s",
        )
        card = RouterControlCard(router_info=info)
        assert card.router_info.model == "GL-MT3600BE"
        assert card.router_info.status == "ONLINE"

        updated_info = RouterSystemInfo(
            model="GL-MT3600BE",
            status="DEGRADED",
        )
        card.update_router_info(updated_info)
        assert card.router_info.status == "DEGRADED"
