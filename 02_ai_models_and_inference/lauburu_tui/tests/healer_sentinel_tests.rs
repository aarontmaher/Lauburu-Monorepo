// =============================================================================
// Comprehensive Test Suite for Autonomic Sentinel & 6-Tier Transports
// Features F17, F18, F19
// =============================================================================

use lauburu_tui::app::{App, Tab};
use lauburu_tui::config::MeshConfig;
use lauburu_tui::healer::{ClusterVitality, DirectiveType, HealerState, InProcessHealer};
use lauburu_tui::transports::{
    CascadingTransportManager, TransportLink, TransportStatus, TransportTier,
};
use lauburu_tui::ui::render;
use ratatui::backend::TestBackend;
use ratatui::Terminal;

#[test]
fn test_canonical_7_node_transport_matrix() {
    let mgr = CascadingTransportManager::new_canonical_7_nodes();
    assert!(!mgr.links.is_empty(), "Canonical transport matrix must contain links");

    // Check that Mac Mini host has active loopback
    let mac_tier = mgr.active_tier_for_node("mac_host");
    assert_eq!(mac_tier, Some(TransportTier::Tier6UnixSocket));

    // Check that MBP has TB4 DMA active
    let mbp_tier = mgr.active_tier_for_node("macbook_pro");
    assert_eq!(mbp_tier, Some(TransportTier::Tier1ThunderboltDma));

    // Check that Linux Head Node has Dual-Subnet Ethernet active
    let linux_tier = mgr.active_tier_for_node("linux_head_node");
    assert_eq!(linux_tier, Some(TransportTier::Tier2DualEthernet));

    // Check that mobile nodes have USB-C ADB Tunnel active
    let pixel_tier = mgr.active_tier_for_node("pixel_10");
    assert_eq!(pixel_tier, Some(TransportTier::Tier4AdbUsbTunnel));

    let samsung_tier = mgr.active_tier_for_node("samsung_s20");
    assert_eq!(samsung_tier, Some(TransportTier::Tier4AdbUsbTunnel));
}

#[test]
fn test_cascading_transport_failover() {
    let mut mgr = CascadingTransportManager::new_canonical_7_nodes();

    // Primary route for MBP is TB4 DMA (Tier 1)
    assert_eq!(mgr.active_tier_for_node("macbook_pro"), Some(TransportTier::Tier1ThunderboltDma));

    // Trigger cascading failover
    let next_tier = mgr.failover_next_tier("macbook_pro");
    assert_eq!(next_tier, Some(TransportTier::Tier2DualEthernet));
    assert_eq!(mgr.active_tier_for_node("macbook_pro"), Some(TransportTier::Tier2DualEthernet));

    // Check link status
    let links = mgr.get_links_for_node("macbook_pro");
    let tb4_link = links.iter().find(|l| l.tier == TransportTier::Tier1ThunderboltDma).unwrap();
    let eth_link = links.iter().find(|l| l.tier == TransportTier::Tier2DualEthernet).unwrap();

    assert_eq!(tb4_link.status, TransportStatus::Offline);
    assert!(!tb4_link.is_active_route);
    assert_eq!(eth_link.status, TransportStatus::Active);
    assert!(eth_link.is_active_route);
}

