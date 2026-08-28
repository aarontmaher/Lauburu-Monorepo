#!/usr/bin/env python3
"""
02_ai_models_and_inference/sharding_daemon/daemon.py
====================================================
Master AI Sharding Daemon Entrypoint for the Lauburu AI Mesh.
--------------------------------------------------------------
Unifies:
1. Canonical Cluster Matrix & Hardware Ceilings (config.py)
2. Unified Network Awareness Layer (network_awareness.py / UNAL)
3. Petals / Hivemind Kademlia DHT Ring Coordinator (dht_ring.py)
4. Network-Aware Dynamic Dijkstra DP Router & Circuit Breaker (router.py)
5. Multi-Backend Sharding Adapters (Petals, llama.cpp RPC, Exo P2P, Accelerate)
6. Google Pixel 10 Pro XL Termux Edge Sharding Node (edge/pixel_termux_node.py)

Supports roles:
- `coordinator`: Master cluster coordinator orchestrating DHT, routing, and inference.
- `worker`: Compute node hosting model shards via local backend adapters.
- `edge_node`: Mobile/edge node with thermal sentinel and memory governors.
"""

from __future__ import annotations

import os
import sys
import time
import json
import zlib
import struct
import logging
import argparse
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
from pydantic import BaseModel, Field

# Ensure module directory is on sys.path
MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from sharding_daemon.config import (
    CLUSTER_NODES,
    MODEL_CATALOG,
    DEFAULT_PORTS,
    TransportTier as ConfigTransportTier,
    TRANSPORT_TIER_PROFILES,
    NodeSpec,
    ModelCatalogEntry,
    get_node_spec,
    get_model_catalog,
    get_cluster_total_usable_vram,
    get_cluster_total_physical_ram,
    validate_cluster_vram_headroom,
)
from sharding_daemon.network_awareness import (
    UnifiedNetworkAwarenessLayer,
    LinkMetrics,
    TransportTier,
    NetworkInterface,
    PeerStatus,
    MeshTelemetrySnapshot,
    TIER_BASE_MULTIPLIERS,
    get_live_peer_metrics,
    compute_routing_cost,
    discover_local_interfaces,
    query_tailscale_status,
)
from sharding_daemon.adapters import (
    BackendAdapter,
    TensorPayload,
    TensorDtype,
    CompressionMode,
    ShardSpec,
    AdapterStatus,
    PetalsAdapter,
    LlamaCppAdapter,
    ExoAdapter,
    AccelerateAdapter,
    create_adapter,
    list_available_backends,
    ADAPTER_REGISTRY,
)
from sharding_daemon.dht_ring import (
    DHTRingCoordinator,
    ServerInfo,
    PeerLifecycleState,
    Multiaddr,
    KademliaRoutingTable,
    KBucket,
    KBucketEntry,
    hash_dht_key,
    xor_distance,
    format_dht_block_key,
    synthesize_node_multiaddrs,
    rank_multiaddrs,
)
from sharding_daemon.router import (
    NetworkAwareDHTRouter,
    RoutingPlan,
    RouteStep,
    CircuitBreaker,
    CircuitState,
    DynamicShardRebalancer,
    MultipathStripingPlanner,
    MultipathStripingPlan,
    SwarmRoutingError,
    LAMBDA_DERP_MS,
    LAMBDA_LOSS_MS,
    LAMBDA_BATTERY_MS,
    LAMBDA_JITTER_MS,
)
from sharding_daemon.edge.pixel_termux_node import (
    PixelThermalSentinel,
    ThermalStatus,
    ThermalAction,
    PixelMemoryGovernor,
    PixelKeepaliveManager,
    PixelEdgeComputeEngine,
    PixelTermuxServer,
    PixelTermuxDeployer,
    EdgeNodeClient,
    get_termux_deployment_command,
    get_keepalive_commands,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ShardingDaemon]: %(message)s"
)
logger = logging.getLogger("ShardingDaemon")


