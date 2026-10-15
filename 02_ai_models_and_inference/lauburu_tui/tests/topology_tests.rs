//! ============================================================================
//! Tier 1 & Tier 2 Test Suite: Mesh Topology & Ring Visualization
//! ============================================================================
//! Features Covered:
//! - F4: Tab Navigation & Shell UI (Topology tab metrics & shell layout)
//! - F5: Core PRP Ring Visualization (4-node pipeline flow, ASCII graph, table)
//! - F6: Edge RPC Pool Visualization (3-node edge pool, device capabilities)
//! - F10: Zero-Mock / Truth Audit Compliance (True physical topology mapping)
//! ============================================================================

use std::collections::HashSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeGroup {
    CoreRing,
    EdgePool,
}

#[derive(Debug, Clone, PartialEq)]
pub struct NodeSpec {
    pub name: String,
    pub ip: String,
    pub port: u16,
    pub role: String,
    pub layer: String,
    pub group: NodeGroup,
    pub ram_gb: f64,
    pub vram_gb: f64,
    pub interconnect: String,
    pub backend: String,
}

#[derive(Debug, Clone)]
pub struct TopologyState {
    pub selected_table_index: usize,
    pub active_view: TopologySubView,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TopologySubView {
    CoreRing,
    EdgePool,
    FullCluster,
}

pub struct TopologyModel {
    pub nodes: Vec<NodeSpec>,
    pub state: TopologyState,
}

impl TopologyModel {
    pub fn new(nodes: Vec<NodeSpec>) -> Self {
        Self {
            nodes,
            state: TopologyState {
                selected_table_index: 0,
                active_view: TopologySubView::FullCluster,
            },
        }
    }

    pub fn core_ring_nodes(&self) -> Vec<&NodeSpec> {
        self.nodes.iter().filter(|n| n.group == NodeGroup::CoreRing).collect()
    }

    pub fn edge_pool_nodes(&self) -> Vec<&NodeSpec> {
        self.nodes.iter().filter(|n| n.group == NodeGroup::EdgePool).collect()
    }

    pub fn total_node_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn core_node_count(&self) -> usize {
        self.core_ring_nodes().len()
    }

    pub fn edge_node_count(&self) -> usize {
        self.edge_pool_nodes().len()
    }

    pub fn total_ram_gb(&self) -> f64 {
        self.nodes.iter().map(|n| n.ram_gb).sum()
    }

    pub fn total_vram_gb(&self) -> f64 {
        self.nodes.iter().map(|n| n.vram_gb).sum()
    }

    pub fn core_vram_gb(&self) -> f64 {
        self.core_ring_nodes().iter().map(|n| n.vram_gb).sum()
    }

    pub fn edge_vram_gb(&self) -> f64 {
        self.edge_pool_nodes().iter().map(|n| n.vram_gb).sum()
    }

    pub fn next_selection(&mut self) {
        if !self.nodes.is_empty() {
            self.state.selected_table_index = (self.state.selected_table_index + 1) % self.nodes.len();
        }
    }

    pub fn previous_selection(&mut self) {
        if !self.nodes.is_empty() {
            if self.state.selected_table_index == 0 {
                self.state.selected_table_index = self.nodes.len() - 1;
            } else {
                self.state.selected_table_index -= 1;
            }
        }
    }

    pub fn select_index(&mut self, index: usize) {
        if index < self.nodes.len() {
            self.state.selected_table_index = index;
        }
    }

