//! Adversarial Verification Test Suite for Milestone 1:
//! 1. 3D Spatial Grappling Kinematics (33 landmarks, zero visibility standby, joint torques).
//! 2. Concurrency Model (Tokio tasks, WebSocket broadcast, Mutex contention, race conditions, deadlocks).

use std::sync::Arc;
use std::time::Duration;
use tokio::sync::broadcast;
use futures::StreamExt;
use tokio_tungstenite::connect_async;

use lauburu_core::spatial::{
    SpatialKinematicsEngine, SpatialGrapplingState, Landmark3D, LANDMARK_NAMES,
};
use lauburu_core::biometrics::BiometricsEngine;
use lauburu_core::server::{create_router, AppState};

#[test]
fn test_adversarial_spatial_standby_landmarks_exact_33() {
    let engine = SpatialKinematicsEngine::new();
    let skeleton = engine.generate_standby_skeleton();

    // 1. Exact count invariant
    assert_eq!(skeleton.len(), 33, "Standby skeleton MUST have exactly 33 landmarks");

    // 2. Strict ID and naming parity with MediaPipe standard
    for (i, lm) in skeleton.iter().enumerate() {
        assert_eq!(lm.id, i, "Landmark ID {} must match array index {}", lm.id, i);
        assert_eq!(lm.name, LANDMARK_NAMES[i], "Landmark name mismatch at index {}", i);
        assert_eq!(lm.x, 0.0, "Standby landmark {} X coordinate must be strictly 0.0", lm.name);
        assert_eq!(lm.y, 0.0, "Standby landmark {} Y coordinate must be strictly 0.0", lm.name);
        assert_eq!(lm.z, 0.0, "Standby landmark {} Z coordinate must be strictly 0.0", lm.name);
        assert_eq!(lm.visibility, 0.0, "Standby landmark {} visibility must be strictly 0.0", lm.name);
    }
}

#[test]
fn test_adversarial_spatial_active_tatami_bounds() {
    let mut engine = SpatialKinematicsEngine::new();
    engine.is_tracking_active = true;

    // Stress test 500 timesteps across active tatami coordinates
    for step in 0..500 {
        let t = step as f32 * 0.05;
        let skeleton = engine.generate_tatami_skeleton(t);
        assert_eq!(skeleton.len(), 33);

        for lm in &skeleton {
            assert!(lm.x >= -5.0 && lm.x <= 5.0, "X coordinate {} out of bounds [-5.0, 5.0]", lm.x);
            assert!(lm.y >= 0.0 && lm.y <= 2.5, "Y coordinate {} out of bounds [0.0, 2.5]", lm.y);
            assert!(lm.z >= -5.0 && lm.z <= 5.0, "Z coordinate {} out of bounds [-5.0, 5.0]", lm.z);
            assert_eq!(lm.visibility, 0.95, "Active landmark visibility must be 0.95");
        }
    }
}

#[test]
fn test_adversarial_joint_torques_degenerate_and_boundary_cases() {
    let engine = SpatialKinematicsEngine::new();

    // Case 1: Standby skeleton (all visibility = 0.0) -> must yield empty torques and 0.0 risk
    let standby_skeleton = engine.generate_standby_skeleton();
    let (torques, risk) = engine.compute_joint_torques(&standby_skeleton);
    assert!(torques.is_empty(), "Standby skeleton must yield 0 joint torques");
    assert_eq!(risk, 0.0, "Standby skeleton must yield 0.0 submission risk");

    // Case 2: Insufficient landmarks (< 29 landmarks)
    let truncated: Vec<Landmark3D> = standby_skeleton.into_iter().take(20).collect();
    let (torques, risk) = engine.compute_joint_torques(&truncated);
    assert!(torques.is_empty());
    assert_eq!(risk, 0.0);

    // Case 3: Degenerate collinear / coincident landmarks (zero distance vectors)
    let mut degenerate_skeleton = Vec::with_capacity(33);
    for i in 0..33 {
        degenerate_skeleton.push(Landmark3D {
            id: i,
            name: format!("Node_{}", i),
            x: 1.0, // all points at exact same position
            y: 1.0,
            z: 1.0,
            visibility: 1.0,
        });
    }
    let (torques, risk) = engine.compute_joint_torques(&degenerate_skeleton);
    assert_eq!(torques.len(), 3);
    assert!(risk >= 0.0 && risk <= 100.0, "Risk must be clamped [0, 100], got {}", risk);
    for torque in torques {
        assert!(!torque.angle_deg.is_nan(), "Angle must not be NaN");
        assert!(!torque.torque_nm.is_nan(), "Torque must not be NaN");
    }
}

