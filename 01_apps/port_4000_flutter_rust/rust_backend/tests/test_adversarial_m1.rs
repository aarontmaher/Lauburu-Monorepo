//! Milestone 1 Adversarial Stress & Oracle Test Suite.
//! Verifies zero-mock invariants, pathological float inputs, rapid transitions,
//! extreme heart rates, DFA edge cases, BLE packet corruption, spatial standby states,
//! uptime monotonicity, and C-FFI concurrency/memory safety.

use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::broadcast;
use tower::ServiceExt;

use lauburu_core::biometrics::{BiometricsEngine, MovesenseBleConnector};
use lauburu_core::bridge::c_api::*;
use lauburu_core::dsp::{DfaCalculator, PanTompkinsDetector};
use lauburu_core::server::{create_router, AppState, HealthResponse};
use lauburu_core::spatial::{Landmark3D, SpatialKinematicsEngine};

// =========================================================================
// 1. DSP & BiometricsEngine Zero-Sample & Boundary Conditions
// =========================================================================

#[test]
fn test_adversarial_zero_sample_stream_stability() {
    let mut engine = BiometricsEngine::new(512.0);

    // Ingest 10,000 continuous zero samples (equivalent to ~19.5 seconds of flatline)
    for _ in 0..10_000 {
        let res = engine.ingest_sample(0.0);
        assert!(!res.is_qrs_peak, "Zero baseline sample must NEVER trigger QRS peak");
        assert_eq!(res.heart_rate_bpm, 0.0, "Zero baseline HR must remain 0.0");
        assert_eq!(res.rr_interval_ms, 0.0, "Zero baseline RR must remain 0.0");
        assert_eq!(res.rmssd_ms, 0.0, "Zero baseline RMSSD must remain 0.0");
        assert_eq!(res.sdnn_ms, 0.0, "Zero baseline SDNN must remain 0.0");
        assert_eq!(res.pnn50_percent, 0.0, "Zero baseline pNN50 must remain 0.0");
    }

    let snap = &engine.latest_snapshot;
    assert!(!snap.connected, "Standby connected flag must be false");
    assert_eq!(snap.heart_rate_bpm, 0.0, "Standby HR must be 0.0");
    assert_eq!(snap.readiness_score, 0.0, "Standby readiness must be 0.0");
    assert_eq!(snap.dfa_alpha1, 0.0, "Standby DFA alpha1 must be 0.0");
    assert_eq!(snap.latest_ecg_sample, 0.0, "Standby latest sample must be 0.0");
    assert!(!snap.qrs_peak_detected, "Standby peak flag must be false");
    assert_eq!(snap.zone2_status, "Resting / Disconnected");
}

#[test]
fn test_adversarial_pathological_floats_and_extremes() {
    let mut engine = BiometricsEngine::new(512.0);

    let pathological_values = [
        f32::NAN,
        f32::INFINITY,
        f32::NEG_INFINITY,
        1e38,
        -1e38,
        1e-38,
        -1e-38,
        -9999.0,
        9999.0,
        0.0,
    ];

    for &val in &pathological_values {
        // Ingestion must not panic
        let _ = engine.ingest_sample(val);
    }

    // Engine must be resettable and recover clean state
    engine.detector.reset();
    let res = engine.ingest_sample(0.0);
    assert_eq!(res.heart_rate_bpm, 0.0);
    assert_eq!(res.rr_interval_ms, 0.0);
}

