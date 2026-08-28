"""
multi_wan/service_keepalive.py - 24/7 AI Service Keep-Alive & Full Network Mesh Health Tracker.

Monitors and maintains 24/7 operational readiness across all local AI services & network nodes:
- Ollama Server (Port 11434)
- LM Studio / lmlink Server (Port 1234 / 8900)
- Lauburu Gemini AI Service (Port 8087)
- Local AGI Bridge Daemon (scripts/lauburu_bridge_daemon.py)
- Full Network Mesh Nodes (macOS macbook-1, Linux linux-1, Pixel 10 Pro XL, Samsung S20, Tablet)
- Mesh Port Health Matrix (Ports 8888, 5050, 8087, 11434, 1234, 445, 8022, 22)

STRICT RULE: FULL NETWORK HEALTH IS "HEALTHY" ONLY IF ALL DEVICES AND ALL REQUIRED PORTS
ARE CONNECTED AND ACTIVE. OTHERWISE STATUS IS DEGRADED / UNHEALTHY.
"""

import asyncio
import logging
import os
import socket
import subprocess
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

logger = logging.getLogger("multi_wan.service_keepalive")

class ManagedService:
    """Represents a 24/7 managed background service or daemon."""

    def __init__(
        self,
        key: str,
        name: str,
        port: Optional[int] = None,
        health_url: Optional[str] = None,
        start_cmd: Optional[List[str]] = None,
        auto_restart: bool = True
    ):
        self.key = key
        self.name = name
        self.port = port
        self.health_url = health_url
        self.start_cmd = start_cmd
        self.auto_restart = auto_restart
        self.status = "OFFLINE"  # ONLINE, DEGRADED, OFFLINE
        self.last_check_time = 0.0
        self.restart_count = 0
        self.last_restart_time = 0.0
        self.process: Optional[subprocess.Popen] = None

    def check_health(self) -> str:
        """
        Executes real socket/HTTP probe to test service health.
        """
        self.last_check_time = time.time()

        # 1. HTTP Probe
        if self.health_url:
            try:
                req = urllib.request.Request(
                    self.health_url,
                    headers={"User-Agent": "Lauburu-ServiceKeepAlive/1.0"}
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status in (200, 204, 301, 302):
                        self.status = "ONLINE"
                        return "ONLINE"
            except Exception as e:
                logger.debug(f"HTTP health probe failed for {self.name} ({self.health_url}): {e}")

        # 2. Port Probe
        if self.port:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                res = sock.connect_ex(("127.0.0.1", self.port))
                sock.close()
                if res == 0:
                    self.status = "ONLINE"
                    return "ONLINE"
            except Exception as e:
                logger.debug(f"Port probe failed for {self.name} on port {self.port}: {e}")

        self.status = "OFFLINE"
        return "OFFLINE"

    def restart_if_needed(self, monorepo_dir: str) -> bool:
        """
        Restarts the service if offline and auto_restart is enabled.
        Rate-limited to prevent rapid restart loops (minimum 10s cooldown).
        """
        if self.status == "ONLINE" or not self.auto_restart or not self.start_cmd:
            return False

        now = time.time()
        if now - self.last_restart_time < 10.0:
            logger.warning(f"Cooldown active for {self.name}. Skipping restart for {int(10 - (now - self.last_restart_time))}s.")
            return False

        logger.info(f"⚡ [24/7 Keep-Alive] Service '{self.name}' is OFFLINE. Attempting automatic start...")
        self.last_restart_time = now
        self.restart_count += 1

        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            formatted_cmd = [part.replace("{MONOREPO}", monorepo_dir) for part in self.start_cmd]

            self.process = subprocess.Popen(
                formatted_cmd,
                cwd=monorepo_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"✓ Launched process for '{self.name}' (PID: {self.process.pid}).")
            return True
        except Exception as e:
            logger.error(f"Failed to auto-restart service '{self.name}': {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "port": self.port,
            "health_url": self.health_url,
            "status": self.status,
            "auto_restart": self.auto_restart,
            "restart_count": self.restart_count,
            "last_check_time": self.last_check_time,
            "last_restart_time": self.last_restart_time
        }


class MeshNodeDefinition:
    """Represents a specific target device node in the full network mesh."""

    def __init__(self, key: str, name: str, primary_ip: str, required_ports: List[int], platform: str):
        self.key = key
        self.name = name
        self.primary_ip = primary_ip
        self.required_ports = required_ports
        self.platform = platform
        self.connected = False
        self.latency_ms = 0.0
        self.open_ports: List[int] = []
        self.missing_ports: List[int] = []

    def probe_node_health(self) -> bool:
        """
        Empirically probes TCP socket connectivity and port openness on the node.
        """
        start = time.time()
        self.open_ports = []
        self.missing_ports = []

        # Probe host reachability on primary IP
        host_reachable = False
        if self.primary_ip in ("127.0.0.1", "localhost"):
            host_reachable = True
            self.latency_ms = 0.5
        else:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.2)
                # Try probing SSH (22/8022) or SMB (445) or arbitrary socket
                probe_port = self.required_ports[0] if self.required_ports else 22
                res = sock.connect_ex((self.primary_ip, probe_port))
                sock.close()
                elapsed = (time.time() - start) * 1000.0
                if res == 0:
                    host_reachable = True
                    self.latency_ms = elapsed
            except Exception:
                host_reachable = False

        # Probe each required port
        for port in self.required_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                res = sock.connect_ex((self.primary_ip, port))
                sock.close()
                if res == 0:
                    self.open_ports.append(port)
                    host_reachable = True
                else:
                    self.missing_ports.append(port)
            except Exception:
                self.missing_ports.append(port)

        self.connected = host_reachable and (len(self.missing_ports) == 0)
        return self.connected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "primary_ip": self.primary_ip,
            "platform": self.platform,
            "connected": self.connected,
            "latency_ms": round(self.latency_ms, 2),
            "required_ports": self.required_ports,
            "open_ports": self.open_ports,
            "missing_ports": self.missing_ports,
            "status": "HEALTHY" if self.connected else ("DEGRADED" if self.open_ports else "OFFLINE")
        }


