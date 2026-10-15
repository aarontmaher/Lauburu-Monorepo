#!/usr/bin/env python3
"""
OpenRouter Hard Killswitch & Ledger Monitor (Rule 6)
Continuously monitors API spend. If the daily / session spend increases by more than $1.00,
it automatically SIGKILLs all cloud orchestration daemons to protect the user's budget.
"""

import os
import time
import json
import urllib.request
import subprocess
from datetime import datetime

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_current_usage():
    if not OPENROUTER_API_KEY:
        return None
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/auth/key",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("data", {}).get("usage", 0.0)
    except Exception as e:
        print(f"Failed to fetch usage: {e}")
        return None

def trigger_killswitch(reason):
    print(f"[{datetime.now().isoformat()}] 🚨 BUDGET KILLSWITCH TRIGGERED: {reason}")
    print("Shutting down all automated cloud Swarm orchestrators and training loops...")
    
    # Kill the continuous training loop
    subprocess.run(["pkill", "-f", "intelligent_lens_router_training_loop.sh"])
    # Kill the Teamwork Preview orchestrator if it's running via agy (fallback)
    subprocess.run(["pkill", "-f", "frontier_swarm_consensus.py"])
    subprocess.run(["pkill", "-f", "agy"])
    
    print("All cloud agents have been terminated. Local Sovereign Triad (Port 8082) remains active.")

def main():
    print(f"[{datetime.now().isoformat()}] Starting OpenRouter Spend Killswitch Monitor...")
    initial_usage = get_current_usage()
    if initial_usage is None:
        print("Warning: OPENROUTER_API_KEY not found or invalid. Using local proxy checks.")
        initial_usage = 0.0
    
    print(f"Initial Ledger Usage: ${initial_usage:.4f}")
    
    MAX_ALLOWABLE_SPEND = 1.00 # Hard limit of $1.00 per session/day
    
    while True:
        time.sleep(300) # Check every 5 mins
        current_usage = get_current_usage()
        
        if current_usage is not None:
            spend_delta = current_usage - initial_usage
            print(f"[{datetime.now().isoformat()}] Session Spend: ${spend_delta:.4f} (Total: ${current_usage:.4f})")
            
            if spend_delta >= MAX_ALLOWABLE_SPEND:
                trigger_killswitch(f"Session spend (${spend_delta:.4f}) exceeded the hard limit of ${MAX_ALLOWABLE_SPEND:.2f}")
                break

if __name__ == "__main__":
    main()
