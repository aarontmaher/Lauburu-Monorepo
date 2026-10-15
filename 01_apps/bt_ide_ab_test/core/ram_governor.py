"""
Dynamic Global Mesh RAM Governor & Backpressure Suspension Manager
==================================================================
Subsystem: 01_apps/bt_ide_ab_test/core/ram_governor.py
Lauburu Mesh Ecosystem — 2026

Calculates the Global RAM Pool Metric (108.0 GB RAM / 82.8 GB usable AI VRAM)
across the 7-layer mesh, evaluates per-node dynamic safety thresholds (Rule 3, Rule 0),
and executes Backpressure Suspension to halt low-priority background subagents
(LoRA Harvester, AST Crawler) under memory saturation to protect the active IDE session.
"""

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
import logging
import os
from pathlib import Path
import signal
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import httpx

from core.config import (
    GLOBAL_CRITICAL_HEADROOM_GB,
    GLOBAL_POOL_SATURATION_PCT,
    HOST_MAX_UTILIZATION_PCT,
    HOST_SANCTUARY_MIN_GB,
    HOST_SANCTUARY_MIN_MB,
    HOST_SANCTUARY_RECOVERY_HEADROOM_MB,
    HOST_SANCTUARY_RECOVERY_MB,
    MESH_NODES,
    NodeConfig,
    NodeLayer,
    SubagentPriority,
    TOTAL_MESH_RAM_GB,
    USABLE_AI_VRAM_GB,
)
from core.telemetry import MeshTelemetryCollector, NodeMemoryTelemetry

logger = logging.getLogger("RAMGovernor")


# ---------------------------------------------------------------------------
# Data Contracts (PROJECT.md § 4.1)
# ---------------------------------------------------------------------------
@dataclass
class GlobalRAMPoolMetric:
    """Aggregated cluster memory pool metric across all reporting mesh layers."""
    total_mesh_ram_gb: float          # Nominal ~108.0 GB
    available_mesh_ram_gb: float
    usable_ai_vram_gb: float          # Nominal ~82.8 GB
    pool_utilization_pct: float
    nodes_reporting: int
    nodes_total: int
    backpressure_triggered: bool
    saturated_nodes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskRecord:
    """Registered subagent or background process governed by backpressure."""
    task_id: str
    name: str
    priority: SubagentPriority
    pid: Optional[int] = None
    endpoint: Optional[str] = None
    status: str = "RUNNING"  # "RUNNING", "SUSPENDED"
    suspended_at: Optional[float] = None
    resumed_at: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority.value
        return d


