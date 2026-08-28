#!/usr/bin/env python3
import json
import time
import random
import os
import sys

if sys.platform.startswith('linux') and os.path.exists('/tmp') and not os.access("/Users/aaron/DFS_UNIFIED", os.W_OK):
    TRENDS_FILE = "/tmp/mesh_trends.json"
    OPTIMIZED_PATH_FILE = "/tmp/ga_optimized_path.json"
else:
    TRENDS_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/mesh_trends.json"
    OPTIMIZED_PATH_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/ga_optimized_path.json"

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

def fitness(path, telemetry):
    total_latency = 0
    for node in path:
        node_data = telemetry.get("nodes", {}).get(node, {})
        lat = node_data.get("latency", "--")
        if lat == "--": return 0
        total_latency += lat
    if total_latency == 0: return 0
    return 1000.0 / total_latency

def genetic_algorithm(paths, telemetry, generations=20):
    if not paths: return None
    population = [{"path": p, "weight": random.random()} for p in paths]
    for _ in range(generations):
        for ind in population:
            ind["fitness"] = fitness(ind["path"], telemetry) * ind["weight"]
        population.sort(key=lambda x: x["fitness"], reverse=True)
        survivors = population[:len(population)//2 + 1]
        next_gen = survivors[:]
        while len(next_gen) < len(paths):
            parent = random.choice(survivors)
            child = {"path": parent["path"], "weight": parent["weight"] * random.uniform(0.8, 1.2)}
            next_gen.append(child)
        population = next_gen
        for ind in population:
            if "fitness" not in ind:
                ind["fitness"] = fitness(ind["path"], telemetry) * ind["weight"]
    population.sort(key=lambda x: x["fitness"], reverse=True)
    return population[0]

def run_optimizer():
    print(f"Starting Genetic BFS Optimizer... Reading {TRENDS_FILE} -> {OPTIMIZED_PATH_FILE}")
    while True:
        if not os.path.exists(TRENDS_FILE):
            time.sleep(1)
            continue
        try:
            with open(TRENDS_FILE, "r") as f:
                telemetry = json.load(f)
        except Exception:
            time.sleep(1)
            continue

        possible_paths = bfs_paths(GRAPH, "L1_Mac_Node", "L6_Pixel_10_Pro")
        best_path = genetic_algorithm(possible_paths, telemetry)
        
        output = {
            "timestamp": time.time(),
            "best_path": best_path["path"] if best_path else [],
            "fitness": best_path["fitness"] if best_path else 0,
            "telemetry_used": telemetry
        }
        
        tmp = OPTIMIZED_PATH_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(output, f, indent=2)
        os.rename(tmp, OPTIMIZED_PATH_FILE)
        time.sleep(2)

if __name__ == "__main__":
    run_optimizer()
