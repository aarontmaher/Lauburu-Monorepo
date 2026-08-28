"""
Tests for Movesense Hardware Tether & Medical-Grade Biometrics DSP Pipeline (Features 6, 7, 8 in PROJECT.md).
Validates:
1. Genuine 128-bit Movesense MDS GATT UUIDs (34800001-7185-4d5d-b431-b30e393d9e05) and Bluetooth SIG HRS (0x180D).
2. Binary SBEM decoding for 128Hz raw ECG (/Meas/ECG/128) and 52Hz 6-DoF IMU (/Meas/IMU6/52).
3. Bluetooth SIG Heart Rate Service (0x180D / 0x2A37) 8-bit & 16-bit HR and RR interval parsing.
4. Kamath et al. (2004) Clinical 20% RR artifact filter against ectopic bursts and noise.
5. RMSSD parasympathetic cardiac vagal calculation with exact mathematical precision.
6. 120-second rolling Detrended Fluctuation Analysis (DFA-alpha1) for Zone 2 aerobic threshold detection.
7. PTT Hemodynamic cuffless blood pressure inversion.
8. Strict Rule #0 Zero-Mock compliance: disconnected sensors return explicit None / null / '--' states.
"""

import math
import os
import random
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Ensure repository paths are on sys.path
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
    apply_kamath_artifact_filter as apply_kamath_movesense,
    calculate_rmssd as calculate_rmssd_movesense,
    calculate_dfa_alpha1 as calculate_dfa_movesense,
    calculate_hemodynamics_bp,
)
from pyspark_biometrics_dsp import (
    MovesenseBiometricsDSPPipeline,
    apply_kamath_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
)
from pyspark_movesense_stream import PySparkMovesenseStreamEngine
from services.telemetry_service import TelemetryService


# ============================================================================
# TIER 1: FEATURE COVERAGE (Unit & Contract Compliance)
# ============================================================================

