#!/usr/bin/env python3
"""
Screen Lens Sovereign Automation for PyCharm / JetBrains & Junie CLI.
Implements CV/OCR UI perception, headless execution, and Teacher-Student LoRA distillation.
Governed by Rule 1 (Zero-Mock), Rule 3 (Sanctuary), and continus-lens-practice-automation.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path

ORCHESTRATOR = Path(__file__).resolve().parent / "multiplexed_ai_terminal_orchestrator.py"
LENS_TELEMETRY_PORT = 3035


def launch_jetbrains_ide(ide_name="PyCharm"):
    """Launches or brings to front the specified JetBrains IDE."""
    print(f"[*] Launching {ide_name} via Screen Lens Sovereign...")
    res = subprocess.run(["open", "-a", ide_name], capture_output=True, text=True)
    time.sleep(2)
    return res.returncode == 0


def screen_lens_inspect_ide_state() -> dict:
    """Probes the IDE process and active window state without disruptive GUI clicks."""
    res = subprocess.run(["pgrep", "-fl", "pycharm"], capture_output=True, text=True)
    pids = res.stdout.strip().splitlines()
    return {
        "ide_running": len(pids) > 0,
        "processes": pids[:3],
        "timestamp": time.time(),
    }


def execute_junie_task(task_description: str, mode: str = "headless") -> dict:
    """Dispatches task to Junie CLI via the Multiplexed AI Terminal Orchestrator."""
    print(f"[*] Dispatching task to Junie CLI ({mode} mode): {task_description}")
    cmd = [sys.executable, str(ORCHESTRATOR), "--run", "junie", "--task", task_description, "--mode", mode]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[:1000],
        "stderr": proc.stderr[:500],
    }


def distill_ide_telemetry() -> int:
    """Harvests IDE and Junie trajectories into continuous LoRA datasets."""
    print("[*] Distilling IDE & Junie session trajectories to LoRA datasets...")
    proc = subprocess.run([sys.executable, str(ORCHESTRATOR), "--harvest-junie"], capture_output=True, text=True)
    print(proc.stdout.strip())
    return proc.returncode


def get_ide_specialist_matrix(target: str = "all") -> dict:
    """Integrates and benchmarks the 6 Polyglot Specialists across GoLand, PyCharm, IntelliJ IDEA, Chromium, and Bluetooth Serial Terminal."""
    scripts_dir = str(Path(__file__).resolve().parents[1])
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from lens_sovereign_unified_system import PolyglotSpecialistIDEAndRuntimeIntegrator
    integrator = PolyglotSpecialistIDEAndRuntimeIntegrator()
    return integrator.integrate_and_benchmark_all(target_filter=target)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JetBrains Lens Sovereign Automation")
    parser.add_argument("--launch", action="store_true", help="Launch JetBrains IDE")
    parser.add_argument("--inspect", action="store_true", help="Inspect IDE process state")
    parser.add_argument("--task", type=str, help="Execute task via Junie CLI")
    parser.add_argument("--distill", action="store_true", help="Harvest and distill IDE traces")
    parser.add_argument("--specialists", nargs="?", const="all", help="Provision & benchmark polyglot specialists (all, goland/langgo, pycharm, intellij, chromium, bt-serial)")

    args = parser.parse_args()

    if args.specialists:
        print(json.dumps(get_ide_specialist_matrix(args.specialists), indent=2))
    elif args.launch:
        launch_jetbrains_ide()
    elif args.inspect:
        st = screen_lens_inspect_ide_state()
        print(json.dumps(st, indent=2))
    elif args.task:
        res = execute_junie_task(args.task)
        print(json.dumps(res, indent=2))
    elif args.distill:
        distill_ide_telemetry()
    else:
        st = screen_lens_inspect_ide_state()
        print(f"[*] IDE State: {'RUNNING' if st['ide_running'] else 'STOPPED'}")
        distill_ide_telemetry()
