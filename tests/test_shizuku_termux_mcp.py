"""
Test Suite: Shizuku Termux MCP Server & Remote Companion Client
==============================================================
Validates:
- Android 15 W^X chmod 400 dex safety enforcement.
- Privileged Shizuku execution wrapper with fallback and timeout handling.
- REST API endpoints (/health, /api/shizuku/status, /api/shizuku/exec, etc.).
- MCP 2024-11-05 SSE protocol and JSON-RPC tool calling.
- Pure Python WebSocket frame processing (/ws).
- Sovereign authentication via X-Lauburu-Sovereign-Key.
- ShizukuRemoteClient cross-device actuation.
"""

import asyncio
import base64
import hashlib
import json
import os
import shutil
import stat
import struct
import sys
import tempfile
import threading
import time
import urllib.request
import pytest

# Ensure monorepo root and script dirs are on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "01_apps", "screen_lens", "android"))

from shizuku_termux_mcp_server import (
    WXDexSafety,
    ShizukuExecutor,
    TermuxShizukuServer,
    MCP_TOOLS,
    SERVER_NAME,
    SERVER_VERSION,
    PROTOCOL_VERSION,
)
from shizuku_remote_client import ShizukuRemoteClient


class TestWXDexSafety:
    """Verifies Android 14/15 W^X memory execution safety rules."""

    def test_enforce_dex_safety_on_writable_file(self):
        with tempfile.NamedTemporaryFile(suffix=".dex", delete=False) as f:
            dex_path = f.name
            f.write(b"DEX_TEST_CONTENT")

        try:
            # Set initially writable (e.g. 0o644)
            os.chmod(dex_path, 0o644)
            initial_mode = stat.S_IMODE(os.stat(dex_path).st_mode)
            assert initial_mode & 0o222 != 0, "Dex must be writable initially"

            # Enforce safety
            safe, msg, new_mode = WXDexSafety.enforce_dex_safety(dex_path)
            assert safe is True
            assert "chmod 400" in msg
            assert new_mode == 0o400
            assert os.stat(dex_path).st_mode & 0o222 == 0, "Dex must no longer be writable"

            # Re-running on already safe file
            safe2, msg2, mode2 = WXDexSafety.enforce_dex_safety(dex_path)
            assert safe2 is True
            assert "already W^X safe" in msg2
            assert mode2 == 0o400
        finally:
            if os.path.exists(dex_path):
                os.chmod(dex_path, 0o600)  # restore so it can be unlinked
                os.unlink(dex_path)

    def test_nonexistent_dex_path(self):
        safe, msg, mode = WXDexSafety.enforce_dex_safety("/nonexistent/path/rish_shizuku.dex")
        assert safe is False
        assert "not found" in msg.lower()
        assert mode is None


class TestShizukuExecutor:
    """Verifies Shizuku command execution and status detection."""

    def test_execute_local_shell_fallback(self):
        executor = ShizukuExecutor()
        res = executor.execute("echo 'Hello Lauburu Shizuku'")
        assert res["exit_code"] == 0
        assert "Hello Lauburu Shizuku" in res["stdout"]
        assert res["duration_ms"] >= 0

    def test_execute_timeout_handling(self):
        executor = ShizukuExecutor()
        res = executor.execute("sleep 5", timeout_sec=1)
        assert res["exit_code"] == -4
        assert "timed out" in res["stderr"]

    def test_get_status_structure(self):
        executor = ShizukuExecutor()
        st = executor.get_status()
        assert "status" in st
        assert "available" in st
        assert "wx_safe" in st
        assert "uptime_sec" in st


