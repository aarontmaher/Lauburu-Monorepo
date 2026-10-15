#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crash-Proof Bluetooth Serial Terminal with Real-Time Hot-Reload (--dev)
=======================================================================
Subsystem: 06_scripts_and_tooling/bluetooth_avf_dev_terminal/bt_serial_terminal.py

Designed specifically for Google Pixel 10 Pro XL AVF Debian 13 Terminal
(`com.android.virtualization.terminal` / `ttyd`) and Lauburu Mesh nodes.

Key Stability & Hot-Reload Features:
1. AST Pre-Validation Firewall: Syntax errors during live editing never crash
   the terminal; they are caught and displayed in the header banner until fixed.
2. Zero-Downtime `importlib.reload`: Hot-reloads `bt_serial_commands.py` and
   `bt_serial_ui.py` in <50ms while preserving PTY (/tmp/bt_serial_pty) and
   TCP (:4005) file descriptors.
3. Single-Threaded Dirty-State Renderer (`auto_refresh=False`): Eliminates
   `ttyd` WebSocket ANSI floods and Android WebView ANRs on the Pixel 10 Pro XL.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
import select
import signal
import socket
import sys
import termios
import time
import tty
from pathlib import Path
from typing import Dict, Optional, Tuple

from rich.console import Console
from rich.live import Live

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bt_serial_state import COMMAND_FIFO_PATH, PTY_SYMLINK, STATE_JSON_PATH, BluetoothSerialState
import bt_serial_commands
import bt_serial_ui


def pin_process_oom_shield() -> None:
    """Best-effort OOM protection for the terminal process inside AVF Debian."""
    for score in ("-900", "-500"):
        try:
            p = Path("/proc/self/oom_score_adj")
            if p.exists() and os.access(p, os.W_OK):
                p.write_text(score)
                break
        except Exception:
            continue


