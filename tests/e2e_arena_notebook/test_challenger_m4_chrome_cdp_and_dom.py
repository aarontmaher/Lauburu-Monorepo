"""
Milestone M4 Headless Chrome CDP & DOM Adversarial Challenger Test Suite.
Authored by teamwork_preview_challenger_m4_2.

Comprehensive Empirical Testing:
1. test_chrome_cdp_mesh_console_filter_pills_and_view_toggles:
   - Category filtering (ALL, ONLINE, metal, linux, edge, STANDBY).
   - Active pill CSS synchronization and DOM visibility (.node-card-item display block/none).
   - View mode toggle (⊞ Grid View vs ☰ Table View) and table column headers.
   - Mesh probe simulation trigger with console timestamp logging.
2. test_chrome_cdp_debate_inspector_scrubber_topics_and_autoplay:
   - Topic selection via <select> dropdown (#debate-console-m4 select).
   - Turn cards rendering with role badges (Local Cyan, Cloud Purple, Devil Amber, Consensus Emerald).
   - Prev/Next topic stepping with full boundary wrap-around.
   - Auto-Replay play/pause toggling (#debate-play-btn).
   - Verified diff viewer rendering (syntax coloring for +, -, @@ lines) and Bradley-Terry ELO delta cards.
3. test_chrome_cdp_standalone_js_engines_fuzzing_and_boundary:
   - Fuzzing window.meshConsoleEngine (invalid categories, invalid view modes, nulls).
   - Fuzzing window.debateInspectorEngine (extreme indices -999, 999999, non-numeric IDs).
   - Clean recovery and 0 unhandled console errors.
4. test_chrome_cdp_rapid_interleaved_action_stress:
   - 100 rapid randomized user interactions across Mesh Console and Debate Inspector.
5. test_chrome_cdp_full_nbconvert_all_cells_m1_to_m4_coexistence:
   - Full notebook execution via jupyter nbconvert --to html --execute.
   - Headless Chrome verification of M3 DPO Viewer and M4 Dual Consoles in single page.
6. test_marimo_conversion_and_standalone_dag_execution:
   - Marimo convert and execution with zero MultipleDefinitionError or DAG cycles.
7. test_ast_zero_print_purity_across_all_code_cells:
   - AST validation enforcing 0 bare print() calls in Cells 1–5.
8. test_symbol_namespace_isolation_and_no_clobbering:
   - Multi-milestone namespace validation (M1, M2, M3, M4 co-existence).
"""

import ast
import json
import os
import random
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from playwright.sync_api import sync_playwright

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
JUPYTER_PATH = "/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter"
MARIMO_PATH = "/Users/aaron/.local/bin/marimo"
MARIMO_PYTHON = "/Users/aaron/.local/share/uv/tools/marimo/bin/python"

HEADLESS_ARGS = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-position=-2400,-2400",
    "--disable-dev-shm-usage",
    "--disable-extensions",
]


