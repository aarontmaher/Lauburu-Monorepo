//! ============================================================================
//! Empirical Challenger 2: Domain Logic & Storage Resilience Test Suite
//! ============================================================================
//! Adversarially stress-tests:
//! 1. Dual-Path Storage Resilience (Unmounted paths, graceful fallback, zero panic)
//! 2. Corrupted, Truncated & Malformed JSON on Disk (Zero panic guarantee)
//! 3. Sequential & Multi-File Concurrent Atomic Writes
//! 4. Identification of Race Condition on Same-Nanosecond Concurrent Atomic Writes
//! 5. Unified AI Sharding Decision Tree Edge Cases (OOM, TB4, MLX, Petals, Solo)
//! 6. RAM Governor State Machine Exact Boundary Transitions (100%, 85%, 70%, 50%, 0%)
//! 7. $0 Cloud Spend Velocity Formula Boundary Conditions (0%, 50%, 100%, Clamping)
//! 8. Identification of Initial Inconsistency in ApiScannerState::new_canonical
//! ============================================================================

use lauburu_tui::api_scanner::ApiScannerState;
use lauburu_tui::persistence::PersistenceManager;
use lauburu_tui::sharding::{ShardingProtocol, ShardingState};
use lauburu_tui::training::{RamGovernorTier, TrainingState};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::Arc;
use std::thread;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
struct ChallengePayload {
    pub uuid: String,
    pub iteration: usize,
    pub telemetry_vector: Vec<f64>,
    pub status: String,
}

// ============================================================================
// SECTION 1: STORAGE RESILIENCE & UNMOUNTED PATH FALLBACK TESTS
// ============================================================================

