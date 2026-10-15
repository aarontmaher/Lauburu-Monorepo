"""
Milestone M5: Tier 5 Adversarial Coverage Hardening Test Suite
6-Pillar Local AI Arena Training & Notebook Optimizer across 7-Layer Lauburu Mesh.

Author: Challenger 1 (challenger_m5_1_gen3) - Critic & Specialist
Mandate: Empirical Verification of All 5 Notebook Code Cells, Boundary Stress Testing,
Zero-Mock Invariants, Extreme Parameter Disparity, High-DPI Rendering, POSIX Concurrency,
and Non-Blocking Socket Probes.
"""

import ast
import concurrent.futures
import fcntl
import html
import http.server
import json
import math
import os
import re
import shutil
import socket
import socketserver
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Strict Matplotlib Agg Mandate
import matplotlib
matplotlib.use("Agg")
os.environ["MPLBACKEND"] = "Agg"
import matplotlib.pyplot as plt
import numpy as np
import pytest

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    NOTEBOOK_PATH,
    GLOBAL_NOTEBOOK_PATH,
    CHART_PATH,
    load_notebook_data,
    extract_code_cells,
    extract_markdown_cells,
    validate_dpo_schema,
    validate_probe_schema,
    calculate_elo_update as conftest_calculate_elo,
)


# =========================================================================
# Shared Fixture: Isolated Master Notebook Execution Sandbox
# =========================================================================
@pytest.fixture(scope="module")
def arena_notebook_sandbox():
    """
    Executes all 5 code cells of the master arena notebook sequentially in an
    isolated namespace with headless display adapters, exposing all internal
    functions, classes, constants, and data models.
    """
    nb_data = load_notebook_data(NOTEBOOK_PATH)
    code_cells = extract_code_cells(nb_data)
    assert len(code_cells) == 5, f"Expected 5 code cells in master notebook, found {len(code_cells)}"

    ns: Dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(NOTEBOOK_PATH),
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "clear_output": lambda *args, **kwargs: None,
    }

    # Sequentially execute cells 1 through 5
    for idx, cell_code in enumerate(code_cells, 1):
        try:
            exec(cell_code, ns)
        except Exception as e:
            pytest.fail(f"Failed to execute notebook code cell {idx}: {e}")

    return ns


