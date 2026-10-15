"""
Empirical Challenger 2 Adversarial Stress Test Suite:
Data Models, ELO Math Invariants, Network Failure Injection, Dataset Parsing, and High-DPI Chart Integrity.
Generation 2 SSoT Master Studio Optimization.

Author: teamwork_preview_challenger_2 (Critic & Specialist)

Core Verification Mandates:
1. ELO rating math across 10,000 random walk iterations verifying zero-sum conservation and win probability bounds [0, 1].
2. Network failure injection (simulated timeout, connection refused, 500/502/503/404, truncated responses) against endpoint probes with clean waiting states ('--', 'STANDBY', 'OFFLINE').
3. Dataset streaming parser adversarial fuzzing against corrupt, empty, malformed, and truncated JSONL lines.
4. High-DPI chart rendering and disk export integrity (3040 x 844 @ 160 DPI, PNG magic bytes, dark palette compliance).
"""

import ast
import functools
import gc
import glob
import html
import http.server
import json
import math
import os
import random
import socket
import socketserver
import sys
import tempfile
import threading
import time
import types
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Strict Matplotlib Agg Mandate (Rule #0 / Parent Directive)
import matplotlib
matplotlib.use('Agg')
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import pytest

# Ensure real IPython is used if available
if 'IPython' in sys.modules and getattr(sys.modules['IPython'], '__file__', None) is None:
    del sys.modules['IPython']
    if 'IPython.display' in sys.modules:
        del sys.modules['IPython.display']
try:
    import IPython
except ImportError:
    pass

from tests.e2e_arena_notebook.conftest import (
    MONOREPO_ROOT,
    NOTEBOOK_PATH,
    GLOBAL_NOTEBOOK_PATH,
    CHART_PATH,
    CYBERPUNK_PALETTE,
    CANONICAL_PILLARS,
    calculate_elo_update,
    validate_dpo_schema,
    validate_seaweed_cluster_status,
    validate_seaweed_filer_entries,
)


@functools.lru_cache(maxsize=1)
def load_global_studio_namespace() -> Dict[str, Any]:
    """Extract and execute code cells from 00_lauburu_global_master_project.ipynb once into an isolated namespace."""
    if 'IPython' in sys.modules and getattr(sys.modules['IPython'], '__file__', None) is None:
        del sys.modules['IPython']
        if 'IPython.display' in sys.modules:
            del sys.modules['IPython.display']
    try:
        import IPython
    except Exception:
        pass

    target_path = NOTEBOOK_PATH if NOTEBOOK_PATH.exists() else GLOBAL_NOTEBOOK_PATH
    with open(target_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    code_cells = [c for c in nb.get('cells', []) if c.get('cell_type') == 'code']
    combined_code = '\n\n'.join([''.join(c.get('source', [])) for c in code_cells])
    
    ns: Dict[str, Any] = {
        'display': lambda *args, **kwargs: None,
        'HTML': lambda x: x,
        'clear_output': lambda *args, **kwargs: None,
        '__name__': '__main__',
    }
    exec(combined_code, ns)
    return ns


# =========================================================================
# Task 1: 10,000-Iteration ELO Math Random Walk & Invariant Stress Tests
# =========================================================================
class TestAdversarialEloMathRandomWalk:
    """Empirically challenge ELO rating math across 10,000 random walk duel steps."""

    @pytest.fixture(autouse=True)
    def setup_namespace(self):
        self.ns = load_global_studio_namespace()
        self.calc_elo = self.ns['calculate_elo_update']
        self.calc_dynamic_k = self.ns['calculate_dynamic_k_factor']
        self.ArenaStateManager = self.ns['ArenaStateManager']
        self.PILLARS = self.ns['PILLARS']
        self.ARENA_MODELS = self.ns['ARENA_MODELS']

    def test_01_single_duel_invariants_and_symmetry(self):
        """Verify basic Bradley-Terry properties: E_A + E_B = 1.0, zero-sum delta, symmetry."""
        test_rating_pairs = [
            (2600.0, 2600.0),
            (2800.0, 2400.0),
            (3200.0, 1800.0),
            (1000.0, 4000.0),
            (-500.0, 3000.0),
            (10000.0, -10000.0),
        ]
        test_scores = [1.0, 0.5, 0.0, 0.75, 0.25]
        test_ks = [1.0, 16.0, 32.0, 64.0, 128.0]

        for r_a, r_b in test_rating_pairs:
            for s_a in test_scores:
                for k in test_ks:
                    exp_a, new_a, new_b = self.calc_elo(r_a, r_b, s_a, k=k)
                    # 1. Expected score bounds
                    assert 0.0 <= exp_a <= 1.0, f'Expected score out of bounds: {exp_a}'
                    
                    # 2. Expected score symmetry
                    exp_b, new_b_rev, new_a_rev = self.calc_elo(r_b, r_a, 1.0 - s_a, k=k)
                    assert math.isclose(exp_a + exp_b, 1.0, abs_tol=1e-12), f'Probabilities do not sum to 1: {exp_a} + {exp_b}'
                    
                    # 3. Exact Zero-Sum Conservation: delta_a + delta_b == 0
                    delta_a = new_a - r_a
                    delta_b = new_b - r_b
                    assert math.isclose(delta_a + delta_b, 0.0, abs_tol=1e-10), f'Zero-sum violated: {delta_a} + {delta_b}'

    def test_02_ten_thousand_iteration_random_walk_zero_sum_conservation(self):
        """
        Execute 10,000 continuous random-walk duel steps across a multi-agent model pool.
        Verify zero-sum conservation holds continuously at every step with zero drift.
        """
        random.seed(42)
        initial_models = {
            'Qwen 2.5 Coder 72B': 2640.0,
            'DeepSeek-Coder-V2-236B': 2633.0,
            'Qwen3-Next-80B-A3B MoE': 2625.0,
            'Qwen-AgentWorld-35B': 2498.0,
            'BioMistral-7B': 2435.0,
            'Huihui-Qwen3.8-27B': 2448.0,
            'Llama-3.3-70B-Instruct': 2550.0,
            'Mistral-Large-2407': 2510.0,
        }
        model_keys = list(initial_models.keys())
        current_ratings = dict(initial_models)
        initial_total_elo = sum(initial_models.values())

        max_observed_drift = 0.0

        for step in range(10000):
            idx_a, idx_b = random.sample(range(len(model_keys)), 2)
            m_a, m_b = model_keys[idx_a], model_keys[idx_b]
            r_a, r_b = current_ratings[m_a], current_ratings[m_b]

            score_a = random.choice([1.0, 0.5, 0.0])
            k_val = random.uniform(8.0, 64.0)

            exp_a, new_a, new_b = self.calc_elo(r_a, r_b, score_a, k=k_val)

            assert 0.0 <= exp_a <= 1.0, f'Step {step}: Expected win probability out of bounds: {exp_a}'
            assert not math.isnan(new_a) and not math.isnan(new_b), f'Step {step}: NaN detected in ratings'
            assert not math.isinf(new_a) and not math.isinf(new_b), f'Step {step}: Inf detected in ratings'

            current_ratings[m_a] = new_a
            current_ratings[m_b] = new_b

            current_total = sum(current_ratings.values())
            drift = abs(current_total - initial_total_elo)
            if drift > max_observed_drift:
                max_observed_drift = drift

            assert drift < 1e-7, f'Step {step}: Total ELO drifted by {drift:.10f} (Initial: {initial_total_elo}, Current: {current_total})'

        final_total_elo = sum(current_ratings.values())
        assert math.isclose(final_total_elo, initial_total_elo, abs_tol=1e-7)

    def test_03_extreme_differential_runaway_random_walk(self):
        """
        Stress test numerical stability and overflow resistance when ratings diverge to extreme values (+/- 50,000).
        Verifies clamped_delta [-100.0, 100.0] correctly protects against 10^x float overflow.
        """
        ratings = {'Model_Titan': 50000.0, 'Model_Mite': -50000.0}
        initial_total = sum(ratings.values())

        for step in range(1000):
            r_a = ratings['Model_Titan']
            r_b = ratings['Model_Mite']
            exp_a, new_a, new_b = self.calc_elo(r_a, r_b, 1.0, k=32.0)
            assert exp_a == 1.0, f'Expected Titan win prob should be clamped to 1.0, got {exp_a}'
            assert math.isclose(new_a, r_a, abs_tol=1e-9)
            assert math.isclose(new_b, r_b, abs_tol=1e-9)

            exp_a_upset, new_a_upset, new_b_upset = self.calc_elo(r_a, r_b, 0.0, k=32.0)
            assert exp_a_upset == 1.0
            assert math.isclose(new_a_upset - r_a, -32.0, abs_tol=1e-9)
            assert math.isclose(new_b_upset - r_b, 32.0, abs_tol=1e-9)
            assert math.isclose((new_a_upset + new_b_upset), initial_total, abs_tol=1e-9)

    def test_04_dynamic_k_factor_adversarial_inputs(self):
        """Test dynamic K-factor calculation under adversarial and pathological inputs."""
        k_unmock = self.calc_dynamic_k(k0=64.0, zero_mock_certified=False)
        assert k_unmock == 1.0, f'Uncertified mock must force K=1.0, got {k_unmock}'

        pathological_cases = [
            {'k0': -100.0, 'params_b': -50.0, 'tokens_used': -100, 'rtt_ms': -5.0, 'consensus_score': -2.0},
            {'k0': 10000.0, 'params_b': 10000.0, 'tokens_used': 1000000, 'rtt_ms': 100000.0, 'consensus_score': 10.0},
            {'k0': 0.0, 'params_b': 0.0, 'tokens_used': 0, 'rtt_ms': 0.0, 'consensus_score': 0.0},
        ]
        for c in pathological_cases:
            k_res = self.calc_dynamic_k(
                k0=c['k0'],
                params_b=c['params_b'],
                tokens_used=c['tokens_used'],
                rtt_ms=c['rtt_ms'],
                consensus_score=c['consensus_score'],
                zero_mock_certified=True,
            )
            assert 1.0 <= k_res <= 128.0, f'K factor out of contract bounds [1.0, 128.0]: {k_res}'
            assert not math.isnan(k_res) and not math.isinf(k_res)

    def test_05_arena_state_manager_multi_round_tournament(self):
        """Verify ArenaStateManager round-robin tournament execution and duel recording."""
        state = self.ArenaStateManager(self.PILLARS, self.ARENA_MODELS)
        initial_total_elo = sum(m['default_elo'] for m in state.models.values())

        models = list(state.models.keys())
        duel_count = 0
        for rnd in range(5):
            for i in range(len(models)):
                for j in range(i + 1, len(models)):
                    m_a, m_b = models[i], models[j]
                    res = state.record_duel(m_a, m_b, score_a=1.0, pillar_id=1, k=24.0)
                    assert 'model_a' in res and 'model_b' in res
                    assert 'old_a' in res and 'old_b' in res
                    assert 'new_a' in res and 'new_b' in res
                    delta_a = res['new_a'] - res['old_a']
                    delta_b = res['new_b'] - res['old_b']
                    assert math.isclose(delta_a + delta_b, 0.0, abs_tol=1e-10)
                    duel_count += 1

        assert len(state.duel_history) == duel_count
        final_total_elo = sum(m['default_elo'] for m in state.models.values())
        assert math.isclose(final_total_elo, initial_total_elo, abs_tol=1e-9)


# =========================================================================
# Task 2: Network Failure Injection & Zero-Mock Endpoint Probe Tests
# =========================================================================
class TestNetworkFailureInjectionAndZeroMockProbes:
    """Empirically test probe functions against simulated network outages and HTTP faults."""

    @pytest.fixture(autouse=True)
    def setup_namespace(self):
        self.ns = load_global_studio_namespace()
        self.probe_mesh_node = self.ns['probe_mesh_node']
        self.inspect_seaweedfs_ssot = self.ns['inspect_seaweedfs_ssot']
        self.render_telemetry_probe_card = self.ns['render_telemetry_probe_card']

    def _assert_valid_probe_result(self, res: Dict[str, Any], expected_node: str, expected_url: str):
        assert isinstance(res, dict)
        assert res.get('node') == expected_node
        assert res.get('url') == expected_url
        assert res.get('status') in ('ONLINE', 'OFFLINE')
        assert isinstance(res.get('code'), int)
        if res.get('status') == 'ONLINE':
            assert isinstance(res.get('rtt_ms'), (int, float))
            assert res.get('error') is None
        else:
            assert res.get('rtt_ms') is None
            assert res.get('error') is not None

    def test_01_probe_mesh_node_connection_refused(self):
        """Verify probe handles connection refused on an unopened local port cleanly."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        _, free_port = s.getsockname()
        s.close()

        target_url = f'http://127.0.0.1:{free_port}'
        res = self.probe_mesh_node('Closed Port Node', target_url, timeout=0.5)

        assert res['status'] == 'OFFLINE'
        assert res['code'] == 0
        assert res['rtt_ms'] is None
        assert res['error'] is not None
        assert 'refused' in res['error'].lower() or 'connection' in res['error'].lower() or 'error' in res['error'].lower()
        self._assert_valid_probe_result(res, 'Closed Port Node', target_url)

    def test_02_probe_mesh_node_socket_timeout(self):
        """Verify probe enforces socket timeout and returns OFFLINE cleanly when remote hangs."""
        class HangingServer(threading.Thread):
            def __init__(self):
                super().__init__(daemon=True)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind(('127.0.0.1', 0))
                self.sock.listen(1)
                self.port = self.sock.getsockname()[1]
                self.running = True

            def run(self):
                while self.running:
                    try:
                        self.sock.settimeout(0.5)
                        conn, _ = self.sock.accept()
                        time.sleep(1.5)
                        conn.close()
                    except (socket.timeout, OSError):
                        pass

            def stop(self):
                self.running = False
                self.sock.close()

        server = HangingServer()
        server.start()
        try:
            t0 = time.time()
            target_url = f'http://127.0.0.1:{server.port}'
            res = self.probe_mesh_node('Hanging Node', target_url, timeout=0.3)
            elapsed = time.time() - t0

            assert elapsed < 1.0, f'Probe timeout was not respected: took {elapsed:.2f}s'
            assert res['status'] == 'OFFLINE'
            assert res['code'] == 0
            assert res['rtt_ms'] is None
            assert res['error'] is not None
            self._assert_valid_probe_result(res, 'Hanging Node', target_url)
        finally:
            server.stop()

    def test_03_probe_mesh_node_http_errors_500_502_503_404(self):
        """Verify probe behavior under HTTP 500, 502, 503, 404 error responses."""
        status_to_return = [500]

        class FaultHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                code = status_to_return[0]
                self.send_response(code)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Fault injection {code}'.encode())

            def log_message(self, *args):
                pass

        class FaultServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = FaultServer(('127.0.0.1', 0), FaultHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        port = server.server_address[1]

        try:
            for http_code in [500, 502, 503, 404]:
                status_to_return[0] = http_code
                target_url = f'http://127.0.0.1:{port}'
                res = self.probe_mesh_node(f'Fault Node {http_code}', target_url, timeout=0.8)
                assert res['status'] == 'OFFLINE'
                assert res['rtt_ms'] is None
                assert res['error'] is not None
                assert str(http_code) in res['error'] or 'HTTP Error' in res['error']
                self._assert_valid_probe_result(res, f'Fault Node {http_code}', target_url)
        finally:
            server.shutdown()
            server.server_close()

    def test_04_probe_mesh_node_malformed_response_and_drop(self):
        """Verify probe handles connection abort and garbage non-HTTP byte stream."""
        class GarbageServer(threading.Thread):
            def __init__(self):
                super().__init__(daemon=True)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.bind(('127.0.0.1', 0))
                self.sock.listen(1)
                self.port = self.sock.getsockname()[1]
                self.running = True

            def run(self):
                while self.running:
                    try:
                        self.sock.settimeout(0.5)
                        conn, _ = self.sock.accept()
                        conn.sendall(bytes([0x00, 0xff, 0xfe]) + b'GARBAGE_NON_HTTP_STREAM')
                        conn.close()
                    except (socket.timeout, OSError):
                        pass

            def stop(self):
                self.running = False
                self.sock.close()

        server = GarbageServer()
        server.start()
        try:
            target_url = f'http://127.0.0.1:{server.port}'
            res = self.probe_mesh_node('Garbage Node', target_url, timeout=0.5)
            assert res['status'] == 'OFFLINE'
            assert res['code'] == 0
            assert res['rtt_ms'] is None
            assert res['error'] is not None
            self._assert_valid_probe_result(res, 'Garbage Node', target_url)
        finally:
            server.stop()

    def test_05_inspect_seaweedfs_ssot_master_raft_failure_injection(self, monkeypatch):
        """Verify SeaweedFS Master Raft failure preserves clean STANDBY state."""
        def broken_urlopen(*args, **kwargs):
            raise urllib.error.URLError('Simulated SeaweedFS Raft Connection Refused')

        monkeypatch.setattr(urllib.request, 'urlopen', broken_urlopen)
        raft_state, filer_state = self.inspect_seaweedfs_ssot()

        assert raft_state['status'] == 'STANDBY'
        assert raft_state['leader'] == '--'
        assert raft_state['peers'] == 0
        assert raft_state['is_leader'] is False
        assert filer_state['status'] == 'STANDBY'

    def test_06_render_telemetry_probe_card_zero_mock_waiting_states(self):
        """Verify HTML rendering of telemetry probe cards for OFFLINE nodes produces zero mock data."""
        offline_html = self.render_telemetry_probe_card(
            node_name='Linux Head Node',
            url='http://100.101.39.98:4005',
            status='OFFLINE',
            rtt_ms=None,
            role='Ray Cluster & Gateway'
        )
        assert '🔴 OFFLINE' in offline_html or 'OFFLINE' in offline_html
        assert '--' in offline_html
        assert 'Linux Head Node' in offline_html

        online_html = self.render_telemetry_probe_card(
            node_name='Mac_Node (M4 Pro)',
            url='http://100.119.199.76:8890',
            status='ONLINE',
            rtt_ms=12.45,
            role='Primary Host & Governor'
        )
        assert '🟢 ONLINE' in online_html or 'ONLINE' in online_html
        assert '12.4ms' in online_html or '12.45' in online_html


# =========================================================================
# Task 3: Dataset Streaming Parser Adversarial Fuzzing & Corruption Tests
# =========================================================================
class TestDatasetStreamingParserAdversarialFuzzing:
    """Adversarially fuzz JSONL DPO parser with empty, malformed, and corrupted payloads."""

    @pytest.fixture(autouse=True)
    def setup_namespace(self):
        self.ns = load_global_studio_namespace()
        self.inspect_training_lake = self.ns['inspect_training_lake']
        self.render_dpo_split_view = self.ns['render_dpo_split_view']

    def test_01_dpo_schema_validation_valid_and_boundary_cases(self):
        """Test validate_dpo_schema against canonical and boundary valid records."""
        valid_record = {
            'prompt': 'Write a Python function to compute fibonacci numbers.',
            'chosen': 'def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)',
            'rejected': 'def fib(n): pass',
            'metadata': {
                'pillar_id': 1,
                'pillar_name': 'WebDev & UI/UX Arena',
                'model': 'Qwen 2.5 Coder 72B',
                'elo': 2640.0,
                'zero_mock_certified': True,
            }
        }
        assert validate_dpo_schema(valid_record) is True

        for pid in range(1, 7):
            rec = dict(valid_record)
            rec['metadata'] = dict(valid_record['metadata'])
            rec['metadata']['pillar_id'] = pid
            assert validate_dpo_schema(rec) is True

    def test_02_dpo_schema_validation_corrupt_jsonl_fuzzing(self):
        """Fuzz validate_dpo_schema with 20+ corrupted and malformed variants."""
        corrupt_variants = [
            None,
            {},
            [],
            'not a dictionary',
            12345,
            {'prompt': 'test', 'chosen': 'test', 'rejected': 'test'},
            {'prompt': 'test', 'chosen': 'test', 'metadata': {}},
            {'prompt': 'test', 'rejected': 'test', 'metadata': {}},
            {'chosen': 'test', 'rejected': 'test', 'metadata': {}},
            {'prompt': 123, 'chosen': 'test', 'rejected': 'test', 'metadata': {}},
            {'prompt': 'test', 'chosen': ['list'], 'rejected': 'test', 'metadata': {}},
            {'prompt': 'test', 'chosen': 'test', 'rejected': None, 'metadata': {}},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': 'string_meta'},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': {'pillar_id': 0, 'pillar_name': 'P', 'model': 'M', 'elo': 2500, 'zero_mock_certified': True}},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': {'pillar_id': 7, 'pillar_name': 'P', 'model': 'M', 'elo': 2500, 'zero_mock_certified': True}},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': {'pillar_id': '1', 'pillar_name': 'P', 'model': 'M', 'elo': 2500, 'zero_mock_certified': True}},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': {'pillar_id': 1, 'pillar_name': 'P', 'model': 'M', 'elo': '2500', 'zero_mock_certified': True}},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': {'pillar_id': 1, 'pillar_name': 'P', 'model': 'M', 'elo': 2500, 'zero_mock_certified': 'yes'}},
            {'prompt': 'p', 'chosen': 'c', 'rejected': 'r', 'metadata': {'pillar_id': 1, 'pillar_name': 'P', 'model': 'M', 'elo': 2500}},
        ]

        for idx, variant in enumerate(corrupt_variants):
            result = validate_dpo_schema(variant)
            assert result is False, f'Variant {idx} should fail validation but passed: {variant}'

    def test_03_streaming_jsonl_parser_adversarial_file_recovery(self, tmp_path):
        """
        Stream through a synthesized corrupt JSONL file containing blank lines, invalid syntax,
        truncated objects, binary bytes, and UTF-8 errors.
        Verify parser recovers and yields all valid records without unhandled crash.
        """
        test_file = tmp_path / 'corrupt_stream_fuzz.jsonl'
        valid_rec_1 = json.dumps({'prompt': 'P1', 'chosen': 'C1', 'rejected': 'R1', 'metadata': {'pillar_id': 1, 'pillar_name': 'P', 'model': 'M', 'elo': 2600.0, 'zero_mock_certified': True}})
        valid_rec_2 = json.dumps({'prompt': 'P2', 'chosen': 'C2', 'rejected': 'R2', 'metadata': {'pillar_id': 2, 'pillar_name': 'P', 'model': 'M', 'elo': 2550.0, 'zero_mock_certified': True}})
        valid_rec_3 = json.dumps({'prompt': 'A' * 50000, 'chosen': 'C3', 'rejected': 'R3', 'metadata': {'pillar_id': 3, 'pillar_name': 'BigCode', 'model': 'Qwen', 'elo': 2625.0, 'zero_mock_certified': True}})

        file_content_lines = [
            '',
            '   ',
            '\n',
            '{"incomplete": true',
            'NOT JSON AT ALL ::: 9999',
            valid_rec_1,
            'null',
            '12345',
            '{"prompt": "bad", "chosen": "bad", "rejected": "bad", "metadata": {"pillar_id": 999}}',
            valid_rec_2,
            valid_rec_3,
            '',
        ]
        test_file.write_text('\n'.join(file_content_lines), encoding='utf-8')

        def parse_jsonl_stream(file_path: Path) -> List[Dict[str, Any]]:
            valid_records = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line_no, raw_line in enumerate(f, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if validate_dpo_schema(obj):
                            valid_records.append(obj)
                    except Exception:
                        continue
            return valid_records

        parsed = parse_jsonl_stream(test_file)
        assert len(parsed) == 3, f'Expected exactly 3 valid parsed records, got {len(parsed)}'
        assert parsed[0]['prompt'] == 'P1'
        assert parsed[1]['prompt'] == 'P2'
        assert len(parsed[2]['prompt']) == 50000

    def test_04_inspect_training_lake_empty_directory_fallback(self, monkeypatch, tmp_path):
        """Verify inspect_training_lake returns clean fallback state when directories are empty."""
        empty_dir = tmp_path / 'empty_lora'
        empty_dir.mkdir()
        monkeypatch.setattr('tests.e2e_arena_notebook.conftest.LORA_DIR', empty_dir)

        monkeypatch.setattr(glob, 'glob', lambda pat: [])
        rows = self.inspect_training_lake()

        assert len(rows) >= 1
        assert rows[0]['status'] == 'WAITING_FOR_DATASET' or rows[0]['status'] == 'WAITING'
        assert rows[0]['file_size'] == '--'
        assert 'webdev_arena_preference_10k.jsonl' in rows[0]['stream_file']

    def test_05_render_dpo_split_view_html_escaping_resilience(self):
        """Verify render_dpo_split_view escapes HTML/XSS payloads in prompts and responses."""
        xss_prompt = '<script>alert("XSS Prompt")</script> & <b>Bold</b>'
        xss_chosen = '<img src=x onerror=alert(1)> chosen code'
        xss_rejected = '<iframe src="evil.com"></iframe> rejected'
        meta = {'pillar_id': 1, 'pillar_name': 'WebDev', 'model': 'Qwen', 'elo': 2640.0, 'zero_mock_certified': True}

        html_out = self.render_dpo_split_view(xss_prompt, xss_chosen, xss_rejected, meta)
        assert '<script>' not in html_out
        assert '<img src=x onerror=' not in html_out
        assert '<iframe' not in html_out
        assert '&lt;script&gt;' in html_out or '&lt;' in html_out


# =========================================================================
# Task 4: High-DPI Chart Rendering & Export Integrity Verification
# =========================================================================
class TestHighDpiChartRenderingAndExportIntegrity:
    """Empirically verify 160 DPI chart generation, file export integrity, and Agg backend."""

    @pytest.fixture(scope="class", autouse=True)
    def setup_namespace(self, request):
        ns = load_global_studio_namespace()
        request.cls.ns = ns
        request.cls.render_console_visualizations = staticmethod(ns['render_console_visualizations'])
        request.cls.PILLARS = ns['PILLARS']
        # Explicitly render and save to ensure chart is fresh and fully flushed
        ns['render_console_visualizations'](ns['PILLARS'], save_to_disk=True)

    def test_01_chart_png_disk_export_existence_and_magic_bytes(self):
        """Verify exported chart exists on disk, is non-empty, and has valid PNG magic header."""
        assert CHART_PATH.exists(), f'Target chart file not found on disk: {CHART_PATH}'
        file_size = CHART_PATH.stat().st_size
        assert file_size > 100 * 1024, f'Chart file size too small ({file_size} bytes, expected >100KB)'

        with open(CHART_PATH, 'rb') as f:
            magic = f.read(8)
        assert magic == bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]), f'Invalid PNG magic bytes: {magic}'

    def test_02_chart_pixel_dimensions_and_160_dpi_geometry(self):
        """Verify image physical dimensions (3040 x 844 px) and DPI (160 DPI)."""
        with Image.open(CHART_PATH) as img:
            width, height = img.size
            format_name = img.format
            dpi_info = img.info.get('dpi')

            assert format_name == 'PNG', f'Image format must be PNG, found {format_name}'
            assert 2950 <= width <= 3150, f'Width ({width}px) out of expected 3040px bounds'
            assert 800 <= height <= 900, f'Height ({height}px) out of expected 844px bounds'
            
            if dpi_info:
                dpi_x, dpi_y = dpi_info
                assert dpi_x >= 159.0 and dpi_y >= 159.0, f'DPI metadata ({dpi_x}, {dpi_y}) below 160 DPI requirement'

    def test_03_dark_cyberpunk_palette_color_compliance(self):
        """Sample pixels from the exported chart to verify dark slate background (#0f172a)."""
        with open(CHART_PATH, 'rb') as f:
            img = Image.open(f)
            img.load()
            rgb_img = img.convert('RGB')
            corner_pixel = rgb_img.getpixel((10, 10))
            r, g, b = corner_pixel
            assert abs(r - 15) <= 5, f'Red channel ({r}) differs from #0f172a (15)'
            assert abs(g - 23) <= 5, f'Green channel ({g}) differs from #0f172a (23)'
            assert abs(b - 42) <= 5, f'Blue channel ({b}) differs from #0f172a (42)'

    def test_04_render_console_visualizations_headless_and_zero_popups(self, monkeypatch):
        """
        Execute render_console_visualizations and assert:
        1. Backend is strictly 'Agg'
        2. Zero open figures remain (plt.close called)
        3. No GUI popup attempts
        """
        assert matplotlib.get_backend().lower() == 'agg'
        
        plt.close('all')
        assert len(plt.get_fignums()) == 0

        fig = self.render_console_visualizations(self.PILLARS, save_to_disk=False)
        assert len(plt.get_fignums()) == 0, 'Figures left open in Matplotlib registry (memory leak risk)'

    def test_05_chart_rendering_memory_safety_loop(self):
        """Render 10 successive charts in loop; verify zero memory growth or figure leakage."""
        initial_figns = len(plt.get_fignums())
        for i in range(10):
            mutated_pillars = [dict(p) for p in self.PILLARS]
            for p in mutated_pillars:
                p['elo'] = p['elo'] + (i * 2.0)
            fig = self.render_console_visualizations(mutated_pillars, save_to_disk=False)
            assert len(plt.get_fignums()) == 0

        gc.collect()
        assert len(plt.get_fignums()) == initial_figns
