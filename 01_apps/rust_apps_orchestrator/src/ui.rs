use crate::model::{AppDomain, AppEntry, AppLiveStatus};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Cell, List, ListItem, Paragraph, Row, Table, Tabs, Wrap},
    Frame,
};
use std::collections::HashMap;

pub struct UiState<'a> {
    pub active_domain: AppDomain,
    pub selected_app_idx: usize,
    pub apps: &'a [AppEntry],
    pub statuses: &'a HashMap<&'static str, AppLiveStatus>,
    pub status_msg: &'a str,
    pub readme_lines: &'a [String],
    pub scan_time_ms: f64,
}

pub fn draw_ui(f: &mut Frame, state: &UiState) {
    let size = f.area();

    // Vertical layout: Header (3), Domain Tabs (3), Main Body (Min 10), Footer (2)
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Length(3),
            Constraint::Min(12),
            Constraint::Length(2),
        ])
        .split(size);

    draw_header(f, state, chunks[0]);
    draw_domain_tabs(f, state, chunks[1]);
    draw_main_body(f, state, chunks[2]);
    draw_footer(f, state, chunks[3]);
}

fn draw_header(f: &mut Frame, state: &UiState, area: Rect) {
    let total_apps = state.apps.len();
    let online_count = state
        .statuses
        .values()
        .filter(|s| s.is_running || s.port_online)
        .count();

    let header_text = Line::from(vec![
        Span::styled(" 🌌 LAUBURU MONOREPO ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled("• MASTER APPLICATIONS ORGANIZATIONAL STRUCTURE ", Style::default().fg(Color::White)),
        Span::styled(format!("[{} APPS] ", total_apps), Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        Span::styled(format!("[{} ONLINE] ", online_count), Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
        Span::styled(format!("[PROBE {:.1}ms] ", state.scan_time_ms), Style::default().fg(Color::Magenta)),
        Span::styled("[RULE #0 ZERO-MOCK]", Style::default().fg(Color::LightYellow)),
    ]);

    let block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Cyan))
        .title(header_text);

    f.render_widget(block, area);
}

fn draw_domain_tabs(f: &mut Frame, state: &UiState, area: Rect) {
    let domains = AppDomain::all();
    let titles: Vec<Line> = domains
        .iter()
        .map(|d| {
            let count = state.apps.iter().filter(|a| a.domain == *d).count();
            Line::from(format!(" {} ({}) ", d.short_name(), count))
        })
        .collect();

    let selected_idx = domains
        .iter()
        .position(|d| *d == state.active_domain)
        .unwrap_or(0);

    let tabs = Tabs::new(titles)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::DarkGray))
                .title(Line::from(vec![
                    Span::styled(" 📂 Canonical Domains ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                    Span::styled("— Use [←/→] or [1-6] to switch domain", Style::default().fg(Color::Gray)),
                ])),
        )
        .select(selected_idx)
        .style(Style::default().fg(Color::Gray))
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        );

    f.render_widget(tabs, area);
}

fn draw_main_body(f: &mut Frame, state: &UiState, area: Rect) {
    let h_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(38), Constraint::Percentage(62)])
        .split(area);

    draw_app_tree_pane(f, state, h_chunks[0]);
    draw_app_details_pane(f, state, h_chunks[1]);
}

fn draw_app_tree_pane(f: &mut Frame, state: &UiState, area: Rect) {
    let filtered_apps: Vec<&AppEntry> = state
        .apps
        .iter()
        .filter(|a| a.domain == state.active_domain)
        .collect();

    let items: Vec<ListItem> = filtered_apps
        .iter()
        .enumerate()
        .map(|(idx, app)| {
            let status = state.statuses.get(app.id);
            let (status_dot, dot_color) = if let Some(st) = status {
                if st.is_running && st.port_online {
                    ("🟢", Color::Green)
                } else if st.port_online {
                    ("🟢", Color::Green)
                } else if st.is_running {
                    ("🟡", Color::Yellow)
                } else {
                    ("⚪", Color::DarkGray)
                }
            } else {
                ("⚪", Color::DarkGray)
            };

            let port_badge = if let Some(p) = app.port {
                format!(" :{}", p)
            } else {
                "".to_string()
            };

            let is_selected = idx == state.selected_app_idx;
            let cursor = if is_selected { "▶ " } else { "  " };

            let content = Line::from(vec![
                Span::styled(cursor, if is_selected { Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD) } else { Style::default().fg(Color::DarkGray) }),
                Span::styled(format!("{} ", status_dot), Style::default().fg(dot_color)),
                Span::styled(format!("{} ", app.icon), Style::default()),
                Span::styled(
                    app.name,
                    if is_selected {
                        Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(Color::White)
                    },
                ),
                Span::styled(port_badge, Style::default().fg(Color::LightBlue)),
            ]);

            ListItem::new(content)
        })
        .collect();

    let title = format!(" 📱 {} ({} apps) ", state.active_domain.title(), filtered_apps.len());
    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Blue))
                .title(title),
        )
        .highlight_style(Style::default().bg(Color::Rgb(15, 23, 42)));

    f.render_widget(list, area);
}

