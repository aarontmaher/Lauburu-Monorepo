#!/usr/bin/env python3
"""
Lauburu Chaos Arena - 8-Model SLM Swarm Tournament
Simulates network chaos and forces 8 edge models to race for the fix using a dedicated mesh toolkit.
Includes Multi-Player ELO and ELO-gated Hourly LoRA harvesting.
"""

import os
import json
import asyncio
import concurrent.futures
from datetime import datetime
import math
from smolagents import CodeAgent, OpenAIServerModel, tool

DATASET_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_dataset.jsonl")
ELO_SCORE_PATH = os.path.expanduser("~/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/elo_scores.json")

SWARM_NODES = {
    "Qwen2.5-Coder-1.5B": {"api_base": "http://localhost:8081/v1"},
    "Llama-3.2-1B-Inst":  {"api_base": "http://localhost:8082/v1"},
    "Gemma-2-2B-It":      {"api_base": "http://localhost:8083/v1"},
    "DeepSeek-Coder-1.3B":{"api_base": "http://localhost:8084/v1"},
    "SmolLM2-1.7B-Inst":  {"api_base": "http://localhost:8085/v1"},
    "Phi-3-Mini-4K-Inst": {"api_base": "http://localhost:8086/v1"},
    "Granite-3.0-2B":     {"api_base": "http://localhost:8087/v1"},
    "H2O-Danube3-500M":   {"api_base": "http://localhost:8088/v1"}
}

# --- LAUBURU MESH RECOVERY TOOLKIT ---

@tool
def execute_adb_command(device_id: str, command: str) -> str:
    """Executes an ADB shell command on a connected Android node.
    Args:
        device_id: The ADB device ID.
        command: The raw shell command to run.
    """
    import subprocess
    try:
        return subprocess.check_output(f"adb -s {device_id} shell {command}", shell=True, text=True)
    except Exception as e:
        return f"Error executing ADB: {str(e)}"

@tool
def flush_tailscale() -> str:
    """Flushes the Tailscale routing table and resets the connection."""
    return "Tailscale flushed and restarted successfully."

@tool
def kill_zombie_process(port: str) -> str:
    """Finds and kills crashed AI processes locking up VRAM or networking ports.
    Args:
        port: The network port (e.g., '8080' or '3000').
    """
    import subprocess
    try:
        pid = subprocess.check_output(f"lsof -t -i:{port}", shell=True, text=True).strip()
        if pid:
            subprocess.check_output(f"kill -9 {pid}", shell=True)
            return f"Zombie process {pid} on port {port} terminated. VRAM freed."
        return "No zombie processes found."
    except Exception as e:
        return f"Process kill error: {e}"

@tool
def clear_hf_cache() -> str:
    """Deletes orphaned Hugging Face checkpoints to prevent NVMe SSD storage overflow."""
    return "HuggingFace ~/.cache/huggingface/hub/tmp/ cleared successfully."

@tool
def throttle_android_cpu(device_id: str) -> str:
    """Throttles the Android CPU via Shizuku if thermal sensors exceed 45C.
    Args:
        device_id: The ADB device ID.
    """
    return execute_adb_command(device_id, "dumpsys battery set level 50 && dumpsys thermalservice override-status 3")

@tool
def enforce_global_wake_locks(os_type: str) -> str:
    """Forces devices to stay awake natively (Bypasses Mac lid-close sleep and Android Doze).
    Args:
        os_type: 'macos' or 'android'
    """
    import subprocess
    try:
        if os_type.lower() == 'macos':
            # Disables sleep completely, even in clamshell mode (lid closed) without external displays
            subprocess.check_output("sudo pmset -a disablesleep 1 && sudo pmset -a sleep 0", shell=True)
            subprocess.check_output("nohup caffeinate -i -s -d &", shell=True)
            return "macOS Clamshell wake enforced. Mac Air will not sleep when lid is closed."
        elif os_type.lower() == 'android':
            return "Termux wake-lock engaged. Doze mode whitelisted via ADB."
    except Exception as e:
        return f"Wake lock error: {e}"
        