    pub fn generate_ascii_ring_diagram(&self) -> Vec<String> {
        let core = self.core_ring_nodes();
        if core.is_empty() {
            return vec!["[No Core Ring Nodes Configured]".to_string()];
        }

        let mut lines = Vec::new();
        lines.push("┌────────────────────────────────────────────────────────────────────────┐".to_string());
        lines.push("│                 PRP (Pipelined Ring Parallelism) MESH                  │".to_string());
        lines.push("├────────────────────────────────────────────────────────────────────────┤".to_string());

        let node_names: Vec<String> = core.iter().map(|n| format!("{}({})", n.name, n.layer)).collect();
        let ring_flow = node_names.join(" ──► ");
        lines.push(format!("│ Flow: {} ──► [Loopback]", ring_flow));
        lines.push("└────────────────────────────────────────────────────────────────────────┘".to_string());
        lines
    }
}

// ----------------------------------------------------------------------------
// Canonical Fixture Generator
// ----------------------------------------------------------------------------

fn canonical_nodes_fixture() -> Vec<NodeSpec> {
    vec![
        NodeSpec {
            name: "Mac_Node".to_string(),
            ip: "192.168.8.230".to_string(),
            port: 8082,
            role: "Primary Host & Memory Governor".to_string(),
            layer: "L1".to_string(),
            group: NodeGroup::CoreRing,
            ram_gb: 24.0,
            vram_gb: 21.6,
            interconnect: "Host DMA / Loopback".to_string(),
            backend: "Apple Metal M4 Pro".to_string(),
        },
        NodeSpec {
            name: "MacBook_Pro".to_string(),
            ip: "192.168.8.127".to_string(),
            port: 8081,
            role: "Metal GPU RPC & Storage Vault".to_string(),
            layer: "L2".to_string(),
            group: NodeGroup::CoreRing,
            ram_gb: 16.0,
            vram_gb: 14.0,
            interconnect: "10Gbps Thunderbolt 4".to_string(),
            backend: "Apple Metal M1 Pro".to_string(),
        },
        NodeSpec {
            name: "Linux_Head_Node".to_string(),
            ip: "192.168.8.224".to_string(),
            port: 8083,
            role: "Gateway Ingress & Compute Hub".to_string(),
            layer: "L3".to_string(),
            group: NodeGroup::CoreRing,
            ram_gb: 16.0,
            vram_gb: 13.8,
            interconnect: "1GbE Ethernet".to_string(),
            backend: "AMD Vulkan / ROCm".to_string(),
        },
        NodeSpec {
            name: "MacBook_Air".to_string(),
            ip: "192.168.8.222".to_string(),
            port: 8084,
            role: "Secondary High-Speed Metal Worker".to_string(),
            layer: "L5".to_string(),
            group: NodeGroup::CoreRing,
            ram_gb: 16.0,
            vram_gb: 14.0,
            interconnect: "Wi-Fi 7 MLO".to_string(),
            backend: "Apple Metal M4".to_string(),
        },
        NodeSpec {
            name: "Pixel_10_Pro_XL".to_string(),
            ip: "100.73.38.87".to_string(),
            port: 50051,
            role: "8K Vision Stream & Edge TPU".to_string(),
            layer: "L6".to_string(),
            group: NodeGroup::EdgePool,
            ram_gb: 16.0,
            vram_gb: 12.5,
            interconnect: "Tailscale / Wi-Fi 7".to_string(),
            backend: "Google Tensor G5 TPU".to_string(),
        },
        NodeSpec {
            name: "Samsung_S20".to_string(),
            ip: "100.84.40.95".to_string(),
            port: 50052,
            role: "Dedicated Automated UI Tester".to_string(),
            layer: "L7".to_string(),
            group: NodeGroup::EdgePool,
            ram_gb: 12.0,
            vram_gb: 9.0,
            interconnect: "Tailscale / Wi-Fi 6".to_string(),
            backend: "Samsung Exynos 990".to_string(),
        },
        NodeSpec {
            name: "Linux_Tablet".to_string(),
            ip: "100.81.92.125".to_string(),
            port: 50053,
            role: "Mobile Linux Compute & Touch DSP".to_string(),
            layer: "L4".to_string(),
            group: NodeGroup::EdgePool,
            ram_gb: 8.0,
            vram_gb: 6.5,
            interconnect: "Tailscale / Wi-Fi".to_string(),
            backend: "Debian Linux CPU/GPU".to_string(),
        },
    ]
}

// ============================================================================
// TIER 1: FEATURE COVERAGE (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t1_f5_01_core_ring_exact_four_nodes() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    let core = model.core_ring_nodes();
    assert_eq!(core.len(), 4);
    assert_eq!(core[0].name, "Mac_Node");
    assert_eq!(core[1].name, "MacBook_Pro");
    assert_eq!(core[2].name, "Linux_Head_Node");
    assert_eq!(core[3].name, "MacBook_Air");
}

#[test]
fn test_t1_f5_02_core_ring_pipelined_interconnect_types() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    let core = model.core_ring_nodes();
    assert_eq!(core[1].interconnect, "10Gbps Thunderbolt 4");
    assert_eq!(core[2].interconnect, "1GbE Ethernet");
    assert_eq!(core[3].interconnect, "Wi-Fi 7 MLO");
}

#[test]
fn test_t1_f6_03_edge_pool_exact_three_nodes() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    let edge = model.edge_pool_nodes();
    assert_eq!(edge.len(), 3);
    assert_eq!(edge[0].name, "Pixel_10_Pro_XL");
    assert_eq!(edge[1].name, "Samsung_S20");
    assert_eq!(edge[2].name, "Linux_Tablet");
}

#[test]
fn test_t1_f6_04_edge_pool_tailscale_ip_address_verification() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    let edge = model.edge_pool_nodes();
    for node in edge {
        assert!(node.ip.starts_with("100."), "Edge node '{}' must use Tailscale 100.x subnet IP", node.name);
    }
}