# ---------------------------------------------------------------------------
# Global Pool Metric Calculation & Safety Evaluation
# ---------------------------------------------------------------------------
def compute_global_pool_metric(
    telemetry_list: List[NodeMemoryTelemetry],
    nodes_config: Optional[Dict[str, NodeConfig]] = None,
    l1_backpressure_active: bool = False,
) -> GlobalRAMPoolMetric:
    """
    Computes cluster-wide RAM pool metrics and evaluates dynamic safety thresholds.
    Enforces Rule 3 (Host Sanctuary: L1 >= 4.8GB free, util <= 80%) and peripheral caps.
    Includes hysteresis damping: once L1 backpressure is active, releases only after
    recovering by >= +512 MB above sanctuary threshold (>= 5427.2 MB).
    """
    cfg_map = nodes_config or MESH_NODES
    total_nodes = len(telemetry_list)
    reporting_nodes = sum(1 for t in telemetry_list if t.is_reachable)

    # Sum total RAM across all nodes in the evaluation list (MB converted to GB)
    total_mesh_ram_gb = round(sum(t.total_ram_mb for t in telemetry_list) / 1024.0, 2)
    if total_mesh_ram_gb <= 0:
        total_mesh_ram_gb = TOTAL_MESH_RAM_GB

    # Sum available RAM strictly from reachable, healthy nodes
    available_mesh_ram_gb = round(
        sum(t.available_ram_mb for t in telemetry_list if t.is_reachable) / 1024.0, 2
    )

    # Calculate usable AI VRAM: each reachable node contributes available RAM up to its AI cap
    usable_vram_sum = 0.0
    for t in telemetry_list:
        if t.is_reachable:
            cfg = cfg_map.get(t.node_id)
            ai_cap = cfg.nominal_ai_cap_gb if cfg else (t.total_ram_mb / 1024.0 * 0.8)
            node_vram = min(t.available_ram_mb / 1024.0, ai_cap)
            usable_vram_sum += max(0.0, node_vram)
    usable_ai_vram_gb = round(min(USABLE_AI_VRAM_GB, usable_vram_sum), 2)

    # Cluster-wide pool utilization
    if total_mesh_ram_gb > 0:
        pool_utilization_pct = round(
            ((total_mesh_ram_gb - available_mesh_ram_gb) / total_mesh_ram_gb) * 100.0, 2
        )
    else:
        pool_utilization_pct = 100.0

    # Saturated nodes list (only reachable nodes are evaluated)
    saturated_nodes: List[str] = []
    l1_saturated = False

    for t in telemetry_list:
        cfg = cfg_map.get(t.node_id)
        is_node_saturated = t.is_saturated

        # Explicit check for L1 Mac Host Sanctuary (Rule 3) with hysteresis damping
        if t.node_id == NodeLayer.L1.value:
            # If L1 backpressure is active, require recovery headroom (+512 MB above 4915.2 MB = 5427.2 MB)
            threshold_to_check = HOST_SANCTUARY_RECOVERY_MB if l1_backpressure_active else HOST_SANCTUARY_MIN_MB
            if (t.available_ram_mb < threshold_to_check) or (t.utilization_pct > HOST_MAX_UTILIZATION_PCT):
                is_node_saturated = True
                if t.is_reachable:
                    l1_saturated = True
            else:
                is_node_saturated = False

        # Explicit check for L3 Linux Hub cap (80%)
        elif t.node_id == NodeLayer.L3.value:
            if t.utilization_pct > 80.0:
                is_node_saturated = True

        # Explicit check for L6 Pixel 10 Edge cap (85%)
        elif t.node_id == NodeLayer.L6.value:
            if t.utilization_pct > 85.0:
                is_node_saturated = True

        # Only reachable nodes should be considered saturated
        if t.is_reachable and is_node_saturated:
            saturated_nodes.append(t.node_id)

    # Backpressure triggers if:
    # 1. Zero reachable nodes reporting
    # 2. L1 Mac Host is saturated (Rule 3 Host Sanctuary breach)
    # 3. 2 or more reachable nodes are saturated
    # 4. Global pool saturation:
    #    - If all nodes reporting: pool_utilization_pct >= 85.0% or available_mesh_ram_gb < 10.0 GB
    #    - If network partition (unreachable remote nodes): unreachable remote nodes must NEVER
    #      trigger cluster backpressure when the local Mac Mini host has plenty of free RAM.
    if reporting_nodes == 0:
        backpressure_triggered = True
    elif l1_saturated:
        backpressure_triggered = True
    elif len(saturated_nodes) >= 2:
        backpressure_triggered = True
    elif reporting_nodes == total_nodes:
        backpressure_triggered = bool(
            (pool_utilization_pct >= GLOBAL_POOL_SATURATION_PCT)
            or (available_mesh_ram_gb < GLOBAL_CRITICAL_HEADROOM_GB)
        )
    else:
        # Partial network partition: check reporting nodes' pool utilization
        reporting_ram_gb = sum(t.total_ram_mb for t in telemetry_list if t.is_reachable) / 1024.0
        if reporting_ram_gb > 0:
            reporting_util_pct = ((reporting_ram_gb - available_mesh_ram_gb) / reporting_ram_gb) * 100.0
            backpressure_triggered = bool(reporting_util_pct >= GLOBAL_POOL_SATURATION_PCT)
        else:
            backpressure_triggered = False

    return GlobalRAMPoolMetric(
        total_mesh_ram_gb=total_mesh_ram_gb,
        available_mesh_ram_gb=available_mesh_ram_gb,
        usable_ai_vram_gb=usable_ai_vram_gb,
        pool_utilization_pct=pool_utilization_pct,
        nodes_reporting=reporting_nodes,
        nodes_total=total_nodes,
        backpressure_triggered=backpressure_triggered,
        saturated_nodes=saturated_nodes,
    )


