//! Milestone 3 Challenger 2 — Backend Ingestion & Thread Safety Adversarial Stress Test
//! Tests:
//! 1. Concurrent payload bursts (hundreds of parallel tasks hitting POST /api/biometrics/sample)
//! 2. Pathological and adversarial payload values (negative HR, out-of-bounds RR, extreme floats, malformed JSON, empty JSON)
//! 3. Thread safety, lock contention under Arc<Mutex<BiometricsEngine>>, and snapshot consistency across concurrent reader/writer storms.

use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use lauburu_core::biometrics::BiometricsEngine;
use lauburu_core::server::{create_router, AppState};
use parking_lot::Mutex;
use std::sync::Arc;
use tokio::sync::broadcast;
use tower::ServiceExt;

#[tokio::test]
async fn test_challenger2_pathological_and_boundary_payloads() {
    let (tx, _rx) = broadcast::channel(1024);
    let biometrics = Arc::new(Mutex::new(BiometricsEngine::new(512.0)));
    let state = AppState::new(biometrics.clone(), tx);
    let app = create_router(state);

    // 1. Empty JSON object: default values should be used without panic
    let empty_payload = serde_json::json!({});
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/biometrics/sample")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&empty_payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let res_json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(res_json["heart_rate_bpm"], 0.0);

    // 2. Negative HR & Negative RR intervals (Physiological Bounding Rejection)
    let negative_payload = serde_json::json!({
        "sample": -0.5,
        "heart_rate": -80.0,
        "rr_interval_ms": -500.0,
        "rmssd_ms": -35.0,
        "device_id": "Movesense-Negative-Test"
    });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/biometrics/sample")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&negative_payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let res_json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    // Negative HR should NOT overwrite resting 0.0 state
    assert_eq!(res_json["heart_rate_bpm"], 0.0);

    // 3. Array of pathological and extreme RR intervals (some out of 250..2200 range, some valid)
    let mixed_rr_payload = serde_json::json!({
        "sample": 0.12,
        "heart_rate": 78.0,
        "rr_intervals": [
            -100.0, // negative (invalid)
            50.0,   // too short (invalid)
            249.0,  // below 250 (invalid)
            800.0,  // VALID
            820.0,  // VALID
            2201.0, // above 2200 (invalid)
            9999.0  // extreme (invalid)
        ],
        "device_id": "Movesense-M3-Challenger2"
    });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/biometrics/sample")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&mixed_rr_payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let bio = biometrics.lock();
    assert_eq!(bio.latest_snapshot.heart_rate_bpm, 78.0);
    assert_eq!(bio.is_connected, true);
    assert_eq!(bio.device_id, "Movesense-M3-Challenger2");
    // Only 800.0 and 820.0 should have been ingested into rr_intervals
    assert_eq!(bio.detector.rr_intervals.len(), 2);
    assert_eq!(bio.detector.rr_intervals[0], 800.0);
    assert_eq!(bio.detector.rr_intervals[1], 820.0);
    drop(bio);

    // 4. Malformed JSON payload (type mismatch string for number)
    let malformed_payload = "{\"sample\": \"not_a_number\"}";
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/biometrics/sample")
                .header("Content-Type", "application/json")
                .body(Body::from(malformed_payload))
                .unwrap(),
        )
        .await
        .unwrap();
    // Axum should reject with 422 Unprocessable Entity without crashing
    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);

    // 5. Extreme float inputs (subnormal, large floats)
    let extreme_payload = serde_json::json!({
        "sample": 1e-15,
        "heart_rate": 220.0,
        "rr_interval_ms": 272.7,
        "rmssd_ms": 12.5
    });
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/biometrics/sample")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&extreme_payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let bio = biometrics.lock();
    assert_eq!(bio.latest_snapshot.heart_rate_bpm, 220.0);
    assert_eq!(bio.detector.current_rmssd, 12.5);
    drop(bio);
}

#[tokio::test]
async fn test_challenger2_concurrent_payload_burst_and_thread_safety() {
    let (tx, _rx) = broadcast::channel(4096);
    let biometrics = Arc::new(Mutex::new(BiometricsEngine::new(512.0)));
    let state = AppState::new(biometrics.clone(), tx);
    let app = create_router(state);

    let num_tasks = 20;
    let requests_per_task = 100;
    let mut handles = Vec::new();

    let start_time = std::time::Instant::now();

    for task_id in 0..num_tasks {
        let app_clone = app.clone();
        let handle = tokio::spawn(async move {
            for i in 0..requests_per_task {
                let sample_val = ((task_id * 100 + i) as f32 * 0.01).sin() * 0.5;
                let hr_val = 60.0 + ((i % 40) as f32);
                let rr_val = 60000.0 / hr_val;

                let payload = serde_json::json!({
                    "sample": sample_val,
                    "heart_rate": hr_val,
                    "rr_interval_ms": rr_val,
                    "device_id": format!("Movesense-Concurrent-Task-{}", task_id)
                });

                let response = app_clone
                    .clone()
                    .oneshot(
                        Request::builder()
                            .method("POST")
                            .uri("/api/biometrics/sample")
                            .header("Content-Type", "application/json")
                            .body(Body::from(serde_json::to_vec(&payload).unwrap()))
                            .unwrap(),
                    )
                    .await
                    .expect("Request should succeed");

                assert_eq!(response.status(), StatusCode::OK);
            }
        });
        handles.push(handle);
    }

    // Simultaneously run concurrent read tasks on /health, /api/biometrics/snapshot, /api/spatial/map
    let mut read_handles = Vec::new();
    for _ in 0..10 {
        let app_clone = app.clone();
        let read_handle = tokio::spawn(async move {
            for _ in 0..50 {
                let resp_snap = app_clone
                    .clone()
                    .oneshot(Request::builder().uri("/api/biometrics/snapshot").body(Body::empty()).unwrap())
                    .await
                    .unwrap();
                assert_eq!(resp_snap.status(), StatusCode::OK);

                let resp_health = app_clone
                    .clone()
                    .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
                    .await
                    .unwrap();
                assert_eq!(resp_health.status(), StatusCode::OK);

                let resp_spatial = app_clone
                    .clone()
                    .oneshot(Request::builder().uri("/api/spatial/map").body(Body::empty()).unwrap())
                    .await
                    .unwrap();
                assert_eq!(resp_spatial.status(), StatusCode::OK);
            }
        });
        read_handles.push(read_handle);
    }

    // Await all concurrent tasks
    for h in handles {
        h.await.expect("Ingestion worker task panicked");
    }
    for rh in read_handles {
        rh.await.expect("Reader worker task panicked");
    }

    let elapsed = start_time.elapsed();
    println!("Successfully processed 2,000 concurrent POST ingestion + 1,500 concurrent GET requests in {:?}", elapsed);

    // Verify final state integrity and lack of deadlock/corruption
    let bio = biometrics.lock();
    assert!(bio.is_connected);
    assert!(bio.latest_snapshot.heart_rate_bpm >= 60.0);
    assert_eq!(bio.detector.rr_intervals.len(), 60); // Clamped to rolling window of 60
    assert!(bio.latest_snapshot.readiness_score > 0.0);
}
