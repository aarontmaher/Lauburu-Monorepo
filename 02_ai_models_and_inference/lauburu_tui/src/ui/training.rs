//! ============================================================================
//! Continuous Training & Dynamic RAM Governor View (Tab 5) - Ratatui UI
//! ============================================================================

use crate::app::App;
use crate::training::TrainingFocus;
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Cell, Gauge, Paragraph, Row, Table};
use ratatui::Frame;

/// Render the 2x2 Continuous Training & Sandbox Protocol view (Tab 5).
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let outer_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Magenta))
        .title(Span::styled(
            " 🏋️ [5] Continuous Training & Dynamic RAM Governor Matrix ",
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ));

    let inner = outer_block.inner(area);
    frame.render_widget(outer_block, area);

    // 2x2 Master Layout: 2-Tier Vertical Split
    let vertical_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage(46), // Upper: LoRA Distillation + RAM Governor
            Constraint::Percentage(54), // Lower: ELO Tournament + NPU Bonus Ledger
        ])
        .split(inner);

    // ------------------------------------------------------------------------
    // TIER 1: Upper Horizontal Split (LoRA Distillation + RAM Governor)
    // ------------------------------------------------------------------------
    let upper_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(58), // Upper Left: LoRA Distillation Status & Loss Trend
            Constraint::Percentage(42), // Upper Right: Dynamic RAM Governor Gauge & Directives
        ])
        .split(vertical_chunks[0]);

    render_lora_distillation_pane(app, frame, upper_chunks[0]);
    render_ram_governor_pane(app, frame, upper_chunks[1]);

    // ------------------------------------------------------------------------
    // TIER 2: Lower Horizontal Split (ELO Tournament + NPU Bonus Ledger)
    // ------------------------------------------------------------------------
    let lower_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(50), // Lower Left: Shadow Swarm Tournament ELO Table
            Constraint::Percentage(50), // Lower Right: NPU Bonus Ledger Table
        ])
        .split(vertical_chunks[1]);

    render_benchmark_tournament_table(app, frame, lower_chunks[0]);
    render_npu_bonus_ledger_table(app, frame, lower_chunks[1]);
}

/// 1. Upper Left: 24/7 LoRA Distillation Status, Progress Gauge, and Loss Trend
fn render_lora_distillation_pane(app: &App, frame: &mut Frame, area: Rect) {
    let job = &app.training_state.lora_job;

    let block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(
            " 🧠 24/7 LoRA Distillation Progress ",
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ));

    let inner_area = block.inner(area);
    frame.render_widget(block, area);

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Progress Gauge
            Constraint::Min(4),    // Job Details & Loss Trend History
        ])
        .split(inner_area);

    // Step Progress Gauge
    let progress_pct = job.progress_pct().clamp(0.0, 100.0);
    let progress_label = format!(
        "1,420 / 5,000 Steps (Epoch {}/{}) │ Loss: {:.2} │ {:.1} spl/s",
        job.current_epoch, job.total_epochs, job.current_loss, job.throughput_samples_sec
    );

    let progress_gauge = Gauge::default()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::DarkGray))
                .title(Span::styled(" Step Progress ", Style::default().fg(Color::White))),
        )
        .gauge_style(
            Style::default()
                .fg(Color::Magenta)
                .add_modifier(Modifier::BOLD),
        )
        .percent(progress_pct as u16)
        .label(progress_label);
    frame.render_widget(progress_gauge, chunks[0]);

    // Loss Trend String
    let loss_trend_str = if job.loss_history.is_empty() {
        "—".to_string()
    } else {
        job.loss_history
            .iter()
            .map(|l| format!("{:.2}", l))
            .collect::<Vec<String>>()
            .join(" ──► ")
    };

    let converging_badge = if job.is_loss_converging() {
        Span::styled(" [CONVERGING]", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
    } else {
        Span::styled(" [DIVERGING]", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))
    };

    let details_lines = vec![
        Line::from(vec![
            Span::styled("Active Model:   ", Style::default().fg(Color::Gray)),
            Span::styled(&job.active_model, Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled(format!(" (r={}, α={})", job.lora_rank, job.lora_alpha), Style::default().fg(Color::White)),
            Span::styled(" │ Targets: ", Style::default().fg(Color::Gray)),
            Span::styled(&job.target_modules, Style::default().fg(Color::LightCyan)),
        ]),
        Line::from(vec![
            Span::styled("Teacher Model:  ", Style::default().fg(Color::Gray)),
            Span::styled(&job.teacher_model, Style::default().fg(Color::LightBlue)),
            Span::styled(" │ Throughput: ", Style::default().fg(Color::Gray)),
            Span::styled(
                format!("{:.1} spl/s ({:.0} tok/s)", job.throughput_samples_sec, job.throughput_tokens_sec),
                Style::default().fg(Color::LightGreen),
            ),
        ]),
        Line::from(vec![
            Span::styled("Loss History:   ", Style::default().fg(Color::Gray)),
            Span::styled(loss_trend_str, Style::default().fg(Color::Cyan)),
            converging_badge,
        ]),
        Line::from(vec![
            Span::styled("Training Pairs: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{} AST Pairs", job.dataset_pairs_count), Style::default().fg(Color::White)),
            Span::styled(" │ Storage Sync: ", Style::default().fg(Color::Gray)),
            Span::styled(&job.gdrive_sync_status, Style::default().fg(Color::LightYellow)),
        ]),
    ];

    let details_paragraph = Paragraph::new(details_lines);
    frame.render_widget(details_paragraph, chunks[1]);
}

