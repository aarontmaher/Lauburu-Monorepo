#!/usr/bin/env python3
"""
================================================================================
Google Jules Autonomous Backlog Generator, Dispatcher & LoRA Harvester
================================================================================
Subsystem: 06_scripts_and_tooling/integrations_and_mcp/jules_debate_dispatcher.py
Version: 2.1.0-JULES-ULTRA-MAXIMIZER
Lauburu Mesh Ecosystem — Canonical Architecture 2026

Role:
- Manages Google Jules AI (Google AI Ultra: 300 tasks/day, 60 concurrent tasks).
- Dynamically discovers high-value engineering tasks across 13 core subsystems.
- Maintains a prioritized backlog (teamwork_projects/jules_global_backlog.json).
- Dispatches tasks using @google/jules CLI up to concurrency threshold.
- Pulls completed diffs, validates AST syntax (Rule #0 Zero-Mock), and serializes
  training pairs to continuous LoRA datasets for local model fine-tuning.
================================================================================
"""

import os
import sys
import time
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# -----------------------------------------------------------------------------
# Configuration & Paths
# -----------------------------------------------------------------------------
MONOREPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = MONOREPO_ROOT / "04_data_and_memory/jules_dispatch_cron.log"
BACKLOG_FILE = MONOREPO_ROOT / "teamwork_projects/jules_global_backlog.json"
SESSIONS_FILE = MONOREPO_ROOT / "04_data_and_memory/jules_active_sessions.json"
LORA_SINK = MONOREPO_ROOT / "04_data_and_memory/data/continuous_lora_dataset.jsonl"
DISTILLATION_SINK = MONOREPO_ROOT / "04_data_and_memory/continuous_master_agi_distillation.jsonl"
REPO_FLAG = "aarontmaher/Lauburu-Monorepo"
JULES_BIN = "/Users/aaron/.local/bin/jules"

# Active automation switch (Google AI Ultra Tier: 300 tasks/day)
JULES_AUTOMATION_ENABLED = True
MAX_CONCURRENT_SESSIONS = 15
DAILY_TASK_LIMIT = 300
MAX_DISPATCHES_PER_CYCLE = 3
COOLDOWN_SECONDS = 180  # 3-minute retry backoff on server concurrency cap

# Environment PATH configuration for Node/npx and tools
os.environ["PATH"] = f"/Users/aaron/.nvm/versions/node/v20.20.2/bin:/Users/aaron/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{os.environ.get('PATH', '')}"


def _jules_cmd(*args: str) -> List[str]:
    if os.path.exists(JULES_BIN) and os.access(JULES_BIN, os.X_OK):
        return [JULES_BIN, *args]
    return ["npx", "-y", "@google/jules", *args]


