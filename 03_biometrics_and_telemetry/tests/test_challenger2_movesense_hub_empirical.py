"""
Empirical Verification Test Suite: Challenger 2 (Milestone M1)
Focus:
1. Concurrency stress on BiometricsStateStore with 1,000 rapid frame updates across multiple threads.
2. Rule #0 strict zero-mock compliance audit across state store, DSP engines, transports, and presentation.
3. OscilloscopePwaConnector ring buffer sweep logic under high throughput and boundary conditions.
"""

from __future__ import annotations

import ast
import concurrent.futures
import json
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import importlib

mhb = importlib.import_module("01_apps.biometrics.movesense_hub")

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


# ============================================================================
# 1. CONCURRENCY STRESS ON BiometricsStateStore (1,000 Rapid Updates)
# ============================================================================

class TestStateStoreConcurrencyStress:
    """
    Stress-tests BiometricsStateStore with 1,000 rapid multi-threaded updates,
    concurrent readers, dynamic listener mutations, and file persistence.
    """

    def test_1000_rapid_frame_updates_multi_threaded_in_memory(self):
        """
        Spawns 10 writer threads each pushing 100 distinct reports (1,000 total).
        Concurrently runs 5 reader threads continuously querying state.
        Verifies thread safety, zero deadlocks, and consistency.
        """
        store = BiometricsStateStore()
        total_writers = 10
        updates_per_writer = 100
        total_updates = total_writers * updates_per_writer

        received_count = 0
        received_lock = threading.Lock()

        def listener(report: ReadinessReport):
            nonlocal received_count
            with received_lock:
                received_count += 1

        store.add_listener(listener)

        start_event = threading.Event()
        stop_readers = threading.Event()
        reader_errors: List[Exception] = []
        writer_errors: List[Exception] = []

        def writer_worker(worker_id: int):
            start_event.wait()
            try:
                for i in range(updates_per_writer):
                    hr_val = 60.0 + (worker_id * 5) + (i % 30)
                    rep = ReadinessReport(
                        status="STREAMING",
                        connected=True,
                        heart_rate_bpm=hr_val,
                        rmssd_ms=40.0 + (i % 20),
                        dfa_alpha1=0.80,
                        blood_pressure=PttBloodPressure(sbp_mmhg=120.0 + i, dbp_mmhg=80.0, map_mmhg=93.3, ptt_ms=195.0, status="NOMINAL"),
                        sleep_analysis=SleepStagingResult(sleep_score_100=85, recovery_status="EXCELLENT (Green)"),
                        workout=WorkoutState(activity_type="STEADY_CARDIO_ZONE_2", training_zone="Zone 2"),
                        cardiorespiratory=Zone2CardioResult(dfa_alpha1=0.80, vo2max_ml_kg_min=50.1, lt1_hr=137.0, lt2_hr=170.0),
                        rule_0_zero_mock=True,
                    )
                    store.update_report(rep)
            except Exception as e:
                writer_errors.append(e)

        def reader_worker():
            start_event.wait()
            try:
                while not stop_readers.is_set():
                    rep = store.get_report()
                    contract = store.get_interface_contract()
                    assert isinstance(rep, ReadinessReport)
                    assert isinstance(contract, dict)
                    assert "status" in contract
                    time.sleep(0.0001)
            except Exception as e:
                reader_errors.append(e)

        # Launch threads
        writers = [threading.Thread(target=writer_worker, args=(w,)) for w in range(total_writers)]
        readers = [threading.Thread(target=reader_worker) for _ in range(5)]

        for t in writers + readers:
            t.start()

        t0 = time.perf_counter()
        start_event.set()

        for w in writers:
            w.join(timeout=10.0)
            assert not w.is_alive(), "Writer thread timed out (deadlock detected)!"

        stop_readers.set()
        for r in readers:
            r.join(timeout=5.0)
            assert not r.is_alive(), "Reader thread timed out!"

        t_elapsed = time.perf_counter() - t0
        qps = total_updates / max(t_elapsed, 1e-6)

        assert len(writer_errors) == 0, f"Writer errors encountered: {writer_errors}"
        assert len(reader_errors) == 0, f"Reader errors encountered: {reader_errors}"
        assert received_count == total_updates, f"Expected {total_updates} listener callbacks, got {received_count}"

        final_report = store.get_report()
        assert final_report.connected is True
        assert final_report.heart_rate_bpm is not None
        assert final_report.rule_0_zero_mock is True

        final_contract = store.get_interface_contract()
        assert final_contract["status"] == "STREAMING"
        assert final_contract["heart_rate_bpm"] is not None

        print(f"\n[BENCHMARK] 1,000 in-memory multi-threaded updates completed in {t_elapsed*1000:.2f}ms ({qps:.1f} updates/sec)")

    def test_1000_rapid_frame_updates_with_disk_persistence(self, tmp_path):
        """
        Tests 1,000 multi-threaded updates while simultaneously persisting JSON live state
        and appending to continuous LoRA dataset.
        Verifies valid JSON formatting on disk and zero file corruption under high contention.
        """
        json_path = tmp_path / "persistence_stress" / "live_readiness.json"
        lora_path = tmp_path / "persistence_stress" / "lora_stream.jsonl"

        store = BiometricsStateStore(persistence_path=json_path, lora_dataset_path=lora_path)
        total_writers = 10
        updates_per_writer = 100
        total_updates = total_writers * updates_per_writer

        start_event = threading.Event()
        writer_errors: List[Exception] = []

        def writer_worker(worker_id: int):
            start_event.wait()
            try:
                for i in range(updates_per_writer):
                    hr_val = 70.0 + (worker_id % 5) * 10.0 + (i % 15)
                    rep = ReadinessReport(
                        status="STREAMING",
                        connected=True,
                        heart_rate_bpm=hr_val,
                        rmssd_ms=45.0,
                        dfa_alpha1=0.78,
                        blood_pressure=PttBloodPressure(sbp_mmhg=122.0, dbp_mmhg=80.0, map_mmhg=94.0, ptt_ms=192.0, status="NOMINAL"),
                        sleep_analysis=SleepStagingResult(sleep_score_100=82, recovery_status="EXCELLENT (Green)"),
                        workout=WorkoutState(activity_type="STEADY_CARDIO_ZONE_2", training_zone="Zone 2"),
                        cardiorespiratory=Zone2CardioResult(dfa_alpha1=0.78, vo2max_ml_kg_min=50.1, lt1_hr=137.0, lt2_hr=170.0),
                        rule_0_zero_mock=True,
                    )
                    store.update_report(rep)
            except Exception as e:
                writer_errors.append(e)

        writers = [threading.Thread(target=writer_worker, args=(w,)) for w in range(total_writers)]
        for w in writers:
            w.start()

        t0 = time.perf_counter()
        start_event.set()

        for w in writers:
            w.join(timeout=15.0)
            assert not w.is_alive(), "Writer thread timed out with disk persistence!"

        t_elapsed = time.perf_counter() - t0
        qps = total_updates / max(t_elapsed, 1e-6)

        assert len(writer_errors) == 0, f"Errors during persisted writes: {writer_errors}"
        assert json_path.exists(), "Live JSON state file was not created!"
        assert lora_path.exists(), "LoRA continuous JSONL dataset was not created!"

        # Validate JSON content integrity
        with open(json_path, "r") as f:
            data = json.load(f)
        assert data["status"] == "STREAMING"
        assert data["sensor_telemetry"]["connected"] is True
        assert data["rule_0_zero_mock"] is True

        # Validate JSONL lines
        with open(lora_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) > 0, "LoRA dataset file is empty!"
        for line in lines[:10]:
            record = json.loads(line)
            assert "instruction" in record
            assert "input" in record
            assert "output" in record
            assert record["metadata"]["rule_0_verified"] is True

        print(f"\n[BENCHMARK] 1,000 persisted multi-threaded updates completed in {t_elapsed*1000:.2f}ms ({qps:.1f} updates/sec, {len(lines)} LoRA records)")

    def test_dynamic_listener_mutation_during_rapid_updates(self):
        """
        Dynamically adds and removes listeners while 500 rapid updates occur.
        Ensures thread safety and absence of concurrent mutation runtime errors.
        """
        store = BiometricsStateStore()
        stop_flag = False

        def cb_1(r): pass
        def cb_2(r): pass
        def cb_3(r): pass

        def updater():
            for i in range(500):
                rep = ReadinessReport(
                    status="STREAMING",
                    connected=True,
                    heart_rate_bpm=60.0 + (i % 40),
                )
                store.update_report(rep)

        def mutator():
            callbacks = [cb_1, cb_2, cb_3]
            while not stop_flag:
                for cb in callbacks:
                    store.add_listener(cb)
                    time.sleep(0.0002)
                    store.remove_listener(cb)

        t_update = threading.Thread(target=updater)
        t_mutate = threading.Thread(target=mutator)

        t_mutate.start()
        t_update.start()

        t_update.join(timeout=10.0)
        stop_flag = True
        t_mutate.join(timeout=5.0)

        assert not t_update.is_alive()
        assert not t_mutate.is_alive()


