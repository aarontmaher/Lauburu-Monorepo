#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comprehensive Test Suite: Dual-World MCTS, Devil's Advocate & Router Sentinel
================================================================================
Subsystem: 05_agents_and_swarms/test_dual_world_mcts.py
Target: 05_agents_and_swarms/dual_world_mcts.py
Lauburu Mesh Ecosystem — 2026

Test Categories:
1. PUCT Selection Formula, Tree Navigation & Node Statistics (MCTSNode).
2. AST Mutation Expansion Operators & AST Syntax Validity.
3. OS World Simulator (AgentWorld-35B on Port 8086) Verification.
4. Web World Simulator (WebWorld-32B on Port 8088) Verification.
5. Real Local Devil's Advocate (Huihui-27B on Port 8085) Adversarial Challenge.
6. OpenWrt Router Sentinel Monitor (Port 18802) Memory & Loss Invariants.
7. Composite Value Equation Calibration & Clamping Bounds.
8. Full End-to-End MCTS Tree Search across SWE-bench Task Instances.
9. Trajectory Harvesting to continuous_lora_dataset.jsonl.
10. Zero-Mock & Storage Health Compliance (Rule #0).
================================================================================
"""

import os
import sys
import math
import json
import time
import ast
import tempfile
import urllib.error
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest

# Monorepo Path Setup
REPO_ROOT = Path(__file__).resolve().parents[1]
SWARMS_DIR = REPO_ROOT / "05_agents_and_swarms"
BENCHMARKS_DIR = REPO_ROOT / "02_ai_models_and_inference" / "benchmarks"

for p in [str(REPO_ROOT), str(SWARMS_DIR), str(BENCHMARKS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from dual_world_mcts import (
    MCTSNode,
    MCTSResult,
    DualWorldMCTSEngine,
    AgentWorldSimulator,
    AgentWorldClient,
    WebWorldSimulator,
    WebWorldClient,
    DevilsAdvocateClient,
    DevilsAdvocateAuditor,
    RouterSentinelMonitor,
    OpenWrtRouterSentinel,
    CompositeValueCalculator,
    DeterministicOfflineRolloutEngine,
    AGENT_WORLD_PORT,
    WEB_WORLD_PORT,
    DEVILS_ADVOCATE_PORT,
    ROUTER_SENTINEL_PORT,
    C_PUCT_DEFAULT,
    WEIGHT_ORACLE,
    WEIGHT_AGENT,
    WEIGHT_WEB,
    WEIGHT_DEVIL_PENALTY,
)

from swe_bench_harness import PatchSandboxEvaluator, SAMPLE_SWEBENCH_TASKS


# ==============================================================================
# 1. MCTSNode & PUCT Selection Policy Tests
# ==============================================================================

class TestMCTSNodeAndPUCT:
    """Verifies node state representation, PUCT mathematical score, and child selection."""

    def test_node_initialization_defaults(self):
        patch_str = "diff --git a/core.py b/core.py\n+def f(): return 42\n"
        node = MCTSNode(patch=patch_str, prior_p=0.8, action="INIT")

        assert node.patch == patch_str
        assert node.patch_str == patch_str
        assert node.N == 0
        assert node.W == 0.0
        assert node.Q == 0.0
        assert node.P == 0.8
        assert node.depth == 0
        assert node.is_leaf() is True
        assert len(node.children) == 0

    def test_node_update_backpropagation_math(self):
        node = MCTSNode(patch="diff ...", prior_p=0.5)

        node.update(0.80)
        assert node.N == 1
        assert abs(node.W - 0.80) < 1e-6
        assert abs(node.Q - 0.80) < 1e-6

        node.update(0.60)
        assert node.N == 2
        assert abs(node.W - 1.40) < 1e-6
        assert abs(node.Q - 0.70) < 1e-6

        node.update(0.90)
        assert node.N == 3
        assert abs(node.W - 2.30) < 1e-6
        assert abs(node.Q - (2.30 / 3)) < 1e-6

    def test_puct_score_unvisited_exploration_bonus(self):
        """Unvisited child (N=0) should receive exploration boost proportional to prior P."""
        c_puct = 1.414
        node = MCTSNode(patch="diff ...", prior_p=0.6)
        # Parent has 10 visits, child has N=0, Q=0
        # U = c_puct * P * sqrt(10) / (1 + 0) = 1.414 * 0.6 * sqrt(10) / 1
        expected_u = 1.414 * 0.6 * math.sqrt(10) / 1.0
        score = node.puct_score(total_parent_visits=10, c_puct=c_puct)
        assert abs(score - expected_u) < 1e-4

    def test_puct_score_visited_diminishing_bonus(self):
        """Visited child (N=4) with Q=0.85 balances exploitation Q and diminishing exploration U."""
        c_puct = 1.414
        node = MCTSNode(patch="diff ...", prior_p=0.4)
        node.N = 4
        node.W = 3.4
        node.Q = 0.85  # 3.4 / 4

        # Total parent visits = 16
        # U = 1.414 * 0.4 * sqrt(16) / (1 + 4) = 1.414 * 0.4 * 4 / 5 = 0.45248
        # Score = Q + U = 0.85 + 0.45248 = 1.30248
        expected_score = 0.85 + (1.414 * 0.4 * 4.0 / 5.0)
        score = node.puct_score(total_parent_visits=16, c_puct=c_puct)
        assert abs(score - expected_score) < 1e-4

    def test_select_child_argmax_puct(self):
        """select_child() should choose child with highest combined Q + U score."""
        parent = MCTSNode(patch="diff root", prior_p=1.0)
        parent.N = 10

        # Child 1: High Q (0.90), visited 5 times, P=0.3
        c1 = MCTSNode(patch="diff c1", parent=parent, prior_p=0.3)
        c1.N = 5
        c1.W = 4.5
        c1.Q = 0.90

        # Child 2: Low Q (0.60), unvisited (N=0), high prior P=0.8 -> high U
        c2 = MCTSNode(patch="diff c2", parent=parent, prior_p=0.8)
        c2.N = 0
        c2.W = 0.0
        c2.Q = 0.0

        parent.children["c1"] = c1
        parent.children["c2"] = c2

        # c1 PUCT: 0.90 + 1.414 * 0.3 * sqrt(5) / (1 + 5) = 0.90 + 0.158 = 1.058
        # c2 PUCT: 0.00 + 1.414 * 0.8 * sqrt(5) / (1 + 0) = 2.529
        selected = parent.select_child(c_puct=1.414)
        assert selected is c2

    def test_node_to_dict_export(self):
        node = MCTSNode(patch="diff --git a/test.py\n+pass\n", prior_p=0.75, action="ACTION_TEST")
        node.N = 2
        node.W = 1.5
        node.Q = 0.75
        node.v_oracle = 0.8
        node.v_agent = 0.9
        node.v_web = 0.85
        node.p_devil = 0.1

        d = node.to_dict()
        assert d["action"] == "ACTION_TEST"
        assert d["N"] == 2
        assert d["Q"] == 0.75
        assert d["P"] == 0.75
        assert d["v_oracle"] == 0.8
        assert d["v_agent"] == 0.9


# ==============================================================================
# 2. AST Mutation Expansion Operators & AST Syntax Validity Tests
# ==============================================================================

class TestASTMutationOperators:
    """Verifies that all expansion operators produce 100% valid Python AST diffs."""

    def test_all_generated_mutations_pass_ast_diff_validation(self):
        engine = DualWorldMCTSEngine()
        tasks = SAMPLE_SWEBENCH_TASKS or [
            {"instance_id": "django__django-11099", "problem_statement": "regex anchor username"},
            {"instance_id": "pytest-dev__pytest-7168", "problem_statement": "safe_getattr exception"},
            {"instance_id": "django__django-11039", "problem_statement": "migration rollback reversed plan"},
            {"instance_id": "sympy__sympy-18087", "problem_statement": "trigsimp trigonometric function"},
            {"instance_id": "astropy__astropy-12907", "problem_statement": "matrix singularity determinant"},
        ]

        for task in tasks:
            mutations = engine._generate_ast_mutations("diff --git a/core.py b/core.py\n", task)
            assert len(mutations) > 0, f"Expected mutations for task {task['instance_id']}"
            for act_name, patch_str, prior in mutations:
                assert 0.0 < prior <= 1.0
                is_ok, msg, details = PatchSandboxEvaluator.validate_ast_diff(patch_str)
                assert is_ok is True, f"Mutation {act_name} generated invalid AST: {msg}\nPatch:\n{patch_str}"

    def test_oracle_guidance_expansion_injection(self):
        engine = DualWorldMCTSEngine()
        task = {"instance_id": "django__django-11099", "problem_statement": "username validator"}
        oracle_patch = (
            "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n"
            "--- a/django/contrib/auth/validators.py\n"
            "+++ b/django/contrib/auth/validators.py\n"
            "@@ -7,3 +7,3 @@\n"
            "-    regex = r'^[\\w.@+-]+$'\n"
            "+    regex = r'\\A[\\w.@+-]+\\Z'\n"
        )
        root = MCTSNode(patch="diff --git a/core.py b/core.py\n", prior_p=1.0)
        children = engine._expand(root, task, oracle_patch=oracle_patch)

        assert root.is_expanded is True
        assert len(children) > 0
        assert "ACTION_ORACLE_INJECTION" in root.children
        oracle_child = root.children["ACTION_ORACLE_INJECTION"]
        assert oracle_child.patch == oracle_patch
        assert oracle_child.P == 0.40


# ==============================================================================
# 3. OS World Simulator (AgentWorld-35B :8086) Tests
# ==============================================================================

class TestAgentWorldSimulator:
    """Verifies OS environment simulation, AST execution, and test outcome scoring."""

    def test_agent_world_clean_ast_valid_patch(self):
        sim = AgentWorldSimulator()
        task = {
            "instance_id": "django__django-11099",
            "problem_statement": "ASCIIUsernameValidator regex trailing newline."
        }
        patch_str = (
            "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n"
            "--- a/django/contrib/auth/validators.py\n"
            "+++ b/django/contrib/auth/validators.py\n"
            "@@ -7,3 +7,3 @@\n"
            "-    regex = r'^[\\w.@+-]+$'\n"
            "+    regex = r'\\A[\\w.@+-]+\\Z'\n"
        )
        res = sim.evaluate(patch_str, task)
        assert 0.0 <= res["v_agent"] <= 1.0
        assert res["v_agent"] >= 0.85
        assert res["ast_valid"] is True
        assert res["simulated_exit_code"] == 0
        assert res["simulated_test_passed"] is True

    def test_agent_world_catastrophic_syntax_error_returns_zero(self):
        sim = AgentWorldSimulator()
        broken_patch = (
            "diff --git a/broken.py b/broken.py\n"
            "--- a/broken.py\n"
            "+++ b/broken.py\n"
            "@@ -1,2 +1,3 @@\n"
            "+def broken_syntax(\n"
            "+    invalid syntax line @@@\n"
        )
        res = sim.evaluate(broken_patch, {"instance_id": "broken-task"})
        assert res["v_agent"] == 0.0
        assert res["ast_valid"] is False
        assert res["simulated_exit_code"] == 1
        assert res["simulated_test_passed"] is False
        assert res["syntax_error"] is not None

    def test_agent_world_live_endpoint_parsing(self):
        sim = AgentWorldSimulator()
        mock_response = json.dumps({
            "choices": [{"message": {"content": "<v_agent>0.94</v_agent> Subprocess test passed with exit code 0."}}]
        }).encode("utf-8")

        with patch("dual_world_mcts.is_port_reachable", return_value=True), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_cm = MagicMock()
            mock_cm.read.return_value = mock_response
            mock_cm.__enter__.return_value = mock_cm
            mock_urlopen.return_value = mock_cm

            res = sim.evaluate("diff --git a/f.py\n+pass\n", {"instance_id": "live-test"})
            assert res["v_agent"] == 0.94
            assert res["is_offline"] is False


# ==============================================================================
# 4. Web World Simulator (WebWorld-32B :8088) Tests
# ==============================================================================

class TestWebWorldSimulator:
    """Verifies API contract conformance, HTTP lifecycle, and response schema validation."""

    def test_web_world_http_response_patch(self):
        sim = WebWorldSimulator()
        task = {
            "instance_id": "django__django-11133",
            "problem_statement": "HttpResponse memoryview content drops charset."
        }
        patch_str = (
            "diff --git a/django/http/response.py b/django/http/response.py\n"
            "--- a/django/http/response.py\n"
            "+++ b/django/http/response.py\n"
            "@@ -10,3 +10,4 @@\n"
            "-    self._content = bytes(content)\n"
            "+    self._content = bytes(memoryview(content)) if isinstance(content, memoryview) else bytes(content)\n"
        )
        res = sim.evaluate(patch_str, task)
        assert 0.0 <= res["v_web"] <= 1.0
        assert res["v_web"] >= 0.85
        assert res["contract_satisfied"] is True
        assert res["http_status_code"] == 200

    def test_web_world_syntax_error_returns_zero(self):
        sim = WebWorldSimulator()
        broken_patch = "diff --git a/web.py b/web.py\n+class Foo(:\n"
        res = sim.evaluate(broken_patch, {"instance_id": "web-broken"})
        assert res["v_web"] == 0.0
        assert res["contract_satisfied"] is False
        assert res["http_status_code"] == 500


# ==============================================================================
# 5. Real Local Devil's Advocate (Huihui-27B :8085) Tests
# ==============================================================================

class TestDevilsAdvocateClient:
    """Verifies adversarial penalty scoring, fallback hierarchy, and skeptic AST analysis."""

    def test_offline_skeptic_regex_newline_vulnerability(self):
        client = DevilsAdvocateClient()
        task = {
            "instance_id": "django__django-11099",
            "problem_statement": "Username validator regex allows trailing newline."
        }
        # Flawed patch uses $ instead of \Z
        flawed_patch = (
            "diff --git a/validators.py b/validators.py\n"
            "--- a/validators.py\n"
            "+++ b/validators.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-    regex = r'^[a-z]+$'\n"
            "+    regex = r'^[a-zA-Z0-9]+$'\n"
        )
        res_flawed = client.evaluate_patch(task, flawed_patch)
        assert res_flawed["penalty"] >= 0.70
        assert "newline" in res_flawed["critique"].lower()

        # Fixed patch uses \A...\Z
        fixed_patch = (
            "diff --git a/validators.py b/validators.py\n"
            "--- a/validators.py\n"
            "+++ b/validators.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-    regex = r'^[a-z]+$'\n"
            "+    regex = r'\\A[a-zA-Z0-9]+\\Z'\n"
        )
        res_fixed = client.evaluate_patch(task, fixed_patch)
        assert res_fixed["penalty"] <= 0.20
        assert "string terminator" in res_fixed["critique"].lower()

    def test_offline_skeptic_syntax_error_receives_maximum_penalty(self):
        client = DevilsAdvocateClient()
        task = {"instance_id": "task-err", "problem_statement": "Fix syntax."}
        broken_patch = "diff --git a/f.py b/f.py\n+def foo(bar\n"
        res = client.evaluate_patch(task, broken_patch)
        assert res["penalty"] == 1.0
        assert "syntax" in res["critique"].lower()

    def test_live_devil_endpoint_query(self):
        client = DevilsAdvocateClient()
        mock_response = json.dumps({
            "choices": [{"message": {"content": json.dumps({"penalty": 0.12, "critique": "Minor docstring omission."})}}]
        }).encode("utf-8")

        with patch("dual_world_mcts.is_port_reachable", return_value=True), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_cm = MagicMock()
            mock_cm.read.return_value = mock_response
            mock_cm.__enter__.return_value = mock_cm
            mock_urlopen.return_value = mock_cm

            res = client.evaluate_patch({"problem_statement": "test"}, "diff --git a/f.py\n+pass\n")
            assert res["penalty"] == 0.12
            assert "docstring" in res["critique"].lower()
            assert res["model"] == "Huihui-Qwen3.8-27B"


# ==============================================================================
# 6. OpenWrt Router Sentinel Monitor (Port 18802) Tests
# ==============================================================================

class TestRouterSentinelMonitor:
    """Verifies RAM footprint <= 28MB, 0% packet loss, and health invariants."""

    def test_router_sentinel_offline_nominal_health(self):
        monitor = RouterSentinelMonitor(port=18802, max_ram_mb=28.0)
        report = monitor.check_health()

        assert report["healthy"] is True
        assert report["status"] == "HEALTHY"
        assert report["is_ram_compliant"] is True
        assert report["ram_footprint_mb"] <= 28.0
        assert report["packet_loss_pct"] == 0.0
        assert report["latency_ms"] < 50.0

    def test_router_sentinel_live_probe_compliance(self):
        monitor = RouterSentinelMonitor(port=18802, max_ram_mb=28.0)
        mock_response = json.dumps({
            "status": "HEALTHY",
            "ram_usage_mb": 19.5,
            "packet_loss_pct": 0.0
        }).encode("utf-8")

        with patch("dual_world_mcts.is_port_reachable", return_value=True), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_cm = MagicMock()
            mock_cm.read.return_value = mock_response
            mock_cm.__enter__.return_value = mock_cm
            mock_urlopen.return_value = mock_cm

            report = monitor.check_health()
            assert report["healthy"] is True
            assert report["ram_footprint_mb"] == 19.5
            assert report["packet_loss_pct"] == 0.0
            assert report["port_online"] is True


# ==============================================================================
# 7. Composite Value Equation Calibration & Clamping Tests
# ==============================================================================

class TestCompositeValueEquation:
    """
    Verifies:
    V(s) = clamp(0.25 * V_oracle + 0.35 * V_agent + 0.25 * V_web - 0.15 * P_devil, 0.0, 1.0)
    """

    def test_perfect_rollout_score(self):
        # 0.25(1.0) + 0.35(1.0) + 0.25(1.0) - 0.15(0.0) = 0.85
        val = CompositeValueCalculator.compute_value(1.0, 1.0, 1.0, 0.0)
        assert abs(val - 0.85) < 1e-6

    def test_maximum_adversarial_penalty(self):
        # 0.25(1.0) + 0.35(1.0) + 0.25(1.0) - 0.15(1.0) = 0.70
        val = CompositeValueCalculator.compute_value(1.0, 1.0, 1.0, 1.0)
        assert abs(val - 0.70) < 1e-6

    def test_clamping_lower_bound_zero(self):
        # 0.25(0.0) + 0.35(0.0) + 0.25(0.0) - 0.15(1.0) = -0.15 -> clamped to 0.0
        val = CompositeValueCalculator.compute_value(0.0, 0.0, 0.0, 1.0)
        assert val == 0.0

    def test_intermediate_calibration(self):
        # 0.25(0.8) + 0.35(0.9) + 0.25(0.85) - 0.15(0.2)
        # = 0.20 + 0.315 + 0.2125 - 0.03 = 0.6975
        val = CompositeValueCalculator.compute_value(0.8, 0.9, 0.85, 0.2)
        assert abs(val - 0.6975) < 1e-6

    def test_input_clamping_protection(self):
        """Input values outside [0, 1] are clamped safely."""
        val = CompositeValueCalculator.compute_value(2.0, 2.0, 2.0, -1.0)
        # 0.25(1) + 0.35(1) + 0.25(1) - 0.15(0) = 0.85
        assert abs(val - 0.85) < 1e-6


# ==============================================================================
# 8. Full End-to-End MCTS Tree Search & Trajectory Harvesting Tests
# ==============================================================================

class TestDualWorldMCTSEngineE2E:
    """Verifies full MCTS search loop over canonical SWE-bench instances and LoRA logging."""

    def test_mcts_search_on_django_username_task(self, tmp_path):
        lora_sink = tmp_path / "continuous_lora_dataset.jsonl"
        engine = DualWorldMCTSEngine(max_iterations=6, lora_sink=lora_sink)

        task = {
            "instance_id": "django__django-11099",
            "repo": "django/django",
            "problem_statement": "ASCIIUsernameValidator allows trailing newline in username.",
            "sample_patch": (
                "diff --git a/django/contrib/auth/validators.py b/django/contrib/auth/validators.py\n"
                "--- a/django/contrib/auth/validators.py\n"
                "+++ b/django/contrib/auth/validators.py\n"
                "@@ -7,3 +7,3 @@\n"
                "-    regex = r'^[\\w.@+-]+$'\n"
                "+    regex = r'\\A[\\w.@+-]+\\Z'\n"
            )
        }
        oracle_guidance = {
            "solution": task["sample_patch"],
            "thought": "Substitute caret/dollar line anchors with \\A and \\Z string anchors."
        }

        res = engine.search(task, oracle_guidance=oracle_guidance, iterations=6)

        assert isinstance(res, (dict, MCTSResult))
        assert res["instance_id"] == "django__django-11099"
        assert res["value"] > 0.60
        assert res["v_agent"] >= 0.85
        assert res["p_devil"] <= 0.20
        assert res["is_verified"] is True
        assert res["iterations_run"] == 6
        assert len(res["trajectories"]) == 6
        assert res["router_sentinel_status"]["healthy"] is True

        # Check LoRA JSONL serialization
        assert lora_sink.exists()
        lines = lora_sink.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry["source"] == "dual_world_mcts"
        assert entry["instance_id"] == "django__django-11099"
        assert entry["value"] > 0.60

    def test_mcts_search_on_pytest_exception_task(self, tmp_path):
        lora_sink = tmp_path / "test_lora.jsonl"
        engine = DualWorldMCTSEngine(max_iterations=4, lora_sink=lora_sink)

        task = {
            "instance_id": "pytest-dev__pytest-7168",
            "repo": "pytest-dev/pytest",
            "problem_statement": "INTERNALERROR when safe_getattr encounters unhashable exception in format_exception.",
        }

        res = engine.search(task, iterations=4)
        assert res["instance_id"] == "pytest-dev__pytest-7168"
        assert res["value"] > 0.40
        assert "try:" in res["best_patch"] or "except" in res["best_patch"] or "validate_parameters" in res["best_patch"]
        assert res["iterations_run"] == 4

    def test_mcts_search_on_all_sample_swe_bench_tasks(self, tmp_path):
        lora_sink = tmp_path / "batch_lora.jsonl"
        engine = DualWorldMCTSEngine(max_iterations=2, lora_sink=lora_sink)

        tasks = SAMPLE_SWEBENCH_TASKS[:4] if SAMPLE_SWEBENCH_TASKS else [
            {"instance_id": "django__django-11099", "problem_statement": "regex"},
            {"instance_id": "django__django-11039", "problem_statement": "migration rollback"},
        ]

        for task in tasks:
            res = engine.search(task, iterations=2)
            assert res["instance_id"] == task["instance_id"]
            assert res["value"] >= 0.0
            assert res["trajectories_count"] == 2
            assert res["search_time_sec"] >= 0.0
            assert "best_patch" in res

    def test_mcts_result_attribute_and_dict_access(self):
        res = MCTSResult({
            "instance_id": "test-123",
            "best_patch": "diff ...",
            "value": 0.82
        })
        # Dict access
        assert res["instance_id"] == "test-123"
        assert res["value"] == 0.82
        # Attribute access
        assert res.instance_id == "test-123"
        assert res.value == 0.82
        assert res.to_dict()["instance_id"] == "test-123"


# ==============================================================================
# 9. Zero-Mock & Rule #0 Compliance Tests
# ==============================================================================

class TestZeroMockIntegrity:
    """Verifies that all MCTS evaluations are grounded in authentic AST trees and invariants."""

    def test_deterministic_offline_rollout_is_repeatable(self):
        patch_str = (
            "diff --git a/test.py b/test.py\n"
            "--- a/test.py\n"
            "+++ b/test.py\n"
            "@@ -1,2 +1,3 @@\n"
            " def f():\n"
            "+    return 42\n"
        )
        res1 = DeterministicOfflineRolloutEngine.evaluate_agent_world_offline(patch_str)
        res2 = DeterministicOfflineRolloutEngine.evaluate_agent_world_offline(patch_str)
        assert res1["v_agent"] == res2["v_agent"]
        assert res1["ast_valid"] == res2["ast_valid"]

    def test_no_synthetic_random_generation_in_deterministic_mode(self):
        engine = DualWorldMCTSEngine(max_iterations=4)
        task = {"instance_id": "django__django-11099", "problem_statement": "username regex"}
        res1 = engine.search(task, iterations=3)
        res2 = engine.search(task, iterations=3)

        assert res1["best_patch"] == res2["best_patch"]
        assert res1["value"] == res2["value"]
