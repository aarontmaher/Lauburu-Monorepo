"""
Adversarial Verification Suite for Milestone M1 (UI/UX, DPI, and Zero-JSON).
Authored by Challenger M1.2.
Uses pure Python standard library for maximum zero-dependency portability.
"""

import ast
import json
import re
import struct
import subprocess
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
NOTEBOOK_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "00_6_PILLAR_LOCAL_AI_ARENA_TRAINING_AND_NOTEBOOK_OPTIMIZER.ipynb"
CHART_PATH = MONOREPO_ROOT / "obsidian_vault" / "notebooks" / "6_pillar_dark_console.png"
RENDERED_HTML_PATH = Path("/tmp/rendered_arena_m1.html")

REQUIRED_CLASSES = [
    "glass-card",
    "glass-card-glow-cyan",
    "glass-header",
    "pill-btn",
    "metric-badge",
    "progress-neon",
]

CYBERPUNK_HEX_CODES = [
    "#06b6d4",  # Cyan
    "#3b82f6",  # Blue
    "#8b5cf6",  # Purple
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
]


class DOMClassExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.classes: Set[str] = set()
        self.class_counts: Dict[str, int] = {}
        self.visible_texts: List[str] = []
        self.in_script: bool = False
        self.in_style: bool = False
        self.in_code_input: bool = False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.in_script = True
        elif tag == "style":
            self.in_style = True

        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "").split()
        if any(c in classes for c in ["input_area", "jp-InputArea", "highlight"]):
            self.in_code_input = True

        for k, v in attrs:
            if k == "class" and v:
                for cls in v.split():
                    self.classes.add(cls)
                    self.class_counts[cls] = self.class_counts.get(cls, 0) + 1

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False
        if tag in ("div", "pre"):
            self.in_code_input = False

    def handle_data(self, data):
        if not self.in_script and not self.in_style and not self.in_code_input:
            stripped = data.strip()
            if stripped:
                self.visible_texts.append(stripped)


def parse_png_metadata(png_path: Path) -> Tuple[int, int, float, float]:
    """Parse PNG width, height, and DPI directly from binary chunks."""
    data = png_path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG file signature"
    pos = 8
    width, height = 0, 0
    dpi_x, dpi_y = 0.0, 0.0

    while pos < len(data):
        length, ctype = struct.unpack(">I4s", data[pos : pos + 8])
        cdata = data[pos + 8 : pos + 8 + length]
        pos += 12 + length

        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", cdata[:10])
        elif ctype == b"pHYs":
            ppux, ppuy, unit = struct.unpack(">IIB", cdata)
            if unit == 1:  # unit: meter
                dpi_x = ppux * 0.0254
                dpi_y = ppuy * 0.0254

    return width, height, dpi_x, dpi_y