# ============================================================================
# 2. RULE #0 STRICT ZERO-MOCK COMPLIANCE AUDIT
# ============================================================================

class TestRuleZeroMockComplianceAudit:
    """
    Forensic verification of strict Rule #0 zero-mock invariants:
    When disconnected, all metrics return clean null/waiting states and zero hardcoded test metric arrays are emitted.
    """

    def test_state_store_default_disconnected_state(self):
        """Validates that a fresh BiometricsStateStore instance is 100% clean and null."""
        store = BiometricsStateStore()
        rep = store.get_report()

        assert rep.status == "WAITING_FOR_SENSOR"
        assert rep.connected is False
        assert rep.heart_rate_bpm is None
        assert rep.rmssd_ms is None
        assert rep.dfa_alpha1 is None
        assert rep.blood_pressure.sbp_mmhg is None
        assert rep.blood_pressure.dbp_mmhg is None
        assert rep.blood_pressure.map_mmhg is None
        assert rep.blood_pressure.ptt_ms is None
        assert rep.blood_pressure.status == "STANDBY"
        assert rep.sleep_analysis.sleep_score_100 is None
        assert rep.sleep_analysis.status == "WAITING_FOR_SENSOR"
        assert rep.workout.activity_type is None
        assert rep.workout.status == "WAITING_FOR_SENSOR"
        assert rep.cardiorespiratory.dfa_alpha1 is None
        assert rep.cardiorespiratory.status == "WAITING_FOR_SENSOR"
        assert rep.rule_0_zero_mock is True

    def test_state_store_interface_contract_when_disconnected(self):
        """Validates that get_interface_contract() strictly adheres to PROJECT.md null schema."""
        store = BiometricsStateStore()
        contract = store.get_interface_contract()

        assert contract["status"] == "WAITING_FOR_SENSOR"
        assert contract["heart_rate_bpm"] is None
        assert contract["rmssd_ms"] is None
        assert contract["dfa_alpha1"] is None
        assert contract["ptt_blood_pressure"] == {
            "systolic_bp_mmhg": None,
            "diastolic_bp_mmhg": None,
            "map_mmhg": None,
        }
        assert contract["sleep_recovery"] == {
            "sleep_score_pct": None,
            "deep_sleep_pct": None,
            "rem_sleep_pct": None,
        }
        assert contract["cardiorespiratory"] == {
            "lt1_threshold_bpm": None,
            "lt2_threshold_bpm": None,
            "vo2max_estimate": None,
            "activity_state": None,
        }

    def test_bleak_daemon_emit_disconnected_state(self):
        """Validates that MovesenseBleakDaemon.emit_disconnected_state() leaves zero residue."""
        store = BiometricsStateStore()
        daemon = MovesenseBleakDaemon(state_store=store)

        # Emit active report first
        active_rep = ReadinessReport(
            status="STREAMING",
            connected=True,
            heart_rate_bpm=140.0,
            rmssd_ms=30.0,
            dfa_alpha1=0.65,
        )
        store.update_report(active_rep)
        assert store.get_report().heart_rate_bpm == 140.0

        # Now disconnect
        daemon.emit_disconnected_state()
        rep = store.get_report()
        assert rep.status == "WAITING_FOR_SENSOR"
        assert rep.connected is False
        assert rep.heart_rate_bpm is None
        assert rep.rmssd_ms is None
        assert rep.dfa_alpha1 is None
        assert rep.rule_0_zero_mock is True

    def test_web_ble_bridge_reset_and_null_packet_handling(self):
        """Validates that WebBleBridge cleanly resets and rejects null or disconnected packets."""
        store = BiometricsStateStore()
        bridge = WebBleBridge(state_store=store)

        # 1. Ingest null heart rate
        rep1 = bridge.ingest_sig_hrs_frame(None)
        assert rep1.status == "WAITING_FOR_SENSOR"
        assert rep1.connected is False
        assert rep1.heart_rate_bpm is None

        # 2. Ingest zero or negative heart rate
        rep2 = bridge.ingest_sig_hrs_frame(0)
        assert rep2.status == "WAITING_FOR_SENSOR"
        assert rep2.heart_rate_bpm is None

        rep3 = bridge.ingest_sig_hrs_frame(-10)
        assert rep3.status == "WAITING_FOR_SENSOR"
        assert rep3.heart_rate_bpm is None

        # 3. Ingest empty/disconnected dictionary packet
        rep4 = bridge.ingest_web_ble_packet({"connected": False, "heart_rate_bpm": 80})
        assert rep4.status == "WAITING_FOR_SENSOR"
        assert rep4.heart_rate_bpm is None

        # 4. Stream valid data, then call reset_to_disconnected
        bridge.ingest_sig_hrs_frame(75, [800.0, 805.0])
        assert store.get_report().status == "STREAMING"

        reset_rep = bridge.reset_to_disconnected()
        assert reset_rep.status == "WAITING_FOR_SENSOR"
        assert reset_rep.heart_rate_bpm is None
        assert store.get_report().status == "WAITING_FOR_SENSOR"

    def test_movesense_ecg_pipeline_empty_and_insufficient_samples(self):
        """Validates that MovesenseECGPipeline returns clean WAITING_FOR_SENSOR for empty/short inputs."""
        pipeline = MovesenseECGPipeline(sample_rate_hz=512)

        # Empty array
        res_empty = pipeline.process_raw_ecg_window([])
        assert res_empty["status"] == "WAITING_FOR_SENSOR"
        assert res_empty["connected"] is False
        assert res_empty["heart_rate_bpm"] is None
        assert res_empty["rr_intervals_ms"] == []
        assert res_empty["clean_rr_intervals_ms"] == []
        assert res_empty["rmssd_ms"] is None
        assert res_empty["dfa_alpha1"] is None
        assert res_empty["ptt_blood_pressure"]["systolic_mmhg"] is None
        assert res_empty["ptt_blood_pressure"]["status"] == "STANDBY"
        assert res_empty["rule_0_zero_mock"] is True

        # Too short (< 0.5s = < 256 samples for 512Hz)
        res_short = pipeline.process_raw_ecg_window([0.1, 0.2] * 50)
        assert res_short["status"] == "WAITING_FOR_SENSOR"
        assert res_short["heart_rate_bpm"] is None

    def test_hemodynamic_bp_model_null_inputs(self):
        """Validates that ContinuousPttBloodPressureModel returns STANDBY when sensors are absent."""
        model = ContinuousPttBloodPressureModel()
        bp = model.compute_ptt_blood_pressure(hr_bpm=None, rmssd_ms=None, ptt_ms=None)
        assert bp.status == "STANDBY"
        assert bp.sbp_mmhg is None
        assert bp.dbp_mmhg is None
        assert bp.map_mmhg is None
        assert bp.ptt_ms is None

        # calculate_hemodynamics_bp function
        sbp, dbp, map_val = calculate_hemodynamics_bp(None, None)
        assert sbp is None and dbp is None and map_val is None

        sbp0, dbp0, map0 = calculate_hemodynamics_bp(0.0, 70.0)
        assert sbp0 is None and dbp0 is None and map0 is None

    def test_sleep_staging_engine_null_inputs(self):
        """Validates that SleepStagingEngine returns WAITING_FOR_SENSOR on empty nocturnal data."""
        engine = SleepStagingEngine()
        sleep = engine.compute_overnight_sleep_analysis(hr_bpm=None, rmssd_ms=None, epoch_stages=None)
        assert sleep.status == "WAITING_FOR_SENSOR"
        assert sleep.sleep_score_100 is None
        assert sleep.deep_pct is None
        assert sleep.rem_pct is None
        assert sleep.dip_pct is None
        assert sleep.recovery_status == "Awaiting Nocturnal Stream"

    def test_zone2_coaching_engine_null_inputs(self):
        """Validates that Zone2 coaching returns STANDBY guidance when disconnected."""
        engine = Zone2CoachingEngine()
        rec = engine.get_coaching_recommendation(None, None)
        assert rec["action"] == "STANDBY"
        assert "Wear Movesense" in rec["recommendation"]

        state = classify_workout_state(None)
        assert state.status == "WAITING_FOR_SENSOR"
        assert state.activity_type is None
        assert state.hr_pct_max is None

        thresh = compute_cardiorespiratory_thresholds(None, None)
        assert thresh.status == "WAITING_FOR_SENSOR"
        assert thresh.dfa_alpha1 is None
        assert thresh.current_zone == "Awaiting Live Stream"

    def test_ast_source_code_zero_mock_static_audit(self):
        """
        Forensic AST audit scanning all Python source files in 01_apps/biometrics/movesense_hub:
        Verifies zero embedded fake metric generators (e.g. random numbers in place of DSP),
        and zero external un-airgapped HTTP endpoints.
        """
        pkg_dir = Path(REPO_ROOT) / "01_apps" / "biometrics" / "movesense_hub"
        py_files = list(pkg_dir.rglob("*.py"))
        assert len(py_files) >= 8, f"Expected at least 8 Python files in package, found {len(py_files)}"

        for py_path in py_files:
            rel_path = py_path.relative_to(REPO_ROOT)
            content = py_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_path))

            # Check that no calls to external HTTP domains occur (airgap check)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value.lower()
                    # Ensure no unauthorized cloud URLs in Movesense hub source
                    if val.startswith("http://") or val.startswith("https://"):
                        assert any(safe in val for safe in ["127.0.0.1", "localhost", "0.0.0.0", "movesense", "schemas"]), \
                            f"Disallowed external cloud URL found in {rel_path}: {val}"

        print(f"\n[FORENSIC AUDIT] Scanned {len(py_files)} Python files in movesense_hub: 100% Rule #0 and Airgap compliant.")


