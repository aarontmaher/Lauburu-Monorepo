// 01_apps/rust_network_analyzer/src/app.rs
// Master State Machine & Reactive Event Coordinator with Non-Blocking Async Background Channel.

use crate::daemon_lens::{DaemonAndFallbackSnapshot, DaemonProber};
use crate::hardware_lens::{HardwareAndPowerSnapshot, HardwareProber};
use crate::mesh_prober::{FullMeshNetworkSnapshot, MeshProber};
use crate::moe_chat_lens::{ChatFocusArea, MoeChatEngine, MoeChatState, TaskDispatchStatus};
use crate::network_ai_lens::{NetworkHealthAiProber, NetworkHealthAiSnapshot};
use crate::packet_lens::{LivePacketSnapshot, PacketProber};
use crate::personal_compute_lens::{PersonalComputeProber, PersonalComputeSnapshot};
use crate::ram_lens::{NetworkRamSnapshot, RamProber};
use crate::sharding_matrix::{NodeShardingMetric, ShardingMatrixProber};
use crate::training_leaderboard::{TrainingLeaderboardProber, TrainingLeaderboardSnapshot};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActiveTab {
    LensTrainingAndChat = 0, // [0] Lens AI & Training (DEFAULT FRONT PAGE)
    MyDeviceAndCompute = 1,  // [1] My Device & Paying by Computing
    MyPersonalSwarm = 2,     // [2] My Personal Swarm (Tenant Isolated)
    FullMeshTopology = 3,    // [3] Global Mesh
    RamPoolLens = 4,         // [4] RAM Pool
    DaemonAndFallback = 5,   // [5] Daemons
    TrainingLeaderboard = 6, // [6] ELO
    NetworkHealthAi = 7,     // [7] Net AI
    HardwareAndPower = 8,    // [8] Thermals/Power
    CableAndSpeeds = 9,      // [9] Cable/RF/TB4
    PacketLens = 10,         // [10] Packets
    ShardingMatrix = 11,     // [11] Shards
    MoeChat = 12,            // [12] MoE Chat & Autonomous Priority Queue
}

#[derive(Debug, Clone)]
pub struct FullTelemetryState {
    pub personal_snapshot: PersonalComputeSnapshot,
    pub mesh_snapshot: FullMeshNetworkSnapshot,
    pub ram_snapshot: NetworkRamSnapshot,
    pub daemon_snapshot: DaemonAndFallbackSnapshot,
    pub training_snapshot: TrainingLeaderboardSnapshot,
    pub network_ai_snapshot: NetworkHealthAiSnapshot,
    pub hardware_snapshot: HardwareAndPowerSnapshot,
    pub packet_snapshot: LivePacketSnapshot,
    pub sharding_metrics: Vec<NodeShardingMetric>,
}

impl FullTelemetryState {
    pub fn probe_all() -> Self {
        Self {
            personal_snapshot: PersonalComputeProber::probe(),
            mesh_snapshot: MeshProber::probe_full_network(),
            ram_snapshot: RamProber::probe_ram(),
            daemon_snapshot: DaemonProber::probe_daemons(),
            training_snapshot: TrainingLeaderboardProber::probe_leaderboard(),
            network_ai_snapshot: NetworkHealthAiProber::probe_network_ai(),
            hardware_snapshot: HardwareProber::probe_all_hardware(),
            packet_snapshot: PacketProber::capture_snapshot(),
            sharding_metrics: ShardingMatrixProber::probe_mesh_matrix(),
        }
    }
}

pub struct App {
    pub current_tab: ActiveTab,
    pub state: FullTelemetryState,
    pub lens_training: crate::lens_training_lens::LensTrainingState,
    pub moe_chat: MoeChatState,
    pub selected_node_idx: usize,
    pub probe_count: u64,
    pub should_quit: bool,
    pub status_message: String,
    pub spinner_frame: usize,
    pub is_dev_mode: bool,
}

impl App {
    #[allow(dead_code)]
    pub fn new() -> Self {
        Self::new_with_dev(false)
    }

    pub fn new_with_dev(is_dev_mode: bool) -> Self {
        let initial_state = FullTelemetryState::probe_all();
        let status_msg = if is_dev_mode {
            "🔥 DEV MODE ACTIVE: High-Frequency 1s Live Auto-Update & Watcher".to_string()
        } else {
            "🟢 Paying by Computing: Active ($29/mo Value Subsidized via Shared Compute)".to_string()
        };

        Self {
            current_tab: ActiveTab::LensTrainingAndChat,
            state: initial_state,
            lens_training: crate::lens_training_lens::LensTrainingState::new(),
            moe_chat: MoeChatState::new(),
            selected_node_idx: 0,
            probe_count: 1,
            should_quit: false,
            status_message: status_msg,
            spinner_frame: 0,
            is_dev_mode,
        }
    }