fn draw_app_details_pane(f: &mut Frame, state: &UiState, area: Rect) {
    let filtered_apps: Vec<&AppEntry> = state
        .apps
        .iter()
        .filter(|a| a.domain == state.active_domain)
        .collect();

    let selected_app = if filtered_apps.is_empty() {
        None
    } else {
        let idx = state.selected_app_idx.min(filtered_apps.len() - 1);
        Some(filtered_apps[idx])
    };

    let v_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(12), Constraint::Min(8)])
        .split(area);

    if let Some(app) = selected_app {
        draw_detail_card(f, state, app, v_chunks[0]);
        draw_readme_preview(f, state, app, v_chunks[1]);
    } else {
        let empty_msg = Paragraph::new("No applications registered in this domain.")
            .style(Style::default().fg(Color::DarkGray));
        f.render_widget(empty_msg, area);
    }
}

fn draw_detail_card(f: &mut Frame, state: &UiState, app: &AppEntry, area: Rect) {
    let status = state.statuses.get(app.id);
    let status_str = status.map(|s| s.status_label.as_str()).unwrap_or("⚪ STOPPED");

    let port_str = if let Some(p) = app.port {
        format!("Port {}", p)
    } else {
        "Headless / No Port".to_string()
    };

    let url_str = app.url.unwrap_or("--");

    let card_rows = vec![
        Row::new(vec![
            Cell::from(Span::styled("• Name / ID:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(format!("{} {} ({})", app.icon, app.name, app.id), Style::default().fg(Color::White).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled("• Live Status:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(status_str, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("• Primary Port:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(port_str, Style::default().fg(Color::Cyan))),
            Cell::from(Span::styled("• Web URL:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(url_str, Style::default().fg(Color::LightCyan))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("• Directory:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(app.path, Style::default().fg(Color::Magenta))),
            Cell::from(Span::styled("• Tech Stack:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(app.tech_stack.join(" • "), Style::default().fg(Color::LightBlue))),
        ]),
        Row::new(vec![
            Cell::from(Span::styled("• Launch Cmd:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(format!("[s] {}", app.launch_cmd), Style::default().fg(Color::Gray))),
            Cell::from(Span::styled("• Test Cmd:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD))),
            Cell::from(Span::styled(format!("[t] {}", app.test_cmd), Style::default().fg(Color::Gray))),
        ]),
    ];

    let widths = [
        Constraint::Length(14),
        Constraint::Percentage(40),
        Constraint::Length(14),
        Constraint::Percentage(46),
    ];

    let table = Table::new(card_rows, widths)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Cyan))
                .title(Line::from(vec![
                    Span::styled(" 📋 Application Profile & Controls ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                    Span::styled("— [s] Start • [k] Kill • [t] Test • [o] Open", Style::default().fg(Color::Yellow)),
                ])),
        );

    f.render_widget(table, area);
}

fn draw_readme_preview(f: &mut Frame, _state: &UiState, app: &AppEntry, area: Rect) {
    let mut lines = Vec::new();
    lines.push(Line::from(vec![
        Span::styled("📖 Summary: ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
        Span::styled(app.description, Style::default().fg(Color::White)),
    ]));
    lines.push(Line::from(""));

    lines.push(Line::from(vec![
        Span::styled("📂 Codebase Architecture Documentation Preview:", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
    ]));

    for l in _state.readme_lines.iter().take(12) {
        let style = if l.starts_with("# ") {
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)
        } else if l.starts_with("## ") {
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)
        } else if l.starts_with("- ") || l.starts_with("* ") {
            Style::default().fg(Color::LightGreen)
        } else {
            Style::default().fg(Color::Gray)
        };
        lines.push(Line::from(Span::styled(l.as_str(), style)));
    }

    let paragraph = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::DarkGray))
                .title(" 📄 Architecture README & Technical Spec "),
        )
        .wrap(Wrap { trim: true });

    f.render_widget(paragraph, area);
}

fn draw_footer(f: &mut Frame, state: &UiState, area: Rect) {
    let footer_text = Line::from(vec![
        Span::styled(" KEYBINDINGS: ", Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled(" [↑/↓] Navigate • [←/→] Domain • [Enter/o] Open in Browser • [s] Start • [k] Kill • [t] Test • [r] Refresh • [q] Quit ", Style::default().fg(Color::White)),
        Span::styled(format!("| {}", state.status_msg), Style::default().fg(Color::Yellow)),
    ]);

    let block = Paragraph::new(footer_text)
        .style(Style::default().bg(Color::Rgb(10, 15, 25)));

    f.render_widget(block, area);
}
