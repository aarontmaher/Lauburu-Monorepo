"""
tests/test_tier5_adversarial_ram.py
Tier 5: Adversarial Stress-Testing & Failure-Mode Challenge Suite
================================================================
Subsystem: 01_apps/bt_ide_ab_test
Author: teamwork_preview_challenger_1 (EMPIRICAL CHALLENGER)

Adversarially tests and challenges:
1. Extreme Memory Saturation Boundaries:
   - Exact 4915.2 MB (4.8 GB) Mac Mini Sanctuary boundary vs fractional epsilon
   - Rapidly oscillating RAM metrics (flapping / absence of hysteresis damping)
   - Simultaneous remote IP timeouts and false backpressure triggering on local IDE
   - Zero-node and corrupted/negative telemetry injection
2. Process Suspension Mechanics:
   - Invariant: IDE_CRITICAL and HIGH tasks are NEVER suspended under any pressure
   - Strict priority-ordered resumption: MEDIUM (2) strictly resumes before LOW (1)
   - Error handling: Dead/non-existent PIDs, permission denial (EPERM), negative PIDs
   - Unhandled return values: Return code of _signal_pid and _signal_http_endpoint ignored
   - Physical OS process actuation: Genuine subprocess SIGSTOP (state 'T') and SIGCONT (state 'S/R')
   - Graduated suspension vs unconditional suspension discrepancy
   - Dangerous PID registration (pid <= 0) lack of validation
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

import pytest

# Ensure project root is available
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    GLOBAL_CRITICAL_HEADROOM_GB,
    GLOBAL_POOL_SATURATION_PCT,
    HOST_MAX_UTILIZATION_PCT,
    HOST_SANCTUARY_MIN_MB,
    MESH_NODES,
    NodeConfig,
    NodeLayer,
    SubagentPriority,
    TOTAL_MESH_RAM_GB,
    USABLE_AI_VRAM_GB,
)
from core.ram_governor import (
    BackpressureSuspensionManager,
    GlobalRAMPoolMetric,
    MeshRAMGovernorCoordinator,
    TaskRecord,
    compute_global_pool_metric,
)
from core.telemetry import (
    MeshTelemetryCollector,
    NodeMemoryTelemetry,
    evaluate_node_saturation,
)


# ==============================================================================
# SECTION 1: Extreme Memory Saturation Boundaries
# ==============================================================================

class TestAdversarialMemoryBoundaries:
    """Stress-tests boundary conditions, floating-point precision, and network isolation."""

    def test_adv_exact_sanctuary_boundary_4915_2mb(self):
        """
        Challenge 1.1: Exact threshold test at 4915.2 MB (4.8 GB * 1024).
        Investigate whether exactly 4915.2 MB available RAM triggers saturation or remains healthy,
        and whether fractional epsilon offsets (0.0001 MB) cause abrupt state transitions.
        """
        exact_mb = 4915.2
        total_mb = 24576.0
        # Exactly 80.0% utilization: (24576.0 - 4915.2) / 24576.0 = 0.80
        util_exact = 80.0

        # Sub-test A: Exactly 4915.2 MB and 80.0% utilization in evaluate_node_saturation
        thresh, is_sat = evaluate_node_saturation(
            NodeLayer.L1.value, total_mb, exact_mb, util_exact, MESH_NODES[NodeLayer.L1.value]
        )
        assert thresh == HOST_SANCTUARY_MIN_MB
        # At exactly 4915.2 MB and 80.0% util, it is strictly on the boundary (not < 4915.2 and not > 80.0)
        assert is_sat is False, "Exact boundary 4915.2 MB with 80.0% util must NOT be flagged saturated"

        # Sub-test B: Infinitesimal deficit (-0.001 MB)
        _, is_sat_under = evaluate_node_saturation(
            NodeLayer.L1.value, total_mb, exact_mb - 0.001, util_exact, MESH_NODES[NodeLayer.L1.value]
        )
        assert is_sat_under is True, "4915.199 MB must immediately flag saturated"

        # Sub-test C: Floating point rounding trap where available_mb is 4915.2, but util is 80.001%
        _, is_sat_util_overflow = evaluate_node_saturation(
            NodeLayer.L1.value, total_mb, exact_mb, 80.001, MESH_NODES[NodeLayer.L1.value]
        )
        assert is_sat_util_overflow is True, "Utilization exceeding 80.0% must trigger saturation even if available_mb == 4915.2"

        # Sub-test D: Mesh-level evaluation with other nodes healthy (> 10GB total available)
        l1_telemetry = NodeMemoryTelemetry(
            node_id="L1_Mac_Host",
            ip="127.0.0.1",
            total_ram_mb=total_mb,
            free_ram_mb=exact_mb,
            available_ram_mb=exact_mb,
            utilization_pct=util_exact,
            dynamic_safety_threshold_mb=HOST_SANCTUARY_MIN_MB,
            is_saturated=False,
            is_reachable=True,
            rtt_ms=0.0,
        )
        l2_telemetry = NodeMemoryTelemetry(
            node_id="L2_MacBook_Pro",
            ip="192.168.2.3",
            total_ram_mb=16384.0,
            free_ram_mb=8000.0,
            available_ram_mb=8000.0,
            utilization_pct=51.2,
            dynamic_safety_threshold_mb=1638.4,
            is_saturated=False,
            is_reachable=True,
            rtt_ms=0.5,
        )
        pool = compute_global_pool_metric([l1_telemetry, l2_telemetry])
        assert pool.backpressure_triggered is False
        assert "L1_Mac_Host" not in pool.saturated_nodes

    def test_adv_rapid_ram_oscillation_flapping_vulnerability(self):
        """
        Challenge 1.2: Rapidly oscillating RAM metrics across consecutive governance cycles.
        Simulates memory hovering right around 4915.2 MB (e.g., 4910 MB <-> 4920 MB)
        every second for 10 cycles.

        EMPIRICAL OBSERVATION:
        The current architecture lacks hysteresis damping (e.g. Schmitt trigger, deadband,
        or recovery holdoff time). This causes the governor to flap between apply_backpressure
        and release_backpressure on EVERY cycle, generating a storm of pause/resume events.
        """
        coordinator = MeshRAMGovernorCoordinator()
        mgr = coordinator.suspension_mgr

        # Register background tasks
        mgr.register_task("lora_worker", "24/7 LoRA Harvester", SubagentPriority.LOW)
        mgr.register_task("benchmark_worker", "Continuous Benchmarker", SubagentPriority.MEDIUM)

        healthy_l2 = NodeMemoryTelemetry(
            "L2_MacBook_Pro", "192.168.2.3", 16384.0, 8000.0, 8000.0, 51.2, 1638.4, False, True, 0.5
        )

        suspend_count = 0
        resume_count = 0

        # Simulate 10 oscillations between 4910 MB (saturated) and 4920 MB (healthy)
        for cycle in range(10):
            if cycle % 2 == 0:
                # Cycle 0, 2, 4, 6, 8: Memory drops slightly below threshold (4910 MB, 80.02% util)
                t_l1 = NodeMemoryTelemetry(
                    "L1_Mac_Host", "127.0.0.1", 24576.0, 4910.0, 4910.0, 80.02,
                    HOST_SANCTUARY_MIN_MB, True, True, 0.0
                )
            else:
                # Cycle 1, 3, 5, 7, 9: Memory recovers slightly above threshold (4920 MB, 79.98% util)
                t_l1 = NodeMemoryTelemetry(
                    "L1_Mac_Host", "127.0.0.1", 24576.0, 4920.0, 4920.0, 79.98,
                    HOST_SANCTUARY_MIN_MB, False, True, 0.0
                )

            pool, _, actions = asyncio.run(coordinator.evaluate_mesh(simulated_telemetry=[t_l1, healthy_l2]))

            if actions["tasks_suspended"]:
                suspend_count += 1
            if actions["tasks_resumed"]:
                resume_count += 1

        # VERIFIED HYSTERESIS DAMPING:
        # In 10 oscillating cycles, the system triggered exactly 1 initial suspension and 0 resumptions,
        # because the recovery threshold (+512 MB, >= 5427.2 MB) was not reached. Zero flapping!
        assert suspend_count == 1, f"Expected 1 suspension with hysteresis damping, got {suspend_count}"
        assert resume_count == 0, f"Expected 0 resumptions without hitting recovery threshold, got {resume_count}"

    def test_adv_all_remote_ips_timeout_causes_false_backpressure(self):
        """
        Challenge 1.3: What happens if all remote IPs time out simultaneously?
        Simulates L1 Mac Mini running healthy with 18.0 GB available RAM, but all remote nodes
        (L2-L7, GW) are unreachable because the mesh network is partitioned or offline.

        EMPIRICAL OBSERVATION & DESIGN DEFECT:
        1. When all remote nodes are unreachable, poll_node sets:
           - available_ram_mb = 0.0
           - is_saturated = True (Safety default when unreachable)
           - is_reachable = False
        2. compute_global_pool_metric checks:
           `for t in telemetry_list: if t.is_saturated: saturated_nodes.append(t.node_id)`
        3. As a result, all 7 unreachable nodes are marked as SATURATED NODES!
        4. Since len(saturated_nodes) >= 2 is True, backpressure_triggered becomes True!
        5. Thus, an offline network partitions the cluster and forces L1 into backpressure,
           even though L1 Mac Mini has 18 GB free RAM and 0% saturation!
        """
        # Create full 8-node telemetry where L1 is completely healthy, but L2-GW are unreachable
        telemetry: List[NodeMemoryTelemetry] = []

        # L1: Fully healthy (18 GB free out of 24 GB, 26.8% util)
        telemetry.append(
            NodeMemoryTelemetry(
                node_id="L1_Mac_Host",
                ip="127.0.0.1",
                total_ram_mb=24576.0,
                free_ram_mb=18432.0,
                available_ram_mb=18432.0,
                utilization_pct=26.8,
                dynamic_safety_threshold_mb=HOST_SANCTUARY_MIN_MB,
                is_saturated=False,
                is_reachable=True,
                rtt_ms=0.0,
            )
        )

        # Peripheral nodes L2-GW: all unreachable
        for node_id, cfg in MESH_NODES.items():
            if node_id == NodeLayer.L1.value:
                continue
            telemetry.append(
                NodeMemoryTelemetry(
                    node_id=node_id,
                    ip=cfg.ip_priority_list[0] if cfg.ip_priority_list else "unknown",
                    total_ram_mb=cfg.nominal_ram_mb,
                    free_ram_mb=0.0,
                    available_ram_mb=0.0,
                    utilization_pct=100.0,
                    dynamic_safety_threshold_mb=cfg.min_sanctuary_free_mb,
                    is_saturated=True,  # Set by poll_node when all IPs timeout
                    is_reachable=False,
                    rtt_ms=-1.0,
                )
            )

        pool = compute_global_pool_metric(telemetry)

        # Verify findings:
        assert pool.nodes_reporting == 1, "Only L1 is reporting"
        assert pool.nodes_total == len(MESH_NODES)
        assert len(pool.saturated_nodes) == 0, (
            "Unreachable remote nodes during network partition must not be counted as saturated!"
        )

        # VERIFIED REMEDIATION:
        # pool.backpressure_triggered is False because L1 has 18 GB available RAM,
        # unreachable nodes have is_saturated=False, and partition does not lock out local IDE!
        assert pool.backpressure_triggered is False, (
            "Unreachable remote nodes must never trigger global backpressure on local IDE when host is healthy!"
        )

    def test_adv_corrupt_negative_and_nan_telemetry_isolation(self):
        """
        Challenge 1.4: Inject corrupt telemetry: negative available RAM, NaN utilization, 0 total RAM.
        System must not raise ZeroDivisionError or crash.
        """
        corrupt_telemetry = [
            NodeMemoryTelemetry(
                node_id="L1_Mac_Host",
                ip="127.0.0.1",
                total_ram_mb=0.0,  # 0 total RAM edge
                free_ram_mb=-500.0,  # Negative free RAM
                available_ram_mb=-1000.0,
                utilization_pct=float("nan"),  # NaN util
                dynamic_safety_threshold_mb=4915.2,
                is_saturated=True,
                is_reachable=True,
                rtt_ms=0.0,
            )
        ]

        # Must not throw UnboundLocalError or ZeroDivisionError
        pool = compute_global_pool_metric(corrupt_telemetry)
        assert pool.nodes_reporting == 1
        assert pool.backpressure_triggered is True
        assert pool.total_mesh_ram_gb > 0  # Falls back to TOTAL_MESH_RAM_GB nominal


# ==============================================================================
# SECTION 2: Process Suspension Mechanics
# ==============================================================================

class TestAdversarialSuspensionMechanics:
    """Stress-tests task priority rules, resumption ordering, and OS signal fault tolerance."""

    def test_adv_ide_critical_and_high_never_suspended(self):
        """
        Challenge 2.1: Verify that IDE_CRITICAL and HIGH tasks are NEVER suspended,
        even under extreme catastrophic memory saturation (100% mesh RAM utilization, 0 MB free).
        """
        mgr = BackpressureSuspensionManager()

        # Register tasks across all priority classes
        t_low1 = mgr.register_task("task_low_lora", "LoRA Harvester", SubagentPriority.LOW)
        t_low2 = mgr.register_task("task_low_ast", "AST Crawler", SubagentPriority.LOW)
        t_med = mgr.register_task("task_med_bench", "Continuous Benchmarker", SubagentPriority.MEDIUM)
        t_high = mgr.register_task("task_high_debate", "AI Debate Council", SubagentPriority.HIGH)
        t_crit = mgr.register_task("task_crit_ide", "Active User IDE Session", SubagentPriority.IDE_CRITICAL)

        # Catastrophic memory saturation
        catastrophic_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=0.1,
            usable_ai_vram_gb=0.0,
            pool_utilization_pct=99.9,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=list(MESH_NODES.keys()),
        )

        suspended_ids = asyncio.run(mgr.apply_backpressure(catastrophic_metric))

        # Check suspended tasks
        assert "task_low_lora" in suspended_ids
        assert "task_low_ast" in suspended_ids
        assert "task_med_bench" in suspended_ids

        # CRITICAL INVARIANT: HIGH and IDE_CRITICAL must NEVER be suspended
        assert "task_high_debate" not in suspended_ids
        assert "task_crit_ide" not in suspended_ids

        assert t_high.status == "RUNNING"
        assert t_high.suspended_at is None
        assert t_crit.status == "RUNNING"
        assert t_crit.suspended_at is None

    def test_adv_strict_priority_ordered_resumption(self):
        """
        Challenge 2.2: Verify that LOW and MEDIUM tasks resume in strict priority order.
        MEDIUM (Priority 2) must resume BEFORE LOW (Priority 1) to restore high-value tasks first.
        """
        mgr = BackpressureSuspensionManager()

        # Register 2 LOW tasks and 2 MEDIUM tasks
        mgr.register_task("low_task_1", "LoRA Harvester 1", SubagentPriority.LOW)
        mgr.register_task("med_task_1", "Benchmarker 1", SubagentPriority.MEDIUM)
        mgr.register_task("low_task_2", "AST Crawler 2", SubagentPriority.LOW)
        mgr.register_task("med_task_2", "Benchmarker 2", SubagentPriority.MEDIUM)

        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=1.0,
            usable_ai_vram_gb=0.5,
            pool_utilization_pct=99.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"],
        )

        # Suspend all
        asyncio.run(mgr.apply_backpressure(saturated_metric))
        assert len(mgr.list_tasks(status="SUSPENDED")) == 4

        # Track resume sequence
        resumed_sequence: List[Tuple[str, int]] = []

        def capture_resume(task: TaskRecord):
            resumed_sequence.append((task.task_id, task.priority.value))

        mgr.on_resume_hook = capture_resume

        resumed_ids = asyncio.run(mgr.release_backpressure())

        # Assert returned list order
        assert len(resumed_ids) == 4
        # First two must be MEDIUM (priority 2), last two must be LOW (priority 1)
        assert resumed_ids[0] in ("med_task_1", "med_task_2")
        assert resumed_ids[1] in ("med_task_1", "med_task_2")
        assert resumed_ids[2] in ("low_task_1", "low_task_2")
        assert resumed_ids[3] in ("low_task_1", "low_task_2")

        # Verify hook invocation order
        assert len(resumed_sequence) == 4
        assert resumed_sequence[0][1] == SubagentPriority.MEDIUM.value
        assert resumed_sequence[1][1] == SubagentPriority.MEDIUM.value
        assert resumed_sequence[2][1] == SubagentPriority.LOW.value
        assert resumed_sequence[3][1] == SubagentPriority.LOW.value

    def test_adv_unhandled_failure_modes_in_process_signaling(self):
        """
        Challenge 2.3: Verify behavior when SIGSTOP is sent to non-existent PIDs,
        or when process signaling fails due to permissions (EPERM).

        VULNERABILITY CONFIRMED:
        In core/ram_governor.py lines 279-295:
            if task.pid is not None:
                self._signal_pid(task.pid, signal.SIGSTOP)
            task.status = "SUSPENDED"
            suspended_ids.append(task.task_id)

        The return value of self._signal_pid (which returns False on ProcessLookupError
        or PermissionError) is completely IGNORED!
        Even if the process does not exist or permission is denied, the task is marked
        as "SUSPENDED" and reported in suspended_ids!
        """
        mgr = BackpressureSuspensionManager()

        # Non-existent PID
        ghost_pid = 99999999
        t_ghost = mgr.register_task(
            "ghost_task", "Ghost Subagent", SubagentPriority.LOW, pid=ghost_pid
        )

        # Root/launchd PID 1 (Permission denied to non-root)
        t_root = mgr.register_task(
            "root_task", "Root Protected Process", SubagentPriority.LOW, pid=1
        )

        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=2.0,
            usable_ai_vram_gb=1.0,
            pool_utilization_pct=95.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"],
        )

        # Directly test _signal_pid return values
        assert mgr._signal_pid(ghost_pid, signal.SIGSTOP) is False, (
            "_signal_pid must return False for non-existent PID"
        )
        assert mgr._signal_pid(1, signal.SIGSTOP) is False, (
            "_signal_pid must return False for PID 1 due to permission denial"
        )

        # Now apply backpressure through the manager
        suspended_ids = asyncio.run(mgr.apply_backpressure(saturated_metric))

        # VERIFIED REMEDIATION:
        # Both ghost_task and root_task failed OS signaling and are NOT marked SUSPENDED!
        assert "ghost_task" not in suspended_ids
        assert t_ghost.status == "FAILED_TO_SUSPEND", (
            "Task correctly marked FAILED_TO_SUSPEND when PID does not exist"
        )

        assert "root_task" not in suspended_ids
        assert t_root.status == "FAILED_TO_SUSPEND", (
            "Task correctly marked FAILED_TO_SUSPEND on PermissionError"
        )

    def test_adv_unhandled_failure_modes_in_http_hooks(self):
        """
        Challenge 2.4: Verify behavior when remote HTTP endpoint fails (e.g. port closed, 500 error).
        Like _signal_pid, the return value of _signal_http_endpoint is ignored by apply_backpressure.
        """
        mgr = BackpressureSuspensionManager()

        # Endpoint on unused loopback port (connection refused)
        dead_endpoint = "http://127.0.0.1:59999"
        t_remote = mgr.register_task(
            "remote_task", "Remote Daemon", SubagentPriority.LOW, endpoint=dead_endpoint
        )

        saturated_metric = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=2.0,
            usable_ai_vram_gb=1.0,
            pool_utilization_pct=95.0,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L1_Mac_Host"],
        )

        # _signal_http_endpoint returns False
        hook_res = asyncio.run(mgr._signal_http_endpoint(dead_endpoint, "suspend"))
        assert hook_res is False

        # Apply backpressure checks HTTP hook status
        suspended_ids = asyncio.run(mgr.apply_backpressure(saturated_metric))
        assert "remote_task" not in suspended_ids
        assert t_remote.status == "FAILED_TO_SUSPEND"

    def test_adv_real_os_process_sigstop_sigcont_actuation(self):
        """
        Challenge 2.5: Physical Process Actuation Proof (Rule 1 & Rule 5 Tri-Proof).
        Spawns a genuine long-running background Python subprocess, attaches it to a LOW task,
        applies backpressure, verifies process state changes to STOPPED ('T'),
        then releases backpressure and verifies it resumes execution ('S' or 'R').
        """
        # Spawn a genuine worker subprocess running a sleep loop
        worker_code = (
            "import sys, time\n"
            "for i in range(500):\n"
            "    time.sleep(0.02)\n"
            "sys.exit(0)\n"
        )
        proc = subprocess.Popen([sys.executable, "-c", worker_code])
        pid = proc.pid

        try:
            # Helper to query macOS/Darwin process state
            def get_proc_state(p: int) -> str:
                try:
                    res = subprocess.check_output(["ps", "-o", "state=", "-p", str(p)])
                    return res.decode().strip()
                except Exception:
                    return ""

            initial_state = get_proc_state(pid)
            assert initial_state != "", f"Process {pid} failed to launch"
            assert "T" not in initial_state, f"Process {pid} should not be in stopped state initially"

            mgr = BackpressureSuspensionManager()
            task = mgr.register_task("real_worker", "Genuine Worker Process", SubagentPriority.LOW, pid=pid)

            saturated_metric = GlobalRAMPoolMetric(
                total_mesh_ram_gb=108.0,
                available_mesh_ram_gb=2.0,
                usable_ai_vram_gb=1.0,
                pool_utilization_pct=95.0,
                nodes_reporting=7,
                nodes_total=7,
                backpressure_triggered=True,
                saturated_nodes=["L1_Mac_Host"],
            )

            # 1. Apply backpressure -> sends SIGSTOP to pid
            suspended_ids = asyncio.run(mgr.apply_backpressure(saturated_metric))
            assert "real_worker" in suspended_ids
            assert task.status == "SUSPENDED"

            # Allow OS kernel signal dispatch
            time.sleep(0.05)
            stopped_state = get_proc_state(pid)
            # In Darwin ps: 'T' represents stopped by signal (SIGSTOP)
            assert "T" in stopped_state, f"Process {pid} should have state 'T' (stopped), got '{stopped_state}'"

            # 2. Release backpressure -> sends SIGCONT to pid
            resumed_ids = asyncio.run(mgr.release_backpressure())
            assert "real_worker" in resumed_ids
            assert task.status == "RUNNING"

            # Allow OS kernel signal dispatch
            time.sleep(0.05)
            resumed_state = get_proc_state(pid)
            assert "T" not in resumed_state, (
                f"Process {pid} should resume from state 'T', got '{resumed_state}'"
            )

        finally:
            # Terminate test subprocess cleanly
            try:
                proc.terminate()
                proc.wait(timeout=1.0)
            except Exception:
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass

    def test_adv_unconditional_suspension_vs_claimed_graduated_behavior(self):
        """
        Challenge 2.6: Discrepancy between docstring contract and implementation.
        Docstring in ram_governor.py says:
        'LOW tasks are suspended first, followed by MEDIUM if memory is severely constrained.'

        EMPIRICAL OBSERVATION:
        The code unconditionally suspends ALL candidates below min_protected_priority
        (both LOW and MEDIUM) on ANY backpressure trigger, even for mild saturation (e.g. 85.1%).
        There is zero graduated suspension logic based on severity!
        """
        mgr = BackpressureSuspensionManager()
        mgr.register_task("low_1", "Low Priority Worker", SubagentPriority.LOW)
        mgr.register_task("med_1", "Medium Priority Worker", SubagentPriority.MEDIUM)

        # Mild saturation: 85.1% pool util (just above 85.0% threshold)
        mild_saturation = GlobalRAMPoolMetric(
            total_mesh_ram_gb=108.0,
            available_mesh_ram_gb=16.0,
            usable_ai_vram_gb=12.0,
            pool_utilization_pct=85.1,
            nodes_reporting=7,
            nodes_total=7,
            backpressure_triggered=True,
            saturated_nodes=["L6_Pixel_10_Edge"],
        )

        suspended = asyncio.run(mgr.apply_backpressure(mild_saturation))

        # Both LOW and MEDIUM are suspended despite mild saturation
        assert "low_1" in suspended
        assert "med_1" in suspended, (
            "Empirically confirmed: MEDIUM tasks are suspended immediately without severity check"
        )

    def test_adv_dangerous_pid_registration_and_lack_of_validation(self):
        """
        Challenge 2.7: Input validation vulnerability on registered PIDs.
        In POSIX:
          os.kill(0, sig) signals every process in the current process group!
          os.kill(-1, sig) signals every process the user has permission to signal!
        register_task does not validate that pid is a positive integer (> 0).
        If pid=0 is registered and signaled with SIGSTOP, it freezes the entire process group.
        """
        mgr = BackpressureSuspensionManager()

        # register_task validates pid > 0 and raises ValueError for pid <= 0
        with pytest.raises(ValueError, match="PID must be a positive integer"):
            mgr.register_task("zero_pid_task", "Dangerous Zero PID", SubagentPriority.LOW, pid=0)

        with pytest.raises(ValueError, match="PID must be a positive integer"):
            mgr.register_task("neg_pid_task", "Dangerous Neg PID", SubagentPriority.LOW, pid=-1)
