"""
Canonical Port TUI - ASCII / ANSI Architecture Graph Renderer
Version: 1.0.0-CANONICAL
Deterministic ASCII/ANSI graph layout and rendering engine:
- Tarjan SCC cycle isolation and bidirectional dependency annotation.
- Sugiyama layered layout stratification with barycentric crossing reduction.
- Unicode box-drawing connectors (╭─╮, ──▶, ├──┴──▶, ╰──▶) with diamond bus convergence.
- Rich ANSI category color styling and interactive selection highlighting.
"""

from typing import Dict, List, Optional, Set, Tuple
from rich.text import Text

try:
    from models.architecture_graph import ArchitectureGraph, VaultNode
except ImportError:
    from tui.models.architecture_graph import ArchitectureGraph, VaultNode


class AsciiGraphRenderer:
    """
    Renders an in-memory ArchitectureGraph to deterministic, highly readable ASCII/ANSI text.
    """

    # Category palette mapping
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

    def detect_cycles(self, node_ids: Optional[Set[str]] = None) -> List[Tuple[str, str]]:
        """
        Returns list of directed edge pairs (u, v) that form cycle components.
        """
        active = node_ids if node_ids is not None else set(self.graph.nodes.keys())
        cycles = self.graph.find_cycles(node_subset=active)
        cycle_edges: List[Tuple[str, str]] = []
        for cyc in cycles:
            cyc_set = set(cyc)
            for u in cyc:
                for v in self.graph.get_out_edges(u):
                    if v in cyc_set:
                        cycle_edges.append((u, v))
        return cycle_edges

    def render_ansi(
        self,
        filtered_nodes: Optional[Set[str]] = None,
        selected_node: Optional[str] = None,
        max_width: int = 120
    ) -> str:
        """
        Renders the architecture graph with layered stratification, box-drawing, and ANSI markup.
        """
        active_nodes = filtered_nodes if filtered_nodes is not None else set(self.graph.nodes.keys())
        active_nodes = active_nodes & set(self.graph.nodes.keys())

        if not active_nodes:
            return (
                "\n\n[bold yellow]  ┌──────────────────────────────────────────────────────────┐[/bold yellow]\n"
                "[bold yellow]  │               NO MATCHING ARCHITECTURE NODES             │[/bold yellow]\n"
                "[bold yellow]  │  Adjust category chips or clear search query to inspect  │[/bold yellow]\n"
                "[bold yellow]  └──────────────────────────────────────────────────────────┘[/bold yellow]\n"
            )

        layers = self.graph.get_stratified_layers(node_subset=active_nodes)
        if not layers:
            layers = [sorted(list(active_nodes))]

        # Barycentric Crossing Reduction Pass
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

        cycles = self.graph.find_cycles(node_subset=active_nodes)
        cycle_node_set = set(nid for cyc in cycles for nid in cyc)

        lines: List[str] = []

        # Graph Header HUD
        total_sub_nodes = len(active_nodes)
        total_sub_edges = len([
            (s, d) for s, d in self.graph.edges if s in active_nodes and d in active_nodes
        ])
        cycle_count = len(cycles)

        lines.append(
            f"[bold #00ffff]╔══════════════════════════════════════════════════════════════════════════════════════════════╗[/bold #00ffff]"
        )
        lines.append(
            f"[bold #00ffff]║[/bold #00ffff] [bold white]OBSIDIAN ARCHITECTURE TOPOLOGY CANVAS[/bold white] │ "
            f"[cyan]Nodes:[/cyan] [bold green]{total_sub_nodes}[/bold green] │ "
            f"[cyan]Edges:[/cyan] [bold yellow]{total_sub_edges}[/bold yellow] │ "
            f"[cyan]Layers:[/cyan] [bold magenta]{len(ordered_layers)}[/bold magenta] │ "
            f"[cyan]SCC Cycles:[/cyan] [{'bold red' if cycle_count > 0 else 'bold green'}]{cycle_count}[/{'bold red' if cycle_count > 0 else 'bold green'}] "
            f"[bold #00ffff]║[/bold #00ffff]"
        )
        lines.append(
            f"[bold #00ffff]╚══════════════════════════════════════════════════════════════════════════════════════════════╝[/bold #00ffff]\n"
        )

        # Render Layers
        for layer_idx, layer_nodes in enumerate(ordered_layers):
            layer_title = f" LAYER {layer_idx:02d} ({len(layer_nodes)} node{'s' if len(layer_nodes) != 1 else ''}) "
            bar_len = max(4, 88 - len(layer_title))
            left_bar = "─" * 4
            right_bar = "─" * bar_len
            lines.append(f"[dim #334155]──{left_bar}[/dim #334155][bold cyan]{layer_title}[/bold cyan][dim #334155]{right_bar}──[/dim #334155]")

            for node_id in layer_nodes:
                node = self.graph.get_node(node_id)
                if not node:
                    continue

                is_selected = (node_id == selected_node)
                is_cyclic = (node_id in cycle_node_set)
                color = self.CATEGORY_COLORS.get(node.category, "#94a3b8")
                icon = self.CATEGORY_ICONS.get(node.category, "📄")

                # Node Box Header & Content
                title_clean = (node.title[:45] + "...") if len(node.title) > 48 else node.title
                cycle_badge = " [bold red]↺ SCC[/bold red]" if is_cyclic else ""
                select_badge = " [bold black on #00ffcc] ★ SELECTED [/bold black on #00ffcc]" if is_selected else ""

                border_style = f"bold {color}" if not is_selected else "bold #00ffcc on #0f172a"
                box_bg = "on #1e293b" if is_selected else ""

                box_width = 80
                top_border = "╭" + ("─" * (box_width - 2)) + "╮"
                bot_border = "╰" + ("─" * (box_width - 2)) + "╯"

                lines.append(f"[{border_style}]  {top_border}[/{border_style}]")
                lines.append(
                    f"[{border_style}]  │[/{border_style}] {icon} [{border_style}][bold]{node.id}[/bold][/{border_style}]{cycle_badge}{select_badge}"
                    f" [{'dim ' + color}]({node.category})[/{'dim ' + color}]"
                )
                if node.title and node.title != node.id:
                    lines.append(f"[{border_style}]  │[/{border_style}]   [dim]Title:[/dim] [white]{title_clean}[/white]")

                tags_str = ", ".join(node.tags[:4]) if node.tags else "none"
                lines.append(
                    f"[{border_style}]  │[/{border_style}]   [dim]In:[/dim] [green]{node.in_degree}[/green] [dim]│ Out:[/dim] [yellow]{node.out_degree}[/yellow] "
                    f"[dim]│ Feats:[/dim] [cyan]{len(node.features)}[/cyan] [dim]│ Tags:[/dim] [dim]{tags_str}[/dim]"
                )

                # Show outgoing targets inside active subset
                active_out = [dst for dst in self.graph.get_out_edges(node_id) if dst in active_nodes]
                if active_out:
                    out_preview = ", ".join(active_out[:3])
                    if len(active_out) > 3:
                        out_preview += f" (+{len(active_out)-3} more)"
                    lines.append(f"[{border_style}]  │[/{border_style}]   [bold yellow]──▶ Outflows:[/bold yellow] [dim cyan]{out_preview}[/dim cyan]")

                lines.append(f"[{border_style}]  {bot_border}[/{border_style}]")

            # Layer Connector Flow
            if layer_idx < len(ordered_layers) - 1:
                next_layer_nodes = ordered_layers[layer_idx + 1]
                edge_count_between = sum(
                    1 for u in layer_nodes for v in self.graph.get_out_edges(u) if v in next_layer_nodes
                )
                if edge_count_between > 0:
                    lines.append(f"        [bold #38bdf8]│      ├──┴──▶ ({edge_count_between} downstream links)[/bold #38bdf8]")
                    lines.append(f"        [bold #38bdf8]▼[/bold #38bdf8]")
                else:
                    lines.append(f"        [dim]│[/dim]")
                    lines.append(f"        [dim]▼[/dim]")

        # Cyclic Components Summary
        if cycles:
            lines.append("\n[bold red]╔══════════════════════════════════════════════════════════════════════════════════════════════╗[/bold red]")
            lines.append("[bold red]║ ↺ STRONGLY CONNECTED CYCLES (TARJAN SCC ISOLATED)                                            ║[/bold red]")
            lines.append("[bold red]╠══════════════════════════════════════════════════════════════════════════════════════════════╣[/bold red]")
            for idx, cyc in enumerate(cycles[:5], 1):
                cyc_str = " ⇄ ".join(cyc[:6])
                if len(cyc) > 6:
                    cyc_str += f" ⇄ ... ({len(cyc)} nodes)"
                lines.append(f"[bold red]║[/bold red] [yellow]Cycle #{idx}:[/yellow] [white]{cyc_str}[/white]")
            lines.append("[bold red]╚══════════════════════════════════════════════════════════════════════════════════════════════╝[/bold red]")

        return "\n".join(lines)

    def render_tree_ascii(self, root_id: str, max_depth: int = 3) -> str:
        """
        Renders a hierarchical ASCII tree starting from root_id up to max_depth.
        """
        root_node = self.graph.get_node(root_id)
        if not root_node:
            return f"[red]Node '{root_id}' not found.[/red]"

        lines: List[str] = [f"[bold #00ffcc]📦 {root_node.id}[/bold #00ffcc] [dim]({root_node.category})[/dim]"]
        visited: Set[str] = {root_id}

        def build_branch(node_id: str, prefix: str, depth: int) -> None:
            if depth >= max_depth:
                return

            out_edges = [dst for dst in self.graph.get_out_edges(node_id) if dst in self.graph.nodes]
            for i, target_id in enumerate(out_edges):
                is_last = (i == len(out_edges) - 1)
                connector = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                target_node = self.graph.get_node(target_id)
                cat_col = self.CATEGORY_COLORS.get(target_node.category if target_node else "", "#94a3b8")
                
                is_cycle = target_id in visited
                cycle_tag = " [bold red]↺[/bold red]" if is_cycle else ""
                lines.append(f"{prefix}{connector}[{cat_col}]{target_id}[/{cat_col}]{cycle_tag}")

                if not is_cycle:
                    visited.add(target_id)
                    build_branch(target_id, next_prefix, depth + 1)

        build_branch(root_id, "", 0)
        return "\n".join(lines)
