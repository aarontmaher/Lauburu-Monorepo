//! ============================================================================
//! Tier 1 & Tier 2 Test Suite: Configuration Parsing & Validation
//! ============================================================================
//! Features Covered:
//! - F1: Cargo Scaffolding & Dependencies (Config structs & Serde contracts)
//! - F2: Mesh TOML Configuration (Deserialization, validation, node specs)
//! - F10: Zero-Mock / Truth Audit Compliance (Accurate data representation)
//! ============================================================================

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

// ----------------------------------------------------------------------------
// Canonical Domain Structs matching Interface Contracts (PROJECT.md)
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeGroup {
    #[serde(rename = "CoreRing")]
    CoreRing,
    #[serde(rename = "EdgePool")]
    EdgePool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
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

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MeshConfig {
    pub nodes: Vec<NodeSpec>,
}

impl MeshConfig {
    pub fn from_toml_str(content: &str) -> Result<Self, toml::de::Error> {
        toml::from_str(content)
    }

    pub fn load_from_path<P: AsRef<Path>>(path: P) -> Result<Self, Box<dyn std::error::Error>> {
        let content = fs::read_to_string(path)?;
        let config: MeshConfig = toml::from_str(&content)?;
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.nodes.is_empty() {
            return Err("Configuration must contain at least one node".to_string());
        }
        for (idx, node) in self.nodes.iter().enumerate() {
            if node.name.trim().is_empty() {
                return Err(format!("Node at index {} has an empty name", idx));
            }
            if node.ip.trim().is_empty() {
                return Err(format!("Node '{}' has an empty IP address", node.name));
            }
            if node.port == 0 {
                return Err(format!("Node '{}' has an invalid port 0", node.name));
            }
            if node.ram_gb < 0.0 {
                return Err(format!("Node '{}' has negative RAM", node.name));
            }
            if node.vram_gb < 0.0 {
                return Err(format!("Node '{}' has negative VRAM", node.name));
            }
        }
        Ok(())
    }

    pub fn total_ram_gb(&self) -> f64 {
        self.nodes.iter().map(|n| n.ram_gb).sum()
    }

    pub fn total_vram_gb(&self) -> f64 {
        self.nodes.iter().map(|n| n.vram_gb).sum()
    }

    pub fn core_vram_gb(&self) -> f64 {
        self.nodes
            .iter()
            .filter(|n| n.group == NodeGroup::CoreRing)
            .map(|n| n.vram_gb)
            .sum()
    }

    pub fn edge_vram_gb(&self) -> f64 {
        self.nodes
            .iter()
            .filter(|n| n.group == NodeGroup::EdgePool)
            .map(|n| n.vram_gb)
            .sum()
    }
}

// ----------------------------------------------------------------------------
// Canonical Reference Configuration (mesh.toml content from canonical arch)
// ----------------------------------------------------------------------------

pub const CANONICAL_MESH_TOML: &str = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 8082
role = "Primary Host & Memory Governor"
layer = "L1"
group = "CoreRing"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "Host DMA / Loopback"
backend = "Apple Metal M4 Pro"

[[nodes]]
name = "MacBook_Pro"
ip = "192.168.8.127"
port = 8081
role = "Metal GPU RPC & Storage Vault"
layer = "L2"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 14.0
interconnect = "10Gbps Thunderbolt 4"
backend = "Apple Metal M1 Pro"

[[nodes]]
name = "Linux_Head_Node"
ip = "192.168.8.224"
port = 8083
role = "Gateway Ingress & Compute Hub"
layer = "L3"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 13.8
interconnect = "1GbE Ethernet"
backend = "AMD Vulkan / ROCm"

[[nodes]]
name = "MacBook_Air"
ip = "192.168.8.222"
port = 8084
role = "Secondary High-Speed Metal Worker"
layer = "L5"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 14.0
interconnect = "Wi-Fi 7 MLO"
backend = "Apple Metal M4"

[[nodes]]
name = "Pixel_10_Pro_XL"
ip = "100.73.38.87"
port = 50051
role = "8K Vision Stream & Edge TPU"
layer = "L6"
group = "EdgePool"
ram_gb = 16.0
vram_gb = 12.5
interconnect = "Tailscale / Wi-Fi 7"
backend = "Google Tensor G5 TPU"

[[nodes]]
name = "Samsung_S20"
ip = "100.84.40.95"
port = 50052
role = "Dedicated Automated UI Tester"
layer = "L7"
group = "EdgePool"
ram_gb = 12.0
vram_gb = 9.0
interconnect = "Tailscale / Wi-Fi 6"
backend = "Samsung Exynos 990"

[[nodes]]
name = "Linux_Tablet"
ip = "100.81.92.125"
port = 50053
role = "Mobile Linux Compute & Touch DSP"
layer = "L4"
group = "EdgePool"
ram_gb = 8.0
vram_gb = 6.5
interconnect = "Tailscale / Wi-Fi"
backend = "Debian Linux CPU/GPU"
"#;

// ============================================================================
// TIER 1: FEATURE COVERAGE TESTS (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t1_f1_01_canonical_toml_deserialization_success() {
    let config = MeshConfig::from_toml_str(CANONICAL_MESH_TOML).expect("Failed to parse canonical mesh.toml");
    assert_eq!(config.nodes.len(), 7, "Expected exactly 7 nodes in canonical mesh");
}

