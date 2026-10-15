import sqlite3
import time
import subprocess
import os
import datetime

DB_PATH = "/Users/aaron/.lauburu/screen_lens.sqlite"

def insert_mock_screen_capture():
    print("[E2E] 1. Inserting simulated high-value repetitive task into screen capture DB...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Fake OCR text indicating the user is manually organizing files in the terminal over and over
    content = "mv file1.txt archive/ && mv file2.txt archive/ && mv file3.txt archive/"
    cursor.execute(
        "INSERT INTO screen_captures (timestamp_iso, app_name, window_title, ocr_text) VALUES (?, ?, ?, ?)",
        (datetime.datetime.now().isoformat(), "Terminal", "bash", content)
    )
    conn.commit()
    conn.close()

def run_pipeline_test():
    insert_mock_screen_capture()
    print("[E2E] 2. Waiting for Life Companion Daemon to extract ROI task...")
    time.sleep(5) # Give the daemon time to process it via Local AI
    
    print("[E2E] 3. Verifying Abstract Optimization Queue extraction...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM optimization_queue ORDER BY id DESC LIMIT 1")
    opt = cursor.fetchone()
    if opt:
        print(f"✅ Optimization Queued: {opt}")
    else:
        print("⚠️ No optimization queued, but this depends on the local AI response.")
        
    print("[E2E] 4. Triggering Autonomous Handoff Worker with MCP Headless Execution...")
    script = """
import sys
from pathlib import Path
sys.path.append('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src')
try:
    from mcp.screen_lens_mcp_server import handle_tool_call
    res = handle_tool_call("screen_lens_actuate_action", {
        "device_id": "local_mac",
        "action": "screenshot",
        "target_mode": "raw_coords"
    })
    print(res)
except Exception as e:
    print(f"MCP Call Failed: {e}")
"""
    with open("temp_mcp_test.py", "w") as f:
        f.write(script)
    
    out = subprocess.run(["python3", "temp_mcp_test.py"], capture_output=True, text=True)
    if "ACTUATED" in out.stdout:
        print(f"✅ Headless Action Executed Successfully: {out.stdout.strip()}")
    else:
        print(f"❌ Headless Action Failed: {out.stdout.strip()} {out.stderr.strip()}")
        
    os.remove("temp_mcp_test.py")
    print("[E2E] Pipeline Test Complete.")

if __name__ == "__main__":
    run_pipeline_test()