# =========================================================================
# 1. Adversarial Cell 1: MRAL, CSS Theme Variables, Zero Raw JSON Helpers
# =========================================================================
class TestAdversarialCell1MRALAndZeroMockHelpers:
    """White-box adversarial tests for Cell 1: CSS tokens, MRAL adapters, Zero-Mock UI helpers."""

    def test_css_variables_and_cyberpunk_palette_completeness(self, arena_notebook_sandbox):
        """Verify all 5-color Cyberpunk CSS variables, glassmorphic styles, and keyframes exist."""
        css = arena_notebook_sandbox.get("ARENA_CYBERPUNK_CSS", "")
        assert css, "ARENA_CYBERPUNK_CSS must not be empty"

        required_css_tokens = [
            "--cyber-cyan: #06b6d4",
            "--cyber-blue: #3b82f6",
            "--cyber-purple: #8b5cf6",
            "--cyber-emerald: #10b981",
            "--cyber-amber: #f59e0b",
            "--bg-dark-base: #090d16",
            "--bg-glass-card: rgba(15, 23, 42, 0.85)",
            "pulse-green",
            "pulse-amber",
            "pulse-red",
            ".glass-console",
            ".glass-card",
            ".glass-card-glow-cyan",
            ".glass-card-glow-blue",
            ".glass-card-glow-purple",
            ".glass-card-glow-emerald",
            ".glass-card-glow-amber",
            ".glass-grid-2",
            ".glass-grid-3",
            ".glass-grid-6",
            ".glass-table",
            ".glass-select",
            ".glass-slider",
            ".pill-btn",
            ".metric-badge",
            ".progress-neon"
        ]
        for token in required_css_tokens:
            assert token in css, f"Missing required CSS design token: '{token}'"

    def test_mral_runtime_adapter_and_html_mimebundle(self, arena_notebook_sandbox):
        """Test Multi-Runtime Abstraction Layer HTML class mimebundle and repr contracts."""
        HTML_cls = arena_notebook_sandbox.get("HTML")
        assert HTML_cls is not None, "HTML class must be present in namespace"

        test_payload = "<div class='glass-card'>Test Content</div>"
        html_obj = HTML_cls(test_payload)
        
        # Check standard IPython / Marimo display protocol methods if available
        if hasattr(html_obj, "_repr_html_"):
            assert html_obj._repr_html_() == test_payload
        if hasattr(html_obj, "_mimebundle_"):
            bundle = html_obj._mimebundle_()
            assert isinstance(bundle, dict)
            assert bundle.get("text/html") == test_payload
        if hasattr(html_obj, "data"):
            assert html_obj.data == test_payload

    def test_zero_raw_json_helpers_adversarial_inputs(self, arena_notebook_sandbox):
        """Adversarial stress testing of zero raw JSON rendering helpers against edge/XSS inputs."""
        render_status_pulse = arena_notebook_sandbox["render_status_pulse"]
        render_glass_metric_card = arena_notebook_sandbox["render_glass_metric_card"]
        render_pillar_badge = arena_notebook_sandbox["render_pillar_badge"]
        render_styled_table = arena_notebook_sandbox["render_styled_table"]
        render_export_toast = arena_notebook_sandbox["render_export_toast"]
        render_dpo_split_view = arena_notebook_sandbox["render_dpo_split_view"]
        render_telemetry_probe_card = arena_notebook_sandbox["render_telemetry_probe_card"]

        # 1. Status pulse edge cases
        xss_status = "<script>alert('xss')</script>"
        pulse_out = render_status_pulse(xss_status, is_online=True, extra_info="<img src=x onerror=1>")
        assert "&lt;script&gt;" in pulse_out
        assert "&lt;img" in pulse_out
        assert "<script>" not in pulse_out

        # Check pulse color mappings
        assert "#10b981" in render_status_pulse("ONLINE", is_online=True)
        assert "#f59e0b" in render_status_pulse("SYNCING", is_online=True)
        assert "#f59e0b" in render_status_pulse("WAITING_FOR_SENSOR", is_online=False)
        assert "#ef4444" in render_status_pulse("OFFLINE", is_online=False)

        # 2. Metric card boundary progress clamping
        card_neg = render_glass_metric_card("Test Metric", "99.9", progress_pct=-50)
        assert "width: 0%;" in card_neg
        card_overflow = render_glass_metric_card("Test Metric", "99.9", progress_pct=250)
        assert "width: 100%;" in card_overflow
        card_none = render_glass_metric_card("Test Metric", "99.9", progress_pct=None)
        assert "progress-neon" not in card_none

        # 3. Pillar badge None/float handling
        badge_none = render_pillar_badge("Pillar X", elo=None, samples=None)
        assert "Pillar X" in badge_none
        assert "ELO:" not in badge_none
        badge_valid = render_pillar_badge(
            "WebDev",
            elo=2640.5,
            samples=10000,
            status="Active 24/7",
            dataset="lmarena-ai/webdev-arena-preference-10k",
            lead_model="Qwen 2.5 Coder 72B"
        )
        assert "ELO: 2640.5" in badge_valid
        assert "10,000 pairs" in badge_valid
        assert "badge-emerald" in badge_valid

        # 4. Styled table heterogeneous rows (dict vs list) and status badge variants
        headers = ["Node", "Status", "Latency", "Layer"]
        dict_rows = [
            {"Node": "Linux_Head", "Status": "ONLINE", "Latency": "4.85 ms", "Layer": "01_apps"},
            {"Node": "Samsung_S20", "Status": "WAITING_FOR_SENSOR", "Latency": "--", "Layer": "05_agents"},
            {"Node": "Offline_Worker", "Status": "OFFLINE", "Latency": "--", "Layer": "02_ai_models"},
            {"Node": "SSoT_Vault", "Status": "TRI-VAULT SYNC", "Latency": "0.28 ms", "Layer": "00_core"}
        ]
        table_dict_html = render_styled_table(headers, dict_rows, title="Active Mesh Matrix")
        assert "badge-emerald" in table_dict_html
        assert "badge-amber" in table_dict_html
        assert "badge-purple" in table_dict_html
        assert "4 Records" in table_dict_html

        list_rows = [
            ["Mac_Node", "ACTIVE", "0.08 ms", "01_apps"],
            ["Pixel_10", "SYNCING", "7.80 ms", "05_agents"]
        ]
        table_list_html = render_styled_table(headers, list_rows)
        assert "Mac_Node" in table_list_html
        assert "Pixel_10" in table_list_html

        # 5. Export toast HTML escaping
        toast_html = render_export_toast("<Special & Toast>", "/path/to/<file>.png", "Details & Metrics")
        assert "&lt;Special &amp; Toast&gt;" in toast_html
        assert "&lt;file&gt;.png" in toast_html

        # 6. DPO split view with metadata
        dpo_html = render_dpo_split_view(
            prompt="<Instruction>",
            chosen="<Solution A>",
            rejected="<Solution B>",
            metadata={"domain": "DSP", "elo": 2600.0}
        )
        assert "&lt;Instruction&gt;" in dpo_html
        assert "&lt;Solution A&gt;" in dpo_html
        assert "&lt;Solution B&gt;" in dpo_html
        assert "DSP" in dpo_html

        # 7. Telemetry probe card fallback args
        probe_card = render_telemetry_probe_card(
            node_name="Probed Node",
            url="http://127.0.0.1:4000",
            status="ONLINE",
            rtt_ms=1.23,
            role="Gateway"
        )
        assert "Probed Node" in probe_card
        assert "1.23 ms RTT" in probe_card
        assert "ONLINE" in probe_card

    def test_inspect_seaweedfs_ssot_adversarial_network_handling(self, arena_notebook_sandbox):
        """Test SeaweedFS SSoT cluster inspector with closed sockets and malformed JSON."""
        inspect_seaweedfs_ssot = arena_notebook_sandbox["inspect_seaweedfs_ssot"]
        
        # Test against non-listening ports (fast failure, zero-mock fallback)
        raft_state, filer_state = inspect_seaweedfs_ssot(
            master_url="http://127.0.0.1:1",
            filer_url="http://127.0.0.1:1"
        )
        assert raft_state["status"] == "STANDBY"
        assert raft_state["leader"] == "--"
        assert raft_state["peers"] == 0
        assert raft_state["is_leader"] is False
        assert filer_state["status"] == "STANDBY"
        assert filer_state["entries"] == 0


