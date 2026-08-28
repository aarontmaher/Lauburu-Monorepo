"""
Adversarial Stress, Fuzzing & Boundary Benchmark Suite
Target: Obsidian Architecture Explorer (ObsidianVaultParser, AsciiGraphRenderer, ArchitectureExplorerView)
Author: Challenger 1 (Empirical Challenger)
"""

import os
import sys
import time
import tempfile
import random
import string
import gc
import pytest
from pathlib import Path
from typing import List, Set, Dict

# Ensure tui package is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tui")))

from textual.app import App, ComposeResult
from textual.widgets import Input, Button, Tree, Markdown, Static

from canonical_tui import CanonicalPortApp
from models.architecture_graph import ArchitectureGraph, VaultNode, VaultFeature, WikilinkRef
from services.obsidian_vault_parser import ObsidianVaultParser
from services.ascii_graph_renderer import AsciiGraphRenderer
from views.architecture_explorer_view import ArchitectureExplorerView
from screens.architecture_explorer_screen import ArchitectureExplorerScreen


class StandaloneExplorerApp(App):
    """Minimal wrapper app for testing ArchitectureExplorerView directly."""
    CSS = """
    Screen { background: #070b12; }
    """

    def __init__(self, vault_path: Path = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vault_path = vault_path

    def compose(self) -> ComposeResult:
        yield ArchitectureExplorerView(vault_path=self.vault_path, id="architecture-explorer-view")


# =============================================================================
# 1. PARSER FUZZING & MALFORMED MARKDOWN CHALLENGE
# =============================================================================

class TestParserFuzzingAndMalformedInputs:
    """Adversarial stress testing for ObsidianVaultParser under corrupted, malformed, or extreme inputs."""

    def test_unclosed_and_corrupted_yaml_frontmatter(self, tmp_path):
        """Test parser robustness with unclosed YAML, tab indentation, invalid colons, and BOM."""
        cases = [
            ("unclosed_yaml.md", "---\ntitle: Unclosed Node\ntags: [a, b]\n# Body starts without closing delimiter\nSome text with [[TargetNode]]"),
            ("tab_yaml.md", "---\n\ttitle: Tab Indented\n\ttags:\n\t\t- tag1\n---\nBody text"),
            ("colon_in_unquoted_val.md", "---\ntitle: Key: With: Many: Colons: Here\ncategory: Infrastructure\n---\n# Header\n- Feature: Description"),
            ("duplicate_keys.md", "---\ntitle: First Title\ntitle: Overridden Title\ntags: [one]\ntags: [two]\n---\nContent"),
            ("null_bytes.md", "---\ntitle: Null\x00Byte\x01Inside\n---\nContent\x00with\x00nulls [[Link\x00Node]]"),
            ("only_delimiters.md", "---\n---\n"),
            ("triple_delimiters.md", "---\n---\n---\n---\n"),
            ("dots_delimiters.md", "---\ntitle: Dot Finished\n...\nBody text"),
            ("nested_yaml_bomb.md", "---\na: &a [\"lol\",\"lol\",\"lol\"]\nb: &b [*a,*a,*a]\nc: &c [*b,*b,*b]\n---\nExplosion test"),
            ("emoji_and_cjk_yaml.md", "---\ntitle: 🧠 神经网络 🚀\ntags: [人工智能, ⚡️speed, 日本語]\ncategory: AI & Inference\n---\n# 架构设计\n- [[02_ai_inference|推理内核]] — **高性能计算**"),
        ]

        vault_dir = tmp_path / "fuzz_vault"
        vault_dir.mkdir()
        for filename, content in cases:
            (vault_dir / filename).write_text(content, encoding="utf-8")

        parser = ObsidianVaultParser(vault_path=vault_dir)
        graph = parser.parse_vault()

        assert len(graph.nodes) == len(cases), f"Expected {len(cases)} nodes, got {len(graph.nodes)}"
        # Verify no crash and titles / tags safely extracted
        for nid, node in graph.nodes.items():
            assert isinstance(node.title, str)
            assert isinstance(node.tags, list)
            assert isinstance(node.features, list)
            assert isinstance(node.out_links, list)

    def test_extreme_wikilinks_fuzzing(self, tmp_path):
        """Fuzz wikilink extraction with bizarre, unclosed, path-traversal, and nested syntax."""
        adversarial_text = """
        # Adversarial Wikilink Stress
        Normal: [[ValidTarget]]
        Aliased: [[ValidTarget|Display Name With Spaces and | Pipes]]
        Anchored: [[ValidTarget#Heading-With-Dashes#Subheading]]
        Combined: [[ValidTarget#Anchor|Alias Text]]
        Path traversal: [[../../../../etc/passwd|Secrets]]
        Windows forbidden: [[CON/PRN/AUX/NUL|Forbidden Device]]
        Deep subfolder: [[00_deep/sub/dir/target_node#sec|Target Alias]]
        Unclosed 1: [[UnclosedOne
        Unclosed 2: [[UnclosedTwo|Alias
        Empty brackets: [[]]
        Only spaces: [[   ]]
        Only pipes: [[|||]]
        Only hashes: [[###]]
        Surrounded by braces: {[[TargetInsideBraces]]}
        Surrounded by markdown link: [[[MarkdownWrapped]]](http://example.com)
        Nested: [[Target|[[InnerTarget]]]]
        Back to back: [[NodeA]][[NodeB]][[NodeC]]
        Special chars in target: [[Target (v2.0) [Special] {Group}]]
        """
        vault_dir = tmp_path / "wikilink_vault"
        vault_dir.mkdir()
        (vault_dir / "wikilink_stress.md").write_text(adversarial_text, encoding="utf-8")

        parser = ObsidianVaultParser(vault_path=vault_dir)
        graph = parser.parse_vault()
        node = graph.get_node("wikilink_stress")

        assert node is not None
        # Verify valid links were extracted without crash
        target_ids = [link.target_id for link in node.out_links]
        assert "ValidTarget" in target_ids
        assert "target_node" in target_ids
        assert len(node.out_links) >= 5

    def test_multi_megabyte_markdown_document(self, tmp_path):
        """Stress parser with a 2MB markdown document containing 5,000 features and 1,000 links."""
        vault_dir = tmp_path / "big_vault"
        vault_dir.mkdir()

        lines = ["---\ntitle: Mega Benchmark Document\ncategory: Architecture & Docs\ntags: [big, stress, scale]\n---\n\n"]
        for i in range(1000):
            lines.append(f"## Section {i}\n")
            lines.append(f"- **Feature_{i}**: Comprehensive description of architectural subsystem {i} with [[Node_{i % 50}]] integration.\n")
            lines.append(f"- [[CrossLink_{i % 100}|Alias_{i}]] — **Capability {i}**\n")

        big_file = vault_dir / "MegaDoc.md"
        big_file.write_text("".join(lines), encoding="utf-8")

        t0 = time.perf_counter()
        parser = ObsidianVaultParser(vault_path=vault_dir)
        graph = parser.parse_vault()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        node = graph.get_node("MegaDoc")
        assert node is not None
        assert len(node.features) >= 1000
        assert len(node.out_links) >= 1000
        assert elapsed_ms < 500.0, f"Mega doc parse took {elapsed_ms:.2f}ms (threshold: 500ms)"


# =============================================================================
# 2. SEARCH INPUT & REGEX INJECTION CHALLENGE
# =============================================================================

class TestSearchRegexInjectionAndBoundaryFuzzing:
    """Stress tests search queries with regex metacharacters, injections, and edge cases."""

    @pytest.fixture
    def populated_graph(self):
        graph = ArchitectureGraph()
        categories = ["Canonical Module", "Infrastructure", "AI & Inference", "Biometrics & DSP", "Data & Memory"]
        for i in range(50):
            node = VaultNode(
                id=f"node_{i:02d}",
                file_path=Path(f"/vault/node_{i:02d}.md"),
                title=f"Subsystem {i} [Module-{i%5}] (v1.{i})",
                category=categories[i % len(categories)],
                tags=[f"tag_{i%10}", f"group_{i%3}", "c++", "regex-test"],
                raw_content=f"Detailed specifications for node_{i:02d} with C++ kernels and DFA-alpha1.",
                features=[VaultFeature(name=f"Feature_{i}", description=f"Description for feature {i}")],
            )
            graph.add_node(node)
        return graph

    @pytest.mark.parametrize("malicious_query", [
        ".*",
        ".+",
        "[a-z]+",
        "\\d+",
        "\\",
        "[",
        "]",
        "(",
        ")",
        "{",
        "}",
        "^$",
        "(a+)+$",
        "node_.*",
        "tag_[0-9]",
        "c++",
        "c#",
        "\x00",
        "\n\r\t",
        " " * 100,
        "a" * 10000,
        "🧠",
        "(!@#$%^&*()_+=-~`{}[]|:;'<>,.?/)",
    ])
    def test_search_injection_queries(self, populated_graph, malicious_query):
        """Verify search handles regex metacharacters, injections, and extreme strings as literal text."""
        # Must execute cleanly without re.error or infinite loops
        t0 = time.perf_counter()
        results = populated_graph.search(malicious_query)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert isinstance(results, list)
        assert elapsed_ms < 50.0, f"Search with '{malicious_query[:20]}' took {elapsed_ms:.2f}ms"

        # Specific literal search assertions
        if malicious_query == "c++":
            assert len(results) == 50  # All nodes have "c++" tag
        elif malicious_query == "node_01":
            assert any(n.id == "node_01" for n in results)


# =============================================================================
# 3. MASSIVE SYNTHETIC GRAPH TOPOLOGIES CHALLENGE
# =============================================================================

class TestMassiveSyntheticGraphTopologies:
    """Stress tests layout, Tarjan SCC cycle detection, and Sugiyama layering on extreme graphs."""

    def test_250_node_scale_free_network(self):
        """Test a synthetic scale-free network with 250 nodes and 750 edges."""
        graph = ArchitectureGraph()
        nodes = [f"N_{i:03d}" for i in range(250)]
        for nid in nodes:
            graph.add_node(VaultNode(
                id=nid,
                file_path=Path(f"/vault/{nid}.md"),
                title=f"Node {nid}",
                category="Infrastructure" if int(nid.split("_")[1]) % 2 == 0 else "AI & Inference"
            ))

        # Preferential attachment edges
        random.seed(42)
        for i in range(1, 250):
            target = random.choice(nodes[:i])
            graph.add_edge(nodes[i], target)
            if i % 3 == 0:
                # Add back-edge to create complex cycles
                graph.add_edge(target, nodes[i])

        t0 = time.perf_counter()
        sccs = graph.find_sccs()
        cycles = graph.find_cycles()
        layers = graph.get_stratified_layers()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert len(sccs) > 0
        assert len(layers) > 0
        # All 250 nodes must be accounted for in layers
        flattened_layers = [nid for layer in layers for nid in layer]
        assert len(flattened_layers) == 250
        assert elapsed_ms < 200.0, f"250-node layout and cycle detection took {elapsed_ms:.2f}ms (threshold: 200ms)"

    def test_dense_clique_k30_stress(self):
        """Test complete directed graph K_30 with 30 nodes and 870 directed edges (every node connects to all others)."""
        graph = ArchitectureGraph()
        for i in range(30):
            graph.add_node(VaultNode(
                id=f"K_{i:02d}",
                file_path=Path(f"/vault/K_{i:02d}.md"),
                title=f"Clique Node {i}",
                category="Canonical Module"
            ))

        for i in range(30):
            for j in range(30):
                if i != j:
                    graph.add_edge(f"K_{i:02d}", f"K_{j:02d}")

        t0 = time.perf_counter()
        cycles = graph.find_cycles()
        layers = graph.get_stratified_layers()
        renderer = AsciiGraphRenderer(graph)
        ansi_output = renderer.render_ansi()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Entire K_30 is a single SCC cycle of 30 nodes
        assert len(cycles) == 1
        assert len(cycles[0]) == 30
        assert len(layers) > 0
        assert "↺ STRONGLY CONNECTED CYCLES" in ansi_output
        assert elapsed_ms < 100.0, f"Dense K_30 clique render took {elapsed_ms:.2f}ms (threshold: 100ms)"

    def test_deep_linear_chain_500_nodes(self):
        """Test linear chain graph with 500 nodes (1 -> 2 -> 3 -> ... -> 500)."""
        graph = ArchitectureGraph()
        for i in range(500):
            graph.add_node(VaultNode(
                id=f"Chain_{i:03d}",
                file_path=Path(f"/vault/Chain_{i:03d}.md"),
                title=f"Chain Element {i}",
                category="Tooling & Scripts"
            ))
            if i > 0:
                graph.add_edge(f"Chain_{i-1:03d}", f"Chain_{i:03d}")

        t0 = time.perf_counter()
        layers = graph.get_stratified_layers()
        cycles = graph.find_cycles()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert len(cycles) == 0
        assert len(layers) == 500, f"Expected 500 layers, got {len(layers)}"
        assert elapsed_ms < 200.0, f"500-node linear chain layering took {elapsed_ms:.2f}ms"

    def test_disconnected_archipelago_100_triangles(self):
        """Test 100 isolated 3-node cyclic components (300 nodes, 300 edges)."""
        graph = ArchitectureGraph()
        for i in range(100):
            a, b, c = f"A_{i}", f"B_{i}", f"C_{i}"
            graph.add_node(VaultNode(id=a, file_path=Path(f"/{a}.md"), title=a))
            graph.add_node(VaultNode(id=b, file_path=Path(f"/{b}.md"), title=b))
            graph.add_node(VaultNode(id=c, file_path=Path(f"/{c}.md"), title=c))
            graph.add_edge(a, b)
            graph.add_edge(b, c)
            graph.add_edge(c, a)

        cycles = graph.find_cycles()
        assert len(cycles) == 100
        layers = graph.get_stratified_layers()
        flattened = [nid for l in layers for nid in l]
        assert len(flattened) == 300


# =============================================================================
# 4. EXTREME TERMINAL GEOMETRIES & RENDERING BOUNDS CHALLENGE
# =============================================================================

class TestExtremeTerminalGeometriesAndMarkupSafety:
    """Stress tests AsciiGraphRenderer with extreme width limits and Rich markup injection."""

    def test_rich_markup_injection_in_node_ids_and_titles(self):
        """Ensure node IDs containing Rich markup tags ([red], [/bold], etc.) do not break rendering."""
        graph = ArchitectureGraph()
        malicious_nodes = [
            ("node_[bold_red]_1", "Title [yellow]With Markup[/yellow]", "Infrastructure"),
            ("[italic]node_2[/italic]", "Title [[Nested Brackets]]", "AI & Inference"),
            ("node_3_tag[blue]", "Title / [dim]dim[/dim] / [blink]blink[/blink]", "Canonical Module"),
        ]
        for nid, title, cat in malicious_nodes:
            graph.add_node(VaultNode(
                id=nid,
                file_path=Path(f"/{nid}.md"),
                title=title,
                category=cat
            ))
        graph.add_edge("node_[bold_red]_1", "[italic]node_2[/italic]")

        renderer = AsciiGraphRenderer(graph)
        ansi = renderer.render_ansi()
        assert isinstance(ansi, str)
        assert len(ansi) > 0

    @pytest.mark.parametrize("max_width", [10, 25, 40, 60, 80, 120, 200, 500, 1000])
    def test_renderer_width_scaling_extremes(self, max_width):
        """Test AsciiGraphRenderer across extreme width boundaries without crashes."""
        graph = ArchitectureGraph()
        for i in range(10):
            graph.add_node(VaultNode(id=f"Node_{i}", file_path=Path(f"/Node_{i}.md"), title=f"Architecture Node {i}"))
            if i > 0:
                graph.add_edge(f"Node_{i-1}", f"Node_{i}")

        renderer = AsciiGraphRenderer(graph)
        output = renderer.render_ansi(max_width=max_width)
        assert "OBSIDIAN ARCHITECTURE TOPOLOGY CANVAS" in output
        assert "Node_0" in output


# =============================================================================
# 5. TEXTUAL PILOT UI CHURN & RACE CONDITION STRESS
# =============================================================================

class TestTextualPilotUiChurnAndInteractionStress:
    """Adversarial Textual Pilot tests for high-frequency user interactions, rapid filtering, and resizing."""

    @pytest.mark.asyncio
    async def test_pilot_rapid_keystroke_churn(self):
        """Simulate a user hammering the search input with rapid keystrokes."""
        app = StandaloneExplorerApp()
        async with app.run_test(size=(160, 50)) as pilot:
            view = app.query_one(ArchitectureExplorerView)
            search_input = view.query_one("#explorer-search-input", Input)

            # Rapid sequential typing and clearing
            test_words = ["seaweedfs", "petals", "movesense", "pyspark", "audit", "index", "00_", "nonexistent_term_xyz"]
            for word in test_words:
                search_input.value = word
                await pilot.pause(0.01)

            search_input.value = ""
            await pilot.pause(0.05)
            assert len(view.graph.nodes) >= 50

    @pytest.mark.asyncio
    async def test_pilot_hammer_all_category_chips_rapidly(self):
        """Simulate a user rapidly clicking all 10 category chips in random sequence."""
        app = StandaloneExplorerApp()
        async with app.run_test(size=(160, 50)) as pilot:
            view = app.query_one(ArchitectureExplorerView)
            chip_ids = [
                "#chip-all", "#chip-modules", "#chip-infra", "#chip-ai",
                "#chip-bio", "#chip-data", "#chip-gov", "#chip-tool",
                "#chip-docs", "#chip-audit"
            ]

            # Click 30 chips in fast succession
            for i in range(30):
                chosen_chip = chip_ids[i % len(chip_ids)]
                await pilot.click(chosen_chip)
                await pilot.pause(0.005)

            await pilot.click("#chip-all")
            await pilot.pause(0.05)
            assert view.active_category is None

    @pytest.mark.asyncio
    async def test_pilot_extreme_resizing_stress(self):
        """Rapidly bounce terminal dimensions between micro-terminal and massive ultra-wide."""
        app = StandaloneExplorerApp()
        async with app.run_test(size=(160, 50)) as pilot:
            dimensions = [
                (40, 15),
                (300, 100),
                (30, 10),
                (200, 60),
                (80, 24),
                (160, 50),
            ]
            for width, height in dimensions:
                await pilot.resize_terminal(width, height)
                await pilot.pause(0.02)

            view = app.query_one(ArchitectureExplorerView)
            assert view is not None

    @pytest.mark.asyncio
    async def test_pilot_repeated_screen_toggle_and_vault_reload_stress(self):
        """Rapidly toggle screen and trigger reload actions under continuous pilot load."""
        app = CanonicalPortApp()
        async with app.run_test(size=(160, 50)) as pilot:
            for _ in range(3):
                await pilot.press("e")  # Switch to explorer
                await pilot.pause(0.02)
                await pilot.press("r")  # Reload vault
                await pilot.pause(0.02)
                await pilot.press("slash")  # Focus search
                await pilot.pause(0.02)
                await pilot.press("escape")  # Pop screen
                await pilot.pause(0.02)

            assert app is not None
