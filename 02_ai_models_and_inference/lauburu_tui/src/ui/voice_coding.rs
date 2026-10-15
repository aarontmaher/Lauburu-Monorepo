use crate::app::App;
use crate::voice_coding::VoiceStatus;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph, Wrap};
use ratatui::Frame;

/// Render the Voice Coding Studio tab.
pub fn render(app: &mut App, frame: &mut Frame, area: Rect) {
    let main_chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Top VU Meter & Status Bar
            Constraint::Length(9), // Control Panel & Spoken Prompt Box
            Constraint::Min(10),   // Generated Code Block & Artifact
        ])
        .split(area);

    // ==================== 1. TOP VU METER & STATUS ====================
    let vu_blocks = match (app.voice_coding.vu_meter_level * 10.0) as usize {
        0..=1 => "   ",
        2..=3 => " ▂ ",
        4..=5 => " ▂▃▅",
        6..=7 => " ▂▃▅▆▇",
        _ => " ▂▃▅▆▇█",
    };

    let status_span = match &app.voice_coding.voice_status {
        VoiceStatus::Idle => Span::styled(" [IDLE] ", Style::default().fg(Color::DarkGray)),
        VoiceStatus::Listening => Span::styled(
            " [🔴 RECORDING AUDIO STREAM] ",
            Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        ),
        VoiceStatus::Synthesizing(engine) => Span::styled(
            format!(" [⚡ SYNTHESIZING VIA {}] ", engine),
            Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
        ),
        VoiceStatus::Ready(ms) => Span::styled(
            format!(" [✅ CODE SYNTHESIZED ({}ms | $0.00)] ", ms),
            Style::default().fg(Color::Green).add_modifier(Modifier::BOLD),
        ),
        VoiceStatus::Injected(dest) => Span::styled(
            format!(" [🚀 INJECTED INTO {}] ", dest),
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        ),
        VoiceStatus::Error(err) => Span::styled(
            format!(" [⚠️ ERROR: {}] ", err),
            Style::default().fg(Color::Red),
        ),
    };

    let vu_line = Line::from(vec![
        Span::styled("🎙️ Voice Source: ", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::styled(app.voice_coding.audio_source.name(), Style::default().fg(Color::White)),
        Span::styled(" │ Audio Level: ", Style::default().fg(Color::DarkGray)),
        Span::styled(format!("[{:<7}] ", vu_blocks), Style::default().fg(Color::LightGreen).add_modifier(Modifier::BOLD)),
        Span::styled(" │ Status: ", Style::default().fg(Color::DarkGray)),
        status_span,
    ]);

    let vu_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Cyan));
    let vu_widget = Paragraph::new(vu_line).block(vu_block).alignment(Alignment::Left);
    frame.render_widget(vu_widget, main_chunks[0]);

    // ==================== 2. CONTROL PANEL & PROMPT ====================
    let middle_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(40), // Left: Source / Target & Shortcuts
            Constraint::Percentage(60), // Right: Spoken Transcription Box
        ])
        .split(main_chunks[1]);

    // Left Panel: Configuration & Shortcuts
    let config_lines = vec![
        Line::from(vec![
            Span::styled("• Target Language   : ", Style::default().fg(Color::DarkGray)),
            Span::styled(
                app.voice_coding.target_lang.name(),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("• Code Destination  : ", Style::default().fg(Color::DarkGray)),
            Span::styled(
                app.voice_coding.target_destination.name(),
                Style::default().fg(Color::LightCyan),
            ),
        ]),
        Line::from(vec![
            Span::styled("• Model Pipeline    : ", Style::default().fg(Color::DarkGray)),
            Span::styled("Qwen 2.5 Coder 32B (:8081) / Huihui (:8083)", Style::default().fg(Color::Magenta)),
        ]),
        Line::from(vec![
            Span::styled("⌨️ [Space] Dictate  [Enter] Synthesize  [i] Inject  [t] Lang  [d] Dest", Style::default().fg(Color::Cyan)),
        ]),
    ];

    let config_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .title(" ⚙️ Voice Coding Engine ")
        .border_style(Style::default().fg(Color::Yellow));
    let config_widget = Paragraph::new(config_lines).block(config_block);
    frame.render_widget(config_widget, middle_chunks[0]);

    // Right Panel: TextArea for Prompt
    let prompt_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .title(" 🗣️ Spoken Intent / Speech-to-Text Transcription ")
        .border_style(Style::default().fg(Color::Green));
    app.voice_coding.prompt_input.set_block(prompt_block);
    frame.render_widget(&app.voice_coding.prompt_input, middle_chunks[1]);

    // ==================== 3. GENERATED CODE ARTIFACT ====================
    let mut code_lines = Vec::new();
    for (i, line) in app.voice_coding.generated_code.lines().enumerate() {
        code_lines.push(Line::from(vec![
            Span::styled(format!("{:>3} │ ", i + 1), Style::default().fg(Color::DarkGray)),
            Span::styled(line, Style::default().fg(Color::White)),
        ]));
    }

    let code_block = Block::default()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .title(format!(
            " 💻 Synthesized Code Artifact ({}) — Zero-Mock Local Engine ",
            app.voice_coding.target_lang.name()
        ))
        .border_style(Style::default().fg(Color::Magenta));
    let code_widget = Paragraph::new(code_lines)
        .block(code_block)
        .wrap(Wrap { trim: false });
    frame.render_widget(code_widget, main_chunks[2]);
}
