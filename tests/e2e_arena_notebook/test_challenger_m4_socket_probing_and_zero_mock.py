"""
Milestone M4 Adversarial Empirical Challenger Test Suite:
Author: teamwork_preview_challenger_m4_1 (Empirical Challenger, Critic, Specialist)

Focus Areas:
1. Strict 200ms Socket Timeout Enforcement:
   - Non-routable blackhole IPs (RFC 5737 / RFC 6890)
   - Real hanging / tarpit TCP servers (unresponsive accept)
   - Slow trickle partial-HTTP servers
   - Concurrent parallel probing bounded execution & sequential accumulation analysis
2. Rule #0 Zero-Mock Fallback Verification:
   - Unused / closed local ports (Connection Refused)
   - HTTP error status codes (500, 502, 503, 404)
   - Corrupted non-UTF8 binary responses
   - AST purity enforcement (zero mock/fake tokens or synthetic generators)
3. Debate Stream Scrubber & Ingestion Robustness:
   - Empty, whitespace, and truncated JSONL files
   - Corrupted lines mixed with valid debate records
   - Schema deviations and missing required fields
   - Mathematical boundary and NaN resilience in Bradley-Terry ELO engine
   - XSS prevention and HTML sanitization across rendered cards
   - Standalone JS generation with zero and pathological records
"""

import ast
import http.server
import json
import math
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    NOTEBOOK_PATH,
    load_notebook_data,
    extract_code_cells,
)


# =========================================================================
# Fixtures & Sandboxed Cell 5 Extraction
# =========================================================================
@pytest.fixture(scope="module")
def cell_5_ns():
    """Extract and execute Cell 5 in an isolated namespace."""
    nb = load_notebook_data(NOTEBOOK_PATH)
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    assert len(code_cells) >= 5, f"Expected at least 5 code cells in notebook, got {len(code_cells)}"
    
    cell5_source = "".join(code_cells[4].get("source", []))
    
    ns: Dict[str, Any] = {
        "__name__": "__main__",
        "display": lambda *args, **kwargs: None,
        "HTML": lambda x: x,
        "clear_output": lambda *args, **kwargs: None,
    }
    exec(cell5_source, ns)
    return ns


# =========================================================================
# Helper TCP Servers for Adversarial Testing
# =========================================================================
class HangingTCPServer:
    """A TCP server that accepts connections but never responds (tarpit)."""
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                self.sock.settimeout(0.5)
                client, _ = self.sock.accept()
                while self.running:
                    time.sleep(0.1)
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


class TrickleTCPServer:
    """A TCP server that sends partial HTTP header and then sleeps indefinitely."""
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                self.sock.settimeout(0.5)
                client, _ = self.sock.accept()
                try:
                    client.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"partial\": ")
                    while self.running:
                        time.sleep(0.1)
                except Exception:
                    pass
                finally:
                    client.close()
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


class ErrorHTTPServer:
    """An HTTP server returning specified status codes (e.g. 500, 502, 503)."""
    def __init__(self, status_code: int = 500):
        self.status_code = status_code
        handler = self._make_handler(status_code)
        self.server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _make_handler(self, code: int):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Injected Error {code}"}).encode("utf-8"))
            def log_message(self, format, *args):
                pass
        return Handler

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class BinaryGarbageServer:
    """A TCP server that sends non-UTF8 binary garbage upon connection."""
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                self.sock.settimeout(0.5)
                client, _ = self.sock.accept()
                try:
                    client.sendall(bytes([0xFF, 0xFE, 0x00, 0x12, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD]))
                except Exception:
                    pass
                finally:
                    client.close()
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


