use crate::app::App;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, List, ListItem, Paragraph, Wrap};
use ratatui::Frame;

/// Render Tab 6: Web Lens (Declarative TUI Web Extractor & Document Reader).
pub fn render(app: &App, frame: &mut Frame, area: Rect) {
    let state = &app.web_lens_state;

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // URL Input & Telemetry Bar
            Constraint::Min(10),   // Reader & Sidebar
        ])
        .split(area);

    // 1. Top URL & Extractor Header Bar
    let input_border_color = if state.is_input_mode {
        Color::Yellow
    } else {
        Color::Cyan
    };

    let url_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(input_border_color))
        .title(Span::styled(
            if state.is_input_mode { " 🌐 Web Lens URL [EDIT MODE - Press Enter to Fetch] " } else { " 🌐 Web Lens Reader [Press 'u' to edit URL, 't' to cycle extractor] " },
            Style::default().fg(input_border_color).add_modifier(Modifier::BOLD),
        ));

    let url_inner = url_block.inner(chunks[0]);
    frame.render_widget(url_block, chunks[0]);

    let url_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(70),
            Constraint::Percentage(30),
        ])
        .split(url_inner);

    if state.is_input_mode {
        frame.render_widget(&state.url_textarea, url_chunks[0]);
    } else {
        let current_url_line = Line::from(vec![
            Span::styled("URL: ", Style::default().fg(Color::DarkGray)),
            Span::styled(&state.current_url, Style::default().fg(Color::White).add_modifier(Modifier::BOLD)),
        ]);
        frame.render_widget(Paragraph::new(current_url_line), url_chunks[0]);
    }

    let stats_badge = Line::from(vec![
        Span::styled(format!("[{}] ", state.active_extractor.name()), Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
        Span::styled(format!("⚡ -{:.1}% Bloat", state.token_reduction_pct), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
    ]);
    frame.render_widget(Paragraph::new(stats_badge).alignment(Alignment::Right), url_chunks[1]);

    // 2. Main Content Split: Reader Viewport (72%) vs Metadata & Presets Sidebar (28%)
    let main_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(72),
            Constraint::Percentage(28),
        ])
        .split(chunks[1]);

    // 2A. Reader Viewport
    let reader_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::LightBlue))
        .title(Span::styled(
            format!(" 📖 {} (Line {}/{}) ", state.title, state.scroll_offset + 1, state.content_lines.len().max(1)),
            Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD),
        ));

    let reader_inner = reader_block.inner(main_chunks[0]);
    frame.render_widget(reader_block, main_chunks[0]);

    let mut rendered_lines = Vec::new();
    for line_str in state.content_lines.iter().skip(state.scroll_offset) {
        if line_str.starts_with("# ") {
            rendered_lines.push(Line::from(Span::styled(
                line_str.clone(),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
            )));
        } else if line_str.starts_with("## ") {
            rendered_lines.push(Line::from(Span::styled(
                line_str.clone(),
                Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
            )));
        } else if line_str.starts_with("### ") {
            rendered_lines.push(Line::from(Span::styled(
                line_str.clone(),
                Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD),
            )));
        } else if line_str.starts_with("```") {
            rendered_lines.push(Line::from(Span::styled(
                line_str.clone(),
                Style::default().fg(Color::DarkGray),
            )));
        } else if line_str.starts_with("•") || line_str.starts_with("-") {
            rendered_lines.push(Line::from(Span::styled(
                line_str.clone(),
                Style::default().fg(Color::LightYellow),
            )));
        } else if line_str.contains("class ") || line_str.contains("def ") || line_str.contains("let ") || line_str.contains("fn ") {
            rendered_lines.push(Line::from(Span::styled(
                format!("  {}", line_str),
                Style::default().fg(Color::LightMagenta),
            )));
        } else {
            rendered_lines.push(Line::from(Span::styled(
                line_str.clone(),
                Style::default().fg(Color::White),
            )));
        }
    }

    let reader_paragraph = Paragraph::new(rendered_lines)
        .wrap(Wrap { trim: false });
    frame.render_widget(reader_paragraph, reader_inner);

    // 2B. Right Sidebar (Stats + Quick Presets + Controls)
    let sidebar_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(7), // Token Economics & Telemetry
            Constraint::Length(9), // Quick Preset Navigator
            Constraint::Min(6),    // Navigation Shortcuts
        ])
        .split(main_chunks[1]);

    // Sidebar 1: Token Economics
    let stats_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Green))
        .title(Span::styled(" 📊 Token Economics ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)));

    let stats_lines = vec![
        Line::from(vec![
            Span::styled("Raw HTML: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{:.1} KB", state.raw_html_bytes as f64 / 1024.0), Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("Clean Markdown: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{:.1} KB", state.clean_markdown_bytes as f64 / 1024.0), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("Context Savings: ", Style::default().fg(Color::Gray)),
            Span::styled(format!("{:.1}%", state.token_reduction_pct), Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(vec![
            Span::styled("RAM Overhead: ", Style::default().fg(Color::Gray)),
            Span::styled("<12 MB", Style::default().fg(Color::LightCyan)),
        ]),
    ];
    frame.render_widget(Paragraph::new(stats_lines).block(stats_block), sidebar_chunks[0]);

    // Sidebar 2: Quick Presets
    let presets_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Yellow))
        .title(Span::styled(" 🚀 Mesh Research Presets ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)));

    let mut preset_items = Vec::new();
    for (i, (title, _)) in state.quick_presets.iter().enumerate() {
        let short_title = if title.len() > 24 { format!("{}...", &title[..21]) } else { title.to_string() };
        preset_items.push(ListItem::new(Line::from(vec![
            Span::styled(format!("[{}] ", i + 1), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled(short_title, Style::default().fg(Color::White)),
        ])));
    }
    frame.render_widget(List::new(preset_items).block(presets_block), sidebar_chunks[1]);

    // Sidebar 3: Navigation Shortcuts
    let controls_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Cyan))
        .title(Span::styled(" ⌨️ Navigation ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)));

    let control_lines = vec![
        Line::from(vec![
            Span::styled("[u] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Edit URL", Style::default().fg(Color::Gray)),
        ]),
        Line::from(vec![
            Span::styled("[t] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Cycle Extractor", Style::default().fg(Color::Gray)),
        ]),
        Line::from(vec![
            Span::styled("[j/k] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Scroll Line", Style::default().fg(Color::Gray)),
        ]),
        Line::from(vec![
            Span::styled("[PgUp/PgDn] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Scroll Page", Style::default().fg(Color::Gray)),
        ]),
        Line::from(vec![
            Span::styled("[1-5] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Quick Preset", Style::default().fg(Color::Gray)),
        ]),
        Line::from(vec![
            Span::styled("[1-6] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab", Style::default().fg(Color::LightCyan)),
        ]),
    ];
    frame.render_widget(Paragraph::new(control_lines).block(controls_block), sidebar_chunks[2]);
}
