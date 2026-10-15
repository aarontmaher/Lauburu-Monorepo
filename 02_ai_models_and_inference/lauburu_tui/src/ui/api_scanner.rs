use crate::api_scanner::SwapStatus;
use crate::app::App;
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Gauge, Paragraph, Row, Table};
use ratatui::Frame;

/// Render the API Scanner & Spend Optimizer view (Tab 4).
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let outer_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Green))
        .title(Span::styled(
            " 💰 [4] API Scanner — Cloud API Usage & Model Swap Optimizer ",
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ));

    let inner = outer_block.inner(area);
    frame.render_widget(outer_block, area);

    // 3-Tier Layout: Top Banner (5), Middle Split (Min 10), Bottom Status (3)
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(5),
            Constraint::Min(10),
            Constraint::Length(3),
        ])
        .split(inner);

    let state = &app.api_scanner_state;
    let total_vram = app.mesh_config.total_vram_gb();
    let pooled_vram = app.mesh_config.mesh.pooled_vram_gb;

    // ------------------------------------------------------------------------
    // TIER 1: Top Dashboard Gauge Banner (3 Sub-Gauges / Cards)
    // ------------------------------------------------------------------------
    let top_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(32),
            Constraint::Percentage(36),
            Constraint::Percentage(32),
        ])
        .split(chunks[0]);

    // Top Left: Baseline vs Current Spend
    let spend_reduction_lines = vec![
        Line::from(vec![
            Span::styled("Baseline Spend: ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("${:.2} / mo", state.baseline_monthly_spend_usd),
                Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("Current Spend:  ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("${:.2} / mo", state.current_cloud_spend_usd),
                Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
            ),
            Span::styled(" ──► Target: ", Style::default().fg(Color::DarkGray)),
            Span::styled("$0.00", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        ]),
    ];
    let spend_reduction_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(" Cloud Spend Reduction ", Style::default().fg(Color::White)));
    let spend_reduction_widget = Paragraph::new(spend_reduction_lines).block(spend_reduction_block);
    frame.render_widget(spend_reduction_widget, top_chunks[0]);

    // Top Center: $0 Cloud Spend Velocity Gauge
    let velocity_pct = state.zero_spend_velocity_pct.clamp(0.0, 100.0);
    let velocity_label = format!(
        "{:.1}% (${:.2} / ${:.2} Saved)",
        velocity_pct, state.total_savings_usd, state.baseline_monthly_spend_usd
    );
    let velocity_gauge = Gauge::default()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Green))
                .title(Span::styled(
                    " $0 Cloud Spend Velocity ",
                    Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
                )),
        )
        .gauge_style(
            Style::default()
                .fg(if velocity_pct >= 80.0 {
                    Color::Green
                } else if velocity_pct >= 50.0 {
                    Color::Yellow
                } else {
                    Color::Red
                })
                .add_modifier(Modifier::BOLD),
        )
        .percent(velocity_pct as u16)
        .label(velocity_label);
    frame.render_widget(velocity_gauge, top_chunks[1]);

    // Top Right: Local Mesh Ratio & Savings
    let local_mesh_lines = vec![
        Line::from(vec![
            Span::styled("Monthly Savings: ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("${:.2} / mo", state.total_savings_usd),
                Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("Mesh Ratio:      ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{:.1}% Local", state.local_request_ratio),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                format!(" │ VRAM: {:.1}/{:.1}GB", pooled_vram, total_vram),
                Style::default().fg(Color::DarkGray),
            ),
        ]),
    ];
    let local_mesh_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(" Local Mesh Economics ", Style::default().fg(Color::White)));
    let local_mesh_widget = Paragraph::new(local_mesh_lines).block(local_mesh_block);
    frame.render_widget(local_mesh_widget, top_chunks[2]);

    // ------------------------------------------------------------------------
    // TIER 2: Middle Split Pane (Endpoints Table + Recommendation Detail Card)
    // ------------------------------------------------------------------------
    let middle_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(55),
            Constraint::Percentage(45),
        ])
        .split(chunks[1]);

    // Left Sub-Pane: Cloud API Endpoint Table
    let table_rows: Vec<Row> = state
        .endpoints
        .iter()
        .enumerate()
        .map(|(idx, ep)| {
            let is_selected = idx == state.selected_endpoint_row;
            let status_badge = if ep.is_active {
                Span::styled("CLOUD ACTIVE", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))
            } else {
                Span::styled("LOCAL SWAPPED", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
            };

            let prefix = if is_selected { "▶ " } else { "  " };
            let row_style = if is_selected {
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
            } else {
                Style::default().fg(Color::White)
            };

            Row::new(vec![
                Line::from(vec![Span::raw(prefix), Span::styled(&ep.provider, row_style)]),
                Line::from(Span::styled(&ep.detected_model, row_style)),
                Line::from(Span::styled(format!("${:.2}", ep.monthly_spend_usd), if ep.is_active { Style::default().fg(Color::Red) } else { Style::default().fg(Color::DarkGray) })),
                Line::from(Span::styled(format!("{}k / {}k", ep.input_tokens_k, ep.output_tokens_k), Style::default().fg(Color::Gray))),
                Line::from(status_badge),
            ])
        })
        .collect();

    let endpoint_table = Table::new(
        table_rows,
        [
            Constraint::Percentage(20),
            Constraint::Percentage(26),
            Constraint::Percentage(16),
            Constraint::Percentage(20),
            Constraint::Percentage(18),
        ],
    )
    .header(
        Row::new(vec!["Provider", "Model", "Spend", "Tokens (In/Out)", "Status"])
            .style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
    )
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::DarkGray))
            .title(Span::styled(
                " Cloud API Endpoints & Local Swaps ",
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            )),
    );
    frame.render_widget(endpoint_table, middle_chunks[0]);

    // Right Sub-Pane: Model Swap Recommendation Card
    let rec_lines = if let Some(rec) = state.selected_recommendation() {
        let status_style = match rec.status {
            SwapStatus::RunningOnMesh => Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
            SwapStatus::ReadyInVault => Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            SwapStatus::PendingDownload => Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            SwapStatus::Evaluating => Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD),
        };

        vec![
            Line::from(vec![
                Span::styled("Detected Cloud Model:    ", Style::default().fg(Color::Gray)),
                Span::styled(&rec.cloud_model, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("Recommended Local Model: ", Style::default().fg(Color::Gray)),
                Span::styled(&rec.local_replacement, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::styled("Target Mesh Layer:       ", Style::default().fg(Color::Gray)),
                Span::styled(&rec.target_layer, Style::default().fg(Color::Cyan)),
            ]),
            Line::from(vec![
                Span::styled("VRAM Footprint:          ", Style::default().fg(Color::Gray)),
                Span::styled(
                    format!("{:.1} GB (Fits in {:.1} GB Pool)", rec.vram_required_gb, pooled_vram),
                    Style::default().fg(Color::White),
                ),
            ]),
            Line::from(vec![
                Span::styled("Est. Monthly Savings:    ", Style::default().fg(Color::Gray)),
                Span::styled(
                    format!("${:.2} / month", rec.est_monthly_savings_usd),
                    Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled("Privacy & Security:      ", Style::default().fg(Color::Gray)),
                Span::styled(&rec.privacy_level, Style::default().fg(Color::LightBlue)),
            ]),
            Line::from(vec![
                Span::styled("Local Swap Status:       ", Style::default().fg(Color::Gray)),
                Span::styled(rec.status.badge(), status_style),
            ]),
        ]
    } else {
        vec![
            Line::from(Span::styled("Select a cloud endpoint on the left table to inspect swap options.", Style::default().fg(Color::DarkGray))),
        ]
    };

    let rec_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(
            " Local GGUF/MLX Model Swap Recommendations ",
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ));
    let rec_widget = Paragraph::new(rec_lines).block(rec_block);
    frame.render_widget(rec_widget, middle_chunks[1]);

    // ------------------------------------------------------------------------
    // TIER 3: Bottom Action & Persistence Status Bar
    // ------------------------------------------------------------------------
    let status_lines = vec![Line::from(vec![
        Span::styled("Hotkeys: ", Style::default().fg(Color::DarkGray)),
        Span::styled(
            "[s/Enter] Activate Swap │ [r] Rescan │ [j/k/↑/↓] Select Row │ [1-5] Switch Tab │ [q] Quit",
            Style::default().fg(Color::Yellow),
        ),
        Span::styled(" │ 💾 ", Style::default().fg(Color::Green)),
        Span::styled(&state.persistence_status, Style::default().fg(Color::White)),
    ])];

    let status_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(" Actions & Persistence ", Style::default().fg(Color::White)));
    let status_widget = Paragraph::new(status_lines).block(status_block);
    frame.render_widget(status_widget, chunks[2]);
}