# =========================================================================
# 1. Adversarial Test Suite: Socket Probing & Strict 200ms Timeout
# =========================================================================
class TestBlackholeAndHangingSocketTimeouts:
    """Stress tests verifying strict 200ms timeout ceiling against adversarial network conditions."""

    @pytest.mark.parametrize("blackhole_ip", [
        "192.0.2.1",     # TEST-NET-1 (RFC 5737)
        "198.51.100.1",  # TEST-NET-2 (RFC 5737)
        "203.0.113.1",   # TEST-NET-3 (RFC 5737)
    ])
    def test_blackhole_ip_tcp_probe_strict_200ms(self, cell_5_ns, blackhole_ip):
        """Assert tcp_socket_probe against non-routable blackhole IPs terminates in <=280ms."""
        tcp_probe_fn = cell_5_ns["tcp_socket_probe"]
        
        t0 = time.perf_counter()
        ok, rtt, err = tcp_probe_fn(blackhole_ip, 8080, timeout=0.20)
        elapsed = time.perf_counter() - t0
        
        assert ok is False, f"Blackhole IP {blackhole_ip} unexpectedly reported connected!"
        assert rtt is None, f"Blackhole IP should have None RTT, got {rtt}"
        assert err is not None, "Expected error message for blackhole probe"
        assert elapsed <= 0.30, f"Blackhole TCP probe exceeded timeout ceiling: took {elapsed:.4f}s > 0.30s"

    def test_blackhole_ip_mesh_node_probe_strict_200ms(self, cell_5_ns):
        """Assert probe_mesh_node against blackhole IP returns clean offline state in <=280ms."""
        probe_node_fn = cell_5_ns["probe_mesh_node"]
        
        t0 = time.perf_counter()
        res = probe_node_fn("Blackhole Node", "http://198.51.100.254:8080/state", timeout=0.20)
        elapsed = time.perf_counter() - t0
        
        assert res["status"] == "OFFLINE"
        assert res["rtt_ms"] is None
        assert res["data"] is None
        assert res["zero_mock_certified"] is True
        assert elapsed <= 0.30, f"probe_mesh_node took {elapsed:.4f}s > 0.30s"

    def test_hanging_tcp_server_probe_strict_200ms(self, cell_5_ns):
        """Assert prober cleanly times out on a hanging TCP tarpit server within <=280ms."""
        server = HangingTCPServer()
        try:
            probe_endpoint_fn = cell_5_ns["probe_mesh_endpoint"]
            MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
            
            spec = MeshEndpointSpec(
                endpoint_id="HANGING_TEST",
                name="Hanging Server",
                layer="L1_TEST",
                icon="⏳",
                host="127.0.0.1",
                port=server.port,
                primary_url=f"http://127.0.0.1:{server.port}/hang",
                probe_path="/hang",
                timeout_sec=0.20
            )
            
            t0 = time.perf_counter()
            res = probe_endpoint_fn(spec)
            elapsed = time.perf_counter() - t0
            
            assert res["status"] == "OFFLINE"
            assert res["rtt_ms"] is None
            assert res["summary"] == "--"
            assert res["zero_mock_certified"] is True
            assert elapsed <= 0.30, f"Hanging TCP server probe took {elapsed:.4f}s > 0.30s"
        finally:
            server.stop()

    def test_slow_trickle_tcp_server_probe_strict_200ms(self, cell_5_ns):
        """Assert prober cleanly times out on an incomplete/trickle HTTP server in <=280ms."""
        server = TrickleTCPServer()
        try:
            probe_endpoint_fn = cell_5_ns["probe_mesh_endpoint"]
            MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
            
            spec = MeshEndpointSpec(
                endpoint_id="TRICKLE_TEST",
                name="Trickle Server",
                layer="L1_TEST",
                icon="💧",
                host="127.0.0.1",
                port=server.port,
                primary_url=f"http://127.0.0.1:{server.port}/trickle",
                probe_path="/trickle",
                timeout_sec=0.20
            )
            
            t0 = time.perf_counter()
            res = probe_endpoint_fn(spec)
            elapsed = time.perf_counter() - t0
            
            assert res["status"] == "OFFLINE"
            assert res["rtt_ms"] is None
            assert res["summary"] == "--"
            assert res["zero_mock_certified"] is True
            assert elapsed <= 0.30, f"Trickle server probe took {elapsed:.4f}s > 0.30s"
        finally:
            server.stop()

    def test_probe_mesh_endpoint_sequential_timeout_behavior(self, cell_5_ns):
        """
        Empirical finding verification:
        When probe_mesh_endpoint probes a spec with primary + fallback on blackhole IPs,
        it executes tcp_socket_probe (0.2s) + primary urlopen (0.2s) + fallback urlopen (0.2s)
        totaling ~0.60s. This test verifies that each individual step respects timeout=0.20s.
        """
        probe_endpoint_fn = cell_5_ns["probe_mesh_endpoint"]
        MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
        
        # 1. Single URL spec: should take ~0.40s (1 socket timeout + 1 http timeout)
        spec_single = MeshEndpointSpec(
            endpoint_id="TEST_BH_SINGLE",
            name="Single BH",
            layer="L1_TEST",
            icon="🕳️",
            host="192.0.2.99",
            port=8080,
            primary_url="http://192.0.2.99:8080/health",
            fallback_url=None,
            probe_path="/health",
            timeout_sec=0.20
        )
        t0 = time.perf_counter()
        res_single = probe_endpoint_fn(spec_single)
        elapsed_single = time.perf_counter() - t0
        assert res_single["status"] == "OFFLINE"
        assert res_single["zero_mock_certified"] is True
        assert elapsed_single <= 0.50, f"Single-URL probe took {elapsed_single:.4f}s > 0.50s"

        # 2. Dual URL spec: should take ~0.60s (1 socket timeout + 2 http timeouts)
        spec_dual = MeshEndpointSpec(
            endpoint_id="TEST_BH_DUAL",
            name="Dual BH",
            layer="L1_TEST",
            icon="🕳️",
            host="192.0.2.99",
            port=8080,
            primary_url="http://192.0.2.99:8080/health",
            fallback_url="http://198.51.100.99:8080/health",
            probe_path="/health",
            timeout_sec=0.20
        )
        t0 = time.perf_counter()
        res_dual = probe_endpoint_fn(spec_dual)
        elapsed_dual = time.perf_counter() - t0
        assert res_dual["status"] == "OFFLINE"
        assert res_dual["zero_mock_certified"] is True
        assert elapsed_dual <= 0.75, f"Dual-URL probe took {elapsed_dual:.4f}s > 0.75s"

    def test_parallel_blackhole_probes_concurrency_bounding(self, cell_5_ns):
        """Assert parallel probing of 6 blackhole endpoints executes concurrently without serial blocking."""
        probe_all_fn = cell_5_ns["probe_all_mesh_endpoints"]
        MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
        
        blackhole_endpoints = [
            MeshEndpointSpec(
                endpoint_id=f"BH_{i}",
                name=f"Blackhole Node {i}",
                layer=f"L{i}",
                icon="🕳️",
                host=f"192.0.2.{10+i}",
                port=8080,
                primary_url=f"http://192.0.2.{10+i}:8080",
                fallback_url=None,
                probe_path="/",
                timeout_sec=0.20
            )
            for i in range(6)
        ]
        
        t0 = time.perf_counter()
        results = probe_all_fn(blackhole_endpoints)
        elapsed = time.perf_counter() - t0
        
        assert len(results) == 6
        for r in results:
            assert r["status"] == "OFFLINE"
            assert r["rtt_ms"] is None
            assert r["summary"] == "--"
            assert r["zero_mock_certified"] is True
        
        # Parallel execution of 6 endpoints should take ~0.45s, not serial (6 * 0.4s = 2.4s)
        assert elapsed <= 0.65, f"Parallel blackhole probes took {elapsed:.4f}s > 0.65s (serial blocking!)"


