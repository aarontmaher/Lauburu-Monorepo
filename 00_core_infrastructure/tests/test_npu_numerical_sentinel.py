#!/usr/bin/env python3
"""
Unit tests for NpuNumericalSentinel (00_core_infrastructure)
Compliant with Rule 0 (Zero-Mock), Rule 1 (Tri-Proof), Rule 3 (RAM Sanctuary).
"""

import pytest
import sys
from pathlib import Path

INFRA_ROOT = Path(__file__).resolve().parent.parent
if str(INFRA_ROOT) not in sys.path:
    sys.path.insert(0, str(INFRA_ROOT))

from npu_numerical_sentinel import (
    NpuNumericalSentinel,
    HardwareTelemetryVector,
    default_numerical_sentinel
)


class TestNpuNumericalSentinel:
    def setup_method(self):
        self.sentinel = NpuNumericalSentinel()

    def test_elo_calculation_speed_and_accuracy(self):
        res = self.sentinel.calculate_elo_update(1500.0, 1500.0, 1.0)
        assert res["r_a_old"] == 1500.0
        assert res["r_a_new"] == 1551.0  # +16 delta + 35 bonus
        assert res["delta"] == 16.0
        assert res["incentive_bonus"] == 35.0
        assert res["latency_us"] < 200.0  # Sub-millisecond
        assert res["host_ram_mb"] == 0.0

    def test_live_telemetry_collection(self):
        vec = self.sentinel.collect_live_telemetry()
        assert vec.host_ram_free_gb > 0.0
        assert vec.host_ram_total_gb > 0.0
        assert 0.0 <= vec.cpu_percent <= 100.0
        assert vec.disk_free_gb > 0.0

    def test_ram_sanctuary_breach_detection(self):
        # Craft vector breaching Rule 3 (Sanctuary < 4.0 GB)
        breach_vec = HardwareTelemetryVector(
            host_ram_free_gb=3.2,  # < 4.0 GB
            host_ram_total_gb=24.0,
            host_ram_used_pct=81.2,
            cpu_percent=30.0,
            disk_free_gb=100.0,
            tb4_rtt_ms=0.28,
            packet_loss_pct=0.0,
            temperature_c=45.0,
            ane_tops_saturation=90.0,
            gpu_load_pct=0.0,
            active_daemons=4,
            open_sockets=10
        )
        report = self.sentinel.evaluate_telemetry_anomaly(breach_vec)
        assert report.sanctuary_ok is False
        assert report.evacuation_required is True
        assert any("RULE-3-BREACH" in flag for flag in report.anomalies_flagged)

    def test_ram_sanctuary_nominal_state(self):
        # Craft nominal vector
        nominal_vec = HardwareTelemetryVector(
            host_ram_free_gb=12.0,  # >= 9.6 GB
            host_ram_total_gb=24.0,
            host_ram_used_pct=50.0,
            cpu_percent=20.0,
            disk_free_gb=100.0,
            tb4_rtt_ms=0.28,
            packet_loss_pct=0.0,
            temperature_c=40.0,
            ane_tops_saturation=90.0,
            gpu_load_pct=0.0,
            active_daemons=4,
            open_sockets=10
        )
        report = self.sentinel.evaluate_telemetry_anomaly(nominal_vec)
        assert report.sanctuary_ok is True
        assert report.evacuation_required is False

    def test_metrics_tracking(self):
        self.sentinel.calculate_elo_update(1500.0, 1500.0, 1.0)
        self.sentinel.evaluate_telemetry_anomaly()
        metrics = self.sentinel.get_metrics()
        assert metrics["total_evaluations"] >= 1
        assert metrics["total_elo_updates"] >= 1
        assert metrics["host_ram_footprint_mb"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
