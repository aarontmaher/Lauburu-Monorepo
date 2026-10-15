// =============================================================================
// In-Process Micro-AI Healer & Autonomic Governor (Feature F18)
// Real-time offline telemetry reasoning and self-healing directives
// =============================================================================

use crate::transports::{CascadingTransportManager, TransportStatus};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fmt;

/// Categories of autonomous self-healing actions emitted by the local AI governor.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum DirectiveType {
    /// Promote a surviving node to Master Coordinator when L1 is partitioned
    PromoteCoordinator,
    /// Seamlessly migrate inference streams to the next available physical transport
    MigrateTransportTier,
    /// Reallocate VRAM shard layers across remaining active GPU/NPU workers
    RebalanceVramShards,
    /// Re-initialize interface, drop ARP caches, or restart local tunnel socket
    CycleInterface,
    /// Enforce thermal or battery throttling on mobile nodes (Pixel/Samsung)
    ThermalThrottleNode,
    /// Temporarily quarantine a flapping or unverified peer
    IsolateDegradedNode,
    /// Ensure Nomad Courier SSH multiplexed sockets are refreshed
    RestoreNomadCourierMux,
}

impl fmt::Display for DirectiveType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DirectiveType::PromoteCoordinator => write!(f, "PROMOTE_COORDINATOR"),
            DirectiveType::MigrateTransportTier => write!(f, "MIGRATE_TRANSPORT"),
            DirectiveType::RebalanceVramShards => write!(f, "REBALANCE_SHARDS"),
            DirectiveType::CycleInterface => write!(f, "CYCLE_INTERFACE"),
            DirectiveType::ThermalThrottleNode => write!(f, "THERMAL_THROTTLE"),
            DirectiveType::IsolateDegradedNode => write!(f, "ISOLATE_NODE"),
            DirectiveType::RestoreNomadCourierMux => write!(f, "RESTORE_NOMAD_MUX"),
        }
    }
}

/// A concrete self-healing directive formulated by the autonomic AI engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealingDirective {
    pub id: String,
    pub directive_type: DirectiveType,
    pub target_node_id: String,
    pub rationale: String,
    pub confidence_score: f64,
    pub applied: bool,
    pub timestamp: String,
}

/// Aggregate health and offline survival index of the entire 7-node cluster.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterVitality {
    pub overall_score_pct: f64,
    pub active_nodes: usize,
    pub total_nodes: usize,
    pub active_vram_gb: f64,
    pub max_vram_gb: f64,
    pub offline_resilience_index: f64,
    pub active_master_id: String,
}

impl Default for ClusterVitality {
    fn default() -> Self {
        Self {
            overall_score_pct: 100.0,
            active_nodes: 7,
            total_nodes: 7,
            active_vram_gb: 82.8,
            max_vram_gb: 82.8,
            offline_resilience_index: 0.98,
            active_master_id: "mac_host".to_string(),
        }
    }
}

/// In-Process Autonomic Micro-AI Healer engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InProcessHealer {
    pub directives: Vec<HealingDirective>,
    pub max_history: usize,
}

impl Default for InProcessHealer {
    fn default() -> Self {
        let mut healer = Self {
            directives: Vec::new(),
            max_history: 50,
        };
        // Seed bootstrap healing log
        healer.record_directive(HealingDirective {
            id: "DIR-001".to_string(),
            directive_type: DirectiveType::RestoreNomadCourierMux,
            target_node_id: "mac_host".to_string(),
            rationale: "Prewarmed persistent ControlMaster SSH multiplex socket for sub-150ms commands".to_string(),
            confidence_score: 0.99,
            applied: true,
            timestamp: Utc::now().format("%H:%M:%S").to_string(),
        });
        healer.record_directive(HealingDirective {
            id: "DIR-002".to_string(),
            directive_type: DirectiveType::MigrateTransportTier,
            target_node_id: "linux_head_node".to_string(),
            rationale: "Verified Dual-Subnet Ethernet (192.168.20.224) fast path over high-latency WAN".to_string(),
            confidence_score: 0.97,
            applied: true,
            timestamp: Utc::now().format("%H:%M:%S").to_string(),
        });
        healer
    }
}

impl InProcessHealer {
    pub fn record_directive(&mut self, directive: HealingDirective) {
        if self.directives.len() >= self.max_history {
            self.directives.remove(0);
        }
        self.directives.push(directive);
    }

