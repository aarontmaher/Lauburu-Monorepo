import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py"
with open(file_path, "r") as f:
    content = f.read()

# We need to inject the LoRA JSONL harvesting logic right after the MCP server executes a task successfully.
old_exec = """        # Call the MCP server script or mock the action
        mcp_cmd = ["python3", "-c", "from mcp.screen_lens_mcp_server import handle_tool_call; print(handle_tool_call('screen_lens_actuate_action', {'device_id': 'local_mac', 'action': 'screenshot', 'target_mode': 'background_app', 'app_name': 'Terminal'}))"]
        # We just log it for the pipeline proof
        print(f"[Worker] Actuating via MCP (Headless Autonomous Mode)...")
        print(f"[Worker] Task Execution Complete.")"""

new_exec = """        # Parse the AI's JSON response for the action
        import json
        import subprocess
        import time
        from pathlib import Path
        
        # Clean the response for JSON parsing
        clean_resp = response.strip().replace('```json', '').replace('```', '')
        try:
            action_data = json.loads(clean_resp)
        except:
            action_data = {"action": "click", "target_mode": "background_app", "app_name": "Unknown", "x": 0, "y": 0}
            
        # Execute via MCP Server
        action_arg = action_data.get("action", "click")
        mode_arg = action_data.get("target_mode", "background_app")
        app_arg = action_data.get("app_name", "Unknown")
        text_arg = action_data.get("text", "")
        
        mcp_script = f'''
import sys
sys.path.append("/Volumes/Lauburu-Monorepo/01_apps/screen_lens/src")
from mcp.screen_lens_mcp_server import handle_tool_call
res = handle_tool_call("screen_lens_actuate_action", {{
    "device_id": "local_mac",
    "action": "{action_arg}",
    "target_mode": "{mode_arg}",
    "app_name": "{app_arg}",
    "text": "{text_arg}"
}})
print(res)
'''
        with open("temp_mcp_runner.py", "w") as tf:
            tf.write(mcp_script)
            
        print(f"[Worker] Actuating via MCP (Headless Autonomous Mode)...")
        out = subprocess.run(["python3", "temp_mcp_runner.py"], capture_output=True, text=True)
        import os
        os.remove("temp_mcp_runner.py")
        
        # ---------------------------------------------------------------------
        # TIER 1: LORA HARVESTING LOGGER (Append to specialist_candidates.jsonl)
        # ---------------------------------------------------------------------
        if "ACTUATED" in out.stdout:
            ds_path = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/specialist_candidates.jsonl"
            Path(ds_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Format as an instruction-tuning pair for LoRA training
            lora_entry = {
                "instruction": f"Execute background task: {task_content}",
                "input": f"App: {app_arg}, Mode: {mode_arg}",
                "output": json.dumps(action_data)
            }
            with open(ds_path, "a") as df:
                df.write(json.dumps(lora_entry) + "\\n")
            print(f"[Worker] 🧠 Saved successful execution to LoRA Harvesting Dataset.")
            
        print(f"[Worker] Task Execution Complete.")"""

if old_exec in content:
    content = content.replace(old_exec, new_exec)
    with open(file_path, "w") as f:
        f.write(content)
    print("Patched successfully.")
else:
    print("Old exec block not found. Skipping.")
