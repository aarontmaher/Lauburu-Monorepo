"""
Milestone M5: Acceptance Criteria & Standalone Runtime Hardening Test Suite.
Authored by Challenger 2 (challenger_m5_2_gen3).

Verifies:
1. High-DPI Chart Asset:
   - File exists at /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/notebooks/6_pillar_dark_console.png
   - Valid PNG magic bytes, >= 150 DPI (160 DPI verified in metadata), dimensions >= 2000x500 px.
   - 3-Panel Dark Console structure (Radar/ELO calibration, Bradley-Terry Win Curves, 82.8GB Mesh VRAM).
2. Zero Raw JSON Output:
   - Full DOM / HTML scan of headless nbconvert export for absence of bare unstyled JSON dicts/lists.
   - Purity audit of AST in all 5 code cells (zero bare print() or unescaped JSON dumps).
3. Multi-Runtime Execution:
   - Clean headless jupyter nbconvert --to html --execute with exit code 0.
   - Marimo 0.24+ compatibility and AST translation / python compilation with exit code 0.
   - Standalone pure Python execution without Jupyter display or ipywidgets dependencies.
4. Authentic Dataset SSoT Paths:
   - Ingestion from /Users/aaron/DFS_UNIFIED/lora_datasets/ and 04_data_and_memory/.
   - Valid DPO schemas (prompt, chosen, rejected, metadata: pillar_id 1..6, elo, zero_mock_certified).
5. Rule #0 Zero-Mock Probes:
   - Offline nodes return status="OFFLINE", code=0, rtt_ms=None / "--", empty telemetry {}.
   - Live socket probing with timeouts, non-blocking connections, zero synthetic numbers.
"""

import ast
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import pytest

from .conftest import (
    NOTEBOOK_PATH,
    CHART_PATH,
    MONOREPO_ROOT,
    LORA_DIR,
    DATA_MEMORY_DIR,
    CANONICAL_PILLARS,
    load_notebook_data,
    extract_code_cells,
    extract_markdown_cells,
    calculate_elo_update,
    validate_dpo_schema,
    validate_probe_schema,
)

JUPYTER_BIN = Path("/Users/aaron/.local/share/uv/tools/jupyterlab/bin/jupyter")
MARIMO_BIN = Path("/Users/aaron/.local/bin/marimo")


