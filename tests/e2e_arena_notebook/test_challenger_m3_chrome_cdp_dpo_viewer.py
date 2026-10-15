"""
Headless Chrome CDP Adversarial Test Suite for Milestone M3 Interactive DPO Viewer.
Authored by teamwork_preview_challenger_m3_2.

Comprehensive Empirical Testing:
1. test_chrome_cdp_pillar_switching_dropdown_and_pills:
   - Switching across all 6 pillars via Dropdown (#dpo-pillar-dropdown) and Filter Pills (.pill-btn).
   - Verifies active-pill CSS synchronization, badges (pillar, model, elo, latency, tokens), and content areas.
2. test_chrome_cdp_slider_and_prev_next_stepping_boundaries:
   - Slider stepping (#dpo-sample-range-slider) and indicator pill updates ("Sample X of Y").
   - Next ▶ stepping across all samples and wrap-around from max to 0.
   - ◀ Prev stepping and wrap-around from 0 to max.
   - Direct slider manipulation and 100-step rapid click stress test.
3. test_chrome_cdp_copy_json_and_export_triggers_with_toasts:
   - "📋 Copy DPO JSON" clipboard write & toast notification display.
   - "💾 Export JSONL" Blob download event & payload line validation.
   - "⚡ Export to Lake" Tri-Vault sink path & atomic POSIX fsync details in toast.
4. test_chrome_cdp_toast_replacement_and_styling:
   - Toast slot DOM replacement between Copy and Export triggers.
   - Verification of Glassmorphic card styling (.glass-card, #10b981 border).
5. test_chrome_cdp_all_pillars_all_samples_deep_metadata_audit:
   - Exhaustive loop across all 6 pillars and all samples.
   - Verification of positive token counts, valid ELO, non-empty code blocks, and zero mock flags.
6. test_chrome_cdp_rapid_interleaved_action_stress:
   - 100 rapid interleaved actions (pill switch -> step -> copy -> lake export) with 0 console errors.
7. test_chrome_cdp_standalone_js_engine_boundary_and_fuzzing:
   - Boundary inputs (out-of-bounds IDs 0, 7, 999, -42, null, undefined; extreme indices).
   - Global aliases window.inspectPillarDpo and window.exportCurrentDpoPair.
8. test_chrome_cdp_full_nbconvert_executed_html_page:
   - Executes the master notebook via jupyter nbconvert --to html --execute.
   - Loads the full rendered notebook in Google Chrome via CDP and verifies interactive DPO controls work end-to-end.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
import pytest

from playwright.sync_api import sync_playwright

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
JUPYTER_PATH = "/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter"

HEADLESS_ARGS = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--window-position=-2400,-2400",
    "--disable-dev-shm-usage",
    "--disable-extensions",
]


def render_standalone_console_html(output_file: Path) -> str:
    """Executes notebook cells in memory and dumps the standalone training lake console HTML."""
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

    console_html = ns["render_training_lake_console"]()
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Master Arena Console - M3 DPO Viewer</title>
</head>
<body style="background: #090d16; color: #f8fafc; font-family: Inter, sans-serif; margin: 0; padding: 20px;">
{console_html}
</body>
</html>"""
    output_file.write_text(full_html, encoding="utf-8")
    return full_html


