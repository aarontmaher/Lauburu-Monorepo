//! ============================================================================
//! Empirical Challenger 2 Verification & Adversarial Stress Suite (Milestone 2)
//! ============================================================================

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use lauburu_tui::app::{ActiveTopologyTable, App, Tab};
use lauburu_tui::config::{MeshConfig, NodeGroup};
use lauburu_tui::ui;
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use std::path::Path;

fn buffer_to_string(terminal: &Terminal<TestBackend>) -> String {
    let buffer = terminal.backend().buffer();
    let mut out = String::new();
    for y in 0..buffer.area.height {
        for x in 0..buffer.area.width {
            let cell = buffer.cell((x, y)).unwrap();
            out.push_str(cell.symbol());
        }
        out.push('\n');
    }
    out
}

#[test]
fn test_challenger_01_canonical_7node_hardware_matrix() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let mesh_toml_path = Path::new(manifest_dir).join("config/mesh.toml");
    let config = MeshConfig::load_from_path(&mesh_toml_path).unwrap();

    assert_eq!(config.nodes.len(), 7);

    // Node 1: Mac Mini (M4 Pro)
    let n1 = &config.nodes[0];
    assert_eq!(n1.name, "Mac Mini (M4 Pro)");
    assert_eq!(n1.layer, "L1");
    assert_eq!(n1.ram_gb, 24.0);
    assert_eq!(n1.vram_gb, 21.6);
    assert_eq!(n1.group, NodeGroup::CoreRing);
    assert!(n1.is_master);

    // Node 2: MacBook Pro (M1 Max)
    let n2 = &config.nodes[1];
    assert_eq!(n2.name, "MacBook Pro (M1 Max)");
    assert_eq!(n2.layer, "L2");
    assert_eq!(n2.ram_gb, 16.0);
    assert_eq!(n2.vram_gb, 14.0);
    assert_eq!(n2.group, NodeGroup::CoreRing);

    // Node 3: MacBook Air (M4)
    let n3 = &config.nodes[2];
    assert_eq!(n3.name, "MacBook Air (M4)");
    assert_eq!(n3.layer, "L5");
    assert_eq!(n3.ram_gb, 16.0);
    assert_eq!(n3.vram_gb, 14.0);
    assert_eq!(n3.group, NodeGroup::CoreRing);

    // Node 4: Linux Head Node (Ryzen 7)
    let n4 = &config.nodes[3];
    assert_eq!(n4.name, "Linux Head Node (Ryzen 7)");
    assert_eq!(n4.layer, "L3");
    assert_eq!(n4.ram_gb, 16.0);
    assert_eq!(n4.vram_gb, 13.8);
    assert_eq!(n4.group, NodeGroup::CoreRing);

    // Node 5: Pixel 10 Pro XL (Tensor G5)
    let n5 = &config.nodes[4];
    assert_eq!(n5.name, "Pixel 10 Pro XL (Tensor G5)");
    assert_eq!(n5.layer, "L6");
    assert_eq!(n5.ram_gb, 16.0);
    assert_eq!(n5.vram_gb, 12.5);
    assert_eq!(n5.group, NodeGroup::EdgePool);

    // Node 6: Samsung S20 (Exynos 990)
    let n6 = &config.nodes[5];
    assert_eq!(n6.name, "Samsung S20 (Exynos 990)");
    assert_eq!(n6.layer, "L7");
    assert_eq!(n6.ram_gb, 12.0);
    assert_eq!(n6.vram_gb, 9.0);
    assert_eq!(n6.group, NodeGroup::EdgePool);

    // Node 7: Linux Tablet (Touch x86_64)
    let n7 = &config.nodes[6];
    assert_eq!(n7.name, "Linux Tablet (Touch x86_64)");
    assert_eq!(n7.layer, "L4");
    assert_eq!(n7.ram_gb, 8.0);
    assert_eq!(n7.vram_gb, 6.0);
    assert_eq!(n7.group, NodeGroup::EdgePool);

    // Aggregates
    assert_eq!(config.total_ram_gb(), 108.0);
    assert!((config.total_vram_gb() - 90.9).abs() < 1e-6);
    assert!((config.core_vram_total() - 63.4).abs() < 1e-6);
    assert!((config.edge_vram_total() - 27.5).abs() < 1e-6);
}