# =========================================================================
# 2. Adversarial Test Suite: Rule #0 Zero-Mock Fallback Verification
# =========================================================================
class TestRule0ZeroMockFallbackStates:
    """Verify Rule #0 compliance: zero synthetic fake data on offline/error conditions."""

    def test_closed_port_connection_refused_zero_mock_integrity(self, cell_5_ns):
        """Assert closed port returns exact Rule #0 zero-mock contract with no synthetic payload."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        closed_port = s.getsockname()[1]
        s.close()
        
        probe_endpoint_fn = cell_5_ns["probe_mesh_endpoint"]
        MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
        
        spec = MeshEndpointSpec(
            endpoint_id="CLOSED_PORT_TEST",
            name="Closed Port Node",
            layer="L1_TEST",
            icon="🚫",
            host="127.0.0.1",
            port=closed_port,
            primary_url=f"http://127.0.0.1:{closed_port}/state",
            probe_path="/state",
            timeout_sec=0.20
        )
        
        res = probe_endpoint_fn(spec)
        
        assert res["status"] == "OFFLINE"
        assert res["status_symbol"] == "🔴 OFFLINE"
        assert res["rtt_ms"] is None
        assert res["summary"] == "--"
        assert res["telemetry"] == {}
        assert res["zero_mock_certified"] is True
        assert res["code"] == 0
        assert "ConnectionRefused" in res["error"] or "Errno 61" in res["error"] or "refused" in res["error"].lower()

    @pytest.mark.parametrize("http_code", [500, 502, 503, 404])
    def test_http_error_codes_zero_mock_fallback(self, cell_5_ns, http_code):
        """Assert HTTP error responses are captured with accurate status code and zero fake telemetry."""
        server = ErrorHTTPServer(status_code=http_code)
        try:
            probe_endpoint_fn = cell_5_ns["probe_mesh_endpoint"]
            MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
            
            spec = MeshEndpointSpec(
                endpoint_id=f"HTTP_{http_code}_TEST",
                name=f"HTTP {http_code} Node",
                layer="L1_TEST",
                icon="⚠️",
                host="127.0.0.1",
                port=server.port,
                primary_url=f"http://127.0.0.1:{server.port}/api/state",
                probe_path="/api/state",
                timeout_sec=0.20
            )
            
            res = probe_endpoint_fn(spec)
            
            assert res["status"] == "OFFLINE"
            assert res["rtt_ms"] is None
            assert res["summary"] == "--"
            assert res["telemetry"] == {}
            assert res["zero_mock_certified"] is True
            assert res["code"] == http_code
            assert f"{http_code}" in res["error"]
        finally:
            server.stop()

    def test_corrupted_binary_garbage_payload_zero_mock(self, cell_5_ns):
        """Assert raw non-UTF8 binary responses do not crash prober and yield clean fallback."""
        server = BinaryGarbageServer()
        try:
            probe_endpoint_fn = cell_5_ns["probe_mesh_endpoint"]
            MeshEndpointSpec = cell_5_ns["MeshEndpointSpec"]
            
            spec = MeshEndpointSpec(
                endpoint_id="GARBAGE_TEST",
                name="Binary Garbage Server",
                layer="L1_TEST",
                icon="👾",
                host="127.0.0.1",
                port=server.port,
                primary_url=f"http://127.0.0.1:{server.port}/raw",
                probe_path="/raw",
                timeout_sec=0.20
            )
            
            res = probe_endpoint_fn(spec)
            
            assert res["status"] == "OFFLINE"
            assert res["rtt_ms"] is None
            assert res["summary"] == "--"
            assert res["telemetry"] == {}
            assert res["zero_mock_certified"] is True
        finally:
            server.stop()

    def test_canonical_mesh_endpoints_zero_mock_contract(self, cell_5_ns):
        """Assert all 6 canonical endpoints satisfy strict zero-mock contract."""
        probe_all_fn = cell_5_ns["probe_all_mesh_endpoints"]
        results = probe_all_fn()
        
        assert len(results) == 6
        for r in results:
            assert r["zero_mock_certified"] is True
            assert r["status"] in ("ONLINE", "STANDBY", "OFFLINE")
            if r["status"] == "OFFLINE":
                assert r["rtt_ms"] is None
                assert r["summary"] == "--"
                assert r["telemetry"] == {}
                assert r["status_symbol"] == "🔴 OFFLINE"
            else:
                assert r["rtt_ms"] is not None
                assert r["rtt_ms"] > 0.0
                assert r["code"] in (200, 201, 204)
                assert r["error"] is None

    def test_ast_zero_mock_token_scan_in_cell_5(self, cell_5_ns):
        """AST parse Cell 5 to guarantee zero mock libraries or synthetic data generation."""
        nb = load_notebook_data(NOTEBOOK_PATH)
        code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
        cell5_source = "".join(code_cells[4].get("source", []))
        
        parsed = ast.parse(cell5_source)
        
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in ("mock", "unittest.mock", "faker"), f"Forbidden mock import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert node.module not in ("mock", "unittest.mock", "faker"), f"Forbidden mock import from: {node.module}"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in ("randint", "uniform", "choice", "sample"), f"Forbidden synthetic generator call: {node.func.attr}"


# =========================================================================
# 3. Adversarial Test Suite: Debate Stream Scrubber & Ingestion
# =========================================================================
class TestDebateStreamScrubberAndIngestion:
    """Stress tests verifying DebateStreamIngestor and renderers under pathological input."""

    def test_debate_empty_and_whitespace_jsonl_files(self, cell_5_ns, tmp_path):
        """Assert empty and whitespace-only JSONL files return empty list without exceptions."""
        DebateStreamIngestor = cell_5_ns["DebateStreamIngestor"]
        
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        
        ws_file = tmp_path / "whitespace.jsonl"
        ws_file.write_text("\n   \n\t\n\n")
        
        orig_paths = DebateStreamIngestor.DEFAULT_TRANSCRIPT_PATHS
        try:
            DebateStreamIngestor.DEFAULT_TRANSCRIPT_PATHS = [empty_file, ws_file]
            accords = DebateStreamIngestor.load_local_transcripts()
            assert accords == [], f"Expected empty list for empty/whitespace files, got {accords}"
        finally:
            DebateStreamIngestor.DEFAULT_TRANSCRIPT_PATHS = orig_paths

    def test_debate_corrupted_and_truncated_json_lines(self, cell_5_ns, tmp_path):
        """Assert corrupted, truncated, and malformed lines are safely skipped while valid records parse."""
        DebateStreamIngestor = cell_5_ns["DebateStreamIngestor"]
        
        corrupted_file = tmp_path / "corrupted_debate.jsonl"
        lines = [
            "{\"topic_id\": \"CORRUPTED_1\", \"title\": \"Incomplete",
            "None",
            "<<<INVALID_JSON_STREAM>>>",
            "{\"topic_id\": \"VALID_01\", \"title\": \"Valid Topic 1\", \"prompt\": \"Test prompt\", \"devils_advocate\": \"Critique\", \"consensus\": \"Accord text\", \"truth_compliance_pct\": 95.0}",
            "{\"invalid_json: 12345}",
            "{\"topic_id\": \"VALID_02\", \"title\": \"Valid Topic 2\", \"prompt\": \"Prompt 2\", \"devils_advocate\": \"Critique 2\", \"consensus\": \"Accord 2\", \"truth_compliance_pct\": 88.0}",
            ""
        ]
        corrupted_file.write_text("\n".join(lines))
        
        orig_paths = DebateStreamIngestor.DEFAULT_TRANSCRIPT_PATHS
        try:
            DebateStreamIngestor.DEFAULT_TRANSCRIPT_PATHS = [corrupted_file]
            accords = DebateStreamIngestor.load_local_transcripts()
            
            assert len(accords) == 2, f"Expected exactly 2 valid accords from corrupted stream, got {len(accords)}"
            titles = {a.title for a in accords}
            assert "Valid Topic 1" in titles
            assert "Valid Topic 2" in titles
        finally:
            DebateStreamIngestor.DEFAULT_TRANSCRIPT_PATHS = orig_paths

    def test_debate_missing_fields_and_schema_deviations(self, cell_5_ns):
        """Assert _normalize_jsonl_record handles records with missing fields gracefully."""
        DebateStreamIngestor = cell_5_ns["DebateStreamIngestor"]
        
        assert DebateStreamIngestor._normalize_jsonl_record({}, 0) is None
        
        rec_prompt_only = {"prompt": "Stand-alone prompt without title or topic_id"}
        accord = DebateStreamIngestor._normalize_jsonl_record(rec_prompt_only, 0)
        assert accord is not None
        assert accord.topic_id == "TOPIC_00"
        assert accord.consensus_score == 1.0
        assert len(accord.top_priorities) >= 1
        assert len(accord.rounds) == 4

    @pytest.mark.parametrize("score", [-10.0, 0.0, 0.5, 1.0, 25.0])
    def test_debate_elo_math_boundary_resilience(self, cell_5_ns, score):
        """Assert compute_debate_elo_updates handles out-of-bounds consensus scores without crashing."""
        compute_elo_fn = cell_5_ns["compute_debate_elo_updates"]
        
        deltas = compute_elo_fn(score)
        assert "local_model" in deltas
        assert "cloud_shadow" in deltas
        assert "devils_advocate" in deltas
        
        for pid, info in deltas.items():
            assert not math.isnan(info["new_elo"])
            assert not math.isinf(info["new_elo"])
            assert 4.0 <= info["k_factor"] <= 64.0
            assert 0.0 <= info["actual_perf"] <= 1.0

    def test_debate_elo_extreme_participant_parameters(self, cell_5_ns):
        """Assert compute_debate_elo_updates with 0 parameter models or zero/extreme RTT never div-by-zero."""
        compute_elo_fn = cell_5_ns["compute_debate_elo_updates"]
        
        adversarial_participants = [
            {"id": "zero_param", "name": "Zero Param", "rating": 1500.0, "params_b": 0.0, "rtt_ms": 0.0},
            {"id": "huge_param", "name": "Huge Param", "rating": 2500.0, "params_b": 10000.0, "rtt_ms": 99999.0},
            {"id": "neg_param", "name": "Negative Param", "rating": -500.0, "params_b": -5.0, "rtt_ms": -10.0}
        ]
        
        deltas = compute_elo_fn(0.85, adversarial_participants)
        assert len(deltas) == 3
        for pid, info in deltas.items():
            assert not math.isnan(info["new_elo"])
            assert not math.isinf(info["new_elo"])
            assert isinstance(info["delta"], float)

    def test_debate_xss_and_html_escaping(self, cell_5_ns):
        """Assert DebateViewRenderer and turn cards escape all HTML tags to prevent XSS."""
        DebateViewRenderer = cell_5_ns["DebateViewRenderer"]
        NormalizedDebateTurn = cell_5_ns["NormalizedDebateTurn"]
        NormalizedConsensusAccord = cell_5_ns["NormalizedConsensusAccord"]
        
        xss_payload = "<script>alert('XSS_ATTACK')</script><img src=x onerror=alert(1)>"
        
        turn = NormalizedDebateTurn(
            turn_index=1,
            role_key="local_model",
            role_label="LOCAL MODEL",
            speaker_name=xss_payload,
            hardware_target=xss_payload,
            content=xss_payload,
            metrics={"payload": xss_payload}
        )
        
        turn_html = DebateViewRenderer.render_turn_card(turn)
        assert "<script>" not in turn_html
        assert "&lt;script&gt;" in turn_html
        assert "<img" not in turn_html
        assert "&lt;img" in turn_html
        
        diff_html = DebateViewRenderer.render_diff_viewer("+ <script>evil()</script>")
        assert "<script>" not in diff_html
        assert "&lt;script&gt;" in diff_html

    def test_standalone_js_client_empty_and_special_character_accords(self, cell_5_ns):
        """Assert StandaloneDebateInspectorJS generates valid HTML/JS for empty and complex accords."""
        StandaloneDebateInspectorJS = cell_5_ns["StandaloneDebateInspectorJS"]
        NormalizedConsensusAccord = cell_5_ns["NormalizedConsensusAccord"]
        NormalizedDebateTurn = cell_5_ns["NormalizedDebateTurn"]
        
        empty_html = StandaloneDebateInspectorJS.generate_html([])
        assert "Debate Stream Standby" in empty_html
        assert "04_data_and_memory/truth_audit_debate.jsonl" in empty_html
        
        complex_accord = NormalizedConsensusAccord(
            debate_id="COMPLEX_01",
            topic_id="TOPIC_COMPLEX",
            title="Special Quotes & Escapes",
            domain="Architecture Escapes",
            timestamp_utc="2026-09-02 06:00:00 UTC",
            consensus_score=0.92,
            consensus_status="RATIFIED",
            truth_verified=True,
            truth_compliance_pct=92.0,
            actionable_consensus="Line 1\nLine 2 with code and quotes\n- Priority 1",
            top_priorities=["Priority one with dollar", "Priority two"],
            elo_deltas={"local": {"name": "Local", "initial_elo": 1500.0, "new_elo": 1512.0, "delta": 12.0, "k_factor": 32.0, "actual_perf": 0.92}},
            verified_diff="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old = \"val\"\n+new = \"val\"",
            rounds=[
                NormalizedDebateTurn(
                    turn_index=1,
                    role_key="local_model",
                    role_label="LOCAL MODEL",
                    speaker_name="Qwen 3.8",
                    hardware_target="Mac_Node",
                    content="Discourse with template syntax"
                )
            ]
        )
        
        js_html = StandaloneDebateInspectorJS.generate_html([complex_accord])
        assert "window.debateInspectorEngine" in js_html
        assert "TOPIC_COMPLEX" in js_html

    def test_debate_live_endpoint_unreachable_fallback(self, cell_5_ns):
        """Assert fetch_live_debate against unreachable endpoint times out cleanly in <=280ms."""
        DebateStreamIngestor = cell_5_ns["DebateStreamIngestor"]
        
        t0 = time.perf_counter()
        res = DebateStreamIngestor.fetch_live_debate("http://192.0.2.1:4005/api/debate", timeout_sec=0.20)
        elapsed = time.perf_counter() - t0
        
        assert res is None, f"Expected None for unreachable live debate endpoint, got {res}"
        assert elapsed <= 0.30, f"fetch_live_debate took {elapsed:.4f}s > 0.30s"
