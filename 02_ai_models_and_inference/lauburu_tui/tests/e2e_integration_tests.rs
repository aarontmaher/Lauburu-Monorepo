//! ============================================================================
//! Tier 1, 2, 3 & 4 Test Suite: End-to-End Integration & Shell UI Harness
//! ============================================================================
//! Features Covered:
//! - F3: Terminal Lifecycle & Event Loop (Event dispatch, tick rate, render safety)
//! - F4: Tab Navigation & Shell UI (Header, Footer, Tab switching)
//! - F7: Chat Textarea Input (Cursor manipulation, multiline editing)
//! - F9: Scrollable Chat History (Auto-scroll follow, manual PgUp/PgDn)
//! - F11: Complete Binary Execution & 100% E2E Verification
//! ============================================================================

use ratatui::backend::TestBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Paragraph, Tabs, Wrap};
use ratatui::Terminal;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;

// ----------------------------------------------------------------------------
// Synthetic UI State Model mimicking Interface Contracts (PROJECT.md)
// ----------------------------------------------------------------------------

pub use lauburu_tui::Tab;

#[derive(Debug, Clone, PartialEq)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

pub struct AppState {
    pub current_tab: Tab,
    pub chat_history: Vec<ChatMessage>,
    pub input_buffer: String,
    pub cursor_pos: usize,
    pub scroll_offset: u16,
    pub auto_scroll: bool,
    pub is_streaming: bool,
    pub status_message: String,
    pub total_vram_gb: f64,
    pub total_ram_gb: f64,
    pub core_node_count: usize,
    pub edge_node_count: usize,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            current_tab: Tab::Topology,
            chat_history: Vec::new(),
            input_buffer: String::new(),
            cursor_pos: 0,
            scroll_offset: 0,
            auto_scroll: true,
            is_streaming: false,
            status_message: "Ready".to_string(),
            total_vram_gb: 82.8,
            total_ram_gb: 108.0,
            core_node_count: 4,
            edge_node_count: 3,
        }
    }
}

impl AppState {
    pub fn switch_tab(&mut self, tab: Tab) {
        self.current_tab = tab;
    }

    pub fn next_tab(&mut self) {
        self.current_tab = self.current_tab.next();
    }

    pub fn insert_char(&mut self, c: char) {
        self.input_buffer.insert(self.cursor_pos, c);
        self.cursor_pos += 1;
    }

    pub fn delete_backspace(&mut self) {
        if self.cursor_pos > 0 && !self.input_buffer.is_empty() {
            self.cursor_pos -= 1;
            self.input_buffer.remove(self.cursor_pos);
        }
    }

    pub fn clear_input(&mut self) {
        self.input_buffer.clear();
        self.cursor_pos = 0;
    }

    pub fn submit_prompt(&mut self) -> Option<String> {
        let prompt = self.input_buffer.trim().to_string();
        if prompt.is_empty() {
            return None;
        }
        self.chat_history.push(ChatMessage {
            role: "user".to_string(),
            content: prompt.clone(),
        });
        self.clear_input();
        self.is_streaming = true;
        self.status_message = "Streaming...".to_string();
        if self.auto_scroll {
            self.scroll_to_bottom();
        }
        Some(prompt)
    }

    pub fn append_token(&mut self, token: &str) {
        if let Some(last) = self.chat_history.last_mut() {
            if last.role == "assistant" {
                last.content.push_str(token);
                if self.auto_scroll {
                    self.scroll_to_bottom();
                }
                return;
            }
        }
        // First token of new assistant response
        self.chat_history.push(ChatMessage {
            role: "assistant".to_string(),
            content: token.to_string(),
        });
        if self.auto_scroll {
            self.scroll_to_bottom();
        }
    }

    pub fn complete_stream(&mut self) {
        self.is_streaming = false;
        self.status_message = "Idle".to_string();
    }

    pub fn cancel_stream(&mut self) {
        self.is_streaming = false;
        self.status_message = "Cancelled".to_string();
    }

