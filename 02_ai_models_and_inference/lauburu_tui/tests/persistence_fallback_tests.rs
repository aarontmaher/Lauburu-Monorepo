//! ============================================================================
//! Tier 1, 2, 3 & 4 Test Suite: Dual-Path Persistence & Fallback Resilience (R5)
//! ============================================================================
//! Features Covered:
//! - F13: Dual-Path Persistence Manager (Primary GDrive vs Fallback `config/memory_fallback.json`)
//! - F14: Atomic Write & Zero-Panic Invariant (Safe rename, unmounted volume handling)
//! - F15: Non-Blocking Persistence Worker Simulation
//! - F10: Zero-Mock / Truth Audit Compliance
//! ============================================================================

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

use lauburu_tui::persistence::{PersistenceLocation, PersistenceManager};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MockSnapshotData {
    pub session_id: String,
    pub active_tab_index: usize,
    pub timestamp_utc: String,
    pub metrics_count: usize,
}

// ============================================================================
// TIER 1: FEATURE COVERAGE TESTS (≥5 tests)
// ============================================================================

#[test]
fn test_t1_f13_01_save_to_primary_when_mounted() {
    let temp_base = std::env::temp_dir().join("lauburu_test_persist_primary");
    let _ = fs::remove_dir_all(&temp_base);
    let primary_dir = temp_base.join("gdrive_mock");
    let fallback_dir = temp_base.join("fallback_mock");

    fs::create_dir_all(&primary_dir).unwrap();
    let manager = PersistenceManager::with_dirs(primary_dir.clone(), fallback_dir);

    let sample_data = MockSnapshotData {
        session_id: "sess-001".to_string(),
        active_tab_index: 2,
        timestamp_utc: "2026-08-30T15:00:00Z".to_string(),
        metrics_count: 42,
    };

    let result = manager.save_json("snapshot.json", &sample_data).expect("Save must succeed");
    match result {
        PersistenceLocation::GoogleDrive(p) => {
            assert!(p.exists());
            assert_eq!(p.file_name().unwrap(), "snapshot.json");
        }
        _ => panic!("Expected GoogleDrive persistence location"),
    }

    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_t1_f13_02_unmounted_primary_gracefully_falls_back_to_local_disk() {
    let temp_base = std::env::temp_dir().join("lauburu_test_persist_fallback");
    let _ = fs::remove_dir_all(&temp_base);
    // Non-existent primary volume
    let unmounted_primary = PathBuf::from("/Volumes/NonExistent_Drive_99999/Lauburu");
    let fallback_dir = temp_base.join("fallback_config");

    let manager = PersistenceManager::with_dirs(unmounted_primary, fallback_dir.clone());

    let sample_data = MockSnapshotData {
        session_id: "sess-fallback-002".to_string(),
        active_tab_index: 3,
        timestamp_utc: "2026-08-30T15:05:00Z".to_string(),
        metrics_count: 10,
    };

    let result = manager.save_json("memory_fallback.json", &sample_data).expect("Must fall back cleanly");
    match result {
        PersistenceLocation::LocalFallback(p) => {
            assert!(p.exists());
            assert_eq!(p.file_name().unwrap(), "memory_fallback.json");
        }
        _ => panic!("Expected LocalFallback location"),
    }

    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_t1_f14_03_atomic_write_leaves_no_lingering_temp_files() {
    let temp_dir = std::env::temp_dir().join("lauburu_test_atomic_clean");
    let _ = fs::remove_dir_all(&temp_dir);
    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid/drive"), temp_dir.clone());

    let data = MockSnapshotData {
        session_id: "clean-check".to_string(),
        active_tab_index: 0,
        timestamp_utc: "2026-08-30T15:10:00Z".to_string(),
        metrics_count: 5,
    };

    manager.save_json("clean_test.json", &data).unwrap();

    // Verify only the target file exists, no .tmp files
    let mut files = Vec::new();
    for entry in fs::read_dir(&temp_dir).unwrap() {
        let name = entry.unwrap().file_name().into_string().unwrap();
        files.push(name);
    }

    assert_eq!(files, vec!["clean_test.json"]);
    let _ = fs::remove_dir_all(temp_dir);
}

#[test]
fn test_t1_f14_04_load_json_roundtrip_fidelity() {
    let temp_base = std::env::temp_dir().join("lauburu_test_roundtrip");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid/drive"), fallback_dir);

    let original = MockSnapshotData {
        session_id: "roundtrip-uuid-12345".to_string(),
        active_tab_index: 4,
        timestamp_utc: "2026-08-30T15:15:00Z".to_string(),
        metrics_count: 999,
    };

    manager.save_json("roundtrip.json", &original).unwrap();
    let loaded: MockSnapshotData = manager.load_json("roundtrip.json").expect("Must load successfully");

    assert_eq!(original, loaded);
    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_t1_f14_05_load_precedence_prefers_primary_over_fallback() {
    let temp_base = std::env::temp_dir().join("lauburu_test_precedence");
    let _ = fs::remove_dir_all(&temp_base);
    let primary_dir = temp_base.join("primary");
    let fallback_dir = temp_base.join("fallback");

    fs::create_dir_all(&primary_dir).unwrap();
    fs::create_dir_all(&fallback_dir).unwrap();

    let primary_data = MockSnapshotData {
        session_id: "from-primary".to_string(),
        active_tab_index: 1,
        timestamp_utc: "2026-08-30T15:20:00Z".to_string(),
        metrics_count: 100,
    };

    let fallback_data = MockSnapshotData {
        session_id: "from-fallback".to_string(),
        active_tab_index: 2,
        timestamp_utc: "2026-08-30T15:20:00Z".to_string(),
        metrics_count: 50,
    };

    // Write different contents to primary and fallback
    fs::write(primary_dir.join("data.json"), serde_json::to_string(&primary_data).unwrap()).unwrap();
    fs::write(fallback_dir.join("data.json"), serde_json::to_string(&fallback_data).unwrap()).unwrap();

    let manager = PersistenceManager::with_dirs(primary_dir, fallback_dir);
    let loaded: MockSnapshotData = manager.load_json("data.json").unwrap();

    assert_eq!(loaded.session_id, "from-primary", "Primary must take precedence when present");
    let _ = fs::remove_dir_all(temp_base);
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (≥5 tests)
// ============================================================================

#[test]
fn test_t2_f14_b01_corrupted_json_returns_none_without_panic() {
    let temp_base = std::env::temp_dir().join("lauburu_test_corrupt");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    fs::create_dir_all(&fallback_dir).unwrap();

    // Write malformed JSON
    fs::write(fallback_dir.join("corrupted.json"), "{ invalid: json :::").unwrap();

    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid/drive"), fallback_dir);
    let result: Option<MockSnapshotData> = manager.load_json("corrupted.json");

    assert!(result.is_none(), "Corrupted JSON must return None without panicking");
    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_t2_f14_b02_missing_file_returns_none() {
    let manager = PersistenceManager::new();
    let result: Option<MockSnapshotData> = manager.load_json("completely_nonexistent_file.json");
    assert!(result.is_none());
}

#[test]
fn test_t2_f14_b03_empty_file_returns_none() {
    let temp_base = std::env::temp_dir().join("lauburu_test_empty");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    fs::create_dir_all(&fallback_dir).unwrap();
    fs::write(fallback_dir.join("empty.json"), "").unwrap();

    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid/drive"), fallback_dir);
    let result: Option<MockSnapshotData> = manager.load_json("empty.json");

    assert!(result.is_none(), "0-byte file must return None");
    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_t2_f13_b04_missing_parent_directories_auto_created() {
    let temp_base = std::env::temp_dir().join("lauburu_test_nested");
    let _ = fs::remove_dir_all(&temp_base);
    let deeply_nested = temp_base.join("level1/level2/level3/config");

    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid"), deeply_nested.clone());
    let data = MockSnapshotData {
        session_id: "nested-test".to_string(),
        active_tab_index: 0,
        timestamp_utc: "2026-08-30T15:30:00Z".to_string(),
        metrics_count: 1,
    };

    let res = manager.save_json("nested_save.json", &data);
    assert!(res.is_ok(), "Parent directories must be automatically created");
    assert!(deeply_nested.exists());

    let _ = fs::remove_dir_all(temp_base);
}

#[test]
fn test_t2_f15_b05_rapid_100_sequential_saves_integrity() {
    let temp_base = std::env::temp_dir().join("lauburu_test_rapid_saves");
    let _ = fs::remove_dir_all(&temp_base);
    let fallback_dir = temp_base.join("config");
    let manager = PersistenceManager::with_dirs(PathBuf::from("/invalid"), fallback_dir);

    for i in 0..100 {
        let data = MockSnapshotData {
            session_id: format!("rapid-{}", i),
            active_tab_index: i % 5,
            timestamp_utc: "2026-08-30T15:35:00Z".to_string(),
            metrics_count: i,
        };
        manager.save_json("rapid.json", &data).unwrap();
    }

    let final_loaded: MockSnapshotData = manager.load_json("rapid.json").unwrap();
    assert_eq!(final_loaded.session_id, "rapid-99");
    assert_eq!(final_loaded.metrics_count, 99);

    let _ = fs::remove_dir_all(temp_base);
}

// ============================================================================
// TIER 3 & 4: REAL-WORLD OFFLINE NODE RESILIENCE
// ============================================================================

#[test]
fn test_t4_f13_scenario_01_offline_node_full_persistence_lifecycle() {
    let temp_base = std::env::temp_dir().join("lauburu_test_offline_node");
    let _ = fs::remove_dir_all(&temp_base);
    let unmounted_drive = PathBuf::from("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory");
    let local_config = temp_base.join("config");

    let manager = PersistenceManager::with_dirs(unmounted_drive, local_config.clone());

    // 1. Save training metrics on an offline node
    let metrics = MockSnapshotData {
        session_id: "offline-lora-run-01".to_string(),
        active_tab_index: 4,
        timestamp_utc: "2026-08-30T15:40:00Z".to_string(),
        metrics_count: 5000,
    };

    let loc = manager.save_json("training_metrics.json", &metrics).unwrap();
    assert!(matches!(loc, PersistenceLocation::LocalFallback(_)));

    // 2. Restart app and reload state
    let reloaded: MockSnapshotData = manager.load_json("training_metrics.json").unwrap();
    assert_eq!(reloaded.session_id, "offline-lora-run-01");
    assert_eq!(reloaded.metrics_count, 5000);

    let _ = fs::remove_dir_all(temp_base);
}
