"""
Stage 3 SSH / Mosh High-Throughput Handoff & Session Spawner
Part of Canonical Mesh Fallback Terminal (bluetooth_terminal_ide).

Governs:
- Non-blocking subnet reachability detector probing 192.168.44.1:8022 (Termux) and :22 with 2-probe debounce
- Non-blocking adaptive session spawner (Mode A: Tmux split, Mode B: app.suspend(), Mode C: Background tunnel)
- Adaptive binary selection (mosh -> /usr/bin/ssh fallback)
- Stage 3 keepalive watchdog (3s interval, 3 misses triggers demotion)
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("mesh_healer.session_spawner")

DEFAULT_GATEWAY_IP = "192.168.44.1"
DEFAULT_SSH_PORTS = (8022, 22)


class SessionSpawner:
    """
    Manages Stage 3 high-throughput SSH/Mosh handoff, reachability verification,
    and link collapse recovery watchdog.
    """

    def __init__(
        self,
        app: Optional[Any] = None,
        custom_binary_path: Optional[str] = None,
        gateway_ip: str = DEFAULT_GATEWAY_IP,
        ssh_ports: Tuple[int, ...] = DEFAULT_SSH_PORTS,
        ssh_user: str = "u0_a363",
        watchdog_interval: float = 3.0,
        on_link_collapsed: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.app = app
        self.custom_binary_path = custom_binary_path
        self.gateway_ip = gateway_ip
        self.ssh_ports = ssh_ports
        self.ssh_user = ssh_user
        self.watchdog_interval = watchdog_interval
        self.on_link_collapsed = on_link_collapsed

        self.active_port: Optional[int] = None
        self.active_process: Optional[asyncio.subprocess.Process] = None
        self.active_pid: Optional[int] = None
        self.is_session_active: bool = False
        self._watchdog_task: Optional[asyncio.Task] = None
        self._watchdog_running: bool = False
        self.consecutive_watchdog_misses: int = 0

    async def probe_single_target(
        self, host: str, port: int, timeout: float = 1.0
    ) -> bool:
        """Asynchronously checks if a TCP port is open on host."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            return False

    async def probe_reachability(
        self,
        host: Optional[str] = None,
        ports: Optional[Tuple[int, ...]] = None,
        timeout: float = 1.0,
    ) -> Tuple[bool, Optional[int]]:
        """
        Executes a 2-probe debounce gate to verify subnet reachability.
        Returns (is_reachable: bool, active_port: Optional[int]).
        """
        target_host = host or self.gateway_ip
        candidate_ports = ports or self.ssh_ports

        # First probe pass
        found_port: Optional[int] = None
        for port in candidate_ports:
            if await self.probe_single_target(target_host, port, timeout=timeout):
                found_port = port
                break

        if not found_port:
            return False, None

        # Debounce: wait briefly and verify with 2nd probe pass
        await asyncio.sleep(0.3)
        if await self.probe_single_target(target_host, found_port, timeout=timeout):
            self.active_port = found_port
            return True, found_port

        return False, None

    def resolve_binary_and_command(
        self, host: str, port: int, user: str
    ) -> Tuple[str, List[str], str]:
        """
        Dynamically selects mosh or ssh and generates invocation command arguments.
        Returns (binary_name, arg_list, full_command_string).
        """
        if self.custom_binary_path and os.path.exists(self.custom_binary_path):
            args = [self.custom_binary_path, "-p", str(port), f"{user}@{host}"]
            full_str = f"{self.custom_binary_path} -p {port} {user}@{host}"
            return self.custom_binary_path, args, full_str

        mosh_path = shutil.which("mosh")
        if mosh_path:
            # Mosh available
            args = [
                mosh_path,
                f"--ssh=ssh -p {port}",
                f"{user}@{host}",
            ]
            full_str = f"mosh --ssh='ssh -p {port}' {user}@{host}"
            return "mosh", args, full_str

        ssh_path = shutil.which("ssh") or "/usr/bin/ssh"
        args = [
            ssh_path,
            "-p",
            str(port),
            "-o",
            "StrictHostKeyChecking=no",
            f"{user}@{host}",
        ]
        full_str = f"ssh -p {port} -o StrictHostKeyChecking=no {user}@{host}"
        return "ssh", args, full_str

    async def spawn_session(
        self,
        mode: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Spawns SSH/Mosh session non-blockingly without freezing Textual TUI.
        Modes:
        - "tmux": Splits current tmux window horizontally (zero TUI disruption)
        - "suspend": Uses Textual app.suspend() for full interactive terminal
        - "background": Async background headless tunnel
        Auto-detects mode if not explicitly provided.
        """
        target_host = host or self.gateway_ip
        target_port = port or self.active_port or 8022
        target_user = user or self.ssh_user

        binary_name, cmd_args, cmd_str = self.resolve_binary_and_command(
            target_host, target_port, target_user
        )

        selected_mode = mode
        if not selected_mode:
            if os.environ.get("TMUX") and shutil.which("tmux"):
                selected_mode = "tmux"
            elif self.app and hasattr(self.app, "suspend"):
                selected_mode = "suspend"
            else:
                selected_mode = "background"

        logger.info(f"Spawning Stage 3 session using Mode '{selected_mode}': {cmd_str}")

        try:
            if self.active_process and self.active_process.returncode is None:
                logger.info("Existing active Stage 3 session detected; terminating prior session before re-spawning.")
                await self.terminate_session()

            if selected_mode == "tmux":
                tmux_bin = shutil.which("tmux") or "tmux"
                # Split tmux window horizontally and launch shell command
                tmux_proc = await asyncio.create_subprocess_exec(
                    tmux_bin,
                    "split-window",
                    "-h",
                    cmd_str,
                )
                await tmux_proc.wait()
                self.is_session_active = (tmux_proc.returncode == 0)
                msg = f"[STAGE 3] Tmux pane spawned for {binary_name} ({target_host}:{target_port})."
                self.start_watchdog(target_host, target_port)
                return True, msg

            elif selected_mode == "suspend" and self.app and hasattr(self.app, "suspend"):
                # Execute inside suspend context in non-blocking thread or synchronous runner
                # Note: app.suspend() clears alternate screen and pauses Textual
                def _run_interactive():
                    with self.app.suspend():
                        return subprocess.run(cmd_args)

                loop = asyncio.get_running_loop()
                self.is_session_active = True
                try:
                    result = await loop.run_in_executor(None, _run_interactive)
                finally:
                    self.is_session_active = False
                exit_code = getattr(result, "returncode", 0)
                msg = f"[STAGE 3] Interactive session {binary_name} completed via app.suspend() (Exit code: {exit_code})."
                return True, msg

            else:
                # Background headless process
                self.active_process = await asyncio.create_subprocess_exec(
                    *cmd_args,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                self.active_pid = self.active_process.pid
                self.is_session_active = True
                msg = f"[STAGE 3] Background tunnel {binary_name} active (PID {self.active_pid})."
                self.start_watchdog(target_host, target_port)
                return True, msg

        except Exception as e:
            logger.error(f"Failed to spawn Stage 3 session: {e}")
            self.is_session_active = False
            return False, f"Failed spawning Stage 3 session: {e}"

    def start_watchdog(self, host: str, port: int) -> None:
        """Starts background keepalive watchdog monitoring the active Stage 3 session."""
        if self._watchdog_running:
            self.stop_watchdog()
        self._watchdog_running = True
        self.consecutive_watchdog_misses = 0
        self._watchdog_task = asyncio.create_task(self._watchdog_loop(host, port))

    def stop_watchdog(self) -> None:
        """Stops the keepalive watchdog cleanly."""
        self._watchdog_running = False
        this_task = None
        try:
            this_task = asyncio.current_task()
        except RuntimeError:
            pass
        if self._watchdog_task and not self._watchdog_task.done():
            if self._watchdog_task is not this_task:
                self._watchdog_task.cancel()
        self._watchdog_task = None

    async def _watchdog_loop(self, host: str, port: int) -> None:
        """
        Watchdog loop checking TCP reachability every interval.
        3 consecutive misses marks link collapsed and triggers demotion.
        """
        this_task = asyncio.current_task()
        try:
            while self._watchdog_running and (self._watchdog_task is this_task):
                await asyncio.sleep(self.watchdog_interval)
                is_alive = await self.probe_single_target(host, port, timeout=1.0)
                if is_alive:
                    self.consecutive_watchdog_misses = 0
                else:
                    self.consecutive_watchdog_misses += 1
                    logger.warning(
                        f"Stage 3 watchdog miss ({self.consecutive_watchdog_misses}/3) for {host}:{port}"
                    )
                    if self.consecutive_watchdog_misses >= 3:
                        logger.error(f"Stage 3 link collapsed for {host}:{port}! Triggering demotion.")
                        await self.terminate_session()
                        if self.on_link_collapsed:
                            try:
                                res = self.on_link_collapsed()
                                if asyncio.iscoroutine(res):
                                    await res
                            except Exception as e:
                                logger.error(f"Error in on_link_collapsed callback: {e}")
                        break
        except asyncio.CancelledError:
            pass
        finally:
            if self._watchdog_task is this_task:
                self._watchdog_running = False

    async def terminate_session(self, timeout: float = 1.5) -> None:
        """Terminates active Stage 3 subprocess using SIGTERM, followed by SIGKILL if needed."""
        self.stop_watchdog()
        self.is_session_active = False

        if self.active_process:
            if self.active_process.returncode is None:
                try:
                    self.active_process.send_signal(signal.SIGTERM)
                    try:
                        await asyncio.wait_for(self.active_process.wait(), timeout=timeout)
                    except (asyncio.TimeoutError, TimeoutError):
                        try:
                            self.active_process.kill()
                            await self.active_process.wait()
                        except ProcessLookupError:
                            pass
                except ProcessLookupError:
                    pass
                except Exception as e:
                    logger.warning(f"Error terminating Stage 3 process: {e}")
            self.active_process = None
            self.active_pid = None
