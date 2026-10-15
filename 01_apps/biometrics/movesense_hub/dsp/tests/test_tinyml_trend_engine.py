"""
Unit & Physiological Validation Suite for TinyML Zero-Rejection Movesense Trend Engine
=====================================================================================
Governed by:
- Rule #0: 100% Zero-Mock Compliance
- Rule #1: Tri-Proof Verification
- Verifies:
  1. 0% Data Rejection: Authentic PVCs and PACs are retained in biometric metrics.
  2. Dual-Stream Gating: Distinguishes true ectopic beats from mechanical motion artifacts.
  3. Real-Time Trend Tracking: Accurately computes DFA-alpha1 decay and cardiac drift.
  4. 16-Byte BLE Serialization: Byte-exact packing and unpack verification.
"""

import math
import struct
import sys
from pathlib import Path

DSP_DIR = Path(__file__).resolve().parent.parent
if str(DSP_DIR) not in sys.path:
    sys.path.insert(0, str(DSP_DIR))

from tinyml_trend_engine import (
    TinyMLMovesenseTrendEngine,
    BeatType,
    EdgeTrendSnapshot,
)


class TestTinyMLTrendEngine:

    def test_01_sinus_rhythm_processing(self):
        """Verify normal sinus rhythm produces accurate HR, RMSSD, and Zone 2 DFA-alpha1."""
        engine = TinyMLMovesenseTrendEngine(window_size_beats=60)
        # Feed 60 beats of 857ms (70 BPM) with natural 20ms sinus variability
        base_rr = 857.0
        for i in range(60):
            var = 15.0 * math.sin(i * 0.4)
            rr = base_rr + var
            beat = engine.classify_beat(
                rr_interval_ms=rr,
                imu_accel_g=1.0,
                imu_jerk_g=0.04,
                qrs_duration_ms=85.0,
                timestamp_offset_ms=i * 857.0,
            )
            assert beat.beat_type == BeatType.NORMAL_SINUS
            assert beat.is_sinus is True

        snapshot = engine.evaluate_trend_snapshot(current_time_ms=60 * 857.0)
        assert 68.0 <= snapshot.heart_rate_bpm <= 72.0
        assert snapshot.rmssd_ms > 0.0
        assert snapshot.dfa_alpha1 >= 0.75  # Zone 2 baseline
        assert snapshot.total_beats_processed == 60
        assert snapshot.ectopic_beats_retained == 0
        assert snapshot.signal_quality_sqi_pct == 100.0

    def test_02_zero_rejection_of_ectopic_beats(self):
        """
        CRITICAL MANDATE: Make sure nothing is missed out on, don't reject data for no reason.
        Verify that premature ventricular contractions (PVCs) and PACs are retained,
        counted, and integrated into autonomic trend tracking rather than discarded.
        """
        engine = TinyMLMovesenseTrendEngine(window_size_beats=60)
        # Establish sinus baseline
        for i in range(30):
            engine.classify_beat(
                rr_interval_ms=850.0,
                imu_accel_g=1.0,
                imu_jerk_g=0.02,
                qrs_duration_ms=85.0,
                timestamp_offset_ms=i * 850.0,
            )

        # Inject Premature Ventricular Contraction (PVC):
        # Short coupling interval (520ms, < 0.82 ratio), wide QRS (118ms), NO mechanical shock (jerk=0.03g)
        pvc_beat = engine.classify_beat(
            rr_interval_ms=520.0,
            imu_accel_g=1.0,
            imu_jerk_g=0.03,
            qrs_duration_ms=118.0,
            timestamp_offset_ms=30 * 850.0 + 520.0,
        )
        assert pvc_beat.beat_type == BeatType.PVC
        assert pvc_beat.is_sinus is False
        assert pvc_beat.confidence > 0.85

        # Inject Premature Atrial Contraction (PAC):
        # Short coupling interval (560ms), normal narrow QRS (82ms), NO mechanical shock
        pac_beat = engine.classify_beat(
            rr_interval_ms=560.0,
            imu_accel_g=1.0,
            imu_jerk_g=0.02,
            qrs_duration_ms=82.0,
            timestamp_offset_ms=30 * 850.0 + 1080.0,
        )
        assert pac_beat.beat_type == BeatType.PAC
        assert pac_beat.is_sinus is False

        # Compensatory pause (1150ms)
        engine.classify_beat(
            rr_interval_ms=1150.0,
            imu_accel_g=1.0,
            imu_jerk_g=0.03,
            qrs_duration_ms=88.0,
            timestamp_offset_ms=30 * 850.0 + 2230.0,
        )

        snapshot = engine.evaluate_trend_snapshot(current_time_ms=30000.0)
        # Verify both ectopic beats were retained in the trend tracking metrics
        assert snapshot.ectopic_beats_retained == 2
        assert snapshot.ectopic_density_per_min == 2.0
        assert snapshot.total_beats_processed == 33
        # SQI remains high because these are true cardiac events, not loose strap artifacts
        assert snapshot.signal_quality_sqi_pct == 100.0

    def test_03_motion_artifact_discriminator(self):
        """
        Verify that violent physical movement (jerk > 1.8g) with anomalous interval
        is correctly flagged as MOTION_ARTIFACT to protect HRV metrics from corruption.
        """
        engine = TinyMLMovesenseTrendEngine(window_size_beats=60)
        for i in range(20):
            engine.classify_beat(
                rr_interval_ms=850.0,
                imu_accel_g=1.0,
                imu_jerk_g=0.05,
                qrs_duration_ms=85.0,
                timestamp_offset_ms=i * 850.0,
            )

        # Inject sudden strap slap / combat grapple slam:
        # Extreme short interval (350ms) WITH high IMU jerk (3.4g)
        artifact_beat = engine.classify_beat(
            rr_interval_ms=350.0,
            imu_accel_g=3.8,
            imu_jerk_g=3.4,
            qrs_duration_ms=140.0,
            timestamp_offset_ms=20 * 850.0 + 350.0,
        )
        assert artifact_beat.beat_type == BeatType.MOTION_ARTIFACT
        assert artifact_beat.is_sinus is False

        snapshot = engine.evaluate_trend_snapshot(current_time_ms=20000.0)
        # Ectopic count should NOT increase for mechanical artifacts
        assert snapshot.ectopic_beats_retained == 0
        assert snapshot.signal_quality_sqi_pct < 100.0

    def test_04_cardiac_drift_detection(self):
        """Verify internal-to-external aerobic decoupling (cardiac drift) computation."""
        engine = TinyMLMovesenseTrendEngine(window_size_beats=40)
        # First half: steady 140 BPM at constant 1.2g acceleration
        for i in range(20):
            engine.classify_beat(
                rr_interval_ms=428.5,  # 140 BPM
                imu_accel_g=1.2,
                imu_jerk_g=0.1,
                timestamp_offset_ms=i * 428.5,
            )
        # Second half: cardiac drift! HR rises to 155 BPM while workload stays flat at 1.2g
        for i in range(20, 40):
            engine.classify_beat(
                rr_interval_ms=387.0,  # 155 BPM
                imu_accel_g=1.2,
                imu_jerk_g=0.1,
                timestamp_offset_ms=i * 400.0,
            )

        drift_pct = engine.compute_cardiac_drift()
        # Decoupling should be positive (~9-11%) indicating aerobic drift/fatigue
        assert drift_pct > 5.0
        assert drift_pct < 15.0

    def test_05_16byte_ble_packet_serialization(self):
        """
        Verify that the TinyML Trend snapshot serializes into a byte-exact 16-byte GATT payload
        for ultra-low energy transmission (300+ hr battery life).
        """
        snapshot = EdgeTrendSnapshot(
            heart_rate_bpm=142.0,
            rmssd_ms=34.5,
            dfa_alpha1=0.78,
            alpha1_slope_per_min=-0.0450,
            cardiac_drift_pct=6.85,
            ectopic_density_per_min=1.0,
            parasympathetic_recovery_tau=28.5,
            signal_quality_sqi_pct=98.0,
            training_zone="Zone 2: Aerobic Base (Fat Max)",
            total_beats_processed=1240,
            ectopic_beats_retained=4,
            rule_0_zero_mock=True,
        )

        payload = snapshot.serialize_16byte_ble_payload()
        assert len(payload) == 16
        assert payload[15] == 0xAA  # Guard byte

        # Unpack and verify byte-level fidelity
        unpacked = struct.unpack("<BHh h h B B B B H B", payload)
        hr_unpacked = unpacked[0]
        rmssd_unpacked = unpacked[1] / 10.0
        dfa_unpacked = unpacked[2] / 1000.0
        slope_unpacked = unpacked[3] / 10000.0
        drift_unpacked = unpacked[4] / 100.0
        ectopic_unpacked = unpacked[5]
        sqi_unpacked = unpacked[6]
        zone_unpacked = unpacked[7]
        total_beats_unpacked = unpacked[9]

        assert hr_unpacked == 142
        assert abs(rmssd_unpacked - 34.5) < 0.1
        assert abs(dfa_unpacked - 0.78) < 0.01
        assert abs(slope_unpacked - (-0.0450)) < 0.001
        assert abs(drift_unpacked - 6.85) < 0.01
        assert ectopic_unpacked == 1
        assert sqi_unpacked == 98
        assert zone_unpacked == 2  # Zone 2 code
        assert total_beats_unpacked == 1240
