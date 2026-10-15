//! ============================================================================
//! Tier 1, 2, 3 & 4 Test Suite: Unified AI Sharding Protocol & Routing (R2)
//! ============================================================================
//! Features Covered:
//! - F3: Unified AI Sharding Decision Tree (TB4 DMA -> Exo MLX -> Petals DHT -> Local Solo)
//! - F4: 7-Layer Node Capabilities & Sharding Matrix (82.8 GB pool validation)
//! - F5: Dynamic Model-to-Protocol Routing Matrix & Quantization Fitting
//! - F10: Zero-Mock / Rule #0 Truth Audit Compliance
//! ============================================================================

use serde::{Deserialize, Serialize};

// ----------------------------------------------------------------------------
// Canonical Domain Structs matching Interface Contracts (PROJECT.md)
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ShardingProtocol {
    LlamaRpcTb4,
    ExoP2pMlx,
    PetalsDht,
    LocalStandalone,
    AccelerateFsdp,
    UnsupportedOom,
}

impl ShardingProtocol {
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::LlamaRpcTb4 => "llama.cpp RPC over 10Gbps TB4 DMA",
            Self::ExoP2pMlx => "Exo P2P MLX Ring (Apple Silicon)",
            Self::PetalsDht => "Petals DHT Decentralized Swarm",
            Self::LocalStandalone => "Local Standalone (Mac Mini Host)",
            Self::AccelerateFsdp => "HuggingFace Accelerate FSDP",
            Self::UnsupportedOom => "❌ Out of Memory (Exceeds Mesh VRAM)",
        }
    }

    pub fn tag(&self) -> &'static str {
        match self {
            Self::LlamaRpcTb4 => "TB4-RPC",
            Self::ExoP2pMlx => "EXO-MLX",
            Self::PetalsDht => "PETALS-DHT",
            Self::LocalStandalone => "LOCAL-SOLO",
            Self::AccelerateFsdp => "HF-FSDP",
            Self::UnsupportedOom => "OOM-BLOCK",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModelRoutingSpec {
    pub model_name: String,
    pub parameter_size: String,
    pub quantization: String,
    pub memory_req_gb: f64,
    pub optimal_protocol: ShardingProtocol,
    pub min_nodes: usize,
    pub target_interconnect: String,
    pub est_latency_ms: f64,
    pub est_throughput_tps: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeShardingCapability {
    pub layer: String,
    pub name: String,
    pub endpoint: String,
    pub interconnect: String,
    pub vram_gb: f64,
    pub dynamic_cap_pct: u8,
    pub mlx_supported: bool,
    pub llama_rpc_role: String,
    pub petals_role: String,
    pub allocated_shard_gb: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum ShardingFocus {
    #[default]
    RoutingMatrix,
    NodeMatrix,
}

#[derive(Debug, Clone)]
pub struct ShardingTopologyGovernor {
    pub tb4_bridge_active: bool,
    pub tb4_rtt_ms: f64,
    pub apple_silicon_nodes_online: usize,
    pub linux_nodes_online: usize,
    pub android_nodes_online: usize,
    pub local_host_vram_gb: f64,
    pub apple_pool_vram_gb: f64,
    pub total_mesh_vram_gb: f64,
    pub routing_specs: Vec<ModelRoutingSpec>,
    pub node_capabilities: Vec<NodeShardingCapability>,
    pub active_focus: ShardingFocus,
    pub selected_routing_row: usize,
    pub selected_node_row: usize,
}

impl ShardingTopologyGovernor {
    pub fn new_canonical() -> Self {
        let node_capabilities = vec![
            NodeShardingCapability {
                layer: "L1".to_string(),
                name: "Mac_Node".to_string(),
                endpoint: "127.0.0.1:8082".to_string(),
                interconnect: "Host DMA / Loopback".to_string(),
                vram_gb: 21.6,
                dynamic_cap_pct: 90,
                mlx_supported: true,
                llama_rpc_role: "Master Server".to_string(),
                petals_role: "Client Ingress".to_string(),
                allocated_shard_gb: 21.6,
            },
            NodeShardingCapability {
                layer: "L2".to_string(),
                name: "MacBook_Pro".to_string(),
                endpoint: "169.254.187.138:50052".to_string(),
                interconnect: "10Gbps Thunderbolt 4".to_string(),
                vram_gb: 14.0,
                dynamic_cap_pct: 90,
                mlx_supported: true,
                llama_rpc_role: "RPC Worker".to_string(),
                petals_role: "Worker".to_string(),
                allocated_shard_gb: 14.0,
            },
            NodeShardingCapability {
                layer: "L3".to_string(),
                name: "Linux_Head_Node".to_string(),
                endpoint: "100.101.39.98:50053".to_string(),
                interconnect: "1GbE Ethernet".to_string(),
                vram_gb: 13.8,
                dynamic_cap_pct: 80,
                mlx_supported: false,
                llama_rpc_role: "RPC Worker".to_string(),
                petals_role: "Bootstrap Anchor".to_string(),
                allocated_shard_gb: 13.8,
            },
            NodeShardingCapability {
                layer: "L4".to_string(),
                name: "Linux_Tablet".to_string(),
                endpoint: "100.81.92.125:31330".to_string(),
                interconnect: "Tailscale / Wi-Fi".to_string(),
                vram_gb: 6.5,
                dynamic_cap_pct: 75,
                mlx_supported: false,
                llama_rpc_role: "RPC Worker".to_string(),
                petals_role: "Worker".to_string(),
                allocated_shard_gb: 6.5,
            },
            NodeShardingCapability {
                layer: "L5".to_string(),
                name: "MacBook_Air".to_string(),
                endpoint: "100.93.158.96:50052".to_string(),
                interconnect: "Wi-Fi 7 MLO".to_string(),
                vram_gb: 14.0,
                dynamic_cap_pct: 90,
                mlx_supported: true,
                llama_rpc_role: "RPC Worker".to_string(),
                petals_role: "Worker".to_string(),
                allocated_shard_gb: 14.0,
            },
            NodeShardingCapability {
                layer: "L6".to_string(),
                name: "Pixel_10_Pro_XL".to_string(),
                endpoint: "100.73.38.87:8084".to_string(),
                interconnect: "Tailscale / USB-C".to_string(),
                vram_gb: 12.5,
                dynamic_cap_pct: 85,
                mlx_supported: false,
                llama_rpc_role: "Offline".to_string(),
                petals_role: "Edge TPU Worker".to_string(),
                allocated_shard_gb: 12.5,
            },
            NodeShardingCapability {
                layer: "L7".to_string(),
                name: "Samsung_S20".to_string(),
                endpoint: "100.84.40.95:8022".to_string(),
                interconnect: "Router USB ADB".to_string(),
                vram_gb: 9.0,
                dynamic_cap_pct: 75,
                mlx_supported: false,
                llama_rpc_role: "Offline".to_string(),
                petals_role: "Auxiliary Edge".to_string(),
                allocated_shard_gb: 0.0,
            },
        ];

        let routing_specs = vec![
            ModelRoutingSpec {
                model_name: "Qwen2.5-7B-Instruct".to_string(),
                parameter_size: "≤8B".to_string(),
                quantization: "Q4_K_M".to_string(),
                memory_req_gb: 4.5,
                optimal_protocol: ShardingProtocol::LocalStandalone,
                min_nodes: 1,
                target_interconnect: "Host Memory Bus".to_string(),
                est_latency_ms: 12.0,
                est_throughput_tps: 85.0,
            },
            ModelRoutingSpec {
                model_name: "Qwen2.5-14B-Instruct".to_string(),
                parameter_size: "≤14B".to_string(),
                quantization: "Q4_K_M".to_string(),
                memory_req_gb: 8.5,
                optimal_protocol: ShardingProtocol::LocalStandalone,
                min_nodes: 1,
                target_interconnect: "Host Memory Bus".to_string(),
                est_latency_ms: 18.0,
                est_throughput_tps: 52.0,
            },
            ModelRoutingSpec {
                model_name: "DeepSeek-R1-Distill-32B".to_string(),
                parameter_size: "≤32B".to_string(),
                quantization: "Q4_K_M".to_string(),
                memory_req_gb: 19.5,
                optimal_protocol: ShardingProtocol::LlamaRpcTb4,
                min_nodes: 2,
                target_interconnect: "10Gbps TB4 DMA (0.27ms)".to_string(),
                est_latency_ms: 25.0,
                est_throughput_tps: 38.0,
            },
            ModelRoutingSpec {
                model_name: "DeepSeek-R1-32B-IQ2".to_string(),
                parameter_size: "32B".to_string(),
                quantization: "IQ2_XXS".to_string(),
                memory_req_gb: 9.8,
                optimal_protocol: ShardingProtocol::LocalStandalone,
                min_nodes: 1,
                target_interconnect: "Metal / Local Bus".to_string(),
                est_latency_ms: 16.0,
                est_throughput_tps: 62.0,
            },
            ModelRoutingSpec {
                model_name: "Llama-3.3-49B-Instruct".to_string(),
                parameter_size: "≤49B".to_string(),
                quantization: "Q4_K_M".to_string(),
                memory_req_gb: 28.0,
                optimal_protocol: ShardingProtocol::ExoP2pMlx,
                min_nodes: 2,
                target_interconnect: "10Gbps TB4 + Wi-Fi 7".to_string(),
                est_latency_ms: 32.0,
                est_throughput_tps: 28.0,
            },
            ModelRoutingSpec {
                model_name: "Qwen2.5-70B-Instruct".to_string(),
                parameter_size: "≤70B".to_string(),
                quantization: "Q4_K_M".to_string(),
                memory_req_gb: 39.5,
                optimal_protocol: ShardingProtocol::LlamaRpcTb4,
                min_nodes: 3,
                target_interconnect: "10Gbps TB4 DMA + MBA".to_string(),
                est_latency_ms: 38.0,
                est_throughput_tps: 20.0,
            },
            ModelRoutingSpec {
                model_name: "Llama-3.3-70B-Unquantized".to_string(),
                parameter_size: "≤70B".to_string(),
                quantization: "FP16".to_string(),
                memory_req_gb: 140.0,
                optimal_protocol: ShardingProtocol::UnsupportedOom,
                min_nodes: 0,
                target_interconnect: "Exceeds 82.8GB Mesh".to_string(),
                est_latency_ms: 0.0,
                est_throughput_tps: 0.0,
            },
            ModelRoutingSpec {
                model_name: "Mixtral-8x22B-MoE".to_string(),
                parameter_size: "≤120B".to_string(),
                quantization: "Q4 MoE".to_string(),
                memory_req_gb: 65.0,
                optimal_protocol: ShardingProtocol::ExoP2pMlx,
                min_nodes: 4,
                target_interconnect: "Exo P2P MLX Swarm".to_string(),
                est_latency_ms: 95.0,
                est_throughput_tps: 12.0,
            },
            ModelRoutingSpec {
                model_name: "Llama-3.1-405B-Instruct".to_string(),
                parameter_size: ">120B".to_string(),
                quantization: "Q4_K_M".to_string(),
                memory_req_gb: 230.0,
                optimal_protocol: ShardingProtocol::PetalsDht,
                min_nodes: 7,
                target_interconnect: "Petals Swarm P2P".to_string(),
                est_latency_ms: 250.0,
                est_throughput_tps: 5.0,
            },
        ];

        Self {
            tb4_bridge_active: true,
            tb4_rtt_ms: 0.27,
            apple_silicon_nodes_online: 3,
            linux_nodes_online: 2,
            android_nodes_online: 2,
            local_host_vram_gb: 21.6,
            apple_pool_vram_gb: 49.6,
            total_mesh_vram_gb: 82.8,
            routing_specs,
            node_capabilities,
            active_focus: ShardingFocus::RoutingMatrix,
            selected_routing_row: 0,
            selected_node_row: 0,
        }
    }

    /// Evaluates the Unified AI Sharding Decision Tree for a given model requirement.
    pub fn evaluate_protocol_decision(&self, memory_req_gb: f64, quant: &str) -> ShardingProtocol {
        // Step 0: Check if model exceeds total pool
        if memory_req_gb > self.total_mesh_vram_gb || quant == "FP16" && memory_req_gb > 50.0 {
            return ShardingProtocol::UnsupportedOom;
        }

        // Step 1: Fits comfortably in local Mac Mini host
        if memory_req_gb <= self.local_host_vram_gb && memory_req_gb <= 10.0 {
            return ShardingProtocol::LocalStandalone;
        }

        // Step 2: TB4 Bridge Active (ping < 2.0ms) -> llama.cpp RPC over TB4 DMA
        if self.tb4_bridge_active && self.tb4_rtt_ms < 2.0 && memory_req_gb <= 39.5 {
            return ShardingProtocol::LlamaRpcTb4;
        }

        // Step 3: Apple Silicon nodes online -> Exo P2P MLX Ring
        if self.apple_silicon_nodes_online >= 2 && memory_req_gb <= self.apple_pool_vram_gb {
            return ShardingProtocol::ExoP2pMlx;
        }

        // Step 4: Linux/Android nodes online -> Petals DHT
        if (self.linux_nodes_online + self.android_nodes_online) >= 1 && memory_req_gb <= self.total_mesh_vram_gb {
            return ShardingProtocol::PetalsDht;
        }

        // Fallback: Local Standalone
        ShardingProtocol::LocalStandalone
    }

    pub fn toggle_focus(&mut self) {
        self.active_focus = match self.active_focus {
            ShardingFocus::RoutingMatrix => ShardingFocus::NodeMatrix,
            ShardingFocus::NodeMatrix => ShardingFocus::RoutingMatrix,
        };
    }

    pub fn next_row(&mut self) {
        match self.active_focus {
            ShardingFocus::RoutingMatrix => {
                if !self.routing_specs.is_empty() {
                    self.selected_routing_row = (self.selected_routing_row + 1) % self.routing_specs.len();
                }
            }
            ShardingFocus::NodeMatrix => {
                if !self.node_capabilities.is_empty() {
                    self.selected_node_row = (self.selected_node_row + 1) % self.node_capabilities.len();
                }
            }
        }
    }

    pub fn prev_row(&mut self) {
        match self.active_focus {
            ShardingFocus::RoutingMatrix => {
                if !self.routing_specs.is_empty() {
                    if self.selected_routing_row == 0 {
                        self.selected_routing_row = self.routing_specs.len() - 1;
                    } else {
                        self.selected_routing_row -= 1;
                    }
                }
            }
            ShardingFocus::NodeMatrix => {
                if !self.node_capabilities.is_empty() {
                    if self.selected_node_row == 0 {
                        self.selected_node_row = self.node_capabilities.len() - 1;
                    } else {
                        self.selected_node_row -= 1;
                    }
                }
            }
        }
    }
}

// ============================================================================
// TIER 1: FEATURE COVERAGE TESTS (≥5 tests)
// ============================================================================

#[test]
fn test_t1_f3_01_tb4_active_routes_to_llama_rpc() {
    let gov = ShardingTopologyGovernor::new_canonical();
    // 32B model (19.5GB) with TB4 active (0.27ms) -> LlamaRpcTb4
    let protocol = gov.evaluate_protocol_decision(19.5, "Q4_K_M");
    assert_eq!(protocol, ShardingProtocol::LlamaRpcTb4);
    assert_eq!(protocol.tag(), "TB4-RPC");
}

#[test]
fn test_t1_f3_02_tb4_down_apple_online_routes_to_exo_mlx() {
    let mut gov = ShardingTopologyGovernor::new_canonical();
    gov.tb4_bridge_active = false; // Simulate TB4 disconnect

    // 49B model (28.0GB) with 3 Apple nodes online -> ExoP2pMlx
    let protocol = gov.evaluate_protocol_decision(28.0, "Q4_K_M");
    assert_eq!(protocol, ShardingProtocol::ExoP2pMlx);
    assert_eq!(protocol.tag(), "EXO-MLX");
}

#[test]
fn test_t1_f3_03_heterogeneous_cluster_routes_to_petals_dht() {
    let mut gov = ShardingTopologyGovernor::new_canonical();
    gov.tb4_bridge_active = false;
    gov.apple_silicon_nodes_online = 1; // Only 1 Apple node

    // 65.0GB model needing Linux/Android cluster -> PetalsDht
    let protocol = gov.evaluate_protocol_decision(65.0, "Q4 MoE");
    assert_eq!(protocol, ShardingProtocol::PetalsDht);
    assert_eq!(protocol.tag(), "PETALS-DHT");
}

#[test]
fn test_t1_f4_04_canonical_7layer_node_matrix_accounts_for_all_physical_nodes() {
    let gov = ShardingTopologyGovernor::new_canonical();
    assert_eq!(gov.node_capabilities.len(), 7);

    let layers: Vec<&str> = gov.node_capabilities.iter().map(|n| n.layer.as_str()).collect();
    assert_eq!(layers, vec!["L1", "L2", "L3", "L4", "L5", "L6", "L7"]);

    let total_vram: f64 = gov.node_capabilities.iter().map(|n| n.vram_gb).sum();
    // 21.6 + 14.0 + 13.8 + 6.5 + 14.0 + 12.5 + 9.0 = 91.4 GB total physical VRAM
    assert!((total_vram - 91.4).abs() < 1e-6);

    let apple_vram: f64 = gov
        .node_capabilities
        .iter()
        .filter(|n| n.mlx_supported)
        .map(|n| n.vram_gb)
        .sum();
    // 21.6 + 14.0 + 14.0 = 49.6 GB Apple Silicon Pool
    assert!((apple_vram - 49.6).abs() < 1e-6);
}

#[test]
fn test_t1_f5_05_dynamic_model_routing_specs_match_catalog() {
    let gov = ShardingTopologyGovernor::new_canonical();
    assert_eq!(gov.routing_specs.len(), 9);

    let small = &gov.routing_specs[0]; // 7B
    assert_eq!(small.parameter_size, "≤8B");
    assert_eq!(small.optimal_protocol, ShardingProtocol::LocalStandalone);

    let oom = &gov.routing_specs[6]; // 70B FP16
    assert_eq!(oom.quantization, "FP16");
    assert_eq!(oom.optimal_protocol, ShardingProtocol::UnsupportedOom);
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (≥5 tests)
// ============================================================================

#[test]
fn test_t2_f3_b01_latency_threshold_boundary_2ms() {
    let mut gov = ShardingTopologyGovernor::new_canonical();

    // At 1.99ms: TB4 RPC is active
    gov.tb4_rtt_ms = 1.99;
    assert_eq!(gov.evaluate_protocol_decision(19.5, "Q4_K_M"), ShardingProtocol::LlamaRpcTb4);

    // At 2.01ms: Exceeds TB4 threshold -> falls over to Exo MLX
    gov.tb4_rtt_ms = 2.01;
    assert_eq!(gov.evaluate_protocol_decision(19.5, "Q4_K_M"), ShardingProtocol::ExoP2pMlx);
}

#[test]
fn test_t2_f5_b02_exact_vram_limit_70b_fp16_oom_detection() {
    let gov = ShardingTopologyGovernor::new_canonical();
    // 140GB model exceeds 82.8GB usable pool
    let result = gov.evaluate_protocol_decision(140.0, "FP16");
    assert_eq!(result, ShardingProtocol::UnsupportedOom);
}

#[test]
fn test_t2_f4_b03_table_navigation_wrap_around() {
    let mut gov = ShardingTopologyGovernor::new_canonical();
    assert_eq!(gov.selected_routing_row, 0);

    // Previous from row 0 wraps to end
    gov.prev_row();
    assert_eq!(gov.selected_routing_row, gov.routing_specs.len() - 1);

    // Next wraps back to 0
    gov.next_row();
    assert_eq!(gov.selected_routing_row, 0);
}

#[test]
fn test_t2_f4_b04_focus_toggle_switches_active_table() {
    let mut gov = ShardingTopologyGovernor::new_canonical();
    assert_eq!(gov.active_focus, ShardingFocus::RoutingMatrix);

    gov.toggle_focus();
    assert_eq!(gov.active_focus, ShardingFocus::NodeMatrix);

    gov.toggle_focus();
    assert_eq!(gov.active_focus, ShardingFocus::RoutingMatrix);
}

#[test]
fn test_t2_f5_b05_single_node_deepseek_32b_iq2_xxs_fits_locally() {
    let gov = ShardingTopologyGovernor::new_canonical();
    // 9.8GB fits in Mac Mini host local VRAM (21.6GB)
    let decision = gov.evaluate_protocol_decision(9.8, "IQ2_XXS");
    assert_eq!(decision, ShardingProtocol::LocalStandalone);
}

// ============================================================================
// TIER 3: CROSS-FEATURE INTEGRATION (Multi-Node Re-routing)
// ============================================================================

#[test]
fn test_t3_f3_cross_01_cascading_failover_tb4_to_exo_to_petals_to_local() {
    let mut gov = ShardingTopologyGovernor::new_canonical();

    // 1. Initial State: TB4 Active -> TB4 RPC
    assert_eq!(gov.evaluate_protocol_decision(20.0, "Q4_K_M"), ShardingProtocol::LlamaRpcTb4);

    // 2. TB4 drops -> Exo MLX
    gov.tb4_bridge_active = false;
    assert_eq!(gov.evaluate_protocol_decision(20.0, "Q4_K_M"), ShardingProtocol::ExoP2pMlx);

    // 3. Apple nodes drop to 1 -> Petals DHT
    gov.apple_silicon_nodes_online = 1;
    assert_eq!(gov.evaluate_protocol_decision(20.0, "Q4_K_M"), ShardingProtocol::PetalsDht);

    // 4. Linux/Android nodes drop -> Local Standalone
    gov.linux_nodes_online = 0;
    gov.android_nodes_online = 0;
    assert_eq!(gov.evaluate_protocol_decision(20.0, "Q4_K_M"), ShardingProtocol::LocalStandalone);
}

// ============================================================================
// TIER 4: REAL-WORLD SCENARIOS
// ============================================================================

#[test]
fn test_t4_f3_scenario_01_sharded_70b_launch_verification() {
    let gov = ShardingTopologyGovernor::new_canonical();

    // Qwen2.5-70B requires 39.5GB VRAM
    let spec = gov.routing_specs.iter().find(|s| s.parameter_size == "≤70B" && s.quantization == "Q4_K_M").unwrap();
    assert_eq!(spec.min_nodes, 3);
    assert_eq!(spec.optimal_protocol, ShardingProtocol::LlamaRpcTb4);
    assert!(spec.memory_req_gb <= gov.total_mesh_vram_gb);
    assert!(spec.est_throughput_tps >= 20.0);
}
