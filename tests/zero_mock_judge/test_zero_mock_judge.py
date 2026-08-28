#!/usr/bin/env python3
"""
Zero-Mock Agent-as-Judge & Verification Suite Test Harness
==========================================================
Comprehensive tests validating that the Zero-Mock Static Judge,
Dynamic Runtime Judge, and Active Fault Injector accurately detect
all classes of synthetic mock data, while correctly certifying genuine
live implementations with zero false positives.
"""

import ast
import json
import math
import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import List, Dict, Any

# Ensure tests import correctly regardless of invocation cwd
try:
    from .zero_mock_static_judge import (
        ZeroMockStaticJudge,
        Violation,
        PythonAstJudge,
        JsTsScanner,
        CrossLanguageCommentJudge
    )
    from .zero_mock_dynamic_judge import (
        ZeroMockDynamicJudge,
        MetricSample,
        KernelInterfaceProbe
    )
    from .zero_mock_fault_injector import (
        ZeroMockFaultInjector,
        FaultSimulationServer,
        FaultInjectionResult
    )
    from .runner import ZeroMockMasterRunner
except ImportError:
    from zero_mock_static_judge import (
        ZeroMockStaticJudge,
        Violation,
        PythonAstJudge,
        JsTsScanner,
        CrossLanguageCommentJudge
    )
    from zero_mock_dynamic_judge import (
        ZeroMockDynamicJudge,
        MetricSample,
        KernelInterfaceProbe
    )
    from zero_mock_fault_injector import (
        ZeroMockFaultInjector,
        FaultSimulationServer,
        FaultInjectionResult
    )
    from runner import ZeroMockMasterRunner


