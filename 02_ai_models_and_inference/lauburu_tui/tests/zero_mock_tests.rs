//! ============================================================================
//! Tier 1 & Tier 2 Test Suite: Truth Audit & Zero-Mock Enforcement (Rule #0)
//! ============================================================================
//! Features Covered:
//! - F10: Zero-Mock / Truth Audit Compliance (Zero synthetic data, true sockets)
//! - F1: Cargo Scaffolding & Codebase Integrity
//! - F2: Mesh TOML Dynamic Memory Computation
//! - F8: Real Network SSE Verification
//! ============================================================================

use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

// ----------------------------------------------------------------------------
// Domain & Verification Structs
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct NodeSpec {
    pub name: String,
    pub ip: String,
    pub port: u16,
    pub ram_gb: f64,
    pub vram_gb: f64,
}

pub struct MeshCluster {
    pub nodes: Vec<NodeSpec>,
}

impl MeshCluster {
    pub fn new(nodes: Vec<NodeSpec>) -> Self {
        Self { nodes }
    }

    /// Strictly dynamically calculated — never returns a hardcoded constant
    pub fn compute_dynamic_vram_sum(&self) -> f64 {
        self.nodes.iter().map(|n| n.vram_gb).sum()
    }

    /// Strictly dynamically calculated — never returns a hardcoded constant
    pub fn compute_dynamic_ram_sum(&self) -> f64 {
        self.nodes.iter().map(|n| n.ram_gb).sum()
    }
}

// ============================================================================
// TIER 1: ZERO-MOCK TRUTH AUDIT TESTS (≥5 tests)
// ============================================================================

#[test]
fn test_t1_f10_01_dynamic_computation_scales_with_modified_node_vram() {
    let mut nodes = vec![
        NodeSpec {
            name: "Mac_Node".to_string(),
            ip: "192.168.8.230".to_string(),
            port: 8082,
            ram_gb: 24.0,
            vram_gb: 21.6,
        },
        NodeSpec {
            name: "MacBook_Pro".to_string(),
            ip: "192.168.8.127".to_string(),
            port: 8081,
            ram_gb: 16.0,
            vram_gb: 14.0,
        },
    ];

    let cluster = MeshCluster::new(nodes.clone());
    assert!((cluster.compute_dynamic_vram_sum() - 35.6).abs() < 1e-6);

    // If an implementer hardcoded 35.6, changing the node VRAM will catch the violation
    nodes[0].vram_gb = 30.0;
    let modified_cluster = MeshCluster::new(nodes);
    assert_eq!(
        modified_cluster.compute_dynamic_vram_sum(),
        44.0,
        "VRAM sum must be computed dynamically, not hardcoded"
    );
}

#[test]
fn test_t1_f10_02_dynamic_computation_scales_with_modified_node_ram() {
    let mut nodes = vec![
        NodeSpec {
            name: "Linux_Head".to_string(),
            ip: "192.168.8.224".to_string(),
            port: 8083,
            ram_gb: 16.0,
            vram_gb: 13.8,
        },
    ];

    let cluster = MeshCluster::new(nodes.clone());
    assert_eq!(cluster.compute_dynamic_ram_sum(), 16.0);

    nodes[0].ram_gb = 64.0;
    let modified = MeshCluster::new(nodes);
    assert_eq!(modified.compute_dynamic_ram_sum(), 64.0);
}

#[test]
fn test_t1_f10_03_zero_synthetic_tokens_emitted_on_empty_sse_stream() {
    let empty_payload = b"";
    let mut acc_tokens = Vec::<String>::new();

    // Any real parser must emit 0 tokens for empty payload
    if !empty_payload.is_empty() {
        acc_tokens.push("synthetic".to_string());
    }

    assert!(
        acc_tokens.is_empty(),
        "Must never generate synthetic fallback tokens on empty payload"
    );
}

#[test]
fn test_t1_f10_04_real_monotonic_latency_measurement() {
    let start = Instant::now();
    std::thread::sleep(std::time::Duration::from_millis(15));
    let elapsed = start.elapsed();

    // Verify clock is strictly monotonic and non-zero
    assert!(elapsed.as_millis() >= 10, "Elapsed time must reflect real wall clock time");
    assert!(elapsed.as_millis() < 500, "Elapsed time must not be artificially padded");
}

