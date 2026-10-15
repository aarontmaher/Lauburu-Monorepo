#!/usr/bin/env python3
"""
01_apps/screen_lens/src/mesh_universal_remote_hid_server.py
===========================================================
Sovereign Cross-Platform Mesh Universal Remote HID & Adaptive Screen Controller (Port 4006).

Enables Samsung Galaxy S20, Pixel 10 Pro XL, iPad / Linux Tablets, or any desktop/laptop browser
to automatically detect client form factor (Phone, Tablet, Laptop, or Desktop Computer) and adapt
its layout, input modality, and interaction mode across all 7 physical mesh layers:
- L1: Mac Mini M4 Pro (Local Host)
- L2: MacBook Pro (Thunderbolt 4 Bridge)
- L3: Linux Head Node (Intel 2018 Mac Mini 7)
- L4: Linux Tablet (Debian Touch Digitizer)
- L5: MacBook Air (M4 Air - VNC / Metal)
- GW: GL.iNet Router (OpenWrt)
- L7: Samsung S20 (ADB Bridge)

Features & Adaptive Modalities:
1. PWA & Native App Compliant (Web App Manifest, Service Worker, 192/512px Icons)
2. Tri-Modal Form Factor Adaptation:
   - 📱 PHONE: Compact portrait trackpad, 1-handed thumb click bars, haptic vibration, virtual keyboard drawer.
   - 📟 TABLET: Split-deck (Screenview + Gestures), Direct Touch Digitizer (absolute coordinate touch-to-click), Stylus/Pen support.
   - 💻 LAPTOP / DESKTOP: Full-size interactive screenview, direct mouse clicking, mouse wheel scrolling, Physical Keyboard Pass-Through.
3. Native CoreGraphics macOS Ctypes Injection (<1ms input latency, zero dependencies)
4. Absolute Coordinate Digitizer Engine (/api/hid/digitizer_click) for direct touch mapping.
5. Client Device Telemetry Engine (/api/device/report and /api/device/current).
6. Universal Multi-Node Target Routing with One-Click VNC Screen Sharing (/api/node/vnc).
7. Terminal Command Runner for Headless Node Recovery.
"""

import os
import sys
import time
import json
import ctypes
import threading
import subprocess
import urllib.parse
import urllib.request
import socket
import struct
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Tuple
from pathlib import Path

PORT = 4006
ASSETS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/assets")

# ---------------------------------------------------------------------------
# macOS CoreGraphics Ctypes Setup (Zero External Dependencies)
# ---------------------------------------------------------------------------
class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

IS_MACOS = sys.platform == "darwin"
cg = None
cf = None

if IS_MACOS:
    try:
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        cf.CFRelease.restype = None
        
        cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
        cg.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32]
        
        cg.CGEventCreateScrollWheelEvent2.restype = ctypes.c_void_p
        cg.CGEventCreateScrollWheelEvent2.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
        
        cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
        cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
        
        cg.CGEventKeyboardSetUnicodeString.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
        cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        
        cg.CGEventGetLocation.restype = CGPoint
        cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
        
        cg.CGEventCreate.restype = ctypes.c_void_p
        cg.CGEventCreate.argtypes = [ctypes.c_void_p]
        
        cg.CGMainDisplayID.restype = ctypes.c_uint32
        cg.CGDisplayPixelsWide.restype = ctypes.c_size_t
        cg.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
        cg.CGDisplayPixelsHigh.restype = ctypes.c_size_t
        cg.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
        
        cg.CGWarpMouseCursorPosition.argtypes = [CGPoint]
        cg.CGWarpMouseCursorPosition.restype = ctypes.c_int32
    except Exception as e:
        print(f"[WARN] Failed to initialize CoreGraphics ctypes: {e}", file=sys.stderr)

# Virtual Keycodes on macOS
KEYCODES_MACOS = {
    "return": 36, "enter": 36, "tab": 48, "space": 49, "delete": 51,
    "backspace": 51, "escape": 53, "esc": 53, "command": 55, "cmd": 55,
    "shift": 56, "control": 59, "ctrl": 59, "option": 58, "alt": 58,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97
}

# ---------------------------------------------------------------------------
# State & Node Registry
# ---------------------------------------------------------------------------
active_node = "l1_mac_mini"
state_lock = threading.Lock()

last_client_device = {
    "profile": "desktop",
    "label": "💻 LAPTOP / DESKTOP",
    "touch": False,
    "width": 1920,
    "height": 1080,
    "pointer": "fine",
    "updated_at": time.time()
}

NODES: Dict[str, Dict[str, Any]] = {
    "l1_mac_mini": {
        "name": "L1: Mac Mini (M4 Pro Host)",
        "ip": "127.0.0.1",
        "type": "macos_local",
        "vnc_url": "vnc://100.119.199.76:5900",
        "desc": "Primary Host & Memory Governor (24GB RAM)"
    },
    "l2_macbook_pro": {
        "name": "L2: MacBook Pro (M1 Max)",
        "ip": "100.103.212.21",
        "type": "macos_ssh",
        "ssh_host": "macbook-pro",
        "vnc_url": "vnc://100.103.212.21:5900",
        "desc": "10Gbps TB4 Bridge & Model Vault"
    },
    "l3_linux": {
        "name": "L3: Linux Head Node (Intel 2018 Mac Mini 7)",
        "ip": "100.101.39.98",
        "type": "linux_ssh",
        "ssh_host": "linux",
        "desc": "Docker Hub & Compute Gateway"
    },
    "l4_tablet": {
        "name": "L4: Linux Tablet (Debian)",
        "ip": "100.81.92.125",
        "type": "linux_ssh",
        "ssh_host": "tablet",
        "desc": "Mobile Touch DSP & Worker"
    },
    "l5_macbook_air": {
        "name": "L5: MacBook Air (M4)",
        "ip": "100.121.202.34",
        "type": "macos_ssh",
        "ssh_host": "macbook",
        "vnc_url": "vnc://100.121.202.34:5900",
        "desc": "Secondary High-Speed Metal Worker (VNC Port 5900)"
    },
    "l6_pixel": {
        "name": "L6: Pixel 10 Pro XL (Android 15)",
        "ip": "100.73.38.87",
        "type": "android_termux",
        "port": 8022,
        "desc": "8K Vision Stream & Edge TPU"
    },
    "gw_router": {
        "name": "GW: GL.iNet Beryl 7 (OpenWrt)",
        "ip": "192.168.8.1",
        "type": "router_ssh",
        "ssh_host": "root@192.168.8.1",
        "desc": "Core Network Gateway & USB Bridge"
    },
    "l7_samsung": {
        "name": "L7: Samsung S20 (ADB Bridge)",
        "ip": "192.168.8.134",
        "type": "android_adb",
        "serial": "192.168.8.134:5555",
        "desc": "Automated UI Tester & Edge Sensor"
    }
}

