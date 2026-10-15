// =============================================================================
// 6-Tier Cascading Physical Transport Matrix (Feature F17)
// Autonomous offline link-layer hopping for 7-node Lauburu AI Mesh
// =============================================================================

use serde::{Deserialize, Serialize};
use std::fmt;

/// The 6 physical and link-layer transport tiers, ordered by priority / performance.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum TransportTier {
    /// Tier 1: 40Gbps Thunderbolt 4 / USB4 DMA PCIe Bridge (0.27ms RTT)
    Tier1ThunderboltDma,
    /// Tier 2: 1Gbps Dual-Subnet Fixed Copper LAN (192.168.8.x / 192.168.20.x, 0.90ms RTT)
    Tier2DualEthernet,
    /// Tier 3: 802.11s Wi-Fi Ad-Hoc / Wi-Fi Direct Peer Mesh (Zero-Router, 3-8ms RTT)
    Tier3WifiAdHoc,
    /// Tier 4: Direct USB-C High-Speed ADB Reverse-Tether Sockets (Mobile Nodes, 2-5ms RTT)
    Tier4AdbUsbTunnel,
    /// Tier 5: Bluetooth Low Energy / Bluetooth PAN Beaconing (Low-Power, 40-120ms RTT)
    Tier5BleBeacon,
    /// Tier 6: Local Unix Domain Sockets & Named IPC Pipes (/tmp/lauburu.sock, <0.05ms RTT)
    Tier6UnixSocket,
}

impl Default for TransportTier {
    fn default() -> Self {
        TransportTier::Tier2DualEthernet
    }
}

impl fmt::Display for TransportTier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TransportTier::Tier1ThunderboltDma => write!(f, "TB4 DMA Bridge (40G)"),
            TransportTier::Tier2DualEthernet => write!(f, "Dual-Subnet Copper (1G)"),
            TransportTier::Tier3WifiAdHoc => write!(f, "Wi-Fi Direct Ad-Hoc (802.11s)"),
            TransportTier::Tier4AdbUsbTunnel => write!(f, "USB-C ADB Reverse Tunnel"),
            TransportTier::Tier5BleBeacon => write!(f, "BLE Mesh Control Beacon"),
            TransportTier::Tier6UnixSocket => write!(f, "Local Unix IPC Domain"),
        }
    }
}

impl TransportTier {
    pub fn all() -> &'static [TransportTier] {
        &[
            TransportTier::Tier1ThunderboltDma,
            TransportTier::Tier2DualEthernet,
            TransportTier::Tier3WifiAdHoc,
            TransportTier::Tier4AdbUsbTunnel,
            TransportTier::Tier5BleBeacon,
            TransportTier::Tier6UnixSocket,
        ]
    }

    pub fn nominal_latency_ms(&self) -> f64 {
        match self {
            TransportTier::Tier1ThunderboltDma => 0.27,
            TransportTier::Tier2DualEthernet => 0.90,
            TransportTier::Tier3WifiAdHoc => 4.50,
            TransportTier::Tier4AdbUsbTunnel => 2.80,
            TransportTier::Tier5BleBeacon => 65.0,
            TransportTier::Tier6UnixSocket => 0.04,
        }
    }

    pub fn nominal_bandwidth_mbps(&self) -> f64 {
        match self {
            TransportTier::Tier1ThunderboltDma => 40_000.0,
            TransportTier::Tier2DualEthernet => 1_000.0,
            TransportTier::Tier3WifiAdHoc => 850.0,
            TransportTier::Tier4AdbUsbTunnel => 480.0,
            TransportTier::Tier5BleBeacon => 2.0,
            TransportTier::Tier6UnixSocket => 50_000.0,
        }
    }
}

/// Operational state of a physical transport link.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransportStatus {
    Active,
    Standby,
    Degraded,
    Offline,
}

impl fmt::Display for TransportStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TransportStatus::Active => write!(f, "ACTIVE"),
            TransportStatus::Standby => write!(f, "STANDBY"),
            TransportStatus::Degraded => write!(f, "DEGRADED"),
            TransportStatus::Offline => write!(f, "OFFLINE"),
        }
    }
}

/// A specific physical link bound to a target cluster node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportLink {
    pub node_id: String,
    pub tier: TransportTier,
    pub name: String,
    pub endpoint: String,
    pub status: TransportStatus,
    pub latency_ms: f64,
    pub bandwidth_mbps: f64,
    pub loss_pct: f64,
    pub consecutive_failures: u32,
    pub is_active_route: bool,
}

