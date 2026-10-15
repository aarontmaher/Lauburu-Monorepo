use ratatui::style::Color;
use ratatui::widgets::TableState;
use serde::{Deserialize, Serialize};

/// Dynamic RAM Governor Operational Tiers governing continuous background compute.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum RamGovernorTier {
    #[default]
    Full,
    Medium,
    Minimal,
    EmergencyPause,
}

impl RamGovernorTier {
    /// Classify tier based on percentage of free host RAM.
    pub fn from_free_pct(free_pct: f64) -> Self {
        if free_pct > 85.0 {
            Self::Full
        } else if free_pct >= 70.0 {
            Self::Medium
        } else if free_pct >= 50.0 {
            Self::Minimal
        } else {
            Self::EmergencyPause
        }
    }

    /// Human-readable badge text with status icon.
    pub fn badge_text(&self) -> &'static str {
        match self {
            Self::Full => "🟢 FULL TIER (>85% Free)",
            Self::Medium => "🟡 MEDIUM TIER (70-85% Free)",
            Self::Minimal => "🟠 MINIMAL TIER (50-70% Free)",
            Self::EmergencyPause => "🔴 EMERGENCY PAUSE (<50% Free)",
        }
    }

    /// Badge text and associated Ratatui display color.
    pub fn display_badge(&self) -> (&'static str, Color) {
        match self {
            Self::Full => ("🟢 FULL TIER (>85% Free)", Color::Green),
            Self::Medium => ("🟡 MEDIUM TIER (70-85% Free)", Color::Yellow),
            Self::Minimal => ("🟠 MINIMAL TIER (50-70% Free)", Color::Rgb(255, 140, 0)),
            Self::EmergencyPause => ("🔴 EMERGENCY PAUSE (<50% Free)", Color::Red),
        }
    }

    /// Operational directive associated with this tier.
    pub fn directive(&self) -> &'static str {
        match self {
            Self::Full => "Full 32B model fine-tuning active across TB4 RPC shards",
            Self::Medium => "Lightweight adapter updates on 1.5B-7B models active",
            Self::Minimal => "Dataset curation, deduplication & AST parsing only (0 MB VRAM)",
            Self::EmergencyPause => "Training compute paused - yielding all resources to production apps",
        }
    }
}

/// Real-time 24/7 LoRA Fine-Tuning Job State.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LoraTrainingJob {
    pub active_model: String,
    pub teacher_model: String,
    pub lora_rank: u32,
    pub lora_alpha: u32,
    pub target_modules: String,
    pub current_step: u64,
    pub total_steps: u64,
    pub current_epoch: u32,
    pub total_epochs: u32,
    pub current_loss: f64,
    pub loss_history: Vec<f64>,
    pub throughput_samples_sec: f64,
    pub throughput_tokens_sec: f64,
    pub dataset_pairs_count: usize,
    pub gdrive_sync_status: String,
}

impl LoraTrainingJob {
    /// Calculate current step progress as percentage [0.0, 100.0].
    pub fn progress_pct(&self) -> f64 {
        if self.total_steps == 0 {
            return 0.0;
        }
        ((self.current_step as f64 / self.total_steps as f64) * 100.0).clamp(0.0, 100.0)
    }

    /// Check if loss history indicates loss convergence.
    pub fn is_loss_converging(&self) -> bool {
        if self.loss_history.len() < 2 {
            return true;
        }
        let first = self.loss_history.first().unwrap();
        let last = self.loss_history.last().unwrap();
        last <= first
    }
}

/// Shadow Swarm Benchmark Tournament Candidate Entry.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BenchmarkTournamentRow {
    pub model_name: String,
    pub architecture: String,
    pub elo_score: u32,
    pub win_loss_draw: (u32, u32, u32),
    pub truth_audit_pct: f64,
    pub promotion_verdict: String,
}

/// NPU Bonus Ledger Grant Entry for Edge TPU & ANE acceleration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NpuBonusGrant {
    pub node_name: String,
    pub layer: String,
    pub promoted_feature: String,
    pub grant_date: String,
    pub priority_multiplier: f64,
    pub token_credits: u64,
    pub execution_target: String,
    pub grant_status: String,
}

/// Active table receiving arrow key navigation in Continuous Training tab.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum TrainingFocus {
    #[default]
    BenchmarkTournament,
    NpuLedger,
}

/// Complete Continuous Training View State.
#[derive(Debug, Clone)]
pub struct TrainingState {
    pub lora_job: LoraTrainingJob,
    pub governor_tier: RamGovernorTier,
    pub host_ram_free_pct: f64,
    pub host_ram_free_gb: f64,
    pub benchmark_rows: Vec<BenchmarkTournamentRow>,
    pub npu_grants: Vec<NpuBonusGrant>,
    pub selected_benchmark_row: usize,
    pub selected_npu_row: usize,
    pub benchmark_table_state: TableState,
    pub npu_table_state: TableState,
    pub active_training_focus: TrainingFocus,
    pub is_paused: bool,
}