class TestRule1HardcodedTelemetryLiterals(unittest.TestCase):
    """Tests detection of Rule 1: Hardcoded latency and bandwidth literals in objects/dictionaries."""

    def setUp(self):
        self.judge = ZeroMockStaticJudge(ignore_test_files=False)

    def test_detects_hardcoded_latency_string_in_js_fleet_array(self):
        js_code = textwrap.dedent("""
        const FLEET_DEVICES = [
          {
            id: "Mac_Node_Local",
            name: "Host Mac Mini M4",
            latency: "0.28ms (DMA)",
            status: "APPLIED"
          }
        ];
        """).strip()
        scanner = JsTsScanner("test_fleet.js", js_code)
        violations = scanner.scan()
        rule1_violations = [v for v in violations if v.rule_id == "ZM-JS-01"]
        self.assertTrue(len(rule1_violations) >= 1)
        self.assertIn("0.28ms (DMA)", rule1_violations[0].message)

    def test_detects_hardcoded_latency_string_in_python_dict(self):
        py_code = textwrap.dedent("""
        node_spec = {
            "id": "linux_head_node",
            "latency": "0.45ms (Ethernet)",
            "status": "APPLIED"
        }
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("test_node.py", py_code.splitlines())
        py_judge.visit(tree)
        rule1_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-01"]
        self.assertTrue(len(rule1_violations) >= 1)
        self.assertIn("0.45ms", rule1_violations[0].message)

    def test_passes_dynamic_latency_property(self):
        js_code = textwrap.dedent("""
        function renderDevice(deviceMetrics) {
            return {
                id: deviceMetrics.id,
                latency: deviceMetrics.measured_rtt_ms ? `${deviceMetrics.measured_rtt_ms.toFixed(2)}ms` : null,
                status: deviceMetrics.is_online ? "ONLINE" : "OFFLINE"
            };
        }
        """).strip()
        scanner = JsTsScanner("clean_render.js", js_code)
        violations = scanner.scan()
        rule1_violations = [v for v in violations if v.rule_id == "ZM-JS-01"]
        self.assertEqual(len(rule1_violations), 0)

    def test_detects_unquoted_js_property_keys_and_numbers(self):
        js_code = textwrap.dedent("""
        const metrics = {
            throughput: 10.0,
            ping: 15,
            speed_mbps: 50.0
        };
        """).strip()
        scanner = JsTsScanner("metrics.js", js_code)
        violations = scanner.scan()
        rule1_violations = [v for v in violations if v.rule_id == "ZM-JS-01"]
        self.assertTrue(len(rule1_violations) >= 3)

    def test_detects_throughput_units_in_js_object(self):
        js_code = textwrap.dedent("""
        const link = {
            id: "wifi_link",
            throughput: "50.0 Mbps",
            bandwidth: "1.2 Gbps"
        };
        """).strip()
        scanner = JsTsScanner("link.js", js_code)
        violations = scanner.scan()
        rule1_violations = [v for v in violations if v.rule_id == "ZM-JS-01"]
        self.assertTrue(len(rule1_violations) >= 2)

    def test_detects_expanded_telemetry_keys_in_python_dict(self):
        py_code = textwrap.dedent("""
        node_data = {
            "id": "node_99",
            "throughput_mbps": 100.0,
            "speed_mbps": 50.0,
            "latency_ms": 0.28,
            "ping_ms": 15.5,
            "rtt_ms": 1.2
        }
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("test_expanded.py", py_code.splitlines())
        py_judge.visit(tree)
        rule1_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-01"]
        self.assertTrue(len(rule1_violations) >= 5)


class TestRule2SyntheticMathMultipliers(unittest.TestCase):
    """Tests detection of Rule 2: Synthetic scaling multipliers (* 2.0, * 0.5, load * 5)."""

    def test_detects_synthetic_throughput_multipliers_python(self):
        py_code = textwrap.dedent("""
        def compute_multiwan_speed(single_tp_mbps, active_nodes):
            if active_nodes:
                merged_tp_mbps = sum(n.tp for n in active_nodes)
            else:
                merged_tp_mbps = round(single_tp_mbps * 2.0, 2)
            
            pixel_tp = single_tp_mbps * 0.5
            return merged_tp_mbps, pixel_tp
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("test_bench.py", py_code.splitlines())
        py_judge.visit(tree)
        rule2_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-02"]
        self.assertTrue(len(rule2_violations) >= 2)

    def test_detects_synthetic_rtt_multipliers_python(self):
        py_code = textwrap.dedent("""
        def estimate_bandwidth(rtt_ms):
            # Synthetic calculation from RTT
            return (1000 / rtt_ms) * 4.5
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("test_rtt.py", py_code.splitlines())
        py_judge.visit(tree)
        rule2_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-02"]
        self.assertTrue(len(rule2_violations) >= 1)

    def test_passes_legitimate_unit_conversions(self):
        py_code = textwrap.dedent("""
        def bytes_to_mbps(total_bytes, elapsed_seconds):
            if elapsed_seconds <= 0:
                return 0.0
            bits = total_bytes * 8
            megabits = bits / 1000000.0
            return megabits / elapsed_seconds
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("test_units.py", py_code.splitlines())
        py_judge.visit(tree)
        rule2_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-02"]
        self.assertEqual(len(rule2_violations), 0)


class TestRule3StaticNodesPreMarkedActive(unittest.TestCase):
    """Tests detection of Rule 3: Static node arrays initialized pre-marked ACTIVE / APPLIED."""

    def test_detects_static_applied_fleet_array_js(self):
        js_code = textwrap.dedent("""
        const FLEET_DEVICES = [
            { id: "Mac_Node_Local", name: "Host Mac", status: "APPLIED" },
            { id: "Linux_Head_Node", name: "Linux Head", status: "APPLIED" }
        ];
        """).strip()
        scanner = JsTsScanner("fleet_static.js", js_code)
        violations = scanner.scan()
        rule3_violations = [v for v in violations if v.rule_id == "ZM-JS-03"]
        self.assertTrue(len(rule3_violations) >= 1)

    def test_detects_static_active_node_dict_python(self):
        py_code = textwrap.dedent("""
        NODE_MAP = {
            "id": "node_01",
            "name": "Termux Pixel",
            "status": "ACTIVE"
        }
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("node_map.py", py_code.splitlines())
        py_judge.visit(tree)
        rule3_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-03"]
        self.assertTrue(len(rule3_violations) >= 1)

    def test_passes_dynamic_hydration_pattern(self):
        js_code = textwrap.dedent("""
        async function fetchLiveFleet() {
            const resp = await fetch('/api/dark-mode/status');
            const data = await resp.json();
            return data.devices.map(d => ({
                id: d.id,
                name: d.name,
                status: d.is_reachable ? "APPLIED" : "DISCONNECTED"
            }));
        }
        """).strip()
        scanner = JsTsScanner("dynamic_fleet.js", js_code)
        violations = scanner.scan()
        rule3_violations = [v for v in violations if v.rule_id == "ZM-JS-03"]
        self.assertEqual(len(rule3_violations), 0)

    def test_detects_generic_array_variable_names_premarked_active(self):
        js_code = textwrap.dedent("""
        const nodes = [
            { id: "node_1", status: "ONLINE" }
        ];
        let activeNodes = [
            { id: "node_2", status: "ACTIVE" }
        ];
        """).strip()
        scanner = JsTsScanner("generic_nodes.js", js_code)
        violations = scanner.scan()
        rule3_violations = [v for v in violations if v.rule_id == "ZM-JS-03"]
        self.assertTrue(len(rule3_violations) >= 2)


class TestRule4HardcodedFallbackDictionaries(unittest.TestCase):
    """Tests detection of Rule 4: Hardcoded fallback objects in exception handlers and endpoints."""

    def test_detects_fleet_dark_active_fallback_python(self):
        py_code = textwrap.dedent("""
        def get_fleet_status():
            try:
                with open("missing_file.json") as f:
                    return json.load(f)
            except Exception:
                status_data = {"status": "FLEET_DARK_ACTIVE", "devices_active": 6}
                return status_data
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("server_status.py", py_code.splitlines())
        py_judge.visit(tree)
        rule4_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-04"]
        self.assertTrue(len(rule4_violations) >= 1)

    def test_passes_truthful_null_fallback_python(self):
        py_code = textwrap.dedent("""
        def get_fleet_status():
            try:
                with open("data/status.json") as f:
                    return json.load(f)
            except Exception as e:
                return {
                    "status": "OFFLINE",
                    "error": str(e),
                    "devices_active": 0,
                    "devices": []
                }
        """).strip()
        tree = ast.parse(py_code)
        py_judge = PythonAstJudge("server_clean.py", py_code.splitlines())
        py_judge.visit(tree)
        rule4_violations = [v for v in py_judge.violations if v.rule_id == "ZM-AST-PY-04"]
        self.assertEqual(len(rule4_violations), 0)


class TestRule5SimulationCommentsAndTimers(unittest.TestCase):
    """Tests detection of Rule 5: Explicit simulation comments and fake async timers."""

    def test_detects_simulation_comment_in_healer(self):
        py_code = textwrap.dedent("""
        def trigger_tailscale_failover():
            # Simulating the failover logic
            subprocess.run("sleep 1", shell=True)
        """).strip()
        comment_judge = CrossLanguageCommentJudge("healer.py", py_code, "Python")
        violations = comment_judge.scan()
        rule5_violations = [v for v in violations if v.rule_id == "ZM-COM-05"]
        self.assertTrue(len(rule5_violations) >= 1)

    def test_detects_simulated_ui_timeout_js(self):
        js_code = textwrap.dedent("""
        function applyDarkMode() {
            setLoading(true);
            setTimeout(() => {
                setStatus("APPLIED");
                setLoading(false);
            }, 1000);
        }
        """).strip()
        scanner = JsTsScanner("ui.jsx", js_code)
        violations = scanner.scan()
        rule5_violations = [v for v in violations if v.rule_id == "ZM-JS-05"]
        self.assertTrue(len(rule5_violations) >= 1)


class TestRule6UnverifiedRandomization(unittest.TestCase):
    """Tests detection of Rule 6: Math.random() in telemetry pipelines."""

    def test_detects_unverified_math_random_in_webgpu(self):
        js_code = textwrap.dedent("""
        function generateTelemetryVector() {
            return {
                vx: (Math.random() - 0.5) * 2.4,
                vy: (Math.random() - 0.5) * 2.4,
                radius: Math.random() * 2.5 + 1.2
            };
        }
        """).strip()
        scanner = JsTsScanner("WebGPUVisualizer.jsx", js_code)
        violations = scanner.scan()
        rule6_violations = [v for v in violations if v.rule_id == "ZM-JS-06"]
        self.assertTrue(len(rule6_violations) >= 1)

    def test_passes_tagged_visual_animation(self):
        js_code = textwrap.dedent("""
        /* @verified-visual-animation */
        function createBackgroundParticles() {
            return {
                x: Math.random() * 800,
                y: Math.random() * 600
            };
        }
        """).strip()
        scanner = JsTsScanner("CanvasBackground.jsx", js_code)
        violations = scanner.scan()
        rule6_violations = [v for v in violations if v.rule_id == "ZM-JS-06"]
        self.assertEqual(len(rule6_violations), 0)


class TestDynamicRuntimeZeroVarianceJudge(unittest.TestCase):
    """Tests Dynamic Runtime Judge statistical variance analysis."""

    def setUp(self):
        self.dynamic_judge = ZeroMockDynamicJudge()

    def test_flags_flatline_constant_latency(self):
        samples = [
            MetricSample(
                sample_index=i,
                timestamp=100.0 + i,
                endpoint="http://localhost:5050/api/stats",
                status_code=200,
                raw_payload={"latency_ms": 0.28, "cpu_load": 12.0},
                extracted_metrics={"latency_ms": 0.28, "cpu_load": 12.0}
            )
            for i in range(5)
        ]
        stats = self.dynamic_judge.analyze_variance(samples)
        self.assertEqual(stats["latency_ms"].verdict, "SUSPECT_MOCK_DATA")
        self.assertEqual(stats["cpu_load"].verdict, "SUSPECT_MOCK_DATA")
        self.assertEqual(stats["latency_ms"].variance, 0.0)

    def test_passes_naturally_varying_live_metrics(self):
        latencies = [1.24, 1.45, 1.18, 1.62, 1.30]
        cpu_loads = [22.4, 25.1, 21.8, 28.0, 24.3]
        samples = [
            MetricSample(
                sample_index=i,
                timestamp=100.0 + i,
                endpoint="http://localhost:5050/api/stats",
                status_code=200,
                raw_payload={"latency_ms": latencies[i], "cpu_pct": cpu_loads[i]},
                extracted_metrics={"latency_ms": latencies[i], "cpu_pct": cpu_loads[i]}
            )
            for i in range(5)
        ]
        stats = self.dynamic_judge.analyze_variance(samples)
        self.assertEqual(stats["latency_ms"].verdict, "PASS")
        self.assertEqual(stats["cpu_pct"].verdict, "PASS")
        self.assertGreater(stats["latency_ms"].std_dev, 0.0)

    def test_exempts_constant_discrete_fields(self):
        samples = [
            MetricSample(
                sample_index=i,
                timestamp=100.0 + i,
                endpoint="http://localhost:3000/api/ports",
                status_code=200,
                raw_payload={"port": 5050, "cores": 8},
                extracted_metrics={"port": 5050.0, "cores": 8.0}
            )
            for i in range(5)
        ]
        stats = self.dynamic_judge.analyze_variance(samples)
        self.assertEqual(stats["port"].verdict, "EXEMPT_CONSTANT")
        self.assertEqual(stats["cores"].verdict, "EXEMPT_CONSTANT")

    def test_flags_flatline_large_sample_size_float_residuals(self):
        for n in [20, 50, 100]:
            samples = [
                MetricSample(
                    sample_index=i,
                    timestamp=100.0 + i * 0.1,
                    endpoint="http://localhost:5050/api/stats",
                    status_code=200,
                    raw_payload={"latency_ms": 0.28, "throughput_mbps": 10.0},
                    extracted_metrics={"latency_ms": 0.28, "throughput_mbps": 10.0}
                )
                for i in range(n)
            ]
            stats = self.dynamic_judge.analyze_variance(samples)
            self.assertEqual(stats["latency_ms"].verdict, "SUSPECT_MOCK_DATA")
            self.assertEqual(stats["throughput_mbps"].verdict, "SUSPECT_MOCK_DATA")


class TestActiveFaultInjector(unittest.TestCase):
    """Tests Active Fault Injector simulation and assertion gates."""

    def setUp(self):
        self.injector = ZeroMockFaultInjector()

    def test_closed_port_returns_clean_error(self):
        res = self.injector.test_closed_port(port=59997)
        self.assertTrue(res.passed)
        self.assertTrue(res.returned_explicit_null)
        self.assertFalse(res.returned_mock_fallback)

    def test_blackhole_ip_times_out_cleanly(self):
        res = self.injector.test_blackhole_ip(blackhole_ip="192.0.2.1")
        self.assertTrue(res.passed)
        self.assertTrue(res.returned_explicit_null)
        self.assertFalse(res.returned_mock_fallback)

    def test_client_fallback_flags_forbidden_mock_dict(self):
        def bad_client():
            return {"status": "FLEET_DARK_ACTIVE", "devices_active": 6}

        res = self.injector.test_client_fallback_handler(bad_client)
        self.assertFalse(res.passed)
        self.assertTrue(res.returned_mock_fallback)

    def test_client_fallback_flags_non_null_active_states(self):
        def active_client_1():
            return {"status": "ONLINE", "devices_active": 4}

        def active_client_2():
            return {"status": "ACTIVE", "throughput_mbps": 50.0}

        res1 = self.injector.test_client_fallback_handler(active_client_1)
        self.assertFalse(res1.passed)
        self.assertTrue(res1.returned_mock_fallback)
        self.assertEqual(res1.status_code_or_error, "UNEXPECTED_ACTIVE_STATE_DURING_FAULT")

        res2 = self.injector.test_client_fallback_handler(active_client_2)
        self.assertFalse(res2.passed)
        self.assertTrue(res2.returned_mock_fallback)
        self.assertEqual(res2.status_code_or_error, "UNEXPECTED_ACTIVE_STATE_DURING_FAULT")

    def test_client_fallback_passes_truthful_null(self):
        def clean_client():
            return {"status": "OFFLINE", "devices_active": 0, "devices": []}

        res = self.injector.test_client_fallback_handler(clean_client)
        self.assertTrue(res.passed)
        self.assertTrue(res.returned_explicit_null)


class TestFullDirectoryScoringAndCertification(unittest.TestCase):
    """Tests full directory audit, scoring formula, and master runner integration."""

    def test_clean_directory_achieves_100_percent_score(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            clean_py = Path(tmpdir) / "clean_daemon.py"
            clean_py.write_text("""
def measure_ping(target_host):
    # Measures ping using standard socket connect timing
    import time, socket
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((target_host, 80), timeout=2.0)
        s.close()
        return round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        return None
            """)

            judge = ZeroMockStaticJudge(ignore_test_files=False)
            violations = judge.audit_directory(tmpdir)
            report = judge.generate_report(tmpdir, violations)
            self.assertEqual(report["score"], 100.0)
            self.assertEqual(report["verdict"], "ZERO_MOCK_CERTIFIED")
            self.assertEqual(len(violations), 0)

    def test_mock_heavy_directory_receives_penalty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_py = Path(tmpdir) / "mock_app.py"
            mock_py.write_text("""
def fake_metrics(single_tp):
    # Simulating the failover logic
    mock_data = {"status": "FLEET_DARK_ACTIVE", "devices_active": 6}
    speed = single_tp * 2.0
    return mock_data, speed
            """)

            judge = ZeroMockStaticJudge(ignore_test_files=False)
            violations = judge.audit_directory(tmpdir)
            report = judge.generate_report(tmpdir, violations)
            self.assertLess(report["score"], 80.0)
            self.assertEqual(report["verdict"], "MOCK_VIOLATIONS_DETECTED")
            self.assertGreater(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