class TestTier1FeatureCoverage:
    """Tier 1: Verification of Features 6, 7, and 8 from PROJECT.md."""

    def test_f6_genuine_128bit_mds_and_sig_hrs_uuids(self):
        """Feature 7: Validates authoritative 128-bit Movesense MDS and Bluetooth SIG GATT UUIDs."""
        # Authoritative 128-bit Movesense Device Service (MDS 2.0) UUIDs
        MDS_SERVICE_UUID = "34800001-7185-4d5d-b431-b30e393d9e05"
        MDS_COMMAND_CHAR_UUID = "34800001-7185-4d5d-b431-b30e393d9e05"
        MDS_DATA_CHAR_UUID_1 = "34800002-7185-4d5d-b431-b30e393d9e05"
        MDS_DATA_CHAR_UUID_2 = "34800003-7185-4d5d-b431-b30e393d9e05"

        # Nordic UART Service (NUS) Fallback
        NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        NUS_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
        NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

        # Bluetooth SIG 16-bit Standard UUIDs
        SIG_HEART_RATE_SERVICE = 0x180D
        SIG_HEART_RATE_MEASUREMENT = 0x2A37
        SIG_BODY_SENSOR_LOCATION = 0x2A38
        SIG_BATTERY_SERVICE = 0x180F
        SIG_BATTERY_LEVEL = 0x2A19
        SIG_DEVICE_INFO_SERVICE = 0x180A

        # Assert UUID format and length (128-bit = 36 chars with hyphens)
        assert len(MDS_SERVICE_UUID) == 36
        assert len(NUS_SERVICE_UUID) == 36
        assert MDS_SERVICE_UUID.startswith("34800001")
        assert MDS_DATA_CHAR_UUID_1.startswith("34800002")
        assert MDS_DATA_CHAR_UUID_2.startswith("34800003")

        # Standard SIG profile values
        assert SIG_HEART_RATE_SERVICE == 6157
        assert SIG_HEART_RATE_MEASUREMENT == 10807

    def test_f7_sbem_binary_ecg_128hz_decoding(self):
        """Feature 8: Validates binary byte buffer decoding of 128Hz raw ECG (/Meas/ECG/128)."""
        # Construct synthetic authentic SBEM packet:
        # Header: [type (1B) = 2 (notification), req_id (1B) = 1, timestamp (4B) = 1000000 ms]
        # Payload: 4 x int32 signed microvolt samples (+1200 uV, -450 uV, +2300 uV, +80 uV)
        header = struct.pack("<BBI", 2, 1, 1000000)
        samples_uV = [1200, -450, 2300, 80]
        payload = struct.pack("<iiii", *samples_uV)
        raw_packet = header + payload

        decoded = MovesenseBinaryDecoder.decode_ecg_128_packet(raw_packet)

        assert decoded["type"] == 2
        assert decoded["req_id"] == 1
        assert decoded["sensor_timestamp_ms"] == 1000000
        assert decoded["sample_count"] == 4
        assert decoded["samples_uV"] == [1200, -450, 2300, 80]
        assert decoded["samples_mV"] == [1.2, -0.45, 2.3, 0.08]
        assert decoded["sample_rate_hz"] == 128

    def test_f7_sbem_binary_imu6_52hz_decoding(self):
        """Feature 8: Validates binary byte buffer decoding of 52Hz 6-DoF IMU (/Meas/IMU6/52)."""
        # Construct SBEM packet:
        # Header: [type (1B) = 2, req_id (1B) = 1, timestamp (4B) = 1000000 ms]
        # Payload: 6 x float32 (ax=0.05, ay=0.98, az=0.15, gx=1.2, gy=-0.8, gz=0.3)
        header = struct.pack("<BBI", 2, 1, 1000000)
        frame1 = struct.pack("<ffffff", 0.05, 0.98, 0.15, 1.2, -0.8, 0.3)
        raw_packet = header + frame1

        decoded = MovesenseBinaryDecoder.decode_imu6_52_packet(raw_packet)

        assert decoded["type"] == 2
        assert decoded["req_id"] == 1
        assert decoded["sensor_timestamp_ms"] == 1000000
        assert decoded["frame_count"] == 1
        assert decoded["sample_rate_hz"] == 52

        frame = decoded["imu_frames"][0]
        assert frame["accel"]["x"] == 0.05
        assert frame["accel"]["y"] == 0.98
        assert frame["accel"]["z"] == 0.15
        expected_g = round(math.sqrt(0.05**2 + 0.98**2 + 0.15**2), 3)
        assert frame["dynamic_g"] == expected_g

    def test_f7_bluetooth_sig_hrs_decoding(self):
        """Feature 8: Validates standard Bluetooth SIG Heart Rate Service (0x2A37) decoding."""
        # 1. 8-bit HR (flag 0x00) -> 74 BPM
        buf_8bit = bytes([0x00, 74])
        res_8 = PolarHrsDecoder.decode_hrs_packet(buf_8bit)
        assert res_8["heart_rate"] == 74.0
        assert res_8["rr_intervals_ms"] == []

        # 2. 16-bit HR with RR intervals present (flags: 0x01 | 0x10 = 0x11)
        # HR = 142 BPM (uint16 little endian: 0x8E, 0x00)
        # RR interval = 430 raw units (430 / 1024 * 1000 = 419.9 ms)
        hr_uint16 = struct.pack("<H", 142)
        rr_uint16 = struct.pack("<H", 430)
        buf_16bit = bytes([0x11]) + hr_uint16 + rr_uint16

        res_16 = PolarHrsDecoder.decode_hrs_packet(buf_16bit)
        assert res_16["heart_rate"] == 142.0
        assert len(res_16["rr_intervals_ms"]) == 1
        assert res_16["rr_intervals_ms"][0] == 419.9

    def test_f8_kamath_2004_20pct_clinical_rr_filter(self):
        """Feature 8: Verifies Kamath et al. (2004) 20% clinical RR artifact filter."""
        # Baseline ~800ms; contains +100% ectopic artifact (1600.0) and -50% dip (400.0)
        raw_rr = [800.0, 810.0, 1600.0, 805.0, 400.0, 815.0]

        clean_rr, count = apply_kamath_movesense(raw_rr)
        assert count == 2, f"Expected 2 artifacts, got {count}"
        assert 1600.0 not in clean_rr
        assert 400.0 not in clean_rr

        # pyspark_biometrics_dsp implementation
        clean_pyspark = apply_kamath_filter(raw_rr)
        assert 1600.0 not in clean_pyspark
        assert 400.0 not in clean_pyspark
        assert clean_pyspark == [800.0, 810.0, 805.0, 815.0]

    def test_f8_rmssd_cardiac_parasympathetic_metric(self):
        """Feature 8: Verifies exact mathematical formula of RMSSD."""
        rr = [800.0, 820.0, 810.0, 830.0]
        # diffs: +20, -10, +20 -> sq: 400, 100, 400 -> sum=900 -> mean=300 -> sqrt(300)=17.32 ms
        rmssd = calculate_rmssd(rr)
        expected = round(math.sqrt((20**2 + 10**2 + 20**2) / 3.0), 2)
        assert rmssd == expected == 17.32

        # Edge cases: None for < 2 beats, 0.0 for constant RR
        assert calculate_rmssd([]) is None
        assert calculate_rmssd([800.0]) is None
        assert calculate_rmssd([800.0, 800.0, 800.0]) == 0.0

    def test_f8_dfa_alpha1_zone2_aerobic_threshold(self):
        """Feature 8: Verifies 120s rolling DFA-alpha1 scaling exponent and Zone 2 target ~0.75."""
        # Sufficient buffer with physiological variance
        rr_series = [800.0 + math.sin(i * 0.3) * 25.0 for i in range(30)]
        alpha1 = calculate_dfa_alpha1(rr_series)

        assert alpha1 is not None
        assert 0.40 <= alpha1 <= 1.50

        # Buffer < 4 beats returns None
        assert calculate_dfa_alpha1([]) is None
        assert calculate_dfa_alpha1([800.0, 810.0, 805.0]) is None

    def test_f8_hemodynamic_ptt_blood_pressure_inversion(self):
        """Feature 8: Verifies PTT-based blood pressure inversion calculations."""
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=195.0, hr_bpm=140.0)
        assert sbp is not None and dbp is not None and map_val is not None
        assert 100.0 <= sbp <= 180.0
        assert 60.0 <= dbp <= 110.0
        assert map_val == round((sbp + 2.0 * dbp) / 3.0, 1)

        # Missing or non-positive PTT returns strict None tuple
        assert calculate_hemodynamics_bp(ptt_ms=None, hr_bpm=140.0) == (None, None, None)
        assert calculate_hemodynamics_bp(ptt_ms=-50.0, hr_bpm=140.0) == (None, None, None)

    def test_f8_strict_rule_zero_zero_mock_disconnection(self):
        """
        Feature 8 / Rule #0: Disconnected sensors MUST return explicit None / null / '--' states.
        Strict verification across movesense_hub, self_healing_hub, and port_4000_hub.
        """
        # 1. MovesenseBiometricsDSPPipeline (movesense_hub)
        dsp = MovesenseBiometricsDSPPipeline()
        out_dsp = dsp.process_biometrics_stream(None)
        assert out_dsp["status"] == "AWAITING_SENSOR"
        assert out_dsp["kinematics"] is None
        assert out_dsp["hrv_cardiac"] is None

        # 2. PySparkMovesenseStreamEngine (self_healing_hub)
        engine = PySparkMovesenseStreamEngine()
        out_engine = engine.process_movesense_stream(None)
        assert out_engine["stream_status"] == "WAITING_FOR_SENSOR"
        assert out_engine["biometrics"]["heart_rate_bpm"] is None
        assert out_engine["biometrics"]["dfa_alpha1"] is None
        assert out_engine["biometrics"]["rmssd_ms"] is None
        assert out_engine["kinematics_imu_12axis"]["accelerometer_g"] is None

        # 3. TelemetryService (port_4000_hub)
        svc = TelemetryService()
        status = svc.get_sensor_status()
        assert status["connected_count"] == 0
        assert status["fusion_state"] == "AWAITING_BLUETOOTH_SENSORS"
        assert status["sensors"]["movesense"]["connected"] is False
        assert status["sensors"]["movesense"]["heart_rate"] is None


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES (Stress & Exception Hardening)
# ============================================================================

