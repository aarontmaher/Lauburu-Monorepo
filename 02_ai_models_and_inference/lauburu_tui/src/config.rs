use crate::errors::AppError;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

/// Classification of nodes within the Lauburu mesh topology.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeGroup {
    #[serde(alias = "core_prp", alias = "CoreRing", alias = "core")]
    CoreRing,
    #[serde(alias = "edge_rpc", alias = "EdgePool", alias = "edge")]
    EdgePool,
}

impl Default for NodeGroup {
    fn default() -> Self {
        NodeGroup::CoreRing
    }
}

impl fmt::Display for NodeGroup {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NodeGroup::CoreRing => write!(f, "Core PRP Ring"),
            NodeGroup::EdgePool => write!(f, "Edge RPC Pool"),
        }
    }
}

/// Global mesh metadata and default settings.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MeshMetadata {
    #[serde(default = "default_mesh_name")]
    pub name: String,
    #[serde(default = "default_mesh_version")]
    pub version: String,
    #[serde(default = "default_prima_endpoint")]
    pub prima_endpoint: String,
    #[serde(default = "default_master_url")]
    pub master_url: String,
    #[serde(default = "default_fallback_endpoint")]
    pub fallback_endpoint: String,
    #[serde(default = "default_model")]
    pub default_model: String,
    #[serde(default = "default_vram")]
    pub pooled_vram_gb: f64,
    #[serde(default = "default_ram")]
    pub pooled_ram_gb: f64,
    #[serde(default = "default_tick_rate")]
    pub tick_rate_ms: u64,
}

fn default_mesh_name() -> String {
    "Lauburu Heterogeneous AI Mesh".to_string()
}
fn default_mesh_version() -> String {
    "1.0.0".to_string()
}
fn default_prima_endpoint() -> String {
    "http://127.0.0.1:8082/v1/chat/completions".to_string()
}
fn default_master_url() -> String {
    "http://127.0.0.1:8082".to_string()
}
fn default_fallback_endpoint() -> String {
    "http://127.0.0.1:8083/v1/chat/completions".to_string()
}
fn default_model() -> String {
    "Huihui-Qwen3.8-27B-abliterated-UD-Q4_K_XL.gguf".to_string()
}
fn default_vram() -> f64 {
    82.8
}
fn default_ram() -> f64 {
    108.0
}
fn default_tick_rate() -> u64 {
    16
}

impl Default for MeshMetadata {
    fn default() -> Self {
        Self {
            name: default_mesh_name(),
            version: default_mesh_version(),
            prima_endpoint: default_prima_endpoint(),
            master_url: default_master_url(),
            fallback_endpoint: default_fallback_endpoint(),
            default_model: default_model(),
            pooled_vram_gb: default_vram(),
            pooled_ram_gb: default_ram(),
            tick_rate_ms: default_tick_rate(),
        }
    }
}

/// Specification for an individual physical/logical node in the mesh.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeSpec {
    #[serde(default)]
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub layer: String,
    pub ip: String,
    pub port: u16,
    pub role: String,
    #[serde(default)]
    pub group: NodeGroup,
    #[serde(default)]
    pub ram_gb: f64,
    #[serde(default)]
    pub vram_gb: f64,
    #[serde(default)]
    pub interconnect: String,
    #[serde(default)]
    pub backend: String,
    #[serde(default)]
    pub tailscale_ip: Option<String>,
    #[serde(default)]
    pub local_ip: Option<String>,
    #[serde(default)]
    pub is_master: bool,
    #[serde(default)]
    pub model_path: Option<String>,
}

impl NodeSpec {
    /// Return the preferred host/ip for network connectivity.
    pub fn endpoint(&self) -> String {
        format!("{}:{}", self.ip, self.port)
    }
}

/// Full mesh configuration model.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct MeshConfig {
    #[serde(default)]
    pub mesh: MeshMetadata,
    #[serde(default)]
    pub nodes: Vec<NodeSpec>,
}

impl MeshConfig {
    /// Load and validate configuration from a TOML string.
    pub fn load_from_str(content: &str) -> Result<Self, AppError> {
        let config: MeshConfig = toml::from_str(content)?;
        config.validate()?;
        Ok(config)
    }

