"""
canonical_sync_engine.verification.mesh_scanner
Multi-transport non-blocking scanner for the 7-layer physical mesh network (L1-L7 + Gateway).
"""
from __future__ import annotations

import concurrent.futures
import datetime
import logging
import os
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from canonical_sync_engine.models.health import (
    MeshSummaryReport,
    NodeProbeMethod,
    NodeStorageHealth,
)

logger = logging.getLogger(__name__)

# Default Mesh Topology Descriptor
DEFAULT_MESH_TOPOLOGY: List[Dict[str, Any]] = [
    {
        "node_id": "L1",
        "name": "Mac_Node",
        "layer": 1,
        "probe_method": NodeProbeMethod.LOCAL,
        "mount_point": "/",
        "endpoint": "127.0.0.1",
    },
    {
        "node_id": "L2",
        "name": "MacBook_Pro",
        "layer": 2,
        "probe_method": NodeProbeMethod.SSH,
        "endpoints": ["169.254.187.138", "100.103.212.21", "192.168.8.127"],
        "user": "aaron",
        "port": 22,
        "key_file": os.path.expanduser("~/.ssh/id_ed25519_monorepo"),
        "mount_point": "/System/Volumes/Data",
    },
    {
        "node_id": "L3",
        "name": "Linux_Head_Node",
        "layer": 3,
        "probe_method": NodeProbeMethod.SSH,
        "endpoints": ["100.101.39.98", "192.168.8.224"],
        "user": "aaron",
        "port": 22,
        "key_file": os.path.expanduser("~/.ssh/id_ed25519_monorepo"),
        "mount_point": "/",
    },
    {
        "node_id": "L4",
        "name": "Linux_Tablet",
        "layer": 4,
        "probe_method": NodeProbeMethod.SSH,
        "endpoints": ["100.81.92.125", "192.168.8.173"],
        "user": "aaron",
        "port": 22,
        "key_file": os.path.expanduser("~/.ssh/id_ed25519_monorepo"),
        "mount_point": "/",
    },
    {
        "node_id": "L5",
        "name": "MacBook_Air",
        "layer": 5,
        "probe_method": NodeProbeMethod.SSH,
        "endpoints": ["100.93.158.96", "192.168.8.222"],
        "user": "aaron",
        "port": 22,
        "key_file": os.path.expanduser("~/.ssh/id_ed25519"),
        "mount_point": "/System/Volumes/Data",
    },
    {
        "node_id": "L6",
        "name": "Pixel_10_Pro_XL",
        "layer": 6,
        "probe_method": NodeProbeMethod.SSH,
        "endpoints": ["100.73.38.87", "192.168.8.160"],
        "user": "u0_a363",
        "port": 8022,
        "key_file": os.path.expanduser("~/.ssh/id_ed25519_monorepo"),
        "mount_point": "/data",
    },
    {
        "node_id": "L7",
        "name": "Samsung_S20",
        "layer": 7,
        "probe_method": NodeProbeMethod.ADB,
        "adb_targets": ["100.84.40.95:5555", "100.99.123.58:5555", "R3CN40CJJ1R"],
        "mount_point": "/storage/emulated",
    },
    {
        "node_id": "GW",
        "name": "GL.iNet Router",
        "layer": 0,
        "probe_method": NodeProbeMethod.SOCKET,
        "endpoints": ["192.168.8.1", "100.122.185.123"],
        "port": 80,
        "mount_point": "embedded",
    },
]


