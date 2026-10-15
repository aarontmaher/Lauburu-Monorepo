"""
00_core_infrastructure/lens_bootstrapper/supervisor/local_lens_supervisor.py
============================================================================
Local Autonomous Healing Supervisor Entrypoint (Milestone 2).

Main Python supervisor spawned by the C++ Bootstrapper daemon (`lens_bootstrapper_daemon`).
Binds an HTTP server on port 3037 with endpoints:
- `GET /health`     -> Liveness probe & core status
- `GET /telemetry`  -> Darwin Mach memory, interfaces & core ports telemetry
- `GET /status`     -> Supervisor state & circuit breaker statuses
- `POST /heal`      -> Autonomous multi-transport healing sweep

Integrates:
- F7: MLX TinyLM Local Engine & Host Memory Sanctuary Guard (Rule 3)
- F8: Android Edge TinyLM Adapter (Rule 9)
- F9: Multi-Transport Autonomous Network Healer
- F10: Local Leaky-Bucket Circuit Breaker
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional

# Ensure package directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from .circuit_breaker import CircuitBreaker
    from .mlx_engine import MLXTinyLMEngine, MemorySanctuaryGuard
    from .android_adapter import AndroidEdgeTinyLMAdapter, AndroidEnvironment
    from .network_healer import NetworkHealer
except ImportError:
    from circuit_breaker import CircuitBreaker
    from mlx_engine import MLXTinyLMEngine, MemorySanctuaryGuard
    from android_adapter import AndroidEdgeTinyLMAdapter, AndroidEnvironment
    from network_healer import NetworkHealer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LensSupervisor] %(message)s",
)
logger = logging.getLogger("LensSupervisor")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server allowing concurrent telemetry and health probes."""
    daemon_threads = True
    allow_reuse_address = True


