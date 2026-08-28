#!/usr/bin/env python3
"""
Lauburu Edge Swarm Healer - Powered by Hugging Face `smolagents`
Broadcasts network errors to multiple ultra-small local models (<3B parameters) simultaneously.
They race to generate a valid Python fix. The winner gains ELO and contributes to the Hourly LoRA.
"""

import os
import json
import asyncio
import concurrent.futures
from datetime import datetime
from smolagents import CodeAgent, OpenAIServerModel, tool

DATASET_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_dataset.jsonl")
ELO_SCORE_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/elo_scores.json")

# Define the SLM Swarm (Small Language Models < 3B parameters)
# These represent instances running on different edge devices in the mesh
SWARM_NODES = {
    "Qwen2.5-Coder-1.5B": {"api_base": "http://localhost:8081/v1"}, # Target: Pixel 10 Pro
    "Llama-3.2-1B": {"api_base": "http://localhost:8082/v1"},       # Target: Samsung S20+
    "Gemma-2-2B": {"api_base": "http://localhost:8083/v1"},         # Target: Mac Mini (Background)
    "DeepSeek-Coder-1.3B": {"api_base": "http://localhost:8084/v1"} # Target: GL.iNet Router
}

@tool
def execute_adb_command(device_id: str, command: str) -> str:
    """Executes an ADB shell command on a connected Android node.
    Args:
        device_id: The ADB device ID.
        command: The raw shell command to run.
    """
    import subprocess
    try:
        res = subprocess.check_output(f"adb -s {device_id} shell {command}", shell=True, text=True)
        return res
    except Exception as e:
        return f"Error executing ADB: {str(e)}"

def init_agent(model_name: str, config: dict) -> CodeAgent:
    """Initializes a smolagents CodeAgent bound to a specific local model."""
    model = OpenAIServerModel(
        model_id=model_name,
        api_base=config["api_base"],
        api_key="sk-local-mesh"
    )
    # add_base_tools=False includes python code execution sandbox natively
    return CodeAgent(tools=[execute_adb_command], model=model, add_base_tools=False)

def load_elo():
    """Loads current model ELO rankings from the filesystem."""
    if os.path.exists(ELO_SCORE_PATH):
        with open(ELO_SCORE_PATH, "r") as f:
            return json.load(f)
    return {name: 1200 for name in SWARM_NODES.keys()} # Default ELO

def save_elo(scores):
    os.makedirs(os.path.dirname(ELO_SCORE_PATH), exist_ok=True)
    with open(ELO_SCORE_PATH, "w") as f:
        json.dump(scores, f, indent=4)

def harvest_training_data(error: str, fix: str):
    """Saves successful self-healing interactions for hourly LoRA fine-tuning."""
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    with open(DATASET_PATH, "a") as f:
        f.write(json.dumps({"prompt": error, "completion": fix}) + "\n")

def run_agent_task(agent_name: str, agent: CodeAgent, prompt: str):
    """Runs the CodeAgent. Raises an exception if the agent fails to generate a working fix."""
    try:
        # CodeAgent generates and executes Python locally
        result = agent.run(prompt)
        
        # If the returned string contains a trace or error, it failed its self-execution
        if isinstance(result, str) and "Error" in result:
            raise ValueError("Agent executed code but resulted in an error.")
        return agent_name, result
    except Exception as e:
        raise RuntimeError(f"{e}")

async def broadcast_heal(error_log: str):
    """Broadcasts a crash log to all SLMs. The first to successfully fix it wins."""
    print(f"\n[{datetime.now()}] 🚨 MESH ERROR DETECTED: {error_log[:60]}...")
    print(f"[{datetime.now()}] 🏁 Broadcasting to Edge Swarm (Qwen, Llama, Gemma, DeepSeek)...\n")
    
    prompt = f"""
    You are the Lauburu Mesh Healer. A critical network error occurred:
    {error_log}
    
    Write the Python code necessary to diagnose and fix this on the local system or via ADB.
    """
    
    agents = {name: init_agent(name, conf) for name, conf in SWARM_NODES.items()}
    loop = asyncio.get_running_loop()
    
    # Fire the prompt at all models simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SWARM_NODES)) as executor:
        tasks = [
            loop.run_in_executor(executor, run_agent_task, name, agent, prompt)
            for name, agent in agents.items()
        ]
        
        winner_name = None
        winning_fix = None
        
        # Use FIRST_COMPLETED to enforce the race condition. 
        # The fastest model to successfully generate and execute the Python code wins.
        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                try:
                    winner_name, winning_fix = task.result()
                    break # We have a winner!
                except Exception as e:
                    print(f"❌ {task.exception()}")
            
            if winner_name:
                break # Exit the while loop
            else:
                tasks = pending # Continue waiting for the remaining models
        
        if not winner_name:
            print("\n❌ All edge models failed to resolve the issue.")
            return False
        
        print(f"\n🏆 WINNER: {winner_name} generated and executed the fix first!")
        
        # Update the mathematical ELO ladder
        elo = load_elo()
        elo[winner_name] += 15 # Award points to the victor
        save_elo(elo)
        print(f"📈 ELO Standings Updated: {elo}")
        
        # Log the fix for the Hourly SFTTrainer
        harvest_training_data(error_log, str(winning_fix))
        print(f"💾 Fix harvested for hourly SFTTrainer distillation.")
        
        return True

if __name__ == "__main__":
    # Test Trigger
    asyncio.run(broadcast_heal("adb: device 'Pixel_10_Pro' not found; Tailscale routing table corrupted on Layer 5."))