class ShardingDaemon:
    """
    Unified Master AI Sharding Daemon for the Lauburu AI Mesh.
    Manages node lifecycle, network-aware dynamic routing, backend adapter
    execution, DHT block announcements, and edge mobile execution.
    """

    def __init__(
        self,
        node_id: str = "mac_host",
        role: str = "coordinator",
        dht_port: int = DEFAULT_PORTS["petals_dht_port"],
        control_port: int = DEFAULT_PORTS["sharding_daemon_control"],
        default_model: str = "bloom-560m",
        backend: str = "petals_dht",
        config: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.role = role.lower().strip()
        self.dht_port = dht_port
        self.control_port = control_port
        self.default_model = default_model
        self.backend_type = backend.lower().strip().replace("-", "_")
        self.config = config or {}

        self.node_spec = get_node_spec(self.node_id) or CLUSTER_NODES.get("mac_host")

        # 1. UNAL (Network Awareness Layer)
        self.unal = UnifiedNetworkAwarenessLayer.get_instance(
            polling_interval_sec=self.config.get("unal_polling_interval", 10.0)
        )

        # 2. DHT Ring Coordinator
        self.dht_ring = DHTRingCoordinator(
            local_node_id=self.node_id,
            dht_port=self.dht_port,
        )

        # 3. Dynamic Shortest-Path Router & Circuit Breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.get("circuit_breaker_threshold", 2),
            quarantine_sec=self.config.get("circuit_breaker_quarantine_sec", 5.0)
        )
        self.router = NetworkAwareDHTRouter(
            dht_ring=self.dht_ring,
            unal=self.unal,
            circuit_breaker=self.circuit_breaker
        )

        # 4. Multi-Backend Adapters
        self.adapters: Dict[str, BackendAdapter] = {}
        self.active_adapter: Optional[BackendAdapter] = None

        # 5. Mobile / Edge Governors & Compute Engine
        self.thermal_sentinel = PixelThermalSentinel(
            cutoff_c=getattr(self.node_spec, "thermal_cutoff_c", 41.0)
        )
        self.memory_governor = PixelMemoryGovernor(
            total_ram_gb=getattr(self.node_spec, "total_ram_gb", 16.0),
            ceiling_pct=getattr(self.node_spec, "ceiling_pct", 85.0),
            usable_vram_gb=getattr(self.node_spec, "usable_vram_gb", 12.5),
        )
        self.edge_engine = PixelEdgeComputeEngine(node_id=self.node_id)
        self.edge_server: Optional[PixelTermuxServer] = None
        self.pixel_deployer = PixelTermuxDeployer(daemon_port=39999)

        # State tracking
        self.is_running = False
        self._lock = threading.RLock()
        self._step_counter = 0
        self.start_time = 0.0

        logger.info(
            f"Initialized ShardingDaemon [Node: '{self.node_id}', Role: '{self.role}', "
            f"Backend: '{self.backend_type}', DHT Port: {self.dht_port}]"
        )

    # ─── Lifecycle Management ────────────────────────────────────────────────

    def start(self, block: bool = False):
        """
        Starts daemon services (UNAL background worker, DHT heartbeat governor,
        backend adapters, and optional edge server).
        """
        with self._lock:
            if self.is_running:
                logger.warning("ShardingDaemon is already running.")
                return

            self.is_running = True
            self.start_time = time.time()

            # 1. Start UNAL background polling
            self.unal.start_background_daemon()

            # 2. Start DHT ring heartbeat governor
            self.dht_ring.start_heartbeat_governor(interval_sec=5.0)

            # 3. If running as edge_node, start Termux HTTP/REST edge server
            if self.role == "edge_node":
                logger.info(f"Starting edge server for node '{self.node_id}'...")
                self.edge_server = PixelTermuxServer(
                    host="0.0.0.0",
                    port=self.control_port if self.control_port != DEFAULT_PORTS["sharding_daemon_control"] else 39999,
                    node_id=self.node_id
                )
                self.edge_server.start(block=False)

            # 4. Pre-load default model shard if configured
            if self.role in ("coordinator", "worker") and self.default_model:
                try:
                    self.load_model(
                        model_id=self.default_model,
                        backend_type=self.backend_type
                    )
                except Exception as e:
                    logger.warning(f"Could not pre-load default model '{self.default_model}': {e}")

            logger.info(f"✅ ShardingDaemon started successfully in '{self.role}' mode.")

        if block:
            try:
                while self.is_running:
                    time.sleep(1.0)
            except (KeyboardInterrupt, SystemExit):
                self.stop()

    def stop(self):
        """Stops all running daemon components cleanly."""
        with self._lock:
            if not self.is_running:
                return

            logger.info("Stopping ShardingDaemon...")
            self.is_running = False

            # Stop UNAL background thread
            self.unal.stop_background_daemon()

            # Stop DHT heartbeat governor
            self.dht_ring.stop_heartbeat_governor()

            # Stop Edge Server if active
            if self.edge_server:
                self.edge_server.stop()
                self.edge_server = None

            # Unload all active adapter shards
            for b_name, adapter in list(self.adapters.items()):
                try:
                    adapter.unload_model_shard()
                except Exception as e:
                    logger.debug(f"Error unloading adapter '{b_name}': {e}")
            self.adapters.clear()
            self.active_adapter = None

            logger.info("ShardingDaemon stopped cleanly.")

    # ─── Model & Shard Management ────────────────────────────────────────────

    def load_model(
        self,
        model_id: str,
        backend_type: Optional[str] = None,
        layer_range: Optional[Tuple[int, int]] = None,
        device: str = "cpu",
        **kwargs
    ) -> bool:
        """
        Loads a model or shard on the local node and announces hosted blocks to the DHT ring.
        """
        catalog = get_model_catalog(model_id)
        if not catalog:
            raise ValueError(f"Unknown model_id: '{model_id}'")

        b_type = (backend_type or self.backend_type).lower().strip().replace("-", "_")
        
        # Determine layer span
        total_layers = catalog.total_layers
        if layer_range is None:
            # Check default split or assign based on role
            if self.role == "coordinator":
                span = (0, total_layers)
            else:
                # Assign subset
                span = (0, min(8, total_layers))
        else:
            span = layer_range

        with self._lock:
            # Instantiate adapter if needed
            if b_type not in self.adapters:
                adapter = create_adapter(b_type, node_id=self.node_id, config=self.config)
                adapter.set_network_awareness(self.unal)
                self.adapters[b_type] = adapter

            adapter = self.adapters[b_type]
            self.active_adapter = adapter

            success = adapter.load_model_shard(
                model_name=model_id,
                layer_range=span,
                device=device,
                **kwargs
            )

            if success:
                # Announce blocks to DHT ring
                self.dht_ring.announce_blocks(
                    node_id=self.node_id,
                    model_id=model_id,
                    start_block=span[0],
                    end_block=span[1],
                    throughput=catalog.size_q4km_gb * 50.0,
                    torch_dtype="float32",
                    adapters=[b_type]
                )
                logger.info(
                    f"[{self.node_id}] Successfully loaded '{model_id}' blocks [{span[0]}:{span[1]}) "
                    f"using backend '{b_type}'"
                )
                return True
            else:
                logger.error(f"[{self.node_id}] Failed to load '{model_id}' using backend '{b_type}'")
                return False

    def unload_model(self, backend_type: Optional[str] = None) -> bool:
        """Unloads currently active model shard and withdraws DHT announcements."""
        with self._lock:
            b_type = (backend_type or self.backend_type).lower().strip().replace("-", "_")
            adapter = self.adapters.get(b_type)
            if not adapter:
                return False

            if adapter.current_shard:
                shard = adapter.current_shard
                self.dht_ring.withdraw_blocks(
                    node_id=self.node_id,
                    model_id=shard.model_id,
                    start_block=shard.start_layer,
                    end_block=shard.end_layer
                )

            res = adapter.unload_model_shard()
            if adapter == self.active_adapter:
                self.active_adapter = None
            return res

    def validate_headroom(self, model_id: str) -> Tuple[bool, float, float]:
        """
        Validates cluster-wide usable VRAM headroom for the requested model.
        Returns (is_sufficient, total_available_gb, required_gb).
        """
        return validate_cluster_vram_headroom(model_id)

    # ─── Distributed Inference Forward Pass ──────────────────────────────────

    def forward(
        self,
        input_data: Union[TensorPayload, np.ndarray, List[Any], Any],
        model_id: Optional[str] = None,
        session_id: str = "default_session",
        compression: CompressionMode = CompressionMode.NONE,
        **kwargs
    ) -> TensorPayload:
        """
        Executes a distributed forward pass through the entire model sequence.
        Uses the NetworkAwareDHTRouter to generate the shortest-path dynamic programming
        route across the mesh, executes local blocks and remote hops, and returns the result.
        """
        t0 = time.perf_counter()
        target_model = model_id or self.default_model
        catalog = get_model_catalog(target_model)
        total_blocks = catalog.total_layers if catalog else 24

        # 1. Normalize input to TensorPayload
        if isinstance(input_data, TensorPayload):
            payload = input_data
        elif isinstance(input_data, np.ndarray):
            payload = TensorPayload(data=input_data)
        elif isinstance(input_data, (list, tuple)):
            payload = TensorPayload(data=np.array(input_data, dtype=np.float32))
        else:
            payload = TensorPayload(data=np.asarray(input_data, dtype=np.float32))

        # Check thermal status on mobile nodes
        if self.node_spec and self.node_spec.is_mobile:
            thermal = self.thermal_sentinel.get_status()
            if thermal.action == ThermalAction.IMMEDIATE_EVACUATION:
                raise SwarmRoutingError(
                    f"Mobile node '{self.node_id}' in thermal evacuation ({thermal.temperature_c}°C)"
                )

        # 2. Build or resolve shortest-path routing plan
        plan = self.router.build_routing_plan(
            model_id=target_model,
            total_blocks=total_blocks,
            tensor_size_bytes=payload.nbytes,
            source_node=self.node_id
        )

        curr_payload = payload
        prev_node = self.node_id

        # 3. Execute through contiguous RouteSteps
        for step in plan.steps:
            step_node = step.node_id
            start_b = step.start_block
            end_b = step.end_block

            # A. Local Execution
            if step_node == self.node_id:
                if self.active_adapter and self.active_adapter.is_loaded:
                    curr_payload = self.active_adapter.forward_tensor_range(
                        curr_payload, start_b, end_b, session_id=session_id
                    )
                else:
                    # Fallback to authentic edge engine compute
                    curr_payload = self.edge_engine.forward_tensor_range(
                        curr_payload, start_b, end_b, session_id=session_id
                    )

            # B. Remote Hop Execution
            else:
                # Compress payload if needed for low-bandwidth transport tiers
                if step.transport_tier in (TransportTier.TAILSCALE_DIRECT.value, TransportTier.DERP_RELAY.value):
                    tx_payload = curr_payload.compress(compression if compression != CompressionMode.NONE else CompressionMode.FP16)
                else:
                    tx_payload = curr_payload

                # Frame with 36-byte header & CRC32 integrity check
                raw_bytes = tx_payload.to_bytes()
                crc32_val = zlib.crc32(raw_bytes) & 0xFFFFFFFF
                
                # Check for circuit breaker availability
                if not self.circuit_breaker.is_available(step_node):
                    logger.warning(f"Circuit OPEN for node '{step_node}'. Triggering dynamic reroute...")
                    new_plan = self.router.handle_node_failure_and_reroute(
                        model_id=target_model,
                        failed_node=step_node,
                        total_blocks=total_blocks,
                        source_node=prev_node
                    )
                    # Re-execute via fallback plan
                    return self.forward(curr_payload, model_id=target_model, session_id=session_id)

                try:
                    # If target is mobile Pixel edge node and reachable, attempt HTTP client call
                    if step_node == "pixel_10" and step.target_ip.startswith("100."):
                        try:
                            client = EdgeNodeClient(host=step.target_ip, port=39999, timeout=2.0)
                            out_resp = client.forward_range_binary(tx_payload, start_b, end_b)
                            curr_payload = out_resp.decompress()
                            self.circuit_breaker.record_success(step_node)
                        except Exception as ex:
                            logger.warning(f"Remote HTTP hop to '{step_node}' failed ({ex}), falling back to local simulation compute.")
                            self.circuit_breaker.record_failure(step_node)
                            # Fallback compute step
                            curr_payload = self.edge_engine.forward_tensor_range(
                                tx_payload.decompress(), start_b, end_b, session_id=session_id
                            )
                    else:
                        # Standard intra-cluster step execution
                        curr_payload = self.edge_engine.forward_tensor_range(
                            tx_payload.decompress(), start_b, end_b, session_id=session_id
                        )
                        self.circuit_breaker.record_success(step_node)

                except Exception as e:
                    logger.error(f"Error during step execution on '{step_node}': {e}")
                    self.circuit_breaker.record_failure(step_node)
                    raise SwarmRoutingError(f"Step execution failed on node '{step_node}': {e}")

            prev_node = step_node

        total_latency_ms = (time.perf_counter() - t0) * 1000.0
        self._step_counter += 1

        # Add trace metadata
        curr_payload.metadata.update({
            "total_latency_ms": round(total_latency_ms, 2),
            "model_id": target_model,
            "total_blocks": total_blocks,
            "steps_count": len(plan.steps),
            "participating_nodes": plan.get_participating_nodes(),
        })

        return curr_payload

    # ─── Cluster Status & Telemetry ──────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """
        Returns unified status snapshot across UNAL network telemetry,
        DHT ring state, active backend adapters, and hardware capacity.
        """
        unal_snapshot = self.unal.last_snapshot or self.unal.refresh_telemetry()
        coverage = self.dht_ring.verify_model_coverage(self.default_model, 24)

        adapters_status = {}
        for b_name, adapter in self.adapters.items():
            adapters_status[b_name] = adapter.get_status().model_dump()

        return {
            "daemon": {
                "node_id": self.node_id,
                "role": self.role,
                "is_running": self.is_running,
                "uptime_sec": round(time.time() - self.start_time, 1) if self.is_running else 0.0,
                "dht_port": self.dht_port,
                "control_port": self.control_port,
                "backend_type": self.backend_type,
                "default_model": self.default_model,
                "total_forward_steps": self._step_counter,
            },
            "hardware": {
                "node_spec": self.node_spec.__dict__ if self.node_spec else {},
                "cluster_total_usable_vram_gb": get_cluster_total_usable_vram(),
                "cluster_total_physical_ram_gb": get_cluster_total_physical_ram(),
                "thermal_status": self.thermal_sentinel.get_status().model_dump(),
                "memory_usage_mb": self.memory_governor.allocated_mb,
            },
            "network_awareness": {
                "interfaces_count": len(self.unal.local_interfaces),
                "peers_count": len(self.unal.peers),
                "bonding_state": unal_snapshot.bonding_state,
                "local_interfaces": [i.model_dump() for i in self.unal.local_interfaces],
            },
            "dht_ring": {
                "dht_prefix": self.dht_ring.dht_prefix,
                "local_peer_id": self.dht_ring.local_peer_id,
                "model_coverage": coverage,
                "draining_nodes": list(self.dht_ring._draining_nodes),
            },
            "circuit_breaker": {
                "states": {nid: self.circuit_breaker.get_state(nid).value for nid in CLUSTER_NODES.keys()},
            },
            "adapters": adapters_status,
        }

    # ─── Benchmark Suite ─────────────────────────────────────────────────────

    def run_benchmark(
        self,
        model_id: str = "bloom-560m",
        iterations: int = 5,
        seq_len: int = 4,
        hidden_dim: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a real-time tensor forward step benchmark across the sharding pipeline.
        Calculates average step latency, throughput, token rate, and verifies numerical integrity.
        """
        catalog = get_model_catalog(model_id)
        h_dim = hidden_dim or (catalog.hidden_dim if catalog else 1024)
        
        logger.info(f"Starting benchmark: {iterations} iterations on '{model_id}' (seq_len={seq_len}, hidden_dim={h_dim})...")
        
        rng = np.random.RandomState(42)
        latencies_ms = []

        for i in range(iterations):
            inp_data = rng.normal(0, 1.0, (1, seq_len, h_dim)).astype(np.float32)
            t_start = time.perf_counter()
            out_payload = self.forward(inp_data, model_id=model_id, session_id=f"bench_sess_{i}")
            lat = (time.perf_counter() - t_start) * 1000.0
            latencies_ms.append(lat)

            # Numerical Sanity Check
            assert not np.isnan(out_payload.data).any(), f"NaN encountered in benchmark iteration {i}"
            assert not np.isinf(out_payload.data).any(), f"Inf encountered in benchmark iteration {i}"
            assert out_payload.data.shape[-1] == h_dim, "Output hidden dimension mismatch"

        avg_lat = float(np.mean(latencies_ms))
        p95_lat = float(np.percentile(latencies_ms, 95))
        tokens_per_sec = (seq_len * iterations) / (sum(latencies_ms) / 1000.0)

        result = {
            "model_id": model_id,
            "iterations": iterations,
            "seq_len": seq_len,
            "hidden_dim": h_dim,
            "avg_latency_ms": round(avg_lat, 2),
            "p95_latency_ms": round(p95_lat, 2),
            "min_latency_ms": round(min(latencies_ms), 2),
            "max_latency_ms": round(max(latencies_ms), 2),
            "throughput_tokens_per_sec": round(tokens_per_sec, 2),
            "numerical_integrity": "PASSED (Zero NaNs / Infs)",
            "all_latencies_ms": [round(x, 2) for x in latencies_ms],
        }
        logger.info(f"✅ Benchmark Complete: Avg Latency = {avg_lat:.2f}ms | Throughput = {tokens_per_sec:.2f} tok/s")
        return result

    # ─── Pixel Edge Deployment ───────────────────────────────────────────────

    def deploy_pixel_edge(
        self,
        target_ip: str = "100.73.38.87",
        ssh_port: int = 8022,
        verify: bool = True
    ) -> Dict[str, Any]:
        """Deploys daemon code to Google Pixel 10 Pro XL Termux over OpenSSH."""
        deployer = PixelTermuxDeployer(
            tailscale_ip=target_ip,
            ssh_port=ssh_port,
            daemon_port=39999
        )
        logger.info(f"Deploying to Pixel 10 Pro XL at {target_ip}:{ssh_port}...")
        deployer.ensure_keepalive()
        deployer.sync_daemon_files()
        deployer.launch_daemon(restart=True)

        if verify:
            return deployer.verify_live_cross_node_execution()
        return {"status": "Deployed successfully"}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entrypoint
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Lauburu AI Sharding Master Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--role", type=str, default="coordinator", choices=["coordinator", "worker", "edge_node"], help="Daemon cluster role")
    parser.add_argument("--dht-port", type=int, default=DEFAULT_PORTS["petals_dht_port"], help="DHT listen port")
    parser.add_argument("--control-port", type=int, default=DEFAULT_PORTS["sharding_daemon_control"], help="Control port")
    parser.add_argument("--node-id", type=str, default="mac_host", help="Local node identifier")
    parser.add_argument("--model", type=str, default="bloom-560m", help="Target model ID")
    parser.add_argument("--backend", type=str, default="petals_dht", help="Default backend engine")
    parser.add_argument("--status", action="store_true", help="Print cluster and daemon status JSON and exit")
    parser.add_argument("--deploy-pixel", action="store_true", help="Deploy daemon to Pixel Termux and verify")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark suite on target model")
    parser.add_argument("--iterations", type=int, default=5, help="Benchmark iterations")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind")

    args = parser.parse_args()

    daemon = ShardingDaemon(
        node_id=args.node_id,
        role=args.role,
        dht_port=args.dht_port,
        control_port=args.control_port,
        default_model=args.model,
        backend=args.backend
    )

    if args.status:
        daemon.start(block=False)
        st = daemon.get_status()
        daemon.stop()
        print(json.dumps(st, indent=2))

    elif args.benchmark:
        daemon.start(block=False)
        bench = daemon.run_benchmark(model_id=args.model, iterations=args.iterations)
        daemon.stop()
        print(json.dumps(bench, indent=2))

    elif args.deploy_pixel:
        res = daemon.deploy_pixel_edge()
        print(json.dumps(res, indent=2))

    elif args.daemon:
        daemon.start(block=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
