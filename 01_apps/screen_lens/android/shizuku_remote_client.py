#!/usr/bin/env python3
"""
Shizuku Remote Companion Client Helper
======================================
Python client enabling macOS and iOS companion apps (as well as mesh agents)
to interact with Android nodes (Pixel 10 Pro XL, Samsung S20+) via the
Termux Shizuku Python MCP Server over Tailscale.

Supported protocols:
- High-speed REST API (HTTP POST / GET)
- Model Context Protocol (MCP 2024-11-05 SSE JSON-RPC)
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

DEFAULT_HOST = "100.114.215.68"  # L6 Pixel 10 Pro XL Tailscale IP
DEFAULT_PORT = 8089


class ShizukuRemoteClient:
    """Remote companion client communicating with shizuku_termux_mcp_server.py."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        auth_key: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.auth_key = auth_key or os.environ.get("SHIZUKU_AUTH_KEY")
        self.timeout = timeout
        self.base_url = f"http://{self.host}:{self.port}"

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, Dict[str, Any], bytes]:
        url = f"{self.base_url}{endpoint}"
        if query:
            url += f"?{urllib.parse.urlencode(query)}"

        headers = {"User-Agent": "ShizukuRemoteClient/1.0"}
        if self.auth_key:
            headers["X-Lauburu-Sovereign-Key"] = self.auth_key

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        req_timeout = timeout if timeout is not None else self.timeout

        try:
            with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                resp_bytes = resp.read()
                status_code = resp.status
                try:
                    resp_json = json.loads(resp_bytes.decode("utf-8"))
                except Exception:
                    resp_json = {}
                return status_code, resp_json, resp_bytes
        except urllib.error.HTTPError as e:
            err_bytes = e.read()
            try:
                err_json = json.loads(err_bytes.decode("utf-8"))
            except Exception:
                err_json = {"error": str(e), "body": err_bytes.decode("utf-8", errors="ignore")}
            return e.code, err_json, err_bytes
        except Exception as e:
            return -1, {"error": str(e)}, b""

    def health(self) -> Dict[str, Any]:
        """Check server health."""
        code, resp, _ = self._request("/health")
        return resp

    def is_available(self) -> bool:
        """Check if remote Shizuku server is healthy and has rish available."""
        h = self.health()
        return h.get("status") == "healthy" and h.get("available") is True

    def get_status(self) -> Dict[str, Any]:
        """Query detailed remote Shizuku status including W^X dex safety & UID."""
        code, resp, _ = self._request("/api/shizuku/status")
        return resp

    def execute(self, command: str, timeout_sec: int = 10) -> Dict[str, Any]:
        """Execute privileged shell command via Shizuku rish."""
        code, resp, _ = self._request(
            "/api/shizuku/exec",
            method="POST",
            data={"command": command, "timeout_sec": timeout_sec},
            timeout=timeout_sec + 2,
        )
        return resp

    def tap(self, x: int, y: int) -> bool:
        """Inject touch tap at screen coordinates."""
        code, resp, _ = self._request("/api/shizuku/tap", method="POST", data={"x": x, "y": y})
        return resp.get("status") == "ok"

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Inject swipe gesture."""
        code, resp, _ = self._request(
            "/api/shizuku/swipe",
            method="POST",
            data={"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
        )
        return resp.get("status") == "ok"

    def key(self, keycode: int) -> bool:
        """Inject Android keycode (Home=3, Back=4, Power=26)."""
        code, resp, _ = self._request("/api/shizuku/key", method="POST", data={"keycode": keycode})
        return resp.get("status") == "ok"

    def text(self, text_to_type: str) -> bool:
        """Type text into focused input field."""
        code, resp, _ = self._request("/api/shizuku/text", method="POST", data={"text": text_to_type})
        return resp.get("status") == "ok"

    def screencap(self, output_path: Optional[str] = None, as_base64: bool = False) -> Union[bytes, str, None]:
        """Capture active screen. Can save to file or return raw PNG bytes / base64 string."""
        if as_base64:
            code, resp, _ = self._request("/api/shizuku/screencap", query={"format": "base64"}, timeout=15)
            return resp.get("image_base64")
        else:
            code, _, raw_bytes = self._request("/api/shizuku/screencap", query={"format": "png"}, timeout=15)
            if code == 200 and raw_bytes:
                if output_path:
                    with open(output_path, "wb") as f:
                        f.write(raw_bytes)
                return raw_bytes
            return None

    def get_battery(self) -> Dict[str, Any]:
        """Query physical battery telemetry."""
        code, resp, _ = self._request("/api/shizuku/battery")
        return resp

    def get_telemetry(self) -> Dict[str, Any]:
        """Query system telemetry."""
        code, resp, _ = self._request("/api/shizuku/telemetry")
        return resp

    def get_active_app(self) -> str:
        """Query current foreground focused package."""
        res = self.execute("dumpsys window displays | grep -E 'mCurrentFocus|mFocusedApp'")
        return res.get("stdout", "").strip()

    def grant_permission(self, package: str, permission: str) -> bool:
        """Grant privileged runtime permission without user prompt."""
        res = self.execute(f"pm grant {package} {permission}")
        return res.get("exit_code") == 0


def main():
    parser = argparse.ArgumentParser(description="Shizuku Remote Companion Client")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Target Android host IP (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Target port (default: {DEFAULT_PORT})")
    parser.add_argument("--auth-key", default=os.environ.get("SHIZUKU_AUTH_KEY"), help="X-Lauburu-Sovereign-Key auth key")

    subparsers = parser.add_subparsers(dest="action", help="Action to execute")

    subparsers.add_parser("health", help="Check server health")
    subparsers.add_parser("status", help="Get Shizuku & Android W^X status")

    exec_parser = subparsers.add_parser("exec", help="Execute shell command")
    exec_parser.add_argument("command", help="Command string")
    exec_parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")

    tap_parser = subparsers.add_parser("tap", help="Inject tap event")
    tap_parser.add_argument("x", type=int, help="X coordinate")
    tap_parser.add_argument("y", type=int, help="Y coordinate")

    swipe_parser = subparsers.add_parser("swipe", help="Inject swipe gesture")
    swipe_parser.add_argument("x1", type=int)
    swipe_parser.add_argument("y1", type=int)
    swipe_parser.add_argument("x2", type=int)
    swipe_parser.add_argument("y2", type=int)
    swipe_parser.add_argument("--duration", type=int, default=300)

    key_parser = subparsers.add_parser("key", help="Inject keyevent")
    key_parser.add_argument("keycode", type=int, help="KeyEvent code (3=Home, 4=Back, 26=Power)")

    text_parser = subparsers.add_parser("text", help="Type text into focus")
    text_parser.add_argument("text", help="Text to type")

    cap_parser = subparsers.add_parser("screencap", help="Capture screen")
    cap_parser.add_argument("output", nargs="?", default=None, help="Output PNG file path")
    cap_parser.add_argument("--base64", action="store_true", help="Print base64 instead of binary")

    subparsers.add_parser("battery", help="Query battery info")
    subparsers.add_parser("telemetry", help="Query system telemetry")
    subparsers.add_parser("active-app", help="Get current foreground package")

    grant_parser = subparsers.add_parser("grant", help="Grant permission")
    grant_parser.add_argument("package", help="Target package name")
    grant_parser.add_argument("permission", help="Permission name")

    args = parser.parse_args()

    client = ShizukuRemoteClient(host=args.host, port=args.port, auth_key=args.auth_key)

    if not args.action or args.action == "status":
        st = client.get_status()
        print(json.dumps(st, indent=2))
    elif args.action == "health":
        h = client.health()
        print(json.dumps(h, indent=2))
    elif args.action == "exec":
        res = client.execute(args.command, timeout_sec=args.timeout)
        print(json.dumps(res, indent=2))
    elif args.action == "tap":
        ok = client.tap(args.x, args.y)
        print("Success" if ok else "Failed")
    elif args.action == "swipe":
        ok = client.swipe(args.x1, args.y1, args.x2, args.y2, duration_ms=args.duration)
        print("Success" if ok else "Failed")
    elif args.action == "key":
        ok = client.key(args.keycode)
        print("Success" if ok else "Failed")
    elif args.action == "text":
        ok = client.text(args.text)
        print("Success" if ok else "Failed")
    elif args.action == "screencap":
        if args.base64:
            b64 = client.screencap(as_base64=True)
            print(b64)
        else:
            out_file = args.output or f"screencap_{int(time.time())}.png"
            client.screencap(output_path=out_file)
            print(f"Screen capture saved to {out_file}")
    elif args.action == "battery":
        b = client.get_battery()
        print(json.dumps(b, indent=2))
    elif args.action == "telemetry":
        t = client.get_telemetry()
        print(json.dumps(t, indent=2))
    elif args.action == "active-app":
        app = client.get_active_app()
        print(app)
    elif args.action == "grant":
        ok = client.grant_permission(args.package, args.permission)
        print("Granted" if ok else "Failed")


if __name__ == "__main__":
    main()