#[test]
fn test_adversarial_fusion_standby_zero_mock_invariants() {
    let engine = SpatialKinematicsEngine::new();

    // 1. Standby with disconnected biometrics
    let state_disconnected = engine.fuse_with_movesense(0.0, 0.0, 0.0, 0.0);
    assert_eq!(state_disconnected.current_position, "Standby / Mat Empty");
    assert_eq!(state_disconnected.active_technique, "No Athlete Detected");
    assert_eq!(state_disconnected.center_of_mass, [0.0, 0.0, 0.0]);
    assert_eq!(state_disconnected.athlete_velocity_mps, 0.0);
    assert_eq!(state_disconnected.submission_risk_percent, 0.0);
    assert_eq!(state_disconnected.movesense_heart_rate, 0.0);
    assert_eq!(state_disconnected.movesense_rmssd, 0.0);
    assert_eq!(state_disconnected.movesense_dfa_alpha1, 0.0);
    assert_eq!(state_disconnected.metabolic_stress_index, 0.0);
    assert_eq!(state_disconnected.landmarks.len(), 33);
    assert!(state_disconnected.joint_torques.is_empty());

    // 2. Standby with active Movesense biometrics (HR=165, RMSSD=18ms) but video tracking standby
    let state_active_bio = engine.fuse_with_movesense(165.0, 18.0, 0.65, 45.0);
    assert_eq!(state_active_bio.current_position, "Standby / Mat Empty");
    assert_eq!(state_active_bio.active_technique, "No Athlete Detected");
    assert_eq!(state_active_bio.center_of_mass, [0.0, 0.0, 0.0]);
    assert_eq!(state_active_bio.athlete_velocity_mps, 0.0);
    assert_eq!(state_active_bio.submission_risk_percent, 0.0);
    assert!(state_active_bio.metabolic_stress_index > 0.0, "Metabolic stress should reflect HR/RMSSD");
    assert_eq!(state_active_bio.landmarks.len(), 33);
    assert!(state_active_bio.joint_torques.is_empty(), "Joint torques must remain empty in standby mode");
}

#[test]
fn test_adversarial_spatial_state_json_roundtrip() {
    let engine = SpatialKinematicsEngine::new();
    let state = engine.fuse_with_movesense(0.0, 0.0, 0.0, 0.0);

    let json_str = serde_json::to_string(&state).expect("Serialization failed");
    let json_val: serde_json::Value = serde_json::from_str(&json_str).expect("JSON parsing failed");

    // Check JSON schema compliance
    assert!(json_val.get("timestamp").is_some());
    assert_eq!(json_val["current_position"], "Standby / Mat Empty");
    assert_eq!(json_val["active_technique"], "No Athlete Detected");
    assert_eq!(json_val["center_of_mass"], serde_json::json!([0.0, 0.0, 0.0]));
    assert_eq!(json_val["athlete_velocity_mps"], 0.0);
    assert_eq!(json_val["submission_risk_percent"], 0.0);
    assert_eq!(json_val["landmarks"].as_array().unwrap().len(), 33);
    assert_eq!(json_val["joint_torques"].as_array().unwrap().len(), 0);

    let deserialized: SpatialGrapplingState = serde_json::from_str(&json_str).expect("Deserialization failed");
    assert_eq!(deserialized.landmarks.len(), 33);
    assert_eq!(deserialized.joint_torques.len(), 0);
}

