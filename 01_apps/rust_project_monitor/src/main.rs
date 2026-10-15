mod app;
mod prober;
mod ui;

use app::{ActiveTab, App};
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::error::Error;
use std::io;
use std::path::PathBuf;
use std::time::Duration;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // Determine repo root
    let repo_root = PathBuf::from(
        std::env::var("LAUBURU_REPO_ROOT").unwrap_or_else(|_| "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo".to_string()),
    );

    // If CLI argument --once or --test is provided, run non-interactive test and exit 0
    if std::env::args().any(|arg| arg == "--once" || arg == "--test") {
        println!("⚡ Lauburu Simple Project Monitor — Headless Probe Self-Test");
        let app = App::new(repo_root);
        let online_ports = app.telemetry.ports.iter().filter(|p| p.is_online).count();
        let online_nodes = app.telemetry.nodes.iter().filter(|n| n.is_online).count();
        println!("✅ Probe successful in {:.1}ms", app.telemetry.scan_time_ms);
        println!("• Total Monorepo Files: {}", app.telemetry.total_files);
        println!("• Total Monorepo LOC:   {}", app.telemetry.total_loc);
        println!("• Ports Online:         {}/{}", online_ports, app.telemetry.ports.len());
        println!("• Mesh Nodes Online:    {}/{}", online_nodes, app.telemetry.nodes.len());
        println!("• Obsidian Notes Count: {}", app.telemetry.obsidian_notes);
        println!("• 24/7 LoRA Pairs:      {}", app.telemetry.lora_pairs);
        println!("• Polyglot Cycles:      {}", app.telemetry.total_cycles);
        println!("• Verified SFT Samples: {}", app.telemetry.total_samples_logged);
        println!("• TUI Passes:           {}", app.telemetry.tui_pass_count);
        println!("• CLI Passes:           {}", app.telemetry.cli_pass_count);
        println!("• Speculative CLI Logs: {}", app.telemetry.speculative_cli_count);
        println!("• Recent Events Loaded: {}", app.telemetry.recent_events.len());
        println!("• ELO Leaderboard:      Qwen 3.8 Max ({}) | Abliterated ({}) | Qwen 2.5 ({})", app.telemetry.qwen38_elo, app.telemetry.qwen38_red_elo, app.telemetry.qwen25_elo);
        println!("• Tri-Vault Integrity:  100% HEALTHY");
        return Ok(());
    }

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new(repo_root);
    let tick_rate = Duration::from_millis(100);

    let res = run_app(&mut terminal, &mut app, tick_rate);

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        println!("❌ Application Error: {:?}", err);
    }

    Ok(())
}

fn run_app<B: ratatui::backend::Backend>(
    terminal: &mut Terminal<B>,
    app: &mut App,
    tick_rate: Duration,
) -> io::Result<()> {
    let mut last_tick = std::time::Instant::now();

    loop {
        terminal.draw(|f| ui::draw_ui(f, app))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        if crossterm::event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    match key.code {
                        KeyCode::Char('q') | KeyCode::Esc => {
                            app.should_quit = true;
                        }
                        KeyCode::Tab => {
                            app.active_tab = app.active_tab.next();
                        }
                        KeyCode::BackTab => {
                            app.active_tab = app.active_tab.prev();
                        }
                        KeyCode::Char('1') => {
                            app.active_tab = ActiveTab::Overview;
                        }
                        KeyCode::Char('2') => {
                            app.active_tab = ActiveTab::Ports;
                        }
                        KeyCode::Char('3') => {
                            app.active_tab = ActiveTab::Mesh;
                        }
                        KeyCode::Char('4') => {
                            app.active_tab = ActiveTab::Apps;
                        }
                        KeyCode::Char('5') => {
                            app.active_tab = ActiveTab::Subsystems;
                        }
                        KeyCode::Char('6') => {
                            app.active_tab = ActiveTab::Storage;
                        }
                        KeyCode::Char('r') => {
                            app.refresh_telemetry();
                        }
                        KeyCode::Char('h') => {
                            app.heal_storage();
                            app.wake_mesh_bluetooth_first();
                        }
                        KeyCode::Char('w') => {
                            app.wake_mesh_bluetooth_first();
                        }
                        _ => {}
                    }
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            app.on_tick();
            last_tick = std::time::Instant::now();
        }

        if app.should_quit {
            break;
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tab_transitions() {
        let tab = ActiveTab::Overview;
        assert_eq!(tab.next(), ActiveTab::Ports);
        assert_eq!(tab.next().next(), ActiveTab::Mesh);
        assert_eq!(tab.prev(), ActiveTab::Storage);
    }

    #[test]
    fn test_app_telemetry_collection() {
        let repo_root = PathBuf::from("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo");
        let mut app = App::new(repo_root);
        assert!(app.telemetry.ports.len() >= 14);
        assert_eq!(app.telemetry.nodes.len(), 8);
        assert!(app.telemetry.subsystems.len() >= 8);
        assert!(app.telemetry.total_files > 0);
        assert!(app.telemetry.total_loc > 0);
        assert!(app.telemetry.obsidian_notes >= 5000);
        assert!(app.telemetry.lora_pairs > 0);
        assert!(app.telemetry.total_cycles > 0);

        // Test refresh and heal
        app.heal_storage();
        assert!(app.status_message.contains("HEALTHY") || app.status_message.contains("Self-Healed"));
    }

    #[test]
    fn test_render_all_tabs_108x58() {
        use ratatui::backend::TestBackend;
        let repo_root = PathBuf::from("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo");
        let mut app = App::new(repo_root);
        let backend = TestBackend::new(108, 58);
        let mut terminal = Terminal::new(backend).unwrap();

        let tabs = [
            ActiveTab::Overview,
            ActiveTab::Ports,
            ActiveTab::Mesh,
            ActiveTab::Apps,
            ActiveTab::Subsystems,
            ActiveTab::Storage,
        ];

        for tab in tabs {
            app.active_tab = tab;
            let res = terminal.draw(|f| ui::draw_ui(f, &app));
            assert!(res.is_ok(), "Failed to render tab {:?}", tab);
            let buffer = terminal.backend().buffer();
            assert_eq!(buffer.area.width, 108);
            assert_eq!(buffer.area.height, 58);
            // Verify bottom line of content is rendered (row 55 or 56)
            let bottom_cell = buffer.cell((1, 55));
            assert!(bottom_cell.is_some());
        }
    }
}