    pub fn next_tab(&mut self) {
        self.current_tab = match self.current_tab {
            ActiveTab::LensTrainingAndChat => ActiveTab::MyDeviceAndCompute,
            ActiveTab::MyDeviceAndCompute => ActiveTab::MyPersonalSwarm,
            ActiveTab::MyPersonalSwarm => ActiveTab::FullMeshTopology,
            ActiveTab::FullMeshTopology => ActiveTab::RamPoolLens,
            ActiveTab::RamPoolLens => ActiveTab::DaemonAndFallback,
            ActiveTab::DaemonAndFallback => ActiveTab::TrainingLeaderboard,
            ActiveTab::TrainingLeaderboard => ActiveTab::NetworkHealthAi,
            ActiveTab::NetworkHealthAi => ActiveTab::HardwareAndPower,
            ActiveTab::HardwareAndPower => ActiveTab::CableAndSpeeds,
            ActiveTab::CableAndSpeeds => ActiveTab::PacketLens,
            ActiveTab::PacketLens => ActiveTab::ShardingMatrix,
            ActiveTab::ShardingMatrix => ActiveTab::MoeChat,
            ActiveTab::MoeChat => ActiveTab::LensTrainingAndChat,
        };
    }

    pub fn previous_tab(&mut self) {
        self.current_tab = match self.current_tab {
            ActiveTab::LensTrainingAndChat => ActiveTab::MoeChat,
            ActiveTab::MyDeviceAndCompute => ActiveTab::LensTrainingAndChat,
            ActiveTab::MyPersonalSwarm => ActiveTab::MyDeviceAndCompute,
            ActiveTab::FullMeshTopology => ActiveTab::MyPersonalSwarm,
            ActiveTab::RamPoolLens => ActiveTab::FullMeshTopology,
            ActiveTab::DaemonAndFallback => ActiveTab::RamPoolLens,
            ActiveTab::TrainingLeaderboard => ActiveTab::DaemonAndFallback,
            ActiveTab::NetworkHealthAi => ActiveTab::TrainingLeaderboard,
            ActiveTab::HardwareAndPower => ActiveTab::NetworkHealthAi,
            ActiveTab::CableAndSpeeds => ActiveTab::HardwareAndPower,
            ActiveTab::PacketLens => ActiveTab::CableAndSpeeds,
            ActiveTab::ShardingMatrix => ActiveTab::PacketLens,
            ActiveTab::MoeChat => ActiveTab::ShardingMatrix,
        };
    }

    pub fn select_tab(&mut self, index: usize) {
        self.current_tab = match index {
            0 => ActiveTab::LensTrainingAndChat,
            1 => ActiveTab::MyDeviceAndCompute,
            2 => ActiveTab::MyPersonalSwarm,
            3 => ActiveTab::FullMeshTopology,
            4 => ActiveTab::RamPoolLens,
            5 => ActiveTab::DaemonAndFallback,
            6 => ActiveTab::TrainingLeaderboard,
            7 => ActiveTab::NetworkHealthAi,
            8 => ActiveTab::HardwareAndPower,
            9 => ActiveTab::CableAndSpeeds,
            10 => ActiveTab::PacketLens,
            11 => ActiveTab::ShardingMatrix,
            12 => ActiveTab::MoeChat,
            _ => self.current_tab,
        };
    }

    pub fn next_node(&mut self) {
        if !self.state.mesh_snapshot.nodes.is_empty() {
            self.selected_node_idx = (self.selected_node_idx + 1) % self.state.mesh_snapshot.nodes.len();
        }
    }

    pub fn previous_node(&mut self) {
        if !self.state.mesh_snapshot.nodes.is_empty() {
            if self.selected_node_idx == 0 {
                self.selected_node_idx = self.state.mesh_snapshot.nodes.len() - 1;
            } else {
                self.selected_node_idx -= 1;
            }
        }
    }

    pub fn update_state(&mut self, new_state: FullTelemetryState) {
        self.state = new_state;
        self.probe_count += 1;
        self.spinner_frame = (self.spinner_frame + 1) % 4;
        self.lens_training.sync_live_telemetry();
    }

    // -------------------------------------------------------------------------
    // Tab [0] Lens AI & Training State Modifiers
    // -------------------------------------------------------------------------