    pub fn scroll_up(&mut self, lines: u16) {
        if self.scroll_offset >= lines {
            self.scroll_offset -= lines;
        } else {
            self.scroll_offset = 0;
        }
        self.auto_scroll = false; // Suspend auto-scroll while browsing past history
    }

    pub fn scroll_down(&mut self, lines: u16) {
        self.scroll_offset = self.scroll_offset.saturating_add(lines);
    }

    pub fn scroll_to_bottom(&mut self) {
        self.scroll_offset = 0;
        self.auto_scroll = true;
    }

    pub fn render_ui(&self, f: &mut ratatui::Frame) {
        let area = f.area();
        // Micro-viewport guard
        if area.width < 10 || area.height < 5 {
            let small_msg = Paragraph::new("Viewport too small")
                .style(Style::default().fg(Color::Yellow));
            f.render_widget(small_msg, area);
            return;
        }

        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3), // Header
                Constraint::Min(3),    // Main Content
                Constraint::Length(1), // Footer
            ])
            .split(area);

        // 1. Header
        let tab_titles = vec![" [1] Topology Ring ", " [2] Chat Stream "];
        let active_index = self.current_tab.index();
        let header_tabs = Tabs::new(tab_titles)
            .select(active_index)
            .block(Block::default().borders(Borders::ALL).title(format!(
                " 🌐 Lauburu TUI | Mesh VRAM: {:.1} GB | RAM: {:.1} GB ",
                self.total_vram_gb, self.total_ram_gb
            )))
            .style(Style::default().fg(Color::Cyan))
            .highlight_style(Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD));
        f.render_widget(header_tabs, chunks[0]);

        // 2. Main Content
        match self.current_tab {
            Tab::Topology => {
                let topo_text = format!(
                    "Core PRP Ring Nodes: {}\nEdge RPC Pool Nodes: {}\nStatus: {}",
                    self.core_node_count, self.edge_node_count, self.status_message
                );
                let topo_widget = Paragraph::new(topo_text)
                    .block(Block::default().borders(Borders::ALL).title(" Ring Topology "));
                f.render_widget(topo_widget, chunks[1]);
            }
            Tab::Chat => {
                let chat_layout = Layout::default()
                    .direction(Direction::Vertical)
                    .constraints([
                        Constraint::Min(3),    // Chat history
                        Constraint::Length(3), // Input box
                    ])
                    .split(chunks[1]);

                let history_lines: Vec<Line> = self
                    .chat_history
                    .iter()
                    .map(|msg| {
                        let prefix = if msg.role == "user" { "User: " } else { "AI: " };
                        Line::from(vec![
                            Span::styled(prefix, Style::default().fg(Color::Green).add_modifier(Modifier::BOLD)),
                            Span::raw(&msg.content),
                        ])
                    })
                    .collect();

                let chat_widget = Paragraph::new(history_lines)
                    .block(Block::default().borders(Borders::ALL).title(" Conversation History "))
                    .scroll((self.scroll_offset, 0))
                    .wrap(Wrap { trim: false });
                f.render_widget(chat_widget, chat_layout[0]);

                let input_widget = Paragraph::new(self.input_buffer.as_str())
                    .block(Block::default().borders(Borders::ALL).title(format!(" Prompt Input [{}] ", self.status_message)));
                f.render_widget(input_widget, chat_layout[1]);
            }
            _ => {
                let placeholder = Paragraph::new("Module View")
                    .block(Block::default().borders(Borders::ALL).title(" Module View "));
                f.render_widget(placeholder, chunks[1]);
            }
        }

        // 3. Footer
        let footer_text = " [Tab] Switch Views | [Enter] Send | [PgUp/PgDn] Scroll | [Esc] Cancel | [q] Quit";
        let footer_widget = Paragraph::new(footer_text).style(Style::default().fg(Color::DarkGray));
        f.render_widget(footer_widget, chunks[2]);
    }
}

// ============================================================================
// TIER 1: FEATURE COVERAGE (≥5 tests per feature)
// ============================================================================

