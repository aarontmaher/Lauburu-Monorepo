#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Lauburu Sovereign Mesh: Omni Terminal Notebook Plugin Test Suite
================================================================================
Test Target:
- 01_apps/omniterminal_notebook_plugin/__init__.py
- 01_apps/omniterminal_notebook_plugin/hardware_hud.py
- 01_apps/omniterminal_notebook_plugin/polyglot_runner.py
- 01_apps/omniterminal_notebook_plugin/training_bridge.py
- 01_apps/omniterminal_notebook_plugin/terminal_widget.py
- 01_apps/omniterminal_notebook_plugin/magics.py
================================================================================
"""

import json
import os
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT / "01_apps"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))

import omniterminal_notebook_plugin
from omniterminal_notebook_plugin import (
    NotebookHardwareAnalyzer,
    NotebookPolyglotRunner,
    NotebookTrainingBridge,
    OmniterminalNotebookWidget,
    OmniterminalMagics,
    load_ipython_extension,
    unload_ipython_extension
)


def test_plugin_package_import():
    assert omniterminal_notebook_plugin.__version__ == "1.0.0"
    assert callable(load_ipython_extension)
    assert callable(unload_ipython_extension)


def test_hardware_analyzer_authentic_metrics():
    analyzer = NotebookHardwareAnalyzer()
    snap = analyzer.get_snapshot()

    assert snap.ram_total_gb >= 16.0
    assert snap.ram_available_gb > 0.0
    assert snap.ram_sanctuary_headroom_gb >= 4.0  # Rule 3 sanctuary compliant (4.0 GB Headroom)
    assert snap.ram_sanctuary_ok is True
    assert snap.cpu_temp_c > 0.0
    assert "L2_MacBook_Pro_TB4" in snap.mesh_latencies_ms
    assert snap.mesh_latencies_ms["L2_MacBook_Pro_TB4"] <= 1.0  # Sub-millisecond TB4

    html = analyzer.render_html_hud()
    assert "🛰️ LAUBURU OMNITERMINAL" in html
    assert "RAM SANCTUARY" in html


def test_polyglot_runner_python_execution():
    runner = NotebookPolyglotRunner(timeout_sec=4.0)

    # 1. Valid python execution
    valid_code = "def add(a, b):\n    return a + b\nassert add(10, 20) == 30\nprint('TEST_PASS')"
    res = runner.execute_code(valid_code, "python", prompt="Addition assert")
    assert res.exit_code == 0
    assert res.ast_valid is True
    assert res.zero_mock_clean is True
    assert res.grpo_reward > 0
    assert "TEST_PASS" in res.stdout
    assert res.serialized_to_lora is True

    # 2. Syntax error detection
    bad_syntax = "def add(a, b\n    return a + b"
    bad_res = runner.execute_code(bad_syntax, "python")
    assert bad_res.exit_code != 0
    assert bad_res.ast_valid is False
    assert bad_res.grpo_reward < 0

    # 3. Rule #0 Zero-mock violation check
    mock_code = "import unittest.mock\ndef add(a, b): return 30"
    mock_res = runner.execute_code(mock_code, "python")
    assert mock_res.exit_code != 0
    assert mock_res.zero_mock_clean is False
    assert mock_res.grpo_reward == -5.0


def test_polyglot_runner_bash_execution():
    runner = NotebookPolyglotRunner(timeout_sec=4.0)
    bash_code = "echo 'BASH_NOTEBOOK_TEST_ONLINE'\nexit 0"
    res = runner.execute_code(bash_code, "bash")
    assert res.exit_code == 0
    assert "BASH_NOTEBOOK_TEST_ONLINE" in res.stdout
    assert res.grpo_reward > 0


def test_training_bridge_interactive():
    bridge = NotebookTrainingBridge()
    # 1. Test GRPO step
    step_res = bridge.run_training_step("grpo_compiler_reward")
    assert step_res["protocol"] == "grpo_compiler_reward"
    assert step_res["samples_count"] >= 1
    assert step_res["best_candidate"]["exit_code"] == 0

    # 2. Test HTML dashboard render
    html = bridge.render_html_dashboard()
    assert "HIGH-ROI TRAINING CONSOLE" in html
    assert "Frontier Win Rate" in html


def test_terminal_widget_probe_and_render():
    widget = OmniterminalNotebookWidget()
    probe = widget.probe_daemon()

    # Daemon is running in background via launchd/task
    assert probe["online"] is True
    assert "Tier 1" in probe["transport"]
    assert probe["latency_ms"] < 5.0  # Sub-5ms socket latency

    html = widget.render_html_widget(height_px=280)
    assert "OMNITERMINAL MULTIPLEXER PTY" in html
    assert "ONLINE • READY" in html


def test_magics_execution():
    magics = OmniterminalMagics()

    # %omni status
    magics.omni("status")

    # %omni snapshot
    magics.omni("snapshot")

    # %%omni_polyglot
    magics.omni_polyglot("python", "assert 2 * 2 == 4\nprint('MAGICS_PASS')")


def test_zero_mock_compliance():
    """Rule #0 & Rule 1: Zero mock imports across all notebook plugin files."""
    plugin_files = [
        REPO_ROOT / "01_apps/omniterminal_notebook_plugin/__init__.py",
        REPO_ROOT / "01_apps/omniterminal_notebook_plugin/hardware_hud.py",
        REPO_ROOT / "01_apps/omniterminal_notebook_plugin/polyglot_runner.py",
        REPO_ROOT / "01_apps/omniterminal_notebook_plugin/training_bridge.py",
        REPO_ROOT / "01_apps/omniterminal_notebook_plugin/terminal_widget.py",
        REPO_ROOT / "01_apps/omniterminal_notebook_plugin/magics.py",
    ]

    for fpath in plugin_files:
        assert fpath.exists(), f"File {fpath} does not exist"
        content = fpath.read_text(encoding="utf-8")
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("import mock") or s.startswith("from unittest import mock") or s.startswith("from unittest.mock"):
                pytest.fail(f"Mock import violation in {fpath.name}:{i} -> {line}")
            if "MagicMock" in line and not ("forbidden" in content or "mock_tokens" in line):
                pytest.fail(f"MagicMock usage violation in {fpath.name}:{i} -> {line}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
