"""
Comprehensive Unit & Integration Test Suite for Movesense Hub Modular Package.
Tests all subpackages: core, dsp, transport, presentation, and root package exports.
Verifies Rule #0 Zero-Mock invariants, 512Hz/128Hz DSP accuracy, and interface contracts.
"""

import importlib
import math
import os
import sys
from pathlib import Path
from typing import List

import pytest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import modular package via importlib
mhb = importlib.import_module("01_apps.biometrics.movesense_hub")

# Extract subpackage exports directly from mhb
BiometricsStateStore = mhb.BiometricsStateStore
MovesenseHubConfig = mhb.MovesenseHubConfig
PttBloodPressure = mhb.PttBloodPressure
QrsDetectionResult = mhb.QrsDetectionResult
RawEcgFrame = mhb.RawEcgFrame
ReadinessReport = mhb.ReadinessReport
SleepStagingResult = mhb.SleepStagingResult
WorkoutState = mhb.WorkoutState
Zone2CardioResult = mhb.Zone2CardioResult

ContinuousPttBloodPressureModel = mhb.ContinuousPttBloodPressureModel
MovesenseECGPipeline = mhb.MovesenseECGPipeline
PanTompkinsQRSDetector = mhb.PanTompkinsQRSDetector
SleepStagingEngine = mhb.SleepStagingEngine
Zone2CoachingEngine = mhb.Zone2CoachingEngine
apply_kamath_artifact_filter = mhb.apply_kamath_artifact_filter
apply_kamath_filter = mhb.apply_kamath_filter
calculate_dfa_alpha1 = mhb.calculate_dfa_alpha1
calculate_hemodynamics_bp = mhb.calculate_hemodynamics_bp
calculate_rmssd = mhb.calculate_rmssd
classify_sleep_epoch = mhb.classify_sleep_epoch
classify_workout_state = mhb.classify_workout_state
classify_zone2_alignment = mhb.classify_zone2_alignment
compute_cardiorespiratory_thresholds = mhb.compute_cardiorespiratory_thresholds
compute_overnight_sleep_analysis = mhb.compute_overnight_sleep_analysis

MovesenseReadinessTUIApp = mhb.MovesenseReadinessTUIApp
OscilloscopePwaConnector = mhb.OscilloscopePwaConnector
ReadinessRestAdapter = mhb.ReadinessRestAdapter
WebTuiAdapter = mhb.WebTuiAdapter

MovesenseBleakDaemon = mhb.MovesenseBleakDaemon
WebBleBridge = mhb.WebBleBridge
decode_movesense_ecg_packet = mhb.decode_movesense_ecg_packet
decode_sig_heart_rate_measurement = mhb.decode_sig_heart_rate_measurement


class TestMovesenseHubPackageStructure:
    """Verifies modular package imports, versioning, and top-level convenience functions."""

    def test_package_version_and_exports(self):
        assert mhb.__version__ == "1.0.0"
        assert hasattr(mhb, "create_hub")
        assert hasattr(mhb, "process_raw_ecg")
        assert hasattr(mhb, "get_readiness_contract")

    def test_create_hub_factory(self, tmp_path):
        cfg = MovesenseHubConfig(
            readiness_live_output_path=tmp_path / "readiness.json",
            lora_dataset_output_path=tmp_path / "lora.jsonl"
        )
        state_store, pipeline, bridge = mhb.create_hub(config=cfg)
        assert isinstance(state_store, BiometricsStateStore)
        assert isinstance(pipeline, MovesenseECGPipeline)
        assert isinstance(bridge, WebBleBridge)

    def test_process_raw_ecg_convenience(self):
        # Empty samples returns WAITING_FOR_SENSOR
        res = mhb.process_raw_ecg([])
        assert res["status"] == "WAITING_FOR_SENSOR"
        assert res["rule_0_zero_mock"] is True

    def test_get_readiness_contract_convenience(self):
        contract = mhb.get_readiness_contract()
        assert contract["status"] == "WAITING_FOR_SENSOR"
        assert contract["heart_rate_bpm"] is None
        assert contract["ptt_blood_pressure"]["systolic_bp_mmhg"] is None


