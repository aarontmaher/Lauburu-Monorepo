import re
with open("backend/agents/crons/daemon_supervisor.py", "r") as f:
    content = f.read()

container_method = """    async def _check_and_heal_containers(self) -> Dict[str, str]:
        \"\"\"Check Docker containers and restart crashed or unhealthy ones.\"\"\"
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
                
            lines = stdout.decode('utf-8').strip().split('\\n')
            for line in lines:
                if not line: continue
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
            logger.error(f"Failed to check containers: {e}")
            
        return container_status

    async def run_monitoring_cycle(self) -> Dict[str, Any]:"""

content = content.replace("    async def run_monitoring_cycle(self) -> Dict[str, Any]:", container_method)

run_monitoring_patch = """        for name, cmds in self.DAEMON_COMMANDS.items():
            is_running = await self._check_daemon(name, cmds)
            
            if not is_running:
                # Daemon is down, attempt restart
                restarted = await self._restart_daemon(name, cmds)
                if restarted:
                    actions_taken.append(f"Restarted daemon: {name}")
                current_status[name] = "RESTARTING"
            else:
                current_status[name] = "ONLINE"
                
        # --- NEW: Docker Container Check ---
        if current_status.get("docker") == "ONLINE":
            container_stats = await self._check_and_heal_containers()
            current_status["docker_containers"] = container_stats
            for c_name, c_state in container_stats.items():
                if c_state == "RESTARTED":
                    actions_taken.append(f"Restarted container: {c_name}")
        # -----------------------------------
        
        self.status_history = current_status"""

# Find the loop block and replace
content = re.sub(
    r"\s+for name, cmds in self\.DAEMON_COMMANDS\.items\(\):.*?\n\s+self\.status_history = current_status",
    run_monitoring_patch,
    content,
    flags=re.DOTALL
)

with open("backend/agents/crons/daemon_supervisor.py", "w") as f:
    f.write(content)