#[tokio::test]
async fn test_adversarial_concurrency_tokio_websocket_and_rest_hammer() {
    // Spawn server on dynamic ephemeral port
    let (tx, _rx) = broadcast::channel(1024);
    let biometrics = Arc::new(parking_lot::Mutex::new(BiometricsEngine::new(512.0)));
    let state = AppState::new(biometrics.clone(), tx.clone());

    let router = create_router(state);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.expect("Failed to bind ephemeral listener");
    let local_addr = listener.local_addr().expect("Failed to get local addr");
    let server_port = local_addr.port();

    // Spawn server in background task
    let server_handle = tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });

    // Spawn 125Hz background telemetry generator (same as server.rs)
    let bio_clone = biometrics.clone();
    let tx_clone = tx.clone();
    let tele_loop = tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_millis(8));
        for _ in 0..100 {
            interval.tick().await;
            let mut bio = bio_clone.lock();
            bio.ingest_sample(0.0);
            let snapshot_json = serde_json::to_string(&bio.latest_snapshot).unwrap_or_default();
            drop(bio);
            let _ = tx_clone.send(snapshot_json);
        }
    });

    // 1. Connect 10 concurrent WebSocket clients to /ws/spatial
    let mut ws_spatial_handles = Vec::new();
    for _i in 0..10 {
        let port = server_port;
        ws_spatial_handles.push(tokio::spawn(async move {
            let url = format!("ws://127.0.0.1:{}/ws/spatial", port);
            let (ws_stream, _) = connect_async(&url).await.expect("Failed to connect spatial WS");
            let (_, mut read) = ws_stream.split();
            let mut received_count = 0;
            while let Some(msg) = read.next().await {
                if let Ok(tokio_tungstenite::tungstenite::Message::Text(text)) = msg {
                    let parsed: serde_json::Value = serde_json::from_str(&text).expect("Valid JSON");
                    assert_eq!(parsed["landmarks"].as_array().unwrap().len(), 33);
                    received_count += 1;
                    if received_count >= 10 {
                        break;
                    }
                }
            }
            received_count
        }));
    }

    // 2. Connect 10 concurrent WebSocket clients to /ws/telemetry
    let mut ws_tele_handles = Vec::new();
    for _ in 0..10 {
        let port = server_port;
        ws_tele_handles.push(tokio::spawn(async move {
            let url = format!("ws://127.0.0.1:{}/ws/telemetry", port);
            let (ws_stream, _) = connect_async(&url).await.expect("Failed to connect telemetry WS");
            let (_, mut read) = ws_stream.split();
            let mut received_count = 0;
            while let Some(msg) = read.next().await {
                if let Ok(tokio_tungstenite::tungstenite::Message::Text(text)) = msg {
                    let parsed: serde_json::Value = serde_json::from_str(&text).expect("Valid JSON");
                    assert_eq!(parsed["connected"], false);
                    received_count += 1;
                    if received_count >= 10 {
                        break;
                    }
                }
            }
            received_count
        }));
    }

    // 3. Concurrently hammer REST endpoints with 15 concurrent worker tasks (30 requests each = 450 requests)
    let client = reqwest::Client::new();
    let mut rest_handles = Vec::new();
    for worker_id in 0..15 {
        let client = client.clone();
        let port = server_port;
        rest_handles.push(tokio::spawn(async move {
            for req_id in 0..30 {
                let ep = match req_id % 4 {
                    0 => format!("http://127.0.0.1:{}/health", port),
                    1 => format!("http://127.0.0.1:{}/api/biometrics/snapshot", port),
                    2 => format!("http://127.0.0.1:{}/api/biometrics/readiness", port),
                    _ => format!("http://127.0.0.1:{}/api/spatial/map", port),
                };
                let resp = client.get(&ep).send().await.expect("REST request failed");
                assert_eq!(resp.status(), 200, "Worker {} endpoint {} failed", worker_id, ep);
            }
        }));
    }

    // 4. Concurrently POST raw ECG samples to /api/biometrics/sample
    let mut ingest_handles = Vec::new();
    for _ in 0..5 {
        let client = client.clone();
        let port = server_port;
        ingest_handles.push(tokio::spawn(async move {
            for s in 0..20 {
                let sample_val = (s as f32 * 0.1).sin();
                let resp = client
                    .post(format!("http://127.0.0.1:{}/api/biometrics/sample", port))
                    .json(&serde_json::json!({ "sample": sample_val }))
                    .send()
                    .await
                    .expect("Ingest sample POST failed");
                assert_eq!(resp.status(), 200);
            }
        }));
    }

    // Await all concurrent tasks
    for handle in ws_spatial_handles {
        let count = handle.await.expect("Spatial WS task failed");
        assert!(count >= 10, "Spatial WS must receive at least 10 frames");
    }

    for handle in ws_tele_handles {
        let count = handle.await.expect("Telemetry WS task failed");
        assert!(count >= 10, "Telemetry WS must receive at least 10 frames");
    }

    for handle in rest_handles {
        handle.await.expect("REST worker task failed");
    }

    for handle in ingest_handles {
        handle.await.expect("Ingest worker task failed");
    }

    tele_loop.abort();
    server_handle.abort();
}

