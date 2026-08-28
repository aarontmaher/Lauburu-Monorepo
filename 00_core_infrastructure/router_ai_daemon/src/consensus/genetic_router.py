"""
genetic_router.py — Evolutionary Chromosome Route Optimizer.

Implements Feature F3 Core 2: Vectorized chromosome-based multi-attribute route
optimizer evaluating RTT, packet loss, bandwidth, node health, and hardware telemetry
across the 7-Layer Lauburu Mesh.
"""

from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Canonical 7-Layer Mesh Topology Definition
# -----------------------------------------------------------------------------

MESH_TOPOLOGY: Dict[str, Dict[str, Any]] = {
    "L1": {
        "name": "Mac_Node",
        "role": "Primary Host & Memory Governor",
        "local_ip": "192.168.8.230",
        "tailscale_ip": "100.119.199.76",
        "port": 8081,
        "default_action": "ROUTE_LAN_1GBPS",
        "default_rtt_ms": 1.1,
        "default_bw_mbps": 1000.0,
        "total_ram_mb": 24000.0,
        "is_gateway": False,
    },
    "L2": {
        "name": "MacBook_Pro",
        "role": "Metal GPU RPC & Storage Vault",
        "local_ip": "192.168.8.127",
        "tb4_ip": "169.254.187.138",
        "tailscale_ip": "100.103.212.21",
        "port": 8082,
        "default_action": "ROUTE_TB4_DMA",
        "default_rtt_ms": 0.27,
        "default_bw_mbps": 10000.0,
        "total_ram_mb": 16000.0,
        "is_gateway": False,
    },
    "L3": {
        "name": "Linux_Head_Node",
        "role": "Gateway Ingress & Compute Hub",
        "local_ip": "192.168.8.224",
        "tailscale_ip": "100.101.39.98",
        "port": 8083,
        "default_action": "ROUTE_LAN_1GBPS",
        "default_rtt_ms": 1.2,
        "default_bw_mbps": 1000.0,
        "total_ram_mb": 16000.0,
        "is_gateway": False,
    },
    "L4": {
        "name": "Linux_Tablet",
        "role": "Mobile Linux Compute & Touch DSP",
        "local_ip": "192.168.8.150",
        "tailscale_ip": "100.81.92.125",
        "port": 8084,
        "default_action": "ROUTE_WIFI7",
        "default_rtt_ms": 4.5,
        "default_bw_mbps": 800.0,
        "total_ram_mb": 8000.0,
        "is_gateway": False,
    },
    "L5": {
        "name": "MacBook_Air",
        "role": "Secondary High-Speed Metal Worker",
        "local_ip": "192.168.8.222",
        "tailscale_ip": "100.93.158.96",
        "port": 8085,
        "default_action": "ROUTE_WIFI7",
        "default_rtt_ms": 3.8,
        "default_bw_mbps": 1200.0,
        "total_ram_mb": 16000.0,
        "is_gateway": False,
    },
    "L6": {
        "name": "Pixel_10_Pro_XL",
        "role": "8K Vision Stream & Edge TPU",
        "local_ip": "192.168.8.180",
        "tailscale_ip": "100.73.38.87",
        "port": 8086,
        "default_action": "ROUTE_WIFI7",
        "default_rtt_ms": 6.0,
        "default_bw_mbps": 600.0,
        "total_ram_mb": 16000.0,
        "is_gateway": False,
    },
    "L7": {
        "name": "Samsung_S20",
        "role": "Dedicated Automated UI Tester",
        "local_ip": "192.168.8.190",
        "tailscale_ip": "100.84.40.95",
        "port": 8087,
        "default_action": "ROUTE_ADB_TUNNEL",
        "default_rtt_ms": 8.5,
        "default_bw_mbps": 300.0,
        "total_ram_mb": 12000.0,
        "is_gateway": False,
    },
    "GW": {
        "name": "GL.iNet Router",
        "role": "Core Gateway & Hardware USB Bridge",
        "local_ip": "192.168.8.1",
        "tailscale_ip": "100.122.185.123",
        "port": 8080,
        "default_action": "ROUTE_LOCAL_CGROUP",
        "default_rtt_ms": 0.1,
        "default_bw_mbps": 20000.0,
        "total_ram_mb": 1000.0,
        "is_gateway": True,
    },
}


# -----------------------------------------------------------------------------
# Chromosome Model
# -----------------------------------------------------------------------------

