#!/usr/bin/env python3
"""
Shizuku Termux MCP Server
=========================
A zero-dependency Python MCP (Model Context Protocol) & REST/WebSocket server
running natively in Android Termux on Port 8089.

Features:
- Privileged ADB-level system execution via Shizuku's `rish` binary (UID 2000 / UID 0).
- Android 15 W^X Safety: Automatically checks and enforces `chmod 400` on `rish_shizuku.dex`.
- REST API endpoints for execution, gestures, input injection, and telemetry.
- WebSocket endpoint (`/ws`) for high-speed streaming gestures and continuous screen monitoring.
- MCP 2024-11-05 Server-Sent Events (SSE) protocol (`/sse` & `/messages`) exposing standard tools.
- Sovereign Authentication support via `X-Lauburu-Sovereign-Key`.
"""

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

SERVER_NAME = "shizuku-termux-mcp"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"
DEFAULT_PORT = 8089
DEFAULT_HOST = "0.0.0.0"


class WXDexSafety:
    """Manages Android 14/15 W^X memory safety rules for rish_shizuku.dex."""

    @staticmethod
    def enforce_dex_safety(dex_path: Optional[str]) -> Tuple[bool, str, Optional[int]]:
        """
        Ensures rish_shizuku.dex is read-only (chmod 400 or 444).
        Returns: (is_safe, message, current_mode)
        """
        if not dex_path or not os.path.exists(dex_path):
            return False, f"Dex file not found at: {dex_path}", None

        try:
            st = os.stat(dex_path)
            current_mode = stat.S_IMODE(st.st_mode)
            # Check if writable by anyone
            is_writable = bool(current_mode & 0o222)

            if is_writable:
                # Android 15 W^X safety violation: enforce read-only
                os.chmod(dex_path, 0o400)
                new_mode = stat.S_IMODE(os.stat(dex_path).st_mode)
                return True, f"Enforced W^X safety: chmod 400 applied (was {oct(current_mode)})", new_mode
            else:
                return True, f"Dex file is already W^X safe (mode: {oct(current_mode)})", current_mode
        except Exception as e:
            return False, f"Error inspecting/modifying dex permissions: {e}", None


class ShizukuExecutor:
    """Discovers and invokes Shizuku's rish shell binary."""

    def __init__(self, rish_path: Optional[str] = None, dex_path: Optional[str] = None):
        self.rish_path = rish_path or self._find_rish()
        self.dex_path = dex_path or self._find_dex()
        self.wx_safe = False
        self.wx_message = ""
        self.dex_mode = None
        self._check_dex_safety()

    def _find_rish(self) -> Optional[str]:
        candidates = [
            os.environ.get("RISH_PATH"),
            os.path.expanduser("~/../usr/bin/rish"),  # Termux $PREFIX/bin/rish
            "/data/data/com.termux/files/usr/bin/rish",
            "/data/local/tmp/rish",
            shutil.which("rish"),
        ]
        for path in candidates:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return os.path.abspath(path)
        return None

    def _find_dex(self) -> Optional[str]:
        if self.rish_path:
            dir_name = os.path.dirname(self.rish_path)
            dex_candidate = os.path.join(dir_name, "rish_shizuku.dex")
            if os.path.exists(dex_candidate):
                return dex_candidate

        candidates = [
            os.environ.get("RISH_DEX_PATH"),
            os.path.expanduser("~/../usr/bin/rish_shizuku.dex"),
            "/data/data/com.termux/files/usr/bin/rish_shizuku.dex",
            "/data/local/tmp/rish_shizuku.dex",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return os.path.abspath(path)
        return None

    def _check_dex_safety(self):
        if self.dex_path and os.path.exists(self.dex_path):
            self.wx_safe, self.wx_message, self.dex_mode = WXDexSafety.enforce_dex_safety(self.dex_path)
        else:
            self.wx_safe = True
            self.wx_message = "No dex file located locally; safety check deferred."

    def is_available(self) -> bool:
        return self.rish_path is not None and os.access(self.rish_path, os.X_OK)

    def execute(self, command: str, timeout_sec: int = 10) -> Dict[str, Any]:
        """Executes a command via rish or local shell fallback."""
        start_time = time.time()
        if not self.is_available():
            # Fallback to local system sh if rish is not installed (e.g. testing or host mode)
            cmd = ["sh", "-c", command]
            used_rish = False
        else:
            cmd = [self.rish_path, "-c", command]
            used_rish = True

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_sec,
                text=True,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration_ms": duration_ms,
                "used_rish": used_rish,
                "timestamp": time.time(),
            }
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": -4,
                "stdout": "",
                "stderr": f"Command timed out after {timeout_sec}s",
                "duration_ms": duration_ms,
                "used_rish": used_rish,
                "timestamp": time.time(),
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": -3,
                "stdout": "",
                "stderr": str(e),
                "duration_ms": duration_ms,
                "used_rish": used_rish,
                "timestamp": time.time(),
            }

    def get_status(self) -> Dict[str, Any]:
        available = self.is_available()
        uid = None
        permission_granted = False
        if available:
            res = self.execute("id", timeout_sec=3)
            if res["exit_code"] == 0:
                match = re.search(r"uid=(\d+)", res["stdout"])
                if match:
                    uid = int(match.group(1))
                    permission_granted = uid in (0, 2000)

        return {
            "status": "ok" if available else "waiting_for_shizuku",
            "available": available,
            "rish_path": self.rish_path,
            "dex_path": self.dex_path,
            "dex_mode": oct(self.dex_mode) if self.dex_mode is not None else None,
            "wx_safe": self.wx_safe,
            "wx_message": self.wx_message,
            "uid": uid,
            "permission_granted": permission_granted,
            "is_android": os.path.exists("/system/build.prop") or bool(os.environ.get("ANDROID_ROOT")),
            "uptime_sec": time.time() - SERVER_START_TIME,
        }


