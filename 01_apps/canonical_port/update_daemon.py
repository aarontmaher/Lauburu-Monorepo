with open("backend/agents/crons/daemon_supervisor.py", "w") as f:
    f.write('''import asyncio
import logging
import os
import platform
import subprocess
import time
from typing import Dict, Any, List

logger = logging.getLogger("DaemonSupervisor")

MAX_RESTART_ATTEMPTS = 3
BASE_COOLDOWN_SECONDS = 60.0
MAX_COOLDOWN_SECONDS = 1800.0


class DaemonSupervisor:
    """Supervises local OS daemons and Docker containers with circuit breakers and exponential backoff."""

    def __init__(self):
        self.status_history = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_restart_time: Dict[str, float] = {}
        self._os_type = platform.system()

    def _get_daemon_commands(self) -> Dict[str, Dict[str, List[str]]]:
        is_mac = self._os_type == "Darwin"
        return {
            "docker": {
                "check": ["docker", "info"],
                "start": ["open", "-a", "Docker"] if is_mac else ["systemctl", "start", "docker"],
            },
            "tailscale": {
                "check": ["tailscale", "status"],
                "start": ["tailscale", "up"] if is_mac else ["systemctl", "start", "tailscaled"],
            },
            "cloudflared": {
                "check": ["pgrep", "-x", "cloudflared"],
                "start": ["cloudflared", "tunnel", "run"],
            },
            "llama.cpp": {
                "check": ["pgrep", "-f", "llama-server"],
                "start": ["./llama-server", "--port", "50052"],
            },
            "openclaw": {
                "check": ["pgrep", "-f", "openclaw"],
                "start": ["uv", "run", "openclaw"],
            },
            "seaweedfs": {
                "check": ["pgrep", "-f", "weed"],
                "start": ["weed", "server"],
            },
            "movesense": {
                "check": ["pgrep", "-f", "movesense_api_daemon"],
                "start": ["uv", "run", "python", "../03_biometrics_and_telemetry/movesense_api_daemon.py"],
            },
        }

    async def _check_daemon(self, name: str, cmds: Dict[str, List[str]]) -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                *cmds["check"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def _restart_daemon(self, name: str, cmds: Dict[str, List[str]]) -> bool:
        now = time.time()
        attempts = self.restart_counts.get(name, 0)

        if attempts >= MAX_RESTART_ATTEMPTS:
            last_time = self.last_restart_time.get(name, 0)
            if now - last_time < MAX_COOLDOWN_SECONDS:
                logger.warning(f"Daemon '{name}' is in CIRCUIT_OPEN quarantine ({attempts} failed restarts). Skipping.")
                return False
            else:
                self.restart_counts[name] = 0
                attempts = 0

        cooldown = min(BASE_COOLDOWN_SECONDS * (2 ** attempts), MAX_COOLDOWN_SECONDS)
        last_time = self.last_restart_time.get(name, 0)
        if now - last_time < cooldown:
            logger.info(f"Daemon '{name}' in backoff cooldown ({cooldown - (now - last_time):.1f}s remaining).")
            return False

        logger.info(f"Restarting daemon '{name}' (Attempt {attempts + 1}/{MAX_RESTART_ATTEMPTS})...")
        try:
            subprocess.Popen(
                cmds["start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            self.restart_counts[name] = attempts + 1
            self.last_restart_time[name] = now
            return True
        except Exception as e:
            logger.error(f"Failed to spawn restart process for {name}: {e}")
            return False

    async def _check_and_heal_containers(self) -> Dict[str, str]:
        container_status = {}
        try:
            process = await asyncio.create_subprocess_shell(
                "docker ps -a --format '{{.Names}}|{{.State}}|{{.Status}}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if process.returncode != 0:
                return {"docker_daemon": "OFFLINE_OR_UNAVAILABLE"}

            for line in stdout.decode('utf-8').strip().split('\\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    name, state, status = parts[0], parts[1], parts[2]
                    is_unhealthy = "unhealthy" in status.lower()
                    is_exited = state.lower() == "exited"
                    if is_exited or is_unhealthy:
                        logger.info(f"Container {name} is {state}/{status}. Restarting...")
                        restart_proc = await asyncio.create_subprocess_shell(
                            f"docker restart {name}",
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        await restart_proc.wait()
                        container_status[name] = "RESTARTED"
                    else:
                        container_status[name] = "HEALTHY"
        except Exception as e:
            logger.error(f"Error checking Docker containers: {e}")
        return container_status

    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        current_status = {}
        actions_taken = []
        daemon_cmds = self._get_daemon_commands()

        for name, cmds in daemon_cmds.items():
            is_running = await self._check_daemon(name, cmds)
            if is_running:
                current_status[name] = "ONLINE"
                self.restart_counts[name] = 0
            else:
                current_status[name] = "OFFLINE"
                restarted = await self._restart_daemon(name, cmds)
                if restarted:
                    current_status[name] = "RESTARTING"
                    actions_taken.append(f"Restarted daemon: {name}")
                elif self.restart_counts.get(name, 0) >= MAX_RESTART_ATTEMPTS:
                    current_status[name] = "QUARANTINED"

        # Check Docker containers only if Docker daemon is online
        container_results = {}
        if current_status.get("docker") == "ONLINE":
            container_results = await self._check_and_heal_containers()

        report = {
            "timestamp": time.time(),
            "daemons": current_status,
            "containers": container_results,
            "actions_taken": actions_taken,
        }
        self.status_history[time.strftime("%Y-%m-%d %H:%M:%S")] = report
        return report


supervisor = DaemonSupervisor()
''')