impl TrainingState {
    /// Initialize canonical training state matching the 7-layer mesh topology.
    pub fn new_canonical() -> Self {
        let lora_job = LoraTrainingJob {
            active_model: "Qwen2.5-Coder-7B-LoRA".to_string(),
            teacher_model: "Gemini 3.7 Flash CoT Distillation".to_string(),
            lora_rank: 16,
            lora_alpha: 32,
            target_modules: "q_proj, v_proj, k_proj, o_proj".to_string(),
            current_step: 1420,
            total_steps: 5000,
            current_epoch: 2,
            total_epochs: 5,
            current_loss: 1.15,
            loss_history: vec![2.41, 2.15, 1.89, 1.48, 1.28, 1.15],
            throughput_samples_sec: 18.4,
            throughput_tokens_sec: 1250.0,
            dataset_pairs_count: 3120,
            gdrive_sync_status: "Synced (Fallback Ready)".to_string(),
        };

        let benchmark_rows = vec![
            BenchmarkTournamentRow {
                model_name: "Claude 3.5 Sonnet (Teacher)".to_string(),
                architecture: "Cloud Frontier MoE".to_string(),
                elo_score: 1910,
                win_loss_draw: (145, 12, 8),
                truth_audit_pct: 99.4,
                promotion_verdict: "Frontier Benchmark".to_string(),
            },
            BenchmarkTournamentRow {
                model_name: "Local LoRA v3 (Active)".to_string(),
                architecture: "Qwen2.5-Coder-7B + PEFT".to_string(),
                elo_score: 1842,
                win_loss_draw: (120, 28, 17),
                truth_audit_pct: 98.8,
                promotion_verdict: "Candidate (ELO Gap: -68)".to_string(),
            },
            BenchmarkTournamentRow {
                model_name: "DeepSeek-R1-Distill-32B".to_string(),
                architecture: "Dense Transformer".to_string(),
                elo_score: 1885,
                win_loss_draw: (132, 21, 12),
                truth_audit_pct: 99.1,
                promotion_verdict: "Promoted to Mesh RPC".to_string(),
            },
        ];

        let npu_grants = vec![
            NpuBonusGrant {
                node_name: "Pixel_10_Pro_XL".to_string(),
                layer: "L6".to_string(),
                promoted_feature: "Pan-Tompkins DSP Kernel".to_string(),
                grant_date: "2026-08-30".to_string(),
                priority_multiplier: 1.5,
                token_credits: 450_000,
                execution_target: "Google Tensor G5 TPU (1.2W)".to_string(),
                grant_status: "Active Grant".to_string(),
            },
            NpuBonusGrant {
                node_name: "Mac_Node".to_string(),
                layer: "L1".to_string(),
                promoted_feature: "Continuous AST Parser".to_string(),
                grant_date: "2026-08-30".to_string(),
                priority_multiplier: 2.0,
                token_credits: 820_000,
                execution_target: "Apple Neural Engine (ANE)".to_string(),
                grant_status: "Active Grant".to_string(),
            },
        ];

        let mut benchmark_table_state = TableState::default();
        benchmark_table_state.select(Some(0));

        let mut npu_table_state = TableState::default();
        npu_table_state.select(Some(0));

        Self {
            lora_job,
            governor_tier: RamGovernorTier::Full,
            host_ram_free_pct: 88.5,
            host_ram_free_gb: 21.2,
            benchmark_rows,
            npu_grants,
            selected_benchmark_row: 0,
            selected_npu_row: 0,
            benchmark_table_state,
            npu_table_state,
            active_training_focus: TrainingFocus::BenchmarkTournament,
            is_paused: false,
        }
    }

    /// Move to the next row in the currently focused table.
    pub fn next_row(&mut self) {
        match self.active_training_focus {
            TrainingFocus::BenchmarkTournament => {
                if !self.benchmark_rows.is_empty() {
                    self.selected_benchmark_row = (self.selected_benchmark_row + 1) % self.benchmark_rows.len();
                    self.benchmark_table_state.select(Some(self.selected_benchmark_row));
                }
            }
            TrainingFocus::NpuLedger => {
                if !self.npu_grants.is_empty() {
                    self.selected_npu_row = (self.selected_npu_row + 1) % self.npu_grants.len();
                    self.npu_table_state.select(Some(self.selected_npu_row));
                }
            }
        }
    }

    /// Move to the previous row in the currently focused table.
    pub fn prev_row(&mut self) {
        match self.active_training_focus {
            TrainingFocus::BenchmarkTournament => {
                if !self.benchmark_rows.is_empty() {
                    if self.selected_benchmark_row == 0 {
                        self.selected_benchmark_row = self.benchmark_rows.len() - 1;
                    } else {
                        self.selected_benchmark_row -= 1;
                    }
                    self.benchmark_table_state.select(Some(self.selected_benchmark_row));
                }
            }
            TrainingFocus::NpuLedger => {
                if !self.npu_grants.is_empty() {
                    if self.selected_npu_row == 0 {
                        self.selected_npu_row = self.npu_grants.len() - 1;
                    } else {
                        self.selected_npu_row -= 1;
                    }
                    self.npu_table_state.select(Some(self.selected_npu_row));
                }
            }
        }
    }

