#!/usr/bin/env python3
"""
Unit and Integration Tests for Google Jules API, CLI & Local Speculation Practice Engine
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Add project root to sys.path
MONOREPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
sys.path.insert(0, str(MONOREPO_ROOT / "06_scripts_and_tooling/jules"))

from jules_config_and_speculation_engine import (
    JulesConfigManager,
    LocalSpeculationEngine,
    JulesContinuousOptimizer,
    CONFIG_API_URL
)


def test_config_manager_initialization():
    mgr = JulesConfigManager(MONOREPO_ROOT)
    config = mgr.load_config()

    assert config is not None
    assert config["repository"]["config_url"] == CONFIG_API_URL
    assert config["automation"]["daily_task_limit"] == 300
    assert len(config["mcps"]) >= 3
    assert config["ci_app"]["enabled"] is True


def test_setup_script_exists_and_executable():
    setup_script = MONOREPO_ROOT / ".jules/setup.sh"
    assert setup_script.exists()
    assert os.access(setup_script, os.X_OK)


def test_local_speculation_engine():
    engine = LocalSpeculationEngine(MONOREPO_ROOT)
    task_item = {
        "id": "test_spec_001",
        "task": "Test unit execution for Jules local speculation practice",
        "target_file": "06_scripts_and_tooling/gemini_lens_integration/sync_engine.py"
    }

    res = engine.run_local_task_speculation(task_item)

    assert res["task_id"] == "test_spec_001"
    assert res["ast_parse_success"] is True
    assert res["syntax_pass"] is True
    assert res["execution_latency_ms"] > 0
    assert len(res["sha256"]) == 64


def test_continuous_optimizer_benchmark():
    optimizer = JulesContinuousOptimizer(MONOREPO_ROOT)
    res = optimizer.run_benchmark_cycle()

    assert res["config_url"] == CONFIG_API_URL
    assert res["setup_script_verified"] is True
    assert res["mcps_enabled"] >= 3
    assert res["zero_mock_verified"] is True
    assert "cycle_latency_ms" in res
    assert len(res["tri_proof_sha256"]) == 64


def test_status_manifest_creation():
    manifest_path = MONOREPO_ROOT / "04_data_and_memory/jules_config_status.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["config_url"] == CONFIG_API_URL
    assert data["zero_mock_verified"] is True