# ---------------------------------------------------------------------------
# Backpressure Suspension Manager
# ---------------------------------------------------------------------------
class BackpressureSuspensionManager:
    """
    Manages task registration and executes pause/resume signals:
    - Local PIDs: SIGSTOP / SIGCONT
    - Remote HTTP hooks: POST /suspend /resume
    - Priority classes: LOW, MEDIUM, HIGH, IDE_CRITICAL
    """

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}
        self.on_suspend_hook: Optional[Callable[[TaskRecord], None]] = None
        self.on_resume_hook: Optional[Callable[[TaskRecord], None]] = None

    def register_task(
        self,
        task_id: str,
        name: str,
        priority: SubagentPriority,
        pid: Optional[int] = None,
        endpoint: Optional[str] = None,
        notes: str = "",
    ) -> TaskRecord:
        """Registers a subagent or task for backpressure governance."""
        if pid is not None and pid <= 0:
            raise ValueError(f"Invalid PID {pid}: PID must be a positive integer (> 0).")

        record = TaskRecord(
            task_id=task_id,
            name=name,
            priority=priority,
            pid=pid,
            endpoint=endpoint,
            status="RUNNING",
            notes=notes,
        )
        self._tasks[task_id] = record
        logger.info(f"Registered task '{name}' (ID: {task_id}, Priority: {priority.name})")
        return record

    def unregister_task(self, task_id: str) -> bool:
        """Unregisters a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[TaskRecord]:
        if status:
            return [t for t in self._tasks.values() if t.status == status]
        return list(self._tasks.values())

    def _signal_pid(self, pid: int, sig: int) -> bool:
        """Sends OS signal (SIGSTOP/SIGCONT) to a local process."""
        try:
            os.kill(pid, sig)
            return True
        except ProcessLookupError:
            logger.warning(f"Process {pid} no longer exists.")
            return False
        except PermissionError:
            logger.warning(f"Permission denied signaling process {pid}.")
            return False
        except Exception as e:
            logger.warning(f"Error signaling process {pid}: {e}")
            return False

    async def _signal_http_endpoint(self, endpoint: str, action: str) -> bool:
        """Sends HTTP hook to remote daemon (/suspend or /resume)."""
        url = f"{endpoint.rstrip('/')}/{action}"
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.post(url, json={"action": action, "timestamp": time.time()})
                return resp.status_code in (200, 202, 204)
        except Exception as e:
            logger.warning(f"Failed to send HTTP {action} to {url}: {e}")
            return False

    async def apply_backpressure(
        self,
        pool_metric: GlobalRAMPoolMetric,
        min_protected_priority: SubagentPriority = SubagentPriority.HIGH,
    ) -> List[str]:
        """
        Executes backpressure suspension on running tasks below min_protected_priority.
        LOW tasks are suspended first, followed by MEDIUM if memory is severely constrained.
        Returns list of task IDs that were suspended.
        """
        if not pool_metric.backpressure_triggered:
            return []

        suspended_ids: List[str] = []

        # Sort candidate tasks: LOW (1) first, then MEDIUM (2)
        candidates = [
            t for t in self._tasks.values()
            if t.status == "RUNNING" and t.priority < min_protected_priority
        ]
        candidates.sort(key=lambda t: t.priority.value)

        for task in candidates:
            signaling_failed = False

            # 1. Local process suspension via SIGSTOP
            if task.pid is not None:
                if not self._signal_pid(task.pid, signal.SIGSTOP):
                    signaling_failed = True
                    task.status = "FAILED_TO_SUSPEND"
                    logger.warning(f"Failed to signal PID {task.pid} for task '{task.task_id}'.")

            # 2. Remote HTTP suspension hook
            if task.endpoint is not None and not signaling_failed:
                if not await self._signal_http_endpoint(task.endpoint, "suspend"):
                    signaling_failed = True
                    task.status = "FAILED_TO_SUSPEND"
                    logger.warning(f"Failed to signal HTTP endpoint {task.endpoint} for task '{task.task_id}'.")

            if signaling_failed:
                continue

            # 3. Custom callback hook
            if self.on_suspend_hook:
                try:
                    self.on_suspend_hook(task)
                except Exception as e:
                    logger.warning(f"on_suspend_hook failed for {task.task_id}: {e}")

            task.status = "SUSPENDED"
            task.suspended_at = time.time()
            suspended_ids.append(task.task_id)
            logger.warning(
                f"[BACKPRESSURE] Suspended task '{task.name}' (ID: {task.task_id}, Priority: {task.priority.name})"
            )

        return suspended_ids

    async def release_backpressure(self) -> List[str]:
        """
        Resumes all suspended tasks in reverse priority order (MEDIUM first, then LOW).
        Returns list of task IDs that were resumed.
        """
        resumed_ids: List[str] = []

        suspended_tasks = [t for t in self._tasks.values() if t.status == "SUSPENDED"]
        # Resume higher priority first (MEDIUM=2 before LOW=1)
        suspended_tasks.sort(key=lambda t: t.priority.value, reverse=True)

        for task in suspended_tasks:
            resume_failed = False

            # 1. Local process resumption via SIGCONT
            if task.pid is not None:
                if not self._signal_pid(task.pid, signal.SIGCONT):
                    resume_failed = True
                    task.status = "FAILED_TO_RESUME"
                    logger.warning(f"Failed to resume PID {task.pid} for task '{task.task_id}'.")

            # 2. Remote HTTP resume hook
            if task.endpoint is not None and not resume_failed:
                if not await self._signal_http_endpoint(task.endpoint, "resume"):
                    resume_failed = True
                    task.status = "FAILED_TO_RESUME"
                    logger.warning(f"Failed to resume HTTP endpoint {task.endpoint} for task '{task.task_id}'.")

            if resume_failed:
                continue

            # 3. Custom callback hook
            if self.on_resume_hook:
                try:
                    self.on_resume_hook(task)
                except Exception as e:
                    logger.warning(f"on_resume_hook failed for {task.task_id}: {e}")

            task.status = "RUNNING"
            task.resumed_at = time.time()
            resumed_ids.append(task.task_id)
            logger.info(
                f"[BACKPRESSURE] Resumed task '{task.name}' (ID: {task.task_id}, Priority: {task.priority.name})"
            )

        return resumed_ids


# ---------------------------------------------------------------------------
# High-Level Mesh RAM Governor Coordinator
# ---------------------------------------------------------------------------
class MeshRAMGovernorCoordinator:
    """
    Coordinates asynchronous telemetry collection, global pool aggregation,
    threshold evaluation, and backpressure suspension.
    """

    def __init__(
        self,
        collector: Optional[MeshTelemetryCollector] = None,
        suspension_mgr: Optional[BackpressureSuspensionManager] = None,
    ):
        self.collector = collector or MeshTelemetryCollector()
        self.suspension_mgr = suspension_mgr or BackpressureSuspensionManager()
        self.last_pool_metric: Optional[GlobalRAMPoolMetric] = None
        self.last_telemetry: List[NodeMemoryTelemetry] = []
        self._l1_backpressure_active: bool = False

    async def evaluate_mesh(
        self,
        simulated_telemetry: Optional[List[NodeMemoryTelemetry]] = None,
    ) -> Tuple[GlobalRAMPoolMetric, List[NodeMemoryTelemetry], Dict[str, Any]]:
        """
        Executes a single governance cycle:
        1. Collects telemetry (or uses simulated telemetry).
        2. Computes Global RAM Pool metric.
        3. Evaluates per-node thresholds.
        4. Applies or releases backpressure.
        Returns (pool_metric, telemetry_list, action_summary).
        """
        if simulated_telemetry is not None:
            telemetry = simulated_telemetry
        else:
            telemetry = await self.collector.collect_all()

        pool_metric = compute_global_pool_metric(
            telemetry,
            l1_backpressure_active=self._l1_backpressure_active,
        )
        self.last_pool_metric = pool_metric
        self.last_telemetry = telemetry
        self._l1_backpressure_active = "L1_Mac_Host" in pool_metric.saturated_nodes

        actions: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "backpressure_triggered": pool_metric.backpressure_triggered,
            "saturated_nodes": pool_metric.saturated_nodes,
            "tasks_suspended": [],
            "tasks_resumed": [],
        }

        if pool_metric.backpressure_triggered:
            suspended = await self.suspension_mgr.apply_backpressure(pool_metric)
            actions["tasks_suspended"] = suspended
        else:
            # If healthy, resume any previously suspended tasks
            resumed = await self.suspension_mgr.release_backpressure()
            actions["tasks_resumed"] = resumed

        return pool_metric, telemetry, actions