# MCP Tool Definitions (Model Context Protocol 2024-11-05 standard)
MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "shizuku_exec",
        "description": "Execute an arbitrary shell command with privileged Shizuku / ADB shell permissions (UID 2000/0).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute."},
                "timeout_sec": {"type": "integer", "description": "Execution timeout in seconds (default 10).", "default": 10},
            },
            "required": ["command"],
        },
    },
    {
        "name": "shizuku_tap",
        "description": "Inject a touch tap event at coordinates (x, y) on the Android screen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate in pixels."},
                "y": {"type": "integer", "description": "Y coordinate in pixels."},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "shizuku_swipe",
        "description": "Inject a swipe/drag gesture on the screen from (x1, y1) to (x2, y2).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x1": {"type": "integer"},
                "y1": {"type": "integer"},
                "x2": {"type": "integer"},
                "y2": {"type": "integer"},
                "duration_ms": {"type": "integer", "default": 300},
            },
            "required": ["x1", "y1", "x2", "y2"],
        },
    },
    {
        "name": "shizuku_key",
        "description": "Inject an Android keyevent (e.g. 3=Home, 4=Back, 24=VolUp, 25=VolDown, 26=Power).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keycode": {"type": "integer", "description": "Android KeyEvent code."},
            },
            "required": ["keycode"],
        },
    },
    {
        "name": "shizuku_text",
        "description": "Type text into the currently focused input field.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "shizuku_screencap",
        "description": "Capture the current Android screen as base64-encoded PNG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["base64", "png"], "default": "base64"},
            },
        },
    },
    {
        "name": "shizuku_active_app",
        "description": "Query the currently active/focused foreground Android package and activity.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "shizuku_pm_grant",
        "description": "Grant a runtime permission to an installed package without user prompting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "Package name (e.g. com.example.lauburu_life_companion)."},
                "permission": {"type": "string", "description": "Permission name (e.g. android.permission.POST_NOTIFICATIONS)."},
            },
            "required": ["package", "permission"],
        },
    },
    {
        "name": "shizuku_battery_info",
        "description": "Retrieve physical battery level, temperature, voltage, and charging status via dumpsys battery.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "shizuku_telemetry",
        "description": "Query live Android system telemetry (RAM, CPU load, thermals, uptime).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

SERVER_START_TIME = time.time()


class TermuxShizukuServer:
    """Pure-Python asyncio HTTP, WebSocket, and MCP SSE server."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, auth_key: Optional[str] = None, executor: Optional[ShizukuExecutor] = None):
        self.host = host
        self.port = port
        self.auth_key = auth_key
        self.executor = executor or ShizukuExecutor()
        self.sessions: Dict[str, asyncio.Queue] = {}
        self.active_writers: set = set()
        self.server: Optional[asyncio.AbstractServer] = None

    def _is_authorized(self, headers: Dict[str, str], query: Dict[str, List[str]]) -> bool:
        if not self.auth_key:
            return True
        key = headers.get("x-lauburu-sovereign-key") or query.get("key", [None])[0]
        return key == self.auth_key

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.active_writers.add(writer)
        try:
            line = await reader.readline()
            if not line:
                try:
                    if not writer.is_closing():
                        writer.close()
                except Exception:
                    pass
                return

            request_line = line.decode("utf-8", errors="ignore").strip()
            parts = request_line.split()
            if len(parts) < 2:
                writer.close()
                await writer.wait_closed()
                return

            method, raw_path = parts[0], parts[1]
            parsed_url = urllib.parse.urlparse(raw_path)
            path = parsed_url.path
            query = urllib.parse.parse_qs(parsed_url.query)

            headers = {}
            while True:
                hdr_line = await reader.readline()
                if not hdr_line or hdr_line == b"\r\n" or hdr_line == b"\n":
                    break
                hdr_text = hdr_line.decode("utf-8", errors="ignore").strip()
                if ":" in hdr_text:
                    k, v = hdr_text.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            content_length = int(headers.get("content-length", 0))
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            # Check WebSocket Upgrade
            if headers.get("upgrade", "").lower() == "websocket" and path == "/ws":
                await self.handle_websocket(reader, writer, headers)
                return

            # Check Authorization (skip for /health)
            if path != "/health" and not self._is_authorized(headers, query):
                await self.send_json(writer, 401, {"error": "Unauthorized", "message": "Invalid or missing X-Lauburu-Sovereign-Key"})
                return

            # Route HTTP Requests
            if method == "GET" and path == "/health":
                await self.send_json(writer, 200, {
                    "status": "healthy",
                    "available": self.executor.is_available(),
                    "service": SERVER_NAME,
                    "version": SERVER_VERSION,
                    "timestamp": time.time(),
                })
            elif method == "GET" and path == "/api/shizuku/status":
                status = self.executor.get_status()
                await self.send_json(writer, 200, status)
            elif method == "POST" and path == "/api/shizuku/exec":
                data = json.loads(body.decode("utf-8") or "{}")
                cmd = data.get("command", "")
                timeout = int(data.get("timeout_sec", 10))
                res = self.executor.execute(cmd, timeout_sec=timeout)
                await self.send_json(writer, 200, res)
            elif method == "POST" and path == "/api/shizuku/tap":
                data = json.loads(body.decode("utf-8") or "{}")
                x, y = int(int(data.get("x", 0)) * 0.1), int(int(data.get("y", 0)) * 0.1)
                res = self.executor.execute(f"input tap {x} {y}")
                await self.send_json(writer, 200, {"status": "ok" if res["exit_code"] == 0 else "error", "result": res})
            elif method == "POST" and path == "/api/shizuku/swipe":
                data = json.loads(body.decode("utf-8") or "{}")
                x1, y1 = int(int(data.get("x1", 0)) * 0.1), int(int(data.get("y1", 0)) * 0.1)
                x2, y2 = int(int(data.get("x2", 0)) * 0.1), int(int(data.get("y2", 0)) * 0.1)
                dur = int(data.get("duration_ms", 300))
                res = self.executor.execute(f"input swipe {x1} {y1} {x2} {y2} {dur}")
                await self.send_json(writer, 200, {"status": "ok" if res["exit_code"] == 0 else "error", "result": res})
            elif method == "POST" and path == "/api/shizuku/key":
                data = json.loads(body.decode("utf-8") or "{}")
                keycode = int(data.get("keycode", 3))
                res = self.executor.execute(f"input keyevent {keycode}")
                await self.send_json(writer, 200, {"status": "ok" if res["exit_code"] == 0 else "error", "result": res})
            elif method == "POST" and path == "/api/shizuku/text":
                data = json.loads(body.decode("utf-8") or "{}")
                text = data.get("text", "").replace("'", "'\\''")
                res = self.executor.execute(f"input text '{text}'")
                await self.send_json(writer, 200, {"status": "ok" if res["exit_code"] == 0 else "error", "result": res})
            elif method == "GET" and path == "/api/shizuku/screencap":
                fmt = query.get("format", ["base64"])[0]
                res = self.executor.execute("screencap -p | base64", timeout_sec=10)
                if res["exit_code"] == 0:
                    clean_b64 = res["stdout"].replace("\n", "").replace("\r", "").strip()
                    if fmt == "png":
                        png_bytes = base64.b64decode(clean_b64)
                        header = (
                            "HTTP/1.1 200 OK\r\n"
                            "Content-Type: image/png\r\n"
                            f"Content-Length: {len(png_bytes)}\r\n"
                            "Access-Control-Allow-Origin: *\r\n\r\n"
                        )
                        writer.write(header.encode("utf-8") + png_bytes)
                        await writer.drain()
                    else:
                        await self.send_json(writer, 200, {
                            "status": "ok",
                            "format": "png",
                            "image_base64": clean_b64,
                            "timestamp": time.time(),
                        })
                else:
                    await self.send_json(writer, 500, {"status": "error", "error": res["stderr"]})
            elif method == "GET" and path == "/api/shizuku/battery":
                res = self.executor.execute("dumpsys battery", timeout_sec=5)
                data = {"status": "ok" if res["exit_code"] == 0 else "error"}
                for line in res["stdout"].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k_strip = k.strip()
                        v_strip = v.strip()
                        if v_strip.isdigit():
                            val = int(v_strip)
                            if k_strip == "temperature":
                                val = val / 10.0
                            data[k_strip] = val
                        else:
                            data[k_strip] = v_strip
                await self.send_json(writer, 200, data)
            elif method == "GET" and path == "/api/shizuku/telemetry":
                mem = self.executor.execute("cat /proc/meminfo", timeout_sec=3)
                uptime = self.executor.execute("uptime", timeout_sec=3)
                await self.send_json(writer, 200, {
                    "status": "ok",
                    "uptime": uptime["stdout"].strip(),
                    "meminfo_snippet": mem["stdout"][:256],
                    "timestamp": time.time(),
                })
            # MCP Protocol SSE Handling
            elif method == "GET" and path == "/sse":
                await self.handle_mcp_sse(reader, writer)
                return
            elif method == "POST" and path == "/messages":
                session_id = query.get("sessionId", [""])[0]
                await self.handle_mcp_message(writer, session_id, body)
            else:
                await self.send_json(writer, 404, {"error": "Not Found", "path": path})

        except (asyncio.CancelledError, GeneratorExit):
            pass
        except Exception as e:
            try:
                if not writer.is_closing():
                    await self.send_json(writer, 500, {"error": "Internal Server Error", "message": str(e)})
            except Exception:
                pass
        finally:
            self.active_writers.discard(writer)
            # For persistent SSE connections, writer is kept open in handle_mcp_sse
            try:
                if not writer.is_closing():
                    writer.close()
            except Exception:
                pass

    async def send_json(self, writer: asyncio.StreamWriter, status: int, data: Any):
        payload = json.dumps(data).encode("utf-8")
        status_text = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 404: "Not Found", 500: "Internal Server Error"}.get(status, "OK")
        resp = (
            f"HTTP/1.1 {status} {status_text}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Headers: *\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8") + payload
        writer.write(resp)
        await writer.drain()

    # --- WebSocket Handling (RFC 6455 Pure-Python Implementation) ---
    async def handle_websocket(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, headers: Dict[str, str]):
        ws_key = headers.get("sec-websocket-key")
        if not ws_key:
            writer.close()
            await writer.wait_closed()
            return

        guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_token = base64.b64encode(hashlib.sha1((ws_key + guid).encode("utf-8")).digest()).decode("utf-8")

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_token}\r\n\r\n"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()

        # Send greeting frame
        await self._ws_send_text(writer, json.dumps({"type": "connected", "server": SERVER_NAME, "version": SERVER_VERSION}))

        try:
            while True:
                msg = await self._ws_read_message(reader)
                if msg is None:
                    break
                # Process message
                try:
                    req = json.loads(msg)
                    action = req.get("action", "")
                    if action == "exec":
                        cmd = req.get("command", "")
                        res = self.executor.execute(cmd, timeout_sec=int(req.get("timeout_sec", 10)))
                        await self._ws_send_text(writer, json.dumps({"action": "exec_result", "result": res}))
                    elif action == "tap":
                        x, y = int(int(req.get("x", 0)) * 0.1), int(int(req.get("y", 0)) * 0.1)
                        res = self.executor.execute(f"input tap {x} {y}")
                        await self._ws_send_text(writer, json.dumps({"action": "tap_result", "success": res["exit_code"] == 0}))
                    elif action == "ping":
                        await self._ws_send_text(writer, json.dumps({"action": "pong", "timestamp": time.time()}))
                    else:
                        await self._ws_send_text(writer, json.dumps({"action": "unknown", "raw": req}))
                except Exception as ex:
                    await self._ws_send_text(writer, json.dumps({"error": str(ex)}))
        except Exception:
            pass
        finally:
            try:
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
            except (asyncio.CancelledError, GeneratorExit, Exception):
                pass

    async def _ws_read_message(self, reader: asyncio.StreamReader) -> Optional[str]:
        hdr = await reader.read(2)
        if len(hdr) < 2:
            return None
        b1, b2 = hdr[0], hdr[1]
        opcode = b1 & 0x0F
        if opcode == 0x8:  # Close
            return None

        masked = bool(b2 & 0x80)
        payload_len = b2 & 0x7F
        if payload_len == 126:
            ext = await reader.read(2)
            payload_len = struct.unpack("!H", ext)[0]
        elif payload_len == 127:
            ext = await reader.read(8)
            payload_len = struct.unpack("!Q", ext)[0]

        mask = b""
        if masked:
            mask = await reader.read(4)

        data = await reader.readexactly(payload_len)
        if masked:
            unmasked = bytearray(len(data))
            for i in range(len(data)):
                unmasked[i] = data[i] ^ mask[i % 4]
            return unmasked.decode("utf-8", errors="ignore")
        return data.decode("utf-8", errors="ignore")

    async def _ws_send_text(self, writer: asyncio.StreamWriter, text: str):
        payload = text.encode("utf-8")
        length = len(payload)
        header = bytearray([0x81])  # FIN + Text
        if length <= 125:
            header.append(length)
        elif length <= 65535:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))

        writer.write(bytes(header) + payload)
        await writer.drain()

    # --- MCP 2024-11-05 Protocol (SSE & JSON-RPC) ---
    async def handle_mcp_sse(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        session_id = hashlib.sha256(f"{time.time()}:{os.urandom(16)}".encode("utf-8")).hexdigest()[:16]
        queue: asyncio.Queue = asyncio.Queue()
        self.sessions[session_id] = queue

        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/event-stream\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: keep-alive\r\n"
            "Access-Control-Allow-Origin: *\r\n\r\n"
        )
        writer.write(header.encode("utf-8"))
        await writer.drain()

        # Send initial endpoint event specifying message POST URL
        endpoint_event = f"event: endpoint\ndata: /messages?sessionId={session_id}\n\n"
        writer.write(endpoint_event.encode("utf-8"))
        await writer.drain()

        try:
            while True:
                data = await queue.get()
                if data is None:
                    break
                msg_event = f"event: message\ndata: {json.dumps(data)}\n\n"
                writer.write(msg_event.encode("utf-8"))
                await writer.drain()
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self.sessions.pop(session_id, None)
            try:
                if not writer.is_closing():
                    writer.close()
            except Exception:
                pass

    async def handle_mcp_message(self, writer: asyncio.StreamWriter, session_id: str, body: bytes):
        if session_id not in self.sessions:
            await self.send_json(writer, 404, {"error": "Invalid or expired sessionId"})
            return

        try:
            req = json.loads(body.decode("utf-8"))
        except Exception:
            await self.send_json(writer, 400, {"error": "Invalid JSON-RPC payload"})
            return

        method = req.get("method")
        msg_id = req.get("id")
        params = req.get("params", {})

        response_payload: Optional[Dict[str, Any]] = None

        if method == "initialize":
            response_payload = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": True},
                    },
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                },
            }
        elif method == "notifications/initialized":
            # No-op acknowledgement for MCP protocol
            response_payload = None
        elif method == "tools/list":
            response_payload = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": MCP_TOOLS,
                },
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            call_res = await self._execute_mcp_tool(tool_name, tool_args)
            response_payload = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(call_res, indent=2)}],
                    "isError": call_res.get("exit_code", 0) != 0 if isinstance(call_res, dict) else False,
                },
            }
        elif method == "ping":
            response_payload = {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        else:
            response_payload = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        # Return 202 Accepted via HTTP POST response
        await self.send_json(writer, 202, {"status": "accepted"})

        # Forward response through SSE stream
        if response_payload is not None and session_id in self.sessions:
            await self.sessions[session_id].put(response_payload)

    async def _execute_mcp_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "shizuku_exec":
            cmd = args.get("command", "")
            timeout = int(args.get("timeout_sec", 10))
            return self.executor.execute(cmd, timeout_sec=timeout)
        elif tool_name == "shizuku_tap":
            x, y = int(int(args.get("x", 0)) * 0.1), int(int(args.get("y", 0)) * 0.1)
            return self.executor.execute(f"input tap {x} {y}")
        elif tool_name == "shizuku_swipe":
            x1, y1 = int(int(args.get("x1", 0)) * 0.1), int(int(args.get("y1", 0)) * 0.1)
            x2, y2 = int(int(args.get("x2", 0)) * 0.1), int(int(args.get("y2", 0)) * 0.1)
            dur = int(args.get("duration_ms", 300))
            return self.executor.execute(f"input swipe {x1} {y1} {x2} {y2} {dur}")
        elif tool_name == "shizuku_key":
            keycode = int(args.get("keycode", 3))
            return self.executor.execute(f"input keyevent {keycode}")
        elif tool_name == "shizuku_text":
            text = args.get("text", "").replace("'", "'\\''")
            return self.executor.execute(f"input text '{text}'")
        elif tool_name == "shizuku_screencap":
            res = self.executor.execute("screencap -p | base64", timeout_sec=10)
            if res["exit_code"] == 0:
                return {"status": "ok", "format": "png_base64", "image_base64": res["stdout"].replace("\n", "").strip()}
            return {"status": "error", "error": res["stderr"]}
        elif tool_name == "shizuku_active_app":
            res = self.executor.execute("dumpsys window displays | grep -E 'mCurrentFocus|mFocusedApp'")
            return {"active_app": res["stdout"].strip(), "exit_code": res["exit_code"]}
        elif tool_name == "shizuku_pm_grant":
            pkg = args.get("package", "")
            perm = args.get("permission", "")
            return self.executor.execute(f"pm grant {pkg} {perm}")
        elif tool_name == "shizuku_battery_info":
            res = self.executor.execute("dumpsys battery")
            parsed = {}
            for line in res["stdout"].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k_strip = k.strip()
                    v_strip = v.strip()
                    if v_strip.isdigit():
                        val = int(v_strip)
                        if k_strip == "temperature":
                            val = val / 10.0
                        parsed[k_strip] = val
                    else:
                        parsed[k_strip] = v_strip
            return parsed
        elif tool_name == "shizuku_telemetry":
            return self.executor.get_status()
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
        print(f"[{SERVER_NAME}] Server running on {addrs}")

    async def stop(self):
        if self.server:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception:
                pass
        for q in list(self.sessions.values()):
            try:
                await q.put(None)
            except Exception:
                pass
        for w in list(self.active_writers):
            try:
                if not w.is_closing():
                    w.close()
            except Exception:
                pass
        self.active_writers.clear()


def main():
    parser = argparse.ArgumentParser(description="Termux Shizuku Python MCP & REST/WebSocket Server")
    parser.add_argument("--host", default=os.environ.get("SHIZUKU_HOST", DEFAULT_HOST), help="Host interface (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SHIZUKU_PORT", DEFAULT_PORT)), help="Port (default 8089)")
    parser.add_argument("--auth-key", default=os.environ.get("SHIZUKU_AUTH_KEY"), help="Optional Sovereign Key for authentication")
    parser.add_argument("--rish-path", default=os.environ.get("RISH_PATH"), help="Path to rish binary")
    parser.add_argument("--dex-path", default=os.environ.get("RISH_DEX_PATH"), help="Path to rish_shizuku.dex")
    args = parser.parse_args()

    executor = ShizukuExecutor(rish_path=args.rish_path, dex_path=args.dex_path)
    status = executor.get_status()
    print(f"[{SERVER_NAME}] Shizuku Executor initialized: {json.dumps(status, indent=2)}")

    server = TermuxShizukuServer(host=args.host, port=args.port, auth_key=args.auth_key, executor=executor)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(server.start())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nStopping Shizuku MCP server...")
        loop.run_until_complete(server.stop())


if __name__ == "__main__":
    main()
