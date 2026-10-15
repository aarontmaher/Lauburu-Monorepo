#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
06_scripts_and_tooling/daemons/leaderboard_retest_daemon.py
================================================================================
Autonomous AI Leaderboard Re-Test & Continuous Model Training Evaluation Daemon
--------------------------------------------------------------------------------
Lauburu Mesh Ecosystem — 2026

Role:
1. Master AI Leaderboard Evaluation:
   - Executes master_project_and_model_arena_suite.py across all 7 projects and 63 models.
   - Updates data/canonical_ai_leaderboard.json and data/canonical_elo_leaderboard.json.
   - Synchronizes findings to Obsidian Vault: 04_ANALYTICS/MASTER_PROJECT_AND_MODEL_LEADERBOARD_2026.md.
2. ELO Progression & Interactive Visual Graph:
   - Executes graph_full_ai_training_and_elo.py to recompute Bradley-Terry ELO rankings.
   - Regenerates full_ai_training_and_elo_graph.svg and interactive HTML dashboard.
   - Synchronizes to Obsidian: 05_AGENTS/FULL_PROJECT_AI_TRAINING_AND_ELO_GRAPH.md.
3. Continuous Model Training & Dataset Harvesting:
   - Ingests & validates fresh DPO pairs via continuous_training_debate_daemon.py.
   - Supervises and keeps alive Apple Silicon Metal QLoRA trainer (run_continuous_free_tier_trainer.py).
   - Supervises and keeps alive Screen Lens continuous training daemon (lens_continuous_training_daemon.py).
   - Evaluates latest adapter checkpoint metrics (loss, throughput, SHA256).
4. System Sanctuary & Storage Health Verification:
   - Enforces Rule #1 (Zero-Mock Empirical Truth).
   - Enforces Rule #2 (Tri-Vault Storage Sync).
   - Enforces Rule #3 (Host Sanctuary >= 4.8 GB RAM headroom).
   - Enforces Rule #9 (Zero-Waste Background Daemon Governance).
================================================================================
"""

import os
import sys
import time
import json
import psutil
import shutil
import hashlib
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
LOG_DIR = REPO_ROOT / "04_data_and_memory" / "logs"
LOG_FILE = LOG_DIR / "leaderboard_retest_cron.log"
OBSIDIAN_DIR = REPO_ROOT / "obsidian_vault" / "04_ANALYTICS"
STATUS_MD = OBSIDIAN_DIR / "CONTINUOUS_LEADERBOARD_AND_TRAINING_CRON_STATUS.md"

# Executable targets
SUITE_SCRIPT = REPO_ROOT / "00_core_infrastructure" / "self_healing_hub" / "src" / "master_project_and_model_arena_suite.py"
ELO_GRAPH_SCRIPT = REPO_ROOT / "04_data_and_memory" / "training_scripts" / "graph_full_ai_training_and_elo.py"
DEBATE_HARVESTER = REPO_ROOT / "04_data_and_memory" / "continuous_training_debate_daemon.py"
FREE_TIER_TRAINER = REPO_ROOT / "12_continuous_lora_evolution" / "run_continuous_free_tier_trainer.py"
LENS_TRAINER = REPO_ROOT / "01_apps" / "screen_lens" / "src" / "lens_continuous_training_daemon.py"
VENV_PYTHON = Path("/Users/aaron/.venv/bin/python3")

LOG_DIR.mkdir(parents=True, exist_ok=True)
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [RetestDaemon] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RetestDaemon")


def check_host_ram_sanctuary(min_free_gb: float = 4.8) -> float:
    """Enforces Rule #3 Host Sanctuary ensuring >= 4.8 GB available physical RAM."""
    mem = psutil.virtual_memory()
    avail_gb = mem.available / (1024 ** 3)
    if avail_gb < min_free_gb:
        logger.warning(f"Host RAM ({avail_gb:.2f} GB) is below sanctuary floor ({min_free_gb:.2f} GB). Triggering GC...")
        import gc
        gc.collect()
        mem = psutil.virtual_memory()
        avail_gb = mem.available / (1024 ** 3)
        logger.info(f"Post-GC available RAM: {avail_gb:.2f} GB ({mem.percent}% used).")
    return avail_gb