    /// Autonomous diagnostic pass across all physical links.
    pub fn diagnose(&mut self, transport_mgr: &CascadingTransportManager) -> Vec<HealingDirective> {
        let mut new_directives = Vec::new();
        let timestamp = Utc::now().format("%H:%M:%S").to_string();

        let node_ids = [
            "mac_host",
            "macbook_pro",
            "linux_head_node",
            "linux_tablet",
            "macbook_air",
            "pixel_10",
            "samsung_s20",
        ];

        for node_id in &node_ids {
            let links = transport_mgr.get_links_for_node(node_id);
            let active_link = links.iter().find(|l| l.is_active_route);

            match active_link {
                Some(link) if link.status == TransportStatus::Offline => {
                    // Rule 1: Active link is offline -> Trigger transport migration
                    let dir = HealingDirective {
                        id: format!("DIR-{:03}", self.directives.len() + new_directives.len() + 1),
                        directive_type: DirectiveType::MigrateTransportTier,
                        target_node_id: node_id.to_string(),
                        rationale: format!(
                            "Active route on {} is offline; cascading to standby offline transport",
                            link.tier
                        ),
                        confidence_score: 0.96,
                        applied: false,
                        timestamp: timestamp.clone(),
                    };
                    new_directives.push(dir);
                }
                Some(link) if link.status == TransportStatus::Degraded => {
                    // Rule 2: High loss or latency degradation -> Attempt interface cycle
                    let dir = HealingDirective {
                        id: format!("DIR-{:03}", self.directives.len() + new_directives.len() + 1),
                        directive_type: DirectiveType::CycleInterface,
                        target_node_id: node_id.to_string(),
                        rationale: format!(
                            "Transport {} packet loss at {:.1}%; cycling link socket",
                            link.tier, link.loss_pct
                        ),
                        confidence_score: 0.88,
                        applied: false,
                        timestamp: timestamp.clone(),
                    };
                    new_directives.push(dir);
                }
                None if *node_id != "mac_host" => {
                    // Rule 3: No active route -> Isolate or fallback
                    let dir = HealingDirective {
                        id: format!("DIR-{:03}", self.directives.len() + new_directives.len() + 1),
                        directive_type: DirectiveType::IsolateDegradedNode,
                        target_node_id: node_id.to_string(),
                        rationale: "All candidate transports offline; isolating node from active VRAM pool".to_string(),
                        confidence_score: 0.94,
                        applied: false,
                        timestamp: timestamp.clone(),
                    };
                    new_directives.push(dir);
                }
                _ => {}
            }
        }

        // Check coordinator health
        let mac_links = transport_mgr.get_links_for_node("mac_host");
        if mac_links.iter().all(|l| l.status == TransportStatus::Offline) {
            let dir = HealingDirective {
                id: format!("DIR-{:03}", self.directives.len() + new_directives.len() + 1),
                directive_type: DirectiveType::PromoteCoordinator,
                target_node_id: "linux_head_node".to_string(),
                rationale: "Master Coordinator (mac_host) unresponsive; promoting Ryzen 7 Linux node".to_string(),
                confidence_score: 0.99,
                applied: false,
                timestamp: timestamp.clone(),
            };
            new_directives.push(dir);
        }

        for dir in &new_directives {
            self.record_directive(dir.clone());
        }

        new_directives
    }

    /// Calculate cluster vitality score and offline survival index.
    pub fn calculate_vitality(&self, transport_mgr: &CascadingTransportManager) -> ClusterVitality {
        let node_ids = [
            ("mac_host", 21.6),
            ("macbook_pro", 14.0),
            ("linux_head_node", 13.8),
            ("linux_tablet", 6.0),
            ("macbook_air", 14.0),
            ("pixel_10", 12.5),
            ("samsung_s20", 9.0),
        ];

        let mut active_count = 0;
        let mut active_vram: f64 = 0.0;
        let mut total_score: f64 = 0.0;

        for (node_id, vram) in &node_ids {
            let links = transport_mgr.get_links_for_node(node_id);
            let has_active = links.iter().any(|l| l.is_active_route && l.status == TransportStatus::Active);
            let has_degraded = links.iter().any(|l| l.is_active_route && l.status == TransportStatus::Degraded);

            if has_active {
                active_count += 1;
                active_vram += vram;
                total_score += 100.0;
            } else if has_degraded {
                active_count += 1;
                active_vram += vram * 0.75;
                total_score += 65.0;
            }
        }

        let overall_pct = if !node_ids.is_empty() {
            total_score / (node_ids.len() as f64)
        } else {
            0.0
        };

        let offline_resilience = (active_count as f64 / 7.0) * 0.7 + (overall_pct / 100.0) * 0.3;

        ClusterVitality {
            overall_score_pct: (overall_pct * 10.0).round() / 10.0,
            active_nodes: active_count,
            total_nodes: 7,
            active_vram_gb: (active_vram * 10.0).round() / 10.0,
            max_vram_gb: 82.8,
            offline_resilience_index: (offline_resilience * 100.0).round() / 100.0,
            active_master_id: "mac_host".to_string(),
        }
    }
}

/// Consolidated state model for Tab 8 (Autonomic Sentinel).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealerState {
    pub healer: InProcessHealer,
    pub transport_mgr: CascadingTransportManager,
    pub vitality: ClusterVitality,
    pub selected_link_index: usize,
    pub selected_directive_index: usize,
    pub auto_healing_active: bool,
}

impl Default for HealerState {
    fn default() -> Self {
        let transport_mgr = CascadingTransportManager::default();
        let healer = InProcessHealer::default();
        let vitality = healer.calculate_vitality(&transport_mgr);

        Self {
            healer,
            transport_mgr,
            vitality,
            selected_link_index: 0,
            selected_directive_index: 0,
            auto_healing_active: true,
        }
    }
}

impl HealerState {
    pub fn trigger_diagnostics(&mut self) {
        let new_dirs = self.healer.diagnose(&self.transport_mgr);
        if self.auto_healing_active {
            for dir in new_dirs {
                if dir.directive_type == DirectiveType::MigrateTransportTier {
                    self.transport_mgr.failover_next_tier(&dir.target_node_id);
                }
            }
        }
        self.vitality = self.healer.calculate_vitality(&self.transport_mgr);
    }

    pub fn next_link(&mut self) {
        if !self.transport_mgr.links.is_empty() {
            self.selected_link_index = (self.selected_link_index + 1) % self.transport_mgr.links.len();
        }
    }

    pub fn prev_link(&mut self) {
        if !self.transport_mgr.links.is_empty() {
            self.selected_link_index = if self.selected_link_index == 0 {
                self.transport_mgr.links.len() - 1
            } else {
                self.selected_link_index - 1
            };
        }
    }

    pub fn force_failover_selected(&mut self) {
        if self.selected_link_index < self.transport_mgr.links.len() {
            let node_id = self.transport_mgr.links[self.selected_link_index].node_id.clone();
            self.transport_mgr.failover_next_tier(&node_id);
            self.vitality = self.healer.calculate_vitality(&self.transport_mgr);
        }
    }
}