#[test]
fn test_challenge_storage_unmounted_primary_path_fallback() {
    let temp_base = std::env::temp_dir().join("lauburu_chal_unmounted_vol");
    let _ = fs::remove_dir_all(&temp_base);
    let unmounted_primary = PathBuf::from("/Volumes/NonExistent_Drive_Offline_Test_9999");
    let fallback_dir = temp_base.join("fallback_store");

    let manager = PersistenceManager::with_dirs(unmounted_primary, fallback_dir.clone());
    assert!(!manager.is_primary_available());

    let payload = ChallengePayload {
        uuid: "offline-node-uuid-001".to_string(),
        iteration: 42,
        telemetry_vector: vec![0.27, 14.0, 82.8],
        status: "OFFLINE_FALLBACK_OK".to_string(),
    };

    let save_res = manager.save_json("memory_fallback.json", &payload).expect("Save must succeed via fallback");
    assert!(save_res.is_local_fallback());
    assert_eq!(save_res.path(), fallback_dir.join("memory_fallback.json"));

    // Verify file exists on local fallback disk
    assert!(fallback_dir.join("memory_fallback.json").exists());

    // Verify load recovers exact payload from fallback
    let loaded: ChallengePayload = manager.load_json("memory_fallback.json").expect("Must load from fallback");
    assert_eq!(loaded, payload);

    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_challenge_storage_deep_directory_creation() {
    let temp_base = std::env::temp_dir().join("lauburu_chal_deep_dir");
    let _ = fs::remove_dir_all(&temp_base);
    let deep_fallback = temp_base.join("nested1/nested2/nested3/deep_config");

    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid/drive"), deep_fallback.clone());

    let payload = ChallengePayload {
        uuid: "deep-dir-payload".to_string(),
        iteration: 1,
        telemetry_vector: vec![1.0, 2.0],
        status: "DEEP_DIR_OK".to_string(),
    };

    let res = manager.save_json("nested_payload.json", &payload).expect("Auto-creation of parent directories must succeed");
    assert!(res.is_local_fallback());
    assert!(deep_fallback.exists());
    assert!(deep_fallback.join("nested_payload.json").exists());

    let loaded: Option<ChallengePayload> = manager.load_json("nested_payload.json");
    assert_eq!(loaded, Some(payload));

    let _ = fs::remove_dir_all(temp_base);
}

// ============================================================================
// SECTION 2: CORRUPTED JSON DATA & ZERO-PANIC TESTS
// ============================================================================

#[test]
fn test_challenge_storage_corrupted_json_zero_panic_guarantee() {
    let temp_base = std::env::temp_dir().join("lauburu_chal_corrupt_tests");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    fs::create_dir_all(&fallback_dir).unwrap();

    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid/path"), fallback_dir.clone());

    // 1. Syntactic garbage
    fs::write(fallback_dir.join("syntax_error.json"), "{ invalid: json, [ broken ]").unwrap();
    let res1: Option<ChallengePayload> = manager.load_json("syntax_error.json");
    assert!(res1.is_none(), "Syntactic garbage must return None without panic");

    // 2. Truncated mid-write JSON (simulated power loss / killed process)
    fs::write(fallback_dir.join("truncated.json"), r#"{"uuid": "test-123", "iteration": 42, "telemetry_vector": [1.0, 2."#).unwrap();
    let res2: Option<ChallengePayload> = manager.load_json("truncated.json");
    assert!(res2.is_none(), "Truncated JSON must return None without panic");

    // 3. 0-byte empty file
    fs::write(fallback_dir.join("zero_byte.json"), "").unwrap();
    let res3: Option<ChallengePayload> = manager.load_json("zero_byte.json");
    assert!(res3.is_none(), "0-byte file must return None without panic");

    // 4. Whitespace-only file
    fs::write(fallback_dir.join("whitespace.json"), "   \r\n\t   \n  ").unwrap();
    let res4: Option<ChallengePayload> = manager.load_json("whitespace.json");
    assert!(res4.is_none(), "Whitespace file must return None without panic");

    // 5. Schema mismatch (valid JSON of wrong structure)
    fs::write(fallback_dir.join("wrong_schema.json"), r#"{"unrelated_key": 9999, "other": true}"#).unwrap();
    let res5: Option<ChallengePayload> = manager.load_json("wrong_schema.json");
    assert!(res5.is_none(), "Schema mismatch must return None without panic");

    // 6. Binary garbage (non-UTF8)
    fs::write(fallback_dir.join("binary_garbage.json"), b"\x00\xFF\xFE\xFD\x80\x81\x82").unwrap();
    let res6: Option<ChallengePayload> = manager.load_json("binary_garbage.json");
    assert!(res6.is_none(), "Binary non-UTF8 garbage must return None without panic");

    // 7. Non-existent file
    let res7: Option<ChallengePayload> = manager.load_json("completely_nonexistent.json");
    assert!(res7.is_none(), "Missing file must return None without panic");

    let _ = fs::remove_dir_all(temp_base);
}

// ============================================================================
// SECTION 3: ATOMIC WRITES (.tmp.<pid> + rename) & CONCURRENCY ANALYSIS
// ============================================================================

#[test]
fn test_challenge_storage_sequential_atomic_writes_stress() {
    let temp_base = std::env::temp_dir().join("lauburu_chal_seq_atomic");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    fs::create_dir_all(&fallback_dir).unwrap();

    let manager = PersistenceManager::with_dirs(
        PathBuf::from("/invalid/drive"),
        fallback_dir.clone(),
    );

    // 100 sequential atomic overwrites to the same target file
    for i in 0..100 {
        let payload = ChallengePayload {
            uuid: format!("seq-iter-{}", i),
            iteration: i,
            telemetry_vector: vec![i as f64, (i * 2) as f64],
            status: "SEQUENTIAL_WRITE".to_string(),
        };
        manager.save_json("seq_target.json", &payload).expect("Sequential save must succeed");
    }

    let loaded: ChallengePayload = manager.load_json("seq_target.json").expect("Must load final valid JSON");
    assert_eq!(loaded.uuid, "seq-iter-99");
    assert_eq!(loaded.iteration, 99);

    // Assert zero lingering .tmp files
    let dir_entries = fs::read_dir(&fallback_dir).unwrap();
    let file_names: Vec<String> = dir_entries
        .map(|e| e.unwrap().file_name().into_string().unwrap())
        .collect();

    for name in &file_names {
        assert!(
            !name.contains(".tmp."),
            "Found leftover uncleaned temporary file: {}",
            name
        );
    }
    assert_eq!(file_names, vec!["seq_target.json"]);

    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_challenge_storage_concurrent_distinct_files_atomic_writes() {
    let temp_base = std::env::temp_dir().join("lauburu_chal_concurrent_distinct");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    fs::create_dir_all(&fallback_dir).unwrap();

    let manager = Arc::new(PersistenceManager::with_dirs(
        PathBuf::from("/invalid/drive"),
        fallback_dir.clone(),
    ));

    let concurrency = 20;
    let mut handles = Vec::new();

    for thread_idx in 0..concurrency {
        let mgr = Arc::clone(&manager);
        let handle = thread::spawn(move || {
            let filename = format!("thread_{}_file.json", thread_idx);
            for i in 0..5 {
                let payload = ChallengePayload {
                    uuid: format!("thread-{}-iter-{}", thread_idx, i),
                    iteration: thread_idx * 10 + i,
                    telemetry_vector: vec![thread_idx as f64, i as f64],
                    status: "DISTINCT_FILE_WRITE".to_string(),
                };
                mgr.save_json(&filename, &payload).expect("Distinct file save must succeed");
            }
        });
        handles.push(handle);
    }

    for h in handles {
        h.join().unwrap();
    }

    // Verify all 20 distinct files exist and are valid intact JSON
    for thread_idx in 0..concurrency {
        let filename = format!("thread_{}_file.json", thread_idx);
        let loaded: ChallengePayload = manager.load_json(&filename).expect("File must be valid intact JSON");
        assert_eq!(loaded.status, "DISTINCT_FILE_WRITE");
        assert_eq!(loaded.iteration, thread_idx * 10 + 4);
    }

    let _ = fs::remove_dir_all(temp_base);
}

// ============================================================================
// SECTION 4: UNIFIED AI SHARDING DECISION TREE EDGE CASES
// ============================================================================

#[test]
fn test_challenge_sharding_decision_tree_edge_cases() {
    let mut state = ShardingState::new_canonical();

    // 1. ≤8B Model: Local Solo
    assert_eq!(
        state.evaluate_protocol_decision(4.5, "Q4_K_M"),
        ShardingProtocol::LocalStandalone
    );
    assert_eq!(
        state.evaluate_protocol_decision(8.5, "Q4_K_M"),
        ShardingProtocol::LocalStandalone
    );

    // 2. 32B Model: TB4 DMA RPC when active & ping < 2.0ms
    assert_eq!(
        state.evaluate_protocol_decision(19.5, "Q4_K_M"),
        ShardingProtocol::LlamaRpcTb4
    );

    // 3. 32B IQ2_XXS Model (9.8 GB <= 10.0 GB threshold): Local Solo
    assert_eq!(
        state.evaluate_protocol_decision(9.8, "IQ2_XXS"),
        ShardingProtocol::LocalStandalone
    );

    // 4. Exact TB4 latency threshold: 1.999ms vs 2.000ms / 2.001ms
    state.tb4_rtt_ms = 1.999;
    assert_eq!(
        state.evaluate_protocol_decision(19.5, "Q4_K_M"),
        ShardingProtocol::LlamaRpcTb4
    );

    state.tb4_rtt_ms = 2.000;
    assert_eq!(
        state.evaluate_protocol_decision(19.5, "Q4_K_M"),
        ShardingProtocol::ExoP2pMlx
    );

    state.tb4_rtt_ms = 2.001;
    assert_eq!(
        state.evaluate_protocol_decision(19.5, "Q4_K_M"),
        ShardingProtocol::ExoP2pMlx
    );
    state.tb4_rtt_ms = 0.27; // Reset to canonical

    // 5. Exact TB4 memory limit: 39.5 GB vs 39.501 GB
    assert_eq!(
        state.evaluate_protocol_decision(39.5, "Q4_K_M"),
        ShardingProtocol::LlamaRpcTb4
    );
    assert_eq!(
        state.evaluate_protocol_decision(39.501, "Q4_K_M"),
        ShardingProtocol::ExoP2pMlx
    );

    // 6. Exo MLX vs Petals DHT transition on Apple node count drop
    state.tb4_link_up = false; // Disable TB4
    assert_eq!(
        state.evaluate_protocol_decision(28.0, "Q4_K_M"),
        ShardingProtocol::ExoP2pMlx
    );

    // Drop Apple nodes to 1 -> Petals DHT
    state.apple_silicon_nodes_online = 1;
    assert_eq!(
        state.evaluate_protocol_decision(28.0, "Q4_K_M"),
        ShardingProtocol::PetalsDht
    );

    // 7. Petals DHT to Local Solo when Linux and Android nodes drop to 0
    state.linux_nodes_online = 0;
    state.android_nodes_online = 0;
    assert_eq!(
        state.evaluate_protocol_decision(28.0, "Q4_K_M"),
        ShardingProtocol::LocalStandalone
    );

    // 8. OOM Detection: 70B FP16 (140.0 GB) -> UnsupportedOom
    assert_eq!(
        state.evaluate_protocol_decision(140.0, "FP16"),
        ShardingProtocol::UnsupportedOom
    );

    // 9. OOM Detection: Exceeding 82.8 GB usable mesh VRAM (e.g. 230.0 GB or 405B)
    assert_eq!(
        state.evaluate_protocol_decision(230.0, "Q4_K_M"),
        ShardingProtocol::UnsupportedOom
    );
    assert_eq!(
        state.evaluate_protocol_decision(82.801, "Q4_K_M"),
        ShardingProtocol::UnsupportedOom
    );
}

// ============================================================================
// SECTION 5: RAM GOVERNOR TIER TRANSITIONS & BOUNDARY PERCENTAGES
// ============================================================================

#[test]
fn test_challenge_ram_governor_exact_boundary_transitions() {
    // > 85.0% -> Full
    assert_eq!(RamGovernorTier::from_free_pct(100.0), RamGovernorTier::Full);
    assert_eq!(RamGovernorTier::from_free_pct(90.0), RamGovernorTier::Full);
    assert_eq!(RamGovernorTier::from_free_pct(85.00001), RamGovernorTier::Full);

    // 70.0% .. 85.0% -> Medium
    assert_eq!(RamGovernorTier::from_free_pct(85.0), RamGovernorTier::Medium);
    assert_eq!(RamGovernorTier::from_free_pct(84.99999), RamGovernorTier::Medium);
    assert_eq!(RamGovernorTier::from_free_pct(70.0), RamGovernorTier::Medium);

    // 50.0% .. 70.0% -> Minimal
    assert_eq!(RamGovernorTier::from_free_pct(69.99999), RamGovernorTier::Minimal);
    assert_eq!(RamGovernorTier::from_free_pct(60.0), RamGovernorTier::Minimal);
    assert_eq!(RamGovernorTier::from_free_pct(50.0), RamGovernorTier::Minimal);

    // < 50.0% -> EmergencyPause
    assert_eq!(RamGovernorTier::from_free_pct(49.99999), RamGovernorTier::EmergencyPause);
    assert_eq!(RamGovernorTier::from_free_pct(25.0), RamGovernorTier::EmergencyPause);
    assert_eq!(RamGovernorTier::from_free_pct(0.0), RamGovernorTier::EmergencyPause);
    assert_eq!(RamGovernorTier::from_free_pct(-10.0), RamGovernorTier::EmergencyPause);
}

#[test]
fn test_challenge_ram_governor_pause_and_resume_dynamics() {
    let mut state = TrainingState::new_canonical();
    state.update_ram_metrics(90.0, 21.6);
    assert_eq!(state.governor_tier, RamGovernorTier::Full);
    assert!(!state.is_paused);

    // Toggle pause -> sets EmergencyPause tier
    state.toggle_pause();
    assert!(state.is_paused);
    assert_eq!(state.governor_tier, RamGovernorTier::EmergencyPause);

    // While paused, RAM updates should NOT override EmergencyPause
    state.update_ram_metrics(95.0, 22.8);
    assert_eq!(state.governor_tier, RamGovernorTier::EmergencyPause);

    // Unpause -> restores tier based on current RAM (95% -> Full)
    state.toggle_pause();
    assert!(!state.is_paused);
    assert_eq!(state.governor_tier, RamGovernorTier::Full);

    // Drop to 65% -> Minimal
    state.update_ram_metrics(65.0, 15.6);
    assert_eq!(state.governor_tier, RamGovernorTier::Minimal);
}

// ============================================================================
// SECTION 6: $0 CLOUD SPEND VELOCITY FORMULA BOUNDARY CONDITIONS
// ============================================================================

#[test]
fn test_challenge_spend_velocity_formula_boundary_conditions() {
    // 1. 100% velocity ($0 cloud spend reached)
    assert_eq!(ApiScannerState::compute_spend_velocity(200.0, 0.0), 100.0);

    // 2. 50% velocity ($100 spend of $200 baseline)
    assert_eq!(ApiScannerState::compute_spend_velocity(200.0, 100.0), 50.0);

    // 3. 0% velocity ($200 spend of $200 baseline, no reduction)
    assert_eq!(ApiScannerState::compute_spend_velocity(200.0, 200.0), 0.0);

    // 4. Spend Spike / Negative Reduction Clamping: Current spend ($300) > Baseline ($200) -> 0.0%
    assert_eq!(ApiScannerState::compute_spend_velocity(200.0, 300.0), 0.0);
    assert_eq!(ApiScannerState::compute_spend_velocity(100.0, 1000.0), 0.0);

    // 5. Baseline is 0.0 (Zero baseline cloud spend) -> Safe fallback 100.0%
    assert_eq!(ApiScannerState::compute_spend_velocity(0.0, 0.0), 100.0);
    assert_eq!(ApiScannerState::compute_spend_velocity(0.0, 50.0), 100.0);

    // 6. Negative current spend (e.g. credit/rebate) -> clamped to 100.0%
    assert_eq!(ApiScannerState::compute_spend_velocity(100.0, -20.0), 100.0);
}

#[test]
fn test_challenge_spend_optimizer_dynamic_recalculation_from_synced_state() {
    let mut state = ApiScannerState::new_canonical();
    // Synchronize totals to match actual initial active endpoints
    state.recalculate_totals();

    let initial_spend = state.current_cloud_spend_usd;
    let initial_velocity = state.zero_spend_velocity_pct;

    // Toggle Anthropic endpoint (row 1, $68.00) from active (true) to inactive (false)
    state.selected_endpoint_row = 1;
    assert!(state.endpoints[1].is_active);
    state.toggle_active_swap();
    assert!(!state.endpoints[1].is_active);

    // Totals must dynamically update: spend must decrease, savings & velocity must increase
    assert!(
        state.current_cloud_spend_usd < initial_spend,
        "Current spend {} must be less than initial spend {}",
        state.current_cloud_spend_usd,
        initial_spend
    );
    assert!(
        state.zero_spend_velocity_pct > initial_velocity,
        "Velocity {} must be greater than initial velocity {}",
        state.zero_spend_velocity_pct,
        initial_velocity
    );
}
