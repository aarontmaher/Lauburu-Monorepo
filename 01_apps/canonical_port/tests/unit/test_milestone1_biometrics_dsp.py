#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Milestone 1 Test Suite: Biometrics DSP & Open Wearables Federation
Subsystem: Open Wearables TUI Mesh
Coverage:
1. Multi-provider commercial wearable normalization (Whoop, Garmin, Oura, Apple Health, Google Health)
2. High-frequency 512Hz/128Hz Movesense ECG DSP (Pan-Tompkins QRS, Kamath 20% filter, RMSSD, DFA-alpha1, PTT BP)
3. Strict Rule #0 Zero-Mock Enforcement (WAITING_FOR_SENSOR, null metrics on disconnected hardware)
4. Macro-micro biometrics correlation and dynamic readiness indexing
5. Delta Lake ACID writes (DeltaDatasetWriter) and PySpark JSONL stream persistence
6. Blackboard state schema translation and atomic persistence
"""

import os
import sys
import json
import math
import tempfile
import pytest
from pathlib import Path

# Add paths to sys.path
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
DSP_DIR = MONOREPO_ROOT / "03_biometrics_and_telemetry"
DELTA_DIR = MONOREPO_ROOT / "04_data_and_memory"
CANONICAL_PORT = MONOREPO_ROOT / "01_apps/canonical_port"

for p in [str(DSP_DIR), str(DELTA_DIR), str(CANONICAL_PORT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from pan_tompkins_dsp import (
    PanTompkinsQRSDetector,
    MovesenseECGPipeline,
    apply_kamath_artifact_filter,
    calculate_rmssd,
    calculate_dfa_alpha1,
    calculate_hemodynamics_bp,
    classify_zone2_alignment,
)
from open_wearables_bridge import OpenWearablesNormalizer, OpenWearablesBridge
from delta_engine.writer import DeltaDatasetWriter
from delta_engine.schema import WEARABLES_TELEMETRY_ARROW_SCHEMA, MOVESENSE_STREAM_ARROW_SCHEMA, get_schema_by_name
from tui.models.blackboard_models import (
    BlackboardTelemetryState,
    Layer2BiometricsState,
    WearablesTelemetryState,
    ReadinessState,
    MovesenseStreamState,
    KamathFilterState,
    PttBloodPressure
)
from tui.services.blackboard_store import BlackboardStore


# ============================================================================
# 1. MULTI-PROVIDER COMMERCIAL WEARABLE NORMALIZATION TESTS
# ============================================================================

def test_whoop_normalization():
    """Verify Whoop raw schema normalization into canonical structure."""
    raw = {
        "provider": "whoop",
        "recovery": {
            "recovery_score": 85.0,
            "resting_heart_rate": 48.0,
            "hrv_rmssd_milli": 68.0,
            "spo2_percentage": 98.2
        },
        "sleep": {
            "sleep_score": 90.0,
            "total_sleep_time_milli": 27600000  # 460 min
        },
        "strain": {
            "strain_score": 14.8,
            "kilojoules": 3765
        },
        "steps": 11200
    }
    norm = OpenWearablesNormalizer.normalize_payload(raw)
    assert norm["source"] == "whoop"
    assert norm["providers"] == ["whoop"]
    assert norm["recovery_score"] == 85.0
    assert norm["resting_hr_bpm"] == 48.0
    assert norm["hrv_rmssd_ms"] == 68.0
    assert norm["sleep_score"] == 90.0
    assert norm["strain_score"] == 14.8
    assert norm["rule_0_zero_mock"] is True


def test_garmin_normalization():
    """Verify Garmin Connect raw schema normalization."""
    raw = {
        "provider": "garmin",
        "daily_summary": {
            "body_battery": 78,
            "resting_heart_rate": 52.0,
            "hrv_rmssd": 54.0,
            "sleep_score": 82.0,
            "active_kilocalories": 680,
            "total_steps": 12800
        }
    }
    norm = OpenWearablesNormalizer.normalize_payload(raw)
    assert norm["source"] == "garmin"
    assert norm["recovery_score"] == 78.0
    assert norm["resting_hr_bpm"] == 52.0
    assert norm["hrv_rmssd_ms"] == 54.0
    assert norm["sleep_score"] == 82.0
    assert norm["steps"] == 12800
    assert norm["calories"] == 680
    assert norm["rule_0_zero_mock"] is True


def test_oura_normalization():
    """Verify Oura Ring Gen 3 raw schema normalization."""
    raw = {
        "provider": "oura",
        "readiness": {"score": 92.0, "resting_hr": 46.0, "rmssd": 76.0},
        "sleep": {"score": 94.0, "total_sleep_duration": 28800},
        "activity": {"score": 80.0, "active_calories": 550, "steps": 10500}
    }
    norm = OpenWearablesNormalizer.normalize_payload(raw)
    assert norm["source"] == "oura"
    assert norm["recovery_score"] == 92.0
    assert norm["resting_hr_bpm"] == 46.0
    assert norm["hrv_rmssd_ms"] == 76.0
    assert norm["sleep_score"] == 94.0
    assert norm["steps"] == 10500
    assert norm["calories"] == 550
    assert norm["rule_0_zero_mock"] is True


def test_apple_health_normalization():
    """Verify Apple HealthKit export payload normalization."""
    raw = {
        "provider": "apple_health",
        "HKQuantityTypeIdentifierRestingHeartRate": 50.0,
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": 60.0,
        "HKQuantityTypeIdentifierStepCount": 14200,
        "HKQuantityTypeIdentifierActiveEnergyBurned": 820,
        "recovery_score": 84.0,
        "sleep_score": 86.0
    }
    norm = OpenWearablesNormalizer.normalize_payload(raw)
    assert norm["source"] == "apple_health"
    assert norm["resting_hr_bpm"] == 50.0
    assert norm["hrv_rmssd_ms"] == 60.0
    assert norm["steps"] == 14200
    assert norm["calories"] == 820
    assert norm["recovery_score"] == 84.0


def test_google_health_normalization():
    """Verify Google Health Connect raw schema normalization."""
    raw = {
        "provider": "google_health_connect",
        "RestingHeartRateRecord": 53.0,
        "HeartRateVariabilityRmssdRecord": 52.0,
        "StepsRecord": 8900,
        "TotalCaloriesBurnedRecord": 620,
        "recovery_score": 79.0,
        "sleep_score": 81.0
    }
    norm = OpenWearablesNormalizer.normalize_payload(raw)
    assert norm["source"] == "google_health_connect"
    assert norm["resting_hr_bpm"] == 53.0
    assert norm["hrv_rmssd_ms"] == 52.0
    assert norm["steps"] == 8900
    assert norm["calories"] == 620


def test_open_wearables_aggregator_summary():
    """Verify standard Open Wearables multi-provider aggregate schema."""
    raw = {
        "source": "open_wearables_aggregator",
        "providers": ["whoop", "garmin", "oura"],
        "recovery_score": 88.0,
        "sleep_score": 91.0,
        "strain_score": 14.2,
        "resting_hr": 48.5,
        "hrv_rmssd": 64.2,
        "steps": 12450,
        "active_calories": 840
    }
    norm = OpenWearablesNormalizer.normalize_payload(raw)
    assert norm["source"] == "open_wearables_aggregator"
    assert "whoop" in norm["providers"]
    assert norm["recovery_score"] == 88.0
    assert norm["resting_hr_bpm"] == 48.5
    assert norm["hrv_rmssd_ms"] == 64.2
    assert norm["steps"] == 12450
    assert norm["calories"] == 840


# ============================================================================
# 2. PAN-TOMPKINS QRS DETECTION & DSP PIPELINE TESTS
# ============================================================================

def test_pan_tompkins_qrs_detection_synthetic_ecg():
    """Verify Pan-Tompkins detects R-peaks and computes RR intervals on realistic ECG."""
    fs = 512
    detector = PanTompkinsQRSDetector(sample_rate_hz=fs)
    
    # Generate 3 seconds of realistic physiological ECG signal at 60 BPM (1 beat per second)
    ecg_signal = []
    for s in range(3 * fs):
        phase = (s % fs) / float(fs)
        # QRS spike around phase 0.20
        if 0.18 <= phase <= 0.22:
            val = 2.0 * math.sin((phase - 0.18) / 0.04 * math.pi)
        elif 0.35 <= phase <= 0.45:
            val = 0.3 * math.sin((phase - 0.35) / 0.10 * math.pi)  # T-wave
        elif 0.10 <= phase <= 0.15:
            val = 0.15 * math.sin((phase - 0.10) / 0.05 * math.pi)  # P-wave
        else:
            val = 0.02 * math.sin(phase * 10 * math.pi)  # Baseline noise
        ecg_signal.append(val)

    peak_indices, rr_intervals = detector.detect_qrs_peaks(ecg_signal)
    assert len(peak_indices) >= 2
    assert len(rr_intervals) >= 1
    # RR interval for 60 BPM should be ~1000ms (+/- 50ms)
    assert 950.0 <= rr_intervals[0] <= 1050.0


def test_kamath_2004_artifact_filter():
    """Verify Kamath 20% clinical RR filter rejects ectopic bursts and preserves baseline."""
    # Normal sinus rhythm with ectopic premature beat and post-extrasystolic pause
    rrs = [850.0, 845.0, 852.0, 848.0, 420.0, 1280.0, 850.0, 846.0, 854.0]
    cleaned, artifacts = apply_kamath_artifact_filter(rrs, threshold_pct=20.0)
    assert artifacts >= 2  # Ectopic beat (420ms) and compensatory pause (1280ms) rejected
    assert len(cleaned) == len(rrs)
    # Filtered values should remain within +/-20% of 850ms
    for r in cleaned:
        assert 680.0 <= r <= 1020.0


def test_rmssd_calculation():
    """Verify RMSSD calculation against ground truth physiological formula."""
    rrs = [800.0, 820.0, 790.0, 810.0, 805.0]
    # diffs = [+20, -30, +20, -5] -> squares = [400, 900, 400, 25] -> sum = 1725 -> mean = 1725 / 4 = 431.25 -> sqrt = 20.766
    rmssd = calculate_rmssd(rrs)
    assert rmssd == 20.77

    # Edge cases
    assert calculate_rmssd([]) is None
    assert calculate_rmssd([800.0]) is None


def test_dfa_alpha1_calculation():
    """Verify short-term DFA-alpha1 scaling exponent calculation."""
    # Baseline physiological RR series (~800ms with fractal variation)
    rrs = [800.0, 805.0, 795.0, 810.0, 802.0, 798.0, 808.0, 804.0, 796.0, 812.0, 801.0, 799.0, 806.0, 803.0, 797.0, 811.0]
    alpha1 = calculate_dfa_alpha1(rrs, scale_min=4, scale_max=16)
    assert alpha1 is not None
    assert 0.40 <= alpha1 <= 1.50

    # Zone 2 classification
    zone_desc, zone_color = classify_zone2_alignment(0.78)
    assert "Zone 2" in zone_desc
    assert zone_color == "#10b981"

    zone_desc_fatigue, _ = classify_zone2_alignment(0.42)
    assert "Zone 4/5" in zone_desc_fatigue

    # Edge cases
    assert calculate_dfa_alpha1([]) is None
    assert calculate_dfa_alpha1([800.0, 805.0]) is None


def test_ptt_hemodynamic_blood_pressure():
    """Verify Pulse Transit Time hemodynamic arterial BP inversion."""
    # Normal resting PTT (~200ms) at 70 BPM -> 120/80 mmHg
    sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=200.0, hr_bpm=70.0)
    assert sbp == 120.0
    assert dbp == 80.0
    assert map_val == 93.3

    # Exercise vasoconstriction: shorter PTT (160ms) and elevated HR (140 BPM)
    sbp_ex, dbp_ex, map_ex = calculate_hemodynamics_bp(ptt_ms=160.0, hr_bpm=140.0)
    assert sbp_ex > 120.0
    assert dbp_ex > 80.0

    # Disconnected / missing PTT
    assert calculate_hemodynamics_bp(None, 70.0) == (None, None, None)
    assert calculate_hemodynamics_bp(0.0, 70.0) == (None, None, None)


# ============================================================================
# 3. STRICT RULE #0 ZERO-MOCK COMPLIANCE TESTS
# ============================================================================

def test_movesense_pipeline_zero_mock_when_disconnected():
    """Verify pipeline emits WAITING_FOR_SENSOR and strict nulls when sensor is absent."""
    pipeline = MovesenseECGPipeline(sample_rate_hz=512)
    
    # Process empty / absent sample stream
    state = pipeline.process_raw_ecg_window([])
    assert state["status"] == "WAITING_FOR_SENSOR"
    assert state["connected"] is False
    assert state["heart_rate_bpm"] is None
    assert state["rr_intervals_ms"] == []
    assert state["clean_rr_intervals_ms"] == []
    assert state["rmssd_ms"] is None
    assert state["dfa_alpha1"] is None
    assert state["ptt_blood_pressure"]["systolic_mmhg"] is None
    assert state["ptt_blood_pressure"]["status"] == "STANDBY"
    assert state["rule_0_zero_mock"] is True


def test_movesense_pipeline_short_buffer_zero_mock():
    """Verify pipeline does not synthesize numbers on insufficient sample buffer."""
    pipeline = MovesenseECGPipeline(sample_rate_hz=512)
    # 50 samples is < 0.5s at 512Hz
    state = pipeline.process_raw_ecg_window([0.1] * 50)
    assert state["status"] == "WAITING_FOR_SENSOR"
    assert state["heart_rate_bpm"] is None


# ============================================================================
# 4. MACRO-MICRO FEDERATION & READINESS CORRELATION TESTS
# ============================================================================

def test_macro_micro_correlation():
    """Verify federation of macro recovery with live Movesense ECG metrics."""
    bridge = OpenWearablesBridge()

    macro_whoop = {
        "source": "whoop",
        "recovery_score": 90.0,
        "sleep_score": 92.0,
        "hrv_rmssd_ms": 65.0,
        "resting_hr_bpm": 48.0
    }

    movesense_active = {
        "connected": True,
        "heart_rate_bpm": 136.0,
        "rmssd_ms": 48.0,
        "dfa_alpha1": 0.78,
        "ptt_blood_pressure": {"systolic_mmhg": 124.0, "diastolic_mmhg": 82.0}
    }

    correlated = bridge.correlate_with_micro_dsp(macro_whoop, movesense_state=movesense_active)
    assert correlated["readiness_score"] is not None
    assert correlated["readiness_category"] == "PRIME_OPTIMAL"
    assert "High-intensity" in correlated["training_advice"]
    assert correlated["autonomic_balance"] == "PARASYMPATHETIC_DOMINANT"


def test_macro_micro_correlation_disconnected_sensor():
    """Verify fallback to macro score when micro Movesense sensor is disconnected."""
    bridge = OpenWearablesBridge()
    macro_garmin = {
        "source": "garmin",
        "recovery_score": 82.0,
        "sleep_score": 85.0,
        "hrv_rmssd_ms": 55.0
    }
    correlated = bridge.correlate_with_micro_dsp(macro_garmin, movesense_state={"connected": False})
    assert correlated["readiness_score"] == 82.0
    assert correlated["readiness_category"] == "RECOVERED"


# ============================================================================
# 5. DELTA LAKE & PYSPARK STORAGE TESTS
# ============================================================================

def test_delta_lake_schema_registration():
    """Verify WEARABLES_TELEMETRY_ARROW_SCHEMA and MOVESENSE_STREAM_ARROW_SCHEMA are registered."""
    schema_wearables = get_schema_by_name("wearables_telemetry")
    assert schema_wearables is not None
    assert "recovery_score" in schema_wearables.names
    assert "live_dfa_alpha1" in schema_wearables.names
    assert "rule_0_zero_mock" in schema_wearables.names

    schema_movesense = get_schema_by_name("movesense_stream")
    assert schema_movesense is not None
    assert "sample_rate_hz" in schema_movesense.names
    assert "dfa_alpha1" in schema_movesense.names


def test_delta_lake_acid_persistence():
    """Verify DeltaDatasetWriter writes normalized wearable records with ACID guarantees."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        table_path = os.path.join(tmp_dir, "wearables_test_delta")
        writer = DeltaDatasetWriter(
            table_uri=table_path,
            schema=WEARABLES_TELEMETRY_ARROW_SCHEMA,
            mode="append",
            schema_mode="merge",
            buffer_size=1
        )

        record = {
            "timestamp": "2026-08-29T05:15:00Z",
            "user_id": "test_user_01",
            "source": "whoop",
            "providers": ["whoop"],
            "recovery_score": 88.5,
            "sleep_score": 91.0,
            "strain_score": 14.2,
            "resting_hr_bpm": 48.0,
            "hrv_rmssd_ms": 66.0,
            "steps": 12500,
            "active_calories": 840,
            "movesense_connected": True,
            "live_hr_bpm": 138.0,
            "live_dfa_alpha1": 0.76,
            "live_rmssd_ms": 44.0,
            "ptt_systolic_mmhg": 122.0,
            "ptt_diastolic_mmhg": 78.0,
            "rule_0_zero_mock": True,
            "raw_payload_json": '{"test": true}'
        }

        res = writer.write(record, mode="append")
        assert res["status"] == "success"
        assert res["rows_written"] == 1
        assert res["version"] >= 0
        assert writer.count_rows() == 1


# ============================================================================
# 6. CENTRAL BLACKBOARD STATE SYNCHRONIZATION TESTS
# ============================================================================

def test_blackboard_wearables_telemetry_roundtrip():
    """Verify WearablesTelemetryState round-trip serialization and store mutation."""
    store = BlackboardStore()
    snap = store.get_snapshot(force_refresh=True)
    assert hasattr(snap, "wearables_telemetry")
    assert snap.wearables_telemetry.rule_0_zero_mock is True

    # Mutate layer
    updated = store.update_layer("wearables_telemetry", {
        "source": "oura",
        "recovery_score": 94.0,
        "sleep_score": 96.0,
        "resting_hr_bpm": 45.0,
        "hrv_rmssd_ms": 78.0,
        "steps": 15000,
        "calories": 950,
        "rule_0_zero_mock": True
    })
    assert updated.wearables_telemetry.source == "oura"
    assert updated.wearables_telemetry.recovery_score == 94.0

    # Verify JSON serialization includes wearables_telemetry
    json_str = updated.to_json()
    parsed = json.loads(json_str)
    assert "wearables_telemetry" in parsed
    assert parsed["wearables_telemetry"]["recovery_score"] == 94.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
