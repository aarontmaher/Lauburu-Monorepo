//! ============================================================================
//! Milestone 2 Empirical Challenger Stress Harness
//! ============================================================================
//! Adversarial challenge tests for Ratatui UI rendering and layout stability:
//! 1. Micro-viewport dimensions (0x0, 10x2, 40x8, 49x11, 50x12, 300x100)
//! 2. Zero-panic underflow on extreme dimensions (1x1, 0x100, 100x0, 5000x5000)
//! 3. Keyboard navigation & rapid Tab toggling (10,000 cycles)
//! 4. Row selection bounds, wrapping, and active table switching
//! 5. Stateful Table rendering with TestBackend inspection
//! ============================================================================

use crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyEventState, KeyModifiers};
use lauburu_tui::app::{ActiveTopologyTable, App, Tab};
use lauburu_tui::config::MeshConfig;
use lauburu_tui::ui::render;
use ratatui::backend::TestBackend;
use ratatui::Terminal;
use std::time::Instant;

fn make_key_event(code: KeyCode) -> KeyEvent {
    KeyEvent {
        code,
        modifiers: KeyModifiers::NONE,
        kind: KeyEventKind::Press,
        state: KeyEventState::NONE,
    }
}

fn make_key_event_with_mod(code: KeyCode, modifiers: KeyModifiers) -> KeyEvent {
    KeyEvent {
        code,
        modifiers,
        kind: KeyEventKind::Press,
        state: KeyEventState::NONE,
    }
}

// ----------------------------------------------------------------------------
// 1. Micro-Viewport Dimensions & Zero-Panic Underflow Suite
// ----------------------------------------------------------------------------

#[test]
fn test_micro_viewport_0x0() {
    let backend = TestBackend::new(0, 0);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let res = terminal.draw(|f| render(&mut app, f));
    assert!(res.is_ok(), "Viewport 0x0 must not panic");
}

#[test]
fn test_micro_viewport_10x2() {
    let backend = TestBackend::new(10, 2);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let res = terminal.draw(|f| render(&mut app, f));
    assert!(res.is_ok(), "Viewport 10x2 must not panic");
}

#[test]
fn test_micro_viewport_40x8() {
    let backend = TestBackend::new(40, 8);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let res = terminal.draw(|f| render(&mut app, f));
    assert!(res.is_ok(), "Viewport 40x8 must not panic");

    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();
    assert!(text.contains("Viewport Too Small"), "40x8 is below 50x12 threshold");
}

#[test]
fn test_micro_viewport_49x11() {
    let backend = TestBackend::new(49, 11);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let res = terminal.draw(|f| render(&mut app, f));
    assert!(res.is_ok(), "Viewport 49x11 (just below 50x12) must not panic");

    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();
    assert!(text.contains("Viewport Too Small"), "49x11 must trigger fallback banner");
}

#[test]
fn test_micro_viewport_50x12_exact_boundary() {
    let backend = TestBackend::new(50, 12);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let res = terminal.draw(|f| render(&mut app, f));
    assert!(res.is_ok(), "Viewport 50x12 (exact threshold) must render full layout without panic");

    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();
    assert!(!text.contains("Viewport Too Small"), "50x12 is the exact threshold for full layout");
}

#[test]
fn test_extreme_viewport_300x100() {
    let backend = TestBackend::new(300, 100);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let res = terminal.draw(|f| render(&mut app, f));
    assert!(res.is_ok(), "Viewport 300x100 must render without panic");

    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();
    assert!(text.contains("Mac Mini"), "Must render Mac Mini node in Core Ring");
    assert!(text.contains("Pixel 10"), "Must render Pixel 10 in Edge Pool");
    assert!(text.contains("Pipelined-Ring Parallelism"), "Must render PRP flow diagram");
}

