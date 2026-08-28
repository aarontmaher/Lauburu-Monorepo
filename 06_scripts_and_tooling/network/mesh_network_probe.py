#!/usr/bin/env python3
"""
06_scripts_and_tooling/network/mesh_network_probe.py
===================================================
Lauburu Mesh Network Probe & Live Telemetry Engine (v3.0)
---------------------------------------------------------
Continuous background network probe that measures RTT, jitter, packet loss,
and interface bandwidth across all active Tailscale and physical interfaces.
Performs dynamic interface and socket discovery without hardcoded IP bindings.

Publishes live zero-mock telemetry snapshots to:
  /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/network/mesh_telemetry_live.json

CLI Usage:
  python3 mesh_network_probe.py --once
  python3 mesh_network_probe.py --daemon --interval 5
  python3 mesh_network_probe.py --status
  python3 mesh_network_probe.py --probe 100.73.38.87
"""

import os
import sys
import time
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Add monorepo paths for sharding daemon and network awareness imports
REPO_ROOT = Path(__file__).resolve().parents[2]
SHARDING_PATH = REPO_ROOT / "02_ai_models_and_inference"
if str(SHARDING_PATH) not in sys.path:
    sys.path.insert(0, str(SHARDING_PATH))

from sharding_daemon.network_awareness import (
    UnifiedNetworkAwarenessLayer,
    LinkMetrics,
    TransportTier,
    get_live_peer_metrics,
    compute_routing_cost,
    discover_local_interfaces,
    query_tailscale_status,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MeshProbe]: %(message)s"
)
logger = logging.getLogger("MeshProbe")

DATA_DIR = REPO_ROOT / "data" / "network"
OUTPUT_FILE = DATA_DIR / "mesh_telemetry_live.json"
LORA_FILE = REPO_ROOT / "data" / "lora_datasets" / "network_decisions.jsonl"


class MeshNetworkProbe:
    """Zero-mock empirical mesh network probe and telemetry engine."""

    def __init__(self, interval_sec: float = 5.0):
        self.interval_sec = interval_sec
        self.unal = UnifiedNetworkAwarenessLayer.get_instance(polling_interval_sec=interval_sec)

    def probe_cycle(self, verbose: bool = True) -> Dict[str, Any]:
        """Execute a single empirical probing cycle and save live telemetry JSON."""
        if verbose:
            logger.info(f"Initiating empirical network probe cycle at {datetime.now(timezone.utc).isoformat()}...")

        snapshot = self.unal.refresh_telemetry()
        out_path = self.unal.export_telemetry_json(OUTPUT_FILE)
        data = snapshot.model_dump()

        # Append structured LoRA training record for network decisions
        self.serialize_lora(data)

        if verbose:
            logger.info(f"Live telemetry published -> {out_path}")
            active_peers = [p for p in data.get("peers", []) if p.get("online") or p.get("active")]
            logger.info(
                f"Discovered {len(data.get('local_node', {}).get('interfaces', []))} local interfaces, "
                f"{len(active_peers)} active peers, "
                f"Bonded Throughput: {data.get('bonding_state', {}).get('effective_throughput_mbps', 0)} Mbps"
            )

        return data

    def run_daemon(self, verbose: bool = True):
        """Run continuous probe daemon at configured interval."""
        logger.info(f"Starting continuous mesh probe daemon (polling interval: {self.interval_sec}s)...")
        cycle = 0
        try:
            while True:
                cycle += 1
                if verbose:
                    print(f"\n{'='*70}\n[MeshProbe] Telemetry Cycle #{cycle}")
                try:
                    self.probe_cycle(verbose=verbose)
                except Exception as e:
                    logger.error(f"Error in probe cycle #{cycle}: {e}")
                time.sleep(self.interval_sec)
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user. Exiting cleanly.")

    def probe_single_peer(self, target_ip: str) -> Dict[str, Any]:
        """Empirically probe a single peer and compute routing metrics."""
        metrics: LinkMetrics = get_live_peer_metrics(target_ip)
        sample_tensor_bytes = 10 * 1024 * 1024  # 10 MB tensor
        cost = compute_routing_cost("127.0.0.1", target_ip, sample_tensor_bytes)

        result = {
            "target": target_ip,
            "metrics": metrics.model_dump(),
            "sample_tensor_size_mb": 10,
            "routing_cost": cost,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        return result

    def serialize_lora(self, data: Dict[str, Any]) -> None:
        """Record live routing decisions and network states to LoRA dataset."""
        try:
            LORA_FILE.parent.mkdir(parents=True, exist_ok=True)
            active_peers = [p for p in data.get("peers", []) if p.get("online")]
            peer_summary = "; ".join(
                f"{p.get('node_name')}(ip={p.get('tailscale_ip')},type={p.get('connection_type')},rtt={p.get('rtt_ms')}ms)"
                for p in active_peers
            )
            bonding = data.get("bonding_state", {})
            entry = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "instruction": (
                    "Given real-time Tailscale Direct WireGuard vs DERP status and physical multi-interface metrics, "
                    "compute Dijkstra DP routing weights and parallel tensor striping allocations."
                ),
                "input": f"Local: {data.get('local_node', {}).get('node_name')}; Active Peers: {peer_summary}",
                "output": (
                    f"Bonding Mode: {bonding.get('mode')}; "
                    f"Throughput: {bonding.get('effective_throughput_mbps')} Mbps; "
                    f"Weighted RTT: {bonding.get('weighted_rtt_ms')} ms; "
                    f"Active Paths: {bonding.get('active_paths_count')}"
                )
            }
            with open(LORA_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.debug(f"LoRA logging notice: {e}")


def main():
    parser = argparse.ArgumentParser(description="Lauburu Mesh Network Probe & Live Telemetry Engine (v3.0)")
    parser.add_argument("--once", action="store_true", help="Run a single empirical probe cycle and output JSON")
    parser.add_argument("--daemon", action="store_true", help="Run continuous background probe daemon")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds (default: 5.0)")
    parser.add_argument("--status", action="store_true", help="Display current live telemetry JSON")
    parser.add_argument("--probe", type=str, help="Probe a specific peer IP and show LinkMetrics & routing cost")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose stdout logs")
    args = parser.parse_args()

    probe = MeshNetworkProbe(interval_sec=args.interval)

    if args.status:
        if OUTPUT_FILE.exists():
            print(OUTPUT_FILE.read_text())
        else:
            result = probe.probe_cycle(verbose=not args.quiet)
            print(json.dumps(result, indent=2))
        return

    if args.probe:
        result = probe.probe_single_peer(args.probe)
        print(json.dumps(result, indent=2))
        return

    if args.daemon:
        probe.run_daemon(verbose=not args.quiet)
        return

    # Default to single cycle (--once)
    result = probe.probe_cycle(verbose=not args.quiet)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