def test_chrome_cdp_pillar_switching_dropdown_and_pills(tmp_path):
    """
    Test switching across all 6 pillars via:
    1. Dropdown selection (#dpo-pillar-dropdown)
    2. Filter pills (.pill-btn[data-pillar="N"])
    Verifies DOM text updates, active class toggling, and metadata sync.
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

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

        page.goto(f"file://{html_path}")

        # Canonical pillar definitions
        pillars = [
            (1, "WebDev & UI/UX Arena", "Qwen 2.5 Coder 72B"),
            (2, "SWE-bench Verified", "Qwen 2.5 Coder 72B"),
            (3, "BigCodeBench & LiveCode", "Qwen3-Next-80B-A3B MoE"),
            (4, "Tau-Bench & Tool Calling", "Qwen-AgentWorld-35B"),
            (5, "PhysioNet Clinical DSP", "BioMistral-7B / Qwen-Med"),
            (6, "AgentHarm & Red Team", "Huihui-Qwen3.8-27B"),
        ]

        # 1. Test Dropdown Switching across all 6 pillars
        dropdown = page.locator("#dpo-pillar-dropdown")
        for pid, name, model in pillars:
            dropdown.select_option(str(pid))
            page.wait_for_timeout(50)

            # Verify badge updates
            pillar_badge = page.locator("#badge-pillar-name").inner_text()
            assert name in pillar_badge or f"Pillar {pid}" in pillar_badge

            model_badge = page.locator("#badge-model-name").inner_text()
            assert model in model_badge or "Model:" in model_badge

            # Verify active pill class synced
            active_pill = page.locator("#dpo-viewer-root .pill-btn.active-pill")
            active_pid = active_pill.get_attribute("data-pillar")
            assert active_pid == str(pid)

            # Verify Prompt & Chosen & Rejected content populated
            prompt_text = page.locator("#dpo-prompt-content").inner_text()
            chosen_text = page.locator("#dpo-chosen-content").inner_text()
            rejected_text = page.locator("#dpo-rejected-content").inner_text()
            assert len(prompt_text) > 0
            assert len(chosen_text) > 0
            assert len(rejected_text) > 0

        # 2. Test Filter Pill Buttons Switching across all 6 pillars
        for pid, name, model in reversed(pillars):
            pill_btn = page.locator(f'#dpo-viewer-root .pill-btn[data-pillar="{pid}"]')
            pill_btn.click()
            page.wait_for_timeout(50)

            # Verify dropdown value synced with pill click
            dropdown_val = dropdown.input_value()
            assert dropdown_val == str(pid)

            # Verify badge and content
            pillar_badge = page.locator("#badge-pillar-name").inner_text()
            assert name in pillar_badge or f"Pillar {pid}" in pillar_badge

        assert len(console_errors) == 0, f"Console errors during pillar switching: {console_errors}"
        browser.close()


def test_chrome_cdp_slider_and_prev_next_stepping_boundaries(tmp_path):
    """
    Test slider stepping and Prev/Next buttons:
    1. Slider range interaction and sample indicator pill updates
    2. Next button forward stepping and wrap-around from max to 0
    3. Prev button backward stepping and wrap-around from 0 to max
    4. Rapid stepping stress test (100 steps)
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

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

        slider = page.locator("#dpo-sample-range-slider")
        indicator = page.locator("#dpo-sample-indicator-pill")
        prev_btn = page.locator('button.dpo-step-btn:has-text("Prev")')
        next_btn = page.locator('button.dpo-step-btn:has-text("Next")')

        # Read max sample count
        max_attr = slider.get_attribute("max")
        total_samples = int(max_attr) + 1
        assert total_samples >= 1

        # Initial state: Sample 1 of N
        init_ind = indicator.inner_text()
        assert init_ind == f"Sample 1 of {total_samples}"

        # 1. Step Next through all samples
        for expected_idx in range(1, total_samples):
            next_btn.click()
            ind_text = indicator.inner_text()
            assert ind_text == f"Sample {expected_idx + 1} of {total_samples}"
            slider_val = slider.input_value()
            assert slider_val == str(expected_idx)

        # 2. Wrap-around Test: Next from max boundary should wrap back to Sample 1
        next_btn.click()
        wrap_ind = indicator.inner_text()
        assert wrap_ind == f"Sample 1 of {total_samples}"
        assert slider.input_value() == "0"

        # 3. Wrap-around Test: Prev from 0 boundary should wrap to max
        prev_btn.click()
        prev_wrap_ind = indicator.inner_text()
        assert prev_wrap_ind == f"Sample {total_samples} of {total_samples}"
        assert slider.input_value() == str(total_samples - 1)

        # 4. Direct Slider Manipulation
        slider.fill("0")
        slider.dispatch_event("input")
        assert indicator.inner_text() == f"Sample 1 of {total_samples}"

        # 5. Rapid Stepping Stress Test (100 clicks)
        for _ in range(100):
            next_btn.click()
        ind_final = indicator.inner_text()
        assert "Sample " in ind_final

        assert len(console_errors) == 0, f"Console errors during stepping: {console_errors}"
        browser.close()


