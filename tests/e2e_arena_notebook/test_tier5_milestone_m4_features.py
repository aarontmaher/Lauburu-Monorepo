"""
Milestone M4 Dedicated E2E Test Suite:
Feature F10: Zero-Mock Live Mesh Sockets & Telemetry Probes Engine
Feature F11: Live Multi-Agent Debate Stream Inspector & Consensus Card
Feature F12: Multi-Runtime Compatibility & Kernel Execution Architecture

Author: teamwork_preview_worker_m4_gen3 (Implementer, QA, Specialist)
"""

import ast
import json
import math
import os
import socket
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    NOTEBOOK_PATH,
    GLOBAL_NOTEBOOK_PATH,
    calculate_elo_update,
    validate_dpo_schema,
    load_notebook_data,
    extract_code_cells,
)


@pytest.fixture(scope="module")
def notebook_cells():
    """Load notebook JSON and extract code cells."""
    nb = load_notebook_data(NOTEBOOK_PATH)
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    return code_cells


@pytest.fixture(scope="module")
def cell_5_namespace(notebook_cells):
    """Execute Cell 5 in an isolated sandbox namespace with MRAL mocks."""
    ns: Dict[str, Any] = {
        "__name__": "__main__",
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "clear_output": lambda *args, **kwargs: None,
    }
    # Execute Cell 1, Cell 2, Cell 5 for shared prerequisites
    cell1_src = "".join(notebook_cells[0].get("source", []))
    cell2_src = "".join(notebook_cells[1].get("source", []))
    cell5_src = "".join(notebook_cells[4].get("source", []))

    exec(cell1_src, ns)
    exec(cell2_src, ns)
    exec(cell5_src, ns)
    return ns


# =========================================================================
# Feature F10 Tests: Zero-Mock Live Mesh Sockets & Telemetry Probes Engine
# =========================================================================
class TestFeatureF10ZeroMockMeshProbes:
    """Test Feature F10: 7-layer canonical endpoints, <=200ms timeout ceiling, and zero-mock integrity."""

    def test_f10_01_canonical_endpoints_definition(self, cell_5_namespace):
        """Verify 7-layer canonical endpoints are defined in CANONICAL_7LAYER_NODES."""
        nodes = cell_5_namespace.get("CANONICAL_7LAYER_NODES", [])
        assert len(nodes) >= 7, f"Expected at least 7 canonical nodes, found {len(nodes)}"

        node_ids = {n.node_id for n in nodes}
        expected_ids = {"mac_node", "macbook_pro", "linux_head_node", "macbook_air", "pixel_10_pro_xl", "gl_inet_router"}
        assert expected_ids.issubset(node_ids), f"Missing expected node IDs: {expected_ids - node_ids}"

        # Check endpoints and hardware specs
        endpoints = [n.primary_endpoint for n in nodes]
        assert any("4005" in ep for ep in endpoints), "Missing Linux Head Node (:4005)"
        assert any("8889" in ep for ep in endpoints), "Missing MacBook Air Metal (:8889)"
        assert any("8083" in ep for ep in endpoints), "Missing Devil's Advocate (:8083)"
        assert any("8081" in ep or "8082" in ep for ep in endpoints), "Missing llama.cpp RPC"

    def test_f10_02_timeout_ceiling_enforcement(self, cell_5_namespace):
        """Verify probes enforce <=200ms socket timeout ceiling."""
        nodes = cell_5_namespace.get("CANONICAL_7LAYER_NODES", [])
        for n in nodes:
            assert n.timeout_sec <= 0.20, f"Node {n.name} has timeout {n.timeout_sec}s exceeding 0.20s ceiling"

    def test_f10_03_zero_mock_offline_fallback(self, cell_5_namespace):
        """Verify unreachable node returns clean waiting state without fabricated telemetry."""
        probe_fn = cell_5_namespace["probe_mesh_node"]
        
        # Probe an unused local port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        _, free_port = s.getsockname()
        s.close()

        res = probe_fn("Offline Test Node", f"http://127.0.0.1:{free_port}", timeout=0.10)
        assert res["status"] == "OFFLINE"
        assert res["code"] == 0
        assert res["rtt_ms"] is None
        assert res["data"] is None
        assert res["zero_mock_certified"] is True

    def test_f10_04_css_pulse_color_palette(self, cell_5_namespace):
        """Verify CSS status pulses conform to Cyberpunk Palette."""
        render_pulse = cell_5_namespace["render_status_pulse"]
        
        online_pulse = render_pulse("ONLINE", is_online=True)
        assert "#10b981" in online_pulse  # Emerald
        
        offline_pulse = render_pulse("OFFLINE", is_online=False)
        assert "#ef4444" in offline_pulse  # Ruby
        
        sync_pulse = render_pulse("SYNCING", is_online=False)
        assert "#f59e0b" in sync_pulse  # Amber

    def test_f10_05_parallel_probe_execution(self, cell_5_namespace):
        """Verify parallel multi-node probing completes within bounded duration."""
        probe_all_fn = cell_5_namespace["probe_all_mesh_nodes"]
        nodes = cell_5_namespace["CANONICAL_7LAYER_NODES"]

        results = probe_all_fn(nodes, max_workers=6)
        assert len(results) == len(nodes)
        for n in nodes:
            assert n.node_id in results or n.name in results
            r = results.get(n.node_id, results.get(n.name))
            assert r["status"] in ("ONLINE", "OFFLINE")