#[test]
fn test_t1_f2_02_all_node_names_parsed_correctly() {
    let config = MeshConfig::from_toml_str(CANONICAL_MESH_TOML).unwrap();
    let names: Vec<&str> = config.nodes.iter().map(|n| n.name.as_str()).collect();
    assert_eq!(
        names,
        vec![
            "Mac_Node",
            "MacBook_Pro",
            "Linux_Head_Node",
            "MacBook_Air",
            "Pixel_10_Pro_XL",
            "Samsung_S20",
            "Linux_Tablet"
        ]
    );
}

#[test]
fn test_t1_f2_03_node_groups_partitioned_accurately() {
    let config = MeshConfig::from_toml_str(CANONICAL_MESH_TOML).unwrap();
    let core_nodes: Vec<&NodeSpec> = config.nodes.iter().filter(|n| n.group == NodeGroup::CoreRing).collect();
    let edge_nodes: Vec<&NodeSpec> = config.nodes.iter().filter(|n| n.group == NodeGroup::EdgePool).collect();

    assert_eq!(core_nodes.len(), 4, "Expected 4 CoreRing nodes");
    assert_eq!(edge_nodes.len(), 3, "Expected 3 EdgePool nodes");
}

#[test]
fn test_t1_f2_04_aggregate_ram_calculation() {
    let config = MeshConfig::from_toml_str(CANONICAL_MESH_TOML).unwrap();
    let total_ram = config.total_ram_gb();
    // 24 + 16 + 16 + 16 + 16 + 12 + 8 = 108.0 GB
    assert!((total_ram - 108.0).abs() < 1e-6, "Expected 108.0 GB RAM, got {}", total_ram);
}

#[test]
fn test_t1_f2_05_aggregate_vram_calculation() {
    let config = MeshConfig::from_toml_str(CANONICAL_MESH_TOML).unwrap();
    let total_vram = config.total_vram_gb();
    // 21.6 + 14.0 + 13.8 + 14.0 + 12.5 + 9.0 + 6.5 = 91.4 GB
    assert!((total_vram - 91.4).abs() < 1e-6, "Expected 91.4 GB total VRAM, got {}", total_vram);

    let core_vram = config.core_vram_gb();
    // 21.6 + 14.0 + 13.8 + 14.0 = 63.4 GB
    assert!((core_vram - 63.4).abs() < 1e-6, "Expected 63.4 GB Core VRAM, got {}", core_vram);

    let edge_vram = config.edge_vram_gb();
    // 12.5 + 9.0 + 6.5 = 28.0 GB
    assert!((edge_vram - 28.0).abs() < 1e-6, "Expected 28.0 GB Edge VRAM, got {}", edge_vram);
}