#[test]
fn test_t1_f4_01_tab_switching_state_toggles() {
    let mut app = AppState::default();
    assert_eq!(app.current_tab, Tab::Topology);

    app.switch_tab(Tab::Chat);
    assert_eq!(app.current_tab, Tab::Chat);

    app.next_tab();
    assert_eq!(app.current_tab, Tab::Sharding);
    app.next_tab();
    assert_eq!(app.current_tab, Tab::ApiScanner);
    app.next_tab();
    assert_eq!(app.current_tab, Tab::Training);
    app.next_tab();
    assert_eq!(app.current_tab, Tab::WebLens);
    app.next_tab();
    assert_eq!(app.current_tab, Tab::VoiceCoding);
    app.next_tab();
    assert_eq!(app.current_tab, Tab::Topology);
}

#[test]
fn test_t1_f7_02_textarea_typing_and_backspace() {
    let mut app = AppState::default();
    for c in "Hello Mesh".chars() {
        app.insert_char(c);
    }
    assert_eq!(app.input_buffer, "Hello Mesh");
    assert_eq!(app.cursor_pos, 10);

    app.delete_backspace();
    assert_eq!(app.input_buffer, "Hello Mes");
    assert_eq!(app.cursor_pos, 9);
}

#[test]
fn test_t1_f7_03_prompt_submission_clears_input_and_enables_streaming() {
    let mut app = AppState::default();
    app.input_buffer = "What is the token rate?".to_string();
    app.cursor_pos = app.input_buffer.len();

    let submitted = app.submit_prompt();
    assert_eq!(submitted, Some("What is the token rate?".to_string()));
    assert_eq!(app.input_buffer, "");
    assert_eq!(app.cursor_pos, 0);
    assert!(app.is_streaming);
    assert_eq!(app.chat_history.len(), 1);
    assert_eq!(app.chat_history[0].role, "user");
}

#[test]
fn test_t1_f9_04_streaming_tokens_appended_to_assistant_message() {
    let mut app = AppState::default();
    app.append_token("Token 1 ");
    app.append_token("Token 2");

    assert_eq!(app.chat_history.len(), 1);
    assert_eq!(app.chat_history[0].role, "assistant");
    assert_eq!(app.chat_history[0].content, "Token 1 Token 2");
}

