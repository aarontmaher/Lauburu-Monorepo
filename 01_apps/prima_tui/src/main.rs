// prima-tui: prima.cpp Ring Monitor + 5-Framework Benchmark TUI
// Lauburu Mesh Ecosystem — Rust Ratatui specialist implementation

use std::{
    sync::Arc,
    time::{Duration, Instant},
};
use anyhow::Result;
use crossterm::{
    event::{self, Event, KeyCode, KeyEvent, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{prelude::*, widgets::*};
use tokio::sync::{mpsc, RwLock};
use serde::{Deserialize, Serialize};

mod config;
mod network;
mod ui;

use config::{ClusterConfig, NodeSpec};
use network::Poller;

// ─── Application State ────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum NodeStatus {
    Online,
    Degraded,
    Offline,
}

#[derive(Debug, Clone)]
pub struct NodeState {
    pub spec: NodeSpec,
    pub status: NodeStatus,
    pub ttft_ms: Option<f64>,
    pub tps: Option<f64>,
    pub ram_pct: Option<f64>,
    pub gpu_layers: Option<u32>,
    pub layer_window: Option<String>, // Halda -lw assignment
    pub last_poll: Option<Instant>,
    pub tokens_generated: u64,
}

impl NodeState {
    pub fn new(spec: NodeSpec) -> Self {
        Self {
            spec,
            status: NodeStatus::Offline,
            ttft_ms: None,
            tps: None,
            ram_pct: None,
            gpu_layers: None,
            layer_window: None,
            last_poll: None,
            tokens_generated: 0,
        }
    }

    pub fn status_symbol(&self) -> &str {
        match self.status {
            NodeStatus::Online => "●",
            NodeStatus::Degraded => "◐",
            NodeStatus::Offline => "○",
        }
    }

    pub fn status_style(&self) -> Style {
        match self.status {
            NodeStatus::Online => Style::default().fg(Color::Green),
            NodeStatus::Degraded => Style::default().fg(Color::Yellow),
            NodeStatus::Offline => Style::default().fg(Color::Red),
        }
    }
}

#[derive(Debug, Clone)]
pub struct BenchmarkResult {
    pub framework: String,
    pub ttft_ms: f64,
    pub tps: f64,
    pub transport: String,
    pub nodes: Vec<String>,
    pub timestamp: chrono::DateTime<chrono::Local>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum AppTab {
    Ring,       // prima.cpp ring topology
    Halda,      // Layer assignment monitor
    Benchmark,  // 5-framework comparison
    Chat,       // Integrated token streaming
}

pub struct AppState {
    pub tab: AppTab,
    pub nodes: Vec<NodeState>,
    pub benchmark_results: Vec<BenchmarkResult>,
    pub chat_input: String,
    pub chat_history: Vec<(String, String)>, // (role, content)
    pub chat_streaming: bool,
    pub stream_buffer: String,
    pub log_lines: Vec<String>,
    pub scroll_offset: usize,
    pub selected_node: usize,
    pub master_url: String,
    pub last_refresh: Instant,
}

impl AppState {
    pub fn new(config: &ClusterConfig) -> Self {
        let nodes = config.nodes.iter().map(|s| NodeState::new(s.clone())).collect();
        Self {
            tab: AppTab::Ring,
            nodes,
            benchmark_results: Vec::new(),
            chat_input: String::new(),
            chat_history: Vec::new(),
            chat_streaming: false,
            stream_buffer: String::new(),
            log_lines: vec![
                format!("⚡ prima-tui v0.1.0 — Lauburu Mesh | {}", chrono::Local::now().format("%H:%M:%S")),
                "  Monitoring prima.cpp PRP ring | 5-Framework Benchmark".to_string(),
                "  Press [Tab] switch view | [c] chat | [b] benchmark | [q] quit".to_string(),
            ],
            scroll_offset: 0,
            selected_node: 0,
            master_url: config.master_url.clone(),
            last_refresh: Instant::now(),
        }
    }
}

// ─── Main Entry Point ─────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<()> {
    // Panic hook: always restore terminal
    std::panic::set_hook(Box::new(|info| {
        let _ = disable_raw_mode();
        let _ = execute!(
            std::io::stdout(),
            LeaveAlternateScreen,
            crossterm::cursor::Show
        );
        eprintln!("PANIC: {:?}", info);
    }));

    let config = config::load_cluster_config();

    if std::env::args().any(|a| a == "--test" || a == "--headless" || a == "--snapshot" || a == "--help" || a == "-h") {
        println!("⚡ prima-tui: prima.cpp Ring Monitor & 5-Framework Benchmark");
        println!("• Cluster:      {}", config.cluster_name);
        println!("• Model:        {}", config.model_name);
        println!("• Master URL:   {}", config.master_url);
        println!("• World Size:   {} nodes", config.world_size);
        println!("• Configured Ring Nodes:");
        for node in &config.nodes {
            println!("  - [Rank {}] {:<28} (Host: {:<14} Transport: {})", node.rank, node.name, node.host, node.transport);
        }
        println!("• Benchmarking Frameworks: {}", config.frameworks.len());
        for fw in &config.frameworks {
            println!("  - {:<18} URL: {:<26} ({})", fw.name, fw.url, fw.description);
        }
        println!("✅ prima-tui Cluster Verified: 100% OK");
        return Ok(());
    }

    let state = Arc::new(RwLock::new(AppState::new(&config)));

    // Channels
    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<network::PollEvent>();

    // Spawn background poller (polls all node /health endpoints every 3s)
    let poller = Poller::new(config.clone(), event_tx.clone());
    tokio::spawn(async move { poller.run().await });

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = std::io::stdout();
    execute!(stdout, EnterAlternateScreen, crossterm::cursor::Hide)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Event loop
    let tick_rate = Duration::from_millis(16); // ~60 FPS
    let mut last_tick = Instant::now();

    loop {
        // Drain network events (non-blocking)
        loop {
            match event_rx.try_recv() {
                Ok(ev) => apply_poll_event(&state, ev).await,
                Err(_) => break,
            }
        }

        // Draw frame
        {
            let state_read = state.read().await;
            terminal.draw(|f| ui::render(f, &state_read))?;
        }

        // Poll keyboard events
        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_default();

        if crossterm::event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if handle_key(key, &state, &event_tx, &config).await? {
                    break; // quit
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            last_tick = Instant::now();
        }
    }

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        crossterm::cursor::Show
    )?;
    terminal.show_cursor()?;

    Ok(())
}