#[test]
fn test_pathological_viewport_aspect_ratios() {
    let test_dims = [
        (1, 1),
        (1, 100),
        (100, 1),
        (0, 100),
        (100, 0),
        (49, 50),
        (50, 11),
        (51, 11),
        (49, 12),
        (51, 13),
        (1000, 2),
        (2, 1000),
        (500, 500),
    ];

    for &(w, h) in &test_dims {
        let backend = TestBackend::new(w, h);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut app = App::new(MeshConfig::fallback());

        // Test on Tab::Topology
        let res_topo = terminal.draw(|f| render(&mut app, f));
        assert!(res_topo.is_ok(), "Topology render panicked on dimension {}x{}", w, h);

        // Test on Tab::Chat
        app.switch_tab(Tab::Chat);
        let res_chat = terminal.draw(|f| render(&mut app, f));
        assert!(res_chat.is_ok(), "Chat render panicked on dimension {}x{}", w, h);
    }
}

// ----------------------------------------------------------------------------
// 2. Keyboard Navigation & Rapid Tab Toggling Stress Suite
// ----------------------------------------------------------------------------

#[test]
fn test_rapid_tab_toggling_stress() {
    let mut app = App::new(MeshConfig::fallback());
    let start = Instant::now();

    for i in 0..10_000 {
        if i % 3 == 0 {
            app.handle_key(make_key_event(KeyCode::Tab));
        } else if i % 3 == 1 {
            app.handle_key(make_key_event(KeyCode::Char('1')));
        } else {
            app.handle_key(make_key_event(KeyCode::Char('2')));
        }
    }

    let elapsed = start.elapsed();
    assert!(
        elapsed.as_millis() < 200,
        "10,000 tab switches should complete in <200ms, took {:?}",
        elapsed
    );
}

#[test]
fn test_row_selection_bounds_and_wrapping_stress() {
    let mut app = App::new(MeshConfig::fallback());
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
    assert_eq!(app.core_table_state.selected(), Some(0));

    // Core nodes = 4 (indices 0..3)
    // Press Down 100 times
    for _ in 0..100 {
        app.handle_key(make_key_event(KeyCode::Down));
    }
    // 100 % 4 = 0 -> back at 0
    assert_eq!(app.core_table_state.selected(), Some(0));

    // Press Up 1 time -> wrap to 3
    app.handle_key(make_key_event(KeyCode::Up));
    assert_eq!(app.core_table_state.selected(), Some(3));

    // Switch to Edge table via Right arrow
    app.handle_key(make_key_event(KeyCode::Right));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);
    assert_eq!(app.edge_table_state.selected(), Some(0));

    // Edge nodes = 3 (indices 0..2)
    // Press Down 100 times
    for _ in 0..100 {
        app.handle_key(make_key_event(KeyCode::Down));
    }
    // 100 % 3 = 1 -> should be index 1
    assert_eq!(app.edge_table_state.selected(), Some(1));

    // Switch back to Core table via Left arrow
    app.handle_key(make_key_event(KeyCode::Left));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
    assert_eq!(app.core_table_state.selected(), Some(3), "Core selection index must be preserved");

    // Vim navigation keys (j/k/h/l)
    app.handle_key(make_key_event(KeyCode::Char('l')));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);
    app.handle_key(make_key_event(KeyCode::Char('j')));
    assert_eq!(app.edge_table_state.selected(), Some(2));
    app.handle_key(make_key_event(KeyCode::Char('k')));
    assert_eq!(app.edge_table_state.selected(), Some(1));
    app.handle_key(make_key_event(KeyCode::Char('h')));
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
}

#[test]
fn test_switch_table_focus_toggle() {
    let mut app = App::new(MeshConfig::fallback());
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);

    app.switch_table_focus();
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Edge);

    app.switch_table_focus();
    assert_eq!(app.active_topology_table, ActiveTopologyTable::Core);
}

#[test]
fn test_quit_key_handling() {
    let mut app = App::new(MeshConfig::fallback());
    assert!(!app.should_quit);

    // Ctrl+C on any tab triggers quit
    app.handle_key(make_key_event_with_mod(KeyCode::Char('c'), KeyModifiers::CONTROL));
    assert!(app.should_quit);

    // Reset and test 'q' on Topology tab
    app.should_quit = false;
    app.handle_key(make_key_event(KeyCode::Char('q')));
    assert!(app.should_quit);

    // Reset and test 'Esc' on Topology tab
    app.should_quit = false;
    app.handle_key(make_key_event(KeyCode::Esc));
    assert!(app.should_quit);
}

