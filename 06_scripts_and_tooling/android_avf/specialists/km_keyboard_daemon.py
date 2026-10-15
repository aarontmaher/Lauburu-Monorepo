#!/usr/bin/env python3
"""
06_scripts_and_tooling/android_avf/specialists/km_keyboard_daemon.py
=====================================================================
Sovereign KM Keyboard Specialist (Android KeyMapper + Screen Lens Integration)
-----------------------------------------------------------------------------
Incorporates Screen Lens visual perception and AI assistance directly INTO the
Android KM Keyboard / KeyMapper daemon.

Capabilities:
1. Ingests KeyMapper / IME logcat and macro events via Shizuku.
2. Bidirectional Screen Lens Integration:
   - Queries Screen Lens Visual Autocomplete (/api/keyboard/lens/autocomplete)
   - Triggers AI Keystroke Copilot (/api/keyboard/lens/ai_copilot)
   - Executes Type-to-Jump Navigation (/api/keyboard/lens/jump/execute)
   - Cycles Mesh Keyboard Routing Destination (/api/keyboard/lens/cycle_target)
3. Local TinyLM Fallback: Evaluates on-device keystrokes when offline.
"""

import os
import sys
import time
import json
import shlex
import asyncio
import subprocess
from typing import Dict, List, Any, Optional

import httpx

# Endpoints
L1_HOST = os.environ.get("L1_HOST", "100.119.199.76")
SCREEN_LENS_BASE = os.environ.get("SCREEN_LENS_BASE", f"http://{L1_HOST}:4006")
AVF_TINYLM_API = os.environ.get("AVF_TINYLM_API", "http://10.86.187.34:8080/completion")

KM_MACRO_TRIGGERS = {
    "TRIGGER_LENS_AUTOFILL": "/api/keyboard/lens/autofill",
    "TRIGGER_LENS_AI": "/api/keyboard/lens/ai_copilot",
    "TRIGGER_LENS_JUMP": "/api/keyboard/lens/jump/index",
    "TRIGGER_MESH_CYCLE": "/api/keyboard/lens/cycle_target",
    "TRIGGER_OCR_SUGGEST": "/api/keyboard/lens/autocomplete",
    "TRIGGER_MACRODROID_AUTOMATION": "MACRODROID",
    "TRIGGER_LENS_SCRIPT": "SCRIPT"
}

