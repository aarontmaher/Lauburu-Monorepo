import logging
import time

logger = logging.getLogger(__name__)

class DaemonManager:
    def __init__(self, orchestrator_devices, lora_logger):
        """
        Manages high availability (HA) for critical mesh daemons.
        :param orchestrator_devices: A reference to the orchestrator's loaded device contexts.
        :param lora_logger: A reference to the LoraLogger for telemetry.
        """
        self.devices = orchestrator_devices
        self.lora = lora_logger
        
        # Define our critical daemons and their failover path (Primary Node -> Fallback Node)
        # Commands dictate how to check status and how to start/resurrect the daemon
        self.critical_daemons = {
            "docker_colima": {
                "display_name": "Docker / Colima Container Engine",
                "primary": "Mac_Node",
                "fallback": "Linux_Head_Node",
                "check_cmd": "colima status >/dev/null 2>&1 || docker info >/dev/null 2>&1 || pgrep -f 'colima|dockerd'",
                "start_cmd": "colima start >/dev/null 2>&1 || sudo systemctl start docker >/dev/null 2>&1 &",
                "icon": "🐳"
            },
            "llama.cpp_rpc": {
                "display_name": "llama.cpp RPC Distributed Server",
                "primary": "Mac_Node",
                "fallback": "Linux_Head_Node",
                "check_cmd": "pgrep -f llama-rpc-server",
                "start_cmd": "nohup llama-rpc-server --host 0.0.0.0 --port 50052 > /dev/null 2>&1 &",
                "icon": "🧠"
            },
            "openclaw": {
                "display_name": "OpenClaw Proxy Gateway",
                "primary": "Mac_Node",
                "fallback": "Linux_Head_Node",
                "check_cmd": "pgrep -f openclaw",
                "start_cmd": "nohup openclaw-proxy --bind 0.0.0.0 > /dev/null 2>&1 &",
                "icon": "⚡"
            },
            "cloudflared": {
                "display_name": "Cloudflare Edge Tunnel",
                "primary": "Mac_Node",
                "fallback": "Linux_Head_Node",
                "check_cmd": "pgrep -f cloudflared",
                "start_cmd": "nohup cloudflared tunnel run swarm-tunnel > /dev/null 2>&1 &",
                "icon": "🛡️"
            }
        }
        
        # Track detailed state of each daemon for UI and self-healing
        self.daemons_state = {}
        self.active_locations = {daemon: config["primary"] for daemon, config in self.critical_daemons.items()}

    def _execute_on_node(self, node_name, cmd, timeout=3):
        """Helper to run a shell command on a specific node via its AdbHelper/SSH context."""
        if node_name not in self.devices:
            logger.error(f"Node {node_name} not found in active devices.")
            return None
        
        adb = self.devices[node_name]["adb"]
        return adb.run_shell(cmd, timeout=timeout)

    def _check_daemon_health(self, daemon_name, node_name):
        """Returns True if the daemon is running on the specified node."""
        cmd = self.critical_daemons[daemon_name]["check_cmd"]
        result = self._execute_on_node(node_name, cmd, timeout=3)
        
        # pgrep returns 0 if found, 1 if not found
        if result and result.returncode == 0:
            return True
        return False

    def _resurrect_daemon(self, daemon_name, target_node):
        """Attempts to start the daemon on the target node."""
        # Check target node reachability first to avoid long timeouts
        reachability = self._execute_on_node(target_node, "echo 1", timeout=2)
        if not reachability or reachability.returncode != 0:
            logger.warning(f"[HA] Target node {target_node} is unreachable. Skipping resurrection of {daemon_name}.")
            telemetry = {"daemon": daemon_name, "target_node": target_node, "reason": "node_unreachable"}
            self.lora.log_telemetry_event(telemetry, "resurrect_daemon", False)
            return False

        logger.info(f"[HA] Attempting to resurrect {daemon_name} on fallback node: {target_node}...")
        cmd = self.critical_daemons[daemon_name]["start_cmd"]
        result = self._execute_on_node(target_node, cmd, timeout=5)
        
        # Give it a second to spin up
        time.sleep(1)
        if self._check_daemon_health(daemon_name, target_node):
            logger.info(f"[HA] Successfully resurrected {daemon_name} on {target_node}!")
            self.active_locations[daemon_name] = target_node
            
            # Log this HA event for AI training
            telemetry = {"daemon": daemon_name, "failed_node": self.critical_daemons[daemon_name]["primary"], "fallback_node": target_node}
            self.lora.log_telemetry_event(telemetry, "resurrect_daemon", True)
            return True
        else:
            logger.error(f"[HA] Failed to resurrect {daemon_name} on {target_node}.")
            telemetry = {"daemon": daemon_name, "target_node": target_node}
            self.lora.log_telemetry_event(telemetry, "resurrect_daemon", False)
            return False

    def evaluate_daemons(self):
        """Iterates through all critical daemons and ensures they are running somewhere in the mesh."""
        logger.info("Evaluating Swarm Daemon HA Status...")
        for daemon, config in self.critical_daemons.items():
            current_node = self.active_locations[daemon]
            
            is_running = self._check_daemon_health(daemon, current_node)
            
            extra_info = None
            if is_running and daemon == "docker_colima":
                # Gather empirical container count if active
                res = self._execute_on_node(current_node, "docker ps -q 2>/dev/null | wc -l", timeout=2)
                if res and res.returncode == 0:
                    cnt = res.stdout.strip()
                    extra_info = f"{cnt} active containers (Colima virtiofs)"
                else:
                    extra_info = "Engine Active"
            elif is_running and daemon == "llama.cpp_rpc":
                extra_info = "Port 50052 Active"
            elif is_running and daemon == "openclaw":
                extra_info = "Port 18789 Active"
            elif is_running and daemon == "cloudflared":
                extra_info = "Tunnel Active ($0 Free Tier)"
            
            if is_running:
                logger.debug(f"[HA] {daemon} is healthy on {current_node}.")
                self.daemons_state[daemon] = {
                    "display_name": config.get("display_name", daemon),
                    "icon": config.get("icon", "🛡️"),
                    "status": "HEALTHY",
                    "location": current_node,
                    "primary": config["primary"],
                    "fallback": config["fallback"],
                    "extra_info": extra_info,
                    "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            else:
                logger.warning(f"[HA] CRITICAL: {daemon} is offline on {current_node}!")
                
                # Determine failover path
                fallback_node = config["fallback"] if current_node == config["primary"] else config["primary"]
                
                # Trigger Resurrection
                resurrected = self._resurrect_daemon(daemon, fallback_node)
                self.daemons_state[daemon] = {
                    "display_name": config.get("display_name", daemon),
                    "icon": config.get("icon", "🛡️"),
                    "status": "RESURRECTED" if resurrected else "OFFLINE",
                    "location": fallback_node if resurrected else current_node,
                    "primary": config["primary"],
                    "fallback": config["fallback"],
                    "extra_info": "Failover Triggered" if resurrected else "Resurrection Failed",
                    "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }

    def get_daemons_state(self):
        """Returns the full rich dictionary of HA daemons for the API & frontend."""
        return self.daemons_state or {
            daemon: {
                "display_name": config.get("display_name", daemon),
                "icon": config.get("icon", "🛡️"),
                "status": "HEALTHY",
                "location": self.active_locations.get(daemon, config["primary"]),
                "primary": config["primary"],
                "fallback": config["fallback"],
                "extra_info": "Active",
                "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            for daemon, config in self.critical_daemons.items()
        }