class ServiceKeepAliveManager:
    """
    Manager coordinating 24/7 service monitoring, full network mesh health tracking,
    and automatic daemon recovery.
    """

    def __init__(self, monorepo_dir: str = "/Volumes/Lauburu-Monorepo", check_interval: float = 10.0):
        self.monorepo_dir = monorepo_dir
        self.check_interval = check_interval
        self.services: Dict[str, ManagedService] = {}
        self.mesh_nodes: Dict[str, MeshNodeDefinition] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False

        try:
            from .dynamic_port_scanner import DynamicPortScanner
            from .wifi_optimizer import WifiOptimizer
        except (ImportError, ValueError):
            try:
                from dynamic_port_scanner import DynamicPortScanner
                from wifi_optimizer import WifiOptimizer
            except ImportError:
                DynamicPortScanner = None
                WifiOptimizer = None

        self.port_scanner = DynamicPortScanner() if DynamicPortScanner else None
        self.wifi_optimizer = WifiOptimizer(rssi_threshold=-75) if WifiOptimizer else None
        self.wifi_status = {}
        self._initialize_services()
        self._initialize_mesh_nodes()

    def _initialize_services(self):
        """Initializes 24/7 local services to manage and monitor."""
        service_list = [
            ManagedService(
                key="ollama",
                name="Ollama LLM Server",
                port=11434,
                health_url="http://localhost:11434/api/tags",
                start_cmd=["ollama", "serve"]
            ),
            ManagedService(
                key="lmlink",
                name="LM Studio / lmlink Server",
                port=1234,
                health_url="http://localhost:1234/v1/models",
                start_cmd=["lms", "server", "start"]
            ),
            ManagedService(
                key="gemini_service",
                name="Lauburu Gemini AI Service",
                port=8087,
                health_url="http://localhost:8087/health",
                start_cmd=["python3", "{MONOREPO}/apps/gemini_service.py"]
            ),
            ManagedService(
                key="agi_bridge",
                name="Lauburu Local AGI Bridge Daemon",
                health_url=None,
                start_cmd=["python3", "{MONOREPO}/scripts/lauburu_bridge_daemon.py"]
            ),
            ManagedService(
                key="multi_wan_proxy",
                name="Multi-WAN Multiplexing Proxy",
                port=8888,
                health_url="http://localhost:8888/health",
                start_cmd=None
            ),
            ManagedService(
                key="llamacpp_rpc",
                name="llama.cpp RPC Distributed Tensor Server",
                port=50052,
                health_url=None,
                start_cmd=["python3", "{MONOREPO}/02_ai_models_and_inference/rpc_server.py", "--port", "50052"],
                auto_restart=True
            ),
        ]
        for s in service_list:
            self.services[s.key] = s

    def _initialize_mesh_nodes(self):
        """Initializes full network mesh target node definitions."""
        nodes = [
            MeshNodeDefinition("macbook_host", "macOS Host (macbook-1)", "127.0.0.1", [8888, 5050, 8087, 11434, 1234, 50052], "macOS"),
            MeshNodeDefinition("linux_server", "Linux Samba NAS Server (linux-1)", "100.101.39.98", [445, 22, 50052], "Linux"),
            MeshNodeDefinition("linux_tplink_eth", "Linux TP-Link Extender Node", "192.168.8.224", [22, 50052], "Linux"),
            MeshNodeDefinition("pixel_phone", "Google Pixel 10 Pro XL", "100.73.38.87", [8022, 50052], "Android"),
            MeshNodeDefinition("samsung_s20", "Samsung S20", "100.99.123.58", [22], "Android"),
            MeshNodeDefinition("samsung_tablet", "Samsung Tablet", "100.118.79.63", [22], "Windows/Android"),
        ]
        for n in nodes:
            self.mesh_nodes[n.key] = n

    def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Probes all local services and returns status dictionary."""
        results = {}
        for key, s in self.services.items():
            s.check_health()
            results[key] = s.to_dict()
        return results

    def probe_full_network_mesh(self) -> Dict[str, Any]:
        """
        Probes all mesh nodes & required ports.
        STRICT RULE: Full network status is 'HEALTHY' ONLY if 100% of nodes and ports are connected.
        """
        all_nodes_connected = True
        missing_nodes = []
        missing_ports_all = []
        node_matrix = {}

        for key, node in self.mesh_nodes.items():
            is_healthy = node.probe_node_health()
            node_dict = node.to_dict()
            node_matrix[key] = node_dict

            if not node.connected:
                all_nodes_connected = False
                missing_nodes.append(node.name)

            if node.missing_ports:
                for p in node.missing_ports:
                    missing_ports_all.append(f"{node.name}:{p}")

        overall_status = "HEALTHY" if (all_nodes_connected and not missing_ports_all) else "DEGRADED"

        return {
            "overall_mesh_status": overall_status,
            "all_nodes_connected": all_nodes_connected,
            "total_nodes": len(self.mesh_nodes),
            "connected_nodes_count": sum(1 for n in self.mesh_nodes.values() if n.connected),
            "missing_nodes": missing_nodes,
            "missing_ports": missing_ports_all,
            "node_matrix": node_matrix,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def maintain_services(self) -> Dict[str, Dict[str, Any]]:
        """Probes last confirmed port first (Fast Path). If offline, triggers fallback scan and auto-restarts."""
        if hasattr(self, "port_scanner") and self.port_scanner:
            for s_key, srv in self.services.items():
                if srv.port is not None:
                    # Fast Path Probe on last confirmed port; fallback scan if unreachable
                    discovered = self.port_scanner.get_service_fast_path_or_scan(
                        service_type=s_key,
                        default_ip="127.0.0.1",
                        default_port=srv.port
                    )
                    if discovered and discovered.port != srv.port:
                        logger.info(f"🔄 [Port Dynamic Shift] Updated '{srv.name}': {srv.port} -> {discovered.port}")
                        srv.port = discovered.port
                        srv.health_url = discovered.endpoint_url

        # 2. Check health and restart if offline
        results = {}
        for key, s in self.services.items():
            status = s.check_health()
            if status == "OFFLINE":
                s.restart_if_needed(self.monorepo_dir)
            results[key] = s.to_dict()
        return results

    async def start_monitoring_loop(self):
        """Asynchronous background loop maintaining 24/7 service uptime & full mesh tracking."""
        self._is_running = True
        logger.info(f"Starting 24/7 Service Keep-Alive & Full Network Mesh Health Loop (Interval: {self.check_interval}s)...")
        
        while self._is_running:
            try:
                # Optimize Wi-Fi before checking mesh
                if hasattr(self, "wifi_optimizer"):
                    self.wifi_status = self.wifi_optimizer.optimize_wifi()
                    
                self.maintain_services()
                self.probe_full_network_mesh()
            except Exception as e:
                logger.error(f"Error in keep-alive/mesh monitoring loop: {e}")
            await asyncio.sleep(self.check_interval)

    def stop_monitoring(self):
        """Stops background keep-alive monitoring."""
        self._is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("24/7 Service Keep-Alive monitoring stopped.")

    def get_status_summary(self) -> Dict[str, Any]:
        """Exposes status summary for dashboard and telemetry API."""
        services_dict = {key: s.to_dict() for key, s in self.services.items()}
        online_count = sum(1 for s in self.services.values() if s.status == "ONLINE")
        total_count = len(self.services)
        
        mesh_health = self.probe_full_network_mesh()
        auto_scan_data = self.port_scanner.get_summary() if hasattr(self, "port_scanner") and self.port_scanner else None

        return {
            "24_7_system_status": "OPTIMAL" if (online_count == total_count and mesh_health["overall_mesh_status"] == "HEALTHY") else "DEGRADED",
            "online_services": online_count,
            "total_services": total_count,
            "full_network_mesh": mesh_health,
            "auto_port_scanner": auto_scan_data,
            "wifi_status": getattr(self, "wifi_status", {}),
            "services": services_dict
        }