#[test]
fn test_adversarial_extreme_pacing_and_tachycardia_rejection() {
    let mut detector = PanTompkinsDetector::new(512.0);

    // 1. Pacing faster than refractory period (every 50 samples = ~97.6ms -> ~614 BPM)
    // Refractory period at 512Hz is 102 samples (200ms). Pulses within refractory period must be rejected.
    let mut peak_count = 0;
    for i in 0..2000 {
        let sample = if i % 50 == 0 { 5.0 } else { 0.0 };
        let res = detector.process_sample(sample);
        if res.is_qrs_peak {
            peak_count += 1;
        }
    }
    // At most 1 peak per ~102 samples: in 2000 samples, maximum ~20 peaks, NOT 40
    assert!(peak_count <= 20, "Refractory period must reject pulses spaced < 200ms");

    // 2. Pulses spaced by 200ms (5 Hz = 300 BPM).
    // RR intervals must be rejected by (250.0..=2200.0) guard in Pan-Tompkins
    let mut detector2 = PanTompkinsDetector::new(500.0);
    for _beat in 0..10 {
        for cycle_idx in 0..100 { // 100 samples at 500Hz = 200ms
            let sample = if cycle_idx == 5 { 4.0 } else { 0.0 };
            detector2.process_sample(sample);
        }
    }
    // All detected RR intervals should be 200ms, which is < 250ms, so rr_intervals buffer must remain empty
    assert!(
        detector2.rr_intervals.is_empty(),
        "RR intervals < 250ms (rate > 240 BPM) must NOT be added to physiological RR history"
    );
}

#[test]
fn test_adversarial_severe_bradycardia_and_flatline_rejection() {
    let mut detector = PanTompkinsDetector::new(500.0);

    // Pulses spaced by 3000ms (3.0s = 20 BPM -> 1500 samples at 500Hz)
    for _beat in 0..4 {
        for cycle_idx in 0..1500 {
            let sample = if cycle_idx == 5 { 4.0 } else { 0.0 };
            detector.process_sample(sample);
        }
    }

    // RR intervals are 3000ms, which exceeds 2200ms upper limit -> must not be stored in rr_intervals
    assert!(
        detector.rr_intervals.is_empty(),
        "RR intervals > 2200ms (rate < 27.2 BPM) must NOT be added to physiological RR history"
    );
}

#[test]
fn test_adversarial_constant_dc_offset_rejection() {
    let mut detector = PanTompkinsDetector::new(512.0);

    // Feed massive DC offset of +500.0 mV
    for _ in 0..500 {
        let res = detector.process_sample(500.0);
        assert!(!res.is_qrs_peak, "Constant DC bias must not trigger QRS peak");
    }

    // Feed negative DC offset of -500.0 mV
    for _ in 0..500 {
        let res = detector.process_sample(-500.0);
        assert!(!res.is_qrs_peak, "Constant negative DC bias must not trigger QRS peak");
    }
}

// =========================================================================
// 2. DFA Alpha-1 Calculator Adversarial Tests
// =========================================================================

#[test]
fn test_adversarial_dfa_edge_cases() {
    let mut dfa = DfaCalculator::new(60);
    assert_eq!(dfa.get_alpha1(), 0.0, "Initial DFA alpha1 must be 0.0");

    // Adding out-of-range RR intervals must be ignored
    assert_eq!(dfa.add_rr_interval(100.0), 0.0); // < 300ms ignored
    assert_eq!(dfa.add_rr_interval(2500.0), 0.0); // > 2000ms ignored
    assert_eq!(dfa.add_rr_interval(-500.0), 0.0); // negative ignored
    assert_eq!(dfa.add_rr_interval(f32::NAN), 0.0); // NaN ignored

    // Feed identical constant RR intervals (0 variance case)
    for _ in 0..40 {
        dfa.add_rr_interval(800.0);
    }
    // When fluctuations are 0, log_fluctuations is empty, so alpha1 must safely return 0.0 without division by zero
    let alpha_const = dfa.get_alpha1();
    assert_eq!(alpha_const, 0.0, "Zero-variance RR series must produce 0.0 alpha1 safely");

    // Feed 50 oscillating physiological RR intervals
    let mut dfa_phys = DfaCalculator::new(60);
    for i in 0..50 {
        let rr = 800.0 + ((i as f32 * 0.5).sin() * 50.0);
        dfa_phys.add_rr_interval(rr);
    }
    let alpha_phys = dfa_phys.get_alpha1();
    assert!(
        (0.25..=1.75).contains(&alpha_phys),
        "Physiological alpha1 {} must be clamped within [0.25, 1.75]",
        alpha_phys
    );
}

// =========================================================================
// 3. BLE Movesense Packet Parsing Adversarial Stress
// =========================================================================

