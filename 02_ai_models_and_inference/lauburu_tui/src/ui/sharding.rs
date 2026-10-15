//! ============================================================================
//! Unified AI Sharding View (Tab 3) - Ratatui UI Implementation
//! ============================================================================

use crate::app::App;
use crate::sharding::{ShardingFocus, ShardingProtocol};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Cell, Paragraph, Row, Table};
use ratatui::Frame;

/// Render the Unified AI Sharding protocol view (Tab 3).
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let outer_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Cyan))
        .title(Span::styled(
            " 🔀 Unified AI Sharding Protocol Matrix ",
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ));

    let inner = outer_block.inner(area);
    frame.render_widget(outer_block, area);

    // 3-tier vertical division
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(7),      // Upper: Flowchart Banner & Telemetry
            Constraint::Percentage(50), // Middle: Dynamic Model Routing Matrix
            Constraint::Percentage(50), // Lower: 7-Layer Node Capabilities Matrix
        ])
        .split(inner);

    render_decision_flowchart(app, frame, chunks[0]);
    render_model_routing_table(app, frame, chunks[1]);
    render_node_sharding_table(app, frame, chunks[2]);
}

/// 1. Upper: Unified AI Sharding Decision Tree Flowchart & Interconnect Hierarchy
fn render_decision_flowchart(app: &App, frame: &mut Frame, area: Rect) {
    let total_vram = app.sharding_state.total_vram_gb();
    let usable_vram = app.sharding_state.usable_vram_gb();
    let apple_pool = app.sharding_state.apple_pool_vram_gb();

    let tree_lines = vec![
        Line::from(vec![
            Span::styled("Decision Tree: ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("10Gbps TB4 DMA (0.27ms RTT) ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("──► ", Style::default().fg(Color::DarkGray)),
            Span::styled("Exo P2P MLX Ring (49.6 GB) ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::styled("──► ", Style::default().fg(Color::DarkGray)),
            Span::styled("Petals DHT Swarm (82.8 GB) ", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
            Span::styled("──► ", Style::default().fg(Color::DarkGray)),
            Span::styled("Local Standalone (21.6 GB)", Style::default().fg(Color::LightBlue)),
        ]),
        Line::from(vec![
            Span::styled("Mesh VRAM Pool: ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{:.1} GB Total ({:.1} GB Usable)", total_vram, usable_vram),
                Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
            ),
            Span::styled(" │ Apple Silicon Sub-Pool: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{:.1} GB", apple_pool), Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
            Span::styled(" │ Core Shard Tier: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{:.1} GB", app.mesh_config.core_vram_total()), Style::default().fg(Color::LightYellow)),
            Span::styled(" │ Edge RPC Tier: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{:.1} GB", app.mesh_config.edge_vram_total()), Style::default().fg(Color::LightRed)),
        ]),
        Line::from(vec![
            Span::styled("Active Interconnect: ", Style::default().fg(Color::Gray)),
            Span::styled("TB4 Link: ", Style::default().fg(Color::White)),
            if app.sharding_state.tb4_link_up {
                Span::styled(format!("[ACTIVE {:.2}ms RTT]", app.sharding_state.tb4_rtt_ms), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
            } else {
                Span::styled("[OFFLINE]", Style::default().fg(Color::Red))
            },
            Span::styled(" │ Exo Cluster: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("[{} Apple Nodes Online]", app.sharding_state.apple_silicon_nodes_online), Style::default().fg(Color::Cyan)),
            Span::styled(" │ Petals DHT: ", Style::default().fg(Color::Gray)),
            if app.sharding_state.petals_bootstrap_connected {
                Span::styled("[CONNECTED :50053]", Style::default().fg(Color::Magenta))
            } else {
                Span::styled("[DISCONNECTED]", Style::default().fg(Color::Yellow))
            },
        ]),
    ];

    let tree_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(
            " ⚡ Unified AI Sharding Decision Flow & Interconnect Hierarchy ",
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ));

    let tree_widget = Paragraph::new(tree_lines).block(tree_block);
    frame.render_widget(tree_widget, area);
}

/// 2. Middle: Dynamic Model-to-Protocol Routing Matrix Table
fn render_model_routing_table(app: &mut App, frame: &mut Frame, area: Rect) {
    let is_focused = app.sharding_state.active_focus == ShardingFocus::RoutingMatrix;

    let border_color = if is_focused { Color::Cyan } else { Color::DarkGray };
    let title_style = if is_focused {
        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(Color::Gray)
    };

    let title_text = if is_focused {
        " ▶ Dynamic Model-to-Protocol Routing Matrix (F5) [ACTIVE FOCUS] "
    } else {
        " Dynamic Model-to-Protocol Routing Matrix (F5) "
    };

    let header_cells = [
        "Model Name",
        "Size",
        "Quant",
        "Mem Req",
        "Optimal Protocol",
        "Nodes",
        "Target Interconnect",
        "Est. Latency",
        "Throughput",
    ]
    .iter()
    .map(|h| Cell::from(*h).style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)));

    let header = Row::new(header_cells).height(1).bottom_margin(0);

    let rows: Vec<Row> = app
        .sharding_state
        .routing_specs
        .iter()
        .map(|spec| {
            let (protocol_tag, protocol_color) = match spec.optimal_protocol {
                ShardingProtocol::LlamaRpcTb4 => ("TB4-RPC", Color::Green),
                ShardingProtocol::ExoP2pMlx => ("EXO-MLX", Color::Cyan),
                ShardingProtocol::PetalsDht => ("PETALS-DHT", Color::Magenta),
                ShardingProtocol::LocalStandalone => ("LOCAL-SOLO", Color::LightBlue),
                ShardingProtocol::AccelerateFsdp => ("HF-FSDP", Color::Yellow),
                ShardingProtocol::UnsupportedOom => ("OOM-BLOCK", Color::Red),
            };

            let cells = vec![
                Cell::from(spec.model_name.as_str()).style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Cell::from(spec.parameter_size.as_str()).style(Style::default().fg(Color::Yellow)),
                Cell::from(spec.quantization.as_str()).style(Style::default().fg(Color::LightGreen)),
                Cell::from(format!("{:.1} GB", spec.memory_req_gb)).style(Style::default().fg(Color::LightCyan)),
                Cell::from(Line::from(vec![
                    Span::styled(format!("[{}] ", protocol_tag), Style::default().fg(protocol_color).add_modifier(Modifier::BOLD)),
                    Span::styled(spec.optimal_protocol.display_name(), Style::default().fg(protocol_color)),
                ])),
                Cell::from(if spec.min_nodes == 0 { "—".to_string() } else { format!("{} Node{}", spec.min_nodes, if spec.min_nodes > 1 { "s" } else { "" }) })
                    .style(Style::default().fg(Color::Gray)),
                Cell::from(spec.target_interconnect.as_str()).style(Style::default().fg(Color::DarkGray)),
                Cell::from(if spec.est_latency_ms > 0.0 { format!("~{:.0} ms", spec.est_latency_ms) } else { "N/A".to_string() })
                    .style(Style::default().fg(Color::LightMagenta)),
                Cell::from(if spec.est_throughput_tps > 0.0 { format!("~{:.0} tok/s", spec.est_throughput_tps) } else { "0.0 tok/s".to_string() })
                    .style(Style::default().fg(Color::Green)),
            ];

            Row::new(cells).height(1)
        })
        .collect();

    let widths = [
        Constraint::Percentage(20), // Model Name
        Constraint::Length(7),      // Size
        Constraint::Length(9),      // Quant
        Constraint::Length(9),      // Mem Req
        Constraint::Percentage(25), // Optimal Protocol
        Constraint::Length(9),      // Nodes
        Constraint::Percentage(18), // Interconnect
        Constraint::Length(9),      // Latency
        Constraint::Length(11),     // Throughput
    ];

    let table = Table::new(rows, widths)
        .header(header)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(border_color))
                .title(Span::styled(title_text, title_style)),
        )
        .row_highlight_style(
            Style::default()
                .bg(Color::Rgb(30, 40, 60))
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol(if is_focused { "▶ " } else { "  " });

    frame.render_stateful_widget(table, area, &mut app.sharding_state.routing_table_state);
}

