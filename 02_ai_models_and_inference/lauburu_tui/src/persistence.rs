//! ============================================================================
//! Dual-Path Persistence & Resilient Fallback Engine (`src/persistence.rs`)
//! ============================================================================
//! Features Covered:
//! - F13: Dual-Path Persistence Manager (Primary GDrive vs Fallback `config/memory_fallback.json`)
//! - F14: Atomic Write & Zero-Panic Invariant (Safe rename, unmounted volume handling)
//! - F15: Non-Blocking Persistence Worker Support
//!
//! Provides resilient atomic serialization and deserialization across the
//! Lauburu AI Mesh ecosystem with graceful fallback when primary cloud mounts
//! (e.g. `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory/`) are offline.
//! ============================================================================

use crate::errors::AppError;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

/// Destination location where a payload was successfully persisted.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PersistenceLocation {
    /// Saved to primary Google Drive volume mount.
    GoogleDrive(PathBuf),
    /// Saved to local fallback disk storage directory.
    LocalFallback(PathBuf),
}

impl PersistenceLocation {
    /// Return a reference to the filesystem path of the persisted target file.
    pub fn path(&self) -> &Path {
        match self {
            PersistenceLocation::GoogleDrive(path) => path.as_path(),
            PersistenceLocation::LocalFallback(path) => path.as_path(),
        }
    }

    /// Return true if persisted to primary Google Drive storage.
    pub fn is_google_drive(&self) -> bool {
        matches!(self, PersistenceLocation::GoogleDrive(_))
    }

    /// Return true if persisted to local fallback disk storage.
    pub fn is_local_fallback(&self) -> bool {
        matches!(self, PersistenceLocation::LocalFallback(_))
    }

    /// Human-readable label for status bars and telemetry.
    pub fn display_label(&self) -> String {
        match self {
            PersistenceLocation::GoogleDrive(path) => {
                format!("Google Drive ({})", path.display())
            }
            PersistenceLocation::LocalFallback(path) => {
                format!("Local Fallback ({})", path.display())
            }
        }
    }
}

impl fmt::Display for PersistenceLocation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.display_label())
    }
}

/// Dual-tier persistence manager governing primary and fallback storage directories.
#[derive(Debug, Clone)]
pub struct PersistenceManager {
    /// Primary storage directory (defaults to Google Drive memory vault).
    pub primary_dir: PathBuf,
    /// Fallback storage directory (defaults to local `config` folder).
    pub fallback_dir: PathBuf,
}

impl Default for PersistenceManager {
    fn default() -> Self {
        Self::new()
    }
}

impl PersistenceManager {
    /// Initialize with canonical production directory paths:
    /// - Primary: `/Volumes/Google Drive/My Drive/Lauburu_AI_Memory`
    /// - Fallback: `config`
    pub fn new() -> Self {
        Self {
            primary_dir: PathBuf::from("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory"),
            fallback_dir: PathBuf::from("config"),
        }
    }

    /// Construct persistence manager with explicit primary and fallback directories.
    pub fn with_dirs(primary: PathBuf, fallback: PathBuf) -> Self {
        Self {
            primary_dir: primary,
            fallback_dir: fallback,
        }
    }

    /// Access the primary directory path.
    pub fn primary_dir(&self) -> &Path {
        &self.primary_dir
    }

    /// Access the fallback directory path.
    pub fn fallback_dir(&self) -> &Path {
        &self.fallback_dir
    }

    /// Check whether the primary storage directory exists and is an accessible directory.
    pub fn is_primary_available(&self) -> bool {
        self.primary_dir.exists() && self.primary_dir.is_dir()
    }