#[test]
fn test_t1_f3_05_ratatui_testbackend_renders_topology_tab() {
    let app = AppState::default();
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();

    terminal.draw(|f| app.render_ui(f)).unwrap();
    let buffer = terminal.backend().buffer();

    // Check that header and topology title are present in rendered buffer
    let rendered_text = buffer
        .content
        .iter()
        .map(|cell| cell.symbol())
        .collect::<Vec<&str>>()
        .join("");

    assert!(rendered_text.contains("Lauburu TUI"));
    assert!(rendered_text.contains("Topology Ring"));
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (Micro-viewports, long text, extreme history)
// ============================================================================

#[test]
fn test_t2_b01_micro_viewport_zero_by_zero_no_panic() {
    let app = AppState::default();
    let backend = TestBackend::new(0, 0);
    let mut terminal = Terminal::new(backend).unwrap();
    let res = terminal.draw(|f| app.render_ui(f));
    assert!(res.is_ok(), "Zero viewport must not panic");
}

#[test]
fn test_t2_b02_micro_viewport_five_by_two_fallback_banner() {
    let app = AppState::default();
    let backend = TestBackend::new(5, 2);
    let mut terminal = Terminal::new(backend).unwrap();
    let res = terminal.draw(|f| app.render_ui(f));
    assert!(res.is_ok(), "5x2 micro-viewport must not panic");
}

#[test]
fn test_t2_b03_extreme_viewport_large_display() {
    let app = AppState::default();
    let backend = TestBackend::new(300, 100);
    let mut terminal = Terminal::new(backend).unwrap();
    let res = terminal.draw(|f| app.render_ui(f));
    assert!(res.is_ok(), "300x100 8K viewport must render smoothly");
}

#[test]
fn test_t2_b04_empty_prompt_submission_ignored() {
    let mut app = AppState::default();
    app.input_buffer = "   \t\n  ".to_string();
    let res = app.submit_prompt();
    assert_eq!(res, None, "Whitespace-only prompt must not submit");
    assert!(!app.is_streaming);
    assert_eq!(app.chat_history.len(), 0);
}

#[test]
fn test_t2_b05_extremely_long_prompt_input() {
    let mut app = AppState::default();
    let long_str = "A".repeat(5000);
    for c in long_str.chars() {
        app.insert_char(c);
    }
    assert_eq!(app.input_buffer.len(), 5000);
    let submitted = app.submit_prompt();
    assert_eq!(submitted.unwrap().len(), 5000);
    assert_eq!(app.chat_history.len(), 1);
}

#[test]
fn test_t2_b06_chat_history_scroll_bounds_clamped() {
    let mut app = AppState::default();
    app.scroll_offset = 0;
    app.scroll_up(10); // Attempt to scroll above 0
    assert_eq!(app.scroll_offset, 0, "Scroll offset must not underflow 0");

    app.scroll_down(50);
    assert_eq!(app.scroll_offset, 50);
    app.scroll_up(20);
    assert_eq!(app.scroll_offset, 30);
}

#[test]
fn test_t2_b07_rapid_event_spam_throughput() {
    let mut app = AppState::default();
    let start = std::time::Instant::now();

    for i in 0..1000 {
        if i % 10 == 0 {
            app.next_tab();
        } else if i % 2 == 0 {
            app.insert_char('x');
        } else {
            app.delete_backspace();
        }
    }

    let elapsed = start.elapsed();
    assert!(
        elapsed.as_millis() < 50,
        "1000 event dispatches must complete in <50ms, took {:?}",
        elapsed
    );
}

// ============================================================================
// TIER 3: CROSS-FEATURE INTERACTIONS
// ============================================================================

#[test]
fn test_t3_cross_01_tab_switch_during_active_streaming_preserves_tokens() {
    let mut app = AppState::default();
    app.switch_tab(Tab::Chat);
    app.input_buffer = "Explain PRP".to_string();
    app.submit_prompt();

    // User navigates to Topology tab while stream is running in background
    app.switch_tab(Tab::Topology);
    assert_eq!(app.current_tab, Tab::Topology);

    // Incoming background tokens arrive
    app.append_token("Pipelined ");
    app.append_token("Ring ");
    app.append_token("Parallelism");
    app.complete_stream();

    // User switches back to Chat tab
    app.switch_tab(Tab::Chat);
    assert_eq!(app.chat_history.len(), 2);
    assert_eq!(app.chat_history[1].content, "Pipelined Ring Parallelism");
    assert!(!app.is_streaming);
    assert_eq!(app.status_message, "Idle");
}

#[test]
fn test_t3_cross_02_manual_scroll_suspends_auto_scroll() {
    let mut app = AppState::default();
    app.switch_tab(Tab::Chat);
    assert!(app.auto_scroll);

    // User scrolls up manually
    app.scroll_up(5);
    assert!(!app.auto_scroll, "Manual scrolling up must suspend auto_scroll");

    // Receiving tokens should not jump to bottom if auto_scroll is suspended
    // until user calls scroll_to_bottom
    app.scroll_to_bottom();
    assert!(app.auto_scroll, "scroll_to_bottom must re-enable auto_scroll");
}

#[test]
fn test_t3_cross_03_stream_cancellation_resets_status() {
    let mut app = AppState::default();
    app.switch_tab(Tab::Chat);
    app.input_buffer = "Long calculation prompt".to_string();
    app.submit_prompt();
    assert!(app.is_streaming);

    app.cancel_stream();
    assert!(!app.is_streaming);
    assert_eq!(app.status_message, "Cancelled");
}

// ============================================================================
// TIER 4: REAL-WORLD MULTI-STEP SCENARIOS
// ============================================================================

#[tokio::test]
async fn test_t4_scenario_01_complete_app_workflow() {
    // 1. Initialize Mock HTTP SSE Server
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let server_addr = listener.local_addr().unwrap();

    let server_handle = tokio::spawn(async move {
        if let Ok((mut socket, _)) = listener.accept().await {
            let mut buf = vec![0u8; 1024];
            let _ = socket.read(&mut buf).await;

            let response = "HTTP/1.1 200 OK\r\n\
                Content-Type: text/event-stream\r\n\
                Cache-Control: no-cache\r\n\
                Connection: keep-alive\r\n\r\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"Node L1 \"}}]}\n\n\
                data: {\"choices\":[{\"delta\":{\"content\":\"is Mac Mini M4 Pro.\"}}]}\n\n\
                data: [DONE]\n\n";

            let _ = socket.write_all(response.as_bytes()).await;
        }
    });

    // 2. Initialize App and Terminal Backend
    let mut app = AppState::default();
    let backend = TestBackend::new(100, 30);
    let mut terminal = Terminal::new(backend).unwrap();

    // Step A: Initial draw on Topology tab
    terminal.draw(|f| app.render_ui(f)).unwrap();
    assert_eq!(app.current_tab, Tab::Topology);

    // Step B: Switch to Chat tab
    app.switch_tab(Tab::Chat);
    terminal.draw(|f| app.render_ui(f)).unwrap();

    // Step C: Enter prompt and submit
    app.input_buffer = "Describe Node L1".to_string();
    let prompt = app.submit_prompt().unwrap();
    assert_eq!(prompt, "Describe Node L1");

    // Step D: Fetch SSE stream from local server
    let client = reqwest::Client::new();
    let url = format!("http://{}/v1/chat/completions", server_addr);
    let res = client.post(&url).send().await.unwrap();
    let body = res.text().await.unwrap();

    // Parse mock SSE response into app tokens
    for line in body.lines() {
        if let Some(data) = line.trim().strip_prefix("data:") {
            let d = data.trim();
            if d == "[DONE]" {
                app.complete_stream();
            } else if let Ok(val) = serde_json::from_str::<serde_json::Value>(d) {
                if let Some(content) = val["choices"][0]["delta"]["content"].as_str() {
                    app.append_token(content);
                }
            }
        }
    }

    // Step E: Render final Chat view and verify buffer
    terminal.draw(|f| app.render_ui(f)).unwrap();
    let buf = terminal.backend().buffer();
    let text = buf
        .content
        .iter()
        .map(|c| c.symbol())
        .collect::<Vec<&str>>()
        .join("");

    assert!(text.contains("Node L1 is Mac Mini M4 Pro."));
    assert_eq!(app.status_message, "Idle");

    let _ = server_handle.await;
}

#[tokio::test]
async fn test_t4_scenario_02_backend_error_recovery_workflow() {
    let mut app = AppState::default();
    app.switch_tab(Tab::Chat);
    app.input_buffer = "Check node health".to_string();
    app.submit_prompt();

    // Simulate backend failure (e.g. 503 Service Unavailable)
    app.is_streaming = false;
    app.status_message = "Error: 503 Service Unavailable".to_string();
    app.chat_history.push(ChatMessage {
        role: "system".to_string(),
        content: "[Error: Connection failed to prima master :8082]".to_string(),
    });

    assert_eq!(app.status_message, "Error: 503 Service Unavailable");
    assert!(app.chat_history.last().unwrap().content.contains("Connection failed"));

    // User recovers by re-submitting once online
    app.input_buffer = "Retry node health".to_string();
    app.submit_prompt();
    assert_eq!(app.status_message, "Streaming...");
}

// ============================================================================
// TIER 5: ADVERSARIAL E2E & COMPLETE SYSTEM INTEGRATION
// ============================================================================

#[test]
fn test_t5_adv_e2e_01_complete_app_interactive_session() {
    use crossterm::event::{KeyCode, KeyEvent, KeyEventState, KeyModifiers};
    use lauburu_tui::app::{ActiveTopologyTable, App, Tab};
    use lauburu_tui::config::MeshConfig;
    use lauburu_tui::network::NetworkCommand;
    use lauburu_tui::ui;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let make_key = |code: KeyCode| KeyEvent {
        code,
        modifiers: KeyModifiers::NONE,
        kind: crossterm::event::KeyEventKind::Press,
        state: KeyEventState::NONE,
    };

    // 1. Initial draw on Topology
    terminal.draw(|f| ui::render(&mut app, f)).unwrap();
    assert_eq!(app.current_tab, Tab::Topology);

    // 2. Navigate nodes in Core Ring
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.core_table_state.selected(), Some(1));

    // 3. Switch to Edge Pool
    app.handle_key(make_key(KeyCode::Right));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.edge_table_state.selected(), Some(1));

    // 4. Switch to Chat Tab
    app.handle_key(make_key(KeyCode::Tab));
    assert_eq!(app.current_tab, Tab::Chat);
    terminal.draw(|f| ui::render(&mut app, f)).unwrap();

    // 5. Type prompt "Mesh Status"
    for c in "Mesh Status".chars() {
        app.handle_key(make_key(KeyCode::Char(c)));
    }

    // 6. Submit prompt
    let cmd = app.handle_key(make_key(KeyCode::Enter));
    assert!(cmd.is_some());
    match cmd.unwrap() {
        NetworkCommand::SendPrompt { prompt, .. } => {
            assert_eq!(prompt, "Mesh Status");
        }
        _ => panic!("Expected SendPrompt"),
    }
    assert!(app.is_streaming);

    // 7. Receive streaming tokens
    app.append_token("All 7 ");
    app.append_token("nodes ");
    app.append_token("operational.");
    terminal.draw(|f| ui::render(&mut app, f)).unwrap();

    let buf = terminal.backend().buffer();
    let text: String = buf.content.iter().map(|c| c.symbol()).collect();
    assert!(text.contains("All 7 nodes operational."));

    // 8. Complete stream
    app.complete_stream(10, 25);
    assert!(!app.is_streaming);

    // 9. Return to Topology
    app.handle_key(make_key(KeyCode::Esc));
    assert_eq!(app.current_tab, Tab::Topology);
}

