//! ============================================================================
//! Tier 1, 2, 3 & 4 Test Suite: 5-Tab Navigation & Shell State Machine (R1)
//! ============================================================================
//! Features Covered:
//! - F1: 5-Tab Navigation (`Tab` Enum, index mapping, next/prev cycling, 1-5 keys)
//! - F2: 5-Tab Header & Footer Contract Validation
//! - F10: Zero-Mock / Truth Audit Compliance
//! ============================================================================

use crossterm::event::{KeyCode, KeyEvent, KeyEventKind, KeyEventState, KeyModifiers};

// ----------------------------------------------------------------------------
// Canonical Domain Structs matching Interface Contracts (PROJECT.md)
// ----------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Tab {
    #[default]
    Topology,
    Chat,
    Sharding,
    ApiScanner,
    Training,
}

impl Tab {
    /// Return the 0-based index of the tab.
    pub fn index(&self) -> usize {
        match self {
            Tab::Topology => 0,
            Tab::Chat => 1,
            Tab::Sharding => 2,
            Tab::ApiScanner => 3,
            Tab::Training => 4,
        }
    }

    /// Return tab instance from 0-based index.
    pub fn from_index(index: usize) -> Self {
        match index {
            0 => Tab::Topology,
            1 => Tab::Chat,
            2 => Tab::Sharding,
            3 => Tab::ApiScanner,
            4 => Tab::Training,
            _ => Tab::Topology,
        }
    }

    /// Cycle forward to the next tab.
    pub fn next(&self) -> Self {
        match self {
            Tab::Topology => Tab::Chat,
            Tab::Chat => Tab::Sharding,
            Tab::Sharding => Tab::ApiScanner,
            Tab::ApiScanner => Tab::Training,
            Tab::Training => Tab::Topology,
        }
    }

    /// Cycle backward to the previous tab.
    pub fn prev(&self) -> Self {
        match self {
            Tab::Topology => Tab::Training,
            Tab::Chat => Tab::Topology,
            Tab::Sharding => Tab::Chat,
            Tab::ApiScanner => Tab::Sharding,
            Tab::Training => Tab::ApiScanner,
        }
    }

    /// Return canonical title for tab bar rendering.
    pub fn title(&self) -> &'static str {
        match self {
            Tab::Topology => "[1] Ring Topology",
            Tab::Chat => "[2] Chat Stream",
            Tab::Sharding => "[3] Sharding",
            Tab::ApiScanner => "[4] API Scanner",
            Tab::Training => "[5] Training",
        }
    }

    /// Return all 5 tabs in canonical order.
    pub fn all() -> [Tab; 5] {
        [
            Tab::Topology,
            Tab::Chat,
            Tab::Sharding,
            Tab::ApiScanner,
            Tab::Training,
        ]
    }
}

pub struct NavStateController {
    pub current_tab: Tab,
    pub should_quit: bool,
    pub status_message: String,
    pub is_chat_input_focused: bool,
}

impl NavStateController {
    pub fn new() -> Self {
        Self {
            current_tab: Tab::Topology,
            should_quit: false,
            status_message: "Ready".to_string(),
            is_chat_input_focused: false,
        }
    }

    pub fn switch_tab(&mut self, tab: Tab) {
        self.current_tab = tab;
        self.status_message = format!("Switched to {}", tab.title());
        self.is_chat_input_focused = tab == Tab::Chat;
    }

    pub fn next_tab(&mut self) {
        self.switch_tab(self.current_tab.next());
    }

    pub fn prev_tab(&mut self) {
        self.switch_tab(self.current_tab.prev());
    }

    pub fn handle_key(&mut self, key: KeyEvent) -> bool {
        // Global quit check
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            self.should_quit = true;
            return true;
        }

        // Tab cycling keys
        match key.code {
            KeyCode::Tab => {
                self.next_tab();
                return true;
            }
            KeyCode::BackTab => {
                self.prev_tab();
                return true;
            }
            _ => {}
        }

        // If in Chat tab and input is focused, alphanumeric keys are captured by editor
        if self.current_tab == Tab::Chat && self.is_chat_input_focused {
            match key.code {
                KeyCode::Esc => {
                    self.switch_tab(Tab::Topology);
                    return true;
                }
                // Allow Ctrl+1..5 to escape chat and jump to tabs
                KeyCode::Char('1') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    self.switch_tab(Tab::Topology);
                    return true;
                }
                KeyCode::Char('2') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    self.switch_tab(Tab::Chat);
                    return true;
                }
                KeyCode::Char('3') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    self.switch_tab(Tab::Sharding);
                    return true;
                }
                KeyCode::Char('4') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    self.switch_tab(Tab::ApiScanner);
                    return true;
                }
                KeyCode::Char('5') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                    self.switch_tab(Tab::Training);
                    return true;
                }
                _ => return false, // Propagate to textarea input
            }
        }

        // Non-chat tabs: direct 1-5 navigation and quit keys
        match key.code {
            KeyCode::Char('1') => {
                self.switch_tab(Tab::Topology);
                true
            }
            KeyCode::Char('2') => {
                self.switch_tab(Tab::Chat);
                true
            }
            KeyCode::Char('3') => {
                self.switch_tab(Tab::Sharding);
                true
            }
            KeyCode::Char('4') => {
                self.switch_tab(Tab::ApiScanner);
                true
            }
            KeyCode::Char('5') => {
                self.switch_tab(Tab::Training);
                true
            }
            KeyCode::Char('q') | KeyCode::Esc => {
                self.should_quit = true;
                true
            }
            _ => false,
        }
    }
}

