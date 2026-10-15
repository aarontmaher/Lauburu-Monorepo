# -*- coding: utf-8 -*-
"""
================================================================================
Test Suite: Master Notebook Multi-View UI Engine, Port Matrix & Headless Safety
================================================================================
Validates:
1. Headless Safety: `matplotlib.use('Agg')` in Cell 1, non-blocking socket probes
2. Dual-Vault Parity: Byte-level structure parity between 01_apps and obsidian_vault
3. Metadata Integrity: Explicit "kernelspec" (python3) and language_info
4. 14-Port Matrix: Complete endpoint directory including Port 3000
5. Localhost URL Routing: All local host endpoints routed to 127.0.0.1 (resolving Errno 61)
6. Multi-View 2x2 Grid Engine: Layout modes (2x2, 1x2, 1x1), 4 Quad presets, 4 slot viewports
7. AST Compilation: Zero SyntaxErrors across all notebook code cells
8. Jupytext Markdown Sync: Synchronized Obsidian Vault markdown document
================================================================================
"""

import ast
import json
import os
import socket
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
APPS_NOTEBOOK = REPO_ROOT / "01_apps" / "notebooks" / "00_lauburu_global_master_project.ipynb"
OBSIDIAN_NOTEBOOK = REPO_ROOT / "obsidian_vault" / "notebooks" / "00_lauburu_global_master_project.ipynb"
OBSIDIAN_MARKDOWN = REPO_ROOT / "obsidian_vault" / "notebooks" / "00_lauburu_global_master_project.md"
GENERATOR_SCRIPT = REPO_ROOT / "01_apps" / "notebooks" / "generate_glassmorphic_master_studio.py"


