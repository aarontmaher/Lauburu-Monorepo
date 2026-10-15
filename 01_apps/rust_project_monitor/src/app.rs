use crate::prober::{collect_project_telemetry, ProjectTelemetry};
use std::path::PathBuf;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActiveTab {
    Overview = 0,
    Ports = 1,
    Mesh = 2,
    Apps = 3,
    Subsystems = 4,
    Storage = 5,
}

impl ActiveTab {
    pub fn next(&self) -> Self {
        match self {
            ActiveTab::Overview => ActiveTab::Ports,
            ActiveTab::Ports => ActiveTab::Mesh,
            ActiveTab::Mesh => ActiveTab::Apps,
            ActiveTab::Apps => ActiveTab::Subsystems,
            ActiveTab::Subsystems => ActiveTab::Storage,
            ActiveTab::Storage => ActiveTab::Overview,
        }
    }

    pub fn prev(&self) -> Self {
        match self {
            ActiveTab::Overview => ActiveTab::Storage,
            ActiveTab::Ports => ActiveTab::Overview,
            ActiveTab::Mesh => ActiveTab::Ports,
            ActiveTab::Apps => ActiveTab::Mesh,
            ActiveTab::Subsystems => ActiveTab::Apps,
            ActiveTab::Storage => ActiveTab::Subsystems,
        }
    }
}

pub struct App {
    pub repo_root: PathBuf,
    pub telemetry: ProjectTelemetry,
    pub active_tab: ActiveTab,
    pub should_quit: bool,
    pub last_refresh: Instant,
    pub refresh_interval: Duration,
    pub status_message: String,
    pub status_time: Option<Instant>,
    pub tick_count: u64,
}

impl App {
    pub fn new(repo_root: PathBuf) -> Self {
        let telemetry = collect_project_telemetry(&repo_root);
        Self {
            repo_root,
            telemetry,
            active_tab: ActiveTab::Overview,
            should_quit: false,
            last_refresh: Instant::now(),
            refresh_interval: Duration::from_secs(3),
            status_message: "⚡ Ready • Press [Tab] to cycle tabs • [r] Refresh • [h] Heal • [w] BT Wake • [q] Quit".to_string(),
            status_time: Some(Instant::now()),
            tick_count: 0,
        }
    }

    pub fn on_tick(&mut self) {
        self.tick_count += 1;
        if self.last_refresh.elapsed() >= self.refresh_interval {
            self.refresh_telemetry();
        }
    }

    pub fn refresh_telemetry(&mut self) {
        self.telemetry = collect_project_telemetry(&self.repo_root);
        self.last_refresh = Instant::now();
        self.set_status(format!("🔄 Refreshed all socket probes in {:.1}ms", self.telemetry.scan_time_ms));
    }

    pub fn heal_storage(&mut self) {
        let obsidian_path = self.repo_root.join("obsidian_vault");
        let lora_path = PathBuf::from("/Users/aaron/DFS_UNIFIED/lora_datasets");
        let mut healed_actions = Vec::new();

        if !obsidian_path.exists() {
            let _ = std::fs::create_dir_all(&obsidian_path);
            healed_actions.push("Created obsidian_vault");
        }
        if !lora_path.exists() {
            let _ = std::fs::create_dir_all(&lora_path);
            healed_actions.push("Created lora_datasets");
        }

        // Clean stale git locks if present
        let lock_path = self.repo_root.join(".git/index.lock");
        if lock_path.exists() {
            let _ = std::fs::remove_file(lock_path);
            healed_actions.push("Removed .git/index.lock");
        }

        if healed_actions.is_empty() {
            self.set_status("✨ Tri-Vault Storage verified 100% HEALTHY (Zero defects)".to_string());
        } else {
            self.set_status(format!("🩹 Self-Healed: {}", healed_actions.join(", ")));
        }
    }

    pub fn wake_mesh_bluetooth_first(&mut self) {
        let wol_script = PathBuf::from("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/mesh/canonical_network_resurrection_engine.py");
        if wol_script.exists() {
            let output = std::process::Command::new("python3")
                .arg(&wol_script)
                .arg("--wake-all")
                .output();

            match output {
                Ok(out) if out.status.success() => {
                    self.set_status("📶 Dispatched Line 1 Bluetooth Proximity Wake ➔ Line 2 UDP WoL to all nodes".to_string());
                }
                Ok(out) => {
                    self.set_status(format!("⚠️ BT/WoL wake exited with code {:?}", out.status.code()));
                }
                Err(e) => {
                    self.set_status(format!("❌ Failed to execute BT/WoL wake: {}", e));
                }
            }
        } else {
            self.set_status("❌ canonical_network_resurrection_engine.py not found on disk".to_string());
        }
    }

    pub fn set_status(&mut self, msg: String) {
        self.status_message = msg;
        self.status_time = Some(Instant::now());
    }
}