class LocalLensSupervisor:
    """
    Core supervisor managing local AI engines, network diagnosis,
    and HTTP telemetry endpoints on port 3037.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3037,
        circuit_breaker: Optional[CircuitBreaker] = None,
        memory_guard: Optional[MemorySanctuaryGuard] = None,
        mlx_engine: Optional[MLXTinyLMEngine] = None,
        network_healer: Optional[NetworkHealer] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.start_time = time.time()
        self.pid = os.getpid()

        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            max_restarts=3, window_seconds=300.0, cooldown_seconds=300.0
        )
        self.memory_guard = memory_guard or MemorySanctuaryGuard()
        self.mlx_engine = mlx_engine or MLXTinyLMEngine(memory_guard=self.memory_guard)
        self.android_env = AndroidEnvironment()
        self.android_adapter = AndroidEdgeTinyLMAdapter(env=self.android_env)
        self.network_healer = network_healer or NetworkHealer(circuit_breaker=self.circuit_breaker)

        self._server: Optional[ThreadedHTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def uptime_sec(self) -> float:
        return round(time.time() - self.start_time, 2)

    def get_health_payload(self) -> Dict[str, Any]:
        """Constructs the /health endpoint JSON payload."""
        mem_stats = self.memory_guard.get_host_memory_stats()
        return {
            "status": "ok",
            "supervisor": "local_lens_supervisor",
            "service_name": "Sovereign Lens Bootstrapper Supervisor",
            "version": "1.0.0",
            "pid": self.pid,
            "uptime_seconds": self.uptime_sec,
            "timestamp": time.time(),
            "port": self.port,
            "mlx_available": self.mlx_engine.is_available(),
            "mlx_version": self.mlx_engine.mlx_version,
            "sanctuary_ok": mem_stats.get("sanctuary_ok", True),
            "free_headroom_gb": mem_stats.get("headroom_gb", 0.0),
        }

    def get_telemetry_payload(self) -> Dict[str, Any]:
        """Constructs the /telemetry endpoint JSON payload."""
        mem_stats = self.memory_guard.get_host_memory_stats()
        interfaces = self.network_healer.probe_all_interfaces()
        ports = self.network_healer.probe_all_ports()

        return {
            "timestamp": time.time(),
            "uptime_seconds": self.uptime_sec,
            "pid": self.pid,
            "host_memory": mem_stats,
            "interfaces": interfaces,
            "ports": ports,
            "engines": {
                "mlx": {
                    "available": self.mlx_engine.is_available(),
                    "version": self.mlx_engine.mlx_version,
                    "model_id": self.mlx_engine.model_id,
                },
                "android_edge": {
                    "is_android": self.android_env.is_android(),
                    "is_avf": self.android_env.is_avf_microvm(),
                    "runner_type": self.android_adapter.runner_type,
                },
            },
        }

    def get_status_payload(self) -> Dict[str, Any]:
        """Constructs the /status endpoint JSON payload."""
        cb_statuses = self.circuit_breaker.get_all_statuses()
        mem_stats = self.memory_guard.get_host_memory_stats()
        return {
            "status": "RUNNING",
            "supervisor_pid": self.pid,
            "uptime_seconds": self.uptime_sec,
            "circuit_breaker": cb_statuses,
            "sanctuary_ok": mem_stats.get("sanctuary_ok", True),
            "memory_headroom_gb": mem_stats.get("headroom_gb", 0.0),
            "active_port": self.port,
        }

    def trigger_healing(self, dry_run: bool = False) -> Dict[str, Any]:
        """Executes an autonomous network healing sweep."""
        return self.network_healer.sweep_and_heal(dry_run=dry_run)

    def start(self, block: bool = False) -> bool:
        """Starts the HTTP server."""
        handler_cls = self._create_handler()
        try:
            self._server = ThreadedHTTPServer((self.host, self.port), handler_cls)
            self._running = True
            logger.info(f"Local Lens Supervisor listening on http://{self.host}:{self.port}")
        except OSError as e:
            logger.error(f"Failed to bind supervisor HTTP server on port {self.port}: {e}")
            return False

        if block:
            try:
                self._server.serve_forever()
            except (KeyboardInterrupt, SystemExit):
                self.stop()
        else:
            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                name="LensSupervisorServerThread",
                daemon=True,
            )
            self._server_thread.start()

        return True

    def stop(self) -> None:
        """Stops the HTTP server gracefully."""
        self._running = False
        if self._server:
            logger.info("Shutting down Local Lens Supervisor HTTP server...")
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def _create_handler(self):
        """Creates an HTTP request handler bound to this supervisor instance."""
        supervisor = self

        class SupervisorRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                # Terse logging per token conservation rules
                pass

            def send_json(self, status_code: int, data: Dict[str, Any]) -> None:
                body = json.dumps(data, indent=2).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                path = self.path.split("?")[0].rstrip("/")
                if path in ("", "/health"):
                    self.send_json(200, supervisor.get_health_payload())
                elif path == "/telemetry":
                    self.send_json(200, supervisor.get_telemetry_payload())
                elif path == "/status":
                    self.send_json(200, supervisor.get_status_payload())
                elif path == "/heal":
                    dry_run = "dry_run=true" in self.path.lower()
                    self.send_json(200, supervisor.trigger_healing(dry_run=dry_run))
                else:
                    self.send_json(404, {"error": "NOT_FOUND", "path": self.path})

            def do_POST(self) -> None:
                path = self.path.split("?")[0].rstrip("/")
                if path == "/heal":
                    dry_run = "dry_run=true" in self.path.lower()
                    self.send_json(200, supervisor.trigger_healing(dry_run=dry_run))
                else:
                    self.send_json(404, {"error": "NOT_FOUND", "path": self.path})

        return SupervisorRequestHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Lens Supervisor Daemon")
    parser.add_argument("--port", type=int, default=3037, help="HTTP server port (default: 3037)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="HTTP server bind host")
    parser.add_argument("--daemon", action="store_true", help="Run in background daemon mode")
    args = parser.parse_args()

    supervisor = LocalLensSupervisor(host=args.host, port=args.port)

    def handle_signal(sig, frame):
        logger.info(f"Caught signal {sig}, terminating supervisor...")
        supervisor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    success = supervisor.start(block=True)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
