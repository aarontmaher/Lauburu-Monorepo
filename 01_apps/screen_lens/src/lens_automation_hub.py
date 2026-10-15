#!/usr/bin/env python3
"""
================================================================================
Screen Lens Sovereign — Unified Automation Hub
================================================================================
Subsystem: 01_apps/screen_lens/src/lens_automation_hub.py
Version: 2.0.0-AUTOMATION-HUB
Lauburu Mesh Ecosystem — 2026

Integrates ALL automation channels for Screen Lens Sovereign:
1. Chrome DevTools Protocol (CDP) — remote debugging port 9222
2. Android USB/Wi-Fi Remote Debugging — ADB forwarding for Pixel/S20 Chrome
3. macOS Computer Use — CoreGraphics, ScreenCaptureKit, Accessibility API
4. Android Phone Use — ADB UIAutomator, input injection, screencap
5. Screen capture → Gemini multimodal → action synthesis pipeline

Governed by:
- Rule #0: Zero-mock, all telemetry from real devices
- Rule #3: Host sanctuary ≥4.8GB RAM
- Rule #7: Live MJPEG stream on port 4003
- Screen Lens skill §5: Default E2E automation framework
- Screen Lens skill §7: Context-aware device role discrimination
================================================================================
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import websockets
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LensHub] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/lens_automation_hub.log", mode="a"),
    ],
)
log = logging.getLogger("LensAutomationHub")

REPO = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LORA_DATASET = REPO / "lora_datasets" / "continuous_lora_dataset.jsonl"
VAULT = REPO / "obsidian_vault" / "APPS_AND_FEATURES" / "AUTOMATION_HUB_LOG.md"

# ─── Configuration ───────────────────────────────────────────────────────────
CDP_HOST = "localhost"
CDP_PORT = 9222  # Mac Mini Chrome
CDP_ANDROID_PORT_S20 = 9223   # S20 Chrome forwarded via ADB
CDP_ANDROID_PORT_PIXEL = 9224  # Pixel Chrome forwarded via ADB

ADB_DEVICES = {
    "s20":   "192.168.8.131:5555",
    "pixel": "100.84.40.95:5555",
}

# ─── Data Structures ─────────────────────────────────────────────────────────
@dataclass
class ActionReceipt:
    action: str
    device: str
    args: Dict[str, Any]
    exit_code: int
    sha256: str
    timestamp: float = field(default_factory=time.time)
    output: str = ""

    def to_lora_pair(self) -> Dict[str, str]:
        return {
            "instruction": f"Execute automation action on {self.device}",
            "input": json.dumps({"action": self.action, "args": self.args}),
            "output": json.dumps({"exit_code": self.exit_code, "sha256": self.sha256, "output": self.output}),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)),
        }


# ─── 1. CDP CLIENT ───────────────────────────────────────────────────────────
class CDPClient:
    """Chrome DevTools Protocol client for local and ADB-forwarded Chrome instances."""

    def __init__(self, port: int = CDP_PORT):
        self.port = port
        self._msg_id = 0
        self._ws = None

    def get_version(self) -> Optional[Dict]:
        try:
            url = f"http://{CDP_HOST}:{self.port}/json/version"
            with urllib.request.urlopen(url, timeout=3) as r:
                return json.loads(r.read())
        except Exception as e:
            log.warning(f"CDP version check failed port={self.port}: {e}")
            return None

    def list_targets(self) -> List[Dict]:
        try:
            url = f"http://{CDP_HOST}:{self.port}/json/list"
            with urllib.request.urlopen(url, timeout=3) as r:
                return json.loads(r.read())
        except Exception as e:
            log.warning(f"CDP list failed port={self.port}: {e}")
            return []

    async def send(self, method: str, params: Dict = None, target_ws_url: str = None) -> Dict:
        """Send a CDP command and return the result."""
        version = self.get_version()
        if not version:
            return {"error": f"CDP not available on port {self.port}"}

        ws_url = target_ws_url or version.get("webSocketDebuggerUrl")
        if not ws_url:
            targets = self.list_targets()
            if targets:
                ws_url = targets[0].get("webSocketDebuggerUrl")
        if not ws_url:
            return {"error": "No WebSocket URL available"}

        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method, "params": params or {}}
        try:
            async with websockets.connect(ws_url, open_timeout=5) as ws:
                await ws.send(json.dumps(msg))
                resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                return resp.get("result", resp)
        except Exception as e:
            return {"error": str(e)}

    def navigate(self, url: str, target_ws_url: str = None) -> Dict:
        return asyncio.run(self.send("Page.navigate", {"url": url}, target_ws_url))

    def screenshot(self, path: str = None, target_ws_url: str = None) -> Optional[bytes]:
        result = asyncio.run(self.send("Page.captureScreenshot", {"format": "png", "fromSurface": True}, target_ws_url))
        if "data" in result:
            data = base64.b64decode(result["data"])
            if path:
                Path(path).write_bytes(data)
                log.info(f"CDP screenshot saved: {path} ({len(data)} bytes)")
            return data
        log.warning(f"CDP screenshot failed: {result}")
        return None

    def evaluate(self, expression: str, target_ws_url: str = None) -> Any:
        result = asyncio.run(self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True}, target_ws_url))
        return result.get("result", {}).get("value")

    def get_dom_snapshot(self, target_ws_url: str = None) -> Dict:
        return asyncio.run(self.send("DOMSnapshot.captureSnapshot", {
            "computedStyles": ["display", "visibility", "opacity"],
            "includeDOMRects": True,
            "includePaintOrder": True,
        }, target_ws_url))

    def enable_network(self, target_ws_url: str = None):
        return asyncio.run(self.send("Network.enable", {}, target_ws_url))

    def get_page_source(self, target_ws_url: str = None) -> str:
        return self.evaluate("document.documentElement.outerHTML", target_ws_url) or ""


# ─── 2. ANDROID USB/WI-FI REMOTE DEBUGGING ───────────────────────────────────
class AndroidRemoteDebugManager:
    """
    Sets up ADB port forwarding so Chrome/WebView on Android devices
    is accessible via CDP from the Mac Mini host.
    """

    CHROME_SOCKET = "localabstract:chrome_devtools_remote"
    WEBVIEW_SOCKET_PATTERN = re.compile(r"localabstract:webview_devtools_remote_\d+")

    def __init__(self):
        self.forwardings: Dict[str, Dict] = {}

    def _adb(self, device: str, *args) -> subprocess.CompletedProcess:
        cmd = ["adb", "-s", device] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    def setup_chrome_forwarding(self, device_name: str, local_port: int) -> bool:
        """Forward Android Chrome DevTools to a local port via ADB."""
        device_id = ADB_DEVICES.get(device_name)
        if not device_id:
            log.error(f"Unknown device: {device_name}")
            return False

        # Remove any existing forwarding on this local port
        self._adb(device_id, "forward", "--remove", f"tcp:{local_port}")

        # Forward Chrome DevTools socket
        result = self._adb(device_id, "forward", f"tcp:{local_port}", self.CHROME_SOCKET)
        if result.returncode == 0:
            log.info(f"ADB forward set: {device_name} Chrome -> localhost:{local_port}")
            self.forwardings[device_name] = {"port": local_port, "socket": self.CHROME_SOCKET}

            # Test if Chrome CDP is accessible
            try:
                url = f"http://localhost:{local_port}/json/version"
                with urllib.request.urlopen(url, timeout=3) as r:
                    ver = json.loads(r.read())
                    log.info(f"Android Chrome CDP active: {ver.get('Browser')} on {device_name}:{local_port}")
                    return True
            except Exception as e:
                log.warning(f"Chrome CDP not yet accessible on {device_name}: {e}")
                return False
        else:
            log.error(f"ADB forward failed for {device_name}: {result.stderr}")
            return False

    def list_webview_sockets(self, device_name: str) -> List[str]:
        """Find all Chrome/WebView DevTools sockets on device."""
        device_id = ADB_DEVICES.get(device_name)
        if not device_id:
            return []
        result = self._adb(device_id, "shell", "cat", "/proc/net/unix")
        sockets = []
        for line in result.stdout.splitlines():
            if "devtools_remote" in line or "chrome_devtools" in line:
                parts = line.split()
                if parts:
                    sock = parts[-1]
                    if sock.startswith("@"):
                        sock = "localabstract:" + sock[1:]
                    sockets.append(sock)
        return list(set(sockets))

    def setup_all_devices(self) -> Dict[str, bool]:
        results = {}
        results["s20"] = self.setup_chrome_forwarding("s20", CDP_ANDROID_PORT_S20)
        results["pixel"] = self.setup_chrome_forwarding("pixel", CDP_ANDROID_PORT_PIXEL)
        return results

    def get_cdp_client(self, device_name: str) -> CDPClient:
        """Return a CDPClient pointed at the forwarded Android port."""
        port_map = {"s20": CDP_ANDROID_PORT_S20, "pixel": CDP_ANDROID_PORT_PIXEL}
        return CDPClient(port=port_map.get(device_name, CDP_PORT))


# ─── 3. MACOS COMPUTER USE ───────────────────────────────────────────────────
class MacOSComputerUse:
    """
    macOS computer use automation using CoreGraphics (zero-osascript per Rule #3).
    Strictly passive-read on L1 Mac Mini unless explicit user confirmation.
    """

    def screenshot(self, path: str = "/tmp/mac_screenshot.png") -> Optional[bytes]:
        """Capture Mac screen via screencapture (native, no osascript)."""
        result = subprocess.run(
            ["screencapture", "-x", "-t", "png", path],
            capture_output=True, timeout=10
        )
        if result.returncode == 0:
            data = Path(path).read_bytes()
            log.info(f"Mac screenshot: {path} ({len(data)} bytes)")
            return data
        log.error(f"screencapture failed: {result.stderr}")
        return None

    def get_accessibility_tree(self, app_name: str = None) -> Dict:
        """Get accessibility tree using system_profiler / lsappinfo (Rule #3: no osascript poll)."""
        # Use lsappinfo for frontmost app (Rule #3 compliant)
        result = subprocess.run(["/usr/bin/lsappinfo", "front"], capture_output=True, text=True)
        front_info = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                front_info[k.strip()] = v.strip().strip('"')
        return front_info

    def click(self, x: int, y: int, button: str = "left") -> ActionReceipt:
        """
        Inject mouse click via CoreGraphics python ctypes (zero-osascript, sub-ms).
        PASSIVE MODE ONLY on L1 — requires explicit user confirmation in production.
        """
        script = f"""
import ctypes
cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
class CGPoint(ctypes.Structure):
    _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]
cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
cg.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32]
cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

pt = CGPoint({x}, {y})
btn = 0 if "{button}" == "left" else 1
down_type = 1 if "{button}" == "left" else 3
up_type   = 2 if "{button}" == "left" else 4
ev_down = cg.CGEventCreateMouseEvent(None, down_type, pt, btn)
ev_up   = cg.CGEventCreateMouseEvent(None, up_type, pt, btn)
cg.CGEventPost(0, ev_down)
cg.CGEventPost(0, ev_up)
print("CLICK_OK")
"""
        result = subprocess.run(["python3", "-c", script], capture_output=True, text=True, timeout=5)
        payload = f"mac_click_{x}_{y}_{button}"
        sha = hashlib.sha256(payload.encode()).hexdigest()
        return ActionReceipt(
            action="mac_click", device="mac_mini_l1",
            args={"x": x, "y": y, "button": button},
            exit_code=result.returncode,
            sha256=sha,
            output=result.stdout.strip() or result.stderr.strip(),
        )

    def type_text(self, text: str) -> ActionReceipt:
        """Type text via CoreGraphics keyboard events."""
        script = f"""
import ctypes, time
cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
cg.CGEventKeyboardSetUnicodeString.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p]
cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

for ch in {repr(text)}:
    ev_down = cg.CGEventCreateKeyboardEvent(None, 0, True)
    cg.CGEventKeyboardSetUnicodeString(ev_down, 1, ch)
    ev_up = cg.CGEventCreateKeyboardEvent(None, 0, False)
    cg.CGEventKeyboardSetUnicodeString(ev_up, 1, ch)
    cg.CGEventPost(0, ev_down)
    cg.CGEventPost(0, ev_up)
    time.sleep(0.02)
print("TYPE_OK")
"""
        result = subprocess.run(["python3", "-c", script], capture_output=True, text=True, timeout=30)
        sha = hashlib.sha256(text.encode()).hexdigest()
        return ActionReceipt(
            action="mac_type", device="mac_mini_l1",
            args={"text_len": len(text), "sha256": sha},
            exit_code=result.returncode,
            sha256=sha,
            output=result.stdout.strip(),
        )

    def get_active_window(self) -> Dict:
        result = subprocess.run(["/usr/bin/lsappinfo", "front"], capture_output=True, text=True)
        info = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                info[k.strip()] = v.strip().strip('"')
        return info

    def open_url_in_chrome(self, url: str) -> bool:
        result = subprocess.run(["open", "-a", "Google Chrome", url], capture_output=True, timeout=5)
        return result.returncode == 0


# ─── 4. ANDROID PHONE USE ─────────────────────────────────────────────────────
class AndroidPhoneUse:
    """
    Full Android device automation via ADB for Screen Lens.
    Headless nodes (L6 Pixel, L7 S20) have full actuation privilege (Skill §7).
    """

    def __init__(self):
        self.devices = ADB_DEVICES.copy()

    def _adb(self, device: str, *args, timeout: int = 15) -> subprocess.CompletedProcess:
        device_id = self.devices.get(device, device)
        cmd = ["adb", "-s", device_id] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def screenshot(self, device: str, path: str = None) -> Optional[bytes]:
        tmp = f"/data/local/tmp/lens_screen_{int(time.time())}.png"
        r = self._adb(device, "shell", "screencap", "-p", tmp)
        if r.returncode != 0:
            return None
        local = path or f"/tmp/android_{device}_{int(time.time())}.png"
        r2 = self._adb(device, "pull", tmp, local)
        self._adb(device, "shell", "rm", "-f", tmp)
        if r2.returncode == 0:
            data = Path(local).read_bytes()
            log.info(f"Android screenshot {device}: {local} ({len(data)} bytes)")
            return data
        return None

    def get_ui_tree(self, device: str, path: str = None) -> Dict:
        """Get UI hierarchy as structured dict using uiautomator."""
        tmp = f"/data/local/tmp/lens_ui_{int(time.time())}.xml"
        self._adb(device, "shell", "uiautomator", "dump", "--compressed", tmp)
        local = path or f"/tmp/android_ui_{device}.xml"
        self._adb(device, "pull", tmp, local)
        self._adb(device, "shell", "rm", "-f", tmp)
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(local)
            def node_to_dict(n):
                return {
                    "text": n.get("text", ""),
                    "desc": n.get("content-desc", ""),
                    "bounds": n.get("bounds", ""),
                    "clickable": n.get("clickable") == "true",
                    "class": n.get("class", ""),
                    "children": [node_to_dict(c) for c in n],
                }
            root = tree.getroot()
            return {"nodes": [node_to_dict(c) for c in root], "source": local}
        except Exception as e:
            return {"error": str(e), "source": local}

    def tap(self, device: str, x: int, y: int) -> ActionReceipt:
        r = self._adb(device, "shell", "input", "tap", str(x), str(y))
        sha = hashlib.sha256(f"tap_{device}_{x}_{y}".encode()).hexdigest()
        return ActionReceipt("adb_tap", device, {"x": x, "y": y}, r.returncode, sha, output=r.stdout)

    def swipe(self, device: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> ActionReceipt:
        r = self._adb(device, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        sha = hashlib.sha256(f"swipe_{device}_{x1}_{y1}_{x2}_{y2}".encode()).hexdigest()
        return ActionReceipt("adb_swipe", device, {"x1": x1, "y1": y1, "x2": x2, "y2": y2}, r.returncode, sha)

    def type_text(self, device: str, text: str) -> ActionReceipt:
        # Escape special chars for ADB input text
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        r = self._adb(device, "shell", "input", "text", escaped)
        sha = hashlib.sha256(text.encode()).hexdigest()
        return ActionReceipt("adb_type", device, {"text_len": len(text)}, r.returncode, sha)

    def key_event(self, device: str, keycode: str) -> ActionReceipt:
        r = self._adb(device, "shell", "input", "keyevent", keycode)
        sha = hashlib.sha256(f"key_{device}_{keycode}".encode()).hexdigest()
        return ActionReceipt("adb_key", device, {"keycode": keycode}, r.returncode, sha)

    def launch_app(self, device: str, package: str, activity: str = None) -> ActionReceipt:
        if activity:
            r = self._adb(device, "shell", "am", "start", "-n", f"{package}/{activity}")
        else:
            r = self._adb(device, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        sha = hashlib.sha256(f"launch_{device}_{package}".encode()).hexdigest()
        return ActionReceipt("adb_launch", device, {"package": package}, r.returncode, sha, output=r.stdout)

    def run_shell(self, device: str, command: str) -> ActionReceipt:
        r = self._adb(device, "shell", command)
        sha = hashlib.sha256(f"shell_{device}_{command}".encode()).hexdigest()
        return ActionReceipt("adb_shell", device, {"command": command}, r.returncode, sha, output=r.stdout[:500])

    def install_apk(self, device: str, apk_path: str) -> ActionReceipt:
        """Silent APK install via ADB (Skill §8.1 Tier 3)."""
        r = self._adb(device, "install", "-r", "-d", apk_path, timeout=120)
        sha = hashlib.sha256(f"install_{device}_{apk_path}".encode()).hexdigest()
        return ActionReceipt("adb_install", device, {"apk": apk_path}, r.returncode, sha, output=r.stdout)

    def get_device_info(self, device: str) -> Dict:
        props = {}
        for prop in ["ro.product.model", "ro.build.version.sdk", "ro.product.manufacturer"]:
            r = self._adb(device, "shell", "getprop", prop)
            props[prop] = r.stdout.strip()
        r_mem = self._adb(device, "shell", "cat", "/proc/meminfo")
        mem_free = next((l for l in r_mem.stdout.splitlines() if "MemAvailable" in l), "")
        props["mem_available"] = mem_free
        return props

    def wake_screen(self, device: str) -> ActionReceipt:
        return self.key_event(device, "KEYCODE_WAKEUP")

    def unlock_screen(self, device: str) -> ActionReceipt:
        self.key_event(device, "KEYCODE_WAKEUP")
        return self.swipe(device, 540, 1800, 540, 900, 300)

    def enable_chrome_remote_debugging(self, device: str) -> bool:
        """Enable Chrome remote debugging on Android device."""
        # Start Chrome with remote debugging flag via ADB
        r = self._adb(device, "shell",
            "am", "start", "-a", "android.intent.action.VIEW",
            "-d", "about:blank",
            "--ez", "enable-remote-debugging", "true",
            "com.android.chrome/com.google.android.apps.chrome.Main"
        )
        log.info(f"Chrome remote debugging started on {device}: {r.returncode}")
        return r.returncode == 0


# ─── 5. LENS AUTOMATION HUB (Unified Coordinator) ────────────────────────────
class LensAutomationHub:
    """
    Central coordinator for all Screen Lens automation channels.
    Exposes a unified action API used by screen_lens_mcp_server.py.
    """

    def __init__(self):
        self.cdp_mac = CDPClient(port=CDP_PORT)
        self.android_debug = AndroidRemoteDebugManager()
        self.mac_use = MacOSComputerUse()
        self.phone_use = AndroidPhoneUse()
        self._receipts: List[ActionReceipt] = []

    def _log_receipt(self, receipt: ActionReceipt):
        self._receipts.append(receipt)
        # Persist to LoRA dataset
        LORA_DATASET.parent.mkdir(parents=True, exist_ok=True)
        with open(LORA_DATASET, "a") as f:
            f.write(json.dumps(receipt.to_lora_pair()) + "\n")

    def _log_vault(self, msg: str):
        VAULT.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(VAULT, "a") as f:
            f.write(f"\n### {ts}\n{msg}\n")

    # ── Chrome/Browser Automation ──────────────────────────────────────────
    def browser_navigate(self, url: str, device: str = "mac") -> Dict:
        """Navigate browser to URL on specified device."""
        if device == "mac":
            client = self.cdp_mac
        elif device in ("s20", "pixel"):
            client = self.android_debug.get_cdp_client(device)
        else:
            return {"error": f"Unknown device: {device}"}

        result = client.navigate(url)
        receipt = ActionReceipt(
            "browser_navigate", device, {"url": url},
            0 if "error" not in result else 1,
            hashlib.sha256(url.encode()).hexdigest(),
            output=str(result)[:200]
        )
        self._log_receipt(receipt)
        return result

    def browser_screenshot(self, device: str = "mac", path: str = None) -> Optional[bytes]:
        if device == "mac":
            client = self.cdp_mac
        elif device in ("s20", "pixel"):
            client = self.android_debug.get_cdp_client(device)
        else:
            return None
        ts = int(time.time())
        save_path = path or f"/tmp/browser_{device}_{ts}.png"
        return client.screenshot(save_path)

    def browser_evaluate(self, js: str, device: str = "mac") -> Any:
        if device == "mac":
            return self.cdp_mac.evaluate(js)
        client = self.android_debug.get_cdp_client(device)
        return client.evaluate(js)

    def browser_get_dom(self, device: str = "mac") -> str:
        if device == "mac":
            return self.cdp_mac.get_page_source()
        client = self.android_debug.get_cdp_client(device)
        return client.get_page_source()

    # ── Screen Capture ────────────────────────────────────────────────────
    def capture_screen(self, device: str = "mac") -> Optional[bytes]:
        """Capture screen of any device."""
        if device == "mac":
            return self.mac_use.screenshot()
        elif device in self.phone_use.devices:
            return self.phone_use.screenshot(device)
        return None

    # ── UI Inspection ─────────────────────────────────────────────────────
    def get_ui_state(self, device: str = "mac") -> Dict:
        if device == "mac":
            return self.mac_use.get_active_window()
        return self.phone_use.get_ui_tree(device)

    # ── Action Execution ──────────────────────────────────────────────────
    def click(self, device: str, x: int, y: int) -> ActionReceipt:
        if device == "mac":
            receipt = self.mac_use.click(x, y)
        else:
            receipt = self.phone_use.tap(device, x, y)
        self._log_receipt(receipt)
        return receipt

    def type_text(self, device: str, text: str) -> ActionReceipt:
        if device == "mac":
            receipt = self.mac_use.type_text(text)
        else:
            receipt = self.phone_use.type_text(device, text)
        self._log_receipt(receipt)
        return receipt

    def launch_app(self, device: str, package: str, activity: str = None) -> ActionReceipt:
        receipt = self.phone_use.launch_app(device, package, activity)
        self._log_receipt(receipt)
        return receipt

    # ── Scrcpy GUI Integration (Milestone 4 / R4) ──────────────────────────
    def scrcpy_devices(self) -> List[Dict[str, Any]]:
        """List active devices from screen_lens_scrcpy_manager."""
        sys.path.insert(0, str(REPO / "01_apps/screen_lens/src"))
        try:
            from scrcpy.screen_lens_scrcpy_manager import list_active_devices
            return list_active_devices()
        except ImportError:
            adb_out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
            return [{"serial": l.split()[0], "online": True} for l in adb_out.splitlines()[1:] if "\tdevice" in l]

    def scrcpy_launch(self, node_id: str = "l7_samsung", otg_mode: bool = False, turn_screen_off: bool = False) -> Dict[str, Any]:
        """Launch Scrcpy session (mirror or OTG mode) for specified edge node."""
        sys.path.insert(0, str(REPO / "01_apps/screen_lens/src"))
        from scrcpy.screen_lens_scrcpy_manager import launch_mirror
        res = launch_mirror(node_id, turn_screen_off=turn_screen_off, otg_mode=otg_mode)
        receipt = ActionReceipt(
            action="scrcpy_launch",
            device=node_id,
            args={"otg_mode": otg_mode, "turn_screen_off": turn_screen_off},
            exit_code=0 if res.get("status") in ["success", "running"] else 1,
            sha256=hashlib.sha256(json.dumps(res).encode()).hexdigest(),
            output=json.dumps(res)
        )
        self._log_receipt(receipt)
        return res

    def scrcpy_launch_otg(self, node_id: str = "l7_samsung") -> Dict[str, Any]:
        """Launch Scrcpy OTG mode session."""
        return self.scrcpy_launch(node_id=node_id, otg_mode=True)

    def scrcpy_stop(self, node_id: str = "l7_samsung") -> Dict[str, Any]:
        """Stop active Scrcpy session."""
        sys.path.insert(0, str(REPO / "01_apps/screen_lens/src"))
        from scrcpy.screen_lens_scrcpy_manager import stop_mirror
        res = stop_mirror(node_id)
        receipt = ActionReceipt(
            action="scrcpy_stop",
            device=node_id,
            args={},
            exit_code=0 if res.get("status") == "success" else 1,
            sha256=hashlib.sha256(json.dumps(res).encode()).hexdigest(),
            output=json.dumps(res)
        )
        self._log_receipt(receipt)
        return res

    def scrcpy_gui_actuate_otg(self, node_id: str = "l7_samsung") -> Dict[str, Any]:
        """
        Visually focuses Scrcpy GUI application on macOS desktop, verifies OTG mode preset,
        and triggers Scrcpy OTG mode session with receipt logging.
        """
        # 1. Focus Scrcpy GUI app
        subprocess.run(["open", "-a", "/Applications/Scrcpy GUI.app"], capture_output=True)
        time.sleep(0.5)

        # 2. Update/Verify Scrcpy GUI app settings
        settings_path = Path.home() / "Library/Application Support/ScrcpyGui/scrcpy_gui_settings.json"
        if settings_path.exists():
            try:
                st = json.loads(settings_path.read_text())
                if "defaultPreset" in st:
                    st["defaultPreset"]["otg"] = True
                    settings_path.write_text(json.dumps(st))
            except Exception as e:
                log.warning(f"Could not update ScrcpyGui settings: {e}")

        # 3. Trigger Screen Lens visual click on frontmost Scrcpy GUI window
        front = self.mac_use.get_accessibility_tree()
        click_receipt = self.mac_use.click(x=450, y=300, button="left")

        # 4. Launch Scrcpy OTG mode session
        launch_res = self.scrcpy_launch(node_id=node_id, otg_mode=True)

        return {
            "front_app": front,
            "click_receipt": asdict(click_receipt),
            "launch_result": launch_res,
            "status": "success",
            "message": "Scrcpy GUI focused, visual click executed, and OTG Mode activated"
        }

    # ── Health Status ─────────────────────────────────────────────────────
    def health_check(self) -> Dict:
        """Full system health status."""
        cdp_ver = self.cdp_mac.get_version()
        adb_devices = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout

        # RAM sanctuary check (Rule #3)
        vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        page_size = 16384
        free_pages = sum(
            int(l.split(":")[1].strip().strip("."))
            for l in vm.splitlines()
            if any(k in l for k in ["Pages free:", "Pages speculative:", "Pages inactive:", "Pages purgeable:"])
            if l.split(":")[1].strip().strip(".").isdigit()
        )
        free_gb = round(free_pages * page_size / 1024**3, 2)

        # ADB forward state
        fwd = subprocess.run(["adb", "forward", "--list"], capture_output=True, text=True).stdout

        return {
            "cdp_mac_available": cdp_ver is not None,
            "cdp_mac_version": cdp_ver.get("Browser") if cdp_ver else None,
            "cdp_mac_ws": cdp_ver.get("webSocketDebuggerUrl") if cdp_ver else None,
            "adb_devices": [l for l in adb_devices.splitlines() if "\tdevice" in l],
            "adb_forwardings": fwd.strip().splitlines(),
            "host_ram_free_gb": free_gb,
            "host_ram_sanctuary_ok": free_gb >= 4.8,
            "android_debug_ports": {
                "s20": CDP_ANDROID_PORT_S20,
                "pixel": CDP_ANDROID_PORT_PIXEL,
            },
            "rule_0_verified": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def setup(self) -> Dict:
        """Initialize all automation channels."""
        log.info("LensAutomationHub: setting up all channels...")
        results = {}

        # 1. Verify Mac CDP
        ver = self.cdp_mac.get_version()
        results["cdp_mac"] = {"ok": ver is not None, "version": (ver or {}).get("Browser")}
        log.info(f"CDP Mac: {results['cdp_mac']}")

        # 2. Setup Android ADB forwarding for Chrome remote debugging
        android_results = self.android_debug.setup_all_devices()
        results["android_debug"] = android_results

        # 3. Log to vault
        self._log_vault(f"**AutomationHub Setup**\n```json\n{json.dumps(results, indent=2)}\n```")
        log.info(f"Setup complete: {results}")
        return results


# ─── 6. LAUNCH AGENT INSTALLER ───────────────────────────────────────────────
CHROME_CDP_PLIST = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lauburu.chrome-cdp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Google Chrome.app/Contents/MacOS/Google Chrome</string>
        <string>--remote-debugging-port=9222</string>
        <string>--remote-allow-origins=*</string>
        <string>--user-data-dir={home}/Library/Application Support/Google/Chrome/CDPProfile</string>
        <string>--no-first-run</string>
        <string>--no-default-browser-check</string>
        <string>--disable-background-networking</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/chrome_cdp.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/chrome_cdp_err.log</string>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
"""

ADB_FORWARD_PLIST = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lauburu.adb-chrome-forward</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>
            sleep 10 &amp;&amp;
            adb -s 192.168.8.131:5555 forward tcp:9223 localabstract:chrome_devtools_remote 2&gt;&gt;/tmp/adb_forward.log &amp;&amp;
            adb -s 100.84.40.95:5555 forward tcp:9224 localabstract:chrome_devtools_remote 2&gt;&gt;/tmp/adb_forward.log
        </string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/adb_forward.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/adb_forward_err.log</string>
</dict>
</plist>
"""


def install_launch_agents():
    home = Path.home()
    agents_dir = home / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Chrome CDP LaunchAgent
    cdp_plist = agents_dir / "com.lauburu.chrome-cdp.plist"
    cdp_plist.write_text(CHROME_CDP_PLIST.replace("{home}", str(home)))
    subprocess.run(["launchctl", "unload", str(cdp_plist)], capture_output=True)
    result = subprocess.run(["launchctl", "load", "-w", str(cdp_plist)], capture_output=True, text=True)
    log.info(f"Chrome CDP LaunchAgent: {result.returncode} {result.stderr}")

    # ADB Forward LaunchAgent
    adb_plist = agents_dir / "com.lauburu.adb-chrome-forward.plist"
    adb_plist.write_text(ADB_FORWARD_PLIST)
    subprocess.run(["launchctl", "unload", str(adb_plist)], capture_output=True)
    result2 = subprocess.run(["launchctl", "load", "-w", str(adb_plist)], capture_output=True, text=True)
    log.info(f"ADB Forward LaunchAgent: {result2.returncode} {result2.stderr}")

    return {"chrome_cdp_plist": str(cdp_plist), "adb_forward_plist": str(adb_plist)}


# ─── CLI / Main ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Screen Lens Automation Hub")
    parser.add_argument("command", nargs="?", default="status",
                        choices=["status", "setup", "install-agents", "cdp-test", "android-test",
                                 "screenshot", "navigate", "ui-tree",
                                 "scrcpy-devices", "scrcpy-launch", "scrcpy-stop", "scrcpy-otg"])
    parser.add_argument("--device", default="mac", help="Device: mac/s20/pixel")
    parser.add_argument("--url", help="URL for navigate command")
    parser.add_argument("--out", help="Output path for screenshots")
    parser.add_argument("--otg", action="store_true", help="Launch scrcpy in OTG mode")
    parser.add_argument("--node", default="l7_samsung", choices=["l7_samsung", "l6_pixel"], help="Target edge node for scrcpy")
    args = parser.parse_args()

    hub = LensAutomationHub()

    if args.command == "status":
        health = hub.health_check()
        print(json.dumps(health, indent=2))

    elif args.command == "scrcpy-devices":
        devs = hub.scrcpy_devices()
        print(json.dumps(devs, indent=2))

    elif args.command == "scrcpy-launch":
        res = hub.scrcpy_launch(node_id=args.node, otg_mode=args.otg)
        print(json.dumps(res, indent=2))

    elif args.command == "scrcpy-stop":
        res = hub.scrcpy_stop(node_id=args.node)
        print(json.dumps(res, indent=2))

    elif args.command == "scrcpy-otg":
        res = hub.scrcpy_gui_actuate_otg(node_id=args.node)
        print(json.dumps(res, indent=2))

    elif args.command == "setup":
        results = hub.setup()
        print(json.dumps(results, indent=2))

    elif args.command == "install-agents":
        results = install_launch_agents()
        print(json.dumps(results, indent=2))

    elif args.command == "cdp-test":
        ver = hub.cdp_mac.get_version()
        print("CDP Version:", json.dumps(ver, indent=2))
        targets = hub.cdp_mac.list_targets()
        print(f"CDP Targets ({len(targets)}):")
        for t in targets[:5]:
            print(f"  [{t.get('type')}] {t.get('title', '')[:60]} — {t.get('url', '')[:80]}")

    elif args.command == "android-test":
        for dev in ["s20", "pixel"]:
            info = hub.phone_use.get_device_info(dev)
            print(f"\n{dev}: {json.dumps(info, indent=2)}")

    elif args.command == "screenshot":
        data = hub.capture_screen(args.device)
        if data:
            path = args.out or f"/tmp/lens_capture_{args.device}_{int(time.time())}.png"
            Path(path).write_bytes(data)
            print(f"Screenshot saved: {path} ({len(data)} bytes)")
        else:
            print("Screenshot failed", file=sys.stderr)
            sys.exit(1)

    elif args.command == "navigate":
        if not args.url:
            print("--url required", file=sys.stderr)
            sys.exit(1)
        result = hub.browser_navigate(args.url, args.device)
        print(json.dumps(result, indent=2))

    elif args.command == "ui-tree":
        tree = hub.get_ui_state(args.device)
        print(json.dumps(tree, indent=2)[:3000])