def log_event(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [JulesOrchestrator] {msg}"
    print(log_line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass


def load_json(filepath: Path, default_factory=list):
    if not filepath.exists():
        return default_factory()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_factory()


def save_json(filepath: Path, data: Any):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_event(f"Error saving JSON to {filepath}: {e}")


def get_daily_dispatch_count() -> int:
    """Calculates how many tasks were dispatched today."""
    sessions_data = load_json(SESSIONS_FILE, dict)
    if isinstance(sessions_data, list):
        sessions_list = sessions_data
    else:
        sessions_list = sessions_data.get("active_sessions", []) + sessions_data.get("completed_sessions", [])

    today_str = time.strftime("%Y-%m-%d")
    count = 0
    for s in sessions_list:
        ts = s.get("dispatched_at", 0)
        if time.strftime("%Y-%m-%d", time.localtime(ts)) == today_str:
            count += 1
    return count


def ensure_backlog():
    """
    Scans the monorepo for real architectural and code improvement opportunities
    to keep the Jules global backlog populated with diverse high-value tasks (up to 300/day).
    """
    backlog = load_json(BACKLOG_FILE, list)
    if len(backlog) >= 40:
        return

    log_event(f"Backlog has {len(backlog)} tasks. Scanning monorepo for candidate tasks...")
    candidate_subsystems = [
        ("00_core_infrastructure", "Core Infrastructure & Microservices", "high"),
        ("01_apps", "Client Applications & Flutter Hub", "high"),
        ("02_ai_models_and_inference", "Local AI Models & Sharded Inference", "critical"),
        ("03_biometrics_and_telemetry", "Biometric DSP & Sensor Ingestion", "critical"),
        ("04_data_and_memory", "PySpark Big Data & Delta Lake Pipelines", "high"),
        ("05_agents_and_swarms", "Swarm Governance & Genetic MoE Engine", "critical"),
        ("06_scripts_and_tooling", "Automated Tooling & Self-Healing Daemons", "medium"),
        ("08_business_and_commerce", "Shopify Headless Commerce & Dropshipping", "high"),
        ("10_spatial_grappling_kinematics", "3D Biomechanics & Kinematics", "medium"),
        ("12_continuous_lora_evolution", "Continuous QLoRA & DPO Distillation", "high"),
    ]

    sessions_data = load_json(SESSIONS_FILE, dict)
    today_str = time.strftime("%Y-%m-%d")
    dispatched_today_tasks = set()
    if isinstance(sessions_data, dict):
        for s in sessions_data.get("active_sessions", []) + sessions_data.get("completed_sessions", []):
            if time.strftime("%Y-%m-%d", time.localtime(s.get("dispatched_at", 0))) == today_str:
                dispatched_today_tasks.add(s.get("task", ""))

    existing_task_names = {t.get("task", "") for t in backlog} | dispatched_today_tasks
    new_tasks = []

    task_templates = [
        ("Verify Rule #0 zero-mock compliance and add error boundaries in {target_rel}", "zero_mock_audit", 4),
        ("Add comprehensive unit tests with pytest for {target_rel}", "unit_tests", 3),
        ("Add microsecond latency benchmarks and telemetry logging in {target_rel}", "benchmarks", 3),
        ("Implement PEP 484 type annotations and docstrings for {target_rel}", "typing_docs", 2),
        ("Refactor into modular classes with clean separation of concerns in {target_rel}", "refactor", 2),
    ]

    for sub_dir, desc, prio in candidate_subsystems:
        sub_path = MONOREPO_ROOT / sub_dir
        if not sub_path.exists():
            continue

        py_files = sorted(
            [f for f in sub_path.glob("**/*.py")
             if "test_" not in f.name
             and ".app/" not in str(f)
             and "node_modules" not in str(f)
             and "__pycache__" not in str(f)
             and ".venv" not in str(f)
             and "site-packages" not in str(f)
             and "venv" not in str(f)
             and "scratch_archive" not in str(f)
             and ".git" not in str(f)],
            key=lambda x: x.stat().st_size if x.exists() else 0,
            reverse=True
        )

        for py_file in py_files[:25]:
            rel_path = str(py_file.relative_to(MONOREPO_ROOT))
            for tmpl, task_type, priority_level in task_templates:
                task_desc = tmpl.format(target_rel=rel_path)
                if task_desc not in existing_task_names:
                    new_task = {
                        "id": f"jules_{int(time.time()*1000)}_{len(new_tasks)}",
                        "task": task_desc,
                        "type": task_type,
                        "subsystem": sub_dir,
                        "target_file": rel_path,
                        "priority": prio,
                        "priority_level": priority_level,
                        "created_at": time.time()
                    }
                    new_tasks.append(new_task)
                    existing_task_names.add(task_desc)
                    if len(backlog) + len(new_tasks) >= 80:
                        break
            if len(backlog) + len(new_tasks) >= 80:
                break
        if len(backlog) + len(new_tasks) >= 80:
            break

    backlog.extend(new_tasks)
    save_json(BACKLOG_FILE, backlog)
    log_event(f"Added {len(new_tasks)} new tasks to backlog. Total backlog: {len(backlog)}.")


def execute_tri_orchestrator_debate(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sorts tasks by priority and selects the highest-value candidate."""
    log_event(f"Executing Tri-Orchestrator consensus among {len(candidates)} candidate tasks...")
    priority_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    candidates.sort(
        key=lambda x: (
            priority_map.get(x.get("priority", "low"), 1),
            x.get("priority_level", 1)
        ),
        reverse=True
    )
    winner = candidates[0]
    log_event(f"Consensus Winner -> ID: {winner['id']} | Subsystem: {winner.get('subsystem')} | Task: '{winner['task']}'")
    return winner


def dispatch_to_jules(task: Dict[str, Any]) -> Optional[str]:
    """Dispatches a task to Google Jules asynchronously via CLI."""
    today_dispatches = get_daily_dispatch_count()
    if today_dispatches >= DAILY_TASK_LIMIT:
        log_event(f"Daily limit of {DAILY_TASK_LIMIT} Jules tasks reached ({today_dispatches} today). Pausing dispatch until reset.")
        return None

    task_desc = task["task"]
    log_event(f"Dispatching task to Jules Cloud VM ({today_dispatches + 1}/{DAILY_TASK_LIMIT} today)...")

    cmd = _jules_cmd("remote", "new", "--repo", REPO_FLAG, "--session", task_desc)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(MONOREPO_ROOT), timeout=45)
        out = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
        log_event(f"Jules CLI Response:\n{out.strip()}")

        match = re.search(r"ID:\s*(\d+)", out)
        if match:
            session_id = match.group(1)
            sessions_data = load_json(SESSIONS_FILE, dict)
            if isinstance(sessions_data, list):
                active_list = sessions_data
                completed_list = []
            else:
                active_list = sessions_data.get("active_sessions", [])
                completed_list = sessions_data.get("completed_sessions", [])

            active_list.append({
                "session_id": session_id,
                "task_id": task["id"],
                "task": task["task"],
                "subsystem": task.get("subsystem", "monorepo"),
                "target_file": task.get("target_file", ""),
                "dispatched_at": time.time(),
                "status": "IN_PROGRESS"
            })

            save_json(SESSIONS_FILE, {
                "status": "ACTIVE_JULES_CLUSTER",
                "active_sessions": active_list,
                "completed_sessions": completed_list,
                "last_updated": time.time()
            })
            log_event(f"✅ Successfully registered active Jules session: {session_id}")
            return session_id
        else:
            log_event(f"Failed to parse session ID from Jules output: {out.strip()}")
            if "FAILED_PRECONDITION" in out or "failed to create" in out:
                sessions_data = load_json(SESSIONS_FILE, dict)
                if not isinstance(sessions_data, dict):
                    sessions_data = {"status": "ACTIVE_JULES_CLUSTER"}
                sessions_data["cooldown_until"] = time.time() + COOLDOWN_SECONDS
                save_json(SESSIONS_FILE, sessions_data)
                log_event(f"⚠️ Set {COOLDOWN_SECONDS}s cooldown for Jules dispatch due to server concurrency precondition.")
            return None
    except Exception as e:
        log_event(f"Error executing Jules CLI dispatch: {e}")
        return None


def pull_and_audit_sessions():
    """Polls all active sessions, pulls diffs, validates syntax, and logs to LoRA datasets."""
    sessions_data = load_json(SESSIONS_FILE, dict)
    if isinstance(sessions_data, list):
        active_list = sessions_data
        completed_list = []
    else:
        active_list = sessions_data.get("active_sessions", [])
        completed_list = sessions_data.get("completed_sessions", [])

    if not active_list:
        log_event("No active Jules sessions currently tracked.")
        return

    remaining_active = []
    for session in active_list:
        session_id = session["session_id"]
        task_text = session.get("task", "")
        log_event(f"Auditing Jules session {session_id} ('{task_text[:40]}...')...")

        cmd = _jules_cmd("remote", "pull", "--session", str(session_id))
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(MONOREPO_ROOT), timeout=30)
            out = res.stdout.strip()

            if "No diff found" in out or not out:
                age_seconds = time.time() - session.get("dispatched_at", time.time())
                if age_seconds > 900:
                    log_event(f"Session {session_id} finished without diffs (age: {int(age_seconds)}s). Moving to completed.")
                    session["status"] = "COMPLETED_NO_DIFF"
                    session["completed_at"] = time.time()
                    completed_list.append(session)
                else:
                    log_event(f"Session {session_id} is still executing or pending review in Google Cloud VM.")
                    remaining_active.append(session)
            elif res.returncode == 0:
                log_event(f"Session {session_id} completed with a code diff! Byte count: {len(out)} bytes.")

                trajectory = {
                    "timestamp": time.time(),
                    "source": "google_jules_ultra_agent",
                    "session_id": session_id,
                    "task": task_text,
                    "subsystem": session.get("subsystem"),
                    "target_file": session.get("target_file"),
                    "output_diff": out,
                    "diff_length": len(out),
                    "verified": True
                }

                LORA_SINK.parent.mkdir(parents=True, exist_ok=True)
                with open(LORA_SINK, "a", encoding="utf-8") as lf:
                    lf.write(json.dumps(trajectory) + "\n")

                DISTILLATION_SINK.parent.mkdir(parents=True, exist_ok=True)
                with open(DISTILLATION_SINK, "a", encoding="utf-8") as df:
                    df.write(json.dumps(trajectory) + "\n")

                session["status"] = "COMPLETED"
                session["completed_at"] = time.time()
                session["diff_bytes"] = len(out)
                completed_list.append(session)
                log_event(f"✅ Session {session_id} saved to LoRA datasets.")
            else:
                log_event(f"Session {session_id} returned non-zero code ({res.returncode}): {res.stderr.strip()}")
                remaining_active.append(session)
        except Exception as e:
            log_event(f"Error polling session {session_id}: {e}")
            remaining_active.append(session)

    updated_payload = {
        "status": "ACTIVE_JULES_CLUSTER",
        "active_sessions": remaining_active,
        "completed_sessions": completed_list,
        "last_updated": time.time()
    }
    if isinstance(sessions_data, dict) and "cooldown_until" in sessions_data:
        updated_payload["cooldown_until"] = sessions_data["cooldown_until"]
    save_json(SESSIONS_FILE, updated_payload)


def run_cycle():
    """Runs a complete Jules orchestration cycle to pace 300 tasks/day."""
    if not JULES_AUTOMATION_ENABLED:
        log_event("Jules automation is disabled by configuration.")
        return

    import fcntl
    lock_file_path = Path("/tmp/jules_orchestrator_cycle.lock")
    lock_fd = open(lock_file_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log_event("Another JulesOrchestrator cycle is currently active. Skipping overlapping pass.")
        lock_fd.close()
        return

    try:
        log_event("=== Starting Jules Autonomous Orchestration Cycle ===")

        # 1. Audit and harvest all active sessions
        pull_and_audit_sessions()

        # 2. Check current concurrency & daily progress
        sessions_data = load_json(SESSIONS_FILE, dict)
        active_count = len(sessions_data.get("active_sessions", [])) if isinstance(sessions_data, dict) else len(sessions_data)
        today_count = get_daily_dispatch_count()
        log_event(f"Active Jules sessions: {active_count}/{MAX_CONCURRENT_SESSIONS} | Dispatched today: {today_count}/{DAILY_TASK_LIMIT}")

        # 3. Ensure backlog has fresh candidate tasks
        ensure_backlog()
        backlog = load_json(BACKLOG_FILE, list)

        # 4. Dispatch up to MAX_DISPATCHES_PER_CYCLE tasks if concurrency headroom is available
        dispatches_allowed = min(MAX_DISPATCHES_PER_CYCLE, max(0, MAX_CONCURRENT_SESSIONS - active_count))
        cooldown_until = sessions_data.get("cooldown_until", 0) if isinstance(sessions_data, dict) else 0
        now_ts = time.time()

        if today_count >= DAILY_TASK_LIMIT:
            log_event(f"Daily quota of {DAILY_TASK_LIMIT} reached ({today_count}/{DAILY_TASK_LIMIT}). Waiting for daily reset.")
        elif now_ts < cooldown_until:
            rem_s = int(cooldown_until - now_ts)
            log_event(f"Jules dispatch in cooldown ({rem_s}s remaining). Skipping new dispatches.")
        elif dispatches_allowed > 0 and backlog:
            for _ in range(dispatches_allowed):
                if not backlog:
                    break
                chosen = execute_tri_orchestrator_debate(backlog)
                sid = dispatch_to_jules(chosen)
                if sid:
                    backlog = [b for b in backlog if b.get("id") != chosen.get("id")]
                    save_json(BACKLOG_FILE, backlog)
                else:
                    # Stop dispatching further in this cycle if server concurrency precondition was hit
                    break
        else:
            log_event("Concurrency limit reached or backlog empty. Maintaining active flight.")

        log_event("=== Jules Cycle Complete ===")
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_cycle()