@pytest.fixture(scope="module")
def server_instance():
    # Find free port
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    auth_key = "test_sovereign_key_42"
    server = TermuxShizukuServer(host="127.0.0.1", port=port, auth_key=auth_key)

    loop = asyncio.new_event_loop()
    stop_event = threading.Event()

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.start())
        stop_event.set()
        loop.run_forever()
        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
    stop_event.wait(timeout=5)
    time.sleep(0.1)

    yield {"host": "127.0.0.1", "port": port, "auth_key": auth_key, "server": server}

    # Teardown
    async def cleanup():
        await server.stop()
        curr = asyncio.current_task()
        pending = [task for task in asyncio.all_tasks(loop) if task is not curr and not task.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    future = asyncio.run_coroutine_threadsafe(cleanup(), loop)
    try:
        future.result(timeout=3)
    except Exception:
        pass
    loop.call_soon_threadsafe(loop.stop)
    t.join(timeout=3)


class TestTermuxShizukuServerAndClient:
    """Spawns an in-process asyncio server on an ephemeral port and tests endpoints & client."""

    @pytest.fixture(autouse=True)
    def setup_system_stubs_in_path(self):
        """Ensures 'input' exists in PATH when running tests outside Android."""
        temp_dir = tempfile.mkdtemp()
        input_script = os.path.join(temp_dir, "input")
        with open(input_script, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(input_script, 0o755)

        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{temp_dir}:{old_path}"
        yield
        os.environ["PATH"] = old_path
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_health_endpoint_unauthenticated(self, server_instance):
        url = f"http://127.0.0.1:{server_instance['port']}/health"
        with urllib.request.urlopen(url, timeout=3) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "healthy"
            assert data["service"] == SERVER_NAME

    def test_auth_rejection_without_key(self, server_instance):
        url = f"http://127.0.0.1:{server_instance['port']}/api/shizuku/status"
        try:
            urllib.request.urlopen(url, timeout=3)
            pytest.fail("Expected 401 Unauthorized without auth key")
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_client_status_and_exec(self, server_instance):
        client = ShizukuRemoteClient(
            host=server_instance["host"],
            port=server_instance["port"],
            auth_key=server_instance["auth_key"],
        )

        # Health
        h = client.health()
        assert h.get("status") == "healthy"

        # Status
        st = client.get_status()
        assert st.get("status") in ("ok", "waiting_for_shizuku")
        assert "wx_safe" in st

        # Exec
        res = client.execute("echo 'client_integration_verified'")
        assert res.get("exit_code") == 0
        assert "client_integration_verified" in res.get("stdout")

    def test_client_gestures_and_input(self, server_instance):
        client = ShizukuRemoteClient(
            host=server_instance["host"],
            port=server_instance["port"],
            auth_key=server_instance["auth_key"],
        )

        assert client.tap(200, 400) is True
        assert client.swipe(100, 200, 300, 400, duration_ms=150) is True
        assert client.key(3) is True  # Home key
        assert client.text("lauburu_test_text") is True

    def test_mcp_tools_list_and_call(self, server_instance):
        """Validates MCP 2024-11-05 protocol over SSE and /messages."""
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", server_instance["port"], timeout=5)
        headers = {"Accept": "text/event-stream", "X-Lauburu-Sovereign-Key": server_instance["auth_key"]}
        conn.request("GET", "/sse", headers=headers)
        resp = conn.getresponse()
        assert resp.status == 200

        # Helper to read next SSE event
        def read_event():
            line = resp.readline().decode("utf-8")
            while line in ("\r\n", "\n"):
                line = resp.readline().decode("utf-8")
            ev = line.strip()
            data_line = resp.readline().decode("utf-8").strip()
            raw_data = data_line[6:] if data_line.startswith("data: ") else data_line
            return ev, raw_data

        ev_name, endpoint_path = read_event()
        assert ev_name == "event: endpoint"
        assert "sessionId=" in endpoint_path
        session_id = endpoint_path.split("sessionId=")[1].strip()

        # Send initialize JSON-RPC POST
        init_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": PROTOCOL_VERSION},
        })
        msg_conn = http.client.HTTPConnection("127.0.0.1", server_instance["port"], timeout=5)
        msg_headers = {
            "Content-Type": "application/json",
            "X-Lauburu-Sovereign-Key": server_instance["auth_key"],
        }
        msg_conn.request("POST", f"/messages?sessionId={session_id}", body=init_body, headers=msg_headers)
        post_resp = msg_conn.getresponse()
        assert post_resp.status == 202

        # Read SSE response
        ev_type, raw_json = read_event()
        assert ev_type == "event: message"
        sse_json = json.loads(raw_json)
        assert sse_json["result"]["serverInfo"]["name"] == SERVER_NAME

        # Send tools/list JSON-RPC POST
        list_body = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        msg_conn.request("POST", f"/messages?sessionId={session_id}", body=list_body, headers=msg_headers)
        assert msg_conn.getresponse().status == 202

        ev_type, raw_json = read_event()
        assert ev_type == "event: message"
        tools_resp = json.loads(raw_json)
        tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
        assert "shizuku_exec" in tool_names
        assert "shizuku_tap" in tool_names
        assert "shizuku_swipe" in tool_names
        assert "shizuku_key" in tool_names
        assert "shizuku_screencap" in tool_names
        assert "shizuku_battery_info" in tool_names
        assert "shizuku_telemetry" in tool_names

        # Send tools/call JSON-RPC POST
        call_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "shizuku_exec", "arguments": {"command": "echo 'mcp_tool_success'"}},
        })
        msg_conn.request("POST", f"/messages?sessionId={session_id}", body=call_body, headers=msg_headers)
        assert msg_conn.getresponse().status == 202

        ev_type, raw_json = read_event()
        assert ev_type == "event: message"
        call_resp = json.loads(raw_json)
        text_content = call_resp["result"]["content"][0]["text"]
        assert "mcp_tool_success" in text_content

        conn.close()
        msg_conn.close()

    def test_websocket_ping_pong_and_exec(self, server_instance):
        """Validates RFC 6455 WebSocket framing, handshake, and JSON messages."""
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", server_instance["port"]))

        ws_key = base64.b64encode(os.urandom(16)).decode("utf-8")
        handshake = (
            f"GET /ws HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{server_instance['port']}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"X-Lauburu-Sovereign-Key: {server_instance['auth_key']}\r\n\r\n"
        )
        s.sendall(handshake.encode("utf-8"))

        # Read HTTP handshake response up to header delimiter
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(512)
            if not chunk:
                break
            buf += chunk

        hdr_bytes, remaining = buf.split(b"\r\n\r\n", 1)
        resp_hdr = hdr_bytes.decode("utf-8")
        assert "101 Switching Protocols" in resp_hdr
        assert "Sec-WebSocket-Accept" in resp_hdr

        # Read server greeting frame (unmasked from server)
        while len(remaining) < 2:
            remaining += s.recv(512)
        frame_hdr = remaining[:2]
        remaining = remaining[2:]
        payload_len = frame_hdr[1] & 0x7F
        while len(remaining) < payload_len:
            remaining += s.recv(512)
        greeting = remaining[:payload_len].decode("utf-8")
        remaining = remaining[payload_len:]
        assert "connected" in greeting

        # Send client masked frame with action: ping
        msg = json.dumps({"action": "ping"})
        payload = msg.encode("utf-8")
        mask = os.urandom(4)
        masked_payload = bytearray(len(payload))
        for i in range(len(payload)):
            masked_payload[i] = payload[i] ^ mask[i % 4]

        frame = bytearray([0x81, 0x80 | len(payload)]) + mask + masked_payload
        s.sendall(frame)

        # Read response frame
        f_buf = remaining
        while len(f_buf) < 2:
            f_buf += s.recv(512)
        f_hdr = f_buf[:2]
        f_buf = f_buf[2:]
        f_len = f_hdr[1] & 0x7F
        while len(f_buf) < f_len:
            f_buf += s.recv(512)
        pong_data = f_buf[:f_len].decode("utf-8")
        pong_json = json.loads(pong_data)
        assert pong_json.get("action") == "pong"

        s.close()
