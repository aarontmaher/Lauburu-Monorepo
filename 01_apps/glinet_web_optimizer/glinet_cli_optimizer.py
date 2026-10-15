# -*- coding: utf-8 -*-
"""
GL.iNet CLI Network & Kernel Optimizer
======================================
Subsystem: 01_apps/glinet_web_optimizer/glinet_cli_optimizer.py
Lauburu Mesh Ecosystem — 2026

Command-Line Interface for low-latency kernel, network, sysctl,
QoS Cake queueing, Tailscale WireGuard, and 500 MB cgroup tuning.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("GLiNetCLIOptimizer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Dynamically import RouterDualWorldTester
_sim_path = Path(__file__).resolve().parents[2] / "02_ai_models_and_inference" / "simulation" / "router_dual_world_tester.py"
_mod = _load_module("router_dual_world_tester", _sim_path)
RouterDualWorldTester = _mod.RouterDualWorldTester


@dataclass
class CLICommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    dual_world_safety_score: float
    executed: bool


class GLiNetCLIOptimizer:
    """
    CLI Optimizer applying direct uci, sysctl, tc, and tailscale tuning.
    """

    def __init__(self, dry_run: bool = False, dual_world_tester: Optional[Any] = None):
        self.dry_run = dry_run
        self.tester = dual_world_tester or RouterDualWorldTester()
        self.history: List[CLICommandResult] = []

    def execute_safe_command(
        self,
        command_str: str,
        action_name: str = "cli_tune",
        params: Optional[Dict[str, Any]] = None,
    ) -> CLICommandResult:
        """
        Runs dual-world lookahead validation before executing a CLI mutation.
        """
        params = params or {}
        sim_res = self.tester.evaluate_healing_trajectory(
            action_name=action_name,
            parameters=params,
            lookahead_steps=10,
        )

        if not sim_res.is_safe:
            logger.warning(f"❌ Rejected by Dual-World Safety Gate (Score: {sim_res.agentworld_safety_score:.2f}): {command_str}")
            res = CLICommandResult(
                command=command_str,
                exit_code=126,
                stdout="",
                stderr="[REJECTED_BY_DUAL_WORLD_GATE]",
                dual_world_safety_score=sim_res.agentworld_safety_score,
                executed=False,
            )
            self.history.append(res)
            return res

        if self.dry_run:
            logger.info(f"🔍 [DRY-RUN] Would execute: {command_str}")
            res = CLICommandResult(
                command=command_str,
                exit_code=0,
                stdout="[DRY-RUN_SUCCESS]",
                stderr="",
                dual_world_safety_score=sim_res.agentworld_safety_score,
                executed=False,
            )
            self.history.append(res)
            return res

        logger.info(f"⚡ Executing CLI Optimization: {command_str}")
        try:
            p = subprocess.run(
                command_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            res = CLICommandResult(
                command=command_str,
                exit_code=p.returncode,
                stdout=p.stdout.strip(),
                stderr=p.stderr.strip(),
                dual_world_safety_score=sim_res.agentworld_safety_score,
                executed=True,
            )
        except Exception as e:
            res = CLICommandResult(
                command=command_str,
                exit_code=1,
                stdout="",
                stderr=str(e),
                dual_world_safety_score=sim_res.agentworld_safety_score,
                executed=False,
            )

        self.history.append(res)
        return res

    def optimize_bbr_and_sysctl(self) -> List[CLICommandResult]:
        """Configures BBR TCP Congestion Control and Cake default queue discipline."""
        commands = [
            ("sysctl -w net.core.default_qdisc=cake", "sysctl_qdisc"),
            ("sysctl -w net.ipv4.tcp_congestion_control=bbr", "sysctl_bbr"),
            ("sysctl -w net.ipv4.tcp_fastopen=3", "sysctl_tfo"),
        ]
        results = []
        for cmd, name in commands:
            results.append(self.execute_safe_command(cmd, action_name=name))
        return results

    def optimize_cake_sqm(self, interface: str = "eth0", bandwidth_mbps: int = 450) -> CLICommandResult:
        """Applies Cake Smart Queue Management to eradicate bufferbloat."""
        cmd = f"tc qdisc replace dev {interface} root cake bandwidth {bandwidth_mbps}mbit rtt 100ms autorate-ingress"
        return self.execute_safe_command(cmd, action_name="tc_cake_sqm", params={"interface": interface, "bandwidth": bandwidth_mbps})

    def optimize_tailscale_wireguard(self, mtu: int = 1420) -> List[CLICommandResult]:
        """Tunes Tailscale WireGuard encapsulation parameters."""
        commands = [
            (f"ip link set dev tailscale0 mtu {mtu}", "mtu_clamping", {"tailscale_mtu": mtu}),
            ("tailscale set --accept-routes=true", "tailscale_accept_routes", {}),
        ]
        results = []
        for cmd, name, p in commands:
            results.append(self.execute_safe_command(cmd, action_name=name, params=p))
        return results

    def optimize_500mb_cgroups(self, limit_mb: int = 120) -> CLICommandResult:
        """Enforces strict 500 MB (120 MB AI quota) cgroups v2 memory ceiling."""
        bytes_val = limit_mb * 1024 * 1024
        cmd = f"echo {bytes_val} > /sys/fs/cgroup/ai_supervisor/memory.max"
        return self.execute_safe_command(cmd, action_name="cgroup_memory_rebalance", params={"cap_mb": limit_mb})


def main():
    parser = argparse.ArgumentParser(description="GL.iNet CLI Network & Kernel Optimizer")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without applying shell mutations")
    parser.add_argument("--all", action="store_true", help="Apply full optimization suite (BBR, SQM, Tailscale, Cgroups)")
    parser.add_argument("--sqm", action="store_true", help="Apply Cake Smart Queue Management")
    parser.add_argument("--tailscale", action="store_true", help="Optimize Tailscale WireGuard interface")
    parser.add_argument("--cgroups", type=int, default=120, help="Set AI Cgroup memory ceiling in MB")
    args = parser.parse_args()

    opt = GLiNetCLIOptimizer(dry_run=args.dry_run)
    print("🚀 Starting GL.iNet CLI Network & Kernel Optimization...")

    if args.all or args.sqm:
        print("📊 Applying Cake SQM Bufferbloat optimization...")
        opt.optimize_cake_sqm()

    if args.all:
        print("🧠 Applying BBR TCP Congestion Control...")
        opt.optimize_bbr_and_sysctl()

    if args.all or args.tailscale:
        print("🔒 Optimizing Tailscale WireGuard encapsulation...")
        opt.optimize_tailscale_wireguard()

    if args.all:
        print(f"🛡️ Enforcing 500MB Cgroup RAM Ceiling ({args.cgroups} MB AI Cap)...")
        opt.optimize_500mb_cgroups(limit_mb=args.cgroups)

    print(f"\n✅ Optimization complete! Applied {len([h for h in opt.history if h.executed or h.exit_code == 0])} directives.")


if __name__ == "__main__":
    main()