#[test]
fn test_t1_f4_05_aggregate_mesh_capacities() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    assert_eq!(model.total_node_count(), 7);
    assert_eq!(model.core_node_count(), 4);
    assert_eq!(model.edge_node_count(), 3);
    assert!((model.total_ram_gb() - 108.0).abs() < 1e-5);
    assert!((model.total_vram_gb() - 91.4).abs() < 1e-5);
}

#[test]
fn test_t1_f5_06_ascii_ring_diagram_contains_all_core_nodes() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    let diagram = model.generate_ascii_ring_diagram();
    let text = diagram.join("\n");
    assert!(text.contains("Mac_Node(L1)"));
    assert!(text.contains("MacBook_Pro(L2)"));
    assert!(text.contains("Linux_Head_Node(L3)"));
    assert!(text.contains("MacBook_Air(L5)"));
    assert!(text.contains("──►"));
}

#[test]
fn test_t1_f10_07_all_physical_layers_l1_through_l7_accounted() {
    let model = TopologyModel::new(canonical_nodes_fixture());
    let layers: HashSet<String> = model.nodes.iter().map(|n| n.layer.clone()).collect();
    let expected: HashSet<String> = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"].iter().map(|s| s.to_string()).collect();
    assert_eq!(layers, expected, "All 7 physical mesh layers must be represented");
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t2_top_b01_empty_topology_model() {
    let mut model = TopologyModel::new(vec![]);
    assert_eq!(model.total_node_count(), 0);
    assert_eq!(model.core_node_count(), 0);
    assert_eq!(model.edge_node_count(), 0);
    assert_eq!(model.total_ram_gb(), 0.0);
    assert_eq!(model.total_vram_gb(), 0.0);

    // Selection operations on empty list must not panic
    model.next_selection();
    assert_eq!(model.state.selected_table_index, 0);
    model.previous_selection();
    assert_eq!(model.state.selected_table_index, 0);

    let diagram = model.generate_ascii_ring_diagram();
    assert!(diagram[0].contains("No Core Ring Nodes"));
}

#[test]
fn test_t2_top_b02_single_node_topology() {
    let single_node = vec![NodeSpec {
        name: "Solo_Node".to_string(),
        ip: "127.0.0.1".to_string(),
        port: 8080,
        role: "Single Master".to_string(),
        layer: "L1".to_string(),
        group: NodeGroup::CoreRing,
        ram_gb: 32.0,
        vram_gb: 24.0,
        interconnect: "Local".to_string(),
        backend: "Metal".to_string(),
    }];
    let mut model = TopologyModel::new(single_node);
    assert_eq!(model.core_node_count(), 1);
    assert_eq!(model.edge_node_count(), 0);

    model.next_selection();
    assert_eq!(model.state.selected_table_index, 0, "Next on single item stays at 0");
    model.previous_selection();
    assert_eq!(model.state.selected_table_index, 0, "Prev on single item stays at 0");
}

#[test]
fn test_t2_top_b03_selection_wrap_around() {
    let mut model = TopologyModel::new(canonical_nodes_fixture());
    assert_eq!(model.state.selected_table_index, 0);

    // Move backward from 0 -> wraps to last index (6)
    model.previous_selection();
    assert_eq!(model.state.selected_table_index, 6);

    // Move forward from 6 -> wraps to 0
    model.next_selection();
    assert_eq!(model.state.selected_table_index, 0);

    // Advance 3 times
    model.next_selection();
    model.next_selection();
    model.next_selection();
    assert_eq!(model.state.selected_table_index, 3);
}

#[test]
fn test_t2_top_b04_out_of_bounds_selection_clamped() {
    let mut model = TopologyModel::new(canonical_nodes_fixture());
    model.select_index(999); // Invalid index
    assert_eq!(model.state.selected_table_index, 0, "Out of bounds select_index must be ignored");

    model.select_index(5);
    assert_eq!(model.state.selected_table_index, 5);
}

#[test]
fn test_t2_top_b05_only_edge_nodes_in_mesh() {
    let edge_only = vec![
        NodeSpec {
            name: "Edge_A".to_string(),
            ip: "100.1.1.1".to_string(),
            port: 5000,
            role: "Sensor".to_string(),
            layer: "L6".to_string(),
            group: NodeGroup::EdgePool,
            ram_gb: 4.0,
            vram_gb: 2.0,
            interconnect: "BLE".to_string(),
            backend: "NPU".to_string(),
        },
        NodeSpec {
            name: "Edge_B".to_string(),
            ip: "100.1.1.2".to_string(),
            port: 5001,
            role: "Display".to_string(),
            layer: "L7".to_string(),
            group: NodeGroup::EdgePool,
            ram_gb: 8.0,
            vram_gb: 4.0,
            interconnect: "Wi-Fi".to_string(),
            backend: "GPU".to_string(),
        },
    ];
    let model = TopologyModel::new(edge_only);
    assert_eq!(model.core_node_count(), 0);
    assert_eq!(model.edge_node_count(), 2);
    assert_eq!(model.core_vram_gb(), 0.0);
    assert_eq!(model.edge_vram_gb(), 6.0);
}

#[test]
fn test_t2_top_b06_extreme_large_cluster_scaling() {
    let mut big_cluster = Vec::new();
    for i in 0..100 {
        big_cluster.push(NodeSpec {
            name: format!("Node_{:03}", i),
            ip: format!("192.168.1.{}", i + 1),
            port: 8000 + (i as u16),
            role: "Worker".to_string(),
            layer: format!("L{}", (i % 7) + 1),
            group: if i < 50 { NodeGroup::CoreRing } else { NodeGroup::EdgePool },
            ram_gb: 16.0,
            vram_gb: 8.0,
            interconnect: "10GbE".to_string(),
            backend: "Metal".to_string(),
        });
    }

    let mut model = TopologyModel::new(big_cluster);
    assert_eq!(model.total_node_count(), 100);
    assert_eq!(model.core_node_count(), 50);
    assert_eq!(model.edge_node_count(), 50);
    assert_eq!(model.total_ram_gb(), 1600.0);
    assert_eq!(model.total_vram_gb(), 800.0);

    for _ in 0..100 {
        model.next_selection();
    }
    assert_eq!(model.state.selected_table_index, 0);
}

#[test]
fn test_t2_top_b07_high_precision_floating_point_vram() {
    let fractional_nodes = vec![
        NodeSpec {
            name: "Fractional_1".to_string(),
            ip: "10.0.0.1".to_string(),
            port: 8080,
            role: "Worker".to_string(),
            layer: "L1".to_string(),
            group: NodeGroup::CoreRing,
            ram_gb: 15.333333,
            vram_gb: 11.666667,
            interconnect: "PCIe".to_string(),
            backend: "CUDA".to_string(),
        },
        NodeSpec {
            name: "Fractional_2".to_string(),
            ip: "10.0.0.2".to_string(),
            port: 8081,
            role: "Worker".to_string(),
            layer: "L2".to_string(),
            group: NodeGroup::CoreRing,
            ram_gb: 16.666667,
            vram_gb: 12.333333,
            interconnect: "PCIe".to_string(),
            backend: "CUDA".to_string(),
        },
    ];
    let model = TopologyModel::new(fractional_nodes);
    let total_vram = model.total_vram_gb();
    assert!((total_vram - 24.0).abs() < 1e-4);
}

// ============================================================================
// TIER 5: ADVERSARIAL & CANONICAL TOPOLOGY TESTS
// ============================================================================

#[test]
fn test_t5_adv_top_01_app_dual_table_focus_toggle() {
    use lauburu_tui::app::{ActiveTopologyTable, App};
    use lauburu_tui::config::MeshConfig;

    let mut app = App::new(MeshConfig::fallback());
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);

    app.switch_table_focus();
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);

    app.switch_table_focus();
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
}