/// 2. Upper Right: Dynamic RAM Governor Gauge, Tier Indicator, and Directives
fn render_ram_governor_pane(app: &App, frame: &mut Frame, area: Rect) {
    let tier = app.training_state.governor_tier;
    let (badge_str, badge_color) = tier.display_badge();
    let total_ram = app.mesh_config.total_ram_gb();

    let block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray))
        .title(Span::styled(
            " ⚡ Dynamic RAM Governor Status ",
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ));

    let inner_area = block.inner(area);
    frame.render_widget(block, area);

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Headroom Gauge
            Constraint::Min(4),    // Tier Policy & Directives
        ])
        .split(inner_area);

    // RAM Free Headroom Gauge
    let free_pct = app.training_state.host_ram_free_pct.clamp(0.0, 100.0);
    let headroom_label = format!(
        "{:.1}% Free ({:.1} GB / {:.1} GB Total)",
        free_pct, app.training_state.host_ram_free_gb, total_ram
    );

    let headroom_gauge = Gauge::default()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::DarkGray))
                .title(Span::styled(" Host RAM Headroom ", Style::default().fg(Color::White))),
        )
        .gauge_style(
            Style::default()
                .fg(badge_color)
                .add_modifier(Modifier::BOLD),
        )
        .percent(free_pct as u16)
        .label(headroom_label);
    frame.render_widget(headroom_gauge, chunks[0]);

    // Governor Directive Details
    let engine_status_span = if app.training_state.is_paused {
        Span::styled("[PAUSED (Press 'p' to resume)]", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD))
    } else {
        Span::styled("[ACTIVE 24/7 LoRA Loop]", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))
    };

    let directive_lines = vec![
        Line::from(vec![
            Span::styled("Governor Tier: ", Style::default().fg(Color::Gray)),
            Span::styled(badge_str, Style::default().fg(badge_color).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("Policy:        ", Style::default().fg(Color::Gray)),
            Span::styled(tier.directive(), Style::default().fg(Color::White)),
        ]),
        Line::from(vec![
            Span::styled("Engine State:  ", Style::default().fg(Color::Gray)),
            engine_status_span,
        ]),
        Line::from(vec![
            Span::styled("Pre-emption:   ", Style::default().fg(Color::Gray)),
            Span::styled("Yields compute when Host RAM free drops <50%", Style::default().fg(Color::DarkGray)),
        ]),
    ];

    let directive_paragraph = Paragraph::new(directive_lines);
    frame.render_widget(directive_paragraph, chunks[1]);
}

