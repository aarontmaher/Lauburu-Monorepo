pub mod api_scanner;
pub mod chat;
pub mod footer;
pub mod header;
pub mod sharding;
pub mod topology;
pub mod training;
pub mod voice_coding;
pub mod web_lens;
pub mod healer;

use crate::app::{App, Tab};
use ratatui::layout::{Alignment, Constraint, Direction, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Paragraph};
use ratatui::Frame;

/// Minimum safe viewport dimensions to prevent layout panics
pub const MIN_VIEWPORT_WIDTH: u16 = 50;
pub const MIN_VIEWPORT_HEIGHT: u16 = 12;

/// Master UI render entrypoint coordinating header, active tab view, and footer.
pub fn render(app: &mut App, frame: &mut Frame) {
    let area = frame.area();
    app.terminal_size = (area.width, area.height);

    // Adversarial Viewport Defense: Protect against micro-viewports (<50x12)
    if area.width < MIN_VIEWPORT_WIDTH || area.height < MIN_VIEWPORT_HEIGHT {
        let warning_block = Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Red));

        let warning_lines = vec![
            Line::from(vec![
                Span::styled(
                    "⚠️ Viewport Too Small",
                    Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
                ),
            ]),
            Line::from(vec![
                Span::styled(
                    format!(
                        "Current: {}x{} | Minimum: {}x{}",
                        area.width, area.height, MIN_VIEWPORT_WIDTH, MIN_VIEWPORT_HEIGHT
                    ),
                    Style::default().fg(Color::Yellow),
                ),
            ]),
            Line::from(vec![
                Span::styled("Please enlarge your terminal window.", Style::default().fg(Color::White)),
            ]),
        ];

        let warning_paragraph = Paragraph::new(warning_lines)
            .block(warning_block)
            .alignment(Alignment::Center);

        frame.render_widget(warning_paragraph, area);
        return;
    }

    // Enforce high-contrast dark cyberpunk theme across all terminal backgrounds
    let root_block = Block::default().style(Style::default().bg(Color::Rgb(15, 17, 26)).fg(Color::Rgb(220, 225, 235)));
    frame.render_widget(root_block, area);

    // Standard 3-tier layout: Header (3), Body (Min 10), Footer (3)
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(10),
            Constraint::Length(3),
        ])
        .split(area);

    header::render(app, frame, chunks[0]);

    match app.current_tab {
        Tab::Topology => topology::render(app, frame, chunks[1]),
        Tab::Chat => chat::render(app, frame, chunks[1]),
        Tab::Sharding => sharding::render(app, frame, chunks[1]),
        Tab::ApiScanner => api_scanner::render(app, frame, chunks[1]),
        Tab::Training => training::render(app, frame, chunks[1]),
        Tab::WebLens => web_lens::render(app, frame, chunks[1]),
        Tab::VoiceCoding => voice_coding::render(app, frame, chunks[1]),
        Tab::Healer => healer::render(app, frame, chunks[1]),
    }

    footer::render(app, frame, chunks[2]);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app::App;
    use crate::config::MeshConfig;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn test_micro_viewport_renders_fallback_warning() {
        let backend = TestBackend::new(40, 10);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        assert!(
            rendered_text.contains("Viewport Too Small"),
            "Micro viewport should render fallback warning banner"
        );
    }

    #[test]
    fn test_standard_viewport_renders_topology_tab() {
        let backend = TestBackend::new(120, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        // Verify Core PRP Ring elements
        assert!(rendered_text.contains("Mac Mini"), "Must render Mac Mini node");
        assert!(rendered_text.contains("MBP"), "Must render MBP node");
        assert!(rendered_text.contains("Pipelined-Ring Parallelism"), "Must render PRP flow diagram");

        // Verify Edge RPC Pool elements
        assert!(rendered_text.contains("Pixel 10"), "Must render Pixel 10 node");
        assert!(rendered_text.contains("Edge RPC Pool"), "Must render Edge Pool title");

        // Verify Header & Metrics
        assert!(rendered_text.contains("Ring Topology"), "Must render active tab title");
        assert!(rendered_text.contains("AI VRAM"), "Must render VRAM metrics");
    }

    #[test]
    fn test_chat_tab_renders_cleanly() {
        let backend = TestBackend::new(120, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(Tab::Chat);

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        assert!(rendered_text.contains("Chat Stream"), "Must render Chat tab header");
        assert!(rendered_text.contains("Prompt Input"), "Must render Prompt Input box");
    }

    #[test]
    fn test_sharding_tab_renders_cleanly() {
        let backend = TestBackend::new(120, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(Tab::Sharding);

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        assert!(rendered_text.contains("Sharding"), "Must render Sharding tab header");
        assert!(rendered_text.contains("Decision Tree"), "Must render Decision Tree banner");
    }

    #[test]
    fn test_api_scanner_tab_renders_cleanly() {
        let backend = TestBackend::new(120, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(Tab::ApiScanner);

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        assert!(rendered_text.contains("API Scanner"), "Must render API Scanner tab header");
        assert!(rendered_text.contains("$0 Cloud Spend Velocity"), "Must render Spend Velocity Dashboard");
    }

    #[test]
    fn test_training_tab_renders_cleanly() {
        let backend = TestBackend::new(120, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(Tab::Training);

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        assert!(rendered_text.contains("Training"), "Must render Training tab header");
        assert!(rendered_text.contains("RAM Governor"), "Must render RAM Governor Status");
    }

    #[test]
    fn test_web_lens_tab_renders_cleanly() {
        let backend = TestBackend::new(120, 30);
        let mut terminal = Terminal::new(backend).unwrap();

        let mut app = App::new(MeshConfig::fallback());
        app.switch_tab(Tab::WebLens);

        terminal
            .draw(|frame| {
                render(&mut app, frame);
            })
            .unwrap();

        let buffer = terminal.backend().buffer();
        let rendered_text: String = buffer
            .content
            .iter()
            .map(|cell| cell.symbol())
            .collect();

        assert!(rendered_text.contains("Web Lens"), "Must render Web Lens tab header");
        assert!(rendered_text.contains("Token Economics"), "Must render Token Economics sidebar");
    }
}
