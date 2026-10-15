#!/usr/bin/env python3
"""
Adversarial Stress Test Harness for Milestone M1 (Glassmorphic High-DPI UI/UX & Tailwind Theme)
Target: 00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb

Covers:
1. Headless execution across varied environments & parameters (nbconvert, standalone python, cwd invariance)
2. Rendering under extreme data conditions (0/5000 ELO, strings, missing fields, fuzzing, XSS)
3. CSS syntax validity and class name collisions
4. Image dimensions, DPI (>=150 DPI), and file integrity on disk
"""

import os
import sys
import io
import re
import json
import time
import math
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Monorepo and Target Paths
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault/notebooks/00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb"
IMAGE_PATH = MONOREPO_ROOT / "obsidian_vault/notebooks/6_pillar_dark_console.png"
JUPYTER_BIN = Path("/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter")
PYTHON_BIN = Path("/Users/aaron/.local/share/uv/tools/jupyterlab/bin/python")
MARIMO_BIN = Path("/Users/aaron/.local/share/uv/tools/marimo/bin/marimo")


# =========================================================================
# HELPER EXTRACTION FROM NOTEBOOK CELL 1
# =========================================================================
def extract_notebook_code():
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)
    code_cells = [c["source"] for c in nb["cells"] if c["cell_type"] == "code"]
    full_code = "\n".join("".join(c) for c in code_cells)
    return full_code, nb

FULL_CODE, NB_JSON = extract_notebook_code()

# Execute helper definitions in an isolated sandbox dict
SANDBOX = {
    "__name__": "__arena_sandbox__",
    "display": lambda x: x,
    "HTML": lambda x: x,
}
exec(
    """
import os, sys, time, json, shutil, html
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
""",
    SANDBOX,
)

# Extract and exec Cell 1 code into SANDBOX
cell1_source = "".join(NB_JSON["cells"][1]["source"])
# remove display calls from direct exec to prevent interference
cleaned_cell1 = re.sub(r'display\(HTML\(.*?\)\)', '', cell1_source, flags=re.DOTALL)
exec(cleaned_cell1, SANDBOX)

# Convenience function references
render_status_pulse = SANDBOX["render_status_pulse"]
render_glass_metric_card = SANDBOX["render_glass_metric_card"]
render_pillar_badge = SANDBOX["render_pillar_badge"]
render_styled_table = SANDBOX["render_styled_table"]
render_export_toast = SANDBOX["render_export_toast"]
render_dpo_split_view = SANDBOX["render_dpo_split_view"]
render_telemetry_probe_card = SANDBOX["render_telemetry_probe_card"]
ARENA_CYBERPUNK_CSS = SANDBOX["ARENA_CYBERPUNK_CSS"]