    /// Switch focus between Benchmark Tournament and NPU Bonus Ledger tables.
    pub fn switch_focus(&mut self) {
        self.active_training_focus = match self.active_training_focus {
            TrainingFocus::BenchmarkTournament => TrainingFocus::NpuLedger,
            TrainingFocus::NpuLedger => TrainingFocus::BenchmarkTournament,
        };
    }

    /// Toggle pause state for continuous background training.
    pub fn toggle_pause(&mut self) {
        self.is_paused = !self.is_paused;
        if self.is_paused {
            self.governor_tier = RamGovernorTier::EmergencyPause;
        } else {
            self.governor_tier = RamGovernorTier::from_free_pct(self.host_ram_free_pct);
        }
    }

    /// Update host RAM metrics and adjust governor tier.
    pub fn update_ram_metrics(&mut self, free_pct: f64, free_gb: f64) {
        self.host_ram_free_pct = free_pct;
        self.host_ram_free_gb = free_gb;
        if !self.is_paused {
            self.governor_tier = RamGovernorTier::from_free_pct(free_pct);
        }
    }

    /// Record a new loss value into training history.
    pub fn record_loss(&mut self, loss: f64) {
        self.lora_job.loss_history.push(loss);
        self.lora_job.current_loss = loss;
    }
}

impl Default for TrainingState {
    fn default() -> Self {
        Self::new_canonical()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ram_governor_tier_boundaries() {
        assert_eq!(RamGovernorTier::from_free_pct(90.0), RamGovernorTier::Full);
        assert_eq!(RamGovernorTier::from_free_pct(85.001), RamGovernorTier::Full);
        assert_eq!(RamGovernorTier::from_free_pct(85.0), RamGovernorTier::Medium);
        assert_eq!(RamGovernorTier::from_free_pct(70.0), RamGovernorTier::Medium);
        assert_eq!(RamGovernorTier::from_free_pct(69.999), RamGovernorTier::Minimal);
        assert_eq!(RamGovernorTier::from_free_pct(50.0), RamGovernorTier::Minimal);
        assert_eq!(RamGovernorTier::from_free_pct(49.999), RamGovernorTier::EmergencyPause);
        assert_eq!(RamGovernorTier::from_free_pct(0.0), RamGovernorTier::EmergencyPause);
    }

    #[test]
    fn test_lora_job_progress_and_convergence() {
        let mut state = TrainingState::new_canonical();
        assert_eq!(state.lora_job.progress_pct(), 28.4);
        assert!(state.lora_job.is_loss_converging());

        state.record_loss(0.95);
        assert_eq!(state.lora_job.current_loss, 0.95);
        assert_eq!(state.lora_job.loss_history.len(), 7);
        assert!(state.lora_job.is_loss_converging());
    }

    #[test]
    fn test_navigation_and_focus_switching() {
        let mut state = TrainingState::new_canonical();
        assert_eq!(state.active_training_focus, TrainingFocus::BenchmarkTournament);
        assert_eq!(state.selected_benchmark_row, 0);

        state.next_row();
        assert_eq!(state.selected_benchmark_row, 1);
        state.next_row();
        assert_eq!(state.selected_benchmark_row, 2);
        state.next_row();
        assert_eq!(state.selected_benchmark_row, 0);

        state.prev_row();
        assert_eq!(state.selected_benchmark_row, 2);

        state.switch_focus();
        assert_eq!(state.active_training_focus, TrainingFocus::NpuLedger);
        assert_eq!(state.selected_npu_row, 0);

        state.next_row();
        assert_eq!(state.selected_npu_row, 1);
        state.next_row();
        assert_eq!(state.selected_npu_row, 0);

        state.prev_row();
        assert_eq!(state.selected_npu_row, 1);
    }

    #[test]
    fn test_pause_and_ram_metric_updates() {
        let mut state = TrainingState::new_canonical();
        assert!(!state.is_paused);
        assert_eq!(state.governor_tier, RamGovernorTier::Full);

        state.toggle_pause();
        assert!(state.is_paused);
        assert_eq!(state.governor_tier, RamGovernorTier::EmergencyPause);

        state.toggle_pause();
        assert!(!state.is_paused);
        assert_eq!(state.governor_tier, RamGovernorTier::Full);

        state.update_ram_metrics(65.0, 15.6);
        assert_eq!(state.governor_tier, RamGovernorTier::Minimal);
        assert_eq!(state.host_ram_free_pct, 65.0);
    }
}
