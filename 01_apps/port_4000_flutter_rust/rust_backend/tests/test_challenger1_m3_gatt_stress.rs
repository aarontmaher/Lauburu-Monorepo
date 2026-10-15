// Milestone 3 Adversarial Challenger 1 — Rust Backend GATT & Ingestion Stress Test
// Tests native BLE GATT packet decoding, Pan-Tompkins DSP integration, and sample flood throughput.

use lauburu_core::biometrics::ble_movesense::MovesenseBleConnector;
use lauburu_core::biometrics::BiometricsEngine;
use parking_lot::Mutex;
use std::sync::Arc;
use tokio::sync::broadcast;

#[tokio::test]
async fn test_challenger1_rust_gatt_pathological_payloads() {
    let bio_engine = Arc::new(Mutex::new(BiometricsEngine::new(512.0)));
    let (tx, mut rx) = broadcast::channel(128);
    let connector = MovesenseBleConnector::new(bio_engine.clone(), tx);

    // 1. Empty byte slice (returns early, no panic)
    connector.handle_raw_packet(None, &[]);

    // 2. 1-byte truncated flags (HR defaults to 0.0 without panic)
    connector.handle_raw_packet(None, &[0x00]);
    let _ = rx.recv().await;

    connector.handle_raw_packet(None, &[0x01]);
    let _ = rx.recv().await;

    // 3. 2-byte slice with 16-bit flag (needs 3 bytes minimum, defaults to 0.0 without panic)
    connector.handle_raw_packet(None, &[0x01, 0x4B]);
    let _ = rx.recv().await;

    // 4. Valid 8-bit HR packet with 2 RR intervals
    // 0x10, HR=75, RR1=819 (800ms), RR2=870 (850ms)
    connector.handle_raw_packet(None, &[0x10, 75, 0x33, 0x03, 0x66, 0x03]);

    let snap_str = rx.recv().await.expect("Should broadcast snapshot");
    assert!(snap_str.contains("Movesense-261030002013"));
    assert!(snap_str.contains("\"heart_rate_bpm\":75.0"));

    let bio = bio_engine.lock();
    assert_eq!(bio.latest_snapshot.heart_rate_bpm, 75.0);
    assert!(bio.latest_snapshot.rr_interval_ms > 700.0);
}

#[tokio::test]
async fn test_challenger1_rust_gatt_high_frequency_flood() {
    let bio_engine = Arc::new(Mutex::new(BiometricsEngine::new(512.0)));
    let (tx, _) = broadcast::channel(1024);
    let connector = MovesenseBleConnector::new(bio_engine.clone(), tx);

    let start = std::time::Instant::now();
    // Ingest 50,000 BLE packets with varying RR intervals
    for i in 0..50000 {
        let hr = ((i % 60) + 60) as u8;
        let rr_raw: u16 = 800 + (i % 200) as u16;
        let rr_bytes = rr_raw.to_le_bytes();

        let packet = [0x10, hr, rr_bytes[0], rr_bytes[1], 0xEE]; // 5 bytes (with 1 dangling byte)
        connector.handle_raw_packet(None, &packet);
    }
    let elapsed = start.elapsed();
    println!("Processed 50,000 Rust GATT packets in {:?}", elapsed);
    assert!(elapsed.as_millis() < 10000, "50k packets processed in under 10 seconds in debug mode");

    let bio = bio_engine.lock();
    assert!(bio.latest_snapshot.heart_rate_bpm >= 60.0);
    assert_eq!(bio.detector.rr_intervals.len(), 60, "Rolling RR window clamped at 60");
}

#[tokio::test]
async fn test_challenger1_rust_dfa_zone2_metabolic_transitions() {
    let bio = BiometricsEngine::new(512.0);

    // Initial state (resting/disconnected)
    let zone_initial = bio.classify_zone2(1.0, 0.0);
    assert_eq!(zone_initial, "Resting / Disconnected");

    // Zone 1: Active recovery (alpha1 >= 0.85)
    let zone1 = bio.classify_zone2(0.95, 110.0);
    assert!(zone1.contains("Zone 1"));

    // Zone 2: Optimal aerobic (0.70 <= alpha1 < 0.85)
    let zone2 = bio.classify_zone2(0.78, 135.0);
    assert!(zone2.contains("Zone 2"));

    // Zone 3: Tempo / Aerobic Threshold (0.50 <= alpha1 < 0.70)
    let zone3 = bio.classify_zone2(0.62, 155.0);
    assert!(zone3.contains("Zone 3"));

    // Zone 4/5: Anaerobic (alpha1 < 0.50)
    let zone4 = bio.classify_zone2(0.42, 175.0);
    assert!(zone4.contains("Zone 4/5") || zone4.contains("Anaerobic"));
}
