"""
test_swarm.py — Comprehensive Test Suite for Shadow Swarm Orchestration & smolctl CLI.

Validates Features F5 and F6:
  - Heterogeneous Micro-Specialist Registry & Taxonomy
  - Dynamic RAM/VRAM Capacity Governor (300MB Budget, N_local <= 3, 7-Layer Mesh Offloading)
  - Swarm Spawner, Task Dispatcher, Concurrency Governor & Lifecycle Management
  - Standalone POSIX CLI (bin/smolctl) Commands & Outputs
Authoritative Specifications: ORIGINAL_REQUEST.md §R3 & PROJECT.md §F5, §F6.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any

import pytest

from src.config import RouterConfig, get_config
from src.swarm.capacity_governor import (
    CANONICAL_MESH_MATRIX,
    CapacityGovernor,
    CapacityReport,
    MeshNodeSpec,
    ScalePlan,
)
from src.swarm.specialist_registry import (
    CANONICAL_SPECIALISTS,
    SpecialistRegistry,
    SpecialistSpec,
)
from src.swarm.swarm_controller import (
    SwarmController,
    SwarmScaleResult,
    TaskDispatchResult,
    WorkerInstance,
)

# Dynamically import bin/smolctl as a module using SourceFileLoader
SMOLCTL_PATH = Path(__file__).resolve().parent.parent / "bin" / "smolctl"
loader = importlib.machinery.SourceFileLoader("smolctl", str(SMOLCTL_PATH))
spec = importlib.util.spec_from_loader("smolctl", loader)
if spec is not None and spec.loader is not None:
    smolctl_cli = importlib.util.module_from_spec(spec)
    sys.modules["smolctl"] = smolctl_cli
    spec.loader.exec_module(smolctl_cli)
else:
    raise ImportError("Failed to load smolctl CLI module")


# ---------------------------------------------------------------------------
# Test Category 1: Specialist Registry & Taxonomy
# ---------------------------------------------------------------------------

class TestSpecialistRegistry:
    """Validates heterogeneous micro-specialist registry across architectures & quantizations."""

    def test_canonical_specialists_count_and_ids(self):
        registry = SpecialistRegistry()
        specs = registry.list_all()
        assert len(specs) == 6
        expected_ids = {
            "spec_posix_healer",
            "spec_movesense_dsp",
            "spec_ast_surgeon",
            "spec_tb4_dma",
            "spec_hf_turbo",
            "spec_ui_fuzzer",
        }
        assert {s.id for s in specs} == expected_ids

    def test_specialist_quantization_memory_bounds(self):
        registry = SpecialistRegistry()
        for spec in registry.list_all():
            if spec.quant == "IQ1_S":
                assert spec.ram_mb <= 50.0
            elif spec.quant == "IQ2_XXS":
                assert spec.ram_mb <= 100.0 or spec.specialty == "ui_fuzzer"
            elif spec.quant == "Q4_K_M":
                assert spec.ram_mb <= 220.0

    def test_find_by_language_and_specialty(self):
        registry = SpecialistRegistry()
        python_specialists = registry.find_by_language("python")
        assert len(python_specialists) >= 3  # ast_surgeon, movesense_dsp, hf_turbo
        
        rust_specialists = registry.find_by_language("rust")
        assert len(rust_specialists) >= 2  # ast_surgeon, tb4_dma

        posix_spec = registry.get_by_specialty("posix_healer")
        assert posix_spec is not None
        assert posix_spec.target_layer == "GW"
        assert "bash" in posix_spec.supported_languages

    def test_find_by_layer_and_quant(self):
        registry = SpecialistRegistry()
        gw_specs = registry.find_by_layer("GW")
        assert len(gw_specs) == 2  # posix_healer, hf_turbo

        iq1_specs = registry.find_by_quant("IQ1_S")
        assert len(iq1_specs) == 2
        for s in iq1_specs:
            assert s.ram_mb <= 45.0

    def test_dynamic_register_and_unregister(self):
        registry = SpecialistRegistry()
        custom_spec = SpecialistSpec(
            id="spec_custom_golang",
            model="Qwen2.5-0.5B-Go",
            quant="IQ2_XXS",
            ram_mb=65.0,
            specialty="go_surgeon",
            target_layer="L3",
            supported_languages=["go", "golang"],
            architecture="Qwen2.5",
        )
        registry.register(custom_spec)
        assert registry.get("spec_custom_golang") == custom_spec
        assert registry.count() == 7

        assert registry.unregister("spec_custom_golang") is True
        assert registry.get("spec_custom_golang") is None
        assert registry.count() == 6


# ---------------------------------------------------------------------------
# Test Category 2: Capacity Governor & Mesh Offload Calculations
# ---------------------------------------------------------------------------

class TestCapacityGovernor:
    """Validates dynamic memory budget enforcement and 7-layer mesh scaling math."""

    def test_local_capacity_governor_math(self):
        governor = CapacityGovernor()
        n_local = governor.compute_local_capacity()
        assert n_local == 3  # (300 - 110 - 40) // 45 = 150 // 45 = 3

    def test_allocatable_headroom_math(self):
        governor = CapacityGovernor()
        # Daemon base 110MB + 75MB workers = 185MB used
        headroom = governor.compute_allocatable_headroom(185.0)
        assert headroom == 75.0  # 300 - 185 - 40 = 75

        # Edge case: near full budget
        headroom_low = governor.compute_allocatable_headroom(270.0)
        assert headroom_low == 0.0

    def test_can_allocate_local_bounds(self):
        governor = CapacityGovernor()
        # 110MB used, requesting 42MB -> total 152MB <= 300MB -> allowed
        assert governor.can_allocate_local(110.0, 42.0) is True
        # 265MB used, requesting 45MB -> total 310MB > 300MB -> rejected
        assert governor.can_allocate_local(265.0, 45.0) is False

    def test_mesh_capacity_computation(self, mock_mesh_matrix):
        governor = CapacityGovernor(mesh_matrix=mock_mesh_matrix)
        mesh_cap = governor.compute_mesh_capacity()
        assert mesh_cap["total_mesh_workers"] > 20
        assert mesh_cap["nodes_online"] == 7
        assert "L1" in mesh_cap["layer_breakdown"]

    def test_calculate_scale_plan_distribution(self, mock_mesh_matrix):
        governor = CapacityGovernor(mesh_matrix=mock_mesh_matrix)
        plan = governor.calculate_scale_plan(target_workers=10)
        assert plan.local_allocated == 3
        assert plan.mesh_allocated == 7
        assert sum(plan.offload_by_layer.values()) == 7
        assert plan.is_feasible is True

    def test_node_offline_updates_scaling_plan(self):
        governor = CapacityGovernor()
        governor.update_node_status("L1", False)
        plan = governor.calculate_scale_plan(target_workers=10)
        assert plan.local_allocated == 3
        # L1 is offline, so overflow goes to L2 (MacBook Pro) and L3 (Linux Head Node)
        assert "L1" not in plan.offload_by_layer
        assert plan.mesh_allocated == 7
        assert plan.is_feasible is True

    def test_capacity_report_health(self):
        governor = CapacityGovernor()
        report = governor.get_capacity_report(
            current_used_mb=194.0,
            active_local_workers=2,
            active_mesh_workers=3,
        )
        assert report.is_healthy is True
        assert report.allocatable_mb == 66.0
        assert report.max_local_workers == 3


# ---------------------------------------------------------------------------
# Test Category 3: Swarm Controller Lifecycle & Task Dispatch
# ---------------------------------------------------------------------------

class TestSwarmController:
    """Validates worker lifecycle, concurrency governance, and multi-domain task dispatch."""

    def test_spawn_and_kill_worker(self):
        controller = SwarmController()
        worker = controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        assert worker.specialty == "posix_healer"
        assert worker.target_layer == "GW"
        assert worker.status == "idle"
        assert controller.get_local_worker_count() == 1
        assert controller.get_allocated_ram_mb() == 110.0 + 42.0

        # Terminate worker
        killed = controller.kill_worker(worker.worker_id)
        assert killed is True
        assert controller.get_local_worker_count() == 0
        assert controller.get_allocated_ram_mb() == 110.0

    def test_spawn_memory_limit_rejection(self):
        controller = SwarmController()
        # Spawn 3 local workers to saturate quota
        controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        assert controller.get_local_worker_count() == 3

        # 4th worker with 210MB RAM would exceed 300MB budget -> MemoryError
        with pytest.raises(MemoryError):
            controller.spawn_worker(specialty="ast_surgeon", target_layer="GW")

    def test_scale_swarm_lifecycle(self):
        controller = SwarmController()
        scale_res = controller.scale_swarm(target_workers=5, filter_specialty="posix_healer")
        assert scale_res.local_workers_spawned == 3
        assert scale_res.mesh_workers_spawned == 2
        assert len(scale_res.active_workers) == 5
        assert controller.get_local_worker_count() == 3
        assert controller.get_mesh_worker_count() == 2

        # Scale down to 2 workers
        scale_down = controller.scale_swarm(target_workers=2)
        assert len(scale_down.active_workers) == 2

    def test_prune_idle_workers(self):
        controller = SwarmController()
        w1 = controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        w2 = controller.spawn_worker(specialty="tb4_dma", target_layer="L1")
        
        # Simulate idle time
        w1.last_active_time = time.time() - 45.0  # 45s idle
        w2.last_active_time = time.time() - 5.0   # 5s idle

        pruned = controller.prune_workers(idle_seconds_threshold=30.0)
        assert w1.worker_id in pruned
        assert w2.worker_id not in pruned
        assert len(controller.list_active_workers()) == 1

    def test_multi_domain_task_dispatch(self):
        controller = SwarmController()
        
        # 1. POSIX task
        res_posix = controller.dispatch_task(
            task_id="task_uci_check",
            task_domain="posix_healer",
            prompt="check uci firewall rules",
        )
        assert res_posix.status == "success"
        assert res_posix.result["uci_status"] == "synced"

        # 2. AST code task
        code_sample = "def fib(n):\n    return n if n <= 1 else fib(n-1) + fib(n-2)\n"
        res_ast = controller.dispatch_task(
            task_id="task_ast_verify",
            task_domain="ast_surgeon",
            prompt="verify AST structure",
            payload={"code": code_sample},
        )
        assert res_ast.status == "success"
        assert res_ast.result["ast_valid"] is True
        assert res_ast.result["node_count"] == 1

        # 3. DSP IMU/ECG task
        res_dsp = controller.dispatch_task(
            task_id="task_dsp_peaks",
            task_domain="movesense_dsp",
            prompt="detect ECG peaks",
            payload={"signal": [0.1, 0.9, 0.2, 0.85, 0.1]},
        )
        assert res_dsp.status == "success"
        assert res_dsp.result["peaks_detected"] == 2

    def test_emergency_memory_pressure_handler(self):
        controller = SwarmController()
        w1 = controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        w2 = controller.spawn_worker(specialty="posix_healer", target_layer="GW")
        
        # Simulate critical RSS at 285MB (> 270MB threshold)
        killed = controller.emergency_memory_pressure_handler(current_rss_mb=285.0)
        assert len(killed) > 0
        assert controller.get_local_worker_count() < 2


# ---------------------------------------------------------------------------
# Test Category 4: Standalone smolctl CLI Testing
# ---------------------------------------------------------------------------

class TestSmolctlCli:
    """Validates smolctl POSIX CLI subcommands and JSON outputs."""

    def test_smolctl_status_cli_json(self):
        parser = smolctl_cli.build_parser()
        args = parser.parse_args(["status", "--json"])
        ret = smolctl_cli.cmd_status(args)
        assert ret == 0

    def test_smolctl_scale_cli(self):
        parser = smolctl_cli.build_parser()
        args = parser.parse_args(["scale", "--count", "4", "--json"])
        ret = smolctl_cli.cmd_scale(args)
        assert ret == 0

    def test_smolctl_spawn_and_kill_cli(self):
        parser = smolctl_cli.build_parser()
        
        # Spawn
        spawn_args = parser.parse_args(["spawn", "--specialty", "posix_healer", "--quant", "IQ1_S", "--json"])
        ret_spawn = smolctl_cli.cmd_spawn(spawn_args)
        assert ret_spawn == 0

        # Kill with invalid ID
        kill_args = parser.parse_args(["kill", "--agent-id", "non_existent_id", "--json"])
        ret_kill = smolctl_cli.cmd_kill(kill_args)
        assert ret_kill == 1  # Returns error code 1 for non-existent ID

    def test_smolctl_prune_cli(self):
        parser = smolctl_cli.build_parser()
        args = parser.parse_args(["prune", "--force", "--json"])
        ret = smolctl_cli.cmd_prune(args)
        assert ret == 0

    def test_smolctl_bench_cli(self):
        parser = smolctl_cli.build_parser()
        args = parser.parse_args(["bench", "--specialty", "posix_healer", "--iterations", "3", "--json"])
        ret = smolctl_cli.cmd_bench(args)
        assert ret == 0

    def test_smolctl_nested_swarm_subcommand_syntax(self):
        parser = smolctl_cli.build_parser()
        args = parser.parse_args(["swarm", "status", "--json"])
        ret = smolctl_cli.cmd_status(args)
        assert ret == 0

    def test_smolctl_binary_executable_execution(self):
        cli_path = SMOLCTL_PATH
        assert cli_path.exists()
        assert os.access(cli_path, os.X_OK)

        proc = subprocess.run(
            [str(cli_path), "status", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        assert "allocated_ram_mb" in data
        assert "max_ram_mb" in data
        assert data["max_ram_mb"] == 300.0
