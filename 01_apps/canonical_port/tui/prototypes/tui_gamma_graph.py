#!/usr/bin/env python3
"""
Canonical Port TUI Prototype Gamma — Obsidian Topology & Knowledge Explorer
Version: 1.0.0-GAMMA (M2 Competitive Swarm)
Paradigm: Graph & Architecture-Heavy Command Center

Features:
- Collapsible Left Sidebar (25% width):
  * Real-time search input ('/' to focus) with fuzzy substring matching.
  * 10 Quick-Filter Category Chips ([All], [Modules], [Infra], [AI], [Biometrics], [Data], [Governance], [Tooling], [Docs], [Audit]).
  * Hierarchical Obsidian Knowledge Tree with expand/collapse and dependency link counts.
  * Sidebar collapse/expand toggle ('b' keybinding).
- Center Canvas (55% width - Primary Focus):
  * Expansive ASCII/ANSI directed topology canvas rendered via Sugiyama layered layout.
  * Tarjan SCC cycle component badges ('↺ SCC') and bidirectional dependency flow vectors.
  * Zoom / Depth selector ('Depth: 1 / 2 / 3 / All') and Layer isolation toggles ([Layer: All], [L0], [L1], [L2], [L3+]).
  * Detail / Compact canvas render modes.
- Right Inspector Pane (20% width):
  * Markdown Architecture Document Inspector (Frontmatter, tags, backlinks, features, subsystem specifications).
  * Code AST Metrics Card (PySpark LOC count, AST file counts, language breakdowns).
- Bottom Dock:
  * Graph Metrics HUD (Total nodes, total edges, graph density, dangling link count, average degree, SCC cycles).
- Live Synchronization:
  * Selecting a node in the tree or search updates the ASCII canvas highlight, depth subgraph, and Markdown detail pane simultaneously.
"""

import os
import sys
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Markdown,
    Static,
    Tree,
)

