"""
Lauburu Mesh - Docker Container Engine & Microservices Manager
Provides container lifecycle orchestration, health telemetry, and compose service management.
"""

import os
import sys
import time
import json
import shutil
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
COMPOSE_MASTER = REPO_ROOT / "00_core_infrastructure" / "docker-compose.master.yml"

class DockerEngine:
    @staticmethod
    def get_daemon_status() -> Dict[str, Any]:
        """Checks if Docker engine / Colima runtime is active and reachable."""
        colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
        default_sock = Path("/var/run/docker.sock")
        
        sock_path = None
        if colima_sock.exists():
            sock_path = str(colima_sock)
        elif default_sock.exists():
            sock_path = str(default_sock)

        has_docker_cli = shutil.which("docker") is not None
        has_colima = shutil.which("colima") is not None

        is_running = False
        daemon_info = {}
        
        if has_docker_cli:
            try:
                env = os.environ.copy()
                if sock_path and "DOCKER_HOST" not in env:
                    env["DOCKER_HOST"] = f"unix://{sock_path}"
                
                res = subprocess.run(["docker", "info", "--format", "{{json .}}"], capture_output=True, text=True, timeout=3, env=env)
                if res.returncode == 0:
                    info = json.loads(res.stdout)
                    is_running = True
                    daemon_info = {
                        "containers_total": info.get("Containers", 0),
                        "containers_running": info.get("ContainersRunning", 0),
                        "containers_paused": info.get("ContainersPaused", 0),
                        "containers_stopped": info.get("ContainersStopped", 0),
                        "images_count": info.get("Images", 0),
                        "server_version": info.get("ServerVersion", "Unknown"),
                        "memory_total_gb": round(info.get("MemTotal", 0) / (1024**3), 2),
                        "cpus": info.get("NCPU", 0),
                        "storage_driver": info.get("Driver", "overlay2")
                    }
            except Exception:
                pass

        return {
            "status": "RUNNING" if is_running else "STANDBY",
            "docker_cli_available": has_docker_cli,
            "colima_available": has_colima,
            "active_socket": sock_path,
            "compose_manifest_exists": COMPOSE_MASTER.exists(),
            "daemon_info": daemon_info,
            "timestamp": time.time()
        }

    @staticmethod
    def list_containers() -> List[Dict[str, Any]]:
        """Lists active and inactive containers across the local Docker runtime."""
        containers = []
        if not shutil.which("docker"):
            return containers

        try:
            env = os.environ.copy()
            colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
            if colima_sock.exists() and "DOCKER_HOST" not in env:
                env["DOCKER_HOST"] = f"unix://{colima_sock}"

            cmd = ["docker", "ps", "-a", "--format", "{{json .}}"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4, env=env)
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                        containers.append({
                            "id": c.get("ID", "")[:12],
                            "name": c.get("Names", "unknown"),
                            "image": c.get("Image", "unknown"),
                            "state": c.get("State", "unknown").upper(),
                            "status": c.get("Status", "unknown"),
                            "ports": c.get("Ports", "None"),
                            "is_running": (c.get("State", "").lower() == "running")
                        })
                    except Exception:
                        continue
        except Exception:
            pass

        return containers

    @staticmethod
    def execute_compose_action(action: str = "up") -> Dict[str, Any]:
        """Manages the Master Compose stack (up, down, restart)."""
        if not COMPOSE_MASTER.exists():
            return {"status": "ERROR", "message": "Master docker-compose.yml not found"}

        env = os.environ.copy()
        colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
        if colima_sock.exists() and "DOCKER_HOST" not in env:
            env["DOCKER_HOST"] = f"unix://{colima_sock}"

        try:
            if action == "up":
                cmd = ["docker", "compose", "-f", str(COMPOSE_MASTER), "up", "-d"]
            elif action == "down":
                cmd = ["docker", "compose", "-f", str(COMPOSE_MASTER), "down"]
            elif action == "restart":
                cmd = ["docker", "compose", "-f", str(COMPOSE_MASTER), "restart"]
            else:
                return {"status": "ERROR", "message": f"Unsupported action: {action}"}

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
            return {
                "status": "SUCCESS" if res.returncode == 0 else "ERROR",
                "action": action,
                "output": res.stdout or res.stderr
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

if __name__ == "__main__":
    print("=== 🐳 DOCKER ENGINE STATUS ===")
    print(json.dumps(DockerEngine.get_daemon_status(), indent=2))
    print("\n=== 📦 CONTAINER LIST ===")
    print(json.dumps(DockerEngine.list_containers(), indent=2))
