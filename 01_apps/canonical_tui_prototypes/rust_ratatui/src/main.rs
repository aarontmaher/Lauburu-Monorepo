use std::{
    collections::BTreeMap,
    error::Error,
    fs::File,
    io::{self, stdout, Read},
    path::PathBuf,
    thread,
    time::{Duration, Instant},
};

use clap::Parser;
use crossterm::{
    event::{self, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::{Backend, CrosstermBackend},
    layout::{Alignment, Constraint, Direction, Layout},
    style::{Color, Modifier, Style, Stylize},
    text::{Line, Span},
    widgets::{Block, BorderType, Borders, Cell, Gauge, Paragraph, Row, Table},
    Frame, Terminal,
};
use serde::{Deserialize, Serialize};

const DEFAULT_STATE_PATH: &str =
    "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/cloud_api_quota_state.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuotaState {
    pub version: String,
    #[serde(default)]
    pub last_reset: Option<String>,
    #[serde(default)]
    pub last_reset_date: Option<String>,
    #[serde(default)]
    pub last_updated: Option<String>,
    pub providers: BTreeMap<String, ProviderState>,
    pub metrics: GlobalMetrics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderState {
    pub daily_limit: i64,
    pub used_today: i64,
    pub remaining_pct: f64,
    pub avg_latency_ms: f64,
    #[serde(default)]
    pub max_tokens: Option<i64>,
    #[serde(default)]
    pub consecutive_failures: i64,
    #[serde(default)]
    pub total_requests: i64,
    #[serde(default)]
    pub successful_requests: i64,
    pub status: String,
    #[serde(default)]
    pub cooldown_until: f64,
    #[serde(default)]
    pub last_used_timestamp: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalMetrics {
    #[serde(default)]
    pub total_tasks_routed: i64,
    #[serde(default)]
    pub cloud_tasks_succeeded: i64,
    #[serde(default)]
    pub local_mesh_fallback_count: i64,
    #[serde(default)]
    pub total_lora_samples_harvested: i64,
}

pub struct QuotaReader {
    pub state_path: PathBuf,
}

impl QuotaReader {
    pub fn new(path: PathBuf) -> Self {
        Self { state_path: path }
    }

    pub fn read_state(&self, retries: usize) -> Result<QuotaState, Box<dyn Error>> {
        let mut last_err: Box<dyn Error> = "File could not be opened".into();
        for attempt in 0..retries {
            if let Ok(mut file) = File::open(&self.state_path) {
                let mut contents = String::new();
                if file.read_to_string(&mut contents).is_ok() && !contents.trim().is_empty() {
                    match serde_json::from_str::<QuotaState>(&contents) {
                        Ok(state) => {
                            if !state.providers.is_empty() {
                                return Ok(state);
                            } else {
                                last_err = "Providers map is empty in quota state".into();
                            }
                        }
                        Err(e) => {
                            last_err = Box::new(e);
                        }
                    }
                }
            }
            if attempt + 1 < retries {
                thread::sleep(Duration::from_millis(50 * (1 << attempt)));
            }
        }
        Err(last_err)
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "canonical_tui_rust",
    author = "Lauburu Monorepo Team",
    version = "2.0.0",
    about = "Canonical Lauburu Ratatui Cloud API Quota & Telemetry HUD"
)]
struct Cli {
    #[arg(long, short = 's', default_value = DEFAULT_STATE_PATH)]
    state_path: PathBuf,

    #[arg(long, default_value_t = 2.0)]
    poll_interval: f64,

    #[arg(long, default_value_t = false)]
    verify: bool,

    #[arg(long)]
    timeout: Option<f64>,
}

struct App {
    poll_interval: Duration,
    quota_data: Option<QuotaState>,
    reader: QuotaReader,
    last_poll: Instant,
    start_time: Instant,
    timeout: Option<Duration>,
    paused: bool,
    should_quit: bool,
}

impl App {
    fn new(state_path: PathBuf, poll_interval_secs: f64, timeout_secs: Option<f64>) -> Self {
        let reader = QuotaReader::new(state_path);
        let initial_data = reader.read_state(3).ok();
        Self {
            poll_interval: Duration::from_secs_f64(poll_interval_secs.max(0.1)),
            quota_data: initial_data,
            reader,
            last_poll: Instant::now(),
            start_time: Instant::now(),
            timeout: timeout_secs.map(Duration::from_secs_f64),
            paused: false,
            should_quit: false,
        }
    }

    fn on_tick(&mut self) {
        if !self.paused && self.last_poll.elapsed() >= self.poll_interval {
            if let Ok(data) = self.reader.read_state(3) {
                self.quota_data = Some(data);
            }
            self.last_poll = Instant::now();
        }
        if let Some(to) = self.timeout {
            if self.start_time.elapsed() >= to {
                self.should_quit = true;
            }
        }
    }
}

fn verify_state_headless(state_path: &PathBuf) -> Result<(), Box<dyn Error>> {
    let reader = QuotaReader::new(state_path.clone());
    let state = reader.read_state(3)?;
    let p_names: Vec<String> = state.providers.keys().cloned().collect();

    println!("✓ Rust Ratatui Verification Passed: Version {}", state.version);
    println!("  Providers ({}): {}", p_names.len(), p_names.join(", "));
    println!(
        "  Metrics: Routed={}, Cloud OK={}, Fallbacks={}, LoRA Harvested={}",
        state.metrics.total_tasks_routed,
        state.metrics.cloud_tasks_succeeded,
        state.metrics.local_mesh_fallback_count,
        state.metrics.total_lora_samples_harvested
    );
    Ok(())
}

fn run_headless_loop(state_path: &PathBuf, poll_interval_secs: f64, timeout_secs: Option<f64>) -> io::Result<()> {
    let reader = QuotaReader::new(state_path.clone());
    let start = Instant::now();
    let poll_dur = Duration::from_secs_f64(poll_interval_secs.max(0.1));
    let timeout_dur = timeout_secs.map(Duration::from_secs_f64);

    loop {
        let _ = reader.read_state(3);
        if let Some(to) = timeout_dur {
            if start.elapsed() >= to {
                break;
            }
        }
        thread::sleep(poll_dur.min(Duration::from_millis(500)));
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.verify {
        match verify_state_headless(&cli.state_path) {
            Ok(_) => std::process::exit(0),
            Err(e) => {
                eprintln!("❌ Rust Ratatui Verification FAILED: {e}");
                std::process::exit(1);
            }
        }
    }

    // Try enabling raw mode. If not running in a TTY and timeout is provided, run headless loop.
    if enable_raw_mode().is_err() {
        if cli.timeout.is_some() {
            run_headless_loop(&cli.state_path, cli.poll_interval, cli.timeout)?;
            return Ok(());
        }
        eprintln!("Warning: Terminal not detected. Running headless.");
        run_headless_loop(&cli.state_path, cli.poll_interval, cli.timeout)?;
        return Ok(());
    }

    let mut stdout = stdout();
    if execute!(stdout, EnterAlternateScreen).is_err() {
        let _ = disable_raw_mode();
        run_headless_loop(&cli.state_path, cli.poll_interval, cli.timeout)?;
        return Ok(());
    }

    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new(cli.state_path, cli.poll_interval, cli.timeout);
    let res = run_app(&mut terminal, &mut app);

    // Terminal Teardown
    let _ = disable_raw_mode();
    let _ = execute!(terminal.backend_mut(), LeaveAlternateScreen);
    let _ = terminal.show_cursor();

    if let Err(err) = res {
        eprintln!("Application Error: {err:?}");
    }
    Ok(())
}

fn run_app<B: Backend>(terminal: &mut Terminal<B>, app: &mut App) -> io::Result<()> {
    loop {
        terminal.draw(|f| ui(f, app))?;
        app.on_tick();

        if app.should_quit {
            return Ok(());
        }

        if event::poll(Duration::from_millis(100))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') | KeyCode::Esc => return Ok(()),
                    KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => return Ok(()),
                    KeyCode::Char('r') => {
                        if let Ok(data) = app.reader.read_state(3) {
                            app.quota_data = Some(data);
                        }
                    }
                    KeyCode::Char('p') => {
                        app.paused = !app.paused;
                    }
                    _ => {}
                }
            }
        }
    }
}