@dataclass
class RoutingChromosome:
    """Represents an evolutionary routing policy unit."""

    chromosome_id: str = field(default_factory=lambda: f"chrom_{uuid.uuid4().hex[:8]}")
    target_layer: str = "L1"
    target_node: str = "Mac_Node"
    action: str = "ROUTE_LAN_1GBPS"
    params: Dict[str, Any] = field(default_factory=dict)
    affinity_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "rtt": 0.30,
            "loss": 0.25,
            "bandwidth": 0.20,
            "health": 0.15,
            "headroom": 0.10,
        }
    )
    fitness: float = 0.85
    generation: int = 0
    success_count: int = 0
    failure_count: int = 0

    def copy(self) -> RoutingChromosome:
        """Create deep copy of chromosome."""
        return RoutingChromosome(
            chromosome_id=f"chrom_{uuid.uuid4().hex[:8]}",
            target_layer=self.target_layer,
            target_node=self.target_node,
            action=self.action,
            params=dict(self.params),
            affinity_weights=dict(self.affinity_weights),
            fitness=self.fitness,
            generation=self.generation,
            success_count=self.success_count,
            failure_count=self.failure_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize chromosome to dictionary."""
        return {
            "chromosome_id": self.chromosome_id,
            "target_layer": self.target_layer,
            "target_node": self.target_node,
            "action": self.action,
            "params": dict(self.params),
            "affinity_weights": dict(self.affinity_weights),
            "fitness": round(self.fitness, 4),
            "generation": self.generation,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


# -----------------------------------------------------------------------------
# Genetic Router Implementation
# -----------------------------------------------------------------------------

class GeneticRouter:
    """
    Core 2 Evolutionary Policy Optimizer.
    
    Maintains and evolves a population of routing chromosomes to optimize
    network routes, swarm offload targets, and failover topologies.
    """

    def __init__(
        self,
        population_size: int = 32,
        mutation_rate: float = 0.15,
        crossover_rate: float = 0.80,
        seed: Optional[int] = 42,
    ) -> None:
        if population_size < 4:
            raise ValueError("Population size must be at least 4")
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self._rng = random.Random(seed if seed is not None else time.time())
        self.generation_count = 0

        # Live telemetry state for all layers
        self.telemetry: Dict[str, Dict[str, Any]] = {}
        self._init_default_telemetry()

        # Initialize chromosome population
        self.population: List[RoutingChromosome] = []
        self._bootstrap_population()

    def _init_default_telemetry(self) -> None:
        """Initialize telemetry with nominal topology baselines."""
        for layer, meta in MESH_TOPOLOGY.items():
            self.telemetry[layer] = {
                "node_name": meta["name"],
                "rtt_ms": meta["default_rtt_ms"],
                "packet_loss": 0.001,
                "bandwidth_mbps": meta["default_bw_mbps"],
                "is_healthy": True,
                "is_online": True,
                "free_ram_mb": meta["total_ram_mb"] * 0.70,
                "last_updated": time.time(),
            }

    def _bootstrap_population(self) -> None:
        """Generate diverse initial chromosome pool across mesh layers."""
        self.population.clear()
        layers = list(MESH_TOPOLOGY.keys())

        # Ensure representation for each layer
        for layer in layers:
            meta = MESH_TOPOLOGY[layer]
            ip = meta.get("tb4_ip") or meta.get("local_ip") or meta.get("tailscale_ip")
            chrom = RoutingChromosome(
                target_layer=layer,
                target_node=meta["name"],
                action=meta["default_action"],
                params={
                    "target_ip": ip,
                    "port": meta["port"],
                    "timeout_ms": 100 if layer in ("L1", "L2") else 250,
                    "priority": 1 if layer == "L2" else 2,
                    "layer": layer,
                },
                affinity_weights=self._random_normalized_weights(),
                fitness=0.85,
                generation=0,
            )
            self.population.append(chrom)

        # Fill remainder with stochastic variations
        while len(self.population) < self.population_size:
            layer = self._rng.choice(layers)
            meta = MESH_TOPOLOGY[layer]
            ip = meta.get("tb4_ip") or meta.get("local_ip") or meta.get("tailscale_ip")
            chrom = RoutingChromosome(
                target_layer=layer,
                target_node=meta["name"],
                action=meta["default_action"],
                params={
                    "target_ip": ip,
                    "port": meta["port"],
                    "timeout_ms": self._rng.choice([50, 100, 200, 300]),
                    "priority": self._rng.randint(1, 3),
                    "layer": layer,
                },
                affinity_weights=self._random_normalized_weights(),
                fitness=0.80,
                generation=0,
            )
            self.population.append(chrom)

        # Initial fitness evaluation
        for c in self.population:
            c.fitness = self.evaluate_fitness(c)

    def _random_normalized_weights(self) -> Dict[str, float]:
        """Produce normalized weight vector summing to 1.0."""
        keys = ["rtt", "loss", "bandwidth", "health", "headroom"]
        raw = [self._rng.uniform(0.1, 1.0) for _ in keys]
        total = sum(raw)
        return {k: round(v / total, 4) for k, v in zip(keys, raw)}

    def update_telemetry(
        self,
        layer_or_node: str,
        rtt_ms: Optional[float] = None,
        packet_loss: Optional[float] = None,
        bandwidth_mbps: Optional[float] = None,
        is_healthy: Optional[bool] = None,
        is_online: Optional[bool] = None,
        free_ram_mb: Optional[float] = None,
    ) -> None:
        """Update dynamic mesh telemetry metrics for a layer or node."""
        layer = self._resolve_layer(layer_or_node)
        if layer not in self.telemetry:
            self.telemetry[layer] = {
                "node_name": layer_or_node,
                "rtt_ms": 10.0,
                "packet_loss": 0.0,
                "bandwidth_mbps": 100.0,
                "is_healthy": True,
                "is_online": True,
                "free_ram_mb": 4000.0,
                "last_updated": time.time(),
            }

        entry = self.telemetry[layer]
        if rtt_ms is not None:
            entry["rtt_ms"] = max(0.01, float(rtt_ms))
        if packet_loss is not None:
            entry["packet_loss"] = max(0.0, min(1.0, float(packet_loss)))
        if bandwidth_mbps is not None:
            entry["bandwidth_mbps"] = max(1.0, float(bandwidth_mbps))
        if is_healthy is not None:
            entry["is_healthy"] = bool(is_healthy)
        if is_online is not None:
            entry["is_online"] = bool(is_online)
        if free_ram_mb is not None:
            entry["free_ram_mb"] = max(0.0, float(free_ram_mb))
        entry["last_updated"] = time.time()

    def _resolve_layer(self, layer_or_node: str) -> str:
        """Resolve node name or layer string to canonical layer key."""
        if layer_or_node in MESH_TOPOLOGY:
            return layer_or_node
        for layer, meta in MESH_TOPOLOGY.items():
            if meta["name"].lower() == layer_or_node.lower():
                return layer
        return "L1"

    def evaluate_fitness(
        self,
        chromosome: RoutingChromosome,
        mesh_metrics: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
    ) -> float:
        """
        Evaluate chromosome fitness against multi-attribute network telemetry.
        
        Fitness  \in [0.0, 1.0]$ combines:
        - Latency score (RTT vs 100ms baseline)
        - Packet loss resilience (1.0 - loss)
        - Bandwidth capacity score
        - Node health & online status
        - Memory headroom
        - Intent alignment bonus/penalty
        """
        layer = self._resolve_layer(chromosome.target_layer)
        tel = self.telemetry.get(layer, {})
        
        # Override telemetry with request-provided metrics if present
        if mesh_metrics and layer in mesh_metrics:
            tel = {**tel, **mesh_metrics[layer]}
        elif mesh_metrics and chromosome.target_node in mesh_metrics:
            tel = {**tel, **mesh_metrics[chromosome.target_node]}

        rtt = tel.get("rtt_ms", 10.0)
        loss = tel.get("packet_loss", 0.0)
        bw = tel.get("bandwidth_mbps", 1000.0)
        is_healthy = tel.get("is_healthy", True)
        is_online = tel.get("is_online", True)
        free_ram = tel.get("free_ram_mb", 4000.0)

        # 1. RTT score: sub-1ms = ~1.0, 10ms = ~0.90, 100ms = 0.0
        s_rtt = max(0.0, min(1.0, 1.0 - (rtt / 100.0)))
        # Bonus for sub-millisecond links (e.g. TB4 DMA 0.27ms)
        if rtt < 0.5:
            s_rtt = min(1.0, s_rtt + 0.05)

        # 2. Loss score
        s_loss = max(0.0, min(1.0, 1.0 - loss))

        # 3. Bandwidth score (log-scaled relative to 10Gbps)
        s_bw = max(0.0, min(1.0, math.log10(max(1.0, bw)) / 4.0))

        # 4. Health & online invariant
        if not is_online or not is_healthy:
            s_health = 0.05
        else:
            s_health = 1.0

        # 5. Headroom score
        s_headroom = max(0.0, min(1.0, free_ram / 16000.0))

        # Weighted combination using chromosome's evolved affinity
        w = chromosome.affinity_weights
        total_w = sum(w.values()) or 1.0
        fitness = (
            (w.get("rtt", 0.30) * s_rtt)
            + (w.get("loss", 0.25) * s_loss)
            + (w.get("bandwidth", 0.20) * s_bw)
            + (w.get("health", 0.15) * s_health)
            + (w.get("headroom", 0.10) * s_headroom)
        ) / total_w

        # Intent affinity modulation
        if intent:
            intent_u = intent.upper()
            if "TB4" in intent_u or "TENSOR" in intent_u or "SPEED" in intent_u:
                if chromosome.action == "ROUTE_TB4_DMA" or layer == "L2":
                    fitness *= 1.15
            elif "FAILOVER" in intent_u or "SAFE" in intent_u:
                if chromosome.action in ("ROUTE_LAN_1GBPS", "ROUTE_LAN_L1_DEFAULT") or layer == "L1":
                    fitness *= 1.10
            elif "SWARM" in intent_u or "SCALE" in intent_u:
                if free_ram > 6000.0:
                    fitness *= 1.08

        # Hard disqualification if offline
        if not is_online:
            fitness = min(fitness, 0.10)

        chromosome.fitness = max(0.01, min(1.0, fitness))
        return chromosome.fitness

    def crossover(
        self, parent_a: RoutingChromosome, parent_b: RoutingChromosome
    ) -> Tuple[RoutingChromosome, RoutingChromosome]:
        """Perform uniform and blend crossover on parent chromosomes."""
        child_a = parent_a.copy()
        child_b = parent_b.copy()
        child_a.generation = max(parent_a.generation, parent_b.generation) + 1
        child_b.generation = child_a.generation

        # Crossover affinity weights via blend
        keys = ["rtt", "loss", "bandwidth", "health", "headroom"]
        w_a = {}
        w_b = {}
        for k in keys:
            va = parent_a.affinity_weights.get(k, 0.2)
            vb = parent_b.affinity_weights.get(k, 0.2)
            alpha = self._rng.uniform(0.0, 1.0)
            w_a[k] = alpha * va + (1.0 - alpha) * vb
            w_b[k] = (1.0 - alpha) * va + alpha * vb

        sum_a, sum_b = sum(w_a.values()), sum(w_b.values())
        child_a.affinity_weights = {k: round(v / sum_a, 4) for k, v in w_a.items()}
        child_b.affinity_weights = {k: round(v / sum_b, 4) for k, v in w_b.items()}

        # Swap discrete target or parameters probabilistically
        if self._rng.random() < 0.5:
            child_a.target_layer = parent_b.target_layer
            child_a.target_node = parent_b.target_node
            child_a.action = parent_b.action
            child_a.params = dict(parent_b.params)

        if self._rng.random() < 0.5:
            child_b.target_layer = parent_a.target_layer
            child_b.target_node = parent_a.target_node
            child_b.action = parent_a.action
            child_b.params = dict(parent_a.params)

        return child_a, child_b

    def mutate(self, chromosome: RoutingChromosome) -> RoutingChromosome:
        """Apply stochastic mutations to weights, parameters, or targets."""
        mutated = chromosome.copy()
        keys = list(mutated.affinity_weights.keys())

        # Perturb weights
        if self._rng.random() < self.mutation_rate:
            k = self._rng.choice(keys)
            delta = self._rng.uniform(-0.10, 0.10)
            mutated.affinity_weights[k] = max(0.05, mutated.affinity_weights[k] + delta)
            total = sum(mutated.affinity_weights.values())
            mutated.affinity_weights = {
                k: round(v / total, 4) for k, v in mutated.affinity_weights.items()
            }

        # Parameter mutation
        if self._rng.random() < (self.mutation_rate * 0.5):
            if "timeout_ms" in mutated.params:
                mutated.params["timeout_ms"] = max(
                    20, mutated.params["timeout_ms"] + self._rng.choice([-20, 20, 50])
                )

        # Target exploration mutation
        if self._rng.random() < (self.mutation_rate * 0.3):
            all_layers = list(MESH_TOPOLOGY.keys())
            layer = self._rng.choice(all_layers)
            meta = MESH_TOPOLOGY[layer]
            mutated.target_layer = layer
            mutated.target_node = meta["name"]
            mutated.action = meta["default_action"]
            ip = meta.get("tb4_ip") or meta.get("local_ip") or meta.get("tailscale_ip")
            mutated.params = {
                "target_ip": ip,
                "port": meta["port"],
                "timeout_ms": 100,
                "priority": 2,
                "layer": layer,
            }

        return mutated

    def evolve(
        self,
        generations: int = 4,
        mesh_metrics: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
    ) -> List[RoutingChromosome]:
        """Run generational evolution loop with elitism selection."""
        for _ in range(generations):
            self.generation_count += 1

            # Evaluate fitness of all individuals
            for chrom in self.population:
                self.evaluate_fitness(chrom, mesh_metrics=mesh_metrics, intent=intent)

            # Sort descending by fitness
            self.population.sort(key=lambda c: c.fitness, reverse=True)

            # Elitism: retain top 20%
            elite_count = max(2, int(self.population_size * 0.20))
            new_population: List[RoutingChromosome] = [c.copy() for c in self.population[:elite_count]]

            # Breed remainder
            while len(new_population) < self.population_size:
                # Tournament selection
                parent_a = self._tournament_select()
                parent_b = self._tournament_select()

                if self._rng.random() < self.crossover_rate:
                    child_a, child_b = self.crossover(parent_a, parent_b)
                else:
                    child_a, child_b = parent_a.copy(), parent_b.copy()

                child_a = self.mutate(child_a)
                child_b = self.mutate(child_b)

                self.evaluate_fitness(child_a, mesh_metrics=mesh_metrics, intent=intent)
                self.evaluate_fitness(child_b, mesh_metrics=mesh_metrics, intent=intent)

                new_population.append(child_a)
                if len(new_population) < self.population_size:
                    new_population.append(child_b)

            self.population = new_population

        self.population.sort(key=lambda c: c.fitness, reverse=True)
        return self.population

    def _tournament_select(self, k: int = 3) -> RoutingChromosome:
        """Perform tournament selection of size k."""
        candidates = self._rng.sample(self.population, min(k, len(self.population)))
        return max(candidates, key=lambda c: c.fitness)

    def propose_routing_decision(
        self,
        intent: str,
        candidate_routes: Optional[List[Any]] = None,
        mesh_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate Core 2 proposal decision vector.
        
        Returns formatted decision dict conforming to Dual-Core protocol:
        {"action": str, "params": dict, "fitness": float, "chromosome_id": str, ...}
        """
        # Run rapid 2-generation evolution for dynamic adaptation
        self.evolve(generations=2, mesh_metrics=mesh_metrics, intent=intent)
        best_chrom = self.population[0]

        # If candidates are explicitly provided, find the closest matching or best candidate
        if candidate_routes:
            matched_chrom = None
            best_cand_fitness = -1.0
            for cand in candidate_routes:
                cand_action = cand if isinstance(cand, str) else cand.get("action", "")
                for chrom in self.population:
                    if cand_action in (chrom.action, f"ROUTE_{chrom.target_layer}", chrom.target_layer):
                        f = self.evaluate_fitness(chrom, mesh_metrics=mesh_metrics, intent=intent)
                        if f > best_cand_fitness:
                            best_cand_fitness = f
                            matched_chrom = chrom
            if matched_chrom:
                best_chrom = matched_chrom

        params = dict(best_chrom.params)
        if "latency_ms" not in params:
            layer = self._resolve_layer(best_chrom.target_layer)
            params["latency_ms"] = self.telemetry.get(layer, {}).get("rtt_ms", 1.0)

        return {
            "core": "genetic_router",
            "action": best_chrom.action,
            "params": params,
            "fitness": round(best_chrom.fitness, 4),
            "chromosome_id": best_chrom.chromosome_id,
            "target_layer": best_chrom.target_layer,
            "target_node": best_chrom.target_node,
            "timestamp": time.time(),
        }
