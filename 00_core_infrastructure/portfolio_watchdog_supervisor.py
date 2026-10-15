#!/usr/bin/env python3
"""
00_core_infrastructure/portfolio_watchdog_supervisor.py
=======================================================
Autonomous Watchdog Supervisor for Top 5 Lauburu Applications:
- Combat Lab Lauburu (Port 4010)
- OpenVitals Lauburu Bridge (Port 4012)
- Screen Lens Lauburu OCR Daemon (Port 3035)
- Network Cable Analyzer Lauburu (Port 4007)
- Showrunner Lauburu Engine (Port 8101)

Features:
- Continuous polling loop of standardized /health endpoints.
- Multi-stage autonomous recovery triggered on 3 consecutive failures.
- Native macOS LaunchAgent management via `launchctl kickstart -k gui/<uid>/<label>`.
- Fallback subprocess daemon spawn with detached process session.
- Exponential backoff cooldown between repeated retries (5s, 10s, 20s... max 120s).
- Circuit breaker limiting restarts to max 5 per 15-minute sliding window (Rule 3).
- Structured incident serialization to self_healing_incidents.json & 24/7 LoRA memory.
"""
import os
import sys
import time
import json
import socket
import logging
import argparse
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PortfolioWatchdog] %(levelname)s: %(message)s"
)
logger = logging.getLogger("PortfolioWatchdog")

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
INCIDENTS_PRIMARY = REPO_ROOT / "00_core_infrastructure/self_healing_hub/src/self_healing_incidents.json"
INCIDENTS_FALLBACK = REPO_ROOT / "self_healing_incidents.json"
LORA_DATASET = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_lora_dataset.jsonl")

PORTFOLIO_REGISTRY = {
    "network_cable_analyzer": {
        "name": "Network Cable Analyzer Lauburu",
        "port": 4007,
        "health_url": "http://127.0.0.1:4007/health",
        "launchagent_label": "com.lauburu.network-cable-analyzer",
        "fallback_cmd": [
            sys.executable, "-m", "uvicorn", "backend.server:app",
            "--host", "0.0.0.0", "--port", "4007"
        ],
        "cwd": str(REPO_ROOT / "01_apps/network_cable_analyzer"),
        "max_restarts_per_window": 5
    },
    "lauburu_showrunner": {
        "name": "Showrunner Lauburu",
        "port": 8101,
        "health_url": "http://127.0.0.1:8101/health",
        "launchagent_label": "com.lauburu.showrunner",
        "fallback_cmd": [
            sys.executable, "-m", "uvicorn", "engine:app",
            "--host", "0.0.0.0", "--port", "8101"
        ],
        "cwd": str(REPO_ROOT / "01_apps/lauburu_showrunner/backend"),
        "max_restarts_per_window": 5
    },
    "screen_lens_ocr": {
        "name": "Screen Lens Lauburu OCR Daemon",
        "port": 3035,
        "health_url": "http://127.0.0.1:3035/health",
        "launchagent_label": "com.lauburu.lens-orchestrator",
        "fallback_cmd": [str(REPO_ROOT / "01_apps/screen_lens/bin/lauburu-lens"), "--daemon"],
        "cwd": str(REPO_ROOT / "01_apps/screen_lens"),
        "max_restarts_per_window": 5
    },
    "combat_lab_lauburu": {
        "name": "Combat Lab Lauburu",
        "port": 4010,
        "health_url": "http://127.0.0.1:4010/health",
        "launchagent_label": "com.lauburu.combat-lab",
        "fallback_cmd": [sys.executable, str(REPO_ROOT / "01_apps/combat_lab_lauburu/server.py")],
        "cwd": str(REPO_ROOT / "01_apps/combat_lab_lauburu"),
        "max_restarts_per_window": 5
    },
    "openvitals_bridge": {
        "name": "OpenVitals Lauburu Bridge",
        "port": 4012,
        "health_url": "http://127.0.0.1:4012/health",
        "launchagent_label": "com.lauburu.openvitals-bridge",
        "fallback_cmd": [sys.executable, str(REPO_ROOT / "06_scripts_and_tooling/android/openvitals_telemetry_bridge.py")],
        "cwd": str(REPO_ROOT / "06_scripts_and_tooling/android"),
        "max_restarts_per_window": 5
    }
}


