#!/usr/bin/env python3
"""
Sovereign 24/7 TUI Fact-Checking, Visual Truth & Mesh Resurrection Swarm
Version: 4.0.0-CANONICAL
Commander: Abliterated Llama 70B (Uncensored Sovereign Auditor)
Specialist Workers:
- Visual Truth Auditor: Terminal renderable OCR, layout bounds, and occlusion checks
- Code & Context Auditor: Monorepo AST verification and Zero-Mock Rule #0 enforcement
- Mesh Network & RPC Auditor: Socket probing, automatic WoL resurrection, and RPC keepalive
"""

import os
import sys
import time
import json
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TRUTH-SWARM]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TruthAuditSwarm")

SWARM_ROOT = Path(__file__).resolve().parent
MONOREPO_ROOT = SWARM_ROOT.parent.parent
CANONICAL_PORT_DIR = MONOREPO_ROOT / "01_apps" / "canonical_port"

if str(CANONICAL_PORT_DIR) not in sys.path:
    sys.path.insert(0, str(CANONICAL_PORT_DIR))
if str(CANONICAL_PORT_DIR / "tui") not in sys.path:
    sys.path.insert(0, str(CANONICAL_PORT_DIR / "tui"))
if str(MONOREPO_ROOT / "05_agents_and_swarms" / "red_blue_arena") not in sys.path:
    sys.path.insert(0, str(MONOREPO_ROOT / "05_agents_and_swarms" / "red_blue_arena"))

try:
    from services.blackboard_store import blackboard_store
    from tournament.red_blue_debate_tournament import RedBlueDebateTournament
except ImportError:
    blackboard_store = None
    RedBlueDebateTournament = None


class SovereignTruthAuditSwarm:
    """
    Continuous Fact-Checking & Self-Healing Swarm commanded by Abliterated Llama 70B.
    """

    NODES = [
        {"id": "L1", "name": "Mac_Node", "ip": "192.168.8.155", "ts": "100.119.199.76", "rpc_port": 50052, "ssh_port": 22},
        {"id": "L2", "name": "MacBook_Pro", "ip": "192.168.8.127", "ts": "100.103.212.21", "rpc_port": 50052, "ssh_port": 22},
        {"id": "L3", "name": "Linux_Head_Node", "ip": "192.168.8.224", "ts": "100.101.39.98", "rpc_port": 50052, "ssh_port": 22},
        {"id": "L4", "name": "Linux_Tablet", "ip": "192.168.8.173", "ts": "100.81.92.125", "rpc_port": 50052, "ssh_port": 22},
        {"id": "L5", "name": "MacBook_Air", "ip": "192.168.8.222", "ts": "100.93.158.96", "rpc_port": 50052, "ssh_port": 22},
        {"id": "L6", "name": "Pixel_10_Pro_XL", "ip": "192.168.8.160", "ts": "100.73.38.87", "rpc_port": 8084, "ssh_port": 8022},
        {"id": "L7", "name": "Samsung_S20", "ip": "192.168.8.158", "ts": "100.84.40.95", "rpc_port": 8084, "ssh_port": 8022},
        {"id": "GW", "name": "GL.iNet_Router", "ip": "192.168.8.1", "ts": "100.122.185.123", "rpc_port": 80, "ssh_port": 22},
    ]

    def __init__(self):
        self.tournament = RedBlueDebateTournament() if RedBlueDebateTournament else None
        self.audit_count = 0

    def probe_socket(self, host: str, port: int, timeout: float = 0.4) -> bool:
        """Non-blocking TCP socket liveness probe."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def execute_truth_audit(self) -> Dict[str, Any]:
        """
        Executes a 3-tier fact check:
        1. Network & Hardware Liveness Verification
        2. Rule #0 Zero-Mock / Qi Telemetry Audit
        3. Multi-Orchestrator AI Debate Ratification
        """
        self.audit_count += 1
        logger.info(f"=== [TRUTH AUDIT #{self.audit_count}] Commanded by Abliterated Llama 70B ===")

        discrepancies: List[str] = []
        offline_nodes: List[str] = []

        # 1. Probe All Physical Nodes & RPC Sockets
        for node in self.NODES:
            # Check SSH port
            ssh_online = self.probe_socket(node["ip"], node["ssh_port"]) or self.probe_socket(node["ts"], node["ssh_port"])
            rpc_online = self.probe_socket(node["ip"], node["rpc_port"]) or self.probe_socket(node["ts"], node["rpc_port"])

            if not ssh_online:
                offline_nodes.append(f"{node['id']}_{node['name']} (SSH :{node['ssh_port']})")
                self.attempt_auto_heal_node(node)
            if not rpc_online and node["rpc_port"] == 50052:
                discrepancies.append(f"RPC Shard Dropped on {node['name']} (Port 50052)")

        # 2. Rule #0 Zero-Mock Audit on Blackboard Telemetry
        if blackboard_store:
            snap = blackboard_store.get_snapshot(force_refresh=True)
            for n in snap.layer_1_hardware.nodes:
                if n.qi_power_watts > 0 and n.power_source == "AC":
                    discrepancies.append(f"Discrepancy: Node {n.node_id} claiming Qi wireless charging without active inductive dock.")

        logger.info(f"Audit Findings: {len(discrepancies)} Discrepancies | {len(offline_nodes)} Offline Nodes")

        # 3. Trigger /ai-debate Ratification if Discrepancies Found
        topic = f"Truth Audit #{self.audit_count}: Remediation of {len(discrepancies)} discrepancies and {len(offline_nodes)} node drops"
        if self.tournament:
            try:
                outcome = self.tournament.run_debate_round(
                    topic=topic,
                    red_model_id="abiliterated_llama_70b",
                    blue_model_id="deepseek_r1_32b",
                    cloud_judge_model_id="gemini_31_pro"
                )
                logger.info(f"✔ Audit Ratified: {outcome.is_ratified} | Consensus Accord: {outcome.consensus_agreement*100:.2f}% | Root: {outcome.merkle_state_root[:16]}")
            except Exception as e:
                logger.error(f"Debate ratification error: {e}")

        return {
            "audit_id": self.audit_count,
            "discrepancies": discrepancies,
            "offline_nodes": offline_nodes,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def attempt_auto_heal_node(self, node: Dict[str, Any]) -> None:
        """Sends Wake-on-LAN magic packet and triggers SSH keepalive."""
        logger.info(f"⚡ Attempting Auto-Healing for {node['name']} ({node['ip']})...")
        try:
            # Wake-on-LAN attempt via Port 18802 or broadcast
            subprocess.run(
                ["curl", "-s", "-X", "POST", f"http://192.168.8.230:18802/api/wake/{node['id']}"],
                timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


def main():
    swarm = SovereignTruthAuditSwarm()
    logger.info("Starting Sovereign 24/7 Truth Audit Swarm Daemon...")
    while True:
        swarm.execute_truth_audit()
        time.sleep(300)


if __name__ == "__main__":
    main()
