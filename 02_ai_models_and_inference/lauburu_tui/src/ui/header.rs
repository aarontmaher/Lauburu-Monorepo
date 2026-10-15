use crate::app::{App, Tab};
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph, Tabs};
use ratatui::Frame;

/// Render the header component containing cluster title, active tab selector, and aggregate metrics.
pub fn render(app: &App, frame: &mut Frame, area: Rect) {
    let outer_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Cyan));

    let inner_area = outer_block.inner(area);
    frame.render_widget(outer_block, area);

    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(25),
            Constraint::Percentage(45),
            Constraint::Percentage(30),
        ])
        .split(inner_area);

    // Left: Cluster Title & Master Node Info
    let master_info = if let Some(master) = app.mesh_config.get_master_node() {
        format!("Master: {} ({}:{})", master.layer, master.ip, master.port)
    } else {
        "Master: 127.0.0.1:8082".to_string()
    };

    let title_line = Line::from(vec![
        Span::styled("⚡ ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        Span::styled(
            &app.mesh_config.mesh.name,
            Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
        ),
        Span::styled(" │ ", Style::default().fg(Color::DarkGray)),
        Span::styled(master_info, Style::default().fg(Color::LightCyan)),
    ]);
    let title_paragraph = Paragraph::new(title_line).alignment(Alignment::Left);
    frame.render_widget(title_paragraph, chunks[0]);

    // Center: Active Tab Selector (All 7 Tabs)
    let tab_titles: Vec<&'static str> = Tab::all().iter().map(|t| t.title()).collect();
    let tabs = Tabs::new(tab_titles)
        .select(app.current_tab.index())
        .style(Style::default().fg(Color::DarkGray))
        .highlight_style(
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
        )
        .divider(Span::styled(" │ ", Style::default().fg(Color::DarkGray)));
    frame.render_widget(tabs, chunks[1]);

    // Right: Aggregate RAM and VRAM metrics
    let total_ram = app.mesh_config.total_ram_gb();
    let total_vram = app.mesh_config.total_vram_gb();
    let usable_vram = app.mesh_config.mesh.pooled_vram_gb;

    let metrics_line = Line::from(vec![
        Span::styled("RAM: ", Style::default().fg(Color::Gray)),
        Span::styled(
            format!("{:.1} GB", total_ram),
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ),
        Span::styled(" │ ", Style::default().fg(Color::DarkGray)),
        Span::styled("AI VRAM: ", Style::default().fg(Color::Gray)),
        Span::styled(
            format!("{:.1} GB", total_vram),
            Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
        ),
        Span::styled(
            format!(" ({:.1} GB usable)", usable_vram),
            Style::default().fg(Color::DarkGray),
        ),
    ]);
    let metrics_paragraph = Paragraph::new(metrics_line).alignment(Alignment::Right);
    frame.render_widget(metrics_paragraph, chunks[2]);
}