/// Cascading transport manager maintaining active and fallback routes across all 7 nodes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CascadingTransportManager {
    pub links: Vec<TransportLink>,
    pub auto_failover_enabled: bool,
}

impl Default for CascadingTransportManager {
    fn default() -> Self {
        Self::new_canonical_7_nodes()
    }
}

impl CascadingTransportManager {
    pub fn new() -> Self {
        Self {
            links: Vec::new(),
            auto_failover_enabled: true,
        }
    }

    /// Seed the canonical 7-node physical transport matrix.
    pub fn new_canonical_7_nodes() -> Self {
        let mut mgr = Self::new();

        // 1. Mac Mini Host (L1) - Master
        mgr.register_link(TransportLink {
            node_id: "mac_host".to_string(),
            tier: TransportTier::Tier6UnixSocket,
            name: "Local IPC Loopback".to_string(),
            endpoint: "/tmp/lauburu_mesh.sock".to_string(),
            status: TransportStatus::Active,
            latency_ms: 0.04,
            bandwidth_mbps: 50_000.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });

        // 2. MacBook Pro Intel Vault (L2)
        mgr.register_link(TransportLink {
            node_id: "macbook_pro".to_string(),
            tier: TransportTier::Tier1ThunderboltDma,
            name: "TB4 Direct DMA".to_string(),
            endpoint: "10.0.0.2".to_string(),
            status: TransportStatus::Active,
            latency_ms: 0.27,
            bandwidth_mbps: 40_000.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });
        mgr.register_link(TransportLink {
            node_id: "macbook_pro".to_string(),
            tier: TransportTier::Tier2DualEthernet,
            name: "1GbE Copper LAN".to_string(),
            endpoint: "192.168.8.127".to_string(),
            status: TransportStatus::Standby,
            latency_ms: 0.95,
            bandwidth_mbps: 1_000.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: false,
        });

        // 3. Linux Head Node (L3)
        mgr.register_link(TransportLink {
            node_id: "linux_head_node".to_string(),
            tier: TransportTier::Tier2DualEthernet,
            name: "Dual-Subnet Copper (Eth)".to_string(),
            endpoint: "192.168.20.224".to_string(),
            status: TransportStatus::Active,
            latency_ms: 0.88,
            bandwidth_mbps: 1_000.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });
        mgr.register_link(TransportLink {
            node_id: "linux_head_node".to_string(),
            tier: TransportTier::Tier3WifiAdHoc,
            name: "802.11s Ad-Hoc Mesh".to_string(),
            endpoint: "10.12.211.206".to_string(),
            status: TransportStatus::Standby,
            latency_ms: 4.20,
            bandwidth_mbps: 850.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: false,
        });

        // 4. Linux Tablet (L4)
        mgr.register_link(TransportLink {
            node_id: "linux_tablet".to_string(),
            tier: TransportTier::Tier3WifiAdHoc,
            name: "Direct Wi-Fi Peer".to_string(),
            endpoint: "192.168.8.189".to_string(),
            status: TransportStatus::Active,
            latency_ms: 5.10,
            bandwidth_mbps: 450.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });
        mgr.register_link(TransportLink {
            node_id: "linux_tablet".to_string(),
            tier: TransportTier::Tier5BleBeacon,
            name: "BLE Mesh Control Link".to_string(),
            endpoint: "ble:c8:f9:22:14".to_string(),
            status: TransportStatus::Standby,
            latency_ms: 68.0,
            bandwidth_mbps: 2.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: false,
        });

        // 5. MacBook Air M4 (L5)
        mgr.register_link(TransportLink {
            node_id: "macbook_air".to_string(),
            tier: TransportTier::Tier1ThunderboltDma,
            name: "TB4 Daisy Chain".to_string(),
            endpoint: "10.0.0.5".to_string(),
            status: TransportStatus::Active,
            latency_ms: 0.32,
            bandwidth_mbps: 40_000.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });
        mgr.register_link(TransportLink {
            node_id: "macbook_air".to_string(),
            tier: TransportTier::Tier2DualEthernet,
            name: "Wi-Fi 7 MLO Local LAN".to_string(),
            endpoint: "192.168.8.222".to_string(),
            status: TransportStatus::Standby,
            latency_ms: 1.80,
            bandwidth_mbps: 2_400.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: false,
        });

        // 6. Pixel 10 Pro XL (L6)
        mgr.register_link(TransportLink {
            node_id: "pixel_10".to_string(),
            tier: TransportTier::Tier4AdbUsbTunnel,
            name: "USB-C 3.2 High-Speed Tunnel".to_string(),
            endpoint: "adb:100.73.38.87:8084".to_string(),
            status: TransportStatus::Active,
            latency_ms: 2.60,
            bandwidth_mbps: 480.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });
        mgr.register_link(TransportLink {
            node_id: "pixel_10".to_string(),
            tier: TransportTier::Tier3WifiAdHoc,
            name: "Wi-Fi Direct Hotspot".to_string(),
            endpoint: "192.168.49.1".to_string(),
            status: TransportStatus::Standby,
            latency_ms: 8.50,
            bandwidth_mbps: 600.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: false,
        });

        // 7. Samsung S20 (L7)
        mgr.register_link(TransportLink {
            node_id: "samsung_s20".to_string(),
            tier: TransportTier::Tier4AdbUsbTunnel,
            name: "Router USB Bridge ADB".to_string(),
            endpoint: "adb:100.84.40.95:5555".to_string(),
            status: TransportStatus::Active,
            latency_ms: 3.10,
            bandwidth_mbps: 480.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: true,
        });
        mgr.register_link(TransportLink {
            node_id: "samsung_s20".to_string(),
            tier: TransportTier::Tier5BleBeacon,
            name: "Bluetooth PAN Bridge".to_string(),
            endpoint: "bt:s20:pan".to_string(),
            status: TransportStatus::Standby,
            latency_ms: 72.0,
            bandwidth_mbps: 2.0,
            loss_pct: 0.0,
            consecutive_failures: 0,
            is_active_route: false,
        });

        mgr
    }

