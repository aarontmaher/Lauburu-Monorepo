import math
import random
import time
from typing import List, Dict, Any, Tuple
from collections import defaultdict

GRAPH = {
    "L1_Mac_Node": ["GW_Router", "L2_MacBook_Pro", "L5_MacBook_Air"],
    "L2_MacBook_Pro": ["L1_Mac_Node", "GW_Router"],
    "L3_Linux_Head": ["GW_Router", "L4_Linux_Tablet"],
    "L4_Linux_Tablet": ["L3_Linux_Head", "GW_Router"],
    "L5_MacBook_Air": ["L1_Mac_Node", "GW_Router"],
    "L6_Pixel_10_Pro": ["GW_Router"],
    "L7_Samsung_S20": ["GW_Router"],
    "GW_Router": ["L1_Mac_Node", "L2_MacBook_Pro", "L3_Linux_Head", "L4_Linux_Tablet", "L5_MacBook_Air", "L6_Pixel_10_Pro", "L7_Samsung_S20"]
}

def bfs_paths(graph, start, goal):
    queue = [(start, [start])]
    paths = []
    while queue:
        (vertex, path) = queue.pop(0)
        for next_node in set(graph[vertex]) - set(path):
            if next_node == goal:
                paths.append(path + [next_node])
            else:
                queue.append((next_node, path + [next_node]))
    return paths

class GeneticMeshOptimizer:
    """Evolutionary algorithm to find the lowest-latency path in real-time."""
    def __init__(self, start="L1_Mac_Node", goal="L6_Pixel_10_Pro"):
        self.start = start
        self.goal = goal
        self.possible_paths = bfs_paths(GRAPH, start, goal)
        self.population = [{"path": p, "weight": random.random(), "fitness": 0.0} for p in self.possible_paths]
    
    def _fitness(self, path: List[str], telemetry: Any) -> float:
        # Extract latencies from snapshot (simulated mapping from telemetry)
        # Using a dummy lookup for now, we will parse real telemetry object
        total_latency = 0.0
        for node in path:
            # Map node to real metrics
            val = self._extract_latency(node, telemetry)
            if val <= 0: return 0.0
            total_latency += val
        return 1000.0 / total_latency if total_latency > 0 else 0.0

    def _extract_latency(self, node: str, telemetry: Any) -> float:
        # Check tailscale peers, fallback to random 0.1-50ms for demo if missing
        if hasattr(telemetry, "layer_0_networking"):
            for peer in telemetry.layer_0_networking.tailscale_peers:
                if peer.node_name and peer.node_name.startswith(node.split("_")[0]):
                    return max(0.1, float(peer.rtt_ms)) if getattr(peer, "rtt_ms", None) else 5.0
        return 5.0

    def tick(self, telemetry: Any, generations: int = 5) -> Dict[str, Any]:
        for _ in range(generations):
            for ind in self.population:
                ind["fitness"] = self._fitness(ind["path"], telemetry) * ind["weight"]
            self.population.sort(key=lambda x: x["fitness"], reverse=True)
            survivors = self.population[:len(self.population)//2 + 1]
            next_gen = survivors[:]
            while len(next_gen) < len(self.possible_paths):
                parent = random.choice(survivors)
                child = {"path": parent["path"], "weight": parent["weight"] * random.uniform(0.9, 1.1), "fitness": 0.0}
                next_gen.append(child)
            self.population = next_gen
            
        self.population.sort(key=lambda x: x["fitness"], reverse=True)
        best = self.population[0]
        return {
            "best_path": best["path"],
            "fitness": best["fitness"],
            "generation_time": time.time()
        }

class AntColonyOptimizer:
    """Fast-decay ant pheromone algorithm for sub-ms dynamic mesh."""
    def __init__(self, start="L1_Mac_Node", goal="L6_Pixel_10_Pro", num_ants=10, decay=0.85):
        self.start = start
        self.goal = goal
        self.num_ants = num_ants
        self.decay = decay
        self.pheromones = defaultdict(lambda: 1.0) # Edge to pheromone
    
    def _extract_latency(self, node: str, telemetry: Any) -> float:
        if hasattr(telemetry, "layer_0_networking"):
            for peer in telemetry.layer_0_networking.tailscale_peers:
                if peer.node_name and peer.node_name.startswith(node.split("_")[0]):
                    return max(0.1, float(peer.rtt_ms)) if getattr(peer, "rtt_ms", None) else 5.0
        return 5.0

    def tick(self, telemetry: Any) -> Dict[str, Any]:
        # Fast Evaporation (due to sub-ms environment per AI Debate)
        for edge in self.pheromones:
            self.pheromones[edge] *= self.decay
            self.pheromones[edge] = max(self.pheromones[edge], 0.01)

        best_path = []
        best_latency = float('inf')

        # Ants tour
        for _ in range(self.num_ants):
            current = self.start
            path = [current]
            path_latency = 0.0
            
            while current != self.goal and len(path) < 10:
                neighbors = [n for n in GRAPH[current] if n not in path]
                if not neighbors:
                    break
                
                # Probabilistic choice based on pheromones and inverse latency
                probs = []
                for n in neighbors:
                    edge = tuple(sorted((current, n)))
                    phero = self.pheromones[edge]
                    lat = self._extract_latency(n, telemetry)
                    heuristic = 1.0 / (lat**2) if lat > 0 else 1.0
                    probs.append(phero * heuristic)
                
                total = sum(probs)
                if total == 0:
                    chosen = random.choice(neighbors)
                else:
                    r = random.uniform(0, total)
                    upto = 0.0
                    chosen = neighbors[0]
                    for n, p in zip(neighbors, probs):
                        if upto + p >= r:
                            chosen = n
                            break
                        upto += p
                        
                path_latency += self._extract_latency(chosen, telemetry)
                current = chosen
                path.append(current)
                
            if current == self.goal:
                if path_latency < best_latency:
                    best_latency = path_latency
                    best_path = path
                
                # Deposit pheromone (exponentially weighted to latency)
                deposit = 100.0 / (path_latency ** 2) if path_latency > 0 else 0
                for i in range(len(path)-1):
                    edge = tuple(sorted((path[i], path[i+1])))
                    self.pheromones[edge] += deposit

        return {
            "best_path": best_path,
            "latency": best_latency,
            "pheromones": dict(self.pheromones)
        }