    /// Load and validate configuration from a filesystem path.
    pub fn load_from_path<P: AsRef<Path>>(path: P) -> Result<Self, AppError> {
        let p = path.as_ref();
        let content = fs::read_to_string(p)
            .map_err(|e| AppError::Config(format!("Failed to read file {}: {}", p.display(), e)))?;
        Self::load_from_str(&content)
    }

    /// Auto-discover configuration across common relative and absolute search paths.
    pub fn find_and_load() -> Result<(Self, PathBuf), AppError> {
        let mut candidates = vec![
            PathBuf::from("config/mesh.toml"),
            PathBuf::from("../config/mesh.toml"),
            PathBuf::from("../../config/mesh.toml"),
            PathBuf::from("02_ai_models_and_inference/lauburu_tui/config/mesh.toml"),
            PathBuf::from("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/lauburu_tui/config/mesh.toml"),
            PathBuf::from("/home/linux/lauburu_tui/config/mesh.toml"),
            PathBuf::from("/etc/lauburu/mesh.toml"),
        ];

        if let Ok(home) = std::env::var("HOME") {
            candidates.push(PathBuf::from(format!("{}/.config/lauburu/mesh.toml", home)));
        }

        for candidate in &candidates {
            if candidate.exists() {
                let cfg = Self::load_from_path(candidate)?;
                return Ok((cfg, candidate.clone()));
            }
        }

        Err(AppError::Config(format!(
            "mesh.toml not found in any candidate path: {:?}",
            candidates
        )))
    }

    /// Default fallback configuration mirroring the canonical 7-node Lauburu mesh.
    pub fn fallback() -> Self {
        Self {
            mesh: MeshMetadata::default(),
            nodes: vec![
                NodeSpec {
                    id: "mac_host".to_string(),
                    name: "Mac Mini (M4 Pro)".to_string(),
                    layer: "L1".to_string(),
                    ip: "127.0.0.1".to_string(),
                    port: 8082,
                    role: "Master Coordinator & Prompt Ingestion".to_string(),
                    group: NodeGroup::CoreRing,
                    ram_gb: 24.0,
                    vram_gb: 21.6,
                    interconnect: "Local / TB4 DMA".to_string(),
                    backend: "Metal".to_string(),
                    tailscale_ip: Some("100.119.199.76".to_string()),
                    local_ip: Some("192.168.8.230".to_string()),
                    is_master: true,
                    model_path: None,
                },
                NodeSpec {
                    id: "macbook_pro".to_string(),
                    name: "MacBook Pro (Intel Core i7 Vault)".to_string(),
                    layer: "L2".to_string(),
                    ip: "100.103.212.21".to_string(),
                    port: 50053,
                    role: "Model Storage Vault & Secondary Worker".to_string(),
                    group: NodeGroup::CoreRing,
                    ram_gb: 16.0,
                    vram_gb: 14.0,
                    interconnect: "10Gbps TB4 Bridge (0.27ms)".to_string(),
                    backend: "Metal".to_string(),
                    tailscale_ip: Some("100.103.212.21".to_string()),
                    local_ip: Some("192.168.8.127".to_string()),
                    is_master: false,
                    model_path: None,
                },
                NodeSpec {
                    id: "macbook_air".to_string(),
                    name: "MacBook Air (M4)".to_string(),
                    layer: "L5".to_string(),
                    ip: "100.93.158.96".to_string(),
                    port: 50053,
                    role: "Secondary Metal Worker & LoRA Distillation".to_string(),
                    group: NodeGroup::CoreRing,
                    ram_gb: 16.0,
                    vram_gb: 14.0,
                    interconnect: "TB4 DMA / Wi-Fi 7 MLO".to_string(),
                    backend: "Metal".to_string(),
                    tailscale_ip: Some("100.93.158.96".to_string()),
                    local_ip: Some("192.168.8.222".to_string()),
                    is_master: false,
                    model_path: None,
                },
                NodeSpec {
                    id: "linux_head_node".to_string(),
                    name: "Linux Head Node (Ryzen 7)".to_string(),
                    layer: "L3".to_string(),
                    ip: "100.101.39.98".to_string(),
                    port: 50053,
                    role: "Gateway Ingress & Compute Hub".to_string(),
                    group: NodeGroup::CoreRing,
                    ram_gb: 16.0,
                    vram_gb: 13.8,
                    interconnect: "1GbE Copper LAN (0.90ms)".to_string(),
                    backend: "CPU + Vulkan".to_string(),
                    tailscale_ip: Some("100.101.39.98".to_string()),
                    local_ip: Some("192.168.8.224".to_string()),
                    is_master: false,
                    model_path: None,
                },
                NodeSpec {
                    id: "pixel_10".to_string(),
                    name: "Pixel 10 Pro XL (Tensor G5)".to_string(),
                    layer: "L6".to_string(),
                    ip: "100.73.38.87".to_string(),
                    port: 8084,
                    role: "Edge TPU & 8K Vision Stream".to_string(),
                    group: NodeGroup::EdgePool,
                    ram_gb: 16.0,
                    vram_gb: 12.5,
                    interconnect: "Multipath Bond / USB".to_string(),
                    backend: "Edge TPU".to_string(),
                    tailscale_ip: Some("100.73.38.87".to_string()),
                    local_ip: None,
                    is_master: false,
                    model_path: None,
                },
                NodeSpec {
                    id: "samsung_s20".to_string(),
                    name: "Samsung S20 (Exynos 990)".to_string(),
                    layer: "L7".to_string(),
                    ip: "100.84.40.95".to_string(),
                    port: 8022,
                    role: "Automated UI Tester & Edge Worker".to_string(),
                    group: NodeGroup::EdgePool,
                    ram_gb: 12.0,
                    vram_gb: 9.0,
                    interconnect: "Router USB Bridge".to_string(),
                    backend: "OpenClaw / Termux".to_string(),
                    tailscale_ip: Some("100.84.40.95".to_string()),
                    local_ip: None,
                    is_master: false,
                    model_path: None,
                },
                NodeSpec {
                    id: "linux_tablet".to_string(),
                    name: "Linux Tablet (Touch x86_64)".to_string(),
                    layer: "L4".to_string(),
                    ip: "100.81.92.125".to_string(),
                    port: 31330,
                    role: "Mobile Compute & Biometrics DSP".to_string(),
                    group: NodeGroup::EdgePool,
                    ram_gb: 8.0,
                    vram_gb: 6.5,
                    interconnect: "Tailscale Direct".to_string(),
                    backend: "Petals DHT".to_string(),
                    tailscale_ip: Some("100.81.92.125".to_string()),
                    local_ip: None,
                    is_master: false,
                    model_path: None,
                },
            ],
        }
    }

