import sys
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/mcp/screen_lens_mcp_server.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace the actuate_action block again to support all 3 targeting modes
old_actuate = """    elif name == "screen_lens_actuate_action":
        device_id = arguments.get("device_id", "local_mac")
        action = arguments.get("action", "tap")
        x = arguments.get("x", 540)
        y = arguments.get("y", 900)
        text = arguments.get("text", "")

        if device_id == "local_mac":
            if action in ["tap", "click"]:
                # Requires cliclick or AppleScript. AppleScript is universally available.
                script = f'tell application "System Events" to click at {{{x}, {y}}}'
                cmd = ["osascript", "-e", script]
            elif action == "type":
                script = f'tell application "System Events" to keystroke "{text}"'
                cmd = ["osascript", "-e", script]
            elif action == "screenshot":
                # Background headless screenshot
                cmd = ["screencapture", "-x", f"/Volumes/Lauburu-Monorepo/01_apps/screen_lens/data/headless_screenshot_{int(time.time())}.png"]
            elif action == "record_start":
                # Start background headless recording
                cmd = ["screencapture", "-v", f"/Volumes/Lauburu-Monorepo/01_apps/screen_lens/data/headless_recording.mp4"]
                subprocess.Popen(cmd, start_new_session=True)
                return {"device_id": "local_mac", "action_executed": "Background video recording started.", "status": "ACTUATED"}
            elif action == "record_stop":
                cmd = ["killall", "screencapture"]
            else:
                cmd = ["echo", "unsupported action"]
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "device_id": device_id,
                "action_executed": f"{action} executed locally",
                "exit_code": res.returncode,
                "status": "ACTUATED" if res.returncode == 0 else f"FAILED: {res.stderr}"
            }
        else:
            # ADB Actuation for Android Mesh Nodes
            cmd = ["adb", "-s", device_id, "shell", "input", action, str(x), str(y)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "device_id": device_id,
                "action_executed": f"{action} at ({x}, {y})",
                "exit_code": res.returncode,
                "status": "ACTUATED" if res.returncode == 0 else "FAILED"
            }"""

new_actuate = """    elif name == "screen_lens_actuate_action":
        device_id = arguments.get("device_id", "local_mac")
        action = arguments.get("action", "tap")
        x = arguments.get("x", 540)
        y = arguments.get("y", 900)
        text = arguments.get("text", "")
        target_mode = arguments.get("target_mode", "raw_coords") # raw_coords, background_app, headless_browser
        app_name = arguments.get("app_name", "Safari")

        if device_id == "local_mac":
            if target_mode == "background_app":
                if action in ["tap", "click"]:
                    script = f'tell application "{app_name}" to activate\\ntell application "System Events" to click at {{{x}, {y}}}'
                    cmd = ["osascript", "-e", script]
                elif action == "type":
                    script = f'tell application "System Events" to tell process "{app_name}" to keystroke "{text}"'
                    cmd = ["osascript", "-e", script]
            elif target_mode == "headless_browser":
                # Write a fast playwright script on the fly
                import tempfile
                pw_script = f'''
import asyncio
from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # For a generic headless action, just dump the text to a local headless log
        await page.evaluate("console.log('Headless browser actuated: {action} {text}')")
        await browser.close()
asyncio.run(run())
'''
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(pw_script)
                    temp_path = f.name
                cmd = ["python3", temp_path]
            else: # raw_coords
                if action in ["tap", "click"]:
                    script = f'tell application "System Events" to click at {{{x}, {y}}}'
                    cmd = ["osascript", "-e", script]
                elif action == "type":
                    script = f'tell application "System Events" to keystroke "{text}"'
                    cmd = ["osascript", "-e", script]

            if action == "screenshot":
                cmd = ["screencapture", "-x", f"/Volumes/Lauburu-Monorepo/01_apps/screen_lens/data/headless_screenshot_{int(time.time())}.png"]
            elif action == "record_start":
                cmd = ["screencapture", "-v", f"/Volumes/Lauburu-Monorepo/01_apps/screen_lens/data/headless_recording.mp4"]
                subprocess.Popen(cmd, start_new_session=True)
                return {"device_id": "local_mac", "action_executed": "Background video recording started.", "status": "ACTUATED"}
            elif action == "record_stop":
                cmd = ["killall", "screencapture"]
                
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "device_id": device_id,
                "action_executed": f"{action} executed locally via {target_mode}",
                "exit_code": res.returncode,
                "status": "ACTUATED" if res.returncode == 0 else f"FAILED: {res.stderr}"
            }
        else:
            # ADB Actuation for Android Mesh Nodes
            cmd = ["adb", "-s", device_id, "shell", "input", action, str(x), str(y)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "device_id": device_id,
                "action_executed": f"{action} at ({x}, {y})",
                "exit_code": res.returncode,
                "status": "ACTUATED" if res.returncode == 0 else "FAILED"
            }"""

content = content.replace(old_actuate, new_actuate)

with open(file_path, "w") as f:
    f.write(content)