@pytest.fixture(scope="session")
def apps_notebook_data():
    """Loads the 01_apps master notebook JSON."""
    assert APPS_NOTEBOOK.exists(), f"Missing apps notebook: {APPS_NOTEBOOK}"
    with open(APPS_NOTEBOOK, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def obsidian_notebook_data():
    """Loads the obsidian_vault master notebook JSON."""
    assert OBSIDIAN_NOTEBOOK.exists(), f"Missing obsidian notebook: {OBSIDIAN_NOTEBOOK}"
    with open(OBSIDIAN_NOTEBOOK, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. HEADLESS SAFETY & METADATA TESTS
# ==============================================================================

def test_headless_safety_matplotlib_agg(apps_notebook_data):
    """TC-1.1: Verify matplotlib.use('Agg') is enforced before pyplot import in Cell 1."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) >= 1, "Notebook must contain at least 1 code cell"
    cell_0_source = "".join(code_cells[0]["source"])

    assert "import matplotlib" in cell_0_source, "Cell 0 must import matplotlib"
    assert "matplotlib.use('Agg')" in cell_0_source or 'matplotlib.use("Agg")' in cell_0_source, (
        "matplotlib.use('Agg') must be explicitly called for headless safety"
    )

    # Verify use('Agg') appears before pyplot import
    agg_idx = cell_0_source.find("matplotlib.use('Agg')")
    if agg_idx == -1:
        agg_idx = cell_0_source.find('matplotlib.use("Agg")')
    plt_idx = cell_0_source.find("matplotlib.pyplot")
    assert agg_idx != -1 and plt_idx != -1, "Both matplotlib.use('Agg') and matplotlib.pyplot must exist"
    assert agg_idx < plt_idx, "matplotlib.use('Agg') must precede matplotlib.pyplot import"


def test_generator_script_headless_safety():
    """TC-1.2: Verify generator script defines matplotlib.use('Agg') in source."""
    assert GENERATOR_SCRIPT.exists(), f"Missing generator: {GENERATOR_SCRIPT}"
    content = GENERATOR_SCRIPT.read_text(encoding="utf-8")
    assert "matplotlib.use('Agg')" in content or 'matplotlib.use("Agg")' in content, (
        "Generator script must include headless matplotlib backend"
    )


def test_notebook_kernelspec_metadata(apps_notebook_data, obsidian_notebook_data):
    """TC-1.3: Verify explicit kernelspec is present in notebook metadata for papermill/nbconvert."""
    for name, nb in [("apps", apps_notebook_data), ("obsidian", obsidian_notebook_data)]:
        meta = nb.get("metadata", {})
        assert "kernelspec" in meta, f"{name} notebook metadata must contain 'kernelspec'"
        ks = meta["kernelspec"]
        assert ks.get("name") in ("lauburu-notebooks", "python3"), f"{name} kernelspec name must be valid"
        assert ks.get("language") == "python", f"{name} kernelspec language must be 'python'"


# ==============================================================================
# 2. DUAL-VAULT PARITY & JUPYTEXT SYNCHRONIZATION
# ==============================================================================

def test_dual_vault_cell_count_and_types_parity(apps_notebook_data, obsidian_notebook_data):
    """TC-2.1: Verify exact cell count and cell types match between 01_apps and obsidian_vault."""
    apps_cells = apps_notebook_data["cells"]
    obsidian_cells = obsidian_notebook_data["cells"]

    assert len(apps_cells) == len(obsidian_cells), (
        f"Expected cell count match between notebooks, got {len(apps_cells)} and {len(obsidian_cells)}"
    )
    assert len(apps_cells) >= 2, f"Notebook must contain at least 2 cells, got {len(apps_cells)}"

    for i, (ac, oc) in enumerate(zip(apps_cells, obsidian_cells)):
        assert ac["cell_type"] == oc["cell_type"], (
            f"Cell {i} type mismatch: {ac['cell_type']} vs {oc['cell_type']}"
        )
        assert "".join(ac["source"]).strip() == "".join(oc["source"]).strip(), (
            f"Cell {i} content mismatch between dual vaults"
        )


def test_obsidian_jupytext_markdown_exists():
    """TC-2.2: Verify obsidian markdown is generated and non-empty."""
    assert OBSIDIAN_MARKDOWN.exists(), f"Obsidian markdown sync missing: {OBSIDIAN_MARKDOWN}"
    md_content = OBSIDIAN_MARKDOWN.read_text(encoding="utf-8")
    assert len(md_content) > 1000, "Obsidian markdown file is too short / incomplete"
    assert "PORT_DIRECTORY" in md_content, "Obsidian markdown must contain PORT_DIRECTORY"
    assert "Zone 2 Endurance" in md_content or "Zone 2" in md_content, (
        "Obsidian markdown must mention Zone 2"
    )


# ==============================================================================
# 3. 14-PORT DIRECTORY & ROUTING INVARIANTS
# ==============================================================================

def test_port_directory_14_endpoints(apps_notebook_data):
    """TC-3.1: Verify PORT_DIRECTORY defines all 14 canonical mesh endpoints."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    expected_ports = [3000, 4000, 8081, 8082, 8083, 8084, 8088, 8888, 8889, 8890, 9000, 9333, 18802, 18805]
    for port in expected_ports:
        assert f':{port}' in cell_1_source or f'"port": {port}' in cell_1_source, (
            f"Port {port} must be present in PORT_DIRECTORY"
        )


def test_port_3000_integration(apps_notebook_data):
    """TC-3.2: Verify Port 3000 (Zone 2 Endurance & Web Portal Hub) is correctly configured."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    assert '"port": 3000' in cell_1_source, "Port 3000 must be defined in PORT_DIRECTORY"
    assert "http://127.0.0.1:3000" in cell_1_source, "Port 3000 URL must be http://127.0.0.1:3000"
    assert "Zone 2" in cell_1_source, "Port 3000 role/name must reference Zone 2"


def test_localhost_loopback_routing_no_tailscale_l1_mismatch(apps_notebook_data):
    """TC-3.3: Verify all L1 Mac Mini local services use loopback 127.0.0.1 (not 100.119.199.76)."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    # Local services that must use 127.0.0.1
    local_ports = [3000, 4000, 8081, 8082, 8083, 8084, 8088, 8888, 8890, 9000, 9333, 18802, 18805]
    for port in local_ports:
        assert f'"url": "http://100.119.199.76:{port}' not in cell_1_source, (
            f"Port {port} must not use L1 Tailscale IP 100.119.199.76 for iframe routing"
        )
        assert f'"http://127.0.0.1:{port}' in cell_1_source or f'"url": "http://127.0.0.1:{port}' in cell_1_source, (
            f"Port {port} must use http://127.0.0.1:{port} for host iframe routing"
        )

    # Remote services: Port 8889 on Layer 5 Air must use 100.93.158.96
    assert "http://100.93.158.96:8889/lab" in cell_1_source, "Port 8889 (Air) must point to 100.93.158.96:8889/lab"


# ==============================================================================
# 4. MULTI-VIEW 2X2 GRID ENGINE & PRESETS
# ==============================================================================

def test_multiview_layout_options(apps_notebook_data):
    """TC-4.1: Verify Multi-View engine supports 2x2, 1x2, and 1x1 layouts."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    assert "2x2" in cell_1_source, "Multi-View must support 2x2 Quad Grid"
    assert "1x2" in cell_1_source, "Multi-View must support 1x2 Dual Split"
    assert "1x1" in cell_1_source, "Multi-View must support 1x1 Solo Focus"
    assert "btn_2x2" in cell_1_source or "layout_mode" in cell_1_source, "Layout mode buttons or handler must be defined"


def test_multiview_preset_configurations(apps_notebook_data):
    """TC-4.2: Verify the 4 canonical Quad presets are defined."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    expected_presets = [
        "🚀 Full Stack Quad",
        "🧠 AI Cluster Quad",
        "🖥️ Ops Grid Quad",
        "💾 Storage Quad"
    ]
    for preset in expected_presets:
        assert preset in cell_1_source, f"Preset '{preset}' must be defined in PRESET_CONFIGS"


def test_multiview_slot_controls_and_direct_links(apps_notebook_data):
    """TC-4.3: Verify 4 independent slots with dropdowns, open links, and status pills."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    assert "target=\"_blank\"" in cell_1_source or 'target="_blank"' in cell_1_source, (
        "Each slot must have direct open link with target='_blank'"
    )
    assert "↗ Open" in cell_1_source, "Direct open link label must include '↗ Open'"
    assert "LIVE" in cell_1_source and "STANDBY" in cell_1_source, (
        "Zero-mock socket status badges must be present"
    )
    assert "height_dropdown" in cell_1_source, "Height selector dropdown must be present"


def test_zero_mock_standby_cards(apps_notebook_data):
    """TC-4.4: Verify zero-mock glassmorphic standby card is rendered when port is offline."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    cell_1_source = "\n".join("".join(c.get("source", [])) for c in code_cells)

    assert "STATUS: STANDBY (Zero-Mock Verified)" in cell_1_source, (
        "Standby card must state zero-mock verification status"
    )
    assert "probe_port_quick" in cell_1_source, "Socket prober must be implemented"


# ==============================================================================
# 5. AST SYNTAX & CODE CELL COMPILATION
# ==============================================================================

def test_all_notebook_code_cells_compile_cleanly(apps_notebook_data):
    """TC-5.1: Verify all code cells in the master notebook compile cleanly without SyntaxError."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) >= 1, f"Expected at least 1 code cell, got {len(code_cells)}"

    for idx, cell in enumerate(code_cells):
        source = "".join(cell["source"])
        try:
            tree = ast.parse(source)
            compiled = compile(source, f"<notebook_cell_{idx}>", "exec")
            assert compiled is not None
        except SyntaxError as e:
            pytest.fail(f"SyntaxError in code cell {idx}: {e}")


def test_generator_script_compiles_cleanly():
    """TC-5.2: Verify the generator script itself compiles cleanly."""
    source = GENERATOR_SCRIPT.read_text(encoding="utf-8")
    try:
        compiled = compile(source, str(GENERATOR_SCRIPT), "exec")
        assert compiled is not None
    except SyntaxError as e:
        pytest.fail(f"SyntaxError in generator script: {e}")


# ==============================================================================
# 6. HEADLESS EXECUTION VERIFICATION
# ==============================================================================

def test_headless_execution_via_execute_preprocessor():
    """TC-6.1: Verify master notebook executes 100% headlessly with 0 errors via ExecutePreprocessor."""
    import subprocess
    import shutil

    uv_python = "/Users/aaron/.local/share/uv/tools/jupyterlab/bin/python"
    if not os.path.exists(uv_python):
        uv_python = shutil.which("python3")

    script = """
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

with open('01_apps/notebooks/00_lauburu_global_master_project.ipynb') as f:
    nb = nbformat.read(f, as_version=4)

ep = ExecutePreprocessor(timeout=60, kernel_name='python3')
ep.preprocess(nb, {'metadata': {'path': '01_apps/notebooks'}})

# Verify every code cell executed without error output
for idx, cell in enumerate(nb.cells):
    if cell.cell_type == 'code':
        for out in cell.get('outputs', []):
            if out.get('output_type') == 'error':
                raise RuntimeError(f"Cell {idx} raised execution error: {out.get('ename')}: {out.get('evalue')}")

with open('/tmp/pytest_headless_preprocessed.ipynb', 'w') as f:
    nbformat.write(nb, f)

print('EXEC_SUCCESS_TABBED_CONSOLE')
"""
    res = subprocess.run(
        [uv_python, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60
    )
    assert res.returncode == 0, f"ExecutePreprocessor failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert "EXEC_SUCCESS_TABBED_CONSOLE" in res.stdout, "ExecutePreprocessor must print EXEC_SUCCESS_TABBED_CONSOLE"


def test_headless_execution_produces_valid_notebook(apps_notebook_data):
    """TC-6.2: Verify preprocessed output notebook exists and contains valid outputs."""
    out_path = Path("/tmp/pytest_headless_preprocessed.ipynb")
    assert out_path.exists(), "Preprocessed output notebook must exist"
    with open(out_path, "r", encoding="utf-8") as f:
        nb_out = json.load(f)
    assert len(nb_out.get("cells", [])) == len(apps_notebook_data["cells"]), "Preprocessed notebook cell count must match"
    code_cells = [c for c in nb_out["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) >= 1, "Preprocessed notebook must contain code cells"
    for idx, cell in enumerate(code_cells):
        for out in cell.get("outputs", []):
            assert out.get("output_type") != "error", f"Code cell {idx} produced error output"


# ==============================================================================
# 7. CYBER IDE, TUI & SUB-COMPONENTS VERIFICATION
# ==============================================================================

def test_height_dropdown_observer_registered(apps_notebook_data):
    """TC-7.1: Verify height_dropdown registers observe handler for dynamic height resizing."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    source = "\n".join("".join(c.get("source", [])) for c in code_cells)
    assert "height_dropdown.observe" in source, "height_dropdown must have an observer registered"


def test_cyber_ide_controls_and_safety(apps_notebook_data):
    """TC-7.2: Verify Cyber IDE contains path traversal guard and dedicated directory navigation."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    source = "\n".join("".join(c.get("source", [])) for c in code_cells)
    assert "open_dir_btn" in source, "Cyber IDE must have open_dir_btn"
    assert "Path traversal forbidden" in source, "Cyber IDE must prevent path traversal"
    assert "IsADirectoryError" in source, "Cyber IDE must prevent overwriting directories"


def test_tui_endpoints_routing(apps_notebook_data):
    """TC-7.3: Verify TUI tab provides authentic Port 8088 routes."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    source = "\n".join("".join(c.get("source", [])) for c in code_cells)
    for route in ["/canonical", "/readiness", "/grappling", "/arena", "/leaderboard", "/smolagents", "/store"]:
        assert route in source, f"TUI tab must route to {route}"


def test_bjj_opml_options_include_canonical_and_extended(apps_notebook_data):
    """TC-7.4: Verify BJJ tab supports canonical 955-node and extended OPML graphs."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    source = "\n".join("".join(c.get("source", [])) for c in code_cells)
    assert "mindomo_final copy.opml" in source, "BJJ tab must include canonical 955-node OPML"
    assert "grappling.opml" in source, "BJJ tab must include extended 3,044-node OPML"


def test_corewar_pmars_native_discovery(apps_notebook_data):
    """TC-7.5: Verify CoreWar tab includes dynamic warrior discovery and pmars runner."""
    code_cells = [c for c in apps_notebook_data["cells"] if c["cell_type"] == "code"]
    source = "\n".join("".join(c.get("source", [])) for c in code_cells)
    assert "warriors" in source, "CoreWar tab must check warriors directory"
    assert "codeclash_corewar_runner.py" in source, "CoreWar tab must reference codeclash_corewar_runner.py"


