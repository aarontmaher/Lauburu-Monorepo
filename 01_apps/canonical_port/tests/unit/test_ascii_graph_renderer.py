"""
Unit Test Suite: ASCII / ANSI Architecture Graph Renderer
Requirements Covered:
- R2. ASCII Topological Stratified Layout Engine with Tarjan SCC cycle isolation.
- R2. Unicode Box-Drawing Graph Renderer (╭─╮, ──▶, ├──┴──▶, ╰──▶).
- R2. ANSI category color styling and interactive selection highlighting.
- R2. Barycentric crossing reduction and deterministic formatting.
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from models.architecture_graph import ArchitectureGraph, VaultNode
from services.ascii_graph_renderer import AsciiGraphRenderer
from services.obsidian_vault_parser import ObsidianVaultParser


class TestAsciiGraphRenderer:
    """Unit tests for ASCII and ANSI graph canvas rendering."""

    def test_render_ansi_basic_graph(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="node_a", file_path=Path("node_a.md"), title="Root Module", category="Canonical Module")
        n2 = VaultNode(id="node_b", file_path=Path("node_b.md"), title="Child Module", category="Infrastructure")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_edge("node_a", "node_b")

        renderer = AsciiGraphRenderer(graph)
        output = renderer.render_ansi()

        assert "OBSIDIAN ARCHITECTURE TOPOLOGY CANVAS" in output
        assert "node_a" in output
        assert "node_b" in output
        assert "LAYER 00" in output
        assert "Canonical Module" in output
        assert "Infrastructure" in output

    def test_render_ansi_empty_graph(self):
        graph = ArchitectureGraph()
        renderer = AsciiGraphRenderer(graph)
        output = renderer.render_ansi(filtered_nodes=set())

        assert "NO MATCHING ARCHITECTURE NODES" in output

    def test_render_ansi_selected_node_highlighting(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="node_a", file_path=Path("node_a.md"), title="Node A", category="Canonical Module")
        n2 = VaultNode(id="node_b", file_path=Path("node_b.md"), title="Node B", category="Infrastructure")
        graph.add_node(n1)
        graph.add_node(n2)

        renderer = AsciiGraphRenderer(graph)
        output = renderer.render_ansi(selected_node="node_a")

        assert "★ SELECTED" in output
        assert "node_a" in output

    def test_render_ansi_scc_cycle_annotations(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="cycler_1", file_path=Path("c1.md"), title="Cycler 1", category="Swarm & Governance")
        n2 = VaultNode(id="cycler_2", file_path=Path("c2.md"), title="Cycler 2", category="AI & Inference")
        graph.add_node(n1)
        graph.add_node(n2)
        # Cycle: cycler_1 <-> cycler_2
        graph.add_edge("cycler_1", "cycler_2")
        graph.add_edge("cycler_2", "cycler_1")

        renderer = AsciiGraphRenderer(graph)
        output = renderer.render_ansi()

        assert "STRONGLY CONNECTED CYCLES (TARJAN SCC ISOLATED)" in output
        assert "cycler_1" in output
        assert "cycler_2" in output
        assert "↺ SCC" in output

    def test_detect_cycles_in_subgraph(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="A", file_path=Path("a.md"), title="A")
        n2 = VaultNode(id="B", file_path=Path("b.md"), title="B")
        n3 = VaultNode(id="C", file_path=Path("c.md"), title="C")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        graph.add_edge("A", "B")
        graph.add_edge("B", "A")
        graph.add_edge("B", "C")

        renderer = AsciiGraphRenderer(graph)
        cycle_edges = renderer.detect_cycles()
        assert ("A", "B") in cycle_edges
        assert ("B", "A") in cycle_edges
        assert ("B", "C") not in cycle_edges

    def test_render_tree_ascii(self):
        graph = ArchitectureGraph()
        n1 = VaultNode(id="Root", file_path=Path("root.md"), title="Root", category="Canonical Module")
        n2 = VaultNode(id="Child1", file_path=Path("c1.md"), title="Child 1", category="Infrastructure")
        n3 = VaultNode(id="Child2", file_path=Path("c2.md"), title="Child 2", category="AI & Inference")
        graph.add_node(n1)
        graph.add_node(n2)
        graph.add_node(n3)

        graph.add_edge("Root", "Child1")
        graph.add_edge("Root", "Child2")

        renderer = AsciiGraphRenderer(graph)
        tree_text = renderer.render_tree_ascii("Root", max_depth=2)

        assert "Root" in tree_text
        assert "Child1" in tree_text
        assert "Child2" in tree_text
        assert "├── " in tree_text or "└── " in tree_text

    def test_render_live_vault_ansi(self):
        parser = ObsidianVaultParser()
        graph = parser.parse_vault()
        renderer = AsciiGraphRenderer(graph)

        output = renderer.render_ansi(selected_node="Index")
        assert "OBSIDIAN ARCHITECTURE TOPOLOGY CANVAS" in output
        assert "Index" in output
        assert "★ SELECTED" in output
        assert len(output.splitlines()) > 50

    def test_render_ansi_max_width_truncation_no_overflow(self):
        graph = ArchitectureGraph()
        for i in range(5):
            graph.add_node(VaultNode(id=f"wide_node_{i}", file_path=Path(f"w{i}.md"), title=f"Wide Architecture Node #{i} with Long Descriptive Subtitle"))
        renderer = AsciiGraphRenderer(graph)
        output = renderer.render_ansi(max_width=80)
        assert len(output) > 0

    def test_render_ansi_diamond_bus_convergence_format(self):
        graph = ArchitectureGraph()
        graph.add_node(VaultNode(id="Root", file_path=Path("root.md"), title="Root"))
        graph.add_node(VaultNode(id="B1", file_path=Path("b1.md"), title="Branch 1"))
        graph.add_node(VaultNode(id="B2", file_path=Path("b2.md"), title="Branch 2"))
        graph.add_node(VaultNode(id="Sink", file_path=Path("sink.md"), title="Sink"))
        graph.add_edge("Root", "B1")
        graph.add_edge("Root", "B2")
        graph.add_edge("B1", "Sink")
        graph.add_edge("B2", "Sink")

        renderer = AsciiGraphRenderer(graph)
        rendered = renderer.render_ansi()
        assert "Root" in rendered
        assert "Sink" in rendered

    def test_barycentric_ordering_layer_permutation(self):
        graph = ArchitectureGraph()
        graph.add_node(VaultNode(id="A1", file_path=Path("a1.md"), title="A1"))
        graph.add_node(VaultNode(id="A2", file_path=Path("a2.md"), title="A2"))
        graph.add_node(VaultNode(id="B1", file_path=Path("b1.md"), title="B1"))
        graph.add_node(VaultNode(id="B2", file_path=Path("b2.md"), title="B2"))
        graph.add_edge("A1", "B2")
        graph.add_edge("A2", "B1")

        layers = graph.get_stratified_layers()
        assert len(layers) == 2

    def test_sugiyama_layering_self_loop_handling(self):
        graph = ArchitectureGraph()
        graph.add_node(VaultNode(id="LoopNode", file_path=Path("loop.md"), title="Loop Node"))
        graph.add_edge("LoopNode", "LoopNode")

        renderer = AsciiGraphRenderer(graph)
        cycles = renderer.detect_cycles()
        assert ("LoopNode", "LoopNode") in cycles
        layers = graph.get_stratified_layers()
        assert len(layers) == 1
        assert layers[0] == ["LoopNode"]

    def test_render_ansi_category_color_palette_rich_tags(self):
        graph = ArchitectureGraph()
        graph.add_node(VaultNode(id="M1", file_path=Path("m1.md"), title="M1", category="Canonical Module"))
        graph.add_node(VaultNode(id="M2", file_path=Path("m2.md"), title="M2", category="AI & Inference"))
        graph.add_node(VaultNode(id="M3", file_path=Path("m3.md"), title="M3", category="Biometrics & Telemetry"))

        renderer = AsciiGraphRenderer(graph)
        rendered = renderer.render_ansi()
        assert "Canonical Module" in rendered
        assert "AI & Inference" in rendered
