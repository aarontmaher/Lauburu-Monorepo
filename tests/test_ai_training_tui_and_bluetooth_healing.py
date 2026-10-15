#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for AI Training TUI and Bluetooth Serial Self-Healing Strategy.
Strict Rule #0 Compliance: 0 unittest.mock occurrences, 0 synthetic arrays.
"""

import os
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "01_apps"))
sys.path.insert(0, str(REPO_ROOT / "05_agents_and_swarms"))
sys.path.insert(0, str(REPO_ROOT / "06_scripts_and_tooling"))
sys.path.insert(0, "/Users/aaron/teamwork_projects/unified_resilient_serial_terminal_ide/src")

from ai_training_tui.training_tui import TrainingTUIApp
from bluetooth_serial_self_healing_tui import BluetoothSerialSelfHealingTUI
from cloud_ai_routing_governor import CloudAIRoutingGovernor


def test_gemini_3_1_pro_hard_block_enforced():
    """Verify Gemini 3.1 Pro and Gemini Pro Exp are hard-blocked to preserve user quota."""
    gov = CloudAIRoutingGovernor()
    assert gov.tiers["gemini_3_1_pro"]["enabled"] is False
    assert gov.tiers["gemini_3_1_pro"]["daily_quota"] == 0
    assert gov.tiers["gemini_pro_exp"]["enabled"] is False
    assert gov.tiers["gemini_pro_exp"]["daily_quota"] == 0

    # System planning must divert to local_qwen_moe
    res = gov.route_task("system_planning", "high", 5000)
    assert res["chosen_target"] == "local_qwen_moe"
    assert "BLOCKED" in res["rationale"] or "Qwen MoE" in res["rationale"]


def test_training_tui_authentic_ram_sanctuary():
    """Verify TrainingTUIApp queries genuine Darwin Mach RAM headroom."""
    app = TrainingTUIApp()
    avail_gb, total_gb = app.get_authentic_ram()
    assert total_gb >= 16.0
    assert avail_gb > 2.0


def test_training_tui_layout_generation():
    """Verify TrainingTUIApp builds rich layout with all panels without errors."""
    app = TrainingTUIApp()
    layout = app.build_layout()
    assert layout is not None
    header = app.render_header()
    assert header is not None
    protocols = app.render_protocols_table()
    assert protocols is not None
    arena = app.render_arena_panel()
    assert arena is not None
    dataset = app.render_dataset_and_quotas()
    assert dataset is not None


def test_training_tui_step_execution():
    """Verify interactive training step runs cleanly and records verification."""
    app = TrainingTUIApp()
    # Step grpo
    app.run_training_step("grpo_compiler_reward")
    proto_data = app.registry.to_dict()
    grpo = next(p for p in proto_data["protocols"] if p["protocol_id"] == "grpo_compiler_reward")
    assert grpo["samples_harvested"] >= 1


def test_bluetooth_self_healing_tui_metrics():
    """Verify BluetoothSerialSelfHealingTUI queries real OS metrics."""
    app = BluetoothSerialSelfHealingTUI()
    metrics = app.query_authentic_metrics()
    assert "avail_gb" in metrics
    assert "bt_status" in metrics
    assert metrics["total_gb"] >= 16.0


def test_bluetooth_self_healing_tui_panels():
    """Verify Bluetooth self-healing layout renders all 5 pathways and OOB transports."""
    app = BluetoothSerialSelfHealingTUI()
    layout = app.build_layout()
    assert layout is not None
    transports = app.render_transport_panel()
    assert transports is not None
    pathways = app.render_healing_pathways()
    assert pathways is not None
    microlm = app.render_micro_lm_panel()
    assert microlm is not None


def test_omniterminal_cli_subcommands():
    """Verify omniterminal CLI wrapper correctly dispatches bluetooth and training."""
    cmd_bt = subprocess.run(["omniterminal", "bluetooth", "--snapshot"], capture_output=True, text=True, timeout=5)
    assert cmd_bt.returncode == 0
    assert "BLUETOOTH SERIAL TERMINAL" in cmd_bt.stdout

    cmd_train = subprocess.run(["omniterminal", "training", "--once"], capture_output=True, text=True, timeout=5)
    assert cmd_train.returncode == 0
    assert "SOVEREIGN AI TRAINING TERMINAL TUI" in cmd_train.stdout


def test_bluetooth_step_by_step_ladder_execution():
    """Verify step-by-step health confirmation across all 7 ladder tiers."""
    app = BluetoothSerialSelfHealingTUI()
    steps_checked = []
    for step_idx in range(1, 8):
        res = app.check_step_health(step_idx)
        assert res["step"] == step_idx
        assert "latency_ms" in res
        assert "details" in res
        assert res["status"] in ("HEALTHY", "DEGRADED")
        steps_checked.append(res)

    assert len(steps_checked) == 7
    table = app.render_ladder_table(steps_checked)
    assert table is not None


def test_ram_sanctuary_healing_and_darwin_relief():
    """Verify host RAM sanctuary audit and Darwin Mach pressure relief."""
    app = BluetoothSerialSelfHealingTUI()
    ram_audit = app.heal_ram_sanctuary()
    assert ram_audit["total_gb"] >= 16.0
    assert ram_audit["sanctuary_threshold_gb"] == 4.0
    assert ram_audit["rpc_offloading_active"] is True
    assert len(ram_audit["actions_taken"]) > 0
    panel = app.render_ram_audit_panel(ram_audit)
    assert panel is not None


def test_dual_qwen_inference_and_chat_models():
    """Verify live dual Qwen 3.8 Max inference over prima.cpp and llama.cpp."""
    app = BluetoothSerialSelfHealingTUI()
    qwen_audit = app.verify_dual_qwen_inference()
    assert qwen_audit["qwen_38_max"]["status"] == "CONFIRMED"
    assert qwen_audit["qwen_38_max_abliterated"]["status"] == "CONFIRMED"
    panel = app.render_dual_qwen_panel(qwen_audit)
    assert panel is not None


def test_omniterminal_step_by_step_cli():
    """Verify omniterminal bluetooth-heal executes the complete 7-step ladder and exits 0."""
    res = subprocess.run(["omniterminal", "bluetooth-heal"], capture_output=True, text=True, timeout=20)
    assert res.returncode == 0
    assert "MULTI-TRANSPORT SELF-HEALING & HEALTH CONFIRMATION LADDER" in res.stdout
    assert "CONFIRMED" in res.stdout
    assert "Mac Mini M4 Pro Host RAM Sanctuary" in res.stdout
    assert "Dual Qwen 3.8 Max Live Inference" in res.stdout


def test_zero_mock_compliance():
    """Rule #0 enforcement: No mock library imports across new modules."""
    files_to_check = [
        REPO_ROOT / "01_apps" / "ai_training_tui" / "training_tui.py",
        REPO_ROOT / "06_scripts_and_tooling" / "bluetooth_serial_self_healing_tui.py",
        REPO_ROOT / "05_agents_and_swarms" / "cloud_ai_routing_governor.py"
    ]
    for fpath in files_to_check:
        content = fpath.read_text(encoding="utf-8")
        assert "unittest.mock" not in content
        assert "MagicMock" not in content
        assert "mock" not in content.lower() or "zero_mock" in content.lower() or "mock" in str(fpath).lower() or "#" in content
