import subprocess
import logging
import os

logger = logging.getLogger(__name__)

class SSHHandler:
    def __init__(self, host="127.0.0.1", username="root", port=22, key_file=None, relay_host=None, relay_cmd=None):
        self.host = host
        self.username = username
        self.port = int(port) if port is not None else 22
        key_candidates = [
            os.path.expanduser(key_file) if key_file else None,
            os.path.expanduser("~/.ssh/id_ed25519"),
            os.path.expanduser("~/.ssh/id_ed25519_monorepo"),
            os.path.expanduser("~/.ssh/id_rsa"),
            "/Users/aaron/DFS_UNIFIED/.ssh/id_ed25519",
            "/Users/aaron/.ssh/id_ed25519",
        ]
        self.key_file = None
        for k in key_candidates:
            if k and os.path.exists(k):
                self.key_file = k
                break

        self.relay_host = relay_host
        self.relay_cmd = relay_cmd

    def run_cmd(self, cmd_string, timeout=20.0):
        """
        Executes a command over SSH (or via SSH relay).
        :param cmd_string: The command string to execute on the remote host.
        :return: A subprocess.CompletedProcess-like object or None on failure/timeout.
        """
        try:
            if self.relay_host and self.relay_cmd:
                # Enforce minimum 20.0s timeout for relay connections to prevent Dropbear socket contention timeouts
                if timeout < 20.0:
                    timeout = 20.0
                # Relay connection (e.g. Linux_Head_Node via router relay)
                relay_target_user = "root"
                if os.path.exists("/opt/homebrew/bin/sshpass"):
                    relay_base = ["/opt/homebrew/bin/sshpass", "-p", "goldfighting1", "ssh", "-n", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
                else:
                    relay_base = ["ssh", "-n", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]
                if self.key_file and os.path.exists(self.key_file):
                    relay_base.extend(["-i", self.key_file])
                
                formatted_relay_cmd = self.relay_cmd
                if "dbclient" in formatted_relay_cmd:
                    if "-y" not in formatted_relay_cmd:
                        parts = formatted_relay_cmd.split("dbclient", 1)
                        formatted_relay_cmd = parts[0] + "dbclient -y" + parts[1]
                    if "DROPBEAR_PASSWORD" not in formatted_relay_cmd:
                        formatted_relay_cmd = f"DROPBEAR_PASSWORD='goldfighting1' {formatted_relay_cmd}"
                
                safe_cmd_string = cmd_string.replace("'", "'\\''")
                remote_cmd = f"{formatted_relay_cmd} '{safe_cmd_string}'"
                full_cmd = relay_base + [f"{relay_target_user}@{self.relay_host}", remote_cmd]
            else:
                base_cmd = ["ssh", "-n", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes"]
                if self.port:
                    base_cmd.extend(["-p", str(self.port)])
                if self.key_file and os.path.exists(self.key_file):
                    base_cmd.extend(["-i", self.key_file])
                
                base_cmd.append(f"{self.username}@{self.host}")
                if self.port == 8022 and "export PATH=" not in cmd_string:
                    exec_cmd = f"export PATH=/data/data/com.termux/files/usr/bin:$PATH; {cmd_string}"
                else:
                    exec_cmd = cmd_string
                full_cmd = base_cmd + [exec_cmd]

            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0 and os.path.exists("/opt/homebrew/bin/sshpass") and not (self.relay_host and self.relay_cmd):
                # Fallback to sshpass if key auth failed
                fallback_cmd = ["/opt/homebrew/bin/sshpass", "-p", "goldfighting1", "ssh", "-n", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5"]
                if self.port:
                    fallback_cmd.extend(["-p", str(self.port)])
                fallback_cmd.append(f"{self.username}@{self.host}")
                fallback_cmd.append(cmd_string)
                result = subprocess.run(
                    fallback_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            if result.returncode != 0:
                logger.warning(f"SSH command failed: {cmd_string}\nError: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"SSH command timed out after {timeout}s: {cmd_string}")
            return None
        except Exception as e:
            logger.error(f"Error running SSH command: {e}")
            return None