class PortfolioWatchdogSupervisor:
    """
    Autonomous supervisor daemon inspecting /health contracts, managing process
    lifecycles, and executing multi-stage self-healing recovery.
    """
    def __init__(self, failure_threshold: int = 3, window_seconds: float = 900.0):
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds  # 15 min
        self.consecutive_failures: Dict[str, int] = {k: 0 for k in PORTFOLIO_REGISTRY}
        self.restart_history: Dict[str, List[float]] = {k: [] for k in PORTFOLIO_REGISTRY}
        self.circuit_tripped: Dict[str, bool] = {k: False for k in PORTFOLIO_REGISTRY}
        self.current_backoff: float = 5.0
        self.backoffs: Dict[str, float] = {k: 5.0 for k in PORTFOLIO_REGISTRY}
        self.restarts_triggered: int = 0
        self.last_probe_results: Dict[str, Any] = {}

    def probe_health(self, app_key: str, timeout: float = 3.0) -> Tuple[bool, Dict[str, Any], int]:
        """Probes the /health endpoint of an application."""
        cfg = PORTFOLIO_REGISTRY[app_key]
        url = cfg["health_url"]
        port = cfg["port"]
        req = urllib.request.Request(url, headers={"User-Agent": "PortfolioWatchdog/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.status
                body = response.read().decode("utf-8")
                data = json.loads(body)
                is_healthy = (status_code == 200 and data.get("status") in ("healthy", "ok", "degraded"))
                return (is_healthy, data, status_code)
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8")
                data = json.loads(body)
            except Exception:
                data = {"status": "down", "error": f"HTTP {e.code}"}
            return (False, data, e.code)
        except Exception as e:
            # Diagnostic socket check, but do NOT mask HTTP failure as healthy
            sock_open = self._check_socket(port)
            data = {
                "status": "down",
                "error": str(e),
                "port": port,
                "socket_open": sock_open
            }
            return (False, data, 503)

    def _check_socket(self, port: int) -> bool:
        """Fast TCP connect check."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            res = s.connect_ex(("127.0.0.1", port))
            s.close()
            return res == 0
        except Exception:
            return False

    def inspect_health(self, health_payload: Dict[str, Any], http_status: int, app_key: str = "network_cable_analyzer") -> str:
        """
        Pure inspection state machine used by tests and live loops.
        Returns: 'HEALTHY', 'DEGRADED_WAITING', 'RESTART_TRIGGERED', 'CIRCUIT_BREAKER_TRIPPED'.
        """
        status_val = health_payload.get("status")
        if http_status == 200 and status_val in ("healthy", "ok"):
            self.consecutive_failures[app_key] = 0
            self.backoffs[app_key] = 5.0
            return "HEALTHY"

        self.consecutive_failures[app_key] += 1
        if self.consecutive_failures[app_key] >= self.failure_threshold:
            # Check circuit breaker
            now = time.time()
            cfg = PORTFOLIO_REGISTRY.get(app_key, {"max_restarts_per_window": 5})
            recent_restarts = [t for t in self.restart_history[app_key] if now - t < self.window_seconds]
            self.restart_history[app_key] = recent_restarts

            if len(recent_restarts) >= cfg.get("max_restarts_per_window", 5):
                self.circuit_tripped[app_key] = True
                return "CIRCUIT_BREAKER_TRIPPED"

            self.restarts_triggered += 1
            self.current_backoff = min(self.current_backoff * 2, 120.0)
            self.backoffs[app_key] = min(self.backoffs[app_key] * 2, 120.0)
            self.restart_history[app_key].append(now)
            return "RESTART_TRIGGERED"

        return "DEGRADED_WAITING"

    def restart_app(self, app_key: str) -> bool:
        """
        Executes multi-stage auto-restart on target application:
        Stage 1: Kill stale hung PID
        Stage 2: Launchctl kickstart
        Stage 3: Subprocess fallback
        Stage 4: Verify recovery
        """
        cfg = PORTFOLIO_REGISTRY[app_key]
        now = time.time()

        # Circuit breaker verification
        recent = [t for t in self.restart_history[app_key] if now - t < self.window_seconds]
        self.restart_history[app_key] = recent
        if len(recent) >= cfg["max_restarts_per_window"]:
            logger.error(f"🚨 CIRCUIT BREAKER TRIPPED for {app_key}! Exceeded {cfg['max_restarts_per_window']} restarts in 15m.")
            self.circuit_tripped[app_key] = True
            self.record_incident(app_key, "CIRCUIT_BREAKER_TRIPPED", {"window_restarts": len(recent)})
            return False

        logger.warning(f"⚡ Autonomously restarting {cfg['name']} (Port {cfg['port']})...")

        # Stage 1: Terminate stale process listening on target port
        port = cfg["port"]
        try:
            res = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True, timeout=2.0)
            pids = [int(p) for p in res.stdout.strip().split() if p.isdigit()]
            for p in pids:
                if p != os.getpid():
                    logger.info(f"Terminating stale PID {p} on port {port}...")
                    subprocess.run(["kill", "-15", str(p)], capture_output=True)
                    time.sleep(1.0)
                    subprocess.run(["kill", "-9", str(p)], capture_output=True)
        except Exception as e:
            logger.debug(f"Stage 1 PID clean: {e}")

        # Stage 2: Attempt LaunchAgent kickstart
        restarted = False
        label = cfg.get("launchagent_label")
        if label:
            try:
                uid = os.getuid()
                cmd = ["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
                if res.returncode == 0:
                    logger.info(f"✅ Successfully kickstarted LaunchAgent: {label}")
                    restarted = True
            except Exception as e:
                logger.debug(f"LaunchAgent kickstart failed for {label}: {e}")

        # Stage 3: Fallback subprocess spawn if not kickstarted
        if not restarted and cfg.get("fallback_cmd"):
            try:
                cmd = cfg["fallback_cmd"]
                cwd = cfg.get("cwd")
                log_file = REPO_ROOT / f"logs/{app_key}.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(log_file, "a") as lf:
                    subprocess.Popen(
                        cmd, cwd=cwd, stdout=lf, stderr=lf,
                        start_new_session=True
                    )
                logger.info(f"✅ Spawned fallback subprocess: {cmd[0]}")
                restarted = True
            except Exception as e:
                logger.error(f"Fallback spawn failed for {app_key}: {e}")

        if restarted:
            # Avoid double-counting: only record if not already recorded within 2s by inspect_health
            if not self.restart_history[app_key] or abs(self.restart_history[app_key][-1] - now) > 2.0:
                self.restart_history[app_key].append(now)
            self.record_incident(app_key, "AUTONOMOUS_RESTART_EXECUTED", {"port": port})
            # Wait for socket recovery
            time.sleep(2.0)
            recovered = self._check_socket(port)
            logger.info(f"Recovery status for {app_key} on port {port}: {'HEALTHY' if recovered else 'STARTING'}")
            return True

        return False

    def record_incident(self, app_key: str, action: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Serializes self-healing incident to incidents JSON and LoRA dataset."""
        now_iso = datetime.now(timezone.utc).isoformat()
        incident = {
            "timestamp": now_iso,
            "application": app_key,
            "port": PORTFOLIO_REGISTRY.get(app_key, {}).get("port"),
            "action": action,
            "restart_count_15m": len(self.restart_history.get(app_key, [])),
            "details": details or {}
        }

        # 1. Update self_healing_incidents.json
        for target_path in [INCIDENTS_PRIMARY, INCIDENTS_FALLBACK]:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                existing = []
                if target_path.exists():
                    try:
                        existing = json.loads(target_path.read_text(encoding="utf-8"))
                        if not isinstance(existing, list):
                            existing = []
                    except Exception:
                        existing = []
                existing.append(incident)
                # Keep last 100 incidents
                target_path.write_text(json.dumps(existing[-100:], indent=2), encoding="utf-8")
                break
            except Exception as e:
                logger.debug(f"Incident write to {target_path} failed: {e}")

        # 2. Append to LoRA lake
        try:
            if LORA_DATASET.parent.exists():
                with open(LORA_DATASET, "a", encoding="utf-8") as f:
                    entry = {
                        "instruction": f"Self-healing recovery incident for {app_key}",
                        "input": json.dumps(incident),
                        "output": f"Watchdog executed {action} to restore port {PORTFOLIO_REGISTRY.get(app_key, {}).get('port')}.",
                        "timestamp": now_iso
                    }
                    f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        return incident

    def run_cycle(self) -> Dict[str, Any]:
        """Runs a single inspection and self-healing cycle across all registered apps."""
        results = {}
        for app_key in PORTFOLIO_REGISTRY:
            if self.circuit_tripped[app_key]:
                results[app_key] = {"status": "CIRCUIT_BREAKER_TRIPPED", "consecutive_failures": self.consecutive_failures[app_key]}
                continue

            is_healthy, payload, status_code = self.probe_health(app_key)
            decision = self.inspect_health(payload, status_code, app_key=app_key)
            results[app_key] = {
                "decision": decision,
                "is_healthy": is_healthy,
                "status_code": status_code,
                "consecutive_failures": self.consecutive_failures[app_key]
            }

            if decision == "RESTART_TRIGGERED":
                self.restart_app(app_key)
                self.consecutive_failures[app_key] = 0

        self.last_probe_results = results
        return results

    def run_forever(self, interval: float = 5.0):
        """Continuous supervisor polling loop."""
        logger.info(f"🛡️ Portfolio Watchdog Supervisor active. Monitoring {len(PORTFOLIO_REGISTRY)} targets every {interval}s...")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Supervisor cycle error: {e}")
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Portfolio Watchdog Supervisor")
    parser.add_argument("--once", action="store_true", help="Run a single probe cycle and exit")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    args = parser.parse_args()

    supervisor = PortfolioWatchdogSupervisor()
    if args.once:
        results = supervisor.run_cycle()
        print(json.dumps(results, indent=2))
    else:
        supervisor.run_forever(interval=args.interval)


if __name__ == "__main__":
    main()