# ---------------------------------------------------------------------------
# Native Input Handlers
# ---------------------------------------------------------------------------
def get_macos_screen_dims() -> Tuple[int, int]:
    if not cg:
        return (1920, 1080)
    try:
        main_disp = cg.CGMainDisplayID()
        w = cg.CGDisplayPixelsWide(main_disp)
        h = cg.CGDisplayPixelsHigh(main_disp)
        return (int(w) if w > 0 else 1920, int(h) if h > 0 else 1080)
    except Exception:
        return (1920, 1080)


def get_macos_mouse_pos() -> Tuple[float, float]:
    if not cg:
        return (0.0, 0.0)
    ev = cg.CGEventCreate(None)
    if not ev:
        return (0.0, 0.0)
    loc = cg.CGEventGetLocation(ev)
    if cf:
        cf.CFRelease(ev)
    return (loc.x, loc.y)


def macos_mouse_move(dx: float, dy: float, sensitivity: float = 1.0):
    if not cg:
        return
    cur_x, cur_y = get_macos_mouse_pos()
    new_x = max(0.0, cur_x + dx * sensitivity)
    new_y = max(0.0, cur_y + dy * sensitivity)
    
    pt = CGPoint(new_x, new_y)
    try:
        cg.CGWarpMouseCursorPosition(pt)
    except Exception:
        pass
    ev = cg.CGEventCreateMouseEvent(None, 5, pt, 0)  # 5 = kCGEventMouseMoved
    if ev:
        cg.CGEventPost(0, ev)
        if cf:
            cf.CFRelease(ev)


def macos_digitizer_click(x_pct: float, y_pct: float, button: str = "left", double: bool = False):
    """Direct Absolute Touch Digitizer Injection."""
    if not cg:
        return
    screen_w, screen_h = get_macos_screen_dims()
    target_x = max(0.0, min(float(screen_w), x_pct * screen_w))
    target_y = max(0.0, min(float(screen_h), y_pct * screen_h))
    pt = CGPoint(target_x, target_y)
    try:
        cg.CGWarpMouseCursorPosition(pt)
    except Exception:
        pass
    macos_mouse_click(button=button, double=double)


def macos_mouse_click(button: str = "left", double: bool = False):
    if not cg:
        return
    cur_x, cur_y = get_macos_mouse_pos()
    pt = CGPoint(cur_x, cur_y)
    
    down_type = 1 if button == "left" else 3
    up_type = 2 if button == "left" else 4
    btn_code = 0 if button == "left" else 1
    
    for _ in range(2 if double else 1):
        down = cg.CGEventCreateMouseEvent(None, down_type, pt, btn_code)
        up = cg.CGEventCreateMouseEvent(None, up_type, pt, btn_code)
        if down and up:
            cg.CGEventPost(0, down)
            cg.CGEventPost(0, up)
            if cf:
                cf.CFRelease(down)
                cf.CFRelease(up)
        if double:
            time.sleep(0.05)


def macos_mouse_scroll(dx: float, dy: float):
    if not cg:
        return
    ev = cg.CGEventCreateScrollWheelEvent2(None, 0, 2, int(dy * 2), int(dx * 2), 0)
    if ev:
        cg.CGEventPost(0, ev)
        if cf:
            cf.CFRelease(ev)


