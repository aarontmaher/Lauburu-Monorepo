//! ============================================================================
//! Challenger 1 Comprehensive Empirical Stress & Verification Test Harness
//! ============================================================================
//! Mandatory Empirical Challenge Scenarios:
//! 1. Rapid 10,000-cycle tab switching across all 5 tabs (`1-5`, `Tab`, `BackTab`)
//! 2. Extreme micro-viewports (`40x10`, `20x5`, `0x0`, `1x1`, `49x11`, `50x12`) across all 5 tabs
//! 3. High-frequency event loop throughput & 60 FPS non-blocking render benchmark
//! 4. Comprehensive keyboard navigation boundary wrapping across all tables (Tabs 1, 3, 4, 5)
//! ============================================================================

use crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyEventState, KeyModifiers};
use lauburu_tui::api_scanner::SwapStatus;
use lauburu_tui::app::{ActiveTopologyTable, App, Tab};
use lauburu_tui::config::MeshConfig;
use lauburu_tui::events::AppEvent;
use lauburu_tui::sharding::ShardingFocus;
use lauburu_tui::training::{RamGovernorTier, TrainingFocus};
use lauburu_tui::ui;
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use std::time::Instant;
use tokio::sync::mpsc;

fn make_key(code: KeyCode) -> KeyEvent {
    KeyEvent {
        code,
        modifiers: KeyModifiers::NONE,
        kind: KeyEventKind::Press,
        state: KeyEventState::NONE,
    }
}

fn make_key_with_mod(code: KeyCode, modifiers: KeyModifiers) -> KeyEvent {
    KeyEvent {
        code,
        modifiers,
        kind: KeyEventKind::Press,
        state: KeyEventState::NONE,
    }
}

fn buffer_to_string(terminal: &Terminal<TestBackend>) -> String {
    let buffer = terminal.backend().buffer();
    let mut out = String::new();
    for y in 0..buffer.area.height {
        for x in 0..buffer.area.width {
            let cell = buffer.cell((x, y)).unwrap();
            out.push_str(cell.symbol());
        }
        out.push('\n');
    }
    out
}

// ============================================================================
// 1. Rapid 10,000-Cycle Tab Switching Stress & Throughput Benchmark
// ============================================================================

#[test]
fn test_empirical_01_rapid_10k_tab_switching_throughput_and_zero_panic() {
    let mut app = App::new(MeshConfig::fallback());
    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();

    let start = Instant::now();
    let mut render_count = 0;

    for i in 0..10_000 {
        match i % 7 {
            0 => app.handle_key(make_key(KeyCode::Tab)),
            1 => app.handle_key(make_key(KeyCode::BackTab)),
            2 => app.handle_key(make_key(KeyCode::Char('1'))),
            3 => app.handle_key(make_key(KeyCode::Char('3'))),
            4 => app.handle_key(make_key(KeyCode::Char('4'))),
            5 => app.handle_key(make_key(KeyCode::Char('5'))),
            6 => {
                app.handle_key(make_key(KeyCode::Char('2')));
                // In Chat tab, use Ctrl+1 to switch back
                app.handle_key(make_key_with_mod(KeyCode::Char('1'), KeyModifiers::CONTROL));
                None
            }
            _ => unreachable!(),
        };

        // Render every 100 cycles to verify drawing pipeline integrity during rapid switching
        if i % 100 == 0 {
            terminal.draw(|f| ui::render(&mut app, f)).unwrap();
            render_count += 1;
        }
    }

    let elapsed = start.elapsed();
    let throughput = 10_000.0 / elapsed.as_secs_f64();

    println!(
        "\n[BENCHMARK] 10,000 Tab Switches + {} Frame Renders completed in {:?} ({:.0} switches/sec)",
        render_count, elapsed, throughput
    );

    assert!(
        elapsed.as_millis() < 500,
        "10,000 tab switches should complete in <500ms, took {:?}",
        elapsed
    );
    assert!(!app.should_quit, "App should not have triggered quit");
}

// ============================================================================
// 2. Extreme Micro-Viewports Across All 5 Tabs
// ============================================================================

