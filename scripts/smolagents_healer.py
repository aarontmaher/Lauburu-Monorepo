#!/usr/bin/env python3
"""
Lauburu Mesh Healer - Powered by Hugging Face `smolagents`
Wraps Qwen2.5-Coder to act as an autonomous CodeAgent for self-healing the network.
"""

import os
import json
from datetime import datetime
from smolagents import CodeAgent, OpenAIServerModel, tool

# 1. Connect smolagents to the local Llama.cpp RPC engine running Qwen2.5-Coder
# This keeps all inference 100% local and utilizes the 82.8 GB VRAM pool.
local_model = OpenAIServerModel(
    model_id="qwen2.5-coder-7b",
    api_base="http://localhost:8080/v1",
    api_key="sk-local-mesh"
)

DATASET_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_dataset.jsonl")

# 2. Define Custom Tools for the CodeAgent
@tool
def execute_adb_command(device_id: str, command: str) -> str:
    """Executes an ADB shell command on a connected Android node.
    Args:
        device_id: The ADB device ID (e.g., 'Pixel_10_Pro' or IP address).
        command: The raw shell command to run.
    """
    import subprocess
    try:
        res = subprocess.check_output(f"adb -s {device_id} shell {command}", shell=True, text=True)
        return res
    except Exception as e:
        return f"Error executing ADB: {str(e)}"

# 3. Initialize the CodeAgent (It will write and execute raw Python)
agent = CodeAgent(tools=[execute_adb_command], model=local_model, add_base_tools=True)

def harvest_training_data(error: str, fix: str):
    """Saves successful self-healing interactions for LoRA fine-tuning."""
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    with open(DATASET_PATH, "a") as f:
        f.write(json.dumps({"prompt": error, "completion": fix}) + "\n")

def heal_network_error(error_log: str):
    """Entrypoint called by the Mesh Sentinel when a crash occurs."""
    print(f"[{datetime.now()}] Immune System triggered for error: {error_log[:50]}...")
    
    prompt = f"""
    You are the Lauburu Mesh Healer. A critical network error occurred:
    {error_log}
    
    Write the Python code necessary to diagnose and fix this on the local system or via ADB.
    """
    
    try:
        # The agent will generate Python, execute it, and return the result
        result = agent.run(prompt)
        print(f"[{datetime.now()}] Fix Successfully Applied: {result}")
        
        # Save the interaction to the evolutionary flywheel
        harvest_training_data(error_log, str(result))
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Healer failed to resolve the issue: {e}")
        return False

if __name__ == "__main__":
    # Example trigger
    heal_network_error("adb: device 'Pixel_10_Pro' not found; Tailscale routing table corrupted on Layer 5.")