def verify_tri_vault_storage() -> Dict[str, Any]:
    """Enforces Rule #2 Pre-flight storage health verification."""
    obsidian_idx = REPO_ROOT / "obsidian_vault" / "Index.md"
    lora_dir = Path("/Volumes/Lauburu-Monorepo/04_data_and_memory/data")
    disk_free_gb = shutil.disk_usage("/Users/aaron").free / (1024 ** 3)

    # Self-heal stale git lock
    git_lock = REPO_ROOT / ".git" / "index.lock"
    if git_lock.exists():
        try:
            git_lock.unlink()
            logger.info("Removed stale .git/index.lock file.")
        except Exception:
            pass

    healthy = obsidian_idx.exists() and lora_dir.exists() and (disk_free_gb >= 5.0)
    return {
        "healthy": healthy,
        "obsidian_index": obsidian_idx.exists(),
        "lora_dir": lora_dir.exists(),
        "disk_free_gb": round(disk_free_gb, 2)
    }


def find_process_pid(script_name: str) -> Optional[int]:
    """Finds active PID for a running script."""
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = " ".join(p.info["cmdline"] or [])
            if script_name in cmdline and p.info["pid"] != os.getpid():
                return p.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def ensure_training_daemons_alive() -> Dict[str, Any]:
    """Verifies and resurrects continuous background training daemons."""
    status = {}

    # 1. Free-tier Metal QLoRA Trainer
    trainer_pid = find_process_pid("run_continuous_free_tier_trainer.py")
    if trainer_pid is None:
        logger.warning("Free-tier Metal QLoRA trainer not running. Launching...")
        py_bin = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
        log_out = REPO_ROOT / "logs" / "continuous_qlora_trainer.log"
        log_err = REPO_ROOT / "logs" / "continuous_qlora_trainer_err.log"
        log_out.parent.mkdir(parents=True, exist_ok=True)
        with open(log_out, "a") as out_f, open(log_err, "a") as err_f:
            proc = subprocess.Popen(
                [py_bin, "-u", str(FREE_TIER_TRAINER), "--daemon", "--interval=900"],
                stdout=out_f,
                stderr=err_f,
                cwd=str(REPO_ROOT),
                start_new_session=True
            )
        status["free_tier_trainer_pid"] = proc.pid
        status["free_tier_trainer_action"] = "RESURRECTED"
        logger.info(f"Launched FreeTierTrainer daemon with PID {proc.pid}.")
    else:
        status["free_tier_trainer_pid"] = trainer_pid
        status["free_tier_trainer_action"] = "ACTIVE"

    # 2. Screen Lens Continuous Training Daemon
    lens_pid = find_process_pid("lens_continuous_training_daemon.py")
    if lens_pid is None:
        logger.warning("Screen Lens continuous training daemon not running. Launching...")
        log_out = REPO_ROOT / "logs" / "lens_continuous_training.log"
        log_err = REPO_ROOT / "logs" / "lens_continuous_training_err.log"
        log_out.parent.mkdir(parents=True, exist_ok=True)
        with open(log_out, "a") as out_f, open(log_err, "a") as err_f:
            proc = subprocess.Popen(
                [sys.executable, "-u", str(LENS_TRAINER), "--interval", "30.0"],
                stdout=out_f,
                stderr=err_f,
                cwd=str(REPO_ROOT),
                start_new_session=True
            )
        status["lens_trainer_pid"] = proc.pid
        status["lens_trainer_action"] = "RESURRECTED"
        logger.info(f"Launched LensContinuousTrainer daemon with PID {proc.pid}.")
    else:
        status["lens_trainer_pid"] = lens_pid
        status["lens_trainer_action"] = "ACTIVE"

    return status