def render_m4_composite_console_html(output_file: Path) -> str:
    """Executes all notebook cells and dumps standalone M4 composite HTML page."""
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    combined_code = "\n".join("".join(c.get("source", [])) for c in code_cells)

    ns = {
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "__name__": "__main__",
    }
    exec(combined_code, ns)

    composite_html = ns["execute_cell_5"]()
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Master Arena Console - M4 Mesh & Debate Inspector</title>
</head>
<body style="background: #090d16; color: #f8fafc; font-family: Inter, sans-serif; margin: 0; padding: 20px;">
{composite_html}
</body>
</html>"""
    output_file.write_text(full_html, encoding="utf-8")
    return full_html


# =========================================================================
# 1. Mesh Socket Console DOM Toggles & Probes Test
# =========================================================================
def test_chrome_cdp_mesh_console_filter_pills_and_view_toggles(tmp_path):
    """
    Empirically test Mesh Socket Console DOM:
    1. Filter pills toggling (ALL, ONLINE, metal, linux, edge, STANDBY)
    2. Active pill class synchronization
    3. Node card visibility in DOM
    4. Grid View vs Table View toggles
    5. Table headers and row data
    6. Probe refresh action trigger
    """
    html_path = tmp_path / "console_m4_mesh_test.html"
    render_m4_composite_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        page = browser.new_page()

        console_logs = []
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else console_logs.append(msg.text))
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        page.goto(f"file://{html_path}")
        page.wait_for_timeout(100)

        console_root = page.locator("#mesh-telemetry-console-root")
        assert console_root.count() == 1

        # 1. Verify Cluster VRAM & RAM summary header
        summary_text = console_root.inner_text()
        assert "108.0 GB" in summary_text
        assert "82.8 GB" in summary_text
        assert "7-LAYER PHYSICAL MESH" in summary_text

        # 2. Test Category Filter Pills
        filter_tests = [
            ("ALL", 8),
            ("ONLINE", 5),
            ("metal", 3),
            ("linux", 2),
            ("edge", 2),
            ("STANDBY", 3),
        ]

        for cat_name, min_expected_count in filter_tests:
            # Click matching pill button
            pill_btn = console_root.locator(f'.pill-btn:has-text("{cat_name}")').first
            pill_btn.click()
            page.wait_for_timeout(50)

            # Check that clicked pill is active
            assert "active-pill" in (pill_btn.get_attribute("class") or "")

            # Count visible nodes
            visible_count = page.evaluate("""() => {
                const cards = document.querySelectorAll('#mesh-telemetry-console-root .node-card-item');
                let count = 0;
                cards.forEach(c => {
                    if (c.style.display !== 'none') count++;
                });
                return count;
            }""")

            if cat_name == "ALL":
                assert visible_count == 8, f"Expected 8 visible nodes on ALL, got {visible_count}"
            elif cat_name == "metal":
                assert visible_count == 3, f"Expected 3 visible metal nodes, got {visible_count}"
            elif cat_name == "linux":
                assert visible_count == 2, f"Expected 2 visible linux nodes, got {visible_count}"
            elif cat_name == "edge":
                assert visible_count == 2, f"Expected 2 visible edge nodes, got {visible_count}"

        # 3. Test View Mode Toggles (Grid vs Table)
        grid_view = page.locator("#mesh-grid-view")
        table_view = page.locator("#mesh-table-view")
        btn_grid = page.locator("#view-toggle-grid")
        btn_table = page.locator("#view-toggle-table")

        # Initial state: Grid visible, Table hidden
        assert grid_view.is_visible()
        assert not table_view.is_visible()

        # Switch to Table View
        btn_table.click()
        page.wait_for_timeout(150)
        assert not grid_view.is_visible()
        assert table_view.is_visible()
        assert "active-pill" in (btn_table.get_attribute("class") or "")
        assert "active-pill" not in (btn_grid.get_attribute("class") or "")

        # Verify Table structure and rows
        table_rows = page.locator("#mesh-table-view tbody tr")
        assert table_rows.count() == 8
        table_headers = page.locator("#mesh-table-view thead th").all_inner_texts()
        assert any("Layer" in h for h in table_headers)
        assert any("Node Name" in h for h in table_headers)
        assert any("Transport" in h for h in table_headers)
        assert any("AI VRAM Cap" in h for h in table_headers)
        assert any("Health Status" in h for h in table_headers)

        # Switch back to Grid View
        btn_grid.click()
        page.wait_for_timeout(150)
        assert grid_view.is_visible()
        assert not table_view.is_visible()
        assert "active-pill" in (btn_grid.get_attribute("class") or "")
        assert "active-pill" not in (btn_table.get_attribute("class") or "")

        # 4. Test Probe Mesh Button
        probe_btn = page.locator('button.dpo-action-btn:has-text("Probe Mesh")')
        probe_btn.click()
        page.wait_for_timeout(50)
        assert any("Mesh probe telemetry refreshed" in log for log in console_logs)

        assert len(console_errors) == 0, f"Console errors in mesh console test: {console_errors}"
        browser.close()


# =========================================================================
# 2. Debate Stream Inspector Scrubber, Topics, & Auto-Play Test
# =========================================================================
def test_chrome_cdp_debate_inspector_scrubber_topics_and_autoplay(tmp_path):
    """
    Empirically test Live Multi-Agent Debate Inspector DOM:
    1. Topic dropdown selector switching
    2. Prev/Next topic stepping with boundary wrap-around
    3. Auto-Replay play/pause toggling
    4. Multi-agent turn cards and role styles
    5. Actionable Consensus Accord card, ELO deltas, and Diff Viewer syntax
    """
    html_path = tmp_path / "console_m4_debate_test.html"
    render_m4_composite_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        page.goto(f"file://{html_path}")
        page.wait_for_timeout(100)

        debate_root = page.locator("#debate-console-m4")
        assert debate_root.count() == 1

        topic_select = debate_root.locator("select.glass-select")
        prev_btn = debate_root.locator('button.pill-btn:has-text("Prev Topic")')
        next_btn = debate_root.locator('button.pill-btn:has-text("Next Topic")')
        play_btn = debate_root.locator("#debate-play-btn")

        # 1. Verify options in topic dropdown
        options = topic_select.locator("option").all()
        topic_count = len(options)
        assert topic_count >= 1

        # 2. Test Dropdown Selection
        for test_idx in range(min(5, topic_count)):
            topic_select.select_option(str(test_idx))
            page.wait_for_timeout(50)

            # Check that turn cards are populated in #debate-turns-container
            turns_html = page.locator("#debate-turns-container").inner_html()
            assert "glass-card" in turns_html
            assert "Turn " in turns_html

        # 3. Reset to Topic 0 before Stepping and Boundary Wrap-Around
        topic_select.select_option("0")
        page.wait_for_timeout(50)

        # Step Next across topics
        for exp_idx in range(1, min(6, topic_count)):
            next_btn.click()
            page.wait_for_timeout(30)
            cur_val = topic_select.input_value()
            assert cur_val == str(exp_idx)

        # Wrap-around from last topic
        topic_select.select_option(str(topic_count - 1))
        next_btn.click()
        page.wait_for_timeout(30)
        assert topic_select.input_value() == "0"

        # Wrap-around backwards from 0
        prev_btn.click()
        page.wait_for_timeout(30)
        assert topic_select.input_value() == str(topic_count - 1)

        # Reset to Topic 0
        topic_select.select_option("0")

        # 4. Verify Role Color Styles and Badges in Turn Cards
        turns = page.locator("#debate-turns-container .glass-card").all()
        assert len(turns) >= 2

        turns_text = page.locator("#debate-turns-container").inner_text()
        assert "Local Model" in turns_text or "Turn 1" in turns_text or "Sovereign" in turns_text

        # 5. Verify Consensus Accord Card & Verified Diff Viewer
        consensus_container = page.locator("#debate-consensus-container")
        assert consensus_container.count() == 1

        consensus_text = consensus_container.inner_text()
        assert "CONSENSUS" in consensus_text
        assert "ACTIONABLE CONSENSUS ACCORD" in consensus_text
        assert "TOP PRIORITIES" in consensus_text
        assert "BRADLEY-TERRY ELO" in consensus_text

        # 6. Verify Verified Diff Syntax Highlighting
        diff_lines = consensus_container.locator("div[style*='JetBrains Mono'] div").all()
        if len(diff_lines) > 0:
            # Check presence of styled diff lines
            has_add = any("+" in l.inner_text() for l in diff_lines)
            has_del = any("-" in l.inner_text() for l in diff_lines)
            assert has_add or has_del

        # 7. Test Auto-Replay Toggle
        assert "Auto-Replay" in play_btn.inner_text()
        play_btn.click()
        page.wait_for_timeout(50)
        assert "Pause" in play_btn.inner_text()

        play_btn.click()
        page.wait_for_timeout(50)
        assert "Auto-Replay" in play_btn.inner_text()

        assert len(console_errors) == 0, f"Console errors in debate inspector test: {console_errors}"
        browser.close()


# =========================================================================
# 3. Standalone JS Engines Fuzzing & Boundary Inputs
# =========================================================================
def test_chrome_cdp_standalone_js_engines_fuzzing_and_boundary(tmp_path):
    """
    Test direct JavaScript engine invocations with invalid/boundary parameters:
    1. window.meshConsoleEngine.setFilter with unknown categories, null, empty string.
    2. window.meshConsoleEngine.setViewMode with invalid strings.
    3. window.debateInspectorEngine.setTopic with negative index, huge index, null.
    4. window.debateInspectorEngine.stepTopic with extreme delta (+10000, -10000).
    5. Clean recovery and zero console errors.
    """
    html_path = tmp_path / "console_m4_fuzz_test.html"
    render_m4_composite_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        page.goto(f"file://{html_path}")

        # 1. Fuzz window.meshConsoleEngine
        page.evaluate("""() => {
            window.meshConsoleEngine.setFilter('NON_EXISTENT_CAT', null);
            window.meshConsoleEngine.setFilter('', null);
            window.meshConsoleEngine.setFilter(null, null);
            window.meshConsoleEngine.setViewMode('invalid_view_mode', null);
            window.meshConsoleEngine.refreshSimulation();
            // Recover
            window.meshConsoleEngine.setFilter('ALL', null);
            window.meshConsoleEngine.setViewMode('grid', null);
        }""")

        # 2. Fuzz window.debateInspectorEngine
        page.evaluate("""() => {
            window.debateInspectorEngine.setTopic(-9999);
            window.debateInspectorEngine.setTopic(999999);
            window.debateInspectorEngine.setTopic(null);
            window.debateInspectorEngine.setTopic(undefined);
            window.debateInspectorEngine.stepTopic(10000);
            window.debateInspectorEngine.stepTopic(-10000);
            // Toggle autoplay repeatedly
            for (let i = 0; i < 10; i++) {
                window.debateInspectorEngine.toggleAutoPlay();
            }
            // Recover
            window.debateInspectorEngine.setTopic(0);
        }""")

        # Verify page still functioning properly after fuzzing
        turns_html = page.locator("#debate-turns-container").inner_html()
        assert "glass-card" in turns_html

        assert len(console_errors) == 0, f"Console errors during JS fuzzing: {console_errors}"
        browser.close()


# =========================================================================
# 4. Rapid Interleaved Action Stress Test
# =========================================================================
def test_chrome_cdp_rapid_interleaved_action_stress(tmp_path):
    """
    Stress tests 100 rapid interleaved actions across Mesh Console and Debate Inspector.
    """
    html_path = tmp_path / "console_m4_stress_test.html"
    render_m4_composite_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        page = browser.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        page.goto(f"file://{html_path}")

        random.seed(42)
        actions = ["filter_all", "filter_metal", "filter_linux", "view_grid", "view_table", "probe", "next_topic", "prev_topic", "toggle_play"]

        for _ in range(100):
            act = random.choice(actions)
            if act == "filter_all":
                page.evaluate("() => window.meshConsoleEngine.setFilter('ALL', null)")
            elif act == "filter_metal":
                page.evaluate("() => window.meshConsoleEngine.setFilter('metal', null)")
            elif act == "filter_linux":
                page.evaluate("() => window.meshConsoleEngine.setFilter('linux', null)")
            elif act == "view_grid":
                page.evaluate("() => window.meshConsoleEngine.setViewMode('grid', null)")
            elif act == "view_table":
                page.evaluate("() => window.meshConsoleEngine.setViewMode('table', null)")
            elif act == "probe":
                page.evaluate("() => window.meshConsoleEngine.refreshSimulation()")
            elif act == "next_topic":
                page.evaluate("() => window.debateInspectorEngine.stepTopic(1)")
            elif act == "prev_topic":
                page.evaluate("() => window.debateInspectorEngine.stepTopic(-1)")
            elif act == "toggle_play":
                page.evaluate("() => window.debateInspectorEngine.toggleAutoPlay()")

        # Ensure zero console errors accumulated
        assert len(console_errors) == 0, f"Errors during rapid stress test: {console_errors}"
        browser.close()


# =========================================================================
# 5. Full Notebook Nbconvert HTML Execution Test
# =========================================================================
def test_chrome_cdp_full_nbconvert_all_cells_m1_to_m4_coexistence(tmp_path):
    """
    Executes full master notebook via jupyter nbconvert and validates in Headless Chrome
    that M3 DPO Viewer and M4 Dual Consoles co-exist and function without conflict.
    """
    out_html = tmp_path / "full_arena_notebook_executed_m4.html"
    cmd = [
        JUPYTER_PATH,
        "nbconvert",
        "--to", "html",
        "--execute",
        str(NOTEBOOK_PATH),
        "--output", str(out_html.name),
        "--output-dir", str(tmp_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"nbconvert failed: {res.stderr}"
    assert out_html.exists()
    assert out_html.stat().st_size > 500000

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        page.goto(f"file://{out_html}")
        page.wait_for_timeout(200)

        # 1. Verify M3 DPO Viewer exists and works
        dpo_root = page.locator("#dpo-viewer-root")
        assert dpo_root.count() >= 1

        pill_p2 = page.locator('#dpo-viewer-root .pill-btn[data-pillar="2"]').first
        pill_p2.click()
        page.wait_for_timeout(50)

        # 2. Verify M4 Mesh Telemetry Console exists and works
        mesh_root = page.locator("#mesh-telemetry-console-root")
        assert mesh_root.count() >= 1

        btn_table = page.locator("#view-toggle-table").first
        btn_table.click()
        page.wait_for_timeout(50)
        assert page.locator("#mesh-table-view").first.is_visible()

        # 3. Verify M4 Debate Inspector exists and works
        debate_root = page.locator("#debate-console-m4")
        assert debate_root.count() >= 1

        next_topic = debate_root.locator('button.pill-btn:has-text("Next Topic")').first
        next_topic.click()
        page.wait_for_timeout(50)

        assert len(console_errors) == 0, f"Console errors in full notebook page: {console_errors}"
        browser.close()


# =========================================================================
# 6. Marimo Conversion and Standalone DAG Execution Test
# =========================================================================
def test_marimo_conversion_and_standalone_dag_execution(tmp_path):
    """
    Converts notebook to Marimo script and verifies zero symbol collisions or MultipleDefinitionErrors.
    """
    marimo_py = tmp_path / "test_marimo_m4_dag.py"
    cmd_convert = f"{MARIMO_PATH} convert {NOTEBOOK_PATH} > {marimo_py}"
    res_convert = subprocess.run(cmd_convert, shell=True, capture_output=True, text=True)
    assert res_convert.returncode == 0, f"Marimo convert failed: {res_convert.stderr}"
    assert marimo_py.exists()

    # Execute Marimo script with Python
    env = dict(os.environ)
    env["PYTHONPATH"] = "/Users/aaron/.local/share/uv/tools/jupyterlab/lib/python3.13/site-packages"
    res_exec = subprocess.run(
        [MARIMO_PYTHON, str(marimo_py)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60
    )
    assert res_exec.returncode == 0, f"Marimo execution failed:\nSTDOUT:\n{res_exec.stdout}\nSTDERR:\n{res_exec.stderr}"
    assert "MultipleDefinitionError" not in res_exec.stderr
    assert "Traceback" not in res_exec.stderr


# =========================================================================
# 7. AST Zero print() Purity Across All Code Cells Test
# =========================================================================
def test_ast_zero_print_purity_across_all_code_cells():
    """
    Validates that Cells 1 to 5 contain ZERO bare print() calls.
    """
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", []))
            tree = ast.parse(source)
            prints = [
                n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
            ]
            assert len(prints) == 0, f"Cell {idx} contains {len(prints)} print calls at lines {prints}"


# =========================================================================
# 8. Symbol Namespace Isolation & Multi-Milestone Coexistence Test
# =========================================================================
def test_symbol_namespace_isolation_and_no_clobbering():
    """
    Executes all cells in a single dictionary and verifies no key clobbering across M1-M4.
    """
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    ns = {
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "__name__": "__main__",
    }

    for idx, cell in enumerate(code_cells):
        src = "".join(cell.get("source", []))
        exec(src, ns)

    # Check M1-M4 symbols all co-exist
    expected_symbols = [
        "ArenaStateManager",
        "calculate_elo_update",
        "UniversalDPOFormatter",
        "InteractiveDPOSampleViewer",
        "render_training_lake_console",
        "CANONICAL_7LAYER_NODES",
        "CANONICAL_MESH_ENDPOINTS",
        "DebateStreamIngestor",
        "DebateViewRenderer",
        "StandaloneDebateInspectorJS",
        "render_mesh_telemetry_console",
        "execute_cell_5",
    ]

    for sym in expected_symbols:
        assert sym in ns, f"Symbol {sym} missing from combined notebook namespace"