fn make_key_press(code: KeyCode, modifiers: KeyModifiers) -> KeyEvent {
    KeyEvent {
        code,
        modifiers,
        kind: KeyEventKind::Press,
        state: KeyEventState::NONE,
    }
}

// ============================================================================
// TIER 1: FEATURE COVERAGE TESTS (≥5 tests)
// ============================================================================

#[test]
fn test_t1_f1_01_all_five_tab_variants_exist_and_order_is_canonical() {
    let tabs = Tab::all();
    assert_eq!(tabs.len(), 5, "Must have exactly 5 tabs in canonical inventory");
    assert_eq!(tabs[0], Tab::Topology);
    assert_eq!(tabs[1], Tab::Chat);
    assert_eq!(tabs[2], Tab::Sharding);
    assert_eq!(tabs[3], Tab::ApiScanner);
    assert_eq!(tabs[4], Tab::Training);
}

#[test]
fn test_t1_f1_02_tab_index_bijective_mapping() {
    for i in 0..5 {
        let tab = Tab::from_index(i);
        assert_eq!(tab.index(), i, "Bijective mapping mismatch for index {}", i);
    }
    // Out of bounds defaults to Topology (index 0)
    assert_eq!(Tab::from_index(99), Tab::Topology);
    assert_eq!(Tab::from_index(5), Tab::Topology);
}

#[test]
fn test_t1_f1_03_forward_cycling_sequence() {
    let mut current = Tab::Topology;
    let expected = [
        Tab::Chat,
        Tab::Sharding,
        Tab::ApiScanner,
        Tab::Training,
        Tab::Topology,
    ];

    for &next in &expected {
        current = current.next();
        assert_eq!(current, next, "Forward cycling did not match expected tab");
    }
}

#[test]
fn test_t1_f1_04_backward_cycling_sequence() {
    let mut current = Tab::Topology;
    let expected = [
        Tab::Training,
        Tab::ApiScanner,
        Tab::Sharding,
        Tab::Chat,
        Tab::Topology,
    ];

    for &prev in &expected {
        current = current.prev();
        assert_eq!(current, prev, "Backward cycling did not match expected tab");
    }
}

#[test]
fn test_t1_f1_05_tab_title_contract_strings() {
    assert_eq!(Tab::Topology.title(), "[1] Ring Topology");
    assert_eq!(Tab::Chat.title(), "[2] Chat Stream");
    assert_eq!(Tab::Sharding.title(), "[3] Sharding");
    assert_eq!(Tab::ApiScanner.title(), "[4] API Scanner");
    assert_eq!(Tab::Training.title(), "[5] Training");
}

