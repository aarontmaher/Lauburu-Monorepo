"""
Canonical Port TUI - Architecture Explorer View
Version: 1.0.0-CANONICAL
Responsive dual-layout Textual container for Obsidian Architecture Explorer:
- Left Pane (48% width): Search Input, Category Chip toggles, interactive Tree widget, and Markdown detail pane.
- Right Pane (52% width): Header metrics HUD and scrollable ASCII/ANSI graph canvas.
- Dynamic filtering engine that synchronizes both the Tree and ASCII canvas in real time.
- Node selection synchronization (tree selection highlights ASCII node and updates Markdown detail).
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Static,
    Input,
    Button,
    Tree,
    Markdown,
)
from textual.widget import Widget
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from models.architecture_graph import ArchitectureGraph, VaultNode
    from services.obsidian_vault_parser import ObsidianVaultParser
    from services.ascii_graph_renderer import AsciiGraphRenderer
except ImportError:
    from tui.models.architecture_graph import ArchitectureGraph, VaultNode
    from tui.services.obsidian_vault_parser import ObsidianVaultParser
    from tui.services.ascii_graph_renderer import AsciiGraphRenderer


class ArchitectureExplorerView(Vertical):
    """
    Dual-layout interactive visualizer for the Obsidian Knowledge Vault.
    """

    DEFAULT_CSS = """
    ArchitectureExplorerView {
        height: 1fr;
        width: 100%;
        background: #070b12;
    }

    #explorer-split-container {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }

    #explorer-left-pane {
        width: 48%;
        height: 1fr;
        border-right: solid #1e293b;
        padding: 0 1;
    }

    #explorer-right-pane {
        width: 52%;
        height: 1fr;
        padding: 0 1;
    }

    #explorer-search-input {
        height: 3;
        margin-bottom: 1;
        border: solid #00ffcc;
        background: #0b111c;
        color: #e2e8f0;
    }

    #explorer-category-chips {
        height: auto;
        margin-bottom: 1;
        layout: horizontal;
    }

    .category-chip {
        min-width: 6;
        height: 1;
        margin-right: 1;
        margin-bottom: 1;
        padding: 0 1;
        border: none;
    }

    #explorer-tree {
        height: 14;
        border: solid #334155;
        background: #0b111c;
        margin-bottom: 1;
    }

    #explorer-detail-container {
        height: 1fr;
        border: solid #1e293b;
        background: #0b111c;
        padding: 1;
    }

    #explorer-metrics-hud {
        height: auto;
        margin-bottom: 1;
    }

    #explorer-ascii-container {
        height: 1fr;
        border: solid #1e293b;
        background: #070b12;
        padding: 0 1;
    }
    """

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
        self.parser = ObsidianVaultParser(vault_path=vault_path)
        self.graph: ArchitectureGraph = ArchitectureGraph()
        self.renderer: Optional[AsciiGraphRenderer] = None
        self.active_category: Optional[str] = None
        self.current_query: str = ""
        self.selected_node_id: Optional[str] = None
        self.active_chip_id: str = "chip-all"

    def compose(self) -> ComposeResult:
        with Horizontal(id="explorer-split-container"):
            # LEFT PANE
            with Vertical(id="explorer-left-pane"):
                yield Input(
                    placeholder="Search architecture nodes, tags, features (/ to focus)...",
                    id="explorer-search-input"
                )
                with Horizontal(id="explorer-category-chips"):
                    for label, chip_id, _ in self.CHIP_CONFIGS:
                        variant = "primary" if chip_id == "chip-all" else "default"
                        yield Button(label, id=chip_id, classes="category-chip", variant=variant)

                yield Tree[str]("🧠 Obsidian Knowledge Graph", id="explorer-tree")

                with ScrollableContainer(id="explorer-detail-container"):
                    yield Markdown(id="explorer-markdown-detail")

            # RIGHT PANE
            with Vertical(id="explorer-right-pane"):
                yield Static(id="explorer-metrics-hud")
                with ScrollableContainer(id="explorer-ascii-container"):
                    yield Static(id="explorer-ascii-canvas")

    def on_mount(self) -> None:
        """Initial load and render on mount."""
        self.reload_vault()
        # Focus Tree by default so navigation keybindings work until '/' is pressed
        try:
            tree = self.query_one("#explorer-tree", Tree)
            if tree:
                tree.focus()
        except Exception:
            pass

    def reload_vault(self) -> None:
        """Parses the vault and refreshes all views."""
        self.graph = self.parser.parse_vault()
        self.renderer = AsciiGraphRenderer(self.graph)

        # Select initial default node
        if "Index" in self.graph.nodes:
            self.selected_node_id = "Index"
        elif "00_core_infrastructure" in self.graph.nodes:
            self.selected_node_id = "00_core_infrastructure"
        elif self.graph.nodes:
            self.selected_node_id = next(iter(self.graph.nodes.keys()))

        self.apply_filter(category=self.active_category, query=self.current_query)

    def apply_filter(self, category: Optional[str] = None, query: str = "") -> None:
        """
        Filters graph nodes and synchronously updates Tree, ASCII canvas, and Metrics HUD.
        """
        self.active_category = category
        self.current_query = query

        cat_filter = None if (category is None or category == "All") else category
        matching_nodes = self.graph.filter_nodes(category=cat_filter, query=query)
        matching_ids = set(node.id for node in matching_nodes)

        # 1. Update Metrics HUD
        self._render_metrics_hud(len(matching_nodes))

        # 2. Update Tree
        self._populate_tree(matching_nodes)

        # 3. Update Selected Node & Markdown Detail
        exact_match = next((n.id for n in matching_nodes if n.id.lower() == query.strip().lower()), None)
        if exact_match:
            self.selected_node_id = exact_match
        elif self.selected_node_id not in matching_ids and matching_nodes:
            self.selected_node_id = matching_nodes[0].id
        elif not matching_nodes:
            self.selected_node_id = None

        if self.selected_node_id:
            self.select_node(self.selected_node_id, update_canvas=False)
        else:
            self._render_empty_detail()


        # 4. Update ASCII Canvas
        self._render_ascii_canvas(matching_ids)

    def select_node(self, node_id: str, update_canvas: bool = True) -> None:
        """
        Selects an architecture node, updating the Markdown detail pane and highlighting in ASCII canvas.
        """
        self.selected_node_id = node_id
        node = self.graph.get_node(node_id)
        if not node:
            return

        # Update Markdown Detail Pane
        self._render_node_detail(node)

        # Update ASCII Canvas with selected node highlight
        if update_canvas:
            cat_filter = None if (self.active_category is None or self.active_category == "All") else self.active_category
            matching = self.graph.filter_nodes(category=cat_filter, query=self.current_query)
            matching_ids = set(n.id for n in matching)
            self._render_ascii_canvas(matching_ids)

    def _render_metrics_hud(self, matching_count: int) -> None:
        try:
            hud = self.query_one("#explorer-metrics-hud", Static)
            if not hud:
                return

            metrics = self.graph.get_metrics()
            table = Table(expand=True, box=None, show_header=False, padding=(0, 1))
            table.add_column("Col1", ratio=3)
            table.add_column("Col2", ratio=3)
            table.add_column("Col3", ratio=3)
            table.add_column("Col4", ratio=2)

            table.add_row(
                Text.assemble(("📚 Total Vault Nodes: ", "dim"), (str(metrics["total_nodes"]), "bold cyan")),
                Text.assemble(("🔍 Active Matches: ", "dim"), (str(matching_count), "bold green")),
                Text.assemble(("🔗 Total Directed Edges: ", "dim"), (str(metrics["total_edges"]), "bold yellow")),
                Text.assemble(("🏷️ Categories: ", "dim"), (str(metrics["categories_count"]), "bold magenta")),
            )
            table.add_row(
                Text.assemble(("⚡ Density: ", "dim"), (str(metrics["density"]), "bold green")),
                Text.assemble(("↺ SCC Cycles: ", "dim"), (str(metrics["cycles_count"]), "bold red" if metrics["cycles_count"] > 0 else "bold green")),
                Text.assemble(("❓ Dangling Links: ", "dim"), (str(metrics["dangling_links_count"]), "bold yellow")),
                Text.assemble(("🔀 Avg Degree: ", "dim"), (str(metrics["avg_degree"]), "bold cyan")),
            )

            hud.update(Panel(table, title="[bold cyan]🏛️ OBSIDIAN ARCHITECTURE KNOWLEDGE GRAPH HUD[/bold cyan]", border_style="cyan"))
        except Exception:
            pass

    def _populate_tree(self, nodes: List[VaultNode]) -> None:
        try:
            tree = self.query_one("#explorer-tree", Tree)
            if not tree:
                return

            tree.clear()
            tree.root.expand()

            # Group nodes by category
            by_category: Dict[str, List[VaultNode]] = {}
            for node in nodes:
                cat = node.category or "Uncategorized"
                by_category.setdefault(cat, []).append(node)

            for cat_name, cat_nodes in sorted(by_category.items()):
                icon = AsciiGraphRenderer.CATEGORY_ICONS.get(cat_name, "📁")
                color = AsciiGraphRenderer.CATEGORY_COLORS.get(cat_name, "#94a3b8")
                cat_branch = tree.root.add(
                    f"[{color}]{icon} {cat_name} ({len(cat_nodes)})[/{color}]",
                    data=None,
                    expand=True
                )

                for node in sorted(cat_nodes, key=lambda n: n.id):
                    node_label = f"[{color}]{node.id}[/{color}]"
                    if node.id == self.selected_node_id:
                        node_label = f"[bold #00ffcc]▶ {node.id}[/bold #00ffcc]"
                    
                    node_leaf = cat_branch.add(node_label, data=node.id)

                    # Add outgoing dependency sub-leaves
                    for out_link in node.out_links[:4]:
                        node_leaf.add_leaf(f"[dim]──▶ {out_link.target_id}[/dim]", data=out_link.target_id)
                    if len(node.out_links) > 4:
                        node_leaf.add_leaf(f"[dim]    (+{len(node.out_links) - 4} more links)[/dim]", data=None)

        except Exception:
            pass

    def _render_node_detail(self, node: VaultNode) -> None:
        try:
            md_widget = self.query_one("#explorer-markdown-detail", Markdown)
            if not md_widget:
                return

            icon = AsciiGraphRenderer.CATEGORY_ICONS.get(node.category, "📄")
            tags_str = " ".join(f"`#{t}`" for t in node.tags) if node.tags else "_none_"
            updated_str = node.updated if node.updated else "_not recorded_"

            md_lines: List[str] = [
                f"# {icon} {node.id}",
                f"**Title:** {node.title}  ",
                f"**Category:** `{node.category}`  ",
                f"**Tags:** {tags_str}  ",
                f"**Updated:** {updated_str}  ",
                f"**Path:** `{node.file_path.name}`  ",
                f"**Degree:** In: `{node.in_degree}` | Out: `{node.out_degree}`  ",
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
        try:
            md_widget = self.query_one("#explorer-markdown-detail", Markdown)
            if md_widget:
                md_widget.update(
                    "# 🔍 No Node Selected\n\n"
                    "Select a node from the tree or adjust your filter query."
                )
        except Exception:
            pass

    def _render_ascii_canvas(self, matching_ids: Set[str]) -> None:
        try:
            canvas = self.query_one("#explorer-ascii-canvas", Static)
            if not canvas or not self.renderer:
                return

            rendered_text = self.renderer.render_ansi(
                filtered_nodes=matching_ids,
                selected_node=self.selected_node_id
            )
            canvas.update(Text.from_markup(rendered_text))
        except Exception:
            pass

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle dynamic search input typing."""
        if event.input.id == "explorer-search-input":
            self.apply_filter(category=self.active_category, query=event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submit."""
        if event.input.id == "explorer-search-input":
            self.apply_filter(category=self.active_category, query=event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle category chip toggle button clicks."""
        btn_id = event.button.id
        matched_chip = next((cfg for cfg in self.CHIP_CONFIGS if cfg[1] == btn_id), None)
        if matched_chip:
            label, chip_id, cat_name = matched_chip
            self.active_chip_id = chip_id

            # Update chip button variants
            for _, c_id, _ in self.CHIP_CONFIGS:
                try:
                    chip_btn = self.query_one(f"#{c_id}", Button)
                    if chip_btn:
                        chip_btn.variant = "primary" if c_id == chip_id else "default"
                except Exception:
                    pass

            target_category = None if cat_name == "All" else cat_name
            self.apply_filter(category=target_category, query=self.current_query)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle interactive tree node selection."""
        node_id = event.node.data
        if node_id and isinstance(node_id, str):
            self.select_node(node_id)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Handle tree node highlight cursor change."""
        node_id = event.node.data
        if node_id and isinstance(node_id, str):
            self.select_node(node_id)
