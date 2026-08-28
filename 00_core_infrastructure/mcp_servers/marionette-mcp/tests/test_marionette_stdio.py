#!/usr/bin/env python3
"""
Python verification script testing marionette-mcp stdio server.
Verifies JSON-RPC 2.0 handshake, 29 tools listed, page navigation,
accessibility snapshot, and valid base64 screenshot generation.
"""

import json
import subprocess
import os
import sys
import base64

def main():
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(server_dir, "dist", "src", "index.js")

    if not os.path.exists(server_script):
        print(f"Error: Server script not found at {server_script}. Build TypeScript first.")
        sys.exit(1)

    print(f"Spawning marionette-mcp server: node {server_script}")
    proc = subprocess.Popen(
        ["node", server_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    def send_rpc(method, params=None, req_id=1):
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        raw = json.dumps(payload) + "\n"
        proc.stdin.write(raw)
        proc.stdin.flush()

        while True:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("Subprocess stdout closed unexpectedly")
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("id") == req_id:
                    return data
            except json.JSONDecodeError:
                # ignore non-JSON log lines
                continue

    try:
        # 1. Initialize Handshake
        print("[1/5] Testing MCP initialize handshake...")
        init_res = send_rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "python-e2e-test", "version": "1.0.0"}
        }, req_id=1)
        assert init_res["result"]["serverInfo"]["name"] == "marionette-mcp"
        print("  -> Passed initialize: server name is 'marionette-mcp'")

        # 2. List tools
        print("[2/5] Testing tools/list...")
        list_res = send_rpc("tools/list", {}, req_id=2)
        tools = list_res["result"]["tools"]
        assert len(tools) == 29, f"Expected 29 tools, got {len(tools)}"
        tool_names = [t["name"] for t in tools]
        print(f"  -> Passed tools/list: verified {len(tools)} tools registered ({', '.join(tool_names[:5])}...)")

        # 3. Navigate page
        print("[3/5] Testing tools/call navigate_page...")
        nav_res = send_rpc("tools/call", {
            "name": "navigate_page",
            "arguments": {"pageId": 1, "url": "http://localhost:3000"}
        }, req_id=3)
        assert "Navigated page 1" in nav_res["result"]["content"][0]["text"]
        print("  -> Passed navigate_page")

        # 4. Take AX snapshot
        print("[4/5] Testing tools/call take_snapshot...")
        snap_res = send_rpc("tools/call", {
            "name": "take_snapshot",
            "arguments": {"pageId": 1}
        }, req_id=4)
        snap_text = snap_res["result"]["content"][0]["text"]
        assert "RootWebArea" in snap_text
        assert "[uid=" in snap_text
        print("  -> Passed take_snapshot: verified RootWebArea and UID markers")

        # 5. Take screenshot
        print("[5/5] Testing tools/call take_screenshot...")
        shot_res = send_rpc("tools/call", {
            "name": "take_screenshot",
            "arguments": {"pageId": 1, "format": "png"}
        }, req_id=5)
        content = shot_res["result"]["content"][0]
        assert content["type"] == "image"
        assert content["mimeType"] == "image/png"
        b64_data = content["data"]
        raw_bytes = base64.b64decode(b64_data)
        # Verify PNG 8-byte magic header: \x89PNG\r\n\x1a\n
        assert raw_bytes[:8] == b"\x89PNG\r\n\x1a\n", "Invalid PNG magic signature"
        print(f"  -> Passed take_screenshot: valid PNG image ({len(raw_bytes)} bytes)")

        print("\n=== ALL MARIONETTE MCP INTEGRATION TESTS PASSED CLEANLY! ===")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    main()
