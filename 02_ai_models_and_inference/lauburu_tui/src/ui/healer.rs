// =============================================================================
// Tab 8: Autonomic Sentinel & Healer TUI View (Feature F19)
// Visual 6-tier transport matrix and autonomous local AI decision stream
// =============================================================================

use crate::app::App;
use crate::transports::TransportStatus;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{
    Block, BorderType, Borders, Cell, Gauge, Paragraph, Row, Table,
};
use ratatui::Frame;

/// Render the complete Autonomic Sentinel & Healer view.
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let main_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(5),  // Vitality & resilience banner
            Constraint::Min(12),    // Transport Matrix + Micro-AI Stream
            Constraint::Length(4),  // Cascading Fallback Pipeline visual
        ])
        .split(area);

    render_vitality_banner(app, frame, main_chunks[0]);
    render_matrix_and_stream(app, frame, main_chunks[1]);
    render_fallback_pipeline(frame, main_chunks[2]);
}

fn render_vitality_banner(app: &App, frame: &mut Frame, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(35),
            Constraint::Percentage(35),
            Constraint::Percentage(30),
        ])
        .split(area);

    let vit = &app.healer_state.vitality;

    // 1. Overall Cluster Vitality Gauge
    let gauge_color = if vit.overall_score_pct >= 90.0 {
        Color::Green
    } else if vit.overall_score_pct >= 70.0 {
        Color::Yellow
    } else {
        Color::Red
    };

    let gauge = Gauge::default()
        .block(
            Block::default()
                .title(" 🛡️ Cluster Vitality Index ")
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Cyan)),
        )
        .gauge_style(Style::default().fg(gauge_color).bg(Color::DarkGray))
        .percent(vit.overall_score_pct.clamp(0.0, 100.0) as u16)
        .label(format!("{:.1}% Vitality", vit.overall_score_pct));
    frame.render_widget(gauge, chunks[0]);

    // 2. Offline Survival Metrics
    let offline_block = Block::default()
        .title(" 🌐 Offline Resilience ")
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::LightCyan));

    let offline_text = vec![
        Line::from(vec![
            Span::styled("Active VRAM: ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{:.1} / {:.1} GB", vit.active_vram_gb, vit.max_vram_gb),
                Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("Surviving Nodes: ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{}/{} Operational", vit.active_nodes, vit.total_nodes),
                Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
            ),
            Span::styled(" │ Index: ", Style::default().fg(Color::DarkGray)),
            Span::styled(
                format!("{:.2}", vit.offline_resilience_index),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            ),
        ]),
    ];
    let offline_paragraph = Paragraph::new(offline_text)
        .block(offline_block)
        .alignment(Alignment::Left);
    frame.render_widget(offline_paragraph, chunks[1]);

    // 3. Coordinator & Autonomic State
    let coord_block = Block::default()
        .title(" 👑 Master Coordinator ")
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Yellow));

    let coord_text = vec![
        Line::from(vec![
            Span::styled("Leader: ", Style::default().fg(Color::Gray)),
            Span::styled(
                &vit.active_master_id,
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("Autonomic Healer: ", Style::default().fg(Color::Gray)),
            if app.healer_state.auto_healing_active {
                Span::styled("ACTIVE (Autonomous OODA)", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
            } else {
                Span::styled("MANUAL OVERRIDE", Style::default().fg(Color::LightRed))
            },
        ]),
    ];
    let coord_paragraph = Paragraph::new(coord_text)
        .block(coord_block)
        .alignment(Alignment::Left);
    frame.render_widget(coord_paragraph, chunks[2]);
}

fn render_matrix_and_stream(app: &App, frame: &mut Frame, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(64), // 6-tier matrix
            Constraint::Percentage(36), // Decision stream
        ])
        .split(area);

    // ── 6-Tier Cascading Physical Transport Matrix ─────────────
    let matrix_block = Block::default()
        .title(" ⚡ 6-Tier Cascading Physical Transport Matrix ")
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Green));

    let rows: Vec<Row> = app
        .healer_state
        .transport_mgr
        .links
        .iter()
        .enumerate()
        .map(|(idx, link)| {
            let status_style = match link.status {
                TransportStatus::Active => Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
                TransportStatus::Standby => Style::default().fg(Color::Cyan),
                TransportStatus::Degraded => Style::default().fg(Color::Yellow),
                TransportStatus::Offline => Style::default().fg(Color::Red),
            };

            let row_style = if idx == app.healer_state.selected_link_index {
                Style::default().bg(Color::Rgb(30, 45, 65)).fg(Color::White).add_modifier(Modifier::BOLD)
            } else {
                Style::default()
            };

            let active_marker = if link.is_active_route { "★ " } else { "  " };

            Row::new(vec![
                Cell::from(format!("{}{}", active_marker, link.node_id)),
                Cell::from(format!("{}", link.tier)),
                Cell::from(link.endpoint.clone()),
                Cell::from(format!("{}", link.status)).style(status_style),
                Cell::from(format!("{:.2} ms", link.latency_ms)),
                Cell::from(format!("{:.0} Mbps", link.bandwidth_mbps)),
                Cell::from(format!("{:.1}%", link.loss_pct)),
            ])
            .style(row_style)
        })
        .collect();

    let table = Table::new(
        rows,
        [
            Constraint::Length(18),
            Constraint::Length(22),
            Constraint::Length(18),
            Constraint::Length(9),
            Constraint::Length(10),
            Constraint::Length(11),
            Constraint::Length(7),
        ],
    )
    .header(
        Row::new(vec![
            "Node ID",
            "Transport Tier",
            "Physical Endpoint",
            "Status",
            "RTT",
            "Bandwidth",
            "Loss",
        ])
        .style(
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
        ),
    )
    .block(matrix_block);

    frame.render_widget(table, chunks[0]);

    // ── Autonomic Micro-AI Decision Stream ───────────────────────
    let stream_block = Block::default()
        .title(" 🧠 Micro-AI Autonomic Decision Stream ")
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Magenta));

    let directive_lines: Vec<Line> = app
        .healer_state
        .healer
        .directives
        .iter()
        .rev()
        .take(10)
        .map(|dir| {
            let type_color = match dir.directive_type {
                crate::healer::DirectiveType::PromoteCoordinator => Color::LightRed,
                crate::healer::DirectiveType::MigrateTransportTier => Color::Yellow,
                crate::healer::DirectiveType::RebalanceVramShards => Color::Cyan,
                crate::healer::DirectiveType::CycleInterface => Color::LightYellow,
                crate::healer::DirectiveType::ThermalThrottleNode => Color::Magenta,
                crate::healer::DirectiveType::IsolateDegradedNode => Color::Red,
                crate::healer::DirectiveType::RestoreNomadCourierMux => Color::Green,
            };

            Line::from(vec![
                Span::styled(format!("[{}] ", dir.timestamp), Style::default().fg(Color::DarkGray)),
                Span::styled(format!("{:<18} ", format!("{}", dir.directive_type)), Style::default().fg(type_color).add_modifier(Modifier::BOLD)),
                Span::styled(format!("-> {} ", dir.target_node_id), Style::default().fg(Color::White)),
                Span::styled(format!("({:.0}% conf) ", dir.confidence_score * 100.0), Style::default().fg(Color::LightCyan)),
                Span::styled(&dir.rationale, Style::default().fg(Color::Gray)),
            ])
        })
        .collect();

    let stream_paragraph = Paragraph::new(directive_lines)
        .block(stream_block)
        .alignment(Alignment::Left);

    frame.render_widget(stream_paragraph, chunks[1]);
}

fn render_fallback_pipeline(frame: &mut Frame, area: Rect) {
    let block = Block::default()
        .title(" ⛓️ Node Resurrection & Transport Fallback (Line 1 Bluetooth Proximity Wake Default) ")
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray));

    let pipeline_line = Line::from(vec![
        Span::styled(" [Line 1: BT Proximity Wake] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        Span::styled("──►", Style::default().fg(Color::DarkGray)),
        Span::styled(" [Line 2: UDP WoL Packet] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled("──►", Style::default().fg(Color::DarkGray)),
        Span::styled(" [Line 3: ADB Wake/Keepalive] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        Span::styled("──►", Style::default().fg(Color::DarkGray)),
        Span::styled(" [Line 4: TB4 DMA / 1GbE / Tailscale] ", Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD)),
        Span::styled("──►", Style::default().fg(Color::DarkGray)),
        Span::styled(" [Line 5: Multi-WAN Gateway] ", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
    ]);

    let paragraph = Paragraph::new(pipeline_line)
        .block(block)
        .alignment(Alignment::Center);

    frame.render_widget(paragraph, area);
}