fn ui(f: &mut Frame, app: &mut App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // Header
            Constraint::Length(4), // Metrics HUD Cards
            Constraint::Min(10),   // Main Body (Table + Gauges)
            Constraint::Length(3), // Footer
        ])
        .split(f.area());

    // 1. Header
    let pause_tag = if app.paused { " [PAUSED]" } else { "" };
    let header_text = format!("⚡ LAUBURU MESH — RATATUI QUOTA COMMAND{}", pause_tag);
    let header = Paragraph::new(Line::from(vec![
        Span::styled(header_text, Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
        Span::raw("  "),
        Span::styled(
            "Free Token Maximizer & 24/7 LoRA Telemetry",
            Style::default().fg(Color::DarkGray).add_modifier(Modifier::ITALIC),
        ),
    ]))
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Rgb(30, 41, 59))),
    );
    f.render_widget(header, chunks[0]);

    // 2. Metrics HUD Cards
    let (tasks, cloud, fallback, lora) = if let Some(ref data) = app.quota_data {
        (
            data.metrics.total_tasks_routed,
            data.metrics.cloud_tasks_succeeded,
            data.metrics.local_mesh_fallback_count,
            data.metrics.total_lora_samples_harvested,
        )
    } else {
        (0, 0, 0, 0)
    };

    let metric_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(25),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
            Constraint::Percentage(25),
        ])
        .split(chunks[1]);

    let card1 = Paragraph::new(vec![
        Line::from(Span::styled("TOTAL TASKS", Style::default().fg(Color::DarkGray).bold())),
        Line::from(Span::styled(format!("{tasks}"), Style::default().fg(Color::Rgb(56, 189, 248)).bold())),
    ])
    .alignment(Alignment::Center)
    .block(Block::default().borders(Borders::ALL).border_type(BorderType::Rounded).border_style(Style::default().fg(Color::Rgb(30, 41, 59))));

    let card2 = Paragraph::new(vec![
        Line::from(Span::styled("CLOUD SUCCEEDED", Style::default().fg(Color::DarkGray).bold())),
        Line::from(Span::styled(format!("{cloud}"), Style::default().fg(Color::Rgb(56, 189, 248)).bold())),
    ])
    .alignment(Alignment::Center)
    .block(Block::default().borders(Borders::ALL).border_type(BorderType::Rounded).border_style(Style::default().fg(Color::Rgb(30, 41, 59))));

    let card3 = Paragraph::new(vec![
        Line::from(Span::styled("MESH FALLBACKS", Style::default().fg(Color::DarkGray).bold())),
        Line::from(Span::styled(format!("{fallback}"), Style::default().fg(Color::Rgb(56, 189, 248)).bold())),
    ])
    .alignment(Alignment::Center)
    .block(Block::default().borders(Borders::ALL).border_type(BorderType::Rounded).border_style(Style::default().fg(Color::Rgb(30, 41, 59))));

    let card4 = Paragraph::new(vec![
        Line::from(Span::styled("LORA HARVESTED", Style::default().fg(Color::DarkGray).bold())),
        Line::from(Span::styled(format!("{lora}"), Style::default().fg(Color::Rgb(56, 189, 248)).bold())),
    ])
    .alignment(Alignment::Center)
    .block(Block::default().borders(Borders::ALL).border_type(BorderType::Rounded).border_style(Style::default().fg(Color::Rgb(30, 41, 59))));

    f.render_widget(card1, metric_chunks[0]);
    f.render_widget(card2, metric_chunks[1]);
    f.render_widget(card3, metric_chunks[2]);
    f.render_widget(card4, metric_chunks[3]);

    // 3. Body Split (60% Table, 40% Gauges)
    let body_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
        .split(chunks[2]);

    // Table
    let mut rows = Vec::new();
    if let Some(ref data) = app.quota_data {
        for (name, p) in &data.providers {
            let limit_str = if p.daily_limit >= 999999 {
                "∞".to_string()
            } else {
                p.daily_limit.to_string()
            };
            let rem_pct = format!("{:.1}%", p.remaining_pct * 100.0);
            let lat = format!("{:.1} ms", p.avg_latency_ms);

            let (status_text, status_color) = match p.status.to_lowercase().as_str() {
                "healthy" => ("● HEALTHY", Color::Green),
                "in_cooldown" | "cooldown" => ("⏱ COOLDOWN", Color::Yellow),
                "degraded" => ("🔻 DEGRADED", Color::Red),
                "exhausted" => ("⛔ EXHAUSTED", Color::DarkGray),
                _ => ("● ACTIVE", Color::Cyan),
            };

            rows.push(Row::new(vec![
                Cell::from(name.clone()).style(Style::default().fg(Color::Cyan).bold()),
                Cell::from(limit_str),
                Cell::from(p.used_today.to_string()),
                Cell::from(rem_pct),
                Cell::from(lat),
                Cell::from(p.consecutive_failures.to_string()),
                Cell::from(status_text).style(Style::default().fg(status_color).bold()),
            ]));
        }
    }

    let table = Table::new(
        rows,
        [
            Constraint::Percentage(22),
            Constraint::Percentage(13),
            Constraint::Percentage(13),
            Constraint::Percentage(12),
            Constraint::Percentage(15),
            Constraint::Percentage(11),
            Constraint::Percentage(14),
        ],
    )
    .header(
        Row::new(vec!["Provider", "Daily Limit", "Used Today", "Rem %", "Avg Latency", "Failures", "Status"])
            .style(Style::default().fg(Color::Rgb(56, 189, 248)).bold()),
    )
    .block(
        Block::default()
            .title(" Active Providers Quota Matrix ")
            .borders(Borders::ALL)
            .border_type(BorderType::Rounded)
            .border_style(Style::default().fg(Color::Rgb(30, 41, 59))),
    );
    f.render_widget(table, body_chunks[0]);

    // Gauges
    let mut gauge_constraints = Vec::new();
    let provider_count = app.quota_data.as_ref().map(|d| d.providers.len()).unwrap_or(0);
    for _ in 0..provider_count {
        gauge_constraints.push(Constraint::Length(2));
    }
    if gauge_constraints.is_empty() {
        gauge_constraints.push(Constraint::Min(2));
    }

    let gauge_block = Block::default()
        .title(" Provider Quota Remaining ")
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::default().fg(Color::Rgb(30, 41, 59)));

    let inner_gauge_rect = gauge_block.inner(body_chunks[1]);
    f.render_widget(gauge_block, body_chunks[1]);

    if let Some(ref data) = app.quota_data {
        let gauge_layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints(gauge_constraints)
            .split(inner_gauge_rect);

        for (idx, (name, p)) in data.providers.iter().enumerate() {
            if idx < gauge_layout.len() {
                let pct = (p.remaining_pct.max(0.0).min(1.0) * 100.0) as u16;
                let gauge_color = if pct >= 50 {
                    Color::Green
                } else if pct >= 15 {
                    Color::Yellow
                } else {
                    Color::Red
                };

                let gauge = Gauge::default()
                    .block(Block::default().title(format!("{name} ({pct}%)")))
                    .gauge_style(Style::default().fg(gauge_color).bg(Color::Rgb(15, 23, 42)))
                    .percent(pct);
                f.render_widget(gauge, gauge_layout[idx]);
            }
        }
    }

    // 4. Footer
    let footer = Paragraph::new("Press 'q' or Esc to exit | 'r' to refresh | 'p' to pause | --verify for CI check")
        .style(Style::default().fg(Color::DarkGray))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_type(BorderType::Rounded)
                .border_style(Style::default().fg(Color::Rgb(30, 41, 59))),
        );
    f.render_widget(footer, chunks[3]);
}
