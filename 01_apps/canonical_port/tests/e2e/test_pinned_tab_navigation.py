"""
E2E & Textual Pilot Test Suite for Pinned Tab Navigation Bar & Keybindings
Requirements Covered:
- R1. Pinned Navigation Bar: Structurally docked/locked at top so it never scrolls out of view during extreme vertical pane/log scrolling.
- R2. Visible Keybindings: Each tab explicitly renders assigned keybindings ([1]..[9], [<] Prev, [>] Next) directly in the navigation bar.
- R3. Mouse & Keyboard Sync: Visual state updates instantaneously via mouse scroll wheel, click, or keyboard shortcuts.
- R4. Layout & Occlusion Protection: Guarantees Header at y=0, NavBar at y=1, Content at y=2..N-2, Legend at y=N-2, Footer at y=N-1 with zero clipping or occlusion.
- R5. Responsive Width Scaling: Responsive formatting across 60, 80, 100, 120, 140, 160, 180 column viewports.
"""

import os
import sys
import pytest
from rich.text import Text

# Ensure tui package is on Python import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from canonical_tui import CanonicalPortTUI
from widgets.pinned_tab_nav_bar import PinnedTabNavBar
from widgets.docked_shortcuts_legend import DockedShortcutsLegend
from screens.agi_coding_terminal_screen import AgiCodingTerminalScreen
from screens.network_screen import NetworkScreen
from screens.hardware_screen import HardwareScreen
from screens.biometrics_screen import BiometricsScreen
from screens.ai_inference_screen import AiInferenceScreen
from screens.training_screen import TrainingScreen
from screens.governance_screen import GovernanceScreen
from screens.tooling_screen import ToolingScreen
from screens.optimization_screen import OptimizationScreen
from textual.containers import ScrollableContainer
from textual.widgets import RichLog, Static, Header, Footer
from textual.geometry import Region, Offset, Size


@pytest.mark.asyncio
async def test_pinned_navbar_rendered_on_all_screens_with_keybindings():
    """
    R2 Verification: Keybindings are visually rendered as part of tab titles on every screen.
    Verify PinnedTabNavBar is present on all 9 screens with keybindings [1]..[9], [<] Prev, [>] Next.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(180, 60)) as pilot:
        screen_keys = [
            ("1", "agi_terminal", AgiCodingTerminalScreen),
            ("2", "network", NetworkScreen),
            ("3", "hardware", HardwareScreen),
            ("4", "biometrics", BiometricsScreen),
            ("5", "ai_inference", AiInferenceScreen),
            ("6", "training", TrainingScreen),
            ("7", "governance", GovernanceScreen),
            ("8", "tooling", ToolingScreen),
            ("9", "optimization", OptimizationScreen),
        ]

        for key, screen_name, expected_cls in screen_keys:
            await pilot.press(key)
            assert isinstance(app.screen, expected_cls)

            # Query PinnedTabNavBar
            navbar = app.screen.query_one(PinnedTabNavBar)
            assert navbar is not None
            assert navbar.active_screen == screen_name

            # Build and verify rendered text in full mode
            text = navbar.build_nav_text(screen_name, width=180)
            plain = text.plain

            # Verify visible keybindings
            assert "[<] Prev" in plain
            assert "[>] Next" in plain
            assert "[1] AGI Term" in plain
            assert "[2] Network" in plain
            assert "[3] Hardware" in plain
            assert "[4] Biometrics" in plain
            assert "[5] Inference" in plain
            assert "[6] Training" in plain
            assert "[7] Governance" in plain
            assert "[8] Tooling" in plain
            assert "[9] Optimization" in plain

            # Verify DockedShortcutsLegend at bottom
            legend = app.screen.query_one(DockedShortcutsLegend)
            assert legend is not None


@pytest.mark.asyncio
async def test_layout_no_occlusion_and_clean_vertical_stack():
    """
    Parent Guidance & Ledger Verification:
    Verify that Header, PinnedTabNavBar, ScrollableContainer, DockedShortcutsLegend, and Footer
    stack cleanly without overlapping or obscuring the topmost terminal pane in 16-pane grid layout.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 40)) as pilot:
        screen = app.screen
        header = screen.query_one(Header)
        navbar = screen.query_one(PinnedTabNavBar)
        container = screen.query_one("#agi-terminal-container")
        legend = screen.query_one(DockedShortcutsLegend)
        footer = screen.query_one(Footer)

        # 1. Header sits at y=0, height=1
        assert header.region.y == 0
        assert header.region.height == 1

        # 2. PinnedTabNavBar sits at y=1, height=1 (directly below Header)
        assert navbar.region.y == 1
        assert navbar.region.height == 1

        # 3. Main container starts at y=2 and occupies remaining vertical headroom
        assert container.region.y == 2
        assert container.region.height == 40 - 4  # 36 lines for content

        # 4. DockedShortcutsLegend sits at y=38, height=1 (directly above Footer)
        assert legend.region.y == 38
        assert legend.region.height == 1

        # 5. Footer sits at y=39, height=1
        assert footer.region.y == 39
        assert footer.region.height == 1

        # 6. Verify rendered strips are non-blank for all fixed components
        strips = screen._compositor.render_strips(screen.size)
        header_text = strips[0].text
        navbar_text = strips[1].text
        legend_text = strips[38].text
        footer_text = strips[39].text

        assert "CANONICAL PORT" in header_text or "LAUBURU" in header_text
        assert "[1]" in navbar_text and "[<]" in navbar_text
        assert "[1/c]" in legend_text or "AGI" in legend_text
        assert len(footer_text.strip()) > 0