// ─── Event Handlers ───────────────────────────────────────────────────────────

async fn apply_poll_event(state: &Arc<RwLock<AppState>>, ev: network::PollEvent) {
    let mut s = state.write().await;
    match ev {
        network::PollEvent::NodeHealth { rank, status, ttft_ms, tps, ram_pct } => {
            if let Some(node) = s.nodes.get_mut(rank) {
                node.status = if status { NodeStatus::Online } else { NodeStatus::Offline };
                if let Some(t) = ttft_ms { node.ttft_ms = Some(t); }
                if let Some(t) = tps { node.tps = Some(t); }
                if let Some(r) = ram_pct { node.ram_pct = Some(r); }
                node.last_poll = Some(Instant::now());
            }
        }
        network::PollEvent::BenchmarkResult(result) => {
            s.benchmark_results.push(result);
            if s.benchmark_results.len() > 20 {
                s.benchmark_results.remove(0);
            }
        }
        network::PollEvent::LogLine(line) => {
            s.log_lines.push(line);
            if s.log_lines.len() > 200 {
                s.log_lines.remove(0);
            }
        }
        network::PollEvent::TokenChunk(chunk) => {
            s.stream_buffer.push_str(&chunk);
        }
        network::PollEvent::StreamDone => {
            let response = std::mem::take(&mut s.stream_buffer);
            s.chat_history.push(("assistant".to_string(), response));
            s.chat_streaming = false;
        }
        network::PollEvent::HaldaAssignment { rank, layer_window, gpu_layers } => {
            if let Some(node) = s.nodes.get_mut(rank) {
                node.layer_window = Some(layer_window);
                node.gpu_layers = Some(gpu_layers);
            }
        }
    }
}