#[test]
fn test_offline_micro_ai_healing_diagnostics() {
    let mut healer = InProcessHealer::default();
    let mut mgr = CascadingTransportManager::new_canonical_7_nodes();

    // Initial diagnosis on healthy cluster
    let initial_directives = healer.diagnose(&mgr);
    assert!(initial_directives.is_empty(), "Healthy cluster produces zero fault directives");

    // Degrade Linux head node transport
    mgr.record_probe("linux_head_node", TransportTier::Tier2DualEthernet, 120.0, false);
    mgr.record_probe("linux_head_node", TransportTier::Tier2DualEthernet, 150.0, false);

    let degraded_directives = healer.diagnose(&mgr);
    assert!(!degraded_directives.is_empty(), "Degraded link triggers healing directive");
    assert_eq!(degraded_directives[0].directive_type, DirectiveType::CycleInterface);
        assert_eq!(degraded_directives[0].target_node_id, "linux_head_node");

        // Simulate 3rd failure with auto_failover disabled to test offline directive detection
        mgr.auto_failover_enabled = false;
        mgr.record_probe("linux_head_node", TransportTier::Tier2DualEthernet, 999.0, false);
        let offline_directives = healer.diagnose(&mgr);
        assert!(!offline_directives.is_empty(), "Offline active link triggers migration directive");
        assert_eq!(offline_directives[0].directive_type, DirectiveType::MigrateTransportTier);
    }

#[test]
fn test_cluster_vitality_and_resilience_scoring() {
    let healer = InProcessHealer::default();
    let mgr = CascadingTransportManager::new_canonical_7_nodes();

    let vitality = healer.calculate_vitality(&mgr);
    assert_eq!(vitality.total_nodes, 7);
    assert_eq!(vitality.active_nodes, 7);
    assert!(vitality.overall_score_pct >= 95.0);
    assert!(vitality.offline_resilience_index >= 0.90);
    assert_eq!(vitality.active_master_id, "mac_host");
}

#[test]
fn test_all_8_tabs_navigation_cycle() {
    let config = MeshConfig::fallback();
    let mut app = App::new(config);

    assert_eq!(app.current_tab, Tab::Topology);
    assert_eq!(Tab::all().len(), 8);

    // Step through tabs 0 to 7
    for i in 0..8 {
        assert_eq!(app.current_tab.index(), i);
        app.next_tab();
    }
    // Should wrap back to 0
    assert_eq!(app.current_tab, Tab::Topology);

    // Direct tab switches
    app.switch_tab(Tab::Healer);
    assert_eq!(app.current_tab, Tab::Healer);
    assert_eq!(app.current_tab.title(), "[8] Autonomic Sentinel");

    app.prev_tab();
    assert_eq!(app.current_tab, Tab::VoiceCoding);
}

#[test]
fn test_autonomic_sentinel_tab_renders_cleanly() {
    let backend = TestBackend::new(160, 40);
    let mut terminal = Terminal::new(backend).unwrap();

    let mut app = App::new(MeshConfig::fallback());
    app.switch_tab(Tab::Healer);

    terminal
        .draw(|frame| {
            render(&mut app, frame);
        })
        .unwrap();

    let buffer = terminal.backend().buffer();
    let rendered_text: String = buffer
        .content
        .iter()
        .map(|cell| cell.symbol())
        .collect();

    // Verify Tab 8 Elements
    assert!(
        rendered_text.contains("Cluster Vitality Index"),
        "Must render Cluster Vitality Gauge"
    );
    assert!(
        rendered_text.contains("Offline Resilience"),
        "Must render Offline Resilience panel"
    );
    assert!(
        rendered_text.contains("Master Coordinator"),
        "Must render Master Coordinator banner"
    );
    assert!(
        rendered_text.contains("6-Tier Cascading Physical Transport Matrix"),
        "Must render 6-tier transport matrix table"
    );
    assert!(
        rendered_text.contains("Micro-AI Autonomic Decision Stream"),
        "Must render autonomic decision stream"
    );
    assert!(
        rendered_text.contains("Cascading Physical Fallback Pipeline"),
        "Must render fallback pipeline diagram"
    );

    // Verify canonical endpoints appear in table
    assert!(rendered_text.contains("mac_host"), "Must render mac_host");
    assert!(rendered_text.contains("macbook_pro"), "Must render macbook_pro");
    assert!(rendered_text.contains("linux_head_node"), "Must render linux_head_node");
    assert!(rendered_text.contains("TB4 DMA Bridge"), "Must render TB4 tier");
}