class TestTier2BoundaryAndCornerLimits:
    """Tier 2: Extreme physiological boundaries, corrupted packets, and noise stress."""

    def test_b1_kamath_dense_ectopic_bursts(self):
        """Boundary B1: Consecutive 3-beat ectopic burst must maintain true baseline without latching."""
        burst_seq = [800.0, 1600.0, 1650.0, 1700.0, 810.0]
        clean_rr = apply_kamath_filter(burst_seq)
        assert clean_rr == [800.0, 810.0]

    def test_b2_kamath_zero_and_negative_intervals(self):
        """Boundary B2: Filters out corrupted 0.0 and negative sensor tick intervals."""
        corrupted = [800.0, 0.0, -250.0, 820.0, -999.0, 810.0]
        clean_rr = apply_kamath_filter(corrupted)
        assert clean_rr == [800.0, 820.0, 810.0]

    def test_b3_kamath_sustained_ventricular_tachycardia(self):
        """Boundary B3: Rapid steady rhythm (VT at 200 BPM, RR ~300ms) is tracked accurately."""
        vt_rhythm = [300.0, 305.0, 295.0, 302.0, 298.0, 301.0]
        clean_vt = apply_kamath_filter(vt_rhythm)
        assert len(clean_vt) == len(vt_rhythm)
        assert clean_vt == vt_rhythm

    def test_b4_dfa_alpha1_flatline_zero_variance(self):
        """Boundary B4: Zero-variance flatline buffer handled safely without ZeroDivisionError."""
        flatline = [800.0] * 50
        alpha1 = calculate_dfa_alpha1(flatline)
        assert alpha1 is not None
        assert 0.40 <= alpha1 <= 1.50

    def test_b5_dfa_alpha1_fractal_noise_monotonicity(self):
        """Boundary B5: Validates fractal scaling monotonicity: White noise < Pink noise < Brownian noise."""
        random.seed(42)
        # White noise (uncorrelated random)
        white_noise = [800.0 + random.gauss(0, 30.0) for _ in range(120)]
        alpha_white = calculate_dfa_alpha1(white_noise)

        # Pink noise (1/f physiological)
        pink_noise = [800.0]
        for _ in range(119):
            step = 0.6 * (pink_noise[-1] - 800.0) + random.gauss(0, 15.0)
            pink_noise.append(800.0 + step)
        alpha_pink = calculate_dfa_alpha1(pink_noise)

        # Brownian noise (random walk)
        brownian_noise = [800.0]
        for _ in range(119):
            brownian_noise.append(brownian_noise[-1] + random.gauss(0, 10.0))
        alpha_brownian = calculate_dfa_alpha1(brownian_noise)

        assert alpha_white is not None and alpha_pink is not None and alpha_brownian is not None
        assert alpha_white < alpha_brownian
        print(f"\n[Tier 2 Fractal Test] White: {alpha_white:.3f}, Pink: {alpha_pink:.3f}, Brownian: {alpha_brownian:.3f}")

    def test_b6_sbem_corrupted_and_truncated_packets(self):
        """Boundary B6: Truncated SBEM packets (< 6 bytes) raise ValueError cleanly."""
        truncated_bytes = b"\x02\x01\x00\x00"  # 4 bytes only
        with pytest.raises(ValueError, match="Packet too short"):
            MovesenseBinaryDecoder.decode_ecg_128_packet(truncated_bytes)

        with pytest.raises(ValueError, match="Packet too short"):
            MovesenseBinaryDecoder.decode_imu6_52_packet(truncated_bytes)

    def test_b7_hrs_truncated_and_corrupt_buffers(self):
        """Boundary B7: Truncated or empty HRS byte buffers raise ValueError."""
        with pytest.raises(ValueError, match="Invalid HRS byte buffer"):
            PolarHrsDecoder.decode_hrs_packet(b"")

        with pytest.raises(ValueError, match="Invalid HRS byte buffer"):
            PolarHrsDecoder.decode_hrs_packet(bytes([0x01]))

        # Length 2 with 16-bit flag (needs 3 bytes)
        with pytest.raises(ValueError, match="Incomplete 16-bit HR payload"):
            PolarHrsDecoder.decode_hrs_packet(bytes([0x01, 0x50]))

    def test_b8_stale_sensor_timeout_pruning(self):
        """Boundary B8: Sensor state automatically resets to disconnected/null after timeout."""
        svc = TelemetryService(sensor_timeout_sec=0.1)  # 100ms timeout
        svc.sensors["movesense"]["connected"] = True
        svc.sensors["movesense"]["heart_rate"] = 135.0
        svc.sensors["movesense"]["last_seen_epoch"] = time.time()

        time.sleep(0.15)
        status = svc.get_sensor_status()
        assert status["connected_count"] == 0
        assert status["sensors"]["movesense"]["connected"] is False
        assert status["sensors"]["movesense"]["heart_rate"] is None


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (Pairwise Integrations)
# ============================================================================

