#!/usr/bin/env python3
"""
================================================================================
Lauburu Lens: Chrome DevTools, Computer & Device Use Bridge (2026)
================================================================================
Subsystem: 01_apps/lauburu_lens/chrome_debugging_bridge.py
Lauburu Mesh Ecosystem — Multimodal Screen Perception & Cross-Device Automation

Integrates:
  1. Chrome DevTools Protocol (CDP) WebSocket Connection (Port 9222 / 9224)
  2. Autonomous Headless Chrome Process Supervision
  3. Dynamic Navigation, Script Evaluation, DOM Inspection & Screenshots
  4. Device Use via ADB Chrome Forwarding (Pixel 10 Pro XL, Samsung S20)
================================================================================
"""

import os
import sys
import json
import time
import base64
import urllib.request
import subprocess
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

try:
    import websockets
    import websockets.sync.client as ws_sync
except ImportError:
    websockets = None
    ws_sync = None

REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LOGS_DIR = REPO / "obsidian_vault/04_ANALYTICS/LENS_AUDITS"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Lens-CDP-Bridge] %(message)s")
log = logging.getLogger("LensCDPBridge")

CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_PROFILE = "/tmp/lens_cdp_profile"


class ChromeDebuggingBridge:
    """
    Bi-directional Chrome DevTools Protocol (CDP) WebSocket bridge.
    Connects to live browser sessions or spawns managed headless Chrome instances.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9222, fallback_port: int = 9224):
        self.host = host
        self.port = port
        self.fallback_port = fallback_port
        self.active_port = port
        self.base_url = f"http://{host}:{port}"
        self.process: Optional[subprocess.Popen] = None
        self.ws = None
        self.ws_url: Optional[str] = None
        self._msg_id = 0
        self._target_id: Optional[str] = None

    def check_cdp_status(self, port: Optional[int] = None) -> Dict[str, Any]:
        """Check if Chrome DevTools Protocol endpoint is responding."""
        check_port = port or self.active_port
        url = f"http://{self.host}:{check_port}/json/version"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LauburuLens/2.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "online": True,
                        "port": check_port,
                        "browser": data.get("Browser", "Unknown"),
                        "protocol_version": data.get("Protocol-Version", "Unknown"),
                        "web_socket_debugger_url": data.get("webSocketDebuggerUrl")
                    }
        except Exception as e:
            return {
                "online": False,
                "port": check_port,
                "error": str(e),
                "hint": "Start Chrome with --remote-debugging-port or spawn headless Chrome"
            }
        return {"online": False, "port": check_port, "error": "Unknown status"}

    def spawn_headless_chrome(self, port: int = 9224, profile_dir: str = DEFAULT_PROFILE) -> bool:
        """
        Spawn an isolated headless Chrome instance with remote debugging enabled.
        """
        if not os.path.exists(CHROME_BINARY):
            log.error(f"Chrome binary not found at {CHROME_BINARY}")
            return False

        os.makedirs(profile_dir, exist_ok=True)
        cmd = [
            CHROME_BINARY,
            "--headless=new",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile_dir}",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080"
        ]

        log.info(f"🚀 Spawning Headless Chrome on port {port}...")
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )
            # Wait for endpoint to become ready
            for _ in range(25):
                time.sleep(0.2)
                status = self.check_cdp_status(port)
                if status.get("online"):
                    self.active_port = port
                    self.base_url = f"http://{self.host}:{port}"
                    log.info(f"✅ Headless Chrome online on port {port} (PID: {self.process.pid})")
                    return True
        except Exception as e:
            log.error(f"Failed to spawn headless Chrome: {e}")
        return False

    def list_open_tabs(self) -> List[Dict[str, Any]]:
        """List open inspectable browser tabs / pages."""
        url = f"http://{self.host}:{self.active_port}/json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LauburuLens/2.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                tabs = json.loads(resp.read().decode("utf-8"))
                return [
                    {
                        "id": t.get("id"),
                        "title": t.get("title"),
                        "url": t.get("url"),
                        "type": t.get("type"),
                        "ws_url": t.get("webSocketDebuggerUrl")
                    }
                    for t in tabs if t.get("type") == "page"
                ]
        except Exception as e:
            log.warning(f"Unable to query tabs from {url}: {e}")
            return []

    def connect(self, port: Optional[int] = None) -> Any:
        """
        Establish WebSocket connection to Chrome DevTools Protocol.
        Automatically detects running Chrome or spawns headless Chrome.
        """
        target_port = port or self.port
        status = self.check_cdp_status(target_port)

        if not status.get("online"):
            log.info(f"Port {target_port} not online, trying fallback port {self.fallback_port}...")
            fallback_status = self.check_cdp_status(self.fallback_port)
            if fallback_status.get("online"):
                self.active_port = self.fallback_port
                target_port = self.fallback_port
            else:
                log.info(f"Spawning fresh headless Chrome on port {self.fallback_port}...")
                if self.spawn_headless_chrome(port=self.fallback_port):
                    target_port = self.fallback_port
                else:
                    raise RuntimeError(f"Unable to connect or spawn Chrome on port {target_port} or {self.fallback_port}")

        self.active_port = target_port
        self.base_url = f"http://{self.host}:{self.active_port}"

        # Get target page or create new one
        tabs = self.list_open_tabs()
        ws_url = None
        if tabs:
            ws_url = tabs[0].get("ws_url")
            self._target_id = tabs[0].get("id")

        if not ws_url:
            # Create new target tab via HTTP PUT /json/new
            try:
                req = urllib.request.Request(f"{self.base_url}/json/new", method="PUT")
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    page_data = json.loads(resp.read().decode("utf-8"))
                    ws_url = page_data.get("webSocketDebuggerUrl")
                    self._target_id = page_data.get("id")
            except Exception as e:
                # Fallback to browser websocket
                version_info = self.check_cdp_status(self.active_port)
                ws_url = version_info.get("webSocketDebuggerUrl")

        if not ws_url:
            raise ConnectionError(f"No webSocketDebuggerUrl found for Chrome at {self.base_url}")

        self.ws_url = ws_url
        log.info(f"Connecting WebSocket to {self.ws_url}...")

        # Use sync client for clean synchronous Python API
        if ws_sync is not None:
            self.ws = ws_sync.connect(self.ws_url, open_timeout=5.0, max_size=50 * 1024 * 1024)
        else:
            raise ImportError("websockets.sync.client is required for ChromeDebuggingBridge")

        log.info("✅ CDP WebSocket connected successfully.")
        return self.ws

    def send_cdp(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
        """Send synchronous CDP command and wait for matching response."""
        if not self.ws:
            self.connect()

        self._msg_id += 1
        req_id = self._msg_id
        payload = {"id": req_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                raw = self.ws.recv(timeout=timeout)
                msg = json.loads(raw)
                if msg.get("id") == req_id:
                    if "error" in msg:
                        log.error(f"CDP error in {method}: {msg.get('error')}")
                    return msg
            except Exception as e:
                log.error(f"Error receiving CDP message for {method}: {e}")
                break
        return {"id": req_id, "error": {"message": f"Timeout waiting for response to {method}"}}

    def navigate(self, url: str, wait_seconds: float = 2.0) -> bool:
        """Navigate to URL and wait for DOM load."""
        log.info(f"Navigating to {url}...")
        res = self.send_cdp("Page.navigate", {"url": url})
        if "error" in res:
            return False
        time.sleep(wait_seconds)
        return True

    def evaluate(self, script: str, timeout: float = 10.0) -> Any:
        """Evaluate JavaScript expression and return deserialized result."""
        res = self.send_cdp("Runtime.evaluate", {
            "expression": script,
            "returnByValue": True,
            "awaitPromise": True
        }, timeout=timeout)
        if "result" in res and "result" in res["result"]:
            inner = res["result"]["result"]
            if inner.get("type") == "undefined":
                return None
            return inner.get("value")
        return None

    def capture_screenshot(self, format: str = "png") -> bytes:
        """Capture current page screenshot as raw bytes."""
        res = self.send_cdp("Page.captureScreenshot", {"format": format})
        if "result" in res and "data" in res["result"]:
            return base64.b64decode(res["result"]["data"])
        return b""

    def forward_android_chrome(self, device_id: str = "100.73.38.87:5555", local_port: int = 9223) -> bool:
        """Forward remote Android Chrome DevTools via ADB socket."""
        cmd = ["adb", "-s", device_id, "forward", f"tcp:{local_port}", "localabstract:chrome_devtools_remote"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                log.info(f"✅ ADB forwarded Android Chrome on {device_id} to 127.0.0.1:{local_port}")
                return True
            else:
                log.warning(f"ADB forward failed: {res.stderr}")
                return False
        except Exception as e:
            log.warning(f"Error running ADB forward: {e}")
            return False

    def close(self):
        """Close WebSocket connection and cleanly terminate managed browser."""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    bridge = ChromeDebuggingBridge()
    log.info("═══════════════════════════════════════════════════════════════")
    log.info(" 🔍 Lauburu Lens Chrome DevTools & Device Use Bridge")
    log.info("═══════════════════════════════════════════════════════════════")

    bridge.connect()
    title = bridge.evaluate("document.title")
    log.info(f"Connected to page: {title}")

    # Navigate to Port 4000 Console
    bridge.navigate("http://127.0.0.1:4000")
    title4000 = bridge.evaluate("document.title")
    log.info(f"Port 4000 Title: {title4000}")

    screenshot = bridge.capture_screenshot()
    log.info(f"Captured screenshot: {len(screenshot)} bytes")
    bridge.close()

if __name__ == "__main__":
    main()