def macos_type_text(text: str):
    if not cg or not cf:
        return
    for char in text:
        ev_down = cg.CGEventCreateKeyboardEvent(None, 0, True)
        ev_up = cg.CGEventCreateKeyboardEvent(None, 0, False)
        if ev_down and ev_up:
            utf16 = char.encode("utf-16-le")
            buf = ctypes.create_string_buffer(utf16)
            cg.CGEventKeyboardSetUnicodeString(ev_down, len(utf16) // 2, ctypes.cast(buf, ctypes.c_void_p))
            cg.CGEventKeyboardSetUnicodeString(ev_up, len(utf16) // 2, ctypes.cast(buf, ctypes.c_void_p))
            cg.CGEventPost(0, ev_down)
            cg.CGEventPost(0, ev_up)
            cf.CFRelease(ev_down)
            cf.CFRelease(ev_up)
            time.sleep(0.005)


def macos_send_key(key_name: str):
    key_name = key_name.lower().strip()
    if key_name == "ctrl_c":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "c" using control down'], timeout=2.0)
    elif key_name == "cmd_space":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 49 using command down'], timeout=2.0)
    elif key_name == "cmd_tab":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 48 using command down'], timeout=2.0)
    elif key_name == "cmd_q":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using command down'], timeout=2.0)
    elif key_name == "cmd_w":
        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "w" using command down'], timeout=2.0)
    elif key_name in KEYCODES_MACOS and cg and cf:
        code = KEYCODES_MACOS[key_name]
        down = cg.CGEventCreateKeyboardEvent(None, code, True)
        up = cg.CGEventCreateKeyboardEvent(None, code, False)
        if down and up:
            cg.CGEventPost(0, down)
            cg.CGEventPost(0, up)
            cf.CFRelease(down)
            cf.CFRelease(up)

# ---------------------------------------------------------------------------
# Android ADB & Termux Input Handlers
# ---------------------------------------------------------------------------
ADB_BIN = "/Users/aaron/.local/bin/adb" if os.path.exists("/Users/aaron/.local/bin/adb") else "adb"
os.environ["PATH"] = f"/Users/aaron/.local/bin:/usr/local/bin:/opt/homebrew/bin:{os.environ.get('PATH', '')}"

def adb_command(cmd: str, serial: str = "192.168.8.134:5555") -> str:
    # 1. Try local Wi-Fi ADB
    try:
        res = subprocess.run([ADB_BIN, "-s", "192.168.8.134:5555", "shell", cmd], capture_output=True, text=True, timeout=3.0)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    # 2. Try Tailscale ADB
    try:
        res = subprocess.run([ADB_BIN, "-s", "100.84.40.95:5555", "shell", cmd], capture_output=True, text=True, timeout=3.0)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    # 3. Fallback to router USB ADB
    try:
        res = subprocess.run(["ssh", "-o", "ConnectTimeout=2", "root@192.168.8.1", f"adb -s R3CN40CJJ1R shell {cmd}"], capture_output=True, text=True, timeout=3.0)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    # 4. Fallback to Termux SSH (for terminal commands)
    try:
        res = subprocess.run(["ssh", "-o", "ConnectTimeout=2", "-p", "8022", "100.84.40.95", cmd], capture_output=True, text=True, timeout=3.0)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def pixel_command(cmd: str) -> str:
    try:
        res = subprocess.run(["ssh", "-o", "ConnectTimeout=3", "-p", "8022", "100.73.38.87", cmd], capture_output=True, text=True, timeout=4.0)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

# ---------------------------------------------------------------------------
# Remote SSH & Dispatchers
# ---------------------------------------------------------------------------
def dispatch_hid_event(node_id: str, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    node = NODES.get(node_id, NODES["l1_mac_mini"])
    node_type = node.get("type", "macos_local")
    
    if node_type == "macos_local":
        if event_type == "move":
            macos_mouse_move(data.get("dx", 0.0), data.get("dy", 0.0), data.get("sensitivity", 1.0))
        elif event_type == "digitizer_click":
            x_pct = float(data.get("x_pct", 0.5))
            y_pct = float(data.get("y_pct", 0.5))
            button = data.get("button", "left")
            macos_digitizer_click(x_pct, y_pct, button=button, double=data.get("double", False))
        elif event_type == "click":
            macos_mouse_click(data.get("button", "left"), data.get("double", False))
        elif event_type == "scroll":
            macos_mouse_scroll(data.get("dx", 0.0), data.get("dy", 0.0))
        elif event_type == "type":
            macos_type_text(data.get("text", ""))
        elif event_type == "key":
            macos_send_key(data.get("key", ""))
        return {"status": "ok", "node": node_id, "event": event_type, "x_pct": data.get("x_pct", 0.5), "y_pct": data.get("y_pct", 0.5)}
        
    elif node_type == "android_adb":
        serial = node.get("serial", "192.168.8.134:5555")
        if event_type == "digitizer_click":
            x_pct = float(data.get("x_pct", 0.5))
            y_pct = float(data.get("y_pct", 0.5))
            tx = int(max(0, min(1080, x_pct * 1080)))
            ty = int(max(0, min(2400, y_pct * 2400)))
            adb_command(f"input tap {tx} {ty}", serial)
        elif event_type == "click":
            adb_command("input tap 540 1200", serial)
        elif event_type == "type":
            text = urllib.parse.quote(data.get("text", ""))
            adb_command(f"input text '{text}'", serial)
        elif event_type == "key":
            key = data.get("key", "").lower()
            if key in ["enter", "return"]:
                adb_command("input keyevent 66", serial)
            elif key == "backspace":
                adb_command("input keyevent 67", serial)
            elif key in ["back", "escape", "esc"]:
                adb_command("input keyevent 4", serial)
            elif key in ["home", "cmd_space"]:
                adb_command("input keyevent 3", serial)
        elif event_type in ["scroll", "move"]:
            dx = float(data.get("dx", 0.0))
            dy = float(data.get("dy", 0.0))
            cx, cy = 540, 1200
            ex = int(max(0, min(1080, cx - dx * 2)))
            ey = int(max(0, min(2400, cy - dy * 2)))
            adb_command(f"input swipe {cx} {cy} {ex} {ey} 100", serial)
        return {"status": "ok", "node": node_id, "event": event_type}

    elif node_type == "linux_ssh":
        ssh_host = node.get("ssh_host", node.get("ip"))
        if event_type == "type":
            text = data.get("text", "").strip()
            if text:
                escaped_text = text.replace("'", "'\\''")
                # Direct to physical hardware console (/dev/tty1) and out-of-band stream
                script = f"echo 'linuxmini$ {escaped_text}' | tee -a /dev/tty1 >> /tmp/bluetooth_terminal_stream.ansi 2>/dev/null && ({text}) 2>&1 | tee -a /dev/tty1 >> /tmp/bluetooth_terminal_stream.ansi 2>/dev/null"
                try:
                    subprocess.Popen(["ssh", "-o", "ConnectTimeout=3", ssh_host, script])
                except Exception as e:
                    print(f"[ERROR] Failed to dispatch ssh type command: {e}")
        elif event_type == "key":
            key = data.get("key", "").lower()
            if key == "ctrl_c":
                subprocess.Popen(["ssh", "-o", "ConnectTimeout=2", ssh_host, "pkill -SIGINT -f python3 || true"])
            elif key in ["enter", "return"]:
                subprocess.Popen(["ssh", "-o", "ConnectTimeout=2", ssh_host, "echo '' | tee -a /dev/tty1 >> /tmp/bluetooth_terminal_stream.ansi 2>/dev/null"])
        elif event_type in ["click", "digitizer_click"]:
            x_pct = float(data.get("x_pct", 0.5))
            y_pct = float(data.get("y_pct", 0.5))
            script = f"echo '[TOUCH] Tap at ({x_pct:.2f}, {y_pct:.2f})' >> /tmp/bluetooth_terminal_stream.ansi"
            try:
                subprocess.Popen(["ssh", "-o", "ConnectTimeout=2", ssh_host, script])
            except Exception:
                pass
        return {"status": "ok", "node": node_id, "event": event_type}

    elif node_type == "android_termux":
        if event_type == "type":
            text = urllib.parse.quote(data.get("text", ""))
            pixel_command(f"am broadcast -a com.termux.action.SEND_TEXT --es text '{text}' 2>/dev/null || true")
        elif event_type == "key":
            k = data.get("key", "").lower()
            if k == "ctrl_c":
                pixel_command("pkill -SIGINT -f python3 || true")
        return {"status": "ok", "node": node_id, "event": event_type}
        
    elif "ssh" in node_type:
        ssh_target = node.get("ssh_host", node.get("ip"))
        if event_type == "key":
            k = data.get("key", "").lower()
            if k == "ctrl_c":
                subprocess.Popen(["ssh", "-o", "ConnectTimeout=2", ssh_target, "pkill -SIGINT -f python3 || true"])
        elif event_type == "type":
            text = data.get("text", "").replace("'", "\\'")
            subprocess.Popen(["ssh", "-o", "ConnectTimeout=2", ssh_target, f"echo '{text}'"])
        return {"status": "ok", "node": node_id, "event": event_type}
        
    return {"status": "unsupported", "node": node_id}


def get_frontmost_app_info() -> Dict[str, str]:
    if not IS_MACOS:
        return {"app": "Linux/Headless", "title": "Mesh Console"}
    try:
        script = 'tell application "System Events" to get {name of first process whose frontmost is true}'
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.0)
        app_name = res.stdout.strip() if res.returncode == 0 else "Desktop"
        return {"app": app_name, "title": f"Active: {app_name}"}
    except Exception:
        return {"app": "System", "title": "Active Desktop"}

# ---------------------------------------------------------------------------
# PWA Web App Manifest & Service Worker
# ---------------------------------------------------------------------------
PWA_MANIFEST = {
    "name": "Lauburu Remote HID",
    "short_name": "Mesh Remote",
    "description": "Adaptive Sovereign Cross-Platform Mesh Universal Remote & Screen Controller",
    "start_url": "/",
    "display": "standalone",
    "orientation": "any",
    "background_color": "#090d16",
    "theme_color": "#0f172a",
    "icons": [
        {
            "src": "/icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "/icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable"
        }
    ]
}

SERVICE_WORKER_JS = """
const CACHE_NAME = 'lauburu-remote-v2';
const ASSETS = ['/', '/manifest.json', '/icon-192.png', '/icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
  if (e.request.url.includes('/api/')) {
    e.respondWith(fetch(e.request));
  } else {
    e.respondWith(
      caches.match(e.request).then((res) => res || fetch(e.request))
    );
  }
});
"""

# ---------------------------------------------------------------------------
# HTML5 Adaptive Mobile Touch / Tablet Digitizer / Desktop Controller UI
# ---------------------------------------------------------------------------
HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Mesh Remote">
  <link rel="manifest" href="/manifest.json">
  <link rel="icon" type="image/png" href="/icon-192.png">
  <link rel="apple-touch-icon" href="/icon-192.png">
  <title>Lauburu Universal Remote HID</title>
  <style>
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; margin: 0; padding: 0; }
    :root {
      --bg-main: #090d16;
      --bg-panel: #0f172a;
      --border-color: #1e293b;
      --cyan-neon: #06b6d4;
      --sky-neon: #38bdf8;
      --emerald-neon: #10b981;
      --purple-neon: #8b5cf6;
    }
    body {
      background: var(--bg-main);
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      user-select: none;
      -webkit-user-select: none;
    }
    header {
      background: var(--bg-panel);
      border-bottom: 1px solid var(--border-color);
      padding: 8px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 20;
    }
    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }
    .brand {
      font-size: 13px;
      font-weight: 700;
      color: var(--sky-neon);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .device-badge {
      font-size: 10px;
      padding: 3px 8px;
      border-radius: 9999px;
      font-weight: 700;
      background: rgba(6, 182, 212, 0.15);
      color: var(--sky-neon);
      border: 1px solid rgba(56, 189, 248, 0.3);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .device-badge:hover {
      background: rgba(6, 182, 212, 0.25);
    }
    .node-select-row {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 2px;
      scrollbar-width: none;
    }
    .node-select-row::-webkit-scrollbar { display: none; }
    .node-pill {
      font-size: 11px;
      padding: 4px 10px;
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #334155;
      border-radius: 12px;
      white-space: nowrap;
      cursor: pointer;
      font-weight: 500;
    }
    .node-pill.active {
      background: #0284c7;
      color: #ffffff;
      border-color: var(--sky-neon);
      font-weight: 700;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }
    .control-toolbar {
      display: flex;
      gap: 8px;
      padding: 6px 12px;
      background: #0b1120;
      border-bottom: 1px solid var(--border-color);
      font-size: 11px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      z-index: 15;
    }
    .tool-btn {
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid #334155;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 11px;
      cursor: pointer;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .tool-btn.active {
      background: #2563eb;
      color: #fff;
      border-color: #60a5fa;
    }
    .tool-btn.vnc-btn {
      background: #4f46e5;
      color: #fff;
      border-color: #818cf8;
    }
    
    /* Main Workspace Container */
    #workspace {
      flex: 1;
      position: relative;
      display: flex;
      overflow: hidden;
    }

    /* Trackpad Surface */
    #trackpad {
      flex: 1;
      background: radial-gradient(circle at 50% 50%, #111827 0%, #030712 100%);
      position: relative;
      touch-action: none;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      z-index: 2;
    }
    .trackpad-hint {
      color: #475569;
      font-size: 12px;
      pointer-events: none;
      text-align: center;
      line-height: 1.6;
    }
    #pointer-info {
      position: absolute;
      bottom: 8px;
      right: 12px;
      font-family: monospace;
      font-size: 10px;
      color: #64748b;
      pointer-events: none;
      z-index: 5;
    }

    /* Screenview Container & SVG */
    #screenview-container {
      flex: 1;
      position: relative;
      background: #000;
      display: none;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      cursor: crosshair;
    }
    #screen-svg {
      width: 100%;
      height: 100%;
      object-fit: contain;
      user-select: none;
    }
    .digitizer-ripple {
      position: absolute;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: rgba(56, 189, 248, 0.5);
      border: 2px solid #38bdf8;
      transform: translate(-50%, -50%) scale(0.5);
      animation: ripple 0.4s ease-out forwards;
      pointer-events: none;
      z-index: 30;
    }
    @keyframes ripple {
      to { transform: translate(-50%, -50%) scale(2.0); opacity: 0; }
    }

    /* Bottom Click Bar */
    .click-bar {
      display: grid;
      grid-template-columns: 1fr 1fr;
      height: 54px;
      background: var(--bg-panel);
      border-top: 1px solid var(--border-color);
      z-index: 10;
    }
    .click-btn {
      background: var(--bg-panel);
      color: #94a3b8;
      border: none;
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }
    .click-btn:active {
      background: #1e293b;
      color: var(--sky-neon);
    }
    .click-btn:first-child { border-right: 1px solid var(--border-color); }

    /* Keyboard Drawer */
    #keyboard-drawer {
      background: #0b1120;
      border-top: 1px solid var(--border-color);
      padding: 8px 12px;
      display: none;
      flex-direction: column;
      gap: 8px;
      z-index: 10;
    }
    .quick-keys-row {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .quick-keys-row::-webkit-scrollbar { display: none; }
    .key-btn {
      background: #1e293b;
      color: #f1f5f9;
      border: 1px solid #334155;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
      cursor: pointer;
    }
    .key-btn:active { background: #0284c7; }
    .key-btn.danger { background: #881337; color: #fecdd3; border-color: #be123c; }
    .input-row {
      display: flex;
      gap: 6px;
    }
    .text-input {
      flex: 1;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 6px;
      color: #fff;
      padding: 8px 10px;
      font-size: 13px;
      outline: none;
    }
    .text-input:focus { border-color: var(--sky-neon); }
    .send-btn {
      background: #0284c7;
      color: #fff;
      border: none;
      padding: 0 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }

    /* -----------------------------------------------------------------------
       ADAPTIVE PROFILE STYLES (Phone vs Tablet vs Desktop)
       ----------------------------------------------------------------------- */
    /* 1. Phone Mode: Dedicated Trackpad View */
    body.device-phone #workspace {
      flex-direction: column;
    }
    body.device-phone #trackpad {
      display: flex;
    }
    body.device-phone #screenview-container {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      z-index: 1;
    }
    body.device-phone #trackpad.translucent {
      background: rgba(3, 7, 18, 0.4);
    }

    /* 2. Tablet Mode: Split-Deck Direct Digitizer */
    body.device-tablet #workspace {
      flex-direction: row;
    }
    body.device-tablet #screenview-container {
      display: flex;
      flex: 2;
      border-right: 2px solid var(--border-color);
    }
    body.device-tablet #trackpad {
      display: flex;
      flex: 1;
      max-width: 380px;
      background: #0b1120;
    }
    body.device-tablet .click-bar {
      display: none; /* Direct tap on tablet replaces bottom click bar */
    }
    body.device-tablet #keyboard-drawer {
      display: flex;
    }

    /* 3. Laptop / Desktop Mode: Interactive Monitor & Keyboard Pass-Through */
    body.device-desktop #workspace {
      flex-direction: row;
    }
    body.device-desktop #screenview-container {
      display: flex;
      flex: 1;
    }
    body.device-desktop #trackpad {
      display: none; /* Physical mouse replaces virtual trackpad on desktop */
    }
    body.device-desktop .click-bar {
      display: none; /* Physical mouse buttons active */
    }
    body.device-desktop #keyboard-drawer {
      display: flex;
    }
    body.device-desktop .trackpad-hint {
      display: none;
    }
    .desktop-key-banner {
      display: none;
      font-size: 11px;
      color: #34d399;
      background: rgba(5, 150, 105, 0.15);
      border: 1px solid rgba(52, 211, 153, 0.3);
      padding: 4px 8px;
      border-radius: 4px;
    }
    body.device-desktop .desktop-key-banner {
      display: block;
    }
  </style>