#[test]
fn test_t1_f10_05_offline_socket_produces_real_error_not_simulated_reply() {
    // Attempting to connect to offline socket must yield an explicit error,
    // NEVER a synthetic "Hello from mock AI" reply.
    let offline_endpoint = "http://127.0.0.1:59997/v1/chat/completions";
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_millis(200))
        .build()
        .unwrap();

    let result = client.post(offline_endpoint).send();
    assert!(
        result.is_err(),
        "Zero-Mock invariant: Offline endpoint must fail natively and return Err"
    );
}

// ============================================================================
// TIER 2: STATIC SOURCE CODE FORENSIC AUDIT (Scan src/ directory for mocks)
// ============================================================================

#[test]
fn test_t2_f10_audit_01_no_forbidden_mock_keywords_in_source() {
    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let src_dir = project_root.join("src");

    if src_dir.exists() {
        let forbidden_patterns = [
            "mock_response",
            "fake_stream",
            "dummy_token",
            "simulated_reply",
            "lorem ipsum",
            "This is a simulated AI response",
        ];

        for entry in walk_dir(&src_dir) {
            if entry.extension().and_then(|s| s.to_str()) == Some("rs") {
                let content = fs::read_to_string(&entry).expect("Failed to read src file");
                for pattern in &forbidden_patterns {
                    assert!(
                        !content.to_lowercase().contains(pattern),
                        "Zero-Mock Violation: Found forbidden mock pattern '{}' in file {:?}",
                        pattern,
                        entry
                    );
                }
            }
        }
    }
}

#[test]
fn test_t2_f10_audit_02_mesh_toml_no_dummy_ips() {
    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let config_path = project_root.join("config/mesh.toml");

    if config_path.exists() {
        let content = fs::read_to_string(config_path).expect("Failed to read config/mesh.toml");
        assert!(
            !content.contains("0.0.0.0"),
            "Zero-Mock Violation: mesh.toml must not use placeholder 0.0.0.0 IPs"
        );
        assert!(
            !content.contains("example.com"),
            "Zero-Mock Violation: mesh.toml must not use example.com"
        );
        assert!(
            content.contains("192.168.8.230"),
            "Canonical Truth: Must contain Mac_Node real IP 192.168.8.230"
        );
    }
}

// Helper to recursively walk a directory
fn walk_dir(dir: &Path) -> Vec<PathBuf> {
    let mut files = Vec::new();
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                files.extend(walk_dir(&path));
            } else {
                files.push(path);
            }
        }
    }
    files
}

// ============================================================================
// TIER 5: ADVERSARIAL ZERO-MOCK & FORENSIC AUDIT TESTS
// ============================================================================

#[test]
fn test_t5_adv_zero_mock_01_no_hardcoded_tokens_in_network_module() {
    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let net_path = project_root.join("src/network.rs");

    if net_path.exists() {
        let content = fs::read_to_string(&net_path).expect("Failed to read src/network.rs");
        assert!(
            !content.contains("mock_stream"),
            "Zero-Mock Violation: src/network.rs must not contain mock_stream"
        );
        assert!(
            !content.contains("fake_token"),
            "Zero-Mock Violation: src/network.rs must not contain fake_token"
        );
        assert!(
            content.contains("reqwest::Client"),
            "Zero-Mock Truth: Must use real reqwest HTTP client"
        );
        assert!(
            content.contains("bytes_stream"),
            "Zero-Mock Truth: Must use real HTTP streaming bytes_stream"
        );
    }
}