class TestCoreSubpackage:
    """Verifies core models, configuration, state store, and Rule #0 invariants."""

    def test_config_defaults_and_derived_properties(self):
        cfg = MovesenseHubConfig(user_age=30, hr_rest_baseline=58.0)
        assert cfg.device_serial == "261030002013"
        assert cfg.default_sample_rate_hz == 512
        assert cfg.hr_max == 190
        # LT1 = 58 + 0.60 * (190 - 58) = 58 + 79.2 = 137.2 -> 137
        assert cfg.lt1_hr_estimate == 137
        # LT2 = 58 + 0.85 * (190 - 58) = 58 + 112.2 = 170.2 -> 170
        assert cfg.lt2_hr_estimate == 170
        # VO2max = 15.3 * (190 / 58) = 50.07 -> 50.1
        assert pytest.approx(cfg.estimated_vo2max, abs=0.2) == 50.1

    def test_state_store_listeners_and_persistence(self, tmp_path):
        out_json = tmp_path / "live_readiness.json"
        out_lora = tmp_path / "lora.jsonl"
        store = BiometricsStateStore(persistence_path=out_json, lora_dataset_path=out_lora)

        received_reports: List[ReadinessReport] = []
        store.add_listener(lambda r: received_reports.append(r))

        report = ReadinessReport(
            status="STREAMING",
            connected=True,
            heart_rate_bpm=72.0,
            rmssd_ms=45.2,
            dfa_alpha1=0.82,
            blood_pressure=PttBloodPressure(sbp_mmhg=122.0, dbp_mmhg=79.0, map_mmhg=93.3, ptt_ms=195.0, status="NOMINAL"),
            sleep_analysis=SleepStagingResult(sleep_score_100=88, recovery_status="EXCELLENT (Green)"),
            workout=WorkoutState(activity_type="STEADY_CARDIO_ZONE_2", training_zone="Zone 2"),
            cardiorespiratory=Zone2CardioResult(dfa_alpha1=0.82, vo2max_ml_kg_min=50.1, lt1_hr=137.0, lt2_hr=170.0),
            rule_0_zero_mock=True
        )

        store.update_report(report)
        assert len(received_reports) == 1
        assert received_reports[0].heart_rate_bpm == 72.0

        # Verify disk persistence
        assert out_json.exists()
        assert out_lora.exists()

        contract = store.get_interface_contract()
        assert contract["status"] == "STREAMING"
        assert contract["heart_rate_bpm"] == 72.0
        assert contract["ptt_blood_pressure"]["systolic_bp_mmhg"] == 122.0
        assert contract["sleep_recovery"]["sleep_score_pct"] == 88


class TestDspSubpackage:
    """Verifies signal processing math, filters, QRS detector, and coaching models."""

    def test_pan_tompkins_512hz_synthetic_ecg(self):
        detector = PanTompkinsQRSDetector(sample_rate_hz=512)
        # Create 3s signal with 3 QRS complexes at 0.5s, 1.5s, 2.5s (60 BPM)
        fs = 512
        signal = [0.0] * (fs * 3)
        for t in [0.5, 1.5, 2.5]:
            idx = int(t * fs)
            signal[idx - 2] = 0.5
            signal[idx - 1] = 2.0
            signal[idx] = 4.0
            signal[idx + 1] = -1.0
            signal[idx + 2] = -0.5

        peaks, rrs = detector.detect_qrs_peaks(signal)
        assert len(peaks) == 3
        assert len(rrs) == 2
        for rr in rrs:
            assert pytest.approx(rr, abs=30.0) == 1000.0

    def test_kamath_2004_filter(self):
        # 1000ms baseline with a single ectopic 600ms premature beat followed by compensatory pause 1400ms
        raw = [1000.0, 1000.0, 600.0, 1400.0, 1000.0]
        cleaned, count = apply_kamath_artifact_filter(raw, threshold_pct=20.0)
        assert count >= 1
        for rr in cleaned:
            assert abs(rr - 1000.0) < 250.0

    def test_rmssd_microsecond_precision(self):
        rrs = [1000.0, 1050.0, 980.0, 1020.0, 990.0]
        rmssd = calculate_rmssd(rrs)
        assert rmssd is not None
        # Differences: [50, -70, 40, -30] -> sq: [2500, 4900, 1600, 900] -> sum: 9900 -> mean: 2475 -> sqrt: 49.75
        assert pytest.approx(rmssd, abs=0.1) == 49.75

    def test_dfa_alpha1_scaling(self):
        # 20 beats constant interval -> zero fluctuation, handled cleanly
        rrs = [1000.0] * 20
        dfa = calculate_dfa_alpha1(rrs)
        assert dfa is not None
        assert 0.40 <= dfa <= 1.50

    def test_hemodynamics_bp_inversion(self):
        # Direct PTT: PTT=195ms, HR=70 -> SBP = 120 + 5*0.45 = 122.25 -> 122.2, DBP = 80 + 5*0.25 = 81.25 -> 81.2
        sbp, dbp, map_val = calculate_hemodynamics_bp(ptt_ms=195.0, hr_bpm=70.0)
        assert sbp == 122.2
        assert dbp == 81.2
        assert map_val == 94.9

        # Disconnected state
        sbp_null, dbp_null, map_null = calculate_hemodynamics_bp(ptt_ms=None, hr_bpm=None)
        assert sbp_null is None and dbp_null is None and map_null is None

    def test_sleep_staging_epoch_scoring(self):
        # Sequence of 10 epochs: 4 DEEP, 3 REM, 2 LIGHT, 1 AWAKE
        epochs = ["DEEP", "DEEP", "DEEP", "DEEP", "REM", "REM", "REM", "LIGHT", "LIGHT", "AWAKE"]
        res = compute_overnight_sleep_analysis(hr_bpm=54.0, rmssd_ms=52.0, epoch_stages=epochs)
        assert res.status == "COMPLETED"
        assert res.sleep_score_100 is not None
        assert res.deep_pct == 40.0
        assert res.rem_pct == 30.0
        assert res.efficiency_pct == 90.0

    def test_zone2_coaching_recommendations(self):
        engine = Zone2CoachingEngine(user_age=30, hr_rest_baseline=58.0)
        rec_opt = engine.get_coaching_recommendation(hr_bpm=135.0, dfa_alpha1=0.78)
        assert rec_opt["action"] == "PERFECT_PACE"

        rec_anaerobic = engine.get_coaching_recommendation(hr_bpm=175.0, dfa_alpha1=0.45)
        assert rec_anaerobic["action"] == "REDUCE_PACE_NOW"


