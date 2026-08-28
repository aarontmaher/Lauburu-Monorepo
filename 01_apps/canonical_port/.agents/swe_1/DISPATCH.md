## 2026-08-27T09:29:50+10:00

Implement a pinned, always-visible tab navigation bar and keybinding legend for the Canonical Port TUI. The tabs must remain locked in place during pane scrolling, ensuring the user always knows their current view and the keys to switch contexts.

This is a single self-contained UI fix; keep it small and focused.

Working directory: ~/DFS_UNIFIED/Lauburu-Monorepo/01_apps/canonical_port
Integrity mode: development

Requirements:
- R1. Pinned Navigation Bar: The tab navigation list must be structurally docked (e.g., as a Textual Header or fixed Dock component) so that it never scrolls out of view when the user scrolls through the 16-pane terminal grids or logs.
- R2. Visible Keybindings: Each tab must explicitly render its assigned keybinding (e.g., `[1] Hardware`, `[2] Network`, `[<] Prev`, `[>] Next`) directly on the navigation bar so the user never has to guess how to switch screens.
- R3. Mouse & Keyboard Sync: The visual state of the pinned tabs must update instantaneously whether the user navigates via the mouse scroll wheel or the dedicated keyboard shortcuts.

Acceptance Criteria:
- A dedicated UI component for the tabs remains fixed at the top or bottom of the terminal during extreme vertical scrolling of the main content area.
- Keybindings are visually rendered as part of the tab titles.
- An automated Textual pilot test successfully switches tabs using the rendered keybindings and verifies that the active tab's visual state updates correctly.

Execute the SWE Light workflow: spawn one implementer on the whole task, then run reviewer rounds carrying a cumulative open-issues ledger, establish correctness via tests, and send a completion message back to parent when done.

## 2026-08-26T23:32:48Z

Guidance from parent:
"Keep up the pace on the Round 0 Implementer. Ensure that pinning the Textual Header/Dock does not obscure the topmost terminal pane in the 16-pane grid layout. Proceed to adversarial review!"
Please ensure the implementer and reviewers incorporate this constraint into verification.