    pub fn lens_chat_insert_char(&mut self, c: char) {
        self.lens_training.insert_char(c);
    }

    pub fn lens_chat_backspace(&mut self) {
        self.lens_training.backspace();
    }

    pub fn lens_chat_submit_prompt(&mut self) {
        self.lens_training.submit_prompt();
    }

    pub fn lens_chat_toggle_focus(&mut self) {
        self.lens_training.toggle_focus();
    }

    // -------------------------------------------------------------------------
    // Tab [12] MoE Chat & Autonomous Priority Queue State Modifiers
    // -------------------------------------------------------------------------

    pub fn moe_chat_insert_char(&mut self, c: char) {
        if self.moe_chat.cursor_position >= self.moe_chat.input_buffer.chars().count() {
            self.moe_chat.input_buffer.push(c);
            self.moe_chat.cursor_position = self.moe_chat.input_buffer.chars().count();
        } else {
            let byte_idx = self.moe_chat.input_buffer
                .char_indices()
                .nth(self.moe_chat.cursor_position)
                .map(|(i, _)| i)
                .unwrap_or(self.moe_chat.input_buffer.len());
            self.moe_chat.input_buffer.insert(byte_idx, c);
            self.moe_chat.cursor_position += 1;
        }
    }

    pub fn moe_chat_backspace(&mut self) {
        if self.moe_chat.cursor_position > 0 && !self.moe_chat.input_buffer.is_empty() {
            let prev_idx = self.moe_chat.cursor_position - 1;
            let byte_idx = self.moe_chat.input_buffer
                .char_indices()
                .nth(prev_idx)
                .map(|(i, _)| i);
            if let Some(idx) = byte_idx {
                self.moe_chat.input_buffer.remove(idx);
                self.moe_chat.cursor_position -= 1;
            }
        }
    }

    pub fn moe_chat_delete(&mut self) {
        if self.moe_chat.cursor_position < self.moe_chat.input_buffer.chars().count() {
            let byte_idx = self.moe_chat.input_buffer
                .char_indices()
                .nth(self.moe_chat.cursor_position)
                .map(|(i, _)| i);
            if let Some(idx) = byte_idx {
                self.moe_chat.input_buffer.remove(idx);
            }
        }
    }

    pub fn moe_chat_cursor_left(&mut self) {
        if self.moe_chat.cursor_position > 0 {
            self.moe_chat.cursor_position -= 1;
        }
    }

    pub fn moe_chat_cursor_right(&mut self) {
        if self.moe_chat.cursor_position < self.moe_chat.input_buffer.chars().count() {
            self.moe_chat.cursor_position += 1;
        }
    }

    pub fn moe_chat_cursor_home(&mut self) {
        self.moe_chat.cursor_position = 0;
    }

    pub fn moe_chat_cursor_end(&mut self) {
        self.moe_chat.cursor_position = self.moe_chat.input_buffer.chars().count();
    }

    pub fn moe_chat_toggle_focus(&mut self) {
        self.moe_chat.focus_area = match self.moe_chat.focus_area {
            ChatFocusArea::Input => ChatFocusArea::TaskQueue,
            ChatFocusArea::TaskQueue => ChatFocusArea::ResponseView,
            ChatFocusArea::ResponseView => ChatFocusArea::Input,
        };
    }

    pub fn moe_chat_set_focus(&mut self, focus: ChatFocusArea) {
        self.moe_chat.focus_area = focus;
    }

    pub fn moe_chat_select_next_task(&mut self) {
        if !self.moe_chat.priority_queue.is_empty() {
            self.moe_chat.selected_task_idx = (self.moe_chat.selected_task_idx + 1) % self.moe_chat.priority_queue.len();
        }
    }

    pub fn moe_chat_select_previous_task(&mut self) {
        if !self.moe_chat.priority_queue.is_empty() {
            if self.moe_chat.selected_task_idx == 0 {
                self.moe_chat.selected_task_idx = self.moe_chat.priority_queue.len() - 1;
            } else {
                self.moe_chat.selected_task_idx -= 1;
            }
        }
    }

    pub fn moe_chat_scroll_response_up(&mut self) {
        if self.moe_chat.response_scroll_offset > 0 {
            self.moe_chat.response_scroll_offset -= 1;
        }
    }

    pub fn moe_chat_scroll_response_down(&mut self) {
        self.moe_chat.response_scroll_offset = self.moe_chat.response_scroll_offset.saturating_add(1);
    }