/// 3. Lower: 7-Layer Node Capabilities & Sharding Matrix Table
fn render_node_sharding_table(app: &mut App, frame: &mut Frame, area: Rect) {
    let is_focused = app.sharding_state.active_focus == ShardingFocus::NodeMatrix;

    let border_color = if is_focused { Color::Cyan } else { Color::DarkGray };
    let title_style = if is_focused {
        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(Color::Gray)
    };

    let title_text = if is_focused {
        " ▶ 7-Layer Node Capabilities & Sharding Matrix (F4) [ACTIVE FOCUS] "
    } else {
        " 7-Layer Node Capabilities & Sharding Matrix (F4) "
    };

    let header_cells = [
        "Layer",
        "Node Name",
        "Endpoint / Interconnect",
        "VRAM",
        "Cap %",
        "MLX?",
        "llama-RPC Role",
        "Petals Role",
        "Shard Alloc",
    ]
    .iter()
    .map(|h| Cell::from(*h).style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)));

    let header = Row::new(header_cells).height(1).bottom_margin(0);

    let rows: Vec<Row> = app
        .sharding_state
        .node_capabilities
        .iter()
        .map(|node| {
            let mlx_badge = if node.mlx_supported {
                Span::styled("✅ Yes", Style::default().fg(Color::Green))
            } else {
                Span::styled("❌ No", Style::default().fg(Color::DarkGray))
            };

            let rpc_color = match node.llama_rpc_role.as_str() {
                "Master Server" => Color::Green,
                "RPC Worker" => Color::LightCyan,
                _ => Color::DarkGray,
            };

            let petals_color = match node.petals_role.as_str() {
                "Client Ingress" => Color::Green,
                "Bootstrap Anchor" => Color::Magenta,
                "Edge TPU Worker" => Color::Yellow,
                "Worker" => Color::LightBlue,
                _ => Color::DarkGray,
            };

            let cells = vec![
                Cell::from(node.layer.as_str()).style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Cell::from(node.name.as_str()).style(Style::default().fg(Color::White)),
                Cell::from(format!("{} ({})", node.endpoint, node.interconnect)).style(Style::default().fg(Color::Gray)),
                Cell::from(format!("{:.1} GB", node.vram_gb)).style(Style::default().fg(Color::LightGreen)),
                Cell::from(format!("{}%", node.dynamic_cap_pct)).style(Style::default().fg(Color::LightYellow)),
                Cell::from(Line::from(vec![mlx_badge])),
                Cell::from(node.llama_rpc_role.as_str()).style(Style::default().fg(rpc_color)),
                Cell::from(node.petals_role.as_str()).style(Style::default().fg(petals_color)),
                Cell::from(format!("{:.1} GB", node.allocated_shard_gb)).style(Style::default().fg(Color::Cyan)),
            ];

            Row::new(cells).height(1)
        })
        .collect();

    let widths = [
        Constraint::Length(7),      // Layer
        Constraint::Percentage(18), // Node Name
        Constraint::Percentage(26), // Endpoint / Interconnect
        Constraint::Length(9),      // VRAM
        Constraint::Length(7),      // Cap %
        Constraint::Length(8),      // MLX?
        Constraint::Percentage(14), // llama-RPC
        Constraint::Percentage(14), // Petals
        Constraint::Length(11),     // Shard Alloc
    ];

    let table = Table::new(rows, widths)
        .header(header)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(border_color))
                .title(Span::styled(title_text, title_style)),
        )
        .row_highlight_style(
            Style::default()
                .bg(Color::Rgb(30, 40, 60))
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol(if is_focused { "▶ " } else { "  " });

    frame.render_stateful_widget(table, area, &mut app.sharding_state.node_table_state);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::MeshConfig;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

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
    fn test_sharding_view_renders_all_three_tiers() {
        let backend = TestBackend::new(180, 45);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(crate::app::Tab::Sharding);

        terminal
            .draw(|frame| {
                render(&mut app, frame, Rect::new(0, 0, 180, 45));
            })
            .unwrap();

        let rendered = buffer_to_string(&terminal);

        // Tier 1: Flowchart & Decision Tree
        assert!(rendered.contains("Unified AI Sharding Decision Flow"));
        assert!(rendered.contains("10Gbps TB4 DMA"));
        assert!(rendered.contains("(82.8 GB Usable)"));
        assert!(rendered.contains("49.6 GB"));
        assert!(rendered.contains("49.6 GB"));

        // Tier 2: Dynamic Model Routing Matrix Table
        assert!(rendered.contains("Dynamic Model-to-Protocol Routing Matrix"));
        assert!(rendered.contains("Qwen2.5-7B-Instruct"));
        assert!(rendered.contains("DeepSeek-R1-Distill-32B"));
        assert!(rendered.contains("Q4_K_M"));
        assert!(rendered.contains("TB4-RPC"));

        // Tier 3: 7-Layer Node Capabilities Matrix Table
        assert!(rendered.contains("7-Layer Node Capabilities & Sharding Matrix"));
        assert!(rendered.contains("Mac_Node") || rendered.contains("Mac Mini"));
        assert!(rendered.contains("L1"));
        assert!(rendered.contains("L2"));
        assert!(rendered.contains("L7"));
    }

    #[test]
    fn test_sharding_view_focus_toggle_renders_active_indicators() {
        let backend = TestBackend::new(180, 45);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(crate::app::Tab::Sharding);

        // Initially RoutingMatrix is focused
        assert_eq!(app.sharding_state.active_focus, ShardingFocus::RoutingMatrix);
        terminal
            .draw(|frame| {
                render(&mut app, frame, Rect::new(0, 0, 180, 45));
            })
            .unwrap();
        let rendered1 = buffer_to_string(&terminal);
        assert!(rendered1.contains("Dynamic Model-to-Protocol Routing Matrix (F5) [ACTIVE FOCUS]"));

        // Toggle focus to NodeMatrix
        app.sharding_state.toggle_focus();
        assert_eq!(app.sharding_state.active_focus, ShardingFocus::NodeMatrix);
        terminal
            .draw(|frame| {
                render(&mut app, frame, Rect::new(0, 0, 180, 45));
            })
            .unwrap();
        let rendered2 = buffer_to_string(&terminal);
        assert!(rendered2.contains("7-Layer Node Capabilities & Sharding Matrix (F4) [ACTIVE FOCUS]"));
    }

    #[test]
    fn test_sharding_view_small_viewport_does_not_panic() {
        let small_dims = [(50, 15), (60, 20), (80, 24), (200, 60)];
        for (w, h) in small_dims {
            let backend = TestBackend::new(w, h);
            let mut terminal = Terminal::new(backend).unwrap();
            let mut app = App::new(MeshConfig::fallback());
            app.switch_tab(crate::app::Tab::Sharding);

            let res = terminal.draw(|frame| {
                render(&mut app, frame, Rect::new(0, 0, w, h));
            });
            assert!(res.is_ok(), "Sharding view rendering at {}x{} must not panic", w, h);
        }
    }
}
