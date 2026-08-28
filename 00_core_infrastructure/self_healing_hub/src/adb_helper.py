import subprocess
import logging
from ssh_handler import SSHHandler

logger = logging.getLogger(__name__)

class AdbHelper:
    def __init__(self, device_id=None, use_ssh=False, ssh_host=None, ssh_user="root", ssh_port=22, ssh_key=None, relay_host=None, relay_cmd=None):
        """
        Initialize the device executor.
        :param device_id: Optional specific device ID (for local ADB).
        :param use_ssh: If True, executes commands directly over SSH to the device, bypassing local ADB.
        """
        self.device_id = device_id
        self.use_ssh = use_ssh
        self.ssh_port = ssh_port
        self.ssh_key = ssh_key
        self.relay_host = relay_host
        self.relay_cmd = relay_cmd

        if self.use_ssh:
            self.ssh_handler = SSHHandler(
                host=ssh_host,
                username=ssh_user,
                port=ssh_port,
                key_file=ssh_key,
                relay_host=relay_host,
                relay_cmd=relay_cmd
            )
        else:
            self.ssh_handler = None

        self.base_adb_cmd = "adb"
        if self.device_id:
            if ":" in self.device_id and not self.use_ssh:
                self._ensure_adb_connected()
            self.base_adb_cmd += f" -s {self.device_id}"

    def _ensure_adb_connected(self):
        """Connect to device over TCP if device_id specifies host:port."""
        if not self.device_id or ":" not in self.device_id:
            return
        try:
            subprocess.run(
                ["adb", "connect", self.device_id],
                capture_output=True,
                text=True,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to connect ADB device {self.device_id}: {e}")

    def run_cmd(self, cmd_args, timeout=10):
        """Run a standard local ADB command (not a shell command)."""
        if self.use_ssh:
            logger.error("Cannot run base ADB commands (like push/pull/install) over direct SSH yet.")
            return None

        if self.device_id and ":" in self.device_id:
            self._ensure_adb_connected()

        full_cmd = self.base_adb_cmd.split() + cmd_args
        try:
            result = subprocess.run(
                full_cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            if result.returncode != 0:
                logger.warning(f"ADB command failed: {' '.join(full_cmd)}\nError: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timed out after {timeout}s: {' '.join(full_cmd)}")
            return None
        except Exception as e:
            logger.error(f"Error running ADB command: {e}")
            return None

    def run_shell(self, shell_cmd, as_root=False, timeout=10):
        """
        Run a shell command on the device.
        If use_ssh is True and host is localhost, runs directly via local subprocess.
        If use_ssh is True, it runs directly via SSH to the device.
        If use_ssh is False, it runs via local ADB shell.
        """
        if self.use_ssh:
            # Check for localhost/127.0.0.1
            if self.ssh_handler and self.ssh_handler.host in ["127.0.0.1", "localhost"]:
                try:
                    res = subprocess.run(["zsh", "-c", shell_cmd], capture_output=True, text=True, timeout=timeout)
                    return res
                except Exception as e:
                    logger.error(f"Localhost command error: {e}")
                    return None

            if as_root:
                safe_cmd = shell_cmd.replace("'", "'\\''")
                cmd_string = f"su -c '{safe_cmd}'"
            else:
                cmd_string = shell_cmd
            logger.debug(f"Executing over direct SSH: {cmd_string}")
            return self.ssh_handler.run_cmd(cmd_string, timeout=timeout)
        else:
            if as_root:
                safe_cmd = shell_cmd.replace("'", "'\\''")
                cmd_args = ["shell", "su", "-c", f"'{safe_cmd}'"]
            else:
                cmd_args = ["shell", shell_cmd]
            return self.run_cmd(cmd_args, timeout=timeout)

    def check_root_access(self):
        """Check if the device grants root access without prompting."""
        result = self.run_shell("id", as_root=True)
        if result and result.returncode == 0 and "uid=0(root)" in result.stdout:
            return True
        return False
