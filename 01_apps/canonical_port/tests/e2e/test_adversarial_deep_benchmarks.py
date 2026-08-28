"""
Adversarial Micro-Benchmarks and Quantitative Stress Profiler
Target: Obsidian Architecture Explorer (ObsidianVaultParser, AsciiGraphRenderer, ArchitectureExplorerView)
Author: Challenger 1 (Empirical Challenger)
"""

import os
import sys
import time
import random
import tracemalloc
import gc
import pytest
from pathlib import Path

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from models.architecture_graph import ArchitectureGraph, VaultNode, VaultFeature
from services.obsidian_vault_parser import ObsidianVaultParser
from services.ascii_graph_renderer import AsciiGraphRenderer
from views.architecture_explorer_view import ArchitectureExplorerView


def test_tarjan_scc_and_sugiyama_stress_1000_nodes():
    """Benchmark Tarjan SCC and Sugiyama Layering on a 1,000 node, 3,000 edge dense web."""
    graph = ArchitectureGraph()
    for i in range(1000):
        graph.add_node(VaultNode(
            id=f"Node_{i:04d}",
            file_path=Path(f"/vault/Node_{i:04d}.md"),
            title=f"Synthetic Node {i}",
            category="Infrastructure"
        ))

    # Add 3,000 directed edges with dense random cycles
    random.seed(1337)
    for i in range(3000):
        src = f"Node_{random.randint(0, 999):04d}"
        dst = f"Node_{random.randint(0, 999):04d}"
        if src != dst:
            graph.add_edge(src, dst)

    tracemalloc.start()
    t0 = time.perf_counter()
    sccs = graph.find_sccs()
    cycles = graph.find_cycles()
    layers = graph.get_stratified_layers()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\n[BENCHMARK 1000 NODES] Time: {elapsed_ms:.2f}ms | Peak Mem: {peak_mem / 1024 / 1024:.2f}MB | SCCs: {len(sccs)} | Cycles: {len(cycles)} | Layers: {len(layers)}")

    assert len(layers) > 0
    assert elapsed_ms < 600.0, f"1000-node graph computation took {elapsed_ms:.2f}ms (threshold 600ms)"


def test_renderer_stress_500_nodes():
    """Benchmark AsciiGraphRenderer on 500 nodes generating ~500,000 characters."""
    graph = ArchitectureGraph()
    for i in range(500):
        graph.add_node(VaultNode(
            id=f"V_{i:03d}",
            file_path=Path(f"/vault/V_{i:03d}.md"),
            title=f"Subsystem {i}",
            category="AI & Inference" if i % 2 == 0 else "Biometrics & DSP"
        ))
        if i > 0:
            graph.add_edge(f"V_{i-1:03d}", f"V_{i:03d}")

    renderer = AsciiGraphRenderer(graph)
    t0 = time.perf_counter()
    ansi_text = renderer.render_ansi(max_width=160)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n[BENCHMARK RENDERER 500 NODES] Time: {elapsed_ms:.2f}ms | Output length: {len(ansi_text)} chars")
    assert len(ansi_text) > 1000
    assert elapsed_ms < 300.0, f"500-node render took {elapsed_ms:.2f}ms (threshold 300ms)"


def test_repeated_parse_memory_stability_steady_state():
    """Verify zero incremental memory accumulation over 50 consecutive vault crawls in steady state."""
    live_vault_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
    if not live_vault_path.exists():
        pytest.skip("Live vault path does not exist on this environment")

    parser = ObsidianVaultParser(vault_path=live_vault_path)
    
    tracemalloc.start()
    # Warmup memory pools and caches
    for _ in range(10):
        g = parser.parse_vault()
        _ = g.get_metrics()
        _ = g.get_stratified_layers()

    gc.collect()
    snapshot1 = tracemalloc.take_snapshot()

    for _ in range(50):
        g = parser.parse_vault()
        _ = g.get_metrics()
        _ = g.get_stratified_layers()

    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_diff = sum(stat.size_diff for stat in top_stats)
    print(f"\n[BENCHMARK MEMORY STABILITY 50 STEADY-STATE ITERATIONS] Total Diff: {total_diff / 1024:.2f}KB")
    # Steady state memory growth over 50 iterations should be negligible (< 100KB)
    assert total_diff < 100 * 1024, f"Steady state memory growth of {total_diff/1024:.2f}KB exceeds threshold of 100KB"
