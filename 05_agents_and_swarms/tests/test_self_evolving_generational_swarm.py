#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_agents_and_swarms/tests/test_self_evolving_generational_swarm.py
==================================================================
Unit & Integration Tests for Autonomous Self-Evolving Swarm Engine:
- Gemini Shadow Teacher zero-plan-token initialization
- Local student model code execution and AST verification
- Confidence governor and autonomous shadow fade-out (C >= 0.95)
- Continuous DPO pair serialization & SHA256 integrity
- Local AI superiority benchmarking
"""

import os
import sys
import json
import importlib.util
import pytest
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
ENGINE_PATH = REPO_ROOT / "05_agents_and_swarms" / "self_evolving_generational_swarm_engine.py"

# Dynamically import engine module
spec = importlib.util.spec_from_file_location("self_evolving_generational_swarm_engine", str(ENGINE_PATH))
engine_module = importlib.util.module_from_spec(spec)
sys.modules["self_evolving_generational_swarm_engine"] = engine_module
spec.loader.exec_module(engine_module)

GeminiShadowTeacher = engine_module.GeminiShadowTeacher
LocalStudentRunner = engine_module.LocalStudentRunner
ConfidenceGovernorAndFadeOut = engine_module.ConfidenceGovernorAndFadeOut
ContinuousDpoDistillationSink = engine_module.ContinuousDpoDistillationSink
LocalAiSuperiorityBenchmark = engine_module.LocalAiSuperiorityBenchmark
GenerationalSwarmEngine = engine_module.GenerationalSwarmEngine


def test_gemini_shadow_teacher_initialization():
    teacher = GeminiShadowTeacher()
    assert teacher.model_name in ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    assert teacher.plan_tokens_consumed == 0
    assert teacher.project_id == "lauburu-play-deploy"


def test_local_student_runner_ast_and_execution_success():
    runner = LocalStudentRunner()
    valid_code = "def add(a, b):\n    return a + b\n"
    harness = "assert add(2, 3) == 5\nassert add(-1, 1) == 0\nprint('PASS')"
    res = runner.execute_and_verify(valid_code, harness)
    assert res["ast_valid"] is True
    assert res["exit_code"] == 0
    assert res["test_passed"] is True
    assert res["runtime_ms"] >= 0.0


def test_local_student_runner_syntax_error():
    runner = LocalStudentRunner()
    invalid_code = "def broken(a, b\n    return a +"
    harness = "assert broken(1, 2) == 3"
    res = runner.execute_and_verify(invalid_code, harness)
    assert res["ast_valid"] is False
    assert res["exit_code"] != 0
    assert res["test_passed"] is False
    assert "SyntaxError" in res["ast_error"]


def test_confidence_governor_calculation():
    gov = ConfidenceGovernorAndFadeOut()
    perfect_test = {
        "ast_valid": True,
        "exit_code": 0,
        "runtime_ms": 12.5,
        "stderr": "",
        "test_passed": True
    }
    conf = gov.calculate_confidence(perfect_test)
    assert conf == 1.0

    failing_test = {
        "ast_valid": False,
        "exit_code": 1,
        "runtime_ms": 50.0,
        "stderr": "SyntaxError",
        "test_passed": False
    }
    conf_fail = gov.calculate_confidence(failing_test)
    assert conf_fail == 0.10


def test_confidence_governor_shadow_fadeout_lifecycle():
    gov = ConfidenceGovernorAndFadeOut()
    gov.consecutive_passes = 0
    gov.shadow_teacher_active = True

    passing_test = {
        "ast_valid": True,
        "exit_code": 0,
        "runtime_ms": 20.0,
        "stderr": "",
        "test_passed": True
    }

    # Simulate 4 consecutive passes: shadow teacher still engaged
    for i in range(4):
        state = gov.update(passing_test)
        assert state["consecutive_passes"] == i + 1
        assert state["shadow_teacher_active"] is True
        assert state["status"] == "SHADOW_TEACHER_ENGAGED"

    # 5th consecutive pass: triggers autonomous shadow fade-out
    state_5 = gov.update(passing_test)
    assert state_5["consecutive_passes"] == 5
    assert state_5["shadow_teacher_active"] is False
    assert state_5["status"] == "SHADOW_FADEOUT_LOCAL_AUTONOMOUS"

    # Simulate failure: immediately re-engages shadow teacher
    failing_test = {
        "ast_valid": True,
        "exit_code": 1,
        "runtime_ms": 20.0,
        "stderr": "AssertionError",
        "test_passed": False
    }
    state_fail = gov.update(failing_test)
    assert state_fail["consecutive_passes"] == 0
    assert state_fail["shadow_teacher_active"] is True
    assert state_fail["status"] == "SHADOW_TEACHER_ENGAGED"


def test_continuous_dpo_sink_serialization():
    task = "Implement factorial function"
    chosen = "def fact(n):\n    return 1 if n <= 1 else n * fact(n - 1)\n"
    rejected = "def fact(n):\n    return n * fact(n - 1)\n"
    critique = "Base case handled cleanly in chosen."

    dpo = ContinuousDpoDistillationSink.append_dpo_pair(
        task=task,
        chosen_code=chosen,
        rejected_code=rejected,
        critique=critique,
        student_model="SmolLM2-135M",
        teacher_model="gemini-2.5-flash-lite",
        confidence=1.0
    )

    assert dpo["task"] == task
    assert dpo["chosen"] == chosen
    assert dpo["rejected"] == rejected
    assert len(dpo["sha256"]) == 64
    assert dpo["empirical_confidence"] == 1.0


def test_local_ai_superiority_benchmark_suite():
    benchmarks = LocalAiSuperiorityBenchmark.run_benchmark_suite()
    assert benchmarks["overall_local_win_rate"] == 1.00
    assert len(benchmarks["benchmarks"]) == 4
    for b in benchmarks["benchmarks"]:
        assert b["winner"] == "LOCAL_AI"
        assert b["local_latency_ms"] < b["cloud_latency_ms"]
        assert b["local_cost"] == "$0.00"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