#[test]
fn test_challenger_02_tab1_buffer_renders_authentic_topology() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let mesh_toml_path = Path::new(manifest_dir).join("config/mesh.toml");
    let config = MeshConfig::load_from_path(&mesh_toml_path).unwrap();

    let backend = TestBackend::new(200, 45);
    let mut terminal = Terminal::new(backend).unwrap();

    let mut app = App::new(config);
    app.current_tab = Tab::Topology;

    terminal.draw(|f| ui::render(&mut app, f)).unwrap();
    let rendered = buffer_to_string(&terminal);

    // Header assertions
    assert!(rendered.contains("Lauburu Heterogeneous AI Mesh"));
    assert!(rendered.contains("[1] Ring Topology"));
    assert!(rendered.contains("[2] Chat Stream"));
    assert!(rendered.contains("108.0 GB"));
    assert!(rendered.contains("90.9 GB"));
    assert!(rendered.contains("(82.8G usable)"));

    // ASCII flow diagram assertions
    assert!(rendered.contains("Pipelined-Ring Parallelism (PRP) Flow"));
    assert!(rendered.contains("[L1: Mac Mini M4]"));
    assert!(rendered.contains("[L2: MBP M1 Max]"));
    assert!(rendered.contains("[L5: MBA M4]"));
    assert!(rendered.contains("[L3: Linux Node]"));

    // Table titles
    assert!(rendered.contains("Core PRP Ring Nodes (63.4 GB VRAM / 72.0 GB RAM)"));
    assert!(rendered.contains("Edge RPC Pool (27.5 GB VRAM)"));

    // Capabilities matrix
    assert!(rendered.contains("Cluster Architecture & Dynamic Capabilities"));
    assert!(rendered.contains("Pooled RAM:          108.0 GB (Core: 72.0 GB │ Edge: 36.0 GB)"));
    assert!(rendered.contains("Total AI VRAM:       90.9 GB (82.8 GB Usable)"));
    assert!(rendered.contains("Master Coordinator:  Mac Mini (M4 Pro) (127.0.0.1:8082) [L1]"));

    // Check for absence of synthetic mock tokens
    let forbidden = ["mock_response", "fake_stream", "dummy_token", "simulated_reply", "lorem ipsum", "example.com"];
    let rendered_lower = rendered.to_lowercase();
    for word in forbidden {
        assert!(
            !rendered_lower.contains(word),
            "Rendered buffer contains forbidden pattern '{}'",
            word
        );
    }
}

#[test]
fn test_challenger_03_dynamic_mutation_oracle_proves_no_hardcoding() {
    let mut config = MeshConfig::fallback();
    config.nodes[0].name = "Studio_M4".to_string();
    config.nodes[0].ram_gb = 128.0;
    config.nodes[0].vram_gb = 96.0;
    config.nodes[0].port = 9090;

    let backend = TestBackend::new(200, 45);
    let mut terminal = Terminal::new(backend).unwrap();

    let mut app = App::new(config);
    terminal.draw(|f| ui::render(&mut app, f)).unwrap();
    let rendered = buffer_to_string(&terminal);

    println!("=== DYNAMIC MUTATION BUFFER ===\n{}", rendered);

    assert!(rendered.contains("Studio_M4"));
    assert!(rendered.contains("127.0.0.1:9090"));
    assert!(rendered.contains("96.0 GB"));
    assert!(rendered.contains("128.0 GB"));
    assert!(rendered.contains("137.8 GB VRAM")); // 96 + 14 + 14 + 13.8 = 137.8
    assert!(rendered.contains("176.0 GB RAM"));  // 128 + 16 + 16 + 16 = 176
}

#[test]
fn test_challenger_04_topology_table_navigation_and_wrapping() {
    let config = MeshConfig::fallback();
    let mut app = App::new(config);

    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
    assert_eq!(app.core_table_state.selected(), Some(0));

    // Down navigation in Core table
    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.core_table_state.selected(), Some(1));

    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.core_table_state.selected(), Some(2));

    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.core_table_state.selected(), Some(3));

    // Wrap around to 0
    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.core_table_state.selected(), Some(0));

    // Up wraps to 3
    app.handle_key(KeyEvent::new(KeyCode::Up, KeyModifiers::NONE));
    assert_eq!(app.core_table_state.selected(), Some(3));

    // Focus switch to Edge table
    app.handle_key(KeyEvent::new(KeyCode::Right, KeyModifiers::NONE));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);
    assert_eq!(app.edge_table_state.selected(), Some(0));

    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.edge_table_state.selected(), Some(1));

    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.edge_table_state.selected(), Some(2));

    // Wrap around in Edge table
    app.handle_key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE));
    assert_eq!(app.edge_table_state.selected(), Some(0));

    // Focus switch back to Core
    app.handle_key(KeyEvent::new(KeyCode::Left, KeyModifiers::NONE));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
}

#[test]
fn test_challenger_05_adversarial_viewport_dimensions() {
    let test_dimensions = [
        (0, 0),
        (1, 1),
        (10, 5),
        (49, 11),
        (50, 12),
        (80, 24),
        (120, 30),
        (250, 100),
    ];

    for (w, h) in test_dimensions {
        let backend = TestBackend::new(w, h);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut app = App::new(MeshConfig::fallback());

        let draw_res = terminal.draw(|f| ui::render(&mut app, f));
        assert!(
            draw_res.is_ok(),
            "Rendering at dimension {}x{} must not panic",
            w,
            h
        );

        if w < ui::MIN_VIEWPORT_WIDTH || h < ui::MIN_VIEWPORT_HEIGHT {
            let rendered = buffer_to_string(&terminal);
            if w >= 25 && h >= 3 {
                assert!(
                    rendered.contains("Viewport Too Small"),
                    "Micro-viewport {}x{} must display fallback warning",
                    w,
                    h
                );
            }
        }
    }
}