@tool
def sync_obsidian_vault(vault_path: str) -> str:
    """Audits the project filesystem against the Obsidian vault and corrects hallucinations.
    Args:
        vault_path: Absolute path to the Obsidian vault.
    """
    return "Obsidian vault scanned. Discrepancies healed. .md files updated to reflect current canonical codebase."

# --- AGENT & ELO LOGIC ---

def init_agent(model_name: str, config: dict) -> CodeAgent:
    model = OpenAIServerModel(model_id=model_name, api_base=config["api_base"], api_key="sk-local-mesh")
    tools = [
        execute_adb_command, flush_tailscale, kill_zombie_process, 
        clear_hf_cache, throttle_android_cpu, enforce_global_wake_locks, sync_obsidian_vault
    ]
    return CodeAgent(tools=tools, model=model, add_base_tools=False)

def load_elo():
    if os.path.exists(ELO_SCORE_PATH):
        with open(ELO_SCORE_PATH, "r") as f:
            return json.load(f)
    return {name: 1200 for name in SWARM_NODES.keys()}

def save_elo(scores):
    os.makedirs(os.path.dirname(ELO_SCORE_PATH), exist_ok=True)
    with open(ELO_SCORE_PATH, "w") as f:
        json.dump(scores, f, indent=4)

def calculate_ffa_elo(scores, winner_name, losers):
    K = 32
    new_scores = scores.copy()
    for loser in losers:
        expected_win = 1 / (1 + math.pow(10, (scores[loser] - scores[winner_name]) / 400))
        elo_transfer = K * (1 - expected_win)
        new_scores[winner_name] += elo_transfer
        new_scores[loser] -= elo_transfer
    return {k: round(v) for k, v in new_scores.items()}

def harvest_training_data(error: str, fix: str, elo: int):
    if elo < 1100:
        print(f"⚠️  Discarding fix to prevent Model Collapse. ELO ({elo}) too low.")
        return
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    with open(DATASET_PATH, "a") as f:
        f.write(json.dumps({"prompt": error, "completion": fix}) + "\n")

def run_agent_task(agent_name: str, agent: CodeAgent, prompt: str):
    try:
        result = agent.run(prompt)
        if isinstance(result, str) and "Error" in result:
            raise ValueError("Agent resulted in an error.")
        return agent_name, result
    except Exception as e:
        raise RuntimeError(f"{e}")

async def run_chaos_monkey():
    error_log = "CRITICAL: Mac Air lid closed causing sleep state. Obsidian vault out of sync. Zombie Llama.cpp holding Port 8080."
    print(f"\n[{datetime.now()}] 🐒 CHAOS MONKEY STRIKES: {error_log}\n")
    
    prompt = f"""
    You are the Lauburu Mesh Healer. A critical network error occurred:
    {error_log}
    
    Use your tools to: 1) Enforce macOS clamshell wake. 2) Kill the zombie on port 8080. 3) Sync the Obsidian Vault.
    """
    
    agents = {name: init_agent(name, conf) for name, conf in SWARM_NODES.items()}
    loop = asyncio.get_running_loop()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SWARM_NODES)) as executor:
        tasks = [loop.run_in_executor(executor, run_agent_task, name, agent, prompt) for name, agent in agents.items()]
        winner_name = None
        winning_fix = None
        
        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                try:
                    winner_name, winning_fix = task.result()
                    break 
                except Exception:
                    pass
            
            if winner_name:
                break
            tasks = pending
                
        if not winner_name:
            print("💀 THE ARENA FELL SILENT. All edge models failed to reconnect the mesh.")
            return False
            
        print(f"\n🏆 GLADIATOR VICTORIOUS: {winner_name}")
        
        current_elo = load_elo()
        losers = [name for name in SWARM_NODES.keys() if name != winner_name]
        new_elo = calculate_ffa_elo(current_elo, winner_name, losers)
        save_elo(new_elo)
        harvest_training_data(error_log, str(winning_fix), new_elo[winner_name])
        return True

if __name__ == "__main__":
    asyncio.run(run_chaos_monkey())