#[test]
fn test_empirical_02_micro_viewports_across_all_five_tabs() {
    let micro_viewports = [
        (0, 0, false),
        (1, 1, false),
        (10, 2, false),
        (20, 5, true),
        (40, 10, true),
        (49, 11, true),
        (50, 12, false), // Exact boundary - full layout rendered
        (80, 24, false), // Standard
        (200, 50, false), // Large
    ];

    let all_tabs = [
        Tab::Topology,
        Tab::Chat,
        Tab::Sharding,
        Tab::ApiScanner,
        Tab::Training,
    ];

    for &(w, h, expect_fallback_banner) in &micro_viewports {
        for &tab in &all_tabs {
            let backend = TestBackend::new(w, h);
            let mut terminal = Terminal::new(backend).unwrap();
            let mut app = App::new(MeshConfig::fallback());
            app.switch_tab(tab);

            let draw_res = terminal.draw(|f| ui::render(&mut app, f));
            assert!(
                draw_res.is_ok(),
                "Tab {:?} panicked on viewport {}x{}",
                tab,
                w,
                h
            );

            if expect_fallback_banner {
                let rendered = buffer_to_string(&terminal);
                assert!(
                    rendered.contains("Viewport"),
                    "Viewport {}x{} on Tab {:?} failed to render fallback warning banner. Buffer:\n{}",
                    w,
                    h,
                    tab,
                    rendered
                );
            }
        }
    }
}

// ============================================================================
// 3. High-Frequency Event Loop Throughput & Non-Blocking 60 FPS Render Benchmark
// ============================================================================

#[tokio::test]
async fn test_empirical_03_high_frequency_event_loop_and_60fps_render_stability() {
    let (tx, mut rx) = mpsc::unbounded_channel::<AppEvent>();
    let mut app = App::new(MeshConfig::fallback());
    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();

    let total_events = 50_000;
    let push_start = Instant::now();

    // Pump 50,000 heterogeneous events into the channel
    for i in 0..total_events {
        let evt = match i % 5 {
            0 => AppEvent::Tick,
            1 => AppEvent::TokenChunk(" token".to_string()),
            2 => AppEvent::Key(make_key(KeyCode::Tab)),
            3 => AppEvent::Resize(120, 30),
            4 => AppEvent::StreamComplete {
                prompt_tokens: 15,
                completion_tokens: 45,
            },
            _ => unreachable!(),
        };
        tx.send(evt).expect("Send failed");
    }

    let push_elapsed = push_start.elapsed();
    println!(
        "\n[BENCHMARK] Pushed {} events in {:?} ({:.0} events/sec)",
        total_events,
        push_elapsed,
        total_events as f64 / push_elapsed.as_secs_f64()
    );

    // Drain and process all 50,000 events in app state loop
    let process_start = Instant::now();
    let mut processed = 0;

    while processed < total_events {
        if let Ok(event) = rx.try_recv() {
            match event {
                AppEvent::Key(k) => {
                    app.handle_key(k);
                }
                AppEvent::Resize(w, h) => {
                    app.terminal_size = (w, h);
                }
                AppEvent::Tick => {}
                AppEvent::TokenChunk(chunk) => {
                    app.append_token(&chunk);
                }
                AppEvent::StreamComplete {
                    prompt_tokens,
                    completion_tokens,
                } => {
                    app.complete_stream(prompt_tokens, completion_tokens);
                }
                _ => {}
            }
            processed += 1;
        }
    }

    let process_elapsed = process_start.elapsed();
    let process_throughput = total_events as f64 / process_elapsed.as_secs_f64();

    println!(
        "[BENCHMARK] Processed {} events in {:?} ({:.0} events/sec)",
        processed, process_elapsed, process_throughput
    );
    assert!(
        process_elapsed.as_millis() < 200,
        "50,000 events processed in {:?} (exceeded 200ms limit)",
        process_elapsed
    );

    // Non-blocking 1,000-frame render loop simulation across all 5 tabs (200 frames per tab)
    let render_start = Instant::now();
    let total_frames = 1000;

    for i in 0..total_frames {
        let target_tab = Tab::from_index((i / 200) % 5);
        if app.current_tab != target_tab {
            app.switch_tab(target_tab);
        }
        terminal.draw(|f| ui::render(&mut app, f)).unwrap();
    }

    let render_elapsed = render_start.elapsed();
    let fps = total_frames as f64 / render_elapsed.as_secs_f64();
    let frame_time_ms = (render_elapsed.as_secs_f64() / total_frames as f64) * 1000.0;

    println!(
        "[BENCHMARK] Rendered {} full-tab frames in {:?} ({:.1} FPS, {:.3} ms/frame)",
        total_frames, render_elapsed, fps, frame_time_ms
    );

    assert!(
        fps >= 60.0,
        "Render throughput {:.1} FPS fell below 60 FPS target",
        fps
    );
    assert!(
        frame_time_ms < 16.6,
        "Frame time {:.3}ms exceeded 16.6ms budget for 60 FPS",
        frame_time_ms
    );
}