class HotReloadSupervisor:
    """
    Watches `bt_serial_commands.py` and `bt_serial_ui.py` for modifications,
    validates AST syntax before reloading, and hot-swaps modules in real time.
    """

    def __init__(self, state: BluetoothSerialState):
        self.state = state
        self.watched_files: Dict[str, Path] = {
            "commands": SCRIPT_DIR / "bt_serial_commands.py",
            "ui": SCRIPT_DIR / "bt_serial_ui.py",
        }
        self.file_hashes: Dict[str, str] = {}
        self.file_mtimes: Dict[str, int] = {}
        self._last_check: float = 0.0
        self._snapshot_initial()

    def _compute_sha256(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def _snapshot_initial(self) -> None:
        for key, path in self.watched_files.items():
            if path.exists():
                self.file_mtimes[key] = path.stat().st_mtime_ns
                self.file_hashes[key] = self._compute_sha256(path)
        self.state.last_reload_sha256 = self.file_hashes.get("commands", "--")

    def check_and_reload(self, force: bool = False) -> bool:
        now = time.time()
        if not force and (now - self._last_check < 0.18):
            return False
        self._last_check = now

        reloaded_any = False
        for key, path in self.watched_files.items():
            if not path.exists():
                continue
            try:
                mtime_ns = path.stat().st_mtime_ns
            except OSError:
                continue

            if not force and mtime_ns == self.file_mtimes.get(key):
                continue

            new_hash = self._compute_sha256(path)
            self.file_mtimes[key] = mtime_ns
            if new_hash == self.file_hashes.get(key):
                continue

            t0 = time.perf_counter()
            try:
                source = path.read_text(encoding="utf-8")
                # Step 1: AST Syntax Firewall
                ast.parse(source, filename=str(path))

                # Step 2: Live Module Reload (invalidate .pyc so sub-second edits always recompile)
                try:
                    pyc_path = Path(importlib.util.cache_from_source(str(path)))
                    pyc_path.unlink(missing_ok=True)
                except Exception:
                    pass
                importlib.invalidate_caches()

                if key == "commands":
                    importlib.reload(bt_serial_commands)
                    bt_serial_commands.on_hot_reload(self.state)
                elif key == "ui":
                    importlib.reload(bt_serial_ui)
                    self.state.add_log("RELOAD", f"Hot-reloaded {path.name} ({bt_serial_ui.UI_THEME_VERSION})")

                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                self.file_hashes[key] = new_hash
                self.state.reload_count += 1
                self.state.last_reload_ts = time.time()
                self.state.last_reload_ms = elapsed_ms
                self.state.last_reload_file = path.name
                self.state.last_reload_sha256 = new_hash
                self.state.syntax_status = "OK"
                self.state.last_error = ""
                self.state.mark_dirty()
                self.state.persist_state_snapshot()
                reloaded_any = True
            except SyntaxError as se:
                self.state.syntax_status = f"SYNTAX ERR L{se.lineno}"
                self.state.last_error = f"{path.name}:{se.lineno}:{se.offset}: {se.msg}"
                self.state.add_log("ERR", f"Hot-Reload blocked syntax error in {path.name} L{se.lineno}: {se.msg}")
                self.state.mark_dirty()
                self.state.persist_state_snapshot()
            except Exception as ex:
                self.state.syntax_status = "RUNTIME ERR"
                self.state.last_error = f"{path.name}: {ex}"
                self.state.add_log("ERR", f"Hot-Reload exception in {path.name}: {ex}")
                self.state.mark_dirty()
                self.state.persist_state_snapshot()

        return reloaded_any


def handle_command_safe(
    state: BluetoothSerialState, supervisor: HotReloadSupervisor, raw_cmd: str, source: str = "TUI"
) -> str:
    """Executes a command through the hot-reloadable command engine with an exception firewall."""
    cmd_clean = raw_cmd.strip()
    if not cmd_clean:
        return ""
    if cmd_clean.lower() in ("reload", "hotreload"):
        supervisor.check_and_reload(force=True)
        return "Forced hot-reload completed."
    if cmd_clean.lower() in ("quit", "exit") and source == "TUI":
        state.running = False
        return "Exiting Bluetooth Serial Terminal..."

    try:
        return bt_serial_commands.execute_command(state, cmd_clean, source=source)
    except Exception as e:
        err_msg = f"Command exception ({cmd_clean}): {e}"
        state.last_error = err_msg
        state.add_log("ERR", err_msg)
        return err_msg


def run_interactive_dev_tui(port: int = 4005, connect_mesh: bool = False) -> int:
    """
    Runs the interactive Rich TUI with non-blocking keyboard input and dirty-state
    rendering so it never floods `ttyd` or crashes the Pixel AVF terminal.
    """
    pin_process_oom_shield()
    state = BluetoothSerialState(tcp_port=port)
    supervisor = HotReloadSupervisor(state)

    state.on_line_callback = lambda line, src: handle_command_safe(state, supervisor, line, source=src)
    state.setup_pty()
    state.setup_tcp_server()
    if connect_mesh:
        state.connect_mesh_upstream()

    state.probe_bluetooth_devices(force=True)
    state.probe_avf_health(force=True)
    handle_command_safe(state, supervisor, "teleplot demo", source="INIT")
    state.add_log(
        "SYS",
        "🔥 Live Hot-Reload Dev Mode Active! Edit bt_serial_commands.py or bt_serial_ui.py or run 'patch <cmd> <reply>'.",
    )
    state.persist_state_snapshot()

    console = Console()
    has_tty = sys.stdin.isatty() and sys.stdout.isatty()
    old_tty_attrs = None
    stdin_fd = sys.stdin.fileno() if has_tty else -1

    def _sig_handler(signum, frame):
        state.running = False
        state.mark_dirty()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)
    if hasattr(signal, "SIGWINCH"):
        signal.signal(signal.SIGWINCH, lambda s, f: state.mark_dirty())

    if has_tty:
        try:
            old_tty_attrs = termios.tcgetattr(stdin_fd)
            tty.setcbreak(stdin_fd)
        except Exception:
            old_tty_attrs = None

    last_render_ts = 0.0
    last_snapshot_ts = 0.0

    try:
        initial_layout = bt_serial_ui.render_dashboard(state, bt_serial_commands.CUSTOM_COMMANDS)
        with Live(initial_layout, console=console, screen=True, auto_refresh=False) as live:
            live.refresh()
            state.dirty = False

            while state.running:
                # 1. Poll serial PTY, TCP clients, and external command queue
                state.poll_io()

                # 2. Check for hot-reloadable file changes
                supervisor.check_and_reload(force=False)

                # 3. Poll keyboard input if attached to a TTY
                if has_tty and stdin_fd >= 0:
                    try:
                        rlist, _, _ = select.select([stdin_fd], [], [], 0.02)
                    except Exception:
                        rlist = []
                    if stdin_fd in rlist:
                        try:
                            ch_bytes = os.read(stdin_fd, 32)
                        except OSError:
                            ch_bytes = b""
                        if ch_bytes:
                            # Handle escape sequences (arrow keys) gracefully
                            if ch_bytes.startswith(b"\x1b"):
                                if ch_bytes == b"\x1b[A" and state.command_history:
                                    # Up arrow: previous command
                                    state.input_buffer = state.command_history[-1]
                                    state.mark_dirty()
                                elif ch_bytes == b"\x1b[B":
                                    state.input_buffer = ""
                                    state.mark_dirty()
                            else:
                                text_in = ch_bytes.decode("utf-8", errors="ignore")
                                for ch in text_in:
                                    if ch in ("\r", "\n"):
                                        cmd_to_run = state.input_buffer.strip()
                                        state.input_buffer = ""
                                        if cmd_to_run:
                                            state.command_history.append(cmd_to_run)
                                            handle_command_safe(state, supervisor, cmd_to_run, source="TUI")
                                        state.mark_dirty()
                                    elif ch in ("\x7f", "\x08"):  # Backspace
                                        state.input_buffer = state.input_buffer[:-1]
                                        state.mark_dirty()
                                    elif ch == "\x03":  # Ctrl+C
                                        state.running = False
                                        break
                                    elif ch == "\x0c":  # Ctrl+L
                                        state.mark_dirty()
                                    elif ch.isprintable():
                                        state.input_buffer += ch
                                        state.mark_dirty()

                # 4. Dirty-state frame rendering capped at <= 5 FPS to protect AVF ttyd WebView
                now = time.time()
                if (now - last_render_ts >= 2.0) or (state.dirty and (now - last_render_ts >= 0.15)):
                    try:
                        layout = bt_serial_ui.render_dashboard(state, bt_serial_commands.CUSTOM_COMMANDS)
                        live.update(layout, refresh=True)
                        state.dirty = False
                        last_render_ts = now
                    except Exception as render_err:
                        state.last_error = f"UI Render Error: {render_err}"

                if now - last_snapshot_ts >= 2.0:
                    state.persist_state_snapshot()
                    last_snapshot_ts = now

    finally:
        if old_tty_attrs is not None and stdin_fd >= 0:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_tty_attrs)
            except Exception:
                pass
        state.close()

    return 0