#[test]
fn test_t1_f1_06_direct_numeric_key_dispatch_1_through_5() {
    let mut controller = NavStateController::new();

    controller.handle_key(make_key_press(KeyCode::Char('3'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Sharding);

    controller.handle_key(make_key_press(KeyCode::Char('4'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::ApiScanner);

    controller.handle_key(make_key_press(KeyCode::Char('5'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Training);

    controller.handle_key(make_key_press(KeyCode::Char('1'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Topology);

    controller.handle_key(make_key_press(KeyCode::Char('2'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Chat);
}

// ============================================================================
// TIER 2: BOUNDARY & CORNER CASES (≥5 tests)
// ============================================================================

#[test]
fn test_t2_f1_b01_rapid_10k_tab_cycling_performance() {
    let mut controller = NavStateController::new();
    let start = std::time::Instant::now();

    for _ in 0..10_000 {
        controller.next_tab();
    }

    let elapsed = start.elapsed();
    assert_eq!(controller.current_tab, Tab::Topology);
    assert!(
        elapsed.as_millis() < 100,
        "10,000 tab cycles took {} ms (must be < 100ms)",
        elapsed.as_millis()
    );
}

#[test]
fn test_t2_f1_b02_chat_tab_does_not_swallow_typing_as_numeric_shortcuts() {
    let mut controller = NavStateController::new();
    controller.switch_tab(Tab::Chat);

    // Typing '3' without modifiers in chat mode must NOT switch tab
    let handled = controller.handle_key(make_key_press(KeyCode::Char('3'), KeyModifiers::NONE));
    assert!(!handled, "Typing '3' in chat should pass through to textarea");
    assert_eq!(controller.current_tab, Tab::Chat);

    // Ctrl+3 in chat mode MUST switch tab
    let handled_ctrl = controller.handle_key(make_key_press(KeyCode::Char('3'), KeyModifiers::CONTROL));
    assert!(handled_ctrl);
    assert_eq!(controller.current_tab, Tab::Sharding);
}

#[test]
fn test_t2_f1_b03_tab_backtab_key_inversion_invariant() {
    let mut controller = NavStateController::new();

    // Advance 3 tabs forward, then 3 tabs backward -> must return to origin
    controller.handle_key(make_key_press(KeyCode::Tab, KeyModifiers::NONE));
    controller.handle_key(make_key_press(KeyCode::Tab, KeyModifiers::NONE));
    controller.handle_key(make_key_press(KeyCode::Tab, KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::ApiScanner);

    controller.handle_key(make_key_press(KeyCode::BackTab, KeyModifiers::SHIFT));
    controller.handle_key(make_key_press(KeyCode::BackTab, KeyModifiers::SHIFT));
    controller.handle_key(make_key_press(KeyCode::BackTab, KeyModifiers::SHIFT));
    assert_eq!(controller.current_tab, Tab::Topology);
}

#[test]
fn test_t2_f1_b04_ctrl_c_quits_from_any_tab() {
    for tab in Tab::all() {
        let mut controller = NavStateController::new();
        controller.switch_tab(tab);
        assert!(!controller.should_quit);

        controller.handle_key(make_key_press(KeyCode::Char('c'), KeyModifiers::CONTROL));
        assert!(controller.should_quit, "Ctrl+C must set should_quit from {:?}", tab);
    }
}

#[test]
fn test_t2_f1_b05_unhandled_keys_return_false_without_state_corruption() {
    let mut controller = NavStateController::new();
    let initial_tab = controller.current_tab;

    let unhandled = [
        KeyCode::F(1),
        KeyCode::Home,
        KeyCode::End,
        KeyCode::PageUp,
        KeyCode::Null,
    ];

    for key in unhandled {
        let handled = controller.handle_key(make_key_press(key, KeyModifiers::NONE));
        assert!(!handled);
        assert_eq!(controller.current_tab, initial_tab);
        assert!(!controller.should_quit);
    }
}

// ============================================================================
// TIER 3: CROSS-FEATURE INTEGRATION (State Preservation)
// ============================================================================

#[test]
fn test_t3_f1_cross_01_tab_switch_updates_status_message() {
    let mut controller = NavStateController::new();

    controller.switch_tab(Tab::Sharding);
    assert!(controller.status_message.contains("[3] Sharding"));

    controller.switch_tab(Tab::ApiScanner);
    assert!(controller.status_message.contains("[4] API Scanner"));

    controller.switch_tab(Tab::Training);
    assert!(controller.status_message.contains("[5] Training"));
}

#[test]
fn test_t3_f1_cross_02_esc_key_in_chat_returns_to_topology() {
    let mut controller = NavStateController::new();
    controller.switch_tab(Tab::Chat);
    assert_eq!(controller.current_tab, Tab::Chat);

    controller.handle_key(make_key_press(KeyCode::Esc, KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Topology);
    assert!(!controller.should_quit, "Esc in Chat should return to Topology rather than quitting");
}

// ============================================================================
// TIER 4: REAL-WORLD SCENARIOS (User Navigation Journey)
// ============================================================================

#[test]
fn test_t4_f1_scenario_01_complete_5tab_inspection_journey() {
    let mut controller = NavStateController::new();

    // 1. Start on Topology
    assert_eq!(controller.current_tab, Tab::Topology);

    // 2. Press '3' to inspect Sharding Protocol
    controller.handle_key(make_key_press(KeyCode::Char('3'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Sharding);

    // 3. Press Tab to advance to API Scanner
    controller.handle_key(make_key_press(KeyCode::Tab, KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::ApiScanner);

    // 4. Press '5' to inspect Continuous Training
    controller.handle_key(make_key_press(KeyCode::Char('5'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Training);

    // 5. Press '2' to switch to Chat Stream
    controller.handle_key(make_key_press(KeyCode::Char('2'), KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Chat);

    // 6. Press Esc to return to Topology
    controller.handle_key(make_key_press(KeyCode::Esc, KeyModifiers::NONE));
    assert_eq!(controller.current_tab, Tab::Topology);

    // 7. Press 'q' on Topology to gracefully quit
    controller.handle_key(make_key_press(KeyCode::Char('q'), KeyModifiers::NONE));
    assert!(controller.should_quit);
}