class TestTransportSubpackage:
    """Verifies BLE GATT payload decoders and Web Bluetooth bridge."""

    def test_decode_sig_heart_rate_measurement_uint8(self):
        # Flags: 0x10 (RR present), HR format uint8 -> data: [0x10, 72, 0x00, 0x04] (1024 / 1024 = 1.0s = 1000ms)
        raw_bytes = bytes([0x10, 72, 0x00, 0x04])
        hr, rrs = decode_sig_heart_rate_measurement(raw_bytes)
        assert hr == 72
        assert len(rrs) == 1
        assert pytest.approx(rrs[0], abs=1.0) == 1000.0

    def test_decode_movesense_ecg_packet(self):
        # Header: 0x02, 0x01, timestamp (1000ms = 0xE8, 0x03, 0x00, 0x00), 2 int32 samples (1000uV, 2000uV)
        packet = bytes([0x02, 0x01, 0xE8, 0x03, 0x00, 0x00, 0xE8, 0x03, 0x00, 0x00, 0xD0, 0x07, 0x00, 0x00])
        frame = decode_movesense_ecg_packet(packet)
        assert frame is not None
        assert frame.timestamp_us == 1000000
        assert frame.samples_mv == [1.0, 2.0]

    def test_web_ble_bridge_streaming_and_reset(self):
        bridge = WebBleBridge()
        report = bridge.ingest_sig_hrs_frame(hr_bpm=68, rr_intervals_ms=[882.0, 885.0, 880.0])
        assert report.status == "STREAMING"
        assert report.heart_rate_bpm == 68.0
        assert report.blood_pressure.sbp_mmhg is not None

        reset_report = bridge.reset_to_disconnected()
        assert reset_report.status == "WAITING_FOR_SENSOR"
        assert reset_report.heart_rate_bpm is None


class TestPresentationSubpackage:
    """Verifies Web-TUI adapter, PWA Oscilloscope connector, and TUI App."""

    def test_web_tui_adapter_command(self):
        cmd = WebTuiAdapter.get_pty_command()
        assert len(cmd) >= 2
        assert "tui.py" in cmd[1]

    def test_oscilloscope_pwa_connector_formatting(self):
        connector = OscilloscopePwaConnector(sampling_rate_hz=128)
        payload = connector.format_oscilloscope_payload(
            ecg_samples=[0.1, -0.2, 10.0, -10.0],  # 10.0 and -10.0 should be clamped to 5.0 and -5.0
            heart_rate=75,
            is_connected=True
        )
        assert payload["type"] == "ECG_SWEEP_FRAME"
        assert payload["leadStatus"] == "CONNECTED"
        assert payload["samplingRateHz"] == 128
        assert payload["heartRate"] == 75
        assert payload["ecgSamples"] == [0.1, -0.2, 5.0, -5.0]

    def test_tui_app_mount_and_render(self):
        app = MovesenseReadinessTUIApp()
        # Verify app title and CSS
        assert "MOVESENSE" in app.TITLE or "LAUBURU" in app.TITLE
        assert "Screen" in app.CSS
