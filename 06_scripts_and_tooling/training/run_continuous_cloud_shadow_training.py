#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
06_scripts_and_tooling/training/run_continuous_cloud_shadow_training.py
================================================================================
Autonomous CLI Runner: Continuous Local AI Training with Cloud Model Shadowing
--------------------------------------------------------------------------------
Lauburu Mesh Ecosystem — 2026

Executes the continuous autonomous outperformance training loop:
- AI Debate Tri-Orchestrator Council (Qwen 3.8 Max, Kimi Titan, Gemini, Abliterated)
- Cloud Model Shadowing Quality Audit (Zero-mock DPO pair harvesting)
- Screen Lens Sovereign Apple Silicon Metal GPU training steps on Device(gpu, 0)
- Neo Execution Task Tracker integration
- Gate 8 Significant Outperformance Verification (COI >= 1.15x, 100% Exit Code 0)
================================================================================
"""

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/Volumes/Lauburu-Monorepo")
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RUNNER_LOG = LOGS_DIR / "continuous_cloud_shadow_training.log"

# Setup Dual Logging
file_handler = logging.FileHandler(RUNNER_LOG, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [ShadowRunner] %(message)s"))

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger("ContinuousShadowRunner")

PROTOCOLS_DIR = REPO_ROOT / "05_agents_and_swarms" / "training_protocols"
if str(PROTOCOLS_DIR) not in sys.path:
    sys.path.insert(0, str(PROTOCOLS_DIR))

try:
    from continuous_cloud_shadow_outperformance_engine import (
        ContinuousCloudShadowOutperformanceEngine,
        check_host_ram_headroom
    )
except ImportError as err:
    logger.error(f"Failed to import ContinuousCloudShadowOutperformanceEngine: {err}")
    sys.exit(1)


stop_requested = False

def handle_signal(sig, frame):
    global stop_requested
    logger.info(f"Signal {sig} received. Requesting clean shutdown...")
    stop_requested = True

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Runner for Continuous Local AI Training with Cloud Shadowing"
    )
    parser.add_argument("--mode", choices=["sweep", "daemon", "debate_only"], default="sweep",
                        help="Execution mode (sweep, daemon, debate_only)")
    parser.add_argument("--epochs", type=int, default=2, help="Number of training epochs")
    parser.add_argument("--interval", type=float, default=30.0, help="Daemon interval in seconds")
    parser.add_argument("--target-coi", type=float, default=1.15, help="Target significant COI")
    parser.add_argument("--verify-significant", action="store_true", default=True,
                        help="Assert Gate 8 outperformance stopping invariant")
    args = parser.parse_args()

    # Pre-Flight RAM and Headroom check (Rule #3)
    is_safe, avail_gb, pct_used = check_host_ram_headroom()
    logger.info(f"Host Memory Pre-Flight: {pct_used}% used, {avail_gb} GB available. Safe: {is_safe}")
    if not is_safe:
        logger.error(f"Host RAM utilization exceeded safety buffer ({pct_used}% > 90.0%). Aborting.")
        sys.exit(1)

    engine = ContinuousCloudShadowOutperformanceEngine()

    if args.mode == "debate_only":
        logger.info("Executing Tri-Orchestrator AI Debate Deliberation...")
        consensus = engine.debate_council.conduct_deliberation(
            topic="Continuous Local AI Outperformance via Cloud Shadowing",
            subsystem="Swarm Intelligence & Metal Acceleration",
            min_consensus=0.98
        )
        logger.info(f"Debate completed. Agreement Score: {consensus.final_agreement_score * 100:.2f}%")
        logger.info(f"Synthesized Decision: {consensus.synthesized_decision}")
        return

    if args.mode == "sweep":
        logger.info(f"Executing Multi-Epoch Sweep (min_epochs={args.epochs}, target_coi={args.target_coi}x)...")
        results, meta = engine.run_continuous_training_loop(
            min_epochs=args.epochs,
            max_epochs=max(args.epochs, 5),
            target_coi=args.target_coi,
            verify_significant=args.verify_significant
        )
        logger.info(f"Sweep Finished! Converged at Epoch {meta['converged_epoch']}. All 7 projects verified.")
        for r in results:
            logger.info(
                f"  [{r.project_id}] {r.student_name}: COI={r.coi_score:.4f}x | "
                f"Sig={r.is_significant} | ExitCode={r.verification_exit_code}"
            )
        return

    if args.mode == "daemon":
        logger.info(f"Starting 24/7 Autonomous Daemon loop (interval={args.interval}s, initial target_coi={args.target_coi}x)...")
        epoch = 1
        active_target_coi = args.target_coi
        while not stop_requested:
            try:
                # Pre-flight check before each daemon epoch
                is_safe, avail_gb, pct_used = check_host_ram_headroom()
                if not is_safe:
                    logger.warning(f"RAM headroom constrained ({avail_gb} GB available). Pausing for 60s...")
                    time.sleep(60.0)
                    continue

                logger.info(f"--- Daemon Epoch {epoch} (Active Dynamic Target COI: {active_target_coi:.2f}x) ---")
                results = engine.run_full_sweep(epoch=epoch, target_coi=active_target_coi)

                # Dynamic Progressive Target Ratchet (Uncapped Mandate)
                if results and all(r.coi_score >= active_target_coi and r.verification_exit_code == 0 for r in results):
                    min_achieved = min(r.coi_score for r in results)
                    active_target_coi = round(max(active_target_coi + 0.05, min_achieved * 0.98), 2)
                    logger.info(f"🔥 UNRESTRICTED ELEVATION: All 7 projects exceeded threshold! Ratcheting target COI up to {active_target_coi:.2f}x!")

                epoch += 1

                for _ in range(int(args.interval)):
                    if stop_requested:
                        break
                    time.sleep(1.0)
            except Exception as err:
                logger.error(f"Error during daemon cycle: {err}")
                time.sleep(10.0)

        logger.info("Daemon cleanly terminated.")


if __name__ == "__main__":
    main()
