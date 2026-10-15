use axum::http::StatusCode;
use std::sync::Arc;
use tokio::sync::broadcast;
use lauburu_core::server::{create_router, AppState, HealthResponse};
use lauburu_core::biometrics::{BiometricsEngine, BiometricTelemetrySnapshot};
use lauburu_core::spatial::SpatialGrapplingState;
use tower::ServiceExt;
use axum::http::Request;
use axum::body::{Body, to_bytes};

#[tokio::test]
async fn test_server_endpoints() {
    let (tx, _rx) = broadcast::channel(16);
    let biometrics = Arc::new(parking_lot::Mutex::new(BiometricsEngine::new(512.0)));
    let state = AppState::new(biometrics, tx);

    let app = create_router(state);

    // 1. Test /health (Zero-Mock dynamic uptime & initial resting state)
    let response = app
        .clone()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let health: HealthResponse = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(health.status, "HEALTHY");
    assert_eq!(health.service, "lauburu_port4000_core");
    assert_eq!(health.port, 4000);
    assert_eq!(health.device_connected, false);
    assert_eq!(health.current_hr_bpm, 0.0);
    assert_eq!(health.readiness_score, 0.0);
    assert_eq!(health.dfa_alpha1, 0.0);

    // 2. Test /api/biometrics/readiness (Zero-Mock initial resting state)
    let response = app
        .clone()
        .oneshot(Request::builder().uri("/api/biometrics/readiness").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let readiness_json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(readiness_json["readiness_score"], 0.0);
    assert_eq!(readiness_json["heart_rate_bpm"], 0.0);
    assert_eq!(readiness_json["hrv_rmssd_ms"], 0.0);
    assert_eq!(readiness_json["dfa_alpha1"], 0.0);
    assert_eq!(readiness_json["zone2_status"], "Resting / Disconnected");

    // 3. Test /api/biometrics/snapshot (Zero-Mock initial snapshot contract)
    let response = app
        .clone()
        .oneshot(Request::builder().uri("/api/biometrics/snapshot").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let snapshot: BiometricTelemetrySnapshot = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(snapshot.connected, false);
    assert_eq!(snapshot.heart_rate_bpm, 0.0);
    assert_eq!(snapshot.readiness_score, 0.0);
    assert_eq!(snapshot.dfa_alpha1, 0.0);
    assert_eq!(snapshot.latest_ecg_sample, 0.0);
    assert_eq!(snapshot.qrs_peak_detected, false);
    assert_eq!(snapshot.zone2_status, "Resting / Disconnected");

    // 4. Test /api/spatial/map (Zero-Mock standby state)
    let response = app
        .clone()
        .oneshot(Request::builder().uri("/api/spatial/map").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 32).await.unwrap();
    let spatial: SpatialGrapplingState = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(spatial.current_position, "Standby / Mat Empty");
    assert_eq!(spatial.active_technique, "No Athlete Detected");
    assert_eq!(spatial.movesense_heart_rate, 0.0);
    assert_eq!(spatial.metabolic_stress_index, 0.0);
    assert_eq!(spatial.landmarks.len(), 33);
    assert!(spatial.joint_torques.is_empty());

    // 5. Test /api/shopify/verify (Multi-Tier Token Verification)
    let verify_pro = serde_json::json!({"token": "lauburu_pro_sample_token"});
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/shopify/verify")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&verify_pro).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let pro_json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(pro_json["tier_code"], 1);

    let verify_free = serde_json::json!({"token": "invalid_guest_token"});
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/shopify/verify")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&verify_free).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let free_json: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(free_json["tier_code"], 0);

    // 6. Test /api/biometrics/sample (Flexible Web Bluetooth Ingestion)
    let sample_payload = serde_json::json!({
        "sample": 0.25,
        "heart_rate": 145.0,
        "rr_interval_ms": 413.8,
        "device_id": "Movesense-M3-Pixel"
    });
    let response = app
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
    assert_eq!(response.status(), StatusCode::OK);
    let body_bytes = to_bytes(response.into_body(), 1024 * 16).await.unwrap();
    let sample_res: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap();
    assert_eq!(sample_res["heart_rate_bpm"], 145.0);
    let rr_res = sample_res["rr_interval_ms"].as_f64().unwrap();
    assert!((rr_res - 413.8).abs() < 1e-3);

    // 7. Test /api/npu/status (Zero-Copy Systolic Hardware Accelerator)
    let npu_status_resp = app
        .clone()
        .oneshot(Request::builder().uri("/api/npu/status").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(npu_status_resp.status(), StatusCode::OK);
    let npu_status_bytes = to_bytes(npu_status_resp.into_body(), 1024 * 16).await.unwrap();
    let npu_hw: serde_json::Value = serde_json::from_slice(&npu_status_bytes).unwrap();
    assert_eq!(npu_hw["status"], "ONLINE_ACTIVE");
    assert_eq!(npu_hw["zero_copy_shared_memory"], true);
    assert_eq!(npu_hw["host_ram_allocation_bytes"], 0);
    assert!(npu_hw["peak_tops"].as_f64().unwrap() >= 14.0);

    // 8. Test /api/npu/analysis (Live Biometrics & Kinematics Systolic Snapshot)
    let npu_analysis_resp = app
        .clone()
        .oneshot(Request::builder().uri("/api/npu/analysis").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(npu_analysis_resp.status(), StatusCode::OK);
    let npu_analysis_bytes = to_bytes(npu_analysis_resp.into_body(), 1024 * 16).await.unwrap();
    let npu_snap: serde_json::Value = serde_json::from_slice(&npu_analysis_bytes).unwrap();
    assert!(npu_snap["mean_inference_latency_us"].as_f64().unwrap() < 250.0);
    assert_eq!(npu_snap["kinematics"]["biomechanical_danger_level"], "SAFE_NOMINAL");

    // 9. Test /api/npu/analyze (POST with Active Joint Danger Angles)
    let npu_req_payload = serde_json::json!({
        "heart_rate": 165.0,
        "rr_interval_ms": 363.6,
        "arm_angle_rad": 1.57,
        "knee_angle_rad": 0.5,
        "shoulder_angle_rad": 0.3
    });
    let npu_post_resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/npu/analyze")
                .header("Content-Type", "application/json")
                .body(Body::from(serde_json::to_vec(&npu_req_payload).unwrap()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(npu_post_resp.status(), StatusCode::OK);
    let npu_post_bytes = to_bytes(npu_post_resp.into_body(), 1024 * 16).await.unwrap();
    let npu_post_snap: serde_json::Value = serde_json::from_slice(&npu_post_bytes).unwrap();
    assert_eq!(npu_post_snap["kinematics"]["biomechanical_danger_level"], "CAUTION_PRESSURE_APPLIED");
    assert!(npu_post_snap["kinematics"]["tap_probability_pct"].as_f64().unwrap() > 50.0);
}
