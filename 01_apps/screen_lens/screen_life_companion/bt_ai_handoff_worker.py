import sqlite3
import json
import asyncio
import httpx
import logging
import socket
import os
import subprocess
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BT Handoff] %(levelname)s: %(message)s')

DB_PATH = "/Users/aaron/.lauburu/screen_life_companion.sqlite"
LOCAL_AI_URL = "http://127.0.0.1:8081/v1/chat/completions"
BT_TCP_PORT = 4005
GEMINI_URL = "https://master.heyneo.com/v2/thread/init-chat-direct"

def send_to_bt_terminal(message: str):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", BT_TCP_PORT))
        s.sendall(f"\r\n\033[1;36m[AI HANDOFF]\033[0m {message}\r\n".encode("utf-8"))
        s.close()
    except Exception as e:
        logging.warning(f"Could not reach BT Terminal on 4005: {e}")

async def execute_task(task_id: int, task_content: str):
    send_to_bt_terminal(f"Starting auto-execution of task ID {task_id}: {task_content}")
    
    prompt = f"You are the Lauburu AI Autonomous Worker.\\nYou have been handed off the following high ROI task to execute headlessly:\\n\\nTASK: {task_content}\\n\\nPlease analyze this task and return a strict JSON object with 'action' (click, type, screenshot), 'target_mode' (background_app, headless_browser, raw_coords), and 'app_name' or 'text' if applicable."
    
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(LOCAL_AI_URL, json=payload)
            if res.status_code == 200:
                response = res.json()["choices"][0]["message"]["content"].strip()
                clean_resp = response.replace('```json', '').replace('```', '')
                
                try:
                    action_data = json.loads(clean_resp)
                except:
                    action_data = {"action": "screenshot", "target_mode": "raw_coords", "app_name": "Unknown", "x": 0, "y": 0}
                
                action_arg = action_data.get("action", "click")
                mode_arg = action_data.get("target_mode", "background_app")
                app_arg = action_data.get("app_name", "Unknown")
                text_arg = action_data.get("text", "")
                
                mcp_script = f'''
import sys
sys.path.append("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src")
try:
    from mcp.screen_lens_mcp_server import handle_tool_call
    res = handle_tool_call("screen_lens_actuate_action", {{
        "device_id": "local_mac",
        "action": "{action_arg}",
        "target_mode": "{mode_arg}",
        "app_name": "{app_arg}",
        "text": "{text_arg}"
    }})
    print(res)
except Exception as e:
    print(f"MCP Call Failed: {{e}}")
'''
                with open("temp_mcp_runner.py", "w") as tf:
                    tf.write(mcp_script)
                    
                send_to_bt_terminal(f"Actuating via MCP (Headless Autonomous Mode)...")
                out = subprocess.run(["python3", "temp_mcp_runner.py"], capture_output=True, text=True)
                os.remove("temp_mcp_runner.py")
                
                # ---------------------------------------------------------------------
                # TIER 1: LORA HARVESTING LOGGER (Append to specialist_candidates.jsonl)
                # ---------------------------------------------------------------------
                if "ACTUATED" in out.stdout:
                    ds_path = "/Users/aaron/DFS_UNIFIED/lora_datasets/specialist_candidates.jsonl"
                    Path(ds_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    lora_entry = {
                        "instruction": f"Execute background task: {task_content}",
                        "input": f"App: {app_arg}, Mode: {mode_arg}",
                        "output": json.dumps(action_data)
                    }
                    with open(ds_path, "a") as df:
                        df.write(json.dumps(lora_entry) + "\n")
                    send_to_bt_terminal(f"🧠 Saved successful execution to LoRA Harvesting Dataset.")
                else:
                    send_to_bt_terminal(f"❌ MCP Actuation Failed: {out.stdout.strip()}")
            else:
                send_to_bt_terminal(f"Local AI failed (HTTP {res.status_code}).")
    except Exception as e:
        send_to_bt_terminal(f"Local AI unreachable ({e}).")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task_id = int(sys.argv[1])
        task_content = sys.argv[2]
        asyncio.run(execute_task(task_id, task_content))