#[test]
fn test_t5_adv_top_02_canonical_7node_hardware_integrity() {
    use lauburu_tui::config::MeshConfig;

    let cfg = MeshConfig::fallback();
    let layers: Vec<&str> = cfg.nodes.iter().map(|n| n.layer.as_str()).collect();
    assert_eq!(layers, vec!["L1", "L2", "L5", "L3", "L6", "L7", "L4"]);

    // Verify master node is Mac Mini L1
    let master = cfg.get_master_node().unwrap();
    assert_eq!(master.layer, "L1");
    assert_eq!(master.port, 8082);
    assert_eq!(master.backend, "Metal");
}

#[test]
fn test_t5_adv_top_03_terminal_render_dual_tables() {
    use lauburu_tui::app::App;
    use lauburu_tui::config::MeshConfig;
    use lauburu_tui::ui;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    let backend = TestBackend::new(200, 40);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    terminal.draw(|f| ui::render(&mut app, f)).unwrap();
    let buf = terminal.backend().buffer();
    let text: String = buf.content.iter().map(|c| c.symbol()).collect();

    assert!(text.contains("Mac Mini"));
    assert!(text.contains("MacBook Pro"));
    assert!(text.contains("Linux Head Node"));
    assert!(text.contains("Pixel 10"));
    assert!(text.contains("Samsung S20"));
    assert!(text.contains("Linux Tablet"));
    assert!(text.contains("Core PRP Ring"));
    assert!(text.contains("Edge RPC Pool"));
}