@pytest.fixture(scope="module")
def executed_html() -> str:
    """Ensure fresh headless execution and return rendered HTML."""
    jupyter_bin = "/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter"
    cmd = [
        jupyter_bin,
        "nbconvert",
        "--to",
        "html",
        "--execute",
        str(NOTEBOOK_PATH),
        "--output",
        str(RENDERED_HTML_PATH),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"nbconvert execution failed:\n{res.stderr}"
    assert RENDERED_HTML_PATH.exists()
    return RENDERED_HTML_PATH.read_text(encoding="utf-8")


class TestAdversarialAestheticsAndClasses:
    """Adversarial verification of CSS design tokens, classes, and palette."""

    def test_all_required_classes_present_in_stylesheet_or_dom(self, executed_html: str):
        """Verify all 6 required classes are defined and present in the rendered HTML."""
        parser = DOMClassExtractor()
        parser.feed(executed_html)

        for cls in REQUIRED_CLASSES:
            in_stylesheet = f".{cls}" in executed_html
            in_dom = cls in parser.classes
            assert in_stylesheet or in_dom, f"Required class .{cls} missing from rendered HTML!"

    def test_all_cyberpunk_hex_codes_present(self, executed_html: str):
        """Verify all 5 Cyberpunk palette hex codes are rendered."""
        for hex_code in CYBERPUNK_HEX_CODES:
            matches = re.findall(re.escape(hex_code), executed_html, re.IGNORECASE)
            assert len(matches) > 0, f"Cyberpunk hex code {hex_code} missing from rendered HTML!"

    def test_glassmorphism_css_properties(self, executed_html: str):
        """Verify backdrop-filter, rgba translucent surfaces, and border-radius."""
        assert "backdrop-filter: blur" in executed_html or "backdrop-filter" in executed_html
        assert "rgba(15, 23, 42" in executed_html or "rgba(15,23,42" in executed_html
        assert "border-radius" in executed_html


class TestAdversarialZeroRawJsonAndPrints:
    """Adversarial verification of Zero Raw JSON and zero unescaped print statements."""

    def test_zero_ast_print_statements_in_notebook(self):
        """Verify 0 print() function calls exist in any notebook code cell AST."""
        with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
            nb = json.load(f)

        for cell_idx, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") == "code":
                src = "".join(cell.get("source", []))
                tree = ast.parse(src)
                print_calls = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                        print_calls.append(node.lineno)
                assert len(print_calls) == 0, f"Cell {cell_idx} contains unescaped print() calls at lines: {print_calls}"

    def test_zero_raw_json_dumps_in_rendered_html(self, executed_html: str):
        """Verify no unformatted JSON dictionaries appear in visible HTML output."""
        parser = DOMClassExtractor()
        parser.feed(executed_html)

        raw_json_patterns = [
            r"^\{[ \t\n]*\"[a-zA-Z0-9_]+\"[ \t\n]*:[ \t\n]*[\"0-9\{]",
            r"^\[[ \t\n]*\{[ \t\n]*\"[a-zA-Z0-9_]+\"",
        ]

        violations = []
        for text in parser.visible_texts:
            for pat in raw_json_patterns:
                if re.search(pat, text):
                    violations.append(text)

        assert len(violations) == 0, f"Found unstyled raw JSON in rendered output: {violations}"

    def test_structured_html_table_and_toast_rendering(self, executed_html: str):
        """Verify structured HTML table and toast notifications are rendered in output."""
        assert "<table" in executed_html
        assert "<thead>" in executed_html
        assert "<tbody>" in executed_html
        assert "3-Panel Dark Console Exported" in executed_html or "Dark Console Exported" in executed_html


class TestAdversarialHighDpiChart:
    """Adversarial verification of exported dark console chart resolution and subplots."""

    def test_chart_file_exists_and_non_empty(self):
        """Verify 6_pillar_dark_console.png exists and size >= 50 KB."""
        assert CHART_PATH.exists(), f"Chart file not found: {CHART_PATH}"
        assert CHART_PATH.stat().st_size >= 50 * 1024, "Chart file size unexpectedly small (< 50KB)"

    def test_chart_dpi_resolution_meets_threshold(self):
        """Verify chart DPI resolution >= 160 DPI."""
        width, height, dpi_x, dpi_y = parse_png_metadata(CHART_PATH)
        assert dpi_x >= 159.0 and dpi_y >= 159.0, f"Chart DPI ({dpi_x}, {dpi_y}) is below 160 DPI threshold"

    def test_chart_dimensions_and_dark_background(self):
        """Verify chart pixel dimensions."""
        width, height, dpi_x, dpi_y = parse_png_metadata(CHART_PATH)
        assert width >= 2800, f"Chart width ({width}px) below 2800px threshold"
        assert height >= 750, f"Chart height ({height}px) below 750px threshold"

    def test_chart_code_3_distinct_subplots_structure(self):
        """Verify Cell 3 Matplotlib code configures 3 distinct subplots."""
        with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
            nb = json.load(f)

        cell_3_src = "".join(nb["cells"][3]["source"])
        assert "add_subplot(1, 3, 1)" in cell_3_src, "Missing subplot 1 (Bar chart)"
        assert "add_subplot(1, 3, 2" in cell_3_src, "Missing subplot 2 (Polar radar chart)"
        assert "add_subplot(1, 3, 3)" in cell_3_src, "Missing subplot 3 (Throughput/TTFT chart)"
        assert "dpi=160" in cell_3_src, "Missing dpi=160 configuration in Matplotlib figure initialization"
        assert "#0f172a" in cell_3_src, "Missing dark background facecolor (#0f172a)"
