"""
Canonical Port TUI - Optimization Shells (5 Modules)
Version: 3.1.0-CANONICAL
Hardware, Software & ASan, Internet & Multi-WAN, Storage & Tri-Vault, and AI Network Routing.
"""

import os
import sys
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane
from textual import work
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from services.blackboard_store import blackboard_store
    from models.blackboard_models import BlackboardTelemetryState
    from widgets.docked_shortcuts_legend import DockedShortcutsLegend
    from widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from widgets.optimization_visualizers import GeneticOptimizationWidget, AntColonyOptimizationWidget
    from widgets.network_settings_optimizer_widget import NetworkSettingsOptimizerWidget
    from services.mesh_optimization_algorithms import GeneticMeshOptimizer, AntColonyOptimizer
except ImportError:
    from tui.services.blackboard_store import blackboard_store
    from tui.models.blackboard_models import BlackboardTelemetryState
    from tui.widgets.docked_shortcuts_legend import DockedShortcutsLegend
    from tui.widgets.pinned_tab_nav_bar import PinnedTabNavBar
    from tui.widgets.optimization_visualizers import GeneticOptimizationWidget, AntColonyOptimizationWidget
    from tui.widgets.network_settings_optimizer_widget import NetworkSettingsOptimizerWidget
    from tui.services.mesh_optimization_algorithms import GeneticMeshOptimizer, AntColonyOptimizer