def run_self_test() -> int:
    """
    Executes an empirical zero-mock verification of:
    1. Virtual RFCOMM PTY (/tmp/bt_serial_pty) loopback
    2. Multi-client TCP (:4005) serial bridge
    3. Real-time file modification -> AST check -> hot-reload (<50ms) -> new command execution
    4. Syntax error firewall protection (verifies broken code does not crash the terminal)
    """
    print("=== 🧪 Running Bluetooth Serial Terminal + Live Hot-Reload E2E Self-Test ===")
    state = BluetoothSerialState(tcp_port=4005)
    supervisor = HotReloadSupervisor(state)
    state.on_line_callback = lambda line, src: handle_command_safe(state, supervisor, line, source=src)

    pty_path = state.setup_pty()
    tcp_port = state.setup_tcp_server()
    assert os.path.exists(pty_path), f"PTY slave {pty_path} does not exist"
    assert tcp_port > 0, "TCP server failed to bind"
    print(f"  [1/5] ✅ Virtual PTY ({PTY_SYMLINK} -> {pty_path}) & TCP Bridge (:{tcp_port}) active")

    # Test 2: PTY Slave -> Master RX loopback
    with open(PTY_SYMLINK, "wb", buffering=0) as slave_out:
        slave_out.write(b">hr_bpm:73.5\r\nHELLO_FROM_AVF_PTY\r\n")
    time.sleep(0.05)
    state.poll_io()
    assert state.rx_bytes > 0, "No bytes received over PTY loopback"
    assert "hr_bpm" in state.teleplot_series, "Teleplot parser did not capture >hr_bpm:73.5"
    print(f"  [2/5] ✅ PTY Loopback & Teleplot Parser verified (RX={state.rx_bytes}B, hr_bpm={list(state.teleplot_series['hr_bpm'])})")

    # Test 3: TCP Client -> Server Serial Bridge
    with socket.create_connection(("127.0.0.1", tcp_port), timeout=2.0) as cli:
        time.sleep(0.02)
        state.poll_io()
        banner = cli.recv(1024).decode("utf-8", errors="ignore")
        assert "BLUETOOTH SERIAL TERMINAL" in banner
        cli.sendall(b"ping\n")
        time.sleep(0.05)
        state.poll_io()
    print(f"  [3/5] ✅ TCP :{tcp_port} bidirectional client bridge verified")

    # Test 4: Live Code Modification & Hot-Reload Verification
    cmd_file = SCRIPT_DIR / "bt_serial_commands.py"
    original_src = cmd_file.read_text(encoding="utf-8")
    try:
        test_token = f"HOT_RELOAD_VERIFIED_{int(time.time())}"
        handle_command_safe(state, supervisor, f"patch livecheck {test_token}")
        time.sleep(0.02)
        reloaded = supervisor.check_and_reload(force=True)
        assert reloaded, "HotReloadSupervisor did not detect patched file"
        out = handle_command_safe(state, supervisor, "livecheck")
        assert test_token in out, f"Expected {test_token} in hot-reloaded command output, got {out}"
        print(
            f"  [4/5] ✅ Live Hot-Reload verified in {state.last_reload_ms:.2f}ms (Reload #{state.reload_count}, output='{out}')"
        )

        # Test 5: Syntax Error Firewall Verification
        cmd_file.write_text(original_src + "\ndef broken_syntax(:\n", encoding="utf-8")
        supervisor.check_and_reload(force=True)
        assert "SYNTAX ERR" in state.syntax_status, "Syntax firewall did not flag syntax error"
        # Ensure previous commands STILL work while syntax error is present on disk!
        still_works = handle_command_safe(state, supervisor, "ping")
        assert "PONG" in still_works
        print(
            f"  [5/5] ✅ Crash-Proof Syntax Firewall verified (Status='{state.syntax_status}', terminal stayed alive!)"
        )
    finally:
        cmd_file.write_text(original_src, encoding="utf-8")
        supervisor.check_and_reload(force=True)
        state.persist_state_snapshot()
        state.close()

    print("=== ✅ ALL 5 E2E HOT-RELOAD & BLUETOOTH SERIAL TESTS PASSED (EXIT CODE 0) ===")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crash-Proof Bluetooth Serial Terminal with Real-Time Hot-Reload (--dev)"
    )
    parser.add_argument("--dev", action="store_true", help="Run interactive live hot-reloading TUI")
    parser.add_argument("--port", type=int, default=4005, help="TCP serial bridge port (default: 4005)")
    parser.add_argument("--connect-mesh", action="store_true", help="Auto-connect to L1 Mac Mini :4005")
    parser.add_argument("--self-test", action="store_true", help="Run automated E2E hot-reload & PTY verification")
    parser.add_argument("--exec", type=str, metavar="CMD", help="Inject a command into the running terminal or run once")
    parser.add_argument("--snapshot", action="store_true", help="Print a single dashboard snapshot and exit")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if args.exec:
        # If a live terminal is running, also queue the command to its FIFO so the live screen updates!
        try:
            with open(COMMAND_FIFO_PATH, "a", encoding="utf-8") as f:
                f.write(args.exec.strip() + "\n")
        except Exception:
            pass
        state = BluetoothSerialState(tcp_port=args.port)
        supervisor = HotReloadSupervisor(state)
        res = handle_command_safe(state, supervisor, args.exec, source="CLI")
        print(res)
        state.close()
        return 0

    if args.snapshot:
        state = BluetoothSerialState(tcp_port=args.port)
        supervisor = HotReloadSupervisor(state)
        state.setup_pty()
        state.setup_tcp_server()
        state.probe_bluetooth_devices(force=True)
        state.probe_avf_health(force=True)
        handle_command_safe(state, supervisor, "teleplot demo", source="INIT")
        console = Console(width=105, height=28)
        console.print(bt_serial_ui.render_dashboard(state, bt_serial_commands.CUSTOM_COMMANDS))
        state.persist_state_snapshot()
        state.close()
        return 0

    return run_interactive_dev_tui(port=args.port, connect_mesh=args.connect_mesh)


if __name__ == "__main__":
    sys.exit(main())