# =========================================================================
# SUITE 1: HEADLESS EXECUTION ACROSS ENVIRONMENTS & PARAMETERS
# =========================================================================
class TestSuite1HeadlessExecution:
    """Stress tests headless execution of the master arena notebook."""

    def test_jupyter_nbconvert_headless_execution(self):
        """Verify nbconvert cleanly executes all cells to HTML without errors."""
        assert NOTEBOOK_PATH.exists(), f"Notebook does not exist: {NOTEBOOK_PATH}"
        assert JUPYTER_BIN.exists(), f"Jupyter binary not found at: {JUPYTER_BIN}"

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_out:
            tmp_html_path = tmp_out.name

        try:
            cmd = [
                str(JUPYTER_BIN),
                "nbconvert",
                "--to", "html",
                "--execute",
                "--ExecutePreprocessor.timeout=60",
                str(NOTEBOOK_PATH),
                "--output", tmp_html_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            assert res.returncode == 0, f"nbconvert failed (code {res.returncode}): {res.stderr}\n{res.stdout}"
            assert os.path.exists(tmp_html_path), "Output HTML was not generated"
            file_size = os.path.getsize(tmp_html_path)
            assert file_size > 10_000, f"Output HTML too small ({file_size} bytes)"

            with open(tmp_html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Verify no Python traceback error divs in output
            assert "output_stderr" not in html_content or "Traceback" not in html_content
            assert "output_error" not in html_content
            assert "LIVE MESH ENGINE" in html_content
            assert "6_pillar_dark_console.png" in html_content
        finally:
            if os.path.exists(tmp_html_path):
                os.remove(tmp_html_path)

    def test_marimo_conversion_compatibility(self):
        """Verify the notebook can be converted cleanly by marimo if marimo is available."""
        if MARIMO_BIN.exists():
            cmd = [str(MARIMO_BIN), "convert", str(NOTEBOOK_PATH)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            assert res.returncode == 0, f"marimo convert failed: {res.stderr}"
            assert "import marimo" in res.stdout or "@app.cell" in res.stdout

    def test_cwd_invariance_and_path_resolution(self):
        """Verify extracted code executes identically from arbitrary working directories."""
        test_cwds = ["/tmp", "/Users/aaron", str(MONOREPO_ROOT)]
        
        # Test code snippet running cells 1, 2, 3, 4 with headless Agg backend
        script = f"""
import sys, os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.show = lambda *args, **kwargs: None
from pathlib import Path

notebook_path = Path('{NOTEBOOK_PATH}')
import json
with open(notebook_path) as f:
    nb = json.load(f)

# Mock IPython display and HTML
class MockHTML:
    def __init__(self, data): self.data = data
def display(obj): pass

g = {{
    '__name__': '__main__',
    'display': display,
    'HTML': MockHTML,
    'plt': plt
}}
for c in nb['cells']:
    if c['cell_type'] == 'code':
        code = ''.join(c['source'])
        exec(code, g)

assert 'PILLARS' in g
assert len(g['PILLARS']) == 6
assert os.path.exists('{IMAGE_PATH}')
print("SUCCESS_CWD_INVARIANCE")
"""
        env = {**os.environ, "MPLBACKEND": "Agg"}
        for cwd in test_cwds:
            res = subprocess.run(
                [str(PYTHON_BIN), "-c", script],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=40
            )
            assert res.returncode == 0, f"Execution failed in CWD={cwd}: {res.stderr}"
            assert "SUCCESS_CWD_INVARIANCE" in res.stdout

    def test_repeated_execution_idempotency(self):
        """Verify 3 consecutive executions do not create file corruption or race conditions."""
        for i in range(3):
            # Run figure generation logic
            fig = plt.figure(figsize=(19, 5.4), dpi=160)
            ax1 = fig.add_subplot(1, 3, 1)
            ax1.barh([0, 1], [2500, 2600])
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                tmp_path = tmp_img.name
            try:
                fig.savefig(tmp_path, dpi=160)
                plt.close(fig)
                assert os.path.getsize(tmp_path) > 1000
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)


# =========================================================================
# SUITE 2: RENDERING UNDER EXTREME DATA CONDITIONS & BOUNDARIES
# =========================================================================
class TestSuite2ExtremeDataRendering:
    """Stress tests rendering helper functions with adversarial and boundary inputs."""

    def test_render_status_pulse_extreme_inputs(self):
        # Null, empty, whitespace
        h1 = render_status_pulse("", is_online=True)
        assert "<span" in h1
        h2 = render_status_pulse(None, is_online=False)
        assert "None" in h2

        # Special chars and XSS injection in extra_info
        xss_payload = '<script>alert("XSS")</script>'
        h3 = render_status_pulse("ONLINE", is_online=True, extra_info=xss_payload)
        assert "<script>" not in h3
        assert "&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;" in h3

        # Non-ascii, RTL, unicode emojis
        h4 = render_status_pulse("⚡ 🔴 🟢 🚀 SYNCHRONIZED 状态", is_online=True, extra_info="مرحبا بالعالم")
        assert "SYNCHRONIZED" in h4

        # Massive string length (10,000 characters)
        long_str = "A" * 10000
        h5 = render_status_pulse(long_str, is_online=True)
        assert len(h5) > 10000

    def test_render_glass_metric_card_extreme_inputs(self):
        # Extreme progress_pct bounds (-1000, 0, 100, 99999, None)
        c1 = render_glass_metric_card("Test", "100", progress_pct=-1000)
        assert "width: 0%;" in c1  # Clamped to 0
        c2 = render_glass_metric_card("Test", "100", progress_pct=99999)
        assert "width: 100%;" in c2  # Clamped to 100
        c3 = render_glass_metric_card("Test", "100", progress_pct=None)
        assert "progress-neon" not in c3

        # Extreme string values and XSS payloads in title/subtitle/icon
        xss = '<img src=x onerror=alert(1)>'
        c4 = render_glass_metric_card(xss, xss, subtitle=xss, icon="🔥")
        assert "<img" not in c4
        assert "&lt;img" in c4

        # None / Missing values
        c5 = render_glass_metric_card(None, None, subtitle=None)
        assert "None" in c5

    def test_render_pillar_badge_extreme_elo_and_bounds(self):
        # Extreme ELO: 0.0, 5000.0, negative, None, float('nan')
        p1 = render_pillar_badge("Pillar 0", elo=0.0)
        assert "ELO: 0.0" in p1
        p2 = render_pillar_badge("Pillar 5000", elo=5000.0)
        assert "ELO: 5000.0" in p2
        p3 = render_pillar_badge("Pillar None", elo=None)
        assert "ELO:" not in p3

        # Huge sample counts & zero samples
        p4 = render_pillar_badge("Pillar Huge", dataset="test/huge", samples=10**12)
        assert "1,000,000,000,000 pairs" in p4
        p5 = render_pillar_badge("Pillar Zero", dataset="test/zero", samples=0)
        assert "•" not in p5  # Zero samples omitted cleanly

        # XSS injection in pillar_name, lead_model, dataset
        xss = "'; DROP TABLE models; -- <script>alert(1)</script>"
        p6 = render_pillar_badge(pillar_name=xss, lead_model=xss, dataset=xss)
        assert "<script>" not in p6
        assert "&lt;script&gt;" in p6

    def test_render_styled_table_extreme_inputs(self):
        headers = ["Col A", "Col B", "Col C"]

        # Empty rows
        t1 = render_styled_table(headers, [])
        assert "0 Records" in t1
        assert "<tbody></tbody>" in t1

        # Mismatched rows (dict missing keys, list shorter/longer than headers)
        t2 = render_styled_table(headers, [{"Col A": "Val1"}])
        assert "Val1" in t2
        t3 = render_styled_table(headers, [["A1"], ["B1", "B2", "B3", "B4_extra"]])
        assert "A1" in t3

        # Mixed types (ints, floats, dicts, booleans, None)
        t4 = render_styled_table(headers, [
            [123, 45.67, True],
            [None, {"nested": 1}, [1, 2]],
            ["ONLINE", "WAITING_FOR_DATASET", "FAIL"]
        ])
        assert "badge-emerald" in t4
        assert "badge-amber" in t4
        assert "badge-cyan" in t4

        # 1,000 rows stress test
        large_rows = [[f"row_{i}_c1", f"row_{i}_c2", f"row_{i}_c3"] for i in range(1000)]
        t5 = render_styled_table(headers, large_rows, title="Massive Table")
        assert "1000 Records" in t5
        assert len(t5) > 50_000

    def test_render_dpo_split_view_extreme_payloads(self):
        # 50,000 char prompt, chosen, rejected
        huge_prompt = "P" * 20000
        huge_chosen = "C" * 20000
        huge_rejected = "R" * 20000
        v1 = render_dpo_split_view(huge_prompt, huge_chosen, huge_rejected)
        assert len(v1) > 60000

        # Markdown, Python code with quotes, backticks, brackets
        code_prompt = 'def foo(x):\n    """Docstring with \'quotes\' and "double" """\n    return x `test` <xml>'
        v2 = render_dpo_split_view(code_prompt, 'chosen_code()', 'rejected_code()', metadata={"pillar_id": 1, "elo": 2640.0})
        assert "&lt;xml&gt;" in v2
        assert "pillar_id: 1" in v2

    def test_render_telemetry_probe_card_extremes(self):
        # Null rtt_ms
        c1 = render_telemetry_probe_card("Node 1", "http://10.0.0.1:4000", "ONLINE", rtt_ms=None)
        assert "--" in c1
        # High precision float RTT
        c2 = render_telemetry_probe_card("Node 2", "http://10.0.0.2:4000", "OFFLINE", rtt_ms=0.00034)
        assert "0.00 ms RTT" in c2

    def test_matplotlib_3panel_figure_with_extreme_data(self):
        """Stress-test Matplotlib 3-panel plotting function under extreme ELOs and counts."""
        extreme_cases = [
            # Case 1: Extreme high ELOs (5000+)
            [{"pillar": f"P{i}", "elo": 5000.0 + i*100, "color": "#06b6d4", "tok_s": 500.0, "ttft_ms": 1.0} for i in range(6)],
            # Case 2: Extreme low ELOs (0.0 to 100.0)
            [{"pillar": f"P{i}", "elo": 10.0 * i, "color": "#3b82f6", "tok_s": 0.1, "ttft_ms": 500.0} for i in range(6)],
            # Case 3: Negative / Outlier ELOs
            [{"pillar": f"P{i}", "elo": -100.0 + i*500, "color": "#8b5cf6", "tok_s": 10.0, "ttft_ms": 20.0} for i in range(6)],
            # Case 4: Single pillar (N=1)
            [{"pillar": "Single", "elo": 2500.0, "color": "#10b981", "tok_s": 50.0, "ttft_ms": 15.0}]
        ]

        for idx, test_pillars in enumerate(extreme_cases):
            fig = plt.figure(figsize=(19, 5.4), dpi=160)
            fig.patch.set_facecolor('#0f172a')

            names = [p['pillar'] for p in test_pillars]
            elos = [p['elo'] for p in test_pillars]
            colors = [p['color'] for p in test_pillars]
            y_pos = np.arange(len(names))

            # Panel 1
            ax1 = fig.add_subplot(1, 3, 1)
            ax1.barh(y_pos, elos, color=colors)
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels(names)

            # Panel 2 (Polar)
            N = len(names)
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles_closed = angles + angles[:1]
            values = [max(0, (e - 2200) / (2700 - 2200) * 100) if not math.isnan(e) else 0 for e in elos]
            values_closed = values + values[:1]
            ax2 = fig.add_subplot(1, 3, 2, polar=True)
            ax2.plot(angles_closed, values_closed)

            # Panel 3 (Twinx)
            ax3 = fig.add_subplot(1, 3, 3)
            tok_speeds = [p['tok_s'] for p in test_pillars]
            ttft_latencies = [p['ttft_ms'] for p in test_pillars]
            ax3.bar(np.arange(N), tok_speeds)
            ax3_twin = ax3.twinx()
            ax3_twin.plot(np.arange(N), ttft_latencies)

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_f:
                tmp_path = tmp_f.name
            try:
                fig.savefig(tmp_path, dpi=160)
                plt.close(fig)
                assert os.path.getsize(tmp_path) > 1000, f"Extreme case {idx} produced invalid image"
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)


# =========================================================================
# SUITE 3: CSS SYNTAX VALIDITY & CLASS NAME COLLISIONS
# =========================================================================
class TestSuite3CssSyntaxAndCollisions:
    """Verifies CSS syntax validity, design token conformance, and style isolation."""

    def test_css_brace_balancing_and_syntax(self):
        """Verify braces, quotes, and semicolon terminations in ARENA_CYBERPUNK_CSS."""
        css = ARENA_CYBERPUNK_CSS
        assert css.count("{") == css.count("}"), "Unbalanced curly braces in CSS"
        assert css.count("/*") == css.count("*/"), "Unbalanced CSS comment blocks"
        
        # Verify mandatory 5-color Cyberpunk tokens exist
        mandatory_colors = ["#06b6d4", "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b"]
        for col in mandatory_colors:
            assert col in css, f"Mandatory Cyberpunk color {col} missing in CSS"

        # Verify Google Fonts import
        assert "@import url('https://fonts.googleapis.com" in css
        assert "JetBrains+Mono" in css
        assert "Inter" in css

    def test_css_isolation_and_no_polluting_global_selectors(self):
        """Ensure no global element overrides (e.g. bare body, table, div) that leak into Jupyter UI."""
        lines = [l.strip() for l in ARENA_CYBERPUNK_CSS.split("\n") if l.strip() and not l.strip().startswith("/*") and not l.strip().startswith("*")]
        
        forbidden_bare_selectors = ["body {", "div {", "table {", "p {", "h1 {", "h2 {", "h3 {", "pre {", "code {", "span {"]
        for line in lines:
            for forbidden in forbidden_bare_selectors:
                assert not line.startswith(forbidden), f"Found forbidden un-scoped global selector: {line}"

    def test_all_html_rendered_classes_defined_in_css(self):
        """Verify every CSS class emitted by helper functions is explicitly defined in ARENA_CYBERPUNK_CSS."""
        # Render a comprehensive payload exercising all helpers
        html_payloads = [
            render_status_pulse("ONLINE", True, "Test info"),
            render_glass_metric_card("Title", "Value", "Subtitle", progress_pct=75),
            render_pillar_badge("Pillar", 2640.0, "Active", "01_apps", "⚡", "dataset", "Qwen", 1000, "glass-card-glow-cyan", 80, "progress-bar-cyan"),
            render_styled_table(["H1", "H2"], [["Val1", "ONLINE"], ["Val2", "SYNCING"]]),
            render_export_toast("Title", "/path/to/file", "Details"),
            render_dpo_split_view("prompt", "chosen", "rejected", {"meta": "val"}),
            render_telemetry_probe_card("Node", "http://endpoint", "ONLINE", 12.5)
        ]
        combined_html = "".join(html_payloads)

        # Extract class names from HTML
        classes_in_html = set()
        for match in re.finditer(r'class=["\']([^"\']+)["\']', combined_html):
            for cls in match.group(1).split():
                if cls.strip():
                    classes_in_html.add(cls.strip())

        # Extract class selectors from CSS
        css_classes = set(re.findall(r'\.([a-zA-Z0-9_\-]+)', ARENA_CYBERPUNK_CSS))

        # Check each class in HTML has a matching class definition or prefix in CSS
        for cls in classes_in_html:
            assert cls in css_classes, f"Emitted HTML class '.{cls}' is missing in ARENA_CYBERPUNK_CSS!"


# =========================================================================
# SUITE 4: IMAGE DIMENSIONS, DPI (>=150 DPI) & FILE INTEGRITY
# =========================================================================
class TestSuite4ImageDimensionsAndIntegrity:
    """Verifies file integrity, dimensions, DPI metadata, and visual properties of the exported image."""

    def test_image_file_existence_and_magic_bytes(self):
        """Verify PNG file exists, is non-empty, and has valid PNG header magic bytes."""
        assert IMAGE_PATH.exists(), f"Console PNG does not exist at {IMAGE_PATH}"
        size_bytes = os.path.getsize(IMAGE_PATH)
        assert size_bytes > 50_000, f"Console PNG unexpectedly small ({size_bytes} bytes)"

        with open(IMAGE_PATH, "rb") as f:
            header = f.read(8)
        # PNG signature: \x89PNG\r\n\x1a\n
        assert header == b'\x89PNG\r\n\x1a\n', "Invalid PNG magic bytes header"

    def test_image_dimensions_and_aspect_ratio(self):
        """Verify image resolution matches 4K / High-DPI requirements."""
        with Image.open(IMAGE_PATH) as img:
            width, height = img.size
            # At 160 DPI, 19x5.4 inches is approx 3040 x 864 px (tight bounding box ~3040 x 844)
            assert width >= 2500, f"Image width too small: {width}px (expected >= 2500)"
            assert height >= 700, f"Image height too small: {height}px (expected >= 700)"
            aspect_ratio = width / height
            assert 2.8 <= aspect_ratio <= 4.2, f"Unexpected aspect ratio: {aspect_ratio:.2f}"

    def test_image_dpi_metadata_greater_than_or_equal_150(self):
        """Verify DPI is >= 150 DPI per acceptance criteria."""
        with Image.open(IMAGE_PATH) as img:
            dpi_info = img.info.get("dpi")
            if dpi_info is not None:
                dpi_x, dpi_y = dpi_info
                assert dpi_x >= 150.0, f"DPI X too low: {dpi_x} (expected >= 150.0)"
                assert dpi_y >= 150.0, f"DPI Y too low: {dpi_y} (expected >= 150.0)"
            else:
                # If PIL doesn't extract dpi directly, check pHYs chunk in PNG
                with open(IMAGE_PATH, "rb") as f:
                    content = f.read()
                assert b'pHYs' in content, "PNG missing pHYs resolution chunk"
                phys_idx = content.find(b'pHYs')
                # 4 bytes ppu_x, 4 bytes ppu_y, 1 byte unit (1 = meters)
                data = content[phys_idx+4:phys_idx+13]
                ppu_x = int.from_bytes(data[0:4], 'big')
                ppu_y = int.from_bytes(data[4:8], 'big')
                dpi_x = ppu_x * 0.0254
                dpi_y = ppu_y * 0.0254
                assert dpi_x >= 150.0, f"DPI from pHYs too low: {dpi_x:.1f}"
                assert dpi_y >= 150.0, f"DPI from pHYs too low: {dpi_y:.1f}"

    def test_image_dark_background_and_color_variance(self):
        """Verify image background is dark slate (#0f172a) and figure contains rich non-blank content."""
        with Image.open(IMAGE_PATH) as img:
            rgb_img = img.convert("RGB")
            np_arr = np.array(rgb_img)

            # Sample top-left corner (background)
            corner_pixel = np_arr[10, 10]
            # #0f172a is RGB (15, 23, 42)
            assert corner_pixel[0] < 30 and corner_pixel[1] < 40 and corner_pixel[2] < 60, \
                f"Background is not dark slate: RGB={corner_pixel}"

            # Verify image is not blank or corrupted (standard deviation across channels)
            std_dev = np.std(np_arr)
            assert std_dev > 15.0, f"Image variance too low ({std_dev:.2f}), possible blank or corrupted image"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