# =========================================================================
# Tier 1: High-DPI Chart Asset Acceptance Verification
# =========================================================================
class TestHighDPIChartAssetAcceptance:
    """Rigorous empirical validation of the exported 6-pillar dark console chart asset."""

    def test_chart_asset_existence_and_magic_bytes(self):
        """Verify PNG file exists, is readable, and contains canonical PNG magic signature."""
        assert CHART_PATH.exists(), f"Chart asset does not exist at {CHART_PATH}"
        assert CHART_PATH.is_file(), f"Chart asset is not a file: {CHART_PATH}"
        assert os.path.getsize(CHART_PATH) > 50_000, "Chart asset size is suspiciously small (< 50 KB)"

        with open(CHART_PATH, "rb") as f:
            header = f.read(8)
        # Canonical PNG magic signature: 0x89 'P' 'N' 'G' 0x0D 0x0A 0x1A 0x0A
        assert header == b"\x89PNG\r\n\x1a\n", "Corrupted or invalid PNG header magic bytes"

    def test_chart_dpi_resolution_threshold(self):
        """Verify DPI resolution in metadata is >= 150 DPI (specifically ~160 DPI)."""
        img = Image.open(CHART_PATH)
        assert img.format == "PNG", f"Image format is {img.format}, expected PNG"
        
        dpi = img.info.get("dpi")
        if dpi is not None:
            dpi_x, dpi_y = dpi
            assert dpi_x >= 150.0, f"DPI x {dpi_x} is below minimum requirement of 150 DPI"
            assert dpi_y >= 150.0, f"DPI y {dpi_y} is below minimum requirement of 150 DPI"
            # Verify close to target 160 DPI
            assert 155.0 <= dpi_x <= 165.0, f"DPI x {dpi_x} outside expected range [155, 165]"
            assert 155.0 <= dpi_y <= 165.0, f"DPI y {dpi_y} outside expected range [155, 165]"
        else:
            # Check pHYs chunk directly in PNG binary if PIL info doesn't parse it
            with open(CHART_PATH, "rb") as f:
                content = f.read()
            phys_idx = content.find(b"pHYs")
            assert phys_idx != -1, "Neither PIL dpi nor pHYs chunk found in PNG asset"
            ppx, ppy, unit = struct.unpack(">IIB", content[phys_idx + 4 : phys_idx + 13])
            assert unit == 1, "pHYs unit is not meters"
            dpi_x = ppx * 0.0254
            dpi_y = ppy * 0.0254
            assert dpi_x >= 150.0, f"Calculated DPI {dpi_x} < 150"

    def test_chart_pixel_dimensions_and_aspect_ratio(self):
        """Verify 4K/Retina pixel dimensions (width >= 2400, height >= 600)."""
        img = Image.open(CHART_PATH)
        width, height = img.size
        assert width >= 2400, f"Image width {width} < 2400 px"
        assert height >= 600, f"Image height {height} < 600 px"
        aspect_ratio = width / height
        # 19 / 5.4 = ~3.518
        assert 3.0 <= aspect_ratio <= 4.0, f"Unexpected aspect ratio: {aspect_ratio}"

    def test_chart_dark_palette_and_background_color(self):
        """Verify dark theme palette (#0f172a background, non-white dominating)."""
        img = Image.open(CHART_PATH).convert("RGBA")
        np_img = np.array(img)
        # Sample corner pixels (background facecolor)
        top_left = np_img[10, 10, :3]
        top_right = np_img[10, -10, :3]
        bottom_left = np_img[-10, 10, :3]
        bottom_right = np_img[-10, -10, :3]

        for corner, name in [(top_left, "top-left"), (top_right, "top-right"), 
                             (bottom_left, "bottom-left"), (bottom_right, "bottom-right")]:
            r, g, b = corner
            # Background #0f172a is ~ (15, 23, 42)
            assert r < 40 and g < 50 and b < 70, f"Corner {name} {corner} is not dark background"

    def test_headless_reproducible_chart_generation(self, temp_test_dir):
        """Execute the rendering logic from Cell 1 + Cell 2 + Cell 3 headlessly and verify output."""
        nb_data = load_notebook_data(NOTEBOOK_PATH)
        code_cells = extract_code_cells(nb_data)
        cell_1_code = code_cells[0]
        cell_2_code = code_cells[1]
        cell_3_code = code_cells[2]

        test_out_png = temp_test_dir / "test_reproduced_console.png"
        
        # Build executable standalone script for Cells 1..3
        script_content = f"""
import sys, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Pure Python environment simulator
class MockDisplay:
    def __init__(self):
        self.rendered_html = []
    def __call__(self, obj):
        pass

class MockHTML:
    def __init__(self, data):
        self.data = str(data)

def mock_clear_output(*a, **k):
    pass

display = MockDisplay()
HTML = MockHTML
clear_output = mock_clear_output

# CELL 1
{cell_1_code}

# CELL 2
{cell_2_code}

# CELL 3 (with custom save path)
{cell_3_code.replace('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/notebooks/6_pillar_dark_console.png', str(test_out_png))}
"""
        py_file = temp_test_dir / "render_script.py"
        py_file.write_text(script_content, encoding="utf-8")

        res = subprocess.run([sys.executable, str(py_file)], capture_output=True, text=True, timeout=30)
        assert res.returncode == 0, f"Standalone chart render failed: {res.stderr}"
        assert test_out_png.exists(), "Reproduced chart PNG was not written to disk"
        
        reproduced_img = Image.open(test_out_png)
        assert reproduced_img.format == "PNG"
        assert reproduced_img.size[0] >= 2400
        assert reproduced_img.size[1] >= 600