    /// Validate the configuration invariant constraints.
    pub fn validate(&self) -> Result<(), AppError> {
        if self.nodes.is_empty() {
            return Err(AppError::Validation(
                "Mesh configuration must contain at least one node".to_string(),
            ));
        }

        for (idx, node) in self.nodes.iter().enumerate() {
            if node.name.trim().is_empty() {
                return Err(AppError::Validation(format!(
                    "Node at index {idx} has an empty name"
                )));
            }
            if node.ip.trim().is_empty() {
                return Err(AppError::Validation(format!(
                    "Node '{}' has an empty IP address",
                    node.name
                )));
            }
            if node.port == 0 {
                return Err(AppError::Validation(format!(
                    "Node '{}' has an invalid port 0",
                    node.name
                )));
            }
            if node.ram_gb < 0.0 {
                return Err(AppError::Validation(format!(
                    "Node '{}' has negative RAM value: {}",
                    node.name, node.ram_gb
                )));
            }
            if node.vram_gb < 0.0 {
                return Err(AppError::Validation(format!(
                    "Node '{}' has negative VRAM value: {}",
                    node.name, node.vram_gb
                )));
            }
        }

        Ok(())
    }

    /// Calculate total pooled RAM (GB) across all configured nodes.
    pub fn total_ram_gb(&self) -> f64 {
        self.nodes.iter().map(|n| n.ram_gb).sum()
    }

    /// Calculate total pooled AI VRAM (GB) across all configured nodes.
    pub fn total_vram_gb(&self) -> f64 {
        self.nodes.iter().map(|n| n.vram_gb).sum()
    }

    /// Filter nodes belonging to the Core PRP Ring.
    pub fn core_nodes(&self) -> Vec<&NodeSpec> {
        self.nodes
            .iter()
            .filter(|n| matches!(n.group, NodeGroup::CoreRing))
            .collect()
    }