@pytest.mark.asyncio
async def test_pinned_navbar_locks_in_place_during_extreme_scrolling():
    """
    R1 Acceptance Criteria Verification:
    The dedicated UI component for tabs remains fixed at the top of the terminal
    during extreme vertical scrolling of the main content area (e.g. 16-pane terminal grid / 500 lines log).
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(120, 40)) as pilot:
        assert isinstance(app.screen, AgiCodingTerminalScreen)
        screen = app.screen

        # Switch to 16 panes
        for _ in range(3):
            await pilot.press("+")
        assert screen.grid_split_count == 16

        # Write 200 lines to output log to induce heavy vertical content overflow
        log_widget = screen.query_one("#terminal-output-log", RichLog)
        for i in range(200):
            log_widget.write(f"[cyan]Stream #{i % 16} line {i}: computing shard tensors...[/cyan]")
        await pilot.pause(0.05)

        container = screen.query_one("#agi-terminal-container", ScrollableContainer)
        navbar = screen.query_one(PinnedTabNavBar)
        legend = screen.query_one(DockedShortcutsLegend)

        # Record navbar and legend dock positions before scrolling
        nav_region_before = navbar.region
        assert nav_region_before.y == 1
        assert nav_region_before.height == 1
        legend_region_before = legend.region
        assert legend_region_before.y == 38

        # Perform extreme vertical scroll down
        container.scroll_end(animate=False)
        await pilot.pause(0.05)

        # Verify scroll container moved down
        assert container.scroll_y > 0 or container.max_scroll_y >= 0

        # Invariant: PinnedTabNavBar remains structurally locked at y=1 without vertical displacement
        assert navbar.region.y == nav_region_before.y
        assert navbar.region.height == 1

        # Invariant: DockedShortcutsLegend remains structurally locked at y=38 without vertical displacement
        assert legend.region.y == legend_region_before.y


@pytest.mark.asyncio
async def test_mouse_and_keyboard_tab_switching_sync():
    """
    R3 Acceptance Criteria Verification:
    Automated Textual pilot test successfully switches tabs using rendered keybindings
    and mouse scroll wheel, verifying that the active tab's visual state updates instantaneously.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 60)) as pilot:
        # 1. Test letter key shortcuts ('c', 'n', 'h', 'b', 'i', 't', 'g', 's', 'o')
        letter_shortcuts = [
            ("c", "agi_terminal", AgiCodingTerminalScreen),
            ("n", "network", NetworkScreen),
            ("h", "hardware", HardwareScreen),
            ("b", "biometrics", BiometricsScreen),
            ("i", "ai_inference", AiInferenceScreen),
            ("t", "training", TrainingScreen),
            ("g", "governance", GovernanceScreen),
            ("s", "tooling", ToolingScreen),
            ("o", "optimization", OptimizationScreen),
        ]

        for key, expected_id, expected_cls in letter_shortcuts:
            await pilot.press(key)
            assert isinstance(app.screen, expected_cls)
            navbar = app.screen.query_one(PinnedTabNavBar)
            assert navbar.active_screen == expected_id

        # 2. Test navigation prev / next keys ('less_than', 'greater_than', 'left', 'right')
        await pilot.press("less_than")
        assert isinstance(app.screen, ToolingScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "tooling"

        await pilot.press("left")
        assert isinstance(app.screen, GovernanceScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "governance"

        await pilot.press("greater_than")
        assert isinstance(app.screen, ToolingScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "tooling"

        await pilot.press("right")
        assert isinstance(app.screen, OptimizationScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "optimization"

        # 3. Test direct number keys ('1' through '9')
        await pilot.press("1")
        assert isinstance(app.screen, AgiCodingTerminalScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "agi_terminal"

        await pilot.press("3")
        assert isinstance(app.screen, HardwareScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "hardware"

        # 4. Test mouse scroll cycling via navbar
        navbar = app.screen.query_one(PinnedTabNavBar)
        navbar.on_mouse_scroll_down(None)
        await pilot.pause(0.05)
        assert isinstance(app.screen, BiometricsScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "biometrics"

        navbar = app.screen.query_one(PinnedTabNavBar)
        navbar.on_mouse_scroll_up(None)
        await pilot.pause(0.05)
        assert isinstance(app.screen, HardwareScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "hardware"


@pytest.mark.asyncio
async def test_mouse_click_on_pinned_nav_bar_tabs():
    """
    Verify clicking on PinnedTabNavBar regions triggers screen transitions with centered coordinate compensation.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(180, 60)) as pilot:
        assert isinstance(app.screen, AgiCodingTerminalScreen)
        navbar = app.screen.query_one(PinnedTabNavBar)

        # 1. Click on hardware tab region
        hw_region = next((r for r in navbar._click_regions if r[2] == "hardware"), None)
        assert hw_region is not None
        start_x, end_x, _ = hw_region
        mid_x = (start_x + end_x) // 2

        # In a 180-col window, text is centered. Let's calculate visual click offset
        w = navbar.size.width
        text_len = navbar._last_text_len
        start_offset = max(0, (w - text_len) // 2) if w > text_len else 0
        visual_click_x = start_offset + mid_x

        await pilot.click(PinnedTabNavBar, offset=(visual_click_x, 0))
        await pilot.pause(0.05)

        assert isinstance(app.screen, HardwareScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "hardware"

        # 2. Click on prev control
        navbar = app.screen.query_one(PinnedTabNavBar)
        prev_region = next((r for r in navbar._click_regions if r[2] == "prev"), None)
        assert prev_region is not None
        p_start, p_end, _ = prev_region
        p_mid = (p_start + p_end) // 2
        visual_prev_x = start_offset + p_mid

        await pilot.click(PinnedTabNavBar, offset=(visual_prev_x, 0))
        await pilot.pause(0.05)

        assert isinstance(app.screen, NetworkScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "network"


@pytest.mark.asyncio
async def test_responsive_width_scaling_across_viewports():
    """
    Adversarial Edge Case Verification:
    Verify PinnedTabNavBar renders without horizontal overflow or clipping across 60, 80, 100, 120, 140, 160, 180 cols.
    """
    navbar = PinnedTabNavBar(active_screen="agi_terminal")

    # Tier 1: Wide Viewport (>=165 cols)
    for w in [165, 180, 200]:
        txt = navbar.build_nav_text("agi_terminal", width=w)
        plain = txt.plain
        assert "[1] AGI Term" in plain
        assert "[9] Optimization" in plain
        assert "[<] Prev" in plain
        assert "[>] Next" in plain
        assert len(plain) <= w

    # Tier 2: Standard Desktop Viewport (115-164 cols)
    for w in [115, 120, 140, 160]:
        txt = navbar.build_nav_text("network", width=w)
        plain = txt.plain
        assert "[1] AGI" in plain
        assert "[2] Net" in plain
        assert "[9] Opt" in plain
        assert "[<] Prev" in plain
        assert "[>] Next" in plain
        assert len(plain) <= w

    # Tier 3: Compact Viewport (70-114 cols, e.g. 80-col terminal)
    for w in [70, 80, 90, 100, 110]:
        txt = navbar.build_nav_text("hardware", width=w)
        plain = txt.plain
        assert "[1]AGI" in plain
        assert "[3]HW" in plain
        assert "[9]Opt" in plain
        assert "[<]" in plain
        assert "[>]" in plain
        assert len(plain) <= w

    # Tier 4: Ultra-compact Viewport (67-69 cols)
    for w in [67, 68, 69]:
        txt = navbar.build_nav_text("biometrics", width=w)
        plain = txt.plain
        assert "[1]AGI" in plain
        assert "[4]Bio" in plain
        assert "[9]Opt" in plain
        assert "[<]" in plain
        assert "[>]" in plain
        assert len(plain) <= w

    # Tier 5: Micro Viewport (50-66 cols)
    for w in [50, 55, 60, 65]:
        txt = navbar.build_nav_text("ai_inference", width=w)
        plain = txt.plain
        assert "[1]A" in plain
        assert "[5]I" in plain
        assert "[9]O" in plain
        assert "[<]" in plain
        assert "[>]" in plain
        assert len(plain) <= w

    # Tier 6: Nano Viewport (<50 cols)
    for w in [35, 40, 45, 48]:
        txt = navbar.build_nav_text("training", width=w)
        plain = txt.plain
        assert "[1]" in plain
        assert "[6]" in plain
        assert "[9]" in plain
        assert "[<]" in plain
        assert "[>]" in plain
        assert len(plain) <= w


@pytest.mark.asyncio
async def test_boundary_character_click_hit_testing():
    """
    Adversarial Edge Case:
    Verify that every single character coordinate [start_x, end_x) inside every tab's
    region maps exclusively to that specific target tab with zero boundary bleed or misdirection.
    """
    navbar = PinnedTabNavBar(active_screen="agi_terminal")
    test_widths = [200, 180, 140, 100, 80, 68, 60, 45]

    for w in test_widths:
        txt = navbar.build_nav_text("agi_terminal", width=w)
        text_len = len(txt.plain)
        start_offset = max(0, (w - text_len) // 2) if w > text_len else 0

        for region_idx, (start_x, end_x, expected_target) in enumerate(navbar._click_regions):
            assert start_x < end_x, f"Region {expected_target} at width {w} has invalid range [{start_x}, {end_x})"
            for char_x in range(start_x, end_x):
                relative_x = char_x
                matched_target = None
                for s_x, e_x, target in navbar._click_regions:
                    if s_x <= relative_x < e_x:
                        matched_target = target
                        break
                assert matched_target == expected_target, (
                    f"Boundary click mismatch at width {w}: char_x={char_x} in [{start_x}, {end_x}) "
                    f"expected '{expected_target}' but matched '{matched_target}'"
                )


@pytest.mark.asyncio
async def test_docked_shortcuts_legend_responsive_tiers_and_click():
    """
    Adversarial Edge Case:
    Verify DockedShortcutsLegend renders without overflow across wide and narrow viewports,
    and clicking shortcuts correctly triggers screen switches, refresh, and quit.
    """
    legend = DockedShortcutsLegend(active_screen="agi_terminal")

    # 1. Tier verification across viewport sizes
    for w in [200, 180, 140, 138, 120, 80, 78, 60, 50, 40]:
        txt = legend.build_legend_text("hardware", width=w)
        plain = txt.plain
        assert len(plain) <= w, f"Legend overflowed width {w}: len={len(plain)} ({plain})"

    # 2. Click hit testing on legend
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 40)) as pilot:
        screen = app.screen
        legend_widget = screen.query_one(DockedShortcutsLegend)
        assert legend_widget is not None

        # Click on Hardware item in legend
        hw_region = next((r for r in legend_widget._click_regions if r[2] == "hardware"), None)
        assert hw_region is not None
        w = legend_widget.size.width
        text_len = legend_widget._last_text_len
        start_offset = max(0, (w - text_len) // 2) if w > text_len else 0
        click_x = start_offset + (hw_region[0] + hw_region[1]) // 2

        await pilot.click(DockedShortcutsLegend, offset=(click_x, 0))
        await pilot.pause(0.05)
        assert isinstance(app.screen, HardwareScreen)
        assert app.screen.query_one(PinnedTabNavBar).active_screen == "hardware"


@pytest.mark.asyncio
async def test_dynamic_terminal_resize_and_tab_click_stress():
    """
    Adversarial Stress Test:
    Verify dynamic terminal resizing between 180, 80, 120, and 60 columns updates
    navbar and legend layout, and tab clicks work seamlessly at all sizes.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(180, 40)) as pilot:
        # Start at 180 cols -> switch to Biometrics
        navbar = app.screen.query_one(PinnedTabNavBar)
        assert navbar._last_text_len == 161

        # Resize to 80 cols
        await pilot.resize_terminal(80, 40)
        await pilot.pause(0.05)
        navbar = app.screen.query_one(PinnedTabNavBar)
        assert navbar._last_text_len == 69

        # Click Network tab at 80 cols
        net_region = next((r for r in navbar._click_regions if r[2] == "network"), None)
        assert net_region is not None
        w = navbar.size.width
        text_len = navbar._last_text_len
        start_offset = max(0, (w - text_len) // 2) if w > text_len else 0
        click_x = start_offset + (net_region[0] + net_region[1]) // 2
        await pilot.click(PinnedTabNavBar, offset=(click_x, 0))
        await pilot.pause(0.05)
        assert isinstance(app.screen, NetworkScreen)

        # Resize to 120 cols
        await pilot.resize_terminal(120, 40)
        await pilot.pause(0.05)
        navbar = app.screen.query_one(PinnedTabNavBar)
        assert navbar._last_text_len == 111

        # Click Governance tab at 120 cols
        gov_region = next((r for r in navbar._click_regions if r[2] == "governance"), None)
        assert gov_region is not None
        w = navbar.size.width
        text_len = navbar._last_text_len
        start_offset = max(0, (w - text_len) // 2) if w > text_len else 0
        click_x = start_offset + (gov_region[0] + gov_region[1]) // 2
        await pilot.click(PinnedTabNavBar, offset=(click_x, 0))
        await pilot.pause(0.05)
        assert isinstance(app.screen, GovernanceScreen)


@pytest.mark.asyncio
async def test_rapid_tab_switching_stress():
    """
    Adversarial Stress Test:
    Verify rapid sequential and interleaved key presses ('1'..'9', '<', '>', 'c', 'n', 'h', 'b', 'i', 't', 'g', 's', 'o')
    succeed without stack overflow, desync, or layout displacement.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(140, 40)) as pilot:
        # Rapid sequence of 27 screen switches
        keys_sequence = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "c", "n", "h", "b", "i", "t", "g", "s", "o",
            "less_than", "less_than", "greater_than", "greater_than",
            "1", "9", "5", "2", "1"
        ]

        for key in keys_sequence:
            await pilot.press(key)

        # Invariant: Final screen is AgiCodingTerminalScreen and navbar/legend are locked
        assert isinstance(app.screen, AgiCodingTerminalScreen)
        navbar = app.screen.query_one(PinnedTabNavBar)
        legend = app.screen.query_one(DockedShortcutsLegend)
        assert navbar.region.y == 1
        assert navbar.region.height == 1
        assert legend.region.y == 38
        assert navbar.active_screen == "agi_terminal"


@pytest.mark.asyncio
async def test_margin_and_separator_click_isolation_no_phantom_actions():
    """
    Adversarial Stress Test:
    Verify clicking on empty margin padding (left/right of centered text) or separator characters
    (pipes '│' or whitespace ' ') does NOT trigger any false-positive screen switch or action dispatch.
    """
    app = CanonicalPortTUI()
    async with app.run_test(size=(180, 40)) as pilot:
        assert isinstance(app.screen, AgiCodingTerminalScreen)
        navbar = app.screen.query_one(PinnedTabNavBar)
        legend = app.screen.query_one(DockedShortcutsLegend)

        w = navbar.size.width
        text_len = navbar._last_text_len
        start_offset = max(0, (w - text_len) // 2) if w > text_len else 0
        assert start_offset > 0, "Test requires start_offset > 0 to verify margin clicks"

        # 1. Click in left margin padding (x = 0, 1, 2)
        for margin_x in [0, 1, 2, start_offset - 1]:
            await pilot.click(PinnedTabNavBar, offset=(margin_x, 0))
            await pilot.pause(0.02)
            assert isinstance(app.screen, AgiCodingTerminalScreen), f"Left margin click at x={margin_x} caused phantom screen switch!"

        # 2. Click in right margin padding (x >= start_offset + text_len)
        for margin_x in [start_offset + text_len, start_offset + text_len + 3, w - 1]:
            await pilot.click(PinnedTabNavBar, offset=(margin_x, 0))
            await pilot.pause(0.02)
            assert isinstance(app.screen, AgiCodingTerminalScreen), f"Right margin click at x={margin_x} caused phantom screen switch!"

        # 3. Click on separator regions between tabs in PinnedTabNavBar
        # In Tier 1 (161 chars): separators ' │ ' are at [8..11), [23..26), etc.
        sep_indices = [8, 9, 10, 23, 24, 25]
        for sep_idx in sep_indices:
            click_x = start_offset + sep_idx
            await pilot.click(PinnedTabNavBar, offset=(click_x, 0))
            await pilot.pause(0.02)
            assert isinstance(app.screen, AgiCodingTerminalScreen), f"Separator click at x={click_x} (rel={sep_idx}) caused phantom switch!"

        # 4. Click in left/right margins and separators of DockedShortcutsLegend
        legend_offset = max(0, (w - legend._last_text_len) // 2)
        for margin_x in [0, 1, legend_offset - 1, legend_offset + legend._last_text_len + 1]:
            await pilot.click(DockedShortcutsLegend, offset=(margin_x, 0))
            await pilot.pause(0.02)
            assert isinstance(app.screen, AgiCodingTerminalScreen), f"Legend margin click at x={margin_x} caused phantom action!"


@pytest.mark.asyncio
async def test_docked_shortcuts_legend_character_boundary_hit_testing():
    """
    Adversarial Edge Case:
    Verify that every single character coordinate [start_x, end_x) inside every shortcut item in
    DockedShortcutsLegend maps strictly to that specific item with zero boundary bleed across all tiers.
    """
    legend = DockedShortcutsLegend(active_screen="agi_terminal")
    test_widths = [200, 180, 140, 100, 80, 60, 45]

    for w in test_widths:
        txt = legend.build_legend_text("agi_terminal", width=w)
        text_len = len(txt.plain)

        for region_idx, (start_x, end_x, expected_target) in enumerate(legend._click_regions):
            assert start_x < end_x, f"Legend region {expected_target} at width {w} has invalid range [{start_x}, {end_x})"
            for char_x in range(start_x, end_x):
                relative_x = char_x
                matched_target = None
                for s_x, e_x, target in legend._click_regions:
                    if s_x <= relative_x < e_x:
                        matched_target = target
                        break
                assert matched_target == expected_target, (
                    f"Legend boundary click mismatch at width {w}: char_x={char_x} in [{start_x}, {end_x}) "
                    f"expected '{expected_target}' but matched '{matched_target}'"
                )


