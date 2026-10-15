#!/usr/bin/env python3
"""
Omniterminal & Continuous ML Supervisor Daemon
=============================================
Subsystem: 06_scripts_and_tooling/omniterminal_production_supervisor.py
Lauburu Mesh — Silent 24/7 Background Runner for Omniterminal & Telemetry Watchdog

Supervises:
  1. Omniterminal Virtual PTY Daemon (/tmp/omniterminal.sock & TCP port 4001)
  2. Autonomous ML Trainer, Cloud AI Optimizer & Project Telemetry Watchdog
  3. Network-Adaptive AI Governor
"""

from __future__ import annotations

import os
import sys
import time
import signal
import asyncio
import logging
import threading
from pathlib import Path

# Add project paths to sys.path
PROJECT_DIR = Path("/Users/aaron/teamwork_projects/unified_resilient_serial_terminal_ide")
MONOREPO_DIR = Path("/Volumes/Lauburu-Monorepo")
WORKSPACE_ROOT = MONOREPO_DIR

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(PROJECT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR / "src"))
if str(MONOREPO_DIR) not in sys.path:
    sys.path.insert(0, str(MONOREPO_DIR))
if str(MONOREPO_DIR / "05_agents_and_swarms/continuous_ml_trainer") not in sys.path:
    sys.path.insert(0, str(MONOREPO_DIR / "05_agents_and_swarms/continuous_ml_trainer"))
if str(MONOREPO_DIR / "05_agents_and_swarms/genetic_moe") not in sys.path:
    sys.path.insert(0, str(MONOREPO_DIR / "05_agents_and_swarms/genetic_moe"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("omniterminal.supervisor")


async def run_omniterminal():
    """Runs the virtual PTY multiplexer daemon."""
    from src.omniterminal.daemon import OmniterminalDaemon
    daemon = OmniterminalDaemon(socket_path="/tmp/omniterminal.sock", tcp_port=4001, enable_hotplug=True)
    # Pre-spawn default session 1
    session = daemon.get_or_create_session(session_id=1, shell_cmd=["/bin/zsh", "-l"])
    logger.info(f"Initialized Session 1 with child PID {session.child_pid}")
    await daemon.start()
    logger.info("Omniterminal daemon active on /tmp/omniterminal.sock and TCP 4001")
    try:
        while True:
            await asyncio.sleep(10.0)
    except asyncio.CancelledError:
        logger.info("Stopping Omniterminal daemon...")
        await daemon.stop()


def run_telemetry_loop():
    """Runs the autonomous ML trainer, self-optimizer and project telemetry auditor in background thread."""
    from autonomous_ml_optimizer_daemon import AutonomousOptimizerEngine
    from network_adaptive_ai_governor import NetworkAdaptiveAIGovernor
    import importlib.util

    opt_path = WORKSPACE_ROOT / "05_agents_and_swarms/tool_ecosystem/continuous_self_optimizer.py"
    spec = importlib.util.spec_from_file_location("continuous_self_optimizer", str(opt_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    self_optimizer = mod.ContinuousSelfOptimizer()

    engine = AutonomousOptimizerEngine()
    gov = NetworkAdaptiveAIGovernor()

    logger.info("Starting Autonomous ML Trainer, Self-Optimizer & Telemetry Watchdog loop...")
    while True:
        try:
            # 1. Audit all local services, hardware, LoRA pairs, cloud pacing
            rep = engine.run_cycle()
            # 2. Re-evaluate network topology & model routing
            strat = gov.evaluate_strategy()
            # 3. Continuous Self-Optimizer with Frontier Local & Cloud Model Oversight
            opt_rep = self_optimizer.run_optimization_cycle()
            online_count = sum(1 for s in rep["services"].values() if s["online"])
            logger.info(
                f"[WATCHDOG] Topology: {strat['active_topology']} | Services: {online_count}/{len(rep['services'])} UP | "
                f"RAM Headroom: {rep['trainer']['host_ram_headroom_gb']}GB | LoRA Pairs: {rep['trainer']['total_dataset_lines']} | "
                f"Self-Opt Gen: {opt_rep['generation']} (Fitness: {opt_rep['average_system_fitness']}%)"
            )
        except Exception as e:
            logger.error(f"Error in telemetry loop: {e}")
        time.sleep(20.0)


async def main():
    # Start telemetry in background daemon thread
    t_thread = threading.Thread(target=run_telemetry_loop, daemon=True)
    t_thread.start()

    # Run omniterminal in main async loop
    await run_omniterminal()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Supervisor terminated by user.")
