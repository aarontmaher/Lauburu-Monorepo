import json
import os
import time
from datetime import datetime

DATASET_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/continuous_mcts_traces.jsonl"
MCTS_TRACES_PATH = "/tmp/mcts_latest_traces.jsonl"

def harvest_mcts_traces():
    """
    Checks the temporary traces file dumped by mesh_mcts_orchestrator.py,
    formats them, and appends them to the persistent PySpark Data Lake.
    """
    if not os.path.exists(MCTS_TRACES_PATH):
        return
        
    print(f"[{datetime.now().isoformat()}] Harvesting MCTS traces from {MCTS_TRACES_PATH}...")
    
    if not os.path.exists(os.path.dirname(DATASET_PATH)):
        os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
        
    traces = []
    with open(MCTS_TRACES_PATH, "r") as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line))
                
    if not traces:
        return
        
    with open(DATASET_PATH, "a") as f:
        for trace in traces:
            trace["type"] = "mcts_pruned_trace"
            f.write(json.dumps(trace) + "\n")
            
    # Clear the temporary file
    open(MCTS_TRACES_PATH, "w").close()
    
    print(f"Harvest complete. {len(traces)} traces appended to {DATASET_PATH}.")

def daemon_loop():
    print("Starting MCTS LoRA Harvester Daemon...")
    while True:
        try:
            harvest_mcts_traces()
            time.sleep(60) # Check every minute
        except KeyboardInterrupt:
            print("Shutting down harvester daemon.")
            break
        except Exception as e:
            print(f"Error in harvester: {e}")
            time.sleep(60)

if __name__ == "__main__":
    daemon_loop()