class KMKeyboardLensClient:
    """Client for querying Screen Lens directly from the keyboard workflow."""

    def __init__(self, base_url: str = SCREEN_LENS_BASE):
        self.base_url = base_url
        self.last_sync_time = 0.0
        self.cached_suggestions: List[Dict[str, Any]] = []

    async def trigger_macrodroid(self, macro_name: str) -> Dict[str, Any]:
        """Triggers MacroDroid webhook running on local AVF."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post("http://127.0.0.1:8085", json={"action": "run_macro", "macro": macro_name})
                if res.status_code == 200:
                    return {"status": "ok", "macro": macro_name}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Failed to trigger MacroDroid"}

    async def run_lens_script(self, script_name: str) -> Dict[str, Any]:
        """Triggers a Screen Lens automation script on the Mac Mini."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.base_url}/api/automation/run", json={"script": script_name})
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Failed to trigger Lens script"}

    async def get_visual_autocomplete(self, prefix: str) -> List[Dict[str, Any]]:
        """Queries Screen Lens on Mac Mini for on-screen words matching current typing."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/keyboard/lens/autocomplete",
                    json={"prefix": prefix}
                )
                if res.status_code == 200:
                    data = res.json()
                    self.cached_suggestions = data.get("suggestions", [])
                    return self.cached_suggestions
        except Exception:
            pass
        return []

    async def trigger_ai_copilot(self, prompt: str) -> Dict[str, Any]:
        """Calls Screen Lens AI Keystroke Copilot (Hermes-3 on Metal) with visual screen context."""
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/keyboard/lens/ai_copilot",
                    json={"prefix": prompt}
                )
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            # Fallback to local AVF TinyLM
            return await self._fallback_tinylm(prompt)
        return {"status": "error", "message": "Failed to reach AI Copilot"}

    async def trigger_type_to_jump(self, tag: Optional[str] = None) -> Dict[str, Any]:
        """Indexes or executes a Type-to-Jump click via Screen Lens."""
        endpoint = "/api/keyboard/lens/jump/execute" if tag else "/api/keyboard/lens/jump/index"
        payload = {"tag": tag} if tag else {}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.base_url}{endpoint}", json=payload)
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Jump request failed"}

    async def cycle_mesh_target(self) -> Dict[str, Any]:
        """Switches physical/KM keyboard routing destination across mesh nodes."""
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                res = await client.post(f"{self.base_url}/api/keyboard/lens/cycle_target", json={})
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Target switch failed"}

    async def forward_event(self, raw_line: str) -> Dict[str, Any]:
        """Ingests raw KeyMapper event into Screen Lens Keyboard ring buffer."""
        payload = {
            "source": "android_km_keyboard_daemon",
            "raw_log": raw_line,
            "key": raw_line.split(":")[-1].strip() if ":" in raw_line else raw_line,
            "event_type": "keymapper_logcat",
            "target_node": "l1_mac_mini"
        }
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.post(f"{self.base_url}/api/hid/km_keyboard/event", json=payload)
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return {"status": "offline_buffered"}

    async def _fallback_tinylm(self, prompt: str) -> Dict[str, Any]:
        """Local AVF TinyLM prediction fallback."""
        payload = {"prompt": f"Keyboard completion for: {prompt}", "n_predict": 24}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(AVF_TINYLM_API, json=payload)
                if resp.status_code == 200:
                    return {
                        "status": "ok",
                        "completion": resp.json().get("content", "").strip(),
                        "source": "avf_tinylm_fallback"
                    }
        except Exception:
            pass
        return {"status": "error", "message": "All AI backends unavailable"}


km_client = KMKeyboardLensClient()


def process_keymapper_line(line: str):
    """Processes a single line from KeyMapper logcat or stdin."""
    stripped = line.strip()
    if not stripped:
        return

    # Check for direct Screen Lens macro triggers
    for macro_name, endpoint in KM_MACRO_TRIGGERS.items():
        if macro_name in stripped:
            print(f"[KM Specialist] Triggering Screen Lens feature: {macro_name}")
            if macro_name == "TRIGGER_LENS_AI":
                res = asyncio.run(km_client.trigger_ai_copilot("Next action"))
                print(f"[KM AI] Suggestion: {res.get('completion')}")
            elif macro_name == "TRIGGER_MESH_CYCLE":
                res = asyncio.run(km_client.cycle_mesh_target())
                print(f"[KM Mesh Router] Active Destination: {res.get('active_target')}")
            elif macro_name == "TRIGGER_LENS_JUMP":
                res = asyncio.run(km_client.trigger_type_to_jump())
                print(f"[KM Jump] Targets indexed: {res.get('total_jump_targets')}")
            elif macro_name == "TRIGGER_MACRODROID_AUTOMATION":
                # Extract macro name from log if available, else use a default
                macro_target = "LENS_MACRO_1"
                parts = stripped.split("MACRO:")
                if len(parts) > 1:
                    macro_target = parts[1].strip()
                res = asyncio.run(km_client.trigger_macrodroid(macro_target))
                print(f"[KM MacroDroid] Dispatched intent: {res}")
            elif macro_name == "TRIGGER_LENS_SCRIPT":
                script_target = "default_script"
                parts = stripped.split("SCRIPT:")
                if len(parts) > 1:
                    script_target = parts[1].strip()
                res = asyncio.run(km_client.run_lens_script(script_target))
                print(f"[KM Script] Dispatched Lens Script: {res}")
            return

    # Normal event forward
    asyncio.run(km_client.forward_event(stripped))


def monitor_keyboard():
    """Tails logcat for KeyMapper and InputMethod events via Shizuku."""
    print(f"[KM Keyboard Specialist] Screen Lens Incorporated into Keyboard")
    print(f"[KM Keyboard Specialist] Upstream Screen Lens: {SCREEN_LENS_BASE}")
    print(f"[KM Keyboard Specialist] Tailing KeyMapper/IME events...")

    cmd = ["/data/data/com.termux/files/home/rish", "-c", "logcat -T 1 -v brief -s KeyMapper InputMethod"]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ''):
            process_keymapper_line(line)
    except FileNotFoundError:
        # Fallback for testing/desktop simulation
        print("[KM Specialist] rish binary not found on local path. Running in test listener mode.")
        while True:
            time.sleep(10.0)
    except Exception as e:
        print(f"[KM Specialist] Fatal Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Testing KM Keyboard Screen Lens Client...")
        res = asyncio.run(km_client.get_visual_autocomplete("git"))
        print("Autocomplete:", res)
        ai_res = asyncio.run(km_client.trigger_ai_copilot("echo"))
        print("AI Copilot:", ai_res)
    else:
        monitor_keyboard()