# Ensure tui and parent directories are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_TUI_DIR = _CURRENT_DIR.parent
_APP_DIR = _TUI_DIR.parent
for p in [str(_TUI_DIR), str(_APP_DIR), str(_CURRENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from models.architecture_graph import (
        ArchitectureGraph,
        VaultFeature,
        VaultNode,
        WikilinkRef,
    )
    from services.ascii_graph_renderer import AsciiGraphRenderer
    from services.obsidian_vault_parser import ObsidianVaultParser
except ImportError:
    try:
        from tui.models.architecture_graph import (
            ArchitectureGraph,
            VaultFeature,
            VaultNode,
            WikilinkRef,
        )
        from tui.services.ascii_graph_renderer import AsciiGraphRenderer
        from tui.services.obsidian_vault_parser import ObsidianVaultParser
    except ImportError:
        @dataclass
        class WikilinkRef:
            target_id: str
            raw_target: str = ""
            alias: Optional[str] = None
            anchor: Optional[str] = None
            source_file: str = ""
            line_number: int = 0

            @property
            def display_text(self) -> str:
                if self.alias:
                    return self.alias
                if self.anchor:
                    return f"{self.target_id}#{self.anchor}"
                return self.target_id

        @dataclass
        class VaultFeature:
            name: str
            description: str = ""
            section: str = ""
            line_number: int = 0

        @dataclass
        class VaultNode:
            id: str
            file_path: Path
            title: str
            category: str = "Uncategorized"
            tags: List[str] = field(default_factory=list)
            updated: str = ""
            frontmatter: Dict[str, Any] = field(default_factory=dict)
            features: List[VaultFeature] = field(default_factory=list)
            headings: List[str] = field(default_factory=list)
            raw_content: str = ""
            out_links: List[WikilinkRef] = field(default_factory=list)
            in_links: List[str] = field(default_factory=list)
            in_degree: int = 0
            out_degree: int = 0

            def has_tag(self, tag: str) -> bool:
                clean = tag.strip().lstrip("#").lower()
                return any(t.lower() == clean for t in self.tags)

            def matches_query(self, query: str) -> bool:
                if not query:
                    return True
                q = query.lower().strip()
                tokens = q.split()
                haystack = f"{self.id} {self.title} {self.category} {' '.join(self.tags)} {' '.join(f.name for f in self.features)} {self.raw_content}".lower()
                return all(token in haystack for token in tokens)

        @dataclass
        class ArchitectureGraph:
            nodes: Dict[str, VaultNode] = field(default_factory=dict)
            edges: List[Tuple[str, str]] = field(default_factory=list)
            dangling_links: Set[str] = field(default_factory=set)
            categories: Set[str] = field(default_factory=set)

            def add_node(self, node: VaultNode) -> None:
                self.nodes[node.id] = node
                if node.category:
                    self.categories.add(node.category)

            def add_edge(self, source_id: str, target_id: str) -> None:
                if (source_id, target_id) not in self.edges:
                    self.edges.append((source_id, target_id))
                if source_id in self.nodes:
                    self.nodes[source_id].out_degree = len(self.get_out_edges(source_id))
                if target_id in self.nodes:
                    self.nodes[target_id].in_degree = len(self.get_in_edges(target_id))

            def get_node(self, node_id: str) -> Optional[VaultNode]:
                return self.nodes.get(node_id)

            def get_out_edges(self, node_id: str) -> List[str]:
                return [dst for src, dst in self.edges if src == node_id]

            def get_in_edges(self, node_id: str) -> List[str]:
                return [src for src, dst in self.edges if dst == node_id]

            def filter_nodes(self, category: Optional[str] = None, query: str = "", tags: Optional[List[str]] = None) -> List[VaultNode]:
                results = []
                clean_cat = category.strip().lower() if category and category != "All" else None
                for node in self.nodes.values():
                    if clean_cat and node.category.lower() != clean_cat:
                        continue
                    if tags and not all(node.has_tag(t) for t in tags):
                        continue
                    if query and not node.matches_query(query):
                        continue
                    results.append(node)
                return results

            def get_category_distribution(self) -> Dict[str, int]:
                dist: Dict[str, int] = {}
                for node in self.nodes.values():
                    cat = node.category or "Uncategorized"
                    dist[cat] = dist.get(cat, 0) + 1
                return dist

            def get_metrics(self) -> Dict[str, Any]:
                total_nodes = len(self.nodes)
                total_edges = len(self.edges)
                avg_deg = (total_edges / total_nodes) if total_nodes > 0 else 0.0
                density = (total_edges / (total_nodes * (total_nodes - 1))) if total_nodes > 1 else 0.0
                return {
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "dangling_links_count": len(self.dangling_links),
                    "categories_count": len(self.categories),
                    "category_distribution": self.get_category_distribution(),
                    "avg_degree": round(avg_deg, 2),
                    "density": round(density, 4),
                    "cycles_count": len(self.find_cycles()),
                }

            def find_sccs(self, node_subset: Optional[Set[str]] = None) -> List[List[str]]:
                nodes_to_check = set(self.nodes.keys()) if node_subset is None else (node_subset & set(self.nodes.keys()))
                index_counter = 0
                stack: List[str] = []
                indices: Dict[str, int] = {}
                lowlinks: Dict[str, int] = {}
                on_stack: Set[str] = set()
                sccs: List[List[str]] = []

                def strongconnect(v: str) -> None:
                    nonlocal index_counter
                    indices[v] = index_counter
                    lowlinks[v] = index_counter
                    index_counter += 1
                    stack.append(v)
                    on_stack.add(v)

                    for w in self.get_out_edges(v):
                        if w not in nodes_to_check:
                            continue
                        if w not in indices:
                            strongconnect(w)
                            lowlinks[v] = min(lowlinks[v], lowlinks[w])
                        elif w in on_stack:
                            lowlinks[v] = min(lowlinks[v], indices[w])

                    if lowlinks[v] == indices[v]:
                        scc: List[str] = []
                        while True:
                            w = stack.pop()
                            on_stack.remove(w)
                            scc.append(w)
                            if w == v:
                                break
                        sccs.append(scc)

                for node_id in sorted(nodes_to_check):
                    if node_id not in indices:
                        strongconnect(node_id)
                return sccs

            def find_cycles(self, node_subset: Optional[Set[str]] = None) -> List[List[str]]:
                sccs = self.find_sccs(node_subset=node_subset)
                cycles: List[List[str]] = []
                for scc in sccs:
                    if len(scc) > 1:
                        cycles.append(sorted(scc))
                    elif len(scc) == 1:
                        node = scc[0]
                        if node in self.get_out_edges(node):
                            cycles.append([node])
                return cycles

            def get_stratified_layers(self, node_subset: Optional[Set[str]] = None) -> List[List[str]]:
                active_nodes = set(self.nodes.keys()) if node_subset is None else (node_subset & set(self.nodes.keys()))
                if not active_nodes:
                    return []
                cycles = self.find_cycles(node_subset=active_nodes)
                cycle_edges: Set[Tuple[str, str]] = set()
                for cyc in cycles:
                    cyc_set = set(cyc)
                    for u in cyc:
                        for v in self.get_out_edges(u):
                            if v in cyc_set:
                                cycle_edges.add((u, v))

                in_degree: Dict[str, int] = {nid: 0 for nid in active_nodes}
                adj: Dict[str, List[str]] = {nid: [] for nid in active_nodes}
                for src, dst in self.edges:
                    if src in active_nodes and dst in active_nodes:
                        if (src, dst) in cycle_edges and src > dst:
                            continue
                        adj[src].append(dst)
                        in_degree[dst] += 1

                layers: List[List[str]] = []
                current_layer = [nid for nid in active_nodes if in_degree[nid] == 0]
                if not current_layer:
                    min_deg = min(in_degree.values())
                    current_layer = [nid for nid, deg in in_degree.items() if deg == min_deg]

                visited: Set[str] = set()
                while current_layer:
                    layers.append(sorted(current_layer))
                    visited.update(current_layer)
                    next_layer: List[str] = []
                    for node in current_layer:
                        for neighbor in adj[node]:
                            in_degree[neighbor] -= 1
                            if in_degree[neighbor] <= 0 and neighbor not in visited and neighbor not in next_layer:
                                next_layer.append(neighbor)
                    if not next_layer:
                        remaining = [nid for nid in active_nodes if nid not in visited]
                        if remaining:
                            min_deg = min(in_degree[nid] for nid in remaining)
                            next_layer = [nid for nid in remaining if in_degree[nid] == min_deg]
                    current_layer = next_layer
                return layers


# =============================================================================
# PYSPARK AST METRICS LOADER (Authentic Monorepo Codebase Metrics)
# =============================================================================

@dataclass
class AstMetricsData:
    """Represents real AST metrics parsed from PYSPARK_MONOREPO_CRAWL_AUG26.md"""
    scan_date: str = "2026-08-26"
    total_projects: int = 32
    total_files: int = 3104
    total_loc: int = 434965
    total_tests: int = 325
    languages: Dict[str, int] = field(default_factory=lambda: {
        "Markdown": 2228,
        "Python": 752,
        "JSON": 30,
        "TypeScript": 24,
        "Shell": 22,
        "JavaScript": 14,
        "TOML": 13,
        "YAML": 11,
        "HTML": 4,
        "CSS": 3,
        "Rust": 1,
    })
    project_loc_map: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "00_core_infrastructure": {"loc": 23344, "files": 184, "tests": 18, "langs": "Python, Shell, TOML"},
        "01_apps": {"loc": 25438, "files": 204, "tests": 36, "langs": "Python, JS, HTML"},
        "02_ai_models_and_inference": {"loc": 17587, "files": 177, "tests": 11, "langs": "Python, Markdown, TOML"},
        "03_biometrics_and_telemetry": {"loc": 13547, "files": 162, "tests": 5, "langs": "Python, Markdown, JSON"},
        "04_data_and_memory": {"loc": 14886, "files": 104, "tests": 6, "langs": "Python, Markdown, JSON"},
        "05_agents_and_swarms": {"loc": 88352, "files": 158, "tests": 26, "langs": "Python, Markdown, JSON"},
        "06_scripts_and_tooling": {"loc": 17030, "files": 124, "tests": 17, "langs": "Python, Shell, JSON"},
        "07_docs_and_architecture": {"loc": 12920, "files": 106, "tests": 5, "langs": "Markdown, Python, Rust"},
        "08_business_and_commerce": {"loc": 18635, "files": 158, "tests": 40, "langs": "HTML, JS, CSS"},
        "09_app_store_and_release": {"loc": 15823, "files": 167, "tests": 11, "langs": "JS, Markdown, JSON"},
        "10_spatial_grappling_kinematics": {"loc": 13454, "files": 133, "tests": 20, "langs": "JS, HTML, CSS"},
        "11_security_and_governance": {"loc": 13933, "files": 106, "tests": 23, "langs": "Python, TOML, Markdown"},
        "12_continuous_lora_evolution": {"loc": 16150, "files": 96, "tests": 6, "langs": "Python, Markdown, JSON"},
        "Index": {"loc": 434965, "files": 3104, "tests": 325, "langs": "11 Polyglot Languages"},
    })

    @classmethod
    def load_from_vault(cls, vault_path: Optional[Path] = None) -> "AstMetricsData":
        """Loads metrics from PYSPARK_MONOREPO_CRAWL_AUG26.md if present."""
        data = cls()
        if not vault_path:
            return data

        crawl_file = vault_path / "PYSPARK_MONOREPO_CRAWL_AUG26.md"
        if not crawl_file.exists():
            matches = list(vault_path.rglob("PYSPARK_MONOREPO_CRAWL_AUG26.md"))
            if matches:
                crawl_file = matches[0]
            else:
                return data

        try:
            content = crawl_file.read_text(encoding="utf-8", errors="replace")
            m_files = re.search(r"\*\*Total Code Files:\*\*\s*([\d,]+)", content)
            if m_files:
                data.total_files = int(m_files.group(1).replace(",", ""))
            m_loc = re.search(r"\*\*Total LOC:\*\*\s*([\d,]+)", content)
            if m_loc:
                data.total_loc = int(m_loc.group(1).replace(",", ""))
            m_tests = re.search(r"\*\*Total Test Files:\*\*\s*([\d,]+)", content)
            if m_tests:
                data.total_tests = int(m_tests.group(1).replace(",", ""))
            m_proj = re.search(r"\*\*Total Projects:\*\*\s*([\d,]+)", content)
            if m_proj:
                data.total_projects = int(m_proj.group(1).replace(",", ""))

            lang_matches = re.findall(r"\|\s*([a-zA-Z\s]+)\s*\|\s*(\d+)\s*files\s*\|", content)
            if lang_matches:
                data.languages = {name.strip(): int(count) for name, count in lang_matches}
        except Exception:
            pass

        return data