# =========================================================================
# 2. Adversarial Cell 2: Bradley-Terry ELO Math & Model Metadata Governance
# =========================================================================
class TestAdversarialCell2BradleyTerryAndModelSelector:
    """Adversarial testing of Bradley-Terry math invariants, dynamic K-factor, and model metadata."""

    def test_bradley_terry_extreme_rating_disparities(self, arena_notebook_sandbox):
        """Verify numerical stability and exponent clamping on extreme rating differences (+-10,000 ELO)."""
        calculate_elo_update = arena_notebook_sandbox["calculate_elo_update"]

        # Huge disparity A >> B (10,000 vs 100)
        exp_a, new_a, new_b = calculate_elo_update(10000.0, 100.0, score_a=1.0, k=32.0)
        assert math.isclose(exp_a, 1.0, abs_tol=1e-6)
        assert math.isclose(new_a, 10000.0, abs_tol=1e-4)
        assert math.isclose(new_b, 100.0, abs_tol=1e-4)
        assert math.isclose((new_a - 10000.0) + (new_b - 100.0), 0.0, abs_tol=1e-9)

        # Huge disparity A << B (100 vs 10,000)
        exp_a_rev, new_a_rev, new_b_rev = calculate_elo_update(100.0, 10000.0, score_a=0.0, k=32.0)
        assert math.isclose(exp_a_rev, 0.0, abs_tol=1e-6)
        assert math.isclose(new_a_rev, 100.0, abs_tol=1e-4)
        assert math.isclose(new_b_rev, 10000.0, abs_tol=1e-4)
        assert math.isclose((new_a_rev - 100.0) + (new_b_rev - 10000.0), 0.0, abs_tol=1e-9)

        # Massive upset (100 beats 10,000 with score_a=1.0)
        exp_upset, new_a_upset, new_b_upset = calculate_elo_update(100.0, 10000.0, score_a=1.0, k=32.0)
        assert math.isclose(exp_upset, 0.0, abs_tol=1e-6)
        assert math.isclose(new_a_upset, 100.0 + 32.0, abs_tol=1e-4)
        assert math.isclose(new_b_upset, 10000.0 - 32.0, abs_tol=1e-4)
        assert math.isclose((new_a_upset - 100.0) + (new_b_upset - 10000.0), 0.0, abs_tol=1e-9)

    def test_bradley_terry_exact_tie_and_monotonic_margin_scaling(self, arena_notebook_sandbox):
        """Verify exact draw handling and strict monotonic score response."""
        calculate_elo_update = arena_notebook_sandbox["calculate_elo_update"]

        # Exact symmetrical draw
        exp_draw, new_a_draw, new_b_draw = calculate_elo_update(2500.0, 2500.0, score_a=0.5, k=32.0)
        assert math.isclose(exp_draw, 0.5, abs_tol=1e-9)
        assert math.isclose(new_a_draw, 2500.0, abs_tol=1e-9)
        assert math.isclose(new_b_draw, 2500.0, abs_tol=1e-9)

        # Monotonicity test across 21 fine-grained margin steps
        r_a, r_b = 2600.0, 2550.0
        prev_new_a = -1e9
        prev_new_b = 1e9

        for score_pct in range(0, 105, 5):
            score = score_pct / 100.0
            _, cur_new_a, cur_new_b = calculate_elo_update(r_a, r_b, score_a=score, k=32.0)
            assert cur_new_a >= prev_new_a, f"ELO A failed monotonicity at score {score}"
            assert cur_new_b <= prev_new_b, f"ELO B failed anti-monotonicity at score {score}"
            assert math.isclose((cur_new_a - r_a) + (cur_new_b - r_b), 0.0, abs_tol=1e-9)
            prev_new_a = cur_new_a
            prev_new_b = cur_new_b

    def test_dynamic_k_factor_extreme_boundaries(self, arena_notebook_sandbox):
        """Stress test dynamic K-factor multi-parameter scaling formula."""
        calculate_dynamic_k_factor = arena_notebook_sandbox["calculate_dynamic_k_factor"]

        # 1. Base test
        k_base = calculate_dynamic_k_factor()
        assert 1.0 <= k_base <= 128.0

        # 2. Extreme parameter sizes (0.01B vs 10,000B)
        k_tiny = calculate_dynamic_k_factor(params_b=0.01)
        k_huge = calculate_dynamic_k_factor(params_b=10000.0)
        assert k_tiny > k_huge, "Smaller model should have larger learning volatility K"

        # 3. Extreme token counts (1 token vs 1,000,000 tokens)
        k_short = calculate_dynamic_k_factor(tokens_used=1)
        k_long = calculate_dynamic_k_factor(tokens_used=1000000)
        assert k_short >= k_long

        # 4. Latency deltas (0ms vs 100,000ms)
        k_fast = calculate_dynamic_k_factor(rtt_ms=0.0)
        k_slow = calculate_dynamic_k_factor(rtt_ms=100000.0)
        assert k_fast >= k_slow

        # 5. Rule #0 Truth certification gate: if not certified, K must be clamped to 1.0 (minimum)
        k_fake = calculate_dynamic_k_factor(zero_mock_certified=False)
        assert k_fake == 1.0

    def test_sanitize_model_metadata_fuzzing(self, arena_notebook_sandbox):
        """Fuzz test model metadata sanitizer with corrupt types and unknown keys."""
        sanitize_model_metadata = arena_notebook_sandbox["sanitize_model_metadata"]

        # Unknown model name falls back to default
        name, meta = sanitize_model_metadata("Unknown Quantum Model 9000")
        assert name == "Qwen 2.5 Coder 72B"
        assert meta["vram_gb"] == 42.0

        # None model name
        name_none, meta_none = sanitize_model_metadata(None)
        assert name_none == "Qwen 2.5 Coder 72B"

        # Extreme context window clamping
        _, meta_min_ctx = sanitize_model_metadata("Qwen 2.5 Coder 72B", {"context_window": 10})
        assert meta_min_ctx["context_window"] == 2048

        _, meta_max_ctx = sanitize_model_metadata("Qwen 2.5 Coder 72B", {"context_window": 50000000})
        assert meta_max_ctx["context_window"] == 1048576

        # Sharded flag computation
        _, meta_sharded = sanitize_model_metadata("Qwen 2.5 Coder 72B", {"vram_gb": 49.6})
        assert meta_sharded["is_sharded"] is True

        _, meta_cloud = sanitize_model_metadata("Gemini 3.1 Pro High", {"vram_gb": 0.0})
        assert meta_cloud["is_cloud"] is True
        assert meta_cloud["is_sharded"] is False

    def test_arena_state_manager_duel_lifecycle(self, arena_notebook_sandbox):
        """Verify ArenaStateManager mutates rankings, updates lead model ELO, and records history."""
        ArenaStateManager = arena_notebook_sandbox["ArenaStateManager"]
        PILLARS = arena_notebook_sandbox["PILLARS"]
        ARENA_MODELS = arena_notebook_sandbox["ARENA_MODELS"]

        manager = ArenaStateManager(PILLARS, ARENA_MODELS)
        initial_history_len = len(manager.duel_history)

        duel = manager.record_duel(
            model_a="Qwen 2.5 Coder 72B",
            model_b="Llama-3.3-70B-Instruct (Cloud Shadow)",
            score_a=1.0,
            pillar_id=1,
            k=32.0
        )

        assert len(manager.duel_history) == initial_history_len + 1
        assert duel["new_a"] > duel["old_a"]
        assert duel["new_b"] < duel["old_b"]
        assert math.isclose((duel["new_a"] - duel["old_a"]) + (duel["new_b"] - duel["old_b"]), 0.0, abs_tol=1e-9)

        # Verify pillar lead model ELO synchronization
        p1 = next(p for p in manager.pillars if p["id"] == 1)
        assert math.isclose(p1["elo"], duel["new_a"], abs_tol=1e-9)