    /// Atomically serialize and save data, falling back to local disk if primary is unmounted or fails.
    pub fn save_json<T: Serialize>(
        &self,
        filename: &str,
        data: &T,
    ) -> Result<PersistenceLocation, AppError> {
        let json_str = serde_json::to_string_pretty(data)?;

        // 1. Attempt primary save if primary directory exists and is accessible
        if self.primary_dir.exists() {
            match self.atomic_write(&self.primary_dir, filename, &json_str) {
                Ok(path) => return Ok(PersistenceLocation::GoogleDrive(path)),
                Err(err) => {
                    eprintln!(
                        "Warning: Primary persistence to {:?} failed: {}. Falling back to {:?}",
                        self.primary_dir, err, self.fallback_dir
                    );
                }
            }
        }

        // 2. Fallback to local config directory
        let fallback_path = self.atomic_write(&self.fallback_dir, filename, &json_str)?;
        Ok(PersistenceLocation::LocalFallback(fallback_path))
    }

    /// Atomic write helper using a temporary file in the same directory + rename to prevent corruption.
    fn atomic_write(&self, dir: &Path, filename: &str, content: &str) -> Result<PathBuf, AppError> {
        if !dir.exists() {
            fs::create_dir_all(dir)?;
        }

        let target_path = dir.join(filename);
        let pid = std::process::id();
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        let tmp_path = dir.join(format!("{}.tmp.{}.{}", filename, pid, timestamp));

        fs::write(&tmp_path, content)?;
        fs::rename(&tmp_path, &target_path)?;

        Ok(target_path)
    }

    /// Load and deserialize JSON data attempting primary first, then fallback.
    /// Returns `None` without panicking if files are absent or corrupted.
    pub fn load_json<T: for<'de> Deserialize<'de>>(&self, filename: &str) -> Option<T> {
        // Try primary first
        let primary_file = self.primary_dir.join(filename);
        if primary_file.exists() {
            if let Ok(content) = fs::read_to_string(&primary_file) {
                if !content.trim().is_empty() {
                    if let Ok(data) = serde_json::from_str::<T>(&content) {
                        return Some(data);
                    }
                }
            }
        }

        // Try fallback
        let fallback_file = self.fallback_dir.join(filename);
        if fallback_file.exists() {
            if let Ok(content) = fs::read_to_string(&fallback_file) {
                if !content.trim().is_empty() {
                    if let Ok(data) = serde_json::from_str::<T>(&content) {
                        return Some(data);
                    }
                }
            }
        }

        None
    }

    /// Asynchronous non-blocking save helper executing off the UI loop via `tokio::task::spawn_blocking`.
    pub async fn save_json_async<T>(
        &self,
        filename: String,
        data: T,
    ) -> Result<PersistenceLocation, AppError>
    where
        T: Serialize + Send + 'static,
    {
        let manager = self.clone();
        tokio::task::spawn_blocking(move || manager.save_json(&filename, &data))
            .await
            .map_err(|e| AppError::Persistence(format!("Async persistence task join error: {e}")))?
    }

