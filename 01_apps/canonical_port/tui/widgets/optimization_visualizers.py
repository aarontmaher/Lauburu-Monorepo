from textual.widgets import Static
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

class GeneticOptimizationWidget(Static):
    """Renders the Genetic Mesh Optimizer state."""
    def update_state(self, state: dict):
        if not state:
            return
        
        path = " ➔ ".join(state.get("best_path", []))
        fitness = state.get("fitness", 0.0)
        
        t = Table(title="[bold cyan]Genetic BFS Mesh Optimizer (L1 -> L6)[/bold cyan]", expand=True)
        t.add_column("Metric", style="yellow")
        t.add_column("Value", style="green")
        
        t.add_row("Best Route", f"[bold white]{path}[/bold white]")
        t.add_row("Generation Fitness", f"{fitness:.2f}")
        t.add_row("Latency Goal", "Target: < 2.0 ms RTT")
        
        self.update(Panel(t, border_style="cyan"))

class AntColonyOptimizationWidget(Static):
    """Renders the Ant Pheromone algorithm state."""
    def update_state(self, state: dict):
        if not state:
            return
            
        path = " ➔ ".join(state.get("best_path", []))
        latency = state.get("latency", 0.0)
        pheromones = state.get("pheromones", {})
        
        t = Table(title="[bold magenta]Sub-ms Ant Colony Pheromone Tracker (L1 -> L6)[/bold magenta]", expand=True)
        t.add_column("Edge Topology", style="cyan")
        t.add_column("Pheromone Density", style="magenta")
        t.add_column("State", style="white")
        
        # Sort edges by pheromone density
        sorted_edges = sorted(pheromones.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for edge, phero in sorted_edges:
            edge_str = f"{edge[0]} ↔ {edge[1]}"
            style = "bold red" if phero < 5 else "bold yellow" if phero < 20 else "bold green"
            state_str = "Evaporating" if phero < 5 else "Active Route"
            t.add_row(edge_str, f"[{style}]{phero:.2f}[/{style}]", state_str)
            
        t.add_row("", "", "")
        t.add_row("[bold white]Global Best Path[/bold white]", f"[bold green]{path}[/bold green]", f"Lat: {latency:.2f}ms")
        
        self.update(Panel(t, border_style="magenta"))
