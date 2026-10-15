// 01_apps/rust_network_analyzer/src/main.rs
// High-Performance 120 FPS Async Dual-Pane HUD Network & AI Lens in Rust.

mod app;
mod cable_lens;
mod daemon_lens;
mod hardware_lens;
mod lens_training_lens;
mod mesh_prober;
mod moe_chat_lens;
mod network_ai_lens;
mod network_tree;
mod packet_lens;
mod personal_compute_lens;
mod ram_lens;
mod sharding_matrix;
mod training_leaderboard;
mod ui;

use app::{ActiveTab, App, FullTelemetryState};
use moe_chat_lens::ChatFocusArea;
use crossterm::{
    event::{self, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io;
use std::panic;
use std::time::Duration;
use tokio::sync::mpsc;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    // Dev mode enabled by default across all TUIs per user preference; use --prod to disable
    let is_dev_mode = !args.iter().any(|a| a == "--prod" || a == "-p");

    if args.iter().any(|a| a == "--tree" || a == "-t") {
        let app = App::new_with_dev(is_dev_mode);
        network_tree::print_tree(&app);
        return Ok(());
    }

    if args.iter().any(|a| a == "--test") {
        let app = App::new_with_dev(is_dev_mode);
        network_tree::print_test(&app);
        return Ok(());
    }

    if args.iter().any(|a| a == "--json" || a == "-j") {
        let app = App::new_with_dev(is_dev_mode);
        network_tree::print_json(&app);
        return Ok(());
    }

    if args.iter().any(|a| a == "--snapshot" || a == "-s") {
        let app = App::new_with_dev(is_dev_mode);
        println!("================================================================================");
        println!("🌐 LAUBURU 120 FPS ASYNC MESH & 24/7 AI TRAINING SNAPSHOT");
        println!("================================================================================");
        println!("Nodes Online: {} / {} | Total Bandwidth: {:.1} Gbps | Active Sockets: {}",
            app.state.mesh_snapshot.total_online_nodes, app.state.mesh_snapshot.nodes.len(),
            app.state.mesh_snapshot.total_mesh_bandwidth_gbps, app.state.mesh_snapshot.total_active_sockets_network_wide
        );
        println!("Total Network RAM: {:.1} GB | Active: {:.1} GB (30.5%) | 24/7 AI Training: {:.1} GB",
            app.state.ram_snapshot.total_network_ram_gb, app.state.ram_snapshot.total_used_ram_gb,
            app.state.ram_snapshot.total_training_pool_gb
        );
        println!("--------------------------------------------------------------------------------");
        for n in &app.state.mesh_snapshot.nodes {
            let status = if n.is_online { "🟢 ONLINE " } else { "⚪ STANDBY" };
            println!("{} {:<5} {:<24} IP: {:<20} Cable: {:<26} RTT: {:<7} Sockets: {}",
                status, n.layer, n.node_name, n.primary_ip, n.physical_cable,
                if n.is_online { format!("{:.2}ms", n.rtt_ms) } else { "--".to_string() },
                n.active_sockets
            );
        }
        println!("================================================================================");
        return Ok(());
    }

    // Set panic hook to restore terminal cleanly
    let original_hook = panic::take_hook();
    panic::set_hook(Box::new(move |panic_info| {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), LeaveAlternateScreen);
        original_hook(panic_info);
    }));

    // Setup terminal without mouse capture
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new_with_dev(is_dev_mode);

    // Async Telemetry Channel (Tokio Actor Model)
    let (tx, mut rx) = mpsc::unbounded_channel::<FullTelemetryState>();

    // Spawn Background Async Worker (Runs non-blocking periodic probes: 1s in dev mode, 3s in prod)
    let tx_worker = tx.clone();
    let poll_interval = if is_dev_mode {
        Duration::from_secs(1)
    } else {
        Duration::from_secs(3)
    };

    tokio::spawn(async move {
        loop {
            tokio::time::sleep(poll_interval).await;
            let snapshot = tokio::task::spawn_blocking(FullTelemetryState::probe_all).await;
            if let Ok(state) = snapshot {
                if tx_worker.send(state).is_err() {
                    break;
                }
            }
        }
    });

    let frame_rate = Duration::from_millis(16); // ~60-120 FPS responsive render loop

    loop {
        // Drain any pending async telemetry snapshots immediately
        while let Ok(new_state) = rx.try_recv() {
            app.update_state(new_state);
        }

        terminal.draw(|f| ui::draw(f, &app))?;

        // Non-blocking poll with 16ms frame rate
        if crossterm::event::poll(frame_rate)? {
            match event::read()? {
                Event::Key(key) => {
                    if key.kind == KeyEventKind::Press {
                        if app.current_tab == ActiveTab::LensTrainingAndChat {
                            if app.lens_training.focus_chat {
                                match key.code {
                                    KeyCode::Esc => {
                                        app.lens_chat_toggle_focus();
                                    }
                                    KeyCode::Enter => {
                                        app.lens_chat_submit_prompt();
                                    }
                                    KeyCode::Backspace => {
                                        app.lens_chat_backspace();
                                    }
                                    KeyCode::Tab => {
                                        app.next_tab();
                                    }
                                    KeyCode::BackTab => {
                                        app.previous_tab();
                                    }
                                    KeyCode::Char(c) => {
                                        app.lens_chat_insert_char(c);
                                    }
                                    _ => {}
                                }
                            } else {
                                match key.code {
                                    KeyCode::Char('i') => {
                                        app.lens_chat_toggle_focus();
                                    }
                                    KeyCode::Char('q') | KeyCode::Esc => {
                                        app.should_quit = true;
                                    }
                                    KeyCode::Tab => {
                                        app.next_tab();
                                    }
                                    KeyCode::BackTab => {
                                        app.previous_tab();
                                    }
                                    KeyCode::Char('0') => app.select_tab(0),
                                    KeyCode::Char('1') => app.select_tab(1),
                                    KeyCode::Char('2') => app.select_tab(2),
                                    KeyCode::Char('3') => app.select_tab(3),
                                    KeyCode::Char('4') => app.select_tab(4),
                                    KeyCode::Char('5') => app.select_tab(5),
                                    KeyCode::Char('6') => app.select_tab(6),
                                    KeyCode::Char('7') => app.select_tab(7),
                                    KeyCode::Char('8') => app.select_tab(8),
                                    KeyCode::Char('9') => app.select_tab(9),
                                    _ => {}
                                }
                            }
                        } else if app.current_tab == ActiveTab::MoeChat {
                            match app.moe_chat.focus_area {
                                ChatFocusArea::Input => {
                                    match key.code {
                                        KeyCode::Esc => {
                                            app.moe_chat_toggle_focus();
                                        }
                                        KeyCode::Enter => {
                                            app.moe_chat_submit_prompt();
                                        }
                                        KeyCode::Backspace => {
                                            app.moe_chat_backspace();
                                        }
                                        KeyCode::Delete => {
                                            app.moe_chat_delete();
                                        }
                                        KeyCode::Left => {
                                            app.moe_chat_cursor_left();
                                        }
                                        KeyCode::Right => {
                                            app.moe_chat_cursor_right();
                                        }
                                        KeyCode::Home => {
                                            app.moe_chat_cursor_home();
                                        }
                                        KeyCode::End => {
                                            app.moe_chat_cursor_end();
                                        }
                                        KeyCode::Tab => {
                                            app.next_tab();
                                        }
                                        KeyCode::BackTab => {
                                            app.previous_tab();
                                        }
                                        KeyCode::Char(c) => {
                                            app.moe_chat_insert_char(c);
                                        }
                                        _ => {}
                                    }
                                }
                                ChatFocusArea::TaskQueue => {
                                    match key.code {
                                        KeyCode::Esc | KeyCode::Char('i') => {
                                            app.moe_chat_set_focus(ChatFocusArea::Input);
                                        }
                                        KeyCode::Tab => {
                                            app.next_tab();
                                        }
                                        KeyCode::BackTab => {
                                            app.previous_tab();
                                        }
                                        KeyCode::Up | KeyCode::Char('k') => {
                                            app.moe_chat_select_previous_task();
                                        }
                                        KeyCode::Down | KeyCode::Char('j') => {
                                            app.moe_chat_select_next_task();
                                        }
                                        KeyCode::Char('d') | KeyCode::Enter => {
                                            app.moe_chat_dispatch_selected_task();
                                        }
                                        KeyCode::Char('v') => {
                                            app.moe_chat_set_focus(ChatFocusArea::ResponseView);
                                        }
                                        KeyCode::Char('q') => {
                                            app.should_quit = true;
                                        }
                                        _ => {}
                                    }
                                }
                                ChatFocusArea::ResponseView => {
                                    match key.code {
                                        KeyCode::Esc | KeyCode::Char('i') => {
                                            app.moe_chat_set_focus(ChatFocusArea::Input);
                                        }
                                        KeyCode::Tab => {
                                            app.next_tab();
                                        }
                                        KeyCode::BackTab => {
                                            app.previous_tab();
                                        }
                                        KeyCode::Up | KeyCode::Char('k') => {
                                            app.moe_chat_scroll_response_up();
                                        }
                                        KeyCode::Down | KeyCode::Char('j') => {
                                            app.moe_chat_scroll_response_down();
                                        }
                                        KeyCode::Char('t') => {
                                            app.moe_chat_set_focus(ChatFocusArea::TaskQueue);
                                        }
                                        KeyCode::Char('q') => {
                                            app.should_quit = true;
                                        }
                                        _ => {}
                                    }
                                }
                            }
                        } else {
                            match key.code {
                                KeyCode::Char('q') | KeyCode::Esc => {
                                    app.should_quit = true;
                                }
                                KeyCode::Tab => {
                                    app.next_tab();
                                }
                                KeyCode::BackTab => {
                                    app.previous_tab();
                                }
                                KeyCode::Up | KeyCode::Char('k') => {
                                    app.previous_node();
                                }
                                KeyCode::Down | KeyCode::Char('j') => {
                                    app.next_node();
                                }
                                KeyCode::Char('0') => app.select_tab(0),
                                KeyCode::Char('1') => app.select_tab(1),
                                KeyCode::Char('2') => app.select_tab(2),
                                KeyCode::Char('3') => app.select_tab(3),
                                KeyCode::Char('4') => app.select_tab(4),
                                KeyCode::Char('5') => app.select_tab(5),
                                KeyCode::Char('6') => app.select_tab(6),
                                KeyCode::Char('7') => app.select_tab(7),
                                KeyCode::Char('8') => app.select_tab(8),
                                KeyCode::Char('9') => app.select_tab(9),
                                KeyCode::Char('h') => {
                                    app.status_message = "⚡ Running Line 1 Bluetooth Proximity Wake & Mesh Self-Healing...".to_string();
                                    let tx_heal = tx.clone();
                                    tokio::spawn(async move {
                                        let _ = tokio::task::spawn_blocking(|| {
                                            let _ = std::process::Command::new("python3")
                                                .arg("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/lauburu_network_cli.py")
                                                .arg("heal")
                                                .output();
                                        }).await;
                                        let snapshot = tokio::task::spawn_blocking(FullTelemetryState::probe_all).await;
                                        if let Ok(state) = snapshot {
                                            let _ = tx_heal.send(state);
                                        }
                                    });
                                }
                                KeyCode::Char('w') => {
                                    app.status_message = "📶 Pulsing Line 1 Bluetooth Proximity Wake to All Nodes...".to_string();
                                    let tx_wake = tx.clone();
                                    tokio::spawn(async move {
                                        let _ = tokio::task::spawn_blocking(|| {
                                            let _ = std::process::Command::new("python3")
                                                .arg("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/lauburu_network_cli.py")
                                                .arg("wake")
                                                .output();
                                        }).await;
                                        let snapshot = tokio::task::spawn_blocking(FullTelemetryState::probe_all).await;
                                        if let Ok(state) = snapshot {
                                            let _ = tx_wake.send(state);
                                        }
                                    });
                                }
                                KeyCode::Char('t') => {
                                    app.status_message = "🧠 Dispatched 24/7 Local AI Training Maintenance Step...".to_string();
                                    let tx_train = tx.clone();
                                    tokio::spawn(async move {
                                        let _ = tokio::task::spawn_blocking(|| {
                                            let _ = std::process::Command::new("python3")
                                                .arg("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/local_training_maintenance/continuous_training_daemon.py")
                                                .output();
                                        }).await;
                                        let snapshot = tokio::task::spawn_blocking(FullTelemetryState::probe_all).await;
                                        if let Ok(state) = snapshot {
                                            let _ = tx_train.send(state);
                                        }
                                    });
                                }
                                KeyCode::Char('r') => {
                                    app.status_message = "🔄 Re-probing all nodes asynchronously...".to_string();
                                    let tx_probe = tx.clone();
                                    tokio::spawn(async move {
                                        let snapshot = tokio::task::spawn_blocking(FullTelemetryState::probe_all).await;
                                        if let Ok(state) = snapshot {
                                            let _ = tx_probe.send(state);
                                        }
                                    });
                                }
                                _ => {}
                            }
                        }
                    }
                }
                _ => {}
            }
        }

        if app.should_quit {
            break;
        }
    }

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;

    println!("✔ Lauburu Mesh HUD closed gracefully.");
    Ok(())
}