    /// Filter nodes belonging to the Edge RPC Pool.
    pub fn edge_nodes(&self) -> Vec<&NodeSpec> {
        self.nodes
            .iter()
            .filter(|n| matches!(n.group, NodeGroup::EdgePool))
            .collect()
    }

    /// Calculate total VRAM (GB) dedicated to the Core PRP Ring.
    pub fn core_vram_total(&self) -> f64 {
        self.core_nodes().iter().map(|n| n.vram_gb).sum()
    }

    /// Calculate total VRAM (GB) dedicated to the Edge RPC Pool.
    pub fn edge_vram_total(&self) -> f64 {
        self.edge_nodes().iter().map(|n| n.vram_gb).sum()
    }

    /// Calculate total RAM (GB) in Core PRP Ring.
    pub fn core_ram_total(&self) -> f64 {
        self.core_nodes().iter().map(|n| n.ram_gb).sum()
    }

    /// Calculate total RAM (GB) in Edge RPC Pool.
    pub fn edge_ram_total(&self) -> f64 {
        self.edge_nodes().iter().map(|n| n.ram_gb).sum()
    }

    /// Look up a node by its unique ID.
    pub fn get_node_by_id(&self, id: &str) -> Option<&NodeSpec> {
        self.nodes.iter().find(|n| n.id == id)
    }

    /// Look up a node by its layer designation (e.g. "L1", "L2").
    pub fn get_node_by_layer(&self, layer: &str) -> Option<&NodeSpec> {
        self.nodes.iter().find(|n| n.layer == layer)
    }

    /// Locate the master ring coordinator node.
    pub fn get_master_node(&self) -> Option<&NodeSpec> {
        self.nodes
            .iter()
            .find(|n| n.is_master)
            .or_else(|| self.nodes.first())
    }

    /// Return the primary master chat completion endpoint URL (prima.cpp).
    pub fn master_endpoint(&self) -> &str {
        if !self.mesh.prima_endpoint.is_empty() {
            &self.mesh.prima_endpoint
        } else {
            &self.mesh.master_url
        }
    }