</head>
<body class="device-desktop">
  <header>
    <div class="header-top">
      <div class="brand">
        <img src="/icon-192.png" alt="Logo" style="width: 20px; height: 20px; border-radius: 4px;" />
        <span>LAUBURU REMOTE HID</span>
      </div>
      <div style="display: flex; gap: 6px; align-items: center;">
        <div id="device-mode-badge" class="device-badge" onclick="cycleFormFactor()">
          <span>⚡ AUTO:</span> <span id="detected-profile-label">DESKTOP</span>
        </div>
        <div class="desktop-key-banner">⌨️ Physical Keys Active</div>
        <button id="install-pwa-btn" class="tool-btn" style="display: none; background: #059669; color: #fff;" onclick="installPWA()">📲 Install</button>
      </div>
    </div>
    <div class="node-select-row" id="node-list">
      <!-- Nodes populated via JS -->
    </div>
  </header>

  <div class="control-toolbar">
    <div style="display: flex; gap: 8px; align-items: center;">
      <span style="color: #64748b;">Target: </span>
      <strong id="active-node-name" style="color: var(--sky-neon);">L1: Mac Mini</strong>
    </div>
    <div style="display: flex; gap: 6px;">
      <button class="tool-btn vnc-btn" id="vnc-launch-btn" onclick="launchVNC()">🖥️ Open VNC Screen</button>
      <button class="tool-btn" id="toggle-screen-btn" onclick="toggleScreenview()">👁️ Screen: ON</button>
      <button class="tool-btn" id="monitor-mode-btn" onclick="toggleMonitorMode()" style="background: #10b981; color: white; border-color: #34d399;">📺 Monitor Mode</button>
      <button class="tool-btn" id="toggle-kb-btn" onclick="toggleKeyboard()">⌨️ Keys</button>
    </div>
  </div>

  <div id="workspace">
    <!-- Screenview Overlay / Direct Digitizer Canvas -->
    <div id="screenview-container">
      <img id="screen-svg" src="/api/screen/preview.svg" alt="Live Screenview" />
      <button id="exit-monitor-btn" onclick="toggleMonitorMode()" style="display: none; position: absolute; bottom: 20px; right: 20px; z-index: 9999; padding: 12px 24px; background: rgba(239,68,68,0.8); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; backdrop-filter: blur(4px);">Exit Monitor Mode</button>
    </div>

    <!-- Virtual Trackpad Surface -->
    <div id="trackpad">
      <div class="trackpad-hint" id="trackpad-guide">
        👆 1-Finger: Move Pointer<br>
        👇 1-Finger Tap: Left Click<br>
        ✌️ 2-Finger Tap: Right Click<br>
        📜 2-Finger Drag: Smooth Scroll
      </div>
      <div id="pointer-info">X: 0 | Y: 0</div>
    </div>
  </div>

  <!-- Keyboard Drawer -->
  <div id="keyboard-drawer">
    <div class="quick-keys-row">
      <button class="key-btn danger" onclick="sendKey('ctrl_c')">Ctrl+C (Kill)</button>
      <button class="key-btn" onclick="sendKey('enter')">Enter ↵</button>
      <button class="key-btn" onclick="sendKey('tab')">Tab ⇥</button>
      <button class="key-btn" onclick="sendKey('esc')">Esc</button>
      <button class="key-btn" onclick="sendKey('cmd_space')">⌘+Space (Spotlight)</button>
      <button class="key-btn" onclick="sendKey('cmd_tab')">⌘+Tab</button>
      <button class="key-btn" onclick="sendKey('cmd_w')">⌘+W</button>
      <button class="key-btn" onclick="sendKey('cmd_q')">⌘+Q</button>
    </div>
    <div class="input-row">
      <input type="text" id="type-input" class="text-input" placeholder="Type text or command..." autocomplete="off" autocorrect="off" autocapitalize="off" />
      <button class="send-btn" onclick="sendTypedText()">Send</button>
    </div>
  </div>

  <!-- Bottom Click Bar (Visible in Phone Mode) -->
  <div class="click-bar">
    <button class="click-btn" onclick="sendClick('left')">LEFT CLICK</button>
    <button class="click-btn" onclick="sendClick('right')">RIGHT CLICK</button>
  </div>

  <script>
    let activeNode = 'l1_mac_mini';
    let screenviewEnabled = true;
    let keyboardEnabled = true;
    let sensitivity = 1.25;
    let manualProfileOverride = null; // null for auto, or 'phone' | 'tablet' | 'desktop'
    let currentProfile = 'desktop';

    // -------------------------------------------------------------------------
    // Device Form Factor & Input Modality Detection Engine
    // -------------------------------------------------------------------------
    function detectDeviceFormFactor() {
      if (manualProfileOverride) {
        return manualProfileOverride;
      }
      const hasTouch = ('ontouchstart' in window) || 
                       (navigator.maxTouchPoints > 0) || 
                       (window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
      const hasFinePointer = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
      const width = window.innerWidth || screen.width;
      const height = window.innerHeight || screen.height;
      const minDim = Math.min(width, height);
      const ua = navigator.userAgent.toLowerCase();
      const isTabletUA = /ipad|tablet|(android(?!.*mobile))/i.test(ua);

      if (hasTouch) {
        if (minDim >= 600 || isTabletUA || (width >= 768 && height >= 600)) {
          return 'tablet';
        }
        return 'phone';
      }
      return 'desktop';
    }

    function applyAdaptiveProfile() {
      currentProfile = detectDeviceFormFactor();
      document.body.classList.remove('device-phone', 'device-tablet', 'device-desktop');
      document.body.classList.add('device-' + currentProfile);

      const labelSpan = document.getElementById('detected-profile-label');
      const badge = document.getElementById('device-mode-badge');
      const prefix = manualProfileOverride ? '🔒 MANUAL: ' : '⚡ AUTO: ';

      if (currentProfile === 'phone') {
        labelSpan.textContent = 'PHONE (Touch Trackpad)';
        badge.style.borderColor = '#06b6d4';
        badge.style.color = '#38bdf8';
        document.getElementById('screenview-container').style.display = screenviewEnabled ? 'block' : 'none';
        if (screenviewEnabled) {
          document.getElementById('trackpad').classList.add('translucent');
        } else {
          document.getElementById('trackpad').classList.remove('translucent');
        }
        document.getElementById('trackpad').style.display = 'flex';
      } else if (currentProfile === 'tablet') {
        labelSpan.textContent = 'TABLET (Direct Digitizer)';
        badge.style.borderColor = '#8b5cf6';
        badge.style.color = '#c084fc';
        document.getElementById('screenview-container').style.display = 'flex';
        document.getElementById('trackpad').classList.remove('translucent');
        document.getElementById('trackpad').style.display = 'flex';
      } else {
        labelSpan.textContent = 'LAPTOP / DESKTOP (Mouse & Keys)';
        badge.style.borderColor = '#10b981';
        badge.style.color = '#34d399';
        document.getElementById('screenview-container').style.display = 'flex';
        document.getElementById('trackpad').style.display = 'none';
      }
      badge.firstElementChild.textContent = prefix;

      // Report telemetry to server
      fetch('/api/device/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: currentProfile,
          touch: ('ontouchstart' in window) || (navigator.maxTouchPoints > 0),
          width: window.innerWidth,
          height: window.innerHeight,
          maxTouchPoints: navigator.maxTouchPoints || 0,
          manual: Boolean(manualProfileOverride)
        })
      }).catch(() => {});
    }

    function cycleFormFactor() {
      const modes = [null, 'phone', 'tablet', 'desktop'];
      const currentIndex = modes.indexOf(manualProfileOverride);
      manualProfileOverride = modes[(currentIndex + 1) % modes.length];
      applyAdaptiveProfile();
    }

    window.addEventListener('resize', applyAdaptiveProfile);
    window.addEventListener('orientationchange', applyAdaptiveProfile);

    // -------------------------------------------------------------------------
    // Physical Keyboard Pass-Through (Laptop / Desktop Modality)
    // -------------------------------------------------------------------------
    window.addEventListener('keydown', (e) => {
      if (currentProfile !== 'desktop') return;
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      const key = e.key;
      if (key === 'Escape') {
        sendKey('esc');
        e.preventDefault();
      } else if (key === 'Enter') {
        sendKey('enter');
        e.preventDefault();
      } else if (key === 'Tab') {
        sendKey('tab');
        e.preventDefault();
      } else if (key === 'Backspace') {
        sendKey('delete');
        e.preventDefault();
      } else if (e.ctrlKey && key.toLowerCase() === 'c') {
        sendKey('ctrl_c');
        e.preventDefault();
      } else if ((e.metaKey || e.ctrlKey) && key.toLowerCase() === ' ') {
        sendKey('cmd_space');
        e.preventDefault();
      } else if (key.length === 1 && !e.metaKey && !e.ctrlKey) {
        postHID('type', { text: key });
        e.preventDefault();
      }
    });

    // -------------------------------------------------------------------------
    // Direct Touch Digitizer on Screenview Canvas
    // -------------------------------------------------------------------------
    const screenContainer = document.getElementById('screenview-container');

    function handleDirectDigitizer(clientX, clientY, button = 'left') {
      const rect = screenContainer.getBoundingClientRect();
      const x_pct = Math.max(0.0, Math.min(1.0, (clientX - rect.left) / rect.width));
      const y_pct = Math.max(0.0, Math.min(1.0, (clientY - rect.top) / rect.height));

      // Visual Ripple Indicator
      const ripple = document.createElement('div');
      ripple.className = 'digitizer-ripple';
      ripple.style.left = clientX + 'px';
      ripple.style.top = clientY + 'px';
      document.body.appendChild(ripple);
      setTimeout(() => ripple.remove(), 400);

      // Haptic Vibration if on mobile/tablet
      if ('vibrate' in navigator) {
        navigator.vibrate(15);
      }

      postHID('digitizer_click', { x_pct, y_pct, button });
    }

    screenContainer.addEventListener('click', (e) => {
      handleDirectDigitizer(e.clientX, e.clientY, e.button === 2 ? 'right' : 'left');
    });

    screenContainer.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      handleDirectDigitizer(e.clientX, e.clientY, 'right');
    });

    screenContainer.addEventListener('wheel', (e) => {
      if (currentProfile === 'desktop') {
        e.preventDefault();
        postHID('scroll', { dx: e.deltaX * 0.5, dy: e.deltaY * 0.5 });
      }
    }, { passive: false });

    // Touch digitizer for tablets
    screenContainer.addEventListener('touchstart', (e) => {
      if (currentProfile === 'tablet') {
        e.preventDefault();
        if (e.touches.length === 1) {
          handleDirectDigitizer(e.touches[0].clientX, e.touches[0].clientY, 'left');
        }
      }
    }, { passive: false });

    // -------------------------------------------------------------------------
    // Trackpad Multi-Touch Listeners (Phone & Tablet Relative Touch)
    // -------------------------------------------------------------------------
    let lastX = 0, lastY = 0;
    let isTracking = false;
    let touchCount = 0;
    let touchStartTime = 0;
    let hasMoved = false;

    const trackpad = document.getElementById('trackpad');

    trackpad.addEventListener('touchstart', (e) => {
      e.preventDefault();
      touchCount = e.touches.length;
      touchStartTime = Date.now();
      hasMoved = false;

      if (touchCount === 1) {
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
        isTracking = true;
      } else if (touchCount === 2) {
        lastX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        lastY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        isTracking = true;
      }
    }, { passive: false });

    trackpad.addEventListener('touchmove', (e) => {
      e.preventDefault();
      if (!isTracking) return;

      if (e.touches.length === 1) {
        const curX = e.touches[0].clientX;
        const curY = e.touches[0].clientY;
        const dx = (curX - lastX) * sensitivity;
        const dy = (curY - lastY) * sensitivity;

        if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
          hasMoved = true;
          postHID('move', { dx, dy, sensitivity });
        }
        lastX = curX;
        lastY = curY;
      } else if (e.touches.length === 2) {
        const curY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const curX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        const scrollDY = (curY - lastY) * sensitivity * 1.5;
        const scrollDX = (curX - lastX) * sensitivity * 1.5;

        if (Math.abs(scrollDY) > 1.0 || Math.abs(scrollDX) > 1.0) {
          hasMoved = true;
          postHID('scroll', { dx: scrollDX, dy: scrollDY });
        }
        lastX = curX;
        lastY = curY;
      }
    }, { passive: false });

    trackpad.addEventListener('touchend', (e) => {
      e.preventDefault();
      const duration = Date.now() - touchStartTime;

      if (!hasMoved && duration < 300) {
        if (touchCount === 1) {
          sendClick('left');
          if ('vibrate' in navigator) navigator.vibrate(10);
        } else if (touchCount === 2) {
          sendClick('right');
          if ('vibrate' in navigator) navigator.vibrate([10, 20]);
        }
      }
      isTracking = false;
      touchCount = e.touches.length;
    }, { passive: false });

    // -------------------------------------------------------------------------
    // Node Management & Actions
    // -------------------------------------------------------------------------
    const NODES = {
      'l1_mac_mini': '🖥️ L1: Mac Mini',
      'l2_macbook_pro': '💻 L2: MacBook Pro',
      'l3_linux': '🐧 L3: Linux Node',
      'l4_tablet': '📟 L4: Linux Tablet',
      'l5_macbook_air': '💻 L5: MacBook Air (VNC)',
      'l6_pixel': '📱 L6: Pixel 10 Pro XL',
      'gw_router': '🌐 GW: Router',
      'l7_samsung': '🤖 L7: Samsung S20'
    };

    function renderNodeButtons() {
      const container = document.getElementById('node-list');
      container.innerHTML = '';
      for (const [key, label] of Object.entries(NODES)) {
        const btn = document.createElement('button');
        btn.className = 'node-pill' + (key === activeNode ? ' active' : '');
        btn.textContent = label;
        btn.onclick = () => selectNode(key);
        container.appendChild(btn);
      }
    }

    function selectNode(key) {
      if (activeNode !== key) {
        currentStreamNode = null;
      }
      activeNode = key;
      document.getElementById('active-node-name').textContent = NODES[key];
      renderNodeButtons();
      fetch('/api/node/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node: key })
      });
      refreshScreen();
    }

    function launchVNC() {
      fetch('/api/node/vnc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node: activeNode })
      }).then(r => r.json()).then(data => {
        if (data.status === 'ok') {
          let targetUrl = data.vnc_url;
          // Force Bluetooth PAN or local IP if browsing the host directly
          if (activeNode === 'l1_mac_mini') {
            targetUrl = 'vnc://' + window.location.hostname + ':5900';
          }
          window.location.href = targetUrl;
        } else {
          alert(data.message || "VNC not supported for this node.");
        }
      }).catch(() => {});
    }

    function toggleScreenview() {
      screenviewEnabled = !screenviewEnabled;
      const btn = document.getElementById('toggle-screen-btn');
      const container = document.getElementById('screenview-container');
      const img = document.getElementById('screen-svg');
      if (!screenviewEnabled) {
        btn.textContent = '👁️ Screen: OFF';
        btn.style.opacity = '0.5';
        container.style.display = 'none';
        img.src = '';
        currentStreamNode = null;
      } else {
        btn.textContent = '👁️ Screen: ON';
        btn.style.opacity = '1';
        container.style.display = 'block';
        currentStreamNode = null;
        refreshScreen();
      }
      btn.classList.toggle('active', screenviewEnabled);
      if (currentProfile === 'phone') {
        container.style.display = screenviewEnabled ? 'block' : 'none';
        if (screenviewEnabled) {
          document.getElementById('trackpad').classList.add('translucent');
        } else {
          document.getElementById('trackpad').classList.remove('translucent');
        }
      }
    }

    let monitorModeActive = false;
    function toggleMonitorMode() {
      monitorModeActive = !monitorModeActive;
      const trackpad = document.getElementById('trackpad');
      const drawer = document.getElementById('keyboard-drawer');
      const header = document.getElementById('top-bar');
      const container = document.getElementById('screenview-container');
      const exitBtn = document.getElementById('exit-monitor-btn');

      if (monitorModeActive) {
        trackpad.style.display = 'none';
        drawer.style.display = 'none';
        header.style.display = 'none';
        container.style.display = 'block';
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.zIndex = '9998';
        exitBtn.style.display = 'block';
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
      } else {
        trackpad.style.display = 'block';
        drawer.style.display = keyboardEnabled ? 'flex' : 'none';
        header.style.display = 'flex';
        container.style.position = 'absolute';
        container.style.width = '100%';
        container.style.height = '100%';
        container.style.zIndex = '1';
        exitBtn.style.display = 'none';
        if (currentProfile === 'phone' && !screenviewEnabled) {
          container.style.display = 'none';
        }
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(() => {});
        }
      }
    }

    function toggleKeyboard() {
      keyboardEnabled = !keyboardEnabled;
      const drawer = document.getElementById('keyboard-drawer');
      const btn = document.getElementById('toggle-kb-btn');
      drawer.style.display = keyboardEnabled ? 'flex' : 'none';
      btn.classList.toggle('active', keyboardEnabled);
      if (keyboardEnabled) document.getElementById('type-input').focus();
    }

    function postHID(endpoint, payload) {
      payload.node = activeNode;
      fetch('/api/hid/' + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).catch(() => {});
    }

    function sendClick(button) {
      postHID('click', { button });
    }

    function sendKey(key) {
      postHID('key', { key });
    }

    function sendTypedText() {
      const input = document.getElementById('type-input');
      const text = input.value;
      if (!text) return;
      postHID('type', { text });
      input.value = '';
    }

    document.getElementById('type-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendTypedText();
    });

    // Screen Refresh Loop
    let currentStreamNode = null;
    function refreshScreen() {
      if (document.hidden || !screenviewEnabled) return;
      const img = document.getElementById('screen-svg');
      if (activeNode === 'l1_mac_mini') {
        if (currentStreamNode !== 'l1_mac_mini') {
          img.src = 'http://' + window.location.hostname + ':4003/stream.mjpg';
          currentStreamNode = 'l1_mac_mini';
        }
        return;
      } else if (activeNode === 'l3_linux') {
        if (currentStreamNode !== 'l3_linux') {
          img.src = '/api/screen/mjpeg_proxy?node=l3_linux';
          currentStreamNode = 'l3_linux';
        }
        return;
      }

      // Fallback to SVG
      currentStreamNode = null;
      img.src = '/api/screen/preview.svg?t=' + Date.now() + '&node=' + activeNode;
    }
    setInterval(() => {
      if (!currentStreamNode) refreshScreen();
    }, 500);

    // Live Telemetry Updates
    setInterval(() => {
      fetch('/api/status')
        .then(r => r.json())
        .then(data => {
          document.getElementById('pointer-info').textContent =
            `Pointer: (${Math.round(data.mouse.x)}, ${Math.round(data.mouse.y)}) • App: ${data.frontmost.app}`;
        }).catch(() => {});
    }, 1000);

    // Initial Setup
    renderNodeButtons();
    applyAdaptiveProfile();
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------
class RemoteHIDHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
        elif path == "/manifest.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.end_headers()
        elif path in ["/sw.js", "/service-worker.js"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.end_headers()
        elif path in ["/icon-192.png", "/icon-512.png"]:
            icon_file = ASSETS_DIR / path.strip("/")
            if icon_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
            else:
                self.send_error(404, "Icon Not Found")
        elif path in ["/api/status", "/api/device/current"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
        elif path == "/api/screen/preview.svg":
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path in ["/", "/index.html"]:
            host = self.headers.get("Host", "127.0.0.1:4006").split(":")[0]
            self.send_response(302)
            self.send_header("Location", f"http://{host}:4003/")
            self.end_headers()
            return

        elif path in ["/health", "/api/health"]:
            payload = json.dumps({"status": "HEALTHY", "service": "mesh_universal_remote_hid_server", "port": 4006, "unified_upstream": 4003}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        elif path == "/api/screen/mjpeg_proxy":
            query = urllib.parse.parse_qs(parsed.query)
            node_id = query.get("node", [""])[0]
            if node_id == "l3_linux":
                target_url = "http://100.101.39.98:4003/stream.mjpg"
                try:
                    req = urllib.request.Request(target_url)
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        self.send_response(200)
                        for k, v in resp.headers.items():
                            self.send_header(k, v)
                        self.end_headers()
                        while True:
                            chunk = resp.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            self.wfile.flush()
                except Exception as e:
                    self.send_error(502, f"Bad Gateway: {e}")
                return
            self.send_error(404, "Not Found")
            return
            
        elif path == "/manifest.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.end_headers()
            self.wfile.write(json.dumps(PWA_MANIFEST, indent=2).encode("utf-8"))
            return
            
        elif path in ["/sw.js", "/service-worker.js"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.end_headers()
            self.wfile.write(SERVICE_WORKER_JS.encode("utf-8"))
            return
            
        elif path in ["/icon-192.png", "/icon-512.png"]:
            icon_file = ASSETS_DIR / path.strip("/")
            if icon_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                with open(icon_file, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Icon Not Found")
                return

        elif path == "/api/device/current":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(last_client_device).encode("utf-8"))
            return

        elif path == "/api/status":
            cur_x, cur_y = get_macos_mouse_pos()
            frontmost = get_frontmost_app_info()
            resp = {
                "active_node": active_node,
                "mouse": {"x": cur_x, "y": cur_y},
                "frontmost": frontmost,
                "nodes": list(NODES.keys()),
                "client_device": last_client_device
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return
            
        elif path == "/api/screen/preview.svg":
            cur_x, cur_y = get_macos_mouse_pos()
            frontmost = get_frontmost_app_info()
            svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%">
              <rect width="1920" height="1080" fill="#0f172a"/>
              <rect x="40" y="40" width="1840" height="1000" rx="12" fill="#1e293b" stroke="#334155" stroke-width="2"/>
              <rect x="40" y="40" width="1840" height="48" rx="12" fill="#0b1120"/>
              <circle cx="70" cy="64" r="8" fill="#ef4444"/>
              <circle cx="95" cy="64" r="8" fill="#eab308"/>
              <circle cx="120" cy="64" r="8" fill="#22c55e"/>
              <text x="160" y="70" fill="#38bdf8" font-family="-apple-system, sans-serif" font-size="18" font-weight="bold">
                {frontmost.get("app", "Desktop")} — Lauburu Mesh Sovereign Workspace
              </text>
              <text x="60" y="160" fill="#94a3b8" font-family="monospace" font-size="24">
                Target Node: {active_node.upper()} ({NODES.get(active_node, {}).get("name", "")})
              </text>
              <text x="60" y="210" fill="#64748b" font-family="monospace" font-size="18">
                Mouse Coordinates: X={cur_x:.1f}, Y={cur_y:.1f}
              </text>
              <!-- Mouse Cursor Indicator -->
              <g transform="translate({cur_x}, {cur_y})">
                <circle cx="0" cy="0" r="16" fill="rgba(56, 189, 248, 0.4)" stroke="#38bdf8" stroke-width="3"/>
                <polygon points="0,0 20,15 12,18 16,28 10,30 6,20 0,25" fill="#38bdf8" stroke="#ffffff" stroke-width="1.5"/>
              </g>
            </svg>"""
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(svg.encode("utf-8"))
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            data = json.loads(post_data.decode("utf-8"))
        except Exception:
            data = {}
            
        global active_node, last_client_device

        if path == "/api/device/report":
            with state_lock:
                last_client_device = {
                    "profile": data.get("profile", "desktop"),
                    "touch": bool(data.get("touch", False)),
                    "width": int(data.get("width", 1920)),
                    "height": int(data.get("height", 1080)),
                    "maxTouchPoints": int(data.get("maxTouchPoints", 0)),
                    "manual": bool(data.get("manual", False)),
                    "updated_at": time.time()
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "client_device": last_client_device}).encode("utf-8"))
            return

        elif path == "/api/node/select":
            selected = data.get("node", "l1_mac_mini")
            if selected in NODES:
                with state_lock:
                    active_node = selected
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "active_node": active_node}).encode("utf-8"))
            return

        elif path == "/api/node/vnc":
            selected = data.get("node", active_node)
            node_info = NODES.get(selected, {})
            if node_info.get("type") == "linux_ssh":
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Headless node. Use Terminal Stream."}).encode("utf-8"))
                return
            vnc_url = node_info.get("vnc_url", f"vnc://{node_info.get('ip', '127.0.0.1')}:5900")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "node": selected, "vnc_url": vnc_url}).encode("utf-8"))
            return

        elif path.startswith("/api/hid/"):
            event_type = path.replace("/api/hid/", "")
            target_node = data.get("node", active_node)
            # Forward directly to unified engine on Port 4003
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:4003/api/hid/{event_type}",
                    data=json.dumps(data).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
            except Exception:
                res = dispatch_hid_event(target_node, event_type, data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        elif path == "/api/terminal/run":
            target_node = data.get("node", active_node)
            cmd = data.get("cmd", "")
            out = ""
            if target_node == "l1_mac_mini":
                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5.0)
                    out = res.stdout + res.stderr
                except Exception as e:
                    out = str(e)
            elif target_node == "l6_pixel":
                out = pixel_command(cmd)
            elif "ssh" in NODES.get(target_node, {}).get("type", ""):
                ssh_host = NODES[target_node].get("ssh_host", NODES[target_node]["ip"])
                try:
                    res = subprocess.run(["ssh", "-o", "ConnectTimeout=3", ssh_host, cmd], capture_output=True, text=True, timeout=5.0)
                    out = res.stdout + res.stderr
                except Exception as e:
                    out = str(e)
            elif target_node == "l7_samsung":
                out = adb_command(cmd)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"output": out}).encode("utf-8"))
            return

        self.send_error(404, "Not Found")


def run_udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", PORT))
        print(f"[LAUBURU HID] Ultra-Low Latency UDP Mouse Receiver active on UDP:{PORT}", flush=True)
        while True:
            data, _ = sock.recvfrom(64)
            if not data:
                continue
            header = data[0:1]
            if header == b'M' and len(data) >= 3:
                dx, dy = struct.unpack("bb", data[1:3])
                macos_mouse_move(float(dx), float(-dy), 1.0)
            elif header == b'C' and len(data) >= 2:
                btn_code = data[1:2]
                btn = "left" if btn_code == b'L' else "right"
                macos_mouse_click(btn)
            elif header == b'S' and len(data) >= 2:
                dy = struct.unpack("b", data[1:2])[0]
                macos_mouse_scroll(0.0, float(dy))
    except Exception as e:
        print(f"[WARN] UDP mouse receiver error: {e}", file=sys.stderr)


def run_server():
    udp_thread = threading.Thread(target=run_udp_listener, daemon=True)
    udp_thread.start()
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", PORT), RemoteHIDHandler)
    print(f"[LAUBURU HID] Remote Controller Server listening on http://0.0.0.0:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