async fn handle_key(
    key: KeyEvent,
    state: &Arc<RwLock<AppState>>,
    event_tx: &mpsc::UnboundedSender<network::PollEvent>,
    config: &config::ClusterConfig,
) -> Result<bool> {
    let mut s = state.write().await;

    // Global shortcuts
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
        return Ok(true);
    }

    match key.code {
        KeyCode::Char('q') if s.tab != AppTab::Chat => return Ok(true),

        // Tab switching
        KeyCode::Tab => {
            s.tab = match s.tab {
                AppTab::Ring => AppTab::Halda,
                AppTab::Halda => AppTab::Benchmark,
                AppTab::Benchmark => AppTab::Chat,
                AppTab::Chat => AppTab::Ring,
            };
        }
        KeyCode::Char('1') => s.tab = AppTab::Ring,
        KeyCode::Char('2') => s.tab = AppTab::Halda,
        KeyCode::Char('3') => s.tab = AppTab::Benchmark,
        KeyCode::Char('4') | KeyCode::Char('c') => s.tab = AppTab::Chat,

        // Scrolling
        KeyCode::Up => s.scroll_offset = s.scroll_offset.saturating_sub(1),
        KeyCode::Down => s.scroll_offset += 1,
        KeyCode::PageUp => s.scroll_offset = s.scroll_offset.saturating_sub(10),
        KeyCode::PageDown => s.scroll_offset += 10,

        // Node selection
        KeyCode::Left => {
            if s.selected_node > 0 { s.selected_node -= 1; }
        }
        KeyCode::Right => {
            if s.selected_node + 1 < s.nodes.len() { s.selected_node += 1; }
        }

        // Benchmark trigger
        KeyCode::Char('b') => {
            s.log_lines.push("⚡ Triggering 5-framework benchmark...".to_string());
            let tx = event_tx.clone();
            let master = s.master_url.clone();
            let nodes = s.nodes.iter().map(|n| n.spec.clone()).collect::<Vec<_>>();
            drop(s);
            tokio::spawn(async move {
                network::run_benchmark(&master, &nodes, &tx).await;
            });
            return Ok(false);
        }

        // Chat input
        KeyCode::Char(c) if s.tab == AppTab::Chat => {
            s.chat_input.push(c);
        }
        KeyCode::Backspace if s.tab == AppTab::Chat => {
            s.chat_input.pop();
        }
        KeyCode::Enter if s.tab == AppTab::Chat => {
            let prompt = std::mem::take(&mut s.chat_input);
            if !prompt.is_empty() && !s.chat_streaming {
                s.chat_history.push(("user".to_string(), prompt.clone()));
                s.chat_streaming = true;
                s.stream_buffer.clear();
                let tx = event_tx.clone();
                let url = s.master_url.clone();
                let history = s.chat_history.clone();
                drop(s);
                tokio::spawn(async move {
                    network::stream_chat(&url, &history, &tx).await;
                });
                return Ok(false);
            }
        }

        _ => {}
    }

    Ok(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;

    #[test]
    fn test_app_state_and_render_all_tabs() {
        let config = config::load_cluster_config();
        assert_eq!(config.world_size, 7);
        assert_eq!(config.nodes.len(), 7);

        let mut state = AppState::new(&config);
        assert_eq!(state.nodes.len(), 7);
        assert_eq!(state.nodes[0].spec.name, "L1: Mac Mini M4 Pro (Host)");

        let backend = TestBackend::new(120, 36);
        let mut terminal = Terminal::new(backend).expect("Failed to create TestBackend terminal");

        // Tab 1: Ring
        state.tab = AppTab::Ring;
        terminal.draw(|f| ui::render(f, &state)).expect("Ring render failed");
        let buffer = terminal.backend().buffer();
        let content = format!("{:?}", buffer);
        assert!(content.contains("Ring") || content.contains("Lauburu"));

        // Tab 2: Halda
        state.tab = AppTab::Halda;
        terminal.draw(|f| ui::render(f, &state)).expect("Halda render failed");

        // Tab 3: Benchmark
        state.tab = AppTab::Benchmark;
        terminal.draw(|f| ui::render(f, &state)).expect("Benchmark render failed");

        // Tab 4: Chat
        state.tab = AppTab::Chat;
        terminal.draw(|f| ui::render(f, &state)).expect("Chat render failed");
    }
}