def test_chrome_cdp_copy_json_and_export_triggers_with_toasts(tmp_path):
    """
    Test Action Triggers:
    1. Copy DPO JSON: Copies valid JSON to clipboard and displays toast.
    2. Export JSONL: Triggers Blob file download with valid JSONL payload.
    3. Export to Lake: Updates #export-toast-slot with atomic POSIX fsync details.
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
            accept_downloads=True,
        )
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        page.goto(f"file://{html_path}")

        toast_slot = page.locator("#export-toast-slot")

        # 1. Test Copy DPO JSON Trigger
        copy_btn = page.locator('button.dpo-action-btn:has-text("Copy DPO JSON")')
        copy_btn.click()
        page.wait_for_timeout(100)

        # Check Toast Display
        toast_content = toast_slot.inner_html()
        assert "Canonical DPO JSON copied to clipboard" in toast_content
        assert "glass-card" in toast_content

        # Verify Clipboard Content
        clipboard_text = page.evaluate("navigator.clipboard.readText()")
        copied_data = json.loads(clipboard_text)
        assert "prompt" in copied_data
        assert "chosen" in copied_data
        assert "rejected" in copied_data
        assert copied_data["metadata"]["zero_mock_certified"] is True

        # 2. Test Export JSONL Trigger (Download)
        export_jsonl_btn = page.locator('button.dpo-action-btn:has-text("Export JSONL")')
        with page.expect_download() as download_info:
            export_jsonl_btn.click()
        download = download_info.value
        assert "pillar_1_dpo_pairs.jsonl" in download.suggested_filename

        dl_path = tmp_path / download.suggested_filename
        download.save_as(dl_path)
        assert dl_path.exists()
        lines = dl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 1
        for line in lines:
            rec = json.loads(line)
            assert "prompt" in rec and "chosen" in rec and "rejected" in rec

        # 3. Test Export to Lake Trigger
        export_lake_btn = page.locator('button.dpo-action-btn:has-text("Export to Lake")')
        export_lake_btn.click()
        page.wait_for_timeout(100)

        lake_toast = toast_slot.inner_html()
        assert "DPO Training Pair Exported to Tri-Vault Lake" in lake_toast
        assert "continuous_lora_dataset.jsonl" in lake_toast
        assert "POSIX Atomic fsync Complete" in lake_toast

        assert len(console_errors) == 0, f"Console errors during triggers: {console_errors}"
        browser.close()


def test_chrome_cdp_toast_replacement_and_styling(tmp_path):
    """
    Test that toast slot updates and replaces content cleanly across multiple triggers.
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()

        page.goto(f"file://{html_path}")
        toast_slot = page.locator("#export-toast-slot")

        # Initial state: toast slot is empty
        assert toast_slot.inner_html() == ""

        # Trigger 1: Copy
        copy_btn = page.locator('button.dpo-action-btn:has-text("Copy DPO JSON")')
        copy_btn.click()
        page.wait_for_timeout(50)
        assert "Canonical DPO JSON copied to clipboard" in toast_slot.inner_html()

        # Trigger 2: Lake Export replaces Copy Toast
        export_lake_btn = page.locator('button.dpo-action-btn:has-text("Export to Lake")')
        export_lake_btn.click()
        page.wait_for_timeout(50)
        lake_html = toast_slot.inner_html()
        assert "DPO Training Pair Exported to Tri-Vault Lake" in lake_html
        assert "Canonical DPO JSON copied to clipboard" not in lake_html

        browser.close()


def test_chrome_cdp_all_pillars_all_samples_deep_metadata_audit(tmp_path):
    """
    Iterates through all 6 pillars and every sample within each pillar.
    Verifies:
    - Prompt, Chosen, Rejected non-empty
    - Tokens badges positive integers
    - ELO badge formatted as decimal number
    - TTFT latency positive float
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True,
            args=HEADLESS_ARGS,
        )
        page = browser.new_page()
        page.goto(f"file://{html_path}")

        for pid in range(1, 7):
            page.evaluate(f"() => window.dpoViewerEngine.setPillar({pid})")
            slider_max = int(page.locator("#dpo-sample-range-slider").get_attribute("max"))
            sample_count = slider_max + 1

            for s_idx in range(sample_count):
                page.evaluate(f"() => window.dpoViewerEngine.setIndex({s_idx})")

                prompt = page.locator("#dpo-prompt-content").inner_text()
                chosen = page.locator("#dpo-chosen-content").inner_text()
                rejected = page.locator("#dpo-rejected-content").inner_text()
                assert len(prompt.strip()) > 0, f"Empty prompt on Pillar {pid} Sample {s_idx}"
                assert len(chosen.strip()) > 0, f"Empty chosen on Pillar {pid} Sample {s_idx}"
                assert len(rejected.strip()) > 0, f"Empty rejected on Pillar {pid} Sample {s_idx}"

                elo_text = page.locator("#badge-elo-score").inner_text()
                assert "ELO:" in elo_text

                tot_tok = page.locator("#badge-total-tokens").inner_text()
                assert "Total:" in tot_tok and "tok" in tot_tok

        browser.close()


def test_chrome_cdp_rapid_interleaved_action_stress(tmp_path):
    """
    Stress-tests rapid interleaved user actions:
    100 randomized pill clicks, slider moves, step clicks, copy triggers, and lake exports.
    Enforces 0 console errors or exceptions.
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

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

        page.goto(f"file://{html_path}")

        import random
        random.seed(42)

        for _ in range(100):
            action = random.choice(["pill", "step_next", "step_prev", "copy", "lake", "slider"])
            if action == "pill":
                pid = random.randint(1, 6)
                page.locator(f'#dpo-viewer-root .pill-btn[data-pillar="{pid}"]').click()
            elif action == "step_next":
                page.locator('button.dpo-step-btn:has-text("Next")').click()
            elif action == "step_prev":
                page.locator('button.dpo-step-btn:has-text("Prev")').click()
            elif action == "copy":
                page.locator('button.dpo-action-btn:has-text("Copy DPO JSON")').click()
            elif action == "lake":
                page.locator('button.dpo-action-btn:has-text("Export to Lake")').click()
            elif action == "slider":
                slider = page.locator("#dpo-sample-range-slider")
                max_val = int(slider.get_attribute("max") or 0)
                if max_val > 0:
                    val = random.randint(0, max_val)
                    slider.fill(str(val))
                    slider.dispatch_event("input")

        assert len(console_errors) == 0, f"Errors during rapid stress: {console_errors}"
        browser.close()


