use crate::app::{ActiveTopologyTable, App};
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{
    Block, BorderType, Borders, Cell, Paragraph, Row, Table,
};
use ratatui::Frame;

/// Render Tab 1: Ring Topology View (Core PRP Ring + Edge RPC Pool + Capabilities Matrix).
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let main_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
        .split(area);

    render_core_ring_pane(app, frame, main_chunks[0]);
    render_edge_pool_pane(app, frame, main_chunks[1]);
}

fn probe_endpoint(host: &str, port: u16, timeout_ms: u64) -> (bool, Option<f64>) {
    use std::net::{TcpStream, ToSocketAddrs};
    use std::time::{Duration, Instant};

    let addr_str = format!("{}:{}", host, port);
    let start = Instant::now();
    if let Ok(mut addrs) = addr_str.to_socket_addrs() {
        if let Some(addr) = addrs.next() {
            if let Ok(_) = TcpStream::connect_timeout(&addr, Duration::from_millis(timeout_ms)) {
                let elapsed = start.elapsed().as_secs_f64() * 1000.0;
                return (true, Some((elapsed * 10.0).round() / 10.0));
            }
        }
    }
    (false, None)
}

/// Render left pane: Core PRP Ring (Token-Flow Diagram + Node Table).
fn render_core_ring_pane(app: &mut App, frame: &mut Frame, area: Rect) {
    let left_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(8), Constraint::Min(8)])
        .split(area);

    // 1. Upper: Unicode/ASCII Ring Pipeline Diagram
    let is_core_focused = app.active_topology_table == ActiveTopologyTable::Core;
    let diagram_border_color = if is_core_focused {
        Color::Cyan
    } else {
        Color::DarkGray
    };

    let diagram_block = Block::default()
        .title(Span::styled(
            " ⭕ Pipelined-Ring Parallelism (PRP) Flow ",
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(diagram_border_color));

    let diagram_lines = vec![
        Line::from(vec![
            Span::styled(" [L1: Mac Mini M4] ", Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
            Span::styled("──────(10Gbps TB4 DMA 0.28ms)─────> ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("[L2: MBP Intel Vault] ", Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("        ▲                                                      │", Style::default().fg(Color::Yellow)),
        ]),
        Line::from(vec![
            Span::styled("        │                                              (TB4 DMA / Wi-Fi 7)", Style::default().fg(Color::Yellow)),
        ]),
        Line::from(vec![
            Span::styled("   (1GbE Copper LAN)                                           │", Style::default().fg(Color::Yellow)),
        ]),
        Line::from(vec![
            Span::styled("        │                                                      ▼", Style::default().fg(Color::Yellow)),
        ]),
        Line::from(vec![
            Span::styled(" [L3: Linux Node]  ", Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
            Span::styled("<──────(1GbE Copper LAN / TS)────── ", Style::default().fg(Color::Yellow)),
            Span::styled("[L5: MBA M4 Metal] ", Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
        ]),
    ];

    let diagram_paragraph = Paragraph::new(diagram_lines)
        .block(diagram_block)
        .alignment(Alignment::Center);
    frame.render_widget(diagram_paragraph, left_chunks[0]);

    // 2. Lower: Core Ring Stateful Table
    let table_border_color = if is_core_focused {
        Color::Cyan
    } else {
        Color::DarkGray
    };

    let table_title = format!(
        " ⭕ Core PRP Ring Nodes ({:.1} GB VRAM / {:.1} GB RAM) {} ",
        app.mesh_config.core_vram_total(),
        app.mesh_config.core_ram_total(),
        if is_core_focused { "[ACTIVE FOCUS]" } else { "" }
    );

    let table_block = Block::default()
        .title(Span::styled(
            table_title,
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(table_border_color));

    let header_cells = ["Status", "Layer", "Node Name", "Endpoint", "VRAM", "RAM", "Interconnect", "Role"]
        .iter()
        .map(|h| {
            Cell::from(*h).style(
                Style::default()
                    .fg(Color::Yellow)
                    .add_modifier(Modifier::BOLD),
            )
        });
    let header_row = Row::new(header_cells).height(1).bottom_margin(1);

    let core_nodes = app.mesh_config.core_nodes();
    let rows: Vec<Row> = core_nodes
        .iter()
        .enumerate()
        .map(|(i, node)| {
            let (is_up, rtt) = if node.is_master || node.ip == "127.0.0.1" {
                probe_endpoint("127.0.0.1", 4000, 100)
            } else if let Some(ref ts) = node.tailscale_ip {
                probe_endpoint(ts, 22, 120)
            } else {
                probe_endpoint(&node.ip, node.port, 120)
            };

            let status_cell = if is_up {
                let ms = rtt.unwrap_or(0.1);
                Cell::from(format!("🟢 LIVE ({:.0}ms)", ms))
                    .style(Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
            } else {
                Cell::from("⚪ STANDBY")
                    .style(Style::default().fg(Color::Yellow))
            };

            let cells = vec![
                status_cell,
                Cell::from(node.layer.clone()).style(Style::default().fg(Color::Cyan)),
                Cell::from(node.name.clone()).style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Cell::from(node.endpoint()).style(Style::default().fg(Color::LightCyan)),
                Cell::from(format!("{:.1} GB", node.vram_gb)).style(Style::default().fg(Color::Green)),
                Cell::from(format!("{:.1} GB", node.ram_gb)).style(Style::default().fg(Color::Gray)),
                Cell::from(node.interconnect.clone()).style(Style::default().fg(Color::Yellow)),
                Cell::from(node.role.clone()).style(Style::default().fg(Color::DarkGray)),
            ];

            let row_style = if i % 2 == 0 {
                Style::default().bg(Color::Rgb(15, 20, 28))
            } else {
                Style::default().bg(Color::Rgb(20, 26, 36))
            };

            Row::new(cells).style(row_style).height(1)
        })
        .collect();

    let widths = [
        Constraint::Length(14),
        Constraint::Length(7),
        Constraint::Min(18),
        Constraint::Min(16),
        Constraint::Length(10),
        Constraint::Length(10),
        Constraint::Min(20),
        Constraint::Min(20),
    ];

    let table = Table::new(rows, widths)
        .header(header_row)
        .block(table_block)
        .row_highlight_style(
            Style::default()
                .bg(Color::Rgb(28, 55, 88))
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("▶ ");

    frame.render_stateful_widget(table, left_chunks[1], &mut app.core_table_state);
}

/// Render right pane: Edge RPC Pool + Capabilities & Telemetry Matrix.
fn render_edge_pool_pane(app: &mut App, frame: &mut Frame, area: Rect) {
    let right_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(52), Constraint::Percentage(48)])
        .split(area);

    let is_edge_focused = app.active_topology_table == ActiveTopologyTable::Edge;
    let edge_border_color = if is_edge_focused {
        Color::Magenta
    } else {
        Color::DarkGray
    };

    // 1. Upper: Edge Pool Table
    let table_title = format!(
        " ⚡ Edge RPC Pool ({:.1} GB VRAM) {} ",
        app.mesh_config.edge_vram_total(),
        if is_edge_focused { "[ACTIVE FOCUS]" } else { "" }
    );

    let table_block = Block::default()
        .title(Span::styled(
            table_title,
            Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(edge_border_color));

    let header_cells = ["Status", "Layer", "Node Name", "Endpoint", "VRAM", "Role"]
        .iter()
        .map(|h| {
            Cell::from(*h).style(
                Style::default()
                    .fg(Color::Magenta)
                    .add_modifier(Modifier::BOLD),
            )
        });
    let header_row = Row::new(header_cells).height(1).bottom_margin(1);

    let edge_nodes = app.mesh_config.edge_nodes();
    let rows: Vec<Row> = edge_nodes
        .iter()
        .enumerate()
        .map(|(i, node)| {
            let (is_up, rtt) = if node.id == "pixel_10" {
                // Check ADB local port or Tailscale port
                let (adb_up, adb_rtt) = probe_endpoint("192.168.8.145", 36815, 100);
                if adb_up {
                    (true, adb_rtt)
                } else {
                    probe_endpoint(&node.ip, node.port, 120)
                }
            } else if let Some(ref ts) = node.tailscale_ip {
                probe_endpoint(ts, node.port, 120)
            } else {
                probe_endpoint(&node.ip, node.port, 120)
            };

            let status_cell = if is_up {
                let ms = rtt.unwrap_or(0.1);
                Cell::from(format!("🟢 LIVE ({:.0}ms)", ms))
                    .style(Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
            } else {
                Cell::from("⚪ STANDBY")
                    .style(Style::default().fg(Color::Yellow))
            };

            let cells = vec![
                status_cell,
                Cell::from(node.layer.clone()).style(Style::default().fg(Color::Magenta)),
                Cell::from(node.name.clone()).style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Cell::from(node.endpoint()).style(Style::default().fg(Color::LightCyan)),
                Cell::from(format!("{:.1} GB", node.vram_gb)).style(Style::default().fg(Color::Green)),
                Cell::from(node.role.clone()).style(Style::default().fg(Color::Gray)),
            ];

            let row_style = if i % 2 == 0 {
                Style::default().bg(Color::Rgb(24, 16, 28))
            } else {
                Style::default().bg(Color::Rgb(30, 20, 36))
            };

            Row::new(cells).style(row_style).height(1)
        })
        .collect();

    let widths = [
        Constraint::Length(14),
        Constraint::Length(7),
        Constraint::Min(18),
        Constraint::Min(16),
        Constraint::Length(10),
        Constraint::Min(20),
    ];

    let table = Table::new(rows, widths)
        .header(header_row)
        .block(table_block)
        .row_highlight_style(
            Style::default()
                .bg(Color::Rgb(70, 25, 75))
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("▶ ");

    frame.render_stateful_widget(table, right_chunks[0], &mut app.edge_table_state);

    // 2. Lower: Cluster Architecture & Capabilities Matrix
    let matrix_block = Block::default()
        .title(Span::styled(
            " 📊 Cluster Architecture & Dynamic Capabilities ",
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Green));

    let master_node = app.mesh_config.get_master_node();
    let master_str = if let Some(m) = master_node {
        format!("{} ({}:{}) [{}]", m.name, m.ip, m.port, m.layer)
    } else {
        "127.0.0.1:8082 (Local Master)".to_string()
    };

    let matrix_lines = vec![
        Line::from(vec![
            Span::styled("• Pooled RAM:          ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{:.1} GB", app.mesh_config.total_ram_gb()),
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
            ),
            Span::styled(" (Core: ", Style::default().fg(Color::DarkGray)),
            Span::styled(
                format!("{:.1} GB", app.mesh_config.core_ram_total()),
                Style::default().fg(Color::LightCyan),
            ),
            Span::styled(" │ Edge: ", Style::default().fg(Color::DarkGray)),
            Span::styled(
                format!("{:.1} GB", app.mesh_config.edge_ram_total()),
                Style::default().fg(Color::Magenta),
            ),
            Span::styled(")", Style::default().fg(Color::DarkGray)),
        ]),
        Line::from(vec![
            Span::styled("• Total AI VRAM:       ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{:.1} GB", app.mesh_config.total_vram_gb()),
                Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
            ),
            Span::styled(" (", Style::default().fg(Color::DarkGray)),
            Span::styled(
                format!("{:.1} GB Usable", app.mesh_config.mesh.pooled_vram_gb),
                Style::default().fg(Color::Yellow),
            ),
            Span::styled(")", Style::default().fg(Color::DarkGray)),
        ]),
        Line::from(vec![
            Span::styled("• Master Coordinator:  ", Style::default().fg(Color::Gray)),
            Span::styled(master_str, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("• Dynamic RAM Cap:     ", Style::default().fg(Color::Gray)),
            Span::styled("Mac ≤90%, Linux ≤80%, Android ≤85%", Style::default().fg(Color::LightYellow)),
        ]),
        Line::from(vec![
            Span::styled("• Interconnect Tiers:  ", Style::default().fg(Color::Gray)),
            Span::styled("10Gbps TB4 DMA (0.27ms) │ 1GbE LAN │ Tailscale", Style::default().fg(Color::Cyan)),
        ]),
        Line::from(vec![
            Span::styled("• Swarm Rule #0:       ", Style::default().fg(Color::Gray)),
            Span::styled("Zero-Mock Truth Invariant Active (Real config/mesh.toml)", Style::default().fg(Color::LightGreen)),
        ]),
    ];

    let matrix_paragraph = Paragraph::new(matrix_lines)
        .block(matrix_block)
        .alignment(Alignment::Left);
    frame.render_widget(matrix_paragraph, right_chunks[1]);
}
