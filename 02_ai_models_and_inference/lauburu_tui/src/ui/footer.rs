use crate::app::{App, Tab};
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};
use ratatui::Frame;

/// Render the footer component containing context-sensitive hotkeys and system status.
pub fn render(app: &App, frame: &mut Frame, area: Rect) {
    let outer_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::DarkGray));

    let inner_area = outer_block.inner(area);
    frame.render_widget(outer_block, area);

    let chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(70), Constraint::Percentage(30)])
        .split(inner_area);

    // Left: Hotkey help bar
    let hotkeys = match app.current_tab {
        Tab::Topology => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [1-5] ", Style::default().fg(Color::Yellow)),
            Span::styled("Direct Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [↑/↓] ", Style::default().fg(Color::Yellow)),
            Span::styled("Select Node ", Style::default().fg(Color::White)),
            Span::styled("│ [←/→] ", Style::default().fg(Color::Yellow)),
            Span::styled("Table Focus ", Style::default().fg(Color::White)),
            Span::styled("│ [r] ", Style::default().fg(Color::Yellow)),
            Span::styled("Reload ", Style::default().fg(Color::White)),
            Span::styled("│ [w] ", Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
            Span::styled("BT Wake ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
        Tab::Chat => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [Enter] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("Send Prompt ", Style::default().fg(Color::White)),
            Span::styled("│ [PgUp/PgDn] ", Style::default().fg(Color::Yellow)),
            Span::styled("Scroll ", Style::default().fg(Color::White)),
            Span::styled("│ [Esc] ", Style::default().fg(Color::Yellow)),
            Span::styled("Topology ", Style::default().fg(Color::White)),
            Span::styled("│ [Ctrl+C] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
        Tab::Sharding => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [1-5] ", Style::default().fg(Color::Yellow)),
            Span::styled("Direct Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [↑/↓] ", Style::default().fg(Color::Yellow)),
            Span::styled("Select Model ", Style::default().fg(Color::White)),
            Span::styled("│ [r] ", Style::default().fg(Color::Yellow)),
            Span::styled("Refresh ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
        Tab::ApiScanner => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [1-5] ", Style::default().fg(Color::Yellow)),
            Span::styled("Direct Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [↑/↓] ", Style::default().fg(Color::Yellow)),
            Span::styled("Select Endpoint ", Style::default().fg(Color::White)),
            Span::styled("│ [s/Enter] ", Style::default().fg(Color::Green)),
            Span::styled("Swap Model ", Style::default().fg(Color::White)),
            Span::styled("│ [r] ", Style::default().fg(Color::Yellow)),
            Span::styled("Rescan ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
        Tab::Training => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [1-6] ", Style::default().fg(Color::Yellow)),
            Span::styled("Direct Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [↑/↓] ", Style::default().fg(Color::Yellow)),
            Span::styled("Select Job ", Style::default().fg(Color::White)),
            Span::styled("│ [p] ", Style::default().fg(Color::Yellow)),
            Span::styled("Pause/Resume ", Style::default().fg(Color::White)),
            Span::styled("│ [s] ", Style::default().fg(Color::Green)),
            Span::styled("Sync Memory ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
        Tab::WebLens => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [u] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Edit URL ", Style::default().fg(Color::White)),
            Span::styled("│ [t] ", Style::default().fg(Color::LightCyan)),
            Span::styled("Cycle Extractor ", Style::default().fg(Color::White)),
            Span::styled("│ [j/k] ", Style::default().fg(Color::Yellow)),
            Span::styled("Scroll ", Style::default().fg(Color::White)),
            Span::styled("│ [1-5] ", Style::default().fg(Color::Green)),
            Span::styled("Presets ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
                Tab::Healer => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [r] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("Run Diagnostics ", Style::default().fg(Color::White)),
            Span::styled("│ [w] ", Style::default().fg(Color::LightCyan).add_modifier(Modifier::BOLD)),
            Span::styled("BT Wake ", Style::default().fg(Color::White)),
            Span::styled("│ [f] ", Style::default().fg(Color::LightCyan)),
            Span::styled("Force Failover ", Style::default().fg(Color::White)),
            Span::styled("│ [↑/↓] ", Style::default().fg(Color::Yellow)),
            Span::styled("Select Link ", Style::default().fg(Color::White)),
            Span::styled("│ [1-8] ", Style::default().fg(Color::Yellow)),
            Span::styled("Direct Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
        Tab::VoiceCoding => vec![
            Span::styled(" [Tab] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::styled("Switch Tab ", Style::default().fg(Color::White)),
            Span::styled("│ [Space] ", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
            Span::styled("Dictate ", Style::default().fg(Color::White)),
            Span::styled("│ [Enter] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
            Span::styled("Synthesize ", Style::default().fg(Color::White)),
            Span::styled("│ [t] ", Style::default().fg(Color::Yellow)),
            Span::styled("Lang ", Style::default().fg(Color::White)),
            Span::styled("│ [d] ", Style::default().fg(Color::Cyan)),
            Span::styled("Dest ", Style::default().fg(Color::White)),
            Span::styled("│ [s] ", Style::default().fg(Color::Magenta)),
            Span::styled("Audio Source ", Style::default().fg(Color::White)),
            Span::styled("│ [q/Esc] ", Style::default().fg(Color::Red)),
            Span::styled("Quit", Style::default().fg(Color::White)),
        ],
    };

    let hotkey_line = Line::from(hotkeys);
    let hotkey_paragraph = Paragraph::new(hotkey_line).alignment(Alignment::Left);
    frame.render_widget(hotkey_paragraph, chunks[0]);

    // Right: Status & Zero-Mock Invariant
    let status_spans = vec![
        Span::styled("● ", Style::default().fg(Color::Green)),
        Span::styled(&app.status_message, Style::default().fg(Color::Gray)),
        Span::styled(" ", Style::default()),
    ];
    let status_line = Line::from(status_spans);
    let status_paragraph = Paragraph::new(status_line).alignment(Alignment::Right);
    frame.render_widget(status_paragraph, chunks[1]);
}
