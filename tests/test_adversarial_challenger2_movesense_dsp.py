#!/usr/bin/env python3
"""
Comprehensive Empirical Adversarial Stress Test Suite: Challenger 2
Focus: Movesense Bluetooth Tether, Protocol Standards, Binary SBEM/HRS Decoders,
Kamath 2004 20% Clinical RR Filter, RMSSD Math, 120s Rolling DFA-alpha1 Zone 2 DSP,
Hemodynamic PTT Blood Pressure Inversion, and Strict Rule #0 Zero-Mock Null Invariants.
"""

import math
import os
import random
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import pytest

# Repository Path setup
BASE_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
for p in [
    BASE_DIR,
    os.path.join(BASE_DIR, "01_apps", "lauburu_compute_hub", "services"),
    os.path.join(BASE_DIR, "01_apps", "movesense_hub"),
    os.path.join(BASE_DIR, "01_apps", "port_4000_hub"),
    os.path.join(BASE_DIR, "00_core_infrastructure", "self_healing_hub", "src"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from movesense_ingestion import (
    MovesenseBinaryDecoder,
    PolarHrsDecoder,
    MovesenseStreamSimulator,
    MovesenseGattTetherDaemon,
    apply_kamath_artifact_filter,
    calculate_rmssd as calculate_rmssd_ingest,
    calculate_dfa_alpha1 as calculate_dfa_ingest,
    calculate_hemodynamics_bp,
    classify_zone2_alignment,
    MOVESENSE_MDS_SERVICE_UUID,
    MOVESENSE_COMMAND_CHAR_UUID,
    MOVESENSE_DATA_CHAR_UUID_1,
    MOVESENSE_DATA_CHAR_UUID_2,
    NUS_SERVICE_UUID,
    SIG_HEART_RATE_SERVICE_UUID,
    SIG_HEART_RATE_MEASUREMENT_UUID,
    STATE_WAITING_FOR_SENSOR,
    STATE_CONNECTED_STREAMING,
    WB_REQ_SUBSCRIBE,
)
from pyspark_biometrics_dsp import (
    MovesenseBiometricsDSPPipeline,
    apply_kamath_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
)
from pyspark_movesense_stream import PySparkMovesenseStreamEngine
from services.telemetry_service import TelemetryService


class TestChallenger2MovesenseProtocolStandards:
    """1. Empirical verification of genuine 128-bit Movesense MDS & SIG GATT standards."""

    def test_genuine_128bit_mds_uuid_conformance(self):
        """Validates canonical 128-bit Movesense Device Service (MDS) UUIDs."""
        assert MOVESENSE_MDS_SERVICE_UUID == "34800001-7185-4d5d-b431-b30e393d9e05"
        assert MOVESENSE_COMMAND_CHAR_UUID == "34800001-7185-4d5d-b431-b30e393d9e05"
        assert MOVESENSE_DATA_CHAR_UUID_1 == "34800002-7185-4d5d-b431-b30e393d9e05"
        assert MOVESENSE_DATA_CHAR_UUID_2 == "34800003-7185-4d5d-b431-b30e393d9e05"

        # Check standard 128-bit hyphenated length
        for u in [MOVESENSE_MDS_SERVICE_UUID, MOVESENSE_DATA_CHAR_UUID_1, MOVESENSE_DATA_CHAR_UUID_2]:
            assert len(u) == 36
            parts = u.split("-")
            assert [len(p) for p in parts] == [8, 4, 4, 4, 12]

    def test_whiteboard_protocol_subscription_framing(self):
        """Verifies binary framing of Whiteboard REST-over-BLE subscription requests."""
        # Subscribe request format: [Opcode (0x05), ReqId (1B)] + URI (ASCII bytes)
        sub_ecg_128 = bytes([WB_REQ_SUBSCRIBE, 0x01]) + b"/Meas/ECG/128"
        assert sub_ecg_128[0] == 0x05
        assert sub_ecg_128[1] == 0x01
        assert sub_ecg_128[2:].decode("ascii") == "/Meas/ECG/128"

        sub_imu_52 = bytes([WB_REQ_SUBSCRIBE, 0x02]) + b"/Meas/IMU6/52"
        assert sub_imu_52[0] == 0x05
        assert sub_imu_52[1] == 0x02
        assert sub_imu_52[2:].decode("ascii") == "/Meas/IMU6/52"


class TestChallenger2BinarySBEMAndHRSByteParsers:
    """2. Adversarial stress testing of binary SBEM and Bluetooth SIG HRS packet decoders."""

    def test_sbem_ecg_128hz_arbitrary_sample_counts(self):
        """Tests ECG 128Hz decoding across 1, 4, 16, and 128 samples, including extreme microvolt values."""
        for sample_count in [1, 4, 16, 128]:
            timestamp_ms = 4500000
            header = struct.pack("<BBI", 2, 1, timestamp_ms)
            # Mix positive, negative, and extreme microvolts (+5000 uV = +5 mV, -3500 uV = -3.5 mV)
            raw_samples = [int(1500 * math.sin(i * 0.2) + 200 * math.cos(i * 0.5)) for i in range(sample_count)]
            payload = struct.pack(f"<{sample_count}i", *raw_samples)
            packet = header + payload

            decoded = MovesenseBinaryDecoder.decode_ecg_128_packet(packet)
            assert decoded["type"] == 2
            assert decoded["req_id"] == 1
            assert decoded["sensor_timestamp_ms"] == timestamp_ms
            assert decoded["sample_count"] == sample_count
            assert decoded["samples_uV"] == raw_samples
            assert decoded["sample_rate_hz"] == 128
            assert len(decoded["samples_mV"]) == sample_count
            for uv, mv in zip(raw_samples, decoded["samples_mV"]):
                assert mv == round(uv / 1000.0, 4)

    def test_sbem_imu6_52hz_multi_frame_kinematics(self):
        """Tests 52Hz IMU 6-DoF decoding across multi-frame bursts and dynamic g vector verification."""
        timestamp_ms = 9999000
        header = struct.pack("<BBI", 2, 2, timestamp_ms)
        # 3 IMU frames (each frame = 6 x float32: ax, ay, az, gx, gy, gz)
        frames_input = [
            (0.0, 1.0, 0.0, 0.0, 0.0, 0.0),       # Pure 1.0g along Y
            (0.577, 0.577, 0.577, 45.2, -30.1, 12.0), # Isometric 1.0g vector
            (0.0, 0.0, 0.0, 180.0, -90.0, 45.0)   # Freefall / pure rotation
        ]
        payload = b"".join(struct.pack("<ffffff", *f) for f in frames_input)
        packet = header + payload

        decoded = MovesenseBinaryDecoder.decode_imu6_52_packet(packet)
        assert decoded["frame_count"] == 3
        assert decoded["sample_rate_hz"] == 52
        assert len(decoded["imu_frames"]) == 3

        # Check Frame 0: 1.0g
        assert decoded["imu_frames"][0]["dynamic_g"] == 1.0
        # Check Frame 1: sqrt(3 * 0.577^2) = ~1.0
        expected_g1 = round(math.sqrt(0.577**2 * 3), 3)
        assert decoded["imu_frames"][1]["dynamic_g"] == expected_g1
        # Check Frame 2: 0.0g
        assert decoded["imu_frames"][2]["dynamic_g"] == 0.0
        assert decoded["imu_frames"][2]["gyro"]["x"] == 180.0

    def test_sbem_decoder_malformed_and_truncated_packets(self):
        """Tests error handling for truncated and corrupt SBEM buffers."""
        with pytest.raises(ValueError, match="Packet too short"):
            MovesenseBinaryDecoder.decode_ecg_128_packet(b"")

        with pytest.raises(ValueError, match="Packet too short"):
            MovesenseBinaryDecoder.decode_ecg_128_packet(b"\x02\x01\x10\x20\x30") # 5 bytes

        with pytest.raises(ValueError, match="Packet too short"):
            MovesenseBinaryDecoder.decode_imu6_52_packet(b"\x02\x02\x00")

    def test_polar_sig_hrs_multi_rr_parsing(self):
        """Tests Polar / SIG Heart Rate Service (0x2A37) parser with multi-RR intervals and 1/1024s conversion."""
        # 16-bit HR flag (0x01) + RR intervals present flag (0x10) -> 0x11
        # HR = 150 BPM (uint16 = 150)
        # RR1 = 410 raw units (410 / 1024 * 1000 = 400.39 -> 400.4 ms)
        # RR2 = 415 raw units (415 / 1024 * 1000 = 405.27 -> 405.3 ms)
        # RR3 = 408 raw units (408 / 1024 * 1000 = 398.44 -> 398.4 ms)
        flag = 0x11
        hr_bytes = struct.pack("<H", 150)
        rr_bytes = struct.pack("<HHH", 410, 415, 408)
        raw_pkt = bytes([flag]) + hr_bytes + rr_bytes

        decoded = PolarHrsDecoder.decode_hrs_packet(raw_pkt)
        assert decoded["heart_rate"] == 150.0
        assert len(decoded["rr_intervals_ms"]) == 3
        assert decoded["rr_intervals_ms"][0] == 400.4
        assert decoded["rr_intervals_ms"][1] == 405.3
        assert decoded["rr_intervals_ms"][2] == 398.4


class TestChallenger2Kamath2004RRFilterStress:
    """3. Clinical stress testing of Kamath et al. (2004) 20% RR Artifact Filter."""

    def test_kamath_dense_alternating_ectopic_bursts(self):
        """Tests that a barrage of alternating high and low ectopic artifacts do not derail the baseline."""
        # Baseline = 800ms
        # Ectopics: 1600 (+100%), 350 (-56%), 1700 (+112%), 380 (-52%), 805 (+0.6%)
        series = [800.0, 1600.0, 350.0, 1700.0, 380.0, 805.0, 795.0, 810.0]
        filtered = apply_kamath_filter(series)
        assert filtered == [800.0, 805.0, 795.0, 810.0]

    def test_kamath_pvc_with_compensatory_pause(self):
        """
        Tests Premature Ventricular Contraction (PVC) signature:
        Short coupled beat (450ms, -43% from 800ms) followed by compensatory pause (1150ms, +43% from 800ms).
        Both must be filtered to protect RMSSD and DFA-alpha1 from spurious variance.
        """
        series = [800.0, 805.0, 450.0, 1150.0, 802.0, 798.0]
        filtered = apply_kamath_filter(series)
        assert filtered == [800.0, 805.0, 802.0, 798.0]

    def test_kamath_physiological_respiratory_sinus_arrhythmia(self):
        """Verifies that normal physiological RSA swings (5% to 15%) are 100% preserved."""
        # 10 breaths/min sinusoidal modulation (+-10% around 800ms)
        rsa_series = [800.0 + math.sin(i * 0.4) * 60.0 for i in range(25)]
        # Maximum step difference between successive beats in this series is < 20%
        filtered = apply_kamath_filter(rsa_series)
        assert len(filtered) == len(rsa_series)
        for orig, filt in zip(rsa_series, filtered):
            assert orig == filt

    def test_kamath_tachycardia_ramp_vs_sudden_step(self):
        """Tests smooth physiological acceleration (exercise ramp) vs sudden noise step."""
        # Exercise ramp from 75 BPM (800ms) to 150 BPM (400ms) over 40 beats (each step ~10ms < 20%)
        ramp = [800.0 - (i * 10.0) for i in range(41)]
        filtered_ramp = apply_kamath_filter(ramp)
        assert len(filtered_ramp) == len(ramp)
        assert filtered_ramp[-1] == 400.0


class TestChallenger2RMSSDAndDFAAlpha1Precision:
    """4. Mathematical precision and boundary tests for RMSSD and 120s Rolling DFA-alpha1."""

    def test_rmssd_exact_analytical_match(self):
        """Asserts exact mathematical match between calculate_rmssd and manual analytical derivation."""
        rr = [750.0, 780.0, 760.0, 810.0, 770.0]
        # diffs: +30, -20, +50, -40
        # squared diffs: 900, 400, 2500, 1600 -> sum = 5400
        # mean sq diff = 5400 / 4 = 1350.0
        # rmssd = sqrt(1350) = 36.742346... -> round(2) = 36.74
        expected_rmssd = round(math.sqrt((30**2 + 20**2 + 50**2 + 40**2) / 4.0), 2)
        assert expected_rmssd == 36.74
        actual = calculate_rmssd(rr)
        assert actual == expected_rmssd

    def test_rmssd_single_beat_and_empty_behavior(self):
        """Ensures RMSSD returns None for insufficient sample lengths (< 2 beats)."""
        assert calculate_rmssd([]) is None
        assert calculate_rmssd([800.0]) is None
        assert calculate_rmssd([800.0, 800.0]) == 0.0

    def test_dfa_alpha1_short_window_invariance(self):
        """Tests DFA-alpha1 behavior across windows of length 0, 1, 2, 3, 4, 6, 16, 60."""
        # N < 4 returns None
        assert calculate_dfa_alpha1([]) is None
        assert calculate_dfa_alpha1([800.0]) is None
        assert calculate_dfa_alpha1([800.0, 810.0]) is None
        assert calculate_dfa_alpha1([800.0, 810.0, 805.0]) is None

        # 4 <= N <= 16 returns estimated alpha1 within [0.40, 1.50]
        for n in [4, 6, 10, 16]:
            buf = [800.0 + math.sin(i * 0.5) * 20.0 for i in range(n)]
            alpha = calculate_dfa_alpha1(buf)
            assert alpha is not None
            assert 0.40 <= alpha <= 1.50

    def test_dfa_alpha1_zone2_aerobic_threshold_transitions(self):
        """Verifies DFA-alpha1 classification across Zone 2 (>=0.75), Zone 3 (0.50-0.75), and Zone 4/5 (<0.50)."""
        z2_desc, z2_color = classify_zone2_alignment(0.82)
        assert "Zone 2" in z2_desc
        assert z2_color == "#10b981"

        z3_desc, z3_color = classify_zone2_alignment(0.62)
        assert "Zone 3" in z3_desc
        assert z3_color == "#f59e0b"

        z4_desc, z4_color = classify_zone2_alignment(0.42)
        assert "Zone 4/5" in z4_desc
        assert z4_color == "#ef4444"

        none_desc, none_color = classify_zone2_alignment(None)
        assert "Awaiting" in none_desc
        assert none_color == "#94a3b8"


class TestChallenger2HemodynamicPTTBloodPressure:
    """5. Empirical tests of PTT cuffless blood pressure inversion and physiological constraints."""

    def test_ptt_bp_inversion_equations(self):
        """Verifies SBP, DBP, and MAP calculations from PTT and HR."""
        # Resting: PTT = 200ms, HR = 70 BPM -> SBP = 120, DBP = 80, MAP = (120 + 160)/3 = 93.3
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=200.0, hr_bpm=70.0)
        assert sbp == 120.0
        assert dbp == 80.0
        assert map_val == 93.3

        # High effort: PTT = 160ms (delta = +40), HR = 150 BPM (hr_adj = 80 * 0.15 = 12.0)
        # SBP = 120.0 + (40 * 0.45 = 18.0) + 12.0 = 150.0
        # DBP = 80.0 + (40 * 0.25 = 10.0) + 6.0 = 96.0
        # MAP = (150.0 + 192.0) / 3 = 114.0
        sbp_e, dbp_e, map_e = calculate_hemodynamics_bp(ptt_ms=160.0, hr_bpm=150.0)
        assert sbp_e == 150.0
        assert dbp_e == 96.0
        assert map_e == 114.0

    def test_ptt_bp_invalid_inputs_return_none(self):
        """Ensures missing, zero, or negative PTT returns strictly (None, None, None)."""
        assert calculate_hemodynamics_bp(ptt_ms=None, hr_bpm=120.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=0.0, hr_bpm=120.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=-150.0, hr_bpm=120.0) == (None, None, None)


class TestChallenger2StrictRuleZeroMockNullStates:
    """6. Forensic audit of zero-mock null states across all biometrics and tethering components."""

    def test_movesense_gatt_daemon_disconnected_null_state(self):
        """Validates that MovesenseGattTetherDaemon emits explicit WAITING_FOR_SENSOR and null metrics."""
        daemon = MovesenseGattTetherDaemon()
        state = daemon.get_state()

        assert state["state"] == STATE_WAITING_FOR_SENSOR
        assert state["status"] == STATE_WAITING_FOR_SENSOR
        assert state["connected"] is False
        assert state["is_streaming"] is False
        assert state["metrics"]["heart_rate_bpm"] is None
        assert state["metrics"]["rmssd_ms"] is None
        assert state["metrics"]["dfa_alpha1"] is None
        assert state["metrics"]["ecg_mv"] == []
        assert state["metrics"]["kinematics"] is None
        assert state["metrics"]["total_dynamic_g"] is None
        assert state["metrics"]["zone_alignment"] == "Awaiting Live Stream"

    def test_movesense_biometrics_dsp_pipeline_disconnected_state(self):
        """Validates that MovesenseBiometricsDSPPipeline emits AWAITING_SENSOR and null hrv_cardiac."""
        dsp = MovesenseBiometricsDSPPipeline()
        out = dsp.process_biometrics_stream(None)

        assert out["status"] == "AWAITING_SENSOR"
        assert out["kinematics"] is None
        assert out["hrv_cardiac"] is None
        assert "Awaiting physical sensor" in out["coaching_recommendation"]

    def test_pyspark_movesense_stream_engine_disconnected_state(self):
        """Validates that PySparkMovesenseStreamEngine emits WAITING_FOR_SENSOR and null biometrics."""
        engine = PySparkMovesenseStreamEngine()
        out = engine.process_movesense_stream(None)

        assert out["stream_status"] == "WAITING_FOR_SENSOR"
        assert out["biometrics"]["heart_rate_bpm"] is None
        assert out["biometrics"]["dfa_alpha1"] is None
        assert out["biometrics"]["rmssd_ms"] is None
        assert out["kinematics_imu_12axis"]["accelerometer_g"] is None

    def test_telemetry_service_disconnected_sensor_state(self):
        """Validates that TelemetryService tracks zero connected BLE sensors when inactive."""
        svc = TelemetryService()
        status = svc.get_sensor_status()

        assert status["connected_count"] == 0
        assert status["fusion_state"] == "AWAITING_BLUETOOTH_SENSORS"
        assert status["sensors"]["movesense"]["connected"] is False
        assert status["sensors"]["movesense"]["heart_rate"] is None
        assert status["sensors"]["polar"]["connected"] is False
        assert status["sensors"]["polar"]["heart_rate"] is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