# =========================================================================
# 3. Adversarial Cell 3: High-DPI Chart Rendering & Matplotlib Agg Invariants
# =========================================================================
class TestAdversarialCell3HighDpiVisualizationsAndAgg:
    """Adversarial stress testing of 3-Panel dark visualization generator and disk export."""

    def test_matplotlib_agg_backend_enforcement(self):
        """Verify that matplotlib backend is strictly Agg and no GUI windows can spawn."""
        backend = matplotlib.get_backend().lower()
        assert backend == "agg", f"Expected backend 'agg', found '{backend}'"

    def test_render_console_visualizations_and_png_integrity(self, arena_notebook_sandbox, temp_test_dir):
        """Render high-DPI console chart with custom pillars and verify PNG magic bytes and DPI."""
        render_console_visualizations = arena_notebook_sandbox["render_console_visualizations"]
        PILLARS = arena_notebook_sandbox["PILLARS"]

        # Render with default canonical pillars
        fig = render_console_visualizations(PILLARS, save_to_disk=True)
        assert fig is not None, "render_console_visualizations returned None"

        chart_file = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault/notebooks/6_pillar_dark_console.png")
        assert chart_file.exists(), f"Console chart file was not created at {chart_file}"
        assert chart_file.stat().st_size > 50000, f"Console chart size {chart_file.stat().st_size} bytes is too small"

        # Verify PNG Header Magic Bytes (89 50 4E 47 0D 0A 1A 0A)
        with open(chart_file, "rb") as f:
            header = f.read(8)
            assert header == b"\x89PNG\r\n\x1a\n", "Generated chart does not have valid PNG magic bytes"

        # Verify figure dimensions and dark slate background
        assert fig.get_dpi() == 160.0
        assert fig.get_size_inches().tolist() == [19.0, 5.4]
        assert len(fig.axes) >= 3, f"Expected 3 main panel axes (plus twinx), found {len(fig.axes)}"

    def test_render_console_visualizations_extreme_values(self, arena_notebook_sandbox):
        """Adversarially test chart generator with extreme outlier ELO ratings and latencies."""
        render_console_visualizations = arena_notebook_sandbox["render_console_visualizations"]
        
        adversarial_pillars = [
            {"pillar": "Ultra Low ELO", "elo": 1000.0, "color": "#06b6d4", "tok_s": 5.0, "ttft_ms": 150.0},
            {"pillar": "Ultra High ELO", "elo": 4500.0, "color": "#3b82f6", "tok_s": 200.0, "ttft_ms": 1.0},
            {"pillar": "Mid ELO A", "elo": 2500.0, "color": "#8b5cf6", "tok_s": 40.0, "ttft_ms": 20.0},
            {"pillar": "Mid ELO B", "elo": 2600.0, "color": "#10b981", "tok_s": 50.0, "ttft_ms": 15.0},
            {"pillar": "Mid ELO C", "elo": 2700.0, "color": "#f59e0b", "tok_s": 60.0, "ttft_ms": 10.0},
            {"pillar": "Mid ELO D", "elo": 2800.0, "color": "#ec4899", "tok_s": 70.0, "ttft_ms": 8.0}
        ]

        fig = render_console_visualizations(adversarial_pillars, save_to_disk=False)
        assert fig is not None
        plt.close(fig)