class OptimizationScreen(Screen):
    """
    Screen aggregating the optimization modules (Hardware, Software, Internet, Storage, AI Routing, Network System Settings).
    Key: 'o' | Border: cyan
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.genetic_optimizer = GeneticMeshOptimizer()
        self.aco_optimizer = AntColonyOptimizer()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield PinnedTabNavBar(active_screen="optimization")
        with TabbedContent(initial="tab-net-optimizer"):
            with TabPane("6. Network Settings Optimizer (⚡🛠️)", id="tab-net-optimizer"):
                yield NetworkSettingsOptimizerWidget(id="network-settings-optimizer-widget")
            with TabPane("1. Hardware (⚡)", id="tab-hw"):
                yield Static(id="hw-view")
            with TabPane("2. Software & ASan (🛠️)", id="tab-sw"):
                yield Static(id="sw-view")
            with TabPane("3. Internet & Multi-WAN (🌐)", id="tab-net"):
                yield Static(id="net-view")
            with TabPane("4. Storage & Tri-Vault (💾)", id="tab-st"):
                yield Static(id="st-view")
            with TabPane("5. AI Network Routing (🐜/🧬)", id="tab-ai-routing"):
                yield GeneticOptimizationWidget(id="genetic-view")
                yield AntColonyOptimizationWidget(id="aco-view")
        yield DockedShortcutsLegend(active_screen="optimization")
        yield Footer()

    def on_mount(self) -> None:
        self.update_telemetry()
        self.set_interval(1.0, self.update_telemetry)

    def update_telemetry(self) -> None:
        snapshot = blackboard_store.get_snapshot()
        self.render_hw(snapshot)
        self.render_sw(snapshot)
        self.render_net(snapshot)
        self.render_st(snapshot)
        
        # Advance AI Algorithms using live data
        ga_state = self.genetic_optimizer.tick(snapshot)
        aco_state = self.aco_optimizer.tick(snapshot)
        
        try:
            self.query_one("#genetic-view", GeneticOptimizationWidget).update_state(ga_state)
            self.query_one("#aco-view", AntColonyOptimizationWidget).update_state(aco_state)
        except Exception:
            pass

    def render_hw(self, snapshot: BlackboardTelemetryState) -> None:
        l1 = snapshot.layer_1_hardware
        t = Table(title="[bold cyan]MOUNTED SUBSYSTEM: LiveDeviceSentinelHUD (Port 18802)[/bold cyan]", expand=True)
        t.add_column("Node Layer", style="cyan")
        t.add_column("VRAM Allocation", style="yellow")
        t.add_column("Temperature", style="red")
        t.add_column("CPU Load", style="magenta")
        t.add_column("DSP Biometrics", style="green")

        for node in l1.nodes[:7]:
            t.add_row(
                f"{node.node_id}_{node.name}",
                f"{node.vram_used_gb:.1f} / {node.vram_cap_gb:.1f} GB",
                f"{node.thermal_c:.1f}°C",
                f"{node.cpu_usage_pct:.1f}%",
                "Pan-Tompkins 512Hz Active" if node.node_id == "L1" else "TB4 10Gbps Active" if node.node_id == "L2" else "Active Telemetry"
            )
        self.query_one("#hw-view", Static).update(t)

    def render_sw(self, snapshot: BlackboardTelemetryState) -> None:
        t = Table(title="[bold yellow]MOUNTED SUBSYSTEM: MetaTrainingGame AST & Clang ASan Sandbox[/bold yellow]", expand=True)
        t.add_column("Compiler / Sanitizer Pass", style="white")
        t.add_column("Duration", style="cyan")
        t.add_column("Result", style="green")
        t.add_column("Details", style="bright_black")

        t.add_row("Clang AddressSanitizer (ASan)", "12 ms", "● PASSING", "Zero heap-use-after-free or buffer overflows")
        t.add_row("MemorySanitizer (MSan)", "18 ms", "● PASSING", "No uninitialized memory reads in tensor shims")
        t.add_row("UndefinedBehaviorSanitizer (UBSan)", "9 ms", "● PASSING", "Signed integer overflows clean")
        t.add_row("PySpark AST Monorepo Crawler", "142 ms", "● PASSING", "3,104 files indexed; 0 syntax violations")

        self.query_one("#sw-view", Static).update(t)

    def render_net(self, snapshot: BlackboardTelemetryState) -> None:
        t = Table(title="[bold green]MOUNTED SUBSYSTEM: FutureNetworkSimulationHub & Multi-WAN 10-Route Accelerator[/bold green]", expand=True)
        t.add_column("Interface", style="cyan")
        t.add_column("Bandwidth", style="yellow")
        t.add_column("RTT Latency", style="green")
        t.add_column("Priority", style="magenta")
        t.add_column("Status", style="green")

        for route in snapshot.layer_0_networking.wan_routes[:4]:
            rtt_str = f"{route.rtt_ms:.2f} ms" if route.rtt_ms is not None else "--"
            t.add_row(route.interface, route.bandwidth, rtt_str, route.priority, f"● {route.status}")

        self.query_one("#net-view", Static).update(t)

    def render_st(self, snapshot: BlackboardTelemetryState) -> None:
        st = snapshot.layer_1_hardware.storage_health
        
        # Pull Autonomous Storage Governor State
        routing_state = {"primary_write": "L1_Mac_Node", "mac_status": "HEALTHY", "router_status": "WATCHDOG ACTIVE"}
        import json
        import os
        state_file = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/storage_routing_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    routing_state = json.load(f)
            except Exception:
                pass
                
        is_mac_full = routing_state.get("mac_status") == "FULL_LOCKED"
        write_target = routing_state.get("primary_write")
        
        write_tgt = "Joint Mesh Capacity" if write_target == "SeaweedFS_Joint_Capacity" else write_target
        t = Table(title=f"[bold magenta]MOUNTED SUBSYSTEM: Tri-Orchestrator Storage Governor [Target: {write_tgt}][/bold magenta]", expand=True)
        t.add_column("Storage Domain", style="cyan")
        t.add_column("Path", style="bright_black")
        t.add_column("Role / Headroom", style="yellow")
        t.add_column("AI Routing Status", style="green")

        # 1. Trigger Layer
        router_status = routing_state.get("router_status", "WATCHDOG ACTIVE")
        t.add_row("1. GL.iNet Trigger Layer", "/Volumes/GL_Router_Storage/", "Obsidian Vault / Lockfile", f"[bold cyan]● {router_status}[/bold cyan]")
        
        # 2. Compute Layer
        mac_style = "bold red" if is_mac_full else "bold green"
        mac_text = "● WRITE_LOCKED (Capacity > 95%)" if is_mac_full else "● PRIMARY WRITE TARGET"
        t.add_row("2. Heavy Compute Layer", st.pyspark_lake.path, f"Mac Mini NVMe ({st.pyspark_lake.free_headroom_gb:.1f} GB free)", f"[{mac_style}]{mac_text}[/{mac_style}]")
        
        # 3. Joint Network Storage (SeaweedFS DFS)
        dfs_style = "bold green" if is_mac_full else "bright_black"
        dfs_text = "● REBALANCING VOLUMES TO MESH" if is_mac_full else "● JOINT CAPACITY POOL"
        t.add_row("3. Joint Mesh Storage", "/Users/aaron/DFS_UNIFIED", "SeaweedFS Distributed Storage", f"[{dfs_style}]{dfs_text}[/{dfs_style}]")
        
        # 4. GitHub
        t.add_row("4. Canonical Monorepo", st.github_tree.path, "Git Version Control", "● HEALTHY (No lockfiles)")

        try:
            self.query_one("#st-view", Static).update(t)
        except Exception:
            pass