    pub fn register_link(&mut self, link: TransportLink) {
        self.links.push(link);
    }

    pub fn get_links_for_node(&self, node_id: &str) -> Vec<&TransportLink> {
        self.links.iter().filter(|l| l.node_id == node_id).collect()
    }

    pub fn active_tier_for_node(&self, node_id: &str) -> Option<TransportTier> {
        self.links
            .iter()
            .find(|l| l.node_id == node_id && l.is_active_route)
            .map(|l| l.tier)
    }

    /// Trigger cascading failover for a node when primary transport drops.
    pub fn failover_next_tier(&mut self, node_id: &str) -> Option<TransportTier> {
        let current_active_idx = self
            .links
            .iter()
            .position(|l| l.node_id == node_id && l.is_active_route)?;

        // Mark current link offline
        self.links[current_active_idx].status = TransportStatus::Offline;
        self.links[current_active_idx].is_active_route = false;

        // Find next standby link for this node
        if let Some(next_idx) = self
            .links
            .iter()
            .position(|l| l.node_id == node_id && l.status != TransportStatus::Offline)
        {
            self.links[next_idx].status = TransportStatus::Active;
            self.links[next_idx].is_active_route = true;
            Some(self.links[next_idx].tier)
        } else {
            None
        }
    }

    /// Record a probe result and update link status.
    pub fn record_probe(&mut self, node_id: &str, tier: TransportTier, latency_ms: f64, success: bool) {
        if let Some(link) = self
            .links
            .iter_mut()
            .find(|l| l.node_id == node_id && l.tier == tier)
        {
            if success {
                link.status = if link.is_active_route {
                    TransportStatus::Active
                } else {
                    TransportStatus::Standby
                };
                link.latency_ms = latency_ms;
                link.consecutive_failures = 0;
                link.loss_pct = (link.loss_pct * 0.8).max(0.0);
            } else {
                link.consecutive_failures += 1;
                link.loss_pct = (link.loss_pct * 0.8 + 20.0).min(100.0);
                if link.consecutive_failures >= 3 {
                    link.status = TransportStatus::Offline;
                    if link.is_active_route && self.auto_failover_enabled {
                        link.is_active_route = false;
                        let current_tier = link.tier;
                        if let Some(next) = self
                            .links
                            .iter_mut()
                            .find(|l| l.node_id == node_id && l.tier != current_tier && l.status != TransportStatus::Offline)
                        {
                            next.status = TransportStatus::Active;
                            next.is_active_route = true;
                        }
                    }
                } else {
                    link.status = TransportStatus::Degraded;
                }
            }
        }
    }
}