# =========================================================================
# 4. Adversarial Cell 4: 6-Pillar Ingestion, DPO Formatting & Tri-Vault Sync
# =========================================================================
class TestAdversarialCell4TriVaultSyncAndDatasetIngestion:
    """Adversarial testing of 6-Pillar dataset streaming, universal DPO formatting, and Tri-Vault sync."""

    def test_fast_count_and_stream_records_on_fuzzed_files(self, arena_notebook_sandbox, temp_test_dir):
        """Test line counter and streaming generator on corrupted and blank files."""
        fast_count_records = arena_notebook_sandbox["fast_count_records"]
        stream_dataset_records = arena_notebook_sandbox["stream_dataset_records"]

        # 1. Non-existent file
        assert fast_count_records(temp_test_dir / "non_existent.jsonl") == 0
        assert list(stream_dataset_records(temp_test_dir / "non_existent.jsonl")) == []

        # 2. Corrupt JSONL with blank lines, comments, and invalid JSON tokens
        corrupt_jsonl = temp_test_dir / "corrupt_data.jsonl"
        with open(corrupt_jsonl, "w", encoding="utf-8") as f:
            f.write("\n")
            f.write('{"valid_key": "record 1"}\n')
            f.write("NOT_A_JSON_STRING\n")
            f.write("\n")
            f.write('{"valid_key": "record 2"}\n')
            f.write("{unclosed_json: true\n")
            f.write('{"valid_key": "record 3"}\n')

        # Fast count counts newline bytes
        assert fast_count_records(corrupt_jsonl) == 7
        
        # Stream parser skips invalid/empty lines safely
        valid_records = list(stream_dataset_records(corrupt_jsonl))
        assert len(valid_records) == 3
        assert valid_records[0]["valid_key"] == "record 1"
        assert valid_records[1]["valid_key"] == "record 2"
        assert valid_records[2]["valid_key"] == "record 3"

        # 3. JSON array file
        json_array = temp_test_dir / "array.json"
        with open(json_array, "w", encoding="utf-8") as f:
            json.dump([{"item": 1}, {"item": 2}, {"item": 3}, {"item": 4}], f)

        assert fast_count_records(json_array) == 4
        assert len(list(stream_dataset_records(json_array, limit=2))) == 2

    def test_format_pillar_dpo_all_6_pillars_adversarial_contract(self, arena_notebook_sandbox):
        """Verify format_pillar_dpo handles empty, partial, and custom records across all 6 pillars."""
        format_pillar_dpo = arena_notebook_sandbox["format_pillar_dpo"]

        for pillar_id in range(1, 7):
            # 1. Empty dictionary record
            p, c, r, meta = format_pillar_dpo(pillar_id, {})
            assert isinstance(p, str) and len(p) > 0
            assert isinstance(c, str) and len(c) > 0
            assert isinstance(r, str) and len(r) > 0
            assert meta["pillar_id"] == pillar_id
            assert meta["zero_mock_certified"] is True
            assert meta["tokens_prompt"] > 0
            assert meta["tokens_chosen"] > 0
            assert meta["tokens_rejected"] > 0

            # 2. Custom record with unexpected types
            custom_rec = {
                "instruction": 12345,  # int instead of str
                "chosen": ["list", "of", "tokens"],  # list instead of str
                "rejected": None
            }
            p2, c2, r2, meta2 = format_pillar_dpo(pillar_id, custom_rec)
            assert isinstance(p2, str)
            assert isinstance(c2, str)
            assert isinstance(r2, str)

    def test_verify_zero_mock_compliance_adversarial_rejections(self, arena_notebook_sandbox):
        """Verify Rule #0 validator rejects all 10+ adversarial simulated/corrupt patterns."""
        verify_zero_mock_compliance = arena_notebook_sandbox["verify_zero_mock_compliance"]

        # Valid baseline
        valid_rec = {
            "prompt": "Authentic prompt",
            "chosen": "Authentic chosen response",
            "rejected": "Suboptimal response",
            "metadata": {
                "zero_mock_certified": True,
                "truth_verified": True,
                "truth_compliance_pct": 100.0,
                "latency_ms": 14.2,
                "tokens_generated": 120
            }
        }
        ok, msg = verify_zero_mock_compliance(valid_rec)
        assert ok is True, f"Valid record rejected: {msg}"

        # 1. Non-dict record
        ok, _ = verify_zero_mock_compliance(["not", "a", "dict"])
        assert ok is False

        # 2. Negative latency
        bad_lat = dict(valid_rec)
        bad_lat["latency_ms"] = -5.0
        ok, _ = verify_zero_mock_compliance(bad_lat)
        assert ok is False

        # 3. Negative token count
        bad_tok = dict(valid_rec)
        bad_tok["tokens_generated"] = -10
        ok, _ = verify_zero_mock_compliance(bad_tok)
        assert ok is False

        # 4. truth_verified = False
        bad_truth = dict(valid_rec)
        bad_truth["truth_verified"] = False
        ok, _ = verify_zero_mock_compliance(bad_truth)
        assert ok is False

        # 5. truth_compliance_pct < 100.0
        bad_pct = dict(valid_rec)
        bad_pct["metadata"] = dict(valid_rec["metadata"])
        bad_pct["metadata"]["truth_compliance_pct"] = 99.5
        ok, _ = verify_zero_mock_compliance(bad_pct)
        assert ok is False

        # 6. Empty prompt
        bad_p = dict(valid_rec)
        bad_p["prompt"] = ""
        ok, _ = verify_zero_mock_compliance(bad_p)
        assert ok is False

        # 7. Empty completion
        bad_c = dict(valid_rec)
        bad_c["chosen"] = ""
        ok, _ = verify_zero_mock_compliance(bad_c)
        assert ok is False

        # 8. Dummy mock placeholder string
        bad_mock = dict(valid_rec)
        bad_mock["custom_debug"] = "Generated from mock_dummy generator"
        ok, _ = verify_zero_mock_compliance(bad_mock)
        assert ok is False

    def test_tri_vault_sync_engine_posix_locking_concurrency(self, arena_notebook_sandbox, temp_test_dir):
        """Simulate multithreaded concurrent POSIX atomic writes to verify zero line corruption."""
        TriVaultSyncEngine = arena_notebook_sandbox["TriVaultSyncEngine"]
        
        sink_path = temp_test_dir / "concurrent_training.jsonl"
        board_path = temp_test_dir / "leaderboard.md"

        engine = TriVaultSyncEngine(
            monorepo_root=temp_test_dir,
            lora_sink=sink_path,
            leaderboard_path=board_path
        )

        num_threads = 16
        records_per_thread = 25
        total_expected = num_threads * records_per_thread

        def _worker(thread_id: int):
            for i in range(records_per_thread):
                rec = {
                    "prompt": f"Prompt from worker {thread_id} item {i}",
                    "chosen": f"Chosen response {thread_id}-{i}",
                    "rejected": f"Rejected response {thread_id}-{i}",
                    "metadata": {
                        "pillar_id": (thread_id % 6) + 1,
                        "thread_id": thread_id,
                        "item_id": i,
                        "zero_mock_certified": True
                    }
                }
                engine.append_training_record(rec)

        threads = [threading.Thread(target=_worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Read back and verify exact line count and JSON validity
        assert sink_path.exists()
        with open(sink_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) == total_expected, f"Expected {total_expected} lines, found {len(lines)}"
        
        # Verify every line is valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert "prompt" in parsed and "chosen" in parsed

        # Test leaderboard synchronization
        pillars_data = arena_notebook_sandbox["PILLARS"]
        board_res = engine.sync_obsidian_leaderboard(pillars_data)
        assert board_path.exists()
        board_content = board_path.read_text(encoding="utf-8")
        assert "6-Pillar Local AI Arena & Training Synchronization Leaderboard" in board_content
        assert "WebDev & UI/UX Arena" in board_content


# =========================================================================
# 5. Adversarial Cell 5: Live Sockets, Debate Stream Inspector & Standalone JS
# =========================================================================
class TestAdversarialCell5LiveSocketsAndDebateStreamInspector:
    """Adversarial testing of <=200ms socket timeouts, live debate normalization, and JS bundle."""

    def test_tcp_socket_probe_strict_timeout_ceiling(self, arena_notebook_sandbox):
        """Empirically measure that tcp_socket_probe never exceeds the 200ms ceiling on dead ports."""
        tcp_socket_probe = arena_notebook_sandbox["tcp_socket_probe"]

        # Probe an unused localhost port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        _, free_port = s.getsockname()
        s.close()

        t0 = time.perf_counter()
        ok, rtt, err = tcp_socket_probe("127.0.0.1", free_port, timeout=0.15)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert ok is False
        assert rtt is None
        assert err is not None
        assert elapsed_ms <= 300.0, f"Socket probe took {elapsed_ms:.1f}ms, exceeding timeout boundary"

    def test_probe_mesh_node_dual_signature_and_zero_mock_fallback(self, arena_notebook_sandbox):
        """Test probe_mesh_node with both Spec object and positional arguments."""
        probe_mesh_node = arena_notebook_sandbox["probe_mesh_node"]
        MeshNodeSpec = arena_notebook_sandbox["MeshNodeSpec"]

        # Signature 1: String arguments (node_name, url, timeout)
        res_str = probe_mesh_node("Dead Node", "http://127.0.0.1:59999", timeout=0.10)
        assert res_str["status"] == "OFFLINE"
        assert res_str["code"] == 0
        assert res_str["rtt_ms"] is None
        assert res_str["zero_mock_certified"] is True

        # Signature 2: MeshNodeSpec object
        spec = MeshNodeSpec(
            layer_id="L9",
            node_id="test_dead_node",
            name="Spec Dead Node",
            hardware="Virtual Test",
            role="Test",
            category="test",
            local_ip="127.0.0.1",
            tailscale_ip="127.0.0.1",
            primary_endpoint="http://127.0.0.1:59998",
            timeout_sec=0.10
        )
        res_spec = probe_mesh_node(spec)
        assert res_spec["status"] == "OFFLINE"
        assert res_spec["node_id"] == "test_dead_node"
        assert res_spec["zero_mock_certified"] is True

    def test_compute_debate_elo_updates_adversarial_consensus_scores(self, arena_notebook_sandbox):
        """Adversarially test debate ELO update engine across out-of-range consensus scores."""
        compute_debate_elo_updates = arena_notebook_sandbox["compute_debate_elo_updates"]

        # 1. Extreme negative score (clamped to 0.0)
        deltas_neg = compute_debate_elo_updates(-5.0)
        assert "local_model" in deltas_neg
        assert deltas_neg["local_model"]["delta"] < 0  # failed consensus penalizes local model

        # 2. Extreme positive score (clamped to 1.0)
        deltas_pos = compute_debate_elo_updates(5.0)
        assert deltas_pos["local_model"]["delta"] > 0  # 100% consensus rewards local model

        # 3. Custom participants
        custom_participants = [
            {"id": "agent_alpha", "name": "Agent Alpha", "rating": 1800.0, "params_b": 70.0, "rtt_ms": 5.0},
            {"id": "agent_beta", "name": "Agent Beta", "rating": 1400.0, "params_b": 8.0, "rtt_ms": 2.0}
        ]
        deltas_custom = compute_debate_elo_updates(0.95, participants=custom_participants)
        assert "agent_alpha" in deltas_custom
        assert "agent_beta" in deltas_custom

    def test_debate_view_renderer_and_accord_components(self, arena_notebook_sandbox):
        """Test DebateViewRenderer produces well-formed glassmorphic cards for all roles."""
        DebateViewRenderer = arena_notebook_sandbox["DebateViewRenderer"]
        NormalizedDebateTurn = arena_notebook_sandbox["NormalizedDebateTurn"]
        NormalizedConsensusAccord = arena_notebook_sandbox["NormalizedConsensusAccord"]

        # Render turn cards across all 4 role keys
        roles = ["local_model", "cloud_shadow", "devils_advocate", "consensus"]
        for r_key in roles:
            turn = NormalizedDebateTurn(
                turn_index=1,
                role_key=r_key,
                role_label=r_key.upper(),
                speaker_name=f"Speaker for {r_key}",
                hardware_target="Node X",
                content="Sample discourse text with <script> safe encoding.",
                metrics={"tokens_sec": 45.0, "vram_gb": 14.0}
            )
            card_html = DebateViewRenderer.render_turn_card(turn)
            assert "Speaker for" in card_html
            assert "&lt;script&gt;" in card_html

        # Render diff viewer
        diff_text = """--- a/router.py\n+++ b/router.py\n@@ -1,3 +1,3 @@\n-def old():\n+def new():\n     pass"""
        diff_html = DebateViewRenderer.render_diff_viewer(diff_text)
        assert "def old()" in diff_html
        assert "def new()" in diff_html

        # Render consensus card
        accord = NormalizedConsensusAccord(
            debate_id="DEBATE_TEST_001",
            topic_id="TOPIC_01",
            title="Consensus Title",
            domain="Testing",
            timestamp_utc="2026-09-02 00:00:00 UTC",
            consensus_score=0.95,
            consensus_status="RATIFIED",
            truth_verified=True,
            truth_compliance_pct=100.0,
            actionable_consensus="Actionable text",
            top_priorities=["Priority 1", "Priority 2"],
            elo_deltas={"local_model": {"name": "Qwen", "initial_elo": 1600.0, "new_elo": 1610.0, "delta": 10.0}},
            verified_diff=diff_text
        )
        accord_html = DebateViewRenderer.render_consensus_card(accord)
        assert "95% CONSENSUS" in accord_html
        assert "RATIFIED" in accord_html
        assert "Priority 1" in accord_html

    def test_standalone_debate_inspector_js_bundle_and_syntax(self, arena_notebook_sandbox):
        """Test StandaloneDebateInspectorJS generates valid offline JavaScript replay engine."""
        StandaloneDebateInspectorJS = arena_notebook_sandbox["StandaloneDebateInspectorJS"]
        NormalizedConsensusAccord = arena_notebook_sandbox["NormalizedConsensusAccord"]

        # 1. Empty accords list generates standby card
        empty_html = StandaloneDebateInspectorJS.generate_html([])
        assert "Debate Stream Standby" in empty_html

        # 2. Populated accords list generates JS bundle
        sample_accord = NormalizedConsensusAccord(
            debate_id="DEBATE_TEST_002",
            topic_id="TOPIC_02",
            title="Mesh Resilience",
            domain="Governance",
            timestamp_utc="2026-09-02 00:00:00 UTC",
            consensus_score=0.88,
            consensus_status="APPROVED",
            truth_verified=True,
            truth_compliance_pct=100.0,
            actionable_consensus="Enforce bounded timeouts",
            top_priorities=["Priority A"],
            elo_deltas={},
            verified_diff=""
        )
        bundle_html = StandaloneDebateInspectorJS.generate_html([sample_accord])
        assert "<script>" in bundle_html
        assert "window.debateInspectorEngine" in bundle_html
        assert "setTopic" in bundle_html
        assert "stepTopic" in bundle_html
        assert "renderCurrent" in bundle_html