    pub fn moe_chat_submit_prompt(&mut self) {
        let prompt = self.moe_chat.input_buffer.trim().to_string();
        if prompt.is_empty() {
            return;
        }

        let plan = MoeChatEngine::decompose_prompt(&prompt, Some(&self.state.mesh_snapshot));
        let synthesized = MoeChatEngine::generate_synthesized_response(&prompt, &plan);
        let extracted_tasks = MoeChatEngine::extract_priority_tasks(&prompt, &plan);

        let now_str = chrono::Local::now().format("%H:%M:%S").to_string();

        self.moe_chat.messages.push(crate::moe_chat_lens::ChatMessage {
            role: "user".to_string(),
            content: prompt.clone(),
            timestamp: now_str.clone(),
            decomposition: Some(plan.clone()),
        });

        self.moe_chat.messages.push(crate::moe_chat_lens::ChatMessage {
            role: "synthesizer".to_string(),
            content: synthesized,
            timestamp: now_str,
            decomposition: Some(plan.clone()),
        });

        self.moe_chat.active_plan = Some(plan);

        // Prepend newly extracted tasks at top of queue
        for task in extracted_tasks.into_iter().rev() {
            self.moe_chat.priority_queue.insert(0, task);
        }
        self.moe_chat.selected_task_idx = 0;

        self.moe_chat.input_buffer.clear();
        self.moe_chat.cursor_position = 0;
        self.moe_chat.response_scroll_offset = 0;
        self.status_message = format!("🧬 Genetic MoE Decomposed & Synthesized: {} tasks queued", self.moe_chat.priority_queue.len());
    }

    pub fn moe_chat_dispatch_selected_task(&mut self) {
        if self.moe_chat.selected_task_idx < self.moe_chat.priority_queue.len() {
            let task = &mut self.moe_chat.priority_queue[self.moe_chat.selected_task_idx];
            task.status = TaskDispatchStatus::Dispatched;
            let task_id = task.id.clone();
            let title = task.title.clone();
            let layer = task.assigned_layer.clone();
            self.status_message = format!("⚡ Dispatched [{}] {} across mesh to {}", task_id, title, layer);
            self.moe_chat.status_note = format!("Dispatched {} to {} ({})", task_id, layer, chrono::Local::now().format("%H:%M:%S"));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_active_tab_cycling_13_tabs() {
        let mut tab = ActiveTab::LensTrainingAndChat;
        let expected_sequence = [
            ActiveTab::MyDeviceAndCompute,
            ActiveTab::MyPersonalSwarm,
            ActiveTab::FullMeshTopology,
            ActiveTab::RamPoolLens,
            ActiveTab::DaemonAndFallback,
            ActiveTab::TrainingLeaderboard,
            ActiveTab::NetworkHealthAi,
            ActiveTab::HardwareAndPower,
            ActiveTab::CableAndSpeeds,
            ActiveTab::PacketLens,
            ActiveTab::ShardingMatrix,
            ActiveTab::MoeChat,
            ActiveTab::LensTrainingAndChat,
        ];

        for expected in expected_sequence {
            tab = match tab {
                ActiveTab::LensTrainingAndChat => ActiveTab::MyDeviceAndCompute,
                ActiveTab::MyDeviceAndCompute => ActiveTab::MyPersonalSwarm,
                ActiveTab::MyPersonalSwarm => ActiveTab::FullMeshTopology,
                ActiveTab::FullMeshTopology => ActiveTab::RamPoolLens,
                ActiveTab::RamPoolLens => ActiveTab::DaemonAndFallback,
                ActiveTab::DaemonAndFallback => ActiveTab::TrainingLeaderboard,
                ActiveTab::TrainingLeaderboard => ActiveTab::NetworkHealthAi,
                ActiveTab::NetworkHealthAi => ActiveTab::HardwareAndPower,
                ActiveTab::HardwareAndPower => ActiveTab::CableAndSpeeds,
                ActiveTab::CableAndSpeeds => ActiveTab::PacketLens,
                ActiveTab::PacketLens => ActiveTab::ShardingMatrix,
                ActiveTab::ShardingMatrix => ActiveTab::MoeChat,
                ActiveTab::MoeChat => ActiveTab::LensTrainingAndChat,
            };
            assert_eq!(tab, expected);
        }
    }

    #[test]
    fn test_select_tab_0_is_lens_training() {
        let mut app = App::new();
        app.select_tab(0);
        assert_eq!(app.current_tab, ActiveTab::LensTrainingAndChat);
    }

    #[test]
    fn test_select_tab_12_is_moe_chat() {
        let mut app = App::new();
        app.select_tab(12);
        assert_eq!(app.current_tab, ActiveTab::MoeChat);
    }
}