    /// Asynchronous non-blocking load helper executing off the UI loop via `tokio::task::spawn_blocking`.
    pub async fn load_json_async<T>(&self, filename: String) -> Option<T>
    where
        T: for<'de> Deserialize<'de> + Send + 'static,
    {
        let manager = self.clone();
        tokio::task::spawn_blocking(move || manager.load_json::<T>(&filename))
            .await
            .ok()
            .flatten()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
    struct TestPayload {
        id: String,
        count: u64,
        active: bool,
    }

    #[test]
    fn test_persistence_manager_default_paths() {
        let manager = PersistenceManager::new();
        assert_eq!(
            manager.primary_dir(),
            Path::new("/Volumes/Google Drive/My Drive/Lauburu_AI_Memory")
        );
        assert_eq!(manager.fallback_dir(), Path::new("config"));
    }

    #[test]
    fn test_save_and_load_roundtrip_primary() {
        let temp_dir = std::env::temp_dir().join("lauburu_persist_unit_primary");
        let primary = temp_dir.join("primary");
        let fallback = temp_dir.join("fallback");

        fs::create_dir_all(&primary).unwrap();
        let manager = PersistenceManager::with_dirs(primary.clone(), fallback);

        let payload = TestPayload {
            id: "unit-01".to_string(),
            count: 42,
            active: true,
        };

        let loc = manager.save_json("test_data.json", &payload).expect("Save should succeed");
        assert!(loc.is_google_drive());
        assert_eq!(loc.path(), primary.join("test_data.json"));

        let loaded: TestPayload = manager.load_json("test_data.json").expect("Should load data");
        assert_eq!(loaded, payload);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_save_and_load_fallback_when_primary_missing() {
        let temp_dir = std::env::temp_dir().join("lauburu_persist_unit_fallback");
        let unmounted = PathBuf::from("/Volumes/NonExistent_Drive_Unit_Test_404");
        let fallback = temp_dir.join("fallback_config");

        let manager = PersistenceManager::with_dirs(unmounted, fallback.clone());

        let payload = TestPayload {
            id: "unit-fallback-02".to_string(),
            count: 100,
            active: false,
        };

        let loc = manager.save_json("fallback_data.json", &payload).expect("Should fallback cleanly");
        assert!(loc.is_local_fallback());
        assert_eq!(loc.path(), fallback.join("fallback_data.json"));

        let loaded: TestPayload = manager.load_json("fallback_data.json").expect("Should load from fallback");
        assert_eq!(loaded, payload);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_atomic_write_no_leftover_temp_files() {
        let temp_dir = std::env::temp_dir().join("lauburu_persist_unit_atomic");
        let manager = PersistenceManager::with_dirs(PathBuf::from("/unmounted"), temp_dir.clone());

        let payload = TestPayload {
            id: "atomic-check".to_string(),
            count: 7,
            active: true,
        };

        manager.save_json("atomic.json", &payload).unwrap();

        let entries = fs::read_dir(&temp_dir).unwrap();
        let file_names: Vec<String> = entries
            .map(|e| e.unwrap().file_name().into_string().unwrap())
            .collect();

        assert_eq!(file_names, vec!["atomic.json"]);

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_corrupted_and_empty_json_returns_none() {
        let temp_dir = std::env::temp_dir().join("lauburu_persist_unit_corrupt");
        let fallback = temp_dir.join("fallback");
        fs::create_dir_all(&fallback).unwrap();

        fs::write(fallback.join("corrupt.json"), "{ malformed json :::").unwrap();
        fs::write(fallback.join("empty.json"), "").unwrap();

        let manager = PersistenceManager::with_dirs(PathBuf::from("/unmounted"), fallback);

        let corrupt_res: Option<TestPayload> = manager.load_json("corrupt.json");
        assert!(corrupt_res.is_none());

        let empty_res: Option<TestPayload> = manager.load_json("empty.json");
        assert!(empty_res.is_none());

        let missing_res: Option<TestPayload> = manager.load_json("nonexistent.json");
        assert!(missing_res.is_none());

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[tokio::test]
    async fn test_async_save_and_load() {
        let temp_dir = std::env::temp_dir().join("lauburu_persist_unit_async");
        let fallback = temp_dir.join("async_fallback");
        let manager = PersistenceManager::with_dirs(PathBuf::from("/unmounted"), fallback);

        let payload = TestPayload {
            id: "async-01".to_string(),
            count: 999,
            active: true,
        };

        let loc = manager
            .save_json_async("async.json".to_string(), payload.clone())
            .await
            .expect("Async save should succeed");
        assert!(loc.is_local_fallback());

        let loaded: Option<TestPayload> = manager.load_json_async("async.json".to_string()).await;
        assert_eq!(loaded, Some(payload));

        let _ = fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_persistence_location_methods_and_display() {
        let gdrive_loc = PersistenceLocation::GoogleDrive(PathBuf::from("/Volumes/GDrive/test.json"));
        assert!(gdrive_loc.is_google_drive());
        assert!(!gdrive_loc.is_local_fallback());
        assert_eq!(gdrive_loc.path(), Path::new("/Volumes/GDrive/test.json"));
        assert!(gdrive_loc.to_string().contains("Google Drive"));

        let local_loc = PersistenceLocation::LocalFallback(PathBuf::from("config/test.json"));
        assert!(!local_loc.is_google_drive());
        assert!(local_loc.is_local_fallback());
        assert_eq!(local_loc.path(), Path::new("config/test.json"));
        assert!(local_loc.to_string().contains("Local Fallback"));
    }
}
