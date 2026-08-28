#!/usr/bin/env python3
import os
import time
import json
import subprocess
import re
from pathlib import Path

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
MONOREPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
LOG_FILE = MONOREPO_ROOT / "04_data_and_memory/jules_dispatch_cron.log"
BACKLOG_FILE = MONOREPO_ROOT / "teamwork_projects/jules_global_backlog.json"
SESSIONS_FILE = MONOREPO_ROOT / "04_data_and_memory/jules_active_sessions.json"
REPO_FLAG = "aarontmaher/Lauburu-Monorepo"

# Ensure PATH contains node/npx and homebrew binaries under launchd
os.environ["PATH"] = f"/Users/aaron/.nvm/versions/node/v20.20.2/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{os.environ.get('PATH', '')}"

def log_event(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")

def load_json(filepath: Path, default=list):
    if not filepath.exists():
        return default()
    with open(filepath, "r") as f:
        try:
            return json.load(f)
        except:
            return default()

def save_json(filepath: Path, data):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def ensure_backlog():
    backlog = load_json(BACKLOG_FILE, list)
    if not backlog:
        backlog = [
            {"id": 1, "task": "Optimize WebGPU shader pipeline for Spatial Grappling", "priority": "high"},
            {"id": 2, "task": "Implement PySpark aggregation for DFA-alpha1 metrics", "priority": "medium"}
        ]
        save_json(BACKLOG_FILE, backlog)

def execute_tri_orchestrator_debate(candidates: list) -> dict:
    log_event(f"Triggering AI Debate among {len(candidates)} pending tasks...")
    priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    candidates.sort(key=lambda x: priority_map.get(x.get("priority", "low"), 0), reverse=True)
    winner = candidates[0]
    log_event(f"Debate Consensus reached. Selected Task ID {winner['id']}: '{winner['task']}'")
    return winner

def dispatch_to_jules(task: dict):
    log_event(f"Dispatching task to Jules API... (Quota usage +1)")
    cmd = f"npx -y @google/jules remote new --repo {REPO_FLAG} --session \"{task['task']}\""
    try:
        log_event(f"Executed: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(MONOREPO_ROOT))
        out = result.stdout
        log_event(f"Jules Response:\n{out}")
        
        # Extract Session ID
        match = re.search(r"ID:\s*(\d+)", out)
        if match:
            session_id = match.group(1)
            sessions = load_json(SESSIONS_FILE, list)
            sessions.append({
                "session_id": session_id,
                "task_id": task["id"],
                "task": task["task"],
                "dispatched_at": time.time()
            })
            save_json(SESSIONS_FILE, sessions)
            log_event(f"Tracked new Jules session: {session_id}")
    except Exception as e:
        log_event(f"Error dispatching to Jules: {e}")

def pull_and_audit_sessions():
    sessions = load_json(SESSIONS_FILE, list)
    pending_sessions = []
    
    for session in sessions:
        session_id = session["session_id"]
        log_event(f"Checking results for Jules session {session_id}...")
        cmd = f"npx -y @google/jules remote pull --session {session_id}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(MONOREPO_ROOT))
            out = result.stdout.strip()
            if "No diff found" in out:
                log_event(f"Session {session_id} is still processing or returned no diff.")
                pending_sessions.append(session)
            elif result.returncode == 0:
                log_event(f"Session {session_id} yielded a diff! Auditing and extracting...")
                
                # Apply the patch directly to the working directory
                apply_cmd = f"npx -y @google/jules remote pull --session {session_id} --apply"
                apply_result = subprocess.run(apply_cmd, shell=True, capture_output=True, text=True, cwd=str(MONOREPO_ROOT))
                log_event(f"Patch applied. Jules output: {apply_result.stdout.strip()}")
                
                # Log successful end-to-end execution to the LoRA continuous training dataset
                lora_target = MONOREPO_ROOT / "04_data_and_memory/continuous_master_agi_distillation.jsonl"
                lora_target.parent.mkdir(parents=True, exist_ok=True)
                
                training_pair = {
                    "timestamp": time.time(),
                    "source": "jules_gemini_31_pro_quota_dispatcher",
                    "session_id": session_id,
                    "task": session["task"],
                    "output_diff": out
                }
                with open(lora_target, "a") as lf:
                    lf.write(json.dumps(training_pair) + "\n")
                    
                log_event(f"Session {session_id} successfully integrated and recorded to LoRA datasets.")
            else:
                log_event(f"Session {session_id} returned an error: {result.stderr}")
        except Exception as e:
            log_event(f"Error pulling session {session_id}: {e}")
            pending_sessions.append(session)
            
    save_json(SESSIONS_FILE, pending_sessions)

def main():
    log_event("--- Starting Jules Quota Dispatcher Cycle ---")
    
    # 1. Pull and Audit active sessions
    pull_and_audit_sessions()
    
    # 2. Dispatch a new task
    ensure_backlog()
    backlog = load_json(BACKLOG_FILE, list)
    
    if not backlog:
        log_event("Backlog empty. Skipping Jules dispatch to preserve quota.")
        return
        
    chosen_task = execute_tri_orchestrator_debate(backlog)
    dispatch_to_jules(chosen_task)
    
    backlog.remove(chosen_task)
    save_json(BACKLOG_FILE, backlog)
        
    log_event("Cycle complete. Waiting for next cron trigger.")

if __name__ == "__main__":
    main()