    /// Return the fallback chat completion endpoint URL (llama.cpp).
    pub fn fallback_endpoint(&self) -> &str {
        if !self.mesh.fallback_endpoint.is_empty() {
            &self.mesh.fallback_endpoint
        } else {
            "http://127.0.0.1:8083/v1/chat/completions"
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEST_TOML: &str = r#"
[mesh]
name = "Lauburu Heterogeneous AI Mesh"
version = "1.0.0"
prima_endpoint = "http://127.0.0.1:8082/v1/chat/completions"
master_url = "http://127.0.0.1:8082"
pooled_vram_gb = 82.8
pooled_ram_gb = 108.0

[[nodes]]
id = "mac_host"
name = "Mac Mini (M4 Pro)"
layer = "L1"
ip = "127.0.0.1"
port = 8082
role = "Master Coordinator"
group = "core_ring"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "TB4 DMA"
backend = "Metal"
is_master = true

[[nodes]]
id = "macbook_pro"
name = "MacBook Pro (M1 Max)"
layer = "L2"
ip = "100.103.212.21"
port = 50053
role = "Worker"
group = "core_ring"
ram_gb = 16.0
vram_gb = 14.0
interconnect = "TB4"
backend = "Metal"

[[nodes]]
id = "pixel_10"
name = "Pixel 10 Pro XL"
layer = "L6"
ip = "100.73.38.87"
port = 8084
role = "Edge TPU"
group = "edge_pool"
ram_gb = 16.0
vram_gb = 12.5
interconnect = "Tailscale"
backend = "Edge TPU"
"#;

    #[test]
    fn test_parse_valid_mesh_config() {
        let config = MeshConfig::load_from_str(TEST_TOML).expect("Failed to parse TEST_TOML");
        assert_eq!(config.mesh.name, "Lauburu Heterogeneous AI Mesh");
        assert_eq!(config.nodes.len(), 3);
        assert_eq!(config.nodes[0].name, "Mac Mini (M4 Pro)");
        assert_eq!(config.nodes[0].group, NodeGroup::CoreRing);
        assert!(config.nodes[0].is_master);
    }

    #[test]
    fn test_total_ram_vram_calculations() {
        let config = MeshConfig::load_from_str(TEST_TOML).expect("Failed to parse");
        let total_ram = config.total_ram_gb();
        let total_vram = config.total_vram_gb();
        assert!((total_ram - 56.0).abs() < 1e-5);
        assert!((total_vram - 48.1).abs() < 1e-5);

        let core_vram = config.core_vram_total();
        let edge_vram = config.edge_vram_total();
        assert!((core_vram - 35.6).abs() < 1e-5);
        assert!((edge_vram - 12.5).abs() < 1e-5);
    }

    #[test]
    fn test_core_and_edge_partitioning() {
        let config = MeshConfig::load_from_str(TEST_TOML).expect("Failed to parse");
        let core = config.core_nodes();
        let edge = config.edge_nodes();
        assert_eq!(core.len(), 2);
        assert_eq!(edge.len(), 1);
        assert_eq!(core[0].layer, "L1");
        assert_eq!(core[1].layer, "L2");
        assert_eq!(edge[0].layer, "L6");
    }

    #[test]
    fn test_node_lookups() {
        let config = MeshConfig::load_from_str(TEST_TOML).expect("Failed to parse");
        assert!(config.get_node_by_id("mac_host").is_some());
        assert_eq!(
            config.get_node_by_id("mac_host").unwrap().name,
            "Mac Mini (M4 Pro)"
        );
        assert!(config.get_node_by_layer("L6").is_some());
        assert_eq!(
            config.get_node_by_layer("L6").unwrap().name,
            "Pixel 10 Pro XL"
        );
        assert!(config.get_node_by_id("nonexistent").is_none());

        let master = config.get_master_node().expect("Master node not found");
        assert_eq!(master.id, "mac_host");
        assert_eq!(master.port, 8082);
    }

    #[test]
    fn test_validation_empty_nodes() {
        let invalid = r#"
[mesh]
name = "Empty Mesh"
nodes = []
"#;
        let res = MeshConfig::load_from_str(invalid);
        assert!(res.is_err());
        assert!(matches!(res.unwrap_err(), AppError::Validation(_)));
    }

    #[test]
    fn test_validation_zero_port() {
        let invalid = r#"
[[nodes]]
name = "Invalid Port Node"
ip = "127.0.0.1"
port = 0
role = "Test"
"#;
        let res = MeshConfig::load_from_str(invalid);
        assert!(res.is_err());
        assert!(matches!(res.unwrap_err(), AppError::Validation(_)));
    }

    #[test]
    fn test_validation_empty_name() {
        let invalid = r#"
[[nodes]]
name = "  "
ip = "127.0.0.1"
port = 8080
role = "Test"
"#;
        let res = MeshConfig::load_from_str(invalid);
        assert!(res.is_err());
        assert!(matches!(res.unwrap_err(), AppError::Validation(_)));
    }

    #[test]
    fn test_validation_empty_ip() {
        let invalid = r#"
[[nodes]]
name = "Valid Name"
ip = " "
port = 8080
role = "Test"
"#;
        let res = MeshConfig::load_from_str(invalid);
        assert!(res.is_err());
        assert!(matches!(res.unwrap_err(), AppError::Validation(_)));
    }

    #[test]
    fn test_fallback_config_validity() {
        let fallback = MeshConfig::fallback();
        assert_eq!(fallback.nodes.len(), 7);
        assert!(fallback.validate().is_ok());
        assert_eq!(fallback.core_nodes().len(), 4);
        assert_eq!(fallback.edge_nodes().len(), 3);
        assert!((fallback.total_ram_gb() - 108.0).abs() < 1e-4);
        assert!((fallback.total_vram_gb() - 90.9).abs() < 1e-4);
    }

    #[test]
    fn test_canonical_mesh_toml_parsing() {
        let config_path = PathBuf::from("config/mesh.toml");
        if config_path.exists() {
            let config =
                MeshConfig::load_from_path(&config_path).expect("Failed to parse config/mesh.toml");
            assert_eq!(config.nodes.len(), 7);
            assert_eq!(config.core_nodes().len(), 4);
            assert_eq!(config.edge_nodes().len(), 3);
        }
    }
}