class MeshNodeScanner:
    """
    Scans storage health, capacity, and reachability across the physical mesh.
    """

    def __init__(
        self,
        topology: Optional[List[Dict[str, Any]]] = None,
        timeout_sec: float = 2.0,
        min_headroom_gb: float = 10.0,
    ):
        self.topology = topology or DEFAULT_MESH_TOPOLOGY
        self.timeout_sec = timeout_sec
        self.min_headroom_gb = min_headroom_gb

    def scan_all_nodes(self, parallel: bool = True, max_workers: int = 8) -> Dict[str, NodeStorageHealth]:
        """
        Scans all registered mesh nodes and returns a mapping of node_id -> NodeStorageHealth.
        """
        results: Dict[str, NodeStorageHealth] = {}

        if parallel and len(self.topology) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_node = {
                    executor.submit(self.scan_node_by_spec, node_spec): node_spec["node_id"]
                    for node_spec in self.topology
                }
                for future in concurrent.futures.as_completed(future_to_node):
                    node_id = future_to_node[future]
                    try:
                        report = future.result()
                        results[report.node_id] = report
                    except Exception as e:
                        logger.error(f"Unexpected error scanning node {node_id}: {e}")
                        results[node_id] = self._create_error_report(node_id, str(e))
        else:
            for node_spec in self.topology:
                report = self.scan_node_by_spec(node_spec)
                results[report.node_id] = report

        return results

    def get_mesh_summary(self, parallel: bool = True) -> MeshSummaryReport:
        """
        Executes a full mesh scan and compiles an aggregated MeshSummaryReport.
        """
        t0 = time.time()
        node_reports = self.scan_all_nodes(parallel=parallel)
        duration_ms = (time.time() - t0) * 1000.0

        online_count = sum(1 for n in node_reports.values() if n.is_reachable)
        offline_count = len(node_reports) - online_count
        total_free = sum(n.disk_free_gb for n in node_reports.values() if n.is_reachable)
        total_cap = sum(n.disk_total_gb for n in node_reports.values() if n.is_reachable)

        return MeshSummaryReport(
            total_nodes=len(node_reports),
            online_nodes=online_count,
            offline_nodes=offline_count,
            total_mesh_free_gb=round(total_free, 2),
            total_mesh_capacity_gb=round(total_cap, 2),
            scan_duration_ms=round(duration_ms, 2),
            nodes=node_reports,
        )

    def scan_node_by_spec(self, node_spec: Dict[str, Any]) -> NodeStorageHealth:
        """
        Routes node probe based on configured probe_method.
        """
        method = node_spec.get("probe_method", NodeProbeMethod.LOCAL)
        if isinstance(method, str):
            method = NodeProbeMethod.from_string(method)

        if method == NodeProbeMethod.LOCAL:
            return self._probe_local(node_spec)
        elif method == NodeProbeMethod.SSH:
            return self._probe_ssh(node_spec)
        elif method == NodeProbeMethod.ADB:
            return self._probe_adb(node_spec)
        elif method == NodeProbeMethod.SOCKET:
            return self._probe_socket(node_spec)
        else:
            return self._create_error_report(node_spec.get("node_id", "unknown"), f"Unsupported probe method: {method}")

    def _probe_local(self, spec: Dict[str, Any]) -> NodeStorageHealth:
        node_id = spec["node_id"]
        name = spec.get("name", node_id)
        layer = spec.get("layer", 1)
        mount = spec.get("mount_point", "/")
        t0 = time.time()

        try:
            target_mount = mount if os.path.exists(mount) else "/"
            usage = shutil.disk_usage(target_mount)
            total_gb = round(usage.total / (1024.0 ** 3), 2)
            free_gb = round(usage.free / (1024.0 ** 3), 2)
            used_gb = round(usage.used / (1024.0 ** 3), 2)
            pct_free = round((free_gb / total_gb * 100.0) if total_gb > 0 else 0.0, 2)
            latency = round((time.time() - t0) * 1000.0, 2)
            healthy = free_gb >= self.min_headroom_gb

            return NodeStorageHealth(
                node_id=node_id,
                node_name=name,
                layer=layer,
                is_reachable=True,
                disk_total_gb=total_gb,
                disk_used_gb=used_gb,
                disk_free_gb=free_gb,
                disk_free_percent=pct_free,
                inode_state="OK",
                latency_ms=latency,
                headroom_ok=healthy,
                probe_method=NodeProbeMethod.LOCAL,
                endpoint="127.0.0.1",
                mount_point=mount,
            )
        except Exception as e:
            return NodeStorageHealth(
                node_id=node_id,
                node_name=name,
                layer=layer,
                is_reachable=False,
                disk_total_gb=0.0,
                disk_used_gb=0.0,
                disk_free_gb=0.0,
                disk_free_percent=0.0,
                inode_state="UNKNOWN",
                latency_ms=round((time.time() - t0) * 1000.0, 2),
                headroom_ok=False,
                probe_method=NodeProbeMethod.LOCAL,
                endpoint="127.0.0.1",
                mount_point=mount,
                error_message=str(e),
            )

    def _probe_ssh(self, spec: Dict[str, Any]) -> NodeStorageHealth:
        node_id = spec["node_id"]
        name = spec.get("name", node_id)
        layer = spec.get("layer", 0)
        endpoints = spec.get("endpoints", [spec.get("endpoint", "127.0.0.1")])
        user = spec.get("user", "aaron")
        port = spec.get("port", 22)
        key_file = spec.get("key_file", os.path.expanduser("~/.ssh/id_ed25519_monorepo"))
        mount = spec.get("mount_point", "/")

        last_error = None
        t0 = time.time()

        for host in endpoints:
            cmd = [
                "ssh",
                "-n",
                "-o", "StrictHostKeyChecking=no",
                "-o", f"ConnectTimeout={max(1, int(self.timeout_sec))}",
                "-o", "BatchMode=yes",
                "-p", str(port),
            ]
            if key_file and os.path.exists(key_file):
                cmd.extend(["-i", key_file])
            cmd.extend([f"{user}@{host}", f"df -k {mount}"])

            try:
                cp = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_sec + 0.5)
                latency = round((time.time() - t0) * 1000.0, 2)
                if cp.returncode == 0:
                    total_gb, free_gb = self._parse_df_output(cp.stdout)
                    used_gb = round(total_gb - free_gb if total_gb >= free_gb else 0.0, 2)
                    pct_free = round((free_gb / total_gb * 100.0) if total_gb > 0 else 0.0, 2)
                    healthy = free_gb >= self.min_headroom_gb
                    return NodeStorageHealth(
                        node_id=node_id,
                        node_name=name,
                        layer=layer,
                        is_reachable=True,
                        disk_total_gb=total_gb,
                        disk_used_gb=used_gb,
                        disk_free_gb=free_gb,
                        disk_free_percent=pct_free,
                        inode_state="OK",
                        latency_ms=latency,
                        headroom_ok=healthy,
                        probe_method=NodeProbeMethod.SSH,
                        endpoint=f"{host}:{port}",
                        mount_point=mount,
                    )
                else:
                    last_error = f"SSH exit {cp.returncode}: {cp.stderr.strip()}"
            except subprocess.TimeoutExpired:
                last_error = f"SSH connection timed out after {self.timeout_sec}s"
            except Exception as e:
                last_error = str(e)

        latency = round((time.time() - t0) * 1000.0, 2)
        return NodeStorageHealth(
            node_id=node_id,
            node_name=name,
            layer=layer,
            is_reachable=False,
            disk_total_gb=0.0,
            disk_used_gb=0.0,
            disk_free_gb=0.0,
            disk_free_percent=0.0,
            inode_state="UNKNOWN",
            latency_ms=latency,
            headroom_ok=False,
            probe_method=NodeProbeMethod.SSH,
            endpoint=str(endpoints[0] if endpoints else "unknown"),
            mount_point=mount,
            error_message=last_error or "All endpoints unreachable",
        )

    def _probe_adb(self, spec: Dict[str, Any]) -> NodeStorageHealth:
        node_id = spec["node_id"]
        name = spec.get("name", node_id)
        layer = spec.get("layer", 7)
        targets = spec.get("adb_targets", ["100.84.40.95:5555"])
        mount = spec.get("mount_point", "/storage/emulated")

        last_error = None
        t0 = time.time()

        for target in targets:
            cmd = ["adb", "-s", target, "shell", f"df -k {mount}"]
            try:
                cp = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_sec + 0.5)
                latency = round((time.time() - t0) * 1000.0, 2)
                if cp.returncode == 0:
                    total_gb, free_gb = self._parse_df_output(cp.stdout)
                    used_gb = round(total_gb - free_gb if total_gb >= free_gb else 0.0, 2)
                    pct_free = round((free_gb / total_gb * 100.0) if total_gb > 0 else 0.0, 2)
                    healthy = free_gb >= self.min_headroom_gb
                    return NodeStorageHealth(
                        node_id=node_id,
                        node_name=name,
                        layer=layer,
                        is_reachable=True,
                        disk_total_gb=total_gb,
                        disk_used_gb=used_gb,
                        disk_free_gb=free_gb,
                        disk_free_percent=pct_free,
                        inode_state="OK",
                        latency_ms=latency,
                        headroom_ok=healthy,
                        probe_method=NodeProbeMethod.ADB,
                        endpoint=target,
                        mount_point=mount,
                    )
                else:
                    last_error = f"ADB error: {cp.stderr.strip() or cp.stdout.strip()}"
            except subprocess.TimeoutExpired:
                last_error = f"ADB command timed out after {self.timeout_sec}s"
            except FileNotFoundError:
                last_error = "adb executable not found on PATH"
                break
            except Exception as e:
                last_error = str(e)

        latency = round((time.time() - t0) * 1000.0, 2)
        return NodeStorageHealth(
            node_id=node_id,
            node_name=name,
            layer=layer,
            is_reachable=False,
            disk_total_gb=0.0,
            disk_used_gb=0.0,
            disk_free_gb=0.0,
            disk_free_percent=0.0,
            inode_state="UNKNOWN",
            latency_ms=latency,
            headroom_ok=False,
            probe_method=NodeProbeMethod.ADB,
            endpoint=str(targets[0] if targets else "unknown"),
            mount_point=mount,
            error_message=last_error or "ADB device not found",
        )

    def _probe_socket(self, spec: Dict[str, Any]) -> NodeStorageHealth:
        node_id = spec["node_id"]
        name = spec.get("name", node_id)
        layer = spec.get("layer", 0)
        endpoints = spec.get("endpoints", ["192.168.8.1"])
        port = spec.get("port", 80)
        t0 = time.time()

        for host in endpoints:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(min(self.timeout_sec, 1.0))
                s.connect((host, port))
                s.close()
                latency = round((time.time() - t0) * 1000.0, 2)
                return NodeStorageHealth(
                    node_id=node_id,
                    node_name=name,
                    layer=layer,
                    is_reachable=True,
                    disk_total_gb=1.0,
                    disk_used_gb=0.5,
                    disk_free_gb=0.5,
                    disk_free_percent=50.0,
                    inode_state="OK",
                    latency_ms=latency,
                    headroom_ok=True,
                    probe_method=NodeProbeMethod.SOCKET,
                    endpoint=f"{host}:{port}",
                    mount_point="embedded",
                )
            except Exception:
                pass

        latency = round((time.time() - t0) * 1000.0, 2)
        return NodeStorageHealth(
            node_id=node_id,
            node_name=name,
            layer=layer,
            is_reachable=False,
            disk_total_gb=0.0,
            disk_used_gb=0.0,
            disk_free_gb=0.0,
            disk_free_percent=0.0,
            inode_state="UNKNOWN",
            latency_ms=latency,
            headroom_ok=False,
            probe_method=NodeProbeMethod.SOCKET,
            endpoint=str(endpoints[0]),
            mount_point="embedded",
            error_message="Socket connection refused or timed out",
        )

    @staticmethod
    def _parse_df_output(output: str) -> Tuple[float, float]:
        """
        Robust multi-platform parser for POSIX/Linux/Android `df -k` output.
        Handles wrapped filesystem identifiers and variable column formatting.
        Returns: (total_gb, free_gb)
        """
        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
        if not lines or len(lines) < 2:
            return 0.0, 0.0

        flat_tokens: List[str] = []
        for line in lines[1:]:  # Skip header
            flat_tokens.extend(line.split())

        for i in range(len(flat_tokens) - 2):
            try:
                total_kb = float(flat_tokens[i])
                avail_kb = float(flat_tokens[i + 2])
                if total_kb > 0 and avail_kb >= 0:
                    total_gb = round(total_kb / (1024.0 * 1024.0), 2)
                    avail_gb = round(avail_kb / (1024.0 * 1024.0), 2)
                    return total_gb, avail_gb
            except (ValueError, IndexError):
                continue

        return 0.0, 0.0

    def _create_error_report(self, node_id: str, error_msg: str) -> NodeStorageHealth:
        return NodeStorageHealth.create_unreachable(
            node_id=node_id,
            node_name=node_id,
            error_message=error_msg,
            latency_ms=0.0,
        )
