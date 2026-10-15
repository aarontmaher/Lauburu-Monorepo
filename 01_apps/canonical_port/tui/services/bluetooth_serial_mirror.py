"""
Canonical Port TUI - Bluetooth Serial Mirror Service
Subsystem: 01_apps/canonical_port/tui/services/bluetooth_serial_mirror.py
Version: 1.0.0-CANONICAL-MIRROR

Mirrors Canonical TUI ANSI stream to physical Bluetooth links & virtual PTY:
- Target Pipe: /tmp/bluetooth_terminal_stream.ansi
- Virtual PTY: /tmp/bluetooth_terminal_pty
- Enforces strict CRLF (\\r\\n) staircasing prevention for Android Kai Morich terminals
- Enforces <= 128-byte chunk slicing for UART FIFO overrun protection
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

BT_STREAM_PIPE = Path("/tmp/bluetooth_terminal_stream.ansi")
BT_PTY_SYMLINK = Path("/tmp/bluetooth_terminal_pty")
MAX_UART_SLICE_BYTES = 128


class BluetoothSerialMirrorService:
    """Singleton service for streaming TUI ANSI frames over Bluetooth serial transport."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BluetoothSerialMirrorService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.frames_sent = 0
        self.bytes_sent = 0
        self.last_frame_time = 0.0
        self.running = True
        self._initialized = True

    def format_crlf(self, text: str) -> str:
        """Converts raw POSIX \\n to CRLF (\\r\\n) to eliminate mobile staircasing."""
        normalized = text.replace("\r\n", "\n")
        return normalized.replace("\n", "\r\n")

    def mirror_frame(self, frame_text: str, clear_screen: bool = False) -> int:
        """
        Formats and slices an ANSI frame, writing it to /tmp/bluetooth_terminal_stream.ansi
        and /tmp/bluetooth_terminal_pty if available.
        """
        if not frame_text:
            return 0

        header = "\x1b[2J\x1b[H" if clear_screen else ""
        crlf_text = header + self.format_crlf(frame_text)
        raw_bytes = crlf_text.encode("utf-8", errors="replace")
        total_written = 0

        # 1. Write to ANSI stream pipe in UART-friendly slices
        try:
            with open(BT_STREAM_PIPE, "ab") as f:
                for i in range(0, len(raw_bytes), MAX_UART_SLICE_BYTES):
                    chunk = raw_bytes[i:i + MAX_UART_SLICE_BYTES]
                    f.write(chunk)
                    f.flush()
                    total_written += len(chunk)
        except Exception:
            pass

        # 2. Write to PTY if connected
        if BT_PTY_SYMLINK.exists():
            try:
                pty_path = str(BT_PTY_SYMLINK.resolve())
                fd = os.open(pty_path, os.O_WRONLY | os.O_NONBLOCK)
                try:
                    for i in range(0, len(raw_bytes), MAX_UART_SLICE_BYTES):
                        chunk = raw_bytes[i:i + MAX_UART_SLICE_BYTES]
                        os.write(fd, chunk)
                finally:
                    os.close(fd)
            except Exception:
                pass

        self.frames_sent += 1
        self.bytes_sent += total_written
        self.last_frame_time = time.time()
        return total_written

    def get_stats(self) -> Dict[str, Any]:
        return {
            "frames_sent": self.frames_sent,
            "bytes_sent": self.bytes_sent,
            "last_frame_time": self.last_frame_time,
            "pipe_path": str(BT_STREAM_PIPE),
            "pty_path": str(BT_PTY_SYMLINK.resolve()) if BT_PTY_SYMLINK.exists() else "INACTIVE",
            "crlf_enforced": True,
            "max_slice_bytes": MAX_UART_SLICE_BYTES,
        }


bluetooth_serial_mirror = BluetoothSerialMirrorService()