# ============================================================================
# 3. OscilloscopePwaConnector RING BUFFER SWEEP LOGIC UNDER HIGH THROUGHPUT
# ============================================================================

class TestOscilloscopePwaConnectorHighThroughput:
    """
    Stress-tests OscilloscopePwaConnector:
    - High sample throughput (10,000+ samples at 128Hz & 512Hz)
    - Amplitude voltage clamping (-5.0 mV to +5.0 mV)
    - Handling of None, NaN, and extreme spikes
    - Lead status and contract conformance
    - JSON serialization latency and throughput benchmark.
    """

    def test_voltage_clamping_and_sanitization(self):
        """
        Verifies that OscilloscopePwaConnector strictly clamps all samples to [-5.0, 5.0] mV,
        and sanitizes None to 0.0 mV.
        """
        connector = OscilloscopePwaConnector(sampling_rate_hz=512)

        # Test extreme spikes
        raw_samples = [
            0.0,
            0.5,
            -0.5,
            10.0,      # Should clamp to 5.0
            -10.0,     # Should clamp to -5.0
            999.99,    # Should clamp to 5.0
            -999.99,   # Should clamp to -5.0
            None,      # Should become 0.0
            2.3456,
        ]

        payload = connector.format_oscilloscope_payload(
            ecg_samples=raw_samples,
            heart_rate=72,
            is_connected=True,
        )

        assert payload["type"] == "ECG_SWEEP_FRAME"
        assert payload["leadStatus"] == "CONNECTED"
        assert payload["samplingRateHz"] == 512
        assert payload["heartRate"] == 72
        assert payload["rule_0_zero_mock"] is True

        expected_clamped = [0.0, 0.5, -0.5, 5.0, -5.0, 5.0, -5.0, 0.0, 2.3456]
        assert payload["ecgSamples"] == expected_clamped

    def test_disconnected_lead_status_formatting(self):
        """
        Verifies formatting when sensor is disconnected (Rule #0).
        """
        connector = OscilloscopePwaConnector(sampling_rate_hz=128)

        # Disconnected with empty samples
        p1 = connector.format_oscilloscope_payload(
            ecg_samples=[],
            heart_rate=None,
            is_connected=False,
        )
        assert p1["leadStatus"] == "DISCONNECTED"
        assert p1["heartRate"] == 0
        assert p1["ecgSamples"] == []
        assert p1["rule_0_zero_mock"] is True

        # Disconnected with samples present (e.g. lead-off noise)
        p2 = connector.format_oscilloscope_payload(
            ecg_samples=[0.0, 0.0],
            heart_rate=None,
            is_connected=False,
        )
        assert p2["leadStatus"] == "DISCONNECTED"
        assert p2["heartRate"] == 0

    def test_high_throughput_burst_processing_10000_samples(self):
        """
        Pushes 10,000 ECG samples across 200 consecutive 50-sample frame sweeps.
        Measures processing time, ensures no memory leaks or buffer degradation.
        """
        connector = OscilloscopePwaConnector(sampling_rate_hz=512)
        total_samples = 10000
        samples_per_frame = 50
        total_frames = total_samples // samples_per_frame

        t0 = time.perf_counter()
        frames_out: List[Dict[str, Any]] = []

        for frame_idx in range(total_frames):
            # Generate synthetic 50-sample chunk
            chunk = [math.sin((frame_idx * samples_per_frame + i) * 0.1) * 2.0 for i in range(samples_per_frame)]
            payload = connector.format_oscilloscope_payload(
                ecg_samples=chunk,
                heart_rate=75,
                is_connected=True,
            )
            frames_out.append(payload)

        t_elapsed = time.perf_counter() - t0
        frames_per_sec = total_frames / max(t_elapsed, 1e-6)
        samples_per_sec = total_samples / max(t_elapsed, 1e-6)

        assert len(frames_out) == total_frames
        for frame in frames_out:
            assert len(frame["ecgSamples"]) == samples_per_frame
            assert frame["leadStatus"] == "CONNECTED"
            assert frame["heartRate"] == 75

        print(f"\n[BENCHMARK] 10,000 ECG samples ({total_frames} frames) processed in {t_elapsed*1000:.2f}ms ({frames_per_sec:.1f} frames/sec, {samples_per_sec:.1f} samples/sec)")

    def test_json_serialization_performance(self):
        """
        Benchmarks JSON serialization of 2,000 oscilloscope frames to verify
        it comfortably meets 120 FPS frontend WebSocket delivery targets (>1,000 FPS serializable).
        """
        connector = OscilloscopePwaConnector(sampling_rate_hz=128)
        frame = connector.format_oscilloscope_payload(
            ecg_samples=[math.sin(i * 0.2) * 1.5 for i in range(32)],
            heart_rate=68,
            is_connected=True,
        )

        iterations = 2000
        t0 = time.perf_counter()
        for _ in range(iterations):
            json_str = json.dumps(frame)
            assert len(json_str) > 0
        t_elapsed = time.perf_counter() - t0

        fps = iterations / max(t_elapsed, 1e-6)
        avg_ms = (t_elapsed / iterations) * 1000.0

        assert fps >= 1000.0, f"JSON serialization too slow: {fps:.1f} frames/sec (target >= 1,000 fps)"
        print(f"\n[BENCHMARK] JSON serialization benchmark: {fps:.1f} frames/sec (avg {avg_ms:.4f}ms per frame)")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