#[test]
fn test_adversarial_movesense_packet_fuzzing() {
    let (tx, _rx) = broadcast::channel(16);
    let biometrics = Arc::new(parking_lot::Mutex::new(BiometricsEngine::new(512.0)));
    let connector = MovesenseBleConnector::new(biometrics.clone(), tx);

    // Empty packet
    connector.handle_raw_packet(None, &[]);

    // 1-byte packet (flags only)
    connector.handle_raw_packet(None, &[0x00]);
    connector.handle_raw_packet(None, &[0x01]); // 16-bit flag set, but payload truncated
    connector.handle_raw_packet(None, &[0x10]); // RR flag set, but payload truncated

    // 2-byte packet (8-bit HR)
    connector.handle_raw_packet(None, &[0x00, 140]); // HR = 140
    {
        let bio = biometrics.lock();
        assert_eq!(bio.latest_snapshot.heart_rate_bpm, 140.0);
        assert!(bio.latest_snapshot.connected);
    }

    // 3-byte packet (16-bit HR = 180 BPM)
    // 180 = 0x00B4 -> [0xB4, 0x00]
    connector.handle_raw_packet(None, &[0x01, 0xB4, 0x00]);
    {
        let bio = biometrics.lock();
        assert_eq!(bio.latest_snapshot.heart_rate_bpm, 180.0);
    }

    // Packet with 16-bit HR + multiple RR intervals (flags = 0x11)
    // HR = 75 BPM (0x004B), RR1 = 800ms (800 / 1000 * 1024 = 819 = 0x0333), RR2 = 820ms (820/1000*1024 = 839 = 0x0347)
    let pkt = vec![
        0x11, // 16-bit HR + RR present
        0x4B, 0x00, // HR = 75
        0x33, 0x03, // RR1 = 819 raw (800ms)
        0x47, 0x03, // RR2 = 839 raw (819.3ms)
    ];
    connector.handle_raw_packet(None, &pkt);
    {
        let bio = biometrics.lock();
        assert_eq!(bio.latest_snapshot.heart_rate_bpm, 75.0);
        assert!(bio.latest_snapshot.rr_interval_ms > 750.0);
    }

    // Corrupted trailing byte (odd length RR payload)
    let corrupt_pkt = vec![0x11, 0x4B, 0x00, 0x33, 0x03, 0xFF]; // 1 extra trailing byte
    connector.handle_raw_packet(None, &corrupt_pkt);
}

// =========================================================================
// 4. Spatial Kinematics Standby & Boundary Stress
// =========================================================================

#[test]
fn test_adversarial_spatial_standby_and_geometry() {
    let engine = SpatialKinematicsEngine::new();
    assert!(!engine.is_tracking_active);

    // Standby skeleton check
    let standby_nodes = engine.generate_standby_skeleton();
    assert_eq!(standby_nodes.len(), 33);
    for (i, node) in standby_nodes.iter().enumerate() {
        assert_eq!(node.id, i);
        assert_eq!(node.x, 0.0);
        assert_eq!(node.y, 0.0);
        assert_eq!(node.z, 0.0);
        assert_eq!(node.visibility, 0.0);
    }

    // Standby fusion check with various biometrics
    let state_idle = engine.fuse_with_movesense(0.0, 0.0, 0.0, 0.0);
    assert_eq!(state_idle.current_position, "Standby / Mat Empty");
    assert_eq!(state_idle.active_technique, "No Athlete Detected");
    assert_eq!(state_idle.center_of_mass, [0.0, 0.0, 0.0]);
    assert_eq!(state_idle.submission_risk_percent, 0.0);
    assert_eq!(state_idle.metabolic_stress_index, 0.0);
    assert!(state_idle.joint_torques.is_empty());

    // Standby fusion with physical HR > 0
    let state_hr = engine.fuse_with_movesense(160.0, 25.0, 0.65, 10.0);
    assert_eq!(state_hr.current_position, "Standby / Mat Empty");
    assert_eq!(state_hr.movesense_heart_rate, 160.0);
    assert!(state_hr.metabolic_stress_index > 0.0);
    assert_eq!(state_hr.submission_risk_percent, 0.0);
    // Landmarks must remain standby
    assert_eq!(state_hr.landmarks[0].visibility, 0.0);

    // Compute joint torques on degenerated / coincident / all-zero landmark array
    let degenerate_landmarks: Vec<Landmark3D> = (0..33)
        .map(|i| Landmark3D {
            id: i,
            name: format!("L{}", i),
            x: 0.0,
            y: 0.0,
            z: 0.0,
            visibility: 0.95,
        })
        .collect();
    let (torques, risk) = engine.compute_joint_torques(&degenerate_landmarks);
    assert_eq!(torques.len(), 3);
    assert!(risk >= 0.0 && risk <= 100.0);
}

