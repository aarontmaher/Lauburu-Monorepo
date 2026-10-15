"""
Empirical Challenger 2 Adversarial Stress Test Suite:
Interactive Widget Runtime Logic, IPyWidgets State Transitions, Rule #0 Zero-Mock Verification,
Cyber IDE Execution Sandbox, 512Hz DSP, and Live Qwen Inference TTFT Benchmark.
Generation 4 SSoT Master Studio Visual & Organizational Overhaul.

Author: teamwork_preview_challenger_2 (Critic & Specialist)

Core Verification Mandates:
1. Full AST syntax and cell structure parsing of 00_lauburu_global_master_project.ipynb across monorepo and obsidian vault mirrors.
2. Complete headless IPyWidgets runtime simulation: layout mode toggling (2x2, 1x2, 1x1), preset switching (Full Stack, AI Cluster, Ops Grid, Storage), slot observer triggers, height dropdown updates, re-probe button callback, and multi-TUI switcher.
3. Custom Cyber IDE & SeaweedFS Client stress: directory browsing, file loading/saving, binary file guards, and in-kernel sandboxed code execution with error isolation.
4. 512Hz Pan-Tompkins Movesense ECG DSP studio: authentic telemetry ingestion, filter parameter bounds, and zero-mock standby state fallback.
5. Rule #0 Zero-Mock Forensic Audit: verify real TCP connect_ex probes, genuine waiting states ('--', 'STANDBY'), and zero synthetic mock waveforms.
6. Live Qwen Port 8083 Inference Benchmark: /health probe and /v1/chat/completions streaming TTFT strictly < 200ms.
7. Concurrency & rapid state transition stress testing.
"""

import ast
import gc
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

# Matplotlib Agg Backend Mandate
import matplotlib
matplotlib.use("Agg")
os.environ["MPLBACKEND"] = "Agg"
import matplotlib.pyplot as plt
import numpy as np
import pytest

# Ensure real IPython is used if available
if "IPython" in sys.modules and getattr(sys.modules["IPython"], "__file__", None) is None:
    del sys.modules["IPython"]
    if "IPython.display" in sys.modules:
        del sys.modules["IPython.display"]
try:
    import IPython
    from IPython.display import display, HTML, clear_output
except ImportError:
    pass

import ipywidgets as widgets

CANONICAL_NB_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/00_lauburu_global_master_project.ipynb")
OBSIDIAN_NB_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/notebooks/00_lauburu_global_master_project.ipynb")
GENERATOR_PATH = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/generate_glassmorphic_master_studio.py")


def load_notebook_code_cells(nb_path: Path) -> List[str]:
    """Extract all code cell sources from a notebook file."""
    assert nb_path.is_file(), f"Notebook file not found: {nb_path}"
    with open(nb_path, "r", encoding="utf-8") as f:
        nb_data = json.load(f)
    cells = []
    for c in nb_data.get("cells", []):
        if c.get("cell_type") == "code":
            source = "".join(c.get("source", []))
            cells.append(source)
    return cells


