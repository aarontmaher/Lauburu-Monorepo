#!/usr/bin/env python3
"""
Mesh RAM Governor CLI & HTTP Telemetry Server
=============================================
Subsystem: 01_apps/bt_ide_ab_test/mesh_ram_governor.py
Lauburu Mesh Ecosystem — 2026

Canonical CLI entry point for Dynamic Global Mesh RAM Governance (Requirement R1).
Polls OS-level telemetry across the 7-layer mesh, computes the Global RAM Pool Metric,
evaluates dynamic safety thresholds (Rule 3 Host Sanctuary, L3 <= 80%, L6 <= 85%),
and enforces Backpressure Suspension to halt background subagents during saturation.

Zero-Mock Invariant: All local telemetry originates from genuine kernel metrics
(Darwin sysctl/Mach vm_stat, Linux /proc/meminfo), and remote telemetry from real async
HTTP probes or registered test endpoints.
"""

import argparse
import asyncio
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from core.config import (
    GATEWAY_PORT,
    HOST_SANCTUARY_MIN_GB,
    MESH_NODES,
    NodeConfig,
    NodeLayer,
    RAM_GOVERNOR_PORT,
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
from core.telemetry import MeshTelemetryCollector, NodeMemoryTelemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MeshRAMGovernorCLI")

# Global singleton governor instance for CLI and HTTP server
_coordinator = MeshRAMGovernorCoordinator()


# ---------------------------------------------------------------------------
# HTTP Handler for Governor Daemon Mode
# ---------------------------------------------------------------------------
class MeshGovernorHTTPHandler(BaseHTTPRequestHandler):
    """
    Lightweight HTTP server exposing live telemetry, global pool metrics,
    and backpressure task management endpoints.
    """

    coordinator: MeshRAMGovernorCoordinator = _coordinator

    def _send_json(self, status_code: int, data: Any):
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                raw = self.rfile.read(length).decode("utf-8")
                return json.loads(raw)
        except Exception:
            pass
        return {}

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/status", "/health"):
            pool = self.coordinator.last_pool_metric
            status_data = {
                "status": "NOMINAL" if (pool and not pool.backpressure_triggered) else "BACKPRESSURE_ACTIVE",
                "backpressure_triggered": pool.backpressure_triggered if pool else False,
                "nodes_reporting": pool.nodes_reporting if pool else 0,
                "nodes_total": pool.nodes_total if pool else len(MESH_NODES),
                "timestamp": datetime.now().isoformat(),
            }
            self._send_json(200, status_data)

        elif path in ("/telemetry", "/nodes"):
            nodes = [t.to_dict() for t in self.coordinator.last_telemetry]
            self._send_json(200, {"nodes": nodes, "count": len(nodes)})

        elif path in ("/pool", "/metrics"):
            if self.coordinator.last_pool_metric:
                self._send_json(200, self.coordinator.last_pool_metric.to_dict())
            else:
                self._send_json(503, {"error": "Telemetry not yet collected"})

        elif path == "/tasks":
            tasks = [t.to_dict() for t in self.coordinator.suspension_mgr.list_tasks()]
            self._send_json(200, {"tasks": tasks, "count": len(tasks)})

        else:
            self._send_json(404, {"error": f"Endpoint '{path}' not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._read_json_body()

        if path == "/govern":
            loop = asyncio.new_event_loop()
            try:
                pool, telemetry, actions = loop.run_until_complete(self.coordinator.evaluate_mesh())
                self._send_json(200, {
                    "pool": pool.to_dict(),
                    "actions": actions,
                    "nodes": [t.to_dict() for t in telemetry],
                })
            finally:
                loop.close()

        elif path == "/tasks/register":
            task_id = body.get("task_id", f"task_{int(time.time()*1000)}")
            name = body.get("name", "Unnamed Subagent")
            p_val = int(body.get("priority", SubagentPriority.LOW.value))
            priority = SubagentPriority(p_val)
            pid = body.get("pid")
            endpoint = body.get("endpoint")
            record = self.coordinator.suspension_mgr.register_task(
                task_id=task_id, name=name, priority=priority, pid=pid, endpoint=endpoint
            )
            self._send_json(201, record.to_dict())

        elif path == "/tasks/suspend":
            loop = asyncio.new_event_loop()
            try:
                pool = self.coordinator.last_pool_metric
                if not pool:
                    pool = GlobalRAMPoolMetric(
                        total_mesh_ram_gb=TOTAL_MESH_RAM_GB,
                        available_mesh_ram_gb=0.0,
                        usable_ai_vram_gb=0.0,
                        pool_utilization_pct=100.0,
                        nodes_reporting=0,
                        nodes_total=len(MESH_NODES),
                        backpressure_triggered=True,
                        saturated_nodes=["MANUAL_SUSPEND_TRIGGER"],
                    )
                else:
                    pool.backpressure_triggered = True
                suspended = loop.run_until_complete(self.coordinator.suspension_mgr.apply_backpressure(pool))
                self._send_json(200, {"status": "BACKPRESSURE_APPLIED", "suspended_tasks": suspended})
            finally:
                loop.close()

        elif path == "/tasks/resume":
            loop = asyncio.new_event_loop()
            try:
                resumed = loop.run_until_complete(self.coordinator.suspension_mgr.release_backpressure())
                self._send_json(200, {"status": "BACKPRESSURE_RELEASED", "resumed_tasks": resumed})
            finally:
                loop.close()

        elif path == "/v1/chat/completions":
            # Direct proxy check for IDE clients hitting 8085
            pool = self.coordinator.last_pool_metric
            if pool and pool.backpressure_triggered:
                # Signal memory backpressure without fake auto-cloud routing
                self._send_json(503, {
                    "error": {
                        "message": "Mesh RAM backpressure active: host sanctuary limits reached. Low-priority tasks suspended.",
                        "type": "backpressure_saturation_error",
                        "code": 503,
                    }
                })
            else:
                self._send_json(200, {
                    "status": "HEALTHY",
                    "message": "Mesh RAM healthy. Ready for local inference.",
                    "available_mesh_ram_gb": pool.available_mesh_ram_gb if pool else 0.0,
                })

        else:
            self._send_json(404, {"error": f"Endpoint '{path}' not found"})


# ---------------------------------------------------------------------------
# CLI Reporting Helpers
# ---------------------------------------------------------------------------
def format_telemetry_table(telemetry: List[NodeMemoryTelemetry], pool: GlobalRAMPoolMetric) -> str:
    lines = []
    lines.append("=" * 88)
    lines.append(" LAUBURU 7-LAYER MESH RAM GOVERNOR — CLUSTER TELEMETRY")
    lines.append("=" * 88)
    lines.append(
        f"{'NODE ID':<18} {'IP':<16} {'TOTAL':<9} {'AVAIL':<9} {'UTIL %':<8} {'THRESH':<9} {'RTT':<7} {'STATUS'}"
    )
    lines.append("-" * 88)

    for t in telemetry:
        status = "🔴 SATURATED" if t.is_saturated else ("🟢 HEALTHY" if t.is_reachable else "⚪ OFFLINE")
        rtt_str = f"{t.rtt_ms:.1f}ms" if t.rtt_ms >= 0 else "--"
        lines.append(
            f"{t.node_id:<18} {t.ip:<16} {t.total_ram_mb/1024.0:>6.1f}GB {t.available_ram_mb/1024.0:>6.1f}GB "
            f"{t.utilization_pct:>6.1f}% {t.dynamic_safety_threshold_mb/1024.0:>6.1f}GB {rtt_str:>7} {status}"
        )

    lines.append("-" * 88)
    pool_status = "🚨 BACKPRESSURE ACTIVE" if pool.backpressure_triggered else "🟢 POOL HEALTHY"
    lines.append(
        f"CLUSTER POOL: Total: {pool.total_mesh_ram_gb:.1f} GB | Avail: {pool.available_mesh_ram_gb:.1f} GB | "
        f"AI VRAM: {pool.usable_ai_vram_gb:.1f} GB | Util: {pool.pool_utilization_pct:.1f}% | "
        f"Reporting: {pool.nodes_reporting}/{pool.nodes_total} | {pool_status}"
    )
    if pool.saturated_nodes:
        lines.append(f"SATURATED NODES: {', '.join(pool.saturated_nodes)}")
    lines.append("=" * 88)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Lauburu Mesh RAM Governor — Dynamic 7-Layer Memory Governance & Backpressure Suspension"
    )
    parser.add_argument("--once", action="store_true", help="Execute single governance cycle and print report")
    parser.add_argument("--poll", action="store_true", help="Continuously poll telemetry at specified interval")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds (default: 5.0)")
    parser.add_argument("--server", action="store_true", help="Start HTTP daemon on specified port")
    parser.add_argument("--port", type=int, default=RAM_GOVERNOR_PORT, help=f"HTTP port (default: {RAM_GOVERNOR_PORT})")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--timeout", type=float, default=0.6, help="Timeout in seconds per IP probe (default: 0.6)")
    parser.add_argument(
        "--simulate-ips",
        type=str,
        default=None,
        help="JSON string or file path containing simulated node memory payloads",
    )
    parser.add_argument(
        "--simulate-pressure",
        action="store_true",
        help="Inject simulated high memory pressure on L1 Mac Host (<4.8GB free) to test backpressure suspension",
    )

    args = parser.parse_args()

    collector = MeshTelemetryCollector(timeout_per_ip=args.timeout)
    suspension_mgr = BackpressureSuspensionManager()
    coordinator = MeshRAMGovernorCoordinator(collector=collector, suspension_mgr=suspension_mgr)

    # Handle simulated IPs if provided
    if args.simulate_ips:
        sim_data = {}
        if os.path.exists(args.simulate_ips):
            with open(args.simulate_ips, "r", encoding="utf-8") as f:
                sim_data = json.load(f)
        else:
            try:
                sim_data = json.loads(args.simulate_ips)
            except Exception as e:
                logger.error(f"Failed to parse --simulate-ips: {e}")
                sys.exit(1)

        for ip_or_node, payload in sim_data.items():
            collector.set_simulated_ip(ip_or_node, payload)

    # Register default background test tasks if simulating pressure
    if args.simulate_pressure:
        suspension_mgr.register_task("bg_lora_1", "24/7 LoRA Harvester", SubagentPriority.LOW)
        suspension_mgr.register_task("bg_ast_crawler", "AST Code Crawler", SubagentPriority.LOW)
        suspension_mgr.register_task("bg_benchmarker", "Continuous Benchmarker", SubagentPriority.MEDIUM)
        suspension_mgr.register_task("debate_council", "AI Debate Council", SubagentPriority.HIGH)
        suspension_mgr.register_task("ide_session", "User Active IDE Session", SubagentPriority.IDE_CRITICAL)

        # Inject simulated saturation on L1
        collector.set_simulated_ip("127.0.0.1", {
            "total_ram_mb": 24576.0,
            "available_ram_mb": 3500.0,  # Below 4.8GB (4915.2 MB) sanctuary
            "free_ram_mb": 500.0,
            "utilization_pct": 85.8,
            "rtt_ms": 0.0,
        })
        # Inject simulated response for L2
        collector.set_simulated_ip("192.168.2.3", {
            "total_ram_mb": 16384.0,
            "available_ram_mb": 7000.0,
            "rtt_ms": 0.54,
        })

    async def execute_cycle():
        pool, telemetry, actions = await coordinator.evaluate_mesh()
        if args.json:
            out = {
                "pool": pool.to_dict(),
                "actions": actions,
                "nodes": [t.to_dict() for t in telemetry],
                "tasks": [t.to_dict() for t in suspension_mgr.list_tasks()],
            }
            print(json.dumps(out, indent=2))
        else:
            print(format_telemetry_table(telemetry, pool))
            if actions.get("tasks_suspended"):
                print(f"🛑 Backpressure Suspended Tasks: {actions['tasks_suspended']}")
            if actions.get("tasks_resumed"):
                print(f"▶️ Backpressure Resumed Tasks: {actions['tasks_resumed']}")
        return pool

    if args.server:
        MeshGovernorHTTPHandler.coordinator = coordinator
        server_address = ("", args.port)
        httpd = HTTPServer(server_address, MeshGovernorHTTPHandler)
        logger.info(f"🛡️ Mesh RAM Governor HTTP Daemon active on port {args.port}")

        # Run one initial evaluation
        asyncio.run(execute_cycle())

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Stopping Mesh RAM Governor HTTP Daemon.")
            httpd.server_close()
        return

    if args.poll:
        logger.info(f"Starting continuous polling (interval: {args.interval}s)...")
        try:
            while True:
                asyncio.run(execute_cycle())
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Polling terminated by user.")
        return

    # Default: run once
    asyncio.run(execute_cycle())


# Backward compatibility aliases
MeshRamGovernor = MeshGovernorHTTPHandler

def run(server_class=HTTPServer, handler_class=MeshGovernorHTTPHandler, port=RAM_GOVERNOR_PORT):
    """Runs the Mesh RAM Governor HTTP daemon."""
    server_address = ("", port)
    handler_class.coordinator = _coordinator
    httpd = server_class(server_address, handler_class)
    logger.info(f"🛡️ Mesh RAM Governor Proxy Active on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    main()

