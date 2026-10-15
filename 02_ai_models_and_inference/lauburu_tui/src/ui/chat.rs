use crate::app::App;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph, Wrap};
use ratatui::Frame;

/// Render Tab 2: Embedded Chat Stream (Conversation History + TextArea Input).
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(8), Constraint::Length(4)])
        .split(area);

    // 1. Upper: Chat conversation history
    let master_ep = app.mesh_config.master_endpoint();
    let model_name = &app.mesh_config.mesh.default_model;
    let status_tag = if app.is_streaming {
        "● STREAMING"
    } else {
        "○ IDLE"
    };

    let title_spans = vec![
        Span::styled(" 💬 prima.cpp Chat Stream ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled(format!("({master_ep}) "), Style::default().fg(Color::DarkGray)),
        Span::styled(format!("[{model_name}] "), Style::default().fg(Color::Magenta)),
        Span::styled(
            format!("[{status_tag}] "),
            Style::default().fg(if app.is_streaming { Color::Yellow } else { Color::Green }).add_modifier(Modifier::BOLD),
        ),
    ];


    let history_block = Block::default()
        .title(Line::from(title_spans))
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(if app.is_streaming {
            Color::Yellow
        } else {
            Color::Cyan
        }));

    let mut lines: Vec<Line> = Vec::new();
    if app.chat_history.is_empty() {
        lines.push(Line::from(vec![
            Span::styled(
                "⚡ Welcome to Lauburu 7-Node Inference Mesh Control Plane.",
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            ),
        ]));
        lines.push(Line::from(vec![
            Span::styled(
                "Type a prompt below and press Enter to stream completions directly from prima.cpp master (127.0.0.1:8082).",
                Style::default().fg(Color::Gray),
            ),
        ]));
        lines.push(Line::from(vec![
            Span::styled(
                "Zero-Mock invariant: responses reflect authentic SSE tokens streamed from the physical mesh.",
                Style::default().fg(Color::DarkGray),
            ),
        ]));
    } else {
        for msg in &app.chat_history {
            let (role_badge, role_style) = match msg.role.to_lowercase().as_str() {
                "user" => ("[USER] ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                "assistant" => ("[ASSISTANT] ", Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                "system" => ("[SYSTEM] ", Style::default().fg(Color::Magenta).add_modifier(Modifier::BOLD)),
                _ => ("[AI] ", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            };

            let is_error = msg.content.starts_with("[Error:");
            let text_style = if is_error {
                Style::default().fg(Color::Red)
            } else {
                Style::default().fg(Color::White)
            };

            let msg_lines: Vec<&str> = msg.content.split('\n').collect();
            for (idx, m_line) in msg_lines.iter().enumerate() {
                if idx == 0 {
                    lines.push(Line::from(vec![
                        Span::styled(role_badge, role_style),
                        Span::styled(*m_line, text_style),
                    ]));
                } else {
                    let indent = "       "; // Indent under role badge
                    lines.push(Line::from(vec![
                        Span::raw(indent),
                        Span::styled(*m_line, text_style),
                    ]));
                }
            }
            lines.push(Line::default()); // Blank line spacer between messages
        }
    }

    let inner_height = chunks[0].height.saturating_sub(2);
    let total_lines = lines.len() as u16;
    let effective_scroll = if app.auto_scroll {
        if total_lines > inner_height {
            total_lines.saturating_sub(inner_height)
        } else {
            0
        }
    } else {
        app.scroll_offset
    };

    let history_paragraph = Paragraph::new(lines)
        .block(history_block)
        .wrap(Wrap { trim: false })
        .scroll((effective_scroll, 0))
        .alignment(Alignment::Left);

    frame.render_widget(history_paragraph, chunks[0]);

    // 2. Lower: Input TextArea widget
    let prompt_title = if app.is_streaming {
        " ⌨️ Prompt Input ([Esc/Ctrl+C] Cancel Stream) "
    } else {
        " ⌨️ Prompt Input ([Enter] Submit │ [Esc] Topology) "
    };

    let textarea_block = Block::default()
        .title(Span::styled(
            prompt_title,
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ))
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(if app.is_streaming {
            Color::Yellow
        } else {
            Color::Cyan
        }));

    app.textarea.set_block(textarea_block);
    frame.render_widget(&app.textarea, chunks[1]);
}