// =========================================================================
// 5. Axum Server Dynamic Uptime & REST Stress
// =========================================================================

#[tokio::test]
async fn test_adversarial_server_dynamic_uptime_and_endpoints() {
    let (tx, _rx) = broadcast::channel(16);
    let biometrics = Arc::new(parking_lot::Mutex::new(BiometricsEngine::new(512.0)));
    let state = AppState {
        biometrics,
        tx_telemetry: tx,
        start_time: std::time::Instant::now() - Duration::from_secs(5), // Simulated 5s uptime
        npu: Arc::new(parking_lot::Mutex::new(lauburu_core::npu_analysis::NpuDataAnalysisEngine::default())),
    };

    let app = create_router(state);

    // 1. Initial /health request
    let resp1 = app
        .clone()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(resp1.status(), StatusCode::OK);
    let bytes1 = to_bytes(resp1.into_body(), 1024 * 16).await.unwrap();
    let health1: HealthResponse = serde_json::from_slice(&bytes1).unwrap();
    assert!(health1.uptime_seconds >= 5, "Uptime must reflect elapsed time");
    assert_eq!(health1.device_connected, false);
    assert_eq!(health1.current_hr_bpm, 0.0);
    assert_eq!(health1.readiness_score, 0.0);

    // 2. Ingest sample via REST POST /api/biometrics/sample with extreme values
    let sample_payload = serde_json::json!({"sample": 1.25});
    let resp_sample = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/biometrics/sample")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&sample_payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(resp_sample.status(), StatusCode::OK);

    // 3. Shopify Tier Verification Boundary Tests
    let tiers = [
        ("lauburu_pro_sub_12345", 1),
        ("lauburu_mesh_worker_node", 2),
        ("", 0),
        ("invalid_token_999", 0),
    ];
    for (token, expected_tier) in tiers {
        let payload = serde_json::json!({"token": token});
        let resp = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/api/shopify/verify")
                    .header("Content-Type", "application/json")
                    .body(Body::from(serde_json::to_vec(&payload).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let b = to_bytes(resp.into_body(), 1024 * 16).await.unwrap();
        let val: serde_json::Value = serde_json::from_slice(&b).unwrap();
        assert_eq!(val["tier_code"], expected_tier);
    }
}

// =========================================================================
// 6. C-FFI Bridge Multi-Threaded Concurrency & Memory Safety
// =========================================================================

#[test]
fn test_adversarial_c_ffi_concurrency_and_safety() {
    assert_eq!(lauburu_core_init(), 0);

    // Null safety
    assert_eq!(lauburu_verify_shopify_tier(std::ptr::null()), 0);
    lauburu_free_string(std::ptr::null_mut()); // Must not crash

    // Multi-threaded concurrent calls to FFI
    let mut handles = Vec::new();
    for thread_idx in 0..8 {
        let handle = std::thread::spawn(move || {
            for i in 0..1000 {
                let sample = ((i + thread_idx) as f32 * 0.1).sin();
                let _ = lauburu_process_ecg_sample(sample);
                let _ = lauburu_get_readiness_score();
                let _ = lauburu_get_hrv_rmssd();
                let _ = lauburu_get_dfa_alpha1();

                let json_ptr = lauburu_get_telemetry_json();
                assert!(!json_ptr.is_null());
                lauburu_free_string(json_ptr);
            }
        });
        handles.push(handle);
    }

    for h in handles {
        h.join().expect("FFI concurrency thread panicked");
    }
}