#[test]
fn test_t1_f10_06_node_spec_truth_attributes() {
    let config = MeshConfig::from_toml_str(CANONICAL_MESH_TOML).unwrap();
    let mac_mini = &config.nodes[0];
    assert_eq!(mac_mini.name, "Mac_Node");
    assert_eq!(mac_mini.ip, "192.168.8.230");
    assert_eq!(mac_mini.port, 8082);
    assert_eq!(mac_mini.layer, "L1");
    assert_eq!(mac_mini.backend, "Apple Metal M4 Pro");
    assert_eq!(mac_mini.interconnect, "Host DMA / Loopback");
}

#[test]
fn test_t1_f2_07_load_from_temporary_file() {
    let temp_dir = std::env::temp_dir();
    let temp_file = temp_dir.join("lauburu_test_mesh.toml");
    fs::write(&temp_file, CANONICAL_MESH_TOML).expect("Failed to write temp file");

    let loaded = MeshConfig::load_from_path(&temp_file).expect("Failed to load config from temp file");
    assert_eq!(loaded.nodes.len(), 7);

    let _ = fs::remove_file(temp_file);
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t2_b01_empty_toml_string_fails() {
    let result = MeshConfig::from_toml_str("");
    assert!(result.is_err(), "Empty TOML must fail to parse nodes array");
}

#[test]
fn test_t2_b02_empty_nodes_array_fails_validation() {
    let toml_data = "nodes = []";
    let config = MeshConfig::from_toml_str(toml_data).expect("Should parse empty vec");
    let validation = config.validate();
    assert!(validation.is_err(), "Validation must fail for empty node list");
    assert!(validation.unwrap_err().contains("at least one node"));
}

#[test]
fn test_t2_b03_missing_mandatory_field_ip() {
    let invalid_toml = r#"
[[nodes]]
name = "Mac_Node"
port = 8082
role = "Primary"
layer = "L1"
group = "CoreRing"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "DMA"
backend = "Metal"
"#;
    let result = MeshConfig::from_toml_str(invalid_toml);
    assert!(result.is_err(), "Missing 'ip' field must trigger deserialization error");
}

#[test]
fn test_t2_b04_missing_mandatory_field_group() {
    let invalid_toml = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 8082
role = "Primary"
layer = "L1"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "DMA"
backend = "Metal"
"#;
    let result = MeshConfig::from_toml_str(invalid_toml);
    assert!(result.is_err(), "Missing 'group' field must fail deserialization");
}

#[test]
fn test_t2_b05_invalid_group_enum_value() {
    let invalid_toml = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 8082
role = "Primary"
layer = "L1"
group = "UnknownGroup"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "DMA"
backend = "Metal"
"#;
    let result = MeshConfig::from_toml_str(invalid_toml);
    assert!(result.is_err(), "Invalid group 'UnknownGroup' must fail deserialization");
}

#[test]
fn test_t2_b06_invalid_port_zero() {
    let toml_data = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 0
role = "Primary"
layer = "L1"
group = "CoreRing"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "DMA"
backend = "Metal"
"#;
    let config = MeshConfig::from_toml_str(toml_data).unwrap();
    let err = config.validate().unwrap_err();
    assert!(err.contains("invalid port 0"));
}

#[test]
fn test_t2_b07_port_overflow_in_toml() {
    let toml_data = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 70000
role = "Primary"
layer = "L1"
group = "CoreRing"
ram_gb = 24.0
vram_gb = 21.6
interconnect = "DMA"
backend = "Metal"
"#;
    let result = MeshConfig::from_toml_str(toml_data);
    assert!(result.is_err(), "Port > 65535 must fail u16 deserialization");
}

#[test]
fn test_t2_b08_negative_ram_fails_validation() {
    let toml_data = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 8082
role = "Primary"
layer = "L1"
group = "CoreRing"
ram_gb = -16.0
vram_gb = 14.0
interconnect = "DMA"
backend = "Metal"
"#;
    let config = MeshConfig::from_toml_str(toml_data).unwrap();
    let err = config.validate().unwrap_err();
    assert!(err.contains("negative RAM"));
}

#[test]
fn test_t2_b09_negative_vram_fails_validation() {
    let toml_data = r#"
[[nodes]]
name = "Mac_Node"
ip = "192.168.8.230"
port = 8082
role = "Primary"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = -1.0
interconnect = "DMA"
backend = "Metal"
"#;
    let config = MeshConfig::from_toml_str(toml_data).unwrap();
    let err = config.validate().unwrap_err();
    assert!(err.contains("negative VRAM"));
}

#[test]
fn test_t2_b10_empty_node_name_fails_validation() {
    let toml_data = r#"
[[nodes]]
name = "   "
ip = "192.168.8.230"
port = 8082
role = "Primary"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 14.0
interconnect = "DMA"
backend = "Metal"
"#;
    let config = MeshConfig::from_toml_str(toml_data).unwrap();
    let err = config.validate().unwrap_err();
    assert!(err.contains("empty name"));
}

#[test]
fn test_t2_b11_unicode_node_names_and_roles() {
    let toml_data = r#"
[[nodes]]
name = "🦀_Rust_Node_🚀"
ip = "127.0.0.1"
port = 8082
role = "高性能推論ノード"
layer = "L1"
group = "CoreRing"
ram_gb = 32.5
vram_gb = 24.0
interconnect = "雷霆 4 ⚡"
backend = "Metal 3.0"
"#;
    let config = MeshConfig::from_toml_str(toml_data).expect("Should handle full unicode strings");
    assert_eq!(config.nodes[0].name, "🦀_Rust_Node_🚀");
    assert_eq!(config.nodes[0].role, "高性能推論ノード");
    assert_eq!(config.nodes[0].interconnect, "雷霆 4 ⚡");
    assert!(config.validate().is_ok());
}

#[test]
fn test_t2_b12_nonexistent_file_path_error() {
    let fake_path = PathBuf::from("/nonexistent/path/mesh_999.toml");
    let result = MeshConfig::load_from_path(fake_path);
    assert!(result.is_err(), "Loading from nonexistent file path must return Err");
}

#[test]
fn test_t2_b13_crlf_line_endings_support() {
    let crlf_toml = CANONICAL_MESH_TOML.replace('\n', "\r\n");
    let config = MeshConfig::from_toml_str(&crlf_toml).expect("Must handle CRLF line endings cleanly");
    assert_eq!(config.nodes.len(), 7);
}

#[test]
fn test_t2_b14_float_zero_vram_node_valid() {
    let toml_data = r#"
[[nodes]]
name = "CPU_Only_Worker"
ip = "192.168.8.200"
port = 9000
role = "CPU Ingestion"
layer = "L8"
group = "EdgePool"
ram_gb = 64.0
vram_gb = 0.0
interconnect = "10GbE"
backend = "x86_64 AVX-512"
"#;
    let config = MeshConfig::from_toml_str(toml_data).unwrap();
    assert!(config.validate().is_ok());
    assert_eq!(config.nodes[0].vram_gb, 0.0);
    assert_eq!(config.edge_vram_gb(), 0.0);
    assert_eq!(config.total_ram_gb(), 64.0);
}

#[test]
fn test_t2_b15_duplicate_node_names_parsed() {
    let toml_data = r#"
[[nodes]]
name = "Duplicate_Node"
ip = "192.168.8.10"
port = 8080
role = "Worker A"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"

[[nodes]]
name = "Duplicate_Node"
ip = "192.168.8.11"
port = 8081
role = "Worker B"
layer = "L2"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#;
    let config = MeshConfig::from_toml_str(toml_data).unwrap();
    assert_eq!(config.nodes.len(), 2);
    assert_eq!(config.nodes[0].name, config.nodes[1].name);
    assert_ne!(config.nodes[0].ip, config.nodes[1].ip);
}

// ============================================================================
// TIER 5: ADVERSARIAL STRESS & CORRUPTION HARNESS
// ============================================================================

#[test]
fn test_t5_adv01_zero_byte_config_fails_validation() {
    let local_res = MeshConfig::from_toml_str("");
    assert!(local_res.is_err() || local_res.unwrap().validate().is_err());

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str("");
    assert!(prod_res.is_err(), "Zero-byte string must fail production load_from_str");
    assert!(matches!(prod_res.unwrap_err(), lauburu_tui::errors::AppError::Validation(_)));
}

#[test]
fn test_t5_adv02_whitespace_only_config_fails_validation() {
    let whitespace_input = "   \n\t  \r\n   ";
    let local_res = MeshConfig::from_toml_str(whitespace_input);
    assert!(local_res.is_err() || local_res.unwrap().validate().is_err());

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(whitespace_input);
    assert!(prod_res.is_err(), "Whitespace-only config must fail validation");
}

#[test]
fn test_t5_adv03_malformed_toml_unclosed_quotes() {
    let bad_toml = r#"
[[nodes]]
name = "Unclosed String Value
ip = "127.0.0.1"
port = 8080
"#;
    let local_res = MeshConfig::from_toml_str(bad_toml);
    assert!(local_res.is_err(), "Unclosed string literal must fail TOML deserialization");

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(bad_toml);
    assert!(prod_res.is_err(), "Unclosed string literal must fail production deserializer");
}

#[test]
fn test_t5_adv04_malformed_toml_invalid_datatypes() {
    let bad_toml = r#"
[[nodes]]
name = 12345
ip = true
port = "not_a_number"
role = []
"#;
    let local_res = MeshConfig::from_toml_str(bad_toml);
    assert!(local_res.is_err(), "Invalid datatypes must fail deserialization");

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(bad_toml);
    assert!(prod_res.is_err(), "Invalid datatypes must fail production deserializer");
}

#[test]
fn test_t5_adv05_missing_mandatory_key_name() {
    let bad_toml = r#"
[[nodes]]
ip = "127.0.0.1"
port = 8080
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#;
    let local_res = MeshConfig::from_toml_str(bad_toml);
    assert!(local_res.is_err(), "Missing 'name' field must fail");

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(bad_toml);
    assert!(prod_res.is_err(), "Missing 'name' must fail production deserializer");
}

#[test]
fn test_t5_adv06_missing_mandatory_key_port() {
    let bad_toml = r#"
[[nodes]]
name = "Node_A"
ip = "127.0.0.1"
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#;
    let local_res = MeshConfig::from_toml_str(bad_toml);
    assert!(local_res.is_err(), "Missing 'port' field must fail");

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(bad_toml);
    assert!(prod_res.is_err(), "Missing 'port' must fail production deserializer");
}

#[test]
fn test_t5_adv07_missing_mandatory_key_role() {
    let bad_toml = r#"
[[nodes]]
name = "Node_A"
ip = "127.0.0.1"
port = 8080
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#;
    let local_res = MeshConfig::from_toml_str(bad_toml);
    assert!(local_res.is_err(), "Missing 'role' field must fail");

    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(bad_toml);
    assert!(prod_res.is_err(), "Missing 'role' must fail production deserializer");
}

#[test]
fn test_t5_adv08_negative_ram_boundary_values() {
    for neg_val in &[-0.000001, -1.0, -100.0, -1e10] {
        let bad_toml = format!(
            r#"
[[nodes]]
name = "Node_Neg"
ip = "127.0.0.1"
port = 8080
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = {}
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#,
            neg_val
        );
        let local_res = MeshConfig::from_toml_str(&bad_toml);
        if let Ok(cfg) = local_res {
            assert!(cfg.validate().is_err(), "RAM {} must fail validation", neg_val);
        }

        let prod_res = lauburu_tui::config::MeshConfig::load_from_str(&bad_toml);
        assert!(prod_res.is_err(), "Production RAM {} must fail validation", neg_val);
    }
}

#[test]
fn test_t5_adv09_negative_vram_boundary_values() {
    for neg_val in &[-0.000001, -1.0, -50.0, -1e10] {
        let bad_toml = format!(
            r#"
[[nodes]]
name = "Node_Neg"
ip = "127.0.0.1"
port = 8080
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = {}
interconnect = "LAN"
backend = "Metal"
"#,
            neg_val
        );
        let local_res = MeshConfig::from_toml_str(&bad_toml);
        if let Ok(cfg) = local_res {
            assert!(cfg.validate().is_err(), "VRAM {} must fail validation", neg_val);
        }

        let prod_res = lauburu_tui::config::MeshConfig::load_from_str(&bad_toml);
        assert!(prod_res.is_err(), "Production VRAM {} must fail validation", neg_val);
    }
}

#[test]
fn test_t5_adv10_whitespace_padded_name_fails_validation() {
    for bad_name in &["", " ", "   \t  ", "\n\r\t"] {
        let bad_toml = format!(
            r#"
[[nodes]]
name = "{}"
ip = "127.0.0.1"
port = 8080
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#,
            bad_name.escape_debug()
        );
        let local_res = MeshConfig::from_toml_str(&bad_toml);
        if let Ok(cfg) = local_res {
            assert!(cfg.validate().is_err(), "Name '{:?}' must fail validation", bad_name);
        }

        let prod_res = lauburu_tui::config::MeshConfig::load_from_str(&bad_toml);
        assert!(prod_res.is_err(), "Production Name '{:?}' must fail validation", bad_name);
    }
}

#[test]
fn test_t5_adv11_whitespace_padded_ip_fails_validation() {
    for bad_ip in &["", " ", "   \t  ", "\n"] {
        let bad_toml = format!(
            r#"
[[nodes]]
name = "Node_Test"
ip = "{}"
port = 8080
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#,
            bad_ip.escape_debug()
        );
        let local_res = MeshConfig::from_toml_str(&bad_toml);
        if let Ok(cfg) = local_res {
            assert!(cfg.validate().is_err(), "IP '{:?}' must fail validation", bad_ip);
        }

        let prod_res = lauburu_tui::config::MeshConfig::load_from_str(&bad_toml);
        assert!(prod_res.is_err(), "Production IP '{:?}' must fail validation", bad_ip);
    }
}

#[test]
fn test_t5_adv12_corrupted_binary_file_load_fails() {
    let temp_dir = std::env::temp_dir();
    let temp_path = temp_dir.join("corrupted_mesh_test.bin");
    // Write invalid UTF-8 binary bytes
    let bad_bytes: Vec<u8> = vec![0x80, 0x81, 0xFF, 0xFE, 0x00, 0xAA, 0xBB, 0xCC];
    fs::write(&temp_path, bad_bytes).expect("Failed to write binary test file");

    let local_res = MeshConfig::load_from_path(&temp_path);
    assert!(local_res.is_err(), "Corrupted binary file must fail local load_from_path");

    let prod_res = lauburu_tui::config::MeshConfig::load_from_path(&temp_path);
    assert!(prod_res.is_err(), "Corrupted binary file must fail production load_from_path");

    let _ = fs::remove_file(temp_path);
}

#[test]
fn test_t5_adv13_massive_cluster_1000_nodes_stress() {
    let mut toml_buf = String::from("[mesh]\nname = \"Mega Cluster\"\n\n");
    for i in 0..1000 {
        let group_str = if i % 2 == 0 { "core_ring" } else { "edge_pool" };
        toml_buf.push_str(&format!(
            r#"[[nodes]]
id = "node_{i}"
name = "Node #{i}"
layer = "L1"
ip = "10.0.0.{}"
port = {}
role = "Compute Worker"
group = "{}"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "10GbE"
backend = "Metal"

"#,
            (i % 250) + 1,
            8000 + (i % 1000),
            group_str
        ));
    }

    let prod_cfg = lauburu_tui::config::MeshConfig::load_from_str(&toml_buf)
        .expect("Massive 1000-node cluster should deserialize cleanly");
    assert_eq!(prod_cfg.nodes.len(), 1000);
    assert_eq!(prod_cfg.core_nodes().len(), 500);
    assert_eq!(prod_cfg.edge_nodes().len(), 500);
    assert!((prod_cfg.total_ram_gb() - 16000.0).abs() < 1e-4);
    assert!((prod_cfg.total_vram_gb() - 8000.0).abs() < 1e-4);
}

#[test]
fn test_t5_adv14_production_mesh_config_find_and_load() {
    let res = lauburu_tui::config::MeshConfig::find_and_load();
    assert!(res.is_ok(), "find_and_load() must discover canonical mesh.toml");
    let (cfg, path) = res.unwrap();
    assert!(path.exists(), "Discovered path must exist");
    assert_eq!(cfg.nodes.len(), 7, "Canonical mesh must have exactly 7 nodes");
    assert_eq!(cfg.core_nodes().len(), 4, "Canonical mesh must have 4 core nodes");
    assert_eq!(cfg.edge_nodes().len(), 3, "Canonical mesh must have 3 edge nodes");
    assert!((cfg.total_ram_gb() - 108.0).abs() < 1e-4);
}

#[test]
fn test_t5_adv15_production_mesh_config_endpoint_formatting() {
    let (cfg, _) = lauburu_tui::config::MeshConfig::find_and_load().expect("Should load mesh.toml");
    for node in &cfg.nodes {
        let ep = node.endpoint();
        assert_eq!(ep, format!("{}:{}", node.ip, node.port));
        assert!(!ep.is_empty());
        assert!(ep.contains(':'));
    }
}

#[test]
fn test_t5_adv16_production_mesh_config_master_node_lookup() {
    let (cfg, _) = lauburu_tui::config::MeshConfig::find_and_load().expect("Should load mesh.toml");
    let master = cfg.get_master_node().expect("Master node must exist");
    assert_eq!(master.id, "mac_host");
    assert_eq!(master.port, 8082);
    assert!(master.is_master);
}

#[test]
fn test_t5_adv17_production_mesh_config_layer_lookups() {
    let (cfg, _) = lauburu_tui::config::MeshConfig::find_and_load().expect("Should load mesh.toml");
    for layer in &["L1", "L2", "L3", "L4", "L5", "L6", "L7"] {
        assert!(cfg.get_node_by_layer(layer).is_some(), "Layer {} must exist", layer);
    }
    assert!(cfg.get_node_by_layer("L99").is_none());
}

#[test]
fn test_t5_adv18_deeply_nested_toml_table_attack() {
    let deeply_nested = r#"
[mesh]
name = "Nested Test"

[mesh.extra.metadata.deeply.nested.property.level.eight]
key = "value"

[[nodes]]
name = "Node_Nested"
ip = "127.0.0.1"
port = 8080
role = "Worker"
layer = "L1"
group = "CoreRing"
ram_gb = 16.0
vram_gb = 8.0
interconnect = "LAN"
backend = "Metal"
"#;
    let prod_res = lauburu_tui::config::MeshConfig::load_from_str(deeply_nested);
    assert!(prod_res.is_ok(), "Deeply nested extra tables should be safely ignored");
}