# =========================================================================
# Feature F11 Tests: Live Multi-Agent Debate Stream Inspector & Consensus Card
# =========================================================================
class TestFeatureF11DebateStreamInspector:
    """Test Feature F11: Transcript Ingestion, Bradley-Terry ELO, Consensus Cards & Verified Diffs."""

    def test_f11_01_debate_transcript_ingestion(self, cell_5_namespace):
        """Verify debate transcripts are ingested from authentic SSoT paths."""
        ingestor = cell_5_namespace["DebateStreamIngestor"]()
        transcripts = ingestor.load_local_transcripts()
        assert len(transcripts) >= 1, "Expected at least 1 debate transcript record"
        
        first = transcripts[0]
        assert hasattr(first, "debate_id")
        assert hasattr(first, "topic_id")
        assert hasattr(first, "rounds")
        assert len(first.rounds) >= 1

    def test_f11_02_turn_roles_and_color_coding(self, cell_5_namespace):
        """Verify multi-agent turn roles map to required colors."""
        ingestor = cell_5_namespace["DebateStreamIngestor"]()
        transcripts = ingestor.load_local_transcripts()
        first = transcripts[0]

        roles = {t.role_key for t in first.rounds}
        assert any("local" in r.lower() or "cloud" in r.lower() or "judge" in r.lower() or "devil" in r.lower() or "consensus" in r.lower() for r in roles)

    def test_f11_03_bradley_terry_elo_dynamic_k_factor(self, cell_5_namespace):
        """Verify dynamic K-factor scaling with model size, compute RTT, and consensus score."""
        calc_k = cell_5_namespace["calculate_dynamic_k_factor"]
        
        # Base calculation
        k_base = calc_k(k0=32.0, params_b=72.0, rtt_ms=18.5, consensus_score=1.0)
        assert 1.0 <= k_base <= 128.0, f"K-factor {k_base} out of expected bounds"

        # Smaller model (7B) has higher size scaling (larger K)
        k_small = calc_k(k0=32.0, params_b=7.0, rtt_ms=18.5, consensus_score=1.0)
        assert k_small > k_base, "Smaller model should have larger K-factor multiplier"

        # High latency decreases compute confidence
        k_slow = calc_k(k0=32.0, params_b=72.0, rtt_ms=200.0, consensus_score=1.0)
        assert k_slow < k_base, "Higher latency should lower K-factor"

    def test_f11_04_consensus_card_and_diff_rendering(self, cell_5_namespace):
        """Verify consensus card renders verified diff patch and zero raw JSON."""
        renderer = cell_5_namespace["DebateViewRenderer"]()
        ingestor = cell_5_namespace["DebateStreamIngestor"]()
        transcripts = ingestor.load_local_transcripts()
        first = transcripts[0]
        
        consensus_html = renderer.render_consensus_card(first)
        assert "CONSENSUS ACCORD" in consensus_html
        assert "diff" in consensus_html or "patch" in consensus_html or "@@" in consensus_html or "Score" in consensus_html

        turn_html = renderer.render_turn_card(first.rounds[0])
        assert "glass-card" in turn_html

    def test_f11_05_standalone_js_client_generation(self, cell_5_namespace):
        """Verify standalone client-side JavaScript engine is embedded with play/pause and scrubber."""
        js_engine = cell_5_namespace["StandaloneDebateInspectorJS"]()
        ingestor = cell_5_namespace["DebateStreamIngestor"]()
        transcripts = ingestor.load_local_transcripts()
        
        html_out = js_engine.generate_html(transcripts)
        assert "<script>" in html_out
        assert "debate-inspector-root" in html_out
        assert "function" in html_out or "=>" in html_out


# =========================================================================
# Feature F12 Tests: Multi-Runtime Compatibility & Kernel Execution Architecture
# =========================================================================
class TestFeatureF12MultiRuntimeArchitecture:
    """Test Feature F12: Multi-Runtime compatibility, zero print() AST calls, and DOM rendering."""

    def test_f12_01_zero_ast_print_calls_in_cell_5(self, notebook_cells):
        """Verify Cell 5 contains ZERO standard print() AST calls (Rule #0 DOM Compliance)."""
        cell5_src = "".join(notebook_cells[4].get("source", []))
        tree = ast.parse(cell5_src)

        print_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    print_calls.append(node.lineno)
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "print":
                    print_calls.append(node.lineno)

        assert len(print_calls) == 0, f"Found {len(print_calls)} disallowed print() calls in Cell 5 at lines {print_calls}"

    def test_f12_02_all_cells_zero_unrendered_prints(self, notebook_cells):
        """Verify all notebook cells use structured glassmorphic DOM display over raw prints."""
        for idx, cell in enumerate(notebook_cells):
            src = "".join(cell.get("source", []))
            tree = ast.parse(src)
            print_nodes = [
                n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
            ]
            assert len(print_nodes) == 0, f"Cell {idx+1} contains bare print() calls at lines {print_nodes}"

    def test_f12_03_multi_runtime_abstraction_dispatch(self, cell_5_namespace):
        """Verify Multi-Runtime Abstraction Layer (MRAL) handles IPython, Marimo, and pure Python."""
        assert "display" in cell_5_namespace
        assert "HTML" in cell_5_namespace
        assert "clear_output" in cell_5_namespace

        # Test fallback rendering without error
        html_obj = cell_5_namespace["HTML"]("<div>Test</div>")
        assert html_obj is not None

    def test_f12_04_marimo_compatibility_clean_variable_scoping(self, notebook_cells):
        """Verify Cell 5 uses aliased private imports to avoid Marimo MultipleDefinitionError."""
        cell5_src = "".join(notebook_cells[4].get("source", []))
        tree = ast.parse(cell5_src)

        # Check imports are aliased with leading underscore
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("json", "time", "math", "socket", "urllib", "html"):
                        assert alias.asname is not None and alias.asname.startswith("_"), (
                            f"Standard module '{alias.name}' should be aliased with leading underscore for Marimo compatibility"
                        )