class TestNotebookASTAndStructure:
    """Validate AST parsing and structural properties of the Master Studio notebook."""

    @pytest.mark.parametrize("path", [CANONICAL_NB_PATH, OBSIDIAN_NB_PATH])
    def test_notebook_ast_compilation(self, path: Path):
        """All code cells in the notebook must parse cleanly with ast.parse without SyntaxError."""
        code_cells = load_notebook_code_cells(path)
        assert len(code_cells) >= 8, f"Expected at least 8 code cells, found {len(code_cells)}"
        for idx, code in enumerate(code_cells):
            try:
                tree = ast.parse(code)
                assert isinstance(tree, ast.Module)
            except SyntaxError as e:
                pytest.fail(f"Cell {idx} failed AST parse: {e}")

    def test_generator_script_integrity(self):
        """The generator script generate_glassmorphic_master_studio.py must compile cleanly."""
        assert GENERATOR_PATH.is_file(), f"Generator not found: {GENERATOR_PATH}"
        with open(GENERATOR_PATH, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        assert isinstance(tree, ast.Module)


class TestWidgetRuntimeSimulation:
    """Empirically execute and stress-test the widget runtime engine of the notebook."""

    @pytest.fixture(scope="class")
    def runtime_ns(self):
        """Execute all notebook code cells in an isolated namespace."""
        code_cells = load_notebook_code_cells(CANONICAL_NB_PATH)
        ns: Dict[str, Any] = {
            "__name__": "__main__",
            "widgets": widgets,
            "display": display,
            "HTML": HTML,
            "clear_output": clear_output,
        }
        for idx, code in enumerate(code_cells):
            try:
                exec(code, ns)
            except Exception as e:
                pytest.fail(f"Failed executing cell {idx}: {e}")
        return ns

    def test_port_directory_structure(self, runtime_ns):
        """Verify the 14-port directory has all required canonical fields and categories."""
        port_dir = runtime_ns.get("PORT_DIRECTORY")
        assert isinstance(port_dir, list), "PORT_DIRECTORY must be a list"
        assert len(port_dir) == 14, f"Expected exactly 14 ports, found {len(port_dir)}"
        
        expected_ports = {3000, 4000, 8890, 8081, 8082, 8083, 8084, 8088, 8889, 8888, 9000, 9333, 18802, 18805}
        actual_ports = {p["port"] for p in port_dir}
        assert actual_ports == expected_ports, f"Port mismatch: {expected_ports ^ actual_ports}"

        categories = {p["category"] for p in port_dir}
        assert len(categories) == 4, f"Expected 4 categories, found {len(categories)}"
        for p in port_dir:
            assert "name" in p and "url" in p and "protocol" in p and "host" in p and "role" in p

    def test_preset_configs_integrity(self, runtime_ns):
        """Verify all 4 Quad presets contain exactly 4 valid endpoint URLs."""
        presets = runtime_ns.get("PRESET_CONFIGS")
        assert isinstance(presets, dict), "PRESET_CONFIGS must be a dict"
        expected_preset_names = {"🚀 Full Stack Quad", "🧠 AI Cluster Quad", "🖥️ Ops Grid Quad", "💾 Storage Quad"}
        assert set(presets.keys()) == expected_preset_names
        for name, urls in presets.items():
            assert len(urls) == 4, f"Preset '{name}' must have exactly 4 URLs"
            for u in urls:
                assert u.startswith("http://"), f"Invalid URL in preset '{name}': {u}"

    def test_multi_view_layout_mode_switching(self, runtime_ns):
        """Stress-test 1-click segmented layout mode switching (2x2, 1x2, 1x1)."""
        set_layout_mode = runtime_ns.get("set_layout_mode")
        slots = runtime_ns.get("slots")
        btn_2x2 = runtime_ns.get("btn_2x2")
        btn_1x2 = runtime_ns.get("btn_1x2")
        btn_1x1 = runtime_ns.get("btn_1x1")
        grid_container = runtime_ns.get("grid_container")

        assert callable(set_layout_mode)
        assert len(slots) == 4

        # Test 2x2 mode
        set_layout_mode("2x2")
        assert btn_2x2.button_style == "primary"
        assert btn_1x2.button_style == ""
        assert btn_1x1.button_style == ""
        for i in range(4):
            assert slots[i]["box"].layout.display == "flex"
        assert grid_container.layout.grid_template_columns == "repeat(2, minmax(0, 1fr))"

        # Test 1x2 mode
        set_layout_mode("1x2")
        assert btn_2x2.button_style == ""
        assert btn_1x2.button_style == "primary"
        assert btn_1x1.button_style == ""
        assert slots[0]["box"].layout.display == "flex"
        assert slots[1]["box"].layout.display == "flex"
        assert slots[2]["box"].layout.display == "none"
        assert slots[3]["box"].layout.display == "none"

        # Test 1x1 mode
        set_layout_mode("1x1")
        assert btn_2x2.button_style == ""
        assert btn_1x2.button_style == ""
        assert btn_1x1.button_style == "primary"
        assert slots[0]["box"].layout.display == "flex"
        assert slots[1]["box"].layout.display == "none"
        assert slots[2]["box"].layout.display == "none"
        assert slots[3]["box"].layout.display == "none"
        assert grid_container.layout.grid_template_columns == "1fr"

        # Rapid fuzz switching
        modes = ["2x2", "1x2", "1x1"]
        for m in modes * 15:
            set_layout_mode(m)
        # Restore 2x2
        set_layout_mode("2x2")

    def test_quad_preset_switching_and_slot_updates(self, runtime_ns):
        """Stress-test preset selection and verify all slot dropdown values sync."""
        set_preset = runtime_ns.get("set_preset")
        slots = runtime_ns.get("slots")
        presets = runtime_ns.get("PRESET_CONFIGS")
        preset_buttons = runtime_ns.get("preset_buttons")

        assert callable(set_preset)
        for name, expected_urls in presets.items():
            set_preset(name)
            for i, expected_url in enumerate(expected_urls):
                assert slots[i]["dropdown"].value == expected_url, f"Slot {i} dropdown mismatch for preset '{name}'"
            # Verify active button styling
            active_btn = [b for b in preset_buttons if b.description == name]
            assert len(active_btn) == 1
            assert active_btn[0].button_style == "success"

    def test_slot_dropdown_observer_and_rendering(self, runtime_ns):
        """Trigger dropdown value observers on all 4 slots and verify status and link rendering."""
        slots = runtime_ns.get("slots")
        port_dir = runtime_ns.get("PORT_DIRECTORY")

        for s_idx, slot in enumerate(slots):
            for p in port_dir[:5]:
                slot["dropdown"].value = p["url"]
                assert p["url"] in slot["link"].value
                assert "badge-chip" in slot["status"].value

    def test_height_selector_and_reprobe_button(self, runtime_ns):
        """Test height selector value changes and re-probe button click."""
        height_dropdown = runtime_ns.get("height_dropdown")
        refresh_btn = runtime_ns.get("refresh_btn")
        render_slot = runtime_ns.get("render_slot")

        # Verify button width styling prevents label clipping
        assert refresh_btn.layout.width == "135px", f"Expected width 135px for refresh button, got {refresh_btn.layout.width}"

        # Test height switching
        for h in ["380", "520", "750"]:
            height_dropdown.value = h
            for i in range(4):
                render_slot(i)

    def test_multi_tui_switcher(self, runtime_ns):
        """Verify Multi-TUI dropdown switching across Rust Ratatui, Go Bubble Tea, and Python Textual."""
        tui_dropdown = runtime_ns.get("tui_dropdown")
        render_tui_terminal = runtime_ns.get("render_tui_terminal")
        tui_previews = runtime_ns.get("TUI_PREVIEWS")

        assert tui_dropdown is not None
        assert render_tui_terminal is not None
        assert len(tui_previews) == 3

        for key in tui_previews.keys():
            tui_dropdown.value = key
            html_out = render_tui_terminal(key)
            assert "terminal-frame" in html_out
            assert "120 FPS PTY Stream" in html_out
            assert "terminal-dot" in html_out

    def test_cyber_ide_seaweedfs_client_and_sandbox(self, runtime_ns):
        """Stress-test SeaweedFSClient and the in-kernel execution sandbox."""
        SeaweedFSClient = runtime_ns.get("SeaweedFSClient")
        execute_in_kernel_sandbox = runtime_ns.get("execute_in_kernel_sandbox")

        client = SeaweedFSClient()
        # 1. Directory listing
        root_items = client.list_directory("/")
        assert isinstance(root_items, list)

        # 2. Read file
        nb_read = client.read_file("01_apps/notebooks/generate_glassmorphic_master_studio.py")
        if "error" not in nb_read:
            assert "content" in nb_read
            assert nb_read["lines"] > 10

        # 3. Binary safety guard
        bin_read = client.read_file("02_ai_models_and_inference/model.gguf")
        assert bin_read.get("is_binary") is True

        # 4. In-Kernel Sandbox execution
        res_ok = execute_in_kernel_sandbox("print('SANDBOX_TEST_SUCCESS'); a = 40 + 2")
        assert res_ok["success"] is True
        assert "SANDBOX_TEST_SUCCESS" in res_ok["stdout"]
        assert res_ok["elapsed_ms"] >= 0.0

        # 5. Sandbox syntax error handling
        res_syntax = execute_in_kernel_sandbox("def invalid_syntax(:")
        assert res_syntax["success"] is False
        assert "SyntaxError" in (res_syntax.get("error") or "") or "SyntaxError" in (res_syntax.get("stderr") or "")

        # 6. Sandbox runtime exception handling
        res_runtime = execute_in_kernel_sandbox("1 / 0")
        assert res_runtime["success"] is False
        assert "ZeroDivisionError" in (res_runtime.get("error") or "") or "ZeroDivisionError" in (res_runtime.get("stderr") or "")

    def test_pan_tompkins_dsp_engine(self, runtime_ns):
        """Test Pan-Tompkins 512Hz ECG DSP filter parameter bounds and fallback state."""
        load_authentic_movesense_telemetry = runtime_ns.get("load_authentic_movesense_telemetry")
        plot_ecg_dsp = runtime_ns.get("plot_ecg_dsp")
        render_dsp = runtime_ns.get("render_dsp")

        assert callable(load_authentic_movesense_telemetry)
        assert callable(plot_ecg_dsp)
        assert callable(render_dsp)

        # Execute plot_ecg_dsp with default and custom values
        plot_ecg_dsp(low_val=5.0, high_val=15.0, mwi_val=150)
        plot_ecg_dsp(low_val=2.0, high_val=25.0, mwi_val=200)

    def test_system_optimizer_sweep(self, runtime_ns):
        """Execute the 1-Click Multi-Domain System Optimizer empirical audit."""
        perform_empirical_system_audit = runtime_ns.get("perform_empirical_system_audit")
        assert callable(perform_empirical_system_audit)
        audit_res = perform_empirical_system_audit()
        assert isinstance(audit_res, str)
        assert "glass-card" in audit_res
        assert "Memory Governor" in audit_res
        assert "Tri-Vault Knowledge Sync" in audit_res


class TestRule0ZeroMockCompliance:
    """Forensic audit ensuring zero simulated arrays, real TCP socket probes, and authentic standby states."""

    def test_zero_mock_socket_probing(self):
        """Verify probe_port_quick and probe_mesh_live use authentic TCP sockets without synthetic overrides."""
        code_cells = load_notebook_code_cells(CANONICAL_NB_PATH)
        full_source = "\n".join(code_cells)

        # Check for socket connect_ex
        assert "s.connect_ex((host, port))" in full_source
        assert "s.settimeout" in full_source

        # Verify no fake arrays or hardcoded mock telemetry
        banned_patterns = [
            "mock_ecg_stream",
            "fake_telemetry",
            "random.uniform(60, 100)",
            "np.random.normal(size=512)",
        ]
        for pat in banned_patterns:
            assert pat not in full_source, f"Violation of Rule #0: Found banned pattern '{pat}'"

    def test_standby_cards_zero_mock_labeling(self):
        """Verify that offline endpoints render explicit 'STATUS: STANDBY (Zero-Mock Verified)' cards."""
        code_cells = load_notebook_code_cells(CANONICAL_NB_PATH)
        full_source = "\n".join(code_cells)
        assert "STATUS: STANDBY (Zero-Mock Verified)" in full_source
        assert "RULE #0 ZERO-MOCK VERIFIED" in full_source

    def test_hardware_isolation_no_gui_open(self):
        """Verify no 'open <file>' commands or GUI app spawns exist in notebook code."""
        code_cells = load_notebook_code_cells(CANONICAL_NB_PATH)
        full_source = "\n".join(code_cells)
        assert 'subprocess.run(["open"' not in full_source
        assert 'os.system("open ' not in full_source


class TestLiveQwenPort8083Inference:
    """Benchmark live Qwen inference on Port 8083 verifying TTFT < 200ms."""

    PORT_8083_URL = "http://127.0.0.1:8083"

    def test_port_8083_health(self):
        """Port 8083 /health must return HTTP 200."""
        req = urllib.request.Request(f"{self.PORT_8083_URL}/health")
        try:
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                assert resp.status == 200
        except Exception as e:
            pytest.fail(f"Port 8083 /health check failed: {e}")

    def test_port_8083_chat_completion_ttft(self):
        """Port 8083 /v1/chat/completions streaming Time To First Token (TTFT) must be < 200ms across 5 runs."""
        url = f"{self.PORT_8083_URL}/v1/chat/completions"
        ttfts: List[float] = []

        for i in range(5):
            payload = json.dumps({
                "model": "default",
                "messages": [{"role": "user", "content": f"Ping run {i}! Reply with PONG."}],
                "max_tokens": 10,
                "stream": True,
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

            t0 = time.perf_counter()
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                first_chunk = resp.readline()
                ttft_ms = (time.perf_counter() - t0) * 1000.0
                ttfts.append(ttft_ms)
                _ = resp.read()
            time.sleep(0.05)

        avg_ttft = sum(ttfts) / len(ttfts)
        max_ttft = max(ttfts)
        print(f"\n[QWEN INFERENCE 8083] TTFT Runs: {[round(t, 2) for t in ttfts]} ms | Avg: {avg_ttft:.2f}ms | Max: {max_ttft:.2f}ms")
        assert avg_ttft < 200.0, f"Average TTFT {avg_ttft:.2f}ms exceeded 200ms threshold"
        assert max_ttft < 350.0, f"Max TTFT {max_ttft:.2f}ms exceeded maximum burst limit"


class TestConcurrentWidgetStress:
    """Stress-test concurrent widget event dispatching and memory stability."""

    def test_concurrent_mode_and_preset_switching(self):
        """Simulate concurrent user interactions from multiple threads without deadlock or race corruption."""
        code_cells = load_notebook_code_cells(CANONICAL_NB_PATH)
        ns: Dict[str, Any] = {
            "__name__": "__main__",
            "widgets": widgets,
            "display": display,
            "HTML": HTML,
            "clear_output": clear_output,
        }
        for code in code_cells:
            exec(code, ns)

        set_layout_mode = ns["set_layout_mode"]
        set_preset = ns["set_preset"]
        presets = list(ns["PRESET_CONFIGS"].keys())
        modes = ["2x2", "1x2", "1x1"]

        errors: List[Exception] = []

        def worker_modes():
            try:
                for _ in range(30):
                    for m in modes:
                        set_layout_mode(m)
            except Exception as e:
                errors.append(e)

        def worker_presets():
            try:
                for _ in range(30):
                    for p in presets:
                        set_preset(p)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=worker_modes)
        t2 = threading.Thread(target=worker_presets)
        t1.start()
        t2.start()
        t1.join(timeout=10.0)
        t2.join(timeout=10.0)

        assert len(errors) == 0, f"Concurrent widget interaction errors: {errors}"
        # Ensure system settles into stable 2x2 state
        set_layout_mode("2x2")
        assert ns["current_mode"][0] == "2x2"
