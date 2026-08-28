from textual.containers import Container, Grid, ScrollableContainer
from textual.widgets import Static
from textual import work
from rich.panel import Panel

try:
    from services.blackboard_store import blackboard_store
except ImportError:
    from tui.services.blackboard_store import blackboard_store

class OverviewView(Container):
    """All Tab View - Mission Control Overview"""
    
    DEFAULT_CSS = """
    OverviewView {
        width: 100%;
        height: 100%;
    }
    
    #overview-grid {
        grid-size: 3 3;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: 1fr 1fr 1fr;
        grid-gutter: 1;
        margin: 1;
        width: 100%;
        height: 100%;
    }
    
    .overview-panel {
        height: 100%;
        width: 100%;
        content-align: center middle;
        background: #111827;
        border: solid #1e293b;
    }
    """
    
    def compose(self):
        with ScrollableContainer():
            with Grid(id="overview-grid"):
                yield Static(id="overview-net", classes="overview-panel")
                yield Static(id="overview-hw", classes="overview-panel")
                yield Static(id="overview-bio", classes="overview-panel")
                yield Static(id="overview-inf", classes="overview-panel")
                yield Static(id="overview-train", classes="overview-panel")
                yield Static(id="overview-gov", classes="overview-panel")
                yield Static(id="overview-tool", classes="overview-panel")
                
    def on_mount(self):
        self.update_panels()
        self.set_interval(2.0, self.update_panels)
        
    def update_panels(self):
        # The store returns a BlackboardTelemetryState via get_snapshot()
        state = blackboard_store.get_snapshot()
        
        # We handle potential missing values gracefully by converting the dataclasses to dicts for safe access
        net = state.layer_0_networking
        hw = state.layer_1_hardware
        bio = state.layer_2_biometrics
        inf = state.layer_3_ai_inference
        train = state.layer_4_training_games
        gov = state.layer_5_governance
        tool = state.layer_6_tooling_skills

        # For the mock display, we will just dump some basic metrics safely
        self.query_one("#overview-net", Static).update(Panel(f"[bold #00ffff]Network[/]\nWAN: {getattr(net, 'wan_active_interface', 'eth0')}\nLat: {getattr(net, 'llama_cpp_rpc_latency_ms', 0)}ms", title="Layer 0"))
        self.query_one("#overview-hw", Static).update(Panel(f"[bold #38bdf8]Hardware[/]\nNodes: {getattr(hw, 'active_mesh_nodes', 1)}\nVRAM: {getattr(hw, 'total_usable_vram_gb', 0)} GB", title="Layer 1"))
        self.query_one("#overview-bio", Static).update(Panel(f"[bold #4ade80]Biometrics[/]\nHeart Rate: {getattr(bio, 'movesense_hr_bpm', '--')} BPM", title="Layer 2"))
        self.query_one("#overview-inf", Static).update(Panel(f"[bold #e879f9]Inference[/]\nActive: {getattr(inf, 'active_llamacpp_model', 'None')}\nTPS: {getattr(inf, 'swarm_tokens_per_second', 0)}", title="Layer 3"))
        self.query_one("#overview-train", Static).update(Panel(f"[bold #facc15]Training[/]\nLoRA: {getattr(train, 'lora_distillation_status', 'Idle')}\nPairs: {getattr(train, 'training_pairs_collected_24h', 0)}", title="Layer 4"))
        self.query_one("#overview-gov", Static).update(Panel(f"[bold #f43f5e]Governance[/]\nMaster: {getattr(gov, 'master_agi_victor', 'Pending')}\nAudits: {getattr(gov, 'pending_truth_audits', 0)}", title="Layer 5"))
        self.query_one("#overview-tool", Static).update(Panel(f"[bold #a78bfa]Tooling[/]\nMCP: {getattr(tool, 'mcp_servers_online', 0)}\nAgents: {getattr(tool, 'active_skills_loaded', 0)}", title="Layer 6"))