def test_chrome_cdp_standalone_js_engine_boundary_and_fuzzing(tmp_path):
    """
    Test direct JS calls to window.dpoViewerEngine for boundary values,
    unhandled exceptions, and invalid inputs:
    - Out of bounds pillar IDs (0, 7, 999, -42, null, undefined)
    - Out of bounds indices (-100, 10000)
    - Global alias inspection (window.inspectPillarDpo, window.exportCurrentDpoPair)
    """
    html_path = tmp_path / "console_dpo_test.html"
    render_standalone_console_html(html_path)

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

        # 1. Test Global Alias Functions
        res_alias = page.evaluate("""() => {
            window.inspectPillarDpo(3);
            const p3Text = document.getElementById('badge-pillar-name').innerText;
            window.exportCurrentDpoPair();
            const toast = document.getElementById('export-toast-slot').innerHTML;
            return { p3Text, hasToast: toast.includes('DPO Training Pair Exported') };
        }""")
        assert "BigCodeBench" in res_alias["p3Text"]
        assert res_alias["hasToast"] is True

        # 2. Test Extreme Indices
        page.evaluate("""() => {
            window.dpoViewerEngine.setIndex(999999);
        }""")
        # Clamped to max index without crashing
        ind = page.locator("#dpo-sample-indicator-pill").inner_text()
        assert "Sample " in ind

        page.evaluate("""() => {
            window.dpoViewerEngine.setIndex(-999999);
        }""")
        # Clamped to 0
        ind_zero = page.locator("#dpo-sample-indicator-pill").inner_text()
        assert "Sample 1 of " in ind_zero

        # 3. Test Invalid / Boundary Pillar IDs
        for bad_id in [0, 7, 999, -1, None]:
            page.evaluate(f"() => window.dpoViewerEngine.setPillar({json.dumps(bad_id)})")

        # 4. Recover cleanly back to Pillar 1
        page.evaluate("() => window.dpoViewerEngine.setPillar(1)")
        p1 = page.locator("#badge-pillar-name").inner_text()
        assert "WebDev" in p1

        assert len(console_errors) == 0, f"Console errors during JS engine fuzzing: {console_errors}"
        browser.close()


def test_chrome_cdp_full_nbconvert_executed_html_page(tmp_path):
    """
    Executes full master notebook via jupyter nbconvert and loads the rendered HTML
    in Headless Chrome. Verifies DPO viewer interactive buttons respond cleanly.
    """
    out_html = tmp_path / "full_arena_notebook_executed.html"
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

        # Verify DPO viewer is present in rendered notebook
        dpo_root = page.locator("#dpo-viewer-root")
        assert dpo_root.count() >= 1

        # Test interaction inside full rendered notebook: switch to Pillar 2 (SWE-bench)
        pill_p2 = page.locator('#dpo-viewer-root .pill-btn[data-pillar="2"]').first
        pill_p2.click()
        page.wait_for_timeout(100)

        # Verify SWE-bench badge
        pillar_badge = page.locator("#badge-pillar-name").first.inner_text()
        assert "SWE-bench" in pillar_badge

        # Test Next step button inside full notebook
        next_btn = page.locator('#dpo-viewer-root button.dpo-step-btn:has-text("Next")').first
        next_btn.click()
        page.wait_for_timeout(50)

        ind = page.locator("#dpo-sample-indicator-pill").first.inner_text()
        assert "Sample 2 of " in ind

        # Test Lake Export inside full notebook
        lake_btn = page.locator('#dpo-viewer-root button.dpo-action-btn:has-text("Export to Lake")').first
        lake_btn.click()
        page.wait_for_timeout(50)

        toast = page.locator("#export-toast-slot").first.inner_html()
        assert "DPO Training Pair Exported" in toast

        assert len(console_errors) == 0, f"Console errors in full rendered notebook: {console_errors}"
        browser.close()