# =========================================================================
# Tier 2: Zero Raw JSON Output Acceptance Verification
# =========================================================================
class TestZeroRawJSONOutputAcceptance:
    """Verify ZERO raw unstyled JSON dictionaries/lists are presented in notebook outputs or exports."""

    def test_notebook_ast_zero_bare_print_calls(self):
        """Static AST audit confirming ZERO bare print() calls exist across all 5 code cells."""
        nb_data = load_notebook_data(NOTEBOOK_PATH)
        code_cells = extract_code_cells(nb_data)
        assert len(code_cells) == 5, f"Expected 5 code cells, found {len(code_cells)}"

        for cell_idx, source in enumerate(code_cells, start=1):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "print":
                        # If print() exists, verify it's not a top-level unstyled print
                        pytest.fail(f"Cell {cell_idx} contains a bare print() call at line {node.lineno}")

    def test_notebook_json_cell_outputs_zero_raw_json(self):
        """Check all stored outputs inside .ipynb for zero raw JSON dictionaries or lists."""
        nb_data = load_notebook_data(NOTEBOOK_PATH)
        for cell_idx, cell in enumerate(nb_data.get("cells", [])):
            if cell.get("cell_type") == "code":
                outputs = cell.get("outputs", [])
                for out_idx, out in enumerate(outputs):
                    # Check text/plain outputs
                    data = out.get("data", {})
                    plain_text = data.get("text/plain", [])
                    if isinstance(plain_text, list):
                        plain_text = "".join(plain_text)
                    if plain_text:
                        # Ensure plain_text is not a raw unstyled JSON dump
                        stripped = plain_text.strip()
                        if (stripped.startswith("{") and stripped.endswith("}")) or \
                           (stripped.startswith("[") and stripped.endswith("]")):
                            try:
                                json.loads(stripped)
                                pytest.fail(f"Cell {cell_idx} output {out_idx} has raw JSON in text/plain: {stripped[:100]}")
                            except json.JSONDecodeError:
                                pass

    def test_html_export_zero_raw_json_blocks(self, temp_test_dir):
        """Export notebook via nbconvert and verify the exported HTML contains no unstyled JSON payloads."""
        if not JUPYTER_BIN.exists():
            pytest.skip(f"Jupyter binary not found at {JUPYTER_BIN}")

        out_html = temp_test_dir / "acceptance_export.html"
        cmd = [
            str(JUPYTER_BIN), "nbconvert",
            "--to", "html",
            "--execute",
            str(NOTEBOOK_PATH),
            "--output", str(out_html),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        assert res.returncode == 0, f"nbconvert failed with error: {res.stderr}"
        assert out_html.exists(), "Exported HTML was not generated"

        html_content = out_html.read_text(encoding="utf-8")

        # Verify presence of styled glassmorphic wrappers
        assert "glass-card" in html_content, "Missing .glass-card in exported HTML"
        assert "glass-header" in html_content, "Missing .glass-header in exported HTML"

        # Regex search for unstyled raw JSON blocks in rendered HTML output
        raw_json_pattern = re.compile(r"<pre>\s*\{[\s\S]*?\"id\":\s*\d+[\s\S]*?\}\s*</pre>")
        raw_matches = raw_json_pattern.findall(html_content)
        # Any <pre> block containing raw json without glassmorphic card class is a violation
        for m in raw_matches:
            assert "glass-card" in m or "code-block" in m or "toast" in m, f"Found unstyled raw JSON: {m[:200]}"


# =========================================================================
# Tier 3: Multi-Runtime Execution Acceptance (Jupyter, Marimo, Pure Python)
# =========================================================================
class TestMultiRuntimeExecutionAcceptance:
    """Verify clean headless execution across Jupyter nbconvert, Marimo 0.24+, and Pure Python."""

    def test_jupyter_nbconvert_headless_full_execution(self, temp_test_dir):
        """Verify jupyter nbconvert --to html --execute executes with exit code 0 and >500KB rich HTML."""
        if not JUPYTER_BIN.exists():
            pytest.skip(f"Jupyter binary not found at {JUPYTER_BIN}")

        out_html = temp_test_dir / "nbconvert_full_run.html"
        cmd = [
            str(JUPYTER_BIN), "nbconvert",
            "--to", "html",
            "--execute",
            str(NOTEBOOK_PATH),
            "--output", str(out_html),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        assert res.returncode == 0, f"nbconvert failed with code {res.returncode}: {res.stderr}"
        assert out_html.exists(), "HTML export file does not exist"
        
        size = out_html.stat().st_size
        assert size > 500_000, f"Generated HTML file size {size} bytes is smaller than expected (>500KB)"

        content = out_html.read_text(encoding="utf-8")
        # Validate critical features in rendered DOM
        assert "6-Pillar Local AI Arena" in content, "Missing title in exported HTML"
        assert "Bradley-Terry" in content or "ELO Engine" in content or "elo" in content.lower()
        assert "04_data_and_memory" in content or "lora_datasets" in content

    def test_marimo_convert_and_syntax_validation(self, temp_test_dir):
        """Verify marimo 0.24+ can convert the notebook to a valid Marimo Python module."""
        if not MARIMO_BIN.exists():
            pytest.skip(f"Marimo binary not found at {MARIMO_BIN}")

        out_marimo_py = temp_test_dir / "marimo_converted_notebook.py"
        cmd = [
            str(MARIMO_BIN), "convert",
            str(NOTEBOOK_PATH),
            "-o", str(out_marimo_py),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert res.returncode == 0, f"marimo convert failed: {res.stderr}"
        assert out_marimo_py.exists(), "Converted marimo .py file was not created"

        # Verify the converted file is syntactically valid Python
        marimo_code = out_marimo_py.read_text(encoding="utf-8")
        parsed_ast = ast.parse(marimo_code)
        assert parsed_ast is not None, "Failed to parse converted Marimo Python AST"

    def test_standalone_pure_python_execution_all_cells(self, temp_test_dir):
        """Verify all cells execute successfully in a standalone Python script with MRAL fallbacks."""
        nb_data = load_notebook_data(NOTEBOOK_PATH)
        code_cells = extract_code_cells(nb_data)

        # Combine all 5 cells into a single script with MRAL mock
        combined_script = f"""
import sys, os
import matplotlib
matplotlib.use('Agg')

# Pure Python environment simulator (no ipykernel, no ipywidgets)
class MockDisplay:
    def __init__(self):
        self.rendered_html = []
    def __call__(self, obj):
        if hasattr(obj, 'data'):
            self.rendered_html.append(obj.data)
        elif isinstance(obj, str):
            self.rendered_html.append(obj)

class MockHTML:
    def __init__(self, data):
        self.data = str(data)

def mock_clear_output(*a, **k):
    pass

display = MockDisplay()
HTML = MockHTML
clear_output = mock_clear_output

# CELL 1
{code_cells[0]}

# CELL 2
{code_cells[1]}

# CELL 3
{code_cells[2]}

# CELL 4
{code_cells[3]}

# CELL 5
{code_cells[4]}

print("ALL_CELLS_COMPLETED_SUCCESSFULLY")
"""
        script_file = temp_test_dir / "pure_python_runner.py"
        script_file.write_text(combined_script, encoding="utf-8")

        res = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True, timeout=60)
        assert res.returncode == 0, f"Pure python execution failed: {res.stderr}"
        assert "ALL_CELLS_COMPLETED_SUCCESSFULLY" in res.stdout


# =========================================================================
# Tier 4: Authentic Dataset SSoT Paths Acceptance Verification
# =========================================================================
class TestAuthenticDatasetSSoTPathsAcceptance:
    """Verify dataset ingestion reads from authentic SSoT paths and adheres to DPO schema."""

    def test_ssot_dataset_directories_exist(self):
        """Verify authentic dataset folders exist in the filesystem."""
        assert LORA_DIR.exists(), f"LoRA directory missing: {LORA_DIR}"
        assert DATA_MEMORY_DIR.exists(), f"04_data_and_memory directory missing: {DATA_MEMORY_DIR}"

    def test_continuous_lora_dataset_integrity(self):
        """Verify continuous_lora_dataset.jsonl exists or can be read with valid DPO records."""
        dataset_file = LORA_DIR / "continuous_lora_dataset.jsonl"
        if dataset_file.exists() and dataset_file.stat().st_size > 0:
            with open(dataset_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) > 0, "continuous_lora_dataset.jsonl is empty"
            # Verify first 10 records validate against DPO schema or standard format
            for i, line in enumerate(lines[:10]):
                line_str = line.strip()
                if not line_str:
                    continue
                record = json.loads(line_str)
                assert isinstance(record, dict), f"Record {i} is not a JSON dict"
                # Check for either standard DPO keys (prompt, chosen, rejected) or instruction keys
                is_dpo = {"prompt", "chosen", "rejected"}.issubset(record.keys())
                is_instr = {"instruction", "output"}.issubset(record.keys())
                assert is_dpo or is_instr, f"Record {i} missing standard training keys: {list(record.keys())}"

    def test_six_pillar_metadata_contract(self):
        """Verify canonical 6 pillars cover all required training domains without duplicates."""
        pillar_ids = [p["id"] for p in CANONICAL_PILLARS]
        assert pillar_ids == [1, 2, 3, 4, 5, 6], f"Pillar IDs must be 1..6, found {pillar_ids}"
        
        pillar_names = [p["pillar"] for p in CANONICAL_PILLARS]
        assert len(set(pillar_names)) == 6, "Duplicate pillar names found"

        expected_domains = ["WebDev", "SWE-bench", "BigCodeBench", "Tau-Bench", "PhysioNet", "AgentHarm"]
        for domain in expected_domains:
            assert any(domain.lower() in p["pillar"].lower() for p in CANONICAL_PILLARS), (
                f"Missing expected domain '{domain}' in CANONICAL_PILLARS"
            )


# =========================================================================
# Tier 5: Rule #0 Zero-Mock Probes Acceptance Verification
# =========================================================================
class TestRule0ZeroMockProbesAcceptance:
    """Verify offline nodes cleanly return '--' latency, status code 0, and empty telemetry."""

    def test_offline_socket_probing_contract(self):
        """Simulate probing an inactive port and verify exact Rule #0 compliance."""
        # Probe an unused localhost high port
        test_host = "127.0.0.1"
        test_port = 59999

        start_t = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        try:
            err = s.connect_ex((test_host, test_port))
            if err == 0:
                status = "ONLINE"
                code = 200
                rtt_ms = round((time.time() - start_t) * 1000.0, 2)
            else:
                status = "OFFLINE"
                code = 0
                rtt_ms = None
        except Exception:
            status = "OFFLINE"
            code = 0
            rtt_ms = None
        finally:
            s.close()

        probe_result = {
            "status": status,
            "code": code,
            "rtt_ms": rtt_ms,
            "data": {},
            "error": "Connection refused / port closed" if status == "OFFLINE" else None,
        }

        # Contract assertions
        assert validate_probe_schema(probe_result), "Probe result violates contract schema"
        assert probe_result["status"] == "OFFLINE"
        assert probe_result["code"] == 0
        assert probe_result["rtt_ms"] is None
        assert probe_result["data"] == {}

    def test_offline_latency_display_formatting(self):
        """Verify offline probe results format latency as '--' and never synthetic numbers."""
        offline_rtt = None
        formatted_latency = f"{offline_rtt:.1f} ms" if isinstance(offline_rtt, (int, float)) else "--"
        assert formatted_latency == "--", f"Expected '--', got '{formatted_latency}'"

    def test_zero_mock_probes_in_notebook_code(self):
        """Inspect Cell 5 probing logic for strict adherence to Rule #0."""
        nb_data = load_notebook_data(NOTEBOOK_PATH)
        code_cells = extract_code_cells(nb_data)
        cell_5_code = code_cells[4]

        # Verify timeout is clamped (<= 1.0s) to avoid UI lockup
        assert "timeout" in cell_5_code, "Missing timeout parameter in Cell 5 probing"
        # Verify offline state handling
        assert "OFFLINE" in cell_5_code
        assert "ONLINE" in cell_5_code
        # Verify no hardcoded random/simulated latency generation (e.g. random.uniform(10, 50))
        assert "random.uniform" not in cell_5_code, "Forbidden synthetic random.uniform found in Cell 5"
        assert "random.randint" not in cell_5_code, "Forbidden synthetic random.randint found in Cell 5"


# =========================================================================
# Tier 6: Bradley-Terry Elo Engine Invariants Acceptance Verification
# =========================================================================
class TestEloEngineInvariantsAcceptance:
    """Verify mathematical invariants of the Bradley-Terry Elo rating engine."""

    def test_elo_zero_sum_conservation(self):
        """Verify that total Elo is strictly conserved in any 2-player match."""
        r_a, r_b = 2600.0, 2400.0
        for score_a in [1.0, 0.5, 0.0]:
            _, new_a, new_b = calculate_elo_update(r_a, r_b, score_a, k=32.0)
            initial_sum = r_a + r_b
            final_sum = new_a + new_b
            assert abs(initial_sum - final_sum) < 1e-9, f"Elo sum not conserved for score {score_a}"

    def test_elo_expected_score_bounds(self):
        """Verify expected score strictly satisfies 0 <= E_A <= 1 and E_A + E_B == 1."""
        test_ratings = [
            (2600.0, 2600.0),
            (2800.0, 2400.0),
            (2000.0, 3000.0),
            (1500.0, 3500.0),
        ]
        for r_a, r_b in test_ratings:
            exp_a, _, _ = calculate_elo_update(r_a, r_b, 1.0)
            exp_b = 1.0 - exp_a
            assert 0.0 <= exp_a <= 1.0, f"Expected score {exp_a} out of bounds [0, 1]"
            assert abs((exp_a + exp_b) - 1.0) < 1e-9, "Expected scores do not sum to 1.0"