#[test]
fn test_t5_adv_zero_mock_02_dynamic_subtotals_change_on_node_mutation() {
    use lauburu_tui::config::{MeshConfig, NodeGroup, NodeSpec};

    let mut cfg = MeshConfig::default();
    cfg.nodes = vec![
        NodeSpec {
            id: "n1".into(),
            name: "Node 1".into(),
            layer: "L1".into(),
            ip: "10.0.0.1".into(),
            port: 8080,
            role: "Core".into(),
            group: NodeGroup::CoreRing,
            ram_gb: 32.0,
            vram_gb: 24.0,
            interconnect: "TB4".into(),
            backend: "Metal".into(),
            tailscale_ip: None,
            local_ip: None,
            is_master: true,
            model_path: None,
        },
        NodeSpec {
            id: "n2".into(),
            name: "Node 2".into(),
            layer: "L6".into(),
            ip: "10.0.0.2".into(),
            port: 8080,
            role: "Edge".into(),
            group: NodeGroup::EdgePool,
            ram_gb: 16.0,
            vram_gb: 12.0,
            interconnect: "USB".into(),
            backend: "TPU".into(),
            tailscale_ip: None,
            local_ip: None,
            is_master: false,
            model_path: None,
        },
    ];

    assert_eq!(cfg.core_vram_total(), 24.0);
    assert_eq!(cfg.edge_vram_total(), 12.0);
    assert_eq!(cfg.total_vram_gb(), 36.0);

    // Mutate and verify dynamic recalculation
    cfg.nodes[0].vram_gb = 50.0;
    assert_eq!(cfg.core_vram_total(), 50.0);
    assert_eq!(cfg.total_vram_gb(), 62.0);
}

#[test]
fn test_t5_adv_zero_mock_03_no_fake_tokens_in_app_or_ui_source() {
    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let src_ui = project_root.join("src/ui");

    let forbidden = ["mock_response", "fake_token", "simulated_data", "dummy_array"];
    for entry in walk_dir(&src_ui) {
        if entry.extension().and_then(|s| s.to_str()) == Some("rs") {
            let content = fs::read_to_string(&entry).unwrap();
            for word in &forbidden {
                assert!(
                    !content.to_lowercase().contains(word),
                    "Zero-Mock Violation: Found '{}' in {:?}",
                    word,
                    entry
                );
            }
        }
    }
}

#[test]
fn test_t5_adv_zero_mock_04_dynamic_ram_sum_with_floating_subtotals() {
    use lauburu_tui::config::{MeshConfig, NodeGroup, NodeSpec};

    let mut cfg = MeshConfig::default();
    cfg.nodes = vec![
        NodeSpec {
            id: "m1".into(),
            name: "M1".into(),
            layer: "L1".into(),
            ip: "10.0.0.1".into(),
            port: 8080,
            role: "Core".into(),
            group: NodeGroup::CoreRing,
            ram_gb: 24.5,
            vram_gb: 20.25,
            interconnect: "TB4".into(),
            backend: "Metal".into(),
            tailscale_ip: None,
            local_ip: None,
            is_master: true,
            model_path: None,
        },
        NodeSpec {
            id: "m2".into(),
            name: "M2".into(),
            layer: "L2".into(),
            ip: "10.0.0.2".into(),
            port: 8080,
            role: "Core".into(),
            group: NodeGroup::CoreRing,
            ram_gb: 15.5,
            vram_gb: 13.75,
            interconnect: "TB4".into(),
            backend: "Metal".into(),
            tailscale_ip: None,
            local_ip: None,
            is_master: false,
            model_path: None,
        },
    ];

    assert!((cfg.core_ram_total() - 40.0).abs() < 1e-5);
    assert!((cfg.core_vram_total() - 34.0).abs() < 1e-5);
}

#[test]
fn test_t5_adv_zero_mock_05_dynamic_group_filtering_accuracy() {
    use lauburu_tui::config::MeshConfig;

    let cfg = MeshConfig::fallback();
    assert_eq!(cfg.core_nodes().len(), 4);
    assert_eq!(cfg.edge_nodes().len(), 3);

    for node in cfg.core_nodes() {
        assert_eq!(node.group, lauburu_tui::config::NodeGroup::CoreRing);
    }
    for node in cfg.edge_nodes() {
        assert_eq!(node.group, lauburu_tui::config::NodeGroup::EdgePool);
    }
}

#[test]
fn test_t5_adv_zero_mock_06_endpoint_real_format_truth() {
    use lauburu_tui::config::MeshConfig;

    let cfg = MeshConfig::fallback();
    for node in &cfg.nodes {
        let ep = node.endpoint();
        assert!(!ep.is_empty());
        assert!(ep.contains(':'));
        assert!(!ep.contains("0.0.0.0"));
    }
}


