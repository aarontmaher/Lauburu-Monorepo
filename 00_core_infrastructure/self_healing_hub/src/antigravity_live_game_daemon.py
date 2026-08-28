#!/usr/bin/env python3
"""
Antigravity Live Game Daemon
Hooks the real Gemini API into the AI Mesh Battle Arena.
Ensures ZERO DRIFT: All decisions must map strictly to real monorepo project skills.
"""

import os
import sys
import time
import json
import random

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install google-genai: pip install google-genai")
    sys.exit(1)

GAME_STATE_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/00_core_infrastructure/self_healing_hub/src/game_arena_state.json"
API_KEY = os.environ.get("GEMINI_API_KEY")

PROJECT_SKILLS = [
    "Movesense 128Hz ECG/IMU Bluetooth GATT Telemetry",
    "10Gbps Thunderbolt 4 Node-to-Node RPC Sharding",
    "Tailscale WireGuard Decentralized Overlay Mesh",
    "WebGPU 120 FPS 3D Spatial Canvas UI",
    "LoRA Rank-64 Swarm Model Distillation",
    "AST Monorepo Code Refactoring & SQLite Caching"
]

def load_state():
    with open(GAME_STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(GAME_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def generate_antigravity_move(state):
    if not API_KEY:
        print("[WARNING] GEMINI_API_KEY not found. Skipping live API call.")
        return None

    client = genai.Client(api_key=API_KEY)
    
    # Extract relevant state
    round_num = state.get("round", 0)
    agents = state.get("agents", [])
    local_agents = [a["name"] for a in agents if a.get("faction") == "TEAM_LOCAL_MESH"]
    
    if not local_agents:
        return None
        
    prompt = f"""
    You are the Antigravity Cloud Commander orchestrating a swarm in a simulated AI Mesh Battle Arena.
    The goal of this arena is to generate high-quality LoRA training pairs to optimize real-world Local AI models on the Lauburu Monorepo.
    
    CRITICAL RULE: DO NOT DRIFT into generic fantasy. All actions must be strictly bounded to real project skills:
    {json.dumps(PROJECT_SKILLS, indent=2)}
    
    Current State:
    Round: {round_num}
    Active Local Mesh Targets: {json.dumps(local_agents)}
    
    Choose a target and execute a highly technical, project-grounded cyber strike or optimization maneuver.
    
    Respond ONLY in valid JSON format:
    {{
      "target": "name of local agent",
      "action_name": "Name of the technical strike",
      "project_skill_focus": "One of the provided project skills",
      "narrative": "A strict 2-sentence technical description of the action and how it optimizes the monorepo architecture."
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"[API ERROR] {e}")
        return None

def main():
    print("Starting Antigravity Live Game Daemon...")
    while True:
        try:
            state = load_state()
            
            # We only intervene if Antigravity is actually on the field
            agents = state.get("agents", [])
            is_active = any("Antigravity" in a.get("name", "") for a in agents)
            
            # Only poll the API occasionally to save tokens (e.g. every 10 rounds)
            round_num = state.get("round", 0)
            
            if is_active and round_num % 10 == 0:
                print(f"[Round {round_num}] Triggering Real Antigravity API Call...")
                move = generate_antigravity_move(state)
                
                if move:
                    print(f"Move generated: {move['action_name']}")
                    
                    # Inject move into the action log
                    event = {
                        "type": "ANTIGRAVITY_LIVE_API_STRIKE",
                        "message": f"🔴 LIVE API STRIKE: {move['action_name']} targeting {move['target']}. Focus: {move['project_skill_focus']}.",
                        "narrative": move['narrative'],
                        "turn": round_num
                    }
                    
                    # Also append to the truth audit LoRA to ensure the local models learn from this
                    lora_entry = {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "type": "antigravity_live_api_strike",
                        "instruction": f"Defend against or analyze a live Cloud Titan strike targeting {move['project_skill_focus']}.",
                        "thought": move['narrative'],
                        "output": "Local Mesh registered the architectural insight and appended it to the swarm memory banks."
                    }
                    
                    state.setdefault("game_action_log", []).insert(0, event)
                    
                    # Save both states
                    save_state(state)
                    
                    with open("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/lora_datasets/truth_audit_debate.jsonl", "a") as f:
                        f.write(json.dumps(lora_entry) + "\\n")
                        
            time.sleep(5) # Poll interval
            
        except Exception as e:
            print(f"Daemon Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