#[tokio::test]
async fn test_adversarial_broadcast_channel_lag_tolerance() {
    let (tx, mut rx) = broadcast::channel(16); // Small buffer of 16 messages

    // Send 32 messages (buffer is 16, so 16 messages will be skipped for this subscriber)
    for i in 0..32 {
        let _ = tx.send(format!("msg_{}", i));
    }

    // Attempting to read from a lagged receiver returns RecvError::Lagged(16)
    match rx.recv().await {
        Err(broadcast::error::RecvError::Lagged(skipped)) => {
            assert_eq!(skipped, 16, "Must report exactly 16 skipped messages");
        }
        Ok(msg) => panic!("Expected Lagged error, got message: {}", msg),
        Err(e) => panic!("Unexpected error: {:?}", e),
    }

    // Subsequent read recovers and returns the oldest message currently retained in buffer (msg_16)
    let next_msg = rx.recv().await.expect("Subsequent read should succeed");
    assert_eq!(next_msg, "msg_16");
}

#[test]
fn test_adversarial_joint_torque_danger_transitions() {
    let mut engine = SpatialKinematicsEngine::new();
    engine.is_tracking_active = true;

    // Construct custom skeleton to trigger exact danger threshold on elbow
    // Landmark 11 = Shoulder (0, 1, 0), Landmark 13 = Elbow (0, 0, 0), Landmark 15 = Wrist (0.5, 0.866025, 0)
    // Angle = 30 degrees -> (180 - 30) * 0.38 = 150 * 0.38 = 57.0 N*m > 40.0 N*m (Danger threshold is 40.0 N*m)
    let mut danger_skeleton = engine.generate_tatami_skeleton(0.0);
    danger_skeleton[11] = Landmark3D { id: 11, name: "Left Shoulder".into(), x: 0.0, y: 1.0, z: 0.0, visibility: 1.0 };
    danger_skeleton[13] = Landmark3D { id: 13, name: "Left Elbow".into(), x: 0.0, y: 0.0, z: 0.0, visibility: 1.0 };
    danger_skeleton[15] = Landmark3D { id: 15, name: "Left Wrist".into(), x: 0.5, y: 0.866025, z: 0.0, visibility: 1.0 };

    let (torques, risk) = engine.compute_joint_torques(&danger_skeleton);
    assert_eq!(torques.len(), 3);
    
    let elbow = &torques[0];
    assert_eq!(elbow.joint_name, "Left Elbow Extension");
    assert!((elbow.angle_deg - 30.0).abs() < 0.1, "Elbow angle should be ~30 deg, got {}", elbow.angle_deg);
    assert!((elbow.torque_nm - 57.0).abs() < 0.1, "Elbow torque should be ~57.0 Nm, got {}", elbow.torque_nm);
    assert!(elbow.is_danger, "Elbow must be flagged as is_danger = true since 57.0 > 40.0");
    assert!(risk > 0.0 && risk <= 100.0, "Submission risk should be non-zero and clamped");
}