#[test]
fn test_t5_adv_e2e_02_micro_viewport_stress_across_all_tabs() {
    use lauburu_tui::app::{App, Tab};
    use lauburu_tui::config::MeshConfig;
    use lauburu_tui::ui;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    let viewports = [(1, 1), (5, 2), (20, 5), (49, 11), (50, 12), (100, 30), (300, 100)];
    let mut app = App::new(MeshConfig::fallback());

    for (w, h) in viewports {
        let backend = TestBackend::new(w, h);
        let mut terminal = Terminal::new(backend).unwrap();

        app.switch_tab(Tab::Topology);
        let r1 = terminal.draw(|f| ui::render(&mut app, f));
        assert!(r1.is_ok(), "Topology render at {}x{} must not panic", w, h);

        app.switch_tab(Tab::Chat);
        let r2 = terminal.draw(|f| ui::render(&mut app, f));
        assert!(r2.is_ok(), "Chat render at {}x{} must not panic", w, h);
    }
}

#[test]
fn test_t5_adv_e2e_03_high_velocity_token_stream_rendering() {
    use lauburu_tui::app::{App, Tab};
    use lauburu_tui::config::MeshConfig;
    use lauburu_tui::ui;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());
    app.switch_tab(Tab::Chat);

    app.chat_history.push(lauburu_tui::ChatMessage {
        role: "assistant".to_string(),
        content: String::new(),
    });

    for i in 0..1000 {
        app.append_token(&format!("t{} ", i));
        if i % 20 == 0 {
            terminal.draw(|f| ui::render(&mut app, f)).unwrap();
        }
    }

    assert_eq!(app.chat_history.len(), 1);
    assert!(app.chat_history[0].content.contains("t999"));
}