// ============================================================================
// 4. Keyboard Navigation Boundary Wrapping on All Tables (Tabs 1, 3, 4, 5)
// ============================================================================

#[test]
fn test_empirical_04_table_boundary_wrapping_all_tabs() {
    let mut app = App::new(MeshConfig::fallback());

    // ------------------------------------------------------------------------
    // TAB 1: Topology Table Navigation & Wrapping
    // ------------------------------------------------------------------------
    app.switch_tab(Tab::Topology);
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
    assert_eq!(app.core_table_state.selected(), Some(0));

    // Core table has 4 nodes (0..3)
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.core_table_state.selected(), Some(1));
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.core_table_state.selected(), Some(2));
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.core_table_state.selected(), Some(3));
    // Wrap to 0
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.core_table_state.selected(), Some(0));
    // Up wraps to 3
    app.handle_key(make_key(KeyCode::Up));
    assert_eq!(app.core_table_state.selected(), Some(3));

    // Switch to Edge table via 'l'
    app.handle_key(make_key(KeyCode::Char('l')));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);
    assert_eq!(app.edge_table_state.selected(), Some(0));

    // Edge table has 3 nodes (0..2)
    app.handle_key(make_key(KeyCode::Char('j')));
    assert_eq!(app.edge_table_state.selected(), Some(1));
    app.handle_key(make_key(KeyCode::Char('j')));
    assert_eq!(app.edge_table_state.selected(), Some(2));
    // Wrap to 0
    app.handle_key(make_key(KeyCode::Char('j')));
    assert_eq!(app.edge_table_state.selected(), Some(0));
    // 'k' wraps to 2
    app.handle_key(make_key(KeyCode::Char('k')));
    assert_eq!(app.edge_table_state.selected(), Some(2));

    // Switch back to Core table via 'h'
    app.handle_key(make_key(KeyCode::Char('h')));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
    assert_eq!(app.core_table_state.selected(), Some(3)); // Preserved

    // ------------------------------------------------------------------------
    // TAB 3: Sharding Tables Navigation & Wrapping
    // ------------------------------------------------------------------------
    app.switch_tab(Tab::Sharding);
    assert_eq!(app.sharding_state.active_focus, ShardingFocus::RoutingMatrix);
    let routing_count = app.sharding_state.routing_specs.len();
    assert_eq!(routing_count, 9);
    assert_eq!(app.sharding_state.selected_model_row, 0);

    // Down through all 9 rows and wrap
    for expected in 1..routing_count {
        app.handle_key(make_key(KeyCode::Down));
        assert_eq!(app.sharding_state.selected_model_row, expected);
    }
    // 10th press wraps back to 0
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.sharding_state.selected_model_row, 0);

    // Up wraps to index 8
    app.handle_key(make_key(KeyCode::Up));
    assert_eq!(app.sharding_state.selected_model_row, routing_count - 1);

    // Switch focus to Node Matrix via Right arrow
    app.handle_key(make_key(KeyCode::Right));
    assert_eq!(app.sharding_state.active_focus, ShardingFocus::NodeMatrix);
    let node_count = app.sharding_state.node_capabilities.len();
    assert_eq!(node_count, 7);
    assert_eq!(app.sharding_state.node_table_state.selected(), Some(0));

    // Down through all 7 nodes and wrap
    for expected in 1..node_count {
        app.handle_key(make_key(KeyCode::Char('j')));
        assert_eq!(app.sharding_state.node_table_state.selected(), Some(expected));
    }
    app.handle_key(make_key(KeyCode::Char('j')));
    assert_eq!(app.sharding_state.node_table_state.selected(), Some(0));

    // 'k' wraps to index 6
    app.handle_key(make_key(KeyCode::Char('k')));
    assert_eq!(app.sharding_state.node_table_state.selected(), Some(node_count - 1));

    // ------------------------------------------------------------------------
    // TAB 4: API Scanner Endpoints Table Navigation, Wrapping & Model Swap
    // ------------------------------------------------------------------------
    app.switch_tab(Tab::ApiScanner);
    let ep_count = app.api_scanner_state.endpoints.len();
    assert_eq!(ep_count, 5);
    assert_eq!(app.api_scanner_state.selected_endpoint_row, 0);

    // Down through all 5 endpoints and wrap
    for expected in 1..ep_count {
        app.handle_key(make_key(KeyCode::Down));
        assert_eq!(app.api_scanner_state.selected_endpoint_row, expected);
        assert_eq!(app.api_scanner_table_state.selected(), Some(expected));
    }
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.api_scanner_state.selected_endpoint_row, 0);
    assert_eq!(app.api_scanner_table_state.selected(), Some(0));

    // Up wraps to index 4
    app.handle_key(make_key(KeyCode::Up));
    assert_eq!(app.api_scanner_state.selected_endpoint_row, ep_count - 1);
    assert_eq!(app.api_scanner_table_state.selected(), Some(ep_count - 1));

    // Return to index 0 (gpt-4o) and toggle model swap via 's'
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.api_scanner_state.selected_endpoint_row, 0);
    let initial_active = app.api_scanner_state.endpoints[0].is_active;
    assert!(initial_active);

    app.handle_key(make_key(KeyCode::Char('s')));
    assert!(!app.api_scanner_state.endpoints[0].is_active);
    assert_eq!(
        app.api_scanner_state.recommendations[0].status,
        SwapStatus::RunningOnMesh
    );
    // Dynamic recalculation: total savings increased from 20.80 to 66.00
    assert_eq!(app.api_scanner_state.total_savings_usd, 66.0);
    assert!((app.api_scanner_state.zero_spend_velocity_pct - 39.639).abs() < 0.1);

    // Toggle back
    app.handle_key(make_key(KeyCode::Enter));
    assert!(app.api_scanner_state.endpoints[0].is_active);
    assert_eq!(
        app.api_scanner_state.recommendations[0].status,
        SwapStatus::ReadyInVault
    );

    // ------------------------------------------------------------------------
    // TAB 5: Training Tables Navigation & Wrapping (Tournament & NPU Ledger)
    // ------------------------------------------------------------------------
    app.switch_tab(Tab::Training);
    assert_eq!(
        app.training_state.active_training_focus,
        TrainingFocus::BenchmarkTournament
    );
    let bench_count = app.training_state.benchmark_rows.len();
    assert_eq!(bench_count, 3);
    assert_eq!(app.training_state.selected_benchmark_row, 0);

    // Down through all 3 tournament rows and wrap
    for expected in 1..bench_count {
        app.handle_key(make_key(KeyCode::Down));
        assert_eq!(app.training_state.selected_benchmark_row, expected);
        assert_eq!(app.training_state.benchmark_table_state.selected(), Some(expected));
    }
    app.handle_key(make_key(KeyCode::Down));
    assert_eq!(app.training_state.selected_benchmark_row, 0);
    assert_eq!(app.training_state.benchmark_table_state.selected(), Some(0));

    // Up wraps to index 2
    app.handle_key(make_key(KeyCode::Up));
    assert_eq!(app.training_state.selected_benchmark_row, bench_count - 1);

    // Switch focus to NPU Bonus Ledger via Right arrow
    app.handle_key(make_key(KeyCode::Right));
    assert_eq!(
        app.training_state.active_training_focus,
        TrainingFocus::NpuLedger
    );
    let npu_count = app.training_state.npu_grants.len();
    assert_eq!(npu_count, 2);
    assert_eq!(app.training_state.selected_npu_row, 0);

    app.handle_key(make_key(KeyCode::Char('j')));
    assert_eq!(app.training_state.selected_npu_row, 1);
    assert_eq!(app.training_state.npu_table_state.selected(), Some(1));

    // Wrap to 0
    app.handle_key(make_key(KeyCode::Char('j')));
    assert_eq!(app.training_state.selected_npu_row, 0);
    assert_eq!(app.training_state.npu_table_state.selected(), Some(0));

    // 'k' wraps to 1
    app.handle_key(make_key(KeyCode::Char('k')));
    assert_eq!(app.training_state.selected_npu_row, npu_count - 1);

    // Pause toggle via 'p'
    assert!(!app.training_state.is_paused);
    assert_eq!(app.training_state.governor_tier, RamGovernorTier::Full);

    app.handle_key(make_key(KeyCode::Char('p')));
    assert!(app.training_state.is_paused);
    assert_eq!(
        app.training_state.governor_tier,
        RamGovernorTier::EmergencyPause
    );

    app.handle_key(make_key(KeyCode::Char('p')));
    assert!(!app.training_state.is_paused);
    assert_eq!(app.training_state.governor_tier, RamGovernorTier::Full);
}