#[tokio::test]
async fn test_adversarial_abrupt_websocket_churn_and_lifecycle() {
    let (tx, _rx) = broadcast::channel(1024);
    let biometrics = Arc::new(parking_lot::Mutex::new(BiometricsEngine::new(512.0)));
    let state = AppState::new(biometrics.clone(), tx.clone());

    let router = create_router(state);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.expect("Failed to bind ephemeral listener");
    let server_port = listener.local_addr().unwrap().port();

    let server_handle = tokio::spawn(async move {
        axum::serve(listener, router).await.unwrap();
    });

    // Spawn 125Hz background telemetry generator
    let bio_clone = biometrics.clone();
    let tx_clone = tx.clone();
    let tele_loop = tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_millis(8));
        loop {
            interval.tick().await;
            let mut bio = bio_clone.lock();
            bio.ingest_sample(0.0);
            let snapshot_json = serde_json::to_string(&bio.latest_snapshot).unwrap_or_default();
            drop(bio);
            let _ = tx_clone.send(snapshot_json);
        }
    });

    // Churn 30 WebSocket connections in rapid succession (connect, read 2 messages, drop socket)
    for cycle in 0..30 {
        let url = if cycle % 2 == 0 {
            format!("ws://127.0.0.1:{}/ws/spatial", server_port)
        } else {
            format!("ws://127.0.0.1:{}/ws/telemetry", server_port)
        };

        let (ws_stream, _) = connect_async(&url).await.expect("Connect failed");
        let (_, mut read) = ws_stream.split();
        let mut count = 0;
        while let Some(msg) = read.next().await {
            if let Ok(_) = msg {
                count += 1;
                if count >= 2 {
                    break; // Abrupt drop!
                }
            }
        }
        // Explicitly drop stream
        drop(read);
    }

    // After 30 churn cycles, verify server is still responsive and healthy
    let client = reqwest::Client::new();
    let health_resp = client
        .get(format!("http://127.0.0.1:{}/health", server_port))
        .send()
        .await
        .expect("Server health check failed after churn");
    assert_eq!(health_resp.status(), 200);

    tele_loop.abort();
    server_handle.abort();
}

#[test]
fn test_adversarial_lock_contention_parallel_threads() {
    use std::thread;

    let engine = Arc::new(parking_lot::Mutex::new(BiometricsEngine::new(512.0)));
    let mut handles = Vec::new();

    // 8 concurrent writer threads ingesting samples
    for writer_id in 0..8 {
        let engine_clone = engine.clone();
        handles.push(thread::spawn(move || {
            for i in 0..200 {
                let sample = ((writer_id * 100 + i) as f32 * 0.05).sin();
                let mut guard = engine_clone.lock();
                guard.ingest_sample(sample);
            }
        }));
    }

    // 8 concurrent reader threads reading snapshot
    for _ in 0..8 {
        let engine_clone = engine.clone();
        handles.push(thread::spawn(move || {
            for _ in 0..200 {
                let guard = engine_clone.lock();
                let snap = &guard.latest_snapshot;
                assert!(snap.sample_rate_hz == 512.0);
            }
        }));
    }

    for handle in handles {
        handle.join().expect("Thread panicked during lock contention test");
    }

    let final_guard = engine.lock();
    assert_eq!(final_guard.latest_snapshot.sample_rate_hz, 512.0);
}