/// 3. Lower Left: Shadow Swarm Benchmark Tournament (ELO Leaderboard) Table
fn render_benchmark_tournament_table(app: &mut App, frame: &mut Frame, area: Rect) {
    let is_focused = app.training_state.active_training_focus == TrainingFocus::BenchmarkTournament;

    let border_color = if is_focused { Color::Cyan } else { Color::DarkGray };
    let title_style = if is_focused {
        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(Color::Gray)
    };

    let title_text = if is_focused {
        " ▶ 🏆 Shadow Swarm Benchmark Tournament (ELO Leaderboard) [FOCUS] "
    } else {
        " 🏆 Shadow Swarm Benchmark Tournament (ELO Leaderboard) "
    };

    let header_cells = [
        "Model Name",
        "Architecture",
        "ELO",
        "W / L / D",
        "Truth %",
        "Promotion Verdict",
    ]
    .iter()
    .map(|h| Cell::from(*h).style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)));

    let header = Row::new(header_cells).height(1).bottom_margin(0);

    let rows: Vec<Row> = app
        .training_state
        .benchmark_rows
        .iter()
        .map(|row| {
            let elo_color = if row.elo_score >= 1900 {
                Color::Magenta
            } else if row.elo_score >= 1850 {
                Color::Green
            } else {
                Color::Yellow
            };

            let verdict_color = if row.promotion_verdict.contains("Promoted") {
                Color::Green
            } else if row.promotion_verdict.contains("Frontier") {
                Color::Cyan
            } else {
                Color::Yellow
            };

            let cells = vec![
                Cell::from(row.model_name.as_str()).style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Cell::from(row.architecture.as_str()).style(Style::default().fg(Color::Gray)),
                Cell::from(format!("{}", row.elo_score)).style(Style::default().fg(elo_color).add_modifier(Modifier::BOLD)),
                Cell::from(format!("{}/{}/{}", row.win_loss_draw.0, row.win_loss_draw.1, row.win_loss_draw.2)).style(Style::default().fg(Color::LightGreen)),
                Cell::from(format!("{:.1}%", row.truth_audit_pct)).style(Style::default().fg(Color::LightCyan)),
                Cell::from(row.promotion_verdict.as_str()).style(Style::default().fg(verdict_color)),
            ];

            Row::new(cells).height(1)
        })
        .collect();

    let widths = [
        Constraint::Percentage(28), // Model Name
        Constraint::Percentage(24), // Architecture
        Constraint::Length(7),      // ELO
        Constraint::Length(11),     // W/L/D
        Constraint::Length(9),      // Truth %
        Constraint::Percentage(20), // Verdict
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

    frame.render_stateful_widget(table, area, &mut app.training_state.benchmark_table_state);
}

/// 4. Lower Right: NPU Bonus Ledger (Edge TPU & ANE Compute Credits) Table
fn render_npu_bonus_ledger_table(app: &mut App, frame: &mut Frame, area: Rect) {
    let is_focused = app.training_state.active_training_focus == TrainingFocus::NpuLedger;

    let border_color = if is_focused { Color::Cyan } else { Color::DarkGray };
    let title_style = if is_focused {
        Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(Color::Gray)
    };

    let title_text = if is_focused {
        " ▶ 💎 NPU Bonus Ledger (Edge TPU & ANE Credits) [FOCUS] "
    } else {
        " 💎 NPU Bonus Ledger (Edge TPU & ANE Credits) "
    };

    let header_cells = [
        "Node",
        "Layer",
        "Target NPU / Feature",
        "Token Credits",
        "Status",
    ]
    .iter()
    .map(|h| Cell::from(*h).style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)));

    let header = Row::new(header_cells).height(1).bottom_margin(0);

    let rows: Vec<Row> = app
        .training_state
        .npu_grants
        .iter()
        .map(|grant| {
            let target_display = format!("{} ({})", grant.execution_target, grant.promoted_feature);
            let credits_display = format!("{},000 Credits", grant.token_credits / 1000);

            let cells = vec![
                Cell::from(grant.node_name.as_str()).style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
                Cell::from(grant.layer.as_str()).style(Style::default().fg(Color::Yellow)),
                Cell::from(target_display).style(Style::default().fg(Color::LightCyan)),
                Cell::from(credits_display).style(Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD)),
                Cell::from(grant.grant_status.as_str()).style(Style::default().fg(Color::Green)),
            ];

            Row::new(cells).height(1)
        })
        .collect();

    let widths = [
        Constraint::Percentage(20), // Node
        Constraint::Length(7),      // Layer
        Constraint::Percentage(33), // Target NPU / Feature
        Constraint::Percentage(20), // Token Credits
        Constraint::Percentage(18), // Status
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

    frame.render_stateful_widget(table, area, &mut app.training_state.npu_table_state);
}