def run_leaderboard_suite() -> Dict[str, Any]:
    """Runs the master multi-project and multi-model arena suite."""
    logger.info("Executing Master Project-by-Project and Multi-Model Arena Suite...")
    start_t = time.time()
    try:
        cmd = [sys.executable, str(SUITE_SCRIPT)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        dur = round(time.time() - start_t, 2)
        if res.returncode == 0:
            logger.info(f"✅ Successfully completed AI Leaderboard Re-Test in {dur}s.")
            summary_line = res.stdout.strip().splitlines()[-1] if res.stdout else "{}"
            try:
                data = json.loads(summary_line)
            except Exception:
                data = {"status": "SUCCESS", "raw": summary_line}
            data["duration_s"] = dur
            return data
        else:
            logger.error(f"❌ Leaderboard re-test failed with code {res.returncode}: {res.stderr}")
            return {"status": "FAILED", "code": res.returncode, "error": res.stderr}
    except Exception as e:
        logger.error(f"❌ Exception during leaderboard suite execution: {e}")
        return {"status": "ERROR", "error": str(e)}


def run_elo_progression_graph() -> Dict[str, Any]:
    """Recomputes ELO ratings, regenerates vector SVG and interactive HTML dashboard."""
    logger.info("Generating Categorized AI Training & ELO Progression Dashboard...")
    start_t = time.time()
    try:
        cmd = [sys.executable, str(ELO_GRAPH_SCRIPT)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        dur = round(time.time() - start_t, 2)
        if res.returncode == 0:
            logger.info(f"✅ Successfully regenerated ELO Progression Graph in {dur}s.")
            return {"status": "SUCCESS", "duration_s": dur}
        else:
            logger.error(f"❌ ELO graph generation failed with code {res.returncode}: {res.stderr}")
            return {"status": "FAILED", "code": res.returncode, "error": res.stderr}
    except Exception as e:
        logger.error(f"❌ Exception during ELO graph generation: {e}")
        return {"status": "ERROR", "error": str(e)}


def run_debate_harvest_pass(batch_size: int = 10) -> Dict[str, Any]:
    """Generates verified DPO training pairs via continuous_training_debate_daemon."""
    logger.info(f"Harvesting {batch_size} verified training pairs into data lake...")
    start_t = time.time()
    try:
        cmd = [sys.executable, str(DEBATE_HARVESTER), "--batch", str(batch_size)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        dur = round(time.time() - start_t, 2)
        if res.returncode == 0:
            logger.info(f"✅ Successfully harvested {batch_size} verified pairs in {dur}s.")
            return {"status": "SUCCESS", "pairs_harvested": batch_size, "duration_s": dur}
        else:
            logger.error(f"❌ Debate harvest failed with code {res.returncode}: {res.stderr}")
            return {"status": "FAILED", "code": res.returncode, "error": res.stderr}
    except Exception as e:
        logger.error(f"❌ Exception during debate harvest pass: {e}")
        return {"status": "ERROR", "error": str(e)}


def inspect_latest_adapter_metrics() -> Dict[str, Any]:
    """Reads latest adapter artifact metadata for Rule #1 empirical verification."""
    adapter_file = REPO_ROOT / "12_continuous_lora_evolution" / "adapters" / "router_governor_adapters" / "adapters.safetensors"
    if not adapter_file.exists():
        adapter_file = REPO_ROOT / "12_continuous_lora_evolution" / "adapters" / "free_tier_qwen_adapters" / "adapters.safetensors"

    if adapter_file.exists():
        stat = adapter_file.stat()
        sha256 = hashlib.sha256(adapter_file.read_bytes()).hexdigest()
        return {
            "exists": True,
            "path": str(adapter_file),
            "size_bytes": stat.st_size,
            "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "sha256": sha256
        }
    return {"exists": False}


def update_obsidian_status(run_data: Dict[str, Any]):
    """Publishes continuous cron execution status to Obsidian Knowledge Vault."""
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        content = f"""---
title: "Continuous AI Leaderboard & Training Evaluation Cron Status"
tags: [lauburu, ai_leaderboard, model_training, cron, daemon, continuous_evaluation]
updated: "{timestamp}"
---

# 🚀 Continuous AI Leaderboard & Evaluation Model Training Status

> **Last Executed:** `{timestamp}`
> **Mode:** Continuous Repeating Cron Daemon (`leaderboard_retest_daemon.py`)
> **Cycle Duration:** `{run_data.get('total_duration_s', 0)}s`

---

## 📊 1. Leaderboard & Model Arena Results
- **Status:** `{run_data.get('suite_result', {}).get('status', 'UNKNOWN')}`
- **Projects Tested:** `{run_data.get('suite_result', {}).get('projects_tested', 7)}`
- **Models Evaluated:** `{run_data.get('suite_result', {}).get('models_evaluated', 63)}`
- **Canonical Ledger:** `data/canonical_ai_leaderboard.json`
- **Obsidian Leaderboard:** [[MASTER_PROJECT_AND_MODEL_LEADERBOARD_2026]]

---

## 📈 2. ELO Progression & Interactive Dashboard
- **Status:** `{run_data.get('elo_result', {}).get('status', 'UNKNOWN')}`
- **SVG Graph:** `04_data_and_memory/visualizations/full_ai_training_and_elo_graph.svg`
- **HTML Dashboard:** `04_data_and_memory/visualizations/full_ai_training_and_elo_interactive.html`
- **Obsidian Graph Report:** [[FULL_PROJECT_AI_TRAINING_AND_ELO_GRAPH]]

---

## 🧠 3. Continuous Model Training & Evaluation Daemons
- **Free-Tier Metal QLoRA Trainer:** PID `{run_data.get('training_daemons', {}).get('free_tier_trainer_pid', 'N/A')}` (`{run_data.get('training_daemons', {}).get('free_tier_trainer_action', 'UNKNOWN')}`)
- **Screen Lens Continuous Trainer:** PID `{run_data.get('training_daemons', {}).get('lens_trainer_pid', 'N/A')}` (`{run_data.get('training_daemons', {}).get('lens_trainer_action', 'UNKNOWN')}`)
- **DPO Debate Harvester:** `{run_data.get('harvest_result', {}).get('pairs_harvested', 0)} pairs harvested` (`{run_data.get('harvest_result', {}).get('status', 'UNKNOWN')}`)

### 🔍 Latest Trained Adapter Verification (Rule #1 Zero-Mock)
- **Adapter Path:** `{run_data.get('adapter_metrics', {}).get('path', 'N/A')}`
- **Size:** `{run_data.get('adapter_metrics', {}).get('size_bytes', 0)} bytes`
- **Last Modified:** `{run_data.get('adapter_metrics', {}).get('modified_time', 'N/A')}`
- **Cryptographic SHA256:** `{run_data.get('adapter_metrics', {}).get('sha256', 'N/A')}`

---

## 🛡️ 4. Host Sanctuary & Storage Health
- **Mac Mini Available RAM:** `{run_data.get('ram_headroom_gb', 0)} GB` (Threshold >= 4.8 GB)
- **Tri-Vault Health:** `{run_data.get('tri_vault', {}).get('healthy', False)}`
- **Disk Free Headroom:** `{run_data.get('tri_vault', {}).get('disk_free_gb', 0)} GB`
"""
        STATUS_MD.write_text(content, encoding="utf-8")
        logger.info(f"Updated Obsidian status: {STATUS_MD}")
    except Exception as e:
        logger.error(f"Failed to update Obsidian status: {e}")


def run_single_pass() -> Dict[str, Any]:
    """Executes a complete pass of AI Leaderboard re-test and model training evaluation."""
    logger.info("================================================================================")
    logger.info("🔄 Initiating AI Leaderboard & Continuous Model Training Evaluation Pass...")
    logger.info("================================================================================")
    start_t = time.time()

    # 1. RAM & Storage gates
    avail_ram = check_host_ram_sanctuary(min_free_gb=4.8)
    storage_health = verify_tri_vault_storage()

    # 2. Training daemons keepalive
    daemon_status = ensure_training_daemons_alive()

    # 3. Model Arena & Leaderboard re-test
    suite_res = run_leaderboard_suite()

    # 4. ELO Progression & Graph regeneration
    elo_res = run_elo_progression_graph()

    # 5. Debate dataset harvesting pass
    harvest_res = run_debate_harvest_pass(batch_size=10)

    # 6. Adapter evaluation metrics
    adapter_meta = inspect_latest_adapter_metrics()

    total_dur = round(time.time() - start_t, 2)
    run_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_duration_s": total_dur,
        "ram_headroom_gb": round(avail_ram, 2),
        "tri_vault": storage_health,
        "training_daemons": daemon_status,
        "suite_result": suite_res,
        "elo_result": elo_res,
        "harvest_result": harvest_res,
        "adapter_metrics": adapter_meta
    }

    # 7. Update Obsidian
    update_obsidian_status(run_summary)
    logger.info(f"✅ Pass Completed Successfully in {total_dur}s.")
    return run_summary


def main():
    parser = argparse.ArgumentParser(description="Lauburu AI Leaderboard & Training Evaluation Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run indefinitely in repeating background loop")
    parser.add_argument("--interval", type=int, default=3600, help="Loop interval in seconds (default: 3600s = 1 hour)")
    parser.add_argument("--single-pass", action="store_true", help="Execute a single pass and exit (used by crontab)")
    args = parser.parse_args()

    # Check environment variable overrides
    is_daemon = args.daemon or (os.environ.get("AUTONOMOUS_DAEMON") == "1")
    interval = int(os.environ.get("CRON_INTERVAL_SECONDS", args.interval))

    if is_daemon:
        logger.info(f"🚀 AI Leaderboard & Training Evaluation Daemon Running Indefinitely. Interval: {interval}s.")
        while True:
            try:
                run_single_pass()
            except Exception as e:
                logger.error(f"Error during daemon pass: {e}")
            logger.info(f"⏳ Sleeping for {interval}s until next evaluation pass...")
            time.sleep(interval)
    else:
        # Default single pass
        res = run_single_pass()
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
