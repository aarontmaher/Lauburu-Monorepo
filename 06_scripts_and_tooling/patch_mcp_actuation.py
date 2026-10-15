import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src/mcp/screen_lens_mcp_server.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace the actuate_action block
old_actuate = """    elif name == "screen_lens_actuate_action":
        device_id = arguments.get("device_id", "100.78.206.96:5555")
        action = arguments.get("action", "tap")
        x = arguments.get("x", 540)
        y = arguments.get("y", 900)

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

content = content.replace(old_actuate, new_actuate)

with open(file_path, "w") as f:
    f.write(content)