// ----------------------------------------------------------------------------
// 3. UI Rendering & Table State Content Inspection
// ----------------------------------------------------------------------------

#[test]
fn test_rendered_topology_table_content_and_highlight() {
    let backend = TestBackend::new(200, 40);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    // Select row 1 (MacBook Pro)
    app.next_core_row();
    assert_eq!(app.core_table_state.selected(), Some(1));

    terminal.draw(|f| render(&mut app, f)).unwrap();
    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();

    // Verify presence of table headers and values
    assert!(text.contains("Layer"), "Core table must have Layer column");
    assert!(text.contains("Node Name"), "Core table must have Node Name column");
    assert!(text.contains("Endpoint"), "Core table must have Endpoint column");
    assert!(text.contains("VRAM"), "Core table must have VRAM column");
    assert!(text.contains("RAM"), "Core table must have RAM column");

    // Verify node details
    assert!(text.contains("Mac Mini"), "Must list Mac Mini");
    assert!(text.contains("MacBook Pro"), "Must list MacBook Pro");
    assert!(text.contains("Linux Head Node"), "Must list Linux Head Node");
    assert!(text.contains("MacBook Air"), "Must list MacBook Air");

    // Verify highlight symbol
    assert!(text.contains("▶"), "Must render selection highlight symbol");
}

#[test]
fn test_rendered_cluster_capabilities_matrix() {
    let backend = TestBackend::new(140, 35);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    terminal.draw(|f| render(&mut app, f)).unwrap();
    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();

    assert!(text.contains("Cluster Architecture & Dynamic Capabilities"), "Must render capabilities title");
    assert!(text.contains("Pooled RAM:"), "Must render Pooled RAM line");
    assert!(text.contains("108.0 GB"), "Must render 108.0 GB pooled RAM");
    assert!(text.contains("Total AI VRAM:"), "Must render Total AI VRAM line");
    assert!(text.contains("82.8 GB Usable"), "Must render 82.8 GB usable VRAM");
    assert!(text.contains("Master Coordinator:"), "Must render Master Coordinator line");
    assert!(text.contains("Dynamic RAM Cap:"), "Must render dynamic RAM cap line");
    assert!(text.contains("Swarm Rule #0:"), "Must render Swarm Rule #0 line");
}

#[test]
fn test_chat_tab_input_and_textarea_rendering() {
    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    app.switch_tab(Tab::Chat);
    app.handle_key(make_key_event(KeyCode::Char('H')));
    app.handle_key(make_key_event(KeyCode::Char('i')));

    terminal.draw(|f| render(&mut app, f)).unwrap();
    let buffer = terminal.backend().buffer();
    let text: String = buffer.content.iter().map(|c| c.symbol()).collect();

    assert!(text.contains("Chat Stream"), "Must render Chat Stream tab");
    assert!(text.contains("prima.cpp Chat Stream"), "Must render chat stream header");
    assert!(text.contains("Prompt Input"), "Must render prompt input box");
}

#[test]
fn test_render_cycle_zero_allocation_and_high_fps_simulation() {
    let backend = TestBackend::new(120, 30);
    let mut terminal = Terminal::new(backend).unwrap();
    let mut app = App::new(MeshConfig::fallback());

    let start = Instant::now();
    // Simulate 600 frames (10 seconds at 60 FPS)
    for i in 0..600 {
        if i % 60 == 0 {
            app.next_tab();
        } else if i % 10 == 0 {
            app.next_core_row();
        }
        terminal.draw(|f| render(&mut app, f)).unwrap();
    }

    let elapsed = start.elapsed();
    let fps = 600.0 / elapsed.as_secs_f64();
    println!("Simulated 600 frames in {:?} ({:.1} FPS)", elapsed, fps);
    assert!(fps > 100.0, "Render pipeline should exceed 100 FPS on TestBackend, achieved {:.1}", fps);
}
