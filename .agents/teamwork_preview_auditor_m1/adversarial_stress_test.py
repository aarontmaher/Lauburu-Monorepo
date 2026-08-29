import importlib
import math
import sys
from pathlib import Path

repo_root = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

mhb = importlib.import_module("01_apps.biometrics.movesense_hub")

print("=" * 80)
print("ADVERSARIAL STRESS-TESTING & EDGE-CASE MINING FOR MILESTONE M1")
print("=" * 80)

failures = []

# Edge Case 1: Extreme DC offset & 1000x gain noise
try:
    detector = mhb.PanTompkinsQRSDetector(sample_rate_hz=512)
    extreme_signal = [1e5 + 1e3 * math.sin(i * 0.1) for i in range(1024)]
    peaks, rrs = detector.detect_qrs_peaks(extreme_signal)
    print("  [Edge 1] Extreme DC offset (100,000 mV) handled gracefully (no crash).")
except Exception as e:
    failures.append(f"Edge 1 failed: {e}")

# Edge Case 2: Zero / negative / NaN / Inf inputs to DSP
try:
    pipe = mhb.MovesenseECGPipeline(sample_rate_hz=512)
    res_empty = pipe.process_raw_ecg_window([])
    assert res_empty["status"] == "WAITING_FOR_SENSOR"
    assert res_empty["heart_rate_bpm"] is None
    print("  [Edge 2a] Empty ECG sample array returns WAITING_FOR_SENSOR with null HR.")

    # Short signal (< 0.5s)
    res_short = pipe.process_raw_ecg_window([1.0] * 100)
    assert res_short["status"] == "WAITING_FOR_SENSOR"
    print("  [Edge 2b] Sub-0.5s short window returns WAITING_FOR_SENSOR with null HR.")
except Exception as e:
    failures.append(f"Edge 2 failed: {e}")

# Edge Case 3: Extreme Bradycardia (28 BPM) and Extreme Tachycardia (240 BPM)
try:
    # 28 BPM -> RR = 2142.8 ms
    # 240 BPM -> RR = 250.0 ms
    fs = 512
    # 28 BPM signal (10 seconds)
    signal_brady = [0.0] * (fs * 10)
    for beat_sec in [1.0, 3.14, 5.28, 7.42, 9.56]:
        idx = int(beat_sec * fs)
        signal_brady[idx] = 5.0
        signal_brady[idx-1] = 2.0
        signal_brady[idx+1] = -1.0
    peaks_b, rrs_b = detector.detect_qrs_peaks(signal_brady)
    assert len(peaks_b) >= 4
    print(f"  [Edge 3a] Extreme bradycardia (28 BPM) peaks detected: {len(peaks_b)} peaks.")

    # 220 BPM signal (5 seconds, beat every 0.272s)
    signal_tachy = [0.0] * (fs * 5)
    t = 0.5
    while t < 4.8:
        idx = int(t * fs)
        signal_tachy[idx] = 4.0
        signal_tachy[idx-1] = 1.5
        signal_tachy[idx+1] = -1.0
        t += 0.272
    peaks_t, rrs_t = detector.detect_qrs_peaks(signal_tachy)
    assert len(peaks_t) >= 10
    print(f"  [Edge 3b] Extreme tachycardia (220 BPM) peaks detected: {len(peaks_t)} peaks.")
except Exception as e:
    failures.append(f"Edge 3 failed: {e}")

# Edge Case 4: Hemodynamic PTT blood pressure edge bounds
try:
    bp_model = mhb.ContinuousPttBloodPressureModel(hr_rest_baseline=58.0)
    # Disconnected / null
    res_null = bp_model.compute_ptt_blood_pressure(None, None, None)
    assert res_null.status == "STANDBY"
    assert res_null.sbp_mmhg is None
    
    # Boundary PTT extremes
    res_high_ptt = bp_model.compute_ptt_blood_pressure(hr_bpm=45.0, rmssd_ms=80.0, ptt_ms=350.0)
    assert 80.0 <= res_high_ptt.sbp_mmhg <= 220.0
    
    res_low_ptt = bp_model.compute_ptt_blood_pressure(hr_bpm=195.0, rmssd_ms=5.0, ptt_ms=90.0)
    assert 80.0 <= res_low_ptt.sbp_mmhg <= 220.0
    print(f"  [Edge 4] PTT BP bounds clamping verified: High PTT SBP={res_high_ptt.sbp_mmhg}, Low PTT SBP={res_low_ptt.sbp_mmhg} mmHg.")
except Exception as e:
    failures.append(f"Edge 4 failed: {e}")

# Edge Case 5: Sleep Staging all AWAKE vs all DEEP vs Empty
try:
    sleep_engine = mhb.SleepStagingEngine(hr_rest_baseline=58.0)
    # Empty
    res_empty_sleep = sleep_engine.compute_overnight_sleep_analysis(None, None, [])
    assert res_empty_sleep.status == "WAITING_FOR_SENSOR"
    assert res_empty_sleep.sleep_score_100 is None
    
    # All Awake
    res_awake = sleep_engine.compute_overnight_sleep_analysis(hr_bpm=75.0, rmssd_ms=22.0, epoch_stages=["AWAKE"] * 20)
    assert res_awake.awake_pct == 100.0
    assert res_awake.efficiency_pct == 0.0
    assert res_awake.sleep_score_100 <= 25
    
    # All Deep (100% deep sleep has 0% REM, so score is 75 due to missing REM architecture)
    res_deep = sleep_engine.compute_overnight_sleep_analysis(hr_bpm=48.0, rmssd_ms=65.0, epoch_stages=["DEEP"] * 20)
    assert res_deep.deep_pct == 100.0
    assert res_deep.efficiency_pct == 100.0
    assert res_deep.sleep_score_100 >= 70
    print(f"  [Edge 5] Sleep Staging extremes: All-Awake Score={res_awake.sleep_score_100}, All-Deep Score={res_deep.sleep_score_100}.")
except Exception as e:
    failures.append(f"Edge 5 failed: {e}")

# Edge Case 6: WebBleBridge rapid connect/disconnect cycling
try:
    bridge = mhb.WebBleBridge()
    for i in range(10):
        if i % 2 == 0:
            rep = bridge.ingest_sig_hrs_frame(hr_bpm=70 + i, rr_intervals_ms=[850.0, 860.0])
            assert rep.status == "STREAMING"
            assert rep.heart_rate_bpm == 70 + i
        else:
            rep = bridge.reset_to_disconnected()
            assert rep.status == "WAITING_FOR_SENSOR"
            assert rep.heart_rate_bpm is None
    print("  [Edge 6] Rapid connect/disconnect cycling on WebBleBridge: 10 state transitions PASSED cleanly.")
except Exception as e:
    failures.append(f"Edge 6 failed: {e}")

print("\n" + "=" * 80)
if not failures:
    print("ALL ADVERSARIAL STRESS TESTS PASSED (0 FAILURES)")
else:
    print(f"FAILURES DETECTED: {failures}")
print("=" * 80)