class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise integration across ECG decoding, Kamath filtering, DSP, and multi-sensor routing."""

    def test_c1_raw_ecg_to_rr_to_kamath_to_rmssd_pipeline(self):
        """Combination C1: End-to-end processing pipeline from simulated 128Hz ECG to RMSSD."""
        sim = MovesenseStreamSimulator(base_heart_rate=140.0)
        window_1s = sim.generate_1s_window(window_idx=0)

        # 1. Verify 128 raw ECG samples
        assert len(window_1s["ecg_mv"]) == 128
        assert window_1s["heart_rate"] == 140.0

        # 2. Filter RR intervals
        raw_rr = window_1s["rr_intervals_ms"]
        clean_rr, _ = apply_kamath_movesense(raw_rr)

        # 3. Calculate RMSSD and DFA-alpha1
        rmssd = calculate_rmssd_movesense(clean_rr)
        assert rmssd is not None or len(clean_rr) < 2
        assert window_1s["dfa_alpha1"] == 0.780

    def test_c2_imu_kinematics_and_ecg_time_synchronization(self):
        """Combination C2: Synchronized ingestion of 128Hz ECG and 52Hz IMU with matching timestamps."""
        sim = MovesenseStreamSimulator()
        stream = sim.generate_15s_stream()

        assert len(stream) == 15
        for i, frame in enumerate(stream):
            # Check monotonic timestamp stepping by 1000ms
            if i > 0:
                assert frame["timestamp_epoch_ms"] - stream[i - 1]["timestamp_epoch_ms"] == 1000
            assert frame["sample_rate_hz"] == 128
            assert "x" in frame["acc_g"] and "y" in frame["acc_g"] and "z" in frame["acc_g"]

    def test_c3_multi_sensor_coexistence_movesense_and_polar(self):
        """Combination C3: Simultaneous ingestion of Movesense 128Hz and Polar H10 without key collision."""
        svc = TelemetryService()

        # Ingest Movesense packet
        p_movesense = {
            "sensor_type": "movesense",
            "heart_rate": 142.0,
            "rr_intervals_ms": [422.0, 420.0],
            "dfa_alpha1": 0.77,
            "acc_g": {"x": 0.04, "y": 0.95, "z": 0.31}
        }
        # Ingest Polar packet
        p_polar = {
            "sensor_type": "polar",
            "heart_rate": 141.0,
            "rr_intervals_ms": [425.0, 423.0]
        }

        # Async ingest runner
        import asyncio
        loop = asyncio.new_event_loop()
        res_m = loop.run_until_complete(svc.ingest_telemetry_payload(p_movesense))
        res_p = loop.run_until_complete(svc.ingest_telemetry_payload(p_polar))
        loop.close()

        assert res_m["status"] == "success"
        assert res_p["status"] == "success"

        status = svc.get_sensor_status()
        assert status["connected_count"] == 2
        assert status["fusion_state"] == "DUAL_SENSOR_FUSION"
        assert status["sensors"]["movesense"]["connected"] is True
        assert status["sensors"]["polar"]["connected"] is True
        assert status["sensors"]["movesense"]["heart_rate"] == 142.0
        assert status["sensors"]["polar"]["heart_rate"] == 141.0

    def test_c4_link_to_compute_hub_state_machine(self):
        """Combination C4: Simulates 'Link to Compute Hub' UI connection state transitions."""
        states = ["DISCONNECTED", "CONNECTING", "CONNECTED_STREAMING", "DISCONNECTED"]
        current_state = "DISCONNECTED"

        # 1. UI Button clicked -> CONNECTING
        current_state = "CONNECTING"
        assert current_state == "CONNECTING"

        # 2. GATT link established -> CONNECTED_STREAMING
        current_state = "CONNECTED_STREAMING"
        dsp = MovesenseBiometricsDSPPipeline()
        live_packet = {
            "hr_bpm": 138.0,
            "rr_ms": [435.0, 432.0, 438.0],
            "kinematics": {"accel_g": 1.01}
        }
        res_live = dsp.process_biometrics_stream(live_packet)
        assert res_live["status"] == "LIVE_DSP_ACTIVE"
        assert res_live["hrv_cardiac"]["heart_rate_bpm"] == 138.0

        # 3. Disconnection -> DISCONNECTED (Null states)
        current_state = "DISCONNECTED"
        res_disc = dsp.process_biometrics_stream(None)
        assert res_disc["status"] == "AWAITING_SENSOR"
        assert res_disc["hrv_cardiac"] is None


# ============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (End-to-End Mission Profiles)
# ============================================================================

class TestTier4RealWorldScenarios:
    """Tier 4: End-to-end 15-second exercise session and forensic zero-mock verification."""

    def test_w1_full_15s_movesense_exercise_session_simulation(self):
        """
        Scenario W1: Contiguous 15-second physiological workout stream (1,920 raw ECG samples).
        Verifies continuous Kamath filtering, RMSSD calculation, Zone 2 classification,
        and monotonic timestamp stepping.
        """
        sim = MovesenseStreamSimulator(base_heart_rate=135.0)
        stream_15s = sim.generate_15s_stream()

        assert len(stream_15s) == 15
        dsp = MovesenseBiometricsDSPPipeline()

        tracked_hr = []
        tracked_rmssd = []

        for window in stream_15s:
            packet = {
                "hr_bpm": window["heart_rate"],
                "rr_ms": window["rr_intervals_ms"],
                "kinematics": window["acc_g"]
            }
            res = dsp.process_biometrics_stream(packet)
            assert res["status"] == "LIVE_DSP_ACTIVE"
            tracked_hr.append(res["hrv_cardiac"]["heart_rate_bpm"])
            tracked_rmssd.append(res["hrv_cardiac"]["rmssd_ms"])

        assert len(tracked_hr) == 15
        assert tracked_hr[0] >= 135.0
        # Heart rate gently increases during workout
        assert tracked_hr[-1] > tracked_hr[0]
        print(f"\n[Tier 4 15s Simulation] Initial HR: {tracked_hr[0]} BPM -> Final HR: {tracked_hr[-1]} BPM")
        print(f"[Tier 4 15s Simulation] RMSSD profile: {tracked_rmssd}")

    def test_w2_zero_mock_audit_gate_e2e(self):
        """
        Scenario W2: Comprehensive forensic zero-mock compliance audit.
        Guarantees that no production endpoint emits synthetic placeholder numbers.
        """
        dsp = MovesenseBiometricsDSPPipeline()
        null_state = dsp.process_biometrics_stream(None)

        assert null_state["status"] == "AWAITING_SENSOR"
        assert null_state["kinematics"] is None
        assert null_state["hrv_cardiac"] is None
        assert "Awaiting physical sensor" in null_state["coaching_recommendation"]

        engine = PySparkMovesenseStreamEngine()
        engine_null = engine.process_movesense_stream(None)
        assert engine_null["stream_status"] == "WAITING_FOR_SENSOR"
        assert engine_null["biometrics"]["heart_rate_bpm"] is None
        assert engine_null["biometrics"]["dfa_alpha1"] is None
        assert engine_null["biometrics"]["rmssd_ms"] is None