# =============================================================================
# ENHANCED TOPOLOGY CANVAS RENDERER WITH DEPTH & LAYER ISOLATION
# =============================================================================

class GammaTopologyRenderer:
    """
    Renders the Sugiyama layered architecture graph with depth isolation,
    Tarjan SCC cycle badges, bidirectional flow vectors, and layer slicing.
    """

    CATEGORY_COLORS: Dict[str, str] = {
        "Canonical Module": "#00ffcc",
        "Infrastructure": "#38bdf8",
        "AI & Inference": "#e879f9",
        "Biometrics & DSP": "#4ade80",
        "Data & Memory": "#facc15",
        "Swarm & Governance": "#f43f5e",
        "Tooling & Scripts": "#a78bfa",
        "Architecture & Docs": "#ffffff",
        "Audit & Telemetry": "#fb923c",
        "Uncategorized": "#94a3b8",
    }

    CATEGORY_ICONS: Dict[str, str] = {
        "Canonical Module": "📦",
        "Infrastructure": "🌐",
        "AI & Inference": "🧠",
        "Biometrics & DSP": "💓",
        "Data & Memory": "💾",
        "Swarm & Governance": "⚖️",
        "Tooling & Scripts": "🛠️",
        "Architecture & Docs": "🏛️",
        "Audit & Telemetry": "📊",
        "Uncategorized": "📄",
    }

    def __init__(self, graph: ArchitectureGraph) -> None:
        self.graph = graph

    def get_neighborhood_subgraph(
        self,
        root_id: str,
        depth: int,
        active_set: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Computes the k-hop neighborhood around root_id across active graph nodes.
        """
        allowed = active_set if active_set is not None else set(self.graph.nodes.keys())
        if root_id not in self.graph.nodes or root_id not in allowed:
            return allowed

        visited: Set[str] = {root_id}
        current_level: Set[str] = {root_id}

        for _ in range(depth):
            next_level: Set[str] = set()
            for nid in current_level:
                for out_nid in self.graph.get_out_edges(nid):
                    if out_nid in allowed and out_nid not in visited:
                        visited.add(out_nid)
                        next_level.add(out_nid)
                for in_nid in self.graph.get_in_edges(nid):
                    if in_nid in allowed and in_nid not in visited:
                        visited.add(in_nid)
                        next_level.add(in_nid)
            current_level = next_level
            if not current_level:
                break

        return visited

    def render_canvas(
        self,
        filtered_nodes: Optional[Set[str]] = None,
        selected_node: Optional[str] = None,
        depth_limit: Optional[int] = None,
        layer_isolation: Optional[int] = None,
        detailed_mode: bool = True,
        max_width: int = 100,
    ) -> str:
        """
        Renders the Sugiyama layered topology canvas with rich ANSI box connectors,
        Tarjan SCC cycle badges, bidirectional dependency flow vectors, and layer isolation.
        """
        active_nodes = filtered_nodes if filtered_nodes is not None else set(self.graph.nodes.keys())
        active_nodes = active_nodes & set(self.graph.nodes.keys())

        if not active_nodes:
            return (
                "\n\n[bold yellow]  ╔══════════════════════════════════════════════════════════════════════════════════╗[/bold yellow]\n"
                "[bold yellow]  ║                         NO MATCHING ARCHITECTURE NODES                             ║[/bold yellow]\n"
                "[bold yellow]  ║  Adjust category chips or clear search query to explore the topology.              ║[/bold yellow]\n"
                "[bold yellow]  ╚══════════════════════════════════════════════════════════════════════════════════╝[/bold yellow]\n"
            )

        # Apply Depth Limit Subgraph if selected
        if depth_limit is not None and selected_node and selected_node in active_nodes:
            active_nodes = self.get_neighborhood_subgraph(selected_node, depth_limit, active_nodes)

        # Compute Sugiyama Stratified Layers
        layers = self.graph.get_stratified_layers(node_subset=active_nodes)
        if not layers:
            layers = [sorted(list(active_nodes))]

        # Apply Layer Isolation if selected (0=L0, 1=L1, 2=L2, 3=L3+)
        if layer_isolation is not None:
            if layer_isolation < len(layers):
                if layer_isolation >= 3 and len(layers) > 3:
                    isolated_set: Set[str] = set()
                    for idx in range(3, len(layers)):
                        isolated_set.update(layers[idx])
                    layers = [sorted(list(isolated_set))]
                else:
                    layers = [layers[layer_isolation]]
            else:
                layers = [layers[-1]] if layers else []

        # Barycentric Crossing Reduction
        ordered_layers: List[List[str]] = []
        for layer_idx, layer in enumerate(layers):
            if layer_idx == 0:
                ordered_layers.append(sorted(layer))
                continue

            prev_layer = ordered_layers[layer_idx - 1]
            barycenters: List[Tuple[float, str]] = []
            for node_id in layer:
                parents = [p for p in self.graph.get_in_edges(node_id) if p in prev_layer]
                if parents:
                    b_val = sum(prev_layer.index(p) for p in parents) / len(parents)
                else:
                    b_val = float(layer.index(node_id))
                barycenters.append((b_val, node_id))

            barycenters.sort(key=lambda x: (x[0], x[1]))
            ordered_layers.append([nid for _, nid in barycenters])

        # Identify Cycles and Bidirectional Edges
        cycles = self.graph.find_cycles(node_subset=active_nodes)
        cycle_node_set: Set[str] = set(nid for cyc in cycles for nid in cyc)

        bidirectional_map: Dict[str, Set[str]] = {}
        for u in active_nodes:
            for v in self.graph.get_out_edges(u):
                if v in active_nodes and u in self.graph.get_out_edges(v):
                    bidirectional_map.setdefault(u, set()).add(v)

        lines: List[str] = []

        total_sub_nodes = sum(len(layer) for layer in ordered_layers)
        total_sub_edges = len([
            (s, d) for s, d in self.graph.edges if s in active_nodes and d in active_nodes
        ])
        depth_label = f"Depth {depth_limit}" if depth_limit else "Depth All"
        layer_label = f"L{layer_isolation}" if layer_isolation is not None else "All Layers"
        mode_label = "Detailed" if detailed_mode else "Compact"

        lines.append(
            "[bold #00ffcc]╔══════════════════════════════════════════════════════════════════════════════════════════════════╗[/bold #00ffcc]"
        )
        lines.append(
            f"[bold #00ffcc]║[/bold #00ffcc] [bold white]SUGIYAMA DIRECTED TOPOLOGY CANVAS[/bold white] │ "
            f"[cyan]Nodes:[/cyan] [bold green]{total_sub_nodes}[/bold green] │ "
            f"[cyan]Edges:[/cyan] [bold yellow]{total_sub_edges}[/bold yellow] │ "
            f"[cyan]Layers:[/cyan] [bold magenta]{len(ordered_layers)}[/bold magenta] │ "
            f"[cyan]SCC:[/cyan] [{'bold red' if cycles else 'bold green'}]{len(cycles)}[/{'bold red' if cycles else 'bold green'}] │ "
            f"[dim cyan]{depth_label} • {layer_label} • {mode_label}[/dim cyan] [bold #00ffcc]║[/bold #00ffcc]"
        )
        lines.append(
            "[bold #00ffcc]╚══════════════════════════════════════════════════════════════════════════════════════════════════╝[/bold #00ffcc]\n"
        )

        box_width = min(max(max_width - 8, 60), 86)

        # Render Layers
        for layer_idx, layer_nodes in enumerate(ordered_layers):
            effective_idx = layer_idx if layer_isolation is None else layer_isolation
            layer_title = f" STRATA LAYER {effective_idx:02d} ({len(layer_nodes)} node{'s' if len(layer_nodes) != 1 else ''}) "
            bar_len = max(4, box_width - len(layer_title) - 4)
            left_bar = "─" * 4
            right_bar = "─" * bar_len
            lines.append(
                f"[dim #334155]──{left_bar}[/dim #334155][bold #38bdf8]{layer_title}[/bold #38bdf8][dim #334155]{right_bar}──[/dim #334155]"
            )

            for node_id in layer_nodes:
                node = self.graph.get_node(node_id)
                if not node:
                    continue

                is_selected = (node_id == selected_node)
                is_cyclic = (node_id in cycle_node_set)
                color = self.CATEGORY_COLORS.get(node.category, "#94a3b8")
                icon = self.CATEGORY_ICONS.get(node.category, "📄")

                cycle_badge = " [bold red]↺ SCC[/bold red]" if is_cyclic else ""
                select_badge = " [bold black on #00ffcc] ★ SELECTED [/bold black on #00ffcc]" if is_selected else ""
                bidi_badge = " [bold #e879f9]⇄ BIDI[/bold #e879f9]" if node_id in bidirectional_map else ""

                border_style = "bold #00ffcc on #0f172a" if is_selected else f"bold {color}"
                top_border = "╭" + ("─" * (box_width - 2)) + "╮"
                bot_border = "╰" + ("─" * (box_width - 2)) + "╯"

                lines.append(f"[{border_style}]  {top_border}[/{border_style}]")
                lines.append(
                    f"[{border_style}]  │[/{border_style}] {icon} [{border_style}][bold]{node.id}[/bold][/{border_style}]{cycle_badge}{bidi_badge}{select_badge}"
                    f" [{'dim ' + color}]({node.category})[/{'dim ' + color}]"
                )

                if detailed_mode:
                    if node.title and node.title != node.id:
                        title_clean = (node.title[:45] + "...") if len(node.title) > 48 else node.title
                        lines.append(f"[{border_style}]  │[/{border_style}]   [dim]Title:[/dim] [white]{title_clean}[/white]")

                    tags_str = ", ".join(f"#{t}" for t in node.tags[:4]) if node.tags else "none"
                    lines.append(
                        f"[{border_style}]  │[/{border_style}]   [dim]In:[/dim] [green]{node.in_degree}[/green] [dim]│ Out:[/dim] [yellow]{node.out_degree}[/yellow] "
                        f"[dim]│ Feats:[/dim] [cyan]{len(node.features)}[/cyan] [dim]│ Tags:[/dim] [dim]{tags_str}[/dim]"
                    )

                    if node_id in bidirectional_map:
                        bidi_targets = ", ".join(sorted(bidirectional_map[node_id]))
                        lines.append(f"[{border_style}]  │[/{border_style}]   [bold #e879f9]⇄ Flow Vectors:[/bold #e879f9] [magenta]{bidi_targets}[/magenta]")

                    active_out = [dst for dst in self.graph.get_out_edges(node_id) if dst in active_nodes]
                    if active_out:
                        out_preview = ", ".join(active_out[:3])
                        if len(active_out) > 3:
                            out_preview += f" (+{len(active_out) - 3} more)"
                        lines.append(f"[{border_style}]  │[/{border_style}]   [bold yellow]──▶ Outflows:[/bold yellow] [dim cyan]{out_preview}[/dim cyan]")

                lines.append(f"[{border_style}]  {bot_border}[/{border_style}]")

            if layer_idx < len(ordered_layers) - 1:
                next_layer_nodes = ordered_layers[layer_idx + 1]
                edge_count_between = sum(
                    1 for u in layer_nodes for v in self.graph.get_out_edges(u) if v in next_layer_nodes
                )
                if edge_count_between > 0:
                    lines.append(f"        [bold #38bdf8]│      ├──┴──▶ ({edge_count_between} downstream links)[/bold #38bdf8]")
                    lines.append("        [bold #38bdf8]▼[/bold #38bdf8]")
                else:
                    lines.append("        [dim]│[/dim]")
                    lines.append("        [dim]▼[/dim]")

        if cycles:
            lines.append("\n[bold red]╔══════════════════════════════════════════════════════════════════════════════════════════════════╗[/bold red]")
            lines.append("[bold red]║ ↺ STRONGLY CONNECTED CYCLIC COMPONENTS (TARJAN SCC ISOLATED)                                     ║[/bold red]")
            lines.append("[bold red]╠══════════════════════════════════════════════════════════════════════════════════════════════════╣[/bold red]")
            for idx, cyc in enumerate(cycles[:6], 1):
                cyc_str = " ⇄ ".join(cyc[:6])
                if len(cyc) > 6:
                    cyc_str += f" ⇄ ... (+{len(cyc) - 6} more)"
                lines.append(f"[bold red]║[/bold red] [yellow]Cycle #{idx} ({len(cyc)} nodes):[/yellow] [white]{cyc_str}[/white]")
            lines.append("[bold red]╚══════════════════════════════════════════════════════════════════════════════════════════════════╝[/bold red]")

        return "\n".join(lines)


# =============================================================================
# TUI-GAMMA STANDALONE APPLICATION
# =============================================================================

class TuiGammaGraphApp(App):
    """
    Obsidian Topology & Knowledge Explorer (TUI-Gamma).
    Graph & Architecture-heavy paradigm for the Canonical Port.
    """

    TITLE = "CANONICAL PORT — TUI-GAMMA: OBSIDIAN TOPOLOGY & KNOWLEDGE EXPLORER"
    SUB_TITLE = "Sugiyama Directed Canvas • Tarjan SCC Cycles • PySpark AST Metrics • 3-Pane Architecture Cockpit"

    CSS = """
    Screen {
        background: #070b12;
        color: #e2e8f0;
        layout: vertical;
    }

    Header {
        dock: top;
        height: 1;
        background: #0b111c;
    }

    Footer {
        dock: bottom;
        height: 1;
        background: #070b12;
        border-top: solid #1e293b;
    }

    #gamma-main-container {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }

    /* LEFT SIDEBAR: 25% */
    #gamma-left-sidebar {
        width: 25%;
        height: 1fr;
        border-right: solid #1e293b;
        background: #070b12;
        padding: 0 1;
    }

    #gamma-left-sidebar.collapsed {
        display: none;
    }

    #gamma-sidebar-header {
        height: auto;
        margin-bottom: 1;
        layout: horizontal;
    }

    #gamma-sidebar-title {
        width: 1fr;
        color: #00ffcc;
        text-style: bold;
        padding-top: 1;
    }

    #gamma-btn-toggle-sidebar {
        width: auto;
        min-width: 4;
        height: 1;
        background: #1e293b;
        color: #38bdf8;
        border: none;
    }

    #gamma-search-input {
        height: 3;
        margin-bottom: 1;
        border: solid #00ffcc;
        background: #0b111c;
        color: #e2e8f0;
    }

    #gamma-category-container {
        height: auto;
        margin-bottom: 1;
        layout: vertical;
    }

    .chip-row {
        height: auto;
        margin-bottom: 1;
        layout: horizontal;
    }

    .gamma-chip {
        width: auto;
        min-width: 4;
        height: 1;
        margin-right: 1;
        padding: 0 1;
        border: none;
        background: #1e293b;
        color: #94a3b8;
    }

    .gamma-chip.active {
        background: #00ffcc;
        color: #070b12;
        text-style: bold;
    }

    #gamma-tree {
        height: 1fr;
        border: solid #1e293b;
        background: #0b111c;
        margin-bottom: 1;
    }

    /* CENTER CANVAS: 55% */
    #gamma-center-canvas {
        width: 55%;
        height: 1fr;
        background: #070b12;
        padding: 0 1;
    }

    #gamma-center-canvas.expanded {
        width: 80%;
    }

    #gamma-canvas-controls {
        height: auto;
        margin-bottom: 1;
        layout: vertical;
        background: #0b111c;
        border: solid #1e293b;
        padding: 0 1;
    }

    #gamma-depth-controls, #gamma-layer-controls {
        height: auto;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }

    .control-label {
        width: auto;
        min-width: 7;
        height: 1;
        color: #94a3b8;
        text-style: bold;
        padding-top: 0;
        margin-right: 1;
    }

    .control-btn {
        width: auto;
        min-width: 4;
        height: 1;
        margin-right: 1;
        padding: 0 1;
        border: none;
        background: #1e293b;
        color: #94a3b8;
    }

    .control-btn.active {
        background: #38bdf8;
        color: #070b12;
        text-style: bold;
    }

    #gamma-canvas-scroll {
        height: 1fr;
        border: solid #1e293b;
        background: #070b12;
        padding: 0 1;
    }

    #gamma-ascii-canvas {
        width: 100%;
        height: auto;
    }

    /* RIGHT INSPECTOR PANE: 20% */
    #gamma-right-inspector {
        width: 20%;
        height: 1fr;
        border-left: solid #1e293b;
        background: #070b12;
        padding: 0 1;
    }

    #gamma-ast-metrics-card {
        height: auto;
        margin-bottom: 1;
    }

    #gamma-markdown-container {
        height: 1fr;
        border: solid #1e293b;
        background: #0b111c;
        padding: 1;
    }

    /* BOTTOM DOCK HUD */
    #gamma-bottom-hud {
        dock: bottom;
        height: 4;
        background: #0b111c;
        border-top: solid #00ffcc;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("/", "focus_search", "Search (/)", show=True),
        Binding("b", "toggle_sidebar", "Toggle Sidebar (b)", show=True),
        Binding("r", "reload_vault", "Reload (r)", show=True),
        Binding("d", "toggle_detail_mode", "Detail/Compact (d)", show=True),
        Binding("0", "set_depth_all", "Depth: All (0)", show=True),
        Binding("1", "set_depth_1", "Depth: 1 (1)", show=True),
        Binding("2", "set_depth_2", "Depth: 2 (2)", show=True),
        Binding("3", "set_depth_3", "Depth: 3 (3)", show=True),
        Binding("escape", "clear_or_unfocus", "Clear / Unfocus (Esc)", show=True),
        Binding("q", "quit", "Quit (q)", show=True),
    ]

    CHIP_CONFIGS = [
        ("All", "chip-all", "All"),
        ("Modules", "chip-modules", "Canonical Module"),
        ("Infra", "chip-infra", "Infrastructure"),
        ("AI", "chip-ai", "AI & Inference"),
        ("Biometrics", "chip-bio", "Biometrics & DSP"),
        ("Data", "chip-data", "Data & Memory"),
        ("Governance", "chip-gov", "Swarm & Governance"),
        ("Tooling", "chip-tool", "Tooling & Scripts"),
        ("Docs", "chip-docs", "Architecture & Docs"),
        ("Audit", "chip-audit", "Audit & Telemetry"),
    ]

    def __init__(
        self,
        vault_path: Optional[Path] = None,
        *args,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.vault_path = Path(vault_path) if vault_path else self._discover_vault_path()
        self.parser = ObsidianVaultParser(vault_path=self.vault_path)
        self.graph: ArchitectureGraph = ArchitectureGraph()
        self.renderer: Optional[GammaTopologyRenderer] = None
        self.ast_metrics: AstMetricsData = AstMetricsData.load_from_vault(self.vault_path)

        # Interactive State
        self.active_category: Optional[str] = None
        self.current_query: str = ""
        self.selected_node_id: Optional[str] = None
        self.active_chip_id: str = "chip-all"
        self.active_depth: Optional[int] = None
        self.active_layer: Optional[int] = None
        self.detailed_mode: bool = True
        self.sidebar_collapsed: bool = False

    def _discover_vault_path(self) -> Path:
        """Determines the default Obsidian vault path."""
        p = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault")
        if p.exists() and p.is_dir():
            return p
        cur = Path(__file__).resolve()
        repo_vault = cur.parents[3] / "obsidian_vault" if len(cur.parents) >= 4 else cur.parent / "obsidian_vault"
        if repo_vault.exists() and repo_vault.is_dir():
            return repo_vault
        return p

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="gamma-main-container"):
            # 1. LEFT SIDEBAR (25%)
            with Vertical(id="gamma-left-sidebar"):
                with Horizontal(id="gamma-sidebar-header"):
                    yield Static("🧠 KNOWLEDGE GRAPH", id="gamma-sidebar-title")
                    yield Button("◀", id="gamma-btn-toggle-sidebar", classes="control-btn")

                yield Input(
                    placeholder="Search architecture nodes, tags, features (/ to focus)...",
                    id="gamma-search-input"
                )

                with Vertical(id="gamma-category-container"):
                    with Horizontal(id="gamma-category-chips-row1", classes="chip-row"):
                        for label, chip_id, _ in self.CHIP_CONFIGS[0:3]:
                            classes = "gamma-chip active" if chip_id == "chip-all" else "gamma-chip"
                            yield Button(label, id=chip_id, classes=classes)
                    with Horizontal(id="gamma-category-chips-row2", classes="chip-row"):
                        for label, chip_id, _ in self.CHIP_CONFIGS[3:6]:
                            classes = "gamma-chip active" if chip_id == "chip-all" else "gamma-chip"
                            yield Button(label, id=chip_id, classes=classes)
                    with Horizontal(id="gamma-category-chips-row3", classes="chip-row"):
                        for label, chip_id, _ in self.CHIP_CONFIGS[6:9]:
                            classes = "gamma-chip active" if chip_id == "chip-all" else "gamma-chip"
                            yield Button(label, id=chip_id, classes=classes)
                    with Horizontal(id="gamma-category-chips-row4", classes="chip-row"):
                        for label, chip_id, _ in self.CHIP_CONFIGS[9:10]:
                            classes = "gamma-chip active" if chip_id == "chip-all" else "gamma-chip"
                            yield Button(label, id=chip_id, classes=classes)

                yield Tree[str]("🧠 Obsidian Knowledge Tree", id="gamma-tree")

            # 2. CENTER CANVAS (55%)
            with Vertical(id="gamma-center-canvas"):
                with Vertical(id="gamma-canvas-controls"):
                    with Horizontal(id="gamma-depth-controls"):
                        yield Static("Depth: ", classes="control-label")
                        yield Button("All", id="depth-all", classes="control-btn active")
                        yield Button("1", id="depth-1", classes="control-btn")
                        yield Button("2", id="depth-2", classes="control-btn")
                        yield Button("3", id="depth-3", classes="control-btn")
                        yield Button("Mode: Detailed", id="btn-toggle-mode", classes="control-btn")

                    with Horizontal(id="gamma-layer-controls"):
                        yield Static("Layer: ", classes="control-label")
                        yield Button("All", id="layer-all", classes="control-btn active")
                        yield Button("L0", id="layer-0", classes="control-btn")
                        yield Button("L1", id="layer-1", classes="control-btn")
                        yield Button("L2", id="layer-2", classes="control-btn")
                        yield Button("L3+", id="layer-3", classes="control-btn")

                with ScrollableContainer(id="gamma-canvas-scroll"):
                    yield Static(id="gamma-ascii-canvas")

            # 3. RIGHT INSPECTOR PANE (20%)
            with Vertical(id="gamma-right-inspector"):
                yield Static(id="gamma-ast-metrics-card")
                with ScrollableContainer(id="gamma-markdown-container"):
                    yield Markdown(id="gamma-markdown-detail")

        # 4. BOTTOM DOCK HUD
        yield Static(id="gamma-bottom-hud")
        yield Footer()

    def on_mount(self) -> None:
        """Initial load and render on mount."""
        self.reload_vault()

    def reload_vault(self) -> None:
        """Parses the vault, computes metrics, and synchronizes all widgets."""
        self.graph = self.parser.parse_vault()
        self.renderer = GammaTopologyRenderer(self.graph)
        self.ast_metrics = AstMetricsData.load_from_vault(self.vault_path)

        # Default initial node selection
        if "Index" in self.graph.nodes:
            self.selected_node_id = "Index"
        elif "00_core_infrastructure" in self.graph.nodes:
            self.selected_node_id = "00_core_infrastructure"
        elif self.graph.nodes:
            self.selected_node_id = next(iter(self.graph.nodes.keys()))

        self.apply_filter(category=self.active_category, query=self.current_query)

    def apply_filter(self, category: Optional[str] = None, query: str = "") -> None:
        """
        Filters graph nodes by category and query, synchronously updating
        the Tree, ASCII Canvas, Markdown Detail, AST Metrics, and Bottom HUD.
        """
        self.active_category = category
        self.current_query = query

        cat_filter = None if (category is None or category == "All") else category
        matching_nodes = self.graph.filter_nodes(category=cat_filter, query=query)
        matching_ids = set(node.id for node in matching_nodes)

        # 1. Update Tree Widget
        self._populate_tree(matching_nodes)

        # 2. Update Selected Node
        exact_match = next((n.id for n in matching_nodes if n.id.lower() == query.strip().lower()), None)
        if exact_match:
            self.selected_node_id = exact_match
        elif self.selected_node_id not in matching_ids and matching_nodes:
            self.selected_node_id = matching_nodes[0].id
        elif not matching_nodes:
            self.selected_node_id = None

        # 3. Synchronize Inspector & AST Card
        if self.selected_node_id:
            node = self.graph.get_node(self.selected_node_id)
            if node:
                self._render_node_detail(node)
                self._render_ast_card(node)
        else:
            self._render_empty_detail()
            self._render_ast_card(None)

        # 4. Update Topology Canvas
        self._render_canvas(matching_ids)

        # 5. Update Bottom Dock HUD
        self._render_bottom_hud(len(matching_nodes))

    def select_node(self, node_id: str, update_canvas: bool = True) -> None:
        """
        Selects an individual node, updating Markdown detail, AST Card, and Canvas highlight.
        """
        self.selected_node_id = node_id
        node = self.graph.get_node(node_id)
        if not node:
            return

        self._render_node_detail(node)
        self._render_ast_card(node)

        if update_canvas:
            cat_filter = None if (self.active_category is None or self.active_category == "All") else self.active_category
            matching = self.graph.filter_nodes(category=cat_filter, query=self.current_query)
            matching_ids = set(n.id for n in matching)
            self._render_canvas(matching_ids)
            self._render_bottom_hud(len(matching))

    # =========================================================================
    # WIDGET RENDERING HELPERS
    # =========================================================================

    def _populate_tree(self, nodes: List[VaultNode]) -> None:
        """Populates the hierarchical knowledge tree grouped by category."""
        try:
            tree = self.query_one("#gamma-tree", Tree)
            if not tree:
                return

            tree.clear()
            tree.root.expand()

            by_category: Dict[str, List[VaultNode]] = {}
            for node in nodes:
                cat = node.category or "Uncategorized"
                by_category.setdefault(cat, []).append(node)

            for cat_name, cat_nodes in sorted(by_category.items()):
                icon = GammaTopologyRenderer.CATEGORY_ICONS.get(cat_name, "📁")
                color = GammaTopologyRenderer.CATEGORY_COLORS.get(cat_name, "#94a3b8")
                cat_branch = tree.root.add(
                    f"[{color}]{icon} {cat_name} ({len(cat_nodes)})[/{color}]",
                    data=None,
                    expand=True
                )

                for node in sorted(cat_nodes, key=lambda n: n.id):
                    is_sel = (node.id == self.selected_node_id)
                    prefix = "▶ " if is_sel else ""
                    node_label = f"[bold #00ffcc]{prefix}{node.id}[/bold #00ffcc]" if is_sel else f"[{color}]{node.id}[/{color}]"
                    node_leaf = cat_branch.add(
                        f"{node_label} [dim](in:{node.in_degree} out:{node.out_degree})[/dim]",
                        data=node.id
                    )

                    for out_link in node.out_links[:3]:
                        node_leaf.add_leaf(f"[dim]──▶ {out_link.target_id}[/dim]", data=out_link.target_id)
                    if len(node.out_links) > 3:
                        node_leaf.add_leaf(f"[dim]    (+{len(node.out_links) - 3} more links)[/dim]", data=None)

        except Exception:
            pass

    def _render_canvas(self, matching_ids: Set[str]) -> None:
        """Renders the Sugiyama layered ASCII topology canvas."""
        try:
            canvas = self.query_one("#gamma-ascii-canvas", Static)
            if not canvas or not self.renderer:
                return

            rendered_text = self.renderer.render_canvas(
                filtered_nodes=matching_ids,
                selected_node=self.selected_node_id,
                depth_limit=self.active_depth,
                layer_isolation=self.active_layer,
                detailed_mode=self.detailed_mode,
            )
            canvas.update(Text.from_markup(rendered_text))
        except Exception:
            pass

    def _render_node_detail(self, node: VaultNode) -> None:
        """Renders the Markdown document inspector with frontmatter, links, and features."""
        try:
            md_widget = self.query_one("#gamma-markdown-detail", Markdown)
            if not md_widget:
                return

            icon = GammaTopologyRenderer.CATEGORY_ICONS.get(node.category, "📄")
            tags_str = " ".join(f"`#{t}`" for t in node.tags) if node.tags else "_none_"
            updated_str = node.updated if node.updated else "_not recorded_"

            md_lines: List[str] = [
                f"# {icon} {node.id}",
                f"**Title:** {node.title}  ",
                f"**Category:** `{node.category}`  ",
                f"**Tags:** {tags_str}  ",
                f"**Updated:** {updated_str}  ",
                f"**File:** `{node.file_path.name}`  ",
                f"**Degree:** Inbound: `{node.in_degree}` | Outbound: `{node.out_degree}`  ",
                "",
                "---",
                "",
                "### 🔗 Outbound Links (Dependencies)",
            ]

            if node.out_links:
                for link in node.out_links:
                    alias_info = f" (as `{link.alias}`)" if link.alias else ""
                    anchor_info = f" `#{link.anchor}`" if link.anchor else ""
                    md_lines.append(f"- `[[{link.target_id}]]`{anchor_info}{alias_info}")
            else:
                md_lines.append("_No outbound links._")

            md_lines.extend([
                "",
                "### 📥 Inbound Backlinks (Dependents)",
            ])

            if node.in_links:
                for in_src in sorted(node.in_links):
                    md_lines.append(f"- `[[{in_src}]]`")
            else:
                md_lines.append("_No inbound backlinks._")

            md_lines.extend([
                "",
                "### 📋 Architectural Features & Subsystems",
            ])

            if node.features:
                for feat in node.features:
                    sec_info = f" _(Section: {feat.section})_" if feat.section else ""
                    desc_info = f": {feat.description}" if feat.description else ""
                    md_lines.append(f"- **{feat.name}**{sec_info}{desc_info}")
            else:
                md_lines.append("_No structured features extracted._")

            md_widget.update("\n".join(md_lines))
        except Exception:
            pass

    def _render_empty_detail(self) -> None:
        """Renders placeholder detail when no node is selected."""
        try:
            md_widget = self.query_one("#gamma-markdown-detail", Markdown)
            if md_widget:
                md_widget.update(
                    "# 🔍 No Node Selected\n\n"
                    "Select an architecture document from the tree or search query."
                )
        except Exception:
            pass

    def _render_ast_card(self, node: Optional[VaultNode]) -> None:
        """Renders Code AST Metrics Card (PySpark LOC count, files, languages)."""
        try:
            ast_card = self.query_one("#gamma-ast-metrics-card", Static)
            if not ast_card:
                return

            table = Table(expand=True, box=None, show_header=False, padding=(0, 0))
            table.add_column("Metric", ratio=6)
            table.add_column("Value", ratio=4, justify="right")

            # Global Monorepo AST Stats
            table.add_row(
                Text.assemble(("⚡ Monorepo Total LOC: ", "dim")),
                Text(f"{self.ast_metrics.total_loc:,}", style="bold #00ffcc")
            )
            table.add_row(
                Text.assemble(("📁 Total Code Files: ", "dim")),
                Text(f"{self.ast_metrics.total_files:,}", style="bold cyan")
            )
            table.add_row(
                Text.assemble(("🧪 Total Test Files: ", "dim")),
                Text(f"{self.ast_metrics.total_tests:,}", style="bold green")
            )
            table.add_row(
                Text.assemble(("📦 Monorepo Projects: ", "dim")),
                Text(f"{self.ast_metrics.total_projects}", style="bold magenta")
            )

            # Node-specific AST stats if matching
            if node and node.id in self.ast_metrics.project_loc_map:
                proj_data = self.ast_metrics.project_loc_map[node.id]
                table.add_row(Text("─" * 28, style="dim #334155"), Text("─" * 10, style="dim #334155"))
                table.add_row(
                    Text.assemble(("🎯 Node Target: ", "dim")),
                    Text(node.id[:14], style="bold yellow")
                )
                table.add_row(
                    Text.assemble(("  • Subsystem LOC: ", "dim")),
                    Text(f"{proj_data['loc']:,}", style="bold yellow")
                )
                table.add_row(
                    Text.assemble(("  • Code Files: ", "dim")),
                    Text(str(proj_data["files"]), style="bold white")
                )
                table.add_row(
                    Text.assemble(("  • Languages: ", "dim")),
                    Text(proj_data["langs"], style="dim cyan")
                )

            ast_card.update(
                Panel(table, title="[bold #00ffcc]📊 CODE AST METRICS[/bold #00ffcc]", border_style="#00ffcc")
            )
        except Exception:
            pass

    def _render_bottom_hud(self, matching_count: int) -> None:
        """Renders the comprehensive Bottom Dock Graph Metrics HUD."""
        try:
            hud = self.query_one("#gamma-bottom-hud", Static)
            if not hud:
                return

            metrics = self.graph.get_metrics()
            cycles = self.graph.find_cycles()

            table = Table(expand=True, box=None, show_header=False, padding=(0, 1))
            table.add_column("Col1", ratio=3)
            table.add_column("Col2", ratio=3)
            table.add_column("Col3", ratio=3)
            table.add_column("Col4", ratio=3)

            depth_str = str(self.active_depth) if self.active_depth else "All"
            layer_str = f"L{self.active_layer}" if self.active_layer is not None else "All"

            table.add_row(
                Text.assemble(("📚 Total Nodes: ", "dim"), (str(metrics["total_nodes"]), "bold cyan")),
                Text.assemble(("🔍 Matches: ", "dim"), (str(matching_count), "bold green")),
                Text.assemble(("🔗 Edges: ", "dim"), (str(metrics["total_edges"]), "bold yellow")),
                Text.assemble(("🏷️ Categories: ", "dim"), (str(metrics["categories_count"]), "bold magenta")),
            )
            table.add_row(
                Text.assemble(("⚡ Graph Density: ", "dim"), (str(metrics["density"]), "bold green")),
                Text.assemble(("↺ Tarjan SCC: ", "dim"), (str(len(cycles)), "bold red" if cycles else "bold green")),
                Text.assemble(("❓ Dangling Links: ", "dim"), (str(metrics["dangling_links_count"]), "bold yellow")),
                Text.assemble(("🔀 Avg Degree: ", "dim"), (str(metrics["avg_degree"]), "bold cyan")),
            )

            title_str = (
                f"[bold cyan]🏛️ GRAPH TOPOLOGY METRICS HUD[/bold cyan] │ "
                f"[dim]Depth: {depth_str} • Layer: {layer_str} • Category: {self.active_category or 'All'}[/dim]"
            )
            hud.update(Panel(table, title=title_str, border_style="#00ffcc"))
        except Exception:
            pass

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle real-time search input changes."""
        if event.input.id == "gamma-search-input":
            self.apply_filter(category=self.active_category, query=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submit."""
        if event.input.id == "gamma-search-input":
            self.apply_filter(category=self.active_category, query=event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle category chips, depth selectors, layer isolation, and sidebar toggle buttons."""
        btn_id = event.button.id
        if not btn_id:
            return

        # 1. Sidebar Toggle Button
        if btn_id == "gamma-btn-toggle-sidebar":
            self.action_toggle_sidebar()
            return

        # 2. Category Chips
        matched_chip = next((cfg for cfg in self.CHIP_CONFIGS if cfg[1] == btn_id), None)
        if matched_chip:
            label, chip_id, cat_name = matched_chip
            self.active_chip_id = chip_id

            # Update CSS active class on chips
            for _, c_id, _ in self.CHIP_CONFIGS:
                try:
                    chip_btn = self.query_one(f"#{c_id}", Button)
                    if chip_btn:
                        if c_id == chip_id:
                            chip_btn.add_class("active")
                        else:
                            chip_btn.remove_class("active")
                except Exception:
                    pass

            target_cat = None if cat_name == "All" else cat_name
            self.apply_filter(category=target_cat, query=self.current_query)
            return

        # 3. Depth Buttons
        if btn_id.startswith("depth-"):
            depth_map = {"depth-all": None, "depth-1": 1, "depth-2": 2, "depth-3": 3}
            self.active_depth = depth_map.get(btn_id, None)
            for d_id in ["depth-all", "depth-1", "depth-2", "depth-3"]:
                try:
                    d_btn = self.query_one(f"#{d_id}", Button)
                    if d_btn:
                        if d_id == btn_id:
                            d_btn.add_class("active")
                        else:
                            d_btn.remove_class("active")
                except Exception:
                    pass
            self.apply_filter(category=self.active_category, query=self.current_query)
            return

        # 4. Layer Isolation Buttons
        if btn_id.startswith("layer-"):
            layer_map = {"layer-all": None, "layer-0": 0, "layer-1": 1, "layer-2": 2, "layer-3": 3}
            self.active_layer = layer_map.get(btn_id, None)
            for l_id in ["layer-all", "layer-0", "layer-1", "layer-2", "layer-3"]:
                try:
                    l_btn = self.query_one(f"#{l_id}", Button)
                    if l_btn:
                        if l_id == btn_id:
                            l_btn.add_class("active")
                        else:
                            l_btn.remove_class("active")
                except Exception:
                    pass
            self.apply_filter(category=self.active_category, query=self.current_query)
            return

        # 5. Detail / Compact Mode Toggle
        if btn_id == "btn-toggle-mode":
            self.action_toggle_detail_mode()
            return

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node_id = event.node.data
        if node_id and isinstance(node_id, str):
            self.select_node(node_id)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Handle tree cursor movement."""
        node_id = event.node.data
        if node_id and isinstance(node_id, str):
            self.select_node(node_id)

    # =========================================================================
    # ACTIONS
    # =========================================================================

    def action_focus_search(self) -> None:
        """Action for '/' shortcut: focuses search input."""
        try:
            inp = self.query_one("#gamma-search-input", Input)
            if inp:
                inp.focus()
        except Exception:
            pass

    def action_toggle_sidebar(self) -> None:
        """Action for 'b' shortcut: toggles left sidebar collapsed/expanded."""
        try:
            sidebar = self.query_one("#gamma-left-sidebar", Vertical)
            canvas = self.query_one("#gamma-center-canvas", Vertical)
            toggle_btn = self.query_one("#gamma-btn-toggle-sidebar", Button)

            self.sidebar_collapsed = not self.sidebar_collapsed
            if self.sidebar_collapsed:
                sidebar.add_class("collapsed")
                canvas.add_class("expanded")
                if toggle_btn:
                    toggle_btn.label = "▶"
            else:
                sidebar.remove_class("collapsed")
                canvas.remove_class("expanded")
                if toggle_btn:
                    toggle_btn.label = "◀"
        except Exception:
            pass

    def action_toggle_detail_mode(self) -> None:
        """Action for 'd' shortcut: toggles canvas detail / compact rendering."""
        self.detailed_mode = not self.detailed_mode
        try:
            btn = self.query_one("#btn-toggle-mode", Button)
            if btn:
                btn.label = f"Mode: {'Detailed' if self.detailed_mode else 'Compact'}"
        except Exception:
            pass
        self.apply_filter(category=self.active_category, query=self.current_query)

    def action_reload_vault(self) -> None:
        """Action for 'r' shortcut: reloads vault."""
        self.reload_vault()

    def action_set_depth_all(self) -> None:
        self.active_depth = None
        self._update_depth_btn_classes("depth-all")
        self.apply_filter(category=self.active_category, query=self.current_query)

    def action_set_depth_1(self) -> None:
        self.active_depth = 1
        self._update_depth_btn_classes("depth-1")
        self.apply_filter(category=self.active_category, query=self.current_query)

    def action_set_depth_2(self) -> None:
        self.active_depth = 2
        self._update_depth_btn_classes("depth-2")
        self.apply_filter(category=self.active_category, query=self.current_query)

    def action_set_depth_3(self) -> None:
        self.active_depth = 3
        self._update_depth_btn_classes("depth-3")
        self.apply_filter(category=self.active_category, query=self.current_query)

    def _update_depth_btn_classes(self, active_id: str) -> None:
        for d_id in ["depth-all", "depth-1", "depth-2", "depth-3"]:
            try:
                btn = self.query_one(f"#{d_id}", Button)
                if btn:
                    if d_id == active_id:
                        btn.add_class("active")
                    else:
                        btn.remove_class("active")
            except Exception:
                pass

    def action_clear_or_unfocus(self) -> None:
        """Action for 'escape' shortcut: clears search or unfocuses."""
        try:
            inp = self.query_one("#gamma-search-input", Input)
            if inp and inp.has_focus:
                inp.value = ""
                tree = self.query_one("#gamma-tree", Tree)
                if tree:
                    tree.focus()
            else:
                self.apply_filter(category=None, query="")
        except Exception:
            pass


if __name__ == "__main__":
    app = TuiGammaGraphApp()
    app.run()
